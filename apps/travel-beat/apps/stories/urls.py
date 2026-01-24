from django.urls import path
from . import views

app_name = 'stories'

urlpatterns = [
    # Story List & Detail
    path('', views.story_list, name='list'),
    path('<int:pk>/', views.story_detail, name='detail'),
    
    # Reading
    path('<int:pk>/read/', views.story_read, name='read'),
    path('<int:story_id>/chapter/<int:chapter_num>/', views.chapter_read, name='chapter'),
    
    # Generation Progress
    path('<int:pk>/progress/', views.story_progress, name='progress'),
    
    # Export
    path('<int:pk>/export/markdown/', views.export_markdown, name='export_markdown'),
    path('<int:pk>/export/pdf/', views.export_pdf, name='export_pdf'),
    
    # API
    path('api/<int:pk>/status/', views.api_story_status, name='api_status'),
]
