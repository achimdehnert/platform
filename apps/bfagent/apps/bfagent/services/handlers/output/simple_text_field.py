"""
Simple Text Field Output Handler

Updates a single text field in a model.
"""

from typing import Any, Dict, List
from django.apps import apps
from django.utils import timezone
import structlog

from ..base.output import BaseOutputHandler
from ..exceptions import OutputHandlerException
from ..decorators import with_logging, with_performance_monitoring
from ..schemas import SimpleTextFieldConfig

logger = structlog.get_logger()


class SimpleTextFieldHandler(BaseOutputHandler):
    """
    Updates a single text field in a model.
    
    Useful for actions that produce single text outputs like
    synopsis generation, outline creation, etc.
    
    Configuration:
        {
            "target_model": "BookProjects",
            "target_field": "synopsis",
            "target_instance": "current",  # or specific ID
            "action_name": "generate_synopsis"
        }
    
    Example:
        >>> handler = SimpleTextFieldHandler({
        ...     "target_model": "BookProjects",
        ...     "target_field": "synopsis",
        ...     "target_instance": "current"
        ... })
        >>> parsed = handler.parse("Generated synopsis text...")
        >>> # Creates EnrichmentResponse for approval
    """
    
    handler_name = "simple_text_field"
    handler_version = "1.0.0"
    description = "Updates a single text field in a model"
    supports_multiple_objects = False
    supports_rollback = True
    
    def validate_config(self) -> None:
        """Validate configuration using Pydantic."""
        try:
            SimpleTextFieldConfig(**self.config)
        except Exception as e:
            raise OutputHandlerException(
                message="Invalid configuration for SimpleTextFieldHandler",
                handler_name=self.handler_name,
                context={"config": self.config, "error": str(e)}
            )
    
    @with_logging
    @with_performance_monitoring
    def parse(self, processed_data: Any) -> List[Dict[str, Any]]:
        """
        Parse text data into structured format.
        
        Args:
            processed_data: Text string or dict with text
            
        Returns:
            List with single dict containing the text
        """
        if isinstance(processed_data, str):
            # Simple text string
            text = processed_data
        elif isinstance(processed_data, dict):
            # Dict with field name
            field_name = self.config["target_field"]
            text = processed_data.get(field_name, processed_data.get("text", ""))
        else:
            raise ValueError(f"Cannot parse data of type {type(processed_data)}")
        
        return [{
            self.config["target_field"]: text
        }]
    
    def validate(self, parsed_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate parsed data."""
        errors = []
        warnings = []
        
        if len(parsed_data) != 1:
            errors.append(f"Expected 1 item, got {len(parsed_data)}")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        data = parsed_data[0]
        field_name = self.config["target_field"]
        value = data.get(field_name, "")
        
        # Length validation
        min_length = self.config.get("min_length", 0)
        max_length = self.config.get("max_length", 100000)
        
        if len(value) < min_length:
            errors.append(f"Text too short: {len(value)} < {min_length} characters")
        
        if len(value) > max_length:
            warnings.append(f"Text very long: {len(value)} > {max_length} characters")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "length": len(value)
        }
    
    def create_enrichment_responses(
        self,
        parsed_data: List[Dict[str, Any]],
        project: Any,
        agent: Any
    ) -> List[Any]:
        """Create EnrichmentResponse for approval."""
        from ....models import EnrichmentResponse
        
        data = parsed_data[0]
        field_name = self.config["target_field"]
        
        response = EnrichmentResponse.objects.create(
            project=project,
            agent=agent,
            action_name=self.config.get("action_name", "text_generation"),
            response_data=data,
            field_mappings={
                field_name: f"{self.config['target_model']}.{field_name}"
            },
            status="pending",
            metadata={
                "handler": self.handler_name,
                "handler_version": self.handler_version,
                "target_model": self.config["target_model"],
                "target_field": field_name
            }
        )
        
        return [response]
    
    def apply(self, enrichment_response: Any) -> Any:
        """
        Apply the text to the target field.
        
        Args:
            enrichment_response: EnrichmentResponse to apply
            
        Returns:
            Updated model instance
        """
        # Get model and field info
        target_model = enrichment_response.metadata["target_model"]
        target_field = enrichment_response.metadata["target_field"]
        
        # Get model class
        Model = apps.get_model("bfagent", target_model)
        
        # Get instance
        if self.config.get("target_instance") == "current":
            # Update the project itself
            obj = enrichment_response.project
        else:
            # Get specific instance by ID
            instance_id = self.config.get("target_instance_id")
            obj = Model.objects.get(pk=instance_id)
        
        # Get new value
        value = enrichment_response.response_data[target_field]
        
        # Store old value for rollback
        old_value = getattr(obj, target_field, "")
        
        # Update field
        setattr(obj, target_field, value)
        obj.save()
        
        # Update response status
        enrichment_response.status = "applied"
        enrichment_response.applied_at = timezone.now()
        enrichment_response.metadata["old_value"] = old_value
        enrichment_response.metadata["applied_to"] = f"{target_model}#{obj.pk}.{target_field}"
        enrichment_response.save()
        
        return obj
    
    def _generate_summary(self, enrichment_response: Any) -> str:
        """Generate summary."""
        field_name = enrichment_response.metadata["target_field"]
        value = enrichment_response.response_data.get(field_name, "")
        preview = value[:50] + "..." if len(value) > 50 else value
        return f"Update {field_name}: {preview}"
    
    def rollback(self, enrichment_response: Any) -> None:
        """Rollback changes."""
        if "old_value" not in enrichment_response.metadata:
            raise ValueError("Cannot rollback: old_value not stored")
        
        # Get model and field
        target_model = enrichment_response.metadata["target_model"]
        target_field = enrichment_response.metadata["target_field"]
        
        Model = apps.get_model("bfagent", target_model)
        
        # Get instance
        if self.config.get("target_instance") == "current":
            obj = enrichment_response.project
        else:
            instance_id = self.config.get("target_instance_id")
            obj = Model.objects.get(pk=instance_id)
        
        # Restore old value
        old_value = enrichment_response.metadata["old_value"]
        setattr(obj, target_field, old_value)
        obj.save()
        
        # Update response
        enrichment_response.status = "rejected"
        enrichment_response.save()
