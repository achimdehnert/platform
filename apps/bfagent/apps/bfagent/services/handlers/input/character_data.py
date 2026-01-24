"""
Character Data Input Handler

Collects character information for context building in AI actions.
"""

from typing import Any, Dict, List
import structlog

from ..base.input import BaseInputHandler
from ..exceptions import InputHandlerException
from ..decorators import with_logging, with_performance_monitoring
from ..schemas import CharacterDataConfig

logger = structlog.get_logger()


class CharacterDataHandler(BaseInputHandler):
    """
    Collect character data for context building.
    
    Useful for actions that need character context like:
    - Writing character-focused scenes
    - Analyzing character arcs
    - Generating character interactions
    - Ensuring character consistency
    
    Configuration:
        featured_only (bool): Only featured characters. Defaults to False.
        include_description (bool): Include full descriptions. Defaults to True.
        include_backstory (bool): Include backstory. Defaults to False.
        include_relationships (bool): Include character relationships. Defaults to False.
        include_arc (bool): Include character arc. Defaults to False.
        character_ids (list, optional): Specific character IDs to include
        limit (int, optional): Maximum number of characters to return
        role_filter (str, optional): Filter by role (protagonist, antagonist, supporting)
    
    Input Context:
        project (BookProjects): Required
    
    Returns:
        Dict with keys:
            - characters (list): List of character data dicts
            - character_count (int): Total number of characters
            - roles (dict): Count by role
    
    Example:
        >>> handler = CharacterDataHandler({
        ...     "featured_only": True,
        ...     "include_description": True,
        ...     "include_relationships": True
        ... })
        >>> result = handler.collect(context)
        >>> # {
        >>> #   "characters": [...],
        >>> #   "character_count": 3,
        >>> #   "roles": {"protagonist": 1, "supporting": 2}
        >>> # }
    """
    
    handler_name = "character_data"
    handler_version = "1.0.0"
    description = "Collects character information for AI context"
    
    def validate_config(self) -> None:
        """Validate configuration using Pydantic."""
        try:
            CharacterDataConfig(**self.config)
        except Exception as e:
            raise InputHandlerException(
                message="Invalid configuration for CharacterDataHandler",
                handler_name=self.handler_name,
                context={"config": self.config, "error": str(e)}
            )
    
    @with_logging
    @with_performance_monitoring
    def collect(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect character information.
        
        Args:
            context: Runtime context with project
            
        Returns:
            Dictionary with character data
        """
        project = context.get("project")
        if not project:
            raise ValueError("Context missing 'project'")
        
        # Get configuration
        featured_only = self.config.get("featured_only", False)
        include_description = self.config.get("include_description", True)
        include_backstory = self.config.get("include_backstory", False)
        include_relationships = self.config.get("include_relationships", False)
        include_arc = self.config.get("include_arc", False)
        character_ids = self.config.get("character_ids")
        limit = self.config.get("limit")
        role_filter = self.config.get("role_filter")
        
        # Query characters
        characters_qs = project.characters.all()
        
        if featured_only:
            characters_qs = characters_qs.filter(is_featured=True)
        
        if character_ids:
            characters_qs = characters_qs.filter(id__in=character_ids)
        
        if role_filter:
            characters_qs = characters_qs.filter(role=role_filter)
        
        characters_qs = characters_qs.order_by("-is_featured", "name")
        
        if limit:
            characters_qs = characters_qs[:limit]
        
        # Collect character data
        result = {
            "characters": [],
            "character_count": 0,
            "roles": {}
        }
        
        for character in characters_qs:
            character_data = {
                "id": character.id,
                "name": character.name,
                "role": character.role or "supporting",
                "is_featured": character.is_featured
            }
            
            # Optional fields
            if include_description and character.description:
                character_data["description"] = character.description
            
            if include_backstory and character.backstory:
                character_data["backstory"] = character.backstory
            
            if include_arc and character.character_arc:
                character_data["arc"] = character.character_arc
            
            if include_relationships:
                # Get relationships (if model has them)
                relationships = []
                # Note: Adjust based on actual relationship model structure
                if hasattr(character, 'relationships'):
                    for rel in character.relationships.all():
                        relationships.append({
                            "type": rel.relationship_type,
                            "character": rel.target_character.name
                        })
                character_data["relationships"] = relationships
            
            result["characters"].append(character_data)
            
            # Count by role
            role = character_data["role"]
            result["roles"][role] = result["roles"].get(role, 0) + 1
        
        result["character_count"] = len(result["characters"])
        
        return result
