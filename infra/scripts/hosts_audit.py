#!/usr/bin/env python3
"""Hosts Audit — hält infra/hosts.yaml ehrlich und fängt tote Runner-Label-Pins.

Hintergrund: Infra-/Runner-Topologie-Drift war wiederholt Outage- und Merge-Blocker-
Quelle (2026-06-15 Prod-Web-Outage, 2026-06-17 toter `hetzner`-Runner-Pin blockierte
13h alle risk-hub-Merges). Dieser Gate verankert die SoT `infra/hosts.yaml` und prüft,
dass kein Workflow auf ein Runner-Label zeigt, das kein lebender Runner in der SoT trägt.

Nutzung:
    # Alles prüfen (Schema + Frische der SoT):
    python infra/scripts/hosts_audit.py

    # Nur Schema / nur Frische:
    python infra/scripts/hosts_audit.py --check schema
    python infra/scripts/hosts_audit.py --check staleness --max-age-days 120

    # Runner-Label-Audit: jedes runs-on in <dir> gegen Online-Runner der SoT:
    python infra/scripts/hosts_audit.py --check labels --workflows ../risk-hub/.github/workflows

    # Alles inkl. Label-Audit:
    python infra/scripts/hosts_audit.py --check all --workflows .github/workflows

Exit-Codes:
    0 = keine Findings
    1 = Findings (Schema/Frische/tote Labels)
    2 = Bedienfehler (Datei fehlt o.ä.)

Referenz: platform/infra/hosts.yaml (SoT), session-retro Längsschnitt-Gate.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import sys
from pathlib import Path

import yaml

# Labels, die JEDER self-hosted Runner automatisch trägt → kein Eintrag in der SoT nötig.
_AUTO_LABELS = {"self-hosted", "Linux", "X64", "linux", "x64"}
# GitHub-hosted runs-on (keine self-hosted-Prüfung):
_HOSTED_PREFIXES = ("ubuntu", "windows", "macos")
_DEFAULT_MAX_AGE_DAYS = 120


def load_hosts_yaml(path: Path) -> dict:
    if not path.exists():
        print(f"FEHLER: {path} nicht gefunden", file=sys.stderr)
        sys.exit(2)
    return yaml.safe_load(path.read_text()) or {}


def _today() -> _dt.date:
    return _dt.date.today()


def check_schema(data: dict) -> list[str]:
    issues: list[str] = []
    for top in ("hosts", "runners"):
        if top not in data or not isinstance(data[top], dict):
            issues.append(f"schema: Top-Level-Key '{top}' fehlt oder ist kein Mapping")
    hosts = data.get("hosts", {}) or {}
    runners = data.get("runners", {}) or {}

    for name, r in runners.items():
        if not isinstance(r, dict):
            issues.append(f"schema: runner '{name}' ist kein Mapping")
            continue
        if not isinstance(r.get("labels"), list) or not r["labels"]:
            issues.append(f"schema: runner '{name}' hat keine 'labels'-Liste")
        if not r.get("status"):
            issues.append(f"schema: runner '{name}' hat kein 'status'")
        host = r.get("host")
        if host not in (None, "UNKNOWN") and host not in hosts:
            issues.append(f"schema: runner '{name}'.host='{host}' referenziert keinen Host")

    for name, h in hosts.items():
        if not isinstance(h, dict):
            issues.append(f"schema: host '{name}' ist kein Mapping")
            continue
        for rn in h.get("hosts_runners", []) or []:
            if rn not in runners:
                issues.append(f"schema: host '{name}'.hosts_runners enthält unbekannten Runner '{rn}'")
    return issues


def check_staleness(data: dict, max_age_days: int) -> list[str]:
    issues: list[str] = []
    today = _today()
    cutoff = today - _dt.timedelta(days=max_age_days)
    for section in ("hosts", "runners"):
        for name, item in (data.get(section, {}) or {}).items():
            if not isinstance(item, dict):
                continue
            v = item.get("verified")
            if v is False:
                continue  # explizit als unverifiziert markiert (ok, kein Frische-Fail)
            if v is None:
                issues.append(f"staleness: {section}/{name} hat kein 'verified'-Datum")
                continue
            d = v if isinstance(v, _dt.date) else _parse_date(str(v))
            if d is None:
                issues.append(f"staleness: {section}/{name}.verified='{v}' ist kein gültiges Datum")
            elif d < cutoff:
                age = (today - d).days
                issues.append(
                    f"staleness: {section}/{name} zuletzt {d} verifiziert ({age}d alt > {max_age_days}d) "
                    f"— per server_probe.py / gh api gegenprüfen und hosts.yaml aktualisieren"
                )
    return issues


def _parse_date(s: str) -> _dt.date | None:
    try:
        return _dt.date.fromisoformat(s.strip())
    except ValueError:
        return None


def available_label_sets(data: dict) -> list[set[str]]:
    """Label-Mengen aller ONLINE-Runner aus der SoT (gegen die runs-on geprüft wird)."""
    out: list[set[str]] = []
    for name, r in (data.get("runners", {}) or {}).items():
        if str(r.get("status", "")).lower() == "online":
            out.append({str(lbl) for lbl in (r.get("labels") or [])})
    return out


def _parse_runs_on(raw) -> list[set[str]]:
    """runs-on kann String oder Liste sein → eine Menge geforderter Labels."""
    if raw is None:
        return []
    if isinstance(raw, str):
        return [{raw}]
    if isinstance(raw, list):
        return [{str(x) for x in raw}]
    return []


def _iter_runs_on(wf_path: Path) -> list[tuple[str, set[str]]]:
    """(job_id, required-labels) je Job — tolerant geparst (YAML, sonst Regex-Fallback)."""
    results: list[tuple[str, set[str]]] = []
    text = wf_path.read_text()
    try:
        doc = yaml.safe_load(text) or {}
        jobs = doc.get("jobs", {}) or {}
        for job_id, job in jobs.items():
            if isinstance(job, dict):
                for req in _parse_runs_on(job.get("runs-on")):
                    results.append((job_id, req))
        if results:
            return results
    except yaml.YAMLError:
        pass
    # Fallback: rohe runs-on-Zeilen (falls YAML wegen Templating nicht parst)
    for m in re.finditer(r"runs-on:\s*(.+)", text):
        val = m.group(1).strip()
        if val.startswith("["):
            labels = {x.strip().strip("'\"") for x in val.strip("[]").split(",") if x.strip()}
        else:
            labels = {val.strip("'\"")}
        results.append(("?", labels))
    return results


def check_labels(data: dict, workflows_dir: Path) -> list[str]:
    issues: list[str] = []
    if not workflows_dir.exists():
        print(f"FEHLER: workflows-Verzeichnis {workflows_dir} nicht gefunden", file=sys.stderr)
        sys.exit(2)
    avail = available_label_sets(data)
    for wf in sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml")):
        for job_id, req in _iter_runs_on(wf):
            # GitHub-hosted Runner ignorieren
            if any(any(lbl.lower().startswith(p) for p in _HOSTED_PREFIXES) for lbl in req):
                continue
            if "self-hosted" not in {lbl.lower() for lbl in req}:
                continue
            # Nur nicht-automatische Labels müssen von einem Online-Runner gedeckt sein
            needed = {lbl for lbl in req if lbl not in _AUTO_LABELS}
            if not needed:
                continue  # reines self-hosted → ok
            if not any(needed <= a for a in avail):
                issues.append(
                    f"labels: {wf.name} job '{job_id}' verlangt {sorted(req)} — "
                    f"kein ONLINE-Runner in hosts.yaml trägt {sorted(needed)}. "
                    f"Toter Label-Pin → blockiert Merges. Fix: runs-on: self-hosted "
                    f"(siehe Label-Konvention in infra/hosts.yaml)."
                )
    return issues


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check", choices=["schema", "staleness", "labels", "all"], default="all")
    p.add_argument("--hosts", type=Path, default=Path(__file__).resolve().parents[1] / "hosts.yaml")
    p.add_argument("--workflows", type=Path, help="Verzeichnis mit .github/workflows zum Label-Audit")
    p.add_argument("--max-age-days", type=int, default=_DEFAULT_MAX_AGE_DAYS)
    args = p.parse_args()

    data = load_hosts_yaml(args.hosts)
    issues: list[str] = []

    if args.check in ("schema", "all"):
        issues += check_schema(data)
    if args.check in ("staleness", "all"):
        issues += check_staleness(data, args.max_age_days)
    if args.check in ("labels", "all"):
        if args.workflows:
            issues += check_labels(data, args.workflows)
        elif args.check == "labels":
            print("FEHLER: --check labels braucht --workflows <dir>", file=sys.stderr)
            sys.exit(2)

    if issues:
        print(f"❌ hosts_audit: {len(issues)} Finding(s):")
        for i in issues:
            print(f"  - {i}")
        sys.exit(1)
    print(f"✅ hosts_audit ({args.check}): keine Findings (SoT: {args.hosts}).")
    sys.exit(0)


if __name__ == "__main__":
    main()
