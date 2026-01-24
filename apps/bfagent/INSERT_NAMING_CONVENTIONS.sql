-- ============================================================================
-- BF Agent - Naming Conventions Integration
-- ============================================================================
-- Fügt alle Naming Conventions aus dem BF Agent Projekt in die Tabelle ein
-- Run: python apply_naming_conventions.py

-- Delete existing entries first (for re-runs)
DELETE FROM core_naming_convention;

-- ============================================================================
-- CORE & BASE APPS
-- ============================================================================

-- BF Agent Core
INSERT INTO core_naming_convention (
    app_label, display_name, table_prefix, class_prefix,
    table_pattern, class_pattern, file_pattern,
    description, example_tables, example_classes,
    is_active, enforce_convention, created_at, updated_at
) VALUES (
    'bfagent', 'BF Agent', '', '',
    '{name}', '{Name}', 'models*.py',
    'Hauptapp für Buch-Projekte, Agents, Handler ohne Präfix',
    '["book_projects", "agents", "book_chapters", "story_arcs", "plot_points"]',
    '["BookProject", "Agent", "BookChapter", "StoryArc", "PlotPoint"]',
    1, 0, datetime('now'), datetime('now')
);

-- Core System
INSERT INTO core_naming_convention (
    app_label, display_name, table_prefix, class_prefix,
    table_pattern, class_pattern, file_pattern,
    description, example_tables, example_classes,
    is_active, enforce_convention, created_at, updated_at
) VALUES (
    'core', 'Core System', 'core_', 'Core',
    'core_{name}', 'Core{Name}', 'models.py',
    'Core Domain Models mit core_ Präfix',
    '["core_domain", "core_handler", "core_phase"]',
    '["CoreDomain", "CoreHandler", "CorePhase"]',
    1, 1, datetime('now'), datetime('now')
);

-- BF Agent MCP Server
INSERT INTO core_naming_convention (
    app_label, display_name, table_prefix, class_prefix,
    table_pattern, class_pattern, file_pattern,
    description, example_tables, example_classes,
    is_active, enforce_convention, created_at, updated_at
) VALUES (
    'bfagent_mcp', 'BF Agent MCP', 'mcp_', 'MCP',
    'mcp_{name}', 'MCP{Name}', '*.py',
    'MCP Server Models - alle mit mcp_ Präfix für sofortige Erkennung',
    '["mcp_domain_config", "mcp_protected_path", "mcp_risk_level", "mcp_component_type"]',
    '["MCPDomainConfig", "MCPProtectedPath", "MCPRiskLevel", "MCPComponentType"]',
    1, 1, datetime('now'), datetime('now')
);

-- ============================================================================
-- HUB APPS
-- ============================================================================

-- GenAgent (Generator Agent)
INSERT INTO core_naming_convention (
    app_label, display_name, table_prefix, class_prefix,
    table_pattern, class_pattern, file_pattern,
    description, example_tables, example_classes,
    is_active, enforce_convention, created_at, updated_at
) VALUES (
    'genagent', 'GenAgent', 'genagent_', 'GenAgent',
    'genagent_{name}', 'GenAgent{Name}', 'models.py',
    'Generator Agent mit genagent_ Präfix für Phasen, Actions, Logs',
    '["genagent_phases", "genagent_actions", "genagent_execution_logs", "genagent_custom_domains"]',
    '["GenAgentPhase", "GenAgentAction", "GenAgentExecutionLog", "GenAgentCustomDomain"]',
    1, 1, datetime('now'), datetime('now')
);

-- Writing Hub
INSERT INTO core_naming_convention (
    app_label, display_name, table_prefix, class_prefix,
    table_pattern, class_pattern, file_pattern,
    description, example_tables, example_classes,
    is_active, enforce_convention, created_at, updated_at
) VALUES (
    'writing_hub', 'Writing Hub', 'writing_', 'Writing',
    'writing_{name}', 'Writing{Name}', 'models*.py',
    'Writing Hub für Bücher, Kapitel, Charaktere',
    '["writing_projects", "writing_chapters", "writing_characters", "writing_worlds"]',
    '["WritingProject", "WritingChapter", "WritingCharacter", "WritingWorld"]',
    1, 0, datetime('now'), datetime('now')
);

