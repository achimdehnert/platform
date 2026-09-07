"""Deterministischer Future-Readiness-Bewerter: Formeln, Schema, Schluessel, Zustaende.

Fixture ist synthetisch (kein echtes Repo, keine Secrets): ein kleines Paket im Format von
tools/future_readiness_evidence.py. Invarianten statt Stichproben, wo es geht.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCORE = ROOT / "tools" / "future_readiness_score.py"
AUDIT_PROMPT = ROOT / "docs" / "prompts" / "future-readiness-audit.md"
sys.path.insert(0, str(ROOT / "tools"))
import future_readiness_evidence as evidence  # noqa: E402
import future_readiness_rubric as rubric  # noqa: E402
import future_readiness_score as score_mod  # noqa: E402

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
        gewertet = appl and (
            len(qs) >= rubric.SCORE_MIN_ANSWERED
            or len(qs) >= rubric.SCORE_MIN_SHARE * len(appl)
        )
        exp = int(math.floor(sum(qs) / len(qs) + 0.5)) if gewertet else None
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


def _d06_blind(**over) -> dict:
    """Paket, in dem die D06-Einstellungsfragen keinen Zustand hergeben.

    security_and_analysis fehlt, Dependabot- und Code-Scanning-Endpunkt antworten mit
    403 ohne semantischen Body -> D06.1-D06.5 bleiben `unverified`. Uebrig bleiben die
    Workflow-Fragen. D06 hat 13 anwendbare Fragen; die Faelle unten liegen damit ALLE
    unter 50 % und trennen die neue 3-answered-Bedingung sauber von der Anteilsregel.
    """
    return _pack(
        repo={"visibility": "private", "security_and_analysis": None},
        dependabot_alerts_api={
            "endpoint": "x",
            "exit_code": 1,
            "body_head": "",
            "stderr": "HTTP 403",
        },
        code_scanning_api={
            "endpoint": "x",
            "exit_code": 1,
            "body_head": "",
            "stderr": "HTTP 403",
        },
        **over,
    )


def _d06(res: dict) -> tuple[list[str], list[str], object]:
    s = res["scores"]["D06"]
    ans = [q for q, v in s["questions"].items() if v["state"] == "answered"]
    appl = [q for q, v in s["questions"].items() if v["state"] != "not_applicable"]
    return ans, appl, s["score"]


def test_should_score_a_dimension_with_three_answered_questions(tmp_path):
    # Regel 37a (v2.4, Owner-Wort 2026-09-04): drei beantwortete Fragen oeffnen die
    # Dimension, auch wenn der Anteil unter 50 % liegt. Anlass: D06 (Gewicht 15) fiel
    # bei dev-hub mit 6 von 13 answered ganz aus dem Score.
    assert rubric.SCORE_MIN_ANSWERED == 3 and rubric.SCORE_MIN_SHARE == 0.5
    ans, appl, score = _d06(_run(tmp_path, _d06_blind()))
    assert len(ans) == 3 and len(appl) == 13
    assert len(ans) < rubric.SCORE_MIN_SHARE * len(
        appl
    )  # die Anteilsregel traegt nicht
    assert score is not None


def test_should_not_score_a_dimension_with_two_answered_questions(tmp_path):
    # Zwei answered von 13: weder drei answered noch 50 % — bleibt gesperrt.
    ohne_third_party = json.loads(json.dumps(_pack()["parts"]["workflow_table"]))
    ohne_third_party[0]["third_party_uses"] = []
    ohne_third_party[0]["third_party_sha_pinned"] = []
    res = _run(
        tmp_path,
        _d06_blind(
            workflow_table=ohne_third_party,
            uses_summary={
                "third_party_total": 0,
                "third_party_sha_pinned": 0,
                "first_party_total": 0,
                "first_party_versioned": 0,
            },
        ),
    )
    ans, appl, score = _d06(res)
    assert len(ans) == 2 and len(appl) == 13
    assert score is None
    assert res["scores"]["D06"]["coverage"] is not None  # Coverage bleibt


def test_should_keep_scoring_by_the_share_rule_when_fewer_than_three_are_answered(
    tmp_path,
):
    # Die Anteilsregel bleibt gueltig und ist die einzige, die bei kleinen
    # Dimensionen (weniger als drei anwendbare Fragen) ueberhaupt greifen kann.
    res = _run(tmp_path, _pack())
    geprueft = 0
    for d, s in res["scores"].items():
        appl = [q for q in s["questions"].values() if q["state"] != "not_applicable"]
        ans = [q for q in appl if q["state"] == "answered"]
        if appl and len(ans) < rubric.SCORE_MIN_ANSWERED:
            geprueft += 1
            erwartet = len(ans) >= rubric.SCORE_MIN_SHARE * len(appl)
            assert (s["score"] is not None) == erwartet, d
    assert geprueft, "keine Dimension unter der 3-answered-Grenze im Fixture"


# ---- R1: D02.1 zaehlt [project.optional-dependencies] mit (v2.5, platform#2737 Frage 2) --


def test_should_count_optional_dependencies_as_manifest_entries(tmp_path):
    # iil-enrichment/iil-ingest/nl2cad (#2737): dependencies bleibt leer, alles liegt
    # in Extras-Gruppen — das darf nicht mehr als "leeres Manifest" durchfallen.
    (tmp_path / "pyproject.toml").write_text(
        "[project]\n"
        'name = "iil-enrichment"\n'
        'requires-python = ">=3.11"\n'
        "dependencies = []\n"
        "\n"
        "[project.optional-dependencies]\n"
        'core = ["httpx>=0.27", "pydantic>=2.0"]\n'
        'dev = ["pytest>=8.0", "ruff"]\n'
        'all = ["iil-enrichment[core,dev]"]\n',
        encoding="utf-8",
    )
    p = evidence.pyproject_ops(str(tmp_path))
    assert p["exists"] and p["project_table"]
    assert p["dependencies"]["entries"] == 4  # httpx, pydantic, pytest, ruff
    assert p["dependencies"]["versioned_entries"] == 3  # ruff ist unversioniert
    assert p["optional_entries"] == 4


def test_should_not_double_count_a_self_referencing_extras_group(tmp_path):
    # all = ["pkg[a,b]"] referenziert nur eigene Extras — kein zusaetzlicher Eintrag.
    (tmp_path / "pyproject.toml").write_text(
        "[project]\n"
        'name = "nl2cad"\n'
        "dependencies = []\n"
        "\n"
        "[project.optional-dependencies]\n"
        'a = ["requests>=2.0"]\n'
        'b = ["click"]\n'
        'all = ["nl2cad[a,b]"]\n',
        encoding="utf-8",
    )
    p = evidence.pyproject_ops(str(tmp_path))
    assert p["dependencies"]["entries"] == 2  # requests, click — nicht 3
    assert p["optional_entries"] == 2


def test_should_dedupe_optional_entries_repeated_across_groups(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "[project]\n"
        'name = "pkg"\n'
        "dependencies = []\n"
        "\n"
        "[project.optional-dependencies]\n"
        'dev = ["pytest>=8.0"]\n'
        'test = ["pytest>=8.0"]\n',
        encoding="utf-8",
    )
    p = evidence.pyproject_ops(str(tmp_path))
    assert p["dependencies"]["entries"] == 1
    assert p["optional_entries"] == 1


def test_should_treat_pyproject_without_project_table_as_no_manifest(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["setuptools"]\n\n[tool.ruff]\nline-length = 100\n',
        encoding="utf-8",
    )
    p = evidence.pyproject_ops(str(tmp_path))
    assert p["exists"] and not p["project_table"]
    assert p["dependencies"] is None  # KEIN Manifest, nicht "leeres Manifest"
    res = _run(
        tmp_path,
        _pack(requirements_files_tracked=[], manifests={}, pyproject=p),
    )
    q = res["scores"]["D02"]["questions"]["D02.1"]
    assert q["state"] == "answered" and q["outcome"] == "fail"
    assert q["evidence"][0]["ref"].startswith("kein Manifest")


# ---- R2: D11.2 not_applicable ohne Abhaengigkeits-Manifest (v2.5, platform#2737 Frage 3) --


def test_should_mark_third_party_notices_not_applicable_without_manifest(tmp_path):
    res = _run(
        tmp_path,
        _pack(requirements_files_tracked=[], manifests={}, pyproject={"exists": False}),
    )
    q = res["scores"]["D11"]["questions"]["D11.2"]
    assert q["state"] == "not_applicable"
    assert "v2.5" in q["note"]
    assert not any(f["question_id"] == "D11.2" for f in res["findings"])
    errs = list(jsonschema.Draft202012Validator(rubric.schema()).iter_errors(res))
    assert errs == []


def test_should_keep_third_party_notices_fail_when_manifest_has_entries(tmp_path):
    # Baseline-Pack: requirements.txt mit 4 Eintraegen, NOTICE/THIRD_PARTY_NOTICES.md
    # beide abwesend -> D11.2 bleibt ein echter fail, kein n/a.
    res = _run(tmp_path, _pack())
    q = res["scores"]["D11"]["questions"]["D11.2"]
    assert q["state"] == "answered" and q["outcome"] == "fail"


# ---- R3: Etikett aus RUBRIC_VERSION-Konstante (platform#2876) -----------------------


def test_should_label_result_with_rubric_version_constant_by_default(tmp_path):
    res = _run(tmp_path, _pack())
    assert res["rubric_version"] == f"{score_mod.RUBRIC_VERSION}-2026-09-03"


def test_should_warn_on_stderr_when_rubric_version_is_overridden(tmp_path):
    ev = tmp_path / "evidence.json"
    ev.write_text(json.dumps(_pack()), encoding="utf-8")
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
            "--rubric-version",
            "9.9-custom",
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    assert "WARNUNG" in r.stderr and "RUBRIC_VERSION" in r.stderr
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["rubric_version"] == "9.9-custom"


def test_should_keep_doc_header_version_in_sync_with_rubric_version_constant():
    # Synchrontest platform#2876: der Kopf von docs/prompts/future-readiness-audit.md
    # (z.B. "Master-Prompt v2.5") muss dieselbe Versionsnummer tragen wie die
    # RUBRIC_VERSION-Konstante im Bewerter — sonst laufen Doku und Code auseinander.
    head = AUDIT_PROMPT.read_text(encoding="utf-8").splitlines()[0]
    m = re.search(r"Master-Prompt v(\d+\.\d+)", head)
    assert m, head
    assert m.group(1) == score_mod.RUBRIC_VERSION


# ---- D10-Ausbau: D10.2-D10.6 statt Negativliste (Auftrag 2026-09-07, platform#2944) --

_EMPTY_MARKERS = {
    "verbotene_pfade": [],
    "generierte_dateien": [],
    "definition_of_done": [],
    "cross_repo_vertraege": [],
}


def _agent_doc(**over):
    d = {
        "headings": ["# CLAUDE"],
        "code_block_count": 0,
        "code_block_first_lines": [],
        "marker_lines": dict(_EMPTY_MARKERS),
        "lines_taken": 1,
        "capped": False,
        "size_lines": 5,
    }
    d.update(over)
    return d


def test_should_mark_d10_2_ok_when_a_documented_command_matches_a_real_make_target(
    tmp_path,
):
    # Gruen: der Befehl "make test" verweist auf ein tatsaechlich vorhandenes
    # Makefile-Target — die einzige generische Gegenprobe ohne Ausfuehrung.
    res = _run(
        tmp_path,
        _pack(
            make_targets=["test", "lint"],
            agent_docs={
                "CLAUDE.md": _agent_doc(
                    code_block_count=1, code_block_first_lines=["make test"]
                )
            },
        ),
    )
    q = res["scores"]["D10"]["questions"]["D10.2"]
    assert q["state"] == "answered" and q["outcome"] == "ok"
    assert "make test" in q["evidence"][0]["ref"]


def test_should_mark_d10_2_partial_when_command_documented_but_not_verified(tmp_path):
    # Gelb: ein Codeblock mit Befehl ist da, aber "make deploy" ist kein reales
    # Makefile-Target -> dokumentiert, nicht verifiziert. Kein Finding (PARTIAL_NO_FINDING).
    res = _run(
        tmp_path,
        _pack(
            make_targets=["test"],
            agent_docs={
                "CLAUDE.md": _agent_doc(
                    code_block_count=1, code_block_first_lines=["make deploy"]
                )
            },
        ),
    )
    q = res["scores"]["D10"]["questions"]["D10.2"]
    assert q["state"] == "answered" and q["outcome"] == "partial"
    assert q["note"] == "documented, nicht verified"
    assert not any(f["question_id"] == "D10.2" for f in res["findings"])


def test_should_mark_d10_2_fail_when_agent_doc_has_no_code_blocks(tmp_path):
    # Rot: CLAUDE.md existiert, aber keine Codebloecke -> keine Befehle.
    res = _run(tmp_path, _pack(agent_docs={"CLAUDE.md": _agent_doc()}))
    q = res["scores"]["D10"]["questions"]["D10.2"]
    assert q["state"] == "answered" and q["outcome"] == "fail"


@pytest.mark.parametrize(
    ("qid", "marker_key", "hit_line"),
    [
        ("D10.3", "verbotene_pfade", "NIE `secrets/` anfassen"),
        ("D10.4", "generierte_dateien", "docs/api.md ist auto-generated"),
        ("D10.5", "definition_of_done", "## Definition of Done"),
        ("D10.6", "cross_repo_vertraege", "Schema-Vertrag mit einem anderen Repo"),
    ],
)
def test_should_mark_d10_3_to_6_ok_on_marker_hit(tmp_path, qid, marker_key, hit_line):
    markers = dict(_EMPTY_MARKERS)
    markers[marker_key] = [hit_line]
    res = _run(
        tmp_path, _pack(agent_docs={"CLAUDE.md": _agent_doc(marker_lines=markers)})
    )
    q = res["scores"]["D10"]["questions"][qid]
    assert q["state"] == "answered" and q["outcome"] == "ok"


@pytest.mark.parametrize("qid", ["D10.3", "D10.4", "D10.5", "D10.6"])
def test_should_mark_d10_3_to_6_fail_without_marker_hit(tmp_path, qid):
    res = _run(tmp_path, _pack(agent_docs={"CLAUDE.md": _agent_doc()}))
    q = res["scores"]["D10"]["questions"][qid]
    assert q["state"] == "answered" and q["outcome"] == "fail"


def test_should_answer_d10_2_to_6_even_without_any_agent_doc(tmp_path):
    # CLAUDE.md/AGENTS.md fehlen komplett (D10.1 fail) -> D10.2-D10.6 sind trotzdem
    # beantwortet (fail), nicht mehr in der Negativliste.
    pack = _pack()
    pack["parts"]["files"] = {
        **pack["parts"]["files"],
        "CLAUDE.md": "-",
        "AGENTS.md": "-",
    }
    res = _run(tmp_path, pack)
    for qid in ("D10.1", "D10.2", "D10.3", "D10.4", "D10.5", "D10.6"):
        q = res["scores"]["D10"]["questions"][qid]
        assert q["state"] == "answered" and q["outcome"] == "fail", qid


def test_should_take_d10_2_to_6_off_the_unverified_negative_list_in_evidence():
    unverified = {
        **{q: evidence.NEG_JUDGMENT_NOTE for q in evidence.NEG_JUDGMENT_QUESTIONS},
        **evidence.NEG_EXTERNAL_METER_NOTES,
        **{
            q: evidence.NEG_NOT_COLLECTED_NOTE
            for q in evidence.NEG_NOT_COLLECTED_QUESTIONS
        },
    }
    assert not ({"D10.2", "D10.3", "D10.4", "D10.5", "D10.6"} & unverified.keys())


def test_should_distinguish_the_negative_list_reason_classes():
    """Drei Klassen statt eines Pauschalsatzes — jede mit eigenem Wortlaut.

    Urteilsfrage (D03), externer Melder (mit Werkzeugnamen) und "schlicht nicht
    erhoben" (Rest). D12.1 brauchte zwei Korrekturen: erst war es faelschlich
    handover_fleet_check.py (misst den Handover-Zustand), dann "kein Werkzeug
    vorhanden" — auch falsch, tools/sharedci/pin_landschaft.py misst genau die
    gepinnte shared-ci-Version je Repo. Uebersehen, weil die Suche nur tools/*.py
    abdeckte und keine Unterverzeichnisse.
    """
    judgment = evidence.NEG_JUDGMENT_NOTE
    not_collected = evidence.NEG_NOT_COLLECTED_NOTE
    meter_notes = evidence.NEG_EXTERNAL_METER_NOTES
    assert judgment != not_collected
    assert all(judgment != n and not_collected != n for n in meter_notes.values())
    assert len(set(meter_notes.values())) == len(meter_notes)  # je Frage ihr Werkzeug
    for qid in evidence.NEG_JUDGMENT_QUESTIONS:
        assert qid.startswith("D03.")
    assert "platform#2944" in judgment
    tool_by_qid = {
        "D07.1": "erreichbarkeit_melder.py",
        "D07.4": "alarmweg_probe.py",
        "D07.6": "backup_meter.py",
        "D12.2": "sync_drift_meter.py",
        "D12.1": "sharedci/pin_landschaft.py",
    }
    for qid, tool in tool_by_qid.items():
        assert tool in meter_notes[qid] and "platform#2944" in meter_notes[qid]

    for qid in evidence.NEG_NOT_COLLECTED_QUESTIONS:
        assert (
            qid not in evidence.NEG_JUDGMENT_QUESTIONS
            and qid not in evidence.NEG_EXTERNAL_METER_NOTES
        )


# ---- agent_doc_digest(): begrenzte Struktur je Agent-Doku (D10.2-D10.6) -------------


def test_should_extract_all_headings_not_only_the_first_twelve(tmp_path):
    lines = [f"## Abschnitt {i}" for i in range(1, 20)]
    (tmp_path / "CLAUDE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    d = evidence.agent_doc_digest(str(tmp_path), "CLAUDE.md")
    assert len(d["headings"]) == 19
    assert d["headings"][-1] == "## Abschnitt 19"


def test_should_extract_the_first_line_of_each_code_block_as_the_command(tmp_path):
    content = (
        "# Doku\n\n"
        "```bash\nmake test\necho done\n```\n\n"
        "```bash\nruff check tools/\n```\n"
    )
    (tmp_path / "CLAUDE.md").write_text(content, encoding="utf-8")
    d = evidence.agent_doc_digest(str(tmp_path), "CLAUDE.md")
    assert d["code_block_count"] == 2
    assert d["code_block_first_lines"] == ["make test", "ruff check tools/"]


def test_should_redact_secrets_in_extracted_command_lines(tmp_path):
    content = "# Setup\n```bash\nexport TOKEN=abc123secret\n```\n"
    (tmp_path / "CLAUDE.md").write_text(content, encoding="utf-8")
    d = evidence.agent_doc_digest(str(tmp_path), "CLAUDE.md")
    assert "abc123secret" not in d["code_block_first_lines"][0]
    assert "<redigiert>" in d["code_block_first_lines"][0]


def test_should_cap_total_extracted_lines_and_flag_it(tmp_path):
    lines = [f"### h{i}" for i in range(500)]
    (tmp_path / "CLAUDE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    d = evidence.agent_doc_digest(str(tmp_path), "CLAUDE.md")
    assert d["size_lines"] == 500
    assert d["capped"] is True
    assert d["lines_taken"] == evidence.AGENT_DOC_LINE_CAP
    assert len(d["headings"]) == evidence.AGENT_DOC_LINE_CAP


def test_should_not_cap_a_small_file(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("# Kurz\n\nEin Satz.\n", encoding="utf-8")
    d = evidence.agent_doc_digest(str(tmp_path), "CLAUDE.md")
    assert d["capped"] is False
    assert d["lines_taken"] == len(d["headings"])


def test_should_require_a_path_token_for_forbidden_paths_marker():
    """D10.3 fragt nach verbotenen PFADEN, nicht nach dem Wort "nie".

    "nie" und "verboten" sind Alltagswoerter. Ohne Pfad-Bedingung zaehlte
    "wir haben nie Tests geschrieben" als benannter verbotener Pfad — ein
    falsches Gruen in genau dem Werkzeug, das Selbsttaeuschung aufdecken soll.
    Die Gegenprobe unten ist der eigentliche Test: die drei Positivfaelle
    belegen, dass die Regel ueberhaupt greifen KANN.
    """
    pat = evidence.AGENT_DOC_MARKERS["verbotene_pfade"]

    # Negativ: Marker-Wort ohne Pfad
    assert not pat.search("Wir haben nie Tests geschrieben.")
    assert not pat.search("Das war noch nie ein Problem")
    assert not pat.search("Diese Praxis ist verboten.")

    # Positiv (Gegenprobe): Marker-Wort MIT Pfad
    assert pat.search("NIE `infra/ports.yaml` von Hand editieren.")
    assert pat.search("Do not touch tools/generated/")
    assert pat.search("verboten: Aenderungen an docs/adr/*.md")
