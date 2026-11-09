# セットアップガイド

## 必要なもの

- **Python 3.12.x（必須）**
- Discord Developer Portal で作成した Bot application と token
- Git
- Bot を追加する Discord サーバーで、必要な権限を設定できること

HSS 時間割連携も含め、すべての機能で Python 3.12.x を使用します。通常の Bot 機能には HSS の追加パッケージは必要ありません。

## 1. ソースを取得

```bash
git clone https://github.com/akiy2009/gakuseiBOTv2-Beta.git
cd gakuseiBOTv2-Beta
```

## 2. Python 3.12 の仮想環境を作成

Windows PowerShell:

```powershell
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

macOS / Linux:

```bash
python3.12 --version
python3.12 -m venv .venv
source .venv/bin/activate
python --version
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

仮想環境を有効にした後、`python --version` が `Python 3.12.x` と表示されることを確認してください。

## 3. Discord の token と intents を設定

```bash
cp .env.example .env
```

Windows PowerShell では次を使います。

```powershell
Copy-Item .env.example .env
```

`.env` を開き、`DISCORD_TOKEN` を実際の token に置き換えてください。token はソースコード、Issue、PR、スクリーンショット、ログに貼り付けないでください。

Discord Developer Portal で、コードが使用する privileged intents（Message Content、Server Members など）を有効にしてください。Bot を招待するときは `bot` と `applications.commands` の OAuth2 scopes を選び、利用するコマンドに必要な権限だけを付与します。

## 4. ローカル起動

```bash
python main.py
```

起動ログにログインとスラッシュコマンド同期の結果が表示されます。初回同期後、Discord 側にコマンドが反映されるまで少し時間がかかる場合があります。

## 5. Docker Compose で起動

Docker Engine と Docker Compose v2 を用意し、リポジトリのルートで `.env` を設定してから実行します。Dockerfile は Python 3.12 ベースのイメージを使用します。

```bash
docker compose config --quiet
docker compose up -d --build
docker compose logs -f bot
```

停止は `docker compose down`、再ビルドは `docker compose up -d --build` です。Bot の実行データは名前付き volume に保存されます。

## 6. HSS 時間割機能（任意）

HSS 時間割機能も Python 3.12.x 環境で利用します。

- ローカル: `python -m pip install -r requirements-hss.txt`
- Docker Compose: `.env` の `INSTALL_HSS=true` に変更し、`docker compose up -d --build` でイメージを再ビルド

次に `HSS_API_TOKEN`、`HSS_SCHOOL_ID`、`HSS_GRADE`、`HSS_CLASS` を設定して Bot を再起動し、Discord の `/timetable` を実行します。詳細は [HSS 連携ガイド](study/hss-integration.md) を参照してください。

## 関連ドキュメント

- [環境変数一覧](configuration.md)
- [Bot の内部構成](architecture.md)
- [本番運用とデプロイ](operations.md)
- [HSS 連携の有効化](study/hss-integration.md)
