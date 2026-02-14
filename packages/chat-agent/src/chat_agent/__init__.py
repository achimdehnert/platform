"""chat-agent — Domain-agnostic Chat Agent with Tool-Use loop.

Platform package per ADR-034 §3. Provides:
- ChatAgent: Core Tool-Use loop (LLM → tool calls → execute → LLM)
- DomainToolkit: ABC for app-specific tool collections
- SessionBackend: Protocol for pluggable session storage
- ToolkitRegistry: Global registry for toolkit discovery
"""

__version__ = "0.1.0"

from .agent import ChatAgent, CompletionBackend
from .models import (
    AgentContext,
    AgentResponse,
    ChatMessage,
    ChatSession,
    ToolResult,
)
from .session import (
    InMemorySessionBackend,
    RedisSessionBackend,
    SessionBackend,
)
from .toolkit import DomainToolkit

__all__ = [
    "__version__",
    # Agent
    "ChatAgent",
    "CompletionBackend",
    # Models
    "AgentContext",
    "AgentResponse",
    "ChatMessage",
    "ChatSession",
    "ToolResult",
    # Toolkit
    "DomainToolkit",
    # Session
    "SessionBackend",
    "InMemorySessionBackend",
    "RedisSessionBackend",
]
