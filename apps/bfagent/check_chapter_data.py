"""
Check chapter data in database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models import BookProjects, BookChapters

print("\n" + "="*60)
print("🔍 CHAPTER DATA CHECK")
print("="*60 + "\n")

# Get Essay ID 3
essay = BookProjects.objects.get(id=3)
print(f"📘 Essay: {essay.title}\n")

# Get all chapters
chapters = essay.chapters.all().order_by('chapter_number')

for ch in chapters:
    print(f"Chapter {ch.chapter_number}: {ch.title}")
    print(f"  outline: '{ch.outline}'")
    print(f"  summary: '{ch.summary}'")
    print(f"  notes: '{ch.notes}'")
    print(f"  target_word_count: {ch.target_word_count}")
    print(f"  writing_stage: {ch.writing_stage}")
    print()

print("="*60)
