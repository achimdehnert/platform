# ADR-011: Centralized ADR Management & Repository Hygiene

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-02-03 |
| **Author** | Achim Dehnert |
| **Reviewers** | — |
| **Supersedes** | — |
| **Related** | ADR-009 (Deployment Architecture) |

---

## 1. Executive Summary

Dieses ADR etabliert eine **zentrale ADR-Verwaltung** für die gesamte BF Agent Platform. Alle Architecture Decision Records – unabhängig davon, welche App sie betreffen – werden im **Platform-Repository** verwaltet. Dies gewährleistet eine Single Source of Truth, konsistente Nummerierung und vereinfachte Wartung.

**Kernprinzipien:**
1. **Ein Repository für alle ADRs** → `platform/docs/adr/`
2. **Strukturierung nach Scope** → Unterordner pro App/Bereich
3. **Reservierte Nummernkreise** → Eindeutige IDs ohne Konflikte
4. **Automatisierte Hygiene** → CI-Checks und Index-Generierung

---

## 2. Context

### 2.1 Aktuelle Situation

Die BF Agent Platform besteht aus mehreren Repositories:

| Repository | Beschreibung | ADRs aktuell |
|------------|--------------|--------------|
| `platform` | Core-Infrastruktur, Shared Packages | Ja (verstreut) |
| `bfagent` | BF Agent Anwendung | Keine/Wenige |
| `travel-beat` | Travel-Beat Anwendung | Keine/Wenige |
| `mcp-hub` | MCP Server Registry | Keine |
| `risk-hub` | Risk Assessment | Keine |
| `cad-hub` | CAD Integration | Keine |
| `pptx-hub` | PowerPoint Generation | Keine |

### 2.2 Probleme mit dezentralen ADRs

| Problem | Impact |
|---------|--------|
| **Fragmentierung** | ADRs verstreut über 7 Repos, schwer zu finden |
| **Nummernkonflikte** | Jedes Repo hätte ADR-001, ADR-002, etc. |
| **Inkonsistente Reviews** | Verschiedene Standards pro Repo |
| **Cross-Referenzen** | Schwer zwischen Repos zu verlinken |
| **Duplikate** | Gleiche Entscheidung in mehreren Repos dokumentiert |
| **Wartungsaufwand** | 7x Hygiene-Scripts, 7x CI-Pipelines |
| **Onboarding** | "Wo finde ich die Architektur-Entscheidungen?" |

### 2.3 Ziele

| Ziel | Messbar |
|------|---------|
| Alle ADRs an einem Ort | 100% in `platform/docs/adr/` |
| Eindeutige Nummerierung | Keine Duplikate |
| Automatischer Index | Generiert, filterbar nach Scope |
| Klare Triage-Regeln | Entscheidungsbaum dokumentiert |
| Konsistente Reviews | Ein Review-System für alle |

---

## 3. Decision

### 3.1 Zentralisierte Struktur

**Alle ADRs werden im Platform-Repository verwaltet:**

```
platform/
└── docs/
    └── adr/
        ├── README.md                    # Auto-generierter Master-Index
        ├── TEMPLATE.md                  # ADR Template
        ├── TRIAGE.md                    # Entscheidungshilfe: Welcher Ordner?
        │
        ├── drafts/                      # Neue ADRs (noch nicht reviewed)
        │   └── ADR-DRAFT-xxx.md
        │
        ├── core/                        # Platform-Core (001-019)
        │   ├── ADR-001-initial-architecture.md
        │   ├── ADR-009-deployment-architecture.md
        │   ├── ADR-011-centralized-adr-management.md  ← Dieses ADR
        │   └── ...
        │
        ├── bfagent/                     # BF Agent App (020-029)
        │   ├── ADR-020-agent-lifecycle.md
        │   └── ...
        │
        ├── travel-beat/                 # Travel-Beat App (030-039)
        │   ├── ADR-030-story-generation.md
        │   └── ...
        │
        ├── mcp-hub/                     # MCP Hub (040-049)
        │   └── ...
        │
        ├── risk-hub/                    # Risk Hub (050-059)
        │   └── ...
        │
        ├── cad-hub/                     # CAD Hub (060-069)
        │   └── ...
        │
        ├── pptx-hub/                    # PPTX Hub (070-079)
        │   └── ...
        │
        ├── shared/                      # Cross-App / Shared (080-099)
        │   ├── ADR-080-authentication-strategy.md
        │   └── ...
        │
        └── _archive/                    # Superseded/Deprecated/Rejected
            ├── README.md
            ├── core/
            ├── bfagent/
            └── ...
```

