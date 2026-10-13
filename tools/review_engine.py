#!/usr/bin/env python3
"""Regel-Engine: mechanische Review-Befunde eines PR-Diffs (KONZ-platform-070 Z2 Stufe 1).

Liest die Regeln ausschliesslich ueber tools/review_regeln.py aus
registry/review-regeln.yaml (Kriterium K1, #3903 WP2) und wendet die mechanisch
pruefbaren Detektoren auf einen Git-Diff an:

    pfad    Datei geaendert, deren Pfad ein Muster trifft  → Befund je Datei
    regex   Muster im Inhalt (`inhalt`) oder nur in hinzugefuegten Zeilen
            (`hinzugefuegt`); `+pfad` prueft zusaetzlich den Dateipfad      → Befund je Zeile
    umfang  Summe geaenderter Zeilen des PR > max_zeilen                     → Befund je PR
    llm     nicht mechanisch; wird nur gezaehlt (Stufe 2, Advocatus)

Klasse BLOCK bei `pfad` heisst „bleibt Mensch“ — der Check meldet das als Hinweis
und faellt nicht; ein Mensch-Review ist kein Fehler im Code. BLOCK aus `regex`/
`umfang` laesst den Check nur mit --blockieren fehlschlagen (Schalter, Pilot zuerst
advisory). Approve oder Request-Changes gibt die Engine nie (Charta Art. 3).

Aufruf (shared-ci _review.yml):
    python3 tools/review_engine.py --repo-pfad . --basis <sha> --kopf <sha> \
        --profil deployed --github --json review-befunde.json [--blockieren]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import review_regeln as rr  # noqa: E402

#: Detektoren, die diese Engine selbst auswertet; `llm` bleibt dem Advocatus.
MECHANISCH = ("pfad", "regex", "umfang")
#: Obergrenze Befunde je Regel und Datei, damit ein Massen-Treffer den Check nicht flutet.
MAX_JE_REGEL_UND_DATEI = 20
#: Lokator-Form fuer Befunde, die den ganzen PR betreffen (umfang).
LOKATOR_PR = "PR"
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


@dataclass(frozen=True)
class Befund:
    regel_id: str
    klasse: str
    locator: str
    konfidenz: float
    titel: str
    begruendung: str
    detektor: str
    mensch_noetig: bool

    def als_dict(self) -> dict:
        return asdict(self)


@dataclass
class Diff:
    """Geaenderte Dateien mit hinzugefuegten Zeilen (nummer, text) und Zeilensumme."""

    hinzugefuegt: dict[str, list[tuple[int, str]]]
    geaenderte_zeilen: int

    @property
    def dateien(self) -> list[str]:
        return sorted(self.hinzugefuegt)


# ───────────────────────── Git-Diff lesen ─────────────────────────────────────────────


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


def parse_unified_diff(text: str) -> Diff:
    """`git diff -U0`-Ausgabe in hinzugefuegte Zeilen je Datei und Zeilensumme zerlegen."""
    hinzugefuegt: dict[str, list[tuple[int, str]]] = {}
    datei: str | None = None
    zeile = 0
    summe = 0
    for roh in text.splitlines():
        if roh.startswith("+++ "):
            ziel = roh[4:].strip()
            datei = (
                None
                if ziel == "/dev/null"
                else ziel[2:]
                if ziel.startswith("b/")
                else ziel
            )
            if datei is not None:
                hinzugefuegt.setdefault(datei, [])
            continue
        if (
            roh.startswith("--- ")
            or roh.startswith("diff ")
            or roh.startswith("index ")
        ):
            continue
        m = HUNK.match(roh)
        if m:
            zeile = int(m.group(1))
            continue
        if roh.startswith("-"):
            summe += 1  # auch Zeilen geloeschter Dateien (+++ /dev/null) zaehlen
        elif roh.startswith("+") and datei is not None:
            hinzugefuegt[datei].append((zeile, roh[1:]))
            zeile += 1
            summe += 1
    return Diff(hinzugefuegt=hinzugefuegt, geaenderte_zeilen=summe)


def diff_lesen(repo: Path, basis: str, kopf: str) -> Diff:
    """Diff basis..kopf ohne Kontextzeilen, Umbenennungen als Loeschen+Anlegen."""
    text = _git(repo, "diff", "-U0", "--no-color", "--no-renames", basis, kopf)
    diff = parse_unified_diff(text)
    # Geloeschte Dateien tauchen mit `+++ /dev/null` nicht auf; ihr Pfad zaehlt fuer
    # Pfad-Regeln trotzdem (z. B. CODEOWNERS entfernt).
    for name in _git(
        repo, "diff", "--name-only", "--no-renames", basis, kopf
    ).splitlines():
        diff.hinzugefuegt.setdefault(name.strip(), [])
    return diff


def inhalt_lesen(repo: Path, kopf: str, pfad: str) -> str:
    try:
        return _git(repo, "show", f"{kopf}:{pfad}")
    except subprocess.CalledProcessError:
        return ""  # geloescht oder binaer


# ───────────────────────── Regeln anwenden ────────────────────────────────────────────


def regeln_mechanisch(doc: dict, profil: str) -> list[dict]:
    """Aktive Regeln des Profils, deren Detektor die Engine selbst prueft."""
    return [
        r
        for r in doc["regeln"]
        if r["status"] == "aktiv"
        and profil in r["geltung"]["profile"]
        and r["detektor"]["typ"] in MECHANISCH
    ]


def regeln_llm(doc: dict, profil: str) -> list[dict]:
    return [
        r
        for r in doc["regeln"]
        if r["status"] == "aktiv"
        and profil in r["geltung"]["profile"]
        and r["detektor"]["typ"] == "llm"
    ]


def _gilt_fuer(regel: dict, pfad: str) -> bool:
    return any(rr.pfad_passt(pfad, g) for g in regel["geltung"]["pfade"])


def _konfidenz(regel: dict, default: float) -> float:
    return float((regel.get("ausgabe") or {}).get("konfidenz", default))


def _befund(regel: dict, locator: str, konfidenz: float) -> Befund:
    d = regel["detektor"]
    return Befund(
        regel_id=regel["id"],
        klasse=regel["klasse"],
        locator=locator,
        konfidenz=konfidenz,
        titel=regel.get("titel", regel["id"]),
        begruendung=regel["begruendung"]["text"],
        detektor=d["typ"],
        mensch_noetig=(d["typ"] == "pfad" and regel["klasse"] == "BLOCK"),
    )


def _regex_treffer(regel: dict, pfad: str, diff: Diff, inhalt: str) -> list[Befund]:
    d = regel["detektor"]
    muster = [re.compile(m, re.IGNORECASE) for m in d["muster"]]
    ziel = d["ziel"]
    # HINT-Regeln sind Themen-Marker (Context-Reviewer: "betrifft ADR-x"), keine
    # Defekte — ein Befund je Datei genuegt; BLOCK/WARN zeigen jede Zeile.
    limit = 1 if regel["klasse"] == "HINT" else MAX_JE_REGEL_UND_DATEI
    out: list[Befund] = []
    if ziel.endswith("+pfad") and any(m.search(pfad) for m in muster):
        out.append(_befund(regel, pfad, _konfidenz(regel, 1.0)))
    if ziel.startswith("hinzugefuegt"):
        zeilen = diff.hinzugefuegt.get(pfad, [])
    else:
        zeilen = list(enumerate(inhalt.splitlines(), start=1))
    for nr, text in zeilen:
        if len(out) >= limit:
            break
        if any(m.search(text) for m in muster):
            out.append(_befund(regel, f"{pfad}:{nr}", _konfidenz(regel, 1.0)))
    return out


def befunde(
    repo: Path, basis: str, kopf: str, profil: str = "default", doc: dict | None = None
) -> tuple[list[Befund], dict]:
    """Alle mechanischen Befunde des Diffs plus Kennzahlen fuer die Zusammenfassung."""
    doc = doc or rr.lade_regeln()
    diff = diff_lesen(repo, basis, kopf)
    regeln = regeln_mechanisch(doc, profil)
    out: list[Befund] = []
    inhalte: dict[str, str] = {}
    for regel in regeln:
        d = regel["detektor"]
        if d["typ"] == "umfang":
            if diff.geaenderte_zeilen > d["max_zeilen"]:
                out.append(_befund(regel, LOKATOR_PR, _konfidenz(regel, 0.9)))
            continue
        for pfad in diff.dateien:
            if not _gilt_fuer(regel, pfad):
                continue
            if d["typ"] == "pfad":
                if any(rr.pfad_passt(pfad, m) for m in d["muster"]):
                    out.append(_befund(regel, pfad, _konfidenz(regel, 1.0)))
                continue
            if d["ziel"].startswith("inhalt") and pfad not in inhalte:
                inhalte[pfad] = inhalt_lesen(repo, kopf, pfad)
            out.extend(_regex_treffer(regel, pfad, diff, inhalte.get(pfad, "")))
    kennzahlen = {
        "dateien": len(diff.dateien),
        "geaenderte_zeilen": diff.geaenderte_zeilen,
        "regeln_mechanisch": len(regeln),
        "regeln_llm": len(regeln_llm(doc, profil)),
        "profil": profil,
    }
    return out, kennzahlen


# ───────────────────────── Ausgabe ────────────────────────────────────────────────────


def blockierende(befunde_: list[Befund]) -> list[Befund]:
    """BLOCK-Befunde aus Inhalt/Umfang — nur die duerfen den Check fallen lassen."""
    return [b for b in befunde_ if b.klasse == "BLOCK" and not b.mensch_noetig]


def annotation(b: Befund) -> str:
    """GitHub-Workflow-Kommando mit Locator (Datei:Zeile), Klasse → Schwere."""
    if b.mensch_noetig:
        stufe, titel = "notice", f"{b.regel_id} Mensch-Review noetig"
    elif b.klasse == "BLOCK":
        stufe, titel = "error", f"{b.regel_id} {b.titel}"
    elif b.klasse == "WARN":
        stufe, titel = "warning", f"{b.regel_id} {b.titel}"
    else:
        stufe, titel = "notice", f"{b.regel_id} {b.titel}"
    ort = ""
    if b.locator != LOKATOR_PR:
        pfad, _, zeile = b.locator.partition(":")
        ort = f" file={pfad}" + (f",line={zeile}" if zeile else "")
    text = b.begruendung.replace("\n", " ")
    return f"::{stufe}{ort},title={titel}::{text}"


def zusammenfassung(befunde_: list[Befund], kennzahlen: dict) -> str:
    zeilen = [
        "## Review-Check (Regel-Engine, KONZ-070 Stufe 1)",
        "",
        f"Profil `{kennzahlen['profil']}` · {kennzahlen['dateien']} Dateien · "
        f"{kennzahlen['geaenderte_zeilen']} geaenderte Zeilen · "
        f"{kennzahlen['regeln_mechanisch']} mechanische Regeln · "
        f"{kennzahlen['regeln_llm']} LLM-Regeln (Stufe 2, Advocatus)",
        "",
    ]
    if not befunde_:
        zeilen.append("Keine Befunde.")
        return "\n".join(zeilen) + "\n"
    zeilen += ["| Regel | Klasse | Locator | Befund |", "|---|---|---|---|"]
    for b in befunde_:
        klasse = "BLOCK (Mensch)" if b.mensch_noetig else b.klasse
        zeilen.append(f"| {b.regel_id} | {klasse} | `{b.locator}` | {b.titel} |")
    return "\n".join(zeilen) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--repo-pfad", default=".", help="Git-Arbeitsbaum des geprueften Repos"
    )
    ap.add_argument("--basis", required=True, help="Basis-Commit (PR base)")
    ap.add_argument("--kopf", required=True, help="Kopf-Commit (PR head)")
    ap.add_argument("--profil", default="default", choices=rr.PROFILE)
    ap.add_argument("--regeln", help="abweichende Regeldatei (Tests)")
    ap.add_argument("--json", help="Befunde als JSON-Datei (Ledger-Felder)")
    ap.add_argument("--github", action="store_true", help="Annotations + Step-Summary")
    ap.add_argument(
        "--blockieren",
        action="store_true",
        help="Exit 1 bei BLOCK aus Inhalt/Umfang (Pfad-BLOCK bleibt Hinweis)",
    )
    a = ap.parse_args(argv)

    doc = rr.lade_regeln(a.regeln) if a.regeln else rr.lade_regeln()
    liste, kennzahlen = befunde(Path(a.repo_pfad), a.basis, a.kopf, a.profil, doc)
    text = zusammenfassung(liste, kennzahlen)
    if a.json:
        Path(a.json).write_text(
            json.dumps(
                {"kennzahlen": kennzahlen, "befunde": [b.als_dict() for b in liste]},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    if a.github:
        for b in liste:
            print(annotation(b))
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as fh:
                fh.write(text)
    print(text, end="")
    harte = blockierende(liste)
    if harte and a.blockieren:
        print(f"{len(harte)} blockierende Befunde — Check faellt (--blockieren).")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
