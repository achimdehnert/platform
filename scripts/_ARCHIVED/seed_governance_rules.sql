-- ============================================================================
-- SEED GOVERNANCE RULES (ADR-015 Phase 3)
-- ============================================================================

DO $$
DECLARE
    v_enforcement_block BIGINT;
    v_enforcement_warn BIGINT;
    v_enforcement_log BIGINT;
BEGIN
    SELECT id INTO v_enforcement_block FROM platform.lkp_choice WHERE domain = 'enforcement' AND code = 'block';
    SELECT id INTO v_enforcement_warn FROM platform.lkp_choice WHERE domain = 'enforcement' AND code = 'warn';
    SELECT id INTO v_enforcement_log FROM platform.lkp_choice WHERE domain = 'enforcement' AND code = 'log';

    -- ========================================================================
    -- ACCESS RULES
    -- ========================================================================
    
    INSERT INTO platform.gov_access_rule (name, code, description, target_type, target_pattern, allowed_accessors, access_method, enforcement_id)
    VALUES
    ('LLM Access via Gateway Only', 'llm_gateway_only', 
     'All LLM calls must go through llm_mcp. Never import openai or anthropic directly.',
     'integration', 'anthropic|openai', 
     ARRAY['llm_mcp', 'mcp_core.llm_gateway'], 
     'Use llm_mcp tools: llm_complete, llm_stream, llm_chat',
     v_enforcement_block),
    
    ('Database via Django ORM', 'db_via_orm',
     'Database access via Django ORM or LookupService. No raw psycopg2 in application code.',
     'integration', 'psycopg2|asyncpg',
     ARRAY['migrations', 'management/commands', 'governance.services'],
     'Use Django models or LookupService',
     v_enforcement_warn),
    
    ('Registry Check Before Implementation', 'registry_check_first',
     'Check registry_mcp.check_existing before implementing new functionality.',
     'module', '*',
     ARRAY['*'],
     'Call registry_mcp.check_existing(functionality) first',
     v_enforcement_log)
    ON CONFLICT (code) DO NOTHING;

    -- ========================================================================
    -- IMPORT RULES
    -- ========================================================================
    
    INSERT INTO platform.gov_import_rule (name, code, description, forbidden_import, import_pattern, applies_to, exceptions, alternative_fqn, alternative_usage, enforcement_id)
    VALUES
    ('No Direct Anthropic Import', 'no_anthropic_direct',
     'Never import anthropic library directly. Use llm_mcp gateway.',
     'anthropic', 'import anthropic|from anthropic',
     ARRAY['*'],
     ARRAY['llm_mcp', 'mcp_core'],
     'llm_mcp.llm_complete',
     'Use llm_mcp tools: llm_complete(model="claude-sonnet-4-5", messages=[...])',
     v_enforcement_block),
    
    ('No Direct OpenAI Import', 'no_openai_direct',
     'Never import openai library directly. Use llm_mcp gateway.',
     'openai', 'import openai|from openai',
     ARRAY['*'],
     ARRAY['llm_mcp', 'mcp_core'],
     'llm_mcp.llm_complete',
     'Use llm_mcp tools: llm_complete(model="gpt-4o", messages=[...])',
     v_enforcement_block),
    
    ('No Hardcoded Choices', 'no_hardcoded_choices',
     'Use LookupService instead of hardcoded string choices.',
     'STATUS_CHOICES|PRIORITY_CHOICES',
     'CHOICES\\s*=\\s*\\[',
     ARRAY['models.py'],
     ARRAY['governance.models'],
     'apps.governance.services.LookupService',
     'STATUS_CHOICES = LookupService.get_for_django_choices("status")',
     v_enforcement_warn)
    ON CONFLICT (code) DO NOTHING;

    -- ========================================================================
    -- PATTERN RULES
    -- ========================================================================
    
    INSERT INTO platform.gov_pattern_rule (name, code, description, trigger_keywords, trigger_context, pattern_fqn, pattern_usage, antipattern_regex, enforcement_id)
    VALUES
    ('Use LookupService for Enums', 'use_lookup_service',
     'Use database-driven lookups instead of Python enums.',
     ARRAY['enum', 'Enum', 'choices', 'CHOICES', 'STATUS_', 'PRIORITY_'],
     'When defining model field choices or status values',
     'apps.governance.services.LookupService',
     'choices = LookupService.get_for_django_choices("domain_code")',
     'class\\s+\\w+\\(.*Enum.*\\)|CHOICES\\s*=\\s*\\[\\s*\\(',
     v_enforcement_warn),
    
    ('Use Prompt Framework', 'use_prompt_framework',
     'Use PromptFrameworkService for LLM prompts instead of inline strings.',
     ARRAY['prompt', 'system_message', 'user_message', 'template'],
     'When constructing prompts for LLM calls',
     'apps.core.services.prompt_framework.PromptFrameworkService',
     'prompt = PromptFrameworkService.render("template_name", context)',
     'f""".*system.*"""',
     v_enforcement_log)
    ON CONFLICT (code) DO NOTHING;

END $$;
