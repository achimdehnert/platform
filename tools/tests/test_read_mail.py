"""Tests für tools/mail_agent/read_mail.py — Header-Decode, Body-/Anhang-Extraktion,
From-Filter, Pfad-Traversal-Schutz beim Anhang-Speichern. Kein Netz-/IMAP-Test
(connect/cmd_* bleiben Dogfood/Integration, analog test_send_mail.py).

Run: `python3 -m pytest tools/tests/test_read_mail.py -q`
"""

import datetime
import imaplib
import importlib.util
import json
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


class _FakePostfach:
    """Ein Postfach mit einem Ordner — genug für die Kalibriersonde.

    ``server_treffer`` ist die Antwort, die der Server auf ein SEARCH-Kriterium
    gibt. Sie darf bewusst von dem abweichen, was in den Headern steht — genau
    diese Abweichung soll die Sonde bemerken.
    """

    def __init__(self, ordner_zeile, kopfzeilen, server_treffer):
        self._list = [ordner_zeile]
        self._kopf = kopfzeilen  # {b"1": b"From: ..."}
        self._server = server_treffer

    def list(self):
        return "OK", self._list

    def select(self, mailbox, readonly=True):
        return "OK", [str(len(self._kopf)).encode()]

    def search(self, charset, *kriterien):
        if kriterien == ("ALL",):
            return "OK", [b" ".join(sorted(self._kopf))]
        return "OK", [b" ".join(sorted(self._server))]

    def fetch(self, num, teile):
        return "OK", [(b"", self._kopf[num])]


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


# --- Ausgabe: Bilanz zuerst, maschinenlesbar auf Wunsch -----------------------


def _ergebnis(**over):
    basis = dict(
        treffer=(
            rm.Treffer(
                "MEIKI/LK",
                "70",
                "Tue, 21 Jul 2026",
                "<p.offner@x.de>",
                "<a@b>",
                "AW: Postkorb",
            ),
        ),
        konto="hnu",
        filter={"von": "offner", "an": None, "betreff": None},
        limit=50,
        gesamt_ordner=119,
        geprueft_ordner=92,
        nachrichten_gesehen=0,
        nachrichten_vorhanden=0,
        vorgefiltert=True,
        ausgeschlossen=(("Junk-E-Mail", "Papierkorb/Junk — bewusst nicht indexiert"),),
    )
    basis.update(over)
    return rm.Ergebnis(**basis)


# Realfall 2026-07-28: bei 27 ausgeschlossenen Ordnern scrollte die Bilanz aus dem
# Terminal; `tail` zeigte den Beweis und verschluckte den einzigen Treffer.
def test_should_print_the_denominator_before_the_hits():
    text = rm.rendern_text(_ergebnis())
    assert text.index("92 von 119") < text.index("P.Offner".lower())


def test_should_render_json_with_denominator_and_limit_flag():
    daten = json.loads(rm.rendern_json(_ergebnis(limit=1)))
    assert daten["bilanz"]["ordner_gesamt"] == 119
    assert daten["bilanz"]["ordner_geprueft"] == 92
    assert daten["bilanz"]["limit_erreicht"] is True
    assert daten["bilanz"]["ausgeschlossen"][0]["ordner"] == "Junk-E-Mail"
    assert daten["treffer"][0]["ordner"] == "MEIKI/LK"
    assert daten["konto"] == "hnu"


def test_should_not_claim_limit_reached_below_the_limit():
    daten = json.loads(rm.rendern_json(_ergebnis(limit=50)))
    assert daten["bilanz"]["limit_erreicht"] is False


# --- Kalibriersonde -----------------------------------------------------------
# R-3 (KONZ-035): ein Retrievalpfad zählt erst als belegt, wenn er an einer Menge
# mit bekannter Antwort gezeigt hat, dass er findet, was da ist.


_SENT_ZEILE = rb'(\HasNoChildren \Sent) "/" "Gesendete Objekte"'


def test_should_find_sent_folder_by_flag_not_by_name():
    imap = _FakeImap(
        list_antwort=[
            rb'(\HasNoChildren) "/" "Sent"',  # heisst so, ist es aber nicht
            _SENT_ZEILE,
        ]
    )
    assert rm.gesendet_ordner(imap) == "Gesendete Objekte"


def test_should_report_no_sent_folder_instead_of_guessing():
    assert (
        rm.gesendet_ordner(_FakeImap(list_antwort=[rb'(\HasNoChildren) "/" "INBOX"']))
        == ""
    )


