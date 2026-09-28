#!/usr/bin/env python3
"""Cold-Start-Wache der PyPI-Fleet (#3575 K1/K2, ADR-266 / #2075 K2-Fortführung).

Macht aus dem einmaligen Cold-Start-Beweis vom 2026-08-19 (19/19 T1a-PASS,
docs/verifications/2026-08-19-adr266-k2-llm-coldstart.md) eine stehende
Garantie — ohne neuen Melder: Ergebnis ist EINE Sektion im EINEN Flotten-
Issue (#968, tools/pypi_fleet_sections.py), Zustand lebt in derselben Sektion.

  K1 Drift-Gate   AGENTS.md jedes aktiv-Pakets wird remote (GitHub-API, kein
                  Klon) gegen das Schema pkg-agents-v1 geprüft
                  (tools/check_agents_md.py). Fehlend/Verstoß = Drift.
  K2 Eval         Der T1a-LLM-Cold-Start-Eval (tools/pypi_coldstart_llm_eval.py,
                  Cerebras vor Groq gem. llm-routing.md) läuft NUR für Pakete, deren Eingaben (AGENTS.md, Makefile,
                  pyproject.toml — Blob-SHAs auf main) sich seit dem letzten
                  bewerteten Stand geändert haben: ereignisgesteuert statt
                  wöchentlich-blind (KONZ-052 Linse 4: jeder Melder, der ohne
                  Anlass feuert, verschlechtert die Kennzahl). Je Lauf ein
                  Budget (--max-evals); Rest bleibt fällig und steht so im Report.
                  Beim Eval wird zusätzlich der Generator gegen die committete
                  AGENTS.md gehalten (gen-drift: Fakten in pyproject/Layout
                  haben sich bewegt, Kontextdatei nicht).

Zustand: `<!-- coldstart-state:{json} -->` innerhalb der Sektion — je Paket
Fingerprint der Eingaben, Ergebnis, Datum, Run-ID. Fehlt der Zustand (Erstlauf,
Sektion gelöscht), ist jedes Paket fällig. `--state-file` ersetzt das Issue für
lokale Läufe und Tests.

Sicherheit (Lotsen-Charta Art. 1): Modell-Ausgabe ist Datenlage — der Eval
führt ausschließlich `make <target>`-Ketten aus (fail-closed, siehe llm_eval).
Advisory: rc 0, solange kein --strict (ADR-266-Amendment 2026-08-19: neue
Checks starten advisory, blocking erst nach Präzisions-Nachweis).

    GH_TOKEN=... [CEREBRAS_API_KEY=...] [GROQ_API_KEY=...] python3 tools/pypi_coldstart_watch.py \\
        [--all] [--max-evals 6] [--no-eval] [--state-file s.json] \\
        [--report-out section.md] [--run-id 123]
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from check_agents_md import check_text  # noqa: E402
from gen_pkg_agents_md import generate  # noqa: E402
from pypi_fleet_earlywarn import PLATFORM_DIR, _api, find_org  # noqa: E402
from pypi_fleet_sections import fetch_issue  # noqa: E402

INPUT_FILES = ("AGENTS.md", "Makefile", "pyproject.toml")
STATE_RE = re.compile(r"<!-- coldstart-state:(\{.*?\}) -->", re.S)
SECTION_NAME = "coldstart"
DEFAULT_MAX_EVALS = 6

# Klassen je Paket — die Wörter tauchen im Report auf, Tests hängen daran.
K1_OK = "konform"
K1_DRIFT = "schema-verstoss"
K1_MISSING = "fehlt"
K2_NEW = "neu"
K2_CHANGED = "geaendert"
K2_CURRENT = "aktuell"


# --------------------------------------------------------------------------
# Reine Logik (getestet)
# --------------------------------------------------------------------------


def fingerprint(shas: dict[str, str | None]) -> str:
    """Stabiler Fingerabdruck der Eingaben — Blob-SHAs, keine Inhalte."""
    return "|".join(f"{f}={shas.get(f) or '-'}" for f in INPUT_FILES)


def k1_status(agents_text: str | None) -> tuple[str, list[str]]:
    if agents_text is None:
        return K1_MISSING, ["AGENTS.md fehlt auf main"]
    problems = check_text(agents_text)
    return (K1_DRIFT, problems) if problems else (K1_OK, [])


def k2_status(state_entry: dict | None, fp: str) -> str:
    if not state_entry or not state_entry.get("fingerprint"):
        return K2_NEW
    return K2_CURRENT if state_entry["fingerprint"] == fp else K2_CHANGED


def parse_state(section_body: str | None) -> dict:
    """Zustand aus der Sektion lesen; kaputt/fehlend = leer (alles fällig)."""
    if not section_body:
        return {}
    m = STATE_RE.search(section_body)
    if not m:
        return {}
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def render_state(state: dict) -> str:
    return f"<!-- coldstart-state:{json.dumps(state, sort_keys=True, ensure_ascii=False)} -->"


def select_for_eval(
    rows: list[dict], max_evals: int, force_all: bool, retry_fail: bool = False
) -> list[dict]:
    """Fällige Pakete in stabiler Reihenfolge, gedeckelt durch das Budget.

    `retry_fail`: auch Pakete, deren letztes Ergebnis kein PASS war — ohne
    Änderung an den Eingaben (z.B. nach einem Fix am Runner selbst).
    """
    due = [
        r
        for r in rows
        if force_all
        or r["k2"] != K2_CURRENT
        or (retry_fail and not str(r.get("last") or "").startswith("PASS"))
    ]
    due.sort(key=lambda r: (r["k2"] != K2_NEW, r["repo"]))  # neu zuerst
    return due[:max_evals]


def render_report(
    rows: list[dict], today: dt.date, evaluated: dict[str, dict], budget_left: int
) -> str:
    n = len(rows)
    k1 = {K1_OK: 0, K1_DRIFT: 0, K1_MISSING: 0}
    k2 = {K2_NEW: 0, K2_CHANGED: 0, K2_CURRENT: 0}
    unresolved = 0
    for r in rows:
        if r.get("unresolved"):
            unresolved += 1
            continue
        k1[r["k1"]] += 1
        k2[r["k2"]] += 1
    passes = sum(1 for v in evaluated.values() if v["result"] == "PASS")
    fails = len(evaluated) - passes
    due_total = k2[K2_NEW] + k2[K2_CHANGED]
    still_due = max(due_total - len(evaluated), 0)
    lines = [
        f"== Cold-Start-Wache (#3575 K1/K2) — {n} aktiv-Pakete, Stand {today} ==",
        (
            f"K1 Kontextdatei: {k1[K1_OK]} konform · {k1[K1_DRIFT]} Schema-Verstoss · "
            f"{k1[K1_MISSING]} fehlt"
            + (
                f" · {unresolved} nicht pruefbar (Org nicht aufloesbar)"
                if unresolved
                else ""
            )
        ),
        (
            f"K2 Eval: {due_total} faellig (neu {k2[K2_NEW]}, geaendert {k2[K2_CHANGED]}), "
            f"{len(evaluated)} bewertet in diesem Lauf ({passes} PASS / {fails} FAIL), "
            f"{still_due} weiter faellig"
            + (" — Budget erschoepft" if still_due and budget_left == 0 else "")
        ),
    ]
    for r in rows:
        if r.get("unresolved"):
            lines.append(f"{r['repo']}: ORG NICHT AUFLÖSBAR (nicht pruefbar)")
            continue
        parts: list[str] = []
        if r["k1"] != K1_OK:
            parts.append(f"K1 {r['k1']}: " + "; ".join(r["k1_problems"]))
        ev = evaluated.get(r["repo"])
        if ev:
            parts.append(
                f"K2 {ev['result']}" + (" · gen-drift" if ev.get("gen_drift") else "")
            )
        elif r["k2"] != K2_CURRENT:
            parts.append(f"K2 {r['k2']} — faellig")
        if parts:
            lines.append(f"{r['repo']}: " + " · ".join(parts))
    if not any(":" in ln for ln in lines[3:]):
        lines.append("(alle Pakete konform und aktuell)")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Remote-Erhebung + Eval (nicht unit-getestet — CI-Dry-Run ist der Beweis)
# --------------------------------------------------------------------------


def inputs_remote(
    org: str, repo: str, token: str
) -> tuple[dict[str, str | None], str | None]:
    """(Blob-SHA je Eingabedatei, AGENTS.md-Text) — je Datei ein API-Call."""
    shas: dict[str, str | None] = {}
    agents: str | None = None
    for f in INPUT_FILES:
        data = _api(f"/repos/{org}/{repo}/contents/{f}", token)
        if isinstance(data, dict) and data.get("sha"):
            shas[f] = data["sha"]
            if f == "AGENTS.md" and data.get("encoding") == "base64":
                agents = base64.b64decode(data.get("content", "")).decode(
                    "utf-8", errors="replace"
                )
        else:
            shas[f] = None
    return shas, agents


def clone(org: str, repo: str, dest: Path) -> bool:
    proc = subprocess.run(
        ["gh", "repo", "clone", f"{org}/{repo}", str(dest), "--", "--depth", "1"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return proc.returncode == 0


def evaluate(org: str, repo: str, workdir: Path) -> dict:
    """Ein Paket: klonen, gen-drift messen, T1a-Eval (nur make-Ketten)."""
    import pypi_coldstart_llm_eval as llm_eval

    dest = workdir / repo
    if not clone(org, repo, dest):
        return {"result": "FAIL-clone", "gen_drift": None}
    gen_drift: bool | None = None
    try:
        committed = (dest / "AGENTS.md").read_text(encoding="utf-8")
        gen_drift = generate(dest).strip() != committed.strip()
    except (OSError, UnicodeDecodeError):
        gen_drift = None
    providers = llm_eval.providers_from_env()
    if not providers:
        return {"result": "SKIP (kein Provider-Key)", "gen_drift": gen_drift}
    try:
        result = llm_eval.eval_package(dest, providers)
    except subprocess.TimeoutExpired:
        result = "FAIL-run (timeout)"
    return {"result": result, "gen_drift": gen_drift}


def load_state(args, token: str, owner: str, repo: str) -> dict:
    if args.state_file:
        if args.state_file.is_file():
            return parse_state(args.state_file.read_text(encoding="utf-8"))
        return {}
    issue = fetch_issue(owner, repo, token) if token else None
    return parse_state((issue or {}).get("body"))


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--fleet-file", type=Path, default=PLATFORM_DIR / "registry" / "pypi-fleet.yaml"
    )
    ap.add_argument(
        "--all", action="store_true", help="alle Pakete bewerten (Erstlauf/Beweis)"
    )
    ap.add_argument(
        "--retry-fail",
        action="store_true",
        help="letztes Ergebnis FAIL erneut bewerten",
    )
    ap.add_argument(
        "--max-evals", type=int, default=DEFAULT_MAX_EVALS, help="Eval-Budget je Lauf"
    )
    ap.add_argument(
        "--no-eval", action="store_true", help="nur K1 + Faelligkeit, kein Klon/LLM"
    )
    ap.add_argument(
        "--state-file", type=Path, default=None, help="Zustand aus/in Datei statt Issue"
    )
    ap.add_argument(
        "--report-out",
        type=Path,
        default=None,
        help="Sektionstext (Report + Zustand) in Datei",
    )
    ap.add_argument("--owner", default="achimdehnert")
    ap.add_argument("--repo", default="platform")
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "lokal"))
    ap.add_argument("--today", type=dt.date.fromisoformat, default=None)
    ap.add_argument("--strict", action="store_true", help="rc 1 bei Drift oder FAIL")
    args = ap.parse_args()
    today = args.today or dt.date.today()

    token = os.environ.get("GH_TOKEN", "")
    if not token:
        print("FEHLER: GH_TOKEN fehlt.", file=sys.stderr)
        return 2

    fleet = yaml.safe_load(args.fleet_file.read_text())
    active = sorted(
        n for n, p in fleet["packages"].items() if p.get("strategy") == "aktiv"
    )
    state = load_state(args, token, args.owner, args.repo)

    rows: list[dict] = []
    for repo in active:
        org = find_org(repo, token)
        if org is None:
            rows.append({"repo": repo, "unresolved": True})
            continue
        shas, agents = inputs_remote(org, repo, token)
        fp = fingerprint(shas)
        k1, problems = k1_status(agents)
        rows.append(
            {
                "repo": repo,
                "org": org,
                "fingerprint": fp,
                "k1": k1,
                "k1_problems": problems,
                "k2": k2_status(state.get(repo), fp),
                "last": (state.get(repo) or {}).get("result"),
            }
        )

    evaluated: dict[str, dict] = {}
    todo = (
        []
        if args.no_eval
        else select_for_eval(
            [r for r in rows if not r.get("unresolved")],
            args.max_evals,
            args.all,
            args.retry_fail,
        )
    )
    budget_left = args.max_evals - len(todo)
    if todo:
        workdir = Path(tempfile.mkdtemp(prefix="coldstart-"))
        try:
            for r in todo:
                print(f"== Eval {r['org']}/{r['repo']} ({r['k2']}) ==", file=sys.stderr)
                ev = evaluate(r["org"], r["repo"], workdir)
                evaluated[r["repo"]] = ev
                print(f"    -> {ev['result']}", file=sys.stderr)
                if ev["result"].startswith(("PASS", "FAIL")):
                    state[r["repo"]] = {
                        "fingerprint": r["fingerprint"],
                        "result": ev["result"],
                        "gen_drift": ev.get("gen_drift"),
                        "date": today.isoformat(),
                        "run_id": str(args.run_id),
                    }
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    report = render_report(rows, today, evaluated, budget_left)
    print(report)
    section = f"```\n{report}\n```\n\n_Letzter Lauf: {args.run_id} ({today})_\n{render_state(state)}\n"
    if args.report_out:
        args.report_out.write_text(section, encoding="utf-8")
    if args.state_file:
        args.state_file.write_text(render_state(state), encoding="utf-8")

    bad = any(r.get("k1") not in (None, K1_OK) for r in rows) or any(
        v["result"] != "PASS" for v in evaluated.values()
    )
    return 1 if (args.strict and bad) else 0


if __name__ == "__main__":
    sys.exit(main())
