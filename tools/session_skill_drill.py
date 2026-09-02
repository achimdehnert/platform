#!/usr/bin/env python3
"""Kaltstart-Drill fuer die Session-Skills (start/ende/retro) — K1 aus Issue #2690.

Misst, ob ein frischer Agent (ohne Memory, ohne Handover) einen Session-Skill
allein aus dem Skill-Text vollstaendig und richtig abarbeitet. "Stillschweigend
uebersprungen" ist der Fehler; "bewusst uebersprungen weil X" (Grund >= 3 Woerter)
ist erlaubt (Hausregel Retro c494a2).

Erwartungseinheiten eines Skills:
  - alle ``##``/``###``-Ueberschriften (mit stabiler ID = Phasen-Nummer wie
    ``0.4.3``/``2.7``/``0a-deploy`` falls die Ueberschrift so beginnt, sonst
    normalisierter Ueberschriftentext), geflaggt ``pflicht`` (Ueberschrift
    oder ihr erster Absatz enthaelt "PFLICHT"/"IMMER"/"muss") und ``neu``
    ("NEU" in Ueberschrift/erstem Absatz).
  - alle Zeilen einer Abschluss-/Startklar-Checkliste (Markdown-Tabelle mit
    Spalten ``Check``/``Status``, optional ``#``). Diese Zeilen gelten IMMER
    als Pflicht (der Zweck der Tabelle ist die Pflicht-Gate-Liste selbst).

Fehlt eine Checkliste komplett (z.B. session-retro.md), ist das ein eigener
Befund ("CHECKLISTE FEHLT", Exit-Code 2), kein Absturz.

Nur Python-Stdlib. Aufrufbar als CLI (``--erwartung``/``--vorlage``/
``--protokoll``/``--vergleich``/``--kurz``) oder importierbar fuer Tests.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_FILES = {
    "start": REPO_ROOT / ".windsurf" / "workflows" / "session-start.md",
    "ende": REPO_ROOT / ".windsurf" / "workflows" / "session-ende.md",
    "retro": REPO_ROOT / ".windsurf" / "workflows" / "session-retro.md",
}
SKILL_ORDER = ["start", "ende", "retro"]

FENCE_RE = re.compile(r"^\s*```")
HEADING_RE = re.compile(r"^(#{2,3})\s+(.*\S)\s*$")
TABLE_ROW_RE = re.compile(r"^\s*\|(.*)\|\s*$")
SEP_CELL_RE = re.compile(r"^:?-{1,}:?$")
PHASE_RE = re.compile(r"^(?:Phase\s+)?([−-]?\d+(?:[.\w-]*\w)?)\b")
PFLICHT_MARKERS = ("PFLICHT", "IMMER", "muss")
NEU_MARKER = "NEU"

_UMLAUT_MAP = str.maketrans(
    {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"}
)


@dataclass
class Einheit:
    id: str
    kind: str  # 'ueberschrift' | 'checkliste'
    text: str
    ebene: Optional[int]
    pflicht: bool
    neu: bool
    zeile: int


@dataclass
class SkillParse:
    skill: str
    pfad: Path
    headings: list = field(default_factory=list)
    checklist: list = field(default_factory=list)
    checklist_present: bool = False

    def einheiten(self):
        return list(self.headings) + list(self.checklist)


def _normalize_text(text: str) -> str:
    t = text.translate(_UMLAUT_MAP).lower()
    t = re.sub(r"[^a-z0-9]+", "-", t)
    t = t.strip("-")
    t = re.sub(r"-{2,}", "-", t)
    return t or "ueberschrift"


def _uniquify(base: str, used: set) -> str:
    candidate = base
    n = 2
    while candidate in used:
        candidate = f"{base}-dup{n}"
        n += 1
    used.add(candidate)
    return candidate


_CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")


def _split_row(line: str) -> list:
    """Zerlegt eine Markdown-Tabellenzeile in Zellen.

    Respektiert `\\|` als escapetes Pipe-Zeichen INNERHALB einer Zelle
    (GFM-Tabellensyntax) — noetig, weil die Status-Platzhalter selbst ein
    Pipe-Zeichen enthalten (siehe STATUS_PLACEHOLDER).
    """
    inner = line.strip()
    inner = inner[1:-1]  # strip outer '|' ... '|'
    cells = _CELL_SPLIT_RE.split(inner)
    return [c.strip().replace("\\|", "|") for c in cells]


def _first_paragraph(lines: list, start_idx: int) -> str:
    i = start_idx
    n = len(lines)
    while i < n and lines[i].strip() == "":
        i += 1
    para = []
    while i < n:
        line = lines[i]
        if line.strip() == "":
            break
        if HEADING_RE.match(line):
            break
        if FENCE_RE.match(line):
            break
        para.append(line)
        i += 1
    return "\n".join(para)


def _has_marker(text: str, marker: str) -> bool:
    return marker in text


def _make_heading_id(text: str, used_ids: set) -> str:
    m = PHASE_RE.match(text)
    base = m.group(1) if m else _normalize_text(text)
    return _uniquify(base, used_ids)


def parse_skill(path: Path, skill: str = "custom") -> SkillParse:
    """Parst einen Skill-Text in Ueberschriften- und Checklisten-Einheiten.

    Ueberschriften/Tabellen innerhalb von Fenced-Code-Bloecken (```...```)
    werden ignoriert — Beispiel-Heredocs im Skill-Text (z.B. session-ende.md
    Phase 2, "cat > ... <<'SUMEOF' ... ## Erledigt ...") sind kein echter
    Dokument-Abschnitt.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    n = len(lines)
    in_fence = False
    headings: list = []
    checklist: list = []
    checklist_present = False
    used_ids: set = set()
    i = 0
    while i < n:
        line = lines[i]
        if FENCE_RE.match(line):
            in_fence = not in_fence
            i += 1
            continue
        if in_fence:
            i += 1
            continue

        hm = HEADING_RE.match(line)
        if hm:
            level = len(hm.group(1))
            text_h = hm.group(2).strip()
            para = _first_paragraph(lines, i + 1)
            combined = f"{text_h}\n{para}"
            pflicht = any(_has_marker(combined, m) for m in PFLICHT_MARKERS)
            neu = _has_marker(combined, NEU_MARKER)
            uid = _make_heading_id(text_h, used_ids)
            headings.append(
                Einheit(
                    id=uid,
                    kind="ueberschrift",
                    text=text_h,
                    ebene=level,
                    pflicht=pflicht,
                    neu=neu,
                    zeile=i + 1,
                )
            )
            i += 1
            continue

        tm = TABLE_ROW_RE.match(line)
        if tm and i + 1 < n:
            cells = _split_row(line)
            lowered = [c.lower() for c in cells]
            if "check" in lowered and "status" in lowered:
                sep_line = lines[i + 1]
                if TABLE_ROW_RE.match(sep_line):
                    sep_cells = _split_row(sep_line)
                    if sep_cells and all(SEP_CELL_RE.match(c) for c in sep_cells):
                        checklist_present = True
                        idx_hash = None
                        for idx, c in enumerate(lowered):
                            if c == "#":
                                idx_hash = idx
                        idx_check = lowered.index("check")
                        j = i + 2
                        row_counter = 1
                        while j < n:
                            rl = lines[j]
                            if FENCE_RE.match(rl):
                                break
                            rm = TABLE_ROW_RE.match(rl)
                            if not rm:
                                break
                            rcells = _split_row(rl)
                            rid = (
                                rcells[idx_hash].strip()
                                if idx_hash is not None
                                and idx_hash < len(rcells)
                                and rcells[idx_hash].strip()
                                else str(row_counter)
                            )
                            rtext = (
                                rcells[idx_check].strip()
                                if idx_check < len(rcells)
                                else ""
                            )
                            uid = _uniquify(f"checkliste-{rid}", used_ids)
                            checklist.append(
                                Einheit(
                                    id=uid,
                                    kind="checkliste",
                                    text=rtext,
                                    ebene=None,
                                    pflicht=True,
                                    neu=False,
                                    zeile=j + 1,
                                )
                            )
                            row_counter += 1
                            j += 1
                        i = j
                        continue
        i += 1

    return SkillParse(
        skill=skill,
        pfad=path,
        headings=headings,
        checklist=checklist,
        checklist_present=checklist_present,
    )


