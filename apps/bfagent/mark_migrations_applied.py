import sqlite3
from datetime import datetime

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()

# Markiere Writing Hub Migrations als angewendet
migrations = [
    ('writing_hub', '0001_initial'),
    ('writing_hub', '0002_seed_lookup_data'),
]

for app, name in migrations:
    c.execute('''
        INSERT INTO django_migrations (app, name, applied)
        VALUES (?, ?, ?)
    ''', (app, name, datetime.now()))
    print(f"✅ Markiert: {app}.{name}")

conn.commit()
conn.close()

print("\n✅ Writing Hub Migrations als angewendet markiert!")
