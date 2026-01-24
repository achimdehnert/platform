#!/usr/bin/env python
"""
Apply Naming Conventions to core_naming_convention table
"""
import sqlite3
import sys

SQL_FILE = "INSERT_NAMING_CONVENTIONS.sql"
DB_FILE = "bfagent.db"

def main():
    print(f"\n{'='*70}")
    print("  BF Agent - Naming Conventions Integration")
    print(f"{'='*70}\n")
    
    # Read SQL file
    with open(SQL_FILE, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Execute SQL
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        print("📝 Applying naming conventions...")
        
        # Execute as script
        cursor.executescript(sql_content)
        conn.commit()
        
        # Count results
        cursor.execute("SELECT COUNT(*) FROM core_naming_convention")
        count = cursor.fetchone()[0]
        
        # Show conventions
        cursor.execute("""
            SELECT 
                app_label,
                display_name,
                table_prefix,
                class_prefix,
                enforce_convention
            FROM core_naming_convention
            ORDER BY 
                CASE app_label
                    WHEN 'core' THEN 1
                    WHEN 'bfagent' THEN 2
                    WHEN 'bfagent_mcp' THEN 3
                    ELSE 4
                END,
                app_label
        """)
        conventions = cursor.fetchall()
        
        print(f"\n✅ Successfully integrated {count} naming conventions!\n")
        print(f"{'='*70}")
        print(f"{'App Label':<20} {'Display Name':<20} {'Table':<12} {'Class':<12} {'Enforce'}")
        print(f"{'='*70}")
        
        for app, display, tbl_prefix, cls_prefix, enforce in conventions:
            tbl = f"{tbl_prefix}*" if tbl_prefix else "(none)"
            cls = f"{cls_prefix}*" if cls_prefix else "(none)"
            enf = "✓" if enforce else "-"
            print(f"{app:<20} {display:<20} {tbl:<12} {cls:<12} {enf}")
        
        print(f"{'='*70}\n")
        
        # Show categories
        core_count = len([c for c in conventions if c[0] in ['core', 'bfagent', 'bfagent_mcp']])
        hub_count = len([c for c in conventions if 'hub' in c[0].lower() or c[0] == 'genagent'])
        special_count = count - core_count - hub_count
        
        print("📊 Categories:")
        print(f"   ✅ Core & Base Apps:  {core_count}")
        print(f"   ✅ Hub Apps:          {hub_count}")
        print(f"   ✅ Specialized Apps:  {special_count}")
        print(f"   {'='*30}")
        print(f"   📋 Total:             {count}\n")
        
        print("🎯 Next Steps:")
        print("   1. Test the conventions:")
        print("      python test_refactor_tools_quick.py")
        print("")
        print("   2. Use in Windsurf:")
        print("      'Welche Naming Conventions gibt es?'")
        print("      → bfagent_list_naming_conventions()")
        print("")
        print("   3. Get specific convention:")
        print("      'Naming Convention für genagent?'")
        print("      → bfagent_get_naming_convention(app_label='genagent')")
        print("")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    sys.exit(main())
