# Blender Toolbox validation

Environment: Blender 5.2.2 LTS, macOS / Metal, bundled Python 3.13 and NumPy 2.3.4.

## UV Pixel Transform 0.2.0

- **20 CPU tests:** exact translation; scaling and non-square rotation; all four filters; premultiplied-alpha interpolation; alpha compositing; original-pixel preservation; concave masks; source/destination protection; explicit overwrite; off-canvas round trips; invalid bounds and tiny selections.
- **Background Blender integration:** material/UV checks, direct application, cancellation, true Blender undo/redo for UVs and pixels, UV Sync, partial selection expansion and saved revision handling.
- **Isolated GUI integration:** mouse movement, sidebar entry, remembered operator values, numeric input, zero-scale rejection, continuous rotation through 360°, Shift precision, G/R/S chaining outside and back, unchanged source during floating preview, source-preservation option, overlap preview with protected application, Enter, Esc and undo.
- **View navigation during transforms:** wheel, trackpad and middle-button navigation events pass through to Blender; a native zoom followed by pointer motion preserves the floating transform without a jump.
- **GPU/CPU agreement:** all four sampler kernels compared at 1,024 positions with varying color and alpha. Maximum measured difference below 1.1×10⁻⁶ in premultiplied RGBA.
- **Localization:** filter identifiers survive all five translated locale selections; English and Korean UI paths tested. Japanese, simplified/traditional Chinese and Spanish text is supplied; no native-speaker review has been performed.
- **Extension packaging:** Blender's extension manifest validator accepted the package.
- **Visual QA:** live floating preview, painted color, UV wire overlay and native editor rendering checked in an isolated scene. Original working document pixels and UV hashes checked across installation.

See [profiling details](PROFILING.md) for event and draw timings. Other Blender versions, operating systems and GPUs have not been verified.

## Open Current Folder 0.1.0

- Isolated Blender integration: normal 3D work resolves the `.blend`; UV/image editors resolve their own image; Texture Paint resolves the active material slot or single-image canvas.
- File-menu operator passes the resolved directory to the native folder opener. Multiple distinct UV images require choosing an editor; a missing image does not fall back to an unrelated `.blend` directory.
- Workspace renaming, Unicode/space/quote paths, `//` relative paths and linked-library image paths are covered.
- Unsaved `.blend`, generated images, relative paths without a saved project, packed-only images, missing files and missing directories are covered.
- Repeated register/unregister cycle and Blender extension manifest validation pass.
- Native file-manager launch is checked on macOS. Windows/Linux launching relies on Blender's native `wm.path_open` and has not been run here.
