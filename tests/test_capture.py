"""「実際に入力された文字は記録しない」ことを保証するためのテスト。

配布(README等)で明言している最重要の約束なので、実装が変わっても
機械的に検証できるようにしておく。
"""
import unittest

from pynput import keyboard

from app.capture import KeyCapture, classify_key

ALLOWED_KEY_TYPES = {"char", "backspace", "delete", None}


class FakeDB:
    def __init__(self):
        self.recorded = []

    def record_event(self, ts, key_type, keyboard_id):
        self.recorded.append((ts, key_type, keyboard_id))


class FakeState:
    keyboard_id = 1


class ClassifyKeyOnlyReturnsFixedLabelsTest(unittest.TestCase):
    """classify_keyはキー種別を表す固定文字列しか返してはいけない(キー自体の値を返さない)。"""

    def test_regular_letters_and_digits_return_generic_char_label(self):
        for ch in "abcdefghijklmnopqrstuvwxyz0123456789 !@#\"'":
            key = keyboard.KeyCode.from_char(ch)
            result = classify_key(key)
            self.assertIn(result, ALLOWED_KEY_TYPES)
            # 打った文字そのもの(ch)が結果に紛れ込んでいないことを確認
            if result is not None:
                self.assertNotEqual(result, ch)

    def test_special_keys_return_fixed_labels(self):
        self.assertEqual(classify_key(keyboard.Key.backspace), "backspace")
        self.assertEqual(classify_key(keyboard.Key.delete), "delete")
        self.assertEqual(classify_key(keyboard.Key.space), "char")
        self.assertEqual(classify_key(keyboard.Key.enter), "char")
        self.assertEqual(classify_key(keyboard.Key.tab), "char")

    def test_modifier_and_navigation_keys_are_not_recorded(self):
        for key in (keyboard.Key.shift, keyboard.Key.ctrl, keyboard.Key.alt, keyboard.Key.up, keyboard.Key.esc):
            self.assertIsNone(classify_key(key))


class KeyCaptureDoesNotLeakRawKeyTest(unittest.TestCase):
    """KeyCapture._on_pressがDBに渡す値に、打鍵の生データが含まれないことを確認する。"""

    def test_on_press_only_forwards_classified_type(self):
        db = FakeDB()
        capture = KeyCapture(db, FakeState())

        secret_chars = "Password123!"
        for ch in secret_chars:
            capture._on_press(keyboard.KeyCode.from_char(ch))
        capture._on_press(keyboard.Key.backspace)
        capture._on_press(keyboard.Key.shift)  # 記録対象外(Noneなので保存されない)

        self.assertEqual(len(db.recorded), len(secret_chars) + 1)
        # DBに渡される2番目の要素(key_type)は必ず固定ラベルのいずれかであり、
        # 打った文字そのもの(例: "P" "a" "s" ...)が紛れ込む余地が無いことを確認する。
        recorded_key_types = {r[1] for r in db.recorded}
        self.assertTrue(recorded_key_types.issubset({"char", "backspace", "delete"}))
        self.assertFalse(recorded_key_types & set(secret_chars))


if __name__ == "__main__":
    unittest.main()
