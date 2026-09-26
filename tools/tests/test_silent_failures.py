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


# ── Zweite Familie: stille Schlucker in Shell-Code (Ausweitung 2026-08-20) ────


def _sh(tmp_path, name: str, inhalt: str):
    p = tmp_path / name
    p.write_text(inhalt, encoding="utf-8")
    return p


def test_should_flag_tee_pipeline_without_pipefail(tmp_path):
    """Retro 932035: pytest hinter `| tee` — die Pipeline meldet den Exit des tee."""
    datei = _sh(tmp_path, "lauf.sh", "#!/bin/bash\npytest tools/tests | tee log.txt\n")
    funde = csf.pruefe_shell(datei)
    assert [f.art for f in funde] == ["Pipeline schluckt den Exit-Code"]


def test_should_accept_tee_pipeline_with_pipefail(tmp_path):
    """Gegenprobe: mit pipefail ist die Pipeline ehrlich."""
    datei = _sh(
        tmp_path,
        "lauf.sh",
        "#!/bin/bash\nset -o pipefail\npytest tools/tests | tee log.txt\n",
    )
    assert csf.pruefe_shell(datei) == []


def test_should_flag_error_turned_into_a_number(tmp_path):
    """Retro c45b39: `reap 2>&1 || true` + `grep -c` meldete Fehler als gruene Null."""
    datei = _sh(
        tmp_path,
        "reap.sh",
        '#!/bin/bash\nN=$(reap 2>&1 | grep -c "^entfernt" || true)\n',
    )
    funde = csf.pruefe_shell(datei)
    assert any(f.art == "Fehler wird zu einer Zahl" for f in funde)


def test_should_leave_a_plain_script_alone(tmp_path):
    datei = _sh(tmp_path, "ruhig.sh", "#!/bin/bash\nset -euo pipefail\necho hallo\n")
    assert csf.pruefe_shell(datei) == []


# ── Ausweitung 2026-09-14 (Retro oqu6Z6 §5a, M4): Outputs als WERT ─────────────
# Realfall `.github/workflows/handover-append-only.yml`: der weichgestellte
# Token-Schritt war begruendet, seine Outputs flossen aber nicht in ein `if:`,
# sondern als `GH_TOKEN: ${{ steps.app_token.outputs.token || … }}` in den
# Schritt, der das Gate-Urteil faellt. Der Lint meldete „kein stiller
# Fehlschlag", obwohl ein Ausfall still zum Fallback wurde.

_REALFALL_WERT = f"""
name: Handover append-only
on: pull_request
jobs:
  auslagerung:
    runs-on: ubuntu-latest
    steps:
      # Kurzlebiger App-Token; ohne App faellt der Job auf GITHUB_TOKEN zurueck
      # und meldet Fremd-Refs dann als "nicht ermittelbar".
      - id: app_token
        name: App-Token
        {WEICH}
        uses: actions/create-github-app-token@v3
      - name: Auslagerung pruefen
        env:
          GH_TOKEN: ${{{{ steps.app_token.outputs.token || secrets.GITHUB_TOKEN }}}}
        run: python3 scripts/checks/handover_auslagerung_check.py
"""


def test_should_flag_soft_step_whose_outputs_feed_the_gate_step_as_value(tmp_path):
    """Positivkontrolle am Realfall: Begruendung vorhanden, Fehlerpfad fehlt."""
    wf = _schreibe(tmp_path, "handover-append-only.yml", _REALFALL_WERT)
    funde = csf.pruefe_datei(wf)
    assert [f.art for f in funde] == ["Absturz bleibt still"], [str(f) for f in funde]
    assert "als Wert" in funde[0].text


def test_should_accept_value_consumption_when_the_outcome_is_handled(tmp_path):
    """Negativkontrolle: derselbe Workflow mit Ausfall-Schritt bleibt still."""
    mit_pfad = _REALFALL_WERT.replace(
        "      - name: Auslagerung pruefen\n",
        "      - name: App-Token-Ausfall melden\n"
        "        if: ${{ steps.app_token.outcome == 'failure' }}\n"
        "        run: exit 1\n"
        "      - name: Auslagerung pruefen\n",
    )
    wf = _schreibe(tmp_path, "gut.yml", mit_pfad)
    assert csf.pruefe_datei(wf) == []


def test_should_flag_outputs_passed_on_as_job_outputs_without_outcome(tmp_path):
    """Job-`outputs` tragen den Wert in andere Jobs — derselbe stille Fallback."""
    wf = _schreibe(
        tmp_path,
        "job_outputs.yml",
        f"""
name: Weitergabe
on: push
jobs:
  messen:
    runs-on: ubuntu-latest
    outputs:
      zahl: ${{{{ steps.meter.outputs.zahl }}}}
    steps:
      # Weichgestellt, damit der Push nicht rot wird.
      - id: meter
        {WEICH}
        run: echo "zahl=3" >> "$GITHUB_OUTPUT"
""",
    )
    assert any(f.art == "Absturz bleibt still" for f in csf.pruefe_datei(wf))


def test_should_not_flag_a_soft_step_whose_outputs_nobody_reads(tmp_path):
    """Negativkontrolle: begruendet weichgestellt, Outputs ungenutzt — kein Fund."""
    wf = _schreibe(
        tmp_path,
        "ungenutzt.yml",
        f"""
name: Ungenutzt
on: push
jobs:
  a:
    runs-on: ubuntu-latest
    steps:
      # Weichgestellt: reiner Hinweis-Schritt, niemand liest seine Outputs.
      - id: hinweis
        {WEICH}
        run: echo hallo
      - name: weiter
        run: echo weiter
""",
    )
    assert csf.pruefe_datei(wf) == []
