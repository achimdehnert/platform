"""tools/ux_pfad.py — Pfad-Modus des /ux-review (Step 2a): reine Funktionen ohne Browser.

Der Lauf selbst braucht Playwright und eine laufende App; hier wird geprueft, was
den Lauf lenkt — Normierung der Pfade (Stationen = Seiten, nicht Objekte) und die
Liste dessen, was notiert statt geklickt wird.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "ux_pfad.py"
_spec = importlib.util.spec_from_file_location("ux_pfad", TOOL)
up = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(up)


def test_should_fold_object_ids_into_one_station():
    """Zwei Projekte sind eine Station — sonst zaehlt der Lauf Objekte statt Seiten."""
    a = up.norm("/projekte/05c58a3d-e44d-42dc-80e3-dec3cdcc20bb/write/")
    b = up.norm("/projekte/e95822c0-6c21-4a9b-adc0-80ec39496a78/write/?page=2#top")
    assert a == b == "/projekte/<id>/write/"


def test_should_fold_integer_ids_but_keep_words():
    assert up.norm("/vorlesungen/modul/12/") == "/vorlesungen/modul/<id>/"
    assert up.norm("/projekte/archiv/") == "/projekte/archiv/"


def test_should_not_click_logout_admin_or_login_links():
    """Abmelden beendet den Lauf, /admin/ ist nicht die App, /l/ ist der Einstiegs-Token."""
    for pfad in ("/accounts/abmelden/", "/admin/", "/l/1:abc/", "/projekte/x/delete/"):
        assert up.SKIP.search(pfad), pfad


def test_should_click_ordinary_pages():
    """Positivkontrolle: der Filter frisst nicht alles."""
    for pfad in ("/projekte/", "/outlines/", "/welten/projekt/<id>/"):
        assert not up.SKIP.search(pfad), pfad


def test_should_be_importable_without_playwright():
    """Die reinen Funktionen haengen nicht am Browser — sonst waere dieser Test schon gefallen."""
    assert callable(up.main)
