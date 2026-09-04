#!/usr/bin/env python3
"""handover_stale_reference_check.py — Melder `handover-prio-zeigt-auf-erledigtes`.

Zeigt eine Handover-**Priorität** auf ein geschlossenes Issue oder einen gemergten PR,
ist der Prio-Block überholt: die nächste Session startet Arbeit, die es nicht mehr gibt.
Realfall-Anker (platform#1945, Kriterium 3): am 2026-08-12 zeigte die platform-Prio
**zweimal an einem Tag** auf Überholtes; gefangen hat es nur der manuelle
Diskrepanz-Check aus session-start Phase 2.6 — also ein Mensch, der daran dachte.

Aufruf:
    python3 tools/handover_stale_reference_check.py [AGENT_HANDOVER.md] [--json]

Exit 0 = keine überholte Referenz · Exit 1 = mindestens eine (Melder, kein Blocker:
der Runner macht daraus eine WARN-Zeile) · Exit 2 = Usage/Datei nicht lesbar.

Braucht `gh` im PATH (Status-Abfrage). Ohne Netz/Token degradiert der Lauf zu
„ungeprüft" und meldet das ausdrücklich — er behauptet NICHT „keine Diskrepanz".

Tests: tools/tests/test_handover_stale_reference_check.py
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# KONZ-038 D8: der Kopf gehört ins Modul selbst, nicht nur in die Registry.
GATE_HEADER = {
    "slug": "handover-prio-zeigt-auf-erledigtes",
    "mode": "process",
    "owner": "achim",
    "last_drill_pass": "2026-08-13",
    "evidence": "tools/tests/test_handover_stale_reference_check.py",
}

#: GitHub-Referenzen in der Prio-Sektion. Nur volle URLs — eine nackte `#123` ist ohne
#: Repo-Kontext nicht auflösbar, und Raten wäre hier besonders teuer (die Flotte hat vier
#: Orgs, siehe 🌀 repo_identity_not_from_remote_name).
REF_RE = re.compile(
    r"https://github\.com/([\w.-]+)/([\w.-]+)/(issues|pull)/(\d+)",
)

#: Wörter, die eine Referenz als BEWUSSTE Erwähnung eines erledigten Dings ausweisen.
#: Ohne diese Unterscheidung meldet der Melder Sätze wie „die Wurzel unter dem am
#: 2026-08-10 **geschlossenen** #1845" als Diskrepanz — und ein Melder, der bei jedem
#: Sitzungsstart Bekanntes meldet, wird nach drei Tagen überlesen. Genau daran sind die
#: zwei Cron-Melder aus #1953 gestorben.
# `|---|---|` bzw. `|:--|--:|` — Trennzeile einer Markdown-Tabelle, nie ein Item.
TABELLEN_TRENNER_RE = re.compile(r"^\|[\s:|-]+\|?$")

SETTLED_RE = re.compile(
    r"(geschlossen|gemergt|gemerged|erledigt|abgeschlossen|behoben|✅|closed|merged)",
    re.I,
)


def _load_next_sync_helpers():
    """Importiert die Sektions-Erkennung aus `tools/next-sync/claude-next-sync`.

    Bewusst importiert statt nachgebaut: welche Überschrift die Prio-Sektion einleitet
    (und welche als Archiv NICHT zählt) ist dort zweimal teuer korrigiert worden
    (platform#1323, Retro 2026-07-22 Befund B1). Eine zweite Implementierung würde von
    genau diesen Korrekturen wieder abdriften.
    """
    path = REPO_ROOT / "tools" / "next-sync" / "claude-next-sync"
    spec = importlib.util.spec_from_loader(
        "claude_next_sync", loader=None, origin=str(path)
    )
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = str(path)
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), mod.__dict__)
    return mod


def prio_section(lines: list[str], helpers) -> tuple[int, list[str]]:
    """(Startzeile, Zeilen) der Prio-Sektion; (−1, []) wenn keine existiert."""
    start = helpers._find_section_start(lines)
    if start is None:
        return -1, []
    level = helpers._heading(lines[start])[0]
    out = []
    for line in lines[start + 1 :]:
        h = helpers._heading(line)
        if h is not None and h[0] <= level:
            break
        out.append(line)
    return start, out


def prio_items(section: list[str]) -> list[tuple[int, str]]:
    """Nur die eigentliche Prio-LISTE, nicht die ganze Sektion.

    Warum das nötig ist — gemessen, nicht vermutet: die platform-Sektion
    „Nächste Schritte" reicht über 140 Zeilen und enthält Blockquote-Kontext, in dem
    gemergte PRs völlig zu Recht genannt werden („Alt-Prio 3 ist mit #1854 erledigt").
    Auf der ganzen Sektion meldete dieser Check **18** Treffer, von denen 16 Kontext
    waren. Ein Melder mit dieser Fehlalarmquote ist nach drei Sitzungen unsichtbar —
    dieselbe Klasse, die #1953 für zwei Cron-Melder festhält.

    Grenze der Liste = das, was der SessionStart-Hook `handover_prio_mirror.sh` real
    in den Kontext spiegelt: der erste zusammenhängende nummerierte Block. Endet an
    der ersten Blockquote-/Überschriftszeile nach dem ersten Item.
    """
    items: list[tuple[int, str]] = []
    started = False
    tabelle_kopf_gesehen = False
    for offset, line in enumerate(section):
        stripped = line.strip()
        if re.match(r"^\d+\.\s", stripped):
            started = True
            items.append((offset, line))
            continue
        # Tabellenform: `| 0 | Task ... |`. Bis 2026-08-23 unsichtbar — der Parser
        # kannte nur nummerierte Listen, und `iil-klickdummy` fuehrt seine Prios als
        # Tabelle. Der Check meldete `keine_prio_items`, der Runner verbuchte das als
        # PASS, und eine seit 19 Tagen erledigte Prio stand weiter als offen da.
        # Kopfzeile und Trennzeile sind keine Items; alles danach schon.
        if stripped.startswith("|"):
            if TABELLEN_TRENNER_RE.match(stripped):
                continue
            if not tabelle_kopf_gesehen:
                tabelle_kopf_gesehen = True
                continue
            started = True
            items.append((offset, line))
            continue
        if not started:
            continue
        if stripped.startswith(">") or stripped.startswith("#"):
            break
        if not stripped:
            continue
        # Fortsetzungszeile eines Items (Umbruch) — gehört noch dazu.
        items.append((offset, line))
    return items


def refs_in(lines: list[str]) -> list[dict]:
    """Alle GitHub-Referenzen der Sektion, je mit ihrer Zeile und Zeilennummer."""
    found = []
    for offset, line in enumerate(lines):
        for m in REF_RE.finditer(line):
            owner, repo, kind, num = m.groups()
            found.append(
                {
                    "owner": owner,
                    "repo": repo,
                    "kind": "pr" if kind == "pull" else "issue",
                    "number": int(num),
                    "line_offset": offset,
                    "line": line.strip(),
                    "umfeld": line[max(0, m.start() - 90) : m.end() + 40],
                }
            )
    return found


def is_settled_mention(ref: dict) -> bool:
    """Wird die Referenz im Text ausdrücklich als erledigt beschrieben?

    Geprüft wird ein FENSTER um die Referenz (90 Zeichen davor, 40 danach), nicht die
    ganze Zeile. Auf Zeilenebene war die Regel unbrauchbar: Prio-Items sind hier 300+
    Zeichen lang und enthalten fast immer irgendwo ein „erledigt" — im Echtlauf fiel
    damit JEDE der drei platform-Prios aus der Prüfung, der Melder meldete „0 geprüft"
    und sah dabei grün aus. Genau die Sorte Fehlbefund, die er selbst finden soll.

    Trägt: „dem am 2026-08-10 **geschlossenen** #1845" (davor) und „ist erst mit #1868
    **gemergt**" (danach) — beide sind bewusste Erwähnungen, keine Zeiger.
    """
    return bool(SETTLED_RE.search(ref.get("umfeld") or ref["line"]))


def state_of(ref: dict) -> str | None:
    """'open' | 'closed' | 'merged' | None (nicht abfragbar)."""
    kind = "issue" if ref["kind"] == "issue" else "pr"
    fields = "state,url" if kind == "issue" else "state,url"
    cmd = [
        "gh",
        kind,
        "view",
        str(ref["number"]),
        "--repo",
        f"{ref['owner']}/{ref['repo']}",
        "--json",
        fields,
        "--jq",
        ".state",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except OSError:
        return None
    if res.returncode != 0:
        return None
    return res.stdout.strip().lower() or None


def check(path: Path) -> dict:
    helpers = _load_next_sync_helpers()
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start, section = prio_section(lines, helpers)
    if start < 0:
        return {"status": "keine_prio_sektion", "findings": [], "geprueft": 0}

    items = prio_items(section)
    if not items:
        return {"status": "keine_prio_items", "findings": [], "geprueft": 0}

    findings, unpruefbar, geprueft = [], [], 0
    seen: set[tuple] = set()
    for ref in refs_in([line for _off, line in items]):
        key = (ref["owner"], ref["repo"], ref["kind"], ref["number"])
        if key in seen:
            continue
        seen.add(key)
        if is_settled_mention(ref):
            continue  # ausdrücklich als erledigt beschrieben — kein Zeiger, nur Kontext
        state = state_of(ref)
        if state is None:
            unpruefbar.append(key)
            continue
        geprueft += 1
        if state in ("closed", "merged"):
            findings.append(
                {
                    "ref": f"{ref['owner']}/{ref['repo']}#{ref['number']}",
                    "kind": ref["kind"],
                    "state": state,
                    "zeile": start + 2 + items[ref["line_offset"]][0],
                    "text": ref["line"][:120],
                }
            )
    return {
        "status": "ok",
        "findings": findings,
        "geprueft": geprueft,
        "unpruefbar": [f"{o}/{r}#{n}" for o, r, _k, n in unpruefbar],
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pfad", nargs="?", default="AGENT_HANDOVER.md")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    path = Path(args.pfad)
    if not path.is_file():
        print(f"FEHLER: {path} nicht lesbar", file=sys.stderr)
        return 2

    result = check(path)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    elif result["status"].startswith("keine_prio"):
        print(f"SKIP  {result['status']} — nichts zu prüfen")
    elif not result["findings"]:
        note = (
            f" ({len(result['unpruefbar'])} nicht abfragbar: "
            f"{', '.join(result['unpruefbar'])})"
            if result.get("unpruefbar")
            else ""
        )
        print(f"PASS  {result['geprueft']} Referenz(en) offen{note}")
    else:
        for f in result["findings"]:
            print(
                f"STALE {f['ref']} ist {f['state']} — Prio-Zeile {f['zeile']}: {f['text']}"
            )
        print(
            f"\n⚠️ {len(result['findings'])} Prio-Referenz(en) zeigen auf Erledigtes — "
            "Prio-Block vor Arbeitsbeginn nachziehen (Gate handover-prio-zeigt-auf-erledigtes)."
        )
    return 1 if result["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
