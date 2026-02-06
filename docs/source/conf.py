"""
BF Agent Platform — Sphinx Configuration
=========================================

Central documentation for the entire BF Agent ecosystem.
Three pillars: Codebase (autodoc), Database (DB-driven), Governance (ADR).

See ADR-020 for the full documentation strategy.
"""

import sys
from pathlib import Path

# -- Path setup ---------------------------------------------------------------
# Add project root so autodoc can find Django apps
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# -- Project information ------------------------------------------------------

project = "BF Agent Platform"
copyright = "2026, Achim Dehnert"
author = "Achim Dehnert"
release = "1.0.0"
language = "de"

# -- General configuration ----------------------------------------------------

extensions = [
    # Säule 1: Codebase
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    # Säule 2: Database (PlantUML for ERD)
    # "sphinxcontrib.plantuml",   # enable after: pip install sphinxcontrib-plantuml
    # "sphinx_tabs.tabs",  # optional: pip install sphinx-tabs
    # Säule 3: ADR / Governance
    "myst_parser",
    "sphinx.ext.todo",
    "sphinx_design",
    # Export
    # "sphinx_markdown_builder",  # enable after: pip install sphinx-markdown-builder
]

# MyST: Allow Markdown files alongside RST
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "tasklist",
    "fieldlist",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output --------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "navigation_depth": 4,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "logo_only": False,
    "style_nav_header_background": "#2b3e50",
}
html_static_path = ["_static"]
html_title = "BF Agent Platform Docs"

# -- Intersphinx: Cross-project links ----------------------------------------

intersphinx_mapping = {
    "django": ("https://docs.djangoproject.com/en/5.0/", None),
    "python": ("https://docs.python.org/3/", None),
}

# -- Napoleon: Google-style docstrings ----------------------------------------

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_use_param = True
napoleon_use_rtype = True

# -- Autodoc ------------------------------------------------------------------

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}
autodoc_member_order = "bysource"

# -- TODO extension -----------------------------------------------------------

todo_include_todos = True
