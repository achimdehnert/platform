"""Tests fuer memory_link_fix.

Der Schreibpfad wird ueberall scharf gefahren (--apply), nicht nur der Trockenlauf:
ein Trockenlauf ruft die schreibende Zeile nie auf und belegt deshalb nichts ueber
sie. Jeder Reparaturtest endet mit einer Gegenprobe durch den Pruefer selbst.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from memory_link_check import pruefe_verzeichnis  # noqa: E402
from memory_link_fix import main, repariere  # noqa: E402


def schreibe(mem: Path, slug: str, name: str, body: str = "") -> Path:
    p = mem / f"{slug}.md"
    p.write_text(
        f"---\nname: {name}\nmetadata:\n  type: feedback\n---\n\n{body}\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture()
def mem(tmp_path: Path) -> Path:
    d = tmp_path / "memory"
    d.mkdir()
    return d


def test_should_align_frontmatter_name_to_filename(mem: Path):
    p = schreibe(mem, "feedback_alpha", "feedback-alpha")

    repariere(mem, apply=True)

    assert "name: feedback_alpha" in p.read_text(encoding="utf-8")
    assert pruefe_verzeichnis(mem) == []


def test_should_rewrite_inbound_link_that_used_the_old_frontmatter_name(mem: Path):
    # der Kernfall: Angleichen ohne Umhaengen wuerde diesen Verweis toeten
    schreibe(mem, "feedback_alpha", "feedback-alpha")
    quelle = schreibe(mem, "feedback_beta", "feedback_beta", "s. [[feedback-alpha]]")

    repariere(mem, apply=True)

    assert "[[feedback_alpha]]" in quelle.read_text(encoding="utf-8")
    assert pruefe_verzeichnis(mem) == []


def test_should_resolve_dead_link_by_adding_the_missing_prefix(mem: Path):
    schreibe(mem, "feedback_alpha", "feedback_alpha")
    quelle = schreibe(mem, "feedback_beta", "feedback_beta", "s. [[alpha]]")

    repariere(mem, apply=True)

    assert "[[feedback_alpha]]" in quelle.read_text(encoding="utf-8")


def test_should_leave_unresolvable_link_untouched_and_report_it(mem: Path):
    quelle = schreibe(mem, "feedback_alpha", "feedback_alpha", "s. [[gibtsnicht]]")

    aenderungen, offen = repariere(mem, apply=True)

    assert aenderungen == []
    assert offen == [("feedback_alpha.md", "gibtsnicht")]
    assert "[[gibtsnicht]]" in quelle.read_text(encoding="utf-8")


def test_should_not_touch_policy_references(mem: Path):
    quelle = schreibe(
        mem, "feedback_alpha", "feedback_alpha", "s. [[evidence-discipline]]"
    )

    aenderungen, offen = repariere(mem, apply=True)

    assert (aenderungen, offen) == ([], [])
    assert "[[evidence-discipline]]" in quelle.read_text(encoding="utf-8")


def test_should_not_resolve_when_two_files_claim_the_same_frontmatter_name(mem: Path):
    # Mehrdeutigkeit ist ein Grund zu stoppen, nicht zu raten
    schreibe(mem, "feedback_alpha", "feedback-dup")
    schreibe(mem, "feedback_beta", "feedback-dup")
    quelle = schreibe(mem, "feedback_gamma", "feedback_gamma", "s. [[feedback-dup]]")

    _, offen = repariere(mem, apply=True)

    assert ("feedback_gamma.md", "feedback-dup") in offen
    assert "[[feedback-dup]]" in quelle.read_text(encoding="utf-8")


def test_should_only_rewrite_the_name_field_inside_the_frontmatter(mem: Path):
    # eine name:-Zeile im Fliesstext darf nicht angefasst werden
    p = schreibe(
        mem, "feedback_alpha", "feedback-alpha", "Beispiel:\nname: nicht-anfassen"
    )

    repariere(mem, apply=True)
    text = p.read_text(encoding="utf-8")

    assert "name: feedback_alpha" in text
    assert "name: nicht-anfassen" in text


def test_should_not_write_anything_without_apply(mem: Path):
    p = schreibe(mem, "feedback_alpha", "feedback-alpha")
    vorher = p.read_text(encoding="utf-8")

    aenderungen, _ = repariere(mem, apply=False)

    assert len(aenderungen) == 1
    assert p.read_text(encoding="utf-8") == vorher


def test_should_leave_a_clean_directory_untouched(mem: Path):
    p = schreibe(mem, "feedback_alpha", "feedback_alpha", "s. [[feedback_beta]]")
    schreibe(mem, "feedback_beta", "feedback_beta")
    vorher = p.read_text(encoding="utf-8")

    assert repariere(mem, apply=True) == ([], [])
    assert p.read_text(encoding="utf-8") == vorher


def test_should_exit_0_when_clean_and_1_when_repairs_pending(mem: Path):
    schreibe(mem, "feedback_alpha", "feedback-alpha")
    assert main(["--root", str(mem), "--quiet"]) == 1

    assert main(["--root", str(mem), "--apply", "--quiet"]) == 1  # hat repariert
    assert main(["--root", str(mem), "--quiet"]) == 0  # jetzt sauber


def test_should_exit_2_on_unusable_root(tmp_path: Path):
    assert main(["--root", str(tmp_path / "gibtsnicht"), "--quiet"]) == 2


def test_should_repair_every_memory_dir_under_a_projects_root(tmp_path: Path):
    for projekt in ("projekt-a", "projekt-b"):
        d = tmp_path / projekt / "memory"
        d.mkdir(parents=True)
        schreibe(d, "feedback_alpha", "feedback-alpha")

    main(["--root", str(tmp_path), "--apply", "--quiet"])

    for projekt in ("projekt-a", "projekt-b"):
        assert pruefe_verzeichnis(tmp_path / projekt / "memory") == []


def test_should_not_rewrite_a_wikilink_inside_code(mem: Path):
    """Der gefaehrlichere Fall: str.replace haette auch das Code-Vorkommen
    umgeschrieben und damit dokumentierte Makro-Syntax verfaelscht."""
    schreibe(mem, "feedback_alpha", "feedback-alpha")
    quelle = schreibe(
        mem,
        "feedback_beta",
        "feedback_beta",
        "Prosa: [[feedback-alpha]]\n\n```\nMakro: [[feedback-alpha]]\n```\n",
    )

    repariere(mem, apply=True)
    text = quelle.read_text(encoding="utf-8")

    assert "Prosa: [[feedback_alpha]]" in text
    assert "Makro: [[feedback-alpha]]" in text  # unveraendert


def test_should_not_report_a_code_only_link_as_open(mem: Path):
    schreibe(mem, "feedback_alpha", "feedback_alpha", "`[[clause]]` ist ein Makro")

    assert repariere(mem, apply=True) == ([], [])
