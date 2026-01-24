"""
Sphinx Markdown Export
======================

Konvertiert Sphinx-Dokumentationsprojekte in einzelne Markdown-Dateien.

Features:
- Nutzt sphinx-markdown-builder wenn verfügbar
- Fallback auf direkte RST→MD Konvertierung
- Django-Admin Integration mit Export-Actions
- Management Command für CLI-Nutzung
- Unterstützt alle wichtigen Sphinx-Extensions

Installation:
    pip install sphinx sphinx-markdown-builder

    # In Django settings.py
    INSTALLED_APPS = [
        ...
        'sphinx_markdown_export',
    ]

Usage (Python):
    from sphinx_markdown_export import sphinx_to_markdown
    
    success, path, metadata = sphinx_to_markdown(
        '/path/to/docs',
        title="My Documentation"
    )

Usage (CLI):
    python manage.py sphinx_to_markdown myproject -o docs/complete.md

Author: BF Agent Framework
License: MIT
Version: 1.0.0
"""

from .export_service import (
    SphinxToMarkdownService,
    ExportConfig,
    ExportMetadata,
    sphinx_to_markdown,
)

from .sphinx_converter import (
    SphinxFeatureConverter,
    AutodocConverter,
    ConversionContext,
)

__version__ = '1.0.0'
__author__ = 'BF Agent Framework'

__all__ = [
    # Main Service
    'SphinxToMarkdownService',
    'ExportConfig',
    'ExportMetadata',
    'sphinx_to_markdown',
    
    # Converters
    'SphinxFeatureConverter',
    'AutodocConverter',
    'ConversionContext',
]

# Django app config
default_app_config = 'sphinx_markdown_export.apps.SphinxMarkdownExportConfig'
