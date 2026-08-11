"""Das Buch-Design bringt seinen eigenen Satz mit — und nur es (platform#1919).

`print_agent` war ein Geschäftsdokument-Generator: A4, Projekt-Kopfzeile,
Förder-Footer, Executive-Summary-Kasten. Ein Roman braucht davon nichts. Statt
eines Code-Zweigs darf ein Design jetzt eine eigene CSS-Datei nennen
(`extra_css_file`) — additiv, die drei Haus-Profile bleiben unberührt.

Diese Tests prüfen die **Verdrahtung**, nicht das Aussehen: dass die Datei
gefunden und geladen wird, dass sie NUR beim Buch-Design greift, und dass ein
fehlender Pfad kracht statt still den A4-Satz zurückzuliefern. Der Beleg für das
Aussehen ist ein gerendertes PDF und ein Blick darauf — der gehört in den PR,
nicht in einen Unit-Test.
"""

from pathlib import Path

import pytest
import yaml

AGENT_DIR = Path(__file__).resolve().parent.parent
DESIGNS = yaml.safe_load(
    (AGENT_DIR / "print_designs.yaml").read_text(encoding="utf-8")
)["designs"]


def test_should_offer_a_book_design():
    assert "buch" in DESIGNS


def test_should_point_at_an_existing_css_file():
    """Ein Design, dessen CSS fehlt, sieht aus wie eins, das keine braucht."""
    datei = DESIGNS["buch"]["extra_css_file"]
    assert (AGENT_DIR / "print_templates" / datei).exists()


def test_should_keep_the_house_profiles_free_of_a_design_css():
    """Additiv heißt: die drei Haus-Profile bleiben unverändert."""
    for key in ("meiki", "iil", "ttz"):
        assert "extra_css_file" not in DESIGNS[key], key


def test_should_carry_no_corporate_text_in_the_book_profile():
    """Kopfzeile, Deckblatt-Label und Footer sind im Buch leer — ein Roman hat keinen Absender."""
    d = DESIGNS["buch"]
    assert d["header_left"] == ""
    assert d["cover_label"] == ""
    assert d["footer_suffix"] == ""
    assert d["es_label_text"] == ""


def test_should_load_the_book_css_into_the_stylesheet():
    from print_agent import build_css

    css = build_css(DESIGNS["buch"])

    assert "size: A5" in css
    # Der Kapitelumbruch ist das sichtbarste Buch-Merkmal.
    assert "page-break-before: always" in css


def test_should_not_load_the_book_css_for_a_house_profile():
    """Gegenprobe — sonst belegt der Test oben nur, dass base.css existiert."""
    from print_agent import build_css

    css = build_css(DESIGNS["iil"])

    assert "size: A5" not in css
    assert "size: A4" in css


def test_should_fail_loudly_when_the_design_css_is_missing():
    from print_agent import build_css

    kaputt = dict(DESIGNS["buch"], extra_css_file="gibt-es-nicht.css")

    with pytest.raises(FileNotFoundError, match="gibt-es-nicht.css"):
        build_css(kaputt)
