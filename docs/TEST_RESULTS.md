# Validation — v0.2.0

Environment: Blender 5.2.2 LTS, macOS / Metal, bundled Python 3.13 and NumPy 2.3.4.

## Passed

- **20 CPU tests:** exact translation; scaling and non-square rotation; all four filters; premultiplied-alpha interpolation; alpha compositing; original-pixel preservation; concave masks; source/destination protection; explicit overwrite; off-canvas round trips; invalid bounds and tiny selections.
- **Background Blender integration:** material/UV checks, direct application, cancellation, true Blender undo/redo for UVs and pixels, UV Sync, partial selection expansion and saved revision handling.
- **Isolated GUI integration:** mouse movement, sidebar entry, remembered operator values, numeric input, zero-scale rejection, continuous rotation through 360°, Shift precision, G/R/S chaining outside and back, unchanged source during floating preview, source-preservation option, overlap preview with protected application, Enter, Esc and undo.
- **View navigation during transforms:** wheel, trackpad and middle-button navigation events pass through to Blender; a native zoom followed by pointer motion preserves the floating transform without a jump.
- **GPU/CPU agreement:** all four sampler kernels compared at 1,024 positions with varying color and alpha. Maximum measured difference below 1.1×10⁻⁶ in premultiplied RGBA.
- **Localization:** filter identifiers survive all five translated locale selections; English and Korean UI paths tested. Japanese, simplified/traditional Chinese and Spanish text is supplied; no native-speaker review has been performed.
- **Extension packaging:** Blender's extension manifest validator accepted the package.
- **Visual QA:** live floating preview, painted color, UV wire overlay and native editor rendering checked in an isolated scene. Original working document pixels and UV hashes checked across installation.

See [profiling details](PROFILING.md) for event and draw timings. Other Blender versions, operating systems and GPUs have not been verified.
