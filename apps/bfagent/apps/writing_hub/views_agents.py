"""
Agent Configuration Views
=========================
Views for managing project agent configurations and pipeline execution.
"""

import json
import logging
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db.models import Sum

from apps.bfagent.models import BookProjects, Llms
from apps.writing_hub.models import (
    AgentRole,
    LlmTier,
    ProjectAgentConfig,
    AgentPipelineTemplate,
    AgentPipelineExecution,
)
from apps.writing_hub.services.agent_pipeline_service import (
    AgentPipelineService,
    AgentPipelineManager,
)

logger = logging.getLogger(__name__)


@login_required
def project_agent_config(request, project_id):
    """Display and manage agent configuration for a project"""
    project = get_object_or_404(BookProjects, id=project_id)
    
    # Get all agent roles
    agent_roles = AgentRole.objects.filter(is_active=True).select_related('parent_role').order_by('sort_order')
    
    # Get project-specific configs
    project_configs = {
        cfg.agent_role_id: cfg
        for cfg in ProjectAgentConfig.objects.filter(project=project).select_related('agent_role', 'llm_override', 'tier_override')
    }
    
    # Enrich agent roles with project config
    for agent in agent_roles:
        cfg = project_configs.get(agent.id)
        agent.config = {
            'tier_override': cfg.tier_override.code if cfg and cfg.tier_override else '',
            'llm_override_id': cfg.llm_override_id if cfg and cfg.llm_override else '',
            'custom_instructions': cfg.custom_instructions if cfg else '',
            'total_calls': cfg.total_calls if cfg else 0,
            'total_cost': cfg.total_cost if cfg else 0,
        }
        agent.is_enabled = cfg.is_enabled if cfg else True
    
    # Get LLM tiers
    llm_tiers = LlmTier.objects.filter(is_active=True).order_by('sort_order')
    
    # Get available LLMs
    available_llms = Llms.objects.filter(is_active=True).order_by('provider', 'name')
    
    # Get pipeline templates
    pipelines = AgentPipelineTemplate.objects.filter(is_active=True).order_by('sort_order')
    
    # Get project stats
    stats = ProjectAgentConfig.objects.filter(project=project).aggregate(
        total_calls=Sum('total_calls'),
        total_tokens=Sum('total_tokens'),
        total_cost=Sum('total_cost'),
    )
    
    # Build agent configs JSON for JS
    agent_configs_json = json.dumps({
        agent.code: agent.config for agent in agent_roles
    })
    
    # Estimate chapter cost based on default pipeline
    estimated_chapter_cost = 0.15  # Placeholder
    
    context = {
        'project': project,
        'agent_roles': agent_roles,
        'llm_tiers': llm_tiers,
        'available_llms': available_llms,
        'pipelines': pipelines,
        'default_pipeline': 'write_chapter',
        'agent_configs_json': agent_configs_json,
        'total_calls': stats['total_calls'] or 0,
        'total_tokens': stats['total_tokens'] or 0,
        'total_cost': stats['total_cost'] or 0,
        'active_agents': sum(1 for a in agent_roles if a.is_enabled),
        'total_agents': agent_roles.count(),
        'estimated_chapter_cost': estimated_chapter_cost,
    }
    
    return render(request, 'writing_hub/project_agent_config.html', context)


@login_required
@require_http_methods(["POST"])
def save_agent_config(request, project_id):
    """Save agent configuration for a project"""
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        data = json.loads(request.body)
        agent_configs = data.get('agent_configs', {})
        default_pipeline = data.get('default_pipeline', 'write_chapter')
        
        for agent_code, config in agent_configs.items():
            try:
                agent_role = AgentRole.objects.get(code=agent_code)
            except AgentRole.DoesNotExist:
                continue
            
            # Get or create project config
            project_config, created = ProjectAgentConfig.objects.get_or_create(
                project=project,
                agent_role=agent_role,
            )
            
            # Update fields
            if 'enabled' in config:
                project_config.is_enabled = config['enabled']
            
            if 'tier' in config:
                if config['tier']:
                    project_config.tier_override = LlmTier.objects.filter(code=config['tier']).first()
                else:
                    project_config.tier_override = None
            
            if 'llm' in config:
                if config['llm']:
                    project_config.llm_override_id = config['llm']
                else:
                    project_config.llm_override = None
            
            if 'instructions' in config:
                project_config.custom_instructions = config['instructions']
            
            project_config.save()
        
        # Save default pipeline to project settings
        if project.genre_settings:
            try:
                settings = json.loads(project.genre_settings)
            except (json.JSONDecodeError, TypeError):
                settings = {}
        else:
            settings = {}
        
        settings['default_pipeline'] = default_pipeline
        project.genre_settings = json.dumps(settings)
        project.save(update_fields=['genre_settings'])
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        logger.exception(f"Error saving agent config: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def reset_agent_config(request, project_id):
    """Reset agent configuration to defaults"""
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        # Delete all project-specific configs
        ProjectAgentConfig.objects.filter(project=project).delete()
        return JsonResponse({'success': True})
    except Exception as e:
        logger.exception(f"Error resetting agent config: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def execute_pipeline(request, project_id):
    """Execute a pipeline for content generation"""
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        data = json.loads(request.body)
        pipeline_code = data.get('pipeline', 'write_chapter')
        context = data.get('context', {})
        dry_run = data.get('dry_run', False)
        
        # Add project info to context
        context['project_title'] = project.title
        context['project_id'] = project.id
        
        # Get content type
        if project.genre_settings:
            try:
                settings = json.loads(project.genre_settings)
                context['content_type'] = settings.get('content_type', 'novel')
            except (json.JSONDecodeError, TypeError):
                context['content_type'] = 'novel'
        else:
            context['content_type'] = 'novel'
        
        # Execute pipeline
        service = AgentPipelineService(project_id)
        result = service.execute_pipeline(pipeline_code, context, dry_run=dry_run)
        
        return JsonResponse({
            'success': result.success,
            'output': result.final_output,
            'steps': result.steps,
            'total_tokens': result.total_tokens,
            'total_cost': result.total_cost,
            'duration': result.total_duration,
            'error': result.error_message,
        })
        
    except Exception as e:
        logger.exception(f"Error executing pipeline: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def pipeline_history(request, project_id):
    """View pipeline execution history"""
    project = get_object_or_404(BookProjects, id=project_id)
    
    executions = AgentPipelineExecution.objects.filter(
        project=project
    ).select_related('pipeline_template').order_by('-created_at')[:50]
    
    return JsonResponse({
        'executions': [
            {
                'id': ex.id,
                'pipeline': ex.pipeline_template.name if ex.pipeline_template else 'Custom',
                'status': ex.status,
                'tokens': ex.total_tokens_used,
                'cost': ex.total_cost,
                'duration': ex.duration_seconds,
                'created_at': ex.created_at.isoformat(),
            }
            for ex in executions
        ]
    })


@login_required
def get_available_pipelines(request):
    """Get list of available pipeline templates"""
    content_type = request.GET.get('content_type')
    pipelines = AgentPipelineManager.get_available_pipelines(content_type)
    return JsonResponse({'pipelines': pipelines})
