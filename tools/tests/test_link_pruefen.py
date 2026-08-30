"""Tests fuer tools/mail_agent/link_pruefen.py.

Warum es diese Datei gibt: das Werkzeug entstand am 2026-08-25 als Antwort auf
einen getippten, dreifach falschen Link — und ging ohne einen einzigen Test auf
`main`. Die Retro desselben Tages fuehrt das als Befund
(`untested-tool-module-green-gate`, 8. Vorkommen ueber alle Retros): ein
Werkzeug, das eine Regel durchsetzen soll, ist ohne Test und ohne Aufrufer ein
Entwurf, kein Gate.

Jeder Test hier hat eine Gegenprobe. Ein Pruefer, der nur bestaetigt, dass er
bei gesundem Bestand schweigt, belegt nicht, dass er bei krankem anschlaegt.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

WERKZEUG = Path(__file__).resolve().parents[1] / "mail_agent" / "link_pruefen.py"


def _modul():
    spec = importlib.util.spec_from_file_location("link_pruefen", WERKZEUG)
    modul = importlib.util.module_from_spec(spec)
    sys.modules["link_pruefen"] = modul
    spec.loader.exec_module(modul)
    return modul


lp = _modul()


# --------------------------------------------------------------------------
# urls_aus — die beiden gemessenen Fehlalarme
# --------------------------------------------------------------------------


def test_should_keep_trailing_dot_inside_markdown_link():
    """Der Punkt gehoert zur URL, nicht zum Satz.

    Realfall: `[Termin 28.08.](https://todo.iil.pet/t/Termin%2028.08.)`. Eine
    rstrip-Heuristik schnitt den Punkt ab, prueft damit eine ANDERE URL als die
    im Text und meldete 404 fuer einen gesunden Link.
    """
    text = "siehe [Termin 28.08.](https://todo.iil.pet/t/Termin%2028.08.) im Board"
    assert lp.urls_aus(text) == ["https://todo.iil.pet/t/Termin%2028.08."]


def test_should_still_strip_sentence_punctuation_from_bare_url():
    """Gegenprobe zum vorigen Test: ausserhalb der Klammerform wird gestrippt."""
    assert lp.urls_aus("offen unter https://mail.iil.pet/i/abc.") == [
        "https://mail.iil.pet/i/abc"
    ]


def test_should_ignore_urls_inside_code_spans():
    """Schablonen in Backticks sind Doku, keine Adressen."""
    assert lp.urls_aus("die Route `https://mail.iil.pet/m/hnu/` erklaert das") == []


def test_should_ignore_placeholder_urls_with_angle_brackets():
    assert lp.urls_aus("Form: https://mail.iil.pet/i/<kurz-id> nutzen") == []


def test_should_find_the_real_link_next_to_a_placeholder():
    """Gegenprobe: die Schablonen-Regel darf echte Links nicht mitverschlucken."""
    text = "Form: https://mail.iil.pet/i/<kurz-id> — konkret https://mail.iil.pet/i/abc"
    assert lp.urls_aus(text) == ["https://mail.iil.pet/i/abc"]


# --------------------------------------------------------------------------
# ingress_karte — Hostname zu Loopback-Port
# --------------------------------------------------------------------------


def _ingress(tmp_path: Path, inhalt: str) -> Path:
    d = tmp_path / "cloudflared"
    d.mkdir()
    (d / "tunnel.yml").write_text(inhalt, encoding="utf-8")
    return d


def test_should_map_hostname_to_its_loopback_service(tmp_path):
    d = _ingress(
        tmp_path,
        "ingress:\n"
        "  - hostname: mail.example.test\n"
        "    service: http://127.0.0.1:8787\n"
        "  - hostname: todo.example.test\n"
        "    service: http://127.0.0.1:8789\n",
    )
    karte = lp.ingress_karte([d])
    assert karte["mail.example.test"] == "http://127.0.0.1:8787"
    assert karte["todo.example.test"] == "http://127.0.0.1:8789"


def test_should_skip_non_loopback_services(tmp_path):
    """Nur Loopback ist von hier aus ohne Access pruefbar."""
    d = _ingress(
        tmp_path,
        "ingress:\n  - hostname: extern.example.test\n    service: https://10.0.0.5\n",
    )
    assert lp.ingress_karte([d]) == {}


def test_should_return_empty_map_when_no_config_dir_exists(tmp_path):
    assert lp.ingress_karte([tmp_path / "gibtsnicht"]) == {}


# --------------------------------------------------------------------------
# pruefe — die drei Ausgaenge
# --------------------------------------------------------------------------


class _Antwort:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


@pytest.fixture
def karte():
    return {"mail.example.test": "http://127.0.0.1:8787"}


def test_should_report_ok_on_200(monkeypatch, karte):
    monkeypatch.setattr(lp.urllib.request, "urlopen", lambda *a, **k: _Antwort(200))
    status, _ = lp.pruefe("https://mail.example.test/m/hnu/inbox/1", karte)
    assert status == "ok"


def test_should_report_error_on_404(monkeypatch, karte):
    import urllib.error

    def wirft(*_a, **_k):
        raise urllib.error.HTTPError("u", 404, "nope", None, None)

    monkeypatch.setattr(lp.urllib.request, "urlopen", wirft)
    status, hinweis = lp.pruefe("https://mail.example.test/m/hnu/1", karte)
    assert status == "fehler"
    assert "404" in hinweis


def test_should_report_skipped_for_host_without_loopback_service(karte):
    """Ein unbekannter Host ist NICHT geprueft — das ist der Standardfall,
    der seit der Retro vom 2026-08-25 als Fehler zaehlt (siehe main())."""
    status, _ = lp.pruefe("https://github.com/x/y", karte)
    assert status == "uebersprungen"


# --------------------------------------------------------------------------
# main — Exit-Code: das eigentliche Versprechen des Werkzeugs
# --------------------------------------------------------------------------


def _lauf(monkeypatch, argv, karte, urlopen):
    monkeypatch.setattr(sys, "argv", ["link_pruefen.py", *argv])
    monkeypatch.setattr(lp, "ingress_karte", lambda *_a, **_k: karte)
    monkeypatch.setattr(lp.urllib.request, "urlopen", urlopen)
    return lp.main()


def test_should_exit_nonzero_for_unknown_host_by_default(monkeypatch, karte):
    """Der Kern des Befunds: ein erfundener Hostname darf NICHT durchgehen.

    Vor der Retro-Massnahme war `--streng` optional und die dokumentierte
    Aufrufform nutzte es nicht — ein Link auf einem beliebigen Fantasie-Host
    ergab Exit 0, ohne je geprueft worden zu sein.
    """
    assert _lauf(monkeypatch, ["https://erfunden.test/x"], karte, None) == 1


def test_should_exit_zero_for_unknown_host_when_nachsichtig(monkeypatch, karte):
    """Gegenprobe: die Ausnahme muss weiterhin erreichbar sein."""
    assert _lauf(monkeypatch, ["--nachsichtig", "https://erfunden.test/x"], karte, None) == 0


def test_should_exit_zero_when_every_link_answers_200(monkeypatch, karte):
    assert (
        _lauf(
            monkeypatch,
            ["https://mail.example.test/m/hnu/inbox/1"],
            karte,
            lambda *a, **k: _Antwort(200),
        )
        == 0
    )


def test_should_exit_nonzero_when_ingress_list_is_missing(monkeypatch):
    """Ohne Ingress-Liste ist kein Hostname aufloesbar — fail-closed."""
    assert _lauf(monkeypatch, ["https://mail.example.test/x"], {}, None) == 1
