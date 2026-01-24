"""
Illustration MCP Server
=======================

MCP Server for AI-powered book illustration generation using ComfyUI.

Features:
- Chapter illustration generation
- Character portrait generation
- Batch generation for entire books
- Style management and presets
- ComfyUI status monitoring
"""

__version__ = "1.0.0"

from .server import main, run_server

__all__ = [
    "__version__",
    "main",
    "run_server",
]
