"""Tests für tools/mail_agent/send_mail.py — Config-/Credentials-Parsing (retro f4a546 #4).

Deckt: parse_env (Quotes, Kommentare, Leerzeilen), load_credentials (Paar-Bildung in
Zeilen-Reihenfolge, Auswahl per user==sender, Quotes, fehlendes Paar → SystemExit,
password vor user / verwaistes password → kein False-Match), build_message (Empfänger,
Anhänge, Body-Quelle). Kein Netz-/SMTP-Test (send() bleibt Dogfood/Integration).

Run: `python3 -m pytest tools/tests/test_send_mail.py -q`
"""
import argparse
import importlib.util
import pathlib

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "send_mail.py"
_spec = importlib.util.spec_from_file_location("send_mail", _SRC)
sm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sm)


def _creds(tmp_path, text):
    f = tmp_path / "creds.env"
    f.write_text(text)
    return f


# --- parse_env ---------------------------------------------------------------

def test_should_parse_env_with_quotes_comments_and_blanks(tmp_path):
    f = _creds(tmp_path, "# Kommentar\n\nSMTP_HOST='mail.example.org'\nSMTP_PORT=465\nMAIL_FROM=\"a@b.c\"\n")
    values = sm.parse_env(f)
    assert values == {"SMTP_HOST": "mail.example.org", "SMTP_PORT": "465", "MAIL_FROM": "a@b.c"}


def test_should_keep_last_value_on_duplicate_keys(tmp_path):
    f = _creds(tmp_path, "K=1\nK=2\n")
    assert sm.parse_env(f)["K"] == "2"


# --- load_credentials --------------------------------------------------------

def test_should_pick_pair_matching_sender_among_multiple(tmp_path):
    f = _creds(tmp_path, "user='x@d.team'\npassword='px'\nuser='ad@d.team'\npassword='pa'\n")
    assert sm.load_credentials(f, "ad@d.team") == ("ad@d.team", "pa")


def test_should_pair_by_line_order_not_by_proximity(tmp_path):
    # verwaistes password VOR dem passenden user darf nicht matchen
    f = _creds(tmp_path, "password='orphan'\nuser='ad@d.team'\npassword='real'\n")
    assert sm.load_credentials(f, "ad@d.team") == ("ad@d.team", "real")


def test_should_use_last_pair_on_duplicate_user_rotation(tmp_path):
    # Passwort-Rotation hängt das neue Paar unten an — das LETZTE gewinnt
    # (retro f4a546-incr #6: first-match lieferte still den veralteten Wert)
    f = _creds(tmp_path, "user='ad@d.team'\npassword='OLD'\nuser='ad@d.team'\npassword='NEW'\n")
    assert sm.load_credentials(f, "ad@d.team") == ("ad@d.team", "NEW")


def test_should_exit_when_sender_has_no_pair(tmp_path):
    f = _creds(tmp_path, "user='x@d.team'\npassword='px'\n")
    with pytest.raises(SystemExit):
        sm.load_credentials(f, "ad@d.team")


def test_should_exit_on_empty_file(tmp_path):
    with pytest.raises(SystemExit):
        sm.load_credentials(_creds(tmp_path, ""), "ad@d.team")


def test_should_ignore_non_kv_lines(tmp_path):
    f = _creds(tmp_path, "IMAP-SSL noise ohne gleichheitszeichen\nuser='ad@d.team'\npassword='pa'\n")
    assert sm.load_credentials(f, "ad@d.team") == ("ad@d.team", "pa")


# --- build_message -----------------------------------------------------------

def _args(**kw):
    base = dict(to=["r@x.y"], subject="s", body="b", body_file=None, attach=[], sender=None)
    base.update(kw)
    return argparse.Namespace(**base)


def test_should_build_message_with_recipients_and_subject():
    msg = sm.build_message("a@b.c", _args(to=["r1@x.y", "r2@x.y"]))
    assert msg["From"] == "a@b.c"
    assert msg["To"] == "r1@x.y, r2@x.y"
    assert msg["Subject"] == "s"
    assert "b" in msg.get_content()


