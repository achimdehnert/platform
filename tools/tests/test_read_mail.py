"""Tests für tools/mail_agent/read_mail.py — Header-Decode, Body-/Anhang-Extraktion,
From-Filter, Pfad-Traversal-Schutz beim Anhang-Speichern. Kein Netz-/IMAP-Test
(connect/cmd_* bleiben Dogfood/Integration, analog test_send_mail.py).

Run: `python3 -m pytest tools/tests/test_read_mail.py -q`
"""

import imaplib
import importlib.util
import pathlib
from email.message import EmailMessage

_SRC = pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "read_mail.py"
_spec = importlib.util.spec_from_file_location("read_mail", _SRC)
rm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rm)


def _msg(subject="s", frm="a@b.c", body="hallo", attachments=()):
    m = EmailMessage()
    m["From"] = frm
    m["Subject"] = subject
    m.set_content(body)
    for name, data in attachments:
        m.add_attachment(
            data, maintype="application", subtype="octet-stream", filename=name
        )
    return m


class _FakeImap:
    """Nur die drei Aufrufe, die alle_ordner/_kandidaten wirklich machen — kein Netz."""

    def __init__(self, list_antwort=(), alle_ids=b"", search_fehler=False):
        self._list = list(list_antwort)
        self._alle = alle_ids
        self._fehler = search_fehler

    def list(self):
        return "OK", self._list

    def search(self, charset, *kriterien):
        if kriterien == ("ALL",):
            return "OK", [self._alle]
        if self._fehler:
            raise imaplib.IMAP4.error("SEARCH nicht unterstützt")
        return "OK", [self._alle]


# --- decode_hdr --------------------------------------------------------------


def test_should_decode_mime_encoded_header():
    enc = "=?iso-8859-1?Q?Pr=FCfergebnis?="
    assert rm.decode_hdr(enc) == "Prüfergebnis"


def test_should_flatten_newlines_and_none():
    assert rm.decode_hdr("a\n b\r") == "a  b"
    assert rm.decode_hdr(None) == ""


# Regression #1342: brach den Massen-Header-Scan von ~24k HNU-Mails ab.
# Ohne den latin-1-Fallback wirft codecs.lookup("unknown-8bit") LookupError.
def test_should_decode_header_with_charset_python_does_not_know():
    assert rm.decode_hdr("=?unknown-8bit?Q?Gr=FC=DFe?=") == "Grüße"
    assert rm.decode_hdr("=?x-unknown?B?SGFsbG8=?=") == "Hallo"


# --- extract_text ------------------------------------------------------------


def test_should_extract_plain_body():
    assert "hallo" in rm.extract_text(_msg())


def test_should_truncate_long_body():
    out = rm.extract_text(_msg(body="x" * 5000), max_chars=100)
    assert out.startswith("x" * 100)
    assert "gekürzt" in out


def test_should_report_missing_plain_part():
    m = EmailMessage()
    m.add_alternative("<p>nur html</p>", subtype="html")
    assert rm.extract_text(m) == "(kein text/plain-Teil)"


# --- attachments -------------------------------------------------------------


def test_should_list_attachment_names():
    m = _msg(attachments=[("a.md", b"1"), ("b.zip", b"22")])
    assert rm.attachment_names(m) == ["a.md", "b.zip"]


def test_should_save_attachments_and_strip_path_traversal(tmp_path):
    m = _msg(attachments=[("../../evil.txt", b"x"), ("ok.bin", b"12345")])
    saved = rm.save_attachments(m, tmp_path)
    assert ("evil.txt", 1) in saved and ("ok.bin", 5) in saved
    assert (tmp_path / "evil.txt").exists()
    assert not (tmp_path.parent / "evil.txt").exists()


# --- matches_from ------------------------------------------------------------


def test_should_match_from_substring_case_insensitive():
    m = _msg(frm="Ilja Lerch <Ilja.Lerch@example.com>")
    assert rm.matches_from(m, "ilja")
    assert not rm.matches_from(m, "achim")
    assert rm.matches_from(m, None)


# --- matches_to --------------------------------------------------------------


