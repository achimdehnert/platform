"""
PPTX-Hub Django Integration.

A Django app for processing PowerPoint presentations with
multi-tenancy support, REST API, and async job processing.

Installation:
    1. Add 'pptx_hub.django' to INSTALLED_APPS
    2. Configure PPTX_HUB settings
    3. Run migrations: python manage.py migrate pptx_hub
    4. Include URLs: path('api/pptx-hub/', include('pptx_hub.django.urls'))
"""

default_app_config = "pptx_hub.django.apps.PptxHubConfig"
