"""
Views for the Idea Generation Wizard.
Implements the iterative feedback loop for project-type-specific idea generation.
"""
import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, DetailView

from .models import (
    ContentType, IdeaGenerationStep, IdeaSession, IdeaResponse
)


class IdeaWizardStartView(LoginRequiredMixin, TemplateView):
    """Start page: Select project type"""
    template_name = 'writing_hub/idea_wizard/start.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['content_types'] = ContentType.objects.filter(is_active=True).order_by('sort_order')
        context['recent_sessions'] = IdeaSession.objects.filter(
            user=self.request.user
        ).order_by('-updated_at')[:5]
        return context


class IdeaWizardCreateView(LoginRequiredMixin, View):
    """Create a new idea session for a content type"""
    
    def post(self, request, content_type_slug):
        content_type = get_object_or_404(ContentType, slug=content_type_slug, is_active=True)
        
        session = IdeaSession.objects.create(
            content_type=content_type,
            user=request.user,
            status=IdeaSession.Status.IN_PROGRESS,
            current_step=1
        )
        
        return redirect('writing_hub:idea-wizard-step', session_id=session.pk)


class IdeaWizardStepView(LoginRequiredMixin, DetailView):
    """Main wizard step view with feedback loop"""
    template_name = 'writing_hub/idea_wizard/step.html'
    model = IdeaSession
    pk_url_kwarg = 'session_id'
    context_object_name = 'session'
    
    def get_queryset(self):
        return IdeaSession.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.object
        
        # Get all steps for this content type
        all_steps = session.content_type.idea_steps.filter(is_active=True).order_by('sort_order')
        context['all_steps'] = all_steps
        context['total_steps'] = all_steps.count()
        
        # Current step
        current_step = all_steps.filter(step_number=session.current_step).first()
        if not current_step:
            current_step = all_steps.first()
        context['current_step'] = current_step
        
        # Get existing response for current step
        context['current_response'] = IdeaResponse.objects.filter(
            session=session,
            step=current_step,
            is_current=True
        ).first()
        
        # Get all accepted responses (for context display)
        context['accepted_responses'] = IdeaResponse.objects.filter(
            session=session,
            is_accepted=True
        ).select_related('step').order_by('step__sort_order')
        
        # Progress calculation
        context['progress'] = session.get_progress_percentage()
        
        # Response history for current step
        context['response_history'] = IdeaResponse.objects.filter(
            session=session,
            step=current_step
        ).order_by('-version')[:5]
        
        return context


class IdeaWizardSaveResponseView(LoginRequiredMixin, View):
    """Save user response for a step"""
    
    def post(self, request, session_id):
        session = get_object_or_404(IdeaSession, pk=session_id, user=request.user)
        
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        step_id = data.get('step_id')
        content = data.get('content', '').strip()
        source = data.get('source', IdeaResponse.Source.USER)
        accept = data.get('accept', False)
        
        if not step_id or not content:
            return JsonResponse({'error': 'Missing step_id or content'}, status=400)
        
        step = get_object_or_404(IdeaGenerationStep, pk=step_id, content_type=session.content_type)
        
        # Create new response (versioning handled in model.save())
        response = IdeaResponse.objects.create(
            session=session,
            step=step,
            content=content,
            source=source,
            is_accepted=accept
        )
        
        # If accepted, move to next step
        if accept:
            next_step = session.content_type.idea_steps.filter(
                is_active=True,
                sort_order__gt=step.sort_order
            ).order_by('sort_order').first()
            
            if next_step:
                session.current_step = next_step.step_number
            else:
                session.status = IdeaSession.Status.COMPLETED
                session.completed_at = timezone.now()
            session.save()
        
        return JsonResponse({
            'success': True,
            'response_id': response.pk,
            'version': response.version,
            'next_step': session.current_step,
            'is_complete': session.status == IdeaSession.Status.COMPLETED
        })