def test_should_pass_calibration_when_prefilter_covers_the_known_messages():
    postfach = _FakePostfach(
        _SENT_ZEILE,
        {b"1": b"From: Achim <a@iil.gmbh>\r\n", b"2": b"From: Achim <a@iil.gmbh>\r\n"},
        server_treffer={b"1", b"2"},
    )
    ok, wie = rm.kalibrierungssonde(postfach, "a@iil.gmbh")
    assert ok, wie


# Der eigentliche Zweck der Sonde: ein Vorfilter, der etwas VERSCHWEIGT, ist die
# teure Fehlerklasse — er sieht aus wie eine leere Menge.
def test_should_fail_calibration_when_prefilter_hides_a_known_message():
    postfach = _FakePostfach(
        _SENT_ZEILE,
        {b"1": b"From: Achim <a@iil.gmbh>\r\n", b"2": b"From: Achim <a@iil.gmbh>\r\n"},
        server_treffer={b"1"},  # #2 verschwiegen
    )
    ok, wie = rm.kalibrierungssonde(postfach, "a@iil.gmbh")
    assert not ok
    assert "verschweigt 1 von 2" in wie


def test_should_fail_calibration_without_a_sent_folder():
    postfach = _FakePostfach(rb'(\HasNoChildren) "/" "INBOX"', {}, set())
    ok, wie = rm.kalibrierungssonde(postfach, "a@iil.gmbh")
    assert not ok
    assert "Sent" in wie


# --- Konten-Erkennung ---------------------------------------------------------


def test_should_ignore_env_files_that_are_not_accounts(tmp_path, monkeypatch):
    # mail-folders.env liegt neben den Konten, ist aber eine Ordner-Zuordnung.
    (tmp_path / "mail.env").write_text(
        "SMTP_HOST=h\nMAIL_FROM=a@b.c\nMAIL_CREDS_FILE=/dev/null\n"
    )
    (tmp_path / "mail-hnu.env").write_text(
        "SMTP_HOST=h\nMAIL_FROM=d@e.f\nMAIL_CREDS_FILE=/dev/null\n"
    )
    (tmp_path / "mail-folders.env").write_text(
        "# nur Zuordnung\nIIL.Kunden/X | kunde\n"
    )
    monkeypatch.setattr(rm, "CONFIG_FILE", tmp_path / "mail.env")

    assert [k for k, _ in rm.imap_konten()] == ["default", "hnu"]


# --- Bulk-Abruf ---------------------------------------------------------------
# Gemessen 2026-07-29: 10,1/s einzeln gegen 106,3/s gebündelt (Faktor 10,6);
# end-to-end auf einem 354er-Ordner 34,9 s -> 3,9 s bei identischem Ergebnis.


class _FetchImap:
    """Liefert eine Bulk-FETCH-Antwort im imaplib-Format."""

    def __init__(self, saetze):
        # saetze: {nummer: b"From: ...\r\n"}
        self._s = saetze

    def fetch(self, bereich, teile):
        out = []
        for nr, roh in sorted(self._s.items()):
            out.append(
                (f"{nr} (BODY[HEADER.FIELDS (...)] {{{len(roh)}}}".encode(), roh)
            )
            out.append(b")")
        return "OK", out


def test_should_fetch_many_headers_in_one_command():
    imap = _FetchImap(
        {1: b"From: a@b.c\r\nSubject: eins\r\n", 2: b"From: d@e.f\r\nSubject: zwei\r\n"}
    )
    raus = rm.bulk_kopfsaetze(imap, [b"1", b"2"])
    assert [nr for nr, _ in raus] == ["1", "2"]
    assert raus[1][1].get("Subject") == "zwei"


# Der Server liefert den ganzen Bereich, auch Nummern die niemand wollte —
# ohne Nachfilter zählte der Aufrufer fremde Nachrichten mit.
def test_should_drop_messages_outside_the_requested_set():
    imap = _FetchImap(
        {1: b"Subject: ja\r\n", 2: b"Subject: nein\r\n", 3: b"Subject: ja\r\n"}
    )
    raus = rm.bulk_kopfsaetze(imap, [b"1", b"3"])
    assert [nr for nr, _ in raus] == ["1", "3"]


def test_should_return_nothing_for_empty_id_list():
    assert rm.bulk_kopfsaetze(_FetchImap({}), []) == []


# --- Gesendet zuerst ----------------------------------------------------------


def test_should_sort_the_sent_folder_first():
    o = ["Archiv/2025", "INBOX", "Gesendete Objekte", "Projekte"]
    assert rm.sortiere_gesendet_zuerst(o, "Gesendete Objekte")[0] == "Gesendete Objekte"


