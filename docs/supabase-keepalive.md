# Supabase の定期ヘルスチェック

## 目的と注意点

`.github/workflows/supabase-keepalive.yml` は GitHub Actions から Supabase Data API に定期アクセスし、専用の `public.ops_heartbeat` 行を upsert した後、読み戻して書き込みを検証します。

Supabase Free は、過去7日間のユーザーデータベースアクティビティが少ない場合にプロジェクトが自動 pause されることがあります。公式ドキュメントでは、通常は1日に数件のユーザーリクエストが目安とされています。そのため、この Workflow は週1回だけではなく、JST 06:00 / 14:00 / 22:00 の1日3回実行します。月曜06:00 JSTの実行は `monday_weekly` として記録されます。

**この仕組みは pause 回避を保証しません。** GitHub Actions の遅延・停止、GitHub のスケジュール実行制限、Supabase 側の判定変更などがあります。実際のアプリケーションからの通常のDBアクセスを第一にし、この機能は補助的なヘルスチェックとして扱ってください。重要なデータは別途バックアップしてください。

## 1. Supabase migration

Supabase SQL Editor で次の migration を適用するか、Supabase CLI の migration 運用に組み込んでください。

`supabase/migrations/20261110000000_create_ops_heartbeat.sql`

この migration は `public.ops_heartbeat` テーブルを作成し、RLSを有効にして、`anon` と `authenticated` の権限を取り消します。GitHub Actions のサーバー側処理だけが `service_role` 権限でアクセスします。

## 2. GitHub Actions Secrets

Repository の **Settings → Secrets and variables → Actions → Repository secrets** に以下を登録します。

| Secret | 値 |
| --- | --- |
| `SUPABASE_URL` | Supabase Project URL（例: `https://your-project.supabase.co`） |
| `SUPABASE_SERVICE_ROLE_KEY` | 対象プロジェクトの service_role key |

service_role key はRLSを迂回できる強い権限を持ちます。公開・ログ出力・クライアント側への埋め込みは禁止です。GitHub Actions の Secret にだけ保存し、fork からの pull request では使用しません。キーを漏えいした場合は Supabase 側でローテーションしてください。

## 3. 実行スケジュール

GitHub Actions の cron は UTC です。

| UTC cron | JST | 用途 |
| --- | --- | --- |
| `0 21 * * *` | 毎日 06:00 | 月曜は週次ラベル付き |
| `0 5 * * *` | 毎日 14:00 | 定期アクティビティ |
| `0 13 * * *` | 毎日 22:00 | 定期アクティビティ |

Workflow は `workflow_dispatch` にも対応しているため、Actions タブから手動実行できます。GitHub のスケジュール実行は混雑時に遅延する場合があります。

## 4. チェック内容

1. HTTPS の Supabase Project URL を検証します。
2. Data API に heartbeat 行を upsert します。
3. 同じ行を読み戻し、workflow run ID が一致することを確認します。
4. 429 / 5xx / 一時的なネットワークエラーは最大3回まで待機時間を延ばして再試行します。
5. GitHub Actions の Step Summary に成功・失敗・未設定を記録します。

同じ primary key `github-actions` を upsert するため、再実行してもheartbeat行が増え続けません。HTTP応答本文や秘密情報はログに出力しません。

## 5. 動作確認

ローカルでテストを実行します。

```bash
python -m pytest -q tests/test_supabase_keepalive.py
```

Secrets を登録した後、GitHub の **Actions → Supabase database keepalive → Run workflow** から手動実行し、Step Summary に書き込みと読み戻しの成功が表示されることを確認してください。Secrets が未設定の場合は、Workflow は安全に skip し、設定が必要である旨を表示します。

## 6. 運用上の注意

- Supabase の pause 条件を完全に回避する保証はありません。公式の案内とプロジェクトの Activity を定期的に確認してください。
- Free プランでは自動バックアップが提供されないため、重要データは定期的に外部へエクスポートしてください。
- heartbeatテーブルはアプリケーションのユーザーデータや監査ログの代替ではありません。
- DBのパスワードや service_role key をソースコード、Issue、PR、Actionsログに記載しないでください。
