import os
import sys
sys.path.insert(0, os.path.abspath('../..'))  # リポジトリルートをパスに追加

# Sphinx拡張
extensions = [
    "myst_parser",            # Markdownサポート
    "sphinx.ext.autodoc",     # 自動ドキュメント生成
    "sphinx.ext.napoleon",    # Google / NumPy docstring
]

# importできない外部依存モジュールをモック
autodoc_mock_imports = ["discord", "numpy", "some_other_module"]

# Markdown設定
myst_enable_extensions = [
    "linkify",
    "colon_fence",
]

# HTML出力テーマ
html_theme = "sphinx_rtd_theme"

# 出力ディレクトリ設定
source_suffix = [".rst", ".md"]
master_doc = "index"