"""
Temporal Client — Singleton für alle Platform-Services (ADR-077)

Nutzung:
    from platform_context.temporal_client import get_temporal_client

    client = await get_temporal_client()
    handle = await client.start_workflow(...)

Konfiguration via Env-Vars:
    TEMPORAL_ADDRESS   — default: "temporal:7233"
    TEMPORAL_NAMESPACE — default: "platform-dev"

Hinweis: temporalio ist ein optionales Extra.
    pip install platform-context[temporal]
"""

import os

TEMPORAL_ADDRESS = os.environ.get("TEMPORAL_ADDRESS", "temporal:7233")
TEMPORAL_NAMESPACE = os.environ.get("TEMPORAL_NAMESPACE", "platform-dev")

_client = None


async def get_temporal_client():
    """
    Singleton — Temporal-Client ist teuer zu erstellen, wird gecacht.

    Returns:
        temporalio.client.Client
    """
    global _client
    if _client is None:
        try:
            from temporalio.client import Client
        except ImportError as exc:
            raise ImportError(
                "temporalio is required for Temporal support. "
                "Install with: pip install platform-context[temporal]"
            ) from exc
        _client = await Client.connect(TEMPORAL_ADDRESS, namespace=TEMPORAL_NAMESPACE)
    return _client


def reset_temporal_client() -> None:
    """Setzt den gecachten Client zurück — nützlich in Tests."""
    global _client
    _client = None
