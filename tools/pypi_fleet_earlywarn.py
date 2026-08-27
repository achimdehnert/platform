#!/usr/bin/env python3
"""Frühwarn-Scanner der PyPI-Fleet (#2075 K3, ADR-266) — advisory, read-only.

Meldet Zustände, die HEUTE grün aussehen und MORGEN still brechen, je Paket
mit `strategy: aktiv` aus registry/pypi-fleet.yaml:

  M1 heimat_drift   — Repo liegt nicht unter iilgmbh (Heimat-Regel,
                      ADR-266-Amendment 2026-08-19; Umzug nur via ADR-255-Bahn)
  M2 python_eol     — requires-python-Untergrenze ist EOL oder wird es in <6
                      Monaten (python.org/downloads EOL-Daten, Tabelle unten)
  M3 version_pin    — versionsgekoppelte Interpreter-Strings (`python3.12`
                      o.ä.) in Makefile/Workflows/Dockerfile/compose — die
                      pidof-python3.12-Klasse: bricht still beim Minor-Bump
  M4 reusable_lag   — `_ci-pypi.yml@REF` mit REF != main bzw. shared-ci-Pin
                      hinter dem neuesten shared-ci-Release
  M5 archival_info  — downloads_30d unter Schwelle (nur Info, Trend folgt)
  K4 unattested_release — Release nach ADR-278 (2026-07-24) ohne PyPI-
                      Attestation-Bundle (`pypi.provenance` aus dem Inventar,
                      KONZ-platform-052 V10). `unbekannt` (Netzfehler/Timeout/
                      kein Wheel) ist KEIN Finding, wird aber gezählt.

Advisory-Kontrakt (ADR-266-Amendment / #2075 K3): rc ist IMMER 0, außer mit
`--strict` (für späteres Blocking nach Präzisions-Nachweis). Braucht GH_TOKEN.

    GH_TOKEN=... python3 tools/pypi_fleet_earlywarn.py
    python3 tools/pypi_fleet_earlywarn.py --fleet-file registry/pypi-fleet.yaml
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

PLATFORM_DIR = Path(__file__).resolve().parent.parent
ORGS = ("iilgmbh", "achimdehnert", "ttz-lif", "meiki-lra")
HOME_ORG = "iilgmbh"
DOWNLOAD_FLOOR_30D = 50

# EOL-Daten laut python.org/downloads (Stand 2026-08; bei neuem Minor ergänzen).
PY_EOL = {
    (3, 8): dt.date(2024, 10, 7),
    (3, 9): dt.date(2025, 10, 31),
    (3, 10): dt.date(2026, 10, 31),
    (3, 11): dt.date(2027, 10, 31),
    (3, 12): dt.date(2028, 10, 31),
    (3, 13): dt.date(2029, 10, 31),
}
EOL_WARN_WINDOW = dt.timedelta(days=183)

# Dateien, in denen versionsgekoppelte Strings brechen (M3).
M3_FILES = ("Makefile", "Dockerfile", "docker-compose.yml", "docker-compose.prod.yml")

# ADR-278 Decision-Date: Releases danach ohne Attestation-Bundle sind K4-Findings.
ADR278_DATE = dt.date(2026, 7, 24)


# --------------------------------------------------------------------------
# Pure functions (getestet in tools/tests/test_pypi_fleet_earlywarn.py)
# --------------------------------------------------------------------------


def parse_requires_python(spec: str | None) -> tuple[int, int] | None:
    """Untere Python-Grenze aus requires-python (">=3.10,<4" -> (3,10))."""
    if not spec:
        return None
    m = re.search(r">=\s*3\.(\d+)", spec)
    if m:
        return (3, int(m.group(1)))
    m = re.search(r"\b3\.(\d+)\b", spec)  # "~=3.11" / "==3.12.*"
    return (3, int(m.group(1))) if m else None


def eol_status(lower: tuple[int, int] | None, today: dt.date) -> str | None:
    """None|'eol'|'eol_soon' für die Untergrenze der Python-Spanne."""
    if lower is None or lower not in PY_EOL:
        return None
    eol = PY_EOL[lower]
    if today >= eol:
        return "eol"
    if today >= eol - EOL_WARN_WINDOW:
        return "eol_soon"
    return None


def version_coupled(text: str) -> list[str]:
    """Interpreter-Strings mit hartem Minor ('python3.12', 'bin/python3.11')."""
    return sorted(set(re.findall(r"python3\.\d+", text)))


def parse_reusable_refs(workflow_text: str) -> list[tuple[str, str, str]]:
    """(owner/repo, workflow-file, ref) aller cross-repo reusable-Aufrufe."""
    return [
        (m.group(1), m.group(2), m.group(3))
        for m in re.finditer(
            r"uses:\s*([\w-]+/[\w-]+)/\.github/workflows/([\w.-]+)@(\S+)",
            workflow_text,
        )
    ]


def unattested_release_finding(
    pkg: dict, threshold: dt.date = ADR278_DATE
) -> str | None:
    """K4 unattested_release: Release nach ADR-278 ohne Attestation-Bundle.

    `unbekannt` (Netzfehler/Timeout/kein Wheel — 🌀 Null aus dem eigenen
    Fehlerfall ist keine Abwesenheit) ist bewusst KEIN Finding; der Aufrufer
    zählt es separat ("nicht messbar: N").
    """
    prov = (pkg.get("pypi") or {}).get("provenance") or {}
    if prov.get("status") != "unattested":
        return None
    last_upload = (pkg.get("pypi") or {}).get("last_upload")
    if not last_upload:
        return None
    try:
        upload_date = dt.datetime.fromisoformat(
            last_upload.replace("Z", "+00:00")
        ).date()
    except ValueError:
        return None
    if upload_date <= threshold:
        return None
    return (
        f"K4 unattested_release: {prov.get('version')} ({upload_date.isoformat()}) "
        "ohne Attestation-Bundle seit ADR-278"
    )


# --------------------------------------------------------------------------
# GitHub-API (read-only)
# --------------------------------------------------------------------------


def _api(path: str, token: str, raw: bool = False):
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Authorization", f"Bearer {token}")
    accept = "application/vnd.github.raw+json" if raw else "application/vnd.github+json"
    req.add_header("Accept", accept)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    if raw:
        return body
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return body


def find_org(repo: str, token: str) -> str | None:
    for org in ORGS:
        meta = _api(f"/repos/{org}/{repo}", token)
        # full_name gegen die Anfrage prüfen: GitHub folgt Transfer-Redirects,
        # sonst zählte ein umgezogenes Repo für seine ALTE Org (Heimat-Drift
        # wäre per Konstruktion unsichtbar).
        if (
            isinstance(meta, dict)
            and meta.get("full_name", "").lower() == f"{org}/{repo}".lower()
        ):
            return org
    return None


def semver_key(tag: str) -> tuple[int, ...] | None:
    m = re.fullmatch(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", tag)
    return tuple(int(g or 0) for g in m.groups()) if m else None


_TAG_CACHE: dict[str, str | None] = {}


def latest_tag(owner_repo: str, token: str) -> str | None:
    """Neuester semver-Tag des Repos (Tags, nicht Releases — shared-ci hat
    keine GitHub-Releases). None = nicht auflösbar; der Aufrufer MUSS das
    laut melden, nie still schlucken (Fetch-Fehler ist kein grüner Zustand)."""
    if owner_repo not in _TAG_CACHE:
        tags = _api(f"/repos/{owner_repo}/tags?per_page=100", token)
        best = None
        if isinstance(tags, list):
            keyed = [(semver_key(t.get("name", "")), t.get("name")) for t in tags]
            keyed = [(k, n) for k, n in keyed if k]
            if keyed:
                best = max(keyed)[1]
        _TAG_CACHE[owner_repo] = best
    return _TAG_CACHE[owner_repo]


# --------------------------------------------------------------------------
# Scan
# --------------------------------------------------------------------------


def scan_package(repo: str, org: str, token: str, today: dt.date) -> list[str]:
    findings: list[str] = []
    if org != HOME_ORG:
        findings.append(f"M1 heimat_drift: liegt unter {org}, Heimat ist {HOME_ORG}")

    pyproject = _api(f"/repos/{org}/{repo}/contents/pyproject.toml", token, raw=True)
    if isinstance(pyproject, str):
        m = re.search(r'^\s*requires-python\s*=\s*"([^"]+)"', pyproject, re.M)
        status = eol_status(parse_requires_python(m.group(1) if m else None), today)
        if status == "eol":
            findings.append(f"M2 python_eol: Untergrenze {m.group(1)!r} ist EOL")
        elif status == "eol_soon":
            findings.append(
                f"M2 python_eol: Untergrenze {m.group(1)!r} EOL in <6 Monaten"
            )

    m3_texts: dict[str, str] = {}
    for fname in M3_FILES:
        text = _api(f"/repos/{org}/{repo}/contents/{fname}", token, raw=True)
        if isinstance(text, str):
            m3_texts[fname] = text
    listing = _api(f"/repos/{org}/{repo}/contents/.github/workflows", token)
    wf_names = (
        [e["name"] for e in listing if e.get("name", "").endswith((".yml", ".yaml"))]
        if isinstance(listing, list)
        else []
    )
    for name in wf_names:
        text = _api(
            f"/repos/{org}/{repo}/contents/.github/workflows/{name}", token, raw=True
        )
        if not isinstance(text, str):
            continue
        m3_texts[f".github/workflows/{name}"] = text
        for owner_repo, wf, ref in parse_reusable_refs(text):
            if (
                owner_repo.endswith("/platform")
                and wf == "_ci-pypi.yml"
                and ref != "main"
            ):
                findings.append(
                    f"M4 reusable_lag: {name} pinnt _ci-pypi.yml@{ref} (!= main)"
                )
            elif owner_repo.endswith("/shared-ci") and ref != "main":
                newest = latest_tag(owner_repo, token)
                if newest is None:
                    findings.append(
                        f"M4 nicht prüfbar: {name} pinnt {owner_repo}@{ref}, "
                        "neuester Tag nicht auflösbar"
                    )
                elif semver_key(ref) is not None and semver_key(ref) < semver_key(
                    newest
                ):
                    findings.append(
                        f"M4 reusable_lag: {name} pinnt {owner_repo}/{wf}@{ref} "
                        f"(neuester Tag: {newest})"
                    )
    for fname, text in sorted(m3_texts.items()):
        hits = version_coupled(text)
        if hits:
            findings.append(f"M3 version_pin: {fname} enthält {', '.join(hits)}")
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--fleet-file", type=Path, default=PLATFORM_DIR / "registry" / "pypi-fleet.yaml"
    )
    ap.add_argument("--today", type=dt.date.fromisoformat, default=None)
    ap.add_argument(
        "--strict", action="store_true", help="rc 1 bei Findings (blocking)"
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Findings als JSON-Liste [{repo, org, metric, text}] (Emitter-Input)",
    )
    args = ap.parse_args()
    today = args.today or dt.date.today()

    token = os.environ.get("GH_TOKEN", "")
    if not token:
        print("FEHLER: GH_TOKEN fehlt.", file=sys.stderr)
        return 2

    fleet = yaml.safe_load(args.fleet_file.read_text())
    active = sorted(
        name for name, p in fleet["packages"].items() if p.get("strategy") == "aktiv"
    )
    records: list[dict] = []
    unmeasurable = 0
    if not args.json:
        print(
            f"== Frühwarn-Scan (advisory) — {len(active)} aktiv-Pakete, Stand {today} =="
        )
    for repo in active:
        org = find_org(repo, token)
        if org is None:
            records.append(
                {
                    "repo": repo,
                    "org": None,
                    "metric": "unresolved",
                    "text": "ORG NICHT AUFLÖSBAR (Zugriff/Umbenennung prüfen)",
                }
            )
            continue
        findings = scan_package(repo, org, token, today)
        pkg = fleet["packages"][repo]
        dl = (pkg.get("pypi") or {}).get("downloads_30d")
        if isinstance(dl, int) and dl < DOWNLOAD_FLOOR_30D:
            findings.append(
                f"M5 archival_info: nur {dl} Downloads/30d (<{DOWNLOAD_FLOOR_30D})"
            )
        k4 = unattested_release_finding(pkg)
        if k4:
            findings.append(k4)
        if ((pkg.get("pypi") or {}).get("provenance") or {}).get(
            "status"
        ) == "unbekannt":
            unmeasurable += 1
        for f in findings:
            records.append(
                {"repo": repo, "org": org, "metric": f.split(" ", 1)[0], "text": f}
            )
    if args.json:
        print(json.dumps(records, ensure_ascii=False, indent=1))
    else:
        for r in records:
            print(f"{r['repo']}: {r['text']}")
        print(
            f"== {len(records)} Frühwarn-Findings über {len(active)} Pakete "
            f"(K4 nicht messbar: {unmeasurable}) =="
        )
    return 1 if (args.strict and records) else 0


if __name__ == "__main__":
    sys.exit(main())
