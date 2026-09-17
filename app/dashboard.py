"""ローカルダッシュボード(Flask)。日次・週次トレンドとキーボード別比較を表示する。

キーボードラベルの「新規追加」もここ(ブラウザ)で行う。タスクトレイの
バックグラウンドスレッドからtkinterダイアログを開くと、Windows側が
そのウィンドウにキー入力フォーカスを渡さないことがあり、文字が打てない
問題が起きたため、普段からアクティブになっているブラウザ側に寄せている。

USB自動検出で未登録デバイスを検知した際のトースト通知も、ここ
(`/keyboards/new-device`)に飛んでくる。初回起動時のオンボーディング
(`/onboarding`)が未完了のうちは、他のページへのアクセスをすべて
オンボーディングへリダイレクトする。
"""
import json

from flask import Flask, jsonify, redirect, render_template, request, send_file, url_for

from . import autostart
from .analysis import aggregate_by_keyboard, aggregate_daily, aggregate_period, build_bursts
from .config import save_config
from .icons import icon_path_for, keyboards_with_dedicated_icon


def create_app(db, state, config):
    app = Flask(__name__)
    burst_gap_seconds = config["burst_gap_seconds"]
    typo_window_seconds = config["typo_window_seconds"]

    def _bursts():
        events = db.fetch_events()
        return build_bursts(events, burst_gap_seconds, typo_window_seconds)

    def _daily_summary():
        return aggregate_daily(_bursts())

    @app.before_request
    def _require_onboarding():
        if config.get("onboarding_done") or request.endpoint in ("onboarding", "static"):
            return None
        return redirect(url_for("onboarding"))

    @app.route("/onboarding", methods=["GET", "POST"])
    def onboarding():
        if request.method == "POST":
            no_external = request.form.get("no_external") == "on"
            if not no_external:
                name = (request.form.get("name") or "").strip()
                if name:
                    state.set_keyboard(name, method="manual")
            if request.form.get("register_startup") == "on":
                try:
                    autostart.register()
                except Exception:
                    # スタートアップ登録に失敗しても、README記載の手動手順にフォールバック
                    # できるので、オンボーディング自体は継続する。
                    pass
            config["onboarding_done"] = True
            save_config(config)
            return redirect(url_for("index"))
        return render_template("onboarding.html")

    @app.route("/")
    def index():
        summary = _daily_summary()
        keyboards = [name for (_id, name) in db.list_keyboards()]
        return render_template(
            "dashboard.html",
            summary=summary,
            summary_json=json.dumps(summary),
            current_keyboard=state.keyboard_name,
            keyboards=keyboards,
            icon_keyboards=keyboards_with_dedicated_icon(),
            icon_keyboards_json=json.dumps(keyboards_with_dedicated_icon()),
            auto_open_dashboard_on_startup=config.get("auto_open_dashboard_on_startup", True),
        )

    @app.route("/api/summary")
    def api_summary():
        range_type = request.args.get("range")
        if range_type in ("week", "month", "year"):
            return jsonify(aggregate_period(_bursts(), range_type))
        return jsonify(_daily_summary())

    @app.route("/api/keyboard_summary")
    def api_keyboard_summary():
        return jsonify(aggregate_by_keyboard(_bursts()))

    @app.route("/api/current_keyboard")
    def api_current_keyboard():
        return jsonify({"keyboard": state.keyboard_name})

    @app.route("/icons/<path:keyboard_name>.png")
    def keyboard_icon(keyboard_name):
        return send_file(icon_path_for(keyboard_name), mimetype="image/png")

    @app.route("/settings/auto_open_dashboard", methods=["POST"])
    def set_auto_open_dashboard():
        config["auto_open_dashboard_on_startup"] = request.form.get("enabled") == "on"
        save_config(config)
        return redirect(url_for("index"))

    @app.route("/keyboards/switch", methods=["POST"])
    def switch_keyboard():
        name = (request.form.get("name") or "").strip()
        if name:
            state.set_keyboard(name, method="manual")
        return redirect(url_for("index"))

    @app.route("/keyboards/add", methods=["POST"])
    def add_keyboard():
        name = (request.form.get("name") or "").strip()
        if name:
            state.set_keyboard(name, method="manual")
        return redirect(url_for("index"))

    @app.route("/keyboards/new-device")
    def new_device():
        device_key = request.args.get("key", "")
        keyboards = [name for (_id, name) in db.list_keyboards()]
        return render_template("new_device.html", device_key=device_key, keyboards=keyboards)

    @app.route("/keyboards/new-device/link", methods=["POST"])
    def link_device():
        device_key = (request.form.get("device_key") or "").strip()
        name = (request.form.get("name") or "").strip()
        if device_key and name:
            db.set_device_keyboard(device_key, name)
            state.set_keyboard(name, device_key=device_key, method="manual")
        return redirect(url_for("index"))

    return app
