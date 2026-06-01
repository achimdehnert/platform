#!/usr/bin/env python3
"""repo_readiness.py — Readiness-Gate für ein Repo (platform:/repo-ready).

Beantwortet EINE Frage: "Ist dieses Repo bereit zum Testen?" — entlang drei
Schichten, ohne `teste_repo.py`/`repo_health_check.py` zu duplizieren:

  1. FRESHNESS/KONSISTENZ (das Novum): git == origin/main, Working-Tree clean,
     und vor allem **installierte/aktive Paket-Version == Source** — fängt den
     Stale-Install-Footgun (z. B. editable auf /tmp statt aufs echte Repo).
  2. QUALITY (delegiert): ruft `scripts/teste_repo.py` (+ optional
     `tools/repo_health_check.py`) auf, statt Lint/pytest neu zu bauen.
  3. RUNTIME-SMOKE (typ-bewusst): lib/cli → Import + Entrypoint; renderer →
     gerendertes Artefakt + Schlüssel-Marker; django/mcp → an bestehende
     Checks/Health delegieren.

Auto-Fix ist **default an** (idempotent + sicher): editable-Repoint, `git pull
--ff-only` (nur bei cleanem Tree), `ruff --fix`. NIE: dirty Tree anfassen,
reset/clean/force, fremde Working-Trees. `--report-only` schaltet Fixes aus.

Repo-Typ kommt aus `project-facts.md` (`**Type**:`), sonst Heuristik — NICHT
hardcoden. Aufruf:  python3 tools/repo_readiness.py <repo-name|pfad> [--report-only] [--json]

platform:ADR-211/216/225-Kontext; Skill `/repo-ready`. Exit 0 = bereit, 1 = nicht.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def sh(cmd: list[str], cwd: Path | None = None, timeout: int = 120) -> tuple[int, str]:
    """Subprozess, kombinierter Output. Nie Exception nach außen."""
    try:
        p = subprocess.run(
            cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, timeout=timeout
        )
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return 127, f"not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"timeout: {' '.join(cmd)}"


def resolve_repo(arg: str) -> Path | None:
    """Repo-Arg → Pfad. Name relativ zu $GITHUB_DIR oder absoluter Pfad."""
    p = Path(arg).expanduser()
    if p.is_dir() and (p / ".git").exists():
        return p.resolve()
    base = Path(os.environ.get("GITHUB_DIR", str(Path.home() / "github")))
    cand = base / arg
    if cand.is_dir():
        return cand.resolve()
    return None


def read_repo_type(repo: Path) -> str:
    """`**Type**:`-Feld aus project-facts.md, sonst Heuristik (kein Hardcode)."""
    for rel in (".windsurf/rules/project-facts.md", "project-facts.md", "docs/project-facts.md"):
        pf = repo / rel
        if pf.exists():
            m = re.search(r"\*\*Type\*\*\s*:\s*`?([a-z0-9_-]+)`?", pf.read_text(errors="ignore"), re.I)
            if m and m.group(1).lower() != "unknown":
                return m.group(1).lower()
    # Heuristik
    if (repo / "manage.py").exists():
        return "django"
    if list(repo.glob("*_mcp/server.py")) or list(repo.glob("**/server.py"))[:1] and "mcp" in repo.name:
        return "mcp"
    if list(repo.glob("**/klickdummy/*/screens-spec.yaml")) or (repo / "src").glob("*/snippets/skins"):
        # iil-klickdummy / KD-Tooling: zugleich python-package
        if (repo / "pyproject.toml").exists():
            return "python-package"
    if (repo / "pyproject.toml").exists():
        return "python-package"
    return "unknown"


def pyproject_name_version(repo: Path) -> tuple[str | None, str | None]:
    pp = repo / "pyproject.toml"
    if not pp.exists():
        return (None, None)
    txt = pp.read_text(errors="ignore")
    name = re.search(r'(?m)^\s*name\s*=\s*"([^"]+)"', txt)
    ver = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"', txt)
    return (name.group(1) if name else None, ver.group(1) if ver else None)


# ---------- Layer 1: Freshness / Konsistenz ----------------------------------

def check_git(repo: Path, fix: bool, findings: list[dict]) -> None:
    sh(["git", "fetch", "-q", "origin"], cwd=repo, timeout=60)
    rc, head = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)
    branch = head.strip()
    rc, dirty = sh(["git", "status", "--porcelain"], cwd=repo)
    is_dirty = bool(dirty.strip())
    rc, counts = sh(["git", "rev-list", "--left-right", "--count", "HEAD...@{upstream}"], cwd=repo)
    ahead = behind = 0
    if rc == 0 and counts.split():
        parts = counts.split()
        if len(parts) == 2:
            ahead, behind = int(parts[0]), int(parts[1])
    status, action = "ok", ""
    if is_dirty:
        status, action = "warn", "Working-Tree dirty — NICHT auto-gefixt (Datenverlust-Schutz)."
    elif behind > 0 and fix:
        rc, out = sh(["git", "pull", "--ff-only"], cwd=repo, timeout=90)
        action = f"git pull --ff-only ({behind} behind) → rc={rc}"
        status = "fixed" if rc == 0 else "fail"
    elif behind > 0:
        status, action = "warn", f"{behind} commits behind origin (kein Fix: --report-only)."
    findings.append({
        "layer": "freshness", "check": "git",
        "detail": f"branch={branch} ahead={ahead} behind={behind} dirty={is_dirty}",
        "status": status, "action": action,
    })


def check_install_consistency(repo: Path, fix: bool, findings: list[dict]) -> None:
    """Installierte/aktive Version + editable-Target == dieses Repo? (Kern-Novum)."""
    name, src_ver = pyproject_name_version(repo)
    if not name:
        findings.append({"layer": "freshness", "check": "install", "detail": "kein pyproject [project].name", "status": "skip", "action": ""})
        return
    import importlib.metadata as im

    inst_ver = editable_path = None
    try:
        inst_ver = im.version(name)
        dist = im.distribution(name)
        durl = dist.read_text("direct_url.json")
        if durl:
            j = json.loads(durl)
            if j.get("dir_info", {}).get("editable"):
                editable_path = (j.get("url") or "").replace("file://", "")
    except im.PackageNotFoundError:
        inst_ver = "NOT-INSTALLED"
    except Exception as exc:  # noqa: BLE001
        findings.append({"layer": "freshness", "check": "install", "detail": f"metadata-read: {exc}", "status": "warn", "action": ""})

    repo_str = str(repo)
    stale_target = bool(editable_path) and Path(editable_path).resolve() != repo
    version_mismatch = bool(src_ver) and inst_ver not in (src_ver, None) and inst_ver != "NOT-INSTALLED"
    needs_fix = inst_ver == "NOT-INSTALLED" or stale_target or version_mismatch

    detail = f"name={name} installed={inst_ver} source={src_ver} editable_target={editable_path or '—'}"
    if not needs_fix:
        findings.append({"layer": "freshness", "check": "install", "detail": detail, "status": "ok", "action": ""})
        return
    why = "nicht installiert" if inst_ver == "NOT-INSTALLED" else ("stale editable-target → " + str(editable_path) if stale_target else f"version {inst_ver}≠{src_ver}")
    if fix:
        rc, out = sh([sys.executable, "-m", "pip", "install", "-e", repo_str, "--break-system-packages", "--quiet"], cwd=repo, timeout=300)
        # re-check
        try:
            new_ver = im.version(name)
        except Exception:  # noqa: BLE001
            new_ver = "?"
        ok = rc == 0
        findings.append({"layer": "freshness", "check": "install", "detail": detail + f" → repoint rc={rc} now={new_ver}",
                         "status": "fixed" if ok else "fail", "action": f"pip install -e . ({why})"})
    else:
        findings.append({"layer": "freshness", "check": "install", "detail": detail,
                         "status": "warn", "action": f"editable-Repoint nötig ({why}) — mit Fix-Modus behebbar"})


# ---------- Layer 2: Quality (delegiert) -------------------------------------

def platform_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def check_quality(repo: Path, fix: bool, findings: list[dict]) -> None:
    teste = platform_dir() / "scripts" / "teste_repo.py"
    if not teste.exists():
        findings.append({"layer": "quality", "check": "teste_repo", "detail": "scripts/teste_repo.py fehlt", "status": "skip", "action": ""})
        return
    # ruff --fix vorab (nur sichere Fixes), wenn gewünscht
    if fix:
        sh(["ruff", "check", "--fix", str(repo)], cwd=repo, timeout=120)
    rc, out = sh([sys.executable, str(teste), str(repo)], cwd=repo, timeout=600)
    # Report-Zeilen (✅/❌/⚠️/⏭️) aus dem teste_repo-Report extrahieren, einzeilig.
    lines = [ln.strip() for ln in out.splitlines() if any(s in ln for s in ("✅", "❌", "⚠️", "⏭️"))]
    detail = " · ".join(lines[-8:]) if lines else "(kein Report)"
    findings.append({"layer": "quality", "check": "teste_repo", "detail": detail, "status": "ok" if rc == 0 else "fail", "action": f"teste_repo.py rc={rc}"})


# ---------- Layer 3: Runtime-Smoke (typ-bewusst) -----------------------------

def smoke_python(repo: Path, findings: list[dict]) -> None:
    name, _ = pyproject_name_version(repo)
    if not name:
        return
    mod = name.replace("-", "_")
    rc, out = sh([sys.executable, "-c", f"import {mod}; print(getattr({mod},'__version__','?'))"], cwd=repo)
    findings.append({"layer": "runtime", "check": "import", "detail": f"import {mod}: {out.strip()[:80]}", "status": "ok" if rc == 0 else "fail", "action": ""})


def smoke_renderer(repo: Path, findings: list[dict]) -> None:
    # Schlüssel-Marker im Renderer-Quelltext (no-deps, schnell). Voller
    # Playwright-Smoke ist Skill-Schritt (browser), hier statische Mindestprobe.
    src = repo / "src"
    markers = {"spec-toggle": False, "trace-strip": False}
    for f in src.rglob("lineage.py"):
        t = f.read_text(errors="ignore")
        for m in markers:
            markers[m] = markers[m] or (m in t)
    if any(markers.values()):
        findings.append({"layer": "runtime", "check": "renderer-markers",
                         "detail": ", ".join(f"{k}={'✓' if v else '✗'}" for k, v in markers.items()),
                         "status": "ok" if all(markers.values()) else "warn", "action": "Voll-Smoke via Playwright im Skill-Schritt"})


def smoke_mcp(repo: Path, findings: list[dict]) -> None:
    # Endpoint-Smoke nur wenn ENV-URL gesetzt (kein Hardcode).
    base = os.environ.get("ORCHESTRATOR_HEALTH_URL")
    if not base:
        findings.append({"layer": "runtime", "check": "mcp-health", "detail": "ORCHESTRATOR_HEALTH_URL nicht gesetzt — übersprungen", "status": "skip", "action": ""})
        return
    rc, out = sh(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "10", base], timeout=15)
    findings.append({"layer": "runtime", "check": "mcp-health", "detail": f"{base} → {out.strip()}", "status": "ok" if out.strip() == "200" else "warn", "action": ""})


def check_runtime(repo: Path, rtype: str, findings: list[dict]) -> None:
    if rtype in ("python-package", "lib", "cli"):
        smoke_python(repo, findings)
    if rtype in ("python-package", "renderer", "klickdummy") or list(repo.glob("**/klickdummy")):
        smoke_renderer(repo, findings)
    if rtype in ("mcp", "orchestrator"):
        smoke_mcp(repo, findings)
    if rtype == "django":
        findings.append({"layer": "runtime", "check": "django", "detail": "→ /frontend-ui-test bzw. /pre-release-test (Views/CSRF/DNS)", "status": "skip", "action": "delegieren"})


# ---------- Report -----------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Repo-Readiness-Gate (/repo-ready)")
    ap.add_argument("repo", help="Repo-Name (rel. zu $GITHUB_DIR) oder Pfad")
    ap.add_argument("--report-only", action="store_true", help="Keine Auto-Fixes (default: fixen)")
    ap.add_argument("--json", action="store_true", help="JSON statt Tabelle")
    args = ap.parse_args(argv)

    repo = resolve_repo(args.repo)
    if not repo:
        print(f"✗ Repo nicht gefunden: {args.repo}", file=sys.stderr)
        return 2
    fix = not args.report_only
    rtype = read_repo_type(repo)

    findings: list[dict] = []
    check_git(repo, fix, findings)
    check_install_consistency(repo, fix, findings)
    check_quality(repo, fix, findings)
    check_runtime(repo, rtype, findings)

    bad = [f for f in findings if f["status"] == "fail"]
    warn = [f for f in findings if f["status"] == "warn"]
    ready = not bad and not warn

    if args.json:
        print(json.dumps({"repo": str(repo), "type": rtype, "ready": ready, "findings": findings}, ensure_ascii=False, indent=2))
    else:
        print(f"\n== /repo-ready · {repo.name} (type={rtype}) · fix={'on' if fix else 'off'} ==")
        for f in findings:
            icon = {"ok": "✅", "fixed": "🔧", "warn": "⚠️", "fail": "❌", "skip": "·"}.get(f["status"], "?")
            det = " ".join(str(f["detail"]).split())  # einzeilig
            print(f"  {icon} [{f['layer']}/{f['check']}] {det}" + (f"  → {f['action']}" if f["action"] else ""))
        verdict = "BEREIT ✅" if ready else ("FAIL ❌" if bad else "mit Warnungen ⚠️")
        print(f"\n→ {verdict}  ({len(bad)} fail, {len(warn)} warn)")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
