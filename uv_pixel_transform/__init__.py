# SPDX-License-Identifier: GPL-3.0-or-later
"""UV Pixel Transform — select an island, transform its UVs and its paint."""

import hashlib
import math
import time
import zlib
from dataclasses import dataclass, field

import bpy
import bmesh
import numpy as np
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty

from .raster import PixelSelection, TransformError, affine, transform_points
from .preview import FloatingLayer
from . import i18n
from .i18n import tr


REVISION = ".uvpt_revision"
_histories = {}
_revision = 0
_running = None


def read_pixels(image):
    values = np.empty(len(image.pixels), dtype=np.float32)
    image.pixels.foreach_get(values)
    return values.reshape(image.size[1], image.size[0], 4)


def write_pixels(image, pixels):
    image.pixels.foreach_set(np.ascontiguousarray(pixels).reshape(-1))
    image.update()


def mesh_signature(mesh, bm=None):
    if mesh.is_editmode:
        bm = bm or bmesh.from_edit_mesh(mesh)
        uv = bm.loops.layers.uv.active
        values = [(l[uv].uv.x, l[uv].uv.y) for f in bm.faces for l in f.loops] if uv else []
    else:
        layer = mesh.uv_layers.active
        values = [(v.vector.x, v.vector.y) for v in layer.uv] if layer else []
    return hashlib.sha256(np.asarray(values, dtype=np.float32).tobytes()).digest()


def get_revision(mesh, bm=None):
    if mesh.is_editmode:
        bm = bm or bmesh.from_edit_mesh(mesh)
        layer = bm.faces.layers.int.get(REVISION)
        return next(iter(bm.faces))[layer] if layer and len(bm.faces) else 0
    layer = mesh.attributes.get(REVISION)
    return layer.data[0].value if layer and len(layer.data) else 0


@dataclass
class Snapshot:
    signature: bytes
    size: tuple
    pixels: bytes

    @classmethod
    def capture(cls, signature, pixels):
        return cls(signature, pixels.shape, zlib.compress(pixels.tobytes(), level=1))

    def restore(self, image):
        if tuple(image.size) != (self.size[1], self.size[0]):
            return
        pixels = np.frombuffer(zlib.decompress(self.pixels), dtype=np.float32).reshape(self.size)
        write_pixels(image, pixels)


@dataclass
class History:
    image_uid: int
    current: int
    states: dict = field(default_factory=dict)


@persistent
def restore_history(_):
    """BMesh's undoable revision connects Blender undo to non-undoable image pixels."""
    for mesh in bpy.data.meshes:
        history = _histories.get(mesh.session_uid)
        if history is None:
            continue
        revision = get_revision(mesh)
        if revision == history.current:
            continue
        state = history.states.get(revision)
        if state is None or state.signature != mesh_signature(mesh):
            continue
        image = next((i for i in bpy.data.images if i.session_uid == history.image_uid), None)
        if image:
            state.restore(image)
            history.current = revision


@persistent
def clear_history(_):
    _histories.clear()


def material_nodes(material, image):
    if not material or not material.use_nodes:
        return []
    # Nodes inside groups cannot be mapped safely by this first version.
    return [n for n in material.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image == image]


def tree_uses_image(tree, image, seen=None):
    seen = set() if seen is None else seen
    if tree is None or tree.as_pointer() in seen:
        return False
    seen.add(tree.as_pointer())
    return any((n.type == 'TEX_IMAGE' and n.image == image) or
               (n.type == 'GROUP' and tree_uses_image(n.node_tree, image, seen)) for n in tree.nodes)


def selected_islands(bm, uv, settings):
    """Expand selected UV elements to whole edge-connected UV islands."""
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
    if settings.use_uv_select_sync and not bm.uv_select_sync_valid:
        bm.uv_select_sync_from_mesh()
    seeds = {f.index for f in bm.faces if not f.hide and
             (settings.use_uv_select_sync or f.select) and
             any(l.uv_select_vert for l in f.loops)}
    if not seeds:
        raise TransformError("Select a UV island in the UV Editor first.")
    parents = list(range(len(bm.faces)))

    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    for edge in bm.edges:
        groups = {}
        for loop in edge.link_loops:
            a, b = loop, loop.link_loop_next
            if a.vert.index > b.vert.index:
                a, b = b, a
            key = tuple(round(v, 6) for l in (a, b) for v in l[uv].uv)
            if key in groups:
                parents[root(loop.face.index)] = root(groups[key])
            else:
                groups[key] = loop.face.index
    chosen = {root(i) for i in seeds}
    return {f.index for f in bm.faces if root(f.index) in chosen}


