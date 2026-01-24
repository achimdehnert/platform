#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

# CRITICAL: Force UTF-8 Mode BEFORE any Django imports
os.environ["PYTHONUTF8"] = "1"

# Windows: Force UTF-8 for console and file operations
if sys.platform == "win32":
    # Force UTF-8 console code page
    try:
        import locale

        locale.setlocale(locale.LC_ALL, "")
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except:
        pass


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
