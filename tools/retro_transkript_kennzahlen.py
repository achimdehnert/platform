#!/usr/bin/env python3
"""retro_transkript_kennzahlen.py — Transkript-Fakten für /session-retro Phase 1, deterministisch.

Warum es das gibt: In der Retro `session-retro-2026-09-14-apo-hub-kbiAvn-incr.md`
meldete der Sammler-Subagent für ein 2,3-MB-Transkript „0 Ablehnungen, 0 Fehlerläufe" —
tatsächlich waren es 4 und 7. Er hatte die JSONL-Struktur nicht verstanden und die
Null als Faktum gemeldet (Streichkandidat `retro-phase1-sammler-transkriptauswertung`,
Owner-Freigabe 2026-09-14). Transkript-Kennzahlen sind kommandobelegt: ein Skript
liefert sie reproduzierbar, ein Agent nur mit Glück.

Was es liest (Claude-Code-JSONL, ein Inhaltsblock je Zeile):
  - `type=assistant`, `content[].type=tool_use`  → Tool-Aufrufe je Name (id merken)
  - `type=user`, `content[].type=tool_result`    → über `tool_use_id` dem Aufruf zugeordnet:
        Ablehnung  = „Permission for this action was denied" (+ Reason)
        Fehler     = `is_error` ODER „Exit code N≠0" am Anfang ODER Traceback/`…Error:` im Text
                     (fängt auch Fehler mit `is_error: False`, z. B. Playwright-TimeoutError
                     hinter einer Pipe — die Lücke, die die Widerlegungsbahn benannte)
  - `type=user` mit Text (nicht `<…>`)            → Nutzer-Nachrichten
  - `type=assistant`, `content[].type=text`       → sichtbare Texte an den Nutzer
  - `type=attachment`, `attachment.type=silent_turn_reminder` → Hinweis „hasn't heard from you",
        mit Abstand bis zum nächsten sichtbaren Text

Positivkontrolle eingebaut: `--selbsttest` fährt eine Fixture mit je einem Fall jeder
Klasse; eine Null für eine Klasse im echten Lauf ist erst glaubwürdig, wenn der
Selbsttest sie findet.

Aufruf:
  python3 tools/retro_transkript_kennzahlen.py <transkript.jsonl> [--von ISO] [--bis ISO]
  python3 tools/retro_transkript_kennzahlen.py --selbsttest

stdlib-only. Gibt nie Secrets aus: Kommandos mit Passwort-/Token-Mustern werden geschwärzt.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime

_SECRET = re.compile(r"(PASSWORD|_PW\b|TOKEN|SECRET|API[_-]?KEY)", re.I)
_DENIAL = "Permission for this action was denied"
_EXIT = re.compile(r"^\s*Exit code ([1-9]\d*)")
_TRACE = re.compile(
    r"Traceback \(most recent call last\)|^\s*(?:\w+\.)*\w+Error: ", re.M
)


@dataclass
class Kennzahlen:
    aufrufe: dict[str, int] = field(default_factory=dict)
    ablehnungen: list[tuple[str, str, str, str]] = field(default_factory=list)
    fehler: list[tuple[str, str, str, str]] = field(default_factory=list)
    nutzer: list[tuple[str, str]] = field(default_factory=list)
    texte: list[str] = field(default_factory=list)
    reminder: list[str] = field(default_factory=list)


def _kurz(text: str, n: int) -> str:
    return " ".join(str(text).split())[:n]


def _ergebnis_text(inhalt) -> str:
    if isinstance(inhalt, str):
        return inhalt
    return " ".join(x.get("text", "") for x in (inhalt or []) if isinstance(x, dict))


def _im_fenster(ts: str, von: str | None, bis: str | None) -> bool:
    return (von is None or ts >= von) and (bis is None or ts <= bis)


def lies(zeilen, von: str | None = None, bis: str | None = None) -> Kennzahlen:
    k = Kennzahlen()
    aufrufe: dict[str, tuple[str, str]] = {}
    for zeile in zeilen:
        try:
            d = json.loads(zeile)
        except (json.JSONDecodeError, ValueError):
            continue
        ts = d.get("timestamp", "")
        if not _im_fenster(ts, von, bis):
            continue
        typ = d.get("type")
        if typ == "attachment":
            if (d.get("attachment") or {}).get("type") == "silent_turn_reminder":
                k.reminder.append(ts)
            continue
        inhalt = (d.get("message") or {}).get("content")
        if typ == "assistant" and isinstance(inhalt, list):
            for c in inhalt:
                if c.get("type") == "tool_use":
                    eingabe = c.get("input") or {}
                    kurz = eingabe.get("command") or eingabe.get("file_path") or ""
                    aufrufe[c.get("id", "")] = (c.get("name", "?"), str(kurz))
                    k.aufrufe[c.get("name", "?")] = (
                        k.aufrufe.get(c.get("name", "?"), 0) + 1
                    )
                elif c.get("type") == "text" and c.get("text", "").strip():
                    k.texte.append(ts)
        elif typ == "user":
            if isinstance(inhalt, str):
                if inhalt.strip() and not inhalt.lstrip().startswith("<"):
                    k.nutzer.append((ts, _kurz(inhalt, 200)))
                continue
            for c in inhalt or []:
                if c.get("type") == "text" and not c.get(
                    "text", ""
                ).lstrip().startswith("<"):
                    k.nutzer.append((ts, _kurz(c["text"], 200)))
                if c.get("type") != "tool_result":
                    continue
                text = _ergebnis_text(c.get("content"))
                name, kommando = aufrufe.get(c.get("tool_use_id", ""), ("?", ""))
                kommando = (
                    "<geschwärzt>" if _SECRET.search(kommando) else _kurz(kommando, 140)
                )
                if _DENIAL in text:
                    grund = re.search(r"Reason: \[([^\]]+)\]", text)
                    k.ablehnungen.append(
                        (ts, name, grund.group(1) if grund else "?", kommando)
                    )
                elif c.get("is_error") or _EXIT.match(text) or _TRACE.search(text):
                    k.fehler.append((ts, name, kommando, _kurz(text, 90)))
    return k


def _minuten(a: str, b: str) -> float:
    f = "%Y-%m-%dT%H:%M:%S"
    return (
        datetime.strptime(b[:19], f) - datetime.strptime(a[:19], f)
    ).total_seconds() / 60


def bericht(k: Kennzahlen) -> str:
    out = [
        f"Tool-Aufrufe: {dict(sorted(k.aufrufe.items()))}",
        "",
        f"Ablehnungen: {len(k.ablehnungen)}",
    ]
    out += [f"  {ts} | {n} | {g} | {c}" for ts, n, g, c in k.ablehnungen]
    out += ["", f"Fehlerläufe: {len(k.fehler)}"]
    out += [f"  {ts} | {n} | {c} | {r}" for ts, n, c, r in k.fehler]
    out += [
        "",
        f"Sichtbare Texte an den Nutzer: {len(k.texte)}",
        f"Silent-Reminder: {len(k.reminder)}",
    ]
    for ts in k.reminder:
        danach = next((t for t in k.texte if t > ts), None)
        abstand = (
            f"{_minuten(ts, danach):.1f} min bis Text {danach}"
            if danach
            else "kein Text danach"
        )
        out.append(f"  {ts} → {abstand}")
    out += ["", "Nutzer-Nachrichten:"] + [f"  {ts} | {t}" for ts, t in k.nutzer]
    return "\n".join(out)


_FIXTURE = [
    {
        "type": "user",
        "timestamp": "2026-01-01T10:00:00Z",
        "message": {"content": "los geht's"},
    },
    {
        "type": "assistant",
        "timestamp": "2026-01-01T10:00:01Z",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": "a",
                    "name": "Bash",
                    "input": {"command": "gh pr merge 1"},
                }
            ]
        },
    },
    {
        "type": "user",
        "timestamp": "2026-01-01T10:00:02Z",
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "a",
                    "content": "Permission for this action was denied by the classifier. Reason: [Merge Without Review].",
                }
            ]
        },
    },
    {
        "type": "assistant",
        "timestamp": "2026-01-01T10:00:03Z",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": "b",
                    "name": "Bash",
                    "input": {"command": "pytest"},
                }
            ]
        },
    },
    {
        "type": "user",
        "timestamp": "2026-01-01T10:00:04Z",
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "b",
                    "is_error": True,
                    "content": "Exit code 1\nFAILED",
                }
            ]
        },
    },
    {
        "type": "assistant",
        "timestamp": "2026-01-01T10:00:05Z",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": "c",
                    "name": "Bash",
                    "input": {"command": "python3 klick.py | cut -c1-9"},
                }
            ]
        },
    },
    {
        "type": "user",
        "timestamp": "2026-01-01T10:00:06Z",
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "c",
                    "is_error": False,
                    "content": "playwright._impl._errors.TimeoutError: Locator.click: Timeout",
                }
            ]
        },
    },
    {
        "type": "attachment",
        "timestamp": "2026-01-01T10:01:00Z",
        "attachment": {
            "type": "silent_turn_reminder",
            "text": "The user hasn't heard from you",
        },
    },
    {
        "type": "assistant",
        "timestamp": "2026-01-01T10:05:00Z",
        "message": {"content": [{"type": "text", "text": "Zwischenstand."}]},
    },
]


def selbsttest() -> int:
    k = lies(json.dumps(z) for z in _FIXTURE)
    pruefungen = {
        "Ablehnung": len(k.ablehnungen) == 1
        and k.ablehnungen[0][2] == "Merge Without Review",
        "Fehler is_error": any(r.startswith("Exit code 1") for *_, r in k.fehler),
        "Fehler ohne is_error": any("TimeoutError" in r for *_, r in k.fehler),
        "Silent-Reminder": k.reminder == ["2026-01-01T10:01:00Z"],
        "Sichtbarer Text": k.texte == ["2026-01-01T10:05:00Z"],
        "Nutzer-Nachricht": k.nutzer == [("2026-01-01T10:00:00Z", "los geht's")],
    }
    for name, ok in pruefungen.items():
        print(f"  {'✓' if ok else '✗'} {name}")
    return 0 if all(pruefungen.values()) else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("transkript", nargs="?")
    p.add_argument("--von")
    p.add_argument("--bis")
    p.add_argument("--selbsttest", action="store_true")
    a = p.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if not a.transkript:
        p.error("Transkript-Pfad oder --selbsttest angeben")
    with open(a.transkript, encoding="utf-8") as f:
        print(bericht(lies(f, a.von, a.bis)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
