#!/usr/bin/env python
"""One-time script to add Import Framework V2 columns to database."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import connection

# BookProjects columns
book_projects_sql = [
    "ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS project_definition_xml TEXT",
    "ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS outline_template_code VARCHAR(100)",
    "ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS logline TEXT",
    "ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS central_question TEXT",
    "ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS narrative_voice TEXT",
    "ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS prose_style TEXT",
    "ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS pacing_style TEXT",
    "ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS dialogue_style TEXT",
    "ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS comparable_titles TEXT",
    "ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS spice_level VARCHAR(50)",
    "ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS content_warnings TEXT",
    "ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS series_arc TEXT",
    "ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS threads_to_continue TEXT",
    "ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS consistency_rules TEXT",
    "ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS forbidden_elements TEXT",
    "ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS required_elements TEXT",
    "ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS agent_instructions TEXT",
]

with connection.cursor() as cursor:
    for sql in book_projects_sql:
        cursor.execute(sql)
        print(f"OK: {sql[:60]}...")

print("\nBookProjects columns added!")
