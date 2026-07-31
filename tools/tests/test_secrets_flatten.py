"""secrets-flatten: Aufraeumen von ~/.secrets/.secrets/ — Plan und Loeschpfad.

Dieses Werkzeug loescht Dateien in einem Secret-Verzeichnis. Bis heute sicherte
nichts ab, dass es dabei den richtigen Fall trifft. Die teuerste Fehlrichtung ist
eindeutig: eine Datei verwerfen, deren Inhalt oben NICHT identisch vorliegt — dann
ist ein Zugangsdatum weg, das nirgends sonst steht. Genau dagegen ist die
Konflikt-Regel gebaut, und genau die haelt der wichtigste Fall unten fest.

SICHERHEIT: Das Modul zeigt per Default auf das echte ``~/.secrets``. Jeder Test
lenkt SECRETS und NESTED VOR dem ersten Aufruf auf tmp_path um; die Fixture prueft
das zusaetzlich hart nach. Es werden keine echten Werte gelesen oder ausgegeben.
"""

import importlib.util
import pathlib

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "secrets-flatten.py"
_spec = importlib.util.spec_from_file_location("secrets_flatten", _SRC)
sf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sf)


@pytest.fixture()
def secrets(tmp_path, monkeypatch):
    """Lenkt das Modul auf tmp_path um und belegt, dass es nicht mehr nach Hause zeigt."""
    oben = tmp_path / "secrets"
    unten = oben / ".secrets"
    unten.mkdir(parents=True)
    monkeypatch.setattr(sf, "SECRETS", oben)
    monkeypatch.setattr(sf, "NESTED", unten)

    heim = pathlib.Path.home()
    assert tmp_path in sf.SECRETS.parents and heim not in sf.SECRETS.parents
    assert tmp_path in sf.NESTED.parents
    return oben, unten


def schreib(d: pathlib.Path, name: str, inhalt: str) -> pathlib.Path:
    p = d / name
    p.write_text(inhalt, encoding="utf-8")
    return p


# --- plan(): Einordnung ------------------------------------------------------


def test_should_propose_lifting_a_file_that_exists_only_below(secrets):
    _, unten = secrets
    schreib(unten, "fritz-nas", "wert\n")

    hoch, kopie, abgeloest, konflikt = sf.plan()

    assert (hoch, kopie, abgeloest, konflikt) == (["fritz-nas"], [], [], [])


def test_should_propose_discarding_an_identical_copy(secrets):
    oben, unten = secrets
    schreib(oben, "token", "gleich\n")
    schreib(unten, "token", "gleich\n")

    hoch, kopie, abgeloest, konflikt = sf.plan()

    assert (hoch, kopie, abgeloest, konflikt) == ([], ["token"], [], [])


def test_should_report_a_conflict_when_contents_differ(secrets):
    # der teuerste Fall: unterschiedlicher Inhalt darf NIE automatisch fallen
    oben, unten = secrets
    schreib(oben, "token", "neu\n")
    schreib(unten, "token", "alt\n")

    hoch, kopie, abgeloest, konflikt = sf.plan()

    assert (hoch, kopie, abgeloest) == ([], [], [])
    assert len(konflikt) == 1
    name, grund, _, _ = konflikt[0]
    assert (name, grund) == ("token", "Inhalte verschieden")


def test_should_discard_a_superseded_loader_even_without_a_counterpart_above(secrets):
    _, unten = secrets
    schreib(unten, "load_secrets.py", "alter loader\n")

    hoch, _, abgeloest, _ = sf.plan()

    assert abgeloest == ["load_secrets.py"]
    assert hoch == []  # NICHT hochziehen, obwohl oben nichts liegt


def test_should_ignore_subdirectories(secrets):
    _, unten = secrets
    (unten / "unterordner").mkdir()

    assert sf.plan() == ([], [], [], [])


def test_should_not_decide_by_mtime(secrets):
    """Eine neuere Datei kann den aelteren Wert tragen — Inhalt entscheidet."""
    oben, unten = secrets
    a = schreib(oben, "token", "wert-A\n")
    b = schreib(unten, "token", "wert-B\n")
    b.touch()  # unten ist jetzt die neuere Datei
    assert b.stat().st_mtime >= a.stat().st_mtime

    _, _, _, konflikt = sf.plan()

    assert [k[0] for k in konflikt] == ["token"]


def test_should_never_expose_a_secret_value_in_the_fingerprint(secrets):
    _, unten = secrets
    schreib(unten, "token", "supergeheim-123\n")
    oben, _ = secrets
    schreib(oben, "token", "anderer-wert\n")

    _, _, _, konflikt = sf.plan()
    _, _, fo, fu = konflikt[0]

    assert "supergeheim-123" not in fo + fu
    assert "anderer-wert" not in fo + fu


# --- Schreib- und Loeschpfad -------------------------------------------------


def test_should_move_lift_candidates_and_unlink_copies_on_apply(secrets, monkeypatch):
    oben, unten = secrets
    schreib(unten, "neu-hier", "wert\n")
    schreib(oben, "dublette", "gleich\n")
    schreib(unten, "dublette", "gleich\n")
    schreib(unten, "env_loader.py", "abgeloest\n")
    monkeypatch.setattr(sf.sys, "argv", ["secrets-flatten.py", "--apply"])

    assert sf.main() == 0

    assert (oben / "neu-hier").read_text(encoding="utf-8") == "wert\n"
    assert not (unten / "neu-hier").exists()
    assert not (unten / "dublette").exists()
    assert not (unten / "env_loader.py").exists()
    assert (oben / "dublette").read_text(encoding="utf-8") == "gleich\n"
    assert not unten.exists()  # leer -> entfernt


def test_should_leave_a_conflicting_file_untouched_on_apply(secrets, monkeypatch):
    """Die wichtigste Zusicherung des ganzen Werkzeugs."""
    oben, unten = secrets
    schreib(oben, "token", "neu\n")
    schreib(unten, "token", "alt\n")
    monkeypatch.setattr(sf.sys, "argv", ["secrets-flatten.py", "--apply"])

    sf.main()

    assert (unten / "token").read_text(encoding="utf-8") == "alt\n"
    assert (oben / "token").read_text(encoding="utf-8") == "neu\n"
    assert unten.is_dir()  # bleibt bestehen, weil noch belegt


def test_should_change_nothing_without_apply(secrets, monkeypatch):
    oben, unten = secrets
    schreib(unten, "neu-hier", "wert\n")
    schreib(oben, "dublette", "x\n")
    schreib(unten, "dublette", "x\n")
    monkeypatch.setattr(sf.sys, "argv", ["secrets-flatten.py"])

    assert sf.main() == 0

    assert (unten / "neu-hier").exists()
    assert (unten / "dublette").exists()
    assert not (oben / "neu-hier").exists()


def test_should_exit_0_when_the_nested_directory_is_absent(secrets, monkeypatch):
    _, unten = secrets
    unten.rmdir()
    monkeypatch.setattr(sf.sys, "argv", ["secrets-flatten.py", "--apply"])

    assert sf.main() == 0


def test_should_keep_the_nested_dir_when_an_unclassified_entry_remains(secrets, monkeypatch):
    oben, unten = secrets
    schreib(oben, "dublette", "x\n")
    schreib(unten, "dublette", "x\n")
    (unten / "unterordner").mkdir()
    monkeypatch.setattr(sf.sys, "argv", ["secrets-flatten.py", "--apply"])

    sf.main()

    assert unten.is_dir()
    assert (unten / "unterordner").is_dir()
