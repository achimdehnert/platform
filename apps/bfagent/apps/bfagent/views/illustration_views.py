"""
Views for AI-Powered Illustration System
"""
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from ..models_illustration import (
    ImageStyleProfile,
    IllustrationImage,
)
from ..models import BookChapters
from ..mixins.illustration_permissions import (
    IllustrationOwnerMixin,
    IllustrationListOwnerFilterMixin,
)


class StyleProfileListView(LoginRequiredMixin, IllustrationListOwnerFilterMixin, ListView):
    model = ImageStyleProfile
    template_name = 'bfagent/illustration/style_profile_list.html'
    context_object_name = 'style_profiles'
    paginate_by = 12

    def get_queryset(self):
        # Use mixin's filtering, then apply ordering
        return super().get_queryset().order_by('-created_at')


class StyleProfileDetailView(LoginRequiredMixin, IllustrationOwnerMixin, DetailView):
    model = ImageStyleProfile
    template_name = 'bfagent/illustration/style_profile_detail.html'
    context_object_name = 'style_profile'


class StyleProfileCreateView(LoginRequiredMixin, CreateView):
    model = ImageStyleProfile
    template_name = 'bfagent/illustration/style_profile_form.html'
    fields = ['display_name', 'description', 'project', 'art_style', 'color_mood',
              'base_prompt', 'negative_prompt', 'default_quality', 'preferred_provider']

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.style_id = form.instance.display_name.lower().replace(' ', '_')[:50]
        messages.success(self.request, "Style Profile created!")
        return super().form_valid(form)

    def get_success_url(self):
        # Redirect to styles list - detail view accessible from there
        return '/bookwriting/illustrations/styles/'


class GeneratedImageListView(LoginRequiredMixin, IllustrationListOwnerFilterMixin, ListView):
    model = IllustrationImage
    template_name = 'bfagent/illustration/image_gallery.html'
    context_object_name = 'images'
    paginate_by = 50  # Increased to show more images for grouping

    def get_queryset(self):
        # Use mixin's filtering, then select related chapter for efficiency
        return super().get_queryset().select_related('chapter').order_by('chapter__chapter_number', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Group images by chapter
        from collections import defaultdict
        images_by_chapter = defaultdict(list)
        unassigned_images = []
        
        for image in context['images']:
            if image.chapter:
                chapter_key = f"Chapter {image.chapter.chapter_number}"
                if image.chapter.title:
                    chapter_key += f": {image.chapter.title}"
                images_by_chapter[chapter_key].append(image)
            else:
                unassigned_images.append(image)
        
        context['images_by_chapter'] = dict(images_by_chapter)
        context['unassigned_images'] = unassigned_images
        
        # Get all user's books for filter
        from ..models import BookProjects
        user_books = BookProjects.objects.filter(user=self.request.user).order_by('-updated_at')
        context['user_books'] = user_books
        
        # Filter chapters by selected book (if any)
        selected_book_id = self.request.GET.get('book')
        if selected_book_id:
            all_chapters = BookChapters.objects.filter(
                project__user=self.request.user,
                project__pk=selected_book_id
            ).select_related('project').order_by('chapter_number')
            context['selected_book_id'] = int(selected_book_id)
        else:
            # Show chapters from most recent book by default
            if user_books.exists():
                recent_book = user_books.first()
                all_chapters = BookChapters.objects.filter(
                    project=recent_book
                ).select_related('project').order_by('chapter_number')
                context['selected_book_id'] = recent_book.pk
            else:
                all_chapters = BookChapters.objects.none()
                context['selected_book_id'] = None
        
        context['all_chapters'] = all_chapters
        
        return context


class GeneratedImageDetailView(LoginRequiredMixin, IllustrationOwnerMixin, DetailView):
    model = IllustrationImage
    template_name = 'bfagent/illustration/image_detail.html'
    context_object_name = 'image'


class ChapterImageGalleryView(LoginRequiredMixin, ListView):
    """Gallery view for chapter-specific illustrations"""
    model = IllustrationImage
    template_name = 'bfagent/illustration/chapter_gallery.html'
    context_object_name = 'images'
    paginate_by = 24

    def get_queryset(self):
        """Filter images by chapter and user"""
        chapter_id = self.kwargs.get('chapter_id')
        
        # Get chapter and verify ownership
        try:
            chapter = BookChapters.objects.get(pk=chapter_id, project__user=self.request.user)
        except BookChapters.DoesNotExist:
            return IllustrationImage.objects.none()
        
        # Return all images for this chapter owned by user
        return IllustrationImage.objects.filter(
            chapter=chapter,
            user=self.request.user
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        """Add chapter to context"""
        context = super().get_context_data(**kwargs)
        chapter_id = self.kwargs.get('chapter_id')
        
        try:
            context['chapter'] = BookChapters.objects.get(pk=chapter_id, project__user=self.request.user)
        except BookChapters.DoesNotExist:
            context['chapter'] = None
        
        return context


@login_required
@require_POST
def assign_image_to_chapter(request):
    """
    API endpoint to assign an image to a chapter via drag-and-drop
    
    Expected POST data:
    - image_id: ID of the IllustrationImage
    - chapter_id: ID of the BookChapter
    
    Returns JSON:
    - success: boolean
    - message: string
    - chapter_number: int (if successful)
    """
    import json
    
    try:
        data = json.loads(request.body)
        image_id = data.get('image_id')
        chapter_id = data.get('chapter_id')
        
        if not image_id or not chapter_id:
            return JsonResponse({
                'success': False,
                'error': 'Missing image_id or chapter_id'
            }, status=400)
        
        # Get and verify ownership of image
        image = get_object_or_404(IllustrationImage, pk=image_id, user=request.user)
        
        # Get and verify ownership of chapter
        chapter = get_object_or_404(
            BookChapters,
            pk=chapter_id,
            project__user=request.user
        )
        
        # Assign image to chapter
        image.chapter = chapter
        image.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Image assigned to Chapter {chapter.chapter_number}',
            'chapter_number': chapter.chapter_number,
            'chapter_title': chapter.title or f'Chapter {chapter.chapter_number}'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
