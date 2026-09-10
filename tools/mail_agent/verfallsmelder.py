#!/usr/bin/env python3
"""Verfallsmelder fuer Mailcheck und To-do-Liste (K3, #3015).

Das Messjournal (K2, `messjournal.py`) sammelt Kennzahlen — dieser Melder liest
sie und feuert, BEVOR aus einer Kennzahl ein sichtbarer Ausfall wird. Jedes
Signal traegt eine Schwelle und einen Vorlauf; die Sollwerte stehen in
`docs/betrieb/mailcheck.md` und `docs/betrieb/todo-liste.md` im Abschnitt
"Verfallsignale (K3, Soll)".

**Nie Personendaten.** Jede Quelle liefert ausschliesslich Zahlen, Daten und
Bezeichner — nie Adressen, Betreffs oder Namen aus dem Vorgangs-Ledger.

**Nie ein Absturz.** Jede Quelle steht unter Timeout und Fehlerfang; fehlt ein
Wert, ist das Signal `nicht pruefbar`, nie eine Ausnahme.

Kommandos::

    python3 tools/mail_agent/verfallsmelder.py
    python3 tools/mail_agent/verfallsmelder.py --anwendung mailcheck
    python3 tools/mail_agent/verfallsmelder.py --json
    python3 tools/mail_agent/verfallsmelder.py --block   # Exit 1 bei Warnung

`--eingabe JSON` (Inline-JSON oder Pfad zu einer JSON-Datei) ersetzt ALLE
Live-Quellen (Journal, Skill-Kopie-Commit, Quell-Commit, Dienst-Start,
Code-Commit-Zeit) durch feste Werte — fuer Tests, ganz ohne Postfach,
systemctl oder Netz. Schema::

    {
      "journal": [<Journalzeilen wie in mail-messjournal.jsonl>],
      "skill_kopie_commit": "1c0e20978c23",
      "quelle_commit": "d868fa66d3a8",
      "dienst_start": "2026-09-10T10:31:17+00:00",
      "code_commit_zeit": "2026-09-10T12:24:20+02:00"
    }

`--schwellen JSON` ueberschreibt einzelne Default-Schwellen, z. B.
`{"mailcheck.index_alter_tage": 0}`.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
MAIL_AGENT_DIR = Path(__file__).resolve().parent

JOURNAL_DEFAULT = Path.home() / ".claude" / "mail-messjournal.jsonl"
SKILL_KOPIE_MAILCHECK = Path.home() / ".claude" / "commands" / "mailcheck.md"
QUELLE_MAILCHECK = ".windsurf/workflows/mailcheck.md"

TIMEOUT = 15

#: Schluessel "<anwendung>.<signal>" -> Default-Schwelle. `--schwellen`
#: ueberschreibt einzelne Eintraege, nie die ganze Tabelle.
SCHWELLEN_DEFAULT: dict[str, float] = {
    "mailcheck.index_alter_tage": 1.5,  # 36 Stunden
    "mailcheck.ohne_frist": 1,
    "mailcheck.mail_links_tot": 3,
    "mailcheck.journal_alter_tage": 2,
    "todo.mail_links_tot": 3,
    "todo.ohne_kopf_aktion": 5,
    "todo.journal_alter_tage": 2,
}


@dataclass
class Signal:
    anwendung: str
    name: str
    ist: str
    schwelle: str
    zustand: str  # "ok" | "WARNUNG" | "nicht pruefbar"
    hinweis: str

    def zeile(self) -> str:
        return (
            f"{self.anwendung} | {self.name} | {self.ist} | {self.schwelle} | "
            f"{self.zustand} | {self.hinweis}"
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "anwendung": self.anwendung,
            "signal": self.name,
            "ist": self.ist,
            "schwelle": self.schwelle,
            "zustand": self.zustand,
            "hinweis": self.hinweis,
        }


def _run(args: list[str], timeout: int = TIMEOUT) -> tuple[str, str, int | None]:
    """Kommando ausfuehren, nie eine Ausnahme werfen."""
    try:
        lauf = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout, cwd=REPO
        )
        return lauf.stdout, lauf.stderr, lauf.returncode
    except subprocess.TimeoutExpired:
        return "", f"Timeout nach {timeout}s", None
    except OSError as exc:
        return "", str(exc), None


# --- Journal lesen ---------------------------------------------------------


def _journal_lesen(pfad: Path) -> list[dict[str, Any]]:
    if not pfad.exists():
        return []
    try:
        text = pfad.read_text(encoding="utf-8")
    except OSError:
        return []
    eintraege: list[dict[str, Any]] = []
    for zeile in text.splitlines():
        zeile = zeile.strip()
        if not zeile:
            continue
        try:
            eintrag = json.loads(zeile)
        except ValueError:
            continue
        if isinstance(eintrag, dict):
            eintraege.append(eintrag)
    return eintraege


def _juengste_zeile(
    eintraege: list[dict[str, Any]], anwendung: str
) -> dict[str, Any] | None:
    """Die zuletzt angehaengte Zeile der Anwendung. Das Journal waechst nur per
    Anhaengen (`messjournal.schreiben`), die letzte passende Zeile ist die juengste."""
    treffer = [e for e in eintraege if e.get("anwendung") == anwendung]
    return treffer[-1] if treffer else None


def _zeit_parsen(text: Any) -> datetime | None:
    if not isinstance(text, str) or not text:
        return None
    try:
        wert = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if wert.tzinfo is None:
        wert = wert.replace(tzinfo=timezone.utc)
    return wert


# --- Einzelne Signale --------------------------------------------------


def _schwelle(schwellen: dict[str, float], schluessel: str) -> float:
    return schwellen.get(schluessel, SCHWELLEN_DEFAULT[schluessel])


def signal_kennzahl_ueber(
    anwendung: str,
    name: str,
    eintrag: dict[str, Any] | None,
    feld: str,
    schwellen_key: str,
    schwellen: dict[str, float],
    einheit: str,
    vorlauf: str,
) -> Signal:
    """Warnung, wenn `feld` STRENG GROESSER als die Schwelle ist."""
    schwelle = _schwelle(schwellen, schwellen_key)
    if eintrag is None:
        return Signal(
            anwendung,
            name,
            "kein Wert",
            f"> {schwelle}{einheit}",
            "nicht pruefbar",
            "kein Lauf im Messjournal — make boards",
        )
    wert = eintrag.get("kennzahlen", {}).get(feld)
    if wert is None or isinstance(wert, bool):
        return Signal(
            anwendung,
            name,
            "kein Wert",
            f"> {schwelle}{einheit}",
            "nicht pruefbar",
            f"Kennzahl {feld} fehlt in der juengsten Journalzeile",
        )
    zustand = "WARNUNG" if wert > schwelle else "ok"
    hinweis = vorlauf if zustand == "WARNUNG" else "ok"
    return Signal(
        anwendung, name, f"{wert}{einheit}", f"> {schwelle}{einheit}", zustand, hinweis
    )


def signal_kennzahl_ab(
    anwendung: str,
    name: str,
    eintrag: dict[str, Any] | None,
    feld: str,
    schwellen_key: str,
    schwellen: dict[str, float],
    einheit: str,
    vorlauf: str,
) -> Signal:
    """Warnung, wenn `feld` GROESSER-GLEICH der Schwelle ist."""
    schwelle = _schwelle(schwellen, schwellen_key)
    if eintrag is None:
        return Signal(
            anwendung,
            name,
            "kein Wert",
            f">= {schwelle}{einheit}",
            "nicht pruefbar",
            "kein Lauf im Messjournal — make boards",
        )
    wert = eintrag.get("kennzahlen", {}).get(feld)
    if wert is None or isinstance(wert, bool):
        return Signal(
            anwendung,
            name,
            "kein Wert",
            f">= {schwelle}{einheit}",
            "nicht pruefbar",
            f"Kennzahl {feld} fehlt in der juengsten Journalzeile",
        )
    zustand = "WARNUNG" if wert >= schwelle else "ok"
    hinweis = vorlauf if zustand == "WARNUNG" else "ok"
    return Signal(
        anwendung, name, f"{wert}{einheit}", f">= {schwelle}{einheit}", zustand, hinweis
    )


def signal_journal_alter(
    anwendung: str, eintraege: list[dict[str, Any]], schwellen: dict[str, float]
) -> Signal:
    name = "Journal-Alter"
    schwellen_key = f"{anwendung}.journal_alter_tage"
    schwelle = _schwelle(schwellen, schwellen_key)
    eintrag = _juengste_zeile(eintraege, anwendung)
    if eintrag is None:
        return Signal(
            anwendung,
            name,
            "kein Lauf",
            f"> {schwelle} Tage",
            "nicht pruefbar",
            "Journal enthaelt keine Zeile dieser Anwendung — make boards",
        )
    zeit = _zeit_parsen(eintrag.get("zeit"))
    if zeit is None:
        return Signal(
            anwendung,
            name,
            "kein Datum",
            f"> {schwelle} Tage",
            "nicht pruefbar",
            "juengste Journalzeile ohne lesbares Zeitfeld",
        )
    alter_tage = (datetime.now(timezone.utc) - zeit).total_seconds() / 86400
    zustand = "WARNUNG" if alter_tage > schwelle else "ok"
    hinweis = (
        f"kein Lauf seit {alter_tage:.1f} Tagen — make boards"
        if zustand == "WARNUNG"
        else "ok"
    )
    return Signal(
        anwendung,
        name,
        f"{alter_tage:.1f} Tage",
        f"> {schwelle} Tage",
        zustand,
        hinweis,
    )


def signal_skill_kopie_alter(eingabe: dict[str, Any] | None) -> Signal:
    """Verteilte Skill-Kopie vs. Quelle (Issue #3052)."""
    name = "Skill-Kopie"
    anwendung = "mailcheck"
    if eingabe is not None:
        kopie = eingabe.get("skill_kopie_commit")
        quelle = eingabe.get("quelle_commit")
        if not kopie or not quelle:
            return Signal(
                anwendung,
                name,
                "kein Wert",
                "1 Commit",
                "nicht pruefbar",
                "skill_kopie_commit/quelle_commit fehlen in --eingabe",
            )
    else:
        try:
            text = SKILL_KOPIE_MAILCHECK.read_text(encoding="utf-8")
        except OSError:
            return Signal(
                anwendung,
                name,
                "kein Wert",
                "1 Commit",
                "nicht pruefbar",
                f"{SKILL_KOPIE_MAILCHECK} nicht lesbar",
            )
        treffer = re.search(r"source_commit=([0-9a-f]+)", text)
        if not treffer:
            return Signal(
                anwendung,
                name,
                "kein Wert",
                "1 Commit",
                "nicht pruefbar",
                "MANAGED-BY-Kopfzeile ohne source_commit",
            )
        kopie = treffer.group(1)
        out, _err, rc = _run(
            ["git", "log", "-1", "--format=%H", "origin/main", "--", QUELLE_MAILCHECK]
        )
        quelle = out.strip()
        if rc != 0 or not quelle:
            return Signal(
                anwendung,
                name,
                "kein Wert",
                "1 Commit",
                "nicht pruefbar",
                "git log gegen origin/main nicht auswertbar",
            )
    gleich = quelle.startswith(kopie) or kopie.startswith(quelle)
    zustand = "ok" if gleich else "WARNUNG"
    hinweis = (
        "ok" if gleich else "Kopie aelter als Quelle — cc-skill-dist neu verteilen"
    )
    return Signal(anwendung, name, kopie[:12], f"= {quelle[:12]}", zustand, hinweis)


def _dienst_code_signal(
    anwendung: str,
    name: str,
    unit: str,
    quelldatei: str,
    eingabe: dict[str, Any] | None,
) -> Signal:
    schwelle = "Unit-Start >= Code-Commit"
    if eingabe is not None:
        start_text = eingabe.get("dienst_start")
        commit_text = eingabe.get("code_commit_zeit")
        if not start_text:
            return Signal(
                anwendung,
                name,
                "kein Wert",
                schwelle,
                "nicht pruefbar",
                "dienst_start fehlt in --eingabe",
            )
        start = _zeit_parsen(start_text)
        commit = _zeit_parsen(commit_text)
    else:
        out, _err, rc = _run(
            ["systemctl", "--user", "show", unit, "-p", "ActiveEnterTimestamp"]
        )
        if rc is None or rc != 0 or "=" not in out:
            return Signal(
                anwendung,
                name,
                "kein Wert",
                schwelle,
                "nicht pruefbar",
                f"systemctl nicht aufrufbar fuer {unit}",
            )
        start_text = out.strip().split("=", 1)[1]
        start = _zeit_parsen_systemd(start_text)
        commit_out, _e, commit_rc = _run(
            ["git", "log", "-1", "--format=%cI", "--", quelldatei]
        )
        commit = _zeit_parsen(commit_out.strip()) if commit_rc == 0 else None
    if start is None or commit is None:
        return Signal(
            anwendung,
            name,
            "kein Wert",
            schwelle,
            "nicht pruefbar",
            f"Start- oder Commit-Zeit fuer {unit} nicht lesbar",
        )
    zustand = "WARNUNG" if commit > start else "ok"
    hinweis = (
        f"Dienst laeuft mit altem Code, Neustart noetig — systemctl --user restart {unit}"
        if zustand == "WARNUNG"
        else "ok"
    )
    return Signal(
        anwendung,
        name,
        start.isoformat(timespec="seconds"),
        f"< {commit.isoformat(timespec='seconds')}",
        zustand,
        hinweis,
    )


def _zeit_parsen_systemd(text: str) -> datetime | None:
    """`systemctl show -p ActiveEnterTimestamp` liefert z. B.
    'Thu 2026-09-10 10:31:17 UTC' — kein ISO-Format, eigenes Parsing noetig."""
    text = text.strip()
    if not text or text == "n/a":
        return None
    try:
        ohne_tag = text.split(" ", 1)[1]
        wert = datetime.strptime(ohne_tag, "%Y-%m-%d %H:%M:%S %Z")
    except (ValueError, IndexError):
        try:
            wert = datetime.strptime(text, "%a %Y-%m-%d %H:%M:%S %Z")
        except ValueError:
            return None
    return wert.replace(tzinfo=timezone.utc)


# --- Je Anwendung sammeln ---------------------------------------------


def signale_mailcheck(
    eintraege: list[dict[str, Any]],
    eingabe: dict[str, Any] | None,
    schwellen: dict[str, float],
) -> list[Signal]:
    juengste = _juengste_zeile(eintraege, "mailcheck")
    return [
        signal_kennzahl_ueber(
            "mailcheck",
            "Index-Alter",
            juengste,
            "index_alter_tage",
            "mailcheck.index_alter_tage",
            schwellen,
            " Tage",
            "Post-Ingest-Fenster prueft veraltete Daten — suche.py --nur-deckung",
        ),
        signal_kennzahl_ab(
            "mailcheck",
            "Ohne Frist",
            juengste,
            "ohne_frist",
            "mailcheck.ohne_frist",
            schwellen,
            "",
            "Vorgang ohne Frist gefunden — board.py --pruefe",
        ),
        signal_kennzahl_ueber(
            "mailcheck",
            "Tote Links",
            juengste,
            "vorgangsseiten_tot",
            "mailcheck.mail_links_tot",
            schwellen,
            "",
            "tote Links auf Vorgangsseiten — link_pruefen.py --vorgangsseiten",
        ),
        signal_skill_kopie_alter(eingabe),
        signal_journal_alter("mailcheck", eintraege, schwellen),
    ]


def signale_todo(
    eintraege: list[dict[str, Any]],
    eingabe: dict[str, Any] | None,
    schwellen: dict[str, float],
) -> list[Signal]:
    juengste = _juengste_zeile(eintraege, "todo")
    return [
        signal_kennzahl_ueber(
            "todo",
            "Tote Links",
            juengste,
            "mail_links_tot",
            "todo.mail_links_tot",
            schwellen,
            "",
            "tote Links auf Vorgangsseiten — link_pruefen.py --vorgangsseiten",
        ),
        signal_kennzahl_ueber(
            "todo",
            "Ohne Kopf-Aktion",
            juengste,
            "ohne_kopf_aktion",
            "todo.ohne_kopf_aktion",
            schwellen,
            "",
            "Vorgaenge ohne Aktion in der Kopfzeile — todo_board.py build",
        ),
        _dienst_code_signal(
            "todo",
            "Dienst-Code (todo-board)",
            "todo-board.service",
            "tools/todo_board/todo_board.py",
            eingabe,
        ),
        _dienst_code_signal(
            "todo",
            "Dienst-Code (mail-links)",
            "mail-links.service",
            "tools/mail_agent/mail_link_server.py",
            eingabe,
        ),
        signal_journal_alter("todo", eintraege, schwellen),
    ]


# --- Sammeln, ausgeben ---------------------------------------------------


def sammeln(
    anwendung: str,
    journal_pfad: Path,
    eingabe: dict[str, Any] | None,
    schwellen: dict[str, float],
) -> list[Signal]:
    eintraege = (
        eingabe.get("journal", [])
        if eingabe is not None
        else _journal_lesen(journal_pfad)
    )
    if not isinstance(eintraege, list):
        eintraege = []
    signale: list[Signal] = []
    if anwendung in ("mailcheck", "alle"):
        signale += signale_mailcheck(eintraege, eingabe, schwellen)
    if anwendung in ("todo", "alle"):
        signale += signale_todo(eintraege, eingabe, schwellen)
    return signale


def _eingabe_lesen(wert: str) -> dict[str, Any]:
    try:
        geladen = json.loads(wert)
    except ValueError:
        pfad = Path(wert).expanduser()
        geladen = json.loads(pfad.read_text(encoding="utf-8"))
    if not isinstance(geladen, dict):
        raise SystemExit("FEHLER: --eingabe muss ein JSON-Objekt sein.")
    return geladen


def _schwellen_lesen(wert: str) -> dict[str, float]:
    geladen = _eingabe_lesen(wert)
    return {str(k): float(v) for k, v in geladen.items()}


def bericht(signale: list[Signal], als_json: bool) -> tuple[str, int, int]:
    warnungen = sum(1 for s in signale if s.zustand == "WARNUNG")
    nicht_pruefbar = sum(1 for s in signale if s.zustand == "nicht pruefbar")
    if als_json:
        text = json.dumps(
            {
                "signale": [s.as_dict() for s in signale],
                "warnungen": warnungen,
                "nicht_pruefbar": nicht_pruefbar,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return text, warnungen, nicht_pruefbar
    heute = date.today().isoformat()
    zeilen = [
        f"Verfallsmelder {heute}: {warnungen} Warnungen, {nicht_pruefbar} nicht pruefbar",
        "",
    ]
    zeilen += [s.zeile() for s in signale]
    return "\n".join(zeilen), warnungen, nicht_pruefbar


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0] if __doc__ else "")
    ap.add_argument(
        "--anwendung", choices=["mailcheck", "todo", "alle"], default="alle"
    )
    ap.add_argument("--journal", default=str(JOURNAL_DEFAULT))
    ap.add_argument(
        "--eingabe", help="Inline-JSON oder Pfad zu einer JSON-Datei (Tests)"
    )
    ap.add_argument(
        "--schwellen", help="Inline-JSON oder Pfad, ueberschreibt einzelne Schwellen"
    )
    ap.add_argument("--json", action="store_true", help="Ausgabe als JSON statt Zeilen")
    ap.add_argument(
        "--block", action="store_true", help="Exit 1 bei mindestens einer Warnung"
    )
    args = ap.parse_args()

    journal_pfad = Path(args.journal).expanduser()
    eingabe = _eingabe_lesen(args.eingabe) if args.eingabe else None
    schwellen = dict(SCHWELLEN_DEFAULT)
    if args.schwellen:
        schwellen.update(_schwellen_lesen(args.schwellen))

    signale = sammeln(args.anwendung, journal_pfad, eingabe, schwellen)
    text, warnungen, _nicht_pruefbar = bericht(signale, args.json)
    print(text)

    if args.block and warnungen > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
