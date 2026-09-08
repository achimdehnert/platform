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
    #: Stand der Owner im Text (volle URL oder `owner/repo#N`) — oder wurde er
    #: mangels Angabe angenommen (`repo#N`, blankes `#N`)?
    #:
    #: Die Unterscheidung entscheidet, ob eine spätere Abweichung ein **Befund**
    #: ist oder nur eine Annahme dieses Parsers. Gemessen 2026-08-16
    #: (platform#2006): vier Referenzen — `risk-hub#596`, `tax-hub#119`,
    #: `ttz-hub#28`, `frist-hub#117` — bekamen hier `achimdehnert` zugewiesen,
    #: obwohl die Repos in `iilgmbh`, `ttz-lif` bzw. `meiki-lra` liegen. Bei
    #: `frist-hub#117` stand die **richtige** URL direkt daneben; gelesen wurde
    #: nur der Label-Text. Ergebnis: vier 404 im Nightly, die wie ein
    #: Zugriffsproblem aussahen und ein Parser-Problem waren.
    owner_explizit: bool = True


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


def alle_refs(text: str, default_owner: str, default_repo: str) -> list[Ref]:
    """Referenzen aus dem GANZEN Text, nicht nur aus den offenen Abschnitten.

    Gebraucht vom Auslagerungs-Gate (platform#2974): dort ist die Frage nicht
    „was steht in den offenen Abschnitten", sondern „welche Referenz war vorher
    irgendwo in der Datei und ist jetzt nirgends mehr". Bewusst derselbe Parser —
    ein zweiter waere genau die Doppelung, vor der der Modul-Kopf warnt.
    """
    return _refs_aus_zeilen(
        list(enumerate(_ohne_linktext(text).splitlines(), 1)),
        default_owner,
        default_repo,
    )


#: `[#66](https://github.com/achimdehnert/robo-lab/issues/66)` enthaelt ZWEI Treffer:
#: das Label `#66` (Owner/Repo geraten) und die URL daneben (Owner/Repo gelesen).
#: Genau diese Verwechslung hat am 2026-08-16 vier falsche Owner erzeugt (s. `Ref`).
#: Fuer `alle_refs` faellt das Label weg — bewusst nur hier, damit der Nightly-Pfad
#: ueber `extract_refs` unveraendert bleibt.
_MD_LINK = re.compile(r"\[([^\]]*)\]\((https?://[^)\s]+)\)")


def _ohne_linktext(text: str) -> str:
    return _MD_LINK.sub(lambda m: m.group(2), text)


def extract_refs(
    text: str, default_owner: str, default_repo: str
) -> tuple[list[Ref], list[str]]:
    """Alle Referenzen der offenen Abschnitte, dedupliziert nach (owner, repo, number)."""
    lines, skipped = open_section_lines(text)
    return _refs_aus_zeilen(lines, default_owner, default_repo), skipped


def _refs_aus_zeilen(
    lines: list[tuple[int, str]], default_owner: str, default_repo: str
) -> list[Ref]:
    seen: set[tuple[str, str, int]] = set()
    refs: list[Ref] = []
    for line_no, line in lines:
        for m in REF_RE.finditer(line):
            explizit = True
            if m.group("u_num"):
                owner, repo, num = (
                    m.group("u_owner"),
                    m.group("u_repo"),
                    m.group("u_num"),
                )
            elif m.group("s_num"):
                owner, repo, num = (
                    m.group("s_owner"),
                    m.group("s_repo"),
                    m.group("s_num"),
                )
            elif m.group("r_num"):
                owner, repo, num = default_owner, m.group("r_repo"), m.group("r_num")
                explizit = False  # `repo#N` — der Owner ist geraten, nicht gelesen
            else:
                owner, repo, num = default_owner, default_repo, m.group("b_num")
                explizit = False  # blankes `#N` — Owner UND Repo sind Annahme
            key = (owner, repo, int(num))
            if key in seen:
                continue
            seen.add(key)
            refs.append(Ref(owner, repo, int(num), line_no, line.strip(), explizit))
    return refs
