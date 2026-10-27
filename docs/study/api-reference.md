# HSS API 使用箇所リファレンス

このページは HSS API 全体の仕様書ではなく、gakuseiBOT の HSS 連携が使用するクラス・プロパティ・操作をまとめたものです。API の完全な仕様は [HSS-Project の公式ドキュメント](https://hss-dev-docs.aknet.tech/) と [HSS.py README](https://github.com/HSS-Project/HSS.py/blob/main/README.md) を参照してください。

## この Bot で使用する要素

| API / 属性 | 用途 | 使用場所 |
| --- | --- | --- |
| `hss.Client()` | HSS API クライアントを作成 | `cogs/normal/timetable.py` |
| `await client.setup(token=...)` | token を使って接続し、アクセス可能な学校データを読み込む | 同上 |
| `client.get_school(school_id)` | 指定した学校を取得 | 同上 |
| `school.name` | Embed のタイトルに学校名を表示 | 同上 |
| `school.classes[grade][class]` | 指定学年・クラスのデータを選択 | 同上 |
| `classroom.timeline` | クラスの時間割を参照 | 同上 |
| `timeline.mon` など | 曜日別の `DayTimeline` を選択 | 同上 |
| `day_timeline.lessons` | 授業名、場所、行事情報の一覧 | 同上 |
| `await client.close()` | HTTP session を閉じる | 同上 |

## 日・時間割データ

HSS.py の `Timeline` には `sun`、`mon`、`tue`、`wed`、`thu`、`fri`、`sat` があり、Bot はこれを日曜日から土曜日の日本語ラベルに対応付けます。各日の `lessons` は授業データの並びです。空の要素は「登録なし」として表示します。

現在の Bot は時間割の読み取りのみを行います。HSS 側への変更を行う `Timeline.edit()`、イベント時間の変更、任意の低レベル HTTP リクエストは呼び出しません。

## エラーとリソース管理

- 初期化エラーは型名だけをログに記録し、token やリクエスト詳細をログ出力しないようにします。
- クライアントが作成されていれば Cog の終了時に `close()` を呼び、HTTP session を閉じます。
- 学校 ID、学年、クラス番号は正の整数である必要があります。対象データが API token から見えない場合は、管理者が権限と ID を確認します。
- HSS の API は外部サービスです。モックテストが成功しても、外部 API が利用可能であることや token の権限までは保証しません。
