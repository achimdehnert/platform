"""
URL configuration for BF Agent app

STRUCTURE:
1. Core URLs (dashboard, health check)
2. Custom Project URLs (enrichment, agent base, etc.)
3. Custom Feature URLs (chapter actions, executions, worlds)
4. API Endpoints
5. AUTO-GENERATED CRUD URLs (managed by auto_compliance_fixer.py)
"""

from django.core.exceptions import ImproperlyConfigured
from django.urls import include, path

# Create 'views' alias for backward compatibility with existing urlpatterns
# The views package now exports all view functions from all modules
from . import views


def validate_view_exists(module, view_name):
    """Validate that a view exists before URL registration"""
    if not hasattr(module, view_name):
        raise ImproperlyConfigured(
            f"View '{view_name}' not found in module '{module.__name__}'. "
            f"Available views: {[attr for attr in dir(module) if not attr.startswith('_')]}"
        )
    return getattr(module, view_name)


from .domains.book_writing.views import (
    batch_views,
    chapter_edit_views,
    chapter_views,
    outline_views,
    world_views,
)
from .views import (
    chapter_comment_views,
    character_views,
    code_review_views,
    crud_views,
    enrichment_views_handler,
    enrichment_views_minimal,
    feature_planning_views,
    handler_test_view,
    migration_registry_views,
    story_engine_views,
    test_studio_views,
    workflow_builder_views,
)
from . import views_controlling
from .views.crud_views import crud_config_api, dynamic_project_detail, dynamic_project_list

app_name = "bfagent"

