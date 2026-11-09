# Contributing Guide

gakuseiBOT v2 への貢献を歓迎します。バグ報告、機能改善、ドキュメント修正など、変更の規模にかかわらずご協力ください。

## 開発環境

このプロジェクトでは **Python 3.12.x** を使用します。`.python-version` を参照し、別バージョンの仮想環境を使い回さないでください。

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pytest
```

macOS / Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python --version
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pytest
```

## 開発の流れ

1. リポジトリを Fork します。
2. Fork したリポジトリを clone します。

   ```bash
   git clone https://github.com/<your-account>/gakuseiBOTv2-Beta.git
   cd gakuseiBOTv2-Beta
   ```

3. 変更内容が分かるブランチを作成します。

   ```bash
   git switch -c feature/short-description
   ```

4. 変更を実装し、必要に応じてテストを追加・更新します。
5. Pull Request を作成する前に、次のチェックを実行します。

   ```bash
   python --version
   python -m pip check
   python -m compileall -q main.py cogs
   python -m pytest -q
   ```

6. 変更を小さな単位で commit し、Fork へ push します。

   ```bash
   git add <changed-files>
   git commit -m "type: describe the change"
   git push -u origin feature/short-description
   ```

7. GitHub から `main` ブランチに向けて Pull Request を作成します。

## Pull Request の書き方

Pull Request には、次の内容を含めてください。

- **目的:** なぜ変更が必要なのか
- **変更内容:** どの機能・ファイルを変更したか
- **確認方法:** 実行したテストと結果
- **影響範囲:** 設定変更、依存関係変更、互換性への影響
- **関連 Issue:** 該当する場合はリンク

機能変更には可能な範囲でテストを追加してください。token、API key、個人情報などの秘密情報を commit・Issue・Pull Request・ログへ含めないでください。

## コミットメッセージ

変更の目的が分かる短いメッセージを推奨します。

- `feat: add a study command`
- `fix: handle missing configuration`
- `docs: clarify local setup`
- `test: cover timetable parsing`
- `chore: update dependencies`

## レビューとマージ

CI が成功していること、変更内容が説明されていること、必要なドキュメント・テストが更新されていることを確認してからレビュー・マージします。
