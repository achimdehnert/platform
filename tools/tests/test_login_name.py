"""Tests für send_mail.login_name — Anmeldename getrennt von der Absenderadresse.

Anlass (2026-07-29): `MAIL_FROM` diente beidem zugleich. Beim HNU-Postfach ist der
Anmeldename ein blosser Benutzername, also stand genau der als Absender im
Entwurf — keine gültige Adresse. Wer die Adresse eintrug, fand kein Zugangspaar
mehr und kam gar nicht erst hinein.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mail_agent"))

sm = pytest.importorskip("send_mail")


class TestLoginName:
    def test_should_use_mail_login_when_present(self):
        cfg = {"MAIL_FROM": "Achim.Dehnert@hnu.de", "MAIL_LOGIN": "dehnert"}
        assert sm.login_name(cfg) == "dehnert"

    def test_should_fall_back_to_mail_from(self):
        """Bestehende Konfigurationen ohne MAIL_LOGIN verhalten sich unverändert."""
        assert sm.login_name({"MAIL_FROM": "ad@dehnert.team"}) == "ad@dehnert.team"

    def test_should_ignore_empty_mail_login(self):
        cfg = {"MAIL_FROM": "ad@dehnert.team", "MAIL_LOGIN": ""}
        assert sm.login_name(cfg) == "ad@dehnert.team"

    def test_should_raise_without_any_identity(self):
        with pytest.raises(KeyError):
            sm.login_name({"SMTP_HOST": "mail.example.org"})


class TestZusammenspielMitCredentials:
    """Der eigentliche Punkt: Anmeldung gelingt, während der Absender eine
    Adresse bleibt, die in der Zugangsdatei gar nicht vorkommt."""

    @pytest.fixture
    def creds(self, tmp_path):
        pfad = tmp_path / "creds.env"
        pfad.write_text("user=dehnert\npassword=geheim\n", encoding="utf-8")
        return pfad

    def test_should_authenticate_with_login_not_sender(self, creds):
        cfg = {"MAIL_FROM": "Achim.Dehnert@hnu.de", "MAIL_LOGIN": "dehnert"}
        user, password = sm.load_credentials(creds, sm.login_name(cfg))
        assert user == "dehnert"
        assert password == "geheim"

    def test_should_still_fail_for_an_unknown_login(self, creds):
        with pytest.raises(SystemExit):
            sm.load_credentials(creds, "Achim.Dehnert@hnu.de")

    def test_should_keep_last_pair_on_rotation(self, tmp_path):
        """Vorhandenes Verhalten darf sich nicht ändern: bei zwei Paaren mit
        gleichem Benutzer gewinnt das letzte (Rotation hängt unten an)."""
        pfad = tmp_path / "creds.env"
        pfad.write_text(
            "user=dehnert\npassword=alt\nuser=dehnert\npassword=neu\n", encoding="utf-8"
        )
        assert sm.load_credentials(pfad, "dehnert") == ("dehnert", "neu")
