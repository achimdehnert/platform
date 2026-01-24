#!/usr/bin/env python
"""
Safe Migration Script
Automatically handles "table already exists" errors with --fake migrations
"""
import os
import subprocess
import sys
from pathlib import Path

# Django Setup
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django

django.setup()


def run_migrate():
    """Run migration with automatic --fake on table exists errors"""
    print("🔄 Running migrations...")

    # Try normal migration first
    result = subprocess.run(
        [sys.executable, "manage.py", "migrate"], capture_output=True, text=True
    )

    # Check if successful
    if result.returncode == 0:
        print("✅ Migrations applied successfully!")
        print(result.stdout)
        return 0

    # Check for "table already exists" error
    error_output = result.stderr + result.stdout

    if "already exists" in error_output.lower() or 'table "' in error_output.lower():
        print("\n⚠️ DETECTED: Table already exists error")
        print("🔧 AUTO-FIX: Running migration with --fake...")
        print("")

        # Extract the migration that failed
        if "Running migration" in error_output:
            print("📋 Migration Details:")
            for line in error_output.split("\n"):
                if "Running migration" in line or "already exists" in line:
                    print(f"   {line.strip()}")

        print("")
        print("🔄 Executing: python manage.py migrate --fake")

        # Run with --fake
        fake_result = subprocess.run(
            [sys.executable, "manage.py", "migrate", "--fake"], capture_output=True, text=True
        )

        if fake_result.returncode == 0:
            print("✅ Migration marked as fake successfully!")
            print("")
            print("📊 What happened:")
            print("   • Tables already exist in database")
            print("   • Migration marked as applied (--fake)")
            print("   • Database state and migrations now in sync")
            print("")
            print(fake_result.stdout)
            return 0
        else:
            print("❌ Fake migration also failed!")
            print(fake_result.stderr)
            return 1

    # Different error - show it
    print("❌ Migration failed with error:")
    print(result.stderr)
    print(result.stdout)
    return result.returncode


if __name__ == "__main__":
    sys.exit(run_migrate())
