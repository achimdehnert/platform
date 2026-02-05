# Configuration file for the Sphinx documentation builder.
# DDL Governance Documentation

project = 'DDL Governance'
copyright = '2026, Platform Team'
author = 'Platform Team'
release = '1.0.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'myst_parser',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# MyST Parser settings
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "tasklist",
]

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