def test_should_read_body_from_file(tmp_path):
    bf = tmp_path / "body.txt"
    bf.write_text("datei-body\n")
    msg = sm.build_message("a@b.c", _args(body=None, body_file=str(bf)))
    assert "datei-body" in msg.get_content()


def test_should_attach_markdown_as_text_markdown(tmp_path):
    att = tmp_path / "doc.md"
    att.write_text("# hi\n")
    msg = sm.build_message("a@b.c", _args(attach=[str(att)]))
    parts = [p for p in msg.iter_attachments()]
    assert len(parts) == 1
    assert parts[0].get_content_type() == "text/markdown"
    assert parts[0].get_filename() == "doc.md"


# --- HTML-Body (multipart/alternative) ---------------------------------------

def test_should_build_multipart_alternative_with_html_and_text(tmp_path):
    hf = tmp_path / "mail.html"
    hf.write_text("<p>Hallo <strong>Ilja</strong></p>")
    msg = sm.build_message("a@b.c", _args(body="text-fallback", body_file=None, html_file=str(hf)))
    assert msg.get_content_type() == "multipart/alternative"
    types = {p.get_content_type() for p in msg.iter_parts()}
    assert types == {"text/plain", "text/html"}
    html_part = next(p for p in msg.iter_parts() if p.get_content_type() == "text/html")
    assert "<strong>Ilja</strong>" in html_part.get_content()
    text_part = next(p for p in msg.iter_parts() if p.get_content_type() == "text/plain")
    assert "text-fallback" in text_part.get_content()


def test_should_derive_text_fallback_from_html_when_no_body(tmp_path):
    hf = tmp_path / "mail.html"
    hf.write_text("<p>Hallo Ilja</p><p>Zeile zwei</p>")
    msg = sm.build_message("a@b.c", _args(body=None, body_file=None, html_file=str(hf)))
    assert msg.get_content_type() == "multipart/alternative"
    text_part = next(p for p in msg.iter_parts() if p.get_content_type() == "text/plain")
    txt = text_part.get_content()
    assert "Hallo Ilja" in txt and "Zeile zwei" in txt
    assert "<p>" not in txt


def test_should_strip_tags_and_unescape_in_html_to_text():
    out = sm.html_to_text("<style>x{color:red}</style><p>Guten Tag &amp; hallo</p><br>Ende")
    assert "Guten Tag & hallo" in out
    assert "<" not in out and "color:red" not in out


# --- find_sent_folder (Sent-Kopie, kein Netz — s. append_to_sent Docstring) ---

class _FakeImap:
    def __init__(self, list_response):
        self._list_response = list_response

    def list(self):
        return "OK", self._list_response


def test_should_prefer_special_use_sent_flag_over_name_heuristic():
    # Realer Server-Output (dogfood 2026-07-17): Name unquoted, \Sent-Flag gesetzt.
    imap = _FakeImap([
        b'(\\HasNoChildren \\UnMarked \\Trash) "." INBOX.Trash',
        b'(\\HasNoChildren \\UnMarked \\Sent) "." INBOX.Sent',
    ])
    assert sm.find_sent_folder(imap, None) == "INBOX.Sent"


def test_should_prefer_configured_folder_when_it_exists_and_no_special_use_flag():
    imap = _FakeImap([b'(\\HasNoChildren) "." "INBOX.Sent"', b'(\\HasNoChildren) "." "Sent"'])
    assert sm.find_sent_folder(imap, "Sent") == "Sent"


def test_should_fall_back_to_name_heuristic_when_configured_is_absent():
    imap = _FakeImap([b'(\\HasNoChildren) "." "INBOX.Sent"', b'(\\HasNoChildren) "." "INBOX.Trash"'])
    assert sm.find_sent_folder(imap, "Sent") == "INBOX.Sent"


def test_should_return_configured_when_list_has_no_sent_candidate():
    imap = _FakeImap([b'(\\HasNoChildren) "." "INBOX"', b'(\\HasNoChildren) "." "INBOX.Trash"'])
    assert sm.find_sent_folder(imap, "Sent") == "Sent"


def test_should_return_none_when_list_fails_and_nothing_configured():
    class _FailingImap:
        def list(self):
            return "NO", []

    assert sm.find_sent_folder(_FailingImap(), None) is None
