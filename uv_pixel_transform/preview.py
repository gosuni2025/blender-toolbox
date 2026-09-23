# SPDX-License-Identifier: GPL-3.0-or-later
"""GPU floating layer. Neither image pixels nor mesh UVs change during a gesture."""
import bpy
import gpu
import numpy as np
from mathutils import Matrix
from gpu_extras.batch import batch_for_shader


def transform_matrix(matrix):
    return Matrix(((matrix[0, 0], matrix[0, 1], 0, matrix[0, 2]),
                   (matrix[1, 0], matrix[1, 1], 0, matrix[1, 2]),
                   (0, 0, 1, 0), (0, 0, 0, 1)))


class FloatingLayer:
    def __init__(self, session, area, region):
        self.session, self.area, self.region = session, area, region
        self.matrix = np.eye(3)
        self.error = None
        self.handler = None
        self.space = area.spaces.active
        self.show_uv = self.space.uv_editor.show_uv
        interface = gpu.types.GPUStageInterfaceInfo('uvpt_layer_interface')
        interface.smooth('VEC2', 'source_uv')
        info = gpu.types.GPUShaderCreateInfo()
        info.push_constant('MAT4', 'MVP')
        info.push_constant('BOOL', 'linear_display')
        info.push_constant('INT', 'sampling_mode')
        info.sampler(0, 'FLOAT_2D', 'paint')
        info.vertex_in(0, 'VEC2', 'position')
        info.vertex_in(1, 'VEC2', 'uv')
        info.vertex_out(interface)
        info.fragment_out(0, 'VEC4', 'out_color')
        info.vertex_source('''void main() {
            source_uv = uv;
            gl_Position = MVP * vec4(position, 0.0, 1.0);
        }''')
        info.fragment_source('''
        float weight(float distance_value) {
            float x = abs(distance_value);
            if (sampling_mode == 2) {
                if (x <= 1.0) return (1.5*x - 2.5)*x*x + 1.0;
                if (x < 2.0) return ((-0.5*x + 2.5)*x - 4.0)*x + 2.0;
                return 0.0;
            }
            if (x < 0.000001) return 1.0;
            if (x >= 3.0) return 0.0;
            float pi_x = 3.141592653589793*x;
            return sin(pi_x)*sin(pi_x/3.0)/(pi_x*pi_x/3.0);
        }
        vec4 sample_paint() {
            if (sampling_mode == 0) return texture(paint, source_uv);
            ivec2 image_size = textureSize(paint, 0);
            vec2 pixel = source_uv * vec2(image_size) - vec2(0.5);
            ivec2 base = ivec2(floor(pixel));
            vec2 fraction_value = pixel - vec2(base);
            if (sampling_mode == 1) {
                ivec2 end_pixel = image_size-ivec2(1);
                vec4 a = texelFetch(paint,clamp(base,ivec2(0),end_pixel),0);
                vec4 b = texelFetch(paint,clamp(base+ivec2(1,0),ivec2(0),end_pixel),0);
                vec4 c = texelFetch(paint,clamp(base+ivec2(0,1),ivec2(0),end_pixel),0);
                vec4 d = texelFetch(paint,clamp(base+ivec2(1,1),ivec2(0),end_pixel),0);
                return mix(mix(a,b,fraction_value.x),mix(c,d,fraction_value.x),fraction_value.y);
            }
            vec4 color_value = vec4(0.0);
            float total = 0.0;
            for (int y = -2; y <= 3; y++) {
                for (int x = -2; x <= 3; x++) {
                    float w = weight(fraction_value.x-float(x))*weight(fraction_value.y-float(y));
                    ivec2 pixel_index = clamp(base + ivec2(x,y), ivec2(0), image_size-ivec2(1));
                    color_value += texelFetch(paint, pixel_index, 0)*w;
                    total += w;
                }
            }
            color_value /= total;
            if (color_value.a > 0.00000001) color_value.rgb *= clamp(color_value.a,0.0,1.0)/color_value.a;
            else color_value.rgb = vec3(0.0);
            color_value.a = clamp(color_value.a,0.0,1.0);
            return color_value;
        }
        void main() {
            vec4 c = sample_paint();
            if (linear_display && c.a > 0.00000001) {
                vec3 rgb = max(c.rgb / c.a, vec3(0.0));
                vec3 high = 1.055 * pow(rgb, vec3(1.0 / 2.4)) - 0.055;
                rgb = mix(high, rgb * 12.92, lessThanEqual(rgb, vec3(0.0031308)));
                c.rgb = rgb * c.a;
            }
            out_color = c;
        }''')
        self.shader = gpu.shader.create_from_info(info)
        pixels = np.ascontiguousarray(session.pixels.premultiplied).reshape(-1)
        self.texture = gpu.types.GPUTexture(tuple(int(n) for n in session.size), format='RGBA32F',
                                            data=gpu.types.Buffer('FLOAT', len(pixels), pixels))
        self.texture.filter_mode(session.interpolation != 'NEAREST')
        self.texture.extend_mode('EXTEND')
        points = session.pixels.triangles.reshape(-1, 2).astype(np.float32)
        self.paint_batch = batch_for_shader(self.shader, 'TRIS',
                                             {'position': points, 'uv': (points / session.size).astype(np.float32)})
        self.line_shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        # Blender 5.2's built-in IMAGE shader performs the editor framebuffer's
        # display-space conversion. Custom shaders cannot import that private
        # color-space helper, so composite through a GPU-only intermediate.
        self.display_shader = gpu.shader.from_builtin('IMAGE')
        self.display_batch = batch_for_shader(self.display_shader, 'TRI_STRIP',
                                              {'pos': [(-1,-1),(1,-1),(-1,1),(1,1)],
                                               'texCoord': [(0,0),(1,0),(0,1),(1,1)]})
        self.canvas = None
        self.canvas_size = None
        self.edges = []
        for selected in (False, True):
            edges = []
            for face in session.bm.faces:
                if (face.index in session.chosen) != selected or face.hide:
                    continue
                for loop in face.loops:
                    for endpoint in (loop, loop.link_loop_next):
                        co = np.asarray(endpoint[session.uv].uv[:]) * session.size
                        edges.append((*co, 0))
            self.edges.append(batch_for_shader(self.line_shader, 'LINES', {'pos': edges}) if edges else None)
        self.space.uv_editor.show_uv = False
        self.handler = bpy.types.SpaceImageEditor.draw_handler_add(self.draw, (), 'WINDOW', 'POST_PIXEL')

    def set_matrix(self, matrix):
        self.matrix = matrix.copy()
        self.area.tag_redraw()

    def draw(self):
        if bpy.context.area != self.area or bpy.context.region != self.region or self.error:
            return
        previous_blend = gpu.state.blend_get()
        previous_depth = gpu.state.depth_test_get()
        previous_viewport = gpu.state.viewport_get()
        try:
            lo = np.array(self.region.view2d.region_to_view(0, 0))
            hi = np.array(self.region.view2d.region_to_view(self.region.width, self.region.height))
            span = hi - lo
            view = Matrix(((2 / (span[0] * self.session.size[0]), 0, 0, -1 - 2 * lo[0] / span[0]),
                           (0, 2 / (span[1] * self.session.size[1]), 0, -1 - 2 * lo[1] / span[1]),
                           (0, 0, 1, 0), (0, 0, 0, 1)))
            model = transform_matrix(self.matrix)
            gpu.state.depth_test_set('NONE')
            if self.session.show_preview:
                size = (self.region.width, self.region.height)
                if self.canvas_size != size:
                    if self.canvas is not None:
                        self.canvas.free()
                    self.canvas = gpu.types.GPUOffScreen(*size, format='RGBA32F')
                    self.canvas_size = size
                viewport = gpu.state.viewport_get()
                with self.canvas.bind():
                    gpu.state.viewport_set(0, 0, *size)
                    gpu.state.active_framebuffer_get().clear(color=(0,0,0,0))
                    gpu.state.blend_set('NONE')
                    self.shader.bind()
                    self.shader.uniform_float('MVP', view @ model)
                    # Float buffer precision does not identify the color space:
                    # foreach_set may promote an sRGB byte image to float.
                    self.shader.uniform_bool('linear_display', self.session.image.colorspace_settings.name
                                             in {'Linear', 'Linear Rec.709', 'Linear Rec709'})
                    self.shader.uniform_int('sampling_mode', {'NEAREST':0,'BILINEAR':1,'BICUBIC':2,'LANCZOS3':3}[self.session.interpolation])
                    self.shader.uniform_sampler('paint', self.texture)
                    self.paint_batch.draw(self.shader)
                gpu.state.viewport_set(*viewport)
                gpu.state.blend_set('ALPHA_PREMULT')
                with gpu.matrix.push_pop():
                    gpu.matrix.load_matrix(Matrix.Identity(4))
                    gpu.matrix.load_projection_matrix(Matrix.Identity(4))
                    self.display_shader.bind()
                    self.display_shader.uniform_sampler('image', self.canvas.texture_color)
                    self.display_batch.draw(self.display_shader)
            gpu.state.blend_set('ALPHA')
            if self.show_uv:
                for selected, batch in enumerate(self.edges):
                    if batch is None:
                        continue
                    with gpu.matrix.push_pop():
                        gpu.matrix.load_matrix(view @ model if selected else view)
                        gpu.matrix.load_projection_matrix(Matrix.Identity(4))
                        self.line_shader.bind()
                        self.line_shader.uniform_float('viewportSize', gpu.state.viewport_get()[2:])
                        self.line_shader.uniform_float('lineWidth', 2.5 if selected else 2)
                        self.line_shader.uniform_float('color', (0.05, 0.05, 0.05, 1))
                        batch.draw(self.line_shader)
                        self.line_shader.uniform_float('lineWidth', 1.2 if selected else .7)
                        self.line_shader.uniform_float('color', (1, .45, .05, 1) if selected else (.65, .65, .65, 1))
                        batch.draw(self.line_shader)
        except Exception as exc:
            self.error = str(exc)
        finally:
            gpu.state.viewport_set(*previous_viewport)
            gpu.state.blend_set(previous_blend)
            gpu.state.depth_test_set(previous_depth)

    def close(self):
        if self.handler is not None:
            bpy.types.SpaceImageEditor.draw_handler_remove(self.handler, 'WINDOW')
            self.handler = None
        try:
            self.space.uv_editor.show_uv = self.show_uv
            self.area.tag_redraw()
        except ReferenceError:
            pass
        self.texture = None
        if self.canvas is not None:
            self.canvas.free()
            self.canvas = None
