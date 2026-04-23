"""Source document retriever — plugin/hook system (#1).

Consuming apps (e.g. risk-hub) register retrievers at startup:

    from doc_templates.services.retriever import register_source_retriever

    def get_sds_texts(tenant_id, instance):
        return ["SDS content for Substance X...", ...]

    register_source_retriever("sds", get_sds_texts)

The retriever callable receives (tenant_id: str, instance: DocumentInstance)
and returns a list of text strings to inject into the LLM prompt.
"""

import logging
from typing import Callable

logger = logging.getLogger(__name__)

# Registry: source_type → callable(tenant_id, instance) → list[str]
_RETRIEVERS: dict[str, Callable] = {}


def register_source_retriever(
    source_type: str,
    retriever: Callable,
) -> None:
    """Register a retriever for a source document type.

    Args:
        source_type: Key matching AI_SOURCE_TYPES (e.g. 'sds', 'cad').
        retriever: Callable(tenant_id: str, instance) -> list[str].
    """
    _RETRIEVERS[source_type] = retriever
    logger.debug("Registered source retriever for '%s'", source_type)


def get_source_content(
    source_type: str,
    tenant_id: str,
    instance,
) -> list[str]:
    """Retrieve actual document content for a source type.

    Returns list of text snippets. Empty list if no retriever registered.
    """
    retriever = _RETRIEVERS.get(source_type)
    if retriever is None:
        return []
    try:
        result = retriever(tenant_id, instance)
        if isinstance(result, str):
            return [result]
        return list(result) if result else []
    except Exception as exc:
        logger.warning(
            "Source retriever '%s' failed: %s", source_type, exc,
        )
        return []


def get_all_source_content(
    source_types: list[str],
    tenant_id: str,
    instance,
) -> dict[str, list[str]]:
    """Retrieve content for multiple source types at once.

    Returns dict: source_type → list[str] (only non-empty).
    """
    result = {}
    for src in source_types:
        texts = get_source_content(src, tenant_id, instance)
        if texts:
            result[src] = texts
    return result


def list_registered_retrievers() -> list[str]:
    """Return list of source types that have a retriever registered."""
    return list(_RETRIEVERS.keys())
