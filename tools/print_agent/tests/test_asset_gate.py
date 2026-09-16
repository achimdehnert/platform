"""Render-freie Tests fuer das Lizenz-Gate je Asset-Bereich (asset_gate).

Anders als test_profile_license_gate.py braucht diese Datei WEDER WeasyPrint
noch litellm und laeuft deshalb in `make test` (= CI). Sie bewacht die
Lizenz-Invariante selbst; die Verdrahtung in print_agent pruefen die
Render-Tests, sobald WeasyPrint da ist.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from asset_gate import asset_freigegeben, bild_mime  # noqa: E402


def test_should_release_shared_asset_by_shared_flag_not_db():
    ok, bereich = asset_freigegeben("assets/shared/logos/hnu.svg", {"db": False, "shared": True})
    assert (ok, bereich) == (True, "shared")


def test_should_not_let_db_flag_release_asset_from_other_bereich():
    ok, _ = asset_freigegeben("assets/shared/logos/hnu.svg", {"db": True, "shared": False})
    assert ok is False


def test_should_release_iil_asset_by_iil_flag():
    assert asset_freigegeben("assets/iil/logos/iil.png", {"db": False, "iil": True}) == (True, "iil")


def test_should_keep_db_asset_bound_to_db_flag():
    assert asset_freigegeben("assets/db/logos/db.png", {"db": False, "shared": True}) == (False, "db")


def test_should_fail_closed_to_db_flag_for_unknown_bereich():
    # Unbekannter Bereich oder Pfad ohne Bereich: strengstes Flag, nie "frei".
    assert asset_freigegeben("assets/fremd/logo.png", {"db": False, "shared": True}) == (False, "db")
    assert asset_freigegeben("logo.png", {"db": False, "shared": True}) == (False, "db")


def test_should_treat_missing_path_as_not_released():
    assert asset_freigegeben("", {"shared": True})[0] is False


def test_should_map_svg_to_svg_xml_mime():
    assert bild_mime(".svg") == "svg+xml"
    assert bild_mime("SVG") == "svg+xml"


def test_should_map_jpg_to_jpeg_mime():
    assert bild_mime(".jpg") == "jpeg"