### 3.2 Nummernkreise

| Scope | Nummernkreis | Kapazität | Beschreibung |
|-------|--------------|-----------|--------------|
| **Core/Platform** | 001-019 | 19 | Infrastruktur, CI/CD, DB, Deployment |
| **BF Agent** | 020-029 | 10 | Agent-spezifische Entscheidungen |
| **Travel-Beat** | 030-039 | 10 | Story/Content Generation |
| **MCP-Hub** | 040-049 | 10 | MCP Server, Registry |
| **Risk-Hub** | 050-059 | 10 | Risk Assessment, Scoring |
| **CAD-Hub** | 060-069 | 10 | CAD Import/Export |
| **PPTX-Hub** | 070-079 | 10 | PowerPoint Generation |
| **Shared/Cross-App** | 080-099 | 20 | Auth, API-Conventions, Logging |
| **Reserve** | 100-199 | 100 | Neue Apps, Erweiterungen |

**Dateinamenskonvention:**
```
ADR-{NNN}-{kebab-case-title}.md

Beispiele:
- ADR-009-deployment-architecture.md     (Core)
- ADR-025-tool-execution-model.md        (BF Agent)
- ADR-033-timing-engine-v2.md            (Travel-Beat)
- ADR-085-api-versioning-strategy.md     (Shared)
```

