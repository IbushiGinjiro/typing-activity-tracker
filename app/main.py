"""エントリポイント。キー入力キャプチャ・ダッシュボード・タスクトレイ・USB自動検出を起動する。"""
import sys
import threading

from .capture import KeyCapture
from .config import load_config, save_config
from .dashboard import create_app
from .db import Database
from .device_watch import DeviceWatcher
from .notifier import DeviceNotifier
from .state import AppState
from .tray import TrayApp


def _migrate_onboarding_flag(config, db):
    """既存ユーザー(既にキーボードを登録済み)は、オンボーディング画面を初回起動時に
    スキップさせるため、onboarding_doneを自動的にtrueにしておく。"""
    if config.get("onboarding_done"):
        return
    registered = [name for (_id, name) in db.list_keyboards() if name != "default"]
    if registered:
        config["onboarding_done"] = True
        save_config(config)


def main():
    config = load_config()
    db = Database(config["db_path"])
    state = AppState(db)
    _migrate_onboarding_flag(config, db)

    capture = KeyCapture(db, state)
    capture.start()

    flask_app = create_app(db, state, config)
    dashboard_url = f"http://{config['dashboard_host']}:{config['dashboard_port']}/"

    server_thread = threading.Thread(
        target=lambda: flask_app.run(
            host=config["dashboard_host"],
            port=config["dashboard_port"],
            debug=False,
            use_reloader=False,
        ),
        daemon=True,
    )
    server_thread.start()

    notifier = DeviceNotifier(dashboard_url)
    watcher = DeviceWatcher(db, state, config["device_grace_period_seconds"], notifier)
    watcher.start()

    def on_quit():
        watcher.stop()
        capture.stop()
        sys.exit(0)

    TrayApp(state, dashboard_url, on_quit).run()


if __name__ == "__main__":
    main()
