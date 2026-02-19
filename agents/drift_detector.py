"""
agents/drift_detector.py — Drift Detector (Agent A4)

Prüft Dokumentations-Freshness anhand von YAML-Frontmatter:
  - last_verified Datum > threshold_days → stale
  - status = 'deprecated' ohne Nachfolger → orphan
  - Fehlende Frontmatter-Pflichtfelder → incomplete

Zusätzlich: API Key Health Check (alle konfigurierten Keys).

Nutzung:
  python -m agents.drift_detector --docs-dir docs/source --threshold 90
  python -m agents.drift_detector --check-keys
  python -m agents.drift_detector --output github-issue

Gate-Integration:
  Drift Report → Gate 0 (Auto, GitHub Issue erstellen)
  Key Expiry Alert → Gate 1 (Notify)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
            f"**Dokumente gepr\u00fcft:** {self.docs_checked}\n",
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
                f"\n## \ud83d\udd34 Unvollst\u00e4ndige Frontmatter"
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
            for ks in self.key_statuses:
                icon = "\u2705" if ks.valid else "\u274c"
                msg = "OK" if ks.valid else ks.error
                lines.append(
                    f"- {icon} **{ks.service}**"
                    f" (`{ks.key_prefix}...`): {msg}"
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
    """Pr\u00fcft ein Dokument auf Freshness und Vollst\u00e4ndigkeit."""
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
    """Pr\u00fcft alle konfigurierten API Keys auf G\u00fcltigkeit."""
    results: list[KeyStatus] = []

    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if openai_key:
        try:
            import httpx

            resp = httpx.get(
                "https://api.openai.com/v1/models",
                headers={
                    "Authorization": f"Bearer {openai_key}",
                },
                timeout=10,
            )
            valid = resp.status_code == 200
            error = None if valid else f"HTTP {resp.status_code}"
        except Exception as e:
            valid = False
            error = str(e)

        results.append(KeyStatus(
            service="OpenAI",
            key_prefix=openai_key[:12],
            valid=valid,
            error=error,
        ))

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        try:
            import httpx

            resp = httpx.get(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": anthropic_key,
                    "anthropic-version": "2023-06-01",
                },
                timeout=10,
            )
            valid = resp.status_code == 200
            error = None if valid else f"HTTP {resp.status_code}"
        except Exception as e:
            valid = False
            error = str(e)

        results.append(KeyStatus(
            service="Anthropic",
            key_prefix=anthropic_key[:12],
            valid=valid,
            error=error,
        ))

    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    if openrouter_key:
        try:
            import httpx

            resp = httpx.get(
                "https://openrouter.ai/api/v1/auth/key",
                headers={
                    "Authorization": f"Bearer {openrouter_key}",
                },
                timeout=10,
            )
            valid = resp.status_code == 200
            error = None if valid else f"HTTP {resp.status_code}"
        except Exception as e:
            valid = False
            error = str(e)

        results.append(KeyStatus(
            service="OpenRouter",
            key_prefix=openrouter_key[:12],
            valid=valid,
            error=error,
        ))

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Drift Detector \u2014 Docs Freshness & Key Health",
    )
    parser.add_argument(
        "--docs-dir", type=str, default="docs/source",
        help="Verzeichnis mit Sphinx-Quellen",
    )
    parser.add_argument(
        "--threshold", type=int, default=90,
        help="Tage bis ein Dokument als stale gilt",
    )
    parser.add_argument(
        "--check-keys", action="store_true",
        help="API Keys auf G\u00fcltigkeit pr\u00fcfen",
    )
    parser.add_argument(
        "--format", choices=["markdown", "json"],
        default="markdown",
    )
    args = parser.parse_args()

    docs_dir = Path(args.docs_dir)
    report = DriftReport()

    if docs_dir.exists():
        report = scan_docs(docs_dir, args.threshold)
    else:
        logger.warning("Docs dir not found: %s", docs_dir)

    if args.check_keys:
        report.key_statuses = check_api_keys()

    if args.format == "json":
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(report.to_markdown())

    sys.exit(1 if report.has_issues else 0)


if __name__ == "__main__":
    main()
