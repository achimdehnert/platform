#!/usr/bin/env python
"""Generate ALL 15 chapters for Hugo & Luise"""

import os
import django
import time
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.handlers.processing_handlers.chapter_generate_handler import ChapterGenerateHandler
from apps.bfagent.services.content_storage import ContentStorageService
from django.utils.text import slugify

print("=" * 80)
print("📚 GENERATING ALL 15 CHAPTERS FOR 'HUGO & LUISE'")
print("=" * 80)

# Chapter titles and focus points
chapters = [
    {
        'number': 1,
        'title': 'Ein gewöhnlicher Tag',
        'focus': ["Introduce Hugo's world", "Show social gap", "First glimpse of Luise"]
    },
    {
        'number': 2,
        'title': 'Die Begegnung',
        'focus': ["First real meeting", "Instant connection", "Social barriers evident"]
    },
    {
        'number': 3,
        'title': 'Verbotene Gedanken',
        'focus': ["Hugo's growing feelings", "Luise's curiosity", "Family expectations introduced"]
    },
    {
        'number': 4,
        'title': 'Heimliche Treffen',
        'focus': ["Secret meetings begin", "Deepening connection", "Risk of discovery"]
    },
    {
        'number': 5,
        'title': 'Der Konflikt',
        'focus': ["Herr Richter discovers", "Family confrontation", "Stakes raised"]
    },
    {
        'number': 6,
        'title': 'Verzweiflung',
        'focus': ["Forced separation", "Hugo's struggle", "Luise's defiance"]
    },
    {
        'number': 7,
        'title': 'Ein Plan',
        'focus': ["Hugo works harder", "Plans to prove himself", "Hope rekindled"]
    },
    {
        'number': 8,
        'title': 'Die Prüfung',
        'focus': ["Hugo's opportunity", "Challenges faced", "Character growth"]
    },
    {
        'number': 9,
        'title': 'Luises Entscheidung',
        'focus': ["Luise must choose", "Family vs love", "Internal conflict"]
    },
    {
        'number': 10,
        'title': 'Der Wendepunkt',
        'focus': ["Major revelation", "Perspectives shift", "New possibilities"]
    },
    {
        'number': 11,
        'title': 'Zusammenhalt',
        'focus': ["United front", "Facing opposition together", "Love strengthens"]
    },
    {
        'number': 12,
        'title': 'Die Wahrheit',
        'focus': ["Secrets revealed", "Understanding grows", "Path forward emerges"]
    },
    {
        'number': 13,
        'title': 'Herausforderung',
        'focus': ["Final obstacle", "Ultimate test", "All or nothing"]
    },
    {
        'number': 14,
        'title': 'Versöhnung',
        'focus': ["Resolution begins", "Acceptance", "Bridge between worlds"]
    },
    {
        'number': 15,
        'title': 'Neubeginn',
        'focus': ["Happy ending", "Love triumphs", "New life together"]
    },
]

# Initialize
handler = ChapterGenerateHandler()
storage = ContentStorageService()
project_slug = slugify("Hugo und Luise.")

# Statistics
start_time = datetime.now()
results = []
total_words = 0

print(f"\n⏱️  Started at: {start_time.strftime('%H:%M:%S')}")
print(f"📁 Saving to: ~/domains/{project_slug}/chapters/")
print("\n" + "=" * 80)

