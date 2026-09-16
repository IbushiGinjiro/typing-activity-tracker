"""アプリ全体の設定値。"""
import json
import os
import sys

DEFAULT_CONFIG = {
    "burst_gap_seconds": 2.0,
    "typo_window_seconds": 1.0,
    "db_path": "data/events.db",
    "dashboard_host": "127.0.0.1",
    "dashboard_port": 5151,
    "device_grace_period_seconds": 15.0,
    "onboarding_done": False,
}


def _detect_project_root():
    """設定ファイル・DBの置き場所の基準ディレクトリ。

    PyInstallerでonefile化した場合、`__file__`は実行のたびに変わる一時展開先
    (`sys._MEIPASS`)を指してしまい、これを基準にするとconfig.json/data/events.dbを
    起動のたびに見失う(=打鍵データが毎回リセットされる)重大な問題になる。
    frozen時は実行ファイル(.exe)自体があるフォルダを基準にする。
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


PROJECT_ROOT = _detect_project_root()
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.json")


def load_config():
    config = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config.update(json.load(f))
    # db_pathは実行時のカレントディレクトリに依存させず、常にプロジェクト直下を基準にする
    # (スタートアップ自動起動など、作業ディレクトリが異なる環境から起動されても
    # 同じdata/events.dbを参照できるようにするため)
    if not os.path.isabs(config["db_path"]):
        config["db_path"] = os.path.join(PROJECT_ROOT, config["db_path"])
    return config


def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
