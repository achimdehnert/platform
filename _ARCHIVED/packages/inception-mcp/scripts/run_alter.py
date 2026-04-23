#!/usr/bin/env python3
"""Apply ALTER TABLE statements to platform database."""
import psycopg

conn = psycopg.connect('postgresql://bfagent:bfagent_dev_2024@localhost:5432/platform')
cur = conn.cursor()

# Add missing columns
print("Adding owner_id to dom_business_case...")
cur.execute('ALTER TABLE platform.dom_business_case ADD COLUMN IF NOT EXISTS owner_id INTEGER')

print("Adding exception_flows to dom_use_case...")
cur.execute("ALTER TABLE platform.dom_use_case ADD COLUMN IF NOT EXISTS exception_flows JSONB DEFAULT '[]'::jsonb")

print("Adding estimated_effort to dom_use_case...")
cur.execute('ALTER TABLE platform.dom_use_case ADD COLUMN IF NOT EXISTS estimated_effort VARCHAR(50)')

print("Adding description to lkp_choice...")
cur.execute('ALTER TABLE platform.lkp_choice ADD COLUMN IF NOT EXISTS description TEXT')

print("Adding metadata to lkp_choice...")
cur.execute("ALTER TABLE platform.lkp_choice ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb")

# Seed missing lookup domains
print("Seeding uc_priority domain...")
cur.execute("INSERT INTO platform.lkp_domain (code, name, name_de, description) VALUES ('uc_priority', 'UC Priority', 'UC Priorität', 'Use Case priority') ON CONFLICT (code) DO NOTHING")

print("Seeding uc_complexity domain...")
cur.execute("INSERT INTO platform.lkp_domain (code, name, name_de, description) VALUES ('uc_complexity', 'UC Complexity', 'UC Komplexität', 'Use Case complexity') ON CONFLICT (code) DO NOTHING")

# Seed uc_priority choices
cur.execute("SELECT id FROM platform.lkp_domain WHERE code = 'uc_priority'")
row = cur.fetchone()
if row:
    domain_id = row[0]
    for code, name, name_de, sort_order, color in [
        ('high', 'High', 'Hoch', 1, '#dc3545'),
        ('medium', 'Medium', 'Mittel', 2, '#ffc107'),
        ('low', 'Low', 'Niedrig', 3, '#198754'),
    ]:
        cur.execute(
            "INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, sort_order, color) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (domain_id, code) DO NOTHING",
            (domain_id, code, name, name_de, sort_order, color)
        )
    print("  uc_priority choices seeded")

# Seed uc_complexity choices
cur.execute("SELECT id FROM platform.lkp_domain WHERE code = 'uc_complexity'")
row = cur.fetchone()
if row:
    domain_id = row[0]
    for code, name, name_de, sort_order, color in [
        ('simple', 'Simple', 'Einfach', 1, '#198754'),
        ('moderate', 'Moderate', 'Mittel', 2, '#ffc107'),
        ('complex', 'Complex', 'Komplex', 3, '#dc3545'),
    ]:
        cur.execute(
            "INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, sort_order, color) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (domain_id, code) DO NOTHING",
            (domain_id, code, name, name_de, sort_order, color)
        )
    print("  uc_complexity choices seeded")

conn.commit()
print("Schema updated successfully!")
conn.close()
