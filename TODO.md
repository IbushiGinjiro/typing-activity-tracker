# TODO.md

## セットアップ
- [x] プロジェクト雛形作成(requirements.txt, .gitignore, README.md, パッケージ構成)

## コア機能
- [x] キー入力キャプチャ(pynputでグローバルフック、キー種別+タイムスタンプのみ記録)
- [x] SQLiteスキーマ設計・実装(打鍵イベント、キーボードラベル)
- [x] バースト区切りロジック(閾値2秒、設定可能)
- [x] タイポ訂正/推敲の分類ロジック(閾値1秒、設定可能)
- [x] 集計ロジック(バースト単位・日次単位のCPM中央値、訂正率)

## タスクトレイアプリ
- [x] pystrayでタスクトレイ常駐化
- [x] キーボードラベルの登録・切り替えメニュー
- [x] ダッシュボードを開く/終了メニュー

## ダッシュボード
- [x] Flaskでローカルダッシュボード(日次・週次トレンド、キーボード別比較)

## 動作確認
- [x] バースト区切り・訂正分類ロジックの単体テスト(合成データ、`python -m unittest tests.test_analysis` で8件パス)
- [x] ダッシュボード表示の動作確認(合成データ投入、`/`と`/api/summary`ともHTTP 200を確認)
- [x] 実機でのキー入力キャプチャ動作確認(ユーザー側で `python -m app.main` を実行して確認、キーボード登録も確認済み)

## ドキュメント・配布準備
- [x] README.mdに「実際の入力文字列は記録しない」ことを明記
- [x] PyInstallerでのビルド手順メモ(実際のビルド・公開はv1完成後)

## KNOWLEDGE.md
- [x] 実装中に得た気付きを記録(pystrayのradio挙動、バックグラウンドプロセスのkill等)
- [ ] 実運用での閾値調整結果を随時追記

## ダッシュボードのカラム名改善(2026-09-08)
- [x] 「バースト数」「速度(CPM中央値)」「訂正率」「推敲回数」の見出しを分かりやすい表記に変更
- [x] 各見出しにホバーで計算式・単位が出るtitle属性を追加

## キーボード別タスクトレイアイコン(2026-09-15)
- [x] ピクセルデータ定義(Pillow描画)をコードで作成: f65/th40の2種(`app/assets/icons/generate_icons.py`)
- [x] 同じ描画データからPNG(`app/assets/icons/*.png`)と.piskel(`app/assets/icons/piskel/*.piskel`)を
      両方生成するスクリプトを実装
- [x] ラベル→アイコンファイルの対応表を追加(`app/tray.py`の`KEYBOARD_ICON_FILES`、未対応ラベルはデフォルトにフォールバック)
- [x] `app/tray.py`: `_load_icon_image()`を追加し初期表示・切替時の両方で使用、キーボード切替時に`icon.icon`を更新
- [x] 動作確認(単体テスト・登録済み2ラベル/未登録ラベルでの読み込み結果を確認、DB実データとの対応表一致を確認)
- [x] KNOWLEDGE.mdに気付きを追記
- [x] (ユーザー側)実機での見た目・切替の確認、Piskelでf65/th40の色・形を調整済み

## デフォルトアイコンをASUS Vivobook風に変更(2026-09-15)
- [x] `generate_icons.py`に`_draw_laptop()`を追加(黒っぽい筐体+キーボード行+タッチパッド)
- [x] `generate()`に`names`引数を追加し、ユーザー編集済みのf65/th40を上書きせず
      `default`アイコンだけを再生成できるようにした
- [x] `app/tray.py`: フォールバック先を旧・青丸生成関数から`default.png`読み込みに変更
      (ファイルが万一無い場合のみ旧・青丸を最終フォールバックとして残す)
- [x] 動作確認(各ラベルで読み込まれるファイル名が意図通りか確認)

