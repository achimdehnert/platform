"""Tests für tools/mail_agent/organize_mail.py — netzfreie Logik:
Header-Decode, Ordner-Namen-Parsing, Papierkorb-Auflösung, Matching-Filter
UND der Move-Pfad (_matches/_move) über Mock-IMAP (Seq-Nr-vs-UID-Regress).
Nur connect/cmd_* bleiben Dogfood/Integration (echte Verbindung).
"""

import imaplib
import importlib.util
import pathlib

_SRC = pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "organize_mail.py"
_spec = importlib.util.spec_from_file_location("organize_mail", _SRC)
om = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(om)


class _FakeImap:
    def __init__(self, list_data):
        self._list = list_data

    def list(self):
        return "OK", self._list


# --- Ordner-Parsing ----------------------------------------------------------


def test_should_parse_folder_names_quoted_and_unquoted():
    imap = _FakeImap(
        [
            b'(\\HasNoChildren) "." "INBOX.Sent"',
            b'(\\HasNoChildren \\Trash) "." INBOX.Trash',
        ]
    )
    assert om.list_folders(imap) == ["INBOX.Sent", "INBOX.Trash"]


def test_should_return_empty_on_list_failure():
    class _Fail:
        def list(self):
            return "NO", []

    assert om.list_folders(_Fail()) == []


# --- Papierkorb-Auflösung ----------------------------------------------------


def test_should_resolve_trash_by_known_candidate():
    imap = _FakeImap(
        [b'(\\HasNoChildren) "." "INBOX.Trash"', b'(\\HasNoChildren) "." "INBOX.Sent"']
    )
    assert om.resolve_trash(imap) == "INBOX.Trash"


def test_should_resolve_trash_by_name_heuristic():
    imap = _FakeImap([b'(\\HasNoChildren) "." "INBOX.Papierkorb"'])
    assert om.resolve_trash(imap) == "INBOX.Papierkorb"


def test_should_return_none_when_no_trash():
    imap = _FakeImap(
        [b'(\\HasNoChildren) "." "INBOX"', b'(\\HasNoChildren) "." "INBOX.Sent"']
    )
    assert om.resolve_trash(imap) is None


# --- Header-Decode -----------------------------------------------------------


def test_should_decode_mime_and_flatten():
    assert om._decode("=?iso-8859-1?Q?Antonela?=") == "Antonela"
    assert om._decode("a\nb\r") == "a b"  # Zeilenumbruch → Leerzeichen (Header-Faltung)
    assert om._decode(None) == ""


# Regression #1342: brach den Massen-Header-Scan von ~24k HNU-Mails ab.
# Ohne den latin-1-Fallback wirft codecs.lookup("unknown-8bit") LookupError.
def test_should_decode_header_with_charset_python_does_not_know():
    assert om._decode("=?unknown-8bit?Q?Gr=FC=DFe?=") == "Grüße"
    assert om._decode("=?x-unknown?B?SGFsbG8=?=") == "Hallo"


# --- Move-Pfad (Regression: Seq-Nr-vs-UID-Bug, Retro 2026-07-22 Befund #1) ----
# Guard gegen `untested-tool-module-green-gate` (retro_kpis ×2): _matches MUSS
# echte UIDs aus der UID-FETCH-Antwort ziehen, nicht Sequenz-Nummern — sonst traf
# UID MOVE auf Exchange ins Leere und meldete trotzdem "OK: N verschoben".


class _FakeUidImap:
    """Antwortet NUR auf UID-basierte Aufrufe (uid SEARCH/FETCH/MOVE) — ein
    Aufruf von .search()/.fetch() (Sequenz-Nr, der alte Bug) würde hier mit
    AttributeError scheitern und den Regress sofort sichtbar machen."""

    def __init__(self, search_uids, fetch_resp, caps=("MOVE",)):
        self._search, self._fetch, self.capabilities = search_uids, fetch_resp, caps
        self.moved = None
        self.selected = None

    def select(self, folder, readonly=False):
        self.selected = folder
        return "OK", [b"2"]

    def uid(self, cmd, *args):
        if cmd == "SEARCH":
            return "OK", [self._search]
        if cmd == "FETCH":
            return "OK", self._fetch
        if cmd == "MOVE":
            self.moved = (args[0], args[1])
            return "OK", [b"[COPYUID ...]"]
        return "OK", [b""]


