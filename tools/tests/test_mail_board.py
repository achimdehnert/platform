"""Tests für tools/mail_agent/board.py — Board aus dem Vorgangs-Ledger rendern.

Geprüft werden die drei Zusagen, die das Board dem Leser macht: eine stabile
Nummer als Anrede, ein Link je Posten in seine Mail, und naheliegende Aktionen,
die zum Inhalt passen. Kein Test fasst ein Postfach an — alle Pfade sind auf
tmp_path umgebogen.
"""

from __future__ import annotations

import json
import sys
from datetime import timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mail_agent"))

board = pytest.importorskip("board")
anker_modul = pytest.importorskip("anker")
referenzen = pytest.importorskip("referenzen")


@pytest.fixture
def pfade(tmp_path, monkeypatch):
    """Ledger, Anker und Kurz-ID-Registry in tmp_path statt unter ~/.claude."""
    anker = tmp_path / "anker.json"
    links = tmp_path / "links.json"
    anker.write_text(
        json.dumps(
            {
                "3": {
                    "item": "3",
                    "konto": "hnu",
                    "ordner": "INBOX",
                    "uid": "1",
                    "message_id": "<a@b>",
                    "betreff": "x",
                }
            }
        ),
        encoding="utf-8",
    )
    links.write_text(json.dumps({"4": {"graph_id": "AAMk="}}), encoding="utf-8")
    monkeypatch.setattr(board, "ANKER", anker)
    monkeypatch.setattr(board, "LINKS", links)
    return tmp_path


def _ledger(*vorgaenge, naechste=None):
    daten = {"vorgaenge": list(vorgaenge)}
    if naechste is not None:
        daten["naechste_nr"] = naechste
    return daten


def _v(**felder):
    grund = {"konto": "hnu", "typ": "vorgang", "bucket": "owner", "kurz": "K"}
    return {**grund, **felder}


class TestStabileNummer:
    def test_should_never_reuse_a_number_already_seen_in_the_anchors(self, pfade):
        """Anker kennen Nummer 3 und 4 — eine Neuvergabe muss darüber hinausgehen.

        Sonst zeigte die Anrede „3" auf zwei verschiedene Vorgänge: den alten,
        dessen Mail noch verankert ist, und den neuen.
        """
        ledger, neu = board.vergib_nummern(_ledger(_v()))
        assert [nr for nr, _ in neu] == [5]
        assert ledger["naechste_nr"] == 6

    def test_should_leave_existing_numbers_untouched(self, pfade):
        ledger, neu = board.vergib_nummern(_ledger(_v(nr=9), _v(kurz="L")))
        assert neu == [(10, "L")]
        assert [v["nr"] for v in ledger["vorgaenge"]] == [9, 10]

    def test_should_keep_gaps_instead_of_renumbering(self, pfade):
        """Lücken sind der Preis der Stabilität und ausdrücklich gewollt."""
        ledger, _ = board.vergib_nummern(_ledger(_v(nr=7), _v(nr=42), _v(kurz="neu")))
        assert [v["nr"] for v in ledger["vorgaenge"]] == [7, 42, 43]

    def test_should_report_duplicate_numbers_as_ambiguous(self, pfade):
        befunde = board.pruefe(_ledger(_v(nr=5), _v(nr=5, kurz="L"), naechste=6))
        assert any("doppelt" in b for b in befunde)

    def test_should_report_counter_that_allows_reuse(self, pfade):
        befunde = board.pruefe(_ledger(_v(nr=9), naechste=3))
        assert any("Wiederverwendung" in b for b in befunde)


class TestMailBezug:
    def test_should_link_imap_and_graph_items_through_the_same_route(self, pfade):
        """Eine Linkform für alle Konten — der Leser soll den Unterschied nicht sehen."""
        text = board.render(
            _ledger(_v(nr=3, kurz="IMAP-Posten"), _v(nr=4, kurz="Graph-Posten")),
            "2026-08-10",
        )
        assert "[IMAP-Posten](https://mail.iil.pet/a/3)" in text
        assert "[Graph-Posten](https://mail.iil.pet/a/4)" in text

    def test_should_make_the_action_text_the_link_not_a_bare_url(self, pfade):
        text = board.render(_ledger(_v(nr=3, kurz="Antwort entwerfen")), "2026-08-10")
        assert "[Antwort entwerfen](https://mail.iil.pet/a/3)" in text
        # Eine nackte URL in einer eigenen Zeile wäre der alte, verworfene Weg.
        assert "\nhttps://mail.iil.pet" not in text

    def test_should_flag_an_item_without_any_anchor(self, pfade):
        befunde = board.pruefe(_ledger(_v(nr=99), naechste=100))
        assert any("keine Mail verankert" in b for b in befunde)

    def test_should_not_demand_an_anchor_for_waiting_items(self, pfade):
        """Beim Warten liegt der Ball außen — ein fehlender Link blockiert nichts."""
        befunde = board.pruefe(_ledger(_v(nr=99, bucket="warten"), naechste=100))
        assert not any("keine Mail verankert" in b for b in befunde)

    def test_should_mark_unlinked_items_visibly_in_the_board(self, pfade):
        text = board.render(_ledger(_v(nr=99, kurz="Ohne Anker")), "2026-08-10")
        assert "⚠️ keine Mail verankert" in text


