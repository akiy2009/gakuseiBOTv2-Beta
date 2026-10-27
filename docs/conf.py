import os
import sys

sys.path.insert(0, os.path.abspath("../.."))

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]

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

myst_enable_extensions = ["linkify", "colon_fence"]
html_theme = "sphinx_rtd_theme"
source_suffix = [".rst", ".md"]
master_doc = "index"
