"""Konsistenz-Gate für _ci-pypi.yml (Retro e17299-incr B1).

Der gate-Aggregat-Job ist der einzige Required-Check der Caller-Repos —
seine needs-Liste MUSS jeden Job des Reusables abdecken, sonst kann ein
Job (insbesondere ein neuer opt-in-Job) still am Gate vorbeilaufen.
"""

from pathlib import Path

import yaml

WF = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "_ci-pypi.yml"


def _jobs() -> dict:
    return yaml.safe_load(WF.read_text(encoding="utf-8"))["jobs"]


def test_should_include_every_job_in_gate_needs():
    jobs = _jobs()
    gate_needs = set(jobs["gate"]["needs"])
    all_other_jobs = set(jobs) - {"gate"}
    missing = all_other_jobs - gate_needs
    assert not missing, (
        f"Jobs fehlen in gate.needs: {sorted(missing)} — jeder Job des Reusables "
        "muss durchs Aggregat-Gate (Retro e17299-incr B1)."
    )


def test_should_not_reference_unknown_jobs_in_gate_needs():
    jobs = _jobs()
    unknown = set(jobs["gate"]["needs"]) - set(jobs)
    assert not unknown, f"gate.needs referenziert nicht-existente Jobs: {sorted(unknown)}"


def test_should_keep_gate_always_running():
    gate = _jobs()["gate"]
    assert str(gate.get("if", "")).strip() == "always()", (
        "gate braucht if: always(), sonst blockt ein geskippter Vorjob den Check "
        "und Required-Status hängt ewig."
    )
