"""Was `tools/umgebung.py` verspricht, muss es auch halten.

Das Werkzeug entstand aus vier Fehlschluessen einer einzigen Sitzung (2026-08-30),
die alle dieselbe Form hatten: eine Aussage ueber die Umgebung, die nie gemessen
wurde, weil sie zu selbstverstaendlich schien.

- Die Sitzung hielt ihre Maschine fuer einen Entwicklungsrechner. Sie stand auf
  dem Staging-Host.
- »Kein Staging vorhanden« — geprueft waren zwei von acht Hosts, und `docker ps`
  zeigt nur Laufendes.
- »Der Name zeigt auf writing-hub« — er loeste auf, lieferte 200 und eine FREMDE
  Anwendung.
- »Access bietet E-Mail-Login« — das Wort stand in einer OAuth-URL.

Die Tests hier sichern die drei Zusagen, die daraus folgen: der Titel entscheidet
(nicht der Statuscode), ein Alias ist moeglich (nicht jedes Produkt heisst wie sein
Repo), und eine Auth-Wand ist eine LUECKE, kein Befund.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from umgebung import PLATFORM, _hinweis, _marker, wo_bin_ich  # noqa: E402


# ── Der Titel entscheidet, nicht der Statuscode ─────────────────────────


def test_should_stay_silent_when_the_title_confirms_the_repo():
    assert _hinweis("writing-hub", {}, "200", "Login — Writing Hub") == ""


def test_should_warn_when_a_200_serves_a_foreign_application():
    """Der Kernfall: der Name antwortet, aber mit etwas anderem.

    Genau so sah `staging-writing.iil.pet` aus — 200, sauber, und dahinter
    »Sozialimmobilie im Unterallgaeu«.
    """
    hinweis = _hinweis("writing-hub", {}, "200", "Sozialimmobilie im Unterallgäu")
    assert "nachsehen" in hinweis, "Eine fremde Anwendung hinter 200 bleibt unbemerkt"


def test_should_not_judge_a_non_200():
    """Ein 302 oder 500 ist Sache des Erreichbarkeits-Melders, nicht dieses Hinweises."""
    assert _hinweis("writing-hub", {}, "302", "(Fehlerseite)") == ""
    assert _hinweis("writing-hub", {}, "n/a", "(URLError)") == ""


def test_should_call_an_auth_wall_a_gap_not_a_finding():
    """Hinter einer Access-Wand ist von hier NICHTS pruefbar — das ist zu sagen,
    nicht als Fehler zu buchen."""
    hinweis = _hinweis("writing-hub", {}, "200", "Sign in ・ Cloudflare Access")
    assert "nicht pruefbar" in hinweis
    assert "nachsehen" not in hinweis, "Eine Auth-Wand ist kein Repo-Fehlbefund"


# ── Nicht jedes Produkt heisst wie sein Repo ────────────────────────────


def test_should_accept_a_declared_title_marker():
    """`weltenhub` liegt unter `weltenforger.com`. Ohne Alias waere das ein
    Fehlalarm — und ein Werkzeug, das falsch anschlaegt, wird ignoriert."""
    assert _marker("weltenhub", {"titel_marker": "weltenforger"}) == ["weltenforger"]
    assert _hinweis("weltenhub", {"titel_marker": "weltenforger"}, "200", "Weltenforger — Welten") == ""


def test_should_fall_back_to_the_repo_name_without_a_marker():
    marker = _marker("research-hub", {})
    assert "research" in marker


# ── Wo stehe ich ────────────────────────────────────────────────────────


def test_should_name_the_host_when_the_ip_matches(monkeypatch):
    import umgebung

    monkeypatch.setattr(umgebung, "eigene_ip", lambda: "88.99.38.75")
    name, warum = wo_bin_ich({"hosts": {"staging": {"ip": "88.99.38.75"}, "prod": {"ip": "1.2.3.4"}}})
    assert name == "staging"
    assert "88.99.38.75" in warum


def test_should_admit_when_the_machine_is_not_in_the_registry(monkeypatch):
    """Ein unbekannter Host ist zu sagen — nicht auf den erstbesten zu raten."""
    import umgebung

    monkeypatch.setattr(umgebung, "eigene_ip", lambda: "10.0.0.9")
    name, warum = wo_bin_ich({"hosts": {"prod": {"ip": "1.2.3.4"}}})
    assert name == ""
    assert "keinem hosts.yaml-Eintrag" in warum


def test_should_admit_when_the_ip_cannot_be_determined(monkeypatch):
    import umgebung

    monkeypatch.setattr(umgebung, "eigene_ip", lambda: "")
    name, warum = wo_bin_ich({"hosts": {"prod": {"ip": "1.2.3.4"}}})
    assert name == ""
    assert "nicht ermittelbar" in warum


# ── Regression: das Werkzeug muss dort lesen, wo es liegt ───────────────


def test_should_read_the_declarations_from_its_own_checkout():
    """Ein fest verdrahteter Pfad las in einem Worktree still die Datei des
    Hauptbaums — das Werkzeug sah woanders hin als sein Aufrufer und meldete eine
    Aenderung als wirkungslos, die es gar nicht gelesen hatte. Dieselbe Klasse,
    gegen die es gebaut ist."""
    # Diese Datei liegt in tools/tests/ — bis zur Repo-Wurzel sind es DREI
    # Ebenen, nicht zwei. Der erste Anlauf zaehlte eine zu wenig und liess den
    # Test scheitern, obwohl das Werkzeug richtig lag.
    hier = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assert PLATFORM == hier, f"liest aus {PLATFORM}, liegt aber in {hier}"
    assert os.path.exists(os.path.join(PLATFORM, "infra", "ports.yaml"))
