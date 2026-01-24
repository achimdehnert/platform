"""
Django Management Command for Code Review

Usage:
    python manage.py review_code
    python manage.py review_code --path apps/bfagent/
    python manage.py review_code --security --performance
    python manage.py review_code --auto-fix
    python manage.py review_code --output review.md
"""

import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError

from apps.bfagent.review.core import ReviewOrchestrator, ReviewSeverity
from apps.bfagent.review.handlers import (
    SecurityReviewHandler,
    PerformanceReviewHandler,
    IllustrationReviewHandler,
)


class Command(BaseCommand):
    help = "Run code review on BF Agent codebase"

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            type=str,
            default='apps/bfagent/',
            help='Path to review (default: apps/bfagent/)'
        )
        parser.add_argument(
            '--security',
            action='store_true',
            help='Run security checks only'
        )
        parser.add_argument(
            '--performance',
            action='store_true',
            help='Run performance checks only'
        )
        parser.add_argument(
            '--illustration',
            action='store_true',
            help='Run illustration-specific checks only'
        )
        parser.add_argument(
            '--auto-fix',
            action='store_true',
            help='Automatically fix issues where possible'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path (default: stdout)'
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['text', 'json', 'markdown'],
            default='text',
            help='Output format'
        )
        parser.add_argument(
            '--fail-on-critical',
            action='store_true',
            help='Exit with error code if critical issues found'
        )

    def handle(self, *args, **options):
        path_str = options['path']
        target_path = Path(path_str)

        if not target_path.exists():
            raise CommandError(f"Path does not exist: {path_str}")

        self.stdout.write(f"🔍 Reviewing: {target_path}")

        # Create orchestrator
        orchestrator = ReviewOrchestrator()

        # Register handlers based on options
        all_checks = not any([
            options['security'],
            options['performance'],
            options['illustration']
        ])

        if all_checks or options['security']:
            orchestrator.register_review_handler(SecurityReviewHandler())
            self.stdout.write("  ✓ Security checks enabled")

        if all_checks or options['performance']:
            orchestrator.register_review_handler(PerformanceReviewHandler())
            self.stdout.write("  ✓ Performance checks enabled")

        if all_checks or options['illustration']:
            orchestrator.register_review_handler(IllustrationReviewHandler())
            self.stdout.write("  ✓ Illustration checks enabled")

        # Run review
        self.stdout.write("\n" + "="*70)
        result = orchestrator.review(
            target_path=target_path,
            auto_fix=options['auto_fix']
        )
        self.stdout.write("="*70 + "\n")

        # Output results
        output_format = options['format']
        output_file = options.get('output')

        if output_format == 'json':
            output_content = json.dumps(result.to_dict(), indent=2)
        elif output_format == 'markdown':
            output_content = self._format_markdown(result)
        else:
            output_content = self._format_text(result)

        if output_file:
            Path(output_file).write_text(output_content, encoding='utf-8')
            self.stdout.write(self.style.SUCCESS(f"\n✅ Report saved to: {output_file}"))
        else:
            self.stdout.write(output_content)

        # Summary
        stats = result.to_dict()['stats']
        self.stdout.write("\n" + "="*70)
        self.stdout.write("📊 SUMMARY")
        self.stdout.write("="*70)
        self.stdout.write(f"Files reviewed: {result.files_reviewed}")
        self.stdout.write(f"Duration: {result.duration_seconds:.2f}s")
        self.stdout.write(f"Total findings: {stats['total']}")
        self.stdout.write(f"  • Critical: {stats['critical']}")
        self.stdout.write(f"  • Error: {stats['error']}")
        self.stdout.write(f"  • Warning: {stats['warning']}")
        self.stdout.write(f"  • Info: {stats['info']}")
        self.stdout.write(f"  • Style: {stats['style']}")

        # Exit with error if critical issues and flag set
        if options['fail_on_critical'] and result.has_critical():
            self.stdout.write(self.style.ERROR("\n❌ CRITICAL ISSUES FOUND!"))
            raise CommandError("Critical issues detected - failing build")

        if stats['total'] == 0:
            self.stdout.write(self.style.SUCCESS("\n✅ No issues found!"))
        elif stats['critical'] > 0 or stats['error'] > 0:
            self.stdout.write(self.style.ERROR(f"\n⚠️  {stats['critical'] + stats['error']} issues require attention"))
        else:
            self.stdout.write(self.style.WARNING(f"\n⚠️  {stats['total']} issues found"))

    def _format_text(self, result):
        """Format as plain text"""
        lines = []
        for finding in result.findings:
            severity_icon = self._get_severity_icon(finding.severity)
            lines.append(f"{severity_icon} [{finding.severity.value.upper()}] {finding.title}")
            lines.append(f"  File: {finding.file_path}")
            if finding.line_number:
                lines.append(f"  Line: {finding.line_number}")
            lines.append(f"  {finding.description}")
            if finding.suggestion:
                lines.append(f"  💡 Suggestion: {finding.suggestion}")
            lines.append("")
        return "\n".join(lines)

    def _format_markdown(self, result):
        """Format as markdown"""
        lines = [
            "# Code Review Report",
            "",
            f"**Duration:** {result.duration_seconds:.2f}s",
            f"**Files Reviewed:** {result.files_reviewed}",
            f"**Total Findings:** {len(result.findings)}",
            "",
            "## Summary by Severity",
            ""
        ]

        stats = result.to_dict()['stats']
        for severity in ['critical', 'error', 'warning', 'info', 'style']:
            count = stats[severity]
            if count > 0:
                lines.append(f"- **{severity.upper()}:** {count}")

        lines.extend(["", "## Detailed Findings", ""])

        for finding in result.findings:
            severity_badge = f"`{finding.severity.value.upper()}`"
            lines.append(f"### [{severity_badge}] {finding.title}")
            lines.append(f"- **File:** `{finding.file_path}`")
            if finding.line_number:
                lines.append(f"- **Line:** {finding.line_number}")
            lines.append(f"- **Description:** {finding.description}")
            if finding.code_snippet:
                lines.append(f"- **Code:**")
                lines.append(f"  ```python")
                lines.append(f"  {finding.code_snippet}")
                lines.append(f"  ```")
            if finding.suggestion:
                lines.append(f"- **Suggestion:** {finding.suggestion}")
            lines.append("")

        return "\n".join(lines)

    def _get_severity_icon(self, severity):
        """Get icon for severity level"""
        icons = {
            ReviewSeverity.CRITICAL: "🔴",
            ReviewSeverity.ERROR: "❌",
            ReviewSeverity.WARNING: "⚠️",
            ReviewSeverity.INFO: "ℹ️",
            ReviewSeverity.STYLE: "💅",
        }
        return icons.get(severity, "•")
