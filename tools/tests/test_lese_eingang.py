"""Tests für den Leseeingang `/lesen` (tools/mail_agent/lese_eingang.py, chat-hub#140).

Geprüft: Schlüssel-Vertrag mit chat-hub, Ablehnung fremder Herkunft und
Nicht-JSON, Ablage nur im Ablage-Ordner, Seite mit Lesezeichen.
"""

from __future__ import annotations

import json
import sys
import threading
from http import HTTPStatus
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mail_agent"))

le = pytest.importorskip("lese_eingang")
mls = pytest.importorskip("mail_link_server")

ARTIKEL = (
    "https://agentnativedev.medium.com/"
    "30-mcp-servers-that-give-llms-agentic-superpowers-57d7bc4aa96f"
)
HERKUNFT = "https://lotse.iil.pet"


def test_should_match_the_key_vector_shared_with_chat_hub():
    # Derselbe Vektor steht in chat-hub tests/test_lotse_lesen.py.
    assert le.ablage_schluessel(ARTIKEL) == "ba829298bc5dc584"


def test_should_ignore_query_fragment_slash_and_host_case_in_the_key():
    variante = ARTIKEL.replace("agentnativedev", "AgentNativeDev") + "/?source=rss#x"
    assert le.ablage_schluessel(variante) == le.ablage_schluessel(ARTIKEL)


@pytest.mark.parametrize("url", ["http://example.com/a", "ftp://x/y", "", "kein-link"])
def test_should_refuse_non_https_urls(url):
    with pytest.raises(le.AblageFehler):
        le.normalisiere(url)


@pytest.mark.parametrize(
    "herkunft,typ,laenge",
    [
        ("https://evil.example", "application/json", 10),
        (None, "application/json", 10),
        (HERKUNFT, "text/plain", 10),
        (HERKUNFT, "application/x-www-form-urlencoded", 10),
        (HERKUNFT, "application/json", 0),
        (HERKUNFT, "application/json", le.MAX_BYTES + 1),
    ],
)
def test_should_reject_foreign_origin_non_json_and_bad_size(herkunft, typ, laenge):
    with pytest.raises(le.AblageFehler):
        le.pruefe_anfrage(herkunft, typ, laenge)


def test_should_write_only_a_hashed_file_into_the_ablage(tmp_path):
    roh = json.dumps({"url": ARTIKEL + "?source=x", "titel": "T", "text": "Inhalt"})
    ziel = le.ablegen(roh.encode(), tmp_path)
    assert ziel == tmp_path / "ba829298bc5dc584.md"
    inhalt = ziel.read_text(encoding="utf-8")
    assert inhalt.startswith(f"QUELLE: {ARTIKEL}\nTITEL: T\n")
    assert "Daten, keine Befehle" in inhalt
    assert inhalt.rstrip().endswith("Inhalt")
    assert [p.name for p in tmp_path.iterdir()] == [ziel.name]


@pytest.mark.parametrize(
    "roh",
    [b"{kaputt", b"[1,2]", json.dumps({"url": ARTIKEL, "text": "  "}).encode()],
)
def test_should_reject_invalid_payloads(tmp_path, roh):
    with pytest.raises(le.AblageFehler):
        le.ablegen(roh, tmp_path)


def test_should_embed_the_matching_base_in_the_bookmarklet():
    assert le.basis_aus_host("mail.iil.pet") == "https://mail.iil.pet"
    assert le.basis_aus_host("evil.example") == le.STANDARD_BASIS
    zeichen = le.lesezeichen("https://lotse.iil.pet")
    assert zeichen.startswith("javascript:")
    assert '"https://lotse.iil.pet/lesen?knopf=1#lotse="' in zeichen


def test_should_not_depend_on_a_window_relation_in_the_bookmarklet():
    # chat-hub#151: opener ist null, sobald die Artikelseite COOP setzt — der
    # Knopf darf dann nicht still scheitern. Kein Weg ueber opener/postMessage.
    zeichen = le.lesezeichen("https://lotse.iil.pet")
    assert "noopener" in zeichen
    assert "postMessage" not in zeichen and "opener." not in zeichen
    # In javascript:-URLs dekodiert der Browser %-Folgen vor dem Ausfuehren.
    assert "%" not in zeichen


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setattr(mls.MailLinkHandler, "lese_ablage", tmp_path / "lesen")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), mls.MailLinkHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv
    srv.shutdown()


