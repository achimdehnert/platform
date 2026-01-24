# apps/cad_hub/urls.py
"""
URL-Routing für IFC Dashboard
"""
from django.urls import path, include

from . import views
from . import views_avb
from . import views_dxf
from . import views_nl2cad
from . import views_analysis

app_name = "cad_hub"

urlpatterns = [
    # Dashboard
    path("", views.DashboardView.as_view(), name="dashboard"),
    # Projekte
    path("projects/", views.ProjectListView.as_view(), name="project_list"),
    path("project/<uuid:pk>/", views.ProjectDetailView.as_view(), name="project_detail"),
    path("project/create/", views.ProjectCreateView.as_view(), name="project_create"),
    path("project/<uuid:pk>/edit/", views.ProjectUpdateView.as_view(), name="project_edit"),
    path("project/<uuid:pk>/delete/", views.ProjectDeleteView.as_view(), name="project_delete"),
    # Modelle
    path("model/<uuid:pk>/", views.ModelDetailView.as_view(), name="model_detail"),
    path("model/<uuid:pk>/viewer/", views.ModelViewerView.as_view(), name="model_viewer"),
    path(
        "model/<uuid:pk>/content/",
        views.IFCContentOverviewView.as_view(),
        name="ifc_content_overview",
    ),
    path("model/<uuid:pk>/delete/", views.ModelDeleteView.as_view(), name="model_delete"),
    path("project/<uuid:project_id>/upload/", views.ModelUploadView.as_view(), name="model_upload"),
    path("project/<uuid:project_id>/cad-upload/", views.CADUploadView.as_view(), name="cad_upload"),
    # Räume (HTMX Partials)
    path("model/<uuid:model_id>/rooms/", views.RoomListView.as_view(), name="room_list"),
    path("room/<uuid:pk>/", views.RoomDetailView.as_view(), name="room_detail"),
    # Fenster, Türen, Wände, Decken
    path("model/<uuid:model_id>/windows/", views.WindowListView.as_view(), name="window_list"),
    path("model/<uuid:model_id>/doors/", views.DoorListView.as_view(), name="door_list"),
    path("model/<uuid:model_id>/walls/", views.WallListView.as_view(), name="wall_list"),
    path("model/<uuid:model_id>/slabs/", views.SlabListView.as_view(), name="slab_list"),
    # Flächen
    path("model/<uuid:model_id>/areas/", views.AreaSummaryView.as_view(), name="area_summary"),
    path("model/<uuid:model_id>/woflv/", views.WoFlVSummaryView.as_view(), name="woflv_summary"),
    # Export
    path(
        "model/<uuid:model_id>/export/", views.ExportRaumbuchView.as_view(), name="export_raumbuch"
    ),
    path(
        "model/<uuid:model_id>/export/woflv/", views.ExportWoFlVView.as_view(), name="export_woflv"
    ),
    path("model/<uuid:model_id>/export/gaeb/", views.ExportGAEBView.as_view(), name="export_gaeb"),
    path("model/<uuid:model_id>/export/x83/", views.ExportX83View.as_view(), name="export_x83"),
    
    # ==========================================================================
    # AVB: Ausschreibung, Vergabe, Bauausführung
    # ==========================================================================
    
    # Bauprojekte
    path("avb/projects/", views_avb.ConstructionProjectListView.as_view(), name="avb_project_list"),
    path("avb/project/<uuid:pk>/", views_avb.ConstructionProjectDetailView.as_view(), name="avb_project_detail"),
    path("avb/project/create/", views_avb.ConstructionProjectCreateView.as_view(), name="avb_project_create"),
    path("avb/project/<uuid:pk>/edit/", views_avb.ConstructionProjectUpdateView.as_view(), name="avb_project_edit"),
    
    # Ausschreibungen
    path("avb/tenders/", views_avb.TenderListView.as_view(), name="tender_list"),
    path("avb/tender/<uuid:pk>/", views_avb.TenderDetailView.as_view(), name="tender_detail"),
    path("avb/tender/create/", views_avb.TenderCreateView.as_view(), name="tender_create"),
    path("avb/tender/<uuid:pk>/publish/", views_avb.TenderPublishView.as_view(), name="tender_publish"),
    path("avb/tender/<uuid:pk>/comparison/", views_avb.PriceComparisonView.as_view(), name="price_comparison"),
    path("avb/tender/<uuid:pk>/export/comparison/", views_avb.ExportPriceComparisonView.as_view(), name="export_price_comparison"),
    path("avb/tender/<uuid:pk>/export/gaeb/", views_avb.ExportTenderGAEBView.as_view(), name="export_tender_gaeb"),
    path("avb/tender/<uuid:pk>/stats/", views_avb.TenderStatsAPIView.as_view(), name="tender_stats_api"),
    
    # Aus IFC erstellen
    path("model/<uuid:model_id>/create-tender/", views_avb.TenderFromIFCView.as_view(), name="create_tender_from_ifc"),
    
    # Bieter
    path("avb/bidders/", views_avb.BidderListView.as_view(), name="bidder_list"),
    path("avb/bidder/<uuid:pk>/", views_avb.BidderDetailView.as_view(), name="bidder_detail"),
    path("avb/bidder/create/", views_avb.BidderCreateView.as_view(), name="bidder_create"),
    
    # Angebote
    path("avb/tender/<uuid:tender_id>/bids/", views_avb.BidListView.as_view(), name="bid_list"),
    path("avb/bid/<uuid:pk>/", views_avb.BidDetailView.as_view(), name="bid_detail"),
    path("avb/tender/<uuid:tender_id>/bid/invite/", views_avb.BidCreateView.as_view(), name="bid_invite"),
    path("avb/bid/<uuid:pk>/receive/", views_avb.BidReceiveView.as_view(), name="bid_receive"),
    
    # Vergabe
    path("avb/tender/<uuid:tender_id>/bid/<uuid:bid_id>/award/", views_avb.AwardCreateView.as_view(), name="award_create"),
    
    # ==========================================================================
    # DXF: Viewer, Parser, NL2DXF
    # ==========================================================================
    
    path("dxf/", views_dxf.DXFViewerView.as_view(), name="dxf_viewer"),
    path("dxf/upload/", views_dxf.DXFUploadView.as_view(), name="dxf_upload"),
    path("dxf/render-svg/", views_dxf.DXFRenderSVGView.as_view(), name="dxf_render_svg"),
    path("dxf/parse/", views_dxf.DXFParseView.as_view(), name="dxf_parse"),
    path("dxf/nl2dxf/", views_dxf.NL2DXFView.as_view(), name="nl2dxf"),
    path("dxf/nl2dxf/generate/", views_dxf.NL2DXFGenerateView.as_view(), name="nl2dxf_generate"),
    path("dxf/download/", views_dxf.DXFDownloadView.as_view(), name="dxf_download"),
    
    # DXF Analyse
    path("dxf/analyze/", views_dxf.DXFAnalysisView.as_view(), name="dxf_analysis"),
    path("dxf/analyze/upload/", views_dxf.DXFAnalyzeUploadView.as_view(), name="dxf_analyze_upload"),
    path("dxf/api/layers/", views_dxf.DXFLayersAPIView.as_view(), name="dxf_api_layers"),
    path("dxf/api/blocks/", views_dxf.DXFBlocksAPIView.as_view(), name="dxf_api_blocks"),
    path("dxf/api/texts/", views_dxf.DXFTextsAPIView.as_view(), name="dxf_api_texts"),
    path("dxf/api/dimensions/", views_dxf.DXFDimensionsAPIView.as_view(), name="dxf_api_dimensions"),
    path("dxf/api/rooms/", views_dxf.DXFRoomsAPIView.as_view(), name="dxf_api_rooms"),
    path("dxf/export/json/", views_dxf.DXFExportJSONView.as_view(), name="dxf_export_json"),
    path("dxf/dwg-status/", views_dxf.DWGStatusView.as_view(), name="dwg_status"),
    
    # ==========================================================================
    # NL2CAD: Natural Language CAD Analysis
    # ==========================================================================
    
    path("nl2cad/", views_nl2cad.NL2CADView.as_view(), name="nl2cad"),
    path("nl2cad/upload/", views_nl2cad.NL2CADUploadView.as_view(), name="nl2cad_upload"),
    path("nl2cad/query/", views_nl2cad.NL2CADQueryView.as_view(), name="nl2cad_query"),
    path("nl2cad/rooms/", views_nl2cad.NL2CADRoomsView.as_view(), name="nl2cad_rooms"),
    path("nl2cad/massen/", views_nl2cad.NL2CADMassenView.as_view(), name="nl2cad_massen"),
    path("nl2cad/gaeb/", views_nl2cad.NL2CADGAEBExportView.as_view(), name="nl2cad_gaeb"),
    path("nl2cad/learn/", views_nl2cad.NL2CADLearnView.as_view(), name="nl2cad_learn"),
    path("nl2cad/use-cases/", views_nl2cad.NL2CADUseCasesView.as_view(), name="nl2cad_use_cases"),
    path("nl2cad/classifier/", views_nl2cad.NL2CADClassifierView.as_view(), name="nl2cad_classifier"),
    
    # ==========================================================================
    # Brandschutz: Analyse, Prüfungen, Reports
    # ==========================================================================
    
    path("brandschutz/", include("apps.cad_hub.urls_brandschutz", namespace="brandschutz")),
    
    # ==========================================================================
    # CAD Analysis: MCP-Integration, Format-Analyse, NL-Query
    # ==========================================================================
    
    # Analyse Dashboard
    path("analysis/", views_analysis.AnalysisDashboardView.as_view(), name="analysis_dashboard"),
    
    # Szenario 1: Format-Analyse
    path("analyze/", views_analysis.FormatAnalyzerView.as_view(), name="format_analyzer"),
    path("analyze/api/", views_analysis.FormatAnalyzeAPIView.as_view(), name="format_analyze_api"),
    
    # Szenario 2: DXF Qualitätsprüfung
    path("dxf-quality/", views_analysis.DXFQualityView.as_view(), name="dxf_quality"),
    path("dxf-quality/api/", views_analysis.DXFQualityAPIView.as_view(), name="dxf_quality_api"),
    path("model/<uuid:pk>/dxf-quality/", views_analysis.DXFQualityModelView.as_view(), name="dxf_quality_model"),
    
    # Szenario 3: Natural Language Query
    path("nl-query/", views_analysis.NL2CADQueryView.as_view(), name="nl_query"),
    path("nl-query/api/", views_analysis.NL2CADQueryAPIView.as_view(), name="nl_query_api"),
    path("model/<uuid:pk>/query/", views_analysis.NL2CADModelQueryView.as_view(), name="nl_query_model"),
    
    # Szenario 4: Batch-Analyse
    path("batch-analyze/", views_analysis.BatchAnalyzeView.as_view(), name="batch_analyze"),
    path("batch-analyze/api/", views_analysis.BatchAnalyzeAPIView.as_view(), name="batch_analyze_api"),
    
    # Utility
    path("formats/", views_analysis.SupportedFormatsView.as_view(), name="supported_formats"),
]
