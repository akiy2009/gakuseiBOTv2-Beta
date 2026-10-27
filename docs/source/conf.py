import os
import sys

sys.path.insert(0, os.path.abspath("../.."))

extensions = [
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
html_theme = "sphinx_rtd_theme"
master_doc = "index"
