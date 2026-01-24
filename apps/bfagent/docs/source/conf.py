"""
Sphinx Configuration for BF Agent Documentation
================================================

Single Source of Truth (SSOT) Dokumentation.
Generiert automatisch API-Docs aus Docstrings.

Author: Achim Grosskopf
Generated: 2025-01-14
"""

import os
import sys
from datetime import datetime

# ==============================================================================
# PATH SETUP - Django Project
# ==============================================================================

# Add project root to path for autodoc
# docs_v2/doku-system/docs/source/ -> need to go up 4 levels to project root
PROJECT_ROOT = os.path.abspath('../../../..')
sys.path.insert(0, PROJECT_ROOT)

# Django Setup (CRITICAL for model documentation)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Try to setup Django (graceful fallback if not available)
DJANGO_AVAILABLE = False
try:
    import django
    django.setup()
    DJANGO_AVAILABLE = True
    print(f"✓ Django initialized successfully from: {PROJECT_ROOT}")
except Exception as e:
    print(f"Note: Django not available - building without model docs: {e}")
    DJANGO_AVAILABLE = False

# ==============================================================================
# PROJECT INFORMATION
# ==============================================================================

project = 'BF Agent'
copyright = f'{datetime.now().year}, Achim Grosskopf'
author = 'Achim Grosskopf'

# Version info
version = '2.0'  # Short X.Y version
release = '2.0.0'  # Full version

# ==============================================================================
# GENERAL CONFIGURATION
# ==============================================================================

# Extensions
extensions = [
    # Core Sphinx
    'sphinx.ext.autodoc',           # Auto-generate from docstrings
    'sphinx.ext.autosummary',       # Generate summary tables
    'sphinx.ext.napoleon',          # Google/NumPy docstrings
    'sphinx.ext.viewcode',          # Add source code links
    'sphinx.ext.intersphinx',       # Cross-project references
    'sphinx.ext.todo',              # TODO directives
    'sphinx.ext.coverage',          # Documentation coverage
    'sphinx.ext.graphviz',          # Diagrams
    'sphinx.ext.inheritance_diagram',  # Class inheritance
    
    # Markdown Support
    'myst_parser',                  # Markdown files (.md)
    
    # Django-specific (uncomment when project is available)
    # 'sphinxcontrib_django',         # Django model docs
    
    # UX Enhancements
    'sphinx_copybutton',            # Copy button for code blocks
    'sphinx_design',                # Cards, tabs, grids
    
    # Diagrams
    'sphinxcontrib.mermaid',        # Mermaid diagrams
]

# Source file suffixes
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# Master document
master_doc = 'index'

# Exclude patterns
exclude_patterns = [
    '_build',
    'Thumbs.db',
    '.DS_Store',
    '**/.git',
    '**/migrations/*',
    '**/tests/*',
]

# Language
language = 'de'

# ==============================================================================
# AUTODOC CONFIGURATION
# ==============================================================================

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__',
    'show-inheritance': True,
    'inherited-members': False,
}

# Type hints
autodoc_typehints = 'description'
autodoc_typehints_description_target = 'documented'

# Mock imports for external dependencies that might not be installed
autodoc_mock_imports = [
    'ezdxf',
    'pdf2image',
    'pytesseract',
    'cv2',
    'numpy',
    'PIL',
    'celery',
    'redis',
    'openai',
    'anthropic',
]

# ==============================================================================
# AUTOSUMMARY CONFIGURATION
# ==============================================================================

autosummary_generate = True
autosummary_generate_overwrite = True
autosummary_imported_members = False

# ==============================================================================
# NAPOLEON CONFIGURATION (Google-Style Docstrings)
# ==============================================================================

napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_use_keyword = True
napoleon_preprocess_types = True
napoleon_type_aliases = None
napoleon_attr_annotations = True

# ==============================================================================
# DJANGO EXTENSION CONFIGURATION
# ==============================================================================

# Django settings module
django_settings = 'config.settings'

# Show model fields
django_show_db_tables = True

# ==============================================================================
# INTERSPHINX CONFIGURATION
# ==============================================================================

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'django': ('https://docs.djangoproject.com/en/5.0/', 
               'https://docs.djangoproject.com/en/5.0/_objects/'),
    'celery': ('https://docs.celeryq.dev/en/stable/', None),
    'pydantic': ('https://docs.pydantic.dev/latest/', None),
}

