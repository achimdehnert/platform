"""
Mutation Pipeline (Design #3: Strategy Pattern).

Orchestrates deterministic + LLM strategies in order.
Deterministic strategies run first (free, fast, testable).
LLM strategy only if score still above threshold.
"""

from __future__ import annotations

import logging
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hub_identity.core.plugins import MutationStrategy
    from hub_identity.core.schema import HubDNA
    from hub_identity.core.scoring import ScoreNode

logger = logging.getLogger(__name__)


class MutationPipeline:
    """
    Runs mutation strategies in sequence.

    Order: deterministic first, LLM last.
    Stops early if score drops below threshold.
    """

    def __init__(
        self,
        strategies: list[MutationStrategy] | None = None,
        threshold: float = 25.0,
    ) -> None:
        if strategies is not None:
            self.strategies = strategies
        else:
            self.strategies = self._load_plugins()
        self.threshold = threshold

    @staticmethod
    def _load_plugins() -> list[MutationStrategy]:
        """Load strategies from entry points, sorted: deterministic first."""
        strategies = []
        eps = entry_points(group="hub_identity.mutations")
        for ep in eps:
            try:
                cls = ep.load()
                strategies.append(cls())
            except Exception as e:
                logger.warning("Failed to load mutation %s: %s", ep.name, e)
        # Deterministic first, LLM last
        strategies.sort(key=lambda s: (s.requires_llm, s.name))
        return strategies

    def mutate(
        self,
        dna: HubDNA,
        score: ScoreNode,
        audit_fn: callable | None = None,
    ) -> HubDNA:
        """
        Run all applicable strategies in sequence.

        Args:
            dna: Current hub DNA
            score: Current score tree
            audit_fn: Optional re-audit function to check progress.
                      Signature: (HubDNA) -> ScoreNode
        """
        current_dna = dna
        current_score = score
        applied = []

        for strategy in self.strategies:
            if current_score.weighted_score < self.threshold:
                logger.info(
                    "Score %.1f < %.1f — stopping early",
                    current_score.weighted_score,
                    self.threshold,
                )
                break

            if not strategy.should_apply(current_dna, current_score):
                continue

            logger.info("Applying strategy: %s", strategy.name)
            try:
                new_dna = strategy.apply(current_dna)
                applied.append(strategy.name)
                current_dna = new_dna

                # Re-audit if function provided
                if audit_fn:
                    current_score = audit_fn(current_dna)
                    logger.info(
                        "  Score after %s: %.1f",
                        strategy.name,
                        current_score.weighted_score,
                    )
            except Exception as e:
                logger.error(
                    "Strategy %s failed: %s", strategy.name, e,
                )
                continue

        logger.info(
            "Pipeline complete: %d strategies applied (%s)",
            len(applied),
            ", ".join(applied) if applied else "none",
        )
        return current_dna

    def preview(
        self,
        dna: HubDNA,
        score: ScoreNode,
    ) -> list[dict]:
        """Preview which strategies would apply (dry run)."""
        previews = []
        for strategy in self.strategies:
            previews.append({
                "name": strategy.name,
                "requires_llm": strategy.requires_llm,
                "would_apply": strategy.should_apply(dna, score),
            })
        return previews
