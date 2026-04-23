"""
Auditor registry — loads plugins and runs them against a HubDNA.

Populates the composite ScoreTree with results from all auditors.
"""

from __future__ import annotations

import logging
from importlib.metadata import entry_points

from hub_identity.core.plugins import AuditorPlugin
from hub_identity.core.schema import HubDNA
from hub_identity.core.scoring import ScoreNode, ScoreTree

logger = logging.getLogger(__name__)


def load_auditors() -> list[AuditorPlugin]:
    """Load all auditor plugins from entry points."""
    auditors = []
    eps = entry_points(group="hub_identity.auditors")
    for ep in eps:
        try:
            cls = ep.load()
            auditors.append(cls())
        except Exception as e:
            logger.warning(
                "Failed to load auditor %s: %s", ep.name, e,
            )
    return auditors


def audit_hub(
    dna: HubDNA,
    auditors: list[AuditorPlugin] | None = None,
) -> ScoreNode:
    """
    Run all auditors against a HubDNA, return populated ScoreTree.

    Each auditor writes its matches into the corresponding
    ScoreNode (matched by auditor.category + auditor.name).
    """
    if auditors is None:
        auditors = load_auditors()

    tree = ScoreTree.create()

    for auditor in auditors:
        matches = auditor.detect(dna)
        total_weight = sum(m.weight for m in matches)
        multiplier = auditor.weight_multiplier()
        score = min(total_weight * multiplier, 100.0)

        # Find the right node in the tree
        node = tree.find(auditor.name.title())
        if not node:
            node = tree.find(auditor.category.title())
        if node:
            node.raw_score = score
            node.details = [
                f"{m.pattern_id}: {m.description}"
                for m in matches[:5]
            ]

    return tree
