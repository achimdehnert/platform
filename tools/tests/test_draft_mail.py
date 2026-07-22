"""Tests für tools/mail_agent/draft_mail.py — Ordner-Auflösung, HTML→Text, Entwurfsbau.

Deckt: find_drafts_folder (SPECIAL-USE \\Drafts gewinnt, --folder-Vorgabe, de/en-Namens-
heuristik, kein Kandidat), html_to_text (Absätze/Listen/Entities), build_draft (Empfänger,
Cc, multipart/alternative nur mit HTML, abgeleiteter Text-Teil, Anhänge, leerer Body).
Kein Netz-/IMAP-Test (append_draft bleibt Dogfood/Integration, wie send() in send_mail).

Run: `python3 -m pytest tools/tests/test_draft_mail.py -q`
"""

import importlib.util
import pathlib

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "draft_mail.py"
_spec = importlib.util.spec_from_file_location("draft_mail", _SRC)
dm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dm)


class _FakeImap:
    """Minimal-Stub: liefert nur die LIST-Antwort, die find_drafts_folder auswertet."""

    def __init__(self, lines, typ="OK"):
        self._lines = [line.encode() for line in lines]
        self._typ = typ

    def list(self):
        return self._typ, self._lines


# --- find_drafts_folder ------------------------------------------------------


def test_should_prefer_special_use_drafts_over_name_guessing():
    imap = _FakeImap(
        [
            '(\\HasNoChildren) "/" Entwuerfe-alt',
            '(\\HasNoChildren \\Drafts) "/" Entw&APw-rfe',
        ]
    )
    assert dm.find_drafts_folder(imap, None) == "Entw&APw-rfe"


def test_should_use_configured_folder_when_it_exists_and_no_special_use():
    imap = _FakeImap(
        [
            '(\\HasNoChildren) "/" INBOX.Drafts',
            '(\\HasNoChildren) "/" Archiv',
        ]
    )
    assert dm.find_drafts_folder(imap, "INBOX.Drafts") == "INBOX.Drafts"


def test_should_fall_back_to_german_folder_name():
    imap = _FakeImap(
        [
            '(\\HasNoChildren) "/" Archiv',
            '(\\HasNoChildren) "/" Entw&APw-rfe',
        ]
    )
    assert dm.find_drafts_folder(imap, None) == "Entw&APw-rfe"


def test_should_return_configured_when_list_fails():
    imap = _FakeImap([], typ="NO")
    assert dm.find_drafts_folder(imap, "Drafts") == "Drafts"


def test_should_return_none_when_no_candidate_and_nothing_configured():
    imap = _FakeImap(['(\\HasNoChildren) "/" Archiv'])
    assert dm.find_drafts_folder(imap, None) is None


# --- html_to_text ------------------------------------------------------------


def test_should_render_paragraphs_and_lists_as_readable_text():
    text = dm.html_to_text(
        "<p>Hallo</p><ul><li>eins</li><li>zwei</li></ul><p>Gr&uuml;&szlig;e</p>"
    )
    assert "Hallo" in text
    assert "- eins" in text and "- zwei" in text
    assert "Grüße" in text
    assert "<" not in text


def test_should_collapse_excess_blank_lines():
    assert "\n\n\n" not in dm.html_to_text("<p>a</p><p></p><p></p><p>b</p>")


# --- build_draft -------------------------------------------------------------


def test_should_build_plain_text_draft_without_alternative():
    msg = dm.build_draft("me@x.de", ["a@b.de"], [], "Betreff", text="Hallo\n")
    assert msg.get_content_type() == "text/plain"
    assert msg["To"] == "a@b.de"
    assert msg["Cc"] is None


def test_should_build_alternative_and_derive_text_part_from_html():
    msg = dm.build_draft(
        "me@x.de", ["a@b.de"], ["c@d.de"], "Betreff", html="<p>Hallo</p>"
    )
    assert msg.get_content_type() == "multipart/alternative"
    assert msg["Cc"] == "c@d.de"
    types = {part.get_content_type() for part in msg.walk()}
    assert {"text/plain", "text/html"} <= types
    plain = next(p for p in msg.walk() if p.get_content_type() == "text/plain")
    assert "Hallo" in plain.get_payload(decode=True).decode()


def test_should_join_multiple_recipients():
    msg = dm.build_draft("me@x.de", ["a@b.de", "e@f.de"], [], "B", text="x")
    assert msg["To"] == "a@b.de, e@f.de"


def test_should_attach_file_with_guessed_mimetype(tmp_path):
    attachment = tmp_path / "notiz.txt"
    attachment.write_text("inhalt")
    msg = dm.build_draft(
        "me@x.de", ["a@b.de"], [], "B", text="x", attachments=[str(attachment)]
    )
    names = [part.get_filename() for part in msg.walk() if part.get_filename()]
    assert names == ["notiz.txt"]


def test_should_reject_draft_without_any_body():
    with pytest.raises(ValueError):
        dm.build_draft("me@x.de", ["a@b.de"], [], "Betreff")