class TestNaheliegendeAktionen:
    def test_should_derive_actions_from_the_type(self, pfade):
        kuerzel = dict(board.aktionen_fuer(_v(typ="termin")))
        assert "Terminvorschlag entwerfen" in kuerzel.values()
        assert "Absage entwerfen" in kuerzel.values()

    def test_should_offer_different_actions_for_a_different_type(self, pfade):
        termin = {t for _, t in board.aktionen_fuer(_v(typ="termin"))}
        arbeit = {t for _, t in board.aktionen_fuer(_v(typ="betreuung-masterarbeit"))}
        assert termin != arbeit

    def test_should_add_follow_up_only_while_waiting(self, pfade):
        wartend = {t for _, t in board.aktionen_fuer(_v(typ="termin", bucket="warten"))}
        eigener = {t for _, t in board.aktionen_fuer(_v(typ="termin", bucket="owner"))}
        assert "Nachfassen entwerfen" in wartend
        assert "Nachfassen entwerfen" not in eigener

    def test_should_never_leave_an_item_without_an_action(self, pfade):
        assert board.aktionen_fuer(_v(typ="voellig-unbekannt"))

    def test_should_always_offer_closing_the_item(self, pfade):
        for typ in [*board.AKTIONEN_JE_TYP, "unbekannt"]:
            kuerzel = [k for k, _ in board.aktionen_fuer(_v(typ=typ))]
            assert "z" in kuerzel, typ

    def test_should_keep_shortcuts_unique_within_an_item(self, pfade):
        """`7a` muss eindeutig sein, sonst ist die kurze Anweisung mehrdeutig."""
        for typ in [*board.AKTIONEN_JE_TYP, "unbekannt"]:
            for bucket in ("owner", "warten"):
                kuerzel = [
                    k for k, _ in board.aktionen_fuer(_v(typ=typ, bucket=bucket))
                ]
                assert len(kuerzel) == len(set(kuerzel)), (typ, bucket)

    def test_should_never_propose_sending_anything(self, pfade):
        """Draft-first: nach außen entsteht ein Entwurf, gesendet wird von Hand."""
        alle = [
            text
            for aktionen in (
                *board.AKTIONEN_JE_TYP.values(),
                board.AKTIONEN_WARTEN,
                board.AKTIONEN_IMMER,
                board.AKTIONEN_FALLBACK,
            )
            for _, text in aktionen
        ]
        verboten = ("senden", "abschicken", "verschicken", "versenden")
        treffer = [t for t in alle if any(w in t.lower() for w in verboten)]
        assert treffer == []

    def test_should_not_offer_booking_without_approval(self, pfade):
        """sevdesk wird nie ohne ausdrückliche Freigabe gebucht."""
        texte = [t for _, t in board.AKTIONEN_JE_TYP["todo-edv-beratung"]]
        assert any("nicht buchen" in t for t in texte)


class TestRendern:
    def test_should_group_items_into_their_buckets(self, pfade):
        text = board.render(
            _ledger(
                _v(nr=3, bucket="owner", kurz="Meiner"),
                _v(nr=4, bucket="agent", kurz="Deiner"),
            ),
            "2026-08-10",
        )
        assert text.index("dein Zug") < text.index("Meiner")
        assert text.index("ich kann sofort") < text.index("Deiner")

    def test_should_surface_items_without_a_bucket_instead_of_dropping_them(
        self, pfade
    ):
        text = board.render(
            _ledger(_v(nr=3, bucket=None, kurz="Heimatlos")), "2026-1-1"
        )
        assert "Ohne Zuordnung" in text
        assert "Heimatlos" in text

    def test_should_carry_the_findings_into_the_board(self, pfade):
        text = board.render(_ledger(_v(nr=99, kurz="Ohne Anker")), "2026-08-10")
        assert "Befunde der Pruefung" in text

    def test_should_state_that_numbers_are_stable(self, pfade):
        text = board.render(_ledger(_v(nr=3)), "2026-08-10")
        assert "nie wiederverwendet" in text

    def test_should_append_the_local_care_rules_verbatim(self, pfade, monkeypatch):
        """Rendern darf die gewachsenen Pflege-Regeln nicht stillschweigend fressen."""
        regeln = pfade / "regeln.md"
        regeln.write_text("## Pflege-Regeln\n\n1. Vollerhebung.\n", encoding="utf-8")
        monkeypatch.setattr(board, "REGELN", regeln)
        text = board.render(_ledger(_v(nr=3)), "2026-08-10")
        assert "1. Vollerhebung." in text

    def test_should_render_without_care_rules_present(self, pfade, monkeypatch):
        monkeypatch.setattr(board, "REGELN", pfade / "gibtsnicht.md")
        assert board.render(_ledger(_v(nr=3)), "2026-08-10").startswith("# Mail")


class TestErledigt:
    """Der Zustand `erledigt` — bis 2026-08-18 gab es die Aktion, aber kein Ziel.

    Geschlossene Vorgänge wurden aus dem Ledger entfernt. Damit war weder sichtbar,
    was fertig wurde, noch hatte eine Nachlogik am Abschluss einen Auslöser.
    """

    def test_should_render_a_recently_closed_item_in_its_own_section(self, pfade):
        heute = "2026-08-18"
        ausgabe = board.render(
            _ledger(_v(nr=3, bucket="erledigt", erledigt_am=heute, kurz="Fertig")),
            heute,
        )
        assert "✅ Erledigt" in ausgabe
        assert "Fertig" in ausgabe

    def test_should_hide_an_old_closure_but_still_count_it(self, pfade):
        """Nach dem Fenster verschwindet die Zeile, nicht der Vorgang."""
        heute = "2026-08-18"
        alt = (
            board.date.fromisoformat(heute)
            - timedelta(days=board.ERLEDIGT_FENSTER_TAGE + 1)
        ).isoformat()
        ausgabe = board.render(
            _ledger(_v(nr=3, bucket="erledigt", erledigt_am=alt, kurz="Uralt")), heute
        )
        assert "Uralt" not in ausgabe
        assert "1 weitere" in ausgabe

    def test_should_report_a_closed_item_without_a_closing_date(self, pfade):
        befunde = board.pruefe(_ledger(_v(nr=3, bucket="erledigt"), naechste=4))
        assert any("erledigt_am" in b for b in befunde)

    def test_should_not_offer_follow_up_actions_on_a_closed_item(self, pfade):
        """„Nachfassen entwerfen" auf einem geschlossenen Vorgang wäre sinnlos."""
        aktionen = dict(board.aktionen_fuer(_v(bucket="erledigt")))
        assert "n" not in aktionen
        assert "z" not in aktionen
        assert "o" in aktionen

    def test_should_treat_an_unreadable_closing_date_as_a_finding(self, pfade):
        befunde = board.pruefe(
            _ledger(_v(nr=3, bucket="erledigt", erledigt_am="gestern"), naechste=4)
        )
        assert any("erledigt_am" in b for b in befunde)


