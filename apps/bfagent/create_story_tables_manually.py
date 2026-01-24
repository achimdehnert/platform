"""
Manual table creation for Story Elements
Run this if migrations are stuck
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection

# SQL from sqlmigrate writing_hub 0004
SQL_STATEMENTS = """
-- Emotional Tones
CREATE TABLE IF NOT EXISTS "emotional_tones" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "code" varchar(50) NOT NULL UNIQUE,
    "name_en" varchar(100) NOT NULL,
    "name_de" varchar(100) NOT NULL,
    "description" text NOT NULL,
    "color" varchar(7) NOT NULL,
    "order" integer NOT NULL,
    "is_active" bool NOT NULL
);

-- Conflict Levels
CREATE TABLE IF NOT EXISTS "conflict_levels" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "code" varchar(50) NOT NULL UNIQUE,
    "name_en" varchar(100) NOT NULL,
    "name_de" varchar(100) NOT NULL,
    "description" text NOT NULL,
    "intensity" integer NOT NULL,
    "color" varchar(7) NOT NULL,
    "order" integer NOT NULL,
    "is_active" bool NOT NULL
);

-- Beat Types
CREATE TABLE IF NOT EXISTS "beat_types" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "code" varchar(50) NOT NULL UNIQUE,
    "name_en" varchar(100) NOT NULL,
    "name_de" varchar(100) NOT NULL,
    "description" text NOT NULL,
    "icon" varchar(50) NOT NULL,
    "color" varchar(7) NOT NULL,
    "order" integer NOT NULL,
    "is_active" bool NOT NULL
);

-- Scene Connection Types
CREATE TABLE IF NOT EXISTS "scene_connection_types" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "code" varchar(50) NOT NULL UNIQUE,
    "name_en" varchar(100) NOT NULL,
    "name_de" varchar(100) NOT NULL,
    "description" text NOT NULL,
    "icon" varchar(50) NOT NULL,
    "order" integer NOT NULL,
    "is_active" bool NOT NULL
);

-- Locations
CREATE TABLE IF NOT EXISTS "story_locations" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "name" varchar(200) NOT NULL,
    "description" text NOT NULL,
    "time_period" varchar(200) NOT NULL,
    "mood" varchar(200) NOT NULL,
    "notes" text NOT NULL,
    "created_at" datetime NOT NULL,
    "updated_at" datetime NOT NULL,
    "project_id" bigint NOT NULL REFERENCES "book_projects" ("id") DEFERRABLE INITIALLY DEFERRED
);

-- Plot Threads
CREATE TABLE IF NOT EXISTS "plot_threads" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "name" varchar(200) NOT NULL,
    "description" text NOT NULL,
    "thread_type" varchar(50) NOT NULL,
    "color" varchar(7) NOT NULL,
    "resolution" text NOT NULL,
    "created_at" datetime NOT NULL,
    "updated_at" datetime NOT NULL,
    "project_id" bigint NOT NULL REFERENCES "book_projects" ("id") DEFERRABLE INITIALLY DEFERRED,
    "status_id" bigint NULL REFERENCES "writing_stages" ("id") DEFERRABLE INITIALLY DEFERRED
);

-- Scenes
CREATE TABLE IF NOT EXISTS "story_scenes" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "title" varchar(200) NOT NULL,
    "summary" text NOT NULL,
    "order" integer NOT NULL,
    "story_datetime" datetime NULL,
    "story_date_description" varchar(200) NOT NULL,
    "goal" text NOT NULL,
    "disaster" text NOT NULL,
    "word_count_target" integer NOT NULL,
    "word_count_actual" integer NOT NULL,
    "content" text NOT NULL,
    "notes" text NOT NULL,
    "created_at" datetime NOT NULL,
    "updated_at" datetime NOT NULL,
    "chapter_id" bigint NOT NULL REFERENCES "book_chapters" ("id") DEFERRABLE INITIALLY DEFERRED,
    "conflict_level_id" bigint NULL REFERENCES "conflict_levels" ("id") DEFERRABLE INITIALLY DEFERRED,
    "emotional_end_id" bigint NULL REFERENCES "emotional_tones" ("id") DEFERRABLE INITIALLY DEFERRED,
    "emotional_start_id" bigint NULL REFERENCES "emotional_tones" ("id") DEFERRABLE INITIALLY DEFERRED,
    "location_id" bigint NULL REFERENCES "story_locations" ("id") DEFERRABLE INITIALLY DEFERRED,
    "pov_character_id" bigint NULL REFERENCES "characters" ("id") DEFERRABLE INITIALLY DEFERRED,
    "status_id" bigint NULL REFERENCES "writing_stages" ("id") DEFERRABLE INITIALLY DEFERRED
);

