"""
Workflow Builder API Views

REST API for visual workflow builder integration
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.http import JsonResponse

from apps.bfagent.services.workflow_templates import WORKFLOWS, WorkflowTemplate
from apps.bfagent.services.workflow_templates_v2 import (
    EnhancedWorkflowRegistry,
    WORKFLOWS_V2
)
from apps.bfagent.services.llm_client import execute_workflow
from apps.bfagent.services.handlers.registries import (
    InputHandlerRegistry,
    ProcessingHandlerRegistry,
    OutputHandlerRegistry
)


# ============================================================================
# HANDLER CATALOG API
# ============================================================================

@api_view(['GET'])
def list_handlers(request):
    """
    Get catalog of all available handlers from DATABASE (V3)
    
    Returns:
        {
            "handlers": [...],  # All handlers with real metrics
            "count": 11,
            "categories": {...}
        }
    """
    from apps.bfagent.models_handlers import Handler
    
    # Get all active handlers
    handlers = Handler.objects.filter(is_active=True).order_by('category', 'handler_id')
    
    # Build response
    handler_list = []
    for handler in handlers:
        handler_list.append({
            'handler_id': handler.handler_id,
            'display_name': handler.display_name,
            'description': handler.description,
            'category': handler.category,
            'version': handler.version,
            'requires_llm': handler.requires_llm,
            'is_experimental': handler.is_experimental,
            'is_deprecated': handler.is_deprecated,
            # Real metrics from DB
            'total_executions': handler.total_executions,
            'success_rate': handler.success_rate,
            'avg_execution_time_ms': handler.avg_execution_time_ms,
            # Usage info
            'used_in_workflows': handler.used_in_actions.count(),
            'config_schema': handler.config_schema,
        })
    
    # Category breakdown
    categories = {
        'input': handlers.filter(category='input').count(),
        'processing': handlers.filter(category='processing').count(),
        'output': handlers.filter(category='output').count(),
    }
    
    return JsonResponse({
        'handlers': handler_list,
        'count': len(handler_list),
        'categories': categories
    })


@api_view(['GET'])
def handler_detail(request, handler_id):
    """
    Get detailed handler information from DATABASE (V3)
    
    Args:
        handler_id: Handler identifier
        
    Returns:
        Complete handler details with real metrics and usage
    """
    from apps.bfagent.models_handlers import Handler, ActionHandler
    
    try:
        handler = Handler.objects.get(handler_id=handler_id)
    except Handler.DoesNotExist:
        return JsonResponse(
            {'error': f'Handler "{handler_id}" not found'},
            status=404
        )
    
    # Get actions using this handler
    action_handlers = ActionHandler.objects.filter(
        handler=handler
    ).select_related('action', 'action__agent')
    
    used_in_templates = []
    for ah in action_handlers:
        used_in_templates.append({
            'action_id': ah.action.id,
            'action_name': ah.action.display_name,
            'agent_name': ah.action.agent.name,
            'phase': ah.phase,
            'order': ah.order,
            'is_active': ah.is_active
        })
    
    return JsonResponse({
        'handler_id': handler.handler_id,
        'display_name': handler.display_name,
        'description': handler.description,
        'category': handler.category,
        'version': handler.version,
        'is_deprecated': handler.is_deprecated,
        'deprecation_reason': handler.deprecation_reason,
        'replacement_handler': handler.replacement_handler.handler_id if handler.replacement_handler else None,
        # Technical details
        'module_path': handler.module_path,
        'class_name': handler.class_name,
        'config_schema': handler.config_schema,
        'input_schema': handler.input_schema,
        'output_schema': handler.output_schema,
        'example_config': handler.example_config,
        # Metadata
        'requires_llm': handler.requires_llm,
        'is_experimental': handler.is_experimental,
        'documentation_url': handler.documentation_url,
        # Real metrics
        'total_executions': handler.total_executions,
        'success_rate': round(handler.success_rate, 2),
        'avg_execution_time_ms': handler.avg_execution_time_ms,
        # Usage
        'used_in_templates': used_in_templates,
        'used_in_count': len(used_in_templates),
        # Dependencies
        'required_handlers': [h.handler_id for h in handler.required_handlers.all()],
        'dependent_handlers': [h.handler_id for h in handler.dependent_handlers.all()],
        # Input/Output types
        'input_type': 'context (Dict)',
        'output_type': 'Dict'
    })


# ============================================================================
# WORKFLOW TEMPLATE API
# ============================================================================

@api_view(['GET'])
def list_workflow_templates(request):
    """
    Get all available workflow templates (Domain-Aware V2).
    
    Query Params:
        domain: Filter by domain ID (optional)
    
    Returns:
        List of workflow templates with domain metadata
    """
    domain_filter = request.GET.get('domain')
    templates = []
    
    # Use V2 templates (domain-aware)
    for template in EnhancedWorkflowRegistry.get_all():
        # Get domain-aware format
        domain_aware = template.to_domain_aware_dict()
        
        # Filter by domain if requested
        if domain_filter and domain_aware['domain']['domain_id'] != domain_filter:
            continue
        
        templates.append({
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description,
            "domain": domain_aware['domain'],
            "phase_count": len(domain_aware['phases']),
            "handler_count": sum(
                len(phase['handlers']) 
                for phase in domain_aware['phases']
            ),
            "required_variables": template.required_variables
        })
    
    return JsonResponse({
        "count": len(templates),
        "templates": templates
    })


@api_view(['GET'])
def workflow_template_detail(request, template_id):
    """
    Get detailed workflow template configuration (Domain-Aware V2).
    
    Args:
        template_id: Workflow template ID
        
    Returns:
        Complete workflow configuration with domain metadata and phases
    """
    # Try V2 first (domain-aware)
    template = EnhancedWorkflowRegistry.get(template_id)
    
    if not template:
        return JsonResponse(
            {"error": f"Workflow template '{template_id}' not found"},
            status=404
        )
    
    # Return domain-aware format
    domain_aware = template.to_domain_aware_dict()
    
    return JsonResponse({
        "template_id": template.template_id,
        "name": template.name,
        "description": template.description,
        "domain": domain_aware['domain'],
        "phases": domain_aware['phases'],
        "variables": {
            "required": template.required_variables,
            "optional": getattr(template, 'optional_variables', [])
        },
        # Backward compatibility: also include pipeline format
        "pipeline": template.to_pipeline_config()
    })


@api_view(['GET'])
def list_domains(request):
    """
    Get all available domains with template counts (NEW V2 Endpoint).
    
    Returns:
        List of domains with metadata and template counts
    """
    domains = EnhancedWorkflowRegistry.get_domains()
    
    return JsonResponse({
        "count": len(domains),
        "domains": list(domains.values())
    })


@api_view(['GET'])
def list_projects_api(request):
    """
    Get list of projects for workflow execution dropdowns.
    
    Returns:
        JSON list of projects with id and title
    """
    from apps.bfagent.models import Project
    
    projects = Project.objects.filter(
        user=request.user
    ).values('id', 'title').order_by('-created_at')[:50]
    
    return JsonResponse({
        "count": len(projects),
        "projects": list(projects)
    })


@api_view(['POST'])
def execute_workflow_api(request):
    """
    Execute a workflow template.
    
    Request Body:
        {
            "workflow_id": "chapter_gen",
            "variables": {...},
            "context": {...}
        }
        
    Returns:
        Workflow execution results
    """
    workflow_id = request.data.get('workflow_id')
    variables = request.data.get('variables', {})
    context = request.data.get('context', {})
    
    if not workflow_id:
        return JsonResponse(
            {"error": "Missing 'workflow_id'"},
            status=400
        )
    
    # Execute workflow
    result = execute_workflow(
        workflow_id=workflow_id,
        variables=variables,
        context=context
    )
    
    if result["ok"]:
        return JsonResponse({
            "success": True,
            "workflow_id": result["workflow_id"],
            "result": result["result"]
        })
    else:
        return JsonResponse(
            {"error": result.get("error")},
            status=500
        )


@api_view(['POST'])
def save_custom_workflow(request):
    """
    Save a custom workflow created in visual editor.
    
    Request Body:
        {
            "name": "My Custom Workflow",
            "description": "...",
            "react_flow_data": {...},
            "pipeline_config": {...}
        }
        
    Returns:
        Saved workflow with generated ID
    """
    # TODO: Save to database (WorkflowDefinition model)
    # For now, just validate and return
    
    name = request.data.get('name')
    description = request.data.get('description')
    react_flow_data = request.data.get('react_flow_data')
    pipeline_config = request.data.get('pipeline_config')
    
    if not all([name, pipeline_config]):
        return JsonResponse(
            {"error": "Missing required fields: name, pipeline_config"},
            status=400
        )
    
    # Generate ID from name
    workflow_id = name.lower().replace(' ', '_')
    
    return JsonResponse({
        "success": True,
        "workflow_id": workflow_id,
        "message": "Workflow saved successfully"
    }, status=201)


# ============================================================================
# REACT FLOW CONVERTER
# ============================================================================

@api_view(['POST'])
def convert_react_flow_to_pipeline(request):
    """
    Convert React Flow JSON to PipelineOrchestrator config.
    
    Request Body:
        {
            "nodes": [...],
            "edges": [...]
        }
        
    Returns:
        {
            "input": [...],
            "processing": [...],
            "output": {...}
        }
    """
    nodes = request.data.get('nodes', [])
    edges = request.data.get('edges', [])
    
    # Group nodes by type/phase
    input_handlers = []
    processing_handlers = []
    output_handlers = []
    
    for node in nodes:
        node_data = node.get('data', {})
        node_type = node.get('type', '')
        
        handler_config = {
            "handler": node_data.get('handler_id'),
            "config": node_data.get('config', {})
        }
        
        if node_type == 'input' or 'Input' in node_data.get('label', ''):
            input_handlers.append(handler_config)
        elif node_type == 'output' or 'Output' in node_data.get('label', ''):
            output_handlers.append(handler_config)
        else:
            processing_handlers.append(handler_config)
    
    return JsonResponse({
        "pipeline": {
            "input": input_handlers,
            "processing": processing_handlers,
            "output": output_handlers[0] if output_handlers else {}
        }
    })


@api_view(['POST'])
def convert_pipeline_to_react_flow(request):
    """
    Convert PipelineOrchestrator config to React Flow JSON.
    
    Request Body:
        {
            "input": [...],
            "processing": [...],
            "output": {...}
        }
        
    Returns:
        {
            "nodes": [...],
            "edges": [...]
        }
    """
    pipeline = request.data
    
    nodes = []
    edges = []
    node_id_counter = 1
    
    # Convert input handlers
    prev_node_id = None
    for handler_config in pipeline.get('input', []):
        node_id = f"node-{node_id_counter}"
        nodes.append({
            "id": node_id,
            "type": "input",
            "position": {"x": 100, "y": node_id_counter * 100},
            "data": {
                "label": handler_config.get('handler', 'Unknown'),
                "handler_id": handler_config.get('handler'),
                "config": handler_config.get('config', {})
            }
        })
        
        if prev_node_id:
            edges.append({
                "id": f"edge-{prev_node_id}-{node_id}",
                "source": prev_node_id,
                "target": node_id
            })
        
        prev_node_id = node_id
        node_id_counter += 1
    
    # Convert processing handlers
    for handler_config in pipeline.get('processing', []):
        node_id = f"node-{node_id_counter}"
        nodes.append({
            "id": node_id,
            "type": "processing",
            "position": {"x": 400, "y": node_id_counter * 100},
            "data": {
                "label": handler_config.get('handler', 'Unknown'),
                "handler_id": handler_config.get('handler'),
                "config": handler_config.get('config', {})
            }
        })
        
        if prev_node_id:
            edges.append({
                "id": f"edge-{prev_node_id}-{node_id}",
                "source": prev_node_id,
                "target": node_id
            })
        
        prev_node_id = node_id
        node_id_counter += 1
    
    # Convert output handler
    output_config = pipeline.get('output', {})
    if output_config:
        node_id = f"node-{node_id_counter}"
        nodes.append({
            "id": node_id,
            "type": "output",
            "position": {"x": 700, "y": node_id_counter * 100},
            "data": {
                "label": output_config.get('handler', 'Unknown'),
                "handler_id": output_config.get('handler'),
                "config": output_config.get('config', {})
            }
        })
        
        if prev_node_id:
            edges.append({
                "id": f"edge-{prev_node_id}-{node_id}",
                "source": prev_node_id,
                "target": node_id
            })
    
    return JsonResponse({
        "nodes": nodes,
        "edges": edges
    })
