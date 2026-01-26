# Platform - Sphinx Documentation Configuration

import os
import sys

# Add packages to path for autodoc
sys.path.insert(0, os.path.abspath('../../packages/creative-services'))

# Project information
project = 'Platform'
copyright = '2026, Platform Team'
author = 'Platform Team'
release = '1.0.0'

# Extensions
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
]

# Optional extensions
try:
    import sphinx_autodoc_typehints
    extensions.append('sphinx_autodoc_typehints')
except ImportError:
    pass

try:
    import myst_parser
    extensions.append('myst_parser')
except ImportError:
    pass

# Templates
templates_path = ['_templates']
exclude_patterns = []

# HTML output
try:
    import furo
    html_theme = 'furo'
except ImportError:
    html_theme = 'alabaster'
html_static_path = ['_static']
html_title = 'Platform Documentation'

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
}

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True

# Intersphinx
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}

# MyST (Markdown support)
myst_enable_extensions = [
    'colon_fence',
    'deflist',
]
