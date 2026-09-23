# SPDX-License-Identifier: GPL-3.0-or-later
"""Addon-local language selection plus Blender's native translation registry."""
import bpy

LANGUAGES = [('AUTO', 'Auto', 'Follow Blender'), ('en_US', 'English', 'English'),
             ('ko_KR', '한국어', '한국어'), ('ja_JP', '日本語', '日本語'),
             ('zh_HANS', '简体中文', '简体中文'), ('zh_HANT', '繁體中文', '繁體中文'),
             ('es', 'Español', 'Español')]
# Message: Korean, Japanese, simplified Chinese, traditional Chinese, Spanish.
ROWS = {
'Language': ('언어', '言語', '语言', '語言', 'Idioma'),
'Move UV + Pixels': ('UV와 그림 이동', 'UVとピクセルを移動', '移动 UV 和像素', '移動 UV 與像素', 'Mover UV y píxeles'),
'Scale UV + Pixels': ('UV와 그림 확대·축소', 'UVとピクセルを拡大縮小', '缩放 UV 和像素', '縮放 UV 與像素', 'Escalar UV y píxeles'),
'Rotate UV + Pixels': ('UV와 그림 회전', 'UVとピクセルを回転', '旋转 UV 和像素', '旋轉 UV 與像素', 'Rotar UV y píxeles'),
'Precise Transform…': ('수치로 변환…', '数値で変形…', '精确变换…', '精確變換…', 'Transformación precisa…'),
'Sampling': ('보간 방식', '補間方法', '采样', '取樣', 'Muestreo'),
'Smooth': ('부드럽게', 'スムーズ', '平滑', '平滑', 'Suave'),
'Pixel Art': ('픽셀 아트', 'ピクセルアート', '像素画', '像素畫', 'Arte de píxeles'),
'Padding': ('가장자리 여백', '余白', '边缘扩展', '邊緣擴展', 'Margen'),
'Clear old pixels on apply': ('적용 시 원래 자리 지우기', '適用時に元のピクセルを消去', '应用时清除原位置像素', '套用時清除原位置像素', 'Borrar origen al aplicar'),
'Live pixel preview': ('그림 미리보기', 'ピクセルをプレビュー', '像素预览', '像素預覽', 'Vista previa de píxeles'),
'Allow outside preview': ('이미지 밖에서도 조작', '画像の外側でもプレビュー', '允许在图像外预览', '允許在影像外預覽', 'Permitir vista fuera de imagen'),
'Protect other islands on apply': ('적용 시 다른 UV 섬 보호', '適用時に他のUVアイランドを保護', '应用时保护其他 UV 岛', '套用時保護其他 UV 島', 'Proteger otras islas al aplicar'),
'Floating layer · G / S / R switches mode': ('임시 레이어 · G / S / R로 조작 전환', '仮レイヤー · G / S / Rで切替', '浮动图层 · G / S / R 切换模式', '浮動圖層 · G / S / R 切換模式', 'Capa flotante · G / S / R cambia modo'),
'Click a button, then enter the image area': ('버튼을 누른 뒤 이미지 영역으로 이동', 'ボタンを押して画像領域へ移動', '点击按钮后将鼠标移入图像区域', '按下按鈕後將滑鼠移入影像區域', 'Pulsa un botón y entra en la imagen'),
'Select islands · transform · save image': ('UV 섬 선택 → 조작 → 이미지 저장', 'UV選択 → 変形 → 画像を保存', '选择 UV 岛 → 变换 → 保存图像', '選取 UV 島 → 變換 → 儲存影像', 'Selecciona islas, transforma y guarda'),
'Enter applies · Esc cancels · Ctrl+Z undoes': ('Enter 적용 · Esc 취소 · Ctrl+Z 되돌리기', 'Enterで適用 · Escで取消 · Ctrl+Zで戻す', 'Enter 应用 · Esc 取消 · Ctrl+Z 撤销', 'Enter 套用 · Esc 取消 · Ctrl+Z 復原', 'Enter aplica · Esc cancela · Ctrl+Z deshace'),
'Choose a painted image': ('편집할 이미지를 선택하세요', '編集する画像を選択', '请选择要编辑的图像', '請選擇要編輯的影像', 'Elige una imagen para editar'),
'Move X (px)': ('X 이동 (픽셀)', 'X移動（px）', 'X 移动（像素）', 'X 移動（像素）', 'Mover X (px)'),
'Move Y (px)': ('Y 이동 (픽셀)', 'Y移動（px）', 'Y 移动（像素）', 'Y 移動（像素）', 'Mover Y (px)'),
'Scale': ('배율', '拡大縮小', '缩放', '縮放', 'Escala'),
'Rotation': ('회전', '回転', '旋转', '旋轉', 'Rotación'),
'Move': ('이동', '移動', '移动', '移動', 'Mover'),
'Rotate': ('회전', '回転', '旋转', '旋轉', 'Rotar'),
'Move pointer onto the image to start, or type a value': ('이미지 영역으로 마우스를 가져오거나 수치를 입력하세요', '画像領域へカーソルを移動するか数値を入力', '将鼠标移入图像区域或输入数值', '將滑鼠移入影像區域或輸入數值', 'Entra en la imagen o escribe un valor'),
'G/S/R: switch · Enter: apply · Esc: cancel · Ctrl: snap': ('G/S/R 전환 · Enter 적용 · Esc 취소 · Ctrl 스냅', 'G/S/R 切替 · Enter 適用 · Esc 取消 · Ctrl スナップ', 'G/S/R 切换 · Enter 应用 · Esc 取消 · Ctrl 吸附', 'G/S/R 切換 · Enter 套用 · Esc 取消 · Ctrl 吸附', 'G/S/R cambia · Enter aplica · Esc cancela · Ctrl ajusta'),
'Outside preview: return inside to apply': ('이미지 밖 미리보기: 안으로 가져온 뒤 적용', '外側プレビュー：画像内に戻して適用', '图像外预览：移回图像内后应用', '影像外預覽：移回影像內後套用', 'Vista fuera: vuelve dentro para aplicar'),
'Esc: cancel': ('Esc: 취소', 'Esc：取消', 'Esc：取消', 'Esc：取消', 'Esc: cancelar'),
'Scale must be positive.': ('배율은 0보다 커야 합니다.', '倍率は0より大きくしてください。', '缩放比例必须大于 0。', '縮放比例必須大於 0。', 'La escala debe ser mayor que cero.'),
'Finish typing a number or press Esc.': ('숫자 입력을 마치거나 Esc로 취소하세요.', '数値を入力し終えるかEscで取り消してください。', '请完成数值输入或按 Esc。', '請完成數值輸入或按 Esc。', 'Termina de escribir el número o pulsa Esc.'),
'Bring the whole island inside the image before applying. Esc restores the original.': ('UV 섬 전체를 이미지 안으로 가져온 뒤 적용하세요. Esc는 원본으로 복원합니다.', 'UV全体を画像内に戻して適用してください。Escで元に戻ります。', '请将整个 UV 岛移回图像内再应用。Esc 恢复原状。', '請將整個 UV 島移回影像內再套用。Esc 恢復原狀。', 'Mueve toda la isla dentro de la imagen antes de aplicar. Esc restaura el original.'),
'Keep all UVs inside the image (0–1 tile). UDIM/repeated UVs are not supported yet.': ('UV를 이미지 안에 유지하세요. 밖에서 조작하려면 해당 옵션을 켜세요. UDIM·반복 UV는 아직 지원하지 않습니다.', 'UVを画像内に保ってください。外側で操作するには外側プレビューを有効にしてください。UDIM・繰り返しUVは未対応です。', '请将 UV 保持在图像内。若要在外部操作，请开启外部预览。暂不支持 UDIM 或重复 UV。', '請將 UV 保持在影像內。若要在外部操作，請開啟外部預覽。尚不支援 UDIM 或重複 UV。', 'Mantén los UV dentro de la imagen o activa la vista exterior. UDIM y UV repetidos no están disponibles.'),
'Destination overlaps another island or its padding. Move it or reduce Padding.': ('다른 UV 섬 또는 여백과 겹칩니다. 위치·여백을 바꾸거나 다른 섬 보호를 끄세요.', '他のUVまたは余白と重なっています。位置や余白を調整するか保護を無効にしてください。', '目标与其他 UV 岛或边缘重叠。请调整位置或边缘，或关闭保护。', '目標與其他 UV 島或邊緣重疊。請調整位置或邊緣，或關閉保護。', 'El destino solapa otra isla o su margen. Ajusta la posición o el margen, o desactiva la protección.'),
'Select a UV island in the UV Editor first.': ('먼저 UV 에디터에서 UV 섬을 선택하세요.', '先にUVエディターでUVアイランドを選択してください。', '请先在 UV 编辑器中选择 UV 岛。', '請先在 UV 編輯器中選取 UV 島。', 'Selecciona una isla en el editor UV primero.'),
'Select a mesh and enter Edit Mode.': ('메시를 선택하고 편집 모드로 들어가세요.', 'メッシュを選択し編集モードにしてください。', '请选择网格并进入编辑模式。', '請選取網格並進入編輯模式。', 'Selecciona una malla y entra en modo Edición.'),
'Edit one mesh at a time.': ('한 번에 하나의 메시만 편집하세요.', '一度に1つのメッシュを編集してください。', '请一次只编辑一个网格。', '請一次只編輯一個網格。', 'Edita una sola malla a la vez.'),
'Run this from the UV Editor.': ('UV 에디터에서 실행하세요.', 'UVエディターから実行してください。', '请从 UV 编辑器运行。', '請從 UV 編輯器執行。', 'Ejecuta esto desde el editor UV.'),
'Display a loaded, single-tile image in the UV Editor.': ('UV 에디터에서 불러온 단일 타일 이미지를 표시하세요.', 'UVエディターに読み込んだ単一タイル画像を表示してください。', '请在 UV 编辑器中显示已加载的单块图像。', '請在 UV 編輯器中顯示已載入的單一區塊影像。', 'Muestra una imagen cargada de un solo mosaico en el editor UV.'),
'Create a UV map first.': ('먼저 UV 맵을 만드세요.', '先にUVマップを作成してください。', '请先创建 UV 贴图。', '請先建立 UV 貼圖。', 'Crea un mapa UV primero.'),
'Every selected face must use the displayed image in its material.': ('선택한 모든 면의 머티리얼에서 현재 이미지를 사용해야 합니다.', '選択面のマテリアルは表示中の画像を使用する必要があります。', '所选面的材质必须使用当前显示的图像。', '所選面的材質必須使用目前顯示的影像。', 'El material de cada cara seleccionada debe usar la imagen mostrada.'),
'Selected and unselected UVs share pixels. Select all stacked islands together.': ('선택한 UV와 선택하지 않은 UV가 픽셀을 공유합니다. 겹친 섬을 함께 선택하세요.', '選択UVと未選択UVがピクセルを共有しています。重なったUVをまとめて選択してください。', '已选与未选 UV 共用像素。请一起选择重叠的 UV 岛。', '已選與未選 UV 共用像素。請一起選取重疊的 UV 島。', 'Los UV seleccionados y no seleccionados comparten píxeles. Selecciona juntas las islas apiladas.'),
'The transformed selection is smaller than a pixel.': ('변환 결과가 한 픽셀보다 작습니다.', '変形後の選択範囲が1ピクセル未満です。', '变换后的区域小于一个像素。', '變換後的區域小於一個像素。', 'La selección transformada es menor que un píxel.'),
'Selection is smaller than a pixel. Increase image resolution.': ('선택 영역이 한 픽셀보다 작습니다. 이미지 해상도를 높이세요.', '選択範囲が1ピクセル未満です。画像の解像度を上げてください。', '选区小于一个像素。请提高图像分辨率。', '選取範圍小於一個像素。請提高影像解析度。', 'La selección es menor que un píxel. Aumenta la resolución.'),
'Use a finite, non-zero transform.': ('유한한 값과 0이 아닌 배율을 사용하세요.', '有限の値と0以外の倍率を使用してください。', '请使用有限值和非零缩放。', '請使用有限值與非零縮放。', 'Usa valores finitos y una escala distinta de cero.'),
'Transform cancelled: {error}': ('변환 취소: {error}', '変形を取消：{error}', '变换已取消：{error}', '變換已取消：{error}', 'Transformación cancelada: {error}'),
}

