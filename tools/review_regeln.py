#!/usr/bin/env python3
"""Lader, Pruefer und Generator fuer `registry/review-regeln.yaml` (KONZ-platform-070 Z1).

Die YAML ist die einzige Quelle aller Review-Regeln. Dieses Modul ist der eine
Weg, sie zu lesen — fuer den Bot-Review (`tabu_pfade`), den Context-Reviewer
(`context_muster`) und die Prosa fuer Menschen (`render_reviewer_md`). Kein
Konsument haelt eigene Regel-Literale (Kriterium K1, #3903).

CLI:

    python3 tools/review_regeln.py --check            # Drift generierter Dateien, Exit 1
    python3 tools/review_regeln.py --render           # .windsurf/rules/reviewer.md neu schreiben
    python3 tools/review_regeln.py --tabu [--profil deployed]

`--check` ist Teil von `make test` (tools/tests/test_review_regeln.py) und damit im CI.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - Umgebungsfehler, kein Logikfall
    raise SystemExit(
        "review_regeln braucht PyYAML (requirements-dev.txt: pyyaml). "
        f"Import schlug fehl: {exc}"
    ) from exc

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PFAD = REPO_ROOT / "registry" / "review-regeln.yaml"
REVIEWER_MD = REPO_ROOT / ".windsurf" / "rules" / "reviewer.md"

#: Fusszeile der generierten Dateien — Muster wie tools/cc-skill-dist (MANAGED-BY,
#: source, content_hash, do_not_edit). Kein source_commit: der aenderte sich mit jedem
#: Commit und machte `--check` nutzlos; der Hash der Quelle sagt, welcher Stand drin ist.
MARK = "MANAGED-BY: platform/tools/review_regeln.py"

KLASSEN = ("BLOCK", "WARN", "HINT")
DETEKTOR_TYPEN = ("pfad", "regex", "umfang", "llm")
REGEX_ZIELE = ("inhalt", "inhalt+pfad", "hinzugefuegt", "hinzugefuegt+pfad")
PROFILE = ("default", "deployed", "library")
KONSUMENTEN = ("bot-tabu", "context-reviewer", "reviewer-md", "advocatus")
STATUS = ("aktiv", "herabgestuft", "gestrichen")
PFLICHTFELDER = (
    "id",
    "klasse",
    "geltung",
    "detektor",
    "begruendung",
    "konsumenten",
    "seit",
    "praezision",
    "status",
)
ID_MUSTER = re.compile(r"^RR-\d{3}$")
DATUM_MUSTER = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SchemaFehler(ValueError):
    """Die Regeldatei verletzt das Schema; `fehler` nennt jede Verletzung."""

    def __init__(self, fehler: list[str]):
        self.fehler = fehler
        super().__init__("\n".join(fehler))


# ───────────────────────── Laden und Pruefen ─────────────────────────────────────────


def pruefe_schema(doc: Any) -> list[str]:
    """Alle Schema-Verletzungen als Liste; leer = gueltig."""
    fehler: list[str] = []
    if not isinstance(doc, dict):
        return ["Wurzel ist kein Mapping"]
    for kopf in ("version", "beschreibung", "generiert", "reviewer_md", "regeln"):
        if kopf not in doc:
            fehler.append(f"Kopffeld fehlt: {kopf}")
    regeln = doc.get("regeln")
    if not isinstance(regeln, list) or not regeln:
        return fehler + ["`regeln` fehlt oder ist leer"]

    gesehen: set[str] = set()
    for i, r in enumerate(regeln):
        wo = (
            f"regeln[{i}]"
            if not isinstance(r, dict)
            else f"{r.get('id', f'regeln[{i}]')}"
        )
        if not isinstance(r, dict):
            fehler.append(f"{wo}: Regel ist kein Mapping")
            continue
        for feld in PFLICHTFELDER:
            if feld not in r:
                fehler.append(f"{wo}: Pflichtfeld fehlt: {feld}")
        rid = r.get("id")
        if not isinstance(rid, str) or not ID_MUSTER.match(rid):
            fehler.append(f"{wo}: id nicht im Format RR-NNN")
        elif rid in gesehen:
            fehler.append(f"{wo}: id doppelt")
        else:
            gesehen.add(rid)
        if r.get("klasse") not in KLASSEN:
            fehler.append(f"{wo}: klasse {r.get('klasse')!r} nicht in {KLASSEN}")
        if r.get("status") not in STATUS:
            fehler.append(f"{wo}: status {r.get('status')!r} nicht in {STATUS}")
        # PyYAML liest `seit: 2026-10-13` als datetime.date; ein String ist ebenfalls erlaubt.
        seit = r.get("seit")
        if not (
            isinstance(seit, datetime.date)
            or (isinstance(seit, str) and DATUM_MUSTER.match(seit))
        ):
            fehler.append(f"{wo}: seit muss YYYY-MM-DD sein")
        if r.get("praezision") is not None and not isinstance(
            r["praezision"], (int, float)
        ):
            fehler.append(f"{wo}: praezision muss null oder Zahl sein")

        geltung = r.get("geltung")
        if not isinstance(geltung, dict):
            fehler.append(f"{wo}: geltung ist kein Mapping")
        else:
            if not isinstance(geltung.get("pfade"), list) or not geltung["pfade"]:
                fehler.append(f"{wo}: geltung.pfade fehlt oder leer")
            profile = geltung.get("profile")
            if not isinstance(profile, list) or not profile:
                fehler.append(f"{wo}: geltung.profile fehlt oder leer")
            else:
                for p in profile:
                    if p not in PROFILE:
                        fehler.append(f"{wo}: Profil {p!r} nicht in {PROFILE}")

        kons = r.get("konsumenten")
        if not isinstance(kons, list) or not kons:
            fehler.append(f"{wo}: konsumenten fehlt oder leer")
        else:
            for k in kons:
                if k not in KONSUMENTEN:
                    fehler.append(f"{wo}: Konsument {k!r} nicht in {KONSUMENTEN}")

        beg = r.get("begruendung")
        if not isinstance(beg, dict) or not beg.get("quelle") or not beg.get("text"):
            fehler.append(f"{wo}: begruendung braucht quelle und text")

        fehler.extend(f"{wo}: {f}" for f in _pruefe_detektor(r.get("detektor")))

        if "context-reviewer" in (kons or []) and not isinstance(
            r.get("ausgabe"), dict
        ):
            fehler.append(f"{wo}: Konsument context-reviewer braucht `ausgabe`")
    return fehler


def _pruefe_detektor(d: Any) -> list[str]:
    if not isinstance(d, dict):
        return ["detektor ist kein Mapping"]
    typ = d.get("typ")
    if typ not in DETEKTOR_TYPEN:
        return [f"detektor.typ {typ!r} nicht in {DETEKTOR_TYPEN}"]
    fehler: list[str] = []
    if typ in ("pfad", "regex"):
        muster = d.get("muster")
        if (
            not isinstance(muster, list)
            or not muster
            or not all(isinstance(m, str) for m in muster)
        ):
            fehler.append("detektor.muster muss nicht-leere Liste von Strings sein")
        elif typ == "regex":
            for m in muster:
                try:
                    re.compile(m)
                except re.error as exc:
                    fehler.append(f"detektor.muster {m!r} kein gueltiger Regex: {exc}")
            if d.get("ziel") not in REGEX_ZIELE:
                fehler.append(f"detektor.ziel {d.get('ziel')!r} nicht in {REGEX_ZIELE}")
    elif typ == "umfang":
        if not isinstance(d.get("max_zeilen"), int) or d["max_zeilen"] <= 0:
            fehler.append("detektor.max_zeilen muss positive Ganzzahl sein")
    elif typ == "llm":
        if not isinstance(d.get("frage"), str) or not d["frage"].strip():
            fehler.append("detektor.frage fehlt")
    return fehler


def lade_regeln(pfad: str | Path | None = None) -> dict:
    """Regeldatei laden und gegen das Schema pruefen; wirft SchemaFehler."""
    p = Path(pfad) if pfad else DEFAULT_PFAD
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    fehler = pruefe_schema(doc)
    if fehler:
        raise SchemaFehler([f"{p}: {f}" for f in fehler])
    return doc


def regeln_fuer(
    konsument: str,
    doc: dict | None = None,
    profil: str | None = None,
    nur_aktiv: bool = True,
) -> list[dict]:
    """Regeln eines Konsumenten, optional auf ein Profil eingeschraenkt."""
    doc = doc or lade_regeln()
    out = []
    for r in doc["regeln"]:
        if konsument not in r["konsumenten"]:
            continue
        if nur_aktiv and r["status"] != "aktiv":
            continue
        if profil and profil not in r["geltung"]["profile"]:
            continue
        out.append(r)
    return out


# ───────────────────────── Pfad-Matching ─────────────────────────────────────────────


def pfad_passt(dateipfad: str, muster: str) -> bool:
    """Glob-Vergleich (fnmatch, `*` ueberspannt `/`) oder exakter Pfad."""
    return dateipfad == muster or fnmatchcase(dateipfad, muster)


# ───────────────────────── Konsument: Bot-Tabu ───────────────────────────────────────


def tabu_pfade(
    profil: str = "default", pfad: str | Path | None = None
) -> tuple[str, ...]:
    """Alle Tabu-Muster des Bot-Reviews fuer ein Profil, in Dateireihenfolge."""
    doc = lade_regeln(pfad)
    muster: list[str] = []
    for r in regeln_fuer("bot-tabu", doc, profil=profil):
        for m in r["detektor"]["muster"]:
            if m not in muster:
                muster.append(m)
    return tuple(muster)


def ist_tabu(
    dateipfad: str, profil: str = "default", tabu: tuple[str, ...] | None = None
) -> bool:
    """Trifft ein Tabu-Muster auf den Pfad? `tabu` erspart das erneute Laden."""
    for m in tabu if tabu is not None else tabu_pfade(profil):
        if pfad_passt(dateipfad, m):
            return True
    return False


# ───────────────────────── Konsument: Context-Reviewer ───────────────────────────────


def context_muster(pfad: str | Path | None = None) -> dict[str, Any]:
    """Muster des Context-Reviewers, nach Ausgabe-Kategorie gruppiert.

    Rueckgabe:
      adr        {referenz: [regex, ...]}  (ziel inhalt+pfad)
      prinzipien {referenz: [regex, ...]}  (ziel hinzugefuegt+pfad)
      umfang     [{referenz, max_zeilen, konfidenz}]
      projekte   {referenz: [glob, ...]}
      insights   [regel, ...]  Datei-Hinweise in Dateireihenfolge (mit `ausgabe.meldung`)
    """
    doc = lade_regeln(pfad)
    out: dict[str, Any] = {
        "adr": {},
        "prinzipien": {},
        "umfang": [],
        "projekte": {},
        "insights": [],
    }
    for r in regeln_fuer("context-reviewer", doc):
        a = r["ausgabe"]
        d = r["detektor"]
        if a.get("meldung"):
            out["insights"].append(r)
        elif a["kategorie"] == "ADR":
            out["adr"][a["referenz"]] = list(d["muster"])
        elif a["kategorie"] == "Prinzip" and d["typ"] == "umfang":
            out["umfang"].append(
                {
                    "referenz": a["referenz"],
                    "max_zeilen": d["max_zeilen"],
                    "konfidenz": a.get("konfidenz", 0.8),
                }
            )
        elif a["kategorie"] == "Prinzip":
            out["prinzipien"][a["referenz"]] = list(d["muster"])
        elif a["kategorie"] == "Projekt":
            out["projekte"][a["referenz"]] = list(d["muster"])
    return out


# ───────────────────────── Konsument: reviewer.md ────────────────────────────────────


def _quelle_hash(pfad: Path) -> str:
    return hashlib.sha256(pfad.read_bytes()).hexdigest()[:16]


def render_reviewer_md(doc: dict | None = None, pfad: str | Path | None = None) -> str:
    """Prosa fuer Menschen aus den Regeln mit Konsument `reviewer-md`."""
    p = Path(pfad) if pfad else DEFAULT_PFAD
    doc = doc or lade_regeln(p)
    rm = doc["reviewer_md"]
    regeln = regeln_fuer("reviewer-md", doc)
    prinzipien = [r for r in regeln if r["klasse"] != "BLOCK"]
    verboten = [r for r in regeln if r["klasse"] == "BLOCK"]

    zeilen: list[str] = ["---"]
    for k, v in rm["frontmatter"].items():
        zeilen.append(f"{k}: {v}")
    zeilen += ["---", "", f"# {rm['titel']}", "", rm["rolle"].strip(), ""]
    zeilen += ["## Tech-Stack", "", rm["tech_stack"].strip(), ""]
    zeilen += ["## Architektur-Prinzipien (nicht verhandelbar)", ""]
    for n, r in enumerate(prinzipien, 1):
        zeilen.append(f"{n}. {r['begruendung']['text']} · `{r['id']}`")
    zeilen += ["", "## Verbotene Patterns (BLOCK ohne Ausnahme)", ""]
    for r in verboten:
        zeilen.append(f"- {r['begruendung']['text']} · `{r['id']}`")
    zeilen += ["", "## Wenn du Code reviewst, immer dieses Format verwenden", "", "```"]
    zeilen += rm["format"].rstrip("\n").split("\n")
    zeilen += ["```", ""]
    zeilen += [
        "## Regelquelle",
        "",
        f"Jede Regel traegt ihre ID aus `{p.relative_to(REPO_ROOT) if p.is_relative_to(REPO_ROOT) else p}`"
        " (Klasse, Geltung, Detektor, Begruendung, Praezision). Diese Datei wird daraus generiert"
        " — Aenderungen dort vornehmen und `python3 tools/review_regeln.py --render` ausfuehren.",
    ]
    footer = (
        f"\n\n<!-- {MARK} · source={p.relative_to(REPO_ROOT) if p.is_relative_to(REPO_ROOT) else p}"
        f" · content_hash=sha256:{_quelle_hash(p)} · do_not_edit -->\n"
    )
    return "\n".join(zeilen).rstrip("\n") + footer


def pruefe_drift(
    regeln_pfad: str | Path | None = None, reviewer_md: str | Path | None = None
) -> list[str]:
    """Abweichungen der generierten Dateien vom Stand der YAML; leer = kein Drift."""
    rp = Path(regeln_pfad) if regeln_pfad else DEFAULT_PFAD
    md = Path(reviewer_md) if reviewer_md else REVIEWER_MD
    doc = lade_regeln(rp)
    befunde: list[str] = []
    soll = render_reviewer_md(doc, rp)
    ist = md.read_text(encoding="utf-8") if md.exists() else ""
    if ist != soll:
        befunde.append(
            f"{md}: weicht vom Render aus {rp} ab — `python3 tools/review_regeln.py --render`"
        )
    return befunde


# ───────────────────────── CLI ───────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--regeln", default=None, help=f"Regeldatei (Default {DEFAULT_PFAD})"
    )
    ap.add_argument(
        "--reviewer-md",
        default=None,
        help=f"Zieldatei fuer --render/--check (Default {REVIEWER_MD})",
    )
    ap.add_argument(
        "--check", action="store_true", help="Schema + Drift pruefen, Exit 1 bei Befund"
    )
    ap.add_argument("--render", action="store_true", help="reviewer.md neu schreiben")
    ap.add_argument("--tabu", action="store_true", help="Tabu-Pfade ausgeben")
    ap.add_argument(
        "--context",
        action="store_true",
        help="Muster des Context-Reviewers als JSON ausgeben",
    )
    ap.add_argument("--profil", default="default", choices=PROFILE)
    a = ap.parse_args(argv)

    try:
        doc = lade_regeln(a.regeln)
    except SchemaFehler as exc:
        for f in exc.fehler:
            print(f"SCHEMA: {f}", file=sys.stderr)
        return 1

    rc = 0
    if a.tabu:
        for m in tabu_pfade(a.profil, a.regeln):
            print(m)
    if a.context:
        print(
            json.dumps(
                context_muster(a.regeln), ensure_ascii=False, indent=2, default=str
            )
        )
    if a.render:
        ziel = Path(a.reviewer_md) if a.reviewer_md else REVIEWER_MD
        ziel.write_text(render_reviewer_md(doc, a.regeln), encoding="utf-8")
        print(f"geschrieben: {ziel}")
    if a.check:
        befunde = pruefe_drift(a.regeln, a.reviewer_md)
        for b in befunde:
            print(f"DRIFT: {b}", file=sys.stderr)
        if befunde:
            rc = 1
        else:
            n = len(doc["regeln"])
            print(f"review-regeln: Schema gueltig, {n} Regeln, kein Drift")
    if not (a.tabu or a.context or a.render or a.check):
        ap.print_help()
        return 64
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