class TestErledigtKommando:
    """`board.py --erledigt` schliesst einen Vorgang per Kommando statt per Hand (#3049)."""

    def test_should_close_an_open_item_and_set_the_three_fields(self, pfade, tmp_path):
        ledger = tmp_path / "l.json"
        ledger.write_text(
            json.dumps(_ledger(_v(nr=7, bucket="owner", kurz="K"), naechste=8)),
            "utf-8",
        )
        # --ohne-anker: dieser Test prueft die drei Felder, nicht den seit V3
        # (#3015 K4) verlangten Anker — der hat seine eigene Testklasse.
        rc = board.main(
            [
                "--ledger",
                str(ledger),
                "--erledigt",
                "7",
                "--am",
                "2026-09-11",
                "--grund",
                "Antwort erhalten",
                "--ohne-anker",
            ]
        )
        v = json.loads(ledger.read_text())["vorgaenge"][0]
        assert rc == 0
        assert (v["bucket"], v["erledigt_am"], v["zustand"]) == (
            "erledigt",
            "2026-09-11",
            "erledigt: Antwort erhalten",
        )
        assert "ERLEDIGT (Owner): Antwort erhalten" in v["notiz"]

    def test_should_refuse_an_unknown_number(self, pfade, tmp_path):
        ledger = tmp_path / "l.json"
        ledger.write_text(json.dumps(_ledger(_v(nr=7), naechste=8)), "utf-8")
        with pytest.raises(SystemExit) as fehler:
            board.main(
                ["--ledger", str(ledger), "--erledigt", "99", "--am", "2026-09-11"]
            )
        assert fehler.value.code == 2

    def test_should_leave_an_already_closed_item_unchanged_on_a_second_close(
        self, pfade, tmp_path
    ):
        ledger = tmp_path / "l.json"
        ledger.write_text(
            json.dumps(
                _ledger(
                    _v(
                        nr=7,
                        bucket="erledigt",
                        erledigt_am="2026-09-01",
                        zustand="erledigt",
                        notiz="2026-09-01 ERLEDIGT (Owner): x",
                    ),
                    naechste=8,
                )
            ),
            "utf-8",
        )
        vorher = ledger.read_text()
        rc = board.main(
            ["--ledger", str(ledger), "--erledigt", "7", "--am", "2026-09-11"]
        )
        assert rc == 0
        assert ledger.read_text() == vorher

    def test_should_reverse_a_closure_on_reopen(self, pfade):
        ledger = _ledger(_v(nr=7, bucket="owner", kurz="K"))
        vorgang, status = board.schliesse_vorgang(
            ledger, 7, "2026-09-11", "", "2026-09-11"
        )
        assert status == "geschlossen"
        wieder, status2 = board.wiedereroeffne_vorgang(ledger, 7, "2026-09-12")
        assert status2 == "geoeffnet"
        assert wieder["bucket"] == "owner"
        assert "erledigt_am" not in wieder
        assert "WIEDER GEOEFFNET (Owner)" in wieder["notiz"]

    def test_should_report_a_closing_date_without_the_closed_bucket(self, pfade):
        befunde = board.pruefe(
            _ledger(_v(nr=7, bucket="owner", erledigt_am="2026-09-01"), naechste=8)
        )
        assert any("erledigt_am" in b and "!= 'erledigt'" in b for b in befunde)


class TestLinkZiel:
    """Der Posten fuehrt in die Vorgangsansicht, nicht in die aelteste Mail."""

    def test_should_link_to_the_vorgangsansicht(self):
        ziel = board.link_fuer(7, "imap", {"thread_key": "Muster Vorgang"})
        assert ziel == "https://todo.iil.pet/t/Muster%20Vorgang"

    def test_should_encode_umlauts_in_the_thread_key(self):
        ziel = board.link_fuer(7, "imap", {"thread_key": "Löschung Konto"})
        assert ziel == "https://todo.iil.pet/t/L%C3%B6schung%20Konto"

    def test_should_fall_back_to_the_mail_anchor_without_thread_key(self):
        assert board.link_fuer(7, "imap", {}) == "https://mail.iil.pet/a/7"

    def test_should_return_nothing_when_neither_exists(self):
        assert board.link_fuer(7, "fehlt", {}) is None

    def test_should_link_even_without_anchored_mail(self):
        """Genau die Luecke, die vorher 'nicht anklickbar' hiess."""
        assert board.link_fuer(7, "fehlt", {"thread_key": "Ohne Anker"}) is not None


