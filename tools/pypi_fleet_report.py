#!/usr/bin/env python3
"""Befund-Report je Paket der PyPI-Flotte (#2591 K2, ADR-266 / KONZ-052).

Eine Zeile pro Paket, jede Zelle mit Beleg (URL/Run/Commit) — keine Zelle ohne
Quelle. Quellen, alle bereits vorhanden, hier nur zusammengeführt:

  registry/pypi-fleet.yaml        PyPI-Version, pyproject-Version, Provenance,
                                  Inventar-Findings (tools/pypi_fleet_inventory.py)
  earlywarn JSON (--earlywarn)    Frühwarn-Metriken je Paket (tools/pypi_fleet_earlywarn.py --json)
  coldstart results.tsv (--coldstart)  make setup && make test in frischem Klon
                                  (tools/pypi_coldstart_baseline.sh); Commit aus dem Klon
  GitHub-API                      neuester Tag, shared-ci-Pin je Workflow, letzter
                                  push-Lauf auf main (Conclusion + Run-URL)

    GH_TOKEN=... python3 tools/pypi_fleet_report.py \\
        --earlywarn earlywarn.json --coldstart <COLDSTART_BASE> \\
        --out docs/verifications/<datum>-adr266-k2-befund.md

Design: stdlib+yaml, read-only, Owner über tools/registry_api.owner() (nie geraten),
API-Helfer aus tools/pypi_fleet_earlywarn.py wiederverwendet statt dupliziert.
Nicht auflösbare Werte stehen als `n/a (Grund)` in der Zelle — ein Fetch-Fehler
ist kein grüner Zustand.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

TOOLS_DIR = Path(__file__).resolve().parent
PLATFORM_DIR = TOOLS_DIR.parent
FLEET_FILE = PLATFORM_DIR / "registry" / "pypi-fleet.yaml"

sys.path.insert(0, str(TOOLS_DIR))
import registry_api  # noqa: E402
from pypi_fleet_earlywarn import (  # noqa: E402
    _api,
    lag_is_nominal,
    latest_tag,
    parse_reusable_refs,
    semver_key,
    workflow_file_at,
)

GH = "https://github.com"
PYPI = "https://pypi.org/project"


# --------------------------------------------------------------------------
# Pure Helfer (getestet in tools/tests/test_pypi_fleet_report.py)
# --------------------------------------------------------------------------


def version_state(pypi_version: str | None, tag: str | None) -> str:
    """gleich | drift | n/a — Tag `v0.14.0` und PyPI `0.14.0` gelten als gleich."""
    if not pypi_version or not tag:
        return "n/a"
    return "gleich" if semver_key(tag) == semver_key(pypi_version) else "drift"


def pin_state(ref: str | None, newest: str | None, nominal: bool | None = None) -> str:
    """aktuell | lag | lag nominal | main | n/a für einen shared-ci-Pin gegen den
    neuesten Tag. `nominal=True` = gepinnte Datei identisch (earlywarn M4-Semantik
    seit 2026-09-02): hinter dem Tag, aber ohne Verhaltensunterschied."""
    if ref is None:
        return "n/a"
    if ref == "main":
        return "main"
    if newest is None or semver_key(ref) is None:
        return "n/a"
    if semver_key(ref) >= semver_key(newest):
        return "aktuell"
    return "lag nominal" if nominal is True else "lag"


def parse_coldstart_tsv(text: str) -> dict[str, dict[str, str]]:
    """results.tsv → {repo: {slug, entry, setup, tests, dauer}} (letzte Zeile gewinnt)."""
    out: dict[str, dict[str, str]] = {}
    for row in csv.reader(text.splitlines(), delimiter="\t"):
        if len(row) < 5:
            continue
        slug, entry, setup, tests, dauer = row[:5]
        out[slug.split("/")[-1]] = {
            "slug": slug,
            "entry": entry,
            "setup": setup,
            "tests": tests,
            "dauer": dauer,
        }
    return out


def coldstart_verdict(row: dict[str, str] | None) -> str:
    """bestanden | fehlgeschlagen | n/a — Kontrakt aus pypi_coldstart_baseline.sh."""
    if not row:
        return "n/a"
    if row["entry"] != "none" and row["setup"] == "ok" and row["tests"] == "ok":
        return "bestanden"
    return "fehlgeschlagen"


def earlywarn_by_repo(findings: list[dict]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for f in findings:
        out.setdefault(f["repo"], []).append(f["metric"])
    return {k: sorted(v) for k, v in out.items()}


# --------------------------------------------------------------------------
# GitHub-Fakten (read-only)
# --------------------------------------------------------------------------


def shared_ci_pins(
    owner_repo: str, token: str
) -> list[tuple[str, str, str, bool | None]]:
    """(workflow-datei, ref, neuester Tag, nominal) je shared-ci-Aufruf im Repo;
    nominal = gepinnte Datei bei ref und neuestem Tag identisch (None = nicht prüfbar)."""
    listing = _api(f"/repos/{owner_repo}/contents/.github/workflows", token)
    if not isinstance(listing, list):
        return []
    pins = []
    for entry in listing:
        name = entry.get("name", "")
        if not name.endswith((".yml", ".yaml")):
            continue
        text = _api(
            f"/repos/{owner_repo}/contents/.github/workflows/{name}", token, raw=True
        )
        if not isinstance(text, str):
            continue
        for src_repo, wf, ref in parse_reusable_refs(text):
            if src_repo.endswith("/shared-ci"):
                newest = latest_tag(src_repo, token)
                nominal = None
                if (
                    newest
                    and ref != "main"
                    and semver_key(ref)
                    and semver_key(ref) < semver_key(newest)
                ):
                    nominal = lag_is_nominal(
                        src_repo,
                        wf,
                        ref,
                        newest,
                        lambda o, f, r: workflow_file_at(o, f, r, token),
                    )
                pins.append((name, ref, newest, nominal))
    return pins


def last_main_run(owner_repo: str, token: str) -> dict | None:
    data = _api(
        f"/repos/{owner_repo}/actions/runs?branch=main&event=push&status=completed&per_page=1",
        token,
    )
    runs = (data or {}).get("workflow_runs") if isinstance(data, dict) else None
    return runs[0] if runs else None


def coldstart_commit(base: Path, repo: str) -> str | None:
    d = base / repo
    if not (d / ".git").exists():
        return None
    res = subprocess.run(
        ["git", "-C", str(d), "rev-parse", "HEAD"], capture_output=True, text=True
    )
    return res.stdout.strip() if res.returncode == 0 else None


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def build_rows(
    packages: dict,
    token: str,
    earlywarn: dict[str, list[str]],
    coldstart: dict[str, dict[str, str]],
    coldstart_base: Path | None,
) -> list[dict]:
    rows = []
    for repo, pkg in sorted(packages.items()):
        owner = registry_api.owner(repo) or "?"
        owner_repo = f"{owner}/{repo}"
        dist = pkg.get("dist_name") or repo
        pypi = pkg.get("pypi") or {}
        prov = pypi.get("provenance") or {}
        tag = latest_tag(owner_repo, token)
        pins = shared_ci_pins(owner_repo, token)
        run = last_main_run(owner_repo, token)
        cs = coldstart.get(repo)
        sha = coldstart_commit(coldstart_base, repo) if coldstart_base else None
        rows.append(
            {
                "repo": repo,
                "owner_repo": owner_repo,
                "strategy": pkg.get("strategy") or "?",
                "dist": dist,
                "pypi_version": pypi.get("version"),
                "pyproject_version": pkg.get("pyproject_version"),
                "tag": tag,
                "version_state": version_state(pypi.get("version"), tag),
                "provenance": prov.get("status", "n/a")
                if pypi
                else "n/a (nicht auf PyPI)",
                "pins": pins,
                "run": run,
                "coldstart": cs,
                "coldstart_verdict": coldstart_verdict(cs),
                "coldstart_sha": sha,
                "inventory_findings": pkg.get("findings") or [],
                "earlywarn": earlywarn.get(repo, []),
            }
        )
    return rows


def _pin_cell(row: dict) -> str:
    if not row["pins"]:
        return "n/a (kein shared-ci-Aufruf)"
    parts = []
    for wf, ref, newest, nominal in row["pins"]:
        state = pin_state(ref, newest, nominal)
        url = f"{GH}/{row['owner_repo']}/blob/main/.github/workflows/{wf}"
        parts.append(
            f"[{ref}]({url}) {state}" + (f" (neu: {newest})" if state == "lag" else "")
        )
    return "<br>".join(parts)


def _ci_cell(row: dict) -> str:
    run = row["run"]
    if not run:
        return "n/a (kein push-Lauf auf main)"
    date = (run.get("run_started_at") or run.get("created_at") or "")[:10]
    return f"[{run.get('conclusion')}]({run.get('html_url')}) {date}"


def _coldstart_cell(row: dict) -> str:
    cs, sha = row["coldstart"], row["coldstart_sha"]
    if not cs:
        return "n/a (nicht gelaufen)"
    label = f"{row['coldstart_verdict']} ({cs['entry']}, setup={cs['setup']}, tests={cs['tests']}, {cs['dauer']})"
    if sha:
        return f"[{label}]({GH}/{row['owner_repo']}/commit/{sha})"
    return label


def _version_cell(row: dict) -> str:
    v, tag = row["pypi_version"], row["tag"]
    v_txt = f"[{v}]({PYPI}/{row['dist']}/{v}/)" if v else "n/a (nicht auf PyPI)"
    t_txt = (
        f"[{tag}]({GH}/{row['owner_repo']}/releases/tag/{tag})"
        if tag
        else "n/a (kein Tag)"
    )
    return f"{v_txt} / {t_txt} → {row['version_state']}"


def _prov_cell(row: dict) -> str:
    v = row["pypi_version"]
    if v:
        return f"[{row['provenance']}]({PYPI}/{row['dist']}/{v}/#files)"
    return row["provenance"]


def render(rows: list[dict], generated_at: str, sources: dict[str, str]) -> str:
    n = len(rows)
    counts = {
        "attested": sum(r["provenance"] == "attested" for r in rows),
        "unattested": sum(r["provenance"] == "unattested" for r in rows),
        "drift": sum(r["version_state"] == "drift" for r in rows),
        "lag": sum(
            any(pin_state(ref, nw, nom) == "lag" for _, ref, nw, nom in r["pins"])
            for r in rows
        ),
        "lag_nominal": sum(
            any(
                pin_state(ref, nw, nom) == "lag nominal"
                for _, ref, nw, nom in r["pins"]
            )
            for r in rows
        ),
        "ci_red": sum(
            bool(r["run"]) and r["run"].get("conclusion") != "success" for r in rows
        ),
        "cs_pass": sum(r["coldstart_verdict"] == "bestanden" for r in rows),
        "cs_fail": sum(r["coldstart_verdict"] == "fehlgeschlagen" for r in rows),
        "cs_na": sum(r["coldstart_verdict"] == "n/a" for r in rows),
        "ew": sum(len(r["earlywarn"]) for r in rows),
    }
    out = [
        f"# ADR-266 / #2591 K2 — Befund je Paket der PyPI-Flotte ({generated_at[:10]})",
        "",
        f"Generiert {generated_at} von `tools/pypi_fleet_report.py`; {n} Pakete aus",
        "`registry/pypi-fleet.yaml`. Jede Zelle trägt ihren Beleg als Link (PyPI-Release,",
        "Tag, Workflow-Datei, Actions-Run, Commit des Cold-Start-Klons). `n/a (Grund)` =",
        "nicht auflösbar, kein grüner Zustand.",
        "",
        "## Quellen",
        "",
        *[f"- {k}: {v}" for k, v in sources.items()],
        "",
        "## Summe",
        "",
        "| Kennzahl | Wert |",
        "|---|---|",
        f"| Pakete | {n} |",
        f"| Provenance attested / unattested | {counts['attested']} / {counts['unattested']} |",
        f"| PyPI-Version ≠ neuester Tag | {counts['drift']} |",
        f"| shared-ci-Pin hinter neuestem Tag, Datei geändert | {counts['lag']} |",
        f"| shared-ci-Pin hinter neuestem Tag, Datei identisch (nominal) | {counts['lag_nominal']} |",
        f"| letzter push-Lauf auf main nicht success | {counts['ci_red']} |",
        f"| Cold-Start bestanden / fehlgeschlagen / n/a | {counts['cs_pass']} / {counts['cs_fail']} / {counts['cs_na']} |",
        f"| Earlywarn-Findings gesamt | {counts['ew']} |",
        "",
        "## Befund je Paket",
        "",
        "| Paket | Strategie | PyPI-Version / Tag | Provenance | shared-ci-Pin | CI main | Cold-Start | Findings |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        findings = ", ".join(r["inventory_findings"] + r["earlywarn"]) or "—"
        out.append(
            f"| [{r['owner_repo']}]({GH}/{r['owner_repo']}) | {r['strategy']} | {_version_cell(r)} "
            f"| {_prov_cell(r)} | {_pin_cell(r)} | {_ci_cell(r)} | {_coldstart_cell(r)} | {findings} |"
        )
    out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fleet-file", type=Path, default=FLEET_FILE)
    ap.add_argument(
        "--earlywarn", type=Path, help="JSON aus pypi_fleet_earlywarn.py --json"
    )
    ap.add_argument(
        "--coldstart", type=Path, help="COLDSTART_BASE mit results.tsv + Klonen"
    )
    ap.add_argument(
        "--anhang",
        type=Path,
        help="Markdown-Datei, die als Abschnitt 'Lesart' unter den Report gehängt wird",
    )
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    token = os.environ.get("GH_TOKEN", "")
    if not token:
        print("FEHLER: GH_TOKEN im Env nötig (Tags, Workflows, Runs).", file=sys.stderr)
        return 2

    doc = yaml.safe_load(args.fleet_file.read_text(encoding="utf-8"))
    packages = doc.get("packages") or {}
    sources = {
        "Inventar": f"`{args.fleet_file.relative_to(PLATFORM_DIR) if args.fleet_file.is_relative_to(PLATFORM_DIR) else args.fleet_file}` "
        f"(generated_at {doc.get('_meta', {}).get('generated_at')})",
    }
    earlywarn: dict[str, list[str]] = {}
    if args.earlywarn:
        earlywarn = earlywarn_by_repo(
            json.loads(args.earlywarn.read_text(encoding="utf-8"))
        )
        sources["Earlywarn"] = (
            f"`tools/pypi_fleet_earlywarn.py --json` ({sum(map(len, earlywarn.values()))} Findings)"
        )
    coldstart: dict[str, dict[str, str]] = {}
    if args.coldstart:
        tsv = args.coldstart / "results.tsv"
        if tsv.exists():
            coldstart = parse_coldstart_tsv(tsv.read_text(encoding="utf-8"))
        sources["Cold-Start"] = (
            f"`tools/pypi_coldstart_baseline.sh` ({len(coldstart)} Ergebnisse; Commit je Zeile verlinkt)"
        )
    sources["GitHub"] = (
        "Tags, Workflow-Dateien, letzter push-Lauf auf main (API, read-only)"
    )

    rows = build_rows(packages, token, earlywarn, coldstart, args.coldstart)
    generated_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    text = render(rows, generated_at, sources)
    if args.anhang:
        text += (
            "\n## Lesart\n\n" + args.anhang.read_text(encoding="utf-8").rstrip() + "\n"
        )
    args.out.write_text(text, encoding="utf-8")
    print(f"→ {args.out} ({len(rows)} Pakete)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
