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

    monkeypatch.setattr(
        mls.MailLinkHandler,
        "_rendern",
        lambda self, konto, uid, ordner=None: seite,
    )
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

        def _fehlt(self, konto, uid, ordner=None):
            raise mls.MailNichtGefunden(f"keine Nachricht mit UID {uid}")

        monkeypatch.setattr(mls.MailLinkHandler, "_rendern", _fehlt)
        status, _, koerper = _get(server, "/m/999999")
        assert status == 404
        assert b"999999" in koerper

    def test_should_pass_folder_segment_through(self, server, monkeypatch):
        """Ohne Ordner-Segment war nur INBOX erreichbar — ein Entwurf gab 404."""
        gesehen = {}

        def _merken(self, konto, uid, ordner=None):
            gesehen.update(konto=konto, uid=uid, ordner=ordner)
            return Path(__file__)  # irgendeine lesbare Datei

        monkeypatch.setattr(mls.MailLinkHandler, "_rendern", _merken)
        assert _get(server, "/m/hnu/entwuerfe/23254")[0] == 200
        assert gesehen == {"konto": "hnu", "uid": "23254", "ordner": "entwuerfe"}

    def test_should_keep_default_folder_without_segment(self, server, monkeypatch):
        gesehen = {}

        def _merken(self, konto, uid, ordner=None):
            gesehen["ordner"] = ordner
            return Path(__file__)

        monkeypatch.setattr(mls.MailLinkHandler, "_rendern", _merken)
        _get(server, "/m/4711")
        assert gesehen["ordner"] is None

    def test_should_502_when_mailbox_is_unreachable(self, server, monkeypatch):
        def _kaputt(self, konto, uid, ordner=None):
            raise OSError("Verbindung abgelehnt")

        monkeypatch.setattr(mls.MailLinkHandler, "_rendern", _kaputt)
        assert _get(server, "/m/4711")[0] == 502


class TestAnkerRoute:
    """`/a/<item>` löst über die Message-ID auf und überlebt darum ein Verschieben."""

    @pytest.fixture
    def anker_pfad(self, tmp_path, monkeypatch):
        import anker as anker_modul

        pfad = tmp_path / "mail-anker.json"
        anker_modul.speichere(
            {
                "1": anker_modul.Anker(
                    item="1",
                    konto="hnu",
                    ordner="INBOX",
                    uid="100",
                    message_id="<a@hnu.de>",
                    betreff="Leistungsbezüge",
                )
            },
            pfad,
        )
        monkeypatch.setattr(mls.MailLinkHandler, "anker_pfad", pfad)
        return pfad

    def test_should_404_unknown_board_item(self, server, anker_pfad):
        status, _, koerper = _get(server, "/a/999")
        assert status == 404
        assert b"999" in koerper

    def test_should_400_without_board_number(self, server, anker_pfad):
        assert _get(server, "/a")[0] in (400, 404)

    def test_should_fall_back_to_graph_registry_for_iil_items(
        self, server, anker_pfad, registry
    ):
        """IIL-Posten haben keinen IMAP-Anker — `/a/<nr>` muss sie trotzdem finden.

        Ohne diesen Rückfall trägt die Hälfte des Boards (Graph-Konto) keinen Link.
        """
        registry.write_text(
            json.dumps({"7": {"graph_id": "AAMkAGY0="}}), encoding="utf-8"
        )
        status, kopf, _ = _get(server, "/a/7")
        assert status == 302
        assert "AAMkAGY0%3D" in kopf["Location"]

    def test_should_still_404_when_neither_anchor_nor_registry_knows_it(
        self, server, anker_pfad, registry
    ):
        registry.write_text(json.dumps({"7": {"graph_id": "x"}}), encoding="utf-8")
        assert _get(server, "/a/8")[0] == 404

    def test_should_list_anchored_items_on_index(self, server, anker_pfad):
        status, _, koerper = _get(server, "/")
        assert status == 200
        assert b"/a/1" in koerper
        assert "Leistungsbezüge".encode() in koerper


class TestIndex:
    def test_should_list_registered_short_links(self, server):
        status, _, koerper = _get(server, "/")
        assert status == 200
        assert b"/i/az1" in koerper
        assert "Azure Copilot".encode() in koerper


