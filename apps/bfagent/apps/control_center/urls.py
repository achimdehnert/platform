# apps/control_center/urls.py
from django.urls import path, include
from .views import ki_auto_loesen, dashboard_home, model_consistency_dashboard, screen_documentation_dashboard, genagent_dashboard, system_metrics, api_status, api_tool_detail, api_tool_execute, genagent_feature_status
from .views_ai_config import (
    ai_config_dashboard, llms_list, agents_list, llm_create_all,
    llm_create, llm_detail, llm_edit, llm_delete, llm_live_test,
    agent_create, agent_detail, agent_edit, agent_delete,
    llm_create_gemini, llm_create_groq, llm_create_anthropic
)
from .views_initiatives import (
    initiative_dashboard, initiative_kanban, initiative_create, initiative_list, 
    initiative_detail, initiative_update, initiative_delete, initiative_change_status,
    initiative_change_workflow_phase, initiative_add_requirement, requirement_update_status, 
    requirement_preview, requirement_delete, requirement_add_comment, requirement_analyze, 
    requirement_approve, initiative_start_research, initiative_research_status
)
from .views_feature_planning import feature_planning_dashboard, cross_domain_features_view, feature_create
from .views_mcp import MCPDashboardView
from .views_hub_management import (
    hub_management_dashboard, hub_toggle_status, hub_detail,
    feature_flags_view, event_log_view
)
from apps.bfagent.views import test_studio_views, cascade_api, code_review_views, migration_registry_views
from apps.bfagent import views_controlling

app_name = 'control_center'

