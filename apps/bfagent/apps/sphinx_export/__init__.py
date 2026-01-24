"""
Sphinx Markdown Export
======================

Konvertiert Sphinx-Dokumentationsprojekte in einzelne Markdown-Dateien.

Features:
- Nutzt sphinx-markdown-builder wenn verfügbar
- Fallback auf direkte RST→MD Konvertierung
- Django-Admin Integration mit Export-Actions
- Management Command für CLI-Nutzung
- MCP Tool für AI-Agenten
- Unterstützt alle wichtigen Sphinx-Extensions

Installation:
    pip install sphinx sphinx-markdown-builder

    # In Django settings.py
    INSTALLED_APPS = [
        ...
        'apps.sphinx_export',
    ]

Usage (Python):
    from apps.sphinx_export import sphinx_to_markdown
    
    success, path, metadata = sphinx_to_markdown(
        '/path/to/docs',
        title="My Documentation"
    )

Usage (CLI):
    python manage.py sphinx_to_markdown --source docs/ -o complete.md

Usage (MCP):
    Tool: sphinx_export_to_markdown
    Parameters: source_path, output_path, title, include_toc

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

from .services import (
    SphinxExportService,
    TableConverter,
    ExportResult,
    get_sphinx_export_service,
)

from .sync_service import (
    SphinxSyncService,
    SyncReport,
    get_sphinx_sync_service,
)

__version__ = '1.0.0'
__author__ = 'BF Agent Framework'

__all__ = [
    # High-Level Export Service (empfohlen)
    'SphinxExportService',
    'TableConverter',
    'ExportResult',
    'get_sphinx_export_service',
    
    # Sync Service
    'SphinxSyncService',
    'SyncReport',
    'get_sphinx_sync_service',
    
    # Low-Level Service
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
default_app_config = 'apps.sphinx_export.apps.SphinxExportConfig'
