"""Tests für tools/mail_agent/mail_link_server.py — kurze Links über Loopback.

Der IMAP-Pfad ist gestubbt: geprüft werden Routing, Weiterleitung, Traversal-Schutz
und die Loopback-Sperre. Das Postfach wird in keinem Test angefasst.
"""

from __future__ import annotations

import http.client
import json
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mail_agent"))

mls = pytest.importorskip("mail_link_server")


@pytest.fixture
def registry(tmp_path):
    pfad = tmp_path / "mail-links.json"
    pfad.write_text(
        json.dumps(
            {
                "az1": {"graph_id": "AAMkAGY0=", "notiz": "Azure Copilot"},
                "roh": {"url": "https://example.org/direkt"},
            }
        ),
        encoding="utf-8",
    )
    return pfad


@pytest.fixture
def server(tmp_path, registry, monkeypatch):
    """Server auf einem freien Port; IMAP durch eine feste Datei ersetzt."""
    seite = tmp_path / "hnu" / "inbox" / "4711-test.html"
    seite.parent.mkdir(parents=True)
    seite.write_text("<h1>Testmail</h1>", encoding="utf-8")
    (seite.parent / "4711-anhaenge").mkdir()
    (seite.parent / "4711-anhaenge" / "bericht.pdf").write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(mls.MailLinkHandler, "_rendern", lambda self, konto, uid: seite)
    mls.MailLinkHandler.konten = {"hnu": "hnu", "ad": "ad"}
    mls.MailLinkHandler.default_konto = "hnu"
    mls.MailLinkHandler.registry_pfad = registry

    srv = ThreadingHTTPServer(("127.0.0.1", 0), mls.MailLinkHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv
    srv.shutdown()


def _get(srv, pfad):
    conn = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=5)
    conn.request("GET", pfad)
    antwort = conn.getresponse()
    koerper = antwort.read()
    conn.close()
    return antwort.status, dict(antwort.getheaders()), koerper


class TestKurzlink:
    def test_should_redirect_short_id_to_owa_deeplink(self, server):
        status, kopf, _ = _get(server, "/i/az1")
        assert status == 302
        assert kopf["Location"].startswith("https://outlook.office365.com/owa/?ItemID=")
        assert "AAMkAGY0%3D" in kopf["Location"]

    def test_should_prefer_explicit_url_over_graph_id(self, server):
        status, kopf, _ = _get(server, "/i/roh")
        assert (status, kopf["Location"]) == (302, "https://example.org/direkt")

    def test_should_404_unknown_short_id(self, server):
        assert _get(server, "/i/gibtsnicht")[0] == 404

    def test_should_reject_malformed_short_id(self, server):
        assert _get(server, "/i/../../etc")[0] in (400, 404)

    def test_should_not_leak_referrer(self, server):
        assert _get(server, "/i/az1")[1]["Referrer-Policy"] == "no-referrer"


class TestMailRoute:
    def test_should_serve_rendered_mail_by_uid(self, server):
        status, _, koerper = _get(server, "/m/4711")
        assert status == 200
        assert b"Testmail" in koerper

    def test_should_accept_explicit_account_segment(self, server):
        assert _get(server, "/m/hnu/4711")[0] == 200

    def test_should_reject_non_numeric_uid(self, server):
        assert _get(server, "/m/kein-uid")[0] == 400

    def test_should_serve_attachment(self, server):
        status, _, koerper = _get(server, "/m/4711/anhaenge/bericht.pdf")
        assert (status, koerper) == (200, b"%PDF-1.4")

    def test_should_block_path_traversal_in_attachment_name(self, server):
        status, _, _ = _get(server, "/m/4711/anhaenge/..%2F..%2F..%2Fetc%2Fpasswd")
        assert status == 404

    def test_should_404_unknown_attachment(self, server):
        assert _get(server, "/m/4711/anhaenge/gibtsnicht.pdf")[0] == 404

    def test_should_404_when_message_does_not_exist(self, server, monkeypatch):
        """Früher beendete sich der Fetch per sys.exit — das SystemExit ging an
        `except Exception` vorbei, der Request-Thread starb und der Browser bekam
        eine leere Antwort statt einer Fehlerseite (gemessen an /m/ad/64)."""

        def _fehlt(self, konto, uid):
            raise mls.MailNichtGefunden(f"keine Nachricht mit UID {uid}")

        monkeypatch.setattr(mls.MailLinkHandler, "_rendern", _fehlt)
        status, _, koerper = _get(server, "/m/999999")
        assert status == 404
        assert b"999999" in koerper

    def test_should_502_when_mailbox_is_unreachable(self, server, monkeypatch):
        def _kaputt(self, konto, uid):
            raise OSError("Verbindung abgelehnt")

        monkeypatch.setattr(mls.MailLinkHandler, "_rendern", _kaputt)
        assert _get(server, "/m/4711")[0] == 502


