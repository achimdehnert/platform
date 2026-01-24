# apps/cad_hub/urls_brandschutz.py
"""
URL-Konfiguration für Brandschutz-Frontend.
"""
from django.urls import path

from .views_brandschutz import (
    BrandschutzDashboardView,
    BrandschutzPruefungListView,
    BrandschutzPruefungDetailView,
    BrandschutzPruefungCreateView,
    BrandschutzPruefungUpdateView,
    BrandschutzAnalyseView,
    BrandschutzReportView,
    BrandschutzMangelToggleView,
    BrandschutzSymbolApproveView,
    BrandschutzRegelwerkListView,
    BrandschutzStatsAPIView,
    BrandschutzSearchAPIView,
)

app_name = "brandschutz"

urlpatterns = [
    # Dashboard
    path("", BrandschutzDashboardView.as_view(), name="dashboard"),
    
    # Prüfungen
    path("pruefungen/", BrandschutzPruefungListView.as_view(), name="pruefung_list"),
    path("pruefungen/neu/", BrandschutzPruefungCreateView.as_view(), name="pruefung_create"),
    path("pruefungen/<uuid:pk>/", BrandschutzPruefungDetailView.as_view(), name="pruefung_detail"),
    path("pruefungen/<uuid:pk>/bearbeiten/", BrandschutzPruefungUpdateView.as_view(), name="pruefung_edit"),
    
    # Analyse
    path("analyse/", BrandschutzAnalyseView.as_view(), name="analyse"),
    path("analyse/<uuid:pk>/", BrandschutzAnalyseView.as_view(), name="analyse_pruefung"),
    
    # Reports
    path("pruefungen/<uuid:pk>/report/", BrandschutzReportView.as_view(), name="report_html"),
    path("pruefungen/<uuid:pk>/report/pdf/", BrandschutzReportView.as_view(), {"format": "pdf"}, name="report_pdf"),
    path("pruefungen/<uuid:pk>/report/excel/", BrandschutzReportView.as_view(), {"format": "excel"}, name="report_excel"),
    path("pruefungen/<uuid:pk>/report/json/", BrandschutzReportView.as_view(), {"format": "json"}, name="report_json"),
    
    # HTMX Partials
    path("maengel/<uuid:pk>/toggle/", BrandschutzMangelToggleView.as_view(), name="mangel_toggle"),
    path("symbole/<uuid:pk>/approve/", BrandschutzSymbolApproveView.as_view(), name="symbol_approve"),
    
    # Regelwerke
    path("regelwerke/", BrandschutzRegelwerkListView.as_view(), name="regelwerk_list"),
    
    # API
    path("api/stats/", BrandschutzStatsAPIView.as_view(), name="api_stats"),
    path("api/search/", BrandschutzSearchAPIView.as_view(), name="api_search"),
]