## 1. ブラウザタブのfavicon連動(2026-09-16)
- [x] `app/icons.py`新設、`KEYBOARD_ICON_FILES`/`DEFAULT_ICON_FILE`/`ICON_DIR`を`tray.py`から移設し、両方から import する形にリファクタ
- [x] `AppState`(`app/state.py`)に変更通知の仕組み(コールバック登録・`on_change`)を追加
- [x] `TrayApp`側の切替ハンドラを`AppState`のコールバック経由でのicon更新に統一(手動切替・ダッシュボード切替・自動検出切替の3経路を1本化)
- [x] Flaskに`/icons/<keyboard_name>.png`配信ルートを追加
- [x] `dashboard.html`に`<link rel="icon">`を追加、`current_keyboard`に応じたパスを設定
- [x] `/api/current_keyboard`エンドポイント追加
- [x] `dashboard.html`にポーリングJS追加(数秒おきにfaviconを最新化)
- [x] Flaskテストクライアントでの動作確認(`/`にfaviconリンク、`/api/current_keyboard`、`%`を含むラベルでの`/icons/*.png`が200を返すこと)
- [ ] 実機での最終確認(タスクトレイ切替→favicon追従、ダッシュボード切替→トレイアイコン追従)はアプリ再起動が必要なため、2〜4の実装完了後にまとめて行う

## 2. キーボードの自動選択(2026-09-16)
- [x] `requirements.txt`に`WMI`・`winotify`を追加、インストール済み
- [x] DBスキーマに`device_keyboards(device_key TEXT PRIMARY KEY, keyboard_id INTEGER)`追加
- [x] `keyboard_switches`テーブル(ts, keyboard_id, device_key, method)を追加し、切替のたびに記録(事後訂正用の監査ログ。`events`へのカラム追加ではなく専用テーブルにした。理由はKNOWLEDGE.md参照)
- [x] `app/device_key.py`: DeviceIDからVID/PIDキーを抽出する関数(実機のWMI出力で動作確認済み)
- [x] PnP監視モジュール(`app/device_watch.py`)新設: `wmi`でPNPClass="Keyboard"のCreation/Deletionイベントを監視するバックグラウンドスレッド(スレッド2本、`stop_event`で終了可能)
- [x] Creation時: VID/PID抽出→`device_keyboards`照合→登録済みなら即切替+トースト、未登録ならトースト+クリックでダッシュボードの新規デバイス登録画面を開く
- [x] Deletion時: 現在のラベルに紐づくデバイスの場合のみ、5秒の猶予タイマーを開始(`config.json`の`device_grace_period_seconds`)+固定文言トースト。猶予中に同一デバイス再接続でキャンセル、別の登録済みデバイス接続で即座にそちらへ切替、タイムアウトでdefaultへ切替+通知
- [x] ダッシュボードに`/keyboards/new-device`(GET)・`/keyboards/new-device/link`(POST)ルート追加(登録済みリストから選択 or 新規登録)
- [x] `/onboarding`ルート・テンプレート追加(「外部接続キーボードを使わない」チェックボックス付き)、`config.json`に`onboarding_done`フラグ追加、`before_request`での分岐追加
- [x] 既存ユーザー(既にキーボード登録済み)は初回起動時にオンボーディングをスキップし`onboarding_done: true`を自動設定するマイグレーション処理(`main.py`の`_migrate_onboarding_flag`)
- [x] 単体テスト: VID/PID抽出ロジック(実機のDeviceID文字列で検証)、`DeviceWatcher`のシナリオ1〜4相当(既知デバイス切替、未知デバイス通知、猶予→フォールバック、猶予中再接続でのキャンセル、猶予中の別デバイス即時切替、手動切替でのdevice_key追跡リセット/引き継ぎ、VID/PID無しデバイスの無視)を`tests/test_device_watch.py`でカバー、全件パス
- [x] Flaskテストクライアントでオンボーディングのリダイレクト・完了後の`onboarding_done`永続化、新規デバイス登録画面の表示・紐付け(`device_keyboards`登録+即切替)を確認
- [ ] (ユーザー側)実機での動作確認: 新規デバイス検出→登録フロー、登録済みデバイスの抜き挿し、猶予期間中の挙動、Bluetoothキーボードでの検出可否(BLE HIDはVID/PIDが取れず自動検出対象外になる可能性がある。KNOWLEDGE.md参照)

