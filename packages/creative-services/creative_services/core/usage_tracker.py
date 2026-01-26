"""
Usage Tracker - Track LLM usage and costs.

Provides:
- UsageRecord: Single usage record
- UsageTracker Protocol: Interface for usage storage
- InMemoryTracker: Simple in-memory tracker for testing
- Adapters for Django ORM integration (in consuming apps)

Usage:
    tracker = InMemoryTracker()
    
    # Track usage
    tracker.track(
        llm_id=2,
        app_name="travel-beat",
        service_name="story_generator",
        tokens_input=500,
        tokens_output=1500,
        cost=0.001,
        latency_ms=2500,
    )
    
    # Get stats
    stats = tracker.get_stats(app_name="travel-beat")
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Protocol, runtime_checkable
from collections import defaultdict


@dataclass
class UsageRecord:
    """Single LLM usage record."""
    id: Optional[int] = None
    llm_id: int = 0
    llm_name: str = ""
    app_name: str = ""
    service_name: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    cost: float = 0.0
    latency_ms: int = 0
    success: bool = True
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def total_tokens(self) -> int:
        return self.tokens_input + self.tokens_output


@dataclass
class UsageStats:
    """Aggregated usage statistics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_cost: float = 0.0
    avg_latency_ms: float = 0.0
    
    @property
    def total_tokens(self) -> int:
        return self.total_tokens_input + self.total_tokens_output
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def avg_cost_per_request(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_cost / self.total_requests


@runtime_checkable
class UsageTracker(Protocol):
    """Protocol for usage tracker implementations."""
    
    def track(
        self,
        llm_id: int,
        app_name: str,
        service_name: str,
        tokens_input: int,
        tokens_output: int,
        cost: float,
        latency_ms: int,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> UsageRecord:
        """Track a single LLM usage."""
        ...
    
    def get_stats(
        self,
        app_name: Optional[str] = None,
        service_name: Optional[str] = None,
        llm_id: Optional[int] = None,
        since: Optional[datetime] = None,
    ) -> UsageStats:
        """Get aggregated usage statistics."""
        ...
    
    def get_recent(
        self,
        limit: int = 100,
        app_name: Optional[str] = None,
    ) -> list[UsageRecord]:
        """Get recent usage records."""
        ...


class InMemoryTracker:
    """Simple in-memory usage tracker for testing."""
    
    def __init__(self):
        self._records: list[UsageRecord] = []
        self._next_id = 1
    
    def track(
        self,
        llm_id: int,
        app_name: str,
        service_name: str,
        tokens_input: int,
        tokens_output: int,
        cost: float,
        latency_ms: int,
        success: bool = True,
        error_message: Optional[str] = None,
        llm_name: str = "",
    ) -> UsageRecord:
        """Track a single LLM usage."""
        record = UsageRecord(
            id=self._next_id,
            llm_id=llm_id,
            llm_name=llm_name,
            app_name=app_name,
            service_name=service_name,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost=cost,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
        )
        self._records.append(record)
        self._next_id += 1
        return record
    
    def get_stats(
        self,
        app_name: Optional[str] = None,
        service_name: Optional[str] = None,
        llm_id: Optional[int] = None,
        since: Optional[datetime] = None,
    ) -> UsageStats:
        """Get aggregated usage statistics."""
        filtered = self._filter_records(app_name, service_name, llm_id, since)
        
        if not filtered:
            return UsageStats()
        
        total_latency = sum(r.latency_ms for r in filtered)
        
        return UsageStats(
            total_requests=len(filtered),
            successful_requests=sum(1 for r in filtered if r.success),
            failed_requests=sum(1 for r in filtered if not r.success),
            total_tokens_input=sum(r.tokens_input for r in filtered),
            total_tokens_output=sum(r.tokens_output for r in filtered),
            total_cost=sum(r.cost for r in filtered),
            avg_latency_ms=total_latency / len(filtered) if filtered else 0,
        )
    
    def get_recent(
        self,
        limit: int = 100,
        app_name: Optional[str] = None,
    ) -> list[UsageRecord]:
        """Get recent usage records."""
        filtered = self._records
        if app_name:
            filtered = [r for r in filtered if r.app_name == app_name]
        return sorted(filtered, key=lambda r: r.created_at, reverse=True)[:limit]
    
    def _filter_records(
        self,
        app_name: Optional[str] = None,
        service_name: Optional[str] = None,
        llm_id: Optional[int] = None,
        since: Optional[datetime] = None,
    ) -> list[UsageRecord]:
        """Filter records by criteria."""
        result = self._records
        
        if app_name:
            result = [r for r in result if r.app_name == app_name]
        if service_name:
            result = [r for r in result if r.service_name == service_name]
        if llm_id:
            result = [r for r in result if r.llm_id == llm_id]
        if since:
            result = [r for r in result if r.created_at >= since]
        
        return result
    
    def get_cost_by_app(self) -> dict[str, float]:
        """Get total cost grouped by app."""
        costs: dict[str, float] = defaultdict(float)
        for record in self._records:
            costs[record.app_name] += record.cost
        return dict(costs)
    
    def get_cost_by_service(self, app_name: Optional[str] = None) -> dict[str, float]:
        """Get total cost grouped by service."""
        costs: dict[str, float] = defaultdict(float)
        for record in self._records:
            if app_name and record.app_name != app_name:
                continue
            costs[record.service_name] += record.cost
        return dict(costs)
    
    def clear(self) -> None:
        """Clear all records (for testing)."""
        self._records.clear()
        self._next_id = 1


def calculate_cost(
    tokens_input: int,
    tokens_output: int,
    cost_per_1k_input: float,
    cost_per_1k_output: float,
) -> float:
    """Calculate cost from token counts and rates."""
    input_cost = (tokens_input / 1000) * cost_per_1k_input
    output_cost = (tokens_output / 1000) * cost_per_1k_output
    return input_cost + output_cost
