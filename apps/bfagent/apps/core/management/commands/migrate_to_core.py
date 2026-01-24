"""
Migration Command: Update Imports to Core Services

Scans project files and updates old imports to use the new
consolidated core services.

Usage:
    python manage.py migrate_to_core --dry-run
    python manage.py migrate_to_core --apply
    python manage.py migrate_to_core --app bfagent
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


@dataclass
class ImportMapping:
    """Maps old imports to new core imports."""

    old_pattern: str
    new_import: str
    description: str


@dataclass
class FileChange:
    """Tracks changes to a single file."""

    file_path: Path
    changes: List[Tuple[str, str]] = field(default_factory=list)

    @property
    def change_count(self) -> int:
        return len(self.changes)


# =============================================================================
# Import Mappings
# =============================================================================

IMPORT_MAPPINGS = [
    # LLM Service
    ImportMapping(
        old_pattern=r"from apps\.bfagent\.services\.llm_service import (\w+)",
        new_import="from apps.core.services.llm import \\1",
        description="LLM Service",
    ),
    ImportMapping(
        old_pattern=r"from apps\.bfagent\.services\.llm import (\w+)",
        new_import="from apps.core.services.llm import \\1",
        description="LLM Service (alt)",
    ),
    ImportMapping(
        old_pattern=r"from apps\.genagent\.services\.llm_provider import (\w+)",
        new_import="from apps.core.services.llm import \\1",
        description="GenAgent LLM Provider",
    ),
    # Cache Service
    ImportMapping(
        old_pattern=r"from apps\.bfagent\.services\.cache_service import (\w+)",
        new_import="from apps.core.services.cache import \\1",
        description="Cache Service",
    ),
    ImportMapping(
        old_pattern=r"from apps\.bfagent\.services\.caching import (\w+)",
        new_import="from apps.core.services.cache import \\1",
        description="Caching Service",
    ),
    # Storage Service
    ImportMapping(
        old_pattern=r"from apps\.bfagent\.services\.storage_service import (\w+)",
        new_import="from apps.core.services.storage import \\1",
        description="Storage Service",
    ),
    ImportMapping(
        old_pattern=r"from apps\.bfagent\.services\.content_storage import (\w+)",
        new_import="from apps.core.services.storage import \\1",
        description="Content Storage",
    ),
    # Export Service
    ImportMapping(
        old_pattern=r"from apps\.bfagent\.services\.book_export import (\w+)",
        new_import="from apps.core.services.export import \\1",
        description="Book Export Service",
    ),
    ImportMapping(
        old_pattern=r"from apps\.bfagent\.services\.handlers\.output\.markdown_file import (\w+)",
        new_import="from apps.core.services.export import \\1",
        description="Markdown File Handler",
    ),
    # Extractors
    ImportMapping(
        old_pattern=r"from apps\.medtrans\.services\.xml_text_extractor import (\w+)",
        new_import="from apps.core.services.extractors import \\1",
        description="XML Text Extractor (PPTX)",
    ),
    ImportMapping(
        old_pattern=r"from apps\.presentation_studio\.handlers\.pdf_content_extractor import (\w+)",
        new_import="from apps.core.services.extractors import \\1",
        description="PDF Content Extractor",
    ),
    ImportMapping(
        old_pattern=r"from apps\.presentation_studio\.handlers\.slide_extractor import (\w+)",
        new_import="from apps.core.services.extractors import \\1",
        description="Slide Extractor",
    ),
    # Handler Base Classes
    ImportMapping(
        old_pattern=r"from apps\.bfagent\.services\.handlers\.base import (\w+)",
        new_import="from apps.core.handlers import \\1",
        description="Handler Base Classes",
    ),
    ImportMapping(
        old_pattern=r"from apps\.genagent\.core\.handlers import (\w+)",
        new_import="from apps.core.handlers import \\1",
        description="GenAgent Handlers",
    ),
]

# Class name mappings for renamed classes
CLASS_MAPPINGS = {
    # Old name -> New name
    "PPTXExtractor": "PPTXExtractor",
    "PDFExtractor": "PDFExtractor",
    "BookExporter": "BookExporter",
    "MarkdownExporter": "MarkdownExporter",
}


class Command(BaseCommand):
    help = "Migrate old imports to consolidated core services"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without making changes",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply the changes to files",
        )
        parser.add_argument(
            "--app",
            type=str,
            help="Only migrate specific app (e.g., bfagent)",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed output",
        )
        parser.add_argument(
            "--report",
            type=str,
            help="Generate report file",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        apply = options["apply"]
        target_app = options.get("app")
        verbose = options.get("verbose", False)
        report_path = options.get("report")

        if not dry_run and not apply:
            self.stdout.write(self.style.WARNING("Please specify --dry-run or --apply"))
            return

        if dry_run and apply:
            raise CommandError("Cannot use both --dry-run and --apply")

        # Find project root
        project_root = Path(settings.BASE_DIR)
        apps_dir = project_root / "apps"

        if not apps_dir.exists():
            raise CommandError(f"Apps directory not found: {apps_dir}")

        self.stdout.write(
            self.style.SUCCESS(f'\n{"="*60}\n' f"Core Services Migration Tool\n" f'{"="*60}\n')
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made\n"))

        # Collect files to process
        files_to_process = self._collect_files(apps_dir, target_app)
        self.stdout.write(f"Found {len(files_to_process)} Python files to scan\n")

        # Process files
        all_changes: List[FileChange] = []

        for file_path in files_to_process:
            changes = self._process_file(file_path, apply, verbose)
            if changes.change_count > 0:
                all_changes.append(changes)

        # Summary
        self._print_summary(all_changes, dry_run)

        # Generate report if requested
        if report_path:
            self._generate_report(all_changes, report_path)
            self.stdout.write(f"\nReport saved to: {report_path}")

    def _collect_files(self, apps_dir: Path, target_app: str = None) -> List[Path]:
        """Collect Python files to process."""
        files = []

        for root, dirs, filenames in os.walk(apps_dir):
            # Skip certain directories
            dirs[:] = [
                d
                for d in dirs
                if d
                not in {
                    "__pycache__",
                    "migrations",
                    ".git",
                    "node_modules",
                    "static",
                    "templates",
                    "media",
                }
            ]

            root_path = Path(root)

            # Filter by app if specified
            if target_app:
                rel_path = root_path.relative_to(apps_dir)
                if not str(rel_path).startswith(target_app):
                    continue

            for filename in filenames:
                if filename.endswith(".py"):
                    files.append(root_path / filename)

        return sorted(files)

    def _process_file(self, file_path: Path, apply: bool, verbose: bool) -> FileChange:
        """Process a single file for import updates."""
        changes = FileChange(file_path=file_path)

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            if verbose:
                self.stdout.write(self.style.WARNING(f"Could not read {file_path}: {e}"))
            return changes

        new_content = content

        # Apply import mappings
        for mapping in IMPORT_MAPPINGS:
            matches = re.findall(mapping.old_pattern, content)
            if matches:
                new_content = re.sub(mapping.old_pattern, mapping.new_import, new_content)
                for match in matches:
                    changes.changes.append(
                        (
                            f"{mapping.description}: {match}",
                            mapping.new_import.replace("\\1", match),
                        )
                    )

        # Apply class name mappings
        for old_name, new_name in CLASS_MAPPINGS.items():
            if old_name in new_content:
                # Only replace in import statements and class usage
                pattern = rf"\b{old_name}\b"
                if re.search(pattern, new_content):
                    new_content = re.sub(pattern, new_name, new_content)
                    changes.changes.append((f"Class rename: {old_name}", new_name))

        # Apply changes if requested
        if apply and changes.change_count > 0:
            file_path.write_text(new_content, encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"✓ Updated: {file_path}"))
        elif verbose and changes.change_count > 0:
            self.stdout.write(f"Would update: {file_path}")
            for old, new in changes.changes:
                self.stdout.write(f"  - {old} → {new}")

        return changes

    def _print_summary(self, all_changes: List[FileChange], dry_run: bool):
        """Print migration summary."""
        total_files = len(all_changes)
        total_changes = sum(c.change_count for c in all_changes)

        self.stdout.write(f'\n{"="*60}')
        self.stdout.write(self.style.SUCCESS("MIGRATION SUMMARY"))
        self.stdout.write(f'{"="*60}\n')

        self.stdout.write(f"Files with changes: {total_files}")
        self.stdout.write(f"Total changes: {total_changes}")

        if total_changes > 0:
            self.stdout.write(f"\nChanges by category:")

            # Group by description
            by_category: Dict[str, int] = {}
            for fc in all_changes:
                for old, _ in fc.changes:
                    cat = old.split(":")[0]
                    by_category[cat] = by_category.get(cat, 0) + 1

            for cat, count in sorted(by_category.items()):
                self.stdout.write(f"  - {cat}: {count}")

        if dry_run and total_changes > 0:
            self.stdout.write(self.style.WARNING(f"\nRun with --apply to make these changes"))

    def _generate_report(self, all_changes: List[FileChange], report_path: str):
        """Generate migration report."""
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Core Services Migration Report\n\n")
            f.write(f'Generated: {__import__("datetime").datetime.now()}\n\n')

            f.write("## Summary\n\n")
            f.write(f"- Files changed: {len(all_changes)}\n")
            f.write(f"- Total changes: {sum(c.change_count for c in all_changes)}\n\n")

            f.write("## Changes by File\n\n")

            for fc in all_changes:
                f.write(f"### {fc.file_path}\n\n")
                for old, new in fc.changes:
                    f.write(f"- {old}\n")
                    f.write(f"  → `{new}`\n")
                f.write("\n")
