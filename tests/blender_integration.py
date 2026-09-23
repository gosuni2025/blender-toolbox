"""blender -b --factory-startup --python tests/blender_integration.py"""
import sys
import math
from pathlib import Path
import bpy
import bmesh
import numpy as np
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import uv_pixel_transform as addon

addon.register()
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
mesh = bpy.data.meshes.new('UVPT Test Mesh')
mesh.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
                  (2, 0, 0), (3, 0, 0), (3, 1, 0), (2, 1, 0)], [], [(0, 1, 2, 3), (4, 5, 6, 7)])
obj = bpy.data.objects.new('UVPT Test', mesh)
bpy.context.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
uv = mesh.uv_layers.new(name='UVMap')
coords = [(4/64, 4/32), (8/64, 4/32), (8/64, 8/32), (4/64, 8/32),
          (50/64, 20/32), (54/64, 20/32), (54/64, 24/32), (50/64, 24/32)]
for value, co in zip(uv.uv, coords):
    value.vector = co
image = bpy.data.images.new('UVPT Test Paint', width=64, height=32, alpha=True, float_buffer=True)
pixels = np.zeros((32, 64, 4), dtype=np.float32)
pixels[4:8, 4:8] = [1, .25, .5, 1]
pixels[20:24, 50:54] = [0, .8, 1, 1]
addon.write_pixels(image, pixels)
mat = bpy.data.materials.new('UVPT Test Material')
mat.use_nodes = True
tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
tex.image = image
mat.node_tree.links.new(tex.outputs['Color'], mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
mesh.materials.append(mat)
area = bpy.context.screen.areas[0]
area.type = 'IMAGE_EDITOR'
area.ui_type = 'UV'
area.spaces.active.image = image
region = next(r for r in area.regions if r.type == 'WINDOW')
bpy.context.scene.tool_settings.use_uv_select_sync = False
bpy.context.scene.uvpt_settings.padding = 0
assert not bpy.context.scene.uvpt_settings.clear_source
bpy.context.scene.uvpt_settings.clear_source = True
bpy.ops.object.mode_set(mode='EDIT')
bm = bmesh.from_edit_mesh(mesh)
bm.faces.ensure_lookup_table()
for face in bm.faces:
    face.select_set(True)
    for loop in face.loops:
        loop.uv_select_vert = face.index == 0
bmesh.update_edit_mesh(mesh)

with bpy.context.temp_override(area=area, region=region):
    baseline_uv = addon.mesh_signature(mesh)
    session = addon.TransformSession(bpy.context)
    session.apply(addon.affine(session.pivot, (12, 8), 2))
    assert addon.read_pixels(image)[10:18, 14:22, 0].min() == 1
    assert addon.read_pixels(image)[20:24, 50:54, 1].min() > .79
    session.cancel()
    np.testing.assert_array_equal(addon.read_pixels(image), pixels)
    assert addon.mesh_signature(mesh) == baseline_uv
    print('PASS session scale, stationary image, cancellation')

    bpy.context.scene.uvpt_settings.allow_outside = True
    session = addon.TransformSession(bpy.context)
    session.set_preview(addon.affine(session.pivot, (-100, 0), 2, .4))
    assert session.outside
    assert addon.mesh_signature(mesh) == baseline_uv
    np.testing.assert_array_equal(addon.read_pixels(image), pixels)
    try:
        session.commit()
        raise AssertionError('An outside preview must not be committed')
    except addon.TransformError as exc:
        assert 'inside' in str(exc)
    target = addon.affine(session.pivot, (12, 8), 2, .4)
    session.set_preview(target)
    session.apply(target)
    np.testing.assert_array_equal(addon.read_pixels(image), session.pixels.render(target, composite=True))
    session.cancel()
    np.testing.assert_array_equal(addon.read_pixels(image), pixels)
    bpy.context.scene.uvpt_settings.allow_outside = False
    print('PASS outside scale/rotation preview, blocked commit, return without pixel loss, cancel')

    # Verify real Blender undo/redo, not a mock or a manual call to our handler.
    bpy.context.preferences.edit.use_global_undo = True
    bpy.ops.ed.undo_push(message='UVPT baseline')
    result = bpy.ops.uv.pixel_transform(offset_x=12, offset_y=8, scale=2)
    assert result == {'FINISHED'}, result
    after = addon.read_pixels(bpy.data.images['UVPT Test Paint']).copy()
    after_uv = addon.mesh_signature(bpy.data.meshes['UVPT Test Mesh'])
    # Python-driven EXEC calls do not push undo automatically (UI calls do).
    bpy.ops.ed.undo_push(message='UVPT Transform')
    bpy.ops.ed.undo()
    np.testing.assert_array_equal(addon.read_pixels(bpy.data.images['UVPT Test Paint']), pixels)
    assert addon.mesh_signature(bpy.data.meshes['UVPT Test Mesh']) == baseline_uv
    bpy.ops.ed.redo()
    np.testing.assert_array_equal(addon.read_pixels(bpy.data.images['UVPT Test Paint']), after)
    assert addon.mesh_signature(bpy.data.meshes['UVPT Test Mesh']) == after_uv
    print('PASS native undo and redo restore UVs AND pixels')

    # Undo again; test the 5.2 UV-sync API and the full-island selection rule.
    bpy.ops.ed.undo()
    mesh = bpy.data.meshes['UVPT Test Mesh']
    image = bpy.data.images['UVPT Test Paint']
    bm = bmesh.from_edit_mesh(mesh)
    bm.faces.ensure_lookup_table()
    bpy.context.scene.tool_settings.use_uv_select_sync = True
    for face in bm.faces:
        face.select_set(face.index == 0)
    bm.uv_select_sync_from_mesh()
    session = addon.TransformSession(bpy.context)
    assert len(session.loops) == 4
    session.apply(addon.affine(session.pivot, (6, 0)))
    session.cancel()
    np.testing.assert_array_equal(addon.read_pixels(image), pixels)
    bpy.context.scene.tool_settings.use_uv_select_sync = False
    for face in bm.faces:
        face.select_set(True)
        for i, loop in enumerate(face.loops):
            loop.uv_select_vert = face.index == 0 and i == 0
    session = addon.TransformSession(bpy.context)
    assert len(session.loops) == 4
    print('PASS UV sync, partial selection expands to island')

    if not bpy.app.background:
        # The GUI runner prepares the editor before this callback; fit its test
        # image now to obtain the same View2D mapping as a visible UV editor.
        bpy.ops.image.view_all(fit_view=True)
        # Invoke the real operator, then exercise its event handler without OS input.
        result = bpy.ops.uv.pixel_transform('INVOKE_DEFAULT', mode='SCALE')
        assert result == {'RUNNING_MODAL'}, result
        op = addon._running
        mx = op.region.x + 300
        my = op.region.y + 300
        def event(kind, char='', value='PRESS'):
            return SimpleNamespace(type=kind, ascii=char, value=value, mouse_x=mx, mouse_y=my, ctrl=False, shift=False)
        op.modal(bpy.context, event('TWO', '2'))
        op.last_preview = 0  # Advance the preview clock in this synchronous event test.
        op.modal(bpy.context, event('TIMER', value='NOTHING'))
        assert op.scale == 2
        assert addon.mesh_signature(mesh) == baseline_uv
        np.testing.assert_array_equal(addon.read_pixels(image), pixels)
        assert not np.array_equal(op.layer.matrix, np.eye(3))
        op.layer.draw()
        assert not op.layer.error, op.layer.error
        op.modal(bpy.context, event('ESC'))
        np.testing.assert_array_equal(addon.read_pixels(image), pixels)
        assert addon.mesh_signature(mesh) == baseline_uv
        assert addon._running is None
        print('PASS interactive invoke, typed scale, live preview, Esc')

        result = bpy.ops.uv.pixel_transform('INVOKE_DEFAULT', mode='SCALE')
        op = addon._running
        op.modal(bpy.context, event('ZERO', '0'))
        assert op.modal(bpy.context, event('RET')) == {'RUNNING_MODAL'}
        assert 'positive' in op.error
        op.modal(bpy.context, event('ESC'))
        print('PASS zero-scale cannot accidentally confirm previous preview')

        # Reproduce the UI's remembered parameters: Move must not inherit the
        # preceding Scale/Rotate transform, including during a mouse preview.
        result = bpy.ops.uv.pixel_transform('INVOKE_DEFAULT', mode='MOVE',
                                            scale=1.7, angle=.8, offset_x=100, offset_y=100)
        assert result == {'RUNNING_MODAL'}
        op = addon._running
        assert (op.scale, op.angle, op.offset_x, op.offset_y) == (1, 0, 0, 0)
        # A sidebar/menu launch arms on entry into the canvas, without including
        # the trip from the button to the image in the translation.
        op.start = op.pointer = None
        def mouse(x, y, ctrl=False, shift=False, kind='MOUSEMOVE'):
            return SimpleNamespace(type=kind, ascii='', value='PRESS', mouse_x=x, mouse_y=y,
                                   ctrl=ctrl, shift=shift)
        op.modal(bpy.context, mouse(area.x + area.width + 20, area.y + 100))
        assert op.start is None and op.offset_x == 0 and op.offset_y == 0
        anchor = mouse(region.x + 100, region.y + 100)
        op.modal(bpy.context, anchor)
        assert op.start is not None and op.offset_x == 0 and op.offset_y == 0
        # Convert a desired 12px/8px image displacement to screen coordinates.
        unit = op.mouse_pixels(mouse(anchor.mouse_x + 1, anchor.mouse_y + 1)) - op.start
        assert np.isfinite(unit).all() and np.all(np.abs(unit) > 1e-9), unit
        moved = mouse(anchor.mouse_x + 12 / unit[0], anchor.mouse_y + 8 / unit[1], ctrl=True)
        op.modal(bpy.context, moved)
        op.last_preview = 0  # Advance the preview clock in this synchronous event test.
        op.modal(bpy.context, event('TIMER', value='NOTHING'))
        assert not op.error, op.error
        np.testing.assert_allclose([op.offset_x, op.offset_y], [12, 8])
        np.testing.assert_array_equal(addon.read_pixels(image), pixels)
        np.testing.assert_allclose(op.layer.matrix[:2, 2], [12, 8])
        uv_after = np.array([l[op.session.uv].uv[:] for l in op.session.loops])
        np.testing.assert_array_equal(uv_after, op.session.original_uv)
        op.modal(bpy.context, event('ESC'))
        np.testing.assert_array_equal(addon.read_pixels(image), pixels)
        print('PASS mouse Move, sidebar entry, previous-mode reset, floating displacement, untouched source, cancel')

        # Pointer motion through 180 degrees must keep accumulating, and pressing
        # Shift should affect subsequent deltas rather than jumping to 10%.
        bpy.ops.uv.pixel_transform('INVOKE_DEFAULT', mode='ROTATE')
        op = addon._running
        pivot = op.session.pivot
        # Use real View2D coordinate conversion to create circular mouse events.
        origin = op.mouse_pixels(mouse(0, 0))
        units = op.mouse_pixels(mouse(1, 1)) - origin
        def on_circle(degrees, shift=False, kind='MOUSEMOVE'):
            radians = math.radians(degrees)
            point = pivot + np.array([math.cos(radians), math.sin(radians)]) * 3
            screen = (point - origin) / units
            return mouse(*screen, shift=shift, kind=kind)
        op.start = op.pointer = op.mouse_pixels(on_circle(0))
        for degrees in [45, 90, 135, 179, 181, 225, 270, 315, 359, 361]:
            op.modal(bpy.context, on_circle(degrees))
        assert abs(math.degrees(op.angle) - 361) < .05, math.degrees(op.angle)
        op.modal(bpy.context, on_circle(371, shift=True))
        assert abs(math.degrees(op.angle) - 362) < .05
        op.modal(bpy.context, on_circle(381))
        assert abs(math.degrees(op.angle) - 372) < .05
        op.modal(bpy.context, event('ESC'))
        np.testing.assert_array_equal(addon.read_pixels(image), pixels)
        print('PASS continuous rotation beyond 360 degrees and Shift without jumps')

        # A single floating transaction may leave the tile, rotate, scale, and
        # return. No intermediate operation is baked into the image or UV map.
        bpy.context.scene.uvpt_settings.allow_outside = True
        bpy.context.scene.uvpt_settings.clear_source = False
        bpy.ops.uv.pixel_transform('INVOKE_DEFAULT', mode='MOVE')
        op = addon._running
        original_dirty = image.is_dirty
        def type_value(value):
            for char in str(value):
                op.modal(bpy.context, event('NONE', char))
            op.modal(bpy.context, event('TIMER', value='NOTHING'))
        type_value(-100)
        assert op.session.outside
        assert op.modal(bpy.context, event('RET')) == {'RUNNING_MODAL'}
        op.modal(bpy.context, event('R'))
        type_value(90)
        op.modal(bpy.context, event('S'))
        type_value(2)
        op.modal(bpy.context, event('G'))
        type_value(112)
        op.modal(bpy.context, event('G'))
        op.modal(bpy.context, event('Y'))
        type_value(8)
        assert not op.session.outside
        np.testing.assert_array_equal(addon.read_pixels(image), pixels)
        assert image.is_dirty == original_dirty
        assert addon.mesh_signature(mesh) == baseline_uv
        np.testing.assert_allclose(op.session.matrix, addon.affine((6, 6), (12, 8), 2, math.pi/2), atol=1e-5)
        assert op.modal(bpy.context, event('RET')) == {'FINISHED'}
        np.testing.assert_array_equal(addon.read_pixels(image)[4:8, 4:8], pixels[4:8, 4:8])
        assert addon.mesh_signature(mesh) != baseline_uv
        bpy.ops.ed.undo_push(message='UVPT floating composite')
        bpy.ops.ed.undo()
        mesh = bpy.data.meshes['UVPT Test Mesh']
        image = bpy.data.images['UVPT Test Paint']
        bm = bmesh.from_edit_mesh(mesh)
        np.testing.assert_array_equal(addon.read_pixels(image), pixels)
        assert addon.mesh_signature(mesh) == baseline_uv
        bpy.context.scene.uvpt_settings.clear_source = True
        print('PASS floating G/R/S chain, outside return, untouched source until apply, keep-source flag, undo')

        bpy.ops.uv.pixel_transform('INVOKE_DEFAULT', mode='MOVE')
        op = addon._running
        op.offset_x, op.offset_y = 46, 16
        op.preview()
        assert not op.error
        np.testing.assert_array_equal(addon.read_pixels(image), pixels)
        try:
            op.session.commit()
            raise AssertionError('Protected overlap should not apply')
        except addon.TransformError as exc:
            assert 'overlaps' in str(exc)
        np.testing.assert_array_equal(addon.read_pixels(image), pixels)
        op.modal(bpy.context, event('ESC'))
        print('PASS floating overlap allowed while protected commit leaves source untouched')

        bpy.ops.uv.pixel_transform('INVOKE_DEFAULT', mode='MOVE')
        op = addon._running
        op.modal(bpy.context, event('Y'))
        op.modal(bpy.context, event('EIGHT', '8'))
        assert op.modal(bpy.context, event('RET')) == {'FINISHED'}
        np.testing.assert_array_equal(addon.read_pixels(image)[12:16, 4:8], pixels[4:8, 4:8])
        bpy.ops.ed.undo_push(message='UVPT modal move')
        bpy.ops.ed.undo()
        mesh = bpy.data.meshes['UVPT Test Mesh']
        image = bpy.data.images['UVPT Test Paint']
        bm = bmesh.from_edit_mesh(mesh)
        np.testing.assert_array_equal(addon.read_pixels(image), pixels)
        print('PASS numeric axis Move, Enter commit, native undo')

    # A saved file can contain a revision attribute from an older session.
    layer = bm.faces.layers.int.get(addon.REVISION) or bm.faces.layers.int.new(addon.REVISION)
    for face in bm.faces:
        face[layer] = 100
    addon.clear_history(None)
    result = bpy.ops.uv.pixel_transform(offset_x=8)
    assert result == {'FINISHED'}
    assert addon.get_revision(mesh) > 100
    print('PASS saved revision cannot collide with a new session')

addon.unregister()
print('BLENDER INTEGRATION PASSED', bpy.app.version_string)