ROWS.update({
'Use finite values and a positive scale.': ('유한한 값과 양수 배율을 사용하세요.', '有限の値と正の倍率を使用してください。', '请使用有限值和正缩放比例。', '請使用有限值和正縮放比例。', 'Usa valores finitos y una escala positiva.'),
'Expected an RGBA image.': ('RGBA 이미지가 필요합니다.', 'RGBA画像が必要です。', '需要 RGBA 图像。', '需要 RGBA 影像。', 'Se requiere una imagen RGBA.'),
'Padding must be between 0 and 16 pixels.': ('여백은 0~16픽셀이어야 합니다.', '余白は0〜16ピクセルにしてください。', '边缘扩展必须为 0 到 16 像素。', '邊緣擴展必須為 0 到 16 像素。', 'El margen debe estar entre 0 y 16 píxeles.'),
'UV coordinates must be finite.': ('UV 좌표는 유한한 값이어야 합니다.', 'UV座標は有限の値にしてください。', 'UV 坐标必须为有限值。', 'UV 座標必須為有限值。', 'Las coordenadas UV deben ser finitas.'),
'Transform must be finite and invertible.': ('변환은 유한하고 역변환이 가능해야 합니다.', '変換は有限で逆変換可能である必要があります。', '变换必须有限且可逆。', '變換必須有限且可逆。', 'La transformación debe ser finita e invertible.'),
'Unknown sampling method.': ('알 수 없는 보간 방식입니다.', '不明な補間方法です。', '未知采样方式。', '未知取樣方式。', 'Método de muestreo desconocido.'),
'Make the mesh and image local before editing.': ('메시와 이미지를 로컬 데이터로 바꾼 뒤 편집하세요.', '編集前にメッシュと画像をローカルデータにしてください。', '编辑前请将网格和图像设为本地数据。', '編輯前請將網格與影像設為本機資料。', 'Haz locales la malla y la imagen antes de editar.'),
'Use an RGBA image with Straight or None alpha mode.': ('RGBA 이미지의 알파 모드를 Straight 또는 None으로 설정하세요.', 'RGBA画像のアルファモードをストレートまたはなしにしてください。', '请使用 Alpha 模式为直接或无的 RGBA 图像。', '請使用 Alpha 模式為直接或無的 RGBA 影像。', 'Usa una imagen RGBA con alfa Straight o None.'),
'This preview version supports images up to 16 megapixels.': ('이 버전은 최대 1,600만 픽셀 이미지를 지원합니다.', 'このバージョンは最大1600万画素の画像に対応しています。', '此版本支持最多 1600 万像素的图像。', '此版本支援最多 1600 萬像素的影像。', 'Esta versión admite imágenes de hasta 16 megapíxeles.'),
'Image pixel buffer is unavailable.': ('이미지 픽셀 버퍼를 읽을 수 없습니다.', '画像のピクセルバッファを読み込めません。', '图像像素缓冲区不可用。', '影像像素緩衝區無法使用。', 'El búfer de píxeles no está disponible.'),
'Image also used by {name}. Give this mesh its own image first.': ('{name}에서도 같은 이미지를 사용합니다. 먼저 이미지 사본을 할당하세요.', '{name}も同じ画像を使用しています。先に画像を複製してください。', '{name} 也在使用此图像。请先为此网格分配独立图像。', '{name} 也在使用此影像。請先為此網格指派獨立影像。', '{name} también usa esta imagen. Asigna una imagen propia a esta malla.'),
'Only flat UV image mapping is supported.': ('Flat UV 이미지 매핑만 지원합니다.', 'フラットUVマッピングのみ対応しています。', '仅支持平面 UV 图像映射。', '僅支援平面 UV 影像映射。', 'Solo se admite el mapeo UV plano.'),
'Use the active UV map directly for this image (no Mapping node).': ('현재 UV 맵을 이미지에 직접 연결하세요. Mapping 노드는 지원하지 않습니다.', 'アクティブUVを画像に直接使用してください。マッピングノードは未対応です。', '请将当前 UV 贴图直接用于此图像，不使用映射节点。', '請將目前 UV 貼圖直接用於此影像，不使用映射節點。', 'Usa directamente el mapa UV activo, sin nodo Mapping.'),
'Undo history is tracking a different image on this mesh. Reload the file first.': ('되돌리기 기록이 다른 이미지를 참조합니다. 저장 후 파일을 다시 여세요.', '履歴が別の画像を参照しています。保存後にファイルを開き直してください。', '撤销记录正在跟踪另一幅图像。请保存后重新打开文件。', '復原記錄正在追蹤另一幅影像。請儲存後重新開啟檔案。', 'El historial sigue otra imagen. Guarda y vuelve a abrir el archivo.'),
})