def test_should_classify_every_bucket_as_stand_or_zug():
    """Jeder Bucket gehoert genau einer Haelfte an — sonst ist die Reihenfolge undefiniert.

    Ohne diese Zusage koennte ein fuenfter Bucket hinzukommen, ohne dass
    irgendwo entschieden waere, ob er den Stand beschreibt oder einen Zug
    verlangt; er landete erfahrungsgemaess am Listenende und damit hinter
    "dein Zug".
    """
    benannt = set(board.STAND_BUCKETS) | set(board.ZUG_BUCKETS)
    assert {b for b, _ in board.BUCKETS} == benannt
    assert not set(board.STAND_BUCKETS) & set(board.ZUG_BUCKETS)


def test_should_render_stand_before_zug():
    """Erst was war, dann was zu tun ist — die Regel, nicht die konkrete Liste.

    Der Test prueft die Eigenschaft statt der Reihenfolge selbst: er ueberlebt
    das Hinzufuegen eines Buckets und faellt trotzdem, wenn jemand "dein Zug"
    wieder nach oben zieht.
    """
    stellen = {b: i for i, (b, _) in enumerate(board.BUCKETS)}
    assert max(stellen[b] for b in board.STAND_BUCKETS) < min(
        stellen[b] for b in board.ZUG_BUCKETS
    )


class TestFristPflicht:
    """Jeder offene Vorgang traegt eine Frist oder sagt, warum nicht (#2592 K4)."""

    def test_should_flag_an_open_item_without_deadline_and_reason(self, pfade):
        befunde = board.pruefe(_ledger(_v(nr=1, bucket="warten"), naechste=2))
        assert any("keine Frist und kein frist_grund" in b for b in befunde)

    def test_should_accept_an_iso_deadline(self, pfade):
        befunde = board.pruefe(
            _ledger(_v(nr=1, bucket="warten", frist="2026-09-30"), naechste=2)
        )
        assert not any("Frist" in b for b in befunde)

    def test_should_accept_null_with_a_reason(self, pfade):
        v = _v(nr=1, bucket="warten", frist=None, frist_grund="kein Termin vereinbart")
        assert not any("Frist" in b for b in board.pruefe(_ledger(v, naechste=2)))

    def test_should_flag_an_unreadable_deadline(self, pfade):
        befunde = board.pruefe(
            _ledger(_v(nr=1, bucket="owner", frist="28.08."), naechste=2)
        )
        assert any("kein ISO-Datum" in b for b in befunde)

    def test_should_not_demand_a_deadline_for_finished_items(self, pfade):
        v = _v(nr=1, bucket="erledigt", erledigt_am="2026-08-30")
        assert not any("Frist" in b for b in board.pruefe(_ledger(v, naechste=2)))

    def test_should_set_a_deadline_through_the_cli(self, pfade, tmp_path, capsys):
        ledger = tmp_path / "l.json"
        ledger.write_text(
            json.dumps(_ledger(_v(nr=7, bucket="owner"), naechste=8)), "utf-8"
        )
        assert (
            board.main(
                ["--ledger", str(ledger), "--frist", "7", "--datum", "2026-09-30"]
            )
            == 0
        )
        assert json.loads(ledger.read_text())["vorgaenge"][0]["frist"] == "2026-09-30"
        assert "#7" in capsys.readouterr().out

    def test_should_record_reason_when_there_is_no_deadline(self, pfade, tmp_path):
        ledger = tmp_path / "l.json"
        ledger.write_text(
            json.dumps(_ledger(_v(nr=7, bucket="owner"), naechste=8)), "utf-8"
        )
        board.main(
            [
                "--ledger",
                str(ledger),
                "--frist",
                "7",
                "--datum",
                "keine",
                "--grund",
                "Owner-Aufgabe ohne Termin",
            ]
        )
        v = json.loads(ledger.read_text())["vorgaenge"][0]
        assert (v["frist"], v["frist_grund"]) == (None, "Owner-Aufgabe ohne Termin")

    def test_should_refuse_none_without_a_reason(self, pfade):
        with pytest.raises(SystemExit, match="braucht --grund"):
            board.setze_frist(_ledger(_v(nr=7)), 7, "keine", "")

    def test_should_refuse_a_non_iso_date(self, pfade):
        with pytest.raises(SystemExit, match="kein ISO-Datum"):
            board.setze_frist(_ledger(_v(nr=7)), 7, "28.08.2026", "")

    def test_should_refuse_an_unknown_number(self, pfade):
        with pytest.raises(SystemExit, match="gibt es nicht"):
            board.setze_frist(_ledger(_v(nr=7)), 8, "2026-09-30", "")


class TestReproduzierbar:
    """Zwei Laeufe ueber denselben Ledger liefern dasselbe Board (#2592 K1)."""

    def test_should_render_identically_twice(self, pfade):
        ledger = _ledger(
            _v(nr=3, kurz="A", bucket="owner", frist="2026-09-30"),
            _v(nr=4, kurz="B", bucket="warten", frist=None, frist_grund="kein Termin"),
            _v(nr=5, kurz="C", bucket="erledigt", erledigt_am="2026-08-30"),
            naechste=6,
        )
        assert board.render(ledger, "2026-09-02") == board.render(ledger, "2026-09-02")

    def test_should_render_with_an_explicit_cutoff_from_the_cli(
        self, pfade, tmp_path, capsys
    ):
        ledger = tmp_path / "l.json"
        ledger.write_text(
            json.dumps(_ledger(_v(nr=3, frist="2026-09-30"), naechste=4)), "utf-8"
        )
        assert (
            board.main(
                ["--ledger", str(ledger), "--render", "--stichtag", "2026-09-02"]
            )
            == 0
        )
        erster = capsys.readouterr().out
        board.main(["--ledger", str(ledger), "--render", "--stichtag", "2026-09-02"])
        assert capsys.readouterr().out == erster

    def test_should_reject_an_unreadable_cutoff(self, pfade, tmp_path):
        ledger = tmp_path / "l.json"
        ledger.write_text(json.dumps(_ledger(_v(nr=3), naechste=4)), "utf-8")
        with pytest.raises(ValueError):
            board.main(
                ["--ledger", str(ledger), "--render", "--stichtag", "02.09.2026"]
            )


