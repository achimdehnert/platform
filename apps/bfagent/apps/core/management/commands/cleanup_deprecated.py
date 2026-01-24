"""
Cleanup Command: Mark or Remove Deprecated Service Files

After migration to core services, this command helps clean up
the old service files.

Usage:
    python manage.py cleanup_deprecated --dry-run
    python manage.py cleanup_deprecated --mark
    python manage.py cleanup_deprecated --backup
    python manage.py cleanup_deprecated --delete
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

# =============================================================================
# Deprecated Files List
# =============================================================================

DEPRECATED_FILES = [
    # LLM Service (Phase 2) - Now in apps/core/services/llm/
    {
        "path": "apps/bfagent/services/llm_service.py",
        "replacement": "apps.core.services.llm",
        "phase": 2,
    },
    {
        "path": "apps/genagent/services/llm_provider.py",
        "replacement": "apps.core.services.llm",
        "phase": 2,
    },
    # Cache Service (Phase 3) - Now in apps/core/services/cache/
    {
        "path": "apps/bfagent/services/cache_service.py",
        "replacement": "apps.core.services.cache",
        "phase": 3,
    },
    {
        "path": "apps/bfagent/services/caching.py",
        "replacement": "apps.core.services.cache",
        "phase": 3,
    },
    # Storage Service (Phase 4) - Now in apps/core/services/storage/
    {
        "path": "apps/bfagent/services/storage_service.py",
        "replacement": "apps.core.services.storage",
        "phase": 4,
    },
    {
        "path": "apps/bfagent/services/content_storage.py",
        "replacement": "apps.core.services.storage",
        "phase": 4,
    },
    # Export Service (Phase 5) - Now in apps/core/services/export/
    # Note: book_export.py may still be in use, check imports first
    {
        "path": "apps/bfagent/services/book_export.py",
        "replacement": "apps.core.services.export",
        "phase": 5,
    },
    # Extractors (Phase 6) - Now in apps/core/services/extractors/
    {
        "path": "apps/medtrans/services/xml_text_extractor.py",
        "replacement": "apps.core.services.extractors.PPTXExtractor",
        "phase": 6,
    },
    {
        "path": "apps/presentation_studio/handlers/pdf_content_extractor.py",
        "replacement": "apps.core.services.extractors.PDFExtractor",
        "phase": 6,
    },
    {
        "path": "apps/presentation_studio/handlers/slide_extractor.py",
        "replacement": "apps.core.services.extractors.PPTXExtractor",
        "phase": 6,
    },
]

DEPRECATION_HEADER = '''"""
================================================================================
DEPRECATED - DO NOT USE
================================================================================

This file has been deprecated and replaced by the consolidated Core Services.

Replacement: {replacement}
Deprecated: {date}
Migration Phase: {phase}

This file is kept for reference only. All new code should use the replacement.

To migrate existing code, run:
    python manage.py migrate_to_core --apply

