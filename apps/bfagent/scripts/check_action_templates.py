#!/usr/bin/env python
"""Check if action_templates table exists"""
import sqlite3

conn = sqlite3.connect('bfagent.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='action_templates'")
result = cursor.fetchone()

if result:
    print("✅ action_templates table EXISTS!")
    cursor.execute("SELECT COUNT(*) FROM action_templates")
    count = cursor.fetchone()[0]
    print(f"   Records: {count}")
else:
    print("❌ action_templates table NOT FOUND")

conn.close()