def _fetch_exchange(uid, frm, subj):
    # Exchange legt die UID in den Separator NACH dem Tupel.
    hdr = f"From: {frm}\r\nSubject: {subj}\r\nDate: Wed, 22 Jul 2026 09:00:00 +0000\r\n"
    return [
        (b"1 (BODY[HEADER.FIELDS (FROM SUBJECT DATE)] {%d}" % len(hdr), hdr.encode()),
        b" UID %d)" % uid,
    ]


def test_should_return_real_uids_not_seqnums_exchange_style():
    fetch = _fetch_exchange(1001, "alice@x.de", "Hallo") + _fetch_exchange(
        1002, "bob@y.de", "Tschuess"
    )
    imap = _FakeUidImap(b"1001 1002", fetch)
    hits = om._matches(imap, "INBOX", None, None)
    assert [h[0] for h in hits] == [b"1001", b"1002"]  # ECHTE UIDs, nicht Seq 1/2


def test_should_read_uid_from_part0_dovecot_style():
    hdr = b"From: c@z.de\r\nSubject: x\r\nDate: x\r\n"
    fetch = [
        (b"1 (UID 5005 BODY[HEADER.FIELDS (FROM SUBJECT DATE)] {%d}" % len(hdr), hdr)
    ]
    imap = _FakeUidImap(b"5005", fetch)
    assert [h[0] for h in om._matches(imap, "INBOX", None, None)] == [b"5005"]


def test_should_filter_matches_by_from_substring():
    fetch = _fetch_exchange(1001, "alice@x.de", "Hallo") + _fetch_exchange(
        1002, "bob@y.de", "Tschuess"
    )
    hits = om._matches(_FakeUidImap(b"1001 1002", fetch), "INBOX", "alice", None)
    assert [h[0] for h in hits] == [b"1001"]


def test_should_move_via_uid_move_with_those_uids():
    imap = _FakeUidImap(b"", [])
    om._move(imap, "INBOX", "Ziel/2020", [b"1001", b"1002"])
    assert imap.moved == (b"1001,1002", "Ziel/2020")


# --- Ordner-Namen mit Leerzeichen quoten (Regression 2026-07-24) -------------
# Realfall: `--move --source "Entw&APw-rfe" --to "Gel&APY-schte Objekte"` schlug mit
# `BAD [Command Argument Error. 12]` fehl. Ursache: organize_mail reichte Ordner-
# namen ROH an select()/UID MOVE durch — read_mail hatte den Quoting-Helper längst,
# organize_mail nicht. Umlaute bleiben Sache des Aufrufers (IMAP modified UTF-7);
# hier geht es ausschliesslich um das Quoting von Leerzeichen.


def test_should_quote_folder_name_with_spaces():
    assert om._mailbox_arg("Gel&APY-schte Objekte") == '"Gel&APY-schte Objekte"'


def test_should_leave_folder_name_without_spaces_unquoted():
    assert om._mailbox_arg("INBOX.Trash") == "INBOX.Trash"


def test_should_not_double_quote_already_quoted_folder():
    assert om._mailbox_arg('"Deleted Items"') == '"Deleted Items"'


def test_should_quote_move_target_with_spaces():
    imap = _FakeUidImap(b"", [])
    om._move(imap, "Entw&APw-rfe", "Gel&APY-schte Objekte", [b"1001"])
    assert imap.moved == (b"1001", '"Gel&APY-schte Objekte"')


def test_should_quote_source_folder_on_select():
    imap = _FakeUidImap(b"", [])
    om._move(imap, "Gesendete Objekte", "INBOX.Trash", [b"1001"])
    assert imap.selected == '"Gesendete Objekte"'


# --- Papierkorb-Erkennung: deutsches Exchange/M365 ---------------------------
# Realfall: HNU-Postfach meldet den Papierkorb als "Gel&APY-schte Objekte"
# (= "Gelöschte Objekte"). Weder "trash" noch "papierkorb" kommt darin vor →
# `--to-trash` brach mit "kein Papierkorb-Ordner gefunden" ab.


def test_should_resolve_german_exchange_trash_utf7():
    imap = _FakeImap([b'(\\HasNoChildren) "." "Gel&APY-schte Objekte"'])
    assert om.resolve_trash(imap) == "Gel&APY-schte Objekte"