### 3.3 ADR Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ADR LIFECYCLE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   1. DRAFT                                                                   │
│      ┌──────────────────────────────────────────┐                           │
│      │ Location: drafts/ADR-DRAFT-xxx.md        │                           │
│      │ • Jeder kann Draft erstellen             │                           │
│      │ • Noch keine Nummer zugewiesen           │                           │
│      │ • Template ausfüllen                     │                           │
│      └─────────────────┬────────────────────────┘                           │
│                        │                                                     │
│                        ▼                                                     │
│   2. TRIAGE (Scope bestimmen)                                               │
│      ┌──────────────────────────────────────────┐                           │
│      │ Fragen:                                  │                           │
│      │ • Welche Apps sind betroffen?            │                           │
│      │ • Ist es Infrastruktur/Core?             │                           │
│      │ • Betrifft es mehrere Apps? → shared/    │                           │
│      │                                          │                           │
│      │ → Nächste freie Nummer aus Nummernkreis  │                           │
│      │ → Verschieben in richtigen Ordner        │                           │
│      └─────────────────┬────────────────────────┘                           │
│                        │                                                     │
│                        ▼                                                     │
│   3. PROPOSED                                                                │
│      ┌──────────────────────────────────────────┐                           │
│      │ Location: {scope}/ADR-{NNN}-xxx.md       │                           │
│      │ Status: Proposed                         │                           │
│      │ • PR erstellen                           │                           │
│      │ • AI-Review (automatisch)                │                           │
│      │ • Team-Review                            │                           │
│      └─────────────────┬────────────────────────┘                           │
│                        │                                                     │
│           ┌───────────┴───────────┐                                         │
│           ▼                       ▼                                         │
│   4a. ACCEPTED               4b. REJECTED                                   │
│      ┌──────────────┐           ┌──────────────┐                           │
│      │ Status:      │           │ Location:    │                           │
│      │ Accepted     │           │ _archive/    │                           │
│      │              │           │ {scope}/     │                           │
│      │ Implementie- │           │              │                           │
│      │ rung startet │           │ Status:      │                           │
│      └──────┬───────┘           │ Rejected     │                           │
│             │                   └──────────────┘                           │
│             │                                                               │
│             ▼                                                               │
│   5. SUPERSEDED / DEPRECATED                                                │
│      ┌──────────────────────────────────────────┐                           │
│      │ Wenn neue Entscheidung die alte ersetzt: │                           │
│      │ • Status → Superseded by ADR-XXX         │                           │
│      │ • Verschieben nach _archive/{scope}/     │                           │
│      │                                          │                           │
│      │ Wenn nicht mehr relevant:                │                           │
│      │ • Status → Deprecated                    │                           │
│      │ • Verschieben nach _archive/{scope}/     │                           │
│      └──────────────────────────────────────────┘                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.4 Triage-Entscheidungsbaum

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TRIAGE: WELCHER SCOPE?                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  START: Neues ADR                                                           │
│    │                                                                         │
│    ▼                                                                         │
│  ┌─────────────────────────────────────┐                                    │
│  │ Betrifft es Infrastruktur?          │                                    │
│  │ (CI/CD, Deployment, DB-Schema,      │                                    │
│  │  Monitoring, Security)              │                                    │
│  └─────────────┬───────────────────────┘                                    │
│                │                                                             │
│       Ja ──────┴────── Nein                                                 │
│        │                 │                                                   │
│        ▼                 ▼                                                   │
│   ┌─────────┐    ┌─────────────────────────────┐                            │
│   │  core/  │    │ Betrifft es mehrere Apps?   │                            │
│   │ 001-019 │    │ (≥2 Apps oder shared code)  │                            │
│   └─────────┘    └─────────────┬───────────────┘                            │
│                                │                                             │
│                       Ja ──────┴────── Nein                                 │
│                        │                 │                                   │
│                        ▼                 ▼                                   │
│                   ┌─────────┐    ┌─────────────────────┐                    │
│                   │ shared/ │    │ Welche App ist      │                    │
│                   │ 080-099 │    │ primär betroffen?   │                    │
│                   └─────────┘    └─────────┬───────────┘                    │
│                                            │                                 │
│                    ┌───────────────────────┼───────────────────────┐        │
│                    │           │           │           │           │        │
│                    ▼           ▼           ▼           ▼           ▼        │
│               ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐       │
│               │bfagent/│ │travel- │ │mcp-hub/│ │risk-   │ │ ...    │       │
│               │020-029 │ │beat/   │ │040-049 │ │hub/    │ │        │       │
│               └────────┘ │030-039 │ └────────┘ │050-059 │ └────────┘       │
│                          └────────┘            └────────┘                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.5 Scope-Definitionen

| Scope | Ordner | Kriterien | Beispiele |
|-------|--------|-----------|-----------|
| **Core** | `core/` | Infrastruktur, Platform-weit, alle Apps betroffen | Deployment, CI/CD, DB-Strategie, Monitoring |
| **BF Agent** | `bfagent/` | Nur BF Agent Anwendung | Agent Lifecycle, Tool Execution, Memory |
| **Travel-Beat** | `travel-beat/` | Nur Travel-Beat Anwendung | Story Generation, Timing Engine, Content |
| **MCP-Hub** | `mcp-hub/` | Nur MCP Hub | Server Registry, Protocol Extensions |
| **Risk-Hub** | `risk-hub/` | Nur Risk Hub | Risk Scoring, Assessment Models |
| **CAD-Hub** | `cad-hub/` | Nur CAD Hub | CAD Import, Format Conversion |
| **PPTX-Hub** | `pptx-hub/` | Nur PPTX Hub | Slide Generation, Templates |
| **Shared** | `shared/` | ≥2 Apps, aber nicht Infrastruktur | Auth, API Conventions, Logging Format |

---

## 4. Implementation

### 4.1 Ordnerstruktur erstellen

