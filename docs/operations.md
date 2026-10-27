# 運用とデプロイ

## Docker Compose

本リポジトリには `Dockerfile` と `compose.yaml` を用意しています。サーバーに Docker Engine / Compose v2 をインストールし、リポジトリのルートに秘密の `.env` を用意して実行します。

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 bot
```

更新時はレビュー済みの commit を取得してから `docker compose up -d --build --remove-orphans` を実行します。停止は `docker compose down` です。Bot の実行データは `bot-data` という名前付き volume に保持されます。`docker compose down -v` は保存データを消去するため、必要性を確認してから実行してください。

## GitHub Actions による VPS デプロイ

`.github/workflows/deploy.yml` は `main` への push または手動実行時に動作します。GitHub Actions の repository Secrets に次の値を登録してください。

| Secret | 用途 |
| --- | --- |
| `SERVER_IP` | デプロイ先ホスト名または IP アドレス |
| `SSH_USER` | SSH 接続ユーザー |
| `SSH_KEY` | デプロイ用 SSH 秘密鍵 |

リモートサーバー上にリポジトリを `~/gakuseiBOT` として配置し、同ディレクトリに `.env` を安全に作成しておく必要があります。Workflow は `main` のコードを取得して Compose イメージをビルドし、サービスを更新します。初回は事前にサーバー側で Git、Docker Engine、Docker Compose v2、SSH 鍵認証を準備してください。

## 障害時の確認

1. `docker compose ps` でコンテナが再起動を繰り返していないか確認します。
2. `docker compose logs --tail=200 bot` で起動エラーを確認します。ログを共有する際は token や API key が含まれていないことを確認してください。
3. Discord Developer Portal の token、intents、Bot 権限、チャンネル ID を確認します。
4. HSS を利用する場合は、HSS token の有効性、学校 ID、学年・クラス番号、ネットワーク接続、追加依存関係を確認します。

token をログへ出力する修正は行わないでください。秘密情報を誤って公開した場合は、該当 token を無効化して再発行します。
