"""Tests für tools/mail_agent/organize_mail.py — netzfreie Logik:
Header-Decode, Ordner-Namen-Parsing, Papierkorb-Auflösung, Matching-Filter
UND der Move-Pfad (_matches/_move) über Mock-IMAP (Seq-Nr-vs-UID-Regress).
Nur connect/cmd_* bleiben Dogfood/Integration (echte Verbindung).
"""

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

    def select(self, folder, readonly=False):
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
