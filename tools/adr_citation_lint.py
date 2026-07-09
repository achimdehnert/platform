#!/usr/bin/env python3
"""adr_citation_lint.py — deterministischer Lint fuer ADR-Querverweise (Body-Zitate).

Ergaenzt den bestehenden `iil-adrfw staleness`-Step (der nur depends_on-Frontmatter
prueft) um Body-Zitate und Markdown-Links. Hintergrund: ADR-Full-Scan 2026-06-06
fand ~30 tote/falsch betitelte ADR-Querverweise (Zitat auf Nummer, die archiviert
oder anders belegt ist) — der dominante, CI-fangbare Defekt-Typ.

Finding-Kategorien (deterministisch-strukturell, kein LLM):
  dead_ref        Referenz auf eine ADR-Nummer ohne aktive Datei in docs/adr/
                  (mit Hinweis auf den Archiv-Pfad, falls die Nummer dort liegt)
  stale_filename  Markdown-Link, dessen Ziel-Slug nicht dem realen Dateinamen
                  der aktiven Nummer entspricht (z.B. nach Rename/Renumbering)
  external_target Markdown-Link mit ADR-Bezug, dessen Ziel ausserhalb docs/adr/
                  liegt (z.B. ../../mcp-hub/...)

Whitelist fuer bekannte Alt-Funde:
  - Inline-Marker `<!-- adr-lint: ignore-next-line -->` (unterdrueckt die
    Folgezeile komplett)
  - docs/adr/.adr-lint-ignore — eine Referenz pro Zeile, Format:
        ADR-054 in ADR-101
    (unterdrueckt alle Findings fuer Referenz ADR-054 innerhalb von ADR-101;
    `#`-Kommentare und Leerzeilen erlaubt)

SUGGEST-Modus (Default, repo-health-rule-discipline): Exit-Code IMMER 0.
`--gate` ist fuer die spaetere Promotion vorgesehen (Exit 1 bei Findings),
erst nach Bereinigung der Alt-Funde aktivieren.

Usage:
    python3 tools/adr_citation_lint.py [--adr-dir docs/adr] [--format human|github] [--gate]
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from dataclasses import dataclass

ADR_FILE_RE = re.compile(r"^ADR-(\d{3})\b")
ADR_REF_RE = re.compile(r"ADR-(\d{3})")
# Markdown-Link: [text](target) — target ohne Whitespace, optionaler "title"
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
IGNORE_MARKER = "<!-- adr-lint: ignore-next-line -->"
IGNORE_FILE_LINE_RE = re.compile(r"^(ADR-\d{3})\s+in\s+(ADR-\d{3})\s*$")


@dataclass
class Finding:
    path: str  # repo-relativer Pfad der Quelldatei
    line: int  # 1-basiert
    category: str  # dead_ref | stale_filename | external_target
    message: str


def build_maps(
    adr_dir: pathlib.Path,
) -> tuple[dict[str, pathlib.Path], dict[str, list[pathlib.Path]]]:
    """Nummer→Datei-Maps: aktiv (docs/adr/ flach) und archiviert (archive/ + _archive/)."""
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


def load_ignore_pairs(adr_dir: pathlib.Path) -> set[tuple[str, str]]:
    """Liest .adr-lint-ignore: {(referenzierte Nummer, Quell-Nummer), ...}."""
    pairs: set[tuple[str, str]] = set()
    ignore_file = adr_dir / ".adr-lint-ignore"
    if not ignore_file.is_file():
        return pairs
    for raw in ignore_file.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        m = IGNORE_FILE_LINE_RE.match(line)
        if m:
            pairs.add((m.group(1)[4:], m.group(2)[4:]))  # nur die Nummern
    return pairs


def _rel(path: pathlib.Path, root: pathlib.Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def lint_file(
    src: pathlib.Path,
    adr_dir: pathlib.Path,
    active: dict[str, pathlib.Path],
    archived: dict[str, list[pathlib.Path]],
    ignore_pairs: set[tuple[str, str]],
    repo_root: pathlib.Path,
) -> list[Finding]:
    """Lintet eine aktive ADR-Datei (Body + Frontmatter, zeilenweise)."""
    findings: list[Finding] = []
    src_rel = _rel(src, repo_root)
    own_m = ADR_FILE_RE.match(src.name)
    own_num = own_m.group(1) if own_m else ""
    adr_dir_resolved = adr_dir.resolve()
    seen: set[tuple[int, str, str]] = set()  # (line, category, num/target) dedupe

    def add(line_no: int, category: str, num: str, message: str) -> None:
        if num and (num, own_num) in ignore_pairs:
            return
        key = (line_no, category, num or message)
        if key in seen:
            return
        seen.add(key)
        findings.append(Finding(src_rel, line_no, category, message))

    def check_number(line_no: int, num: str) -> None:
        """dead_ref-Check fuer eine bare Nummern-Referenz."""
        if num == own_num or num in active:
            return
        if num in archived:
            hint = ", ".join(_rel(p, repo_root) for p in archived[num])
            add(line_no, "dead_ref", num, f"ADR-{num} hat keine aktive Datei (archiviert: {hint})")
        else:
            add(line_no, "dead_ref", num, f"ADR-{num} existiert weder aktiv noch archiviert")

    lines = src.read_text(encoding="utf-8", errors="ignore").splitlines()
    skip_next = False
    for i, line in enumerate(lines, start=1):
        if skip_next:
            skip_next = False
            continue
        if IGNORE_MARKER in line:
            skip_next = True
            continue

        rest = line
        for m in MD_LINK_RE.finditer(line):
            text, target = m.group(1), m.group(2)
            rest = rest.replace(m.group(0), " ", 1)
            target_path = target.split("#", 1)[0]
            has_adr = bool(ADR_REF_RE.search(text) or ADR_REF_RE.search(target))
            if "://" in target or target.startswith("mailto:"):
                # URL-Ziele: nur die Nummern im Link-Text pruefen
                for num in ADR_REF_RE.findall(text):
                    check_number(i, num)
                continue
            if not has_adr:
                continue
            # relativer Pfad: gegen das Verzeichnis der Quelldatei aufloesen
            resolved = (src.parent / target_path).resolve() if target_path else src.resolve()
            if not str(resolved).startswith(str(adr_dir_resolved) + "/") and resolved != adr_dir_resolved:
                nums = ADR_REF_RE.findall(target) or ADR_REF_RE.findall(text)
                num = nums[0] if nums else ""
                add(
                    i,
                    "external_target",
                    num,
                    f"Link-Ziel ausserhalb docs/adr/: {target}",
                )
                continue
            fm = ADR_REF_RE.search(pathlib.Path(target_path).name)
            if fm and target_path.endswith(".md"):
                num = fm.group(1)
                if num == own_num:
                    continue
                if num in active:
                    if resolved != active[num].resolve():
                        add(
                            i,
                            "stale_filename",
                            num,
                            f"Link-Slug '{target_path}' entspricht nicht der aktiven Datei "
                            f"{active[num].name} fuer ADR-{num}",
                        )
                else:
                    check_number(i, num)
            else:
                # Link auf Nicht-ADR-Datei innerhalb docs/adr mit ADR-Nummer im Text
                for num in ADR_REF_RE.findall(text):
                    check_number(i, num)

        # bare Referenzen ausserhalb von Links
        for num in ADR_REF_RE.findall(rest):
            check_number(i, num)

    return findings


def run(adr_dir: pathlib.Path, repo_root: pathlib.Path) -> list[Finding]:
    active, archived = build_maps(adr_dir)
    ignore_pairs = load_ignore_pairs(adr_dir)
    findings: list[Finding] = []
    for num in sorted(active):
        findings.extend(
            lint_file(active[num], adr_dir, active, archived, ignore_pairs, repo_root)
        )
    return findings


def emit(findings: list[Finding], fmt: str) -> None:
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.category] = counts.get(f.category, 0) + 1
        if fmt == "github":
            print(
                f"::warning file={f.path},line={f.line},"
                f"title=adr-citation-lint {f.category}::{f.message}"
            )
        else:
            print(f"{f.path}:{f.line}: [{f.category}] {f.message}")
    summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "0 Findings"
    if fmt == "github":
        print(f"::warning title=adr-citation-lint summary::{len(findings)} Finding(s): {summary}")
    print(f"adr-citation-lint: {len(findings)} Finding(s) ({summary})")


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
        print(f"adr-citation-lint: Verzeichnis {adr_dir} nicht gefunden — nichts zu pruefen.")
        return 0
    repo_root = adr_dir.resolve().parent.parent  # docs/adr → repo root
    findings = run(adr_dir.resolve(), repo_root)
    emit(findings, args.format)
    if args.gate and findings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