-- Control Center
INSERT INTO core_naming_convention (
    app_label, display_name, table_prefix, class_prefix,
    table_pattern, class_pattern, file_pattern,
    description, example_tables, example_classes,
    is_active, enforce_convention, created_at, updated_at
) VALUES (
    'control_center', 'Control Center', '', '',
    '{name}', '{Name}', 'models*.py',
    'Control Center - verschiedene Präfixe je nach Feature (navigation_, workflow_)',
    '["navigation_sections", "navigation_items", "workflow_domains", "project_types"]',
    '["NavigationSection", "NavigationItem", "WorkflowDomain", "ProjectType"]',
    1, 0, datetime('now'), datetime('now')
);

-- Hub (Main Hub)
INSERT INTO core_naming_convention (
    app_label, display_name, table_prefix, class_prefix,
    table_pattern, class_pattern, file_pattern,
    description, example_tables, example_classes,
    is_active, enforce_convention, created_at, updated_at
) VALUES (
    'hub', 'Hub', 'hub_', 'Hub',
    'hub_{name}', 'Hub{Name}', 'models.py',
    'Main Hub App',
    '["hub_settings", "hub_navigation"]',
    '["HubSettings", "HubNavigation"]',
    1, 0, datetime('now'), datetime('now')
);

-- ============================================================================
-- SPECIALIZED APPS
-- ============================================================================

-- Medical Translation (MedTrans)
INSERT INTO core_naming_convention (
    app_label, display_name, table_prefix, class_prefix,
    table_pattern, class_pattern, file_pattern,
    description, example_tables, example_classes,
    is_active, enforce_convention, created_at, updated_at
) VALUES (
    'medtrans', 'Medical Translation', 'medtrans_', 'MedTrans',
    'medtrans_{name}', 'MedTrans{Name}', 'models.py',
    'Medical Translation CRM mit medtrans_ Präfix',
    '["medtrans_customers", "medtrans_presentations", "medtrans_presentation_texts"]',
    '["MedTransCustomer", "MedTransPresentation", "MedTransPresentationText"]',
    1, 1, datetime('now'), datetime('now')
);

-- Presentation Studio
INSERT INTO core_naming_convention (
    app_label, display_name, table_prefix, class_prefix,
    table_pattern, class_pattern, file_pattern,
    description, example_tables, example_classes,
    is_active, enforce_convention, created_at, updated_at
) VALUES (
    'presentation_studio', 'Presentation Studio', 'presentation_studio_', 'PresentationStudio',
    'presentation_studio_{name}', 'PresentationStudio{Name}', 'models.py',
    'PowerPoint Enhancement mit presentation_studio_ Präfix',
    '["presentation_studio_presentation", "presentation_studio_enhancement", "presentation_studio_preview_slide"]',
    '["PresentationStudioPresentation", "PresentationStudioEnhancement", "PresentationStudioPreviewSlide"]',
    1, 1, datetime('now'), datetime('now')
);

-- Image Generation
INSERT INTO core_naming_convention (
    app_label, display_name, table_prefix, class_prefix,
    table_pattern, class_pattern, file_pattern,
    description, example_tables, example_classes,
    is_active, enforce_convention, created_at, updated_at
) VALUES (
    'image_generation', 'Image Generation', 'image_', 'Image',
    'image_{name}', 'Image{Name}', 'models*.py',
    'Image Generation Models',
    '["image_generation_request", "image_styles"]',
    '["ImageGenerationRequest", "ImageStyle"]',
    1, 0, datetime('now'), datetime('now')
);

-- CAD Analysis
INSERT INTO core_naming_convention (
    app_label, display_name, table_prefix, class_prefix,
    table_pattern, class_pattern, file_pattern,
    description, example_tables, example_classes,
    is_active, enforce_convention, created_at, updated_at
) VALUES (
    'cad_analysis', 'CAD Analysis', 'cad_', 'CAD',
    'cad_{name}', 'CAD{Name}', 'models.py',
    'CAD Analysis Domain',
    '["cad_analysis_job", "cad_drawing_file", "cad_analysis_result"]',
    '["CADAnalysisJob", "CADDrawingFile", "CADAnalysisResult"]',
    1, 1, datetime('now'), datetime('now')
);

