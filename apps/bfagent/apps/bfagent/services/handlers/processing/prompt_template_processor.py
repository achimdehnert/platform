"""
Prompt Template Processing Handler

Integrates the Prompt Management System v2.0 with the Handler Pipeline.
Loads templates from database, renders with variables, and passes to LLM Handler.
"""

from typing import Any, Dict
import structlog

from apps.bfagent.models import PromptTemplate, PromptExecution
from ..base.processing import BaseProcessingHandler
from ..exceptions import ProcessingHandlerException
from ..decorators import with_logging, with_performance_monitoring

logger = structlog.get_logger()


class PromptTemplateProcessingHandler(BaseProcessingHandler):
    """
    Processing Handler that loads and renders database-stored prompt templates.
    
    This handler bridges the Prompt Management System v2.0 with the handler pipeline,
    enabling dynamic template selection, versioning, and execution tracking.
    
    Configuration:
        template_key (str, required): Unique template identifier
        version (str, optional): Template version ("latest", "1.0", "2.0-beta")
        variables (dict, optional): Template variables (can also come from input_data)
        track_execution (bool, optional): Enable execution tracking, default True
        use_preferred_llm (bool, optional): Use template's preferred LLM, default True
        
    Input Data:
        Dictionary with template variables that will be merged with config variables
        
    Output:
        {
            "rendered_template": str,          # Rendered prompt text
            "template_used": PromptTemplate,   # Template instance
            "template_key": str,               # Template identifier
            "template_version": str,           # Template version
            "variables_used": dict,            # Final variables after merge
            "execution_id": int (optional)     # Execution tracking ID
        }
        
    Example Config:
        {
            "template_key": "character_generation",
            "version": "1.0",
            "variables": {
                "genre": "Fantasy"  # Static variable
            },
            "track_execution": True
        }
        
    Example Usage in Pipeline:
        pipeline = [
            {
                "handler": "prompt_template_processor",
                "config": {
                    "template_key": "character_generation",
                    "version": "latest"
                }
            },
            {
                "handler": "llm_processor",
                "config": {
                    "temperature": 0.8,
                    "max_tokens": 2000
                }
            }
        ]
    """
    
    handler_type = "processing"
    handler_name = "prompt_template_processor"
    handler_version = "1.0.0"
    description = "Loads and renders database-stored prompt templates"
    
    def validate_config(self) -> None:
        """Validate configuration"""
        if "template_key" not in self.config:
            raise ProcessingHandlerException(
                message="Missing required 'template_key' in configuration",
                handler_name=self.handler_name,
                context={"config": self.config}
            )
        
        template_key = self.config["template_key"]
        if not isinstance(template_key, str) or not template_key.strip():
            raise ProcessingHandlerException(
                message="'template_key' must be a non-empty string",
                handler_name=self.handler_name,
                context={"template_key": template_key}
            )
    
    def _get_template(self) -> PromptTemplate:
        """
        Load template from database based on configuration
        
        Returns:
            PromptTemplate instance
            
        Raises:
            ValueError: If template not found
        """
        template_key = self.config["template_key"]
        version = self.config.get("version", "latest")
        
        try:
            if version == "latest":
                template = PromptTemplate.objects.filter(
                    template_key=template_key,
                    is_active=True
                ).order_by('-version').first()
            else:
                template = PromptTemplate.objects.filter(
                    template_key=template_key,
                    version=version
                ).first()
            
            if not template:
                raise ValueError(
                    f"Template not found: key='{template_key}', version='{version}'"
                )
            
            return template
            
        except Exception as e:
            raise ProcessingHandlerException(
                message=f"Failed to load template: {str(e)}",
                handler_name=self.handler_name,
                context={
                    "template_key": template_key,
                    "version": version
                }
            )
    
    def _merge_variables(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge variables from config, input_data, and context
        
        Priority (highest to lowest):
        1. input_data (runtime variables)
        2. config.variables (static variables)
        3. context (execution context)
        
        Args:
            input_data: Runtime input data
            context: Execution context
            
        Returns:
            Merged variables dictionary
        """
        merged = {}
        
        # Start with config variables
        if "variables" in self.config:
            merged.update(self.config["variables"])
        
        # Add input data (overrides config)
        if isinstance(input_data, dict):
            merged.update(input_data)
        
        # Add relevant context items (doesn't override)
        for key in ["project_id", "agent_id", "user_id"]:
            if key in context and key not in merged:
                merged[key] = context[key]
        
        return merged
    
    @with_logging
    @with_performance_monitoring
    def process(
        self,
        input_data: Any,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process template loading and rendering
        
        Args:
            input_data: Input data with variables
            context: Execution context
            
        Returns:
            dict: Rendered template and metadata
        """
        # Load template
        template = self._get_template()
        
        # Merge variables
        variables = self._merge_variables(input_data, context)
        
        # Render template
        try:
            rendered = template.render(variables)
        except ValueError as e:
            raise ProcessingHandlerException(
                message=f"Template rendering failed: {str(e)}",
                handler_name=self.handler_name,
                context={
                    "template_key": template.template_key,
                    "template_version": template.version,
                    "variables": variables,
                    "missing_variables": str(e)
                }
            )
        
        # Build result
        result = {
            "rendered_template": rendered,
            "template_used": template,
            "template_key": template.template_key,
            "template_version": template.version,
            "variables_used": variables
        }
        
        # Track execution if enabled
        if self.config.get("track_execution", True):
            try:
                execution = PromptExecution.objects.create(
                    template=template,
                    agent_id=context.get("agent_id"),
                    project_id=context.get("project_id"),
                    target_model=context.get("target_model", ""),
                    target_id=context.get("target_id", 0),
                    rendered_prompt=rendered,
                    context_used=variables,
                    llm_response="",  # Will be filled by LLM handler
                    status="pending"
                )
                result["execution_id"] = execution.id
                
                logger.info(
                    "prompt_template_execution_tracked",
                    execution_id=execution.id,
                    template_key=template.template_key,
                    template_version=template.version
                )
            except Exception as e:
                logger.warning(
                    "failed_to_track_execution",
                    error=str(e),
                    template_key=template.template_key
                )
        
        # Update template usage stats
        template.usage_count += 1
        template.save(update_fields=['usage_count'])
        
        # Pass preferred LLM to context if configured
        if self.config.get("use_preferred_llm", True) and template.preferred_llm:
            result["preferred_llm_id"] = template.preferred_llm.id
            result["preferred_llm"] = template.preferred_llm
        
        return result
