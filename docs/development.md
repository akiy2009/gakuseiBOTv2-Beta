# 開発と品質確認

## 開発環境

このプロジェクトの開発・テスト・実行環境は **Python 3.12.x** に統一しています。異なる Python バージョンで作成した仮想環境を流用せず、Python 3.12 で新しく作成してください。

Windows PowerShell:

```powershell
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
```

macOS / Linux:

```bash
python3.12 --version
python3.12 -m venv .venv
source .venv/bin/activate
python --version
```

`Python 3.12.x` と表示されることを確認してから、リポジトリのルートで品質チェックを実行します。

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pytest
python -m pip check
python -m compileall -q main.py cogs
python -m pytest -q
```

CI と同様に依存関係、Python 構文、Cog の読み込み、設定ファイル、権限チェックをテストします。単体テストは Discord Gateway に接続せず、HSS テストも実 API には接続しません。

## 任意の HSS 連携を検証する

```bash
python -m pip install -r requirements-hss.txt
```

HSS API の実通信を行う場合は、管理者が発行した token と検証用学校 ID を安全な環境変数として用意してください。通常の CI は実 token を必要としません。実 API の可用性・権限・返却データの整合性は、モックを使った単体テストだけでは保証できません。

## ドキュメントをローカルでビルド

```bash
python -m pip install -r requirements-docs.txt
python scripts/generate_docs.py
sphinx-build -W --keep-going -b html docs build/manual-docs
pdoc --output-dir build/api-docs cogs
```

- `docs/`: 運用・開発者向けの Markdown ドキュメント。
- `build/manual-docs/`: Sphinx が生成する HTML マニュアル。
- `build/api-docs/`: pdoc が生成する Cog の API リファレンス。
- `docs/generated/`: Cog のコマンド定義と `.env.example` / Python ソースから抽出した自動生成リファレンス。

`docs/generated/` はビルド時に毎回再生成されます。コマンド名・説明は Cog のデコレーターや docstring を、環境変数は `.env.example` と `os.getenv` / `os.environ` の参照を情報源とします。秘密情報の実値は出力しません。生成済み HTML は CI の Artifact として確認します。

## CI / PR status

GitHub Actions は Python 3.12 で依存関係、構文、pytest を確認します。ドキュメント workflow も Python 3.12 を使用し、Sphinx の警告をエラー扱いして HTML を生成し、pdoc の API ドキュメントも生成します。PR の status comment は識別マーカーを使って既存コメントを更新するため、チェックの再実行ごとにコメントが増え続けることを避けます。

## 変更を提出する前に

1. Python 3.12 の仮想環境が有効になっていることを確認します。
2. `python -m pip check` が成功することを確認します。
3. `python -m compileall -q main.py cogs` を実行します。
4. `python -m pytest -q` を実行します。
5. 変更した機能・設定・テスト結果を Pull Request に記載します。
