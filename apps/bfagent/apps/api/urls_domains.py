"""
URL Configuration for Domains API
"""
from django.urls import path

from .views import domains_list

urlpatterns = [
    path("", domains_list, name="api_domains_list"),
]
