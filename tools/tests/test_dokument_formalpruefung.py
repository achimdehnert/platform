"""Tests für tools/dokument_formalpruefung.py (Konsument: /arbeit-pruefen).

Die Attrappe unten traegt **bekannte** Fehler. Jeder Test prueft nicht nur, dass
eine Pruefung feuert, sondern auch, dass sie bei einem sauberen Dokument
schweigt — sonst belegt ein Treffer nichts (die Null bzw. der Treffer waere das
Messgeraet, nicht das Dokument).

Zwei Tests halten Regressionen fest, die beim Erstlauf am echten Dokument
auftraten und beide zu WENIG meldeten:
- `test_should_umbrochene_unterschrift_vollstaendig_zaehlen`: die erste Fassung
  schnitt Eintraege nach fester Zeichenzahl ab und meldete 16 statt 32.
- `test_should_beleg_hinter_semikolon_finden`: die erste Fassung sah nur die
  erste Quelle je Klammer; "(A, 2016; PMI, 2021)" verlor PMI still.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_TOOL = _ROOT / "tools" / "dokument_formalpruefung.py"
sys.path.insert(0, str(_ROOT / "tools"))

from dokument_formalpruefung import (  # noqa: E402
    belege_im_text,
    literatur_eintraege,
    pruefe,
)

DECKBLATT = """\
                 Masterarbeit

 Ein sauberer Titel ohne Abweichung

Verfasser:               Erika Musterfrau
Arbeit abgeliefert:
Anlagen:
"""

INHALT = """\
Inhaltsverzeichnis                                          ii

 Inhaltsverzeichnis
 Abbildungsverzeichnis ................................. vi
 1.     Einleitung ..................................... 1
 7.     Literaturverzeichnis und Anhang ............... 115
"""

ABB = """\
Abbildungsverzeichnis                                       vi

 Abbildungsverzeichnis
 Abbildung 1 - Auftragseingang nach Jahren, eine sehr lange Unterschrift die
        ueber mehrere Zeilen laeuft und am Ende eine Datei nennt
        (Export_PAS.xlsx) ............................. 17
 Abbildung 2 - ML_BOXPLOT_ERRORS.png ................... 90
 Abbildung 3 - Verteilung der Restfehler je Abteilung .. 91
"""

TAB = """\
Tabellenverzeichnis                                        viii

 Tabellenverzeichnis
 Tabelle 1 - Projekte nach Klassen ...................... 18
 Tabelle 2 - Vergleichsrahmen ........................... 30
 Tabelle 4 - Erste Doppelung ............................ 88
 Tabelle 4 - Zweite Doppelung .......................... 101
"""

KAPITEL = """\
Kapitel 2 - Grundlagen                                        9

Die S-Kurve entsteht aus kumulierten Kosten. (Fleming & Koppelman, 2016; PMI, 2021)
Klassische Verfahren bleiben Referenz. (Tashman, 2000)
Ein Wort mit verlorener Ligatur: E ects und Di erenz.
"""

LITERATUR = """\
Literaturverzeichnis und Anhang                             115

 Literaturverzeichnis
 arXiv:1603.02754. (9. 03 2016). arxiv.org. Von XGBoost: https://arxiv.org/abs/1603.02754 abgerufen
 Breiman, L. (2001). Random Forests. Springer Nature, 5-32.
 Hansika Hewamalage, K. A. (2022). Forecast evaluation. Springer Nature, 788-832.
 Institute For the Future (IFF), U. o. (11. 05 2026). PubMed Central. Von etwas abgerufen
 Quentin W. Fleming, J. M. (2010). Earned Value Project management. PMI.
 Tashman, L. J. (2000). Out-of-sample tests. International Journal of Forecasting, 437-450.
 truegeometry. (17. 05 2026). truegeometry.com. Von Data leakage: https://blog.truegeometry.com/x abgerufen
