"""Run only in an isolated process: blender -b --factory-startup --python-exit-code 1 --python tests/folder_blender_integration.py"""
import sys
import tempfile
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import open_current_folder as addon


def rejected(target, text):
    try:
        addon.resolve_location(target)
    except addon.FolderError as exc:
        assert text in str(exc), str(exc)
    else:
        raise AssertionError('Expected a useful error: ' + text)


addon.register()
assert addon.current_target(bpy.context).kind == 'BLEND'
rejected(addon.Target('BLEND'), 'Save the .blend')
rejected(addon.Target('IMAGE'), 'Choose an image')
generated = bpy.data.images.new('Unsaved paint', width=4, height=4)
rejected(addon.Target('IMAGE', generated), 'no external file')

with tempfile.TemporaryDirectory(prefix='blender-folder-test-') as temp:
    root = Path(temp)
    textures = root / "그림 with spaces ' quotes"
    textures.mkdir()
    image_path = textures / 'paint.png'
    generated.filepath_raw = str(image_path)
    generated.file_format = 'PNG'
    generated.save()
    image = bpy.data.images.load(str(image_path), check_existing=False)
    assert addon.resolve_location(addon.Target('IMAGE', image)).folder == str(textures)
    image.filepath = '//' + str(image_path.relative_to(root))
    rejected(addon.Target('IMAGE', image), 'absolute path')

    blend = root / 'project.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    assert addon.resolve_location(addon.Target('BLEND')).folder == str(root)
    assert addon.resolve_location(addon.Target('IMAGE', image)).filepath == str(image_path)

    # UV mode decides the target even after the workspace is renamed.
    bpy.context.workspace.name = '사용자 지정 작업공간'
    area = next(a for a in bpy.context.screen.areas if a.type == 'VIEW_3D')
    area.type = 'IMAGE_EDITOR'
    area.ui_type = 'UV'
    area.spaces.active.image = image
    properties = next(a for a in bpy.context.screen.areas if a.type == 'PROPERTIES')
    with bpy.context.temp_override(area=properties):
        assert addon.current_target(bpy.context).image == image
        opened = []
        original_open = addon.open_folder
        addon.open_folder = lambda path: opened.append(path) or {'FINISHED'}
        assert bpy.ops.wm.open_current_file_folder() == {'FINISHED'}
        assert opened == [str(textures)]
        addon.open_folder = original_open
    with bpy.context.temp_override(area=area):
        assert addon.current_target(bpy.context).image == image
        assert addon.current_target(bpy.context).image_user == area.spaces.active.image_user

    # A missing image in UV mode must not silently open the blend's directory.
    area.spaces.active.image = None
    with bpy.context.temp_override(area=properties):
        rejected(addon.current_target(bpy.context), 'Choose an image')
    area.spaces.active.image = image

    # Multiple UV/image panes require disambiguation from the desired Image menu.
    second = next(a for a in bpy.context.screen.areas if a.type == 'OUTLINER')
    second.type = 'IMAGE_EDITOR'
    second.ui_type = 'UV'
    second.spaces.active.image = generated
    with bpy.context.temp_override(area=properties):
        try:
            addon.current_target(bpy.context)
        except addon.FolderError as exc:
            assert 'Several images' in str(exc)
        else:
            raise AssertionError('Do not guess between distinct UV images')
    with bpy.context.temp_override(area=second):
        assert addon.current_target(bpy.context).image == generated
    second.type = 'OUTLINER'

    # Active material paint slots take priority over a pinned reference editor.
    area.type = 'VIEW_3D'
    obj = bpy.context.active_object
    material = bpy.data.materials.new('Paint slots')
    material.use_nodes = True
    node = material.node_tree.nodes.new('ShaderNodeTexImage')
    node.image = image
    material.node_tree.nodes.active = node
    obj.data.materials.clear()
    obj.data.materials.append(material)
    bpy.context.view_layer.update()
    with bpy.context.temp_override(area=area):
        bpy.ops.object.mode_set(mode='TEXTURE_PAINT')
        assert addon.current_target(bpy.context).image == image
        settings = bpy.context.scene.tool_settings.image_paint
        settings.mode = 'IMAGE'
        settings.canvas = generated
        assert addon.current_target(bpy.context).image == generated
        bpy.ops.object.mode_set(mode='OBJECT')
        assert addon.current_target(bpy.context).kind == 'BLEND'

    # Missing image file vs missing directory; packed-only has no external file.
    image.pack()
    image_path.unlink()
    rejected(addon.Target('IMAGE', image), 'packed only')
    image.unpack(method='REMOVE')
    assert addon.resolve_location(addon.Target('IMAGE', image)).missing
    image.filepath = str(root / 'missing folder' / 'paint.png')
    rejected(addon.Target('IMAGE', image), 'folder does not exist')

    # Linked-image relative paths are based on their library, not the current blend.
    library_dir = root / 'library'
    library_dir.mkdir()
    linked_path = library_dir / 'linked.png'
    generated.filepath_raw = str(linked_path)
    generated.save()
    linked_source = bpy.data.images.load(str(linked_path), check_existing=False)
    linked_source.name = 'Linked paint'
    linked_source.filepath = '//linked.png'
    library = library_dir / 'assets.blend'
    bpy.data.libraries.write(str(library), {linked_source}, path_remap='NONE')
    bpy.data.images.remove(linked_source)
    with bpy.data.libraries.load(str(library), link=True) as (source, target):
        target.images = ['Linked paint']
    linked = target.images[0]
    assert addon.resolve_location(addon.Target('IMAGE', linked)).folder == str(library_dir)

addon.unregister()
addon.register()
addon.unregister()
print('PASS folder selection, file-menu operator, UV/image context, texture paint canvas and material slots, renamed workspace, relative and linked paths, Unicode, unsaved/packed/missing files, registration lifecycle')
