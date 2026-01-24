"""
Handler Management Views

Web interface for managing and testing GenAgent handlers
"""

from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from apps.genagent.handlers import list_handlers, get_handler
import json


@require_http_methods(["GET"])
def handler_list(request):
    """
    List all registered handlers
    
    GET /genagent/handlers/
    """
    handlers = list_handlers()
    
    # Organize handlers by category
    handlers_data = []
    for path, handler_class in handlers.items():
        # Extract module and class name
        module_parts = path.split('.')
        module = '.'.join(module_parts[:-1])
        class_name = module_parts[-1]
        
        # Get category from module name
        if 'demo' in module:
            category = 'Demo'
        elif 'data' in module:
            category = 'Data Processing'
        elif 'validation' in module:
            category = 'Validation'
        else:
            category = 'Other'
        
        handlers_data.append({
            'path': path,
            'path_encoded': path.replace('.', '--'),  # URL-safe version
            'name': class_name,
            'module': module,
            'category': category,
            'description': handler_class.get_description(),
            'has_config': bool(handler_class.get_config_schema().get('properties'))
        })
    
    # Group by category
    handlers_by_category = {}
    for handler in handlers_data:
        cat = handler['category']
        if cat not in handlers_by_category:
            handlers_by_category[cat] = []
        handlers_by_category[cat].append(handler)
    
    # Statistics
    stats = {
        'total_handlers': len(handlers),
        'categories': len(handlers_by_category),
        'with_config': sum(1 for h in handlers_data if h['has_config']),
        'without_config': sum(1 for h in handlers_data if not h['has_config'])
    }
    
    context = {
        'handlers': handlers_data,
        'handlers_by_category': handlers_by_category,
        'stats': stats,
        'title': 'Handler Registry'
    }
    
    return render(request, 'genagent/handlers/handler_list.html', context)


@require_http_methods(["GET"])
def handler_detail(request, handler_path):
    """
    Show detailed information about a handler
    
    GET /genagent/handlers/<handler_path>/
    """
    # Decode handler_path (replace -- with .)
    handler_path = handler_path.replace('--', '.')
    
    handler_class = get_handler(handler_path)
    
    if not handler_class:
        return render(request, 'genagent/handlers/handler_not_found.html', {
            'handler_path': handler_path
        }, status=404)
    
    # Extract handler info
    module_parts = handler_path.split('.')
    class_name = module_parts[-1]
    module = '.'.join(module_parts[:-1])
    
    # Get config schema
    config_schema = handler_class.get_config_schema()
    properties = config_schema.get('properties', {})
    required = config_schema.get('required', [])
    
    # Format properties for display
    config_fields = []
    for field_name, field_schema in properties.items():
        config_fields.append({
            'name': field_name,
            'type': field_schema.get('type', 'string'),
            'description': field_schema.get('description', ''),
            'default': field_schema.get('default'),
            'required': field_name in required,
            'enum': field_schema.get('enum'),
            'items': field_schema.get('items')
        })
    
    context = {
        'handler_path': handler_path,
        'handler_path_encoded': handler_path.replace('.', '--'),
        'class_name': class_name,
        'module': module,
        'description': handler_class.get_description(),
        'config_schema': config_schema,
        'config_fields': config_fields,
        'has_config': bool(properties),
        'title': f'Handler: {class_name}'
    }
    
    return render(request, 'genagent/handlers/handler_detail.html', context)


@require_http_methods(["GET"])
def handler_test_interface(request, handler_path):
    """
    Show test interface for a handler
    
    GET /genagent/handlers/<handler_path>/test/
    """
    handler_path = handler_path.replace('--', '.')
    handler_class = get_handler(handler_path)
    
    if not handler_class:
        return render(request, 'genagent/handlers/handler_not_found.html', {
            'handler_path': handler_path
        }, status=404)
    
    config_schema = handler_class.get_config_schema()
    
    context = {
        'handler_path': handler_path,
        'handler_path_encoded': handler_path.replace('.', '--'),
        'class_name': handler_path.split('.')[-1],
        'description': handler_class.get_description(),
        'config_schema': config_schema,
        'title': f'Test: {handler_path.split(".")[-1]}'
    }
    
    return render(request, 'genagent/handlers/handler_test.html', context)


@require_http_methods(["POST"])
def handler_execute_test(request, handler_path):
    """
    Execute handler with test data
    
    POST /genagent/handlers/<handler_path>/execute/
    """
    handler_path = handler_path.replace('--', '.')
    handler_class = get_handler(handler_path)
    
    if not handler_class:
        return JsonResponse({
            'success': False,
            'error': f"Handler '{handler_path}' not found"
        }, status=404)
    
    try:
        # Parse request data
        config_str = request.POST.get('config', '{}').strip()
        context_str = request.POST.get('context', '{}').strip()
        
        # Handle empty strings
        if not config_str:
            config_str = '{}'
        if not context_str:
            context_str = '{}'
            
        config = json.loads(config_str)
        context = json.loads(context_str)
        test_mode = request.POST.get('test_mode', 'true').lower() == 'true'
        
        # Create handler instance
        handler = handler_class(config=config)
        
        # Execute
        result = handler.execute(context, test_mode=test_mode)
        
        # Return HTML for HTMX
        return render(request, 'genagent/handlers/handler_test_result.html', {
            'success': True,
            'result': result,
            'handler_path': handler_path,
            'test_mode': test_mode
        })
        
    except json.JSONDecodeError as e:
        return render(request, 'genagent/handlers/handler_test_result.html', {
            'success': False,
            'error': f"Invalid JSON: {str(e)}"
        }, status=400)
    except Exception as e:
        return render(request, 'genagent/handlers/handler_test_result.html', {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }, status=500)


@require_http_methods(["GET"])
def handler_search(request):
    """
    Search handlers by name or description
    
    GET /genagent/handlers/search/?q=<query>
    """
    query = request.GET.get('q', '').lower()
    handlers = list_handlers()
    
    results = []
    for path, handler_class in handlers.items():
        name = path.split('.')[-1]
        description = handler_class.get_description()
        
        if query in name.lower() or query in description.lower():
            results.append({
                'path': path,
                'path_encoded': path.replace('.', '--'),
                'name': name,
                'description': description
            })
    
    context = {
        'query': query,
        'results': results,
        'count': len(results)
    }
    
    return render(request, 'genagent/handlers/handler_search_results.html', context)


# API Endpoints

@require_http_methods(["GET"])
def handler_api_list(request):
    """
    API: List all handlers
    
    GET /genagent/api/handlers/
    """
    handlers = list_handlers()
    
    data = {
        'handlers': [
            {
                'path': path,
                'name': path.split('.')[-1],
                'module': '.'.join(path.split('.')[:-1]),
                'description': handler_class.get_description(),
                'config_schema': handler_class.get_config_schema()
            }
            for path, handler_class in handlers.items()
        ],
        'count': len(handlers)
    }
    
    return JsonResponse(data)


@require_http_methods(["GET"])
def handler_api_detail(request, handler_path):
    """
    API: Get handler details
    
    GET /genagent/api/handlers/<handler_path>/
    """
    handler_path = handler_path.replace('--', '.')
    handler_class = get_handler(handler_path)
    
    if not handler_class:
        return JsonResponse({
            'error': f"Handler '{handler_path}' not found"
        }, status=404)
    
    data = {
        'path': handler_path,
        'name': handler_path.split('.')[-1],
        'module': '.'.join(handler_path.split('.')[:-1]),
        'description': handler_class.get_description(),
        'config_schema': handler_class.get_config_schema()
    }
    
    return JsonResponse(data)
