"""Tests für tools/mail_agent/mail_view.py — lokale HTML-Ansicht einer IMAP-Mail.

Kein IMAP im Test: geprüft werden die reinen Funktionen (Slug, Sanitizer, Rendering
einer zusammengebauten Message). Der Netzpfad ist in test_read_mail.py abgedeckt.
"""

from __future__ import annotations

import sys
from email.message import EmailMessage
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mail_agent"))

mail_view = pytest.importorskip("mail_view")


class TestSlugify:
    def test_should_transliterate_german_umlauts(self):
        assert mail_view.slugify("Leistungsbezüge für Mitarbeiter") == (
            "leistungsbezuege-fuer-mitarbeiter"
        )

    def test_should_strip_path_separators(self):
        assert "/" not in mail_view.slugify("a/../../etc/passwd")

    def test_should_fall_back_when_subject_is_empty(self):
        assert mail_view.slugify("") == "ohne-betreff"

    def test_should_cap_length(self):
        assert len(mail_view.slugify("wort " * 50)) <= 40


class TestSanitizeHtml:
    def test_should_remove_script_blocks(self):
        out, _ = mail_view.sanitize_html("<p>hallo</p><script>alert(1)</script>")
        assert "script" not in out.lower()
        assert "hallo" in out

    def test_should_neutralize_remote_tracking_pixel(self):
        out, blockiert = mail_view.sanitize_html(
            '<img src="https://track.example/p.gif?id=1" width="1">'
        )
        assert blockiert == 1
        assert "src=" not in out.replace("data-blockiert-src=", "")
        assert "track.example" in out  # Herkunft bleibt sichtbar, nur inaktiv

    def test_should_keep_inline_cid_images(self):
        out, blockiert = mail_view.sanitize_html('<img src="cid:bild001">')
        assert blockiert == 0
        assert 'src="cid:bild001"' in out

    def test_should_strip_event_handlers(self):
        out, _ = mail_view.sanitize_html('<div onclick="steal()">x</div>')
        assert "onclick" not in out.lower()

    def test_should_neutralize_css_url_references(self):
        out, blockiert = mail_view.sanitize_html(
            '<div style="background:url(https://track.example/x.png)">x</div>'
        )
        assert blockiert == 1
        assert "url(https://track.example" not in out


def _nachricht(betreff="Test", *, html_teil=None, text_teil="hallo", anhang=None):
    msg = EmailMessage()
    msg["From"] = "Absender <a@example.org>"
    msg["To"] = "b@example.org"
    msg["Subject"] = betreff
    msg["Date"] = "Wed, 29 Jul 2026 09:00:00 +0200"
    msg.set_content(text_teil)
    if html_teil:
        msg.add_alternative(html_teil, subtype="html")
    if anhang:
        name, daten = anhang
        msg.add_attachment(daten, maintype="application", subtype="pdf", filename=name)
    return msg


class TestRender:
    def test_should_write_file_named_by_uid_and_subject(self, tmp_path):
        datei = mail_view.render(
            _nachricht("Strategiemeeting 30.09."), "hnu", "INBOX", "4711", tmp_path
        )
        assert datei.name == "4711-strategiemeeting-30-09.html"
        assert datei.exists()

    def test_should_carry_headers_and_uid_into_page(self, tmp_path):
        datei = mail_view.render(_nachricht(), "hnu", "INBOX", "4711", tmp_path)
        inhalt = datei.read_text(encoding="utf-8")
        assert "a@example.org" in inhalt
        assert "UID 4711" in inhalt
        assert "hnu" in inhalt

    def test_should_render_plain_text_when_no_html_part(self, tmp_path):
        datei = mail_view.render(
            _nachricht(text_teil="nur text"), "hnu", "INBOX", "1", tmp_path
        )
        assert "nur text" in datei.read_text(encoding="utf-8")

    def test_should_warn_when_remote_references_were_blocked(self, tmp_path):
        msg = _nachricht(html_teil='<p>hi<img src="https://track.example/p.gif"></p>')
        datei = mail_view.render(msg, "hnu", "INBOX", "2", tmp_path)
        inhalt = datei.read_text(encoding="utf-8")
        assert "neutralisiert" in inhalt
        assert "data-blockiert-src" in inhalt

    def test_should_save_attachment_and_link_it_url_encoded(self, tmp_path):
        msg = _nachricht(anhang=("Anhörung Bericht.pdf", b"%PDF-1.4 test"))
        datei = mail_view.render(msg, "hnu", "INBOX", "3", tmp_path)
        gespeichert = tmp_path / "3-anhaenge" / "Anhörung Bericht.pdf"
        assert gespeichert.read_bytes() == b"%PDF-1.4 test"
        inhalt = datei.read_text(encoding="utf-8")
        assert "Anh%C3%B6rung%20Bericht.pdf" in inhalt
        assert 'href="3-anhaenge/Anhörung Bericht.pdf"' not in inhalt

    def test_should_not_escape_attachment_outside_target_dir(self, tmp_path):
        msg = _nachricht(anhang=("../../evil.pdf", b"x"))
        mail_view.render(msg, "hnu", "INBOX", "5", tmp_path)
        assert (tmp_path / "5-anhaenge" / "evil.pdf").exists()
        assert not (tmp_path.parent / "evil.pdf").exists()
