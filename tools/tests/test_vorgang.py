"""Tests für die Vorgangs-Sicht (ADR-286 §4.9).

Die Logik ist bewusst von IMAP getrennt, deshalb laufen diese Tests ohne Postfach —
sie prüfen genau das, was fachlich entscheidet: wie aus einem Ordnerbaum Vorgänge
werden und wie eine Zuordnung entsteht, die mehrdeutige Fälle NICHT stillschweigend
auflöst.
"""

import importlib.util
import pathlib

_SRC = pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "vorgang.py"
_spec = importlib.util.spec_from_file_location("vorgang", _SRC)
vg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vg)


ORDNER = [
    "INBOX",
    "Archiv",
    "Archiv/2025",
    "Betreuungen",
    "Betreuungen/Anfragen",
    "Betreuungen/Muster-Max",
    "Betreuungen/Beispiel-Anna",
    "Betreuungen/.erledigt",
    "Betreuungen/.erledigt/Alt-Fall",
    "Betreuungen/Tief/Zu/Tief",
    "AndererBaum/Nicht-Relevant",
]


def test_should_derive_vorgaenge_only_below_the_root():
    vs = vg.vorgaenge_aus_ordnern(ORDNER, "Betreuungen")
    namen = {v.name for v in vs}
    assert "Nicht-Relevant" not in namen
    assert "2025" not in namen
    assert {"Muster-Max", "Beispiel-Anna", "Anfragen", "Alt-Fall"} <= namen


def test_should_mark_closed_vorgaenge_from_the_tree_position():
    vs = {v.name: v for v in vg.vorgaenge_aus_ordnern(ORDNER, "Betreuungen")}
    assert vs["Alt-Fall"].abgeschlossen is True
    assert vs["Muster-Max"].abgeschlossen is False


def test_should_ignore_deeper_nesting_instead_of_guessing():
    # Ein Vorgang ist EINE Ebene. Tiefere Pfade sind etwas anderes und werden
    # nicht zu einem Vorgang erklärt, nur weil sie unterhalb der Wurzel liegen.
    namen = {v.name for v in vg.vorgaenge_aus_ordnern(ORDNER, "Betreuungen")}
    assert not any("/" in n for n in namen)
    assert "Tief" not in namen


def test_should_sort_open_before_closed():
    vs = vg.vorgaenge_aus_ordnern(ORDNER, "Betreuungen")
    zustaende = [v.abgeschlossen for v in vs]
    assert zustaende == sorted(zustaende)


# --- Zuordnung ---------------------------------------------------------------


def test_should_map_unique_sender_to_its_vorgang():
    eindeutig, mehrdeutig = vg.zuordnung_bauen(
        {"Muster-Max": {"max@example.com"}, "Beispiel-Anna": {"anna@example.com"}}
    )
    assert eindeutig == {
        "max@example.com": "Muster-Max",
        "anna@example.com": "Beispiel-Anna",
    }
    assert mehrdeutig == {}


def test_should_keep_ambiguous_senders_separate_instead_of_picking_one():
    # Realer Fall: Zweitgutachter, Sekretariat, Prüfungsamt kommen in mehreren
    # Vorgängen vor. Einen davon zu wählen wäre eine stille Falschzuordnung.
    eindeutig, mehrdeutig = vg.zuordnung_bauen(
        {
            "Muster-Max": {"max@example.com", "amt@example.com"},
            "Beispiel-Anna": {"anna@example.com", "amt@example.com"},
        }
    )
    assert "amt@example.com" not in eindeutig
    assert mehrdeutig["amt@example.com"] == ["Beispiel-Anna", "Muster-Max"]


def test_should_normalise_case_of_addresses():
    eindeutig, _ = vg.zuordnung_bauen({"Muster-Max": {"Max@Example.COM"}})
    assert eindeutig == {"max@example.com": "Muster-Max"}


def test_should_not_call_a_sender_ambiguous_when_the_same_vorgang_repeats():
    eindeutig, mehrdeutig = vg.zuordnung_bauen({"Muster-Max": {"max@example.com"}})
    assert mehrdeutig == {}
    assert eindeutig["max@example.com"] == "Muster-Max"


# --- Vorschlag ---------------------------------------------------------------


def test_should_classify_a_sender_into_one_of_three_buckets():
    eindeutig = {"max@example.com": "Muster-Max"}
    mehrdeutig = {"amt@example.com": ["A", "B"]}
    assert vg.vorschlag_fuer("max@example.com", eindeutig, mehrdeutig) == (
        "eindeutig",
        ["Muster-Max"],
    )
    assert vg.vorschlag_fuer("AMT@example.com", eindeutig, mehrdeutig) == (
        "mehrdeutig",
        ["A", "B"],
    )
    assert vg.vorschlag_fuer("fremd@example.com", eindeutig, mehrdeutig) == (
        "unbekannt",
        [],
    )
    assert vg.vorschlag_fuer("", eindeutig, mehrdeutig) == ("unbekannt", [])


def test_should_not_treat_the_closed_container_as_a_vorgang():
    # `Betreuungen/.erledigt` ist der Sammelordner, kein Vorgang — er tauchte im
    # ersten Lauf gegen das echte Postfach faelschlich als "offen" auf.
    namen = {v.name for v in vg.vorgaenge_aus_ordnern(ORDNER, "Betreuungen")}
    assert ".erledigt" not in namen


# --- Trefferqualität der Sachsuche -------------------------------------------


def test_should_warn_about_short_search_terms():
    # Realmessung 2026-07-27: derselbe 3-Zeichen-Begriff lieferte 0 / 327 / 678
    # Treffer je nach Feld. Ohne Hinweis liest man 678 als "der Sachverhalt".
    h = vg.such_hinweis("OZG", "BODY")
    assert any("kurz" in x for x in h)


def test_should_point_out_that_text_includes_headers():
    assert any("Kopfzeilen" in x for x in vg.such_hinweis("Penetrationstest", "TEXT"))


def test_should_stay_quiet_for_a_long_term_in_a_narrow_field():
    assert vg.such_hinweis("Penetrationstest", "SUBJECT") == []