class TestKopfzeile:
    """Eine Zeile beantwortet den Tag, bevor der Leser scrollt (2026-09-09)."""

    def test_should_open_with_a_rollup_line(self, pfade):
        text = board.render(
            _ledger(
                _v(nr=3, bucket="owner", kurz="Meiner", frist="2026-09-20"),
                _v(nr=4, bucket="warten", kurz="Deiner", frist="2026-09-30"),
            ),
            "2026-09-09",
        )
        assert "**Heute:**" in text
        assert text.index("**Heute:**") < text.index("Meiner")
        assert "1 dein Zug" in text and "1 wartend" in text

    def test_should_name_the_nearest_deadline(self, pfade):
        text = board.kopfzeile(
            [
                _v(nr=3, bucket="owner", frist="2026-09-20"),
                _v(nr=4, bucket="warten", frist="2026-09-11"),
            ],
            "2026-09-09",
        )
        assert "nächste Frist 2026-09-11 (#4)" in text

    def test_should_count_overdue_items(self, pfade):
        text = board.kopfzeile(
            [_v(nr=3, bucket="owner", frist="2026-09-01")], "2026-09-09"
        )
        assert "1 überfällig" in text

    def test_should_stay_silent_about_deadlines_when_there_are_none(self, pfade):
        assert "Frist" not in board.kopfzeile([_v(nr=3, bucket="owner")], "2026-09-09")

    def test_should_not_depend_on_the_clock(self, pfade):
        posten = [_v(nr=3, bucket="owner", frist="2026-09-20")]
        assert board.kopfzeile(posten, "2026-09-09") == board.kopfzeile(
            posten, "2026-09-09"
        )


class TestKenntnis:
    """Post, die nichts verlangt, bleibt sichtbar — ohne Frist und ohne Zug."""

    def test_should_render_a_kenntnis_item_in_its_own_section(self, pfade):
        text = board.render(
            _ledger(
                _v(nr=3, bucket="kenntnis", kurz="Statusbericht", angelegt="2026-09-08")
            ),
            "2026-09-09",
        )
        assert "Nur zur Kenntnis" in text
        assert text.index("Nur zur Kenntnis") < text.index("Statusbericht")

    def test_should_hide_an_old_kenntnis_item_but_still_count_it(self, pfade):
        text = board.render(
            _ledger(_v(nr=3, bucket="kenntnis", kurz="Uralt", angelegt="2026-08-01")),
            "2026-09-09",
        )
        assert "Uralt" not in text
        assert f"{board.KENNTNIS_FENSTER_TAGE} Tagen angelegt" in text

    def test_should_not_demand_a_deadline_for_kenntnis(self, pfade):
        befunde = board.pruefe(
            _ledger(_v(nr=1, bucket="kenntnis", angelegt="2026-09-09"), naechste=2)
        )
        assert not [b for b in befunde if "frist" in b.lower()]

    def test_should_offer_promoting_a_kenntnis_item(self, pfade):
        kuerzel = [k for k, _ in board.aktionen_fuer(_v(bucket="kenntnis"))]
        assert "v" in kuerzel and "z" in kuerzel

    def test_should_not_offer_follow_up_on_a_kenntnis_item(self, pfade):
        kuerzel = [k for k, _ in board.aktionen_fuer(_v(bucket="kenntnis"))]
        assert "n" not in kuerzel

    def test_should_count_as_stand_not_as_zug(self, pfade):
        assert "kenntnis" in board.STAND_BUCKETS
        assert "kenntnis" not in board.ZUG_BUCKETS


class TestThreadKeyUndReferenzText:
    """Bausteine von `--neu` (V2, platform#3015 K4) — reine Textfunktionen."""

    @pytest.mark.parametrize(
        "betreff, erwartet",
        [
            ("Anfrage Musterarbeit", "Anfrage Musterarbeit"),
            ("Re: Anfrage Musterarbeit", "Anfrage Musterarbeit"),
            ("AW: Re: Anfrage Musterarbeit", "Anfrage Musterarbeit"),
            ("Fwd: WG: Anfrage Musterarbeit", "Anfrage Musterarbeit"),
            ("re:Anfrage Musterarbeit", "Anfrage Musterarbeit"),
        ],
    )
    def test_should_strip_leading_reply_and_forward_prefixes(self, betreff, erwartet):
        assert board.thread_key_aus_betreff(betreff) == erwartet

    def test_should_use_the_plain_form_for_a_one_word_folder(self):
        assert board._referenz_text("INBOX", "164024") == "INBOX #164024"

    def test_should_use_the_quoted_form_for_a_folder_with_a_space(self):
        assert (
            board._referenz_text("Gesendete Objekte", "34349")
            == "Ordner 'Gesendete Objekte' (#34349)"
        )


