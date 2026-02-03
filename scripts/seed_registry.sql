-- ============================================================================
-- SEED REGISTRY DATA (ADR-015 Phase 2)
-- ============================================================================

-- Get lookup choice IDs for FKs
DO $$
DECLARE
    v_status_production BIGINT;
    v_status_development BIGINT;
    v_status_beta BIGINT;
    v_category_core BIGINT;
    v_category_integration BIGINT;
    v_category_utility BIGINT;
    v_owner_architect BIGINT;
    v_service_type_internal BIGINT;
BEGIN
    SELECT id INTO v_status_production FROM platform.lkp_choice WHERE domain = 'status' AND code = 'production';
    SELECT id INTO v_status_development FROM platform.lkp_choice WHERE domain = 'status' AND code = 'development';
    SELECT id INTO v_status_beta FROM platform.lkp_choice WHERE domain = 'status' AND code = 'beta';
    SELECT id INTO v_category_core FROM platform.lkp_choice WHERE domain = 'category' AND code = 'core';
    SELECT id INTO v_category_integration FROM platform.lkp_choice WHERE domain = 'category' AND code = 'integration';
    SELECT id INTO v_category_utility FROM platform.lkp_choice WHERE domain = 'category' AND code = 'utility';
    SELECT id INTO v_owner_architect FROM platform.lkp_choice WHERE domain = 'owner' AND code = 'architect';
    SELECT id INTO v_service_type_internal FROM platform.lkp_choice WHERE domain = 'service_type' AND code = 'internal';

    -- Seed MCP Servers
    INSERT INTO platform.reg_mcp_server (name, display_name, description, when_to_use, repository, path, category_id, status_id, owner_id, port)
    VALUES
    ('llm_mcp', 'LLM Gateway', 'Unified LLM access for all AI providers (Anthropic, OpenAI)', 
     'Use for ALL LLM calls. Never import openai or anthropic directly.', 
     'mcp-hub', 'llm_mcp/', v_category_core, v_status_production, v_owner_architect, 8001),
    ('orchestrator_mcp', 'AI Orchestrator', 'Task analysis, cost estimation, approval gates (ADR-014)', 
     'Use for task routing, cost estimates, and approval gate checks.', 
     'mcp-hub', 'orchestrator_mcp/', v_category_core, v_status_production, v_owner_architect, 8000),
    ('deployment_mcp', 'Deployment Manager', 'Docker, Hetzner, PostgreSQL operations', 
     'Use for server management, container ops, database operations.', 
     'mcp-hub', 'deployment_mcp/', v_category_integration, v_status_production, v_owner_architect, 8002),
    ('github_mcp', 'GitHub Integration', 'GitHub API operations (issues, PRs, repos)', 
     'Use for GitHub repository operations.', 
     'mcp-hub', 'github_mcp/', v_category_integration, v_status_production, v_owner_architect, NULL),
    ('filesystem_mcp', 'Filesystem Access', 'Safe file system operations', 
     'Use for reading/writing files in allowed directories.', 
     'mcp-hub', 'filesystem_mcp/', v_category_utility, v_status_production, v_owner_architect, NULL),
    ('test_generator_mcp', 'Test Generator', 'Automated test generation for Python code', 
     'Use to generate pytest tests for existing code.', 
     'mcp-hub', 'test_generator_mcp/', v_category_utility, v_status_beta, v_owner_architect, NULL),
    ('code_quality_mcp', 'Code Quality', 'Code analysis and quality metrics', 
     'Use for code reviews and quality checks.', 
     'mcp-hub', 'code_quality_mcp/', v_category_utility, v_status_beta, v_owner_architect, NULL),
    ('illustration_mcp', 'Illustration', 'Image generation via DALL-E/Midjourney', 
     'Use for generating images and illustrations.', 
     'mcp-hub', 'illustration_mcp/', v_category_integration, v_status_production, v_owner_architect, NULL)
    ON CONFLICT (name) DO NOTHING;

    -- Seed Services
    INSERT INTO platform.reg_service (name, code, fqn, service_type_id, description, module_path, status_id, owner_id, is_singleton, direct_access_allowed, access_via_fqn)
    VALUES
    ('LookupService', 'lookup_service', 'apps.governance.services.LookupService', v_service_type_internal,
     'Database-driven lookup choices. Replaces hardcoded enums.', 
     'apps/governance/services/lookup_service.py', v_status_production, v_owner_architect, true, true, NULL),
    ('PromptFrameworkService', 'prompt_service', 'apps.core.services.prompt_framework.PromptFrameworkService', v_service_type_internal,
     'Prompt template management with Jinja2 rendering.', 
     'apps/core/services/prompt_framework/service.py', v_status_production, v_owner_architect, true, true, NULL)
    ON CONFLICT (code) DO NOTHING;

END $$;
