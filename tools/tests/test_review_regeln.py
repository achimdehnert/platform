"""Tests fuer registry/review-regeln.yaml und tools/review_regeln.py (KONZ-platform-070 Z1).

Kriterium K1 (#3903): kein Regel-Literal ausserhalb der YAML, generierte Dateien
ohne Drift. Dieser Test laeuft ueber `make test` (tools/tests/) und damit in
tools-tests.yml — der Drift-Test im CI.
"""

from __future__ import annotations

import ast
import copy
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import review_regeln as rr  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
BOT_MODUL = REPO / "tools" / "bot_review_kandidaten.py"
CONTEXT_MODUL = REPO / "agents" / "context_reviewer.py"


@pytest.fixture(scope="module")
def doc() -> dict:
    return rr.lade_regeln()


# ───────────────────────── Schema ─────────────────────────────────────────────────────


def test_should_load_committed_rules_without_schema_errors(doc):
    assert rr.pruefe_schema(doc) == []
    assert len(doc["regeln"]) >= 50


def test_should_require_a_detector_on_every_rule(doc):
    for r in doc["regeln"]:
        d = r["detektor"]
        assert d["typ"] in rr.DETEKTOR_TYPEN, r["id"]
        if d["typ"] in ("pfad", "regex"):
            assert d["muster"], r["id"]
        elif d["typ"] == "umfang":
            assert d["max_zeilen"] > 0, r["id"]
        else:
            assert d["frage"].strip(), r["id"]


def test_should_have_unique_ids_and_report_a_duplicate(doc):
    ids = [r["id"] for r in doc["regeln"]]
    assert len(ids) == len(set(ids))
    kaputt = copy.deepcopy(doc)
    kaputt["regeln"].append(copy.deepcopy(kaputt["regeln"][0]))
    assert any("id doppelt" in f for f in rr.pruefe_schema(kaputt))


def test_should_reject_unknown_class_consumer_and_detector(doc):
    kaputt = copy.deepcopy(doc)
    kaputt["regeln"][0]["klasse"] = "MAYBE"
    kaputt["regeln"][1]["konsumenten"] = ["kaffeemaschine"]
    kaputt["regeln"][2]["detektor"] = {"typ": "orakel"}
    fehler = rr.pruefe_schema(kaputt)
    assert any("klasse" in f for f in fehler)
    assert any("Konsument" in f for f in fehler)
    assert any("detektor.typ" in f for f in fehler)


def test_should_reject_an_invalid_regex(doc):
    kaputt = copy.deepcopy(doc)
    regex_regel = next(r for r in kaputt["regeln"] if r["detektor"]["typ"] == "regex")
    regex_regel["detektor"]["muster"] = ["(unbalanced"]
    assert any("kein gueltiger Regex" in f for f in rr.pruefe_schema(kaputt))


def test_should_raise_schema_error_from_loader(tmp_path, doc):
    kaputt = copy.deepcopy(doc)
    del kaputt["regeln"][0]["begruendung"]
    p = tmp_path / "r.yaml"
    p.write_text(yaml.safe_dump(kaputt, allow_unicode=True), encoding="utf-8")
    with pytest.raises(rr.SchemaFehler) as exc:
        rr.lade_regeln(p)
    assert any("begruendung" in f for f in exc.value.fehler)


# ───────────────────────── K1: kein Regel-Literal ausserhalb der YAML ─────────────────


