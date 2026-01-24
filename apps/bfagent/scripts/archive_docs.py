#!/usr/bin/env python
"""
Archiviert kategorisierte Dokumentation.
Verschiebt ARCHIVE-Dateien nach docs/_archive/
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime

DOCS_PATH = Path(__file__).parent.parent / "docs"
ARCHIVE_PATH = DOCS_PATH / "_archive"
CATEGORIZATION_FILE = DOCS_PATH / "_categorization.json"


def archive_docs(dry_run: bool = True):
    """Archiviert Dateien basierend auf der Kategorisierung."""
    
    # Kategorisierung laden
    if not CATEGORIZATION_FILE.exists():
        print("❌ Keine Kategorisierung gefunden. Führe erst categorize_docs.py aus.")
        return
    
    with open(CATEGORIZATION_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    archive_files = data.get("ARCHIVE", [])
    
    if not archive_files:
        print("✅ Keine Dateien zum Archivieren.")
        return
    
    # Archive-Ordner erstellen
    if not dry_run:
        ARCHIVE_PATH.mkdir(exist_ok=True)
    
    print(f"📦 Archivierung {'(DRY RUN)' if dry_run else ''}")
    print("=" * 50)
    print(f"   Ziel: {ARCHIVE_PATH}")
    print(f"   Dateien: {len(archive_files)}")
    print()
    
    moved = 0
    skipped = 0
    
    for file_info in archive_files:
        src = DOCS_PATH / file_info["name"]
        dst = ARCHIVE_PATH / file_info["name"]
        
        if not src.exists():
            print(f"   ⚠️  Nicht gefunden: {file_info['name']}")
            skipped += 1
            continue
        
        if dst.exists():
            print(f"   ⚠️  Existiert bereits: {file_info['name']}")
            skipped += 1
            continue
        
        if dry_run:
            print(f"   📄 Würde verschieben: {file_info['name']}")
        else:
            shutil.move(str(src), str(dst))
            print(f"   ✅ Verschoben: {file_info['name']}")
        
        moved += 1
    
    print()
    print(f"📊 Ergebnis:")
    print(f"   {'Würden verschoben' if dry_run else 'Verschoben'}: {moved}")
    print(f"   Übersprungen: {skipped}")
    
    if dry_run:
        print()
        print("💡 Führe mit --execute aus um tatsächlich zu verschieben:")
        print("   python scripts/archive_docs.py --execute")


def main():
    import sys
    dry_run = "--execute" not in sys.argv
    archive_docs(dry_run=dry_run)


if __name__ == "__main__":
    main()
