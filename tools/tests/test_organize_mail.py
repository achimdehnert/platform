"""Tests für tools/mail_agent/organize_mail.py — netzfreie Logik:
Header-Decode, Ordner-Namen-Parsing, Papierkorb-Auflösung, Matching-Filter.
Kein IMAP-/Netz-Test (connect/_move/cmd_* bleiben Dogfood/Integration).
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
    imap = _FakeImap([
        b'(\\HasNoChildren) "." "INBOX.Sent"',
        b'(\\HasNoChildren \\Trash) "." INBOX.Trash',
    ])
    assert om.list_folders(imap) == ["INBOX.Sent", "INBOX.Trash"]


def test_should_return_empty_on_list_failure():
    class _Fail:
        def list(self):
            return "NO", []
    assert om.list_folders(_Fail()) == []


# --- Papierkorb-Auflösung ----------------------------------------------------

def test_should_resolve_trash_by_known_candidate():
    imap = _FakeImap([b'(\\HasNoChildren) "." "INBOX.Trash"', b'(\\HasNoChildren) "." "INBOX.Sent"'])
    assert om.resolve_trash(imap) == "INBOX.Trash"


def test_should_resolve_trash_by_name_heuristic():
    imap = _FakeImap([b'(\\HasNoChildren) "." "INBOX.Papierkorb"'])
    assert om.resolve_trash(imap) == "INBOX.Papierkorb"


def test_should_return_none_when_no_trash():
    imap = _FakeImap([b'(\\HasNoChildren) "." "INBOX"', b'(\\HasNoChildren) "." "INBOX.Sent"'])
    assert om.resolve_trash(imap) is None


# --- Header-Decode -----------------------------------------------------------

def test_should_decode_mime_and_flatten():
    assert om._decode("=?iso-8859-1?Q?Antonela?=") == "Antonela"
    assert om._decode("a\nb\r") == "a b"  # Zeilenumbruch → Leerzeichen (Header-Faltung)
    assert om._decode(None) == ""
