-- Seed LLM providers and models
INSERT INTO platform.lkp_choice (domain_id, domain, code, name, sort_order, is_system, metadata) VALUES
((SELECT id FROM platform.lkp_domain WHERE code='llm_provider'), 'llm_provider', 'anthropic', 'Anthropic', 10, true, '{}'),
((SELECT id FROM platform.lkp_domain WHERE code='llm_provider'), 'llm_provider', 'openai', 'OpenAI', 20, true, '{}'),
((SELECT id FROM platform.lkp_domain WHERE code='llm_provider'), 'llm_provider', 'azure_openai', 'Azure OpenAI', 30, true, '{}')
ON CONFLICT (domain, code) DO NOTHING;

INSERT INTO platform.lkp_choice (domain_id, domain, code, name, sort_order, is_system, metadata) VALUES
((SELECT id FROM platform.lkp_domain WHERE code='llm_model'), 'llm_model', 'claude-opus-4-5', 'Claude Opus 4.5', 10, true, 
 '{"provider": "anthropic", "model_id": "claude-opus-4-5-20250514", "context_window": 200000, "cost_input": 15.0, "cost_output": 75.0, "tier": "premium"}'),
((SELECT id FROM platform.lkp_domain WHERE code='llm_model'), 'llm_model', 'claude-sonnet-4-5', 'Claude Sonnet 4.5', 20, true,
 '{"provider": "anthropic", "model_id": "claude-sonnet-4-5-20250514", "context_window": 200000, "cost_input": 3.0, "cost_output": 15.0, "tier": "standard"}'),
((SELECT id FROM platform.lkp_domain WHERE code='llm_model'), 'llm_model', 'claude-haiku-4-5', 'Claude Haiku 4.5', 30, true,
 '{"provider": "anthropic", "model_id": "claude-haiku-4-5-20250514", "context_window": 200000, "cost_input": 0.25, "cost_output": 1.25, "tier": "economy"}'),
((SELECT id FROM platform.lkp_domain WHERE code='llm_model'), 'llm_model', 'gpt-4o', 'GPT-4o', 40, true,
 '{"provider": "openai", "model_id": "gpt-4o", "context_window": 128000, "cost_input": 2.5, "cost_output": 10.0, "tier": "standard"}')
ON CONFLICT (domain, code) DO NOTHING;

-- Seed handler types
INSERT INTO platform.lkp_choice (domain_id, domain, code, name, sort_order, is_system) VALUES
((SELECT id FROM platform.lkp_domain WHERE code='handler_type'), 'handler_type', 'event', 'Event Handler', 10, true),
((SELECT id FROM platform.lkp_domain WHERE code='handler_type'), 'handler_type', 'request', 'Request Handler', 20, true),
((SELECT id FROM platform.lkp_domain WHERE code='handler_type'), 'handler_type', 'signal', 'Signal Handler', 30, true),
((SELECT id FROM platform.lkp_domain WHERE code='handler_type'), 'handler_type', 'task', 'Task Handler', 40, true),
((SELECT id FROM platform.lkp_domain WHERE code='handler_type'), 'handler_type', 'webhook', 'Webhook Handler', 50, true)
ON CONFLICT (domain, code) DO NOTHING;

-- Seed service types
INSERT INTO platform.lkp_choice (domain_id, domain, code, name, sort_order, is_system) VALUES
((SELECT id FROM platform.lkp_domain WHERE code='service_type'), 'service_type', 'internal', 'Internal Service', 10, true),
((SELECT id FROM platform.lkp_domain WHERE code='service_type'), 'service_type', 'external', 'External Service', 20, true),
((SELECT id FROM platform.lkp_domain WHERE code='service_type'), 'service_type', 'hybrid', 'Hybrid Service', 30, true)
ON CONFLICT (domain, code) DO NOTHING;

-- Seed class types
INSERT INTO platform.lkp_choice (domain_id, domain, code, name, sort_order, is_system) VALUES
((SELECT id FROM platform.lkp_domain WHERE code='class_type'), 'class_type', 'class', 'Class', 10, true),
((SELECT id FROM platform.lkp_domain WHERE code='class_type'), 'class_type', 'function', 'Function', 20, true),
((SELECT id FROM platform.lkp_domain WHERE code='class_type'), 'class_type', 'decorator', 'Decorator', 30, true),
((SELECT id FROM platform.lkp_domain WHERE code='class_type'), 'class_type', 'constant', 'Constant', 40, true)
ON CONFLICT (domain, code) DO NOTHING;
