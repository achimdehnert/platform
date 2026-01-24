"""
GenAgent URL Configuration

Integrates all GenAgent view modules:
- Domain Templates (domain_views)
- Action Management (action_views)
- Handler Discovery (handler_views)
- Handler Registry (registry_views)
"""

from django.urls import path
from apps.genagent.views import domain_views, action_views, handler_views, registry_views

app_name = 'genagent'

urlpatterns = [
    # ========================================================================
    # MAIN DASHBOARD
    # ========================================================================
    path('', action_views.genagent_dashboard, name='dashboard'),

    # ========================================================================
    # DOMAIN TEMPLATE MANAGEMENT
    # ========================================================================
    path('domains/', domain_views.domain_list, name='domain-list'),
    path('domains/search/', domain_views.domain_search, name='domain-search'),
    path('domains/<str:domain_id>/', domain_views.domain_detail, name='domain-detail'),
    path('domains/<str:domain_id>/install/', domain_views.domain_install_wizard, name='domain-install'),
    path('domains/<str:domain_id>/install/execute/', domain_views.domain_install_execute, name='domain-install-execute'),
    path('domains/<str:domain_id>/installed/<int:phase_id>/', domain_views.domain_installed_success, name='domain-installed'),
    path('domains/<str:domain_id>/add-phase/', domain_views.domain_add_phase, name='domain-add-phase'),

    # Custom Domains (Database-backed)
    path('domains/custom/create/', domain_views.custom_domain_create, name='custom-domain-create'),
    path('domains/custom/<int:pk>/', domain_views.custom_domain_detail, name='custom-domain-detail'),
    path('domains/custom/<int:pk>/edit/', domain_views.custom_domain_edit, name='custom-domain-edit'),
    path('domains/custom/<int:pk>/delete/', domain_views.custom_domain_delete, name='custom-domain-delete'),

    # ========================================================================
    # ACTION MANAGEMENT (CRUD)
    # ========================================================================
    path('actions/', action_views.action_list, name='action-list'),
    path('actions/phase/<int:phase_id>/create/', action_views.action_create, name='action-create'),
    path('actions/<int:action_id>/edit/', action_views.action_edit, name='action-edit'),
    path('actions/<int:action_id>/delete/', action_views.action_delete, name='action-delete'),
    path('actions/config-schema/', action_views.action_get_config_schema, name='action-config-schema'),
    path('actions/<int:action_id>/execute/', action_views.action_execute, name='action-execute'),
    path('actions/<int:action_id>/logs/', action_views.action_execution_logs, name='action-logs'),
    path('phases/<int:phase_id>/', action_views.phase_detail, name='phase-detail'),
    path('phases/<int:phase_id>/execute/', action_views.phase_execute, name='phase-execute'),
    path('phases/<int:phase_id>/reorder/', action_views.action_reorder, name='action-reorder'),
    path('execution-logs/<int:log_id>/', action_views.execution_log_detail, name='execution-log-detail'),

    # ========================================================================
    # HANDLER DISCOVERY & TESTING
    # ========================================================================
    path('handlers/', handler_views.handler_list, name='handler-list'),
    path('handlers/search/', handler_views.handler_search, name='handler-search'),
    path('handlers/<str:handler_path>/', handler_views.handler_detail, name='handler-detail'),
    path('handlers/<str:handler_path>/test/', handler_views.handler_test_interface, name='handler-test'),
    path('handlers/<str:handler_path>/execute/', handler_views.handler_execute_test, name='handler-execute'),

    # ========================================================================
    # HANDLER REGISTRY (PHASE 1)
    # ========================================================================
    path('registry/', registry_views.registry_dashboard, name='registry-dashboard'),
    path('registry/domains/', registry_views.registry_domain_list, name='registry-domain-list'),
    path('registry/domains/<str:domain>/', registry_views.registry_domain_detail, name='registry-domain-detail'),
    path('registry/handlers/<str:handler_name>/', registry_views.registry_handler_detail, name='registry-handler-detail'),
    path('registry/handlers/<str:handler_name>/test/', registry_views.registry_handler_test, name='registry-handler-test'),

    # ========================================================================
    # API ENDPOINTS
    # ========================================================================
    # Domain API
    path('api/domains/', domain_views.domain_api_list, name='api-domain-list'),
    path('api/domains/<str:domain_id>/', domain_views.domain_api_detail, name='api-domain-detail'),

    # Handler API
    path('api/handlers/', handler_views.handler_api_list, name='api-handler-list'),
    path('api/handlers/<str:handler_path>/', handler_views.handler_api_detail, name='api-handler-detail'),

    # Registry API
    path('api/registry/stats/', registry_views.registry_api_stats, name='api-registry-stats'),
    path('api/registry/domains/', registry_views.registry_api_domains, name='api-registry-domains'),
    path('api/registry/handlers/', registry_views.registry_api_handlers, name='api-registry-handlers'),
    path('api/registry/handlers/<str:handler_name>/', registry_views.registry_api_handler_detail, name='api-registry-handler-detail'),
]
