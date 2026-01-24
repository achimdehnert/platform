"""
Handler Test View
Interactive testing interface for ChapterGenerateHandler and CharacterEnrichHandler
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from apps.bfagent.handlers.processing_handlers import (
    ChapterGenerateHandler,
    CharacterEnrichHandler,
    LLMCallHandler,
)
from apps.bfagent.models import BookProjects, Characters, Agents, Llms


class HandlerTestView(View):
    """Test interface for new handlers"""
    
    def get(self, request):
        """Show test interface"""
        # Get available projects and characters
        projects = BookProjects.objects.all()[:10]
        characters = Characters.objects.all()[:10]
        agents = Agents.objects.filter(status='active')
        llms = Llms.objects.filter(is_active=True)
        
        context = {
            'projects': projects,
            'characters': characters,
            'agents': agents,
            'llms': llms,
        }
        
        return render(request, 'bfagent/handler_test.html', context)


@method_decorator(csrf_exempt, name='dispatch')
class HandlerExecuteView(View):
    """Execute handler actions via AJAX"""
    
    def post(self, request):
        """Execute handler action"""
        import json
        
        try:
            data = json.loads(request.body)
            handler_type = data.get('handler_type')
            action = data.get('action')
            project_id = data.get('project_id')
            
            # Initialize handler
            if handler_type == 'chapter':
                handler = ChapterGenerateHandler()
                context = {
                    'action': action,
                    'project_id': int(project_id),
                    'chapter_number': data.get('chapter_number', 1),
                    'parameters': {
                        'chapter_title': data.get('chapter_title', 'Chapter 1'),
                        'word_count_target': int(data.get('word_count', 3000)),
                        'plot_points': data.get('plot_points', '').split(',') if data.get('plot_points') else [],
                    }
                }
            elif handler_type == 'character':
                handler = CharacterEnrichHandler()
                context = {
                    'action': action,
                    'project_id': int(project_id),
                    'character_id': int(data.get('character_id')),
                    'parameters': data.get('parameters', {})
                }
            elif handler_type == 'llm':
                handler = LLMCallHandler()
                context = {
                    'system_prompt': data.get('system_prompt'),
                    'user_prompt': data.get('user_prompt'),
                    'max_tokens': int(data.get('max_tokens', 500)),
                }
            else:
                return JsonResponse({'success': False, 'error': 'Invalid handler type'})
            
            # Execute
            result = handler.execute(context)
            
            return JsonResponse({
                'success': True,
                'result': result,
            })
            
        except Exception as e:
            import traceback
            return JsonResponse({
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc(),
            })
