"""GPU/CPU filter agreement; called only by the isolated GUI test runner."""
import bpy
import gpu
import numpy as np
from types import SimpleNamespace
from mathutils import Matrix
from gpu_extras.batch import batch_for_shader
import uv_pixel_transform as addon
from uv_pixel_transform.raster import sample

addon.register()
props = bpy.context.scene.uvpt_settings
for language in addon.i18n.LOCALES:
    props.language = language
    props.interpolation = 'LANCZOS3'
    assert props.interpolation == 'LANCZOS3'
    assert addon.i18n.tr('Move UV + Pixels') != 'Move UV + Pixels'
props.language = 'en_US'
print('PASS localized enum values survive all five translated languages')
area = next(a for a in bpy.context.screen.areas if a.type == 'IMAGE_EDITOR')
region = next(r for r in area.regions if r.type == 'WINDOW')
source = np.random.default_rng(53).random((8, 8, 4), dtype=np.float32)
source[..., 3] = source[..., 3] * .6 + .3
premultiplied = source.copy()
premultiplied[..., :3] *= premultiplied[..., 3:4]
session = SimpleNamespace(size=np.array([8,8]), interpolation='BILINEAR',
                          pixels=SimpleNamespace(premultiplied=premultiplied,
                                                 triangles=np.array([[[0,0],[8,0],[8,8]],[[0,0],[8,8],[0,8]]])),
                          bm=SimpleNamespace(faces=[]), chosen=set())
layer = addon.FloatingLayer(session, area, region)
quad = batch_for_shader(layer.shader,'TRI_STRIP',
                        {'position':np.array([[-1,-1],[1,-1],[-1,1],[1,1]],dtype=np.float32),
                         'uv':np.array([[.1,.1],[.9,.1],[.1,.9],[.9,.9]],dtype=np.float32)})
offscreen = gpu.types.GPUOffScreen(32,32,format='RGBA32F')
y,x = np.mgrid[:32,:32]
coordinates = np.column_stack(((.1+(x.ravel()+.5)/32*.8)*8,
                               (.1+(y.ravel()+.5)/32*.8)*8))
try:
    for mode, interpolation in enumerate(('NEAREST','BILINEAR','BICUBIC','LANCZOS3')):
        layer.texture.filter_mode(mode != 0)
        with offscreen.bind():
            gpu.state.viewport_set(0,0,32,32)
            gpu.state.blend_set('NONE')
            gpu.state.depth_test_set('NONE')
            layer.shader.bind()
            layer.shader.uniform_float('MVP',Matrix.Identity(4))
            layer.shader.uniform_bool('linear_display',False)
            layer.shader.uniform_int('sampling_mode',mode)
            layer.shader.uniform_sampler('paint',layer.texture)
            quad.draw(layer.shader)
            actual=np.array(offscreen.texture_color.read(),dtype=np.float32).reshape(-1,4)
        expected=sample(source,coordinates,interpolation,premultiplied)
        expected[:,:3]*=expected[:,3:4]
        np.testing.assert_allclose(actual,expected,atol=2e-5,rtol=1e-4,err_msg=interpolation)
        print('PASS GPU/CPU filter agreement',interpolation, float(np.abs(actual-expected).max()))
finally:
    layer.close()
    offscreen.free()
    addon.unregister()
