"""
Handler Generator API
REST API for AI-powered handler generation
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from apps.bfagent.agents.handler_generator.agent import HandlerGeneratorAgent
from apps.bfagent.services.handlers.config_models import HandlerRequirements, GeneratedHandler


@api_view(['POST'])
def generate_handler(request):
    """
    Generate handler from natural language description
    
    POST /api/handler-generator/generate/
    
    Body:
    {
        "description": "I need a handler that extracts text from PDF files",
        "auto_deploy": false,
        "llm_provider": "anthropic"  // optional, default: "anthropic"
    }
    
    Response:
    {
        "success": true,
        "requirements": {...},
        "generated": {
            "handler_code": "...",
            "config_model_code": "...",
            "test_code": "...",
            "documentation": "...",
            "example_usage": "..."
        },
        "validation": {
            "is_valid": true,
            "syntax_valid": true,
            "syntax_errors": [],
            "warnings": []
        },
        "deployed": false,
        "handler_id": null
    }
    """
    try:
        # Parse request
        data = request.data
        description = data.get('description')
        auto_deploy = data.get('auto_deploy', False)
        llm_provider = data.get('llm_provider', 'anthropic')
        
        if not description:
            return Response(
                {'error': 'description is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate handler
        agent = HandlerGeneratorAgent(llm_provider=llm_provider)
        result = agent.generate_handler(
            description=description,
            user=request.user if request.user.is_authenticated else None,
            auto_deploy=auto_deploy
        )
        
        # Format response
        response_data = {
            'success': True,
            'requirements': result['requirements'].model_dump(),
            'generated': {
                'handler_code': result['generated'].handler_code,
                'config_model_code': result['generated'].config_model_code,
                'test_code': result['generated'].test_code,
                'documentation': result['generated'].documentation,
                'example_usage': result['generated'].example_usage
            },
            'validation': result['validation'].model_dump(),
            'deployed': result['deployed'],
            'handler_id': result['handler'].handler_id if result['handler'] else None
        }
        
        if 'deployment_error' in result:
            response_data['deployment_error'] = result['deployment_error']
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def deploy_handler(request):
    """
    Deploy a generated handler
    
    POST /api/handler-generator/deploy/
    
    Body:
    {
        "requirements": {...},  // HandlerRequirements dict
        "generated": {...}      // GeneratedHandler dict
    }
    
    Response:
    {
        "success": true,
        "handler_id": "pdf_extractor",
        "message": "Handler deployed successfully"
    }
    """
    try:
        data = request.data
        
        # Parse and validate
        requirements = HandlerRequirements.model_validate(data['requirements'])
        generated = GeneratedHandler.model_validate(data['generated'])
        
        # Deploy
        agent = HandlerGeneratorAgent()
        handler = agent.deploy_handler(
            requirements=requirements,
            generated=generated,
            user=request.user if request.user.is_authenticated else None
        )
        
        return Response({
            'success': True,
            'handler_id': handler.handler_id,
            'message': 'Handler deployed successfully'
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def regenerate_handler(request):
    """
    Regenerate handler with feedback
    
    POST /api/handler-generator/regenerate/
    
    Body:
    {
        "requirements": {...},
        "feedback": "Make it faster and add caching"
    }
    
    Response:
    {
        "success": true,
        "generated": {...}
    }
    """
    try:
        data = request.data
        
        requirements = HandlerRequirements.model_validate(data['requirements'])
        feedback = data.get('feedback', '')
        
        agent = HandlerGeneratorAgent()
        generated = agent.regenerate_handler(
            requirements=requirements,
            feedback=feedback
        )
        
        return Response({
            'success': True,
            'generated': {
                'handler_code': generated.handler_code,
                'config_model_code': generated.config_model_code,
                'test_code': generated.test_code,
                'documentation': generated.documentation,
                'example_usage': generated.example_usage
            }
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def generator_status(request):
    """
    Get generator status and capabilities
    
    GET /api/handler-generator/status/
    
    Response:
    {
        "available": true,
        "llm_providers": ["anthropic", "openai"],
        "supported_categories": ["input", "processing", "output"],
        "features": [...]
    }
    """
    return Response({
        'available': True,
        'llm_providers': ['anthropic', 'openai'],
        'supported_categories': ['input', 'processing', 'output'],
        'features': [
            'Natural language to handler',
            'Type-safe with Pydantic',
            'Structured LLM outputs',
            'Transaction-safe deployment',
            'Automatic testing',
            'Complete documentation',
            'Syntax validation',
            'Regeneration with feedback'
        ],
        'version': '1.0.0'
    }, status=status.HTTP_200_OK)
