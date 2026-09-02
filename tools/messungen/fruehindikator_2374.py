#!/usr/bin/env python3
"""platform#2374 Ziel B — Fruehindikator aus den Transkripten, Stufe 1 (modellfrei).

Misst den Moment, in dem eine pruefbare Behauptung geschrieben wird, OHNE dass im selben
Zug vorher ein Werkzeug lief. Auflage aus der Freigabe (Owner 2026-08-27): reine Messung,
KEIN Gate — sobald ungeprueft gezaehlt wird, ist die billigste Anpassung, weniger Konkretes
zu schreiben, und das macht Antworten schlechter.

Tier-Zuschnitt (Owner-Kommentar 2026-08-27): Extraktion = kein Modell (diese Datei),
Marker-Erkennung = T2, Klassenurteil = T4. Diese Stufe liefert die Kandidaten und die
strukturellen Zahlen; die Marker hier sind eine Vorfilterung, kein Urteil (Policy
evidence-discipline Punkt 4: Heuristik-Ausgabe ist Kandidat, nicht Schluss).

Zaehleinheit: Assistant-**Textblock** (nicht thinking, nicht tool_use). "Zug" = alles seit
der letzten echten Nutzer-Nachricht (user-Zeile mit Textinhalt, kein tool_result).
"Check vor Behauptung" = im selben Zug lag vor dem Textblock mindestens ein tool_result.
Das ist die strukturelle Naeherung; ob der Check den GEGENSTAND der Behauptung beruehrt
("Schreibweise != Sache"), entscheidet erst T4.

Aufruf:
    python3 tools/messungen/fruehindikator_2374.py [--dir <projekt-dir>] [--out <jsonl>]
    → Statistik auf stdout, Kandidatenzeilen als JSONL (fuer die Modellstufen).

stdlib-only. Exit 0 immer.
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import re
import sys

DEFAULT_DIR = os.path.expanduser("~/.claude/projects/-home-devuser-github-platform")

# Marker-Klassen nach policies/evidence-discipline.md ("fires when the claim carries a
# cheaply-falsifiable specificity marker"). Bewusst breit — Praezision ist Sache von T2/T4.
MARKER = {
    "artefakt": re.compile(
        r"(?:\bPR\s*#?\d+|\bIssue\s*#?\d+|(?<![\w/])#\d{2,5}\b|\b[\w./-]+\.(?:py|md|yml|yaml|sh|json|toml)\b)"
    ),
    "status": re.compile(
        r"\b(?:gr[üu]n|green|done|fertig|erledigt|gemergt|merged|deployed|live|verifiziert|validiert|bestanden|passed|CLEAN|erfolgreich|geschlossen|abgeschlossen)\b",
        re.I,
    ),
    "zahl": re.compile(
        r"\b\d+\s*(?:von|/)\s*\d+\b|\b\d+\s*(?:Tests?|Dateien|Zeilen|Commits?|Retros?|Checks?|Repos?|Gates?|%)\b"
    ),
    "datum": re.compile(r"\b20\d{2}-\d{2}-\d{2}\b"),
    "ursache": re.compile(
        r"\b(?:pre-existing|vorbestehend|nicht mein|infra(?:-| )?smell|Wurzel|root cause|Ursache ist)\b",
        re.I,
    ),
    "universal": re.compile(
        r"\b(?:alle|keine?|nie|immer|jede[rs]?|s[äa]mtliche)\b", re.I
    ),
}
STOP_RE = re.compile(r"^\s*$")


def _blocks(o: dict):
    m = o.get("message")
    if not isinstance(m, dict):
        return []
    c = m.get("content")
    if isinstance(c, str):
        return [{"type": "text", "text": c}]
    return [b for b in (c or []) if isinstance(b, dict)]


def scanne(pfad: str) -> tuple[list[dict], dict]:
    """Liefert Kandidaten (Textbloecke mit Marker) und Zaehler je Datei."""
    z = collections.Counter()
    kandidaten = []
    tools_im_zug = 0
    results_im_zug = 0
    letzte_tools: list[str] = []
    # Kontext fuer T4 ("beruehrt der Check den Gegenstand?"): die letzten Werkzeug-
    # Aufrufe und -Ergebnisse des Zuges, gekuerzt. Ohne sie kann das Klassenurteil
    # nur raten, ob ein Lauf die Behauptung tragen KONNTE.
    kontext: list[dict] = []
    zug = 0
    session = os.path.basename(pfad).split(".")[0]
    tool_namen: dict[str, str] = {}
    for line in open(pfad, encoding="utf-8", errors="replace"):
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            z["zeilen_defekt"] += 1
            continue
        t = o.get("type")
        if t == "user":
            bl = _blocks(o)
            if any(b.get("type") == "tool_result" for b in bl):
                for b in bl:
                    if b.get("type") != "tool_result":
                        continue
                    results_im_zug += 1
                    inhalt = b.get("content")
                    if isinstance(inhalt, list):
                        inhalt = " ".join(
                            str(x.get("text", ""))
                            for x in inhalt
                            if isinstance(x, dict)
                        )
                    kontext.append(
                        {
                            "art": "result",
                            "tool": tool_namen.get(str(b.get("tool_use_id")), "?"),
                            "text": str(inhalt or "")[:400],
                        }
                    )
                continue
            if any(
                b.get("type") == "text" and not STOP_RE.match(b.get("text", ""))
                for b in bl
            ):
                zug += 1
                tools_im_zug = 0
                results_im_zug = 0
                letzte_tools = []
                kontext = []
            continue
        if t != "assistant":
            continue
        for b in _blocks(o):
            bt = b.get("type")
            if bt == "tool_use":
                tools_im_zug += 1
                name = str(b.get("name", "?"))
                tool_namen[str(b.get("id"))] = name
                letzte_tools.append(name)
                eingabe = b.get("input")
                if isinstance(eingabe, dict):
                    eingabe = (
                        eingabe.get("command") or eingabe.get("file_path") or eingabe
                    )
                kontext.append({"art": "use", "tool": name, "text": str(eingabe)[:300]})
                continue
            if bt != "text":
                continue
            text = b.get("text", "") or ""
            z["textbloecke"] += 1
            z["zeichen"] += len(text)
            treffer = {k: len(r.findall(text)) for k, r in MARKER.items()}
            treffer = {k: v for k, v in treffer.items() if v}
            if not treffer:
                continue
            z["mit_marker"] += 1
            ungeprueft = results_im_zug == 0
            if ungeprueft:
                z["marker_ohne_check_im_zug"] += 1
            kandidaten.append(
                {
                    "session": session,
                    "ts": o.get("timestamp"),
                    "zug": zug,
                    "marker": treffer,
                    "tool_results_vor_block": results_im_zug,
                    "tool_uses_vor_block": tools_im_zug,
                    "letzte_tools": letzte_tools[-3:],
                    "kontext": kontext[-6:],
                    "id": f"{session[:8]}-{zug}-{z['textbloecke']}",
                    "ungeprueft_strukturell": ungeprueft,
                    "laenge": len(text),
                    "text": text[:1200],
                }
            )
    return kandidaten, z


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    dateien = sorted(glob.glob(os.path.join(a.dir, "*.jsonl")))
    gesamt = collections.Counter()
    alle: list[dict] = []
    je_tag: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter
    )
    for f in dateien:
        k, z = scanne(f)
        gesamt.update(z)
        gesamt["dateien"] += 1
        alle.extend(k)
        for e in k:
            tag = (e["ts"] or "")[:10]
            je_tag[tag]["marker"] += 1
            if e["ungeprueft_strukturell"]:
                je_tag[tag]["ungeprueft"] += 1
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            for e in alle:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    tb = gesamt["textbloecke"] or 1
    mm = gesamt["mit_marker"] or 1
    print(
        f"Dateien {gesamt['dateien']} · Textbloecke {gesamt['textbloecke']} · Zeichen {gesamt['zeichen']:,} (~{gesamt['zeichen'] // 4:,} Token, Zeichen/4)"
    )
    print(
        f"mit Marker {gesamt['mit_marker']} ({100 * gesamt['mit_marker'] / tb:.1f} % der Bloecke)"
    )
    print(
        f"Marker OHNE tool_result im selben Zug (strukturell ungeprueft): {gesamt['marker_ohne_check_im_zug']} ({100 * gesamt['marker_ohne_check_im_zug'] / mm:.1f} % der Marker-Bloecke)"
    )
    print()
    print("| Tag | Marker-Bloecke | strukturell ungeprueft | Quote |")
    print("|---|---|---|---|")
    for tag in sorted(je_tag):
        if not tag:
            continue
        c = je_tag[tag]
        print(
            f"| {tag} | {c['marker']} | {c['ungeprueft']} | {100 * c['ungeprueft'] / max(c['marker'], 1):.0f} % |"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
