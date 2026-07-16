"""Tests fuer tools/check_design_tokens.py (ADR-049 Pre-Commit-Gate).

Issue #1199 TEST-7 (M): Schwester-Skript zu check_htmx_patterns.py, laut
ADR-244 fleet-weit als Pre-Commit-Gate verteilt ("blockiert sonst 7 Consumer-
CIs"), war im platform-Repo selbst ungetestet. Positiv-Fall (Direkt-Farbe /
Hex-Farbe korrekt erkannt) + Negativ-Fall (semantisches Token / erlaubte
Property loest keinen False-Positive aus) je Regel.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools import check_design_tokens as cdt  # noqa: E402


# ---------------------------------------------------------------------------
# DIRECT_COLORS: direkte Tailwind-Farbklassen -> Warnung mit Vorschlag
# ---------------------------------------------------------------------------


def test_should_warn_on_direct_tailwind_color_class(tmp_path):
    f = tmp_path / "t.html"
    f.write_text('<div class="bg-blue-500 p-4">x</div>\n', encoding="utf-8")

    errors, warnings = cdt.check_file(f)

    assert errors == []
    assert any("bg-blue-500" in w and "bg-primary" in w for w in warnings)


def test_should_not_warn_on_semantic_token_class(tmp_path):
    f = tmp_path / "t.html"
    f.write_text('<div class="bg-primary p-4">x</div>\n', encoding="utf-8")

    errors, warnings = cdt.check_file(f)

    assert errors == []
    assert warnings == []


# ---------------------------------------------------------------------------
# HARDCODED_HEX: hex-Farbe in color/background/border-color -> Error
# ---------------------------------------------------------------------------


def test_should_error_on_hardcoded_hex_color(tmp_path):
    f = tmp_path / "t.css"
    f.write_text(".x { color: #ff0000; }\n", encoding="utf-8")

    errors, warnings = cdt.check_file(f)

    assert any("#ff0000" in e for e in errors)


def test_should_not_error_on_pui_token_var(tmp_path):
    """Aehnlich aussehende, aber korrekte Deklaration ueber ein --pui-*-Token
    (kein Hex-Literal) darf keinen False-Positive ausloesen."""
    f = tmp_path / "t.css"
    f.write_text(".x { color: var(--pui-danger); }\n", encoding="utf-8")

    errors, warnings = cdt.check_file(f)

    assert errors == []


def test_should_not_error_on_unrelated_property_with_hex_like_value(tmp_path):
    """Property ausserhalb color/background/border-color mit Hex-artigem
    Wert (z.B. z-index) darf nicht als Hardcoded-Hex-Verstoss zaehlen."""
    f = tmp_path / "t.css"
    f.write_text(".x { z-index: 100; }\n", encoding="utf-8")

    errors, warnings = cdt.check_file(f)

    assert errors == []


# ---------------------------------------------------------------------------
# main() — Kernpfad Exit-Code + --strict
# ---------------------------------------------------------------------------


def test_should_exit_1_on_hardcoded_hex_error(tmp_path, monkeypatch, capsys):
    f = tmp_path / "bad.css"
    f.write_text(".x { color: #123456; }\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["check_design_tokens.py", str(f)])

    rc = cdt.main()

    assert rc == 1
    assert "#123456" in capsys.readouterr().out


def test_should_exit_0_on_warning_only_without_strict(tmp_path, monkeypatch):
    f = tmp_path / "warn.html"
    f.write_text('<div class="bg-blue-500">x</div>\n', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["check_design_tokens.py", str(f)])

    assert cdt.main() == 0


def test_should_exit_1_on_warning_with_strict(tmp_path, monkeypatch):
    f = tmp_path / "warn.html"
    f.write_text('<div class="bg-blue-500">x</div>\n', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["check_design_tokens.py", "--strict", str(f)])

    assert cdt.main() == 1


def test_should_exit_0_for_clean_file(tmp_path, monkeypatch):
    f = tmp_path / "clean.html"
    f.write_text('<div class="bg-primary text-foreground">x</div>\n', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["check_design_tokens.py", str(f)])

    assert cdt.main() == 0
