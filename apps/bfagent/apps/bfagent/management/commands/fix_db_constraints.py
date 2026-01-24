"""
Custom Django management command to fix database foreign key constraints
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Fix database foreign key constraints by temporarily disabling them"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Disable foreign key checks
            cursor.execute("PRAGMA foreign_keys = OFF;")

            # Create Django migrations table if it doesn't exist
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS "django_migrations" (
                    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                    "app" varchar(255) NOT NULL,
                    "name" varchar(255) NOT NULL,
                    "applied" datetime NOT NULL
                );
            """
            )

            # Re-enable foreign key checks
            cursor.execute("PRAGMA foreign_keys = ON;")

        self.stdout.write(
            self.style.SUCCESS(
                "Successfully created django_migrations table with foreign keys disabled"
            )
        )