def test_should_match_to_and_cc_substring_case_insensitive():
    m = EmailMessage()
    m["From"] = "achim@iil.gmbh"  # Gesendete: Absender ist man selbst
    m["To"] = "Anna Martinkat <A.Martinkat@landkreis-guenzburg.de>"
    m["Cc"] = "Wibke Michalk <wibke.michalk@th-rosenheim.de>"
    m.set_content("x")
    assert rm.matches_to(m, "martinkat")  # Treffer im To-Header
    assert rm.matches_to(m, "michalk")  # Treffer im Cc-Header
    assert not rm.matches_to(m, "brandl")
    assert rm.matches_to(m, None)  # kein Filter -> True


def test_should_handle_missing_to_and_cc_headers():
    m = EmailMessage()
    m["From"] = "achim@iil.gmbh"
    m.set_content("x")
    assert rm.matches_to(m, None)
    assert not rm.matches_to(m, "irgendwer")


# --- Nenner sichtbar machen ---------------------------------------------------
# Eine Liste ohne Gesamtzahl ist von einer Vollerhebung nicht zu unterscheiden.
# Realfall 2026-07-27: `--list N` wurde als Bestand gelesen; erst ein zweiter
# Aufruf mit hohem N plus `grep -c` lieferte die echte Zahl. Die Graph-Variante
# desselben Musters ist platform#1480.


def test_should_report_total_and_examined_count():
    zeile = rm._bilanz(
        "INBOX",
        gesamt=120,
        geprueft=25,
        gezeigt=25,
        limit=25,
        from_filter=None,
        to_filter=None,
    )
    assert "25 gezeigt" in zeile
    assert "25 von 120" in zeile
    assert "INBOX" in zeile


def test_should_warn_loudly_when_the_limit_truncated_the_listing():
    zeile = rm._bilanz(
        "INBOX",
        gesamt=120,
        geprueft=25,
        gezeigt=25,
        limit=25,
        from_filter=None,
        to_filter=None,
    )
    assert "KEINE Vollerhebung" in zeile
    assert "95 Nachricht(en) wurden gar nicht erst angesehen" in zeile


def test_should_not_warn_when_the_whole_folder_was_examined():
    zeile = rm._bilanz(
        "INBOX",
        gesamt=12,
        geprueft=12,
        gezeigt=12,
        limit=500,
        from_filter=None,
        to_filter=None,
    )
    assert "KEINE Vollerhebung" not in zeile
    assert "12 von 12" in zeile


def test_should_name_the_active_filters_in_the_summary():
    zeile = rm._bilanz(
        "Sent",
        gesamt=30,
        geprueft=30,
        gezeigt=4,
        limit=500,
        from_filter="scheppach",
        to_filter="brandl",
    )
    assert "Absender~'scheppach'" in zeile
    assert "Empfänger~'brandl'" in zeile
    assert "UND" in zeile


def test_should_state_how_many_were_filtered_out():
    zeile = rm._bilanz(
        "Sent",
        gesamt=30,
        geprueft=30,
        gezeigt=4,
        limit=500,
        from_filter="scheppach",
        to_filter=None,
    )
    assert "26 Nachricht(en) passten nicht auf den Filter" in zeile


def test_should_say_no_filter_when_none_is_set():
    zeile = rm._bilanz(
        "INBOX",
        gesamt=5,
        geprueft=5,
        gezeigt=5,
        limit=500,
        from_filter=None,
        to_filter=None,
    )
    assert "kein Filter" in zeile


def test_should_name_the_subject_filter_in_the_summary():
    zeile = rm._bilanz(
        "INBOX",
        gesamt=5,
        geprueft=5,
        gezeigt=1,
        limit=500,
        from_filter=None,
        to_filter=None,
        subject_filter="Postkorb",
    )
    assert "Betreff~'Postkorb'" in zeile


# --- matches_subject ----------------------------------------------------------


def test_should_match_subject_substring_case_insensitive():
    m = _msg(subject="AW: Termin OCOS Meiki - Postkorb")
    assert rm.matches_subject(m, "postkorb")
    assert rm.matches_subject(m, None)
    assert not rm.matches_subject(m, "Rechnung")


# --- LIST-Parsing -------------------------------------------------------------
# Realfall 2026-07-28: naives Splitten am Trenner erzeugte Phantom-Ordner
# ('/" Notizen'), deren SELECT die IMAP-Verbindung riss — der Lauf meldete
# danach "0 Treffer" für ein Postfach, in dem die gesuchte Mail lag.