def test_should_resolve_german_exchange_trash_plaintext():
    imap = _FakeImap(['(\\HasNoChildren) "." "Gelöschte Objekte"'.encode()])
    assert om.resolve_trash(imap) == "Gelöschte Objekte"


# --- _set_flagged / cmd_flag: \Flagged setzen & entfernen --------------------


class _FlagImap:
    """Fake, der select + uid(STORE|SEARCH|FETCH) bedient und STORE mitschneidet."""

    def __init__(self, search_uids=b"", fetch_resp=None):
        self._search, self._fetch = search_uids, fetch_resp or []
        self.stored = None
        self.selected_readonly = None

    def select(self, folder, readonly=False):
        self.selected_readonly = readonly
        return "OK", [b"1"]

    def uid(self, cmd, *args):
        if cmd == "SEARCH":
            return "OK", [self._search]
        if cmd == "FETCH":
            return "OK", self._fetch
        if cmd == "STORE":
            self.stored = args  # (uid_set, op, flags)
            return "OK", [b"1 (UID 1 FLAGS (\\Flagged))"]
        return "OK", [b""]


def test_should_store_add_flagged_flag():
    imap = _FlagImap()
    om._set_flagged(imap, "INBOX", [b"1001", b"1002"], add=True)
    assert imap.stored == (b"1001,1002", "+FLAGS", r"(\Flagged)")
    assert imap.selected_readonly is False  # write-select vor STORE


def test_should_store_remove_flagged_flag():
    imap = _FlagImap()
    om._set_flagged(imap, "INBOX", [b"1001"], add=False)
    assert imap.stored == (b"1001", "-FLAGS", r"(\Flagged)")


def test_should_flag_matched_messages_via_cmd_flag():
    fetch = _fetch_exchange(1001, "alice@x.de", "Frist") + _fetch_exchange(
        1002, "bob@y.de", "Egal"
    )
    imap = _FlagImap(b"1001 1002", fetch)
    om.cmd_flag(imap, "INBOX", "alice", None, yes=True, add=True)
    # nur die alice-Mail wird geflaggt, nicht bob
    assert imap.stored == (b"1001", "+FLAGS", r"(\Flagged)")


def test_should_not_store_when_no_matches():
    imap = _FlagImap(b"1001", _fetch_exchange(1001, "alice@x.de", "Frist"))
    om.cmd_flag(imap, "INBOX", "niemand", None, yes=True, add=True)
    assert imap.stored is None


# --- Genau eine Nachricht verschieben (--uid) --------------------------------
#
# Bis 2026-08-18 konnte `--move` nur nach Absender oder Betreff filtern. Wer eine
# einzelne Mail bewegen wollte, musste einen Betreff-Filter nehmen — der trifft
# auch fremde Mails mit demselben Wort.


def test_should_restrict_matches_to_the_named_uids():
    fetch = _fetch_exchange(1001, "alice@x.de", "Hallo") + _fetch_exchange(
        1002, "bob@y.de", "Tschuess"
    )
    imap = _FakeUidImap(b"1001 1002", fetch)
    hits = om._matches(imap, "INBOX", None, None, nur_uids=["1002"])
    assert [h[0] for h in hits] == [b"1002"]


def test_should_combine_uid_and_sender_filter_as_and():
    """Beide gesetzt heißt beides muss passen — nicht eines von beiden."""
    fetch = _fetch_exchange(1001, "alice@x.de", "Hallo") + _fetch_exchange(
        1002, "bob@y.de", "Tschuess"
    )
    imap = _FakeUidImap(b"1001 1002", fetch)
    assert om._matches(imap, "INBOX", "alice", None, nur_uids=["1002"]) == []


def test_should_return_nothing_for_a_uid_that_is_not_in_the_folder():
    fetch = _fetch_exchange(1001, "alice@x.de", "Hallo")
    imap = _FakeUidImap(b"1001", fetch)
    assert om._matches(imap, "INBOX", None, None, nur_uids=["9999"]) == []


class _FakeUidImapMitOrdnern(_FakeUidImap):
    """Wie `_FakeUidImap`, kennt zusätzlich `list()`.

    `cmd_move` prüft über `list_folders()`, ob der Zielordner existiert. Der
    Basis-Fake lässt jeden Nicht-UID-Aufruf absichtlich scheitern, damit der alte
    Sequenznummer-Regress sofort auffällt — diese Zusicherung bleibt unangetastet,
    deshalb eine eigene Klasse statt eines `list()` in der Basis.
    """

    def list(self):
        return "OK", [b'(\\HasNoChildren) "/" "INBOX"', b'(\\HasNoChildren) "/" "Archiv/2026"']


