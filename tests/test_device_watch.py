import time
import unittest

from app.device_key import extract_device_key
from app.device_watch import DeviceWatcher


class ExtractDeviceKeyTest(unittest.TestCase):
    def test_usb_composite_device(self):
        self.assertEqual(
            extract_device_key(r"HID\VID_FEED&PID_4346&MI_00\8&273C3704&0&0000"),
            "VID_FEED&PID_4346",
        )

    def test_case_insensitive_and_normalized_upper(self):
        self.assertEqual(extract_device_key(r"hid\vid_feed&pid_4346"), "VID_FEED&PID_4346")

    def test_no_vid_pid_returns_none(self):
        self.assertIsNone(extract_device_key(r"ACPI\ATK3001\4&230E843&0"))

    def test_empty_or_none(self):
        self.assertIsNone(extract_device_key(""))
        self.assertIsNone(extract_device_key(None))


class FakeDB:
    def __init__(self, mapping=None):
        self.mapping = mapping or {}
        self.switches = []

    def get_keyboard_for_device(self, device_key):
        return self.mapping.get(device_key)

    def get_or_create_keyboard(self, name):
        return name  # 名前をそのままIDとして使う(テスト用)

    def record_switch(self, ts, keyboard_id, device_key, method):
        self.switches.append((keyboard_id, device_key, method))


class FakeState:
    def __init__(self, db, name="default"):
        self.db = db
        self.keyboard_name = name
        self._listeners = []

    def on_change(self, callback):
        self._listeners.append(callback)

    def set_keyboard(self, name, device_key=None, method="manual"):
        if self.keyboard_name == name:
            return
        self.keyboard_name = name
        self.db.record_switch(time.time(), name, device_key, method)
        for cb in self._listeners:
            cb(name, device_key, method)


class FakeNotifier:
    def __init__(self):
        self.switches = []
        self.unknowns = []
        self.grace_starts = []
        self.fallbacks = 0

    def notify_switch(self, name):
        self.switches.append(name)

    def notify_unknown(self, device_key):
        self.unknowns.append(device_key)

    def notify_grace_start(self, name, seconds):
        self.grace_starts.append((name, seconds))

    def notify_fallback(self):
        self.fallbacks += 1


KEY_A = "VID_0001&PID_0001"
KEY_B = "VID_0002&PID_0002"


def make_watcher(mapping, grace=5.0):
    db = FakeDB(mapping)
    state = FakeState(db)
    notifier = FakeNotifier()
    watcher = DeviceWatcher(db, state, grace, notifier)
    return watcher, db, state, notifier


class DeviceWatcherScenarioTest(unittest.TestCase):
    def test_known_device_creation_switches_and_notifies(self):
        watcher, db, state, notifier = make_watcher({KEY_A: "aula65"})
        watcher._handle_creation(f"HID\\{KEY_A}&MI_00")
        self.assertEqual(state.keyboard_name, "aula65")
        self.assertEqual(notifier.switches, ["aula65"])

    def test_unknown_device_creation_notifies_without_switch(self):
        watcher, db, state, notifier = make_watcher({})
        watcher._handle_creation(f"HID\\{KEY_A}&MI_00")
        self.assertEqual(state.keyboard_name, "default")
        self.assertEqual(notifier.unknowns, [KEY_A])

    def test_deletion_of_active_device_starts_grace_then_falls_back(self):
        watcher, db, state, notifier = make_watcher({KEY_A: "aula65"}, grace=0.05)
        watcher._handle_creation(f"HID\\{KEY_A}&MI_00")
        watcher._handle_deletion(f"HID\\{KEY_A}&MI_00")
        self.assertEqual(len(notifier.grace_starts), 1)
        self.assertEqual(state.keyboard_name, "aula65")  # 猶予中はまだ切り替わらない
        time.sleep(0.15)
        self.assertEqual(state.keyboard_name, "default")
        self.assertEqual(notifier.fallbacks, 1)

    def test_reconnect_within_grace_cancels_fallback_silently(self):
        watcher, db, state, notifier = make_watcher({KEY_A: "aula65"}, grace=0.2)
        watcher._handle_creation(f"HID\\{KEY_A}&MI_00")
        watcher._handle_deletion(f"HID\\{KEY_A}&MI_00")
        watcher._handle_creation(f"HID\\{KEY_A}&MI_00")  # 猶予中に挿し直し
        time.sleep(0.35)
        self.assertEqual(state.keyboard_name, "aula65")
        self.assertEqual(notifier.fallbacks, 0)
        # 再接続時に「切り替えました」通知が二重に出ていない(最初の1回のみ)
        self.assertEqual(notifier.switches, ["aula65"])

    def test_different_known_device_during_grace_overrides_immediately(self):
        watcher, db, state, notifier = make_watcher({KEY_A: "aula65", KEY_B: "th40"}, grace=5.0)
        watcher._handle_creation(f"HID\\{KEY_A}&MI_00")
        watcher._handle_deletion(f"HID\\{KEY_A}&MI_00")
        watcher._handle_creation(f"HID\\{KEY_B}&MI_00")
        self.assertEqual(state.keyboard_name, "th40")
        self.assertEqual(notifier.switches, ["aula65", "th40"])
        # 長い猶予(5秒)を待たなくても即座に切り替わっている = 保留中のフォールバックは
        # もう有効ではないはず(キャンセルされている)
        self.assertIsNone(watcher._grace_timer)

    def test_manual_switch_resets_device_tracking(self):
        watcher, db, state, notifier = make_watcher({KEY_A: "aula65"}, grace=0.05)
        watcher._handle_creation(f"HID\\{KEY_A}&MI_00")
        state.set_keyboard("th40", method="manual")  # タスクトレイ/ダッシュボードからの手動切替を模擬
        self.assertIsNone(watcher._active_device_key)
        # Aを抜いても、もう追跡対象ではないので何も起きない
        watcher._handle_deletion(f"HID\\{KEY_A}&MI_00")
        self.assertEqual(len(notifier.grace_starts), 0)

    def test_manual_switch_with_device_key_is_adopted(self):
        # ダッシュボードの「新規デバイス登録」経由の切替(device_key付き)は追跡を引き継ぐ
        watcher, db, state, notifier = make_watcher({}, grace=0.05)
        state.set_keyboard("new-kb", device_key=KEY_A, method="manual")
        self.assertEqual(watcher._active_device_key, KEY_A)
        watcher._handle_deletion(f"HID\\{KEY_A}&MI_00")
        self.assertEqual(len(notifier.grace_starts), 1)

    def test_device_without_vid_pid_is_ignored(self):
        watcher, db, state, notifier = make_watcher({})
        watcher._handle_creation(r"ACPI\ATK3001\4&230E843&0")
        self.assertEqual(state.keyboard_name, "default")
        self.assertEqual(notifier.switches, [])
        self.assertEqual(notifier.unknowns, [])


if __name__ == "__main__":
    unittest.main()
