"""
Public Views for Weltenhub
==========================

Landing page, Impressum, Datenschutz.
"""

from django.views.generic import TemplateView


class LandingView(TemplateView):
    """Landing page for Weltenforger."""

    template_name = "public/landing.html"


class ImpressumView(TemplateView):
    """Impressum page (IIL GmbH)."""

    template_name = "public/impressum.html"


class DatenschutzView(TemplateView):
    """Datenschutzerklärung page."""

    template_name = "public/datenschutz.html"
