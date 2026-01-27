# Configuration file for the Sphinx documentation builder.
# ==========================================================
#
# Optimized for Django/Python projects with:
# - AutoAPI (no django.setup() needed)
# - MyST for Markdown
# - Furo theme
# - OpenGraph for social previews
# - Nitpicky mode for CI

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# -- Path setup --------------------------------------------------------------

# Project root (docs-infrastructure is in platform/)
DOCS_ROOT = Path(__file__).parent.parent.absolute()
PROJECT_ROOT = DOCS_ROOT.parent.parent  # platform/
PACKAGES_ROOT = PROJECT_ROOT / "packages"

# Add paths for autodoc (if needed)
sys.path.insert(0, str(PROJECT_ROOT))
if (PACKAGES_ROOT / "creative-services").exists():
    sys.path.insert(0, str(PACKAGES_ROOT / "creative-services"))

# -- Project information -----------------------------------------------------

project = os.environ.get("DOCS_PROJECT_NAME", "BF Agent Platform")
author = os.environ.get("DOCS_AUTHOR", "BF Agent Team")
copyright = f"{datetime.now(timezone.utc).year}, {author}"

# Version from environment (set by CI) or default
release = os.environ.get("DOCS_RELEASE", os.environ.get("GITHUB_REF_NAME", "dev"))
version = release.split("-")[0] if "-" in release else release

# -- General configuration ---------------------------------------------------

extensions = [
    # Core Sphinx
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx.ext.autosectionlabel",
    
    # Markdown support
    "myst_parser",
    
    # Auto-generate API from source (no imports needed!)
    "autoapi.extension",
    
    # Type hints in docs
    "sphinx_autodoc_typehints",
    
    # Social previews
    "sphinxext.opengraph",
    
    # Copy button for code blocks
    "sphinx_copybutton",
    
    # Cards, grids, tabs
    "sphinx_design",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "**/.ipynb_checkpoints"]

# Language
language = "de"

# Source file suffixes
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# -- MyST Configuration ------------------------------------------------------

myst_enable_extensions = [
    "deflist",           # Definition lists
    "fieldlist",         # Field lists
    "colon_fence",       # ::: fences
    "substitution",      # {{ }} substitutions
    "tasklist",          # - [ ] checkboxes
    "attrs_inline",      # {#id .class}
]
myst_heading_anchors = 3
myst_fence_as_directive = ["mermaid"]

# -- Theme Configuration -----------------------------------------------------

html_theme = "furo"
html_static_path = ["_static"]
html_title = f"{project} Documentation"
html_favicon = "_static/favicon.ico"
html_logo = "_static/logo.png"

html_theme_options: dict[str, Any] = {
    "light_css_variables": {
        "color-brand-primary": "#2563eb",
        "color-brand-content": "#2563eb",
    },
    "dark_css_variables": {
        "color-brand-primary": "#60a5fa",
        "color-brand-content": "#60a5fa",
    },
    "sidebar_hide_name": False,
    "navigation_with_keys": True,
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/achimdehnert/platform",
            "html": """
                <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 16 16">
                    <path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path>
                </svg>
            """,
            "class": "",
        },
    ],
}

# -- Napoleon (Docstring styles) ---------------------------------------------

napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = True
napoleon_attr_annotations = True

# -- Intersphinx -------------------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "django": (
        "https://docs.djangoproject.com/en/5.0/",
        "https://docs.djangoproject.com/en/5.0/_objects/",
    ),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
    "httpx": ("https://www.python-httpx.org/", None),
}

# -- AutoAPI Configuration ---------------------------------------------------
#
# IMPORTANT: AutoAPI parses source files WITHOUT importing them.
# This avoids django.setup() and keeps builds reproducible.

autoapi_type = "python"
autoapi_dirs = []

# Add package directories that exist
_potential_dirs = [
    PACKAGES_ROOT / "creative-services" / "creative_services",
]
for _dir in _potential_dirs:
    if _dir.exists():
        autoapi_dirs.append(str(_dir))

autoapi_root = "api"
autoapi_keep_files = False
autoapi_add_toctree_entry = True
autoapi_python_use_implicit_namespaces = True

autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
    "imported-members",
]

# Exclude noisy paths
autoapi_ignore = [
    "**/migrations/*",
    "**/tests/*",
    "**/*_test.py",
    "**/conftest.py",
    "**/settings/*",
    "**/wsgi.py",
    "**/asgi.py",
    "**/__pycache__/*",
]

# -- Autodoc Safety (for any remaining autodoc usage) ------------------------

# Mock Django and other imports that would fail without setup
autodoc_mock_imports = [
    "django",
    "rest_framework",
    "celery",
    "redis",
    "psycopg2",
    "gunicorn",
]

autodoc_typehints = "description"
autodoc_member_order = "bysource"
autodoc_class_signature = "separated"

# -- Nitpicky Mode -----------------------------------------------------------
#
# Treat missing references as errors. Combined with -W in CI.

nitpicky = True

# Ignore common dynamic types
nitpick_ignore = [
    ("py:class", "QuerySet"),
    ("py:class", "Manager"),
    ("py:class", "HttpRequest"),
    ("py:class", "HttpResponse"),
    ("py:class", "Model"),
    ("py:class", "Field"),
    ("py:class", "BaseModel"),
    ("py:class", "ConfigDict"),
    ("py:class", "Self"),
    ("py:class", "T"),
    ("py:class", "Callable"),
    ("py:class", "Awaitable"),
    ("py:class", "Coroutine"),
    ("py:obj", "creative_services.prompts.schemas.variables.T"),
]

nitpick_ignore_regex = [
    (r"py:.*", r".*\.T"),  # Generic type vars
    (r"py:.*", r".*\._.*"),  # Private members
]

# -- Autosectionlabel --------------------------------------------------------

autosectionlabel_prefix_document = True
autosectionlabel_maxdepth = 2

# -- OpenGraph ---------------------------------------------------------------

ogp_site_url = os.environ.get("DOCS_SITE_URL", "https://docs.iil.pet/")
ogp_site_name = project
ogp_use_first_image = True
ogp_image = os.environ.get(
    "DOCS_OG_IMAGE", 
    "https://docs.iil.pet/_static/og-image.png"
)
ogp_description_length = 200
ogp_type = "website"

# -- Copy Button -------------------------------------------------------------

copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True
copybutton_only_copy_prompt_lines = True
copybutton_remove_prompts = True

# -- Build Hygiene -----------------------------------------------------------

# Keep warnings visible; CI uses -W
suppress_warnings = []

# Default role for inline refs
default_role = "any"

# -- Custom Setup ------------------------------------------------------------

def setup(app):
    """Custom Sphinx setup."""
    # Add custom CSS
    app.add_css_file("custom.css")
