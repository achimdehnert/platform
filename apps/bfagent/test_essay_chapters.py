"""
Quick test script to check Essay auto-chapter creation
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models import BookProjects, BookChapters, BookTypes

print("\n" + "="*60)
print("📚 ESSAY CHAPTER TEST")
print("="*60 + "\n")

# Check if Essay BookType exists
essay_type = BookTypes.objects.filter(name='Essay').first()
if essay_type:
    print(f"✅ Essay BookType found (ID: {essay_type.id})")
    print(f"   Configuration: {essay_type.configuration[:100]}...")
else:
    print("❌ Essay BookType NOT found!")
    print("\nRun: python manage.py create_essay_booktype")
    exit(1)

print()

# Find all Essays
essays = BookProjects.objects.filter(book_type__name='Essay')
print(f"📖 Found {essays.count()} Essay(s) in database\n")

if essays.count() == 0:
    print("⚠️  No Essays found. Create one at /books/create/")
    exit(0)

# Check each Essay
for essay in essays:
    print(f"📘 Essay: {essay.title}")
    print(f"   ID: {essay.id}")
    print(f"   Created: {essay.created_at}")
    
    # Count chapters
    chapters = essay.chapters.all().order_by('chapter_number')
    chapter_count = chapters.count()
    
    print(f"   Chapters: {chapter_count}")
    
    if chapter_count == 0:
        print("   ❌ NO CHAPTERS! Auto-creation failed!")
        print(f"   Debug - book_type.name: '{essay.book_type.name}'")
    else:
        print("   ✅ Chapters found:")
        for ch in chapters:
            print(f"      {ch.chapter_number}. {ch.title} ({ch.target_word_count} words)")
    
    print()

print("="*60)
print("\n💡 To manually create chapters for an Essay:")
print("   essay = BookProjects.objects.get(id=X)")
print("   essay._create_essay_chapters()")
print()
