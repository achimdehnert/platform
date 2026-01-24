"""
Feature Registry System for BF Agent
Tracks implemented features to prevent duplication
"""

import json
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Dict, List, Optional


class FeatureRegistry:
    _instance = None
    _features = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(
        self,
        name: str,
        version: str = "1.0",
        status: str = "complete",
        tests: Optional[List[str]] = None,
        htmx_endpoints: Optional[List[str]] = None,
        templates: Optional[List[str]] = None,
    ):
        """
        Register a feature with metadata

        Args:
            name: Feature name (e.g., "llm_test_interface")
            version: Version string
            status: 'complete', 'partial', 'testing', 'deprecated'
            tests: List of test functions/files
            htmx_endpoints: List of HTMX endpoints used
            templates: List of template files
        """

        def decorator(func):
            self._features[name] = {
                "function": f"{func.__module__}.{func.__name__}",
                "version": version,
                "status": status,
                "tests": tests or [],
                "htmx_endpoints": htmx_endpoints or [],
                "templates": templates or [],
                "registered_at": datetime.now().isoformat(),
                "docstring": func.__doc__ or "No description",
            }

            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def get_features(self) -> Dict:
        """Get all registered features"""
        return self._features.copy()

    def get_feature(self, name: str) -> Optional[Dict]:
        """Get specific feature info"""
        return self._features.get(name)

    def is_implemented(self, name: str) -> bool:
        """Check if feature is implemented"""
        feature = self._features.get(name)
        return feature and feature["status"] in ["complete", "testing"]

    def export_to_file(self, filepath: str = ".ai_context/features.json"):
        """Export feature registry to JSON file"""
        Path(filepath).parent.mkdir(exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(self._features, f, indent=2)

    def generate_markdown_report(self) -> str:
        """Generate markdown report of all features"""
        report = ["# Feature Registry Report\n"]

        by_status = {}
        for name, info in self._features.items():
            status = info["status"]
            if status not in by_status:
                by_status[status] = []
            by_status[status].append((name, info))

        for status in ["complete", "testing", "partial", "deprecated"]:
            if status in by_status:
                report.append(f"## {status.title()} Features\n")
                for name, info in by_status[status]:
                    report.append(f"- **{name}** (v{info['version']})")
                    report.append(f"  - Function: `{info['function']}`")
                    if info["htmx_endpoints"]:
                        report.append(f"  - HTMX: {', '.join(info['htmx_endpoints'])}")
                    if info["templates"]:
                        report.append(f"  - Templates: {', '.join(info['templates'])}")
                    report.append("")

        return "\n".join(report)


# Global registry instance
registry = FeatureRegistry()


# Convenience decorator
def feature(name: str, **kwargs):
    """Decorator to register a feature"""
    return registry.register(name, **kwargs)
