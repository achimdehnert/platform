#!/usr/bin/env python
"""Generate Chapter 1 for Hugo & Luise"""

import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.handlers.processing_handlers.chapter_generate_handler import ChapterGenerateHandler

print("=" * 80)
print("📝 GENERATING CHAPTER 1: 'Hugo & Luise'")
print("=" * 80)

# Initialize handler
handler = ChapterGenerateHandler()

# Context for outline generation
context = {
    'action': 'generate_chapter_outline',
    'project_id': 3,
    'chapter_number': 1,
    'parameters': {
        'chapter_title': 'Ein gewöhnlicher Tag',  # Set-Up chapter
        'word_count_target': 3000,
        'focus_points': [
            "Introduce Hugo's world and daily life",
            "Show what's missing in his life",
            "Establish the social gap",
            "First mention or glimpse of Luise"
        ]
    }
}

print("\n📋 Generation Context:")
print(json.dumps(context, indent=2, ensure_ascii=False))

print("\n⚙️  Generating outline...")
print("-" * 80)

try:
    result = handler.execute(context)
    
    print("\n✅ SUCCESS!")
    print("=" * 80)
    
    if result.get('success'):
        print("\n📊 RESULT:")
        print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
        
        # Extract key information
        if 'data' in result:
            data = result['data']
            
            print("\n" + "=" * 80)
            print("📖 CHAPTER 1 OUTLINE")
            print("=" * 80)
            
            if 'outline' in data:
                print(f"\n{data['outline']}")
            
            if 'project_context' in data:
                ctx = data['project_context']
                print("\n" + "=" * 80)
                print("🎯 ENRICHED CONTEXT USED:")
                print("=" * 80)
                print(f"\nProject: {ctx.get('title')}")
                print(f"Genre: {ctx.get('genre')}")
                print(f"Target Audience: {ctx.get('target_audience')}")
                print(f"\nProtagonist: {ctx.get('protagonist_name')}")
                print(f"Antagonist: {ctx.get('antagonist_name')}")
                print(f"\nThemes: {ctx.get('themes')}")
                
                if ctx.get('current_beat'):
                    print(f"\nCurrent Beat: {ctx.get('current_beat')}")
                    
    else:
        print(f"\n❌ ERROR: {result.get('error')}")
        
except Exception as e:
    print(f"\n❌ EXCEPTION: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("✅ Generation Complete!")
print("=" * 80)
