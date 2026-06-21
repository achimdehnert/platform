#!/usr/bin/env python3
"""adr_index_check.py — Konsistenz-Check INDEX.md ↔ ADR-Dateibestand.

docs/adr/INDEX.md ist handgepflegt und driftet (stale "Next free ADR number",
fehlende Zeilen fuer neue ADRs, Geister-Eintraege, Status-Drift). Dieser Check
vergleicht die INDEX-Tabelle (| # | Title | Status | Impl | Link |) deterministisch
gegen den Dateibestand in docs/adr/ (aktiv) + archive/ + _archive/ (archiviert).

Finding-Kategorien:
  missing_row     aktive ADR-Datei ohne INDEX-Eintrag
  ghost_row       INDEX-Eintrag, fuer den weder aktive noch archivierte Datei existiert
  status_drift    INDEX-Status ≠ Frontmatter `status:` (case-insensitive;
                  INDEX `Archived` matcht Dateien unter _archive/)
  broken_link     INDEX-Link-Ziel existiert nicht im Filesystem
  stale_next_free Kopfzeile "Next free ADR number" ≠ max(aktive Nummer)+1

SUGGEST-Modus (Default, repo-health-rule-discipline): Exit-Code IMMER 0.
`--gate` fuer spaetere Promotion (Exit 1 bei Findings) nach Bereinigung der Alt-Funde.

Usage:
    python3 tools/adr_index_check.py [--adr-dir docs/adr] [--format human|github] [--gate]
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from dataclasses import dataclass

ADR_FILE_RE = re.compile(r"^ADR-(\d{3})\b")
NEXT_FREE_RE = re.compile(r"Next free ADR number:\*{0,2}\s*(\d+)")
ROW_RE = re.compile(r"^\|\s*(\d{3})\s*\|")
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
FRONTMATTER_STATUS_RE = re.compile(r"^status:\s*(.+?)\s*$", re.MULTILINE)


@dataclass
class Finding:
    path: str
    line: int
    category: str
    message: str


@dataclass
class IndexRow:
    line: int
    number: str
    title: str
    status: str  # normalisiert (lowercase, ohne Backticks)
    link_target: str  # leer wenn kein Link geparst


def build_maps(
    adr_dir: pathlib.Path,
) -> tuple[dict[str, pathlib.Path], dict[str, list[pathlib.Path]]]:
    """Nummer→Datei-Maps: aktiv (flach) und archiviert (archive/ + _archive/, rekursiv)."""
    active: dict[str, pathlib.Path] = {}
    for f in sorted(adr_dir.glob("ADR-*.md")):
        m = ADR_FILE_RE.match(f.name)
        if m:
            active[m.group(1)] = f
    archived: dict[str, list[pathlib.Path]] = {}
    for sub in ("archive", "_archive"):
        d = adr_dir / sub
        if not d.is_dir():
            continue
        for f in sorted(d.rglob("ADR-*.md")):
            m = ADR_FILE_RE.match(f.name)
            if m:
                archived.setdefault(m.group(1), []).append(f)
    return active, archived


def _norm_status(raw: str) -> str:
    """Normalisiert Status: Backticks/Quotes weg, lowercase, erstes Wort."""
    s = raw.strip().strip("`'\"").strip()
    return s.split()[0].lower() if s else ""


def frontmatter_status(path: pathlib.Path) -> str:
    """Liest `status:` aus dem YAML-Frontmatter; leer wenn nicht vorhanden."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    if end == -1:
        return ""
    m = FRONTMATTER_STATUS_RE.search(text[3:end])
    return _norm_status(m.group(1)) if m else ""


def parse_index(index_path: pathlib.Path) -> tuple[list[IndexRow], int | None, int]:
    """Parst INDEX.md → (Tabellenzeilen mit 3-stelliger Nummer, next-free-Wert, dessen Zeile)."""
    rows: list[IndexRow] = []
    next_free: int | None = None
    next_free_line = 0
    for i, line in enumerate(index_path.read_text(encoding="utf-8").splitlines(), start=1):
        nf = NEXT_FREE_RE.search(line)
        if nf and next_free is None:
            next_free = int(nf.group(1))
            next_free_line = i
        m = ROW_RE.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        link_m = LINK_RE.search(cells[4])
        rows.append(
            IndexRow(
                line=i,
                number=m.group(1),
                title=cells[1],
                status=_norm_status(cells[2]),
                link_target=link_m.group(2) if link_m else "",
            )
        )
    return rows, next_free, next_free_line


