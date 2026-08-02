"""Tests für `bodystructure` — überwiegend gegen **echte** Serverantworten.

Die Fixture `fixtures/bodystructure_echt.json` wurde am 2026-08-02 aus dem
HNU-Postfach erhoben. Erfundene Beispiele hätten hier nicht getragen: dass
Dateinamen über zwei RFC-2047-Wörter *mitten im Wort* zerrissen ankommen und
dass Outlook-Signaturlogos als `inline` mit Content-ID auftreten, stand in
keinem Lehrbuch-Beispiel — beides fiel erst am echten Bestand auf (Lehre
platform#1596/#1606).

**Die Werte sind entpersonalisiert, die Form ist echt.** Jede Zeichenkette, die
nicht strukturell ist (Medientyp, Parametername, Kodierung, Zeichensatz,
Disposition, Sprachcode), wurde per Whitelist ersetzt — Dateinamen durch
`AnlageN.<endung>`, Adressen und Betreffzeilen durch Platzhalter, Content-IDs
durch `<cidN@example.invalid>`. Erhalten bleibt genau das, was geprüft wird:
Verschachtelung, Feldpositionen, Dispositionen und die Zerreißung kodierter
Namen. Die Rohfassung enthielt Namen Studierender und eine Anschrift; solche
Daten gehören in kein Repository, auch in kein privates.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mail_agent"))

import bodystructure as bs  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "bodystructure_echt.json"


@pytest.fixture(scope="module")
def echt() -> dict[str, bytes]:
    daten = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return {k: v.encode("utf-8") for k, v in daten.items()}


# -- echte Serverantworten -------------------------------------------------


def test_should_pdf_anhang_aus_echter_antwort_erkennen(echt):
    teile = bs.aus_fetch_antwort(echt["pdf_anhang"])
    assert teile is not None
    anhaenge = bs.anhaenge(teile)
    pdfs = [t for t in anhaenge if t.media_type == "application/pdf"]
    assert pdfs, "kein PDF erkannt, obwohl die Antwort eines enthaelt"
    assert pdfs[0].dateiname.lower().endswith(".pdf")
    assert pdfs[0].groesse > 0
    assert pdfs[0].disposition == "attachment"


def test_should_signaturlogo_nicht_als_anhang_zaehlen(echt):
    """Ein `inline`-Bild mit Content-ID ist Darstellung, kein Dokument."""
    teile = bs.aus_fetch_antwort(echt["inline_bild_mit_cid"])
    assert teile is not None
    bilder = [t for t in teile if t.media_type.startswith("image/") and t.content_id]
    assert bilder, "Fixture enthaelt kein inline-Bild mit Content-ID"
    assert all(b.ist_layout for b in bilder)
    assert all(not b.ist_anhang for b in bilder)


def test_should_kodierten_dateinamen_aus_zwei_woertern_zusammensetzen(echt):
    """Der reale Fall: ein Name, zerrissen über ein B- und ein Q-Wort.

    Die Fixture stammt aus einer echten Nachricht, in der der Dateiname als
    ``=?utf-8?B?…?= =?utf-8?Q?terzeichnet.pdf?=`` ankam — die Trennung liegt
    **mitten im Wort**, nicht an einer Silbengrenze. Wer nur das erste Wort
    dekodiert, bekommt einen Namen ohne Endung; wer gar nicht dekodiert,
    bekommt ``…?=`` und findet später keinen Parser.
    """
    teile = bs.aus_fetch_antwort(echt["kodierter_dateiname"])
    assert teile is not None
    pdfs = [t for t in bs.anhaenge(teile) if t.media_type == "application/pdf"]
    assert pdfs, "kein PDF-Anhang in der Fixture"
    name = pdfs[0].dateiname
    assert name.endswith("unterzeichnet.pdf"), f"Name nicht zusammengesetzt: {name!r}"
    assert "=?" not in name and "?=" not in name


def test_should_keinen_kodierten_rest_in_dateinamen_lassen(echt):
    """Über ALLE erhobenen Antworten: kein Dateiname trägt Kodierungsreste."""
    for schluessel, roh in echt.items():
        for t in bs.aus_fetch_antwort(roh) or []:
            assert "=?" not in t.dateiname, f"{schluessel}: {t.dateiname!r}"
            assert "?=" not in t.dateiname, f"{schluessel}: {t.dateiname!r}"


def test_should_in_weitergeleitete_nachricht_absteigen(echt):
    """Ein Anhang *in* einer eingebetteten Nachricht bleibt sonst unsichtbar."""
    teile = bs.aus_fetch_antwort(echt["verschachtelte_nachricht"])
    assert teile is not None
    rfc822 = [t for t in teile if t.media_type == "message/rfc822"]
    assert rfc822, "Fixture enthaelt keine eingebettete Nachricht"
    # Der Abstieg erzeugt Teile mit einer Nummer UNTERHALB der des Containers.
    tiefer = [t for t in teile if t.teilnummer.startswith(rfc822[0].teilnummer + ".")]
    assert tiefer, "nicht in die eingebettete Nachricht abgestiegen"


def test_should_dateiname_nicht_aus_der_eingebetteten_nachricht_erben(echt):
    """Der Container darf keinen Namen aus seinem Inneren übernehmen.

    Am echten Bericht nachgemessen: seine eigene Disposition (`attachment`,
    Index 11) trägt **nur Datumsangaben, keinen Dateinamen** — ein geerbter
    Name wäre also sofort als Fremdkörper erkennbar.
    """
    teile = bs.aus_fetch_antwort(echt["verschachtelte_nachricht"])
    container = [t for t in teile if t.media_type == "message/rfc822"][0]
    innere = [
        t.dateiname
        for t in teile
        if t.teilnummer.startswith(container.teilnummer + ".") and t.dateiname
    ]
    assert container.dateiname not in innere or not container.dateiname


def test_should_disposition_des_inneren_teils_nicht_dem_aeusseren_zuschreiben():
    """Regressionsschutz für die typabhängigen Erweiterungs-Offsets.

    Bei `message/rfc822` steht die eingebettete Struktur an Index 8, also VOR
    den Erweiterungsfeldern. Eine Suche über den ganzen Rest fände dort die
    Disposition des inneren Anhangs und schriebe sie dem Container zu. Hier hat
    der Container **gar keine** Disposition — findet der Leser trotzdem eine,
    stammt sie aus dem Inneren.
    """
    roh = (
        b'1 (BODYSTRUCTURE ("message" "rfc822" NIL NIL NIL "7bit" 500 '
        b'("Datum" "Betreff" NIL NIL NIL NIL NIL NIL NIL NIL) '
        b'(("text" "plain" ("charset" "utf-8") NIL NIL "7bit" 10 1 NIL NIL NIL NIL)'
        b'("application" "pdf" ("name" "innen.pdf") NIL NIL "base64" 100 NIL '
        b'("attachment" ("filename" "innen.pdf")) NIL NIL) "mixed" ("boundary" "b") NIL NIL) '
        b"12 NIL NIL NIL NIL))"
    )
    teile = bs.aus_fetch_antwort(roh)
    assert teile is not None
    container = [t for t in teile if t.media_type == "message/rfc822"][0]
    assert container.disposition == "", "Disposition aus der eingebetteten Nachricht geerbt"
    assert container.dateiname == "", "Dateiname aus der eingebetteten Nachricht geerbt"
    # Der innere Anhang muss trotzdem gefunden werden.
    assert any(t.dateiname == "innen.pdf" and t.ist_anhang for t in teile)


def test_should_docx_und_tabelle_mit_medientyp_erkennen(echt):
    for schluessel, erwartet in (
        ("docx_anhang", "wordprocessingml.document"),
        ("tabelle", "spreadsheetml.sheet"),
    ):
        teile = bs.aus_fetch_antwort(echt[schluessel])
        assert teile is not None, schluessel
        assert any(erwartet in t.media_type for t in bs.anhaenge(teile)), schluessel


def test_should_alle_echten_antworten_lesen_koennen(echt):
    """Keine der erhobenen Antworten darf als „nicht lesbar" enden."""
    for schluessel, roh in echt.items():
        assert bs.aus_fetch_antwort(roh) is not None, f"{schluessel} nicht lesbar"


