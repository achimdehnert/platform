"""Tests fuer die Verankerung je Verlaufs-Referenz (platform#2592 K2).

Die Postfach-Attrappe kennt SEARCH UID (liegt die Nummer im Ordner?) und den
Kopfzeilen-Abruf — genau die zwei Zugriffe, die die Verankerung braucht. Ein
Test, der mehr braucht, testet nicht dieses Werkzeug.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mail_agent"))

ea = pytest.importorskip("eintrag_anker")
anker_modul = pytest.importorskip("anker")


class FakeImap:
    """{ordner: {uid: (message_id, betreff)}} — read-only, wie das Original."""

    def __init__(self, postfach: dict[str, dict[str, tuple[str, str]]]):
        self.postfach = postfach
        self.gewaehlt = ""
        self.ausgeloggt = False

    def select(self, mailbox, readonly=False):
        assert readonly, "die Verankerung darf das Postfach nie schreibend oeffnen"
        name = mailbox.strip('"')
        if name not in self.postfach:
            return "NO", [b"kein solcher Ordner"]
        self.gewaehlt = name
        return "OK", [b"1"]

    def list(self):
        return "OK", [f'() "/" "{o}"'.encode() for o in self.postfach]

    def uid(self, befehl, *args):
        ordner = self.postfach.get(self.gewaehlt, {})
        if befehl == "SEARCH" and args[0] == "UID":
            return "OK", [args[1].encode() if args[1] in ordner else b""]
        if befehl == "FETCH":
            eintrag = ordner.get(args[0])
            if not eintrag:
                return "OK", [None]
            mid, betreff = eintrag
            roh = f"Message-ID: {mid}\r\nSubject: {betreff}\r\n\r\n".encode()
            return "OK", [(b"1 (BODY[] {%d}" % len(roh), roh)]
        raise AssertionError(f"unerwarteter Befehl {befehl} {args}")

    def logout(self):
        self.ausgeloggt = True


@pytest.fixture
def postfaecher():
    return {
        "hnu": FakeImap(
            {
                "INBOX": {"164024": ("<a@hnu.de>", "Klimm")},
                "Entw&APw-rfe": {"23611": ("<b@hnu.de>", "Entwurf Bittner")},
                "Gesendete Objekte": {"34349": ("<c@hnu.de>", "AW: Beleg")},
                "Archiv/2025": {"700": ("<alt@hnu.de>", "alt")},
            }
        ),
        "default": FakeImap({"INBOX": {"555": ("<d@ad.de>", "AD-Post")}}),
    }


def _ledger(*vorgaenge: tuple[str, str]) -> dict:
    return {
        "vorgaenge": [
            {"nr": i + 1, "konto": konto, "notiz": notiz}
            for i, (konto, notiz) in enumerate(vorgaenge)
        ]
    }


def _lauf(ledger, postfaecher, anker=None, archiv=None):
    anker = {} if anker is None else anker
    funde = ea.referenzen_im_ledger(ledger, archiv or {})
    return ea.verankere_alle(funde, anker, verbinde=lambda k: postfaecher[k]), anker


class TestFunde:
    def test_should_key_a_reference_by_case_account_folder_and_uid(self):
        funde = ea.referenzen_im_ledger(_ledger(("hnu", "Klimm (INBOX #164024)")), {})
        assert list(funde) == ["hnu-inbox-164024"]
        assert funde["hnu-inbox-164024"].nr == 1

    def test_should_count_the_same_number_in_two_entries_once(self):
        funde = ea.referenzen_im_ledger(
            _ledger(
                ("hnu", "INBOX #164024 kam | 2026-08-22: INBOX #164024 beantwortet")
            ),
            {},
        )
        assert len(funde) == 1
        assert funde["hnu-inbox-164024"].eintrag == 1

    def test_should_skip_a_case_without_account(self):
        assert (
            ea.referenzen_im_ledger({"vorgaenge": [{"nr": 1, "notiz": "INBOX #1"}]}, {})
            == {}
        )

    def test_should_treat_a_folder_reference_as_anchored_under_its_bare_key(self):
        funde = ea.referenzen_im_ledger(_ledger(("hnu", "Entwuerfe #23611")), {})
        assert ea.unverankert(funde, {"hnu-23611": object()}) == {}


class TestVerankern:
    def test_should_anchor_a_number_in_its_named_folder(self, postfaecher):
        ergebnisse, anker = _lauf(
            _ledger(("hnu", "Klimm (INBOX #164024)")), postfaecher
        )
        (e,) = ergebnisse
        assert e.zustand == ea.NEU
        assert ea.uebernehme(ergebnisse, anker) == 1
        a = anker["hnu-inbox-164024"]
        assert (a.konto, a.ordner, a.uid, a.message_id, a.betreff) == (
            "hnu",
            "INBOX",
            "164024",
            "<a@hnu.de>",
            "Klimm",
        )

    def test_should_resolve_the_folder_slug_against_the_real_folder_name(
        self, postfaecher
    ):
        ergebnisse, anker = _lauf(
            _ledger(("hnu", "Entwuerfe #23611 liegt")), postfaecher
        )
        ea.uebernehme(ergebnisse, anker)
        # Der Anker traegt den ROHEN IMAP-Namen (UTF-7), wie anker.py --setze auch.
        assert anker["hnu-entwuerfe-23611"].ordner == "Entw&APw-rfe"

    def test_should_search_the_folder_list_for_a_bare_number(self, postfaecher):
        ergebnisse, anker = _lauf(
            _ledger(("hnu", "Antwort UID 34349 raus")), postfaecher
        )
        ea.uebernehme(ergebnisse, anker)
        assert anker["hnu-34349"].ordner == "Gesendete Objekte"

    def test_should_not_search_archives_for_a_bare_number(self, postfaecher):
        """SUCHORDNER ist bewusst kurz: die Jahresarchive werden nicht durchsucht."""
        (e,), _ = _lauf(_ledger(("hnu", "alt UID 700")), postfaecher)
        assert e.zustand == ea.NICHT_GEFUNDEN

    def test_should_refuse_to_guess_between_two_folders(self, postfaecher):
        postfaecher["hnu"].postfach["Entw&APw-rfe"]["164024"] = (
            "<x@hnu.de>",
            "Doppelt",
        )
        (e,), anker = _lauf(_ledger(("hnu", "siehe UID 164024")), postfaecher)
        assert e.zustand == ea.MEHRDEUTIG
        assert "2 Ordnern" in e.hinweis
        assert anker == {}

    def test_should_report_a_dead_uid_instead_of_inventing_an_anchor(self, postfaecher):
        (e,), anker = _lauf(_ledger(("hnu", "INBOX #999999")), postfaecher)
        assert e.zustand == ea.NICHT_GEFUNDEN
        assert anker == {}

    def test_should_leave_an_existing_anchor_alone(self, postfaecher):
        alt = anker_modul.Anker(
            "hnu-inbox-164024", "hnu", "INBOX", "164024", "<alt>", "x"
        )
        ergebnisse, anker = _lauf(
            _ledger(("hnu", "INBOX #164024")), postfaecher, {"hnu-inbox-164024": alt}
        )
        assert [e.zustand for e in ergebnisse] == [ea.VORHANDEN]
        assert anker["hnu-inbox-164024"] is alt

    def test_should_look_up_iil_numbers_in_the_imap_accounts(self, postfaecher):
        """IIL laeuft ueber Graph; eine Nummer in einem IIL-Vorgang meint HNU/AD.
        Der Schluessel traegt das Vorgangs-Konto, der Anker das Fundkonto."""
        ergebnisse, anker = _lauf(_ledger(("iil", "NEU: INBOX #555 (AD)")), postfaecher)
        ea.uebernehme(ergebnisse, anker)
        assert anker["iil-inbox-555"].konto == "default"

    def test_should_read_the_capped_archive_too(self, postfaecher):
        archiv = {"1": ["2026-08-01: Klimm (INBOX #164024)"]}
        ergebnisse, _ = _lauf(
            _ledger(("hnu", "2026-08-25: nichts")), postfaecher, archiv=archiv
        )
        assert [e.fund.schluessel for e in ergebnisse] == ["hnu-inbox-164024"]

    def test_should_log_out_of_every_account_it_opened(self, postfaecher):
        _lauf(_ledger(("hnu", "INBOX #164024"), ("ad", "INBOX #555")), postfaecher)
        assert postfaecher["hnu"].ausgeloggt and postfaecher["default"].ausgeloggt

    def test_should_report_an_unreachable_account_instead_of_crashing(
        self, postfaecher
    ):
        def verbinde(konto):
            raise OSError("kein Netz")

        funde = ea.referenzen_im_ledger(_ledger(("hnu", "INBOX #164024")), {})
        (e,) = ea.verankere_alle(funde, {}, verbinde=verbinde)
        assert e.zustand == ea.UNPRUEFBAR


class TestBericht:
    def test_should_summarise_counts_first_and_name_the_open_ones(self, postfaecher):
        ergebnisse, _ = _lauf(
            _ledger(("hnu", "INBOX #164024 und INBOX #999999")), postfaecher
        )
        text = ea.bericht(ergebnisse)
        assert text.splitlines()[0].startswith("2 Referenzen: 1 neu verankert")
        assert "hnu-inbox-999999" in text and "nicht-gefunden" in text


class TestCli:
    def test_should_count_without_touching_a_mailbox(
        self, tmp_path, capsys, monkeypatch
    ):
        ledger = tmp_path / "l.json"
        ledger.write_text(
            json.dumps(_ledger(("hnu", "INBOX #1001 und UID 2002"))), "utf-8"
        )
        anker = tmp_path / "a.json"
        anker.write_text(
            json.dumps(
                {
                    "hnu-2002": {
                        "item": "hnu-2002",
                        "konto": "hnu",
                        "ordner": "INBOX",
                        "uid": "2002",
                        "message_id": "<x>",
                    }
                }
            ),
            "utf-8",
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "eintrag_anker.py",
                "--nur-zaehlen",
                "--ledger",
                str(ledger),
                "--anker",
                str(anker),
            ],
        )
        assert ea.main() == 0
        assert "2 Referenzen, 1 ohne Anker" in capsys.readouterr().out

    def test_should_not_write_in_dry_run(self, tmp_path, monkeypatch, postfaecher):
        ledger = tmp_path / "l.json"
        ledger.write_text(json.dumps(_ledger(("hnu", "INBOX #164024"))), "utf-8")
        anker = tmp_path / "a.json"
        monkeypatch.setattr(ea, "_verbinde", lambda k: postfaecher[k])
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "eintrag_anker.py",
                "--trocken",
                "--ledger",
                str(ledger),
                "--anker",
                str(anker),
            ],
        )
        assert ea.main() == 0
        assert not anker.exists()


class TestUnaufloesbar:
    def test_should_record_a_dead_uid_with_date_and_place(self, postfaecher):
        ergebnisse, _ = _lauf(_ledger(("hnu", "INBOX #999999")), postfaecher)
        tot = ea.uebernehme_tot(ergebnisse, {}, "2026-09-01")
        assert tot == {
            "hnu-inbox-999999": {"seit": "2026-09-01", "vorgang": 1, "eintrag": 1}
        }

    def test_should_keep_the_first_date_when_seen_again(self, postfaecher):
        ergebnisse, _ = _lauf(_ledger(("hnu", "INBOX #999999")), postfaecher)
        alt = {"hnu-inbox-999999": {"seit": "2026-08-01"}}
        assert (
            ea.uebernehme_tot(ergebnisse, alt, "2026-09-01")["hnu-inbox-999999"]["seit"]
            == "2026-08-01"
        )

    def test_should_drop_a_number_that_came_back(self, postfaecher):
        ergebnisse, _ = _lauf(_ledger(("hnu", "INBOX #164024")), postfaecher)
        alt = {"hnu-inbox-164024": {"seit": "2026-08-01"}}
        assert ea.uebernehme_tot(ergebnisse, alt, "2026-09-01") == {}

    def test_should_count_only_what_is_neither_anchored_nor_judged_as_open(self):
        funde = ea.referenzen_im_ledger(
            _ledger(("hnu", "INBOX #1001, #1002 und #1003")), {}
        )
        noch = ea.offen(funde, {"hnu-inbox-1001": object()}, {"hnu-inbox-1002": {}})
        assert list(noch) == ["hnu-inbox-1003"]


def test_should_print_only_the_summary_line_with_kurz(
    tmp_path, monkeypatch, capsys, postfaecher
):
    ledger = tmp_path / "l.json"
    ledger.write_text(
        json.dumps(_ledger(("hnu", "INBOX #164024 und INBOX #999999"))), "utf-8"
    )
    monkeypatch.setattr(ea, "_verbinde", lambda k: postfaecher[k])
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "eintrag_anker.py",
            "--kurz",
            "--trocken",
            "--ledger",
            str(ledger),
            "--anker",
            str(tmp_path / "a.json"),
            "--tot",
            str(tmp_path / "t.json"),
        ],
    )
    assert ea.main() == 0
    zeilen = capsys.readouterr().out.strip().splitlines()
    assert len(zeilen) == 1 and zeilen[0].startswith("2 Referenzen: 1 neu verankert")
