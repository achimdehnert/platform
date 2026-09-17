"""Render-freie Unit-Tests fürs allowed_assets-Lizenz-Gate in print_agent._profile_to_design.

Kern-Invariante (Lizenz §1 DB Type): DB-Logo/Fonts werden NUR eingebettet,
wenn das design-hub-Profil `allowed_assets.db: true` setzt. Kein Rendering nötig.
"""

import struct
import sys
import zlib
from pathlib import Path

import pytest

# Schwere Render-Deps sind hier nicht nötig, aber print_agent importiert sie
# auf Modulebene — wo sie fehlen (CI ohne weasyprint), sauber überspringen statt failen.
pytest.importorskip("weasyprint")
pytest.importorskip("litellm")
pytest.importorskip("markdown")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import print_agent  # noqa: E402


def _tiny_png(path: Path) -> None:
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(typ: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + typ
            + data
            + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\xff\xff\xff")
    path.write_bytes(
        sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    )


_COLOURS = (
    "colours: {primary: '#EC0016', primary_dark: '#8C000E', text: '#3C414C', "
    "bg_light: '#FFF1F2', border: '#F5C5C9', zebra: '#F4F5F7', "
    "accent_1: '#3C414C', accent_2: '#646973'}\n"
)
_COMMON = (
    "header: {text: H, cover_label: CL}\nfooter: {suffix: F}\n"
    "llm_context: ctx\nes_label_text: Zus\n"
    "fonts: {primary: 'Test Font', primary_path: fonts/x.ttf, fallbacks: [Arial]}\n"
    "logo: {url: logo.png, height_px: 36, alt: DB}\n"
    "classification: {banner_text: VERTRAULICH}\n"
)


def _fake_design_hub(root: Path) -> None:
    (root / "profiles").mkdir(parents=True)
    _tiny_png(root / "logo.png")
    (root / "profiles" / "db-yes.yaml").write_text(
        "schema_version: 1\nname: db-yes\n"
        "allowed_assets: {db: true, iil: false, shared: true}\n" + _COLOURS + _COMMON
    )
    (root / "profiles" / "db-no.yaml").write_text(
        "schema_version: 1\nname: db-no\n"
        "allowed_assets: {db: false, iil: true, shared: true}\n" + _COLOURS + _COMMON
    )


def test_should_embed_db_assets_when_allowed(tmp_path, monkeypatch):
    _fake_design_hub(tmp_path)
    monkeypatch.setattr(print_agent, "DESIGN_HUB_DIR", tmp_path)
    # Font-Installation (fontconfig-Seiteneffekt) für den Unit-Test neutralisieren.
    monkeypatch.setattr(print_agent, "_install_brand_fonts", lambda rel: True)

    d = print_agent._profile_to_design("db-yes")

    assert d.get("_logo_data_uri", "").startswith("data:image/png;base64,")
    assert d.get("_body_font")  # Font nur wenn db erlaubt UND Installation ok
    assert d["primary"] == "#EC0016"
    assert d["_classification"] == "VERTRAULICH"


def test_should_not_embed_db_assets_when_not_allowed(tmp_path, monkeypatch):
    _fake_design_hub(tmp_path)
    monkeypatch.setattr(print_agent, "DESIGN_HUB_DIR", tmp_path)
    # Selbst wenn die Installation erfolgreich WÄRE, muss db:false sie überspringen.
    monkeypatch.setattr(print_agent, "_install_brand_fonts", lambda rel: True)

    d = print_agent._profile_to_design("db-no")

    assert "_logo_data_uri" not in d
    assert "_body_font" not in d


def test_should_abort_on_missing_profile(tmp_path, monkeypatch):
    (tmp_path / "profiles").mkdir(parents=True)
    monkeypatch.setattr(print_agent, "DESIGN_HUB_DIR", tmp_path)
    with pytest.raises(SystemExit):
        print_agent._profile_to_design("does-not-exist")


# --- Freigabe je Asset-Bereich (2026-09-16) ---------------------------------
# Bis dahin hing jedes Logo am Flag `db`: das freigegebene HNU-Logo
# (assets/shared/) und das IIL-Logo (assets/iil/) kamen nie in ein PDF.


def _bereichs_hub(root: Path, allowed: str, logo_url: str) -> None:
    (root / "profiles").mkdir(parents=True, exist_ok=True)
    ziel = root / logo_url
    ziel.parent.mkdir(parents=True, exist_ok=True)
    if logo_url.endswith(".svg"):
        ziel.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>')
    else:
        _tiny_png(ziel)
    (root / "profiles" / "p.yaml").write_text(
        "schema_version: 1\nname: p\n"
        f"allowed_assets: {allowed}\n" + _COLOURS
        + "header: {text: H, cover_label: CL}\nfooter: {suffix: F}\n"
        + f"logo: {{url: {logo_url}, height_px: 32, alt: X}}\n"
    )


def test_should_embed_shared_logo_when_shared_allowed_even_if_db_is_not(tmp_path, monkeypatch):
    _bereichs_hub(tmp_path, "{db: false, iil: false, shared: true}", "assets/shared/logos/hnu.png")
    monkeypatch.setattr(print_agent, "DESIGN_HUB_DIR", tmp_path)

    d = print_agent._profile_to_design("p")

    assert d.get("_logo_data_uri", "").startswith("data:image/png;base64,")


def test_should_not_embed_shared_logo_when_shared_not_allowed(tmp_path, monkeypatch):
    # Gegenprobe: `db: true` darf ein Logo aus einem ANDEREN Bereich nicht freigeben.
    _bereichs_hub(tmp_path, "{db: true, iil: true, shared: false}", "assets/shared/logos/hnu.png")
    monkeypatch.setattr(print_agent, "DESIGN_HUB_DIR", tmp_path)

    d = print_agent._profile_to_design("p")

    assert "_logo_data_uri" not in d


def test_should_embed_iil_logo_when_iil_allowed(tmp_path, monkeypatch):
    _bereichs_hub(tmp_path, "{db: false, iil: true, shared: false}", "assets/iil/logos/iil.png")
    monkeypatch.setattr(print_agent, "DESIGN_HUB_DIR", tmp_path)

    d = print_agent._profile_to_design("p")

    assert "_logo_data_uri" in d


def test_should_use_svg_xml_mime_for_svg_logo(tmp_path, monkeypatch):
    # `data:image/svg;base64,...` ist kein gueltiger Typ und wird still verworfen.
    _bereichs_hub(tmp_path, "{db: false, iil: false, shared: true}", "assets/shared/logos/hnu.svg")
    monkeypatch.setattr(print_agent, "DESIGN_HUB_DIR", tmp_path)

    d = print_agent._profile_to_design("p")

    assert d.get("_logo_data_uri", "").startswith("data:image/svg+xml;base64,")


def test_should_fall_back_to_db_flag_for_logo_outside_known_bereich():
    # fail-closed: ein Pfad ohne bekannten Bereich braucht weiterhin `db`.
    assert print_agent.asset_freigegeben("logo.png", {"db": False, "shared": True}) == (False, "db")
    assert print_agent.asset_freigegeben("logo.png", {"db": True}) == (True, "db")
