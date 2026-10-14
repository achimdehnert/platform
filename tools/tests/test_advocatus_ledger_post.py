"""Tests fuer tools/advocatus_ledger_post.py (KONZ-070 Z3, WP4): Validierung, Exit-Codes,
Token-Disziplin. HTTP ist durchgehend gemockt — kein Test erreicht das Ledger.
"""

from __future__ import annotations

import copy
import io
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import advocatus_ledger_post as alp  # noqa: E402
import review_risiko as rk  # noqa: E402

TOKEN = "TESTTOKEN-nie-ausgeben-0123456789"
SHA = "a" * 40


@pytest.fixture(scope="module")
def konfig() -> dict:
    return rk.lade_risiko()


def _befund(**extra) -> dict:
    b = {
        "repo": "achimdehnert/platform",
        "pr_nummer": 17,
        "head_sha": SHA,
        "regel_id": "RR-021",
        "klasse": "BLOCK",
        "locator": "docker-compose.prod.yml:42",
        "konfidenz": 0.8,
        "begruendung": "Secret per Interpolation.",
    }
    b.update(extra)
    return b


class _Antwort:
    def __init__(self, status: int):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _mock_urlopen(monkeypatch, status=201, fehler: int | None = None):
    aufrufe: list[urllib.request.Request] = []

    def fake(req, timeout=None):
        aufrufe.append(req)
        if fehler is not None:
            raise urllib.error.HTTPError(
                req.full_url, fehler, "nope", {}, io.BytesIO(b'{"detail":"geheimer body"}')
            )
        return _Antwort(status)

    monkeypatch.setattr(urllib.request, "urlopen", fake)
    return aufrufe


# ───────────────────────── Validierung ────────────────────────────────────────────────


def test_should_normalize_quelle_and_modell_from_config(konfig):
    out = alp.validiere([_befund()], konfig)
    assert out[0]["quelle"] == konfig["routine"]["quelle_ledger"]
    assert out[0]["modell"] == konfig["routine"]["modell"]
    assert "kosten_usd" not in out[0]


def test_should_accept_empty_rule_id_and_zero_costs(konfig):
    out = alp.validiere([_befund(regel_id="", kosten_usd=0)], konfig)
    assert out[0]["regel_id"] == "" and out[0]["kosten_usd"] == 0


@pytest.mark.parametrize(
    "kaputt, erwartet",
    [
        ({"klasse": "INFO"}, "klasse"),
        ({"konfidenz": 1.5}, "konfidenz"),
        ({"konfidenz": "hoch"}, "konfidenz"),
        ({"pr_nummer": 0}, "pr_nummer"),
        ({"regel_id": "XX-1"}, "regel_id"),
        ({"quelle": "bot"}, "quelle ist fest"),
        ({"head_sha": "nicht-hex"}, "head_sha"),
        ({"kosten_usd": -1}, "kosten_usd"),
        ({"locator": "x" * 513}, "locator laenger"),
        ({"fremd": 1}, "unbekannte Felder"),
    ],
)
def test_should_reject_invalid_befund(konfig, kaputt, erwartet):
    with pytest.raises(alp.BefundFehler) as exc:
        alp.validiere([_befund(**kaputt)], konfig)
    assert any(erwartet in f for f in exc.value.fehler)


def test_should_reject_missing_required_field_and_non_list(konfig):
    b = _befund()
    del b["begruendung"]
    with pytest.raises(alp.BefundFehler) as exc:
        alp.validiere([b], konfig)
    assert any("Pflichtfeld fehlt: begruendung" in f for f in exc.value.fehler)
    with pytest.raises(alp.BefundFehler):
        alp.validiere({"repo": "x"}, konfig)


# ───────────────────────── CLI und HTTP ──────────────────────────────────────────────


def _datei(tmp_path, befunde) -> str:
    p = tmp_path / "befunde.json"
    p.write_text(json.dumps(befunde), encoding="utf-8")
    return str(p)


def test_should_dry_run_without_token_and_never_print_it(tmp_path, monkeypatch, capsys, konfig):
    monkeypatch.setenv(konfig["routine"]["token_env"], TOKEN)
    aufrufe = _mock_urlopen(monkeypatch)
    rc = alp.main([_datei(tmp_path, [_befund()]), "--dry-run"])
    aus = capsys.readouterr()
    assert rc == alp.RC_OK and aufrufe == []
    assert "DRY-RUN" in aus.out and '"quelle": "advocatus"' in aus.out
    assert TOKEN not in aus.out + aus.err


def test_should_exit_two_without_token(tmp_path, monkeypatch, capsys, konfig):
    monkeypatch.delenv(konfig["routine"]["token_env"], raising=False)
    aufrufe = _mock_urlopen(monkeypatch)
    rc = alp.main([_datei(tmp_path, [_befund()])])
    assert rc == alp.RC_KEIN_TOKEN and aufrufe == []
    assert konfig["routine"]["token_env"] in capsys.readouterr().err


