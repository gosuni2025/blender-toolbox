# SPDX-License-Identifier: GPL-3.0-or-later
"""Open the current .blend or image folder in the operating system file manager."""

import os
from dataclasses import dataclass

import bpy
from bpy.props import EnumProperty

from . import i18n
from .i18n import tr


class FolderError(ValueError):
    pass


@dataclass(frozen=True)
class Target:
    kind: str
    image: object = None
    image_user: object = None


@dataclass(frozen=True)
class Location:
    filepath: str
    folder: str
    missing: bool


def paint_target(context):
    settings = context.scene.tool_settings.image_paint
    if settings.mode == 'IMAGE':
        return settings.canvas
    obj = context.active_object
    material = obj.active_material if obj else None
    if material:
        images = material.texture_paint_images
        index = material.paint_active_slot
        if 0 <= index < len(images):
            return images[index]
    return None


def current_target(context):
    """Use editor roles and the active paint canvas, independent of workspace names."""
    area = context.area
    if area and area.type == 'IMAGE_EDITOR':
        space = area.spaces.active
        return Target('IMAGE', space.image, space.image_user)

    painting = context.mode == 'PAINT_TEXTURE'
    if painting:
        image = paint_target(context)
        if image:
            return Target('IMAGE', image)

    editors = [a.spaces.active for a in context.screen.areas
               if a.type == 'IMAGE_EDITOR' and
               (a.ui_type == 'UV' or a.spaces.active.ui_mode == 'PAINT')] if context.screen else []
    if editors:
        images = {space.image.as_pointer(): space for space in editors if space.image}
        if len(images) > 1:
            raise FolderError('Several images are open. Use the Image menu in the desired editor.')
        if images:
            space = next(iter(images.values()))
            return Target('IMAGE', space.image, space.image_user)
        return Target('IMAGE')
    return Target('IMAGE' if painting else 'BLEND')


def resolve_location(target):
    if target.kind == 'BLEND':
        if not bpy.data.filepath:
            raise FolderError('Save the .blend file first.')
        filepath = bpy.data.filepath
    else:
        image = target.image
        if image is None:
            raise FolderError('Choose an image in the UV or Image Editor first.')
        if image.source in {'GENERATED', 'VIEWER'} or not image.filepath:
            raise FolderError('This image has no external file. Save it first.')
        if image.filepath.startswith('//') and not image.library and not bpy.data.filepath:
            raise FolderError('Save the .blend file or give this image an absolute path first.')
        filepath = image.filepath_from_user(image_user=target.image_user)
        filepath = bpy.path.abspath(filepath, library=image.library)
        if (image.packed_file or len(image.packed_files)) and not os.path.isfile(filepath):
            raise FolderError('This image is packed only. Save or unpack it to an external file first.')

    filepath = os.path.normpath(filepath)
    if not os.path.isabs(filepath):
        raise FolderError('The file path is not absolute. Save the file first.')
    folder = os.path.dirname(filepath)
    if not os.path.isdir(folder):
        raise FolderError('The containing folder does not exist: {path}'.format(path=folder))
    return Location(filepath, folder, not os.path.isfile(filepath))


def open_folder(folder):
    # Blender handles Finder, Explorer and the Linux default file manager.
    # Pass a folder path, never a shell command or the image file itself.
    return bpy.ops.wm.path_open(filepath=folder)


class OCF_Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    language: EnumProperty(name='Language', items=i18n.LANGUAGES, default='AUTO')

    def draw(self, context):
        self.layout.prop(self, 'language', text=tr('Language', context), translate=False)
        self.layout.label(text=tr('File → Open Current File Folder', context), translate=False)


class OCF_OT_open_current_folder(bpy.types.Operator):
    bl_idname = 'wm.open_current_file_folder'
    bl_label = 'Open Current File Folder'
    bl_description = 'Open the current blend or image folder in the system file manager'
    bl_options = set()

    def execute(self, context):
        try:
            location = resolve_location(current_target(context))
            if 'FINISHED' not in open_folder(location.folder):
                raise FolderError('The system file manager could not open this folder.')
        except (FolderError, RuntimeError, OSError) as exc:
            message = str(exc)
            prefix = 'The containing folder does not exist: '
            if message.startswith(prefix):
                message = tr('The containing folder does not exist: {path}', context).format(path=message[len(prefix):])
            else:
                message = tr(message, context)
            self.report({'WARNING'}, message)
            return {'CANCELLED'}
        if location.missing:
            self.report({'WARNING'}, tr('Opened the folder, but the file is missing on disk.', context))
        return {'FINISHED'}


def file_menu(self, context):
    try:
        kind = current_target(context).kind
        label = 'Open Image Folder' if kind == 'IMAGE' else 'Open .blend Folder'
    except FolderError:
        label = 'Open Current File Folder'
    self.layout.separator()
    self.layout.operator('wm.open_current_file_folder', text=tr(label, context), icon='FILE_FOLDER', translate=False)


CLASSES = (OCF_Preferences, OCF_OT_open_current_folder)


def register():
    i18n.register()
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file.append(file_menu)
    bpy.types.IMAGE_MT_image.append(file_menu)


def unregister():
    bpy.types.IMAGE_MT_image.remove(file_menu)
    bpy.types.TOPBAR_MT_file.remove(file_menu)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    i18n.unregister()