# -- Dreiwertigkeit: „nicht erhoben" ist kein „nein" -----------------------


def test_should_fehlende_struktur_als_nicht_erhoben_melden():
    assert bs.aus_fetch_antwort(b"1 (UID 5 FLAGS (\\Seen))") is None


def test_should_unlesbare_struktur_als_nicht_erhoben_melden():
    assert bs.aus_fetch_antwort(b'1 (UID 5 BODYSTRUCTURE (("text" "plain"') is None


def test_should_literal_nicht_raten():
    """Ein Literal steht in einem eigenen Antwortteil — hier fehlt er."""
    assert bs.aus_fetch_antwort(b'1 (BODYSTRUCTURE ("text" "plain" ("name" {5}') is None


def test_should_nicht_erhoben_zu_true_fuehren():
    """Im Zweifel `True`: ein falsches `False` verliert den Anhang dauerhaft."""
    assert bs.hat_anhaenge(None) is True


def test_should_erhoben_ohne_anhang_false_sein():
    roh = b'1 (UID 5 BODYSTRUCTURE ("text" "plain" ("charset" "utf-8") NIL NIL "7bit" 42 2 NIL NIL NIL NIL))'
    teile = bs.aus_fetch_antwort(roh)
    assert teile is not None
    assert bs.hat_anhaenge(teile) is False


