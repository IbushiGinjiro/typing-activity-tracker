"""タスクトレイ常駐UI。登録済みキーボードへの切替、ダッシュボードを開く、終了を提供する。

新しいキーボードラベルの「追加」はここでは行わない。バックグラウンド
スレッドからtkinterダイアログを開くと、Windowsがそのウィンドウにキー入力
フォーカスを渡さず文字が打てないことがあったため、普段からアクティブに
なっているブラウザ側のダッシュボード(`app/dashboard.py`)に寄せている。
"""
import webbrowser
import os

import pystray
from PIL import Image, ImageDraw

from .icons import icon_path_for


def _fallback_icon_image():
    """アイコン画像ファイルが見つからない場合の最終フォールバック(通常は使われない)。"""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, size - 4, size - 4), fill=(76, 110, 245, 255))
    draw.text((24, 20), "T", fill="white")
    return img


def _load_icon_image(keyboard_name):
    path = icon_path_for(keyboard_name)
    if os.path.exists(path):
        return Image.open(path).convert("RGBA")
    return _fallback_icon_image()


class TrayApp:
    def __init__(self, state, dashboard_url, on_quit):
        self.state = state
        self.dashboard_url = dashboard_url
        self.on_quit = on_quit
        self.icon = pystray.Icon(
            "typing-activity-tracker", _load_icon_image(state.keyboard_name), "打鍵アクティビティ"
        )
        # callableを渡すと、メニューを開くたびに最新の登録キーボード一覧・現在値で
        # 作り直してくれる(DB側の変更をタスクトレイ側が自動的に拾える)。
        self.icon.menu = pystray.Menu(self._menu_items)
        # 手動切替(タスクトレイ・ダッシュボード)・自動検出のどの経路で切り替わっても
        # ここでアイコンを更新する(切替経路を1本化するため)。
        self.state.on_change(self._on_keyboard_changed)

    def _on_keyboard_changed(self, name, device_key=None, method=None):
        self.icon.icon = _load_icon_image(name)

    def _menu_items(self):
        keyboards = self.state.db.list_keyboards()
        keyboard_items = [
            pystray.MenuItem(
                name,
                self._make_switch_handler(name),
                checked=self._make_checked(name),
                radio=True,
            )
            for (_id, name) in keyboards
        ] or [pystray.MenuItem("(未登録。ダッシュボードで追加してください)", None, enabled=False)]

        return (
            pystray.MenuItem(f"現在: {self.state.keyboard_name}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("キーボードを切替", pystray.Menu(*keyboard_items)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("ダッシュボードを開く(キーボードの追加もこちらから)", self._open_dashboard),
            pystray.MenuItem("終了", self._quit),
        )

    def _make_switch_handler(self, name):
        def handler(icon, item):
            self.state.set_keyboard(name)

        return handler

    def _make_checked(self, name):
        def checked(item):
            return self.state.keyboard_name == name

        return checked

    def _open_dashboard(self, icon, item):
        webbrowser.open(self.dashboard_url)

    def _quit(self, icon, item):
        self.icon.stop()
        self.on_quit()

    def run(self):
        self.icon.run()
