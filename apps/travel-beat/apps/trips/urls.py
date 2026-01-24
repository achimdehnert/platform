from django.urls import path
from . import views, wizard

app_name = 'trips'

urlpatterns = [
    # Landing & Dashboard
    path('', views.landing_page, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Trip Wizard (Multi-Step)
    path('new/', wizard.wizard_step1, name='wizard_step1'),
    path('new/stops/', wizard.wizard_step2, name='wizard_step2'),
    path('new/preferences/', wizard.wizard_step3, name='wizard_step3'),
    path('new/review/', wizard.wizard_step4, name='wizard_step4'),
    path('new/cancel/', wizard.wizard_cancel, name='wizard_cancel'),
    
    # Trip CRUD
    path('trips/', views.trip_list, name='trip_list'),
    path('trips/create/', views.trip_create, name='trip_create'),
    path('trips/<int:pk>/', views.trip_detail, name='trip_detail'),
    path('trips/<int:pk>/edit/', views.trip_edit, name='trip_edit'),
    path('trips/<int:pk>/delete/', views.trip_delete, name='trip_delete'),
    
    # Trip Actions
    path('trips/<int:pk>/calculate/', views.trip_calculate, name='trip_calculate'),
    path('trips/<int:pk>/generate/', views.trip_generate_story, name='trip_generate'),
    
    # HTMX Partials - Stops
    path('trips/<int:trip_id>/stops/add/', views.stop_add, name='stop_add'),
    path('stops/<int:pk>/edit/', views.stop_edit, name='stop_edit'),
    path('stops/<int:pk>/delete/', views.stop_delete, name='stop_delete'),
]
