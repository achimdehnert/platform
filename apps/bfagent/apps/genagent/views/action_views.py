"""
Action Management Views

CRUD interface for managing GenAgent Actions with dynamic Handler integration
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from apps.genagent.models import Phase, Action, ExecutionLog
from apps.genagent.handlers import list_handlers, get_handler
import json


@require_http_methods(["GET"])
def genagent_dashboard(request):
    """
    GenAgent Dashboard - Overview of all components
    
    GET /genagent/
    """
    phases = Phase.objects.filter(is_active=True).prefetch_related('actions')
    handlers = list_handlers()
    
    # Stats
    total_phases = phases.count()
    total_actions = Action.objects.filter(is_active=True).count()
    total_handlers = len(handlers)
    recent_logs = ExecutionLog.objects.order_by('-started_at')[:10]
    
    context = {
        'title': 'GenAgent Dashboard',
        'phases': phases,
        'handlers': handlers,
        'stats': {
            'phases': total_phases,
            'actions': total_actions,
            'handlers': total_handlers,
        },
        'recent_logs': recent_logs
    }
    
    return render(request, 'genagent/dashboard.html', context)


@require_http_methods(["GET"])
def action_list(request):
    """
    List all actions grouped by phase

    GET /genagent/actions/
    """
    phases = Phase.objects.filter(is_active=True).prefetch_related('actions')

    context = {
        'phases': phases,
        'title': 'GenAgent Actions'
    }

    return render(request, 'genagent/actions/action_list.html', context)


@require_http_methods(["GET", "POST"])
def action_create(request, phase_id):
    """
    Create new action for a phase

    GET/POST /genagent/actions/phase/<phase_id>/create/
    """
    phase = get_object_or_404(Phase, pk=phase_id)
    handlers = list_handlers()

    if request.method == 'POST':
        try:
            # Extract form data
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            handler_class = request.POST.get('handler_class')
            order = int(request.POST.get('order', 0))
            timeout_seconds = request.POST.get('timeout_seconds')
            retry_count = int(request.POST.get('retry_count', 0))
            continue_on_error = request.POST.get('continue_on_error') == 'on'

            # Parse config JSON
            config_json = request.POST.get('config', '{}')
            config = json.loads(config_json)

            # Create action
            action = Action.objects.create(
                phase=phase,
                name=name,
                description=description,
                handler_class=handler_class,
                order=order,
                config=config,
                timeout_seconds=int(timeout_seconds) if timeout_seconds else None,
                retry_count=retry_count,
                continue_on_error=continue_on_error
            )

            messages.success(request, f'Action "{action.name}" created successfully!')
            return redirect('genagent:phase-detail', phase_id=phase.id)

        except json.JSONDecodeError as e:
            messages.error(request, f'Invalid JSON in config: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error creating action: {str(e)}')

    # Prepare handlers for dropdown
    handlers_list = []
    for path, handler_class in handlers.items():
        handlers_list.append({
            'path': path,
            'name': path.split('.')[-1],
            'description': handler_class.get_description()
        })

    context = {
        'phase': phase,
        'handlers': handlers_list,
        'title': f'Create Action for {phase.name}'
    }

    return render(request, 'genagent/actions/action_form.html', context)


@require_http_methods(["GET", "POST"])
def action_edit(request, action_id):
    """
    Edit existing action

    GET/POST /genagent/actions/<action_id>/edit/
    """
    action = get_object_or_404(Action, pk=action_id)
    handlers = list_handlers()

    if request.method == 'POST':
        try:
            action.name = request.POST.get('name')
            action.description = request.POST.get('description', '')
            action.handler_class = request.POST.get('handler_class')
            action.order = int(request.POST.get('order', 0))

            timeout = request.POST.get('timeout_seconds')
            action.timeout_seconds = int(timeout) if timeout else None

            action.retry_count = int(request.POST.get('retry_count', 0))
            action.continue_on_error = request.POST.get('continue_on_error') == 'on'

            # Parse config JSON
            config_json = request.POST.get('config', '{}')
            action.config = json.loads(config_json)

            action.save()

            messages.success(request, f'Action "{action.name}" updated successfully!')
            return redirect('genagent:phase-detail', phase_id=action.phase.id)

        except json.JSONDecodeError as e:
            messages.error(request, f'Invalid JSON in config: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error updating action: {str(e)}')

    # Prepare handlers for dropdown
    handlers_list = []
    for path, handler_class in handlers.items():
        handlers_list.append({
            'path': path,
            'name': path.split('.')[-1],
            'description': handler_class.get_description()
        })

    context = {
        'action': action,
        'phase': action.phase,
        'handlers': handlers_list,
        'title': f'Edit Action: {action.name}'
    }

    return render(request, 'genagent/actions/action_form.html', context)


@require_http_methods(["GET", "POST"])
def action_delete(request, action_id):
    """
    Delete action

    GET/POST /genagent/actions/<action_id>/delete/
    """
    action = get_object_or_404(Action, pk=action_id)
    phase = action.phase

    if request.method == 'POST':
        action_name = action.name
        action.delete()
        messages.success(request, f'Action "{action_name}" deleted successfully!')
        return redirect('genagent:phase-detail', phase_id=phase.id)

    context = {
        'action': action,
        'title': f'Delete Action: {action.name}'
    }

    return render(request, 'genagent/actions/action_confirm_delete.html', context)


@require_http_methods(["GET"])
def action_get_config_schema(request):
    """
    HTMX endpoint: Get config schema for selected handler

    GET /genagent/actions/config-schema/?handler_class=<path>
    """
    handler_path = request.GET.get('handler_class')

    if not handler_path:
        return render(request, 'genagent/actions/action_config_fields.html', {
            'schema': None,
            'error': 'No handler selected'
        })

    handler_class = get_handler(handler_path)

    if not handler_class:
        return render(request, 'genagent/actions/action_config_fields.html', {
            'schema': None,
            'error': f'Handler "{handler_path}" not found'
        })

    schema = handler_class.get_config_schema()

    context = {
        'schema': schema,
        'handler_path': handler_path,
        'handler_name': handler_path.split('.')[-1]
    }

    return render(request, 'genagent/actions/action_config_fields.html', context)


@require_http_methods(["GET"])
def phase_detail(request, phase_id):
    """
    Show phase details with actions

    GET /genagent/phases/<phase_id>/
    """
    phase = get_object_or_404(Phase, pk=phase_id)
    actions = phase.actions.filter(is_active=True).order_by('order')

    context = {
        'phase': phase,
        'actions': actions,
        'title': f'Phase: {phase.name}'
    }

    return render(request, 'genagent/actions/phase_detail.html', context)


@require_http_methods(["POST"])
def action_execute(request, action_id):
    """
    Execute a single action

    POST /genagent/actions/<action_id>/execute/
    """
    action = get_object_or_404(Action, pk=action_id)

    try:
        # Get context from POST data
        context_json = request.POST.get('context', '{}').strip()
        # Handle empty strings
        if not context_json:
            context_json = '{}'
        context = json.loads(context_json)
        test_mode = request.POST.get('test_mode', 'true').lower() == 'true'

        # Execute action
        result = action.execute(context=context, test_mode=test_mode)

        # Return HTML for HTMX
        return render(request, 'genagent/actions/execution_result.html', {
            'result': result,
            'action': action
        })

    except json.JSONDecodeError as e:
        return render(request, 'genagent/actions/execution_result.html', {
            'result': {
                'status': 'failed',
                'error': f'Invalid JSON in context: {str(e)}'
            },
            'action': action
        }, status=400)
    except Exception as e:
        return render(request, 'genagent/actions/execution_result.html', {
            'result': {
                'status': 'failed',
                'error': str(e)
            },
            'action': action
        }, status=500)


@require_http_methods(["POST"])
def phase_execute(request, phase_id):
    """
    Execute all actions in a phase

    POST /genagent/phases/<phase_id>/execute/
    """
    phase = get_object_or_404(Phase, pk=phase_id)

    try:
        # Get context from POST data
        context_json = request.POST.get('context', '{}').strip()
        # Handle empty strings
        if not context_json:
            context_json = '{}'
        context = json.loads(context_json)
        test_mode = request.POST.get('test_mode', 'true').lower() == 'true'

        # Execute phase
        results = phase.execute_actions(context=context, test_mode=test_mode)

        # Return HTML for HTMX
        return render(request, 'genagent/actions/phase_execution_result.html', {
            'results': results,
            'phase': phase
        })

    except json.JSONDecodeError as e:
        return render(request, 'genagent/actions/phase_execution_result.html', {
            'results': {
                'status': 'failed',
                'error': f'Invalid JSON in context: {str(e)}'
            },
            'phase': phase
        }, status=400)
    except Exception as e:
        return render(request, 'genagent/actions/phase_execution_result.html', {
            'results': {
                'status': 'failed',
                'error': str(e)
            },
            'phase': phase
        }, status=500)


@require_http_methods(["GET"])
def action_execution_logs(request, action_id):
    """
    View execution logs for an action

    GET /genagent/actions/<action_id>/logs/
    """
    action = get_object_or_404(Action, pk=action_id)
    logs = action.executions.all()[:50]  # Last 50 executions

    context = {
        'action': action,
        'logs': logs,
        'title': f'Execution Logs: {action.name}'
    }

    return render(request, 'genagent/actions/action_execution_logs.html', context)


@require_http_methods(["POST"])
def action_reorder(request, phase_id):
    """
    Reorder actions in a phase
    
    POST /genagent/phases/<phase_id>/reorder/
    """
    phase = get_object_or_404(Phase, pk=phase_id)
    
    try:
        import json as json_module
        data = json_module.loads(request.body)
        action_ids = data.get('action_ids', [])
        
        # Update order for each action
        for index, action_id in enumerate(action_ids):
            Action.objects.filter(pk=action_id, phase=phase).update(order=index)
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_http_methods(["GET"])
def execution_log_detail(request, log_id):
    """
    View details of a single execution log

    GET /genagent/execution-logs/<log_id>/
    """
    log = get_object_or_404(ExecutionLog, pk=log_id)

    context = {
        'log': log,
        'title': f'Execution Log #{log.id}'
    }

    return render(request, 'genagent/actions/execution_log_detail.html', context)
