"""
Handler Loader - Loads handlers from Database

This module provides functions to dynamically load handler classes
from the database Handler model.
"""

import importlib
from typing import Any, Optional
from apps.bfagent.models_handlers import Handler
import logging

logger = logging.getLogger(__name__)


def get_handler_from_db(handler_id: str) -> Optional[Any]:
    """
    Load a handler instance from database.
    
    Args:
        handler_id: Handler identifier (e.g., 'bookwriting.project.enrich')
    
    Returns:
        Handler instance or None if not found
    
    Example:
        handler = get_handler_from_db('bookwriting.project.enrich')
        result = handler.execute(context)
    """
    try:
        # Get handler from DB
        handler_record = Handler.objects.get(
            handler_id=handler_id,
            is_active=True
        )
        
        # Dynamically import the module
        module = importlib.import_module(handler_record.module_path)
        
        # Get the class
        handler_class = getattr(module, handler_record.class_name)
        
        # Instantiate and return
        return handler_class()
        
    except Handler.DoesNotExist:
        logger.error(f"Handler not found: {handler_id}")
        return None
    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to load handler {handler_id}: {e}")
        return None


def execute_handler(handler_id: str, context: dict) -> dict:
    """
    Execute a handler by ID.
    
    Args:
        handler_id: Handler identifier
        context: Execution context
    
    Returns:
        Execution result dict
    
    Example:
        result = execute_handler(
            'bookwriting.project.enrich',
            {'project': project, 'agent': agent, 'action': 'premise'}
        )
    """
    handler = get_handler_from_db(handler_id)
    
    if not handler:
        return {
            'success': False,
            'error': f'Handler not found: {handler_id}',
            'result': None
        }
    
    try:
        # Validate input if handler has validation method
        if hasattr(handler, 'validate_input'):
            is_valid, error = handler.validate_input(context)
            if not is_valid:
                return {
                    'success': False,
                    'error': f'Validation failed: {error}',
                    'result': None
                }
        
        # Execute handler
        result = handler.execute(context)
        return result
        
    except Exception as e:
        logger.exception(f"Handler execution failed: {handler_id}")
        return {
            'success': False,
            'error': str(e),
            'result': None
        }


def list_handlers(category: Optional[str] = None, domain: Optional[str] = None) -> list:
    """
    List available handlers from database.
    
    Args:
        category: Filter by category (input, processing, output)
        domain: Filter by domain prefix (e.g., 'bookwriting')
    
    Returns:
        List of handler dicts
    """
    queryset = Handler.objects.filter(is_active=True)
    
    if category:
        queryset = queryset.filter(category=category)
    
    if domain:
        queryset = queryset.filter(handler_id__startswith=f'{domain}.')
    
    return list(queryset.values(
        'handler_id',
        'display_name',
        'description',
        'category',
        'version',
        'avg_execution_time_ms',
        'success_rate'
    ))


def get_handler_info(handler_id: str) -> Optional[dict]:
    """
    Get handler metadata from database.
    
    Args:
        handler_id: Handler identifier
    
    Returns:
        Handler metadata dict or None
    """
    try:
        handler = Handler.objects.get(handler_id=handler_id)
        return {
            'handler_id': handler.handler_id,
            'display_name': handler.display_name,
            'description': handler.description,
            'category': handler.category,
            'version': handler.version,
            'module_path': handler.module_path,
            'class_name': handler.class_name,
            'config_schema': handler.config_schema,
            'input_schema': handler.input_schema,
            'output_schema': handler.output_schema,
            'is_active': handler.is_active,
            'requires_llm': handler.requires_llm,
            'is_experimental': handler.is_experimental,
            'avg_execution_time_ms': handler.avg_execution_time_ms,
            'success_rate': handler.success_rate,
            'total_executions': handler.total_executions,
        }
    except Handler.DoesNotExist:
        return None