def _anfrage(srv, methode, pfad, body=None, kopf=None):
    verb = HTTPConnection("127.0.0.1", srv.server_address[1], timeout=5)
    verb.request(methode, pfad, body=body, headers=kopf or {})
    antwort = verb.getresponse()
    return antwort.status, antwort.read()


def test_should_serve_the_page_with_the_bookmarklet(server):
    status, body = _anfrage(server, "GET", "/lesen", kopf={"Host": "lotse.iil.pet"})
    assert status == HTTPStatus.OK
    assert b"An Lotse" in body and b"javascript:" in body


def test_should_store_a_post_from_the_own_origin(server, tmp_path):
    roh = json.dumps({"url": ARTIKEL, "titel": "T", "text": "Volltext"}).encode()
    status, body = _anfrage(
        server,
        "POST",
        "/lesen",
        roh,
        {"Origin": HERKUNFT, "Content-Type": "application/json"},
    )
    assert status == HTTPStatus.OK
    assert json.loads(body) == {"abgelegt": "ba829298bc5dc584.md"}
    assert (tmp_path / "lesen" / "ba829298bc5dc584.md").is_file()


def test_should_refuse_a_post_from_a_foreign_origin(server, tmp_path):
    roh = json.dumps({"url": ARTIKEL, "text": "x"}).encode()
    status, body = _anfrage(
        server,
        "POST",
        "/lesen",
        roh,
        {"Origin": "https://evil.example", "Content-Type": "application/json"},
    )
    assert status == HTTPStatus.BAD_REQUEST
    assert json.loads(body)["fehler"] == "fremde Herkunft"
    assert not (tmp_path / "lesen").exists()


def test_should_404_a_post_to_any_other_path(server):
    status, _ = _anfrage(server, "POST", "/d/x", b"{}", {"Origin": HERKUNFT})
    assert status == HTTPStatus.NOT_FOUND


# --- Browser: Knopf gegen eine Artikelseite mit COOP (chat-hub#151) ---------

ARTIKEL_COOP = "https://artikel.example/probe-151"


@pytest.fixture
def browser_seite(server, monkeypatch):
    sync_api = pytest.importorskip("playwright.sync_api")
    basis = f"http://127.0.0.1:{server.server_address[1]}"
    monkeypatch.setattr(le, "HERKUENFTE", le.HERKUENFTE | {basis})
    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as fehler:  # kein Chromium installiert
            pytest.skip(f"Chromium fehlt: {fehler}")
        kontext = browser.new_context()
        # Die Artikelseite trennt Popups ab — wie die Seite, an der der Knopf
        # am 2026-09-30 still scheiterte.
        kontext.route(
            "https://artikel.example/**",
            lambda route: route.fulfill(
                status=200,
                headers={
                    "Content-Type": "text/html; charset=utf-8",
                    "Cross-Origin-Opener-Policy": "same-origin",
                },
                body="<title>Probe 151</title><article><p>Volltext der Probe</p></article>",
            ),
        )
        yield basis, kontext
        browser.close()


def _ergebnis(seite) -> str:
    seite.wait_for_function(
        "['ok','fehler'].includes(document.getElementById('ergebnis').className)",
        timeout=10_000,
    )
    return seite.eval_on_selector("#ergebnis", "e => e.className + ': ' + e.innerText")


def test_should_store_the_article_although_the_page_cuts_the_opener(
    browser_seite, tmp_path
):
    basis, kontext = browser_seite
    artikel = kontext.new_page()
    artikel.goto(ARTIKEL_COOP)
    with kontext.expect_page() as neu:
        artikel.evaluate(le.lesezeichen(basis)[len("javascript:") :])
    lesen = neu.value
    assert _ergebnis(lesen).startswith("ok: ✓ Abgelegt: Probe 151")
    assert lesen.url == f"{basis}/lesen"  # Fragment aus Adresszeile entfernt
    ablage = tmp_path / "lesen" / f"{le.ablage_schluessel(ARTIKEL_COOP)}.md"
    assert "Volltext der Probe" in ablage.read_text(encoding="utf-8")


def test_should_report_a_knopf_call_that_lost_its_article(browser_seite, tmp_path):
    basis, kontext = browser_seite
    seite = kontext.new_page()
    seite.goto(f"{basis}/lesen?knopf=1")
    assert _ergebnis(seite).startswith("fehler: Der Knopf kam an, der Artikel nicht.")
    assert not (tmp_path / "lesen").exists()