```bash
#!/bin/bash
# scripts/setup-adr-structure.sh

ADR_ROOT="docs/adr"

# Hauptordner
mkdir -p "$ADR_ROOT"/{drafts,core,bfagent,travel-beat,mcp-hub,risk-hub,cad-hub,pptx-hub,shared,_archive}

# Archive-Unterordner
mkdir -p "$ADR_ROOT/_archive"/{core,bfagent,travel-beat,mcp-hub,risk-hub,cad-hub,pptx-hub,shared}

# .gitkeep für leere Ordner
find "$ADR_ROOT" -type d -empty -exec touch {}/.gitkeep \;

echo "✅ ADR structure created"
```

### 4.2 ADR Template

```markdown
<!-- docs/adr/TEMPLATE.md -->
# ADR-{NNN}: {Title}

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | {YYYY-MM-DD} |
| **Author** | {Name} |
| **Scope** | {core/bfagent/travel-beat/mcp-hub/risk-hub/cad-hub/pptx-hub/shared} |
| **Reviewers** | — |
| **Supersedes** | — |
| **Related** | — |

---

## 1. Context

{Beschreibe das Problem oder die Situation, die diese Entscheidung erfordert.}

## 2. Decision

{Beschreibe die Entscheidung, die getroffen wurde.}

## 3. Consequences

### 3.1 Positive
- {Vorteil 1}
- {Vorteil 2}

### 3.2 Negative
- {Nachteil 1}
- {Nachteil 2}

### 3.3 Risks & Mitigation
| Risk | Mitigation |
|------|------------|
| {Risiko 1} | {Gegenmaßnahme} |

## 4. Alternatives Considered

| Alternative | Pros | Cons | Why not chosen |
|-------------|------|------|----------------|
| {Option A} | ... | ... | ... |

## 5. Implementation

{Implementierungsplan, falls relevant}

## 6. References

- {Link 1}
- {Link 2}
```

### 4.3 Index Generator (aktualisiert)

