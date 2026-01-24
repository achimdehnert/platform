"""
Handler Generator Web UI Views
Provides a visual interface for the AI-powered handler generator
"""

from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_http_methods
from apps.bfagent.agents.handler_generator.agent import generate_handler_from_description
import traceback


@require_http_methods(["GET"])
def handler_generator_dashboard(request: HttpRequest) -> HttpResponse:
    """
    Handler Generator Dashboard - Main UI
    """
    return render(request, 'bfagent/handler_generator_dashboard.html', {
        'page_title': 'Handler Generator',
    })


@require_http_methods(["POST"])
def handler_generator_generate(request: HttpRequest) -> HttpResponse:
    """
    Generate handler from description via HTMX
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Handler Generator: Method={request.method}")
    logger.info(f"Handler Generator: POST data={request.POST}")
    
    description = request.POST.get('description', '').strip()
    llm_provider = request.POST.get('llm_provider', 'anthropic')
    auto_deploy = request.POST.get('auto_deploy') == 'on'
    
    logger.info(f"Handler Generator: description length={len(description)}")
    
    # Validate input
    if not description:
        return render(request, 'bfagent/handler_generator_results.html', {
            'success': False,
            'error_message': 'Please provide a handler description',
        })
    
    try:
        # Generate handler
        result = generate_handler_from_description(
            description=description,
            auto_deploy=auto_deploy,
            llm_provider=llm_provider
        )
        
        # Prepare code preview (first 50 lines)
        handler_code_lines = result['generated'].handler_code.split('\n')
        handler_code_preview = '\n'.join(handler_code_lines[:50])
        if len(handler_code_lines) > 50:
            handler_code_preview += f"\n\n... ({len(handler_code_lines) - 50} more lines)"
        
        return render(request, 'bfagent/handler_generator_results.html', {
            'success': True,
            'requirements': result['requirements'],
            'generated': result['generated'],
            'validation': result['validation'],
            'deployed': result.get('deployed', False),
            'handler_id': result['handler'].id if result.get('handler') else None,
            'handler_code_preview': handler_code_preview,
        })
        
    except Exception as e:
        error_details = traceback.format_exc()
        
        return render(request, 'bfagent/handler_generator_results.html', {
            'success': False,
            'error_message': str(e),
            'error_details': error_details,
        })


@require_http_methods(["POST"])
def handler_generator_deploy(request: HttpRequest) -> HttpResponse:
    """
    Deploy a previously generated handler
    """
    handler_id = request.POST.get('handler_id', '').strip()
    
    if not handler_id:
        return render(request, 'bfagent/handler_generator_results.html', {
            'success': False,
            'error_message': 'Handler ID is required for deployment',
        })
    
    try:
        from pathlib import Path
        from apps.bfagent.models_handlers import Handler
        
        # Look for generated files
        project_root = Path(__file__).resolve().parents[3]
        handler_file = project_root / f"generated_{handler_id}_handler.py"
        config_file = project_root / f"generated_{handler_id}_config.py"
        test_file = project_root / f"generated_{handler_id}_tests.py"
        
        if not handler_file.exists():
            return render(request, 'bfagent/handler_generator_results.html', {
                'success': False,
                'error_message': 'Handler files not found. Please regenerate the handler with auto-deploy enabled.',
            })
        
        # Read the generated files
        handler_code = handler_file.read_text(encoding='utf-8')
        config_code = config_file.read_text(encoding='utf-8') if config_file.exists() else ""
        test_code = test_file.read_text(encoding='utf-8') if test_file.exists() else ""
        
        # Extract class name from handler code (simple parsing)
        class_name = handler_id.replace('_', ' ').title().replace(' ', '') + 'Handler'
        
        # Create handler record in database with proper fields
        handler = Handler.objects.create(
            handler_id=handler_id,
            display_name=handler_id.replace('_', ' ').title(),
            description="AI-generated handler from natural language description",
            category='processing',
            module_path=f'generated_{handler_id}_handler',
            class_name=class_name,
            version='1.0.0',
            is_active=True,
            is_experimental=True
        )
        
        return render(request, 'bfagent/handler_generator_results.html', {
            'success': True,
            'deployed': True,
            'handler_id': handler.id,
            'requirements': {'handler_id': handler_id},
            'generated': {
                'handler_code': handler_code,
                'config_code': config_code,
                'test_code': test_code
            },
            'validation': {'is_valid': True},
            'handler_code_preview': '\n'.join(handler_code.split('\n')[:50])
        })
        
    except Exception as e:
        error_details = traceback.format_exc()
        return render(request, 'bfagent/handler_generator_results.html', {
            'success': False,
            'error_message': f'Deployment failed: {str(e)}',
            'error_details': error_details,
        })
