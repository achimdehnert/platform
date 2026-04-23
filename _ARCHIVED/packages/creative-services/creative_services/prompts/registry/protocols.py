"""
Protocol definitions for template registry.

These protocols define the interface that all registry implementations must follow,
enabling dependency injection and easy testing.
"""

from typing import Protocol, runtime_checkable

from ..schemas import PromptTemplateSpec


@runtime_checkable
class TemplateStore(Protocol):
    """
    Protocol for basic template storage operations.
    
    This is the minimal interface for storing and retrieving templates.
    """

    def get(self, template_key: str) -> PromptTemplateSpec | None:
        """
        Get a template by key.
        
        Args:
            template_key: Unique template identifier
            
        Returns:
            Template if found, None otherwise
        """
        ...

    def exists(self, template_key: str) -> bool:
        """
        Check if a template exists.
        
        Args:
            template_key: Unique template identifier
            
        Returns:
            True if template exists
        """
        ...


@runtime_checkable
class TemplateRegistry(Protocol):
    """
    Protocol for full template registry operations.
    
    Extends TemplateStore with write operations and querying.
    """

    def get(self, template_key: str) -> PromptTemplateSpec | None:
        """Get a template by key."""
        ...

    def exists(self, template_key: str) -> bool:
        """Check if a template exists."""
        ...

    def save(self, template: PromptTemplateSpec) -> None:
        """
        Save a template to the registry.
        
        Args:
            template: Template to save
            
        Raises:
            TemplateValidationError: If template is invalid
        """
        ...

    def delete(self, template_key: str) -> bool:
        """
        Delete a template from the registry.
        
        Args:
            template_key: Key of template to delete
            
        Returns:
            True if deleted, False if not found
        """
        ...

    def list_keys(self, domain_code: str | None = None) -> list[str]:
        """
        List all template keys, optionally filtered by domain.
        
        Args:
            domain_code: Optional domain filter
            
        Returns:
            List of template keys
        """
        ...

    def list_by_domain(self, domain_code: str) -> list[PromptTemplateSpec]:
        """
        Get all templates for a domain.
        
        Args:
            domain_code: Domain to filter by
            
        Returns:
            List of templates
        """
        ...

    def search(
        self,
        query: str | None = None,
        domain_code: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        active_only: bool = True,
    ) -> list[PromptTemplateSpec]:
        """
        Search templates with filters.
        
        Args:
            query: Text search in name/description
            domain_code: Filter by domain
            category: Filter by category
            tags: Filter by tags (any match)
            active_only: Only return active templates
            
        Returns:
            List of matching templates
        """
        ...
