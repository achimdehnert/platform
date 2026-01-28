"""
In-memory template registry implementation.

Useful for testing and development. Not persistent.
"""

from typing import Any

from ..schemas import PromptTemplateSpec
from ..exceptions import TemplateNotFoundError, TemplateValidationError


class InMemoryRegistry:
    """
    In-memory template registry for testing and development.
    
    Templates are stored in a dictionary and lost on restart.
    Thread-safe for basic operations.
    
    Example:
        registry = InMemoryRegistry()
        registry.save(template)
        template = registry.get("my.template.v1")
    """

    def __init__(self, templates: dict[str, PromptTemplateSpec] | None = None):
        """
        Initialize the registry.
        
        Args:
            templates: Optional initial templates
        """
        self._templates: dict[str, PromptTemplateSpec] = templates or {}

    def get(self, template_key: str) -> PromptTemplateSpec | None:
        """Get a template by key."""
        return self._templates.get(template_key)

    def get_or_raise(self, template_key: str) -> PromptTemplateSpec:
        """Get a template or raise TemplateNotFoundError."""
        template = self.get(template_key)
        if template is None:
            raise TemplateNotFoundError(template_key, registry="memory")
        return template

    def exists(self, template_key: str) -> bool:
        """Check if a template exists."""
        return template_key in self._templates

    def save(self, template: PromptTemplateSpec) -> None:
        """
        Save a template to the registry.
        
        Validates the template before saving.
        """
        # Template is already validated by Pydantic
        self._templates[template.template_key] = template

    def delete(self, template_key: str) -> bool:
        """Delete a template. Returns True if deleted."""
        if template_key in self._templates:
            del self._templates[template_key]
            return True
        return False

    def list_keys(self, domain_code: str | None = None) -> list[str]:
        """List all template keys, optionally filtered by domain."""
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

        # Filter by active status
        if active_only:
            results = [t for t in results if t.is_active]

        # Filter by domain
        if domain_code:
            results = [t for t in results if t.domain_code == domain_code]

        # Filter by category
        if category:
            results = [t for t in results if t.category == category]

        # Filter by tags (any match)
        if tags:
            tag_set = set(tags)
            results = [t for t in results if tag_set & set(t.tags)]

        # Text search in name and description
        if query:
            query_lower = query.lower()
            results = [
                t for t in results
                if query_lower in t.name.lower()
                or (t.description and query_lower in t.description.lower())
            ]

        return results

    def clear(self) -> None:
        """Clear all templates."""
        self._templates.clear()

    def count(self) -> int:
        """Get total number of templates."""
        return len(self._templates)

    @classmethod
    def from_dict(cls, data: dict[str, dict[str, Any]]) -> "InMemoryRegistry":
        """
        Create registry from a dictionary of template data.
        
        Args:
            data: Dict mapping template_key to template data
            
        Returns:
            Populated registry
        """
        templates = {}
        for key, template_data in data.items():
            # Ensure template_key is set
            if "template_key" not in template_data:
                template_data["template_key"] = key
            templates[key] = PromptTemplateSpec(**template_data)
        return cls(templates)
