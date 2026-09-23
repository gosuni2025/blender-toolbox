# SPDX-License-Identifier: GPL-3.0-or-later
import bpy

LANGUAGES = [('AUTO', 'Auto', 'Follow Blender'), ('en_US', 'English', 'English'),
             ('ko_KR', '한국어', '한국어'), ('ja_JP', '日本語', '日本語'),
             ('zh_HANS', '简体中文', '简体中文'), ('zh_HANT', '繁體中文', '繁體中文'),
             ('es', 'Español', 'Español')]
ROWS = {
'Language': ('언어', '言語', '语言', '語言', 'Idioma'),
'Open Current File Folder': ('현재 파일 폴더 열기', '現在のファイルのフォルダーを開く', '打开当前文件所在文件夹', '開啟目前檔案所在資料夾', 'Abrir carpeta del archivo actual'),
'Open Image Folder': ('이미지 폴더 열기', '画像のフォルダーを開く', '打开图像所在文件夹', '開啟影像所在資料夾', 'Abrir carpeta de la imagen'),
'Open .blend Folder': ('.blend 파일 폴더 열기', '.blendのフォルダーを開く', '打开 .blend 所在文件夹', '開啟 .blend 所在資料夾', 'Abrir carpeta del .blend'),
'File → Open Current File Folder': ('파일 → 현재 파일 폴더 열기', 'ファイル → 現在のファイルのフォルダーを開く', '文件 → 打开当前文件所在文件夹', '檔案 → 開啟目前檔案所在資料夾', 'Archivo → Abrir carpeta del archivo actual'),
'Open the current blend or image folder in the system file manager': ('현재 .blend 또는 이미지의 폴더를 시스템 파일 탐색기로 엽니다', '現在の.blendまたは画像のフォルダーをファイルマネージャーで開きます', '在系统文件管理器中打开当前 .blend 或图像所在文件夹', '在系統檔案管理員中開啟目前 .blend 或影像所在資料夾', 'Abre la carpeta del .blend o imagen actual en el gestor de archivos'),
'Save the .blend file first.': ('먼저 .blend 파일을 저장하세요.', '先に.blendファイルを保存してください。', '请先保存 .blend 文件。', '請先儲存 .blend 檔案。', 'Guarda primero el archivo .blend.'),
'Choose an image in the UV or Image Editor first.': ('먼저 UV 또는 이미지 에디터에서 이미지를 선택하세요.', '先にUVまたは画像エディターで画像を選択してください。', '请先在 UV 或图像编辑器中选择图像。', '請先在 UV 或影像編輯器中選取影像。', 'Elige una imagen en el editor UV o de imágenes primero.'),
'This image has no external file. Save it first.': ('이 이미지는 외부 파일이 없습니다. 먼저 이미지를 저장하세요.', 'この画像には外部ファイルがありません。先に保存してください。', '此图像没有外部文件。请先保存图像。', '此影像沒有外部檔案。請先儲存影像。', 'Esta imagen no tiene archivo externo. Guárdala primero.'),
'Save the .blend file or give this image an absolute path first.': ('먼저 .blend를 저장하거나 이미지에 절대 경로를 지정하세요.', '先に.blendを保存するか画像の絶対パスを指定してください。', '请先保存 .blend 或为图像指定绝对路径。', '請先儲存 .blend 或為影像指定絕對路徑。', 'Guarda el .blend o asigna una ruta absoluta a la imagen primero.'),
'This image is packed only. Save or unpack it to an external file first.': ('이 이미지는 .blend 안에만 포함되어 있습니다. 먼저 외부 파일로 저장하거나 압축을 해제하세요.', 'この画像は.blend内にのみパックされています。先に外部ファイルへ保存または展開してください。', '此图像仅打包在 .blend 中。请先保存或解包为外部文件。', '此影像僅封裝在 .blend 中。請先儲存或解封裝為外部檔案。', 'Esta imagen solo está empaquetada. Guárdala o desempaquétala como archivo externo primero.'),
'Several images are open. Use the Image menu in the desired editor.': ('여러 이미지가 열려 있습니다. 원하는 에디터의 이미지 메뉴에서 실행하세요.', '複数の画像が開いています。対象エディターの画像メニューから実行してください。', '已打开多张图像。请使用目标编辑器的图像菜单。', '已開啟多張影像。請使用目標編輯器的影像選單。', 'Hay varias imágenes abiertas. Usa el menú Imagen del editor deseado.'),
'The file path is not absolute. Save the file first.': ('파일 경로가 확정되지 않았습니다. 먼저 파일을 저장하세요.', 'ファイルパスが絶対パスではありません。先に保存してください。', '文件路径不是绝对路径。请先保存文件。', '檔案路徑不是絕對路徑。請先儲存檔案。', 'La ruta no es absoluta. Guarda el archivo primero.'),
'The containing folder does not exist: {path}': ('폴더가 존재하지 않습니다: {path}', 'フォルダーが存在しません：{path}', '所在文件夹不存在：{path}', '所在資料夾不存在：{path}', 'La carpeta no existe: {path}'),
'The system file manager could not open this folder.': ('시스템 파일 탐색기로 이 폴더를 열지 못했습니다.', 'ファイルマネージャーでフォルダーを開けませんでした。', '系统文件管理器无法打开此文件夹。', '系統檔案管理員無法開啟此資料夾。', 'El gestor de archivos no pudo abrir esta carpeta.'),
'Opened the folder, but the file is missing on disk.': ('폴더를 열었습니다. 해당 파일은 디스크에 없습니다.', 'フォルダーを開きましたがファイルはディスクにありません。', '已打开文件夹，但磁盘上缺少该文件。', '已開啟資料夾，但磁碟上缺少該檔案。', 'Se abrió la carpeta, pero el archivo no está en el disco.'),
}
LOCALES = ('ko_KR', 'ja_JP', 'zh_HANS', 'zh_HANT', 'es')
TABLES = {locale: {key: values[i] for key, values in ROWS.items()} for i, locale in enumerate(LOCALES)}
ALIASES = {'zh_CN': 'zh_HANS', 'zh_TW': 'zh_HANT', 'es_ES': 'es'}


def tr(message, context=None):
    context = context or bpy.context
    addon = context.preferences.addons.get(__package__)
    value = addon.preferences.language if addon else 'AUTO'
    if value == 'AUTO':
        value = context.preferences.view.language
        if value == 'DEFAULT':
            value = bpy.app.translations.locale
    return TABLES.get(ALIASES.get(value, value), {}).get(message, message)


def register():
    translations = {locale: {(context, key): value for key, value in table.items()
                             for context in ('*', 'Operator')} for locale, table in TABLES.items()}
    for alias, locale in ALIASES.items():
        translations[alias] = translations[locale]
    bpy.app.translations.register(__name__, translations)


def unregister():
    bpy.app.translations.unregister(__name__)
