"""
Project Fields Input Handler

Collects specified fields from BookProjects model.
"""

from typing import Any, Dict
import structlog

from ..base.input import BaseInputHandler
from ..exceptions import InputHandlerException
from ..decorators import with_logging, with_performance_monitoring
from ..schemas import ProjectFieldsConfig

logger = structlog.get_logger()


class ProjectFieldsInputHandler(BaseInputHandler):
    """
    Collects fields from the current BookProjects instance.
    
    Configuration:
        {
            "fields": ["title", "genre", "synopsis", "themes", ...],
            "mode": "specified"  # or "all" for all filled fields
        }
    
    Example:
        >>> handler = ProjectFieldsInputHandler({"fields": ["title", "genre"]})
        >>> data = handler.collect({"project": project})
        >>> # Returns: {"title": "My Novel", "genre": "Fantasy"}
        
        >>> # Auto-collect all filled fields:
        >>> handler = ProjectFieldsInputHandler({"mode": "all"})
        >>> data = handler.collect({"project": project})
        >>> # Returns all non-empty fields
    """
    
    handler_name = "project_fields"
    handler_version = "1.1.0"
    description = "Collects specified fields from current project"
    
    # Field name mapping: user-friendly name → DB field name
    FIELD_MAPPING = {
        "synopsis": "description",
        "themes": "story_themes",
        "audience": "target_audience",
        "time": "setting_time",
        "location": "setting_location",
        "tone": "atmosphere_tone",
        "conflict": "main_conflict",
        "protagonist": "protagonist_concept",
        "antagonist": "antagonist_concept",
        "inspiration": "inspiration_sources",
        "unique": "unique_elements",
    }
    
    def validate_config(self) -> None:
        """Validate configuration using Pydantic."""
        try:
            ProjectFieldsConfig(**self.config)
        except Exception as e:
            raise InputHandlerException(
                message="Invalid configuration for ProjectFieldsInputHandler",
                handler_name=self.handler_name,
                context={"config": self.config, "error": str(e)}
            )
    
    @with_logging
    @with_performance_monitoring
    def collect(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect project fields.
        
        Args:
            context: Must contain 'project' key with BookProjects instance
            
        Returns:
            Dictionary with requested fields
        """
        project = context.get("project")
        
        if project is None:
            raise ValueError("Missing 'project' in context")
        
        mode = self.config.get("mode", "specified")
        collected_data = {}
        
        if mode == "all":
            # Auto-discover all filled fields
            collected_data = self._collect_all_fields(project)
        else:
            # Collect specified fields
            fields = self.config["fields"]
            
            for field_name in fields:
                # Map user-friendly name to DB field name
                db_field_name = self.FIELD_MAPPING.get(field_name, field_name)
                
                # Get field value
                value = getattr(project, db_field_name, None)
                
                # Only include if value exists and is not empty
                if value is not None and value != "":
                    collected_data[field_name] = value
        
        return collected_data
    
    def _collect_all_fields(self, project: Any) -> Dict[str, Any]:
        """
        Collect all non-empty fields from project.
        
        Args:
            project: BookProjects instance
            
        Returns:
            Dictionary with all filled fields
        """
        # List of all text fields in BookProjects
        text_fields = [
            "title",
            "genre",
            "content_rating",
            "description",
            "tagline",
            "story_premise",
            "target_audience",
            "story_themes",
            "setting_time",
            "setting_location",
            "atmosphere_tone",
            "main_conflict",
            "stakes",
            "protagonist_concept",
            "antagonist_concept",
            "inspiration_sources",
            "unique_elements",
            "genre_settings",
        ]
        
        collected_data = {}
        
        for field_name in text_fields:
            value = getattr(project, field_name, None)
            
            # Only include if value exists and is not empty
            if value is not None and value != "":
                collected_data[field_name] = value
        
        return collected_data
    
    def get_schema(self) -> Dict[str, Any]:
        """Return schema of provided data."""
        fields = self.config["fields"]
        
        return {
            "type": "object",
            "source": "BookProjects",
            "fields": {
                field_name: {
                    "type": "string",  # Most project fields are text
                    "source": f"BookProjects.{field_name}",
                    "required": False
                }
                for field_name in fields
            }
        }
