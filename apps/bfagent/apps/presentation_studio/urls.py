"""
Presentation Studio URLs
Namespace wird in apps/bfagent/urls.py via Tuple-Syntax definiert
"""

from django.urls import path
from . import views
from . import views_research

# KEIN app_name hier - wird in bfagent/urls.py definiert!

urlpatterns = [
    path('', views.presentation_list, name='list'),
    path('upload/', views.upload_presentation, name='upload'),
    path('<uuid:pk>/', views.presentation_detail, name='detail'),
    path('<uuid:pk>/delete/', views.delete_presentation, name='delete_presentation'),
    path('<uuid:pk>/enhance/', views.enhance_presentation, name='enhance'),
    path('<uuid:pk>/download/', views.download_enhanced, name='download'),
    path('<uuid:pk>/slide/<int:slide_number>/', views.slide_viewer, name='slide_viewer'),
    path('<uuid:pk>/slide/<int:slide_number>/edit/', views.edit_slide, name='edit_slide'),
    path('<uuid:pk>/slide/<int:slide_number>/delete/', views.delete_slide, name='delete_slide'),
    # Preview Slides
    path('<uuid:pk>/preview/', views.get_preview_slides, name='get_preview_slides'),
    path('<uuid:pk>/preview/<uuid:preview_pk>/convert/', views.convert_preview_slide, name='convert_preview_slide'),
    path('<uuid:pk>/preview/convert-all/', views.convert_all_previews, name='convert_all_previews'),
    # Research Agent
    path('<uuid:pk>/research/', views_research.research_interface, name='research_interface'),
    path('<uuid:pk>/research/perform/', views_research.perform_research, name='perform_research'),
    path('<uuid:pk>/research/generate/', views_research.generate_slides_from_research, name='generate_slides_from_research'),
    path('<uuid:pk>/research/clear/', views_research.clear_research_slides, name='clear_research_slides'),
]