def test_should_parse_quoted_and_unquoted_folder_names():
    ordner, unlesbar = rm.alle_ordner(
        _FakeImap(
            list_antwort=[
                rb'(\HasNoChildren) "/" "Gesendete Objekte"',
                rb'(\HasNoChildren) "/" INBOX',
                rb'(\HasChildren) "/" "Sent-Archiv/2025"',
            ]
        )
    )
    assert ordner == ["Gesendete Objekte", "INBOX", "Sent-Archiv/2025"]
    assert unlesbar == []


def test_should_skip_noselect_containers():
    ordner, _ = rm.alle_ordner(
        _FakeImap(
            list_antwort=[
                rb'(\Noselect \HasChildren) "/" "Betreuungen"',
                rb'(\HasNoChildren) "/" "Betreuungen/Anfragen"',
            ]
        )
    )
    assert ordner == ["Betreuungen/Anfragen"]


def test_should_surface_unparsable_list_lines_instead_of_dropping_them():
    ordner, unlesbar = rm.alle_ordner(_FakeImap(list_antwort=[b"kaputte zeile"]))
    assert ordner == []
    assert unlesbar == ["kaputte zeile"]


# --- Server-Vorfilter ---------------------------------------------------------
# Kalibriert am 2026-07-28 gegen den vollen Header-Scan: bei ASCII deckungsgleich.
# Nicht-ASCII geht nicht über die Leitung -> None -> voller Scan statt "0 Treffer".


def test_should_build_and_criteria_for_from_and_subject():
    assert rm._such_kriterien("offner", None, "Postkorb") == [
        "FROM",
        '"offner"',
        "SUBJECT",
        '"Postkorb"',
    ]


def test_should_search_to_or_cc_because_matches_to_checks_both():
    # Ein reines TO verschwiege Cc-Empfänger — falsch-negativ, die teuerste Fehlerklasse hier.
    assert rm._such_kriterien(None, "offner", None) == [
        "OR",
        "TO",
        '"offner"',
        "CC",
        '"offner"',
    ]


def test_should_refuse_server_prefilter_for_non_ascii_needle():
    assert rm._such_kriterien("Grüninger", None, None) is None


def test_should_return_none_without_any_filter():
    assert rm._such_kriterien(None, None, None) is None


def test_should_fall_back_to_full_scan_when_server_rejects_the_search():
    imap = _FakeImap(search_fehler=True, alle_ids=b"1 2 3")
    ids, vorgefiltert = rm._kandidaten(imap, ["FROM", '"x"'])
    assert [i.decode() for i in ids] == ["1", "2", "3"]
    assert vorgefiltert is False


# --- Bilanz des Ordner-Laufs --------------------------------------------------


def test_should_report_full_folder_denominator_not_the_reduced_one():
    zeile = rm._bilanz_alle(
        gesamt_ordner=119,
        geprueft=92,
        gezeigt=1,
        limit=50,
        nachrichten=0,
        vorgefiltert=True,
        ausgeschlossen=[("Junk-E-Mail", "Papierkorb/Junk — bewusst nicht indexiert")],
        fehler=[],
        unlesbar=[],
    )
    assert "92 von 119 Ordner(n)" in zeile
    assert "1 Ordner bewusst ausgeschlossen" in zeile
    assert "Junk-E-Mail" in zeile


def test_should_flag_unreadable_folders_as_incomplete_result():
    zeile = rm._bilanz_alle(
        gesamt_ordner=10,
        geprueft=9,
        gezeigt=0,
        limit=50,
        nachrichten=0,
        vorgefiltert=False,
        ausgeschlossen=[],
        fehler=[("Kalender", "SELECT NO")],
        unlesbar=[],
    )
    assert "keine Treffer" in zeile
    assert "Ergebnis ist unvollständig" in zeile
    assert "Kalender" in zeile


def test_should_warn_when_the_hit_limit_cut_the_folder_walk_short():
    zeile = rm._bilanz_alle(
        gesamt_ordner=119,
        geprueft=12,
        gezeigt=50,
        limit=50,
        nachrichten=0,
        vorgefiltert=True,
        ausgeschlossen=[],
        fehler=[],
        unlesbar=[],
    )
    assert "KEINE Vollerhebung" in zeile
    assert "107 Ordner wurden gar nicht erst angesehen" in zeile
