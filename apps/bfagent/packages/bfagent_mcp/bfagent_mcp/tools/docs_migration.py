"""
Documentation Migration Tools
=============================

Semi-automatische Migration von Legacy-Docs nach Sphinx.
User behält volle Kontrolle über jede Migration.
"""

import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

# Project root detection
def get_project_root() -> Path:
    """Find project root by looking for manage.py."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "manage.py").exists():
            return parent
    return current.parent.parent.parent.parent.parent


PROJECT_ROOT = get_project_root()


# Category patterns for auto-classification
CATEGORY_PATTERNS = {
    "api/handlers": [
        r"HANDLER.*\.md$",
        r".*_HANDLER.*\.md$",
        r".*handler.*\.md$",
    ],
    "api/models": [
        r"MODEL.*\.md$",
        r".*_MODEL.*\.md$",
        r"DATABASE.*\.md$",
    ],
    "guides": [
        r".*GUIDE.*\.md$",
        r".*QUICKSTART.*\.md$",
        r".*QUICK_START.*\.md$",
        r".*TUTORIAL.*\.md$",
        r".*HOW_TO.*\.md$",
    ],
    "concepts/architecture": [
        r"ARCHITECTURE.*\.md$",
        r".*_ARCHITECTURE.*\.md$",
        r"DESIGN.*\.md$",
    ],
    "concepts/workflows": [
        r"WORKFLOW.*\.md$",
        r".*_WORKFLOW.*\.md$",
        r"PIPELINE.*\.md$",
    ],
    "reference/tools": [
        r"TOOL.*\.md$",
        r".*_TOOL.*\.md$",
        r"MCP.*\.md$",
    ],
    "reference/api": [
        r"API.*\.md$",
        r".*_API.*\.md$",
        r"OPENAPI.*\.md$",
    ],
    "concepts/systems": [
        r".*SYSTEM.*\.md$",
        r".*FRAMEWORK.*\.md$",
    ],
    "uncategorized": [],  # Fallback
}


@dataclass
class LegacyDoc:
    """Represents a legacy documentation file."""
    path: Path
    name: str
    size_kb: float
    category: str
    suggested_target: str
    first_lines: str  # Preview


@dataclass
class MigrationResult:
    """Result of a migration operation."""
    success: bool
    message: str
    source: str
    target: str


def categorize_file(filename: str) -> Tuple[str, str]:
    """
    Categorize a file based on its name.
    
    Returns:
        Tuple of (category, suggested_target_path)
    """
    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if re.match(pattern, filename, re.IGNORECASE):
                return category, f"docs/source/{category}/{filename}"
    
    return "uncategorized", f"docs/source/uncategorized/{filename}"


def get_file_preview(file_path: Path, lines: int = 5) -> str:
    """Get first N lines of a file as preview."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            preview_lines = []
            for i, line in enumerate(f):
                if i >= lines:
                    break
                preview_lines.append(line.rstrip())
            return "\n".join(preview_lines)
    except Exception as e:
        return f"(Fehler beim Lesen: {e})"


def analyze_legacy_docs(
    legacy_path: str = "docs_legacy",
    include_subdirs: bool = True
) -> Dict[str, List[LegacyDoc]]:
    """
    Analyze legacy documentation folder.
    
    Args:
        legacy_path: Path to legacy docs relative to project root
        include_subdirs: Whether to scan subdirectories
        
    Returns:
        Dict with categories as keys and lists of LegacyDoc as values
    """
    legacy_dir = PROJECT_ROOT / legacy_path
    
    if not legacy_dir.exists():
        return {"error": [LegacyDoc(
            path=legacy_dir,
            name="NOT_FOUND",
            size_kb=0,
            category="error",
            suggested_target="",
            first_lines=f"Verzeichnis nicht gefunden: {legacy_dir}"
        )]}
    
    results = defaultdict(list)
    
    # Scan for markdown files
    pattern = "**/*.md" if include_subdirs else "*.md"
    
    for file_path in legacy_dir.glob(pattern):
        if file_path.is_file():
            filename = file_path.name
            category, suggested_target = categorize_file(filename)
            
            # Get file stats
            size_kb = file_path.stat().st_size / 1024
            preview = get_file_preview(file_path)
            
            doc = LegacyDoc(
                path=file_path,
                name=filename,
                size_kb=round(size_kb, 1),
                category=category,
                suggested_target=suggested_target,
                first_lines=preview[:200]
            )
            
            results[category].append(doc)
    
    # Sort each category by name
    for category in results:
        results[category].sort(key=lambda x: x.name)
    
    return dict(results)


