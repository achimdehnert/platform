"""
LLM Cost Tracker & Utilities
============================

Cost tracking, token estimation, and utility functions.

Usage:
    from apps.core.services.llm import CostTracker

    tracker = CostTracker()
    tracker.record(response)
    print(tracker.get_summary())
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import LLM_PRICING, LLMResponse, TokenUsage

logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    """Single usage record."""

    timestamp: datetime
    provider: str
    model: str
    usage: TokenUsage
    cost: float
    latency_ms: int
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class CostTracker:
    """
    Track LLM usage and costs across requests.

    Provides:
    - Per-request cost tracking
    - Aggregated statistics
    - Budget monitoring
    - Usage reports

    Example:
        tracker = CostTracker(budget_limit=10.0)

        response = client.generate("Hello")
        tracker.record(response, provider="openai", model="gpt-4")

        if tracker.is_over_budget():
            print("Budget exceeded!")

        print(tracker.get_summary())
    """

    def __init__(self, budget_limit: Optional[float] = None):
        """
        Initialize cost tracker.

        Args:
            budget_limit: Optional budget limit in USD
        """
        self.budget_limit = budget_limit
        self.records: List[UsageRecord] = []
        self._totals: Dict[str, float] = defaultdict(float)

    def record(
        self, response: LLMResponse, provider: str = "unknown", model: str = "unknown", **metadata
    ) -> float:
        """
        Record usage from a response.

        Args:
            response: LLMResponse to record
            provider: Provider name
            model: Model name
            **metadata: Additional metadata

        Returns:
            Calculated cost for this request
        """
        if not response.usage:
            return 0.0

        # Calculate cost
        cost = self._calculate_cost(provider, model, response.usage)

        # Create record
        record = UsageRecord(
            timestamp=datetime.now(),
            provider=provider,
            model=model,
            usage=response.usage,
            cost=cost,
            latency_ms=response.latency_ms or 0,
            success=response.success,
            metadata=metadata,
        )

        self.records.append(record)

        # Update totals
        self._totals["total_cost"] += cost
        self._totals["total_input_tokens"] += response.usage.prompt_tokens
        self._totals["total_output_tokens"] += response.usage.completion_tokens
        self._totals["total_requests"] += 1
        if response.success:
            self._totals["successful_requests"] += 1

        return cost

    def _calculate_cost(self, provider: str, model: str, usage: TokenUsage) -> float:
        """Calculate cost for token usage."""
        provider_pricing = LLM_PRICING.get(provider, {})
        model_pricing = provider_pricing.get(model, {})

        if not model_pricing:
            # Try partial match
            for m, p in provider_pricing.items():
                if m in model or model in m:
                    model_pricing = p
                    break

        if not model_pricing:
            return 0.0

        input_cost = (usage.prompt_tokens / 1000) * model_pricing.get("input", 0)
        output_cost = (usage.completion_tokens / 1000) * model_pricing.get("output", 0)

        return input_cost + output_cost

    def get_total_cost(self) -> float:
        """Get total cost across all records."""
        return self._totals["total_cost"]

    def get_remaining_budget(self) -> Optional[float]:
        """Get remaining budget (None if no limit set)."""
        if self.budget_limit is None:
            return None
        return max(0, self.budget_limit - self.get_total_cost())

    def is_over_budget(self) -> bool:
        """Check if budget limit exceeded."""
        if self.budget_limit is None:
            return False
        return self.get_total_cost() >= self.budget_limit

    def get_summary(self) -> Dict[str, Any]:
        """
        Get usage summary.

        Returns:
            Dict with usage statistics
        """
        return {
            "total_cost": round(self._totals["total_cost"], 6),
            "total_requests": int(self._totals["total_requests"]),
            "successful_requests": int(self._totals["successful_requests"]),
            "total_input_tokens": int(self._totals["total_input_tokens"]),
            "total_output_tokens": int(self._totals["total_output_tokens"]),
            "total_tokens": int(
                self._totals["total_input_tokens"] + self._totals["total_output_tokens"]
            ),
            "budget_limit": self.budget_limit,
            "remaining_budget": self.get_remaining_budget(),
            "is_over_budget": self.is_over_budget(),
            "records_count": len(self.records),
        }

    def get_breakdown_by_model(self) -> Dict[str, Dict[str, Any]]:
        """Get cost breakdown by model."""
        breakdown = defaultdict(
            lambda: {"cost": 0.0, "requests": 0, "input_tokens": 0, "output_tokens": 0}
        )

        for record in self.records:
            key = f"{record.provider}/{record.model}"
            breakdown[key]["cost"] += record.cost
            breakdown[key]["requests"] += 1
            breakdown[key]["input_tokens"] += record.usage.prompt_tokens
            breakdown[key]["output_tokens"] += record.usage.completion_tokens

        return dict(breakdown)

    def reset(self) -> None:
        """Reset all tracking data."""
        self.records.clear()
        self._totals.clear()


# ==================== Token Utilities ====================


def estimate_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Estimate token count for text.

    Uses tiktoken if available, otherwise falls back to
    character-based estimation.

    Args:
        text: Text to estimate
        model: Model name (for tiktoken encoding)

    Returns:
        Estimated token count
    """
    try:
        import tiktoken

        # Get encoding for model
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")

        return len(encoding.encode(text))

    except ImportError:
        # Fallback: ~4 characters per token for English
        return len(text) // 4


