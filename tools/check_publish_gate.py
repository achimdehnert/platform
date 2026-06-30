#!/usr/bin/env python3
"""Org-Gate gegen ungegatete PyPI-Publish-Workflows (Recurrence-Guard).

Hintergrund (ADR-226): Der bindende Test-Gate muss UNMITTELBAR vor der
irreversiblen PyPI-Upload-Aktion sitzen — pro Repo, nicht zentralisiert. Ein
wiederkehrender Copy-Paste-Drift hängt den Test-Job aus der `needs:`-Kette aus
(z.B. `build` ohne `needs: test`, `publish` nur `needs: build`), sodass ein
Tag-Push auch bei roten Tests publiziert. Realfälle 2026-06-30: aifw, promptfw
(verwaister test-Job), researchfw, nl2cad (gar kein test-Job).

Dieser Checker meldet jeden Job, der die PyPI-Upload-Action ausführt, ohne dass
ein Test-Job (pytest) ihn transitiv über `needs:` gatet — oder, bei Single-Job-
Workflows, ohne dass ein pytest-Schritt VOR dem Upload-Schritt läuft.

Usage:
    python3 tools/check_publish_gate.py [PFAD ...]

PFAD kann sein:
  - eine konkrete Workflow-YAML,
  - ein Repo-Root (dann werden .github/workflows/*publish*.y*ml + *release*.y*ml geprüft),
  - mehrere davon. Default: aktuelles Verzeichnis.

Exit-Code 0 = alle Publish-Jobs gegated; 1 = mindestens ein ungegateter Upload.
"""
from __future__ import annotations

import pathlib
import sys

import yaml

PUBLISH_ACTION = "pypa/gh-action-pypi-publish"


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


def _step_is_publish(step: dict) -> bool:
    return isinstance(step, dict) and str(step.get("uses", "")).startswith(PUBLISH_ACTION)


def _step_runs_pytest(step: dict) -> bool:
    if not isinstance(step, dict):
        return False
    run = step.get("run")
    return isinstance(run, str) and "pytest" in run


def _runs_pytest(job: dict) -> bool:
    return any(_step_runs_pytest(s) for s in _steps(job))


def _is_test_job(job_id: str, job: dict) -> bool:
    """Test-Job = führt pytest aus, ODER heißt erkennbar nach Test."""
    if _runs_pytest(job):
        return True
    name = str(job.get("name", "")) if isinstance(job, dict) else ""
    hay = f"{job_id} {name}".lower()
    return "test" in hay


def _publish_step_index(job: dict) -> int | None:
    for i, step in enumerate(_steps(job)):
        if _step_is_publish(step):
            return i
    return None


def _is_publish_job(job: dict) -> bool:
    return _publish_step_index(job) is not None


def _self_gated(job: dict) -> bool:
    """Single-Job-Fall: läuft ein pytest-Schritt VOR dem Upload-Schritt?"""
    pub_idx = _publish_step_index(job)
    if pub_idx is None:
        return False
    return any(_step_runs_pytest(s) for s in _steps(job)[:pub_idx])


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


def _has_test_ancestor(job_id: str, jobs: dict) -> bool:
    """BFS über die needs-Kette: existiert ein transitiver Test-Job-Vorfahr?"""
    seen: set[str] = set()
    queue = list(_needs_of(jobs.get(job_id, {})))
    while queue:
        cur = queue.pop()
        if cur in seen or cur not in jobs:
            continue
        seen.add(cur)
        if _is_test_job(cur, jobs[cur]):
            return True
        queue.extend(_needs_of(jobs[cur]))
    return False


def analyze_workflow(content: str) -> dict:
    """Analysiert EINEN Workflow-Text.

    Returns dict mit:
      publish_jobs: Liste der Job-IDs, die die PyPI-Upload-Action ausführen
      offenders:    Teilmenge davon, die NICHT (self- oder transitiv) gegated ist
    """
    data = yaml.safe_load(content)
    jobs = _jobs(data)
    publish_jobs = [jid for jid, job in jobs.items() if _is_publish_job(job)]
    offenders = []
    for jid in publish_jobs:
        job = jobs[jid]
        if _self_gated(job):
            continue
        if _has_test_ancestor(jid, jobs):
            continue
        offenders.append(jid)
    return {"publish_jobs": publish_jobs, "offenders": offenders}


def check_file(path: pathlib.Path) -> list[str]:
    """Returns Liste ungegateter Publish-Job-IDs in der Datei (leer = ok)."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        return analyze_workflow(content)["offenders"]
    except yaml.YAMLError:
        return []


def _expand(arg: str) -> list[pathlib.Path]:
    p = pathlib.Path(arg)
    if p.is_dir():
        wf = p / ".github" / "workflows"
        out: list[pathlib.Path] = []
        if wf.is_dir():
            for f in sorted(wf.iterdir()):
                low = f.name.lower()
                if f.suffix in (".yml", ".yaml") and ("publish" in low or "release" in low):
                    out.append(f)
        return out
    return [p]


def main(argv: list[str]) -> int:
    args = argv or ["."]
    targets: list[pathlib.Path] = []
    for a in args:
        targets.extend(_expand(a))

    if not targets:
        print("check_publish_gate: keine Publish-Workflows gefunden.")
        return 0

    bad = False
    for path in targets:
        offenders = check_file(path)
        if offenders:
            bad = True
            for jid in offenders:
                print(
                    f"UNGEGATET: {path}: Job '{jid}' führt {PUBLISH_ACTION} aus, "
                    f"ohne transitiv per needs: einen Test-Job zu gaten."
                )
        else:
            print(f"ok: {path}")

    if bad:
        print(
            "\nFIX: Test-Job in die needs-Kette ziehen "
            "(z.B. `needs: test` an build, oder publish `needs: [test, build]`), "
            "sodass test -> ... -> publish gilt. Siehe ADR-226."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
