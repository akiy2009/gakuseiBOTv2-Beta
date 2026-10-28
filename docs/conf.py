from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

project = "gakuseiBOT v2"
copyright = "gakuseiBOT contributors"
author = "gakuseiBOT contributors"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]

myst_enable_extensions = ["colon_fence"]
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
root_doc = "index"
master_doc = "index"
html_theme = "sphinx_rtd_theme"
exclude_patterns = ["_build", "build", "source"]
autodoc_mock_imports = [
    "discord",
    "aiohttp",
    "watchdog",
    "dotenv",
    "wikipedia",
    "pytz",
    "psutil",
    "requests",
]
