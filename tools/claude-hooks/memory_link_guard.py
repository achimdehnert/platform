#!/usr/bin/env python3
"""Stop-Hook: meldet kaputte Memory-Verweise in dem Zug, der sie erzeugt hat.

Warum Stop und nicht SessionStart
---------------------------------
Memory-Schaden entsteht beim **Schreiben**, nicht beim Starten. Realfall
2026-07-31: eine parallel laufende Sitzung schrieb um 15:10 ein Memory mit einem
Verweis auf einen Namen, der um 10:43 zusammengelegt worden war. Ein
SessionStart-Hook hätte in jener Sitzung kurz vor 15:00 gefeuert — also *bevor*
der schlechte Verweis existierte — und danach geschwiegen. Gefunden wurde es
zwei Stunden später nur durch einen Lauf von Hand.

Vorbedingung statt Dauerlauf
----------------------------
833 Dateien nach jeder Antwort zu scannen wäre Verschwendung. Der Hook prüft
zuerst per ``git status``, ob dieser Zug überhaupt unter ``projects/*/memory/``
geschrieben hat — möglich, seit das Verzeichnis versioniert ist. Ist dort nichts
offen, endet er nach einem git-Aufruf. Bewusst ``git status`` und nicht mtime:
mtime ändert sich auch ohne Inhaltsänderung (siehe Memory ``mtime_not_dirty``).

Seit 2026-09-02 kommt eine zweite, ebenso billige Vorbedingung dazu: der
Inhalts-Fingerabdruck der offenen Dateien. ``git status`` sagt nur, dass dort
*etwas* offen ist — nicht, dass dieser Zug es verändert hat. Solange eine
Memory-Änderung uncommitted liegen blieb, lief der teure Prüfer deshalb bei
JEDEM Stop erneut (gemessen: 698 ms je Stop, davon 13 ms git und ~685 ms
Prüfer). Ist der Abdruck unverändert, ist auch der Befund unverändert und war
beim ersten Mal schon gemeldet — der Lauf entfällt, ohne einen Fund zu
verlieren.

Vertrag: Stop-Event-JSON auf stdin, **immer Exit 0** — ein Melder darf nie
blockieren. Funde gehen als ``hookSpecificOutput.additionalContext`` nach stdout.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

PROJEKTE = Path.home() / ".claude" / "projects"
CLAUDE_REPO = Path.home() / ".claude"
PRUEFER = Path(__file__).with_name("memory_link_check.py")


def geaenderte_memory_dirs() -> tuple[list[Path], set[str]]:
    """Memory-Verzeichnisse mit offenen Änderungen und die geänderten Dateinamen.

    Zwei Rückgabewerte, weil das Prüfwerkzeug immer ein ganzes Verzeichnis liest:
    die Verzeichnisliste sagt, **wo** geprüft wird, die Dateinamen sagen, **was
    dieser Zug angefasst hat**. Ohne die zweite Menge meldet der Melder Funde in
    fremden Dateien als „dieser Zug hat sie erzeugt" — das ist falsch und war der
    Anlass für diese Änderung (Realfall 2026-08-02: 8 Funde in 3 Dateien, die der
    meldende Zug nie geöffnet hatte).
    """
    try:
        roh = subprocess.run(
            ["git", "-C", str(CLAUDE_REPO), "status", "--porcelain", "--", "projects/"],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return [], set()
    if roh.returncode != 0:
        return [], set()

    dirs: set[Path] = set()
    dateien: set[str] = set()
    for zeile in roh.stdout.splitlines():
        # Format: "XY <pfad>"; bei Umbenennung "XY alt -> neu"
        pfad = zeile[3:].split(" -> ")[-1].strip().strip('"')
        teile = Path(pfad).parts
        if "memory" not in teile:
            continue
        idx = teile.index("memory")
        dirs.add(CLAUDE_REPO.joinpath(*teile[: idx + 1]))
        if len(teile) > idx + 1:
            dateien.add(teile[-1])
    return sorted(d for d in dirs if d.is_dir()), dateien


def pruefe(dirs: list[Path], geaendert: set[str]) -> tuple[list[str], int]:
    """Harte Funde als Meldezeilen — getrennt nach angefasst und fremd.

    Rückgabe: (Zeilen zu Dateien, die dieser Zug geschrieben hat; Anzahl der
    übrigen harten Funde). Die fremden werden gezählt, nicht verschwiegen — sonst
    verschwände Bestandsschuld lautlos, sobald der Melder ehrlicher wird.
    """
    eigene: list[str] = []
    fremd = 0
    for d in dirs:
        try:
            lauf = subprocess.run(
                [sys.executable, str(PRUEFER), "--root", str(d), "--json"],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if lauf.returncode == 2:  # Werkzeugfehler, kein Befund
            continue
        try:
            bericht = json.loads(lauf.stdout)
        except json.JSONDecodeError:
            continue
        for det in bericht.get("details", []):
            for f in det.get("funde", []):
                if f.get("art") == "forward-ref":
                    continue
                if f.get("datei") in geaendert:
                    eigene.append(f"  {f['art']:<15} {f['datei']:<52} {f['detail']}")
                else:
                    fremd += 1
    return eigene, fremd


def _abdruck(dirs: list[Path], geaendert: set[str]) -> str:
    """Inhalts-Fingerabdruck der offenen Memory-Aenderungen.

    Gehasht wird der INHALT der offenen Dateien, nicht ihre mtime — eine
    Beruehrung ohne Aenderung darf den Pruefer nicht erneut anwerfen, eine
    Aenderung muss ihn zwingend anwerfen (Memory `mtime_not_dirty`).
    """
    h = hashlib.sha256()
    for d in dirs:
        h.update(str(d).encode("utf-8", "replace") + b"\0")
        for name in sorted(geaendert):
            p = d / name
            h.update(name.encode("utf-8", "replace") + b"\0")
            try:
                h.update(p.read_bytes())
            except OSError:
                h.update(b"<weg>")
            h.update(b"\0")
    return h.hexdigest()


def _abdruck_datei(session_id: str) -> Path:
    return Path(tempfile.gettempdir()) / f"memory_link_guard_{session_id or 'na'}.txt"


def main() -> int:
    # Der Client verlangt hookSpecificOutput.hookEventName ("Stop"|"SubagentStop");
    # ohne das Feld verwirft er die Ausgabe und zeigt den rohen Schema-Dump.
    event = "Stop"
    daten: dict = {}
    try:
        roh = json.load(sys.stdin)
        if isinstance(roh, dict):
            daten = roh
            if daten.get("hook_event_name") == "SubagentStop":
                event = "SubagentStop"
    except (json.JSONDecodeError, ValueError):
        pass

    if not PRUEFER.is_file():
        return 0

    dirs, geaendert = geaenderte_memory_dirs()
    if not dirs:
        return 0

    # Entprellung gegen den Inhalt, nicht gegen die Zeit.
    #
    # `git status` ist der billige Teil (gemessen 2026-09-02: 13 ms). Teuer ist
    # der Pruefer dahinter: er liest je Verzeichnis den GESAMTEN Bestand, und er
    # lief bisher bei JEDEM Stop, solange unter `projects/*/memory/` irgendetwas
    # offen war — auch in Zuegen, die dort nichts geschrieben haben. Am realen
    # Bestand gemessen: 698 ms je Stop, davon ~685 ms Pruefer.
    #
    # Bewusst NICHT ueber Werkzeug-Evidenz des Turns gefiltert: eine Memory-Datei
    # kann auch aus einer Bash-Zeile oder einem Unteragenten entstehen, und ein
    # solcher Filter haette genau diese Faelle blind gemacht. Der Inhalts-Hash
    # verliert dagegen keinen einzigen Fund: aendert sich eine offene Datei,
    # aendert sich der Abdruck und der Pruefer laeuft. Bleibt alles gleich, ist
    # auch der Befund derselbe — und wurde beim ersten Mal schon gemeldet.
    abdruck = _abdruck(dirs, geaendert)
    merker = _abdruck_datei(str(daten.get("session_id", "")))
    try:
        if merker.read_text(encoding="utf-8").strip() == abdruck:
            return 0
    except OSError:
        pass
    try:
        merker.write_text(abdruck, encoding="utf-8")
    except OSError:
        pass  # Merker-Verlust heisst schlimmstenfalls ein Lauf mehr — nie blocken

    eigene, fremd = pruefe(dirs, geaendert)
    if not eigene:
        return 0

    nachsatz = ""
    if fremd:
        nachsatz = (
            f"\n\nAusserdem {fremd} harte(r) Fund(e) in Dateien, die dieser Zug "
            "NICHT angefasst hat — Bestandsschuld, nicht deine. Aufraeumen ja, "
            "aber als eigene Aufgabe."
        )

    text = (
        "⚠️ memory-link-guard: dieser Zug hat Memory-Dateien geschrieben und "
        f"dabei {len(eigene)} harte(n) Verweis-Fund erzeugt:\n"
        + "\n".join(eigene)
        + "\n\nEin toter Verweis entsteht meist, weil ein Ziel unter seinem "
        "Frontmatter-Namen statt seinem Dateinamen genannt wurde, oder weil das "
        "Ziel zusammengelegt/umbenannt wurde. Vorausschauende Verweise gehören "
        "in tools/claude-hooks/memory_forward_refs.tsv, nicht in die Prosa. "
        "Jetzt im selben Zug korrigieren." + nachsatz
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": event,
                    "additionalContext": text,
                }
            }
        )
    )
    return 0


def main_sicher() -> int:
    """`main()` unter dem Hook-Vertrag: Exit 0 immer, ausser bewusstes Blocken.

    Siehe `evidence_claim_scanner.main_sicher` fuer die Begruendung; bewusst
    dupliziert statt geteilt, damit der Auffangbogen keinen Import braucht.
    """
    try:
        return main()
    except Exception as exc:  # noqa: BLE001 — Hook-Vertrag: nie blockieren
        print(f"memory_link_guard: {type(exc).__name__}: {exc}"[:400], file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main_sicher())
