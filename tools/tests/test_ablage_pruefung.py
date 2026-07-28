"""Ablage-Prüfung: Beurteilungslogik ohne Postfach.

Der teuerste Fehler dieses Werkzeugs wäre ein **falscher Positivbefund**: Es meldet
eine korrekt abgelegte Nachricht als fehlsortiert, ein Aufräumlauf glaubt ihm und
reißt sie aus dem richtigen Archiv. Genau das ist am 2026-07-28 fast passiert — die
Vorgängerfassung beurteilte über den Ankunftsstempel statt über die Date-Kopfzeile
und meldete eine Nachricht von 2017 als 2026er Fehlablage, weil sie am selben Tag
umsortiert worden war.

Die Prüffälle bilden diesen Realfall nach und sichern die Grenzfall-Behandlung ab.
"""

import importlib.util
import pathlib

_SRC = pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "ablage_pruefung.py"
_spec = importlib.util.spec_from_file_location("ablage_pruefung", _SRC)
ap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ap)

JAHRGAENGE = {2019, 2020, 2021, 2022, 2023, 2024, 2025}


def _b(ordner, kopf_jahr, grenze=False, stempel=None, jetzt=2026):
    return ap.beurteile(ordner, kopf_jahr, grenze, stempel, jetzt, JAHRGAENGE)


# --- Datumsauswertung -----------------------------------------------------


def test_should_read_year_from_date_header():
    assert ap.jahr_und_grenzfall("Wed, 10 May 2017 07:28:11 +0200") == (2017, False)


def test_should_flag_year_boundary_as_ambiguous():
    """31.12. 23:30 +0200 ist in UTC noch 2025 — dieselbe Nachricht faellt je nach
    Bezugszeitzone in zwei Jahrgaenge. Mehrdeutig, nicht falsch."""
    jahr, grenze = ap.jahr_und_grenzfall("Thu, 1 Jan 2026 00:30:00 +0200")
    assert jahr == 2026 and grenze is True


def test_should_not_flag_a_normal_date_as_boundary():
    jahr, grenze = ap.jahr_und_grenzfall("Mon, 14 Jul 2025 12:00:00 +0200")
    assert jahr == 2025 and grenze is False


def test_should_return_none_for_unreadable_dates():
    for wert in (None, "", "irgendwann", "32 Foo 2020"):
        assert ap.jahr_und_grenzfall(wert)[0] is None


# --- Ordnernamen ----------------------------------------------------------


def test_should_recognise_year_folders_in_any_tree():
    assert ap.jahrgang_des_ordners("Archiv/2024") == (2024, False)
    assert ap.jahrgang_des_ordners("Sent-Archiv/2020") == (2020, False)
    assert ap.jahrgang_des_ordners("Sent-Archiv/2019-und-aelter") == (2019, True)


def test_should_not_mistake_business_folders_for_year_folders():
    for name in ("IIL.Kunden/Scheppach", "Archiv", "Betreuungen/Muster-Max"):
        assert ap.jahrgang_des_ordners(name) is None


def test_should_recognise_live_folders_in_both_languages():
    for name in ("INBOX", "Posteingang", "Gesendete Objekte", "Gesendete Elemente"):
        assert ap.ist_laufender_ordner(name) is True
    assert ap.ist_laufender_ordner("Archiv/2024") is False


# --- Kernbeurteilung ------------------------------------------------------


def test_should_accept_a_correctly_filed_message():
    assert _b("Archiv/2024", 2024) == []


def test_should_report_a_misfiled_message():
    assert _b("Archiv/2024", 2022) == ["A"]


def test_should_accept_older_mail_in_a_catch_all_folder():
    """'2019-und-aelter' nimmt alles bis einschliesslich 2019 auf."""
    assert _b("Sent-Archiv/2019-und-aelter", 2017) == []
    assert _b("Sent-Archiv/2019-und-aelter", 2019) == []
    assert _b("Sent-Archiv/2019-und-aelter", 2020) == ["A"]


