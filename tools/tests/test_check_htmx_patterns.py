"""Tests fuer tools/check_htmx_patterns.py (ADR-048 Pre-Commit-Gate AP-001..004).

Issue #1199 TEST-7 (M): laut ADR-244 blockiert dieses Skript "sonst 7 Consumer-
CIs", war aber im platform-Repo selbst ungetestet, obwohl es fleet-weit als
Pre-Commit-Gate verteilt wird -- ein Regex-Fehler haette 7 Consumer-CIs
gleichzeitig brechen koennen. Je Anti-Pattern (AP-001..004) mind. 1
Positiv-Fall (korrekt erkannt) + 1 Negativ-Fall (kein False-Positive bei
aehnlichem, aber korrektem Code).

Modul liegt unter `tools.check_htmx_patterns` (regulaerer Punkt-Name, im
Gegensatz zu den Bindestrich-Skripten) -- direkter Import genuegt.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools import check_htmx_patterns as chp  # noqa: E402


# ---------------------------------------------------------------------------
# AP-001: hx-swap="innerHTML" ohne hx-target
# ---------------------------------------------------------------------------

def test_should_flag_innerhtml_swap_without_target(tmp_path):
    f = tmp_path / "t.html"
    f.write_text('<div hx-get="/x" hx-swap="innerHTML"></div>\n', encoding="utf-8")

    errors = chp.check_file(f)

    assert any("AP-001" in e for e in errors)


def test_should_not_flag_innerhtml_swap_with_target(tmp_path):
    # Regex-Grenze bewusst getroffen: die negative Lookahead im Skript
    # (?![^>]*hx-target) prueft nur VORWAERTS bis zum naechsten '>' — hx-target
    # muss also NACH hx-swap im selben Tag stehen, damit es erkannt wird.
    f = tmp_path / "t.html"
    f.write_text(
        '<div hx-get="/x" hx-swap="innerHTML" hx-target="#out"></div>\n', encoding="utf-8"
    )

    errors = chp.check_file(f)

    assert not any("AP-001" in e for e in errors)


# ---------------------------------------------------------------------------
# AP-002: hx-boost="true" auf <form>
# ---------------------------------------------------------------------------

def test_should_flag_hx_boost_on_form(tmp_path):
    f = tmp_path / "t.html"
    f.write_text('<form hx-boost="true" method="post"></form>\n', encoding="utf-8")

    errors = chp.check_file(f)

    assert any("AP-002" in e for e in errors)


def test_should_not_flag_hx_boost_on_non_form_element(tmp_path):
    f = tmp_path / "t.html"
    f.write_text('<div hx-boost="true"></div>\n', encoding="utf-8")

    errors = chp.check_file(f)

    assert not any("AP-002" in e for e in errors)


# ---------------------------------------------------------------------------
# AP-003: onclick kombiniert mit HTMX-Attribut
# ---------------------------------------------------------------------------

def test_should_flag_onclick_combined_with_htmx_attribute(tmp_path):
    f = tmp_path / "t.html"
    f.write_text(
        '<button onclick="doThing()" hx-post="/x">Go</button>\n', encoding="utf-8"
    )

    errors = chp.check_file(f)

    assert any("AP-003" in e for e in errors)


def test_should_not_flag_onclick_alone_without_htmx(tmp_path):
    f = tmp_path / "t.html"
    f.write_text('<button onclick="doThing()">Go</button>\n', encoding="utf-8")

    errors = chp.check_file(f)

    assert not any("AP-003" in e for e in errors)


# ---------------------------------------------------------------------------
# AP-004: Inline style mit Layout/Color-Property
# ---------------------------------------------------------------------------

def test_should_flag_inline_style_with_color_property(tmp_path):
    f = tmp_path / "t.html"
    f.write_text('<div style="color: red;">x</div>\n', encoding="utf-8")

    errors = chp.check_file(f)

    assert any("AP-004" in e for e in errors)


def test_should_not_flag_inline_style_without_layout_or_color(tmp_path):
    f = tmp_path / "t.html"
    f.write_text('<div style="cursor: pointer;">x</div>\n', encoding="utf-8")

    errors = chp.check_file(f)

    assert not any("AP-004" in e for e in errors)


# ---------------------------------------------------------------------------
# noqa-Marker + Kommentar-Strip
# ---------------------------------------------------------------------------

def test_should_respect_noqa_marker(tmp_path):
    f = tmp_path / "t.html"
    f.write_text(
        '<div hx-get="/x" hx-swap="innerHTML"></div> {# noqa: AP-001 #}\n', encoding="utf-8"
    )

    errors = chp.check_file(f)

    assert not any("AP-001" in e for e in errors)


def test_should_ignore_patterns_inside_html_comments(tmp_path):
    f = tmp_path / "t.html"
    f.write_text(
        '<!-- <div hx-get="/x" hx-swap="innerHTML"></div> -->\n', encoding="utf-8"
    )

    errors = chp.check_file(f)

    assert errors == []


# ---------------------------------------------------------------------------
# main() — Kernpfad Exit-Code
# ---------------------------------------------------------------------------

def test_should_exit_1_when_violations_found(tmp_path, monkeypatch, capsys):
    f = tmp_path / "bad.html"
    f.write_text('<div hx-get="/x" hx-swap="innerHTML"></div>\n', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["check_htmx_patterns.py", str(f)])

    rc = chp.main()

    assert rc == 1
    assert "AP-001" in capsys.readouterr().out


def test_should_exit_0_when_no_violations(tmp_path, monkeypatch):
    f = tmp_path / "good.html"
    f.write_text('<div hx-get="/x" hx-swap="innerHTML" hx-target="#out"></div>\n', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["check_htmx_patterns.py", str(f)])

    assert chp.main() == 0
