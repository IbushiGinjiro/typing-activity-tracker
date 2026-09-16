"""USB/BluetoothキーボードのPnP着脱をWMIで監視し、登録済みキーボードへの自動切替、
猶予期間つきのdefaultへのフォールバックを行う。

シナリオ(SPEC.md参照):
  1. 登録済みdevice_keyが挿さった -> 自動切替+通知
  2. 未登録のdevice_keyが挿さった -> 通知(クリックでダッシュボードの登録画面へ)
  3. 猶予期間中に別の登録済みdevice_keyが挿さった -> 猶予を待たず即座にそちらへ切替
  4. 現在のラベルに紐づくdevice_keyが抜けた -> 猶予期間(既定5秒)後にdefaultへフォールバック。
     猶予期間中に同じdevice_keyが再接続されたら何もせず継続。

pynputの低レベルフックはどの物理キーボードから打鍵が来たか区別できないため、本モジュールは
「挿さっているデバイスの変化に応じて現在のラベルというフラグを切り替える」だけで、
2台同時使用の使い分けには対応しない(SPEC.mdのシナリオ3として明示的にスコープ外)。
"""
import threading

import pythoncom
import wmi

from .device_key import extract_device_key

WATCH_TIMEOUT_MS = 1000


class DeviceWatcher:
    def __init__(self, db, state, grace_period_seconds, notifier):
        self.db = db
        self.state = state
        self.grace_period_seconds = grace_period_seconds
        self.notifier = notifier

        self._lock = threading.Lock()
        self._active_device_key = None  # 現在のラベルの根拠になっているdevice_key
        self._grace_timer = None
        self._self_initiated = False

        self._stop_event = threading.Event()
        self._creation_thread = None
        self._deletion_thread = None

        self.state.on_change(self._on_state_changed)

    # --- ライフサイクル ---

    def start(self):
        # wmi.WMI()(COMオブジェクト)はCOMアパートメントを持つスレッドの中で作る必要がある。
        # メインスレッドで作って渡すと、別スレッド(監視スレッド)からのアクセス時に
        # 「COM初期化されていない」旨のCOMエラーで例外になる(実機ビルドで実際に発生した)。
        # そのため接続の生成自体を各監視スレッド内で行う。
        self._creation_thread = threading.Thread(
            target=self._watch_loop, args=("creation", self._handle_creation), daemon=True
        )
        self._deletion_thread = threading.Thread(
            target=self._watch_loop, args=("deletion", self._handle_deletion), daemon=True
        )
        self._creation_thread.start()
        self._deletion_thread.start()

    def stop(self):
        self._stop_event.set()
        with self._lock:
            if self._grace_timer is not None:
                self._grace_timer.cancel()
                self._grace_timer = None

    def _watch_loop(self, notification_type, handler):
        pythoncom.CoInitialize()
        try:
            wmi_conn = wmi.WMI()
            watcher = wmi_conn.Win32_PnPEntity.watch_for(
                notification_type=notification_type, delay_secs=1, PNPClass="Keyboard"
            )
            while not self._stop_event.is_set():
                try:
                    event = watcher(timeout_ms=WATCH_TIMEOUT_MS)
                except wmi.x_wmi_timed_out:
                    continue
                except Exception:
                    # WMI接続が一時的に不安定なケース等。監視は続行する。
                    continue
                handler(event.DeviceID)
        finally:
            pythoncom.CoUninitialize()

    # --- AppStateの変更通知(手動切替・自身の切替の両方で呼ばれる) ---

    def _on_state_changed(self, _name, device_key, _method):
        with self._lock:
            if self._self_initiated:
                self._self_initiated = False
                return
            # 自分(DeviceWatcher)以外の経路で変わった場合。ダッシュボードの新規デバイス
            # 登録のようにdevice_keyが分かっていればそれを追跡の根拠として引き継ぎ、
            # 通常の手動切替(device_key=None)なら追跡をリセットする。
            self._active_device_key = device_key
            if self._grace_timer is not None:
                self._grace_timer.cancel()
                self._grace_timer = None

    def _switch_to(self, name, device_key, method):
        with self._lock:
            self._self_initiated = True
            self._active_device_key = device_key
            if self._grace_timer is not None:
                self._grace_timer.cancel()
                self._grace_timer = None
        self.state.set_keyboard(name, device_key=device_key, method=method)

    # --- PnPイベントハンドラ ---

    def _handle_creation(self, device_id):
        device_key = extract_device_key(device_id)
        if device_key is None:
            return

        with self._lock:
            reconnect_of_pending = device_key == self._active_device_key and self._grace_timer is not None
            if reconnect_of_pending:
                self._grace_timer.cancel()
                self._grace_timer = None

        if reconnect_of_pending:
            return  # 猶予期間中に同じデバイスが戻ってきた -> 何もせず継続(通知もしない)

        mapping = self.db.get_keyboard_for_device(device_key)
        if mapping is not None:
            self._switch_to(mapping, device_key, method="auto")
            self.notifier.notify_switch(mapping)
        else:
            self.notifier.notify_unknown(device_key)

    def _handle_deletion(self, device_id):
        device_key = extract_device_key(device_id)
        if device_key is None:
            return

        with self._lock:
            if device_key != self._active_device_key or self._grace_timer is not None:
                return  # 今使っているラベルの根拠ではない、または既に猶予中
            current_name = self.state.keyboard_name
            timer = threading.Timer(self.grace_period_seconds, self._fallback_after_grace, args=(device_key,))
            self._grace_timer = timer
            timer.start()

        self.notifier.notify_grace_start(current_name, self.grace_period_seconds)

    def _fallback_after_grace(self, device_key):
        with self._lock:
            if self._active_device_key != device_key or self._grace_timer is None:
                return  # 猶予中に何か他のことが起きて既に上書きされている
            self._grace_timer = None
        self._switch_to("default", None, method="fallback")
        self.notifier.notify_fallback()