def test_should_post_bulk_with_token_header_and_exit_zero(tmp_path, monkeypatch, capsys, konfig):
    monkeypatch.setenv(konfig["routine"]["token_env"], TOKEN)
    aufrufe = _mock_urlopen(monkeypatch, status=201)
    rc = alp.main([_datei(tmp_path, [_befund(), _befund(locator="b:1")])])
    assert rc == alp.RC_OK and len(aufrufe) == 1
    req = aufrufe[0]
    assert req.full_url == konfig["routine"]["ledger_url"] and req.get_method() == "POST"
    assert req.get_header("Authorization") == f"Token {TOKEN}"
    # Cloudflare blockt die urllib-Standardkennung mit 403 — eigene Kennung ist Pflicht.
    assert req.get_header("User-agent") == alp.USER_AGENT and "urllib" not in alp.USER_AGENT
    body = json.loads(req.data.decode("utf-8"))
    assert isinstance(body, list) and len(body) == 2 and body[0]["quelle"] == "advocatus"
    assert TOKEN not in "".join(capsys.readouterr())


def test_should_exit_one_on_http_error_without_leaking_body(tmp_path, monkeypatch, capsys, konfig):
    monkeypatch.setenv(konfig["routine"]["token_env"], TOKEN)
    _mock_urlopen(monkeypatch, fehler=403)
    rc = alp.main([_datei(tmp_path, [_befund()])])
    aus = capsys.readouterr()
    assert rc == alp.RC_FEHLER
    assert "403" in aus.err and "geheimer body" not in aus.err and TOKEN not in aus.err


def test_should_report_reachable_on_probe_even_for_http_error(monkeypatch, capsys, konfig):
    monkeypatch.setenv(konfig["routine"]["token_env"], TOKEN)
    aufrufe = _mock_urlopen(monkeypatch, fehler=401)
    rc = alp.main(["--probe"])
    aus = capsys.readouterr()
    assert rc == alp.RC_OK
    assert aus.out.startswith(alp.PROBE_PRAEFIX) and "erreichbar, HTTP 401, mit Token" in aus.out
    assert aufrufe[0].get_header("User-agent") == alp.USER_AGENT
    assert len(aufrufe) == 1 and aufrufe[0].get_method() == "GET" and aufrufe[0].data is None
    assert aufrufe[0].get_header("Authorization") == f"Token {TOKEN}"
    assert TOKEN not in aus.out + aus.err and "geheimer body" not in aus.out + aus.err


def test_should_report_unreachable_on_probe_connection_error(monkeypatch, capsys, konfig):
    monkeypatch.delenv(konfig["routine"]["token_env"], raising=False)

    def fake(req, timeout=None):
        raise urllib.error.URLError("Tunnel connection failed: 403 Forbidden")

    monkeypatch.setattr(urllib.request, "urlopen", fake)
    rc = alp.main(["--probe"])
    aus = capsys.readouterr().out
    assert rc == alp.RC_FEHLER
    assert aus.startswith(alp.PROBE_PRAEFIX) and "nicht erreichbar" in aus
    assert "Tunnel connection failed" in aus and "ohne Token" in aus


def test_should_require_either_file_or_probe(monkeypatch, konfig):
    aufrufe = _mock_urlopen(monkeypatch)
    with pytest.raises(SystemExit):
        alp.main([])
    with pytest.raises(SystemExit):
        alp.main(["--probe", "irgendwas.json"])
    assert aufrufe == []


def test_should_exit_one_on_unexpected_status(tmp_path, monkeypatch, capsys, konfig):
    monkeypatch.setenv(konfig["routine"]["token_env"], TOKEN)
    _mock_urlopen(monkeypatch, status=204)
    assert alp.main([_datei(tmp_path, [_befund()])]) == alp.RC_FEHLER
    assert "204" in capsys.readouterr().err


def test_should_exit_one_on_invalid_befund_without_posting(tmp_path, monkeypatch, capsys, konfig):
    monkeypatch.setenv(konfig["routine"]["token_env"], TOKEN)
    aufrufe = _mock_urlopen(monkeypatch)
    rc = alp.main([_datei(tmp_path, [_befund(klasse="INFO")])])
    assert rc == alp.RC_FEHLER and aufrufe == []
    assert "BEFUND" in capsys.readouterr().err


def test_should_skip_post_for_empty_list(tmp_path, monkeypatch, capsys, konfig):
    monkeypatch.delenv(konfig["routine"]["token_env"], raising=False)
    aufrufe = _mock_urlopen(monkeypatch)
    assert alp.main([_datei(tmp_path, [])]) == alp.RC_OK
    assert aufrufe == [] and "leere" in capsys.readouterr().out


def test_should_chunk_by_bulk_max(monkeypatch, konfig):
    klein = copy.deepcopy(konfig)
    klein["routine"]["ledger_bulk_max"] = 2
    aufrufe = _mock_urlopen(monkeypatch, status=200)
    befunde = alp.validiere([_befund(locator=f"x:{i}") for i in range(5)], klein)
    assert alp.poste(befunde, klein, TOKEN) == [200, 200, 200]
    assert [len(json.loads(r.data)) for r in aufrufe] == [2, 2, 1]
