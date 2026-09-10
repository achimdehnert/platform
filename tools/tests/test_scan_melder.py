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


# --- Eingang des Stapel-Zerlegers (doc-hub#4, A6) ---------------------------


def test_should_watch_the_splitter_input_although_paperless_ignores_it():
    """`schleuse` ist fuer Paperless ignoriert - der Eingang darin nicht."""
    dateien = [
        _datei("schleuse/scan-eingang/stapel.pdf", 60),
        _datei("schleuse/von-box/buch.pdf", 60),
    ]
    treffer = sm.haengende(
        dateien,
        jetzt=JETZT,
        ignore_dirs=["schleuse"],
        beobachtet_trotz=("schleuse/scan-eingang",),
    )
    assert [t["pfad"] for t in treffer] == ["schleuse/scan-eingang/stapel.pdf"]


def test_should_still_ignore_the_splitter_input_without_the_exception():
    """Positivkontrolle: ohne die Ausnahme greift die Ignoranz wie zuvor."""
    dateien = [_datei("schleuse/scan-eingang/stapel.pdf", 60)]
    assert sm.haengende(dateien, jetzt=JETZT, ignore_dirs=["schleuse"]) == []


# --- Ablagen ausserhalb des Consume-Baums (Retro 2026-09-09, Befund 12) -----


def test_should_watch_an_extra_root_outside_the_consume_tree():
    """Was der Zerleger nicht trennen konnte, darf nicht still liegen bleiben."""
    dateien = [_datei("/opt/doc-hub/unklar/stapel.pdf", 600)]
    treffer = sm.haengende(dateien, jetzt=JETZT, ignore_dirs=["schleuse"])
    assert [t["pfad"] for t in treffer] == ["/opt/doc-hub/unklar/stapel.pdf"]


def test_should_prefix_extra_root_files_with_their_absolute_path(monkeypatch):
    """Der absolute Pfad bleibt stehen - sonst kollidiert er mit dem Baum."""
    monkeypatch.setattr(
        sm,
        "sammle",
        lambda wurzel, ssh: ([{"pfad": "a.pdf", "mtime": 0, "groesse": 1}], True),
    )
    dateien, blind = sm.sammle_zusatz(("/opt/doc-hub/unklar",), None)
    assert [d["pfad"] for d in dateien] == ["/opt/doc-hub/unklar/a.pdf"]
    assert blind == []


def test_should_report_an_unreadable_extra_root_as_blind_not_green(monkeypatch):
    """Positivkontrolle: nicht lesbar ist kein leeres Ergebnis."""
    monkeypatch.setattr(sm, "sammle", lambda wurzel, ssh: ([], False))
    dateien, blind = sm.sammle_zusatz(("/opt/doc-hub/unklar",), None)
    assert dateien == []
    assert blind == ["/opt/doc-hub/unklar"]


# --- Aufnahme-Protokoll (doc-hub#3, dritte Messung) -------------------------
#
# Realfall 2026-09-07: `07092026101932.pdf` (Scanner-Nummerndateiname, kein
# Personenbezug) scheiterte in Paperless mit `InputFileError`. Zeilen wortgleich
# aus dem Prod-Log kopiert (2026-09-10 gemessen) - nur der Erfolgsfall unten
# traegt einen erfundenen Ablagenamen statt des echten (oeffentliches Repo).

FEHLSCHLAG_LOG = (
    "[2026-09-07 10:19:50,174] [INFO] [paperless.consumer] [e3fc54dc] "
    "Consuming 07092026101932.pdf\n"
    "[2026-09-07 10:19:50,686] [ERROR] [paperless.tasks] [e3fc54dc] "
    "ConsumeTaskPlugin failed: 07092026101932.pdf: Error occurred while "
    "consuming document 07092026101932.pdf: InputFileError: \n"
    "[2026-09-07 10:19:50,738] [ERROR] [celery.app.trace] Task "
    "documents.tasks.consume_file[e3fc54dc-6f28-4963-8fe3-c5e5b3173dfb] "
    "raised unexpected: ConsumerError(...)\n"
)

ERFOLG_LOG = (
    "[2026-09-10 09:28:10,001] [INFO] [paperless.consumer] [20271811] "
    "Consuming 10092026092800.pdf\n"
    "[2026-09-10 09:28:36,952] [INFO] [paperless.consumer] [20271811] "
    "Document 2026-09-10 Testablage consumption finished\n"
    "[2026-09-10 09:28:36,959] [INFO] [paperless.tasks] [20271811] "
    "ConsumeTaskPlugin completed with: {'document_id': 2491}\n"
)

OFFEN_LOG = (
    "[2026-09-10 09:15:00,000] [INFO] [paperless.consumer] [abc12345] "
    "Consuming 10092026091500.pdf\n"
)


def test_should_recognize_the_real_2026_09_07_ingestion_failure():
    """Positivkontrolle: der Parser muss den echten historischen Fall finden."""
    treffer = sm.aufnahmen(FEHLSCHLAG_LOG)
    assert len(treffer) == 1
    assert treffer[0]["dateiname"] == "07092026101932.pdf"
    assert treffer[0]["ergebnis"] == "fehlgeschlagen"
    assert treffer[0]["fehlerklasse"] == "InputFileError"


def test_should_not_flag_a_successful_ingestion_as_a_finding():
    treffer = sm.aufnahmen(ERFOLG_LOG)
    assert len(treffer) == 1
    assert treffer[0]["ergebnis"] == "fertig"
    assert treffer[0]["document_id"] == 2491
    fehlgeschlagene = [t for t in treffer if t["ergebnis"] == "fehlgeschlagen"]
    assert fehlgeschlagene == []


def test_should_track_an_unfinished_ingestion_as_open_not_failed():
    treffer = sm.aufnahmen(OFFEN_LOG)
    assert len(treffer) == 1
    assert treffer[0]["ergebnis"] == "offen"


def test_should_flag_ingestion_log_as_unmeasured_when_fetch_fails(monkeypatch):
    """Ein stummer Container ist KEIN 'keine Fehlschlaege' — dieselbe Falle wie Ignoranz."""
    monkeypatch.setattr(sm, "_lauf", lambda argv, ssh: (1, ""))
    log_text, gemessen = sm.lies_consumer_log(90, None)
    assert gemessen is False
    zeile = sm.kurzzeile([], geprueft=0, gemessene_ignoranz=True, log_gemessen=gemessen)
    assert "Aufnahme-Log nicht gemessen" in zeile


def test_should_keep_filenames_out_of_short_line_for_failed_ingestions():
    """`--kurz` bleibt zahlenrein — auch bei Aufnahme-Fehlschlaegen."""
    fehlgeschlagene = [
        t for t in sm.aufnahmen(FEHLSCHLAG_LOG) if t["ergebnis"] == "fehlgeschlagen"
    ]
    zeile = sm.kurzzeile(
        [], geprueft=1, gemessene_ignoranz=True, fehlgeschlagene=fehlgeschlagene
    )
    assert "07092026101932" not in zeile
    assert "FEHLGESCHLAGEN" in zeile
    # Der Vollbericht darf den Dateinamen nennen — er laeuft nur lokal.
    assert "07092026101932.pdf" in sm.bericht(
        [], geprueft=1, gemessene_ignoranz=True, fehlgeschlagene=fehlgeschlagene
    )
