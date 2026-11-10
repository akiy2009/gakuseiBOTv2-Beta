# ヘルスチェックと管理者通知

## 機能

`cogs/normal/health.py` が一定間隔で次を確認します。

- Discord Gateway: Bot の ready 状態と Gateway latency
- SQLite: `USER_DATA_DB` の存在、`PRAGMA quick_check`、簡単な読み取り
- Supabase: 設定されている場合に `ops_heartbeat` テーブルへの読み取り接続

異常は既定で2回連続してから通知します。同一コンポーネントの通知は復旧まで抑制し、正常に戻った時点で復旧通知を送信します。未設定の Supabase は監視対象外です。

## 設定

`.env` に必要な値を追加します。

| 変数 | 既定値 | 説明 |
| --- | --- | --- |
| `HEALTH_ALERT_CHANNEL_ID` | 空欄 | 障害・復旧通知を送信する Discord テキストチャンネル ID |
| `HEALTH_ADMIN_USER_IDS` | 空欄 | DM通知先の管理者ユーザーID。複数指定はカンマ区切り |
| `HEALTH_CHECK_INTERVAL_SECONDS` | `60` | 監視間隔。30秒未満は既定値に戻す |
| `HEALTH_FAILURE_THRESHOLD` | `2` | 通知を出すまでの連続失敗回数 |
| `USER_DATA_DB` | `data/user_data.sqlite3` | SQLite DB のパス |
| `SUPABASE_URL` | 空欄 | Supabase Project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | 空欄 | サーバー専用の service role key |

`DEVELOPER_ID` は互換性のため管理者DMの宛先にも含めます。通知先はチャンネルか管理者IDの少なくとも一方を設定してください。DMを受け取る管理者はBotからのDMを許可する必要があります。

## 管理者コマンド

`/health` は `HEALTH_ADMIN_USER_IDS` または `DEVELOPER_ID` に登録されたユーザーのみ実行できます。結果は実行者にだけ表示されます。

## 通知例

- `🚨 SQLite health check failed`: 連続失敗がしきい値に達したとき
- `✅ SQLite recovered`: 正常状態へ復帰したとき

通知にはコンポーネント名、連続失敗回数、簡潔な理由のみを含めます。SQL本文、HTTPレスポンス本文、トークン、接続文字列は通知しません。

## 制約

この監視はBotプロセス内で動くため、プロセス自体が停止した場合やDiscord Gatewayが切断中の場合、その瞬間にDiscord通知を送ることはできません。プロセス停止も検知したい場合は、別ホストの外形監視やホスティング側のアラートを併用してください。

Supabase チェックは前段の `ops_heartbeat` migration が適用済みで、Secrets が設定されている場合のみ成功します。Free プランの自動一時停止を防ぐ保証ではありません。
