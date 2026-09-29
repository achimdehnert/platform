"""Tests fuer den Seitenumbruch-Stil von Tabellen (tabellen_umbruch.py).

Realfall 2026-09-29: eine zehnzeilige Tabelle wurde als Block auf die naechste
Seite geschoben, die halbe Seite davor blieb leer. Die Tests pruefen beide
Richtungen — kurze Tabellen bekommen die Zusammenhalte-Klasse, lange nicht —
damit der Test nicht nur den Happy-Path misst.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_MODUL = Path(__file__).resolve().parents[1] / "tabellen_umbruch.py"
_spec = importlib.util.spec_from_file_location("tabellen_umbruch", _MODUL)
tu = importlib.util.module_from_spec(_spec)
sys.modules["tabellen_umbruch"] = tu
_spec.loader.exec_module(tu)


def _tabelle(zeilen: int, attrs: str = "") -> str:
    rows = "".join(f"<tr><td>{i}</td><td>x</td></tr>" for i in range(zeilen))
    return f"<table{attrs}><thead><tr><th>a</th><th>b</th></tr></thead><tbody>{rows}</tbody></table>"


def test_should_count_only_body_rows_not_the_header():
    assert tu.datenzeilen(_tabelle(3)) == 3


def test_should_keep_a_short_table_together():
    html = tu.markiere_kurze_tabellen(_tabelle(tu.KURZE_TABELLE_MAX_ZEILEN))
    assert f'class="{tu.KLASSE_ZUSAMMENHALTEN}"' in html


def test_should_let_a_long_table_flow():
    html = tu.markiere_kurze_tabellen(_tabelle(tu.KURZE_TABELLE_MAX_ZEILEN + 1))
    assert tu.KLASSE_ZUSAMMENHALTEN not in html


def test_should_append_to_an_existing_class_attribute():
    html = tu.markiere_kurze_tabellen(_tabelle(2, ' class="price-table"'))
    assert f'class="price-table {tu.KLASSE_ZUSAMMENHALTEN}"' in html


def test_should_not_duplicate_the_class():
    html = tu.markiere_kurze_tabellen(_tabelle(2, f' class="{tu.KLASSE_ZUSAMMENHALTEN}"'))
    assert html.count(tu.KLASSE_ZUSAMMENHALTEN) == 1


def test_should_treat_each_table_on_its_own():
    html = tu.markiere_kurze_tabellen(_tabelle(2) + "<p>Text</p>" + _tabelle(20))
    erste, zweite = html.split("<p>Text</p>")
    assert tu.KLASSE_ZUSAMMENHALTEN in erste
    assert tu.KLASSE_ZUSAMMENHALTEN not in zweite


def test_should_leave_html_without_tables_untouched():
    assert tu.markiere_kurze_tabellen("<p>nur Text</p>") == "<p>nur Text</p>"
