#!/usr/bin/env python
"""
Dokumentations-Kategorisierung für Cleanup Phase B.
Kategorisiert alle MD-Dateien in docs/ in drei Gruppen:
1. ARCHIVE - Temporäre/veraltete Dateien
2. KEEP_MD - Essentielle MD-Dateien
3. MIGRATE_TO_DB - In Datenbank zu überführen
"""

import os
import json
from pathlib import Path
from datetime import datetime

DOCS_PATH = Path(__file__).parent.parent / "docs"

# Patterns für Kategorisierung
ARCHIVE_PATTERNS = [
    "SESSION_",
    "PHASE_",
    "CLEANUP_",
    "FIX_",
    "CIRCULAR_",
    "UTF8_",
    "COMMIT_MESSAGE",
    "REFACTORING_SESSION",
    "REFACTORING_TODO",
    "QUICK_START_TOMORROW",
    "RESUME_WORK",
    "TEST_RESULTS",
    "V2_IMPLEMENTATION_SUMMARY",
    "_full_analysis",
    "alternative_approaches",
]

ARCHIVE_CONTAINS = [
    "_SUCCESS",
    "_COMPLETE",
    "_STATUS",
    "_SUMMARY",
    "INTEGRATION_SUCCESS",
    "CHECKLIST",
]

KEEP_MD_PATTERNS = [
    "README",
    "USER_GUIDE",
    "USER_DOCUMENTATION",
    "DEVELOPER_GUIDE",
    "ARCHITECTURE_DOCUMENTATION",
    "DEPLOYMENT-GUIDE",
    "TESTING_GUIDE",
    "API-DOCUMENTATION",
    "GOLDEN_RULES",
    "QUICK_REFERENCE_CARD",
]

# Domains für Migration
DOMAINS = [
    "CONTROL_CENTER",
    "WRITING_HUB",
    "MEDTRANS",
    "GENAGENT",
    "HANDLER",
    "WORKFLOW",
    "BOOK_",
    "CHARACTER",
    "ILLUSTRATION",
    "MCP_",
    "TOOL",
    "NAVIGATION",
    "TEMPLATE",
]


def categorize_file(filename: str) -> tuple[str, str]:
    """Kategorisiert eine Datei basierend auf dem Namen."""
    name_upper = filename.upper()
    
    # 1. Check KEEP_MD first (highest priority)
    for pattern in KEEP_MD_PATTERNS:
        if pattern in name_upper:
            return "KEEP_MD", f"Matches keep pattern: {pattern}"
    
    # 2. Check ARCHIVE patterns
    for pattern in ARCHIVE_PATTERNS:
        if name_upper.startswith(pattern):
            return "ARCHIVE", f"Starts with: {pattern}"
    
    for pattern in ARCHIVE_CONTAINS:
        if pattern in name_upper:
            return "ARCHIVE", f"Contains: {pattern}"
    
    # 3. Domain-specific → MIGRATE_TO_DB
    for domain in DOMAINS:
        if domain in name_upper:
            return "MIGRATE_TO_DB", f"Domain: {domain}"
    
    # 4. Default: MIGRATE_TO_DB (wird manuell geprüft)
    return "MIGRATE_TO_DB", "Default - needs review"


def analyze_docs():
    """Analysiert alle MD-Dateien im docs/ Ordner."""
    results = {
        "ARCHIVE": [],
        "KEEP_MD": [],
        "MIGRATE_TO_DB": [],
        "stats": {
            "total": 0,
            "archive": 0,
            "keep_md": 0,
            "migrate": 0,
        }
    }
    
    # Nur Root-Level MD-Dateien
    for file in DOCS_PATH.glob("*.md"):
        if file.is_file():
            category, reason = categorize_file(file.name)
            
            file_info = {
                "name": file.name,
                "size_kb": round(file.stat().st_size / 1024, 1),
                "modified": datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d"),
                "reason": reason,
            }
            
            results[category].append(file_info)
            results["stats"]["total"] += 1
            
            if category == "ARCHIVE":
                results["stats"]["archive"] += 1
            elif category == "KEEP_MD":
                results["stats"]["keep_md"] += 1
            else:
                results["stats"]["migrate"] += 1
    
    # Sortieren nach Name
    for cat in ["ARCHIVE", "KEEP_MD", "MIGRATE_TO_DB"]:
        results[cat].sort(key=lambda x: x["name"])
    
    return results


def main():
    print("📚 Dokumentations-Kategorisierung")
    print("=" * 50)
    
    results = analyze_docs()
    
    # Statistiken
    stats = results["stats"]
    print(f"\n📊 Statistiken:")
    print(f"   Total:         {stats['total']} Dateien")
    print(f"   ARCHIVE:       {stats['archive']} ({stats['archive']*100//stats['total']}%)")
    print(f"   KEEP_MD:       {stats['keep_md']} ({stats['keep_md']*100//stats['total']}%)")
    print(f"   MIGRATE_TO_DB: {stats['migrate']} ({stats['migrate']*100//stats['total']}%)")
    
    # Details
    print(f"\n✅ KEEP_MD ({len(results['KEEP_MD'])} Dateien):")
    for f in results["KEEP_MD"]:
        print(f"   📄 {f['name']}")
    
    print(f"\n📦 ARCHIVE ({len(results['ARCHIVE'])} Dateien):")
    for f in results["ARCHIVE"][:10]:
        print(f"   🗄️  {f['name']}")
    if len(results["ARCHIVE"]) > 10:
        print(f"   ... und {len(results['ARCHIVE']) - 10} weitere")
    
    print(f"\n🗄️  MIGRATE_TO_DB ({len(results['MIGRATE_TO_DB'])} Dateien):")
    for f in results["MIGRATE_TO_DB"][:10]:
        print(f"   📝 {f['name']}")
    if len(results["MIGRATE_TO_DB"]) > 10:
        print(f"   ... und {len(results['MIGRATE_TO_DB']) - 10} weitere")
    
    # JSON speichern
    output_file = DOCS_PATH / "_categorization.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Ergebnis gespeichert: {output_file}")
    
    return results


if __name__ == "__main__":
    main()
