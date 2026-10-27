# gakuseiBOT v2 (Beta)

gakuseiBOT v2 は、学習支援やリマインダー、サーバー運営向けの機能を提供する Discord Bot です。

公式サイト: https://gakuseibot.com

## 動作環境

- Python 3.10 以上
- Discord Bot application と Bot token
- Discord Developer Portal で、利用する privileged intents を有効化していること
- Bot を招待する際は OAuth2 scopes に `bot` と `applications.commands` を指定すること

## ローカルで起動する

```bash
git clone https://github.com/akiy2009/gakuseiBOTv2-Beta.git
cd gakuseiBOTv2-Beta
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Windows PowerShell では仮想環境を `py -3 -m venv .venv` で作成し、`.\.venv\Scripts\Activate.ps1` を実行してから、`Copy-Item .env.example .env` で設定ファイルを作成してください。

`.env` の `DISCORD_TOKEN` を実際の Bot token に変更してから起動します。

```bash
python main.py
```

詳しい手順、環境変数、権限設定、運用方法は [ドキュメント](docs/index.md) を参照してください。

## Docker Compose で起動する

Docker Engine と Docker Compose v2 がインストールされた環境で、`.env` を用意してから実行します。

```bash
docker compose up -d --build
docker compose logs -f bot
```

停止する場合:

```bash
docker compose down
```

実行データは名前付き volume に保存されます。Bot token はイメージに含めず、Compose の環境変数として渡してください。

## HSS 時間割連携（任意）

[HSS-Project/HSS.py](https://github.com/HSS-Project/HSS.py) を使った時間割表示機能を任意で有効化できます。HSS ライブラリ本体をこのリポジトリに複製せず、追加依存関係として利用します。

1. Python 3.11 以上の環境で `python -m pip install -r requirements-hss.txt` を実行します。
2. `.env` に `HSS_API_TOKEN`、`HSS_SCHOOL_ID`、`HSS_GRADE`、`HSS_CLASS` を設定します。
3. Bot を再起動し、Discord の `/timetable` コマンドを使います。

HSS 連携は未設定でも通常の Bot 起動を妨げません。詳細は [HSS 連携ガイド](docs/study/hss-integration.md) を確認してください。

## 開発時のチェック

```bash
python -m pip check
python -m compileall -q main.py cogs
python -m pip install pytest
python -m pytest -q
```

ドキュメントのビルド:

```bash
python -m pip install -r requirements-docs.txt
sphinx-build -W --keep-going -b html docs build/manual-docs
pdoc --output-dir build/api-docs cogs
```

GitHub Actions では Python 3.10 / 3.11 / 3.12 で依存関係・構文・テストを確認し、ドキュメントをビルドします。PR の会話欄にはチェック状況が自動投稿され、再実行時は既存の要約コメントが更新されます。
