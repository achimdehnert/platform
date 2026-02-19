"""Drift Detector (Agent A4) — Docs-Freshness & API Key Health.

Prüft die Aktualität aller Architektur-Dokumente (ADRs, Prinzipien)
und validiert API-Key-Gesundheit für externe Services.

Gate: 1 (NOTIFY) — erstellt GitHub Issues, blockiert nie.
Model: GPT-4o-mini
Trigger: Cron (wöchentlich) oder manuell
Output: Markdown-Report oder JSON

Usage:
    python -m agents.drift_detector --docs-dir docs/
    python -m agents.drift_detector --check-keys
    python -m agents.drift_detector --format json

Siehe ADR-054 für Details zum Agent-Ökosystem.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("drift_detector")

REQUIRED_FIELDS = {"id", "title", "status"}
RECOMMENDED_FIELDS = {"owner", "last_verified", "tags"}


@dataclass
class DocStatus:
    """Status eines einzelnen Dokuments."""

    path: str
    frontmatter: dict[str, Any]
    issues: list[str] = field(default_factory=list)

    @property
    def is_stale(self) -> bool:
        return any("stale" in i.lower() for i in self.issues)

    @property
    def is_incomplete(self) -> bool:
        return any("missing" in i.lower() for i in self.issues)


@dataclass
class KeyStatus:
    """Status eines API Keys."""

    service: str
    key_prefix: str
    valid: bool
    error: str | None = None


@dataclass
class DriftReport:
    """Gesamtbericht."""

    docs_checked: int = 0
    stale_docs: list[DocStatus] = field(default_factory=list)
    incomplete_docs: list[DocStatus] = field(default_factory=list)
    deprecated_docs: list[DocStatus] = field(default_factory=list)
    key_statuses: list[KeyStatus] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        return bool(
            self.stale_docs
            or self.incomplete_docs
            or self.deprecated_docs
            or any(not k.valid for k in self.key_statuses)
        )

    def to_markdown(self) -> str:
        lines = [
            "# \ud83d\udcca Drift Detection Report",
            f"\n**Datum:** {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')}",
            f"**Dokumente geprüft:** {self.docs_checked}\n",
        ]

        if not self.has_issues:
            lines.append("\u2705 **Keine Drift-Probleme gefunden.**\n")
            return "\n".join(lines)

        if self.stale_docs:
            lines.append(
                f"## \ud83d\udfe1 Veraltete Dokumente ({len(self.stale_docs)})\n"
            )
            lines.append("| Dokument | Letztes Verify | Owner | Problem |")
            lines.append("|----------|---------------|-------|---------|")
            for doc in self.stale_docs:
                fm = doc.frontmatter
                last = fm.get("last_verified", "nie")
                owner = fm.get("owner", "unbekannt")
                issue = "; ".join(doc.issues)
                lines.append(
                    f"| `{doc.path}` | {last} | {owner} | {issue} |"
                )

        if self.incomplete_docs:
            lines.append(
                f"\n## \ud83d\udd34 Unvollständige Frontmatter"
                f" ({len(self.incomplete_docs)})\n"
            )
            for doc in self.incomplete_docs:
                lines.append(
                    f"- `{doc.path}`: {', '.join(doc.issues)}"
                )

        if self.deprecated_docs:
            lines.append(
                f"\n## \u26aa Deprecated"
                f" ({len(self.deprecated_docs)})\n"
            )
            for doc in self.deprecated_docs:
                lines.append(
                    f"- `{doc.path}`:"
                    f" {doc.frontmatter.get('title', 'N/A')}"
                )

        if self.key_statuses:
            lines.append("\n## \ud83d\udd11 API Key Health\n")
            lines.append("| Service | Prefix | Status | Error |")
            lines.append("|---------|--------|--------|-------|")
            for k in self.key_statuses:
                status_icon = "\u2705" if k.valid else "\u274c"
                err = k.error or "-"
                lines.append(
                    f"| {k.service} | `{k.key_prefix}` "
                    f"| {status_icon} | {err} |"
                )

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "docs_checked": self.docs_checked,
            "stale_count": len(self.stale_docs),
            "incomplete_count": len(self.incomplete_docs),
            "deprecated_count": len(self.deprecated_docs),
            "keys_checked": len(self.key_statuses),
            "keys_invalid": sum(
                1 for k in self.key_statuses if not k.valid
            ),
            "has_issues": self.has_issues,
            "stale_docs": [
                {"path": d.path, "issues": d.issues}
                for d in self.stale_docs
            ],
            "incomplete_docs": [
                {"path": d.path, "issues": d.issues}
                for d in self.incomplete_docs
            ],
        }


def extract_frontmatter(
    file_path: Path,
) -> dict[str, Any] | None:
    """Extrahiert YAML-Frontmatter aus einer Markdown-Datei."""
    text = file_path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.+?)\n---", text, re.DOTALL)
    if not match:
        return None
    try:
        return yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None


def check_doc_freshness(
    file_path: Path,
    docs_dir: Path,
    threshold_days: int,
) -> DocStatus:
    """Prüft ein Dokument auf Freshness und Vollständigkeit."""
    rel_path = str(file_path.relative_to(docs_dir))
    fm = extract_frontmatter(file_path)

    if fm is None:
        return DocStatus(
            path=rel_path,
            frontmatter={},
            issues=["Missing frontmatter entirely"],
        )

    status = DocStatus(path=rel_path, frontmatter=fm)

    missing = REQUIRED_FIELDS - set(fm.keys())
    if missing:
        status.issues.append(
            f"Missing required fields: {', '.join(sorted(missing))}"
        )

    missing_rec = RECOMMENDED_FIELDS - set(fm.keys())
    if missing_rec:
        status.issues.append(
            f"Missing recommended fields:"
            f" {', '.join(sorted(missing_rec))}"
        )

    last_verified = fm.get("last_verified")
    if last_verified:
        if isinstance(last_verified, str):
            try:
                last_date = datetime.strptime(
                    last_verified, "%Y-%m-%d",
                )
            except ValueError:
                status.issues.append(
                    f"Invalid last_verified format:"
                    f" {last_verified}"
                )
                return status
        elif isinstance(last_verified, datetime):
            last_date = last_verified
        elif isinstance(last_verified, date):
            last_date = datetime(
                last_verified.year,
                last_verified.month,
                last_verified.day,
            )
        else:
            last_date = datetime.now()

        days_old = (datetime.now() - last_date).days
        if days_old > threshold_days:
            status.issues.append(
                f"Stale: last_verified {days_old} days ago"
                f" (threshold: {threshold_days})"
            )

    return status


def scan_docs(
    docs_dir: Path,
    threshold_days: int = 90,
) -> DriftReport:
    """Scannt alle Markdown-Dateien im docs-Verzeichnis."""
    report = DriftReport()

    md_files = sorted(docs_dir.rglob("*.md"))
    report.docs_checked = len(md_files)

    for md_file in md_files:
        if md_file.name.startswith("_"):
            continue

        doc = check_doc_freshness(
            md_file, docs_dir, threshold_days,
        )

        if doc.frontmatter.get("status") == "deprecated":
            report.deprecated_docs.append(doc)
        elif doc.is_stale:
            report.stale_docs.append(doc)
        elif doc.is_incomplete:
            report.incomplete_docs.append(doc)

    logger.info(
        "Scanned %d docs: %d stale, %d incomplete, %d deprecated",
        report.docs_checked,
        len(report.stale_docs),
        len(report.incomplete_docs),
        len(report.deprecated_docs),
    )
    return report


def check_api_keys() -> list[KeyStatus]:
    """Prüft alle konfigurierten API Keys auf Gültigkeit."""
    results: list[KeyStatus] = []

    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if openai_key:
        valid = openai_key.startswith("sk-") and len(openai_key) > 20
        results.append(
            KeyStatus(
                service="OpenAI",
                key_prefix=openai_key[:8] + "...",
                valid=valid,
                error=None if valid else "Invalid format",
            )
        )

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        valid = (
            anthropic_key.startswith("sk-ant-")
            and len(anthropic_key) > 20
        )
        results.append(
            KeyStatus(
                service="Anthropic",
                key_prefix=anthropic_key[:10] + "...",
                valid=valid,
                error=None if valid else "Invalid format",
            )
        )

    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    if openrouter_key:
        valid = (
            openrouter_key.startswith("sk-or-")
            and len(openrouter_key) > 20
        )
        results.append(
            KeyStatus(
                service="OpenRouter",
                key_prefix=openrouter_key[:10] + "...",
                valid=valid,
                error=None if valid else "Invalid format",
            )
        )

    return results


def run_full_scan(
    docs_dir: Path | None = None,
    threshold_days: int = 90,
    check_keys: bool = True,
) -> DriftReport:
    """Führt einen vollständigen Drift-Scan durch."""
    report = DriftReport()

    if docs_dir and docs_dir.exists():
        report = scan_docs(docs_dir, threshold_days)

    if check_keys:
        report.key_statuses = check_api_keys()

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Drift Detector — Docs Freshness & API Key Health",
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path("docs"),
        help="Verzeichnis mit Markdown-Dokumenten (default: docs/)",
    )
    parser.add_argument(
        "--threshold-days",
        type=int,
        default=90,
        help="Tage bis ein Dokument als stale gilt (default: 90)",
    )
    parser.add_argument(
        "--check-keys",
        action="store_true",
        default=True,
        help="API Keys prüfen (default: true)",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Ausgabeformat (default: markdown)",
    )

    args = parser.parse_args()

    report = run_full_scan(
        docs_dir=args.docs_dir,
        threshold_days=args.threshold_days,
        check_keys=args.check_keys,
    )

    if args.format == "json":
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(report.to_markdown())

    if report.has_issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
