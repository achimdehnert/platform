"""
World Data Input Handler - World-building Information Collector
"""

from typing import Dict, Any
import structlog

from ..base.input import BaseInputHandler
from ..exceptions import InputHandlerException
from ..decorators import with_logging, with_performance_monitoring
from ..schemas import WorldDataConfig

logger = structlog.get_logger()


class WorldDataHandler(BaseInputHandler):
    """
    Collects world-building information from various sources.
    
    Gathers locations, cultures, magic systems, history, and world rules
    to provide context for story generation.
    
    Configuration (WorldDataConfig):
        include_locations (bool): Include location data. Default: True
        include_cultures (bool): Include cultural information. Default: False
        include_magic_systems (bool): Include magic/power systems. Default: False
        include_history (bool): Include world history. Default: False
        include_rules (bool): Include world rules/physics. Default: False
        location_ids (list): Specific location IDs to include
        limit (int): Maximum items per category (1-50)
    
    Example:
        >>> handler = WorldDataHandler({
        ...     "include_locations": True,
        ...     "include_cultures": True,
        ...     "include_magic_systems": True,
        ...     "limit": 10
        ... })
        >>> result = handler.collect({"project": project})
        >>> print(result["location_count"])
    """
    
    handler_name = "world_data"
    handler_version = "2.0.0"
    description = "Collects world-building information for context"
    
    cache_enabled = True
    cache_ttl = 600  # 10 minutes
    
    def validate_config(self) -> None:
        """Validate configuration using Pydantic"""
        try:
            self.validated_config = WorldDataConfig(**self.config)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {e}")
    
    @with_logging
    @with_performance_monitoring
    def collect(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect world-building data.
        
        Args:
            context: Must contain 'project'
            
        Returns:
            Dict with locations, cultures, magic_systems, history, rules
        """
        self._validate_context(context, ["project"])
        
        project = context["project"]
        
        self.logger.info(
            "collecting_world_data",
            project_id=project.id,
            config=self.config
        )
        
        result = {
            "locations": [],
            "location_count": 0,
            "cultures": [],
            "culture_count": 0,
            "magic_systems": [],
            "magic_system_count": 0,
            "world_history": "",
            "world_rules": "",
            "has_world_data": False
        }
        
        try:
            # Collect locations
            if self.validated_config.include_locations:
                locations_data = self._collect_locations(project)
                result["locations"] = locations_data
                result["location_count"] = len(locations_data)
            
            # Collect cultures
            if self.validated_config.include_cultures:
                cultures_data = self._collect_cultures(project)
                result["cultures"] = cultures_data
                result["culture_count"] = len(cultures_data)
            
            # Collect magic systems
            if self.validated_config.include_magic_systems:
                magic_data = self._collect_magic_systems(project)
                result["magic_systems"] = magic_data
                result["magic_system_count"] = len(magic_data)
            
            # Collect history
            if self.validated_config.include_history:
                result["world_history"] = self._collect_history(project)
            
            # Collect world rules
            if self.validated_config.include_rules:
                result["world_rules"] = self._collect_rules(project)
            
            # Check if any world data exists
            result["has_world_data"] = any([
                result["location_count"] > 0,
                result["culture_count"] > 0,
                result["magic_system_count"] > 0,
                bool(result["world_history"]),
                bool(result["world_rules"])
            ])
            
            self.logger.info(
                "world_data_collected",
                location_count=result["location_count"],
                culture_count=result["culture_count"],
                has_data=result["has_world_data"]
            )
            
            return result
            
        except Exception as e:
            raise InputHandlerException(
                f"Failed to collect world data: {e}",
                handler_name=self.handler_name,
                context={"project_id": project.id},
                original_error=e
            )
    
    def _collect_locations(self, project) -> list:
        """Collect location data"""
        locations = []
        
        # Check if project has locations model
        if not hasattr(project, 'locations'):
            self.logger.warning("project_has_no_locations_relation")
            return locations
        
        try:
            locations_qs = project.locations.all()
            
            # Filter by specific IDs if provided
            if self.validated_config.location_ids:
                locations_qs = locations_qs.filter(
                    id__in=self.validated_config.location_ids
                )
            
            # Apply limit
            if self.validated_config.limit:
                locations_qs = locations_qs[:self.validated_config.limit]
            
            for location in locations_qs:
                location_data = {
                    "id": location.id,
                    "name": location.name,
                }
                
                # Add optional fields if they exist
                if hasattr(location, 'description'):
                    location_data["description"] = location.description
                
                if hasattr(location, 'location_type'):
                    location_data["type"] = location.location_type
                
                if hasattr(location, 'significance'):
                    location_data["significance"] = location.significance
                
                if hasattr(location, 'parent_location'):
                    parent = location.parent_location
                    if parent:
                        location_data["parent"] = parent.name
                
                locations.append(location_data)
            
        except Exception as e:
            self.logger.error("failed_to_collect_locations", error=str(e))
        
        return locations
    
    def _collect_cultures(self, project) -> list:
        """Collect culture/faction data"""
        cultures = []
        
        # Check for cultures or factions relation
        culture_attr = None
        for attr in ['cultures', 'factions', 'societies']:
            if hasattr(project, attr):
                culture_attr = attr
                break
        
        if not culture_attr:
            self.logger.warning("project_has_no_cultures_relation")
            return cultures
        
        try:
            cultures_qs = getattr(project, culture_attr).all()
            
            if self.validated_config.limit:
                cultures_qs = cultures_qs[:self.validated_config.limit]
            
            for culture in cultures_qs:
                culture_data = {
                    "id": culture.id,
                    "name": culture.name,
                }
                
                if hasattr(culture, 'description'):
                    culture_data["description"] = culture.description
                
                if hasattr(culture, 'values'):
                    culture_data["values"] = culture.values
                
                if hasattr(culture, 'traditions'):
                    culture_data["traditions"] = culture.traditions
                
                cultures.append(culture_data)
            
        except Exception as e:
            self.logger.error("failed_to_collect_cultures", error=str(e))
        
        return cultures
    
    def _collect_magic_systems(self, project) -> list:
        """Collect magic/power systems"""
        magic_systems = []
        
        # Check for magic systems relation
        if not hasattr(project, 'magic_systems') and not hasattr(project, 'power_systems'):
            self.logger.warning("project_has_no_magic_systems_relation")
            return magic_systems
        
        try:
            magic_attr = 'magic_systems' if hasattr(project, 'magic_systems') else 'power_systems'
            magic_qs = getattr(project, magic_attr).all()
            
            if self.validated_config.limit:
                magic_qs = magic_qs[:self.validated_config.limit]
            
            for magic in magic_qs:
                magic_data = {
                    "id": magic.id,
                    "name": magic.name,
                }
                
                if hasattr(magic, 'description'):
                    magic_data["description"] = magic.description
                
                if hasattr(magic, 'rules'):
                    magic_data["rules"] = magic.rules
                
                if hasattr(magic, 'limitations'):
                    magic_data["limitations"] = magic.limitations
                
                if hasattr(magic, 'source'):
                    magic_data["source"] = magic.source
                
                magic_systems.append(magic_data)
            
        except Exception as e:
            self.logger.error("failed_to_collect_magic_systems", error=str(e))
        
        return magic_systems
    
    def _collect_history(self, project) -> str:
        """Collect world history"""
        history = ""
        
        # Check various field names
        for field_name in ['world_history', 'history', 'background', 'timeline']:
            if hasattr(project, field_name):
                history = getattr(project, field_name, "")
                if history:
                    break
        
        return history or ""
    
    def _collect_rules(self, project) -> str:
        """Collect world rules/physics"""
        rules = ""
        
        # Check various field names
        for field_name in ['world_rules', 'rules', 'physics', 'laws']:
            if hasattr(project, field_name):
                rules = getattr(project, field_name, "")
                if rules:
                    break
        
        return rules or ""