================================================================================
"""

'''


class Command(BaseCommand):
    help = "Clean up deprecated service files after core migration"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )
        parser.add_argument(
            "--mark",
            action="store_true",
            help="Add DEPRECATED header to files",
        )
        parser.add_argument(
            "--backup",
            action="store_true",
            help="Move files to _deprecated/ backup folder",
        )
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete deprecated files (use with caution!)",
        )
        parser.add_argument(
            "--check-imports",
            action="store_true",
            help="Check if deprecated files are still imported anywhere",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        mark = options["mark"]
        backup = options["backup"]
        delete = options["delete"]
        check_imports = options["check_imports"]

        # Validate options
        actions = sum([mark, backup, delete])
        if actions > 1:
            raise CommandError("Cannot combine --mark, --backup, and --delete")

        if not any([dry_run, mark, backup, delete, check_imports]):
            self.stdout.write(
                self.style.WARNING(
                    "Please specify an action: --dry-run, --mark, --backup, --delete, or --check-imports"
                )
            )
            return

        project_root = Path(settings.BASE_DIR)

        self.stdout.write(
            self.style.SUCCESS(
                "\n" + "=" * 60 + "\n" "Deprecated Files Cleanup Tool\n" + "=" * 60 + "\n"
            )
        )

        # Find existing deprecated files
        existing_files = []
        missing_files = []

        for file_info in DEPRECATED_FILES:
            file_path = project_root / file_info["path"]
            if file_path.exists():
                existing_files.append((file_path, file_info))
            else:
                missing_files.append(file_info["path"])

        # Report status
        self.stdout.write(f"Deprecated files found: {len(existing_files)}")
        self.stdout.write(f"Already removed: {len(missing_files)}\n")

        if existing_files:
            self.stdout.write("Files to process:")
            for file_path, info in existing_files:
                self.stdout.write(f'  - {info["path"]}')
                self.stdout.write(f'    -> {info["replacement"]}')
            self.stdout.write("")

        # Check imports if requested
        if check_imports:
            self._check_imports(project_root, existing_files)
            return

        # Process files
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made\n"))
            self._show_plan(existing_files, mark, backup, delete)
        elif mark:
            self._mark_files(existing_files)
        elif backup:
            self._backup_files(project_root, existing_files)
        elif delete:
            self._delete_files(existing_files)

    def _show_plan(self, files: List[Tuple[Path, dict]], mark: bool, backup: bool, delete: bool):
        """Show what would be done."""
        if not files:
            self.stdout.write("No files to process.")
            return

        action = (
            "mark as deprecated" if mark else "backup" if backup else "delete" if delete else "list"
        )

        self.stdout.write(f"Would {action}:")
        for file_path, info in files:
            size = file_path.stat().st_size
            self.stdout.write(f'  {info["path"]} ({size} bytes)')

    def _check_imports(self, project_root: Path, files: List[Tuple[Path, dict]]):
        """Check if deprecated files are still imported."""
        self.stdout.write(self.style.SUCCESS("\nChecking for remaining imports...\n"))

        # Build search patterns
        import_patterns = []
        for file_path, info in files:
            # Convert path to module name
            module_path = info["path"].replace("/", ".").replace("\\", ".").replace(".py", "")
            import_patterns.append(module_path)

        # Search all Python files
        found_imports = {}

        for py_file in project_root.rglob("*.py"):
            # Skip deprecated files themselves
            if any(str(py_file).endswith(info["path"].replace("/", os.sep)) for _, info in files):
                continue

            # Skip migrations and cache
            if "__pycache__" in str(py_file) or "migrations" in str(py_file):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")

                for pattern in import_patterns:
                    # Check various import styles
                    if pattern in content:
                        if pattern not in found_imports:
                            found_imports[pattern] = []
                        found_imports[pattern].append(str(py_file.relative_to(project_root)))
            except Exception:
                pass

        if found_imports:
            self.stdout.write(self.style.WARNING("Found remaining imports:\n"))
            for module, files in found_imports.items():
                self.stdout.write(f"  {module}:")
                for f in files[:5]:  # Show max 5
                    self.stdout.write(f"    - {f}")
                if len(files) > 5:
                    self.stdout.write(f"    ... and {len(files) - 5} more")
            self.stdout.write(
                self.style.WARNING('\nRun "python manage.py migrate_to_core --apply" first!')
            )
        else:
            self.stdout.write(self.style.SUCCESS("No remaining imports found. Safe to clean up!"))

    def _mark_files(self, files: List[Tuple[Path, dict]]):
        """Add deprecation header to files."""
        self.stdout.write("Marking files as deprecated...\n")

        for file_path, info in files:
            try:
                content = file_path.read_text(encoding="utf-8")

                # Check if already marked
                if "DEPRECATED - DO NOT USE" in content:
                    self.stdout.write(f'  Already marked: {info["path"]}')
                    continue

                # Add header
                header = DEPRECATION_HEADER.format(
                    replacement=info["replacement"],
                    date=datetime.now().strftime("%Y-%m-%d"),
                    phase=info["phase"],
                )

                new_content = header + content
                file_path.write_text(new_content, encoding="utf-8")

                self.stdout.write(self.style.SUCCESS(f'  Marked: {info["path"]}'))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error marking {info["path"]}: {e}'))

        self.stdout.write(self.style.SUCCESS("\nDone!"))

    def _backup_files(self, project_root: Path, files: List[Tuple[Path, dict]]):
        """Move files to backup folder."""
        backup_dir = project_root / "_deprecated" / datetime.now().strftime("%Y%m%d")
        backup_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write(f"Backing up to: {backup_dir}\n")

        for file_path, info in files:
            try:
                # Create subdirectory structure
                rel_path = Path(info["path"])
                dest_path = backup_dir / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                # Move file
                shutil.move(str(file_path), str(dest_path))

                self.stdout.write(self.style.SUCCESS(f'  Backed up: {info["path"]}'))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error backing up {info["path"]}: {e}'))

        self.stdout.write(self.style.SUCCESS(f"\nBackup complete! Files in: {backup_dir}"))

    def _delete_files(self, files: List[Tuple[Path, dict]]):
        """Delete deprecated files."""
        self.stdout.write(self.style.WARNING("Deleting deprecated files...\n"))

        # Confirm
        self.stdout.write(self.style.WARNING(f"This will permanently delete {len(files)} files!"))
        confirm = input('Type "yes" to confirm: ')

        if confirm.lower() != "yes":
            self.stdout.write("Cancelled.")
            return

        for file_path, info in files:
            try:
                file_path.unlink()
                self.stdout.write(self.style.SUCCESS(f'  Deleted: {info["path"]}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error deleting {info["path"]}: {e}'))

        self.stdout.write(self.style.SUCCESS("\nDeletion complete!"))
