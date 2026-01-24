"""
Prompt Template Service
Loads and renders prompt templates from database
"""
import logging
from typing import Any, Dict, Optional
from apps.bfagent.models import PromptTemplate, PromptExecution

logger = logging.getLogger(__name__)


class PromptTemplateService:
    """Service for loading and rendering prompt templates"""
    
    def get_template(
        self,
        template_key: str,
        version: Optional[str] = None
    ) -> Optional[PromptTemplate]:
        """
        Get prompt template by key
        
        Args:
            template_key: Unique template key
            version: Optional specific version
            
        Returns:
            PromptTemplate or None
        """
        try:
            query = PromptTemplate.objects.filter(
                template_key=template_key,
                is_active=True
            )
            
            if version:
                query = query.filter(version=version)
            
            # Get default template if multiple exist
            template = query.filter(is_default=True).first()
            if not template:
                template = query.first()
            
            if template:
                logger.info(f"Loaded template: {template_key}")
                return template
            else:
                logger.warning(f"Template not found: {template_key}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading template {template_key}: {e}")
            return None
    
    def render_template(
        self,
        template_key: str,
        variables: Dict[str, Any],
        version: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        """
        Render prompt template with variables
        
        Args:
            template_key: Unique template key
            variables: Variables to render in template
            version: Optional specific version
            
        Returns:
            Dict with 'system_prompt' and 'user_prompt' or None
        """
        template = self.get_template(template_key, version)
        if not template:
            return None
        
        try:
            # Apply defaults for optional variables
            render_vars = template.variable_defaults.copy() if template.variable_defaults else {}
            render_vars.update(variables)
            
            # Simple template rendering ({{variable}})
            system_prompt = self._render_string(template.system_prompt, render_vars)
            user_prompt = self._render_string(template.user_prompt_template, render_vars)
            
            # Increment usage count
            template.usage_count += 1
            template.save(update_fields=['usage_count'])
            
            logger.info(f"Rendered template: {template_key}")
            
            return {
                'system_prompt': system_prompt,
                'user_prompt': user_prompt,
                'template': template,
            }
            
        except Exception as e:
            logger.error(f"Error rendering template {template_key}: {e}")
            return None
    
    def _render_string(self, template_str: str, variables: Dict[str, Any]) -> str:
        """Simple template variable replacement"""
        result = template_str
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))
        return result
    
    def record_execution(
        self,
        template: PromptTemplate,
        success: bool,
        tokens_used: int = 0,
        execution_time: float = 0.0,
        confidence: float = 0.0,
        cost: float = 0.0,
        output_preview: str = '',
        error_message: str = ''
    ) -> PromptExecution:
        """
        Record prompt execution for tracking and optimization
        
        Args:
            template: The template that was executed
            success: Whether execution was successful
            tokens_used: Number of tokens used
            execution_time: Execution time in seconds
            confidence: Confidence score (0.0-1.0)
            cost: Cost in dollars
            output_preview: First 500 chars of output
            error_message: Error message if failed
            
        Returns:
            PromptExecution record
        """
        execution = PromptExecution.objects.create(
            template=template,
            status='success' if success else 'error',
            tokens_used=tokens_used,
            execution_time=execution_time,
            confidence_score=confidence,
            cost=cost,
            output_preview=output_preview[:500] if output_preview else '',
            error_message=error_message[:1000] if error_message else '',
        )
        
        # Update template statistics
        if success:
            template.success_count += 1
        else:
            template.failure_count += 1
        
        # Update averages
        total_executions = template.success_count + template.failure_count
        if total_executions > 0:
            template.avg_tokens_used = (
                (template.avg_tokens_used * (total_executions - 1) + tokens_used) 
                / total_executions
            )
            template.avg_execution_time = (
                (template.avg_execution_time * (total_executions - 1) + execution_time)
                / total_executions
            )
            template.avg_confidence = (
                (template.avg_confidence * (total_executions - 1) + confidence)
                / total_executions
            )
            template.avg_cost = (
                (float(template.avg_cost) * (total_executions - 1) + cost)
                / total_executions
            )
        
        template.save()
        
        logger.info(
            f"Recorded execution for {template.template_key}: "
            f"{'success' if success else 'error'}"
        )
        
        return execution
