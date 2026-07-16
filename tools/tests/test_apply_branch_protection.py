"""Repro-Tests für SEC-1 (Issue #1198, `/repo-optimize` 2026-07-16, live reproduziert).

Befund: `apply_ruleset()` in `tools/apply-branch-protection.sh` UND `apply_one()`
in der Inline-Bash von `.github/workflows/apply-branch-protection.yml` endeten in
JEDEM Zweig mit einem unbedingten `echo "✅ ..."`. Da beide Funktionen im Testkopf
eines `if apply_ruleset ...; then`/`if apply_one ...; then` aufgerufen werden, ist
`set -e` innerhalb wirkungslos — der Rückgabewert der Funktion war der des letzten
Befehls (`echo`, immer 0), nicht der des vorangegangenen `gh api`/`curl`-Aufrufs.
Ein fehlgeschlagener API-Call wurde also fälschlich als "✅ ... angelegt/aktualisiert"
gemeldet UND der Gesamtlauf zählte den Fehlschlag als Erfolg (SUCCESS/ok statt
FAIL/fail).

Diese Tests laufen die Skripte end-to-end via subprocess gegen eine isolierte
Fixture (eigenes governance/rulesets/, kein Bezug zu echten Repos), mit einem
`gh`- bzw. `curl`-PATH-Shim, der einen fehlschlagenden API-Call simuliert. Vor dem
Fix (SEC-1) hätten beide `test_should_report_*_failure_*`-Tests fehlgeschlagen,
weil das Skript trotz simuliertem Fehlschlag Exit-Code 0 + "✅" gemeldet hätte.

Beide Testklassen überspringen sich selbst (`pytest.skip`), wenn `jq` auf der
Testmaschine fehlt (lokale Dev-Sandbox ohne `jq`) — das Skript selbst hart-
requires `jq`, die CI-Laufzeit stellt es bereit (ubuntu-latest/self-hosted).

Run: `python3 -m pytest tools/tests/test_apply_branch_protection.py -q`
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "apply-branch-protection.sh"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "apply-branch-protection.yml"

_TEMPLATE_JSON = (
    '{"_comment": "test", "name": "main-required-checks", "target": "branch", '
    '"enforcement": "active", '
    '"conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}}, '
    '"rules": [{"type": "required_status_checks", "parameters": '
    '{"required_status_checks": [{"context": "__REQUIRED_CHECK__"}], '
    '"strict_required_status_checks_policy": false}}], "bypass_actors": []}'
)
_WAVE1_JSON = '[{"repo": "demo-repo", "owner": "demo-owner", "required_check": "ci"}]'

_GH_SHIM_FAIL_ON_WRITE = """#!/usr/bin/env bash
# Simuliert: GET (Existenz-Check, --jq-gefiltert von echtem `gh`) -> leere
#            Ausgabe (kein bestehendes Ruleset -> POST-Zweig wird genommen).
#            POST/PATCH (Anlegen/Update) -> API-Fehlschlag (z.B. 422/403).
verb="GET"
prev=""
for a in "$@"; do
  if [ "$prev" = "-X" ]; then verb="$a"; fi
  prev="$a"
done
cat >/dev/null || true
if [ "$verb" = "POST" ] || [ "$verb" = "PATCH" ]; then
  echo "gh: HTTP 422: Validation Failed (test-simulated failure)" >&2
  exit 1
fi
# GET: leer -> existing_id bleibt leer (kein Ruleset gefunden)
"""

_GH_SHIM_SUCCEED = """#!/usr/bin/env bash
verb="GET"
prev=""
for a in "$@"; do
  if [ "$prev" = "-X" ]; then verb="$a"; fi
  prev="$a"
done
cat >/dev/null || true
if [ "$verb" = "POST" ]; then
  echo "999"
  exit 0
fi
if [ "$verb" = "PATCH" ]; then
  exit 0
