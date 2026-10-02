"""Tests für den privaten Schreibweg der mail_agent-Werkzeuge (#3642).

Ledger, Archiv, Anker, Link-Listen und Regeln entstanden mit 664, weil
``write_text`` die umask 002 des Prozesses erbt. Geprüft wird: unter umask 002
entstehen die Dateien trotzdem mit 600, und kein Modul schreibt an diesem Weg
vorbei. Alle Daten sind synthetisch, dieses Repo ist öffentlich.
"""

import ast
import importlib.util
import os
import pathlib
import stat
import sys

import pytest

_DIR = pathlib.Path(__file__).resolve().parents[1] / "mail_agent"
sys.path.insert(0, str(_DIR))


def _lade(name: str):
    spec = importlib.util.spec_from_file_location(name, _DIR / f"{name}.py")
    modul = importlib.util.module_from_spec(spec)
    sys.modules[name] = modul
    spec.loader.exec_module(modul)
    return modul


pd = _lade("privat_datei")


def _rechte(pfad: pathlib.Path) -> int:
    return stat.S_IMODE(pfad.stat().st_mode)


@pytest.fixture
def umask_002():
    alt = os.umask(0o002)
    yield
    os.umask(alt)


class TestSchreibePrivat:
    def test_should_create_file_with_600_under_umask_002(self, tmp_path, umask_002):
        # Positivkontrolle: unter derselben umask liefert write_text 664 —
        # der Test würde den alten Schreibweg also erkennen.
        alt = tmp_path / "alt.json"
        alt.write_text("{}", encoding="utf-8")
        assert _rechte(alt) == 0o664

        neu = tmp_path / "neu.json"
        pd.schreibe_privat(neu, '{"a": 1}')
        assert _rechte(neu) == 0o600
        assert neu.read_text(encoding="utf-8") == '{"a": 1}'

    def test_should_tighten_existing_664_file_to_600(self, tmp_path, umask_002):
        pfad = tmp_path / "ledger.json"
        pfad.write_text("alt", encoding="utf-8")
        assert _rechte(pfad) == 0o664

        pd.schreibe_privat(pfad, "neu")
        assert _rechte(pfad) == 0o600
        assert pfad.read_text(encoding="utf-8") == "neu"

    def test_should_keep_original_and_leave_no_temp_on_failure(
        self, tmp_path, monkeypatch
    ):
        pfad = tmp_path / "ledger.json"
        pd.schreibe_privat(pfad, "unversehrt")

        def kaputt(*_a, **_k):
            raise OSError("Platte voll")

        monkeypatch.setattr(pd.os, "replace", kaputt)
        with pytest.raises(OSError):
            pd.schreibe_privat(pfad, "halb")
        assert pfad.read_text(encoding="utf-8") == "unversehrt"
        assert sorted(p.name for p in tmp_path.iterdir()) == ["ledger.json"]


class TestVerdrahtung:
    """Die Speicherfunktionen der Module legen neue Dateien mit 600 an."""

    def test_should_save_rules_with_600(self, tmp_path, umask_002):
        regeln = _lade("regeln")
        pfad = regeln.speichern([], tmp_path / "mail-regeln.json")
        assert _rechte(pfad) == 0o600

    def test_should_save_anchors_with_600(self, tmp_path, umask_002):
        anker = _lade("anker")
        pfad = tmp_path / "mail-anker.json"
        anker.speichere({}, pfad)
        assert _rechte(pfad) == 0o600

    def test_should_save_link_registry_with_600(self, tmp_path, umask_002):
        server = _lade("mail_link_server")
        pfad = tmp_path / "mail-links.json"
        server.speichere_registry({"1": {"ziel": "x"}}, pfad)
        assert _rechte(pfad) == 0o600


#: Bewusst verbleibende ``write_text``-Aufrufe, je Modul mit Anzahl und Grund.
#: Alles andere in tools/mail_agent schreibt über ``schreibe_privat``.
ERLAUBT = {
    # Token-Datei: setzt direkt danach chmod 600, liegt in einem 700-Verzeichnis.
    "graph_mail.py": 1,
    # HTML-Ansicht im Mail-Cache, ausgeliefert vom Link-Server.
    "mail_view.py": 1,
    # Board-Ausgabe an einen frei gewählten Ort (``--nach``), kein Ledger.
    "board.py": 1,
    # Ablage in ~/shared/lesen, dem Übergabeordner — Rechte gehören dorthin.
    "lese_eingang.py": 1,
}


def _write_text_aufrufe(pfad: pathlib.Path) -> int:
    baum = ast.parse(pfad.read_text(encoding="utf-8"))
    return sum(
        isinstance(k, ast.Call)
        and isinstance(k.func, ast.Attribute)
        and k.func.attr == "write_text"
        for k in ast.walk(baum)
    )


def test_should_route_all_mail_agent_writes_through_schreibe_privat():
    gefunden = {
        p.name: n
        for p in sorted(_DIR.glob("*.py"))
        if (n := _write_text_aufrufe(p))
    }
    assert gefunden == ERLAUBT
