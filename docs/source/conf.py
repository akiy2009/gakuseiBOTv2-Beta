import os
import sys
sys.path.insert(0, os.path.abspath('../../'))  # リポジトリルートをパスに追加

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',  # Googleスタイル・NumPyスタイルのdocstring対応
]

# ここに依存しているけどimportできないモジュール名をリストアップする
autodoc_mock_imports = ["discord", "some_other_module", "numpy"]

# テーマ（ReadTheDocsテーマ推奨）
html_theme = 'sphinx_rtd_theme'