urlpatterns = [
    # ============================================================================
    # CORE URLs
    # ============================================================================
    path("", crud_views.dashboard, name="dashboard"),
    path("control-center-health/", crud_views.control_center_health, name="control-center-health"),
    # Workflow Builder
    path(
        "workflow-builder/",
        workflow_builder_views.WorkflowBuilderView.as_view(),
        name="workflow-builder",
    ),
    # Code Review
    path("code-review/", code_review_views.code_review_dashboard, name="code-review-dashboard"),
    path("code-review/run/", code_review_views.run_code_review, name="code-review-run"),
    path(
        "books/<int:project_id>/code-review/",
        code_review_views.project_code_review,
        name="project-code-review",
    ),
    # Agent/LLM Controlling moved to Control Center: /control-center/controlling/
    # ============================================================================
    # CUSTOM BOOK URLs (formerly projects)
    # ============================================================================
    path("books/", views.project_list, name="project-list"),
    path("books/<int:pk>/", views.project_detail, name="project-detail"),
    path("books/create/", crud_views.project_create, name="project-create"),
    path("books/<int:pk>/edit/", crud_views.project_edit, name="project-edit"),
    path(
        "books/<int:pk>/update-field/",
        crud_views.project_update_field,
        name="project-update-field",
    ),
    path("books/<int:pk>/delete/", crud_views.project_delete, name="project-delete"),
    # Chapter Generation & Editing
    path(
        "books/<int:project_id>/chapters/<int:chapter_id>/generate/",
        chapter_views.generate_chapter,
        name="chapter-generate",
    ),
    path(
        "books/<int:project_id>/chapters/<int:chapter_id>/edit/",
        chapter_edit_views.chapter_edit,
        name="chapter-edit",
    ),
    # Outline Generation
    path(
        "books/<int:project_id>/outline/generate/",
        outline_views.generate_outline,
        name="outline-generate",
    ),
    # Batch Chapter Generation
    path(
        "books/<int:project_id>/chapters/generate-all/",
        batch_views.generate_all_chapters,
        name="chapters-generate-all",
    ),
    # Project Workflow transitions (HTMX)
    path(
        "projects/<int:pk>/workflow/start/",
        views.project_workflow_start,
        name="project-workflow-start",
    ),
    path(
        "projects/<int:pk>/workflow/next/",
        views.project_workflow_next,
        name="project-workflow-next",
    ),
    path(
        "projects/<int:pk>/workflow/previous/",
        views.project_workflow_previous,
        name="project-workflow-previous",
    ),
    # Project Agent Base editing (HTMX)
    path(
        "projects/<int:pk>/agent-base/panel/",
        views.project_agent_base_panel,
        name="project-agent-base-panel",
    ),
    path(
        "projects/<int:pk>/agent-base/save/",
        views.project_agent_base_save,
        name="project-agent-base-save",
    ),
    # Project enrichment (agent-driven)
    path(
        "projects/<int:pk>/enrich/panel/",
        views.project_enrich_panel,
        name="project-enrich-panel",
    ),
    path(
        "projects/<int:pk>/enrich/actions/",
        views.project_enrich_actions,
        name="project-enrich-actions",
    ),
    # 2-Step Enrichment Workflow (OLD - crud_views.py)
    path(
        "projects/<int:pk>/enrich/run/", views.project_enrich_run, name="project-enrich-run"
    ),  # Step 1: Preview
    path(
        "projects/<int:pk>/enrich/execute/",
        views.project_enrich_execute,
        name="project-enrich-execute",
    ),  # Step 2: Execute
    # 🧪 HANDLER-BASED VERSIONS (NEW - Testing in Parallel)
    path(
        "projects/<int:pk>/enrich/run/handler/",
        enrichment_views_handler.project_enrich_run_handler,
        name="project-enrich-run-handler",
    ),  # Step 1: Preview (Handler)
    path(
        "projects/<int:pk>/enrich/execute/handler/",
        enrichment_views_handler.project_enrich_execute_handler,
        name="project-enrich-execute-handler",
    ),  # Step 2: Execute (Handler)
    # 🧪 MINIMAL HANDLER-BASED VERSIONS (Pure Handler Architecture)
    path(
        "projects/<int:pk>/enrich/run/minimal/",
        enrichment_views_minimal.minimal_enrich_run,
        name="project-enrich-run-minimal",
    ),  # Minimal: Pure handler execution
    path(
        "projects/<int:pk>/enrich/execute/minimal/",
        enrichment_views_minimal.minimal_enrich_execute,
        name="project-enrich-execute-minimal",
    ),  # Minimal: Apply results (placeholder)
    # Enrichment Response Management
    path(
        "projects/<int:pk>/enrichment/<int:response_id>/edit/",
        views.enrichment_response_edit,
        name="enrichment-response-edit",
    ),
    path(
        "projects/<int:pk>/enrichment/<int:response_id>/apply/",
        views.project_enrich_apply,
        name="enrichment-response-apply",
    ),
    path(
        "projects/<int:pk>/enrichment/<int:response_id>/reject/",
        views.enrichment_response_reject,
        name="enrichment-response-reject",
    ),
    # ============================================================================
    # CHARACTER MANAGEMENT URLs (Handler-First Architecture)
    # ============================================================================
    path(
        "projects/<int:pk>/characters/",
        character_views.project_characters,
        name="project-characters",
    ),
    path(
        "projects/<int:pk>/characters/<int:character_pk>/",
        character_views.character_detail,
        name="character-detail",
    ),
    path(
        "projects/<int:pk>/characters/generate/",
        character_views.generate_character_cast,
        name="generate-character-cast",
    ),
    path(
        "projects/<int:pk>/characters/<int:character_pk>/enrich/",
        character_views.enrich_character,
        name="enrich-character",
    ),
    path(
        "projects/<int:pk>/characters/create/",
        character_views.character_create,
        name="character-create",
    ),
    path(
        "projects/<int:pk>/characters/<int:character_pk>/edit/",
        character_views.character_edit,
        name="character-edit",
    ),
    path(
        "projects/<int:pk>/characters/<int:character_pk>/delete/",
        character_views.character_delete,
        name="character-delete",
    ),
    # ============================================================================
    # WORLD BUILDING URLs
    # ============================================================================
    path(
        "projects/<int:pk>/world/",
        world_views.world_detail,
        name="world-detail",
    ),
    path(
        "projects/<int:pk>/world/edit/",
        world_views.world_create_or_edit,
        name="world-edit",
    ),
    path(
        "projects/<int:pk>/world/locations/create/",
        world_views.location_create,
        name="location-create",
    ),
    path(
        "projects/<int:pk>/world/locations/<int:location_pk>/edit/",
        world_views.location_edit,
        name="location-edit",
    ),
    path(
        "projects/<int:pk>/world/locations/<int:location_pk>/delete/",
        world_views.location_delete,
        name="location-delete",
    ),
    path(
        "projects/<int:pk>/world/rules/create/",
        world_views.rule_create,
        name="rule-create",
    ),
    path(
        "projects/<int:pk>/world/rules/<int:rule_pk>/edit/",
        world_views.rule_edit,
        name="rule-edit",
    ),
    path(
        "projects/<int:pk>/world/rules/<int:rule_pk>/delete/",
        world_views.rule_delete,
        name="rule-delete",
    ),
    path(
        "books/<int:pk>/world/generate/",
        validate_view_exists(world_views, "world_generate"),
        name="world-generate",
    ),
    path(
        "books/<int:pk>/worlds/",
        validate_view_exists(world_views, "project_worlds_list"),
        name="project-worlds-list",
    ),
    # ============================================================================
    # FIELD MANAGEMENT URLs (Custom Fields System)
    # ============================================================================
    # Field Definitions
    path("fields/", views.field_definition_list, name="field-definition-list"),
    path("fields/create/", views.field_definition_create, name="field-definition-create"),
    path("fields/<int:pk>/edit/", views.field_definition_edit, name="field-definition-edit"),
    path("fields/<int:pk>/delete/", views.field_definition_delete, name="field-definition-delete"),
    path("api/fields/<int:pk>/", views.field_definition_api, name="field-definition-api"),
    # Field Groups
    path("field-groups/", views.field_group_list, name="field-group-list"),
    path("field-groups/create/", views.field_group_create, name="field-group-create"),
    # Project Field Values
    path("projects/<int:pk>/fields/", views.project_field_values, name="project-field-values"),
    path(
        "projects/<int:pk>/fields/<int:field_id>/save/",
        views.project_field_value_save,
        name="project-field-value-save",
    ),
    # ============================================================================
    # CUSTOM FEATURE URLs
    # ============================================================================
    # Chapter AI Actions (custom) - DEPRECATED, use chapter-generate instead
    # path(
    #     "chapters/<int:pk>/action/<str:action>/",
    #     chapter_views.chapter_action,
    #     name="chapter-action",
    # ),
    # Executions
    path("executions/", views.execution_list, name="execution-list"),
    # ============================================================================
    # API ENDPOINTS
    # ============================================================================
    path("api/projects/", views.projects_api, name="projects-api"),
    path("api/crud-config/<str:model_name>/", crud_config_api, name="crud-config-api"),
    path("api/agents/<int:agent_id>/", crud_views.agent_api, name="agent-api"),
    path("api/templates/", crud_views.templates_api, name="templates-api"),
    # Handler Generator API
    # TODO: Fix these endpoints - functions don't exist or have different names
    # path("api/handler-generator/generate/", views.generate_handler, name="handler-generator-api-generate"),
    # path("api/handler-generator/deploy/", views.deploy_handler, name="handler-generator-api-deploy"),
    # path("api/handler-generator/regenerate/", views.regenerate_handler, name="handler-generator-api-regenerate"),
    # path("api/handler-generator/status/", views.generator_status, name="handler-generator-api-status"),
    # Handler Generator Web UI
    path(
        "handler-generator/", views.handler_generator_dashboard, name="handler-generator-dashboard"
    ),
    path(
        "handler-generator/generate/",
        views.handler_generator_generate,
        name="handler-generator-generate",
    ),
    path(
        "handler-generator/deploy/", views.handler_generator_deploy, name="handler-generator-deploy"
    ),
    # Handler Management UI (Phase 1 MVP + Phase 3A)
    path(
        "handler-management/",
        views.handler_management_dashboard,
        name="handler-management-dashboard",
    ),
    path("handler-management/handlers/", views.handler_list_tab, name="handler-list-tab"),
    path("handler-management/mappings/", views.action_mappings_tab, name="action-mappings-tab"),
    path(
        "handler-management/mappings/create/",
        views.create_action_mapping,
        name="create-action-mapping",
    ),
    path(
        "handler-management/mappings/<int:pk>/update/",
        views.update_action_mapping,
        name="update-action-mapping",
    ),
    path(
        "handler-management/mappings/<int:pk>/delete/",
        views.delete_action_mapping,
        name="delete-action-mapping",
    ),
    path(
        "handler-management/mappings/bulk-delete/",
        views.bulk_delete_mappings,
        name="bulk-delete-mappings",
    ),
    path(
        "handler-management/mappings/bulk-update-phase/",
        views.bulk_update_phase,
        name="bulk-update-phase",
    ),
    path(
        "handler-management/mappings/bulk-toggle-active/",
        views.bulk_toggle_active,
        name="bulk-toggle-active",
    ),
    path("handler-management/mappings/reorder/", views.reorder_mappings, name="reorder-mappings"),
    path("handler-management/handlers/<int:pk>/", views.handler_detail, name="handler-detail"),
    path("handler-management/handlers/<int:pk>/test/", views.test_handler, name="test-handler"),
    path("handler-management/llm-test/", views.llm_handler_test_tab, name="llm-handler-test-tab"),
    path("handler-management/llm-test/execute/", views.llm_test_execute, name="llm-test-execute"),
    # ============================================================================
    # METRICS & ANALYTICS (Phase 3A Session 3)
    # ============================================================================
    path("handler-management/metrics/", views.metrics_dashboard_tab, name="metrics-dashboard"),
    path(
        "handler-management/metrics/api/chart-data/",
        views.metrics_api_chart_data,
        name="metrics-chart-data",
    ),
    path(
        "handler-management/metrics/api/top-handlers/",
        views.metrics_api_top_handlers,
        name="metrics-top-handlers",
    ),
    # ============================================================================
    # DYNAMIC CRUD SYSTEM
    # ============================================================================
    path("dynamic/projects/", dynamic_project_list, name="dynamic-project-list"),
    path("dynamic/projects/<int:pk>/", dynamic_project_detail, name="dynamic-project-detail"),
    # ============================================================================
    # AUTO-GENERATED CRUD URLs
    # Generated by: scripts/auto_compliance_fixer.py
    # DO NOT EDIT MANUALLY - Will be regenerated from config/crud_config.yaml
    # ============================================================================
    # Agents URLs
    path("agents/", views.AgentsListView.as_view(), name="agent-list"),
    path("agents/create/", views.AgentsCreateView.as_view(), name="agent-create"),
    path("agents/<int:pk>/", views.AgentsDetailView.as_view(), name="agent-detail"),
    path("agents/<int:pk>/edit/", views.AgentsUpdateView.as_view(), name="agent-update"),
    path("agents/<int:pk>/delete/", views.AgentsDeleteView.as_view(), name="agent-delete"),
    # CUSTOM: Agent Live Test (Protected from auto-generation)
    path("agents/<int:pk>/live-test/", views.agent_live_test, name="agent-live-test"),
    # BookChapters URLs
    path("chapters/", views.BookChaptersListView.as_view(), name="chapter-list"),
    path("chapters/create/", views.BookChaptersCreateView.as_view(), name="chapter-create"),
    path("chapters/<int:pk>/", views.BookChaptersDetailView.as_view(), name="chapter-detail"),
    path("chapters/<int:pk>/edit/", views.BookChaptersUpdateView.as_view(), name="chapter-update"),
    path(
        "chapters/<int:pk>/delete/", views.BookChaptersDeleteView.as_view(), name="chapter-delete"
    ),
    # Chapter Comments
    path(
        "chapters/<int:chapter_id>/comments/add/",
        chapter_comment_views.chapter_comment_add,
        name="chapter-comment-add",
    ),
    path(
        "chapters/<int:chapter_id>/comments/",
        chapter_comment_views.chapter_comments_list,
        name="chapter-comments-list",
    ),
    path(
        "chapters/comments/<int:comment_id>/toggle/",
        chapter_comment_views.chapter_comment_toggle_status,
        name="chapter-comment-toggle",
    ),
    path(
        "chapters/comments/<int:comment_id>/delete/",
        chapter_comment_views.chapter_comment_delete,
        name="chapter-comment-delete",
    ),
    # Characters URLs
    path("characters/", views.CharactersListView.as_view(), name="character-list"),
    path("characters/create/", views.CharactersCreateView.as_view(), name="character-create"),
    path("characters/<int:pk>/", views.CharactersDetailView.as_view(), name="character-detail"),
    path(
        "characters/<int:pk>/edit/", views.CharactersUpdateView.as_view(), name="character-update"
    ),
    path(
        "characters/<int:pk>/delete/", views.CharactersDeleteView.as_view(), name="character-delete"
    ),
    # Llms URLs
    path("llms/", views.LlmsListView.as_view(), name="llm-list"),
    path("llms/create/", views.LlmsCreateView.as_view(), name="llm-create"),
    path("llms/<int:pk>/", views.LlmsDetailView.as_view(), name="llm-detail"),
    path("llms/<int:pk>/edit/", views.LlmsUpdateView.as_view(), name="llm-update"),
    path("llms/<int:pk>/delete/", views.LlmsDeleteView.as_view(), name="llm-delete"),
    # CUSTOM: LLM Live Test (Protected from auto-generation)
    path("llms/<int:pk>/live-test/", views.llm_live_test, name="llm-live-test"),
    # StoryArc URLs
    path("storyarc/", views.StoryArcListView.as_view(), name="storyarc-list"),
    path("storyarc/create/", views.StoryArcCreateView.as_view(), name="storyarc-create"),
    path("storyarc/<int:pk>/", views.StoryArcDetailView.as_view(), name="storyarc-detail"),
    path("storyarc/<int:pk>/edit/", views.StoryArcUpdateView.as_view(), name="storyarc-update"),
    path("storyarc/<int:pk>/delete/", views.StoryArcDeleteView.as_view(), name="storyarc-delete"),
    # PlotPoint URLs
    path("plotpoint/", views.PlotPointListView.as_view(), name="plotpoint-list"),
    path("plotpoint/create/", views.PlotPointCreateView.as_view(), name="plotpoint-create"),
    path("plotpoint/<int:pk>/", views.PlotPointDetailView.as_view(), name="plotpoint-detail"),
    path("plotpoint/<int:pk>/edit/", views.PlotPointUpdateView.as_view(), name="plotpoint-update"),
    path(
        "plotpoint/<int:pk>/delete/", views.PlotPointDeleteView.as_view(), name="plotpoint-delete"
    ),
    # AgentArtifacts URLs
    path("artifacts/", views.AgentArtifactsListView.as_view(), name="artifact-list"),
    path("artifacts/create/", views.AgentArtifactsCreateView.as_view(), name="artifact-create"),
    path("artifacts/<int:pk>/", views.AgentArtifactsDetailView.as_view(), name="artifact-detail"),
    path(
        "artifacts/<int:pk>/edit/", views.AgentArtifactsUpdateView.as_view(), name="artifact-update"
    ),
    path(
        "artifacts/<int:pk>/delete/",
        views.AgentArtifactsDeleteView.as_view(),
        name="artifact-delete",
    ),
    # BookTypes URLs
    path("booktypes/", views.BookTypesListView.as_view(), name="booktype-list"),
    path("booktypes/create/", views.BookTypesCreateView.as_view(), name="booktype-create"),
    path("booktypes/<int:pk>/", views.BookTypesDetailView.as_view(), name="booktype-detail"),
    path("booktypes/<int:pk>/edit/", views.BookTypesUpdateView.as_view(), name="booktype-update"),
    path("booktypes/<int:pk>/delete/", views.BookTypesDeleteView.as_view(), name="booktype-delete"),
    # QueryPerformanceLog URLs
    path(
        "performance-log/", views.QueryPerformanceLogListView.as_view(), name="performance-log-list"
    ),
    path(
        "performance-log/create/",
        views.QueryPerformanceLogCreateView.as_view(),
        name="performance-log-create",
    ),
    path(
        "performance-log/<int:pk>/",
        views.QueryPerformanceLogDetailView.as_view(),
        name="performance-log-detail",
    ),
    path(
        "performance-log/<int:pk>/edit/",
        views.QueryPerformanceLogUpdateView.as_view(),
        name="performance-log-update",
    ),
    path(
        "performance-log/<int:pk>/delete/",
        views.QueryPerformanceLogDeleteView.as_view(),
        name="performance-log-delete",
    ),
    # Worlds URLs
    path("worlds/", views.WorldsListView.as_view(), name="world-list"),
    path("worlds/create/", views.WorldsCreateView.as_view(), name="world-create"),
    path("worlds/<int:pk>/", views.WorldsDetailView.as_view(), name="world-detail"),
    path("worlds/<int:pk>/edit/", views.WorldsUpdateView.as_view(), name="world-update"),
    path("worlds/<int:pk>/delete/", views.WorldsDeleteView.as_view(), name="world-delete"),
    # Genre URLs
    path("genres/", views.GenreListView.as_view(), name="genre-list"),
    path("genres/create/", views.GenreCreateView.as_view(), name="genre-create"),
    path("genres/<int:pk>/", views.GenreDetailView.as_view(), name="genre-detail"),
    path("genres/<int:pk>/edit/", views.GenreUpdateView.as_view(), name="genre-update"),
    path("genres/<int:pk>/delete/", views.GenreDeleteView.as_view(), name="genre-delete"),
    # TargetAudience URLs
    path("audiences/", views.TargetAudienceListView.as_view(), name="targetaudience-list"),
    path(
        "audiences/create/", views.TargetAudienceCreateView.as_view(), name="targetaudience-create"
    ),
    path(
        "audiences/<int:pk>/",
        views.TargetAudienceDetailView.as_view(),
        name="targetaudience-detail",
    ),
    path(
        "audiences/<int:pk>/edit/",
        views.TargetAudienceUpdateView.as_view(),
        name="targetaudience-update",
    ),
    path(
        "audiences/<int:pk>/delete/",
        views.TargetAudienceDeleteView.as_view(),
        name="targetaudience-delete",
    ),
    # WritingStatus URLs
    path("statuses/", views.WritingStatusListView.as_view(), name="writingstatus-list"),
    path("statuses/create/", views.WritingStatusCreateView.as_view(), name="writingstatus-create"),
    path(
        "statuses/<int:pk>/", views.WritingStatusDetailView.as_view(), name="writingstatus-detail"
    ),
    path(
        "statuses/<int:pk>/edit/",
        views.WritingStatusUpdateView.as_view(),
        name="writingstatus-update",
    ),
    path(
        "statuses/<int:pk>/delete/",
        views.WritingStatusDeleteView.as_view(),
        name="writingstatus-delete",
    ),
    # WorkflowPhase URLs
    path("workflowphase/", views.WorkflowPhaseListView.as_view(), name="workflowphase-list"),
    path(
        "workflowphase/create/",
        views.WorkflowPhaseCreateView.as_view(),
        name="workflowphase-create",
    ),
    path(
        "workflowphase/<int:pk>/",
        views.WorkflowPhaseDetailView.as_view(),
        name="workflowphase-detail",
    ),
    path(
        "workflowphase/<int:pk>/edit/",
        views.WorkflowPhaseUpdateView.as_view(),
        name="workflowphase-update",
    ),
    path(
        "workflowphase/<int:pk>/delete/",
        views.WorkflowPhaseDeleteView.as_view(),
        name="workflowphase-delete",
    ),
    # WorkflowTemplate URLs
    path(
        "workflowtemplate/", views.WorkflowTemplateListView.as_view(), name="workflowtemplate-list"
    ),
    path(
        "workflowtemplate/create/",
        views.WorkflowTemplateCreateView.as_view(),
        name="workflowtemplate-create",
    ),
    path(
        "workflowtemplate/<int:pk>/",
        views.WorkflowTemplateDetailView.as_view(),
        name="workflowtemplate-detail",
    ),
    path(
        "workflowtemplate/<int:pk>/edit/",
        views.WorkflowTemplateUpdateView.as_view(),
        name="workflowtemplate-update",
    ),
    path(
        "workflowtemplate/<int:pk>/delete/",
        views.WorkflowTemplateDeleteView.as_view(),
        name="workflowtemplate-delete",
    ),
    # WorkflowPhaseStep URLs
    path(
        "workflowphasestep/",
        views.WorkflowTemplatePhasesManagementView.as_view(),
        name="workflowphasestep-manage",
    ),
    path(
        "workflowphasestep/list/",
        views.WorkflowPhaseStepListView.as_view(),
        name="workflowphasestep-list",
    ),
    path(
        "workflowphasestep/create/",
        views.WorkflowPhaseStepCreateView.as_view(),
        name="workflowphasestep-create",
    ),
    path(
        "workflowphasestep/<int:pk>/",
        views.WorkflowPhaseStepDetailView.as_view(),
        name="workflowphasestep-detail",
    ),
    path(
        "workflowphasestep/<int:pk>/edit/",
        views.WorkflowPhaseStepUpdateView.as_view(),
        name="workflowphasestep-update",
    ),
    path(
        "workflowphasestep/<int:pk>/delete/",
        views.WorkflowPhaseStepDeleteView.as_view(),
        name="workflowphasestep-delete",
    ),
    path(
        "api/workflow-phase-step/add/",
        views.workflow_phase_step_add,
        name="workflow-phase-step-add",
    ),
    path(
        "api/workflow-phase-step/remove/",
        views.workflow_phase_step_remove,
        name="workflow-phase-step-remove",
    ),
    path(
        "api/workflow-phase-step/reorder/",
        views.workflow_phase_step_reorder,
        name="workflow-phase-step-reorder",
    ),
    # BookTypePhase URLs
    path(
        "booktypephase/",
        views.BookTypePhaseManagementView.as_view(),
        name="booktypephase-manage",
    ),
    path(
        "booktypephase/list/",
        views.BookTypePhaseListView.as_view(),
        name="booktypephase-list",
    ),
    path(
        "booktypephase/create/",
        views.BookTypePhaseCreateView.as_view(),
        name="booktypephase-create",
    ),
    path(
        "booktypephase/<int:pk>/",
        views.BookTypePhaseDetailView.as_view(),
        name="booktypephase-detail",
    ),
    path(
        "booktypephase/<int:pk>/edit/",
        views.BookTypePhaseUpdateView.as_view(),
        name="booktypephase-update",
    ),
    path(
        "booktypephase/<int:pk>/delete/",
        views.BookTypePhaseDeleteView.as_view(),
        name="booktypephase-delete",
    ),
    # BookTypePhase Management API
    path(
        "api/booktype-phase/add/",
        views.booktype_phase_add,
        name="booktype-phase-add",
    ),
    path(
        "api/booktype-phase/remove/",
        views.booktype_phase_remove,
        name="booktype-phase-remove",
    ),
    path(
        "api/booktype-phase/reorder/",
        views.booktype_phase_reorder,
        name="booktype-phase-reorder",
    ),
    # AgentAction URLs
    path(
        "agentaction/",
        views.AgentActionListView.as_view(),
        name="agentaction-list",
    ),
    path(
        "agentaction/create/",
        views.AgentActionCreateView.as_view(),
        name="agentaction-create",
    ),
    path(
        "agentaction/<int:pk>/",
        views.AgentActionDetailView.as_view(),
        name="agentaction-detail",
    ),
    path(
        "agentaction/<int:pk>/edit/",
        views.AgentActionUpdateView.as_view(),
        name="agentaction-update",
    ),
    path(
        "agentaction/<int:pk>/delete/",
        views.AgentActionDeleteView.as_view(),
        name="agentaction-delete",
    ),
    path(
        "agentaction/<int:pk>/test/",
        views.AgentActionTestView.as_view(),
        name="agentaction-test",
    ),
    # Action Template Assignment Modal (HTMX)
    path(
        "action/<int:action_id>/assign-template/",
        views.action_template_assign_modal,
        name="action-template-assign",
    ),
    path(
        "action/<int:action_id>/assign-template/save/",
        views.action_template_assign_save,
        name="action-template-assign-save",
    ),
    # PhaseActionConfig URLs
    path(
        "phaseactionconfig/",
        views.PhaseActionConfigListView.as_view(),
        name="phaseactionconfig-list",
    ),
    path(
        "phaseactionconfig/create/",
        views.PhaseActionConfigCreateView.as_view(),
        name="phaseactionconfig-create",
    ),
    path(
        "phaseactionconfig/<int:pk>/",
        views.PhaseActionConfigDetailView.as_view(),
        name="phaseactionconfig-detail",
    ),
    path(
        "phaseactionconfig/<int:pk>/edit/",
        views.PhaseActionConfigUpdateView.as_view(),
        name="phaseactionconfig-update",
    ),
    path(
        "phaseactionconfig/<int:pk>/delete/",
        views.PhaseActionConfigDeleteView.as_view(),
        name="phaseactionconfig-delete",
    ),
    # Phase-Actions Management URLs
    path(
        "phase-actions/manage/",
        views.PhaseActionsManagementView.as_view(),
        name="phase-actions-manage",
    ),
    path(
        "phase-actions/add/",
        views.phase_action_add,
        name="phase-action-add",
    ),
    path(
        "phase-actions/remove/<int:pk>/",
        views.phase_action_remove,
        name="phase-action-remove",
    ),
    path(
        "phase-actions/reorder/",
        views.phase_action_reorder,
        name="phase-action-reorder",
    ),
    # ProjectPhaseHistory URLs
    path(
        "projectphasehistory/",
        views.ProjectPhaseHistoryListView.as_view(),
        name="projectphasehistory-list",
    ),
    path(
        "projectphasehistory/create/",
        views.ProjectPhaseHistoryCreateView.as_view(),
        name="projectphasehistory-create",
    ),
    path(
        "projectphasehistory/<int:pk>/",
        views.ProjectPhaseHistoryDetailView.as_view(),
        name="projectphasehistory-detail",
    ),
    path(
        "projectphasehistory/<int:pk>/edit/",
        views.ProjectPhaseHistoryUpdateView.as_view(),
        name="projectphasehistory-update",
    ),
    path(
        "projectphasehistory/<int:pk>/delete/",
        views.ProjectPhaseHistoryDeleteView.as_view(),
        name="projectphasehistory-delete",
    ),
    # ActionTemplate URLs (Action→Template Mappings)
    path("action-templates/", views.ActionTemplateListView.as_view(), name="actiontemplate-list"),
    path(
        "action-templates/create/",
        views.ActionTemplateCreateView.as_view(),
        name="actiontemplate-create",
    ),
    path(
        "action-templates/<int:pk>/",
        views.ActionTemplateDetailView.as_view(),
        name="actiontemplate-detail",
    ),
    path(
        "action-templates/<int:pk>/edit/",
        views.ActionTemplateUpdateView.as_view(),
        name="actiontemplate-update",
    ),
    path(
        "action-templates/<int:pk>/delete/",
        views.ActionTemplateDeleteView.as_view(),
        name="actiontemplate-delete",
    ),
    # PromptTemplate URLs
    path("prompt-templates/", views.PromptTemplateListView.as_view(), name="prompttemplate-list"),
    path(
        "prompt-templates/create/",
        views.PromptTemplateCreateView.as_view(),
        name="prompttemplate-create",
    ),
    path(
        "prompt-templates/<int:pk>/",
        views.PromptTemplateDetailView.as_view(),
        name="prompttemplate-detail",
    ),
    path(
        "prompt-templates/<int:pk>/edit/",
        views.PromptTemplateUpdateView.as_view(),
        name="prompttemplate-update",
    ),
    path(
        "prompt-templates/<int:pk>/delete/",
        views.PromptTemplateDeleteView.as_view(),
        name="prompttemplate-delete",
    ),
    # CUSTOM: Template quick-save (HTMX endpoint)
    path(
        "prompt-templates/<int:template_id>/quick-save/",
        crud_views.template_quick_save,
        name="template-quick-save",
    ),
    # ============================================================================
    # MIGRATION REGISTRY
    # ============================================================================
    path(
        "migration-registry/",
        migration_registry_views.migration_dashboard,
        name="migration-registry-dashboard",
    ),
    path(
        "migration-registry/list/",
        migration_registry_views.migration_list_partial,
        name="migration-registry-list",
    ),
    path(
        "migration-registry/<int:pk>/",
        migration_registry_views.migration_detail,
        name="migration-registry-detail",
    ),
    # ============================================================================
    # FEATURE PLANNING (Book Domain)
    # ============================================================================
    path(
        "feature-planning/",
        feature_planning_views.feature_planning_dashboard_book,
        name="feature-planning-dashboard-book",
    ),
    path(
        "feature-planning/list/",
        feature_planning_views.feature_list_partial_book,
        name="feature-planning-list",
    ),
    path(
        "feature-planning/<int:pk>/",
        feature_planning_views.feature_detail,
        name="feature-planning-detail",
    ),
    # CRUD operations
    path(
        "feature-planning/create/",
        feature_planning_views.feature_create,
        name="feature-planning-create",
    ),
    path(
        "feature-planning/<int:pk>/edit/",
        feature_planning_views.feature_update,
        name="feature-planning-update",
    ),
    path(
        "feature-planning/<int:pk>/delete/",
        feature_planning_views.feature_delete,
        name="feature-planning-delete",
    ),
    path(
        "feature-planning/<int:pk>/status/",
        feature_planning_views.feature_change_status,
        name="feature-planning-status",
    ),
    # ============================================================================
    # HANDLER TESTING (Features #28, #29, #45)
    # ============================================================================
    path("handler/test/", handler_test_view.HandlerTestView.as_view(), name="handler-test"),
    path(
        "handler/execute/", handler_test_view.HandlerExecuteView.as_view(), name="handler-execute"
    ),
    # ============================================================================
    # TEST STUDIO - Requirements & Test Generation
    # ============================================================================
    path("test-studio/", test_studio_views.requirements_list, name="test-studio"),
    path(
        "test-studio/requirements/", test_studio_views.requirements_list, name="requirements-list"
    ),
    path(
        "test-studio/requirements/create/",
        test_studio_views.requirement_create,
        name="requirement-create",
    ),
    path(
        "test-studio/requirements/<uuid:pk>/",
        test_studio_views.requirement_detail,
        name="requirement-detail",
    ),
    path(
        "test-studio/requirements/<uuid:requirement_id>/generate/<int:criterion_index>/",
        test_studio_views.generate_test,
        name="generate-test",
    ),
    path(
        "test-studio/test-cases/<uuid:pk>/",
        test_studio_views.test_case_detail,
        name="test-case-detail",
    ),
    path(
        "test-studio/test-cases/<uuid:pk>/feedback/",
        test_studio_views.testcase_add_feedback,
        name="testcase-add-feedback",
    ),
    path(
        "test-studio/testcase-feedback/<int:feedback_id>/delete/",
        test_studio_views.testcase_feedback_delete,
        name="testcase-feedback-delete",
    ),
    path(
        "test-studio/test-cases/<uuid:test_case_id>/run/",
        test_studio_views.run_test,
        name="run-test",
    ),
    path("test-studio/bug-to-test/", test_studio_views.bug_to_test, name="bug-to-test"),
    path("bugs-for-page/", test_studio_views.bugs_for_page, name="bugs-for-page"),
    path("fix-bug/<uuid:bug_id>/", test_studio_views.fix_bug, name="fix-bug"),
    path("test-studio/fix-plans/", test_studio_views.fix_plan_list, name="fix-plan-list"),
    path(
        "test-studio/fix-plans/<uuid:plan_id>/",
        test_studio_views.fix_plan_detail,
        name="fix-plan-detail",
    ),
    path(
        "test-studio/fix-plans/<uuid:plan_id>/approve/",
        test_studio_views.approve_fix_plan,
        name="approve-fix-plan",
    ),
    path(
        "test-studio/fix-plans/<uuid:plan_id>/reject/",
        test_studio_views.reject_fix_plan,
        name="reject-fix-plan",
    ),
    path(
        "test-studio/fix-plans/<uuid:plan_id>/execute/",
        test_studio_views.execute_fix_plan,
        name="execute-fix-plan",
    ),
    # ============================================================================
    # STORY ENGINE - AI Novel Generation
    # ============================================================================
    path(
        "story/bible/<int:pk>/",
        story_engine_views.story_bible_dashboard,
        name="story-bible-dashboard",
    ),
    path("story/beats/", story_engine_views.beats_list, name="beats-list"),
    path("story/beat/<int:pk>/", story_engine_views.beat_detail, name="beat-detail"),
    path(
        "story/beat/<int:beat_id>/generate/",
        story_engine_views.generate_chapter,
        name="generate-chapter",
    ),
    path("story/chapter/<int:pk>/", story_engine_views.chapter_preview, name="chapter-preview"),
    # ============================================================================
    # CONTEXT ENRICHMENT (Testing & Management)
    # ============================================================================
]

