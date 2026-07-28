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


def test_should_keep_non_correspondence_configs_out_of_the_account_denominator(
    tmp_path,
):
    """Pilotbefund 2026-07-27: 'Konten 1/4' zählte das Referenzpostfach mit.

    Ein Nenner, der zu gross ist, ist genauso falsch wie einer, der fehlt — er laesst
    einen vollstaendigen Lauf unvollstaendig aussehen.

    Der Test baut die Konfiguration selbst auf. Gegen das echte Home-Verzeichnis waere
    er auf einer CI-Maschine ohne Mail-Konfiguration inhaltsleer — er lief dann durch,
    ohne irgendetwas zu pruefen.
    """
    assert "search" in vg.KEINE_KORRESPONDENZ
    assert "folders" in vg.KEINE_KORRESPONDENZ

    imap = "IMAP_HOST=imap.example.org\n"
    (tmp_path / "mail.env").write_text(imap, encoding="utf-8")
    for name in ("hnu", "search"):
        (tmp_path / f"mail-{name}.env").write_text(imap, encoding="utf-8")
    # Routing-Tabelle: sieht wie eine Konfiguration aus, hat aber keinen Lese-Zugang
    (tmp_path / "mail-folders.env").write_text(
        "IIL.Kunden/Foo | kunde | foo.de\n", encoding="utf-8"
    )

    konten = vg.bekannte_konten(tmp_path)
    assert konten == ["default", "hnu"], konten
    assert "search" not in konten, "das Referenzpostfach ist keine echte Korrespondenz"
    assert "folders" not in konten


def test_should_drop_configs_without_a_read_access(tmp_path):
    """Struktur schlägt Namensliste: ohne IMAP_HOST ist es kein lesbares Postfach.

    Realstand 2026-07-28: `mail.env` trug nur SMTP (Versand) und stand trotzdem als
    Konto `default` im Nenner. Eine Namensliste haette das nur gefangen, wenn jemand
    `default` vorher hineingeschrieben haette — der Strukturfilter fängt auch den
    naechsten, noch unbekannten Fall.
    """
    (tmp_path / "mail.env").write_text("SMTP_HOST=smtp.example.org\n", encoding="utf-8")
    (tmp_path / "mail-hnu.env").write_text(
        "IMAP_HOST=imap.example.org\n", encoding="utf-8"
    )
    assert vg.bekannte_konten(tmp_path) == ["hnu"]


def test_should_read_graph_accounts_from_the_config_as_second_source(tmp_path):
    """Das Token-Verzeichnis kennt nur Konten, in die schon eingeloggt wurde.

    Ein konfiguriertes Konto ohne Token fiele still aus dem Nenner — genau die Luecke,
    gegen die diese Zaehlung gebaut ist.
    """
    (tmp_path / "calendar.env").write_text(
        "GRAPH_ACCOUNTS=neu@example.org\nGRAPH_TENANT=x\n", encoding="utf-8"
    )
    (tmp_path / "mail-hnu.env").write_text(
        "IMAP_HOST=imap.example.org\n", encoding="utf-8"
    )
    konten = vg.bekannte_konten(tmp_path)
    assert konten == ["hnu", "graph:neu@example.org"], konten


def test_should_not_double_count_an_account_present_in_both_sources(tmp_path):
    tokens = tmp_path / "graph-mail-tokens"
    tokens.mkdir()
    (tokens / "a_at_x.de.json").write_text("{}", encoding="utf-8")
    (tmp_path / "calendar.env").write_text("GRAPH_ACCOUNTS=a@x.de\n", encoding="utf-8")
    assert vg.bekannte_konten(tmp_path) == ["graph:a@x.de"]


def test_should_count_graph_only_mailboxes_in_the_denominator(tmp_path):
    """Pilotbefund 2026-07-27: das IIL-Konto laeuft ueber Graph und fehlte im Nenner.

    Ein Konto, das dieses Werkzeug nicht ansprechen kann, muss sichtbar fehlen — sonst
    sieht ein Lauf ueber 1 von 3 Postfaechern wie 1 von 2 aus.

    Der Test bringt sein eigenes Token-Verzeichnis mit. Die erste Fassung las das echte
    Home-Verzeichnis: lokal gruen, in der CI rot (Lauf 30295192917) — ein Test, der die
    Maschine misst statt den Code.
    """
    (tmp_path / "achim.dehnert_at_iil.gmbh.json").write_text("{}", encoding="utf-8")
    (tmp_path / "zweite_at_example.org.json").write_text("{}", encoding="utf-8")

    konten = vg.graph_konten(tmp_path)
    assert konten == ["graph:achim.dehnert@iil.gmbh", "graph:zweite@example.org"]
    assert all("@" in k for k in konten), "Kontoname soll die Adresse tragen"


def test_should_return_no_graph_accounts_when_the_token_directory_is_absent(tmp_path):
    """Fehlt das Verzeichnis, ist die Antwort leer — kein Absturz, kein geratener Nenner."""
    assert vg.graph_konten(tmp_path / "gibt-es-nicht") == []
