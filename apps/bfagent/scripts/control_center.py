#!/usr/bin/env python
"""
BF Agent Control Center
Stable UTF-8 safe control panel for system management
"""

import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 encoding
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


class ControlCenter:
    """Main control center for BF Agent system management"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.db_path = self.project_root / "bfagent.db"

    def clear_screen(self):
        """Clear terminal screen"""
        os.system("cls" if os.name == "nt" else "clear")

    def print_header(self):
        """Print control center header"""
        print("=" * 70)
        print("  🎛️  BF AGENT - CONTROL CENTER")
        print("=" * 70)
        print()

    def get_database_info(self):
        """Get database statistics"""
        info = {"exists": False, "size_mb": 0, "modified": "N/A", "tables": 0, "records": {}}

        if self.db_path.exists():
            info["exists"] = True
            size_bytes = self.db_path.stat().st_size
            info["size_mb"] = size_bytes / (1024 * 1024)
            info["modified"] = datetime.fromtimestamp(self.db_path.stat().st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            try:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()

                # Count tables
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                info["tables"] = cursor.fetchone()[0]

                # Count records in key tables
                for table in ["bookprojects", "characters", "bookchapters", "agents"]:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        info["records"][table] = cursor.fetchone()[0]
                    except sqlite3.OperationalError:
                        info["records"][table] = 0

                conn.close()
            except Exception as e:
                print(f"⚠️  Database read error: {e}")

        return info

    def get_backup_info(self):
        """Get backup files information"""
        backup_pattern = "bfagent_backup_*.db"
        backups = list(self.project_root.glob(backup_pattern))

        return {
            "count": len(backups),
            "latest": max((b.stat().st_mtime for b in backups), default=None),
            "total_size_mb": sum(b.stat().st_size for b in backups) / (1024 * 1024),
        }

    def run_django_check(self):
        """Run Django system check"""
        try:
            result = subprocess.run(
                [sys.executable, "manage.py", "check"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout if result.returncode == 0 else result.stderr,
            }
        except Exception as e:
            return {"success": False, "output": f"Error running check: {e}"}

    def get_tool_registry_status(self):
        """Get tool registry status"""
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "manage.py",
                    "shell",
                    "-c",
                    "from apps.bfagent.utils.registry import registry; "
                    "print(f'{len(registry.tools)} tools registered')",
                ],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return "Unknown"
        except Exception:
            return "Error checking registry"

    def display_system_status(self):
        """Display comprehensive system status"""
        print("📊 SYSTEM STATUS")
        print("-" * 70)

        # Django Check
        print("\n🔍 Django System Check:")
        check = self.run_django_check()
        if check["success"]:
            print("   ✅ No issues found")
        else:
            print(f"   ⚠️  {check['output'][:100]}...")

        # Tool Registry
        print("\n🛠️  Tool Registry:")
        print(f"   {self.get_tool_registry_status()}")

        print()

    def display_database_status(self):
        """Display database status"""
        print("🗄️  DATABASE STATUS")
        print("-" * 70)

        db_info = self.get_database_info()

        if db_info["exists"]:
            print(f"   ✅ Database: bfagent.db")
            print(f"   📊 Size: {db_info['size_mb']:.2f} MB")
            print(f"   📅 Modified: {db_info['modified']}")
            print(f"   📋 Tables: {db_info['tables']}")

            if db_info["records"]:
                print("\n   📈 Record Counts:")
                for table, count in db_info["records"].items():
                    print(f"      • {table.capitalize()}: {count}")
        else:
            print("   ⚠️  Database not found!")

        print()

    def display_backup_status(self):
        """Display backup status"""
        print("📦 BACKUP STATUS")
        print("-" * 70)

        backup_info = self.get_backup_info()

        print(f"   Backups Available: {backup_info['count']}")
        if backup_info["latest"]:
            latest_time = datetime.fromtimestamp(backup_info["latest"])
            print(f"   Latest Backup: {latest_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if backup_info["count"] > 0:
            print(f"   Total Size: {backup_info['total_size_mb']:.2f} MB")
        else:
            print("   ⚠️  No backups found")

        print()

    def display_available_commands(self):
        """Display available management commands"""
        print("🔧 AVAILABLE COMMANDS")
        print("-" * 70)

        commands = [
            ("make menu", "Interactive command menu"),
            ("make dev", "Start development server"),
            ("make quick", "Quick system check"),
            ("make migrate", "Run database migrations"),
            ("make test", "Run test suite"),
            ("make backup", "Create database backup"),
            ("", ""),
            ("make refactor-agent-architecture", "Full architecture refactor"),
            ("make rollback-agent-architecture", "Restore from backup"),
            ("make setup-agent-actions", "Setup AgentActions"),
            ("make setup-phase-agents", "Setup Phase-Agent mappings"),
            ("make setup-workflows", "Setup Workflow templates"),
        ]

        for cmd, desc in commands:
            if cmd:
                print(f"   {cmd:<35} - {desc}")
            else:
                print()

        print()

    def display_quick_actions(self):
        """Display quick action menu"""
        print("⚡ QUICK ACTIONS")
        print("-" * 70)
        print()
        print("   1. 🚀 Start Development Server        (d)")
        print("   2. 🔍 Run Django Check                (c)")
        print("   3. 📦 Create Database Backup          (b)")
        print("   4. 🧪 Run Tests                       (t)")
        print("   5. 📊 Refresh Stats                   (r)")
        print("   6. 🎛️  Open Interactive Menu           (m)")
        print("   7. 🗂️  Open Django Shell               (s)")
        print("   8. 📝 View Recent Logs                (l)")
        print()
        print("   0. ❌ Exit                            (q)")
        print()

    def view_recent_logs(self):
        """Display recent log entries"""
        log_file = self.project_root / "django.log"

        if not log_file.exists():
            print("⚠️  No log file found")
            return

        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                recent = lines[-50:]  # Last 50 lines

            print("\n📝 RECENT LOGS (Last 50 lines)")
            print("-" * 70)
            for line in recent:
                print(line.rstrip())
        except Exception as e:
            print(f"❌ Error reading logs: {e}")

    def run_action(self, action):
        """Execute selected action"""
        # Map shortcuts to numbers
        shortcut_map = {
            "d": "1",
            "c": "2",
            "b": "3",
            "t": "4",
            "r": "5",
            "m": "6",
            "s": "7",
            "l": "8",
            "q": "0",
        }

        # Convert shortcut to number
        action = shortcut_map.get(action.lower(), action)

        actions = {
            "1": ("python manage.py runserver 0.0.0.0:8000", "Starting server..."),
            "2": ("python manage.py check", "Running system check..."),
            "3": ("python manage.py backup_db", "Creating backup..."),
            "4": ("python manage.py test", "Running tests..."),
            "5": (None, "refresh"),
            "6": ("python scripts/make_interactive.py", "Opening interactive menu..."),
            "7": ("python manage.py shell", "Opening Django shell..."),
            "8": (None, "view_logs"),
        }

        if action not in actions:
            print("❌ Invalid action")
            return False

        cmd, msg = actions[action]

        if msg == "refresh":
            return True

        if msg == "view_logs":
            self.view_recent_logs()
            return False

        print(f"\n{msg}\n")

        if cmd:
            try:
                subprocess.run(cmd.split(), cwd=str(self.project_root), encoding="utf-8")
            except KeyboardInterrupt:
                print("\n⚠️  Action cancelled")
            except Exception as e:
                print(f"❌ Error: {e}")

        return False

    def run(self):
        """Main control center loop"""
        while True:
            self.clear_screen()
            self.print_header()

            # Display all status sections
            self.display_system_status()
            self.display_database_status()
            self.display_backup_status()
            self.display_available_commands()
            self.display_quick_actions()

            # Get user input
            try:
                choice = input("Deine Wahl: ").strip()

                # Handle exit
                if choice in ["0", "q", "Q"]:
                    print("\n👋 Bis bald!")
                    break

                # Handle all actions (numbers and shortcuts)
                valid_choices = [
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "7",
                    "8",
                    "d",
                    "c",
                    "b",
                    "t",
                    "r",
                    "m",
                    "s",
                    "l",
                ]

                if choice.lower() in valid_choices:
                    should_refresh = self.run_action(choice)
                    if should_refresh:
                        continue
                    input("\n⏎ Drücke Enter um fortzufahren...")
                else:
                    print("❌ Ungültige Auswahl")
                    input("\n⏎ Drücke Enter um fortzufahren...")

            except KeyboardInterrupt:
                print("\n\n👋 Bis bald!")
                break
            except Exception as e:
                print(f"\n❌ Fehler: {e}")
                input("\n⏎ Drücke Enter um fortzufahren...")


def main():
    """Entry point for control center"""
    try:
        control = ControlCenter()
        control.run()
    except Exception as e:
        print(f"❌ Critical error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
