"""iil-doc-templates — Reusable Django document template system.

Provides DocumentTemplate + DocumentInstance models, CRUD views,
interactive template editor, PDF extraction, and LLM prefill.

Uses iil-concept-templates for schemas and PDF structure extraction.
"""

__version__ = "0.3.0"

default_app_config = "doc_templates.apps.DocTemplatesConfig"
