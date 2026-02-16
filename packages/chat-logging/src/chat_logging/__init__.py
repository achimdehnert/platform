"""chat-logging — Persistent chat conversation logging & QM.

Platform package per ADR-037. Provides:
- ChatConversation / ChatMessage: Django models for conversation storage
- UseCaseCandidate: Auto-detected unmet user needs (LLM-based)
- EvaluationScore: LLM-based quality evaluation results
- LoggingSessionBackend: Transparent wrapper for any SessionBackend
- evaluate_conversation / batch_evaluate: Quality scoring
"""

__version__ = "0.2.0"

from .backends import LoggingSessionBackend
from .evaluation import batch_evaluate, evaluate_conversation

__all__ = [
    "__version__",
    "LoggingSessionBackend",
    "batch_evaluate",
    "evaluate_conversation",
]
