# gakuseiBOT v2 ドキュメント

このドキュメントは、ローカル開発から本番運用までの手順と、各機能の利用方法をまとめたものです。

```{toctree}
:maxdepth: 2
:caption: ガイド

README
getting-started
configuration
architecture
operations
supabase-keepalive
health-monitoring
reminders
development
gc/rule
study/hss-integration
study/api-reference
generated/commands
generated/environment
```

## クイックリンク

- [セットアップ](getting-started.md)
- [設定一覧](configuration.md)
- [Supabase 定期ヘルスチェック](supabase-keepalive.md)
- [Bot ヘルスチェックと管理者通知](health-monitoring.md)
- [リマインダー機能](reminders.md)
- [HSS 時間割連携](study/hss-integration.md)
- [テストとドキュメントのビルド](development.md)

## 自動生成リファレンス

- [Discord コマンド一覧（ソースコードから自動生成）](generated/commands.md)
- [環境変数一覧（.env.example とソースコードから自動生成）](generated/environment.md)
