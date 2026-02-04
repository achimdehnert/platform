"""
Public URLs for Weltenhub
=========================
"""

from django.urls import path

from .views import LandingView, ImpressumView, DatenschutzView


app_name = "public"

urlpatterns = [
    path("", LandingView.as_view(), name="landing"),
    path("impressum/", ImpressumView.as_view(), name="impressum"),
    path("datenschutz/", DatenschutzView.as_view(), name="datenschutz"),
]