class TransformSession:
    def __init__(self, context):
        obj = context.edit_object
        if not obj or obj.type != 'MESH' or context.mode != 'EDIT_MESH':
            raise TransformError("Select a mesh and enter Edit Mode.")
        if len(context.objects_in_mode_unique_data) != 1:
            raise TransformError("Edit one mesh at a time.")
        if context.area.type != 'IMAGE_EDITOR' or context.area.ui_type != 'UV':
            raise TransformError("Run this from the UV Editor.")
        image = context.space_data.image
        if not image or not image.has_data or image.source not in {'FILE', 'GENERATED'}:
            raise TransformError("Display a loaded, single-tile image in the UV Editor.")
        if image.library or obj.data.library:
            raise TransformError("Make the mesh and image local before editing.")
        if image.channels != 4 or image.alpha_mode not in {'STRAIGHT', 'NONE'}:
            raise TransformError("Use an RGBA image with Straight or None alpha mode.")
        if image.size[0] * image.size[1] > 4096 * 4096:
            raise TransformError("This preview version supports images up to 16 megapixels.")
        if len(image.pixels) != image.size[0] * image.size[1] * 4:
            raise TransformError("Image pixel buffer is unavailable.")
        for other in bpy.data.objects:
            if other == obj or other.type != 'MESH':
                continue
            if any(m and m.use_nodes and tree_uses_image(m.node_tree, image) for m in other.data.materials):
                raise TransformError(tr("Image also used by {name}. Give this mesh its own image first.").format(name=other.name))
        self.obj = obj
        self.mesh = obj.data
        self.image = image
        self.bm = bmesh.from_edit_mesh(self.mesh)
        self.bm.verts.index_update()
        self.uv = self.bm.loops.layers.uv.active
        if self.uv is None:
            raise TransformError("Create a UV map first.")
        chosen = selected_islands(self.bm, self.uv, context.scene.tool_settings)
        self.chosen = chosen
        selected_faces = [f for f in self.bm.faces if f.index in chosen]
        render_uv = next((u.name for u in self.mesh.uv_layers if u.active_render), None)
        for material_index in {f.material_index for f in selected_faces}:
            materials = self.mesh.materials
            mat = materials[material_index] if material_index < len(materials) else None
            nodes = material_nodes(mat, image)
            if not nodes:
                raise TransformError("Every selected face must use the displayed image in its material.")
            for node in nodes:
                if node.projection != 'FLAT':
                    raise TransformError("Only flat UV image mapping is supported.")
                links = node.inputs['Vector'].links
                source = links[0].from_node if links else None
                if source and source.type == 'UVMAP':
                    valid = source.uv_map == self.uv.name
                elif source and source.type == 'TEX_COORD' and links[0].from_socket.name == 'UV':
                    valid = self.uv.name == render_uv
                elif source is None:
                    valid = self.uv.name == render_uv
                else:
                    valid = False
                if not valid:
                    raise TransformError("Use the active UV map directly for this image (no Mapping node).")
        self.loops = [l for f in selected_faces for l in f.loops]
        self.original_uv = np.array([l[self.uv].uv[:] for l in self.loops], dtype=np.float64)
        self.size = np.array(image.size[:], dtype=np.float64)
        points = self.original_uv * self.size
        self.pivot = (points.min(axis=0) + points.max(axis=0)) / 2
        self.before_signature = mesh_signature(self.mesh, self.bm)
        self.before_revision = get_revision(self.mesh, self.bm)
        self.original_pixels = read_pixels(image)
        selected, stationary = [], []
        for triangle in self.bm.calc_loop_triangles():
            target = selected if triangle[0].face.index in chosen else stationary
            target.append([np.asarray(l[self.uv].uv[:]) * self.size for l in triangle])
        props = context.scene.uvpt_settings
        self.pixels = PixelSelection(self.original_pixels, selected, stationary, props.padding)
        self.interpolation = props.interpolation
        self.clear_source = props.clear_source
        self.allow_outside = props.allow_outside
        self.protect_others = props.protect_others
        self.show_preview = props.live_preview
        self.matrix = np.eye(3)
        self.applied_matrix = np.eye(3)
        self.mutated = False
        self.result = self.original_pixels
        self.outside = False

    def apply(self, matrix, preview=False):
        if np.allclose(matrix, self.applied_matrix, atol=1e-10, rtol=0):
            return
        pixels = self.pixels.render(matrix, self.interpolation, self.clear_source,
                                    allow_outside=preview and self.allow_outside,
                                    protect=self.protect_others, composite=True)
        coordinates = transform_points(self.original_uv * self.size, matrix) / self.size
        try:
            self.mutated = True
            write_pixels(self.image, pixels)
            for loop, uv in zip(self.loops, coordinates):
                loop[self.uv].uv = uv
            bmesh.update_edit_mesh(self.mesh, loop_triangles=False, destructive=False)
        except Exception:
            self.cancel()
            raise
        self.matrix, self.result = matrix.copy(), pixels
        self.applied_matrix = matrix.copy()
        self.outside = bool(np.any(coordinates < -1e-8) or np.any(coordinates > 1 + 1e-8))

    def set_preview(self, matrix):
        points = transform_points(self.original_uv * self.size, matrix)
        if not np.isfinite(matrix).all() or abs(np.linalg.det(matrix)) < 1e-10:
            raise TransformError("Use a finite, non-zero transform.")
        if not self.allow_outside:
            self.pixels._bounds(points)
        self.matrix = matrix.copy()
        self.outside = bool(np.any(points < -1e-5) or np.any(points > self.size + 1e-5))

    def cancel(self):
        if not self.mutated:
            return
        for loop, uv in zip(self.loops, self.original_uv):
            loop[self.uv].uv = uv
        bmesh.update_edit_mesh(self.mesh, loop_triangles=False, destructive=False)
        write_pixels(self.image, self.original_pixels)
        self.mutated = False

    def commit(self):
        global _revision
        points = transform_points(self.original_uv * self.size, self.matrix)
        if np.any(points < -1e-5) or np.any(points > self.size + 1e-5):
            raise TransformError("Bring the whole island inside the image before applying. Esc restores the original.")
        if np.allclose(self.matrix, np.eye(3), atol=1e-10):
            return False
        history = _histories.get(self.mesh.session_uid)
        if history and history.image_uid != self.image.session_uid:
            raise TransformError("Undo history is tracking a different image on this mesh. Reload the file first.")
        self.apply(self.matrix)
        if history is None:
            history = History(self.image.session_uid, self.before_revision)
            _histories[self.mesh.session_uid] = history
        before = Snapshot.capture(self.before_signature, self.original_pixels)
        after = Snapshot.capture(mesh_signature(self.mesh, self.bm), self.result)
        _revision = max(_revision, self.before_revision) + 1
        layer = self.bm.faces.layers.int.get(REVISION) or self.bm.faces.layers.int.new(REVISION)
        for face in self.bm.faces:
            face[layer] = _revision
        bmesh.update_edit_mesh(self.mesh, loop_triangles=False, destructive=False)
        history.states[self.before_revision] = before
        history.states[_revision] = after
        history.current = _revision
        return True