def _string_literale_ohne_docstrings(pfad: Path) -> set[str]:
    """Alle String-Konstanten eines Moduls ausser Modul-/Funktions-Docstrings."""
    baum = ast.parse(pfad.read_text(encoding="utf-8"))
    docstrings: set[int] = set()
    for knoten in ast.walk(baum):
        if isinstance(
            knoten, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            if knoten.body and isinstance(knoten.body[0], ast.Expr):
                wert = knoten.body[0].value
                if isinstance(wert, ast.Constant) and isinstance(wert.value, str):
                    docstrings.add(id(wert))
    return {
        k.value
        for k in ast.walk(baum)
        if isinstance(k, ast.Constant)
        and isinstance(k.value, str)
        and id(k) not in docstrings
    }


def test_should_keep_no_tabu_path_literal_in_bot_review_kandidaten():
    literale = _string_literale_ohne_docstrings(BOT_MODUL)
    tabu = rr.tabu_pfade("default") + rr.tabu_pfade("deployed")
    verstoesse = sorted(
        lit
        for lit in literale
        for t in tabu
        if lit == t or lit == t.rstrip("*") or lit.startswith(t.rstrip("*"))
    )
    assert verstoesse == [], f"Tabu-Literal(e) im Code statt in der YAML: {verstoesse}"


def test_should_keep_no_context_pattern_literal_in_context_reviewer():
    literale = _string_literale_ohne_docstrings(CONTEXT_MODUL)
    muster = rr.context_muster()
    alle = set()
    for werte in (
        *muster["adr"].values(),
        *muster["prinzipien"].values(),
        *muster["projekte"].values(),
    ):
        alle.update(werte)
    for r in muster["insights"]:
        alle.update(r["detektor"].get("muster", []))
        alle.add(r["ausgabe"]["meldung"])
    verstoesse = sorted(literale & alle)
    assert verstoesse == [], f"Context-Muster im Code statt in der YAML: {verstoesse}"


def test_should_expose_tabu_wrapper_identical_to_yaml():
    sys.path.insert(0, str(REPO / "tools"))
    import bot_review_kandidaten as brk  # noqa: E402

    assert tuple(brk.TABU) == rr.tabu_pfade("default")


# ───────────────────────── Konsumenten-Funktionen ────────────────────────────────────


def test_should_match_tabu_paths_per_profile():
    assert rr.ist_tabu("policies/irgendwas.md")
    assert rr.ist_tabu("docs/adr/ADR-999-x.md")
    assert rr.ist_tabu(".github/CODEOWNERS")
    assert rr.ist_tabu("registry/review-regeln.yaml")
    assert not rr.ist_tabu("README.md")
    assert not rr.ist_tabu("apps/x/migrations/0001_initial.py")
    assert rr.ist_tabu("apps/x/migrations/0001_initial.py", "deployed")
    assert rr.ist_tabu(".github/workflows/deploy-prod.yml", "deployed")
    assert not rr.ist_tabu(".github/workflows/deploy-prod.yml", "default")


def test_should_group_context_patterns_by_category():
    m = rr.context_muster()
    assert set(m) == {"adr", "prinzipien", "umfang", "projekte", "insights"}
    assert "ADR-048" in m["adr"] and "P-003 Tenant-Isolation" in m["prinzipien"]
    assert m["umfang"] == [
        {"referenz": "P-004 Minimal Diff", "max_zeilen": 400, "konfidenz": 0.9}
    ]
    assert "platform" in m["projekte"]
    assert [r["ausgabe"]["kategorie"] for r in m["insights"]] == [
        "Multi-Tenancy",
        "Architecture",
        "HTMX",
        "Design Tokens",
    ]


def test_should_render_reviewer_md_with_managed_footer(doc):
    text = rr.render_reviewer_md(doc)
    assert text.startswith("---\ntrigger: manual\n---\n")
    assert "## Architektur-Prinzipien" in text and "## Verbotene Patterns" in text
    assert text.count("`RR-0") == len(rr.regeln_fuer("reviewer-md", doc))
    assert rr.MARK in text and "content_hash=sha256:" in text and "do_not_edit" in text


# ───────────────────────── Drift-Test (K1 im CI) ─────────────────────────────────────


def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO / "tools" / "review_regeln.py"), *args],
        capture_output=True,
        text=True,
    )


def test_should_pass_check_against_committed_state():
    assert rr.pruefe_drift() == []
    lauf = _cli("--check")
    assert lauf.returncode == 0, lauf.stderr
    assert "kein Drift" in lauf.stdout


def test_should_detect_drift_when_rules_change_without_render(tmp_path):
    kopie = tmp_path / "review-regeln.yaml"
    shutil.copy(rr.DEFAULT_PFAD, kopie)
    daten = yaml.safe_load(kopie.read_text(encoding="utf-8"))
    ziel = next(r for r in daten["regeln"] if "reviewer-md" in r["konsumenten"])
    ziel["begruendung"]["text"] = ziel["begruendung"]["text"] + " (temporaer geaendert)"
    kopie.write_text(
        yaml.safe_dump(daten, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    befunde = rr.pruefe_drift(kopie, rr.REVIEWER_MD)
    assert len(befunde) == 1 and "--render" in befunde[0]
    lauf = _cli("--check", "--regeln", str(kopie))
    assert lauf.returncode == 1
    assert "DRIFT" in lauf.stderr


def test_should_detect_drift_when_rendered_file_is_hand_edited(tmp_path):
    md = tmp_path / "reviewer.md"
    md.write_text(
        rr.REVIEWER_MD.read_text(encoding="utf-8").replace(
            "· `RR-010`", "· `RR-010` (von Hand)"
        )
    )
    assert rr.pruefe_drift(rr.DEFAULT_PFAD, md)


def test_should_render_then_check_clean_on_a_copy(tmp_path):
    md = tmp_path / "reviewer.md"
    assert _cli("--render", "--reviewer-md", str(md)).returncode == 0
    assert _cli("--check", "--reviewer-md", str(md)).returncode == 0


# ───────────────────────── Advocatus-Block (KONZ-070 WP4) ────────────────────────────


def test_should_render_advocatus_block_with_one_row_per_rule(doc):
    alle = rr.render_advocatus_block(doc)
    zeilen = [z for z in alle.splitlines() if z.startswith("| `RR-")]
    assert len(zeilen) == len(rr.regeln_fuer("advocatus", doc))
    deployed = rr.render_advocatus_block(doc, "deployed")
    assert len([z for z in deployed.splitlines() if z.startswith("| `RR-")]) == len(
        rr.regeln_fuer("advocatus", doc, profil="deployed")
    )
    for spalte in rr.ADVOCATUS_SPALTEN:
        assert spalte in alle.splitlines()[0]


def test_should_print_advocatus_block_via_cli_with_and_without_profile():
    lauf = _cli("--advocatus")
    assert lauf.returncode == 0, lauf.stderr
    assert "`RR-010`" in lauf.stdout
    mit = _cli("--advocatus", "--profil", "library")
    assert mit.returncode == 0 and mit.stdout.count("| `RR-") <= lauf.stdout.count("| `RR-")