```python
#!/usr/bin/env python3
"""
scripts/generate-adr-index.py

Generiert einen Master-Index für alle ADRs mit Filterung nach Scope.
Unterstützt die neue zentralisierte Struktur mit Unterordnern.

Usage:
    python3 scripts/generate-adr-index.py
    python3 scripts/generate-adr-index.py --check
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict

# Configuration
ADR_ROOT = Path("docs/adr")
OUTPUT = ADR_ROOT / "README.md"

SCOPES = {
    "core": {"name": "Core/Platform", "range": "001-019", "emoji": "🏗️"},
    "bfagent": {"name": "BF Agent", "range": "020-029", "emoji": "🤖"},
    "travel-beat": {"name": "Travel-Beat", "range": "030-039", "emoji": "✈️"},
    "mcp-hub": {"name": "MCP-Hub", "range": "040-049", "emoji": "🔌"},
    "risk-hub": {"name": "Risk-Hub", "range": "050-059", "emoji": "⚠️"},
    "cad-hub": {"name": "CAD-Hub", "range": "060-069", "emoji": "📐"},
    "pptx-hub": {"name": "PPTX-Hub", "range": "070-079", "emoji": "📊"},
    "shared": {"name": "Shared/Cross-App", "range": "080-099", "emoji": "🔗"},
    "drafts": {"name": "Drafts", "range": "—", "emoji": "📝"},
    "_archive": {"name": "Archived", "range": "—", "emoji": "📦"},
}

STATUS_EMOJI = {
    "proposed": "🟢",
    "accepted": "✅",
    "superseded": "🔄",
    "deprecated": "⚠️",
    "rejected": "❌",
    "draft": "📝",
}


@dataclass
class ADRInfo:
    """Information about an ADR."""
    file: str
    path: Path
    number: str
    title: str
    status: str
    date: str
    scope: str
    author: str = ""
    related: str = ""
    supersedes: str = ""
    is_archived: bool = False
    
    @property
    def status_emoji(self) -> str:
        for key, emoji in STATUS_EMOJI.items():
            if key in self.status.lower():
                return emoji
        return "❓"
    
    @property
    def sort_key(self) -> tuple:
        """Sort by number, with drafts at the end."""
        try:
            return (0, int(self.number))
        except ValueError:
            return (1, self.number)


def extract_adr_info(filepath: Path, scope: str) -> Optional[ADRInfo]:
    """Extract metadata from an ADR file."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  ⚠️ Could not read {filepath}: {e}")
        return None

    # Extract number from filename
    number_match = re.search(r'ADR-(\d{3}|DRAFT-\w+)', filepath.name)
    number = number_match.group(1) if number_match else "???"

    # Extract title
    title = "Untitled"
    title_match = re.search(r'^#\s+ADR-[\w-]+[:\s]+(.+)$', content, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
    else:
        # Fallback: derive from filename
        title = filepath.stem.replace('ADR-', '').replace('-', ' ').title()
        title = re.sub(r'^\d+\s*', '', title)

    # Extract metadata fields
    def extract_field(name: str) -> str:
        match = re.search(rf'\*\*{name}\*\*\s*\|\s*([^|\n]+)', content, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    status = extract_field("Status") or "Unknown"
    date = extract_field("Date") or ""
    author = extract_field("Author") or ""
    related = extract_field("Related") or ""
    supersedes = extract_field("Supersedes") or ""

    is_archived = "_archive" in str(filepath) or scope == "_archive"

    return ADRInfo(
        file=filepath.name,
        path=filepath,
        number=number,
        title=title,
        status=status,
        date=date,
        scope=scope,
        author=author,
        related=related,
        supersedes=supersedes,
        is_archived=is_archived,
    )


def scan_adrs() -> dict[str, list[ADRInfo]]:
    """Scan all ADRs and group by scope."""
    adrs_by_scope = defaultdict(list)
    
    for scope_dir in ADR_ROOT.iterdir():
        if not scope_dir.is_dir():
            continue
        if scope_dir.name.startswith('.'):
            continue
            
        scope = scope_dir.name
        
        # Handle archive subdirectories
        if scope == "_archive":
            for archive_subdir in scope_dir.iterdir():
                if archive_subdir.is_dir() and not archive_subdir.name.startswith('.'):
                    for adr_file in archive_subdir.glob("ADR-*.md"):
                        info = extract_adr_info(adr_file, f"_archive/{archive_subdir.name}")
                        if info:
                            adrs_by_scope["_archive"].append(info)
        else:
            # Regular scope directory
            for adr_file in scope_dir.glob("ADR-*.md"):
                info = extract_adr_info(adr_file, scope)
                if info:
                    adrs_by_scope[scope].append(info)
    
    # Sort each scope by number
    for scope in adrs_by_scope:
        adrs_by_scope[scope].sort(key=lambda x: x.sort_key)
    
    return adrs_by_scope


def generate_index(adrs_by_scope: dict[str, list[ADRInfo]]) -> str:
    """Generate markdown index."""
    
    # Count totals
    total_active = sum(len(adrs) for scope, adrs in adrs_by_scope.items() if scope != "_archive")
    total_archived = len(adrs_by_scope.get("_archive", []))
    
    output = f"""# 📋 Architecture Decision Records (ADRs)

> **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  
> **Total:** {total_active} active, {total_archived} archived

## 📖 Quick Navigation

| Scope | ADRs | Number Range |
|-------|------|--------------|
"""
    
    # Navigation table
    for scope_key, scope_info in SCOPES.items():
        if scope_key in ("drafts", "_archive"):
            continue
        count = len(adrs_by_scope.get(scope_key, []))
        output += f"| {scope_info['emoji']} [{scope_info['name']}](#{scope_key}) | {count} | {scope_info['range']} |\n"
    
    # Add drafts and archive
    draft_count = len(adrs_by_scope.get("drafts", []))
    output += f"| 📝 [Drafts](#drafts) | {draft_count} | — |\n"
    output += f"| 📦 [Archived](#archived) | {total_archived} | — |\n"
    
    output += """
---

## 🚦 Status Legend

| Status | Meaning |
|--------|---------|
| 🟢 Proposed | Under review, not yet decided |
| ✅ Accepted | Active decision, implemented or in progress |
| 🔄 Superseded | Replaced by a newer ADR |
| ⚠️ Deprecated | No longer relevant |
| ❌ Rejected | Considered but not adopted |
| 📝 Draft | Work in progress |

---

"""
    
    # Generate section for each scope
    for scope_key in ["core", "bfagent", "travel-beat", "mcp-hub", "risk-hub", "cad-hub", "pptx-hub", "shared", "drafts"]:
        scope_info = SCOPES.get(scope_key, {})
        adrs = adrs_by_scope.get(scope_key, [])
        
        output += f"## {scope_info.get('emoji', '')} {scope_info.get('name', scope_key)} {{#{scope_key}}}\n\n"
        
        if scope_key != "drafts":
            output += f"**Number Range:** {scope_info.get('range', '—')}\n\n"
        
        if adrs:
            output += "| # | Title | Status | Date |\n"
            output += "|---|-------|--------|------|\n"
            for adr in adrs:
                rel_path = adr.path.relative_to(ADR_ROOT)
                output += f"| [{adr.number}]({rel_path}) | {adr.title} | {adr.status_emoji} {adr.status} | {adr.date} |\n"
        else:
            output += "*No ADRs in this scope yet.*\n"
        
        output += "\n---\n\n"
    
    # Archived section
    archived = adrs_by_scope.get("_archive", [])
    output += "## 📦 Archived {#archived}\n\n"
    output += "Superseded, deprecated, or rejected ADRs.\n\n"
    
    if archived:
        output += "| # | Title | Original Scope | Status | Date |\n"
        output += "|---|-------|----------------|--------|------|\n"
        for adr in archived:
            rel_path = adr.path.relative_to(ADR_ROOT)
            original_scope = adr.scope.replace("_archive/", "")
            output += f"| [{adr.number}]({rel_path}) | {adr.title} | {original_scope} | {adr.status_emoji} {adr.status} | {adr.date} |\n"
    else:
        output += "*No archived ADRs yet.*\n"
    
    output += """
---

## 📝 Creating a New ADR

### 1. Create Draft

```bash
cp docs/adr/TEMPLATE.md docs/adr/drafts/ADR-DRAFT-my-topic.md
# Edit the file
```

### 2. Determine Scope (Triage)

See [TRIAGE.md](TRIAGE.md) for guidance. Ask:
- Is it infrastructure/platform-wide? → `core/`
- Does it affect multiple apps? → `shared/`
- Is it app-specific? → `{app-name}/`

### 3. Assign Number & Move

```bash
# Example: Next free number in core/ is 012
mv docs/adr/drafts/ADR-DRAFT-my-topic.md docs/adr/core/ADR-012-my-topic.md
# Update the number in the file header
```

### 4. Create PR

- AI Review runs automatically
- Request team review
- After approval: Change Status to `Accepted`

---

## 🔗 Quick Links

- [ADR Template](TEMPLATE.md)
- [Triage Guide](TRIAGE.md)
- [Archive Policy](core/ADR-011-centralized-adr-management.md)

---

*Index auto-generated by `scripts/generate-adr-index.py`*
"""
    
    return output


def main():
    check_only = "--check" in sys.argv
    
    print("🔍 Scanning ADRs...")
    adrs_by_scope = scan_adrs()
    
    total = sum(len(adrs) for adrs in adrs_by_scope.values())
    print(f"📊 Found {total} ADRs across {len(adrs_by_scope)} scopes")
    
    for scope, adrs in sorted(adrs_by_scope.items()):
        if adrs:
            print(f"   {scope}: {len(adrs)} ADRs")
    
    # Generate index
    index_content = generate_index(adrs_by_scope)
    
    if check_only:
        if OUTPUT.exists():
            current = OUTPUT.read_text()
            # Compare ignoring timestamp
            current_lines = [l for l in current.split('\n') if not l.startswith('> **Generated:**')]
            new_lines = [l for l in index_content.split('\n') if not l.startswith('> **Generated:**')]
            
            if current_lines == new_lines:
                print("✅ ADR index is up to date")
                sys.exit(0)
            else:
                print("⚠️ ADR index needs update!")
                print("Run: python3 scripts/generate-adr-index.py")
                sys.exit(1)
        else:
            print("⚠️ ADR index does not exist!")
            sys.exit(1)
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(index_content)
        print(f"✅ Generated: {OUTPUT}")


if __name__ == "__main__":
    main()
```

