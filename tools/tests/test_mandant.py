"""Tests für tools/sevdesk/mandant.py — Mandanten-Umschaltung (K8, platform#3102).

Alle Pfade zeigen auf ``tmp_path`` — es wird NIE die reale ``~/.secrets``-Datei
gelesen oder ihr Inhalt ausgegeben.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sevdesk"))

import mandant  # noqa: E402


@pytest.fixture()
def secret_dateien(tmp_path, monkeypatch):
    pfade = {
        "iil": tmp_path / "sevdesk_api_token",
        "edv": tmp_path / "sevdesk_dehnert_edv_api_token",
    }
    monkeypatch.setattr(mandant, "SECRET_DATEIEN", pfade)
    return pfade


# ── mandant_argument: Default und Umgebungsvariable ───────────────────────


def test_should_default_mandant_to_iil_without_env_or_flag(monkeypatch):
    monkeypatch.delenv("SEVDESK_MANDANT", raising=False)
    p = argparse.ArgumentParser()
    mandant.mandant_argument(p)
    args = p.parse_args([])
    assert args.mandant == "iil"


def test_should_read_default_mandant_from_environment_variable(monkeypatch):
    monkeypatch.setenv("SEVDESK_MANDANT", "edv")
    p = argparse.ArgumentParser()
    mandant.mandant_argument(p)
    args = p.parse_args([])
    assert args.mandant == "edv"


def test_should_let_explicit_flag_override_environment_variable(monkeypatch):
    monkeypatch.setenv("SEVDESK_MANDANT", "edv")
    p = argparse.ArgumentParser()
    mandant.mandant_argument(p)
    args = p.parse_args(["--mandant", "iil"])
    assert args.mandant == "iil"


# ── token_lesen: Format, fehlende Datei ────────────────────────────────────


def test_should_extract_value_after_equals_sign(secret_dateien):
    secret_dateien["iil"].write_text(
        "SEVDESK_TOKEN=platzhalter-synthetisch\n", encoding="utf-8"
    )
    assert mandant.token_lesen("iil") == "platzhalter-synthetisch"


def test_should_use_raw_line_when_no_equals_sign_present(secret_dateien):
    secret_dateien["edv"].write_text("platzhalter-synthetisch", encoding="utf-8")
    assert mandant.token_lesen("edv") == "platzhalter-synthetisch"


def test_should_exit_3_with_expected_path_when_secret_file_missing(
    secret_dateien, capsys
):
    with pytest.raises(SystemExit) as exc:
        mandant.token_lesen("edv")
    assert exc.value.code == 3
    ausgabe = capsys.readouterr().out
    assert str(secret_dateien["edv"]) in ausgabe


def test_should_not_print_any_value_when_secret_file_missing(secret_dateien, capsys):
    """Die Meldung nennt den Pfad — nie einen Wert (auch keinen vorherigen Inhalt)."""
    with pytest.raises(SystemExit):
        mandant.token_lesen("edv")
    ausgabe = capsys.readouterr().out
    assert "SEVDESK_TOKEN" not in ausgabe
    assert "platzhalter" not in ausgabe


def test_should_exit_with_message_for_unknown_mandant(secret_dateien, capsys):
    with pytest.raises(SystemExit) as exc:
        mandant.secret_datei("unbekannt")
    assert exc.value.code == 3
    ausgabe = capsys.readouterr().out
    assert "unbekannt" in ausgabe


def test_should_build_client_with_authorization_header_from_resolved_mandant(
    secret_dateien,
):
    secret_dateien["iil"].write_text("KEY=abc123\n", encoding="utf-8")
    c = mandant.client("iil")
    try:
        assert c.headers["Authorization"] == "abc123"
        assert str(c.base_url).rstrip("/") == mandant.API
    finally:
        c.close()
