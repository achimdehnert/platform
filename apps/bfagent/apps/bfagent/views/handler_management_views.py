"""
Handler Management Views - MVP Phase 1

Provides UI for:
- Tab 1: Handler Registry (read-only list)
- Tab 2: Action Mappings (CRUD)
"""

from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_http_methods
from apps.bfagent.models_handlers import Handler, ActionHandler
from apps.bfagent.models import AgentAction


@require_http_methods(["GET"])
def handler_management_dashboard(request: HttpRequest) -> HttpResponse:
    """
    Main Handler Management Dashboard with Tab Navigation
    """
    # Get all handlers for Tab 1
    handlers = Handler.objects.filter(is_active=True).order_by('handler_id')
    
    # Get all action handlers for Tab 2
    action_handlers = ActionHandler.objects.select_related(
        'handler', 'action'
    ).filter(is_active=True).order_by('action__name')
    
    # Get available actions for dropdown
    actions = AgentAction.objects.all().order_by('name')
    
    # Get available handlers for dropdown
    available_handlers = Handler.objects.filter(is_active=True).order_by('display_name')
    
    context = {
        'page_title': 'Handler Management',
        'handlers': handlers,
        'action_handlers': action_handlers,
        'actions': actions,
        'available_handlers': available_handlers,
    }
    
    return render(request, 'bfagent/handler_management.html', context)


@require_http_methods(["GET"])
def handler_list_tab(request: HttpRequest) -> HttpResponse:
    """
    Tab 1: Handler Registry List (HTMX)
    """
    domain = request.GET.get('domain', '')
    
    handlers = Handler.objects.filter(is_active=True)
    
    if domain:
        handlers = handlers.filter(handler_id__startswith=f'{domain}.')
    
    handlers = handlers.order_by('handler_id')
    
    context = {
        'handlers': handlers,
    }
    
    return render(request, 'bfagent/partials/handler_list.html', context)


@require_http_methods(["GET"])
def action_mappings_tab(request: HttpRequest) -> HttpResponse:
    """
    Tab 2: Action Mappings List (HTMX)
    """
    action_id = request.GET.get('action_id', '')
    
    action_handlers = ActionHandler.objects.select_related('handler', 'action')
    
    if action_id:
        action_handlers = action_handlers.filter(action_id=action_id)
    
    action_handlers = action_handlers.filter(is_active=True).order_by('action__name', 'order')
    
    # Get available actions and handlers
    actions = AgentAction.objects.all().order_by('name')
    available_handlers = Handler.objects.filter(is_active=True).order_by('display_name')
    
    context = {
        'action_handlers': action_handlers,
        'actions': actions,
        'available_handlers': available_handlers,
    }
    
    return render(request, 'bfagent/partials/action_mapping_list.html', context)


