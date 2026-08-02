"""KONZ-Nummern-Guard: Kollisionen und concept_id-Abweichungen.

Das Werkzeug existiert, weil genau diese Kollision bis 2026-07-24 unentdeckt blieb
— vier doppelt vergebene Nummern, aufgeräumt in #1410. Bis heute sicherte kein Test
ab, dass der Guard sie tatsächlich findet: ein Guard ohne Test ist eine Behauptung.

Jeder Positivfall hat hier seinen Negativfall. Ein Prüfer, der nichts meldet, belegt
Sauberkeit erst, wenn derselbe Prüfer nachweislich auch etwas finden kann.
"""

import importlib.util
import pathlib

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "konz_number_check.py"
_spec = importlib.util.spec_from_file_location("konz_number_check", _SRC)
knc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(knc)


def schreibe(d: pathlib.Path, nummer: str, concept_id: str | None = None) -> pathlib.Path:
    """Legt KONZ-platform-<nummer>.md an; concept_id default = nummer."""
    cid = nummer if concept_id is None else concept_id
    kopf = "---\n" + (f"concept_id: KONZ-platform-{cid}\n" if cid else "") + "---\n"
    p = d / f"KONZ-platform-{nummer}-thema.md"
    p.write_text(kopf + "\nInhalt\n", encoding="utf-8")
    return p


@pytest.fixture()
def konz(tmp_path: pathlib.Path) -> pathlib.Path:
    d = tmp_path / "konzepte"
    d.mkdir()
    return d


def test_should_report_no_conflict_for_distinct_numbers(konz):
    schreibe(konz, "001")
    schreibe(konz, "002")

    by_number, mismatches = knc.scan(konz)

    assert knc.conflicts(by_number) == {}
    assert mismatches == []


def test_should_detect_two_files_sharing_one_number(konz):
    # der Realfall aus #1410
    a = schreibe(konz, "007")
    b = konz / "KONZ-platform-007-zweites-thema.md"
    b.write_text("---\nconcept_id: KONZ-platform-007\n---\n", encoding="utf-8")

    by_number, _ = knc.scan(konz)
    dupes = knc.conflicts(by_number)

    assert list(dupes) == [7]
    assert {p.name for p in dupes[7]} == {a.name, b.name}


def test_should_detect_concept_id_that_disagrees_with_filename(konz):
    schreibe(konz, "010", concept_id="011")

    _, mismatches = knc.scan(konz)

    assert len(mismatches) == 1
    datei, fname_num, cid_num = mismatches[0]
    assert (fname_num, cid_num) == ("010", "011")
    assert datei.name.startswith("KONZ-platform-010")


def test_should_report_missing_concept_id_as_mismatch(konz):
    schreibe(konz, "012", concept_id="")

    _, mismatches = knc.scan(konz)

    assert [m[2] for m in mismatches] == ["(fehlt)"]


def test_should_ignore_files_that_are_not_konz_documents(konz):
    (konz / "README.md").write_text("kein KONZ\n", encoding="utf-8")
    schreibe(konz, "003")

    by_number, mismatches = knc.scan(konz)

    assert list(by_number) == [3]
    assert mismatches == []


def test_should_propose_the_next_free_number_above_the_highest(konz):
    schreibe(konz, "003")
    schreibe(konz, "017")

    by_number, _ = knc.scan(konz)

    assert knc.next_free(by_number) == 18


def test_should_propose_number_1_for_an_empty_directory(konz):
    by_number, _ = knc.scan(konz)

    assert by_number == {}
    assert knc.next_free(by_number) == 1


def _lenke_auf(monkeypatch, konz: pathlib.Path) -> None:
    """Lenkt main() auf ein Testverzeichnis.

    `knc.KONZ_DIR` zu patchen genuegt NICHT: `scan(konz_dir=KONZ_DIR)` bindet den
    Pfad als Default-Argument bei der Funktionsdefinition, also einmalig beim
    Import. Ein spaeteres Setzen des Modulattributs erreicht ihn nicht mehr — der
    erste Anlauf dieses Tests lief deshalb still gegen das echte docs/konzepte
    und war gruen, ohne etwas ueber die Testdaten auszusagen. Gepatcht wird
    darum die Funktion.
    """
    echt = knc.scan
    monkeypatch.setattr(knc, "scan", lambda konz_dir=konz: echt(konz_dir))


def test_should_exit_1_in_check_mode_only_when_something_is_wrong(konz, monkeypatch):
    schreibe(konz, "001")
    _lenke_auf(monkeypatch, konz)
    monkeypatch.setattr(knc.sys, "argv", ["konz_number_check.py", "--check"])
    assert knc.main() == 0

    schreibe(konz, "002", concept_id="003")
    assert knc.main() == 1


def test_should_exit_0_without_check_flag_even_when_conflicted(konz, monkeypatch):
    # ohne --check ist das Werkzeug ein Report, kein Gate
    schreibe(konz, "004", concept_id="005")
    _lenke_auf(monkeypatch, konz)
    monkeypatch.setattr(knc.sys, "argv", ["konz_number_check.py"])

    assert knc.main() == 0
