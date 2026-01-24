from django.urls import path
from . import views

app_name = 'locations'

urlpatterns = [
    path('', views.location_list, name='list'),
    path('<int:pk>/', views.location_detail, name='detail'),
    
    # API
    path('api/search/', views.location_search, name='api_search'),
    path('api/generate/', views.location_generate, name='api_generate'),
]