def test_should_recognise_sent_folders_by_name_without_the_flag():
    assert rm.sortiere_gesendet_zuerst(["INBOX", "INBOX.Sent"])[0] == "INBOX.Sent"


# --- Betreff-Normalisierung ---------------------------------------------------
# Ohne sie zerfaellt ein Vorgang in so viele Straenge wie er Richtungswechsel hatte.


def test_should_strip_nested_reply_and_forward_prefixes():
    assert rm.betreff_normalisiert("AW: WG: AW: Termin") == "termin"
    assert rm.betreff_normalisiert("RE[2]: Postkorb") == "postkorb"
    assert rm.betreff_normalisiert("Termin") == "termin"


def test_should_collect_addresses_without_duplicates():
    assert rm.adressen("A <a@b.de>", "a@b.de, d@e.com") == ["a@b.de", "d@e.com"]


# Einbuchstabige Endungen gibt es nicht — die Regex verlangt zu Recht >= 2.
def test_should_ignore_things_that_only_look_like_addresses():
    assert rm.adressen("a@b.c", "kein text") == []


# --- Dossier ------------------------------------------------------------------


def _t(datum, betreff, ausgehend, ordner="X"):
    return rm.Treffer(
        ordner=ordner,
        nummer="1",
        datum=datum,
        von="ich@x.de" if ausgehend else "p@y.de",
        an="p@y.de" if ausgehend else "ich@x.de",
        betreff=betreff,
        ausgehend=ausgehend,
    )


def _erg(treffer, **over):
    basis = dict(
        treffer=tuple(treffer),
        konto="k",
        filter={"an": "p", "von": None, "betreff": None},
        limit=500,
        gesamt_ordner=10,
        geprueft_ordner=10,
        nachrichten_gesehen=0,
        nachrichten_vorhanden=0,
        vorgefiltert=True,
    )
    basis.update(over)
    return rm.Ergebnis(**basis)


_JETZT = datetime.datetime(2026, 7, 29, tzinfo=datetime.timezone.utc)


# Der Referenzfall: am 23.06. drei Fragen gesendet, nie beantwortet.
def test_should_report_an_outgoing_thread_without_reply_as_open():
    d = rm.baue_dossier(
        _erg([_t("Tue, 23 Jun 2026 09:13:20 +0200", "DMS Fragen", True)]), _JETZT
    )
    assert len(d.offene) == 1
    assert d.offene[0].tage_still == 35  # 23.06. 07:13 UTC bis 29.07. 00:00 UTC


def test_should_not_report_a_thread_whose_last_message_is_incoming():
    d = rm.baue_dossier(
        _erg(
            [
                _t("Tue, 23 Jun 2026 09:13:20 +0200", "Frage", True),
                _t("Wed, 24 Jun 2026 09:00:00 +0200", "AW: Frage", False),
            ]
        ),
        _JETZT,
    )
    assert d.offene == ()
    assert len(d.straenge) == 1  # AW: gehoert zum selben Strang


def test_should_respect_the_silence_threshold():
    t = [_t("Mon, 27 Jul 2026 09:00:00 +0200", "Neulich", True)]
    assert rm.baue_dossier(_erg(t), _JETZT, still_ab_tagen=7).offene == ()
    assert len(rm.baue_dossier(_erg(t), _JETZT, still_ab_tagen=1).offene) == 1


def test_should_count_participants_across_all_hits():
    d = rm.baue_dossier(
        _erg(
            [
                _t("Tue, 23 Jun 2026 09:13:20 +0200", "A", True),
                _t("Wed, 24 Jun 2026 09:00:00 +0200", "B", False),
            ]
        ),
        _JETZT,
    )
    assert dict(d.beteiligte)["p@y.de"] == 2


def test_should_put_coverage_before_the_timeline():
    text = rm.rendern_dossier(
        rm.baue_dossier(
            _erg([_t("Tue, 23 Jun 2026 09:13:20 +0200", "DMS Fragen", True)]), _JETZT
        )
    )
    assert text.index("Deckung") < text.index("Zeitachse")


# Eine Abwesenheitsaussage auf lueckenhafter Deckung ist die teuerste Fehlerklasse.
def test_should_warn_when_coverage_is_incomplete():
    erg = _erg(
        [_t("Tue, 23 Jun 2026 09:13:20 +0200", "X", True)],
        fehler=(("Kalender", "SELECT NO"),),
    )
    text = rm.rendern_dossier(rm.baue_dossier(erg, _JETZT))
    assert "NICHT belegt" in text


# --- Parteien-Aufloesung (P3) -------------------------------------------------
# Eine Adresse ist keine Person. Aufgeloest wird VOR der Suche, und das Ergebnis
# wird angezeigt — Uebermatch ist dann sichtbar statt still.


