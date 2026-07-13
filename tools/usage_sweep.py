#!/usr/bin/env python3
"""usage_sweep.py — Quartalsweiser Nutzungs-Sweep (Entbürokratisierungs-Baustein 38, Issue #1076).

Misst, was tatsächlich benutzt wird, und produziert eine Rückbau-**Kandidatenliste**
(Entscheidung bleibt beim Owner — "ungenutzt" ist messbar, "unnötig" ist ein Urteil).
Bewusst KEIN Standing-Agent, KEINE Auto-Löschung: Kandidaten landen als Tabellen in
einem Issue (Label `usage-sweep`), Rückbau-Aktionen selbst sind separate, kleine PRs
mit Owner-Review.

Vier Messungen (n/m/k-Konvention wie im fleet-drift-report: n=geprüft, m=Kandidat,
k=nicht prüfbar):

1. **Skill-Nutzung** — Skill-Aufrufe aus lokalen `~/.claude/projects/*/*.jsonl`
   (Zeitfenster `--window-days`, Default 180) gegen das Inventar
   `.windsurf/workflows/*.md` abgeglichen. Kandidat = 0 Aufrufe im Fenster.
   Zwei Signalformen werden gezählt (eigene Verifikation, Issue #1076-Umsetzung):
   `tool_use` mit `name=="Skill"` (assistant-seitiger Aufruf) UND
   `<command-name>/<slug></command-name>` in User-Messages (direkt getippter
   Slash-Command). Nur die erste Form zu zählen hätte hochfrequente Skills wie
   `session-start`/`session-ende` fälschlich als 0-Aufrufe gemeldet — beide
   Formen laufen technisch unterschiedliche Pfade durch die Transkripte.

2. **Meter-ohne-Konsequenz** — je scheduled Workflow in `.github/workflows/`
   (Cron-getriggert): erzeugt er Issues (Label-Konvention aus `gh issue create
   --label`/`gh api .../labels -f name=`)? Kandidat = mind. 1 Issue mit diesem
   Label ist älter als 90 Tage, hat 0 Kommentare und ist noch offen (Alarm-
   Müdigkeits-Signal, 🌀 advisory-scanner-Lehre).

3. **Label-Nutzung** — Labels im Repo ohne ein einziges Issue (offen+geschlossen),
   das im Fenster `--window-days` angelegt wurde.

4. **Kill-Gate-Vollzug** — überfällige Kill-Gates aus dem aktuellsten
   `fleet-drift`-Report-Issue, die laut dortiger "Kill-Gate"/"Kill-Kriterium"-
   Sektion >30 Tage ohne Reaktion sind. **Nicht strukturiert abfragbar** (der
   Report ist Freitext, keine registry/kill-gates.yaml existiert) — diese
   Messung ist bewusst best-effort und meldet ehrlich k=nicht-prüfbar, wenn die
   aktuelle Report-Instanz keine solche Sektion enthält, statt Kandidaten zu
   erfinden.

Exit-Code: immer 0 (informativ, kein Gate) — außer 2 bei Aufruffehler
(gh/Netzwerk nicht erreichbar).

Usage:
    # Trockenlauf (kein Issue, nur Report auf stdout):
    python3 tools/usage_sweep.py --dry-run

    # Echter Lauf (erzeugt/aktualisiert [usage-sweep]-Issue):
    python3 tools/usage_sweep.py --report /tmp/usage-sweep-report.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_PROJECTS_DIR = Path.home() / ".claude" / "projects"
_DEFAULT_WORKFLOWS_DIR = _ROOT / ".windsurf" / "workflows"
_DEFAULT_GH_WORKFLOWS_DIR = _ROOT / ".github" / "workflows"
_DEFAULT_REPO = "achimdehnert/platform"

_CAVEAT_FOOTNOTE = """
> **Caveats (fest verdrahtet, gilt für Messung 1):**
> - Nur diese Maschine — Skill-Nutzung auf anderen Rechnern/iPad/claude.ai fließt
>   nicht ein.
> - Windsurf-Ära-Nutzung (vor der CC-first-Migration, ADR-229/230) steckt nicht in
>   den CC-Transkripten.
> - Skills können als Sub-Referenz anderer Skills wirken ("siehe /adr-health"),
>   ohne selbst aufgerufen zu werden — zählt hier NICHT als Nutzung (by design).
> - Zwei Signalformen werden gezählt (`tool_use name=Skill` UND getippte
>   `/slug`-Commands) — eine einzelne Form hätte z.B. `session-start` als
>   ungenutzt gemeldet, obwohl es fast jede Session öffnet.
"""


# ---------------------------------------------------------------------------
# Messung 1: Skill-Nutzung
# ---------------------------------------------------------------------------


def load_skill_inventory(workflows_dir: Path) -> set[str]:
    """Skill-Slugs aus dem Datei-Inventar (Dateiname ohne .md)."""
    if not workflows_dir.is_dir():
        return set()
    return {p.stem for p in workflows_dir.glob("*.md")}


_COMMAND_NAME_RE = re.compile(r"<command-name>/([A-Za-z0-9_-]+)</command-name>")


def iter_jsonl_files(projects_dir: Path) -> list[Path]:
    if not projects_dir.is_dir():
        return []
    return sorted(projects_dir.glob("*/*.jsonl"))


def _parse_timestamp(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def extract_usage_events(obj: dict) -> list[tuple[str, str]]:
    """Ein Transkript-Objekt -> Liste von (skill_slug, signal_form).

    signal_form ist "tool_use" oder "command" — rein informativ (Caveat/Debug).
    """
    events: list[tuple[str, str]] = []
    msg_type = obj.get("type")
    message = obj.get("message") or {}
    content = message.get("content")

    if msg_type == "assistant" and isinstance(content, list):
        for block in content:
            if (
                isinstance(block, dict)
                and block.get("type") == "tool_use"
                and block.get("name") == "Skill"
            ):
                slug = (block.get("input") or {}).get("skill")
                if slug:
                    events.append((slug, "tool_use"))

    elif msg_type == "user":
        text = content if isinstance(content, str) else None
        if text is None and isinstance(content, list):
            text = " ".join(
                b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
            )
        if text:
            for m in _COMMAND_NAME_RE.finditer(text):
                events.append((m.group(1), "command"))

    return events


def compute_skill_usage(
    projects_dir: Path, window_start: datetime
) -> tuple[Counter, Counter]:
    """Läuft alle jsonl-Dateien durch, gibt (usage_counter, source_counter) zurück."""
    usage: Counter = Counter()
    sources: Counter = Counter()
    for path in iter_jsonl_files(projects_dir):
        try:
            lines = path.read_text(errors="ignore").splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = _parse_timestamp(obj.get("timestamp"))
            if ts is None or ts < window_start:
                continue
            for slug, form in extract_usage_events(obj):
                usage[slug] += 1
                sources[form] += 1
    return usage, sources


def skill_candidates(inventory: set[str], usage: Counter) -> list[str]:
    return sorted(slug for slug in inventory if usage.get(slug, 0) == 0)


# ---------------------------------------------------------------------------
# Messung 2: Meter-ohne-Konsequenz
# ---------------------------------------------------------------------------

_SCHEDULE_RE = re.compile(r"^\s*schedule:\s*$", re.MULTILINE)
_LABEL_FLAG_RE = re.compile(r"--label[= ]([A-Za-z0-9_-]+)")
_LABEL_F_NAME_RE = re.compile(r'-f\s+name=["\']?([A-Za-z0-9_-]+)["\']?')


def find_scheduled_workflows(gh_workflows_dir: Path) -> list[Path]:
    if not gh_workflows_dir.is_dir():
        return []
    result = []
    for path in sorted(gh_workflows_dir.glob("*.yml")):
        try:
            text = path.read_text()
        except OSError:
            continue
        if _SCHEDULE_RE.search(text):
            result.append(path)
    return result


def extract_issue_label(workflow_text: str) -> str | None:
    """Erste Label-Erwähnung aus `gh issue create --label X` oder
    `gh api .../labels -f name=X` — Heuristik, kein YAML-Parser (Bash-Steps)."""
    m = _LABEL_FLAG_RE.search(workflow_text)
    if m:
        return m.group(1)
    m = _LABEL_F_NAME_RE.search(workflow_text)
    if m:
        return m.group(1)
    return None


def evaluate_meter_consequence(
    label_by_workflow: dict[str, str],
    issues_by_label: dict[str, list[dict]],
    now: datetime,
    min_age_days: int = 90,
) -> list[dict]:
    """label_by_workflow: {workflow_filename: label}.
    issues_by_label: {label: [{"number":.., "createdAt":.., "comments":.., "state":..}]}.
    Kandidat = Workflow, dessen Label >=1 Issue hat: älter als min_age_days,
    0 Kommentare, noch OPEN.
    """
    candidates = []
    for workflow, label in sorted(label_by_workflow.items()):
        issues = issues_by_label.get(label, [])
        stale = []
        for issue in issues:
            created = _parse_timestamp(issue.get("createdAt"))
            if created is None:
                continue
            age_days = (now - created).days
            if (
                age_days >= min_age_days
                and issue.get("comments", 0) == 0
                and issue.get("state", "").upper() == "OPEN"
            ):
                stale.append(issue["number"])
        if stale:
            candidates.append({"workflow": workflow, "label": label, "stale_issues": stale})
    return candidates


# ---------------------------------------------------------------------------
# Messung 3: Label-Nutzung
# ---------------------------------------------------------------------------


def evaluate_label_usage(
    all_labels: list[str], issues_in_window: list[dict]
) -> list[str]:
    """issues_in_window: [{"labels": [{"name": "..."}]}] (gh --json labels Form)."""
    used: set[str] = set()
    for issue in issues_in_window:
        for label in issue.get("labels", []):
            name = label.get("name") if isinstance(label, dict) else label
            if name:
                used.add(name)
    return sorted(name for name in all_labels if name not in used)


# ---------------------------------------------------------------------------
# Messung 4: Kill-Gate-Vollzug (best-effort, Freitext)
# ---------------------------------------------------------------------------

_KILL_SECTION_RE = re.compile(
    r"(?im)^#{0,4}\s*kill-(?:gate|kriterium)s?\b.*$"
)
_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def evaluate_kill_gates(
    report_body: str | None, now: datetime, min_age_days: int = 30
) -> dict:
    """Best-effort: sucht eine Kill-Gate/Kill-Kriterium-Sektion im Report-Body
    und extrahiert Zeilen mit Datum >min_age_days. Kein strukturiertes Format
    vorhanden -> ehrliches k=nicht-prüfbar statt erfundener Kandidaten."""
    if not report_body:
        return {"checked": False, "reason": "kein aktuelles fleet-drift-Issue gefunden", "candidates": []}

    match = _KILL_SECTION_RE.search(report_body)
    if not match:
        return {
            "checked": False,
            "reason": "kein Kill-Gate/Kill-Kriterium-Abschnitt im aktuellen Report",
            "candidates": [],
        }

    section_start = match.end()
    # Sektion endet an der naechsten Markdown-Ueberschrift gleicher/hoeherer Ebene
    # oder am Textende.
    rest = report_body[section_start:]
    next_heading = re.search(r"(?m)^#{1,4}\s", rest)
    section_text = rest[: next_heading.start()] if next_heading else rest

    candidates = []
    for line in section_text.splitlines():
        dates = _DATE_RE.findall(line)
        if not dates:
            continue
        oldest = min(_parse_timestamp(d + "T00:00:00+00:00") for d in dates)
        if oldest and (now - oldest).days >= min_age_days:
            candidates.append(line.strip())
    return {"checked": True, "reason": None, "candidates": candidates}


# ---------------------------------------------------------------------------
# gh-CLI I/O (nicht pur, nicht unit-getestet — Integrationsschicht)
# ---------------------------------------------------------------------------


def _gh_json(args: list[str]):
    result = subprocess.run(
        ["gh", *args], capture_output=True, text=True, check=True, timeout=60
    )
    return json.loads(result.stdout) if result.stdout.strip() else None


def fetch_all_labels(repo: str) -> list[str]:
    data = _gh_json(["label", "list", "--repo", repo, "--limit", "300", "--json", "name"])
    return [row["name"] for row in (data or [])]


def fetch_issues_created_since(repo: str, since: datetime) -> list[dict]:
    date_str = since.strftime("%Y-%m-%d")
    data = _gh_json(
        [
            "issue", "list", "--repo", repo, "--state", "all",
            "--search", f"created:>={date_str}",
            "--json", "number,labels", "--limit", "1000",
        ]
    )
    return data or []


def fetch_issues_by_label(repo: str, label: str) -> list[dict]:
    data = _gh_json(
        [
            "issue", "list", "--repo", repo, "--state", "all", "--label", label,
            "--json", "number,createdAt,comments,state", "--limit", "300",
        ]
    )
    return data or []


def fetch_latest_fleet_drift_body(repo: str) -> str | None:
    data = _gh_json(
        [
            "issue", "list", "--repo", repo, "--label", "fleet-drift", "--state", "all",
            "--json", "number,body,updatedAt", "--limit", "5",
        ]
    )
    if not data:
        return None
    data.sort(key=lambda row: row.get("updatedAt", ""), reverse=True)
    return data[0].get("body")


def ensure_label(repo: str, name: str, color: str, description: str) -> None:
    subprocess.run(
        [
            "gh", "api", f"repos/{repo}/labels",
            "-f", f"name={name}", "-f", f"color={color}", "-f", f"description={description}",
        ],
        capture_output=True, text=True, timeout=30,
    )  # Fehler (Label existiert bereits) bewusst ignoriert


def create_or_comment_issue(repo: str, title: str, label: str, body: str) -> str:
    existing = _gh_json(
        ["issue", "list", "--repo", repo, "--label", label, "--state", "open", "--json", "number"]
    )
    current_quarter_open = next(
        (row for row in (existing or []) if title.split(" ")[-1] in _issue_title(repo, row["number"])),
        None,
    ) if existing else None
    if current_quarter_open:
        number = current_quarter_open["number"]
        subprocess.run(
            ["gh", "issue", "comment", str(number), "--repo", repo, "--body", body],
            check=True, timeout=30,
        )
        return f"Kommentar an bestehendes Issue #{number}"
    result = subprocess.run(
        [
            "gh", "issue", "create", "--repo", repo, "--title", title,
            "--label", label, "--body", body,
        ],
        capture_output=True, text=True, check=True, timeout=30,
    )
    return result.stdout.strip()


def _issue_title(repo: str, number: int) -> str:
    data = _gh_json(["issue", "view", str(number), "--repo", repo, "--json", "title"])
    return (data or {}).get("title", "")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def current_quarter_label(now: datetime) -> str:
    q = (now.month - 1) // 3 + 1
    return f"{now.year}-Q{q}"


def render_report(
    now: datetime,
    window_days: int,
    skill_result: dict,
    meter_candidates: list[dict],
    label_candidates: list[str],
    kill_gate_result: dict,
) -> str:
    lines = [f"## Usage-Sweep — {current_quarter_label(now)} ({now.strftime('%Y-%m-%d')})", ""]

    lines.append(f"### 1. Skill-Nutzung (Fenster: {window_days} Tage)")
    n = skill_result["inventory_size"]
    m = len(skill_result["candidates"])
    lines.append(f"n={n} Skills geprüft, m={m} Kandidaten (0 Aufrufe im Fenster), k=0 nicht prüfbar")
    lines.append("")
    if skill_result["candidates"]:
        lines.append("| Kandidat | Evidenz |")
        lines.append("|---|---|")
        for slug in skill_result["candidates"]:
            lines.append(f"| `{slug}` | 0 Aufrufe (tool_use + command) in {window_days} Tagen |")
    else:
        lines.append("Keine Kandidaten.")
    lines.append(_CAVEAT_FOOTNOTE)

    lines.append("### 2. Meter-ohne-Konsequenz (>=90 Tage alt, 0 Kommentare, offen)")
    n2 = skill_result.get("scheduled_workflow_count", 0)
    m2 = len(meter_candidates)
    lines.append(f"n={n2} scheduled Workflows geprüft, m={m2} Kandidaten, k=0 nicht prüfbar")
    lines.append("")
    if meter_candidates:
        lines.append("| Workflow | Label | Stale-Issues |")
        lines.append("|---|---|---|")
        for c in meter_candidates:
            issue_refs = ", ".join(f"#{n}" for n in c["stale_issues"])
            lines.append(f"| `{c['workflow']}` | `{c['label']}` | {issue_refs} |")
    else:
        lines.append("Keine Kandidaten.")
    lines.append("")

    lines.append(f"### 3. Label-Nutzung (0 Issues seit {window_days} Tagen)")
    lines.append(f"m={len(label_candidates)} Kandidaten")
    lines.append("")
    if label_candidates:
        lines.append("| Kandidat |")
        lines.append("|---|")
        for name in label_candidates:
            lines.append(f"| `{name}` |")
    else:
        lines.append("Keine Kandidaten.")
    lines.append("")

    lines.append("### 4. Kill-Gate-Vollzug (fleet-drift-Report, >=30 Tage ohne Reaktion)")
    if not kill_gate_result["checked"]:
        lines.append(f"k=1 nicht prüfbar: {kill_gate_result['reason']}")
    else:
        m4 = len(kill_gate_result["candidates"])
        lines.append(f"m={m4} Kandidaten")
        lines.append("")
        if kill_gate_result["candidates"]:
            for line in kill_gate_result["candidates"]:
                lines.append(f"- {line}")
        else:
            lines.append("Keine Kandidaten.")
    lines.append("")

    lines.append("---")
    lines.append(
        "**Kill-Kriterium (Issue #1076):** Führen zwei aufeinanderfolgende Sweeps zu "
        "keinem einzigen vollzogenen Rückbau, wird dieser Sweep eingestellt."
    )
    lines.append("_Auto-erzeugt von `tools/usage_sweep.py`._")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--window-days", type=int, default=180, help="Zeitfenster für Skill-/Label-Nutzung (Default 180)")
    parser.add_argument("--dry-run", action="store_true", help="Nur Report drucken, kein Issue erzeugen")
    parser.add_argument("--report", help="Markdown-Report zusätzlich in Datei schreiben")
    parser.add_argument("--repo", default=_DEFAULT_REPO, help=f"GitHub-Repo (Default {_DEFAULT_REPO})")
    parser.add_argument("--projects-dir", default=str(_DEFAULT_PROJECTS_DIR), help="Wurzel der CC-Transkripte")
    parser.add_argument("--workflows-dir", default=str(_DEFAULT_WORKFLOWS_DIR), help="Skill-Inventar-Verzeichnis")
    parser.add_argument("--gh-workflows-dir", default=str(_DEFAULT_GH_WORKFLOWS_DIR), help="CI-Workflow-Verzeichnis")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=args.window_days)

    # Messung 1
    inventory = load_skill_inventory(Path(args.workflows_dir))
    usage, _sources = compute_skill_usage(Path(args.projects_dir), window_start)
    candidates1 = skill_candidates(inventory, usage)

    scheduled = find_scheduled_workflows(Path(args.gh_workflows_dir))

    try:
        # Messung 2
        label_by_workflow: dict[str, str] = {}
        for path in scheduled:
            label = extract_issue_label(path.read_text())
            if label:
                label_by_workflow[path.name] = label
        issues_by_label = {
            label: fetch_issues_by_label(args.repo, label)
            for label in sorted(set(label_by_workflow.values()))
        }
        meter_candidates = evaluate_meter_consequence(label_by_workflow, issues_by_label, now)

        # Messung 3
        all_labels = fetch_all_labels(args.repo)
        issues_in_window = fetch_issues_created_since(args.repo, window_start)
        label_candidates = evaluate_label_usage(all_labels, issues_in_window)

        # Messung 4
        report_body = fetch_latest_fleet_drift_body(args.repo)
        kill_gate_result = evaluate_kill_gates(report_body, now)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        print(f"❌ gh-Aufruf fehlgeschlagen: {exc}", file=sys.stderr)
        return 2

    skill_result = {
        "inventory_size": len(inventory),
        "candidates": candidates1,
        "scheduled_workflow_count": len(scheduled),
    }

    report = render_report(now, args.window_days, skill_result, meter_candidates, label_candidates, kill_gate_result)
    print(report)
    if args.report:
        Path(args.report).write_text(report)

    if args.dry_run:
        print("\n[--dry-run] Kein Issue erzeugt.", file=sys.stderr)
        return 0

    ensure_label(args.repo, "usage-sweep", "0E8A16", "Quartals-Nutzungs-Sweep (Entbürokratisierung, lokal ausgeführt)")
    title = f"[usage-sweep] Rückbau-Kandidaten {current_quarter_label(now)}"
    outcome = create_or_comment_issue(args.repo, title, "usage-sweep", report)
    print(outcome, file=sys.stderr)

    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as fh:
            fh.write(f"candidates={len(candidates1) + len(meter_candidates) + len(label_candidates)}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
