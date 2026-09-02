"""Tests für tools/modellwechsel_check.py (K2, platform#2690).

Maßstab: "bewertet mit" (assessed_with in den Policy-Kopfzeilen) ↔
"läuft mit" (neu-Feld der letzten model-changes.log-Zeile) — NICHT
Vorgänger ↔ Nachfolger. Der Klassifizierer selbst ist eine Portierung aus
tools/claude-hooks/model_change_detector.sh; test_should_match_detector_...
belegt das gegen das Original (subprocess, kein Reimplementieren des Tests).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import modellwechsel_check as mc  # noqa: E402

SCRIPT = Path(__file__).resolve().parents[1] / "modellwechsel_check.py"
DETECTOR = (
    Path(__file__).resolve().parents[1] / "claude-hooks" / "model_change_detector.sh"
)


def _write_policy(policies_dir: Path, name: str, assessed_with: str) -> None:
    policies_dir.mkdir(parents=True, exist_ok=True)
    (policies_dir / name).write_text(
        f"# Policy: {name}\n"
        f"<!-- rule_class: B | assessed_with: {assessed_with} | reassess_by: 2027-01-01 -->\n",
        encoding="utf-8",
    )


def _write_log(log_path: Path, utc: str, alt: str, neu: str, klasse: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"{utc}\t{alt}\t{neu}\t{klasse}\n")


def _run_cli(tmp_path: Path, *extra_args: str) -> subprocess.CompletedProcess:
    log = tmp_path / "state" / "model-changes.log"
    handled = tmp_path / "state" / "model-rebaseline-handled.tsv"
    policies = tmp_path / "policies"
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--log",
            str(log),
            "--handled",
            str(handled),
            "--policies-dir",
            str(policies),
            *extra_args,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )


# ── (a) MAJOR ggü. assessed_with → fällig + suspendiert ─────────────────────


def test_should_report_faellig_for_major_change_against_assessed_with(tmp_path):
    log = tmp_path / "state" / "model-changes.log"
    policies = tmp_path / "policies"
    _write_policy(policies, "adr-threshold.md", "claude-fable-5")
    _write_log(log, "2026-09-02T08:00:00Z", "claude-fable-5-1", "claude-opus-5", "MAJOR")

    r = _run_cli(tmp_path, "--kurz")

    assert r.returncode == 1, r.stdout + r.stderr
    assert "MAJOR" in r.stdout
    assert "fällig=ja" in r.stdout
    assert "suspendiert" in r.stdout


# ── (b) Rücksprung opus → claude-fable-5-1 bei assessed claude-fable-5 → MINOR


def test_should_classify_fallback_to_point_release_as_minor(tmp_path):
    log = tmp_path / "state" / "model-changes.log"
    policies = tmp_path / "policies"
    _write_policy(policies, "adr-threshold.md", "claude-fable-5")
    _write_log(log, "2026-09-02T08:00:00Z", "opus", "claude-fable-5-1", "MAJOR")

    r = _run_cli(tmp_path, "--kurz")

    assert r.returncode == 1, r.stdout + r.stderr
    assert "MINOR" in r.stdout
    assert "Smoke §1 genügt" in r.stdout


# ── (c) bereits behandelt → nicht fällig ─────────────────────────────────────


def test_should_not_be_faellig_when_already_handled(tmp_path):
    log = tmp_path / "state" / "model-changes.log"
    handled = tmp_path / "state" / "model-rebaseline-handled.tsv"
    policies = tmp_path / "policies"
    _write_policy(policies, "adr-threshold.md", "claude-fable-5")
    _write_log(log, "2026-09-02T08:00:00Z", "claude-fable-5-1", "claude-opus-5", "MAJOR")
    handled.parent.mkdir(parents=True, exist_ok=True)
    handled.write_text("2026-09-02T08:00:00Z\tclaude-fable-5-1\tclaude-opus-5\tMAJOR\n")

    r = _run_cli(tmp_path, "--kurz")

    assert r.returncode == 0, r.stdout + r.stderr
    assert "fällig=nein" in r.stdout
    assert "behandelt=ja" in r.stdout


def test_should_mark_last_line_handled_and_become_not_faellig(tmp_path):
    log = tmp_path / "state" / "model-changes.log"
    policies = tmp_path / "policies"
    _write_policy(policies, "adr-threshold.md", "claude-fable-5")
    _write_log(log, "2026-09-02T08:00:00Z", "claude-fable-5-1", "claude-opus-5", "MAJOR")

    first = _run_cli(tmp_path, "--kurz")
    assert first.returncode == 1

    marked = _run_cli(tmp_path, "--behandelt", "--kurz")
    assert marked.returncode == 0, marked.stdout + marked.stderr

    again = _run_cli(tmp_path, "--kurz")
    assert again.returncode == 0
    assert "behandelt=ja" in again.stdout


# ── (d) leeres/fehlendes Log → kein Ereignis, Exit 0 ─────────────────────────


def test_should_report_no_event_when_log_missing(tmp_path):
    r = _run_cli(tmp_path, "--kurz")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "kein Ereignis" in r.stdout


def test_should_report_no_event_when_log_empty(tmp_path):
    log = tmp_path / "state" / "model-changes.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("")
    policies = tmp_path / "policies"
    _write_policy(policies, "adr-threshold.md", "claude-fable-5")

    r = _run_cli(tmp_path, "--kurz")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "kein Ereignis" in r.stdout


# ── (e) Klassifizierer-Vergleich mit dem Detektor auf den §0-Beispielen ─────


def _run_detector(tmp_path: Path, prev: str, curr: str) -> str:
    """Seed den Detektor mit prev, dann lass ihn auf curr wechseln; gibt die

    von IHM geloggte Klasse zurück (ground truth, keine Neuimplementierung).
    """
    settings = tmp_path / "settings.json"
    state_dir = tmp_path / "detector-state"
    env = {
        "CLAUDE_SETTINGS": str(settings),
        "MODEL_STATE_DIR": str(state_dir),
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(tmp_path),
    }
    settings.write_text(json.dumps({"model": prev}), encoding="utf-8")
    subprocess.run(["bash", str(DETECTOR)], env=env, capture_output=True, text=True, timeout=30)
    settings.write_text(json.dumps({"model": curr}), encoding="utf-8")
    subprocess.run(["bash", str(DETECTOR)], env=env, capture_output=True, text=True, timeout=30)
    log_lines = (state_dir / "model-changes.log").read_text(encoding="utf-8").splitlines()
    return log_lines[-1].split("\t")[3]


RUNBOOK_BEISPIELE = [
    ("claude-opus-5", "claude-fable-5", "MAJOR"),
    ("claude-fable-5-1", "claude-fable-6", "MAJOR"),
    ("claude-haiku-4-5-20251001", "claude-haiku-4-5-20260315", "MAJOR"),
    ("claude-fable-5", "claude-fable-5-1", "MINOR"),
    ("claude-fable-5-1", "claude-fable-5-1[1m]", "SUFFIX"),
    ("claude-fable-5-1", "us.anthropic.claude-fable-5-1", "MAJOR"),
]


def test_should_match_detector_on_runbook_examples(tmp_path):
    for i, (prev, curr, expected) in enumerate(RUNBOOK_BEISPIELE):
        sandbox = tmp_path / f"case-{i}"
        sandbox.mkdir()
        detector_klasse = _run_detector(sandbox, prev, curr)
        python_klasse = mc.classify_change(prev, curr)
        assert detector_klasse == expected, f"{prev}→{curr}: Detektor={detector_klasse}"
        assert python_klasse == expected, f"{prev}→{curr}: Python={python_klasse}"
        assert python_klasse == detector_klasse, f"{prev}→{curr}: Python≠Detektor"


# ── Einheiten-Tests der portierten Bausteine ─────────────────────────────────


def test_should_strip_suffix_variant_only_at_end():
    assert mc.norm_id("claude-fable-5-1[1m]") == "claude-fable-5-1"
    assert mc.norm_id("claude-fable-5-1") == "claude-fable-5-1"


def test_should_return_none_family_for_unparsable_form():
    assert mc.fam_major("us.anthropic.claude-fable-5-1") is None
    assert mc.fam_major("claude-fable-5-1") == "fable-5"


def test_should_use_majority_assessed_with_and_flag_disagreement(tmp_path):
    policies = tmp_path / "policies"
    _write_policy(policies, "a.md", "claude-fable-5")
    _write_policy(policies, "b.md", "claude-fable-5")
    _write_policy(policies, "c.md", "claude-opus-5")

    majority, pairs = mc.read_assessed_with(policies)

    assert majority == "claude-fable-5"
    assert len(pairs) == 3
    assert mc.consensus_note(pairs) != ""