def _tp(von, an, betreff="X", datum="Tue, 23 Jun 2026 09:13:20 +0200"):
    return rm.Treffer(
        ordner="O", nummer="1", datum=datum, von=von, an=an, betreff=betreff
    )


# Der Realfall vom 2026-07-29: die Kopfzeile als Ganzes zu strippen gab allen
# Sammelempfaengern denselben "Namen" — die Suche lieferte den halben Verteiler.
def test_should_read_display_names_per_address_not_per_header():
    # So schreibt Exchange es real: Nachname-Komma-Vorname in Anfuehrungszeichen.
    paare = rm._paare(
        '"Kramer, Daniel" <d.kramer@x.de>, "Offner, Petra" <p.offner@x.de>'
    )
    assert dict((a, n) for n, a in paare) == {
        "d.kramer@x.de": "kramer, daniel",
        "p.offner@x.de": "offner, petra",
    }


# Bekannte Grenze: OHNE Anfuehrungszeichen ist 'Nachname, Vorname <adr>' nach RFC
# mehrdeutig und wird am Komma zerlegt. Der Anzeigename wird dadurch kuerzer, die
# ADRESSEN bleiben korrekt — und nur die tragen das Ergebnis.
def test_should_still_get_the_addresses_right_when_the_name_is_unquoted():
    paare = rm._paare("Kramer, Daniel <d.kramer@x.de>, Offner, Petra <p.offner@x.de>")
    assert {a for _, a in paare} == {"d.kramer@x.de", "p.offner@x.de"}


def test_should_reject_display_names_that_cannot_bridge():
    assert not rm._tragfaehiger_name("")
    assert not rm._tragfaehiger_name(",")
    assert not rm._tragfaehiger_name("a@b.de")
    assert rm._tragfaehiger_name("offner, petra")


def test_should_find_the_addresses_of_one_person():
    t = [_tp("Petra Offner <p.offner@x.de>", "ich@y.de")]
    p = rm.parteien_aufloesen(t, "offner")
    assert p.adressen == ("p.offner@x.de",)
    assert p.nachrichten == 1


# Dieselbe Person unter zwei Adressen gehoert zusammengefuehrt.
def test_should_merge_two_addresses_sharing_a_display_name():
    t = [
        _tp("Petra Offner <p.offner@lra.de>", "ich@y.de"),
        _tp("Petra Offner <petra.offner@privat.de>", "ich@y.de"),
    ]
    p = rm.parteien_aufloesen(t, "offner")
    assert set(p.adressen) == {"p.offner@lra.de", "petra.offner@privat.de"}


# Ein Name an einem Dutzend Adressen ist ein Verteiler, keine Person —
# falsche Zusammenfuehrungen sind teurer als verpasste.
def test_should_not_merge_over_a_distribution_list_name():
    t = [
        _tp("Projektteam <p.offner@lra.de>", "ich@y.de"),
        _tp("Projektteam <d.kramer@lra.de>", "ich@y.de"),
        _tp("Projektteam <w.seitz@lra.de>", "ich@y.de"),
    ]
    p = rm.parteien_aufloesen(t, "offner")
    assert p.adressen == ("p.offner@lra.de",)


def test_should_return_nothing_when_the_name_is_unknown():
    assert rm.parteien_aufloesen([_tp("A <a@b.de>", "c@d.de")], "niemand") is None


def test_should_expose_the_party_in_the_dossier():
    erg = _erg([_t("Tue, 23 Jun 2026 09:13:20 +0200", "Frage", True)])
    d = rm.baue_dossier(erg, _JETZT, partei_name="p@y.de")
    assert d.partei is not None
    assert "p@y.de" in d.partei.adressen
    assert "Partei" in rm.rendern_dossier(d)


# --- Evidenz je Zeile ---------------------------------------------------------
# Ohne Evidenzverweis ist eine Dossier-Zeile eine Behauptung: nicht nachschlagbar,
# nicht widerlegbar.


def test_should_point_each_open_thread_at_its_evidence():
    d = rm.baue_dossier(
        _erg(
            [_t("Tue, 23 Jun 2026 09:13:20 +0200", "DMS Fragen", True, ordner="Sent")]
        ),
        _JETZT,
    )
    assert d.offene[0].evidenz == "Sent #1"


def test_should_label_derived_statements_as_derived():
    text = rm.rendern_dossier(
        rm.baue_dossier(
            _erg([_t("Tue, 23 Jun 2026 09:13:20 +0200", "X", True)]), _JETZT
        )
    )
    assert "abgeleitet" in text
    assert "Evidenz:" in text