### 4.4 Triage Guide

```markdown
<!-- docs/adr/TRIAGE.md -->
# ADR Triage Guide

## Entscheidungsbaum: Welcher Scope?

```
                    Neues ADR
                        │
                        ▼
        ┌───────────────────────────────┐
        │ Betrifft es Infrastruktur?    │
        │ (CI/CD, Deployment, DB,       │
        │  Monitoring, Security)        │
        └───────────────┬───────────────┘
                        │
              Ja ───────┴─────── Nein
               │                   │
               ▼                   ▼
          ┌────────┐    ┌─────────────────────┐
          │ core/  │    │ Betrifft es         │
          │001-019 │    │ mehrere Apps (≥2)?  │
          └────────┘    └─────────┬───────────┘
                                  │
                        Ja ───────┴─────── Nein
                         │                   │
                         ▼                   ▼
                    ┌─────────┐    ┌─────────────────┐
                    │ shared/ │    │ Welche App?     │
                    │ 080-099 │    └────────┬────────┘
                    └─────────┘             │
                         ┌─────────────────┬┴────────────────┐
                         ▼                 ▼                  ▼
                    ┌─────────┐      ┌───────────┐     ┌──────────┐
                    │ bfagent │      │travel-beat│     │ mcp-hub  │ ...
                    │ 020-029 │      │  030-039  │     │ 040-049  │
                    └─────────┘      └───────────┘     └──────────┘