# Generate each chapter
for chapter_info in chapters:
    chapter_num = chapter_info['number']
    chapter_title = chapter_info['title']
    focus_points = chapter_info['focus']
    
    print(f"\n📖 CHAPTER {chapter_num}: {chapter_title}")
    print(f"   Focus: {', '.join(focus_points)}")
    
    chapter_start = time.time()
    
    try:
        # Step 1: Generate Outline
        print(f"   ⚙️  Generating outline...")
        outline_context = {
            'action': 'generate_chapter_outline',
            'project_id': 3,
            'chapter_number': chapter_num,
            'parameters': {
                'chapter_title': chapter_title,
                'word_count_target': 3000,
                'focus_points': focus_points
            }
        }
        
        outline_result = handler.execute(outline_context)
        
        if not outline_result.get('success'):
            print(f"   ❌ Outline failed: {outline_result.get('error')}")
            results.append({
                'chapter': chapter_num,
                'success': False,
                'error': 'Outline generation failed'
            })
            continue
        
        outline = outline_result['data']['outline']
        print(f"   ✅ Outline generated")
        
        # Step 2: Generate Content
        print(f"   ⚙️  Generating content...")
        content_context = {
            'action': 'generate_chapter_content',
            'project_id': 3,
            'chapter_number': chapter_num,
            'parameters': {
                'outline': outline,
                'style_notes': 'Engaging German literary fiction with emotional depth and natural dialogue',
                'include_dialogue': True,
            }
        }
        
        content_result = handler.execute(content_context)
        
        if not content_result.get('success'):
            print(f"   ❌ Content failed: {content_result.get('error')}")
            results.append({
                'chapter': chapter_num,
                'success': False,
                'error': 'Content generation failed'
            })
            continue
        
        data = content_result['data']
        word_count = data['word_count']
        saved_path = data.get('saved_path')
        
        chapter_time = time.time() - chapter_start
        total_words += word_count
        
        print(f"   ✅ Chapter {chapter_num} complete!")
        print(f"   📊 Words: {word_count} | Time: {chapter_time:.1f}s")
        print(f"   💾 Saved: {saved_path}")
        
        results.append({
            'chapter': chapter_num,
            'title': chapter_title,
            'success': True,
            'word_count': word_count,
            'time': chapter_time,
            'path': saved_path
        })
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        results.append({
            'chapter': chapter_num,
            'success': False,
            'error': str(e)
        })

# Final statistics
end_time = datetime.now()
duration = (end_time - start_time).total_seconds()

print("\n" + "=" * 80)
print("📊 GENERATION COMPLETE!")
print("=" * 80)

successful = sum(1 for r in results if r.get('success'))
failed = len(results) - successful

print(f"\n⏱️  Duration: {duration/60:.1f} minutes ({duration:.0f} seconds)")
print(f"📝 Chapters Generated: {successful}/{len(chapters)}")
print(f"❌ Failed: {failed}")
print(f"📄 Total Words: {total_words:,}")
print(f"⚡ Average: {total_words/successful if successful > 0 else 0:.0f} words/chapter")
print(f"🕐 Average Time: {duration/successful if successful > 0 else 0:.1f}s/chapter")

# Show results table
print("\n" + "=" * 80)
print("CHAPTER RESULTS:")
print("=" * 80)
print(f"{'Ch':<4} {'Title':<25} {'Words':<8} {'Time':<8} {'Status'}")
print("-" * 80)

for result in results:
    ch = result['chapter']
    title = result.get('title', '?')[:24]
    if result.get('success'):
        words = result.get('word_count', 0)
        time_taken = result.get('time', 0)
        status = "✅"
        print(f"{ch:<4} {title:<25} {words:<8} {time_taken:<8.1f} {status}")
    else:
        error = result.get('error', 'Unknown')[:20]
        status = f"❌ {error}"
        print(f"{ch:<4} {title:<25} {'N/A':<8} {'N/A':<8} {status}")

# Storage stats
print("\n" + "=" * 80)
print("📁 STORAGE STATISTICS:")
print("=" * 80)

stats = storage.get_project_stats(project_slug)
print(f"   Project: {stats['path']}")
print(f"   Chapters: {stats['chapter_count']}")
print(f"   Total Words: {stats['total_words']:,}")

print("\n" + "=" * 80)
print("✅ ALL DONE! BOOK GENERATION COMPLETE!")
print("=" * 80)

print(f"""
📚 NEXT STEPS:
--------------
1. Review chapters in: ~/domains/{project_slug}/chapters/
2. Export to DOCX/PDF
3. Edit and refine as needed
4. Celebrate! 🎉

Your book "Hugo und Luise" is ready!
""")
