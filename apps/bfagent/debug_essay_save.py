"""
Debug script to test Essay auto-chapter creation
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models import BookProjects, BookChapters, BookTypes

print("\n" + "="*60)
print("🔍 DEBUG: Essay Auto-Chapter Creation")
print("="*60 + "\n")

# Get Essay BookType
essay_type = BookTypes.objects.get(name='Essay')
print(f"✅ Essay BookType: {essay_type.name} (ID: {essay_type.id})")

# Get the latest essay (ID: 3)
essay = BookProjects.objects.get(id=3)
print(f"\n📘 Essay: {essay.title} (ID: {essay.id})")
print(f"   book_type: {essay.book_type.name}")
print(f"   book_type.id: {essay.book_type.id}")
print(f"   Chapters: {essay.chapters.count()}")

# Try to manually trigger chapter creation
print(f"\n🔧 Manually triggering _create_essay_chapters()...")
try:
    essay._create_essay_chapters()
    new_count = essay.chapters.count()
    print(f"✅ Success! Now has {new_count} chapters")
    
    for ch in essay.chapters.all().order_by('chapter_number'):
        print(f"   {ch.chapter_number}. {ch.title} ({ch.target_word_count} words)")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