def migrate_file(
    source: str,
    target: str,
    delete_source: bool = False,
    create_dirs: bool = True
) -> MigrationResult:
    """
    Migrate a single documentation file.
    
    Args:
        source: Source file path (relative or absolute)
        target: Target file path (relative or absolute)
        delete_source: Whether to delete source after copy
        create_dirs: Whether to create target directories
        
    Returns:
        MigrationResult with status
    """
    source_path = Path(source)
    if not source_path.is_absolute():
        source_path = PROJECT_ROOT / source
        
    target_path = Path(target)
    if not target_path.is_absolute():
        target_path = PROJECT_ROOT / target
    
    # Validate source
    if not source_path.exists():
        return MigrationResult(
            success=False,
            message=f"Quelle nicht gefunden: {source_path}",
            source=str(source_path),
            target=str(target_path)
        )
    
    # Create target directory if needed
    if create_dirs:
        target_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if target exists
    if target_path.exists():
        return MigrationResult(
            success=False,
            message=f"Ziel existiert bereits: {target_path}",
            source=str(source_path),
            target=str(target_path)
        )
    
    try:
        # Copy file
        shutil.copy2(source_path, target_path)
        
        # Delete source if requested
        if delete_source:
            source_path.unlink()
            action = "verschoben"
        else:
            action = "kopiert"
        
        return MigrationResult(
            success=True,
            message=f"Erfolgreich {action}: {source_path.name}",
            source=str(source_path),
            target=str(target_path)
        )
        
    except Exception as e:
        return MigrationResult(
            success=False,
            message=f"Fehler: {e}",
            source=str(source_path),
            target=str(target_path)
        )


def check_duplicates(
    legacy_path: str = "docs_legacy",
    sphinx_path: str = "docs/source"
) -> List[Tuple[str, str]]:
    """
    Find files that exist in both legacy and sphinx docs.
    
    Returns:
        List of (legacy_path, sphinx_path) tuples for duplicates
    """
    legacy_dir = PROJECT_ROOT / legacy_path
    sphinx_dir = PROJECT_ROOT / sphinx_path
    
    duplicates = []
    
    if not legacy_dir.exists() or not sphinx_dir.exists():
        return duplicates
    
    # Get all sphinx doc names
    sphinx_files = {f.name for f in sphinx_dir.rglob("*.md")}
    sphinx_files.update({f.name for f in sphinx_dir.rglob("*.rst")})
    
    # Check legacy files
    for legacy_file in legacy_dir.rglob("*.md"):
        if legacy_file.name in sphinx_files:
            # Find the sphinx file
            for sphinx_file in sphinx_dir.rglob(legacy_file.name):
                duplicates.append((str(legacy_file), str(sphinx_file)))
                break
    
    return duplicates


def format_analysis_report(analysis: Dict[str, List[LegacyDoc]]) -> str:
    """Format analysis results as markdown report."""
    lines = ["# 📚 Legacy Documentation Analyse\n"]
    
    total_files = sum(len(docs) for docs in analysis.values())
    total_size = sum(doc.size_kb for docs in analysis.values() for doc in docs)
    
    lines.append(f"**Gesamt:** {total_files} Dateien, {total_size:.1f} KB\n")
    lines.append("---\n")
    
    for category, docs in sorted(analysis.items()):
        if not docs:
            continue
            
        emoji = {
            "api/handlers": "🔧",
            "api/models": "📦",
            "guides": "📖",
            "concepts/architecture": "🏗️",
            "concepts/workflows": "🔄",
            "concepts/systems": "⚙️",
            "reference/tools": "🛠️",
            "reference/api": "🔌",
            "uncategorized": "❓",
            "error": "❌",
        }.get(category, "📄")
        
        lines.append(f"\n## {emoji} {category} ({len(docs)} Dateien)\n")
        
        # Show top 10 per category
        for doc in docs[:10]:
            lines.append(f"- `{doc.name}` ({doc.size_kb} KB)")
        
        if len(docs) > 10:
            lines.append(f"- ... und {len(docs) - 10} weitere\n")
    
    lines.append("\n---\n")
    lines.append("### 💡 Nächste Schritte\n")
    lines.append("1. `bfagent_docs_migrate_file(source, target)` für einzelne Dateien")
    lines.append("2. `delete_source=True` um Original zu löschen")
    
    return "\n".join(lines)
