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
import logging
import os
import threading

import pythoncom
import wmi

from .config import PROJECT_ROOT
from .device_key import extract_device_key

WATCH_TIMEOUT_MS = 1000

# 起動時スキャン・着脱イベントの検知状況を追記するデバッグログ。pythonw実行時はコンソールが
# 無く標準出力を確認できないため、実機での不具合調査用にファイルへ残す
# (2026-09-17、起動時スキャンが実機で空振りする不具合の原因調査のために追加)。
_LOG_PATH = os.path.join(PROJECT_ROOT, "data", "device_watch.log")
_logger = logging.getLogger("device_watch")
_logger.setLevel(logging.DEBUG)
if not _logger.handlers:
    os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
    _handler = logging.FileHandler(_LOG_PATH, encoding="utf-8")
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    _logger.addHandler(_handler)


class DeviceWatcher:
    def __init__(self, db, state, grace_period_seconds, notifier, creation_batch_seconds=2.0):
        self.db = db
        self.state = state
        self.grace_period_seconds = grace_period_seconds
        self.notifier = notifier
        self.creation_batch_seconds = creation_batch_seconds

        self._lock = threading.Lock()
        self._active_device_key = None  # 現在のラベルの根拠になっているdevice_key
        self._grace_timer = None
        self._self_initiated = False
        self._pending_creation_keys = []  # 同時多発的なCreationイベントをまとめて判定するための一時バッファ
        self._creation_batch_timer = None

        self._stop_event = threading.Event()
        self._creation_ready = threading.Event()
        self._deletion_ready = threading.Event()
        self._creation_thread = None
        self._deletion_thread = None
        self._scan_thread = None

        self.state.on_change(self._on_state_changed)

    # --- ライフサイクル ---

    def start(self):
        # wmi.WMI()(COMオブジェクト)はCOMアパートメントを持つスレッドの中で作る必要がある。
        # メインスレッドで作って渡すと、別スレッド(監視スレッド)からのアクセス時に
        # 「COM初期化されていない」旨のCOMエラーで例外になる(実機ビルドで実際に発生した)。
        # そのため接続の生成自体を各監視スレッド内で行う。
        self._creation_thread = threading.Thread(
            target=self._watch_loop, args=("creation", self._handle_creation, self._creation_ready), daemon=True
        )
        self._deletion_thread = threading.Thread(
            target=self._watch_loop, args=("deletion", self._handle_deletion, self._deletion_ready), daemon=True
        )
        self._creation_thread.start()
        self._deletion_thread.start()

        # 起動前から既に接続されているキーボード(=着脱イベントが発生しないもの)を検知するため、
        # 現在接続中のデバイスを1回だけスキャンする。Creation/Deletionの監視サブスクリプションが
        # 確立してからスキャンすることで、「サブスクリプション確立前後の一瞬に挿さったデバイス」を
        # 取りこぼす隙間が生じないようにしている(スキャンより前からあるものはスキャンが拾い、
        # サブスクリプション確立後に挿さったものはイベント監視が拾う)。
        self._scan_thread = threading.Thread(target=self._run_initial_scan, daemon=True)
        self._scan_thread.start()
        _logger.info("DeviceWatcher.start(): 監視スレッド・初期スキャンスレッドを起動しました")

    def stop(self):
        self._stop_event.set()
        with self._lock:
            if self._grace_timer is not None:
                self._grace_timer.cancel()
                self._grace_timer = None
            if self._creation_batch_timer is not None:
                self._creation_batch_timer.cancel()
                self._creation_batch_timer = None

    def _watch_loop(self, notification_type, handler, ready_event):
        pythoncom.CoInitialize()
        try:
            wmi_conn = wmi.WMI()
            watcher = wmi_conn.Win32_PnPEntity.watch_for(
                notification_type=notification_type, delay_secs=1, PNPClass="Keyboard"
            )
            ready_event.set()
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

    def _run_initial_scan(self):
        # サブスクリプション確立を待つ(万一確立に失敗しても、取りこぼし防止の意味は薄れるが
        # スキャン自体はタイムアウト後に行う)。
        creation_ok = self._creation_ready.wait(timeout=5)
        deletion_ok = self._deletion_ready.wait(timeout=5)
        if not creation_ok or not deletion_ok:
            _logger.warning(
                "初期スキャン: 監視サブスクリプションの確立待ちがタイムアウトしました"
                " (creation_ready=%s, deletion_ready=%s)。取りこぼし防止の意味は薄れますが、"
                "スキャン自体は続行します。",
                creation_ok,
                deletion_ok,
            )
        if self._stop_event.is_set():
            return

        pythoncom.CoInitialize()
        try:
            wmi_conn = wmi.WMI()
            device_ids = [entity.DeviceID for entity in wmi_conn.Win32_PnPEntity(PNPClass="Keyboard")]
        except Exception:
            _logger.exception("初期スキャン: WMIへのキーボード一覧問い合わせに失敗しました")
            return
        finally:
            pythoncom.CoUninitialize()

        _logger.info("初期スキャン: PNPClass=Keyboardのデバイスを%d件検出しました: %s", len(device_ids), device_ids)
        self._scan_initial(device_ids)

    def _scan_initial(self, device_ids):
        """起動時に既に接続されているデバイスの一覧から、登録済みキーボードがあれば自動切替する。

        複数の登録済みデバイスが同時に見つかった場合は、最初に見つかった1件のみを採用する
        (2台同時使用は非対応というSPEC.mdの方針をそのまま踏襲)。
        """
        for device_id in device_ids:
            if self._stop_event.is_set():
                return
            device_key = extract_device_key(device_id)
            if device_key is None:
                _logger.debug("初期スキャン: VID/PIDが取れないため無視: %s", device_id)
                continue
            mapping = self.db.get_keyboard_for_device(device_key)
            _logger.info(
                "初期スキャン: device_key=%s device_id=%s -> %s",
                device_key,
                device_id,
                f"登録済み({mapping})" if mapping is not None else "未登録",
            )
            if mapping is not None:
                self._switch_to(mapping, device_key, method="auto")
                self.notifier.notify_switch(mapping)
                return
        else:
            _logger.info("初期スキャン: 登録済みキーボードは見つかりませんでした")

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
        _logger.info("Creationイベント: %s", device_id)
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

        # USB複合デバイスの抜き差し1回で、無関係な他のPnPデバイス(ハブ・レシーバー等、PNPClassが
        # 偶然Keyboardになっているもの)のCreationイベントがほぼ同時に複数発生することがある。
        # 都度即座に判定すると、たまたま先に来た方が未登録デバイスだった場合に「新しいキーボードを
        # 検出しました」という紛らわしい通知が、後から来る登録済みキーボードの通知より先に表示されて
        # しまう(実機で確認)。そのため短い時間窓(creation_batch_seconds)にまとめて到着した
        # device_keyをバッファし、その中に登録済みのものが1つでもあればそちらを優先して自動切替し、
        # 未登録の通知は(バッチ内が全て未登録の場合を除いて)出さないようにする。
        with self._lock:
            if device_key not in self._pending_creation_keys:
                self._pending_creation_keys.append(device_key)
            if self._creation_batch_timer is None:
                timer = threading.Timer(self.creation_batch_seconds, self._process_creation_batch)
                self._creation_batch_timer = timer
                timer.start()

    def _process_creation_batch(self):
        with self._lock:
            device_keys = self._pending_creation_keys
            self._pending_creation_keys = []
            self._creation_batch_timer = None

        matched_mapping = None
        matched_key = None
        for device_key in device_keys:
            mapping = self.db.get_keyboard_for_device(device_key)
            if mapping is not None:
                matched_mapping = mapping
                matched_key = device_key
                break

        if matched_mapping is not None:
            self._switch_to(matched_mapping, matched_key, method="auto")
            self.notifier.notify_switch(matched_mapping)
        elif device_keys:
            # バッチ内が全て未登録だった場合のみ通知する。同時に複数の未登録デバイスが挿さっても
            # 通知はまとめて1回だけ(トーストの連発を避ける)。
            self.notifier.notify_unknown(device_keys[0])

    def _handle_deletion(self, device_id):
        _logger.info("Deletionイベント: %s", device_id)
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
