"""
Analyze which scripts are used in Makefile
Version: 1.0.0

Scans all Makefiles and extracts script references
"""

import re
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent

def find_script_references():
    """Find all script references in Makefiles"""
    script_refs = defaultdict(list)
    
    # Find all Makefile* files
    makefiles = list(PROJECT_ROOT.glob("Makefile*"))
    
    for makefile in makefiles:
        if makefile.is_file():
            content = makefile.read_text(encoding='utf-8')
            
            # Pattern: python scripts/something.py
            pattern = r'python\s+scripts/([a-zA-Z0-9_\-]+\.py)'
            matches = re.findall(pattern, content)
            
            for script in matches:
                script_refs[script].append(makefile.name)
    
    return script_refs


def main():
    print("🔍 Makefile Script Analysis")
    print("=" * 70)
    
    script_refs = find_script_references()
    
    if not script_refs:
        print("❌ No script references found!")
        return
    
    # Sort by usage count
    sorted_scripts = sorted(script_refs.items(), key=lambda x: len(x[1]), reverse=True)
    
    print(f"\n📊 Found {len(sorted_scripts)} unique scripts in Makefiles\n")
    
    # Active Makefile Tools (used in make commands)
    print("🎯 ACTIVE MAKEFILE TOOLS (used in make commands):")
    print("-" * 70)
    for script, makefiles in sorted_scripts:
        count = len(makefiles)
        makefile_list = ", ".join(makefiles)
        print(f"  {script:<40} ({count}x in: {makefile_list})")
    
    print("\n" + "=" * 70)
    print(f"✅ Total: {len(sorted_scripts)} scripts actively used in Makefile")
    
    # Generate Python list for reorganize script
    print("\n💡 Python list for reorganize_scripts.py:")
    print("-" * 70)
    print("MAKEFILE_TOOLS = [")
    for script, _ in sorted_scripts:
        print(f'    "{script}",')
    print("]")
    
    # Check which scripts exist
    print("\n🔍 Verification:")
    print("-" * 70)
    missing = []
    existing = []
    for script, _ in sorted_scripts:
        script_path = PROJECT_ROOT / "scripts" / script
        if script_path.exists():
            existing.append(script)
        else:
            missing.append(script)
    
    print(f"  ✅ Existing: {len(existing)}")
    print(f"  ⚠️  Missing: {len(missing)}")
    
    if missing:
        print("\n⚠️  Missing scripts:")
        for script in missing:
            print(f"    - {script}")


if __name__ == "__main__":
    main()
