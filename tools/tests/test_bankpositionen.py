"""Tests für tools/sevdesk/bankpositionen.py — offene Bankpositionen als Arbeitsliste.

Die sevdesk-API wird in keinem Test angefasst: geprüft werden die reinen Funktionen
(Händler-Erkennung, Kontenzuordnung, Sammelbuchungs-Guard, Kürzung) und das
Board-Rendering gegen ein Temp-Verzeichnis.

Anlass: Retro 2026-07-29 Befund #4 — das Werkzeug ging ohne Tests in den Merge,
belegt war es nur über einen Live-Lauf. Slug `untested-tool-module-green-gate`,
drittes Vorkommen über die Retros.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sevdesk"))

# Bewusst KEIN `pytest.importorskip`: das machte den Ausfall still. Im ersten CI-Lauf
# fehlte `httpx`, das Modul war nicht importierbar, und alle 22 Tests wurden
# übersprungen — der Lauf war grün, die Abdeckung null. Ein harter Import lässt einen
# solchen Fehler laut scheitern. `httpx` ist inzwischen lazy in `hole()` importiert,
# die reinen Funktionen brauchen es nicht.
import bankpositionen as bp  # noqa: E402


# ── PayPal-Händler: drei Schreibweisen, jede kostete beim Bau einen Fehlversuch ──


@pytest.mark.parametrize(
    ("zweck", "erwartet"),
    [
        # Variante A — mit PP-Block und Schrägstrichen
        (
            "1047470049958/PP.6820.PP/. Cleverbridge GmbH, Ihr Einkauf bei Cleverbridge",
            "Cleverbridge GmbH",
        ),
        # Variante B — ohne PP-Block
        ("1048171118267/. Ionos SE, Ihr Einkauf bei Ionos SE", "Ionos SE"),
        # Variante C — Leerzeichen statt Schrägstrich
        (
            "1049697671020 PP.1321.PP . Spotify AB, Ihr Einkauf bei Spotify AB",
            "Spotify AB",
        ),
        # Händler mit Komma im Namen — bricht am ERSTEN Komma ab (dokumentiertes Verhalten)
        ("1051431380713 PP.6820.PP . GitHub, Inc., Ihr Einkauf bei GitHub", "GitHub"),
    ],
)
def test_should_extract_merchant_from_all_three_purpose_formats(zweck, erwartet):
    assert bp.paypal_haendler(zweck) == erwartet


@pytest.mark.parametrize(
    "zweck", ["", "SEPA Sammel-Ueberweisung mit 2 Ueberweisungen", None]
)
def test_should_return_empty_when_no_merchant_pattern(zweck):
    assert bp.paypal_haendler(zweck) == ""


# ── Kontenzuordnung: erste passende Regel gewinnt ──


REGELN = [
    {
        "muster": "dehnert (mara|sabine)",
        "konto": "6035",
        "bezeichnung": "Löhne Minijob",
        "nur_betraege": [850.0, 450.0, 400.0],
    },
    {"muster": "knappschaft", "konto": "6110", "bezeichnung": "Sozialvers."},
    {
        "muster": "umsatzsteuer auf .*abrechnung",
        "konto": "KLÄRUNG",
        "bezeichnung": "USt-Anteil",
        "anmerkung": "offen",
    },
    {"muster": "hetzner|ionos", "konto": "6837", "bezeichnung": "Lizenzen"},
]


def test_should_apply_first_matching_rule():
    konto, bez, _ = bp.zuordnen("dehnert mara überweisung", -450.0, REGELN)
    assert (konto, bez) == ("6035", "Löhne Minijob")


def test_should_return_empty_when_no_rule_matches():
    assert bp.zuordnen("völlig unbekannter zahlungsempfänger", -12.0, REGELN) == (
        "",
        "",
        "",
    )


def test_should_match_case_insensitively():
    konto, _, _ = bp.zuordnen("KNAPPSCHAFT-BAHN-SEE BEITRAG", -215.46, REGELN)
    assert konto == "6110"


def test_should_park_unresolved_positions_without_guessing_an_account():
    konto, _, anmerkung = bp.zuordnen(
        "19% Umsatzsteuer auf EUR 21,30- Abrechnung per 31.01.", -4.05, REGELN
    )
    assert konto == "KLÄRUNG"
    assert anmerkung == "offen"


# ── Sammelbuchungs-Guard: nicht stillschweigend ganz zuordnen ──


def test_should_accept_amount_that_matches_a_known_item_exactly():
    _, _, anmerkung = bp.zuordnen("dehnert sabine", -400.0, REGELN)
    assert anmerkung == ""


def test_should_flag_partial_coverage_when_amount_exceeds_known_items():
    """901,18 = 850 Lohn + 51,18 Fremdposten — der Rest darf nicht mitwandern."""
    konto, _, anmerkung = bp.zuordnen("SEPA Sammel dehnert mara", -901.18, REGELN)
    assert konto == "6035"
    assert "NUR TEILWEISE" in anmerkung
    assert "51,18" in anmerkung or "51.18" in anmerkung


def test_should_flag_amount_smaller_than_every_known_item():
    _, _, anmerkung = bp.zuordnen("dehnert mara", -12.50, REGELN)
    assert "BETRAG UNBEKANNT" in anmerkung


# ── Kürzung ──


def test_should_shorten_long_text_with_ellipsis():
    assert bp.kurz("A" * 50, 10) == "A" * 9 + "…"


def test_should_collapse_whitespace_and_keep_short_text():
    assert bp.kurz("  viel   Abstand \n hier ", 40) == "viel Abstand hier"


# ── Board-Rendering ──


def _zeile(nr, betrag, konto="", bez="", anm="", haendler="", name="X", zweck="Z"):
    return {
        "nr": nr,
        "id": f"id{nr}",
        "datum": "2026-01-01",
        "betrag": betrag,
        "name": name,
        "zweck": zweck,
        "konto": konto,
        "bez": bez,
        "anm": anm,
        "haendler": haendler,
    }


def test_should_split_board_into_open_klaerung_and_assigned(tmp_path):
    ziel = tmp_path / "board.md"
    stand = bp.board_schreiben(
        [
            _zeile(1, -10.0, konto="6837", bez="Lizenzen"),
            _zeile(2, -4.05, konto="KLÄRUNG", bez="USt", anm="offen"),
            _zeile(3, -99.0),
        ],
        ziel,
        2026,
    )
    assert stand == {"zugeordnet": 1, "klaerung": 1, "offen": 1}
    text = ziel.read_text(encoding="utf-8")
    assert (
        "## Noch offen" in text and "## In Klärung" in text and "## Zugeordnet" in text
    )
    assert "`id3`" in text  # Umsatz-ID der offenen Position trägt die Zuordnung


def test_should_omit_empty_open_section(tmp_path):
    ziel = tmp_path / "board.md"
    bp.board_schreiben([_zeile(1, -10.0, konto="6837", bez="Lizenzen")], ziel, 2026)
    assert "## Noch offen" not in ziel.read_text(encoding="utf-8")


def test_should_mark_partial_assignment_visibly(tmp_path):
    ziel = tmp_path / "board.md"
    bp.board_schreiben(
        [
            _zeile(
                1,
                -901.18,
                konto="6035",
                bez="Lohn",
                anm="NUR TEILWEISE — 51,18 € nicht abgedeckt",
            )
        ],
        ziel,
        2026,
    )
    text = ziel.read_text(encoding="utf-8")
    assert "⚠" in text
    assert "Nur teilweise zugeordnet" in text


def test_should_prefer_merchant_over_payer_name_in_board(tmp_path):
    ziel = tmp_path / "board.md"
    bp.board_schreiben(
        [_zeile(1, -21.99, name="PayPal Europe S.a.r.l.", haendler="Spotify AB")],
        ziel,
        2026,
    )
    assert "PayPal → Spotify AB" in ziel.read_text(encoding="utf-8")


# ── Token-Datei: KEY=WERT, nicht der rohe Wert (kostete beim Bau einen 401) ──


def test_should_read_token_from_key_value_file(tmp_path):
    p = tmp_path / "tok"
    p.write_text("sevdesk_api_token=abc123\n", encoding="utf-8")
    assert bp.token_lesen(p) == "abc123"


def test_should_read_token_from_raw_file(tmp_path):
    p = tmp_path / "tok"
    p.write_text("abc123\n", encoding="utf-8")
    assert bp.token_lesen(p) == "abc123"
