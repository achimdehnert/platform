"""
Context Enrichment Views

Provides UI for testing and debugging context enrichment schemas.
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json
import time

from apps.bfagent.models import ContextSchema
from apps.bfagent.services.context_enrichment.enricher import DatabaseContextEnricher


@login_required
def context_enrichment_tester(request):
    """Main tester page"""
    schemas = ContextSchema.objects.filter(is_active=True).order_by('display_name')
    
    context = {
        'schemas': schemas,
        'title': 'Context Enrichment Tester',
    }
    
    return render(request, 'bfagent/context_enrichment_tester.html', context)


@login_required
@require_http_methods(["POST"])
def test_enrichment(request):
    """Test enrichment endpoint"""
    try:
        # Parse request
        data = json.loads(request.body)
        schema_name = data.get('schema_name')
        params = data.get('params', {})
        dry_run = data.get('dry_run', False)
        
        if not schema_name:
            return JsonResponse({
                'success': False,
                'error': 'Schema name is required'
            }, status=400)
        
        # Initialize enricher
        enricher = DatabaseContextEnricher()
        
        # Track time
        start_time = time.time()
        
        # Enrich
        try:
            if dry_run:
                result = enricher.enrich(schema_name, dry_run=True, **params)
                execution_info = {
                    'mode': 'dry_run',
                    'message': 'Dry run mode - no actual data fetched'
                }
            else:
                result = enricher.enrich(schema_name, **params)
                execution_info = {
                    'mode': 'live',
                    'message': 'Live enrichment executed'
                }
            
            execution_time = (time.time() - start_time) * 1000  # ms
            
            return JsonResponse({
                'success': True,
                'result': result,
                'execution_info': execution_info,
                'execution_time_ms': round(execution_time, 2),
                'schema_name': schema_name,
                'params': params
            })
        except Exception as enrichment_error:
            # Return enrichment errors as 200 with success=False
            return JsonResponse({
                'success': False,
                'error': str(enrichment_error),
                'error_type': type(enrichment_error).__name__,
                'hint': 'Check if all required parameters are provided'
            })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }, status=500)


@login_required
@require_http_methods(["GET"])
def schema_details(request, schema_id):
    """Get schema details"""
    try:
        schema = ContextSchema.objects.get(id=schema_id)
        sources = schema.get_active_sources()
        
        schema_data = {
            'id': schema.id,
            'name': schema.name,
            'display_name': schema.display_name,
            'description': schema.description,
            'handler_type': schema.handler_type,
            'version': schema.version,
            'is_active': schema.is_active,
            'is_system': schema.is_system,
            'sources': []
        }
        
        for source in sources:
            schema_data['sources'].append({
                'id': source.id,
                'name': source.name,
                'source_type': source.source_type,
                'order': source.order,
                'is_required': source.is_required,
                'is_active': source.is_active,
                'context_key': source.context_key or 'merged',
                'model_name': source.model_name,
                'function_name': source.function_name,
            })
        
        return JsonResponse({
            'success': True,
            'schema': schema_data
        })
        
    except ContextSchema.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Schema not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def schema_params(request, schema_name):
    """Get expected parameters for a schema"""
    try:
        schema = ContextSchema.objects.get(name=schema_name, is_active=True)
        sources = schema.get_active_sources()
        
        # Extract common parameter patterns
        params = set()
        
        for source in sources:
            # Check filter_config for placeholders
            if source.filter_config:
                for key, value in source.filter_config.items():
                    if isinstance(value, str) and '{' in value and '}' in value:
                        # Extract placeholder
                        import re
                        placeholders = re.findall(r'\{(\w+)\}', value)
                        params.update(placeholders)
            
            # Check function_params for placeholders
            if source.function_params:
                for key, value in source.function_params.items():
                    if isinstance(value, str) and '{' in value and '}' in value:
                        import re
                        placeholders = re.findall(r'\{(\w+)\}', value)
                        params.update(placeholders)
        
        return JsonResponse({
            'success': True,
            'schema_name': schema_name,
            'expected_params': list(params),
            'sources_count': sources.count()
        })
        
    except ContextSchema.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Schema "{schema_name}" not found or inactive'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def schema_viewer(request):
    """Schema viewer page - browse all schemas and their sources"""
    schemas = ContextSchema.objects.all().prefetch_related('sources').order_by('-is_active', 'name')
    
    return render(request, 'bfagent/schema_viewer.html', {
        'schemas': schemas,
        'total_schemas': schemas.count(),
        'active_schemas': schemas.filter(is_active=True).count(),
        'title': 'Context Schema Viewer',
    })