class TestVorgangAusMail:
    """`vorgang_aus_mail` legt den Vorgang an — reine Funktion (V2, #3015 K4)."""

    KOPF = {
        "von": "Max Mustermann <max.muster@example.org>",
        "betreff": "Re: Anfrage Musterarbeit",
        "datum": "2026-09-10",
        "message_id": "<abc@example.org>",
    }

    def test_should_create_a_vorgang_from_a_synthetic_header(self, pfade):
        ledger = _ledger(naechste=5)
        v = board.vorgang_aus_mail(
            ledger,
            "ad",
            "INBOX",
            "164024",
            self.KOPF,
            "vorgang",
            "owner",
            None,
            "noch keine Frist vereinbart",
            None,
            "2026-09-13 14:32",
        )
        assert v["nr"] == 5
        assert v["thread_key"] == "Anfrage Musterarbeit"
        assert v["gegenueber"] == "Max Mustermann <max.muster@example.org>"
        assert v["kurz"] == "Mustermann: Anfrage Musterarbeit"
        assert v["zustand"] == "eingang-13-09-owner-entscheidet"
        assert v["angelegt"] == v["letzte_pruefung"] == "2026-09-13 14:32"
        assert v["mail_ref"] == "/a/5"
        assert v in ledger["vorgaenge"]

    def test_should_strip_the_prefix_for_the_thread_key_but_not_for_the_notiz(
        self, pfade
    ):
        v = board.vorgang_aus_mail(
            _ledger(naechste=1),
            "ad",
            "INBOX",
            "1",
            self.KOPF,
            "vorgang",
            "owner",
            None,
            "x",
            None,
            "2026-09-13 08:00",
        )
        assert v["thread_key"] == "Anfrage Musterarbeit"
        assert "'Re: Anfrage Musterarbeit'" in v["notiz"]

    def test_should_increment_the_ledger_counter(self, pfade):
        ledger = _ledger(naechste=5)
        board.vorgang_aus_mail(
            ledger,
            "ad",
            "INBOX",
            "1",
            self.KOPF,
            "vorgang",
            "owner",
            None,
            "x",
            None,
            "2026-09-13 08:00",
        )
        assert ledger["naechste_nr"] == 6

    def test_should_refuse_when_neither_frist_nor_grund_is_given(self, pfade):
        with pytest.raises(ValueError, match="Frist ist Pflicht"):
            board.vorgang_aus_mail(
                _ledger(naechste=1),
                "ad",
                "INBOX",
                "1",
                self.KOPF,
                "vorgang",
                "owner",
                None,
                "",
                None,
                "2026-09-13 08:00",
            )

    def test_should_refuse_none_deadline_without_a_reason(self, pfade):
        with pytest.raises(ValueError, match="braucht --grund"):
            board.vorgang_aus_mail(
                _ledger(naechste=1),
                "ad",
                "INBOX",
                "1",
                self.KOPF,
                "vorgang",
                "owner",
                "keine",
                "",
                None,
                "2026-09-13 08:00",
            )

    def test_should_accept_an_iso_deadline_without_a_reason(self, pfade):
        v = board.vorgang_aus_mail(
            _ledger(naechste=1),
            "ad",
            "INBOX",
            "1",
            self.KOPF,
            "vorgang",
            "owner",
            "2026-10-01",
            "",
            None,
            "2026-09-13 08:00",
        )
        assert v["frist"] == "2026-10-01"
        assert "frist_grund" not in v

    def test_should_set_the_waiting_state_word_for_the_waiting_bucket(self, pfade):
        v = board.vorgang_aus_mail(
            _ledger(naechste=1),
            "ad",
            "INBOX",
            "1",
            self.KOPF,
            "vorgang",
            "warten",
            None,
            "wartet auf Rueckmeldung",
            None,
            "2026-09-13 08:00",
        )
        assert v["zustand"] == "eingang-13-09-warte"

    def test_should_take_an_explicit_kurz_over_the_derived_one(self, pfade):
        v = board.vorgang_aus_mail(
            _ledger(naechste=1),
            "ad",
            "INBOX",
            "1",
            self.KOPF,
            "vorgang",
            "owner",
            None,
            "x",
            "Eigener Kurztext",
            "2026-09-13 08:00",
        )
        assert v["kurz"] == "Eigener Kurztext"

    def test_should_pass_the_referenzen_ordner_check_for_a_single_word_folder(
        self, pfade
    ):
        v = board.vorgang_aus_mail(
            _ledger(naechste=1),
            "ad",
            "INBOX",
            "164024",
            self.KOPF,
            "vorgang",
            "owner",
            None,
            "x",
            None,
            "2026-09-13 14:32",
        )
        ab, _davor = referenzen.pruefe_ordner({"vorgaenge": [v]}, {})
        assert ab == []

    def test_should_pass_the_referenzen_ordner_check_for_a_multi_word_folder(
        self, pfade
    ):
        v = board.vorgang_aus_mail(
            _ledger(naechste=1),
            "hnu",
            "Gesendete Objekte",
            "34349",
            self.KOPF,
            "vorgang",
            "owner",
            None,
            "x",
            None,
            "2026-09-13 14:32",
        )
        ab, _davor = referenzen.pruefe_ordner({"vorgaenge": [v]}, {})
        assert ab == []


