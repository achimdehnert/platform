"""Tests für tools/cf_access — die netzfreien Teile.

Die API-Aufrufe selbst bleiben Dogfood (wie bei den Mail-Werkzeugen): geprüft
wird, was ohne Cloudflare-Konto entscheidbar ist — Zonenableitung und die
Pflichtfeld-Abbrüche. Beides ist genau die Stelle, an der ein Skript still das
Falsche tun könnte, statt laut abzubrechen.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "cf_access" / "_cf.py"
_spec = importlib.util.spec_from_file_location("cf_helfer", _SRC)
cf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cf)


class TestZonenableitung:
    def test_should_derive_zone_from_subdomain(self):
        assert cf.zone_name("mail.iil.pet") == "iil.pet"

    def test_should_keep_apex_domain(self):
        assert cf.zone_name("iil.pet") == "iil.pet"

    def test_should_ignore_trailing_dot(self):
        assert cf.zone_name("mail.iil.pet.") == "iil.pet"

    def test_should_take_last_two_labels_of_deep_host(self):
        assert cf.zone_name("a.b.c.iil.pet") == "iil.pet"


class TestPflichtfelder:
    def test_should_exit_when_env_missing(self, monkeypatch):
        """Ein fehlender Hostname darf nicht als leerer String durchlaufen."""
        monkeypatch.delenv("HOST", raising=False)
        with pytest.raises(SystemExit) as fehler:
            cf.umgebung("HOST")
        assert "HOST" in str(fehler.value)

    def test_should_exit_when_env_is_blank(self, monkeypatch):
        monkeypatch.setenv("HOST", "   ")
        with pytest.raises(SystemExit):
            cf.umgebung("HOST")

    def test_should_return_values_in_order(self, monkeypatch):
        monkeypatch.setenv("HOST", "mail.iil.pet")
        monkeypatch.setenv("PORT", "8787")
        assert cf.umgebung("HOST", "PORT") == ["mail.iil.pet", "8787"]


class TestTokenDatei:
    def test_should_name_the_write_token_file(self):
        """Das kleinere cloudflare_api_token kann kein DNS (403) — Datei fest verdrahtet."""
        assert cf.TOKEN_DATEI.name == "cloudflare_write_token"

    def test_should_exit_when_token_file_missing(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cf, "TOKEN_DATEI", tmp_path / "gibtsnicht")
        with pytest.raises(SystemExit):
            cf.token()

    def test_should_exit_when_token_file_empty(self, monkeypatch, tmp_path):
        leer = tmp_path / "leer"
        leer.write_text("\n")
        monkeypatch.setattr(cf, "TOKEN_DATEI", leer)
        with pytest.raises(SystemExit):
            cf.token()


class TestUrsprungPruefung:
    """Retro-Befund 2026-09-02: ein gesetzter ORIGIN wanderte ungeprueft in die
    Tunnel-Config, und die Kette dahinter kann den Fehler nicht sehen —
    `veroeffentlichen.sh` wertet jedes `nicht 200` als Erfolg und haelt ein 502
    durch einen kaputten Ursprung fuer die erwartete Access-Abweisung.
    """

    def test_should_accept_host_and_port(self):
        assert cf.pruefe_origin("10.99.0.2:11434") == "10.99.0.2:11434"

    def test_should_accept_a_hostname(self):
        assert cf.pruefe_origin("gpu-box.intern:8080") == "gpu-box.intern:8080"

    def test_should_accept_bracketed_ipv6(self):
        assert cf.pruefe_origin("[fd00::1]:8080") == "[fd00::1]:8080"

    def test_should_strip_surrounding_whitespace(self):
        assert cf.pruefe_origin("  127.0.0.1:8787  ") == "127.0.0.1:8787"

    def test_should_reject_a_scheme_prefix(self):
        """Der reale Fehlgriff: das Werkzeug setzt `http://` selbst davor."""
        with pytest.raises(SystemExit) as fehler:
            cf.pruefe_origin("http://10.99.0.2:11434")
        assert "Schema" in str(fehler.value)

    def test_should_reject_a_path(self):
        with pytest.raises(SystemExit) as fehler:
            cf.pruefe_origin("10.99.0.2:11434/api")
        assert "Pfad" in str(fehler.value)

    def test_should_reject_a_missing_port(self):
        with pytest.raises(SystemExit):
            cf.pruefe_origin("10.99.0.2")

    def test_should_reject_an_empty_value(self):
        with pytest.raises(SystemExit) as fehler:
            cf.pruefe_origin("   ")
        assert "leer" in str(fehler.value)

    def test_should_reject_a_port_above_the_range(self):
        with pytest.raises(SystemExit) as fehler:
            cf.pruefe_origin("10.99.0.2:99999")
        assert "65535" in str(fehler.value)

    def test_should_reject_a_non_numeric_port(self):
        """Faengt nebenbei ein kaputtes PORT im Default `127.0.0.1:{port}` ab."""
        with pytest.raises(SystemExit):
            cf.pruefe_origin("127.0.0.1:abc")
