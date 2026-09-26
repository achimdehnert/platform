"""Tests für tools/mail_agent/antwort.py — Antwort-Entwurf aus einer Vorlage.

Alle Daten hier sind erfunden (platform ist öffentlich): der Ledger, der Anker
und die Namen. Kein Test fasst ein Postfach an — der einzige Weg nach draußen
(`subprocess.run`) wird im Trockenlauf scharf gestellt und muss ungenutzt bleiben.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mail_agent"))

antwort = pytest.importorskip("antwort")

VORLAGEN = Path(__file__).resolve().parents[1] / "mail_agent" / "vorlagen"

BEISPIELFELDER = {
    "anrede": "Hallo Lena,",
    "thema": "Betreuung Bachelorarbeit",
    "hinweis": "Ein zusätzlicher Satz.",
    "frist": "bis zum 30.09.2026",
}


@pytest.fixture
def ledger_datei(tmp_path: Path) -> Path:
    daten = {
        "vorgaenge": [
            {
                "nr": 900,
                "typ": "betreuung",
                "konto": "hnu",
                "gegenueber": "Lena Musterfrau (Bachelorarbeit)",
                "thread_key": "Re: Anfrage Betreuung Bachelorarbeit",
                "frist": "2026-09-30",
            },
            {
                "nr": 901,
                "typ": "formalie",
                "konto": "hnu",
                "gegenueber": "Prüfungsamt",
                "thread_key": "Formblatt Anmeldung",
            },
        ]
    }
    pfad = tmp_path / "vorgaenge.json"
    pfad.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
    return pfad


@pytest.fixture
def anker_datei(tmp_path: Path) -> Path:
    daten = {
        "900": {
            "item": "900",
            "konto": "hnu",
            "ordner": "INBOX",
            "uid": "4711",
            "message_id": "<beispiel-900@example.invalid>",
            "absender": "lena.musterfrau@example.invalid",
            "betreff": "Anfrage Betreuung Bachelorarbeit",
        }
    }
    pfad = tmp_path / "anker.json"
    pfad.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
    return pfad


def test_should_pick_template_for_own_type():
    pfad = antwort.vorlage_waehlen("betreuung-masterarbeit", "zusage", VORLAGEN)
    assert pfad.parent.name == "betreuung-masterarbeit"
    assert pfad.name == "zusage.md"


def test_should_fall_back_to_vorgang_for_unknown_type():
    pfad = antwort.vorlage_waehlen("rechnung", "absage", VORLAGEN)
    assert pfad.parent.name == "vorgang"


def test_should_fall_back_for_type_without_that_art():
    # dsb-beratung hat bewusst keine Absage-Vorlage — der Rueckfall traegt sie.
    pfad = antwort.vorlage_waehlen("dsb-beratung", "absage", VORLAGEN)
    assert pfad.parent.name == "vorgang"


def test_should_reject_unknown_art():
    with pytest.raises(ValueError):
        antwort.vorlage_waehlen("betreuung", "vielleicht", VORLAGEN)


def test_should_render_without_leftover_placeholders():
    text = antwort.rendern("{anrede}\n\nThema: {thema}\n\n{hinweis}\n", BEISPIELFELDER)
    assert "{" not in text
    assert "Hallo Lena," in text
    assert text.endswith("\n")


def test_should_drop_paragraph_of_empty_placeholder():
    felder = dict(BEISPIELFELDER, hinweis="")
    text = antwort.rendern("{anrede}\n\nThema: {thema}\n\n{hinweis}\n", felder)
    assert "{" not in text
    assert text.count("\n\n") == 1


@pytest.mark.parametrize(
    ("gegenueber", "erwartet"),
    [
        ("Lena Musterfrau", "Hallo Lena,"),
        ("Lena Musterfrau (Bachelorarbeit)", "Hallo Lena,"),
        ("Musterfrau, Lena", "Hallo Lena,"),
        ("Prof. Dr. Jonas Beispiel", "Hallo Jonas,"),
        ("Prüfungsamt", "Guten Tag,"),
        ("Landratsamt Musterstadt", "Guten Tag,"),
        ("", "Guten Tag,"),
    ],
)
def test_should_derive_anrede(gegenueber: str, erwartet: str):
    assert antwort.anrede_aus(gegenueber) == erwartet


@pytest.mark.parametrize(
    ("konto", "erwartet"),
    [
        ("hnu", "Re: Anfrage Betreuung"),
        ("ad", "Re: Anfrage Betreuung"),
        ("iil", "AW: Anfrage Betreuung"),
    ],
)
def test_should_prefix_subject_per_account(konto: str, erwartet: str):
    assert antwort.betreff_aus("AW: Re: Anfrage Betreuung", konto) == erwartet


def test_should_use_neutral_period_without_frist():
    assert antwort.frist_text(None) == "in den nächsten zwei Wochen"
    assert antwort.frist_text("2026-09-30") == "bis zum 30.09.2026"


def test_should_render_every_template_without_placeholders():
    vorlagen = sorted(VORLAGEN.glob("*/*.md"))
    assert len(vorlagen) >= 11
    for pfad in vorlagen:
        text = antwort.rendern(pfad.read_text(encoding="utf-8"), BEISPIELFELDER)
        assert "{" not in text, pfad
        assert "}" not in text, pfad
        assert "Ã" not in text, pfad  # keine Mojibake, echte Umlaute
        assert text.strip(), pfad


def test_should_build_imap_command_with_reply_and_category():
    kommando = antwort.kommando_bauen(
        konto="hnu",
        an="a@example.invalid",
        betreff="Re: Thema",
        body_datei="/tmp/body.txt",
        kategorie="Vorgang-900-betreuung",
        message_id="<x@example.invalid>",
        rolle="hnu",
    )
    assert "draft_mail.py" in kommando[1]
    assert "--in-reply-to" in kommando
    assert "--kategorie" in kommando
    assert kommando[kommando.index("--role") + 1] == "hnu"


def test_should_build_graph_command_as_reply():
    kommando = antwort.kommando_bauen(
        konto="iil",
        an="",
        betreff="AW: Thema",
        body_datei="/tmp/body.txt",
        kategorie="Vorgang-901-dsb",
        graph_id="AAMkAD==",
        rolle="dsb",
    )
    assert "graph_mail.py" in kommando[1]
    assert "--draft" in kommando
    assert kommando[kommando.index("--reply-to") + 1] == "AAMkAD=="
    assert "--category" in kommando


def test_should_choose_dsb_role_for_datenschutz():
    assert antwort.rolle_waehlen("iil", "dsb-beratung") == "dsb"
    assert antwort.rolle_waehlen("iil", "rechnung") == "iil"
    assert antwort.rolle_waehlen("hnu", "betreuung") == "hnu"
    assert antwort.rolle_waehlen("ad", "vorgang") is None


def test_should_print_draft_and_not_call_subprocess(
    ledger_datei: Path, anker_datei: Path, monkeypatch, capsys
):
    def kein_aufruf(*args, **kwargs):
        raise AssertionError("--trocken darf kein Werkzeug aufrufen")

    monkeypatch.setattr(antwort.subprocess, "run", kein_aufruf)
    code = antwort.main(
        [
            "--vorgang",
            "900",
            "--art",
            "zusage",
            "--trocken",
            "--ledger",
            str(ledger_datei),
            "--anker",
            str(anker_datei),
        ]
    )
    ausgabe = capsys.readouterr().out
    assert code == 0
    assert "lena.musterfrau@example.invalid" in ausgabe
    assert "Re: Anfrage Betreuung Bachelorarbeit" in ausgabe
    assert "Hallo Lena," in ausgabe
    assert "bis zum 30.09.2026" in ausgabe
    assert "{" not in ausgabe


def test_should_exit_one_without_anker(ledger_datei: Path, tmp_path: Path, capsys):
    leer = tmp_path / "leer.json"
    leer.write_text("{}", encoding="utf-8")
    code = antwort.main(
        [
            "--vorgang",
            "901",
            "--art",
            "rueckfrage",
            "--trocken",
            "--ledger",
            str(ledger_datei),
            "--anker",
            str(leer),
        ]
    )
    assert code == 1
    assert "anker.py --setze 901" in capsys.readouterr().err


def test_should_exit_one_for_unknown_vorgang(anker_datei: Path, ledger_datei: Path):
    code = antwort.main(
        [
            "--vorgang",
            "999",
            "--art",
            "zusage",
            "--trocken",
            "--ledger",
            str(ledger_datei),
            "--anker",
            str(anker_datei),
        ]
    )
    assert code == 1