@require_http_methods(["POST"])
def create_action_mapping(request: HttpRequest) -> HttpResponse:
    """
    Create new Action → Handler Mapping
    """
    import json
    import traceback
    
    action_id = request.POST.get('action_id')
    handler_id = request.POST.get('handler_id')
    config_str = request.POST.get('config', '{}')
    phase = request.POST.get('phase', 'processing')
    order = int(request.POST.get('order', 0))
    
    # Error handling parameters
    on_error = request.POST.get('on_error', 'stop')
    retry_count = int(request.POST.get('retry_count', 3))
    retry_delay_ms = int(request.POST.get('retry_delay_ms', 1000))
    fallback_handler_id = request.POST.get('fallback_handler_id') or None
    
    # A/B Testing & Conditional Execution (Phase 3B Session 5 & 6)
    variant = request.POST.get('variant', '').strip()
    traffic_weight = int(request.POST.get('traffic_weight', 100))
    condition_str = request.POST.get('condition', '').strip()
    
    try:
        # Parse config JSON (convert Python dict syntax to JSON first)
        config = {}
        if config_str:
            try:
                # Try JSON first
                config = json.loads(config_str)
            except json.JSONDecodeError:
                # Try converting Python dict syntax (single quotes → double quotes)
                try:
                    config_str_json = config_str.replace("'", '"')
                    config = json.loads(config_str_json)
                except json.JSONDecodeError:
                    config = {}  # If both fail, use empty dict
        
        # Parse condition JSON
        condition = None
        if condition_str:
            try:
                condition = json.loads(condition_str)
            except json.JSONDecodeError:
                pass  # Leave as None if invalid
        
        action = AgentAction.objects.get(id=action_id)
        handler = Handler.objects.get(id=handler_id)
        
        # Check for duplicate mapping (including variant)
        existing = ActionHandler.objects.filter(
            action=action,
            handler=handler,
            phase=phase,
            variant=variant
        ).first()
        
        if existing:
            return HttpResponse(
                f'<div class="alert alert-warning">'
                f'<i class="bi bi-exclamation-triangle"></i> '
                f'Mapping already exists for {action.display_name} → {handler.display_name} in {phase} phase'
                f'{f" (variant: {variant})" if variant else ""}'
                f'</div>',
                status=400
            )
        
        # Create mapping with all fields
        ActionHandler.objects.create(
            action=action,
            handler=handler,
            phase=phase,
            config=config,
            is_active=True,
            order=order,
            on_error=on_error,
            retry_count=retry_count,
            retry_delay_ms=retry_delay_ms,
            fallback_handler_id=fallback_handler_id,
            variant=variant,
            traffic_weight=traffic_weight,
            condition=condition,
        )
        
        # Build success message
        phase_display = phase.capitalize()
        success_msg = (
            f'<div class="alert alert-success alert-dismissible fade show mb-3" role="alert">'
            f'<i class="bi bi-check-circle"></i> '
            f'Successfully created mapping: <strong>{action.display_name}</strong> → <strong>{handler.display_name}</strong> '
            f'<span class="badge bg-success">{phase_display} Phase</span> '
            f'<span class="badge bg-secondary">Order: {order}</span>'
            f'<button type="button" class="btn-close" data-bs-dismiss="alert"></button>'
            f'</div>'
        )
        
        # Return updated list - manually render since we need GET context
        action_handlers = ActionHandler.objects.select_related('handler', 'action')
        action_handlers = action_handlers.filter(is_active=True).order_by('action__name', 'order')
        
        # Apply filter if provided
        filter_action_id = request.POST.get('filter_action_id')
        if filter_action_id:
            action_handlers = action_handlers.filter(action_id=filter_action_id)
        
        actions = AgentAction.objects.all().order_by('name')
        available_handlers = Handler.objects.filter(is_active=True).order_by('display_name')
        
        context = {
            'action_handlers': action_handlers,
            'actions': actions,
            'available_handlers': available_handlers,
            'success_message': success_msg,
        }
        
        return render(request, 'bfagent/partials/action_mapping_list.html', context)
        
    except Exception as e:
        # Log full traceback for debugging
        print(f"Error creating action mapping: {str(e)}")
        print(traceback.format_exc())
        return HttpResponse(
            f'<div class="alert alert-danger">Error: {str(e)}</div>',
            status=400
        )


