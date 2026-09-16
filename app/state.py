"""現在選択中のキーボードラベルを保持する共有状態。

タスクトレイのメニュー・ダッシュボードのフォーム・USB自動検出のいずれから
切り替えても、登録済みのコールバック(`on_change`)を通じて同じ経路で
他コンポーネント(タスクトレイのアイコン等)に変更を伝える。
"""
import threading
import time


class AppState:
    def __init__(self, db, default_keyboard="default"):
        self.db = db
        self._lock = threading.Lock()
        self._keyboard_id = db.get_or_create_keyboard(default_keyboard)
        self._keyboard_name = default_keyboard
        self._listeners = []

    @property
    def keyboard_id(self):
        with self._lock:
            return self._keyboard_id

    @property
    def keyboard_name(self):
        with self._lock:
            return self._keyboard_name

    def on_change(self, callback):
        """keyboard_nameが変わるたびに`callback(name)`を呼ぶ。"""
        self._listeners.append(callback)

    def set_keyboard(self, name, device_key=None, method="manual"):
        """method: "manual"(タスクトレイ/ダッシュボードでの手動切替) /
        "auto"(USB自動検出での切替) / "fallback"(猶予期間切れによるdefaultへの自動復帰)。
        """
        keyboard_id = self.db.get_or_create_keyboard(name)
        with self._lock:
            if self._keyboard_name == name:
                return
            self._keyboard_id = keyboard_id
            self._keyboard_name = name
        self.db.record_switch(time.time(), keyboard_id, device_key, method)
        for callback in self._listeners:
            callback(name, device_key, method)
