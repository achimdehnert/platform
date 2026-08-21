"""Tests für die Verlaufs-Kappung (#2176 Kriterium 3).

Geprüft wird die Entscheidung — was bleibt, was wandert, was passiert beim
zweiten Lauf. Kein Zugriff auf den echten Ledger: die Fixtures sind synthetisch,
dieses Repo ist öffentlich.
"""

import importlib.util
import json
import pathlib
import sys

_SRC = pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "ledger_kappen.py"
_spec = importlib.util.spec_from_file_location("ledger_kappen", _SRC)
lk = importlib.util.module_from_spec(_spec)
sys.modules["ledger_kappen"] = lk
_spec.loader.exec_module(lk)


def _notiz(*eintraege: str) -> str:
    return " | ".join(eintraege)


class TestKappen:
    def test_should_keep_the_newest_entries(self):
        bleibt, weg = lk.kappe(["alt", "mittel", "neu"], grenze=12)
        assert bleibt[-1] == "neu"
        assert "alt" in weg

    def test_should_keep_the_newest_entry_even_when_it_exceeds_the_limit(self):
        """Ein Vorgang ohne aktuellen Stand wäre schlimmer als ein zu langer."""
        bleibt, weg = lk.kappe(["kurz", "x" * 500], grenze=10)
        assert bleibt == ["x" * 500]
        assert weg == ["kurz"]

    def test_should_move_nothing_when_below_the_limit(self):
        bleibt, weg = lk.kappe(["a", "b"], grenze=1000)
        assert weg == []
        assert bleibt == ["a", "b"]

    def test_should_handle_an_empty_history(self):
        assert lk.kappe([]) == ([], [])


class TestVerarbeite:
    def test_should_move_the_old_part_into_the_archive(self):
        ledger = {"vorgaenge": [{"nr": 7, "notiz": _notiz("alt", "mittel", "neu")}]}
        archiv: dict = {}
        bericht = lk.verarbeite(ledger, archiv, grenze=12)
        assert bericht[0]["nr"] == 7
        assert archiv["7"] == ["alt"]
        assert ledger["vorgaenge"][0]["notiz"].endswith("neu")

    def test_should_be_idempotent(self):
        """Zweiter Lauf ohne neue Einträge verschiebt nichts und dupliziert nichts."""
        ledger = {"vorgaenge": [{"nr": 7, "notiz": _notiz("alt", "mittel", "neu")}]}
        archiv: dict = {}
        lk.verarbeite(ledger, archiv, grenze=12)
        zweiter = lk.verarbeite(ledger, archiv, grenze=12)
        assert zweiter == []
        assert archiv["7"] == ["alt"]

    def test_should_append_to_an_existing_archive_without_duplicates(self):
        ledger = {"vorgaenge": [{"nr": 7, "notiz": _notiz("alt", "neu1", "neu2")}]}
        archiv = {"7": ["alt"]}
        lk.verarbeite(ledger, archiv, grenze=10)
        assert archiv["7"].count("alt") == 1

    def test_should_leave_a_vorgang_without_history_alone(self):
        ledger = {"vorgaenge": [{"nr": 7, "notiz": ""}]}
        archiv: dict = {}
        assert lk.verarbeite(ledger, archiv) == []
        assert archiv == {}


def test_should_survive_a_roundtrip_with_umlauts(tmp_path):
    ledger = {"vorgaenge": [{"nr": 7, "notiz": _notiz("Größe & Söhne alt", "neu")}]}
    archiv: dict = {}
    lk.verarbeite(ledger, archiv, grenze=5)
    ziel = tmp_path / "a.json"
    ziel.write_text(json.dumps(archiv, ensure_ascii=False, indent=2), encoding="utf-8")
    assert "Größe & Söhne alt" in json.loads(ziel.read_text(encoding="utf-8"))["7"]