@require_http_methods(["POST"])
def delete_action_mapping(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Delete Action Handler Mapping
    """
    try:
        action_handler = get_object_or_404(ActionHandler, pk=pk)
        action_handler.delete()
        
        # Get filter from request (for persistence)
        filter_action_id = request.POST.get('filter_action_id')
        
        # Return updated list with filter support
        action_handlers = ActionHandler.objects.select_related('handler', 'action', 'fallback_handler')
        action_handlers = action_handlers.filter(is_active=True)
        
        if filter_action_id:
            action_handlers = action_handlers.filter(action_id=filter_action_id)
        
        action_handlers = action_handlers.order_by('action__name', 'order')
        
        actions = AgentAction.objects.all().order_by('name')
        available_handlers = Handler.objects.filter(is_active=True).order_by('display_name')
        
        context = {
            'action_handlers': action_handlers,
            'actions': actions,
            'available_handlers': available_handlers,
        }
        
        return render(request, 'bfagent/partials/action_mapping_list.html', context)
        
    except Exception as e:
        return HttpResponse(
            f'<div class="alert alert-danger">Error: {str(e)}</div>',
            status=400
        )


@require_http_methods(["POST"])
def update_action_mapping(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Update existing Action → Handler Mapping
    """
    import json
    
    try:
        action_handler = get_object_or_404(ActionHandler, pk=pk)
        
        # Get form data
        action_id = request.POST.get('action_id')
        handler_id = request.POST.get('handler_id')
        config_str = request.POST.get('config', '{}')
        phase = request.POST.get('phase', 'processing')
        order = int(request.POST.get('order', 0))
        
        # Error handling parameters
        on_error = request.POST.get('on_error', 'stop')
        retry_count = int(request.POST.get('retry_count', 3))
        retry_delay_ms = int(request.POST.get('retry_delay_ms', 1000))
        fallback_handler_id = request.POST.get('fallback_handler_id') or None
        
        # Parse config JSON
        try:
            config = json.loads(config_str) if config_str else {}
        except json.JSONDecodeError:
            config = {}
        
        action = AgentAction.objects.get(id=action_id)
        handler = Handler.objects.get(id=handler_id)
        
        # Update the mapping
        action_handler.action = action
        action_handler.handler = handler
        action_handler.phase = phase
        action_handler.order = order
        action_handler.config = config
        action_handler.on_error = on_error
        action_handler.retry_count = retry_count
        action_handler.retry_delay_ms = retry_delay_ms
        action_handler.fallback_handler_id = fallback_handler_id
        action_handler.save()
        
        # Build success message
        phase_display = phase.capitalize()
        success_msg = (
            f'<div class="alert alert-success alert-dismissible fade show mb-3" role="alert">'
            f'<i class="bi bi-check-circle"></i> '
            f'Successfully updated mapping: <strong>{action.display_name}</strong> → <strong>{handler.display_name}</strong> '
            f'<span class="badge bg-success">{phase_display} Phase</span> '
            f'<span class="badge bg-secondary">Order: {order}</span>'
            f'<button type="button" class="btn-close" data-bs-dismiss="alert"></button>'
            f'</div>'
        )
        
        # Return updated list with filter support
        filter_action_id = request.POST.get('filter_action_id')
        action_handlers = ActionHandler.objects.select_related('handler', 'action', 'fallback_handler')
        action_handlers = action_handlers.filter(is_active=True)
        
        if filter_action_id:
            action_handlers = action_handlers.filter(action_id=filter_action_id)
        
        action_handlers = action_handlers.order_by('action__name', 'order')
        
        actions = AgentAction.objects.all().order_by('name')
        available_handlers = Handler.objects.filter(is_active=True).order_by('display_name')
        
        context = {
            'action_handlers': action_handlers,
            'actions': actions,
            'available_handlers': available_handlers,
            'success_message': success_msg,
        }
        
        return render(request, 'bfagent/partials/action_mapping_list.html', context)
        
    except Exception as e:
        return HttpResponse(
            f'<div class="alert alert-danger">'
            f'<i class="bi bi-exclamation-triangle"></i> '
            f'Error updating mapping: {str(e)}'
            f'</div>',
            status=400
        )


@require_http_methods(["POST"])
def bulk_delete_mappings(request: HttpRequest) -> HttpResponse:
    """
    Bulk delete action handlers
    """
    import json
    
    try:
        data = json.loads(request.body)
        ids = data.get('ids', [])
        filter_action_id = data.get('filter_action_id')  # Get filter from request
        
        ActionHandler.objects.filter(pk__in=ids).delete()
        
        # Return updated list with filter applied
        action_handlers = ActionHandler.objects.select_related('handler', 'action', 'fallback_handler')
        action_handlers = action_handlers.filter(is_active=True)
        
        if filter_action_id:
            action_handlers = action_handlers.filter(action_id=filter_action_id)
        
        action_handlers = action_handlers.order_by('action__name', 'order')
        
        actions = AgentAction.objects.all().order_by('name')
        available_handlers = Handler.objects.filter(is_active=True).order_by('display_name')
        
        context = {
            'action_handlers': action_handlers,
            'actions': actions,
            'available_handlers': available_handlers,
        }
        
        return render(request, 'bfagent/partials/action_mapping_list.html', context)
    except Exception as e:
        return HttpResponse(f'<div class="alert alert-danger">Error: {str(e)}</div>', status=400)


@require_http_methods(["POST"])
def bulk_update_phase(request: HttpRequest) -> HttpResponse:
    """
    Bulk update phase for action handlers
    """
    import json
    
    try:
        data = json.loads(request.body)
        ids = data.get('ids', [])
        phase = data.get('phase', 'processing')
        
        ActionHandler.objects.filter(pk__in=ids).update(phase=phase)
        
        # Return updated list
        action_handlers = ActionHandler.objects.select_related('handler', 'action', 'fallback_handler')
        action_handlers = action_handlers.filter(is_active=True).order_by('action__name', 'order')
        
        actions = AgentAction.objects.all().order_by('name')
        available_handlers = Handler.objects.filter(is_active=True).order_by('display_name')
        
        context = {
            'action_handlers': action_handlers,
            'actions': actions,
            'available_handlers': available_handlers,
        }
        
        return render(request, 'bfagent/partials/action_mapping_list.html', context)
    except Exception as e:
        return HttpResponse(f'<div class="alert alert-danger">Error: {str(e)}</div>', status=400)


@require_http_methods(["POST"])
def bulk_toggle_active(request: HttpRequest) -> HttpResponse:
    """
    Bulk toggle active status for action handlers
    """
    import json
    
    try:
        data = json.loads(request.body)
        ids = data.get('ids', [])
        
        for handler_id in ids:
            handler = ActionHandler.objects.get(pk=handler_id)
            handler.is_active = not handler.is_active
            handler.save()
        
        # Return updated list
        action_handlers = ActionHandler.objects.select_related('handler', 'action', 'fallback_handler')
        action_handlers = action_handlers.filter(is_active=True).order_by('action__name', 'order')
        
        actions = AgentAction.objects.all().order_by('name')
        available_handlers = Handler.objects.filter(is_active=True).order_by('display_name')
        
        context = {
            'action_handlers': action_handlers,
            'actions': actions,
            'available_handlers': available_handlers,
        }
        
        return render(request, 'bfagent/partials/action_mapping_list.html', context)
    except Exception as e:
        return HttpResponse(f'<div class="alert alert-danger">Error: {str(e)}</div>', status=400)


@require_http_methods(["POST"])
def test_handler(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Test a handler with provided config and sample data
    """
    import json
    import time
    import importlib
    
    try:
        handler = get_object_or_404(Handler, pk=pk)
        
        # Parse input data
        config_str = request.POST.get('config', '{}')
        sample_data_str = request.POST.get('sample_data', '{}')
        
        try:
            config = json.loads(config_str) if config_str else {}
        except json.JSONDecodeError as e:
            return HttpResponse(
                f'<div class="alert alert-danger">'
                f'<i class="bi bi-exclamation-triangle"></i> '
                f'Invalid config JSON: {str(e)}'
                f'</div>',
                status=400
            )
        
        try:
            sample_data = json.loads(sample_data_str) if sample_data_str else {}
        except json.JSONDecodeError as e:
            return HttpResponse(
                f'<div class="alert alert-danger">'
                f'<i class="bi bi-exclamation-triangle"></i> '
                f'Invalid sample data JSON: {str(e)}'
                f'</div>',
                status=400
            )
        
        # Execute handler
        start_time = time.time()
        try:
            # Dynamically import handler class
            module = importlib.import_module(handler.module_path)
            handler_class = getattr(module, handler.class_name)
            handler_instance = handler_class()
            
            # Execute with config and sample_data
            # Merge config into context for handlers that expect a single context dict
            merged_context = {**sample_data}
            if config:
                merged_context['config'] = config
            
            result = handler_instance.execute(merged_context)
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Format result
            result_html = f'''
            <div class="alert alert-success">
                <h6><i class="bi bi-check-circle"></i> Test Successful</h6>
                <div class="mt-2">
                    <strong>Execution Time:</strong> {execution_time:.2f}ms
                </div>
            </div>
            <div class="card mt-3">
                <div class="card-header">
                    <strong>Output Data</strong>
                </div>
                <div class="card-body">
                    <pre class="mb-0"><code>{json.dumps(result, indent=2, ensure_ascii=False)}</code></pre>
                </div>
            </div>
            '''
            return HttpResponse(result_html)
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_html = f'''
            <div class="alert alert-danger">
                <h6><i class="bi bi-exclamation-triangle"></i> Test Failed</h6>
                <div class="mt-2">
                    <strong>Error:</strong> {str(e)}
                </div>
                <div class="mt-2">
                    <strong>Execution Time:</strong> {execution_time:.2f}ms
                </div>
            </div>
            '''
            return HttpResponse(error_html)
        
    except Exception as e:
        return HttpResponse(
            f'<div class="alert alert-danger">'
            f'<i class="bi bi-exclamation-triangle"></i> '
            f'Error: {str(e)}'
            f'</div>',
            status=400
        )


@require_http_methods(["GET"])
def llm_handler_test_tab(request: HttpRequest) -> HttpResponse:
    """Load LLM Handler Testing tab content"""
    from apps.bfagent.models import BookProjects, Agents, Llms
    
    projects = BookProjects.objects.all()[:20]
    llms_count = Llms.objects.filter(is_active=True).count()
    agents_count = Agents.objects.filter(status='active').count()
    
    return render(request, 'bfagent/partials/llm_test_tab.html', {
        'projects': projects,
        'llms_count': llms_count,
        'agents_count': agents_count,
    })


@require_http_methods(["POST"])
def llm_test_execute(request: HttpRequest) -> HttpResponse:
    """Execute LLM handler test"""
    import json
    from apps.bfagent.handlers.processing_handlers import (
        ChapterGenerateHandler,
        LLMCallHandler,
    )
    
    try:
        handler_type = request.POST.get('handler_type')
        
        if handler_type == 'chapter':
            handler = ChapterGenerateHandler()
            
            # Parse plot points
            plot_points_str = request.POST.get('plot_points', '')
            plot_points = [p.strip() for p in plot_points_str.split(',') if p.strip()] if plot_points_str else []
            
            result = handler.execute({
                'action': 'generate_chapter_outline',
                'project_id': int(request.POST.get('project_id')),
                'chapter_number': int(request.POST.get('chapter_number', 1)),
                'parameters': {
                    'chapter_title': request.POST.get('chapter_title', 'Chapter 1'),
                    'word_count_target': int(request.POST.get('word_count', 3000)),
                    'plot_points': plot_points,
                }
            })
        elif handler_type == 'llm':
            handler = LLMCallHandler()
            result = handler.execute({
                'system_prompt': 'You are a professional fiction writing assistant.',
                'user_prompt': request.POST.get('user_prompt'),
                'max_tokens': 500,
            })
        else:
            return HttpResponse('<div class="alert alert-danger">Invalid handler type</div>', status=400)
        
        # Format success response
        return HttpResponse(f'''
            <div class="alert alert-success">
                <strong><i class="bi bi-check-circle"></i> Success!</strong>
                {f'<p class="mb-0 mt-2"><strong>LLM:</strong> {result.get("llm_used", "N/A")}</p>' if 'llm_used' in result else ''}
            </div>
            <div class="card">
                <div class="card-body">
                    <pre class="mb-0" style="max-height: 400px; overflow-y: auto;"><code>{json.dumps(result, indent=2, ensure_ascii=False)}</code></pre>
                </div>
            </div>
        ''')
        
    except Exception as e:
        import traceback
        return HttpResponse(f'''
            <div class="alert alert-danger">
                <strong><i class="bi bi-exclamation-triangle"></i> Error:</strong>
                <p class="mb-0 mt-2">{str(e)}</p>
                <details class="mt-2">
                    <summary>Traceback</summary>
                    <pre class="mt-2"><code>{traceback.format_exc()}</code></pre>
                </details>
            </div>
        ''', status=500)


@require_http_methods(["POST"])
def reorder_mappings(request: HttpRequest) -> HttpResponse:
    """
    Reorder Action Handler Mappings via Drag & Drop
    Expects JSON: {"orders": [{"id": 1, "order": 10}, {"id": 2, "order": 20}, ...]}
    """
    import json
    
    try:
        data = json.loads(request.body)
        orders = data.get('orders', [])
        
        # Update order for each mapping
        updated_count = 0
        for item in orders:
            mapping_id = item.get('id')
            new_order = item.get('order')
            
            if mapping_id and new_order is not None:
                ActionHandler.objects.filter(pk=mapping_id).update(order=new_order)
                updated_count += 1
        
        from django.http import JsonResponse
        return JsonResponse({
            'success': True,
            'updated': updated_count,
            'message': f'Updated order for {updated_count} mappings'
        })
        
    except Exception as e:
        from django.http import JsonResponse
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_http_methods(["GET"])
def handler_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Handler Detail Modal (HTMX)
    """
    handler = get_object_or_404(Handler, pk=pk)
    
    context = {
        'handler': handler,
    }
    
    return render(request, 'bfagent/partials/handler_detail_modal.html', context)
