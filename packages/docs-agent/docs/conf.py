"""Sphinx configuration for docs-agent documentation."""

import sys
from pathlib import Path

# Add source to path for autodoc
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

project = "Docs Agent"
copyright = "2026, Achim Dehnert"
author = "Achim Dehnert"
release = "0.2.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosummary",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_static_path = ["_static"]
html_title = "Docs Agent"

autodoc_member_order = "bysource"
autodoc_typehints = "description"
napoleon_google_docstring = True
napoleon_numpy_docstring = False

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

autosummary_generate = True
