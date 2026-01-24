-- ============================================================================
-- ADD MCP Dashboard Fields to Existing Tables
-- ============================================================================
-- 
-- Adds fields needed for MCP Dashboard V2:
-- - Celery task tracking
-- - Backup paths
-- - User tracking
-- - Component selection
--
-- Usage:
--   sqlite3 bfagent.db < ADD_MCP_DASHBOARD_FIELDS.sql
--
-- Or Python:
--   python packages/bfagent_mcp/scripts/add_dashboard_fields.py
-- ============================================================================

BEGIN TRANSACTION;

-- ============================================================================
-- 1. MCPRefactorSession - Add Dashboard Fields
-- ============================================================================

-- Add celery_task_id (for tracking Celery tasks)
ALTER TABLE mcp_refactor_session 
ADD COLUMN celery_task_id VARCHAR(255) NULL;

-- Add backup_path (for storing backup location)
ALTER TABLE mcp_refactor_session 
ADD COLUMN backup_path VARCHAR(500) NULL;

-- Add components_selected (JSON array of selected components)
ALTER TABLE mcp_refactor_session 
ADD COLUMN components_selected TEXT NULL;  -- JSON field

-- Add triggered_by_user (FK to auth_user)
ALTER TABLE mcp_refactor_session 
ADD COLUMN triggered_by_user_id INTEGER NULL 
REFERENCES auth_user(id) ON DELETE SET NULL;

-- Add ended_at (alias for completed_at)
ALTER TABLE mcp_refactor_session 
ADD COLUMN ended_at TIMESTAMP NULL;

-- Add alias fields for compatibility
ALTER TABLE mcp_refactor_session 
ADD COLUMN files_changed INTEGER DEFAULT 0;

ALTER TABLE mcp_refactor_session 
ADD COLUMN lines_added INTEGER DEFAULT 0;

ALTER TABLE mcp_refactor_session 
ADD COLUMN lines_removed INTEGER DEFAULT 0;

-- Update triggered_by choices (add 'web_dashboard')
-- Note: SQLite doesn't support ALTER COLUMN, but this is just a varchar field
-- The constraint is enforced in Django code

-- ============================================================================
-- 2. MCPFileChange - Add Dashboard Fields
-- ============================================================================

-- Add diff_content (alias for diff_preview)
ALTER TABLE mcp_file_change 
ADD COLUMN diff_content TEXT NULL;

-- ============================================================================
-- 3. Create Indexes for Performance
-- ============================================================================

-- Index on celery_task_id for quick lookup
CREATE INDEX IF NOT EXISTS idx_mcp_session_celery_task 
ON mcp_refactor_session(celery_task_id);

-- Index on triggered_by_user for filtering
CREATE INDEX IF NOT EXISTS idx_mcp_session_triggered_by 
ON mcp_refactor_session(triggered_by_user_id);

-- Index on ended_at for time-based queries
CREATE INDEX IF NOT EXISTS idx_mcp_session_ended_at 
ON mcp_refactor_session(ended_at);

-- ============================================================================
-- 4. Update Existing Data (Optional)
-- ============================================================================

-- Copy completed_at to ended_at for existing records
UPDATE mcp_refactor_session 
SET ended_at = completed_at 
WHERE completed_at IS NOT NULL AND ended_at IS NULL;

-- Copy total_files_changed to files_changed
UPDATE mcp_refactor_session 
SET files_changed = total_files_changed 
WHERE files_changed = 0 AND total_files_changed > 0;

-- Copy total_lines_added to lines_added
UPDATE mcp_refactor_session 
SET lines_added = total_lines_added 
WHERE lines_added = 0 AND total_lines_added > 0;

-- Copy total_lines_removed to lines_removed
UPDATE mcp_refactor_session 
SET lines_removed = total_lines_removed 
WHERE lines_removed = 0 AND total_lines_removed > 0;

-- Copy diff_preview to diff_content
UPDATE mcp_file_change 
SET diff_content = diff_preview 
WHERE diff_content IS NULL AND diff_preview IS NOT NULL;

COMMIT;

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Check if columns exist
SELECT 
    name,
    type
FROM pragma_table_info('mcp_refactor_session')
WHERE name IN (
    'celery_task_id',
    'backup_path',
    'components_selected',
    'triggered_by_user_id',
    'ended_at',
    'files_changed',
    'lines_added',
    'lines_removed'
)
ORDER BY name;

SELECT 
    name,
    type
FROM pragma_table_info('mcp_file_change')
WHERE name = 'diff_content';

-- Check indexes
SELECT name, sql 
FROM sqlite_master 
WHERE type = 'index' 
AND tbl_name = 'mcp_refactor_session'
AND name LIKE 'idx_mcp_%';

-- ============================================================================
-- Success Message
-- ============================================================================

SELECT '✅ MCP Dashboard fields added successfully!' as status;
