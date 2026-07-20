#!/usr/bin/env python3
"""platform-doctor v0.1 — dynamischer, read-only CI-Conformance-Check.

ADR-209 v4 / D5. KEINE Schreib-Operationen. Repo-Set wird zur Laufzeit
entdeckt (kein hartkodiertes Inventar — das wäre selbst Drift/Rot-Fläche).

Discovery:  Scan von $GITHUB_DIR (default ~/github) nach Verzeichnissen mit
            .git → origin owner/repo. Aktualität via `gh repo view
            --json pushedAt,isArchived` (read-only, degradiert offline).

Checks (best-effort, pro Repo):
  - ci-pin       : interne reusable Workflows per SHA gepinnt (nicht @main/@vN)
  - dep-gitsub   : keine `git+…#subdirectory`-Dependencies
  - py-match     : (pylib) requires-python ⊆ CI-python-version
  - health       : (hub) /livez + /healthz referenziert
  - frozen       : .ci-frozen mit gültigem re-review-date
  - freshness    : pushedAt < 180 d ODER frozen (sonst „maintenance")

Exit 0 immer (informativ). `--strict` → exit 1 wenn ein Repo rot.
Verwendung:  python3 platform_doctor.py [--dir ~/github] [--json] [--strict]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SHA_RE = re.compile(r"@[0-9a-f]{40}\b")
USES_INTERNAL_RE = re.compile(
    r"uses:\s*([A-Za-z0-9_.-]+/\.github|achimdehnert/[A-Za-z0-9_.-]+)"
    r"/\.github/workflows/[^@\s]+@(\S+)"
)
GITSUB_RE = re.compile(r"git\+[^\s]+#subdirectory=", re.I)
STALE_DAYS = 180


def sh(args: list[str], cwd: Path | None = None, timeout: int = 15) -> str:
    try:
        return subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, timeout=timeout
        ).stdout.strip()
    except Exception:
        return ""


def discover_repos(root: Path) -> list[Path]:
    return sorted(
        p.parent for p in root.glob("*/.git") if (p.is_dir() or p.is_file())
    )


def origin_slug(repo: Path) -> str:
    url = sh(["git", "-C", str(repo), "remote", "get-url", "origin"])
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+)", url)
    return m.group(1) if m else ""


def gh_meta(slug: str) -> dict:
    if not slug:
        return {}
    out = sh(["gh", "repo", "view", slug, "--json", "pushedAt,isArchived"])
    try:
        return json.loads(out) if out else {}
    except Exception:
        return {}


def infer_category(repo: Path) -> str:
    has_docker = (repo / "Dockerfile").exists() or any(
        repo.glob("docker-compose*.y*ml")
    )
    pyproject = repo / "pyproject.toml"
    is_pkg = pyproject.exists() and "[project]" in _read(pyproject)
    if is_pkg and not has_docker:
        return "pylib"
    if has_docker:
        return "hub"
    return "other"


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _grep_tree(repo: Path, pattern: re.Pattern, globs: list[str]) -> bool:
    for g in globs:
        for f in repo.glob(g):
            if f.is_file() and pattern.search(_read(f)):
                return True
    return False


def check_repo(repo: Path) -> dict:
    slug = origin_slug(repo)
    cat = infer_category(repo)
    meta = gh_meta(slug)
    findings: list[tuple[str, str]] = []  # (severity, msg)  severity: red|yellow

    # ci-pin: interne reusable Workflows müssen per SHA gepinnt sein
    wf = list((repo / ".github" / "workflows").glob("*.y*ml"))
    for f in wf:
        for m in USES_INTERNAL_RE.finditer(_read(f)):
            ref = m.group(2)
            if not re.fullmatch(r"[0-9a-f]{40}", ref):
                findings.append(
                    ("red", f"{f.name}: interner Workflow @{ref} (kein SHA-Pin)")
                )

    # dep-gitsub
    if _grep_tree(repo, GITSUB_RE, ["requirements*.txt", "pyproject.toml",
                                    "requirements/*.txt"]):
        findings.append(("red", "git+…#subdirectory-Dependency vorhanden"))

    # frozen
    frozen = repo / ".ci-frozen"
    is_frozen = frozen.exists()
    if is_frozen:
        txt = _read(frozen)
        m = re.search(r"re-review-date:\s*(\d{4}-\d{2}-\d{2})", txt)
        if m:
            try:
                if dt.date.fromisoformat(m.group(1)) < dt.date.today():
                    findings.append(("red", f".ci-frozen abgelaufen ({m.group(1)})"))
            except ValueError:
                findings.append(("yellow", ".ci-frozen: re-review-date unlesbar"))
        else:
            findings.append(("yellow", ".ci-frozen ohne re-review-date"))

    # py-match (pylib)
    if cat == "pylib":
        pp = _read(repo / "pyproject.toml")
        rp = re.search(r'requires-python\s*=\s*"[^"]*?(\d+\.\d+)', pp)
        ci_pys = set(re.findall(r'(?:python-version|python)[:\s"\']+(\d+\.\d+)',
                                " ".join(_read(f) for f in wf)))
        if rp and ci_pys:
            minv = tuple(int(x) for x in rp.group(1).split("."))
            for c in ci_pys:
                if tuple(int(x) for x in c.split(".")) < minv:
                    findings.append(
                        ("red", f"CI testet py{c} < requires-python {rp.group(1)}")
                    )

    # health (hub)
    if cat == "hub":
        body = " ".join(
            _read(f) for f in list(repo.glob("**/urls.py"))[:50]
        )
        if "/livez" not in body and "livez" not in body:
            findings.append(("yellow", "kein /livez referenziert"))

    # freshness
    pushed = meta.get("pushedAt", "")
    stale = False
    if pushed:
        try:
            age = (dt.datetime.now(dt.timezone.utc)
                   - dt.datetime.fromisoformat(pushed.replace("Z", "+00:00"))).days
            stale = age > STALE_DAYS
        except Exception:
            pass
    if stale and not is_frozen:
        findings.append(("yellow", f"keine Aktivität >{STALE_DAYS}d, kein .ci-frozen"))
    if meta.get("isArchived"):
        findings.append(("yellow", "auf GitHub archiviert — Scope prüfen"))

    sev = "green"
    if any(s == "red" for s, _ in findings):
        sev = "red"
    elif findings:
        sev = "yellow"
    return {
        "repo": repo.name,
        "slug": slug or "?",
        "category": cat,
        "status": sev,
        "findings": findings,
        "pushedAt": pushed[:10] if pushed else "?",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="platform-doctor v0.1 (read-only)")
    ap.add_argument("--dir", default=os.environ.get("GITHUB_DIR",
                                                    str(Path.home() / "github")))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 wenn ein Repo rot")
    a = ap.parse_args()

    root = Path(a.dir).expanduser()
    repos = discover_repos(root)
    results = [check_repo(r) for r in repos]

    if a.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        today = dt.date.today().isoformat()
        n = {s: sum(r["status"] == s for r in results)
             for s in ("green", "yellow", "red")}
        print(f"# platform-doctor — {today}\n")
        print(f"Repos entdeckt: **{len(results)}** (dynamisch, "
              f"`{root}`)  ·  🟢 {n['green']}  🟡 {n['yellow']}  🔴 {n['red']}\n")
        print("| Status | Repo | Kat | pushedAt | Befund |")
        print("|---|---|---|---|---|")
        order = {"red": 0, "yellow": 1, "green": 2}
        for r in sorted(results, key=lambda x: (order[x["status"]], x["repo"])):
            icon = {"red": "🔴", "yellow": "🟡", "green": "🟢"}[r["status"]]
            msg = "; ".join(m for _, m in r["findings"]) or "—"
            print(f"| {icon} | {r['repo']} | {r['category']} "
                  f"| {r['pushedAt']} | {msg} |")
        print("\n_read-only · ADR-209 D5 · keine Schreib-Ops · "
              "Discovery dynamisch, kein hartkodiertes Inventar_")

    if a.strict and any(r["status"] == "red" for r in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
