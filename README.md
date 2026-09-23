# Blender Toolbox

Small Blender utilities by **gosuni2025**. Install each tool separately as a Blender extension.

**Blender 5.2+ · GPL-3.0-or-later**

## Tools

| Tool | What it does | Install / guide |
| --- | --- | --- |
| **Open Current Folder** | Opens the current `.blend` or image folder in Finder, Explorer or your Linux file manager | [Download 0.1.0](https://github.com/gosuni2025/blender-toolbox/releases/tag/open-current-folder-v0.1.0) · [Guide / 한국어](docs/OPEN_CURRENT_FOLDER.md) |
| **UV Pixel Transform** | Moves, scales and rotates UV islands together with their painted pixels | [Download 0.2.0](https://github.com/gosuni2025/blender-toolbox/releases/tag/v0.2.0) · [Guide](docs/UV_PIXEL_TRANSFORM.md) · [한국어](docs/README.ko.md) |

## Open Current Folder

Choose the new folder command at the bottom of Blender's **File** menu:

- **Layout / normal 3D work:** **Open .blend Folder** opens the saved project folder.
- **UV Editing:** **Open Image Folder** opens the displayed image's folder.
- **Texture Paint:** it opens the active paint canvas or material paint image's folder.
- In an **Image Editor**, use **Image → Open Image Folder**, or **F3 → Open Current File Folder**, to target that editor's displayed image directly.

It uses editor roles and paint targets, so renaming a workspace does not break the choice. If several UV images are open, choose the desired editor's Image menu. Unsaved/generated images and images stored only inside a `.blend` receive an explanation instead of opening an unrelated folder. Relative image paths are resolved against the `.blend` or linked library.

**한국어:** 설치 후 **파일 → .blend 파일 폴더 열기 / 이미지 폴더 열기**를 사용하세요. Layout에서는 프로젝트 폴더, Texture Paint·UV에서는 작업 이미지 폴더를 엽니다. 애드온 설정의 **Language → 한국어**로 메뉴 언어를 지정할 수 있습니다.

## UV Pixel Transform demo

[![UV islands and painted pixels moving together](docs/media/demo.gif)](docs/media/demo.mp4)

[720p / 24 fps MP4](docs/media/demo.mp4), about **0.54 MB** from a 38 MB recording. This video shows the earlier 0.1.1 development build; 0.2.0 adds floating GPU layers, off-canvas transforms, four filters, view navigation and six UI languages. [Full guide](docs/UV_PIXEL_TRANSFORM.md) · [Profiling](docs/PROFILING.md).

## Install

1. Download the selected tool's extension ZIP from its release above.
2. In Blender, open **Edit → Preferences → Add-ons → dropdown → Install from Disk…**.
3. Select the ZIP and enable the extension. Install either or both tools.

Use the extension ZIP, not GitHub's automatic source archive. Neither tool needs a network connection. Both provide English, Korean, Japanese, Simplified Chinese, Traditional Chinese and Spanish UI.

## Development and validation

Each top-level package is independently installable:

```text
open_current_folder/   File and image folder utility
uv_pixel_transform/    Painted UV transforms
tests/                 CPU and isolated Blender integration tests
docs/                  Guides, measurements and demonstration media
```

```sh
python -m pip install numpy
python -m unittest discover -s tests -v
blender -b --factory-startup --python-exit-code 1 --python tests/folder_blender_integration.py
blender -b --factory-startup --python-exit-code 1 --python tests/blender_integration.py
blender --factory-startup --python tests/run_gui_tests.py
blender --command extension validate open_current_folder
blender --command extension build --source-dir open_current_folder --output-dir dist
```

Integration tests build temporary scenes and must run in their own factory-startup Blender process. Tested on Blender 5.2.2 LTS / macOS; Windows and Linux file-manager launching use Blender's native API and have not been tested here. [Validation details](docs/TEST_RESULTS.md).

Previously named `uv-pixel-transform`; existing UV tool releases and Git history are retained. Source code is **GPL-3.0-or-later**. Demonstration footage and artwork are separate from the source-code license.
