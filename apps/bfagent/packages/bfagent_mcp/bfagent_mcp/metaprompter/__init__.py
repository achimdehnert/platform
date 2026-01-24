"""
MetaPrompter Gateway
====================

Universal Natural Language Interface für BF Agent MCP Server.
Verarbeitet JEDE Eingabe und routet zum richtigen Tool.
"""

from .gateway import UniversalGateway
from .intent import IntentClassifier, Intent
from .enricher import ContextEnricher

__all__ = ["UniversalGateway", "IntentClassifier", "Intent", "ContextEnricher"]
