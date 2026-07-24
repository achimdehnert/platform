"""Tests für die Rollen-Profil-Registry (KONZ-platform-033, tools/mail_agent/roles.py)."""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "roles.py"
_spec = importlib.util.spec_from_file_location("roles", _SRC)
roles = importlib.util.module_from_spec(_spec)
sys.modules["roles"] = roles  # @dataclass braucht das Modul in sys.modules (string-Annotationen)
_spec.loader.exec_module(roles)


def _registry(tmp_path, **overrides):
    base = {
        "roles": {
            "dehnert_team": {
                "display_name": "KI-Assistent von A. D.",
                "role_line": "LUCA-Werkbank",
                "from": "ad@dehnert.team",
                "transport": "smtp",
                "accent": "#12626B",
                "monogram": "d.",
                "requires_legal_footer": False,
            },
            "iil": {
                "display_name": "Prof. Dr. A. D.",
                "role_line": "Leiter · IIL GmbH",
                "from": "a@iil.gmbh",
                "transport": "graph_draft",
                "accent": "#1F3A5F",
                "requires_legal_footer": True,
            },
        }
    }
    base["roles"].update(overrides)
    p = tmp_path / "mail-roles.json"
    p.write_text(json.dumps(base))
    return str(p)


def test_should_resolve_known_role_with_sender_and_transport(tmp_path):
    reg = _registry(tmp_path)
    prof = roles.resolve("dehnert_team", reg)
    assert prof.sender == "ad@dehnert.team"
    assert prof.transport == "smtp"
    assert prof.accent == "#12626B"


def test_should_raise_on_unknown_role(tmp_path):
    reg = _registry(tmp_path)
    with pytest.raises(ValueError, match="unbekannte Rolle"):
        roles.resolve("does_not_exist", reg)


def test_should_block_when_requires_footer_but_none(tmp_path):
    # iil hat requires_legal_footer=True, aber kein legal_footer_file -> Versand-Blocker
    reg = _registry(tmp_path)
    with pytest.raises(ValueError, match="requires_legal_footer"):
        roles.resolve("iil", reg)


def test_should_resolve_when_required_footer_present(tmp_path):
    footer = tmp_path / "iil-footer.txt"
    footer.write_text("IIL GmbH · HRB 12191 · GF Sabine Dehnert\n")
    reg = _registry(tmp_path, iil={
        "display_name": "Prof. Dr. A. D.", "role_line": "Leiter",
        "from": "a@iil.gmbh", "transport": "graph_draft",
        "requires_legal_footer": True, "legal_footer_file": str(footer),
    })
    prof = roles.resolve("iil", reg)
    assert prof.legal_footer and "HRB 12191" in prof.legal_footer


def test_should_reject_invalid_transport(tmp_path):
    reg = _registry(tmp_path, bad={
        "display_name": "X", "from": "x@y.z", "transport": "carrier_pigeon",
    })
    with pytest.raises(ValueError, match="transport"):
        roles.resolve("bad", reg)


def test_should_render_html_with_role_tokens(tmp_path):
    reg = _registry(tmp_path)
    prof = roles.resolve("dehnert_team", reg)
    htmlout = roles.render_email_html(
        prof, eyebrow="LUCA", greeting="Hallo Ilja,",
        paragraphs=["Erster Absatz.", "Zweiter Absatz."],
        status_rows=[{"label": "Import", "state": "good", "text": "erledigt"}],
    )
    assert prof.accent in htmlout            # Akzent-Token gerendert
    assert "d." in htmlout                    # Monogramm
    assert "Erster Absatz." in htmlout
    assert "#1F7A4D" in htmlout               # good-Status-Farbe
    assert htmlout.lstrip().startswith("<!DOCTYPE html>")


def test_should_html_escape_body_content(tmp_path):
    reg = _registry(tmp_path)
    prof = roles.resolve("dehnert_team", reg)
    htmlout = roles.render_email_html(
        prof, eyebrow="x", greeting="g", paragraphs=["<script>alert(1)</script>"],
    )
    assert "<script>alert(1)</script>" not in htmlout
    assert "&lt;script&gt;" in htmlout


def test_should_raise_on_missing_registry(tmp_path):
    with pytest.raises(FileNotFoundError):
        roles.load_registry(str(tmp_path / "nope.json"))