def _rel(path: pathlib.Path, root: pathlib.Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def run(adr_dir: pathlib.Path, repo_root: pathlib.Path) -> list[Finding]:
    findings: list[Finding] = []
    index_path = adr_dir / "INDEX.md"
    index_rel = _rel(index_path, repo_root)
    if not index_path.is_file():
        findings.append(Finding(index_rel, 1, "ghost_row", "INDEX.md fehlt"))
        return findings

    active, archived = build_maps(adr_dir)
    rows, next_free, next_free_line = parse_index(index_path)
    indexed = {r.number for r in rows}

    # missing_row: aktive Datei ohne INDEX-Eintrag
    for num in sorted(active):
        if num not in indexed:
            findings.append(
                Finding(
                    index_rel,
                    1,
                    "missing_row",
                    f"ADR-{num} ({active[num].name}) hat keinen INDEX-Eintrag",
                )
            )

    for row in rows:
        num = row.number
        # ghost_row: Eintrag ohne Datei (weder aktiv noch archiviert)
        if num not in active and num not in archived:
            findings.append(
                Finding(
                    index_rel,
                    row.line,
                    "ghost_row",
                    f"INDEX-Eintrag ADR-{num} ohne Datei (weder aktiv noch archiviert)",
                )
            )
            continue

        # broken_link: Link-Ziel existiert nicht
        if row.link_target:
            target = (adr_dir / row.link_target.split("#", 1)[0]).resolve()
            if not target.is_file():
                findings.append(
                    Finding(
                        index_rel,
                        row.line,
                        "broken_link",
                        f"ADR-{num}: Link-Ziel {row.link_target} existiert nicht",
                    )
                )

        # status_drift
        if row.status == "archived":
            # INDEX `Archived` matcht Dateien unter _archive/ — egal welcher Frontmatter-Status
            under_underscore_archive = any(
                "_archive" in p.parts for p in archived.get(num, [])
            )
            if num in active:
                findings.append(
                    Finding(
                        index_rel,
                        row.line,
                        "status_drift",
                        f"ADR-{num}: INDEX sagt Archived, aber aktive Datei existiert "
                        f"({active[num].name})",
                    )
                )
            elif not under_underscore_archive:
                findings.append(
                    Finding(
                        index_rel,
                        row.line,
                        "status_drift",
                        f"ADR-{num}: INDEX sagt Archived, aber keine Datei unter _archive/",
                    )
                )
            continue
        # Vergleich gegen Frontmatter der massgeblichen Datei (aktiv bevorzugt)
        path = active.get(num) or archived.get(num, [None])[0]
        if path is None:
            continue
        fm = frontmatter_status(path)
        if fm and row.status and fm != row.status:
            findings.append(
                Finding(
                    index_rel,
                    row.line,
                    "status_drift",
                    f"ADR-{num}: INDEX-Status '{row.status}' ≠ Frontmatter-Status '{fm}' "
                    f"({_rel(path, repo_root)})",
                )
            )

    # stale_next_free
    if active:
        expected = max(int(n) for n in active) + 1
        if next_free is None:
            findings.append(
                Finding(
                    index_rel,
                    1,
                    "stale_next_free",
                    f"Kopfzeile 'Next free ADR number' fehlt (Soll: {expected})",
                )
            )
        elif next_free != expected:
            findings.append(
                Finding(
                    index_rel,
                    next_free_line,
                    "stale_next_free",
                    f"'Next free ADR number: {next_free}' ist stale — "
                    f"Soll: {expected} (max aktive Nummer + 1)",
                )
            )

    return findings


def emit(findings: list[Finding], fmt: str) -> None:
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.category] = counts.get(f.category, 0) + 1
        if fmt == "github":
            print(
                f"::warning file={f.path},line={f.line},"
                f"title=adr-index-check {f.category}::{f.message}"
            )
        else:
            print(f"{f.path}:{f.line}: [{f.category}] {f.message}")
    summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "0 Findings"
    if fmt == "github":
        print(f"::warning title=adr-index-check summary::{len(findings)} Finding(s): {summary}")
    print(f"adr-index-check: {len(findings)} Finding(s) ({summary})")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--adr-dir", default="docs/adr", help="ADR-Verzeichnis (Default docs/adr)")
    ap.add_argument("--format", choices=["human", "github"], default="human")
    ap.add_argument(
        "--gate",
        action="store_true",
        help="Exit 1 bei Findings (Promotion-Pfad; Default ist SUGGEST = Exit 0)",
    )
    args = ap.parse_args(argv)

    adr_dir = pathlib.Path(args.adr_dir)
    if not adr_dir.is_dir():
        print(f"adr-index-check: Verzeichnis {adr_dir} nicht gefunden — nichts zu pruefen.")
        return 0
    repo_root = adr_dir.resolve().parent.parent
    findings = run(adr_dir.resolve(), repo_root)
    emit(findings, args.format)
    if args.gate and findings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
