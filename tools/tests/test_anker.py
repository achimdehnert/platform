"""Tests für tools/mail_agent/anker.py — Board-Einträge an der Message-ID.

Das IMAP-Gegenüber ist eine Attrappe mit echtem Verhalten: sie kennt Ordner,
UIDs und Message-IDs und beantwortet SELECT/UID FETCH/UID SEARCH danach. So wird
der eigentliche Fall geprüft — dieselbe Mail liegt nach einem Verschieben unter
einer anderen UID in einem anderen Ordner.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mail_agent"))

anker_modul = pytest.importorskip("anker")


class FakeImap:
    """Postfach-Attrappe: {ordner: {uid: (message_id, betreff)}}."""

    def __init__(self, postfach: dict[str, dict[str, tuple[str, str]]]):
        self.postfach = postfach
        self.gewaehlt = ""
        self.select_aufrufe: list[str] = []
        self.search_aufrufe = 0

    def select(self, mailbox, readonly=False):
        name = mailbox.strip('"')
        self.select_aufrufe.append(name)
        if name not in self.postfach:
            return "NO", [b"kein solcher Ordner"]
        self.gewaehlt = name
        return "OK", [str(len(self.postfach[name])).encode()]

    def list(self):
        zeilen = [f'() "/" "{o}"'.encode() for o in self.postfach]
        return "OK", zeilen

    def uid(self, befehl, *args):
        if befehl == "FETCH":
            uid = args[0]
            eintrag = self.postfach.get(self.gewaehlt, {}).get(uid)
            if not eintrag:
                return "OK", [None]
            mid, betreff = eintrag
            roh = f"Message-ID: {mid}\r\nSubject: {betreff}\r\n\r\n".encode()
            return "OK", [(b"1 (UID %s BODY[] {%d}" % (uid.encode(), len(roh)), roh)]
        if befehl == "SEARCH":
            self.search_aufrufe += 1
            gesucht = args[-1]
            treffer = [
                uid.encode()
                for uid, (mid, _) in self.postfach.get(self.gewaehlt, {}).items()
                if mid == gesucht
            ]
            return "OK", [b" ".join(treffer)]
        raise AssertionError(f"unerwarteter Befehl {befehl}")

    def logout(self):
        pass


@pytest.fixture
def postfach():
    return {
        "INBOX": {
            "100": ("<a@hnu.de>", "Leistungsbezüge"),
            "101": ("<b@hnu.de>", "SGL"),
        },
        "MEIKI": {"7": ("<c@lra.de>", "Projektbesprechung")},
        "Archiv/2026": {},
    }


def _anker(
    item="1", ordner="INBOX", uid="100", mid="<a@hnu.de>", betreff="Leistungsbezüge"
):
    return anker_modul.Anker(
        item=item, konto="hnu", ordner=ordner, uid=uid, message_id=mid, betreff=betreff
    )


class TestPruefung:
    def test_should_report_unchanged_when_uid_still_matches(self, postfach):
        imap = FakeImap(postfach)
        befund = anker_modul.pruefe_anker(imap, _anker())
        assert befund.zustand == anker_modul.UNVERAENDERT
        assert befund.handlungsbedarf is False

    def test_should_not_search_folders_on_the_fast_path(self, postfach):
        """Der schnelle Weg darf keine Ordnersuche auslösen — sonst kostet jeder
        Mailcheck ein Vielfaches."""
        imap = FakeImap(postfach)
        anker_modul.pruefe_anker(imap, _anker())
        assert imap.search_aufrufe == 0

    def test_should_detect_move_to_another_folder(self, postfach):
        postfach["MEIKI"]["9"] = postfach["INBOX"].pop("100")
        imap = FakeImap(postfach)
        befund = anker_modul.pruefe_anker(imap, _anker())
        assert befund.zustand == anker_modul.VERSCHOBEN
        assert (befund.neuer_ordner, befund.neue_uid) == ("MEIKI", "9")

    def test_should_detect_move_even_when_uid_is_reused(self, postfach):
        """Nach dem Verschieben kann die alte UID von einer ANDEREN Mail belegt
        sein. Ein reiner UID-Test würde das für 'unverändert' halten."""
        postfach["MEIKI"]["9"] = postfach["INBOX"].pop("100")
        postfach["INBOX"]["100"] = ("<fremd@hnu.de>", "ganz andere Mail")
        imap = FakeImap(postfach)
        befund = anker_modul.pruefe_anker(imap, _anker())
        assert befund.zustand == anker_modul.VERSCHOBEN
        assert befund.neuer_ordner == "MEIKI"

    def test_should_report_deleted_when_message_id_is_gone(self, postfach):
        postfach["INBOX"].pop("100")
        imap = FakeImap(postfach)
        befund = anker_modul.pruefe_anker(imap, _anker())
        assert befund.zustand == anker_modul.GELOESCHT
        assert befund.handlungsbedarf is True

    def test_should_report_unverifiable_without_message_id(self, postfach):
        befund = anker_modul.pruefe_anker(FakeImap(postfach), _anker(mid=""))
        assert befund.zustand == anker_modul.UNPRUEFBAR
        assert befund.handlungsbedarf is False

    def test_should_report_unverifiable_when_folder_vanished(self, postfach):
        imap = FakeImap(postfach)
        befund = anker_modul.pruefe_anker(imap, _anker(ordner="Gibt-Es-Nicht"))
        # Ordner weg, Mail aber auffindbar → das ist ein Verschieben, kein Fehler
        assert befund.zustand == anker_modul.VERSCHOBEN
        assert befund.neuer_ordner == "INBOX"


class TestUebernahme:
    def test_should_follow_moved_anchor(self, postfach):
        postfach["MEIKI"]["9"] = postfach["INBOX"].pop("100")
        bestand = {"1": _anker()}
        befund = anker_modul.pruefe_anker(FakeImap(postfach), bestand["1"])
        neu = anker_modul.uebernehme([befund], bestand)
        assert (neu["1"].ordner, neu["1"].uid) == ("MEIKI", "9")
        assert neu["1"].message_id == "<a@hnu.de>"

    def test_should_keep_deleted_anchor_for_the_owner_to_decide(self, postfach):
        """Pflege-Regel 1: ein Eintrag verschwindet erst bei einer Entscheidung
        des Owners, nicht weil ein Befund ihn nicht mehr findet."""
        postfach["INBOX"].pop("100")
        bestand = {"1": _anker()}
        befund = anker_modul.pruefe_anker(FakeImap(postfach), bestand["1"])
        neu = anker_modul.uebernehme([befund], bestand)
        assert "1" in neu
        assert (neu["1"].ordner, neu["1"].uid) == ("INBOX", "100")


class TestSpeicher:
    def test_should_roundtrip_anchors(self, tmp_path):
        pfad = tmp_path / "mail-anker.json"
        anker_modul.speichere({"1": _anker(), "80": _anker(item="80")}, pfad)
        wieder = anker_modul.lade(pfad)
        assert set(wieder) == {"1", "80"}
        assert wieder["1"].message_id == "<a@hnu.de>"

    def test_should_return_empty_on_broken_file(self, tmp_path):
        pfad = tmp_path / "kaputt.json"
        pfad.write_text("{kein json", encoding="utf-8")
        assert anker_modul.lade(pfad) == {}

    def test_should_ignore_unknown_fields(self, tmp_path):
        pfad = tmp_path / "alt.json"
        pfad.write_text(
            '{"1": {"item": "1", "konto": "hnu", "ordner": "INBOX", "uid": "100",'
            ' "message_id": "<a@hnu.de>", "veraltet": "weg"}}',
            encoding="utf-8",
        )
        assert anker_modul.lade(pfad)["1"].uid == "100"

    def test_should_return_empty_when_file_is_missing(self, tmp_path):
        assert anker_modul.lade(tmp_path / "gibtsnicht.json") == {}


class TestDarstellung:
    def test_should_summarise_counts_first(self, postfach):
        postfach["MEIKI"]["9"] = postfach["INBOX"].pop("100")
        imap = FakeImap(postfach)
        befunde = [
            anker_modul.pruefe_anker(imap, _anker()),
            anker_modul.pruefe_anker(
                imap, _anker(item="2", uid="101", mid="<b@hnu.de>", betreff="SGL")
            ),
        ]
        text = anker_modul.rendern(befunde)
        assert text.splitlines()[0].startswith("2 Anker")
        assert "1 verschoben" in text
        assert "MEIKI" in text

    def test_should_say_so_when_nothing_is_anchored(self):
        assert anker_modul.rendern([]) == "keine Anker hinterlegt"
