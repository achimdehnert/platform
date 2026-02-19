"""
agents/adr_scribe.py — ADR Scribe (Agent A3)

Generiert ADR-Drafts aus Problem-Beschreibungen:
  - Nächste freie ADR-Nummer ermitteln
  - 8-Sektionen-Format (Frontmatter + Body)
  - Kontext aus bestehenden ADRs einbeziehen
  - Optionen-Tabelle generieren

Nutzung:
  python -m agents.adr_scribe --problem "Wir brauchen Background-Jobs"
  python -m agents.adr_scribe --problem "..." --project travel-beat
  python -m agents.adr_scribe --problem "..." --context "Celery vs RQ"

Gate-Integration:
  ADR Draft → Gate 2 (APPROVE — Mensch reviewed vor Commit)
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("adr_scribe")

PROJECTS = [
    "platform", "travel-beat", "bfagent",
    "mcp-hub", "risk-hub", "weltenhub", "pptx-hub",
]

ADR_TEMPLATE = """\
---
id: ADR-{number:03d}
title: \"{title}\"
status: PROPOSED
created: {date}
author: {author}
review: Governance Board \u2013 ausstehend
supersedes: {supersedes}
related: [{related}]
tags: [{tags}]
llm_context_weight: medium
---

# ADR-{number:03d} \u2013 {title}

## Status

`PROPOSED` \u2192 Governance Review ausstehend

## 1. Kontext & Problem

{problem}

{context}

## 2. Entscheidungstreiber

{drivers}

## 3. Betrachtete Optionen

{options_table}

## 4. Entscheidung

**Gew\u00e4hlte Option: [TBD \u2014 nach Review ausf\u00fcllen]**

Begr\u00fcndung: [Wird im Governance-Review erg\u00e4nzt]

## 5. Konsequenzen

### Positiv

- [Wird im Review erg\u00e4nzt]

### Negativ

- [Wird im Review erg\u00e4nzt]

## 6. Implementierungsplan

| Phase | Aufgabe | Dauer |
|-------|---------|-------|
| 1 | [TBD] | [TBD] |

## 7. Erfolgsmetriken

| Kriterium | Zielwert | Messung |
|-----------|----------|---------|u
| [TBD] | [TBD] | [TBD] |

## 8. Referenzen

{references}
"""


@dataclass
class AdrContext:
    """Kontext f\u00fcr ADR-Generierung."""

    problem: str
    project: str | None = None
    context: str | None = None
    author: str = "Platform Team"
    related_adrs: list[str] = field(default_factory=list)
    supersedes: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class AdrDraft:
    """Generierter ADR-Draft."""

    number: int
    title: str
    filename: str
    content: str
    gate: int = 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "filename": self.filename,
            "gate": self.gate,
            "content_length": len(self.content),
        }


def find_next_adr_number(adr_dir: Path) -> int:
    """Ermittelt die n\u00e4chste freie ADR-Nummer."""
    existing: list[int] = []
    if adr_dir.exists():
        for f in adr_dir.glob("ADR-*.md"):
            match = re.search(r"ADR-(\d+)", f.name)
            if match:
                existing.append(int(match.group(1)))

    if not existing:
        return 1

    return max(existing) + 1


def find_related_adrs(
    adr_dir: Path,
    keywords: list[str],
) -> list[str]:
    """Sucht bestehende ADRs die thematisch verwandt sind."""
    related: list[str] = []
    if not adr_dir.exists():
        return related

    for f in sorted(adr_dir.glob("ADR-*.md")):
        try:
            text = f.read_text(encoding="utf-8")[:500].lower()
            if any(kw.lower() in text for kw in keywords):
                match = re.search(r"ADR-(\d+)", f.name)
                if match:
                    related.append(f"ADR-{match.group(1)}")
        except (OSError, UnicodeDecodeError):
            continue

    return related[:5]


def slugify(text: str) -> str:
    """Erzeugt einen URL-freundlichen Slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text[:60].rstrip("-")


def generate_title(problem: str) -> str:
    """Extrahiert einen kurzen Titel aus der Problembeschreibung."""
    problem = problem.strip().rstrip(".")
    if len(problem) <= 60:
        return problem

    words = problem.split()
    title = ""
    for word in words:
        if len(title) + len(word) + 1 > 60:
            break
        title = f"{title} {word}" if title else word

    return title


def extract_keywords(text: str) -> list[str]:
    """Extrahiert Schl\u00fcsselw\u00f6rter aus Text."""
    stop_words = {
        "wir", "brauchen", "eine", "einen", "ein", "der",
        "die", "das", "f\u00fcr", "und", "oder", "mit", "ohne",
        "ist", "sind", "wird", "werden", "soll", "sollte",
        "muss", "m\u00fcssen", "kann", "k\u00f6nnen", "hat", "haben",
        "we", "need", "the", "a", "an", "for", "and", "or",
        "with", "without", "is", "are", "will", "should",
        "must", "can", "has", "have", "not", "but", "from",
    }
    words = re.findall(r"\b\w{3,}\b", text.lower())
    return [w for w in words if w not in stop_words][:10]


