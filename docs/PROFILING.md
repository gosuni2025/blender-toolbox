# Profiling: v0.1.1 → v0.2.0

Measured on Blender 5.2.2 LTS, macOS / Metal, using an isolated Blender window and a copy of the test input. The user's working document was not used for benchmark transforms.

## Workload and method

- 1024×512 RGBA texture; 24 selected UV triangles / 48 loops.
- Selected island bounding box approximately 329×196 texture pixels.
- 383 mesh vertices, 302 faces, Mirror modifier, Solid 3D view.
- Move, rotate and scale trajectories, four seconds each; Bilinear sampling and 2-pixel padding.
- Scripted mouse events requested at 120 Hz, subject to Blender's actual event-loop scheduling. Native modal timer events and editor draw callbacks remained active.
- Timers split CPU resampling, padding, pixel-buffer writes, mesh updates, modal input and draw submission. Only frames containing a changed preview were counted as updates.

These are local measurements, not a frame-rate guarantee. Editor draw callbacks measure CPU-side submission, not physical display scan-out or a GPU fence. The profiling callback precedes the floating-layer callback in the same draw pass; the layer's separate CPU submission time is listed below. A screenshot taken during the Move run caused a 63.5 ms outlier, and first-use shader compilation can also pause briefly.

## Measured results

| Metric (median) | v0.1.1 Move / Rotate / Scale | v0.2.0 Move / Rotate / Scale |
| --- | --- | --- |
| Input to updated editor draw | 23.85 / 24.13 / 24.54 ms | **2.96 / 3.23 / 3.27 ms** |
| Updated draw interval | 21.69 / 22.01 / 22.30 ms | **16.65 / 16.68 / 16.64 ms** |
| Updated draw interval, 95th percentile | 22.54 / 24.20 / 23.76 ms | **18.21 / 17.93 / 17.83 ms** |
| New modal input handler | — | 0.50 / 0.52 / 0.52 ms |
| New floating-layer draw submission | — | 0.10 / 0.16 / 0.18 ms |

The v0.1.1 full apply path took approximately 17.4–17.8 ms per preview. Image-buffer writes were only about 0.3 ms. Resampling and padding, rather than uploading the image, were the primary CPU cost. Optimizing those calculations roughly halved their duration, but a second timer gate still introduced uneven frame spacing.

## Changes

1. Edge extension visits only the newly exposed boundary pixels rather than scanning all RGBA pixels eight times per padding step.
2. Premultiplied source colors are cached once; resampling and source erasure allocate and scan less memory.
3. **The release uses a GPU floating layer.** Mouse movement updates a transform matrix immediately. It does not resample the entire image, upload a new image, or modify actual UVs.
4. A GPU-only intermediate and Blender's built-in image shader handle editor display-space conversion. Pixel data never round-trips through the CPU during a gesture.
5. The CPU rasterizer runs once on Apply. This also permits overlap and off-canvas previews while keeping the underlying document intact.
6. The final implementation removes the extra elapsed-time gate from input handling. Blender coalesces draw requests itself.

## Correctness checks

- 20 CPU raster tests cover bounds, transparency, overlap protection, source preservation, concave masks and all four filters.
- Real Blender undo/redo restores UVs and pixels together.
- A floating transaction can move out of the image, rotate, scale and return through G/R/S without changing the source until Apply.
- GPU/CPU sampler comparisons over 1,024 sample positions per filter: maximum absolute premultiplied RGBA error was 0 for Nearest, 6.56×10⁻⁷ for Bilinear, 9.24×10⁻⁷ for Bicubic, and 1.02×10⁻⁶ for Lanczos.
- The editor preview was visually checked. Initial float64 vertex-buffer and framebuffer color-conversion defects were found during QA and corrected before release.

The published benchmark uses Bilinear. Bicubic and Lanczos correctness was tested, but their frame timing has not been separately benchmarked. Larger selections, image sizes, complex scenes and other GPU backends may behave differently.

API references: [Blender 5.2 GPU shader documentation](https://docs.blender.org/api/5.2/gpu.shader.html), [GPU types](https://docs.blender.org/api/5.2/gpu.types.html).
