ここには学習用プログラムに関するDBの処理を記載します。

## 必要なimport（Python）

```python
from typing import Dict, List, Union, Optional
```

## データ構造とパラメータ一覧

### 1. Userdata（ユーザーデータ）

| パラメータ名 | データ型 | 説明 |
|-------------|----------|------|
| `{user_id}` | str | DiscordユーザーID（数値文字列） |
| `question_user_data` | Dict[str, Dict] | ユーザーの問題別学習データ |
| `question_genre` | Dict[str, Dict] | ユーザーが作成したジャンルデータ |

#### question_user_data（問題別ユーザーデータ）

| パラメータ名 | データ型 | 説明 |
|-------------|----------|------|
| `{question_id}` | str | 問題セットのID（数値文字列） |
| `miss_numbers` | List[int] | 間違えた問題の番号リスト |
| `try_number` | int | 挑戦回数 |
| `score` | int | 最高スコア |

#### question_genre（ジャンルデータ）

| パラメータ名 | データ型 | 説明 |
|-------------|----------|------|
| `{genre_id}` | str | ジャンルのID（数値文字列） |
| `title` | str | ジャンルのタイトル/名前 |
| `sharecodes` | List[int] | ジャンルに含まれる問題セットのIDリスト |

### 2. memorization（暗記問題セット）

| パラメータ名 | データ型 | 説明 |
|-------------|----------|------|
| `{memorization_id}` | str | 問題セットのID（数値文字列） |
| `title` | str | 問題セットのタイトル |
| `questions` | List[Dict] | 問題データの配列 |
| `onwer` | List[str] | 問題セットの所有者ユーザーIDリスト |

#### questions（問題データ）

| パラメータ名 | データ型 | 説明 |
|-------------|----------|------|
| `question` | str | 問題文 |
| `answer` | Union[str, int, List[str]] | 問題の答え（モードによって型が変わる） |
| `mode` | int | 問題モード（0: 通常, 1: 選択, 2: 穴埋め） |
| `select` | Optional[List[str]] | 選択肢（mode=1の場合のみ） |

## 各パラメータの詳細説明

### ユーザーデータ関連

- **user_id**: DiscordのユーザーIDで、学習データを個人別に管理するためのキー
- **miss_numbers**: 間違えた問題の番号を記録し、復習機能で活用
- **try_number**: 同じ問題セットに何回挑戦したかを追跡
- **score**: そのユーザーの最高スコアを保存

### 問題セット関連

- **memorization_id**: 各問題セットを一意に識別するID
- **title**: 問題セットの名前（例: "英単語テスト", "数学公式"）
- **onwer**: 問題セットを作成・管理できるユーザー（複数人可能）

### 問題データ関連

- **question**: 実際の問題文
- **answer**: 
  - mode 0（通常）: 文字列型の答え
  - mode 1（選択）: 正解選択肢の番号（0から始まる）
  - mode 2（穴埋め）: 複数の答えを配列で格納
- **mode**: 問題の種類を決定する重要なパラメータ
  - 0: 自由記述式
  - 1: 選択問題式
  - 2: 穴埋め問題式
- **select**: 選択問題の場合の選択肢リスト

### ジャンル機能

- **genre_id**: ジャンルを識別するためのID
- **sharecodes**: そのジャンルに属する問題セットのIDを管理
- ユーザーが関連する問題をまとめて管理できる機能

```json
    "Userdata": {
        "705264675138568192": {
            "question_user_data":{
                "888850": {
                    "miss_numbers": [0,1,2],
                    "try_number": 1,
                    "score": 1
                },
            },
            "question_genre":{
                "9916": {
                    "title": "ジャンル名",
                    "sharecodes": [
                        603920,
                        938199,
                        985040,
                        563681,
                        439447,
                        881218
                    ],
                },
            }
        }
    },
    "memorization": {
        "888850": {
            "title": "test_888850",
            "questions": [
                {
                    "question": "通常モード",
                    "answer": "答え",
                    "mode": 0
                },
                {
                    "question": "選択問題用",
                    "answer": 0,
                    "mode": 1,
                    "select": [
                        "1",
                        "2",
                        "3",
                        "4"
                    ]
                },
                {
                    "question": "穴埋め問題 (①)を答える (②)となる",
                    "answer": ["答え","こうなる"],
                    "mode": 2,
                }
            ],
            "onwer": [
                "705264675138568192"
            ]
    }
    }
```
