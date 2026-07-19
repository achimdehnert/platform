#!/usr/bin/env python3
"""handover_refs.py — geteilter Parser für Issue-/PR-Referenzen in AGENT_HANDOVER.md.

Extrahiert aus den OFFENEN Abschnitten (`## Nächste Schritte`, `## Offene Punkte`,
englische Dialekt-Varianten) alle GitHub-Referenzen. Blockquote-Zeilen (`> …`)
werden übersprungen — dort leben die „Erledigt"-Blöcke, deren Referenzen
absichtlich geschlossen sind.

Konsumenten:
- scripts/checks/agent_handover_reconcile.py (Nightly-Reconciler, Stufe 1 read-only)
- geplant: agent_handover_sync_check.py (platform#1252, PR-Content-Sync-Gate) —
  denselben Parser nutzen, NICHT neu bauen.

Erkannte Referenz-Formen (längste zuerst, Spans dedupliziert):
- volle URL:      github.com/<owner>/<repo>/(issues|pull)/<n>
- owner/repo#N:   achimdehnert/platform#123
- repo#N:         shared-ci#20            (Owner = Default-Owner)
- nacktes #N:     #123                    (Owner/Repo = Default)

Bewusste Grenze (kein Silent Cap — der Reconciler meldet sie im Report):
Abschnitte wie „## 0. Aktuelle Prioritäten" mischen offene Prios mit
Verlaufs-Evidenz („#1009 gemergt") und würden massiv False-Positives liefern —
sie werden NICHT gescannt, bis es eine saubere Markup-Konvention dafür gibt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

OPEN_SECTION_RE = re.compile(
    r"^#{2,3}\s*(nächste schritte|offene punkte|next steps|open (tasks|items|points))",
    re.IGNORECASE,
)
HEADING_RE = re.compile(r"^(#{1,3})\s")

# Reihenfolge = Priorität; ein kombiniertes Muster, damit Spans nicht doppelt zählen.
REF_RE = re.compile(
    r"github\.com/(?P<u_owner>[\w.-]+)/(?P<u_repo>[\w.-]+)/(?:issues|pull)/(?P<u_num>\d+)"
    r"|(?<![\w/])(?P<s_owner>[A-Za-z0-9-]+)/(?P<s_repo>[\w.-]+)#(?P<s_num>\d+)"
    r"|(?<![\w/])(?P<r_repo>[A-Za-z0-9][\w.-]*)#(?P<r_num>\d+)"
    r"|(?<![\w/#])#(?P<b_num>\d+)\b"
)


@dataclass(frozen=True)
class Ref:
    owner: str
    repo: str
    number: int
    line_no: int  # 1-basiert, für Report-Verortung
    line: str


def open_section_lines(text: str) -> tuple[list[tuple[int, str]], list[str]]:
    """Liefert (Zeilen der offenen Abschnitte ohne Blockquotes, übersprungene Abschnitts-Titel)."""
    collected: list[tuple[int, str]] = []
    skipped_titles: list[str] = []
    in_open = False
    open_level = 0
    for i, line in enumerate(text.split("\n"), start=1):
        h = HEADING_RE.match(line)
        if h:
            level = len(h.group(1))
            if OPEN_SECTION_RE.match(line):
                in_open = True
                open_level = level
                continue
            if in_open and level <= open_level:
                in_open = False
            if not in_open and level <= 2 and not OPEN_SECTION_RE.match(line):
                skipped_titles.append(line.strip("# ").strip())
            continue
        if in_open and not line.lstrip().startswith(">"):
            collected.append((i, line))
    return collected, skipped_titles


def extract_refs(
    text: str, default_owner: str, default_repo: str
) -> tuple[list[Ref], list[str]]:
    """Alle Referenzen der offenen Abschnitte, dedupliziert nach (owner, repo, number)."""
    lines, skipped = open_section_lines(text)
    seen: set[tuple[str, str, int]] = set()
    refs: list[Ref] = []
    for line_no, line in lines:
        for m in REF_RE.finditer(line):
            if m.group("u_num"):
                owner, repo, num = m.group("u_owner"), m.group("u_repo"), m.group("u_num")
            elif m.group("s_num"):
                owner, repo, num = m.group("s_owner"), m.group("s_repo"), m.group("s_num")
            elif m.group("r_num"):
                owner, repo, num = default_owner, m.group("r_repo"), m.group("r_num")
            else:
                owner, repo, num = default_owner, default_repo, m.group("b_num")
            key = (owner, repo, int(num))
            if key in seen:
                continue
            seen.add(key)
            refs.append(Ref(owner, repo, int(num), line_no, line.strip()))
    return refs, skipped
