#!/usr/bin/env python
"""
System-Daten Restore Script
Kopiert essentielle System-Konfiguration von Backup zurück in neue DB
"""
import sqlite3
import sys
from pathlib import Path

# Backup file (latest)
BACKUP_FILE = "bfagent_backup_20251211_130156.db"
TARGET_DB = "bfagent.db"

# System tables (NO user data, only configuration)
SYSTEM_TABLES = [
    "core_domain",
    "core_handler",
    "core_handlercategory",
    "llms",
    "agents",
    "agent_types",
    "domain_arts",
    "domain_types",
    "domain_phases",
    "handlers",
    "action_handlers",
    "control_center_workflowdomain",
    "control_center_navigationsection",
    "control_center_navigationitem",
    "writing_hub_handlerphase",
    "genagent_phase",
    "genagent_action",
    "genagent_customdomain",
    "bfagent_mcp_domain",
    "bfagent_mcp_phase",
    "bfagent_mcp_handler",
    "bfagent_mcp_bestpractice",
    "bfagent_mcp_prompttemplate",
]


def main():
    print("\n" + "=" * 50)
    print(" System-Daten Restore")
    print("=" * 50 + "\n")

    # Check files exist
    if not Path(BACKUP_FILE).exists():
        print(f"❌ Backup nicht gefunden: {BACKUP_FILE}")
        sys.exit(1)

    if not Path(TARGET_DB).exists():
        print(f"❌ Target DB nicht gefunden: {TARGET_DB}")
        print("   Führe erst 'python manage.py migrate' aus!")
        sys.exit(1)

    try:
        # Connect
        dst = sqlite3.connect(TARGET_DB)
        dst.execute(f"ATTACH DATABASE '{BACKUP_FILE}' AS backup")

        restored = 0
        skipped = 0

        print("Kopiere System-Daten...\n")

        for table in SYSTEM_TABLES:
            try:
                # Check if table exists in backup
                cursor = dst.execute(
                    f"SELECT COUNT(*) FROM backup.sqlite_master "
                    f'WHERE type="table" AND name="{table}"'
                )

                if cursor.fetchone()[0] == 0:
                    print(f"  ⊗ {table:<40} (nicht im Backup)")
                    skipped += 1
                    continue

                # Copy data
                dst.execute(f"INSERT OR IGNORE INTO {table} SELECT * FROM backup.{table}")
                count = dst.execute("SELECT changes()").fetchone()[0]

                if count > 0:
                    print(f"  ✓ {table:<40} {count:>4} rows")
                    restored += 1
                else:
                    print(f"  ○ {table:<40} {count:>4} rows (leer)")

            except sqlite3.Error as e:
                error_msg = str(e)[:40]
                print(f"  ✗ {table:<40} ERROR: {error_msg}")
                skipped += 1

        dst.commit()
        dst.close()

        print("\n" + "=" * 50)
        print(f"✅ Restored: {restored} tables")
        print(f"⊗  Skipped:  {skipped} tables")
        print("=" * 50 + "\n")

        sys.exit(0)

    except Exception as e:
        print(f"\n❌ FEHLER: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
