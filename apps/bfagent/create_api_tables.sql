-- Create API tables manually
-- This bypasses the migration issue

-- Table: api_workflow_contexts
CREATE TABLE IF NOT EXISTS api_workflow_contexts (
    id BIGSERIAL PRIMARY KEY,
    context_id VARCHAR(255) UNIQUE NOT NULL,
    workflow_name VARCHAR(255) NOT NULL DEFAULT '',
    data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW() + INTERVAL '24 hours'
);

CREATE INDEX IF NOT EXISTS api_workflow_context_idx ON api_workflow_contexts (context_id);
CREATE INDEX IF NOT EXISTS api_workflow_expires_idx ON api_workflow_contexts (expires_at);

-- Table: api_mcp_tool_executions
CREATE TABLE IF NOT EXISTS api_mcp_tool_executions (
    id BIGSERIAL PRIMARY KEY,
    context_id BIGINT REFERENCES api_workflow_contexts(id) ON DELETE SET NULL,
    server VARCHAR(100) NOT NULL,
    tool VARCHAR(100) NOT NULL,
    params JSONB NOT NULL DEFAULT '{}',
    result JSONB,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT NOT NULL DEFAULT '',
    execution_time_ms FLOAT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS api_mcp_server_tool_idx ON api_mcp_tool_executions (server, tool);
CREATE INDEX IF NOT EXISTS api_mcp_created_idx ON api_mcp_tool_executions (created_at);
CREATE INDEX IF NOT EXISTS api_mcp_success_idx ON api_mcp_tool_executions (success);

-- Insert fake migration record so Django thinks it's migrated
INSERT INTO django_migrations (app, name, applied)
VALUES ('api', '0001_initial', NOW())
ON CONFLICT DO NOTHING;

-- Success message
SELECT 'API tables created successfully!' as message;
