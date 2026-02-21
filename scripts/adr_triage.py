#!/usr/bin/env python3
"""
ADR Triage Script — analysiert alle ADR-Dateien und schlägt Status-Korrekturen vor.

Ausführen: python scripts/adr_triage.py [--apply]

Ohne --apply: nur Report ausgeben (read-only)
Mit --apply:  YAML-Frontmatter in ADRs ohne Frontmatter einfügen (schreibt Dateien)
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

ADR_DIR = Path(__file__).parent.parent / "docs" / "adr"

# Bekannte Superseded-Beziehungen (manuell gepflegt)
KNOWN_SUPERSEDED: dict[str, str] = {
    "ADR-017": "ADR-032",   # DDL Duplikat — ADR-032 ist aktueller
    "ADR-020": "ADR-046",   # Sphinx-Doku → techdocs (ADR-046 Accepted)
    "ADR-047": "ADR-046",   # Sphinx Hub → techdocs (ADR-046 Accepted)
    "ADR-033": "ADR-056",   # Dual-Framework (Odoo) → obsolet durch SaaS-Fokus
}

# ADRs die definitiv Accepted sind (aus INDEX.md manuell extrahiert)
KNOWN_ACCEPTED: set[str] = {
    "ADR-007", "ADR-021", "ADR-035", "ADR-046", "ADR-055",
}

# ADRs die definitiv Proposed sind
KNOWN_PROPOSED: set[str] = {
    "ADR-054", "ADR-056", "ADR-057", "ADR-058", "ADR-059",
}


def extract_adr_id(filename: str) -> str | None:
    m = re.match(r"(ADR-\d+)", filename, re.IGNORECASE)
    return m.group(1).upper() if m else None


def extract_status_from_content(content: str) -> str:
    """Extrahiert Status aus Markdown-Tabelle oder Frontmatter."""
    # YAML-Frontmatter
    fm_match = re.match(r"^---\n(.+?)\n---", content, re.DOTALL)
    if fm_match:
        status_m = re.search(r"^status:\s*(.+)$", fm_match.group(1), re.MULTILINE)
        if status_m:
            return status_m.group(1).strip().lower()

    # Markdown-Tabelle: **Status** | Accepted
    table_m = re.search(
        r"\*\*Status\*\*\s*\|?\s*([A-Za-z?]+)",
        content,
        re.IGNORECASE,
    )
    if table_m:
        return table_m.group(1).strip().lower()

    # Inline: **Status:** Proposed
    inline_m = re.search(r"\*\*Status\*\*:\s*([A-Za-z?]+)", content, re.IGNORECASE)
    if inline_m:
        return inline_m.group(1).strip().lower()

    return "?"


def analyze_adr(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    adr_id = extract_adr_id(path.name)
    issues: list[str] = []
    suggested_status: str | None = None
    superseded_by: str | None = None

    # 1. YAML-Frontmatter?
    has_frontmatter = content.startswith("---\n")
    if not has_frontmatter:
        issues.append("NO_FRONTMATTER")

    # 2. Status extrahieren
    raw_status = extract_status_from_content(content)

    # 3. Bekannte Superseded-Beziehungen
    if adr_id and adr_id in KNOWN_SUPERSEDED:
        superseded_by = KNOWN_SUPERSEDED[adr_id]
        suggested_status = "superseded"
        issues.append(f"SUPERSEDED_BY_{superseded_by}")

    # 4. Bekannte Status
    if not suggested_status and adr_id:
        if adr_id in KNOWN_ACCEPTED:
            suggested_status = "accepted"
        elif adr_id in KNOWN_PROPOSED:
            suggested_status = "proposed"

    # 5. Status aus Inhalt ableiten
    if not suggested_status:
        status_lower = raw_status.lower()
        if "accepted" in status_lower:
            suggested_status = "accepted"
        elif "proposed" in status_lower:
            suggested_status = "proposed"
        elif "draft" in status_lower:
            suggested_status = "draft"
        elif "deprecated" in status_lower:
            suggested_status = "deprecated"
        elif "superseded" in status_lower:
            suggested_status = "superseded"
        elif "rejected" in status_lower:
            suggested_status = "rejected"
        else:
            suggested_status = "proposed"  # sicherer Default für unbekannte

    # 6. Confirmation-Abschnitt?
    if (
        "## Confirmation" not in content
        and "### Confirmation" not in content
        and "## 8. Confirmation" not in content
        and "## 9. Confirmation" not in content
    ):
        issues.append("NO_CONFIRMATION")

    # 7. Decision Drivers?
    if "## Decision Drivers" not in content and "Decision Driver" not in content:
        issues.append("NO_DECISION_DRIVERS")

    # 8. Repo-Zugehörigkeit (nur für neue ADRs nach Template v2)
    if has_frontmatter and "## Repo-Zugehörigkeit" not in content:
        issues.append("NO_REPO_AFFILIATION")

    return {
        "file": path.name,
        "adr_id": adr_id,
        "raw_status": raw_status,
        "suggested_status": suggested_status,
        "superseded_by": superseded_by,
        "has_frontmatter": has_frontmatter,
        "issues": issues,
    }


def generate_frontmatter(adr: dict, content: str) -> str:
    """Generiert minimales YAML-Frontmatter für ADRs ohne Frontmatter."""
    # Datum aus Inhalt extrahieren
    date_m = re.search(r"\*\*Datum\*\*[:\|]\s*(\d{4}-\d{2}-\d{2})", content)
    adr_date = date_m.group(1) if date_m else str(date.today())

    frontmatter = (
        f"---\n"
        f"status: {adr['suggested_status']}\n"
        f"date: {adr_date}\n"
        f"decision-makers: Achim Dehnert\n"
        f"---\n\n"
    )
    return frontmatter + content


def print_report(results: list[dict]) -> None:
    total = len(results)
    with_issues = [r for r in results if r["issues"]]
    no_frontmatter = [r for r in results if not r["has_frontmatter"]]
    unknown_status = [r for r in results if r["raw_status"] == "?"]
    superseded = [r for r in results if r["suggested_status"] == "superseded"]

    print(f"\n{'='*70}")
    print(f"ADR TRIAGE REPORT — {date.today()}")
    print(f"{'='*70}")
    print(f"  Total ADRs       : {total}")
    print(f"  With issues      : {len(with_issues)}")
    print(f"  No frontmatter   : {len(no_frontmatter)}")
    print(f"  Unknown status ? : {len(unknown_status)}")
    print(f"  → Superseded     : {len(superseded)}")
    print()

    if superseded:
        print("── SUPERSEDED (sofort updaten) ──────────────────────────────────")
        for r in superseded:
            print(f"  {r['adr_id']:10} → superseded by {r['superseded_by']}")
        print()

    print("── ALLE ADRs MIT ISSUES ─────────────────────────────────────────")
    for r in with_issues:
        status_arrow = f"{r['raw_status']:12} → {r['suggested_status']}"
        print(f"  {r['adr_id'] or '?':10}  {status_arrow:30}  {', '.join(r['issues'])}")

    print()
    print("── STATUS-VORSCHLÄGE (für INDEX.md) ─────────────────────────────")
    status_counts: dict[str, int] = {}
    for r in results:
        s = r["suggested_status"]
        status_counts[s] = status_counts.get(s, 0) + 1
    for status, count in sorted(status_counts.items()):
        print(f"  {status:15}: {count}")

    print()
    print("Ausführen mit --apply um YAML-Frontmatter automatisch einzufügen.")
    print(f"{'='*70}\n")


def apply_frontmatter(results: list[dict]) -> None:
    """Fügt YAML-Frontmatter in ADRs ohne Frontmatter ein."""
    applied = 0
    for r in results:
        if r["has_frontmatter"]:
            continue
        path = ADR_DIR / r["file"]
        content = path.read_text(encoding="utf-8")
        new_content = generate_frontmatter(r, content)
        path.write_text(new_content, encoding="utf-8")
        print(f"  ✅ Frontmatter hinzugefügt: {r['file']} (status: {r['suggested_status']})")
        applied += 1
    print(f"\n{applied} Dateien aktualisiert.")


def main() -> None:
    parser = argparse.ArgumentParser(description="ADR Triage — Staleness & Status Check")
    parser.add_argument("--apply", action="store_true", help="YAML-Frontmatter einfügen")
    parser.add_argument("--only-issues", action="store_true", help="Nur ADRs mit Issues anzeigen")
    args = parser.parse_args()

    adr_files = sorted(
        p for p in ADR_DIR.glob("*.md")
        if not p.name.upper().startswith("INDEX")
    )

    if not adr_files:
        print(f"Keine ADR-Dateien in {ADR_DIR} gefunden.")
        sys.exit(1)

    results = [analyze_adr(p) for p in adr_files]

    print_report(results)

    if args.apply:
        print("── APPLYING FRONTMATTER ─────────────────────────────────────────")
        apply_frontmatter(results)


if __name__ == "__main__":
    main()
