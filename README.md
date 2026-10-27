# gakuseiBOT v2 (Beta)

gakuseiBOT v2 は、学習時間の管理やリマインダーなどを提供する Discord Bot です。

公式サイト: https://gakuseibot.com

## 動作環境

- Python 3.10 以上
- Discord Bot application と Bot token
- Discord Developer Portal で、プロジェクトが利用する privileged intents を有効化していること
- Bot を招待する際は `bot` と `applications.commands` の OAuth2 scopes を指定すること

## セットアップ

### 1. リポジトリを取得

```bash
git clone https://github.com/akiy2009/gakuseiBOTv2-Beta.git
cd gakuseiBOTv2-Beta
```

### 2. 仮想環境を作成して依存関係をインストール

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. 環境変数を設定

`.env.example` を `.env` にコピーし、少なくとも `DISCORD_TOKEN` を実際の Bot token に変更してください。運営向け機能を使う場合は、各機能に対応する ID も設定してください。

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS / Linux:

```bash
cp .env.example .env
```

トークンをソースコードや GitHub に書き込まないでください。`.env` は Git の追跡対象外です。

### 4. 起動

リポジトリのルートディレクトリで実行します。

```bash
python main.py
```

起動後、コンソールにログインとスラッシュコマンド同期の結果が表示されます。同期に失敗した場合はエラーログと Bot の権限設定を確認してください。

## 主な設定

| 変数 | 用途 |
| --- | --- |
| `DISCORD_TOKEN` | Bot token（必須） |
| `PREFIX` | prefix command の接頭辞（既定値: `/`） |
| `DEVELOPER_ID` | 開発者向けコマンドの使用者 ID |
| `REPORT_CHANNEL_ID` | 起動ログ・報告の送信先として使用するチャンネル ID |
| `FEEDBACK_CHANNEL_ID` | フィードバック送信先チャンネル ID |
| `HEAVY_THRESHOLD` | Cog 読み込み時間の警告閾値（秒、既定値: `1.5`） |

設定変更後は Bot を再起動してください。

## 開発時のチェック

```bash
python -m pip install -r requirements.txt
python -m pip install pytest
python -m pip check
python -m compileall -q main.py cogs
python -m pytest -q
```

GitHub Actions では Python 3.10 / 3.11 / 3.12 で依存関係・構文・テストを確認します。PR の会話欄にはチェック状況の要約が自動投稿され、再実行時は既存の要約コメントが更新されます。

不具合の報告や質問は GitHub Issues または公式サイトからお願いします。
