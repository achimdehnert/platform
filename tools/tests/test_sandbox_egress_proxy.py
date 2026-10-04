"""Tests fuer tools/sandbox/egress_proxy.py (platform#3685) — nur lokale Sockets."""

from __future__ import annotations

import importlib.util
import socket
import sys
import threading
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "sandbox" / "egress_proxy.py"
_spec = importlib.util.spec_from_file_location("egress_proxy", _SCRIPT)
ep = importlib.util.module_from_spec(_spec)
sys.modules["egress_proxy"] = ep
_spec.loader.exec_module(ep)


def test_should_allow_only_model_api_and_github_on_port_443():
    assert ep.ziel_erlaubt("api.anthropic.com", 443)
    assert ep.ziel_erlaubt("API.GitHub.com.", 443)
    assert not ep.ziel_erlaubt("api.anthropic.com", 80)
    assert not ep.ziel_erlaubt("example.com", 443)
    assert not ep.ziel_erlaubt("evil.github.com", 443)
    assert not ep.ziel_erlaubt("github.com.evil.example", 443)
    assert not ep.ziel_erlaubt("140.82.121.6", 443)


def test_should_parse_connect_targets_and_reject_garbage():
    assert ep.zerlege_ziel("api.github.com:443") == ("api.github.com", 443)
    assert ep.zerlege_ziel("[::1]:443") == ("::1", 443)
    assert ep.zerlege_ziel("api.github.com") is None
    assert ep.zerlege_ziel(":443") is None


def _echo_server() -> socket.socket:
    server = socket.create_server(("127.0.0.1", 0))

    def bedienen():
        verbindung, _ = server.accept()
        with verbindung:
            verbindung.sendall(verbindung.recv(1024))

    threading.Thread(target=bedienen, daemon=True).start()
    return server


def _anfrage(port: int, zeile: bytes) -> socket.socket:
    s = socket.create_connection(("127.0.0.1", port), timeout=5)
    s.sendall(zeile + b"\r\nHost: x\r\n\r\n")
    return s


def test_should_tunnel_allowed_target_and_refuse_everything_else(capsys):
    echo = _echo_server()
    echo_port = echo.getsockname()[1]
    proxy = ep.starte(("127.0.0.1", 0), erlaubt=frozenset({"127.0.0.1"}))
    port = proxy.getsockname()[1]
    try:
        # Port != 443 ist auch fuer ein erlaubtes Ziel gesperrt …
        with _anfrage(port, f"CONNECT 127.0.0.1:{echo_port} HTTP/1.1".encode()) as s:
            assert s.recv(64).startswith(b"HTTP/1.1 403")
        # … ebenso Klartext-HTTP und unbekannte Ziele.
        with _anfrage(port, b"GET http://example.com/ HTTP/1.1") as s:
            assert s.recv(64).startswith(b"HTTP/1.1 403")
        with _anfrage(port, b"CONNECT example.com:443 HTTP/1.1") as s:
            assert s.recv(64).startswith(b"HTTP/1.1 403")
        # Gegenprobe: mit freigegebenem Port wird getunnelt und Daten kommen zurueck.
        ep.ERLAUBTER_PORT, alt = echo_port, ep.ERLAUBTER_PORT
        try:
            with _anfrage(
                port, f"CONNECT 127.0.0.1:{echo_port} HTTP/1.1".encode()
            ) as s:
                assert s.recv(64).startswith(b"HTTP/1.1 200")
                s.sendall(b"hallo")
                assert s.recv(64) == b"hallo"
        finally:
            ep.ERLAUBTER_PORT = alt
    finally:
        proxy.close()
        echo.close()
    protokoll = capsys.readouterr().out
    assert protokoll.count('"verweigert"') == 3
    assert protokoll.count('"erlaubt"') == 1