"""

ERKLAERUNG = "Eidesstattliche Erklärung        118\n\n    Eidesstattliche Erklärung\n"

SEITEN = [DECKBLATT, INHALT, ABB, TAB, KAPITEL, LITERATUR, ERKLAERUNG]

SAUBER = [
    "Masterarbeit\n\nEin sauberer Titel\n\nVerfasser: Erika Musterfrau\n",
    "Inhaltsverzeichnis\n\nInhaltsverzeichnis\nAbbildungsverzeichnis ... vi\n"
    "Tabellenverzeichnis ... viii\nAbkürzungsverzeichnis ... ix\nAbstract ... x\n",
    "Abbildungsverzeichnis\n\nAbbildungsverzeichnis\n"
    " Abbildung 1 - Auftragseingang nach Jahren ... 17\n"
    " Abbildung 2 - Verteilung der Restfehler ..... 90\n",
    "Tabellenverzeichnis\n\nTabellenverzeichnis\n"
    " Tabelle 1 - Projekte nach Klassen ... 18\n"
    " Tabelle 2 - Vergleichsrahmen ........ 30\n",
    "Kapitel 2 - Grundlagen\n\nKlassische Verfahren bleiben Referenz. (Tashman, 2000)\n",
    "Literaturverzeichnis\n\nLiteraturverzeichnis\n"
    " Tashman, L. J. (2000). Out-of-sample tests. International Journal of Forecasting, 437-450.\n",
    "Abstract\n\nAbstract\n\nDies ist eine echte Zusammenfassung mit genug Woertern darin.\n",
    "Abkürzungsverzeichnis\n\nAbkürzungsverzeichnis\n MAE - mittlerer absoluter Fehler\n",
]


def codes(seiten, meta=None, pfad="Ein sauberer Titel.pdf"):
    return [b.code for b in pruefe(seiten, meta or {}, pfad)]


def befund(seiten, code, meta=None, pfad="Ein sauberer Titel.pdf"):
    treffer = [b for b in pruefe(seiten, meta or {}, pfad) if b.code == code]
    return treffer[0] if treffer else None


class TestPositivprobeUndGegenprobe:
    """Jede Pruefung muss am fehlerhaften Dokument feuern UND am sauberen schweigen."""

    @pytest.mark.parametrize(
        "code", ["F01", "F03", "F04", "F05", "F07", "F08", "F11", "F13"]
    )
    def test_should_bei_bekanntem_fehler_feuern(self, code):
        assert code in codes(SEITEN)

    @pytest.mark.parametrize("code", ["F01", "F03", "F05", "F07", "F08", "F11", "F13"])
    def test_should_am_sauberen_dokument_schweigen(self, code):
        assert code not in codes(SAUBER)


def test_should_umbrochene_unterschrift_vollstaendig_zaehlen():
    # Regression: feste Zeichengrenze schnitt Eintraege ab -> 16 statt 32 am
    # echten Dokument. Abbildung 1 nennt die Datei erst in der DRITTEN Zeile.
    b = befund(SEITEN, "F07")
    assert b is not None
    assert "2 von 3" in b.titel, b.titel


def test_should_beleg_hinter_semikolon_finden():
    # Regression: nur die erste Quelle je Klammer wurde gesehen; PMI ging verloren.
    belege = belege_im_text(KAPITEL)
    assert ("PMI", "2021") in belege
    assert ("Fleming & Koppelman", "2016") in belege


def test_should_beleg_ohne_verzeichniseintrag_melden():
    b = befund(SEITEN, "F13")
    assert b is not None
    assert any("PMI" in d for d in b.details)


def test_should_tabellen_dubletten_und_luecken_nennen():
    b = befund(SEITEN, "F05")
    assert "fehlende Nummern: [3]" in b.details
    assert "doppelt vergeben: [4]" in b.details


def test_should_leere_pflichtabschnitte_melden():
    b = befund(SEITEN, "F08")
    assert any("Eidesstattliche Erklärung" in d for d in b.details)


def test_should_ligaturverlust_melden():
    b = befund(SEITEN, "F01")
    assert any("ects" in d or "erenz" in d for d in b.details)


class TestLiteratureintraege:
    def test_should_alle_eintraege_extrahieren(self):
        eintraege = literatur_eintraege(SEITEN)
        assert len(eintraege) == 7

    def test_should_verdachtsmarker_setzen(self):
        nach_autor = {e["autor"]: e["marker"] for e in literatur_eintraege(SEITEN)}
        assert "quellen-id-statt-autor" in nach_autor["arXiv:1603.02754"]
        assert "verlag-statt-zeitschrift" in nach_autor["Breiman, L"]
        assert "autorenfeld-gemischt" in nach_autor["Hansika Hewamalage, K. A"]
        assert (
            "einrichtung-statt-autor"
            in nach_autor["Institute For the Future (IFF), U. o"]
        )
        assert "blog-oder-anbieterseite" in nach_autor["truegeometry"]
        # Realfall-Regression: der mittlere Initial ("Quentin W. Fleming, J. M.")
        # brach das erste Muster — genau die haeufigste Form im echten Verzeichnis.
        assert "autorenfeld-gemischt" in nach_autor["Quentin W. Fleming, J. M"]

    def test_should_sauberen_eintrag_nicht_markieren(self):
        # Gegenprobe: ohne diesen Test wuerde ein Marker-Generator, der IMMER
        # markiert, alle Tests oben bestehen.
        nach_autor = {e["autor"]: e["marker"] for e in literatur_eintraege(SEITEN)}
        assert nach_autor["Tashman, L. J"] == []

    def test_should_fehlenden_marker_nicht_als_korrekt_ausweisen(self):
        # Der Bericht muss ausdruecklich sagen, dass ein markerfreier Eintrag
        # NICHT geprueft ist — sonst liest ihn jemand als Freigabe.
        b = befund(SEITEN, "F12")
        assert b.zu_pruefen is True
        assert any("heißt NICHT" in d for d in b.details)

    def test_should_strukturierte_nutzlast_liefern(self):
        # Marker duerfen nicht aus der Textzeile zurueckgeparst werden — Quellen
        # enthalten selbst eckige Klammern ("arXiv:1905.11744v1 [cs.LG]").
        b = befund(SEITEN, "F12")
        assert isinstance(b.nutzlast, list)
        assert all("marker" in e and "text" in e for e in b.nutzlast)


class TestCli:
    def test_should_json_mit_befunden_liefern(self, tmp_path):
        p = tmp_path / "arbeit.txt"
        p.write_text("\f".join(SEITEN), encoding="utf-8")
        out = subprocess.run(
            [sys.executable, str(_TOOL), str(p), "--json"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert out.returncode == 0, out.stderr
        d = json.loads(out.stdout)
        assert d["seiten"] == len(SEITEN)
        assert {b["code"] for b in d["befunde"]} >= {"F05", "F07", "F12", "F13"}

    def test_should_bei_unlesbarem_dokument_exit_2(self, tmp_path):
        # Eine leere Befundliste aus einem ungelesenen Dokument waere eine Null,
        # die das Werkzeug erzeugt hat — die darf es nicht als Ergebnis ausgeben.
        out = subprocess.run(
            [sys.executable, str(_TOOL), str(tmp_path / "gibtsnicht.txt")],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert out.returncode == 2
        assert "FEHLER" in out.stderr
