#!/usr/bin/env python3
"""migrations_additiv.py — Gate „nur additive Migrationen" vor einem autonomen Prod-Deploy.

platform#3804, Kriterium 7: „Vor jedem Start maschinell geprüft: nur additive
Migrationen (Prüfskript, Verstoß = Stopp)". Dieses Skript ist das Prüfskript.

Es vergleicht zwei Git-Stände eines Hub-Repos (laufender Prod-Stand → Kandidat)
und sieht sich jede Django-Migrationsdatei an, die dazwischen hinzukommt. Erlaubt
ist nur, was Schema und Daten ergänzt (ADDITIV). Alles andere — Feld oder Modell
entfernen, Typ ändern, umbenennen, freies SQL, Datenmigration per RunPython — ist
ein Verstoß: der Rückweg per Container-Rollback stellt den alten Code wieder her,
aber nicht die alte Datenbank. Geänderte oder gelöschte Alt-Migrationen sind
ebenfalls ein Verstoß (Historie wird nicht umgeschrieben).

Einzige Ausnahme (Owner-Entscheid RM, platform#3804): `RunPython` mit echtem
`reverse_code` und der Markerzeile `# migrations_additiv: ok — <Grund>` in der
Datei (siehe MARKER_RE). Der Grund wird im ADDITIV-Ergebnis mit ausgegeben.

Die Operationen werden per `ast` aus dem Quelltext gelesen, nicht per Import —
das Skript braucht kein Django und keine Settings des Hubs.

Usage:
  tools/migrations_additiv.py <repo-pfad> <von-ref> <bis-ref>

Exit 0 = additiv (auch ohne neue Migration), 1 = Verstoß (Liste auf stdout),
2 = Aufrufe-/Git-Fehler.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

MIGRATIONS_GLOB = "*/migrations/*.py"

#: Operationen, die nur hinzufügen. `AlterModelOptions` ändert Meta (ordering,
#: verbose_name) ohne Schema; `SeparateDatabaseAndState` wird an seinen
#: `database_operations` gemessen.
ADDITIV = frozenset(
    {
        "CreateModel",
        "AddField",
        "AddIndex",
        "AddConstraint",
        "AlterModelOptions",
        "AlterModelManagers",
        "SeparateDatabaseAndState",
    }
)

#: Operationen, die zwar in Migrationsdateien vorkommen, aber kein Op sind.
KEIN_OP = frozenset({"Migration", "swappable_dependency"})

#: Ausnahme für `RunPython` (platform#3804, Owner-Entscheid RM 2026-10-06): zulässig,
#: wenn (1) ein echter Rückweg angegeben ist (`reverse_code`, nicht `noop`) und
#: (2) die Datei diese Markerzeile trägt — der Autor erklärt die Additivität und
#: nennt den Grund, der im Diff und im Review steht. Beispiel:
#:   # migrations_additiv: ok — RLS-Policies anlegen, remove_rls hebt sie auf
MARKER_RE = re.compile(
    r"^#\s*migrations_additiv:\s*ok\s*[—–-]\s*(?P<grund>\S.*)$", re.M
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


def geaenderte_migrationen(repo: Path, von: str, bis: str) -> list[tuple[str, str]]:
    """[(status, pfad)] für Migrationsdateien zwischen `von` und `bis`.

    status: A (neu), M (geändert), D (gelöscht), R… (umbenannt).
    `__init__.py` zählt nicht.
    """
    raw = _git(repo, "diff", "--name-status", f"{von}..{bis}", "--", MIGRATIONS_GLOB)
    treffer = []
    for zeile in raw.splitlines():
        teile = zeile.split("\t")
        status, pfad = teile[0], teile[-1]
        if Path(pfad).name == "__init__.py":
            continue
        treffer.append((status, pfad))
    return treffer


def _op_name(node: ast.AST) -> str | None:
    """`migrations.AddField(...)` → "AddField"; sonst None."""
    if not isinstance(node, ast.Call):
        return None
    f = node.func
    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
        if f.value.id == "migrations":
            return f.attr
    return None


def _keyword(node: ast.Call, name: str) -> ast.AST | None:
    for kw in node.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _hat_rueckweg(node: ast.Call) -> bool:
    """`RunPython(code, reverse_code)` mit echtem Rückweg — `noop` zählt nicht."""
    rueck = node.args[1] if len(node.args) > 1 else _keyword(node, "reverse_code")
    if rueck is None:
        return False
    return not (isinstance(rueck, ast.Attribute) and rueck.attr == "noop")


def marker_grund(quelle: str) -> str | None:
    """Grund aus der Markerzeile `# migrations_additiv: ok — <Grund>`; None ohne Marker."""
    m = MARKER_RE.search(quelle)
    return m.group("grund").strip() if m else None


def verstoesse_in_quelle(quelle: str, pfad: str) -> list[str]:
    """Nicht-additive Operationen einer Migrationsdatei, als lesbare Zeilen.

    `RunPython` wird durchgelassen, wenn Rückweg und Markerzeile vorhanden sind
    (siehe MARKER_RE); fehlt eines, nennt der Befund, was fehlt.
    """
    baum = ast.parse(quelle, filename=pfad)
    befunde: list[str] = []
    grund = marker_grund(quelle)

    def besuche(node: ast.AST, kontext: str = "") -> None:
        name = _op_name(node)
        if name == "SeparateDatabaseAndState":
            # Nur die Datenbank-Seite zählt; `state_operations` berühren die DB nicht.
            db_ops = _keyword(node, "database_operations")
            if db_ops is not None:
                besuche(db_ops, " (in SeparateDatabaseAndState)")
            return
        if name == "RunPython":
            fehlt = []
            if not _hat_rueckweg(node):
                fehlt.append("reverse_code")
            if grund is None:
                fehlt.append("Markerzeile `# migrations_additiv: ok — <Grund>`")
            if fehlt:
                befunde.append(
                    f"{pfad}:{node.lineno}: RunPython{kontext} — fehlt: {', '.join(fehlt)}"
                )
        elif name is not None and name not in KEIN_OP and name not in ADDITIV:
            befunde.append(f"{pfad}:{node.lineno}: {name}{kontext}")
        for kind in ast.iter_child_nodes(node):
            besuche(kind, kontext)

    besuche(baum)
    return befunde


def pruefe(repo: Path, von: str, bis: str) -> tuple[list[str], list[str]]:
    """(Verstöße, zugelassene RunPython-Ausnahmen) zwischen zwei Ständen; Verstöße leer = additiv."""
    befunde: list[str] = []
    ausnahmen: list[str] = []
    for status, pfad in geaenderte_migrationen(repo, von, bis):
        if status != "A":
            befunde.append(
                f"{pfad}: Alt-Migration {status} — Historie wird nicht umgeschrieben"
            )
            continue
        quelle = _git(repo, "show", f"{bis}:{pfad}")
        neue_befunde = verstoesse_in_quelle(quelle, pfad)
        befunde.extend(neue_befunde)
        grund = marker_grund(quelle)
        if grund is not None and "RunPython" in quelle and not neue_befunde:
            ausnahmen.append(f"{pfad}: RunPython zugelassen — {grund}")
    return befunde, ausnahmen


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__.split("Usage:")[1].split("\n")[1].strip(), file=sys.stderr)
        return 2
    repo, von, bis = Path(argv[1]), argv[2], argv[3]
    try:
        befunde, ausnahmen = pruefe(repo, von, bis)
        neue = [p for s, p in geaenderte_migrationen(repo, von, bis) if s == "A"]
    except subprocess.CalledProcessError as e:
        print(f"git-Fehler: {e.stderr.strip()}", file=sys.stderr)
        return 2
    if befunde:
        print(
            f"VERSTOSS — {len(befunde)} nicht-additive Stelle(n) zwischen {von} und {bis}:"
        )
        for b in befunde:
            print(f"  {b}")
        return 1
    print(
        f"ADDITIV — {len(neue)} neue Migration(en) zwischen {von} und {bis}, keine Verstöße"
    )
    for a in ausnahmen:
        print(f"  {a}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
