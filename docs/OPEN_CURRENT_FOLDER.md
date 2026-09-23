# Open Current Folder 0.1.0

[Download extension ZIP](https://github.com/gosuni2025/blender-toolbox/releases/tag/open-current-folder-v0.1.0) · [Toolbox](../README.md)

Open the directory containing the current file in the operating system's file manager. This command opens a folder; it does not save, export, unpack or reload the file.

## Usage

Install `open_current_folder-0.1.0.zip` with **Preferences → Add-ons → dropdown → Install from Disk…**.

Use the command at the bottom of **File**:

| Context | Menu label / target |
| --- | --- |
| Layout and normal 3D work | **Open .blend Folder** → saved `.blend` |
| UV workspace | **Open Image Folder** → image displayed in the UV Editor |
| Texture Paint | **Open Image Folder** → active image canvas or active material paint slot; falls back to a paint editor if no paint target is available |
| Image Editor's **Image** menu or F3 search | The image displayed in that particular editor |

**F3 → Open Current File Folder** also runs the command. The menu label changes according to the target. Renamed workspaces work because selection uses editor types and the active painting mode.

Language can be set under **Preferences → Add-ons → Open Current Folder → Language**: Auto, English, 한국어, 日本語, 简体中文, 繁體中文, Español. Auto follows Blender. Menu text and normal error messages use the selected language; Blender's own UI uses Blender's language settings.

## Path handling

- Relative `//` image paths are based on the saved `.blend`; linked images use the library file's location.
- A saved external image can be opened even when the `.blend` has not been saved.
- Unsaved `.blend` files and generated/viewer images without an external file show an explanation.
- Packed images use their original external file when it exists. Packed-only images must be saved or unpacked first.
- If the file is missing but its folder exists, the folder opens with a warning. Missing folders are reported without creating anything.
- Multiple distinct UV/paint images in the same screen require choosing the desired editor's **Image** menu. The active paint canvas takes priority in Texture Paint; a directly invoked Image Editor command always uses its own image.

Finder on macOS, Explorer on Windows and the Linux default file manager are selected by Blender's `wm.path_open` operator. The extension passes a folder path without constructing shell commands. Opening a folder does not save unsaved image edits.

## 한국어

**파일 메뉴 맨 아래**에 폴더 열기가 추가됩니다.

- **Layout:** `.blend 파일 폴더 열기` — 현재 프로젝트의 저장 폴더
- **Texture Paint:** `이미지 폴더 열기` — 현재 칠하는 캔버스/머티리얼 이미지의 폴더
- **UV Editing:** `이미지 폴더 열기` — UV 에디터에 표시 중인 이미지의 폴더
- 여러 이미지가 열려 있다면 원하는 에디터의 **이미지 → 이미지 폴더 열기**를 사용하세요.
- **F3 → Open Current File Folder**로도 실행할 수 있습니다.

macOS는 Finder, Windows는 탐색기에서 폴더를 엽니다. 애드온 설정의 **Language → 한국어**로 이 도구의 메뉴만 한국어로 바꿀 수 있습니다.

아직 저장하지 않은 파일은 먼저 저장하라는 안내가 나옵니다. `.blend` 안에만 포함된 이미지는 외부 파일로 저장하거나 압축을 해제해야 합니다. `//` 상대 경로와 연결된 라이브러리의 이미지 경로도 처리합니다. 폴더 열기는 파일 저장을 대신하지 않습니다.

## Verification

Blender 5.2.2 LTS on macOS: context selection, native Finder launch, active paint slots/canvas, renamed workspaces, relative and linked-library paths, Unicode and spaces, missing/unsaved/packed files, and repeated registration. See [validation](TEST_RESULTS.md). Windows and Linux have not been run in this environment.
