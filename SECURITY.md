# 🛡️ gakuseiBOTv2 セキュリティガイド

## 🚨 重要な初期設定

### 1. 環境変数の設定

**必須**: Botを起動する前に以下の環境変数を設定してください：

```bash
# Discord Bot設定
DISCORD_TOKEN=your_discord_bot_token_here
PREFIX=/

# 管理者・開発者設定
DEVELOPER_ID=your_discord_user_id_here
REPORT_CHANNEL_ID=your_report_channel_id_here
FEEDBACK_CHANNEL_ID=your_feedback_channel_id_here
```

### 2. .envファイルの作成

1. `.env.example`を`.env`にコピー
2. 実際の値を入力
3. `.env`ファイルがGitに含まれないことを確認

```bash
cp .env.example .env
# .envファイルを編集して実際の値を設定
```

## 🔒 セキュリティ機能

### トークン保護
- ✅ Discord Botトークンは環境変数で管理
- ✅ `.gitignore`で機密ファイルをGit追跡から除外
- ✅ ハードコードされた機密情報を削除

### URL短縮セキュリティ
- ✅ プライベートIPアドレスをブロック
- ✅ 悪意のあるドメインをブロック
- ✅ URLバリデーション機能
- ✅ タイムアウト設定

### エラーハンドリング
- ✅ 詳細なエラー情報の漏洩を防止
- ✅ ログには詳細情報、ユーザーには要約のみ表示
- ✅ 例外処理の強化

### 権限管理
- ✅ 開発者権限の統一チェック
- ✅ 環境変数による権限設定
- ✅ 権限エラーメッセージの統一

## ⚠️ セキュリティ注意事項

### DO ✅
- 環境変数でトークンと機密情報を管理
- 定期的にBotトークンを再生成
- `.env`ファイルをGitに含めない
- プロダクション環境では`DEBUG=false`を設定

### DON'T ❌
- トークンをソースコードにハードコード
- `.env`ファイルを公開リポジトリにプッシュ
- エラーメッセージで詳細情報を漏洩
- 本番環境でデバッグモードを有効化

## 🔧 環境変数一覧

| 変数名 | 必須 | 説明 | デフォルト値 |
|--------|------|------|-------------|
| `DISCORD_TOKEN` | ✅ | Discord Botトークン | なし |
| `DEVELOPER_ID` | ✅ | 開発者のDiscord UID | なし |
| `REPORT_CHANNEL_ID` | ⚠️ | レポート送信チャンネル | なし |
| `FEEDBACK_CHANNEL_ID` | ⚠️ | フィードバック受信チャンネル | なし |
| `PREFIX` | - | コマンドプレフィックス | `/` |
| `DEBUG` | - | デバッグモード | `false` |
| `LOG_LEVEL` | - | ログレベル | `INFO` |

## 🚑 インシデント対応

### トークンが漏洩した場合

1. **即座にDiscord Developer Portalでトークンを再生成**
2. 環境変数を新しいトークンに更新
3. Botを再起動
4. 漏洩したトークンを含むコミット履歴の確認

### セキュリティ問題を発見した場合

1. 問題を詳細に記録
2. 可能な限り迅速に修正
3. 影響範囲を評価
4. 必要に応じてユーザーに通知

## 📞 サポート

セキュリティに関する質問や問題は：
- サポートサーバー: [Discord](https://discord.gg/9x3FwmPxhP)
- GitHub Issues: [報告](https://github.com/akiy2009/gakuseiBOTv2-Beta/issues)

---

> ⚡ **重要**: このガイドに従ってセキュアな環境でBotを運用してください。
