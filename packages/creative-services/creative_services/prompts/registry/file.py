"""
File-based template registry implementation.

Supports YAML and JSON files for template storage.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from ..schemas import PromptTemplateSpec
from ..exceptions import TemplateNotFoundError, TemplateValidationError


class FileRegistry:
    """
    File-based template registry.
    
    Loads templates from YAML or JSON files. Supports both single-file
    and directory-based storage.
    
    Example:
        # Single file with multiple templates
        registry = FileRegistry.from_file("templates.yaml")
        
        # Directory with one file per template
        registry = FileRegistry.from_directory("templates/")
    """

    def __init__(self, templates: dict[str, PromptTemplateSpec] | None = None):
        """Initialize with optional pre-loaded templates."""
        self._templates: dict[str, PromptTemplateSpec] = templates or {}
        self._source_path: Path | None = None

    def get(self, template_key: str) -> PromptTemplateSpec | None:
        """Get a template by key."""
        return self._templates.get(template_key)

    def get_or_raise(self, template_key: str) -> PromptTemplateSpec:
        """Get a template or raise TemplateNotFoundError."""
        template = self.get(template_key)
        if template is None:
            raise TemplateNotFoundError(template_key, registry="file")
        return template

    def exists(self, template_key: str) -> bool:
        """Check if a template exists."""
        return template_key in self._templates

    def save(self, template: PromptTemplateSpec) -> None:
        """
        Save a template (in-memory only).
        
        Note: This does not persist to disk. Use export() to save.
        """
        self._templates[template.template_key] = template

    def delete(self, template_key: str) -> bool:
        """Delete a template (in-memory only)."""
        if template_key in self._templates:
            del self._templates[template_key]
            return True
        return False

    def list_keys(self, domain_code: str | None = None) -> list[str]:
        """List all template keys."""
        if domain_code is None:
            return list(self._templates.keys())
        return [
            key for key, t in self._templates.items()
            if t.domain_code == domain_code
        ]

    def list_by_domain(self, domain_code: str) -> list[PromptTemplateSpec]:
        """Get all templates for a domain."""
        return [
            t for t in self._templates.values()
            if t.domain_code == domain_code
        ]

    def search(
        self,
        query: str | None = None,
        domain_code: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        active_only: bool = True,
    ) -> list[PromptTemplateSpec]:
        """Search templates with filters."""
        results = list(self._templates.values())

        if active_only:
            results = [t for t in results if t.is_active]
        if domain_code:
            results = [t for t in results if t.domain_code == domain_code]
        if category:
            results = [t for t in results if t.category == category]
        if tags:
            tag_set = set(tags)
            results = [t for t in results if tag_set & set(t.tags)]
        if query:
            query_lower = query.lower()
            results = [
                t for t in results
                if query_lower in t.name.lower()
                or (t.description and query_lower in t.description.lower())
            ]

        return results

    def count(self) -> int:
        """Get total number of templates."""
        return len(self._templates)

    def reload(self) -> None:
        """Reload templates from source file/directory."""
        if self._source_path is None:
            raise ValueError("No source path set. Use from_file() or from_directory().")
        
        if self._source_path.is_file():
            self._load_from_file(self._source_path)
        else:
            self._load_from_directory(self._source_path)

    def export_to_file(self, path: str | Path, format: str = "json") -> None:
        """
        Export all templates to a file.
        
        Args:
            path: Output file path
            format: 'json' or 'yaml'
        """
        path = Path(path)
        data = {
            key: template.model_dump(mode="json")
            for key, template in self._templates.items()
        }

        if format == "yaml":
            try:
                import yaml
                with open(path, "w", encoding="utf-8") as f:
                    yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            except ImportError:
                raise ImportError("PyYAML is required for YAML export. Install with: pip install pyyaml")
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def from_file(cls, path: str | Path) -> "FileRegistry":
        """
        Load templates from a single file.
        
        Supports .json, .yaml, .yml files.
        File should contain a dict mapping template_key to template data.
        """
        registry = cls()
        registry._source_path = Path(path)
        registry._load_from_file(registry._source_path)
        return registry

    @classmethod
    def from_directory(cls, path: str | Path, recursive: bool = True) -> "FileRegistry":
        """
        Load templates from a directory.
        
        Each .json/.yaml/.yml file should contain a single template
        or a dict of templates.
        """
        registry = cls()
        registry._source_path = Path(path)
        registry._load_from_directory(registry._source_path, recursive)
        return registry

    def _load_from_file(self, path: Path) -> None:
        """Load templates from a single file."""
        if not path.exists():
            raise FileNotFoundError(f"Template file not found: {path}")

        suffix = path.suffix.lower()
        
        if suffix == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        elif suffix in (".yaml", ".yml"):
            try:
                import yaml
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            except ImportError:
                raise ImportError("PyYAML is required for YAML files. Install with: pip install pyyaml")
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

        self._parse_template_data(data)

    def _load_from_directory(self, path: Path, recursive: bool = True) -> None:
        """Load templates from a directory."""
        if not path.exists():
            raise FileNotFoundError(f"Template directory not found: {path}")

        pattern = "**/*" if recursive else "*"
        
        for file_path in path.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in (".json", ".yaml", ".yml"):
                try:
                    self._load_from_file(file_path)
                except Exception as e:
                    # Log warning but continue loading other files
                    logger.warning("Failed to load %s: %s", file_path, e)

    def _parse_template_data(self, data: dict[str, Any]) -> None:
        """Parse template data and add to registry."""
        if not isinstance(data, dict):
            raise TemplateValidationError("root", ["Expected dict at root level"])

        # Check if this is a single template or multiple
        if "template_key" in data:
            # Single template
            template = PromptTemplateSpec(**data)
            self._templates[template.template_key] = template
        else:
            # Multiple templates
            for key, template_data in data.items():
                if isinstance(template_data, dict):
                    if "template_key" not in template_data:
                        template_data["template_key"] = key
                    template = PromptTemplateSpec(**template_data)
                    self._templates[template.template_key] = template
