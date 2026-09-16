"""グローバルキーフックによる打鍵イベントの記録。

記録するのはキー種別(char/backspace/delete)とタイムスタンプのみ。
実際に入力された文字(何を打ったか)は一切保存しない。
"""
import time

from pynput import keyboard


def classify_key(key):
    """pynputのキーオブジェクトを 'char' / 'backspace' / 'delete' / None に分類する。

    None はモディファイアキーや矢印キーなど、打鍵の速度・正確さの
    分析対象外とするキー(記録しない)。
    """
    if key == keyboard.Key.backspace:
        return "backspace"
    if key == keyboard.Key.delete:
        return "delete"
    if key in (keyboard.Key.space, keyboard.Key.enter, keyboard.Key.tab):
        return "char"
    if hasattr(key, "char") and key.char is not None:
        return "char"
    return None


class KeyCapture:
    def __init__(self, db, state):
        self.db = db
        self.state = state
        self._listener = None

    def _on_press(self, key):
        key_type = classify_key(key)
        if key_type is None:
            return
        self.db.record_event(time.time(), key_type, self.state.keyboard_id)

    def start(self):
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.start()

    def stop(self):
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
