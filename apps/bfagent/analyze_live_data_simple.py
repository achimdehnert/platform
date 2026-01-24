#!/usr/bin/env python
"""Analysiere Live-Daten DIREKT aus SQLite (ohne Django)"""
import sqlite3
import os

DB_PATH = "db.sqlite3"

if not os.path.exists(DB_PATH):
    print(f"❌ Datenbank nicht gefunden: {DB_PATH}")
    exit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("\n" + "="*80)
print("LIVE DATA ANALYSIS - Welche Werte sind aktuell in der DB?")
print("="*80 + "\n")

# 1. Book Projects Status
print("📊 BOOK PROJECT STATUS VALUES:")
print("-" * 80)
try:
    cursor.execute("SELECT DISTINCT status FROM writing_book_projects WHERE status IS NOT NULL ORDER BY status")
    for row in cursor.fetchall():
        print(f"  • {row[0]}")
except Exception as e:
    print(f"  ⚠️ Fehler: {e}")

# 2. Content Ratings
print("\n📊 CONTENT RATING VALUES:")
print("-" * 80)
try:
    cursor.execute("SELECT DISTINCT content_rating FROM writing_book_projects WHERE content_rating IS NOT NULL ORDER BY content_rating")
    for row in cursor.fetchall():
        print(f"  • {row[0]}")
except Exception as e:
    print(f"  ⚠️ Fehler: {e}")

# 3. Writing Stage
print("\n📊 WRITING STAGE VALUES:")
print("-" * 80)
try:
    cursor.execute("SELECT DISTINCT writing_stage FROM writing_book_projects WHERE writing_stage IS NOT NULL ORDER BY writing_stage")
    for row in cursor.fetchall():
        print(f"  • {row[0]}")
except Exception as e:
    print(f"  ⚠️ Fehler: {e}")

# 4. Genres Table (if exists)
print("\n📊 GENRES (FROM LOOKUP TABLE):")
print("-" * 80)
try:
    cursor.execute("SELECT name FROM genres WHERE is_active = 1 ORDER BY name LIMIT 20")
    genres = cursor.fetchall()
    if genres:
        for row in genres:
            print(f"  • {row[0]}")
    else:
        print("  ⚠️ Keine Genres gefunden (Tabelle leer)")
except Exception as e:
    print(f"  ⚠️ Fehler: {e}")

# 5. Writing Status Table (if exists)
print("\n📊 WRITING STATUS (FROM LOOKUP TABLE):")
print("-" * 80)
try:
    cursor.execute("SELECT name FROM writing_statuses WHERE is_active = 1 ORDER BY sort_order")
    statuses = cursor.fetchall()
    if statuses:
        for row in statuses:
            print(f"  • {row[0]}")
    else:
        print("  ⚠️ Keine Writing Statuses gefunden (Tabelle leer)")
except Exception as e:
    print(f"  ⚠️ Fehler: {e}")

# 6. Handler Categories (agents table)
print("\n📊 HANDLER CATEGORIES (from agents):")
print("-" * 80)
try:
    cursor.execute("SELECT DISTINCT agent_type FROM agents WHERE agent_type IS NOT NULL ORDER BY agent_type")
    for row in cursor.fetchall():
        print(f"  • {row[0]}")
except Exception as e:
    print(f"  ⚠️ Fehler: {e}")

# 7. Test Categories
print("\n📊 TEST CASE CATEGORIES:")
print("-" * 80)
try:
    cursor.execute("SELECT DISTINCT category FROM bfagent_testcase WHERE category IS NOT NULL ORDER BY category")
    for row in cursor.fetchall():
        print(f"  • {row[0]}")
except Exception as e:
    print(f"  ⚠️ Fehler: {e}")

# 9. Counts
print("\n📊 RECORD COUNTS:")
print("-" * 80)
try:
    cursor.execute("SELECT COUNT(*) FROM writing_book_projects")
    print(f"  • Book Projects: {cursor.fetchone()[0]}")
except:
    pass

try:
    cursor.execute("SELECT COUNT(*) FROM agents")
    print(f"  • Agents: {cursor.fetchone()[0]}")
except:
    pass

try:
    cursor.execute("SELECT COUNT(*) FROM genres")
    print(f"  • Genres: {cursor.fetchone()[0]}")
except:
    pass

try:
    cursor.execute("SELECT COUNT(*) FROM writing_statuses")
    print(f"  • Writing Statuses: {cursor.fetchone()[0]}")
except:
    pass

conn.close()

print("\n" + "="*80)
print("🎯 NÄCHSTER SCHRITT:")
print("Basierend auf diesen Werten erstelle ich jetzt die Lookup-Tabellen!")
print("="*80)
