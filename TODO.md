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
- [x] 実機での最終確認(2026-09-16、ユーザー確認): アプリ再起動→デフォルト状態→USB抜き差しで新規デバイス登録画面に誘導→登録後、favicon が作成したキーボードのアイコンに追従することを確認

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
- [x] (ユーザー側)実機での動作確認(2026-09-16): アプリ再起動時に挿さった状態→default、USB抜き差しで未登録デバイス検出→登録画面への誘導、を確認。登録済みデバイスの猶予期間中の挙動・Bluetoothキーボードでの検出可否は未確認のまま(必要になったら追って確認)

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
- [x] GitHub Public新規リポジトリ`IbushiGinjiro/typing-activity-tracker`作成、push前にファイル一覧を最終確認してからpush(https://github.com/IbushiGinjiro/typing-activity-tracker)
- [x] GitHub Releases v1.0.0に.exe添付(https://github.com/IbushiGinjiro/typing-activity-tracker/releases/tag/v1.0.0)
- [x] KNOWLEDGE.mdに配布作業で得た気付きを追記(PyInstallerの3つの落とし穴)

## 5. 起動時に既に接続済みのキーボードを検知できない不具合の修正(2026-09-17)
- [x] `DeviceWatcher.start()`の順序を変更: Creation/Deletionの`watch_for`サブスクリプション確立を待ってから初期スキャンを行うようにする(取りこぼし防止)
- [x] `DeviceWatcher._scan_initial()`を追加: `Win32_PnPEntity(PNPClass="Keyboard")`で現在接続中のデバイスを列挙し、`device_keyboards`に登録済みのものが見つかったら`_switch_to`+`notify_switch`(複数該当時は最初の1件のみ採用)
- [x] 単体テスト追加(`tests/test_device_watch.py`): 起動時スキャンで登録済みデバイスが見つかり自動切替されるケース、見つからない(未登録 or 接続無し)ケース、複数登録済みデバイスが同時接続されている場合は最初の1件のみ採用するケース(全33件パス)
- [x] 動作確認: ユーザー側で実機確認 → **実際にはdefaultから変わらず、不具合再現**(2026-09-17)
- [x] 原因調査用に`device_watch.py`へデバッグログ出力を追加(`data/device_watch.log`。初期スキャンで見つかったデバイス一覧・各device_keyの登録有無・Creation/Deletionイベント受信も記録)。pythonw実行はコンソールが無く原因が見えないための対応
- [x] ユーザー側でアプリ再起動→再現→`data/device_watch.log`の内容を確認して原因特定
      → **`_scan_initial`自体は正常動作**(PNPClass=Keyboardのデバイス6件を正しく検出・VID/PID抽出も正常)。
      原因は`device_keyboards`テーブルを直接確認したところ判明: 「自宅TH40%」は`device_key`が登録されているが、
      **「職場aula65%」にはそもそも`device_key`が1件も登録されていなかった**(常時挿しっぱなしで一度も
      「新規デバイス検出」の抜き差しフローを通っていなかったため)。初期スキャン・着脱イベントどちらの
      経路でも、未登録デバイスは自動切替のしようがない(これは仕様通り)。
- [x] ユーザー側で職場aulaのケーブルを一度抜き差しし、「新規デバイス検出」トースト→ダッシュボードの
      登録画面で「職場aula65%」に紐付け、検知に成功したことを確認(2026-09-17)
- [ ] KNOWLEDGE.mdに気付きを追記

## 8. 抜き差し時に「新しいキーボードを検知しました」が登録済みキーボードの通知より先に出る(2026-09-17)
- [x] 原因: USB複合デバイスの抜き差し1回で、無関係な他のPnPデバイス(ハブ・レシーバー等でPNPClassが
      たまたまKeyboardになっているもの)のCreationイベントがほぼ同時に複数発生することがあり、
      たまたま未登録デバイスの方が先に処理されると「新しいキーボードを検出しました」が先に出る
- [x] `DeviceWatcher`にCreationイベントの短時間バッチ処理を追加(`creation_batch_seconds`、既定2秒)。
      同じ時間窓に届いたdevice_keyをまとめて判定し、登録済みのものが1つでもあればそちらを優先して
      自動切替(未登録の通知は出さない)。バッチ内が全部未登録の場合のみ、まとめて1回だけ通知する
- [x] `config.json`に`device_creation_batch_seconds`(既定2.0)を追加、`main.py`から渡すように変更
- [x] 単体テスト追加(登録済み+未登録が同時到着→登録済み優先・未登録通知無し、全部未登録→通知1回のみ、
      時間窓の外なら別々に処理、既存の抜き差しシナリオも全て通ることを確認。全42件パス)
- [ ] (ユーザー側)実機で確認

## 10. スタートアップ登録・ダッシュボード自動起動(2026-09-17)
- [x] `app/autostart.py`新設: `shell:startup`フォルダへのショートカット作成/削除/登録確認(`win32com.client`、frozen/非frozen両対応)
- [x] `app/config.py`に`auto_open_dashboard_on_startup`(既定true)を追加
- [x] `app/main.py`: Flaskサーバ起動後、設定が有効なら`webbrowser.open(dashboard_url)`
- [x] オンボーディング画面に「Windowsのスタートアップに登録する(推奨)」チェックボックス(既定ON)を追加、送信時に`autostart.register()`を呼ぶ(失敗しても致命的にはしない)
- [x] ダッシュボードに「起動時にダッシュボードを自動で開く」チェックボックスを追加、変更時にfetchで即時`/settings/auto_open_dashboard`へ反映・`config.json`に保存
- [x] 単体テスト追加(`tests/test_autostart.py`: ショートカットパス生成、frozen/非frozen判定、pythonw不在時のフォールバック。全47件パス)
- [x] Flaskテストクライアント+ブラウザで動作確認(オンボーディングのチェックボックス表示、送信時の`autostart.register()`呼び出し、ダッシュボードのチェックボックス表示・トグルの永続化)
- [x] READMEに追記
- [ ] (ユーザー側)実機で確認(スタートアップ登録が実際に機能するか、PC再起動を伴うため要実機確認)

## 9. ダッシュボード微調整(2026-09-17)
- [x] キーボード別タブのグラフが期間別タブと比べて縦にすごく大きくなる不具合を修正
      (`flex-basis:100%; max-width:100%`の独自スタイルをやめ、他タブと同じ`.chart-box`サイズに統一)
- [x] キーボード別タブに2つ目のグラフ(円グラフ: 使用日数(メイン機)の内訳)を追加
- [x] 実際にブラウザ(claude-in-chrome)でサイズ・円グラフ描画を確認済み
- [x] ユーザー確認: 棒グラフはOK、円グラフだけ縦に大きすぎるとの指摘
      → 原因はChart.jsの円グラフのデフォルト縦横比(1:1)が棒グラフ側(2:1)と異なるため。
      `aspectRatio: 2`を明示指定して棒グラフと高さを揃え、ブラウザで確認済み
- [ ] (ユーザー側)実機で最終確認

## 7. Chart.jsのCDNバージョンが失効しグラフが描画されない不具合(2026-09-17)
- [x] 原因特定: `dashboard.html`に固定していたcdnjs上の`Chart.js/4.4.4/chart.umd.min.js`が
      cdnjs側から削除されており(バージョン一覧照会で確認)、自宅・会社どちらの環境でも404になっていた
      (ネットワーク・プロキシの問題ではなかった)
- [x] 現在cdnjsに存在する`4.5.1`に固定バージョンを更新(`chart.umd.min.js`のファイル名は変わらず存在)
- [x] 実際にブラウザ(claude-in-chrome)でグラフが描画されることを確認済み
- [ ] (ユーザー側)実機で確認

## 6. ダッシュボード改良(2026-09-17)
- [x] `app/icons.py`に`keyboards_with_dedicated_icon()`追加(専用アイコンが無いラベルはデフォルトにフォールバックさせず判定できるように)
- [x] 日次表・サマリ各表のキーボード名の左に専用アイコンを表示(専用アイコンが無いものは空欄)
- [x] 「期間サマリ」を「サマリ」に改名し、「期間別」「キーボード別」のタブ切替構成にリファクタ
- [x] `app/analysis.py`に`aggregate_by_keyboard()`追加: 月平均セッション数(実使用月数で除算)、使用日数(メイン機。100超え or 10超え+他キーボード未使用の日をカウント)、累計セッション数・総打鍵数・速度中央値・即時訂正率・書き直し回数
- [x] `/api/keyboard_summary`エンドポイント追加
- [x] 「キーボード別」タブに、表のすぐ上へ月別入力セッション数のキーボード別グラフを追加(`/api/summary?range=month`を再利用)
- [x] 単体テスト追加(`aggregate_by_keyboard`: 月平均の分母、使用日数の各境界条件。全39件パス)
- [x] Flaskテストクライアント+実際にブラウザ(claude-in-chrome)で確認: タブ切替、専用アイコン有り/無しキーボードでの表示差、`/api/keyboard_summary`の値
- [ ] (ユーザー側)実機での見た目確認・要望との認識合致の確認
