#!/usr/bin/env python
"""
Quick Scan: Finde alle hardcoded Choices im Projekt
"""
import os
import re
from pathlib import Path

def scan_hardcoded_choices():
    """Scanne nach hardcoded choices in Python Files"""
    
    apps_dir = Path("apps")
    results = {
        "forms": [],
        "models": [],
        "views": []
    }
    
    # Pattern für hardcoded choices
    choice_pattern = re.compile(r'choices\s*=\s*\[', re.IGNORECASE)
    
    for py_file in apps_dir.rglob("*.py"):
        # Skip migrations und __pycache__
        if "migration" in str(py_file) or "__pycache__" in str(py_file):
            continue
            
        try:
            content = py_file.read_text(encoding='utf-8')
            
            if choice_pattern.search(content):
                file_type = "other"
                if "forms.py" in str(py_file):
                    file_type = "forms"
                elif "models" in str(py_file):
                    file_type = "models"
                elif "views" in str(py_file):
                    file_type = "views"
                
                # Extrahiere Zeilen mit choices
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if choice_pattern.search(line):
                        context = lines[max(0, i-2):min(len(lines), i+10)]
                        results.setdefault(file_type, []).append({
                            'file': str(py_file),
                            'line': i,
                            'context': '\n'.join(context)
                        })
        except Exception as e:
            pass
    
    return results

if __name__ == "__main__":
    print("\n" + "="*80)
    print("HARDCODED CHOICES SCAN")
    print("="*80 + "\n")
    
    results = scan_hardcoded_choices()
    
    for file_type, items in results.items():
        if items:
            print(f"\n### {file_type.upper()} ({len(items)} found)")
            print("-" * 80)
            for item in items[:5]:  # Show first 5
                print(f"\nFile: {item['file']}:{item['line']}")
                print("Context:")
                print(item['context'][:200] + "...")
            
            if len(items) > 5:
                print(f"\n... und {len(items) - 5} weitere")
    
    total = sum(len(items) for items in results.values())
    print(f"\n" + "="*80)
    print(f"TOTAL: {total} hardcoded choices gefunden")
    print("="*80)
    
    print("\n🎯 EMPFEHLUNG:")
    print("1. Beginne mit Forms (am einfachsten)")
    print("2. Dann Models (benötigt Migrations)")
    print("3. Zuletzt Views (meistens schon OK)")