class UVPT_Settings(bpy.types.PropertyGroup):
    language: EnumProperty(name="Language", items=i18n.LANGUAGES, default='AUTO')
    padding: IntProperty(name="Padding", description="Protect and extend island edges in pixels", default=2, min=0, max=16)
    interpolation: EnumProperty(name="Sampling", items=i18n.sampling_items, default=0)
    clear_source: BoolProperty(name="Clear old pixels on apply", description="Erase the original island only when applying; leave disabled to keep the original painting", default=False)
    live_preview: BoolProperty(name="Live pixel preview", description="Preview from the original pixels without accumulating blur", default=True)
    allow_outside: BoolProperty(name="Allow outside preview", description="Move, scale and rotate outside the image; bring the island back inside before applying. Original pixels are retained", default=True)
    protect_others: BoolProperty(name="Protect other islands on apply", description="Block applying over another UV island. Floating previews may always overlap", default=True)


class UVPT_OT_transform(bpy.types.Operator):
    bl_idname = "uv.pixel_transform"
    bl_label = "Transform UV + Pixels"
    bl_description = "Transform selected UV islands together with the painted image pixels"
    bl_options = {'UNDO', 'BLOCKING'}

    mode: EnumProperty(items=[('MOVE', "Move", ""), ('SCALE', "Scale", ""), ('ROTATE', "Rotate", ""), ('PRECISE', "Precise", "")], default='MOVE')
    offset_x: FloatProperty(name="Move X (px)", default=0)
    offset_y: FloatProperty(name="Move Y (px)", default=0)
    scale: FloatProperty(name="Scale", default=1, min=0.001, max=100)
    angle: FloatProperty(name="Rotation", default=0, subtype='ANGLE')

    @classmethod
    def poll(cls, context):
        return (_running is None and context.area and context.area.type == 'IMAGE_EDITOR'
                and context.area.ui_type == 'UV' and context.mode == 'EDIT_MESH')

    @classmethod
    def description(cls, context, properties):
        labels = {'MOVE':'Move UV + Pixels', 'SCALE':'Scale UV + Pixels',
                  'ROTATE':'Rotate UV + Pixels', 'PRECISE':'Precise Transform…'}
        return tr(labels[properties.mode], context)

    def execute(self, context):
        session = None
        try:
            session = TransformSession(context)
            session.apply(affine(session.pivot, (self.offset_x, self.offset_y), self.scale, self.angle))
            if session.commit():
                return {'FINISHED'}
            return {'CANCELLED'}
        except (TransformError, RuntimeError, ValueError) as exc:
            if session:
                session.cancel()
            self.report({'ERROR'}, tr(str(exc), context))
            return {'CANCELLED'}

    def draw(self, context):
        for prop, label in [('offset_x','Move X (px)'), ('offset_y','Move Y (px)'),
                            ('scale','Scale'), ('angle','Rotation')]:
            self.layout.prop(self, prop, text=tr(label, context), translate=False)

    def invoke(self, context, event):
        global _running
        if self.mode == 'PRECISE':
            return context.window_manager.invoke_props_dialog(self)
        try:
            self.session = TransformSession(context)
            self.layer = FloatingLayer(self.session, context.area,
                                       next(r for r in context.area.regions if r.type == 'WINDOW'))
        except (TransformError, RuntimeError, ValueError) as exc:
            self.report({'ERROR'}, tr(str(exc), context))
            return {'CANCELLED'}
        self.area = context.area
        self.region = next(r for r in self.area.regions if r.type == 'WINDOW')
        # Blender UI calls reuse the last operator's properties. Each mouse
        # gesture must start at identity, irrespective of the preceding mode.
        self.offset_x = self.offset_y = self.angle = 0
        self.scale = 1
        self.start = self.mouse_pixels(event) if self.on_canvas(event) else None
        self.base_matrix = np.eye(3)
        self.pivot = self.session.pivot.copy()
        self.pointer = self.start
        self.raw_offset = np.zeros(2)
        self.raw_scale = 1.0
        self.raw_angle = 0.0
        self.axis = None
        self.numeric = ""
        self.pending = False
        self.reanchor_after_navigation = False
        self.error = ""
        self.header_text = None
        self.last_preview = 0.0
        self.timer = context.window_manager.event_timer_add(1 / 60, window=context.window)
        _running = self
        context.window_manager.modal_handler_add(self)
        self.header()
        self.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def mouse_pixels(self, event):
        uv = self.region.view2d.region_to_view(event.mouse_x - self.region.x, event.mouse_y - self.region.y)
        return np.asarray(uv) * self.session.size

    def on_canvas(self, event):
        def contains(region):
            return (region.x <= event.mouse_x < region.x + region.width and
                    region.y <= event.mouse_y < region.y + region.height)
        return contains(self.region) and not any(
            contains(r) for r in self.area.regions
            if r.type in {'UI', 'TOOLS', 'TOOL_HEADER', 'ASSET_SHELF', 'ASSET_SHELF_HEADER'}
            and r.width > 1 and r.height > 1)

    def header(self):
        amount = f"X {self.offset_x:.1f}px  Y {self.offset_y:.1f}px" if self.mode == 'MOVE' else (
            f"{self.scale:.3f}×" if self.mode == 'SCALE' else f"{math.degrees(self.angle):.1f}°")
        hint = (tr("Move pointer onto the image to start, or type a value") if self.start is None and not self.numeric
                else amount + ' | ' + tr('G/S/R: switch · Enter: apply · Esc: cancel · Ctrl: snap'))
        if self.session.outside:
            hint = tr('Outside preview: return inside to apply') + ' | ' + amount + ' | ' + tr('Esc: cancel')
        text = self.error or f"UV + Pixels: {tr(self.mode.title())} | {hint}"
        if text != self.header_text:
            self.header_text = text
            self.area.header_text_set(text)

    def update_values(self, event):
        if event.type == 'MOUSEMOVE':
            if self.start is None:
                # A sidebar click is not a meaningful canvas reference point.
                # Arm at the first pointer position over the image instead.
                if self.on_canvas(event):
                    self.start = self.pointer = self.mouse_pixels(event)
            else:
                current = self.mouse_pixels(event)
                fine = 0.1 if event.shift else 1.0
                self.raw_offset += (current - self.pointer) * fine
                a, b = self.pointer - self.pivot, current - self.pivot
                initial = max(np.linalg.norm(self.start - self.pivot), 1)
                self.raw_scale += (np.linalg.norm(b) - np.linalg.norm(a)) / initial * fine
                if np.linalg.norm(a) > 1e-6 and np.linalg.norm(b) > 1e-6:
                    self.raw_angle += math.atan2(a[0] * b[1] - a[1] * b[0], np.dot(a, b)) * fine
                self.pointer = current
        if self.mode == 'MOVE':
            delta = np.round(self.raw_offset) if event.ctrl else self.raw_offset.copy()
            if self.axis == 'X':
                delta[1] = 0
            elif self.axis == 'Y':
                delta[0] = 0
            self.offset_x, self.offset_y = delta
        elif self.mode == 'SCALE':
            self.scale = max(0.001, round(self.raw_scale * 10) / 10 if event.ctrl else self.raw_scale)
        else:
            self.angle = round(self.raw_angle / (math.pi / 12)) * (math.pi / 12) if event.ctrl else self.raw_angle
        if self.numeric not in {"", "-", ".", "-."}:
            value = float(self.numeric)
            if self.mode == 'MOVE':
                self.offset_x, self.offset_y = (0, value) if self.axis == 'Y' else (value, 0)
            elif self.mode == 'SCALE':
                if value <= 0:
                    raise TransformError("Scale must be positive.")
                self.scale = value
            else:
                self.angle = math.radians(value)

    def requested_matrix(self):
        return affine(self.pivot, (self.offset_x, self.offset_y), self.scale, self.angle) @ self.base_matrix

    def switch_mode(self, mode, event):
        self.base_matrix = self.requested_matrix()
        self.pivot = transform_points(self.session.pivot, self.base_matrix)
        self.mode = mode
        self.offset_x = self.offset_y = self.angle = 0
        self.scale = self.raw_scale = 1
        self.raw_offset = np.zeros(2)
        self.raw_angle = 0
        self.axis = None
        self.numeric = ""
        self.start = self.pointer = self.mouse_pixels(event)

    def preview(self):
        started = time.perf_counter()
        matrix = self.requested_matrix()
        self.session.set_preview(matrix)
        self.layer.set_matrix(matrix)
        self.error = ""
        self.pending = False
        self.last_preview = started

    def finish(self, context, cancelled):
        global _running
        self.layer.close()
        if cancelled:
            self.session.cancel()
        self.area.header_text_set(None)
        self.area.tag_redraw()
        context.window_manager.event_timer_remove(self.timer)
        _running = None
        return {'CANCELLED'} if cancelled else {'FINISHED'}

    def modal(self, context, event):
        try:
            if self.layer.error:
                raise RuntimeError('GPU preview: ' + self.layer.error)
            if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'WHEELINMOUSE', 'WHEELOUTMOUSE',
                              'TRACKPADZOOM', 'TRACKPADPAN', 'MIDDLEMOUSE', 'NDOF_MOTION'}:
                self.reanchor_after_navigation = True
                return {'PASS_THROUGH'}
            if self.reanchor_after_navigation and event.type == 'MOUSEMOVE':
                # Blender has now applied the native zoom/pan. Re-anchor the
                # pointer in that updated View2D without changing the layer.
                self.start = self.pointer = self.mouse_pixels(event)
                self.reanchor_after_navigation = False
                return {'RUNNING_MODAL'}
            if event.type in {'ESC', 'RIGHTMOUSE'}:
                return self.finish(context, True)
            if event.type in {'RET', 'NUMPAD_ENTER', 'LEFTMOUSE'} and event.value == 'PRESS':
                if self.numeric in {'-', '.', '-.'}:
                    raise TransformError("Finish typing a number or press Esc.")
                self.update_values(event)
                self.preview()
                if not self.session.commit():
                    return self.finish(context, True)
                return self.finish(context, False)
            changed = event.type == 'MOUSEMOVE'
            if event.value == 'PRESS':
                if event.type in {'G', 'S', 'R'}:
                    self.switch_mode({'G':'MOVE', 'S':'SCALE', 'R':'ROTATE'}[event.type], event)
                    changed = True
                elif event.type in {'X', 'Y'} and self.mode == 'MOVE':
                    self.axis = None if self.axis == event.type else event.type
                    changed = True
                elif event.type == 'BACK_SPACE':
                    self.numeric = self.numeric[:-1]
                    changed = True
                elif event.ascii and event.ascii in '0123456789.-':
                    candidate = self.numeric + event.ascii
                    if candidate.count('.') <= 1 and candidate.count('-') <= 1 and '-' not in candidate[1:]:
                        self.numeric = candidate
                        changed = True
            if changed:
                self.update_values(event)
                self.pending = True
            # Floating previews only update a small matrix. Forward input
            # immediately; Blender coalesces redraws. No pixel resampling or
            # image upload belongs in this mouse-event path.
            if (self.pending and (changed or (event.type == 'TIMER'
                    and (not hasattr(event, 'timer') or event.timer == self.timer)))):
                self.preview()
            self.header()
        except TransformError as exc:
            self.error = tr(str(exc)) + " | " + tr('Esc: cancel')
            self.pending = False
            self.header()
        except Exception as exc:
            self.report({'ERROR'}, tr('Transform cancelled: {error}').format(error=tr(str(exc))))
            return self.finish(context, True)
        return {'RUNNING_MODAL'}