urlpatterns = [
    # Dashboard
    path('', dashboard_home, name='dashboard'),
    
    # KI Auto-Lösen
    path('ki-auto-loesen/', ki_auto_loesen, name='ki_auto_loesen'),
    
    # Test Studio URLs (delegated to bfagent views)
    path('test-studio/', test_studio_views.requirements_list, name='test-studio-dashboard'),
    path('test-studio/kanban/', test_studio_views.requirements_kanban, name='test-studio-kanban'),
    path('test-studio/fix-plans/', test_studio_views.fix_plan_list, name='test-studio-fix-plans'),
    path('test-studio/requirements/create/', test_studio_views.requirement_create, name='test-studio-requirement-create'),
    path('test-studio/requirements/<uuid:pk>/', test_studio_views.requirement_detail, name='test-studio-requirement-detail'),
    path('test-studio/api/cascade-context/<uuid:pk>/', test_studio_views.requirement_cascade_context, name='test-studio-cascade-context'),
    path('test-studio/api/requirement/<uuid:pk>/update/', test_studio_views.requirement_update, name='test-studio-requirement-update'),
    path('test-studio/api/requirement/<uuid:pk>/delete/', test_studio_views.requirement_delete, name='test-studio-requirement-delete'),
    path('test-studio/api/requirement/<uuid:pk>/feedback/', test_studio_views.requirement_add_feedback, name='test-studio-requirement-feedback'),
    path('test-studio/api/requirement/<uuid:pk>/update-tier/', test_studio_views.requirement_update_tier, name='test-studio-requirement-update-tier'),
    path('test-studio/api/status/<uuid:pk>/', test_studio_views.requirement_update_status, name='test-studio-requirement-update-status'),
    path('test-studio/api/requirement/<uuid:pk>/update-doc-status/', test_studio_views.requirement_update_doc_status, name='test-studio-requirement-update-doc-status'),
    path('test-studio/api/requirement/<uuid:pk>/update-doc-notes/', test_studio_views.requirement_update_doc_notes, name='test-studio-requirement-update-doc-notes'),
    path('test-studio/api/feedback/<int:feedback_id>/delete/', test_studio_views.feedback_delete, name='test-studio-feedback-delete'),

    # Model Consistency Check
    path('model-consistency/', model_consistency_dashboard, name='model-consistency'),

    # AI Configuration
    path('ai-config/', ai_config_dashboard, name='ai-config-dashboard'),
    path('ai-config/llms/', llms_list, name='llms-list'),
    path('ai-config/agents/', agents_list, name='agents-list'),
    path('ai-config/llms/create-all/', llm_create_all, name='llm-create-all'),
    path('ai-config/llms/create/', llm_create, name='llm-create'),
    path('ai-config/llms/<int:pk>/', llm_detail, name='llm-detail'),
    path('ai-config/llms/<int:pk>/edit/', llm_edit, name='llm-edit'),
    path('ai-config/llms/<int:pk>/delete/', llm_delete, name='llm-delete'),
    path('ai-config/llms/<int:pk>/live-test/', llm_live_test, name='llm-live-test'),
    path('ai-config/llms/create-gemini/', llm_create_gemini, name='llm-create-gemini'),
    path('ai-config/llms/create-groq/', llm_create_groq, name='llm-create-groq'),
    path('ai-config/llms/create-anthropic/', llm_create_anthropic, name='llm-create-anthropic'),
    path('ai-config/agents/create/', agent_create, name='agent-create'),
    path('ai-config/agents/<int:pk>/', agent_detail, name='agent-detail'),
    path('ai-config/agents/<int:pk>/edit/', agent_edit, name='agent-edit'),
    path('ai-config/agents/<int:pk>/delete/', agent_delete, name='agent-delete'),

    # Initiatives
    path('initiatives/', initiative_dashboard, name='initiative-dashboard'),
    path('initiatives/list/', initiative_list, name='initiative-list'),
    path('initiatives/kanban/', initiative_kanban, name='initiative-kanban'),
    path('initiatives/create/', initiative_create, name='initiative-create'),
    path('initiatives/<uuid:pk>/', initiative_detail, name='initiative-detail'),
    path('initiatives/<uuid:pk>/edit/', initiative_update, name='initiative-edit'),
    path('initiatives/<uuid:pk>/delete/', initiative_delete, name='initiative-delete'),
    path('initiatives/<uuid:pk>/status/', initiative_change_status, name='initiative-status'),
    path('initiatives/<uuid:pk>/workflow-phase/', initiative_change_workflow_phase, name='initiative-workflow-phase'),
    path('initiatives/<uuid:pk>/requirements/add/', initiative_add_requirement, name='initiative-add-requirement'),
    path('initiatives/<uuid:pk>/requirements/<uuid:req_pk>/', requirement_preview, name='requirement-preview'),
    path('initiatives/<uuid:pk>/requirements/<uuid:req_pk>/status/', requirement_update_status, name='requirement-update-status'),
    path('initiatives/<uuid:pk>/requirements/<uuid:req_pk>/delete/', requirement_delete, name='requirement-delete'),
    path('initiatives/<uuid:pk>/requirements/<uuid:req_pk>/comment/', requirement_add_comment, name='requirement-add-comment'),
    path('initiatives/<uuid:pk>/requirements/<uuid:req_pk>/analyze/', requirement_analyze, name='requirement-analyze'),
    path('initiatives/<uuid:pk>/requirements/<uuid:req_pk>/approve/', requirement_approve, name='requirement-approve'),
    
    # AI-Powered Research
    path('initiatives/<uuid:pk>/start-research/', initiative_start_research, name='initiative-start-research'),
    path('initiatives/<uuid:pk>/research-status/', initiative_research_status, name='initiative-research-status'),

    # Feature Planning
    path('features/', feature_planning_dashboard, name='feature-planning-dashboard'),
    path('features/cross-domain/', cross_domain_features_view, name='feature-planning-cross-domain'),
    path('features/create/', feature_create, name='feature-planning-create'),

    # GenAgent & MCP
    path('genagent/', genagent_dashboard, name='genagent-dashboard'),
    path('mcp/', MCPDashboardView.as_view(), name='mcp-dashboard'),

    # Tools & Documentation
    path('code-review/', code_review_views.code_review_dashboard, name='code-review-dashboard'),
    path('migration-registry/', migration_registry_views.migration_dashboard, name='migration-registry-dashboard'),
    path('screen-documentation/', screen_documentation_dashboard, name='screen-documentation'),
    path('metrics/', system_metrics, name='metrics'),
    path('api/status/', api_status, name='api-status'),
    path('api/tools/<str:tool_name>/', api_tool_detail, name='api-tool-detail'),
    path('api/tools/<str:tool_name>/execute/', api_tool_execute, name='tool-execute'),
    path('genagent/feature-status/', genagent_feature_status, name='genagent-feature-status'),

    # Cascade Autonomous API
    path('api/cascade/session/start/', cascade_api.session_start, name='cascade-session-start'),
    path('api/cascade/session/<uuid:session_id>/', cascade_api.session_status, name='cascade-session-status'),
    path('api/cascade/session/<uuid:session_id>/stop/', cascade_api.session_stop, name='cascade-session-stop'),
    path('api/cascade/session/<uuid:session_id>/logs/', cascade_api.session_logs, name='cascade-session-logs'),
    path('api/cascade/session/<uuid:session_id>/log/', cascade_api.session_log_add, name='cascade-session-log-add'),
    path('api/cascade/session/<uuid:session_id>/iterate/', cascade_api.session_iterate, name='cascade-session-iterate'),
    path('api/cascade/sessions/active/', cascade_api.active_sessions, name='cascade-sessions-active'),

    # Agent/LLM Controlling Dashboard
    path('controlling/', views_controlling.controlling_dashboard, name='controlling-dashboard'),
    path('controlling/api/summary/', views_controlling.controlling_api_summary, name='controlling-api-summary'),
    path('controlling/api/baseline-compare/', views_controlling.controlling_baseline_compare, name='controlling-baseline-compare'),
    path('controlling/api/interpret/', views_controlling.controlling_interpret, name='controlling-interpret'),
    path('controlling/llm-usage/', views_controlling.llm_usage_list, name='llm-usage-list'),
    path('controlling/orchestration/', views_controlling.orchestration_list, name='orchestration-list'),
    path('controlling/api/alert/<int:alert_id>/acknowledge/', views_controlling.alert_acknowledge, name='alert-acknowledge'),
    path('controlling/llm-usage/<int:log_id>/', views_controlling.llm_usage_detail, name='llm-usage-detail'),
    path('controlling/orchestration/<str:session_id>/', views_controlling.orchestration_detail, name='orchestration-detail'),
    
    # Usage Tracking (Errors + Tool Usage)
    path("usage-tracking/", include(("apps.bfagent.urls_usage_tracking", "usage_tracking"))),
    
    # Terminal Error Monitor
    path("terminal-monitor/", include(("apps.bfagent.urls_terminal_monitor", "terminal_monitor"))),
    
    # Hub Management (Event-Driven Architecture)
    path('hub-management/', hub_management_dashboard, name='hub_management'),
    path('hub-management/hub/<str:hub_id>/', hub_detail, name='hub_detail'),
    path('hub-management/hub/<str:hub_id>/toggle/', hub_toggle_status, name='hub_toggle'),
    path('hub-management/feature-flags/', feature_flags_view, name='feature_flags'),
    path('hub-management/events/', event_log_view, name='event_log'),
]
