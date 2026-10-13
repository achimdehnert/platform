"""Tests fuer registry/review-risiko.yaml, tools/review_risiko.py und agents/advocatus/* (KONZ-070 WP4).

Drift-Test im CI: PROMPT.md und routine.json muessen dem Render aus den Quellen entsprechen
(`make test` → tools/tests/). Der Klassifikator wird als reine Funktion mit PR-Fixtures
in `gh pr view --json`-Form geprueft; `gh` selbst wird nie aufgerufen.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import review_regeln as rr  # noqa: E402
import review_risiko as rk  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
PILOT = ["achimdehnert/platform", "iilgmbh/risk-hub"]
SHA = "0123456789abcdef0123456789abcdef01234567"


@pytest.fixture(scope="module")
def regeln() -> dict:
    return rr.lade_regeln()


@pytest.fixture(scope="module")
def konfig(regeln) -> dict:
    return rk.lade_risiko(regeln_doc=regeln)


def _pr(**extra) -> dict:
    basis = {
        "number": 17,
        "isDraft": False,
        "author": {"login": "achimdehnert"},
        "headRefOid": SHA,
        "additions": 10,
        "deletions": 2,
        "files": [{"path": "tools/x.py"}],
        "comments": [],
    }
    basis.update(extra)
    return basis


def _diff(pfad: str, *zeilen: str) -> str:
    kopf = f"diff --git a/{pfad} b/{pfad}\n--- a/{pfad}\n+++ b/{pfad}\n@@ -1,1 +1,{len(zeilen)} @@\n"
    return kopf + "".join(f"+{z}\n" for z in zeilen)


def _lauf(konfig, regeln, pr, diff, repo=PILOT[0]):
    return rk.klassifiziere(pr, diff, konfig, regeln, repo, PILOT)


# ───────────────────────── Schema ─────────────────────────────────────────────────────


def test_should_load_committed_risk_file_without_schema_errors(konfig):
    assert konfig["version"] == 1
    assert len(konfig["trigger"]) >= 6
    assert konfig["routine"]["modell"]


def test_should_reject_unknown_art_duplicate_id_and_repeated_pattern(konfig, regeln):
    kaputt = copy.deepcopy(konfig)
    kaputt["trigger"][0]["art"] = "zufall"
    kaputt["trigger"].append(dict(kaputt["trigger"][1]))
    kaputt["trigger"][2]["muster"] = ["x"]
    fehler = rk.pruefe_schema(kaputt, regeln)
    assert any("art 'zufall'" in f for f in fehler)
    assert any("id doppelt" in f for f in fehler)
    assert any("(K1)" in f for f in fehler)


def test_should_reject_unknown_rule_id_and_invalid_regex(konfig, regeln):
    kaputt = copy.deepcopy(konfig)
    kaputt["trigger"][0]["regel_id"] = "RR-999"
    inhalt = next(t for t in kaputt["trigger"] if t["art"] == "inhalt")
    inhalt["muster"] = ["("]
    fehler = rk.pruefe_schema(kaputt, regeln)
    assert any("RR-999 unbekannt" in f for f in fehler)
    assert any("kein gueltiger Regex" in f for f in fehler)


def test_should_raise_schema_error_from_loader(tmp_path):
    p = tmp_path / "risiko.yaml"
    p.write_text("version: 1\n", encoding="utf-8")
    with pytest.raises(rk.SchemaFehler):
        rk.lade_risiko(p)


def test_should_reference_only_rules_without_repeating_their_patterns(konfig, regeln):
    ids = {r["id"] for r in regeln["regeln"]}
    for t in konfig["trigger"]:
        if t["art"] == "regel":
            assert t["regel_id"] in ids
            assert "muster" not in t


# ───────────────────────── Pilot und Profil ──────────────────────────────────────────


def test_should_list_pilot_repos_as_owner_slash_name():
    repos = rk.pilot_repos()
    assert repos and all(r.count("/") == 1 for r in repos)
    assert "achimdehnert/platform" in repos
    for r in repos:
        assert rk.regel_profil(r.split("/")[1]) in rr.PROFILE


# ───────────────────────── Diff-Parser ───────────────────────────────────────────────


def test_should_collect_added_lines_per_file_and_skip_deleted_files():
    diff = (
        _diff("a.py", "x = 1", "y = 2")
        + "diff --git a/b.py b/b.py\n--- a/b.py\n+++ /dev/null\n@@ -1 +0,0 @@\n-gone\n"
        + _diff("c.yml", "permissions:")
    )
    zeilen = rk.hinzugefuegte_zeilen(diff)
    assert zeilen == {"a.py": ["x = 1", "y = 2"], "c.yml": ["permissions:"]}


# ───────────────────────── Klassifikator ─────────────────────────────────────────────


def test_should_not_run_without_any_trigger(konfig, regeln):
    e = _lauf(konfig, regeln, _pr(), _diff("tools/x.py", "print(1)"))
    assert e["laeuft"] is False
    assert e["gruende"] == ["kein Risiko-Trigger"]
    assert e["head_sha"] == SHA


def test_should_run_on_deploy_workflow_via_rule_trigger(konfig, regeln):
    pr = _pr(files=[{"path": ".github/workflows/deploy.yml"}])
    e = _lauf(konfig, regeln, pr, _diff(".github/workflows/deploy.yml", "name: x"))
    assert e["laeuft"] is True
    ids = {t["id"]: t for t in e["trigger"]}
    assert "RK-001" in ids and ids["RK-001"]["regel_id"] == "RR-005"
    assert ".github/workflows/deploy.yml" in ids["RK-001"]["locator"]


def test_should_run_on_migration_path(konfig, regeln):
    pfad = "apps/x/migrations/0002_auto.py"
    e = _lauf(konfig, regeln, _pr(files=[{"path": pfad}]), _diff(pfad, "pass"))
    assert e["laeuft"] and any(t["regel_id"] == "RR-006" for t in e["trigger"])


def test_should_run_on_permissions_block_in_yaml_only(konfig, regeln):
    treffer = _lauf(
        konfig, regeln, _pr(files=[{"path": "ci/job.yml"}]), _diff("ci/job.yml", "permissions:")
    )
    assert any(t["id"] == "RK-007" for t in treffer["trigger"])
    kein = _lauf(
        konfig, regeln, _pr(files=[{"path": "README.md"}]), _diff("README.md", "permissions:")
    )
    assert not any(t["id"] == "RK-007" for t in kein["trigger"])


def test_should_run_on_secret_pattern_in_added_lines(konfig, regeln):
    zeile = "GITHUB_TOKEN = 'ghp_" + "A" * 36 + "'"
    e = _lauf(konfig, regeln, _pr(), _diff("tools/x.py", zeile))
    assert e["laeuft"] and any(t["id"] == "RK-008" for t in e["trigger"])
    assert e["trigger"][0]["locator"] == ["tools/x.py (+1)"]


def test_should_run_on_compose_secret_interpolation_regardless_of_profile(konfig, regeln):
    pfad = "docker-compose.prod.yml"
    e = _lauf(
        konfig, regeln, _pr(files=[{"path": pfad}]), _diff(pfad, "  SECRET_KEY: ${SECRET_KEY}")
    )
    assert any(t["regel_id"] == "RR-021" for t in e["trigger"])


def test_should_run_on_large_diff_via_umfang_rule(konfig, regeln):
    schwelle = next(
        r["detektor"]["max_zeilen"] for r in regeln["regeln"] if r["id"] == "RR-123"
    )
    e = _lauf(konfig, regeln, _pr(additions=schwelle, deletions=1), _diff("tools/x.py", "a"))
    assert any(t["id"] == "RK-006" for t in e["trigger"])
    klein = _lauf(konfig, regeln, _pr(additions=1, deletions=0), _diff("tools/x.py", "a"))
    assert not any(t["id"] == "RK-006" for t in klein["trigger"])


def test_should_not_run_for_draft_excluded_author_or_foreign_repo(konfig, regeln):
    diff = _diff(".github/workflows/deploy.yml", "x")
    pr = _pr(files=[{"path": ".github/workflows/deploy.yml"}])
    assert "Draft" in _lauf(konfig, regeln, {**pr, "isDraft": True}, diff)["gruende"]
    bot = _lauf(konfig, regeln, {**pr, "author": {"login": "app/dependabot"}}, diff)
    assert any("Autor ausgeschlossen" in g for g in bot["gruende"])
    fremd = _lauf(konfig, regeln, pr, diff, repo="achimdehnert/nicht-pilot")
    assert fremd["laeuft"] is False and any("nicht im Pilot" in g for g in fremd["gruende"])


def test_should_not_run_twice_on_same_head_sha(konfig, regeln):
    diff = _diff(".github/workflows/deploy.yml", "x")
    marker = f"<!-- {konfig['routine']['dedup_marker']}:{SHA} -->"
    pr = _pr(
        files=[{"path": ".github/workflows/deploy.yml"}],
        comments=[{"body": marker + "\nAdvocatus …"}],
    )
    e = _lauf(konfig, regeln, pr, diff)
    assert e["laeuft"] is False and any("Marker vorhanden" in g for g in e["gruende"])
    alt = {**pr, "comments": [{"body": f"<!-- advocatus:{'f' * 40} -->"}]}
    assert _lauf(konfig, regeln, alt, diff)["laeuft"] is True


# ───────────────────────── Routine-Artefakte und Drift ───────────────────────────────


def test_should_render_prompt_without_open_placeholders_and_with_footer(konfig, regeln):
    text = rk.render_prompt(konfig, regeln)
    assert "{{" not in text
    assert rk.MARK in text and "content_hash=sha256:" in text
    assert konfig["routine"]["modell"] in text
    assert konfig["routine"]["token_env"] in text
    for r in rr.regeln_fuer("advocatus", regeln):
        assert f"`{r['id']}`" in text
    for t in konfig["trigger"]:
        assert f"`{t['id']}`" in text


def test_should_render_routine_body_in_trigger_api_shape(konfig):
    body = json.loads(rk.render_routine(konfig))
    r = konfig["routine"]
    assert body["name"] == r["name"] and body["cron_expression"] == r["cron"]
    ccr = body["job_config"]["ccr"]
    assert ccr["environment_id"] == rk.ENVIRONMENT_PLATZHALTER
    assert ccr["session_context"]["model"] == r["modell"]
    assert ccr["session_context"]["sources"] == [{"git_repository": {"url": r["checkout"]}}]
    ev = ccr["events"][0]["data"]
    assert ev["type"] == "user" and ev["message"]["role"] == "user"
    assert "agents/advocatus/PROMPT.md" in ev["message"]["content"]
    assert r["token_env"] in ev["message"]["content"]


def test_should_keep_model_id_in_exactly_one_place(konfig):
    modell = konfig["routine"]["modell"]
    for p in (REPO / "tools" / "review_risiko.py", REPO / "tools" / "advocatus_ledger_post.py",
              REPO / "agents" / "advocatus" / "PROMPT.template.md"):
        assert modell not in p.read_text(encoding="utf-8"), p


def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO / "tools" / "review_risiko.py"), *args],
        capture_output=True,
        text=True,
    )


def test_should_pass_check_against_committed_state():
    assert rk.pruefe_drift() == []
    lauf = _cli("--check")
    assert lauf.returncode == 0, lauf.stderr
    assert "kein Drift" in lauf.stdout


def test_should_detect_drift_when_rendered_files_are_hand_edited(tmp_path):
    md = tmp_path / "PROMPT.md"
    md.write_text(rk.PROMPT_MD.read_text(encoding="utf-8").replace("advisory", "entscheidend"))
    js = tmp_path / "routine.json"
    js.write_text(rk.ROUTINE_JSON.read_text(encoding="utf-8").replace('"enabled": true', '"enabled": false'))
    befunde = rk.pruefe_drift(md, js)
    assert len(befunde) == 2 and all("--render" in b for b in befunde)


def test_should_render_then_check_clean_on_a_copy(tmp_path, konfig, regeln):
    md, js = tmp_path / "PROMPT.md", tmp_path / "routine.json"
    md.write_text(rk.render_prompt(konfig, regeln), encoding="utf-8")
    js.write_text(rk.render_routine(konfig), encoding="utf-8")
    assert rk.pruefe_drift(md, js) == []


def test_should_list_pilot_repos_via_cli():
    lauf = _cli("--repos")
    assert lauf.returncode == 0
    assert "achimdehnert/platform" in lauf.stdout.splitlines()


def test_should_exit_zero_when_advocatus_runs_and_one_otherwise(monkeypatch, capsys):
    pr = _pr(files=[{"path": ".github/workflows/deploy.yml"}])
    monkeypatch.setattr(rk, "pilot_repos", lambda: PILOT)
    monkeypatch.setattr(rk, "regel_profil", lambda name: "default")
    monkeypatch.setattr(
        rk, "pr_laden", lambda repo, nr: (pr, _diff(".github/workflows/deploy.yml", "x"))
    )
    assert rk.main(["--repo", PILOT[0], "--pr", "17", "--json"]) == 0
    aus = json.loads(capsys.readouterr().out)
    assert aus["laeuft"] and aus["regel_profil"] == "default"
    assert aus["trigger"][0]["id"] == "RK-001"

    monkeypatch.setattr(rk, "pr_laden", lambda repo, nr: (_pr(), _diff("tools/x.py", "y")))
    assert rk.main(["--repo", PILOT[0], "--pr", "18"]) == 1
    assert "kein Risiko-Trigger" in capsys.readouterr().out