def test_should_anhaenge_none_durchreichen():
    assert bs.anhaenge(None) is None


# -- Dateinamen: Kodierung und Fortsetzung ---------------------------------


def test_should_rfc2047_ueber_zwei_woerter_zusammensetzen():
    """Der reale Fall: die Endung war auf zwei kodierte Wörter verteilt."""
    params = {"filename": "=?iso-8859-1?q?Antrag.pd?= =?iso-8859-1?q?f?="}
    assert bs.dateiname_aus(params, "filename") == "Antrag.pdf"


def test_should_rfc2231_fortsetzung_zusammensetzen():
    """Synthetisch — im HNU-Bestand nicht vorgekommen, im Standard vorgesehen."""
    params = {"filename*0*": "utf-8''Ver%C3%A4nderungs", "filename*1*": "antrag.pdf"}
    assert bs.dateiname_aus(params, "filename") == "Veränderungsantrag.pdf"


def test_should_rfc2231_einteilig_dekodieren():
    assert bs.dateiname_aus({"filename*": "utf-8''Bericht%20Q1.pdf"}, "filename") == "Bericht Q1.pdf"


def test_should_ohne_dateiname_leer_bleiben():
    assert bs.dateiname_aus({}, "filename", "name") == ""


def test_should_kaputte_kodierung_unveraendert_lassen():
    """Lieber der Rohwert als ein Absturz — der Name ist Beiwerk, nicht Kern."""
    assert bs.dateiname_aus({"filename": "=?nicht-existent?q?x?="}, "filename")


# -- Struktur-Feinheiten ---------------------------------------------------


def test_should_mehrteiler_parameter_nicht_als_kind_zaehlen():
    """Nach dem Subtyp folgen Parameter des Mehrteilers — keine weiteren Teile."""
    roh = (
        b'1 (BODYSTRUCTURE (("text" "plain" ("charset" "utf-8") NIL NIL "7bit" 10 1 NIL NIL NIL NIL)'
        b'("text" "html" ("charset" "utf-8") NIL NIL "7bit" 20 2 NIL NIL NIL NIL)'
        b' "alternative" ("boundary" "xyz") NIL NIL))'
    )
    teile = bs.aus_fetch_antwort(roh)
    assert teile is not None
    assert len(teile) == 2


def test_should_maskiertes_anfuehrungszeichen_im_namen_lesen():
    roh = (
        b'1 (BODYSTRUCTURE ("application" "pdf" ("name" "Ver\\"trag.pdf") NIL NIL '
        b'"base64" 100 NIL ("attachment" ("filename" "Ver\\"trag.pdf")) NIL NIL))'
    )
    teile = bs.aus_fetch_antwort(roh)
    assert teile is not None
    assert teile[0].dateiname == 'Ver"trag.pdf'


def test_should_teilnummern_vergeben():
    roh = (
        b'1 (BODYSTRUCTURE (("text" "plain" ("charset" "utf-8") NIL NIL "7bit" 10 1 NIL NIL NIL NIL)'
        b'("application" "pdf" ("name" "a.pdf") NIL NIL "base64" 100 NIL '
        b'("attachment" ("filename" "a.pdf")) NIL NIL) "mixed" ("boundary" "b") NIL NIL))'
    )
    teile = bs.aus_fetch_antwort(roh)
    assert [t.teilnummer for t in teile] == ["1", "2"]
