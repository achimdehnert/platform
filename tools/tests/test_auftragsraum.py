"""Tests für tools/chat_agent/auftragsraum.py — Stufe 1 (KONZ-platform-059, #3079).

Alles offline über `--eingabe DATEI` und `--journal tmp_path`. Kein Test ruft
`chat_lotse.py` oder `gh` auf; `offen` wird ausschliesslich mit `--ohne-gh`
geprueft. `anwenden` (ohne `--trocken`) wird nur mit einem `erledigt`-Vorschlag
real ausgefuehrt — `board.py --erledigt` existiert noch nicht (#3049) und
scheitert VOR jedem Schreibzugriff, ein `frist`-Vorschlag wird deshalb nie
ohne `--trocken` real ausgefuehrt (koennte das echte Ledger beruehren).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

SKRIPT = Path(__file__).resolve().parents[1] / "chat_agent" / "auftragsraum.py"

OWNER = "@achim:chat.iil.pet"
FREMD = "@ilja:chat.iil.pet"


def _lauf(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SKRIPT), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def _zeile(sender: str, ts: str, event_id: str, body: str) -> str:
    return json.dumps(
        {
            "room_id": "!r:chat.iil.pet",
            "room_name": "Auftraege",
            "sender": sender,
            "ts": ts,
            "event_id": event_id,
            "body": body,
        }
    )


def _sortieren(tmp_path: Path, zeilen: list[str], owner: str = OWNER) -> Path:
    eingabe = tmp_path / "sync.jsonl"
    eingabe.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    journal = tmp_path / "journal.jsonl"
    ergebnis = _lauf(
        "sortieren",
        "--eingabe",
        str(eingabe),
        "--journal",
        str(journal),
        "--owner",
        owner,
    )
    assert ergebnis.returncode == 0, ergebnis.stderr
    return journal


def _journal_lesen(journal: Path) -> list[dict]:
    return [json.loads(z) for z in journal.read_text(encoding="utf-8").splitlines()]


def test_should_klassifizieren_kurzbefehl_erledigt_und_frist(tmp_path):
    journal = _sortieren(
        tmp_path,
        [
            _zeile(OWNER, "2026-09-01T08:00:00Z", "$e1", "#12 erledigt"),
            _zeile(OWNER, "2026-09-01T08:01:00Z", "$e2", "#7 Frist 2026-09-20"),
        ],
    )
    eintraege = _journal_lesen(journal)
    assert eintraege[0]["klasse"] == "kurzbefehl"
    assert eintraege[0]["vorschlag"] == {"nummer": 12, "aktion": "erledigt"}
    assert eintraege[1]["vorschlag"] == {
        "nummer": 7,
        "aktion": "frist",
        "datum": "2026-09-20",
    }


def test_should_klassifizieren_korrektur_bei_bekanntem_praefix(tmp_path):
    journal = _sortieren(
        tmp_path,
        [_zeile(OWNER, "2026-09-01T08:00:00Z", "$e1", "nein, das war falsch")],
    )
    eintrag = _journal_lesen(journal)[0]
    assert eintrag["klasse"] == "korrektur"
    assert eintrag["korrektur"] is True


def test_should_klassifizieren_auftrag_ab_neun_woertern_oder_schluesselwort(tmp_path):
    journal = _sortieren(
        tmp_path,
        [
            _zeile(
                OWNER,
                "2026-09-01T08:00:00Z",
                "$e1",
                "bitte einmal kurz die Betriebsakte pruefen",
            )
        ],
    )
    eintrag = _journal_lesen(journal)[0]
    assert eintrag["klasse"] == "auftrag"


def test_should_klassifizieren_notiz_ohne_muster_und_kuerze(tmp_path):
    journal = _sortieren(
        tmp_path, [_zeile(OWNER, "2026-09-01T08:00:00Z", "$e1", "kurze Notiz")]
    )
    eintrag = _journal_lesen(journal)[0]
    assert eintrag["klasse"] == "notiz"
    assert eintrag["vorschlag"] is None
    assert eintrag["korrektur"] is False


def test_should_klassifizieren_fremd_wenn_sender_nicht_owner(tmp_path):
    journal = _sortieren(
        tmp_path, [_zeile(FREMD, "2026-09-01T08:00:00Z", "$e1", "#12 erledigt")]
    )
    eintrag = _journal_lesen(journal)[0]
    assert eintrag["klasse"] == "fremd"
    assert eintrag["vorschlag"] is None


def test_should_nicht_zweimal_schreiben_bei_gleicher_nachricht_id(tmp_path):
    zeilen = [_zeile(OWNER, "2026-09-01T08:00:00Z", "$e1", "#12 erledigt")]
    journal = _sortieren(tmp_path, zeilen)
    eingabe = tmp_path / "sync.jsonl"
    ergebnis = _lauf(
        "sortieren",
        "--eingabe",
        str(eingabe),
        "--journal",
        str(journal),
        "--owner",
        OWNER,
    )
    assert ergebnis.returncode == 0
    assert "0 neu" in ergebnis.stdout
    assert len(_journal_lesen(journal)) == 1


def test_should_offen_block_mit_exit_1_bei_alter_korrektur_ohne_artefakt(tmp_path):
    journal = _sortieren(
        tmp_path, [_zeile(OWNER, "2020-01-01T08:00:00Z", "$e1", "nein, falsch")]
    )
    ergebnis = _lauf("offen", "--journal", str(journal), "--ohne-gh", "--block")
    assert ergebnis.returncode == 1
    assert "$e1" in ergebnis.stdout


def test_should_regel_datei_anlegen_und_artefakt_im_journal_schreiben(tmp_path):
    journal = _sortieren(
        tmp_path, [_zeile(OWNER, "2026-09-01T08:00:00Z", "$e1", "nein, falsch")]
    )
    regeln_dir = tmp_path / "regeln"
    ergebnis = _lauf(
        "regel",
        "$e1",
        "--why",
        "Testgrund",
        "--journal",
        str(journal),
        "--regeln-dir",
        str(regeln_dir),
    )
    assert ergebnis.returncode == 0
    dateien = list(regeln_dir.glob("*.md"))
    assert len(dateien) == 1
    eintrag = _journal_lesen(journal)[0]
    assert eintrag["artefakt"] == f"file://{dateien[0].resolve()}"


def test_should_anwenden_trocken_kommandos_zeigen_ohne_journal_zu_aendern(tmp_path):
    journal = _sortieren(
        tmp_path, [_zeile(OWNER, "2026-09-01T08:00:00Z", "$e1", "#12 erledigt")]
    )
    vorher = journal.read_text(encoding="utf-8")
    ergebnis = _lauf("anwenden", "--journal", str(journal), "--trocken")
    assert ergebnis.returncode == 0
    assert "board.py" in ergebnis.stdout
    assert "--erledigt 12" in ergebnis.stdout
    assert journal.read_text(encoding="utf-8") == vorher


def test_should_anwenden_ohne_erledigt_argument_nicht_anwenden_und_exit_0(tmp_path):
    """#3049 baut `board.py --erledigt` noch nicht — bis dahin bleibt der
    Vorschlag unbearbeitet und `anwenden` bricht trotzdem nicht ab."""
    journal = _sortieren(
        tmp_path, [_zeile(OWNER, "2026-09-01T08:00:00Z", "$e1", "#12 erledigt")]
    )
    ergebnis = _lauf("anwenden", "--journal", str(journal))
    assert ergebnis.returncode == 0
    assert "nicht angewendet" in ergebnis.stdout
    eintrag = _journal_lesen(journal)[0]
    assert eintrag["bearbeitet_am"] is None


def test_should_journalzeile_kein_at_und_keinen_nachrichtentext_enthalten(tmp_path):
    journal = _sortieren(
        tmp_path,
        [
            _zeile(
                OWNER,
                "2026-09-01T08:00:00Z",
                "$e1",
                "bitte niemals die Adresse achim@example.com irgendwo speichern",
            )
        ],
    )
    roh = journal.read_text(encoding="utf-8")
    assert "@" not in roh
    assert "achim@example.com" not in roh
    assert "speichern" not in roh


def test_should_ohne_owner_env_jede_nachricht_als_fremd_behandeln(tmp_path):
    eingabe = tmp_path / "sync.jsonl"
    eingabe.write_text(
        _zeile(OWNER, "2026-09-01T08:00:00Z", "$e1", "#12 erledigt") + "\n",
        encoding="utf-8",
    )
    journal = tmp_path / "journal.jsonl"
    ergebnis = _lauf(
        "sortieren",
        "--eingabe",
        str(eingabe),
        "--journal",
        str(journal),
        "--owner-env",
        str(tmp_path / "nicht-vorhanden.env"),
    )
    assert ergebnis.returncode == 0
    eintrag = _journal_lesen(journal)[0]
    assert eintrag["klasse"] == "fremd"


def test_should_konto_hash_sha256_kurzform_sein():
    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location("auftragsraum", SKRIPT)
    modul = module_from_spec(spec)
    spec.loader.exec_module(modul)  # type: ignore[union-attr]
    erwartet = hashlib.sha256(OWNER.encode("utf-8")).hexdigest()[:12]
    assert modul.sha256_kurz(OWNER) == erwartet


def test_should_positivkontrolle_zwanzig_zeilen_ohne_fehlklassifikation(tmp_path):
    """Fixture mit 20 Sync-Zeilen, jede Zeile mit erwarteter Klasse (R1)."""
    faelle = [
        (OWNER, "#1 erledigt", "kurzbefehl"),
        (OWNER, "#2 erl", "kurzbefehl"),
        (OWNER, "#3 ERLEDIGT", "kurzbefehl"),
        (OWNER, "#4 Frist 2026-10-01", "kurzbefehl"),
        (OWNER, "#5 frist 2026-11-15", "kurzbefehl"),
        (OWNER, "nein, das stimmt nicht", "korrektur"),
        (OWNER, "Falsch, bitte nochmal", "korrektur"),
        (OWNER, "kürzer bitte", "korrektur"),
        (OWNER, "kuerzer!", "korrektur"),
        (OWNER, "so: erst pruefen, dann schreiben", "korrektur"),
        (OWNER, "!regel nie ohne Beleg behaupten", "korrektur"),
        (OWNER, "bitte einmal kurz schauen ob das noch offen ist", "auftrag"),
        (OWNER, "mach daraus bitte ein Issue", "auftrag"),
        (OWNER, "bau mir eine neue Uebersicht ueber die Vorgaenge", "auftrag"),
        (
            OWNER,
            "das ist ein sehr langer Satz mit deutlich mehr als acht Woertern insgesamt",
            "auftrag",
        ),
        (OWNER, "kurze Notiz", "notiz"),
        (OWNER, "ok", "notiz"),
        (OWNER, "danke", "notiz"),
        (FREMD, "#9 erledigt", "fremd"),
        (FREMD, "bitte mach das fuer mich", "fremd"),
    ]
    assert len(faelle) == 20

    zeilen = [
        _zeile(sender, f"2026-09-01T08:{i:02d}:00Z", f"$p{i}", text)
        for i, (sender, text, _erwartet) in enumerate(faelle)
    ]
    journal = _sortieren(tmp_path, zeilen)
    eintraege = {e["nachricht_id"]: e["klasse"] for e in _journal_lesen(journal)}

    fehlklassifikationen = [
        (f"$p{i}", eintraege[f"$p{i}"], erwartet)
        for i, (_sender, _text, erwartet) in enumerate(faelle)
        if eintraege[f"$p{i}"] != erwartet
    ]
    assert fehlklassifikationen == []
