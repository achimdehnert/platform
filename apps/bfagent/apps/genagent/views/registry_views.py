"""
Handler Registry Views

Web interface for GenAgent Phase 1 Handler Registry System
Uses handler_registry from core module for dynamic handler management
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from apps.genagent.core.handler_registry import HandlerRegistry


@require_http_methods(["GET"])
def registry_dashboard(request):
    """
    Handler Registry Dashboard - Overview
    
    GET /genagent/registry/
    """
    stats = HandlerRegistry.get_registry_stats()
    
    # Get domain overview
    domains = []
    for domain, count in stats.get("by_domain", {}).items():
        handlers = HandlerRegistry.get_handlers_for_domain(domain)
        domains.append({
            "name": domain,
            "handler_count": count,
            "handlers": handlers
        })
    
    context = {
        "title": "Handler Registry",
        "stats": stats,
        "domains": sorted(domains, key=lambda x: x["name"]),
        "total_domains": len(domains)
    }
    
    return render(request, "genagent/registry/dashboard.html", context)


@require_http_methods(["GET"])
def registry_domain_list(request):
    """
    List all registered handler domains
    
    GET /genagent/registry/domains/
    """
    stats = HandlerRegistry.get_registry_stats()
    
    # Build domain list with handler details
    domains = []
    for domain, count in stats.get("by_domain", {}).items():
        handler_names = HandlerRegistry.get_handlers_for_domain(domain)
        
        # Get detailed info for each handler
        handler_details = []
        for name in handler_names:
            info = HandlerRegistry.get_handler_info(name)
            if info:
                handler_details.append(info)
        
        domains.append({
            "name": domain,
            "handler_count": count,
            "handlers": handler_details
        })
    
    context = {
        "domains": sorted(domains, key=lambda x: x["name"]),
        "stats": stats,
        "title": "Registry Domains"
    }
    
    return render(request, "genagent/registry/domain_list.html", context)


@require_http_methods(["GET"])
def registry_domain_detail(request, domain):
    """
    Show all handlers in a specific domain
    
    GET /genagent/registry/domains/<domain>/
    """
    handler_names = HandlerRegistry.get_handlers_for_domain(domain)
    
    if not handler_names:
        return render(request, "genagent/registry/domain_not_found.html", {
            "domain": domain,
            "available_domains": list(HandlerRegistry.get_registry_stats().get("by_domain", {}).keys())
        }, status=404)
    
    # Get detailed handler info
    handlers = []
    for name in handler_names:
        info = HandlerRegistry.get_handler_info(name)
        if info:
            handlers.append(info)
    
    context = {
        "domain": domain,
        "handlers": sorted(handlers, key=lambda x: x.get("name", "")),
        "handler_count": len(handlers),
        "title": f"Domain: {domain}"
    }
    
    return render(request, "genagent/registry/domain_detail.html", context)


@require_http_methods(["GET"])
def registry_handler_detail(request, handler_name):
    """
    Show detailed information about a handler
    
    GET /genagent/registry/handlers/<handler_name>/
    """
    info = HandlerRegistry.get_handler_info(handler_name)
    
    if not info:
        return render(request, "genagent/registry/handler_not_found.html", {
            "handler_name": handler_name
        }, status=404)
    
    context = {
        "handler": info,
        "handler_name": handler_name,
        "title": f"Handler: {handler_name}"
    }
    
    return render(request, "genagent/registry/handler_detail.html", context)


@require_http_methods(["GET", "POST"])
def registry_handler_test(request, handler_name):
    """
    Test interface for a handler
    
    GET/POST /genagent/registry/handlers/<handler_name>/test/
    """
    info = HandlerRegistry.get_handler_info(handler_name)
    
    if not info:
        return render(request, "genagent/registry/handler_not_found.html", {
            "handler_name": handler_name
        }, status=404)
    
    if request.method == "POST":
        # Execute handler test
        import json
        
        try:
            test_input = request.POST.get("test_input", "{}")
            input_data = json.loads(test_input)
            
            # Get handler class and execute
            handler_class = HandlerRegistry.get_handler_class(handler_name)
            if not handler_class:
                return JsonResponse({
                    "success": False,
                    "error": f"Handler class not found for '{handler_name}'"
                }, status=404)
            
            # Create instance and execute
            handler = handler_class()
            result = handler.execute(input_data)
            
            return JsonResponse({
                "success": True,
                "result": result
            })
            
        except json.JSONDecodeError as e:
            return JsonResponse({
                "success": False,
                "error": f"Invalid JSON input: {str(e)}"
            }, status=400)
        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": f"Execution error: {str(e)}"
            }, status=500)
    
    # GET request - show test form
    context = {
        "handler": info,
        "handler_name": handler_name,
        "title": f"Test: {handler_name}"
    }
    
    return render(request, "genagent/registry/handler_test.html", context)


# API Endpoints

@require_http_methods(["GET"])
def registry_api_stats(request):
    """
    API: Get registry statistics
    
    GET /genagent/registry/api/stats/
    """
    stats = HandlerRegistry.get_registry_stats()
    
    return JsonResponse({
        "success": True,
        "stats": stats
    })


@require_http_methods(["GET"])
def registry_api_domains(request):
    """
    API: List all domains
    
    GET /genagent/registry/api/domains/
    """
    stats = HandlerRegistry.get_registry_stats()
    
    domains = [
        {
            "name": domain,
            "handler_count": count,
            "handlers": HandlerRegistry.get_handlers_for_domain(domain)
        }
        for domain, count in stats.get("by_domain", {}).items()
    ]
    
    return JsonResponse({
        "success": True,
        "domains": domains,
        "total": len(domains)
    })


@require_http_methods(["GET"])
def registry_api_handlers(request):
    """
    API: List all handlers with details
    
    GET /genagent/registry/api/handlers/
    """
    stats = HandlerRegistry.get_registry_stats()
    
    handlers = []
    for domain in stats.get("by_domain", {}).keys():
        for handler_name in HandlerRegistry.get_handlers_for_domain(domain):
            info = HandlerRegistry.get_handler_info(handler_name)
            if info:
                handlers.append(info)
    
    return JsonResponse({
        "success": True,
        "handlers": handlers,
        "total": len(handlers)
    })


@require_http_methods(["GET"])
def registry_api_handler_detail(request, handler_name):
    """
    API: Get handler details
    
    GET /genagent/registry/api/handlers/<handler_name>/
    """
    info = HandlerRegistry.get_handler_info(handler_name)
    
    if not info:
        return JsonResponse({
            "success": False,
            "error": f"Handler '{handler_name}' not found"
        }, status=404)
    
    return JsonResponse({
        "success": True,
        "handler": info
    })
