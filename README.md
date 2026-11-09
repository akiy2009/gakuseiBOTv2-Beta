# gakuseiBOT v2 (Beta)

gakuseiBOT v2 は、学習支援・リマインダー・Discord サーバー運営を支援する Discord Bot です。

- 公式サイト: https://gakuseibot.com
- 開発言語: Python 3.12
- Bot framework: discord.py
- 実行方式: ローカル / Docker Compose

> **開発版について**
> このリポジトリは Beta 版です。本番環境へ導入する前に、変更内容・必要な権限・設定値を確認してください。

## 動作環境

- **Python 3.12.x（必須）**
- Git
- Discord Developer Portal で作成した Bot application と Bot token
- Docker Compose v2（Docker で実行する場合）

Bot が利用する privileged intents は Discord Developer Portal で有効化してください。招待 URL には OAuth2 scopes の `bot` と `applications.commands` を指定し、必要最小限の権限を付与してください。

## ローカルで起動する

### 1. リポジトリを取得

```bash
git clone https://github.com/akiy2009/gakuseiBOTv2-Beta.git
cd gakuseiBOTv2-Beta
```

### 2. Python 3.12 の仮想環境を作成

Windows PowerShell:

```powershell
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
```

macOS / Linux:

```bash
python3.12 --version
python3.12 -m venv .venv
source .venv/bin/activate
python --version
```

表示が `Python 3.12.x` であることを確認してから、依存関係をインストールします。

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. 環境変数を設定

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

作成した `.env` の `DISCORD_TOKEN` を実際の Bot token に置き換えてください。token をソースコード、Issue、PR、ログへ記載しないでください。

### 4. 起動

```bash
python main.py
```

## Docker Compose で起動する

Docker Engine と Docker Compose v2 を用意し、リポジトリのルートに `.env` を作成してから実行します。

```bash
docker compose config --quiet
docker compose up -d --build
docker compose logs -f bot
```

停止:

```bash
docker compose down
```

実行データは名前付き volume に保存されます。Bot token は Docker image に含めず、環境変数として渡してください。

## HSS 時間割連携（任意）

[HSS-Project/HSS.py](https://github.com/HSS-Project/HSS.py) を利用した時間割表示機能を追加できます。HSS 連携を含め、実行環境は **Python 3.12.x に統一**します。

- ローカル: `python -m pip install -r requirements-hss.txt`
- Docker Compose: `.env` の `INSTALL_HSS=true` を設定し、`docker compose up -d --build` で再ビルド

`HSS_API_TOKEN`、`HSS_SCHOOL_ID`、`HSS_GRADE`、`HSS_CLASS` を設定して Bot を再起動してください。通常の Bot 機能には HSS の追加パッケージは必要ありません。詳しくは [HSS 連携ガイド](docs/study/hss-integration.md) を参照してください。

## 開発・テスト

仮想環境を有効にした状態で実行します。

```bash
python --version
python -m pip install -r requirements.txt
python -m pip install pytest
python -m pip check
python -m compileall -q main.py cogs
python -m pytest -q
```

ドキュメントのビルド:

```bash
python -m pip install -r requirements-docs.txt
sphinx-build -W --keep-going -b html docs build/manual-docs
pdoc --output-dir build/api-docs cogs
```

GitHub Actions も Python 3.12 で品質チェックとドキュメントビルドを実行します。

## ドキュメント

- [セットアップガイド](docs/getting-started.md)
- [環境変数・設定](docs/configuration.md)
- [アーキテクチャ](docs/architecture.md)
- [開発と品質確認](docs/development.md)
- [運用とデプロイ](docs/operations.md)
- [ドキュメント一覧](docs/index.md)

## 貢献

不具合報告・改善提案・Pull Request を歓迎します。変更を提案する際は、目的・変更内容・確認したテストを記載してください。詳細は [CONTRIBUTING.md](CONTRIBUTING.md) を確認してください。

## License

ライセンス条件はリポジトリ内の [LICENSE](LICENSE) を参照してください。
