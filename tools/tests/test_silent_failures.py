"""Guard gegen stille Fehlschläge in Workflows.

Anlass 2026-07-31: Der Hardcoding-Megatest lief zwei Wochen nicht (`python`
statt `python3`), meldete aber grün — `continue-on-error: true` maskierte es.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "check_silent_failures.py"
_spec = importlib.util.spec_from_file_location("csf", _SRC)
csf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(csf)

WEICH = "continue-on-error: true"


def _schreibe(tmp_path, name, inhalt):
    p = tmp_path / name
    p.write_text(inhalt, encoding="utf-8")
    return p


def test_should_flag_step_whose_outputs_are_read_without_outcome_check(tmp_path):
    """Der Realfall: Absturz ⇒ leere Outputs ⇒ kein Folge-Schritt ⇒ grün."""
    wf = _schreibe(
        tmp_path,
        "melder.yml",
        f"""
name: Melder
on: {{schedule: [{{cron: '0 5 * * *'}}]}}
jobs:
  meter:
    runs-on: ubuntu-latest
    steps:
      - name: Meter
        id: meter
        {WEICH}
        run: python3 tools/meter.py
      - name: Issue anlegen
        if: steps.meter.outputs.violations != '0'
        run: gh issue create
""",
    )
    funde = csf.pruefe_datei(wf)
    assert any(f.art == "Absturz bleibt still" for f in funde)


def test_should_accept_step_with_outcome_branch(tmp_path):
    """Wer den Absturz meldet, darf weichstellen."""
    wf = _schreibe(
        tmp_path,
        "gut.yml",
        f"""
# Weichgestellt, damit ein Absturz den Zeitplan nicht rot faerbt — gemeldet
# wird er im Schritt darunter.
name: Melder
on: {{schedule: [{{cron: '0 5 * * *'}}]}}
jobs:
  meter:
    runs-on: ubuntu-latest
    steps:
      - name: Meter
        id: meter
        {WEICH}
        run: python3 tools/meter.py
      - name: Absturz melden
        if: steps.meter.outcome == 'failure'
        run: exit 1
      - name: Issue anlegen
        if: steps.meter.outputs.violations != '0'
        run: gh issue create
""",
    )
    assert csf.pruefe_datei(wf) == []


def test_should_accept_reason_in_file_header(tmp_path):
    """`staging-registry-checks.yml` begründet acht Jobs in EINEM Header.

    Ohne diese Regel meldete der Check dort acht Fehlalarme (erster Lauf
    2026-07-31, 18 Funde — davon 8 falsch).
    """
    wf = _schreibe(
        tmp_path,
        "header.yml",
        f"""
# Bewusst nicht blockierend: die Checks brauchen SSH zu Live-Hosts und wuerden
# sonst PRs an fremder Drift scheitern lassen.
name: Checks
on: {{schedule: [{{cron: '0 5 * * *'}}]}}
jobs:
  r1:
    runs-on: ubuntu-latest
    {WEICH}
    steps:
      - run: bash check.sh
""",
    )
    assert csf.pruefe_datei(wf) == []


def test_should_flag_missing_reason(tmp_path):
    wf = _schreibe(
        tmp_path,
        "ohne.yml",
        f"""
name: Ohne
on: {{push: {{branches: [main]}}}}
jobs:
  j:
    runs-on: ubuntu-latest
    steps:
      - name: Schritt
        {WEICH}
        run: echo hi
""",
    )
    funde = csf.pruefe_datei(wf)
    assert [f.art for f in funde] == ["ohne Begründung"]


def test_should_not_accept_decorative_comment_as_reason(tmp_path):
    """Ein Trennstrich ist keine Begründung."""
    wf = _schreibe(
        tmp_path,
        "deko.yml",
        f"""
name: Deko
on: {{push: {{branches: [main]}}}}
jobs:
  j:
    runs-on: ubuntu-latest
    steps:
      # ---
      - name: Schritt
        {WEICH}
        run: echo hi
""",
    )
    assert any(f.art == "ohne Begründung" for f in csf.pruefe_datei(wf))


def test_should_ignore_step_without_id(tmp_path):
    """Ohne `id` kann niemand die Outputs lesen — kein stiller Pfad."""
    wf = _schreibe(
        tmp_path,
        "ohneid.yml",
        f"""
# Begruendung: optionaler Upload, darf fehlschlagen.
name: X
on: {{push: {{branches: [main]}}}}
jobs:
  j:
    runs-on: ubuntu-latest
    steps:
      - name: Upload
        {WEICH}
        run: echo hi
""",
    )
    assert csf.pruefe_datei(wf) == []


def test_should_report_unparsable_yaml(tmp_path):
    wf = _schreibe(tmp_path, "kaputt.yml", "name: X\n  jobs: [[[\n")
    assert any(f.art == "nicht parsebar" for f in csf.pruefe_datei(wf))


@pytest.mark.parametrize(
    "datei",
    sorted(
        (pathlib.Path(__file__).resolve().parents[2] / ".github" / "workflows").glob(
            "*.yml"
        )
    ),
)
def test_should_find_no_silent_failure_in_repo_workflows(datei):
    """Regression: die echten Workflows bleiben sauber."""
    funde = csf.pruefe_datei(datei)
    assert funde == [], "\n".join(str(f) for f in funde)