class TestNeuKommando:
    """`board.py --neu` legt einen Vorgang aus einer Mail an (V2, #3015 K4)."""

    def test_should_create_a_vorgang_via_manual_headers_without_touching_imap(
        self, pfade, tmp_path
    ):
        ledger = tmp_path / "l.json"
        ledger.write_text(json.dumps(_ledger(naechste=1)), "utf-8")
        rc = board.main(
            [
                "--ledger",
                str(ledger),
                "--neu",
                "ad",
                "INBOX#164024",
                "--typ",
                "vorgang",
                "--von",
                "max.muster@example.org",
                "--betreff",
                "Anfrage Musterarbeit",
                "--datum",
                "2026-09-10",
                "--grund",
                "noch offen",
                "--ohne-anker",
            ]
        )
        assert rc == 0
        v = json.loads(ledger.read_text())["vorgaenge"][0]
        assert v["nr"] == 1
        assert v["thread_key"] == "Anfrage Musterarbeit"
        assert v["konto"] == "ad"

    def test_should_error_clearly_for_iil_without_manual_headers(self, pfade, tmp_path):
        ledger = tmp_path / "l.json"
        ledger.write_text(json.dumps(_ledger(naechste=1)), "utf-8")
        rc = board.main(
            [
                "--ledger",
                str(ledger),
                "--neu",
                "iil",
                "INBOX#1",
                "--typ",
                "vorgang",
                "--grund",
                "x",
            ]
        )
        assert rc == 1
        assert json.loads(ledger.read_text())["vorgaenge"] == []

    def test_should_refuse_missing_typ(self, pfade, tmp_path):
        ledger = tmp_path / "l.json"
        ledger.write_text(json.dumps(_ledger(naechste=1)), "utf-8")
        with pytest.raises(SystemExit):
            board.main(
                [
                    "--ledger",
                    str(ledger),
                    "--neu",
                    "ad",
                    "INBOX#1",
                    "--von",
                    "a@b.de",
                    "--betreff",
                    "x",
                    "--datum",
                    "2026-09-10",
                    "--grund",
                    "x",
                ]
            )

    def test_should_set_an_anchor_when_a_message_id_is_known(self, pfade, tmp_path):
        """Manuelle Kopfangaben tragen keine Message-ID — kein Anker, kein Fehler."""
        ledger = tmp_path / "l.json"
        ledger.write_text(json.dumps(_ledger(naechste=1)), "utf-8")
        rc = board.main(
            [
                "--ledger",
                str(ledger),
                "--neu",
                "ad",
                "INBOX#164024",
                "--typ",
                "vorgang",
                "--von",
                "max.muster@example.org",
                "--betreff",
                "Anfrage Musterarbeit",
                "--datum",
                "2026-09-10",
                "--grund",
                "noch offen",
            ]
        )
        assert rc == 0
        # Ohne message_id (manueller Kopf) bleibt board.ANKER unveraendert.
        anker_inhalt = json.loads(board.ANKER.read_text())
        assert "1" not in anker_inhalt

    def test_should_still_close_the_existing_frist_flag_meaning_without_neu(
        self, pfade, tmp_path
    ):
        """`--frist NR --datum ...` (ohne --neu) bleibt unveraendert (#2592 K4)."""
        ledger = tmp_path / "l.json"
        ledger.write_text(
            json.dumps(_ledger(_v(nr=7, bucket="owner"), naechste=8)), "utf-8"
        )
        rc = board.main(
            ["--ledger", str(ledger), "--frist", "7", "--datum", "2026-09-30"]
        )
        assert rc == 0
        assert json.loads(ledger.read_text())["vorgaenge"][0]["frist"] == "2026-09-30"


class TestErledigtVerlangtAnker:
    """`--erledigt` verankert oder verweigert (V3, platform#3015 K4)."""

    def _ledger_mit(self, tmp_path, notiz="", konto="hnu", **zusatz):
        ledger = tmp_path / "l.json"
        v = _v(nr=7, bucket="owner", kurz="K", konto=konto, notiz=notiz, **zusatz)
        ledger.write_text(json.dumps(_ledger(v, naechste=8)), "utf-8")
        return ledger

    def test_should_close_when_an_anchor_already_exists(self, pfade, tmp_path):
        """Die `pfade`-Fixture hinterlegt bereits einen Anker fuer Nummer 3."""
        ledger = tmp_path / "l.json"
        ledger.write_text(
            json.dumps(_ledger(_v(nr=3, bucket="owner", kurz="K"), naechste=4)),
            "utf-8",
        )
        rc = board.main(
            ["--ledger", str(ledger), "--erledigt", "3", "--am", "2026-09-13"]
        )
        assert rc == 0
        assert json.loads(ledger.read_text())["vorgaenge"][0]["bucket"] == "erledigt"

    def test_should_auto_set_the_anchor_from_the_latest_reference_and_close(
        self, pfade, tmp_path, monkeypatch
    ):
        notiz = "2026-09-01 EINGANG (Max Mustermann, INBOX #164024): 'X'. Offen."
        ledger = self._ledger_mit(tmp_path, notiz=notiz)
        aufrufe = []
        monkeypatch.setattr(
            board,
            "setze_anker_aus_referenz",
            lambda nr, konto, ordner, uid, anker_pfad: (
                aufrufe.append((nr, konto, ordner, uid)) or True
            ),
        )
        rc = board.main(
            ["--ledger", str(ledger), "--erledigt", "7", "--am", "2026-09-13"]
        )
        assert rc == 0
        assert aufrufe == [(7, "hnu", "INBOX", "164024")]
        assert json.loads(ledger.read_text())["vorgaenge"][0]["bucket"] == "erledigt"

    def test_should_refuse_and_leave_the_ledger_unchanged_when_no_anchor_can_be_set(
        self, pfade, tmp_path, monkeypatch
    ):
        ledger = self._ledger_mit(tmp_path, notiz="")
        monkeypatch.setattr(board, "setze_anker_aus_referenz", lambda *a: False)
        vorher = ledger.read_text()
        rc = board.main(
            ["--ledger", str(ledger), "--erledigt", "7", "--am", "2026-09-13"]
        )
        assert rc == 1
        assert ledger.read_text() == vorher

    def test_should_close_anyway_with_ohne_anker_and_mark_the_entry(
        self, pfade, tmp_path
    ):
        ledger = self._ledger_mit(tmp_path, notiz="")
        rc = board.main(
            [
                "--ledger",
                str(ledger),
                "--erledigt",
                "7",
                "--am",
                "2026-09-13",
                "--ohne-anker",
            ]
        )
        assert rc == 0
        v = json.loads(ledger.read_text())["vorgaenge"][0]
        assert v["bucket"] == "erledigt"
        assert "(ohne Anker geschlossen)" in v["notiz"]

    def test_should_not_require_an_anchor_to_close_an_already_closed_item(
        self, pfade, tmp_path
    ):
        ledger = tmp_path / "l.json"
        ledger.write_text(
            json.dumps(
                _ledger(
                    _v(
                        nr=7,
                        bucket="erledigt",
                        erledigt_am="2026-09-01",
                        notiz="2026-09-01 ERLEDIGT (Owner): x",
                    ),
                    naechste=8,
                )
            ),
            "utf-8",
        )
        rc = board.main(
            ["--ledger", str(ledger), "--erledigt", "7", "--am", "2026-09-13"]
        )
        assert rc == 0