class TestIndex:
    def test_should_list_registered_short_links(self, server):
        status, _, koerper = _get(server, "/")
        assert status == 200
        assert b"/i/az1" in koerper
        assert "Azure Copilot".encode() in koerper


class TestSicherheitsgrenzen:
    def test_should_refuse_non_loopback_bind_without_optin(self, monkeypatch, capsys):
        monkeypatch.setattr(
            sys, "argv", ["mail_link_server.py", "--host", "0.0.0.0", "--port", "8787"]
        )
        with pytest.raises(SystemExit) as exc:
            mls.main()
        assert "Authentifizierung" in str(exc.value)

    def test_should_build_owa_link_url_encoded(self):
        link = mls.owa_link("AAMk+/=id")
        assert "AAMk%2B%2F%3Did" in link
        assert link.endswith("&exvsurl=1&viewmodel=ReadMessageItem")

    @pytest.mark.parametrize(
        "roh", ["../../etc/passwd", "/etc/passwd", "..", ".", "a\x00b"]
    )
    def test_should_reject_unsafe_attachment_names(self, roh):
        assert mls.sicherer_dateiname(roh) in (None, "passwd", "b")

    def test_should_keep_plain_attachment_name(self):
        assert mls.sicherer_dateiname("Anh%C3%B6rung%20Bericht.pdf") == (
            "Anhörung Bericht.pdf"
        )


class TestKontenAufloesung:
    """Ein Konto ohne passende Config ließ den Dienst früher starten und jede
    Anfrage mit 502 enden (gemessen 2026-07-29 mit `--account ad`)."""

    @pytest.fixture
    def claude_dir(self, tmp_path, monkeypatch):
        verzeichnis = tmp_path / ".claude"
        verzeichnis.mkdir()
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        # `_resolve_config` greift für die namenlose Config auf die Konstante
        # `read_mail.CONFIG_FILE` zu, die beim Import einmal aus dem echten
        # Home gebildet wird — der Path.home-Patch allein erreicht sie nicht.
        # Ohne diese Zeile bestand der Test lokal nur deshalb, weil dort eine
        # echte ~/.claude/mail.env liegt, und fiel in CI um (2026-07-29).
        import read_mail

        monkeypatch.setattr(read_mail, "CONFIG_FILE", verzeichnis / "mail.env")
        return verzeichnis

    def test_should_map_plain_name_to_named_config(self, claude_dir):
        (claude_dir / "mail-hnu.env").write_text("x")
        assert mls.konten_aufloesen(["hnu"]) == {"hnu": "hnu"}

    def test_should_map_default_suffix_to_unnamed_config(self, claude_dir):
        (claude_dir / "mail.env").write_text("x")
        assert mls.konten_aufloesen(["ad=default"]) == {"ad": None}

    def test_should_map_explicit_config_name(self, claude_dir):
        (claude_dir / "mail-search.env").write_text("x")
        assert mls.konten_aufloesen(["privat=search"]) == {"privat": "search"}

    def test_should_fail_fast_when_config_is_missing(self, claude_dir):
        with pytest.raises(SystemExit) as exc:
            mls.konten_aufloesen(["ad"])
        assert "ad=default" in str(exc.value)
