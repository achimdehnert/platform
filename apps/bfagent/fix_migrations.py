import sqlite3
from datetime import datetime

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()

# Markiere die fehlende Migration als angewendet
c.execute('''
    INSERT INTO django_migrations (app, name, applied) 
    VALUES (?, ?, ?)
''', ('bfagent', '0002_chapterbeat_storybible_storychapter_storycharacter_and_more', datetime.now()))

conn.commit()
conn.close()

print("✅ Migration 0002 als angewendet markiert")
print("✅ Jetzt kannst du 'python manage.py migrate' ausführen")
