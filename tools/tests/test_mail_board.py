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
            _ledger(_v(nr=3, bucket="erledigt", erledigt_am=heute, kurz="Fertig")), heute
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
