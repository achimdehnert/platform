"""
URL Configuration for Context Enrichment
"""

from django.urls import path
from apps.bfagent.views.context_enrichment_views import (
    context_enrichment_tester,
    test_enrichment,
    schema_details,
    schema_params,
    schema_viewer,
)

app_name = 'context_enrichment'

urlpatterns = [
    # Main tester page
    path('tester/', context_enrichment_tester, name='tester'),
    
    # Schema viewer
    path('schemas/', schema_viewer, name='schema_viewer'),

    # API endpoints
    path('test/', test_enrichment, name='test'),
    path('schema/<int:schema_id>/', schema_details, name='schema_details'),
    path('params/<str:schema_name>/', schema_params, name='schema_params'),
]
