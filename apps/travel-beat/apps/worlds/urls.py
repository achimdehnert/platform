from django.urls import path
from . import views

app_name = 'worlds'

urlpatterns = [
    # World Overview
    path('', views.world_detail, name='detail'),
    
    # Characters
    path('characters/', views.character_list, name='character_list'),
    path('characters/add/', views.character_add, name='character_add'),
    path('characters/<int:pk>/edit/', views.character_edit, name='character_edit'),
    path('characters/<int:pk>/delete/', views.character_delete, name='character_delete'),
    
    # Places
    path('places/', views.place_list, name='place_list'),
    path('places/add/', views.place_add, name='place_add'),
    path('places/<int:pk>/edit/', views.place_edit, name='place_edit'),
    path('places/<int:pk>/delete/', views.place_delete, name='place_delete'),
    
    # Settings
    path('settings/', views.world_settings, name='settings'),
]