# Include Workflow Dashboard URLs (Multi-Hub Framework)
urlpatterns += [
    path("workflow/", include("apps.bfagent.urls_workflow")),
]

# Include Context Enrichment URLs
urlpatterns += [
    path("context-enrichment/", include("apps.bfagent.urls_context_enrichment")),
]

# Include Review System URLs
urlpatterns += [
    path("review/", include("apps.bfagent.urls_review")),
]

# Include Illustration System URLs
urlpatterns += [
    path("illustrations/", include(("apps.bfagent.urls_illustration", "illustration"))),
]

# Include Code Refactor API URLs
from .views import code_refactor_api
urlpatterns += [
    # Code Refactor API
    path("api/refactor/session/create/", code_refactor_api.create_session, name="refactor-create-session"),
    path("api/refactor/session/<uuid:session_id>/", code_refactor_api.get_session, name="refactor-get-session"),
    path("api/refactor/session/<uuid:session_id>/generate/", code_refactor_api.generate_proposal, name="refactor-generate"),
    path("api/refactor/session/<uuid:session_id>/approve/", code_refactor_api.approve_proposal, name="refactor-approve"),
    path("api/refactor/session/<uuid:session_id>/reject/", code_refactor_api.reject_proposal, name="refactor-reject"),
    path("api/refactor/session/<uuid:session_id>/apply/", code_refactor_api.apply_proposal, name="refactor-apply"),
    path("api/refactor/session/<uuid:session_id>/revert/", code_refactor_api.revert_proposal, name="refactor-revert"),
    path("api/refactor/session/<uuid:session_id>/diff/", code_refactor_api.get_diff, name="refactor-diff"),
    path("api/refactor/requirement/<uuid:requirement_id>/sessions/", code_refactor_api.list_sessions, name="refactor-list-sessions"),
]

# Include Autorouting API URLs
from .views import autorouting_api
urlpatterns += [
    path("api/autorouting/start/", autorouting_api.start_autorouting, name="autorouting-start"),
    path("api/autorouting/run/<uuid:run_id>/", autorouting_api.get_run_status, name="autorouting-run-status"),
    path("api/autorouting/run/<uuid:run_id>/cancel/", autorouting_api.cancel_run, name="autorouting-cancel"),
    path("api/autorouting/run/<uuid:run_id>/artifacts/", autorouting_api.get_run_artifacts, name="autorouting-artifacts"),
    path("api/autorouting/runs/", autorouting_api.list_runs, name="autorouting-list-runs"),
]
