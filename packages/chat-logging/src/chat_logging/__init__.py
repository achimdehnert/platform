"""chat-logging — Persistent chat conversation logging & QM.

Platform package per ADR-037. Provides:
- ChatConversation / ChatMessage: Django models for conversation storage
- UseCaseCandidate: Auto-detected unmet user needs
- EvaluationScore: DeepEval/LangFuse evaluation results
- LoggingSessionBackend: Transparent wrapper for any SessionBackend
"""

__version__ = "0.1.0"

from .backends import LoggingSessionBackend

__all__ = [
    "__version__",
    "LoggingSessionBackend",
]
