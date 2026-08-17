#!/usr/bin/env python3
"""Alle shared-ci-Referenzen eines Repos auf v1.1.9 — inkl. Deploy-Pfad."""
import base64, json, re, subprocess, sys
ZIEL = "v1.1.10"
ZWEIG = "session/2026-08-17/achim-dehnert/sharedci-v1110"
TROCKEN = "--apply" not in sys.argv
REPOS = sys.argv[1].split(",")

def gh(*a):
    r = subprocess.run(["gh", *a], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[:200])
    return r.stdout

for repo in REPOS:
    basis = json.loads(gh("api", f"repos/{repo}"))["default_branch"]
    # Branch existiert schon (erste Welle) oder wird angelegt
    try:
        gh("api", f"repos/{repo}/git/ref/heads/{ZWEIG}")
        vorhanden = True
    except RuntimeError:
        vorhanden = False
        if not TROCKEN:
            kopf = json.loads(gh("api", f"repos/{repo}/git/ref/heads/{basis}"))["object"]["sha"]
            gh("api", f"repos/{repo}/git/refs", "-X", "POST",
               "-f", f"ref=refs/heads/{ZWEIG}", "-f", f"sha={kopf}")
    ref = ZWEIG if (vorhanden or not TROCKEN) else basis
    dateien = gh("api", f"repos/{repo}/contents/.github/workflows?ref={ref}", "-q", ".[].name").split()
    aend = []
    for f in dateien:
        roh = json.loads(gh("api", f"repos/{repo}/contents/.github/workflows/{f}?ref={ref}"))
        text = base64.b64decode(roh["content"]).decode()
        alt = set(re.findall(r"shared-ci/\.github/(?:workflows|actions)/[\w.-]+@([\w.\-/]+)", text))
        neu = re.sub(r"(shared-ci/\.github/(?:workflows|actions)/[\w.-]+@)[\w.\-/]+", r"\g<1>" + ZIEL, text)
        if neu == text:
            continue
        aend.append(f"{f}({','.join(sorted(alt - {ZIEL}))})")
        if not TROCKEN:
            gh("api", f"repos/{repo}/contents/.github/workflows/{f}", "-X", "PUT",
               "-f", f"message=ci: shared-ci-Referenzen in {f} auf {ZIEL}",
               "-f", f"content={base64.b64encode(neu.encode()).decode()}",
               "-f", f"sha={roh['sha']}", "-f", f"branch={ZWEIG}")
    print(f"{repo}: {' '.join(aend) if aend else 'schon synchron'}")
