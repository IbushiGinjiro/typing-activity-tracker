"""キーボードラベル→アイコンファイルの対応表(タスクトレイ・favicon共通)。

タスクトレイの表示とブラウザタブのfaviconで、同じ画像・同じ対応ルールを
使うために1箇所にまとめている。
"""
import os

ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons")

# キーボードラベル→専用アイコンファイル名の対応表。
# ここに無いラベル("default"含む未登録・新規追加分)はDEFAULT_ICON_FILEにフォールバックする。
KEYBOARD_ICON_FILES = {
    "職場aula65%": "f65.png",
    "自宅TH40%": "th40.png",
}

DEFAULT_ICON_FILE = "default.png"  # ASUS Vivobook(黒っぽいノートPC)のキーボード+タッチパッド


def icon_filename_for(keyboard_name):
    return KEYBOARD_ICON_FILES.get(keyboard_name, DEFAULT_ICON_FILE)


def icon_path_for(keyboard_name):
    return os.path.join(ICON_DIR, icon_filename_for(keyboard_name))
