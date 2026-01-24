"""
Add MCP Dashboard Fields to Database (SAFE)
============================================

Safely adds new fields, skipping those that already exist.

Usage:
    python packages/bfagent_mcp/scripts/add_dashboard_fields_safe.py
"""

import os
import sys
import sqlite3
from pathlib import Path

# Get database path
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DB_FILE = BASE_DIR / 'bfagent.db'


def get_table_columns(cursor, table_name):
    """Get existing columns for a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def add_column_safe(cursor, table_name, column_name, column_def):
    """Add column if it doesn't exist."""
    columns = get_table_columns(cursor, table_name)
    
    if column_name in columns:
        print(f"   ⏭️  {column_name} already exists, skipping")
        return False
    
    try:
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"
        cursor.execute(sql)
        print(f"   ✅ Added {column_name}")
        return True
    except sqlite3.Error as e:
        print(f"   ❌ Failed to add {column_name}: {e}")
        return False


def create_index_safe(cursor, index_name, index_sql):
    """Create index if it doesn't exist."""
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type = 'index' AND name = ?
    """, (index_name,))
    
    if cursor.fetchone():
        print(f"   ⏭️  {index_name} already exists, skipping")
        return False
    
    try:
        cursor.execute(index_sql)
        print(f"   ✅ Created index {index_name}")
        return True
    except sqlite3.Error as e:
        print(f"   ❌ Failed to create {index_name}: {e}")
        return False


def add_dashboard_fields():
    """Add dashboard fields safely."""
    
    print("🚀 Adding MCP Dashboard fields to database...")
    print(f"   Database: {DB_FILE}")
    
    if not DB_FILE.exists():
        print(f"❌ Database not found: {DB_FILE}")
        return False
    
    try:
        conn = sqlite3.connect(str(DB_FILE))
        cursor = conn.cursor()
        print("🔌 Connected to database\n")
        
        # =====================================================================
        # 1. MCPRefactorSession Fields
        # =====================================================================
        
        print("📝 Adding fields to mcp_refactor_session:")
        
        fields_added = 0
        
        if add_column_safe(cursor, 'mcp_refactor_session', 
                          'celery_task_id', 'VARCHAR(255) NULL'):
            fields_added += 1
        
        if add_column_safe(cursor, 'mcp_refactor_session',
                          'backup_path', 'VARCHAR(500) NULL'):
            fields_added += 1
        
        if add_column_safe(cursor, 'mcp_refactor_session',
                          'components_selected', 'TEXT NULL'):
            fields_added += 1
        
        if add_column_safe(cursor, 'mcp_refactor_session',
                          'triggered_by_user_id', 
                          'INTEGER NULL REFERENCES auth_user(id) ON DELETE SET NULL'):
            fields_added += 1
        
        if add_column_safe(cursor, 'mcp_refactor_session',
                          'ended_at', 'TIMESTAMP NULL'):
            fields_added += 1
        
        # Alias fields
        if add_column_safe(cursor, 'mcp_refactor_session',
                          'files_changed', 'INTEGER DEFAULT 0'):
            fields_added += 1
        
        if add_column_safe(cursor, 'mcp_refactor_session',
                          'lines_added', 'INTEGER DEFAULT 0'):
            fields_added += 1
        
        if add_column_safe(cursor, 'mcp_refactor_session',
                          'lines_removed', 'INTEGER DEFAULT 0'):
            fields_added += 1
        
        print(f"\n✅ Added {fields_added} new fields to mcp_refactor_session\n")
        
        # =====================================================================
        # 2. MCPFileChange Fields
        # =====================================================================
        
        print("📝 Adding fields to mcp_file_change:")
        
        if add_column_safe(cursor, 'mcp_file_change',
                          'diff_content', 'TEXT NULL'):
            fields_added += 1
        
        print()
        
        # =====================================================================
        # 3. Create Indexes
        # =====================================================================
        
        print("📝 Creating indexes:")
        
        indexes_created = 0
        
        if create_index_safe(cursor, 'idx_mcp_session_celery_task',
                           'CREATE INDEX idx_mcp_session_celery_task ON mcp_refactor_session(celery_task_id)'):
            indexes_created += 1
        
        if create_index_safe(cursor, 'idx_mcp_session_triggered_by',
                           'CREATE INDEX idx_mcp_session_triggered_by ON mcp_refactor_session(triggered_by_user_id)'):
            indexes_created += 1
        
        if create_index_safe(cursor, 'idx_mcp_session_ended_at',
                           'CREATE INDEX idx_mcp_session_ended_at ON mcp_refactor_session(ended_at)'):
            indexes_created += 1
        
        print(f"\n✅ Created {indexes_created} new indexes\n")
        
        # =====================================================================
        # 4. Update Existing Data (Safe)
        # =====================================================================
        
        print("📝 Updating existing data:")
        
        session_cols = get_table_columns(cursor, 'mcp_refactor_session')
        file_cols = get_table_columns(cursor, 'mcp_file_change')
        
        # Copy completed_at to ended_at (if completed_at exists)
        if 'completed_at' in session_cols and 'ended_at' in session_cols:
            cursor.execute("""
                UPDATE mcp_refactor_session 
                SET ended_at = completed_at 
                WHERE completed_at IS NOT NULL AND ended_at IS NULL
            """)
            updated = cursor.rowcount
            print(f"   ✅ Updated ended_at for {updated} sessions")
        else:
            print(f"   ⏭️  Skipping ended_at update (source column not found)")
        
        # Copy totals to aliases (if source columns exist)
        if 'total_files_changed' in session_cols and 'files_changed' in session_cols:
            cursor.execute("""
                UPDATE mcp_refactor_session 
                SET files_changed = total_files_changed 
                WHERE files_changed = 0 AND total_files_changed > 0
            """)
            updated = cursor.rowcount
            print(f"   ✅ Updated files_changed for {updated} sessions")
        else:
            print(f"   ⏭️  Skipping files_changed update")
        
        if 'total_lines_added' in session_cols and 'lines_added' in session_cols:
            cursor.execute("""
                UPDATE mcp_refactor_session 
                SET lines_added = total_lines_added 
                WHERE lines_added = 0 AND total_lines_added > 0
            """)
            updated = cursor.rowcount
            print(f"   ✅ Updated lines_added for {updated} sessions")
        else:
            print(f"   ⏭️  Skipping lines_added update")
        
        if 'total_lines_removed' in session_cols and 'lines_removed' in session_cols:
            cursor.execute("""
                UPDATE mcp_refactor_session 
                SET lines_removed = total_lines_removed 
                WHERE lines_removed = 0 AND total_lines_removed > 0
            """)
            updated = cursor.rowcount
            print(f"   ✅ Updated lines_removed for {updated} sessions")
        else:
            print(f"   ⏭️  Skipping lines_removed update")
        
        # Copy diff_preview to diff_content (if diff_preview exists)
        if 'diff_preview' in file_cols and 'diff_content' in file_cols:
            cursor.execute("""
                UPDATE mcp_file_change 
                SET diff_content = diff_preview 
                WHERE diff_content IS NULL AND diff_preview IS NOT NULL
            """)
            updated = cursor.rowcount
            print(f"   ✅ Updated diff_content for {updated} file changes")
        else:
            print(f"   ⏭️  Skipping diff_content update")
        
        # Commit changes
        conn.commit()
        print("\n💾 Changes committed to database")
        
        # =====================================================================
        # 5. Verification
        # =====================================================================
        
        print("\n🔍 Verification:")
        
        # Check all fields exist
        columns = get_table_columns(cursor, 'mcp_refactor_session')
        required_fields = {
            'celery_task_id', 'backup_path', 'components_selected',
            'triggered_by_user_id', 'ended_at', 'files_changed',
            'lines_added', 'lines_removed'
        }
        
        missing = required_fields - columns
        if missing:
            print(f"   ⚠️  Missing fields: {missing}")
        else:
            print(f"   ✅ All required fields present in mcp_refactor_session")
        
        columns = get_table_columns(cursor, 'mcp_file_change')
        if 'diff_content' in columns:
            print(f"   ✅ Field diff_content present in mcp_file_change")
        else:
            print(f"   ⚠️  Field diff_content missing in mcp_file_change")
        
        # Count sessions
        cursor.execute("SELECT COUNT(*) FROM mcp_refactor_session")
        count = cursor.fetchone()[0]
        print(f"\n📊 Database contains {count} refactor sessions")
        
        conn.close()
        
        print("\n🎉 SUCCESS! Dashboard fields are ready.")
        
        return True
        
    except sqlite3.Error as e:
        print(f"\n❌ SQLite Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = add_dashboard_fields()
    
    if success:
        print("\n✅ Next steps:")
        print("   1. Create navigation: python packages/bfagent_mcp/scripts/create_mcp_navigation.py")
        print("   2. Restart Django: python manage.py runserver")
        print("   3. Open dashboard: http://localhost:8000/control-center/mcp/")
        sys.exit(0)
    else:
        print("\n❌ Failed to add dashboard fields")
        sys.exit(1)
