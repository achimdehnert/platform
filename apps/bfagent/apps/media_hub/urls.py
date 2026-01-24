"""
Media Hub URL Configuration
============================
"""
from django.urls import path
from apps.media_hub import views

app_name = 'media_hub'

urlpatterns = [
    # Dashboard & UI
    path('', views.dashboard, name='dashboard'),
    path('assets/', views.asset_browser, name='asset-browser'),
    path('assets/<int:asset_id>/', views.asset_detail, name='asset-detail'),
    
    # HTMX Partials
    path('partials/job-queue/', views.job_queue_partial, name='job-queue-partial'),
    path('partials/recent-assets/', views.recent_assets_partial, name='recent-assets-partial'),
    path('partials/asset-grid/', views.asset_grid_partial, name='asset-grid-partial'),
    path('partials/asset/<int:asset_id>/', views.asset_detail_partial, name='asset-detail-partial'),
    path('partials/job/<int:job_id>/', views.job_detail_partial, name='job-detail-partial'),
    
    # Form Actions
    path('submit/', views.submit_job_form, name='submit-job'),
    path('jobs/<int:job_id>/cancel/', views.cancel_job, name='cancel-job'),
    path('jobs/<int:job_id>/retry/', views.retry_job, name='retry-job'),
    path('assets/<int:asset_id>/delete/', views.delete_asset, name='delete-asset'),
    
    # API Endpoints
    path('api/jobs/submit/', views.submit_render_job, name='api-submit-job'),
    path('api/jobs/', views.list_jobs, name='api-list-jobs'),
    path('api/jobs/<int:job_id>/status/', views.get_job_status, name='api-job-status'),
    path('api/presets/', views.list_presets, name='api-list-presets'),
    
    # Audio / TTS API
    path('api/audio/generate/', views.submit_audio_job, name='api-audio-generate'),
    path('api/audio/voices/', views.list_voice_presets, name='api-voice-presets'),
    path('api/audio/status/', views.tts_status, name='api-tts-status'),
]
