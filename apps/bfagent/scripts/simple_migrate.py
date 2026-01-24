"""
Simple SQLite to PostgreSQL migration using Django management commands
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)

    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode != 0:
        print(f"❌ Failed: {description}")
        return False

    print(f"✅ Success: {description}")
    return True


def main():
    project_root = Path(__file__).parent.parent

    print("\n" + "=" * 60)
    print("SQLite → PostgreSQL Migration")
    print("=" * 60)

    # Create fixtures directory
    fixtures_dir = project_root / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)

    backup_file = fixtures_dir / "data_backup.json"

    # Step 1: Export from SQLite
    print("\n📤 STEP 1: Export from SQLite")
    cmd = [
        "python",
        "manage.py",
        "dumpdata",
        "--settings=config.settings.base",
        "--exclude",
        "contenttypes",
        "--exclude",
        "auth.permission",
        "--exclude",
        "sessions.session",
        "--exclude",
        "admin.logentry",
        "--natural-foreign",
        "--natural-primary",
        "--indent",
        "2",
        "--output",
        str(backup_file),
    ]

    if not run_command(cmd, "Export SQLite data"):
        return 1

    file_size = backup_file.stat().st_size / 1024
    print(f"\n📦 Backup file: {backup_file} ({file_size:.2f} KB)")

    # Step 2: Import to PostgreSQL
    print("\n📥 STEP 2: Import to PostgreSQL")
    cmd = [
        "python",
        "manage.py",
        "loaddata",
        "--settings=config.settings.development",
        str(backup_file),
    ]

    if not run_command(cmd, "Import to PostgreSQL"):
        print("\n⚠️  You can retry with:")
        print(f"   python manage.py loaddata {backup_file}")
        return 1

    print("\n" + "=" * 60)
    print("✅ Migration Complete!")
    print("=" * 60)
    print("\nYour data is now in PostgreSQL!")
    print("SQLite backup kept at: bfagent.db")

    return 0


if __name__ == "__main__":
    sys.exit(main())
