"""Ausschlusskonfiguration für die Mail-Indexierung (ADR-286 §4.10.7).

Die Prüffälle stammen aus dem gemessenen Ordner-Rauschbericht vom 2026-07-28 über
die beiden realen Postfächer — nicht aus erfundenen Namen. Der wichtigste Teil sind
die **Negativfälle**: Ein Ausschluss, der zu viel trifft, entfernt fachliche Post
still aus der Indexierung, und genau das wäre schlimmer als gar kein Ausschluss.
"""

import importlib.util
import pathlib

_SRC = pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "indexierung.py"
_spec = importlib.util.spec_from_file_location("indexierung", _SRC)
ix = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ix)

LEER = pathlib.Path("/nonexistent-index-exclude-list")


def _aus(ordner):
    return ix.ist_ausgeschlossen(ordner, LEER)


# --- freigegebene Liste (Owner 2026-07-28) --------------------------------


def test_should_exclude_papierkorb_and_junk():
    for name in ("Gelöschte Elemente", "Junk-E-Mail", "Papierkorb", "Spam"):
        assert _aus(name), name


def test_should_exclude_imap_utf7_encoded_trash_name():
    """Der Server liefert 'Gel&APY-schte Objekte' roh — so muss es getroffen werden."""
    assert _aus("Gel&APY-schte Objekte")


def test_should_exclude_editorial_folders():
    for name in (
        "Posteingang/MediumDaily",
        "AI-News",
        "Posteingang/DSGVO - News",
        "Trading/Zacks",
        "Newsletter",
        "Werbung",
        "RSS-Abonnements",
    ):
        assert _aus(name), name


def test_should_exclude_technical_folders_including_children():
    assert _aus("Synchronisierungsprobleme")
    assert _aus("Synchronisierungsprobleme/Konflikte")
    assert _aus("Synchronisierungsprobleme/Lokale Fehler")


# --- Nicht-Mail-Ordner (Kalender/Kontakte/Aufgaben) -----------------------


def test_should_exclude_non_mail_folders():
    """Exchange gibt diese Ordner über IMAP nicht als RFC822 heraus.

    Gemessen am Konto hnu (2026-07-31): 2.488 von 6.035 Index-Einträgen waren
    Platzhalter mit dem Betreff "Retrieval using the IMAP4 protocol failed for
    the following message: <n>" — ohne Absender, ohne Datum, und exakt
    deckungsgleich mit den 2.488 Einträgen ohne `sent_at`.
    """
    for name in ("Kalender", "Calendar", "Kontakte", "Contacts", "Aufgaben", "Tasks"):
        assert _aus(name), name


def test_should_exclude_non_mail_children():
    """Ein Treffer auf dem Elternsegment nimmt die Unterordner mit.

    Real vorgefunden: 'Kalender/Feiertage in Deutschland' (101 Platzhalter) und
    'Kalender/Achim Dehnert' (13).
    """
    assert _aus("Kalender/Feiertage in Deutschland")
    assert _aus("Kalender/Achim Dehnert")


def test_should_not_exclude_business_folders_starting_like_non_mail():
    """Der Ausschluss matcht ganze Segmente, nicht Präfixe.

    Ein Kundenordner 'Kalenderverlag' oder ein Vorgang 'Aufgabenheft' ist Post
    und muss drinbleiben — dieselbe Falle wie 'Junker' unter 'junk'.
    """
    for name in (
        "Kalenderverlag",
        "Aufgabenheft",
        "Kontaktformulare",
        "IIL.Kunden/Journalismus",
    ):
        assert _aus(name) is None, name


# --- Jahresarchive bis 2024 (Owner-Ergänzung) -----------------------------


def test_should_exclude_year_archives_up_to_2024():
    for jahr in range(2019, 2025):
        assert _aus(f"Archiv/{jahr}"), jahr
        assert _aus(f"Sent-Archiv/{jahr}"), jahr


def test_should_exclude_the_und_aelter_archive():
    assert _aus("Archiv/2019-und-aelter")
    assert _aus("Sent-Archiv/2019-und-aelter")


def test_should_keep_year_archives_after_2024():
    assert _aus("Archiv/2025") is None
    assert _aus("Archiv/2026") is None
    assert _aus("Sent-Archiv/2025") is None


def test_should_keep_undated_archive_folder():
    """Der flache IIL-Ordner 'Archiv' (22.626 Nachrichten) trägt kein Jahr.

    'bis 2024' ist auf ihn nicht anwendbar — er bleibt drin, bis entschieden ist,
    welchen Zeitraum er abdeckt. Ihn mitzunehmen hiesse, unter der Ueberschrift
    'bis 2024' den groessten Einzelbestand ungeprueft auszuschliessen.
    """
    assert _aus("Archiv") is None


# --- Negativfälle: fachliche Post darf NIE stillschweigend rausfallen ------


def test_should_never_exclude_business_folders():
    for name in (
        "INBOX",
        "Posteingang",
        "Gesendete Elemente",
        "Gesendete Objekte",
        "IIL.Kunden/Scheppach",
        "IIL.Kunden/Feha",
        "IIL.Partner/DHRW",
        "MEIKI/Landkreis-Guenzburg",
        "MEIKI/HNU-intern",
        "Betreuungen/Muster-Max",
        "sevdesk",
        "IIL.Finanzen/Rechnungen",
        "IIL.Lieferanten/Hosting",
    ):
        assert _aus(name) is None, name


def test_should_not_match_substrings_of_business_names():
    """Ein Kunde 'Junker' darf nicht unter 'junk' fallen, 'Werbungskosten' nicht
    unter 'Werbung' — deshalb Segment-Anker statt Teilstring."""
    assert _aus("IIL.Kunden/Junker") is None
    assert _aus("IIL.Kunden/Werbungskosten") is None
    assert _aus("Archive/Newsletterversand") is None


def test_should_keep_operational_machine_mail():
    """Betriebliche Maschinenpost traegt Fristen (Azure-Fall 2026-07-23) und bleibt
    indexiert — ausgeschlossen wird nur Redaktionelles."""
    for name in ("Mittwald", "Github", "IIL.Lieferanten/Telekom", "IIL.Recht"):
        assert _aus(name) is None, name


# --- Aufteilung + lokale Liste --------------------------------------------


def test_should_split_into_both_sets_and_lose_nothing():
    ordner = ["INBOX", "Junk-E-Mail", "IIL.Kunden/Feha", "Archiv/2020"]
    behalten, raus = ix.aufteilen(ordner, LEER)
    assert behalten == ["INBOX", "IIL.Kunden/Feha"]
    assert [o for o, _ in raus] == ["Junk-E-Mail", "Archiv/2020"]
    assert len(behalten) + len(raus) == len(ordner)


def test_should_return_a_reason_not_a_boolean():
    """Der Grund landet im Deckungsausweis — ein blosses True erzeugte die stille
    Luecke, die der Ausweis sichtbar machen soll."""
    grund = _aus("Junk-E-Mail")
    assert isinstance(grund, str) and grund.strip()


def test_should_apply_local_exclusion_list(tmp_path):
    liste = tmp_path / "exclude.txt"
    liste.write_text("# Kommentar\nPosteingang/Freizeit\n\n", encoding="utf-8")
    assert ix.ist_ausgeschlossen("Posteingang/Freizeit", liste)
    assert ix.ist_ausgeschlossen("INBOX", liste) is None


def test_should_tolerate_missing_local_list():
    assert ix.ist_ausgeschlossen("INBOX", LEER) is None
