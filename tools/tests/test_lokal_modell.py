"""Tests fuer tools/lokal_modell.py (platform#4049 Punkt 1).

Der Endpunkt ist ein Fake-Ollama auf 127.0.0.1 in einem Thread; er haelt jede
Nutzlast fest. Geprueft wird das, was die GX10 schuetzt (num_predict, think,
keep_alive), und dass es keinen Weg nach aussen gibt: Loopback-Pflicht und
Exit 3 statt Ausweichroute, wenn das Geraet nicht antwortet.
"""

from __future__ import annotations

import json
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import lokal_modell as lm  # noqa: E402

BEISPIEL = Path(__file__).resolve().parents[1] / "lokal_modell.beispiel.json"
MODELL = "acme-modell:7b"


def _roh(**ueber) -> dict:
    roh = {k: v for k, v in json.loads(BEISPIEL.read_text(encoding="utf-8")).items() if not k.startswith("_")}
    roh.pop("tunnel", None)
    roh["modell"] = MODELL
    return roh | ueber


def _freier_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def fake_ollama():
    nutzlasten: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def _json(self, daten: dict) -> None:
            roh = json.dumps(daten).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(roh)))
            self.end_headers()
            self.wfile.write(roh)

        def do_GET(self):  # noqa: N802
            self._json({"models": [{"name": MODELL}]})

        def do_POST(self):  # noqa: N802
            nutzlasten.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            self._json({"response": "Kurzfassung.", "eval_count": 3, "total_duration": 1_000_000})

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}", nutzlasten
    server.shutdown()


def _konfig(tmp_path, monkeypatch, **ueber) -> Path:
    pfad = tmp_path / "lokal_modell.json"
    pfad.write_text(json.dumps(_roh(**ueber)), encoding="utf-8")
    monkeypatch.setenv(lm.KONFIG_ENV, str(pfad))
    return pfad


def test_should_load_example_config():
    assert lm.Konfig(_roh()).num_predict > 0


def test_should_refuse_non_loopback_endpoint():
    with pytest.raises(lm.Fehler) as e:
        lm.Konfig(_roh(basis_url="http://modell.example:11434"))
    assert e.value.code == lm.ABGELEHNT


def test_should_refuse_unbounded_num_predict():
    with pytest.raises(lm.Fehler) as e:
        lm.Konfig(_roh(num_predict=0))
    assert e.value.code == lm.ABGELEHNT


def test_should_refuse_forbidden_model():
    with pytest.raises(lm.Fehler) as e:
        lm.Konfig(_roh(modell="acme-abliterated:8b"))
    assert e.value.code == lm.ABGELEHNT


def test_should_send_bounded_payload(tmp_path, monkeypatch, capsys, fake_ollama):
    url, nutzlasten = fake_ollama
    _konfig(tmp_path, monkeypatch, basis_url=url)
    eingabe = tmp_path / "text.txt"
    eingabe.write_text("ACME Intern\nUmsatz Region Sued.\n", encoding="utf-8")
    assert lm.main(["--datei", str(eingabe), "--ohne-tunnel"]) == lm.OK
    assert capsys.readouterr().out.strip() == "Kurzfassung."
    (n,) = nutzlasten
    assert n["think"] is False and n["keep_alive"] == 0 and n["stream"] is False
    assert n["options"]["num_predict"] == _roh()["num_predict"]
    assert n["model"] == MODELL


def test_should_refuse_text_over_limit_without_call(tmp_path, monkeypatch, fake_ollama):
    url, nutzlasten = fake_ollama
    _konfig(tmp_path, monkeypatch, basis_url=url, max_zeichen=10)
    eingabe = tmp_path / "text.txt"
    eingabe.write_text("x" * 11, encoding="utf-8")
    assert lm.main(["--datei", str(eingabe), "--ohne-tunnel"]) == lm.ABGELEHNT
    assert nutzlasten == []


def test_should_fail_with_exit_3_when_device_off(tmp_path, monkeypatch, capsys):
    _konfig(tmp_path, monkeypatch, basis_url=f"http://127.0.0.1:{_freier_port()}")
    assert lm.main(["--pruefen", "--ohne-tunnel"]) == lm.NICHT_ERREICHBAR
    assert "Kein Ausweichen nach aussen" in capsys.readouterr().err


def test_should_try_only_tunnel_then_fail_without_fallback(tmp_path, monkeypatch):
    aufrufe: list[list[str]] = []

    class Lauf:
        returncode = 255

    def fake_run(befehl, **_):
        aufrufe.append(befehl)
        return Lauf()

    monkeypatch.setattr(lm.subprocess, "run", fake_run)
    port = _freier_port()
    _konfig(tmp_path, monkeypatch, basis_url=f"http://127.0.0.1:{port}",
            tunnel={"sprung": "acme-sprung", "ziel": "acme-gx10:11434"})
    assert lm.main(["--pruefen"]) == lm.NICHT_ERREICHBAR
    (befehl,) = aufrufe
    assert befehl[0] == "ssh" and f"127.0.0.1:{port}:acme-gx10:11434" in befehl


def test_should_report_missing_model(tmp_path, monkeypatch, fake_ollama):
    url, _ = fake_ollama
    _konfig(tmp_path, monkeypatch, basis_url=url, modell="acme-anderes:7b")
    assert lm.main(["--pruefen", "--ohne-tunnel"]) == lm.MODELL_FEHLT
