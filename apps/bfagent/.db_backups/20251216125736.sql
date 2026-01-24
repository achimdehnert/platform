/*
SQLite Backup
Database: main
Backup Time: 2025-12-16 12:58:00
*/

DROP TABLE IF EXISTS "main"."action_templates";
DROP TABLE IF EXISTS "main"."agent_actions";
DROP TABLE IF EXISTS "main"."agent_artifacts";
DROP TABLE IF EXISTS "main"."agent_types";
DROP TABLE IF EXISTS "main"."agents";
DROP TABLE IF EXISTS "main"."auth_group";
DROP TABLE IF EXISTS "main"."auth_group_permissions";
DROP TABLE IF EXISTS "main"."auth_permission";
DROP TABLE IF EXISTS "main"."auth_user";
DROP TABLE IF EXISTS "main"."auth_user_groups";
DROP TABLE IF EXISTS "main"."auth_user_user_permissions";
DROP TABLE IF EXISTS "main"."authtoken_token";
DROP TABLE IF EXISTS "main"."bfagent_bugfixplan";
DROP TABLE IF EXISTS "main"."bfagent_chapterrating";
DROP TABLE IF EXISTS "main"."bfagent_comment";
DROP TABLE IF EXISTS "main"."bfagent_component_change_log";
DROP TABLE IF EXISTS "main"."bfagent_component_registry";
DROP TABLE IF EXISTS "main"."bfagent_component_usage_log";
DROP TABLE IF EXISTS "main"."bfagent_contextenrichmentlog";
DROP TABLE IF EXISTS "main"."bfagent_contextschema";
DROP TABLE IF EXISTS "main"."bfagent_contextsource";
DROP TABLE IF EXISTS "main"."bfagent_feature_document";
DROP TABLE IF EXISTS "main"."bfagent_feature_document_keyword";
DROP TABLE IF EXISTS "main"."bfagent_generatedimage";
DROP TABLE IF EXISTS "main"."bfagent_imagegenerationbatch";
DROP TABLE IF EXISTS "main"."bfagent_imagestyleprofile";
DROP TABLE IF EXISTS "main"."bfagent_migration_conflict";
DROP TABLE IF EXISTS "main"."bfagent_migration_registry";
DROP TABLE IF EXISTS "main"."bfagent_requirementtestlink";
DROP TABLE IF EXISTS "main"."bfagent_reviewparticipant";
DROP TABLE IF EXISTS "main"."bfagent_reviewround";
DROP TABLE IF EXISTS "main"."bfagent_testbug";
DROP TABLE IF EXISTS "main"."bfagent_testcase";
DROP TABLE IF EXISTS "main"."bfagent_testcoveragereport";
DROP TABLE IF EXISTS "main"."bfagent_testexecution";
DROP TABLE IF EXISTS "main"."bfagent_testlog";
DROP TABLE IF EXISTS "main"."bfagent_testrequirement";
DROP TABLE IF EXISTS "main"."bfagent_testscreenshot";
DROP TABLE IF EXISTS "main"."bfagent_testsession";
DROP TABLE IF EXISTS "main"."book_characters_v2";
DROP TABLE IF EXISTS "main"."book_statuses";
DROP TABLE IF EXISTS "main"."book_type_phases";
DROP TABLE IF EXISTS "main"."book_types";
DROP TABLE IF EXISTS "main"."cad_analysis_category";
DROP TABLE IF EXISTS "main"."cad_analysis_jobs";
DROP TABLE IF EXISTS "main"."cad_analysis_reports";
DROP TABLE IF EXISTS "main"."cad_analysis_results";
DROP TABLE IF EXISTS "main"."cad_building_type";
DROP TABLE IF EXISTS "main"."cad_compliance_standard";
DROP TABLE IF EXISTS "main"."cad_drawing_files";
DROP TABLE IF EXISTS "main"."cad_drawing_type";
DROP TABLE IF EXISTS "main"."cad_layer_standard";
DROP TABLE IF EXISTS "main"."cad_severity_level";
DROP TABLE IF EXISTS "main"."chapters_v2";
DROP TABLE IF EXISTS "main"."characters_v2";
DROP TABLE IF EXISTS "main"."checklist_instances";
DROP TABLE IF EXISTS "main"."checklist_item_statuses";
DROP TABLE IF EXISTS "main"."checklist_items";
DROP TABLE IF EXISTS "main"."checklist_templates";
DROP TABLE IF EXISTS "main"."comic_dialogues";
DROP TABLE IF EXISTS "main"."comic_panels";
DROP TABLE IF EXISTS "main"."compliance_audit_log";
DROP TABLE IF EXISTS "main"."compliance_incident_severity";
DROP TABLE IF EXISTS "main"."compliance_priority";
DROP TABLE IF EXISTS "main"."compliance_risk_level";
DROP TABLE IF EXISTS "main"."compliance_status";
DROP TABLE IF EXISTS "main"."compliance_tag";
DROP TABLE IF EXISTS "main"."compliance_tagged_item";
DROP TABLE IF EXISTS "main"."content_blocks";
DROP TABLE IF EXISTS "main"."core_agent_executions";
DROP TABLE IF EXISTS "main"."core_contentitem";
DROP TABLE IF EXISTS "main"."core_customers";
DROP TABLE IF EXISTS "main"."core_locations";
DROP TABLE IF EXISTS "main"."core_plugin_configurations";
DROP TABLE IF EXISTS "main"."core_plugin_executions";
DROP TABLE IF EXISTS "main"."core_plugin_registry";
DROP TABLE IF EXISTS "main"."core_plugin_registry_depends_on";
DROP TABLE IF EXISTS "main"."core_prompt_executions";
DROP TABLE IF EXISTS "main"."core_prompt_templates";
DROP TABLE IF EXISTS "main"."core_prompt_versions";
DROP TABLE IF EXISTS "main"."debug_toolbar_historyentry";
DROP TABLE IF EXISTS "main"."django_admin_log";
DROP TABLE IF EXISTS "main"."django_content_type";
DROP TABLE IF EXISTS "main"."django_migrations";
DROP TABLE IF EXISTS "main"."django_session";
DROP TABLE IF EXISTS "main"."domain_arts";
DROP TABLE IF EXISTS "main"."domain_arts_copy1";
DROP TABLE IF EXISTS "main"."domain_phases";
DROP TABLE IF EXISTS "main"."domain_projects";
DROP TABLE IF EXISTS "main"."domain_section_items";
DROP TABLE IF EXISTS "main"."domain_sections";
DROP TABLE IF EXISTS "main"."domain_types";
DROP TABLE IF EXISTS "main"."dsb_branche";
DROP TABLE IF EXISTS "main"."dsb_datenkategorie";
DROP TABLE IF EXISTS "main"."dsb_dokument";
DROP TABLE IF EXISTS "main"."dsb_mandant";
DROP TABLE IF EXISTS "main"."dsb_mandant_tom";
DROP TABLE IF EXISTS "main"."dsb_rechtsform";
DROP TABLE IF EXISTS "main"."dsb_rechtsgrundlage";
DROP TABLE IF EXISTS "main"."dsb_tom_kategorie";
DROP TABLE IF EXISTS "main"."dsb_tom_massnahme";
DROP TABLE IF EXISTS "main"."dsb_verarbeitung";
DROP TABLE IF EXISTS "main"."dsb_verarbeitung_datenkategorien";
DROP TABLE IF EXISTS "main"."dsb_vorfall";
DROP TABLE IF EXISTS "main"."dsb_vorfall_typ";
DROP TABLE IF EXISTS "main"."enrichment_responses";
DROP TABLE IF EXISTS "main"."expert_hub_assessments";
DROP TABLE IF EXISTS "main"."expert_hub_assessments_team_members";
DROP TABLE IF EXISTS "main"."expert_hub_auditlog";
DROP TABLE IF EXISTS "main"."expert_hub_building";
DROP TABLE IF EXISTS "main"."expert_hub_data_source_config";
DROP TABLE IF EXISTS "main"."expert_hub_data_source_metric";
DROP TABLE IF EXISTS "main"."expert_hub_document_type";
DROP TABLE IF EXISTS "main"."expert_hub_equipment";
DROP TABLE IF EXISTS "main"."expert_hub_equipment_category";
DROP TABLE IF EXISTS "main"."expert_hub_equipment_gutachten";
DROP TABLE IF EXISTS "main"."expert_hub_explosion_group";
DROP TABLE IF EXISTS "main"."expert_hub_exschutzdocument";
DROP TABLE IF EXISTS "main"."expert_hub_exzone";
DROP TABLE IF EXISTS "main"."expert_hub_facility";
DROP TABLE IF EXISTS "main"."expert_hub_facility_hazmat";
DROP TABLE IF EXISTS "main"."expert_hub_facility_type";
DROP TABLE IF EXISTS "main"."expert_hub_gefahrstoff";
DROP TABLE IF EXISTS "main"."expert_hub_gutachten";
DROP TABLE IF EXISTS "main"."expert_hub_gutachten_betroffene_vorschriften";
DROP TABLE IF EXISTS "main"."expert_hub_hazmat_catalog";
DROP TABLE IF EXISTS "main"."expert_hub_ignition_protection_type";
DROP TABLE IF EXISTS "main"."expert_hub_physical_state";
DROP TABLE IF EXISTS "main"."expert_hub_processing_status_type";
DROP TABLE IF EXISTS "main"."expert_hub_regulation";
DROP TABLE IF EXISTS "main"."expert_hub_regulation_type";
DROP TABLE IF EXISTS "main"."expert_hub_regulation_verwandte_vorschriften";
DROP TABLE IF EXISTS "main"."expert_hub_schutzmassnahme";
DROP TABLE IF EXISTS "main"."expert_hub_substance_data_import";
DROP TABLE IF EXISTS "main"."expert_hub_temperature_class";
DROP TABLE IF EXISTS "main"."expert_hub_zone_type";
DROP TABLE IF EXISTS "main"."field_definitions";
DROP TABLE IF EXISTS "main"."field_groups";
DROP TABLE IF EXISTS "main"."field_templates";
DROP TABLE IF EXISTS "main"."field_value_history";
DROP TABLE IF EXISTS "main"."genagent_actions";
DROP TABLE IF EXISTS "main"."genagent_custom_domains";
DROP TABLE IF EXISTS "main"."genagent_execution_logs";
DROP TABLE IF EXISTS "main"."genagent_phases";
DROP TABLE IF EXISTS "main"."generated_images";
DROP TABLE IF EXISTS "main"."genres";
DROP TABLE IF EXISTS "main"."graphql_field_usage";
DROP TABLE IF EXISTS "main"."graphql_operations";
DROP TABLE IF EXISTS "main"."graphql_performance_logs";
DROP TABLE IF EXISTS "main"."handler_executions";
DROP TABLE IF EXISTS "main"."ideas_v2";
DROP TABLE IF EXISTS "main"."ideas_v2_books";
DROP TABLE IF EXISTS "main"."illustration_styles";
DROP TABLE IF EXISTS "main"."llm_prompt_executions";
DROP TABLE IF EXISTS "main"."llm_prompt_templates";
DROP TABLE IF EXISTS "main"."llms";
DROP TABLE IF EXISTS "main"."locations";
DROP TABLE IF EXISTS "main"."medtrans_customers";
DROP TABLE IF EXISTS "main"."medtrans_presentation_texts";
DROP TABLE IF EXISTS "main"."medtrans_presentations";
DROP TABLE IF EXISTS "main"."navigation_items";
DROP TABLE IF EXISTS "main"."navigation_items_domains";
DROP TABLE IF EXISTS "main"."navigation_items_required_groups";
DROP TABLE IF EXISTS "main"."navigation_items_required_permissions";
DROP TABLE IF EXISTS "main"."navigation_sections";
DROP TABLE IF EXISTS "main"."navigation_sections_domains";
DROP TABLE IF EXISTS "main"."navigation_sections_required_groups";
DROP TABLE IF EXISTS "main"."navigation_sections_required_permissions";
DROP TABLE IF EXISTS "main"."phase_action_configs";
DROP TABLE IF EXISTS "main"."phase_agent_configs";
DROP TABLE IF EXISTS "main"."presentation_studio_design_profile";
DROP TABLE IF EXISTS "main"."presentation_studio_enhancement";
DROP TABLE IF EXISTS "main"."presentation_studio_presentation";
DROP TABLE IF EXISTS "main"."presentation_studio_preview_slide";
DROP TABLE IF EXISTS "main"."presentation_studio_template_collection";
DROP TABLE IF EXISTS "main"."project_field_values";
DROP TABLE IF EXISTS "main"."project_phase_actions";
DROP TABLE IF EXISTS "main"."project_phase_history";
DROP TABLE IF EXISTS "main"."project_type_phases";
DROP TABLE IF EXISTS "main"."project_types";
DROP TABLE IF EXISTS "main"."prompt_executions";
DROP TABLE IF EXISTS "main"."prompt_template_tests";
DROP TABLE IF EXISTS "main"."prompt_templates_legacy";
DROP TABLE IF EXISTS "main"."research_citation_style_lookup";
DROP TABLE IF EXISTS "main"."research_depth_lookup";
DROP TABLE IF EXISTS "main"."research_focus_lookup";
DROP TABLE IF EXISTS "main"."research_handler_type_lookup";
DROP TABLE IF EXISTS "main"."research_researchhandlerexecution";
DROP TABLE IF EXISTS "main"."research_researchproject";
DROP TABLE IF EXISTS "main"."research_researchresult";
DROP TABLE IF EXISTS "main"."research_researchsession";
DROP TABLE IF EXISTS "main"."research_researchsource";
DROP TABLE IF EXISTS "main"."research_source_type_lookup";
DROP TABLE IF EXISTS "main"."research_synthesis_type_lookup";
DROP TABLE IF EXISTS "main"."sqlite_sequence";
DROP TABLE IF EXISTS "main"."story_bibles";
DROP TABLE IF EXISTS "main"."target_audiences";
DROP TABLE IF EXISTS "main"."template_fields";
DROP TABLE IF EXISTS "main"."tool_definitions";
DROP TABLE IF EXISTS "main"."tool_executions";
DROP TABLE IF EXISTS "main"."user_navigation_preferences";
DROP TABLE IF EXISTS "main"."workflow_domains";
DROP TABLE IF EXISTS "main"."workflow_phase_steps";
DROP TABLE IF EXISTS "main"."workflow_phases";
DROP TABLE IF EXISTS "main"."workflow_system_checkpoint";
DROP TABLE IF EXISTS "main"."workflow_system_workflow";
DROP TABLE IF EXISTS "main"."workflow_templates";
DROP TABLE IF EXISTS "main"."workflow_templates_v2";
DROP TABLE IF EXISTS "main"."world_rules";
DROP TABLE IF EXISTS "main"."world_settings";
DROP TABLE IF EXISTS "main"."worlds_v2";
DROP TABLE IF EXISTS "main"."worlds_v2_books";
DROP TABLE IF EXISTS "main"."writing_book_projects";
DROP TABLE IF EXISTS "main"."writing_chapters";
DROP TABLE IF EXISTS "main"."writing_chapters_featured_characters";
DROP TABLE IF EXISTS "main"."writing_chapters_plot_points";
DROP TABLE IF EXISTS "main"."writing_characters";
DROP TABLE IF EXISTS "main"."writing_generation_logs";
DROP TABLE IF EXISTS "main"."writing_plot_points";
DROP TABLE IF EXISTS "main"."writing_plot_points_involved_characters";
DROP TABLE IF EXISTS "main"."writing_statuses";
DROP TABLE IF EXISTS "main"."writing_story_arcs";
DROP TABLE IF EXISTS "main"."writing_story_chapters";
DROP TABLE IF EXISTS "main"."writing_story_memories";
DROP TABLE IF EXISTS "main"."writing_story_memories_characters_involved";
DROP TABLE IF EXISTS "main"."writing_story_projects";
DROP TABLE IF EXISTS "main"."writing_story_strands";
DROP TABLE IF EXISTS "main"."writing_story_strands_converges_with";
DROP TABLE IF EXISTS "main"."writing_story_strands_secondary_characters";
DROP TABLE IF EXISTS "main"."writing_worlds";
DROP INDEX IF EXISTS "main"."action_templates_action_id_5232ed93";
DROP INDEX IF EXISTS "main"."action_templates_action_id_template_id_91d6e7a8_uniq";
DROP INDEX IF EXISTS "main"."action_templates_template_id_7f6ae4ec";
DROP INDEX IF EXISTS "main"."action_time_idx";
DROP INDEX IF EXISTS "main"."agent_actions_agent_id_92fee259";
DROP INDEX IF EXISTS "main"."agent_actions_agent_id_name_c367db78_uniq";
DROP INDEX IF EXISTS "main"."agent_actions_prompt_template_id_aeafc531";
DROP INDEX IF EXISTS "main"."agent_artifacts_agent_id_713e1c14";
DROP INDEX IF EXISTS "main"."agent_artifacts_project_id_7c499dac";
DROP INDEX IF EXISTS "main"."agents_agent_t_e12830_idx";
DROP INDEX IF EXISTS "main"."agents_llm_model_id_ddbf10fa";
DROP INDEX IF EXISTS "main"."ai_verify_idx";
DROP INDEX IF EXISTS "main"."auth_group_permissions_group_id_b120cbf9";
DROP INDEX IF EXISTS "main"."auth_group_permissions_group_id_permission_id_0cd325b0_uniq";
DROP INDEX IF EXISTS "main"."auth_group_permissions_permission_id_84c5c92e";
DROP INDEX IF EXISTS "main"."auth_permission_content_type_id_2f476e4b";
DROP INDEX IF EXISTS "main"."auth_permission_content_type_id_codename_01ab375a_uniq";
DROP INDEX IF EXISTS "main"."auth_user_groups_group_id_97559544";
DROP INDEX IF EXISTS "main"."auth_user_groups_user_id_6a12ed8b";
DROP INDEX IF EXISTS "main"."auth_user_groups_user_id_group_id_94350c0c_uniq";
DROP INDEX IF EXISTS "main"."auth_user_user_permissions_permission_id_1fbb5f2c";
DROP INDEX IF EXISTS "main"."auth_user_user_permissions_user_id_a95ead1b";
DROP INDEX IF EXISTS "main"."auth_user_user_permissions_user_id_permission_id_14a6b632_uniq";
DROP INDEX IF EXISTS "main"."bfagent_bug_require_5a83e6_idx";
DROP INDEX IF EXISTS "main"."bfagent_bug_status_7e5e87_idx";
DROP INDEX IF EXISTS "main"."bfagent_bugfixplan_approved_by_id_5eb56692";
DROP INDEX IF EXISTS "main"."bfagent_bugfixplan_created_by_id_666948dc";
DROP INDEX IF EXISTS "main"."bfagent_bugfixplan_requirement_id_9d513cb7";
DROP INDEX IF EXISTS "main"."bfagent_chapterrating_chapter_id_9391c66d";
DROP INDEX IF EXISTS "main"."bfagent_chapterrating_review_round_id_7116774c";
DROP INDEX IF EXISTS "main"."bfagent_chapterrating_review_round_id_chapter_id_reviewer_id_0de22118_uniq";
DROP INDEX IF EXISTS "main"."bfagent_chapterrating_reviewer_id_4012b6c3";
DROP INDEX IF EXISTS "main"."bfagent_com_compone_8f6335_idx";
DROP INDEX IF EXISTS "main"."bfagent_com_compone_a01c39_idx";
DROP INDEX IF EXISTS "main"."bfagent_com_status_35fe57_idx";
DROP INDEX IF EXISTS "main"."bfagent_com_timesta_35d4b9_idx";
DROP INDEX IF EXISTS "main"."bfagent_com_usage_c_ffd1b9_idx";
DROP INDEX IF EXISTS "main"."bfagent_comment_author_id_4d7eb98f";
DROP INDEX IF EXISTS "main"."bfagent_comment_chapter_id_9cc74b14";
DROP INDEX IF EXISTS "main"."bfagent_comment_resolved_by_id_0638d2e6";
DROP INDEX IF EXISTS "main"."bfagent_comment_review_round_id_98c57f6a";
DROP INDEX IF EXISTS "main"."bfagent_component_change_log_component_id_76666e40";
DROP INDEX IF EXISTS "main"."bfagent_component_change_log_timestamp_6c70da2b";
DROP INDEX IF EXISTS "main"."bfagent_component_registry_component_type_d334347f";
DROP INDEX IF EXISTS "main"."bfagent_component_registry_domain_73f123cc";
DROP INDEX IF EXISTS "main"."bfagent_component_registry_name_f064aae3";
DROP INDEX IF EXISTS "main"."bfagent_component_registry_owner_id_0cc26f3c";
DROP INDEX IF EXISTS "main"."bfagent_component_registry_status_eacd60f9";
DROP INDEX IF EXISTS "main"."bfagent_component_usage_log_component_id_0a4c0e8b";
DROP INDEX IF EXISTS "main"."bfagent_component_usage_log_timestamp_a5b8bd1e";
DROP INDEX IF EXISTS "main"."bfagent_con_created_ba0748_idx";
DROP INDEX IF EXISTS "main"."bfagent_con_schema__f2c90d_idx";
DROP INDEX IF EXISTS "main"."bfagent_contextenrichmentlog_schema_id_d41f79be";
DROP INDEX IF EXISTS "main"."bfagent_contextsource_schema_id_ffe95205";
DROP INDEX IF EXISTS "main"."bfagent_contextsource_schema_id_order_d5a8d79c_uniq";
DROP INDEX IF EXISTS "main"."bfagent_fea_feature_2131f3_idx";
DROP INDEX IF EXISTS "main"."bfagent_fea_is_auto_6d6741_idx";
DROP INDEX IF EXISTS "main"."bfagent_fea_keyword_6e4aca_idx";
DROP INDEX IF EXISTS "main"."bfagent_feature_document_feature_id_764d60e3";
DROP INDEX IF EXISTS "main"."bfagent_feature_document_feature_id_file_path_7a71841b_uniq";
DROP INDEX IF EXISTS "main"."bfagent_feature_document_keyword_feature_id_594884e3";
DROP INDEX IF EXISTS "main"."bfagent_feature_document_keyword_feature_id_keyword_c3d8bea1_uniq";
DROP INDEX IF EXISTS "main"."bfagent_feature_document_keyword_keyword_6b834cab";
DROP INDEX IF EXISTS "main"."bfagent_gen_created_d5bb0b_idx";
DROP INDEX IF EXISTS "main"."bfagent_gen_image_t_c825fc_idx";
DROP INDEX IF EXISTS "main"."bfagent_gen_project_972aef_idx";
DROP INDEX IF EXISTS "main"."bfagent_generatedimage_approved_by_id_7ee6c7ee";
DROP INDEX IF EXISTS "main"."bfagent_generatedimage_chapter_id_6b78bd59";
DROP INDEX IF EXISTS "main"."bfagent_generatedimage_project_id_37a7c95b";
DROP INDEX IF EXISTS "main"."bfagent_generatedimage_style_profile_id_feb24cb7";
DROP INDEX IF EXISTS "main"."bfagent_generatedimage_user_id_aeb29fc0";
DROP INDEX IF EXISTS "main"."bfagent_imagegenerationbatch_project_id_e282e69c";
DROP INDEX IF EXISTS "main"."bfagent_imagegenerationbatch_style_profile_id_4ac75a90";
DROP INDEX IF EXISTS "main"."bfagent_imagegenerationbatch_user_id_e63dfa97";
DROP INDEX IF EXISTS "main"."bfagent_imagestyleprofile_project_id_dc338940";
DROP INDEX IF EXISTS "main"."bfagent_imagestyleprofile_user_id_f04435d1";
DROP INDEX IF EXISTS "main"."bfagent_mig_app_lab_49b9ce_idx";
DROP INDEX IF EXISTS "main"."bfagent_mig_applied_956deb_idx";
DROP INDEX IF EXISTS "main"."bfagent_mig_complex_8efe00_idx";
DROP INDEX IF EXISTS "main"."bfagent_mig_is_appl_7ca748_idx";
DROP INDEX IF EXISTS "main"."bfagent_migration_conflict_migration1_id_2142a34a";
DROP INDEX IF EXISTS "main"."bfagent_migration_conflict_migration2_id_e993255b";
DROP INDEX IF EXISTS "main"."bfagent_migration_registry_app_label_ce9b9a6c";
DROP INDEX IF EXISTS "main"."bfagent_migration_registry_app_label_migration_name_af598197_uniq";
DROP INDEX IF EXISTS "main"."bfagent_migration_registry_is_applied_72526bb4";
DROP INDEX IF EXISTS "main"."bfagent_migration_registry_migration_name_4ae81d60";
DROP INDEX IF EXISTS "main"."bfagent_migration_registry_migration_type_3a450c04";
DROP INDEX IF EXISTS "main"."bfagent_req_require_9e50ce_idx";
DROP INDEX IF EXISTS "main"."bfagent_req_test_ca_f222ed_idx";
DROP INDEX IF EXISTS "main"."bfagent_requirementtestlink_requirement_id_91294358";
DROP INDEX IF EXISTS "main"."bfagent_requirementtestlink_requirement_id_criterion_id_e4146098_uniq";
DROP INDEX IF EXISTS "main"."bfagent_requirementtestlink_test_case_id_3c617cd2";
DROP INDEX IF EXISTS "main"."bfagent_reviewparticipant_review_round_id_3b862ec5";
DROP INDEX IF EXISTS "main"."bfagent_reviewparticipant_review_round_id_user_id_d064e03a_uniq";
DROP INDEX IF EXISTS "main"."bfagent_reviewparticipant_user_id_48721ea4";
DROP INDEX IF EXISTS "main"."bfagent_reviewround_created_by_id_54e3467c";
DROP INDEX IF EXISTS "main"."bfagent_reviewround_project_id_5098a619";
DROP INDEX IF EXISTS "main"."bfagent_tes_categor_266b32_idx";
DROP INDEX IF EXISTS "main"."bfagent_tes_created_6e9b05_idx";
DROP INDEX IF EXISTS "main"."bfagent_tes_execute_0cd84a_idx";
DROP INDEX IF EXISTS "main"."bfagent_tes_framewo_f853f8_idx";
DROP INDEX IF EXISTS "main"."bfagent_tes_status_44c843_idx";
DROP INDEX IF EXISTS "main"."bfagent_tes_status_7807e7_idx";
DROP INDEX IF EXISTS "main"."bfagent_tes_test_ca_b2db02_idx";
DROP INDEX IF EXISTS "main"."bfagent_testbug_screenshot_id_fc659e59";
DROP INDEX IF EXISTS "main"."bfagent_testbug_session_id_b680d0a1";
DROP INDEX IF EXISTS "main"."bfagent_testexecution_executed_by_id_d645a7c4";
DROP INDEX IF EXISTS "main"."bfagent_testexecution_test_case_id_1d833f7d";
DROP INDEX IF EXISTS "main"."bfagent_testlog_session_id_ffe3f6ca";
DROP INDEX IF EXISTS "main"."bfagent_testrequirement_created_by_id_f465efb0";
DROP INDEX IF EXISTS "main"."bfagent_testscreenshot_session_id_4fec3171";
DROP INDEX IF EXISTS "main"."bfagent_testsession_requirement_id_2dcd27e4";
DROP INDEX IF EXISTS "main"."bfagent_testsession_user_id_17e8631d";
DROP INDEX IF EXISTS "main"."book_characters_v2_book_id_97ec892c";
DROP INDEX IF EXISTS "main"."book_characters_v2_book_id_character_id_3e701194_uniq";
DROP INDEX IF EXISTS "main"."book_characters_v2_character_id_e9d909bc";
DROP INDEX IF EXISTS "main"."book_characters_v2_first_appearance_id_9c04870d";
DROP INDEX IF EXISTS "main"."book_status_domain__0f8fb5_idx";
DROP INDEX IF EXISTS "main"."book_status_is_acti_233dc0_idx";
DROP INDEX IF EXISTS "main"."book_status_stage_30682d_idx";
DROP INDEX IF EXISTS "main"."book_statuses_domain_art_id_f3f0546b";
DROP INDEX IF EXISTS "main"."book_statuses_domain_art_id_slug_64e6d7fd_uniq";
DROP INDEX IF EXISTS "main"."book_statuses_slug_e0b10c6e";
DROP INDEX IF EXISTS "main"."book_type_phases_book_type_id_cf37fab9";
DROP INDEX IF EXISTS "main"."book_type_phases_book_type_id_phase_id_b4682d33_uniq";
DROP INDEX IF EXISTS "main"."book_type_phases_phase_id_2f1a2ed5";
DROP INDEX IF EXISTS "main"."cad_analysi_job_id_a0ad90_idx";
DROP INDEX IF EXISTS "main"."cad_analysi_project_4f65b1_idx";
DROP INDEX IF EXISTS "main"."cad_analysi_status_052c75_idx";
DROP INDEX IF EXISTS "main"."cad_analysis_category_is_active_42b216da";
DROP INDEX IF EXISTS "main"."cad_analysis_jobs_created_by_id_e17b3de1";
DROP INDEX IF EXISTS "main"."cad_analysis_jobs_project_id_74472271";
DROP INDEX IF EXISTS "main"."cad_analysis_jobs_status_568ae190";
DROP INDEX IF EXISTS "main"."cad_analysis_reports_job_id_eab9ebaf";
DROP INDEX IF EXISTS "main"."cad_analysis_results_file_id_2fa41d58";
DROP INDEX IF EXISTS "main"."cad_analysis_results_job_id_ccd5ccca";
DROP INDEX IF EXISTS "main"."cad_building_type_is_active_8fce5a66";
DROP INDEX IF EXISTS "main"."cad_compliance_standard_is_active_47005316";
DROP INDEX IF EXISTS "main"."cad_drawing_files_job_id_ecdfd390";
DROP INDEX IF EXISTS "main"."cad_drawing_type_is_active_8b52fadf";
DROP INDEX IF EXISTS "main"."cad_layer_standard_is_active_d090d996";
DROP INDEX IF EXISTS "main"."cad_severity_level_is_active_36075761";
DROP INDEX IF EXISTS "main"."cas_lookup_idx";
DROP INDEX IF EXISTS "main"."chapters_v2_book_id_5cb43cc3";
DROP INDEX IF EXISTS "main"."chapters_v2_book_id_b47840_idx";
DROP INDEX IF EXISTS "main"."chapters_v2_book_id_number_c06be84d_uniq";
DROP INDEX IF EXISTS "main"."chapters_v2_created_1dd366_idx";
DROP INDEX IF EXISTS "main"."chapters_v2_status_0a70e7_idx";
DROP INDEX IF EXISTS "main"."characters__created_05e319_idx";
DROP INDEX IF EXISTS "main"."characters__created_f08312_idx";
DROP INDEX IF EXISTS "main"."characters__role_03662d_idx";
DROP INDEX IF EXISTS "main"."characters_v2_created_by_id_34a113d9";
DROP INDEX IF EXISTS "main"."checklist_i_auto_ch_4db7a9_idx";
DROP INDEX IF EXISTS "main"."checklist_i_checkli_c097cc_idx";
DROP INDEX IF EXISTS "main"."checklist_i_complet_a84e32_idx";
DROP INDEX IF EXISTS "main"."checklist_i_content_a9e618_idx";
DROP INDEX IF EXISTS "main"."checklist_i_is_acti_da83ac_idx";
DROP INDEX IF EXISTS "main"."checklist_i_phase_488c30_idx";
DROP INDEX IF EXISTS "main"."checklist_i_templat_f9e7a6_idx";
DROP INDEX IF EXISTS "main"."checklist_instances_completed_by_id_209f60a7";
DROP INDEX IF EXISTS "main"."checklist_instances_content_type_id_2208073f";
DROP INDEX IF EXISTS "main"."checklist_instances_created_by_id_b1733f0e";
DROP INDEX IF EXISTS "main"."checklist_instances_template_id_bd0dcd36";
DROP INDEX IF EXISTS "main"."checklist_item_statuses_checked_by_id_3c74ae5b";
DROP INDEX IF EXISTS "main"."checklist_item_statuses_checklist_id_9a01ee30";
DROP INDEX IF EXISTS "main"."checklist_item_statuses_checklist_id_item_id_0ff0b1f1_uniq";
DROP INDEX IF EXISTS "main"."checklist_item_statuses_item_id_10712416";
DROP INDEX IF EXISTS "main"."checklist_t_domain__d3c3bf_idx";
DROP INDEX IF EXISTS "main"."checklist_t_is_acti_9ef45f_idx";
DROP INDEX IF EXISTS "main"."comic_dialo_charact_e5e049_idx";
DROP INDEX IF EXISTS "main"."comic_dialo_panel_i_bca7c3_idx";
DROP INDEX IF EXISTS "main"."comic_dialogues_character_id_1f7a1011";
DROP INDEX IF EXISTS "main"."comic_dialogues_panel_id_98d839fb";
DROP INDEX IF EXISTS "main"."comic_panel_chapter_cd7960_idx";
DROP INDEX IF EXISTS "main"."comic_panel_status_b43d6c_idx";
DROP INDEX IF EXISTS "main"."comic_panels_chapter_id_60059a09";
DROP INDEX IF EXISTS "main"."comic_panels_chapter_id_panel_number_ec72208c_uniq";
DROP INDEX IF EXISTS "main"."compliance_audit_log_action_3cfe58bd";
DROP INDEX IF EXISTS "main"."compliance_audit_log_client_id_e1eb89be";
DROP INDEX IF EXISTS "main"."compliance_audit_log_domain_88c71613";
DROP INDEX IF EXISTS "main"."compliance_audit_log_entity_type_id_37d88a9a";
DROP INDEX IF EXISTS "main"."compliance_audit_log_timestamp_2028e0cc";
DROP INDEX IF EXISTS "main"."compliance_audit_log_user_id_bf0e49be";
DROP INDEX IF EXISTS "main"."compliance_idx";
DROP INDEX IF EXISTS "main"."compliance_incident_severity_is_active_f9735b67";
DROP INDEX IF EXISTS "main"."compliance_incident_severity_sort_order_9b02f0ac";
DROP INDEX IF EXISTS "main"."compliance_priority_is_active_601f1cce";
DROP INDEX IF EXISTS "main"."compliance_priority_sort_order_c483f7e7";
DROP INDEX IF EXISTS "main"."compliance_risk_level_is_active_b7daa7df";
DROP INDEX IF EXISTS "main"."compliance_risk_level_sort_order_fa44b2c1";
DROP INDEX IF EXISTS "main"."compliance_status_is_active_3d31fa22";
DROP INDEX IF EXISTS "main"."compliance_status_sort_order_8a4d9901";
DROP INDEX IF EXISTS "main"."compliance_tag_created_by_id_67ef98c7";
DROP INDEX IF EXISTS "main"."compliance_tag_domain_20d1f45a";
DROP INDEX IF EXISTS "main"."compliance_tagged_item_content_type_id_dbae70fc";
DROP INDEX IF EXISTS "main"."compliance_tagged_item_tag_id_80b0db75";
DROP INDEX IF EXISTS "main"."compliance_tagged_item_tag_id_content_type_id_object_id_ff5797fc_uniq";
DROP INDEX IF EXISTS "main"."compliance_tagged_item_tagged_by_id_76dd4ea7";
DROP INDEX IF EXISTS "main"."content_blo_content_cc463d_idx";
DROP INDEX IF EXISTS "main"."content_blo_project_d0b0a9_idx";
DROP INDEX IF EXISTS "main"."content_blo_project_dc335e_idx";
DROP INDEX IF EXISTS "main"."content_blo_status_6e639a_idx";
DROP INDEX IF EXISTS "main"."content_blocks_content_hash_0441ebaf";
DROP INDEX IF EXISTS "main"."content_blocks_content_type_2f3e89f0";
DROP INDEX IF EXISTS "main"."content_blocks_order_2454020c";
DROP INDEX IF EXISTS "main"."content_blocks_parent_id_04b891e1";
DROP INDEX IF EXISTS "main"."content_blocks_project_id_35796ce7";
DROP INDEX IF EXISTS "main"."core_agent__agent_i_e04cb0_idx";
DROP INDEX IF EXISTS "main"."core_agent__status_ba891f_idx";
DROP INDEX IF EXISTS "main"."core_agent_executions_agent_id_a893bf91";
DROP INDEX IF EXISTS "main"."core_agent_executions_executed_at_7bf0d1bc";
DROP INDEX IF EXISTS "main"."core_agent_executions_llm_used_id_b62a8e2c";
DROP INDEX IF EXISTS "main"."core_conten_content_00ea43_idx";
DROP INDEX IF EXISTS "main"."core_conten_content_133927_idx";
DROP INDEX IF EXISTS "main"."core_conten_created_9c47aa_idx";
DROP INDEX IF EXISTS "main"."core_conten_is_ai_g_42278e_idx";
DROP INDEX IF EXISTS "main"."core_conten_parent__85ae34_idx";
DROP INDEX IF EXISTS "main"."core_conten_project_92c5e4_idx";
DROP INDEX IF EXISTS "main"."core_conten_project_a96bb8_idx";
DROP INDEX IF EXISTS "main"."core_conten_related_ab07d1_idx";
DROP INDEX IF EXISTS "main"."core_conten_status_bb7f62_idx";
DROP INDEX IF EXISTS "main"."core_contentitem_assigned_to_id_7e1d3f84";
DROP INDEX IF EXISTS "main"."core_contentitem_category_02f38d76";
DROP INDEX IF EXISTS "main"."core_contentitem_completion_percentage_66f74499";
DROP INDEX IF EXISTS "main"."core_contentitem_content_type_7584e81d";
DROP INDEX IF EXISTS "main"."core_contentitem_created_at_67792e15";
DROP INDEX IF EXISTS "main"."core_contentitem_created_by_id_2a5aee81";
DROP INDEX IF EXISTS "main"."core_contentitem_external_id_33ee7da1";
DROP INDEX IF EXISTS "main"."core_contentitem_is_ai_generated_23628622";
DROP INDEX IF EXISTS "main"."core_contentitem_parent_item_id_ce5a4a34";
DROP INDEX IF EXISTS "main"."core_contentitem_primary_tag_e744345d";
DROP INDEX IF EXISTS "main"."core_contentitem_priority_5c448824";
DROP INDEX IF EXISTS "main"."core_contentitem_project_id_5a4a3111";
DROP INDEX IF EXISTS "main"."core_contentitem_related_character_id_102e67de";
DROP INDEX IF EXISTS "main"."core_contentitem_sequence_number_d3e753d2";
DROP INDEX IF EXISTS "main"."core_contentitem_status_ce38514e";
DROP INDEX IF EXISTS "main"."core_contentitem_visual_style_309e5bc7";
DROP INDEX IF EXISTS "main"."core_contentitem_word_count_e02b92ba";
DROP INDEX IF EXISTS "main"."core_customers_is_active_f2fba9b8";
DROP INDEX IF EXISTS "main"."core_customers_name_de984037";
DROP INDEX IF EXISTS "main"."core_locations_customer_id_ea89ed14";
DROP INDEX IF EXISTS "main"."core_locations_customer_id_location_code_03f3c6d5_uniq";
DROP INDEX IF EXISTS "main"."core_locations_is_active_eaaa87ce";
DROP INDEX IF EXISTS "main"."core_locations_name_d9d4d0c2";
DROP INDEX IF EXISTS "main"."core_plugin_configurations_custom_template_id_1948f0a5";
DROP INDEX IF EXISTS "main"."core_plugin_configurations_plugin_id_c52a26a9";
DROP INDEX IF EXISTS "main"."core_plugin_configurations_plugin_id_user_id_project_id_1443e6da_uniq";
DROP INDEX IF EXISTS "main"."core_plugin_configurations_project_id_9669b761";
DROP INDEX IF EXISTS "main"."core_plugin_configurations_user_id_316d29f6";
DROP INDEX IF EXISTS "main"."core_plugin_domain_c246e3_idx";
DROP INDEX IF EXISTS "main"."core_plugin_execute_eef837_idx";
DROP INDEX IF EXISTS "main"."core_plugin_executions_executed_at_bfff5139";
DROP INDEX IF EXISTS "main"."core_plugin_executions_executed_by_id_8508cf71";
DROP INDEX IF EXISTS "main"."core_plugin_executions_plugin_id_045d022d";
DROP INDEX IF EXISTS "main"."core_plugin_last_ex_137c0f_idx";
DROP INDEX IF EXISTS "main"."core_plugin_plugin__f5ac89_idx";
DROP INDEX IF EXISTS "main"."core_plugin_plugin__fcbb53_idx";
DROP INDEX IF EXISTS "main"."core_plugin_registry_ab_test_group_97f586d1";
DROP INDEX IF EXISTS "main"."core_plugin_registry_author_id_6b41fc6b";
DROP INDEX IF EXISTS "main"."core_plugin_registry_category_08e3f849";
DROP INDEX IF EXISTS "main"."core_plugin_registry_default_template_id_a34186ee";
DROP INDEX IF EXISTS "main"."core_plugin_registry_depends_on_from_pluginregistry_id_5b2cd1ac";
DROP INDEX IF EXISTS "main"."core_plugin_registry_depends_on_from_pluginregistry_id_to_pluginregistry_id_737ee385_uniq";
DROP INDEX IF EXISTS "main"."core_plugin_registry_depends_on_to_pluginregistry_id_d2afa833";
DROP INDEX IF EXISTS "main"."core_plugin_registry_domain_037c30b0";
DROP INDEX IF EXISTS "main"."core_plugin_registry_is_active_aa69f1ab";
DROP INDEX IF EXISTS "main"."core_plugin_registry_maintainer_id_812d9a8a";
DROP INDEX IF EXISTS "main"."core_plugin_status_616ed7_idx";
DROP INDEX IF EXISTS "main"."core_plugin_user_ra_71955e_idx";
DROP INDEX IF EXISTS "main"."core_prompt_agent_i_bde561_idx";
DROP INDEX IF EXISTS "main"."core_prompt_categor_2a40b3_idx";
DROP INDEX IF EXISTS "main"."core_prompt_executions_agent_id_1b290184";
DROP INDEX IF EXISTS "main"."core_prompt_executions_executed_at_99577ffd";
DROP INDEX IF EXISTS "main"."core_prompt_executions_executed_by_id_7cbfc0db";
DROP INDEX IF EXISTS "main"."core_prompt_executions_llm_id_f71c3f78";
DROP INDEX IF EXISTS "main"."core_prompt_executions_template_id_a9d45e07";
DROP INDEX IF EXISTS "main"."core_prompt_last_us_7faf90_idx";
DROP INDEX IF EXISTS "main"."core_prompt_status_b7ccf8_idx";
DROP INDEX IF EXISTS "main"."core_prompt_templat_42dd09_idx";
DROP INDEX IF EXISTS "main"."core_prompt_templat_c78b99_idx";
DROP INDEX IF EXISTS "main"."core_prompt_templates_ab_test_group_b861a6cc";
DROP INDEX IF EXISTS "main"."core_prompt_templates_category_1720fe0e";
DROP INDEX IF EXISTS "main"."core_prompt_templates_created_by_id_5d8d885b";
DROP INDEX IF EXISTS "main"."core_prompt_templates_domain_d2a10251";
DROP INDEX IF EXISTS "main"."core_prompt_templates_fallback_template_id_2d5f4fad";
DROP INDEX IF EXISTS "main"."core_prompt_templates_is_active_ec588021";
DROP INDEX IF EXISTS "main"."core_prompt_templates_parent_template_id_0420dd0e";
DROP INDEX IF EXISTS "main"."core_prompt_templates_preferred_llm_id_22225e16";
DROP INDEX IF EXISTS "main"."core_prompt_versions_changed_by_id_c738ec31";
DROP INDEX IF EXISTS "main"."core_prompt_versions_template_id_582116b2";
DROP INDEX IF EXISTS "main"."core_prompt_versions_template_id_version_number_1037d7f2_uniq";
DROP INDEX IF EXISTS "main"."customer_project_idx";
DROP INDEX IF EXISTS "main"."customer_upload_idx";
DROP INDEX IF EXISTS "main"."django_admin_log_content_type_id_c4bce8eb";
DROP INDEX IF EXISTS "main"."django_admin_log_user_id_c564eba6";
DROP INDEX IF EXISTS "main"."django_content_type_app_label_model_76bd3d3b_uniq";
DROP INDEX IF EXISTS "main"."django_session_expire_date_a5c62663";
DROP INDEX IF EXISTS "main"."doc_cas_idx";
DROP INDEX IF EXISTS "main"."doc_massnahme_idx";
DROP INDEX IF EXISTS "main"."doc_time_idx";
DROP INDEX IF EXISTS "main"."doc_type_idx";
DROP INDEX IF EXISTS "main"."doc_zone_idx";
DROP INDEX IF EXISTS "main"."domain_phases_domain_type_id_4ba48196";
DROP INDEX IF EXISTS "main"."domain_phases_domain_type_id_workflow_phase_id_885bcc7b_uniq";
DROP INDEX IF EXISTS "main"."domain_phases_workflow_phase_id_a351bfb2";
DROP INDEX IF EXISTS "main"."domain_proj_created_4e933f_idx";
DROP INDEX IF EXISTS "main"."domain_proj_created_9ef853_idx";
DROP INDEX IF EXISTS "main"."domain_proj_domain__da9d2a_idx";
DROP INDEX IF EXISTS "main"."domain_projects_created_by_id_4767a8ce";
DROP INDEX IF EXISTS "main"."domain_projects_current_phase_id_57dff64f";
DROP INDEX IF EXISTS "main"."domain_projects_domain_type_id_320969fb";
DROP INDEX IF EXISTS "main"."domain_projects_status_bbc4f82c";
DROP INDEX IF EXISTS "main"."domain_section_items_section_id_93d92f01";
DROP INDEX IF EXISTS "main"."domain_section_items_section_id_slug_b82a6176_uniq";
DROP INDEX IF EXISTS "main"."domain_section_items_slug_6f76b04c";
DROP INDEX IF EXISTS "main"."domain_sections_domain_art_id_bfd07226";
DROP INDEX IF EXISTS "main"."domain_sections_domain_art_id_slug_5dfcd28e_uniq";
DROP INDEX IF EXISTS "main"."domain_sections_slug_a013b2db";
DROP INDEX IF EXISTS "main"."dsb_branche_is_active_4e3ebe50";
DROP INDEX IF EXISTS "main"."dsb_branche_sort_order_99c54497";
DROP INDEX IF EXISTS "main"."dsb_datenkategorie_is_active_27cc4bb8";
DROP INDEX IF EXISTS "main"."dsb_datenkategorie_sensitivity_id_32a19970";
DROP INDEX IF EXISTS "main"."dsb_datenkategorie_sort_order_a779f300";
DROP INDEX IF EXISTS "main"."dsb_dokument_approved_by_id_8aef8e7c";
DROP INDEX IF EXISTS "main"."dsb_dokument_client_content_type_id_92c361d0";
DROP INDEX IF EXISTS "main"."dsb_dokument_created_at_c54e6b38";
DROP INDEX IF EXISTS "main"."dsb_dokument_created_by_id_67e4a905";
DROP INDEX IF EXISTS "main"."dsb_dokument_deleted_by_id_79844db2";
DROP INDEX IF EXISTS "main"."dsb_dokument_document_type_861beaa3";
DROP INDEX IF EXISTS "main"."dsb_dokument_is_active_5b23c396";
DROP INDEX IF EXISTS "main"."dsb_dokument_mandant_id_b4b37f04";
DROP INDEX IF EXISTS "main"."dsb_dokument_review_date_c7a71472";
DROP INDEX IF EXISTS "main"."dsb_dokument_status_bcf745f9";
DROP INDEX IF EXISTS "main"."dsb_dokument_valid_until_847e23fb";
DROP INDEX IF EXISTS "main"."dsb_dokument_verarbeitung_id_eedb46d3";
DROP INDEX IF EXISTS "main"."dsb_mandant_betreuer_id_21672275";
DROP INDEX IF EXISTS "main"."dsb_mandant_branche_id_6af36828";
DROP INDEX IF EXISTS "main"."dsb_mandant_client_content_type_id_cac4ea14";
DROP INDEX IF EXISTS "main"."dsb_mandant_created_at_b4f208c1";
DROP INDEX IF EXISTS "main"."dsb_mandant_created_by_id_a0ae7ec3";
DROP INDEX IF EXISTS "main"."dsb_mandant_deleted_by_id_3898fabf";
DROP INDEX IF EXISTS "main"."dsb_mandant_external_id_ee644e08";
DROP INDEX IF EXISTS "main"."dsb_mandant_is_active_d3efdbe9";
DROP INDEX IF EXISTS "main"."dsb_mandant_name_99fd9c4c";
DROP INDEX IF EXISTS "main"."dsb_mandant_rechtsform_id_226ba08a";
DROP INDEX IF EXISTS "main"."dsb_mandant_risk_level_id_61247216";
DROP INDEX IF EXISTS "main"."dsb_mandant_tom_mandant_id_0190488b";
DROP INDEX IF EXISTS "main"."dsb_mandant_tom_mandant_id_massnahme_id_bea1c372_uniq";
DROP INDEX IF EXISTS "main"."dsb_mandant_tom_massnahme_id_4c3b94ef";
DROP INDEX IF EXISTS "main"."dsb_rechtsform_is_active_d612c0e9";
DROP INDEX IF EXISTS "main"."dsb_rechtsform_sort_order_301dddad";
DROP INDEX IF EXISTS "main"."dsb_rechtsgrundlage_is_active_1cad443b";
DROP INDEX IF EXISTS "main"."dsb_rechtsgrundlage_sort_order_617568b9";
DROP INDEX IF EXISTS "main"."dsb_tom_kategorie_is_active_31700232";
DROP INDEX IF EXISTS "main"."dsb_tom_kategorie_sort_order_18b48a96";
DROP INDEX IF EXISTS "main"."dsb_tom_massnahme_is_active_971171ce";
DROP INDEX IF EXISTS "main"."dsb_tom_massnahme_kategorie_id_fde20bf2";
DROP INDEX IF EXISTS "main"."dsb_tom_massnahme_sort_order_9281709c";
DROP INDEX IF EXISTS "main"."dsb_verarbeitung_client_content_type_id_19785dbd";
DROP INDEX IF EXISTS "main"."dsb_verarbeitung_created_at_6045d466";
DROP INDEX IF EXISTS "main"."dsb_verarbeitung_created_by_id_29b2d4c2";
DROP INDEX IF EXISTS "main"."dsb_verarbeitung_datenkategorien_datenkategorie_id_1c99a371";
DROP INDEX IF EXISTS "main"."dsb_verarbeitung_datenkategorien_verarbeitung_id_80fe1b07";
DROP INDEX IF EXISTS "main"."dsb_verarbeitung_datenkategorien_verarbeitung_id_datenkategorie_id_cfe6634b_uniq";
DROP INDEX IF EXISTS "main"."dsb_verarbeitung_deleted_by_id_29349144";
DROP INDEX IF EXISTS "main"."dsb_verarbeitung_is_active_297aed1a";
DROP INDEX IF EXISTS "main"."dsb_verarbeitung_mandant_id_08a3dea6";
DROP INDEX IF EXISTS "main"."dsb_verarbeitung_next_review_641a4d4a";
DROP INDEX IF EXISTS "main"."dsb_verarbeitung_priority_id_d3f6246a";
DROP INDEX IF EXISTS "main"."dsb_verarbeitung_rechtsgrundlage_id_c4c241a2";
DROP INDEX IF EXISTS "main"."dsb_verarbeitung_status_id_15c05c50";
DROP INDEX IF EXISTS "main"."dsb_vorfall_client_content_type_id_ddf7f5f3";
DROP INDEX IF EXISTS "main"."dsb_vorfall_created_at_61d723c9";
DROP INDEX IF EXISTS "main"."dsb_vorfall_created_by_id_0e50d377";
DROP INDEX IF EXISTS "main"."dsb_vorfall_deleted_by_id_723317fd";
DROP INDEX IF EXISTS "main"."dsb_vorfall_incident_datetime_20d87758";
DROP INDEX IF EXISTS "main"."dsb_vorfall_incident_type_0e9a4102";
DROP INDEX IF EXISTS "main"."dsb_vorfall_is_active_8e777f1c";
DROP INDEX IF EXISTS "main"."dsb_vorfall_mandant_id_f8408c34";
DROP INDEX IF EXISTS "main"."dsb_vorfall_severity_id_39061044";
DROP INDEX IF EXISTS "main"."dsb_vorfall_status_a473e5ee";
DROP INDEX IF EXISTS "main"."dsb_vorfall_typ_default_severity_id_6618e820";
DROP INDEX IF EXISTS "main"."dsb_vorfall_typ_is_active_573cafe5";
DROP INDEX IF EXISTS "main"."dsb_vorfall_typ_sort_order_967718cf";
DROP INDEX IF EXISTS "main"."dsb_vorfall_verarbeitung_id_8ee4b12e";
DROP INDEX IF EXISTS "main"."dsb_vorfall_vorfall_typ_id_07bd0196";
DROP INDEX IF EXISTS "main"."enrichment__agent_i_440d3b_idx";
DROP INDEX IF EXISTS "main"."enrichment__project_bea755_idx";
DROP INDEX IF EXISTS "main"."enrichment__target__34a36f_idx";
DROP INDEX IF EXISTS "main"."enrichment_responses_action_id_aa655d05";
DROP INDEX IF EXISTS "main"."enrichment_responses_agent_id_98c1e0d0";
DROP INDEX IF EXISTS "main"."enrichment_responses_applied_by_id_63f65243";
DROP INDEX IF EXISTS "main"."enrichment_responses_llm_used_id_6875c89d";
DROP INDEX IF EXISTS "main"."enrichment_responses_project_id_193cbf1f";
DROP INDEX IF EXISTS "main"."enrichment_responses_target_field_id_9e5f19ed";
DROP INDEX IF EXISTS "main"."entity_idx";
DROP INDEX IF EXISTS "main"."expert_hub__assessm_7afb14_idx";
DROP INDEX IF EXISTS "main"."expert_hub__assessm_7d7358_idx";
DROP INDEX IF EXISTS "main"."expert_hub__ausgabe_68bc40_idx";
DROP INDEX IF EXISTS "main"."expert_hub__bezeich_6abfa0_idx";
DROP INDEX IF EXISTS "main"."expert_hub__created_b4cdd3_idx";
DROP INDEX IF EXISTS "main"."expert_hub__created_b7b6f4_idx";
DROP INDEX IF EXISTS "main"."expert_hub__current_15fc22_idx";
DROP INDEX IF EXISTS "main"."expert_hub__custome_f8359e_idx";
DROP INDEX IF EXISTS "main"."expert_hub__erstell_221019_idx";
DROP INDEX IF EXISTS "main"."expert_hub__geraete_4a0306_idx";
DROP INDEX IF EXISTS "main"."expert_hub__gutacht_061747_idx";
DROP INDEX IF EXISTS "main"."expert_hub__herstel_e03b0f_idx";
DROP INDEX IF EXISTS "main"."expert_hub__regulat_3bdd6a_idx";
DROP INDEX IF EXISTS "main"."expert_hub__status_3a3e35_idx";
DROP INDEX IF EXISTS "main"."expert_hub__status_53c2a7_idx";
DROP INDEX IF EXISTS "main"."expert_hub__status_5d2680_idx";
DROP INDEX IF EXISTS "main"."expert_hub__vollsta_e9180a_idx";
DROP INDEX IF EXISTS "main"."expert_hub_assessments_created_by_id_b56e1274";
DROP INDEX IF EXISTS "main"."expert_hub_assessments_customer_id_c94207e1";
DROP INDEX IF EXISTS "main"."expert_hub_assessments_domain_art_id_8cf566d5";
DROP INDEX IF EXISTS "main"."expert_hub_assessments_domain_type_id_feeba2ec";
DROP INDEX IF EXISTS "main"."expert_hub_assessments_lead_assessor_id_ab9c4534";
DROP INDEX IF EXISTS "main"."expert_hub_assessments_location_id_38407ff3";
DROP INDEX IF EXISTS "main"."expert_hub_assessments_team_members_assessment_id_61b1df9d";
DROP INDEX IF EXISTS "main"."expert_hub_assessments_team_members_assessment_id_user_id_4a6365dc_uniq";
DROP INDEX IF EXISTS "main"."expert_hub_assessments_team_members_user_id_b8e64836";
DROP INDEX IF EXISTS "main"."expert_hub_auditlog_action_98eaab45";
DROP INDEX IF EXISTS "main"."expert_hub_auditlog_compliance_relevant_c0b9d4d2";
DROP INDEX IF EXISTS "main"."expert_hub_auditlog_document_id_b5a5420c";
DROP INDEX IF EXISTS "main"."expert_hub_auditlog_entity_id_a8bf75c1";
DROP INDEX IF EXISTS "main"."expert_hub_auditlog_entity_type_789469ab";
DROP INDEX IF EXISTS "main"."expert_hub_auditlog_human_verified_84a81112";
DROP INDEX IF EXISTS "main"."expert_hub_auditlog_is_ai_generated_c64e0a56";
DROP INDEX IF EXISTS "main"."expert_hub_auditlog_session_id_43fd3f5e";
DROP INDEX IF EXISTS "main"."expert_hub_auditlog_timestamp_bbf5f67f";
DROP INDEX IF EXISTS "main"."expert_hub_auditlog_user_id_208175e4";
DROP INDEX IF EXISTS "main"."expert_hub_auditlog_verified_by_id_dc3952aa";
DROP INDEX IF EXISTS "main"."expert_hub_auditlog_workflow_id_180d1d49";
DROP INDEX IF EXISTS "main"."expert_hub_building_location_id_2162a456";
DROP INDEX IF EXISTS "main"."expert_hub_building_name_0e2122a1";
DROP INDEX IF EXISTS "main"."expert_hub_data_source_metric_source_ts_idx";
DROP INDEX IF EXISTS "main"."expert_hub_data_source_metric_success_ts_idx";
DROP INDEX IF EXISTS "main"."expert_hub_data_source_metric_timestamp_idx";
DROP INDEX IF EXISTS "main"."expert_hub_equipment_bezeichnung_cd44673f";
DROP INDEX IF EXISTS "main"."expert_hub_equipment_created_by_id_7bab3bb0";
DROP INDEX IF EXISTS "main"."expert_hub_equipment_ersetzt_durch_id_ca4b91ed";
DROP INDEX IF EXISTS "main"."expert_hub_equipment_explosionsgruppe_id_a8bebf61";
DROP INDEX IF EXISTS "main"."expert_hub_equipment_facility_id_2ba567c2";
DROP INDEX IF EXISTS "main"."expert_hub_equipment_geraetekategorie_id_fab3937d";
DROP INDEX IF EXISTS "main"."expert_hub_equipment_gutachten_equipment_id_023119d9";
DROP INDEX IF EXISTS "main"."expert_hub_equipment_gutachten_equipment_id_explosionsschutzgutachten_id_481a2b73_uniq";
DROP INDEX IF EXISTS "main"."expert_hub_equipment_gutachten_explosionsschutzgutachten_id_d1593095";
DROP INDEX IF EXISTS "main"."expert_hub_equipment_status_d8eaa8b6";
DROP INDEX IF EXISTS "main"."expert_hub_equipment_temperaturklasse_id_51636a0f";
DROP INDEX IF EXISTS "main"."expert_hub_equipment_wartungsverantwortlicher_id_840b081f";
DROP INDEX IF EXISTS "main"."expert_hub_equipment_zuendschutzart_id_7b855a5a";
DROP INDEX IF EXISTS "main"."expert_hub_exschutzdocument_customer_id_d92b6d36";
DROP INDEX IF EXISTS "main"."expert_hub_exschutzdocument_document_type_id_98b5a2ba";
DROP INDEX IF EXISTS "main"."expert_hub_exschutzdocument_needs_human_review_b1c55ace";
DROP INDEX IF EXISTS "main"."expert_hub_exschutzdocument_processing_status_id_0e8f527e";
DROP INDEX IF EXISTS "main"."expert_hub_exschutzdocument_project_id_adcaf76b";
DROP INDEX IF EXISTS "main"."expert_hub_exschutzdocument_reviewed_by_id_12d3921f";
DROP INDEX IF EXISTS "main"."expert_hub_exschutzdocument_uploaded_at_d2fcae47";
DROP INDEX IF EXISTS "main"."expert_hub_exschutzdocument_uploaded_by_id_35224d4d";
DROP INDEX IF EXISTS "main"."expert_hub_exschutzdocument_workflow_id_eca87eec";
DROP INDEX IF EXISTS "main"."expert_hub_exzone_document_id_82fb43d4";
DROP INDEX IF EXISTS "main"."expert_hub_exzone_gebaeude_id_262121d6";
DROP INDEX IF EXISTS "main"."expert_hub_exzone_hauptgefahrstoff_id_a9f2e9ca";
DROP INDEX IF EXISTS "main"."expert_hub_exzone_needs_review_470cd10d";
DROP INDEX IF EXISTS "main"."expert_hub_exzone_reviewed_by_id_811ac23e";
DROP INDEX IF EXISTS "main"."expert_hub_exzone_zone_classification_id_b37ed125";
DROP INDEX IF EXISTS "main"."expert_hub_facility_facility_type_id_29e5f157";
DROP INDEX IF EXISTS "main"."expert_hub_facility_hazmat_facility_id_ffc0f30f";
DROP INDEX IF EXISTS "main"."expert_hub_facility_hazmat_facility_id_hazmat_id_1e5bed33_uniq";
DROP INDEX IF EXISTS "main"."expert_hub_facility_hazmat_hazmat_id_f082cf7d";
DROP INDEX IF EXISTS "main"."expert_hub_facility_location_id_74786af6";
DROP INDEX IF EXISTS "main"."expert_hub_facility_name_eeb54412";
DROP INDEX IF EXISTS "main"."expert_hub_facility_status_93883d01";
DROP INDEX IF EXISTS "main"."expert_hub_gefahrstoff_cas_number_08d29718";
DROP INDEX IF EXISTS "main"."expert_hub_gefahrstoff_document_id_5a9cc2d7";
DROP INDEX IF EXISTS "main"."expert_hub_gefahrstoff_extracted_by_id_edb754cc";
DROP INDEX IF EXISTS "main"."expert_hub_gefahrstoff_needs_review_cece50d9";
DROP INDEX IF EXISTS "main"."expert_hub_gefahrstoff_reviewed_by_id_1ed16c10";
DROP INDEX IF EXISTS "main"."expert_hub_gutachten_betroffene_vorschriften_explosionsschutzgutachten_id_eb416294";
DROP INDEX IF EXISTS "main"."expert_hub_gutachten_betroffene_vorschriften_explosionsschutzgutachten_id_regulation_id_c9ad6092_uniq";
DROP INDEX IF EXISTS "main"."expert_hub_gutachten_betroffene_vorschriften_regulation_id_b6f4775d";
DROP INDEX IF EXISTS "main"."expert_hub_gutachten_ersteller_id_0131b35e";
DROP INDEX IF EXISTS "main"."expert_hub_gutachten_freigegeben_von_id_06ecfae5";
DROP INDEX IF EXISTS "main"."expert_hub_gutachten_geprueft_von_id_7ed129e4";
DROP INDEX IF EXISTS "main"."expert_hub_gutachten_status_b2780fab";
DROP INDEX IF EXISTS "main"."expert_hub_hazmat_catalog_name_eb74cc48";
DROP INDEX IF EXISTS "main"."expert_hub_regulation_created_by_id_4ffdb183";
DROP INDEX IF EXISTS "main"."expert_hub_regulation_ersetzt_durch_id_79b3b0dd";
DROP INDEX IF EXISTS "main"."expert_hub_regulation_nummer_a5eaeb89";
DROP INDEX IF EXISTS "main"."expert_hub_regulation_regulation_type_id_8074c1ae";
DROP INDEX IF EXISTS "main"."expert_hub_regulation_regulation_type_id_nummer_adc26fe3_uniq";
DROP INDEX IF EXISTS "main"."expert_hub_regulation_relevanz_explosionsschutz_25c0f9be";
DROP INDEX IF EXISTS "main"."expert_hub_regulation_status_ae80098b";
DROP INDEX IF EXISTS "main"."expert_hub_regulation_verwandte_vorschriften_from_regulation_id_ddafcea6";
DROP INDEX IF EXISTS "main"."expert_hub_regulation_verwandte_vorschriften_from_regulation_id_to_regulation_id_e771b06f_uniq";
DROP INDEX IF EXISTS "main"."expert_hub_regulation_verwandte_vorschriften_to_regulation_id_27372fef";
DROP INDEX IF EXISTS "main"."expert_hub_schutzmassnahme_document_id_bdd5d795";
DROP INDEX IF EXISTS "main"."expert_hub_schutzmassnahme_massnahme_typ_32cce024";
DROP INDEX IF EXISTS "main"."expert_hub_schutzmassnahme_needs_review_a06cc37b";
DROP INDEX IF EXISTS "main"."expert_hub_schutzmassnahme_reviewed_by_id_488a70dc";
DROP INDEX IF EXISTS "main"."expert_hub_substance_data_import_cas_imported_idx";
DROP INDEX IF EXISTS "main"."expert_hub_substance_data_import_imported_by_id_idx";
DROP INDEX IF EXISTS "main"."expert_hub_substance_data_import_source_imported_idx";
DROP INDEX IF EXISTS "main"."expert_hub_substance_data_import_success_imported_idx";
DROP INDEX IF EXISTS "main"."field_defin_name_528028_idx";
DROP INDEX IF EXISTS "main"."field_defin_target__c1bdaf_idx";
DROP INDEX IF EXISTS "main"."field_definitions_created_by_id_ed223f8e";
DROP INDEX IF EXISTS "main"."field_definitions_group_id_67233ebf";
DROP INDEX IF EXISTS "main"."field_value_history_changed_by_id_15240210";
DROP INDEX IF EXISTS "main"."field_value_history_field_value_id_4ecda553";
DROP INDEX IF EXISTS "main"."genagent_ac_phase_i_3cd7fa_idx";
DROP INDEX IF EXISTS "main"."genagent_actions_phase_id_4c30ca17";
DROP INDEX IF EXISTS "main"."genagent_cu_categor_3e096b_idx";
DROP INDEX IF EXISTS "main"."genagent_cu_domain__462cf8_idx";
DROP INDEX IF EXISTS "main"."genagent_ex_action__cef494_idx";
DROP INDEX IF EXISTS "main"."genagent_ex_status_4af2ac_idx";
DROP INDEX IF EXISTS "main"."genagent_execution_logs_action_id_41432599";
DROP INDEX IF EXISTS "main"."genagent_ph_order_675106_idx";
DROP INDEX IF EXISTS "main"."generated_i_book_id_74e297_idx";
DROP INDEX IF EXISTS "main"."generated_i_is_acti_c80911_idx";
DROP INDEX IF EXISTS "main"."generated_i_provide_4d6cdc_idx";
DROP INDEX IF EXISTS "main"."generated_images_book_id_8e009312";
DROP INDEX IF EXISTS "main"."generated_images_created_at_e4d6a029";
DROP INDEX IF EXISTS "main"."generated_images_created_by_id_ac051c44";
DROP INDEX IF EXISTS "main"."generated_images_handler_id_c2cbb2da";
DROP INDEX IF EXISTS "main"."generated_images_is_active_6239b8df";
DROP INDEX IF EXISTS "main"."generated_images_provider_2d055b23";
DROP INDEX IF EXISTS "main"."genres_domain__98a665_idx";
DROP INDEX IF EXISTS "main"."genres_domain_art_id_98404dd8";
DROP INDEX IF EXISTS "main"."genres_domain_art_id_slug_c11cbcb9_uniq";
DROP INDEX IF EXISTS "main"."genres_is_acti_9bdcd0_idx";
DROP INDEX IF EXISTS "main"."genres_parent_genre_id_c40038e7";
DROP INDEX IF EXISTS "main"."genres_slug_99e229b7";
DROP INDEX IF EXISTS "main"."graphql_fie_last_us_1a8041_idx";
DROP INDEX IF EXISTS "main"."graphql_fie_usage_c_ead89c_idx";
DROP INDEX IF EXISTS "main"."graphql_field_usage_field_name_c901d6b1";
DROP INDEX IF EXISTS "main"."graphql_field_usage_type_name_e412aa32";
DROP INDEX IF EXISTS "main"."graphql_field_usage_type_name_field_name_2ed69de4_uniq";
DROP INDEX IF EXISTS "main"."graphql_ope_avg_dur_d62c40_idx";
DROP INDEX IF EXISTS "main"."graphql_ope_executi_d5bfab_idx";
DROP INDEX IF EXISTS "main"."graphql_ope_last_us_4f399b_idx";
DROP INDEX IF EXISTS "main"."graphql_operations_operation_hash_07bddc10";
DROP INDEX IF EXISTS "main"."graphql_operations_operation_name_0363a2b1";
DROP INDEX IF EXISTS "main"."graphql_per_operati_c976df_idx";
DROP INDEX IF EXISTS "main"."graphql_per_timesta_9aff51_idx";
DROP INDEX IF EXISTS "main"."graphql_performance_logs_operation_id_fcdce2b8";
DROP INDEX IF EXISTS "main"."graphql_performance_logs_timestamp_1aa0cf3f";
DROP INDEX IF EXISTS "main"."handler_exe_action__158ac2_idx";
DROP INDEX IF EXISTS "main"."handler_exe_project_1a4635_idx";
DROP INDEX IF EXISTS "main"."handler_exe_status_f900f7_idx";
DROP INDEX IF EXISTS "main"."handler_executions_action_handler_id_c4d7a3c4";
DROP INDEX IF EXISTS "main"."handler_executions_executed_by_id_e53d2d83";
DROP INDEX IF EXISTS "main"."handler_executions_llm_used_id_841f77fa";
DROP INDEX IF EXISTS "main"."handler_executions_project_id_feb13bb4";
DROP INDEX IF EXISTS "main"."handler_executions_status_e37b694a";
DROP INDEX IF EXISTS "main"."ideas_v2_books_bookproject_id_5cd060f7";
DROP INDEX IF EXISTS "main"."ideas_v2_books_idea_id_299630a6";
DROP INDEX IF EXISTS "main"."ideas_v2_books_idea_id_bookproject_id_36f6c98f_uniq";
DROP INDEX IF EXISTS "main"."ideas_v2_created_by_id_f4b9d4a7";
DROP INDEX IF EXISTS "main"."ideas_v2_created_df2406_idx";
DROP INDEX IF EXISTS "main"."ideas_v2_status_9bd965_idx";
DROP INDEX IF EXISTS "main"."idx_building_location";
DROP INDEX IF EXISTS "main"."idx_customer_active";
DROP INDEX IF EXISTS "main"."idx_customer_name";
DROP INDEX IF EXISTS "main"."idx_customer_num";
DROP INDEX IF EXISTS "main"."idx_fachaz_facility";
DROP INDEX IF EXISTS "main"."idx_fachaz_hazmat";
DROP INDEX IF EXISTS "main"."idx_facility_inv";
DROP INDEX IF EXISTS "main"."idx_facility_location";
DROP INDEX IF EXISTS "main"."idx_facility_status";
DROP INDEX IF EXISTS "main"."idx_facility_type";
DROP INDEX IF EXISTS "main"."idx_hazcat_cas";
DROP INDEX IF EXISTS "main"."idx_hazcat_exgroup";
DROP INDEX IF EXISTS "main"."idx_hazcat_name";
DROP INDEX IF EXISTS "main"."idx_location_active";
DROP INDEX IF EXISTS "main"."idx_location_code";
DROP INDEX IF EXISTS "main"."idx_location_customer";
DROP INDEX IF EXISTS "main"."llm_prompt__categor_999cba_idx";
DROP INDEX IF EXISTS "main"."llm_prompt__llm_id_bed547_idx";
DROP INDEX IF EXISTS "main"."llm_prompt__prompt__31843c_idx";
DROP INDEX IF EXISTS "main"."llm_prompt__prompt__e79d19_idx";
DROP INDEX IF EXISTS "main"."llm_prompt__status_9d979d_idx";
DROP INDEX IF EXISTS "main"."llm_prompt__total_u_f53b70_idx";
DROP INDEX IF EXISTS "main"."llm_prompt_executions_executed_by_id_d754f13b";
DROP INDEX IF EXISTS "main"."llm_prompt_executions_llm_id_985d4b80";
DROP INDEX IF EXISTS "main"."llm_prompt_executions_prompt_id_64515e91";
DROP INDEX IF EXISTS "main"."llm_prompt_executions_status_432b76da";
DROP INDEX IF EXISTS "main"."llm_prompt_templates_category_fa4b6d5a";
DROP INDEX IF EXISTS "main"."llm_prompt_templates_created_by_id_31b8c07a";
DROP INDEX IF EXISTS "main"."llm_prompt_templates_is_active_b83d15ce";
DROP INDEX IF EXISTS "main"."llm_prompt_templates_prompt_id_variant_c09cbb20_uniq";
DROP INDEX IF EXISTS "main"."llm_prompt_templates_replacement_prompt_id_5db53cda";
DROP INDEX IF EXISTS "main"."locations_parent_location_id_7bb36098";
DROP INDEX IF EXISTS "main"."locations_world_id_aac1a8b1";
DROP INDEX IF EXISTS "main"."massnahme_review_idx";
DROP INDEX IF EXISTS "main"."massnahme_status_idx";
DROP INDEX IF EXISTS "main"."medtrans_customers_user_id_f69f5cc7";
DROP INDEX IF EXISTS "main"."medtrans_pr_present_296fd2_idx";
DROP INDEX IF EXISTS "main"."medtrans_pr_present_a431bb_idx";
DROP INDEX IF EXISTS "main"."medtrans_presentation_texts_presentation_id_2a748594";
DROP INDEX IF EXISTS "main"."medtrans_presentation_texts_presentation_id_text_id_d4e92044_uniq";
DROP INDEX IF EXISTS "main"."medtrans_presentations_customer_id_38cc8243";
DROP INDEX IF EXISTS "main"."navigation_items_code_idx";
DROP INDEX IF EXISTS "main"."navigation_items_domains_navigationitem_id_67e6620d";
DROP INDEX IF EXISTS "main"."navigation_items_domains_navigationitem_id_workflowdomain_id_8221f67a_uniq";
DROP INDEX IF EXISTS "main"."navigation_items_domains_workflowdomain_id_11d91214";
DROP INDEX IF EXISTS "main"."navigation_items_is_active_idx";
DROP INDEX IF EXISTS "main"."navigation_items_order_idx";
DROP INDEX IF EXISTS "main"."navigation_items_parent_id_idx";
DROP INDEX IF EXISTS "main"."navigation_items_required_groups_group_id_f3038baf";
DROP INDEX IF EXISTS "main"."navigation_items_required_groups_navigationitem_id_eebc8734";
DROP INDEX IF EXISTS "main"."navigation_items_required_groups_navigationitem_id_group_id_f65f8040_uniq";
DROP INDEX IF EXISTS "main"."navigation_items_required_permissions_navigationitem_id_14edd041";
DROP INDEX IF EXISTS "main"."navigation_items_required_permissions_navigationitem_id_permission_id_0d85ee79_uniq";
DROP INDEX IF EXISTS "main"."navigation_items_required_permissions_permission_id_2cd3a360";
DROP INDEX IF EXISTS "main"."navigation_items_section_code_unique";
DROP INDEX IF EXISTS "main"."navigation_items_section_id_idx";
DROP INDEX IF EXISTS "main"."navigation_sections_code_idx";
DROP INDEX IF EXISTS "main"."navigation_sections_code_unique";
DROP INDEX IF EXISTS "main"."navigation_sections_domains_navigationsection_id_aaeb4da8";
DROP INDEX IF EXISTS "main"."navigation_sections_domains_navigationsection_id_workflowdomain_id_cd5e94ad_uniq";
DROP INDEX IF EXISTS "main"."navigation_sections_domains_workflowdomain_id_4f38b02e";
DROP INDEX IF EXISTS "main"."navigation_sections_is_active_idx";
DROP INDEX IF EXISTS "main"."navigation_sections_order_idx";
DROP INDEX IF EXISTS "main"."navigation_sections_required_groups_group_id_41f0e8ef";
DROP INDEX IF EXISTS "main"."navigation_sections_required_groups_navigationsection_id_7d0523fa";
DROP INDEX IF EXISTS "main"."navigation_sections_required_groups_navigationsection_id_group_id_4da414ac_uniq";
DROP INDEX IF EXISTS "main"."navigation_sections_required_permissions_navigationsection_id_e239da60";
DROP INDEX IF EXISTS "main"."navigation_sections_required_permissions_navigationsection_id_permission_id_af6d89f0_uniq";
DROP INDEX IF EXISTS "main"."navigation_sections_required_permissions_permission_id_8e6265c7";
DROP INDEX IF EXISTS "main"."phase_action_configs_action_id_6247e482";
DROP INDEX IF EXISTS "main"."phase_action_configs_phase_id_4adc200d";
DROP INDEX IF EXISTS "main"."phase_action_configs_phase_id_action_id_fa2ac745_uniq";
DROP INDEX IF EXISTS "main"."phase_agent_configs_agent_id_8804d447";
DROP INDEX IF EXISTS "main"."phase_agent_configs_phase_id_agent_id_4f60953b_uniq";
DROP INDEX IF EXISTS "main"."phase_agent_configs_phase_id_f6956e67";
DROP INDEX IF EXISTS "main"."presentatio_client_664c13_idx";
DROP INDEX IF EXISTS "main"."presentatio_enhance_13c0c5_idx";
DROP INDEX IF EXISTS "main"."presentatio_enhance_a77e6d_idx";
DROP INDEX IF EXISTS "main"."presentatio_industr_0f6158_idx";
DROP INDEX IF EXISTS "main"."presentatio_is_acti_9d00ca_idx";
DROP INDEX IF EXISTS "main"."presentatio_is_syst_b7bbe3_idx";
DROP INDEX IF EXISTS "main"."presentatio_present_3bcbb2_idx";
DROP INDEX IF EXISTS "main"."presentatio_present_7120c8_idx";
DROP INDEX IF EXISTS "main"."presentatio_present_c4d4a6_idx";
DROP INDEX IF EXISTS "main"."presentatio_source__1b715e_idx";
DROP INDEX IF EXISTS "main"."presentatio_uploade_b0dc07_idx";
DROP INDEX IF EXISTS "main"."presentation_studio_design_profile_created_by_id_6469b538";
DROP INDEX IF EXISTS "main"."presentation_studio_design_profile_presentation_id_f9de8cba";
DROP INDEX IF EXISTS "main"."presentation_studio_enhancement_executed_by_id_094cd913";
DROP INDEX IF EXISTS "main"."presentation_studio_enhancement_presentation_id_201a590d";
DROP INDEX IF EXISTS "main"."presentation_studio_presentation_enhancement_status_c94a1987";
DROP INDEX IF EXISTS "main"."presentation_studio_presentation_template_collection_id_97f51c8f";
DROP INDEX IF EXISTS "main"."presentation_studio_presentation_uploaded_by_id_6ce48f70";
DROP INDEX IF EXISTS "main"."presentation_studio_preview_slide_presentation_id_fe893b87";
DROP INDEX IF EXISTS "main"."presentation_studio_preview_slide_status_175d3e9d";
DROP INDEX IF EXISTS "main"."presentation_studio_template_collection_created_by_id_7ed92b6a";
DROP INDEX IF EXISTS "main"."project_fie_project_78279a_idx";
DROP INDEX IF EXISTS "main"."project_field_values_field_definition_id_b7c4f52e";
DROP INDEX IF EXISTS "main"."project_field_values_project_id_42a790c7";
DROP INDEX IF EXISTS "main"."project_field_values_project_id_field_definition_id_2d712908_uniq";
DROP INDEX IF EXISTS "main"."project_field_values_updated_by_id_903ad678";
DROP INDEX IF EXISTS "main"."project_pha_project_77f25d_idx";
DROP INDEX IF EXISTS "main"."project_pha_projekt_1c8daf_idx";
DROP INDEX IF EXISTS "main"."project_pha_projekt_4dd39a_idx";
DROP INDEX IF EXISTS "main"."project_pha_projekt_8bbc0e_idx";
DROP INDEX IF EXISTS "main"."project_phase_actions_action_id_481262c0";
DROP INDEX IF EXISTS "main"."project_phase_actions_projektart_projekttyp_projektphase_id_action_id_d47e3008_uniq";
DROP INDEX IF EXISTS "main"."project_phase_actions_projektphase_id_e0edfbc5";
DROP INDEX IF EXISTS "main"."project_phase_history_phase_id_7953db92";
DROP INDEX IF EXISTS "main"."project_phase_history_project_id_01240a3b";
DROP INDEX IF EXISTS "main"."project_phase_history_workflow_step_id_b3c5401e";
DROP INDEX IF EXISTS "main"."project_typ_projekt_67fbbb_idx";
DROP INDEX IF EXISTS "main"."project_typ_projekt_84d59b_idx";
DROP INDEX IF EXISTS "main"."project_type_phases_projektart_projekttyp_projektphase_id_ca77a6ac_uniq";
DROP INDEX IF EXISTS "main"."project_type_phases_projektphase_id_a3bfd24f";
DROP INDEX IF EXISTS "main"."prompt_exec_project_4ebcb8_idx";
DROP INDEX IF EXISTS "main"."prompt_exec_status_26fa8b_idx";
DROP INDEX IF EXISTS "main"."prompt_exec_templat_7cc92b_idx";
DROP INDEX IF EXISTS "main"."prompt_exec_user_ac_f23b6c_idx";
DROP INDEX IF EXISTS "main"."prompt_executions_agent_id_464f6ba5";
DROP INDEX IF EXISTS "main"."prompt_executions_project_id_9a703b09";
DROP INDEX IF EXISTS "main"."prompt_executions_retry_of_id_fa02fb51";
DROP INDEX IF EXISTS "main"."prompt_executions_template_id_17f29cb0";
DROP INDEX IF EXISTS "main"."prompt_template_tests_template_id_42dd7b08";
DROP INDEX IF EXISTS "main"."prompt_templates_legacy_agent_id_343034d5";
DROP INDEX IF EXISTS "main"."prompt_templates_legacy_agent_id_name_version_a4cf09ca_uniq";
DROP INDEX IF EXISTS "main"."research_citation_style_lookup_is_active_be91e631";
DROP INDEX IF EXISTS "main"."research_depth_lookup_is_active_33af42f5";
DROP INDEX IF EXISTS "main"."research_focus_lookup_is_active_9880e694";
DROP INDEX IF EXISTS "main"."research_handler_type_lookup_is_active_92530619";
DROP INDEX IF EXISTS "main"."research_re_session_4ec110_idx";
DROP INDEX IF EXISTS "main"."research_re_session_fa08d4_idx";
DROP INDEX IF EXISTS "main"."research_re_started_ffead9_idx";
DROP INDEX IF EXISTS "main"."research_re_url_5bc658_idx";
DROP INDEX IF EXISTS "main"."research_researchhandlerexecution_handler_type_id_e7faf3cc";
DROP INDEX IF EXISTS "main"."research_researchhandlerexecution_session_id_1bce2cd0";
DROP INDEX IF EXISTS "main"."research_researchproject_default_depth_id_9ae03c54";
DROP INDEX IF EXISTS "main"."research_researchproject_owner_id_f4887f9d";
DROP INDEX IF EXISTS "main"."research_researchproject_status_d64d66cf";
DROP INDEX IF EXISTS "main"."research_researchresult_citation_style_id_59dace46";
DROP INDEX IF EXISTS "main"."research_researchresult_synthesis_type_id_87d314a4";
DROP INDEX IF EXISTS "main"."research_researchsession_depth_id_00bba639";
DROP INDEX IF EXISTS "main"."research_researchsession_project_id_bbbb2fd0";
DROP INDEX IF EXISTS "main"."research_researchsession_status_d3544030";
DROP INDEX IF EXISTS "main"."research_researchsource_session_id_6d48d1b2";
DROP INDEX IF EXISTS "main"."research_researchsource_source_type_id_618c3b7f";
DROP INDEX IF EXISTS "main"."research_source_type_lookup_is_active_53907271";
DROP INDEX IF EXISTS "main"."research_synthesis_type_lookup_is_active_5585e770";
DROP INDEX IF EXISTS "main"."review_status_idx";
DROP INDEX IF EXISTS "main"."status_review_idx";
DROP INDEX IF EXISTS "main"."story_bibles_created_by_id_3732dc25";
DROP INDEX IF EXISTS "main"."story_bibles_domain_project_id_3f5493a3";
DROP INDEX IF EXISTS "main"."template_fields_field_id_988731fc";
DROP INDEX IF EXISTS "main"."template_fields_template_id_3d289b9c";
DROP INDEX IF EXISTS "main"."template_fields_template_id_field_id_16d6f84c_uniq";
DROP INDEX IF EXISTS "main"."tool_defini_categor_a4f6d2_idx";
DROP INDEX IF EXISTS "main"."tool_defini_tool_id_3896f0_idx";
DROP INDEX IF EXISTS "main"."tool_defini_total_e_4abadf_idx";
DROP INDEX IF EXISTS "main"."tool_definitions_category_b7473024";
DROP INDEX IF EXISTS "main"."tool_definitions_created_by_id_84b47f69";
DROP INDEX IF EXISTS "main"."tool_definitions_status_65b1ec01";
DROP INDEX IF EXISTS "main"."tool_execut_status_0c276d_idx";
DROP INDEX IF EXISTS "main"."tool_execut_tool_id_c05db9_idx";
DROP INDEX IF EXISTS "main"."tool_executions_executed_by_id_1b3775c1";
DROP INDEX IF EXISTS "main"."tool_executions_status_0ec892b0";
DROP INDEX IF EXISTS "main"."tool_executions_tool_id_9eddbc90";
DROP INDEX IF EXISTS "main"."user_navigation_preferences_section_id_98e971ec";
DROP INDEX IF EXISTS "main"."user_navigation_preferences_user_id_b3914478";
DROP INDEX IF EXISTS "main"."user_navigation_preferences_user_id_section_id_5a78f2de_uniq";
DROP INDEX IF EXISTS "main"."user_time_idx";
DROP INDEX IF EXISTS "main"."user_upload_idx";
DROP INDEX IF EXISTS "main"."workflow_domains_created_by_id_f9d587ca";
DROP INDEX IF EXISTS "main"."workflow_phase_steps_phase_id_8b05ba32";
DROP INDEX IF EXISTS "main"."workflow_phase_steps_template_id_afe27baa";
DROP INDEX IF EXISTS "main"."workflow_phase_steps_template_id_order_bce620b4_uniq";
DROP INDEX IF EXISTS "main"."workflow_phase_steps_template_id_phase_id_d4ba7233_uniq";
DROP INDEX IF EXISTS "main"."workflow_sy_created_02a38d_idx";
DROP INDEX IF EXISTS "main"."workflow_sy_created_1bd21b_idx";
DROP INDEX IF EXISTS "main"."workflow_sy_domain__5fc6b5_idx";
DROP INDEX IF EXISTS "main"."workflow_sy_workflo_115dd2_idx";
DROP INDEX IF EXISTS "main"."workflow_sy_workflo_25e7f4_idx";
DROP INDEX IF EXISTS "main"."workflow_system_checkpoint_status_053ed5b0";
DROP INDEX IF EXISTS "main"."workflow_system_checkpoint_workflow_id_8bd40e4e";
DROP INDEX IF EXISTS "main"."workflow_system_workflow_created_at_aeac618d";
DROP INDEX IF EXISTS "main"."workflow_system_workflow_created_by_id_b91f8cd3";
DROP INDEX IF EXISTS "main"."workflow_system_workflow_domain_id_76a56154";
DROP INDEX IF EXISTS "main"."workflow_system_workflow_status_c2bb0ea2";
DROP INDEX IF EXISTS "main"."workflow_system_workflow_template_id_b298ae65";
DROP INDEX IF EXISTS "main"."workflow_templates_book_type_id_c7d24d47";
DROP INDEX IF EXISTS "main"."workflow_templates_book_type_id_name_f27e69cb_uniq";
DROP INDEX IF EXISTS "main"."workflow_templates_v2_created_by_id_37692696";
DROP INDEX IF EXISTS "main"."workflow_templates_v2_project_type_id_4662ed81";
DROP INDEX IF EXISTS "main"."world_rules_world_id_c3eb0556";
DROP INDEX IF EXISTS "main"."worlds_v2_books_bookproject_id_35bd5206";
DROP INDEX IF EXISTS "main"."worlds_v2_books_world_id_535d00d4";
DROP INDEX IF EXISTS "main"."worlds_v2_books_world_id_bookproject_id_8bd00f10_uniq";
DROP INDEX IF EXISTS "main"."worlds_v2_created_by_id_d68c4631";
DROP INDEX IF EXISTS "main"."writing_boo_created_8ebbad_idx";
DROP INDEX IF EXISTS "main"."writing_boo_genre_i_02e7e0_idx";
DROP INDEX IF EXISTS "main"."writing_boo_owner_i_3fb748_idx";
DROP INDEX IF EXISTS "main"."writing_book_projects_book_type_id_bce2a22e";
DROP INDEX IF EXISTS "main"."writing_book_projects_current_phase_step_id_a43dd065";
DROP INDEX IF EXISTS "main"."writing_book_projects_current_workflow_phase_id_5ebdb555";
DROP INDEX IF EXISTS "main"."writing_book_projects_genre_id_4c75531a";
DROP INDEX IF EXISTS "main"."writing_book_projects_owner_id_f39ba12a";
DROP INDEX IF EXISTS "main"."writing_book_projects_status_id_34d6e47e";
DROP INDEX IF EXISTS "main"."writing_book_projects_user_id_19750375";
DROP INDEX IF EXISTS "main"."writing_book_projects_workflow_template_id_5fbe0570";
DROP INDEX IF EXISTS "main"."writing_cha_content_52a4da_idx";
DROP INDEX IF EXISTS "main"."writing_cha_project_bb160a_idx";
DROP INDEX IF EXISTS "main"."writing_cha_writing_5f2e22_idx";
DROP INDEX IF EXISTS "main"."writing_chapters_content_hash_d2e8319e";
DROP INDEX IF EXISTS "main"."writing_chapters_featured_characters_bookchapters_id_70d33d90";
DROP INDEX IF EXISTS "main"."writing_chapters_featured_characters_bookchapters_id_characters_id_d153b1ae_uniq";
DROP INDEX IF EXISTS "main"."writing_chapters_featured_characters_characters_id_de4cc650";
DROP INDEX IF EXISTS "main"."writing_chapters_plot_points_bookchapters_id_e713eb4b";
DROP INDEX IF EXISTS "main"."writing_chapters_plot_points_bookchapters_id_plotpoint_id_91472809_uniq";
DROP INDEX IF EXISTS "main"."writing_chapters_plot_points_plotpoint_id_d3f2f2cc";
DROP INDEX IF EXISTS "main"."writing_chapters_project_id_58043465";
DROP INDEX IF EXISTS "main"."writing_chapters_project_id_chapter_number_1d4fef32_uniq";
DROP INDEX IF EXISTS "main"."writing_chapters_story_arc_id_044c9bbf";
DROP INDEX IF EXISTS "main"."writing_characters_project_id_18c2ef87";
DROP INDEX IF EXISTS "main"."writing_gen_status_b1b9c1_idx";
DROP INDEX IF EXISTS "main"."writing_gen_story_c_bcf05c_idx";
DROP INDEX IF EXISTS "main"."writing_generation_logs_llm_id_af1276ee";
DROP INDEX IF EXISTS "main"."writing_generation_logs_status_b8063f22";
DROP INDEX IF EXISTS "main"."writing_generation_logs_story_chapter_id_a0782d83";
DROP INDEX IF EXISTS "main"."writing_plot_points_involved_characters_characters_id_0f1174a8";
DROP INDEX IF EXISTS "main"."writing_plot_points_involved_characters_plotpoint_id_9748ab16";
DROP INDEX IF EXISTS "main"."writing_plot_points_involved_characters_plotpoint_id_characters_id_cbc211b6_uniq";
DROP INDEX IF EXISTS "main"."writing_plot_points_project_id_b5d23131";
DROP INDEX IF EXISTS "main"."writing_plot_points_story_arc_id_chapter_number_sequence_order_9ec2197b_uniq";
DROP INDEX IF EXISTS "main"."writing_plot_points_story_arc_id_e7155a3e";
DROP INDEX IF EXISTS "main"."writing_sto_chapter_eed7c1_idx";
DROP INDEX IF EXISTS "main"."writing_sto_importa_1ff0da_idx";
DROP INDEX IF EXISTS "main"."writing_sto_slug_ad6118_idx";
DROP INDEX IF EXISTS "main"."writing_sto_status_68a9e0_idx";
DROP INDEX IF EXISTS "main"."writing_sto_story_p_529781_idx";
DROP INDEX IF EXISTS "main"."writing_sto_story_p_89bf9f_idx";
DROP INDEX IF EXISTS "main"."writing_sto_story_p_ff6e88_idx";
DROP INDEX IF EXISTS "main"."writing_sto_strand__4d6362_idx";
DROP INDEX IF EXISTS "main"."writing_story_arcs_project_id_90b8ae7f";
DROP INDEX IF EXISTS "main"."writing_story_arcs_project_id_name_5ca7a658_uniq";
DROP INDEX IF EXISTS "main"."writing_story_chapters_status_f3d50630";
DROP INDEX IF EXISTS "main"."writing_story_chapters_story_project_id_64868d65";
DROP INDEX IF EXISTS "main"."writing_story_chapters_story_project_id_volume_number_chapter_number_af40bb35_uniq";
DROP INDEX IF EXISTS "main"."writing_story_chapters_strand_id_ac74e011";
DROP INDEX IF EXISTS "main"."writing_story_memories_chapter_id_20f06b55";
DROP INDEX IF EXISTS "main"."writing_story_memories_characters_involved_characters_id_5929de99";
DROP INDEX IF EXISTS "main"."writing_story_memories_characters_involved_storymemory_id_a07881cc";
DROP INDEX IF EXISTS "main"."writing_story_memories_characters_involved_storymemory_id_characters_id_6a90b3a0_uniq";
DROP INDEX IF EXISTS "main"."writing_story_memories_memory_type_eeda48e1";
DROP INDEX IF EXISTS "main"."writing_story_memories_revealed_in_chapter_id_d6f69506";
DROP INDEX IF EXISTS "main"."writing_story_memories_story_project_id_78153f1b";
DROP INDEX IF EXISTS "main"."writing_story_memories_strand_id_591439b7";
DROP INDEX IF EXISTS "main"."writing_story_projects_created_by_id_10fce650";
DROP INDEX IF EXISTS "main"."writing_story_projects_llm_model_id_01b921db";
DROP INDEX IF EXISTS "main"."writing_story_projects_status_a9a7b1c5";
DROP INDEX IF EXISTS "main"."writing_story_projects_story_bible_id_74ffe186";
DROP INDEX IF EXISTS "main"."writing_story_strands_converges_with_from_storystrand_id_5fc04ee2";
DROP INDEX IF EXISTS "main"."writing_story_strands_converges_with_from_storystrand_id_to_storystrand_id_d874771b_uniq";
DROP INDEX IF EXISTS "main"."writing_story_strands_converges_with_to_storystrand_id_972630b2";
DROP INDEX IF EXISTS "main"."writing_story_strands_primary_character_id_bff94ba5";
DROP INDEX IF EXISTS "main"."writing_story_strands_secondary_characters_characters_id_b9c6bb54";
DROP INDEX IF EXISTS "main"."writing_story_strands_secondary_characters_storystrand_id_9328053f";
DROP INDEX IF EXISTS "main"."writing_story_strands_secondary_characters_storystrand_id_characters_id_f14e00f2_uniq";
DROP INDEX IF EXISTS "main"."writing_story_strands_story_project_id_b0053152";
DROP INDEX IF EXISTS "main"."writing_story_strands_story_project_id_code_b14613ad_uniq";
DROP INDEX IF EXISTS "main"."writing_worlds_project_id_8af8963a";
DROP INDEX IF EXISTS "main"."zone_review_idx";
CREATE TABLE "action_templates" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_default" bool NOT NULL, "order" integer NOT NULL, "effectiveness_score" real NULL, "usage_count" integer NOT NULL, "description_override" text NOT NULL, "pipeline_config" text NULL CHECK ((JSON_VALID("pipeline_config") OR "pipeline_config" IS NULL)), "action_id" bigint NOT NULL REFERENCES "agent_actions" ("id") DEFERRABLE INITIALLY DEFERRED, "template_id" bigint NOT NULL REFERENCES "prompt_templates_legacy" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "agent_actions" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(100) NOT NULL, "display_name" varchar(200) NOT NULL, "description" text NOT NULL, "target_model" varchar(50) NOT NULL, "target_fields" text NOT NULL CHECK ((JSON_VALID("target_fields") OR "target_fields" IS NULL)), "order" integer NOT NULL, "is_active" bool NOT NULL, "usage_count" integer NOT NULL, "avg_execution_time" real NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "agent_id" bigint NOT NULL REFERENCES "agents" ("id") DEFERRABLE INITIALLY DEFERRED, "prompt_template_id" bigint NULL REFERENCES "prompt_templates_legacy" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "agent_artifacts" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "action" varchar(100) NOT NULL, "content_type" varchar(20) NOT NULL, "content" text NOT NULL, "metadata" text NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "version" integer unsigned NOT NULL CHECK ("version" >= 0), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "agent_id" bigint NULL REFERENCES "agents" ("id") DEFERRABLE INITIALLY DEFERRED, "project_id" bigint NOT NULL REFERENCES "writing_book_projects" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "agent_types" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(100) NOT NULL UNIQUE, "display_name" varchar(200) NOT NULL, "description" text NULL, "icon" varchar(50) NULL, "color" varchar(50) NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);
CREATE TABLE "agents" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(200) NOT NULL, "agent_type" varchar(100) NOT NULL, "description" text NOT NULL, "system_prompt" text NOT NULL, "instructions" text NOT NULL, "creativity_level" decimal NOT NULL, "consistency_weight" decimal NOT NULL, "total_requests" integer NOT NULL, "successful_requests" integer NOT NULL, "average_response_time" decimal NOT NULL, "status" varchar(50) NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "llm_model_id" bigint NULL REFERENCES "llms" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "auth_group" (
  "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
  "name" varchar(150) NOT NULL,
  UNIQUE ("name" ASC)
);UPDATE "main"."sqlite_sequence" SET seq = 3 WHERE name = 'auth_group';
CREATE TABLE "auth_group_permissions" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "group_id" integer NOT NULL REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED, "permission_id" integer NOT NULL REFERENCES "auth_permission" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "auth_permission" (
  "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
  "content_type_id" integer NOT NULL,
  "codename" varchar(100) NOT NULL,
  "name" varchar(255) NOT NULL,
  FOREIGN KEY ("content_type_id") REFERENCES "django_content_type" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE INITIALLY DEFERRED
);UPDATE "main"."sqlite_sequence" SET seq = 1448 WHERE name = 'auth_permission';
CREATE TABLE "auth_user" (
  "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
  "password" varchar(128) NOT NULL,
  "last_login" datetime,
  "is_superuser" bool NOT NULL,
  "username" varchar(150) NOT NULL,
  "last_name" varchar(150) NOT NULL,
  "email" varchar(254) NOT NULL,
  "is_staff" bool NOT NULL,
  "is_active" bool NOT NULL,
  "date_joined" datetime NOT NULL,
  "first_name" varchar(150) NOT NULL,
  UNIQUE ("username" ASC)
);UPDATE "main"."sqlite_sequence" SET seq = 6 WHERE name = 'auth_user';
CREATE TABLE "auth_user_groups" (
  "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
  "user_id" integer NOT NULL,
  "group_id" integer NOT NULL,
  FOREIGN KEY ("user_id") REFERENCES "auth_user" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("group_id") REFERENCES "auth_group" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE INITIALLY DEFERRED
);UPDATE "main"."sqlite_sequence" SET seq = 4 WHERE name = 'auth_user_groups';
CREATE TABLE "auth_user_user_permissions" (
  "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
  "user_id" integer NOT NULL,
  "permission_id" integer NOT NULL,
  FOREIGN KEY ("user_id") REFERENCES "auth_user" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("permission_id") REFERENCES "auth_permission" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE INITIALLY DEFERRED
);UPDATE "main"."sqlite_sequence" SET seq = 452 WHERE name = 'auth_user_user_permissions';
CREATE TABLE "authtoken_token" ("key" varchar(40) NOT NULL PRIMARY KEY, "created" datetime NOT NULL, "user_id" integer NOT NULL UNIQUE REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_bugfixplan" ("id" char(32) NOT NULL PRIMARY KEY, "fix_type" varchar(100) NOT NULL, "fix_description" text NOT NULL, "fix_actions" text NOT NULL CHECK ((JSON_VALID("fix_actions") OR "fix_actions" IS NULL)), "handler_id" varchar(200) NOT NULL, "handler_code" text NOT NULL, "status" varchar(20) NOT NULL, "execution_result" text NOT NULL CHECK ((JSON_VALID("execution_result") OR "execution_result" IS NULL)), "execution_log" text NOT NULL, "rollback_possible" bool NOT NULL, "rollback_data" text NOT NULL CHECK ((JSON_VALID("rollback_data") OR "rollback_data" IS NULL)), "created_at" datetime NOT NULL, "approved_at" datetime NULL, "executed_at" datetime NULL, "approved_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "requirement_id" char(32) NOT NULL REFERENCES "bfagent_testrequirement" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_chapterrating" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "overall_rating" integer NOT NULL, "feedback_text" text NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "chapter_id" bigint NOT NULL REFERENCES "writing_chapters" ("id") DEFERRABLE INITIALLY DEFERRED, "reviewer_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "review_round_id" bigint NOT NULL REFERENCES "bfagent_reviewround" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_comment" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "text" text NOT NULL, "comment_type" varchar(20) NOT NULL, "status" varchar(20) NOT NULL, "author_reply" text NOT NULL, "replied_at" datetime NULL, "resolved_at" datetime NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "is_edited" bool NOT NULL, "helpful_count" integer NOT NULL, "author_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "chapter_id" bigint NOT NULL REFERENCES "writing_chapters" ("id") DEFERRABLE INITIALLY DEFERRED, "resolved_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "review_round_id" bigint NOT NULL REFERENCES "bfagent_reviewround" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_component_change_log" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "timestamp" datetime NOT NULL, "change_type" varchar(50) NOT NULL, "changes" text NOT NULL CHECK ((JSON_VALID("changes") OR "changes" IS NULL)), "reason" text NOT NULL, "component_id" bigint NOT NULL REFERENCES "bfagent_component_registry" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_component_registry" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "identifier" varchar(300) NOT NULL UNIQUE, "name" varchar(200) NOT NULL, "component_type" varchar(50) NOT NULL, "module_path" varchar(500) NOT NULL, "file_path" varchar(500) NOT NULL, "class_name" varchar(200) NOT NULL, "function_name" varchar(200) NOT NULL, "domain" varchar(100) NOT NULL, "category" varchar(100) NOT NULL, "description" text NOT NULL, "docstring" text NOT NULL, "usage_examples" text NOT NULL CHECK ((JSON_VALID("usage_examples") OR "usage_examples" IS NULL)), "tags" text NOT NULL CHECK ((JSON_VALID("tags") OR "tags" IS NULL)), "metadata" text NOT NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "depends_on" text NOT NULL CHECK ((JSON_VALID("depends_on") OR "depends_on" IS NULL)), "required_by" text NOT NULL CHECK ((JSON_VALID("required_by") OR "required_by" IS NULL)), "status" varchar(20) NOT NULL, "version" varchar(50) NOT NULL, "deprecated_reason" text NOT NULL, "replacement_identifier" varchar(300) NOT NULL, "usage_count" integer NOT NULL, "success_count" integer NOT NULL, "failure_count" integer NOT NULL, "avg_execution_time_ms" integer NOT NULL, "last_used_at" datetime NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "discovered_at" datetime NOT NULL, "priority" varchar(20) NOT NULL, "proposed_at" datetime NULL, "planned_at" datetime NULL, "started_at" datetime NULL, "completed_at" datetime NULL, "owner_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_component_usage_log" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "timestamp" datetime NOT NULL, "success" bool NOT NULL, "execution_time_ms" integer NOT NULL, "context" text NOT NULL CHECK ((JSON_VALID("context") OR "context" IS NULL)), "error_message" text NOT NULL, "component_id" bigint NOT NULL REFERENCES "bfagent_component_registry" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_contextenrichmentlog" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "handler_name" varchar(100) NOT NULL, "params" text NOT NULL CHECK ((JSON_VALID("params") OR "params" IS NULL)), "enriched_context" text NOT NULL CHECK ((JSON_VALID("enriched_context") OR "enriched_context" IS NULL)), "execution_time_ms" real NOT NULL, "success" bool NOT NULL, "error_message" text NOT NULL, "created_at" datetime NOT NULL, "schema_id" bigint NOT NULL REFERENCES "bfagent_contextschema" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_contextschema" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(100) NOT NULL UNIQUE, "display_name" varchar(200) NOT NULL, "description" text NOT NULL, "handler_type" varchar(100) NOT NULL, "is_active" bool NOT NULL, "is_system" bool NOT NULL, "version" varchar(20) NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);
CREATE TABLE "bfagent_contextsource" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(100) NOT NULL, "source_type" varchar(20) NOT NULL, "order" integer NOT NULL, "model_name" varchar(100) NOT NULL, "filter_config" text NOT NULL CHECK ((JSON_VALID("filter_config") OR "filter_config" IS NULL)), "fields" text NOT NULL CHECK ((JSON_VALID("fields") OR "fields" IS NULL)), "field_mappings" text NOT NULL CHECK ((JSON_VALID("field_mappings") OR "field_mappings" IS NULL)), "aggregate_type" varchar(20) NOT NULL, "context_key" varchar(100) NOT NULL, "function_name" varchar(100) NOT NULL, "function_params" text NOT NULL CHECK ((JSON_VALID("function_params") OR "function_params" IS NULL)), "order_by" varchar(100) NOT NULL, "default_value" text NULL CHECK ((JSON_VALID("default_value") OR "default_value" IS NULL)), "is_required" bool NOT NULL, "fallback_value" text NULL CHECK ((JSON_VALID("fallback_value") OR "fallback_value" IS NULL)), "timeout_seconds" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "schema_id" bigint NOT NULL REFERENCES "bfagent_contextschema" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_feature_document" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "title" varchar(200) NOT NULL, "file_path" varchar(500) NOT NULL, "uploaded_file" varchar(100) NULL, "document_type" varchar(20) NOT NULL, "description" text NOT NULL, "is_auto_discovered" bool NOT NULL, "discovered_at" datetime NOT NULL, "file_size" integer NOT NULL, "word_count" integer NOT NULL, "last_modified" datetime NULL, "order" integer NOT NULL, "feature_id" bigint NOT NULL REFERENCES "bfagent_component_registry" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_feature_document_keyword" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "keyword" varchar(100) NOT NULL, "keyword_type" varchar(20) NOT NULL, "weight" integer NOT NULL, "feature_id" bigint NOT NULL REFERENCES "bfagent_component_registry" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_generatedimage" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "image_id" varchar(100) NOT NULL UNIQUE, "image_type" varchar(50) NOT NULL, "status" varchar(20) NOT NULL, "provider_used" varchar(50) NOT NULL, "prompt_used" text NOT NULL, "negative_prompt_used" text NULL, "image_url" varchar(500) NOT NULL, "image_file" varchar(100) NULL, "thumbnail_url" varchar(500) NULL, "resolution" varchar(20) NOT NULL, "quality" varchar(20) NOT NULL, "seed" integer NULL, "generation_time_seconds" real NULL, "cost_usd" decimal NOT NULL, "retry_count" integer NOT NULL, "content_context" text NOT NULL CHECK ((JSON_VALID("content_context") OR "content_context" IS NULL)), "quality_score" real NULL, "user_rating" integer NULL, "approved_at" datetime NULL, "rejection_reason" text NULL, "tags" text NOT NULL CHECK ((JSON_VALID("tags") OR "tags" IS NULL)), "metadata" text NOT NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "error_message" text NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "approved_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "chapter_id" bigint NULL REFERENCES "writing_chapters" ("id") DEFERRABLE INITIALLY DEFERRED, "project_id" bigint NULL REFERENCES "writing_book_projects" ("id") DEFERRABLE INITIALLY DEFERRED, "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "style_profile_id" bigint NULL REFERENCES "bfagent_imagestyleprofile" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_imagegenerationbatch" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "batch_id" varchar(100) NOT NULL UNIQUE, "name" varchar(200) NOT NULL, "description" text NULL, "image_type" varchar(50) NOT NULL, "provider" varchar(50) NOT NULL, "total_images" integer NOT NULL, "generated_count" integer NOT NULL, "failed_count" integer NOT NULL, "status" varchar(20) NOT NULL, "total_cost_usd" decimal NOT NULL, "estimated_cost_usd" decimal NOT NULL, "created_at" datetime NOT NULL, "started_at" datetime NULL, "completed_at" datetime NULL, "project_id" bigint NOT NULL REFERENCES "writing_book_projects" ("id") DEFERRABLE INITIALLY DEFERRED, "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "style_profile_id" bigint NULL REFERENCES "bfagent_imagestyleprofile" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_imagestyleprofile" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "style_id" varchar(100) NOT NULL UNIQUE, "display_name" varchar(200) NOT NULL, "description" text NULL, "art_style" varchar(50) NOT NULL, "color_mood" varchar(500) NOT NULL, "base_prompt" text NOT NULL, "negative_prompt" text NULL, "default_resolution" varchar(20) NOT NULL, "default_quality" varchar(20) NOT NULL, "preferred_provider" varchar(50) NOT NULL, "consistency_weight" real NOT NULL, "style_strength" real NOT NULL, "seed" integer NULL, "reference_images" text NOT NULL CHECK ((JSON_VALID("reference_images") OR "reference_images" IS NULL)), "tags" text NOT NULL CHECK ((JSON_VALID("tags") OR "tags" IS NULL)), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "version" varchar(20) NOT NULL, "usage_count" integer NOT NULL, "total_cost_usd" decimal NOT NULL, "project_id" bigint NULL REFERENCES "writing_book_projects" ("id") DEFERRABLE INITIALLY DEFERRED, "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_migration_conflict" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "conflict_type" varchar(50) NOT NULL, "description" text NOT NULL, "detected_at" datetime NOT NULL, "resolved" bool NOT NULL, "migration1_id" bigint NOT NULL REFERENCES "bfagent_migration_registry" ("id") DEFERRABLE INITIALLY DEFERRED, "migration2_id" bigint NOT NULL REFERENCES "bfagent_migration_registry" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_migration_registry" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "app_label" varchar(100) NOT NULL, "migration_name" varchar(255) NOT NULL, "migration_number" integer NOT NULL, "file_path" varchar(500) NOT NULL, "file_hash" varchar(64) NOT NULL, "description" text NOT NULL, "migration_type" varchar(20) NOT NULL, "complexity_score" integer NOT NULL, "is_reversible" bool NOT NULL, "requires_downtime" bool NOT NULL, "models_created" text NOT NULL CHECK ((JSON_VALID("models_created") OR "models_created" IS NULL)), "models_deleted" text NOT NULL CHECK ((JSON_VALID("models_deleted") OR "models_deleted" IS NULL)), "fields_added" text NOT NULL CHECK ((JSON_VALID("fields_added") OR "fields_added" IS NULL)), "fields_removed" text NOT NULL CHECK ((JSON_VALID("fields_removed") OR "fields_removed" IS NULL)), "fields_modified" text NOT NULL CHECK ((JSON_VALID("fields_modified") OR "fields_modified" IS NULL)), "depends_on" text NOT NULL CHECK ((JSON_VALID("depends_on") OR "depends_on" IS NULL)), "estimated_affected_rows" integer NOT NULL, "estimated_duration_seconds" integer NOT NULL, "warnings" text NOT NULL CHECK ((JSON_VALID("warnings") OR "warnings" IS NULL)), "rollback_risks" text NOT NULL CHECK ((JSON_VALID("rollback_risks") OR "rollback_risks" IS NULL)), "is_applied" bool NOT NULL, "applied_at" datetime NULL, "discovered_at" datetime NOT NULL, "updated_at" datetime NOT NULL);
CREATE TABLE "bfagent_requirementtestlink" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "criterion_id" varchar(50) NOT NULL, "link_type" varchar(20) NOT NULL, "status" varchar(20) NOT NULL, "last_test_result" varchar(20) NOT NULL, "last_executed_at" datetime NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "test_case_id" char(32) NOT NULL REFERENCES "bfagent_testcase" ("id") DEFERRABLE INITIALLY DEFERRED, "requirement_id" char(32) NOT NULL REFERENCES "bfagent_testrequirement" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_reviewparticipant" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "role" varchar(10) NOT NULL, "can_comment" bool NOT NULL, "can_rate" bool NOT NULL, "can_see_other_comments" bool NOT NULL, "status" varchar(20) NOT NULL, "joined_at" datetime NOT NULL, "last_activity_at" datetime NULL, "comments_count" integer NOT NULL, "ratings_count" integer NOT NULL, "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "review_round_id" bigint NOT NULL REFERENCES "bfagent_reviewround" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_reviewround" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "title" varchar(200) NOT NULL, "description" text NOT NULL, "status" varchar(20) NOT NULL, "start_date" datetime NOT NULL, "end_date" datetime NULL, "completed_at" datetime NULL, "allow_comments" bool NOT NULL, "allow_ratings" bool NOT NULL, "comments_visible_to_others" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "total_comments" integer NOT NULL, "unread_comments" integer NOT NULL, "total_participants" integer NOT NULL, "total_ratings" integer NOT NULL, "average_rating" real NULL, "created_by_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "project_id" bigint NOT NULL REFERENCES "writing_book_projects" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_testbug" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "title" varchar(200) NOT NULL, "description" text NOT NULL, "severity" varchar(20) NOT NULL, "page_url" varchar(500) NOT NULL, "status" varchar(20) NOT NULL, "reported_at" datetime NOT NULL, "screenshot_id" bigint NULL REFERENCES "bfagent_testscreenshot" ("id") DEFERRABLE INITIALLY DEFERRED, "session_id" char(32) NOT NULL REFERENCES "bfagent_testsession" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_testcase" ("id" char(32) NOT NULL PRIMARY KEY, "test_id" varchar(100) NOT NULL UNIQUE, "name" varchar(200) NOT NULL, "description" text NOT NULL, "framework" varchar(50) NOT NULL, "test_type" varchar(50) NOT NULL, "test_code" text NOT NULL, "file_path" varchar(500) NOT NULL, "tags" text NOT NULL CHECK ((JSON_VALID("tags") OR "tags" IS NULL)), "priority" integer NOT NULL, "estimated_duration" integer NOT NULL, "status" varchar(20) NOT NULL, "is_auto_generated" bool NOT NULL, "generation_metadata" text NOT NULL CHECK ((JSON_VALID("generation_metadata") OR "generation_metadata" IS NULL)), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);
CREATE TABLE "bfagent_testcoveragereport" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "total_criteria" integer NOT NULL, "criteria_with_tests" integer NOT NULL, "tests_passing" integer NOT NULL, "tests_failing" integer NOT NULL, "tests_pending" integer NOT NULL, "coverage_percentage" real NOT NULL, "last_updated" datetime NOT NULL, "last_test_run" datetime NULL, "requirement_id" char(32) NOT NULL UNIQUE REFERENCES "bfagent_testrequirement" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_testexecution" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "executed_at" datetime NOT NULL, "result" varchar(20) NOT NULL, "duration" real NOT NULL, "error_message" text NOT NULL, "error_traceback" text NOT NULL, "environment" varchar(50) NOT NULL, "git_commit" varchar(40) NOT NULL, "log_file_path" varchar(500) NOT NULL, "screenshot_paths" text NOT NULL CHECK ((JSON_VALID("screenshot_paths") OR "screenshot_paths" IS NULL)), "execution_metadata" text NOT NULL CHECK ((JSON_VALID("execution_metadata") OR "execution_metadata" IS NULL)), "executed_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "test_case_id" char(32) NOT NULL REFERENCES "bfagent_testcase" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_testlog" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "timestamp" datetime NOT NULL, "url" varchar(500) NOT NULL, "method" varchar(10) NOT NULL, "response_status" integer NULL, "response_time" datetime NULL, "request_data" text NOT NULL CHECK ((JSON_VALID("request_data") OR "request_data" IS NULL)), "notes" text NOT NULL, "session_id" char(32) NOT NULL REFERENCES "bfagent_testsession" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_testrequirement" ("id" char(32) NOT NULL PRIMARY KEY, "name" varchar(200) NOT NULL, "description" text NOT NULL, "category" varchar(50) NOT NULL, "priority" varchar(20) NOT NULL, "status" varchar(20) NOT NULL, "acceptance_criteria" text NOT NULL CHECK ((JSON_VALID("acceptance_criteria") OR "acceptance_criteria" IS NULL)), "ui_requirements" text NOT NULL CHECK ((JSON_VALID("ui_requirements") OR "ui_requirements" IS NULL)), "test_coverage_target" integer NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "tags" text NOT NULL CHECK ((JSON_VALID("tags") OR "tags" IS NULL)), "url" varchar(500) NULL, "actual_behavior" text NOT NULL, "expected_behavior" text NOT NULL, "notes" text NOT NULL, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_testscreenshot" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "timestamp" datetime NOT NULL, "page_url" varchar(500) NOT NULL, "image" varchar(100) NOT NULL, "notes" text NOT NULL, "is_bug_screenshot" bool NOT NULL, "session_id" char(32) NOT NULL REFERENCES "bfagent_testsession" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "bfagent_testsession" ("id" char(32) NOT NULL PRIMARY KEY, "started_at" datetime NOT NULL, "ended_at" datetime NULL, "test_type" varchar(50) NOT NULL, "notes" text NOT NULL, "status" varchar(20) NOT NULL, "requirement_id" char(32) NULL REFERENCES "bfagent_testrequirement" ("id") DEFERRABLE INITIALLY DEFERRED, "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "book_characters_v2" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "role_in_book" varchar(100) NOT NULL, "importance" varchar(20) NOT NULL, "character_arc" text NOT NULL, "notes" text NOT NULL, "book_id" bigint NOT NULL REFERENCES "writing_book_projects" ("id") DEFERRABLE INITIALLY DEFERRED, "first_appearance_id" bigint NULL REFERENCES "chapters_v2" ("id") DEFERRABLE INITIALLY DEFERRED, "character_id" bigint NOT NULL REFERENCES "characters_v2" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "book_statuses" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(100) NOT NULL, "slug" varchar(100) NOT NULL, "description" text NOT NULL, "icon" varchar(50) NOT NULL, "color" varchar(20) NOT NULL, "badge_style" varchar(20) NOT NULL, "stage" varchar(50) NOT NULL, "is_final" bool NOT NULL, "is_active" bool NOT NULL, "sort_order" integer NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "domain_art_id" bigint NULL REFERENCES "domain_arts" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "book_type_phases" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "order" integer NOT NULL, "is_required" bool NOT NULL, "estimated_days" integer NULL, "description_override" text NOT NULL, "book_type_id" bigint NOT NULL REFERENCES "book_types" ("id") DEFERRABLE INITIALLY DEFERRED, "phase_id" bigint NOT NULL REFERENCES "workflow_phases" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "book_types" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(100) NOT NULL, "description" text NULL, "complexity" varchar(50) NULL, "estimated_duration_hours" integer NULL, "target_word_count_min" integer NULL, "target_word_count_max" integer NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "configuration" text NULL);
CREATE TABLE "cad_analysis_category" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NOT NULL UNIQUE, "name_de" varchar(200) NOT NULL, "name_en" varchar(200) NOT NULL, "description" text NOT NULL, "sort_order" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "handler_class" varchar(200) NOT NULL, "automation_potential" integer NOT NULL, "priority" varchar(20) NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 9 WHERE name = 'cad_analysis_category';
CREATE TABLE "cad_analysis_jobs" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "external_project_id" varchar(100) NOT NULL, "title" varchar(200) NOT NULL, "description" text NOT NULL, "analysis_type" varchar(20) NOT NULL, "standards" text NOT NULL CHECK ((JSON_VALID("standards") OR "standards" IS NULL)), "config" text NOT NULL CHECK ((JSON_VALID("config") OR "config" IS NULL)), "status" varchar(20) NOT NULL, "progress" integer NOT NULL, "error_message" text NOT NULL, "created_at" datetime NOT NULL, "started_at" datetime NULL, "completed_at" datetime NULL, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "project_id" bigint NULL REFERENCES "domain_projects" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "cad_analysis_reports" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "title" varchar(200) NOT NULL, "report_type" varchar(20) NOT NULL, "file" varchar(100) NOT NULL, "file_size" bigint NOT NULL, "metadata" text NOT NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "generated_at" datetime NOT NULL, "job_id" bigint NOT NULL REFERENCES "cad_analysis_jobs" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "cad_analysis_results" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "result_type" varchar(30) NOT NULL, "handler_name" varchar(100) NOT NULL, "data" text NOT NULL CHECK ((JSON_VALID("data") OR "data" IS NULL)), "summary" text NOT NULL, "confidence_score" real NULL, "quality_score" real NULL, "success" bool NOT NULL, "error_message" text NOT NULL, "created_at" datetime NOT NULL, "processing_time_ms" integer NULL, "job_id" bigint NOT NULL REFERENCES "cad_analysis_jobs" ("id") DEFERRABLE INITIALLY DEFERRED, "file_id" bigint NULL REFERENCES "cad_drawing_files" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "cad_building_type" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NOT NULL UNIQUE, "name_de" varchar(200) NOT NULL, "name_en" varchar(200) NOT NULL, "description" text NOT NULL, "sort_order" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "building_class" varchar(50) NOT NULL, "fire_safety_category" varchar(50) NOT NULL, "requires_accessibility" bool NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 6 WHERE name = 'cad_building_type';
CREATE TABLE "cad_compliance_standard" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NOT NULL UNIQUE, "name_de" varchar(200) NOT NULL, "name_en" varchar(200) NOT NULL, "description" text NOT NULL, "sort_order" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "standard_type" varchar(50) NOT NULL, "issuing_body" varchar(200) NOT NULL, "version" varchar(50) NOT NULL, "publication_date" date NULL, "url" varchar(200) NOT NULL, "is_mandatory" bool NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 9 WHERE name = 'cad_compliance_standard';
CREATE TABLE "cad_drawing_files" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "file" varchar(100) NOT NULL, "original_filename" varchar(255) NOT NULL, "file_type" varchar(10) NOT NULL, "file_size" bigint NOT NULL, "metadata" text NOT NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "is_processed" bool NOT NULL, "processed_at" datetime NULL, "uploaded_at" datetime NOT NULL, "job_id" bigint NOT NULL REFERENCES "cad_analysis_jobs" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "cad_drawing_type" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NOT NULL UNIQUE, "name_de" varchar(200) NOT NULL, "name_en" varchar(200) NOT NULL, "description" text NOT NULL, "sort_order" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "icon" varchar(50) NOT NULL, "color" varchar(7) NOT NULL, "requires_3d" bool NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 10 WHERE name = 'cad_drawing_type';
CREATE TABLE "cad_layer_standard" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NOT NULL UNIQUE, "name_de" varchar(200) NOT NULL, "name_en" varchar(200) NOT NULL, "description" text NOT NULL, "sort_order" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "naming_pattern" varchar(200) NOT NULL, "example_layers" text NOT NULL, "discipline_separator" varchar(5) NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 3 WHERE name = 'cad_layer_standard';
CREATE TABLE "cad_severity_level" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NOT NULL UNIQUE, "name_de" varchar(200) NOT NULL, "name_en" varchar(200) NOT NULL, "description" text NOT NULL, "sort_order" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "color" varchar(7) NOT NULL, "icon" varchar(50) NOT NULL, "requires_action" bool NOT NULL, "escalation_hours" integer NULL);UPDATE "main"."sqlite_sequence" SET seq = 5 WHERE name = 'cad_severity_level';
CREATE TABLE "chapters_v2" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "title" varchar(200) NOT NULL, "number" integer unsigned NOT NULL CHECK ("number" >= 0), "content" text NOT NULL, "summary" text NOT NULL, "notes" text NOT NULL, "status" varchar(50) NOT NULL, "word_count" integer NOT NULL, "word_count_target" integer NULL, "ai_generated" bool NOT NULL, "generation_prompt" text NOT NULL, "settings" text NOT NULL CHECK ((JSON_VALID("settings") OR "settings" IS NULL)), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "book_id" bigint NOT NULL REFERENCES "writing_book_projects" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "characters_v2" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(200) NOT NULL, "full_name" varchar(300) NOT NULL, "nickname" varchar(100) NOT NULL, "age" integer unsigned NULL CHECK ("age" >= 0), "gender" varchar(50) NOT NULL, "appearance" text NOT NULL, "personality" text NOT NULL, "background" text NOT NULL, "motivation" text NOT NULL, "profile_data" text NOT NULL CHECK ((JSON_VALID("profile_data") OR "profile_data" IS NULL)), "backstory" text NOT NULL, "profile_completion" integer NOT NULL, "role" varchar(50) NOT NULL, "notes" text NOT NULL, "settings" text NOT NULL CHECK ((JSON_VALID("settings") OR "settings" IS NULL)), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "created_by_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "checklist_instances" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "object_id" integer unsigned NOT NULL CHECK ("object_id" >= 0), "phase" varchar(50) NOT NULL, "is_locked" bool NOT NULL, "completed_at" datetime NULL, "auto_completed_items" integer NOT NULL, "ai_confidence_score" real NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "completed_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "content_type_id" integer NOT NULL REFERENCES "django_content_type" ("id") DEFERRABLE INITIALLY DEFERRED, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "template_id" bigint NOT NULL REFERENCES "checklist_templates" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "checklist_item_statuses" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_checked" bool NOT NULL, "checked_at" datetime NULL, "auto_checked" bool NOT NULL, "ai_confidence" real NULL, "evidence" text NOT NULL CHECK ((JSON_VALID("evidence") OR "evidence" IS NULL)), "notes" text NOT NULL, "is_enabled" bool NOT NULL, "checked_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "checklist_id" bigint NOT NULL REFERENCES "checklist_instances" ("id") DEFERRABLE INITIALLY DEFERRED, "item_id" bigint NOT NULL REFERENCES "checklist_items" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "checklist_items" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "template_id" INTEGER NOT NULL,
  "text" VARCHAR(500) NOT NULL,
  "help_text" TEXT NOT NULL,
  "order" INTEGER NOT NULL DEFAULT 0,
  "category" VARCHAR(100) NOT NULL,
  "is_mandatory" BOOLEAN NOT NULL DEFAULT 1,
  "condition" VARCHAR(100) NOT NULL,
  "depends_on_id" INTEGER,
  "ai_check_hint" TEXT NOT NULL,
  "reference_norm" VARCHAR(100) NOT NULL,
  "is_active" BOOLEAN NOT NULL DEFAULT 1,
  "linked_handler_id" INTEGER,
  "handler_action" VARCHAR(100) NOT NULL DEFAULT '',
  "handler_config" TEXT NOT NULL DEFAULT '{}',
  "auto_complete_on_handler_success" BOOLEAN NOT NULL DEFAULT 1,
  FOREIGN KEY ("linked_handler_id") REFERENCES "core_handlers" ("id") ON DELETE SET NULL ON UPDATE NO ACTION,
  FOREIGN KEY ("template_id") REFERENCES "checklist_templates" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION,
  FOREIGN KEY ("depends_on_id") REFERENCES "checklist_items" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION
);UPDATE "main"."sqlite_sequence" SET seq = 53 WHERE name = 'checklist_items';
CREATE TABLE "checklist_templates" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "name" VARCHAR(200) NOT NULL,
  "description" TEXT NOT NULL,
  "domain_art_id" INTEGER NOT NULL,
  "domain_type_id" INTEGER,
  "phase" VARCHAR(50) NOT NULL,
  "keywords" JSON NOT NULL,
  "min_required_completion" INTEGER NOT NULL DEFAULT 80,
  "is_active" BOOLEAN NOT NULL DEFAULT 1,
  "is_system" BOOLEAN NOT NULL DEFAULT 0,
  "created_by_id" INTEGER,
  "created_at" DATETIME NOT NULL,
  "updated_at" DATETIME NOT NULL,
  FOREIGN KEY ("domain_art_id") REFERENCES "domain_arts" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION,
  FOREIGN KEY ("domain_type_id") REFERENCES "domain_types" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION,
  FOREIGN KEY ("created_by_id") REFERENCES "auth_user" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION
);UPDATE "main"."sqlite_sequence" SET seq = 4 WHERE name = 'checklist_templates';
CREATE TABLE "comic_dialogues" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "text" text NOT NULL, "order" integer NOT NULL, "dialogue_type" varchar(20) NOT NULL, "bubble_position_x" real NOT NULL, "bubble_position_y" real NOT NULL, "bubble_width" integer NOT NULL, "bubble_height" integer NOT NULL, "font_size" integer NOT NULL, "text_bold" bool NOT NULL, "text_italic" bool NOT NULL, "is_placed" bool NOT NULL, "is_rendered" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "character_id" bigint NULL REFERENCES "writing_characters" ("id") DEFERRABLE INITIALLY DEFERRED, "panel_id" bigint NOT NULL REFERENCES "comic_panels" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "comic_panels" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "panel_number" integer NOT NULL, "description" text NOT NULL, "action" text NOT NULL, "camera_angle" varchar(50) NOT NULL, "shot_type" varchar(50) NOT NULL, "panel_size" varchar(20) NOT NULL, "image_prompt" text NOT NULL, "image_url" varchar(500) NOT NULL, "generation_provider" varchar(50) NOT NULL, "generation_cost_cents" integer NOT NULL, "generation_duration_seconds" real NOT NULL, "status" varchar(20) NOT NULL, "position_x" integer NOT NULL, "position_y" integer NOT NULL, "width" integer NOT NULL, "height" integer NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "chapter_id" bigint NOT NULL REFERENCES "writing_chapters" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "compliance_audit_log" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "action" varchar(100) NOT NULL, "entity_id" integer unsigned NOT NULL CHECK ("entity_id" >= 0), "entity_repr" varchar(255) NOT NULL, "old_values" text NULL CHECK ((JSON_VALID("old_values") OR "old_values" IS NULL)), "new_values" text NULL CHECK ((JSON_VALID("new_values") OR "new_values" IS NULL)), "domain" varchar(50) NOT NULL, "client_id" integer unsigned NULL CHECK ("client_id" >= 0), "timestamp" datetime NOT NULL, "ip_address" char(39) NULL, "user_agent" text NOT NULL, "notes" text NOT NULL, "entity_type_id" integer NOT NULL REFERENCES "django_content_type" ("id") DEFERRABLE INITIALLY DEFERRED, "user_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "compliance_incident_severity" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NULL UNIQUE, "name" varchar(255) NOT NULL, "description" text NOT NULL, "is_active" bool NOT NULL, "sort_order" integer unsigned NOT NULL CHECK ("sort_order" >= 0), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "color" varchar(7) NOT NULL, "authority_notification_required" bool NOT NULL, "affected_notification_required" bool NOT NULL, "notification_deadline_hours" integer unsigned NULL CHECK ("notification_deadline_hours" >= 0));UPDATE "main"."sqlite_sequence" SET seq = 4 WHERE name = 'compliance_incident_severity';
CREATE TABLE "compliance_priority" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NULL UNIQUE, "name" varchar(255) NOT NULL, "description" text NOT NULL, "is_active" bool NOT NULL, "sort_order" integer unsigned NOT NULL CHECK ("sort_order" >= 0), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "color" varchar(7) NOT NULL, "sla_hours" integer unsigned NULL CHECK ("sla_hours" >= 0));UPDATE "main"."sqlite_sequence" SET seq = 4 WHERE name = 'compliance_priority';
CREATE TABLE "compliance_risk_level" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NULL UNIQUE, "name" varchar(255) NOT NULL, "description" text NOT NULL, "is_active" bool NOT NULL, "sort_order" integer unsigned NOT NULL CHECK ("sort_order" >= 0), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "color" varchar(7) NOT NULL, "icon" varchar(50) NOT NULL, "score_min" integer unsigned NOT NULL CHECK ("score_min" >= 0), "score_max" integer unsigned NOT NULL CHECK ("score_max" >= 0));UPDATE "main"."sqlite_sequence" SET seq = 5 WHERE name = 'compliance_risk_level';
CREATE TABLE "compliance_status" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NULL UNIQUE, "name" varchar(255) NOT NULL, "description" text NOT NULL, "is_active" bool NOT NULL, "sort_order" integer unsigned NOT NULL CHECK ("sort_order" >= 0), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "color" varchar(7) NOT NULL, "icon" varchar(50) NOT NULL, "is_terminal" bool NOT NULL, "allows_edit" bool NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 6 WHERE name = 'compliance_status';
CREATE TABLE "compliance_tag" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(50) NOT NULL UNIQUE, "slug" varchar(50) NOT NULL UNIQUE, "color" varchar(7) NOT NULL, "description" text NOT NULL, "domain" varchar(50) NOT NULL, "created_at" datetime NOT NULL, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "compliance_tagged_item" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "object_id" integer unsigned NOT NULL CHECK ("object_id" >= 0), "tagged_at" datetime NOT NULL, "content_type_id" integer NOT NULL REFERENCES "django_content_type" ("id") DEFERRABLE INITIALLY DEFERRED, "tag_id" bigint NOT NULL REFERENCES "compliance_tag" ("id") DEFERRABLE INITIALLY DEFERRED, "tagged_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "content_blocks" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "content_type" varchar(50) NOT NULL, "title" varchar(500) NOT NULL, "order" integer unsigned NOT NULL CHECK ("order" >= 0), "status" varchar(50) NOT NULL, "content" text NOT NULL, "summary" text NOT NULL, "notes" text NOT NULL, "metadata" text NOT NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "ai_analysis" text NOT NULL CHECK ((JSON_VALID("ai_analysis") OR "ai_analysis" IS NULL)), "ai_suggestions" text NOT NULL CHECK ((JSON_VALID("ai_suggestions") OR "ai_suggestions" IS NULL)), "last_ai_check" datetime NULL, "content_hash" varchar(64) NOT NULL, "version" integer unsigned NOT NULL CHECK ("version" >= 0), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "project_id" bigint NOT NULL REFERENCES "writing_book_projects" ("id") DEFERRABLE INITIALLY DEFERRED, "parent_id" bigint NULL REFERENCES "content_blocks" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "core_agent_executions" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "input_data" text NOT NULL CHECK ((JSON_VALID("input_data") OR "input_data" IS NULL)), "prompt_used" text NOT NULL, "output_data" text NOT NULL CHECK ((JSON_VALID("output_data") OR "output_data" IS NULL)), "output_content" text NOT NULL, "tokens_used" integer NOT NULL, "cost" decimal NOT NULL, "duration_seconds" decimal NOT NULL, "quality_score" real NULL, "status" varchar(20) NOT NULL, "error_message" text NOT NULL, "executed_at" datetime NOT NULL, "agent_id" bigint NOT NULL REFERENCES "agents" ("id") DEFERRABLE INITIALLY DEFERRED, "llm_used_id" bigint NULL REFERENCES "llms" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "core_contentitem" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "content_type" varchar(50) NOT NULL, "title" varchar(500) NOT NULL, "content" text NOT NULL, "summary" text NOT NULL, "sequence_number" integer NOT NULL, "status" varchar(50) NOT NULL, "category" varchar(100) NOT NULL, "visual_style" varchar(50) NOT NULL, "related_character_id" integer NULL, "parent_item_id" integer NULL, "priority" integer NOT NULL, "assigned_to_id" integer NULL, "external_id" varchar(100) NOT NULL, "completion_percentage" integer NOT NULL, "primary_tag" varchar(50) NOT NULL, "word_count" integer NOT NULL, "character_count" integer NOT NULL, "is_ai_generated" bool NOT NULL, "ai_confidence_score" real NULL, "ai_model_used" varchar(100) NOT NULL, "domain_data" text NOT NULL CHECK ((JSON_VALID("domain_data") OR "domain_data" IS NULL)), "metadata" text NOT NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "project_id" bigint NOT NULL REFERENCES "writing_book_projects" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "core_customers" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(255) NOT NULL, "short_name" varchar(100) NOT NULL, "customer_number" varchar(50) NULL UNIQUE, "address_street" varchar(255) NOT NULL, "address_zip" varchar(20) NOT NULL, "address_city" varchar(100) NOT NULL, "address_state" varchar(100) NOT NULL, "address_country" varchar(100) NOT NULL, "contact_person" varchar(255) NOT NULL, "contact_email" varchar(254) NOT NULL, "contact_phone" varchar(50) NOT NULL, "contact_mobile" varchar(50) NOT NULL, "industry" varchar(100) NOT NULL, "tax_id" varchar(50) NOT NULL, "website" varchar(200) NOT NULL, "is_active" bool NOT NULL, "customer_type" varchar(50) NOT NULL, "priority" varchar(20) NOT NULL, "notes" text NOT NULL, "metadata" text NOT NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "first_project_at" datetime NULL, "last_activity_at" datetime NULL);UPDATE "main"."sqlite_sequence" SET seq = 1 WHERE name = 'core_customers';
CREATE TABLE "core_locations" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(255) NOT NULL, "location_code" varchar(50) NOT NULL, "description" text NOT NULL, "address_street" varchar(255) NOT NULL, "address_zip" varchar(20) NOT NULL, "address_city" varchar(100) NOT NULL, "address_state" varchar(100) NOT NULL, "address_country" varchar(100) NOT NULL, "building" varchar(100) NOT NULL, "floor" varchar(50) NOT NULL, "room_number" varchar(50) NOT NULL, "area_sqm" decimal NULL, "coordinates_lat" decimal NULL, "coordinates_lng" decimal NULL, "location_type" varchar(100) NOT NULL, "building_type" varchar(100) NOT NULL, "construction_standard" varchar(100) NOT NULL, "site_contact_person" varchar(255) NOT NULL, "site_contact_phone" varchar(50) NOT NULL, "site_contact_email" varchar(254) NOT NULL, "is_active" bool NOT NULL, "access_restricted" bool NOT NULL, "notes" text NOT NULL, "metadata" text NOT NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "customer_id" bigint NOT NULL REFERENCES "core_customers" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "core_plugin_configurations" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "project_id" integer NULL, "config" text NOT NULL CHECK ((JSON_VALID("config") OR "config" IS NULL)), "is_enabled" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "user_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "plugin_id" bigint NOT NULL REFERENCES "core_plugin_registry" ("id") DEFERRABLE INITIALLY DEFERRED, "custom_template_id" bigint NULL REFERENCES "core_prompt_templates" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "core_plugin_executions" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "context_data" text NOT NULL CHECK ((JSON_VALID("context_data") OR "context_data" IS NULL)), "parameters" text NOT NULL CHECK ((JSON_VALID("parameters") OR "parameters" IS NULL)), "result_data" text NOT NULL CHECK ((JSON_VALID("result_data") OR "result_data" IS NULL)), "created_objects" text NOT NULL CHECK ((JSON_VALID("created_objects") OR "created_objects" IS NULL)), "modified_objects" text NOT NULL CHECK ((JSON_VALID("modified_objects") OR "modified_objects" IS NULL)), "execution_time_ms" real NOT NULL, "tokens_used" integer NOT NULL, "cost" decimal NOT NULL, "status" varchar(20) NOT NULL, "error_message" text NOT NULL, "error_type" varchar(100) NOT NULL, "execution_id" varchar(100) NOT NULL UNIQUE, "executed_at" datetime NOT NULL, "executed_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "plugin_id" bigint NOT NULL REFERENCES "core_plugin_registry" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "core_plugin_registry" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(200) NOT NULL, "plugin_id" varchar(100) NOT NULL UNIQUE, "slug" varchar(100) NOT NULL UNIQUE, "domain" varchar(50) NOT NULL, "category" varchar(50) NOT NULL, "tags" text NOT NULL CHECK ((JSON_VALID("tags") OR "tags" IS NULL)), "short_description" varchar(200) NOT NULL, "description" text NOT NULL, "documentation" text NOT NULL, "usage_example" text NOT NULL, "module_path" varchar(255) NOT NULL, "class_name" varchar(100) NOT NULL, "version" varchar(20) NOT NULL, "required_entities" text NOT NULL CHECK ((JSON_VALID("required_entities") OR "required_entities" IS NULL)), "optional_entities" text NOT NULL CHECK ((JSON_VALID("optional_entities") OR "optional_entities" IS NULL)), "required_permissions" text NOT NULL CHECK ((JSON_VALID("required_permissions") OR "required_permissions" IS NULL)), "default_config" text NOT NULL CHECK ((JSON_VALID("default_config") OR "default_config" IS NULL)), "supports_streaming" bool NOT NULL, "supports_async" bool NOT NULL, "max_execution_time" integer NOT NULL, "is_active" bool NOT NULL, "is_beta" bool NOT NULL, "is_premium" bool NOT NULL, "is_public" bool NOT NULL, "ab_test_group" varchar(50) NOT NULL, "ab_test_weight" real NOT NULL, "execution_count" integer NOT NULL, "success_count" integer NOT NULL, "failure_count" integer NOT NULL, "avg_execution_time" real NOT NULL, "avg_tokens_used" integer NOT NULL, "avg_cost" decimal NOT NULL, "user_rating" real NOT NULL, "rating_count" integer NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "last_executed_at" datetime NULL, "icon" varchar(50) NOT NULL, "homepage_url" varchar(200) NOT NULL, "repository_url" varchar(200) NOT NULL, "author_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "maintainer_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "default_template_id" bigint NULL REFERENCES "core_prompt_templates" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "core_plugin_registry_depends_on" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "from_pluginregistry_id" bigint NOT NULL REFERENCES "core_plugin_registry" ("id") DEFERRABLE INITIALLY DEFERRED, "to_pluginregistry_id" bigint NOT NULL REFERENCES "core_plugin_registry" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "core_prompt_executions" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "variables_used" text NOT NULL CHECK ((JSON_VALID("variables_used") OR "variables_used" IS NULL)), "rendered_prompt" text NOT NULL, "output_content" text NOT NULL, "output_data" text NOT NULL CHECK ((JSON_VALID("output_data") OR "output_data" IS NULL)), "tokens_used" integer NOT NULL, "cost" decimal NOT NULL, "execution_time_seconds" real NOT NULL, "quality_score" real NULL, "status" varchar(20) NOT NULL, "error_message" text NOT NULL, "executed_at" datetime NOT NULL, "agent_id" bigint NULL REFERENCES "agents" ("id") DEFERRABLE INITIALLY DEFERRED, "executed_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "llm_id" bigint NULL REFERENCES "llms" ("id") DEFERRABLE INITIALLY DEFERRED, "template_id" bigint NOT NULL REFERENCES "core_prompt_templates" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "core_prompt_templates" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(200) NOT NULL, "template_key" varchar(100) NOT NULL UNIQUE, "domain" varchar(100) NOT NULL, "category" integer NOT NULL, "description" text NOT NULL, "tags" text NOT NULL CHECK ((JSON_VALID("tags") OR "tags" IS NULL)), "system_prompt" text NOT NULL, "user_prompt_template" text NOT NULL, "required_variables" text NOT NULL CHECK ((JSON_VALID("required_variables") OR "required_variables" IS NULL)), "optional_variables" text NOT NULL CHECK ((JSON_VALID("optional_variables") OR "optional_variables" IS NULL)), "variable_defaults" text NOT NULL CHECK ((JSON_VALID("variable_defaults") OR "variable_defaults" IS NULL)), "variable_schemas" text NOT NULL CHECK ((JSON_VALID("variable_schemas") OR "variable_schemas" IS NULL)), "output_format" integer NOT NULL, "output_schema" text NOT NULL CHECK ((JSON_VALID("output_schema") OR "output_schema" IS NULL)), "max_tokens" integer NOT NULL, "temperature" real NOT NULL, "top_p" real NOT NULL, "frequency_penalty" real NOT NULL, "presence_penalty" real NOT NULL, "version" varchar(20) NOT NULL, "is_active" bool NOT NULL, "is_default" bool NOT NULL, "ab_test_group" integer NOT NULL, "ab_test_weight" real NOT NULL, "examples" text NOT NULL CHECK ((JSON_VALID("examples") OR "examples" IS NULL)), "language" integer NOT NULL, "usage_count" integer NOT NULL, "success_count" integer NOT NULL, "failure_count" integer NOT NULL, "avg_quality_score" real NOT NULL, "avg_execution_time" real NOT NULL, "avg_tokens_used" integer NOT NULL, "avg_cost" decimal NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "last_used_at" datetime NULL, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "fallback_template_id" bigint NULL REFERENCES "core_prompt_templates" ("id") DEFERRABLE INITIALLY DEFERRED, "parent_template_id" bigint NULL REFERENCES "core_prompt_templates" ("id") DEFERRABLE INITIALLY DEFERRED, "preferred_llm_id" bigint NULL REFERENCES "llms" ("id") DEFERRABLE INITIALLY DEFERRED);UPDATE "main"."sqlite_sequence" SET seq = 13 WHERE name = 'core_prompt_templates';
CREATE TABLE "core_prompt_versions" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "version_number" varchar(20) NOT NULL, "system_prompt" text NOT NULL, "user_prompt_template" text NOT NULL, "config_snapshot" text NOT NULL CHECK ((JSON_VALID("config_snapshot") OR "config_snapshot" IS NULL)), "change_summary" text NOT NULL, "changed_at" datetime NOT NULL, "changed_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "template_id" bigint NOT NULL REFERENCES "core_prompt_templates" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "debug_toolbar_historyentry" ("request_id" char(32) NOT NULL PRIMARY KEY, "data" text NOT NULL CHECK ((JSON_VALID("data") OR "data" IS NULL)), "created_at" datetime NOT NULL);
CREATE TABLE "django_admin_log" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "object_id" text NULL, "object_repr" varchar(200) NOT NULL, "action_flag" smallint unsigned NOT NULL CHECK ("action_flag" >= 0), "change_message" text NOT NULL, "content_type_id" integer NULL REFERENCES "django_content_type" ("id") DEFERRABLE INITIALLY DEFERRED, "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "action_time" datetime NOT NULL);
CREATE TABLE "django_content_type" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "app_label" varchar(100) NOT NULL, "model" varchar(100) NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 211 WHERE name = 'django_content_type';
CREATE TABLE "django_migrations" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "app" varchar(255) NOT NULL, "name" varchar(255) NOT NULL, "applied" datetime NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 44 WHERE name = 'django_migrations';
CREATE TABLE "django_session" ("session_key" varchar(40) NOT NULL PRIMARY KEY, "session_data" text NOT NULL, "expire_date" datetime NOT NULL);
CREATE TABLE "domain_arts" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "name" VARCHAR(100) NOT NULL,
  "slug" VARCHAR(50) NOT NULL,
  "display_name" VARCHAR(200) NOT NULL,
  "description" TEXT,
  "icon" VARCHAR(50),
  "color" VARCHAR(20) DEFAULT 'primary',
  "is_active" BOOLEAN DEFAULT 1,
  "is_experimental" BOOLEAN DEFAULT 0,
  "created_at" DATETIME DEFAULT CURRENT_TIMESTAMP,
  "updated_at" DATETIME DEFAULT CURRENT_TIMESTAMP,
  "config" TEXT DEFAULT "{}",
  "dashboard_url" VARCHAR(200) DEFAULT "",
  "display_order" INTEGER DEFAULT 0,
  UNIQUE ("name" ASC),
  UNIQUE ("slug" ASC)
);UPDATE "main"."sqlite_sequence" SET seq = 16 WHERE name = 'domain_arts';
CREATE TABLE "domain_arts_copy1" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "name" VARCHAR(100) NOT NULL,
  "slug" VARCHAR(50) NOT NULL,
  "display_name" VARCHAR(200) NOT NULL,
  "description" TEXT,
  "icon" VARCHAR(50),
  "color" VARCHAR(20) DEFAULT 'primary',
  "is_active" BOOLEAN DEFAULT 1,
  "is_experimental" BOOLEAN DEFAULT 0,
  "created_at" DATETIME DEFAULT CURRENT_TIMESTAMP,
  "updated_at" DATETIME DEFAULT CURRENT_TIMESTAMP,
  "config" TEXT DEFAULT "{}",
  "dashboard_url" VARCHAR(200) DEFAULT "",
  "display_order" INTEGER DEFAULT 0,
  UNIQUE ("name" ASC),
  UNIQUE ("slug" ASC)
);UPDATE "main"."sqlite_sequence" SET seq = 16 WHERE name = 'domain_arts_copy1';
CREATE TABLE "domain_phases" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "sort_order" integer NOT NULL, "config" text NOT NULL CHECK ((JSON_VALID("config") OR "config" IS NULL)), "is_active" bool NOT NULL, "is_required" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "workflow_phase_id" bigint NOT NULL REFERENCES "workflow_phases" ("id") DEFERRABLE INITIALLY DEFERRED, "domain_type_id" bigint NOT NULL REFERENCES "domain_types" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "domain_projects" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "title" varchar(500) NOT NULL, "description" text NOT NULL, "status" varchar(20) NOT NULL, "metadata" text NOT NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "started_at" datetime NULL, "completed_at" datetime NULL, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "current_phase_id" bigint NULL REFERENCES "domain_phases" ("id") DEFERRABLE INITIALLY DEFERRED, "domain_type_id" bigint NOT NULL REFERENCES "domain_types" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "domain_section_items" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(100) NOT NULL, "slug" varchar(50) NOT NULL, "display_name" varchar(200) NOT NULL, "description" text NOT NULL, "icon" varchar(50) NOT NULL, "color" varchar(20) NOT NULL, "url" varchar(200) NOT NULL, "badge_text" varchar(20) NOT NULL, "badge_color" varchar(20) NOT NULL, "requires_staff" bool NOT NULL, "requires_superuser" bool NOT NULL, "required_permission" varchar(100) NOT NULL, "display_order" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "section_id" bigint NOT NULL REFERENCES "domain_sections" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "domain_sections" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(100) NOT NULL, "slug" varchar(50) NOT NULL, "display_name" varchar(200) NOT NULL, "description" text NOT NULL, "icon" varchar(50) NOT NULL, "color" varchar(20) NOT NULL, "url" varchar(200) NOT NULL, "config" text NOT NULL CHECK ((JSON_VALID("config") OR "config" IS NULL)), "display_order" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "domain_art_id" bigint NOT NULL REFERENCES "domain_arts" ("id") DEFERRABLE INITIALLY DEFERRED);UPDATE "main"."sqlite_sequence" SET seq = 2 WHERE name = 'domain_sections';
CREATE TABLE "domain_types" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "domain_art_id" INTEGER NOT NULL,
  "name" VARCHAR(100) NOT NULL,
  "slug" VARCHAR(50) NOT NULL,
  "display_name" VARCHAR(200) NOT NULL,
  "description" TEXT,
  "icon" VARCHAR(50),
  "color" VARCHAR(20),
  "config" JSON DEFAULT '{}',
  "is_active" BOOLEAN DEFAULT 1,
  "sort_order" INTEGER DEFAULT 0,
  "created_at" DATETIME DEFAULT CURRENT_TIMESTAMP,
  "updated_at" DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY ("domain_art_id") REFERENCES "domain_arts" ("id") ON DELETE CASCADE ON UPDATE NO ACTION,
  UNIQUE ("domain_art_id" ASC, "slug" ASC)
);UPDATE "main"."sqlite_sequence" SET seq = 12 WHERE name = 'domain_types';
CREATE TABLE "dsb_branche" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NULL UNIQUE, "name" varchar(255) NOT NULL, "description" text NOT NULL, "is_active" bool NOT NULL, "sort_order" integer unsigned NOT NULL CHECK ("sort_order" >= 0), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "risk_factor" decimal NOT NULL, "special_requirements" text NOT NULL CHECK ((JSON_VALID("special_requirements") OR "special_requirements" IS NULL)));UPDATE "main"."sqlite_sequence" SET seq = 7 WHERE name = 'dsb_branche';
CREATE TABLE "dsb_datenkategorie" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NULL UNIQUE, "name" varchar(255) NOT NULL, "description" text NOT NULL, "is_active" bool NOT NULL, "sort_order" integer unsigned NOT NULL CHECK ("sort_order" >= 0), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "examples" text NOT NULL CHECK ((JSON_VALID("examples") OR "examples" IS NULL)), "sensitivity_id" bigint NULL REFERENCES "compliance_risk_level" ("id") DEFERRABLE INITIALLY DEFERRED);UPDATE "main"."sqlite_sequence" SET seq = 6 WHERE name = 'dsb_datenkategorie';
CREATE TABLE "dsb_dokument" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "client_id" integer unsigned NULL CHECK ("client_id" >= 0), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "is_active" bool NOT NULL, "deleted_at" datetime NULL, "title" varchar(255) NOT NULL, "document_type" varchar(100) NOT NULL, "version" varchar(20) NOT NULL, "content" text NOT NULL, "file" varchar(100) NOT NULL, "status" varchar(20) NOT NULL, "valid_from" date NULL, "valid_until" date NULL, "review_date" date NULL, "approved_at" datetime NULL, "approved_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "client_content_type_id" integer NULL REFERENCES "django_content_type" ("id") DEFERRABLE INITIALLY DEFERRED, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "deleted_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "mandant_id" bigint NOT NULL REFERENCES "dsb_mandant" ("id") DEFERRABLE INITIALLY DEFERRED, "verarbeitung_id" bigint NULL REFERENCES "dsb_verarbeitung" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "dsb_mandant" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "client_id" integer unsigned NULL CHECK ("client_id" >= 0), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "is_active" bool NOT NULL, "deleted_at" datetime NULL, "name" varchar(255) NOT NULL, "external_id" varchar(100) NOT NULL, "client_type" varchar(50) NOT NULL, "primary_contact_name" varchar(100) NOT NULL, "primary_contact_email" varchar(254) NOT NULL, "primary_contact_phone" varchar(30) NOT NULL, "address" text NOT NULL, "contract_start" date NOT NULL, "contract_end" date NULL, "metadata" text NOT NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "handelsregisternummer" varchar(50) NOT NULL, "ust_id" varchar(20) NOT NULL, "anzahl_mitarbeiter" integer unsigned NULL CHECK ("anzahl_mitarbeiter" >= 0), "dsb_intern" bool NOT NULL, "dsb_name" varchar(100) NOT NULL, "dsb_email" varchar(254) NOT NULL, "_cached_verarbeitungen_count" integer unsigned NOT NULL CHECK ("_cached_verarbeitungen_count" >= 0), "_cached_compliance_score" decimal NULL, "betreuer_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "branche_id" bigint NOT NULL REFERENCES "dsb_branche" ("id") DEFERRABLE INITIALLY DEFERRED, "client_content_type_id" integer NULL REFERENCES "django_content_type" ("id") DEFERRABLE INITIALLY DEFERRED, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "deleted_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "risk_level_id" bigint NULL REFERENCES "compliance_risk_level" ("id") DEFERRABLE INITIALLY DEFERRED, "rechtsform_id" bigint NOT NULL REFERENCES "dsb_rechtsform" ("id") DEFERRABLE INITIALLY DEFERRED);UPDATE "main"."sqlite_sequence" SET seq = 8 WHERE name = 'dsb_mandant';
CREATE TABLE "dsb_mandant_tom" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "implementiert" bool NOT NULL, "bemerkung" text NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "mandant_id" bigint NOT NULL REFERENCES "dsb_mandant" ("id") DEFERRABLE INITIALLY DEFERRED, "massnahme_id" bigint NOT NULL REFERENCES "dsb_tom_massnahme" ("id") DEFERRABLE INITIALLY DEFERRED);UPDATE "main"."sqlite_sequence" SET seq = 358 WHERE name = 'dsb_mandant_tom';
CREATE TABLE "dsb_rechtsform" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NULL UNIQUE, "name" varchar(255) NOT NULL, "description" text NOT NULL, "is_active" bool NOT NULL, "sort_order" integer unsigned NOT NULL CHECK ("sort_order" >= 0), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "requires_handelsregister" bool NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 7 WHERE name = 'dsb_rechtsform';
CREATE TABLE "dsb_rechtsgrundlage" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NULL UNIQUE, "name" varchar(255) NOT NULL, "description" text NOT NULL, "is_active" bool NOT NULL, "sort_order" integer unsigned NOT NULL CHECK ("sort_order" >= 0), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "article_reference" varchar(20) NOT NULL, "requires_consent_management" bool NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 4 WHERE name = 'dsb_rechtsgrundlage';
CREATE TABLE "dsb_tom_kategorie" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NULL UNIQUE, "name" varchar(255) NOT NULL, "description" text NOT NULL, "is_active" bool NOT NULL, "sort_order" integer unsigned NOT NULL CHECK ("sort_order" >= 0), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 8 WHERE name = 'dsb_tom_kategorie';
CREATE TABLE "dsb_tom_massnahme" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NULL UNIQUE, "name" varchar(255) NOT NULL, "description" text NOT NULL, "is_active" bool NOT NULL, "sort_order" integer unsigned NOT NULL CHECK ("sort_order" >= 0), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "kategorie_id" bigint NOT NULL REFERENCES "dsb_tom_kategorie" ("id") DEFERRABLE INITIALLY DEFERRED);UPDATE "main"."sqlite_sequence" SET seq = 120 WHERE name = 'dsb_tom_massnahme';
CREATE TABLE "dsb_verarbeitung" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "client_id" integer unsigned NULL CHECK ("client_id" >= 0), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "is_active" bool NOT NULL, "deleted_at" datetime NULL, "name" varchar(255) NOT NULL, "description" text NOT NULL, "speicherdauer_tage" integer unsigned NULL CHECK ("speicherdauer_tage" >= 0), "dsfa_erforderlich" bool NOT NULL, "dsfa_durchgefuehrt" bool NOT NULL, "next_review" date NULL, "client_content_type_id" integer NULL REFERENCES "django_content_type" ("id") DEFERRABLE INITIALLY DEFERRED, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "deleted_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "mandant_id" bigint NOT NULL REFERENCES "dsb_mandant" ("id") DEFERRABLE INITIALLY DEFERRED, "priority_id" bigint NOT NULL REFERENCES "compliance_priority" ("id") DEFERRABLE INITIALLY DEFERRED, "rechtsgrundlage_id" bigint NOT NULL REFERENCES "dsb_rechtsgrundlage" ("id") DEFERRABLE INITIALLY DEFERRED, "status_id" bigint NOT NULL REFERENCES "compliance_status" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "dsb_verarbeitung_datenkategorien" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "verarbeitung_id" bigint NOT NULL REFERENCES "dsb_verarbeitung" ("id") DEFERRABLE INITIALLY DEFERRED, "datenkategorie_id" bigint NOT NULL REFERENCES "dsb_datenkategorie" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "dsb_vorfall" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "client_id" integer unsigned NULL CHECK ("client_id" >= 0), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "is_active" bool NOT NULL, "deleted_at" datetime NULL, "title" varchar(255) NOT NULL, "description" text NOT NULL, "incident_datetime" datetime NOT NULL, "discovered_datetime" datetime NOT NULL, "incident_type" varchar(100) NOT NULL, "status" varchar(20) NOT NULL, "requires_authority_notification" bool NOT NULL, "authority_notified_at" datetime NULL, "requires_affected_notification" bool NOT NULL, "affected_notified_at" datetime NULL, "immediate_actions" text NOT NULL, "long_term_actions" text NOT NULL, "metadata" text NOT NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "behoerde_meldepflichtig" bool NOT NULL, "behoerde_gemeldet_am" datetime NULL, "client_content_type_id" integer NULL REFERENCES "django_content_type" ("id") DEFERRABLE INITIALLY DEFERRED, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "deleted_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "mandant_id" bigint NOT NULL REFERENCES "dsb_mandant" ("id") DEFERRABLE INITIALLY DEFERRED, "severity_id" bigint NOT NULL REFERENCES "compliance_incident_severity" ("id") DEFERRABLE INITIALLY DEFERRED, "verarbeitung_id" bigint NULL REFERENCES "dsb_verarbeitung" ("id") DEFERRABLE INITIALLY DEFERRED, "vorfall_typ_id" bigint NOT NULL REFERENCES "dsb_vorfall_typ" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "dsb_vorfall_typ" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NULL UNIQUE, "name" varchar(255) NOT NULL, "description" text NOT NULL, "is_active" bool NOT NULL, "sort_order" integer unsigned NOT NULL CHECK ("sort_order" >= 0), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "default_severity_id" bigint NULL REFERENCES "compliance_incident_severity" ("id") DEFERRABLE INITIALLY DEFERRED);UPDATE "main"."sqlite_sequence" SET seq = 7 WHERE name = 'dsb_vorfall_typ';
CREATE TABLE "enrichment_responses" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "action_name" varchar(100) NOT NULL, "target_model" varchar(50) NOT NULL, "target_id" integer NULL, "field_name" varchar(100) NOT NULL, "original_value" text NOT NULL, "suggested_value" text NOT NULL, "edited_value" text NOT NULL, "response_data" text NOT NULL CHECK ((JSON_VALID("response_data") OR "response_data" IS NULL)), "field_mappings" text NOT NULL CHECK ((JSON_VALID("field_mappings") OR "field_mappings" IS NULL)), "confidence" real NOT NULL, "rationale" text NOT NULL, "metadata" text NOT NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "tokens_used" integer NOT NULL, "prompt_tokens" integer NOT NULL, "completion_tokens" integer NOT NULL, "generation_cost" decimal NOT NULL, "execution_time_ms" integer NOT NULL, "quality_score" real NULL, "status" varchar(20) NOT NULL, "applied_at" datetime NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "action_id" bigint NULL REFERENCES "agent_actions" ("id") DEFERRABLE INITIALLY DEFERRED, "agent_id" bigint NULL REFERENCES "bfagent_agents_legacy" ("id") DEFERRABLE INITIALLY DEFERRED, "applied_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "llm_used_id" bigint NULL REFERENCES "llms" ("id") DEFERRABLE INITIALLY DEFERRED, "project_id" bigint NOT NULL REFERENCES "writing_book_projects" ("id") DEFERRABLE INITIALLY DEFERRED, "target_field_id" bigint NULL REFERENCES "field_definitions" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "expert_hub_assessments" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "assessment_number" varchar(50) NOT NULL UNIQUE, "title" varchar(200) NOT NULL, "description" text NOT NULL, "project_id" integer NULL, "status" varchar(50) NOT NULL, "current_phase" varchar(50) NOT NULL, "phase_data" text NOT NULL CHECK ((JSON_VALID("phase_data") OR "phase_data" IS NULL)), "ai_suggestions" text NOT NULL CHECK ((JSON_VALID("ai_suggestions") OR "ai_suggestions" IS NULL)), "ai_confidence_score" real NOT NULL, "ai_enabled" bool NOT NULL, "planned_start" date NULL, "planned_end" date NULL, "actual_start" date NULL, "actual_end" date NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "customer_id" bigint NOT NULL REFERENCES "core_customers" ("id") DEFERRABLE INITIALLY DEFERRED, "domain_art_id" bigint NOT NULL REFERENCES "domain_arts" ("id") DEFERRABLE INITIALLY DEFERRED, "domain_type_id" bigint NOT NULL REFERENCES "domain_types" ("id") DEFERRABLE INITIALLY DEFERRED, "lead_assessor_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "location_id" bigint NULL REFERENCES "core_locations" ("id") DEFERRABLE INITIALLY DEFERRED);UPDATE "main"."sqlite_sequence" SET seq = 1 WHERE name = 'expert_hub_assessments';
CREATE TABLE "expert_hub_assessments_team_members" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "assessment_id" bigint NOT NULL REFERENCES "expert_hub_assessments" ("id") DEFERRABLE INITIALLY DEFERRED, "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "expert_hub_auditlog" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "entity_type" varchar(50) NOT NULL, "entity_id" integer NOT NULL, "action" varchar(50) NOT NULL, "timestamp" datetime NOT NULL, "ip_address" char(39) NULL, "user_agent" varchar(512) NOT NULL, "is_ai_generated" bool NOT NULL, "ai_model" varchar(50) NOT NULL, "ai_confidence" decimal NULL, "human_verified" bool NOT NULL, "verified_at" datetime NULL, "old_values" text NULL CHECK ((JSON_VALID("old_values") OR "old_values" IS NULL)), "new_values" text NULL CHECK ((JSON_VALID("new_values") OR "new_values" IS NULL)), "changed_fields" text NOT NULL CHECK ((JSON_VALID("changed_fields") OR "changed_fields" IS NULL)), "comment" text NOT NULL, "reason" varchar(255) NOT NULL, "workflow_id" integer NULL, "compliance_relevant" bool NOT NULL, "regulation_reference" varchar(255) NOT NULL, "execution_time_ms" integer NULL, "error_occurred" bool NOT NULL, "error_message" text NOT NULL, "session_id" varchar(255) NOT NULL, "request_id" varchar(255) NOT NULL, "user_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "verified_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "document_id" bigint NULL REFERENCES "expert_hub_exschutzdocument" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "expert_hub_building" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(255) NOT NULL, "code" varchar(50) NOT NULL, "address" text NOT NULL, "description" text NOT NULL, "year_of_construction" integer NULL, "floor_count" integer NULL, "total_area_m2" decimal NULL, "is_active" bool NOT NULL, "metadata" text NOT NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "location_id" bigint NOT NULL REFERENCES "core_locations" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "expert_hub_data_source_config" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "source_type" varchar(20) NOT NULL UNIQUE,
    "is_enabled" bool NOT NULL,
    "api_key" varchar(200) NOT NULL,
    "rate_limit" integer NOT NULL,
    "cache_duration" integer NOT NULL,
    "config" text NOT NULL CHECK ((JSON_VALID("config") OR "config" IS NULL)),
    "created_at" datetime NOT NULL,
    "updated_at" datetime NOT NULL
);
CREATE TABLE "expert_hub_data_source_metric" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "source" varchar(20) NOT NULL,
    "success" bool NOT NULL,
    "response_time" real NOT NULL,
    "error_type" varchar(100) NOT NULL,
    "timestamp" datetime NOT NULL
);
CREATE TABLE "expert_hub_document_type" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NOT NULL UNIQUE, "name" varchar(255) NOT NULL, "description" text NOT NULL, "requires_atex_compliance" bool NOT NULL, "icon" varchar(50) NOT NULL, "is_active" bool NOT NULL, "sort_order" integer NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 5 WHERE name = 'expert_hub_document_type';
CREATE TABLE "expert_hub_equipment" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "bezeichnung" varchar(255) NOT NULL, "beschreibung" text NOT NULL, "typ" varchar(100) NOT NULL, "hersteller" varchar(255) NOT NULL, "modell" varchar(100) NOT NULL, "serien_nummer" varchar(100) NOT NULL, "baujahr" integer unsigned NULL CHECK ("baujahr" >= 0), "atex_zertifizierung" varchar(100) NOT NULL, "zertifikat_nummer" varchar(100) NOT NULL, "kennzeichnung_komplett" varchar(255) NOT NULL, "zulaessige_zonen" text NOT NULL CHECK ((JSON_VALID("zulaessige_zonen") OR "zulaessige_zonen" IS NULL)), "eingesetzte_zone" varchar(50) NOT NULL, "standort" varchar(255) NOT NULL, "nennspannung" varchar(50) NOT NULL, "nennleistung" varchar(50) NOT NULL, "nennstrom" varchar(50) NOT NULL, "schutzart" varchar(20) NOT NULL, "umgebungstemperatur_min" integer NULL, "umgebungstemperatur_max" integer NULL, "wartungsintervall" varchar(50) NOT NULL, "naechste_wartung" date NULL, "letzte_wartung" date NULL, "pruefprotokoll_pfad" varchar(500) NOT NULL, "status" varchar(20) NOT NULL, "inbetriebnahme_datum" date NULL, "ausserbetriebnahme_datum" date NULL, "bemerkungen" text NOT NULL, "dokumente_json" text NOT NULL CHECK ((JSON_VALID("dokumente_json") OR "dokumente_json" IS NULL)), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "ersetzt_durch_id" bigint NULL REFERENCES "expert_hub_equipment" ("id") DEFERRABLE INITIALLY DEFERRED, "explosionsgruppe_id" bigint NULL REFERENCES "expert_hub_explosion_group" ("id") DEFERRABLE INITIALLY DEFERRED, "facility_id" bigint NULL REFERENCES "expert_hub_facility" ("id") DEFERRABLE INITIALLY DEFERRED, "geraetekategorie_id" bigint NULL REFERENCES "expert_hub_equipment_category" ("id") DEFERRABLE INITIALLY DEFERRED, "temperaturklasse_id" bigint NULL REFERENCES "expert_hub_temperature_class" ("id") DEFERRABLE INITIALLY DEFERRED, "wartungsverantwortlicher_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "zuendschutzart_id" bigint NULL REFERENCES "expert_hub_ignition_protection_type" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "expert_hub_equipment_category" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(5) NOT NULL UNIQUE, "name_de" varchar(100) NOT NULL, "name_en" varchar(100) NOT NULL, "protection_level" integer NOT NULL, "category_type" varchar(10) NOT NULL, "applicable_zones" text NOT NULL CHECK ((JSON_VALID("applicable_zones") OR "applicable_zones" IS NULL)), "description" text NOT NULL, "requirements" text NOT NULL, "sort_order" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 6 WHERE name = 'expert_hub_equipment_category';
CREATE TABLE "expert_hub_equipment_gutachten" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "equipment_id" bigint NOT NULL REFERENCES "expert_hub_equipment" ("id") DEFERRABLE INITIALLY DEFERRED, "explosionsschutzgutachten_id" bigint NOT NULL REFERENCES "expert_hub_gutachten" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "expert_hub_explosion_group" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(10) NOT NULL UNIQUE, "name_de" varchar(100) NOT NULL, "name_en" varchar(100) NOT NULL, "category" varchar(20) NOT NULL, "description" text NOT NULL, "danger_level" integer NOT NULL, "sort_order" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 6 WHERE name = 'expert_hub_explosion_group';
CREATE TABLE "expert_hub_exschutzdocument" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "project_id" integer NULL, "uuid" char(32) NOT NULL UNIQUE, "document_type_legacy" varchar(50) NOT NULL, "file_name" varchar(255) NOT NULL, "file_path" varchar(512) NOT NULL, "file_size_bytes" integer NULL, "uploaded_at" datetime NOT NULL, "processing_status_legacy" varchar(50) NOT NULL, "processing_started_at" datetime NULL, "processing_completed_at" datetime NULL, "extracted_text" text NOT NULL, "extraction_method" varchar(50) NOT NULL, "page_count" integer NULL, "overall_confidence" decimal NULL, "extraction_quality_score" decimal NULL, "needs_human_review" bool NOT NULL, "review_reason" text NOT NULL, "reviewed_at" datetime NULL, "review_notes" text NOT NULL, "ai_model_used" varchar(50) NOT NULL, "total_ai_tokens" integer NULL, "total_ai_cost" decimal NULL, "workflow_id" integer NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "customer_id" bigint NOT NULL REFERENCES "core_customers" ("id") DEFERRABLE INITIALLY DEFERRED, "document_type_id" bigint NOT NULL REFERENCES "expert_hub_document_type" ("id") DEFERRABLE INITIALLY DEFERRED, "reviewed_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "uploaded_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "processing_status_id" bigint NOT NULL REFERENCES "expert_hub_processing_status_type" ("id") DEFERRABLE INITIALLY DEFERRED);UPDATE "main"."sqlite_sequence" SET seq = 1 WHERE name = 'expert_hub_exschutzdocument';
CREATE TABLE "expert_hub_exzone" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "zone_classification_legacy" varchar(20) NOT NULL, "zone_typ" varchar(20) NOT NULL, "raum_bereich" varchar(255) NOT NULL, "gebaeude_legacy" varchar(255) NOT NULL, "geschoss" varchar(50) NOT NULL, "ausdehnung_beschreibung" text NOT NULL, "flaeche_m2" decimal NULL, "volumen_m3" decimal NULL, "gefahrstoff_ids" text NOT NULL CHECK ((JSON_VALID("gefahrstoff_ids") OR "gefahrstoff_ids" IS NULL)), "explosionsgruppe" varchar(10) NOT NULL, "temperaturklasse" varchar(10) NOT NULL, "haeufigkeit" varchar(100) NOT NULL, "dauer" varchar(100) NOT NULL, "erforderliche_geraetekategorie" varchar(20) NOT NULL, "zuendschutzart" varchar(50) NOT NULL, "lueftung_typ" varchar(100) NOT NULL, "luftwechsel_pro_stunde" decimal NULL, "ai_model" varchar(50) NOT NULL, "confidence" decimal NOT NULL, "needs_review" bool NOT NULL, "reviewed_at" datetime NULL, "approved" bool NOT NULL, "extracted_at" datetime NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "document_id" bigint NOT NULL REFERENCES "expert_hub_exschutzdocument" ("id") DEFERRABLE INITIALLY DEFERRED, "gebaeude_id" bigint NULL REFERENCES "expert_hub_building" ("id") DEFERRABLE INITIALLY DEFERRED, "reviewed_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "hauptgefahrstoff_id" bigint NULL REFERENCES "expert_hub_gefahrstoff" ("id") DEFERRABLE INITIALLY DEFERRED, "zone_classification_id" bigint NOT NULL REFERENCES "expert_hub_zone_type" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "expert_hub_facility" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(255) NOT NULL, "inventory_number" varchar(100) NOT NULL, "description" text NOT NULL, "manufacturer" varchar(255) NOT NULL, "model" varchar(255) NOT NULL, "serial_number" varchar(100) NOT NULL, "year_of_construction" integer NULL, "technical_specs" text NOT NULL CHECK ((JSON_VALID("technical_specs") OR "technical_specs" IS NULL)), "dimensions_outer" text NOT NULL CHECK ((JSON_VALID("dimensions_outer") OR "dimensions_outer" IS NULL)), "dimensions_inner" text NOT NULL CHECK ((JSON_VALID("dimensions_inner") OR "dimensions_inner" IS NULL)), "weight_kg" decimal NULL, "capacity" text NOT NULL CHECK ((JSON_VALID("capacity") OR "capacity" IS NULL)), "atex_marking" varchar(200) NOT NULL, "ce_marked" bool NOT NULL, "ce_certificate_number" varchar(100) NOT NULL, "status" varchar(50) NOT NULL, "commissioned_at" date NULL, "decommissioned_at" date NULL, "last_inspection_at" date NULL, "next_inspection_due" date NULL, "inspection_interval_months" integer NULL, "notes" text NOT NULL, "metadata" text NOT NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "location_id" bigint NOT NULL REFERENCES "core_locations" ("id") DEFERRABLE INITIALLY DEFERRED, "facility_type_id" bigint NOT NULL REFERENCES "expert_hub_facility_type" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "expert_hub_facility_hazmat" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "usage_type" varchar(100) NOT NULL, "max_quantity_liters" decimal NULL, "max_quantity_kg" decimal NULL, "typical_quantity_liters" decimal NULL, "typical_quantity_kg" decimal NULL, "flow_rate" varchar(100) NOT NULL, "aggregate_state" varchar(50) NOT NULL, "temperature_range_min" decimal NULL, "temperature_range_max" decimal NULL, "pressure_range" varchar(100) NOT NULL, "concentration" varchar(100) NOT NULL, "container_type" varchar(100) NOT NULL, "notes" text NOT NULL, "metadata" text NOT NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "facility_id" bigint NOT NULL REFERENCES "expert_hub_facility" ("id") DEFERRABLE INITIALLY DEFERRED, "hazmat_id" bigint NOT NULL REFERENCES "expert_hub_hazmat_catalog" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "expert_hub_facility_type" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(255) NOT NULL UNIQUE, "code" varchar(50) NOT NULL UNIQUE, "category" varchar(100) NOT NULL, "description" text NOT NULL, "typical_hazmats" text NOT NULL, "default_template_id" integer NULL, "metadata" text NOT NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);
CREATE TABLE "expert_hub_gefahrstoff" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "cas_number" varchar(20) NOT NULL, "cas_valid" bool NOT NULL, "cas_confidence" decimal NOT NULL, "stoff_name" varchar(255) NOT NULL, "stoff_name_en" varchar(255) NOT NULL, "stoff_name_confidence" decimal NOT NULL, "h_saetze" text NOT NULL CHECK ((JSON_VALID("h_saetze") OR "h_saetze" IS NULL)), "h_saetze_text" text NOT NULL, "h_saetze_confidence" decimal NOT NULL, "p_saetze" text NOT NULL CHECK ((JSON_VALID("p_saetze") OR "p_saetze" IS NULL)), "p_saetze_text" text NOT NULL, "menge_kg" decimal NULL, "menge_liter" decimal NULL, "menge_einheit" varchar(20) NOT NULL, "menge_confidence" decimal NULL, "explosionsgruppe" varchar(10) NOT NULL, "explosionsgruppe_confidence" decimal NULL, "temperaturklasse" varchar(10) NOT NULL, "zuendtemperatur_celsius" decimal NULL, "aggregatzustand" varchar(50) NOT NULL, "flammpunkt_celsius" decimal NULL, "siedepunkt_celsius" decimal NULL, "lagerklasse" varchar(10) NOT NULL, "wgk" varchar(10) NOT NULL, "ghs_piktogramme" text NOT NULL CHECK ((JSON_VALID("ghs_piktogramme") OR "ghs_piktogramme" IS NULL)), "signalwort" varchar(20) NOT NULL, "ai_model" varchar(50) NOT NULL, "ai_tokens" integer NULL, "ai_cost" decimal NULL, "overall_confidence" decimal NOT NULL, "needs_review" bool NOT NULL, "review_reason" text NOT NULL, "reviewed_at" datetime NULL, "approved" bool NOT NULL, "extracted_at" datetime NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "document_id" bigint NOT NULL REFERENCES "expert_hub_exschutzdocument" ("id") DEFERRABLE INITIALLY DEFERRED, "extracted_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "reviewed_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "expert_hub_gutachten" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "gutachten_nummer" varchar(50) NOT NULL UNIQUE, "titel" varchar(255) NOT NULL, "untertitel" varchar(255) NOT NULL, "version" varchar(10) NOT NULL, "status" varchar(20) NOT NULL, "betriebsstaette_name" varchar(255) NOT NULL, "betriebsstaette_adresse" text NOT NULL, "anlagentyp" varchar(100) NOT NULL, "betriebsbereich" varchar(100) NOT NULL, "erstellt_am" datetime NOT NULL, "geprueft_am" datetime NULL, "freigegeben_am" datetime NULL, "gueltig_ab" date NOT NULL, "gueltig_bis" date NULL, "naechste_ueberpruefung" date NULL, "pruefgegenstand" text NOT NULL, "pruefumfang" text NOT NULL, "pruefgrundlagen" text NOT NULL, "zusammenfassung" text NOT NULL, "atex_konformitaet" bool NOT NULL, "atex_bemerkungen" text NOT NULL, "gesamtrisiko" varchar(20) NOT NULL, "risikomatrix_json" text NOT NULL CHECK ((JSON_VALID("risikomatrix_json") OR "risikomatrix_json" IS NULL)), "empfohlene_massnahmen" text NOT NULL, "nachbesserungen_erforderlich" bool NOT NULL, "nachbesserungen_beschreibung" text NOT NULL, "nachbesserungen_frist" date NULL, "anlagen_beschreibung" text NOT NULL, "externe_referenzen" text NOT NULL CHECK ((JSON_VALID("externe_referenzen") OR "externe_referenzen" IS NULL)), "bemerkungen" text NOT NULL, "aenderungsprotokoll" text NOT NULL CHECK ((JSON_VALID("aenderungsprotokoll") OR "aenderungsprotokoll" IS NULL)), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "assessment_id" bigint NOT NULL UNIQUE REFERENCES "expert_hub_assessments" ("id") DEFERRABLE INITIALLY DEFERRED, "ersteller_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "freigegeben_von_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "geprueft_von_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "expert_hub_gutachten_betroffene_vorschriften" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "explosionsschutzgutachten_id" bigint NOT NULL REFERENCES "expert_hub_gutachten" ("id") DEFERRABLE INITIALLY DEFERRED, "regulation_id" bigint NOT NULL REFERENCES "expert_hub_regulation" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "expert_hub_hazmat_catalog" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "cas_number" varchar(20) NOT NULL UNIQUE, "name" varchar(255) NOT NULL, "name_en" varchar(255) NOT NULL, "synonyms" text NOT NULL CHECK ((JSON_VALID("synonyms") OR "synonyms" IS NULL)), "chemical_formula" varchar(100) NOT NULL, "molecular_weight" decimal NULL, "density_g_cm3" decimal NULL, "melting_point_celsius" decimal NULL, "boiling_point_celsius" decimal NULL, "flash_point_celsius" decimal NULL, "ignition_temperature_celsius" decimal NULL, "vapor_pressure_mbar" decimal NULL, "lel_vol_percent" decimal NULL, "uel_vol_percent" decimal NULL, "mie_mj" decimal NULL, "limiting_oxygen_concentration" decimal NULL, "max_explosion_pressure_bar" decimal NULL, "kst_value" decimal NULL, "explosion_group" varchar(10) NOT NULL, "temperature_class" varchar(10) NOT NULL, "gas_group" varchar(10) NOT NULL, "dust_class" varchar(10) NOT NULL, "ghs_hazard_statements" text NOT NULL CHECK ((JSON_VALID("ghs_hazard_statements") OR "ghs_hazard_statements" IS NULL)), "ghs_precautionary_statements" text NOT NULL CHECK ((JSON_VALID("ghs_precautionary_statements") OR "ghs_precautionary_statements" IS NULL)), "ghs_pictograms" text NOT NULL CHECK ((JSON_VALID("ghs_pictograms") OR "ghs_pictograms" IS NULL)), "signal_word" varchar(20) NOT NULL, "storage_class" varchar(10) NOT NULL, "water_hazard_class" varchar(10) NOT NULL, "physical_state" varchar(50) NOT NULL, "color" varchar(100) NOT NULL, "odor" varchar(100) NOT NULL, "data_source" varchar(255) NOT NULL, "data_verified_at" date NULL, "data_quality_score" decimal NULL, "notes" text NOT NULL, "metadata" text NOT NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);
CREATE TABLE "expert_hub_ignition_protection_type" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(5) NOT NULL UNIQUE, "name_de" varchar(100) NOT NULL, "name_en" varchar(100) NOT NULL, "atex_symbol" varchar(10) NOT NULL, "description" text NOT NULL, "principle" text NOT NULL, "applicable_to" varchar(20) NOT NULL, "sort_order" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 9 WHERE name = 'expert_hub_ignition_protection_type';
CREATE TABLE "expert_hub_physical_state" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(20) NOT NULL UNIQUE, "name_de" varchar(50) NOT NULL, "name_en" varchar(50) NOT NULL, "symbol" varchar(10) NOT NULL, "description" text NOT NULL, "sort_order" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 6 WHERE name = 'expert_hub_physical_state';
CREATE TABLE "expert_hub_processing_status_type" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NOT NULL UNIQUE, "name" varchar(100) NOT NULL, "description" text NOT NULL, "category" varchar(50) NOT NULL, "color" varchar(20) NOT NULL, "icon" varchar(50) NOT NULL, "is_final" bool NOT NULL, "sort_order" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 9 WHERE name = 'expert_hub_processing_status_type';
CREATE TABLE "expert_hub_regulation" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "nummer" varchar(50) NOT NULL, "vollstaendige_bezeichnung" varchar(100) NOT NULL UNIQUE, "titel" varchar(500) NOT NULL, "untertitel" varchar(500) NOT NULL, "ausgabedatum" date NOT NULL, "version" varchar(50) NOT NULL, "status" varchar(20) NOT NULL, "gueltig_ab" date NULL, "gueltig_bis" date NULL, "zusammenfassung" text NOT NULL, "anwendungsbereich" text NOT NULL, "hauptinhalte" text NOT NULL, "volltext" text NOT NULL, "auszuege_json" text NOT NULL CHECK ((JSON_VALID("auszuege_json") OR "auszuege_json" IS NULL)), "relevanz_explosionsschutz" varchar(20) NOT NULL, "explosionsschutz_themen" text NOT NULL CHECK ((JSON_VALID("explosionsschutz_themen") OR "explosionsschutz_themen" IS NULL)), "betroffene_zonen" text NOT NULL CHECK ((JSON_VALID("betroffene_zonen") OR "betroffene_zonen" IS NULL)), "referenzierte_normen" text NOT NULL, "externe_links" text NOT NULL CHECK ((JSON_VALID("externe_links") OR "externe_links" IS NULL)), "quelle_url" varchar(500) NOT NULL, "download_url" varchar(500) NOT NULL, "bezugsquelle" varchar(255) NOT NULL, "kostenpflichtig" bool NOT NULL, "importiert_am" datetime NULL, "import_quelle" varchar(100) NOT NULL, "import_metadaten" text NOT NULL CHECK ((JSON_VALID("import_metadaten") OR "import_metadaten" IS NULL)), "bemerkungen" text NOT NULL, "schlagworte" text NOT NULL CHECK ((JSON_VALID("schlagworte") OR "schlagworte" IS NULL)), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "ersetzt_durch_id" bigint NULL REFERENCES "expert_hub_regulation" ("id") DEFERRABLE INITIALLY DEFERRED, "regulation_type_id" bigint NOT NULL REFERENCES "expert_hub_regulation_type" ("id") DEFERRABLE INITIALLY DEFERRED);UPDATE "main"."sqlite_sequence" SET seq = 8 WHERE name = 'expert_hub_regulation';
CREATE TABLE "expert_hub_regulation_type" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(20) NOT NULL UNIQUE, "name_de" varchar(255) NOT NULL, "name_en" varchar(255) NOT NULL, "abkuerzung" varchar(50) NOT NULL, "beschreibung" text NOT NULL, "herausgeber" varchar(255) NOT NULL, "rechtscharakter" varchar(50) NOT NULL, "farbe" varchar(7) NOT NULL, "icon" varchar(50) NOT NULL, "sort_order" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 8 WHERE name = 'expert_hub_regulation_type';
CREATE TABLE "expert_hub_regulation_verwandte_vorschriften" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "from_regulation_id" bigint NOT NULL REFERENCES "expert_hub_regulation" ("id") DEFERRABLE INITIALLY DEFERRED, "to_regulation_id" bigint NOT NULL REFERENCES "expert_hub_regulation" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "expert_hub_schutzmassnahme" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "massnahme_typ" varchar(50) NOT NULL, "massnahme_kategorie" varchar(100) NOT NULL, "beschreibung" text NOT NULL, "kurzbeschreibung" varchar(255) NOT NULL, "atex_kategorie" varchar(20) NOT NULL, "atex_geraetegruppe" varchar(20) NOT NULL, "zone_ids" text NOT NULL CHECK ((JSON_VALID("zone_ids") OR "zone_ids" IS NULL)), "gefahrstoff_ids" text NOT NULL CHECK ((JSON_VALID("gefahrstoff_ids") OR "gefahrstoff_ids" IS NULL)), "hersteller" varchar(255) NOT NULL, "produkt_bezeichnung" varchar(255) NOT NULL, "zertifizierung" varchar(255) NOT NULL, "status" varchar(50) NOT NULL, "umsetzungsdatum" date NULL, "pruefintervall_monate" integer NULL, "naechste_pruefung" date NULL, "erfuellt_betrsichv" bool NOT NULL, "erfuellt_trbs" bool NOT NULL, "erfuellt_atex" bool NOT NULL, "compliance_confidence" decimal NULL, "wirksamkeit_bewertet" bool NOT NULL, "wirksamkeit_stufe" varchar(50) NOT NULL, "wirksamkeit_bemerkung" text NOT NULL, "kosten_einmalig_euro" decimal NULL, "kosten_jaehrlich_euro" decimal NULL, "verantwortlicher" varchar(255) NOT NULL, "durchfuehrende_firma" varchar(255) NOT NULL, "ai_model" varchar(50) NOT NULL, "confidence" decimal NOT NULL, "needs_review" bool NOT NULL, "reviewed_at" datetime NULL, "approved" bool NOT NULL, "extracted_at" datetime NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "document_id" bigint NOT NULL REFERENCES "expert_hub_exschutzdocument" ("id") DEFERRABLE INITIALLY DEFERRED, "reviewed_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "expert_hub_substance_data_import" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "substance_name" varchar(255) NOT NULL,
    "cas_number" varchar(20) NOT NULL,
    "source_type" varchar(20) NOT NULL,
    "imported_data" text NOT NULL CHECK ((JSON_VALID("imported_data") OR "imported_data" IS NULL)),
    "imported_at" datetime NOT NULL,
    "source_url" varchar(200) NOT NULL,
    "confidence_score" real NOT NULL,
    "success" bool NOT NULL,
    "error_message" text NOT NULL,
    "response_time" real NULL,
    "imported_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED
);UPDATE "main"."sqlite_sequence" SET seq = 4 WHERE name = 'expert_hub_substance_data_import';
CREATE TABLE "expert_hub_temperature_class" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(5) NOT NULL UNIQUE, "max_surface_temp_celsius" integer NOT NULL, "min_ignition_temp_celsius" integer NOT NULL, "name_de" varchar(100) NOT NULL, "name_en" varchar(100) NOT NULL, "color_code" varchar(7) NOT NULL, "description" text NOT NULL, "sort_order" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 6 WHERE name = 'expert_hub_temperature_class';
CREATE TABLE "expert_hub_zone_type" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(20) NOT NULL UNIQUE, "name" varchar(100) NOT NULL, "zone_number" integer NOT NULL, "category" varchar(20) NOT NULL, "frequency" varchar(50) NOT NULL, "description" text NOT NULL, "is_active" bool NOT NULL, "sort_order" integer NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 6 WHERE name = 'expert_hub_zone_type';
CREATE TABLE "field_definitions" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(100) NOT NULL UNIQUE, "display_name" varchar(200) NOT NULL, "description" text NOT NULL, "field_type" varchar(50) NOT NULL, "target_model" varchar(50) NOT NULL, "validation_rules" text NOT NULL CHECK ((JSON_VALID("validation_rules") OR "validation_rules" IS NULL)), "is_ai_enrichable" bool NOT NULL, "ai_prompt_template" text NOT NULL, "placeholder" varchar(200) NOT NULL, "help_text" text NOT NULL, "order" integer NOT NULL, "is_active" bool NOT NULL, "is_required" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "group_id" bigint NULL REFERENCES "field_groups" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "field_groups" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(100) NOT NULL UNIQUE, "display_name" varchar(200) NOT NULL, "description" text NOT NULL, "icon" varchar(50) NOT NULL, "color" varchar(20) NOT NULL, "order" integer NOT NULL, "is_active" bool NOT NULL);
CREATE TABLE "field_templates" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(100) NOT NULL UNIQUE, "display_name" varchar(200) NOT NULL, "description" text NOT NULL, "icon" varchar(50) NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL);
CREATE TABLE "field_value_history" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "old_value" text NOT NULL, "new_value" text NOT NULL, "changed_at" datetime NOT NULL, "change_source" varchar(50) NOT NULL, "changed_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "field_value_id" bigint NOT NULL REFERENCES "project_field_values" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "genagent_actions" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(100) NOT NULL, "description" text NOT NULL, "handler_class" varchar(200) NOT NULL, "order" integer NOT NULL, "is_active" bool NOT NULL, "config" text NOT NULL CHECK ((JSON_VALID("config") OR "config" IS NULL)), "timeout_seconds" integer NULL, "retry_count" integer NOT NULL, "continue_on_error" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "phase_id" bigint NOT NULL REFERENCES "genagent_phases" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "genagent_custom_domains" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "domain_id" varchar(100) NOT NULL UNIQUE, "name" varchar(200) NOT NULL, "description" text NOT NULL, "category" varchar(50) NOT NULL, "icon" varchar(50) NOT NULL, "color" varchar(7) NOT NULL, "phases_config" text NOT NULL CHECK ((JSON_VALID("phases_config") OR "phases_config" IS NULL)), "required_fields" text NOT NULL CHECK ((JSON_VALID("required_fields") OR "required_fields" IS NULL)), "optional_fields" text NOT NULL CHECK ((JSON_VALID("optional_fields") OR "optional_fields" IS NULL)), "author" varchar(200) NOT NULL, "version" varchar(20) NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);
CREATE TABLE "genagent_execution_logs" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "status" varchar(20) NOT NULL, "started_at" datetime NULL, "finished_at" datetime NULL, "duration_seconds" real NULL, "input_data" text NOT NULL CHECK ((JSON_VALID("input_data") OR "input_data" IS NULL)), "output_data" text NOT NULL CHECK ((JSON_VALID("output_data") OR "output_data" IS NULL)), "error_message" text NOT NULL, "created_at" datetime NOT NULL, "action_id" bigint NOT NULL REFERENCES "genagent_actions" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "genagent_phases" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(100) NOT NULL, "description" text NOT NULL, "order" integer NOT NULL, "is_active" bool NOT NULL, "color" varchar(7) NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);
CREATE TABLE "generated_images" ("image_id" char(32) NOT NULL PRIMARY KEY, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "prompt" text NOT NULL, "revised_prompt" text NOT NULL, "negative_prompt" text NOT NULL, "provider" varchar(50) NOT NULL, "model" varchar(100) NOT NULL, "image_file" varchar(100) NOT NULL, "thumbnail" varchar(100) NULL, "original_url" varchar(1000) NOT NULL, "size" varchar(50) NOT NULL, "quality" varchar(20) NOT NULL, "style" varchar(100) NOT NULL, "width" integer NULL, "height" integer NULL, "file_size_bytes" bigint NULL, "cost_cents" decimal NOT NULL, "generation_time_seconds" real NOT NULL, "book_id" integer NULL, "chapter_id" integer NULL, "scene_number" integer NULL, "scene_description" text NOT NULL, "is_active" bool NOT NULL, "is_favorite" bool NOT NULL, "tags" text NOT NULL CHECK ((JSON_VALID("tags") OR "tags" IS NULL)), "notes" text NOT NULL, "generation_metadata" text NOT NULL CHECK ((JSON_VALID("generation_metadata") OR "generation_metadata" IS NULL)), "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "handler_id" bigint NULL REFERENCES "handlers" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "genres" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(100) NOT NULL, "slug" varchar(100) NOT NULL, "description" text NOT NULL, "icon" varchar(50) NOT NULL, "color" varchar(20) NOT NULL, "is_active" bool NOT NULL, "sort_order" integer NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "domain_art_id" bigint NULL REFERENCES "domain_arts" ("id") DEFERRABLE INITIALLY DEFERRED, "parent_genre_id" bigint NULL REFERENCES "genres" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "graphql_field_usage" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "type_name" varchar(100) NOT NULL, "field_name" varchar(100) NOT NULL, "model_name" varchar(100) NULL, "usage_count" bigint NOT NULL, "last_used" datetime NOT NULL, "avg_resolve_time_ms" real NOT NULL, "error_count" integer NOT NULL, "is_deprecated" bool NOT NULL, "deprecation_reason" text NULL, "suggested_alternative" varchar(255) NULL);
CREATE TABLE "graphql_operations" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "operation_hash" varchar(64) NOT NULL, "operation_name" varchar(255) NULL, "operation_type" varchar(20) NOT NULL, "query_string" text NOT NULL, "execution_count" bigint NOT NULL, "total_duration_ms" real NOT NULL, "avg_duration_ms" real NOT NULL, "min_duration_ms" real NULL, "max_duration_ms" real NULL, "first_seen" datetime NOT NULL, "last_used" datetime NOT NULL, "complexity_score" integer NOT NULL, "depth" integer NOT NULL, "field_count" integer NOT NULL, "htmx_request" bool NOT NULL, "htmx_target" varchar(100) NULL);
CREATE TABLE "graphql_performance_logs" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "timestamp" datetime NOT NULL, "duration_ms" real NOT NULL, "db_queries" integer NOT NULL, "db_time_ms" real NOT NULL, "ip_address" char(39) NULL, "user_agent" varchar(255) NULL, "has_errors" bool NOT NULL, "error_message" text NULL, "operation_id" bigint NOT NULL REFERENCES "graphql_operations" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "handler_executions" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "started_at" datetime NOT NULL, "completed_at" datetime NULL, "status" varchar(20) NOT NULL, "input_data" text NOT NULL CHECK ((JSON_VALID("input_data") OR "input_data" IS NULL)), "output_data" text NULL CHECK ((JSON_VALID("output_data") OR "output_data" IS NULL)), "error_message" text NULL, "error_traceback" text NULL, "retry_attempt" integer NOT NULL, "execution_time_ms" integer NULL, "tokens_used" integer NOT NULL, "cost" decimal NOT NULL, "execution_context" text NOT NULL CHECK ((JSON_VALID("execution_context") OR "execution_context" IS NULL)), "action_handler_id" bigint NOT NULL REFERENCES "action_handlers" ("id") DEFERRABLE INITIALLY DEFERRED, "executed_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "llm_used_id" bigint NULL REFERENCES "llms" ("id") DEFERRABLE INITIALLY DEFERRED, "project_id" bigint NOT NULL REFERENCES "writing_book_projects" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "ideas_v2" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "title" varchar(200) NOT NULL, "concept" text NOT NULL, "notes" text NOT NULL, "tags" text NOT NULL CHECK ((JSON_VALID("tags") OR "tags" IS NULL)), "status" varchar(20) NOT NULL, "ai_expansions" text NOT NULL CHECK ((JSON_VALID("ai_expansions") OR "ai_expansions" IS NULL)), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "created_by_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "ideas_v2_books" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "idea_id" bigint NOT NULL REFERENCES "ideas_v2" ("id") DEFERRABLE INITIALLY DEFERRED, "bookproject_id" bigint NOT NULL REFERENCES "writing_book_projects" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "illustration_styles" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(100) NOT NULL UNIQUE, "description" text NOT NULL, "is_active" bool NOT NULL, "sort_order" integer NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);
CREATE TABLE "llm_prompt_executions" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "started_at" datetime NOT NULL, "completed_at" datetime NULL, "status" varchar(20) NOT NULL, "variables" text NOT NULL CHECK ((JSON_VALID("variables") OR "variables" IS NULL)), "rendered_prompt" text NOT NULL, "response" text NULL, "input_tokens" integer NOT NULL, "output_tokens" integer NOT NULL, "cost" decimal NOT NULL, "duration_ms" integer NULL, "quality_score" real NULL, "quality_notes" text NOT NULL, "error_message" text NULL, "error_traceback" text NULL, "execution_context" text NOT NULL CHECK ((JSON_VALID("execution_context") OR "execution_context" IS NULL)), "executed_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "llm_id" bigint NULL REFERENCES "llms" ("id") DEFERRABLE INITIALLY DEFERRED, "prompt_id" bigint NOT NULL REFERENCES "llm_prompt_templates" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "llm_prompt_templates" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "prompt_id" varchar(100) NOT NULL UNIQUE, "name" varchar(200) NOT NULL, "description" text NOT NULL, "category" varchar(50) NOT NULL, "prompt_type" varchar(20) NOT NULL, "template" text NOT NULL, "required_variables" text NOT NULL CHECK ((JSON_VALID("required_variables") OR "required_variables" IS NULL)), "variable_schema" text NOT NULL CHECK ((JSON_VALID("variable_schema") OR "variable_schema" IS NULL)), "example_variables" text NOT NULL CHECK ((JSON_VALID("example_variables") OR "example_variables" IS NULL)), "version" varchar(20) NOT NULL, "is_active" bool NOT NULL, "is_deprecated" bool NOT NULL, "variant" varchar(20) NOT NULL, "traffic_weight" integer NOT NULL, "recommended_model" varchar(100) NOT NULL, "max_tokens" integer NULL, "temperature" real NULL, "top_p" real NULL, "avg_input_tokens" integer NOT NULL, "avg_output_tokens" integer NOT NULL, "avg_cost" decimal NOT NULL, "total_uses" integer NOT NULL, "success_rate" real NOT NULL, "avg_quality_score" real NOT NULL, "total_ratings" integer NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "documentation_url" varchar(200) NOT NULL, "notes" text NOT NULL, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "replacement_prompt_id" bigint NULL REFERENCES "llm_prompt_templates" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "llms" (
  "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
  "name" varchar(100) NOT NULL,
  "provider" varchar(12) NOT NULL,
  "llm_name" varchar(100) NOT NULL,
  "api_key" text NOT NULL,
  "api_endpoint" text NOT NULL,
  "max_tokens" integer NOT NULL,
  "temperature" real NOT NULL,
  "top_p" real NOT NULL,
  "frequency_penalty" real NOT NULL,
  "presence_penalty" real NOT NULL,
  "total_tokens_used" integer NOT NULL,
  "total_requests" integer NOT NULL,
  "total_cost" real NOT NULL,
  "cost_per_1k_tokens" real NOT NULL,
  "description" text,
  "is_active" bool NOT NULL,
  "created_at" datetime NOT NULL,
  "updated_at" datetime NOT NULL
);UPDATE "main"."sqlite_sequence" SET seq = 10 WHERE name = 'llms';
CREATE TABLE "locations" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(200) NOT NULL, "location_type" varchar(100) NULL, "description" text NULL, "atmosphere" varchar(200) NULL, "importance" varchar(50) NOT NULL, "notes" text NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "world_id" bigint NOT NULL REFERENCES "world_settings" ("id") DEFERRABLE INITIALLY DEFERRED, "parent_location_id" bigint NULL REFERENCES "locations" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "medtrans_customers" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "customer_id" varchar(100) NOT NULL UNIQUE, "customer_name" varchar(200) NOT NULL, "dashboard_access" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "medtrans_presentation_texts" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "slide_number" integer NOT NULL, "text_id" varchar(100) NOT NULL, "original_text" text NOT NULL, "translated_text" text NOT NULL, "translation_method" varchar(20) NOT NULL, "manually_edited" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "presentation_id" bigint NOT NULL REFERENCES "medtrans_presentations" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "medtrans_presentations" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "pptx_file" varchar(100) NOT NULL, "source_language" varchar(10) NOT NULL, "target_language" varchar(10) NOT NULL, "status" varchar(20) NOT NULL, "total_texts" integer NOT NULL, "translated_texts" integer NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "customer_id" bigint NOT NULL REFERENCES "medtrans_customers" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "navigation_items" (
  "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
  "section_id" bigint NOT NULL,
  "code" varchar(50) NOT NULL,
  "name" varchar(100) NOT NULL,
  "description" text NOT NULL,
  "item_type" varchar(20) NOT NULL,
  "url_name" varchar(100) NOT NULL,
  "url_params" text NOT NULL,
  "external_url" varchar(200) NOT NULL,
  "icon" varchar(50) NOT NULL,
  "badge_text" varchar(20) NOT NULL,
  "badge_color" varchar(20) NOT NULL,
  "order" integer NOT NULL,
  "is_active" bool NOT NULL,
  "opens_in_new_tab" bool NOT NULL,
  "parent_id" bigint,
  "created_at" datetime NOT NULL,
  "updated_at" datetime NOT NULL,
  FOREIGN KEY ("section_id") REFERENCES "navigation_sections" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("parent_id") REFERENCES "navigation_items" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE INITIALLY DEFERRED
);UPDATE "main"."sqlite_sequence" SET seq = 106 WHERE name = 'navigation_items';
CREATE TABLE "navigation_items_domains" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "navigationitem_id" bigint NOT NULL REFERENCES "navigation_items" ("id") DEFERRABLE INITIALLY DEFERRED, "workflowdomain_id" bigint NOT NULL REFERENCES "workflow_domains" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "navigation_items_required_groups" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "navigationitem_id" bigint NOT NULL REFERENCES "navigation_items" ("id") DEFERRABLE INITIALLY DEFERRED, "group_id" integer NOT NULL REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "navigation_items_required_permissions" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "navigationitem_id" bigint NOT NULL REFERENCES "navigation_items" ("id") DEFERRABLE INITIALLY DEFERRED, "permission_id" integer NOT NULL REFERENCES "auth_permission" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "navigation_sections" (
  "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
  "code" varchar(50) NOT NULL,
  "name" varchar(100) NOT NULL,
  "description" text NOT NULL,
  "icon" varchar(50) NOT NULL,
  "color" varchar(20) NOT NULL,
  "order" integer NOT NULL,
  "is_active" bool NOT NULL,
  "is_collapsible" bool NOT NULL,
  "is_collapsed_default" bool NOT NULL,
  "created_at" datetime NOT NULL,
  "updated_at" datetime NOT NULL,
  "domain_id" INTEGER,
  "slug" VARCHAR(50),
  FOREIGN KEY ("domain_id") REFERENCES "domain_arts" ("id") ON DELETE CASCADE ON UPDATE NO ACTION,
  UNIQUE ("code" ASC)
);UPDATE "main"."sqlite_sequence" SET seq = 29 WHERE name = 'navigation_sections';
CREATE TABLE "navigation_sections_domains" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "navigationsection_id" bigint NOT NULL REFERENCES "navigation_sections" ("id") DEFERRABLE INITIALLY DEFERRED, "workflowdomain_id" bigint NOT NULL REFERENCES "workflow_domains" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "navigation_sections_required_groups" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "navigationsection_id" bigint NOT NULL REFERENCES "navigation_sections" ("id") DEFERRABLE INITIALLY DEFERRED, "group_id" integer NOT NULL REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "navigation_sections_required_permissions" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "navigationsection_id" bigint NOT NULL REFERENCES "navigation_sections" ("id") DEFERRABLE INITIALLY DEFERRED, "permission_id" integer NOT NULL REFERENCES "auth_permission" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "phase_action_configs" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_required" bool NOT NULL, "order" integer NOT NULL, "description" text NOT NULL, "action_id" bigint NOT NULL REFERENCES "agent_actions" ("id") DEFERRABLE INITIALLY DEFERRED, "phase_id" bigint NOT NULL REFERENCES "workflow_phases" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "phase_agent_configs" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_required" bool NOT NULL, "order" integer NOT NULL, "description" text NOT NULL, "agent_id" bigint NOT NULL REFERENCES "bfagent_agents_legacy" ("id") DEFERRABLE INITIALLY DEFERRED, "phase_id" bigint NOT NULL REFERENCES "workflow_phases" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "presentation_studio_design_profile" ("id" char(32) NOT NULL PRIMARY KEY, "profile_name" varchar(100) NOT NULL, "source_type" varchar(50) NOT NULL, "colors" text NOT NULL CHECK ((JSON_VALID("colors") OR "colors" IS NULL)), "fonts" text NOT NULL CHECK ((JSON_VALID("fonts") OR "fonts" IS NULL)), "is_system_template" bool NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "presentation_id" char(32) NULL REFERENCES "presentation_studio_presentation" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "presentation_studio_enhancement" ("id" char(32) NOT NULL PRIMARY KEY, "enhancement_type" varchar(50) NOT NULL, "enhancement_mode" varchar(20) NOT NULL, "concepts" text NOT NULL CHECK ((JSON_VALID("concepts") OR "concepts" IS NULL)), "configuration" text NOT NULL CHECK ((JSON_VALID("configuration") OR "configuration" IS NULL)), "slides_before" integer NOT NULL, "slides_after" integer NOT NULL, "success" bool NOT NULL, "error_message" text NOT NULL, "result_data" text NOT NULL CHECK ((JSON_VALID("result_data") OR "result_data" IS NULL)), "executed_at" datetime NOT NULL, "duration_seconds" real NULL, "executed_by_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "presentation_id" char(32) NOT NULL REFERENCES "presentation_studio_presentation" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "presentation_studio_presentation" ("id" char(32) NOT NULL PRIMARY KEY, "title" varchar(200) NOT NULL, "description" text NOT NULL, "original_file" varchar(100) NOT NULL, "enhanced_file" varchar(100) NULL, "uploaded_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "enhancement_status" varchar(20) NOT NULL, "slide_count_original" integer NOT NULL, "slide_count_enhanced" integer NOT NULL, "concepts_added" text NOT NULL CHECK ((JSON_VALID("concepts_added") OR "concepts_added" IS NULL)), "enhancement_metadata" text NOT NULL CHECK ((JSON_VALID("enhancement_metadata") OR "enhancement_metadata" IS NULL)), "slide_templates" text NOT NULL CHECK ((JSON_VALID("slide_templates") OR "slide_templates" IS NULL)), "uploaded_by_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "template_collection_id" char(32) NULL REFERENCES "presentation_studio_template_collection" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "presentation_studio_preview_slide" ("id" char(32) NOT NULL PRIMARY KEY, "preview_order" integer NOT NULL, "title" varchar(500) NOT NULL, "content_data" text NOT NULL CHECK ((JSON_VALID("content_data") OR "content_data" IS NULL)), "status" varchar(20) NOT NULL, "source_type" varchar(50) NOT NULL, "source_file_name" varchar(255) NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "converted_at" datetime NULL, "pptx_slide_number" integer NULL, "presentation_id" char(32) NOT NULL REFERENCES "presentation_studio_presentation" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "presentation_studio_template_collection" ("id" char(32) NOT NULL PRIMARY KEY, "name" varchar(200) NOT NULL, "description" text NOT NULL, "client" varchar(200) NOT NULL, "project" varchar(200) NOT NULL, "industry" varchar(100) NOT NULL, "templates" text NOT NULL CHECK ((JSON_VALID("templates") OR "templates" IS NULL)), "master_pptx" varchar(100) NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "is_active" bool NOT NULL, "is_default" bool NOT NULL, "is_system" bool NOT NULL, "usage_count" integer NOT NULL, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "project_field_values" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "value_text" text NOT NULL, "value_json" text NULL CHECK ((JSON_VALID("value_json") OR "value_json" IS NULL)), "value_number" real NULL, "value_date" date NULL, "value_bool" bool NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "version" integer NOT NULL, "field_definition_id" bigint NOT NULL REFERENCES "field_definitions" ("id") DEFERRABLE INITIALLY DEFERRED, "project_id" bigint NOT NULL REFERENCES "writing_book_projects" ("id") DEFERRABLE INITIALLY DEFERRED, "updated_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "project_phase_actions" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "projektart" varchar(50) NOT NULL, "projekttyp" varchar(100) NOT NULL, "is_required" bool NOT NULL, "order" integer NOT NULL, "description" text NOT NULL, "context_variables" text NOT NULL CHECK ((JSON_VALID("context_variables") OR "context_variables" IS NULL)), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "action_id" bigint NOT NULL REFERENCES "agent_actions" ("id") DEFERRABLE INITIALLY DEFERRED, "projektphase_id" bigint NOT NULL REFERENCES "workflow_phases" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "project_phase_history" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "entered_at" datetime NOT NULL, "exited_at" datetime NULL, "entered_by" varchar(100) NOT NULL, "notes" text NOT NULL, "actions_completed" text NOT NULL CHECK ((JSON_VALID("actions_completed") OR "actions_completed" IS NULL)), "requirements_met" bool NOT NULL, "project_id" bigint NOT NULL REFERENCES "writing_book_projects" ("id") DEFERRABLE INITIALLY DEFERRED, "phase_id" bigint NOT NULL REFERENCES "workflow_phases" ("id") DEFERRABLE INITIALLY DEFERRED, "workflow_step_id" bigint NOT NULL REFERENCES "workflow_phase_steps" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "project_type_phases" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "projektart" varchar(50) NOT NULL, "projekttyp" varchar(100) NOT NULL, "order" integer NOT NULL, "is_required" bool NOT NULL, "estimated_days" integer NULL, "description_override" text NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "projektphase_id" bigint NOT NULL REFERENCES "workflow_phases" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "project_types" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "domain_id" INTEGER NOT NULL,
  "code" VARCHAR(100) NOT NULL,
  "name" VARCHAR(150) NOT NULL,
  "description" TEXT NOT NULL,
  "characteristics" TEXT NOT NULL DEFAULT '',
  "typical_duration_days" INTEGER,
  "complexity_level" VARCHAR(20) NOT NULL DEFAULT 'moderate',
  "industry_standards" TEXT NOT NULL DEFAULT '',
  "common_deliverables" TEXT NOT NULL DEFAULT '',
  "stakeholder_types" TEXT NOT NULL DEFAULT '',
  "phase_generation_hints" TEXT NOT NULL DEFAULT '',
  "is_active" BOOLEAN NOT NULL DEFAULT 1,
  "created_by_id" INTEGER,
  "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updated_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "usage_count" INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY ("domain_id") REFERENCES "workflow_domains" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION,
  UNIQUE ("domain_id" ASC, "code" ASC)
);UPDATE "main"."sqlite_sequence" SET seq = 14 WHERE name = 'project_types';
CREATE TABLE "prompt_executions" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "target_model" varchar(50) NOT NULL, "target_id" integer NOT NULL, "rendered_prompt" text NOT NULL, "context_used" text NOT NULL CHECK ((JSON_VALID("context_used") OR "context_used" IS NULL)), "llm_response" text NOT NULL, "parsed_output" text NULL CHECK ((JSON_VALID("parsed_output") OR "parsed_output" IS NULL)), "confidence_score" real NULL, "user_accepted" bool NULL, "user_edited" bool NOT NULL, "user_rating" integer NULL, "user_feedback" text NOT NULL, "context_completeness_score" real NOT NULL, "missing_variables" text NOT NULL CHECK ((JSON_VALID("missing_variables") OR "missing_variables" IS NULL)), "execution_time" real NOT NULL, "tokens_used" integer NULL, "cost" decimal NULL, "status" varchar(20) NOT NULL, "error_message" text NOT NULL, "error_type" varchar(100) NOT NULL, "retry_count" integer NOT NULL, "created_at" datetime NOT NULL, "agent_id" bigint NULL REFERENCES "bfagent_agents_legacy" ("id") DEFERRABLE INITIALLY DEFERRED, "project_id" bigint NOT NULL REFERENCES "writing_book_projects" ("id") DEFERRABLE INITIALLY DEFERRED, "template_id" bigint NOT NULL REFERENCES "core_prompt_templates" ("id") DEFERRABLE INITIALLY DEFERRED, "retry_of_id" bigint NULL REFERENCES "prompt_executions" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "prompt_template_tests" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(200) NOT NULL, "description" text NOT NULL, "test_context" text NOT NULL CHECK ((JSON_VALID("test_context") OR "test_context" IS NULL)), "expected_output_contains" text NOT NULL CHECK ((JSON_VALID("expected_output_contains") OR "expected_output_contains" IS NULL)), "expected_output_not_contains" text NOT NULL CHECK ((JSON_VALID("expected_output_not_contains") OR "expected_output_not_contains" IS NULL)), "expected_min_length" integer NULL, "expected_max_length" integer NULL, "last_run_at" datetime NULL, "last_run_passed" bool NULL, "last_run_output" text NOT NULL, "last_run_error" text NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "template_id" bigint NOT NULL REFERENCES "core_prompt_templates" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "prompt_templates_legacy" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(200) NOT NULL, "description" text NOT NULL, "template_text" text NOT NULL, "usage_count" integer NOT NULL, "avg_quality_score" real NOT NULL, "version" integer NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "agent_id" bigint NOT NULL REFERENCES "agents" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "research_citation_style_lookup" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NOT NULL UNIQUE, "name_de" varchar(200) NOT NULL, "name_en" varchar(200) NOT NULL, "description" text NOT NULL, "sort_order" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "format_template" text NOT NULL, "example" text NOT NULL, "use_footnotes" bool NOT NULL, "use_bibliography" bool NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 3 WHERE name = 'research_citation_style_lookup';
CREATE TABLE "research_depth_lookup" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NOT NULL UNIQUE, "name_de" varchar(200) NOT NULL, "name_en" varchar(200) NOT NULL, "description" text NOT NULL, "sort_order" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "max_sources" integer NOT NULL, "max_iterations" integer NOT NULL, "timeout_seconds" integer NOT NULL, "quality_threshold" real NOT NULL, "enable_synthesis" bool NOT NULL, "enable_fact_check" bool NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 4 WHERE name = 'research_depth_lookup';
CREATE TABLE "research_focus_lookup" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NOT NULL UNIQUE, "name_de" varchar(200) NOT NULL, "name_en" varchar(200) NOT NULL, "description" text NOT NULL, "sort_order" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "domain" varchar(100) NOT NULL, "recommended_sources" text NOT NULL CHECK ((JSON_VALID("recommended_sources") OR "recommended_sources" IS NULL)), "required_fields" text NOT NULL CHECK ((JSON_VALID("required_fields") OR "required_fields" IS NULL)));UPDATE "main"."sqlite_sequence" SET seq = 3 WHERE name = 'research_focus_lookup';
CREATE TABLE "research_handler_type_lookup" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NOT NULL UNIQUE, "name_de" varchar(200) NOT NULL, "name_en" varchar(200) NOT NULL, "description" text NOT NULL, "sort_order" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "handler_class" varchar(200) NOT NULL, "handler_version" varchar(20) NOT NULL, "is_async" bool NOT NULL, "requires_api_keys" text NOT NULL CHECK ((JSON_VALID("requires_api_keys") OR "requires_api_keys" IS NULL)), "default_timeout" integer NOT NULL, "cache_ttl_seconds" integer NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 3 WHERE name = 'research_handler_type_lookup';
CREATE TABLE "research_researchhandlerexecution" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "handler_version" varchar(20) NOT NULL, "status" varchar(20) NOT NULL, "started_at" datetime NOT NULL, "completed_at" datetime NULL, "execution_time_ms" integer NULL, "input_data" text NOT NULL CHECK ((JSON_VALID("input_data") OR "input_data" IS NULL)), "output_data" text NOT NULL CHECK ((JSON_VALID("output_data") OR "output_data" IS NULL)), "error_message" text NOT NULL, "error_traceback" text NOT NULL, "prompt_tokens" integer NOT NULL, "completion_tokens" integer NOT NULL, "total_tokens" integer NOT NULL, "cache_hit" bool NOT NULL, "handler_type_id" bigint NOT NULL REFERENCES "research_handler_type_lookup" ("id") DEFERRABLE INITIALLY DEFERRED, "session_id" bigint NOT NULL REFERENCES "research_researchsession" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "research_researchproject" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(200) NOT NULL, "description" text NOT NULL, "status" varchar(20) NOT NULL, "default_sources" text NOT NULL CHECK ((JSON_VALID("default_sources") OR "default_sources" IS NULL)), "knowledge_base_ids" text NOT NULL CHECK ((JSON_VALID("knowledge_base_ids") OR "knowledge_base_ids" IS NULL)), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "default_depth_id" bigint NULL REFERENCES "research_depth_lookup" ("id") DEFERRABLE INITIALLY DEFERRED, "owner_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);UPDATE "main"."sqlite_sequence" SET seq = 5 WHERE name = 'research_researchproject';
CREATE TABLE "research_researchresult" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "synthesis" text NOT NULL, "key_findings" text NOT NULL CHECK ((JSON_VALID("key_findings") OR "key_findings" IS NULL)), "source_agreement" varchar(20) NOT NULL, "agreement_score" real NOT NULL, "gaps_identified" text NOT NULL CHECK ((JSON_VALID("gaps_identified") OR "gaps_identified" IS NULL)), "contradictions" text NOT NULL CHECK ((JSON_VALID("contradictions") OR "contradictions" IS NULL)), "citations" text NOT NULL CHECK ((JSON_VALID("citations") OR "citations" IS NULL)), "report_content" text NOT NULL, "report_format" varchar(20) NOT NULL, "word_count" integer NOT NULL, "sources_used" integer NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "citation_style_id" bigint NULL REFERENCES "research_citation_style_lookup" ("id") DEFERRABLE INITIALLY DEFERRED, "session_id" bigint NOT NULL UNIQUE REFERENCES "research_researchsession" ("id") DEFERRABLE INITIALLY DEFERRED, "synthesis_type_id" bigint NULL REFERENCES "research_synthesis_type_lookup" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "research_researchsession" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "query" text NOT NULL, "optimized_query" text NOT NULL, "sources" text NOT NULL CHECK ((JSON_VALID("sources") OR "sources" IS NULL)), "language" varchar(10) NOT NULL, "status" varchar(20) NOT NULL, "started_at" datetime NULL, "completed_at" datetime NULL, "execution_time_ms" integer NULL, "iteration_count" integer NOT NULL, "max_iterations" integer NOT NULL, "quality_score" real NULL, "quality_threshold" real NOT NULL, "error_message" text NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "depth_id" bigint NOT NULL REFERENCES "research_depth_lookup" ("id") DEFERRABLE INITIALLY DEFERRED, "project_id" bigint NOT NULL REFERENCES "research_researchproject" ("id") DEFERRABLE INITIALLY DEFERRED);UPDATE "main"."sqlite_sequence" SET seq = 5 WHERE name = 'research_researchsession';
CREATE TABLE "research_researchsource" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "url" varchar(2000) NOT NULL, "title" varchar(500) NOT NULL, "domain" varchar(200) NOT NULL, "snippet" text NOT NULL, "full_content" text NOT NULL, "source_provider" varchar(50) NOT NULL, "published_date" date NULL, "author" varchar(200) NOT NULL, "relevance_score" real NOT NULL, "credibility_score" real NOT NULL, "used_in_synthesis" bool NOT NULL, "citation_count" integer NOT NULL, "retrieved_at" datetime NOT NULL, "session_id" bigint NOT NULL REFERENCES "research_researchsession" ("id") DEFERRABLE INITIALLY DEFERRED, "source_type_id" bigint NOT NULL REFERENCES "research_source_type_lookup" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "research_source_type_lookup" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NOT NULL UNIQUE, "name_de" varchar(200) NOT NULL, "name_en" varchar(200) NOT NULL, "description" text NOT NULL, "sort_order" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "provider_name" varchar(100) NOT NULL, "weight" real NOT NULL, "credibility_boost" real NOT NULL, "requires_api_key" bool NOT NULL, "api_key_setting" varchar(100) NOT NULL, "rate_limit_per_minute" integer NULL);UPDATE "main"."sqlite_sequence" SET seq = 10 WHERE name = 'research_source_type_lookup';
CREATE TABLE "research_synthesis_type_lookup" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NOT NULL UNIQUE, "name_de" varchar(200) NOT NULL, "name_en" varchar(200) NOT NULL, "description" text NOT NULL, "sort_order" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "output_format" varchar(50) NOT NULL, "min_word_count" integer NOT NULL, "max_word_count" integer NOT NULL, "include_citations" bool NOT NULL, "include_contradictions" bool NOT NULL, "include_gaps" bool NOT NULL, "prompt_template_key" varchar(100) NOT NULL);UPDATE "main"."sqlite_sequence" SET seq = 6 WHERE name = 'research_synthesis_type_lookup';
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE "story_bibles" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "title" varchar(200) NOT NULL, "subtitle" varchar(300) NOT NULL, "genre" varchar(100) NOT NULL, "target_word_count" integer NOT NULL, "scientific_concepts" text NOT NULL CHECK ((JSON_VALID("scientific_concepts") OR "scientific_concepts" IS NULL)), "world_rules" text NOT NULL CHECK ((JSON_VALID("world_rules") OR "world_rules" IS NULL)), "technology_levels" text NOT NULL CHECK ((JSON_VALID("technology_levels") OR "technology_levels" IS NULL)), "timeline" text NOT NULL CHECK ((JSON_VALID("timeline") OR "timeline" IS NULL)), "timeline_start_year" integer NULL, "timeline_end_year" integer NULL, "prose_style" text NOT NULL, "tone" varchar(100) NOT NULL, "pacing_profile" text NOT NULL CHECK ((JSON_VALID("pacing_profile") OR "pacing_profile" IS NULL)), "status" varchar(20) NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "domain_project_id" bigint NULL REFERENCES "domain_projects" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "target_audiences" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(100) NOT NULL UNIQUE, "age_range" varchar(50) NOT NULL, "description" text NOT NULL, "is_active" bool NOT NULL, "sort_order" integer NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);
CREATE TABLE "template_fields" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "order" integer NOT NULL, "is_required" bool NOT NULL, "field_id" bigint NOT NULL REFERENCES "field_definitions" ("id") DEFERRABLE INITIALLY DEFERRED, "template_id" bigint NOT NULL REFERENCES "field_templates" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "tool_definitions" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "tool_id" varchar(100) NOT NULL UNIQUE, "name" varchar(200) NOT NULL, "description" text NOT NULL, "category" varchar(20) NOT NULL, "executable_path" varchar(500) NOT NULL, "make_command" varchar(100) NOT NULL, "parameters" text NOT NULL CHECK ((JSON_VALID("parameters") OR "parameters" IS NULL)), "version" varchar(20) NOT NULL, "status" varchar(20) NOT NULL, "is_available" bool NOT NULL, "last_check" datetime NULL, "availability_message" text NOT NULL, "avg_execution_time_seconds" real NOT NULL, "total_executions" integer NOT NULL, "success_count" integer NOT NULL, "failure_count" integer NOT NULL, "requires_venv" bool NOT NULL, "python_version_min" varchar(10) NOT NULL, "dependencies" text NOT NULL CHECK ((JSON_VALID("dependencies") OR "dependencies" IS NULL)), "documentation_url" varchar(200) NOT NULL, "example_usage" text NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "sort_order" integer NOT NULL, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "tool_executions" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "started_at" datetime NOT NULL, "completed_at" datetime NULL, "status" varchar(20) NOT NULL, "parameters" text NOT NULL CHECK ((JSON_VALID("parameters") OR "parameters" IS NULL)), "exit_code" integer NULL, "stdout" text NOT NULL, "stderr" text NOT NULL, "error_message" text NOT NULL, "execution_context" text NOT NULL CHECK ((JSON_VALID("execution_context") OR "execution_context" IS NULL)), "executed_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "tool_id" bigint NOT NULL REFERENCES "tool_definitions" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "user_navigation_preferences" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_collapsed" bool NOT NULL, "is_hidden" bool NOT NULL, "custom_order" integer NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "section_id" bigint NOT NULL REFERENCES "navigation_sections" ("id") DEFERRABLE INITIALLY DEFERRED, "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "workflow_domains" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(50) NOT NULL UNIQUE, "name" varchar(100) NOT NULL, "description" text NOT NULL, "characteristics" text NOT NULL, "typical_phases" text NOT NULL, "icon" varchar(50) NOT NULL, "color" varchar(20) NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "project_count" integer NOT NULL, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);UPDATE "main"."sqlite_sequence" SET seq = 4 WHERE name = 'workflow_domains';
CREATE TABLE "workflow_phase_steps" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "order" integer NOT NULL, "required_chapters" integer NOT NULL, "required_characters" integer NOT NULL, "can_skip" bool NOT NULL, "can_return" bool NOT NULL, "phase_id" bigint NOT NULL REFERENCES "workflow_phases" ("id") DEFERRABLE INITIALLY DEFERRED, "template_id" bigint NOT NULL REFERENCES "workflow_templates" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "workflow_phases" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(50) NOT NULL UNIQUE, "description" text NOT NULL, "icon" varchar(50) NOT NULL, "color" varchar(20) NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);
CREATE TABLE "workflow_system_checkpoint" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "phase_name" varchar(100) NOT NULL, "phase_order" integer NOT NULL, "action_name" varchar(100) NOT NULL, "action_order" integer NOT NULL, "handler_class" varchar(255) NOT NULL, "handler_plugin_id" varchar(100) NOT NULL, "config" text NOT NULL CHECK ((JSON_VALID("config") OR "config" IS NULL)), "status" varchar(20) NOT NULL, "output" text NULL CHECK ((JSON_VALID("output") OR "output" IS NULL)), "error" text NOT NULL, "estimated_duration_seconds" integer NOT NULL, "actual_duration_seconds" integer NULL, "started_at" datetime NULL, "completed_at" datetime NULL, "retry_count" integer NOT NULL, "max_retries" integer NOT NULL, "is_required" bool NOT NULL, "continue_on_error" bool NOT NULL, "description" text NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "workflow_id" bigint NOT NULL REFERENCES "workflow_system_workflow" ("id") DEFERRABLE INITIALLY DEFERRED);UPDATE "main"."sqlite_sequence" SET seq = 12 WHERE name = 'workflow_system_checkpoint';
CREATE TABLE "workflow_system_workflow" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "uuid" char(32) NOT NULL UNIQUE, "context" text NOT NULL CHECK ((JSON_VALID("context") OR "context" IS NULL)), "title" varchar(255) NOT NULL, "description" text NOT NULL, "tags" text NOT NULL CHECK ((JSON_VALID("tags") OR "tags" IS NULL)), "status" varchar(20) NOT NULL, "total_checkpoints" integer NOT NULL, "completed_checkpoints" integer NOT NULL, "failed_checkpoints" integer NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "started_at" datetime NULL, "completed_at" datetime NULL, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "domain_id" bigint NOT NULL REFERENCES "workflow_domains" ("id") DEFERRABLE INITIALLY DEFERRED, "template_id" bigint NULL REFERENCES "workflow_templates_v2" ("id") DEFERRABLE INITIALLY DEFERRED);UPDATE "main"."sqlite_sequence" SET seq = 4 WHERE name = 'workflow_system_workflow';
CREATE TABLE "workflow_templates" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(100) NOT NULL, "description" text NOT NULL, "is_default" bool NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "book_type_id" bigint NOT NULL REFERENCES "book_types" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "workflow_templates_v2" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(200) NOT NULL, "description" text NOT NULL, "phases_json" text NOT NULL CHECK ((JSON_VALID("phases_json") OR "phases_json" IS NULL)), "is_default" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "usage_count" integer NOT NULL, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "project_type_id" bigint NOT NULL REFERENCES "project_types" ("id") DEFERRABLE INITIALLY DEFERRED);UPDATE "main"."sqlite_sequence" SET seq = 1 WHERE name = 'workflow_templates_v2';
CREATE TABLE "world_rules" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "category" varchar(100) NOT NULL, "title" varchar(200) NOT NULL, "description" text NOT NULL, "importance" varchar(50) NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "world_id" bigint NOT NULL REFERENCES "world_settings" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "world_settings" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(200) NOT NULL, "description" text NULL, "time_period" varchar(200) NULL, "geography" text NULL, "culture" text NULL, "technology_level" varchar(200) NULL, "magic_system" text NULL, "political_system" text NULL, "economy" text NULL, "history" text NULL, "atmosphere" varchar(200) NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "project_id" bigint NOT NULL UNIQUE REFERENCES "writing_book_projects" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "worlds_v2" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(200) NOT NULL, "description" text NOT NULL, "genre" varchar(100) NOT NULL, "time_period" varchar(100) NOT NULL, "technology_level" varchar(100) NOT NULL, "geography" text NOT NULL, "climate" text NOT NULL, "culture" text NOT NULL, "history" text NOT NULL, "magic_system" text NOT NULL, "political_system" text NOT NULL, "economic_system" text NOT NULL, "rules_data" text NOT NULL CHECK ((JSON_VALID("rules_data") OR "rules_data" IS NULL)), "timeline_data" text NOT NULL CHECK ((JSON_VALID("timeline_data") OR "timeline_data" IS NULL)), "locations_data" text NOT NULL CHECK ((JSON_VALID("locations_data") OR "locations_data" IS NULL)), "has_magic" bool NOT NULL, "magic_system_data" text NULL CHECK ((JSON_VALID("magic_system_data") OR "magic_system_data" IS NULL)), "notes" text NOT NULL, "settings" text NOT NULL CHECK ((JSON_VALID("settings") OR "settings" IS NULL)), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "created_by_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "worlds_v2_books" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "world_id" bigint NOT NULL REFERENCES "worlds_v2" ("id") DEFERRABLE INITIALLY DEFERRED, "bookproject_id" bigint NOT NULL REFERENCES "writing_book_projects" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "writing_book_projects" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "title" varchar(200) NOT NULL, "description" text NULL, "tagline" varchar(300) NULL, "content_rating" varchar(50) NOT NULL, "target_audience" varchar(100) NULL, "story_premise" text NULL, "story_themes" varchar(500) NULL, "setting_time" varchar(200) NULL, "setting_location" varchar(200) NULL, "atmosphere_tone" varchar(200) NULL, "main_conflict" text NULL, "stakes" varchar(500) NULL, "protagonist_concept" varchar(500) NULL, "antagonist_concept" varchar(500) NULL, "inspiration_sources" varchar(500) NULL, "unique_elements" text NULL, "genre_settings" text NULL, "workflow_progress" text NOT NULL CHECK ((JSON_VALID("workflow_progress") OR "workflow_progress" IS NULL)), "phase_data" text NOT NULL CHECK ((JSON_VALID("phase_data") OR "phase_data" IS NULL)), "target_word_count" integer unsigned NOT NULL CHECK ("target_word_count" >= 0), "current_word_count" integer unsigned NOT NULL CHECK ("current_word_count" >= 0), "deadline" datetime NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "book_type_id" bigint NULL REFERENCES "domain_types" ("id") DEFERRABLE INITIALLY DEFERRED, "current_phase_step_id" bigint NULL REFERENCES "workflow_phase_steps" ("id") DEFERRABLE INITIALLY DEFERRED, "current_workflow_phase_id" bigint NULL REFERENCES "project_type_phases" ("id") DEFERRABLE INITIALLY DEFERRED, "genre_id" bigint NULL REFERENCES "genres" ("id") DEFERRABLE INITIALLY DEFERRED, "owner_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "status_id" bigint NULL REFERENCES "writing_statuses" ("id") DEFERRABLE INITIALLY DEFERRED, "user_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "workflow_template_id" bigint NULL REFERENCES "workflow_templates" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "writing_chapters" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "title" varchar(300) NOT NULL, "summary" text NULL, "content" text NULL, "chapter_number" integer unsigned NOT NULL CHECK ("chapter_number" >= 0), "status" varchar(50) NOT NULL, "word_count" integer unsigned NOT NULL CHECK ("word_count" >= 0), "target_word_count" integer unsigned NULL CHECK ("target_word_count" >= 0), "notes" text NULL, "outline" text NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "writing_stage" varchar(50) NOT NULL, "content_hash" varchar(64) NULL, "metadata" text NOT NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "ai_suggestions" text NOT NULL CHECK ((JSON_VALID("ai_suggestions") OR "ai_suggestions" IS NULL)), "consistency_score" real NOT NULL, "mood_tone" varchar(100) NULL, "setting_location" varchar(200) NULL, "time_period" varchar(100) NULL, "character_arcs" text NOT NULL CHECK ((JSON_VALID("character_arcs") OR "character_arcs" IS NULL)), "ai_generated_outline" text NULL, "ai_generated_draft" text NULL, "ai_generated_summary" text NULL, "ai_dialogue_suggestions" text NOT NULL CHECK ((JSON_VALID("ai_dialogue_suggestions") OR "ai_dialogue_suggestions" IS NULL)), "ai_prose_improvements" text NULL, "ai_scene_expansions" text NOT NULL CHECK ((JSON_VALID("ai_scene_expansions") OR "ai_scene_expansions" IS NULL)), "ai_generation_history" text NOT NULL CHECK ((JSON_VALID("ai_generation_history") OR "ai_generation_history" IS NULL)), "project_id" bigint NOT NULL REFERENCES "writing_book_projects" ("id") DEFERRABLE INITIALLY DEFERRED, "story_arc_id" bigint NULL REFERENCES "writing_story_arcs" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "writing_chapters_featured_characters" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "bookchapters_id" bigint NOT NULL REFERENCES "writing_chapters" ("id") DEFERRABLE INITIALLY DEFERRED, "characters_id" bigint NOT NULL REFERENCES "writing_characters" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "writing_chapters_plot_points" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "bookchapters_id" bigint NOT NULL REFERENCES "writing_chapters" ("id") DEFERRABLE INITIALLY DEFERRED, "plotpoint_id" bigint NOT NULL REFERENCES "writing_plot_points" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "writing_characters" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(200) NOT NULL, "description" text NULL, "role" varchar(100) NOT NULL, "age" integer unsigned NULL CHECK ("age" >= 0), "background" text NULL, "personality" text NULL, "appearance" text NULL, "motivation" text NULL, "conflict" text NULL, "arc" text NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "project_id" bigint NOT NULL REFERENCES "writing_book_projects" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "writing_generation_logs" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "started_at" datetime NOT NULL, "completed_at" datetime NULL, "status" varchar(20) NOT NULL, "workflow_type" varchar(50) NOT NULL, "agent_workflow_id" varchar(100) NOT NULL, "agents_used" text NOT NULL CHECK ((JSON_VALID("agents_used") OR "agents_used" IS NULL)), "input_prompt" text NOT NULL, "output_content" text NOT NULL, "input_tokens" integer NOT NULL, "output_tokens" integer NOT NULL, "total_tokens" integer NOT NULL, "cost" decimal NOT NULL, "duration_seconds" integer NULL, "quality_score" real NULL, "error_message" text NOT NULL, "error_traceback" text NOT NULL, "config_used" text NOT NULL CHECK ((JSON_VALID("config_used") OR "config_used" IS NULL)), "notes" text NOT NULL, "llm_id" bigint NULL REFERENCES "llms" ("id") DEFERRABLE INITIALLY DEFERRED, "story_chapter_id" bigint NOT NULL REFERENCES "writing_story_chapters" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "writing_plot_points" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(200) NOT NULL, "description" text NOT NULL, "chapter_number" integer unsigned NOT NULL CHECK ("chapter_number" >= 0), "sequence_order" integer unsigned NOT NULL CHECK ("sequence_order" >= 0), "point_type" varchar(30) NOT NULL, "emotional_impact" varchar(20) NOT NULL, "completion_status" varchar(20) NOT NULL, "notes" text NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "project_id" bigint NOT NULL REFERENCES "writing_book_projects" ("id") DEFERRABLE INITIALLY DEFERRED, "story_arc_id" bigint NOT NULL REFERENCES "writing_story_arcs" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "writing_plot_points_involved_characters" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "plotpoint_id" bigint NOT NULL REFERENCES "writing_plot_points" ("id") DEFERRABLE INITIALLY DEFERRED, "characters_id" bigint NOT NULL REFERENCES "writing_characters" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "writing_statuses" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(50) NOT NULL UNIQUE, "description" text NOT NULL, "color" varchar(20) NOT NULL, "icon" varchar(50) NOT NULL, "sort_order" integer NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);
CREATE TABLE "writing_story_arcs" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(200) NOT NULL, "description" text NULL, "arc_type" varchar(50) NOT NULL, "start_chapter" integer unsigned NOT NULL CHECK ("start_chapter" >= 0), "end_chapter" integer unsigned NULL CHECK ("end_chapter" >= 0), "central_conflict" text NULL, "resolution" text NULL, "importance_level" varchar(20) NOT NULL, "completion_status" varchar(20) NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "project_id" bigint NOT NULL REFERENCES "writing_book_projects" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "writing_story_chapters" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "chapter_number" integer NOT NULL, "volume_number" integer NOT NULL, "title" varchar(300) NOT NULL, "outline" text NOT NULL, "content" text NOT NULL, "summary" text NOT NULL, "word_count" integer NOT NULL, "target_word_count" integer NOT NULL, "quality_score" real NOT NULL, "consistency_score" real NOT NULL, "generation_prompt" text NOT NULL, "generation_config" text NOT NULL CHECK ((JSON_VALID("generation_config") OR "generation_config" IS NULL)), "agent_workflow_id" varchar(100) NOT NULL, "generation_time_seconds" integer NULL, "generation_cost" decimal NOT NULL, "status" varchar(20) NOT NULL, "revision_count" integer NOT NULL, "last_generated_at" datetime NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "notes" text NOT NULL, "book_chapter_id" bigint NULL UNIQUE REFERENCES "writing_chapters" ("id") DEFERRABLE INITIALLY DEFERRED, "story_project_id" bigint NULL REFERENCES "writing_story_projects" ("id") DEFERRABLE INITIALLY DEFERRED, "strand_id" bigint NULL REFERENCES "writing_story_strands" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "writing_story_memories" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "memory_type" varchar(20) NOT NULL, "content" text NOT NULL, "summary" varchar(500) NOT NULL, "locations" text NOT NULL CHECK ((JSON_VALID("locations") OR "locations" IS NULL)), "timestamp_in_story" varchar(100) NOT NULL, "importance" integer NOT NULL, "is_spoiler" bool NOT NULL, "embedding_id" varchar(100) NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "tags" text NOT NULL CHECK ((JSON_VALID("tags") OR "tags" IS NULL)), "chapter_id" bigint NULL REFERENCES "writing_story_chapters" ("id") DEFERRABLE INITIALLY DEFERRED, "revealed_in_chapter_id" bigint NULL REFERENCES "writing_story_chapters" ("id") DEFERRABLE INITIALLY DEFERRED, "story_project_id" bigint NOT NULL REFERENCES "writing_story_projects" ("id") DEFERRABLE INITIALLY DEFERRED, "strand_id" bigint NULL REFERENCES "writing_story_strands" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "writing_story_memories_characters_involved" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "storymemory_id" bigint NOT NULL REFERENCES "writing_story_memories" ("id") DEFERRABLE INITIALLY DEFERRED, "characters_id" bigint NOT NULL REFERENCES "writing_characters" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "writing_story_projects" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "title" varchar(200) NOT NULL, "subtitle" varchar(300) NOT NULL, "slug" varchar(200) NOT NULL UNIQUE, "logline" text NOT NULL, "synopsis" text NOT NULL, "premise" text NOT NULL, "primary_genre" varchar(20) NOT NULL, "secondary_genres" text NOT NULL CHECK ((JSON_VALID("secondary_genres") OR "secondary_genres" IS NULL)), "themes" text NOT NULL CHECK ((JSON_VALID("themes") OR "themes" IS NULL)), "planned_volumes" integer NOT NULL, "target_word_count_per_volume" integer NOT NULL, "strand_count" integer NOT NULL, "status" varchar(20) NOT NULL, "generation_config" text NOT NULL CHECK ((JSON_VALID("generation_config") OR "generation_config" IS NULL)), "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "notes" text NOT NULL, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "llm_model_id" bigint NULL REFERENCES "llms" ("id") DEFERRABLE INITIALLY DEFERRED, "story_bible_id" bigint NULL REFERENCES "story_bibles" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "writing_story_strands" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "title" varchar(200) NOT NULL, "code" varchar(20) NOT NULL, "sort_order" integer NOT NULL, "description" text NOT NULL, "arc_summary" text NOT NULL, "timeline_start" varchar(100) NOT NULL, "timeline_end" varchar(100) NOT NULL, "convergence_points" text NOT NULL CHECK ((JSON_VALID("convergence_points") OR "convergence_points" IS NULL)), "color" varchar(7) NOT NULL, "icon" varchar(50) NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "primary_character_id" bigint NULL REFERENCES "writing_characters" ("id") DEFERRABLE INITIALLY DEFERRED, "story_project_id" bigint NULL REFERENCES "writing_story_projects" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "writing_story_strands_converges_with" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "from_storystrand_id" bigint NOT NULL REFERENCES "writing_story_strands" ("id") DEFERRABLE INITIALLY DEFERRED, "to_storystrand_id" bigint NOT NULL REFERENCES "writing_story_strands" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "writing_story_strands_secondary_characters" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "storystrand_id" bigint NOT NULL REFERENCES "writing_story_strands" ("id") DEFERRABLE INITIALLY DEFERRED, "characters_id" bigint NOT NULL REFERENCES "writing_characters" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "writing_worlds" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(200) NOT NULL, "description" text NULL, "world_type" varchar(100) NOT NULL, "setting_details" text NULL, "geography" text NULL, "culture" text NULL, "technology_level" varchar(200) NULL, "magic_system" text NULL, "politics" text NULL, "history" text NULL, "inhabitants" text NULL, "connections" text NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "project_id" bigint NOT NULL REFERENCES "writing_book_projects" ("id") DEFERRABLE INITIALLY DEFERRED);
BEGIN;
DELETE FROM "main"."action_templates";
COMMIT;
BEGIN;
DELETE FROM "main"."agent_actions";
COMMIT;
BEGIN;
DELETE FROM "main"."agent_artifacts";
COMMIT;
BEGIN;
DELETE FROM "main"."agent_types";
COMMIT;
BEGIN;
DELETE FROM "main"."agents";
COMMIT;
BEGIN;
DELETE FROM "main"."auth_group";
INSERT INTO "main"."auth_group" ("id","name") VALUES (1, 'BookWriting'),(2, 'MedicalTranslation'),(3, 'GenAgent');
COMMIT;
BEGIN;
DELETE FROM "main"."auth_group_permissions";
COMMIT;
BEGIN;
DELETE FROM "main"."auth_permission";
INSERT INTO "main"."auth_permission" ("id","content_type_id","codename","name") VALUES (1, 1, 'add_logentry', 'Can add log entry'),(2, 1, 'change_logentry', 'Can change log entry'),(3, 1, 'delete_logentry', 'Can delete log entry'),(4, 1, 'view_logentry', 'Can view log entry'),(5, 2, 'add_permission', 'Can add permission'),(6, 2, 'change_permission', 'Can change permission'),(7, 2, 'delete_permission', 'Can delete permission'),(8, 2, 'view_permission', 'Can view permission'),(9, 3, 'add_group', 'Can add group'),(10, 3, 'change_group', 'Can change group'),(11, 3, 'delete_group', 'Can delete group'),(12, 3, 'view_group', 'Can view group'),(13, 4, 'add_user', 'Can add user'),(14, 4, 'change_user', 'Can change user'),(15, 4, 'delete_user', 'Can delete user'),(16, 4, 'view_user', 'Can view user'),(17, 5, 'add_contenttype', 'Can add content type'),(18, 5, 'change_contenttype', 'Can change content type'),(19, 5, 'delete_contenttype', 'Can delete content type'),(20, 5, 'view_contenttype', 'Can view content type'),(21, 6, 'add_session', 'Can add session'),(22, 6, 'change_session', 'Can change session'),(23, 6, 'delete_session', 'Can delete session'),(24, 6, 'view_session', 'Can view session'),(25, 7, 'add_historyentry', 'Can add history entry'),(26, 7, 'change_historyentry', 'Can change history entry'),(27, 7, 'delete_historyentry', 'Can delete history entry'),(28, 7, 'view_historyentry', 'Can view history entry'),(29, 8, 'add_booktypes', 'Can add book types'),(30, 8, 'change_booktypes', 'Can change book types'),(31, 8, 'delete_booktypes', 'Can delete book types'),(32, 8, 'view_booktypes', 'Can view book types'),(33, 9, 'add_llms', 'Can add llms'),(34, 9, 'change_llms', 'Can change llms'),(35, 9, 'delete_llms', 'Can delete llms'),(36, 9, 'view_llms', 'Can view llms'),(37, 10, 'add_characters', 'Can add characters'),(38, 10, 'change_characters', 'Can change characters'),(39, 10, 'delete_characters', 'Can delete characters'),(40, 10, 'view_characters', 'Can view characters'),(41, 11, 'add_agentartifacts', 'Can add agent artifacts'),(42, 11, 'change_agentartifacts', 'Can change agent artifacts'),(43, 11, 'delete_agentartifacts', 'Can delete agent artifacts'),(44, 11, 'view_agentartifacts', 'Can view agent artifacts'),(45, 12, 'add_agents', 'Can add agents'),(46, 12, 'change_agents', 'Can change agents'),(47, 12, 'delete_agents', 'Can delete agents'),(48, 12, 'view_agents', 'Can view agents'),(49, 13, 'add_bookprojects', 'Can add book projects'),(50, 13, 'change_bookprojects', 'Can change book projects'),(51, 13, 'delete_bookprojects', 'Can delete book projects'),(52, 13, 'view_bookprojects', 'Can view book projects'),(53, 14, 'add_bookchapters', 'Can add book chapters'),(54, 14, 'change_bookchapters', 'Can change book chapters'),(55, 14, 'delete_bookchapters', 'Can delete book chapters'),(56, 14, 'view_bookchapters', 'Can view book chapters'),(57, 15, 'add_agentexecutions', 'Can add agent executions'),(58, 15, 'change_agentexecutions', 'Can change agent executions'),(59, 15, 'delete_agentexecutions', 'Can delete agent executions'),(60, 15, 'view_agentexecutions', 'Can view agent executions'),(61, 16, 'add_worlds', 'Can add worlds'),(62, 16, 'change_worlds', 'Can change worlds'),(63, 16, 'delete_worlds', 'Can delete worlds'),(64, 16, 'view_worlds', 'Can view worlds'),(65, 17, 'add_plotpoint', 'Can add plot point'),(66, 17, 'change_plotpoint', 'Can change plot point'),(67, 17, 'delete_plotpoint', 'Can delete plot point'),(68, 17, 'view_plotpoint', 'Can view plot point'),(69, 18, 'add_storyarc', 'Can add story arc'),(70, 18, 'change_storyarc', 'Can change story arc'),(71, 18, 'delete_storyarc', 'Can delete story arc'),(72, 18, 'view_storyarc', 'Can view story arc'),(73, 19, 'add_fieldusage', 'Can add field usage'),(74, 19, 'change_fieldusage', 'Can change field usage'),(75, 19, 'delete_fieldusage', 'Can delete field usage'),(76, 19, 'view_fieldusage', 'Can view field usage'),(77, 20, 'add_queryperformancelog', 'Can add query performance log'),(78, 20, 'change_queryperformancelog', 'Can change query performance log'),(79, 20, 'delete_queryperformancelog', 'Can delete query performance log'),(80, 20, 'view_queryperformancelog', 'Can view query performance log'),(81, 21, 'add_graphqloperation', 'Can add graph ql operation'),(82, 21, 'change_graphqloperation', 'Can change graph ql operation'),(83, 21, 'delete_graphqloperation', 'Can delete graph ql operation'),(84, 21, 'view_graphqloperation', 'Can view graph ql operation'),(85, 22, 'add_targetaudience', 'Can add Target Audience'),(86, 22, 'change_targetaudience', 'Can change Target Audience'),(87, 22, 'delete_targetaudience', 'Can delete Target Audience'),(88, 22, 'view_targetaudience', 'Can view Target Audience'),(89, 23, 'add_writingstatus', 'Can add Writing Status'),(90, 23, 'change_writingstatus', 'Can change Writing Status'),(91, 23, 'delete_writingstatus', 'Can delete Writing Status'),(92, 23, 'view_writingstatus', 'Can view Writing Status'),(93, 24, 'add_genre', 'Can add Genre'),(94, 24, 'change_genre', 'Can change Genre'),(95, 24, 'delete_genre', 'Can delete Genre'),(96, 24, 'view_genre', 'Can view Genre'),(97, 25, 'add_workflowphase', 'Can add Workflow Phase'),(98, 25, 'change_workflowphase', 'Can change Workflow Phase'),(99, 25, 'delete_workflowphase', 'Can delete Workflow Phase'),(100, 25, 'view_workflowphase', 'Can view Workflow Phase'),(101, 26, 'add_workflowphasestep', 'Can add Workflow Phase Step'),(102, 26, 'change_workflowphasestep', 'Can change Workflow Phase Step'),(103, 26, 'delete_workflowphasestep', 'Can delete Workflow Phase Step'),(104, 26, 'view_workflowphasestep', 'Can view Workflow Phase Step'),(105, 27, 'add_workflowtemplate', 'Can add Workflow Template'),(106, 27, 'change_workflowtemplate', 'Can change Workflow Template'),(107, 27, 'delete_workflowtemplate', 'Can delete Workflow Template'),(108, 27, 'view_workflowtemplate', 'Can view Workflow Template'),(109, 28, 'add_phaseactionconfig', 'Can add Phase Action Configuration'),(110, 28, 'change_phaseactionconfig', 'Can change Phase Action Configuration'),(111, 28, 'delete_phaseactionconfig', 'Can delete Phase Action Configuration'),(112, 28, 'view_phaseactionconfig', 'Can view Phase Action Configuration'),(113, 29, 'add_projectphasehistory', 'Can add Project Phase History'),(114, 29, 'change_projectphasehistory', 'Can change Project Phase History'),(115, 29, 'delete_projectphasehistory', 'Can delete Project Phase History'),(116, 29, 'view_projectphasehistory', 'Can view Project Phase History'),(117, 30, 'add_prompttemplate', 'Can add prompt template'),(118, 30, 'change_prompttemplate', 'Can change prompt template'),(119, 30, 'delete_prompttemplate', 'Can delete prompt template'),(120, 30, 'view_prompttemplate', 'Can view prompt template'),(121, 31, 'add_phaseagentconfig', 'Can add Phase Agent Configuration'),(122, 31, 'change_phaseagentconfig', 'Can change Phase Agent Configuration'),(123, 31, 'delete_phaseagentconfig', 'Can delete Phase Agent Configuration'),(124, 31, 'view_phaseagentconfig', 'Can view Phase Agent Configuration'),(125, 32, 'add_agentaction', 'Can add Agent Action'),(126, 32, 'change_agentaction', 'Can change Agent Action'),(127, 32, 'delete_agentaction', 'Can delete Agent Action'),(128, 32, 'view_agentaction', 'Can view Agent Action'),(129, 33, 'add_enrichmentresponse', 'Can add Enrichment Response'),(130, 33, 'change_enrichmentresponse', 'Can change Enrichment Response'),(131, 33, 'delete_enrichmentresponse', 'Can delete Enrichment Response'),(132, 33, 'view_enrichmentresponse', 'Can view Enrichment Response'),(133, 34, 'add_fielddefinition', 'Can add Field Definition'),(134, 34, 'change_fielddefinition', 'Can change Field Definition'),(135, 34, 'delete_fielddefinition', 'Can delete Field Definition'),(136, 34, 'view_fielddefinition', 'Can view Field Definition'),(137, 35, 'add_fieldgroup', 'Can add Field Group'),(138, 35, 'change_fieldgroup', 'Can change Field Group'),(139, 35, 'delete_fieldgroup', 'Can delete Field Group'),(140, 35, 'view_fieldgroup', 'Can view Field Group'),(141, 36, 'add_fieldtemplate', 'Can add Field Template'),(142, 36, 'change_fieldtemplate', 'Can change Field Template'),(143, 36, 'delete_fieldtemplate', 'Can delete Field Template'),(144, 36, 'view_fieldtemplate', 'Can view Field Template'),(145, 37, 'add_fieldvaluehistory', 'Can add Field Value History'),(146, 37, 'change_fieldvaluehistory', 'Can change Field Value History'),(147, 37, 'delete_fieldvaluehistory', 'Can delete Field Value History'),(148, 37, 'view_fieldvaluehistory', 'Can view Field Value History'),(149, 38, 'add_projectfieldvalue', 'Can add Project Field Value'),(150, 38, 'change_projectfieldvalue', 'Can change Project Field Value'),(151, 38, 'delete_projectfieldvalue', 'Can delete Project Field Value'),(152, 38, 'view_projectfieldvalue', 'Can view Project Field Value'),(153, 39, 'add_templatefield', 'Can add template field'),(154, 39, 'change_templatefield', 'Can change template field'),(155, 39, 'delete_templatefield', 'Can delete template field'),(156, 39, 'view_templatefield', 'Can view template field'),(157, 40, 'add_booktypephase', 'Can add Book Type Phase'),(158, 40, 'change_booktypephase', 'Can change Book Type Phase'),(159, 40, 'delete_booktypephase', 'Can delete Book Type Phase'),(160, 40, 'view_booktypephase', 'Can view Book Type Phase'),(161, 41, 'add_actiontemplate', 'Can add Action Template'),(162, 41, 'change_actiontemplate', 'Can change Action Template'),(163, 41, 'delete_actiontemplate', 'Can delete Action Template'),(164, 41, 'view_actiontemplate', 'Can view Action Template'),(165, 42, 'add_agenttype', 'Can add Agent Type'),(166, 42, 'change_agenttype', 'Can change Agent Type'),(167, 42, 'delete_agenttype', 'Can delete Agent Type'),(168, 42, 'view_agenttype', 'Can view Agent Type'),(169, 43, 'add_phase', 'Can add GenAgent Phase'),(170, 43, 'change_phase', 'Can change GenAgent Phase'),(171, 43, 'delete_phase', 'Can delete GenAgent Phase'),(172, 43, 'view_phase', 'Can view GenAgent Phase'),(173, 44, 'add_action', 'Can add GenAgent Action'),(174, 44, 'change_action', 'Can change GenAgent Action'),(175, 44, 'delete_action', 'Can delete GenAgent Action'),(176, 44, 'view_action', 'Can view GenAgent Action'),(177, 45, 'add_executionlog', 'Can add GenAgent Execution Log'),(178, 45, 'change_executionlog', 'Can change GenAgent Execution Log'),(179, 45, 'delete_executionlog', 'Can delete GenAgent Execution Log'),(180, 45, 'view_executionlog', 'Can view GenAgent Execution Log'),(181, 46, 'add_customdomain', 'Can add Custom Domain'),(182, 46, 'change_customdomain', 'Can change Custom Domain'),(183, 46, 'delete_customdomain', 'Can delete Custom Domain'),(184, 46, 'view_customdomain', 'Can view Custom Domain'),(185, 47, 'add_presentation', 'Can add Presentation'),(186, 47, 'change_presentation', 'Can change Presentation'),(187, 47, 'delete_presentation', 'Can delete Presentation'),(188, 47, 'view_presentation', 'Can view Presentation'),(189, 48, 'add_customer', 'Can add Medical Translation Customer'),(190, 48, 'change_customer', 'Can change Medical Translation Customer'),(191, 48, 'delete_customer', 'Can delete Medical Translation Customer'),(192, 48, 'view_customer', 'Can view Medical Translation Customer'),(193, 49, 'add_presentationtext', 'Can add Presentation Text'),(194, 49, 'change_presentationtext', 'Can change Presentation Text'),(195, 49, 'delete_presentationtext', 'Can delete Presentation Text'),(196, 49, 'view_presentationtext', 'Can view Presentation Text'),(197, 50, 'add_promptexecution', 'Can add Prompt Execution'),(198, 50, 'change_promptexecution', 'Can change Prompt Execution'),(199, 50, 'delete_promptexecution', 'Can delete Prompt Execution'),(200, 50, 'view_promptexecution', 'Can view Prompt Execution'),(201, 51, 'add_prompttemplatelegacy', 'Can add Prompt Template (Legacy)'),(202, 51, 'change_prompttemplatelegacy', 'Can change Prompt Template (Legacy)'),(203, 51, 'delete_prompttemplatelegacy', 'Can delete Prompt Template (Legacy)'),(204, 51, 'view_prompttemplatelegacy', 'Can view Prompt Template (Legacy)'),(205, 52, 'add_prompttemplatetest', 'Can add Prompt Template Test'),(206, 52, 'change_prompttemplatetest', 'Can change Prompt Template Test'),(207, 52, 'delete_prompttemplatetest', 'Can delete Prompt Template Test'),(208, 52, 'view_prompttemplatetest', 'Can view Prompt Template Test'),(209, 53, 'add_handler', 'Can add Handler'),(210, 53, 'change_handler', 'Can change Handler'),(211, 53, 'delete_handler', 'Can delete Handler'),(212, 53, 'view_handler', 'Can view Handler'),(213, 54, 'add_actionhandler', 'Can add Action Handler'),(214, 54, 'change_actionhandler', 'Can change Action Handler'),(215, 54, 'delete_actionhandler', 'Can delete Action Handler'),(216, 54, 'view_actionhandler', 'Can view Action Handler'),(217, 55, 'add_handlerexecution', 'Can add Handler Execution'),(218, 55, 'change_handlerexecution', 'Can change Handler Execution'),(219, 55, 'delete_handlerexecution', 'Can delete Handler Execution'),(220, 55, 'view_handlerexecution', 'Can view Handler Execution'),(221, 56, 'add_essay', 'Can add Essay'),(222, 56, 'change_essay', 'Can change Essay'),(223, 56, 'delete_essay', 'Can delete Essay'),(224, 56, 'view_essay', 'Can view Essay'),(225, 57, 'add_location', 'Can add Location'),(226, 57, 'change_location', 'Can change Location'),(227, 57, 'delete_location', 'Can delete Location'),(228, 57, 'view_location', 'Can view Location'),(229, 58, 'add_worldsetting', 'Can add World Setting'),(230, 58, 'change_worldsetting', 'Can change World Setting'),(231, 58, 'delete_worldsetting', 'Can delete World Setting'),(232, 58, 'view_worldsetting', 'Can view World Setting'),(233, 59, 'add_worldrule', 'Can add World Rule'),(234, 59, 'change_worldrule', 'Can change World Rule'),(235, 59, 'delete_worldrule', 'Can delete World Rule'),(236, 59, 'view_worldrule', 'Can view World Rule'),(237, 60, 'add_componentregistry', 'Can add Component'),(238, 60, 'change_componentregistry', 'Can change Component'),(239, 60, 'delete_componentregistry', 'Can delete Component'),(240, 60, 'view_componentregistry', 'Can view Component'),(241, 61, 'add_componentchangelog', 'Can add component change log'),(242, 61, 'change_componentchangelog', 'Can change component change log'),(243, 61, 'delete_componentchangelog', 'Can delete component change log'),(244, 61, 'view_componentchangelog', 'Can view component change log'),(245, 62, 'add_componentusagelog', 'Can add component usage log'),(246, 62, 'change_componentusagelog', 'Can change component usage log'),(247, 62, 'delete_componentusagelog', 'Can delete component usage log'),(248, 62, 'view_componentusagelog', 'Can view component usage log'),(249, 63, 'add_migrationconflict', 'Can add migration conflict'),(250, 63, 'change_migrationconflict', 'Can change migration conflict'),(251, 63, 'delete_migrationconflict', 'Can delete migration conflict'),(252, 63, 'view_migrationconflict', 'Can view migration conflict'),(253, 64, 'add_migrationregistry', 'Can add migration registry'),(254, 64, 'change_migrationregistry', 'Can change migration registry'),(255, 64, 'delete_migrationregistry', 'Can delete migration registry'),(256, 64, 'view_migrationregistry', 'Can view migration registry'),(257, 65, 'add_featuredocumentkeyword', 'Can add feature document keyword'),(258, 65, 'change_featuredocumentkeyword', 'Can change feature document keyword'),(259, 65, 'delete_featuredocumentkeyword', 'Can delete feature document keyword'),(260, 65, 'view_featuredocumentkeyword', 'Can view feature document keyword'),(261, 66, 'add_featuredocument', 'Can add feature document'),(262, 66, 'change_featuredocument', 'Can change feature document'),(263, 66, 'delete_featuredocument', 'Can delete feature document'),(264, 66, 'view_featuredocument', 'Can view feature document'),(265, 67, 'add_contextenrichmentlog', 'Can add Context Enrichment Log'),(266, 67, 'change_contextenrichmentlog', 'Can change Context Enrichment Log'),(267, 67, 'delete_contextenrichmentlog', 'Can delete Context Enrichment Log'),(268, 67, 'view_contextenrichmentlog', 'Can view Context Enrichment Log'),(269, 68, 'add_contextschema', 'Can add Context Schema'),(270, 68, 'change_contextschema', 'Can change Context Schema'),(271, 68, 'delete_contextschema', 'Can delete Context Schema'),(272, 68, 'view_contextschema', 'Can view Context Schema'),(273, 69, 'add_contextsource', 'Can add Context Source'),(274, 69, 'change_contextsource', 'Can change Context Source'),(275, 69, 'delete_contextsource', 'Can delete Context Source'),(276, 69, 'view_contextsource', 'Can view Context Source'),(277, 70, 'add_reviewparticipant', 'Can add Review Participant'),(278, 70, 'change_reviewparticipant', 'Can change Review Participant'),(279, 70, 'delete_reviewparticipant', 'Can delete Review Participant'),(280, 70, 'view_reviewparticipant', 'Can view Review Participant'),(281, 71, 'add_comment', 'Can add Comment'),(282, 71, 'change_comment', 'Can change Comment'),(283, 71, 'delete_comment', 'Can delete Comment'),(284, 71, 'view_comment', 'Can view Comment'),(285, 72, 'add_chapterrating', 'Can add Chapter Rating'),(286, 72, 'change_chapterrating', 'Can change Chapter Rating'),(287, 72, 'delete_chapterrating', 'Can delete Chapter Rating'),(288, 72, 'view_chapterrating', 'Can view Chapter Rating'),(289, 73, 'add_reviewround', 'Can add Review Round'),(290, 73, 'change_reviewround', 'Can change Review Round'),(291, 73, 'delete_reviewround', 'Can delete Review Round'),(292, 73, 'view_reviewround', 'Can view Review Round'),(293, 74, 'add_imagestyleprofile', 'Can add Image Style Profile'),(294, 74, 'change_imagestyleprofile', 'Can change Image Style Profile'),(295, 74, 'delete_imagestyleprofile', 'Can delete Image Style Profile'),(296, 74, 'view_imagestyleprofile', 'Can view Image Style Profile'),(297, 75, 'add_imagegenerationbatch', 'Can add Image Generation Batch'),(298, 75, 'change_imagegenerationbatch', 'Can change Image Generation Batch'),(299, 75, 'delete_imagegenerationbatch', 'Can delete Image Generation Batch'),(300, 75, 'view_imagegenerationbatch', 'Can view Image Generation Batch'),(301, 76, 'add_generatedimage', 'Can add Generated Image'),(302, 76, 'change_generatedimage', 'Can change Generated Image'),(303, 76, 'delete_generatedimage', 'Can delete Generated Image'),(304, 76, 'view_generatedimage', 'Can view Generated Image'),(305, 77, 'add_testcase', 'Can add test case'),(306, 77, 'change_testcase', 'Can change test case'),(307, 77, 'delete_testcase', 'Can delete test case'),(308, 77, 'view_testcase', 'Can view test case'),(309, 78, 'add_testrequirement', 'Can add test requirement'),(310, 78, 'change_testrequirement', 'Can change test requirement'),(311, 78, 'delete_testrequirement', 'Can delete test requirement'),(312, 78, 'view_testrequirement', 'Can view test requirement'),(313, 79, 'add_testcoveragereport', 'Can add test coverage report'),(314, 79, 'change_testcoveragereport', 'Can change test coverage report'),(315, 79, 'delete_testcoveragereport', 'Can delete test coverage report'),(316, 79, 'view_testcoveragereport', 'Can view test coverage report'),(317, 80, 'add_requirementtestlink', 'Can add requirement test link'),(318, 80, 'change_requirementtestlink', 'Can change requirement test link'),(319, 80, 'delete_requirementtestlink', 'Can delete requirement test link'),(320, 80, 'view_requirementtestlink', 'Can view requirement test link'),(321, 81, 'add_testsession', 'Can add test session'),(322, 81, 'change_testsession', 'Can change test session'),(323, 81, 'delete_testsession', 'Can delete test session'),(324, 81, 'view_testsession', 'Can view test session'),(325, 82, 'add_testscreenshot', 'Can add test screenshot'),(326, 82, 'change_testscreenshot', 'Can change test screenshot'),(327, 82, 'delete_testscreenshot', 'Can delete test screenshot'),(328, 82, 'view_testscreenshot', 'Can view test screenshot'),(329, 83, 'add_testlog', 'Can add test log'),(330, 83, 'change_testlog', 'Can change test log'),(331, 83, 'delete_testlog', 'Can delete test log'),(332, 83, 'view_testlog', 'Can view test log'),(333, 84, 'add_testbug', 'Can add test bug'),(334, 84, 'change_testbug', 'Can change test bug'),(335, 84, 'delete_testbug', 'Can delete test bug'),(336, 84, 'view_testbug', 'Can view test bug'),(337, 85, 'add_testexecution', 'Can add test execution'),(338, 85, 'change_testexecution', 'Can change test execution'),(339, 85, 'delete_testexecution', 'Can delete test execution'),(340, 85, 'view_testexecution', 'Can view test execution'),(341, 86, 'add_bugfixplan', 'Can add bug fix plan'),(342, 86, 'change_bugfixplan', 'Can change bug fix plan'),(343, 86, 'delete_bugfixplan', 'Can delete bug fix plan'),(344, 86, 'view_bugfixplan', 'Can view bug fix plan'),(345, 87, 'add_presentation', 'Can add presentation'),(346, 87, 'change_presentation', 'Can change presentation'),(347, 87, 'delete_presentation', 'Can delete presentation'),(348, 87, 'view_presentation', 'Can view presentation'),(349, 88, 'add_enhancement', 'Can add enhancement'),(350, 88, 'change_enhancement', 'Can change enhancement'),(351, 88, 'delete_enhancement', 'Can delete enhancement'),(352, 88, 'view_enhancement', 'Can view enhancement'),(353, 89, 'add_previewslide', 'Can add preview slide'),(354, 89, 'change_previewslide', 'Can change preview slide'),(355, 89, 'delete_previewslide', 'Can delete preview slide'),(356, 89, 'view_previewslide', 'Can view preview slide'),(357, 90, 'add_designprofile', 'Can add design profile'),(358, 90, 'change_designprofile', 'Can change design profile'),(359, 90, 'delete_designprofile', 'Can delete design profile'),(360, 90, 'view_designprofile', 'Can view design profile'),(361, 91, 'add_templatecollection', 'Can add Template Collection'),(362, 91, 'change_templatecollection', 'Can change Template Collection'),(363, 91, 'delete_templatecollection', 'Can delete Template Collection'),(364, 91, 'view_templatecollection', 'Can view Template Collection'),(365, 93, 'add_domainart', 'Can add Domain Art'),(366, 93, 'change_domainart', 'Can change Domain Art'),(367, 93, 'delete_domainart', 'Can delete Domain Art'),(368, 93, 'view_domainart', 'Can view Domain Art'),(369, 94, 'add_domaintype', 'Can add Domain Type'),(370, 94, 'change_domaintype', 'Can change Domain Type'),(371, 94, 'delete_domaintype', 'Can delete Domain Type'),(372, 94, 'view_domaintype', 'Can view Domain Type'),(373, 95, 'add_illustrationimage', 'Can add Illustration Image (Legacy)'),(374, 95, 'change_illustrationimage', 'Can change Illustration Image (Legacy)'),(375, 95, 'delete_illustrationimage', 'Can delete Illustration Image (Legacy)'),(376, 95, 'view_illustrationimage', 'Can view Illustration Image (Legacy)'),(377, 92, 'add_domainphase', 'Can add Domain Phase'),(378, 92, 'change_domainphase', 'Can change Domain Phase'),(379, 92, 'delete_domainphase', 'Can delete Domain Phase'),(380, 92, 'view_domainphase', 'Can view Domain Phase'),(381, 97, 'add_chapterbeat', 'Can add Chapter Beat'),(382, 97, 'change_chapterbeat', 'Can change Chapter Beat'),(383, 97, 'delete_chapterbeat', 'Can delete Chapter Beat'),(384, 97, 'view_chapterbeat', 'Can view Chapter Beat'),(385, 96, 'add_storybible', 'Can add Story Bible'),(386, 96, 'change_storybible', 'Can change Story Bible'),(387, 96, 'delete_storybible', 'Can delete Story Bible'),(388, 96, 'view_storybible', 'Can view Story Bible'),(389, 98, 'add_storychapter', 'Can add Story Chapter'),(390, 98, 'change_storychapter', 'Can change Story Chapter'),(391, 98, 'delete_storychapter', 'Can delete Story Chapter'),(392, 98, 'view_storychapter', 'Can view Story Chapter'),(393, 99, 'add_storycharacter', 'Can add Story Character'),(394, 99, 'change_storycharacter', 'Can change Story Character'),(395, 99, 'delete_storycharacter', 'Can delete Story Character'),(396, 99, 'view_storycharacter', 'Can view Story Character'),(397, 100, 'add_storystrand', 'Can add Story Strand'),(398, 100, 'change_storystrand', 'Can change Story Strand'),(399, 100, 'delete_storystrand', 'Can delete Story Strand'),(400, 100, 'view_storystrand', 'Can view Story Strand'),(401, 101, 'add_domainproject', 'Can add Domain Project'),(402, 101, 'change_domainproject', 'Can change Domain Project'),(403, 101, 'delete_domainproject', 'Can delete Domain Project'),(404, 101, 'view_domainproject', 'Can view Domain Project'),(405, 102, 'add_domain', 'Can add Domain'),(406, 102, 'change_domain', 'Can change Domain'),(407, 102, 'delete_domain', 'Can delete Domain'),(408, 102, 'view_domain', 'Can view Domain'),(409, 103, 'add_domainart', 'Can add domain art'),(410, 103, 'change_domainart', 'Can change domain art'),(411, 103, 'delete_domainart', 'Can delete domain art'),(412, 103, 'view_domainart', 'Can view domain art'),(413, 104, 'add_domaintype', 'Can add domain type'),(414, 104, 'change_domaintype', 'Can change domain type'),(415, 104, 'delete_domaintype', 'Can delete domain type'),(416, 104, 'view_domaintype', 'Can view domain type'),(417, 105, 'add_domainphase', 'Can add domain phase'),(418, 105, 'change_domainphase', 'Can change domain phase'),(419, 105, 'delete_domainphase', 'Can delete domain phase'),(420, 105, 'view_domainphase', 'Can view domain phase'),(421, 106, 'add_domainproject', 'Can add domain project'),(422, 106, 'change_domainproject', 'Can change domain project'),(423, 106, 'delete_domainproject', 'Can delete domain project'),(424, 106, 'view_domainproject', 'Can view domain project'),(425, 107, 'add_tooldefinition', 'Can add Tool Definition'),(426, 107, 'change_tooldefinition', 'Can change Tool Definition'),(427, 107, 'delete_tooldefinition', 'Can delete Tool Definition'),(428, 107, 'view_tooldefinition', 'Can view Tool Definition'),(429, 108, 'add_toolexecution', 'Can add Tool Execution'),(430, 108, 'change_toolexecution', 'Can change Tool Execution'),(431, 108, 'delete_toolexecution', 'Can delete Tool Execution'),(432, 108, 'view_toolexecution', 'Can view Tool Execution'),(433, 109, 'add_llmprompttemplate', 'Can add LLM Prompt Template'),(434, 109, 'change_llmprompttemplate', 'Can change LLM Prompt Template'),(435, 109, 'delete_llmprompttemplate', 'Can delete LLM Prompt Template'),(436, 109, 'view_llmprompttemplate', 'Can view LLM Prompt Template'),(437, 110, 'add_llmpromptexecution', 'Can add Prompt Execution'),(438, 110, 'change_llmpromptexecution', 'Can change Prompt Execution'),(439, 110, 'delete_llmpromptexecution', 'Can delete Prompt Execution'),(440, 110, 'view_llmpromptexecution', 'Can view Prompt Execution'),(441, 111, 'add_generationlog', 'Can add Generation Log'),(442, 111, 'change_generationlog', 'Can change Generation Log'),(443, 111, 'delete_generationlog', 'Can delete Generation Log'),(444, 111, 'view_generationlog', 'Can view Generation Log'),(445, 112, 'add_storymemory', 'Can add Story Memory'),(446, 112, 'change_storymemory', 'Can change Story Memory'),(447, 112, 'delete_storymemory', 'Can delete Story Memory'),(448, 112, 'view_storymemory', 'Can view Story Memory'),(449, 113, 'add_storyproject', 'Can add Story Project'),(450, 113, 'change_storyproject', 'Can change Story Project'),(451, 113, 'delete_storyproject', 'Can delete Story Project'),(452, 113, 'view_storyproject', 'Can view Story Project'),(453, 114, 'add_llm', 'Can add LLM'),(454, 114, 'change_llm', 'Can change LLM'),(455, 114, 'delete_llm', 'Can delete LLM'),(456, 114, 'view_llm', 'Can view LLM'),(457, 115, 'add_agent', 'Can add Agent'),(458, 115, 'change_agent', 'Can change Agent'),(459, 115, 'delete_agent', 'Can delete Agent'),(460, 115, 'view_agent', 'Can view Agent'),(461, 116, 'add_llmexecution', 'Can add LLM Execution'),(462, 116, 'change_llmexecution', 'Can change LLM Execution'),(463, 116, 'delete_llmexecution', 'Can delete LLM Execution'),(464, 116, 'view_llmexecution', 'Can view LLM Execution'),(465, 117, 'add_agentexecution', 'Can add Agent Execution'),(466, 117, 'change_agentexecution', 'Can change Agent Execution'),(467, 117, 'delete_agentexecution', 'Can delete Agent Execution'),(468, 117, 'view_agentexecution', 'Can view Agent Execution'),(469, 118, 'add_prompttemplate', 'Can add Prompt Template'),(470, 118, 'change_prompttemplate', 'Can change Prompt Template'),(471, 118, 'delete_prompttemplate', 'Can delete Prompt Template'),(472, 118, 'view_prompttemplate', 'Can view Prompt Template'),(473, 119, 'add_promptexecution', 'Can add Prompt Execution'),(474, 119, 'change_promptexecution', 'Can change Prompt Execution'),(475, 119, 'delete_promptexecution', 'Can delete Prompt Execution'),(476, 119, 'view_promptexecution', 'Can view Prompt Execution'),(477, 120, 'add_promptversion', 'Can add Prompt Version'),(478, 120, 'change_promptversion', 'Can change Prompt Version'),(479, 120, 'delete_promptversion', 'Can delete Prompt Version'),(480, 120, 'view_promptversion', 'Can view Prompt Version'),(481, 121, 'add_handler', 'Can add Handler'),(482, 121, 'change_handler', 'Can change Handler'),(483, 121, 'delete_handler', 'Can delete Handler'),(484, 121, 'view_handler', 'Can view Handler'),(485, 122, 'add_bookproject', 'Can add Book Project'),(486, 122, 'change_bookproject', 'Can change Book Project'),(487, 122, 'delete_bookproject', 'Can delete Book Project'),(488, 122, 'view_bookproject', 'Can view Book Project'),(489, 123, 'add_chapter', 'Can add Chapter'),(490, 123, 'change_chapter', 'Can change Chapter'),(491, 123, 'delete_chapter', 'Can delete Chapter'),(492, 123, 'view_chapter', 'Can view Chapter'),(493, 124, 'add_character', 'Can add Character'),(494, 124, 'change_character', 'Can change Character'),(495, 124, 'delete_character', 'Can delete Character'),(496, 124, 'view_character', 'Can view Character'),(497, 125, 'add_bookcharacter', 'Can add Book Character'),(498, 125, 'change_bookcharacter', 'Can change Book Character'),(499, 125, 'delete_bookcharacter', 'Can delete Book Character'),(500, 125, 'view_bookcharacter', 'Can view Book Character'),(501, 126, 'add_world', 'Can add World'),(502, 126, 'change_world', 'Can change World'),(503, 126, 'delete_world', 'Can delete World'),(504, 126, 'view_world', 'Can view World'),(505, 127, 'add_illustrationstyle', 'Can add Illustration Style'),(506, 127, 'change_illustrationstyle', 'Can change Illustration Style'),(507, 127, 'delete_illustrationstyle', 'Can delete Illustration Style'),(508, 127, 'view_illustrationstyle', 'Can view Illustration Style'),(509, 128, 'add_projectphaseaction', 'Can add Project Phase Action'),(510, 128, 'change_projectphaseaction', 'Can change Project Phase Action'),(511, 128, 'delete_projectphaseaction', 'Can delete Project Phase Action'),(512, 128, 'view_projectphaseaction', 'Can view Project Phase Action'),(513, 129, 'add_projecttypephase', 'Can add Project Type Phase'),(514, 129, 'change_projecttypephase', 'Can change Project Type Phase'),(515, 129, 'delete_projecttypephase', 'Can delete Project Type Phase'),(516, 129, 'view_projecttypephase', 'Can view Project Type Phase'),(517, 130, 'add_bookstatus', 'Can add Book Status'),(518, 130, 'change_bookstatus', 'Can change Book Status'),(519, 130, 'delete_bookstatus', 'Can delete Book Status'),(520, 130, 'view_bookstatus', 'Can view Book Status'),(521, 131, 'add_genre', 'Can add Genre'),(522, 131, 'change_genre', 'Can change Genre'),(523, 131, 'delete_genre', 'Can delete Genre'),(524, 131, 'view_genre', 'Can view Genre'),(525, 132, 'add_bookproject', 'Can add Book Project'),(526, 132, 'change_bookproject', 'Can change Book Project'),(527, 132, 'delete_bookproject', 'Can delete Book Project'),(528, 132, 'view_bookproject', 'Can view Book Project'),(529, 133, 'add_domainsection', 'Can add Domain Section'),(530, 133, 'change_domainsection', 'Can change Domain Section'),(531, 133, 'delete_domainsection', 'Can delete Domain Section'),(532, 133, 'view_domainsection', 'Can view Domain Section'),(533, 134, 'add_domainsectionitem', 'Can add Domain Section Item'),(534, 134, 'change_domainsectionitem', 'Can change Domain Section Item'),(535, 134, 'delete_domainsectionitem', 'Can delete Domain Section Item'),(536, 134, 'view_domainsectionitem', 'Can view Domain Section Item'),(537, 135, 'add_analysisjob', 'Can add Analysis Job'),(538, 135, 'change_analysisjob', 'Can change Analysis Job'),(539, 135, 'delete_analysisjob', 'Can delete Analysis Job'),(540, 135, 'view_analysisjob', 'Can view Analysis Job'),(541, 136, 'add_analysisreport', 'Can add Analysis Report'),(542, 136, 'change_analysisreport', 'Can change Analysis Report'),(543, 136, 'delete_analysisreport', 'Can delete Analysis Report'),(544, 136, 'view_analysisreport', 'Can view Analysis Report'),(545, 137, 'add_drawingfile', 'Can add Drawing File'),(546, 137, 'change_drawingfile', 'Can change Drawing File'),(547, 137, 'delete_drawingfile', 'Can delete Drawing File'),(548, 137, 'view_drawingfile', 'Can view Drawing File'),(549, 138, 'add_analysisresult', 'Can add Analysis Result'),(550, 138, 'change_analysisresult', 'Can change Analysis Result'),(551, 138, 'delete_analysisresult', 'Can delete Analysis Result'),(552, 138, 'view_analysisresult', 'Can view Analysis Result'),(553, 139, 'add_idea', 'Can add Idea'),(554, 139, 'change_idea', 'Can change Idea'),(555, 139, 'delete_idea', 'Can delete Idea'),(556, 139, 'view_idea', 'Can view Idea'),(557, 144, 'add_contentblock', 'Can add Content Block'),(558, 144, 'change_contentblock', 'Can change Content Block'),(559, 144, 'delete_contentblock', 'Can delete Content Block'),(560, 144, 'view_contentblock', 'Can view Content Block'),(561, 145, 'add_pluginregistry', 'Can add Plugin'),(562, 145, 'change_pluginregistry', 'Can change Plugin'),(563, 145, 'delete_pluginregistry', 'Can delete Plugin'),(564, 145, 'view_pluginregistry', 'Can view Plugin'),(565, 146, 'add_pluginexecution', 'Can add Plugin Execution'),(566, 146, 'change_pluginexecution', 'Can change Plugin Execution'),(567, 146, 'delete_pluginexecution', 'Can delete Plugin Execution'),(568, 146, 'view_pluginexecution', 'Can view Plugin Execution'),(569, 147, 'add_pluginconfiguration', 'Can add Plugin Configuration'),(570, 147, 'change_pluginconfiguration', 'Can change Plugin Configuration'),(571, 147, 'delete_pluginconfiguration', 'Can delete Plugin Configuration'),(572, 147, 'view_pluginconfiguration', 'Can view Plugin Configuration'),(573, 143, 'add_checklisttemplate', 'Can add Checklist Template'),(574, 143, 'change_checklisttemplate', 'Can change Checklist Template'),(575, 143, 'delete_checklisttemplate', 'Can delete Checklist Template'),(576, 143, 'view_checklisttemplate', 'Can view Checklist Template'),(577, 142, 'add_checklistitem', 'Can add Checklist Item'),(578, 142, 'change_checklistitem', 'Can change Checklist Item'),(579, 142, 'delete_checklistitem', 'Can delete Checklist Item'),(580, 142, 'view_checklistitem', 'Can view Checklist Item'),(581, 140, 'add_checklistinstance', 'Can add Checklist Instance'),(582, 140, 'change_checklistinstance', 'Can change Checklist Instance'),(583, 140, 'delete_checklistinstance', 'Can delete Checklist Instance'),(584, 140, 'view_checklistinstance', 'Can view Checklist Instance'),(585, 141, 'add_checklistitemstatus', 'Can add Checklist Item Status'),(586, 141, 'change_checklistitemstatus', 'Can change Checklist Item Status'),(587, 141, 'delete_checklistitemstatus', 'Can delete Checklist Item Status'),(588, 141, 'view_checklistitemstatus', 'Can view Checklist Item Status'),(589, 148, 'add_workflow', 'Can add workflow'),(590, 148, 'change_workflow', 'Can change workflow'),(591, 148, 'delete_workflow', 'Can delete workflow'),(592, 148, 'view_workflow', 'Can view workflow'),(593, 149, 'add_workflowcheckpoint', 'Can add workflow checkpoint'),(594, 149, 'change_workflowcheckpoint', 'Can change workflow checkpoint'),(595, 149, 'delete_workflowcheckpoint', 'Can delete workflow checkpoint'),(596, 149, 'view_workflowcheckpoint', 'Can view workflow checkpoint'),(597, 150, 'add_llm', 'Can add LLM'),(598, 150, 'change_llm', 'Can change LLM'),(599, 150, 'delete_llm', 'Can delete LLM'),(600, 150, 'view_llm', 'Can view LLM'),(601, 151, 'add_workflowdomain', 'Can add workflow domain'),(602, 151, 'change_workflowdomain', 'Can change workflow domain'),(603, 151, 'delete_workflowdomain', 'Can delete workflow domain'),(604, 151, 'view_workflowdomain', 'Can view workflow domain'),(605, 152, 'add_projecttype', 'Can add project type'),(606, 152, 'change_projecttype', 'Can change project type'),(607, 152, 'delete_projecttype', 'Can delete project type'),(608, 152, 'view_projecttype', 'Can view project type'),(609, 153, 'add_navigationsection', 'Can add navigation section'),(610, 153, 'change_navigationsection', 'Can change navigation section'),(611, 153, 'delete_navigationsection', 'Can delete navigation section'),(612, 153, 'view_navigationsection', 'Can view navigation section'),(613, 154, 'add_workflowtemplate', 'Can add workflow template'),(614, 154, 'change_workflowtemplate', 'Can change workflow template'),(615, 154, 'delete_workflowtemplate', 'Can delete workflow template'),(616, 154, 'view_workflowtemplate', 'Can view workflow template'),(617, 155, 'add_usernavigationpreference', 'Can add user navigation preference'),(618, 155, 'change_usernavigationpreference', 'Can change user navigation preference'),(619, 155, 'delete_usernavigationpreference', 'Can delete user navigation preference'),(620, 155, 'view_usernavigationpreference', 'Can view user navigation preference'),(621, 156, 'add_navigationitem', 'Can add navigation item'),(622, 156, 'change_navigationitem', 'Can change navigation item'),(623, 156, 'delete_navigationitem', 'Can delete navigation item'),(624, 156, 'view_navigationitem', 'Can view navigation item'),(625, 157, 'add_comicpanels', 'Can add Comic Panel'),(626, 157, 'change_comicpanels', 'Can change Comic Panel'),(627, 157, 'delete_comicpanels', 'Can delete Comic Panel'),(628, 157, 'view_comicpanels', 'Can view Comic Panel'),(629, 158, 'add_comicdialogues', 'Can add Comic Dialogue'),(630, 158, 'change_comicdialogues', 'Can change Comic Dialogue'),(631, 158, 'delete_comicdialogues', 'Can delete Comic Dialogue'),(632, 158, 'view_comicdialogues', 'Can view Comic Dialogue'),(633, 7, 'add_domainart', 'Can add Domain Art'),(634, 7, 'change_domainart', 'Can change Domain Art'),(635, 7, 'delete_domainart', 'Can delete Domain Art'),(636, 7, 'view_domainart', 'Can view Domain Art'),(637, 8, 'add_agent', 'Can add Agent'),(638, 8, 'change_agent', 'Can change Agent'),(639, 8, 'delete_agent', 'Can delete Agent'),(640, 8, 'view_agent', 'Can view Agent'),(641, 9, 'add_agentexecution', 'Can add Agent Execution'),(642, 9, 'change_agentexecution', 'Can change Agent Execution'),(643, 9, 'delete_agentexecution', 'Can delete Agent Execution'),(644, 9, 'view_agentexecution', 'Can view Agent Execution'),(645, 10, 'add_contentitem', 'Can add Content Item'),(646, 10, 'change_contentitem', 'Can change Content Item'),(647, 10, 'delete_contentitem', 'Can delete Content Item'),(648, 10, 'view_contentitem', 'Can view Content Item'),(649, 11, 'add_customer', 'Can add Customer'),(650, 11, 'change_customer', 'Can change Customer'),(651, 11, 'delete_customer', 'Can delete Customer'),(652, 11, 'view_customer', 'Can view Customer'),(653, 12, 'add_bookstatus', 'Can add Book Status'),(654, 12, 'change_bookstatus', 'Can change Book Status'),(655, 12, 'delete_bookstatus', 'Can delete Book Status'),(656, 12, 'view_bookstatus', 'Can view Book Status'),(657, 13, 'add_domainphase', 'Can add Domain Phase'),(658, 13, 'change_domainphase', 'Can change Domain Phase'),(659, 13, 'delete_domainphase', 'Can delete Domain Phase'),(660, 13, 'view_domainphase', 'Can view Domain Phase'),(661, 14, 'add_domainsection', 'Can add Domain Section'),(662, 14, 'change_domainsection', 'Can change Domain Section'),(663, 14, 'delete_domainsection', 'Can delete Domain Section'),(664, 14, 'view_domainsection', 'Can view Domain Section'),(665, 15, 'add_domainsectionitem', 'Can add Domain Section Item'),(666, 15, 'change_domainsectionitem', 'Can change Domain Section Item'),(667, 15, 'delete_domainsectionitem', 'Can delete Domain Section Item'),(668, 15, 'view_domainsectionitem', 'Can view Domain Section Item'),(669, 16, 'add_domaintype', 'Can add Domain Type'),(670, 16, 'change_domaintype', 'Can change Domain Type'),(671, 16, 'delete_domaintype', 'Can delete Domain Type'),(672, 16, 'view_domaintype', 'Can view Domain Type'),(673, 17, 'add_domainproject', 'Can add Domain Project'),(674, 17, 'change_domainproject', 'Can change Domain Project'),(675, 17, 'delete_domainproject', 'Can delete Domain Project'),(676, 17, 'view_domainproject', 'Can view Domain Project'),(677, 18, 'add_genre', 'Can add Genre'),(678, 18, 'change_genre', 'Can change Genre'),(679, 18, 'delete_genre', 'Can delete Genre'),(680, 18, 'view_genre', 'Can view Genre'),(681, 19, 'add_location', 'Can add Location'),(682, 19, 'change_location', 'Can change Location'),(683, 19, 'delete_location', 'Can delete Location'),(684, 19, 'view_location', 'Can view Location'),(685, 20, 'add_pluginregistry', 'Can add Plugin'),(686, 20, 'change_pluginregistry', 'Can change Plugin'),(687, 20, 'delete_pluginregistry', 'Can delete Plugin'),(688, 20, 'view_pluginregistry', 'Can view Plugin'),(689, 21, 'add_pluginexecution', 'Can add Plugin Execution'),(690, 21, 'change_pluginexecution', 'Can change Plugin Execution'),(691, 21, 'delete_pluginexecution', 'Can delete Plugin Execution'),(692, 21, 'view_pluginexecution', 'Can view Plugin Execution'),(693, 22, 'add_prompttemplate', 'Can add Prompt Template'),(694, 22, 'change_prompttemplate', 'Can change Prompt Template'),(695, 22, 'delete_prompttemplate', 'Can delete Prompt Template'),(696, 22, 'view_prompttemplate', 'Can view Prompt Template'),(697, 23, 'add_promptexecution', 'Can add Prompt Execution'),(698, 23, 'change_promptexecution', 'Can change Prompt Execution'),(699, 23, 'delete_promptexecution', 'Can delete Prompt Execution'),(700, 23, 'view_promptexecution', 'Can view Prompt Execution'),(701, 24, 'add_pluginconfiguration', 'Can add Plugin Configuration'),(702, 24, 'change_pluginconfiguration', 'Can change Plugin Configuration'),(703, 24, 'delete_pluginconfiguration', 'Can delete Plugin Configuration'),(704, 24, 'view_pluginconfiguration', 'Can view Plugin Configuration'),(705, 25, 'add_handler', 'Can add Handler'),(706, 25, 'change_handler', 'Can change Handler'),(707, 25, 'delete_handler', 'Can delete Handler'),(708, 25, 'view_handler', 'Can view Handler'),(709, 26, 'add_promptversion', 'Can add Prompt Version'),(710, 26, 'change_promptversion', 'Can change Prompt Version'),(711, 26, 'delete_promptversion', 'Can delete Prompt Version'),(712, 26, 'view_promptversion', 'Can view Prompt Version'),(713, 27, 'add_bookproject', 'Can add Book Project'),(714, 27, 'change_bookproject', 'Can change Book Project'),(715, 27, 'delete_bookproject', 'Can delete Book Project'),(716, 27, 'view_bookproject', 'Can view Book Project'),(717, 28, 'add_chapter', 'Can add Chapter'),(718, 28, 'change_chapter', 'Can change Chapter'),(719, 28, 'delete_chapter', 'Can delete Chapter'),(720, 28, 'view_chapter', 'Can view Chapter'),(721, 29, 'add_bookcharacter', 'Can add Book Character'),(722, 29, 'change_bookcharacter', 'Can change Book Character'),(723, 29, 'delete_bookcharacter', 'Can delete Book Character'),(724, 29, 'view_bookcharacter', 'Can view Book Character'),(725, 30, 'add_character', 'Can add Character'),(726, 30, 'change_character', 'Can change Character'),(727, 30, 'delete_character', 'Can delete Character'),(728, 30, 'view_character', 'Can view Character'),(729, 31, 'add_idea', 'Can add Idea'),(730, 31, 'change_idea', 'Can change Idea'),(731, 31, 'delete_idea', 'Can delete Idea'),(732, 31, 'view_idea', 'Can view Idea'),(733, 32, 'add_world', 'Can add World'),(734, 32, 'change_world', 'Can change World'),(735, 32, 'delete_world', 'Can delete World'),(736, 32, 'view_world', 'Can view World'),(737, 33, 'add_analysisjob', 'Can add Analysis Job'),(738, 33, 'change_analysisjob', 'Can change Analysis Job'),(739, 33, 'delete_analysisjob', 'Can delete Analysis Job'),(740, 33, 'view_analysisjob', 'Can view Analysis Job'),(741, 34, 'add_analysisreport', 'Can add Analysis Report'),(742, 34, 'change_analysisreport', 'Can change Analysis Report'),(743, 34, 'delete_analysisreport', 'Can delete Analysis Report'),(744, 34, 'view_analysisreport', 'Can view Analysis Report'),(745, 35, 'add_drawingfile', 'Can add Drawing File'),(746, 35, 'change_drawingfile', 'Can change Drawing File'),(747, 35, 'delete_drawingfile', 'Can delete Drawing File'),(748, 35, 'view_drawingfile', 'Can view Drawing File'),(749, 36, 'add_analysisresult', 'Can add Analysis Result'),(750, 36, 'change_analysisresult', 'Can change Analysis Result'),(751, 36, 'delete_analysisresult', 'Can delete Analysis Result'),(752, 36, 'view_analysisresult', 'Can view Analysis Result'),(753, 37, 'add_documenttypemodel', 'Can add Document Type'),(754, 37, 'change_documenttypemodel', 'Can change Document Type'),(755, 37, 'delete_documenttypemodel', 'Can delete Document Type'),(756, 37, 'view_documenttypemodel', 'Can view Document Type'),(757, 38, 'add_facilitytype', 'Can add Facility Type'),(758, 38, 'change_facilitytype', 'Can change Facility Type'),(759, 38, 'delete_facilitytype', 'Can delete Facility Type'),(760, 38, 'view_facilitytype', 'Can view Facility Type'),(761, 39, 'add_processingstatustype', 'Can add Processing Status Type'),(762, 39, 'change_processingstatustype', 'Can change Processing Status Type'),(763, 39, 'delete_processingstatustype', 'Can delete Processing Status Type'),(764, 39, 'view_processingstatustype', 'Can view Processing Status Type'),(765, 40, 'add_zonetype', 'Can add Zone Type'),(766, 40, 'change_zonetype', 'Can change Zone Type'),(767, 40, 'delete_zonetype', 'Can delete Zone Type'),(768, 40, 'view_zonetype', 'Can view Zone Type'),(769, 41, 'add_building', 'Can add Building'),(770, 41, 'change_building', 'Can change Building'),(771, 41, 'delete_building', 'Can delete Building'),(772, 41, 'view_building', 'Can view Building'),(773, 42, 'add_exschutzdocument', 'Can add ExSchutz Document'),(774, 42, 'change_exschutzdocument', 'Can change ExSchutz Document'),(775, 42, 'delete_exschutzdocument', 'Can delete ExSchutz Document'),(776, 42, 'view_exschutzdocument', 'Can view ExSchutz Document'),(777, 43, 'add_auditlog', 'Can add Audit Log Entry'),(778, 43, 'change_auditlog', 'Can change Audit Log Entry'),(779, 43, 'delete_auditlog', 'Can delete Audit Log Entry'),(780, 43, 'view_auditlog', 'Can view Audit Log Entry'),(781, 44, 'add_facility', 'Can add Facility'),(782, 44, 'change_facility', 'Can change Facility'),(783, 44, 'delete_facility', 'Can delete Facility'),(784, 44, 'view_facility', 'Can view Facility'),(785, 45, 'add_gefahrstoff', 'Can add Gefahrstoff'),(786, 45, 'change_gefahrstoff', 'Can change Gefahrstoff'),(787, 45, 'delete_gefahrstoff', 'Can delete Gefahrstoff'),(788, 45, 'view_gefahrstoff', 'Can view Gefahrstoff'),(789, 46, 'add_hazmatcatalog', 'Can add Hazardous Material (Catalog)'),(790, 46, 'change_hazmatcatalog', 'Can change Hazardous Material (Catalog)'),(791, 46, 'delete_hazmatcatalog', 'Can delete Hazardous Material (Catalog)'),(792, 46, 'view_hazmatcatalog', 'Can view Hazardous Material (Catalog)'),(793, 47, 'add_facilityhazmat', 'Can add Facility Hazmat Usage'),(794, 47, 'change_facilityhazmat', 'Can change Facility Hazmat Usage'),(795, 47, 'delete_facilityhazmat', 'Can delete Facility Hazmat Usage'),(796, 47, 'view_facilityhazmat', 'Can view Facility Hazmat Usage'),(797, 48, 'add_schutzmaßnahme', 'Can add Schutzmaßnahme'),(798, 48, 'change_schutzmaßnahme', 'Can change Schutzmaßnahme'),(799, 48, 'delete_schutzmaßnahme', 'Can delete Schutzmaßnahme'),(800, 48, 'view_schutzmaßnahme', 'Can view Schutzmaßnahme'),(801, 49, 'add_exzone', 'Can add Ex-Zone'),(802, 49, 'change_exzone', 'Can change Ex-Zone'),(803, 49, 'delete_exzone', 'Can delete Ex-Zone'),(804, 49, 'view_exzone', 'Can view Ex-Zone'),(805, 50, 'add_assessment', 'Can add Assessment'),(806, 50, 'change_assessment', 'Can change Assessment'),(807, 50, 'delete_assessment', 'Can delete Assessment'),(808, 50, 'view_assessment', 'Can view Assessment'),(809, 51, 'add_checklisttemplate', 'Can add Checklist Template'),(810, 51, 'change_checklisttemplate', 'Can change Checklist Template'),(811, 51, 'delete_checklisttemplate', 'Can delete Checklist Template'),(812, 51, 'view_checklisttemplate', 'Can view Checklist Template'),(813, 52, 'add_checklistitem', 'Can add Checklist Item'),(814, 52, 'change_checklistitem', 'Can change Checklist Item'),(815, 52, 'delete_checklistitem', 'Can delete Checklist Item'),(816, 52, 'view_checklistitem', 'Can view Checklist Item'),(817, 53, 'add_checklistinstance', 'Can add Checklist Instance'),(818, 53, 'change_checklistinstance', 'Can change Checklist Instance'),(819, 53, 'delete_checklistinstance', 'Can delete Checklist Instance'),(820, 53, 'view_checklistinstance', 'Can view Checklist Instance'),(821, 54, 'add_checklistitemstatus', 'Can add Checklist Item Status'),(822, 54, 'change_checklistitemstatus', 'Can change Checklist Item Status'),(823, 54, 'delete_checklistitemstatus', 'Can delete Checklist Item Status'),(824, 54, 'view_checklistitemstatus', 'Can view Checklist Item Status'),(825, 55, 'add_workflow', 'Can add workflow'),(826, 55, 'change_workflow', 'Can change workflow'),(827, 55, 'delete_workflow', 'Can delete workflow'),(828, 55, 'view_workflow', 'Can view workflow'),(829, 56, 'add_workflowcheckpoint', 'Can add workflow checkpoint'),(830, 56, 'change_workflowcheckpoint', 'Can change workflow checkpoint'),(831, 56, 'delete_workflowcheckpoint', 'Can delete workflow checkpoint'),(832, 56, 'view_workflowcheckpoint', 'Can view workflow checkpoint'),(833, 57, 'add_agentexecutions', 'Can add agent executions'),(834, 57, 'change_agentexecutions', 'Can change agent executions'),(835, 57, 'delete_agentexecutions', 'Can delete agent executions'),(836, 57, 'view_agentexecutions', 'Can view agent executions'),(837, 58, 'add_agents', 'Can add agents'),(838, 58, 'change_agents', 'Can change agents'),(839, 58, 'delete_agents', 'Can delete agents'),(840, 58, 'view_agents', 'Can view agents'),(841, 59, 'add_bookproject', 'Can add Book Project (Legacy)'),(842, 59, 'change_bookproject', 'Can change Book Project (Legacy)'),(843, 59, 'delete_bookproject', 'Can delete Book Project (Legacy)'),(844, 59, 'view_bookproject', 'Can view Book Project (Legacy)'),(845, 60, 'add_llm', 'Can add LLM'),(846, 60, 'change_llm', 'Can change LLM'),(847, 60, 'delete_llm', 'Can delete LLM'),(848, 60, 'view_llm', 'Can view LLM'),(849, 61, 'add_llms', 'Can add llms'),(850, 61, 'change_llms', 'Can change llms'),(851, 61, 'delete_llms', 'Can delete llms'),(852, 61, 'view_llms', 'Can view llms'),(853, 62, 'add_actionhandler', 'Can add Action Handler'),(854, 62, 'change_actionhandler', 'Can change Action Handler'),(855, 62, 'delete_actionhandler', 'Can delete Action Handler'),(856, 62, 'view_actionhandler', 'Can view Action Handler'),(857, 63, 'add_actiontemplate', 'Can add Action Template'),(858, 63, 'change_actiontemplate', 'Can change Action Template'),(859, 63, 'delete_actiontemplate', 'Can delete Action Template'),(860, 63, 'view_actiontemplate', 'Can view Action Template'),(861, 64, 'add_agentaction', 'Can add Agent Action'),(862, 64, 'change_agentaction', 'Can change Agent Action'),(863, 64, 'delete_agentaction', 'Can delete Agent Action'),(864, 64, 'view_agentaction', 'Can view Agent Action'),(865, 65, 'add_agentartifacts', 'Can add agent artifacts'),(866, 65, 'change_agentartifacts', 'Can change agent artifacts'),(867, 65, 'delete_agentartifacts', 'Can delete agent artifacts'),(868, 65, 'view_agentartifacts', 'Can view agent artifacts'),(869, 66, 'add_agenttype', 'Can add Agent Type'),(870, 66, 'change_agenttype', 'Can change Agent Type'),(871, 66, 'delete_agenttype', 'Can delete Agent Type'),(872, 66, 'view_agenttype', 'Can view Agent Type'),(873, 67, 'add_bookchapters', 'Can add book chapters'),(874, 67, 'change_bookchapters', 'Can change book chapters'),(875, 67, 'delete_bookchapters', 'Can delete book chapters'),(876, 67, 'view_bookchapters', 'Can view book chapters'),(877, 68, 'add_booktypephase', 'Can add Book Type Phase'),(878, 68, 'change_booktypephase', 'Can change Book Type Phase'),(879, 68, 'delete_booktypephase', 'Can delete Book Type Phase'),(880, 68, 'view_booktypephase', 'Can view Book Type Phase'),(881, 69, 'add_booktypes', 'Can add book types'),(882, 69, 'change_booktypes', 'Can change book types'),(883, 69, 'delete_booktypes', 'Can delete book types'),(884, 69, 'view_booktypes', 'Can view book types'),(885, 70, 'add_bugfixplan', 'Can add bug fix plan'),(886, 70, 'change_bugfixplan', 'Can change bug fix plan'),(887, 70, 'delete_bugfixplan', 'Can delete bug fix plan'),(888, 70, 'view_bugfixplan', 'Can view bug fix plan'),(889, 71, 'add_chapterrating', 'Can add Chapter Rating'),(890, 71, 'change_chapterrating', 'Can change Chapter Rating'),(891, 71, 'delete_chapterrating', 'Can delete Chapter Rating'),(892, 71, 'view_chapterrating', 'Can view Chapter Rating'),(893, 72, 'add_characters', 'Can add characters'),(894, 72, 'change_characters', 'Can change characters'),(895, 72, 'delete_characters', 'Can delete characters'),(896, 72, 'view_characters', 'Can view characters'),(897, 73, 'add_comicdialogues', 'Can add Comic Dialogue'),(898, 73, 'change_comicdialogues', 'Can change Comic Dialogue'),(899, 73, 'delete_comicdialogues', 'Can delete Comic Dialogue'),(900, 73, 'view_comicdialogues', 'Can view Comic Dialogue'),(901, 74, 'add_comicpanels', 'Can add Comic Panel'),(902, 74, 'change_comicpanels', 'Can change Comic Panel'),(903, 74, 'delete_comicpanels', 'Can delete Comic Panel'),(904, 74, 'view_comicpanels', 'Can view Comic Panel'),(905, 75, 'add_comment', 'Can add Comment'),(906, 75, 'change_comment', 'Can change Comment'),(907, 75, 'delete_comment', 'Can delete Comment'),(908, 75, 'view_comment', 'Can view Comment'),(909, 76, 'add_componentchangelog', 'Can add component change log'),(910, 76, 'change_componentchangelog', 'Can change component change log'),(911, 76, 'delete_componentchangelog', 'Can delete component change log'),(912, 76, 'view_componentchangelog', 'Can view component change log'),(913, 77, 'add_componentregistry', 'Can add Component'),(914, 77, 'change_componentregistry', 'Can change Component'),(915, 77, 'delete_componentregistry', 'Can delete Component'),(916, 77, 'view_componentregistry', 'Can view Component'),(917, 78, 'add_componentusagelog', 'Can add component usage log'),(918, 78, 'change_componentusagelog', 'Can change component usage log'),(919, 78, 'delete_componentusagelog', 'Can delete component usage log'),(920, 78, 'view_componentusagelog', 'Can view component usage log'),(921, 79, 'add_contentblock', 'Can add Content Block'),(922, 79, 'change_contentblock', 'Can change Content Block'),(923, 79, 'delete_contentblock', 'Can delete Content Block'),(924, 79, 'view_contentblock', 'Can view Content Block'),(925, 80, 'add_contextenrichmentlog', 'Can add Context Enrichment Log'),(926, 80, 'change_contextenrichmentlog', 'Can change Context Enrichment Log'),(927, 80, 'delete_contextenrichmentlog', 'Can delete Context Enrichment Log'),(928, 80, 'view_contextenrichmentlog', 'Can view Context Enrichment Log'),(929, 81, 'add_contextschema', 'Can add Context Schema'),(930, 81, 'change_contextschema', 'Can change Context Schema'),(931, 81, 'delete_contextschema', 'Can delete Context Schema'),(932, 81, 'view_contextschema', 'Can view Context Schema'),(933, 82, 'add_contextsource', 'Can add Context Source'),(934, 82, 'change_contextsource', 'Can change Context Source'),(935, 82, 'delete_contextsource', 'Can delete Context Source'),(936, 82, 'view_contextsource', 'Can view Context Source'),(937, 83, 'add_enrichmentresponse', 'Can add Enrichment Response'),(938, 83, 'change_enrichmentresponse', 'Can change Enrichment Response'),(939, 83, 'delete_enrichmentresponse', 'Can delete Enrichment Response'),(940, 83, 'view_enrichmentresponse', 'Can view Enrichment Response'),(941, 84, 'add_featuredocument', 'Can add feature document'),(942, 84, 'change_featuredocument', 'Can change feature document'),(943, 84, 'delete_featuredocument', 'Can delete feature document'),(944, 84, 'view_featuredocument', 'Can view feature document'),(945, 85, 'add_featuredocumentkeyword', 'Can add feature document keyword'),(946, 85, 'change_featuredocumentkeyword', 'Can change feature document keyword'),(947, 85, 'delete_featuredocumentkeyword', 'Can delete feature document keyword'),(948, 85, 'view_featuredocumentkeyword', 'Can view feature document keyword'),(949, 86, 'add_fielddefinition', 'Can add Field Definition'),(950, 86, 'change_fielddefinition', 'Can change Field Definition'),(951, 86, 'delete_fielddefinition', 'Can delete Field Definition'),(952, 86, 'view_fielddefinition', 'Can view Field Definition'),(953, 87, 'add_fieldgroup', 'Can add Field Group'),(954, 87, 'change_fieldgroup', 'Can change Field Group'),(955, 87, 'delete_fieldgroup', 'Can delete Field Group'),(956, 87, 'view_fieldgroup', 'Can view Field Group'),(957, 88, 'add_fieldtemplate', 'Can add Field Template'),(958, 88, 'change_fieldtemplate', 'Can change Field Template'),(959, 88, 'delete_fieldtemplate', 'Can delete Field Template'),(960, 88, 'view_fieldtemplate', 'Can view Field Template'),(961, 89, 'add_fieldusage', 'Can add field usage'),(962, 89, 'change_fieldusage', 'Can change field usage'),(963, 89, 'delete_fieldusage', 'Can delete field usage'),(964, 89, 'view_fieldusage', 'Can view field usage'),(965, 90, 'add_fieldvaluehistory', 'Can add Field Value History'),(966, 90, 'change_fieldvaluehistory', 'Can change Field Value History'),(967, 90, 'delete_fieldvaluehistory', 'Can delete Field Value History'),(968, 90, 'view_fieldvaluehistory', 'Can view Field Value History'),(969, 91, 'add_generatedimage', 'Can add generated image'),(970, 91, 'change_generatedimage', 'Can change generated image'),(971, 91, 'delete_generatedimage', 'Can delete generated image'),(972, 91, 'view_generatedimage', 'Can view generated image'),(973, 92, 'add_generationlog', 'Can add Generation Log'),(974, 92, 'change_generationlog', 'Can change Generation Log'),(975, 92, 'delete_generationlog', 'Can delete Generation Log'),(976, 92, 'view_generationlog', 'Can view Generation Log'),(977, 93, 'add_graphqloperation', 'Can add graph ql operation'),(978, 93, 'change_graphqloperation', 'Can change graph ql operation'),(979, 93, 'delete_graphqloperation', 'Can delete graph ql operation'),(980, 93, 'view_graphqloperation', 'Can view graph ql operation'),(981, 94, 'add_handlerexecution', 'Can add Handler Execution'),(982, 94, 'change_handlerexecution', 'Can change Handler Execution'),(983, 94, 'delete_handlerexecution', 'Can delete Handler Execution'),(984, 94, 'view_handlerexecution', 'Can view Handler Execution'),(985, 96, 'add_illustrationstyle', 'Can add Illustration Style'),(986, 96, 'change_illustrationstyle', 'Can change Illustration Style'),(987, 96, 'delete_illustrationstyle', 'Can delete Illustration Style'),(988, 96, 'view_illustrationstyle', 'Can view Illustration Style'),(989, 97, 'add_imagegenerationbatch', 'Can add Image Generation Batch'),(990, 97, 'change_imagegenerationbatch', 'Can change Image Generation Batch'),(991, 97, 'delete_imagegenerationbatch', 'Can delete Image Generation Batch'),(992, 97, 'view_imagegenerationbatch', 'Can view Image Generation Batch'),(993, 98, 'add_imagestyleprofile', 'Can add Image Style Profile'),(994, 98, 'change_imagestyleprofile', 'Can change Image Style Profile'),(995, 98, 'delete_imagestyleprofile', 'Can delete Image Style Profile'),(996, 98, 'view_imagestyleprofile', 'Can view Image Style Profile'),(997, 99, 'add_llmpromptexecution', 'Can add Prompt Execution'),(998, 99, 'change_llmpromptexecution', 'Can change Prompt Execution'),(999, 99, 'delete_llmpromptexecution', 'Can delete Prompt Execution'),(1000, 99, 'view_llmpromptexecution', 'Can view Prompt Execution'),(1001, 100, 'add_llmprompttemplate', 'Can add LLM Prompt Template'),(1002, 100, 'change_llmprompttemplate', 'Can change LLM Prompt Template'),(1003, 100, 'delete_llmprompttemplate', 'Can delete LLM Prompt Template'),(1004, 100, 'view_llmprompttemplate', 'Can view LLM Prompt Template'),(1005, 101, 'add_location', 'Can add Location'),(1006, 101, 'change_location', 'Can change Location'),(1007, 101, 'delete_location', 'Can delete Location'),(1008, 101, 'view_location', 'Can view Location'),(1009, 102, 'add_migrationconflict', 'Can add migration conflict'),(1010, 102, 'change_migrationconflict', 'Can change migration conflict'),(1011, 102, 'delete_migrationconflict', 'Can delete migration conflict'),(1012, 102, 'view_migrationconflict', 'Can view migration conflict'),(1013, 103, 'add_migrationregistry', 'Can add migration registry'),(1014, 103, 'change_migrationregistry', 'Can change migration registry'),(1015, 103, 'delete_migrationregistry', 'Can delete migration registry'),(1016, 103, 'view_migrationregistry', 'Can view migration registry'),(1017, 104, 'add_phaseactionconfig', 'Can add Phase Action Configuration'),(1018, 104, 'change_phaseactionconfig', 'Can change Phase Action Configuration'),(1019, 104, 'delete_phaseactionconfig', 'Can delete Phase Action Configuration'),(1020, 104, 'view_phaseactionconfig', 'Can view Phase Action Configuration'),(1021, 105, 'add_phaseagentconfig', 'Can add Phase Agent Configuration'),(1022, 105, 'change_phaseagentconfig', 'Can change Phase Agent Configuration'),(1023, 105, 'delete_phaseagentconfig', 'Can delete Phase Agent Configuration'),(1024, 105, 'view_phaseagentconfig', 'Can view Phase Agent Configuration'),(1025, 106, 'add_plotpoint', 'Can add plot point'),(1026, 106, 'change_plotpoint', 'Can change plot point'),(1027, 106, 'delete_plotpoint', 'Can delete plot point'),(1028, 106, 'view_plotpoint', 'Can view plot point'),(1029, 107, 'add_projectfieldvalue', 'Can add Project Field Value'),(1030, 107, 'change_projectfieldvalue', 'Can change Project Field Value'),(1031, 107, 'delete_projectfieldvalue', 'Can delete Project Field Value'),(1032, 107, 'view_projectfieldvalue', 'Can view Project Field Value'),(1033, 108, 'add_projectphaseaction', 'Can add Project Phase Action'),(1034, 108, 'change_projectphaseaction', 'Can change Project Phase Action'),(1035, 108, 'delete_projectphaseaction', 'Can delete Project Phase Action'),(1036, 108, 'view_projectphaseaction', 'Can view Project Phase Action'),(1037, 109, 'add_projectphasehistory', 'Can add Project Phase History'),(1038, 109, 'change_projectphasehistory', 'Can change Project Phase History'),(1039, 109, 'delete_projectphasehistory', 'Can delete Project Phase History'),(1040, 109, 'view_projectphasehistory', 'Can view Project Phase History'),(1041, 110, 'add_projecttypephase', 'Can add Project Type Phase'),(1042, 110, 'change_projecttypephase', 'Can change Project Type Phase'),(1043, 110, 'delete_projecttypephase', 'Can delete Project Type Phase'),(1044, 110, 'view_projecttypephase', 'Can view Project Type Phase'),(1045, 111, 'add_promptexecution', 'Can add Prompt Execution'),(1046, 111, 'change_promptexecution', 'Can change Prompt Execution'),(1047, 111, 'delete_promptexecution', 'Can delete Prompt Execution'),(1048, 111, 'view_promptexecution', 'Can view Prompt Execution'),(1049, 112, 'add_prompttemplatelegacy', 'Can add Prompt Template (Legacy)'),(1050, 112, 'change_prompttemplatelegacy', 'Can change Prompt Template (Legacy)'),(1051, 112, 'delete_prompttemplatelegacy', 'Can delete Prompt Template (Legacy)'),(1052, 112, 'view_prompttemplatelegacy', 'Can view Prompt Template (Legacy)'),(1053, 113, 'add_prompttemplatetest', 'Can add Prompt Template Test'),(1054, 113, 'change_prompttemplatetest', 'Can change Prompt Template Test'),(1055, 113, 'delete_prompttemplatetest', 'Can delete Prompt Template Test'),(1056, 113, 'view_prompttemplatetest', 'Can view Prompt Template Test'),(1057, 114, 'add_queryperformancelog', 'Can add query performance log'),(1058, 114, 'change_queryperformancelog', 'Can change query performance log'),(1059, 114, 'delete_queryperformancelog', 'Can delete query performance log'),(1060, 114, 'view_queryperformancelog', 'Can view query performance log'),(1061, 115, 'add_requirementtestlink', 'Can add requirement test link'),(1062, 115, 'change_requirementtestlink', 'Can change requirement test link'),(1063, 115, 'delete_requirementtestlink', 'Can delete requirement test link'),(1064, 115, 'view_requirementtestlink', 'Can view requirement test link'),(1065, 116, 'add_reviewparticipant', 'Can add Review Participant'),(1066, 116, 'change_reviewparticipant', 'Can change Review Participant'),(1067, 116, 'delete_reviewparticipant', 'Can delete Review Participant'),(1068, 116, 'view_reviewparticipant', 'Can view Review Participant'),(1069, 117, 'add_reviewround', 'Can add Review Round'),(1070, 117, 'change_reviewround', 'Can change Review Round'),(1071, 117, 'delete_reviewround', 'Can delete Review Round'),(1072, 117, 'view_reviewround', 'Can view Review Round'),(1073, 118, 'add_storyarc', 'Can add story arc'),(1074, 118, 'change_storyarc', 'Can change story arc'),(1075, 118, 'delete_storyarc', 'Can delete story arc'),(1076, 118, 'view_storyarc', 'Can view story arc'),(1077, 119, 'add_storybible', 'Can add Story Bible'),(1078, 119, 'change_storybible', 'Can change Story Bible'),(1079, 119, 'delete_storybible', 'Can delete Story Bible'),(1080, 119, 'view_storybible', 'Can view Story Bible'),(1081, 120, 'add_storychapter', 'Can add Story Chapter'),(1082, 120, 'change_storychapter', 'Can change Story Chapter'),(1083, 120, 'delete_storychapter', 'Can delete Story Chapter'),(1084, 120, 'view_storychapter', 'Can view Story Chapter'),(1085, 121, 'add_storymemory', 'Can add Story Memory'),(1086, 121, 'change_storymemory', 'Can change Story Memory'),(1087, 121, 'delete_storymemory', 'Can delete Story Memory'),(1088, 121, 'view_storymemory', 'Can view Story Memory'),(1089, 122, 'add_storyproject', 'Can add Story Project'),(1090, 122, 'change_storyproject', 'Can change Story Project'),(1091, 122, 'delete_storyproject', 'Can delete Story Project'),(1092, 122, 'view_storyproject', 'Can view Story Project'),(1093, 123, 'add_storystrand', 'Can add Story Strand'),(1094, 123, 'change_storystrand', 'Can change Story Strand'),(1095, 123, 'delete_storystrand', 'Can delete Story Strand'),(1096, 123, 'view_storystrand', 'Can view Story Strand'),(1097, 124, 'add_targetaudience', 'Can add Target Audience'),(1098, 124, 'change_targetaudience', 'Can change Target Audience'),(1099, 124, 'delete_targetaudience', 'Can delete Target Audience'),(1100, 124, 'view_targetaudience', 'Can view Target Audience'),(1101, 125, 'add_templatefield', 'Can add template field'),(1102, 125, 'change_templatefield', 'Can change template field'),(1103, 125, 'delete_templatefield', 'Can delete template field'),(1104, 125, 'view_templatefield', 'Can view template field'),(1105, 126, 'add_testbug', 'Can add test bug'),(1106, 126, 'change_testbug', 'Can change test bug'),(1107, 126, 'delete_testbug', 'Can delete test bug'),(1108, 126, 'view_testbug', 'Can view test bug'),(1109, 127, 'add_testcase', 'Can add test case'),(1110, 127, 'change_testcase', 'Can change test case'),(1111, 127, 'delete_testcase', 'Can delete test case'),(1112, 127, 'view_testcase', 'Can view test case'),(1113, 128, 'add_testcoveragereport', 'Can add test coverage report'),(1114, 128, 'change_testcoveragereport', 'Can change test coverage report'),(1115, 128, 'delete_testcoveragereport', 'Can delete test coverage report'),(1116, 128, 'view_testcoveragereport', 'Can view test coverage report'),(1117, 129, 'add_testexecution', 'Can add test execution'),(1118, 129, 'change_testexecution', 'Can change test execution'),(1119, 129, 'delete_testexecution', 'Can delete test execution'),(1120, 129, 'view_testexecution', 'Can view test execution'),(1121, 130, 'add_testlog', 'Can add test log'),(1122, 130, 'change_testlog', 'Can change test log'),(1123, 130, 'delete_testlog', 'Can delete test log'),(1124, 130, 'view_testlog', 'Can view test log'),(1125, 131, 'add_testrequirement', 'Can add test requirement'),(1126, 131, 'change_testrequirement', 'Can change test requirement'),(1127, 131, 'delete_testrequirement', 'Can delete test requirement'),(1128, 131, 'view_testrequirement', 'Can view test requirement'),(1129, 132, 'add_testscreenshot', 'Can add test screenshot'),(1130, 132, 'change_testscreenshot', 'Can change test screenshot'),(1131, 132, 'delete_testscreenshot', 'Can delete test screenshot'),(1132, 132, 'view_testscreenshot', 'Can view test screenshot'),(1133, 133, 'add_testsession', 'Can add test session'),(1134, 133, 'change_testsession', 'Can change test session'),(1135, 133, 'delete_testsession', 'Can delete test session'),(1136, 133, 'view_testsession', 'Can view test session'),(1137, 134, 'add_tooldefinition', 'Can add Tool Definition'),(1138, 134, 'change_tooldefinition', 'Can change Tool Definition'),(1139, 134, 'delete_tooldefinition', 'Can delete Tool Definition'),(1140, 134, 'view_tooldefinition', 'Can view Tool Definition'),(1141, 135, 'add_toolexecution', 'Can add Tool Execution'),(1142, 135, 'change_toolexecution', 'Can change Tool Execution'),(1143, 135, 'delete_toolexecution', 'Can delete Tool Execution'),(1144, 135, 'view_toolexecution', 'Can view Tool Execution'),(1145, 136, 'add_workflowphase', 'Can add Workflow Phase'),(1146, 136, 'change_workflowphase', 'Can change Workflow Phase'),(1147, 136, 'delete_workflowphase', 'Can delete Workflow Phase'),(1148, 136, 'view_workflowphase', 'Can view Workflow Phase'),(1149, 137, 'add_workflowphasestep', 'Can add Workflow Template Phase'),(1150, 137, 'change_workflowphasestep', 'Can change Workflow Template Phase'),(1151, 137, 'delete_workflowphasestep', 'Can delete Workflow Template Phase'),(1152, 137, 'view_workflowphasestep', 'Can view Workflow Template Phase'),(1153, 138, 'add_workflowtemplate', 'Can add Workflow Template'),(1154, 138, 'change_workflowtemplate', 'Can change Workflow Template'),(1155, 138, 'delete_workflowtemplate', 'Can delete Workflow Template'),(1156, 138, 'view_workflowtemplate', 'Can view Workflow Template'),(1157, 139, 'add_worldrule', 'Can add World Rule'),(1158, 139, 'change_worldrule', 'Can change World Rule'),(1159, 139, 'delete_worldrule', 'Can delete World Rule'),(1160, 139, 'view_worldrule', 'Can view World Rule'),(1161, 140, 'add_worlds', 'Can add worlds'),(1162, 140, 'change_worlds', 'Can change worlds'),(1163, 140, 'delete_worlds', 'Can delete worlds'),(1164, 140, 'view_worlds', 'Can view worlds'),(1165, 141, 'add_worldsetting', 'Can add World Setting'),(1166, 141, 'change_worldsetting', 'Can change World Setting'),(1167, 141, 'delete_worldsetting', 'Can delete World Setting'),(1168, 141, 'view_worldsetting', 'Can view World Setting'),(1169, 142, 'add_writingstatus', 'Can add Writing Status'),(1170, 142, 'change_writingstatus', 'Can change Writing Status'),(1171, 142, 'delete_writingstatus', 'Can delete Writing Status'),(1172, 142, 'view_writingstatus', 'Can view Writing Status'),(1173, 143, 'add_workflowdomain', 'Can add workflow domain'),(1174, 143, 'change_workflowdomain', 'Can change workflow domain'),(1175, 143, 'delete_workflowdomain', 'Can delete workflow domain'),(1176, 143, 'view_workflowdomain', 'Can view workflow domain'),(1177, 144, 'add_projecttype', 'Can add project type'),(1178, 144, 'change_projecttype', 'Can change project type'),(1179, 144, 'delete_projecttype', 'Can delete project type'),(1180, 144, 'view_projecttype', 'Can view project type'),(1181, 145, 'add_navigationsection', 'Can add navigation section'),(1182, 145, 'change_navigationsection', 'Can change navigation section'),(1183, 145, 'delete_navigationsection', 'Can delete navigation section'),(1184, 145, 'view_navigationsection', 'Can view navigation section'),(1185, 146, 'add_workflowtemplate', 'Can add workflow template'),(1186, 146, 'change_workflowtemplate', 'Can change workflow template'),(1187, 146, 'delete_workflowtemplate', 'Can delete workflow template'),(1188, 146, 'view_workflowtemplate', 'Can view workflow template'),(1189, 147, 'add_usernavigationpreference', 'Can add user navigation preference'),(1190, 147, 'change_usernavigationpreference', 'Can change user navigation preference'),(1191, 147, 'delete_usernavigationpreference', 'Can delete user navigation preference'),(1192, 147, 'view_usernavigationpreference', 'Can view user navigation preference'),(1193, 148, 'add_navigationitem', 'Can add navigation item'),(1194, 148, 'change_navigationitem', 'Can change navigation item'),(1195, 148, 'delete_navigationitem', 'Can delete navigation item'),(1196, 148, 'view_navigationitem', 'Can view navigation item'),(1197, 149, 'add_customdomain', 'Can add Custom Domain'),(1198, 149, 'change_customdomain', 'Can change Custom Domain'),(1199, 149, 'delete_customdomain', 'Can delete Custom Domain'),(1200, 149, 'view_customdomain', 'Can view Custom Domain'),(1201, 150, 'add_phase', 'Can add GenAgent Phase'),(1202, 150, 'change_phase', 'Can change GenAgent Phase'),(1203, 150, 'delete_phase', 'Can delete GenAgent Phase'),(1204, 150, 'view_phase', 'Can view GenAgent Phase'),(1205, 151, 'add_action', 'Can add GenAgent Action'),(1206, 151, 'change_action', 'Can change GenAgent Action'),(1207, 151, 'delete_action', 'Can delete GenAgent Action'),(1208, 151, 'view_action', 'Can view GenAgent Action'),(1209, 152, 'add_executionlog', 'Can add GenAgent Execution Log'),(1210, 152, 'change_executionlog', 'Can change GenAgent Execution Log'),(1211, 152, 'delete_executionlog', 'Can delete GenAgent Execution Log'),(1212, 152, 'view_executionlog', 'Can view GenAgent Execution Log'),(1213, 153, 'add_customer', 'Can add Medical Translation Customer'),(1214, 153, 'change_customer', 'Can change Medical Translation Customer'),(1215, 153, 'delete_customer', 'Can delete Medical Translation Customer'),(1216, 153, 'view_customer', 'Can view Medical Translation Customer'),(1217, 154, 'add_presentation', 'Can add Presentation'),(1218, 154, 'change_presentation', 'Can change Presentation'),(1219, 154, 'delete_presentation', 'Can delete Presentation'),(1220, 154, 'view_presentation', 'Can view Presentation'),(1221, 155, 'add_presentationtext', 'Can add Presentation Text'),(1222, 155, 'change_presentationtext', 'Can change Presentation Text'),(1223, 155, 'delete_presentationtext', 'Can delete Presentation Text'),(1224, 155, 'view_presentationtext', 'Can view Presentation Text'),(1225, 156, 'add_templatecollection', 'Can add Template Collection'),(1226, 156, 'change_templatecollection', 'Can change Template Collection'),(1227, 156, 'delete_templatecollection', 'Can delete Template Collection'),(1228, 156, 'view_templatecollection', 'Can view Template Collection'),(1229, 157, 'add_presentation', 'Can add presentation'),(1230, 157, 'change_presentation', 'Can change presentation'),(1231, 157, 'delete_presentation', 'Can delete presentation'),(1232, 157, 'view_presentation', 'Can view presentation'),(1233, 158, 'add_enhancement', 'Can add enhancement'),(1234, 158, 'change_enhancement', 'Can change enhancement'),(1235, 158, 'delete_enhancement', 'Can delete enhancement'),(1236, 158, 'view_enhancement', 'Can view enhancement'),(1237, 159, 'add_designprofile', 'Can add design profile'),(1238, 159, 'change_designprofile', 'Can change design profile'),(1239, 159, 'delete_designprofile', 'Can delete design profile'),(1240, 159, 'view_designprofile', 'Can view design profile'),(1241, 160, 'add_previewslide', 'Can add preview slide'),(1242, 160, 'change_previewslide', 'Can change preview slide'),(1243, 160, 'delete_previewslide', 'Can delete preview slide'),(1244, 160, 'view_previewslide', 'Can view preview slide'),(1245, 161, 'add_historyentry', 'Can add history entry'),(1246, 161, 'change_historyentry', 'Can change history entry'),(1247, 161, 'delete_historyentry', 'Can delete history entry'),(1248, 161, 'view_historyentry', 'Can view history entry'),(1249, 162, 'add_datasourceconfig', 'Can add Data Source Configuration'),(1250, 162, 'change_datasourceconfig', 'Can change Data Source Configuration'),(1251, 162, 'delete_datasourceconfig', 'Can delete Data Source Configuration'),(1252, 162, 'view_datasourceconfig', 'Can view Data Source Configuration'),(1253, 163, 'add_datasourcemetric', 'Can add Data Source Metric'),(1254, 163, 'change_datasourcemetric', 'Can change Data Source Metric'),(1255, 163, 'delete_datasourcemetric', 'Can delete Data Source Metric'),(1256, 163, 'view_datasourcemetric', 'Can view Data Source Metric'),(1257, 164, 'add_substancedataimport', 'Can add Substance Data Import'),(1258, 164, 'change_substancedataimport', 'Can change Substance Data Import'),(1259, 164, 'delete_substancedataimport', 'Can delete Substance Data Import'),(1260, 164, 'view_substancedataimport', 'Can view Substance Data Import'),(1261, 165, 'add_incidentseverity', 'Can add Vorfall-Schweregrad'),(1262, 165, 'change_incidentseverity', 'Can change Vorfall-Schweregrad'),(1263, 165, 'delete_incidentseverity', 'Can delete Vorfall-Schweregrad'),(1264, 165, 'view_incidentseverity', 'Can view Vorfall-Schweregrad'),(1265, 166, 'add_compliancetag', 'Can add Tag'),(1266, 166, 'change_compliancetag', 'Can change Tag'),(1267, 166, 'delete_compliancetag', 'Can delete Tag'),(1268, 166, 'view_compliancetag', 'Can view Tag'),(1269, 167, 'add_complianceauditlog', 'Can add Audit-Eintrag'),(1270, 167, 'change_complianceauditlog', 'Can change Audit-Eintrag'),(1271, 167, 'delete_complianceauditlog', 'Can delete Audit-Eintrag'),(1272, 167, 'view_complianceauditlog', 'Can view Audit-Eintrag'),(1273, 168, 'add_priority', 'Can add Priorität'),(1274, 168, 'change_priority', 'Can change Priorität'),(1275, 168, 'delete_priority', 'Can delete Priorität'),(1276, 168, 'view_priority', 'Can view Priorität'),(1277, 169, 'add_risklevel', 'Can add Risikostufe'),(1278, 169, 'change_risklevel', 'Can change Risikostufe'),(1279, 169, 'delete_risklevel', 'Can delete Risikostufe'),(1280, 169, 'view_risklevel', 'Can view Risikostufe'),(1281, 170, 'add_compliancetaggeditem', 'Can add Tagged Item'),(1282, 170, 'change_compliancetaggeditem', 'Can change Tagged Item'),(1283, 170, 'delete_compliancetaggeditem', 'Can delete Tagged Item'),(1284, 170, 'view_compliancetaggeditem', 'Can view Tagged Item'),(1285, 171, 'add_compliancestatus', 'Can add Status'),(1286, 171, 'change_compliancestatus', 'Can change Status'),(1287, 171, 'delete_compliancestatus', 'Can delete Status'),(1288, 171, 'view_compliancestatus', 'Can view Status'),(1289, 172, 'add_branche', 'Can add Branche'),(1290, 172, 'change_branche', 'Can change Branche'),(1291, 172, 'delete_branche', 'Can delete Branche'),(1292, 172, 'view_branche', 'Can view Branche'),(1293, 173, 'add_vorfall', 'Can add Datenschutzvorfall'),(1294, 173, 'change_vorfall', 'Can change Datenschutzvorfall'),(1295, 173, 'delete_vorfall', 'Can delete Datenschutzvorfall'),(1296, 173, 'view_vorfall', 'Can view Datenschutzvorfall'),(1297, 174, 'add_verarbeitung', 'Can add Verarbeitungstätigkeit'),(1298, 174, 'change_verarbeitung', 'Can change Verarbeitungstätigkeit'),(1299, 174, 'delete_verarbeitung', 'Can delete Verarbeitungstätigkeit'),(1300, 174, 'view_verarbeitung', 'Can view Verarbeitungstätigkeit'),(1301, 175, 'add_rechtsform', 'Can add Rechtsform'),(1302, 175, 'change_rechtsform', 'Can change Rechtsform'),(1303, 175, 'delete_rechtsform', 'Can delete Rechtsform'),(1304, 175, 'view_rechtsform', 'Can view Rechtsform'),(1305, 176, 'add_vorfalltyp', 'Can add Vorfall-Typ'),(1306, 176, 'change_vorfalltyp', 'Can change Vorfall-Typ'),(1307, 176, 'delete_vorfalltyp', 'Can delete Vorfall-Typ'),(1308, 176, 'view_vorfalltyp', 'Can view Vorfall-Typ'),(1309, 177, 'add_rechtsgrundlage', 'Can add Rechtsgrundlage'),(1310, 177, 'change_rechtsgrundlage', 'Can change Rechtsgrundlage'),(1311, 177, 'delete_rechtsgrundlage', 'Can delete Rechtsgrundlage'),(1312, 177, 'view_rechtsgrundlage', 'Can view Rechtsgrundlage'),(1313, 178, 'add_datenkategorie', 'Can add Datenkategorie'),(1314, 178, 'change_datenkategorie', 'Can change Datenkategorie'),(1315, 178, 'delete_datenkategorie', 'Can delete Datenkategorie'),(1316, 178, 'view_datenkategorie', 'Can view Datenkategorie'),(1317, 179, 'add_mandant', 'Can add Mandant'),(1318, 179, 'change_mandant', 'Can change Mandant'),(1319, 179, 'delete_mandant', 'Can delete Mandant'),(1320, 179, 'view_mandant', 'Can view Mandant'),(1321, 180, 'add_dsbdokument', 'Can add DSB-Dokument'),(1322, 180, 'change_dsbdokument', 'Can change DSB-Dokument'),(1323, 180, 'delete_dsbdokument', 'Can delete DSB-Dokument'),(1324, 180, 'view_dsbdokument', 'Can view DSB-Dokument'),(1325, 181, 'add_tomkategorie', 'Can add TOM-Kategorie'),(1326, 181, 'change_tomkategorie', 'Can change TOM-Kategorie'),(1327, 181, 'delete_tomkategorie', 'Can delete TOM-Kategorie'),(1328, 181, 'view_tomkategorie', 'Can view TOM-Kategorie'),(1329, 182, 'add_mandanttom', 'Can add Mandant-TOM-Zuordnung'),(1330, 182, 'change_mandanttom', 'Can change Mandant-TOM-Zuordnung'),(1331, 182, 'delete_mandanttom', 'Can delete Mandant-TOM-Zuordnung'),(1332, 182, 'view_mandanttom', 'Can view Mandant-TOM-Zuordnung'),(1333, 183, 'add_tommassnahme', 'Can add TOM-Maßnahme'),(1334, 183, 'change_tommassnahme', 'Can change TOM-Maßnahme'),(1335, 183, 'delete_tommassnahme', 'Can delete TOM-Maßnahme'),(1336, 183, 'view_tommassnahme', 'Can view TOM-Maßnahme'),(1337, 184, 'add_equipmentcategory', 'Can add Gerätekategorie'),(1338, 184, 'change_equipmentcategory', 'Can change Gerätekategorie'),(1339, 184, 'delete_equipmentcategory', 'Can delete Gerätekategorie'),(1340, 184, 'view_equipmentcategory', 'Can view Gerätekategorie'),(1341, 185, 'add_explosiongroup', 'Can add Explosionsgruppe'),(1342, 185, 'change_explosiongroup', 'Can change Explosionsgruppe'),(1343, 185, 'delete_explosiongroup', 'Can delete Explosionsgruppe'),(1344, 185, 'view_explosiongroup', 'Can view Explosionsgruppe'),(1345, 186, 'add_ignitionprotectiontype', 'Can add Zündschutzart'),(1346, 186, 'change_ignitionprotectiontype', 'Can change Zündschutzart'),(1347, 186, 'delete_ignitionprotectiontype', 'Can delete Zündschutzart'),(1348, 186, 'view_ignitionprotectiontype', 'Can view Zündschutzart'),(1349, 187, 'add_physicalstate', 'Can add Aggregatzustand'),(1350, 187, 'change_physicalstate', 'Can change Aggregatzustand'),(1351, 187, 'delete_physicalstate', 'Can delete Aggregatzustand'),(1352, 187, 'view_physicalstate', 'Can view Aggregatzustand'),(1353, 188, 'add_temperatureclass', 'Can add Temperaturklasse'),(1354, 188, 'change_temperatureclass', 'Can change Temperaturklasse'),(1355, 188, 'delete_temperatureclass', 'Can delete Temperaturklasse'),(1356, 188, 'view_temperatureclass', 'Can view Temperaturklasse'),(1357, 189, 'add_regulationtype', 'Can add Vorschriftentyp'),(1358, 189, 'change_regulationtype', 'Can change Vorschriftentyp'),(1359, 189, 'delete_regulationtype', 'Can delete Vorschriftentyp'),(1360, 189, 'view_regulationtype', 'Can view Vorschriftentyp'),(1361, 190, 'add_regulation', 'Can add Vorschrift'),(1362, 190, 'change_regulation', 'Can change Vorschrift'),(1363, 190, 'delete_regulation', 'Can delete Vorschrift'),(1364, 190, 'view_regulation', 'Can view Vorschrift'),(1365, 191, 'add_explosionsschutzgutachten', 'Can add Explosionsschutzgutachten'),(1366, 191, 'change_explosionsschutzgutachten', 'Can change Explosionsschutzgutachten'),(1367, 191, 'delete_explosionsschutzgutachten', 'Can delete Explosionsschutzgutachten'),(1368, 191, 'view_explosionsschutzgutachten', 'Can view Explosionsschutzgutachten'),(1369, 192, 'add_equipment', 'Can add Equipment (Betriebsmittel)'),(1370, 192, 'change_equipment', 'Can change Equipment (Betriebsmittel)'),(1371, 192, 'delete_equipment', 'Can delete Equipment (Betriebsmittel)'),(1372, 192, 'view_equipment', 'Can view Equipment (Betriebsmittel)'),(1373, 193, 'add_analysiscategory', 'Can add Analyse-Kategorie'),(1374, 193, 'change_analysiscategory', 'Can change Analyse-Kategorie'),(1375, 193, 'delete_analysiscategory', 'Can delete Analyse-Kategorie'),(1376, 193, 'view_analysiscategory', 'Can view Analyse-Kategorie'),(1377, 194, 'add_buildingtype', 'Can add Gebäudetyp'),(1378, 194, 'change_buildingtype', 'Can change Gebäudetyp'),(1379, 194, 'delete_buildingtype', 'Can delete Gebäudetyp'),(1380, 194, 'view_buildingtype', 'Can view Gebäudetyp'),(1381, 195, 'add_compliancestandard', 'Can add Compliance-Standard'),(1382, 195, 'change_compliancestandard', 'Can change Compliance-Standard'),(1383, 195, 'delete_compliancestandard', 'Can delete Compliance-Standard'),(1384, 195, 'view_compliancestandard', 'Can view Compliance-Standard'),(1385, 196, 'add_drawingtype', 'Can add Zeichnungstyp'),(1386, 196, 'change_drawingtype', 'Can change Zeichnungstyp'),(1387, 196, 'delete_drawingtype', 'Can delete Zeichnungstyp'),(1388, 196, 'view_drawingtype', 'Can view Zeichnungstyp'),(1389, 197, 'add_layerstandard', 'Can add Layer-Standard'),(1390, 197, 'change_layerstandard', 'Can change Layer-Standard'),(1391, 197, 'delete_layerstandard', 'Can delete Layer-Standard'),(1392, 197, 'view_layerstandard', 'Can view Layer-Standard'),(1393, 198, 'add_severitylevel', 'Can add Schweregrad'),(1394, 198, 'change_severitylevel', 'Can change Schweregrad'),(1395, 198, 'delete_severitylevel', 'Can delete Schweregrad'),(1396, 198, 'view_severitylevel', 'Can view Schweregrad'),(1397, 199, 'add_researchfocuslookup', 'Can add Recherche-Fokus'),(1398, 199, 'change_researchfocuslookup', 'Can change Recherche-Fokus'),(1399, 199, 'delete_researchfocuslookup', 'Can delete Recherche-Fokus'),(1400, 199, 'view_researchfocuslookup', 'Can view Recherche-Fokus'),(1401, 200, 'add_sourcetypelookup', 'Can add Quellen-Typ'),(1402, 200, 'change_sourcetypelookup', 'Can change Quellen-Typ'),(1403, 200, 'delete_sourcetypelookup', 'Can delete Quellen-Typ'),(1404, 200, 'view_sourcetypelookup', 'Can view Quellen-Typ'),(1405, 201, 'add_citationstylelookup', 'Can add Zitierstil'),(1406, 201, 'change_citationstylelookup', 'Can change Zitierstil'),(1407, 201, 'delete_citationstylelookup', 'Can delete Zitierstil'),(1408, 201, 'view_citationstylelookup', 'Can view Zitierstil'),(1409, 202, 'add_researchsource', 'Can add Research Source'),(1410, 202, 'change_researchsource', 'Can change Research Source'),(1411, 202, 'delete_researchsource', 'Can delete Research Source'),(1412, 202, 'view_researchsource', 'Can view Research Source'),(1413, 203, 'add_researchhandlerexecution', 'Can add Handler Execution'),(1414, 203, 'change_researchhandlerexecution', 'Can change Handler Execution'),(1415, 203, 'delete_researchhandlerexecution', 'Can delete Handler Execution'),(1416, 203, 'view_researchhandlerexecution', 'Can view Handler Execution'),(1417, 204, 'add_handlertypelookup', 'Can add Handler-Typ'),(1418, 204, 'change_handlertypelookup', 'Can change Handler-Typ'),(1419, 204, 'delete_handlertypelookup', 'Can delete Handler-Typ'),(1420, 204, 'view_handlertypelookup', 'Can view Handler-Typ'),(1421, 205, 'add_researchdepthlookup', 'Can add Recherche-Tiefe'),(1422, 205, 'change_researchdepthlookup', 'Can change Recherche-Tiefe'),(1423, 205, 'delete_researchdepthlookup', 'Can delete Recherche-Tiefe'),(1424, 205, 'view_researchdepthlookup', 'Can view Recherche-Tiefe'),(1425, 206, 'add_synthesistypelookup', 'Can add Synthese-Typ'),(1426, 206, 'change_synthesistypelookup', 'Can change Synthese-Typ'),(1427, 206, 'delete_synthesistypelookup', 'Can delete Synthese-Typ'),(1428, 206, 'view_synthesistypelookup', 'Can view Synthese-Typ'),(1429, 207, 'add_researchproject', 'Can add Research Project'),(1430, 207, 'change_researchproject', 'Can change Research Project'),(1431, 207, 'delete_researchproject', 'Can delete Research Project'),(1432, 207, 'view_researchproject', 'Can view Research Project'),(1433, 208, 'add_researchresult', 'Can add Research Result'),(1434, 208, 'change_researchresult', 'Can change Research Result'),(1435, 208, 'delete_researchresult', 'Can delete Research Result'),(1436, 208, 'view_researchresult', 'Can view Research Result'),(1437, 209, 'add_researchsession', 'Can add Research Session'),(1438, 209, 'change_researchsession', 'Can change Research Session'),(1439, 209, 'delete_researchsession', 'Can delete Research Session'),(1440, 209, 'view_researchsession', 'Can view Research Session'),(1441, 210, 'add_token', 'Can add Token'),(1442, 210, 'change_token', 'Can change Token'),(1443, 210, 'delete_token', 'Can delete Token'),(1444, 210, 'view_token', 'Can view Token'),(1445, 211, 'add_tokenproxy', 'Can add Token'),(1446, 211, 'change_tokenproxy', 'Can change Token'),(1447, 211, 'delete_tokenproxy', 'Can delete Token'),(1448, 211, 'view_tokenproxy', 'Can view Token');
COMMIT;
BEGIN;
DELETE FROM "main"."auth_user";
INSERT INTO "main"."auth_user" ("id","password","last_login","is_superuser","username","last_name","email","is_staff","is_active","date_joined","first_name") VALUES (1, 'pbkdf2_sha256$1000000$LEVWASG2creTipP3cXDhh9$Xqix8nTd20fA2u+QjXPrZOGN21NYlF754Xqeu8Ap2l4=', '2025-10-26 12:26:29.747175', 1, 'achim', '', '', 1, 1, '2025-10-17 15:49:44.503060', ''),(2, 'pbkdf2_sha256$1000000$PewZPVX4jsbkUQnEB78rJh$HgitTHrjU+V+Q7Js/Vke4Jfc4qUG6i47OTOz1XtjfZU=', '2025-12-05 15:39:38.501672', 1, 'admin', '', 'admin@example.com', 1, 1, '2025-10-27 09:05:05', ''),(3, 'pbkdf2_sha256$1000000$UZL0tNp5GWvoM1JGBA8T95$zMxcktiIShXcCUOnE6a+gjKH6oTZTgjfr2a9Y2Ii/Sk=', '2025-11-03 09:24:09.348104', 0, 'book', 'story', '', 0, 1, '2025-10-28 18:10:52', 'book'),(4, 'pbkdf2_sha256$1000000$KX9zEKQiZXb3Os2AaTDDBH$5xwZPlvKguD5sG7HM/mxoea/5fyQgRkZyqBTPos+TFA=', '2025-10-28 19:59:24.661890', 0, 'med', 'arzt', '', 0, 1, '2025-10-28 18:11:50', 'med'),(5, '', NULL, 0, 'workflow_test', '', 'test@workflow.com', 0, 1, '2025-11-17 06:45:27.279395', ''),(6, 'pbkdf2_sha256$1000000$wJ5M3VXhpYIcYLV7QX6KRf$K6fP3YWo92qsvb+cJS+p4eDj6r7XbDAFoq5dF6waV38=', NULL, 0, 'testuser', '', 'test@example.com', 0, 1, '2025-11-19 22:43:50.057485', '');
COMMIT;
BEGIN;
DELETE FROM "main"."auth_user_groups";
INSERT INTO "main"."auth_user_groups" ("id","user_id","group_id") VALUES (1, 3, 1),(2, 4, 2),(3, 2, 1),(4, 2, 2);
COMMIT;
BEGIN;
DELETE FROM "main"."auth_user_user_permissions";
INSERT INTO "main"."auth_user_user_permissions" ("id","user_id","permission_id") VALUES (17, 3, 17),(18, 3, 18),(19, 3, 19),(20, 3, 20),(25, 3, 25),(26, 3, 26),(27, 3, 27),(28, 3, 28),(29, 3, 29),(30, 3, 30),(31, 3, 31),(32, 3, 32),(33, 3, 33),(34, 3, 34),(35, 3, 35),(36, 3, 36),(37, 3, 37),(38, 3, 38),(39, 3, 39),(40, 3, 40),(41, 3, 41),(42, 3, 42),(43, 3, 43),(44, 3, 44),(45, 3, 45),(46, 3, 46),(47, 3, 47),(48, 3, 48),(49, 3, 49),(50, 3, 50),(51, 3, 51),(52, 3, 52),(53, 3, 53),(54, 3, 54),(55, 3, 55),(56, 3, 56),(57, 3, 57),(58, 3, 58),(59, 3, 59),(60, 3, 60),(61, 3, 61),(62, 3, 62),(63, 3, 63),(64, 3, 64),(65, 3, 65),(66, 3, 66),(67, 3, 67),(68, 3, 68),(69, 3, 69),(70, 3, 70),(71, 3, 71),(72, 3, 72),(73, 3, 73),(74, 3, 74),(75, 3, 75),(76, 3, 76),(77, 3, 77),(78, 3, 78),(79, 3, 79),(80, 3, 80),(81, 3, 81),(82, 3, 82),(83, 3, 83),(84, 3, 84),(85, 3, 85),(86, 3, 86),(87, 3, 87),(88, 3, 88),(89, 3, 89),(90, 3, 90),(91, 3, 91),(92, 3, 92),(93, 3, 93),(94, 3, 94),(95, 3, 95),(96, 3, 96),(97, 3, 97),(98, 3, 98),(99, 3, 99),(100, 3, 100),(101, 3, 101),(102, 3, 102),(103, 3, 103),(104, 3, 104),(105, 3, 105),(106, 3, 106),(107, 3, 107),(108, 3, 108),(109, 3, 109),(110, 3, 110),(111, 3, 111),(112, 3, 112),(113, 3, 113),(114, 3, 114),(115, 3, 115),(116, 3, 116),(117, 3, 117),(118, 3, 118),(119, 3, 119),(120, 3, 120),(121, 3, 121),(122, 3, 122),(123, 3, 123),(124, 3, 124),(125, 3, 125),(126, 3, 126),(127, 3, 127),(128, 3, 128),(129, 3, 129),(130, 3, 130),(131, 3, 131),(132, 3, 132),(133, 3, 133),(134, 3, 134),(135, 3, 135),(136, 3, 136),(137, 3, 137),(138, 3, 138),(139, 3, 139),(140, 3, 140),(141, 3, 141),(142, 3, 142),(143, 3, 143),(144, 3, 144),(145, 3, 145),(146, 3, 146),(147, 3, 147),(148, 3, 148),(149, 3, 149),(150, 3, 150),(151, 3, 151),(152, 3, 152),(153, 3, 153),(154, 3, 154),(155, 3, 155),(156, 3, 156),(157, 3, 157),(158, 3, 158),(159, 3, 159),(160, 3, 160),(161, 3, 161),(162, 3, 162),(163, 3, 163),(164, 3, 164),(165, 3, 165),(166, 3, 166),(167, 3, 167),(168, 3, 168),(169, 3, 169),(170, 3, 170),(171, 3, 171),(172, 3, 172),(173, 3, 173),(174, 3, 174),(175, 3, 175),(176, 3, 176),(177, 3, 177),(178, 3, 178),(179, 3, 179),(180, 3, 180),(181, 3, 181),(182, 3, 182),(183, 3, 183),(184, 3, 184),(189, 3, 189),(197, 3, 197),(198, 3, 198),(199, 3, 199),(200, 3, 200),(201, 3, 201),(202, 3, 202),(203, 3, 203),(204, 3, 204),(205, 3, 205),(206, 3, 206),(207, 3, 207),(208, 3, 208),(209, 3, 209),(210, 3, 210),(211, 3, 211),(212, 3, 212),(213, 3, 213),(214, 3, 214),(215, 3, 215),(216, 3, 216),(217, 3, 217),(218, 3, 218),(219, 3, 219),(220, 3, 220),(221, 4, 192),(222, 4, 193),(223, 4, 194),(224, 4, 195),(225, 4, 196),(226, 4, 185),(227, 4, 186),(228, 4, 187),(229, 4, 188),(230, 4, 189),(231, 4, 190),(232, 4, 191),(233, 2, 1),(234, 2, 2),(235, 2, 3),(236, 2, 4),(237, 2, 5),(238, 2, 6),(239, 2, 7),(240, 2, 8),(241, 2, 9),(242, 2, 10),(243, 2, 11),(244, 2, 12),(245, 2, 13),(246, 2, 14),(247, 2, 15),(248, 2, 16),(249, 2, 17),(250, 2, 18),(251, 2, 19),(252, 2, 20),(253, 2, 21),(254, 2, 22),(255, 2, 23),(256, 2, 24),(257, 2, 25),(258, 2, 26),(259, 2, 27),(260, 2, 28),(261, 2, 29),(262, 2, 30),(263, 2, 31),(264, 2, 32),(265, 2, 33),(266, 2, 34),(267, 2, 35),(268, 2, 36),(269, 2, 37),(270, 2, 38),(271, 2, 39),(272, 2, 40),(273, 2, 41),(274, 2, 42),(275, 2, 43),(276, 2, 44),(277, 2, 45),(278, 2, 46),(279, 2, 47),(280, 2, 48),(281, 2, 49),(282, 2, 50),(283, 2, 51),(284, 2, 52),(285, 2, 53),(286, 2, 54),(287, 2, 55),(288, 2, 56),(289, 2, 57),(290, 2, 58),(291, 2, 59),(292, 2, 60),(293, 2, 61),(294, 2, 62),(295, 2, 63),(296, 2, 64),(297, 2, 65),(298, 2, 66),(299, 2, 67),(300, 2, 68),(301, 2, 69),(302, 2, 70),(303, 2, 71),(304, 2, 72),(305, 2, 73),(306, 2, 74),(307, 2, 75),(308, 2, 76),(309, 2, 77),(310, 2, 78),(311, 2, 79),(312, 2, 80),(313, 2, 81),(314, 2, 82),(315, 2, 83),(316, 2, 84),(317, 2, 85),(318, 2, 86),(319, 2, 87),(320, 2, 88),(321, 2, 89),(322, 2, 90),(323, 2, 91),(324, 2, 92),(325, 2, 93),(326, 2, 94),(327, 2, 95),(328, 2, 96),(329, 2, 97),(330, 2, 98),(331, 2, 99),(332, 2, 100),(333, 2, 101),(334, 2, 102),(335, 2, 103),(336, 2, 104),(337, 2, 105),(338, 2, 106),(339, 2, 107),(340, 2, 108),(341, 2, 109),(342, 2, 110),(343, 2, 111),(344, 2, 112),(345, 2, 113),(346, 2, 114),(347, 2, 115),(348, 2, 116),(349, 2, 117),(350, 2, 118),(351, 2, 119),(352, 2, 120),(353, 2, 121),(354, 2, 122),(355, 2, 123),(356, 2, 124),(357, 2, 125),(358, 2, 126),(359, 2, 127),(360, 2, 128),(361, 2, 129),(362, 2, 130),(363, 2, 131),(364, 2, 132),(365, 2, 133),(366, 2, 134),(367, 2, 135),(368, 2, 136),(369, 2, 137),(370, 2, 138),(371, 2, 139),(372, 2, 140),(373, 2, 141),(374, 2, 142),(375, 2, 143),(376, 2, 144),(377, 2, 145),(378, 2, 146),(379, 2, 147),(380, 2, 148),(381, 2, 149),(382, 2, 150),(383, 2, 151),(384, 2, 152),(385, 2, 153),(386, 2, 154),(387, 2, 155),(388, 2, 156),(389, 2, 157),(390, 2, 158),(391, 2, 159),(392, 2, 160),(393, 2, 161),(394, 2, 162),(395, 2, 163),(396, 2, 164),(397, 2, 165),(398, 2, 166),(399, 2, 167),(400, 2, 168),(401, 2, 169),(402, 2, 170),(403, 2, 171),(404, 2, 172),(405, 2, 173),(406, 2, 174),(407, 2, 175),(408, 2, 176),(409, 2, 177),(410, 2, 178),(411, 2, 179),(412, 2, 180),(413, 2, 181),(414, 2, 182),(415, 2, 183),(416, 2, 184),(417, 2, 185),(418, 2, 186),(419, 2, 187),(420, 2, 188),(421, 2, 189),(422, 2, 190),(423, 2, 191),(424, 2, 192),(425, 2, 193),(426, 2, 194),(427, 2, 195),(428, 2, 196),(429, 2, 197),(430, 2, 198),(431, 2, 199),(432, 2, 200),(433, 2, 201),(434, 2, 202),(435, 2, 203),(436, 2, 204),(437, 2, 205),(438, 2, 206),(439, 2, 207),(440, 2, 208),(441, 2, 209),(442, 2, 210),(443, 2, 211),(444, 2, 212),(445, 2, 213),(446, 2, 214),(447, 2, 215),(448, 2, 216),(449, 2, 217),(450, 2, 218),(451, 2, 219),(452, 2, 220);
COMMIT;
BEGIN;
DELETE FROM "main"."authtoken_token";
INSERT INTO "main"."authtoken_token" ("key","created","user_id") VALUES ('0d1110477ab32edb7913741f086e8c15f1dde716', '2025-12-03 10:46:41.925684', 1);
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_bugfixplan";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_chapterrating";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_comment";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_component_change_log";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_component_registry";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_component_usage_log";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_contextenrichmentlog";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_contextschema";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_contextsource";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_feature_document";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_feature_document_keyword";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_generatedimage";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_imagegenerationbatch";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_imagestyleprofile";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_migration_conflict";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_migration_registry";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_requirementtestlink";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_reviewparticipant";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_reviewround";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_testbug";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_testcase";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_testcoveragereport";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_testexecution";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_testlog";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_testrequirement";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_testscreenshot";
COMMIT;
BEGIN;
DELETE FROM "main"."bfagent_testsession";
COMMIT;
BEGIN;
DELETE FROM "main"."book_characters_v2";
COMMIT;
BEGIN;
DELETE FROM "main"."book_statuses";
COMMIT;
BEGIN;
DELETE FROM "main"."book_type_phases";
COMMIT;
BEGIN;
DELETE FROM "main"."book_types";
COMMIT;
BEGIN;
DELETE FROM "main"."cad_analysis_category";
INSERT INTO "main"."cad_analysis_category" ("id","code","name_de","name_en","description","sort_order","is_active","created_at","updated_at","handler_class","automation_potential","priority") VALUES (1, 'PLAN_COMPLETENESS', 'Planvollständigkeit', 'Plan Completeness', 'Prüfung ob alle Pflichtangaben vorhanden', 10, 1, '2025-12-01 21:49:25.311856', '2025-12-02 07:08:28.994390', 'PlanCompletenessHandler', 95, 'critical'),(2, 'AREA_CALCULATION', 'Flächenberechnung', 'Area Calculation', 'Berechnung BGF/NGF/VF/NRF nach DIN 277', 20, 1, '2025-12-01 21:49:25.313388', '2025-12-02 07:08:28.995907', 'AreaCalculationHandler', 90, 'high'),(3, 'LAYER_VALIDATION', 'Layer-Validierung', 'Layer Validation', 'Prüfung Layer-Struktur gegen Standards', 30, 1, '2025-12-01 21:49:25.315600', '2025-12-02 07:08:28.997429', 'LayerAnalysisHandler', 95, 'high'),(4, 'NORM_COMPLIANCE', 'Normkonformität', 'Compliance Check', 'Prüfung gegen DIN/ISO-Normen', 40, 1, '2025-12-01 21:49:25.316112', '2025-12-02 07:08:28.998945', 'DIN1356ComplianceHandler', 85, 'high'),(5, 'DIMENSION_CHECK', 'Maßprüfung', 'Dimension Check', 'Extraktion und Validierung von Maßen', 50, 1, '2025-12-01 21:49:25.317635', '2025-12-02 07:08:28.998945', 'DimensionExtractionHandler', 85, 'medium'),(6, 'REVISION_COMPARE', 'Revisions-Vergleich', 'Revision Comparison', 'Vergleich von Planversionen', 60, 1, '2025-12-01 21:49:25.319150', '2025-12-02 07:08:29.000457', 'RevisionComparisonHandler', 80, 'medium'),(7, 'ACCESSIBILITY', 'Barrierefreiheit', 'Accessibility', 'Prüfung DIN 18040', 70, 1, '2025-12-01 21:49:25.320667', '2025-12-02 07:08:29.002481', 'DIN18040AccessibilityHandler', 85, 'medium'),(8, 'FIRE_SAFETY', 'Brandschutz', 'Fire Safety', 'Brandschutz-Dokumentation', 80, 1, '2025-12-01 21:49:25.322179', '2025-12-02 07:08:29.002990', 'FireSafetyExtractionHandler', 75, 'high'),(9, 'MASS_CALCULATION', 'Massenermittlung', 'Mass Calculation', 'Mengenermittlung für Kalkulation', 90, 1, '2025-12-01 21:49:25.323695', '2025-12-02 07:08:29.004501', 'MassCalculationHandler', 75, 'medium');
COMMIT;
BEGIN;
DELETE FROM "main"."cad_analysis_jobs";
COMMIT;
BEGIN;
DELETE FROM "main"."cad_analysis_reports";
COMMIT;
BEGIN;
DELETE FROM "main"."cad_analysis_results";
COMMIT;
BEGIN;
DELETE FROM "main"."cad_building_type";
INSERT INTO "main"."cad_building_type" ("id","code","name_de","name_en","description","sort_order","is_active","created_at","updated_at","building_class","fire_safety_category","requires_accessibility") VALUES (1, 'WOHNGEBAEUDE', 'Wohngebäude', 'Residential Building', 'Mehrfamilienhaus, Einfamilienhaus', 10, 1, '2025-12-01 21:49:25.345112', '2025-12-02 07:08:29.023293', 'GK1-GK3', '', 1),(2, 'BUERO', 'Bürogebäude', 'Office Building', 'Büro- und Verwaltungsgebäude', 20, 1, '2025-12-01 21:49:25.347167', '2025-12-02 07:08:29.024903', 'GK4-GK5', '', 1),(3, 'GEWERBE', 'Gewerbegebäude', 'Commercial Building', 'Handel, Gastronomie', 30, 1, '2025-12-01 21:49:25.348865', '2025-12-02 07:08:29.025927', 'GK4-GK5', '', 1),(4, 'INDUSTRIE', 'Industriegebäude', 'Industrial Building', 'Produktionshallen, Fabriken', 40, 1, '2025-12-01 21:49:25.350385', '2025-12-02 07:08:29.027444', 'GK5', '', 0),(5, 'SONDERBAU', 'Sonderbau', 'Special Structure', 'Hochhäuser, Versammlungsstätten', 50, 1, '2025-12-01 21:49:25.351896', '2025-12-02 07:08:29.027444', 'GK5', '', 1),(6, 'TIEFBAU', 'Tiefbau', 'Civil Engineering', 'Straßen, Brücken, Kanäle', 60, 1, '2025-12-01 21:49:25.353411', '2025-12-02 07:08:29.028959', '', '', 0);
COMMIT;
BEGIN;
DELETE FROM "main"."cad_compliance_standard";
INSERT INTO "main"."cad_compliance_standard" ("id","code","name_de","name_en","description","sort_order","is_active","created_at","updated_at","standard_type","issuing_body","version","publication_date","url","is_mandatory") VALUES (1, 'DIN_1356', 'DIN 1356', 'DIN 1356', 'Bauzeichnungen - Arten, Inhalte, Grundregeln', 10, 1, '2025-12-01 21:49:25.325209', '2025-12-02 07:08:29.006014', 'din', 'DIN', '1995-02', NULL, '', 0),(2, 'DIN_406', 'DIN 406', 'DIN 406', 'Maßeintragung in Zeichnungen', 20, 1, '2025-12-01 21:49:25.326215', '2025-12-02 07:08:29.007527', 'din', 'DIN', '', NULL, '', 0),(3, 'DIN_277', 'DIN 277', 'DIN 277', 'Grundflächen und Rauminhalte', 30, 1, '2025-12-01 21:49:25.327757', '2025-12-02 07:08:29.009163', 'din', 'DIN', '2016-01', NULL, '', 0),(4, 'DIN_18040_1', 'DIN 18040-1', 'DIN 18040-1', 'Barrierefreies Bauen - öffentliche Gebäude', 40, 1, '2025-12-01 21:49:25.329269', '2025-12-02 07:08:29.010677', 'din', 'DIN', '', NULL, '', 1),(5, 'DIN_18040_2', 'DIN 18040-2', 'DIN 18040-2', 'Barrierefreies Bauen - Wohnungen', 50, 1, '2025-12-01 21:49:25.329269', '2025-12-02 07:08:29.012190', 'din', 'DIN', '', NULL, '', 1),(6, 'DIN_4102', 'DIN 4102', 'DIN 4102', 'Brandverhalten von Baustoffen und Bauteilen', 60, 1, '2025-12-01 21:49:25.332436', '2025-12-02 07:08:29.012190', 'din', 'DIN', '', NULL, '', 1),(7, 'DIN_1998', 'DIN 1998', 'DIN 1998', 'Unterbringung von Leitungen in Verkehrsflächen', 70, 1, '2025-12-01 21:49:25.333951', '2025-12-02 07:08:29.013704', 'din', 'DIN', '', NULL, '', 0),(8, 'ISO_13567', 'ISO 13567', 'ISO 13567', 'CAD-Layer (Ebenen)', 80, 1, '2025-12-01 21:49:25.335463', '2025-12-02 07:08:29.015219', 'iso', 'ISO', '', NULL, '', 0),(9, 'ISO_128', 'ISO 128', 'ISO 128', 'Technische Zeichnungen - Grundlagen', 90, 1, '2025-12-01 21:49:25.336497', '2025-12-02 07:08:29.016736', 'iso', 'ISO', '', NULL, '', 0);
COMMIT;
BEGIN;
DELETE FROM "main"."cad_drawing_files";
COMMIT;
BEGIN;
DELETE FROM "main"."cad_drawing_type";
INSERT INTO "main"."cad_drawing_type" ("id","code","name_de","name_en","description","sort_order","is_active","created_at","updated_at","icon","color","requires_3d") VALUES (1, 'GRUNDRISS', 'Grundriss', 'Floor Plan', 'Horizontaler Schnitt durch ein Gebäude', 10, 1, '2025-12-01 21:49:25.295907', '2025-12-02 07:08:28.980116', 'bi-grid-3x3', '#3498db', 0),(2, 'SCHNITT', 'Schnitt', 'Section', 'Vertikaler Schnitt durch ein Gebäude', 20, 1, '2025-12-01 21:49:25.299731', '2025-12-02 07:08:28.983147', 'bi-scissors', '#e74c3c', 0),(3, 'ANSICHT', 'Ansicht', 'Elevation', 'Außenansicht Fassade', 30, 1, '2025-12-01 21:49:25.301244', '2025-12-02 07:08:28.984660', 'bi-building', '#2ecc71', 0),(4, 'LAGEPLAN', 'Lageplan', 'Site Plan', 'Übersichtsplan Grundstück', 40, 1, '2025-12-01 21:49:25.302762', '2025-12-02 07:08:28.985679', 'bi-geo-alt', '#f39c12', 0),(5, 'DETAIL', 'Detail', 'Detail', 'Detailzeichnung', 50, 1, '2025-12-01 21:49:25.304276', '2025-12-02 07:08:28.987199', 'bi-zoom-in', '#9b59b6', 0),(6, 'BEWEHRUNG', 'Bewehrungsplan', 'Reinforcement Plan', 'Stahlbewehrung für Betonbau', 60, 1, '2025-12-01 21:49:25.305787', '2025-12-02 07:08:28.987199', 'bi-bricks', '#95a5a6', 0),(7, 'HAUSTECHNIK', 'Haustechnik (TGA)', 'MEP', 'Heizung, Lüftung, Sanitär, Elektro', 70, 1, '2025-12-01 21:49:25.306307', '2025-12-02 07:08:28.989736', 'bi-gear', '#1abc9c', 1),(8, 'TIEFBAU', 'Tiefbau', 'Civil Engineering', 'Tiefbau, Infrastruktur', 80, 1, '2025-12-01 21:49:25.307821', '2025-12-02 07:08:28.989736', 'bi-truck', '#34495e', 0),(9, 'KANALPLAN', 'Kanalplan', 'Sewer Plan', 'Entwässerungssystem', 90, 1, '2025-12-01 21:49:25.309335', '2025-12-02 07:08:28.992866', 'bi-water', '#3498db', 0),(10, 'SPARTENPLAN', 'Spartenplan', 'Utility Plan', 'Leitungen verschiedener Sparten', 100, 1, '2025-12-01 21:49:25.310851', '2025-12-02 07:08:28.992866', 'bi-diagram-3', '#e67e22', 0);
COMMIT;
BEGIN;
DELETE FROM "main"."cad_layer_standard";
INSERT INTO "main"."cad_layer_standard" ("id","code","name_de","name_en","description","sort_order","is_active","created_at","updated_at","naming_pattern","example_layers","discipline_separator") VALUES (1, 'DIN_ISO_13567', 'DIN ISO 13567', 'DIN ISO 13567', 'Deutscher Standard für Layer-Benennung', 10, 1, '2025-12-01 21:49:25.355448', '2025-12-02 07:08:29.030468', '^[A-Z]-[A-Z]{2,6}(-[A-Z]{2,6})?$', 'A-WALL-EXTW, E-LITE-POWR, M-HVAC-SUPL', '-'),(2, 'AIA', 'AIA CAD Standard', 'AIA CAD Standard', 'American Institute of Architects Standard', 20, 1, '2025-12-01 21:49:25.356964', '2025-12-02 07:08:29.031986', '^[A-Z]-[A-Z]{4}(-[A-Z]{4})?$', 'A-WALL, A-DOOR-SYMB, M-HVAC', '-'),(3, 'CUSTOM', 'Firmenspezifisch', 'Custom', 'Individueller Firmenstandard', 30, 1, '2025-12-01 21:49:25.356964', '2025-12-02 07:08:29.033506', '', '', '-');
COMMIT;
BEGIN;
DELETE FROM "main"."cad_severity_level";
INSERT INTO "main"."cad_severity_level" ("id","code","name_de","name_en","description","sort_order","is_active","created_at","updated_at","color","icon","requires_action","escalation_hours") VALUES (1, 'CRITICAL', 'Kritisch', 'Critical', 'Muss sofort behoben werden', 10, 1, '2025-12-01 21:49:25.338537', '2025-12-02 07:08:29.018253', '#dc3545', 'bi-exclamation-triangle-fill', 1, 24),(2, 'HIGH', 'Hoch', 'High', 'Sollte zeitnah behoben werden', 20, 1, '2025-12-01 21:49:25.339050', '2025-12-02 07:08:29.018758', '#fd7e14', 'bi-exclamation-circle', 1, 72),(3, 'MEDIUM', 'Mittel', 'Medium', 'Sollte behoben werden', 30, 1, '2025-12-01 21:49:25.340563', '2025-12-02 07:08:29.020267', '#ffc107', 'bi-info-circle', 0, NULL),(4, 'LOW', 'Niedrig', 'Low', 'Optional', 40, 1, '2025-12-01 21:49:25.342081', '2025-12-02 07:08:29.020267', '#0dcaf0', 'bi-dash-circle', 0, NULL),(5, 'INFO', 'Info', 'Info', 'Nur zur Information', 50, 1, '2025-12-01 21:49:25.343599', '2025-12-02 07:08:29.021777', '#6c757d', 'bi-info-square', 0, NULL);
COMMIT;
BEGIN;
DELETE FROM "main"."chapters_v2";
COMMIT;
BEGIN;
DELETE FROM "main"."characters_v2";
COMMIT;
BEGIN;
DELETE FROM "main"."checklist_instances";
COMMIT;
BEGIN;
DELETE FROM "main"."checklist_item_statuses";
COMMIT;
BEGIN;
DELETE FROM "main"."checklist_items";
INSERT INTO "main"."checklist_items" ("id","template_id","text","help_text","order","category","is_mandatory","condition","depends_on_id","ai_check_hint","reference_norm","is_active","linked_handler_id","handler_action","handler_config","auto_complete_on_handler_success") VALUES (1, 1, 'Define book title and working synopsis', '', 1, 'Planning', 1, '', NULL, 'title_defined', '', 1, NULL, '', '{}', 1),(2, 1, 'Select primary genre', '', 2, 'Planning', 1, '', NULL, 'genre_selected', '', 1, NULL, '', '{}', 1),(3, 1, 'Define target audience', '', 3, 'Planning', 1, '', NULL, 'target_audience_defined', '', 1, NULL, '', '{}', 1),(4, 1, 'Set book type (Novel, Novella, etc.)', '', 4, 'Planning', 1, '', NULL, 'book_type_set', '', 1, NULL, '', '{}', 1),(5, 1, 'Create main character profiles', '', 5, 'Planning', 1, '', NULL, 'character_profiles_exist', '', 1, NULL, '', '{}', 1),(6, 1, 'Create supporting character profiles (min 2)', '', 6, 'Planning', 0, '', NULL, 'min_characters_created', '', 1, NULL, '', '{}', 1),(7, 1, 'Define world setting and rules', '', 7, 'Planning', 1, '', NULL, 'world_defined', '', 1, NULL, '', '{}', 1),(8, 1, 'Create key locations', '', 8, 'Planning', 0, '', NULL, 'locations_defined', '', 1, NULL, '', '{}', 1),(9, 1, 'Develop plot structure (3-act, Hero''s Journey, etc.)', '', 9, 'Planning', 1, '', NULL, 'plot_structure_defined', '', 1, NULL, '', '{}', 1),(10, 1, 'Create detailed chapter outline (min 10 chapters)', '', 10, 'Planning', 1, '', NULL, 'min_chapters_planned', '', 1, NULL, '', '{}', 1),(11, 1, 'Complete full story outline', '', 11, 'Planning', 1, '', NULL, 'outline_complete', '', 1, NULL, '', '{}', 1),(12, 1, 'Define character arcs for main characters', '', 12, 'Planning', 0, '', NULL, 'character_arcs_defined', '', 1, NULL, '', '{}', 1),(13, 1, 'Research required topics', '', 13, 'Planning', 0, '', NULL, 'research_completed', '', 1, NULL, '', '{}', 1),(14, 1, 'Set writing goals and timeline', '', 14, 'Planning', 0, '', NULL, 'timeline_set', '', 1, NULL, '', '{}', 1),(15, 2, 'Write Chapter 1', '', 1, 'Writing', 1, '', NULL, 'first_chapter_started', '', 1, NULL, '', '{}', 1),(16, 2, 'Reach 1,000 words milestone', '', 2, 'Writing', 1, '', NULL, 'min_words_written', '', 1, NULL, '', '{}', 1),(17, 2, 'Complete Act 1 (Chapters 1-5)', '', 3, 'Writing', 1, '', NULL, 'chapter_count_act1_complete', '', 1, NULL, '', '{}', 1),(18, 2, 'Character introduction complete', '', 4, 'Writing', 1, '', NULL, 'characters_introduced', '', 1, NULL, '', '{}', 1),(19, 2, 'World-building established', '', 5, 'Writing', 1, '', NULL, 'world_established', '', 1, NULL, '', '{}', 1),(20, 2, 'Reach 25,000 words milestone', '', 6, 'Writing', 1, '', NULL, 'word_count_25k', '', 1, NULL, '', '{}', 1),(21, 2, 'Complete Act 2 - Part 1 (Rising Action)', '', 7, 'Writing', 1, '', NULL, 'act2_part1_complete', '', 1, NULL, '', '{}', 1),(22, 2, 'Midpoint achieved', '', 8, 'Writing', 1, '', NULL, 'midpoint_reached', '', 1, NULL, '', '{}', 1),(23, 2, 'Reach 50,000 words milestone (NaNoWriMo!)', '', 9, 'Writing', 0, '', NULL, 'word_count_50k', '', 1, NULL, '', '{}', 1),(24, 2, 'Complete Act 2 - Part 2 (Complications)', '', 10, 'Writing', 1, '', NULL, 'act2_part2_complete', '', 1, NULL, '', '{}', 1),(25, 2, 'Reach 75,000 words milestone', '', 11, 'Writing', 0, '', NULL, 'word_count_75k', '', 1, NULL, '', '{}', 1),(26, 2, 'Complete Act 3 (Climax & Resolution)', '', 12, 'Writing', 1, '', NULL, 'act3_complete', '', 1, NULL, '', '{}', 1),(27, 2, 'Write "The End"', '', 13, 'Writing', 1, '', NULL, 'story_complete', '', 1, NULL, '', '{}', 1),(28, 2, 'Final word count achieved (80,000+ for novel)', '', 14, 'Writing', 1, '', NULL, 'final_word_count', '', 1, NULL, '', '{}', 1),(29, 3, 'Complete first read-through (no edits)', '', 1, 'Editing', 1, '', NULL, 'first_readthrough_done', '', 1, NULL, '', '{}', 1),(30, 3, 'Structural edit: Plot holes and pacing', '', 2, 'Editing', 1, '', NULL, 'structural_edit_complete', '', 1, NULL, '', '{}', 1),(31, 3, 'Character development review', '', 3, 'Editing', 1, '', NULL, 'character_arcs_reviewed', '', 1, NULL, '', '{}', 1),(32, 3, 'Dialogue polish', '', 4, 'Editing', 1, '', NULL, 'dialogue_polished', '', 1, NULL, '', '{}', 1),(33, 3, 'Scene-by-scene revision', '', 5, 'Editing', 1, '', NULL, 'scenes_revised', '', 1, NULL, '', '{}', 1),(34, 3, 'Line editing: Style and flow', '', 6, 'Editing', 1, '', NULL, 'line_edit_complete', '', 1, NULL, '', '{}', 1),(35, 3, 'Grammar and punctuation check', '', 7, 'Editing', 1, '', NULL, 'grammar_checked', '', 1, NULL, '', '{}', 1),(36, 3, 'Consistency check (names, dates, details)', '', 8, 'Editing', 1, '', NULL, 'consistency_verified', '', 1, NULL, '', '{}', 1),(37, 3, 'Beta reader feedback incorporated', '', 9, 'Editing', 0, '', NULL, 'beta_feedback_applied', '', 1, NULL, '', '{}', 1),(38, 3, 'Professional editing review', '', 10, 'Editing', 0, '', NULL, 'pro_edit_complete', '', 1, NULL, '', '{}', 1),(39, 3, 'Final proofread', '', 11, 'Editing', 1, '', NULL, 'final_proofread_done', '', 1, NULL, '', '{}', 1),(40, 3, 'Format manuscript to industry standards', '', 12, 'Editing', 1, '', NULL, 'manuscript_formatted', '', 1, NULL, '', '{}', 1),(41, 4, 'Write book blurb/synopsis', '', 1, 'Publishing', 1, '', NULL, 'blurb_written', '', 1, NULL, '', '{}', 1),(42, 4, 'Create author bio', '', 2, 'Publishing', 1, '', NULL, 'author_bio_created', '', 1, NULL, '', '{}', 1),(43, 4, 'Design or commission book cover', '', 3, 'Publishing', 1, '', NULL, 'cover_designed', '', 1, NULL, '', '{}', 1),(44, 4, 'Format for print publication', '', 4, 'Publishing', 0, '', NULL, 'print_formatted', '', 1, NULL, '', '{}', 1),(45, 4, 'Format for ebook publication', '', 5, 'Publishing', 1, '', NULL, 'ebook_formatted', '', 1, NULL, '', '{}', 1),(46, 4, 'Register ISBN (if applicable)', '', 6, 'Publishing', 0, '', NULL, 'isbn_registered', '', 1, NULL, '', '{}', 1),(47, 4, 'Copyright registration', '', 7, 'Publishing', 0, '', NULL, 'copyright_registered', '', 1, NULL, '', '{}', 1),(48, 4, 'Create marketing plan', '', 8, 'Publishing', 0, '', NULL, 'marketing_plan_ready', '', 1, NULL, '', '{}', 1),(49, 4, 'Build author platform (website, social media)', '', 9, 'Publishing', 0, '', NULL, 'author_platform_built', '', 1, NULL, '', '{}', 1),(50, 4, 'Gather advance reviews', '', 10, 'Publishing', 0, '', NULL, 'reviews_gathered', '', 1, NULL, '', '{}', 1),(51, 4, 'Set publication date', '', 11, 'Publishing', 1, '', NULL, 'pub_date_set', '', 1, NULL, '', '{}', 1),(52, 4, 'Upload to publishing platform', '', 12, 'Publishing', 1, '', NULL, 'book_uploaded', '', 1, NULL, '', '{}', 1),(53, 4, 'Launch marketing campaign', '', 13, 'Publishing', 0, '', NULL, 'marketing_launched', '', 1, NULL, '', '{}', 1);
COMMIT;
BEGIN;
DELETE FROM "main"."checklist_templates";
INSERT INTO "main"."checklist_templates" ("id","name","description","domain_art_id","domain_type_id","phase","keywords","min_required_completion","is_active","is_system","created_by_id","created_at","updated_at") VALUES (1, 'Novel Writing - Planning Phase', 'Essential planning checklist for novel writing projects', 10, NULL, 'planning', '["planning", "preparation", "outline", "novel"]', 80, 1, 0, NULL, '2025-11-19 14:21:53.035030', '2025-11-19 14:21:53.035030'),(2, 'Novel Writing - Writing Phase', 'First draft writing checklist', 10, NULL, 'writing', '["writing", "draft", "chapters", "novel"]', 100, 1, 0, NULL, '2025-11-19 14:21:53.050731', '2025-11-19 14:21:53.050731'),(3, 'Novel Writing - Editing Phase', 'Revision and editing checklist', 10, NULL, 'editing', '["editing", "revision", "proofreading", "novel"]', 90, 1, 0, NULL, '2025-11-19 14:21:53.058311', '2025-11-19 14:21:53.058311'),(4, 'Novel Writing - Publishing Preparation', 'Pre-publication checklist', 10, NULL, 'publishing', '["publishing", "preparation", "marketing", "novel"]', 85, 1, 0, NULL, '2025-11-19 14:21:53.063898', '2025-11-19 14:21:53.063898');
COMMIT;
BEGIN;
DELETE FROM "main"."comic_dialogues";
COMMIT;
BEGIN;
DELETE FROM "main"."comic_panels";
COMMIT;
BEGIN;
DELETE FROM "main"."compliance_audit_log";
COMMIT;
BEGIN;
DELETE FROM "main"."compliance_incident_severity";
INSERT INTO "main"."compliance_incident_severity" ("id","code","name","description","is_active","sort_order","created_at","updated_at","color","authority_notification_required","affected_notification_required","notification_deadline_hours") VALUES (1, 'low', 'Gering', '', 1, 1, '2025-12-01 16:00:16.884158', '2025-12-01 16:00:16.884158', '#10B981', 0, 0, NULL),(2, 'medium', 'Mittel', '', 1, 2, '2025-12-01 16:00:16.891236', '2025-12-01 16:00:16.891236', '#F59E0B', 0, 0, NULL),(3, 'high', 'Hoch', '', 1, 3, '2025-12-01 16:00:16.898620', '2025-12-01 16:00:16.898620', '#EF4444', 1, 0, '72'),(4, 'critical', 'Kritisch', '', 1, 4, '2025-12-01 16:00:16.906186', '2025-12-01 16:00:16.906186', '#7F1D1D', 1, 1, '24');
COMMIT;
BEGIN;
DELETE FROM "main"."compliance_priority";
INSERT INTO "main"."compliance_priority" ("id","code","name","description","is_active","sort_order","created_at","updated_at","color","sla_hours") VALUES (1, 'low', 'Niedrig', '', 1, 1, '2025-12-01 16:00:16.856170', '2025-12-01 16:00:16.856170', '#3B82F6', 168),(2, 'medium', 'Mittel', '', 1, 2, '2025-12-01 16:00:16.862775', '2025-12-01 16:00:16.862775', '#F59E0B', 72),(3, 'high', 'Hoch', '', 1, 3, '2025-12-01 16:00:16.869642', '2025-12-01 16:00:16.869642', '#EF4444', 24),(4, 'critical', 'Kritisch', '', 1, 4, '2025-12-01 16:00:16.876741', '2025-12-01 16:00:16.876741', '#7F1D1D', 4);
COMMIT;
BEGIN;
DELETE FROM "main"."compliance_risk_level";
INSERT INTO "main"."compliance_risk_level" ("id","code","name","description","is_active","sort_order","created_at","updated_at","color","icon","score_min","score_max") VALUES (1, 'very_low', 'Sehr Gering', '', 1, 1, '2025-12-01 16:00:16.773131', '2025-12-01 16:00:16.773131', '#10B981', '', 0, 20),(2, 'low', 'Gering', '', 1, 2, '2025-12-01 16:00:16.781518', '2025-12-01 16:00:16.781518', '#3B82F6', '', 21, 40),(3, 'medium', 'Mittel', '', 1, 3, '2025-12-01 16:00:16.790138', '2025-12-01 16:00:16.790138', '#F59E0B', '', 41, 60),(4, 'high', 'Hoch', '', 1, 4, '2025-12-01 16:00:16.797755', '2025-12-01 16:00:16.797755', '#EF4444', '', 61, 80),(5, 'very_high', 'Sehr Hoch', '', 1, 5, '2025-12-01 16:00:16.804631', '2025-12-01 16:00:16.804631', '#7F1D1D', '', 81, 100);
COMMIT;
BEGIN;
DELETE FROM "main"."compliance_status";
INSERT INTO "main"."compliance_status" ("id","code","name","description","is_active","sort_order","created_at","updated_at","color","icon","is_terminal","allows_edit") VALUES (1, 'draft', 'Entwurf', '', 1, 1, '2025-12-01 16:00:16.811222', '2025-12-01 16:00:16.811222', '#9CA3AF', '', 0, 1),(2, 'in_progress', 'In Bearbeitung', '', 1, 2, '2025-12-01 16:00:16.817811', '2025-12-01 16:00:16.817811', '#3B82F6', '', 0, 1),(3, 'review', 'In Prüfung', '', 1, 3, '2025-12-01 16:00:16.825119', '2025-12-01 16:00:16.825119', '#F59E0B', '', 0, 0),(4, 'approved', 'Freigegeben', '', 1, 4, '2025-12-01 16:00:16.831548', '2025-12-01 16:00:16.831548', '#10B981', '', 0, 0),(5, 'rejected', 'Abgelehnt', '', 1, 5, '2025-12-01 16:00:16.839124', '2025-12-01 16:00:16.839124', '#EF4444', '', 1, 0),(6, 'archived', 'Archiviert', '', 1, 6, '2025-12-01 16:00:16.847814', '2025-12-01 16:00:16.847814', '#6B7280', '', 1, 0);
COMMIT;
BEGIN;
DELETE FROM "main"."compliance_tag";
COMMIT;
BEGIN;
DELETE FROM "main"."compliance_tagged_item";
COMMIT;
BEGIN;
DELETE FROM "main"."content_blocks";
COMMIT;
BEGIN;
DELETE FROM "main"."core_agent_executions";
COMMIT;
BEGIN;
DELETE FROM "main"."core_contentitem";
COMMIT;
BEGIN;
DELETE FROM "main"."core_customers";
INSERT INTO "main"."core_customers" ("id","name","short_name","customer_number","address_street","address_zip","address_city","address_state","address_country","contact_person","contact_email","contact_phone","contact_mobile","industry","tax_id","website","is_active","customer_type","priority","notes","metadata","created_at","updated_at","first_project_at","last_activity_at") VALUES (1, 'Test GmbH', 'Test', 'TEST-001', 'Teststraße 1', '12345', 'Teststadt', '', 'DE', 'Max Mustermann', 'test@test.de', '', '', '', '', '', 1, 'business', 'normal', '', '{}', '2025-11-27 11:30:42.208564', '2025-11-27 11:30:42.208564', NULL, NULL);
COMMIT;
BEGIN;
DELETE FROM "main"."core_locations";
COMMIT;
BEGIN;
DELETE FROM "main"."core_plugin_configurations";
COMMIT;
BEGIN;
DELETE FROM "main"."core_plugin_executions";
COMMIT;
BEGIN;
DELETE FROM "main"."core_plugin_registry";
COMMIT;
BEGIN;
DELETE FROM "main"."core_plugin_registry_depends_on";
COMMIT;
BEGIN;
DELETE FROM "main"."core_prompt_executions";
COMMIT;
BEGIN;
DELETE FROM "main"."core_prompt_templates";
INSERT INTO "main"."core_prompt_templates" ("id","name","template_key","domain","category","description","tags","system_prompt","user_prompt_template","required_variables","optional_variables","variable_defaults","variable_schemas","output_format","output_schema","max_tokens","temperature","top_p","frequency_penalty","presence_penalty","version","is_active","is_default","ab_test_group","ab_test_weight","examples","language","usage_count","success_count","failure_count","avg_quality_score","avg_execution_time","avg_tokens_used","avg_cost","created_at","updated_at","last_used_at","created_by_id","fallback_template_id","parent_template_id","preferred_llm_id") VALUES (1, 'Character Generation - Standard', 'character_generation', 'book_writing', 1, 'Generates detailed character profiles for fiction writing', '[]', 'You are an expert character development assistant for fiction writers.', 'Create a detailed character profile with the following elements:- Name: {{character_name}}- Role: {{character_role}}- Genre: {{genre}}Include: personality traits, background, motivations, conflicts, and unique characteristics.', '"[\"character_name\", \"character_role\", \"genre\"]"', '"[\"age\", \"gender\", \"occupation\"]"', '"{\"age\": \"30-35\", \"gender\": \"not specified\"}"', '{}', 2, '"{\"name\": \"string\", \"personality\": \"string\", \"background\": \"string\", \"motivations\": \"array\", \"conflicts\": \"array\"}"', 1000, 0.8, 0.9, 0.0, 0.0, '1', 1, 1, 0, 1.0, '[]', 1, 0, 0, 0, 0.0, 0.0, 0, 0, '2025-11-27 13:42:33.206713', '2025-11-27 13:42:33.207720', NULL, 1, NULL, NULL, NULL),(2, 'Chapter Outline Generator', 'chapter_outline', 'book_writing', 2, 'Creates structured chapter outlines with story beats', '[]', 'You are an expert story structure consultant.', 'Generate a chapter outline for:- Chapter Number: {{chapter_number}}- Story Arc: {{story_arc}}- Previous Events: {{previous_events}}Create 5-7 story beats with emotional arcs and character development.', '"[\"chapter_number\", \"story_arc\"]"', '"[\"previous_events\", \"target_word_count\"]"', '"{\"target_word_count\": \"3000\"}"', '{}', 2, '{}', 800, 0.7, 0.85, 0.0, 0.0, '1', 1, 0, 0, 1.0, '[]', 1, 0, 0, 0, 0.0, 0.0, 0, 0, '2025-11-27 13:42:33.218367', '2025-11-27 13:42:33.218367', NULL, 1, NULL, NULL, NULL),(3, 'Dialogue Enhancement - Natural Speech', 'dialogue_enhancement', 'book_writing', 8, 'Improves dialogue to sound more natural and character-specific', '[]', 'You are a dialogue coach specializing in natural, character-driven conversation.', 'Enhance this dialogue:{{original_dialogue}}Character Voice Guidelines:- Character: {{character_name}}- Personality: {{personality_traits}}- Background: {{background}}Make it sound natural and true to the character.', '"[\"original_dialogue\", \"character_name\"]"', '"[\"personality_traits\", \"background\", \"dialect\"]"', '{}', '{}', 1, '{}', 500, 0.75, 1.0, 0.0, 0.0, '1.1.0', 1, 0, 0, 1.0, '[]', 1, 0, 0, 0, 0.0, 0.0, 0, 0, '2025-11-27 13:42:33.227700', '2025-11-27 13:42:33.228212', NULL, 1, NULL, NULL, NULL),(4, 'Plot Development Assistant', 'plot_development', 'book_writing', 9, 'Creates comprehensive plot structures with three-act breakdowns and subplot development', '[]', 'You are a master storyteller specializing in plot structure and narrative design.Your expertise includes:- Three-act structure and story beats- Character-driven vs. plot-driven narratives- Subplot weaving and thematic resonance- Conflict escalation and resolution- Genre-specific conventions and tropes', 'Develop the plot structure for: "{{book_title}}"Project Details:- Genre: {{genre}}- Target Audience: {{target_audience}}- Word Count: {{word_count}}- Tone: {{tone}}Story Premise:{{premise}}Main Characters:{{main_characters}}Provide:1. Three-Act Structure Breakdown2. Major Plot Points (Inciting Incident, Midpoint, Climax, Resolution)3. Subplot Ideas (2-3 subplots)4. Conflict Escalation Path5. Thematic Elements6. Potential Plot Twists', '"[\"book_title\", \"genre\", \"premise\"]"', '"[\"target_audience\", \"word_count\", \"tone\", \"main_characters\"]"', '"{\"target_audience\": \"Adult\", \"word_count\": \"80000-100000\", \"tone\": \"Balanced\", \"main_characters\": \"To be developed\"}"', '{}', 3, '{}', 2500, 0.75, 1.0, 0.0, 0.0, '1', 1, 1, 0, 1.0, '[]', 1, 0, 0, 0, 0.0, 0.0, 0, 0, '2025-11-27 13:42:33.237007', '2025-11-27 13:42:33.237523', NULL, 1, NULL, NULL, NULL),(5, 'World Building Constructor', 'world_building', 'book_writing', 3, 'Constructs detailed fictional worlds with consistent internal logic and rich backstory', '[]', 'You are a world-building specialist for fiction writing.Your skills include:- Creating immersive, believable fictional worlds- Establishing cultural, social, and political systems- Designing geography, history, and mythology- Developing magic systems or technology frameworks- Ensuring world consistency and internal logic', 'Build the world for: "{{book_title}}"World Type: {{world_type}}Genre: {{genre}}Time Period: {{time_period}}Core Concept:{{core_concept}}Required Elements:{{required_elements}}Create:1. World Overview (setting, geography, climate)2. Society & Culture (government, social structure, customs)3. History & Mythology (key historical events, legends)4. Technology/Magic System (rules, limitations, costs)5. Economy & Trade (resources, currency, commerce)6. Conflicts & Tensions (internal/external threats)7. Unique World Details (what makes this world special)', '"[\"book_title\", \"world_type\", \"genre\"]"', '"[\"time_period\", \"core_concept\", \"required_elements\"]"', '"{\"time_period\": \"Contemporary\", \"core_concept\": \"To be defined\", \"required_elements\": \"Standard genre elements\"}"', '{}', 3, '{}', 3000, 0.8, 1.0, 0.0, 0.0, '1', 1, 1, 0, 1.0, '[]', 1, 0, 0, 0, 0.0, 0.0, 0, 0, '2025-11-27 13:42:33.246632', '2025-11-27 13:42:33.247147', NULL, 1, NULL, NULL, NULL),(6, 'Scene Description Generator', 'scene_description', 'book_writing', 1, 'Generates vivid, sensory-rich scene descriptions with character POV and atmosphere', '[]', 'You are a prose writer specializing in vivid, engaging scene descriptions.Your writing style:- Shows rather than tells- Engages multiple senses (sight, sound, smell, touch, taste)- Uses concrete, specific details over abstract descriptions- Balances description with pacing- Reflects character POV and emotional state', 'Write a detailed scene description for:Scene Title: {{scene_title}}Location: {{location}}Time of Day: {{time_of_day}}Weather/Atmosphere: {{atmosphere}}Characters Present: {{characters_present}}POV Character: {{pov_character}}Character''s Emotional State: {{character_emotion}}Scene Purpose: {{scene_purpose}}Scene Beats:{{scene_beats}}Write a vivid {{word_count_target}}-word scene description that:- Establishes the setting through sensory details- Reflects the POV character''s perspective- Builds atmosphere matching the mood- Includes character reactions and observations- Advances the plot or develops character', '"[\"scene_title\", \"location\", \"pov_character\", \"scene_purpose\"]"', '"[\"time_of_day\", \"atmosphere\", \"characters_present\", \"character_emotion\", \"scene_beats\", \"word_count_target\"]"', '"{\"time_of_day\": \"Daytime\", \"atmosphere\": \"Normal\", \"characters_present\": \"POV character only\", \"character_emotion\": \"Neutral\", \"scene_beats\": \"To be determined\", \"word_count_target\": \"500\"}"', '{}', 1, '{}', 1500, 0.85, 1.0, 0.0, 0.0, '1', 1, 1, 0, 1.0, '[]', 1, 0, 0, 0, 0.0, 0.0, 0, 0, '2025-11-27 13:42:33.256380', '2025-11-27 13:42:33.257386', NULL, 1, NULL, NULL, NULL),(7, 'Chapter Outline Generator', 'chapter_outline_generation', 'book_writing', 2, 'Generates detailed chapter outlines based on project context and story position', '[]', 'You are a professional fiction writing assistant specialized in story structure and chapter planning.Your task is to create detailed chapter outlines that serve as blueprints for compelling narrative chapters.', 'Create a detailed outline for Chapter {{chapter_number}}: "{{chapter_title}}"PROJECT CONTEXT:- Title: {{title}}- Genre: {{genre}}- Premise: {{premise}}- Themes: {{themes}}- Target Audience: {{target_audience}}MAIN CHARACTERS:- Protagonist: {{protagonist_name}}  {{protagonist_description}}- Antagonist: {{antagonist_name}}  {{antagonist_description}}STORY POSITION:- Chapter {{chapter_number}} of the story- Story Position: {{story_position}}- Current Beat: {{current_beat_name}}CHAPTER REQUIREMENTS:- Chapter Number: {{chapter_number}}- Title: {{chapter_title}}- Target Word Count: {{word_count}}- Plot Points to Address: {{plot_points}}Please provide a structured outline with:1. 3-4 main sections with headings2. Brief description for each section3. Key elements to include4. Estimated word count per sectionIMPORTANT: Follow the established character roles and descriptions exactly. Pay close attention to the premise and character backgrounds.Format your response as a clear, structured outline.', '["chapter_number", "chapter_title", "title", "genre"]', '["premise", "themes", "target_audience", "protagonist_name", "protagonist_description", "antagonist_name", "antagonist_description", "story_position", "current_beat_name", "word_count", "plot_points"]', '{"word_count": 3000, "plot_points": "General story progression", "premise": "N/A", "themes": "N/A", "target_audience": "Adult", "protagonist_name": "the protagonist", "protagonist_description": "Main character", "antagonist_name": "the antagonist", "antagonist_description": "Opposition force", "story_position": "N/A", "current_beat_name": "N/A"}', '{}', 1, '{}', 1000, 0.7, 1.0, 0.0, 0.0, '1', 1, 1, 0, 1.0, '[]', 1, 0, 0, 0, 0.0, 0.0, 0, 0, '2025-11-27 13:42:33.266463', '2025-11-27 13:42:33.266968', NULL, 1, NULL, NULL, NULL),(8, 'Chapter Content Generator', 'chapter_content_generation', 'book_writing', 2, 'Generates full chapter content in prose form based on outline and project context', '[]', 'You are a professional fiction writer with expertise in crafting compelling narrative prose.Your task is to write engaging chapter content based on a detailed outline, maintaining consistent character voices and story themes.Write in a vivid, immersive style that draws readers into the story.', 'Write Chapter {{chapter_number}} based on the following outline and context.PROJECT CONTEXT:- Title: {{title}}- Genre: {{genre}}- Premise: {{premise}}- Themes: {{themes}}- Target Audience: {{target_audience}}MAIN CHARACTERS:- Protagonist: {{protagonist_name}}  {{protagonist_description}}- Antagonist: {{antagonist_name}}CHAPTER OUTLINE:{{outline}}WRITING REQUIREMENTS:- Write in third person limited perspective, focusing on {{protagonist_name}}- Target length: Approximately {{word_count}} words for the complete chapter- Include dialogue: {{include_dialogue}}- Style: {{style_notes}}- Maintain consistency with the premise: the story explores themes of {{themes}}IMPORTANT:- Follow the outline structure closely- Show don''t tell - use vivid sensory details- Develop characters through actions and dialogue- Create emotional resonance with readers- Maintain proper pacing throughoutWrite the complete chapter now, following the outline sections:', '["chapter_number", "title", "genre", "outline", "protagonist_name"]', '["premise", "themes", "target_audience", "protagonist_description", "antagonist_name", "word_count", "include_dialogue", "style_notes"]', '{"premise": "N/A", "themes": "N/A", "target_audience": "Adult", "protagonist_description": "Main character", "antagonist_name": "the antagonist", "word_count": 2500, "include_dialogue": "Yes, include natural, character-appropriate dialogue", "style_notes": "Engaging literary fiction style with vivid descriptions and emotional depth"}', '{}', 1, '{}', 4000, 0.8, 1.0, 0.0, 0.0, '1', 1, 1, 0, 1.0, '[]', 1, 0, 0, 0, 0.0, 0.0, 0, 0, '2025-11-27 13:42:33.275257', '2025-11-27 13:42:33.275257', NULL, 1, NULL, NULL, NULL),(9, 'Chapter Section Expander', 'chapter_section_expansion', 'book_writing', 2, 'Expands individual chapter sections with rich descriptive prose', '[]', 'You are a professional fiction writer specializing in descriptive prose and scene development.Your task is to expand brief section outlines into rich, detailed narrative prose that immerses readers in the story world.', 'Expand the following chapter section into detailed prose.PROJECT CONTEXT:- Title: {{title}}- Genre: {{genre}}- Themes: {{themes}}CHARACTER FOCUS:- {{protagonist_name}}: {{protagonist_description}}SECTION TO EXPAND:{{section_outline}}REQUIREMENTS:- Target length: {{section_word_count}} words- Perspective: Third person limited, focusing on {{protagonist_name}}- Include dialogue: {{include_dialogue}}- Tone: {{tone}}IMPORTANT:- Use vivid sensory details- Show character emotions through actions and body language- Maintain the story''s themes: {{themes}}- Keep pacing appropriate for the sceneWrite the expanded section now:', '["section_outline", "protagonist_name", "title", "genre"]', '["themes", "protagonist_description", "section_word_count", "include_dialogue", "tone"]', '{"themes": "N/A", "protagonist_description": "Main character", "section_word_count": 750, "include_dialogue": "Yes", "tone": "Engaging and immersive"}', '{}', 1, '{}', 2000, 0.8, 1.0, 0.0, 0.0, '1', 1, 0, 0, 1.0, '[]', 1, 0, 0, 0, 0.0, 0.0, 0, 0, '2025-11-27 13:42:33.283558', '2025-11-27 13:42:33.283558', NULL, 1, NULL, NULL, NULL),(10, 'Chapter Writer', 'chapter_writer', 'book_writing', 2, 'Generates full chapter content from outline and context', '[]', 'You are an expert fiction writer specializing in science fiction novels.Your task is to generate engaging, well-structured novel chapters that:1. Maintain Consistency: Stay true to established characters and plot2. Show, Don''t Tell: Use vivid descriptions and dialogue3. Pacing: Balance action, dialogue, and introspection4. Character Voice: Each character has distinct voice5. Plot Advancement: Move the story forward meaningfullyWrite in past tense, third person unless specified otherwise.', 'Generate a novel chapter with approximately {target_word_count} words.OUTLINE:{outline}{% if genre %}GENRE: {genre}{% endif %}{% if tone %}TONE: {tone}{% endif %}{% if pov %}POV: {pov}{% endif %}Write engaging prose with:- Vivid scene descriptions- Natural dialogue- Character emotions and internal thoughts- Smooth scene transitions- A compelling hook or cliffhanger at the endBegin the chapter content now (no title or chapter number):', '["outline", "target_word_count"]', '["genre", "tone", "pov", "characters", "world_details"]', '{"tone": "suspenseful", "pov": "third person limited", "target_word_count": 3000}', '{}', 1, '{}', 8000, 0.8, 1.0, 0.0, 0.0, '1', 1, 1, 0, 1.0, '[]', 1, 0, 0, 0, 0.0, 0.0, 0, 0, '2025-11-27 13:42:33.291128', '2025-11-27 13:42:33.292642', NULL, 1, NULL, NULL, NULL),(11, 'Dialogue Enhancer', 'dialogue_enhancer', 'book_writing', 5, 'Improves dialogue to be more natural and character-specific', '[]', 'You are an expert fiction writer specializing in science fiction novels.Your task is to generate engaging, well-structured novel chapters that:1. Maintain Consistency: Stay true to established characters and plot2. Show, Don''t Tell: Use vivid descriptions and dialogue3. Pacing: Balance action, dialogue, and introspection4. Character Voice: Each character has distinct voice5. Plot Advancement: Move the story forward meaningfullyWrite in past tense, third person unless specified otherwise.', 'Generate a novel chapter with approximately {target_word_count} words.OUTLINE:{outline}{% if genre %}GENRE: {genre}{% endif %}{% if tone %}TONE: {tone}{% endif %}{% if pov %}POV: {pov}{% endif %}Write engaging prose with:- Vivid scene descriptions- Natural dialogue- Character emotions and internal thoughts- Smooth scene transitions- A compelling hook or cliffhanger at the endBegin the chapter content now (no title or chapter number):', '["outline", "target_word_count"]', '["genre", "tone", "pov", "characters", "world_details"]', '{"tone": "suspenseful", "pov": "third person limited", "target_word_count": 3000}', '{}', 1, '{}', 3000, 0.75, 1.0, 0.0, 0.0, '1', 1, 0, 0, 1.0, '[]', 1, 0, 0, 0, 0.0, 0.0, 0, 0, '2025-11-27 13:42:33.301421', '2025-11-27 13:42:33.301421', NULL, 1, NULL, NULL, '8'),(12, 'Character Creator v1', 'character_creator_v1', 'book_writing', 1, 'AI-powered character generation with personality, backstory, and traits', '[]', 'You are an expert character designer for creative writing.Your expertise includes:- Creating compelling, original characters- Developing realistic personalities and motivations- Writing engaging backstories- Ensuring characters fit naturally into their story world- Balancing character traits for interesting dynamicsGenerate characters that are:- Memorable and unique- Consistent with the story''s genre and setting- Well-rounded with strengths and flaws- Motivated by clear goals and conflicts', 'Create a {{ role }} character for: {{ project_title }}**Genre:** {{ genre }}**World Setting:** {{ world_name }} - {{ world_description }}**Existing Characters:**{% for char in existing_characters %}- {{ char.name }} ({{ char.role }}): {{ char.personality }}{% endfor %}**Requirements:**- Unique name (not similar to existing characters)- Fits world setting and genre conventions- Has clear motivation and internal/external conflict- Age-appropriate for {{ genre }} genre- {{ role }}-appropriate traits and background**Character Role:** {{ role }}{% if age_range %}**Age Range:** {{ age_range }}{% endif %}{% if specific_traits %}**Must Include Traits:** {{ specific_traits }}{% endif %}Return as JSON with this exact structure:{  "name": "character full name",  "role": "{{ role }}",  "traits": {    "primary": "main personality trait",    "secondary": "secondary trait",    "flaw": "character flaw"  },  "appearance": {    "age": 30,    "height": "height description",    "build": "body build",    "distinctive_features": "unique physical features"  },  "background": {    "origin": "where they come from",    "occupation": "their job/role",    "motivation": "what drives them",    "secret": "hidden aspect of their past (optional)"  },  "relationships": [    "relationship to other characters"  ],  "arc_summary": "how they will evolve through the story"}Make the character compelling, original, and memorable!', '["project_title", "genre", "role"]', '["world_name", "world_description", "existing_characters", "age_range", "specific_traits"]', '{"world_name": "Unknown World", "world_description": "A fictional world", "existing_characters": []}', '{}', 2, '{}', 1500, 0.8, 0.95, 0.0, 0.0, '1', 1, 1, 0, 1.0, '[]', 1, 0, 0, 0, 0.0, 0.0, 0, 0, '2025-11-27 13:42:33.310028', '2025-11-27 13:42:33.311543', NULL, 1, NULL, NULL, '8'),(13, 'Story Outline Creator v1', 'outline_creator_v1', 'book_writing', 4, 'Generates structured story outlines using proven narrative frameworks', '[]', 'You are an expert story architect and narrative designer.Your expertise includes:- Classical story structures (3-Act, Hero''s Journey, Save the Cat)- Chapter-level plotting and pacing- Character arc integration- Conflict and resolution design- Genre-specific conventionsCreate outlines that:- Follow proven narrative frameworks- Have clear act/chapter structure- Include compelling conflict and stakes- Integrate character arcs naturally- Maintain pacing and tension- Fit the specified genre and tone', 'Create a {{ structure }} story outline for: {{ project_title }}**Genre:** {{ genre }}**Structure:** {{ structure }}**Number of Chapters:** {{ num_chapters }}**Story Premise:**{{ premise }}**Main Characters:**{% for char in characters %}- **{{ char.name }}** ({{ char.role }}): {{ char.motivation }}  Arc: {{ char.arc }}{% endfor %}**World Setting:**{{ world_description }}**Structure Guidelines:**{% if structure == "three_act" %}- Act I (Setup): 25% - Introduce characters, world, and inciting incident- Act II (Confrontation): 50% - Rising action, complications, midpoint twist- Act III (Resolution): 25% - Climax, falling action, resolution{% elif structure == "hero_journey" %}- Ordinary World, Call to Adventure, Refusal, Meeting Mentor- Crossing Threshold, Tests/Allies/Enemies, Approach- Ordeal, Reward, Road Back- Resurrection, Return with Elixir{% elif structure == "save_the_cat" %}- Opening Image, Theme Stated, Set-Up, Catalyst- Debate, Break into Two, B Story- Fun and Games, Midpoint, Bad Guys Close In- All Is Lost, Dark Night of Soul, Break into Three- Finale, Final Image{% endif %}**Requirements:**- Each chapter needs: Title, Act/Phase, Goal, Conflict, Resolution- Character arcs must progress through chapters- Pacing appropriate for {{ genre }}- Clear story beats and turning points- Engaging hooks at chapter endsReturn as JSON with this structure:{  "structure": "{{ structure }}",  "total_chapters": {{ num_chapters }},  "acts": [    {      "act_number": 1,      "act_name": "Setup",      "chapters": [1, 2, 3, 4, 5]    }  ],  "chapters": [    {      "number": 1,      "title": "Chapter Title",      "act": 1,      "phase": "Opening",      "summary": "Brief chapter summary",      "goal": "What the protagonist tries to achieve",      "conflict": "What opposes them",      "resolution": "How the chapter ends",      "character_arcs": {        "Character Name": "How they change/progress"      },      "key_beats": ["Important story beat 1", "Beat 2"]    }  ],  "story_beats": [    {      "beat_name": "Inciting Incident",      "chapter": 2,      "description": "What happens"    }  ]}Create a compelling, well-paced outline!', '["project_title", "genre", "structure", "num_chapters", "premise"]', '["characters", "world_description"]', '{"structure": "three_act", "num_chapters": 15, "characters": [], "world_description": "A fictional world"}', '{}', 2, '{}', 3000, 0.7, 0.9, 0.0, 0.0, '1', 1, 1, 0, 1.0, '[]', 1, 0, 0, 0, 0.0, 0.0, 0, 0, '2025-11-27 13:42:33.320353', '2025-11-27 13:42:33.320353', NULL, 1, NULL, NULL, NULL);
COMMIT;
BEGIN;
DELETE FROM "main"."core_prompt_versions";
COMMIT;
BEGIN;
DELETE FROM "main"."debug_toolbar_historyentry";
COMMIT;
BEGIN;
DELETE FROM "main"."django_admin_log";
COMMIT;
BEGIN;
DELETE FROM "main"."django_content_type";
INSERT INTO "main"."django_content_type" ("id","app_label","model") VALUES (1, 'admin', 'logentry'),(2, 'auth', 'permission'),(3, 'auth', 'group'),(4, 'auth', 'user'),(5, 'contenttypes', 'contenttype'),(6, 'sessions', 'session'),(7, 'core', 'domainart'),(8, 'core', 'agent'),(9, 'core', 'agentexecution'),(10, 'core', 'contentitem'),(11, 'core', 'customer'),(12, 'core', 'bookstatus'),(13, 'core', 'domainphase'),(14, 'core', 'domainsection'),(15, 'core', 'domainsectionitem'),(16, 'core', 'domaintype'),(17, 'core', 'domainproject'),(18, 'core', 'genre'),(19, 'core', 'location'),(20, 'core', 'pluginregistry'),(21, 'core', 'pluginexecution'),(22, 'core', 'prompttemplate'),(23, 'core', 'promptexecution'),(24, 'core', 'pluginconfiguration'),(25, 'core', 'handler'),(26, 'core', 'promptversion'),(27, 'writing_hub', 'bookproject'),(28, 'writing_hub', 'chapter'),(29, 'writing_hub', 'bookcharacter'),(30, 'writing_hub', 'character'),(31, 'writing_hub', 'idea'),(32, 'writing_hub', 'world'),(33, 'cad_analysis', 'analysisjob'),(34, 'cad_analysis', 'analysisreport'),(35, 'cad_analysis', 'drawingfile'),(36, 'cad_analysis', 'analysisresult'),(37, 'expert_hub', 'documenttypemodel'),(38, 'expert_hub', 'facilitytype'),(39, 'expert_hub', 'processingstatustype'),(40, 'expert_hub', 'zonetype'),(41, 'expert_hub', 'building'),(42, 'expert_hub', 'exschutzdocument'),(43, 'expert_hub', 'auditlog'),(44, 'expert_hub', 'facility'),(45, 'expert_hub', 'gefahrstoff'),(46, 'expert_hub', 'hazmatcatalog'),(47, 'expert_hub', 'facilityhazmat'),(48, 'expert_hub', 'schutzmaßnahme'),(49, 'expert_hub', 'exzone'),(50, 'expert_hub', 'assessment'),(51, 'checklist_system', 'checklisttemplate'),(52, 'checklist_system', 'checklistitem'),(53, 'checklist_system', 'checklistinstance'),(54, 'checklist_system', 'checklistitemstatus'),(55, 'workflow_system', 'workflow'),(56, 'workflow_system', 'workflowcheckpoint'),(57, 'bfagent', 'agentexecutions'),(58, 'bfagent', 'agents'),(59, 'bfagent', 'bookproject'),(60, 'bfagent', 'llm'),(61, 'bfagent', 'llms'),(62, 'bfagent', 'actionhandler'),(63, 'bfagent', 'actiontemplate'),(64, 'bfagent', 'agentaction'),(65, 'bfagent', 'agentartifacts'),(66, 'bfagent', 'agenttype'),(67, 'bfagent', 'bookchapters'),(68, 'bfagent', 'booktypephase'),(69, 'bfagent', 'booktypes'),(70, 'bfagent', 'bugfixplan'),(71, 'bfagent', 'chapterrating'),(72, 'bfagent', 'characters'),(73, 'bfagent', 'comicdialogues'),(74, 'bfagent', 'comicpanels'),(75, 'bfagent', 'comment'),(76, 'bfagent', 'componentchangelog'),(77, 'bfagent', 'componentregistry'),(78, 'bfagent', 'componentusagelog'),(79, 'bfagent', 'contentblock'),(80, 'bfagent', 'contextenrichmentlog'),(81, 'bfagent', 'contextschema'),(82, 'bfagent', 'contextsource'),(83, 'bfagent', 'enrichmentresponse'),(84, 'bfagent', 'featuredocument'),(85, 'bfagent', 'featuredocumentkeyword'),(86, 'bfagent', 'fielddefinition'),(87, 'bfagent', 'fieldgroup'),(88, 'bfagent', 'fieldtemplate'),(89, 'bfagent', 'fieldusage'),(90, 'bfagent', 'fieldvaluehistory'),(91, 'bfagent', 'generatedimage'),(92, 'bfagent', 'generationlog'),(93, 'bfagent', 'graphqloperation'),(94, 'bfagent', 'handlerexecution'),(95, 'bfagent', 'illustrationimage'),(96, 'bfagent', 'illustrationstyle'),(97, 'bfagent', 'imagegenerationbatch'),(98, 'bfagent', 'imagestyleprofile'),(99, 'bfagent', 'llmpromptexecution'),(100, 'bfagent', 'llmprompttemplate'),(101, 'bfagent', 'location'),(102, 'bfagent', 'migrationconflict'),(103, 'bfagent', 'migrationregistry'),(104, 'bfagent', 'phaseactionconfig'),(105, 'bfagent', 'phaseagentconfig'),(106, 'bfagent', 'plotpoint'),(107, 'bfagent', 'projectfieldvalue'),(108, 'bfagent', 'projectphaseaction'),(109, 'bfagent', 'projectphasehistory'),(110, 'bfagent', 'projecttypephase'),(111, 'bfagent', 'promptexecution'),(112, 'bfagent', 'prompttemplatelegacy'),(113, 'bfagent', 'prompttemplatetest'),(114, 'bfagent', 'queryperformancelog'),(115, 'bfagent', 'requirementtestlink'),(116, 'bfagent', 'reviewparticipant'),(117, 'bfagent', 'reviewround'),(118, 'bfagent', 'storyarc'),(119, 'bfagent', 'storybible'),(120, 'bfagent', 'storychapter'),(121, 'bfagent', 'storymemory'),(122, 'bfagent', 'storyproject'),(123, 'bfagent', 'storystrand'),(124, 'bfagent', 'targetaudience'),(125, 'bfagent', 'templatefield'),(126, 'bfagent', 'testbug'),(127, 'bfagent', 'testcase'),(128, 'bfagent', 'testcoveragereport'),(129, 'bfagent', 'testexecution'),(130, 'bfagent', 'testlog'),(131, 'bfagent', 'testrequirement'),(132, 'bfagent', 'testscreenshot'),(133, 'bfagent', 'testsession'),(134, 'bfagent', 'tooldefinition'),(135, 'bfagent', 'toolexecution'),(136, 'bfagent', 'workflowphase'),(137, 'bfagent', 'workflowphasestep'),(138, 'bfagent', 'workflowtemplate'),(139, 'bfagent', 'worldrule'),(140, 'bfagent', 'worlds'),(141, 'bfagent', 'worldsetting'),(142, 'bfagent', 'writingstatus'),(143, 'control_center', 'workflowdomain'),(144, 'control_center', 'projecttype'),(145, 'control_center', 'navigationsection'),(146, 'control_center', 'workflowtemplate'),(147, 'control_center', 'usernavigationpreference'),(148, 'control_center', 'navigationitem'),(149, 'genagent', 'customdomain'),(150, 'genagent', 'phase'),(151, 'genagent', 'action'),(152, 'genagent', 'executionlog'),(153, 'medtrans', 'customer'),(154, 'medtrans', 'presentation'),(155, 'medtrans', 'presentationtext'),(156, 'presentation_studio', 'templatecollection'),(157, 'presentation_studio', 'presentation'),(158, 'presentation_studio', 'enhancement'),(159, 'presentation_studio', 'designprofile'),(160, 'presentation_studio', 'previewslide'),(161, 'debug_toolbar', 'historyentry'),(162, 'expert_hub', 'datasourceconfig'),(163, 'expert_hub', 'datasourcemetric'),(164, 'expert_hub', 'substancedataimport'),(165, 'compliance_core', 'incidentseverity'),(166, 'compliance_core', 'compliancetag'),(167, 'compliance_core', 'complianceauditlog'),(168, 'compliance_core', 'priority'),(169, 'compliance_core', 'risklevel'),(170, 'compliance_core', 'compliancetaggeditem'),(171, 'compliance_core', 'compliancestatus'),(172, 'dsb', 'branche'),(173, 'dsb', 'vorfall'),(174, 'dsb', 'verarbeitung'),(175, 'dsb', 'rechtsform'),(176, 'dsb', 'vorfalltyp'),(177, 'dsb', 'rechtsgrundlage'),(178, 'dsb', 'datenkategorie'),(179, 'dsb', 'mandant'),(180, 'dsb', 'dsbdokument'),(181, 'dsb', 'tomkategorie'),(182, 'dsb', 'mandanttom'),(183, 'dsb', 'tommassnahme'),(184, 'expert_hub', 'equipmentcategory'),(185, 'expert_hub', 'explosiongroup'),(186, 'expert_hub', 'ignitionprotectiontype'),(187, 'expert_hub', 'physicalstate'),(188, 'expert_hub', 'temperatureclass'),(189, 'expert_hub', 'regulationtype'),(190, 'expert_hub', 'regulation'),(191, 'expert_hub', 'explosionsschutzgutachten'),(192, 'expert_hub', 'equipment'),(193, 'cad_analysis', 'analysiscategory'),(194, 'cad_analysis', 'buildingtype'),(195, 'cad_analysis', 'compliancestandard'),(196, 'cad_analysis', 'drawingtype'),(197, 'cad_analysis', 'layerstandard'),(198, 'cad_analysis', 'severitylevel'),(199, 'research', 'researchfocuslookup'),(200, 'research', 'sourcetypelookup'),(201, 'research', 'citationstylelookup'),(202, 'research', 'researchsource'),(203, 'research', 'researchhandlerexecution'),(204, 'research', 'handlertypelookup'),(205, 'research', 'researchdepthlookup'),(206, 'research', 'synthesistypelookup'),(207, 'research', 'researchproject'),(208, 'research', 'researchresult'),(209, 'research', 'researchsession'),(210, 'authtoken', 'token'),(211, 'authtoken', 'tokenproxy');
COMMIT;
BEGIN;
DELETE FROM "main"."django_migrations";
INSERT INTO "main"."django_migrations" ("id","app","name","applied") VALUES (1, 'contenttypes', '0001_initial', '2025-11-27 11:24:22.622280'),(2, 'auth', '0001_initial', '2025-11-27 11:24:22.654514'),(3, 'admin', '0001_initial', '2025-11-27 11:24:22.675841'),(4, 'admin', '0002_logentry_remove_auto_add', '2025-11-27 11:24:22.695819'),(5, 'admin', '0003_logentry_add_action_flag_choices', '2025-11-27 11:24:22.708337'),(6, 'contenttypes', '0002_remove_content_type_name', '2025-11-27 11:24:22.739506'),(7, 'auth', '0002_alter_permission_name_max_length', '2025-11-27 11:24:22.760274'),(8, 'auth', '0003_alter_user_email_max_length', '2025-11-27 11:24:22.777061'),(9, 'auth', '0004_alter_user_username_opts', '2025-11-27 11:24:22.789634'),(10, 'auth', '0005_alter_user_last_login_null', '2025-11-27 11:24:22.810101'),(11, 'auth', '0006_require_contenttypes_0002', '2025-11-27 11:24:22.817629'),(12, 'auth', '0007_alter_validators_add_error_messages', '2025-11-27 11:24:22.831145'),(13, 'auth', '0008_alter_user_username_max_length', '2025-11-27 11:24:22.851780'),(14, 'auth', '0009_alter_user_last_name_max_length', '2025-11-27 11:24:22.870347'),(15, 'auth', '0010_alter_group_name_max_length', '2025-11-27 11:24:22.891259'),(16, 'auth', '0011_update_proxy_permissions', '2025-11-27 11:24:22.902902'),(17, 'auth', '0012_alter_user_first_name_max_length', '2025-11-27 11:24:22.925452'),(18, 'bfagent', '0001_initial', '2025-11-27 11:24:23.155708'),(19, 'core', '0001_initial', '2025-11-27 11:24:24.991209'),(20, 'bfagent', '0002_initial', '2025-11-27 11:24:46.552645'),(21, 'cad_analysis', '0001_initial', '2025-11-27 11:24:47.708040'),(22, 'checklist_system', '0001_initial', '2025-11-27 11:24:48.775133'),(23, 'control_center', '0001_initial', '2025-11-27 11:24:50.157979'),(24, 'debug_toolbar', '0001_initial', '2025-11-27 11:24:50.171708'),(25, 'expert_hub', '0001_initial', '2025-11-27 11:24:53.875207'),(26, 'expert_hub', '0002_assessment', '2025-11-27 11:24:54.418192'),(27, 'genagent', '0001_initial', '2025-11-27 11:24:54.482962'),(28, 'medtrans', '0001_initial', '2025-11-27 11:24:54.920282'),(29, 'presentation_studio', '0001_initial', '2025-11-27 11:24:57.121093'),(30, 'sessions', '0001_initial', '2025-11-27 11:24:57.147095'),(31, 'workflow_system', '0001_initial', '2025-11-27 11:24:58.074559'),(32, 'writing_hub', '0001_initial', '2025-11-27 11:25:01.381039'),(33, 'expert_hub', '0003_add_data_source_models', '2025-11-30 15:25:19.702999'),(34, 'compliance_core', '0001_initial', '2025-12-01 15:58:33.847340'),(35, 'dsb', '0001_initial', '2025-12-01 15:58:34.863427'),(36, 'dsb', '0002_tomkategorie_tommassnahme_mandanttom', '2025-12-01 16:41:00.152114'),(37, 'expert_hub', '0004_equipmentcategory_explosiongroup_and_more', '2025-12-01 19:32:49.064966'),(38, 'expert_hub', '0005_regulationtype_regulation_explosionsschutzgutachten_and_more', '2025-12-01 20:25:58.532456'),(39, 'cad_analysis', '0002_analysiscategory_buildingtype_compliancestandard_and_more', '2025-12-01 21:48:55.074793'),(40, 'research', '0001_initial', '2025-12-02 14:34:17.089870'),(41, 'authtoken', '0001_initial', '2025-12-03 10:46:29.758940'),(42, 'authtoken', '0002_auto_20160226_1747', '2025-12-03 10:46:30.436658'),(43, 'authtoken', '0003_tokenproxy', '2025-12-03 10:46:30.448314'),(44, 'authtoken', '0004_alter_tokenproxy_options', '2025-12-03 10:46:30.467209');
COMMIT;
BEGIN;
DELETE FROM "main"."django_session";
INSERT INTO "main"."django_session" ("session_key","session_data","expire_date") VALUES ('jkotvvai02sfayap65688imrcctam2ck', '.eJxVjDsOwjAQBe_iGllx_Kek5wzWeneDA8iW4qRC3B0ipYD2zcx7iQTbWtLWeUkzibMYxel3y4APrjugO9Rbk9jqusxZ7oo8aJfXRvy8HO7fQYFevvWEPhAiADlUUUc7cbDG8hCDgYysnVKUKY7RaE_IwGFQWQGBs15lK94fD5A4xQ:1vOawR:-R4_A3lgUjCt1ZrLPTOgpPIP7X2Ll2nz6fHcu_K27S4', '2025-12-11 12:17:43.538663'),('glbr94nh8ksseefqgsv2cvuvoji2asd2', '.eJxVjDsOwjAQBe_iGllx_Kek5wzWeneDA8iW4qRC3B0ipYD2zcx7iQTbWtLWeUkzibMYxel3y4APrjugO9Rbk9jqusxZ7oo8aJfXRvy8HO7fQYFevvWEPhAiADlUUUc7cbDG8hCDgYysnVKUKY7RaE_IwGFQWQGBs15lK94fD5A4xQ:1vPlHW:uxa2akV7_P7e3kMiT_TYSZd26pgzV1bqy8-iVNzpbew', '2025-12-14 17:32:18.178456'),('icpkgvxhecns366w2nihd2v34ovwrfhi', '.eJxVjDsOwjAQBe_iGllx_Kek5wzWeneDA8iW4qRC3B0ipYD2zcx7iQTbWtLWeUkzibMYxel3y4APrjugO9Rbk9jqusxZ7oo8aJfXRvy8HO7fQYFevvWEPhAiADlUUUc7cbDG8hCDgYysnVKUKY7RaE_IwGFQWQGBs15lK94fD5A4xQ:1vQk1T:yYhWsUCRirlEfxUYh8aCKMaeKo0pYzyFt6dqTZJFrvY', '2025-12-17 10:23:47.058065'),('0cjsjx4vhga30zq9y2ofsgu8fcq68t0r', '.eJxVjDsOwjAQBe_iGllx_Kek5wzWeneDA8iW4qRC3B0ipYD2zcx7iQTbWtLWeUkzibMYxel3y4APrjugO9Rbk9jqusxZ7oo8aJfXRvy8HO7fQYFevvWEPhAiADlUUUc7cbDG8hCDgYysnVKUKY7RaE_IwGFQWQGBs15lK94fD5A4xQ:1vRXuE:YSo_GIcNTn3kuXAnthN_fJJUjziFL01lgqL6Ufg4vE4', '2025-12-19 15:39:38.558560');
COMMIT;
BEGIN;
DELETE FROM "main"."domain_arts";
INSERT INTO "main"."domain_arts" ("id","name","slug","display_name","description","icon","color","is_active","is_experimental","created_at","updated_at","config","dashboard_url","display_order") VALUES (6, 'control_center', 'control-center', 'Control Center', 'System tools, monitoring, and development utilities', 'gear', 'info', 1, 0, '2025-11-09 10:36:38', '2025-11-18 11:32:27.351447', '{"subtitle": "System & Development", "statistics": {"enabled": true}, "features": ["Tools", "Monitoring", "Master Data"]}', '/control-center/', 1),(8, 'format_hub', 'format-hub', 'Format Hub', 'Medical Translation and PPTX Studio combined', 'file-earmark-slides', 'warning', 1, 0, '2025-11-18 11:32:27.362779', '2025-11-18 11:32:27.362779', '{"subtitle": "Translation & Enhancement", "statistics": {"enabled": true}, "features": ["Medical Translation", "PPTX Studio"]}', '/format-hub/', 2),(9, 'coaching_hub', 'coaching-hub', 'Coaching Hub', 'Coaching and training management', 'mortarboard', 'info', 0, 1, '2025-11-18 11:32:27.383645', '2025-11-18 11:32:27.383645', '{"subtitle": "Coaching & Training", "badge": "SOON", "statistics": {"enabled": false}, "features": ["Courses", "Progress"]}', '/coaching-hub/', 3),(10, 'writing_hub', 'writing-hub', 'Writing Hub', 'Modern novel series management with AI chapter generation', 'pen', 'primary', 1, 0, '2025-11-18 11:51:51', '2025-11-18 11:51:51', '{}', '/writing-hub/v2/', 2),(11, 'expert_hub', 'expert-hub', 'Expert Hub', 'Expert and consultant management', 'people', '#000000', 1, 0, '2025-11-18 11:51:51', '2025-12-01 15:00:17.427034', '{}', '/expert-hub/', 4),(12, 'support_hub', 'support-hub', 'Support Hub', 'Customer support and ticketing', 'headset', 'danger', 0, 1, '2025-11-18 11:51:51', '2025-11-18 11:51:51', '{}', '/support-hub/', 5),(13, 'research_hub', 'research-hub', 'Research Hub', 'Research and documentation management', 'search', '#000000', 1, 0, '2025-11-18 11:51:51', '2025-12-03 05:32:32.319476', '{}', '/research-hub/', 6),(14, 'analytics_hub', 'analytics-hub', 'Analytics Hub', 'Data analytics and reporting platform', 'bi bi-graph-up', '#17a2b8', 1, 1, '2025-11-18 16:17:37.248680', '2025-11-18 16:17:37.248680', '{}', '/analytics-hub/', 8),(15, 'cad_analysis', 'cad-analysis', 'CAD & Zeichnungsanalyse', 'Automatisierte Analyse und Bewertung technischer Zeichnungen', 'bi-rulers', 'teal', 1, 0, '2025-11-19 07:42:25.244963', '2025-11-19 07:42:25.244963', '{"features": ["dxf_parsing", "ocr", "dimension_detection", "standards_compliance"], "max_file_size_mb": 100, "supported_formats": ["dxf", "dwg", "pdf", "png", "jpg"]}', '/cad-analysis/', 50),(16, 'dsgvo_hub', 'dsgvo-hub', 'DSGVO-Hub', 'Multi Tenant Anwendung zur Verwaltung von DSB-Kunden', 'bi bi-star', '#3c8fd7', 1, 0, '2025-12-01 13:43:51.811969', '2025-12-01 13:43:51.811969', '{}', '/dsgvo-hub/', 10);
COMMIT;
BEGIN;
DELETE FROM "main"."domain_arts_copy1";
INSERT INTO "main"."domain_arts_copy1" ("id","name","slug","display_name","description","icon","color","is_active","is_experimental","created_at","updated_at","config","dashboard_url","display_order") VALUES (6, 'control_center', 'control-center', 'Control Center', 'System tools, monitoring, and development utilities', 'gear', 'info', 1, 0, '2025-11-09 10:36:38', '2025-11-18 11:32:27.351447', '{"subtitle": "System & Development", "statistics": {"enabled": true}, "features": ["Tools", "Monitoring", "Master Data"]}', '/control-center/', 1),(8, 'format_hub', 'format-hub', 'Format Hub', 'Medical Translation and PPTX Studio combined', 'file-earmark-slides', 'warning', 1, 0, '2025-11-18 11:32:27.362779', '2025-11-18 11:32:27.362779', '{"subtitle": "Translation & Enhancement", "statistics": {"enabled": true}, "features": ["Medical Translation", "PPTX Studio"]}', '/format-hub/', 2),(9, 'coaching_hub', 'coaching-hub', 'Coaching Hub', 'Coaching and training management', 'mortarboard', 'info', 0, 1, '2025-11-18 11:32:27.383645', '2025-11-18 11:32:27.383645', '{"subtitle": "Coaching & Training", "badge": "SOON", "statistics": {"enabled": false}, "features": ["Courses", "Progress"]}', '/coaching-hub/', 3),(10, 'writing_hub', 'writing-hub', 'Writing Hub', 'Modern novel series management with AI chapter generation', 'pen', 'primary', 1, 0, '2025-11-18 11:51:51', '2025-11-18 11:51:51', '{}', '/writing-hub/v2/', 2),(11, 'expert_hub', 'expert-hub', 'Expert Hub', 'Expert and consultant management', 'people', '#000000', 1, 0, '2025-11-18 11:51:51', '2025-12-01 15:00:17.427034', '{}', '/expert-hub/', 4),(12, 'support_hub', 'support-hub', 'Support Hub', 'Customer support and ticketing', 'headset', 'danger', 0, 1, '2025-11-18 11:51:51', '2025-11-18 11:51:51', '{}', '/support-hub/', 5),(13, 'research_hub', 'research-hub', 'Research Hub', 'Research and documentation management', 'search', '#000000', 1, 0, '2025-11-18 11:51:51', '2025-12-03 05:32:32.319476', '{}', '/research-hub/', 6),(14, 'analytics_hub', 'analytics-hub', 'Analytics Hub', 'Data analytics and reporting platform', 'bi bi-graph-up', '#17a2b8', 1, 1, '2025-11-18 16:17:37.248680', '2025-11-18 16:17:37.248680', '{}', '/analytics-hub/', 8),(15, 'cad_analysis', 'cad-analysis', 'CAD & Zeichnungsanalyse', 'Automatisierte Analyse und Bewertung technischer Zeichnungen', 'bi-rulers', 'teal', 1, 0, '2025-11-19 07:42:25.244963', '2025-11-19 07:42:25.244963', '{"features": ["dxf_parsing", "ocr", "dimension_detection", "standards_compliance"], "max_file_size_mb": 100, "supported_formats": ["dxf", "dwg", "pdf", "png", "jpg"]}', '/cad-analysis/', 50),(16, 'dsgvo_hub', 'dsgvo-hub', 'DSGVO-Hub', 'Multi Tenant Anwendung zur Verwaltung von DSB-Kunden', 'bi bi-star', '#3c8fd7', 1, 0, '2025-12-01 13:43:51.811969', '2025-12-01 13:43:51.811969', '{}', '/dsgvo-hub/', 10);
COMMIT;
BEGIN;
DELETE FROM "main"."domain_phases";
COMMIT;
BEGIN;
DELETE FROM "main"."domain_projects";
COMMIT;
BEGIN;
DELETE FROM "main"."domain_section_items";
COMMIT;
BEGIN;
DELETE FROM "main"."domain_sections";
INSERT INTO "main"."domain_sections" ("id","name","slug","display_name","description","icon","color","url","config","display_order","is_active","created_at","updated_at","domain_art_id") VALUES (1, 'Dashboard', 'dashboard', 'Dashboard', 'Dashboard section', 'bi-folder', '#3c8fd7', '', '{}', 1, 1, '2025-12-01 13:43:51.819567', '2025-12-01 13:43:51.819567', 16),(2, 'Management', 'management', 'Management', 'Management section', 'bi-folder', '#3c8fd7', '', '{}', 2, 1, '2025-12-01 13:43:51.827367', '2025-12-01 13:43:51.827367', 16);
COMMIT;
BEGIN;
DELETE FROM "main"."domain_types";
INSERT INTO "main"."domain_types" ("id","domain_art_id","name","slug","display_name","description","icon","color","config","is_active","sort_order","created_at","updated_at") VALUES (1, 10, 'fiction', 'fiction', 'Fiction', 'Fictional books and novels', '', NULL, '{}', 1, 10, '2025-11-06 08:06:42.683389', '2025-11-06 08:06:42.683389'),(2, 10, 'non_fiction', 'non-fiction', 'Non-Fiction', 'Non-fictional books and guides', '', NULL, '{}', 1, 20, '2025-11-06 08:06:42.692004', '2025-11-06 08:06:42.692004'),(3, 10, 'technical', 'technical', 'Technical', 'Technical documentation and manuals', '', NULL, '{}', 1, 30, '2025-11-06 08:06:42.699780', '2025-11-06 08:06:42.699780'),(4, 10, 'children', 'children', 'Children', 'Children and young adult books', '', NULL, '{}', 1, 40, '2025-11-06 08:06:42.707874', '2025-11-06 08:06:42.708394'),(5, 10, 'novel_series', 'novel-series', 'Novel Series', 'AI-powered novel series with Story Engine', 'book-half', NULL, '{}', 1, 1, '2025-11-09 09:54:34.875777', '2025-11-09 09:54:34.875777'),(6, 10, 'novel', 'novel', 'Novel', 'Full-length fictional narrative', 'book-fill', NULL, '{}', 1, 3, '2025-11-17 10:51:20.400852', '2025-11-17 10:51:20.400852'),(7, 10, 'short_story', 'short-story', 'Short Story Collection', 'Collection of short stories', 'collection', NULL, '{}', 1, 4, '2025-11-17 10:51:20.412760', '2025-11-17 10:51:20.412760'),(8, 10, 'science_fiction', 'sci-fi', 'Science Fiction', 'Science Fiction Books ', 'collection', NULL, '{}', 1, 1, '2025-11-18 06:53:04', '2025-11-18 06:53:04'),(9, 10, 'Buchprojekte ', 'book-projects', 'Buckprojekte', '', 'book-projekt', NULL, '{}', 1, 0, '2025-11-18 13:38:38.647754', '2025-11-18 13:38:38.647754'),(10, 10, 'worlds', 'worlds', 'Welten', 'Beschreibung von Welten in den Projekten ', '', NULL, '{}', 1, 0, '2025-11-18 13:39:50.840901', '2025-11-18 13:39:50.840901'),(11, 10, 'characters', 'characters', 'Charaktere', 'Beschreibung der verschiedenen Charaktere für Buchprojekte ', '', NULL, '{}', 1, 0, '2025-11-18 13:40:37.039131', '2025-11-18 13:40:37.039131'),(12, 10, 'ideation', 'ideation', 'Ideen', 'Skizzierung von Ideen für Buchprojekte ', '', NULL, '{}', 1, 0, '2025-11-18 13:41:18.390773', '2025-11-18 13:41:18.390773');
COMMIT;
BEGIN;
DELETE FROM "main"."dsb_branche";
INSERT INTO "main"."dsb_branche" ("id","code","name","description","is_active","sort_order","created_at","updated_at","risk_factor","special_requirements") VALUES (1, 'it', 'IT / Software', '', 1, 1, '2025-12-01 16:00:16.965889', '2025-12-01 16:00:16.965889', 1.5, '[]'),(2, 'gesundheit', 'Gesundheitswesen', '', 1, 2, '2025-12-01 16:00:16.973494', '2025-12-01 16:00:16.973494', 3, '[]'),(3, 'finanz', 'Finanzdienstleistungen', '', 1, 3, '2025-12-01 16:00:16.980276', '2025-12-01 16:00:16.980276', 2.5, '[]'),(4, 'handel', 'Handel', '', 1, 4, '2025-12-01 16:00:16.985817', '2025-12-01 16:00:16.985817', 1.2, '[]'),(5, 'bildung', 'Bildung', '', 1, 5, '2025-12-01 16:00:16.993288', '2025-12-01 16:00:16.993288', 1.8, '[]'),(6, 'oeffentlich', 'Öffentliche Verwaltung', '', 1, 6, '2025-12-01 16:00:17.000872', '2025-12-01 16:00:17.000872', 2, '[]'),(7, 'sonstige', 'Sonstige', '', 1, 7, '2025-12-01 16:00:17.007488', '2025-12-01 16:00:17.007488', 1, '[]');
COMMIT;
BEGIN;
DELETE FROM "main"."dsb_datenkategorie";
INSERT INTO "main"."dsb_datenkategorie" ("id","code","name","description","is_active","sort_order","created_at","updated_at","examples","sensitivity_id") VALUES (1, 'stammdaten', 'Stammdaten (Name, Adresse)', '', 1, 1, '2025-12-01 16:00:17.042751', '2025-12-01 16:00:17.042751', '[]', NULL),(2, 'kontaktdaten', 'Kontaktdaten (E-Mail, Telefon)', '', 1, 2, '2025-12-01 16:00:17.050842', '2025-12-01 16:00:17.050842', '[]', NULL),(3, 'vertragsdaten', 'Vertragsdaten', '', 1, 3, '2025-12-01 16:00:17.057711', '2025-12-01 16:00:17.057711', '[]', NULL),(4, 'zahlungsdaten', 'Zahlungsdaten', '', 1, 4, '2025-12-01 16:00:17.066121', '2025-12-01 16:00:17.066121', '[]', NULL),(5, 'nutzungsdaten', 'Nutzungsdaten / Log-Daten', '', 1, 5, '2025-12-01 16:00:17.073412', '2025-12-01 16:00:17.073412', '[]', NULL),(6, 'technische_daten', 'Technische Daten (IP, Browser)', '', 1, 6, '2025-12-01 16:00:17.081284', '2025-12-01 16:00:17.081284', '[]', NULL);
COMMIT;
BEGIN;
DELETE FROM "main"."dsb_dokument";
COMMIT;
BEGIN;
DELETE FROM "main"."dsb_mandant";
INSERT INTO "main"."dsb_mandant" ("id","client_id","created_at","updated_at","is_active","deleted_at","name","external_id","client_type","primary_contact_name","primary_contact_email","primary_contact_phone","address","contract_start","contract_end","metadata","handelsregisternummer","ust_id","anzahl_mitarbeiter","dsb_intern","dsb_name","dsb_email","_cached_verarbeitungen_count","_cached_compliance_score","betreuer_id","branche_id","client_content_type_id","created_by_id","deleted_by_id","risk_level_id","rechtsform_id") VALUES (1, NULL, '2025-12-01 16:14:48.775167', '2025-12-01 16:14:48.775167', 1, NULL, 'Oechsle GmbH', '', '', 'Max Mustermann', 'kontakt@oechsle.de', '+49 711 123456', 'Musterstraße 170000 StuttgartDeutschland', '2025-12-01', NULL, '{}', '', '', NULL, 0, '', '', 0, NULL, NULL, 7, NULL, NULL, NULL, NULL, 1),(2, NULL, '2025-12-01 16:14:48.785080', '2025-12-01 16:14:48.785080', 1, NULL, 'LS Bau AG', '', '', 'Hans Bauer', 'info@lsbau.de', '+49 89 987654', 'Baustraße 1080000 MünchenDeutschland', '2025-12-01', NULL, '{}', '', '', NULL, 0, '', '', 0, NULL, NULL, 7, NULL, NULL, NULL, NULL, 2),(3, NULL, '2025-12-01 16:14:48.792159', '2025-12-01 16:14:48.792159', 1, NULL, 'Feha GmbH', '', '', 'Anna Schmidt', 'kontakt@feha.de', '+49 69 456789', 'Technikweg 560000 FrankfurtDeutschland', '2025-12-01', NULL, '{}', '', '', NULL, 0, '', '', 0, NULL, NULL, 1, NULL, NULL, NULL, NULL, 1),(4, NULL, '2025-12-01 16:14:48.801243', '2025-12-01 16:14:48.801760', 1, NULL, 'IIL GmbH', '', '', 'Thomas Müller', 'info@iil.de', '+49 221 789012', 'Innovationsplatz 350000 KölnDeutschland', '2025-12-01', NULL, '{}', '', '', NULL, 0, '', '', 0, NULL, NULL, 1, NULL, NULL, NULL, NULL, 1),(5, NULL, '2025-12-01 16:14:48.808980', '2025-12-01 16:14:48.808980', 1, NULL, 'Scheppach GmbH', '', '', 'Stefan Weber', 'kontakt@scheppach.de', '+49 911 345678', 'Industriestraße 2090000 NürnbergDeutschland', '2025-12-01', NULL, '{}', '', '', NULL, 0, '', '', 0, NULL, NULL, 7, NULL, NULL, NULL, NULL, 1),(6, NULL, '2025-12-01 16:14:48.817422', '2025-12-01 16:14:48.817422', 1, NULL, 'Scheppach France', '', '', 'Jean Dupont', 'contact@scheppach.fr', '+33 1 23456789', 'Rue de la Innovation 1575001 ParisFrance', '2025-12-01', NULL, '{}', '', '', NULL, 0, '', '', 0, NULL, NULL, 7, NULL, NULL, NULL, NULL, 1),(7, NULL, '2025-12-01 16:14:48.827539', '2025-12-01 16:14:48.827539', 1, NULL, 'Scheppach Wooster', '', '', 'John Smith', 'contact@scheppach-wooster.com', '+1 330 1234567', '123 Main StreetWooster, OH 44691USA', '2025-12-01', NULL, '{}', '', '', NULL, 0, '', '', 0, NULL, NULL, 7, NULL, NULL, NULL, NULL, 1),(8, NULL, '2025-12-01 16:14:48.834818', '2025-12-01 16:14:48.834818', 1, NULL, 'Fendt Holzgestaltung GmbH', '', '', 'Michael Fendt', 'info@fendt-holz.de', '+49 821 567890', 'Holzweg 886000 AugsburgDeutschland', '2025-12-01', NULL, '{}', '', '', NULL, 0, '', '', 0, NULL, NULL, 7, NULL, NULL, NULL, NULL, 1);
COMMIT;
BEGIN;
DELETE FROM "main"."dsb_mandant_tom";
INSERT INTO "main"."dsb_mandant_tom" ("id","implementiert","bemerkung","created_at","updated_at","mandant_id","massnahme_id") VALUES (1, 1, '', '2025-12-01 16:45:03.111367', '2025-12-01 16:45:03.111367', 5, 1),(2, 1, '', '2025-12-01 16:45:03.114397', '2025-12-01 16:45:03.114397', 5, 2),(3, 1, '', '2025-12-01 16:45:03.116429', '2025-12-01 16:45:03.116429', 5, 3),(4, 1, '', '2025-12-01 16:45:03.118453', '2025-12-01 16:45:03.118453', 5, 4),(5, 1, '', '2025-12-01 16:45:03.119969', '2025-12-01 16:45:03.119969', 5, 5),(6, 1, '', '2025-12-01 16:45:03.121013', '2025-12-01 16:45:03.121013', 5, 6),(7, 0, '', '2025-12-01 16:45:03.122530', '2025-12-01 16:45:03.122530', 5, 7),(8, 1, '', '2025-12-01 16:45:03.124046', '2025-12-01 16:45:03.124046', 5, 8),(9, 1, '', '2025-12-01 16:45:03.127053', '2025-12-01 16:45:03.127053', 5, 9),(10, 0, '', '2025-12-01 16:45:03.128569', '2025-12-01 16:45:03.128569', 5, 10),(11, 1, '', '2025-12-01 16:45:03.130598', '2025-12-01 16:45:03.130598', 5, 11),(12, 1, '', '2025-12-01 16:45:03.131127', '2025-12-01 16:45:03.131127', 5, 12),(13, 1, '', '2025-12-01 16:45:03.134160', '2025-12-01 16:45:03.134160', 5, 13),(14, 1, '', '2025-12-01 16:45:03.135674', '2025-12-01 16:45:03.135674', 5, 14),(15, 1, '', '2025-12-01 16:45:03.137696', '2025-12-01 16:45:03.137696', 5, 15),(16, 1, '', '2025-12-01 16:45:03.139718', '2025-12-01 16:45:03.139718', 5, 16),(17, 1, '', '2025-12-01 16:45:03.141228', '2025-12-01 16:45:03.141228', 5, 17),(18, 0, '', '2025-12-01 16:45:03.142233', '2025-12-01 16:45:03.142233', 5, 18),(19, 0, '', '2025-12-01 16:45:03.143954', '2025-12-01 16:45:03.143954', 5, 19),(20, 1, '', '2025-12-01 16:45:03.146976', '2025-12-01 16:45:03.146976', 5, 20),(21, 1, '', '2025-12-01 16:45:03.148491', '2025-12-01 16:45:03.148491', 5, 21),(22, 1, '', '2025-12-01 16:45:03.150002', '2025-12-01 16:45:03.150002', 5, 22),(23, 1, '', '2025-12-01 16:45:03.151514', '2025-12-01 16:45:03.151514', 5, 23),(24, 0, '', '2025-12-01 16:45:03.153031', '2025-12-01 16:45:03.153031', 5, 25),(25, 1, '', '2025-12-01 16:45:03.154588', '2025-12-01 16:45:03.154588', 5, 26),(26, 1, '', '2025-12-01 16:45:03.156630', '2025-12-01 16:45:03.156630', 5, 27),(27, 1, '', '2025-12-01 16:45:03.157142', '2025-12-01 16:45:03.157142', 5, 28),(28, 1, '', '2025-12-01 16:45:03.158654', '2025-12-01 16:45:03.158654', 5, 29),(29, 1, '', '2025-12-01 16:45:03.161175', '2025-12-01 16:45:03.161175', 5, 30),(30, 0, '', '2025-12-01 16:45:03.161680', '2025-12-01 16:45:03.161680', 5, 31),(31, 1, '', '2025-12-01 16:45:03.163194', '2025-12-01 16:45:03.163194', 5, 32),(32, 0, '', '2025-12-01 16:45:03.166841', '2025-12-01 16:45:03.166841', 5, 33),(33, 1, '', '2025-12-01 16:45:03.167353', '2025-12-01 16:45:03.167353', 5, 34),(34, 1, '', '2025-12-01 16:45:03.168864', '2025-12-01 16:45:03.168864', 5, 35),(35, 0, '', '2025-12-01 16:45:03.171596', '2025-12-01 16:45:03.171596', 5, 36),(36, 1, '', '2025-12-01 16:45:03.173132', '2025-12-01 16:45:03.173132', 5, 37),(37, 1, '', '2025-12-01 16:45:03.174660', '2025-12-01 16:45:03.174660', 5, 38),(38, 1, '', '2025-12-01 16:45:03.176767', '2025-12-01 16:45:03.176767', 5, 39),(39, 1, '', '2025-12-01 16:45:03.178800', '2025-12-01 16:45:03.178800', 5, 40),(40, 1, '', '2025-12-01 16:45:03.180313', '2025-12-01 16:45:03.180313', 5, 41),(41, 1, '', '2025-12-01 16:45:03.181826', '2025-12-01 16:45:03.181826', 5, 42),(42, 1, '', '2025-12-01 16:45:03.183378', '2025-12-01 16:45:03.183378', 5, 43),(43, 1, '', '2025-12-01 16:45:03.184410', '2025-12-01 16:45:03.184410', 5, 44),(44, 1, '', '2025-12-01 16:45:03.187117', '2025-12-01 16:45:03.187117', 5, 45),(45, 1, '', '2025-12-01 16:45:03.188630', '2025-12-01 16:45:03.188630', 5, 46),(46, 1, '', '2025-12-01 16:45:03.190141', '2025-12-01 16:45:03.190141', 5, 47),(47, 1, '', '2025-12-01 16:45:03.191657', '2025-12-01 16:45:03.191657', 5, 48),(48, 1, '', '2025-12-01 16:45:03.193706', '2025-12-01 16:45:03.193706', 5, 49),(49, 1, '', '2025-12-01 16:45:03.195216', '2025-12-01 16:45:03.196223', 5, 50),(50, 1, '', '2025-12-01 16:45:03.197732', '2025-12-01 16:45:03.197732', 5, 51),(51, 1, '', '2025-12-01 16:45:03.198741', '2025-12-01 16:45:03.198741', 5, 52),(52, 1, '', '2025-12-01 16:45:03.199761', '2025-12-01 16:45:03.199761', 5, 53),(53, 0, '', '2025-12-01 16:45:03.202086', '2025-12-01 16:45:03.202086', 5, 54),(54, 0, '', '2025-12-01 16:45:03.204129', '2025-12-01 16:45:03.204129', 5, 55),(55, 1, '', '2025-12-01 16:45:03.205645', '2025-12-01 16:45:03.205645', 5, 56),(56, 1, '', '2025-12-01 16:45:03.208283', '2025-12-01 16:45:03.208283', 5, 57),(57, 1, '', '2025-12-01 16:45:03.209795', '2025-12-01 16:45:03.209795', 5, 58),(58, 1, '', '2025-12-01 16:45:03.211306', '2025-12-01 16:45:03.211306', 5, 59),(59, 1, '', '2025-12-01 16:45:03.212820', '2025-12-01 16:45:03.212820', 5, 60),(60, 1, '', '2025-12-01 16:45:03.214351', '2025-12-01 16:45:03.214351', 5, 61),(61, 1, '', '2025-12-01 16:45:03.216387', '2025-12-01 16:45:03.216387', 5, 62),(62, 1, '', '2025-12-01 16:45:03.218148', '2025-12-01 16:45:03.218148', 5, 63),(63, 1, '', '2025-12-01 16:45:03.219668', '2025-12-01 16:45:03.219668', 5, 64),(64, 1, '', '2025-12-01 16:45:03.220676', '2025-12-01 16:45:03.220676', 5, 65),(65, 1, '', '2025-12-01 16:45:03.223233', '2025-12-01 16:45:03.223737', 5, 66),(66, 1, '', '2025-12-01 16:45:03.225254', '2025-12-01 16:45:03.225254', 5, 67),(67, 1, '', '2025-12-01 16:45:03.226772', '2025-12-01 16:45:03.226772', 5, 68),(68, 1, '', '2025-12-01 16:45:03.228292', '2025-12-01 16:45:03.228292', 5, 69),(69, 0, '', '2025-12-01 16:45:03.229812', '2025-12-01 16:45:03.229812', 5, 70),(70, 1, '', '2025-12-01 16:45:03.231326', '2025-12-01 16:45:03.231326', 5, 71),(71, 1, '', '2025-12-01 16:45:03.234727', '2025-12-01 16:45:03.234727', 5, 72),(72, 1, '', '2025-12-01 16:45:03.236296', '2025-12-01 16:45:03.236296', 5, 73),(73, 1, '', '2025-12-01 16:45:03.237811', '2025-12-01 16:45:03.237811', 5, 74),(74, 1, '', '2025-12-01 16:45:03.239326', '2025-12-01 16:45:03.239326', 5, 75),(75, 1, '', '2025-12-01 16:45:03.240844', '2025-12-01 16:45:03.240844', 5, 76),(76, 1, '', '2025-12-01 16:45:03.242360', '2025-12-01 16:45:03.242360', 5, 77),(77, 1, '', '2025-12-01 16:45:03.243879', '2025-12-01 16:45:03.243879', 5, 78),(78, 1, '', '2025-12-01 16:45:03.246941', '2025-12-01 16:45:03.247456', 5, 79),(79, 1, '', '2025-12-01 16:45:03.249232', '2025-12-01 16:45:03.249232', 5, 80),(80, 1, '', '2025-12-01 16:45:03.250801', '2025-12-01 16:45:03.250801', 5, 81),(81, 1, '', '2025-12-01 16:45:03.251318', '2025-12-01 16:45:03.252833', 5, 82),(82, 1, '', '2025-12-01 16:45:03.254354', '2025-12-01 16:45:03.254354', 5, 83),(83, 1, '', '2025-12-01 16:45:03.256530', '2025-12-01 16:45:03.256530', 5, 84),(84, 1, '', '2025-12-01 16:45:03.258104', '2025-12-01 16:45:03.258104', 5, 85),(85, 1, '', '2025-12-01 16:45:03.259626', '2025-12-01 16:45:03.259626', 5, 86),(86, 1, '', '2025-12-01 16:45:03.261140', '2025-12-01 16:45:03.261140', 5, 87),(87, 1, '', '2025-12-01 16:45:03.264175', '2025-12-01 16:45:03.264175', 5, 88),(88, 1, '', '2025-12-01 16:45:03.266984', '2025-12-01 16:45:03.266984', 5, 89),(89, 1, '', '2025-12-01 16:45:03.268502', '2025-12-01 16:45:03.268502', 5, 90),(90, 1, '', '2025-12-01 16:45:03.269508', '2025-12-01 16:45:03.269508', 5, 91),(91, 1, '', '2025-12-01 16:45:03.271162', '2025-12-01 16:45:03.271162', 5, 92),(92, 0, '', '2025-12-01 16:45:03.272682', '2025-12-01 16:45:03.272682', 5, 93),(93, 1, '', '2025-12-01 16:45:03.275205', '2025-12-01 16:45:03.275205', 5, 94),(94, 1, '', '2025-12-01 16:45:03.277221', '2025-12-01 16:45:03.277221', 5, 95),(95, 1, '', '2025-12-01 16:45:03.278227', '2025-12-01 16:45:03.278227', 5, 96),(96, 0, '', '2025-12-01 16:45:03.281002', '2025-12-01 16:45:03.281002', 5, 97),(97, 1, '', '2025-12-01 16:45:03.282513', '2025-12-01 16:45:03.282513', 5, 98),(98, 1, '', '2025-12-01 16:45:03.284031', '2025-12-01 16:45:03.284031', 5, 99),(99, 1, '', '2025-12-01 16:45:03.286569', '2025-12-01 16:45:03.286569', 5, 100),(100, 1, '', '2025-12-01 16:45:03.287074', '2025-12-01 16:45:03.287074', 5, 101),(101, 0, '', '2025-12-01 16:45:03.290102', '2025-12-01 16:45:03.290102', 5, 102),(102, 1, '', '2025-12-01 16:45:03.291612', '2025-12-01 16:45:03.291612', 5, 103),(103, 0, '', '2025-12-01 16:45:03.293125', '2025-12-01 16:45:03.293125', 5, 104),(104, 0, '', '2025-12-01 16:45:03.294670', '2025-12-01 16:45:03.294670', 5, 105),(105, 0, '', '2025-12-01 16:45:03.296709', '2025-12-01 16:45:03.296709', 5, 106),(106, 1, '', '2025-12-01 16:45:03.298748', '2025-12-01 16:45:03.298748', 5, 107),(107, 0, '', '2025-12-01 16:45:03.300764', '2025-12-01 16:45:03.300764', 5, 108),(108, 1, '', '2025-12-01 16:45:03.301842', '2025-12-01 16:45:03.301842', 5, 109),(109, 1, '', '2025-12-01 16:45:03.303361', '2025-12-01 16:45:03.303361', 5, 110),(110, 0, '', '2025-12-01 16:45:03.305941', '2025-12-01 16:45:03.305941', 5, 111),(111, 1, '', '2025-12-01 16:45:03.307011', '2025-12-01 16:45:03.307011', 5, 112),(112, 0, '', '2025-12-01 16:45:03.308526', '2025-12-01 16:45:03.308526', 5, 113),(113, 1, '', '2025-12-01 16:45:03.310041', '2025-12-01 16:45:03.310041', 5, 114),(114, 1, '', '2025-12-01 16:45:03.312829', '2025-12-01 16:45:03.312829', 5, 115),(115, 0, '', '2025-12-01 16:45:03.314340', '2025-12-01 16:45:03.314340', 5, 116),(116, 1, '', '2025-12-01 16:45:03.316909', '2025-12-01 16:45:03.316909', 5, 117),(117, 1, '', '2025-12-01 16:45:03.318425', '2025-12-01 16:45:03.318425', 5, 118),(118, 1, '', '2025-12-01 16:45:03.319939', '2025-12-01 16:45:03.319939', 5, 119),(119, 1, '', '2025-12-01 16:45:03.321451', '2025-12-01 16:45:03.321451', 5, 120),(120, 1, '', '2025-12-01 16:45:03.322963', '2025-12-01 16:45:03.322963', 8, 1),(121, 1, '', '2025-12-01 16:45:03.324482', '2025-12-01 16:45:03.324482', 8, 2),(122, 0, '', '2025-12-01 16:45:03.327288', '2025-12-01 16:45:03.327288', 8, 3),(123, 0, '', '2025-12-01 16:45:03.328324', '2025-12-01 16:45:03.328324', 8, 4),(124, 0, '', '2025-12-01 16:45:03.329836', '2025-12-01 16:45:03.329836', 8, 5),(125, 0, '', '2025-12-01 16:45:03.331347', '2025-12-01 16:45:03.331347', 8, 6),(126, 0, '', '2025-12-01 16:45:03.332867', '2025-12-01 16:45:03.332867', 8, 7),(127, 0, '', '2025-12-01 16:45:03.335896', '2025-12-01 16:45:03.335896', 8, 8),(128, 0, '', '2025-12-01 16:45:03.336927', '2025-12-01 16:45:03.336927', 8, 9),(129, 0, '', '2025-12-01 16:45:03.338472', '2025-12-01 16:45:03.338472', 8, 10),(130, 0, '', '2025-12-01 16:45:03.339989', '2025-12-01 16:45:03.339989', 8, 11),(131, 0, '', '2025-12-01 16:45:03.341501', '2025-12-01 16:45:03.341501', 8, 12),(132, 0, '', '2025-12-01 16:45:03.344529', '2025-12-01 16:45:03.344529', 8, 13),(133, 0, '', '2025-12-01 16:45:03.347074', '2025-12-01 16:45:03.347074', 8, 14),(134, 0, '', '2025-12-01 16:45:03.349146', '2025-12-01 16:45:03.349146', 8, 15),(135, 0, '', '2025-12-01 16:45:03.349657', '2025-12-01 16:45:03.349657', 8, 16),(136, 0, '', '2025-12-01 16:45:03.351169', '2025-12-01 16:45:03.351169', 8, 17),(137, 0, '', '2025-12-01 16:45:03.352688', '2025-12-01 16:45:03.352688', 8, 18),(138, 0, '', '2025-12-01 16:45:03.355827', '2025-12-01 16:45:03.355827', 8, 19),(139, 0, '', '2025-12-01 16:45:03.357849', '2025-12-01 16:45:03.357849', 8, 20),(140, 0, '', '2025-12-01 16:45:03.359367', '2025-12-01 16:45:03.359367', 8, 21),(141, 0, '', '2025-12-01 16:45:03.360628', '2025-12-01 16:45:03.360628', 8, 22),(142, 0, '', '2025-12-01 16:45:03.362140', '2025-12-01 16:45:03.362140', 8, 23),(143, 0, '', '2025-12-01 16:45:03.363674', '2025-12-01 16:45:03.363674', 8, 24),(144, 0, '', '2025-12-01 16:45:03.366713', '2025-12-01 16:45:03.366713', 8, 25),(145, 0, '', '2025-12-01 16:45:03.367745', '2025-12-01 16:45:03.367745', 8, 26),(146, 0, '', '2025-12-01 16:45:03.369290', '2025-12-01 16:45:03.369290', 8, 27),(147, 0, '', '2025-12-01 16:45:03.370802', '2025-12-01 16:45:03.370802', 8, 28),(148, 0, '', '2025-12-01 16:45:03.372321', '2025-12-01 16:45:03.372321', 8, 29),(149, 0, '', '2025-12-01 16:45:03.375358', '2025-12-01 16:45:03.375358', 8, 30),(150, 0, '', '2025-12-01 16:45:03.376869', '2025-12-01 16:45:03.376869', 8, 31),(151, 0, '', '2025-12-01 16:45:03.378380', '2025-12-01 16:45:03.378380', 8, 32),(152, 0, '', '2025-12-01 16:45:03.379892', '2025-12-01 16:45:03.379892', 8, 33),(153, 0, '', '2025-12-01 16:45:03.381403', '2025-12-01 16:45:03.381403', 8, 34),(154, 0, '', '2025-12-01 16:45:03.383923', '2025-12-01 16:45:03.383923', 8, 35),(155, 0, '', '2025-12-01 16:45:03.385945', '2025-12-01 16:45:03.385945', 8, 36),(156, 0, '', '2025-12-01 16:45:03.386970', '2025-12-01 16:45:03.386970', 8, 37),(157, 0, '', '2025-12-01 16:45:03.388480', '2025-12-01 16:45:03.388480', 8, 38),(158, 0, '', '2025-12-01 16:45:03.389999', '2025-12-01 16:45:03.389999', 8, 39),(159, 0, '', '2025-12-01 16:45:03.392273', '2025-12-01 16:45:03.392273', 8, 40),(160, 0, '', '2025-12-01 16:45:03.392789', '2025-12-01 16:45:03.392789', 8, 41),(161, 0, '', '2025-12-01 16:45:03.396331', '2025-12-01 16:45:03.396331', 8, 42),(162, 0, '', '2025-12-01 16:45:03.396843', '2025-12-01 16:45:03.396843', 8, 43),(163, 0, '', '2025-12-01 16:45:03.399398', '2025-12-01 16:45:03.399398', 8, 44),(164, 0, '', '2025-12-01 16:45:03.401433', '2025-12-01 16:45:03.401433', 8, 45),(165, 0, '', '2025-12-01 16:45:03.401952', '2025-12-01 16:45:03.401952', 8, 46),(166, 0, '', '2025-12-01 16:45:03.404988', '2025-12-01 16:45:03.404988', 8, 47),(167, 0, '', '2025-12-01 16:45:03.407058', '2025-12-01 16:45:03.407058', 8, 48),(168, 0, '', '2025-12-01 16:45:03.408320', '2025-12-01 16:45:03.408320', 8, 49),(169, 0, '', '2025-12-01 16:45:03.409327', '2025-12-01 16:45:03.409327', 8, 50),(170, 0, '', '2025-12-01 16:45:03.411206', '2025-12-01 16:45:03.411206', 8, 51),(171, 0, '', '2025-12-01 16:45:03.412721', '2025-12-01 16:45:03.412721', 8, 52),(172, 0, '', '2025-12-01 16:45:03.415756', '2025-12-01 16:45:03.415756', 8, 53),(173, 0, '', '2025-12-01 16:45:03.417268', '2025-12-01 16:45:03.417268', 8, 54),(174, 0, '', '2025-12-01 16:45:03.419793', '2025-12-01 16:45:03.419793', 8, 55),(175, 0, '', '2025-12-01 16:45:03.421303', '2025-12-01 16:45:03.421303', 8, 56),(176, 0, '', '2025-12-01 16:45:03.422815', '2025-12-01 16:45:03.422815', 8, 57),(177, 0, '', '2025-12-01 16:45:03.424868', '2025-12-01 16:45:03.424868', 8, 58),(178, 0, '', '2025-12-01 16:45:03.426408', '2025-12-01 16:45:03.426408', 8, 59),(179, 0, '', '2025-12-01 16:45:03.428342', '2025-12-01 16:45:03.428342', 8, 60),(180, 0, '', '2025-12-01 16:45:03.429866', '2025-12-01 16:45:03.429866', 8, 61),(181, 0, '', '2025-12-01 16:45:03.431396', '2025-12-01 16:45:03.431396', 8, 62),(182, 0, '', '2025-12-01 16:45:03.433429', '2025-12-01 16:45:03.433429', 8, 63),(183, 0, '', '2025-12-01 16:45:03.435451', '2025-12-01 16:45:03.435451', 8, 64),(184, 0, '', '2025-12-01 16:45:03.436531', '2025-12-01 16:45:03.436531', 8, 65),(185, 0, '', '2025-12-01 16:45:03.438045', '2025-12-01 16:45:03.438045', 8, 66),(186, 0, '', '2025-12-01 16:45:03.439786', '2025-12-01 16:45:03.439786', 8, 67),(187, 0, '', '2025-12-01 16:45:03.440825', '2025-12-01 16:45:03.440825', 8, 68),(188, 0, '', '2025-12-01 16:45:03.442338', '2025-12-01 16:45:03.442338', 8, 69),(189, 0, '', '2025-12-01 16:45:03.443854', '2025-12-01 16:45:03.445366', 8, 70),(190, 0, '', '2025-12-01 16:45:03.446373', '2025-12-01 16:45:03.446373', 8, 71),(191, 0, '', '2025-12-01 16:45:03.448001', '2025-12-01 16:45:03.448001', 8, 72),(192, 0, '', '2025-12-01 16:45:03.449513', '2025-12-01 16:45:03.449513', 8, 73),(193, 0, '', '2025-12-01 16:45:03.450518', '2025-12-01 16:45:03.450518', 8, 74),(194, 0, '', '2025-12-01 16:45:03.453384', '2025-12-01 16:45:03.453384', 8, 75),(195, 0, '', '2025-12-01 16:45:03.455620', '2025-12-01 16:45:03.455620', 8, 76),(196, 0, '', '2025-12-01 16:45:03.457153', '2025-12-01 16:45:03.457153', 8, 77),(197, 0, '', '2025-12-01 16:45:03.458665', '2025-12-01 16:45:03.458665', 8, 78),(198, 0, '', '2025-12-01 16:45:03.460693', '2025-12-01 16:45:03.460693', 8, 79),(199, 0, '', '2025-12-01 16:45:03.462235', '2025-12-01 16:45:03.462235', 8, 80),(200, 0, '', '2025-12-01 16:45:03.463785', '2025-12-01 16:45:03.463785', 8, 81),(201, 0, '', '2025-12-01 16:45:03.465303', '2025-12-01 16:45:03.466309', 8, 82),(202, 0, '', '2025-12-01 16:45:03.466813', '2025-12-01 16:45:03.466813', 8, 83),(203, 0, '', '2025-12-01 16:45:03.468326', '2025-12-01 16:45:03.468326', 8, 84),(204, 0, '', '2025-12-01 16:45:03.471351', '2025-12-01 16:45:03.471351', 8, 85),(205, 0, '', '2025-12-01 16:45:03.472867', '2025-12-01 16:45:03.472867', 8, 86),(206, 0, '', '2025-12-01 16:45:03.475387', '2025-12-01 16:45:03.475387', 8, 87),(207, 0, '', '2025-12-01 16:45:03.476917', '2025-12-01 16:45:03.476917', 8, 88),(208, 0, '', '2025-12-01 16:45:03.478434', '2025-12-01 16:45:03.478434', 8, 89),(209, 0, '', '2025-12-01 16:45:03.479955', '2025-12-01 16:45:03.479955', 8, 90),(210, 0, '', '2025-12-01 16:45:03.481466', '2025-12-01 16:45:03.481466', 8, 91),(211, 0, '', '2025-12-01 16:45:03.482979', '2025-12-01 16:45:03.482979', 8, 92),(212, 0, '', '2025-12-01 16:45:03.486006', '2025-12-01 16:45:03.486006', 8, 93),(213, 0, '', '2025-12-01 16:45:03.487226', '2025-12-01 16:45:03.487226', 8, 94),(214, 0, '', '2025-12-01 16:45:03.488739', '2025-12-01 16:45:03.488739', 8, 95),(215, 0, '', '2025-12-01 16:45:03.489765', '2025-12-01 16:45:03.489765', 8, 96),(216, 0, '', '2025-12-01 16:45:03.491276', '2025-12-01 16:45:03.491276', 8, 97),(217, 0, '', '2025-12-01 16:45:03.492813', '2025-12-01 16:45:03.492813', 8, 98),(218, 0, '', '2025-12-01 16:45:03.496362', '2025-12-01 16:45:03.496362', 8, 99),(219, 0, '', '2025-12-01 16:45:03.496877', '2025-12-01 16:45:03.496877', 8, 100),(220, 0, '', '2025-12-01 16:45:03.498393', '2025-12-01 16:45:03.498393', 8, 101),(221, 0, '', '2025-12-01 16:45:03.499906', '2025-12-01 16:45:03.499906', 8, 102),(222, 0, '', '2025-12-01 16:45:03.501420', '2025-12-01 16:45:03.501420', 8, 103),(223, 0, '', '2025-12-01 16:45:03.504133', '2025-12-01 16:45:03.504133', 8, 104),(224, 0, '', '2025-12-01 16:45:03.505644', '2025-12-01 16:45:03.505644', 8, 105),(225, 0, '', '2025-12-01 16:45:03.507154', '2025-12-01 16:45:03.507154', 8, 106),(226, 0, '', '2025-12-01 16:45:03.508667', '2025-12-01 16:45:03.508667', 8, 107),(227, 0, '', '2025-12-01 16:45:03.510180', '2025-12-01 16:45:03.510180', 8, 108),(228, 0, '', '2025-12-01 16:45:03.511695', '2025-12-01 16:45:03.511695', 8, 109),(229, 0, '', '2025-12-01 16:45:03.513230', '2025-12-01 16:45:03.513230', 8, 110),(230, 0, '', '2025-12-01 16:45:03.516363', '2025-12-01 16:45:03.516363', 8, 111),(231, 0, '', '2025-12-01 16:45:03.517877', '2025-12-01 16:45:03.517877', 8, 112),(232, 0, '', '2025-12-01 16:45:03.519535', '2025-12-01 16:45:03.519535', 8, 113),(233, 0, '', '2025-12-01 16:45:03.521051', '2025-12-01 16:45:03.521051', 8, 114),(234, 0, '', '2025-12-01 16:45:03.522056', '2025-12-01 16:45:03.522056', 8, 115),(235, 0, '', '2025-12-01 16:45:03.524732', '2025-12-01 16:45:03.524732', 8, 116),(236, 0, '', '2025-12-01 16:45:03.526305', '2025-12-01 16:45:03.526305', 8, 117),(237, 0, '', '2025-12-01 16:45:03.528336', '2025-12-01 16:45:03.528336', 8, 118),(238, 0, '', '2025-12-01 16:45:03.528848', '2025-12-01 16:45:03.528848', 8, 119),(239, 0, '', '2025-12-01 16:45:03.530362', '2025-12-01 16:45:03.530362', 8, 120),(240, 1, '', '2025-12-01 16:45:03.532926', '2025-12-01 16:45:03.532926', 2, 1),(241, 0, '', '2025-12-01 16:45:03.536177', '2025-12-01 16:45:03.536177', 2, 2),(242, 1, '', '2025-12-01 16:45:03.537202', '2025-12-01 16:45:03.537202', 2, 3),(243, 1, '', '2025-12-01 16:45:03.538717', '2025-12-01 16:45:03.538717', 2, 4),(244, 1, '', '2025-12-01 16:45:03.540232', '2025-12-01 16:45:03.540232', 2, 5),(245, 1, '', '2025-12-01 16:45:03.541751', '2025-12-01 16:45:03.541751', 2, 6),(246, 0, '', '2025-12-01 16:45:03.543265', '2025-12-01 16:45:03.543265', 2, 7),(247, 1, '', '2025-12-01 16:45:03.546072', '2025-12-01 16:45:03.546072', 2, 8),(248, 1, '', '2025-12-01 16:45:03.547109', '2025-12-01 16:45:03.547109', 2, 9),(249, 0, '', '2025-12-01 16:45:03.548626', '2025-12-01 16:45:03.548626', 2, 10),(250, 1, '', '2025-12-01 16:45:03.551344', '2025-12-01 16:45:03.551344', 2, 11),(251, 1, '', '2025-12-01 16:45:03.553127', '2025-12-01 16:45:03.553127', 2, 12),(252, 1, '', '2025-12-01 16:45:03.555333', '2025-12-01 16:45:03.555333', 2, 13),(253, 1, '', '2025-12-01 16:45:03.556377', '2025-12-01 16:45:03.556898', 2, 14),(254, 1, '', '2025-12-01 16:45:03.558411', '2025-12-01 16:45:03.558411', 2, 15),(255, 1, '', '2025-12-01 16:45:03.559441', '2025-12-01 16:45:03.559441', 2, 16),(256, 1, '', '2025-12-01 16:45:03.560954', '2025-12-01 16:45:03.560954', 2, 17),(257, 0, '', '2025-12-01 16:45:03.562468', '2025-12-01 16:45:03.562468', 2, 18),(258, 0, '', '2025-12-01 16:45:03.563978', '2025-12-01 16:45:03.563978', 2, 19),(259, 1, '', '2025-12-01 16:45:03.567212', '2025-12-01 16:45:03.567212', 2, 20),(260, 1, '', '2025-12-01 16:45:03.568722', '2025-12-01 16:45:03.568722', 2, 21),(261, 1, '', '2025-12-01 16:45:03.570248', '2025-12-01 16:45:03.570248', 2, 22),(262, 1, '', '2025-12-01 16:45:03.571761', '2025-12-01 16:45:03.571761', 2, 23),(263, 0, '', '2025-12-01 16:45:03.573276', '2025-12-01 16:45:03.573276', 2, 25),(264, 1, '', '2025-12-01 16:45:03.574318', '2025-12-01 16:45:03.574318', 2, 26),(265, 1, '', '2025-12-01 16:45:03.576864', '2025-12-01 16:45:03.576864', 2, 27),(266, 1, '', '2025-12-01 16:45:03.576864', '2025-12-01 16:45:03.576864', 2, 28),(267, 1, '', '2025-12-01 16:45:03.578381', '2025-12-01 16:45:03.578381', 2, 29),(268, 1, '', '2025-12-01 16:45:03.579899', '2025-12-01 16:45:03.579899', 2, 30),(269, 0, '', '2025-12-01 16:45:03.581629', '2025-12-01 16:45:03.581629', 2, 31),(270, 1, '', '2025-12-01 16:45:03.584153', '2025-12-01 16:45:03.584153', 2, 32),(271, 0, '', '2025-12-01 16:45:03.586229', '2025-12-01 16:45:03.586229', 2, 33),(272, 1, '', '2025-12-01 16:45:03.587250', '2025-12-01 16:45:03.587250', 2, 34),(273, 1, '', '2025-12-01 16:45:03.588766', '2025-12-01 16:45:03.588766', 2, 35),(274, 0, '', '2025-12-01 16:45:03.590282', '2025-12-01 16:45:03.590282', 2, 36),(275, 1, '', '2025-12-01 16:45:03.591799', '2025-12-01 16:45:03.591799', 2, 37),(276, 1, '', '2025-12-01 16:45:03.594318', '2025-12-01 16:45:03.594318', 2, 38),(277, 1, '', '2025-12-01 16:45:03.596750', '2025-12-01 16:45:03.596750', 2, 39),(278, 1, '', '2025-12-01 16:45:03.597265', '2025-12-01 16:45:03.597265', 2, 40),(279, 1, '', '2025-12-01 16:45:03.598779', '2025-12-01 16:45:03.598779', 2, 41),(280, 1, '', '2025-12-01 16:45:03.601306', '2025-12-01 16:45:03.601306', 2, 42),(281, 1, '', '2025-12-01 16:45:03.602907', '2025-12-01 16:45:03.602907', 2, 43),(282, 1, '', '2025-12-01 16:45:03.604427', '2025-12-01 16:45:03.604427', 2, 44),(283, 1, '', '2025-12-01 16:45:03.606450', '2025-12-01 16:45:03.606450', 2, 45),(284, 1, '', '2025-12-01 16:45:03.607966', '2025-12-01 16:45:03.607966', 2, 46),(285, 1, '', '2025-12-01 16:45:03.608471', '2025-12-01 16:45:03.608471', 2, 47),(286, 1, '', '2025-12-01 16:45:03.611690', '2025-12-01 16:45:03.611690', 2, 48),(287, 1, '', '2025-12-01 16:45:03.613206', '2025-12-01 16:45:03.613206', 2, 49),(288, 1, '', '2025-12-01 16:45:03.614768', '2025-12-01 16:45:03.614768', 2, 50),(289, 1, '', '2025-12-01 16:45:03.616482', '2025-12-01 16:45:03.616482', 2, 51),(290, 1, '', '2025-12-01 16:45:03.618005', '2025-12-01 16:45:03.618005', 2, 52),(291, 1, '', '2025-12-01 16:45:03.620527', '2025-12-01 16:45:03.620527', 2, 53),(292, 0, '', '2025-12-01 16:45:03.622297', '2025-12-01 16:45:03.622297', 2, 54),(293, 0, '', '2025-12-01 16:45:03.625318', '2025-12-01 16:45:03.625318', 2, 55),(294, 1, '', '2025-12-01 16:45:03.626829', '2025-12-01 16:45:03.626829', 2, 56),(295, 1, '', '2025-12-01 16:45:03.628343', '2025-12-01 16:45:03.628343', 2, 57),(296, 1, '', '2025-12-01 16:45:03.629862', '2025-12-01 16:45:03.629862', 2, 58),(297, 1, '', '2025-12-01 16:45:03.632913', '2025-12-01 16:45:03.632913', 2, 59),(298, 1, '', '2025-12-01 16:45:03.634434', '2025-12-01 16:45:03.634434', 2, 60),(299, 1, '', '2025-12-01 16:45:03.636497', '2025-12-01 16:45:03.636497', 2, 61),(300, 1, '', '2025-12-01 16:45:03.638545', '2025-12-01 16:45:03.638545', 2, 62),(301, 1, '', '2025-12-01 16:45:03.640066', '2025-12-01 16:45:03.640066', 2, 63),(302, 1, '', '2025-12-01 16:45:03.641580', '2025-12-01 16:45:03.641580', 2, 64),(303, 1, '', '2025-12-01 16:45:03.643362', '2025-12-01 16:45:03.643362', 2, 65),(304, 1, '', '2025-12-01 16:45:03.644897', '2025-12-01 16:45:03.644897', 2, 66),(305, 1, '', '2025-12-01 16:45:03.648003', '2025-12-01 16:45:03.648003', 2, 67),(306, 1, '', '2025-12-01 16:45:03.649513', '2025-12-01 16:45:03.649513', 2, 68),(307, 1, '', '2025-12-01 16:45:03.651649', '2025-12-01 16:45:03.651649', 2, 69),(308, 0, '', '2025-12-01 16:45:03.653166', '2025-12-01 16:45:03.653166', 2, 70),(309, 1, '', '2025-12-01 16:45:03.655226', '2025-12-01 16:45:03.655226', 2, 71),(310, 1, '', '2025-12-01 16:45:03.657248', '2025-12-01 16:45:03.657248', 2, 72),(311, 1, '', '2025-12-01 16:45:03.659266', '2025-12-01 16:45:03.659266', 2, 73),(312, 1, '', '2025-12-01 16:45:03.660779', '2025-12-01 16:45:03.660779', 2, 74),(313, 1, '', '2025-12-01 16:45:03.662293', '2025-12-01 16:45:03.662293', 2, 75),(314, 1, '', '2025-12-01 16:45:03.663812', '2025-12-01 16:45:03.663812', 2, 76),(315, 1, '', '2025-12-01 16:45:03.666331', '2025-12-01 16:45:03.666331', 2, 77),(316, 1, '', '2025-12-01 16:45:03.667643', '2025-12-01 16:45:03.667643', 2, 78),(317, 1, '', '2025-12-01 16:45:03.669182', '2025-12-01 16:45:03.669182', 2, 79),(318, 1, '', '2025-12-01 16:45:03.670698', '2025-12-01 16:45:03.670698', 2, 80),(319, 1, '', '2025-12-01 16:45:03.672529', '2025-12-01 16:45:03.672529', 2, 81),(320, 1, '', '2025-12-01 16:45:03.674685', '2025-12-01 16:45:03.674685', 2, 82),(321, 1, '', '2025-12-01 16:45:03.677762', '2025-12-01 16:45:03.677762', 2, 83),(322, 1, '', '2025-12-01 16:45:03.679813', '2025-12-01 16:45:03.679813', 2, 84),(323, 1, '', '2025-12-01 16:45:03.681329', '2025-12-01 16:45:03.681329', 2, 85),(324, 1, '', '2025-12-01 16:45:03.682847', '2025-12-01 16:45:03.682847', 2, 86),(325, 1, '', '2025-12-01 16:45:03.685891', '2025-12-01 16:45:03.685891', 2, 87),(326, 1, '', '2025-12-01 16:45:03.687638', '2025-12-01 16:45:03.687638', 2, 88),(327, 1, '', '2025-12-01 16:45:03.688151', '2025-12-01 16:45:03.688151', 2, 89),(328, 1, '', '2025-12-01 16:45:03.691204', '2025-12-01 16:45:03.691204', 2, 90),(329, 1, '', '2025-12-01 16:45:03.692719', '2025-12-01 16:45:03.692719', 2, 91),(330, 1, '', '2025-12-01 16:45:03.694238', '2025-12-01 16:45:03.694238', 2, 92),(331, 0, '', '2025-12-01 16:45:03.696269', '2025-12-01 16:45:03.696269', 2, 93),(332, 1, '', '2025-12-01 16:45:03.698299', '2025-12-01 16:45:03.698299', 2, 94),(333, 1, '', '2025-12-01 16:45:03.700352', '2025-12-01 16:45:03.700352', 2, 95),(334, 1, '', '2025-12-01 16:45:03.701903', '2025-12-01 16:45:03.701903', 2, 96),(335, 0, '', '2025-12-01 16:45:03.705298', '2025-12-01 16:45:03.705298', 2, 97),(336, 1, '', '2025-12-01 16:45:03.706939', '2025-12-01 16:45:03.706939', 2, 98),(337, 1, '', '2025-12-01 16:45:03.708454', '2025-12-01 16:45:03.708454', 2, 99),(338, 1, '', '2025-12-01 16:45:03.711514', '2025-12-01 16:45:03.711514', 2, 100),(339, 1, '', '2025-12-01 16:45:03.713030', '2025-12-01 16:45:03.713030', 2, 101),(340, 0, '', '2025-12-01 16:45:03.716079', '2025-12-01 16:45:03.716079', 2, 102),(341, 1, '', '2025-12-01 16:45:03.717105', '2025-12-01 16:45:03.717105', 2, 103),(342, 0, '', '2025-12-01 16:45:03.719845', '2025-12-01 16:45:03.719845', 2, 104),(343, 0, '', '2025-12-01 16:45:03.721357', '2025-12-01 16:45:03.721357', 2, 105),(344, 0, '', '2025-12-01 16:45:03.722872', '2025-12-01 16:45:03.722872', 2, 106),(345, 1, '', '2025-12-01 16:45:03.724382', '2025-12-01 16:45:03.724382', 2, 107),(346, 0, '', '2025-12-01 16:45:03.726928', '2025-12-01 16:45:03.726928', 2, 108),(347, 1, '', '2025-12-01 16:45:03.728441', '2025-12-01 16:45:03.728441', 2, 109),(348, 1, '', '2025-12-01 16:45:03.729489', '2025-12-01 16:45:03.729489', 2, 110),(349, 1, '', '2025-12-01 16:45:03.732032', '2025-12-01 16:45:03.732032', 2, 111),(350, 1, '', '2025-12-01 16:45:03.733547', '2025-12-01 16:45:03.733547', 2, 112),(351, 0, '', '2025-12-01 16:45:03.735765', '2025-12-01 16:45:03.735765', 2, 113),(352, 1, '', '2025-12-01 16:45:03.737797', '2025-12-01 16:45:03.737797', 2, 114),(353, 1, '', '2025-12-01 16:45:03.739313', '2025-12-01 16:45:03.739313', 2, 115),(354, 0, '', '2025-12-01 16:45:03.741367', '2025-12-01 16:45:03.741367', 2, 116),(355, 1, '', '2025-12-01 16:45:03.741876', '2025-12-01 16:45:03.741876', 2, 117),(356, 1, '', '2025-12-01 16:45:03.743391', '2025-12-01 16:45:03.743391', 2, 118),(357, 1, '', '2025-12-01 16:45:03.746478', '2025-12-01 16:45:03.746478', 2, 119),(358, 1, '', '2025-12-01 16:45:03.747995', '2025-12-01 16:45:03.747995', 2, 120);
COMMIT;
BEGIN;
DELETE FROM "main"."dsb_rechtsform";
INSERT INTO "main"."dsb_rechtsform" ("id","code","name","description","is_active","sort_order","created_at","updated_at","requires_handelsregister") VALUES (1, 'gmbh', 'GmbH', '', 1, 1, '2025-12-01 16:00:16.913266', '2025-12-01 16:00:16.913266', 1),(2, 'ag', 'AG', '', 1, 2, '2025-12-01 16:00:16.920070', '2025-12-01 16:00:16.920070', 1),(3, 'eg', 'e.G.', '', 1, 3, '2025-12-01 16:00:16.927656', '2025-12-01 16:00:16.927656', 1),(4, 'ohg', 'OHG', '', 1, 4, '2025-12-01 16:00:16.934470', '2025-12-01 16:00:16.934470', 1),(5, 'kg', 'KG', '', 1, 5, '2025-12-01 16:00:16.941752', '2025-12-01 16:00:16.941752', 1),(6, 'einzelunternehmen', 'Einzelunternehmen', '', 1, 6, '2025-12-01 16:00:16.949684', '2025-12-01 16:00:16.949684', 0),(7, 'verein', 'Verein (e.V.)', '', 1, 7, '2025-12-01 16:00:16.958492', '2025-12-01 16:00:16.958492', 0);
COMMIT;
BEGIN;
DELETE FROM "main"."dsb_rechtsgrundlage";
INSERT INTO "main"."dsb_rechtsgrundlage" ("id","code","name","description","is_active","sort_order","created_at","updated_at","article_reference","requires_consent_management") VALUES (1, 'art6_1a', 'Art. 6 Abs. 1 lit. a (Einwilligung)', '', 1, 1, '2025-12-01 16:00:17.013736', '2025-12-01 16:00:17.013736', 'Art. 6(1)(a) DSGVO', 1),(2, 'art6_1b', 'Art. 6 Abs. 1 lit. b (Vertragserfüllung)', '', 1, 2, '2025-12-01 16:00:17.020631', '2025-12-01 16:00:17.020631', 'Art. 6(1)(b) DSGVO', 0),(3, 'art6_1c', 'Art. 6 Abs. 1 lit. c (Rechtliche Verpflichtung)', '', 1, 3, '2025-12-01 16:00:17.027708', '2025-12-01 16:00:17.027708', 'Art. 6(1)(c) DSGVO', 0),(4, 'art6_1f', 'Art. 6 Abs. 1 lit. f (Berechtigtes Interesse)', '', 1, 4, '2025-12-01 16:00:17.034776', '2025-12-01 16:00:17.034776', 'Art. 6(1)(f) DSGVO', 0);
COMMIT;
BEGIN;
DELETE FROM "main"."dsb_tom_kategorie";
INSERT INTO "main"."dsb_tom_kategorie" ("id","code","name","description","is_active","sort_order","created_at","updated_at") VALUES (1, 'tom_cat_1', 'Zutrittskontrolle', 'Unbefugten den Zutritt zu Datenverarbeitungsanlagen, mit denen personenbezogene Daten verarbeitet oder genutzt werden, zu verwehren.', 1, 10, '2025-12-01 16:45:02.886554', '2025-12-01 16:45:02.886554'),(2, 'tom_cat_2', 'Zugangskontrolle', 'Verhindern, dass Datenverarbeitungssysteme von Unbefugten genutzt werden können.', 1, 20, '2025-12-01 16:45:02.890591', '2025-12-01 16:45:02.890591'),(3, 'tom_cat_3', 'Zugriffskontrolle', 'Gewährleisten, dass die zur Benutzung eines Datenverarbeitungssystems Berechtigten ausschließlich auf die ihrer Zugriffsberechtigung unterliegenden Daten zugreifen können, und dass personenbezogene Daten bei der Verarbeitung, Nutzung und nach der Speicherung nicht unbefugt gelesen, kopiert, verändert oder entfernt werden können.', 1, 30, '2025-12-01 16:45:02.893334', '2025-12-01 16:45:02.893334'),(4, 'tom_cat_4', 'Weitergabekontrolle', 'Gewährleisten, dass personenbezogene Daten bei der elektronischen Übertragung oder während ihres Transports oder ihrer Speicherung auf Datenträger nicht unbefugt gelesen, kopiert, verändert oder entfernt werden können, und dass überprüft und festgestellt werden kann, an welche Stellen eine Übermittlung personenbezogener Daten durch Einrichtungen zur Datenübertragung vorgesehen ist.', 1, 40, '2025-12-01 16:45:02.895897', '2025-12-01 16:45:02.895897'),(5, 'tom_cat_5', 'Eingabekontrolle', 'Gewährleisten, dass nachträglich überprüft und festgestellt werden kann, ob und von wem personenbezogene Daten in Datenverarbeitungssysteme eingegeben, verändert oder entfernt worden sind.', 1, 50, '2025-12-01 16:45:02.897973', '2025-12-01 16:45:02.897973'),(6, 'tom_cat_6', 'Auftragskontrolle', 'Gewährleisten, dass personenbezogene Daten, die im Auftrag verarbeitet werden, nur entsprechend den Weisungen des Auftraggebers verarbeitet werden können.', 1, 60, '2025-12-01 16:45:02.898983', '2025-12-01 16:45:02.898983'),(7, 'tom_cat_7', 'Verfügbarkeitskontrolle', 'Gewährleisten, dass personenbezogene Daten gegen zufällige Zerstörung oder Verlust geschützt sind.', 1, 70, '2025-12-01 16:45:02.901761', '2025-12-01 16:45:02.901761'),(8, 'tom_cat_8', 'Trennungsgebot', 'Gewährleisten, dass zu unterschiedlichen Zwecken erhobene Daten getrennt verarbeitet werden können.', 1, 80, '2025-12-01 16:45:02.903799', '2025-12-01 16:45:02.903799');
COMMIT;
BEGIN;
DELETE FROM "main"."dsb_tom_massnahme";
INSERT INTO "main"."dsb_tom_massnahme" ("id","code","name","description","is_active","sort_order","created_at","updated_at","kategorie_id") VALUES (1, 'tom_2', 'Absicherung von Gebäudeschächten', '', 1, 2, '2025-12-01 16:45:02.907581', '2025-12-01 16:45:02.907581', 1),(2, 'tom_3', 'Alarmanlage', '', 1, 3, '2025-12-01 16:45:02.910261', '2025-12-01 16:45:02.910261', 1),(3, 'tom_4', 'Alarmmeldung bei unberechtigten Zutritten zu Serverräumen', '', 1, 4, '2025-12-01 16:45:02.911777', '2025-12-01 16:45:02.911777', 7),(4, 'tom_5', 'Anzahl der Administratoren auf das „Notwendigste“ reduziert', '', 1, 5, '2025-12-01 16:45:02.914819', '2025-12-01 16:45:02.914819', 3),(5, 'tom_6', 'Aufbewahrung von Datensicherung an einem sicheren, ausgelagerten Ort', '', 1, 6, '2025-12-01 16:45:02.916366', '2025-12-01 16:45:02.916366', 7),(6, 'tom_7', 'Aufbewahrung von Formularen, von denen Daten in automatisierte Verarbeitungen übernommen worden sind', '', 1, 7, '2025-12-01 16:45:02.917885', '2025-12-01 16:45:02.917885', 5),(7, 'tom_8', 'Auftragnehmer hat Datenschutzbeauftragten bestellt', '', 1, 8, '2025-12-01 16:45:02.919400', '2025-12-01 16:45:02.919400', 6),(8, 'tom_9', 'Auswahl des Auftragnehmers unter Sorgfaltsgesichtspunkten (insbesondere hinsichtlich Datensicherheit)', '', 1, 9, '2025-12-01 16:45:02.921948', '2025-12-01 16:45:02.921948', 6),(9, 'tom_10', 'Authentifikation mit Benutzername / Passwort', '', 1, 10, '2025-12-01 16:45:02.924762', '2025-12-01 16:45:02.924762', 2),(10, 'tom_11', 'Authentifikation mit biometrischen Verfahren', '', 1, 11, '2025-12-01 16:45:02.926433', '2025-12-01 16:45:02.926433', 2),(11, 'tom_12', 'Automatische Sperrung', '', 1, 12, '2025-12-01 16:45:02.927949', '2025-12-01 16:45:02.927949', 2),(12, 'tom_13', 'Automatisches Zugangskontrollsystem', '', 1, 13, '2025-12-01 16:45:02.929465', '2025-12-01 16:45:02.929465', 1),(13, 'tom_14', 'Backup-Strategie (offline)', '', 1, 14, '2025-12-01 16:45:02.930978', '2025-12-01 16:45:02.930978', 7),(14, 'tom_15', 'Backup-Strategie (online, z.B. Cloud)', '', 1, 15, '2025-12-01 16:45:02.932490', '2025-12-01 16:45:02.932490', 7),(15, 'tom_16', 'Bei pseudonymisierten Daten: Trennung der Zuordnungsdatei und der Aufbewahrung auf einem getrennten, abgesicherten IT-System', '', 1, 16, '2025-12-01 16:45:02.935013', '2025-12-01 16:45:02.935013', 8),(16, 'tom_17', 'Beim physischen Transport: sichere Transportbehälter/-verpackungen', '', 1, 17, '2025-12-01 16:45:02.936592', '2025-12-01 16:45:02.936592', 4),(17, 'tom_18', 'Beim physischen Transport: sorgfältige Auswahl von Transportpersonal und –fahrzeugen', '', 1, 18, '2025-12-01 16:45:02.937107', '2025-12-01 16:45:02.937107', 4),(18, 'tom_19', 'Biometrische Zugangssperren', '', 1, 19, '2025-12-01 16:45:02.939861', '2025-12-01 16:45:02.939861', 1),(19, 'tom_20', 'Chipkarten-/Transponder-Schließsystem', '', 1, 20, '2025-12-01 16:45:02.941375', '2025-12-01 16:45:02.941375', 1),(20, 'tom_21', 'Dokumentation der Empfänger von Daten und der Zeitspannen der geplanten Über-lassung bzw. vereinbarter Löschfristen', '', 1, 21, '2025-12-01 16:45:02.942892', '2025-12-01 16:45:02.942892', 4),(21, 'tom_22', 'Dokumentenmanagement, Dokumentenlenkung', '', 1, 22, '2025-12-01 16:45:02.945423', '2025-12-01 16:45:02.945423', 5),(22, 'tom_23', 'Dokumentenmanagement, Dokumentenlenkung', '', 1, 23, '2025-12-01 16:45:02.948127', '2025-12-01 16:45:02.948127', 4),(23, 'tom_24', 'E-Mail-Verschlüsselung', '', 1, 24, '2025-12-01 16:45:02.949645', '2025-12-01 16:45:02.949645', 4),(24, 'tom_25', 'Eine Pseudonymisierung findet nicht statt', '', 1, 25, '2025-12-01 16:45:02.951165', '2025-12-01 16:45:02.951165', 8),(25, 'tom_26', 'Eine Pseudonymisierung findet nicht statt', '', 1, 26, '2025-12-01 16:45:02.952682', '2025-12-01 16:45:02.952682', 8),(26, 'tom_27', 'Einrichtungen von Standleitungen bzw. VPN-Tunneln', '', 1, 27, '2025-12-01 16:45:02.954862', '2025-12-01 16:45:02.954862', 4),(27, 'tom_28', 'Einsatz einer Hardware-Firewall', '', 1, 28, '2025-12-01 16:45:02.956465', '2025-12-01 16:45:02.956465', 2),(28, 'tom_29', 'Einsatz einer Software-Firewall', '', 1, 29, '2025-12-01 16:45:02.958498', '2025-12-01 16:45:02.958498', 2),(29, 'tom_30', 'Einsatz von Aktenvernichtern bzw. Dienstleistern (nach Möglichkeit mit Datenschutz-Gütesiegel)', '', 1, 30, '2025-12-01 16:45:02.959008', '2025-12-01 16:45:02.959008', 3),(30, 'tom_31', 'Einsatz von Anti-Viren-Software', '', 1, 31, '2025-12-01 16:45:02.960520', '2025-12-01 16:45:02.960520', 2),(31, 'tom_32', 'Einsatz von Intrustion-Detection-Systemen', '', 1, 32, '2025-12-01 16:45:02.962037', '2025-12-01 16:45:02.962037', 2),(32, 'tom_33', 'Einsatz von VPN-Technologie', '', 1, 33, '2025-12-01 16:45:02.965075', '2025-12-01 16:45:02.965075', 2),(33, 'tom_34', 'Einsatz von zentraler Smartphone-Administrations-Software (z.B. zum externen Löschen von Daten)', '', 1, 34, '2025-12-01 16:45:02.966585', '2025-12-01 16:45:02.966585', 2),(34, 'tom_35', 'Elektronische Signatur', '', 1, 35, '2025-12-01 16:45:02.968097', '2025-12-01 16:45:02.968097', 4),(35, 'tom_36', 'Erstellen einer Übersicht von regelmäßigen Abruf- und Übermittlungsvorgängen', '', 1, 36, '2025-12-01 16:45:02.969608', '2025-12-01 16:45:02.969608', 4),(36, 'tom_37', 'Erstellen einer Übersicht, aus der sich ergibt, mit welchen Applikationen welche Daten eingegeben, geändert und gelöscht werden können.', '', 1, 37, '2025-12-01 16:45:02.970861', '2025-12-01 16:45:02.970861', 5),(37, 'tom_38', 'Erstellen eines Backup- & Recoverykonzepts', '', 1, 38, '2025-12-01 16:45:02.972373', '2025-12-01 16:45:02.972373', 7),(38, 'tom_39', 'Erstellen eines Berechtigungskonzepts', '', 1, 39, '2025-12-01 16:45:02.973887', '2025-12-01 16:45:02.973887', 3),(39, 'tom_40', 'Erstellen eines Notfallplans', '', 1, 40, '2025-12-01 16:45:02.976919', '2025-12-01 16:45:02.976919', 7),(40, 'tom_41', 'Erstellen von Benutzerprofilen', '', 1, 41, '2025-12-01 16:45:02.978433', '2025-12-01 16:45:02.978433', 2),(41, 'tom_42', 'Erstellung eines Berechtigungskonzepts', '', 1, 42, '2025-12-01 16:45:02.979948', '2025-12-01 16:45:02.979948', 8),(42, 'tom_43', 'Festlegung von Datenbankrechten', '', 1, 43, '2025-12-01 16:45:02.981467', '2025-12-01 16:45:02.981467', 8),(43, 'tom_44', 'Feuer- und Rauchmeldeanlagen', '', 1, 44, '2025-12-01 16:45:02.982983', '2025-12-01 16:45:02.982983', 7),(44, 'tom_45', 'Feuerlöschgeräte in Serverräumen', '', 1, 45, '2025-12-01 16:45:02.984011', '2025-12-01 16:45:02.984011', 7),(45, 'tom_46', 'Gebäudesicherung (Zäune, Pforten, ...)', '', 1, 46, '2025-12-01 16:45:02.986764', '2025-12-01 16:45:02.986764', 1),(46, 'tom_47', 'Gehäuseverriegelungen', '', 1, 47, '2025-12-01 16:45:02.988305', '2025-12-01 16:45:02.988305', 2),(47, 'tom_48', 'Geräte zur Überwachung von Temperatur und Feuchtigkeit in Serverräumen', '', 1, 48, '2025-12-01 16:45:02.989819', '2025-12-01 16:45:02.989819', 7),(48, 'tom_49', 'In Hochwassergebieten: Serverräume über der Wassergrenze', '', 1, 49, '2025-12-01 16:45:02.991332', '2025-12-01 16:45:02.991332', 7),(49, 'tom_50', 'Kennwortverfahren', '', 1, 50, '2025-12-01 16:45:02.992845', '2025-12-01 16:45:02.992845', 2),(50, 'tom_51', 'Klimaanlage in Serverräumen', '', 1, 51, '2025-12-01 16:45:02.994363', '2025-12-01 16:45:02.994363', 7),(51, 'tom_52', 'laufende Überprüfung des Auftragnehmers und seiner Tätigkeiten', '', 1, 52, '2025-12-01 16:45:02.996394', '2025-12-01 16:45:02.996394', 6),(52, 'tom_53', 'Lichtschranken / Bewegungsmelder', '', 1, 53, '2025-12-01 16:45:02.996911', '2025-12-01 16:45:02.996911', 1),(53, 'tom_54', 'Logische Mandantentrennung (softwareseitig)', '', 1, 54, '2025-12-01 16:45:02.998449', '2025-12-01 16:45:02.998449', 8),(54, 'tom_55', 'Manuelles Schließsystem', '', 1, 55, '2025-12-01 16:45:03.000474', '2025-12-01 16:45:03.000474', 1),(55, 'tom_56', 'Nachvollziehbarkeit von Eingabe, Änderung und Löschung von Daten durch individuelle Benutzernamen (nicht Benutzergruppen)', '', 1, 56, '2025-12-01 16:45:03.002202', '2025-12-01 16:45:03.002202', 5),(56, 'tom_57', 'Notfallmanagement inkl.Notfallpläne', '', 1, 57, '2025-12-01 16:45:03.003718', '2025-12-01 16:45:03.003718', 7),(57, 'tom_58', 'ordnungsgemäße Vernichtung von Datenträgern (DIN 32757)', '', 1, 58, '2025-12-01 16:45:03.005802', '2025-12-01 16:45:03.005802', 3),(58, 'tom_59', 'Passwortrichtlinie inkl. Passwortlänge, Passwortwechsel', '', 1, 59, '2025-12-01 16:45:03.006313', '2025-12-01 16:45:03.007320', 3),(59, 'tom_60', 'Passwortvergabe', '', 1, 60, '2025-12-01 16:45:03.007320', '2025-12-01 16:45:03.007320', 2),(60, 'tom_61', 'Personenkontrolle beim Pförtner / Empfang', '', 1, 61, '2025-12-01 16:45:03.009061', '2025-12-01 16:45:03.009061', 2),(61, 'tom_62', 'Personenkontrolle beim Pförtner / Empfang', '', 1, 62, '2025-12-01 16:45:03.010575', '2025-12-01 16:45:03.010575', 1),(62, 'tom_63', 'physikalisch getrennte Speicherung auf gesonderten Systemen oder Datenträgern', '', 1, 63, '2025-12-01 16:45:03.013613', '2025-12-01 16:45:03.013613', 8),(63, 'tom_64', 'physische Löschung von Datenträgern vor Wiederverwendung', '', 1, 64, '2025-12-01 16:45:03.015132', '2025-12-01 16:45:03.015132', 3),(64, 'tom_65', 'Plausibilitätskontrollen', '', 1, 65, '2025-12-01 16:45:03.016657', '2025-12-01 16:45:03.016657', 5),(65, 'tom_66', 'Protokollierung', '', 1, 66, '2025-12-01 16:45:03.018108', '2025-12-01 16:45:03.018108', 4),(66, 'tom_67', 'Protokollierung der Besucher', '', 1, 67, '2025-12-01 16:45:03.019621', '2025-12-01 16:45:03.019621', 2),(67, 'tom_68', 'Protokollierung der Besucher', '', 1, 68, '2025-12-01 16:45:03.021638', '2025-12-01 16:45:03.021638', 1),(68, 'tom_69', 'Protokollierung der Eingabe, Änderung und Löschung von Daten', '', 1, 69, '2025-12-01 16:45:03.023155', '2025-12-01 16:45:03.023155', 5),(69, 'tom_70', 'Protokollierung der Vernichtung', '', 1, 70, '2025-12-01 16:45:03.024697', '2025-12-01 16:45:03.024697', 3),(70, 'tom_71', 'Protokollierung von Zugriffen auf Anwendungen, insbesondere bei der Eingabe, Änderung und Löschung von Daten', '', 1, 71, '2025-12-01 16:45:03.026311', '2025-12-01 16:45:03.026311', 3),(71, 'tom_72', 'Protokollierungs- und Protokollauswertungssysteme (3 Monate Revisionssicher)', '', 1, 72, '2025-12-01 16:45:03.027832', '2025-12-01 16:45:03.027832', 5),(72, 'tom_73', 'Prüfung der Rechtmäßigkeit der Weitergabe von Daten', '', 1, 73, '2025-12-01 16:45:03.029371', '2025-12-01 16:45:03.029371', 4),(73, 'tom_74', 'Pseudonymisierung', '', 1, 74, '2025-12-01 16:45:03.030887', '2025-12-01 16:45:03.030887', 8),(74, 'tom_75', 'Remote-Administration', '', 1, 75, '2025-12-01 16:45:03.033152', '2025-12-01 16:45:03.033152', 5),(75, 'tom_76', 'Schließsystem mit Codesperre', '', 1, 76, '2025-12-01 16:45:03.035186', '2025-12-01 16:45:03.035703', 1),(76, 'tom_77', 'Schlüsselregelung (Schlüsselausgabe etc.)', '', 1, 77, '2025-12-01 16:45:03.037241', '2025-12-01 16:45:03.037241', 2),(77, 'tom_78', 'Schlüsselregelung (Schlüsselausgabe etc.)', '', 1, 78, '2025-12-01 16:45:03.038270', '2025-12-01 16:45:03.038270', 1),(78, 'tom_79', 'schriftliche Weisungen an den Auftragnehmer (z.B. durch Auftragsdatenverarbeitungsvertrag)', '', 1, 79, '2025-12-01 16:45:03.039802', '2025-12-01 16:45:03.039802', 6),(79, 'tom_80', 'Schutz vor Diebstahl', '', 1, 80, '2025-12-01 16:45:03.041318', '2025-12-01 16:45:03.041318', 7),(80, 'tom_81', 'Schutzsteckdosenleisten in Serverräumen', '', 1, 81, '2025-12-01 16:45:03.042832', '2025-12-01 16:45:03.042832', 7),(81, 'tom_82', 'Serverräume nicht unter sanitären Anlagen', '', 1, 82, '2025-12-01 16:45:03.044352', '2025-12-01 16:45:03.044352', 7),(82, 'tom_83', 'Sicherheitsschlösser', '', 1, 83, '2025-12-01 16:45:03.046894', '2025-12-01 16:45:03.046894', 2),(83, 'tom_84', 'Sicherheitsschlösser', '', 1, 84, '2025-12-01 16:45:03.048411', '2025-12-01 16:45:03.048411', 1),(84, 'tom_85', 'Sicherstellung der Vernichtung von Daten nach Beendigung des Auftrags', '', 1, 85, '2025-12-01 16:45:03.049671', '2025-12-01 16:45:03.049671', 6),(85, 'tom_86', 'Sicherung von Protokolldaten gegen Verlust oder Veränderung', '', 1, 86, '2025-12-01 16:45:03.051182', '2025-12-01 16:45:03.051182', 5),(86, 'tom_87', 'Sorgfältige Auswahl von Reinigungspersonal', '', 1, 87, '2025-12-01 16:45:03.052703', '2025-12-01 16:45:03.052703', 2),(87, 'tom_88', 'Sorgfältige Auswahl von Reinigungspersonal', '', 1, 88, '2025-12-01 16:45:03.055228', '2025-12-01 16:45:03.055228', 1),(88, 'tom_89', 'Sorgfältige Auswahl von Wachpersonal', '', 1, 89, '2025-12-01 16:45:03.056706', '2025-12-01 16:45:03.056706', 2),(89, 'tom_90', 'Sorgfältige Auswahl von Wachpersonal', '', 1, 90, '2025-12-01 16:45:03.058225', '2025-12-01 16:45:03.058225', 1),(90, 'tom_91', 'Sperren von externen Schnittstellen (USB etc.)', '', 1, 91, '2025-12-01 16:45:03.059270', '2025-12-01 16:45:03.059270', 2),(91, 'tom_92', 'Szenarioübungen (incl. worst-case)', '', 1, 92, '2025-12-01 16:45:03.060787', '2025-12-01 16:45:03.060787', 7),(92, 'tom_93', 'Testen von Datenwiederherstellung', '', 1, 93, '2025-12-01 16:45:03.062302', '2025-12-01 16:45:03.062302', 7),(93, 'tom_94', 'Tragepflicht von Berechtigungsausweisen', '', 1, 94, '2025-12-01 16:45:03.065020', '2025-12-01 16:45:03.065020', 2),(94, 'tom_95', 'Tragepflicht von Berechtigungsausweisen', '', 1, 95, '2025-12-01 16:45:03.066536', '2025-12-01 16:45:03.066536', 1),(95, 'tom_96', 'Transportsicherung', '', 1, 96, '2025-12-01 16:45:03.068061', '2025-12-01 16:45:03.068061', 4),(96, 'tom_97', 'Trennung von Produktiv- und Testsystem', '', 1, 97, '2025-12-01 16:45:03.069571', '2025-12-01 16:45:03.069571', 8),(97, 'tom_98', 'Two-Factor Authentication', '', 1, 98, '2025-12-01 16:45:03.070576', '2025-12-01 16:45:03.070576', 2),(98, 'tom_99', 'Unterbrechungsfreie Stromversorgung (USV)', '', 1, 99, '2025-12-01 16:45:03.072091', '2025-12-01 16:45:03.072091', 7),(99, 'tom_100', 'Vergabe von Rechten zur Eingabe, Änderung und Löschung von Daten auf Basis eines Berechtigungskonzepts', '', 1, 100, '2025-12-01 16:45:03.073606', '2025-12-01 16:45:03.073606', 5),(100, 'tom_101', 'Verpflichtung der Mitarbeiter des Auftragnehmers auf das Datengeheimnis', '', 1, 101, '2025-12-01 16:45:03.076127', '2025-12-01 16:45:03.076127', 6),(101, 'tom_102', 'Verschlüsselung /Tunnelverbindung', '', 1, 102, '2025-12-01 16:45:03.076631', '2025-12-01 16:45:03.076631', 4),(102, 'tom_103', 'Verschlüsselung von Datensätzen, die zu demselben Zweck verarbeitet werden', '', 1, 103, '2025-12-01 16:45:03.079154', '2025-12-01 16:45:03.079154', 8),(103, 'tom_104', 'Verschlüsselung von Datenträgern', '', 1, 104, '2025-12-01 16:45:03.079659', '2025-12-01 16:45:03.079659', 3),(104, 'tom_105', 'Verschlüsselung von Datenträgern in Laptops / Notebooks', '', 1, 105, '2025-12-01 16:45:03.081173', '2025-12-01 16:45:03.081173', 2),(105, 'tom_106', 'Verschlüsselung von mobilen Datenträgern', '', 1, 106, '2025-12-01 16:45:03.082686', '2025-12-01 16:45:03.082686', 2),(106, 'tom_107', 'Verschlüsselung von Smartphone-Inhalten', '', 1, 107, '2025-12-01 16:45:03.084195', '2025-12-01 16:45:03.084195', 2),(107, 'tom_108', 'Versehen der Datensätze mit Zweckattributen/Datenfeldern', '', 1, 108, '2025-12-01 16:45:03.086791', '2025-12-01 16:45:03.086791', 8),(108, 'tom_109', 'Vertragsstrafen bei Verstößen', '', 1, 109, '2025-12-01 16:45:03.088309', '2025-12-01 16:45:03.088309', 6),(109, 'tom_110', 'Verwaltung der Rechte durch Systemadministrator', '', 1, 110, '2025-12-01 16:45:03.089822', '2025-12-01 16:45:03.089822', 3),(110, 'tom_111', 'Verwendung von Administrationssoftware für Smartphone', '', 1, 111, '2025-12-01 16:45:03.091362', '2025-12-01 16:45:03.091362', 7),(111, 'tom_112', 'Videoüberwachung der Zugänge', '', 1, 112, '2025-12-01 16:45:03.092878', '2025-12-01 16:45:03.092878', 1),(112, 'tom_113', 'Videoüberwachung Eingangstür', '', 1, 113, '2025-12-01 16:45:03.095394', '2025-12-01 16:45:03.095394', 1),(113, 'tom_114', 'vorherige Prüfung der und Dokumentation der beim Auftragnehmer getroffenen Sicherheitsmaßnahmen', '', 1, 114, '2025-12-01 16:45:03.096929', '2025-12-01 16:45:03.096929', 6),(114, 'tom_115', 'Weitergabe von Daten in anonymisierter oder pseudonymisierter Form', '', 1, 115, '2025-12-01 16:45:03.098442', '2025-12-01 16:45:03.098442', 4),(115, 'tom_116', 'Wirksame Kontrollrechte gegenüber dem Auftragnehmer vereinbart', '', 1, 116, '2025-12-01 16:45:03.099951', '2025-12-01 16:45:03.099951', 6),(116, 'tom_117', 'Zugriff nur über Bürgerkarte, Handysignatur und Bentutzername und Password', '', 1, 117, '2025-12-01 16:45:03.101484', '2025-12-01 16:45:03.101484', 3),(117, 'tom_118', 'Zuordnung von Benutzerprofilen zu IT-Systemen', '', 1, 118, '2025-12-01 16:45:03.103001', '2025-12-01 16:45:03.103001', 2),(118, 'tom_119', 'Zuordnung von Benutzerrechten', '', 1, 119, '2025-12-01 16:45:03.105569', '2025-12-01 16:45:03.105569', 2),(119, 'tom_120', 'Übersicht von regelmäßigen Abruf-und Übermittlungsvorgängen', '', 1, 120, '2025-12-01 16:45:03.107096', '2025-12-01 16:45:03.107096', 4),(120, 'tom_121', 'Überspannungsschutz', '', 1, 121, '2025-12-01 16:45:03.108611', '2025-12-01 16:45:03.108611', 7);
COMMIT;
BEGIN;
DELETE FROM "main"."dsb_verarbeitung";
COMMIT;
BEGIN;
DELETE FROM "main"."dsb_verarbeitung_datenkategorien";
COMMIT;
BEGIN;
DELETE FROM "main"."dsb_vorfall";
COMMIT;
BEGIN;
DELETE FROM "main"."dsb_vorfall_typ";
INSERT INTO "main"."dsb_vorfall_typ" ("id","code","name","description","is_active","sort_order","created_at","updated_at","default_severity_id") VALUES (1, 'unbefugter_zugriff', 'Unbefugter Zugriff', '', 1, 1, '2025-12-01 16:00:17.089037', '2025-12-01 16:00:17.089037', NULL),(2, 'datenverlust', 'Datenverlust', '', 1, 2, '2025-12-01 16:00:17.096651', '2025-12-01 16:00:17.096651', NULL),(3, 'ransomware', 'Ransomware/Verschlüsselung', '', 1, 3, '2025-12-01 16:00:17.104563', '2025-12-01 16:00:17.104563', NULL),(4, 'phishing', 'Phishing-Angriff', '', 1, 4, '2025-12-01 16:00:17.112171', '2025-12-01 16:00:17.112171', NULL),(5, 'fehlversand', 'Fehlversand/Falsche Empfänger', '', 1, 5, '2025-12-01 16:00:17.118911', '2025-12-01 16:00:17.118911', NULL),(6, 'diebstahl', 'Diebstahl/Verlust Hardware', '', 1, 6, '2025-12-01 16:00:17.126566', '2025-12-01 16:00:17.126566', NULL),(7, 'sonstiges', 'Sonstiges', '', 1, 7, '2025-12-01 16:00:17.135406', '2025-12-01 16:00:17.135406', NULL);
COMMIT;
BEGIN;
DELETE FROM "main"."enrichment_responses";
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_assessments";
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_assessments_team_members";
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_auditlog";
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_building";
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_data_source_config";
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_data_source_metric";
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_document_type";
INSERT INTO "main"."expert_hub_document_type" ("id","code","name","description","requires_atex_compliance","icon","is_active","sort_order","created_at","updated_at") VALUES (1, 'explosionsschutz_dokument', 'Explosionsschutz-Dokument', 'Hauptdokument', 0, '', 1, 1, '2025-11-27 12:28:46.917018', '2025-11-27 12:28:46.917018'),(2, 'sicherheitsdatenblatt', 'Sicherheitsdatenblatt', 'SDB', 0, '', 1, 2, '2025-11-27 12:28:46.932778', '2025-11-27 12:28:46.932778'),(3, 'gefaehrdungsbeurteilung', 'Gefährdungsbeurteilung', 'GB', 0, '', 1, 3, '2025-11-27 12:28:46.945812', '2025-11-27 12:28:46.945812'),(4, 'betriebsanweisung', 'Betriebsanweisung', 'BA', 0, '', 1, 4, '2025-11-27 12:28:46.958494', '2025-11-27 12:28:46.958494'),(5, 'pruefprotokoll', 'Prüfprotokoll', 'Prüfung', 0, '', 1, 5, '2025-11-27 12:28:46.970480', '2025-11-27 12:28:46.970480');
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_equipment";
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_equipment_category";
INSERT INTO "main"."expert_hub_equipment_category" ("id","code","name_de","name_en","protection_level","category_type","applicable_zones","description","requirements","sort_order","is_active","created_at","updated_at") VALUES (1, '1G', 'Kategorie 1G (sehr hoher Schutz)', 'Category 1G (very high protection)', 1, 'GAS', '[0, 1, 2]', 'Höchster Schutz für Zone 0, 1 und 2', '2 unabhängige Schutzmittel oder sicher bei 2 Fehlern', 10, 1, '2025-12-01 19:33:01.989090', '2025-12-01 20:45:16.721294'),(2, '2G', 'Kategorie 2G (hoher Schutz)', 'Category 2G (high protection)', 2, 'GAS', '[1, 2]', 'Hoher Schutz für Zone 1 und 2', 'Geeignet für normalen Betrieb und häufige Störungen', 20, 1, '2025-12-01 19:33:01.996196', '2025-12-01 20:45:16.726364'),(3, '3G', 'Kategorie 3G (normaler Schutz)', 'Category 3G (normal protection)', 3, 'GAS', '[2]', 'Normaler Schutz nur für Zone 2', 'Geeignet für normalen Betrieb', 30, 1, '2025-12-01 19:33:02.005604', '2025-12-01 20:45:16.731959'),(4, '1D', 'Kategorie 1D (sehr hoher Schutz)', 'Category 1D (very high protection)', 1, 'DUST', '[20, 21, 22]', 'Höchster Schutz für Zone 20, 21 und 22', '2 unabhängige Schutzmittel oder sicher bei 2 Fehlern', 40, 1, '2025-12-01 19:33:02.013986', '2025-12-01 20:45:16.738021'),(5, '2D', 'Kategorie 2D (hoher Schutz)', 'Category 2D (high protection)', 2, 'DUST', '[21, 22]', 'Hoher Schutz für Zone 21 und 22', 'Geeignet für normalen Betrieb und häufige Störungen', 50, 1, '2025-12-01 19:33:02.021591', '2025-12-01 20:45:16.743616'),(6, '3D', 'Kategorie 3D (normaler Schutz)', 'Category 3D (normal protection)', 3, 'DUST', '[22]', 'Normaler Schutz nur für Zone 22', 'Geeignet für normalen Betrieb', 60, 1, '2025-12-01 19:33:02.030430', '2025-12-01 20:45:16.750183');
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_equipment_gutachten";
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_explosion_group";
INSERT INTO "main"."expert_hub_explosion_group" ("id","code","name_de","name_en","category","description","danger_level","sort_order","is_active","created_at","updated_at") VALUES (1, 'IIA', 'Explosionsgruppe IIA', 'Explosion Group IIA', 'GAS', 'Niedrigste Zündenergie, z.B. Propan, Benzin, Aceton', 1, 10, 1, '2025-12-01 19:33:01.891938', '2025-12-01 20:45:16.648575'),(2, 'IIB', 'Explosionsgruppe IIB', 'Explosion Group IIB', 'GAS', 'Mittlere Zündenergie, z.B. Ethylen, Ethylether', 2, 20, 1, '2025-12-01 19:33:01.900695', '2025-12-01 20:45:16.654149'),(3, 'IIC', 'Explosionsgruppe IIC', 'Explosion Group IIC', 'GAS', 'Höchste Zündgefahr, z.B. Wasserstoff, Acetylen', 3, 30, 1, '2025-12-01 19:33:01.908535', '2025-12-01 20:45:16.660385'),(4, 'IIIA', 'Explosionsgruppe IIIA', 'Explosion Group IIIA', 'DUST', 'Brennbare Fasern und Flusen', 1, 40, 1, '2025-12-01 19:33:01.915602', '2025-12-01 20:45:16.664944'),(5, 'IIIB', 'Explosionsgruppe IIIB', 'Explosion Group IIIB', 'DUST', 'Nichtleitfähige Stäube', 2, 50, 1, '2025-12-01 19:33:01.924585', '2025-12-01 20:45:16.671051'),(6, 'IIIC', 'Explosionsgruppe IIIC', 'Explosion Group IIIC', 'DUST', 'Leitfähige Stäube', 3, 60, 1, '2025-12-01 19:33:01.932178', '2025-12-01 20:45:16.677105');
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_exschutzdocument";
INSERT INTO "main"."expert_hub_exschutzdocument" ("id","project_id","uuid","document_type_legacy","file_name","file_path","file_size_bytes","uploaded_at","processing_status_legacy","processing_started_at","processing_completed_at","extracted_text","extraction_method","page_count","overall_confidence","extraction_quality_score","needs_human_review","review_reason","reviewed_at","review_notes","ai_model_used","total_ai_tokens","total_ai_cost","workflow_id","created_at","updated_at","customer_id","document_type_id","reviewed_by_id","uploaded_by_id","processing_status_id") VALUES (1, NULL, 'd9cce6a66f044096925dca8751418181', 'explosionsschutz_dokument', 'Ex-Schutzdokument_Senkrechtofen_5_K225_200125.pdf', 'expert_hub/2/Ex-Schutzdokument_Senkrechtofen_5_K225_200125_Dy7BP9F.pdf', 717092, '2025-12-01 07:09:51.825309', 'uploaded', '2025-12-01 17:22:21.998006', NULL, '', '', NULL, NULL, NULL, 0, '', NULL, '', '', NULL, NULL, NULL, '2025-12-01 07:09:51.825309', '2025-12-01 16:22:22.001041', 1, 1, NULL, 2, 2);
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_exzone";
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_facility";
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_facility_hazmat";
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_facility_type";
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_gefahrstoff";
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_gutachten";
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_gutachten_betroffene_vorschriften";
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_hazmat_catalog";
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_ignition_protection_type";
INSERT INTO "main"."expert_hub_ignition_protection_type" ("id","code","name_de","name_en","atex_symbol","description","principle","applicable_to","sort_order","is_active","created_at","updated_at") VALUES (1, 'd', 'Druckfeste Kapselung', 'Flameproof enclosure', 'Ex d', 'Umschließung hält innerer Explosion stand', 'Innere Explosion wird zugelassen, aber eingeschlossen', 'GAS', 10, 1, '2025-12-01 19:33:02.037541', '2025-12-01 20:45:16.755946'),(2, 'e', 'Erhöhte Sicherheit', 'Increased safety', 'Ex e', 'Erhöhte Sicherheit gegen Funkenbildung', 'Konstruktive Maßnahmen verhindern unzulässige Erwärmung und Funkenbildung', 'GAS', 20, 1, '2025-12-01 19:33:02.046340', '2025-12-01 20:45:16.762020'),(3, 'i', 'Eigensicherheit', 'Intrinsic safety', 'Ex i', 'Energiebegrenzung verhindert Zündung', 'Elektrische Energie wird so begrenzt, dass keine Zündung möglich ist', 'BOTH', 30, 1, '2025-12-01 19:33:02.054539', '2025-12-01 20:45:16.766573'),(4, 'm', 'Vergusskapselung', 'Encapsulation', 'Ex m', 'Elektrische Teile in Vergussmasse eingeschlossen', 'Zündquellen werden durch Vergussmasse von der Atmosphäre getrennt', 'BOTH', 40, 1, '2025-12-01 19:33:02.062904', '2025-12-01 20:45:16.772802'),(5, 'p', 'Druckkapselung', 'Pressurization', 'Ex p', 'Schutzgas verhindert Eindringen explosiver Atmosphäre', 'Überdruck mit Schutzgas verhindert Eintritt explosiver Atmosphäre', 'GAS', 50, 1, '2025-12-01 19:33:02.070115', '2025-12-01 20:45:16.778356'),(6, 'q', 'Sandkapselung', 'Powder filling', 'Ex q', 'Füllung mit Sand verhindert Funkenübertritt', 'Zündquellen sind in feinkörnigem Material eingekapselt', 'GAS', 60, 1, '2025-12-01 19:33:02.077369', '2025-12-01 20:45:16.784414'),(7, 'o', 'Ölkapselung', 'Oil immersion', 'Ex o', 'Eintauchen in Öl', 'Zündquellen sind in Öl eingetaucht', 'GAS', 70, 1, '2025-12-01 19:33:02.085630', '2025-12-01 20:45:16.790488'),(8, 't', 'Schutz durch Gehäuse', 'Protection by enclosure', 'Ex t', 'Gehäuseschutz gegen Staubablagerungen', 'Gehäuse verhindert Eindringen von Staub', 'DUST', 80, 1, '2025-12-01 19:33:02.093951', '2025-12-01 20:45:16.796596'),(9, 'pD', 'Druckkapselung (Staub)', 'Pressurization (Dust)', 'Ex pD', 'Überdruck verhindert Staubeintritt', 'Schutzgas hält Staub vom Gehäuseinneren fern', 'DUST', 90, 1, '2025-12-01 19:33:02.101552', '2025-12-01 20:45:16.802330');
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_physical_state";
INSERT INTO "main"."expert_hub_physical_state" ("id","code","name_de","name_en","symbol","description","sort_order","is_active","created_at","updated_at") VALUES (1, 'FEST', 'fest', 'solid', '⬛', 'Fester Aggregatzustand (Pulver, Granulat, etc.)', 10, 1, '2025-12-01 19:33:02.109417', '2025-12-01 20:45:16.807383'),(2, 'FLUESSIG', 'flüssig', 'liquid', '💧', 'Flüssiger Aggregatzustand', 20, 1, '2025-12-01 19:33:02.117558', '2025-12-01 20:45:16.813469'),(3, 'GASFOERMIG', 'gasförmig', 'gaseous', '☁️', 'Gasförmiger Aggregatzustand', 30, 1, '2025-12-01 19:33:02.126315', '2025-12-01 20:45:16.818161'),(4, 'DAMPF', 'Dampf', 'vapor', '♨️', 'Dampfförmig (verdampfte Flüssigkeit)', 40, 1, '2025-12-01 19:33:02.134851', '2025-12-01 20:45:16.825233'),(5, 'NEBEL', 'Nebel', 'mist', '🌫️', 'Aerosol/Nebel (fein verteilte Flüssigkeitströpfchen)', 50, 1, '2025-12-01 19:33:02.142121', '2025-12-01 20:45:16.830798'),(6, 'STAUB', 'Staub', 'dust', '💨', 'Feinstaub (brennbare Staubwolke)', 60, 1, '2025-12-01 19:33:02.149774', '2025-12-01 20:45:16.836355');
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_processing_status_type";
INSERT INTO "main"."expert_hub_processing_status_type" ("id","code","name","description","category","color","icon","is_final","sort_order","is_active","created_at","updated_at") VALUES (1, 'uploaded', 'Hochgeladen', 'Neu', '', 'secondary', '', 0, 1, 1, '2025-11-27 12:28:46.982489', '2025-11-27 12:28:46.982489'),(2, 'extracting', 'Extrahiere Text', 'OCR läuft', '', 'secondary', '', 0, 2, 1, '2025-11-27 12:28:46.994978', '2025-11-27 12:28:46.994978'),(3, 'analyzing', 'Analysiere', 'AI Analyse', '', 'secondary', '', 0, 3, 1, '2025-11-27 12:28:47.007382', '2025-11-27 12:28:47.007382'),(4, 'validating', 'Validiere', 'Prüfung', '', 'secondary', '', 0, 4, 1, '2025-11-27 12:28:47.017572', '2025-11-27 12:28:47.017572'),(5, 'needs_review', 'Review erforderlich', 'Manuell', '', 'secondary', '', 0, 5, 1, '2025-11-27 12:28:47.029948', '2025-11-27 12:28:47.029948'),(6, 'reviewed', 'Überprüft', 'Geprüft', '', 'secondary', '', 0, 6, 1, '2025-11-27 12:28:47.042429', '2025-11-27 12:28:47.042429'),(7, 'approved', 'Freigegeben', 'Final', '', 'secondary', '', 0, 7, 1, '2025-11-27 12:28:47.053816', '2025-11-27 12:28:47.053816'),(8, 'failed', 'Fehler', 'Error', '', 'secondary', '', 0, 8, 1, '2025-11-27 12:28:47.066086', '2025-11-27 12:28:47.066086'),(9, 'completed', 'Abgeschlossen', 'Fertig', '', 'secondary', '', 0, 9, 1, '2025-11-27 12:28:47.078459', '2025-11-27 12:28:47.078459');
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_regulation";
INSERT INTO "main"."expert_hub_regulation" ("id","nummer","vollstaendige_bezeichnung","titel","untertitel","ausgabedatum","version","status","gueltig_ab","gueltig_bis","zusammenfassung","anwendungsbereich","hauptinhalte","volltext","auszuege_json","relevanz_explosionsschutz","explosionsschutz_themen","betroffene_zonen","referenzierte_normen","externe_links","quelle_url","download_url","bezugsquelle","kostenpflichtig","importiert_am","import_quelle","import_metadaten","bemerkungen","schlagworte","created_at","updated_at","created_by_id","ersetzt_durch_id","regulation_type_id") VALUES (1, '510', 'TRGS 510', 'Lagerung von Gefahrstoffen in ortsbeweglichen Behältern', '', '2021-05-01', '', 'GUELTIG', NULL, NULL, '', '', '', '', '{}', 'HOCH', '[]', '[]', '', '[]', 'https://www.baua.de/DE/Angebote/Rechtstexte-und-Technische-Regeln/Regelwerk/TRGS/TRGS-510.html', '', '', 0, '2025-12-01 21:45:24.514822', 'Manuell', '{}', '', '[]', '2025-12-01 20:45:24.522487', '2025-12-01 20:45:24.522487', NULL, NULL, 1),(2, '720', 'TRGS 720', 'Gefährliche explosionsfähige Gemische - Allgemeines', '', '2016-10-01', '', 'GUELTIG', NULL, NULL, '', '', '', '', '{}', 'HOCH', '[]', '[]', '', '[]', 'https://www.baua.de/DE/Angebote/Rechtstexte-und-Technische-Regeln/Regelwerk/TRGS/TRGS-720.html', '', '', 0, '2025-12-01 21:45:24.530389', 'Manuell', '{}', '', '[]', '2025-12-01 20:45:24.531904', '2025-12-01 20:45:24.531904', NULL, NULL, 1),(3, '721', 'TRGS 721', 'Gefährliche explosionsfähige Gemische - Beurteilung der Explosionsgefährdung', '', '2021-02-01', '', 'GUELTIG', NULL, NULL, '', '', '', '', '{}', 'HOCH', '[]', '[]', '', '[]', 'https://www.baua.de/DE/Angebote/Rechtstexte-und-Technische-Regeln/Regelwerk/TRGS/TRGS-721.html', '', '', 0, '2025-12-01 21:45:24.538966', 'Manuell', '{}', '', '[]', '2025-12-01 20:45:24.540489', '2025-12-01 20:45:24.540489', NULL, NULL, 1),(4, '722', 'TRGS 722', 'Vermeidung oder Einschränkung gefährlicher explosionsfähiger Atmosphäre', '', '2021-07-01', '', 'GUELTIG', NULL, NULL, '', '', '', '', '{}', 'HOCH', '[]', '[]', '', '[]', 'https://www.baua.de/DE/Angebote/Rechtstexte-und-Technische-Regeln/Regelwerk/TRGS/TRGS-722.html', '', '', 0, '2025-12-01 21:45:24.548603', 'Manuell', '{}', '', '[]', '2025-12-01 20:45:24.550120', '2025-12-01 20:45:24.550120', NULL, NULL, 1),(5, '723', 'TRGS 723', 'Gefährliche explosionsfähige Gemische - Vermeidung der Entzündung gefährlicher explosionsfähiger Gemische', '', '2019-02-01', '', 'GUELTIG', NULL, NULL, '', '', '', '', '{}', 'HOCH', '[]', '[]', '', '[]', 'https://www.baua.de/DE/Angebote/Rechtstexte-und-Technische-Regeln/Regelwerk/TRGS/TRGS-723.html', '', '', 0, '2025-12-01 21:45:24.557201', 'Manuell', '{}', '', '[]', '2025-12-01 20:45:24.558718', '2025-12-01 20:45:24.558718', NULL, NULL, 1),(6, '2152 Teil 2', 'TRBS 2152 Teil 2', 'Gefährliche explosionsfähige Atmosphäre - Allgemeines', '', '2019-10-01', '', 'GUELTIG', NULL, NULL, '', '', '', '', '{}', 'HOCH', '[]', '[]', '', '[]', 'https://www.baua.de/DE/Angebote/Rechtstexte-und-Technische-Regeln/Regelwerk/TRBS/TRBS-2152-2.html', '', '', 0, '2025-12-01 21:45:24.566963', 'Manuell', '{}', '', '[]', '2025-12-01 20:45:24.566963', '2025-12-01 20:45:24.566963', NULL, NULL, 2),(7, '2152 Teil 3', 'TRBS 2152 Teil 3', 'Gefährliche explosionsfähige Atmosphäre - Vermeidung oder Einschränkung gefährlicher explosionsfähiger Atmosphäre', '', '2019-10-01', '', 'GUELTIG', NULL, NULL, '', '', '', '', '{}', 'HOCH', '[]', '[]', '', '[]', 'https://www.baua.de/DE/Angebote/Rechtstexte-und-Technische-Regeln/Regelwerk/TRBS/TRBS-2152-3.html', '', '', 0, '2025-12-01 21:45:24.575565', 'Manuell', '{}', '', '[]', '2025-12-01 20:45:24.576751', '2025-12-01 20:45:24.576751', NULL, NULL, 2),(8, '2152 Teil 4', 'TRBS 2152 Teil 4', 'Gefährliche explosionsfähige Atmosphäre - Vermeidung der Entzündung gefährlicher explosionsfähiger Atmosphäre', '', '2019-10-01', '', 'GUELTIG', NULL, NULL, '', '', '', '', '{}', 'HOCH', '[]', '[]', '', '[]', 'https://www.baua.de/DE/Angebote/Rechtstexte-und-Technische-Regeln/Regelwerk/TRBS/TRBS-2152-4.html', '', '', 0, '2025-12-01 21:45:24.584203', 'Manuell', '{}', '', '[]', '2025-12-01 20:45:24.585230', '2025-12-01 20:45:24.585230', NULL, NULL, 2);
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_regulation_type";
INSERT INTO "main"."expert_hub_regulation_type" ("id","code","name_de","name_en","abkuerzung","beschreibung","herausgeber","rechtscharakter","farbe","icon","sort_order","is_active","created_at","updated_at") VALUES (1, 'TRGS', 'Technische Regeln für Gefahrstoffe', 'Technical Rules for Hazardous Substances', 'TRGS', 'Technische Regeln, die den Stand der Technik bei Tätigkeiten mit Gefahrstoffen wiedergeben', 'BAuA (Bundesanstalt für Arbeitsschutz und Arbeitsmedizin)', 'TECHNISCHE_REGEL', '#e74c3c', 'bi-file-earmark-text', 10, 1, '2025-12-01 20:45:20.628652', '2025-12-01 20:45:20.628652'),(2, 'TRBS', 'Technische Regeln für Betriebssicherheit', 'Technical Rules for Operational Safety', 'TRBS', 'Technische Regeln zur Konkretisierung der Betriebssicherheitsverordnung', 'BAuA', 'TECHNISCHE_REGEL', '#3498db', 'bi-shield-check', 20, 1, '2025-12-01 20:45:20.635757', '2025-12-01 20:45:20.635757'),(3, 'BetrSichV', 'Betriebssicherheitsverordnung', 'Occupational Safety Ordinance', 'BetrSichV', 'Verordnung über Sicherheit und Gesundheitsschutz bei der Verwendung von Arbeitsmitteln', 'BMAS (Bundesministerium für Arbeit und Soziales)', 'VERORDNUNG', '#2ecc71', 'bi-file-earmark-check', 30, 1, '2025-12-01 20:45:20.642838', '2025-12-01 20:45:20.642838'),(4, 'GefStoffV', 'Gefahrstoffverordnung', 'Hazardous Substances Ordinance', 'GefStoffV', 'Verordnung zum Schutz vor Gefahrstoffen', 'BMAS', 'VERORDNUNG', '#f39c12', 'bi-exclamation-triangle', 40, 1, '2025-12-01 20:45:20.649661', '2025-12-01 20:45:20.649661'),(5, 'DGUV', 'DGUV Vorschriften und Regeln', 'DGUV Regulations and Rules', 'DGUV', 'Vorschriften, Regeln und Informationen der Deutschen Gesetzlichen Unfallversicherung', 'DGUV (Deutsche Gesetzliche Unfallversicherung)', 'VORSCHRIFT', '#9b59b6', 'bi-heart-pulse', 50, 1, '2025-12-01 20:45:20.655761', '2025-12-01 20:45:20.655761'),(6, 'EN', 'Europäische Normen', 'European Standards', 'EN', 'Europäische Normen für technische Anforderungen', 'CEN (Europäisches Komitee für Normung)', 'NORM', '#1abc9c', 'bi-globe', 60, 1, '2025-12-01 20:45:20.664076', '2025-12-01 20:45:20.664076'),(7, 'DIN', 'DIN-Normen', 'DIN Standards', 'DIN', 'Deutsche Industrie-Normen', 'DIN (Deutsches Institut für Normung)', 'NORM', '#34495e', 'bi-gear', 70, 1, '2025-12-01 20:45:20.671670', '2025-12-01 20:45:20.671670'),(8, 'ATEX', 'ATEX-Richtlinien', 'ATEX Directives', 'ATEX', 'EU-Richtlinien für explosionsgefährdete Bereiche (ATmosphères EXplosibles)', 'EU-Kommission', 'RICHTLINIE', '#e67e22', 'bi-fire', 80, 1, '2025-12-01 20:45:20.679126', '2025-12-01 20:45:20.679126');
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_regulation_verwandte_vorschriften";
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_schutzmassnahme";
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_substance_data_import";
INSERT INTO "main"."expert_hub_substance_data_import" ("id","substance_name","cas_number","source_type","imported_data","imported_at","source_url","confidence_score","success","error_message","response_time","imported_by_id") VALUES (1, 'propan-2-one', '67-64-1', 'pubchem', '{"name": "propan-2-one", "cas_number": "67-64-1", "formula": "C3H6O", "molecular_weight": 58.08, "melting_point": null, "boiling_point": null, "flash_point": null, "density": null, "explosion_limit_lower": null, "explosion_limit_upper": null, "ignition_temperature": null, "vapor_pressure": null, "ghs_classification": [], "hazard_statements": [], "data_sources": ["PubChem"], "pubchem_cid": 180, "synonyms": ["acetone", "2-propanone", "propanone", "67-64-1", "Dimethyl ketone", "propan-2-one", "Pyroacetic ether", "Methyl ketone", "Dimethylformaldehyde", "beta-Ketopropane"]}', '2025-11-30 15:26:47.234189', 'https://pubchem.ncbi.nlm.nih.gov/compound/180', 1.0, 1, '', 3.001334, NULL),(2, 'propan-2-one', '67-64-1', 'pubchem', '{"name": "propan-2-one", "cas_number": "67-64-1", "formula": "C3H6O", "molecular_weight": 58.08, "melting_point": null, "boiling_point": null, "flash_point": null, "density": null, "explosion_limit_lower": null, "explosion_limit_upper": null, "ignition_temperature": null, "vapor_pressure": null, "ghs_classification": [], "hazard_statements": [], "data_sources": ["PubChem"], "pubchem_cid": 180, "synonyms": ["acetone", "2-propanone", "propanone", "67-64-1", "Dimethyl ketone", "propan-2-one", "Pyroacetic ether", "Methyl ketone", "Dimethylformaldehyde", "beta-Ketopropane"]}', '2025-11-30 15:28:27.102951', 'https://pubchem.ncbi.nlm.nih.gov/compound/180', 1.0, 1, '', 0.009727, NULL),(3, 'toluene', '108-88-3', 'pubchem', '{"name": "toluene", "cas_number": "108-88-3", "formula": "C7H8", "molecular_weight": 92.14, "melting_point": null, "boiling_point": null, "flash_point": null, "density": null, "explosion_limit_lower": null, "explosion_limit_upper": null, "ignition_temperature": null, "vapor_pressure": null, "ghs_classification": [], "hazard_statements": [], "data_sources": ["PubChem"], "pubchem_cid": 1140, "synonyms": ["toluene", "methylbenzene", "108-88-3", "toluol", "Phenylmethane", "methacide", "Benzene, methyl-", "methylbenzol", "antisal 1a", "Toluen"]}', '2025-11-30 15:28:30.414659', 'https://pubchem.ncbi.nlm.nih.gov/compound/1140', 1.0, 1, '', 3.285625, NULL),(4, 'benzene', '71-43-2', 'pubchem', '{"name": "benzene", "cas_number": "71-43-2", "formula": "C6H6", "molecular_weight": 78.11, "melting_point": null, "boiling_point": null, "flash_point": null, "density": null, "explosion_limit_lower": null, "explosion_limit_upper": null, "ignition_temperature": null, "vapor_pressure": null, "ghs_classification": [], "hazard_statements": [], "data_sources": ["PubChem"], "pubchem_cid": 241, "synonyms": ["benzene", "benzol", "71-43-2", "Cyclohexatriene", "benzole", "Pyrobenzole", "Benzine", "Coal naphtha", "Pyrobenzol", "Benzen"]}', '2025-11-30 15:28:32.914166', 'https://pubchem.ncbi.nlm.nih.gov/compound/241', 1.0, 1, '', 2.492269, NULL);
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_temperature_class";
INSERT INTO "main"."expert_hub_temperature_class" ("id","code","max_surface_temp_celsius","min_ignition_temp_celsius","name_de","name_en","color_code","description","sort_order","is_active","created_at","updated_at") VALUES (1, 'T1', 450, 450, 'Temperaturklasse T1 (450°C)', 'Temperature Class T1 (450°C)', '#dc3545', 'Für Stoffe mit Zündtemperatur > 450°C', 10, 1, '2025-12-01 19:33:01.939488', '2025-12-01 20:45:16.683712'),(2, 'T2', 300, 300, 'Temperaturklasse T2 (300°C)', 'Temperature Class T2 (300°C)', '#fd7e14', 'Für Stoffe mit Zündtemperatur 300-450°C', 20, 1, '2025-12-01 19:33:01.948106', '2025-12-01 20:45:16.689283'),(3, 'T3', 200, 200, 'Temperaturklasse T3 (200°C)', 'Temperature Class T3 (200°C)', '#ffc107', 'Für Stoffe mit Zündtemperatur 200-300°C', 30, 1, '2025-12-01 19:33:01.955999', '2025-12-01 20:45:16.695359'),(4, 'T4', 135, 135, 'Temperaturklasse T4 (135°C)', 'Temperature Class T4 (135°C)', '#28a745', 'Für Stoffe mit Zündtemperatur 135-200°C', 40, 1, '2025-12-01 19:33:01.963301', '2025-12-01 20:45:16.701454'),(5, 'T5', 100, 100, 'Temperaturklasse T5 (100°C)', 'Temperature Class T5 (100°C)', '#17a2b8', 'Für Stoffe mit Zündtemperatur 100-135°C', 50, 1, '2025-12-01 19:33:01.972164', '2025-12-01 20:45:16.708517'),(6, 'T6', 85, 85, 'Temperaturklasse T6 (85°C)', 'Temperature Class T6 (85°C)', '#6610f2', 'Für Stoffe mit Zündtemperatur 85-100°C', 60, 1, '2025-12-01 19:33:01.980404', '2025-12-01 20:45:16.714578');
COMMIT;
BEGIN;
DELETE FROM "main"."expert_hub_zone_type";
INSERT INTO "main"."expert_hub_zone_type" ("id","code","name","zone_number","category","frequency","description","is_active","sort_order","created_at","updated_at") VALUES (1, 'ZONE_0', 'Zone 0', 0, '', '', 'Dauerhaft', 1, 1, '2025-11-27 12:29:49.394529', '2025-11-27 12:29:49.394529'),(2, 'ZONE_1', 'Zone 1', 1, '', '', 'Gelegentlich', 1, 2, '2025-11-27 12:29:49.408231', '2025-11-27 12:29:49.408231'),(3, 'ZONE_2', 'Zone 2', 2, '', '', 'Selten', 1, 3, '2025-11-27 12:29:49.420920', '2025-11-27 12:29:49.420920'),(4, 'ZONE_20', 'Zone 20', 20, '', '', 'Staub dauerhaft', 1, 4, '2025-11-27 12:29:49.432847', '2025-11-27 12:29:49.432847'),(5, 'ZONE_21', 'Zone 21', 21, '', '', 'Staub gelegentlich', 1, 5, '2025-11-27 12:29:49.444530', '2025-11-27 12:29:49.444530'),(6, 'ZONE_22', 'Zone 22', 22, '', '', 'Staub selten', 1, 6, '2025-11-27 12:29:49.455466', '2025-11-27 12:29:49.455466');
COMMIT;
BEGIN;
DELETE FROM "main"."field_definitions";
COMMIT;
BEGIN;
DELETE FROM "main"."field_groups";
COMMIT;
BEGIN;
DELETE FROM "main"."field_templates";
COMMIT;
BEGIN;
DELETE FROM "main"."field_value_history";
COMMIT;
BEGIN;
DELETE FROM "main"."genagent_actions";
COMMIT;
BEGIN;
DELETE FROM "main"."genagent_custom_domains";
COMMIT;
BEGIN;
DELETE FROM "main"."genagent_execution_logs";
COMMIT;
BEGIN;
DELETE FROM "main"."genagent_phases";
COMMIT;
BEGIN;
DELETE FROM "main"."generated_images";
COMMIT;
BEGIN;
DELETE FROM "main"."genres";
COMMIT;
BEGIN;
DELETE FROM "main"."graphql_field_usage";
COMMIT;
BEGIN;
DELETE FROM "main"."graphql_operations";
COMMIT;
BEGIN;
DELETE FROM "main"."graphql_performance_logs";
COMMIT;
BEGIN;
DELETE FROM "main"."handler_executions";
COMMIT;
BEGIN;
DELETE FROM "main"."ideas_v2";
COMMIT;
BEGIN;
DELETE FROM "main"."ideas_v2_books";
COMMIT;
BEGIN;
DELETE FROM "main"."illustration_styles";
COMMIT;
BEGIN;
DELETE FROM "main"."llm_prompt_executions";
COMMIT;
BEGIN;
DELETE FROM "main"."llm_prompt_templates";
COMMIT;
BEGIN;
DELETE FROM "main"."llms";
INSERT INTO "main"."llms" ("id","name","provider","llm_name","api_key","api_endpoint","max_tokens","temperature","top_p","frequency_penalty","presence_penalty","total_tokens_used","total_requests","total_cost","cost_per_1k_tokens","description","is_active","created_at","updated_at") VALUES (1, 'GPT-4 Turbo Preview', 'OpenAI', 'gpt-4-turbo-preview', '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', 'https://api.openai.com/v1', 128000, 0.7, 1.0, 0.0, 0.0, 0, 0, 0.0, 0.01, 'GPT-4 Turbo preview model', 1, '2025-11-11 09:13:03.678864', '2025-11-11 09:13:03.678864'),(2, 'GPT-4', 'OpenAI', 'gpt-4', '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', 'https://api.openai.com/v1', 8192, 0.7, 1.0, 0.0, 0.0, 0, 0, 0.0, 0.03, 'Standard GPT-4 model', 1, '2025-11-11 09:13:03.687597', '2025-11-11 09:13:03.687597'),(3, 'GPT-3.5 Turbo', 'OpenAI', 'gpt-3.5-turbo', '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', 'https://api.openai.com/v1', 16385, 0.7, 1.0, 0.0, 0.0, 0, 0, 0.0, 0.0005, 'Fast and inexpensive model for simple tasks', 1, '2025-11-11 09:13:03.696854', '2025-11-11 09:13:03.696854'),(4, 'Claude 3 Opus', 'Anthropic', 'claude-3-opus-20240229', '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', 'https://api.anthropic.com/v1/messages', 4096, 0.7, 1.0, 0.0, 0.0, 0, 0, 0.0, 0.045, 'Most powerful Claude model', 1, '2025-10-28 09:00:37.073770', '2025-10-28 09:00:37.073770'),(5, 'Claude 3 Sonnet', 'Anthropic', 'claude-3-sonnet-20240229', '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', 'https://api.anthropic.com/v1/messages', 4096, 0.7, 1.0, 0.0, 0.0, 0, 0, 0.0, 0.009, 'Balanced performance and cost', 1, '2025-10-28 09:00:37.080913', '2025-10-28 09:00:37.080913'),(6, 'GPT-4 Turbo', 'openai', 'gpt-4-turbo-preview', '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', 'https://api.openai.com/v1/chat/completions', 8000, 0.8, 1.0, 0.0, 0.0, 0, 0, 0.0, 0.02, '', 1, '2025-11-10 13:20:26.393927', '2025-11-11 07:50:19.481473'),(7, 'GPT-4o', 'OpenAI', 'gpt-4o', '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', 'https://api.openai.com/v1', 128000, 0.7, 1.0, 0.0, 0.0, 0, 0, 0.0, 0.01, 'Most advanced GPT-4 Omni model with vision and audio', 1, '2025-11-11 09:13:03.628469', '2025-11-11 09:13:03.628469'),(8, 'GPT-4o Mini', 'OpenAI', 'gpt-4o-mini', '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', 'https://api.openai.com/v1', 128000, 0.7, 1.0, 0.0, 0.0, 0, 0, 0.0, 0.0001, 'Affordable and intelligent small model for fast, lightweight tasks', 1, '2025-11-11 09:13:03.658011', '2025-11-11 09:13:03.658011'),(9, 'GPT-4 Turbo', 'OpenAI', 'gpt-4-turbo', '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', 'https://api.openai.com/v1', 128000, 0.7, 1.0, 0.0, 0.0, 0, 0, 0.0, 0.01, 'Latest GPT-4 Turbo with vision capabilities', 1, '2025-11-11 09:13:03.669770', '2025-11-11 09:13:03.669770'),(10, 'GPT-3.5 Turbo 16K', 'OpenAI', 'gpt-3.5-turbo-16k', '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', 'https://api.openai.com/v1', 16385, 0.7, 1.0, 0.0, 0.0, 0, 0, 0.0, 0.001, 'GPT-3.5 Turbo with 16K context', 1, '2025-11-11 09:13:03.706460', '2025-11-11 09:13:03.706460');
COMMIT;
BEGIN;
DELETE FROM "main"."locations";
COMMIT;
BEGIN;
DELETE FROM "main"."medtrans_customers";
COMMIT;
BEGIN;
DELETE FROM "main"."medtrans_presentation_texts";
COMMIT;
BEGIN;
DELETE FROM "main"."medtrans_presentations";
COMMIT;
BEGIN;
DELETE FROM "main"."navigation_items";
INSERT INTO "main"."navigation_items" ("id","section_id","code","name","description","item_type","url_name","url_params","external_url","icon","badge_text","badge_color","order","is_active","opens_in_new_tab","parent_id","created_at","updated_at") VALUES (1, 1, 'dashboard', 'Dashboard', 'Control Center Main Dashboard', 'link', 'control_center:dashboard', '"{}"', '', 'bi-speedometer2', '', 'primary', 10, 1, 0, NULL, '2025-11-13 15:23:27.159864', '2025-11-16 10:48:37.334476'),(2, 1, 'v2_migration', 'V2 Migration Status', 'Track V2 Architecture Migration Progress', 'link', 'control_center:dashboard', '"{}"', '', 'bi-speedometer2', 'LIVE', 'success', 20, 1, 0, NULL, '2025-11-13 15:23:27.169533', '2025-11-20 16:58:36.422458'),(3, 2, 'llms_v2', 'LLMs V2', 'Large Language Model Management', 'link', 'control_center:llms-v2-list', '{}', '', 'fas fa-brain', 'V2', 'primary', 10, 0, 0, NULL, '2025-11-13 15:23:27.179802', '2025-12-05 16:12:53.375796'),(4, 2, 'agents_v2', 'Agents V2', 'AI Agent Management and Configuration', 'link', 'control_center:agents-v2-list', '{}', '', 'fas fa-user-robot', 'V2', 'primary', 20, 0, 0, NULL, '2025-11-13 15:23:27.188953', '2025-12-05 16:12:53.384046'),(5, 2, 'templates_v2', 'Templates V2', 'Prompt Template Library and Editor', 'link', 'control_center:templates-v2-list', '{}', '', 'fas fa-file-code', 'V2', 'primary', 30, 0, 0, NULL, '2025-11-13 15:23:27.198164', '2025-12-05 16:12:53.398822'),(6, 2, 'agent_actions_v2', 'Agent Actions V2', 'Agent Action Management with Live Testing', 'link', 'control_center:agent-actions-list', '"{}"', '', 'bi-folder', 'V2', 'primary', 100, 0, 0, NULL, '2025-11-13 15:23:27.207907', '2025-12-05 16:12:53.406060'),(7, 2, 'workflow_v2', 'Workflow V2', 'Project Type and Phase Management', 'link', 'control_center:workflow-v2-dashboard', '"{}"', '', 'bi-speedometer2', 'V2', 'primary', 20, 0, 0, NULL, '2025-11-13 15:23:27.217498', '2025-12-05 16:12:53.392165'),(8, 4, 'domains', 'Domains', 'Domain and Project Management', 'link', 'control_center:domains-list', '"{}"', '', 'bi-speedometer2', '', 'primary', 30, 0, 0, NULL, '2025-11-13 15:23:27.227740', '2025-12-05 16:12:53.444434'),(9, 4, 'master_data', 'Master Data V2', 'Genres, Book Types, Audiences, Illustration Styles', 'link', 'control_center:master-data-dashboard', '{}', '', 'fas fa-table', 'V2', 'primary', 10, 0, 0, NULL, '2025-11-13 15:23:27.238577', '2025-12-05 16:12:53.422659'),(10, 4, 'navigation_admin', 'Navigation Dashboard', 'Dynamic Navigation Management', 'link', 'control_center:navigation-management-dashboard', '"{}"', '', 'bi-speedometer2', '', 'primary', 1, 0, 0, NULL, '2025-11-13 15:23:27.249713', '2025-12-05 16:12:53.414756'),(11, 1, 'navigation_builder', 'Navigation Builder', 'Visual Navigation Builder Tool', 'link', 'control_center:navigation-builder-dashboard', '"{}"', '', 'bi-speedometer2', 'BETA', 'warning', 30, 0, 0, NULL, '2025-11-13 15:23:27.260666', '2025-12-05 16:12:53.330030'),(12, 1, 'feature_planning', 'Feature Planning', 'Feature Development and Planning Tools', 'link', 'control_center:feature-planning-dashboard', '"{}"', '', 'bi-speedometer2', '', 'primary', 10, 0, 0, NULL, '2025-11-13 15:23:27.270652', '2025-11-16 10:16:05.998864'),(13, 1, 'handlers', 'Handlers', 'System Handler Management', 'link', 'control_center:handler-management-dashboard', '"{}"', '', 'bi-speedometer2', '', 'primary', 20, 0, 0, NULL, '2025-11-13 15:23:27.280768', '2025-12-05 16:12:53.323788'),(14, 5, 'sidebar_test', 'Sidebar Test', 'Sidebar Testing and Development', 'link', 'control_center:sidebar-test', '{}', '', 'fas fa-vial', 'DEV', 'secondary', 30, 0, 0, NULL, '2025-11-13 15:23:27.291551', '2025-11-15 08:48:49.681707'),(15, 4, 'navigation_sections', 'Navigation Sections', '', 'link', 'control_center:navigation-sections-list', '{}', '', 'fas fa-folder', '', 'primary', 25, 0, 0, NULL, '2025-11-13 18:36:03.788517', '2025-12-05 16:12:53.429990'),(16, 4, 'navigation_items', 'Navigation Items', '', 'link', 'control_center:navigation-items-list', '"{}"', '', 'bi-speedometer2', '', 'primary', 26, 0, 0, NULL, '2025-11-13 18:36:03.797641', '2025-12-05 16:12:53.437046'),(24, 10, 'wh_projects', 'Projects', 'All Writing Hub projects', 'link', 'writing_hub:book-projects-v2-list', '"{}"', '', 'bi-speedometer2', '', 'primary', 10, 1, 0, NULL, '2025-11-14 07:51:00.952172', '2025-11-16 09:19:26.868629'),(29, 10, 'wh_characters_global', 'All Characters', 'Global character list', 'link', 'writing_hub:character-v2-list', '"{}"', '', 'bi-speedometer2', '', 'primary', 60, 1, 0, NULL, '2025-11-14 07:51:00.996991', '2025-11-16 09:20:12.646391'),(30, 10, 'wh_worlds_global', 'All Worlds', 'Global world list', 'link', 'writing_hub:world-v2-list', '"{}"', '', 'bi-speedometer2', '', 'primary', 70, 1, 0, NULL, '2025-11-14 07:51:01.005304', '2025-11-16 09:20:23.979968'),(31, 10, 'wh_dashboard', 'neu: Hub Dashboard', 'Hub Dashboard', 'link', 'writing_hub:v2-dashboard', '{}', '', 'bi-speedometer2', '', 'primary', 10, 1, 0, NULL, '2025-11-15 08:01:31.661430', '2025-11-15 08:48:49.520135'),(34, 10, 'wh_chapters', 'All Chapters', 'View all chapters across projects', 'link', 'writing_hub:chapter-v2-global-list', '{}', '', 'bi-file-text', '', 'primary', 30, 1, 0, NULL, '2025-11-15 08:06:49.222754', '2025-11-15 08:48:49.541616'),(35, 10, 'wh_characters', 'Characters', 'Manage characters', 'link', 'writing_hub:character-v2-list', '"{}"', '', 'bi-people', '', 'primary', 40, 1, 0, NULL, '2025-11-15 08:06:49.231365', '2025-11-15 10:25:35.741641'),(36, 10, 'wh_worlds', 'Worlds', 'Manage story worlds', 'link', 'writing_hub:world-v2-list', '{}', '', 'bi-globe', '', 'primary', 50, 1, 0, NULL, '2025-11-15 08:06:49.238815', '2025-11-15 08:48:49.553268'),(37, 10, 'wh_projects_main', 'Projects', 'All Writing Hub projects', 'link', 'writing_hub:book-projects-v2-list', '{}', '', 'bi-collection', 'Main', 'primary', 20, 1, 0, NULL, '2025-11-15 08:41:43.002691', '2025-11-15 08:48:49.527258'),(39, 10, 'wh_character_create', 'New Character', '', 'link', 'writing_hub:character-v2-create', '{}', '', 'bi-person-plus', 'Create', 'success', 45, 1, 0, NULL, '2025-11-15 09:40:09.220052', '2025-11-15 09:40:09.220052'),(40, 10, 'wh_world_create', 'New World', '', 'link', 'writing_hub:world-v2-create', '{}', '', 'bi-globe-americas', 'Create', 'success', 55, 1, 0, NULL, '2025-11-15 09:40:09.228686', '2025-11-15 09:40:09.228686'),(41, 1, 'code_review', 'Code Review', '', 'link', 'control_center:code-review-dashboard', '"{}"', '', 'bi-speedometer2', '', 'primary', 50, 1, 0, NULL, '2025-11-16 10:03:59.902954', '2025-11-16 10:03:59.902954'),(42, 1, 'system_metrics', 'System Metrics', '', 'link', 'control_center:metrics', '"{}"', '', 'bi-speedometer2', '', 'primary', 100, 1, 0, NULL, '2025-11-16 10:40:59.171097', '2025-11-16 10:40:59.171097'),(43, 1, 'api_status', 'API-Status', '', 'link', 'control_center:api-status', '"{}"', '', 'bi-speedometer2', '', 'primary', 60, 1, 0, NULL, '2025-11-16 10:43:02.161416', '2025-11-16 10:49:28.716626'),(44, 1, 'model_consistency', 'Model Consistency', '', 'link', 'control_center:model-consistency', '"{}"', '', 'bi-speedometer2', '', 'primary', 70, 1, 0, NULL, '2025-11-16 10:44:49.017879', '2025-11-16 10:49:46.081733'),(45, 1, 'genagent', 'GenAgent', '', 'link', 'control_center:genagent-dashboard', '"{}"', '', 'bi-speedometer2', '', 'primary', 80, 1, 0, NULL, '2025-11-16 10:46:01.482314', '2025-11-16 10:50:01.624330'),(46, 1, 'genagent_ii', 'GenAgent II', '', 'link', 'genagent:dashboard', '"{}"', '', 'bi-speedometer2', '', 'primary', 0, 1, 0, NULL, '2025-11-16 11:46:54.796225', '2025-11-16 11:47:07.821369'),(47, 4, 'illustration_management', 'Illustration Management', '', 'link', 'illustration:gallery', '"{}"', '', 'bi-speedometer2', '', 'primary', 0, 1, 0, NULL, '2025-11-16 11:59:07.866888', '2025-11-16 16:27:40.365123'),(48, 12, '', 'Overview', '', 'link', '', '{}', '', 'bi bi-house', '', 'primary', 1, 1, 0, NULL, '2025-11-18 16:21:25.010410', '2025-11-18 16:21:25.010410'),(49, 12, 'ANALYTICS_OVERVIEW', 'Overview', '', 'link', '', '{}', '', 'bi bi-house', '', 'primary', 1, 1, 0, NULL, '2025-11-18 16:22:26.594009', '2025-11-18 16:22:26.594009'),(50, 12, 'ANALYTICS_REPORTS', 'Reports', '', 'link', '', '{}', '', 'bi bi-file-earmark-bar-graph', 'New', 'success', 2, 1, 0, NULL, '2025-11-18 16:22:26.602119', '2025-11-18 16:22:26.602119'),(51, 12, 'ANALYTICS_DATA_SOURCES', 'Data Sources', '', 'link', '', '{}', '', 'bi bi-database', '', 'primary', 3, 1, 0, NULL, '2025-11-18 16:22:26.611455', '2025-11-18 16:22:26.611455'),(52, 13, 'ANALYTICS_SETTINGS', 'Settings', '', 'link', '', '{}', '', 'bi bi-sliders', '', 'primary', 1, 1, 0, NULL, '2025-11-18 16:22:26.617530', '2025-11-18 16:22:26.617530'),(53, 1, 'handler_old', 'Handlers (old)', '', 'link', 'bfagent:handler-management-dashboard', '"{}"', '', 'bi-speedometer2', '', 'primary', 30, 1, 0, NULL, '2025-11-20 16:55:02.576271', '2025-11-20 16:55:56.882790'),(54, 1, 'plugins', 'Plugins', '', 'link', 'control_center:plugin-test-dashboard', '"{}"', '', 'bi-speedometer2', '', 'primary', 200, 0, 0, NULL, '2025-11-21 05:37:48.559878', '2025-12-05 16:12:53.360980'),(55, 2, 'workflow_agnostic', 'Workflow (agnostic)', '', 'link', 'control_center:workflow-list', '"{}"', '', 'bi-speedometer2', '', 'primary', 0, 0, 0, NULL, '2025-11-21 13:03:04.194887', '2025-12-05 16:12:53.368554'),(56, 4, 'data_sources_dashboard', 'Data Sources Dashboard', 'Manage external data sources for explosion protection', 'link', 'control_center:data-sources-dashboard', '"{}"', '', 'bi-speedometer2', '', 'primary', 50, 0, 0, NULL, '2025-11-30 22:29:38.186838', '2025-12-05 16:12:53.450507'),(57, 1, 'data_sources_import', 'Import Substance', 'Import substance data from PubChem and GESTIS', 'link', 'control_center:data-sources-import', '"{}"', '', 'bi-speedometer2', '', 'primary', 51, 0, 0, NULL, '2025-11-30 22:29:38.195623', '2025-12-05 16:12:53.337116'),(58, 1, 'data_sources_history', 'Import History', 'View all substance data imports', 'link', 'control_center:data-sources-import-history', '"{}"', '', 'bi-speedometer2', '', 'primary', 52, 0, 0, NULL, '2025-11-30 22:29:38.202820', '2025-12-05 16:12:53.344443'),(59, 1, 'data_sources_config', 'Data Source Configuration', 'Configure external data sources', 'link', 'control_center:data-sources-config', '"{}"', '', 'bi-speedometer2', '', 'primary', 53, 0, 0, NULL, '2025-11-30 22:29:38.210397', '2025-12-05 16:12:53.352026'),(62, 18, 'hazmat_enrichment', 'Hazmat Enrichment', 'Enrich hazmat catalog with external data', 'link', 'expert_hub:hazmat_enrichment', '"{}"', '', 'bi-speedometer2', '', 'primary', 21, 1, 0, NULL, '2025-11-30 22:29:38.254372', '2025-12-01 17:44:12.002111'),(63, 18, 'substance_search', 'Substance Search', 'Search imported substances', 'link', 'expert_hub:substance_search', '"{}"', '', 'bi-speedometer2', '', 'primary', 22, 1, 0, NULL, '2025-11-30 22:29:38.261949', '2025-12-01 17:43:16.952125'),(64, 17, 'main_home', 'Home', 'Main Dashboard', 'link', '', '{}', '/', 'house-door', '', 'primary', 1, 1, 0, NULL, '2025-12-01 08:05:52.327285', '2025-12-01 12:57:29.034429'),(65, 17, 'all_domains', 'All Domains', 'Overview of all available domains', 'link', '', '{}', '/domains/', 'grid-3x3-gap', '', 'primary', 2, 1, 0, NULL, '2025-12-01 08:05:52.337667', '2025-12-01 12:57:29.044615'),(66, 18, 'expert_hub_dashboard', 'Dashboard', 'Expert Hub Overview', 'link', '', '{}', '/expert-hub/', 'speedometer2', '', 'primary', 1, 1, 0, NULL, '2025-12-01 08:05:52.360127', '2025-12-01 12:57:29.064024'),(67, 18, 'expert_hub_documents', 'Documents', 'Explosionsschutz Documents', 'link', '', '{}', '/expert-hub/documents/', 'file-earmark-pdf', '', 'primary', 2, 1, 0, NULL, '2025-12-01 08:05:52.370128', '2025-12-01 12:57:29.072888'),(68, 18, 'expert_hub_assessments', 'Assessments', 'Risk Assessments', 'link', '', '{}', '/expert-hub/assessments/', 'clipboard-check', '', 'primary', 3, 1, 0, NULL, '2025-12-01 08:05:52.378827', '2025-12-01 12:57:29.081038'),(69, 18, 'expert_hub_data_sources', 'Data Sources', 'External Data Sources', 'link', '', '{}', '/control-center/data-sources/', 'database', 'New', 'success', 4, 1, 0, NULL, '2025-12-01 08:05:52.441295', '2025-12-01 12:57:29.090426'),(70, 19, 'writing_hub_dashboard', 'Dashboard', 'Writing Hub V2 Dashboard', 'link', '', '{}', '/writing-hub/v2/', 'speedometer2', '', 'primary', 1, 1, 0, NULL, '2025-12-01 08:05:52.461482', '2025-12-01 12:57:29.168281'),(71, 19, 'writing_hub_projects', 'Book Projects', 'Manage Book Projects', 'link', '', '{}', '/writing-hub/v2/book-projects/', 'book', '', 'primary', 2, 1, 0, NULL, '2025-12-01 08:05:52.472622', '2025-12-01 12:57:29.178459'),(72, 19, 'writing_hub_characters', 'Characters', 'Character Management', 'link', '', '{}', '/writing-hub/v2/characters/', 'people', '', 'primary', 3, 1, 0, NULL, '2025-12-01 08:05:52.483138', '2025-12-01 12:57:29.187079'),(73, 19, 'writing_hub_worlds', 'Worlds', 'World Building', 'link', '', '{}', '/writing-hub/v2/worlds/', 'globe', '', 'primary', 4, 1, 0, NULL, '2025-12-01 08:05:52.494484', '2025-12-01 12:57:29.194707'),(74, 20, 'genagent_dashboard', 'Dashboard', 'GenAgent Dashboard', 'link', '', '{}', '/genagent/', 'speedometer2', '', 'primary', 1, 1, 0, NULL, '2025-12-01 08:05:52.515408', '2025-12-01 12:57:29.213653'),(75, 20, 'genagent_workflows', 'Workflows', 'Workflow Management', 'link', '', '{}', '/genagent/workflows/', 'diagram-3', 'Coming Soon', 'secondary', 2, 1, 0, NULL, '2025-12-01 08:05:52.525676', '2025-12-01 12:57:29.223543'),(76, 20, 'genagent_handlers', 'Handlers', 'Handler Registry', 'link', '', '{}', '/genagent/handlers/', 'gear', 'Coming Soon', 'secondary', 3, 1, 0, NULL, '2025-12-01 08:05:52.536799', '2025-12-01 12:57:29.233736'),(78, 1, 'control_center_navigation', 'Navigation', 'Manage Navigation', 'link', 'control_center:navigation-api', '"{}"', '/control-center/navigation/', 'bi-speedometer2', '', 'primary', 2, 0, 0, NULL, '2025-12-01 08:05:52.577210', '2025-12-05 16:12:53.305356'),(79, 1, 'control_center_data_sources', 'Data Sources', 'External Data Sources', 'link', 'control_center:data-sources-config', '"{}"', '/control-center/data-sources/', 'bi-speedometer2', '', 'primary', 3, 0, 0, NULL, '2025-12-01 08:05:52.589658', '2025-12-05 16:12:53.314191'),(80, 1, 'control_center_customers', 'Customers', 'Customer Management', 'link', 'expert_hub:customer_dashboard', '"{}"', '/control-center/customers/', 'bi-speedometer2', 'Coming Soon', 'primary', 4, 1, 0, NULL, '2025-12-01 08:05:52.603019', '2025-12-01 10:24:07.694100'),(83, 23, 'illustration_dashboard', 'Gallery', 'Drag & Drop Image Gallery', 'link', '', '{}', '/illustrations/gallery/', 'images', '', 'primary', 1, 1, 0, NULL, '2025-12-01 08:14:20.160774', '2025-12-01 12:57:29.339173'),(84, 23, 'illustration_upload', 'Upload', 'Upload New Images', 'link', '', '{}', '/illustrations/upload/', 'cloud-upload', 'Coming Soon', 'secondary', 2, 1, 0, NULL, '2025-12-01 08:14:20.176071', '2025-12-01 08:30:39.804423'),(85, 23, 'illustration_generate', 'AI Generate', 'Generate with AI', 'link', '', '{}', '/illustrations/generate/', 'magic', 'Coming Soon', 'secondary', 2, 1, 0, NULL, '2025-12-01 08:14:20.189370', '2025-12-01 12:57:29.350585'),(86, 23, 'illustration_styles', 'Style Profiles', 'Manage Style Profiles', 'link', '', '{}', '/illustrations/styles/', 'palette-fill', '', 'primary', 3, 1, 0, NULL, '2025-12-01 08:31:13.400012', '2025-12-01 12:57:29.360237'),(90, 25, 'bfagent_dashboard', 'Dashboard', 'BFAgent Dashboard', 'link', '', '{}', '/bfagent/', 'speedometer2', 'Coming Soon', 'secondary', 1, 1, 0, NULL, '2025-12-01 10:46:44.952648', '2025-12-01 12:57:29.307947'),(91, 25, 'bfagent_agents', 'Agents', 'Agent Management', 'link', '', '{}', '/bfagent/agents/', 'person-workspace', 'Coming Soon', 'secondary', 2, 1, 0, NULL, '2025-12-01 10:46:44.964347', '2025-12-01 12:57:29.318359'),(92, 26, 'format_hub_dashboard', 'Dashboard', 'Format Hub Overview', 'link', '', '{}', '/format-hub/', 'speedometer2', '', 'primary', 1, 1, 0, NULL, '2025-12-01 10:46:45.021399', '2025-12-01 12:57:29.381698'),(93, 26, 'medtrans_presentations', 'Medical Translation', 'PPTX Translation with DeepL', 'link', '', '{}', '/medtrans/', 'translate', '', 'primary', 2, 1, 0, NULL, '2025-12-01 10:46:45.034251', '2025-12-01 12:57:29.392825'),(94, 26, 'pptx_studio', 'PPTX Studio', 'AI-Enhanced Presentations', 'link', '', '{}', '/pptx-studio/', 'stars', '', 'primary', 3, 1, 0, NULL, '2025-12-01 10:46:45.045645', '2025-12-01 12:57:29.403254'),(95, 27, 'dsgvo_dashboard', 'DSGVO-Dashboard', '', 'link', 'dsb:dashboard', '"{}"', '', 'bi-speedometer2', '', 'primary', 0, 1, 0, NULL, '2025-12-01 16:28:16.349799', '2025-12-01 16:28:16.349799'),(96, 28, 'suche', 'Suche', '', 'link', 'research_api:execute_research', '"{}"', '', 'bi-speedometer2', '', 'primary', 0, 1, 0, NULL, '2025-12-03 05:14:45.207550', '2025-12-03 05:14:45.207550'),(97, 28, 'hub_dashboard', 'Hub Dashboard', '', 'link', 'research_api:dashboard', '"{}"', '', 'bi-speedometer2', '', 'primary', 0, 1, 0, NULL, '2025-12-03 05:34:13.153731', '2025-12-03 05:34:13.153731'),(98, 29, 'hub_dashboard_research', 'Research Dashboard', 'Research Hub overview with stats and quick actions', 'link', 'research_api:dashboard', '{}', '', 'bi-speedometer2', 'Home', 'primary', 10, 1, 0, NULL, '2025-12-03 07:31:11.767159', '2025-12-03 07:31:11.767159'),(99, 29, 'hub_main_list_research_sessions', 'Research Sessions', 'List of all research sessions', 'link', 'research_api:session_list', '{}', '', 'bi-collection', 'Main', 'primary', 20, 1, 0, NULL, '2025-12-03 07:31:11.774514', '2025-12-03 07:31:11.774514'),(100, 29, 'research_create_session', 'New Research', 'Start a new research session', 'link', 'research_api:session_create', '{}', '', 'bi-plus-circle', 'Create', 'primary', 25, 1, 0, NULL, '2025-12-03 07:31:11.778089', '2025-12-03 07:31:11.778089'),(101, 29, 'research_domains_list', 'Research Domains', 'Available research domains (ExSchutz, etc.)', 'link', 'research_api:domain_list', '{}', '', 'bi-collection-fill', '', 'primary', 30, 1, 0, NULL, '2025-12-03 07:31:11.780650', '2025-12-03 07:31:11.780650'),(102, 29, 'research_exschutz', 'Explosionsschutz', 'Explosionsschutz research domain', 'link', 'research_api:exschutz_dashboard', '{}', '', 'bi-fire', 'ExSchutz', 'danger', 35, 1, 0, NULL, '2025-12-03 07:31:11.784223', '2025-12-03 07:31:11.784223'),(103, 29, 'research_sources_list', 'Research Sources', 'Data sources and scrapers', 'link', 'research_api:source_list', '{}', '', 'bi-book', '', 'primary', 40, 1, 0, NULL, '2025-12-03 07:31:11.787274', '2025-12-03 07:31:11.787274'),(104, 29, 'research_results_list', 'Research Results', 'Research findings and results', 'link', 'research_api:result_list', '{}', '', 'bi-graph-up', '', 'primary', 45, 1, 0, NULL, '2025-12-03 07:31:11.790310', '2025-12-03 07:31:11.790310'),(105, 29, 'research_api_docs', 'API Documentation', 'Research Framework API documentation', 'link', 'research_api:api_docs', '{}', '', 'bi-file-text', '', 'primary', 80, 1, 0, NULL, '2025-12-03 07:31:11.794440', '2025-12-03 07:31:11.794440'),(106, 29, 'research_settings', 'Research Settings', 'Research Hub configuration', 'link', 'research_api:settings', '{}', '', 'bi-gear', '', 'primary', 90, 1, 0, NULL, '2025-12-03 07:31:11.797473', '2025-12-03 07:31:11.797473');
COMMIT;
BEGIN;
DELETE FROM "main"."navigation_items_domains";
COMMIT;
BEGIN;
DELETE FROM "main"."navigation_items_required_groups";
COMMIT;
BEGIN;
DELETE FROM "main"."navigation_items_required_permissions";
COMMIT;
BEGIN;
DELETE FROM "main"."navigation_sections";
INSERT INTO "main"."navigation_sections" ("id","code","name","description","icon","color","order","is_active","is_collapsible","is_collapsed_default","created_at","updated_at","domain_id","slug") VALUES (1, 'control_center_dashboard', 'Control Center', 'Main Control Center Dashboard and Overview', 'fas fa-tachometer-alt', 'primary', 3, 1, 1, 0, '2025-11-13 15:23:27.113279', '2025-12-01 17:39:00.343649', 6, 'control_center_dashboard'),(2, 'control_center_ai_engine', 'AI ENGINE', 'LLMs, Agents, Templates, and AI Components', 'fas fa-robot', 'success', 20, 1, 1, 0, '2025-11-13 15:23:27.122483', '2025-11-13 15:23:27.122483', 6, 'control_center_ai_engine'),(3, 'control_center_workflow', 'WORKFLOW ENGINE', 'Workflow Management, Agent Actions, and Automation', 'fas fa-cogs', 'info', 30, 1, 1, 0, '2025-11-13 15:23:27.132773', '2025-11-13 15:23:27.132773', 6, 'control_center_workflow'),(4, 'control_center_data', 'DATA MANAGEMENT', 'Master Data, Navigation, and System Configuration', 'fas fa-database', 'warning', 40, 1, 1, 0, '2025-11-13 15:23:27.141375', '2025-11-13 15:23:27.141375', 6, 'control_center_data'),(5, 'control_center_system', 'SYSTEM ADMIN', 'System Administration and Advanced Features', 'fas fa-tools', 'danger', 50, 1, 1, 0, '2025-11-13 15:23:27.150124', '2025-11-13 15:23:27.150124', 6, 'control_center_system'),(9, 'control_center_coaching_hub', 'Coaching Hub', 'Applicationen rund ums Coaching ', 'bi-folder', 'info', 10, 1, 1, 0, '2025-11-14 12:37:43.627594', '2025-11-14 12:37:43.627594', 9, 'control_center_coaching_hub'),(10, 'wh_dashboard', 'Writing Hub', 'Dashboard für Writing', 'bi-pen', 'primary', 10, 0, 0, 0, '2025-11-15 07:59:14.653201', '2025-12-01 13:38:44.391152', 10, 'wh_dashboard'),(11, 'format_hub_powerpoint', 'Format-Hub', 'Übersetzungen für das Format pptx', 'bi-folder', 'primary', 0, 1, 1, 0, '2025-11-18 15:31:24.496150', '2025-12-01 10:26:44.180635', 8, NULL),(12, 'ANALYTICS-HUB_DASHBOARD', 'Dashboard', 'Analytics Hub dashboard and overview', 'bi bi-speedometer2', 'primary', 1, 0, 1, 0, '2025-11-18 16:17:37.258212', '2025-11-20 16:17:27.548121', 14, 'dashboard'),(13, 'ANALYTICS-HUB_MANAGEMENT', 'Management', 'Analytics Hub settings and configuration', 'bi bi-gear', 'primary', 2, 0, 1, 0, '2025-11-18 16:17:37.266053', '2025-11-20 16:17:21.672095', 14, 'management'),(14, 'not used', 'not used', '', '', 'primary', 200, 1, 1, 1, '2025-11-20 16:57:18.090232', '2025-11-20 16:57:18.090232', NULL, NULL),(15, 'CONTROL_CENTER', 'Control Center (inaktiv)', 'System management and configuration', 'gear-fill', 'primary', 1, 0, 1, 0, '2025-11-30 22:29:38.178603', '2025-12-01 17:38:47.857106', NULL, NULL),(17, 'main', 'Main', '', 'house', 'primary', 0, 1, 1, 0, '2025-12-01 08:04:14.378943', '2025-12-01 12:57:29.024745', NULL, 'main'),(18, 'expert_hub', 'Expert Hub', '', 'shield-check', 'primary', 1, 1, 1, 0, '2025-12-01 08:05:52.348342', '2025-12-01 12:57:29.054260', NULL, 'expert_hub'),(19, 'writing_hub', 'Writing Hub', '', 'pen', 'primary', 2, 1, 1, 0, '2025-12-01 08:05:52.451589', '2025-12-01 12:57:29.099052', NULL, 'writing_hub'),(20, 'genagent', 'GenAgent', '', 'cpu', 'primary', 3, 1, 1, 0, '2025-12-01 08:05:52.505098', '2025-12-01 12:57:29.204338', NULL, 'genagent'),(23, 'illustration_hub', 'Illustration Hub', '', 'palette', 'primary', 6, 1, 1, 0, '2025-12-01 08:14:20.147379', '2025-12-01 12:57:29.328545', NULL, 'illustration_hub'),(24, 'cad_hub', 'CAD-Hub', 'CAD Anwendungen', '', 'primary', 0, 1, 0, 0, '2025-12-01 10:15:44.465266', '2025-12-01 10:15:44.465266', NULL, NULL),(25, 'bfagent', 'BFAgent', '', 'robot', 'primary', 5, 0, 1, 0, '2025-12-01 10:46:44.939761', '2025-12-01 17:32:06.612995', NULL, 'bfagent'),(26, 'format_hub', 'Format Hub', '', 'file-earmark-slides', 'primary', 7, 1, 1, 0, '2025-12-01 10:46:45.012100', '2025-12-01 12:57:29.369852', NULL, 'format_hub'),(27, 'dsgvo_hub', 'DSGVO-Hub', 'Verwaltung von Mandanten im  Bezug auf DSGVO', '', 'primary', 0, 1, 1, 0, '2025-12-01 16:19:41.939295', '2025-12-01 16:19:41.939295', NULL, NULL),(28, 'research_hub', 'Research-Hub', 'Alle Aspekte von Recherche Mhm', '', 'primary', 0, 1, 1, 1, '2025-12-03 05:12:46.317848', '2025-12-03 05:12:46.317848', NULL, NULL),(29, 'RESEARCH', 'Research Hub', '', 'bi-search', 'primary', 10, 1, 1, 0, '2025-12-03 07:27:55.003493', '2025-12-03 07:27:55.003493', 13, NULL);
COMMIT;
BEGIN;
DELETE FROM "main"."navigation_sections_domains";
COMMIT;
BEGIN;
DELETE FROM "main"."navigation_sections_required_groups";
COMMIT;
BEGIN;
DELETE FROM "main"."navigation_sections_required_permissions";
COMMIT;
BEGIN;
DELETE FROM "main"."phase_action_configs";
COMMIT;
BEGIN;
DELETE FROM "main"."phase_agent_configs";
COMMIT;
BEGIN;
DELETE FROM "main"."presentation_studio_design_profile";
COMMIT;
BEGIN;
DELETE FROM "main"."presentation_studio_enhancement";
COMMIT;
BEGIN;
DELETE FROM "main"."presentation_studio_presentation";
COMMIT;
BEGIN;
DELETE FROM "main"."presentation_studio_preview_slide";
COMMIT;
BEGIN;
DELETE FROM "main"."presentation_studio_template_collection";
COMMIT;
BEGIN;
DELETE FROM "main"."project_field_values";
COMMIT;
BEGIN;
DELETE FROM "main"."project_phase_actions";
COMMIT;
BEGIN;
DELETE FROM "main"."project_phase_history";
COMMIT;
BEGIN;
DELETE FROM "main"."project_type_phases";
COMMIT;
BEGIN;
DELETE FROM "main"."project_types";
INSERT INTO "main"."project_types" ("id","domain_id","code","name","description","characteristics","typical_duration_days","complexity_level","industry_standards","common_deliverables","stakeholder_types","phase_generation_hints","is_active","created_by_id","created_at","updated_at","usage_count") VALUES (1, 1, 'novel', 'Novel', 'Full-length fictional narrative work', 'Character-driven, plot development, world-building, multiple chapters', 365, 'high', '{}', 'Manuscript, Character profiles, Plot outline, Chapter summaries', '{}', 'Focus on character development phases, plot milestones, revision cycles', 1, NULL, '2025-11-12 11:10:01', '2025-11-12 11:10:01', 0),(2, 1, 'short_story', 'Short Story', 'Brief fictional narrative work', 'Concise narrative, single plot line, limited characters', 30, 'moderate', '{}', 'Complete story, Character sketches, Plot summary', '{}', 'Emphasize concept development, writing, and polishing phases', 1, NULL, '2025-11-12 11:10:01', '2025-11-12 11:10:01', 0),(3, 1, 'poetry_collection', 'Poetry Collection', 'Curated collection of poems', 'Thematic coherence, varied forms, emotional depth', 180, 'moderate', '{}', 'Poem collection, Theme analysis, Publication format', '{}', 'Include inspiration gathering, writing, curation, and arrangement phases', 1, NULL, '2025-11-12 11:10:01', '2025-11-12 11:10:01', 0),(4, 2, 'clinical_trial', 'Clinical Trial Documentation', 'Translation of clinical trial protocols and reports', 'Regulatory compliance, medical terminology, precision required', 45, 'high', '{}', 'Translated protocols, Regulatory submissions, Quality reports', '{}', 'Include terminology research, medical review, regulatory compliance phases', 1, NULL, '2025-11-12 11:10:01', '2025-11-12 11:10:01', 0),(5, 2, 'patient_info', 'Patient Information', 'Translation of patient-facing medical documents', 'Patient accessibility, clear language, cultural sensitivity', 14, 'moderate', '{}', 'Patient leaflets, Consent forms, Instructions', '{}', 'Focus on clarity review, cultural adaptation, patient testing phases', 1, NULL, '2025-11-12 11:10:01', '2025-11-12 11:10:01', 0),(6, 3, 'workflow_agent', 'Workflow Agent', 'AI agent for workflow automation', 'Process automation, decision making, integration capabilities', 90, 'high', '{}', 'Agent code, Templates, Test cases, Documentation', '{}', 'Include requirements analysis, design, implementation, testing, deployment phases', 1, NULL, '2025-11-12 11:10:01', '2025-11-12 11:10:01', 0),(7, 3, 'content_agent', 'Content Generation Agent', 'AI agent for content creation', 'Natural language generation, template-based, quality control', 60, 'moderate', '{}', 'Agent implementation, Content templates, Quality metrics', '{}', 'Focus on template design, generation logic, quality validation phases', 1, NULL, '2025-11-12 11:10:01', '2025-11-12 11:10:01', 0);
COMMIT;
BEGIN;
DELETE FROM "main"."prompt_executions";
COMMIT;
BEGIN;
DELETE FROM "main"."prompt_template_tests";
COMMIT;
BEGIN;
DELETE FROM "main"."prompt_templates_legacy";
COMMIT;
BEGIN;
DELETE FROM "main"."research_citation_style_lookup";
INSERT INTO "main"."research_citation_style_lookup" ("id","code","name_de","name_en","description","sort_order","is_active","created_at","updated_at","format_template","example","use_footnotes","use_bibliography") VALUES (1, 'apa', 'APA 7', 'APA 7th Edition', 'American Psychological Association (7. Auflage)', 10, 1, '2025-12-02 15:57:42.230595', '2025-12-02 15:57:42.230595', '{author} ({year}). {title}. {source}.', 'Schmidt, M. (2023). Forschungsmethoden. Springer.', 0, 1),(2, 'mla', 'MLA 9', 'MLA 9th Edition', 'Modern Language Association (9. Auflage)', 20, 1, '2025-12-02 15:57:42.230595', '2025-12-02 15:57:42.230595', '{author}. "{title}." {source}, {year}.', 'Schmidt, Max. "Forschungsmethoden." Springer, 2023.', 0, 1),(3, 'chicago', 'Chicago', 'Chicago Manual of Style', 'Chicago Style mit Fußnoten', 30, 1, '2025-12-02 15:57:42.230595', '2025-12-02 15:57:42.230595', '{author}, {title} ({place}: {publisher}, {year}).', 'Schmidt, Max. Forschungsmethoden (Berlin: Springer, 2023).', 1, 1);
COMMIT;
BEGIN;
DELETE FROM "main"."research_depth_lookup";
INSERT INTO "main"."research_depth_lookup" ("id","code","name_de","name_en","description","sort_order","is_active","created_at","updated_at","max_sources","max_iterations","timeout_seconds","quality_threshold","enable_synthesis","enable_fact_check") VALUES (1, 'quick', 'Schnelle Recherche', 'Quick Research', 'Fast research with basic sources (1-3 iterations)', 10, 1, '2025-12-02 15:57:42.230595', '2025-12-03 07:39:18.168972', 5, 3, 120, 0.5, 1, 0),(2, 'standard', 'Standard Recherche', 'Standard Research', 'Balanced research with multiple sources (3-5 iterations)', 20, 1, '2025-12-02 15:57:42.230595', '2025-12-03 07:39:18.181938', 10, 5, 300, 0.7, 1, 0),(3, 'deep', 'Tiefenrecherche', 'Deep Research', 'Comprehensive research with extensive sources (5-10 iterations)', 30, 1, '2025-12-02 15:57:42.230595', '2025-12-03 07:39:18.193199', 20, 10, 600, 0.8, 1, 1),(4, 'comprehensive', 'Umfassend', 'Comprehensive', 'Umfassende Recherche mit 30+ Quellen, maximale Tiefe', 40, 1, '2025-12-02 15:57:42.230595', '2025-12-02 15:57:42.230595', 50, 5, 120, 0.9, 1, 1);
COMMIT;
BEGIN;
DELETE FROM "main"."research_focus_lookup";
INSERT INTO "main"."research_focus_lookup" ("id","code","name_de","name_en","description","sort_order","is_active","created_at","updated_at","domain","recommended_sources","required_fields") VALUES (1, 'general', 'Allgemein', 'General', 'Allgemeine Recherche ohne spezifischen Fokus', 10, 1, '2025-12-02 15:57:42.230595', '2025-12-02 15:57:42.230595', '', '["web", "academic"]', '[]'),(2, 'substance', 'Stoff', 'Substance', 'Stoffdaten-Recherche (ExSchutz)', 20, 1, '2025-12-02 15:57:42.230595', '2025-12-02 15:57:42.230595', 'exschutz', '["official", "academic"]', '["substance_name"]'),(3, 'zone', 'Zone', 'Zone Classification', 'Zoneneinteilung (ExSchutz)', 30, 1, '2025-12-02 15:57:42.230595', '2025-12-02 15:57:42.230595', 'exschutz', '["official", "academic"]', '["facility_type"]');
COMMIT;
BEGIN;
DELETE FROM "main"."research_handler_type_lookup";
INSERT INTO "main"."research_handler_type_lookup" ("id","code","name_de","name_en","description","sort_order","is_active","created_at","updated_at","handler_class","handler_version","is_async","requires_api_keys","default_timeout","cache_ttl_seconds") VALUES (1, 'web_search', 'Web-Suche', 'Web Search', 'Multi-Provider Web-Suche mit Ranking', 10, 1, '2025-12-02 15:57:42.230595', '2025-12-02 15:57:42.230595', 'apps.research.handlers.web_search_handler.WebSearchHandler', '2.0.0', 1, '["BRAVE_SEARCH_API_KEY"]', 30, 3600),(2, 'synthesis', 'Synthese', 'Synthesis', 'AI-gestützte Synthese aus mehreren Quellen', 20, 1, '2025-12-02 15:57:42.230595', '2025-12-02 15:57:42.230595', 'apps.research.handlers.synthesis_handler.SynthesisHandler', '2.0.0', 1, '["OPENAI_API_KEY"]', 60, 1800),(3, 'rag', 'RAG', 'RAG (Retrieval)', 'Retrieval Augmented Generation mit Vector DB', 30, 0, '2025-12-02 15:57:42.230595', '2025-12-02 15:57:42.230595', 'apps.research.handlers.rag_handler.RAGHandler', '2.0.0', 1, '["OPENAI_API_KEY", "PINECONE_API_KEY"]', 45, 7200);
COMMIT;
BEGIN;
DELETE FROM "main"."research_researchhandlerexecution";
COMMIT;
BEGIN;
DELETE FROM "main"."research_researchproject";
INSERT INTO "main"."research_researchproject" ("id","name","description","status","default_sources","knowledge_base_ids","created_at","updated_at","default_depth_id","owner_id") VALUES (1, 'Acetone', '', 'active', '[]', '[]', '2025-12-03 05:48:01.341413', '2025-12-03 05:48:01.341413', NULL, 2),(2, 'Acetone', '', 'active', '[]', '[]', '2025-12-03 06:03:16.551911', '2025-12-03 06:03:16.551911', NULL, 2),(3, 'Dynamit', '', 'active', '[]', '[]', '2025-12-03 11:52:21.865345', '2025-12-03 11:52:21.865345', NULL, 2),(4, 'Dynamit', '', 'active', '[]', '[]', '2025-12-03 12:14:38.713416', '2025-12-03 12:14:38.713416', NULL, 2),(5, 'Dynmit', '', 'active', '[]', '[]', '2025-12-03 12:27:04.918726', '2025-12-03 12:27:04.918726', NULL, 2);
COMMIT;
BEGIN;
DELETE FROM "main"."research_researchresult";
COMMIT;
BEGIN;
DELETE FROM "main"."research_researchsession";
INSERT INTO "main"."research_researchsession" ("id","query","optimized_query","sources","language","status","started_at","completed_at","execution_time_ms","iteration_count","max_iterations","quality_score","quality_threshold","error_message","created_at","updated_at","depth_id","project_id") VALUES (1, 'Was sind die Explosions Characteristica von Aceton', '', '[]', 'de', 'running', '2025-12-03 10:36:25.549610', NULL, NULL, 1, 3, NULL, 0.8, '', '2025-12-03 05:48:01.351878', '2025-12-03 10:36:25.549610', 2, 1),(2, 'Characteristics of Acetone', '', '[]', 'de', 'running', '2025-12-03 11:32:30.485555', NULL, NULL, 1, 3, NULL, 0.8, '', '2025-12-03 06:03:16.562604', '2025-12-03 11:32:30.487088', 2, 2),(3, 'Was sind die Characteristika von Dynamit ', '', '[]', 'de', 'running', '2025-12-03 11:52:30.853212', NULL, NULL, 1, 3, NULL, 0.8, '', '2025-12-03 11:52:21.873442', '2025-12-03 11:52:30.853212', 2, 3),(4, 'Chartakteristika von dynamit ', '', '[]', 'de', 'pending', NULL, NULL, NULL, 1, 3, NULL, 0.8, '', '2025-12-03 12:14:38.722808', '2025-12-03 12:14:38.722808', 2, 4),(5, 'Characteristika von Dynamit ', '', '[]', 'de', 'running', '2025-12-03 12:27:11.236373', NULL, NULL, 1, 3, NULL, 0.8, '', '2025-12-03 12:27:04.927894', '2025-12-03 12:27:04.929402', 2, 5);
COMMIT;
BEGIN;
DELETE FROM "main"."research_researchsource";
COMMIT;
BEGIN;
DELETE FROM "main"."research_source_type_lookup";
INSERT INTO "main"."research_source_type_lookup" ("id","code","name_de","name_en","description","sort_order","is_active","created_at","updated_at","provider_name","weight","credibility_boost","requires_api_key","api_key_setting","rate_limit_per_minute") VALUES (1, 'web', 'Web-Suche', 'Web Search', 'Allgemeine Web-Suche über Suchmaschinen', 10, 1, '2025-12-02 15:57:42.230595', '2025-12-02 15:57:42.230595', 'Brave Search', 1.0, 0.0, 1, 'BRAVE_SEARCH_API_KEY', 60),(2, 'academic', 'Wissenschaftliche Artikel', 'Academic Papers', 'Scholarly articles and research papers', 20, 1, '2025-12-02 15:57:42.230595', '2025-12-03 07:39:18.219467', 'Semantic Scholar', 1.5, 0.3, 0, '', 100),(3, 'news', 'Nachrichten', 'News', 'Aktuelle Nachrichten und Berichterstattung', 30, 1, '2025-12-02 15:57:42.230595', '2025-12-02 15:57:42.230595', 'Serper News', 0.8, 0.1, 1, 'SERPER_API_KEY', 60),(4, 'official', 'Amtlich', 'Official', 'Offizielle Quellen (GESTIS, EUR-Lex, BAuA, etc.)', 40, 1, '2025-12-02 15:57:42.230595', '2025-12-02 15:57:42.230595', 'Custom Scrapers', 2.0, 0.5, 0, '', 10),(5, 'internal', 'Intern (RAG)', 'Internal (RAG)', 'Interne Wissensdatenbank via RAG', 50, 0, '2025-12-02 15:57:42.230595', '2025-12-02 15:57:42.230595', 'Vector Database', 1.8, 0.4, 1, 'PINECONE_API_KEY', NULL),(6, 'web_search', 'Websuche', 'Web Search', 'General web search results (Brave, Google, Bing)', 10, 1, '2025-12-03 07:39:18.205364', '2025-12-03 07:39:18.205364', '', 1.0, 0.0, 0, '', NULL),(7, 'database', 'Datenbank', 'Database', 'Specialized databases (GESTIS, TRGS, etc.)', 30, 1, '2025-12-03 07:39:18.232961', '2025-12-03 07:39:18.232961', '', 1.0, 0.0, 0, '', NULL),(8, 'pdf_document', 'PDF-Dokument', 'PDF Document', 'Extracted content from PDF files', 40, 1, '2025-12-03 07:39:18.246292', '2025-12-03 07:39:18.246292', '', 1.0, 0.0, 0, '', NULL),(9, 'api', 'API-Quelle', 'API Source', 'Data from external APIs', 50, 1, '2025-12-03 07:39:18.260299', '2025-12-03 07:39:18.260299', '', 1.0, 0.0, 0, '', NULL),(10, 'scraper', 'Web-Scraper', 'Web Scraper', 'Custom web scraping results', 60, 1, '2025-12-03 07:39:18.274491', '2025-12-03 07:39:18.274491', '', 1.0, 0.0, 0, '', NULL);
COMMIT;
BEGIN;
DELETE FROM "main"."research_synthesis_type_lookup";
INSERT INTO "main"."research_synthesis_type_lookup" ("id","code","name_de","name_en","description","sort_order","is_active","created_at","updated_at","output_format","min_word_count","max_word_count","include_citations","include_contradictions","include_gaps","prompt_template_key") VALUES (1, 'balanced', 'Ausgewogen', 'Balanced', 'Ausgewogene Darstellung aller Perspektiven', 10, 1, '2025-12-02 15:57:42.230595', '2025-12-02 15:57:42.230595', 'markdown', 150, 800, 1, 0, 0, 'research_synthesis_balanced_v1'),(2, 'comparative', 'Vergleichend', 'Comparative', 'Vergleichende Analyse verschiedener Quellen', 20, 1, '2025-12-02 15:57:42.230595', '2025-12-02 15:57:42.230595', 'markdown', 200, 1000, 1, 1, 0, 'research_synthesis_comparative_v1'),(3, 'critical', 'Kritisch', 'Critical', 'Kritische Analyse mit Widersprüchen und Lücken', 30, 1, '2025-12-02 15:57:42.230595', '2025-12-02 15:57:42.230595', 'markdown', 250, 1500, 1, 1, 1, 'research_synthesis_critical_v1'),(4, 'summary', 'Zusammenfassung', 'Summary', 'Concise summary of findings', 10, 1, '2025-12-03 07:39:18.287546', '2025-12-03 07:39:18.287546', 'markdown', 100, 1000, 1, 0, 0, ''),(5, 'detailed_report', 'Detaillierter Bericht', 'Detailed Report', 'Comprehensive analysis with citations', 20, 1, '2025-12-03 07:39:18.301526', '2025-12-03 07:39:18.301526', 'markdown', 100, 1000, 1, 0, 0, ''),(6, 'comparison', 'Vergleich', 'Comparison', 'Comparative analysis of sources', 30, 1, '2025-12-03 07:39:18.313542', '2025-12-03 07:39:18.313542', 'markdown', 100, 1000, 1, 0, 0, '');
COMMIT;
BEGIN;
DELETE FROM "main"."sqlite_sequence";
INSERT INTO "main"."sqlite_sequence" ("name","seq") VALUES ('django_migrations', 44),('django_admin_log', 0),('django_content_type', 211),('domain_phases', 0),('agent_actions', 0),('agent_artifacts', 0),('writing_chapters', 0),('writing_characters', 0),('comic_panels', 0),('comic_dialogues', 0),('bfagent_component_change_log', 0),('bfagent_component_usage_log', 0),('content_blocks', 0),('bfagent_contextenrichmentlog', 0),('bfagent_contextsource', 0),('enrichment_responses', 0),('bfagent_feature_document', 0),('bfagent_feature_document_keyword', 0),('handler_executions', 0),('bfagent_generatedimage', 0),('bfagent_imagegenerationbatch', 0),('bfagent_imagestyleprofile', 0),('llm_prompt_executions', 0),('bfagent_migration_conflict', 0),('project_field_values', 0),('field_value_history', 0),('prompt_executions', 0),('prompt_templates_legacy', 0),('action_templates', 0),('prompt_template_tests', 0),('graphql_performance_logs', 0),('bfagent_reviewround', 0),('bfagent_reviewparticipant', 0),('bfagent_comment', 0),('bfagent_chapterrating', 0),('writing_story_arcs', 0),('writing_plot_points', 0),('writing_story_chapters', 0),('writing_generation_logs', 0),('writing_story_memories', 0),('template_fields', 0),('field_templates', 0),('bfagent_testexecution', 0),('bfagent_testcoveragereport', 0),('bfagent_requirementtestlink', 0),('bfagent_testscreenshot', 0),('bfagent_testlog', 0),('bfagent_testbug', 0),('tool_executions', 0),('project_type_phases', 0),('project_phase_actions', 0),('phase_agent_configs', 0),('phase_action_configs', 0),('book_type_phases', 0),('project_phase_history', 0),('workflow_templates', 0),('workflow_phase_steps', 0),('writing_worlds', 0),('world_settings', 0),('world_rules', 0),('locations', 0),('book_characters_v2', 0),('workflow_domains', 4),('core_customers', 1),('expert_hub_assessments', 1),('auth_group', 3),('auth_permission', 1448),('auth_user', 6),('auth_user_groups', 4),('auth_user_user_permissions', 452),('checklist_templates', 4),('domain_arts', 16),('domain_types', 12),('navigation_items', 106),('navigation_sections', 29),('project_types', 14),('llms', 10),('checklist_items', 53),('expert_hub_document_type', 5),('expert_hub_processing_status_type', 9),('expert_hub_zone_type', 6),('workflow_templates_v2', 1),('workflow_system_workflow', 4),('workflow_system_checkpoint', 12),('core_prompt_templates', 13),('expert_hub_substance_data_import', 4),('expert_hub_exschutzdocument', 1),('domain_sections', 2),('compliance_risk_level', 5),('compliance_status', 6),('compliance_priority', 4),('compliance_incident_severity', 4),('dsb_rechtsform', 7),('dsb_branche', 7),('dsb_rechtsgrundlage', 4),('dsb_datenkategorie', 6),('dsb_vorfall_typ', 7),('dsb_mandant', 8),('dsb_tom_kategorie', 8),('dsb_tom_massnahme', 120),('dsb_mandant_tom', 358),('expert_hub_explosion_group', 6),('expert_hub_temperature_class', 6),('expert_hub_equipment_category', 6),('expert_hub_ignition_protection_type', 9),('expert_hub_physical_state', 6),('expert_hub_regulation_type', 8),('expert_hub_regulation', 8),('cad_drawing_type', 10),('cad_analysis_category', 9),('cad_compliance_standard', 9),('cad_severity_level', 5),('cad_building_type', 6),('cad_layer_standard', 3),('research_depth_lookup', 4),('research_source_type_lookup', 10),('research_citation_style_lookup', 3),('research_synthesis_type_lookup', 6),('research_handler_type_lookup', 3),('research_focus_lookup', 3),('research_researchproject', 5),('research_researchsession', 5),('domain_arts_copy1', 16);
COMMIT;
BEGIN;
DELETE FROM "main"."story_bibles";
COMMIT;
BEGIN;
DELETE FROM "main"."target_audiences";
COMMIT;
BEGIN;
DELETE FROM "main"."template_fields";
COMMIT;
BEGIN;
DELETE FROM "main"."tool_definitions";
COMMIT;
BEGIN;
DELETE FROM "main"."tool_executions";
COMMIT;
BEGIN;
DELETE FROM "main"."user_navigation_preferences";
COMMIT;
BEGIN;
DELETE FROM "main"."workflow_domains";
INSERT INTO "main"."workflow_domains" ("id","code","name","description","characteristics","typical_phases","icon","color","is_active","created_at","updated_at","project_count","created_by_id") VALUES (1, 'writing_hub', 'Book Writing', 'Creative writing domain for novels, stories, and literary works with iterative development processes.', 'Creative process, iterative development, character-driven narratives, plot development, world-building, editing cycles', 'Concept Development, Character Creation, Plot Outline, First Draft, Revision Cycles, Beta Reading, Final Edit, Publishing Preparation', 'bi-book', 'primary', 1, '2025-11-12 11:09:17', '2025-11-12 11:09:17', 0, NULL),(2, 'medtrans', 'Medical Translation', 'Specialized translation services requiring medical expertise and regulatory compliance.', 'Medical terminology, regulatory compliance, quality assurance, specialized expertise, confidentiality requirements', 'Document Analysis, Terminology Research, Translation, Medical Review, Quality Control, Regulatory Check, Final Delivery', 'bi-heart-pulse', 'danger', 1, '2025-11-12 11:09:17', '2025-11-12 11:09:17', 0, NULL),(3, 'genagent', 'AI Agent Development', 'Development and management of AI agents, workflows, and automation systems.', 'AI development, workflow automation, agent orchestration, template management, testing and validation', 'Requirements Analysis, Agent Design, Template Creation, Testing, Deployment, Monitoring, Optimization', 'bi-robot', 'success', 1, '2025-11-12 11:09:17', '2025-11-12 11:09:17', 0, NULL),(4, 'control_hub', 'System Administration', 'Central control and administration of all system components and configurations.', 'System management, configuration control, user administration, monitoring, maintenance', 'Planning, Configuration, Implementation, Testing, Deployment, Monitoring, Maintenance', 'bi-gear-wide-connected', 'info', 1, '2025-11-12 11:09:17', '2025-11-12 11:09:17', 0, NULL);
COMMIT;
BEGIN;
DELETE FROM "main"."workflow_phase_steps";
COMMIT;
BEGIN;
DELETE FROM "main"."workflow_phases";
COMMIT;
BEGIN;
DELETE FROM "main"."workflow_system_checkpoint";
INSERT INTO "main"."workflow_system_checkpoint" ("id","phase_name","phase_order","action_name","action_order","handler_class","handler_plugin_id","config","status","output","error","estimated_duration_seconds","actual_duration_seconds","started_at","completed_at","retry_count","max_retries","is_required","continue_on_error","description","created_at","updated_at","workflow_id") VALUES (1, 'pre_writing', 1, 'create_characters', 1, 'apps.writing_hub.handlers.CharacterHandler', '', '{}', 'completed', '{"success": true, "output": {"characters": [{"id": 1, "name": "Character 1", "role": "protagonist", "description": "A fantasy character with unique traits", "backstory": "Born in a fantasy world..."}, {"id": 2, "name": "Character 2", "role": "supporting", "description": "A fantasy character with unique traits", "backstory": "Born in a fantasy world..."}, {"id": 3, "name": "Character 3", "role": "supporting", "description": "A fantasy character with unique traits", "backstory": "Born in a fantasy world..."}], "character_count": 3, "genre": "fantasy"}, "error": null, "metadata": {"handler": "CharacterHandler", "checkpoint": "create_characters", "phase": "pre_writing"}}', '', 7200, 0, NULL, NULL, 0, 3, 1, 0, 'Create main characters', '2025-11-27 12:58:26.757360', '2025-11-27 12:58:26.758870', 1),(2, 'pre_writing', 1, 'outline_plot', 2, 'apps.writing_hub.handlers.OutlineHandler', '', '{}', 'completed', '{"success": true, "output": {"outline": {"title": "My Fantasy Novel", "acts": [{"act_number": 1, "name": "Act 1", "description": "Setup - Introduce characters and world", "scenes": [{"scene_number": 1, "title": "Scene 1", "description": "Key scene in Act 1"}, {"scene_number": 2, "title": "Scene 2", "description": "Key scene in Act 1"}, {"scene_number": 3, "title": "Scene 3", "description": "Key scene in Act 1"}, {"scene_number": 4, "title": "Scene 4", "description": "Key scene in Act 1"}, {"scene_number": 5, "title": "Scene 5", "description": "Key scene in Act 1"}]}, {"act_number": 2, "name": "Act 2", "description": "Confrontation - Build conflict and tension", "scenes": [{"scene_number": 1, "title": "Scene 1", "description": "Key scene in Act 2"}, {"scene_number": 2, "title": "Scene 2", "description": "Key scene in Act 2"}, {"scene_number": 3, "title": "Scene 3", "description": "Key scene in Act 2"}, {"scene_number": 4, "title": "Scene 4", "description": "Key scene in Act 2"}, {"scene_number": 5, "title": "Scene 5", "description": "Key scene in Act 2"}, {"scene_number": 6, "title": "Scene 6", "description": "Key scene in Act 2"}, {"scene_number": 7, "title": "Scene 7", "description": "Key scene in Act 2"}]}, {"act_number": 3, "name": "Act 3", "description": "Resolution - Climax and conclusion", "scenes": [{"scene_number": 1, "title": "Scene 1", "description": "Key scene in Act 3"}, {"scene_number": 2, "title": "Scene 2", "description": "Key scene in Act 3"}, {"scene_number": 3, "title": "Scene 3", "description": "Key scene in Act 3"}, {"scene_number": 4, "title": "Scene 4", "description": "Key scene in Act 3"}, {"scene_number": 5, "title": "Scene 5", "description": "Key scene in Act 3"}]}], "total_scenes": 17, "character_count": 3}, "act_count": 3}, "error": null, "metadata": {"handler": "OutlineHandler", "checkpoint": "outline_plot", "phase": "pre_writing"}}', '', 14400, 0, NULL, NULL, 0, 3, 1, 0, 'Create plot outline', '2025-11-27 12:58:26.770203', '2025-11-27 12:58:26.770203', 1),(3, 'writing', 2, 'write_chapters', 1, 'apps.writing_hub.handlers.ChapterWriter', '', '{}', 'completed', '{"success": true, "output": {"chapters": [{"chapter_number": 1, "title": "Chapter 1: The Journey Begins", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 1. Characters face new challenges..."}, {"chapter_number": 2, "title": "Chapter 2", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 2. Characters face new challenges..."}, {"chapter_number": 3, "title": "Chapter 3", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 3. Characters face new challenges..."}, {"chapter_number": 4, "title": "Chapter 4", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 4. Characters face new challenges..."}, {"chapter_number": 5, "title": "Chapter 5", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 5. Characters face new challenges..."}, {"chapter_number": 6, "title": "Chapter 6", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 6. Characters face new challenges..."}, {"chapter_number": 7, "title": "Chapter 7", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 7. Characters face new challenges..."}, {"chapter_number": 8, "title": "Chapter 8", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 8. Characters face new challenges..."}, {"chapter_number": 9, "title": "Chapter 9", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 9. Characters face new challenges..."}, {"chapter_number": 10, "title": "Chapter 10", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 10. Characters face new challenges..."}], "chapter_count": 10, "total_words": 25000}, "error": null, "metadata": {"handler": "ChapterWriter", "checkpoint": "write_chapters", "phase": "writing"}}', '', 720000, 0, NULL, NULL, 0, 3, 1, 0, 'Write all chapters', '2025-11-27 12:58:26.780981', '2025-11-27 12:58:26.780981', 1),(4, 'editing', 3, 'edit_content', 1, 'apps.writing_hub.handlers.EditorHandler', '', '{}', 'completed', '{"success": true, "output": {"editing_stats": {"chapters_edited": 10, "grammar_fixes": 42, "style_improvements": 28, "consistency_checks": 15, "readability_score": 8.5}, "suggestions": [{"chapter": 1, "type": "pacing", "suggestion": "Consider slowing down the opening scene"}, {"chapter": 3, "type": "character", "suggestion": "Develop secondary character motivation"}, {"chapter": 5, "type": "dialogue", "suggestion": "Dialogue could be more natural"}], "status": "edited"}, "error": null, "metadata": {"handler": "EditorHandler", "checkpoint": "edit_content", "phase": "editing"}}', '', 288000, 0, NULL, NULL, 0, 3, 1, 0, 'Edit all chapters', '2025-11-27 12:58:26.792297', '2025-11-27 12:58:26.792297', 1),(5, 'pre_writing', 1, 'create_characters', 0, 'apps.writing_hub.handlers.CharacterHandler', '', '{}', 'completed', '{"success": true, "output": {"characters": [{"id": 1, "name": "Character 1", "role": "protagonist", "description": "A fantasy character with unique traits", "backstory": "Born in a fantasy world..."}, {"id": 2, "name": "Character 2", "role": "supporting", "description": "A fantasy character with unique traits", "backstory": "Born in a fantasy world..."}, {"id": 3, "name": "Character 3", "role": "supporting", "description": "A fantasy character with unique traits", "backstory": "Born in a fantasy world..."}], "character_count": 3, "genre": "fantasy"}, "error": null, "metadata": {"handler": "CharacterHandler", "checkpoint": "create_characters", "phase": "pre_writing"}}', '', 7200, 0, NULL, NULL, 0, 3, 1, 0, 'Create main characters', '2025-11-27 12:58:26.803118', '2025-11-27 12:58:26.803118', 3),(6, 'pre_writing', 1, 'outline_plot', 1, 'apps.writing_hub.handlers.OutlineHandler', '', '{}', 'completed', '{"success": true, "output": {"outline": {"title": "a new hostile world", "acts": [{"act_number": 1, "name": "Act 1", "description": "Setup - Introduce characters and world", "scenes": [{"scene_number": 1, "title": "Scene 1", "description": "Key scene in Act 1"}, {"scene_number": 2, "title": "Scene 2", "description": "Key scene in Act 1"}, {"scene_number": 3, "title": "Scene 3", "description": "Key scene in Act 1"}, {"scene_number": 4, "title": "Scene 4", "description": "Key scene in Act 1"}, {"scene_number": 5, "title": "Scene 5", "description": "Key scene in Act 1"}]}, {"act_number": 2, "name": "Act 2", "description": "Confrontation - Build conflict and tension", "scenes": [{"scene_number": 1, "title": "Scene 1", "description": "Key scene in Act 2"}, {"scene_number": 2, "title": "Scene 2", "description": "Key scene in Act 2"}, {"scene_number": 3, "title": "Scene 3", "description": "Key scene in Act 2"}, {"scene_number": 4, "title": "Scene 4", "description": "Key scene in Act 2"}, {"scene_number": 5, "title": "Scene 5", "description": "Key scene in Act 2"}, {"scene_number": 6, "title": "Scene 6", "description": "Key scene in Act 2"}, {"scene_number": 7, "title": "Scene 7", "description": "Key scene in Act 2"}]}, {"act_number": 3, "name": "Act 3", "description": "Resolution - Climax and conclusion", "scenes": [{"scene_number": 1, "title": "Scene 1", "description": "Key scene in Act 3"}, {"scene_number": 2, "title": "Scene 2", "description": "Key scene in Act 3"}, {"scene_number": 3, "title": "Scene 3", "description": "Key scene in Act 3"}, {"scene_number": 4, "title": "Scene 4", "description": "Key scene in Act 3"}, {"scene_number": 5, "title": "Scene 5", "description": "Key scene in Act 3"}]}], "total_scenes": 17, "character_count": 3}, "act_count": 3}, "error": null, "metadata": {"handler": "OutlineHandler", "checkpoint": "outline_plot", "phase": "pre_writing"}}', '', 14400, 0, NULL, NULL, 0, 3, 1, 0, 'Create plot outline', '2025-11-27 12:58:26.814731', '2025-11-27 12:58:26.814731', 3),(7, 'writing', 2, 'write_chapters', 0, 'apps.writing_hub.handlers.ChapterWriter', '', '{}', 'completed', '{"success": true, "output": {"chapters": [{"chapter_number": 1, "title": "Chapter 1: The Journey Begins", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 1. Characters face new challenges..."}, {"chapter_number": 2, "title": "Chapter 2", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 2. Characters face new challenges..."}, {"chapter_number": 3, "title": "Chapter 3", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 3. Characters face new challenges..."}, {"chapter_number": 4, "title": "Chapter 4", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 4. Characters face new challenges..."}, {"chapter_number": 5, "title": "Chapter 5", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 5. Characters face new challenges..."}, {"chapter_number": 6, "title": "Chapter 6", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 6. Characters face new challenges..."}, {"chapter_number": 7, "title": "Chapter 7", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 7. Characters face new challenges..."}, {"chapter_number": 8, "title": "Chapter 8", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 8. Characters face new challenges..."}, {"chapter_number": 9, "title": "Chapter 9", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 9. Characters face new challenges..."}, {"chapter_number": 10, "title": "Chapter 10", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 10. Characters face new challenges..."}], "chapter_count": 10, "total_words": 25000}, "error": null, "metadata": {"handler": "ChapterWriter", "checkpoint": "write_chapters", "phase": "writing"}}', '', 720000, 0, NULL, NULL, 0, 3, 1, 0, 'Write all chapters', '2025-11-27 12:58:26.826142', '2025-11-27 12:58:26.826142', 3),(8, 'editing', 3, 'edit_content', 0, 'apps.writing_hub.handlers.EditorHandler', '', '{}', 'completed', '{"success": true, "output": {"editing_stats": {"chapters_edited": 10, "grammar_fixes": 42, "style_improvements": 28, "consistency_checks": 15, "readability_score": 8.5}, "suggestions": [{"chapter": 1, "type": "pacing", "suggestion": "Consider slowing down the opening scene"}, {"chapter": 3, "type": "character", "suggestion": "Develop secondary character motivation"}, {"chapter": 5, "type": "dialogue", "suggestion": "Dialogue could be more natural"}], "status": "edited"}, "error": null, "metadata": {"handler": "EditorHandler", "checkpoint": "edit_content", "phase": "editing"}}', '', 288000, 0, NULL, NULL, 0, 3, 1, 0, 'Edit all chapters', '2025-11-27 12:58:26.836317', '2025-11-27 12:58:26.836317', 3),(9, 'pre_writing', 1, 'create_characters', 1, 'apps.writing_hub.handlers.CharacterHandler', '', '{}', 'completed', '{"success": true, "output": {"characters": [{"id": 23, "name": "Character 1", "role": "protagonist", "personality": "Protagonist personality - driven, complex character", "background": "A fantasy character with unique traits and compelling backstory", "backstory": "Born in a fantasy world filled with adventure and mystery..."}, {"id": 24, "name": "Character 2", "role": "antagonist", "personality": "Antagonist personality - driven, complex character", "background": "A fantasy character with unique traits and compelling backstory", "backstory": "Born in a fantasy world filled with adventure and mystery..."}, {"id": 25, "name": "Character 3", "role": "supporting", "personality": "Supporting personality - driven, complex character", "background": "A fantasy character with unique traits and compelling backstory", "backstory": "Born in a fantasy world filled with adventure and mystery..."}], "character_count": 3, "character_ids": [23, 24, 25], "genre": "fantasy"}, "error": null, "metadata": {"handler": "CharacterHandler", "checkpoint": "create_characters", "phase": "pre_writing", "db_objects_created": 3}}', '', 7200, 0, NULL, NULL, 0, 3, 1, 0, 'Create main characters', '2025-11-27 12:58:26.847940', '2025-11-27 12:58:26.847940', 4),(10, 'pre_writing', 1, 'outline_plot', 2, 'apps.writing_hub.handlers.OutlineHandler', '', '{}', 'completed', '{"success": true, "output": {"outline": {"title": "My Fantasy Novel", "acts": [{"act_number": 1, "name": "Act 1", "description": "Setup - Introduce characters and world", "scenes": [{"scene_number": 1, "title": "Scene 1", "description": "Key scene in Act 1"}, {"scene_number": 2, "title": "Scene 2", "description": "Key scene in Act 1"}, {"scene_number": 3, "title": "Scene 3", "description": "Key scene in Act 1"}, {"scene_number": 4, "title": "Scene 4", "description": "Key scene in Act 1"}, {"scene_number": 5, "title": "Scene 5", "description": "Key scene in Act 1"}]}, {"act_number": 2, "name": "Act 2", "description": "Confrontation - Build conflict and tension", "scenes": [{"scene_number": 1, "title": "Scene 1", "description": "Key scene in Act 2"}, {"scene_number": 2, "title": "Scene 2", "description": "Key scene in Act 2"}, {"scene_number": 3, "title": "Scene 3", "description": "Key scene in Act 2"}, {"scene_number": 4, "title": "Scene 4", "description": "Key scene in Act 2"}, {"scene_number": 5, "title": "Scene 5", "description": "Key scene in Act 2"}, {"scene_number": 6, "title": "Scene 6", "description": "Key scene in Act 2"}, {"scene_number": 7, "title": "Scene 7", "description": "Key scene in Act 2"}]}, {"act_number": 3, "name": "Act 3", "description": "Resolution - Climax and conclusion", "scenes": [{"scene_number": 1, "title": "Scene 1", "description": "Key scene in Act 3"}, {"scene_number": 2, "title": "Scene 2", "description": "Key scene in Act 3"}, {"scene_number": 3, "title": "Scene 3", "description": "Key scene in Act 3"}, {"scene_number": 4, "title": "Scene 4", "description": "Key scene in Act 3"}, {"scene_number": 5, "title": "Scene 5", "description": "Key scene in Act 3"}]}], "total_scenes": 17, "character_count": 3}, "act_count": 3}, "error": null, "metadata": {"handler": "OutlineHandler", "checkpoint": "outline_plot", "phase": "pre_writing"}}', '', 14400, 0, NULL, NULL, 0, 3, 1, 0, 'Create plot outline', '2025-11-27 12:58:26.857696', '2025-11-27 12:58:26.857696', 4),(11, 'writing', 2, 'write_chapters', 1, 'apps.writing_hub.handlers.ChapterWriter', '', '{}', 'failed', NULL, 'no such table: main.book_projects_v2_backup_20251117_123611', 720000, 0, NULL, NULL, 0, 3, 1, 0, 'Write all chapters', '2025-11-27 12:58:26.868817', '2025-11-27 12:58:26.868817', 4),(12, 'editing', 3, 'edit_content', 1, 'apps.writing_hub.handlers.EditorHandler', '', '{}', 'pending', NULL, '', 288000, 0, NULL, NULL, 0, 3, 1, 0, 'Edit all chapters', '2025-11-27 12:58:26.879640', '2025-11-27 12:58:26.880152', 4);
COMMIT;
BEGIN;
DELETE FROM "main"."workflow_system_workflow";
INSERT INTO "main"."workflow_system_workflow" ("id","uuid","context","title","description","tags","status","total_checkpoints","completed_checkpoints","failed_checkpoints","created_at","updated_at","started_at","completed_at","created_by_id","domain_id","template_id") VALUES (1, '155264defe0d4dfb9e1771bd4f3acb85', '{"characters": [{"id": 1, "name": "Character 1", "role": "protagonist", "description": "A fantasy character with unique traits", "backstory": "Born in a fantasy world..."}, {"id": 2, "name": "Character 2", "role": "supporting", "description": "A fantasy character with unique traits", "backstory": "Born in a fantasy world..."}, {"id": 3, "name": "Character 3", "role": "supporting", "description": "A fantasy character with unique traits", "backstory": "Born in a fantasy world..."}], "character_count": 3, "genre": "fantasy", "outline": {"title": "My Fantasy Novel", "acts": [{"act_number": 1, "name": "Act 1", "description": "Setup - Introduce characters and world", "scenes": [{"scene_number": 1, "title": "Scene 1", "description": "Key scene in Act 1"}, {"scene_number": 2, "title": "Scene 2", "description": "Key scene in Act 1"}, {"scene_number": 3, "title": "Scene 3", "description": "Key scene in Act 1"}, {"scene_number": 4, "title": "Scene 4", "description": "Key scene in Act 1"}, {"scene_number": 5, "title": "Scene 5", "description": "Key scene in Act 1"}]}, {"act_number": 2, "name": "Act 2", "description": "Confrontation - Build conflict and tension", "scenes": [{"scene_number": 1, "title": "Scene 1", "description": "Key scene in Act 2"}, {"scene_number": 2, "title": "Scene 2", "description": "Key scene in Act 2"}, {"scene_number": 3, "title": "Scene 3", "description": "Key scene in Act 2"}, {"scene_number": 4, "title": "Scene 4", "description": "Key scene in Act 2"}, {"scene_number": 5, "title": "Scene 5", "description": "Key scene in Act 2"}, {"scene_number": 6, "title": "Scene 6", "description": "Key scene in Act 2"}, {"scene_number": 7, "title": "Scene 7", "description": "Key scene in Act 2"}]}, {"act_number": 3, "name": "Act 3", "description": "Resolution - Climax and conclusion", "scenes": [{"scene_number": 1, "title": "Scene 1", "description": "Key scene in Act 3"}, {"scene_number": 2, "title": "Scene 2", "description": "Key scene in Act 3"}, {"scene_number": 3, "title": "Scene 3", "description": "Key scene in Act 3"}, {"scene_number": 4, "title": "Scene 4", "description": "Key scene in Act 3"}, {"scene_number": 5, "title": "Scene 5", "description": "Key scene in Act 3"}]}], "total_scenes": 17, "character_count": 3}, "act_count": 3, "chapters": [{"chapter_number": 1, "title": "Chapter 1: The Journey Begins", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 1. Characters face new challenges..."}, {"chapter_number": 2, "title": "Chapter 2", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 2. Characters face new challenges..."}, {"chapter_number": 3, "title": "Chapter 3", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 3. Characters face new challenges..."}, {"chapter_number": 4, "title": "Chapter 4", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 4. Characters face new challenges..."}, {"chapter_number": 5, "title": "Chapter 5", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 5. Characters face new challenges..."}, {"chapter_number": 6, "title": "Chapter 6", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 6. Characters face new challenges..."}, {"chapter_number": 7, "title": "Chapter 7", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 7. Characters face new challenges..."}, {"chapter_number": 8, "title": "Chapter 8", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 8. Characters face new challenges..."}, {"chapter_number": 9, "title": "Chapter 9", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 9. Characters face new challenges..."}, {"chapter_number": 10, "title": "Chapter 10", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 10. Characters face new challenges..."}], "chapter_count": 10, "total_words": 25000, "editing_stats": {"chapters_edited": 10, "grammar_fixes": 42, "style_improvements": 28, "consistency_checks": 15, "readability_score": 8.5}, "suggestions": [{"chapter": 1, "type": "pacing", "suggestion": "Consider slowing down the opening scene"}, {"chapter": 3, "type": "character", "suggestion": "Develop secondary character motivation"}, {"chapter": 5, "type": "dialogue", "suggestion": "Dialogue could be more natural"}], "status": "edited"}', 'My Fantasy Novel', 'A fantasy novel about dragons and magic', '[]', 'completed', 4, 4, 0, '2025-11-27 12:57:53.118359', '2025-11-27 12:57:53.118359', NULL, NULL, 1, 1, 1),(2, '95fbbf3cd0154ca4b99c41a98f9bac88', '{"book_id": 123, "genre": "scifi", "target_words": 5000}', 'Intergalactic Lover ', '2 Geschöpfe aus unterschiedlichen Galaxien lernen sich kennen und lieben.', '["scifi"]', 'completed', 0, 0, 0, '2025-11-27 12:57:53.132937', '2025-11-27 12:57:53.132937', NULL, NULL, 1, 1, NULL),(3, '2369b85ff0ec497689d2656ed0d9fdf0', '{"book_id": 123, "genre": "fantasy", "target_words": 20000, "characters": [{"id": 1, "name": "Character 1", "role": "protagonist", "description": "A fantasy character with unique traits", "backstory": "Born in a fantasy world..."}, {"id": 2, "name": "Character 2", "role": "supporting", "description": "A fantasy character with unique traits", "backstory": "Born in a fantasy world..."}, {"id": 3, "name": "Character 3", "role": "supporting", "description": "A fantasy character with unique traits", "backstory": "Born in a fantasy world..."}], "character_count": 3, "outline": {"title": "a new hostile world", "acts": [{"act_number": 1, "name": "Act 1", "description": "Setup - Introduce characters and world", "scenes": [{"scene_number": 1, "title": "Scene 1", "description": "Key scene in Act 1"}, {"scene_number": 2, "title": "Scene 2", "description": "Key scene in Act 1"}, {"scene_number": 3, "title": "Scene 3", "description": "Key scene in Act 1"}, {"scene_number": 4, "title": "Scene 4", "description": "Key scene in Act 1"}, {"scene_number": 5, "title": "Scene 5", "description": "Key scene in Act 1"}]}, {"act_number": 2, "name": "Act 2", "description": "Confrontation - Build conflict and tension", "scenes": [{"scene_number": 1, "title": "Scene 1", "description": "Key scene in Act 2"}, {"scene_number": 2, "title": "Scene 2", "description": "Key scene in Act 2"}, {"scene_number": 3, "title": "Scene 3", "description": "Key scene in Act 2"}, {"scene_number": 4, "title": "Scene 4", "description": "Key scene in Act 2"}, {"scene_number": 5, "title": "Scene 5", "description": "Key scene in Act 2"}, {"scene_number": 6, "title": "Scene 6", "description": "Key scene in Act 2"}, {"scene_number": 7, "title": "Scene 7", "description": "Key scene in Act 2"}]}, {"act_number": 3, "name": "Act 3", "description": "Resolution - Climax and conclusion", "scenes": [{"scene_number": 1, "title": "Scene 1", "description": "Key scene in Act 3"}, {"scene_number": 2, "title": "Scene 2", "description": "Key scene in Act 3"}, {"scene_number": 3, "title": "Scene 3", "description": "Key scene in Act 3"}, {"scene_number": 4, "title": "Scene 4", "description": "Key scene in Act 3"}, {"scene_number": 5, "title": "Scene 5", "description": "Key scene in Act 3"}]}], "total_scenes": 17, "character_count": 3}, "act_count": 3, "chapters": [{"chapter_number": 1, "title": "Chapter 1: The Journey Begins", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 1. Characters face new challenges..."}, {"chapter_number": 2, "title": "Chapter 2", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 2. Characters face new challenges..."}, {"chapter_number": 3, "title": "Chapter 3", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 3. Characters face new challenges..."}, {"chapter_number": 4, "title": "Chapter 4", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 4. Characters face new challenges..."}, {"chapter_number": 5, "title": "Chapter 5", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 5. Characters face new challenges..."}, {"chapter_number": 6, "title": "Chapter 6", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 6. Characters face new challenges..."}, {"chapter_number": 7, "title": "Chapter 7", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 7. Characters face new challenges..."}, {"chapter_number": 8, "title": "Chapter 8", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 8. Characters face new challenges..."}, {"chapter_number": 9, "title": "Chapter 9", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 9. Characters face new challenges..."}, {"chapter_number": 10, "title": "Chapter 10", "word_count": 2500, "status": "draft", "content_preview": "The story continues in chapter 10. Characters face new challenges..."}], "chapter_count": 10, "total_words": 25000, "editing_stats": {"chapters_edited": 10, "grammar_fixes": 42, "style_improvements": 28, "consistency_checks": 15, "readability_score": 8.5}, "suggestions": [{"chapter": 1, "type": "pacing", "suggestion": "Consider slowing down the opening scene"}, {"chapter": 3, "type": "character", "suggestion": "Develop secondary character motivation"}, {"chapter": 5, "type": "dialogue", "suggestion": "Dialogue could be more natural"}], "status": "edited"}', 'a new hostile world', 'In einer feindlichen Welt müssen sich außerirdische zurecht finden', '["scifi"]', 'completed', 4, 4, 0, '2025-11-27 12:57:53.143209', '2025-11-27 12:57:53.143209', NULL, NULL, 1, 1, 1),(4, '9a1bc852069d48419c36c8204d8f0215', '{"characters": [{"id": 23, "name": "Character 1", "role": "protagonist", "personality": "Protagonist personality - driven, complex character", "background": "A fantasy character with unique traits and compelling backstory", "backstory": "Born in a fantasy world filled with adventure and mystery..."}, {"id": 24, "name": "Character 2", "role": "antagonist", "personality": "Antagonist personality - driven, complex character", "background": "A fantasy character with unique traits and compelling backstory", "backstory": "Born in a fantasy world filled with adventure and mystery..."}, {"id": 25, "name": "Character 3", "role": "supporting", "personality": "Supporting personality - driven, complex character", "background": "A fantasy character with unique traits and compelling backstory", "backstory": "Born in a fantasy world filled with adventure and mystery..."}], "character_count": 3, "character_ids": [23, 24, 25], "genre": "fantasy", "outline": {"title": "My Fantasy Novel", "acts": [{"act_number": 1, "name": "Act 1", "description": "Setup - Introduce characters and world", "scenes": [{"scene_number": 1, "title": "Scene 1", "description": "Key scene in Act 1"}, {"scene_number": 2, "title": "Scene 2", "description": "Key scene in Act 1"}, {"scene_number": 3, "title": "Scene 3", "description": "Key scene in Act 1"}, {"scene_number": 4, "title": "Scene 4", "description": "Key scene in Act 1"}, {"scene_number": 5, "title": "Scene 5", "description": "Key scene in Act 1"}]}, {"act_number": 2, "name": "Act 2", "description": "Confrontation - Build conflict and tension", "scenes": [{"scene_number": 1, "title": "Scene 1", "description": "Key scene in Act 2"}, {"scene_number": 2, "title": "Scene 2", "description": "Key scene in Act 2"}, {"scene_number": 3, "title": "Scene 3", "description": "Key scene in Act 2"}, {"scene_number": 4, "title": "Scene 4", "description": "Key scene in Act 2"}, {"scene_number": 5, "title": "Scene 5", "description": "Key scene in Act 2"}, {"scene_number": 6, "title": "Scene 6", "description": "Key scene in Act 2"}, {"scene_number": 7, "title": "Scene 7", "description": "Key scene in Act 2"}]}, {"act_number": 3, "name": "Act 3", "description": "Resolution - Climax and conclusion", "scenes": [{"scene_number": 1, "title": "Scene 1", "description": "Key scene in Act 3"}, {"scene_number": 2, "title": "Scene 2", "description": "Key scene in Act 3"}, {"scene_number": 3, "title": "Scene 3", "description": "Key scene in Act 3"}, {"scene_number": 4, "title": "Scene 4", "description": "Key scene in Act 3"}, {"scene_number": 5, "title": "Scene 5", "description": "Key scene in Act 3"}]}], "total_scenes": 17, "character_count": 3}, "act_count": 3, "failure_reason": "Critical checkpoint failed: no such table: main.book_projects_v2_backup_20251117_123611"}', 'My Fantasy Novel', 'A fantasy novel about dragons and magic', '[]', 'failed', 4, 2, 1, '2025-11-27 12:57:53.155013', '2025-11-27 12:57:53.155013', NULL, NULL, 1, 1, 1);
COMMIT;
BEGIN;
DELETE FROM "main"."workflow_templates";
COMMIT;
BEGIN;
DELETE FROM "main"."workflow_templates_v2";
INSERT INTO "main"."workflow_templates_v2" ("id","name","description","phases_json","is_default","created_at","updated_at","usage_count","created_by_id","project_type_id") VALUES (1, 'Novel Writing Workflow', 'Standard workflow for novel writing projects', '[{"name": "pre_writing", "order": 1, "description": "Prepare for writing", "estimated_days": 7, "required": true, "actions": [{"name": "create_characters", "description": "Create main characters", "handler_class": "apps.writing_hub.handlers.CharacterHandler", "order": 1, "estimated_hours": 2, "required": true}, {"name": "outline_plot", "description": "Create plot outline", "handler_class": "apps.writing_hub.handlers.OutlineHandler", "order": 2, "estimated_hours": 4, "required": true}]}, {"name": "writing", "order": 2, "description": "Write chapters", "estimated_days": 90, "required": true, "actions": [{"name": "write_chapters", "description": "Write all chapters", "handler_class": "apps.writing_hub.handlers.ChapterWriter", "order": 1, "estimated_hours": 200, "required": true}]}, {"name": "editing", "order": 3, "description": "Edit and refine", "estimated_days": 30, "required": true, "actions": [{"name": "edit_content", "description": "Edit all chapters", "handler_class": "apps.writing_hub.handlers.EditorHandler", "order": 1, "estimated_hours": 80, "required": true}]}]', 1, '2025-11-27 12:57:53.107251', '2025-11-27 12:57:53.107251', 0, NULL, 1);
COMMIT;
BEGIN;
DELETE FROM "main"."world_rules";
COMMIT;
BEGIN;
DELETE FROM "main"."world_settings";
COMMIT;
BEGIN;
DELETE FROM "main"."worlds_v2";
COMMIT;
BEGIN;
DELETE FROM "main"."worlds_v2_books";
COMMIT;
BEGIN;
DELETE FROM "main"."writing_book_projects";
COMMIT;
BEGIN;
DELETE FROM "main"."writing_chapters";
COMMIT;
BEGIN;
DELETE FROM "main"."writing_chapters_featured_characters";
COMMIT;
BEGIN;
DELETE FROM "main"."writing_chapters_plot_points";
COMMIT;
BEGIN;
DELETE FROM "main"."writing_characters";
COMMIT;
BEGIN;
DELETE FROM "main"."writing_generation_logs";
COMMIT;
BEGIN;
DELETE FROM "main"."writing_plot_points";
COMMIT;
BEGIN;
DELETE FROM "main"."writing_plot_points_involved_characters";
COMMIT;
BEGIN;
DELETE FROM "main"."writing_statuses";
COMMIT;
BEGIN;
DELETE FROM "main"."writing_story_arcs";
COMMIT;
BEGIN;
DELETE FROM "main"."writing_story_chapters";
COMMIT;
BEGIN;
DELETE FROM "main"."writing_story_memories";
COMMIT;
BEGIN;
DELETE FROM "main"."writing_story_memories_characters_involved";
COMMIT;
BEGIN;
DELETE FROM "main"."writing_story_projects";
COMMIT;
BEGIN;
DELETE FROM "main"."writing_story_strands";
COMMIT;
BEGIN;
DELETE FROM "main"."writing_story_strands_converges_with";
COMMIT;
BEGIN;
DELETE FROM "main"."writing_story_strands_secondary_characters";
COMMIT;
BEGIN;
DELETE FROM "main"."writing_worlds";
COMMIT;
CREATE INDEX "main"."action_templates_action_id_5232ed93"
ON "action_templates" (
  "action_id" ASC
);
CREATE UNIQUE INDEX "main"."action_templates_action_id_template_id_91d6e7a8_uniq"
ON "action_templates" (
  "action_id" ASC,
  "template_id" ASC
);
CREATE INDEX "main"."action_templates_template_id_7f6ae4ec"
ON "action_templates" (
  "template_id" ASC
);
CREATE INDEX "main"."action_time_idx"
ON "expert_hub_auditlog" (
  "action" ASC,
  "timestamp" ASC
);
CREATE INDEX "main"."agent_actions_agent_id_92fee259"
ON "agent_actions" (
  "agent_id" ASC
);
CREATE UNIQUE INDEX "main"."agent_actions_agent_id_name_c367db78_uniq"
ON "agent_actions" (
  "agent_id" ASC,
  "name" ASC
);
CREATE INDEX "main"."agent_actions_prompt_template_id_aeafc531"
ON "agent_actions" (
  "prompt_template_id" ASC
);
CREATE INDEX "main"."agent_artifacts_agent_id_713e1c14"
ON "agent_artifacts" (
  "agent_id" ASC
);
CREATE INDEX "main"."agent_artifacts_project_id_7c499dac"
ON "agent_artifacts" (
  "project_id" ASC
);
CREATE INDEX "main"."agents_agent_t_e12830_idx"
ON "agents" (
  "agent_type" ASC,
  "status" ASC
);
CREATE INDEX "main"."agents_llm_model_id_ddbf10fa"
ON "agents" (
  "llm_model_id" ASC
);
CREATE INDEX "main"."ai_verify_idx"
ON "expert_hub_auditlog" (
  "is_ai_generated" ASC,
  "human_verified" ASC
);
CREATE INDEX "main"."auth_group_permissions_group_id_b120cbf9"
ON "auth_group_permissions" (
  "group_id" ASC
);
CREATE UNIQUE INDEX "main"."auth_group_permissions_group_id_permission_id_0cd325b0_uniq"
ON "auth_group_permissions" (
  "group_id" ASC,
  "permission_id" ASC
);
CREATE INDEX "main"."auth_group_permissions_permission_id_84c5c92e"
ON "auth_group_permissions" (
  "permission_id" ASC
);
CREATE INDEX "main"."auth_permission_content_type_id_2f476e4b"
ON "auth_permission" (
  "content_type_id" ASC
);
CREATE UNIQUE INDEX "main"."auth_permission_content_type_id_codename_01ab375a_uniq"
ON "auth_permission" (
  "content_type_id" ASC,
  "codename" ASC
);
CREATE INDEX "main"."auth_user_groups_group_id_97559544"
ON "auth_user_groups" (
  "group_id" ASC
);
CREATE INDEX "main"."auth_user_groups_user_id_6a12ed8b"
ON "auth_user_groups" (
  "user_id" ASC
);
CREATE UNIQUE INDEX "main"."auth_user_groups_user_id_group_id_94350c0c_uniq"
ON "auth_user_groups" (
  "user_id" ASC,
  "group_id" ASC
);
CREATE INDEX "main"."auth_user_user_permissions_permission_id_1fbb5f2c"
ON "auth_user_user_permissions" (
  "permission_id" ASC
);
CREATE INDEX "main"."auth_user_user_permissions_user_id_a95ead1b"
ON "auth_user_user_permissions" (
  "user_id" ASC
);
CREATE UNIQUE INDEX "main"."auth_user_user_permissions_user_id_permission_id_14a6b632_uniq"
ON "auth_user_user_permissions" (
  "user_id" ASC,
  "permission_id" ASC
);
CREATE INDEX "main"."bfagent_bug_require_5a83e6_idx"
ON "bfagent_bugfixplan" (
  "requirement_id" ASC,
  "status" ASC
);
CREATE INDEX "main"."bfagent_bug_status_7e5e87_idx"
ON "bfagent_bugfixplan" (
  "status" ASC
);
CREATE INDEX "main"."bfagent_bugfixplan_approved_by_id_5eb56692"
ON "bfagent_bugfixplan" (
  "approved_by_id" ASC
);
CREATE INDEX "main"."bfagent_bugfixplan_created_by_id_666948dc"
ON "bfagent_bugfixplan" (
  "created_by_id" ASC
);
CREATE INDEX "main"."bfagent_bugfixplan_requirement_id_9d513cb7"
ON "bfagent_bugfixplan" (
  "requirement_id" ASC
);
CREATE INDEX "main"."bfagent_chapterrating_chapter_id_9391c66d"
ON "bfagent_chapterrating" (
  "chapter_id" ASC
);
CREATE INDEX "main"."bfagent_chapterrating_review_round_id_7116774c"
ON "bfagent_chapterrating" (
  "review_round_id" ASC
);
CREATE UNIQUE INDEX "main"."bfagent_chapterrating_review_round_id_chapter_id_reviewer_id_0de22118_uniq"
ON "bfagent_chapterrating" (
  "review_round_id" ASC,
  "chapter_id" ASC,
  "reviewer_id" ASC
);
CREATE INDEX "main"."bfagent_chapterrating_reviewer_id_4012b6c3"
ON "bfagent_chapterrating" (
  "reviewer_id" ASC
);
CREATE INDEX "main"."bfagent_com_compone_8f6335_idx"
ON "bfagent_component_usage_log" (
  "component_id" ASC,
  "timestamp" DESC
);
CREATE INDEX "main"."bfagent_com_compone_a01c39_idx"
ON "bfagent_component_registry" (
  "component_type" ASC,
  "domain" ASC
);
CREATE INDEX "main"."bfagent_com_status_35fe57_idx"
ON "bfagent_component_registry" (
  "status" ASC,
  "component_type" ASC
);
CREATE INDEX "main"."bfagent_com_timesta_35d4b9_idx"
ON "bfagent_component_usage_log" (
  "timestamp" DESC
);
CREATE INDEX "main"."bfagent_com_usage_c_ffd1b9_idx"
ON "bfagent_component_registry" (
  "usage_count" DESC
);
CREATE INDEX "main"."bfagent_comment_author_id_4d7eb98f"
ON "bfagent_comment" (
  "author_id" ASC
);
CREATE INDEX "main"."bfagent_comment_chapter_id_9cc74b14"
ON "bfagent_comment" (
  "chapter_id" ASC
);
CREATE INDEX "main"."bfagent_comment_resolved_by_id_0638d2e6"
ON "bfagent_comment" (
  "resolved_by_id" ASC
);
CREATE INDEX "main"."bfagent_comment_review_round_id_98c57f6a"
ON "bfagent_comment" (
  "review_round_id" ASC
);
CREATE INDEX "main"."bfagent_component_change_log_component_id_76666e40"
ON "bfagent_component_change_log" (
  "component_id" ASC
);
CREATE INDEX "main"."bfagent_component_change_log_timestamp_6c70da2b"
ON "bfagent_component_change_log" (
  "timestamp" ASC
);
CREATE INDEX "main"."bfagent_component_registry_component_type_d334347f"
ON "bfagent_component_registry" (
  "component_type" ASC
);
CREATE INDEX "main"."bfagent_component_registry_domain_73f123cc"
ON "bfagent_component_registry" (
  "domain" ASC
);
CREATE INDEX "main"."bfagent_component_registry_name_f064aae3"
ON "bfagent_component_registry" (
  "name" ASC
);
CREATE INDEX "main"."bfagent_component_registry_owner_id_0cc26f3c"
ON "bfagent_component_registry" (
  "owner_id" ASC
);
CREATE INDEX "main"."bfagent_component_registry_status_eacd60f9"
ON "bfagent_component_registry" (
  "status" ASC
);
CREATE INDEX "main"."bfagent_component_usage_log_component_id_0a4c0e8b"
ON "bfagent_component_usage_log" (
  "component_id" ASC
);
CREATE INDEX "main"."bfagent_component_usage_log_timestamp_a5b8bd1e"
ON "bfagent_component_usage_log" (
  "timestamp" ASC
);
CREATE INDEX "main"."bfagent_con_created_ba0748_idx"
ON "bfagent_contextenrichmentlog" (
  "created_at" DESC
);
CREATE INDEX "main"."bfagent_con_schema__f2c90d_idx"
ON "bfagent_contextenrichmentlog" (
  "schema_id" ASC,
  "created_at" DESC
);
CREATE INDEX "main"."bfagent_contextenrichmentlog_schema_id_d41f79be"
ON "bfagent_contextenrichmentlog" (
  "schema_id" ASC
);
CREATE INDEX "main"."bfagent_contextsource_schema_id_ffe95205"
ON "bfagent_contextsource" (
  "schema_id" ASC
);
CREATE UNIQUE INDEX "main"."bfagent_contextsource_schema_id_order_d5a8d79c_uniq"
ON "bfagent_contextsource" (
  "schema_id" ASC,
  "order" ASC
);
CREATE INDEX "main"."bfagent_fea_feature_2131f3_idx"
ON "bfagent_feature_document" (
  "feature_id" ASC,
  "document_type" ASC
);
CREATE INDEX "main"."bfagent_fea_is_auto_6d6741_idx"
ON "bfagent_feature_document" (
  "is_auto_discovered" ASC
);
CREATE INDEX "main"."bfagent_fea_keyword_6e4aca_idx"
ON "bfagent_feature_document_keyword" (
  "keyword" ASC,
  "keyword_type" ASC
);
CREATE INDEX "main"."bfagent_feature_document_feature_id_764d60e3"
ON "bfagent_feature_document" (
  "feature_id" ASC
);
CREATE UNIQUE INDEX "main"."bfagent_feature_document_feature_id_file_path_7a71841b_uniq"
ON "bfagent_feature_document" (
  "feature_id" ASC,
  "file_path" ASC
);
CREATE INDEX "main"."bfagent_feature_document_keyword_feature_id_594884e3"
ON "bfagent_feature_document_keyword" (
  "feature_id" ASC
);
CREATE UNIQUE INDEX "main"."bfagent_feature_document_keyword_feature_id_keyword_c3d8bea1_uniq"
ON "bfagent_feature_document_keyword" (
  "feature_id" ASC,
  "keyword" ASC
);
CREATE INDEX "main"."bfagent_feature_document_keyword_keyword_6b834cab"
ON "bfagent_feature_document_keyword" (
  "keyword" ASC
);
CREATE INDEX "main"."bfagent_gen_created_d5bb0b_idx"
ON "bfagent_generatedimage" (
  "created_at" ASC
);
CREATE INDEX "main"."bfagent_gen_image_t_c825fc_idx"
ON "bfagent_generatedimage" (
  "image_type" ASC,
  "status" ASC
);
CREATE INDEX "main"."bfagent_gen_project_972aef_idx"
ON "bfagent_generatedimage" (
  "project_id" ASC,
  "status" ASC
);
CREATE INDEX "main"."bfagent_generatedimage_approved_by_id_7ee6c7ee"
ON "bfagent_generatedimage" (
  "approved_by_id" ASC
);
CREATE INDEX "main"."bfagent_generatedimage_chapter_id_6b78bd59"
ON "bfagent_generatedimage" (
  "chapter_id" ASC
);
CREATE INDEX "main"."bfagent_generatedimage_project_id_37a7c95b"
ON "bfagent_generatedimage" (
  "project_id" ASC
);
CREATE INDEX "main"."bfagent_generatedimage_style_profile_id_feb24cb7"
ON "bfagent_generatedimage" (
  "style_profile_id" ASC
);
CREATE INDEX "main"."bfagent_generatedimage_user_id_aeb29fc0"
ON "bfagent_generatedimage" (
  "user_id" ASC
);
CREATE INDEX "main"."bfagent_imagegenerationbatch_project_id_e282e69c"
ON "bfagent_imagegenerationbatch" (
  "project_id" ASC
);
CREATE INDEX "main"."bfagent_imagegenerationbatch_style_profile_id_4ac75a90"
ON "bfagent_imagegenerationbatch" (
  "style_profile_id" ASC
);
CREATE INDEX "main"."bfagent_imagegenerationbatch_user_id_e63dfa97"
ON "bfagent_imagegenerationbatch" (
  "user_id" ASC
);
CREATE INDEX "main"."bfagent_imagestyleprofile_project_id_dc338940"
ON "bfagent_imagestyleprofile" (
  "project_id" ASC
);
CREATE INDEX "main"."bfagent_imagestyleprofile_user_id_f04435d1"
ON "bfagent_imagestyleprofile" (
  "user_id" ASC
);
CREATE INDEX "main"."bfagent_mig_app_lab_49b9ce_idx"
ON "bfagent_migration_registry" (
  "app_label" ASC,
  "migration_number" ASC
);
CREATE INDEX "main"."bfagent_mig_applied_956deb_idx"
ON "bfagent_migration_registry" (
  "applied_at" ASC
);
CREATE INDEX "main"."bfagent_mig_complex_8efe00_idx"
ON "bfagent_migration_registry" (
  "complexity_score" ASC
);
CREATE INDEX "main"."bfagent_mig_is_appl_7ca748_idx"
ON "bfagent_migration_registry" (
  "is_applied" ASC,
  "app_label" ASC
);
CREATE INDEX "main"."bfagent_migration_conflict_migration1_id_2142a34a"
ON "bfagent_migration_conflict" (
  "migration1_id" ASC
);
CREATE INDEX "main"."bfagent_migration_conflict_migration2_id_e993255b"
ON "bfagent_migration_conflict" (
  "migration2_id" ASC
);
CREATE INDEX "main"."bfagent_migration_registry_app_label_ce9b9a6c"
ON "bfagent_migration_registry" (
  "app_label" ASC
);
CREATE UNIQUE INDEX "main"."bfagent_migration_registry_app_label_migration_name_af598197_uniq"
ON "bfagent_migration_registry" (
  "app_label" ASC,
  "migration_name" ASC
);
CREATE INDEX "main"."bfagent_migration_registry_is_applied_72526bb4"
ON "bfagent_migration_registry" (
  "is_applied" ASC
);
CREATE INDEX "main"."bfagent_migration_registry_migration_name_4ae81d60"
ON "bfagent_migration_registry" (
  "migration_name" ASC
);
CREATE INDEX "main"."bfagent_migration_registry_migration_type_3a450c04"
ON "bfagent_migration_registry" (
  "migration_type" ASC
);
CREATE INDEX "main"."bfagent_req_require_9e50ce_idx"
ON "bfagent_requirementtestlink" (
  "requirement_id" ASC,
  "status" ASC
);
CREATE INDEX "main"."bfagent_req_test_ca_f222ed_idx"
ON "bfagent_requirementtestlink" (
  "test_case_id" ASC,
  "last_test_result" ASC
);
CREATE INDEX "main"."bfagent_requirementtestlink_requirement_id_91294358"
ON "bfagent_requirementtestlink" (
  "requirement_id" ASC
);
CREATE UNIQUE INDEX "main"."bfagent_requirementtestlink_requirement_id_criterion_id_e4146098_uniq"
ON "bfagent_requirementtestlink" (
  "requirement_id" ASC,
  "criterion_id" ASC
);
CREATE INDEX "main"."bfagent_requirementtestlink_test_case_id_3c617cd2"
ON "bfagent_requirementtestlink" (
  "test_case_id" ASC
);
CREATE INDEX "main"."bfagent_reviewparticipant_review_round_id_3b862ec5"
ON "bfagent_reviewparticipant" (
  "review_round_id" ASC
);
CREATE UNIQUE INDEX "main"."bfagent_reviewparticipant_review_round_id_user_id_d064e03a_uniq"
ON "bfagent_reviewparticipant" (
  "review_round_id" ASC,
  "user_id" ASC
);
CREATE INDEX "main"."bfagent_reviewparticipant_user_id_48721ea4"
ON "bfagent_reviewparticipant" (
  "user_id" ASC
);
CREATE INDEX "main"."bfagent_reviewround_created_by_id_54e3467c"
ON "bfagent_reviewround" (
  "created_by_id" ASC
);
CREATE INDEX "main"."bfagent_reviewround_project_id_5098a619"
ON "bfagent_reviewround" (
  "project_id" ASC
);
CREATE INDEX "main"."bfagent_tes_categor_266b32_idx"
ON "bfagent_testrequirement" (
  "category" ASC
);
CREATE INDEX "main"."bfagent_tes_created_6e9b05_idx"
ON "bfagent_testrequirement" (
  "created_at" ASC
);
CREATE INDEX "main"."bfagent_tes_execute_0cd84a_idx"
ON "bfagent_testexecution" (
  "executed_at" ASC
);
CREATE INDEX "main"."bfagent_tes_framewo_f853f8_idx"
ON "bfagent_testcase" (
  "framework" ASC,
  "test_type" ASC
);
CREATE INDEX "main"."bfagent_tes_status_44c843_idx"
ON "bfagent_testrequirement" (
  "status" ASC,
  "priority" ASC
);
CREATE INDEX "main"."bfagent_tes_status_7807e7_idx"
ON "bfagent_testcase" (
  "status" ASC
);
CREATE INDEX "main"."bfagent_tes_test_ca_b2db02_idx"
ON "bfagent_testexecution" (
  "test_case_id" ASC,
  "result" ASC
);
CREATE INDEX "main"."bfagent_testbug_screenshot_id_fc659e59"
ON "bfagent_testbug" (
  "screenshot_id" ASC
);
CREATE INDEX "main"."bfagent_testbug_session_id_b680d0a1"
ON "bfagent_testbug" (
  "session_id" ASC
);
CREATE INDEX "main"."bfagent_testexecution_executed_by_id_d645a7c4"
ON "bfagent_testexecution" (
  "executed_by_id" ASC
);
CREATE INDEX "main"."bfagent_testexecution_test_case_id_1d833f7d"
ON "bfagent_testexecution" (
  "test_case_id" ASC
);
CREATE INDEX "main"."bfagent_testlog_session_id_ffe3f6ca"
ON "bfagent_testlog" (
  "session_id" ASC
);
CREATE INDEX "main"."bfagent_testrequirement_created_by_id_f465efb0"
ON "bfagent_testrequirement" (
  "created_by_id" ASC
);
CREATE INDEX "main"."bfagent_testscreenshot_session_id_4fec3171"
ON "bfagent_testscreenshot" (
  "session_id" ASC
);
CREATE INDEX "main"."bfagent_testsession_requirement_id_2dcd27e4"
ON "bfagent_testsession" (
  "requirement_id" ASC
);
CREATE INDEX "main"."bfagent_testsession_user_id_17e8631d"
ON "bfagent_testsession" (
  "user_id" ASC
);
CREATE INDEX "main"."book_characters_v2_book_id_97ec892c"
ON "book_characters_v2" (
  "book_id" ASC
);
CREATE UNIQUE INDEX "main"."book_characters_v2_book_id_character_id_3e701194_uniq"
ON "book_characters_v2" (
  "book_id" ASC,
  "character_id" ASC
);
CREATE INDEX "main"."book_characters_v2_character_id_e9d909bc"
ON "book_characters_v2" (
  "character_id" ASC
);
CREATE INDEX "main"."book_characters_v2_first_appearance_id_9c04870d"
ON "book_characters_v2" (
  "first_appearance_id" ASC
);
CREATE INDEX "main"."book_status_domain__0f8fb5_idx"
ON "book_statuses" (
  "domain_art_id" ASC,
  "is_active" ASC
);
CREATE INDEX "main"."book_status_is_acti_233dc0_idx"
ON "book_statuses" (
  "is_active" ASC,
  "sort_order" ASC
);
CREATE INDEX "main"."book_status_stage_30682d_idx"
ON "book_statuses" (
  "stage" ASC
);
CREATE INDEX "main"."book_statuses_domain_art_id_f3f0546b"
ON "book_statuses" (
  "domain_art_id" ASC
);
CREATE UNIQUE INDEX "main"."book_statuses_domain_art_id_slug_64e6d7fd_uniq"
ON "book_statuses" (
  "domain_art_id" ASC,
  "slug" ASC
);
CREATE INDEX "main"."book_statuses_slug_e0b10c6e"
ON "book_statuses" (
  "slug" ASC
);
CREATE INDEX "main"."book_type_phases_book_type_id_cf37fab9"
ON "book_type_phases" (
  "book_type_id" ASC
);
CREATE UNIQUE INDEX "main"."book_type_phases_book_type_id_phase_id_b4682d33_uniq"
ON "book_type_phases" (
  "book_type_id" ASC,
  "phase_id" ASC
);
CREATE INDEX "main"."book_type_phases_phase_id_2f1a2ed5"
ON "book_type_phases" (
  "phase_id" ASC
);
CREATE INDEX "main"."cad_analysi_job_id_a0ad90_idx"
ON "cad_analysis_results" (
  "job_id" ASC,
  "result_type" ASC
);
CREATE INDEX "main"."cad_analysi_project_4f65b1_idx"
ON "cad_analysis_jobs" (
  "project_id" ASC,
  "status" ASC
);
CREATE INDEX "main"."cad_analysi_status_052c75_idx"
ON "cad_analysis_jobs" (
  "status" ASC,
  "created_at" DESC
);
CREATE INDEX "main"."cad_analysis_category_is_active_42b216da"
ON "cad_analysis_category" (
  "is_active" ASC
);
CREATE INDEX "main"."cad_analysis_jobs_created_by_id_e17b3de1"
ON "cad_analysis_jobs" (
  "created_by_id" ASC
);
CREATE INDEX "main"."cad_analysis_jobs_project_id_74472271"
ON "cad_analysis_jobs" (
  "project_id" ASC
);
CREATE INDEX "main"."cad_analysis_jobs_status_568ae190"
ON "cad_analysis_jobs" (
  "status" ASC
);
CREATE INDEX "main"."cad_analysis_reports_job_id_eab9ebaf"
ON "cad_analysis_reports" (
  "job_id" ASC
);
CREATE INDEX "main"."cad_analysis_results_file_id_2fa41d58"
ON "cad_analysis_results" (
  "file_id" ASC
);
CREATE INDEX "main"."cad_analysis_results_job_id_ccd5ccca"
ON "cad_analysis_results" (
  "job_id" ASC
);
CREATE INDEX "main"."cad_building_type_is_active_8fce5a66"
ON "cad_building_type" (
  "is_active" ASC
);
CREATE INDEX "main"."cad_compliance_standard_is_active_47005316"
ON "cad_compliance_standard" (
  "is_active" ASC
);
CREATE INDEX "main"."cad_drawing_files_job_id_ecdfd390"
ON "cad_drawing_files" (
  "job_id" ASC
);
CREATE INDEX "main"."cad_drawing_type_is_active_8b52fadf"
ON "cad_drawing_type" (
  "is_active" ASC
);
CREATE INDEX "main"."cad_layer_standard_is_active_d090d996"
ON "cad_layer_standard" (
  "is_active" ASC
);
CREATE INDEX "main"."cad_severity_level_is_active_36075761"
ON "cad_severity_level" (
  "is_active" ASC
);
CREATE INDEX "main"."cas_lookup_idx"
ON "expert_hub_gefahrstoff" (
  "cas_number" ASC
);
CREATE INDEX "main"."chapters_v2_book_id_5cb43cc3"
ON "chapters_v2" (
  "book_id" ASC
);
CREATE INDEX "main"."chapters_v2_book_id_b47840_idx"
ON "chapters_v2" (
  "book_id" ASC,
  "number" ASC
);
CREATE UNIQUE INDEX "main"."chapters_v2_book_id_number_c06be84d_uniq"
ON "chapters_v2" (
  "book_id" ASC,
  "number" ASC
);
CREATE INDEX "main"."chapters_v2_created_1dd366_idx"
ON "chapters_v2" (
  "created_at" DESC
);
CREATE INDEX "main"."chapters_v2_status_0a70e7_idx"
ON "chapters_v2" (
  "status" ASC,
  "created_at" DESC
);
CREATE INDEX "main"."characters__created_05e319_idx"
ON "characters_v2" (
  "created_by_id" ASC,
  "created_at" DESC
);
CREATE INDEX "main"."characters__created_f08312_idx"
ON "characters_v2" (
  "created_at" DESC
);
CREATE INDEX "main"."characters__role_03662d_idx"
ON "characters_v2" (
  "role" ASC
);
CREATE INDEX "main"."characters_v2_created_by_id_34a113d9"
ON "characters_v2" (
  "created_by_id" ASC
);
CREATE INDEX "main"."checklist_i_auto_ch_4db7a9_idx"
ON "checklist_item_statuses" (
  "auto_checked" ASC
);
CREATE INDEX "main"."checklist_i_checkli_c097cc_idx"
ON "checklist_item_statuses" (
  "checklist_id" ASC,
  "is_checked" ASC
);
CREATE INDEX "main"."checklist_i_complet_a84e32_idx"
ON "checklist_instances" (
  "completed_at" ASC
);
CREATE INDEX "main"."checklist_i_content_a9e618_idx"
ON "checklist_instances" (
  "content_type_id" ASC,
  "object_id" ASC
);
CREATE INDEX "main"."checklist_i_is_acti_da83ac_idx"
ON "checklist_items" (
  "is_active" ASC
);
CREATE INDEX "main"."checklist_i_phase_488c30_idx"
ON "checklist_instances" (
  "phase" ASC
);
CREATE INDEX "main"."checklist_i_templat_f9e7a6_idx"
ON "checklist_items" (
  "template_id" ASC,
  "order" ASC
);
CREATE INDEX "main"."checklist_instances_completed_by_id_209f60a7"
ON "checklist_instances" (
  "completed_by_id" ASC
);
CREATE INDEX "main"."checklist_instances_content_type_id_2208073f"
ON "checklist_instances" (
  "content_type_id" ASC
);
CREATE INDEX "main"."checklist_instances_created_by_id_b1733f0e"
ON "checklist_instances" (
  "created_by_id" ASC
);
CREATE INDEX "main"."checklist_instances_template_id_bd0dcd36"
ON "checklist_instances" (
  "template_id" ASC
);
CREATE INDEX "main"."checklist_item_statuses_checked_by_id_3c74ae5b"
ON "checklist_item_statuses" (
  "checked_by_id" ASC
);
CREATE INDEX "main"."checklist_item_statuses_checklist_id_9a01ee30"
ON "checklist_item_statuses" (
  "checklist_id" ASC
);
CREATE UNIQUE INDEX "main"."checklist_item_statuses_checklist_id_item_id_0ff0b1f1_uniq"
ON "checklist_item_statuses" (
  "checklist_id" ASC,
  "item_id" ASC
);
CREATE INDEX "main"."checklist_item_statuses_item_id_10712416"
ON "checklist_item_statuses" (
  "item_id" ASC
);
CREATE INDEX "main"."checklist_t_domain__d3c3bf_idx"
ON "checklist_templates" (
  "domain_art_id" ASC,
  "phase" ASC
);
CREATE INDEX "main"."checklist_t_is_acti_9ef45f_idx"
ON "checklist_templates" (
  "is_active" ASC
);
CREATE INDEX "main"."comic_dialo_charact_e5e049_idx"
ON "comic_dialogues" (
  "character_id" ASC
);
CREATE INDEX "main"."comic_dialo_panel_i_bca7c3_idx"
ON "comic_dialogues" (
  "panel_id" ASC,
  "order" ASC
);
CREATE INDEX "main"."comic_dialogues_character_id_1f7a1011"
ON "comic_dialogues" (
  "character_id" ASC
);
CREATE INDEX "main"."comic_dialogues_panel_id_98d839fb"
ON "comic_dialogues" (
  "panel_id" ASC
);
CREATE INDEX "main"."comic_panel_chapter_cd7960_idx"
ON "comic_panels" (
  "chapter_id" ASC,
  "panel_number" ASC
);
CREATE INDEX "main"."comic_panel_status_b43d6c_idx"
ON "comic_panels" (
  "status" ASC
);
CREATE INDEX "main"."comic_panels_chapter_id_60059a09"
ON "comic_panels" (
  "chapter_id" ASC
);
CREATE UNIQUE INDEX "main"."comic_panels_chapter_id_panel_number_ec72208c_uniq"
ON "comic_panels" (
  "chapter_id" ASC,
  "panel_number" ASC
);
CREATE INDEX "main"."compliance_audit_log_action_3cfe58bd"
ON "compliance_audit_log" (
  "action" ASC
);
CREATE INDEX "main"."compliance_audit_log_client_id_e1eb89be"
ON "compliance_audit_log" (
  "client_id" ASC
);
CREATE INDEX "main"."compliance_audit_log_domain_88c71613"
ON "compliance_audit_log" (
  "domain" ASC
);
CREATE INDEX "main"."compliance_audit_log_entity_type_id_37d88a9a"
ON "compliance_audit_log" (
  "entity_type_id" ASC
);
CREATE INDEX "main"."compliance_audit_log_timestamp_2028e0cc"
ON "compliance_audit_log" (
  "timestamp" ASC
);
CREATE INDEX "main"."compliance_audit_log_user_id_bf0e49be"
ON "compliance_audit_log" (
  "user_id" ASC
);
CREATE INDEX "main"."compliance_idx"
ON "expert_hub_auditlog" (
  "compliance_relevant" ASC
);
CREATE INDEX "main"."compliance_incident_severity_is_active_f9735b67"
ON "compliance_incident_severity" (
  "is_active" ASC
);
CREATE INDEX "main"."compliance_incident_severity_sort_order_9b02f0ac"
ON "compliance_incident_severity" (
  "sort_order" ASC
);
CREATE INDEX "main"."compliance_priority_is_active_601f1cce"
ON "compliance_priority" (
  "is_active" ASC
);
CREATE INDEX "main"."compliance_priority_sort_order_c483f7e7"
ON "compliance_priority" (
  "sort_order" ASC
);
CREATE INDEX "main"."compliance_risk_level_is_active_b7daa7df"
ON "compliance_risk_level" (
  "is_active" ASC
);
CREATE INDEX "main"."compliance_risk_level_sort_order_fa44b2c1"
ON "compliance_risk_level" (
  "sort_order" ASC
);
CREATE INDEX "main"."compliance_status_is_active_3d31fa22"
ON "compliance_status" (
  "is_active" ASC
);
CREATE INDEX "main"."compliance_status_sort_order_8a4d9901"
ON "compliance_status" (
  "sort_order" ASC
);
CREATE INDEX "main"."compliance_tag_created_by_id_67ef98c7"
ON "compliance_tag" (
  "created_by_id" ASC
);
CREATE INDEX "main"."compliance_tag_domain_20d1f45a"
ON "compliance_tag" (
  "domain" ASC
);
CREATE INDEX "main"."compliance_tagged_item_content_type_id_dbae70fc"
ON "compliance_tagged_item" (
  "content_type_id" ASC
);
CREATE INDEX "main"."compliance_tagged_item_tag_id_80b0db75"
ON "compliance_tagged_item" (
  "tag_id" ASC
);
CREATE UNIQUE INDEX "main"."compliance_tagged_item_tag_id_content_type_id_object_id_ff5797fc_uniq"
ON "compliance_tagged_item" (
  "tag_id" ASC,
  "content_type_id" ASC,
  "object_id" ASC
);
CREATE INDEX "main"."compliance_tagged_item_tagged_by_id_76dd4ea7"
ON "compliance_tagged_item" (
  "tagged_by_id" ASC
);
CREATE INDEX "main"."content_blo_content_cc463d_idx"
ON "content_blocks" (
  "content_hash" ASC
);
CREATE INDEX "main"."content_blo_project_d0b0a9_idx"
ON "content_blocks" (
  "project_id" ASC,
  "content_type" ASC,
  "order" ASC
);
CREATE INDEX "main"."content_blo_project_dc335e_idx"
ON "content_blocks" (
  "project_id" ASC,
  "content_type" ASC
);
CREATE INDEX "main"."content_blo_status_6e639a_idx"
ON "content_blocks" (
  "status" ASC
);
CREATE INDEX "main"."content_blocks_content_hash_0441ebaf"
ON "content_blocks" (
  "content_hash" ASC
);
CREATE INDEX "main"."content_blocks_content_type_2f3e89f0"
ON "content_blocks" (
  "content_type" ASC
);
CREATE INDEX "main"."content_blocks_order_2454020c"
ON "content_blocks" (
  "order" ASC
);
CREATE INDEX "main"."content_blocks_parent_id_04b891e1"
ON "content_blocks" (
  "parent_id" ASC
);
CREATE INDEX "main"."content_blocks_project_id_35796ce7"
ON "content_blocks" (
  "project_id" ASC
);
CREATE INDEX "main"."core_agent__agent_i_e04cb0_idx"
ON "core_agent_executions" (
  "agent_id" ASC,
  "executed_at" DESC
);
CREATE INDEX "main"."core_agent__status_ba891f_idx"
ON "core_agent_executions" (
  "status" ASC,
  "executed_at" DESC
);
CREATE INDEX "main"."core_agent_executions_agent_id_a893bf91"
ON "core_agent_executions" (
  "agent_id" ASC
);
CREATE INDEX "main"."core_agent_executions_executed_at_7bf0d1bc"
ON "core_agent_executions" (
  "executed_at" ASC
);
CREATE INDEX "main"."core_agent_executions_llm_used_id_b62a8e2c"
ON "core_agent_executions" (
  "llm_used_id" ASC
);
CREATE INDEX "main"."core_conten_content_00ea43_idx"
ON "core_contentitem" (
  "content_type" ASC,
  "primary_tag" ASC
);
CREATE INDEX "main"."core_conten_content_133927_idx"
ON "core_contentitem" (
  "content_type" ASC,
  "category" ASC,
  "visual_style" ASC
);
CREATE INDEX "main"."core_conten_created_9c47aa_idx"
ON "core_contentitem" (
  "created_at" ASC,
  "content_type" ASC
);
CREATE INDEX "main"."core_conten_is_ai_g_42278e_idx"
ON "core_contentitem" (
  "is_ai_generated" ASC,
  "ai_confidence_score" ASC
);
CREATE INDEX "main"."core_conten_parent__85ae34_idx"
ON "core_contentitem" (
  "parent_item_id" ASC,
  "sequence_number" ASC
);
CREATE INDEX "main"."core_conten_project_92c5e4_idx"
ON "core_contentitem" (
  "project_id" ASC,
  "content_type" ASC,
  "status" ASC
);
CREATE INDEX "main"."core_conten_project_a96bb8_idx"
ON "core_contentitem" (
  "project_id" ASC,
  "sequence_number" ASC
);
CREATE INDEX "main"."core_conten_related_ab07d1_idx"
ON "core_contentitem" (
  "related_character_id" ASC,
  "content_type" ASC
);
CREATE INDEX "main"."core_conten_status_bb7f62_idx"
ON "core_contentitem" (
  "status" ASC,
  "priority" ASC,
  "assigned_to_id" ASC
);
CREATE INDEX "main"."core_contentitem_assigned_to_id_7e1d3f84"
ON "core_contentitem" (
  "assigned_to_id" ASC
);
CREATE INDEX "main"."core_contentitem_category_02f38d76"
ON "core_contentitem" (
  "category" ASC
);
CREATE INDEX "main"."core_contentitem_completion_percentage_66f74499"
ON "core_contentitem" (
  "completion_percentage" ASC
);
CREATE INDEX "main"."core_contentitem_content_type_7584e81d"
ON "core_contentitem" (
  "content_type" ASC
);
CREATE INDEX "main"."core_contentitem_created_at_67792e15"
ON "core_contentitem" (
  "created_at" ASC
);
CREATE INDEX "main"."core_contentitem_created_by_id_2a5aee81"
ON "core_contentitem" (
  "created_by_id" ASC
);
CREATE INDEX "main"."core_contentitem_external_id_33ee7da1"
ON "core_contentitem" (
  "external_id" ASC
);
CREATE INDEX "main"."core_contentitem_is_ai_generated_23628622"
ON "core_contentitem" (
  "is_ai_generated" ASC
);
CREATE INDEX "main"."core_contentitem_parent_item_id_ce5a4a34"
ON "core_contentitem" (
  "parent_item_id" ASC
);
CREATE INDEX "main"."core_contentitem_primary_tag_e744345d"
ON "core_contentitem" (
  "primary_tag" ASC
);
CREATE INDEX "main"."core_contentitem_priority_5c448824"
ON "core_contentitem" (
  "priority" ASC
);
CREATE INDEX "main"."core_contentitem_project_id_5a4a3111"
ON "core_contentitem" (
  "project_id" ASC
);
CREATE INDEX "main"."core_contentitem_related_character_id_102e67de"
ON "core_contentitem" (
  "related_character_id" ASC
);
CREATE INDEX "main"."core_contentitem_sequence_number_d3e753d2"
ON "core_contentitem" (
  "sequence_number" ASC
);
CREATE INDEX "main"."core_contentitem_status_ce38514e"
ON "core_contentitem" (
  "status" ASC
);
CREATE INDEX "main"."core_contentitem_visual_style_309e5bc7"
ON "core_contentitem" (
  "visual_style" ASC
);
CREATE INDEX "main"."core_contentitem_word_count_e02b92ba"
ON "core_contentitem" (
  "word_count" ASC
);
CREATE INDEX "main"."core_customers_is_active_f2fba9b8"
ON "core_customers" (
  "is_active" ASC
);
CREATE INDEX "main"."core_customers_name_de984037"
ON "core_customers" (
  "name" ASC
);
CREATE INDEX "main"."core_locations_customer_id_ea89ed14"
ON "core_locations" (
  "customer_id" ASC
);
CREATE UNIQUE INDEX "main"."core_locations_customer_id_location_code_03f3c6d5_uniq"
ON "core_locations" (
  "customer_id" ASC,
  "location_code" ASC
);
CREATE INDEX "main"."core_locations_is_active_eaaa87ce"
ON "core_locations" (
  "is_active" ASC
);
CREATE INDEX "main"."core_locations_name_d9d4d0c2"
ON "core_locations" (
  "name" ASC
);
CREATE INDEX "main"."core_plugin_configurations_custom_template_id_1948f0a5"
ON "core_plugin_configurations" (
  "custom_template_id" ASC
);
CREATE INDEX "main"."core_plugin_configurations_plugin_id_c52a26a9"
ON "core_plugin_configurations" (
  "plugin_id" ASC
);
CREATE UNIQUE INDEX "main"."core_plugin_configurations_plugin_id_user_id_project_id_1443e6da_uniq"
ON "core_plugin_configurations" (
  "plugin_id" ASC,
  "user_id" ASC,
  "project_id" ASC
);
CREATE INDEX "main"."core_plugin_configurations_project_id_9669b761"
ON "core_plugin_configurations" (
  "project_id" ASC
);
CREATE INDEX "main"."core_plugin_configurations_user_id_316d29f6"
ON "core_plugin_configurations" (
  "user_id" ASC
);
CREATE INDEX "main"."core_plugin_domain_c246e3_idx"
ON "core_plugin_registry" (
  "domain" ASC,
  "category" ASC,
  "is_active" ASC
);
CREATE INDEX "main"."core_plugin_execute_eef837_idx"
ON "core_plugin_executions" (
  "executed_by_id" ASC,
  "executed_at" DESC
);
CREATE INDEX "main"."core_plugin_executions_executed_at_bfff5139"
ON "core_plugin_executions" (
  "executed_at" ASC
);
CREATE INDEX "main"."core_plugin_executions_executed_by_id_8508cf71"
ON "core_plugin_executions" (
  "executed_by_id" ASC
);
CREATE INDEX "main"."core_plugin_executions_plugin_id_045d022d"
ON "core_plugin_executions" (
  "plugin_id" ASC
);
CREATE INDEX "main"."core_plugin_last_ex_137c0f_idx"
ON "core_plugin_registry" (
  "last_executed_at" DESC
);
CREATE INDEX "main"."core_plugin_plugin__f5ac89_idx"
ON "core_plugin_executions" (
  "plugin_id" ASC,
  "executed_at" DESC
);
CREATE INDEX "main"."core_plugin_plugin__fcbb53_idx"
ON "core_plugin_registry" (
  "plugin_id" ASC
);
CREATE INDEX "main"."core_plugin_registry_ab_test_group_97f586d1"
ON "core_plugin_registry" (
  "ab_test_group" ASC
);
CREATE INDEX "main"."core_plugin_registry_author_id_6b41fc6b"
ON "core_plugin_registry" (
  "author_id" ASC
);
CREATE INDEX "main"."core_plugin_registry_category_08e3f849"
ON "core_plugin_registry" (
  "category" ASC
);
CREATE INDEX "main"."core_plugin_registry_default_template_id_a34186ee"
ON "core_plugin_registry" (
  "default_template_id" ASC
);
CREATE INDEX "main"."core_plugin_registry_depends_on_from_pluginregistry_id_5b2cd1ac"
ON "core_plugin_registry_depends_on" (
  "from_pluginregistry_id" ASC
);
CREATE UNIQUE INDEX "main"."core_plugin_registry_depends_on_from_pluginregistry_id_to_pluginregistry_id_737ee385_uniq"
ON "core_plugin_registry_depends_on" (
  "from_pluginregistry_id" ASC,
  "to_pluginregistry_id" ASC
);
CREATE INDEX "main"."core_plugin_registry_depends_on_to_pluginregistry_id_d2afa833"
ON "core_plugin_registry_depends_on" (
  "to_pluginregistry_id" ASC
);
CREATE INDEX "main"."core_plugin_registry_domain_037c30b0"
ON "core_plugin_registry" (
  "domain" ASC
);
CREATE INDEX "main"."core_plugin_registry_is_active_aa69f1ab"
ON "core_plugin_registry" (
  "is_active" ASC
);
CREATE INDEX "main"."core_plugin_registry_maintainer_id_812d9a8a"
ON "core_plugin_registry" (
  "maintainer_id" ASC
);
CREATE INDEX "main"."core_plugin_status_616ed7_idx"
ON "core_plugin_executions" (
  "status" ASC,
  "executed_at" DESC
);
CREATE INDEX "main"."core_plugin_user_ra_71955e_idx"
ON "core_plugin_registry" (
  "user_rating" DESC
);
CREATE INDEX "main"."core_prompt_agent_i_bde561_idx"
ON "core_prompt_executions" (
  "agent_id" ASC,
  "executed_at" DESC
);
CREATE INDEX "main"."core_prompt_categor_2a40b3_idx"
ON "core_prompt_templates" (
  "category" ASC,
  "is_active" ASC
);
CREATE INDEX "main"."core_prompt_executions_agent_id_1b290184"
ON "core_prompt_executions" (
  "agent_id" ASC
);
CREATE INDEX "main"."core_prompt_executions_executed_at_99577ffd"
ON "core_prompt_executions" (
  "executed_at" ASC
);
CREATE INDEX "main"."core_prompt_executions_executed_by_id_7cbfc0db"
ON "core_prompt_executions" (
  "executed_by_id" ASC
);
CREATE INDEX "main"."core_prompt_executions_llm_id_f71c3f78"
ON "core_prompt_executions" (
  "llm_id" ASC
);
CREATE INDEX "main"."core_prompt_executions_template_id_a9d45e07"
ON "core_prompt_executions" (
  "template_id" ASC
);
CREATE INDEX "main"."core_prompt_last_us_7faf90_idx"
ON "core_prompt_templates" (
  "last_used_at" DESC
);
CREATE INDEX "main"."core_prompt_status_b7ccf8_idx"
ON "core_prompt_executions" (
  "status" ASC,
  "executed_at" DESC
);
CREATE INDEX "main"."core_prompt_templat_42dd09_idx"
ON "core_prompt_templates" (
  "template_key" ASC
);
CREATE INDEX "main"."core_prompt_templat_c78b99_idx"
ON "core_prompt_executions" (
  "template_id" ASC,
  "executed_at" DESC
);
CREATE INDEX "main"."core_prompt_templates_ab_test_group_b861a6cc"
ON "core_prompt_templates" (
  "ab_test_group" ASC
);
CREATE INDEX "main"."core_prompt_templates_category_1720fe0e"
ON "core_prompt_templates" (
  "category" ASC
);
CREATE INDEX "main"."core_prompt_templates_created_by_id_5d8d885b"
ON "core_prompt_templates" (
  "created_by_id" ASC
);
CREATE INDEX "main"."core_prompt_templates_domain_d2a10251"
ON "core_prompt_templates" (
  "domain" ASC
);
CREATE INDEX "main"."core_prompt_templates_fallback_template_id_2d5f4fad"
ON "core_prompt_templates" (
  "fallback_template_id" ASC
);
CREATE INDEX "main"."core_prompt_templates_is_active_ec588021"
ON "core_prompt_templates" (
  "is_active" ASC
);
CREATE INDEX "main"."core_prompt_templates_parent_template_id_0420dd0e"
ON "core_prompt_templates" (
  "parent_template_id" ASC
);
CREATE INDEX "main"."core_prompt_templates_preferred_llm_id_22225e16"
ON "core_prompt_templates" (
  "preferred_llm_id" ASC
);
CREATE INDEX "main"."core_prompt_versions_changed_by_id_c738ec31"
ON "core_prompt_versions" (
  "changed_by_id" ASC
);
CREATE INDEX "main"."core_prompt_versions_template_id_582116b2"
ON "core_prompt_versions" (
  "template_id" ASC
);
CREATE UNIQUE INDEX "main"."core_prompt_versions_template_id_version_number_1037d7f2_uniq"
ON "core_prompt_versions" (
  "template_id" ASC,
  "version_number" ASC
);
CREATE INDEX "main"."customer_project_idx"
ON "expert_hub_exschutzdocument" (
  "customer_id" ASC,
  "project_id" ASC
);
CREATE INDEX "main"."customer_upload_idx"
ON "expert_hub_exschutzdocument" (
  "customer_id" ASC,
  "uploaded_at" ASC
);
CREATE INDEX "main"."django_admin_log_content_type_id_c4bce8eb"
ON "django_admin_log" (
  "content_type_id" ASC
);
CREATE INDEX "main"."django_admin_log_user_id_c564eba6"
ON "django_admin_log" (
  "user_id" ASC
);
CREATE UNIQUE INDEX "main"."django_content_type_app_label_model_76bd3d3b_uniq"
ON "django_content_type" (
  "app_label" ASC,
  "model" ASC
);
CREATE INDEX "main"."django_session_expire_date_a5c62663"
ON "django_session" (
  "expire_date" ASC
);
CREATE INDEX "main"."doc_cas_idx"
ON "expert_hub_gefahrstoff" (
  "document_id" ASC,
  "cas_number" ASC
);
CREATE INDEX "main"."doc_massnahme_idx"
ON "expert_hub_schutzmassnahme" (
  "document_id" ASC,
  "massnahme_typ" ASC
);
CREATE INDEX "main"."doc_time_idx"
ON "expert_hub_auditlog" (
  "document_id" ASC,
  "timestamp" ASC
);
CREATE INDEX "main"."doc_type_idx"
ON "expert_hub_exschutzdocument" (
  "document_type_id" ASC
);
CREATE INDEX "main"."doc_zone_idx"
ON "expert_hub_exzone" (
  "document_id" ASC,
  "zone_classification_id" ASC
);
CREATE INDEX "main"."domain_phases_domain_type_id_4ba48196"
ON "domain_phases" (
  "domain_type_id" ASC
);
CREATE UNIQUE INDEX "main"."domain_phases_domain_type_id_workflow_phase_id_885bcc7b_uniq"
ON "domain_phases" (
  "domain_type_id" ASC,
  "workflow_phase_id" ASC
);
CREATE INDEX "main"."domain_phases_workflow_phase_id_a351bfb2"
ON "domain_phases" (
  "workflow_phase_id" ASC
);
CREATE INDEX "main"."domain_proj_created_4e933f_idx"
ON "domain_projects" (
  "created_by_id" ASC,
  "status" ASC
);
CREATE INDEX "main"."domain_proj_created_9ef853_idx"
ON "domain_projects" (
  "created_at" DESC
);
CREATE INDEX "main"."domain_proj_domain__da9d2a_idx"
ON "domain_projects" (
  "domain_type_id" ASC,
  "status" ASC
);
CREATE INDEX "main"."domain_projects_created_by_id_4767a8ce"
ON "domain_projects" (
  "created_by_id" ASC
);
CREATE INDEX "main"."domain_projects_current_phase_id_57dff64f"
ON "domain_projects" (
  "current_phase_id" ASC
);
CREATE INDEX "main"."domain_projects_domain_type_id_320969fb"
ON "domain_projects" (
  "domain_type_id" ASC
);
CREATE INDEX "main"."domain_projects_status_bbc4f82c"
ON "domain_projects" (
  "status" ASC
);
CREATE INDEX "main"."domain_section_items_section_id_93d92f01"
ON "domain_section_items" (
  "section_id" ASC
);
CREATE UNIQUE INDEX "main"."domain_section_items_section_id_slug_b82a6176_uniq"
ON "domain_section_items" (
  "section_id" ASC,
  "slug" ASC
);
CREATE INDEX "main"."domain_section_items_slug_6f76b04c"
ON "domain_section_items" (
  "slug" ASC
);
CREATE INDEX "main"."domain_sections_domain_art_id_bfd07226"
ON "domain_sections" (
  "domain_art_id" ASC
);
CREATE UNIQUE INDEX "main"."domain_sections_domain_art_id_slug_5dfcd28e_uniq"
ON "domain_sections" (
  "domain_art_id" ASC,
  "slug" ASC
);
CREATE INDEX "main"."domain_sections_slug_a013b2db"
ON "domain_sections" (
  "slug" ASC
);
CREATE INDEX "main"."dsb_branche_is_active_4e3ebe50"
ON "dsb_branche" (
  "is_active" ASC
);
CREATE INDEX "main"."dsb_branche_sort_order_99c54497"
ON "dsb_branche" (
  "sort_order" ASC
);
CREATE INDEX "main"."dsb_datenkategorie_is_active_27cc4bb8"
ON "dsb_datenkategorie" (
  "is_active" ASC
);
CREATE INDEX "main"."dsb_datenkategorie_sensitivity_id_32a19970"
ON "dsb_datenkategorie" (
  "sensitivity_id" ASC
);
CREATE INDEX "main"."dsb_datenkategorie_sort_order_a779f300"
ON "dsb_datenkategorie" (
  "sort_order" ASC
);
CREATE INDEX "main"."dsb_dokument_approved_by_id_8aef8e7c"
ON "dsb_dokument" (
  "approved_by_id" ASC
);
CREATE INDEX "main"."dsb_dokument_client_content_type_id_92c361d0"
ON "dsb_dokument" (
  "client_content_type_id" ASC
);
CREATE INDEX "main"."dsb_dokument_created_at_c54e6b38"
ON "dsb_dokument" (
  "created_at" ASC
);
CREATE INDEX "main"."dsb_dokument_created_by_id_67e4a905"
ON "dsb_dokument" (
  "created_by_id" ASC
);
CREATE INDEX "main"."dsb_dokument_deleted_by_id_79844db2"
ON "dsb_dokument" (
  "deleted_by_id" ASC
);
CREATE INDEX "main"."dsb_dokument_document_type_861beaa3"
ON "dsb_dokument" (
  "document_type" ASC
);
CREATE INDEX "main"."dsb_dokument_is_active_5b23c396"
ON "dsb_dokument" (
  "is_active" ASC
);
CREATE INDEX "main"."dsb_dokument_mandant_id_b4b37f04"
ON "dsb_dokument" (
  "mandant_id" ASC
);
CREATE INDEX "main"."dsb_dokument_review_date_c7a71472"
ON "dsb_dokument" (
  "review_date" ASC
);
CREATE INDEX "main"."dsb_dokument_status_bcf745f9"
ON "dsb_dokument" (
  "status" ASC
);
CREATE INDEX "main"."dsb_dokument_valid_until_847e23fb"
ON "dsb_dokument" (
  "valid_until" ASC
);
CREATE INDEX "main"."dsb_dokument_verarbeitung_id_eedb46d3"
ON "dsb_dokument" (
  "verarbeitung_id" ASC
);
CREATE INDEX "main"."dsb_mandant_betreuer_id_21672275"
ON "dsb_mandant" (
  "betreuer_id" ASC
);
CREATE INDEX "main"."dsb_mandant_branche_id_6af36828"
ON "dsb_mandant" (
  "branche_id" ASC
);
CREATE INDEX "main"."dsb_mandant_client_content_type_id_cac4ea14"
ON "dsb_mandant" (
  "client_content_type_id" ASC
);
CREATE INDEX "main"."dsb_mandant_created_at_b4f208c1"
ON "dsb_mandant" (
  "created_at" ASC
);
CREATE INDEX "main"."dsb_mandant_created_by_id_a0ae7ec3"
ON "dsb_mandant" (
  "created_by_id" ASC
);
CREATE INDEX "main"."dsb_mandant_deleted_by_id_3898fabf"
ON "dsb_mandant" (
  "deleted_by_id" ASC
);
CREATE INDEX "main"."dsb_mandant_external_id_ee644e08"
ON "dsb_mandant" (
  "external_id" ASC
);
CREATE INDEX "main"."dsb_mandant_is_active_d3efdbe9"
ON "dsb_mandant" (
  "is_active" ASC
);
CREATE INDEX "main"."dsb_mandant_name_99fd9c4c"
ON "dsb_mandant" (
  "name" ASC
);
CREATE INDEX "main"."dsb_mandant_rechtsform_id_226ba08a"
ON "dsb_mandant" (
  "rechtsform_id" ASC
);
CREATE INDEX "main"."dsb_mandant_risk_level_id_61247216"
ON "dsb_mandant" (
  "risk_level_id" ASC
);
CREATE INDEX "main"."dsb_mandant_tom_mandant_id_0190488b"
ON "dsb_mandant_tom" (
  "mandant_id" ASC
);
CREATE UNIQUE INDEX "main"."dsb_mandant_tom_mandant_id_massnahme_id_bea1c372_uniq"
ON "dsb_mandant_tom" (
  "mandant_id" ASC,
  "massnahme_id" ASC
);
CREATE INDEX "main"."dsb_mandant_tom_massnahme_id_4c3b94ef"
ON "dsb_mandant_tom" (
  "massnahme_id" ASC
);
CREATE INDEX "main"."dsb_rechtsform_is_active_d612c0e9"
ON "dsb_rechtsform" (
  "is_active" ASC
);
CREATE INDEX "main"."dsb_rechtsform_sort_order_301dddad"
ON "dsb_rechtsform" (
  "sort_order" ASC
);
CREATE INDEX "main"."dsb_rechtsgrundlage_is_active_1cad443b"
ON "dsb_rechtsgrundlage" (
  "is_active" ASC
);
CREATE INDEX "main"."dsb_rechtsgrundlage_sort_order_617568b9"
ON "dsb_rechtsgrundlage" (
  "sort_order" ASC
);
CREATE INDEX "main"."dsb_tom_kategorie_is_active_31700232"
ON "dsb_tom_kategorie" (
  "is_active" ASC
);
CREATE INDEX "main"."dsb_tom_kategorie_sort_order_18b48a96"
ON "dsb_tom_kategorie" (
  "sort_order" ASC
);
CREATE INDEX "main"."dsb_tom_massnahme_is_active_971171ce"
ON "dsb_tom_massnahme" (
  "is_active" ASC
);
CREATE INDEX "main"."dsb_tom_massnahme_kategorie_id_fde20bf2"
ON "dsb_tom_massnahme" (
  "kategorie_id" ASC
);
CREATE INDEX "main"."dsb_tom_massnahme_sort_order_9281709c"
ON "dsb_tom_massnahme" (
  "sort_order" ASC
);
CREATE INDEX "main"."dsb_verarbeitung_client_content_type_id_19785dbd"
ON "dsb_verarbeitung" (
  "client_content_type_id" ASC
);
CREATE INDEX "main"."dsb_verarbeitung_created_at_6045d466"
ON "dsb_verarbeitung" (
  "created_at" ASC
);
CREATE INDEX "main"."dsb_verarbeitung_created_by_id_29b2d4c2"
ON "dsb_verarbeitung" (
  "created_by_id" ASC
);
CREATE INDEX "main"."dsb_verarbeitung_datenkategorien_datenkategorie_id_1c99a371"
ON "dsb_verarbeitung_datenkategorien" (
  "datenkategorie_id" ASC
);
CREATE INDEX "main"."dsb_verarbeitung_datenkategorien_verarbeitung_id_80fe1b07"
ON "dsb_verarbeitung_datenkategorien" (
  "verarbeitung_id" ASC
);
CREATE UNIQUE INDEX "main"."dsb_verarbeitung_datenkategorien_verarbeitung_id_datenkategorie_id_cfe6634b_uniq"
ON "dsb_verarbeitung_datenkategorien" (
  "verarbeitung_id" ASC,
  "datenkategorie_id" ASC
);
CREATE INDEX "main"."dsb_verarbeitung_deleted_by_id_29349144"
ON "dsb_verarbeitung" (
  "deleted_by_id" ASC
);
CREATE INDEX "main"."dsb_verarbeitung_is_active_297aed1a"
ON "dsb_verarbeitung" (
  "is_active" ASC
);
CREATE INDEX "main"."dsb_verarbeitung_mandant_id_08a3dea6"
ON "dsb_verarbeitung" (
  "mandant_id" ASC
);
CREATE INDEX "main"."dsb_verarbeitung_next_review_641a4d4a"
ON "dsb_verarbeitung" (
  "next_review" ASC
);
CREATE INDEX "main"."dsb_verarbeitung_priority_id_d3f6246a"
ON "dsb_verarbeitung" (
  "priority_id" ASC
);
CREATE INDEX "main"."dsb_verarbeitung_rechtsgrundlage_id_c4c241a2"
ON "dsb_verarbeitung" (
  "rechtsgrundlage_id" ASC
);
CREATE INDEX "main"."dsb_verarbeitung_status_id_15c05c50"
ON "dsb_verarbeitung" (
  "status_id" ASC
);
CREATE INDEX "main"."dsb_vorfall_client_content_type_id_ddf7f5f3"
ON "dsb_vorfall" (
  "client_content_type_id" ASC
);
CREATE INDEX "main"."dsb_vorfall_created_at_61d723c9"
ON "dsb_vorfall" (
  "created_at" ASC
);
CREATE INDEX "main"."dsb_vorfall_created_by_id_0e50d377"
ON "dsb_vorfall" (
  "created_by_id" ASC
);
CREATE INDEX "main"."dsb_vorfall_deleted_by_id_723317fd"
ON "dsb_vorfall" (
  "deleted_by_id" ASC
);
CREATE INDEX "main"."dsb_vorfall_incident_datetime_20d87758"
ON "dsb_vorfall" (
  "incident_datetime" ASC
);
CREATE INDEX "main"."dsb_vorfall_incident_type_0e9a4102"
ON "dsb_vorfall" (
  "incident_type" ASC
);
CREATE INDEX "main"."dsb_vorfall_is_active_8e777f1c"
ON "dsb_vorfall" (
  "is_active" ASC
);
CREATE INDEX "main"."dsb_vorfall_mandant_id_f8408c34"
ON "dsb_vorfall" (
  "mandant_id" ASC
);
CREATE INDEX "main"."dsb_vorfall_severity_id_39061044"
ON "dsb_vorfall" (
  "severity_id" ASC
);
CREATE INDEX "main"."dsb_vorfall_status_a473e5ee"
ON "dsb_vorfall" (
  "status" ASC
);
CREATE INDEX "main"."dsb_vorfall_typ_default_severity_id_6618e820"
ON "dsb_vorfall_typ" (
  "default_severity_id" ASC
);
CREATE INDEX "main"."dsb_vorfall_typ_is_active_573cafe5"
ON "dsb_vorfall_typ" (
  "is_active" ASC
);
CREATE INDEX "main"."dsb_vorfall_typ_sort_order_967718cf"
ON "dsb_vorfall_typ" (
  "sort_order" ASC
);
CREATE INDEX "main"."dsb_vorfall_verarbeitung_id_8ee4b12e"
ON "dsb_vorfall" (
  "verarbeitung_id" ASC
);
CREATE INDEX "main"."dsb_vorfall_vorfall_typ_id_07bd0196"
ON "dsb_vorfall" (
  "vorfall_typ_id" ASC
);
CREATE INDEX "main"."enrichment__agent_i_440d3b_idx"
ON "enrichment_responses" (
  "agent_id" ASC,
  "action_name" ASC
);
CREATE INDEX "main"."enrichment__project_bea755_idx"
ON "enrichment_responses" (
  "project_id" ASC,
  "status" ASC
);
CREATE INDEX "main"."enrichment__target__34a36f_idx"
ON "enrichment_responses" (
  "target_model" ASC,
  "target_id" ASC
);
CREATE INDEX "main"."enrichment_responses_action_id_aa655d05"
ON "enrichment_responses" (
  "action_id" ASC
);
CREATE INDEX "main"."enrichment_responses_agent_id_98c1e0d0"
ON "enrichment_responses" (
  "agent_id" ASC
);
CREATE INDEX "main"."enrichment_responses_applied_by_id_63f65243"
ON "enrichment_responses" (
  "applied_by_id" ASC
);
CREATE INDEX "main"."enrichment_responses_llm_used_id_6875c89d"
ON "enrichment_responses" (
  "llm_used_id" ASC
);
CREATE INDEX "main"."enrichment_responses_project_id_193cbf1f"
ON "enrichment_responses" (
  "project_id" ASC
);
CREATE INDEX "main"."enrichment_responses_target_field_id_9e5f19ed"
ON "enrichment_responses" (
  "target_field_id" ASC
);
CREATE INDEX "main"."entity_idx"
ON "expert_hub_auditlog" (
  "entity_type" ASC,
  "entity_id" ASC
);
CREATE INDEX "main"."expert_hub__assessm_7afb14_idx"
ON "expert_hub_assessments" (
  "assessment_number" ASC
);
CREATE INDEX "main"."expert_hub__assessm_7d7358_idx"
ON "expert_hub_gutachten" (
  "assessment_id" ASC
);
CREATE INDEX "main"."expert_hub__ausgabe_68bc40_idx"
ON "expert_hub_regulation" (
  "ausgabedatum" DESC
);
CREATE INDEX "main"."expert_hub__bezeich_6abfa0_idx"
ON "expert_hub_equipment" (
  "bezeichnung" ASC
);
CREATE INDEX "main"."expert_hub__created_b4cdd3_idx"
ON "expert_hub_equipment" (
  "created_at" DESC
);
CREATE INDEX "main"."expert_hub__created_b7b6f4_idx"
ON "expert_hub_assessments" (
  "created_at" ASC
);
CREATE INDEX "main"."expert_hub__current_15fc22_idx"
ON "expert_hub_assessments" (
  "current_phase" ASC
);
CREATE INDEX "main"."expert_hub__custome_f8359e_idx"
ON "expert_hub_assessments" (
  "customer_id" ASC,
  "status" ASC
);
CREATE INDEX "main"."expert_hub__erstell_221019_idx"
ON "expert_hub_gutachten" (
  "erstellt_am" DESC
);
CREATE INDEX "main"."expert_hub__geraete_4a0306_idx"
ON "expert_hub_equipment" (
  "geraetekategorie_id" ASC
);
CREATE INDEX "main"."expert_hub__gutacht_061747_idx"
ON "expert_hub_gutachten" (
  "gutachten_nummer" ASC
);
CREATE INDEX "main"."expert_hub__herstel_e03b0f_idx"
ON "expert_hub_equipment" (
  "hersteller" ASC,
  "modell" ASC
);
CREATE INDEX "main"."expert_hub__regulat_3bdd6a_idx"
ON "expert_hub_regulation" (
  "regulation_type_id" ASC,
  "nummer" ASC
);
CREATE INDEX "main"."expert_hub__status_3a3e35_idx"
ON "expert_hub_regulation" (
  "status" ASC,
  "relevanz_explosionsschutz" ASC
);
CREATE INDEX "main"."expert_hub__status_53c2a7_idx"
ON "expert_hub_equipment" (
  "status" ASC,
  "created_at" DESC
);
CREATE INDEX "main"."expert_hub__status_5d2680_idx"
ON "expert_hub_gutachten" (
  "status" ASC,
  "erstellt_am" DESC
);
CREATE INDEX "main"."expert_hub__vollsta_e9180a_idx"
ON "expert_hub_regulation" (
  "vollstaendige_bezeichnung" ASC
);
CREATE INDEX "main"."expert_hub_assessments_created_by_id_b56e1274"
ON "expert_hub_assessments" (
  "created_by_id" ASC
);
CREATE INDEX "main"."expert_hub_assessments_customer_id_c94207e1"
ON "expert_hub_assessments" (
  "customer_id" ASC
);
CREATE INDEX "main"."expert_hub_assessments_domain_art_id_8cf566d5"
ON "expert_hub_assessments" (
  "domain_art_id" ASC
);
CREATE INDEX "main"."expert_hub_assessments_domain_type_id_feeba2ec"
ON "expert_hub_assessments" (
  "domain_type_id" ASC
);
CREATE INDEX "main"."expert_hub_assessments_lead_assessor_id_ab9c4534"
ON "expert_hub_assessments" (
  "lead_assessor_id" ASC
);
CREATE INDEX "main"."expert_hub_assessments_location_id_38407ff3"
ON "expert_hub_assessments" (
  "location_id" ASC
);
CREATE INDEX "main"."expert_hub_assessments_team_members_assessment_id_61b1df9d"
ON "expert_hub_assessments_team_members" (
  "assessment_id" ASC
);
CREATE UNIQUE INDEX "main"."expert_hub_assessments_team_members_assessment_id_user_id_4a6365dc_uniq"
ON "expert_hub_assessments_team_members" (
  "assessment_id" ASC,
  "user_id" ASC
);
CREATE INDEX "main"."expert_hub_assessments_team_members_user_id_b8e64836"
ON "expert_hub_assessments_team_members" (
  "user_id" ASC
);
CREATE INDEX "main"."expert_hub_auditlog_action_98eaab45"
ON "expert_hub_auditlog" (
  "action" ASC
);
CREATE INDEX "main"."expert_hub_auditlog_compliance_relevant_c0b9d4d2"
ON "expert_hub_auditlog" (
  "compliance_relevant" ASC
);
CREATE INDEX "main"."expert_hub_auditlog_document_id_b5a5420c"
ON "expert_hub_auditlog" (
  "document_id" ASC
);
CREATE INDEX "main"."expert_hub_auditlog_entity_id_a8bf75c1"
ON "expert_hub_auditlog" (
  "entity_id" ASC
);
CREATE INDEX "main"."expert_hub_auditlog_entity_type_789469ab"
ON "expert_hub_auditlog" (
  "entity_type" ASC
);
CREATE INDEX "main"."expert_hub_auditlog_human_verified_84a81112"
ON "expert_hub_auditlog" (
  "human_verified" ASC
);
CREATE INDEX "main"."expert_hub_auditlog_is_ai_generated_c64e0a56"
ON "expert_hub_auditlog" (
  "is_ai_generated" ASC
);
CREATE INDEX "main"."expert_hub_auditlog_session_id_43fd3f5e"
ON "expert_hub_auditlog" (
  "session_id" ASC
);
CREATE INDEX "main"."expert_hub_auditlog_timestamp_bbf5f67f"
ON "expert_hub_auditlog" (
  "timestamp" ASC
);
CREATE INDEX "main"."expert_hub_auditlog_user_id_208175e4"
ON "expert_hub_auditlog" (
  "user_id" ASC
);
CREATE INDEX "main"."expert_hub_auditlog_verified_by_id_dc3952aa"
ON "expert_hub_auditlog" (
  "verified_by_id" ASC
);
CREATE INDEX "main"."expert_hub_auditlog_workflow_id_180d1d49"
ON "expert_hub_auditlog" (
  "workflow_id" ASC
);
CREATE INDEX "main"."expert_hub_building_location_id_2162a456"
ON "expert_hub_building" (
  "location_id" ASC
);
CREATE INDEX "main"."expert_hub_building_name_0e2122a1"
ON "expert_hub_building" (
  "name" ASC
);
CREATE INDEX "main"."expert_hub_data_source_metric_source_ts_idx"
ON "expert_hub_data_source_metric" (
  "source" ASC,
  "timestamp" DESC
);
CREATE INDEX "main"."expert_hub_data_source_metric_success_ts_idx"
ON "expert_hub_data_source_metric" (
  "success" ASC,
  "timestamp" DESC
);
CREATE INDEX "main"."expert_hub_data_source_metric_timestamp_idx"
ON "expert_hub_data_source_metric" (
  "timestamp" ASC
);
CREATE INDEX "main"."expert_hub_equipment_bezeichnung_cd44673f"
ON "expert_hub_equipment" (
  "bezeichnung" ASC
);
CREATE INDEX "main"."expert_hub_equipment_created_by_id_7bab3bb0"
ON "expert_hub_equipment" (
  "created_by_id" ASC
);
CREATE INDEX "main"."expert_hub_equipment_ersetzt_durch_id_ca4b91ed"
ON "expert_hub_equipment" (
  "ersetzt_durch_id" ASC
);
CREATE INDEX "main"."expert_hub_equipment_explosionsgruppe_id_a8bebf61"
ON "expert_hub_equipment" (
  "explosionsgruppe_id" ASC
);
CREATE INDEX "main"."expert_hub_equipment_facility_id_2ba567c2"
ON "expert_hub_equipment" (
  "facility_id" ASC
);
CREATE INDEX "main"."expert_hub_equipment_geraetekategorie_id_fab3937d"
ON "expert_hub_equipment" (
  "geraetekategorie_id" ASC
);
CREATE INDEX "main"."expert_hub_equipment_gutachten_equipment_id_023119d9"
ON "expert_hub_equipment_gutachten" (
  "equipment_id" ASC
);
CREATE UNIQUE INDEX "main"."expert_hub_equipment_gutachten_equipment_id_explosionsschutzgutachten_id_481a2b73_uniq"
ON "expert_hub_equipment_gutachten" (
  "equipment_id" ASC,
  "explosionsschutzgutachten_id" ASC
);
CREATE INDEX "main"."expert_hub_equipment_gutachten_explosionsschutzgutachten_id_d1593095"
ON "expert_hub_equipment_gutachten" (
  "explosionsschutzgutachten_id" ASC
);
CREATE INDEX "main"."expert_hub_equipment_status_d8eaa8b6"
ON "expert_hub_equipment" (
  "status" ASC
);
CREATE INDEX "main"."expert_hub_equipment_temperaturklasse_id_51636a0f"
ON "expert_hub_equipment" (
  "temperaturklasse_id" ASC
);
CREATE INDEX "main"."expert_hub_equipment_wartungsverantwortlicher_id_840b081f"
ON "expert_hub_equipment" (
  "wartungsverantwortlicher_id" ASC
);
CREATE INDEX "main"."expert_hub_equipment_zuendschutzart_id_7b855a5a"
ON "expert_hub_equipment" (
  "zuendschutzart_id" ASC
);
CREATE INDEX "main"."expert_hub_exschutzdocument_customer_id_d92b6d36"
ON "expert_hub_exschutzdocument" (
  "customer_id" ASC
);
CREATE INDEX "main"."expert_hub_exschutzdocument_document_type_id_98b5a2ba"
ON "expert_hub_exschutzdocument" (
  "document_type_id" ASC
);
CREATE INDEX "main"."expert_hub_exschutzdocument_needs_human_review_b1c55ace"
ON "expert_hub_exschutzdocument" (
  "needs_human_review" ASC
);
CREATE INDEX "main"."expert_hub_exschutzdocument_processing_status_id_0e8f527e"
ON "expert_hub_exschutzdocument" (
  "processing_status_id" ASC
);
CREATE INDEX "main"."expert_hub_exschutzdocument_project_id_adcaf76b"
ON "expert_hub_exschutzdocument" (
  "project_id" ASC
);
CREATE INDEX "main"."expert_hub_exschutzdocument_reviewed_by_id_12d3921f"
ON "expert_hub_exschutzdocument" (
  "reviewed_by_id" ASC
);
CREATE INDEX "main"."expert_hub_exschutzdocument_uploaded_at_d2fcae47"
ON "expert_hub_exschutzdocument" (
  "uploaded_at" ASC
);
CREATE INDEX "main"."expert_hub_exschutzdocument_uploaded_by_id_35224d4d"
ON "expert_hub_exschutzdocument" (
  "uploaded_by_id" ASC
);
CREATE INDEX "main"."expert_hub_exschutzdocument_workflow_id_eca87eec"
ON "expert_hub_exschutzdocument" (
  "workflow_id" ASC
);
CREATE INDEX "main"."expert_hub_exzone_document_id_82fb43d4"
ON "expert_hub_exzone" (
  "document_id" ASC
);
CREATE INDEX "main"."expert_hub_exzone_gebaeude_id_262121d6"
ON "expert_hub_exzone" (
  "gebaeude_id" ASC
);
CREATE INDEX "main"."expert_hub_exzone_hauptgefahrstoff_id_a9f2e9ca"
ON "expert_hub_exzone" (
  "hauptgefahrstoff_id" ASC
);
CREATE INDEX "main"."expert_hub_exzone_needs_review_470cd10d"
ON "expert_hub_exzone" (
  "needs_review" ASC
);
CREATE INDEX "main"."expert_hub_exzone_reviewed_by_id_811ac23e"
ON "expert_hub_exzone" (
  "reviewed_by_id" ASC
);
CREATE INDEX "main"."expert_hub_exzone_zone_classification_id_b37ed125"
ON "expert_hub_exzone" (
  "zone_classification_id" ASC
);
CREATE INDEX "main"."expert_hub_facility_facility_type_id_29e5f157"
ON "expert_hub_facility" (
  "facility_type_id" ASC
);
CREATE INDEX "main"."expert_hub_facility_hazmat_facility_id_ffc0f30f"
ON "expert_hub_facility_hazmat" (
  "facility_id" ASC
);
CREATE UNIQUE INDEX "main"."expert_hub_facility_hazmat_facility_id_hazmat_id_1e5bed33_uniq"
ON "expert_hub_facility_hazmat" (
  "facility_id" ASC,
  "hazmat_id" ASC
);
CREATE INDEX "main"."expert_hub_facility_hazmat_hazmat_id_f082cf7d"
ON "expert_hub_facility_hazmat" (
  "hazmat_id" ASC
);
CREATE INDEX "main"."expert_hub_facility_location_id_74786af6"
ON "expert_hub_facility" (
  "location_id" ASC
);
CREATE INDEX "main"."expert_hub_facility_name_eeb54412"
ON "expert_hub_facility" (
  "name" ASC
);
CREATE INDEX "main"."expert_hub_facility_status_93883d01"
ON "expert_hub_facility" (
  "status" ASC
);
CREATE INDEX "main"."expert_hub_gefahrstoff_cas_number_08d29718"
ON "expert_hub_gefahrstoff" (
  "cas_number" ASC
);
CREATE INDEX "main"."expert_hub_gefahrstoff_document_id_5a9cc2d7"
ON "expert_hub_gefahrstoff" (
  "document_id" ASC
);
CREATE INDEX "main"."expert_hub_gefahrstoff_extracted_by_id_edb754cc"
ON "expert_hub_gefahrstoff" (
  "extracted_by_id" ASC
);
CREATE INDEX "main"."expert_hub_gefahrstoff_needs_review_cece50d9"
ON "expert_hub_gefahrstoff" (
  "needs_review" ASC
);
CREATE INDEX "main"."expert_hub_gefahrstoff_reviewed_by_id_1ed16c10"
ON "expert_hub_gefahrstoff" (
  "reviewed_by_id" ASC
);
CREATE INDEX "main"."expert_hub_gutachten_betroffene_vorschriften_explosionsschutzgutachten_id_eb416294"
ON "expert_hub_gutachten_betroffene_vorschriften" (
  "explosionsschutzgutachten_id" ASC
);
CREATE UNIQUE INDEX "main"."expert_hub_gutachten_betroffene_vorschriften_explosionsschutzgutachten_id_regulation_id_c9ad6092_uniq"
ON "expert_hub_gutachten_betroffene_vorschriften" (
  "explosionsschutzgutachten_id" ASC,
  "regulation_id" ASC
);
CREATE INDEX "main"."expert_hub_gutachten_betroffene_vorschriften_regulation_id_b6f4775d"
ON "expert_hub_gutachten_betroffene_vorschriften" (
  "regulation_id" ASC
);
CREATE INDEX "main"."expert_hub_gutachten_ersteller_id_0131b35e"
ON "expert_hub_gutachten" (
  "ersteller_id" ASC
);
CREATE INDEX "main"."expert_hub_gutachten_freigegeben_von_id_06ecfae5"
ON "expert_hub_gutachten" (
  "freigegeben_von_id" ASC
);
CREATE INDEX "main"."expert_hub_gutachten_geprueft_von_id_7ed129e4"
ON "expert_hub_gutachten" (
  "geprueft_von_id" ASC
);
CREATE INDEX "main"."expert_hub_gutachten_status_b2780fab"
ON "expert_hub_gutachten" (
  "status" ASC
);
CREATE INDEX "main"."expert_hub_hazmat_catalog_name_eb74cc48"
ON "expert_hub_hazmat_catalog" (
  "name" ASC
);
CREATE INDEX "main"."expert_hub_regulation_created_by_id_4ffdb183"
ON "expert_hub_regulation" (
  "created_by_id" ASC
);
CREATE INDEX "main"."expert_hub_regulation_ersetzt_durch_id_79b3b0dd"
ON "expert_hub_regulation" (
  "ersetzt_durch_id" ASC
);
CREATE INDEX "main"."expert_hub_regulation_nummer_a5eaeb89"
ON "expert_hub_regulation" (
  "nummer" ASC
);
CREATE INDEX "main"."expert_hub_regulation_regulation_type_id_8074c1ae"
ON "expert_hub_regulation" (
  "regulation_type_id" ASC
);
CREATE UNIQUE INDEX "main"."expert_hub_regulation_regulation_type_id_nummer_adc26fe3_uniq"
ON "expert_hub_regulation" (
  "regulation_type_id" ASC,
  "nummer" ASC
);
CREATE INDEX "main"."expert_hub_regulation_relevanz_explosionsschutz_25c0f9be"
ON "expert_hub_regulation" (
  "relevanz_explosionsschutz" ASC
);
CREATE INDEX "main"."expert_hub_regulation_status_ae80098b"
ON "expert_hub_regulation" (
  "status" ASC
);
CREATE INDEX "main"."expert_hub_regulation_verwandte_vorschriften_from_regulation_id_ddafcea6"
ON "expert_hub_regulation_verwandte_vorschriften" (
  "from_regulation_id" ASC
);
CREATE UNIQUE INDEX "main"."expert_hub_regulation_verwandte_vorschriften_from_regulation_id_to_regulation_id_e771b06f_uniq"
ON "expert_hub_regulation_verwandte_vorschriften" (
  "from_regulation_id" ASC,
  "to_regulation_id" ASC
);
CREATE INDEX "main"."expert_hub_regulation_verwandte_vorschriften_to_regulation_id_27372fef"
ON "expert_hub_regulation_verwandte_vorschriften" (
  "to_regulation_id" ASC
);
CREATE INDEX "main"."expert_hub_schutzmassnahme_document_id_bdd5d795"
ON "expert_hub_schutzmassnahme" (
  "document_id" ASC
);
CREATE INDEX "main"."expert_hub_schutzmassnahme_massnahme_typ_32cce024"
ON "expert_hub_schutzmassnahme" (
  "massnahme_typ" ASC
);
CREATE INDEX "main"."expert_hub_schutzmassnahme_needs_review_a06cc37b"
ON "expert_hub_schutzmassnahme" (
  "needs_review" ASC
);
CREATE INDEX "main"."expert_hub_schutzmassnahme_reviewed_by_id_488a70dc"
ON "expert_hub_schutzmassnahme" (
  "reviewed_by_id" ASC
);
CREATE INDEX "main"."expert_hub_substance_data_import_cas_imported_idx"
ON "expert_hub_substance_data_import" (
  "cas_number" ASC,
  "imported_at" DESC
);
CREATE INDEX "main"."expert_hub_substance_data_import_imported_by_id_idx"
ON "expert_hub_substance_data_import" (
  "imported_by_id" ASC
);
CREATE INDEX "main"."expert_hub_substance_data_import_source_imported_idx"
ON "expert_hub_substance_data_import" (
  "source_type" ASC,
  "imported_at" DESC
);
CREATE INDEX "main"."expert_hub_substance_data_import_success_imported_idx"
ON "expert_hub_substance_data_import" (
  "success" ASC,
  "imported_at" DESC
);
CREATE INDEX "main"."field_defin_name_528028_idx"
ON "field_definitions" (
  "name" ASC
);
CREATE INDEX "main"."field_defin_target__c1bdaf_idx"
ON "field_definitions" (
  "target_model" ASC,
  "is_active" ASC
);
CREATE INDEX "main"."field_definitions_created_by_id_ed223f8e"
ON "field_definitions" (
  "created_by_id" ASC
);
CREATE INDEX "main"."field_definitions_group_id_67233ebf"
ON "field_definitions" (
  "group_id" ASC
);
CREATE INDEX "main"."field_value_history_changed_by_id_15240210"
ON "field_value_history" (
  "changed_by_id" ASC
);
CREATE INDEX "main"."field_value_history_field_value_id_4ecda553"
ON "field_value_history" (
  "field_value_id" ASC
);
CREATE INDEX "main"."genagent_ac_phase_i_3cd7fa_idx"
ON "genagent_actions" (
  "phase_id" ASC,
  "order" ASC,
  "is_active" ASC
);
CREATE INDEX "main"."genagent_actions_phase_id_4c30ca17"
ON "genagent_actions" (
  "phase_id" ASC
);
CREATE INDEX "main"."genagent_cu_categor_3e096b_idx"
ON "genagent_custom_domains" (
  "category" ASC,
  "is_active" ASC
);
CREATE INDEX "main"."genagent_cu_domain__462cf8_idx"
ON "genagent_custom_domains" (
  "domain_id" ASC
);
CREATE INDEX "main"."genagent_ex_action__cef494_idx"
ON "genagent_execution_logs" (
  "action_id" ASC,
  "created_at" DESC
);
CREATE INDEX "main"."genagent_ex_status_4af2ac_idx"
ON "genagent_execution_logs" (
  "status" ASC,
  "created_at" DESC
);
CREATE INDEX "main"."genagent_execution_logs_action_id_41432599"
ON "genagent_execution_logs" (
  "action_id" ASC
);
CREATE INDEX "main"."genagent_ph_order_675106_idx"
ON "genagent_phases" (
  "order" ASC,
  "is_active" ASC
);
CREATE INDEX "main"."generated_i_book_id_74e297_idx"
ON "generated_images" (
  "book_id" ASC,
  "chapter_id" ASC,
  "scene_number" ASC
);
CREATE INDEX "main"."generated_i_is_acti_c80911_idx"
ON "generated_images" (
  "is_active" ASC,
  "created_at" DESC
);
CREATE INDEX "main"."generated_i_provide_4d6cdc_idx"
ON "generated_images" (
  "provider" ASC,
  "created_at" DESC
);
CREATE INDEX "main"."generated_images_book_id_8e009312"
ON "generated_images" (
  "book_id" ASC
);
CREATE INDEX "main"."generated_images_created_at_e4d6a029"
ON "generated_images" (
  "created_at" ASC
);
CREATE INDEX "main"."generated_images_created_by_id_ac051c44"
ON "generated_images" (
  "created_by_id" ASC
);
CREATE INDEX "main"."generated_images_handler_id_c2cbb2da"
ON "generated_images" (
  "handler_id" ASC
);
CREATE INDEX "main"."generated_images_is_active_6239b8df"
ON "generated_images" (
  "is_active" ASC
);
CREATE INDEX "main"."generated_images_provider_2d055b23"
ON "generated_images" (
  "provider" ASC
);
CREATE INDEX "main"."genres_domain__98a665_idx"
ON "genres" (
  "domain_art_id" ASC,
  "is_active" ASC
);
CREATE INDEX "main"."genres_domain_art_id_98404dd8"
ON "genres" (
  "domain_art_id" ASC
);
CREATE UNIQUE INDEX "main"."genres_domain_art_id_slug_c11cbcb9_uniq"
ON "genres" (
  "domain_art_id" ASC,
  "slug" ASC
);
CREATE INDEX "main"."genres_is_acti_9bdcd0_idx"
ON "genres" (
  "is_active" ASC,
  "sort_order" ASC
);
CREATE INDEX "main"."genres_parent_genre_id_c40038e7"
ON "genres" (
  "parent_genre_id" ASC
);
CREATE INDEX "main"."genres_slug_99e229b7"
ON "genres" (
  "slug" ASC
);
CREATE INDEX "main"."graphql_fie_last_us_1a8041_idx"
ON "graphql_field_usage" (
  "last_used" DESC
);
CREATE INDEX "main"."graphql_fie_usage_c_ead89c_idx"
ON "graphql_field_usage" (
  "usage_count" DESC
);
CREATE INDEX "main"."graphql_field_usage_field_name_c901d6b1"
ON "graphql_field_usage" (
  "field_name" ASC
);
CREATE INDEX "main"."graphql_field_usage_type_name_e412aa32"
ON "graphql_field_usage" (
  "type_name" ASC
);
CREATE UNIQUE INDEX "main"."graphql_field_usage_type_name_field_name_2ed69de4_uniq"
ON "graphql_field_usage" (
  "type_name" ASC,
  "field_name" ASC
);
CREATE INDEX "main"."graphql_ope_avg_dur_d62c40_idx"
ON "graphql_operations" (
  "avg_duration_ms" ASC
);
CREATE INDEX "main"."graphql_ope_executi_d5bfab_idx"
ON "graphql_operations" (
  "execution_count" DESC
);
CREATE INDEX "main"."graphql_ope_last_us_4f399b_idx"
ON "graphql_operations" (
  "last_used" DESC,
  "operation_type" ASC
);
CREATE INDEX "main"."graphql_operations_operation_hash_07bddc10"
ON "graphql_operations" (
  "operation_hash" ASC
);
CREATE INDEX "main"."graphql_operations_operation_name_0363a2b1"
ON "graphql_operations" (
  "operation_name" ASC
);
CREATE INDEX "main"."graphql_per_operati_c976df_idx"
ON "graphql_performance_logs" (
  "operation_id" ASC,
  "timestamp" DESC
);
CREATE INDEX "main"."graphql_per_timesta_9aff51_idx"
ON "graphql_performance_logs" (
  "timestamp" DESC
);
CREATE INDEX "main"."graphql_performance_logs_operation_id_fcdce2b8"
ON "graphql_performance_logs" (
  "operation_id" ASC
);
CREATE INDEX "main"."graphql_performance_logs_timestamp_1aa0cf3f"
ON "graphql_performance_logs" (
  "timestamp" ASC
);
CREATE INDEX "main"."handler_exe_action__158ac2_idx"
ON "handler_executions" (
  "action_handler_id" ASC,
  "started_at" DESC
);
CREATE INDEX "main"."handler_exe_project_1a4635_idx"
ON "handler_executions" (
  "project_id" ASC,
  "started_at" DESC
);
CREATE INDEX "main"."handler_exe_status_f900f7_idx"
ON "handler_executions" (
  "status" ASC,
  "started_at" DESC
);
CREATE INDEX "main"."handler_executions_action_handler_id_c4d7a3c4"
ON "handler_executions" (
  "action_handler_id" ASC
);
CREATE INDEX "main"."handler_executions_executed_by_id_e53d2d83"
ON "handler_executions" (
  "executed_by_id" ASC
);
CREATE INDEX "main"."handler_executions_llm_used_id_841f77fa"
ON "handler_executions" (
  "llm_used_id" ASC
);
CREATE INDEX "main"."handler_executions_project_id_feb13bb4"
ON "handler_executions" (
  "project_id" ASC
);
CREATE INDEX "main"."handler_executions_status_e37b694a"
ON "handler_executions" (
  "status" ASC
);
CREATE INDEX "main"."ideas_v2_books_bookproject_id_5cd060f7"
ON "ideas_v2_books" (
  "bookproject_id" ASC
);
CREATE INDEX "main"."ideas_v2_books_idea_id_299630a6"
ON "ideas_v2_books" (
  "idea_id" ASC
);
CREATE UNIQUE INDEX "main"."ideas_v2_books_idea_id_bookproject_id_36f6c98f_uniq"
ON "ideas_v2_books" (
  "idea_id" ASC,
  "bookproject_id" ASC
);
CREATE INDEX "main"."ideas_v2_created_by_id_f4b9d4a7"
ON "ideas_v2" (
  "created_by_id" ASC
);
CREATE INDEX "main"."ideas_v2_created_df2406_idx"
ON "ideas_v2" (
  "created_by_id" ASC
);
CREATE INDEX "main"."ideas_v2_status_9bd965_idx"
ON "ideas_v2" (
  "status" ASC
);
CREATE INDEX "main"."idx_building_location"
ON "expert_hub_building" (
  "location_id" ASC,
  "name" ASC
);
CREATE INDEX "main"."idx_customer_active"
ON "core_customers" (
  "is_active" ASC,
  "name" ASC
);
CREATE INDEX "main"."idx_customer_name"
ON "core_customers" (
  "name" ASC
);
CREATE INDEX "main"."idx_customer_num"
ON "core_customers" (
  "customer_number" ASC
);
CREATE INDEX "main"."idx_fachaz_facility"
ON "expert_hub_facility_hazmat" (
  "facility_id" ASC
);
CREATE INDEX "main"."idx_fachaz_hazmat"
ON "expert_hub_facility_hazmat" (
  "hazmat_id" ASC
);
CREATE INDEX "main"."idx_facility_inv"
ON "expert_hub_facility" (
  "inventory_number" ASC
);
CREATE INDEX "main"."idx_facility_location"
ON "expert_hub_facility" (
  "location_id" ASC,
  "name" ASC
);
CREATE INDEX "main"."idx_facility_status"
ON "expert_hub_facility" (
  "status" ASC
);
CREATE INDEX "main"."idx_facility_type"
ON "expert_hub_facility" (
  "facility_type_id" ASC
);
CREATE INDEX "main"."idx_hazcat_cas"
ON "expert_hub_hazmat_catalog" (
  "cas_number" ASC
);
CREATE INDEX "main"."idx_hazcat_exgroup"
ON "expert_hub_hazmat_catalog" (
  "explosion_group" ASC
);
CREATE INDEX "main"."idx_hazcat_name"
ON "expert_hub_hazmat_catalog" (
  "name" ASC
);
CREATE INDEX "main"."idx_location_active"
ON "core_locations" (
  "is_active" ASC
);
CREATE INDEX "main"."idx_location_code"
ON "core_locations" (
  "location_code" ASC
);
CREATE INDEX "main"."idx_location_customer"
ON "core_locations" (
  "customer_id" ASC,
  "name" ASC
);
CREATE INDEX "main"."llm_prompt__categor_999cba_idx"
ON "llm_prompt_templates" (
  "category" ASC,
  "is_active" ASC
);
CREATE INDEX "main"."llm_prompt__llm_id_bed547_idx"
ON "llm_prompt_executions" (
  "llm_id" ASC,
  "started_at" DESC
);
CREATE INDEX "main"."llm_prompt__prompt__31843c_idx"
ON "llm_prompt_executions" (
  "prompt_id" ASC,
  "started_at" DESC
);
CREATE INDEX "main"."llm_prompt__prompt__e79d19_idx"
ON "llm_prompt_templates" (
  "prompt_id" ASC
);
CREATE INDEX "main"."llm_prompt__status_9d979d_idx"
ON "llm_prompt_executions" (
  "status" ASC,
  "started_at" DESC
);
CREATE INDEX "main"."llm_prompt__total_u_f53b70_idx"
ON "llm_prompt_templates" (
  "total_uses" DESC
);
CREATE INDEX "main"."llm_prompt_executions_executed_by_id_d754f13b"
ON "llm_prompt_executions" (
  "executed_by_id" ASC
);
CREATE INDEX "main"."llm_prompt_executions_llm_id_985d4b80"
ON "llm_prompt_executions" (
  "llm_id" ASC
);
CREATE INDEX "main"."llm_prompt_executions_prompt_id_64515e91"
ON "llm_prompt_executions" (
  "prompt_id" ASC
);
CREATE INDEX "main"."llm_prompt_executions_status_432b76da"
ON "llm_prompt_executions" (
  "status" ASC
);
CREATE INDEX "main"."llm_prompt_templates_category_fa4b6d5a"
ON "llm_prompt_templates" (
  "category" ASC
);
CREATE INDEX "main"."llm_prompt_templates_created_by_id_31b8c07a"
ON "llm_prompt_templates" (
  "created_by_id" ASC
);
CREATE INDEX "main"."llm_prompt_templates_is_active_b83d15ce"
ON "llm_prompt_templates" (
  "is_active" ASC
);
CREATE UNIQUE INDEX "main"."llm_prompt_templates_prompt_id_variant_c09cbb20_uniq"
ON "llm_prompt_templates" (
  "prompt_id" ASC,
  "variant" ASC
);
CREATE INDEX "main"."llm_prompt_templates_replacement_prompt_id_5db53cda"
ON "llm_prompt_templates" (
  "replacement_prompt_id" ASC
);
CREATE INDEX "main"."locations_parent_location_id_7bb36098"
ON "locations" (
  "parent_location_id" ASC
);
CREATE INDEX "main"."locations_world_id_aac1a8b1"
ON "locations" (
  "world_id" ASC
);
CREATE INDEX "main"."massnahme_review_idx"
ON "expert_hub_schutzmassnahme" (
  "needs_review" ASC
);
CREATE INDEX "main"."massnahme_status_idx"
ON "expert_hub_schutzmassnahme" (
  "status" ASC
);
CREATE INDEX "main"."medtrans_customers_user_id_f69f5cc7"
ON "medtrans_customers" (
  "user_id" ASC
);
CREATE INDEX "main"."medtrans_pr_present_296fd2_idx"
ON "medtrans_presentation_texts" (
  "presentation_id" ASC,
  "translation_method" ASC
);
CREATE INDEX "main"."medtrans_pr_present_a431bb_idx"
ON "medtrans_presentation_texts" (
  "presentation_id" ASC,
  "slide_number" ASC
);
CREATE INDEX "main"."medtrans_presentation_texts_presentation_id_2a748594"
ON "medtrans_presentation_texts" (
  "presentation_id" ASC
);
CREATE UNIQUE INDEX "main"."medtrans_presentation_texts_presentation_id_text_id_d4e92044_uniq"
ON "medtrans_presentation_texts" (
  "presentation_id" ASC,
  "text_id" ASC
);
CREATE INDEX "main"."medtrans_presentations_customer_id_38cc8243"
ON "medtrans_presentations" (
  "customer_id" ASC
);
CREATE INDEX "main"."navigation_items_code_idx"
ON "navigation_items" (
  "code" ASC
);
CREATE INDEX "main"."navigation_items_domains_navigationitem_id_67e6620d"
ON "navigation_items_domains" (
  "navigationitem_id" ASC
);
CREATE UNIQUE INDEX "main"."navigation_items_domains_navigationitem_id_workflowdomain_id_8221f67a_uniq"
ON "navigation_items_domains" (
  "navigationitem_id" ASC,
  "workflowdomain_id" ASC
);
CREATE INDEX "main"."navigation_items_domains_workflowdomain_id_11d91214"
ON "navigation_items_domains" (
  "workflowdomain_id" ASC
);
CREATE INDEX "main"."navigation_items_is_active_idx"
ON "navigation_items" (
  "is_active" ASC
);
CREATE INDEX "main"."navigation_items_order_idx"
ON "navigation_items" (
  "order" ASC
);
CREATE INDEX "main"."navigation_items_parent_id_idx"
ON "navigation_items" (
  "parent_id" ASC
);
CREATE INDEX "main"."navigation_items_required_groups_group_id_f3038baf"
ON "navigation_items_required_groups" (
  "group_id" ASC
);
CREATE INDEX "main"."navigation_items_required_groups_navigationitem_id_eebc8734"
ON "navigation_items_required_groups" (
  "navigationitem_id" ASC
);
CREATE UNIQUE INDEX "main"."navigation_items_required_groups_navigationitem_id_group_id_f65f8040_uniq"
ON "navigation_items_required_groups" (
  "navigationitem_id" ASC,
  "group_id" ASC
);
CREATE INDEX "main"."navigation_items_required_permissions_navigationitem_id_14edd041"
ON "navigation_items_required_permissions" (
  "navigationitem_id" ASC
);
CREATE UNIQUE INDEX "main"."navigation_items_required_permissions_navigationitem_id_permission_id_0d85ee79_uniq"
ON "navigation_items_required_permissions" (
  "navigationitem_id" ASC,
  "permission_id" ASC
);
CREATE INDEX "main"."navigation_items_required_permissions_permission_id_2cd3a360"
ON "navigation_items_required_permissions" (
  "permission_id" ASC
);
CREATE UNIQUE INDEX "main"."navigation_items_section_code_unique"
ON "navigation_items" (
  "section_id" ASC,
  "code" ASC
);
CREATE INDEX "main"."navigation_items_section_id_idx"
ON "navigation_items" (
  "section_id" ASC
);
CREATE INDEX "main"."navigation_sections_code_idx"
ON "navigation_sections" (
  "code" ASC
);
CREATE UNIQUE INDEX "main"."navigation_sections_code_unique"
ON "navigation_sections" (
  "code" ASC
);
CREATE INDEX "main"."navigation_sections_domains_navigationsection_id_aaeb4da8"
ON "navigation_sections_domains" (
  "navigationsection_id" ASC
);
CREATE UNIQUE INDEX "main"."navigation_sections_domains_navigationsection_id_workflowdomain_id_cd5e94ad_uniq"
ON "navigation_sections_domains" (
  "navigationsection_id" ASC,
  "workflowdomain_id" ASC
);
CREATE INDEX "main"."navigation_sections_domains_workflowdomain_id_4f38b02e"
ON "navigation_sections_domains" (
  "workflowdomain_id" ASC
);
CREATE INDEX "main"."navigation_sections_is_active_idx"
ON "navigation_sections" (
  "is_active" ASC
);
CREATE INDEX "main"."navigation_sections_order_idx"
ON "navigation_sections" (
  "order" ASC
);
CREATE INDEX "main"."navigation_sections_required_groups_group_id_41f0e8ef"
ON "navigation_sections_required_groups" (
  "group_id" ASC
);
CREATE INDEX "main"."navigation_sections_required_groups_navigationsection_id_7d0523fa"
ON "navigation_sections_required_groups" (
  "navigationsection_id" ASC
);
CREATE UNIQUE INDEX "main"."navigation_sections_required_groups_navigationsection_id_group_id_4da414ac_uniq"
ON "navigation_sections_required_groups" (
  "navigationsection_id" ASC,
  "group_id" ASC
);
CREATE INDEX "main"."navigation_sections_required_permissions_navigationsection_id_e239da60"
ON "navigation_sections_required_permissions" (
  "navigationsection_id" ASC
);
CREATE UNIQUE INDEX "main"."navigation_sections_required_permissions_navigationsection_id_permission_id_af6d89f0_uniq"
ON "navigation_sections_required_permissions" (
  "navigationsection_id" ASC,
  "permission_id" ASC
);
CREATE INDEX "main"."navigation_sections_required_permissions_permission_id_8e6265c7"
ON "navigation_sections_required_permissions" (
  "permission_id" ASC
);
CREATE INDEX "main"."phase_action_configs_action_id_6247e482"
ON "phase_action_configs" (
  "action_id" ASC
);
CREATE INDEX "main"."phase_action_configs_phase_id_4adc200d"
ON "phase_action_configs" (
  "phase_id" ASC
);
CREATE UNIQUE INDEX "main"."phase_action_configs_phase_id_action_id_fa2ac745_uniq"
ON "phase_action_configs" (
  "phase_id" ASC,
  "action_id" ASC
);
CREATE INDEX "main"."phase_agent_configs_agent_id_8804d447"
ON "phase_agent_configs" (
  "agent_id" ASC
);
CREATE UNIQUE INDEX "main"."phase_agent_configs_phase_id_agent_id_4f60953b_uniq"
ON "phase_agent_configs" (
  "phase_id" ASC,
  "agent_id" ASC
);
CREATE INDEX "main"."phase_agent_configs_phase_id_f6956e67"
ON "phase_agent_configs" (
  "phase_id" ASC
);
CREATE INDEX "main"."presentatio_client_664c13_idx"
ON "presentation_studio_template_collection" (
  "client" ASC
);
CREATE INDEX "main"."presentatio_enhance_13c0c5_idx"
ON "presentation_studio_presentation" (
  "enhancement_status" ASC
);
CREATE INDEX "main"."presentatio_enhance_a77e6d_idx"
ON "presentation_studio_enhancement" (
  "enhancement_type" ASC
);
CREATE INDEX "main"."presentatio_industr_0f6158_idx"
ON "presentation_studio_template_collection" (
  "industry" ASC
);
CREATE INDEX "main"."presentatio_is_acti_9d00ca_idx"
ON "presentation_studio_template_collection" (
  "is_active" ASC,
  "is_default" ASC
);
CREATE INDEX "main"."presentatio_is_syst_b7bbe3_idx"
ON "presentation_studio_design_profile" (
  "is_system_template" ASC
);
CREATE INDEX "main"."presentatio_present_3bcbb2_idx"
ON "presentation_studio_preview_slide" (
  "presentation_id" ASC,
  "status" ASC
);
CREATE INDEX "main"."presentatio_present_7120c8_idx"
ON "presentation_studio_enhancement" (
  "presentation_id" ASC,
  "executed_at" DESC
);
CREATE INDEX "main"."presentatio_present_c4d4a6_idx"
ON "presentation_studio_preview_slide" (
  "presentation_id" ASC,
  "preview_order" ASC
);
CREATE INDEX "main"."presentatio_source__1b715e_idx"
ON "presentation_studio_design_profile" (
  "source_type" ASC
);
CREATE INDEX "main"."presentatio_uploade_b0dc07_idx"
ON "presentation_studio_presentation" (
  "uploaded_by_id" ASC,
  "uploaded_at" DESC
);
CREATE INDEX "main"."presentation_studio_design_profile_created_by_id_6469b538"
ON "presentation_studio_design_profile" (
  "created_by_id" ASC
);
CREATE INDEX "main"."presentation_studio_design_profile_presentation_id_f9de8cba"
ON "presentation_studio_design_profile" (
  "presentation_id" ASC
);
CREATE INDEX "main"."presentation_studio_enhancement_executed_by_id_094cd913"
ON "presentation_studio_enhancement" (
  "executed_by_id" ASC
);
CREATE INDEX "main"."presentation_studio_enhancement_presentation_id_201a590d"
ON "presentation_studio_enhancement" (
  "presentation_id" ASC
);
CREATE INDEX "main"."presentation_studio_presentation_enhancement_status_c94a1987"
ON "presentation_studio_presentation" (
  "enhancement_status" ASC
);
CREATE INDEX "main"."presentation_studio_presentation_template_collection_id_97f51c8f"
ON "presentation_studio_presentation" (
  "template_collection_id" ASC
);
CREATE INDEX "main"."presentation_studio_presentation_uploaded_by_id_6ce48f70"
ON "presentation_studio_presentation" (
  "uploaded_by_id" ASC
);
CREATE INDEX "main"."presentation_studio_preview_slide_presentation_id_fe893b87"
ON "presentation_studio_preview_slide" (
  "presentation_id" ASC
);
CREATE INDEX "main"."presentation_studio_preview_slide_status_175d3e9d"
ON "presentation_studio_preview_slide" (
  "status" ASC
);
CREATE INDEX "main"."presentation_studio_template_collection_created_by_id_7ed92b6a"
ON "presentation_studio_template_collection" (
  "created_by_id" ASC
);
CREATE INDEX "main"."project_fie_project_78279a_idx"
ON "project_field_values" (
  "project_id" ASC,
  "field_definition_id" ASC
);
CREATE INDEX "main"."project_field_values_field_definition_id_b7c4f52e"
ON "project_field_values" (
  "field_definition_id" ASC
);
CREATE INDEX "main"."project_field_values_project_id_42a790c7"
ON "project_field_values" (
  "project_id" ASC
);
CREATE UNIQUE INDEX "main"."project_field_values_project_id_field_definition_id_2d712908_uniq"
ON "project_field_values" (
  "project_id" ASC,
  "field_definition_id" ASC
);
CREATE INDEX "main"."project_field_values_updated_by_id_903ad678"
ON "project_field_values" (
  "updated_by_id" ASC
);
CREATE INDEX "main"."project_pha_project_77f25d_idx"
ON "project_phase_history" (
  "project_id" ASC,
  "entered_at" DESC
);
CREATE INDEX "main"."project_pha_projekt_1c8daf_idx"
ON "project_phase_actions" (
  "projektart" ASC,
  "projekttyp" ASC,
  "projektphase_id" ASC
);
CREATE INDEX "main"."project_pha_projekt_4dd39a_idx"
ON "project_phase_actions" (
  "projektart" ASC,
  "projekttyp" ASC
);
CREATE INDEX "main"."project_pha_projekt_8bbc0e_idx"
ON "project_phase_actions" (
  "projektart" ASC
);
CREATE INDEX "main"."project_phase_actions_action_id_481262c0"
ON "project_phase_actions" (
  "action_id" ASC
);
CREATE UNIQUE INDEX "main"."project_phase_actions_projektart_projekttyp_projektphase_id_action_id_d47e3008_uniq"
ON "project_phase_actions" (
  "projektart" ASC,
  "projekttyp" ASC,
  "projektphase_id" ASC,
  "action_id" ASC
);
CREATE INDEX "main"."project_phase_actions_projektphase_id_e0edfbc5"
ON "project_phase_actions" (
  "projektphase_id" ASC
);
CREATE INDEX "main"."project_phase_history_phase_id_7953db92"
ON "project_phase_history" (
  "phase_id" ASC
);
CREATE INDEX "main"."project_phase_history_project_id_01240a3b"
ON "project_phase_history" (
  "project_id" ASC
);
CREATE INDEX "main"."project_phase_history_workflow_step_id_b3c5401e"
ON "project_phase_history" (
  "workflow_step_id" ASC
);
CREATE INDEX "main"."project_typ_projekt_67fbbb_idx"
ON "project_type_phases" (
  "projektart" ASC
);
CREATE INDEX "main"."project_typ_projekt_84d59b_idx"
ON "project_type_phases" (
  "projektart" ASC,
  "projekttyp" ASC
);
CREATE UNIQUE INDEX "main"."project_type_phases_projektart_projekttyp_projektphase_id_ca77a6ac_uniq"
ON "project_type_phases" (
  "projektart" ASC,
  "projekttyp" ASC,
  "projektphase_id" ASC
);
CREATE INDEX "main"."project_type_phases_projektphase_id_a3bfd24f"
ON "project_type_phases" (
  "projektphase_id" ASC
);
CREATE INDEX "main"."prompt_exec_project_4ebcb8_idx"
ON "prompt_executions" (
  "project_id" ASC,
  "created_at" ASC
);
CREATE INDEX "main"."prompt_exec_status_26fa8b_idx"
ON "prompt_executions" (
  "status" ASC,
  "created_at" ASC
);
CREATE INDEX "main"."prompt_exec_templat_7cc92b_idx"
ON "prompt_executions" (
  "template_id" ASC,
  "status" ASC
);
CREATE INDEX "main"."prompt_exec_user_ac_f23b6c_idx"
ON "prompt_executions" (
  "user_accepted" ASC
);
CREATE INDEX "main"."prompt_executions_agent_id_464f6ba5"
ON "prompt_executions" (
  "agent_id" ASC
);
CREATE INDEX "main"."prompt_executions_project_id_9a703b09"
ON "prompt_executions" (
  "project_id" ASC
);
CREATE INDEX "main"."prompt_executions_retry_of_id_fa02fb51"
ON "prompt_executions" (
  "retry_of_id" ASC
);
CREATE INDEX "main"."prompt_executions_template_id_17f29cb0"
ON "prompt_executions" (
  "template_id" ASC
);
CREATE INDEX "main"."prompt_template_tests_template_id_42dd7b08"
ON "prompt_template_tests" (
  "template_id" ASC
);
CREATE INDEX "main"."prompt_templates_legacy_agent_id_343034d5"
ON "prompt_templates_legacy" (
  "agent_id" ASC
);
CREATE UNIQUE INDEX "main"."prompt_templates_legacy_agent_id_name_version_a4cf09ca_uniq"
ON "prompt_templates_legacy" (
  "agent_id" ASC,
  "name" ASC,
  "version" ASC
);
CREATE INDEX "main"."research_citation_style_lookup_is_active_be91e631"
ON "research_citation_style_lookup" (
  "is_active" ASC
);
CREATE INDEX "main"."research_depth_lookup_is_active_33af42f5"
ON "research_depth_lookup" (
  "is_active" ASC
);
CREATE INDEX "main"."research_focus_lookup_is_active_9880e694"
ON "research_focus_lookup" (
  "is_active" ASC
);
CREATE INDEX "main"."research_handler_type_lookup_is_active_92530619"
ON "research_handler_type_lookup" (
  "is_active" ASC
);
CREATE INDEX "main"."research_re_session_4ec110_idx"
ON "research_researchhandlerexecution" (
  "session_id" ASC,
  "handler_type_id" ASC
);
CREATE INDEX "main"."research_re_session_fa08d4_idx"
ON "research_researchsource" (
  "session_id" ASC,
  "source_type_id" ASC
);
CREATE INDEX "main"."research_re_started_ffead9_idx"
ON "research_researchhandlerexecution" (
  "started_at" ASC
);
CREATE INDEX "main"."research_re_url_5bc658_idx"
ON "research_researchsource" (
  "url" ASC
);
CREATE INDEX "main"."research_researchhandlerexecution_handler_type_id_e7faf3cc"
ON "research_researchhandlerexecution" (
  "handler_type_id" ASC
);
CREATE INDEX "main"."research_researchhandlerexecution_session_id_1bce2cd0"
ON "research_researchhandlerexecution" (
  "session_id" ASC
);
CREATE INDEX "main"."research_researchproject_default_depth_id_9ae03c54"
ON "research_researchproject" (
  "default_depth_id" ASC
);
CREATE INDEX "main"."research_researchproject_owner_id_f4887f9d"
ON "research_researchproject" (
  "owner_id" ASC
);
CREATE INDEX "main"."research_researchproject_status_d64d66cf"
ON "research_researchproject" (
  "status" ASC
);
CREATE INDEX "main"."research_researchresult_citation_style_id_59dace46"
ON "research_researchresult" (
  "citation_style_id" ASC
);
CREATE INDEX "main"."research_researchresult_synthesis_type_id_87d314a4"
ON "research_researchresult" (
  "synthesis_type_id" ASC
);
CREATE INDEX "main"."research_researchsession_depth_id_00bba639"
ON "research_researchsession" (
  "depth_id" ASC
);
CREATE INDEX "main"."research_researchsession_project_id_bbbb2fd0"
ON "research_researchsession" (
  "project_id" ASC
);
CREATE INDEX "main"."research_researchsession_status_d3544030"
ON "research_researchsession" (
  "status" ASC
);
CREATE INDEX "main"."research_researchsource_session_id_6d48d1b2"
ON "research_researchsource" (
  "session_id" ASC
);
CREATE INDEX "main"."research_researchsource_source_type_id_618c3b7f"
ON "research_researchsource" (
  "source_type_id" ASC
);
CREATE INDEX "main"."research_source_type_lookup_is_active_53907271"
ON "research_source_type_lookup" (
  "is_active" ASC
);
CREATE INDEX "main"."research_synthesis_type_lookup_is_active_5585e770"
ON "research_synthesis_type_lookup" (
  "is_active" ASC
);
CREATE INDEX "main"."review_status_idx"
ON "expert_hub_gefahrstoff" (
  "needs_review" ASC,
  "approved" ASC
);
CREATE INDEX "main"."status_review_idx"
ON "expert_hub_exschutzdocument" (
  "processing_status_id" ASC,
  "needs_human_review" ASC
);
CREATE INDEX "main"."story_bibles_created_by_id_3732dc25"
ON "story_bibles" (
  "created_by_id" ASC
);
CREATE INDEX "main"."story_bibles_domain_project_id_3f5493a3"
ON "story_bibles" (
  "domain_project_id" ASC
);
CREATE INDEX "main"."template_fields_field_id_988731fc"
ON "template_fields" (
  "field_id" ASC
);
CREATE INDEX "main"."template_fields_template_id_3d289b9c"
ON "template_fields" (
  "template_id" ASC
);
CREATE UNIQUE INDEX "main"."template_fields_template_id_field_id_16d6f84c_uniq"
ON "template_fields" (
  "template_id" ASC,
  "field_id" ASC
);
CREATE INDEX "main"."tool_defini_categor_a4f6d2_idx"
ON "tool_definitions" (
  "category" ASC,
  "status" ASC
);
CREATE INDEX "main"."tool_defini_tool_id_3896f0_idx"
ON "tool_definitions" (
  "tool_id" ASC
);
CREATE INDEX "main"."tool_defini_total_e_4abadf_idx"
ON "tool_definitions" (
  "total_executions" DESC
);
CREATE INDEX "main"."tool_definitions_category_b7473024"
ON "tool_definitions" (
  "category" ASC
);
CREATE INDEX "main"."tool_definitions_created_by_id_84b47f69"
ON "tool_definitions" (
  "created_by_id" ASC
);
CREATE INDEX "main"."tool_definitions_status_65b1ec01"
ON "tool_definitions" (
  "status" ASC
);
CREATE INDEX "main"."tool_execut_status_0c276d_idx"
ON "tool_executions" (
  "status" ASC,
  "started_at" DESC
);
CREATE INDEX "main"."tool_execut_tool_id_c05db9_idx"
ON "tool_executions" (
  "tool_id" ASC,
  "started_at" DESC
);
CREATE INDEX "main"."tool_executions_executed_by_id_1b3775c1"
ON "tool_executions" (
  "executed_by_id" ASC
);
CREATE INDEX "main"."tool_executions_status_0ec892b0"
ON "tool_executions" (
  "status" ASC
);
CREATE INDEX "main"."tool_executions_tool_id_9eddbc90"
ON "tool_executions" (
  "tool_id" ASC
);
CREATE INDEX "main"."user_navigation_preferences_section_id_98e971ec"
ON "user_navigation_preferences" (
  "section_id" ASC
);
CREATE INDEX "main"."user_navigation_preferences_user_id_b3914478"
ON "user_navigation_preferences" (
  "user_id" ASC
);
CREATE UNIQUE INDEX "main"."user_navigation_preferences_user_id_section_id_5a78f2de_uniq"
ON "user_navigation_preferences" (
  "user_id" ASC,
  "section_id" ASC
);
CREATE INDEX "main"."user_time_idx"
ON "expert_hub_auditlog" (
  "user_id" ASC,
  "timestamp" ASC
);
CREATE INDEX "main"."user_upload_idx"
ON "expert_hub_exschutzdocument" (
  "uploaded_by_id" ASC,
  "uploaded_at" ASC
);
CREATE INDEX "main"."workflow_domains_created_by_id_f9d587ca"
ON "workflow_domains" (
  "created_by_id" ASC
);
CREATE INDEX "main"."workflow_phase_steps_phase_id_8b05ba32"
ON "workflow_phase_steps" (
  "phase_id" ASC
);
CREATE INDEX "main"."workflow_phase_steps_template_id_afe27baa"
ON "workflow_phase_steps" (
  "template_id" ASC
);
CREATE UNIQUE INDEX "main"."workflow_phase_steps_template_id_order_bce620b4_uniq"
ON "workflow_phase_steps" (
  "template_id" ASC,
  "order" ASC
);
CREATE UNIQUE INDEX "main"."workflow_phase_steps_template_id_phase_id_d4ba7233_uniq"
ON "workflow_phase_steps" (
  "template_id" ASC,
  "phase_id" ASC
);
CREATE INDEX "main"."workflow_sy_created_02a38d_idx"
ON "workflow_system_workflow" (
  "created_by_id" ASC,
  "status" ASC
);
CREATE INDEX "main"."workflow_sy_created_1bd21b_idx"
ON "workflow_system_workflow" (
  "created_at" DESC
);
CREATE INDEX "main"."workflow_sy_domain__5fc6b5_idx"
ON "workflow_system_workflow" (
  "domain_id" ASC,
  "status" ASC
);
CREATE INDEX "main"."workflow_sy_workflo_115dd2_idx"
ON "workflow_system_checkpoint" (
  "workflow_id" ASC,
  "status" ASC
);
CREATE INDEX "main"."workflow_sy_workflo_25e7f4_idx"
ON "workflow_system_checkpoint" (
  "workflow_id" ASC,
  "phase_order" ASC,
  "action_order" ASC
);
CREATE INDEX "main"."workflow_system_checkpoint_status_053ed5b0"
ON "workflow_system_checkpoint" (
  "status" ASC
);
CREATE INDEX "main"."workflow_system_checkpoint_workflow_id_8bd40e4e"
ON "workflow_system_checkpoint" (
  "workflow_id" ASC
);
CREATE INDEX "main"."workflow_system_workflow_created_at_aeac618d"
ON "workflow_system_workflow" (
  "created_at" ASC
);
CREATE INDEX "main"."workflow_system_workflow_created_by_id_b91f8cd3"
ON "workflow_system_workflow" (
  "created_by_id" ASC
);
CREATE INDEX "main"."workflow_system_workflow_domain_id_76a56154"
ON "workflow_system_workflow" (
  "domain_id" ASC
);
CREATE INDEX "main"."workflow_system_workflow_status_c2bb0ea2"
ON "workflow_system_workflow" (
  "status" ASC
);
CREATE INDEX "main"."workflow_system_workflow_template_id_b298ae65"
ON "workflow_system_workflow" (
  "template_id" ASC
);
CREATE INDEX "main"."workflow_templates_book_type_id_c7d24d47"
ON "workflow_templates" (
  "book_type_id" ASC
);
CREATE UNIQUE INDEX "main"."workflow_templates_book_type_id_name_f27e69cb_uniq"
ON "workflow_templates" (
  "book_type_id" ASC,
  "name" ASC
);
CREATE INDEX "main"."workflow_templates_v2_created_by_id_37692696"
ON "workflow_templates_v2" (
  "created_by_id" ASC
);
CREATE INDEX "main"."workflow_templates_v2_project_type_id_4662ed81"
ON "workflow_templates_v2" (
  "project_type_id" ASC
);
CREATE INDEX "main"."world_rules_world_id_c3eb0556"
ON "world_rules" (
  "world_id" ASC
);
CREATE INDEX "main"."worlds_v2_books_bookproject_id_35bd5206"
ON "worlds_v2_books" (
  "bookproject_id" ASC
);
CREATE INDEX "main"."worlds_v2_books_world_id_535d00d4"
ON "worlds_v2_books" (
  "world_id" ASC
);
CREATE UNIQUE INDEX "main"."worlds_v2_books_world_id_bookproject_id_8bd00f10_uniq"
ON "worlds_v2_books" (
  "world_id" ASC,
  "bookproject_id" ASC
);
CREATE INDEX "main"."worlds_v2_created_by_id_d68c4631"
ON "worlds_v2" (
  "created_by_id" ASC
);
CREATE INDEX "main"."writing_boo_created_8ebbad_idx"
ON "writing_book_projects" (
  "created_at" DESC
);
CREATE INDEX "main"."writing_boo_genre_i_02e7e0_idx"
ON "writing_book_projects" (
  "genre_id" ASC,
  "status_id" ASC
);
CREATE INDEX "main"."writing_boo_owner_i_3fb748_idx"
ON "writing_book_projects" (
  "owner_id" ASC,
  "created_at" DESC
);
CREATE INDEX "main"."writing_book_projects_book_type_id_bce2a22e"
ON "writing_book_projects" (
  "book_type_id" ASC
);
CREATE INDEX "main"."writing_book_projects_current_phase_step_id_a43dd065"
ON "writing_book_projects" (
  "current_phase_step_id" ASC
);
CREATE INDEX "main"."writing_book_projects_current_workflow_phase_id_5ebdb555"
ON "writing_book_projects" (
  "current_workflow_phase_id" ASC
);
CREATE INDEX "main"."writing_book_projects_genre_id_4c75531a"
ON "writing_book_projects" (
  "genre_id" ASC
);
CREATE INDEX "main"."writing_book_projects_owner_id_f39ba12a"
ON "writing_book_projects" (
  "owner_id" ASC
);
CREATE INDEX "main"."writing_book_projects_status_id_34d6e47e"
ON "writing_book_projects" (
  "status_id" ASC
);
CREATE INDEX "main"."writing_book_projects_user_id_19750375"
ON "writing_book_projects" (
  "user_id" ASC
);
CREATE INDEX "main"."writing_book_projects_workflow_template_id_5fbe0570"
ON "writing_book_projects" (
  "workflow_template_id" ASC
);
CREATE INDEX "main"."writing_cha_content_52a4da_idx"
ON "writing_chapters" (
  "content_hash" ASC
);
CREATE INDEX "main"."writing_cha_project_bb160a_idx"
ON "writing_chapters" (
  "project_id" ASC,
  "chapter_number" ASC
);
CREATE INDEX "main"."writing_cha_writing_5f2e22_idx"
ON "writing_chapters" (
  "writing_stage" ASC
);
CREATE INDEX "main"."writing_chapters_content_hash_d2e8319e"
ON "writing_chapters" (
  "content_hash" ASC
);
CREATE INDEX "main"."writing_chapters_featured_characters_bookchapters_id_70d33d90"
ON "writing_chapters_featured_characters" (
  "bookchapters_id" ASC
);
CREATE UNIQUE INDEX "main"."writing_chapters_featured_characters_bookchapters_id_characters_id_d153b1ae_uniq"
ON "writing_chapters_featured_characters" (
  "bookchapters_id" ASC,
  "characters_id" ASC
);
CREATE INDEX "main"."writing_chapters_featured_characters_characters_id_de4cc650"
ON "writing_chapters_featured_characters" (
  "characters_id" ASC
);
CREATE INDEX "main"."writing_chapters_plot_points_bookchapters_id_e713eb4b"
ON "writing_chapters_plot_points" (
  "bookchapters_id" ASC
);
CREATE UNIQUE INDEX "main"."writing_chapters_plot_points_bookchapters_id_plotpoint_id_91472809_uniq"
ON "writing_chapters_plot_points" (
  "bookchapters_id" ASC,
  "plotpoint_id" ASC
);
CREATE INDEX "main"."writing_chapters_plot_points_plotpoint_id_d3f2f2cc"
ON "writing_chapters_plot_points" (
  "plotpoint_id" ASC
);
CREATE INDEX "main"."writing_chapters_project_id_58043465"
ON "writing_chapters" (
  "project_id" ASC
);
CREATE UNIQUE INDEX "main"."writing_chapters_project_id_chapter_number_1d4fef32_uniq"
ON "writing_chapters" (
  "project_id" ASC,
  "chapter_number" ASC
);
CREATE INDEX "main"."writing_chapters_story_arc_id_044c9bbf"
ON "writing_chapters" (
  "story_arc_id" ASC
);
CREATE INDEX "main"."writing_characters_project_id_18c2ef87"
ON "writing_characters" (
  "project_id" ASC
);
CREATE INDEX "main"."writing_gen_status_b1b9c1_idx"
ON "writing_generation_logs" (
  "status" ASC,
  "started_at" DESC
);
CREATE INDEX "main"."writing_gen_story_c_bcf05c_idx"
ON "writing_generation_logs" (
  "story_chapter_id" ASC,
  "started_at" DESC
);
CREATE INDEX "main"."writing_generation_logs_llm_id_af1276ee"
ON "writing_generation_logs" (
  "llm_id" ASC
);
CREATE INDEX "main"."writing_generation_logs_status_b8063f22"
ON "writing_generation_logs" (
  "status" ASC
);
CREATE INDEX "main"."writing_generation_logs_story_chapter_id_a0782d83"
ON "writing_generation_logs" (
  "story_chapter_id" ASC
);
CREATE INDEX "main"."writing_plot_points_involved_characters_characters_id_0f1174a8"
ON "writing_plot_points_involved_characters" (
  "characters_id" ASC
);
CREATE INDEX "main"."writing_plot_points_involved_characters_plotpoint_id_9748ab16"
ON "writing_plot_points_involved_characters" (
  "plotpoint_id" ASC
);
CREATE UNIQUE INDEX "main"."writing_plot_points_involved_characters_plotpoint_id_characters_id_cbc211b6_uniq"
ON "writing_plot_points_involved_characters" (
  "plotpoint_id" ASC,
  "characters_id" ASC
);
CREATE INDEX "main"."writing_plot_points_project_id_b5d23131"
ON "writing_plot_points" (
  "project_id" ASC
);
CREATE UNIQUE INDEX "main"."writing_plot_points_story_arc_id_chapter_number_sequence_order_9ec2197b_uniq"
ON "writing_plot_points" (
  "story_arc_id" ASC,
  "chapter_number" ASC,
  "sequence_order" ASC
);
CREATE INDEX "main"."writing_plot_points_story_arc_id_e7155a3e"
ON "writing_plot_points" (
  "story_arc_id" ASC
);
CREATE INDEX "main"."writing_sto_chapter_eed7c1_idx"
ON "writing_story_memories" (
  "chapter_id" ASC
);
CREATE INDEX "main"."writing_sto_importa_1ff0da_idx"
ON "writing_story_memories" (
  "importance" DESC
);
CREATE INDEX "main"."writing_sto_slug_ad6118_idx"
ON "writing_story_projects" (
  "slug" ASC
);
CREATE INDEX "main"."writing_sto_status_68a9e0_idx"
ON "writing_story_projects" (
  "status" ASC,
  "created_at" DESC
);
CREATE INDEX "main"."writing_sto_story_p_529781_idx"
ON "writing_story_chapters" (
  "story_project_id" ASC,
  "status" ASC
);
CREATE INDEX "main"."writing_sto_story_p_89bf9f_idx"
ON "writing_story_strands" (
  "story_project_id" ASC,
  "sort_order" ASC
);
CREATE INDEX "main"."writing_sto_story_p_ff6e88_idx"
ON "writing_story_memories" (
  "story_project_id" ASC,
  "memory_type" ASC
);
CREATE INDEX "main"."writing_sto_strand__4d6362_idx"
ON "writing_story_chapters" (
  "strand_id" ASC,
  "chapter_number" ASC
);
CREATE INDEX "main"."writing_story_arcs_project_id_90b8ae7f"
ON "writing_story_arcs" (
  "project_id" ASC
);
CREATE UNIQUE INDEX "main"."writing_story_arcs_project_id_name_5ca7a658_uniq"
ON "writing_story_arcs" (
  "project_id" ASC,
  "name" ASC
);
CREATE INDEX "main"."writing_story_chapters_status_f3d50630"
ON "writing_story_chapters" (
  "status" ASC
);
CREATE INDEX "main"."writing_story_chapters_story_project_id_64868d65"
ON "writing_story_chapters" (
  "story_project_id" ASC
);
CREATE UNIQUE INDEX "main"."writing_story_chapters_story_project_id_volume_number_chapter_number_af40bb35_uniq"
ON "writing_story_chapters" (
  "story_project_id" ASC,
  "volume_number" ASC,
  "chapter_number" ASC
);
CREATE INDEX "main"."writing_story_chapters_strand_id_ac74e011"
ON "writing_story_chapters" (
  "strand_id" ASC
);
CREATE INDEX "main"."writing_story_memories_chapter_id_20f06b55"
ON "writing_story_memories" (
  "chapter_id" ASC
);
CREATE INDEX "main"."writing_story_memories_characters_involved_characters_id_5929de99"
ON "writing_story_memories_characters_involved" (
  "characters_id" ASC
);
CREATE INDEX "main"."writing_story_memories_characters_involved_storymemory_id_a07881cc"
ON "writing_story_memories_characters_involved" (
  "storymemory_id" ASC
);
CREATE UNIQUE INDEX "main"."writing_story_memories_characters_involved_storymemory_id_characters_id_6a90b3a0_uniq"
ON "writing_story_memories_characters_involved" (
  "storymemory_id" ASC,
  "characters_id" ASC
);
CREATE INDEX "main"."writing_story_memories_memory_type_eeda48e1"
ON "writing_story_memories" (
  "memory_type" ASC
);
CREATE INDEX "main"."writing_story_memories_revealed_in_chapter_id_d6f69506"
ON "writing_story_memories" (
  "revealed_in_chapter_id" ASC
);
CREATE INDEX "main"."writing_story_memories_story_project_id_78153f1b"
ON "writing_story_memories" (
  "story_project_id" ASC
);
CREATE INDEX "main"."writing_story_memories_strand_id_591439b7"
ON "writing_story_memories" (
  "strand_id" ASC
);
CREATE INDEX "main"."writing_story_projects_created_by_id_10fce650"
ON "writing_story_projects" (
  "created_by_id" ASC
);
CREATE INDEX "main"."writing_story_projects_llm_model_id_01b921db"
ON "writing_story_projects" (
  "llm_model_id" ASC
);
CREATE INDEX "main"."writing_story_projects_status_a9a7b1c5"
ON "writing_story_projects" (
  "status" ASC
);
CREATE INDEX "main"."writing_story_projects_story_bible_id_74ffe186"
ON "writing_story_projects" (
  "story_bible_id" ASC
);
CREATE INDEX "main"."writing_story_strands_converges_with_from_storystrand_id_5fc04ee2"
ON "writing_story_strands_converges_with" (
  "from_storystrand_id" ASC
);
CREATE UNIQUE INDEX "main"."writing_story_strands_converges_with_from_storystrand_id_to_storystrand_id_d874771b_uniq"
ON "writing_story_strands_converges_with" (
  "from_storystrand_id" ASC,
  "to_storystrand_id" ASC
);
CREATE INDEX "main"."writing_story_strands_converges_with_to_storystrand_id_972630b2"
ON "writing_story_strands_converges_with" (
  "to_storystrand_id" ASC
);
CREATE INDEX "main"."writing_story_strands_primary_character_id_bff94ba5"
ON "writing_story_strands" (
  "primary_character_id" ASC
);
CREATE INDEX "main"."writing_story_strands_secondary_characters_characters_id_b9c6bb54"
ON "writing_story_strands_secondary_characters" (
  "characters_id" ASC
);
CREATE INDEX "main"."writing_story_strands_secondary_characters_storystrand_id_9328053f"
ON "writing_story_strands_secondary_characters" (
  "storystrand_id" ASC
);
CREATE UNIQUE INDEX "main"."writing_story_strands_secondary_characters_storystrand_id_characters_id_f14e00f2_uniq"
ON "writing_story_strands_secondary_characters" (
  "storystrand_id" ASC,
  "characters_id" ASC
);
CREATE INDEX "main"."writing_story_strands_story_project_id_b0053152"
ON "writing_story_strands" (
  "story_project_id" ASC
);
CREATE UNIQUE INDEX "main"."writing_story_strands_story_project_id_code_b14613ad_uniq"
ON "writing_story_strands" (
  "story_project_id" ASC,
  "code" ASC
);
CREATE INDEX "main"."writing_worlds_project_id_8af8963a"
ON "writing_worlds" (
  "project_id" ASC
);
CREATE INDEX "main"."zone_review_idx"
ON "expert_hub_exzone" (
  "needs_review" ASC
);
