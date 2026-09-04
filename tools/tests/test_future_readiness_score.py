"""Deterministischer Future-Readiness-Bewerter: Formeln, Schema, Schluessel, Zustaende.

Fixture ist synthetisch (kein echtes Repo, keine Secrets): ein kleines Paket im Format von
tools/future_readiness_evidence.py. Invarianten statt Stichproben, wo es geht.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCORE = ROOT / "tools" / "future_readiness_score.py"
sys.path.insert(0, str(ROOT / "tools"))
import future_readiness_rubric as rubric  # noqa: E402

jsonschema = pytest.importorskip("jsonschema")


def _pack(**over):
    base = {
        "schema": "future-readiness-evidence/1",
        "repo": "example/repo",
        "analyzed_sha": "a" * 40,
        "default_branch": "main",
        "analyzed_at": "2026-09-03T08:00:00Z",
        "truncated": False,
        "parts": {
            "repo": {
                "visibility": "private",
                "security_and_analysis": {
                    "secret_scanning": {"status": "enabled"},
                    "secret_scanning_push_protection": {"status": "enabled"},
                    "dependabot_security_updates": {"status": "disabled"},
                },
            },
            "rules_default_branch": [
                {
                    "type": "required_status_checks",
                    "parameters": {
                        "required_status_checks": [
                            {"context": "pytest"},
                            {"context": "gitleaks"},
                        ]
                    },
                },
                {
                    "type": "pull_request",
                    "parameters": {
                        "required_approving_review_count": 0,
                        "require_code_owner_review": True,
                    },
                },
            ],
            "classic_protection": "absent_404",
            "dependabot_alerts_api": {
                "endpoint": "x",
                "exit_code": 1,
                "body_head": "Dependabot alerts are disabled",
                "stderr": "HTTP 403",
            },
            "code_scanning_api": {
                "endpoint": "x",
                "exit_code": 1,
                "body_head": "no analysis found",
                "stderr": "HTTP 404",
            },
            "files": {
                n: "-"
                for n in (
                    "README.md",
                    "SECURITY.md",
                    "CLAUDE.md",
                    "LICENSE",
                    ".github/CODEOWNERS",
                    "CHANGELOG.md",
                    "Makefile",
                    ".pre-commit-config.yaml",
                    ".env.example",
                    ".python-version",
                    "uv.lock",
                    "Dockerfile",
                    "NOTICE",
                    "THIRD_PARTY_NOTICES.md",
                )
            }
            | {"README.md": "+", "Makefile": "+", "LICENSE": "+", "CLAUDE.md": "+"},
            "requirements_files_tracked": ["requirements.txt"],
            "manifests": {"requirements.txt": {"entries": 4, "versioned_entries": 4}},
            "pyproject": {"exists": False},
            "dependabot_yml": 'package-ecosystem: "pip"\ninterval: "weekly"',
            "test_file_count": 12,
            "python_pins_in_workflows": {"3.12": 2},
            "endoflife_python": [
                {"cycle": "3.12", "eol": "2028-10-31"},
                {"cycle": "3.13", "eol": "2029-10-31"},
            ],
            "endoflife_checked_at": "2026-09-03T08:00:00Z",
            "readme": {"first_paragraph": "Ein Repo.", "setup_section": "12:## Setup"},
            "workflows_active": [".github/workflows/ci.yml"],
            "composite_actions": [],
            "workflow_table": [
                {
                    "path": ".github/workflows/ci.yml",
                    "on": ["push", "pull_request"],
                    "workflow_call": False,
                    "secrets_or_ssh": True,
                    "top_level_permissions": {"contents": "read"},
                    "job_level_permissions": {},
                    "third_party_uses": [
                        "actions/checkout@v7",
                        "actions/setup-python@v7",
                    ],
                    "third_party_sha_pinned": [],
                    "first_party_uses": [],
                    "first_party_versioned": [],
                    "pull_request_target_or_workflow_run": False,
                    "pull_request_target_with_checkout_of_pr_head": False,
                }
            ],
            "ci_jobs": [
                {
                    "workflow": ".github/workflows/ci.yml",
                    "job": "test",
                    "tools": ["pytest", "ruff"],
                    "calls_reusable": None,
                    "executed_for_this_repo": True,
                    "on": ["push", "pull_request"],
                }
            ],
            "uses_summary": {
                "third_party_total": 2,
                "third_party_sha_pinned": 0,
                "first_party_total": 0,
                "first_party_versioned": 0,
            },
            "ci_runs_by_workflow_path": {
                ".github/workflows/ci.yml": [
                    {
                        "conclusion": "success",
                        "status": "completed",
                        "created_at": "2026-09-03T07:00:00Z",
                        "event": "push",
                    }
                ]
            },
            "test_workflows": [".github/workflows/ci.yml"],
            "negative_list": {
                "unverified": {},
                "not_run_at_depth": {"D02.4": "Scanner"},
            },
        },
    }
    base["parts"].update(over)
    return base


def _run(tmp_path, pack, *extra):
    ev = tmp_path / "evidence.json"
    ev.write_text(json.dumps(pack), encoding="utf-8")
    out = tmp_path / "result.json"
    r = subprocess.run(
        [
            sys.executable,
            str(SCORE),
            str(ev),
            "--out",
            str(out),
            "--archetype",
            "python-package",
            "--run-date",
            "2026-09-03",
            "--prod-deploy",
            "true",
            *extra,
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    return json.loads(out.read_text(encoding="utf-8"))


def test_should_produce_schema_valid_result(tmp_path):
    res = _run(tmp_path, _pack())
    errs = list(jsonschema.Draft202012Validator(rubric.schema()).iter_errors(res))
    assert errs == []


def test_should_compute_readiness_from_question_scores(tmp_path):
    res = _run(tmp_path, _pack())
    W = {d: w for d, (_, w) in rubric.DIMS.items()}
    for d, o in res["weights_override"].items():
        W[d] = o["weight"]
    num = den = 0
    for d, s in res["scores"].items():
        qs = [
            q["question_score"]
            for q in s["questions"].values()
            if q["state"] == "answered"
        ]
        appl = [q for q in s["questions"].values() if q["state"] != "not_applicable"]
        exp = (
            None
            if not appl or len(qs) < 0.5 * len(appl)
            else int(math.floor(sum(qs) / len(qs) + 0.5))
        )
        assert s["score"] == exp, d
        if exp is not None:
            num += W[d] * exp
            den += W[d]
    assert res["readiness"] == int(math.floor(num / den / 5 * 100 + 0.5))
    assert (
        res["calculation"]["weighted_score_sum"] == num
        and res["calculation"]["scored_weight_sum"] == den
    )


def test_should_hash_keys_from_locator_and_emit_only_on_fail_or_partial(tmp_path):
    res = _run(tmp_path, _pack())
    for f in res["findings"]:
        assert f["key"].endswith(hashlib.sha256(f["locator"].encode()).hexdigest()[:8])
        q = res["scores"][f["dimension"]]["questions"][f["question_id"]]
        assert q["state"] == "answered" and q["outcome"] in ("fail", "partial")
    keys = [f["key"] for f in res["findings"]]
    assert keys == sorted(keys) and len(keys) == len(set(keys))


def test_should_mark_pinning_p1_when_secrets_workflow_unpinned(tmp_path):
    res = _run(tmp_path, _pack())
    pin = next(f for f in res["findings"] if f["question_id"] == "D06.6")
    assert pin["severity"] == "P1"
    alerts = next(f for f in res["findings"] if f["question_id"] == "D06.3")
    assert alerts["severity"] == "P1"  # BASIC_SECURITY_CONTROL fail + HAS_PROD_DEPLOY


def test_should_keep_open_states_without_outcome_and_apply_matrix(tmp_path):
    res = _run(tmp_path, _pack())
    for d, s in res["scores"].items():
        for qid, q in s["questions"].items():
            if q["state"] != "answered":
                assert "outcome" not in q and q["note"]
    na = {q[0] for q in rubric.Q if "python-package" in q[6]}
    for qid in na:
        assert (
            res["scores"][qid.split(".")[0]]["questions"][qid]["state"]
            == "not_applicable"
        )
    assert res["scores"]["D02"]["questions"]["D02.4"]["state"] == "not_run_at_depth"


def test_should_read_review_rule_unambiguously(tmp_path):
    res = _run(tmp_path, _pack())
    q = res["scores"]["D05"]["questions"]["D05.2"]
    assert q["outcome"] == "partial"  # 0 approvals + codeowner
    ok = _run(
        tmp_path,
        _pack(
            rules_default_branch=[
                {
                    "type": "pull_request",
                    "parameters": {
                        "required_approving_review_count": 1,
                        "require_code_owner_review": False,
                    },
                }
            ]
        ),
    )
    assert ok["scores"]["D05"]["questions"]["D05.2"]["outcome"] == "ok"


def test_should_emit_checked_names_as_locator_when_no_manifest(tmp_path):
    # Phase C 2026-09-03: 11 Repos ohne Manifest brachen am Schema ab, weil der
    # D02.1-Locator hinter dem dritten `|` leer blieb (#2780).
    res = _run(
        tmp_path,
        _pack(requirements_files_tracked=[], manifests={}, pyproject={"exists": False}),
    )
    errs = list(jsonschema.Draft202012Validator(rubric.schema()).iter_errors(res))
    assert errs == []
    f = next(f for f in res["findings"] if f["question_id"] == "D02.1")
    assert f["locator"] == "D02.1|manifest|pyproject.toml;requirements.txt"


def _sec_state(res, control):
    return res["controls"][control]["state"]


def test_should_call_missing_security_block_plan_unavailable_for_private_user_repo(
    tmp_path,
):
    # Regel 34 (v2.4): 27 der 56 Phase-C-Repos lieferten security_and_analysis=null.
    # Privates Repo unter einem Personenkonto -> die Funktion gibt es im Plan nicht.
    res = _run(
        tmp_path,
        _pack(
            repo={
                "visibility": "private",
                "owner_type": "User",
                "security_and_analysis": None,
            }
        ),
    )
    assert _sec_state(res, "secret_scanning") == "plan_unavailable"
    assert _sec_state(res, "push_protection") == "plan_unavailable"
    q = res["scores"]["D06"]["questions"]["D06.1"]
    assert q["state"] == "unverified" and "nicht im Plan" in q["note"]


def test_should_call_missing_security_block_no_permission_for_org_repo(tmp_path):
    res = _run(
        tmp_path,
        _pack(
            repo={
                "visibility": "private",
                "owner_type": "Organization",
                "security_and_analysis": None,
            }
        ),
    )
    assert _sec_state(res, "secret_scanning") == "no_permission"


def test_should_stay_unknown_when_owner_type_is_missing_from_the_pack(tmp_path):
    # Ohne owner_type wird nicht geraten — die alten Pakete bleiben unknown.
    res = _run(
        tmp_path,
        _pack(repo={"visibility": "private", "security_and_analysis": None}),
    )
    assert _sec_state(res, "secret_scanning") == "unknown"
    assert res["scores"]["D06"]["questions"]["D06.1"]["state"] == "unverified"


def test_should_fail_d02_1_on_an_empty_manifest_instead_of_unverified(tmp_path):
    # Regel 25/30 (v2.4): vorhandenes, aber leeres Manifest ist ein Befund.
    res = _run(
        tmp_path,
        _pack(
            requirements_files_tracked=["requirements.txt"],
            manifests={"requirements.txt": {"entries": 0, "versioned_entries": 0}},
            pyproject={"exists": False},
        ),
    )
    q = res["scores"]["D02"]["questions"]["D02.1"]
    assert q["state"] == "answered" and q["outcome"] == "fail"
    assert any(f["question_id"] == "D02.1" for f in res["findings"])
    errs = list(jsonschema.Draft202012Validator(rubric.schema()).iter_errors(res))
    assert errs == []
