"""Tests für tools/chat_agent/auftragsraum_sync.sh — Auffangnetz-Lauf
(KONZ-platform-059, platform#3079, chat-hub#90).

Ein Stub tritt an die Stelle von `chat_lotse.py` (kein Netz, kein echtes
Matrix-Konto). `HOME` zeigt in jedem Test auf `tmp_path`, damit Journal,
Owner-Env und Regeln-Verzeichnis (alle mit Default unter `~/.claude/…`)
automatisch isoliert sind — kein Test rührt das echte `~/.claude`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SKRIPT = Path(__file__).resolve().parents[1] / "chat_agent" / "auftragsraum_sync.sh"

OWNER = "@achim:chat.iil.pet"

_STUB = '''#!/usr/bin/env python3
"""Stub fuer chat_lotse.py — nur der Unterbefehl "sync", Verhalten ueber
STUB_MODE gesteuert (success|lock|error). Ahmt die echten Signale nach:
Erfolg = eine JSON-Zeile auf stdout, Exit 0; Wache haelt den Lock =
"FEHLER: Ein anderer Lotse-Lauf (watch oder sync) haelt die Sperre — ..."
auf stderr, Exit 1 (siehe acquire_sync_lock in chat-hub/deploy/chat_lotse.py);
jeder andere Fehler = andere stderr-Zeile, Exit 1."""
import json
import os
import sys


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] != "sync":
        print("Stub kennt nur 'sync'", file=sys.stderr)
        return 2
    modus = os.environ.get("STUB_MODE", "success")
    if modus == "lock":
        print(
            "FEHLER: Ein anderer Lotse-Lauf (watch oder sync) haelt die "
            "Sperre — kein zweiter Abruf, sonst gehen Nachrichten verloren",
            file=sys.stderr,
        )
        return 1
    if modus == "error":
        print("FEHLER: Sync fehlgeschlagen: Netzwerk nicht erreichbar", file=sys.stderr)
        return 1
    zeile = {
        "room_id": "!r:chat.iil.pet",
        "room_name": "Achim / Lotse",
        "sender": os.environ.get("STUB_SENDER", "@achim:chat.iil.pet"),
        "ts": "2026-09-14T08:00:00Z",
        "event_id": "$stub1",
        "body": "kurze Notiz aus dem Auffangnetz-Test",
    }
    print(json.dumps(zeile))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _stub_anlegen(tmp_path: Path) -> Path:
    stub = tmp_path / "chat_lotse_stub.py"
    stub.write_text(_STUB, encoding="utf-8")
    stub.chmod(0o755)
    return stub


def _env_datei_anlegen(tmp_path: Path, owner: str = OWNER) -> Path:
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    env_datei = home / ".claude" / "auftragsraum.env"
    env_datei.write_text(f"OWNER_MXID={owner}\n", encoding="utf-8")
    return home


def _lauf(tmp_path: Path, *, modus: str, journal: Path, sender: str = OWNER):
    home = _env_datei_anlegen(tmp_path, sender)
    stub = _stub_anlegen(tmp_path)
    env = dict(os.environ)
    env.update(
        {
            "HOME": str(home),
            "CHAT_LOTSE_PY": sys.executable,
            "CHAT_LOTSE_SCRIPT": str(stub),
            "AUFTRAGSRAUM_JOURNAL": str(journal),
            "STUB_MODE": modus,
            "STUB_SENDER": sender,
        }
    )
    return subprocess.run(
        ["bash", str(SKRIPT)],
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )


def _journal_zeilen(journal: Path) -> list[dict]:
    if not journal.exists():
        return []
    return [
        json.loads(z) for z in journal.read_text(encoding="utf-8").splitlines() if z
    ]


def test_should_sortieren_bei_erfolgreichem_sync(tmp_path):
    journal = tmp_path / "journal.jsonl"
    ergebnis = _lauf(tmp_path, modus="success", journal=journal)
    assert ergebnis.returncode == 0, ergebnis.stderr
    zeilen = _journal_zeilen(journal)
    assert len(zeilen) == 1
    assert zeilen[0]["nachricht_id"] == "$stub1"


def test_should_melden_wenn_wache_den_lock_haelt(tmp_path):
    journal = tmp_path / "journal.jsonl"
    ergebnis = _lauf(tmp_path, modus="lock", journal=journal)
    assert ergebnis.returncode == 0, ergebnis.stderr
    assert ergebnis.stdout.strip() == (
        "Wache laeuft — Zurufe werden live bearbeitet, nichts nachzuholen"
    )
    assert _journal_zeilen(journal) == []


def test_should_fehlschlagen_bei_anderem_sync_fehler(tmp_path):
    journal = tmp_path / "journal.jsonl"
    ergebnis = _lauf(tmp_path, modus="error", journal=journal)
    assert ergebnis.returncode != 0
    assert "Netzwerk nicht erreichbar" in ergebnis.stderr
    assert _journal_zeilen(journal) == []
