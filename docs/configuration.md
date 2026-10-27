# 環境変数と設定

設定値はプロセス環境変数またはリポジトリ直下の `.env` から読み込みます。実際の環境変数は `.env` の値より優先されます。

## Bot 本体

| 変数 | 必須 | 既定値 | 用途 |
| --- | --- | --- | --- |
| `DISCORD_TOKEN` | はい | なし | Discord Bot token。未設定なら起動時に終了します。 |
| `PREFIX` | いいえ | `/` | prefix command の接頭辞。空欄は既定値に戻ります。 |
| `DEVELOPER_ID` | いいえ | 空欄 | 開発者向け機能が参照する Discord ユーザー ID。 |
| `REPORT_CHANNEL_ID` | いいえ | 空欄 | 起動ログの送信先チャンネル ID。未設定なら自動送信しません。 |
| `FEEDBACK_CHANNEL_ID` | いいえ | 空欄 | `/feedback` の送信先チャンネル ID。 |
| `HEAVY_THRESHOLD` | いいえ | `1.5` | Cog 読み込み時間の警告閾値（秒）。正の数値以外は既定値を使用します。 |
| `HEAVY_COGS_PATH` | いいえ | `data/heavy_cogs.json` | 読み込みをスキップする Cog 一覧を保存する JSON ファイル。 |

`REPORT_CHANNEL_ID` と `FEEDBACK_CHANNEL_ID` には、Bot が閲覧でき、必要なメッセージを送信できるテキストチャンネル ID を設定します。ID を取得するには Discord の開発者モードを有効にします。

## HSS 時間割連携（任意）

以下の 4 項目を**すべて**設定した場合だけ、HSS クライアントの初期化を試みます。

| 変数 | 必須（HSS を使う場合） | 用途 |
| --- | --- | --- |
| `HSS_API_TOKEN` | はい | HSS API application token。秘密情報として管理します。 |
| `HSS_SCHOOL_ID` | はい | 表示対象の学校 ID（正の整数）。 |
| `HSS_GRADE` | はい | 表示対象の学年（正の整数）。 |
| `HSS_CLASS` | はい | 表示対象のクラス番号（正の整数）。 |

HSS の追加依存関係は `requirements-hss.txt` で別管理します。HSS-Project/HSS.py の現在の実装に合わせ、連携には Python 3.11 以上を使用します。HSS を設定しなくても Bot 本体は起動し、`/timetable` は未設定メッセージを返します。

## 秘密情報の取り扱い

- `.env`、token、API key をコミットしないでください。例示ファイルにはプレースホルダーだけを記載します。
- token をログや Discord メッセージに出さないでください。公開してしまった token は無効化し、新しいものを発行してください。
- デプロイ先では GitHub Actions の Secrets とサーバー上の `.env` を使い分けます。環境変数の値そのものをドキュメントや CI ログに出力しないでください。
