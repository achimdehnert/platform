# Travel Beat - Sphinx Documentation Configuration

import os
import sys
import django

# Add project to path
sys.path.insert(0, os.path.abspath('../..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

# Project information
project = 'Travel Beat'
copyright = '2026, Travel Beat Team'
author = 'Travel Beat Team'
release = '1.0.0'

# Extensions
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx_autodoc_typehints',
    'myst_parser',
]

# Templates
templates_path = ['_templates']
exclude_patterns = []

# HTML output
html_theme = 'furo'
html_static_path = ['_static']
html_title = 'Travel Beat Documentation'

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
}

# Napoleon settings (Google/NumPy docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True

# Intersphinx
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'django': ('https://docs.djangoproject.com/en/5.0/', 'https://docs.djangoproject.com/en/5.0/_objects/'),
}

# MyST (Markdown support)
myst_enable_extensions = [
    'colon_fence',
    'deflist',
]
