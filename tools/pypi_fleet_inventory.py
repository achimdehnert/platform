#!/usr/bin/env python3
"""PyPI-Fleet-Inventar (ADR-266 Stufe 1) — deterministischer Ground-Truth-Scanner.

Erzeugt registry/pypi-fleet.yaml: den maschinenlesbaren Zustand aller Repos,
die als PyPI-Paket dienen (Publisher, Auth-Modus, Registry-Abgleich, PyPI-Live-
Stand, Findings, Owner-Aktionen). Dieses File ist der Aufsetzpunkt für jede
Folge-Session/-Agent des PyPI-Programms — NICHT von Hand editieren, sondern
regenerieren:

    python3 tools/pypi_fleet_inventory.py                 # scan + schreiben
    python3 tools/pypi_fleet_inventory.py --offline       # ohne PyPI-API
    python3 tools/pypi_fleet_inventory.py --check         # nur Findings, rc!=0 bei neuen

Bewusst NICHT hier: Workflow-Run-Historie und PyPI-Trusted-Publisher-Bindings
(nicht headless prüfbar) — solche Fakten stehen als `owner_actions` im Output.
Design-Regeln: stdlib+yaml only, read-only gegen die Flotte, Registry-Zugriff
nur über tools/registry_api.py (ADR-234 §11.1).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

TOOLS_DIR = Path(__file__).resolve().parent
PLATFORM_DIR = TOOLS_DIR.parent  # auch in Session-Worktrees korrekt (= dieser Checkout)
# Fleet liegt IMMER unter $GITHUB_DIR bzw. ~/github — NICHT relativ zu diesem File
# ableiten: in einem Session-Worktree (ADR-233) wäre parent der Worktree-Container.
GITHUB_DIR = Path(
    __import__("os").environ.get("GITHUB_DIR", str(Path.home() / "github"))
)
FLEET_FILE = PLATFORM_DIR / "registry" / "pypi-fleet.yaml"

sys.path.insert(0, str(TOOLS_DIR))
import registry_api  # noqa: E402


# --------------------------------------------------------------------------
# Klassifikation (pure functions — getestet in tools/tests/)
# --------------------------------------------------------------------------


def classify_auth(workflow_text: str) -> str:
    """Auth-Modus eines Publish-Workflows: oidc | token | hybrid | unknown.

    oidc   = id-token: write vorhanden, keine Token-Referenz
    token  = Token-Referenz (PYPI_API_TOKEN/TWINE_PASSWORD/password:), kein id-token
    hybrid = beides (typisch: ein Job OIDC, ein Alt-Job mit Token)
    """
    has_oidc = bool(re.search(r"id-token:\s*write", workflow_text))
    has_token = bool(
        re.search(r"PYPI_API_TOKEN|TWINE_PASSWORD|TEST_PYPI_API_TOKEN", workflow_text)
    )
    if has_oidc and has_token:
        return "hybrid"
    if has_oidc:
        return "oidc"
    if has_token:
        return "token"
    return "unknown"


def uses_reusable(workflow_text: str) -> bool:
    """Nutzt der Workflow das ADR-226-Reusable _ci-pypi.yml?"""
    return "_ci-pypi.yml@" in workflow_text


def parse_remote_publisher(workflow_text: str) -> dict:
    """Extrahiert aus einem platform publish-*.yml, WAS er publiziert.

    Remote-Checkout (repository: org/repo) ⇒ platform ist Remote-Publisher
    für ein fremdes Repo. working-directory packages/<x> ⇒ platform publiziert
    ein Subtree-Paket; existiert der Pfad nicht mehr, ist der Workflow tot.
    """
    out: dict = {}
    m = re.search(r"^\s*repository:\s*(\S+)", workflow_text, re.MULTILINE)
    if m:
        out["remote_repo"] = m.group(1)
    dirs = sorted(
        set(
            re.findall(
                r"(?:working-directory|path):\s*(packages/[\w.-]+)", workflow_text
            )
        )
    )
    if dirs:
        out["package_dirs"] = [d.rstrip("/").removesuffix("/dist") for d in dirs]
    return out


def pyproject_meta_text(text: str | None) -> dict:
    """dist-Name + Version aus pyproject.toml-Inhalt (regex: py3.10-kompatibel)."""
    if not text:
        return {}
    meta = {}
    m = re.search(r'^\s*name\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if m:
        meta["dist_name"] = m.group(1)
    m = re.search(r'^\s*version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if m:
        meta["version"] = m.group(1)
    return meta


# --------------------------------------------------------------------------
# Git-Ground-Truth: IMMER origin/main lesen, nie den Working-Tree.
# Blindfleck-Realfall 2026-07-04: lokale Klone waren Tage/Wochen stale →
# Inventar meldete 3 „ungegatete Publisher", die auf origin/main längst
# gefixt/entfernt waren. Fallback auf Working-Tree nur, wenn kein
# origin/main existiert (z. B. frischer Shallow-Clone im CI, dort ist der
# Working-Tree per Konstruktion frisch).
# --------------------------------------------------------------------------


def _git(repo_dir: Path, *args: str) -> str | None:
    res = subprocess.run(
        ["git", "-C", str(repo_dir), *args], capture_output=True, text=True
    )
    return res.stdout if res.returncode == 0 else None


def repo_read(repo_dir: Path, rel: str) -> str | None:
    """Dateiinhalt von origin/main; Fallback Working-Tree (CI-Shallow-Clone)."""
    out = _git(repo_dir, "show", f"origin/main:{rel}")
    if out is not None:
        return out
    p = repo_dir / rel
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else None


def repo_ls(repo_dir: Path, prefix: str) -> list[str]:
    """Pfade unter prefix auf origin/main; Fallback Working-Tree."""
    out = _git(repo_dir, "ls-tree", "-r", "--name-only", "origin/main", prefix)
    if out is not None:
        return sorted(line for line in out.splitlines() if line.strip())
    base = repo_dir / prefix
    if not base.is_dir():
        return []
    return sorted(str(p.relative_to(repo_dir)) for p in base.rglob("*") if p.is_file())


def registry_packages() -> dict[str, str]:
    """repo -> pypi-Name für alle Registry-Einträge mit pypi-Feld (SSoT canonical).

    flat() liefert {"server": ..., "repos": {name: {type, pypi, ...}}}.
    """
    out = {}
    for name, entry in registry_api.flat().get("repos", {}).items():
        pypi = (entry or {}).get("pypi")
        if pypi:
            out[name] = pypi
    return out


def registry_strategies() -> dict[str, str]:
    """repo -> pypi_strategy (aktiv|einfrieren|archivieren-kandidat, ADR-266
    Amendment 2026-08-19). Fehlt das Feld, ist das ein Finding (s. Aufrufer)."""
    out = {}
    for name, entry in registry_api.flat().get("repos", {}).items():
        strat = (entry or {}).get("pypi_strategy")
        if strat:
            out[name] = strat
    return out


def scan_repo(repo_dir: Path, fetch: bool = True) -> dict | None:
    """Publish-Fakten eines Repos auf origin/main (None, wenn kein Publish-Bezug)."""
    if fetch:
        _git(repo_dir, "fetch", "origin", "--quiet")
    publish_files = [
        p
        for p in repo_ls(repo_dir, ".github/workflows")
        if re.fullmatch(r"\.github/workflows/publish[^/]*\.yml", p)
    ]
    meta = pyproject_meta_text(repo_read(repo_dir, "pyproject.toml"))
    if not publish_files and not meta:
        return None
    workflows = []
    for rel in publish_files:
        text = repo_read(repo_dir, rel) or ""
        workflows.append(
            {
                "file": rel.rsplit("/", 1)[-1],
                "auth": classify_auth(text),
                "reusable": uses_reusable(text),
                **parse_remote_publisher(text),
            }
        )
    return {"pyproject": meta, "publish_workflows": workflows}


# --------------------------------------------------------------------------
# Remote-Modus (CI): Workflows + pyproject je Repo über die GitHub-Contents-API
# lesen — kein Fleet-Klon nötig. Gleiches API-Muster wie publish_gate_meter.py.
# --------------------------------------------------------------------------

ORGS = ("achimdehnert", "iilgmbh", "ttz-lif", "meiki-lra")


def _gh_api(path: str, token: str) -> object | None:
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github.raw+json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return body  # raw file content


def scan_repo_api(repo: str, token: str) -> dict | None:
    """Wie scan_repo, aber über die GitHub-API (default branch = Wahrheit)."""
    for org in ORGS:
        listing = _gh_api(f"/repos/{org}/{repo}/contents/.github/workflows", token)
        pyproject = _gh_api(f"/repos/{org}/{repo}/contents/pyproject.toml", token)
        if listing is None and pyproject is None:
            continue  # Repo nicht in dieser Org (oder kein Zugriff) → nächste
        publish_names = sorted(
            e["name"]
            for e in (listing if isinstance(listing, list) else [])
            if re.fullmatch(r"publish[^/]*\.yml", e.get("name", ""))
        )
        meta = pyproject_meta_text(pyproject if isinstance(pyproject, str) else None)
        if not publish_names and not meta:
            return None
        workflows = []
        for name in publish_names:
            text = _gh_api(
                f"/repos/{org}/{repo}/contents/.github/workflows/{name}", token
            )
            text = text if isinstance(text, str) else ""
            workflows.append(
                {
                    "file": name,
                    "auth": classify_auth(text),
                    "reusable": uses_reusable(text),
                    **parse_remote_publisher(text),
                }
            )
        return {"pyproject": meta, "publish_workflows": workflows}
    return None


class PypistatsRateLimited(Exception):
    """pypistats.org antwortet HTTP 429 — Wert fehlt, weil WIR gedrosselt sind,
    nicht weil das Paket keine Downloads hat (#2591 K1: 20/23 still verloren)."""


def pypistats_recent(dist: str, timeout: int = 10) -> dict:
    """Downloads letzte 30 Tage (Totes-Paket-Signal, 3c). Fail-soft: {} bei
    Netz-/Parse-Fehlern; HTTP 429 wird als PypistatsRateLimited sichtbar."""
    url = f"https://pypistats.org/api/packages/{dist.lower()}/recent"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            data = json.load(resp)
        return {"downloads_30d": data.get("data", {}).get("last_month")}
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise PypistatsRateLimited(dist) from exc
        return {}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return {}


def downloads_or_carryover(
    dist: str, prior_pypi: dict, prior_generated_at: str | None, rate_limited: list[str]
) -> dict:
    """Downloads holen; bei 429 den Vorwert aus dem letzten Inventar übernehmen und
    mit `downloads_30d_stale_from` (generated_at des Laufs, der ihn wirklich holte)
    kennzeichnen. Ohne Vorwert bleibt das Feld weg. So bleibt der Regen bei
    Drosselung deterministisch und M5 (earlywarn) behält seine Datengrundlage —
    ehrlich markiert statt still."""
    try:
        return pypistats_recent(dist)
    except PypistatsRateLimited:
        rate_limited.append(dist)
        if prior_pypi.get("downloads_30d") is None:
            return {}
        return {
            "downloads_30d": prior_pypi["downloads_30d"],
            "downloads_30d_stale_from": prior_pypi.get("downloads_30d_stale_from")
            or prior_generated_at,
        }


def prior_inventory(fleet_file: Path) -> tuple[str | None, dict[str, dict]]:
    """(generated_at, `pypi`-Block je Repo) aus dem letzten geschriebenen Inventar —
    Carry-over-Quelle bei Drosselung. Fehlt/kaputt: (None, {})."""
    if not fleet_file.exists():
        return None, {}
    try:
        doc = yaml.safe_load(fleet_file.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return None, {}
    blocks = {
        repo: (pkg.get("pypi") or {})
        for repo, pkg in (doc.get("packages") or {}).items()
        if isinstance(pkg, dict)
    }
    return (doc.get("_meta") or {}).get("generated_at"), blocks


def pypi_live(dist: str, timeout: int = 10) -> dict:
    """Live-Stand von PyPI (Version, letzter Upload, Provenance). Fail-soft: {} bei Fehlern."""
    url = f"https://pypi.org/pypi/{dist}/json"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            data = json.load(resp)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return {}
    info = data.get("info", {})
    uploads = [
        f.get("upload_time_iso_8601", "")
        for files in data.get("releases", {}).values()
        for f in files
    ]
    version = info.get("version")
    result = {
        "version": version,
        "last_upload": max(uploads) if uploads else None,
    }
    if version:
        result["provenance"] = provenance_for(dist, version, data.get("urls", []))
    return result


# --------------------------------------------------------------------------
# K4 am Artefakt (KONZ-platform-052 V10, ADR-278): Provenance der neuesten
# Version über die PyPI-Integrity-API messen statt den Workflow-Text zu lesen
# (der Guard prüft Schreibweise, nicht Wirkung — Befund F1/F2 des Konzepts).
# 🌀 Null aus dem eigenen Fehlerfall ist keine Abwesenheit: Netzfehler/Timeout/
# kaputtes JSON/kein Release-File → status "unbekannt", NIE bundles=0.
# --------------------------------------------------------------------------


def select_release_file(urls: list[dict]) -> dict | None:
    """Wheel bevorzugt, sonst sdist, sonst die erste Datei — None ohne Dateien."""
    wheels = [f for f in urls if f.get("filename", "").endswith(".whl")]
    if wheels:
        return wheels[0]
    sdists = [f for f in urls if f.get("filename", "").endswith(".tar.gz")]
    if sdists:
        return sdists[0]
    return urls[0] if urls else None


def fetch_provenance(
    dist: str, version: str, filename: str, timeout: int = 10
) -> tuple[int | None, bytes]:
    """PyPI Integrity API — reines Netz-I/O. status None = Timeout/Netzfehler."""
    url = f"https://pypi.org/integrity/{dist}/{version}/{filename}/provenance"
    req = urllib.request.Request(
        url, headers={"Accept": "application/vnd.pypi.integrity.v1+json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, b""


def provenance_for(
    dist: str, version: str, urls: list[dict], fetch=fetch_provenance
) -> dict:
    """Provenance-Status der übergebenen Version (K4, ADR-278/KONZ-052 V10).

    status: attested (>=1 Bundle) | unattested (0 Bundles, 200 oder 404) |
    unbekannt (kein Wheel/sdist, Netzfehler, Timeout, kaputtes JSON-Body).
    `fetch` ist injizierbar (Tests: Fixtures statt echtem Netz).
    """
    checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    base = {"version": version, "checked_at": checked_at}
    file = select_release_file(urls)
    if file is None:
        return {**base, "wheel": None, "bundles": None, "status": "unbekannt"}
    filename = file.get("filename", "")
    status_code, body = fetch(dist, version, filename)
    if status_code == 404:
        return {**base, "wheel": filename, "bundles": 0, "status": "unattested"}
    if status_code == 200 and body:
        try:
            bundles = len(json.loads(body).get("attestation_bundles", []))
        except json.JSONDecodeError:
            return {**base, "wheel": filename, "bundles": None, "status": "unbekannt"}
        return {
            **base,
            "wheel": filename,
            "bundles": bundles,
            "status": "attested" if bundles > 0 else "unattested",
        }
    return {**base, "wheel": filename, "bundles": None, "status": "unbekannt"}


def provenance_counts(packages: dict) -> dict[str, int]:
    """K4 am Artefakt: attested/unattested/unbekannt über die ganze Flotte.

    Pakete ohne `provenance`-Feld (offline, nicht auf PyPI) zählen nicht mit.
    """
    counts = {"attested": 0, "unattested": 0, "unbekannt": 0}
    for pkg in packages.values():
        status = ((pkg.get("pypi") or {}).get("provenance") or {}).get("status")
        if status in counts:
            counts[status] += 1
    return counts


# --------------------------------------------------------------------------
# Findings
# --------------------------------------------------------------------------


def build_findings(pkg: dict) -> list[str]:
    findings = []
    if not pkg.get("in_registry"):
        findings.append("registry_missing")
    if len(pkg.get("publishers", [])) > 1:
        findings.append("double_publisher")
    auths = {
        w["auth"] for p in pkg.get("publishers", []) for w in p.get("workflows", [])
    }
    if "token" in auths:
        findings.append("token_auth")
    if "hybrid" in auths:
        findings.append("hybrid_auth")
    if pkg.get("pypi", {}).get("version") and pkg.get("pyproject_version"):
        if pkg["pypi"]["version"] != pkg["pyproject_version"]:
            findings.append("version_drift_pyproject_vs_pypi")
    if not pkg.get("pypi"):
        findings.append("not_on_pypi_or_offline")
    # Totes-Paket-Signal (3c): >180 Tage kein Upload UND kaum Downloads.
    # Nur Signal/Issue-Kandidat — NIE Auto-Aktion (ADR-266 Nicht-Ziel).
    last = (pkg.get("pypi") or {}).get("last_upload")
    dl = (pkg.get("pypi") or {}).get("downloads_30d")
    if last and dl is not None and dl < 50:
        try:
            age = datetime.now(timezone.utc) - datetime.fromisoformat(
                last.replace("Z", "+00:00")
            )
            if age.days > 180:
                findings.append("archival_candidate_stale_and_unused")
        except ValueError:
            pass
    return sorted(findings)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true", help="PyPI-API nicht abfragen")
    ap.add_argument("--check", action="store_true", help="nur Findings drucken")
    ap.add_argument("--github-dir", type=Path, default=GITHUB_DIR)
    ap.add_argument(
        "--remote",
        action="store_true",
        help="Repo-Fakten via GitHub-API statt lokaler Klone (CI; braucht GH_TOKEN)",
    )
    ap.add_argument(
        "--downloads",
        action="store_true",
        help="pypistats-Downloads (30d) je Paket erheben (Totes-Paket-Signal 3c)",
    )
    args = ap.parse_args()

    reg = registry_packages()
    strategies = registry_strategies()
    prior_generated_at, prior_pypi = (
        prior_inventory(FLEET_FILE) if args.downloads else (None, {})
    )
    rate_limited: list[str] = []

    # 1) Fleet-Scan: alle Repos mit Publish-Bezug (platform selbst separat in (2),
    #    platform-pinned = Worktree-Kopie, skip). --remote (CI): Kandidaten =
    #    Registry-Pakete, Fakten via GitHub-API statt lokaler Klone.
    repos: dict[str, dict] = {}
    if args.remote:
        token = __import__("os").environ.get("GH_TOKEN", "")
        if not token:
            print("FEHLER: --remote braucht GH_TOKEN im Env.", file=sys.stderr)
            return 2
        for name in sorted(reg):
            if name == "platform":
                continue
            facts = scan_repo_api(name, token)
            if facts:
                repos[name] = facts
    else:
        for d in sorted(args.github_dir.iterdir()):
            if (
                not d.is_dir()
                or d.name in {"platform", "platform-pinned"}
                or not (d / ".git").exists()
            ):
                continue
            facts = scan_repo(d)
            if facts and (facts["publish_workflows"] or d.name in reg):
                repos[d.name] = facts

    # 2) platform-Publisher aus DIESEM Checkout lesen (Worktree = PR-Stand):
    #    Remote-Publisher den Ziel-Repos zuordnen; tote packages/-Pfade flaggen
    platform_facts = scan_repo(PLATFORM_DIR) or {"publish_workflows": []}
    dead_platform_workflows = []
    platform_remote: dict[str, list[str]] = {}
    for wf in platform_facts["publish_workflows"]:
        target = wf.get("remote_repo", "")
        if target:
            platform_remote.setdefault(target.split("/")[-1], []).append(wf["file"])
        for pdir in wf.get("package_dirs", []):
            # PLATFORM_DIR = dieser Checkout (Session-Worktree = PR-Stand) —
            # bewusst Working-Tree, damit ein PR seine eigenen Fixes sieht.
            if not (PLATFORM_DIR / pdir).is_dir():
                dead_platform_workflows.append(
                    {"file": wf["file"], "missing_path": pdir}
                )

    # 3) Paket-Sicht bauen (ein Eintrag je publizierendem Repo, ohne platform selbst)
    packages = {}
    for repo, facts in sorted(repos.items()):
        dist = facts["pyproject"].get("dist_name") or reg.get(repo)
        publishers = []
        if facts["publish_workflows"]:
            publishers.append({"kind": "self", "workflows": facts["publish_workflows"]})
        if repo in platform_remote:
            wfs = [
                w
                for w in platform_facts["publish_workflows"]
                if w["file"] in platform_remote[repo]
            ]
            publishers.append({"kind": "platform-remote", "workflows": wfs})
        pkg = {
            "repo": repo,
            "dist_name": dist,
            "pyproject_version": facts["pyproject"].get("version"),
            "in_registry": repo in reg,
            "registry_pypi_name": reg.get(repo),
            "strategy": strategies.get(repo),
            "publishers": publishers,
        }
        if dist and not args.offline:
            pkg["pypi"] = pypi_live(dist)
            if args.downloads:
                pkg["pypi"] = {
                    **pkg.get("pypi", {}),
                    **downloads_or_carryover(
                        dist, prior_pypi.get(repo, {}), prior_generated_at, rate_limited
                    ),
                }
        pkg["findings"] = build_findings(pkg)
        packages[repo] = pkg

    # Platform-remote publizierte Pakete ohne lokalen Klon trotzdem aufnehmen —
    # sonst verschwindet z. B. iil-testkit aus dem Fleet-State, nur weil das
    # Repo auf dieser Maschine nicht ausgecheckt ist.
    for target, files in sorted(platform_remote.items()):
        if target in packages:
            continue
        wfs = [w for w in platform_facts["publish_workflows"] if w["file"] in files]
        pkg = {
            "repo": target,
            "dist_name": reg.get(target),
            "pyproject_version": None,
            "in_registry": target in reg,
            "registry_pypi_name": reg.get(target),
            "strategy": strategies.get(target),
            "publishers": [{"kind": "platform-remote", "workflows": wfs}],
        }
        if pkg["dist_name"] and not args.offline:
            pkg["pypi"] = pypi_live(pkg["dist_name"])
        pkg["findings"] = sorted(build_findings(pkg) + ["repo_not_cloned_locally"])
        packages[target] = pkg

    registry_orphans = sorted(r for r in reg if r not in packages and r != "platform")

    # platform-Subtree-Pakete (packages/<x>/pyproject.toml) ohne Publish-Workflow
    referenced_dirs = {
        d
        for wf in platform_facts["publish_workflows"]
        for d in wf.get("package_dirs", [])
    }
    platform_orphan_packages = sorted(
        f"packages/{p.parent.name}"
        for p in (PLATFORM_DIR / "packages").glob("*/pyproject.toml")
        if f"packages/{p.parent.name}" not in referenced_dirs
    )

    doc = {
        "_meta": {
            "generated_by": "tools/pypi_fleet_inventory.py (ADR-266 Stufe 1)",
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "regenerate": "python3 tools/pypi_fleet_inventory.py",
            "note": "Reiner Ground-Truth-Scan — nicht von Hand editieren. Entscheidungen, "
            "Owner-Aktionen und Stufen-Status leben in docs/adr/ADR-266.",
        },
        "packages": packages,
        "registry_orphans_without_publisher": registry_orphans,
        "dead_platform_publish_workflows": dead_platform_workflows,
        "platform_packages_without_publisher": platform_orphan_packages,
    }

    if rate_limited:
        # Sichtbar auf stdout: der Wochen-Report (tee fleet-findings.txt) soll die
        # Drosselung zeigen, statt dass downloads_30d lautlos fehlt.
        print(
            f"pypistats: {len(rate_limited)}/{len(packages)} Pakete HTTP 429 (rate-limited) — "
            "downloads_30d aus Vorlauf übernommen (downloads_30d_stale_from) oder fehlt"
        )

    if args.check:
        for name, pkg in packages.items():
            if pkg["findings"]:
                print(f"{name}: {', '.join(pkg['findings'])}")
        for o in registry_orphans:
            print(f"{o}: registry_orphan_without_publisher")
        for d in dead_platform_workflows:
            print(f"platform/{d['file']}: dead_path {d['missing_path']}")
        counts = provenance_counts(packages)
        print(
            f"K4 am Artefakt: {counts['attested']} attested / "
            f"{counts['unattested']} unattested / {counts['unbekannt']} nicht messbar"
        )
        return 0

    FLEET_FILE.write_text(
        yaml.safe_dump(doc, sort_keys=True, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    print(
        f"→ {FLEET_FILE} ({len(packages)} Pakete, {len(registry_orphans)} Registry-Waisen, "
        f"{len(dead_platform_workflows)} tote platform-Workflows)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