class UVPT_PT_panel(bpy.types.Panel):
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'UV + Pixels'
    bl_label = 'UV Pixel Transform 0.2.0'

    @classmethod
    def poll(cls, context):
        return context.area.ui_type == 'UV'

    def draw(self, context):
        layout = self.layout
        props = context.scene.uvpt_settings
        layout.prop(props, 'language', text=tr('Language', context), translate=False)
        image = context.space_data.image
        layout.label(text=image.name if image else tr('Choose a painted image', context), icon='IMAGE_DATA', translate=False)
        column = layout.column(align=True)
        column.enabled = context.mode == 'EDIT_MESH' and _running is None
        for mode, label, icon in [('MOVE', 'Move UV + Pixels', 'ARROW_LEFTRIGHT'),
                                   ('SCALE', 'Scale UV + Pixels', 'FULLSCREEN_ENTER'),
                                   ('ROTATE', 'Rotate UV + Pixels', 'DRIVER_ROTATIONAL_DIFFERENCE'),
                                   ('PRECISE', 'Precise Transform…', 'PREFERENCES')]:
            column.operator('uv.pixel_transform', text=tr(label, context), icon=icon, translate=False).mode = mode
        for prop, label in [('interpolation','Sampling'), ('padding','Padding'),
                            ('clear_source','Clear old pixels on apply'), ('live_preview','Live pixel preview'),
                            ('allow_outside','Allow outside preview'), ('protect_others','Protect other islands on apply')]:
            layout.prop(props, prop, text=tr(label, context), translate=False)
        for label in ['Floating layer · G / S / R switches mode',
                      'Click a button, then enter the image area', 'Select islands · transform · save image',
                      'Enter applies · Esc cancels · Ctrl+Z undoes']:
            layout.label(text=tr(label, context), translate=False)


def uv_menu(self, context):
    self.layout.separator()
    for mode in ('MOVE', 'SCALE', 'ROTATE'):
        self.layout.operator('uv.pixel_transform', text=tr(f'{mode.title()} UV + Pixels', context), translate=False).mode = mode


CLASSES = (UVPT_Settings, UVPT_OT_transform, UVPT_PT_panel)


def register():
    i18n.register()
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.uvpt_settings = PointerProperty(type=UVPT_Settings)
    bpy.types.IMAGE_MT_uvs.append(uv_menu)
    bpy.app.handlers.undo_post.append(restore_history)
    bpy.app.handlers.redo_post.append(restore_history)
    bpy.app.handlers.load_pre.append(clear_history)


def unregister():
    if _running is not None:
        _running.finish(bpy.context, True)
    for handlers, fn in ((bpy.app.handlers.undo_post, restore_history),
                         (bpy.app.handlers.redo_post, restore_history),
                         (bpy.app.handlers.load_pre, clear_history)):
        if fn in handlers:
            handlers.remove(fn)
    bpy.types.IMAGE_MT_uvs.remove(uv_menu)
    del bpy.types.Scene.uvpt_settings
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    clear_history(None)
    i18n.unregister()
