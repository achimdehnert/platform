"""Schleuse: Unentschieden-Eintraege verfallen nach 90 Tagen — Secrets nie.

Owner-Entscheid 2026-09-07 (platform#2895 Item 57): "unentschieden" ist kein
Dauerzustand mehr. Ab UNENTSCHIEDEN_FRIST_TAGE gilt ein Eintrag ohne passende
Regel als faellig und wandert mit --aufraeumen --apply ins Archiv, genau wie
jede benannte Klasse. Die Ausnahme fuer Secrets (nie archivieren) darf davon
nicht aufgeweicht werden — das ist hier die Positivkontrolle, kein Nebenfall.

Das Dateisystem wird ausschliesslich ueber tmp_path + monkeypatch simuliert,
nie das echte ~/shared.
"""

import datetime
import importlib.util
import pathlib

_SRC = pathlib.Path(__file__).resolve().parents[1] / "schleuse.py"
_spec = importlib.util.spec_from_file_location("schleuse", _SRC)
schleuse = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(schleuse)

HEUTE = datetime.date(2026, 9, 7)


def _anlegen(schleuse_pfad: pathlib.Path, name: str, alter_tage: int, ist_datei=True):
    ziel = schleuse_pfad / name
    if ist_datei:
        ziel.write_text("inhalt")
    else:
        ziel.mkdir()
        (ziel / "datei.txt").write_text("inhalt")
    stand = HEUTE - datetime.timedelta(days=alter_tage)
    zeitstempel = datetime.datetime.combine(stand, datetime.time(12, 0)).timestamp()
    import os

    os.utime(ziel, (zeitstempel, zeitstempel))
    return ziel


def _sammeln(monkeypatch, tmp_path):
    monkeypatch.setattr(schleuse, "SCHLEUSE", tmp_path)
    return schleuse.sammeln(HEUTE)


def _finde(posten, name):
    for x in posten:
        if x["pfad"].name == name:
            return x
    raise AssertionError(f"{name} nicht in posten: {[p['pfad'].name for p in posten]}")


def test_should_mark_unentschieden_faellig_after_91_days(monkeypatch, tmp_path):
    _anlegen(tmp_path, "irgendein-ordner", 91, ist_datei=False)

    posten = _sammeln(monkeypatch, tmp_path)

    eintrag = _finde(posten, "irgendein-ordner")
    assert eintrag["unentschieden"] is True
    assert eintrag["faellig"] is True


def test_should_keep_unentschieden_in_frist_at_89_days(monkeypatch, tmp_path):
    _anlegen(tmp_path, "irgendein-ordner", 89, ist_datei=False)

    posten = _sammeln(monkeypatch, tmp_path)

    eintrag = _finde(posten, "irgendein-ordner")
    assert eintrag["unentschieden"] is True
    assert eintrag["faellig"] is False


def test_should_never_mark_secrets_container_faellig_even_at_200_days(
    monkeypatch, tmp_path
):
    # SECRETS_TOP ist der Top-Level-Ordner, der die Secrets traegt (inbox/secrets
    # -> "inbox"). sammeln() klassifiziert nur Top-Level-Eintraege, daher hier.
    _anlegen(tmp_path, schleuse.SECRETS_TOP, 200, ist_datei=False)

    posten = _sammeln(monkeypatch, tmp_path)

    eintrag = _finde(posten, schleuse.SECRETS_TOP)
    assert eintrag["unentschieden"] is True
    assert eintrag["faellig"] is False


def test_should_report_unentschieden_faellig_separately_from_in_frist(
    monkeypatch, tmp_path, capsys
):
    _anlegen(tmp_path, "faelliger-ordner", 91, ist_datei=False)
    _anlegen(tmp_path, "frischer-ordner", 40, ist_datei=False)

    posten = _sammeln(monkeypatch, tmp_path)
    schleuse.bericht(posten, zeige_alle=False)
    ausgabe = capsys.readouterr().out

    assert "UNENTSCHIEDEN, IN FRIST (1)" in ausgabe
    assert "UNENTSCHIEDEN, FAELLIG (1)" in ausgabe
    assert "faelliger-ordner" in ausgabe
    assert "frischer-ordner" in ausgabe


def test_should_move_unentschieden_faellig_entry_via_aufraeumen_apply(
    monkeypatch, tmp_path
):
    eintrag_pfad = _anlegen(tmp_path, "alter-rest", 120, ist_datei=False)
    monkeypatch.setattr(schleuse, "SCHLEUSE", tmp_path)

    posten = schleuse.sammeln(HEUTE)
    schleuse.aufraeumen(posten, apply=True, heute=HEUTE)

    assert not eintrag_pfad.exists()
    archiviert = tmp_path / schleuse.ARCHIV / HEUTE.isoformat() / "alter-rest"
    assert archiviert.is_dir()
