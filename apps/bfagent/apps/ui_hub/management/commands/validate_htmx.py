"""Management command to validate HTMX code against guardrail rules."""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.ui_hub.services import ValidationService


class Command(BaseCommand):
    """Validate HTMX code against guardrail rules."""

    help = "Validate code against UI Hub guardrail rules"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument("path", type=str, help="Path to file or directory to validate")
        parser.add_argument("--app", type=str, help="App name for scoping", default="")
        parser.add_argument(
            "--fail-on-error", action="store_true", help="Exit with error code if violations found"
        )
        parser.add_argument(
            "--fail-on-warning", action="store_true", help="Exit with error code if warnings found"
        )

    def handle(self, *args, **options):
        """Execute command."""
        path = options["path"]
        app_name = options.get("app", "")
        fail_on_error = options.get("fail_on_error", False)
        fail_on_warning = options.get("fail_on_warning", False)

        validator = ValidationService()

        # Validate
        path_obj = Path(path)

        if path_obj.is_file():
            self.stdout.write(f"Validating file: {path}")
            result = validator.validate_file(str(path_obj))
        elif path_obj.is_dir():
            self.stdout.write(f"Validating directory: {path}")
            result = validator.validate_directory(str(path_obj), app_name)
        else:
            raise CommandError(f"Path not found: {path}")

        if "error" in result:
            raise CommandError(result["error"])

        # Display results
        if path_obj.is_file():
            violations = result.get("violations", [])
            self.stdout.write(f"\nFile: {path}")
            self.stdout.write(f"Violations found: {len(violations)}\n")

            for v in violations:
                severity = v.get("severity", "warning")
                if severity == "error":
                    style = self.style.ERROR
                elif severity == "warning":
                    style = self.style.WARNING
                else:
                    style = self.style.NOTICE

                self.stdout.write(style(f"  [{severity.upper()}] {v.get('message')}"))

        else:
            # Directory validation
            self.stdout.write("\n" + "=" * 70)
            self.stdout.write(self.style.SUCCESS("VALIDATION RESULTS"))
            self.stdout.write("=" * 70 + "\n")

            self.stdout.write(f"Session ID: {result.get('session_id')}")
            self.stdout.write(f"Total files: {result.get('total_files')}")
            self.stdout.write(f"Total violations: {result.get('total_violations')}\n")

            errors = result.get("errors", 0)
            warnings = result.get("warnings", 0)

            if errors > 0:
                self.stdout.write(self.style.ERROR(f"🔴 Errors: {errors}"))
            if warnings > 0:
                self.stdout.write(self.style.WARNING(f"🟡 Warnings: {warnings}"))

            if errors == 0 and warnings == 0:
                self.stdout.write(self.style.SUCCESS("✅ No violations found!"))

            # Show top violations
            results = result.get("results", [])
            if results:
                self.stdout.write("\nTop violations:")
                for r in results[:5]:
                    if r.get("count", 0) > 0:
                        self.stdout.write(f"  • {r['file']}: {r['count']} violations")

        # Exit with error if needed
        if fail_on_error and result.get("errors", 0) > 0:
            raise CommandError("Validation failed with errors")

        if fail_on_warning and result.get("warnings", 0) > 0:
            raise CommandError("Validation failed with warnings")

        self.stdout.write(self.style.SUCCESS("\n✅ Validation complete"))
