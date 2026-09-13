"""Tests fuer tools/secrets_pruefen.py (V4).

Anlass: eine Secret-Datei ohne ``NAME=WERT``-Form wurde per ``. datei``
gesourced und der nackte Wert dabei als Kommando ausgefuehrt — die Shell
schrieb ihn in die eigene Fehlermeldung. Der bestehende Leak-Guard (argument-
basiert: cat/head/tail/grep mit Secret-Datei als Argument) haette das nicht
gefangen. Dieses Werkzeug ersetzt das Sourcen; die Tests unten pruefen vor
allem EINE Eigenschaft haerter als alle anderen: der Wert selbst darf an
KEINER Ausgabe-Stelle auftauchen, auch nicht als Teilstring.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import secrets_pruefen as sp  # noqa: E402


def schreib(basis: Path, name: str, inhalt: str) -> Path:
    p = basis / name
    p.write_text(inhalt, encoding="utf-8")
    return p


# --- erkenne_form(): Form-Erkennung -----------------------------------------


def test_should_detect_kv_form_when_every_line_is_name_equals_value():
    form, werte = sp.erkenne_form("A=1\nB=2\n# Kommentar\n\n")

    assert form == "kv"
    assert werte == [("A", "1"), ("B", "2")]


def test_should_detect_bare_form_when_single_line_without_equals():
    form, werte = sp.erkenne_form("ghp_geheimerwert\n")

    assert form == "bare"
    assert werte == [(None, "ghp_geheimerwert")]


def test_should_detect_gemischt_form_when_kv_and_bare_lines_mix():
    form, _ = sp.erkenne_form("A=1\nnackter-wert\n")

    assert form == "gemischt"


def test_should_detect_gemischt_form_when_multiple_bare_lines():
    form, _ = sp.erkenne_form("erste-zeile\nzweite-zeile\n")

    assert form == "gemischt"


def test_should_ignore_comments_and_blank_lines_for_form_detection():
    form, werte = sp.erkenne_form("\n# Kommentar\nA=1\n\n")

    assert form == "kv"
    assert werte == [("A", "1")]


# --- --datei: Hash-Ausgabe zeigt nie den Wert --------------------------------


def test_should_never_print_the_value_for_a_bare_file(tmp_path, capsys):
    geheim = "sk-super-geheimer-wert-xyz"
    schreib(tmp_path, "bare-secret", geheim + "\n")

    rc = sp.main(["--datei", "bare-secret", "--basis", str(tmp_path)])

    out = capsys.readouterr().out
    assert rc == 0
    assert geheim not in out
    assert "<bare>" in out
    assert f"len={len(geheim)}" in out


def test_should_never_print_the_value_for_a_kv_file(tmp_path, capsys):
    geheim = "wert-der-nie-erscheinen-darf"
    schreib(tmp_path, "kv-secret", f"CLOUDFLARE_API_TOKEN={geheim}\n")

    rc = sp.main(["--datei", "kv-secret", "--basis", str(tmp_path)])

    out = capsys.readouterr().out
    assert rc == 0
    assert geheim not in out
    assert "CLOUDFLARE_API_TOKEN" in out


def test_should_report_form_kv_for_a_datei_call(tmp_path, capsys):
    schreib(tmp_path, "kv-secret", "A=1\nB=2\n")

    sp.main(["--datei", "kv-secret", "--basis", str(tmp_path)])

    out = capsys.readouterr().out
    assert "form=kv" in out


# --- Pfad-Traversal -----------------------------------------------------------


def test_should_reject_filename_with_slash(tmp_path, capsys):
    rc = sp.main(["--datei", "../oben/x", "--basis", str(tmp_path)])

    assert rc == 2


def test_should_reject_filename_with_forward_slash(tmp_path):
    rc = sp.main(["--datei", "unter/pfad", "--basis", str(tmp_path)])

    assert rc == 2


def test_should_reject_bare_dotdot_filename(tmp_path):
    rc = sp.main(["--datei", "..", "--basis", str(tmp_path)])

    assert rc == 2


def test_should_accept_a_plain_filename_without_path_parts(tmp_path):
    schreib(tmp_path, "plain-name.txt", "A=1\n")

    rc = sp.main(["--datei", "plain-name.txt", "--basis", str(tmp_path)])

    assert rc == 0


# --- --alle: Melder fuer Sourcing-Gefahr -------------------------------------


def test_should_exit_1_when_a_bare_file_exists_among_others(tmp_path, capsys):
    schreib(tmp_path, "a_kv", "A=1\n")
    schreib(tmp_path, "b_bare", "nackter-wert\n")

    rc = sp.main(["--alle", "--basis", str(tmp_path)])

    out = capsys.readouterr().out
    assert rc == 1
    assert "b_bare form=bare" in out
    assert "WARN" in out
    assert "ohne NAME=-Form" in out


def test_should_exit_0_when_all_files_are_kv_form(tmp_path, capsys):
    schreib(tmp_path, "a_kv", "A=1\n")
    schreib(tmp_path, "b_kv", "B=2\nC=3\n")

    rc = sp.main(["--alle", "--basis", str(tmp_path)])

    out = capsys.readouterr().out
    assert rc == 0
    assert "WARN" not in out


def test_should_never_print_names_lengths_in_alle_mode(tmp_path, capsys):
    schreib(tmp_path, "a_kv", "GEHEIM=abcdefabcdef\n")

    sp.main(["--alle", "--basis", str(tmp_path)])

    out = capsys.readouterr().out
    assert "len=" not in out
    assert "sha=" not in out
    assert "abcdefabcdef" not in out


# --- Header-Aufbau je Provider ------------------------------------------------


def test_should_build_bearer_header_for_groq():
    headers = sp.baue_header("groq", "wert")

    assert headers["Authorization"] == "Bearer wert"
    assert "x-api-key" not in headers


def test_should_build_bearer_header_for_openai():
    headers = sp.baue_header("openai", "wert")

    assert headers["Authorization"] == "Bearer wert"


def test_should_build_x_api_key_header_for_anthropic():
    headers = sp.baue_header("anthropic", "wert")

    assert headers["x-api-key"] == "wert"
    assert headers["anthropic-version"] == "2023-06-01"
    assert "Authorization" not in headers


def test_should_set_a_dedicated_user_agent_for_every_provider():
    headers = sp.baue_header("groq", "wert")

    assert headers["User-Agent"] == "secrets_pruefen/1"


# --- --http: injizierbarer Netzwerkzugriff -----------------------------------


def test_should_exit_0_when_http_getter_returns_200(tmp_path, monkeypatch, capsys):
    schreib(tmp_path, "groq_key", "wert-fuer-groq\n")
    monkeypatch.setattr(sp, "http_get", lambda url, headers: 200)

    rc = sp.main(["--datei", "groq_key", "--basis", str(tmp_path), "--http", "groq"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "groq http 200" in out
    assert "wert-fuer-groq" not in out


def test_should_exit_1_when_http_getter_returns_401(tmp_path, monkeypatch, capsys):
    schreib(tmp_path, "groq_key", "wert-fuer-groq\n")
    monkeypatch.setattr(sp, "http_get", lambda url, headers: 401)

    rc = sp.main(["--datei", "groq_key", "--basis", str(tmp_path), "--http", "groq"])

    out = capsys.readouterr().out
    assert rc == 1
    assert "groq http 401" in out


def test_should_report_network_error_as_klasse_not_traceback(
    tmp_path, monkeypatch, capsys
):
    schreib(tmp_path, "groq_key", "wert-fuer-groq\n")

    def platzt(url, headers):
        raise TimeoutError("boom")

    monkeypatch.setattr(sp, "http_get", platzt)

    rc = sp.main(["--datei", "groq_key", "--basis", str(tmp_path), "--http", "groq"])

    out = capsys.readouterr().out
    assert rc == 1
    assert "groq http fehler:TimeoutError" in out
    assert "boom" not in out
    assert "wert-fuer-groq" not in out


def test_should_use_var_to_pick_the_value_from_a_kv_file(tmp_path, monkeypatch, capsys):
    schreib(tmp_path, "mixed", "ANDERE=irrelevant\nGROQ_API_KEY=der-echte-wert\n")
    gesehen = {}

    def fake(url, headers):
        gesehen["auth"] = headers["Authorization"]
        return 200

    monkeypatch.setattr(sp, "http_get", fake)

    rc = sp.main(
        [
            "--datei",
            "mixed",
            "--basis",
            str(tmp_path),
            "--http",
            "groq",
            "--var",
            "GROQ_API_KEY",
        ]
    )

    assert rc == 0
    assert gesehen["auth"] == "Bearer der-echte-wert"


def test_should_reject_http_without_a_matching_var(tmp_path, capsys):
    schreib(tmp_path, "kv-secret", "A=1\nB=2\n")

    rc = sp.main(
        [
            "--datei",
            "kv-secret",
            "--basis",
            str(tmp_path),
            "--http",
            "groq",
            "--var",
            "FEHLT",
        ]
    )

    assert rc == 2


def test_should_use_the_single_bare_value_for_http_without_var(tmp_path, monkeypatch):
    schreib(tmp_path, "bare-secret", "der-bare-wert\n")
    gesehen = {}

    def fake(url, headers):
        gesehen["auth"] = headers["Authorization"]
        return 200

    monkeypatch.setattr(sp, "http_get", fake)

    rc = sp.main(
        ["--datei", "bare-secret", "--basis", str(tmp_path), "--http", "openai"]
    )

    assert rc == 0
    assert gesehen["auth"] == "Bearer der-bare-wert"


def test_should_use_the_anthropic_url_for_anthropic_provider(tmp_path, monkeypatch):
    schreib(tmp_path, "bare-secret", "der-bare-wert\n")
    gesehen = {}

    def fake(url, headers):
        gesehen["url"] = url
        return 200

    monkeypatch.setattr(sp, "http_get", fake)

    sp.main(["--datei", "bare-secret", "--basis", str(tmp_path), "--http", "anthropic"])

    assert gesehen["url"] == sp.PROVIDER_URLS["anthropic"]


def test_should_reject_unknown_provider_via_argparse(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        sp.main(["--datei", "x", "--basis", str(tmp_path), "--http", "nicht-existent"])

    assert exc.value.code == 2
