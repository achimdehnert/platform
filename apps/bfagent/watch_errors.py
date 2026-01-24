#!/usr/bin/env python
"""
Error Watcher - Testmodus
==========================

Startet den autonomen Error Watcher im interaktiven Testmodus.
Während aktiv: Zeigt Fehler live an und ermöglicht manuelle Analyse & Fix.

Usage:
    python watch_errors.py          # Start watcher
    python watch_errors.py --stop   # Stop watcher
    python watch_errors.py --status # Check status
"""

import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

# Add Django to path
django_path = Path(__file__).parent
sys.path.insert(0, str(django_path))

# Import autonomous error fixer
from tools.autonomous_error_fixer import AutonomousErrorFixer

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

try:
    import django

    django.setup()
    print("✅ Django setup successful!")
except Exception as e:
    print(f"❌ Django setup failed: {e}")
    sys.exit(1)


class InteractiveErrorWatcher:
    """
    Interactive Error Watcher for Test Mode.

    Shows errors as they occur and logs them to a file
    that Cascade can read and respond to.
    """

    def __init__(self):
        self.log_file = django_path / "django.log"
        self.error_file = django_path / "error_alerts.txt"
        self.running = False
        self.last_position = 0

    def start(self):
        """Start watching for errors"""
        print("\n" + "=" * 60)
        print("🔍 ERROR WATCHER - TESTMODUS AKTIV")
        print("=" * 60)
        print(f"\n📍 Watching: {self.log_file}")
        print(f"📝 Alerts: {self.error_file}")
        print("\n⚡ Status: MONITORING")
        print("🛑 Stop with: Ctrl+C or python watch_errors.py --stop")
        print("\n" + "=" * 60 + "\n")

        self.running = True

        # Clear old alerts
        if self.error_file.exists():
            self.error_file.unlink()

        # Setup signal handler
        signal.signal(signal.SIGINT, self._signal_handler)

        # If log file doesn't exist, wait for it
        if not self.log_file.exists():
            print("⏳ Waiting for django.log to be created...")
            while not self.log_file.exists() and self.running:
                time.sleep(1)

        # Get initial file size
        self.last_position = self.log_file.stat().st_size

        # Main watch loop
        while self.running:
            self._check_for_errors()
            time.sleep(1)

    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C"""
        print("\n\n🛑 Stopping Error Watcher...")
        self.running = False

    def _check_for_errors(self):
        """Check for new errors in log"""
        if not self.log_file.exists():
            return

        current_size = self.log_file.stat().st_size

        # If file shrank, reset position
        if current_size < self.last_position:
            self.last_position = 0

        # If no new data, return
        if current_size == self.last_position:
            return

        # Read new lines
        with open(self.log_file, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(self.last_position)
            new_lines = f.read()
            self.last_position = current_size

        # Check for errors
        if self._is_error(new_lines):
            self._handle_error(new_lines)

    def _is_error(self, text: str) -> bool:
        """Check if text contains an error"""
        error_keywords = [
            "ERROR",
            "Exception",
            "Traceback",
            "NoReverseMatch",
            "TemplateDoesNotExist",
            "ImportError",
            "ModuleNotFoundError",
            "AttributeError",
        ]
        return any(keyword in text for keyword in error_keywords)

    def _handle_error(self, error_text: str):
        """Handle detected error"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Print to console
        print("\n" + "🐛" * 30)
        print(f"⚠️  ERROR DETECTED at {timestamp}")
        print("🐛" * 30)
        print(error_text[:500])  # First 500 chars
        print("🐛" * 30 + "\n")

        # 🤖 AUTONOMOUS ERROR ANALYSIS
        try:
            fixer = AutonomousErrorFixer()
            analysis = fixer.analyze_error(error_text)
            analysis_text = fixer.format_analysis(analysis)

            # Print analysis to console
            print(analysis_text)

            # Write to alert file for Cascade (with analysis)
            with open(self.error_file, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"{'='*60}\n")
                f.write(error_text)
                f.write(f"\n{analysis_text}")
                f.write(f"\n{'='*60}\n\n")

            print(f"\n✅ Error logged to: {self.error_file}")
            print("💡 Cascade can now read the error + autonomous analysis!\n")

        except Exception as e:
            # Fallback if analysis fails
            print(f"⚠️  Analysis failed: {e}")

            # Write to alert file for Cascade (without analysis)
            with open(self.error_file, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"{'='*60}\n")
                f.write(error_text)
                f.write(f"\n{'='*60}\n\n")

            print(f"✅ Error logged to: {self.error_file}")
            print("💡 Cascade can now read and fix this error!\n")

    def stop(self):
        """Stop the watcher"""
        self.running = False
        print("✅ Error Watcher stopped")

    def status(self):
        """Show watcher status"""
        print("\n" + "=" * 60)
        print("📊 ERROR WATCHER STATUS")
        print("=" * 60)
        print(f"Log File: {self.log_file}")
        print(f"Exists: {'✅' if self.log_file.exists() else '❌'}")
        print(f"Alert File: {self.error_file}")
        print(f"Exists: {'✅' if self.error_file.exists() else '❌'}")

        if self.error_file.exists():
            size = self.error_file.stat().st_size
            print(f"Alert Size: {size} bytes")
            if size > 0:
                print("\n📝 Recent Alerts:")
                with open(self.error_file, "r", encoding="utf-8") as f:
                    print(f.read()[-500:])  # Last 500 chars

        print("=" * 60 + "\n")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Error Watcher - Testmodus")
    parser.add_argument("--stop", action="store_true", help="Stop the watcher")
    parser.add_argument("--status", action="store_true", help="Show status")

    args = parser.parse_args()

    watcher = InteractiveErrorWatcher()

    if args.stop:
        print("🛑 Stop signal sent (if running in separate process)")
        return

    if args.status:
        watcher.status()
        return

    # Start watcher
    try:
        watcher.start()
    except KeyboardInterrupt:
        print("\n✅ Watcher stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
