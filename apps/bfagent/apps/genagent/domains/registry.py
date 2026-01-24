"""
Domain Template Registry

Central registry for all available domain templates.
Enables discovery, search, and management of templates.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from .base import DomainTemplate

logger = logging.getLogger(__name__)


class DomainRegistry:
    """
    Central registry for domain templates
    
    Manages all available templates and provides:
    - Registration of new templates
    - Search for templates
    - Validation
    - Import/Export
    """
    
    # Class-level storage
    _templates: Dict[str, DomainTemplate] = {}
    _categories: Dict[str, List[str]] = {}  # category -> [domain_ids]
    _tags: Dict[str, List[str]] = {}  # tag -> [domain_ids]
    _initialized: bool = False
    
    # ==================== REGISTRATION ====================
    
    @classmethod
    def register(cls, template: DomainTemplate, validate: bool = True) -> None:
        """
        Registers a new domain template
        
        Args:
            template: Template to register
            validate: Whether to validate the template
            
        Raises:
            ValueError: If template is invalid or ID already exists
        """
        if validate:
            try:
                template.validate()
            except Exception as e:
                raise ValueError(f"Template validation failed: {e}")
        
        domain_id = template.domain_id
        
        # Check for duplicates
        if domain_id in cls._templates:
            logger.warning(f"Overwriting existing template: {domain_id}")
        
        # Register template
        cls._templates[domain_id] = template
        
        # Update category index
        category = template.category
        if category not in cls._categories:
            cls._categories[category] = []
        if domain_id not in cls._categories[category]:
            cls._categories[category].append(domain_id)
        
        # Update tag index
        for tag in template.tags:
            if tag not in cls._tags:
                cls._tags[tag] = []
            if domain_id not in cls._tags[tag]:
                cls._tags[tag].append(domain_id)
        
        logger.info(f"Registered domain template: {domain_id} ({template.display_name})")
    
    @classmethod
    def unregister(cls, domain_id: str) -> bool:
        """
        Removes a template from the registry
        
        Args:
            domain_id: ID of template to remove
            
        Returns:
            True if successfully removed
        """
        if domain_id not in cls._templates:
            return False
        
        template = cls._templates[domain_id]
        
        # Remove from category index
        if template.category in cls._categories:
            cls._categories[template.category].remove(domain_id)
        
        # Remove from tag index
        for tag in template.tags:
            if tag in cls._tags:
                cls._tags[tag].remove(domain_id)
        
        # Remove template
        del cls._templates[domain_id]
        
        logger.info(f"Unregistered domain template: {domain_id}")
        return True
    
    # ==================== RETRIEVAL ====================
    
    @classmethod
    def get(cls, domain_id: str) -> DomainTemplate:
        """
        Gets a template by ID
        
        Args:
            domain_id: Template ID
            
        Returns:
            The template
            
        Raises:
            KeyError: If template not found
        """
        if domain_id not in cls._templates:
            available = ', '.join(cls._templates.keys())
            raise KeyError(
                f"Domain '{domain_id}' not found. "
                f"Available domains: {available or 'none'}"
            )
        
        return cls._templates[domain_id]
    
    @classmethod
    def get_safe(cls, domain_id: str) -> Optional[DomainTemplate]:
        """
        Gets a template, returns None if not found
        
        Args:
            domain_id: Template ID
            
        Returns:
            Template or None
        """
        return cls._templates.get(domain_id)
    
    @classmethod
    def list_all(cls) -> List[DomainTemplate]:
        """
        Returns all registered templates
        
        Returns:
            List of all templates
        """
        return list(cls._templates.values())
    
    @classmethod
    def list_ids(cls) -> List[str]:
        """
        Returns all template IDs
        
        Returns:
            List of IDs
        """
        return list(cls._templates.keys())
    
    @classmethod
    def exists(cls, domain_id: str) -> bool:
        """Checks if template exists"""
        return domain_id in cls._templates
    
    # ==================== SEARCH & FILTER ====================
    
    @classmethod
    def search(
        cls,
        query: str = None,
        category: str = None,
        tags: List[str] = None,
        match_all_tags: bool = False
    ) -> List[DomainTemplate]:
        """
        Searches templates by various criteria
        
        Args:
            query: Search term (searches in name, description, tags)
            category: Filter by category
            tags: Filter by tags
            match_all_tags: True = all tags must match, False = at least one
            
        Returns:
            List of found templates
        """
        results = cls.list_all()
        
        # Filter by category
        if category:
            results = [t for t in results if t.category == category]
        
        # Filter by tags
        if tags:
            if match_all_tags:
                # All tags must be present
                results = [
                    t for t in results
                    if all(tag in t.tags for tag in tags)
                ]
            else:
                # At least one tag must be present
                results = [
                    t for t in results
                    if any(tag in t.tags for tag in tags)
                ]
        
        # Text search
        if query:
            query_lower = query.lower()
            results = [
                t for t in results
                if (
                    query_lower in t.domain_id.lower() or
                    query_lower in t.display_name.lower() or
                    query_lower in t.description.lower() or
                    any(query_lower in tag.lower() for tag in t.tags)
                )
            ]
        
        return results
    
    @classmethod
    def get_by_category(cls, category: str) -> List[DomainTemplate]:
        """
        Gets all templates of a category
        
        Args:
            category: Category name
            
        Returns:
            List of templates in this category
        """
        if category not in cls._categories:
            return []
        
        domain_ids = cls._categories[category]
        return [cls._templates[did] for did in domain_ids]
    
    @classmethod
    def get_by_tag(cls, tag: str) -> List[DomainTemplate]:
        """
        Gets all templates with a specific tag
        
        Args:
            tag: Tag name
            
        Returns:
            List of templates with this tag
        """
        if tag not in cls._tags:
            return []
        
        domain_ids = cls._tags[tag]
        return [cls._templates[did] for did in domain_ids]
    
    @classmethod
    def list_categories(cls) -> List[str]:
        """Returns all available categories"""
        return list(cls._categories.keys())
    
    @classmethod
    def list_tags(cls) -> List[str]:
        """Returns all used tags"""
        return list(cls._tags.keys())
    
    # ==================== STATISTICS ====================
    
    @classmethod
    def get_statistics(cls) -> Dict[str, any]:
        """
        Returns statistics about the registry
        
        Returns:
            Dict with various metrics
        """
        templates = cls.list_all()
        
        return {
            'total_templates': len(templates),
            'total_categories': len(cls._categories),
            'total_tags': len(cls._tags),
            'templates_by_category': {
                cat: len(ids) for cat, ids in cls._categories.items()
            },
            'total_phases': sum(len(t.phases) for t in templates),
            'total_actions': sum(len(t.get_all_actions()) for t in templates),
            'avg_phases_per_template': (
                sum(len(t.phases) for t in templates) / len(templates)
                if templates else 0
            ),
            'avg_actions_per_template': (
                sum(len(t.get_all_actions()) for t in templates) / len(templates)
                if templates else 0
            ),
        }
    
    # ==================== IMPORT / EXPORT ====================
    
    @classmethod
    def export_to_json(cls, filepath: Path, domain_id: str = None) -> None:
        """
        Exports template(s) to JSON
        
        Args:
            filepath: Target file
            domain_id: Optional, export only specific template
        """
        if domain_id:
            # Export single template
            template = cls.get(domain_id)
            data = template.to_dict()
        else:
            # Export all templates
            data = {
                did: template.to_dict()
                for did, template in cls._templates.items()
            }
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported to: {filepath}")
    
    @classmethod
    def import_from_json(cls, filepath: Path) -> List[str]:
        """
        Imports template(s) from JSON
        
        Args:
            filepath: Source file
            
        Returns:
            List of imported domain_ids
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        imported = []
        
        # Check if single template or dictionary
        if isinstance(data, dict) and 'domain_id' in data:
            # Single template
            template = DomainTemplate.from_dict(data)
            cls.register(template)
            imported.append(template.domain_id)
        else:
            # Multiple templates
            for domain_id, template_data in data.items():
                template = DomainTemplate.from_dict(template_data)
                cls.register(template)
                imported.append(template.domain_id)
        
        logger.info(f"Imported {len(imported)} templates from: {filepath}")
        return imported
    
    # ==================== UTILITY ====================
    
    @classmethod
    def clear(cls) -> None:
        """Clears all templates from the registry (for tests)"""
        cls._templates.clear()
        cls._categories.clear()
        cls._tags.clear()
        logger.info("Registry cleared")
    
    @classmethod
    def count(cls) -> int:
        """Returns number of registered templates"""
        return len(cls._templates)
    
    @classmethod
    def print_summary(cls) -> None:
        """Prints overview of all templates"""
        print("\n" + "="*60)
        print("DOMAIN TEMPLATE REGISTRY")
        print("="*60)
        
        stats = cls.get_statistics()
        
        print(f"\nStatistics:")
        print(f"   Total Templates: {stats['total_templates']}")
        print(f"   Categories: {stats['total_categories']}")
        print(f"   Tags: {stats['total_tags']}")
        print(f"   Total Phases: {stats['total_phases']}")
        print(f"   Total Actions: {stats['total_actions']}")
        
        print(f"\nTemplates by Category:")
        for category, count in stats['templates_by_category'].items():
            print(f"   {category}: {count}")
        
        print("\nRegistered Templates:")
        for domain_id, template in cls._templates.items():
            print(f"   {template.icon} {template.display_name} ({domain_id})")
            print(f"      └─ {len(template.phases)} phases, {len(template.get_all_actions())} actions")
        
        print("\n" + "="*60 + "\n")
    
    @classmethod
    def initialize(cls) -> None:
        """
        Initializes the registry
        
        Called automatically on first access.
        Can be overridden to load templates.
        """
        if cls._initialized:
            return
        
        # Here templates could be automatically loaded
        # e.g., from a configuration file or database
        
        cls._initialized = True
        logger.info("Registry initialized")


# ==================== DECORATOR FOR AUTO-REGISTRATION ====================

def register_domain(template: DomainTemplate) -> DomainTemplate:
    """
    Decorator for automatic template registration
    
    Usage:
        @register_domain
        def create_explosion_template():
            return DomainTemplate(...)
    """
    DomainRegistry.register(template)
    return template


# ==================== INITIALIZATION ====================

# Auto-initialize on import
DomainRegistry.initialize()
