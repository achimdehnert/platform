#!/usr/bin/env python3
"""Org-Gate gegen ungegatete PyPI-Publish-Workflows (Recurrence-Guard).

Hintergrund (ADR-226): Der bindende Gate muss UNMITTELBAR vor der irreversiblen
PyPI-Upload-Aktion sitzen — pro Repo, nicht zentralisiert. Ein wiederkehrender
Copy-Paste-Drift hängt den Gate-Job aus der `needs:`-Kette aus (z.B. `build`
ohne `needs: test`, `publish` nur `needs: build`), sodass ein Tag-Push auch bei
roten Tests / ungescanntem Artefakt publiziert. Realfälle 2026-06-30: aifw,
promptfw (verwaister test-Job), researchfw, nl2cad, iil-adrfw, iil-codeguard,
iil-ingest.

INVARIANTE (c) — Enforcement-Minimum: Jeder Job, der nach PyPI hochlädt, muss
unmittelbar davor (im selben Job vor dem Upload-Schritt) ODER transitiv per
`needs:` MINDESTENS EINEN bindenden Gate haben. Bindend = Test-Gate (pytest)
ODER Secret-Scan-Gate (gitleaks). Beides zusammen ist das dokumentierte Ziel
(a)+(b), wird hier aber nicht erzwungen.

Erkannte Upload-Mechanismen: `pypa/gh-action-pypi-publish` UND `twine upload`.
Gescannt werden ALLE Workflow-Dateien (nicht nur *publish*/*release*-benannte);
Dateien ohne Upload-Job werden ignoriert.

Usage:
    python3 tools/check_publish_gate.py [PFAD ...]

PFAD = Workflow-YAML, ODER Repo-Root (scannt .github/workflows/*.y*ml), ODER
mehrere. Default: aktuelles Verzeichnis.

Exit-Code 0 = alle Upload-Jobs gegated; 1 = mindestens ein ungegateter Upload.
"""
from __future__ import annotations

import pathlib
import sys

import yaml

PYPA_ACTION = "pypa/gh-action-pypi-publish"
TWINE_UPLOAD = "twine upload"


def _jobs(data: dict) -> dict:
    if not isinstance(data, dict):
        return {}
    jobs = data.get("jobs")
    return jobs if isinstance(jobs, dict) else {}


def _steps(job: dict) -> list:
    if not isinstance(job, dict):
        return []
    steps = job.get("steps")
    return steps if isinstance(steps, list) else []


def _uses(step: dict) -> str:
    return str(step.get("uses", "")) if isinstance(step, dict) else ""


def _run(step: dict) -> str:
    if not isinstance(step, dict):
        return ""
    run = step.get("run")
    return run if isinstance(run, str) else ""


def _step_is_upload(step: dict) -> bool:
    """PyPI-Upload-Schritt: pypa-Action ODER `twine upload`."""
    return _uses(step).startswith(PYPA_ACTION) or TWINE_UPLOAD in _run(step)


def _step_is_test_gate(step: dict) -> bool:
    return "pytest" in _run(step)


def _step_is_secret_gate(step: dict) -> bool:
    return "gitleaks" in _uses(step).lower() or "gitleaks" in _run(step).lower()


def _step_is_gate(step: dict) -> bool:
    """Bindender Gate-Schritt: Test (pytest) ODER Secret-Scan (gitleaks)."""
    return _step_is_test_gate(step) or _step_is_secret_gate(step)


def _has_gate_step(job: dict) -> bool:
    return any(_step_is_gate(s) for s in _steps(job))


def _is_gate_job(job_id: str, job: dict) -> bool:
    """Gate-Job = enthält einen Gate-Schritt, ODER heisst erkennbar nach Test/Secret-Scan."""
    if _has_gate_step(job):
        return True
    name = str(job.get("name", "")) if isinstance(job, dict) else ""
    hay = f"{job_id} {name}".lower()
    return "test" in hay or "secret-scan" in hay or "gitleaks" in hay


def _upload_step_index(job: dict) -> int | None:
    for i, step in enumerate(_steps(job)):
        if _step_is_upload(step):
            return i
    return None


