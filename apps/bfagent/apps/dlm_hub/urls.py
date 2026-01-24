"""DLM Hub URL patterns."""

from django.urls import path

from . import views

app_name = "dlm_hub"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("local-analysis/", views.local_analysis, name="local-analysis"),
    
    # Analysis
    path("scan/", views.trigger_scan, name="trigger-scan"),
    path("scan/async/", views.trigger_scan_async, name="trigger-scan-async"),
    path("scan/<uuid:run_id>/progress/", views.scan_progress, name="scan-progress"),
    path("history/", views.analysis_history, name="analysis-history"),
    path("run/<uuid:run_id>/", views.run_detail, name="run-detail"),
    
    # Issues
    path("issues/", views.issue_list, name="issue-list"),
    path("issues/<int:issue_id>/resolve/", views.resolve_issue, name="resolve-issue"),
    path("issues/<int:issue_id>/preview/", views.file_preview, name="file-preview"),
    path("issues/<int:issue_id>/archive/", views.archive_file, name="archive-file"),
    path("issues/<int:issue_id>/review/", views.claude_review, name="claude-review"),
    path("issues/<int:issue_id>/diff/", views.diff_view, name="diff-view"),
    path("issues/<int:issue_id>/keep-primary/", views.keep_primary, name="keep-primary"),
    path("issues/<int:issue_id>/keep-secondary/", views.keep_secondary, name="keep-secondary"),
    
    # HTMX Partials
    path("htmx/scan/<uuid:run_id>/status/", views.htmx_scan_status, name="htmx-scan-status"),
    
    # API
    path("api/scan/<uuid:run_id>/status/", views.api_scan_status, name="api-scan-status"),
]
