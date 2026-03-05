"""
aifw/management/commands/check_aifw_config.py

Management command: python manage.py check_aifw_config [--fix] [--strict]

Purpose: Verify that every active AIActionType code has at least one catch-all row
(quality_level=NULL, priority=NULL). Missing catch-all rows cause ConfigurationError
at runtime — this command is the CI gate that prevents that.

ADR-097 Release Checklist Step 12. Fills gap G-097-01.

Usage:
    # Check only (exit 0 if OK, exit 1 if problems found):
    python manage.py check_aifw_config

    # Strict mode — also verify TierQualityMapping has all expected tiers:
    python manage.py check_aifw_config --strict

    # Auto-fix missing catch-all rows using default model from any existing row:
    python manage.py check_aifw_config --fix

    # Both:
    python manage.py check_aifw_config --strict --fix

Exit codes:
    0 — All checks passed
    1 — Problems found (--fix was not used or fix failed)
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

EXPECTED_TIERS = ("premium", "pro", "freemium")


class Command(BaseCommand):
    help = (
        "Verify aifw configuration: catch-all AIActionType rows and TierQualityMapping seeds. "
        "Use in CI before deployment. Exit code 1 if problems found."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Auto-create missing catch-all rows and seed missing TierQualityMapping entries.",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help=(
                "Also verify TierQualityMapping has rows for expected tiers "
                f"({', '.join(EXPECTED_TIERS)})."
            ),
        )

    def handle(self, *args, **options) -> None:
        fix = options["fix"]
        strict = options["strict"]
        problems: list[str] = []

        # ── Check 1: catch-all rows ───────────────────────────────────────────
        problems += self._check_catchall_rows(fix=fix)

        # ── Check 2: TierQualityMapping seeds (--strict) ──────────────────────
        if strict:
            problems += self._check_tier_mappings(fix=fix)

        # ── Check 3: priority column valid values ─────────────────────────────
        problems += self._check_priority_values()

        # ── Check 4: quality_level range ──────────────────────────────────────
        problems += self._check_quality_level_range()

        # ── Report ────────────────────────────────────────────────────────────
        if problems:
            self.stderr.write(self.style.ERROR(f"\n❌ {len(problems)} problem(s) found:\n"))
            for i, p in enumerate(problems, 1):
                self.stderr.write(f"  {i}. {p}")
            if not fix:
                self.stderr.write(
                    self.style.WARNING(
                        "\n  Tip: Run with --fix to auto-correct resolvable issues."
                    )
                )
            raise CommandError("aifw configuration check failed. See above.")
        else:
            self.stdout.write(self.style.SUCCESS("✅ aifw configuration check passed."))

    def _check_catchall_rows(self, *, fix: bool) -> list[str]:
        """Verify every active action_code has a catch-all row."""
        from aifw.models import AIActionType

        problems: list[str] = []

        active_codes = (
            AIActionType.objects
            .filter(is_active=True)
            .values_list("code", flat=True)
            .distinct()
        )

        catchall_codes = set(
            AIActionType.objects
            .filter(is_active=True, quality_level__isnull=True, priority__isnull=True)
            .values_list("code", flat=True)
        )

        missing = [c for c in active_codes if c not in catchall_codes]
        if not missing:
            self.stdout.write(f"  ✓ All {len(active_codes)} action codes have a catch-all row.")
            return []

        for code in missing:
            if fix:
                created = self._create_catchall_row(code)
                if created:
                    self.stdout.write(
                        self.style.WARNING(f"  ⚠ Created catch-all row for action_code={code!r}.")
                    )
                else:
                    problems.append(
                        f"action_code={code!r}: no catch-all row and auto-fix failed "
                        f"(no existing row to copy model from)."
                    )
            else:
                problems.append(
                    f"action_code={code!r}: no catch-all row "
                    f"(quality_level=NULL, priority=NULL). "
                    f"This WILL cause ConfigurationError at runtime."
                )

        return problems

    def _create_catchall_row(self, code: str) -> bool:
        """Create a catch-all row by cloning the first existing row for this code."""
        from aifw.models import AIActionType

        template = AIActionType.objects.filter(code=code, is_active=True).first()
        if template is None:
            return False

        with transaction.atomic():
            AIActionType.objects.get_or_create(
                code=code,
                quality_level=None,
                priority=None,
                defaults={
                    "name": f"{template.name} (catch-all)",
                    "description": "Auto-created catch-all row by check_aifw_config --fix",
                    "default_model": template.default_model,
                    "fallback_model": template.fallback_model,
                    "max_tokens": template.max_tokens,
                    "temperature": template.temperature,
                    "is_active": True,
                    "prompt_template_key": None,
                },
            )
        return True

    def _check_tier_mappings(self, *, fix: bool) -> list[str]:
        """Verify TierQualityMapping has rows for expected tiers."""
        from aifw.models import TierQualityMapping
        from aifw.constants import QualityLevel

        problems: list[str] = []

        DEFAULT_QUALITY = {
            "premium": QualityLevel.PREMIUM,
            "pro": QualityLevel.BALANCED,
            "freemium": QualityLevel.ECONOMY,
        }

        existing = set(
            TierQualityMapping.objects
            .filter(is_active=True)
            .values_list("tier", flat=True)
        )

        for tier in EXPECTED_TIERS:
            if tier not in existing:
                if fix:
                    TierQualityMapping.objects.get_or_create(
                        tier=tier,
                        defaults={
                            "quality_level": DEFAULT_QUALITY[tier],
                            "is_active": True,
                        },
                    )
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠ Created TierQualityMapping: {tier} → {DEFAULT_QUALITY[tier]}"
                        )
                    )
                else:
                    problems.append(
                        f"TierQualityMapping missing for tier={tier!r}. "
                        f"get_quality_level_for_tier({tier!r}) will return BALANCED (5) fallback."
                    )

        if not problems:
            self.stdout.write(f"  ✓ TierQualityMapping: all {len(EXPECTED_TIERS)} expected tiers present.")

        return problems

    def _check_priority_values(self) -> list[str]:
        """Check for invalid priority values (DB CHECK constraint may not be enforced on old data)."""
        from aifw.models import AIActionType
        from aifw.constants import VALID_PRIORITIES

        problems: list[str] = []
        invalid = (
            AIActionType.objects
            .filter(is_active=True)
            .exclude(priority__isnull=True)
            .exclude(priority__in=VALID_PRIORITIES)
            .values_list("code", "priority")
        )
        for code, prio in invalid:
            problems.append(
                f"action_code={code!r} has invalid priority={prio!r}. "
                f"Valid: {sorted(VALID_PRIORITIES)} or NULL."
            )
        if not problems:
            self.stdout.write("  ✓ All priority values are valid.")
        return problems

    def _check_quality_level_range(self) -> list[str]:
        """Check for quality_level values outside 1–9."""
        from aifw.models import AIActionType

        problems: list[str] = []
        from django.db.models import Q

        invalid = (
            AIActionType.objects
            .filter(is_active=True)
            .exclude(quality_level__isnull=True)
            .filter(Q(quality_level__lt=1) | Q(quality_level__gt=9))
            .values_list("code", "quality_level")
        )
        for code, ql in invalid:
            problems.append(
                f"action_code={code!r} has quality_level={ql} outside valid range 1–9."
            )
        if not problems:
            self.stdout.write("  ✓ All quality_level values are in range 1–9.")
        return problems
