#!/usr/bin/env python
"""
Create MCP Tables via Python SQLite
"""
import sqlite3
import sys

SQL_FILE = "CREATE_MCP_TABLES.sql"
DB_FILE = "bfagent.db"  # Django uses bfagent.db, not db.sqlite3!

def main():
    print(f"Creating MCP tables in {DB_FILE}...")
    
    # Read SQL file
    with open(SQL_FILE, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Remove comments for cleaner output
    lines = []
    for line in sql_content.split('\n'):
        if not line.strip().startswith('--'):
            lines.append(line)
    sql_clean = '\n'.join(lines)
    
    # Execute SQL
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Execute as script
        cursor.executescript(sql_clean)
        conn.commit()
        
        # Verify tables created
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'mcp_%'
            ORDER BY name
        """)
        mcp_tables = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name = 'core_naming_convention'
        """)
        naming_table = cursor.fetchall()
        
        print("\n✅ MCP Tables created successfully!")
        print(f"\n📋 Created {len(mcp_tables)} MCP tables:")
        for table in mcp_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   - {table}: {count} rows")
        
        if naming_table:
            cursor.execute("SELECT COUNT(*) FROM core_naming_convention")
            count = cursor.fetchone()[0]
            print(f"\n📋 Naming Conventions table: {count} rows")
        
        print("\n🎉 All tables ready for use!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        return 1
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    sys.exit(main())