fi
# GET: leer -> existing_id bleibt leer (kein Ruleset gefunden) -> POST-Zweig
"""


def _require_jq() -> None:
    if not shutil.which("jq"):
        pytest.skip("jq nicht auf PATH — Skript requires jq hart (lokale Dev-Sandbox ohne jq)")


def _make_fixture(tmp_path: Path) -> Path:
    """Isolierte Kopie: tools/apply-branch-protection.sh + minimales governance/rulesets/."""
    root = tmp_path / "fixture-repo"
    (root / "tools").mkdir(parents=True)
    (root / "governance" / "rulesets").mkdir(parents=True)
    shutil.copy(SCRIPT, root / "tools" / "apply-branch-protection.sh")
    (root / "tools" / "apply-branch-protection.sh").chmod(0o755)
    (root / "governance" / "rulesets" / "main-required-checks-template.json").write_text(_TEMPLATE_JSON)
    (root / "governance" / "rulesets" / "wave1-repos.json").write_text(_WAVE1_JSON)
    return root


def _make_gh_shim(tmp_path: Path, script_body: str) -> str:
    shim_dir = tmp_path / "shimbin"
    shim_dir.mkdir(exist_ok=True)
    gh_path = shim_dir / "gh"
    gh_path.write_text(script_body)
    gh_path.chmod(0o755)
    return str(shim_dir)


def _run_script(root: Path, shim_dir: str, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    import os

    env = dict(os.environ)
    env["PATH"] = f"{shim_dir}:{env['PATH']}"
    env["GH_TOKEN"] = "fake-token-for-test"
    if extra_env:
        env.update(extra_env)
    bash_bin = shutil.which("bash")
    return subprocess.run(
        [bash_bin, str(root / "tools" / "apply-branch-protection.sh"), "--repo", "demo-repo"],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestLocalScriptFailureReporting:
    """tools/apply-branch-protection.sh — apply_ruleset()."""

    def test_should_report_failure_and_nonzero_exit_when_post_fails(self, tmp_path):
        _require_jq()
        root = _make_fixture(tmp_path)
        shim = _make_gh_shim(tmp_path, _GH_SHIM_FAIL_ON_WRITE)

        res = _run_script(root, shim)

        assert res.returncode != 0, (
            f"SEC-1 Regression: Skript meldet Exit 0 trotz simuliertem API-Fehlschlag.\n"
            f"stdout={res.stdout}\nstderr={res.stderr}"
        )
        assert "✅" not in res.stdout, (
            f"SEC-1 Regression: '✅ ... angelegt' trotz Fehlschlag ausgegeben.\nstdout={res.stdout}"
        )
        assert "❌" in res.stdout
        assert "0/1 Repos erfolgreich" in res.stdout

    def test_should_report_success_when_api_call_succeeds(self, tmp_path):
        """Gegenprobe: Fix darf den Erfolgspfad nicht kaputt machen."""
        _require_jq()
        root = _make_fixture(tmp_path)
        shim = _make_gh_shim(tmp_path, _GH_SHIM_SUCCEED)

        res = _run_script(root, shim)

        assert res.returncode == 0, f"stdout={res.stdout}\nstderr={res.stderr}"
        assert "✅ demo-repo: Ruleset angelegt" in res.stdout
        assert "1/1 Repos erfolgreich" in res.stdout


# ---------------------------------------------------------------------------
# Workflow-Inline-Bash (.github/workflows/apply-branch-protection.yml)
# ---------------------------------------------------------------------------

_CURL_SHIM_FAIL_ON_WRITE = """#!/usr/bin/env bash
# Simuliert curl -sf: GET -> "[]" (kein bestehendes Ruleset).
#                      -X POST/-X PATCH -> Fehlschlag (curl -f Verhalten: nichts
#                      auf stdout, exit != 0), analog einem 422/403 von der API.
verb="GET"
prev=""
for a in "$@"; do
  if [ "$prev" = "-X" ]; then verb="$a"; fi
  prev="$a"
done
if [ "$verb" = "POST" ] || [ "$verb" = "PATCH" ]; then
  exit 22
fi
echo "[]"
"""


def _extract_apply_rulesets_run_step() -> str:
    wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = wf["jobs"]["apply-rulesets"]["steps"]
    for step in steps:
        if step.get("name") == "Apply Rulesets":
            return step["run"]
    raise AssertionError("Step 'Apply Rulesets' nicht in apply-branch-protection.yml gefunden")


def test_should_report_failure_and_nonzero_exit_when_workflow_post_fails(tmp_path):
    """apply_one() in der Workflow-Inline-Bash — derselbe Bug wie im lokalen Skript."""
    _require_jq()
    run_script = _extract_apply_rulesets_run_step()

    root = tmp_path / "wf-fixture"
    (root / "governance" / "rulesets").mkdir(parents=True)
    (root / "governance" / "rulesets" / "main-required-checks-template.json").write_text(_TEMPLATE_JSON)
    (root / "governance" / "rulesets" / "wave1-repos.json").write_text(_WAVE1_JSON)
    script_path = root / "run.sh"
    script_path.write_text(run_script)
    script_path.chmod(0o755)

    shim_dir = tmp_path / "curlshim"
    shim_dir.mkdir()
    curl_path = shim_dir / "curl"
    curl_path.write_text(_CURL_SHIM_FAIL_ON_WRITE)
    curl_path.chmod(0o755)

    import os

    env = dict(os.environ)
    env["PATH"] = f"{shim_dir}:{env['PATH']}"
    env["TOKEN"] = "fake-token-for-test"
    env["TARGET_REPO"] = "demo-repo"
    env["DRY_RUN"] = "false"
    env["WAVE"] = "1"

    bash_bin = shutil.which("bash")
    res = subprocess.run(
        [bash_bin, str(script_path)],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert res.returncode != 0, (
        f"SEC-1 Regression (Workflow): Exit 0 trotz simuliertem curl-Fehlschlag.\n"
        f"stdout={res.stdout}\nstderr={res.stderr}"
    )
    assert "✅" not in res.stdout, f"SEC-1 Regression (Workflow): '✅' trotz Fehlschlag.\nstdout={res.stdout}"
    assert "❌" in res.stdout
