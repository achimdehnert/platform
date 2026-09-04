"""Portfolio-Aggregation ueber Phase-C-Berichte: Quantile, Baender, P1, Schluessel, Feldabdeckung.

Fixtures sind synthetisch (drei kleine Ergebnisdateien im Format Schema 2.3, keine echten
Repos, keine Secrets). Geprueft werden Invarianten der Rechnung, nicht der Wortlaut.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import future_readiness_portfolio as fp  # noqa: E402


def _bericht(repo: str, readiness: int, findings: list[dict], **over) -> dict:
    d = {
        "repo": repo,
        "readiness": readiness,
        "evidence_coverage": 0.5,
        "readiness_class": "insufficient-evidence",
        "archetype": "python-package",
        "depth": "T1",
        "rubric_version": "2.4-2026-09-04",
        "scores": {},
        "controls": {},
        "calculation": {},
        "findings": findings,
    }
    d.update(over)
    return d


def _f(qid: str, typ: str, sev: str) -> dict:
    return {
        "question_id": qid,
        "finding_type": typ,
        "severity": sev,
        "dimension": qid[:3],
    }


def _lauf(tmp_path: Path, berichte: dict[str, dict]) -> Path:
    rep = tmp_path / "repositories"
    rep.mkdir(parents=True)
    for name, d in berichte.items():
        (rep / name).write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def _fixture(tmp_path: Path) -> Path:
    return _lauf(
        tmp_path,
        {
            "org-a.json": _bericht(
                "org/a",
                40,
                [_f("D06.1", "secret-scanning", "P1"), _f("D02.2", "lockfile", "P2")],
            ),
            "org-b.json": _bericht(
                "org/b",
                60,
                [_f("D05.1", "required-checks", "P1"), _f("D02.2", "lockfile", "P2")],
                archetype="django-app",
            ),
            "org-c.json": _bericht(
                "org/c", 80, [_f("D02.2", "lockfile", "P2")], archetype="django-app"
            ),
        },
    )


def test_should_aggregate_three_reports_with_median_and_quartiles(tmp_path):
    ergebnisse, verdraengt, fremd = fp.lade(str(_fixture(tmp_path)))
    a = fp.auswerten(ergebnisse)
    assert (len(ergebnisse), verdraengt, fremd) == (3, [], [])
    assert a["readiness"] == {
        "min": 40,
        "q1": 50.0,
        "median": 60.0,
        "q3": 70.0,
        "max": 80,
    }


def test_should_bucket_repos_into_readiness_bands(tmp_path):
    ergebnisse, _, _ = fp.lade(str(_fixture(tmp_path)))
    a = fp.auswerten(ergebnisse)
    assert a["baender"]["25-49"] == ["org/a"]
    assert a["baender"]["50-69"] == ["org/b"]
    assert a["baender"]["70-84"] == ["org/c"]
    assert a["baender"]["0-24"] == [] and a["baender"]["85-100"] == []
    assert sum(len(v) for v in a["baender"].values()) == a["repos"]


def test_should_count_p1_per_dimension_and_distinct_repos(tmp_path):
    ergebnisse, _, _ = fp.lade(str(_fixture(tmp_path)))
    a = fp.auswerten(ergebnisse)
    assert a["p1_nach_dimension"] == [
        {"dimension": "D05", "findings": 1, "repos": 1},
        {"dimension": "D06", "findings": 1, "repos": 1},
    ]
    assert a["p1_repos"] == 2
    assert a["severity"] == {"P1": 2, "P2": 3}
    assert a["findings_gesamt"] == 5


def test_should_rank_finding_keys_by_number_of_repos(tmp_path):
    ergebnisse, _, _ = fp.lade(str(_fixture(tmp_path)))
    a = fp.auswerten(ergebnisse)
    assert a["top_schluessel"][0] == {
        "schluessel": "D02.2|lockfile",
        "findings": 3,
        "repos": 3,
    }
    assert len(a["top_schluessel"]) == 3


def test_should_prefer_phase_c_result_and_name_the_displaced_file(tmp_path):
    lauf = _lauf(
        tmp_path,
        {
            "org-a.json": _bericht("org/a", 40, [_f("D06.1", "secret-scanning", "P1")]),
            "org-a.phase-c.json": _bericht("org/a", 55, []),
            "org-b.json": _bericht("org/b", 60, []),
        },
    )
    ergebnisse, verdraengt, fremd = fp.lade(str(lauf))
    assert verdraengt == ["org-a.json"] and fremd == []
    assert sorted(d["readiness"] for d in ergebnisse) == [55, 60]
    assert fp.auswerten(ergebnisse)["severity"] == {}


def test_should_report_missing_fields_instead_of_dropping_the_report(tmp_path):
    ohne = _bericht("org/b", 60, [])
    del ohne["findings"]
    del ohne["evidence_coverage"]
    lauf = _lauf(
        tmp_path,
        {
            "org-a.json": _bericht("org/a", 40, [_f("D02.2", "lockfile", "P2")]),
            "org-b.json": ohne,
            "kaputt.json": {"kein": "ergebnis"},
        },
    )
    ergebnisse, _, fremd = fp.lade(str(lauf))
    a = fp.auswerten(ergebnisse)
    assert fremd == ["kaputt.json"]
    assert a["repos"] == 2
    assert a["findings_ohne_feld"] == ["org/b"]
    assert a["feldabdeckung"]["findings"] == 1
    assert a["feldabdeckung"]["evidence_coverage"] == 1
    assert a["feldabdeckung"]["readiness"] == 2


def test_should_render_markdown_without_breaking_the_table_on_pipes(tmp_path):
    ergebnisse, verdraengt, fremd = fp.lade(str(_fixture(tmp_path)))
    md = fp.markdown(fp.auswerten(ergebnisse), "lauf", verdraengt, fremd)
    schluessel_zeilen = [
        z for z in md.splitlines() if "lockfile" in z and z.startswith("|")
    ]
    assert schluessel_zeilen, "Schluessel-Tabelle fehlt"
    for zeile in schluessel_zeilen:
        assert zeile.count("|") == 5, zeile  # 4 Spalten + Rand: keine rohe Pipe im Text
    assert "D02.2 · lockfile" in md
