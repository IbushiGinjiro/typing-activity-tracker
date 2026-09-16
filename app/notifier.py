"""USB自動検出関連のWindowsトースト通知。

`winotify`はWinRTのトースト通知を使うため、PyInstaller化した無署名exeだと
AppUserModelIDの登録が上手くいかず通知が出ない/一般的なアイコンで出ることがある
(実機での配布時に要確認。動かない場合は通知なしでも自動切替自体は機能する)。
"""
import urllib.parse

from winotify import Notification

APP_ID = "打鍵アクティビティ"


class DeviceNotifier:
    def __init__(self, dashboard_url):
        self.dashboard_url = dashboard_url.rstrip("/")

    def _show(self, title, msg, launch=""):
        try:
            toast = Notification(app_id=APP_ID, title=title, msg=msg, launch=launch)
            toast.show()
        except Exception:
            # 通知が出せない環境でも自動切替自体は継続させる(通知は補助情報のため)。
            pass

    def notify_switch(self, keyboard_name):
        self._show("打鍵アクティビティ", f"{keyboard_name} に切り替えました")

    def notify_unknown(self, device_key):
        url = f"{self.dashboard_url}/keyboards/new-device?key={urllib.parse.quote(device_key)}"
        self._show(
            "新しいキーボードを検出しました",
            "クリックすると登録画面が開きます",
            launch=url,
        )

    def notify_grace_start(self, keyboard_name, grace_period_seconds):
        self._show(
            "打鍵アクティビティ",
            f"{keyboard_name} が外れました。{grace_period_seconds:.0f}秒以内に挿し直せばそのまま継続します",
        )

    def notify_fallback(self):
        self._show("打鍵アクティビティ", "default に切り替えました")
