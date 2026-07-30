"""Antwort-Entwürfe: Zitat erhalten (Graph) und Strang-Zuordnung (IMAP).

Anlass 2026-07-30: Drei Antwort-Entwürfe enthielten **kein** Zitat der
Ursprungsmail. `createReply` legt es an, der anschließende PATCH mit
`body.content` ersetzte aber den ganzen Rumpf. Auf der IMAP-Seite fehlten
`In-Reply-To`/`References` ganz — dort landet eine Antwort beim Empfänger als
neuer Strang, obwohl der Betreff stimmt.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mail_agent"))

gm = pytest.importorskip("graph_mail")
dm = pytest.importorskip("draft_mail")
rl = pytest.importorskip("roles")


class TestGraphZitatErhalten:
    ZITAT_HTML = '<div id="divRplyFwdMsg">Von: Herrmann<br>Hallo Herr Dehnert,</div>'

    def test_should_keep_quote_and_put_new_text_first(self):
        r = gm._antwort_rumpf("Meine Antwort.", self.ZITAT_HTML, "html")
        assert r["contentType"] == "HTML"
        assert "divRplyFwdMsg" in r["content"], "Zitat wurde verworfen"
        assert r["content"].index("Meine Antwort") < r["content"].index("divRplyFwdMsg")

    def test_should_preserve_line_breaks_as_paragraphs(self):
        r = gm._antwort_rumpf("Zeile eins\nZeile zwei", self.ZITAT_HTML, "html")
        assert "<p>Zeile eins</p>" in r["content"]
        assert "<p>Zeile zwei</p>" in r["content"]

    def test_should_escape_html_in_plain_input(self):
        """Klartext mit spitzen Klammern darf das Markup nicht zerreißen."""
        r = gm._antwort_rumpf("Preis < 2 TEUR & fair", self.ZITAT_HTML, "html")
        assert "&lt; 2 TEUR &amp; fair" in r["content"]
        assert "<p>Preis" in r["content"]

    def test_should_keep_blank_lines_as_spacer(self):
        r = gm._antwort_rumpf("oben\n\nunten", self.ZITAT_HTML, "html")
        assert "&nbsp;" in r["content"]

    def test_should_stay_plain_when_original_is_plain(self):
        r = gm._antwort_rumpf("Antwort", "> Original", "text")
        assert r["contentType"] == "Text"
        assert r["content"] == "Antwort\n\n> Original"

    def test_should_fall_back_when_no_quote_exists(self):
        """Ursprungsmail ohne Rumpf — dann wie bisher reiner Text, kein leeres HTML."""
        r = gm._antwort_rumpf("Antwort", "   ", "html")
        assert r == {"contentType": "Text", "content": "Antwort"}


class TestDesignImAntwortEntwurf:
    """--design: fertiges Rollen-HTML darf nicht escaped, das Zitat nicht verworfen werden."""

    def test_should_keep_html_design_unescaped_before_quote(self):
        design = "<html><body><p>Meine Antwort.</p></body></html>"
        r = gm._antwort_rumpf(design, "<div>Zitat</div>", "html", neu_ist_html=True)
        assert r["contentType"] == "HTML"
        assert design in r["content"], "Design wurde escaped oder verworfen"
        assert r["content"].endswith("<div>Zitat</div>")

    def test_should_wrap_plain_quote_in_pre(self):
        r = gm._antwort_rumpf("<p>x</p>", "> Original <b>", "text", neu_ist_html=True)
        assert "<pre>&gt; Original &lt;b&gt;</pre>" in r["content"]

    def test_should_stay_html_without_quote(self):
        r = gm._antwort_rumpf("<p>x</p>", "", "html", neu_ist_html=True)
        assert r == {"contentType": "HTML", "content": "<p>x</p>"}


class TestKlartextZerlegung:
    MAIL = (
        "Hallo Frau Ruß,\n\n"
        "ja, der 01.10. passt.\n\n"
        "Diese vier Tage kommen in Frage:\n"
        "- Di 20.10.2026\n"
        "- Mi 21.10.2026\n\n"
        "Herzliche Grüße\n"
        "Achim Dehnert\n"
    )

    def test_should_split_greeting_paragraphs_and_closing(self):
        b = rl.zerlege_klartext(self.MAIL)
        assert b["greeting"] == "Hallo Frau Ruß,"
        assert b["closing"] == "Herzliche Grüße"
        assert len(b["paragraphs"]) == 2

    def test_should_drop_name_block_below_closing(self):
        """Der Name kommt aus der Rollen-Signatur — im Rumpf wäre er doppelt."""
        b = rl.zerlege_klartext(self.MAIL)
        assert all("Achim Dehnert" not in p for p in b["paragraphs"])

    def test_should_keep_list_lines_separate(self):
        b = rl.zerlege_klartext(self.MAIL)
        assert b["paragraphs"][1].count("\n") == 2  # Einleitung + zwei Termine

    def test_should_default_closing_when_missing(self):
        b = rl.zerlege_klartext("Hallo,\n\nkurzer Hinweis.\n")
        assert b["closing"] == "Viele Grüße"
        assert b["paragraphs"] == ["kurzer Hinweis."]

    def test_should_render_intra_paragraph_breaks_as_br(self):
        profile = rl.Profile(
            role_id="t",
            display_name="T",
            sender="t@example.org",
            transport="graph_draft",
        )
        out = rl.render_email_html(
            profile, eyebrow="E", greeting="Hallo,", paragraphs=["a\nb"]
        )
        assert "a<br>b" in out


class TestImapZitatBlock:
    """IMAP-APPEND hat kein `createReply` — der Zitat-Block wird selbst gebaut."""

    @staticmethod
    def _ursprung():
        from email.message import EmailMessage

        m = EmailMessage()
        m["From"] = "Ruß, Annika <Annika.Russ@hnu.de>"
        m["To"] = "Dehnert, Achim <Achim.Dehnert@hnu.de>"
        m["Date"] = "Wed, 29 Jul 2026 15:29:00 +0200"
        m["Subject"] = "AW: Prüfungsleistung M7 DIL"
        m.set_content("Hallo Herr Dehnert,\n\npasst der 01.10.?\n\nA. Ruß")
        return m

    def test_should_render_outlook_style_header(self):
        z = dm.zitat_bauen(self._ursprung(), als_html=True)
        for label in ("Von:", "Gesendet:", "An:", "Betreff:"):
            assert f"<b>{label}</b>" in z
        assert "passt der 01.10.?" in z

    def test_should_escape_original_body(self):
        m = self._ursprung()
        m.set_content("Preis <b>hoch</b> & knapp")
        z = dm.zitat_bauen(m, als_html=True)
        assert "&lt;b&gt;hoch&lt;/b&gt; &amp; knapp" in z

    def test_should_prefix_quoted_lines_in_text_mode(self):
        z = dm.zitat_bauen(self._ursprung(), als_html=False)
        assert "-----Urspruengliche Nachricht-----" in z
        assert "> Hallo Herr Dehnert," in z
        assert "<b>" not in z


class TestImapStrangZuordnung:
    MID = "<635f02a0a4c84b19ba905d54a7ec3d3a@hnu.de>"

    def test_should_set_in_reply_to_and_references(self):
        msg = dm.build_draft(
            "a@b.de", ["c@d.de"], [], "AW: Test", text="x", in_reply_to=self.MID
        )
        assert msg["In-Reply-To"] == self.MID
        assert msg["References"] == self.MID

    def test_should_prefer_explicit_references_chain(self):
        kette = "<eins@x> <zwei@x>"
        msg = dm.build_draft(
            "a@b.de",
            ["c@d.de"],
            [],
            "AW: Test",
            text="x",
            in_reply_to=self.MID,
            references=kette,
        )
        assert msg["References"] == kette
        assert msg["In-Reply-To"] == self.MID

    def test_should_omit_headers_without_reply_id(self):
        """Eine Neu-Mail darf keine Strang-Kopfzeilen tragen."""
        msg = dm.build_draft("a@b.de", ["c@d.de"], [], "Neu", text="x")
        assert msg["In-Reply-To"] is None
        assert msg["References"] is None