# --- Protokoll-Dateien (Vorlage-Ausgabe / --protokoll-Eingabe) --------------

STATUS_PLACEHOLDER = "<erfüllt\\|bewusst übersprungen: <grund>\\|fehlt>"
BELEG_PLACEHOLDER = "<beleg>"


def parse_protokoll(path: Path) -> dict:
    """Liest eine Drill-Protokoll-Markdown-Tabelle (Spalten ID/Status/Beleg)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    n = len(lines)
    rows: dict = {}
    in_fence = False
    i = 0
    while i < n:
        line = lines[i]
        if FENCE_RE.match(line):
            in_fence = not in_fence
            i += 1
            continue
        if in_fence:
            i += 1
            continue
        tm = TABLE_ROW_RE.match(line)
        if tm and i + 1 < n:
            cells = _split_row(line)
            lowered = [c.lower() for c in cells]
            if "id" in lowered and "status" in lowered:
                sep_line = lines[i + 1]
                if TABLE_ROW_RE.match(sep_line):
                    sep_cells = _split_row(sep_line)
                    if sep_cells and all(SEP_CELL_RE.match(c) for c in sep_cells):
                        idx_id = lowered.index("id")
                        idx_status = lowered.index("status")
                        idx_beleg = lowered.index("beleg") if "beleg" in lowered else None
                        j = i + 2
                        while j < n:
                            rl = lines[j]
                            if FENCE_RE.match(rl):
                                break
                            rm = TABLE_ROW_RE.match(rl)
                            if not rm:
                                break
                            rcells = _split_row(rl)
                            rid = rcells[idx_id].strip() if idx_id < len(rcells) else ""
                            rstatus = (
                                rcells[idx_status].strip()
                                if idx_status < len(rcells)
                                else ""
                            )
                            rbeleg = (
                                rcells[idx_beleg].strip()
                                if idx_beleg is not None and idx_beleg < len(rcells)
                                else ""
                            )
                            if rid:
                                rows[rid] = {"status": rstatus, "beleg": rbeleg}
                            j += 1
                        i = j
                        continue
        i += 1
    return rows


def classify_status(status_text: str) -> str:
    """Klassifiziert eine Status-Zelle: erfuellt | bewusst_uebersprungen | still.

    "still" deckt sowohl fehlende/leere Angaben als auch unbekannten Text und
    "bewusst uebersprungen" mit zu duennem Grund (< 3 Woerter) ab — all das
    ist im Sinn von K1 ein stillschweigendes Ueberspringen.
    """
    s = status_text.strip()
    if not s:
        return "still"
    if "<" in s and ">" in s:
        return "still"  # unausgefuellter Platzhalter
    low = s.lower()
    if low.startswith("erfüllt") or low.startswith("erfuellt"):
        return "erfuellt"
    if low.startswith("bewusst übersprungen") or low.startswith("bewusst uebersprungen"):
        grund = s.split(":", 1)[1].strip() if ":" in s else ""
        wortzahl = len([w for w in re.split(r"\s+", grund) if w])
        return "bewusst_uebersprungen" if wortzahl >= 3 else "still"
    if low == "fehlt":
        return "still"
    return "still"  # unbekannter Status zaehlt konservativ als still


# --- CLI ---------------------------------------------------------------


def _resolve_skill(args, parser: argparse.ArgumentParser):
    if args.datei:
        path = Path(args.datei)
        name = args.skill or path.stem
    elif args.skill:
        path = SKILL_FILES[args.skill]
        name = args.skill
    else:
        parser.error("--skill oder --datei erforderlich")
        return None, None  # pragma: no cover (parser.error exits)
    if not path.exists():
        parser.error(f"Skill-Datei nicht gefunden: {path}")
    return path, name


def cmd_erwartung(args, parser) -> int:
    path, name = _resolve_skill(args, parser)
    sp = parse_skill(path, skill=name)
    n_pflicht = sum(1 for h in sp.headings if h.pflicht)
    n_neu = sum(1 for h in sp.headings if h.neu)
    if args.json:
        data = {
            "skill": name,
            "datei": str(path),
            "ueberschriften": len(sp.headings),
            "pflicht": n_pflicht,
            "neu": n_neu,
            "checklisten_zeilen": len(sp.checklist),
            "checkliste_vorhanden": sp.checklist_present,
            "einheiten": [asdict(e) for e in sp.einheiten()],
        }
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"Skill: {name} ({path})")
        print(f"Ueberschriften: {len(sp.headings)} (davon Pflicht: {n_pflicht}, davon NEU: {n_neu})")
        if sp.checklist_present:
            print(f"Checklisten-Zeilen: {len(sp.checklist)}")
        else:
            print("CHECKLISTE FEHLT")
    return 2 if not sp.checklist_present else 0


def cmd_vorlage(args, parser) -> int:
    path, name = _resolve_skill(args, parser)
    sp = parse_skill(path, skill=name)
    out = [f"# Drill-Protokoll: {name} ({path})", "", "| ID | Status | Beleg |", "|---|---|---|"]
    for e in sp.einheiten():
        out.append(f"| {e.id} | {STATUS_PLACEHOLDER} | {BELEG_PLACEHOLDER} |")
    print("\n".join(out))
    return 0 if sp.checklist_present else 2


def cmd_protokoll(args, parser) -> int:
    path, name = _resolve_skill(args, parser)
    sp = parse_skill(path, skill=name)
    proto = parse_protokoll(Path(args.protokoll))
    einheiten = sp.einheiten()
    ergebnisse = []
    still_total = 0
    still_pflicht = 0
    for e in einheiten:
        row = proto.get(e.id)
        status_raw = row["status"] if row else ""
        beleg = row["beleg"] if row else ""
        klasse = classify_status(status_raw) if row else "still"
        still = klasse == "still"
        if still:
            still_total += 1
            if e.pflicht:
                still_pflicht += 1
        ergebnisse.append(
            {
                "id": e.id,
                "kind": e.kind,
                "pflicht": e.pflicht,
                "status_raw": status_raw,
                "klasse": klasse,
                "still": still,
                "beleg": beleg,
            }
        )
    if args.json:
        print(
            json.dumps(
                {
                    "skill": name,
                    "datei": str(path),
                    "protokoll": str(args.protokoll),
                    "einheiten_gesamt": len(einheiten),
                    "still_uebersprungen": still_total,
                    "still_uebersprungen_pflicht": still_pflicht,
                    "ergebnisse": ergebnisse,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"Skill: {name} — Protokoll: {args.protokoll}")
        print(f"Einheiten gesamt: {len(einheiten)}")
        print(f"Still uebersprungen: {still_total} (davon Pflicht: {still_pflicht})")
        for r in ergebnisse:
            if r["still"]:
                marker = " PFLICHT" if r["pflicht"] else ""
                print(f"  - {r['id']}{marker}: still uebersprungen (status={r['status_raw']!r})")
    return 1 if still_pflicht > 0 else 0


def cmd_vergleich(args) -> int:
    pfad_a, pfad_b = args.vergleich
    a = parse_protokoll(Path(pfad_a))
    b = parse_protokoll(Path(pfad_b))
    ids = sorted(set(a) | set(b))
    abweichungen = []
    for uid in ids:
        ra = a.get(uid)
        rb = b.get(uid)
        if ra is None:
            abweichungen.append({"id": uid, "grund": "nur in B", "a": None, "b": rb["status"]})
        elif rb is None:
            abweichungen.append({"id": uid, "grund": "nur in A", "a": ra["status"], "b": None})
        elif ra["status"].strip() != rb["status"].strip():
            abweichungen.append(
                {"id": uid, "grund": "status weicht ab", "a": ra["status"], "b": rb["status"]}
            )
    if args.json:
        print(json.dumps({"abweichungen": abweichungen}, ensure_ascii=False, indent=2))
    else:
        if not abweichungen:
            print("Reproduzierbar: keine Abweichungen.")
        else:
            print(f"{len(abweichungen)} Abweichung(en):")
            for d in abweichungen:
                print(f"  - {d['id']}: {d['grund']} (A={d['a']!r} B={d['b']!r})")
    return 1 if abweichungen else 0


def cmd_kurz(args) -> int:
    segmente = []
    fehlt_irgendwo = False
    for idx, name in enumerate(SKILL_ORDER):
        path = SKILL_FILES[name]
        sp = parse_skill(path, skill=name)
        if not sp.checklist_present:
            segmente.append(f"{name} CHECKLISTE FEHLT")
            fehlt_irgendwo = True
            continue
        n_pflicht = sum(1 for h in sp.headings if h.pflicht)
        if idx == 0:
            segmente.append(f"{name} {len(sp.headings)} Einheiten/{n_pflicht} Pflicht")
        else:
            segmente.append(f"{name} {len(sp.headings)}/{n_pflicht}")
    print("K1: " + " · ".join(segmente))
    return 2 if fehlt_irgendwo else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Kaltstart-Drill fuer die Session-Skills (K1, Issue #2690).",
    )
    p.add_argument("--skill", choices=SKILL_ORDER, help="Kanonischer Skill-Name.")
    p.add_argument("--datei", type=Path, help="Skill-Datei-Pfad ueberschreiben.")
    p.add_argument("--erwartung", action="store_true", help="Erwartungseinheiten listen.")
    p.add_argument("--vorlage", action="store_true", help="Drill-Protokoll-Vorlage ausgeben.")
    p.add_argument("--protokoll", type=Path, help="Ausgefuelltes Protokoll gegen die Erwartung bewerten.")
    p.add_argument(
        "--vergleich",
        nargs=2,
        metavar=("PROTOKOLL_A", "PROTOKOLL_B"),
        help="Zwei Protokolle auf Reproduzierbarkeit vergleichen.",
    )
    p.add_argument("--kurz", action="store_true", help="Eine Zeile fuer alle drei Skills.")
    p.add_argument("--json", action="store_true", help="Maschinenlesbare Ausgabe.")
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    moden = [
        bool(args.erwartung),
        bool(args.vorlage),
        args.protokoll is not None,
        args.vergleich is not None,
        bool(args.kurz),
    ]
    if sum(moden) != 1:
        parser.error(
            "genau einer von --erwartung/--vorlage/--protokoll/--vergleich/--kurz erforderlich"
        )

    if args.erwartung:
        return cmd_erwartung(args, parser)
    if args.vorlage:
        return cmd_vorlage(args, parser)
    if args.protokoll is not None:
        return cmd_protokoll(args, parser)
    if args.vergleich is not None:
        return cmd_vergleich(args)
    if args.kurz:
        return cmd_kurz(args)
    return 0  # pragma: no cover


if __name__ == "__main__":
    sys.exit(main())
