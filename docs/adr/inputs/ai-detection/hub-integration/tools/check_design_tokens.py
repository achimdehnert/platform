"""
check_design_tokens.py — Extended for ADR-051 Hub Visual Identity System

Extends the original ADR-049 token compliance checker with:
  1. DNA fingerprint score per hub (from audit-report.json)
  2. Check that each hub uses its own pui-tokens-{hub}.css (not the generic one)
  3. Warn on banned fonts in templates

Usage (CI):
    python -m tools.check_design_tokens --ci --strict
    python -m tools.check_design_tokens --hub bieterpilot
    python -m tools.check_design_tokens --report reports/audit-report.json

Exit codes:
    0 — All checks passed
    1 — BLOCKER or KRITISCH findings (CI blocks)
    2 — Only WARNING/INFO findings (CI logs, does not block unless --strict)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Severity
# ---------------------------------------------------------------------------

class Severity:
    BLOCKER  = "BLOCKER"   # Must fix — CI exit 1
    KRITISCH = "KRITISCH"  # Must fix — CI exit 1
    HOCH     = "HOCH"      # Should fix — CI exit 2 in strict mode
    MEDIUM   = "MEDIUM"    # Should fix — warning only
    INFO     = "INFO"      # Informational

    @classmethod
    def blocks_ci(cls, sev: str) -> bool:
        return sev in (cls.BLOCKER, cls.KRITISCH)


@dataclass
class CheckResult:
    severity: str
    rule: str
    file: str
    message: str
    line: int = 0
    fix: str = ""


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

# ADR-049: Original token compliance checks
DIRECT_COLOR_PATTERN = re.compile(
    r"\b(?:bg|text|border|ring|fill|stroke)"
    r"-(?:blue|red|green|gray|grey|amber|sky|purple|violet|indigo|pink|rose|slate|zinc|stone|neutral|orange|yellow|lime|emerald|teal|cyan)"
    r"-\d{2,3}\b"
)
HARDCODED_HEX_PATTERN = re.compile(
    r"(?:color|background|border-color|fill|stroke)\s*:\s*#[0-9a-fA-F]{3,8}"
)
INLINE_STYLE_PATTERN = re.compile(r'\bstyle\s*=\s*["\']')
ONCLICK_PATTERN      = re.compile(r'\bonclick\s*=\s*["\']')
GOOGLE_FONTS_PATTERN = re.compile(r'fonts\.googleapis\.com|fonts\.google\.com')

# ADR-051: Hub identity checks
BANNED_FONTS = {
    "Inter": "TYP-001",
    "system-ui": "TYP-002",
    "Roboto": "TYP-003",
    "Space Grotesk": "TYP-004",
    "Poppins": "TYP-005",
    "Arial": "generic",
}
GENERIC_PUI_PATTERN  = re.compile(r'pui-tokens\.css(?!\?)')  # generic, not hub-specific
HUB_TOKEN_PATTERN    = re.compile(r'pui-tokens-([a-z][a-z0-9-]+)\.css')


def check_html_file(path: Path) -> list[CheckResult]:
    """Run all checks on a single HTML/Django template file."""
    results: list[CheckResult] = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return results

    lines = content.splitlines()

    for i, line in enumerate(lines, start=1):

        # ADR-049: Inline styles banned (AP-004)
        if INLINE_STYLE_PATTERN.search(line):
            results.append(CheckResult(
                severity=Severity.KRITISCH,
                rule="AP-004",
                file=str(path),
                line=i,
                message="Inline style attribute found",
                fix='Remove style="..." — use Tailwind utilities or pui-* CSS classes',
            ))

        # ADR-049: onclick banned (AP-003)
        if ONCLICK_PATTERN.search(line):
            results.append(CheckResult(
                severity=Severity.KRITISCH,
                rule="AP-003",
                file=str(path),
                line=i,
                message="onclick attribute found",
                fix="Replace with hx-* (HTMX) or @click (Alpine.js)",
            ))

        # ADR-049: Direct Tailwind color classes
        match = DIRECT_COLOR_PATTERN.search(line)
        if match:
            results.append(CheckResult(
                severity=Severity.HOCH,
                rule="TOKEN-001",
                file=str(path),
                line=i,
                message=f"Direct color class '{match.group()}' — use semantic class",
                fix=f"Replace with bg-primary, text-foreground, etc. (ADR-049)",
            ))

        # ADR-049: Hardcoded hex in style attributes
        match = HARDCODED_HEX_PATTERN.search(line)
        if match:
            results.append(CheckResult(
                severity=Severity.HOCH,
                rule="TOKEN-002",
                file=str(path),
                line=i,
                message=f"Hardcoded hex color: '{match.group()}'",
                fix="Use --pui-* CSS variable instead",
            ))

        # ADR-051: Google Fonts (DSGVO violation)
        if GOOGLE_FONTS_PATTERN.search(line):
            results.append(CheckResult(
                severity=Severity.BLOCKER,
                rule="DSGVO-001",
                file=str(path),
                line=i,
                message="Google Fonts detected — DSGVO violation",
                fix="Replace with fonts.bunny.net URL (already in pui-tokens-{hub}.css)",
            ))

        # ADR-051: Banned fonts in templates
        for font, rule_id in BANNED_FONTS.items():
            if font.lower() in line.lower() and "font" in line.lower():
                results.append(CheckResult(
                    severity=Severity.HOCH,
                    rule=f"TYP-{rule_id}",
                    file=str(path),
                    line=i,
                    message=f"Banned font '{font}' referenced in template",
                    fix=f"Use --pui-font-display / --pui-font-body from pui-tokens-{{hub}}.css",
                ))

        # ADR-051: Generic pui-tokens.css (not hub-specific)
        if GENERIC_PUI_PATTERN.search(line) and not HUB_TOKEN_PATTERN.search(line):
            results.append(CheckResult(
                severity=Severity.MEDIUM,
                rule="DNA-001",
                file=str(path),
                line=i,
                message="Generic pui-tokens.css loaded — use hub-specific file",
                fix='Replace with: pui-tokens-{{ APP_NAME }}.css',
            ))

    return results


def check_css_file(path: Path) -> list[CheckResult]:
    """Run token compliance checks on CSS files."""
    results: list[CheckResult] = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return results

    # Check if this is a generated pui-tokens file — skip (it IS the source of truth)
    if "DO NOT EDIT" in content and "@pui-meta:" in content:
        return results

    lines = content.splitlines()
    for i, line in enumerate(lines, start=1):
        match = HARDCODED_HEX_PATTERN.search(line)
        if match:
            results.append(CheckResult(
                severity=Severity.HOCH,
                rule="TOKEN-002",
                file=str(path),
                line=i,
                message=f"Hardcoded hex in custom CSS: '{match.group()}'",
                fix="Use var(--pui-*) CSS variable instead",
            ))

    return results


def check_fingerprint_scores(
    audit_report: Path,
    score_threshold: float = 40.0,
) -> list[CheckResult]:
    """Check DNA fingerprint scores from audit-report.json."""
    results: list[CheckResult] = []

    if not audit_report.exists():
        results.append(CheckResult(
            severity=Severity.INFO,
            rule="DNA-AUDIT",
            file=str(audit_report),
            message="No audit report found — run: make audit",
            fix="python -m tools.design_dna audit",
        ))
        return results

    with open(audit_report) as f:
        data = json.load(f)

    for report in data.get("reports", []):
        hub = report.get("hub", "unknown")
        score = report.get("score", 0)
        grade = report.get("grade", "?")

        if score >= 60:
            sev = Severity.BLOCKER
        elif score >= 40:
            sev = Severity.KRITISCH
        elif score >= 30:
            sev = Severity.HOCH
        elif score >= 20:
            sev = Severity.MEDIUM
        else:
            sev = Severity.INFO

        results.append(CheckResult(
            severity=sev,
            rule="DNA-SCORE",
            file=f"hub_dnas/{hub}.yaml",
            message=f"Hub '{hub}': AI fingerprint score {score:.1f}/100 (Grade {grade})",
            fix=(
                f"Run: python -m tools.design_dna mutate --hub {hub}"
                if score >= score_threshold else "OK"
            ),
        ))

    return results


# ---------------------------------------------------------------------------
# Reporter
# ---------------------------------------------------------------------------

def print_report(
    results: list[CheckResult],
    ci_mode: bool = False,
    strict: bool = False,
) -> int:
    """Print results table. Returns exit code."""
    if not results:
        print("✅ No issues found")
        return 0

    # Sort by severity
    order = {
        Severity.BLOCKER: 0, Severity.KRITISCH: 1,
        Severity.HOCH: 2, Severity.MEDIUM: 3, Severity.INFO: 4,
    }
    results.sort(key=lambda r: (order.get(r.severity, 99), r.file, r.line))

    # Count by severity
    counts: dict[str, int] = {}
    for r in results:
        counts[r.severity] = counts.get(r.severity, 0) + 1

    # Print table
    print(f"\n{'Rule':<14} {'Sev':<10} {'File':<50} {'Line':>5}  Message")
    print("─" * 110)
    for r in results:
        if r.severity == Severity.INFO and not ci_mode:
            continue  # Skip INFO in non-CI mode
        file_short = r.file[-48:] if len(r.file) > 48 else r.file
        print(f"  {r.rule:<12} {r.severity:<10} {file_short:<50} {r.line:>5}  {r.message}")
        if r.fix and r.fix != "OK":
            print(f"  {'':12} {'Fix:':10} {r.fix}")

    print()
    for sev in [Severity.BLOCKER, Severity.KRITISCH, Severity.HOCH, Severity.MEDIUM, Severity.INFO]:
        if sev in counts:
            print(f"  {sev}: {counts[sev]}")

    has_blockers = any(Severity.blocks_ci(r.severity) for r in results)
    has_high     = any(r.severity == Severity.HOCH for r in results)

    if has_blockers:
        print("\n❌ FAILED — BLOCKER/KRITISCH findings must be resolved")
        return 1
    elif has_high and strict:
        print("\n⚠️  FAILED (strict mode) — HOCH findings must be resolved")
        return 2
    else:
        print("\n✅ PASSED")
        return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Design Token + Hub Identity Compliance Checker (ADR-049/051)"
    )
    parser.add_argument("--hub",    help="Check a specific hub only")
    parser.add_argument("--ci",     action="store_true", help="CI mode: emit JSON + exit codes")
    parser.add_argument("--strict", action="store_true", help="HOCH findings also fail CI")
    parser.add_argument("--report", default="reports/audit-report.json",
                        help="Path to audit-report.json (default: reports/audit-report.json)")
    parser.add_argument("--templates-dir", default="templates",
                        help="Templates directory to scan (default: templates)")
    parser.add_argument("--css-dir", default="static",
                        help="Static CSS directory to scan (default: static)")
    args = parser.parse_args()

    repo_root = Path.cwd()
    all_results: list[CheckResult] = []

    # 1. Scan templates
    templates_dir = repo_root / args.templates_dir
    if templates_dir.exists():
        for html_path in templates_dir.rglob("*.html"):
            all_results.extend(check_html_file(html_path))

    # 2. Scan custom CSS (not generated pui-tokens files)
    css_dir = repo_root / args.css_dir
    if css_dir.exists():
        for css_path in css_dir.rglob("*.css"):
            all_results.extend(check_css_file(css_path))

    # 3. Check fingerprint scores from audit report
    all_results.extend(check_fingerprint_scores(
        Path(args.report),
        score_threshold=40.0,
    ))

    # 4. Filter by hub if specified
    if args.hub:
        all_results = [r for r in all_results if args.hub in r.file]

    # 5. Report
    exit_code = print_report(all_results, ci_mode=args.ci, strict=args.strict)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
