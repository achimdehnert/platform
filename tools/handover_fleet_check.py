#!/usr/bin/env python3
"""handover_fleet_check.py — Flotten-Messung des Handover-Zustands (platform#1945, Kriterium 1).

**Was gemessen wird:** je aktivem Registry-Repo — trägt es ein `AGENT_HANDOVER.md`?
ein `AGENT_HANDOVER_LOG.md`? welches Datum trägt der jüngste Stand-Block? Optional
(`--gate`, zahlt auf Kriterium 2 ein): ist der Frische-Check `handover-stale-vor-merge`
im Repo verdrahtet?

**Warum GitHub-API und nicht der lokale Klon:** Flotten-Claims über getrackte Dateien
werden ausschließlich über die GitHub-API belegt — lokale Refs sind selbst nach
`git fetch` bis zu 5 Tage hinter live (F1-Sweep 2026-08-07: 8/24 Repos falsch als
dreckig gemeldet, erster Pilot-PR zweigte von einem stale main ab). Dasselbe Muster
nutzen `pypi_fleet_inventory.py --remote` und `publish_gate_meter.py`.

**Warum der Owner aus `full_name` kommt und nicht aus einer Prefix-Regel:** GitHub
folgt nach Umbenennung/Transfer still einem Redirect — ein hartkodierter falscher
Owner *funktioniert* dann und maskiert die Fehlzuordnung. Deshalb wird pro Repo
`/repos/{org}/{name}` abgefragt und der Owner aus dem `full_name` der **Antwort**
gelesen, nicht aus dem angefragten Pfad.

**Determinismus (Kriterium 1 verlangt zwei identische Läufe):** die Nutzlast enthält
keinen Zeitstempel und keine Laufzeit-Zufälligkeit; Repos werden sortiert ausgegeben.
`--json` ist damit byte-gleich zwischen zwei Läufen, solange sich auf GitHub nichts
ändert. Der einzige Zeitbezug (`--json` → `stand_alter_tage`) ist bewusst NICHT Teil
der Ausgabe — er wäre tagesabhängig.

Aufruf:
    python3 tools/handover_fleet_check.py              # Tabelle
    python3 tools/handover_fleet_check.py --json       # maschinenlesbar
    python3 tools/handover_fleet_check.py --gate       # + Spalte "Gate verdrahtet?"

Token: `GH_TOKEN`/`GITHUB_TOKEN` aus dem Env, sonst Fallback `gh auth token`.
Exit 0 = Messung gelaufen (auch bei Lücken — die Lücken SIND das Ergebnis).
Exit 2 = kein Token / Registry nicht lesbar.

Tests: tools/tests/test_handover_fleet_check.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import registry_api as reg  # noqa: E402  (nach sys.path-Setup)

# Die Datums-Konvention des Stand-Blocks wird NICHT neu definiert, sondern aus dem
# Gate importiert, das sie erzwingt — sonst driften Messung und Gate auseinander.
sys.path.insert(0, str(ROOT / "scripts" / "checks"))
from agent_handover_freshness_check import (  # noqa: E402
    HEAD_LINES,
    HEADING_DATE_RE,
)

#: Reihenfolge nur für die Owner-Suche; der tatsächliche Owner kommt aus `full_name`.
ORGS = ("achimdehnert", "iilgmbh", "ttz-lif", "meiki-lra")

HANDOVER_FILE = "AGENT_HANDOVER.md"
LOG_FILE = "AGENT_HANDOVER_LOG.md"

#: Lifecycle-Werte, die ein Repo aus der Messung nehmen (Out-of-Scope laut #1945).
INACTIVE_LIFECYCLES = {"archived", "frozen"}

#: Dateinamen-Heuristik für die Gate-Verdrahtung (nur mit --gate).
GATE_WF_NAME_RE = re.compile(r"hand(off|over)", re.IGNORECASE)
#: Inhaltlicher Beleg: der Caller referenziert den reusable Workflow. Beide Heimaten
#: zählen — der Gate-Workflow ist von `platform` nach `iilgmbh/shared-ci` gewandert
#: (apo-hub pinnt heute `shared-ci/...@v1.1.1`), und eine Regex nur auf `platform`
#: meldete die ganze verdrahtete Hälfte der Flotte fälschlich als „unklar".
GATE_REF_RE = re.compile(
    r"(?:platform|shared-ci)/\.github/workflows/handoff-banner-gate\.yml@(\S+)"
)


def token_from_env_or_gh() -> str:
    """GH_TOKEN/GITHUB_TOKEN, sonst `gh auth token` (lokaler Komfort-Fallback)."""
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if tok:
        return tok
    try:
        res = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, timeout=10
        )
    except OSError:
        return ""
    return res.stdout.strip() if res.returncode == 0 else ""


def gh_api(path: str, token: str, raw: bool = False) -> object | None:
    """GET auf api.github.com. None = nicht vorhanden/kein Zugriff (fail-soft)."""
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header(
        "Accept",
        "application/vnd.github.raw" if raw else "application/vnd.github+json",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    if raw:
        return body
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def active_repos(canon: dict) -> list[str]:
    """Aktive Repos laut Registry: lifecycle nicht archived/frozen, nicht stillgelegt."""
    dead = {d.get("name") for d in canon.get("decommissioned", []) or []}
    out = []
    for name, entry in canon["repos"].items():
        if name in dead:
            continue
        lifecycle = entry.get("lifecycle") or (entry.get("rich") or {}).get("lifecycle")
        if lifecycle in INACTIVE_LIFECYCLES:
            continue
        out.append(name)
    return sorted(out)


def resolve_repo(name: str, token: str) -> dict | None:
    """Sucht das Repo in den bekannten Orgs. Owner kommt aus `full_name` der Antwort
    (Redirect-fest), nicht aus dem angefragten Pfad."""
    for org in ORGS:
        meta = gh_api(f"/repos/{org}/{name}", token)
        if not isinstance(meta, dict) or "full_name" not in meta:
            continue
        return {
            "full_name": meta["full_name"],
            "default_branch": meta.get("default_branch", "main"),
            "gh_archived": bool(meta.get("archived")),
        }
    return None


def heading_date_from_text(text: str) -> date | None:
    """Jüngstes YYYY-MM-DD aus einer Markdown-Überschrift der ersten HEAD_LINES Zeilen.

    Textvariante von `agent_handover_freshness_check.heading_date` (dort Path-basiert) —
    Regex und Fensterbreite sind importiert, damit beide dieselbe Konvention sehen.
    """
    found: date | None = None
    for i, line in enumerate(text.splitlines()):
        if i >= HEAD_LINES:
            break
        m = HEADING_DATE_RE.match(line)
        if not m:
            continue
        try:
            d = date.fromisoformat(m.group(1))
        except ValueError:
            continue
        if found is None or d > found:
            found = d
    return found


def gate_state(full_name: str, token: str) -> str:
    """Ist der Frische-Check im Repo verdrahtet? (Kriterium 2, nur mit --gate)

    'ja@<ref>' — ein Workflow referenziert den reusable Gate-Workflow (mit Pin)
    'unklar'  — namensverdächtiger Workflow vorhanden, aber ohne diese Referenz
    'nein'    — kein namensverdächtiger Workflow
    'n/a'     — kein .github/workflows-Verzeichnis lesbar

    Grenze der Messung: erkannt werden nur Caller, deren **Dateiname** `handoff`/`handover`
    enthält. Ein anders benannter Caller erscheint als 'nein' — der Fehler geht Richtung
    „zu wenig gemeldet" (ein überflüssiger Rollout-PR), nicht Richtung falsch-grün.
    """
    listing = gh_api(f"/repos/{full_name}/contents/.github/workflows", token)
    if not isinstance(listing, list):
        return "n/a"
    candidates = sorted(
        e["name"]
        for e in listing
        if isinstance(e, dict)
        and e.get("name", "").endswith((".yml", ".yaml"))
        and GATE_WF_NAME_RE.search(e.get("name", ""))
    )
    if not candidates:
        return "nein"
    for wf in candidates:
        text = gh_api(
            f"/repos/{full_name}/contents/.github/workflows/{wf}", token, raw=True
        )
        m = GATE_REF_RE.search(text) if isinstance(text, str) else None
        if m:
            return f"ja@{m.group(1)}"
    return "unklar"


def measure_repo(name: str, token: str, with_gate: bool) -> dict:
    """Ein Registry-Repo messen. Fehlendes Repo ist ein Ergebnis, kein Abbruch."""
    row: dict = {"repo": name}
    meta = resolve_repo(name, token)
    if meta is None:
        row.update(
            {
                "owner": None,
                "gefunden": False,
                "handover": False,
                "log": False,
                "stand": None,
            }
        )
        if with_gate:
            row["gate"] = "n/a"
        return row

    full_name = meta["full_name"]
    row["owner"] = full_name.split("/")[0]
    row["gefunden"] = True
    row["gh_archived"] = meta["gh_archived"]

    handover = gh_api(f"/repos/{full_name}/contents/{HANDOVER_FILE}", token, raw=True)
    log = gh_api(f"/repos/{full_name}/contents/{LOG_FILE}", token, raw=True)
    row["handover"] = isinstance(handover, str)
    row["log"] = isinstance(log, str)
    stand = heading_date_from_text(handover) if isinstance(handover, str) else None
    row["stand"] = stand.isoformat() if stand else None
    if with_gate:
        row["gate"] = gate_state(full_name, token)
    return row


def render_table(rows: list[dict], with_gate: bool) -> str:
    """Markdown-Tabelle. Sortiert, ohne Zeitstempel — zwei Läufe sind byte-gleich."""
    head = ["Repo", "Owner", "Handover", "Log", "Stand"]
    if with_gate:
        head.append("Gate")
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in rows:
        if not r["gefunden"]:
            cells = [r["repo"], "—", "nicht gefunden", "—", "—"]
            if with_gate:
                cells.append("—")
            lines.append("| " + " | ".join(cells) + " |")
            continue
        cells = [
            r["repo"],
            r["owner"],
            "ja" if r["handover"] else "**nein**",
            "ja" if r["log"] else "nein",
            (r["stand"] or "**kein Datum**") if r["handover"] else "—",
        ]
        if with_gate:
            g = r["gate"]
            cells.append(g if g.startswith("ja@") else f"**{g}**")
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def summarize(rows: list[dict], with_gate: bool) -> str:
    found = [r for r in rows if r["gefunden"]]
    missing = [r for r in rows if not r["gefunden"]]
    no_handover = [r for r in found if not r["handover"]]
    no_log = [r for r in found if not r["log"]]
    no_date = [r for r in found if r["handover"] and not r["stand"]]
    out = [
        f"Registry-Repos aktiv: {len(rows)} · auf GitHub gefunden: {len(found)}"
        + (f" · nicht gefunden: {len(missing)}" if missing else ""),
        f"ohne {HANDOVER_FILE}: {len(no_handover)} · ohne {LOG_FILE}: {len(no_log)}"
        f" · mit Datei aber ohne datierten Stand: {len(no_date)}",
    ]
    if with_gate:
        no_gate = [r for r in found if not str(r.get("gate", "")).startswith("ja@")]
        out.append(f"Frische-Gate nicht nachweisbar verdrahtet: {len(no_gate)}")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="maschinenlesbare Ausgabe")
    ap.add_argument(
        "--gate",
        action="store_true",
        help="zusätzlich prüfen, ob handover-stale-vor-merge verdrahtet ist (Kriterium 2)",
    )
    ap.add_argument("--repo", action="append", help="nur diese Repos messen (mehrfach)")
    args = ap.parse_args(argv)

    token = token_from_env_or_gh()
    if not token:
        print(
            "FEHLER: kein Token — GH_TOKEN/GITHUB_TOKEN setzen oder `gh auth login`.",
            file=sys.stderr,
        )
        return 2

    try:
        canon = reg.load_canonical()
    except OSError as exc:
        print(f"FEHLER: Registry nicht lesbar: {exc}", file=sys.stderr)
        return 2

    names = sorted(args.repo) if args.repo else active_repos(canon)
    rows = [measure_repo(n, token, args.gate) for n in names]

    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(render_table(rows, args.gate))
        print()
        print(summarize(rows, args.gate))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