-- Scene Characters M2M
CREATE TABLE IF NOT EXISTS "story_scenes_characters" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "scene_id" bigint NOT NULL REFERENCES "story_scenes" ("id") DEFERRABLE INITIALLY DEFERRED,
    "characters_id" bigint NOT NULL REFERENCES "characters" ("id") DEFERRABLE INITIALLY DEFERRED
);

-- Scene Plot Threads M2M
CREATE TABLE IF NOT EXISTS "story_scenes_plot_threads" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "scene_id" bigint NOT NULL REFERENCES "story_scenes" ("id") DEFERRABLE INITIALLY DEFERRED,
    "plotthread_id" bigint NOT NULL REFERENCES "plot_threads" ("id") DEFERRABLE INITIALLY DEFERRED
);

-- Beats
CREATE TABLE IF NOT EXISTS "story_beats" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "description" text NOT NULL,
    "order" integer NOT NULL,
    "notes" text NOT NULL,
    "created_at" datetime NOT NULL,
    "updated_at" datetime NOT NULL,
    "beat_type_id" bigint NULL REFERENCES "beat_types" ("id") DEFERRABLE INITIALLY DEFERRED,
    "scene_id" bigint NOT NULL REFERENCES "story_scenes" ("id") DEFERRABLE INITIALLY DEFERRED
);

-- Scene Connections
CREATE TABLE IF NOT EXISTS "scene_connections" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "description" text NOT NULL,
    "created_at" datetime NOT NULL,
    "updated_at" datetime NOT NULL,
    "from_scene_id" bigint NOT NULL REFERENCES "story_scenes" ("id") DEFERRABLE INITIALLY DEFERRED,
    "to_scene_id" bigint NOT NULL REFERENCES "story_scenes" ("id") DEFERRABLE INITIALLY DEFERRED,
    "connection_type_id" bigint NOT NULL REFERENCES "scene_connection_types" ("id") DEFERRABLE INITIALLY DEFERRED
);

-- Timeline Events
CREATE TABLE IF NOT EXISTS "timeline_events" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "description" text NOT NULL,
    "story_datetime" datetime NULL,
    "story_date_description" varchar(200) NOT NULL,
    "is_shown" bool NOT NULL,
    "created_at" datetime NOT NULL,
    "updated_at" datetime NOT NULL,
    "project_id" bigint NOT NULL REFERENCES "book_projects" ("id") DEFERRABLE INITIALLY DEFERRED,
    "scene_id" bigint NULL REFERENCES "story_scenes" ("id") DEFERRABLE INITIALLY DEFERRED
);

-- Timeline Event Characters M2M
CREATE TABLE IF NOT EXISTS "timeline_events_characters" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "timelineevent_id" bigint NOT NULL REFERENCES "timeline_events" ("id") DEFERRABLE INITIALLY DEFERRED,
    "characters_id" bigint NOT NULL REFERENCES "characters" ("id") DEFERRABLE INITIALLY DEFERRED
);
"""


def create_tables():
    """Create all tables manually"""
    created = 0
    errors = 0

    # Better parsing: split on ); followed by newline/whitespace
    import re

    statements = []

    # Split into individual CREATE TABLE statements
    parts = re.split(r"\);", SQL_STATEMENTS)
    for part in parts:
        part = part.strip()
        if part and "CREATE TABLE" in part.upper():
            # Add back the );
            statements.append(part + ");")

    print(f"Found {len(statements)} CREATE TABLE statements to execute\n")

    with connection.cursor() as cursor:
        for i, statement in enumerate(statements, 1):
            # Extract table name
            match = re.search(r'"([^"]+)"', statement)
            table_name = match.group(1) if match else "unknown"
            print(f"{i}. Creating table: {table_name}...", end=" ")

            try:
                cursor.execute(statement)
                print("✅")
                created += 1
            except Exception as e:
                print(f"⚠️  {e}")
                errors += 1

    print(f"\n{'='*60}")
    print(f"✅ Created: {created} tables")
    if errors:
        print(f"⚠️  Errors: {errors}")
    print(f"{'='*60}")
    print("\nNow run: python manage.py init_story_lookups")


if __name__ == "__main__":
    create_tables()
