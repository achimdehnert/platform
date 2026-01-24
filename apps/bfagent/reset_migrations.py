"""
Reset ALL migrations in django_migrations table.
DA DIE DB LEER IST, ist das sicher!
"""
import sqlite3

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()

# Zähle vorher
c.execute("SELECT COUNT(*) FROM django_migrations")
before = c.fetchone()[0]
print(f"Vorher: {before} Migrations in django_migrations")

# LÖSCHE ALLE
c.execute("DELETE FROM django_migrations")
conn.commit()

# Zähle nachher
c.execute("SELECT COUNT(*) FROM django_migrations")
after = c.fetchone()[0]
print(f"Nachher: {after} Migrations")

conn.close()

print("\n✅ Migrations-History ge löscht!")
print("✅ Jetzt: python manage.py migrate --fake-initial")
