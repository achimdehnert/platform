#!/usr/bin/env python3
"""Dauerhaft rote Cron-Workflows auf `main` finden (platform#1508).

Ein **Melder**, der selbst rot ist, meldet nichts mehr. Genau das lag am
2026-07-22/23 vor: `Runner Health Check` und `Deploy Failure Monitor` scheiterten
beide an `HTTP 401: Bad credentials` und liefen **sechs Tage** rot, ohne dass es
in einer Session auffiel — Phase 0.7 des Session-Start-Runners prüft Deploy-Läufe,
aber nicht den Zustand der Cron-Workflows. Ein dauerhaft roter Melder ist
schlimmer als kein Melder, weil er Abdeckung vortäuscht.

Abgrenzung (🌀 `feedback_run_conclusion_not_tool_health`): **rot heißt nicht
kaputt.** Manche Workflows sind so gebaut, dass ein roter Lauf ein FUND ist —
`Registry-Live-Reconcile (KONZ-015)` etwa meldet damit Drift. Solche Workflows
tragen die Zeile `# ROT-IST-BEFUND` in ihrer YAML-Datei; sie brauchen Triage,
nicht Reparatur.

Sie werden aber **nicht mehr übersprungen**, sondern getrennt als `TRIAGE`
ausgewiesen (2026-07-31). Der erste Entwurf ließ sie ganz aus dem Bericht
fallen — mit zwei Folgen, beide real eingetreten: `Prod-Uptime-Canary` trug den
Marker gar nicht und wurde deshalb als blinder Melder **fehlklassifiziert**,
obwohl er tat, was er soll (Issue #1547, am selben Tag aktualisiert); und die
zwei offenen Drift-Funde von `Registry-Live-Reconcile` blieben unsichtbar, weil
ein markierter Workflow im Bericht überhaupt nicht mehr vorkam. Ein Marker darf
die Ursache umdeuten, nicht den Fund verschwinden lassen.

Gemeldet wird erst ab N aufeinanderfolgenden roten Läufen (Default 3) — ein
einzelner roter Lauf kann ein transienter Netz-/Runner-Fehler sein, und eine
Warnung pro Ausrutscher erzeugt genau die Alarm-Müdigkeit, gegen die dieser
Check antritt.

Ausgabe endet auf `RESULT: OK|BEFUND|TRIAGE|UNGEPRUEFT — <text>` (maschinenlesbar
für `tools/session_start_checks.sh`, Phase 0.7.2).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

#: Wer diese Zeile in seiner Workflow-YAML trägt, ist absichtlich rot, wenn er
#: etwas gefunden hat — kein Defekt, kein Befund dieses Checks.
MARKER_ROT_IST_BEFUND = "ROT-IST-BEFUND"

_NAME_RE = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)


def geplante_workflows(workflow_dir: Path) -> tuple[dict[str, Path], dict[str, Path]]:
    """`(melder, rot_ist_befund)` — beides {Workflow-Name: Datei}.

    Erfasst alle Workflows mit `schedule:`-Trigger und trennt sie am Marker
    `ROT-IST-BEFUND`: die erste Gruppe soll grün sein (rot = kaputt), die
    zweite darf rot sein (rot = Fund). Beide werden abgerufen — die zweite
    landet als Triage-Hinweis im Bericht, nicht im Papierkorb.

    Bewusst eine Textprüfung statt eines YAML-Parsers: der Runner soll ohne
    PyYAML laufen, und `schedule:` ist in diesen Dateien eindeutig.
    """
    melder: dict[str, Path] = {}
    befund: dict[str, Path] = {}
    for datei in sorted(workflow_dir.glob("*.yml")) + sorted(
        workflow_dir.glob("*.yaml")
    ):
        text = datei.read_text(encoding="utf-8", errors="replace")
        if "schedule:" not in text:
            continue
        if m := _NAME_RE.search(text):
            name = m.group(1).strip().strip("\"'")
            (befund if MARKER_ROT_IST_BEFUND in text else melder)[name] = datei
    return melder, befund


def rote_serien(runs: list[dict], schwelle: int) -> dict[str, dict]:
    """Workflows, deren jüngste `schwelle` Läufe ALLE failure sind.

    `runs` ist die Roh-Liste aus der Actions-API (neueste zuerst ist NICHT
    vorausgesetzt — es wird selbst sortiert).
    """
    nach_wf: dict[str, list[dict]] = {}
    for r in runs:
        nach_wf.setdefault(r.get("name", ""), []).append(r)
    befunde: dict[str, dict] = {}
    for name, liste in nach_wf.items():
        liste.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        # `completed` allein zählt: ein noch laufender Lauf sagt nichts aus.
        fertig = [r for r in liste if r.get("status") == "completed"]
        if len(fertig) < schwelle:
            continue
        if any(r.get("conclusion") != "failure" for r in fertig[:schwelle]):
            continue
        rot = [r for r in fertig if r.get("conclusion") == "failure"]
        # Wie weit zurück ist die Serie ununterbrochen rot?
        serie = 0
        for r in fertig:
            if r.get("conclusion") != "failure":
                break
            serie += 1
        befunde[name] = {
            "serie": serie,
            "seit": (rot[serie - 1].get("created_at") or "")[:10],
            "letzter": (fertig[0].get("created_at") or "")[:16],
            "url": fertig[0].get("html_url", ""),
        }
    return befunde


def _hole_runs(repo: str, branch: str, workflow_datei: str, limit: int) -> list[dict]:
    """Läufe EINES Workflows.

    Bewusst je Workflow und nicht ein Sammel-Abruf über `actions/runs`: dort
    verdrängt ein stündlicher Workflow die täglichen aus dem Fenster. Der erste
    Entwurf dieses Checks tat genau das und übersah `Runner Health Check` — er
    meldete 1 von 2 blinden Meldern und sah dabei vollständig aus. Dieselbe
    Fehlerklasse wie 🌀 `feedback_invented_wildcard_is_not_full_enumeration`.
    """
    roh = subprocess.run(
        [
            "gh",
            "api",
            "-X",
            "GET",
            f"repos/{repo}/actions/workflows/{workflow_datei}/runs",
            "-f",
            "event=schedule",
            "-f",
            f"branch={branch}",
            "-f",
            f"per_page={limit}",
            "--jq",
            ".workflow_runs[] | {name, status, conclusion, created_at, html_url}",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if roh.returncode != 0:
        raise RuntimeError(
            (roh.stderr or "gh-Aufruf fehlgeschlagen").strip().splitlines()[-1]
        )
    return [json.loads(z) for z in roh.stdout.splitlines() if z.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default="achimdehnert/platform")
    ap.add_argument("--branch", default="main")
    ap.add_argument(
        "--schwelle",
        type=int,
        default=3,
        help="ab wie vielen roten Läufen in Folge gemeldet wird (Default 3)",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=10,
        help="wie viele Läufe je Workflow geholt werden",
    )
    ap.add_argument(
        "--workflow-dir",
        default=None,
        help="Verzeichnis mit den Workflow-Dateien (Default: <repo-root>/.github/workflows)",
    )
    ap.add_argument("--quiet", action="store_true", help="nur die RESULT-Zeile")
    args = ap.parse_args()

    wf_dir = (
        Path(args.workflow_dir).expanduser()
        if args.workflow_dir
        else (Path(__file__).resolve().parents[1] / ".github" / "workflows")
    )
    if not wf_dir.is_dir():
        print(f"RESULT: UNGEPRUEFT — Workflow-Verzeichnis fehlt: {wf_dir}")
        return 0

    melder, rot_ist_befund = geplante_workflows(wf_dir)
    geplant = {**melder, **rot_ist_befund}
    if not geplant:
        print(f"RESULT: OK — keine geplanten Workflows in {wf_dir.name}")
        return 0

    befunde: dict[str, dict] = {}
    triage: dict[str, dict] = {}
    ungeprueft: list[str] = []

    def _einer(name_datei: tuple[str, Path]):
        name, datei = name_datei
        return name, _hole_runs(args.repo, args.branch, datei.name, args.limit)

    # Ein Abruf je Workflow, aber nebenläufig — seriell dauerte der Lauf 13s und
    # wäre in Phase 0.7.2 des Session-Start-Runners spürbar.
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(_einer, (n, d)): n in rot_ist_befund for n, d in geplant.items()
        }
        for fut in as_completed(futures):
            try:
                _, runs = fut.result()
            except (RuntimeError, subprocess.TimeoutExpired, OSError) as e:
                # Nicht als OK durchgehen lassen — ungeprüft ist ungeprüft.
                ungeprueft.append(str(e))
                continue
            (triage if futures[fut] else befunde).update(
                rote_serien(runs, args.schwelle)
            )

    if not args.quiet:
        print(
            f"Geprüft: {len(geplant) - len(ungeprueft)}/{len(geplant)} geplante Workflow(s) "
            f"auf {args.repo}@{args.branch}, Schwelle {args.schwelle} "
            f"({len(rot_ist_befund)} davon mit {MARKER_ROT_IST_BEFUND}-Marker)"
        )
        for name, b in sorted(befunde.items()):
            print(
                f"  ROT  {name} — {b['serie']} Läufe in Folge, seit {b['seit']}, "
                f"zuletzt {b['letzter']}"
            )
            print(f"       {b['url']}")
        for name, b in sorted(triage.items()):
            print(
                f"  FUND {name} — rot per Design, {b['serie']} Läufe in Folge, "
                f"seit {b['seit']} — triagieren, nicht reparieren"
            )
            print(f"       {b['url']}")
        for u in ungeprueft:
            print(f"  ??   {u}")

    rest = f" · ungeprueft:{len(ungeprueft)}" if ungeprueft else ""
    if triage:
        rest += " · rot per Design (Triage): " + "; ".join(
            f"{n} ({b['serie']}x seit {b['seit']})" for n, b in sorted(triage.items())
        )
    if befunde:
        kurz = "; ".join(
            f"{n} ({b['serie']}x seit {b['seit']})" for n, b in sorted(befunde.items())
        )
        print(
            f"RESULT: BEFUND — blinde(r) Melder: {kurz} — ein dauerhaft roter Melder "
            f"meldet nichts mehr (platform#1508){rest}"
        )
        return 0
    if ungeprueft:
        print(
            f"RESULT: UNGEPRUEFT — {len(ungeprueft)} von {len(geplant)} nicht abrufbar, "
            f"in den uebrigen kein dauerhaft roter Melder{rest}"
        )
        return 0
    if triage:
        kurz = "; ".join(
            f"{n} ({b['serie']}x seit {b['seit']})" for n, b in sorted(triage.items())
        )
        print(
            f"RESULT: TRIAGE — kein blinder Melder; rot per Design und damit offener "
            f"Fund: {kurz} — triagieren, nicht reparieren"
        )
        return 0
    print(
        f"RESULT: OK — {len(geplant)} geplante Workflow(s) geprüft, keiner dauerhaft rot"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