def generate_options_table(problem: str) -> str:
    """Erzeugt eine Optionen-Tabelle als Platzhalter."""
    return (
        "| Option | Beschreibung | Vor-/Nachteile |\n"
        "|--------|-------------|----------------|\n"
        "| Option A | [Beschreibung] | + [Pro] / - [Contra] |\n"
        "| Option B | [Beschreibung] | + [Pro] / - [Contra] |\n"
        "| Option C (Status Quo) | Keine \u00c4nderung | "
        "+ Kein Aufwand / - Problem bleibt |\n"
    )


def generate_drivers(problem: str) -> str:
    """Erzeugt Standard-Entscheidungstreiber."""
    return (
        "- Bestehende Platform-Architektur ber\u00fccksichtigen "
        "(ADR-009, ADR-040)\n"
        "- Minimaler Aufwand, maximaler Nutzen\n"
        "- Kompatibilit\u00e4t mit Multi-Tenant-Architektur "
        "(Prinzip P-003)\n"
        "- Wartbarkeit und Testbarkeit\n"
        "- Kosten-Effizienz"
    )


def generate_adr(
    ctx: AdrContext,
    adr_dir: Path,
) -> AdrDraft:
    """Generiert einen vollst\u00e4ndigen ADR-Draft."""
    number = find_next_adr_number(adr_dir)
    title = generate_title(ctx.problem)
    slug = slugify(title)
    filename = f"ADR-{number:03d}-{slug}.md"

    keywords = extract_keywords(ctx.problem)
    if ctx.context:
        keywords.extend(extract_keywords(ctx.context))

    related = ctx.related_adrs or find_related_adrs(
        adr_dir, keywords,
    )

    tags = ctx.tags or keywords[:5]
    if ctx.project:
        tags.insert(0, ctx.project)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    context_section = ""
    if ctx.context:
        context_section = (
            f"### Zus\u00e4tzlicher Kontext\n\n{ctx.context}"
        )
    if ctx.project:
        context_section += (
            f"\n\n**Betroffenes Projekt:** {ctx.project}"
        )

    references = "\n".join(
        f"- [{adr}](./{adr}.md)" for adr in related
    )
    if not references:
        references = (
            "- [ADR-050](./ADR-050.md) \u2014 "
            "Enterprise Knowledge System\n"
            "- [ADR-009](./ADR-009.md) \u2014 "
            "Platform Architecture"
        )

    content = ADR_TEMPLATE.format(
        number=number,
        title=title,
        date=today,
        author=ctx.author,
        supersedes=ctx.supersedes or "~",
        related=", ".join(related) if related else "",
        tags=", ".join(tags),
        problem=ctx.problem,
        context=context_section,
        drivers=generate_drivers(ctx.problem),
        options_table=generate_options_table(ctx.problem),
        references=references,
    )

    logger.info(
        "Generated ADR-%03d: %s (%d chars)",
        number, title, len(content),
    )

    return AdrDraft(
        number=number,
        title=title,
        filename=filename,
        content=content,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ADR Scribe \u2014 ADR-Draft Generator",
    )
    parser.add_argument(
        "--problem", type=str, required=True,
        help="Problem-Beschreibung (1-3 S\u00e4tze)",
    )
    parser.add_argument(
        "--project", type=str, default=None,
        choices=PROJECTS,
        help="Betroffenes Projekt",
    )
    parser.add_argument(
        "--context", type=str, default=None,
        help="Zus\u00e4tzlicher Kontext",
    )
    parser.add_argument(
        "--author", type=str, default="Platform Team",
        help="ADR-Autor",
    )
    parser.add_argument(
        "--adr-dir", type=str, default="docs/adr",
        help="Verzeichnis mit bestehenden ADRs",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Output-Verzeichnis (default: adr-dir)",
    )
    parser.add_argument(
        "--format", choices=["markdown", "json"],
        default="markdown",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Draft generieren aber nicht speichern",
    )
    args = parser.parse_args()

    adr_dir = Path(args.adr_dir)
    output_dir = (
        Path(args.output_dir) if args.output_dir else adr_dir
    )

    ctx = AdrContext(
        problem=args.problem,
        project=args.project,
        context=args.context,
        author=args.author,
    )

    draft = generate_adr(ctx, adr_dir)

    if args.format == "json":
        print(json.dumps(draft.to_dict(), indent=2))
    else:
        print(draft.content)

    if not args.dry_run and output_dir.exists():
        out_path = output_dir / draft.filename
        out_path.write_text(draft.content, encoding="utf-8")
        logger.info("Written to %s", out_path)

    sys.exit(0)


if __name__ == "__main__":
    main()