# ==============================================================================
# MYST (MARKDOWN) CONFIGURATION
# ==============================================================================

myst_enable_extensions = [
    'amsmath',           # Math support
    'colon_fence',       # ::: directives
    'deflist',           # Definition lists
    'dollarmath',        # $math$
    'fieldlist',         # Field lists
    'html_admonition',   # HTML admonitions
    'html_image',        # HTML images
    'linkify',           # Auto-link URLs
    'replacements',      # Text replacements
    'smartquotes',       # Smart quotes
    'substitution',      # Substitutions
    'tasklist',          # Task lists
]

myst_heading_anchors = 3

# ==============================================================================
# TODO EXTENSION
# ==============================================================================

todo_include_todos = True
todo_emit_warnings = False

# ==============================================================================
# HTML OUTPUT CONFIGURATION
# ==============================================================================

# Theme
html_theme = 'furo'  # Modern, clean theme

# BF Agent Brand Colors
# Primary: Deep Blue (#1e40af) - Trust, Technology
# Accent: Amber (#f59e0b) - Energy, Innovation
# Success: Emerald (#10b981) - Growth, Completion

# Theme options
html_theme_options = {
    # Force light mode
    "light_logo": "logo.svg",
    "dark_logo": "logo.svg",
    
    "light_css_variables": {
        # BF Agent Blue
        "color-brand-primary": "#1e40af",
        "color-brand-content": "#1e40af",
        # Sidebar
        "color-sidebar-background": "#f8fafc",
        "color-sidebar-brand-text": "#1e40af",
        "color-sidebar-link-text": "#374151",
        "color-sidebar-link-text--top-level": "#1e40af",
        # Content
        "color-background-primary": "#ffffff",
        "color-background-secondary": "#f1f5f9",
        # Accent
        "color-highlight-on-target": "#fef3c7",
        # Admonitions
        "color-admonition-title-background--note": "#dbeafe",
        "color-admonition-title--note": "#1e40af",
    },
    "dark_css_variables": {
        "color-brand-primary": "#60a5fa",
        "color-brand-content": "#60a5fa",
        "color-sidebar-brand-text": "#60a5fa",
    },
    "sidebar_hide_name": False,
    "navigation_with_keys": True,
    "top_of_page_buttons": ["view", "edit"],
    # Footer
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/achimdehnert/bfagent",
            "html": """<svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path></svg>""",
            "class": "",
        },
    ],
    "source_repository": "https://github.com/achimdehnert/bfagent",
    "source_branch": "main",
    "source_directory": "docs_v2/doku-system/docs/source/",
}

# Static files
html_static_path = ['_static']

# Custom CSS
html_css_files = [
    'css/custom.css',
]

# Logos and icons
html_logo = '_static/logo.svg'
# html_favicon = '_static/favicon.ico'

# Page title
html_title = f"{project} Documentation"

# Short title for navigation
html_short_title = project

# Last updated format
html_last_updated_fmt = '%d.%m.%Y'

# Show "Created using Sphinx"
html_show_sphinx = True

# Show copyright
html_show_copyright = True

# ==============================================================================
# LATEX OUTPUT CONFIGURATION (for PDF)
# ==============================================================================

latex_elements = {
    'papersize': 'a4paper',
    'pointsize': '11pt',
    'preamble': r'''
        \usepackage[utf8]{inputenc}
        \usepackage[T1]{fontenc}
        \usepackage[german]{babel}
    ''',
    'figure_align': 'htbp',
}

latex_documents = [
    (master_doc, 'bf_agent.tex', 'BF Agent Documentation',
     'Achim Grosskopf', 'manual'),
]

# ==============================================================================
# EPUB OUTPUT CONFIGURATION
# ==============================================================================

epub_title = project
epub_author = author
epub_publisher = author
epub_copyright = copyright

# ==============================================================================
# LINKCHECK CONFIGURATION
# ==============================================================================

linkcheck_ignore = [
    r'http://localhost.*',
    r'http://127\.0\.0\.1.*',
]

linkcheck_timeout = 10

# ==============================================================================
# GRAPHVIZ CONFIGURATION
# ==============================================================================

graphviz_output_format = 'svg'

# ==============================================================================
# CUSTOM SETUP
# ==============================================================================

def setup(app):
    """Custom Sphinx setup."""
    # Add custom CSS
    app.add_css_file('css/custom.css')
    
    # Custom roles or directives can be added here
    pass
