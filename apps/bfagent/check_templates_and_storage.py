#!/usr/bin/env python
"""Check prompt templates and storage structure"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models import PromptTemplate, BookProjects
from django.conf import settings

print("=" * 80)
print("📊 PROMPT TEMPLATES & STORAGE CHECK")
print("=" * 80)

# Check Chapter Templates
print("\n✅ CHAPTER PROMPT TEMPLATES:")
chapter_templates = PromptTemplate.objects.filter(category='chapter')
print(f"   Found: {chapter_templates.count()} templates")

for template in chapter_templates[:5]:
    print(f"   - {template.template_key}: {template.name}")
    if hasattr(template, 'system_prompt'):
        print(f"     System Prompt: {len(template.system_prompt)} chars")

if chapter_templates.count() == 0:
    print("   ⚠️  No chapter templates found in database!")
    print("   → Templates are currently HARDCODED in chapter_generate_handler.py")

# Check current storage location
print("\n📁 CURRENT STORAGE:")
print(f"   Project Root: {settings.BASE_DIR}")
print(f"   Media Root: {getattr(settings, 'MEDIA_ROOT', 'Not configured')}")

# Check for books directory
books_dir = os.path.join(settings.BASE_DIR, 'books')
if os.path.exists(books_dir):
    print(f"   Books Directory: {books_dir}")
    print(f"   Exists: ✅")
    # List contents
    items = os.listdir(books_dir)
    print(f"   Contents: {len(items)} items")
    for item in items[:5]:
        print(f"     - {item}")
else:
    print(f"   Books Directory: {books_dir}")
    print(f"   Exists: ❌")

# Check where current script saved file
current_dir = os.getcwd()
print(f"\n📝 CURRENT WORKING DIRECTORY:")
print(f"   {current_dir}")

# Look for generated files
for f in os.listdir(current_dir):
    if f.startswith('chapter1_'):
        print(f"   Found: {f}")

# Suggest better structure
print("\n" + "=" * 80)
print("💡 SUGGESTED STORAGE STRUCTURE:")
print("=" * 80)

print("""
Option 1: DOMAIN-BASED (Recommended)
-------------------------------------
C:/Users/achim/
  └── domains/
      └── hugo-und-luise/
          ├── metadata.json
          ├── outline.md
          ├── chapters/
          │   ├── chapter_01.md
          │   ├── chapter_02.md
          │   └── ...
          ├── characters/
          │   ├── hugo.json
          │   └── luise.json
          └── exports/
              └── hugo-und-luise_full.docx

Option 2: PROJECT-BASED (In Repo)
----------------------------------
C:/Users/achim/github/bfagent/
  └── content/
      └── projects/
          └── project_3_hugo_luise/
              ├── chapters/
              ├── characters/
              └── exports/

Option 3: MEDIA ROOT (Django Standard)
---------------------------------------
C:/Users/achim/github/bfagent/
  └── media/
      └── books/
          └── hugo-und-luise/
              ├── chapters/
              ├── characters/
              └── exports/
""")

print("=" * 80)
print("🎯 RECOMMENDATION:")
print("=" * 80)
print("""
Use OPTION 1 (Domain-based) because:
- ✅ Clean separation from code
- ✅ Easy to backup/share
- ✅ User's home directory
- ✅ Not affected by git operations
- ✅ Scalable for multiple books

Implementation:
1. Create ~/domains/ directory
2. Each book = subdomain (project slug)
3. Store all generated content there
4. Add path to BookProjects model
""")

print("\n" + "=" * 80)
