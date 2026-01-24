"""Image Gallery Views"""

from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count, Sum, Avg
from django.shortcuts import get_object_or_404
from apps.bfagent.models import GeneratedImage


class ImageGalleryView(LoginRequiredMixin, ListView):
    """
    Grid view of all generated images.
    
    Features:
    - Grid layout with thumbnails
    - Filter by provider, date, book
    - Search prompts
    - Sort by cost, date, time
    """
    model = GeneratedImage
    template_name = 'bfagent/images/gallery.html'
    context_object_name = 'images'
    paginate_by = 24
    
    def get_queryset(self):
        qs = GeneratedImage.objects.filter(is_active=True)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(
                Q(prompt__icontains=search) |
                Q(revised_prompt__icontains=search) |
                Q(scene_description__icontains=search)
            )
        
        # Filter by provider
        provider = self.request.GET.get('provider')
        if provider:
            qs = qs.filter(provider=provider)
        
        # Filter by book
        book_id = self.request.GET.get('book_id')
        if book_id:
            qs = qs.filter(book_id=book_id)
        
        # Filter by favorites
        if self.request.GET.get('favorites') == 'true':
            qs = qs.filter(is_favorite=True)
        
        # Sort
        sort = self.request.GET.get('sort', '-created_at')
        valid_sorts = [
            '-created_at', 'created_at',
            '-cost_cents', 'cost_cents',
            '-generation_time_seconds', 'generation_time_seconds',
        ]
        if sort in valid_sorts:
            qs = qs.order_by(sort)
        
        return qs.select_related('handler', 'created_by')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Stats
        images = GeneratedImage.objects.filter(is_active=True)
        context['stats'] = {
            'total_images': images.count(),
            'total_cost': images.aggregate(Sum('cost_cents'))['cost_cents__sum'] or 0,
            'avg_cost': images.aggregate(Avg('cost_cents'))['cost_cents__avg'] or 0,
            'avg_time': images.aggregate(Avg('generation_time_seconds'))['generation_time_seconds__avg'] or 0,
            'by_provider': images.values('provider').annotate(count=Count('image_id')).order_by('-count'),
        }
        
        # Filter options
        context['providers'] = GeneratedImage.PROVIDER_CHOICES
        context['books'] = images.filter(book_id__isnull=False).values('book_id').distinct()
        
        # Current filters
        context['current_search'] = self.request.GET.get('search', '')
        context['current_provider'] = self.request.GET.get('provider', '')
        context['current_sort'] = self.request.GET.get('sort', '-created_at')
        
        return context


class ImageDetailView(LoginRequiredMixin, DetailView):
    """
    Detailed view of single image.
    
    Shows:
    - Full size image
    - All metadata
    - Generation details
    - Cost & performance
    - Book/chapter info
    """
    model = GeneratedImage
    template_name = 'bfagent/images/detail.html'
    context_object_name = 'image'
    pk_url_kwarg = 'image_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Related images (same book or similar prompt)
        obj = self.object
        related = GeneratedImage.objects.filter(is_active=True).exclude(image_id=obj.image_id)
        
        if obj.book_id:
            # Same book images
            context['related_images'] = related.filter(book_id=obj.book_id)[:6]
        else:
            # Similar images (same provider or style)
            context['related_images'] = related.filter(
                Q(provider=obj.provider) | Q(style=obj.style)
            )[:6]
        
        return context


class BookIllustrationsView(LoginRequiredMixin, ListView):
    """
    View all illustrations for a specific book.
    
    Organized by chapter and scene.
    """
    model = GeneratedImage
    template_name = 'bfagent/images/book_illustrations.html'
    context_object_name = 'illustrations'
    
    def get_queryset(self):
        book_id = self.kwargs.get('book_id')
        return GeneratedImage.objects.filter(
            book_id=book_id,
            is_active=True
        ).order_by('chapter_id', 'scene_number')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book_id = self.kwargs.get('book_id')
        
        context['book_id'] = book_id
        
        # Group by chapter
        illustrations = context['illustrations']
        chapters = {}
        for img in illustrations:
            ch_id = img.chapter_id or 0
            if ch_id not in chapters:
                chapters[ch_id] = []
            chapters[ch_id].append(img)
        context['chapters'] = dict(sorted(chapters.items()))
        
        # Stats
        context['stats'] = {
            'total_illustrations': illustrations.count(),
            'total_cost': sum(img.cost_cents for img in illustrations) / 100,
            'total_time': sum(img.generation_time_seconds for img in illustrations),
            'providers': illustrations.values('provider').annotate(count=Count('image_id')),
        }
        
        return context