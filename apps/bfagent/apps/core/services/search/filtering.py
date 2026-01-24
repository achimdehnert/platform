"""
Core Search Service - Advanced Filtering

Metadata filtering with complex boolean logic.
"""

from typing import Any, Callable, Dict, List


class MetadataFilter:
    """Advanced metadata filtering with boolean logic"""

    def __init__(self):
        self.filters: List[Dict[str, Any]] = []

    def add_filter(self, key: str, operator: str, value: Any) -> "MetadataFilter":
        """
        Add filter condition

        Operators:
            - eq: Equal
            - ne: Not equal
            - in: Value in list
            - contains: String/list contains value
            - gt, gte: Greater than (equal)
            - lt, lte: Less than (equal)
            - exists: Key exists
            - not_exists: Key does not exist

        Args:
            key: Metadata key
            operator: Comparison operator
            value: Comparison value

        Returns:
            Self for chaining
        """
        self.filters.append({"key": key, "operator": operator, "value": value})
        return self

    def matches(self, metadata: Dict[str, Any]) -> bool:
        """
        Check if metadata matches all filters (AND logic)

        Args:
            metadata: Metadata dict to check

        Returns:
            True if all filters match
        """
        for filter_def in self.filters:
            if not self._evaluate_filter(metadata, filter_def):
                return False
        return True

    def _evaluate_filter(self, metadata: Dict, filter_def: Dict) -> bool:
        """Evaluate single filter condition"""
        key = filter_def["key"]
        op = filter_def["operator"]
        value = filter_def["value"]

        actual = metadata.get(key)

        if op == "eq":
            return actual == value
        elif op == "ne":
            return actual != value
        elif op == "in":
            return actual in value if isinstance(value, (list, tuple, set)) else False
        elif op == "contains":
            if isinstance(actual, str):
                return value in actual
            elif isinstance(actual, (list, tuple)):
                return value in actual
            return False
        elif op == "gt":
            return actual > value if actual is not None else False
        elif op == "gte":
            return actual >= value if actual is not None else False
        elif op == "lt":
            return actual < value if actual is not None else False
        elif op == "lte":
            return actual <= value if actual is not None else False
        elif op == "exists":
            return key in metadata
        elif op == "not_exists":
            return key not in metadata
        else:
            raise ValueError(f"Unknown operator: {op}")

    def clear(self) -> None:
        """Clear all filters"""
        self.filters.clear()

    def __repr__(self) -> str:
        return f"MetadataFilter({len(self.filters)} conditions)"


class FilterBuilder:
    """Fluent builder for complex filters"""

    def __init__(self):
        self.filter = MetadataFilter()

    def where(self, key: str, operator: str, value: Any) -> "FilterBuilder":
        """Add filter condition"""
        self.filter.add_filter(key, operator, value)
        return self

    def equals(self, key: str, value: Any) -> "FilterBuilder":
        """Shorthand for equals"""
        return self.where(key, "eq", value)

    def not_equals(self, key: str, value: Any) -> "FilterBuilder":
        """Shorthand for not equals"""
        return self.where(key, "ne", value)

    def in_list(self, key: str, values: List[Any]) -> "FilterBuilder":
        """Shorthand for in list"""
        return self.where(key, "in", values)

    def contains(self, key: str, value: Any) -> "FilterBuilder":
        """Shorthand for contains"""
        return self.where(key, "contains", value)

    def greater_than(self, key: str, value: Any) -> "FilterBuilder":
        """Shorthand for greater than"""
        return self.where(key, "gt", value)

    def less_than(self, key: str, value: Any) -> "FilterBuilder":
        """Shorthand for less than"""
        return self.where(key, "lt", value)

    def build(self) -> MetadataFilter:
        """Build and return filter"""
        return self.filter


__all__ = ["MetadataFilter", "FilterBuilder"]
