"""Tests für tools/mail_agent/read_mail.py — Header-Decode, Body-/Anhang-Extraktion,
From-Filter, Pfad-Traversal-Schutz beim Anhang-Speichern. Kein Netz-/IMAP-Test
(connect/cmd_* bleiben Dogfood/Integration, analog test_send_mail.py).

Run: `python3 -m pytest tools/tests/test_read_mail.py -q`
"""
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
        m.add_attachment(data, maintype="application", subtype="octet-stream", filename=name)
    return m


# --- decode_hdr --------------------------------------------------------------

def test_should_decode_mime_encoded_header():
    enc = "=?iso-8859-1?Q?Pr=FCfergebnis?="
    assert rm.decode_hdr(enc) == "Prüfergebnis"


def test_should_flatten_newlines_and_none():
    assert rm.decode_hdr("a\n b\r") == "a  b"
    assert rm.decode_hdr(None) == ""


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
    assert rm.matches_to(m, "martinkat")   # Treffer im To-Header
    assert rm.matches_to(m, "michalk")     # Treffer im Cc-Header
    assert not rm.matches_to(m, "brandl")
    assert rm.matches_to(m, None)          # kein Filter -> True


def test_should_handle_missing_to_and_cc_headers():
    m = EmailMessage()
    m["From"] = "achim@iil.gmbh"
    m.set_content("x")
    assert rm.matches_to(m, None)
    assert not rm.matches_to(m, "irgendwer")