def _is_upload_job(job: dict) -> bool:
    return _upload_step_index(job) is not None


def _self_gated(job: dict) -> bool:
    """Single-Job-Fall: läuft ein Gate-Schritt (Test/Secret) VOR dem Upload-Schritt?"""
    up_idx = _upload_step_index(job)
    if up_idx is None:
        return False
    return any(_step_is_gate(s) for s in _steps(job)[:up_idx])


def _needs_of(job: dict) -> list:
    if not isinstance(job, dict):
        return []
    needs = job.get("needs")
    if needs is None:
        return []
    if isinstance(needs, str):
        return [needs]
    if isinstance(needs, list):
        return [n for n in needs if isinstance(n, str)]
    return []


def _has_gate_ancestor(job_id: str, jobs: dict) -> bool:
    """BFS über die needs-Kette: existiert ein transitiver Gate-Job-Vorfahr?"""
    seen: set[str] = set()
    queue = list(_needs_of(jobs.get(job_id, {})))
    while queue:
        cur = queue.pop()
        if cur in seen or cur not in jobs:
            continue
        seen.add(cur)
        if _is_gate_job(cur, jobs[cur]):
            return True
        queue.extend(_needs_of(jobs[cur]))
    return False


def analyze_workflow(content: str) -> dict:
    """Analysiert EINEN Workflow-Text.

    Returns dict mit:
      upload_jobs: Job-IDs, die nach PyPI hochladen (pypa ODER twine)
      offenders:   Teilmenge davon ohne (self- oder transitiv) bindenden Gate
    """
    data = yaml.safe_load(content)
    jobs = _jobs(data)
    upload_jobs = [jid for jid, job in jobs.items() if _is_upload_job(job)]
    offenders = []
    for jid in upload_jobs:
        job = jobs[jid]
        if _self_gated(job):
            continue
        if _has_gate_ancestor(jid, jobs):
            continue
        offenders.append(jid)
    return {"upload_jobs": upload_jobs, "offenders": offenders}


def check_file(path: pathlib.Path) -> list[str]:
    """Returns Liste ungegateter Upload-Job-IDs in der Datei (leer = ok/irrelevant)."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        return analyze_workflow(content)["offenders"]
    except yaml.YAMLError:
        return []


def _has_upload_job(path: pathlib.Path) -> bool:
    try:
        return bool(analyze_workflow(path.read_text(encoding="utf-8"))["upload_jobs"])
    except (OSError, yaml.YAMLError):
        return False


def _expand(arg: str) -> list[pathlib.Path]:
    p = pathlib.Path(arg)
    if p.is_dir():
        wf = p / ".github" / "workflows"
        if not wf.is_dir():
            return []
        # ALLE Workflows scannen (nicht nur *publish*-benannte); Nicht-Upload-Dateien
        # werden in main() still übersprungen.
        return [f for f in sorted(wf.iterdir()) if f.suffix in (".yml", ".yaml")]
    return [p]


def main(argv: list[str]) -> int:
    args = argv or ["."]
    targets: list[pathlib.Path] = []
    for a in args:
        targets.extend(_expand(a))

    relevant = [t for t in targets if _has_upload_job(t)]
    if not relevant:
        print("check_publish_gate: keine PyPI-Upload-Workflows gefunden.")
        return 0

    bad = False
    for path in relevant:
        offenders = check_file(path)
        if offenders:
            bad = True
            for jid in offenders:
                print(
                    f"UNGEGATET: {path}: Job '{jid}' lädt nach PyPI hoch, ohne "
                    f"(self- oder transitiv per needs:) einen bindenden Gate "
                    f"(Test ODER Secret-Scan)."
                )
        else:
            print(f"ok: {path}")

    if bad:
        print(
            "\nFIX: Test- ODER Secret-Scan-Gate unmittelbar vor den Upload ziehen "
            "(z.B. `needs: test` an build, publish `needs: [test, build]`, oder "
            "einen gitleaks-Scan-Schritt vor `twine upload`). Siehe ADR-226."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