-- Expert Hub
INSERT INTO core_naming_convention (
    app_label, display_name, table_prefix, class_prefix,
    table_pattern, class_pattern, file_pattern,
    description, example_tables, example_classes,
    is_active, enforce_convention, created_at, updated_at
) VALUES (
    'expert_hub', 'Expert Hub', 'expert_', 'Expert',
    'expert_{name}', 'Expert{Name}', 'models*.py',
    'Expert Hub für Explosionsschutz und andere Expertisen',
    '["expert_document", "expert_gefahrstoff", "expert_ex_zone"]',
    '["ExpertDocument", "ExpertGefahrstoff", "ExpertExZone"]',
    1, 0, datetime('now'), datetime('now')
);

-- Checklist System
INSERT INTO core_naming_convention (
    app_label, display_name, table_prefix, class_prefix,
    table_pattern, class_pattern, file_pattern,
    description, example_tables, example_classes,
    is_active, enforce_convention, created_at, updated_at
) VALUES (
    'checklist_system', 'Checklist System', 'checklist_', 'Checklist',
    'checklist_{name}', 'Checklist{Name}', 'models.py',
    'Checklist System für Projektphasen',
    '["checklist_templates", "checklist_items", "checklist_instances"]',
    '["ChecklistTemplate", "ChecklistItem", "ChecklistInstance"]',
    1, 1, datetime('now'), datetime('now')
);

-- Compliance Core
INSERT INTO core_naming_convention (
    app_label, display_name, table_prefix, class_prefix,
    table_pattern, class_pattern, file_pattern,
    description, example_tables, example_classes,
    is_active, enforce_convention, created_at, updated_at
) VALUES (
    'compliance_core', 'Compliance Core', 'compliance_', 'Compliance',
    'compliance_{name}', 'Compliance{Name}', 'models.py',
    'Compliance Framework Core',
    '["compliance_risk_level", "compliance_status", "compliance_incident"]',
    '["ComplianceRiskLevel", "ComplianceStatus", "ComplianceIncident"]',
    1, 1, datetime('now'), datetime('now')
);

-- DSB (Datenschutzbeauftragter / DSGVO)
INSERT INTO core_naming_convention (
    app_label, display_name, table_prefix, class_prefix,
    table_pattern, class_pattern, file_pattern,
    description, example_tables, example_classes,
    is_active, enforce_convention, created_at, updated_at
) VALUES (
    'dsb', 'DSGVO Hub', 'dsb_', 'DSB',
    'dsb_{name}', 'DSB{Name}', 'models*.py',
    'DSGVO/Datenschutz Domain mit dsb_ Präfix',
    '["dsb_customer", "dsb_processing_activity", "dsb_data_breach"]',
    '["DSBCustomer", "DSBProcessingActivity", "DSBDataBreach"]',
    1, 1, datetime('now'), datetime('now')
);

-- API
INSERT INTO core_naming_convention (
    app_label, display_name, table_prefix, class_prefix,
    table_pattern, class_pattern, file_pattern,
    description, example_tables, example_classes,
    is_active, enforce_convention, created_at, updated_at
) VALUES (
    'api', 'API', 'api_', 'API',
    'api_{name}', 'API{Name}', 'models.py',
    'REST API Models',
    '["api_token", "api_request_log"]',
    '["APIToken", "APIRequestLog"]',
    1, 0, datetime('now'), datetime('now')
);

-- Workflow System
INSERT INTO core_naming_convention (
    app_label, display_name, table_prefix, class_prefix,
    table_pattern, class_pattern, file_pattern,
    description, example_tables, example_classes,
    is_active, enforce_convention, created_at, updated_at
) VALUES (
    'workflow_system', 'Workflow System', 'workflow_', 'Workflow',
    'workflow_{name}', 'Workflow{Name}', 'models.py',
    'Workflow Orchestration System',
    '["workflow_definition", "workflow_instance", "workflow_task"]',
    '["WorkflowDefinition", "WorkflowInstance", "WorkflowTask"]',
    1, 1, datetime('now'), datetime('now')
);
