"""
Deployment MCP Server
=====================

Infrastructure Management via Model Context Protocol.

Features:
- Hetzner Cloud Server Management (create, delete, power actions)
- Firewall Management (create, rules, apply to servers)
- SSH Key Management
- Docker Container Management
- Docker Compose Operations
- PostgreSQL Database Management
- Environment Variables & Secrets Management
"""

__version__ = "0.4.0"

from .server import main, run_server
from .settings import Settings, settings

__all__ = [
    "__version__",
    "main",
    "run_server",
    "Settings",
    "settings",
]