```

## Scope-Kriterien

| Scope | Wann? | Beispiele |
|-------|-------|-----------|
| `core/` | Platform-weit, alle Apps | Deployment, CI/CD, DB-Schema, Auth-Infrastruktur |
| `bfagent/` | Nur BF Agent | Agent Lifecycle, Tool Execution |
| `travel-beat/` | Nur Travel-Beat | Story Generation, Timing Engine |
| `mcp-hub/` | Nur MCP Hub | Server Registry, MCP Extensions |
| `risk-hub/` | Nur Risk Hub | Risk Scoring, Assessment |
| `cad-hub/` | Nur CAD Hub | CAD Import, Format Conversion |
| `pptx-hub/` | Nur PPTX Hub | Slide Generation |
| `shared/` | ≥2 Apps (nicht Infra) | API Conventions, Logging Format |

## Nächste freie Nummer finden

```bash
# Beispiel: Nächste Nummer in core/
ls docs/adr/core/ADR-*.md | sort | tail -1
# ADR-011-xxx.md → Nächste: 012
```
```

### 4.5 Migrations-Script (für bestehende ADRs)

```bash
#!/bin/bash
# scripts/migrate-adrs-to-central.sh
#
# Migriert bestehende ADRs aus anderen Repos nach platform/docs/adr/
# 
# Usage:
#   ./scripts/migrate-adrs-to-central.sh /path/to/other-repo bfagent

set -euo pipefail

SOURCE_REPO="${1:-}"
TARGET_SCOPE="${2:-}"

if [ -z "$SOURCE_REPO" ] || [ -z "$TARGET_SCOPE" ]; then
    echo "Usage: $0 <source-repo-path> <target-scope>"
    echo "Example: $0 ../bfagent bfagent"
    exit 1
fi

TARGET_DIR="docs/adr/$TARGET_SCOPE"
mkdir -p "$TARGET_DIR"

# Find ADRs in source repo
for adr in "$SOURCE_REPO"/docs/adr/ADR-*.md "$SOURCE_REPO"/ADR-*.md; do
    [ -f "$adr" ] || continue
    
    filename=$(basename "$adr")
    
    # Determine new number based on scope
    case "$TARGET_SCOPE" in
        bfagent)     base=20 ;;
        travel-beat) base=30 ;;
        mcp-hub)     base=40 ;;
        risk-hub)    base=50 ;;
        cad-hub)     base=60 ;;
        pptx-hub)    base=70 ;;
        *)           base=80 ;;
    esac
    
    # Find next available number
    existing=$(ls "$TARGET_DIR"/ADR-*.md 2>/dev/null | wc -l)
    new_num=$(printf "%03d" $((base + existing)))
    
    # Extract title from old filename
    title=$(echo "$filename" | sed 's/ADR-[0-9]*-//' | sed 's/\.md$//')
    new_filename="ADR-${new_num}-${title}.md"
    
    echo "Migrating: $adr → $TARGET_DIR/$new_filename"
    
    # Copy and update number in file
    sed "s/ADR-[0-9]*/ADR-$new_num/g" "$adr" > "$TARGET_DIR/$new_filename"
done

echo "✅ Migration complete. Run: python3 scripts/generate-adr-index.py"
```

