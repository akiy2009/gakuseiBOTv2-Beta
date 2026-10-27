# HSS 時間割連携

## 概要

このプロジェクトでは、HSS-Project が公開している [HSS.py](https://github.com/HSS-Project/HSS.py) パッケージを使い、設定済みの学校・学年・クラスの曜日別時間割を `/timetable` コマンドで表示します。

HSS.py 本体を `cogs/` や `py-module/` に複製して管理する方式は採用しません。API ラッパーは upstream を依存関係として利用し、Bot 側には Discord コマンドと設定・エラー処理だけを置きます。

## 対応環境

- Bot 本体: Python 3.10 以上
- HSS 時間割機能: Python 3.11 以上
- HSS.py: upstream のパッケージ。追加依存関係は `requirements-hss.txt` で別管理

HSS.py の現在の `hss/types.py` は `typing.NotRequired` を import します。`typing.NotRequired` は Python 3.11 で標準ライブラリに追加されたため、HSS 連携には Python 3.11 以上を使用してください。upstream のパッケージメタデータには Python 3.10 classifier もありますが、ここでは実装コードの import 要件を優先しています。

## インストールと設定

1. Python 3.11 以上の仮想環境を有効にします。
2. リポジトリのルートから追加依存関係を入れます。

   ```bash
   python -m pip install -r requirements-hss.txt
   ```

3. HSS API の application 画面で発行した token を、秘密の環境変数 `HSS_API_TOKEN` に設定します。
4. `.env` に次の項目を設定します。

   ```dotenv
   HSS_API_TOKEN=ここに実際のtokenを設定
   HSS_SCHOOL_ID=123
   HSS_GRADE=2
   HSS_CLASS=3
   ```

   上記の ID は形式を示す例であり、実在する学校・学年・クラスを保証するものではありません。利用する HSS アカウントで参照できる ID に置き換えてください。

5. Bot を再起動し、Discord で `/timetable` を実行して曜日を選択します。

設定ファイル、token、学校情報をコミットしないでください。HSS token を利用者から Discord 上で直接入力・収集する機能は設けていません。

## 実装ファイル

- `cogs/normal/timetable.py`: slash command、任意依存関係の初期化、学校とクラスの選択、結果の表示、終了時の HTTP session cleanup。
- `requirements-hss.txt`: HSS.py を Bot 本体の必須依存関係から分離。
- `tests/test_hss_timetable.py`: 未設定時の安全な動作、整形、モック HSS client の初期化・終了を確認。
- `docs/study/api-reference.md`: この Bot が利用する HSS API の範囲と upstream へのリンク。

## 動作仕様と制約

- HSS の 4 つの設定値がすべてある場合のみ HSS client の初期化を試みます。不足している場合、Bot は HSS API に接続しません。
- 初期化エラー、ライブラリ未導入、Python バージョン不一致、学校・クラスが見つからない状態は、Bot 本体の起動失敗にせず状態として扱います。
- コマンドの応答は ephemeral で、実行した利用者だけに表示されます。メッセージ内の mention は無効化します。
- 現在の実装は環境変数で指定した 1 校・1 学年・1 クラスの時間割を表示する用途です。ユーザーごとの認証、学校の登録フロー、時間割の編集、キャッシュの自動再取得は実装していません。
- upstream README は `Client.setup()` がアクセス可能な学校をメモリへ読み込み、頻繁な呼び出しを避けるよう説明しています。この Bot では Cog のロード時に一度だけセットアップします。
- 実 API の token がない CI ではモックによるテストのみ行います。実際の API 権限・接続・返却形式は、利用環境の token で別途確認する必要があります。

## upstream とライセンスの出典

- Source code: [HSS-Project/HSS.py](https://github.com/HSS-Project/HSS.py)
- Package: [HSS.py on PyPI](https://pypi.org/project/HSS.py/)
- Official API documentation: [HSS API docs](https://hss-dev-docs.aknet.tech/)

HSS.py の `setup.py` には `license='MIT'` および MIT classifier が記載されています。一方、確認時点の GitHub リポジトリのルートには独立した `LICENSE` ファイルが見当たりませんでした。したがって、この記載は upstream のパッケージメタデータに基づくものであり、ライセンス本文をこのリポジトリで再配布しているわけではありません。HSS.py のソースコードをコピー・改変・再配布する場合は、最新の upstream 配布物と権利者の案内を再確認してください。本プロジェクトは HSS.py のソースを複製せず、パッケージとして利用します。