ROWS.update({
'Nearest': ('최근접 (픽셀 아트)', '最近傍（ピクセルアート）', '最近邻（像素画）', '最近鄰（像素畫）', 'Vecino más cercano'),
'Bilinear': ('바이리니어', 'バイリニア', '双线性', '雙線性', 'Bilineal'),
'Bicubic': ('바이큐빅', 'バイキュービック', '双三次', '雙三次', 'Bicúbico'),
'Lanczos': ('Lanczos (선명하게)', 'ランチョス', 'Lanczos（锐利）', 'Lanczos（銳利）', 'Lanczos'),
})
LOCALES = ('ko_KR', 'ja_JP', 'zh_HANS', 'zh_HANT', 'es')
TABLES = {locale: {key: values[index] for key, values in ROWS.items()} for index, locale in enumerate(LOCALES)}
ALIASES = {'zh_CN':'zh_HANS', 'zh_TW':'zh_HANT', 'es_ES':'es'}


def language(context=None):
    context = context or bpy.context
    props = getattr(context.scene, 'uvpt_settings', None) if context.scene else None
    value = getattr(props, 'language', 'AUTO')
    if value == 'AUTO':
        value = context.preferences.view.language
    return ALIASES.get(value, value)


def tr(message, context=None):
    return TABLES.get(language(context), {}).get(message, message)


def register():
    translations = {locale: {(context, key): value for key, value in table.items()
                             for context in ('*', 'Operator')} for locale, table in TABLES.items()}
    for alias, locale in ALIASES.items():
        translations[alias] = translations[locale]
    bpy.app.translations.register(__name__, translations)


def unregister():
    bpy.app.translations.unregister(__name__)


# Keep enum strings alive: Blender retains references to dynamic enum text.
FILTERS = [('NEAREST','Nearest'), ('BILINEAR','Bilinear'), ('BICUBIC','Bicubic'), ('LANCZOS3','Lanczos')]
FILTER_ITEMS = {locale:[(key, table.get(label,label), table.get(label,label), 0, {'BILINEAR':0,'NEAREST':1,'BICUBIC':2,'LANCZOS3':3}[key]) for key,label in FILTERS]
                for locale,table in {**TABLES,'en_US':{}}.items()}

def sampling_items(self, context):
    return FILTER_ITEMS.get(language(context), FILTER_ITEMS['en_US'])