## 3. 期間サマリ(週/月/年)(2026-09-16)
- [x] `analysis.py`に`aggregate_period(bursts, range_type)`追加(week=ISO週/month/yearでグルーピング、`aggregate_daily`と同様の指標)。単体テスト追加(ISO週の境界、月またぎ、年またぎ、不正なrange_typeでのValueError)
- [x] `/api/summary`に`range`クエリパラメータ追加(week/month/year、指定無しは従来通り日次)
- [x] `dashboard.html`に期間切替セレクト+グラフ2枚+表を追加(日次テーブルの下に新セクションとして追加、ページ遷移なし)
- [x] 動作確認: Flaskテストクライアントでの各range確認に加え、実際にブラウザ(claude-in-chrome)でダッシュボードを開き、週次→月次→年次の切替で表が正しく再取得・再描画されることを確認
- [x] **バグ発見・修正**: 既存の日次`buildChart()`呼び出しがtry/catch無しの状態で、Chart.jsのCDN読み込み失敗(実際にブラウザ確認中に503が発生し再現)時に例外を投げると、同じ`<script>`タグ内の**それ以降の全JS(期間サマリの初期読み込み・faviconポーリング)が丸ごと止まる**ことが分かった。日次グラフの呼び出しをtry/catchで囲み、`buildPeriodChart`も`Chart`未定義なら`null`を返してグラフ無し(表のみ)で継続するよう修正

## 4. 配布(2026-09-16)
- [x] 「実際の文字列を記録しない」ことを保証する単体テスト追加(`tests/test_capture.py`。`classify_key`が固定ラベルしか返さないこと、`KeyCapture._on_press`がDBに渡す値に生のキー情報が含まれないことを確認)
- [x] README.md配布向け整備(情シス確認の注記、同一モデル複数台の制約、2台同時非対応の明記、USB自動検出・期間サマリの説明追加)
- [x] PyInstallerで単一.exe化。**実際にビルドしたexeを動かして動作確認し、以下3件の不具合を発見・修正**:
      (1) `app/main.py`直接ビルドだと相対importが壊れる→`run.py`(絶対import)経由に変更、
      (2) `config.py`の`PROJECT_ROOT`が`__file__`基準だとfrozen時に毎回変わる一時フォルダを指し、
      打鍵データが起動のたびにリセットされてしまう重大な不具合→`sys.frozen`時は`sys.executable`の
      あるフォルダを基準にするよう修正、
      (3) `wmi.WMI()`をメインスレッドで作って別スレッドに渡すとCOM初期化エラーで監視スレッドが
      無言で死ぬ→各スレッド内で`pythoncom.CoInitialize()`してから接続を作るよう修正。
      詳細はKNOWLEDGE.md参照
- [x] 修正後、非公開の隔離フォルダ(別ポート・別config.json)で実際にexeを起動し、ダッシュボード応答・
      config.json/data/events.dbがexeの隣に正しく作られること・オンボーディング完了後にicons/index
      ルートが正常応答することを確認。本番稼働中のpythonwプロセス(ポート5151)には影響が無いことも確認
- [ ] GitHub Public新規リポジトリ`IbushiGinjiro/typing-activity-tracker`作成、push前に`git status`で最終確認してからpush
- [ ] GitHub Releasesに.exe添付
- [x] KNOWLEDGE.mdに配布作業で得た気付きを追記(PyInstallerの3つの落とし穴)
