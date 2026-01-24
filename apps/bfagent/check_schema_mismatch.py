"""
Check schema mismatch for book_chapters
"""

import sqlite3

conn = sqlite3.connect("db.sqlite3")
cursor = conn.cursor()

print("\n" + "=" * 80)
print("🔍 SCHEMA ANALYSIS: book_chapters vs chapters_v2")
print("=" * 80 + "\n")

# Check if book_chapters is a view or table
cursor.execute("SELECT type FROM sqlite_master WHERE name = 'book_chapters'")
result = cursor.fetchone()
if result:
    print(f"book_chapters: {result[0].upper()}")
else:
    print("book_chapters: DOES NOT EXIST")

# Get schema of book_chapters
print("\n📋 book_chapters columns:")
print("-" * 80)
try:
    cursor.execute("PRAGMA table_info(book_chapters)")
    book_chapters_cols = cursor.fetchall()
    if book_chapters_cols:
        for col in book_chapters_cols:
            print(f"  {col[1]:30s} {col[2]:15s} {'NOT NULL' if col[3] else ''}")
    else:
        print("  (no columns or doesn't exist)")
except Exception as e:
    print(f"  ERROR: {e}")

# Get schema of chapters_v2
print("\n📋 chapters_v2 columns:")
print("-" * 80)
try:
    cursor.execute("PRAGMA table_info(chapters_v2)")
    chapters_v2_cols = cursor.fetchall()
    if chapters_v2_cols:
        for col in chapters_v2_cols:
            print(f"  {col[1]:30s} {col[2]:15s} {'NOT NULL' if col[3] else ''}")
    else:
        print("  (no columns or doesn't exist)")
except Exception as e:
    print(f"  ERROR: {e}")

# Get schema of writing_chapters
print("\n📋 writing_chapters columns:")
print("-" * 80)
try:
    cursor.execute("PRAGMA table_info(writing_chapters)")
    writing_chapters_cols = cursor.fetchall()
    if writing_chapters_cols:
        for col in writing_chapters_cols:
            print(f"  {col[1]:30s} {col[2]:15s} {'NOT NULL' if col[3] else ''}")
    else:
        print("  (no columns or doesn't exist)")
except Exception as e:
    print(f"  ERROR: {e}")

# Compare: find which has project_id
print("\n" + "=" * 80)
print("🔍 FINDING project_id:")
print("=" * 80)

for table in ["book_chapters", "chapters_v2", "writing_chapters"]:
    try:
        cursor.execute(f"PRAGMA table_info({table})")
        cols = cursor.fetchall()
        col_names = [col[1] for col in cols]

        if "project_id" in col_names:
            print(f"✅ {table:30s} HAS project_id")
        else:
            print(f"❌ {table:30s} NO project_id")
    except:
        print(f"⚠️  {table:30s} ERROR")

# Check VIEW definition
print("\n" + "=" * 80)
print("📜 VIEW DEFINITION:")
print("=" * 80)
try:
    cursor.execute("SELECT sql FROM sqlite_master WHERE name = 'book_chapters' AND type = 'view'")
    view_sql = cursor.fetchone()
    if view_sql:
        print(view_sql[0])
    else:
        print("book_chapters is not a view")
except Exception as e:
    print(f"ERROR: {e}")

conn.close()

print("\n" + "=" * 80)
print("💡 RECOMMENDATION:")
print("=" * 80)
print("\n1. If writing_chapters has project_id:")
print("   → Drop VIEW book_chapters")
print("   → Create VIEW book_chapters AS SELECT * FROM writing_chapters")
print("\n2. If chapters_v2 should be used:")
print("   → Check if book_id can be used as project_id")
print("   → Or map columns in VIEW definition")
print()
