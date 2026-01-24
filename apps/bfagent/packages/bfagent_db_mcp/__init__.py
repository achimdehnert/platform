"""
BF Agent Database MCP Server
============================

Extended PostgreSQL functionality for Django integration.

Features:
- Schema inspection (tables, columns, indexes)
- Django model introspection
- Migration status
- Query analysis (EXPLAIN)
- Safe parameterized queries
"""

__version__ = "1.0.0"

from .server import main, run_server

__all__ = [
    "__version__",
    "main",
    "run_server",
]