# --- V10: Typen-Export für die Morgen-Zeitung -------------------------------

#: Ein Ledger mit drei Typen, der in jedem Feld etwas trägt, das NICHT
#: hinausdarf. Die Werte sind erfunden, aber an der Stelle, an der im echten
#: Ledger Name, Betreff und Notiz stehen — genau darüber prüft
#: `test_should_export_no_value_from_content_fields`.
GEHEIM = {
    "thread_key": "pruefstein-fadenschluessel",
    "gegenueber": "Pruefstein Gegenueber",
    "notiz": "Pruefstein Notiztext",
}


def _typen_ledger():
    return _ledger(
        _v(
            nr=1,
            typ="dsb-beratung",
            bucket="owner",
            frist="2026-09-20",
            kurz="Kurz-Pruefstein-A",
            **GEHEIM,
        ),
        _v(
            nr=2,
            typ="dsb-beratung",
            bucket="agent",
            frist="2026-09-15",
            kurz="Kurz-Pruefstein-B",
            **GEHEIM,
        ),
        _v(nr=3, typ="loeschung", bucket="warten", kurz="Kurz-Pruefstein-C", **GEHEIM),
        _v(
            nr=4,
            typ="betreuung-masterarbeit",
            bucket="owner",
            frist="2026-10-01",
            kurz="Kurz-Pruefstein-D",
            **GEHEIM,
        ),
        _v(
            nr=5,
            typ="loeschung",
            bucket="erledigt",
            erledigt_am="2026-09-01",
            kurz="Kurz-Pruefstein-E",
            **GEHEIM,
        ),
        naechste=6,
    )


class TestTypenExport:
    """`--typen` beantwortet „gibt es dazu etwas Offenes?" — und sonst nichts."""

    def test_should_group_open_items_by_type(self, pfade):
        uebersicht = board.typen_uebersicht(_typen_ledger())

        assert uebersicht["dsb-beratung"]["offen"] == 2
        assert uebersicht["loeschung"]["offen"] == 1
        assert uebersicht["betreuung-masterarbeit"]["offen"] == 1

    def test_should_report_the_earliest_deadline_of_a_type(self, pfade):
        uebersicht = board.typen_uebersicht(_typen_ledger())

        assert uebersicht["dsb-beratung"]["aelteste_frist"] == "2026-09-15"
        assert uebersicht["loeschung"]["aelteste_frist"] is None

    def test_should_not_count_closed_items_as_open(self, pfade):
        """Vorgang 5 ist erledigt — sonst stünde bei `loeschung` eine 2."""
        assert board.typen_uebersicht(_typen_ledger())["loeschung"]["offen"] == 1

    def test_should_carry_no_field_beyond_count_and_deadline(self, pfade):
        export = board.typen_export(_typen_ledger(), "2026-09-13")

        assert set(export) == {"stand", "typen"}
        assert export["stand"] == "2026-09-13"
        for werte in export["typen"].values():
            assert set(werte) == {"offen", "aelteste_frist"}

    def test_should_export_no_value_from_content_fields(self, pfade, tmp_path, capsys):
        """Die eigentliche Zusage: kein Name, kein Betreff, keine Notiz wandert mit.

        Geprüft wird gegen den Fixture-Text selbst — nicht gegen eine Liste von
        Feldnamen. Ein neues Inhaltsfeld im Ledger fiele einer Feldnamen-Liste
        durch, dem Vergleich mit dem Fixture-Wert nicht.
        """
        ledger = tmp_path / "ledger.json"
        ledger.write_text(json.dumps(_typen_ledger()), encoding="utf-8")

        assert board.main(["--ledger", str(ledger), "--typen"]) == 0
        text = capsys.readouterr().out
        assert board.main(["--ledger", str(ledger), "--typen", "--json"]) == 0
        text += capsys.readouterr().out

        for wert in [*GEHEIM.values(), *[f"Kurz-Pruefstein-{b}" for b in "ABCDE"]]:
            assert wert not in text, f"{wert!r} hat die Arbeitsliste verlassen"

    def test_should_print_three_columns_and_no_fourth(self, pfade, tmp_path, capsys):
        ledger = tmp_path / "ledger.json"
        ledger.write_text(json.dumps(_typen_ledger()), encoding="utf-8")

        board.main(["--ledger", str(ledger), "--typen"])
        zeilen = capsys.readouterr().out.strip().split("\n")

        assert zeilen[0] == "typ | offen | aelteste_frist"
        assert all(len(z.split(" | ")) == 3 for z in zeilen[1:])
        assert "dsb-beratung | 2 | 2026-09-15" in zeilen

    def test_should_take_the_reference_date_from_stichtag(
        self, pfade, tmp_path, capsys
    ):
        """Ohne festes Datum wäre der Export nicht wiederholbar (#2592 K1)."""
        ledger = tmp_path / "ledger.json"
        ledger.write_text(json.dumps(_typen_ledger()), encoding="utf-8")

        board.main(
            ["--ledger", str(ledger), "--typen", "--json", "--stichtag", "2026-01-02"]
        )

        assert json.loads(capsys.readouterr().out)["stand"] == "2026-01-02"
