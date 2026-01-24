"""
URL configuration for Writing Hub
Complete Book Writing Workflow
"""

from django.urls import path
from . import views
from . import views_idea_generation as idea_views
from . import views_import
from . import views_import_v2
from . import views_agents
from . import views_style_lab as style_lab
from . import views_creative as creative
from . import views_lektorat as lektorat
from . import views_world as world

app_name = "writing_hub"

urlpatterns = [
    # ==========================================================================
    # Idea Generation Wizard (NEW - Pre-Project Ideation)
    # ==========================================================================
    path("ideas/", idea_views.IdeaWizardStartView.as_view(), name="idea-wizard-start"),
    path("ideas/create/<slug:content_type_slug>/", idea_views.IdeaWizardCreateView.as_view(), name="idea-wizard-create"),
    path("ideas/<int:session_id>/", idea_views.IdeaWizardStepView.as_view(), name="idea-wizard-step"),
    path("ideas/<int:session_id>/save/", idea_views.IdeaWizardSaveResponseView.as_view(), name="idea-wizard-save"),
    path("ideas/<int:session_id>/generate/", idea_views.IdeaWizardGenerateAIView.as_view(), name="idea-wizard-generate"),
    path("ideas/<int:session_id>/navigate/", idea_views.IdeaWizardNavigateView.as_view(), name="idea-wizard-navigate"),
    path("ideas/<int:session_id>/summary/", idea_views.IdeaWizardSummaryView.as_view(), name="idea-wizard-summary"),
    
    # ==========================================================================
    # Creative Agent (Kreativ-Phase - Buchideen-Brainstorming)
    # ==========================================================================
    path("creative/", creative.creative_dashboard, name="creative-dashboard"),
    path("creative/new/", creative.creative_session_create, name="creative-create"),
    path("creative/<uuid:session_id>/", creative.creative_session_detail, name="creative-session"),
    path("creative/<uuid:session_id>/message/", creative.creative_send_message, name="creative-message"),
    path("creative/<uuid:session_id>/idea/<uuid:idea_id>/rate/", creative.creative_rate_idea, name="creative-rate-idea"),
    path("creative/<uuid:session_id>/idea/<uuid:idea_id>/select/", creative.creative_select_idea, name="creative-select-idea"),
    path("creative/<uuid:session_id>/idea/<uuid:idea_id>/delete/", creative.creative_delete_idea, name="creative-delete-idea"),
    path("creative/<uuid:session_id>/create-project/", creative.creative_create_project, name="creative-create-project"),

    # Dashboard & Projects
    path("", views.dashboard, name="dashboard"),
    path("projects/", views.projects_list, name="projects_list"),
    path("projects/new/", views.project_wizard, name="project_wizard"),
    path("projects/<int:project_id>/delete/", views.delete_project, name="delete_project"),
    
    # ==========================================================================
    # Project Import V1 (Legacy - from existing manuscripts/planning docs)
    # ==========================================================================
    path("projects/import/", views_import.import_project_start, name="import_project_start"),
    path("projects/import/analyze/", views_import.import_project_analyze, name="import_project_analyze"),
    path("projects/import/preview/", views_import.import_project_preview, name="import_project_preview"),
    path("projects/import/create/", views_import.import_project_create, name="import_project_create"),
    path("projects/import/cancel/", views_import.import_project_cancel, name="import_project_cancel"),
    
    # ==========================================================================
    # Project Import V2 (Smart Import with Multi-Step LLM Pipeline)
    # ==========================================================================
    path("projects/import-v2/", views_import_v2.import_v2_start, name="import_v2_start"),
    path("projects/import-v2/analyze/", views_import_v2.import_v2_analyze, name="import_v2_analyze"),
    path("projects/import-v2/review/", views_import_v2.import_v2_review, name="import_v2_review"),
    path("projects/import-v2/outline/", views_import_v2.import_v2_outline, name="import_v2_outline"),
    path("projects/import-v2/create/", views_import_v2.import_v2_create, name="import_v2_create"),
    # V2 API endpoints
    path("api/import-v2/analyze/", views_import_v2.import_v2_api_analyze, name="import_v2_api_analyze"),
    path("api/import-v2/status/", views_import_v2.import_v2_api_status, name="import_v2_api_status"),
    
    # ==========================================================================
    # Import into EXISTING Project (supplement, don't overwrite)
    # ==========================================================================
    path("project/<int:project_id>/import/", views_import.import_to_project_start, name="import_to_project_start"),
    path("project/<int:project_id>/import/analyze/", views_import.import_to_project_analyze, name="import_to_project_analyze"),
    path("project/<int:project_id>/import/preview/", views_import.import_to_project_preview, name="import_to_project_preview"),
    path("project/<int:project_id>/import/merge/", views_import.import_to_project_merge, name="import_to_project_merge"),
    
    # Project Hub (Central Navigation)
    path("project/<int:project_id>/", views.project_hub, name="project_hub"),
    
    # Phase 1: Planning
    path("project/<int:project_id>/planning/", views.planning_editor, name="planning_editor"),
    path("project/<int:project_id>/planning/save/", views.save_planning, name="save_planning"),
    path("project/<int:project_id>/planning/generate/", views.generate_planning, name="generate_planning"),
    path("project/<int:project_id>/apply-style-template/", views.apply_style_template, name="apply_style_template"),
    
    # Phase 2: Characters
    path("project/<int:project_id>/characters/", views.character_editor, name="character_editor"),
    path("project/<int:project_id>/characters/<int:character_id>/", views.get_character, name="get_character"),
    path("project/<int:project_id>/characters/save/", views.save_character, name="save_character"),
    path("project/<int:project_id>/characters/<int:character_id>/delete/", views.delete_character, name="delete_character"),
    path("project/<int:project_id>/characters/generate/", views.generate_characters, name="generate_characters"),
    path("project/<int:project_id>/characters/generate-details/", views.generate_character_details, name="generate_character_details"),
    
    # Phase 3: World Building
    path("project/<int:project_id>/world/", views.world_editor, name="world_editor"),
    path("project/<int:project_id>/world/<int:world_id>/", views.get_world, name="get_world"),
    path("project/<int:project_id>/world/<int:world_id>/delete/", views.delete_world, name="delete_world"),
    path("project/<int:project_id>/world/save/", views.save_world, name="save_world"),
    path("project/<int:project_id>/world/generate/", views.generate_world, name="generate_world"),
    path("project/<int:project_id>/world/generate-details/", views.generate_world_details, name="generate_world_details"),
    
    # Phase 4: Outline Editor
    path("outline/<int:project_id>/", views.outline_editor, name="outline_editor"),
    path("outline/<int:project_id>/save/", views.save_outline, name="save_outline"),
    path("outline/<int:project_id>/convert/", views.convert_framework, name="convert_framework"),
    path("outline/<int:project_id>/versions/", views.get_versions, name="get_versions"),
    path("outline/<int:project_id>/versions/save/", views.save_version, name="save_version"),
    path("outline/<int:project_id>/versions/<int:version_id>/restore/", views.restore_version, name="restore_version"),
    path("outline/<int:project_id>/versions/<int:version_id>/status/", views.update_version_status, name="update_version_status"),
    path("outline/<int:project_id>/versions/<int:version_id>/feedback/", views.save_feedback, name="save_feedback"),
    path("outline/<int:project_id>/versions/<int:version_id>/apply-revision/", views.apply_feedback_revision, name="apply_feedback_revision"),
    
    # AI Generation for Outline
    path("outline/<int:project_id>/ai/generate/", views.generate_ai_content, name="generate_ai_content"),
    path("outline/<int:project_id>/ai/generate-field/", views.generate_ai_content, name="generate_ai_field"),
    path("outline/<int:project_id>/ai/full-outline/", views.generate_full_outline, name="generate_full_outline"),
    
    # Phase 5: Chapter Writer
    path("project/<int:project_id>/write/", views.chapter_writer, name="chapter_writer"),
    path("project/<int:project_id>/chapters/<int:chapter_id>/save/", views.save_chapter_content, name="save_chapter_content"),
    path("project/<int:project_id>/chapters/<int:chapter_id>/generate/", views.generate_chapter_content, name="generate_chapter_content"),
    path("project/<int:project_id>/chapters/generate-all/", views.generate_all_chapters, name="generate_all_chapters"),
    
    # Phase 6: Review (MVP)
    path("project/<int:project_id>/review/", views.review_dashboard, name="review_dashboard"),
    path("project/<int:project_id>/review/<int:chapter_id>/", views.review_chapter, name="review_chapter"),
    path("project/<int:project_id>/review/<int:chapter_id>/feedback/", views.add_feedback, name="add_feedback"),
    path("project/<int:project_id>/feedback/<int:feedback_id>/resolve/", views.resolve_feedback, name="resolve_feedback"),
    path("project/<int:project_id>/feedback/<int:feedback_id>/delete/", views.delete_feedback, name="delete_feedback"),
    # Project-level feedback
    path("project/<int:project_id>/project-feedback/add/", views.add_project_feedback, name="add_project_feedback"),
    path("project/<int:project_id>/project-feedback/<int:feedback_id>/resolve/", views.resolve_project_feedback, name="resolve_project_feedback"),
    path("project/<int:project_id>/project-feedback/<int:feedback_id>/delete/", views.delete_project_feedback, name="delete_project_feedback"),
    
    # Phase 6.5: Editing/Redaktion (MVP)
    path("project/<int:project_id>/editing/", views.editing_dashboard, name="editing_dashboard"),
    path("project/<int:project_id>/editing/<int:chapter_id>/", views.editing_chapter, name="editing_chapter"),
    path("project/<int:project_id>/editing/<int:chapter_id>/analyze/", views.analyze_chapter, name="analyze_chapter"),
    path("project/<int:project_id>/editing/<int:chapter_id>/apply-all/", views.apply_all_suggestions, name="apply_all_suggestions"),
    path("project/<int:project_id>/editing/analyze-all/", views.analyze_all_chapters, name="analyze_all_chapters"),
    path("project/<int:project_id>/suggestion/<int:suggestion_id>/apply/", views.apply_suggestion, name="apply_suggestion"),
    path("project/<int:project_id>/suggestion/<int:suggestion_id>/reject/", views.reject_suggestion, name="reject_suggestion"),
    
    # Phase 6b: Manuscript Preview (komplettes Werk lesen)
    path("project/<int:project_id>/manuscript/", views.manuscript_preview, name="manuscript_preview"),
    
    # Phase 6c: Versioning (MVP)
    path("project/<int:project_id>/versions/", views.versions_dashboard, name="versions_dashboard"),
    path("project/<int:project_id>/versions/create/", views.create_version, name="create_version"),
    path("project/<int:project_id>/versions/<int:version_id>/restore/", views.restore_version, name="restore_version"),
    path("project/<int:project_id>/versions/<int:version_id>/compare/", views.compare_versions, name="compare_versions"),
    
    # Phase 6d: Illustration
    path("project/<int:project_id>/illustration/", views.illustration_dashboard, name="illustration_dashboard"),
    path("project/<int:project_id>/illustration/style/save/", views.save_illustration_style, name="save_illustration_style"),
    path("project/<int:project_id>/illustration/<int:chapter_id>/generate/", views.generate_chapter_illustration, name="generate_chapter_illustration"),
    path("project/<int:project_id>/illustration/<int:chapter_id>/analyze/", views.analyze_chapter_scenes, name="analyze_chapter_scenes"),
    path("project/<int:project_id>/illustration/<int:chapter_id>/gallery/", views.chapter_images_gallery, name="chapter_images_gallery"),
    path("project/<int:project_id>/illustration/<int:chapter_id>/analyze/content/", views.analyze_chapter_content, name="analyze_chapter_content"),
    path("project/<int:project_id>/illustration/analyze-all-scenes/", views.analyze_all_chapters_scenes, name="analyze_all_chapters_scenes"),
    path("project/<int:project_id>/illustration/<int:chapter_id>/scenes/", views.get_chapter_scenes, name="get_chapter_scenes"),
    path("project/<int:project_id>/illustration/<int:chapter_id>/generate-scene/", views.generate_scene_illustration, name="generate_scene_illustration"),
    path("illustration/<int:illustration_id>/delete/", views.delete_illustration, name="delete_illustration"),
    path("illustration/<int:illustration_id>/select/", views.select_illustration, name="select_illustration"),
    path("illustration/<int:illustration_id>/caption/", views.update_illustration_caption, name="update_illustration_caption"),
    path("project/<int:project_id>/illustration/<int:chapter_id>/generate-all-scenes/", views.generate_all_chapter_scenes, name="generate_all_chapter_scenes"),
    path("project/<int:project_id>/illustration/<int:chapter_id>/insert-images/", views.insert_chapter_images, name="insert_chapter_images"),
    path("project/<int:project_id>/illustration/<int:chapter_id>/remove-images/", views.remove_chapter_images, name="remove_chapter_images"),
    path("project/<int:project_id>/illustration/<int:chapter_id>/preview/", views.chapter_preview_with_images, name="chapter_preview_with_images"),
    path("project/<int:project_id>/illustration/generate-all-chapters/", views.generate_all_project_chapters, name="generate_all_project_chapters"),
    path("project/<int:project_id>/illustration/illustrate-all-chapters/", views.illustrate_all_chapters, name="illustrate_all_chapters"),
    path("project/<int:project_id>/illustration/reillustrate-all-chapters/", views.reillustrate_all_chapters, name="reillustrate_all_chapters"),
    path("project/<int:project_id>/illustration/figure-index/", views.generate_figure_index, name="generate_figure_index"),
    
    # Illustration System (AI-powered image generation)
    path("project/<int:project_id>/prompt-system/", views.prompt_system_setup, name="prompt_system_setup"),
    path("project/<int:project_id>/prompt-system/master-style/save/", views.save_master_style, name="save_master_style"),
    path("project/<int:project_id>/prompt-system/master-style/generate-preview/", views.generate_master_style_preview, name="generate_master_style_preview"),
    path("project/<int:project_id>/prompt-system/character/save/", views.save_prompt_character, name="save_prompt_character"),
    path("project/<int:project_id>/prompt-system/character/optimize-with-ai/", views.optimize_character_with_ai, name="optimize_character_with_ai"),
    path("project/<int:project_id>/prompt-system/character/<int:character_id>/", views.get_prompt_character, name="get_prompt_character"),
    path("project/<int:project_id>/prompt-system/character/<int:character_id>/delete/", views.delete_prompt_character, name="delete_prompt_character"),
    path("project/<int:project_id>/prompt-system/character/<int:character_id>/generate-portrait/", views.generate_character_portrait, name="generate_character_portrait"),
    path("project/<int:project_id>/prompt-system/location/save/", views.save_prompt_location, name="save_prompt_location"),
    path("project/<int:project_id>/prompt-system/location/optimize-with-ai/", views.optimize_location_with_ai, name="optimize_location_with_ai"),
    path("project/<int:project_id>/prompt-system/location/<int:location_id>/", views.get_prompt_location, name="get_prompt_location"),
    path("project/<int:project_id>/prompt-system/location/<int:location_id>/delete/", views.delete_prompt_location, name="delete_prompt_location"),
    path("project/<int:project_id>/prompt-system/location/<int:location_id>/generate-preview/", views.generate_location_preview, name="generate_location_preview"),
    path("project/<int:project_id>/prompt-system/load-preset/", views.load_prompt_preset, name="load_prompt_preset"),
    path("project/<int:project_id>/prompt-system/generate-with-ai/", views.generate_prompt_system_with_ai, name="generate_prompt_system_with_ai"),
    path("project/<int:project_id>/prompt-system/extract-characters/", views.extract_characters_from_book, name="extract_characters_from_book"),
    path("project/<int:project_id>/prompt-system/extract-locations/", views.extract_locations_from_book, name="extract_locations_from_book"),
    path("project/<int:project_id>/prompt-system/extract-elements/", views.extract_elements_from_book, name="extract_elements_from_book"),
    path("project/<int:project_id>/prompt-system/suggest-from-book/", views.suggest_style_from_book, name="suggest_style_from_book"),
    path("project/<int:project_id>/prompt-system/optimize-master-style/", views.optimize_master_style_with_ai, name="optimize_master_style_with_ai"),
    
    # Illustration Style Templates
    path("style-templates/", views.list_style_templates, name="list_style_templates"),
    path("project/<int:project_id>/style-templates/save/", views.save_style_template, name="save_style_template"),
    path("project/<int:project_id>/style-templates/apply/", views.apply_style_template_legacy, name="apply_style_template_legacy"),
    path("style-templates/<int:template_id>/delete/", views.delete_style_template, name="delete_style_template"),
    
    # Book Series (Buchreihen / Universes)
    path("series/", views.series_dashboard, name="series_dashboard"),
    path("series/create/", views.series_create, name="series_create"),
    path("series/<uuid:series_id>/", views.series_detail, name="series_detail"),
    path("series/<uuid:series_id>/update/", views.series_update, name="series_update"),
    path("series/<uuid:series_id>/ai-enhance/", views.series_ai_enhance, name="series_ai_enhance"),
    path("series/<uuid:series_id>/add-project/", views.series_add_project, name="series_add_project"),
    path("series/<uuid:series_id>/remove-project/<int:project_id>/", views.series_remove_project, name="series_remove_project"),
    path("series/<uuid:series_id>/reorder-projects/", views.series_reorder_projects, name="series_reorder_projects"),
    # Series Characters
    path("series/<uuid:series_id>/characters/add/", views.series_add_character, name="series_add_character"),
    path("series/<uuid:series_id>/characters/<uuid:character_id>/update/", views.series_update_character, name="series_update_character"),
    path("series/<uuid:series_id>/characters/<uuid:character_id>/delete/", views.series_delete_character, name="series_delete_character"),
    # Series Worlds
    path("series/<uuid:series_id>/worlds/add/", views.series_add_world, name="series_add_world"),
    path("series/<uuid:series_id>/worlds/<uuid:world_id>/update/", views.series_update_world, name="series_update_world"),
    path("series/<uuid:series_id>/worlds/<uuid:world_id>/delete/", views.series_delete_world, name="series_delete_world"),
    
    # Phase 7: Publishing
    path("project/<int:project_id>/publishing/", views.publishing_setup, name="publishing_setup"),
    path("project/<int:project_id>/publishing/save-metadata/", views.save_publishing_metadata, name="save_publishing_metadata"),
    path("project/<int:project_id>/publishing/save-author/", views.save_author_profile, name="save_author_profile"),
    path("project/<int:project_id>/publishing/generate-keywords/", views.generate_publishing_keywords, name="generate_publishing_keywords"),
    path("project/<int:project_id>/publishing/generate-cover/", views.generate_book_cover, name="generate_book_cover"),
    path("project/<int:project_id>/publishing/upload-cover/", views.upload_book_cover, name="upload_book_cover"),
    path("project/<int:project_id>/publishing/matter/<str:position>/<str:page_type>/", views.get_matter_content, name="get_matter_content"),
    path("project/<int:project_id>/publishing/matter/<str:position>/<str:page_type>/save/", views.save_matter_content, name="save_matter_content"),
    path("project/<int:project_id>/publishing/matter/<str:position>/<str:page_type>/toggle/", views.toggle_matter, name="toggle_matter"),
    path("project/<int:project_id>/publishing/generate-matter/", views.generate_matter_content, name="generate_matter_content"),
    path("project/<int:project_id>/publishing/generate-author-bio/", views.generate_author_bio, name="generate_author_bio"),
    
    # Phase 8: Export
    path("project/<int:project_id>/export/", views.export_dialog, name="export_dialog"),
    path("project/<int:project_id>/export/download/", views.export_manuscript, name="export_manuscript"),
    
    # LLM Management
    path("llm-setup/", views.llm_setup, name="llm_setup"),
    path("llm-setup/add/", views.llm_add, name="llm_add"),
    path("llm-setup/test/<int:llm_id>/", views.llm_test, name="llm_test"),
    
    # ==========================================================================
    # Agent Configuration & Pipeline Execution
    # ==========================================================================
    path("project/<int:project_id>/agents/", views_agents.project_agent_config, name="project_agent_config"),
    path("project/<int:project_id>/agents/save/", views_agents.save_agent_config, name="save_agent_config"),
    path("project/<int:project_id>/agents/reset/", views_agents.reset_agent_config, name="reset_agent_config"),
    path("project/<int:project_id>/agents/execute/", views_agents.execute_pipeline, name="execute_pipeline"),
    path("project/<int:project_id>/agents/history/", views_agents.pipeline_history, name="pipeline_history"),
    path("api/pipelines/", views_agents.get_available_pipelines, name="get_pipelines"),
    
    # Author API (for Style Lab)
    path("api/authors/", style_lab.author_api, name="author-api-list"),
    path("api/authors/<uuid:author_id>/", style_lab.author_api_detail, name="author-api-detail"),
    path("api/style-dna/<uuid:dna_id>/assign-author/", style_lab.style_dna_assign_author, name="style-dna-assign-author"),
    
    # ==========================================================================
    # Style Lab (Style Generation & Adoption System)
    # ==========================================================================
    path("style-lab/", style_lab.style_lab_dashboard, name="style-lab-dashboard"),
    
    # Style Builder (NEW - Iterative Style Creation)
    path("style-lab/builder/", style_lab.style_builder, name="style-builder"),
    path("style-lab/builder/<uuid:dna_id>/", style_lab.style_builder, name="style-builder-refine"),
    path("style-lab/builder/extract/", style_lab.style_builder_extract, name="style-builder-extract"),
    path("style-lab/builder/test/", style_lab.style_builder_test, name="style-builder-test"),
    path("style-lab/builder/save/", style_lab.style_builder_save, name="style-builder-save"),
    path("style-lab/builder/reset/", style_lab.style_builder_reset, name="style-builder-reset"),
    
    # Style DNA
    path("style-lab/dna/", style_lab.style_dna_list, name="style-dna-list"),
    path("style-lab/dna/create/", style_lab.style_dna_create, name="style-dna-create"),
    path("style-lab/dna/<uuid:dna_id>/", style_lab.style_dna_detail, name="style-dna-detail"),
    path("style-lab/dna/<uuid:dna_id>/edit/", style_lab.style_dna_edit, name="style-dna-edit"),
    path("style-lab/dna/<uuid:dna_id>/delete/", style_lab.style_dna_delete, name="style-dna-delete"),
    path("style-lab/dna/<uuid:dna_id>/duplicate/", style_lab.style_dna_duplicate, name="style-dna-duplicate"),
    path("style-lab/dna/<uuid:dna_id>/test/", style_lab.style_dna_test, name="style-dna-test"),
    path("style-lab/dna/<uuid:dna_id>/sample/", style_lab.style_dna_generate_sample, name="style-dna-generate-sample"),
    
    # Lab Sessions
    path("style-lab/sessions/", style_lab.session_list, name="session-list"),
    path("style-lab/sessions/create/", style_lab.session_create, name="session-create"),
    path("style-lab/sessions/<uuid:session_id>/", style_lab.session_detail, name="session-detail"),
    path("style-lab/sessions/<uuid:session_id>/advance/", style_lab.session_advance_phase, name="session-advance"),
    path("style-lab/sessions/<uuid:session_id>/previous/", style_lab.session_previous_phase, name="session-previous"),
    
    # Extraction Phase
    path("style-lab/sessions/<uuid:session_id>/extraction/add/", style_lab.extraction_add_text, name="extraction-add"),
    path("style-lab/sessions/<uuid:session_id>/extraction/analyze/", style_lab.extraction_analyze, name="extraction-analyze"),
    
    # Synthesis Phase
    path("style-lab/sessions/<uuid:session_id>/synthesis/generate/", style_lab.synthesis_generate, name="synthesis-generate"),
    path("style-lab/candidates/<uuid:candidate_id>/delete/", style_lab.synthesis_delete_candidate, name="synthesis-delete-candidate"),
    
    # Feedback Phase
    path("style-lab/candidates/<uuid:candidate_id>/feedback/", style_lab.feedback_candidate, name="feedback-candidate"),
    
    # Fixation Phase
    path("style-lab/sessions/<uuid:session_id>/fixation/create-dna/", style_lab.fixation_create_dna, name="fixation-create-dna"),
    
    # HTMX Partials
    path("style-lab/htmx/observation/<uuid:observation_id>/", style_lab.htmx_observation_card, name="htmx-observation"),
    path("style-lab/htmx/candidate/<uuid:candidate_id>/", style_lab.htmx_candidate_card, name="htmx-candidate"),
    path("style-lab/htmx/session/<uuid:session_id>/progress/", style_lab.htmx_phase_progress, name="htmx-phase-progress"),
    
    # Sprint 1: Interaktives Satz-Feedback (HTMX)
    path("style-lab/candidates/<uuid:candidate_id>/interactive/", style_lab.synthesis_interactive, name="synthesis-interactive"),
    path("style-lab/htmx/sentence/<uuid:candidate_id>/<int:sentence_index>/", style_lab.htmx_sentence_feedback, name="htmx-sentence-feedback"),
    path("style-lab/htmx/stats/<uuid:candidate_id>/", style_lab.htmx_feedback_stats, name="htmx-feedback-stats"),
    
    # Sprint 2: Consolidation Phase
    path("style-lab/sessions/<uuid:session_id>/consolidation/", style_lab.consolidation_view, name="consolidation"),
    
    # Sprint 3: Fixation mit Live Preview
    path("style-lab/sessions/<uuid:session_id>/fixation/", style_lab.fixation_view, name="fixation"),
    
    # ==========================================================================
    # World Building (Projektunabhängige Welten)
    # ==========================================================================
    path("worlds/", world.world_dashboard, name="world-dashboard"),
    path("worlds/create/", world.world_create, name="world-create"),
    path("worlds/<uuid:world_id>/", world.world_detail, name="world-detail"),
    path("worlds/<uuid:world_id>/edit/", world.world_edit, name="world-edit"),
    path("worlds/<uuid:world_id>/delete/", world.world_delete, name="world-delete"),
    path("worlds/<uuid:world_id>/duplicate/", world.world_duplicate, name="world-duplicate"),
    
    # World AJAX Endpoints
    path("worlds/save/", world.world_save_ajax, name="world-save-ajax"),
    path("worlds/<uuid:world_id>/location/save/", world.location_save_ajax, name="location-save-ajax"),
    path("worlds/<uuid:world_id>/location/<uuid:location_id>/delete/", world.location_delete_ajax, name="location-delete-ajax"),
    path("worlds/<uuid:world_id>/rule/save/", world.rule_save_ajax, name="rule-save-ajax"),
    path("worlds/<uuid:world_id>/rule/<uuid:rule_id>/delete/", world.rule_delete_ajax, name="rule-delete-ajax"),
    
    # Project-World Linking
    path("project/<int:project_id>/worlds/", world.project_worlds_list, name="project-worlds-list"),
    path("project/<int:project_id>/worlds/<uuid:world_id>/assign/", world.project_world_assign, name="project-world-assign"),
    path("project/<int:project_id>/worlds/<uuid:world_id>/unassign/", world.project_world_unassign, name="project-world-unassign"),
    
    # World AI Generation (via LLMAgent)
    path("worlds/ai/generate/", world.world_generate_ai, name="world-generate-ai"),
    path("worlds/<uuid:world_id>/ai/expand/", world.world_expand_aspect_ai, name="world-expand-ai"),
    path("worlds/<uuid:world_id>/ai/locations/", world.world_generate_locations_ai, name="world-locations-ai"),
    path("worlds/<uuid:world_id>/ai/rules/", world.world_generate_rules_ai, name="world-rules-ai"),
    path("worlds/<uuid:world_id>/ai/consistency/", world.world_check_consistency_ai, name="world-consistency-ai"),
    path("worlds/<uuid:world_id>/ai/apply-suggestions/", world.world_apply_suggestions_ai, name="world-apply-suggestions-ai"),
    
    # ==========================================================================
    # Lektorats-Framework (Systematische Qualitätssicherung)
    # ==========================================================================
    path("project/<int:project_id>/lektorat/", lektorat.lektorat_dashboard, name="lektorat_dashboard"),
    path("project/<int:project_id>/lektorat/session/create/", lektorat.lektorat_create_session, name="lektorat_create_session"),
    
    # Modul 1: Figuren
    path("project/<int:project_id>/lektorat/figuren/", lektorat.lektorat_figuren, name="lektorat_figuren"),
    path("project/<int:project_id>/lektorat/figuren/analyze/", lektorat.lektorat_figuren_analyze, name="lektorat_figuren_analyze"),
    path("project/<int:project_id>/lektorat/figuren/save/", lektorat.lektorat_figur_save, name="lektorat_figur_save"),
    path("project/<int:project_id>/lektorat/figuren/<int:figur_id>/delete/", lektorat.lektorat_figur_delete, name="lektorat_figur_delete"),
    
    # Modul 2: Stilkonsistenz
    path("project/<int:project_id>/lektorat/stil/analyze/", lektorat.lektorat_stil_analyze, name="lektorat_stil_analyze"),
    
    # Modul 3: Handlungslogik
    path("project/<int:project_id>/lektorat/logik/analyze/", lektorat.lektorat_logik_analyze, name="lektorat_logik_analyze"),
    
    # Modul 4: Wiederholungen
    path("project/<int:project_id>/lektorat/wiederholungen/analyze/", lektorat.lektorat_wiederholungen_analyze, name="lektorat_wiederholungen_analyze"),
    
    # Modul 5: Zeitlinien
    path("project/<int:project_id>/lektorat/zeitlinien/analyze/", lektorat.lektorat_zeitlinien_analyze, name="lektorat_zeitlinien_analyze"),
    
    # Ergebnis-Ansichten
    path("project/<int:project_id>/lektorat/ergebnisse/<str:modul_id>/", lektorat.lektorat_ergebnisse, name="lektorat_ergebnisse"),
    
    # Fehler-Management
    path("project/<int:project_id>/lektorat/fehler/", lektorat.lektorat_fehler_list, name="lektorat_fehler_list"),
    path("project/<int:project_id>/lektorat/fehler/create/", lektorat.lektorat_fehler_create, name="lektorat_fehler_create"),
    path("project/<int:project_id>/lektorat/fehler/<int:fehler_id>/update/", lektorat.lektorat_fehler_update, name="lektorat_fehler_update"),
    path("project/<int:project_id>/lektorat/fehler/<int:fehler_id>/ai-correct/", lektorat.lektorat_fehler_ai_correct, name="lektorat_fehler_ai_correct"),
    
    # HTMX Partials
    path("project/<int:project_id>/lektorat/htmx/stats/", lektorat.lektorat_stats_partial, name="lektorat_stats_partial"),
    path("project/<int:project_id>/lektorat/htmx/modul/<str:modul_id>/", lektorat.lektorat_modul_status_partial, name="lektorat_modul_status_partial"),
    
    # Korrektur-System
    path("project/<int:project_id>/lektorat/korrekturen/", lektorat.correction_dashboard, name="correction_dashboard"),
    path("project/<int:project_id>/lektorat/korrekturen/generate/", lektorat.correction_generate, name="correction_generate"),
    path("project/<int:project_id>/lektorat/korrekturen/fehler/<int:fehler_id>/", lektorat.correction_detail, name="correction_detail"),
    path("project/<int:project_id>/lektorat/korrekturen/fehler/<int:fehler_id>/generate/", lektorat.correction_generate_single, name="correction_generate_single"),
    path("project/<int:project_id>/lektorat/korrekturen/fehler/<int:fehler_id>/regenerate/", lektorat.correction_regenerate, name="correction_regenerate"),
    path("project/<int:project_id>/lektorat/korrekturen/apply/<int:suggestion_id>/", lektorat.correction_apply, name="correction_apply"),
]