class TestBoardRoute:
    """`/d/<name>` — Arbeitslisten aus ~/.claude/boards.

    Anlass: Retro 2026-07-29 Befund #4. Die Route ging ohne Test in den Merge; der
    vorhandene `TestAnkerRoute` prüft `/a/<item>`, eine ANDERE Route mit ähnlichem
    Namen ("Board-Nummer") — genau die Verwechslung, die einen fehlenden Test wie
    Abdeckung aussehen ließ.
    """

    @pytest.fixture
    def boards(self, tmp_path):
        wurzel = tmp_path / "boards"
        wurzel.mkdir()
        (wurzel / "liste.md").write_text(
            "# Titel\n\n| A | B |\n|---|---|\n| 1 | 2 |\n", encoding="utf-8"
        )
        mls.MailLinkHandler.board_root = wurzel
        return wurzel

    def test_should_serve_board_content_as_html(self, server, boards):
        """Inhalt muss ankommen — unabhängig davon, ob `markdown` installiert ist.

        Die Bibliothek ist optional (CI hat sie nicht). Ein Test, der `<table>`
        erwartet, prüft die Umgebung statt den Code — dieser Fehler kostete am
        2026-07-29 einen roten CI-Lauf.
        """
        status, kopf, koerper = _get(server, "/d/liste")
        assert status == 200
        assert kopf["Content-Type"].startswith("text/html")
        assert "Titel".encode() in koerper

    def test_should_render_tables_when_markdown_available(self, server, boards):
        pytest.importorskip("markdown")
        _, _, koerper = _get(server, "/d/liste")
        assert b"<table>" in koerper  # Tabelle als HTML, nicht als Rohtext

    def test_should_404_unknown_board_name(self, server, boards):
        status, _, _ = _get(server, "/d/gibtsnicht")
        assert status == 404

    def test_should_list_available_boards_on_index(self, server, boards):
        status, _, koerper = _get(server, "/")
        assert status == 200
        assert b"/d/liste" in koerper

    @pytest.mark.parametrize(
        "roh",
        [
            "../../.secrets/token",
            "/etc/passwd",
            "..",
            ".",
            "liste.md",  # Endung gehört nicht in den Namen
            "a/b",
            "",
        ],
    )
    def test_should_reject_names_that_could_escape_the_board_root(self, boards, roh):
        assert mls.board_pfad(roh, boards) is None

    def test_should_resolve_plain_name_inside_root(self, boards):
        assert mls.board_pfad("liste", boards) == (boards / "liste.md").resolve()

    def test_should_refuse_symlink_pointing_out_of_root(self, tmp_path, boards):
        """Ein Symlink im Board-Verzeichnis darf nicht aus ihm herausführen."""
        aussen = tmp_path / "geheim.md"
        aussen.write_text("nicht ausliefern", encoding="utf-8")
        (boards / "trick.md").symlink_to(aussen)
        assert mls.board_pfad("trick", boards) is None

    def test_should_fall_back_to_plain_text_without_markdown_library(
        self, monkeypatch, boards
    ):
        """Fehlt die Bibliothek, bleibt der Inhalt lesbar statt zu scheitern."""
        import builtins

        echt = builtins.__import__

        def ohne_markdown(name, *a, **k):
            if name == "markdown":
                raise ImportError("nicht installiert")
            return echt(name, *a, **k)

        monkeypatch.setattr(builtins, "__import__", ohne_markdown)
        html = mls.board_als_html("# Titel\n\n| A |\n|---|\n", "liste")
        assert "<pre>" in html
        assert "# Titel" in html


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


class TestGraphAnhaenge:
    """Anhänge einer Graph-Nachricht (IIL) — vorher nur ein Hinweistext.

    Der Satz "im OWA-Deeplink abrufbar" sah wie ein Hinweis aus und wirkte wie
    eine Wand: auf einem Rechner ohne angemeldetes OWA war der Anhang gar nicht
    erreichbar. Der IMAP-Zweig konnte das die ganze Zeit.
    """

    @staticmethod
    def _graph(monkeypatch, anhaenge):
        """graph_mail durch eine Attrappe ersetzen, die genau diese Anhänge kennt."""
        import types

        modul = types.SimpleNamespace(
            GRAPH="https://graph.example",
            load_cfg=lambda: {},
            token=lambda cfg, konto: "tok",
            _auth=lambda tok: {},
            _http=lambda methode, url, headers=None: types.SimpleNamespace(
                status_code=200, json=lambda: {"value": anhaenge}
            ),
        )
        monkeypatch.setitem(sys.modules, "graph_mail", modul)

    def test_should_list_file_attachment_as_link(self, server, monkeypatch):
        self._graph(monkeypatch, [
            {"name": "01_VVT.pdf", "size": 2048, "@odata.type": "#microsoft.graph.fileAttachment"},
        ])
        html = mls.MailLinkHandler._graph_anhang_liste(
            mls.MailLinkHandler, "az1", "AAMkAGY0=", "tok"
        )
        assert '/r/az1/anhaenge/01_VVT.pdf' in html
        assert "2 kB" in html

    def test_should_name_embedded_message_without_linking_it(self, server, monkeypatch):
        """Eine eingebettete Mail hat keine Bytes — benennen, nicht verlinken.

        Sie stumm wegzulassen war der Fehler, an dem der weitergeleitete
        Mailanhang am 2026-08-19 spurlos aus der Ansicht verschwand.
        """
        self._graph(monkeypatch, [
            {"name": "AW: Unterlagen", "size": 900, "@odata.type": "#microsoft.graph.itemAttachment"},
        ])
        html = mls.MailLinkHandler._graph_anhang_liste(
            mls.MailLinkHandler, "az1", "AAMkAGY0=", "tok"
        )
        assert "AW: Unterlagen" in html
        assert "anhaenge/AW" not in html
        assert "eingebettete Nachricht" in html

    def test_should_skip_inline_images(self, server, monkeypatch):
        """Signaturbilder sind kein Anhang, den jemand herunterladen will."""
        self._graph(monkeypatch, [
            {"name": "image001.png", "size": 900, "isInline": True,
             "@odata.type": "#microsoft.graph.fileAttachment"},
        ])
        html = mls.MailLinkHandler._graph_anhang_liste(
            mls.MailLinkHandler, "az1", "AAMkAGY0=", "tok"
        )
        assert html == ""

    def test_should_404_attachment_route_for_unknown_short_id(self, server):
        """Die neue Route darf keine unbekannte Kurz-ID durchreichen."""
        status, _, _ = _get(server, "/r/kennichnicht/anhaenge/x.pdf")
        assert status == 404
