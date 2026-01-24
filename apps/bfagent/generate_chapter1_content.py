#!/usr/bin/env python
"""Generate Chapter 1 FULL CONTENT for Hugo & Luise"""

import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.handlers.processing_handlers.chapter_generate_handler import ChapterGenerateHandler

print("=" * 80)
print("📝 GENERATING CHAPTER 1 CONTENT: 'Hugo & Luise'")
print("=" * 80)

# Initialize handler
handler = ChapterGenerateHandler()

# Step 1: Generate Outline
print("\n⚙️  Step 1: Generating Outline...")
outline_context = {
    'action': 'generate_chapter_outline',
    'project_id': 3,
    'chapter_number': 1,
    'parameters': {
        'chapter_title': 'Ein gewöhnlicher Tag',
        'word_count_target': 3000,
        'focus_points': [
            "Introduce Hugo's world and daily life",
            "Show what's missing in his life",
            "Establish the social gap",
            "First mention or glimpse of Luise"
        ]
    }
}

outline_result = handler.execute(outline_context)

if not outline_result.get('success'):
    print(f"❌ Outline generation failed: {outline_result.get('error')}")
    exit(1)

outline = outline_result['data']['outline']
print("✅ Outline generated!")

# Step 2: Generate Content
print("\n⚙️  Step 2: Generating Chapter Content (2500-3000 words)...")
print("   This may take 30-60 seconds...")
print("-" * 80)

content_context = {
    'action': 'generate_chapter_content',
    'project_id': 3,
    'chapter_number': 1,
    'parameters': {
        'outline': outline,
        'style_notes': 'Engaging literary fiction with vivid descriptions, emotional depth, and natural dialogue',
        'include_dialogue': True,
    }
}

content_result = handler.execute(content_context)

if content_result.get('success'):
    print("\n✅ SUCCESS!")
    print("=" * 80)
    
    data = content_result['data']
    content = data['content']
    word_count = data['word_count']
    
    print(f"\n📊 STATISTICS:")
    print(f"   Word Count: {word_count}")
    print(f"   Chapter Number: {data['chapter_number']}")
    
    print("\n" + "=" * 80)
    print("📖 CHAPTER 1 CONTENT")
    print("=" * 80)
    print(f"\n{content}\n")
    
    print("=" * 80)
    print(f"✅ Chapter 1 Complete! ({word_count} words)")
    print("=" * 80)
    
    # Save to file
    filename = f"chapter1_hugo_luise_{word_count}words.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"CHAPTER 1: Ein gewöhnlicher Tag\n")
        f.write(f"Hugo und Luise - A Romance\n")
        f.write(f"Word Count: {word_count}\n")
        f.write("=" * 80 + "\n\n")
        f.write(content)
    
    print(f"\n💾 Saved to: {filename}")
    
else:
    print(f"\n❌ ERROR: {content_result.get('error')}")
    print(json.dumps(content_result, indent=2, default=str))

print("\n" + "=" * 80)
print("✅ Generation Complete!")
print("=" * 80)
