#!/usr/bin/env python3
"""
scripts/generate-adr-index.py

Generiert einen Master-Index für alle ADRs mit Filterung nach Scope.
Unterstützt die zentralisierte Struktur mit Unterordnern.

Usage:
    python3 scripts/generate-adr-index.py              # Index generieren
    python3 scripts/generate-adr-index.py --check      # Nur prüfen
    python3 scripts/generate-adr-index.py --next core  # Nächste Nummer für Scope
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
from collections import defaultdict

# ============================================================
# Configuration
# ============================================================

ADR_ROOT = Path("docs/adr")
OUTPUT = ADR_ROOT / "README.md"

SCOPES = {
    "core": {
        "name": "Core/Platform",
        "range": (1, 19),
        "emoji": "🏗️",
        "description": "Platform infrastructure, CI/CD, deployment, database"
    },
    "bfagent": {
        "name": "BF Agent",
        "range": (20, 29),
        "emoji": "🤖",
        "description": "BF Agent application decisions"
    },
    "travel-beat": {
        "name": "Travel-Beat",
        "range": (30, 39),
        "emoji": "✈️",
        "description": "Travel-Beat / Drifttales application"
    },
    "mcp-hub": {
        "name": "MCP-Hub",
        "range": (40, 49),
        "emoji": "🔌",
        "description": "MCP Server registry and management"
    },
    "risk-hub": {
        "name": "Risk-Hub",
        "range": (50, 59),
        "emoji": "⚠️",
        "description": "Risk assessment application"
    },
    "cad-hub": {
        "name": "CAD-Hub",
        "range": (60, 69),
        "emoji": "📐",
        "description": "CAD processing application"
    },
    "pptx-hub": {
        "name": "PPTX-Hub",
        "range": (70, 79),
        "emoji": "📊",
        "description": "PowerPoint generation"
    },
    "shared": {
        "name": "Shared/Cross-App",
        "range": (80, 99),
        "emoji": "🔗",
        "description": "Cross-app concerns, shared patterns"
    },
}

STATUS_EMOJI = {
    "proposed": "🟢",
    "accepted": "✅",
    "superseded": "🔄",
    "deprecated": "⚠️",
    "rejected": "❌",
    "draft": "📝",
}


# ============================================================
# Data Classes
# ============================================================

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
    is_archived: bool = False
    is_draft: bool = False
    
    @property
    def status_emoji(self) -> str:
        for key, emoji in STATUS_EMOJI.items():
            if key in self.status.lower():
                return emoji
        return "❓"
    
    @property
    def numeric_sort(self) -> int:
        """Extract numeric value for sorting."""
        try:
            return int(re.search(r'\d+', self.number).group())
        except:
            return 999


# ============================================================
# Extraction Functions
# ============================================================

def extract_adr_info(filepath: Path, scope: str) -> Optional[ADRInfo]:
    """Extract metadata from an ADR file."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  ⚠️ Could not read {filepath}: {e}")
        return None

    # Extract number from filename
    number_match = re.search(r'ADR-(\d{3}|DRAFT[_-]\w+)', filepath.name)
    number = number_match.group(1) if number_match else "???"
    
    is_draft = "DRAFT" in number.upper()
    is_archived = "_archive" in str(filepath)

    # Extract title
    title = "Untitled"
    title_match = re.search(r'^#\s+ADR-[\w-]+[:\s]+(.+)$', content, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
    else:
        # Fallback: derive from filename
        title = filepath.stem
        title = re.sub(r'^ADR-[\d]+-', '', title)
        title = re.sub(r'^ADR-DRAFT-', '', title)
        title = title.replace('-', ' ').title()

    # Extract metadata fields
    def extract_field(name: str) -> str:
        match = re.search(rf'\*\*{name}\*\*\s*\|\s*([^|\n]+)', content, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    status = extract_field("Status") or ("Draft" if is_draft else "Unknown")
    date = extract_field("Date") or ""
    author = extract_field("Author") or ""

    return ADRInfo(
        file=filepath.name,
        path=filepath,
        number=number,
        title=title,
        status=status,
        date=date,
        scope=scope,
        author=author,
        is_archived=is_archived,
        is_draft=is_draft,
    )


# ============================================================
# Scanning Functions
# ============================================================

def scan_adrs() -> dict[str, list[ADRInfo]]:
    """Scan all ADRs and group by scope."""
    adrs_by_scope = defaultdict(list)
    
    if not ADR_ROOT.exists():
        print(f"⚠️ ADR root not found: {ADR_ROOT}")
        return adrs_by_scope
    
    for scope_dir in ADR_ROOT.iterdir():
        if not scope_dir.is_dir():
            continue
        if scope_dir.name.startswith('.'):
            continue
        if scope_dir.name in ('TEMPLATE.md', 'TRIAGE.md', 'README.md'):
            continue
            
        scope = scope_dir.name
        
        # Handle archive subdirectories
        if scope == "_archive":
            for archive_subdir in scope_dir.iterdir():
                if archive_subdir.is_dir() and not archive_subdir.name.startswith('.'):
                    for adr_file in archive_subdir.glob("ADR-*.md"):
                        info = extract_adr_info(adr_file, archive_subdir.name)
                        if info:
                            info.is_archived = True
                            adrs_by_scope["_archive"].append(info)
        else:
            # Regular scope directory
            for adr_file in scope_dir.glob("ADR-*.md"):
                info = extract_adr_info(adr_file, scope)
                if info:
                    adrs_by_scope[scope].append(info)
    
    # Sort each scope by number
    for scope in adrs_by_scope:
        adrs_by_scope[scope].sort(key=lambda x: x.numeric_sort)
    
    return adrs_by_scope


def find_next_number(scope: str) -> int:
    """Find the next available number for a scope."""
    if scope not in SCOPES:
        raise ValueError(f"Unknown scope: {scope}. Available: {', '.join(SCOPES.keys())}")
    
    range_start, range_end = SCOPES[scope]["range"]
    
    # Find all existing numbers in this scope
    existing = set()
    scope_dir = ADR_ROOT / scope
    
    if scope_dir.exists():
        for adr_file in scope_dir.glob("ADR-*.md"):
            match = re.search(r'ADR-(\d{3})', adr_file.name)
            if match:
                existing.add(int(match.group(1)))
    
    # Also check archive
    archive_dir = ADR_ROOT / "_archive" / scope
    if archive_dir.exists():
        for adr_file in archive_dir.glob("ADR-*.md"):
            match = re.search(r'ADR-(\d{3})', adr_file.name)
            if match:
                existing.add(int(match.group(1)))
    
    # Find next available
    for num in range(range_start, range_end + 1):
        if num not in existing:
            return num
    
    raise ValueError(f"No available numbers in scope '{scope}' ({range_start:03d}-{range_end:03d})")


# ============================================================
# Index Generation
# ============================================================

def generate_index(adrs_by_scope: dict[str, list[ADRInfo]]) -> str:
    """Generate markdown index."""
    
    # Count totals
    active_scopes = [s for s in adrs_by_scope.keys() if s not in ("_archive", "drafts")]
    total_active = sum(len(adrs_by_scope.get(s, [])) for s in active_scopes)
    total_drafts = len(adrs_by_scope.get("drafts", []))
    total_archived = len(adrs_by_scope.get("_archive", []))
    
    output = f"""# 📋 Architecture Decision Records

> **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  
> **Active:** {total_active} | **Drafts:** {total_drafts} | **Archived:** {total_archived}

## 📖 Navigation

| Scope | ADRs | Range | Description |
|-------|------|-------|-------------|
"""
    
    # Navigation table
    for scope_key, scope_info in SCOPES.items():
        count = len(adrs_by_scope.get(scope_key, []))
        range_str = f"{scope_info['range'][0]:03d}-{scope_info['range'][1]:03d}"
        output += f"| {scope_info['emoji']} [{scope_info['name']}](#{scope_key}) | {count} | {range_str} | {scope_info['description']} |\n"
    
    output += f"| 📝 [Drafts](#drafts) | {total_drafts} | — | Work in progress |\n"
    output += f"| 📦 [Archived](#archived) | {total_archived} | — | Superseded/Deprecated |\n"
    
    output += """
---

## 🚦 Status Legend

| Status | Emoji | Meaning |
|--------|-------|---------|
| Proposed | 🟢 | Under review |
| Accepted | ✅ | Active decision |
| Superseded | 🔄 | Replaced by newer ADR |
| Deprecated | ⚠️ | No longer relevant |
| Rejected | ❌ | Not adopted |
| Draft | 📝 | Work in progress |

---

"""
    
    # Generate section for each scope
    for scope_key, scope_info in SCOPES.items():
        adrs = adrs_by_scope.get(scope_key, [])
        
        output += f"## {scope_info['emoji']} {scope_info['name']} {{#{scope_key}}}\n\n"
        output += f"**Range:** {scope_info['range'][0]:03d}-{scope_info['range'][1]:03d} | "
        output += f"**Count:** {len(adrs)}\n\n"
        
        if adrs:
            output += "| # | Title | Status | Date |\n"
            output += "|---|-------|--------|------|\n"
            for adr in adrs:
                rel_path = adr.path.relative_to(ADR_ROOT)
                output += f"| [{adr.number}]({rel_path}) | {adr.title} | {adr.status_emoji} {adr.status} | {adr.date} |\n"
        else:
            output += "*No ADRs in this scope yet.*\n"
        
        output += "\n---\n\n"
    
    # Drafts section
    drafts = adrs_by_scope.get("drafts", [])
    output += "## 📝 Drafts {#drafts}\n\n"
    
    if drafts:
        output += "| File | Title | Author |\n"
        output += "|------|-------|--------|\n"
        for adr in drafts:
            rel_path = adr.path.relative_to(ADR_ROOT)
            output += f"| [{adr.file}]({rel_path}) | {adr.title} | {adr.author} |\n"
    else:
        output += "*No drafts pending.*\n"
    
    output += "\n---\n\n"
    
    # Archived section
    archived = adrs_by_scope.get("_archive", [])
    output += "## 📦 Archived {#archived}\n\n"
    
    if archived:
        output += "| # | Title | Scope | Status |\n"
        output += "|---|-------|-------|--------|\n"
        for adr in sorted(archived, key=lambda x: x.numeric_sort):
            rel_path = adr.path.relative_to(ADR_ROOT)
            output += f"| [{adr.number}]({rel_path}) | {adr.title} | {adr.scope} | {adr.status_emoji} {adr.status} |\n"
    else:
        output += "*No archived ADRs.*\n"
    
    output += """
---

## ✏️ Creating a New ADR

```bash
# 1. Create draft
cp docs/adr/TEMPLATE.md docs/adr/drafts/ADR-DRAFT-my-topic.md

# 2. Edit the draft

# 3. Determine scope (see TRIAGE.md)

# 4. Get next number
python3 scripts/generate-adr-index.py --next core

# 5. Move to scope directory
mv docs/adr/drafts/ADR-DRAFT-my-topic.md docs/adr/core/ADR-012-my-topic.md

# 6. Create PR for review
```

See [TRIAGE.md](TRIAGE.md) for scope selection guide.

---

## 🔗 Resources

- [ADR Template](TEMPLATE.md)
- [Triage Guide](TRIAGE.md)
- [ADR-011: Centralized ADR Management](core/ADR-011-centralized-adr-management.md)

---

*Auto-generated by `scripts/generate-adr-index.py`*
"""
    
    return output


# ============================================================
# Main
# ============================================================

def main():
    args = sys.argv[1:]
    
    # Handle --next flag
    if "--next" in args:
        idx = args.index("--next")
        if idx + 1 < len(args):
            scope = args[idx + 1]
            try:
                next_num = find_next_number(scope)
                print(f"✅ Next number for '{scope}': {next_num:03d}")
                print(f"   File: docs/adr/{scope}/ADR-{next_num:03d}-your-title.md")
            except ValueError as e:
                print(f"❌ {e}")
                sys.exit(1)
        else:
            print("Usage: --next <scope>")
            print(f"Available scopes: {', '.join(SCOPES.keys())}")
            sys.exit(1)
        return
    
    check_only = "--check" in args
    
    print("🔍 Scanning ADRs...")
    adrs_by_scope = scan_adrs()
    
    # Summary
    total = sum(len(adrs) for adrs in adrs_by_scope.values())
    print(f"📊 Found {total} ADRs:")
    for scope in sorted(adrs_by_scope.keys()):
        count = len(adrs_by_scope[scope])
        if count > 0:
            print(f"   {scope}: {count}")
    
    # Generate index
    index_content = generate_index(adrs_by_scope)
    
    if check_only:
        if OUTPUT.exists():
            current = OUTPUT.read_text()
            # Compare ignoring timestamp
            def strip_timestamp(text):
                return '\n'.join(l for l in text.split('\n') if not l.startswith('> **Generated:**'))
            
            if strip_timestamp(current) == strip_timestamp(index_content):
                print("✅ ADR index is up to date")
                sys.exit(0)
            else:
                print("⚠️ ADR index needs update!")
                print("   Run: python3 scripts/generate-adr-index.py")
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