def test_should_name_a_missing_uid_instead_of_reporting_nothing_to_do(capsys):
    """Eine nicht gefundene UID ist ein Hinweis, kein stilles 'nichts zu tun'.

    Sonst liest sich ein Tippfehler oder eine zwischenzeitlich verschobene Mail
    wie ein erledigter Lauf.
    """
    fetch = _fetch_exchange(1001, "alice@x.de", "Hallo")
    imap = _FakeUidImapMitOrdnern(b"1001", fetch)
    om.cmd_move(imap, "INBOX", "Archiv/2026", None, None, True, ["9999"])
    ausgabe = capsys.readouterr()
    assert "9999" in ausgabe.err


# --- Server-Fähigkeiten nach der Anmeldung (#2069) ---------------------------
#
# `imap.capabilities` hält die Bannerliste von VOR dem Login. Gemessen am
# 2026-08-18 gegen ein produktives Konto: vorher 9 Einträge ohne MOVE/UIDPLUS,
# nachher 30+ mit beiden. `_move` nahm deshalb immer den COPY-Fallback und ließ
# das EXPUNGE aus — 89 Dubletten bei einer Aufräumaktion.


class _FakeCapImap:
    """IMAP-Doppel mit getrennter Banner- und Post-Auth-Fähigkeitsliste."""

    def __init__(self, banner=("IMAP4REV1",), nach_auth="IMAP4rev1 MOVE UIDPLUS"):
        self.capabilities = tuple(banner)
        self._nach_auth = nach_auth
        self.aufrufe = []

    def capability(self):
        if self._nach_auth is None:
            raise imaplib.IMAP4.error("CAPABILITY nicht verfügbar")
        return "OK", [self._nach_auth.encode()]

    def select(self, mailbox, readonly=False):
        return "OK", [b"1"]

    def uid(self, cmd, *args):
        self.aufrufe.append(cmd)
        return "OK", [b"ok"]


def test_should_read_capabilities_after_login_not_from_the_banner():
    imap = _FakeCapImap(banner=("IMAP4REV1",), nach_auth="IMAP4rev1 MOVE UIDPLUS")
    assert "MOVE" in om.faehigkeiten(imap)
    assert "UIDPLUS" in om.faehigkeiten(imap)


def test_should_use_uid_move_when_the_server_reveals_it_only_after_login():
    """Der eigentliche Regress: Banner ohne MOVE, Sitzung mit MOVE."""
    imap = _FakeCapImap(banner=("IMAP4REV1", "IDLE"), nach_auth="IMAP4rev1 MOVE UIDPLUS")
    om._move(imap, "INBOX", "Archiv/2026", [b"1"])
    assert "MOVE" in imap.aufrufe
    assert "COPY" not in imap.aufrufe


def test_should_fall_back_to_copy_when_the_server_really_lacks_move():
    imap = _FakeCapImap(banner=("IMAP4REV1",), nach_auth="IMAP4rev1 IDLE")
    om._move(imap, "INBOX", "Archiv/2026", [b"1"])
    assert "COPY" in imap.aufrufe
    assert "MOVE" not in imap.aufrufe


def test_should_fall_back_to_the_banner_list_when_capability_fails():
    """Ein Abbruch der Abfrage darf das Verschieben nicht zerreißen."""
    imap = _FakeCapImap(banner=("IMAP4REV1", "MOVE"), nach_auth=None)
    assert "MOVE" in om.faehigkeiten(imap)


def test_should_expunge_only_the_named_uids_when_uidplus_is_available():
    imap = _FakeCapImap(nach_auth="IMAP4rev1 UIDPLUS")
    om._move(imap, "INBOX", "Archiv/2026", [b"7"])
    assert imap.aufrufe == ["COPY", "STORE", "EXPUNGE"]


def test_should_warn_on_stdout_too_when_expunge_is_skipped(capsys):
    """Eine Warnung nur auf stderr verschwindet in jeder Pipeline."""
    imap = _FakeCapImap(nach_auth="IMAP4rev1")
    om._move(imap, "INBOX", "Archiv/2026", [b"7"])
    aus = capsys.readouterr()
    assert "EXPUNGE" in aus.out
    assert "EXPUNGE" in aus.err
