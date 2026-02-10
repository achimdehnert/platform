"""
Shared Scoring and Routing Engine for task complexity estimation.

Zero-dependency Python package that provides weighted multi-dimension
keyword scoring with sigmoid confidence calibration. Consolidates
scoring logic from BFAgent (TestRequirement, LLMRouter) and
Orchestrator MCP (analyzer).

Usage:
    from task_scorer import score_task, ScoringConfig

    # With defaults
    result = score_task("fix the authentication bug in the API")
    print(result.tier)        # Tier.HIGH
    print(result.top_type)    # "security"
    print(result.confidence)  # 0.87

    # With custom config (e.g. from DB)
    config = ScoringConfig(keywords={"security": ["auth", "cve"]})
    result = score_task("check auth flow", config=config)
"""

from .scorer import score_task
from .types import ScoringConfig, ScoringResult, Tier

__all__ = [
    "score_task",
    "ScoringConfig",
    "ScoringResult",
    "Tier",
]

__version__ = "0.1.0"