def test_should_report_unarchived_mail_in_a_live_folder():
    assert _b("INBOX", 2025) == ["B"]


def test_should_accept_current_year_in_a_live_folder():
    assert _b("INBOX", 2026) == []


def test_should_report_a_missing_year_folder_alongside():
    """2015 hat keinen Jahrgangsordner — Befund B allein waere nicht umsetzbar."""
    assert _b("INBOX", 2015) == ["B", "C"]


def test_should_downgrade_boundary_cases_from_error_to_ambiguous():
    """Ein Grenzfall darf nicht als A oder B gemeldet werden, sonst schiebt ihn
    jeder Aufraeumlauf erneut hin und her."""
    assert _b("Archiv/2024", 2025, grenze=True) == ["D"]
    assert _b("INBOX", 2025, grenze=True) == ["D"]


def test_should_report_messages_without_a_usable_date():
    assert _b("Archiv/2024", None) == ["E"]


# --- der Realfall vom 2026-07-28 ------------------------------------------


def test_should_not_call_a_correctly_filed_2017_mail_misfiled():
    """Realfall: Nachricht vom 10.05.2017 in 'Sent-Archiv/2019-und-aelter', deren
    Ankunftsstempel beim Umsortieren auf 2026 gesetzt wurde. Die Vorgaengerfassung
    meldete sie als Fehlablage; sie liegt richtig.

    Erwartet: KEIN harter Befund, nur der Divergenz-Hinweis F.
    """
    befunde = _b("Sent-Archiv/2019-und-aelter", 2017, stempel=2026)
    assert "A" not in befunde
    assert befunde == ["F"]


def test_should_stay_silent_when_stamp_and_header_agree():
    assert _b("Archiv/2024", 2024, stempel=2024) == []


def test_should_report_divergence_alongside_a_real_misfiling():
    befunde = _b("Archiv/2024", 2022, stempel=2026)
    assert set(befunde) == {"F", "A"}


def test_should_treat_only_actionable_classes_as_hard_findings():
    """D, E und F sind Hinweise — sie duerfen den Exit-Code nicht auf 1 setzen."""
    assert set(ap.HART) == {"A", "B", "C"}


# --- Befunde aus dem ersten Lauf gegen ein echtes Postfach -----------------
#
# Beide Faelle waren Fehler des Werkzeugs, nicht des Postfachs. Sie kamen erst
# heraus, als es einmal gegen echte Ordner lief — kein Prueffall haette sie
# vorhergesagt.


def test_should_treat_a_catch_all_folder_as_covering_earlier_years():
    """Realfall: 13 Nachrichten von 2017 wurden als 'kein Jahrgangsordner
    vorhanden' gemeldet, obwohl 'Sent-Archiv/2019-und-aelter' genau dafuer da ist."""
    assert ap.jahr_ist_abgedeckt(2017, JAHRGAENGE, sammel_bis=2019) is True
    assert ap.jahr_ist_abgedeckt(2017, JAHRGAENGE, sammel_bis=None) is False
    assert ap.beurteile(
        "Gesendete Objekte", 2017, False, None, 2026, JAHRGAENGE, 2019
    ) == ["B"]


def test_should_not_let_a_catch_all_cover_later_years():
    assert ap.jahr_ist_abgedeckt(2026, JAHRGAENGE, sammel_bis=2019) is False


def test_should_skip_folders_without_mail():
    """Realfall: 565 'datumslose Nachrichten' waren Termine, Aufgaben und
    Kontakte. Ein Befund, der zu 97 % aus Nicht-Befunden besteht, wird nicht
    gelesen."""
    for name in (
        "Kalender",
        "Kalender/Feiertage in Deutschland",
        "Aufgaben",
        "Kontakte",
        "Synchronisierungsprobleme/Konflikte",
    ):
        assert ap.ist_mail_ordner(name) is False, name


def test_should_keep_checking_real_mail_folders():
    for name in ("INBOX", "Archiv/2024", "IIL.Kunden/Scheppach", "Betreuungen/Anfragen"):
        assert ap.ist_mail_ordner(name) is True, name
