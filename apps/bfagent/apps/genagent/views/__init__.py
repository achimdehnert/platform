"""
GenAgent Views

- domain_views: Domain Template Management
- action_views: Action CRUD & Execution
- handler_views: Handler Discovery & Testing
- registry_views: Handler Registry System (Phase 1)
"""

from . import domain_views, action_views, handler_views, registry_views

__all__ = [
    'domain_views',
    'action_views',
    'handler_views',
    'registry_views'
]