class IdeaWizardGenerateAIView(LoginRequiredMixin, View):
    """Generate AI suggestion for current step"""
    
    def post(self, request, session_id):
        session = get_object_or_404(IdeaSession, pk=session_id, user=request.user)
        
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        step_id = data.get('step_id')
        feedback = data.get('feedback', '')  # Optional refinement feedback
        
        step = get_object_or_404(IdeaGenerationStep, pk=step_id, content_type=session.content_type)
        
        if not step.can_generate_with_ai:
            return JsonResponse({'error': 'AI generation not available for this step'}, status=400)
        
        # Get context from previous responses
        context = self._build_context(session)
        
        # Build prompt
        prompt = self._build_prompt(step, context, feedback)
        
        # TODO: Call actual LLM service
        # For now, return a placeholder
        generated_content = self._generate_mock_content(step, context, feedback)
        
        # Save as AI-generated response
        response = IdeaResponse.objects.create(
            session=session,
            step=step,
            content=generated_content,
            source=IdeaResponse.Source.AI_REFINED if feedback else IdeaResponse.Source.AI,
            ai_prompt_used=prompt,
            user_feedback=feedback
        )
        
        return JsonResponse({
            'success': True,
            'content': generated_content,
            'response_id': response.pk,
            'version': response.version
        })
    
    def _build_context(self, session):
        """Build context from all accepted responses"""
        context = {}
        for resp in session.responses.filter(is_accepted=True).select_related('step'):
            context[resp.step.name] = {
                'name_de': resp.step.name_de,
                'content': resp.content
            }
        return context
    
    def _build_prompt(self, step, context, feedback):
        """Build the prompt for AI generation"""
        prompt_parts = [
            f"Generiere eine Idee für: {step.name_de}",
            f"Frage: {step.question_de}",
        ]
        
        if context:
            prompt_parts.append("\nBisherige Entscheidungen:")
            for name, data in context.items():
                prompt_parts.append(f"- {data['name_de']}: {data['content'][:200]}")
        
        if feedback:
            prompt_parts.append(f"\nUser-Feedback zur Verfeinerung: {feedback}")
        
        return "\n".join(prompt_parts)
    
    def _generate_mock_content(self, step, context, feedback):
        """Generate mock content (placeholder until LLM integration)"""
        # This is a placeholder - replace with actual LLM call
        mock_responses = {
            'moral': 'Wer anderen hilft, findet selbst Hilfe in der Not.',
            'protagonist': 'Ein junges Mädchen namens Luna, das bei ihrer strengen Großmutter aufwächst.',
            'antagonist': 'Eine eitle Hexe, die alle Schönheit für sich allein beansprucht.',
            'magic': 'Ein sprechender Spiegel, der nur die Wahrheit zeigt.',
            'trials': '1) Den Weg durch den Nebelwald finden\n2) Das Rätsel der drei Brücken lösen\n3) Das Herz der Hexe erweichen',
            'reward': 'Luna wird zur Hüterin des Waldes und findet eine neue Familie.',
            'core_conflict': 'Ein Mann muss entscheiden, ob er ein Geheimnis bewahrt oder die Wahrheit enthüllt.',
            'premise': 'Eine junge Wissenschaftlerin entdeckt, dass ihre Erfindung die Welt zerstören könnte.',
            'thesis': 'Künstliche Intelligenz wird die Kreativität des Menschen nicht ersetzen, sondern erweitern.',
        }
        
        base = mock_responses.get(step.name, f'[AI-generierter Vorschlag für {step.name_de}]')
        
        if feedback:
            base = f"{base}\n\n(Angepasst basierend auf Feedback: {feedback})"
        
        return base


class IdeaWizardSummaryView(LoginRequiredMixin, DetailView):
    """Final summary view after completing all steps"""
    template_name = 'writing_hub/idea_wizard/summary.html'
    model = IdeaSession
    pk_url_kwarg = 'session_id'
    context_object_name = 'session'
    
    def get_queryset(self):
        return IdeaSession.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # All accepted responses
        context['responses'] = IdeaResponse.objects.filter(
            session=self.object,
            is_accepted=True
        ).select_related('step').order_by('step__sort_order')
        
        return context


class IdeaWizardNavigateView(LoginRequiredMixin, View):
    """Navigate to a specific step"""
    
    def post(self, request, session_id):
        session = get_object_or_404(IdeaSession, pk=session_id, user=request.user)
        
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        step_number = data.get('step_number')
        
        if step_number:
            step = session.content_type.idea_steps.filter(
                is_active=True,
                step_number=step_number
            ).first()
            
            if step:
                session.current_step = step_number
                session.save()
                return JsonResponse({'success': True, 'current_step': step_number})
        
        return JsonResponse({'error': 'Invalid step'}, status=400)
