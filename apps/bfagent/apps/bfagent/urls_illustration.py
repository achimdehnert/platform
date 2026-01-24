"""
URL Configuration for Illustration System
"""
from django.urls import path
from apps.bfagent.views import illustration_views, illustration_generation_views, auto_illustration_views

app_name = 'illustration'

urlpatterns = [
    # Image Assignment API
    path('api/assign-to-chapter/', illustration_views.assign_image_to_chapter,
         name='assign-to-chapter'),
    
    # Auto-Illustration (MVP - Synchronous, no Celery required)
    path('chapter/<int:chapter_id>/auto-illustrate/', 
         auto_illustration_views.auto_illustrate_chapter_sync,
         name='auto-illustrate-chapter'),
    
    # Auto-Illustration (Production - Async with Celery)
    path('chapter/<int:chapter_id>/auto-illustrate-async/', 
         auto_illustration_views.auto_illustrate_chapter_async,
         name='auto-illustrate-chapter-async'),
    path('task/<str:task_id>/status/', 
         auto_illustration_views.auto_illustrate_task_status,
         name='auto-illustrate-status'),
    
    # Existing URLs:
    # Style Profiles
    path('styles/', illustration_views.StyleProfileListView.as_view(),
         name='style-list'),
    path('styles/<int:pk>/', illustration_views.StyleProfileDetailView.as_view(),
         name='style-detail'),
    path('styles/create/', illustration_views.StyleProfileCreateView.as_view(),
         name='style-create'),

    # Image Generation
    path('generate/', illustration_generation_views.GenerateImageView.as_view(),
         name='generate'),
    path('generate-chapter-prompt/', illustration_generation_views.ChapterPromptGeneratorView.as_view(),
         name='generate-chapter-prompt'),

    # Generated Images
    path('gallery/', illustration_views.GeneratedImageListView.as_view(),
         name='gallery'),
    path('chapter/<int:chapter_id>/gallery/', illustration_views.ChapterImageGalleryView.as_view(),
         name='chapter-gallery'),
    path('images/<int:pk>/', illustration_views.GeneratedImageDetailView.as_view(),
         name='image-detail'),
]
