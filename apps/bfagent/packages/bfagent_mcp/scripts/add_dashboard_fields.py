"""
Add MCP Dashboard Fields to Database
=====================================

Executes SQL script to add new fields to MCP tables.

Usage:
    python packages/bfagent_mcp/scripts/add_dashboard_fields.py
"""

import os
import sys
import sqlite3
from pathlib import Path

# Get database path
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DB_FILE = BASE_DIR / 'bfagent.db'
SQL_FILE = Path(__file__).parent.parent / 'sql' / 'ADD_MCP_DASHBOARD_FIELDS.sql'


def add_dashboard_fields():
    """Execute SQL script to add dashboard fields."""
    
    print("🚀 Adding MCP Dashboard fields to database...")
    print(f"   Database: {DB_FILE}")
    print(f"   SQL Script: {SQL_FILE}")
    
    if not DB_FILE.exists():
        print(f"❌ Database not found: {DB_FILE}")
        return False
    
    if not SQL_FILE.exists():
        print(f"❌ SQL script not found: {SQL_FILE}")
        return False
    
    try:
        # Read SQL script
        with open(SQL_FILE, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        print("\n📄 SQL Script loaded successfully")
        
        # Connect to database
        conn = sqlite3.connect(str(DB_FILE))
        cursor = conn.cursor()
        
        print("🔌 Connected to database")
        
        # Execute script
        print("\n⚙️  Executing SQL script...")
        cursor.executescript(sql_script)
        
        conn.commit()
        print("✅ SQL script executed successfully")
        
        # Verify fields
        print("\n🔍 Verifying new fields...")
        
        # Check mcp_refactor_session
        cursor.execute("PRAGMA table_info(mcp_refactor_session)")
        columns = {row[1] for row in cursor.fetchall()}
        
        required_fields = {
            'celery_task_id',
            'backup_path',
            'components_selected',
            'triggered_by_user_id',
            'ended_at',
            'files_changed',
            'lines_added',
            'lines_removed',
        }
        
        missing = required_fields - columns
        if missing:
            print(f"⚠️  Missing fields in mcp_refactor_session: {missing}")
        else:
            print(f"✅ All fields present in mcp_refactor_session")
        
        # Check mcp_file_change
        cursor.execute("PRAGMA table_info(mcp_file_change)")
        columns = {row[1] for row in cursor.fetchall()}
        
        if 'diff_content' not in columns:
            print("⚠️  Missing field: diff_content in mcp_file_change")
        else:
            print("✅ Field diff_content present in mcp_file_change")
        
        # Check indexes
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type = 'index' 
            AND tbl_name = 'mcp_refactor_session'
            AND name LIKE 'idx_mcp_%'
        """)
        indexes = [row[0] for row in cursor.fetchall()]
        print(f"\n✅ Created {len(indexes)} indexes:")
        for idx in indexes:
            print(f"   - {idx}")
        
        # Count existing sessions
        cursor.execute("SELECT COUNT(*) FROM mcp_refactor_session")
        count = cursor.fetchone()[0]
        print(f"\n📊 Found {count} existing refactor sessions")
        
        conn.close()
        print("\n🎉 SUCCESS! Dashboard fields added successfully.")
        
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
        print("   1. Restart Django server: python manage.py runserver")
        print("   2. Create navigation: python packages/bfagent_mcp/scripts/create_mcp_navigation.py")
        print("   3. Open dashboard: http://localhost:8000/control-center/mcp/")
        sys.exit(0)
    else:
        print("\n❌ Failed to add dashboard fields")
        sys.exit(1)
