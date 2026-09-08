"""Drill fuer tools/scan_melder.py — doc-hub#3.

Der Realfall steht als erster Test: `achim/07092026101932.pdf` lag am 2026-09-07
seit 23 Stunden im Consume-Baum, weil die PDF abgeschnitten war. Genau diese Datei
muss der Melder finden — und die gleichzeitig laufende SFTP-Uebertragung daneben
nicht, sonst meldet er jeden Scan.

Der zweitwichtigste Test ist `test_should_ignore_schleuse_directory`: in
`schleuse/` liegen absichtlich Dateien, die Paperless nie aufnimmt
(`PAPERLESS_CONSUMER_IGNORE_DIRS`). Wuerde der Melder sie zaehlen, meldete er ab
Tag eins denselben Fehlalarm und waere in einer Woche tot.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scan_melder as sm  # noqa: E402

JETZT = 1_757_300_000.0
MIN = 60


def _datei(pfad: str, alter_min: float, groesse: int = 1_091_916) -> dict:
    return {"pfad": pfad, "mtime": JETZT - alter_min * MIN, "groesse": groesse}


def test_should_report_stuck_scan_but_not_the_upload_in_progress():
    dateien = [
        _datei("achim/07092026101932.pdf", 23 * 60),  # Realfall 2026-09-07
        _datei("achim/08092026094500.pdf", 0.3),  # laeuft gerade per SFTP herein
    ]
    treffer = sm.haengende(dateien, jetzt=JETZT)
    assert [t["pfad"] for t in treffer] == ["achim/07092026101932.pdf"]


def test_should_ignore_schleuse_directory():
    dateien = [
        _datei(
            "schleuse/session-retro-extern-2026-09-03-platform-0f59ce.md", 5 * 24 * 60
        )
    ]
    assert sm.haengende(dateien, jetzt=JETZT, ignore_dirs=["schleuse", ".thumbs"]) == []


def test_should_ignore_dotfiles_anywhere():
    dateien = [_datei("achim/.thumbs/vorschau.png", 999), _datei(".DS_Store", 999)]
    assert sm.haengende(dateien, jetzt=JETZT) == []


def test_should_read_ignore_dirs_from_container_env():
    env = 'PAPERLESS_CONSUMER_RECURSIVE=true\nPAPERLESS_CONSUMER_IGNORE_DIRS=["schleuse", ".thumbs"]\n'
    werte, gemessen = sm.ignorierte_ordner(env)
    assert werte == ["schleuse", ".thumbs"]
    assert gemessen is True


def test_should_flag_ignore_list_as_unmeasured_when_container_silent():
    werte, gemessen = sm.ignorierte_ordner("")
    assert werte == sm.IGNORE_DIRS_FALLBACK
    assert gemessen is False
    zeile = sm.kurzzeile([], geprueft=0, gemessene_ignoranz=gemessen)
    assert "nicht gemessen" in zeile


def test_should_report_each_stuck_file_only_once_per_window():
    """Stuendlicher Lauf, 30-min-Schwelle: jede Datei faellt durch genau ein Fenster."""
    datei = _datei("achim/07092026101932.pdf", 45)  # 45 min alt
    assert sm.haengende(
        [datei], jetzt=JETZT, neu_seit_min=60
    )  # erster Lauf danach: Alarm
    aelter = _datei("achim/07092026101932.pdf", 105)  # eine Stunde spaeter
    assert (
        sm.haengende([aelter], jetzt=JETZT, neu_seit_min=60) == []
    )  # kein zweiter Alarm
    assert sm.haengende([aelter], jetzt=JETZT)  # der Lauf bleibt trotzdem rot


def test_should_keep_folder_and_file_names_out_of_short_line():
    """Repo und Actions-Log sind oeffentlich — die Kurzzeile nennt nur Zahlen."""
    treffer = sm.haengende([_datei("tilly/07092026101932.pdf", 23 * 60)], jetzt=JETZT)
    zeile = sm.kurzzeile(treffer, geprueft=1, gemessene_ignoranz=True)
    assert "tilly" not in zeile and "07092026101932" not in zeile
    assert "23.0 h" in zeile
    # Der Vollbericht darf sie nennen — er laeuft nur lokal.
    assert "tilly/07092026101932.pdf" in sm.bericht(
        treffer, geprueft=1, gemessene_ignoranz=True
    )


def test_should_stay_silent_when_nothing_hangs():
    assert sm.haengende([_datei("achim/frisch.pdf", 2)], jetzt=JETZT) == []


# --- Verlust-Erkennung (doc-hub#3, zweite Haelfte) ---------------------------


def test_should_not_call_a_consumed_file_a_loss():
    """Der Normalfall: die Datei verschwindet, WEIL Paperless sie aufgenommen hat."""
    vorher = [_datei("achim/08092026172132.pdf", 5)]
    weg = sm.verschwundene(vorher, jetzt=[])
    assert [w["pfad"] for w in weg] == ["achim/08092026172132.pdf"]
    # Erst die Antwort von Paperless entscheidet — hier: Dokument existiert.
    gefunden = {"08092026172132.pdf"}
    verluste = [w for w in weg if Path(w["pfad"]).name not in gefunden]
    assert verluste == []


def test_should_call_a_vanished_file_without_document_a_loss():
    """Der Realfall vom 2026-09-08: verschwunden, ohne je ein Dokument zu werden."""
    vorher = [_datei("achim/07092026101932.pdf", 23 * 60)]
    weg = sm.verschwundene(vorher, jetzt=[])
    verluste = [w for w in weg if Path(w["pfad"]).name not in set()]
    assert [v["pfad"] for v in verluste] == ["achim/07092026101932.pdf"]
    zeile = sm.kurzzeile([], geprueft=0, gemessene_ignoranz=True, verluste=verluste)
    assert "VERLOREN" in zeile
    assert "07092026101932" not in zeile  # oeffentliches Repo: keine Namen


def test_should_not_report_a_file_that_is_still_there():
    bleibt = _datei("achim/liegt-noch.pdf", 90)
    assert sm.verschwundene([bleibt], jetzt=[bleibt]) == []


def test_should_survive_a_missing_or_broken_inventory(tmp_path):
    """Erstlauf und beschaedigtes Inventar duerfen keinen Verlust erfinden."""
    fehlt = tmp_path / "gibtsnicht.json"
    assert sm.lade_inventar(fehlt) == []
    kaputt = tmp_path / "kaputt.json"
    kaputt.write_text("{kein json", encoding="utf-8")
    assert sm.lade_inventar(kaputt) == []


def test_should_round_trip_the_inventory(tmp_path):
    pfad = tmp_path / "unter" / "inventar.json"
    dateien = [_datei("achim/a.pdf", 1), _datei("tilly/b.pdf", 2)]
    sm.schreibe_inventar(pfad, dateien)
    assert [d["pfad"] for d in sm.lade_inventar(pfad)] == ["achim/a.pdf", "tilly/b.pdf"]
