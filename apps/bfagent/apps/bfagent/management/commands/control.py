"""
BF Agent Control Panel
Interactive tool for common development tasks
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

from django.core.cache import cache
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "BF Agent Control Panel - Interactive development tools"

    def handle(self, *args, **options):
        self.show_menu()

    def show_menu(self):
        """Show main menu"""
        while True:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.SUCCESS("🎛️  BF AGENT CONTROL PANEL"))
            self.stdout.write("=" * 80 + "\n")

            menu = """
📡 SERVER TOOLS:
  1. 🔄 Restart Server       - Kill + clean + restart
  2. 💀 Kill Server          - Stop all processes
  3. 🧹 Clean Cache          - Clear Django cache

🔧 GIT TOOLS:
  4. 🚀 Smart Sync           - Auto-commit + push
  5. 📝 Quick Commit         - Commit with timestamp
  6. 💬 Custom Commit        - Commit with your message
  7. 🚀 Custom Commit + Push - Commit + push with your message

🤖 GENERATOR TOOLS:
  8. ⚙️  Run Generator       - Execute auto_compliance_fixer

  0. ❌ Exit

Select (0-8): """

            try:
                choice = input(menu).strip()

                if choice == "0":
                    self.stdout.write(self.style.SUCCESS("\n👋 Goodbye!"))
                    break
                elif choice == "1":
                    self.restart_server()
                elif choice == "2":
                    self.kill_server()
                elif choice == "3":
                    self.clean_cache()
                elif choice == "4":
                    self.smart_sync()
                elif choice == "5":
                    self.quick_commit()
                elif choice == "6":
                    self.custom_commit()
                elif choice == "7":
                    self.custom_commit_push()
                elif choice == "8":
                    self.run_generator()
                else:
                    self.stdout.write(self.style.ERROR("❌ Invalid choice!"))

            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING("\n\n👋 Cancelled by user"))
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"\n❌ Error: {e}"))

    # ========================================================================
    # SERVER TOOLS
    # ========================================================================

    def kill_server(self):
        """Kill all Django server processes"""
        self.stdout.write("\n💀 Killing Django servers...")
        try:
            # Windows: Kill by port
            subprocess.run(
                [
                    "powershell",
                    "-Command",
                    "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | "
                    "ForEach-Object {Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue}",
                ],
                capture_output=True,
                check=False,
            )
            self.stdout.write(self.style.SUCCESS("✅ Server processes killed!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))

    def clean_cache(self):
        """Clear Django cache"""
        self.stdout.write("\n🧹 Clearing cache...")
        try:
            cache.clear()
            self.stdout.write(self.style.SUCCESS("✅ Cache cleared!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))

    def restart_server(self):
        """Complete server restart"""
        self.stdout.write("\n🔄 Restarting server...")

        # 1. Kill
        self.kill_server()

        # 2. Clean cache
        self.clean_cache()

        # 3. Wait
        import time

        time.sleep(1)

        # 4. Restart
        self.stdout.write(self.style.SUCCESS("\n🚀 Starting server..."))
        self.stdout.write(self.style.WARNING("Run in terminal: python manage.py runserver"))

    # ========================================================================
    # GIT TOOLS
    # ========================================================================

    def smart_sync(self):
        """Smart git sync with AI-generated commit message"""
        self.stdout.write("\n🚀 Smart Git Sync...")

        try:
            # 1. Check status
            result = subprocess.run(
                ["git", "status", "--porcelain"], capture_output=True, text=True
            )

            if not result.stdout.strip():
                self.stdout.write(self.style.WARNING("⚠️  No changes to commit"))
                return

            # 2. Show changes
            self.stdout.write("\n📋 Changed files:")
            for line in result.stdout.strip().split("\n")[:10]:
                self.stdout.write(f"  {line}")

            # 3. Generate commit message
            self.stdout.write("\n🤖 Generating commit message...")

            # Get git diff summary
            diff_result = subprocess.run(["git", "diff", "--stat"], capture_output=True, text=True)

            # Simple AI: Extract main changes
            commit_msg = self._generate_commit_message(result.stdout, diff_result.stdout)

            self.stdout.write(f"\n📝 Suggested message:\n{commit_msg}")

            # 4. Confirm
            confirm = input("\n✅ Commit with this message? (y/N): ").strip().lower()

            if confirm != "y":
                custom_msg = input("Enter custom message: ").strip()
                if custom_msg:
                    commit_msg = custom_msg
                else:
                    self.stdout.write(self.style.WARNING("❌ Cancelled"))
                    return

            # 5. Commit & Push
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)

            push = input("\n📤 Push to remote? (Y/n): ").strip().lower()
            if push != "n":
                subprocess.run(["git", "push"], check=True)
                self.stdout.write(self.style.SUCCESS("\n✅ Pushed successfully!"))
            else:
                self.stdout.write(self.style.SUCCESS("\n✅ Committed (not pushed)"))

        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(f"❌ Git error: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))

    def quick_commit(self):
        """Quick commit with timestamp"""
        self.stdout.write("\n📝 Quick Commit...")

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            message = f"Quick sync: {timestamp}"

            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", message], check=True)

            push = input("\n📤 Push? (Y/n): ").strip().lower()
            if push != "n":
                subprocess.run(["git", "push"], check=True)

            self.stdout.write(self.style.SUCCESS("✅ Done!"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))

    def custom_commit(self):
        """Custom commit with user message"""
        self.stdout.write("\n💬 Custom Commit...")

        try:
            # Get commit message
            message = input("\n📝 Enter commit message: ").strip()
            
            if not message:
                self.stdout.write(self.style.WARNING("❌ Cancelled - no message provided"))
                return

            # Commit
            subprocess.run(["git", "add", "-A"], check=True)
            subprocess.run(["git", "commit", "--no-verify", "-m", message], check=True)

            self.stdout.write(self.style.SUCCESS("✅ Committed successfully!"))
            self.stdout.write(self.style.WARNING("💡 Tip: Run option 7 to push, or use 'git push' manually"))

        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(f"❌ Git error: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))

    def custom_commit_push(self):
        """Custom commit + push with user message"""
        self.stdout.write("\n🚀 Custom Commit + Push...")

        try:
            # Get commit message
            message = input("\n📝 Enter commit message: ").strip()
            
            if not message:
                self.stdout.write(self.style.WARNING("❌ Cancelled - no message provided"))
                return

            # Commit
            subprocess.run(["git", "add", "-A"], check=True)
            subprocess.run(["git", "commit", "--no-verify", "-m", message], check=True)
            
            # Push
            self.stdout.write("\n📤 Pushing to remote...")
            subprocess.run(["git", "push"], check=True)

            self.stdout.write(self.style.SUCCESS("✅ Committed and pushed successfully!"))

        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(f"❌ Git error: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))

    def _generate_commit_message(self, status_output, diff_output):
        """Generate commit message from git changes"""
        # Count changes
        lines = status_output.strip().split("\n")
        added = sum(1 for l in lines if l.startswith("A ") or l.startswith("?? "))
        modified = sum(1 for l in lines if l.startswith("M "))
        deleted = sum(1 for l in lines if l.startswith("D "))

        # Build message
        parts = []
        if added:
            parts.append(f"{added} added")
        if modified:
            parts.append(f"{modified} modified")
        if deleted:
            parts.append(f"{deleted} deleted")

        summary = ", ".join(parts) if parts else "updates"

        # Extract main files
        main_files = []
        for line in lines[:3]:
            if len(line) > 3:
                file_path = line[3:].strip()
                if file_path:
                    main_files.append(Path(file_path).name)

        files_str = ", ".join(main_files[:3])

        return f"Update: {summary}\n\nFiles: {files_str}"

    # ========================================================================
    # GENERATOR TOOLS
    # ========================================================================

    def run_generator(self):
        """Run auto_compliance_fixer"""
        self.stdout.write("\n🤖 Running Generator...")

        try:
            base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
            script = base_dir / "scripts" / "auto_compliance_fixer.py"

            if not script.exists():
                self.stdout.write(self.style.ERROR(f"❌ Script not found: {script}"))
                return

            confirm = input("\n⚠️  Regenerate CRUD components? (y/N): ").strip().lower()
            if confirm != "y":
                self.stdout.write(self.style.WARNING("❌ Cancelled"))
                return

            result = subprocess.run(
                [sys.executable, str(script), "--fix"], 
                capture_output=True, 
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            self.stdout.write(result.stdout)

            if result.returncode == 0:
                self.stdout.write(self.style.SUCCESS("\n✅ Generator completed!"))
            else:
                self.stdout.write(self.style.ERROR(f"\n❌ Failed (code {result.returncode})"))
                if result.stderr:
                    self.stdout.write(result.stderr)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
