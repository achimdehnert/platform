"""
Image Generation Views with Handler Integration
"""
import uuid
import asyncio
import logging

from django.views.generic import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.contrib import messages
from django import forms
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View

from ..models_illustration import (
    ImageStyleProfile,
    IllustrationImage,
    ImageStatus,
    ImageType,
    AIProvider,
)
from ..models import BookProjects, BookChapters  # GeneratedImage is new, use IllustrationImage for this view
from ..handlers.illustration_handler import ImageGenerationHandler, PromptEnhancer

logger = logging.getLogger(__name__)


class ImageGenerationForm(forms.Form):
    """Form for image generation"""
    project = forms.ModelChoiceField(
        queryset=BookProjects.objects.none(),
        required=False,  # Optional für Testing
        label="Book Project (Optional for Testing)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    chapter = forms.ModelChoiceField(
        queryset=BookChapters.objects.none(),
        required=False,
        label="Chapter (Optional)",
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Select chapter to associate this illustration with"
    )
    style_profile = forms.ModelChoiceField(
        queryset=ImageStyleProfile.objects.none(),
        required=False,
        label="Style Profile (Optional)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    image_type = forms.ChoiceField(
        choices=ImageType.choices,
        required=True,
        label="Image Type",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    prompt = forms.CharField(
        required=True,
        label="Description / Prompt",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Describe the image you want to generate...'
        })
    )
    negative_prompt = forms.CharField(
        required=False,
        label="Negative Prompt (Optional)",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Things to avoid in the image...'
        })
    )
    provider = forms.ChoiceField(
        choices=AIProvider.choices,
        initial=AIProvider.STABLE_DIFFUSION,  # Use Stable Diffusion by default (cheaper & works)
        label="AI Provider",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    quality = forms.ChoiceField(
        choices=[('standard', 'Standard'), ('hd', 'HD')],
        initial='standard',
        label="Quality",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    size = forms.ChoiceField(
        choices=[
            ('1024x1024', '1024x1024 (Square)'),
            ('1024x1792', '1024x1792 (Portrait)'),
            ('1792x1024', '1792x1024 (Landscape)'),
        ],
        initial='1024x1024',
        label="Size",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].queryset = BookProjects.objects.filter(user=user)
        self.fields['chapter'].queryset = BookChapters.objects.filter(project__user=user)
        self.fields['style_profile'].queryset = ImageStyleProfile.objects.filter(user=user)


class GenerateImageView(LoginRequiredMixin, FormView):
    """View for generating images with AI"""
    template_name = 'bfagent/illustration/generate_image.html'
    form_class = ImageGenerationForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_initial(self):
        """Pre-populate form if chapter is provided in URL"""
        initial = super().get_initial()
        chapter_id = self.request.GET.get('chapter')
        if chapter_id:
            try:
                # Try to get chapter - allow access if user owns it OR project has no user
                chapter = BookChapters.objects.select_related('project').get(pk=chapter_id)
                project = chapter.project
                
                # Check access: user owns project OR project has no owner
                if project.user is None or project.user == self.request.user:
                    initial['chapter'] = chapter
                    initial['project'] = project
                    # Suggest scene illustration for chapters
                    initial['image_type'] = ImageType.SCENE_ILLUSTRATION
                    
                    # Generate a suggested prompt from chapter content
                    if chapter.content:
                        # Take first 500 chars of content for context
                        content_preview = chapter.content[:500].strip()
                        suggested_prompt = f"Illustration für Kapitel {chapter.chapter_number}"
                        if chapter.title:
                            suggested_prompt += f": {chapter.title}"
                        suggested_prompt += f". Szene basierend auf: {content_preview}..."
                        initial['prompt'] = suggested_prompt
                    elif chapter.title:
                        # Fallback to title-based prompt
                        initial['prompt'] = f"Illustration für Kapitel {chapter.chapter_number}: {chapter.title}"
            except BookChapters.DoesNotExist:
                pass
        return initial
    
    def get_context_data(self, **kwargs):
        """Add chapter info to context for display"""
        context = super().get_context_data(**kwargs)
        chapter_id = self.request.GET.get('chapter')
        if chapter_id:
            try:
                chapter = BookChapters.objects.select_related('project').get(pk=chapter_id)
                project = chapter.project
                # Check access: user owns project OR project has no owner
                if project.user is None or project.user == self.request.user:
                    context['source_chapter'] = chapter
                    context['source_project'] = project
            except BookChapters.DoesNotExist:
                pass
        return context

    def form_valid(self, form):
        try:
            # Extract form data
            project = form.cleaned_data.get('project')  # Can be None for testing
            chapter = form.cleaned_data.get('chapter')  # Optional chapter link
            style_profile = form.cleaned_data.get('style_profile')
            image_type = form.cleaned_data['image_type']
            prompt = form.cleaned_data['prompt']
            negative_prompt = form.cleaned_data.get('negative_prompt', '')
            provider = form.cleaned_data['provider']
            quality = form.cleaned_data['quality']
            size = form.cleaned_data['size']

            # Enhance prompt if style profile is selected
            if style_profile:
                enhanced_prompt = PromptEnhancer.enhance_prompt(
                    base_prompt=prompt,
                    style_profile_prompt=style_profile.base_prompt,
                    image_type=image_type,
                    enhance=True
                )
                if style_profile.negative_prompt:
                    negative_prompt = PromptEnhancer.build_negative_prompt(
                        base_negative=style_profile.negative_prompt,
                        image_type=image_type
                    )
            else:
                enhanced_prompt = PromptEnhancer.enhance_prompt(
                    base_prompt=prompt,
                    image_type=image_type,
                    enhance=True
                )
                negative_prompt = PromptEnhancer.build_negative_prompt(
                    base_negative=negative_prompt,
                    image_type=image_type
                )

            # Initialize handler (mock_mode is controlled by settings/config)
            handler = ImageGenerationHandler()
            # Generate image (async with proper await)
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(
                    handler.generate_image(
                        prompt=enhanced_prompt,
                        provider=provider,
                        quality=quality,
                        size=size,
                        negative_prompt=negative_prompt if provider == 'stable_diffusion' else None,
                        num_images=1
                    )
                )
            except Exception as e:
                logger.error(f"Image generation error for user {self.request.user.username}: {str(e)}")
                messages.error(
                    self.request,
                    f"❌ Image generation failed: {str(e)}"
                )
                return self.form_invalid(form)

            # Save to database
            generated_images = []
            for result in results:
                image_id = f"img_{uuid.uuid4().hex[:12]}"

                generated_image = IllustrationImage.objects.create(
                    image_id=image_id,
                    user=self.request.user,
                    project=project,
                    chapter=chapter,  # Link to chapter if provided
                    style_profile=style_profile,
                    image_type=image_type,
                    status=ImageStatus.GENERATED,
                    provider_used=provider,
                    prompt_used=enhanced_prompt,
                    negative_prompt_used=negative_prompt if provider == 'stable_diffusion' else '',
                    image_url=result['image_url'],
                    resolution=result['size'],
                    quality=result['quality'],
                    generation_time_seconds=result['generation_time_seconds'],
                    # cost_usd is a @property - calculated automatically
                    content_context={}
                )
                generated_images.append(generated_image)

                # Update style profile usage
                if style_profile:
                    style_profile.usage_count += 1
                    style_profile.total_cost_usd += generated_image.cost_usd
                    style_profile.save()

            # Store first image ID for redirect
            self.generated_image_id = generated_images[0].pk if generated_images else None

            # Check if mock mode was used
            mock_indicator = " [MOCK MODE]" if handler.mock_mode else ""

            messages.success(
                self.request,
                f"✨ Image generated successfully{mock_indicator}! Cost: ${results[0]['cost_usd']:.4f}"
            )

            logger.info(
                f"Image generated successfully for user {self.request.user.username}: "
                f"Cost ${results[0]['cost_usd']:.4f}, Time {results[0]['generation_time_seconds']:.1f}s"
            )

            return super().form_valid(form)

        except Exception as e:
            logger.error(
                f"Image generation error for user {self.request.user.username}: {str(e)}",
                exc_info=True
            )
            messages.error(
                self.request,
                f"❌ Image generation failed: {str(e)}"
            )
            return self.form_invalid(form)

    def get_success_url(self):
        # Redirect to generated image detail if available
        if hasattr(self, 'generated_image_id') and self.generated_image_id:
            return reverse('bfagent:illustration:image-detail', kwargs={'pk': self.generated_image_id})
        # Fallback to gallery
        return reverse('bfagent:illustration:gallery')


@method_decorator(csrf_exempt, name='dispatch')
class ChapterPromptGeneratorView(LoginRequiredMixin, View):
    """API endpoint to generate illustration prompts from chapter content"""
    
    def post(self, request):
        try:
            import json
            data = json.loads(request.body)
            chapter_id = data.get('chapter_id')
            
            if not chapter_id:
                return JsonResponse({'error': 'Chapter ID required'}, status=400)
            
            # Get chapter
            try:
                chapter = BookChapters.objects.get(
                    pk=chapter_id, 
                    project__user=request.user
                )
            except BookChapters.DoesNotExist:
                return JsonResponse({'error': 'Chapter not found'}, status=404)
            
            # Generate prompt from chapter content
            prompt = self._generate_prompt_from_chapter(chapter)
            
            return JsonResponse({
                'success': True,
                'prompt': prompt,
                'chapter_title': chapter.title,
                'chapter_number': chapter.chapter_number
            })
            
        except Exception as e:
            logger.error(f"Error generating chapter prompt: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def _generate_prompt_from_chapter(self, chapter):
        """Generate illustration prompt from chapter content"""
        # For now, use rule-based generation
        # Later: integrate with OpenAI GPT for smart prompt generation
        
        content = chapter.content or ""
        title = chapter.title or f"Chapter {chapter.chapter_number}"
        
        # Extract key elements (simple keyword matching)
        keywords = {
            'forest': 'mystical forest with ancient trees',
            'castle': 'majestic castle with stone walls',
            'tavern': 'cozy medieval tavern interior',
            'battle': 'epic battle scene with warriors',
            'library': 'ancient library with towering bookshelves',
            'garden': 'peaceful garden with blooming flowers',
            'mountain': 'towering mountains shrouded in mist',
            'ocean': 'vast ocean with crashing waves',
            'village': 'quaint village with cobblestone streets',
            'night': 'moonlit scene with dramatic shadows',
            'dawn': 'golden dawn light breaking through',
            'storm': 'dramatic storm with lightning'
        }
        
        # Find matching keywords
        found_elements = []
        content_lower = content.lower()
        
        for keyword, description in keywords.items():
            if keyword in content_lower:
                found_elements.append(description)
        
        # Build prompt
        if found_elements:
            scene_description = ', '.join(found_elements[:3])  # Max 3 elements
            prompt = f"A detailed illustration of {scene_description}. "
        else:
            prompt = f"A scene from {title}: "
        
        # Add style and quality descriptors
        prompt += "High quality digital art, detailed textures, atmospheric lighting, "
        prompt += "rich colors, fantasy art style, cinematic composition."
        
        # Limit length
        if len(prompt) > 500:
            prompt = prompt[:497] + "..."
        
        return prompt