---

## 5. Consequences

### 5.1 Positive

| Benefit | Description |
|---------|-------------|
| **Single Source of Truth** | Alle Architektur-Entscheidungen an einem Ort |
| **Eindeutige Nummern** | ADR-042 ist global eindeutig |
| **Einfache Cross-Referenzen** | `[ADR-025](../bfagent/ADR-025-xxx.md)` |
| **Ein Review-System** | Konsistente AI-Reviews für alle ADRs |
| **Besseres Onboarding** | "Lies platform/docs/adr/" |
| **Automatischer Index** | Filterbar nach Scope, immer aktuell |
| **Reduzierte Wartung** | Ein Hygiene-System statt 7 |

### 5.2 Negative

| Drawback | Mitigation |
|----------|------------|
| Platform-Repo wird größer | ADRs sind klein (< 50KB total) |
| Mehr PRs in Platform | Klare Trennung durch Ordner |
| App-Teams müssen in anderes Repo | Klare Dokumentation, einfacher Prozess |

### 5.3 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Falsche Scope-Zuordnung | Medium | Low | Triage-Guide, Review |
| Nummernkreis voll | Low | Medium | Reserve 100-199 |
| Vergessene Migration | Medium | Low | Einmaliger Migrations-Sprint |

---

## 6. Migration Plan

### Phase 1: Setup (Tag 1)

| Task | Deliverable |
|------|-------------|
| Ordnerstruktur erstellen | `docs/adr/{scope}/` |
| Scripts erstellen | `generate-adr-index.py`, `migrate-adrs-to-central.sh` |
| Templates erstellen | `TEMPLATE.md`, `TRIAGE.md` |
| Dieses ADR committen | `ADR-011` in `core/` |

### Phase 2: Migration (Tag 2-3)

| Task | Deliverable |
|------|-------------|
| Bestehende ADRs in Platform kategorisieren | Nach Scope sortiert |
| ADRs aus anderen Repos migrieren | Alle in `platform/docs/adr/` |
| Index generieren | `README.md` aktuell |
| CI-Workflow aktivieren | Automatische Checks |

### Phase 3: Kommunikation (Tag 4)

| Task | Deliverable |
|------|-------------|
| Team informieren | Prozess-Doku |
| README in App-Repos updaten | Links zu Platform ADRs |
| Alte ADR-Ordner in App-Repos archivieren | Keine Duplikate |

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| ADRs in Platform | 100% | `find docs/adr -name "ADR-*.md" \| wc -l` |
| ADRs in anderen Repos | 0 | Check other repos |
| Index up to date | Always | CI check |
| Nummernkonflikte | 0 | Unique check in CI |

---

## 8. References

- [ADR GitHub Organization](https://adr.github.io/)
- [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-02-03 | Achim Dehnert | Initial version with centralized approach |
