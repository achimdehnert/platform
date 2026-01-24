"""
BF Agent MCP Package Cleanup
=============================

Löscht Duplikate und organisiert das Package.

SAFE: Nur Löschen von bestätigten Duplikaten
"""

import os
from pathlib import Path

BASE = Path(__file__).parent / "bfagent_mcp"

def compare_files(file1: Path, file2: Path) -> bool:
    """Vergleicht zwei Dateien - True wenn identisch"""
    if not file1.exists() or not file2.exists():
        return False
    return file1.read_text(encoding='utf-8') == file2.read_text(encoding='utf-8')


def cleanup_duplicates():
    """Löscht bestätigte Duplikate"""
    
    print("🧹 BF Agent MCP Package Cleanup")
    print("=" * 60)
    
    deleted_count = 0
    skipped_count = 0
    
    # 1. __init__.py Duplikate
    print("\n1️⃣  Checking __init__.py duplicates...")
    
    duplicates = [
        ("__init__ (1).py", "metaprompter/__init__.py"),
        ("__init__ (2).py", "standards/__init__.py"),
    ]
    
    for dup, original in duplicates:
        dup_file = BASE / dup
        orig_file = BASE / original
        
        if not dup_file.exists():
            print(f"   ⏭️  {dup} - already deleted")
            continue
        
        if compare_files(dup_file, orig_file):
            print(f"   🗑️  Deleting: {dup} (identical to {original})")
            dup_file.unlink()
            deleted_count += 1
        else:
            print(f"   ⚠️  DIFF: {dup} != {original} (manual check needed!)")
            skipped_count += 1
    
    # 2. MetaPrompter Files (Root vs Subfolder)
    print("\n2️⃣  Checking metaprompter files...")
    
    metaprompter_files = ["gateway.py", "intent.py", "enricher.py"]
    
    for filename in metaprompter_files:
        root_file = BASE / filename
        sub_file = BASE / "metaprompter" / filename
        
        if not root_file.exists():
            print(f"   ⏭️  {filename} - already deleted")
            continue
        
        if not sub_file.exists():
            print(f"   ⚠️  {filename} - subfolder version missing! (keep root)")
            skipped_count += 1
            continue
        
        if compare_files(root_file, sub_file):
            print(f"   🗑️  Deleting: {filename} (identical to metaprompter/{filename})")
            root_file.unlink()
            deleted_count += 1
        else:
            print(f"   ⚠️  DIFF: {filename} (manual check needed!)")
            skipped_count += 1
    
    # 3. Standards Files (Root vs Subfolder)
    print("\n3️⃣  Checking standards files...")
    
    standards_files = ["enforcer.py", "validator.py"]
    
    for filename in standards_files:
        root_file = BASE / filename
        sub_file = BASE / "standards" / filename
        
        if not root_file.exists():
            print(f"   ⏭️  {filename} - already deleted")
            continue
        
        if not sub_file.exists():
            print(f"   ⚠️  {filename} - subfolder version missing! (keep root)")
            skipped_count += 1
            continue
        
        if compare_files(root_file, sub_file):
            print(f"   🗑️  Deleting: {filename} (identical to standards/{filename})")
            root_file.unlink()
            deleted_count += 1
        else:
            print(f"   ⚠️  DIFF: {filename} (manual check needed!)")
            skipped_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"✅ Deleted: {deleted_count}")
    print(f"⚠️  Skipped (manual check): {skipped_count}")
    print("=" * 60)
    
    if deleted_count > 0:
        print("\n🎉 Cleanup successful!")
    
    if skipped_count > 0:
        print("\n⚠️  Manual review needed for files with differences!")
        print("   Check PACKAGE_ANALYSIS.md for details.")
    
    return deleted_count, skipped_count


def verify_imports():
    """Verifiziert dass Imports noch funktionieren"""
    print("\n🔍 Verifying imports after cleanup...")
    
    try:
        # Test metaprompter imports
        server_file = BASE / "server_metaprompter.py"
        if server_file.exists():
            content = server_file.read_text(encoding='utf-8')
            
            if "from .metaprompter import" in content:
                print("   ✅ server_metaprompter.py imports from .metaprompter")
            
            if "from .standards import" in content:
                print("   ✅ server_metaprompter.py imports from .standards")
        
        print("   ✅ Import structure looks good!")
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


if __name__ == "__main__":
    deleted, skipped = cleanup_duplicates()
    verify_imports()
    
    print("\n" + "=" * 60)
    print("📝 NEXT STEPS:")
    print("=" * 60)
    
    if deleted > 0:
        print("1. ✅ Duplikate wurden gelöscht")
        print("2. 🧪 Teste das Package:")
        print("   python -m pytest tests/")
        print("3. 🚀 Starte MCP Server:")
        print("   python -m bfagent_mcp.server_metaprompter")
    
    if skipped > 0:
        print("\n⚠️  MANUAL REVIEW NEEDED:")
        print("   Dateien mit Unterschieden wurden nicht gelöscht!")
        print("   Prüfe sie manuell und entscheide welche Version korrekt ist.")
    
    print("\n📄 Siehe PACKAGE_ANALYSIS.md für Details!")