def truncate_to_tokens(
    text: str, max_tokens: int, model: str = "gpt-4", suffix: str = "..."
) -> str:
    """
    Truncate text to fit within token limit.

    Args:
        text: Text to truncate
        max_tokens: Maximum tokens allowed
        model: Model name (for tiktoken)
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    try:
        import tiktoken

        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")

        tokens = encoding.encode(text)

        if len(tokens) <= max_tokens:
            return text

        # Reserve space for suffix
        suffix_tokens = len(encoding.encode(suffix))
        truncated_tokens = tokens[: max_tokens - suffix_tokens]

        return encoding.decode(truncated_tokens) + suffix

    except ImportError:
        # Fallback: character-based
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text
        return text[: max_chars - len(suffix)] + suffix


def count_messages_tokens(messages: List[Dict[str, str]], model: str = "gpt-4") -> int:
    """
    Count tokens for a list of messages.

    Accounts for message formatting overhead.

    Args:
        messages: List of message dicts
        model: Model name

    Returns:
        Estimated token count
    """
    # Token overhead per message (role, formatting)
    overhead_per_message = 4

    total = 0
    for msg in messages:
        total += overhead_per_message
        total += estimate_tokens(msg.get("content", ""), model)
        total += estimate_tokens(msg.get("role", ""), model)

    # Base overhead
    total += 3

    return total


# ==================== Prompt Utilities ====================


def format_system_prompt(
    instructions: str, context: Optional[str] = None, constraints: Optional[List[str]] = None
) -> str:
    """
    Format a system prompt with optional context and constraints.

    Args:
        instructions: Main instructions
        context: Optional context to include
        constraints: Optional list of constraints

    Returns:
        Formatted system prompt
    """
    parts = [instructions]

    if context:
        parts.append(f"\n\nContext:\n{context}")

    if constraints:
        parts.append("\n\nConstraints:")
        for c in constraints:
            parts.append(f"- {c}")

    return "\n".join(parts)


def build_few_shot_prompt(
    examples: List[Dict[str, str]], query: str, instruction: Optional[str] = None
) -> str:
    """
    Build a few-shot prompt with examples.

    Args:
        examples: List of {"input": ..., "output": ...} dicts
        query: The actual query
        instruction: Optional instruction prefix

    Returns:
        Formatted prompt
    """
    parts = []

    if instruction:
        parts.append(instruction)
        parts.append("")

    for i, example in enumerate(examples, 1):
        parts.append(f"Example {i}:")
        parts.append(f"Input: {example['input']}")
        parts.append(f"Output: {example['output']}")
        parts.append("")

    parts.append("Now process this:")
    parts.append(f"Input: {query}")
    parts.append("Output:")

    return "\n".join(parts)
