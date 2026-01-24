"""
URL configuration for Expert Hub - Explosionsschutz Analyse
"""

from django.urls import path

from . import views

app_name = "expert_hub"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),
    
    # Sessions
    path("sessions/", views.session_list, name="session_list"),
    path("sessions/new/", views.session_create, name="session_create"),
    path("sessions/<uuid:session_id>/", views.session_detail, name="session_detail"),
    
    # Zone Analysis
    path("zone-analysis/", views.zone_analysis, name="zone_analysis"),
    path("sessions/<uuid:session_id>/zone-analysis/", views.zone_analysis, name="session_zone_analysis"),
    
    # Substance Search
    path("substances/", views.substance_search, name="substance_search"),
    path("api/substances/", views.substance_api, name="substance_api"),
    
    # Equipment Check
    path("equipment/", views.equipment_check, name="equipment_check"),
    path("sessions/<uuid:session_id>/equipment/", views.equipment_check, name="session_equipment_check"),
    
    # Ventilation Analysis
    path("ventilation/", views.ventilation_analysis, name="ventilation_analysis"),
    
    # CAD Import
    path("cad-import/", views.cad_import, name="cad_import"),
    path("sessions/<uuid:session_id>/cad-import/", views.cad_import, name="session_cad_import"),
    
    # Document Upload
    path("sessions/<uuid:session_id>/upload/", views.session_upload_document, name="session_upload_document"),
    
    # Phase Detail
    path("sessions/<uuid:session_id>/phase/<int:phase_id>/", views.phase_detail, name="phase_detail"),
    
    # API Endpoints
    path("api/zone-calculate/", views.api_zone_calculate, name="api_zone_calculate"),
    path("api/equipment-check/", views.api_equipment_check, name="api_equipment_check"),
    
    # Document Export
    path("sessions/<uuid:session_id>/document/preview/", views.document_preview, name="document_preview"),
    path("sessions/<uuid:session_id>/document/export/", views.document_export, name="document_export"),
    
    # Corporate Design Template
    path("sessions/<uuid:session_id>/template/upload/", views.upload_template, name="upload_template"),
    path("sessions/<uuid:session_id>/template/remove/", views.remove_template, name="remove_template"),
    
    # HTMX API
    path("api/sessions/<uuid:session_id>/phase/<int:phase_id>/ai-generate/", views.api_ai_generate, name="api_ai_generate"),
]
