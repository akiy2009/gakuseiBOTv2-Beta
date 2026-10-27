# 開発と品質確認

## 開発環境の検証

仮想環境を有効にし、リポジトリのルートで実行します。

```bash
python -m pip install -r requirements.txt
python -m pip check
python -m compileall -q main.py cogs
python -m pip install pytest
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
sphinx-build -W --keep-going -b html docs build/manual-docs
pdoc --output-dir build/api-docs cogs
```

- `docs/`: 運用・開発者向けの Markdown ドキュメント。
- `build/manual-docs/`: Sphinx が生成する HTML マニュアル。
- `build/api-docs/`: pdoc が生成する Cog の API リファレンス。

生成物は Git にコミットせず、CI の Artifact として確認します。

## CI / PR status

GitHub Actions は Python 3.10 / 3.11 / 3.12 で依存関係、構文、pytest を確認します。ドキュメント workflow は Sphinx の警告をエラー扱いして HTML を生成し、pdoc の API ドキュメントも生成します。PR の status comment は識別マーカーを使って既存コメントを更新するため、チェックの再実行ごとにコメントが増え続けることを避けます。
