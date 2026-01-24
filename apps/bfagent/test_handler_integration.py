"""
Quick test for ChapterGenerateHandler with DatabaseContextEnricher
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.bfagent.handlers.processing_handlers.chapter_generate_handler import ChapterGenerateHandler
import json

def test_chapter_handler():
    """Test ChapterGenerateHandler with enriched context"""
    print("=" * 80)
    print("Testing ChapterGenerateHandler with DatabaseContextEnricher")
    print("=" * 80)
    
    handler = ChapterGenerateHandler()
    
    # Test with Hugo & Luise project
    test_context = {
        'action': 'generate_chapter_outline',
        'project_id': 3,
        'chapter_number': 1,
        'parameters': {
            'chapter_title': 'Test Chapter',
            'word_count_target': 3000
        }
    }
    
    print("\n📋 Test Context:")
    print(json.dumps(test_context, indent=2))
    
    try:
        print("\n⚙️  Executing handler...")
        result = handler.execute(test_context)
        
        print("\n✅ SUCCESS!")
        print("\n📊 Result:")
        print(json.dumps(result, indent=2, default=str))
        
        # Check if enriched context is present
        if 'data' in result and 'project_context' in result['data']:
            context = result['data']['project_context']
            print("\n🎯 Enriched Context Keys:")
            print(f"   - Keys: {list(context.keys())}")
            
            # Check for database-enriched fields
            enriched_fields = []
            if 'story_position' in context:
                enriched_fields.append('✅ story_position (computed)')
            if 'current_beat' in context:
                enriched_fields.append('✅ current_beat (beat_sheet)')
            if 'previous_chapters' in context:
                enriched_fields.append('✅ previous_chapters (related_query)')
            
            if enriched_fields:
                print("\n🎉 Database-Enriched Fields Found:")
                for field in enriched_fields:
                    print(f"   {field}")
            else:
                print("\n⚠️  Using fallback context (enrichment may have failed)")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    success = test_chapter_handler()
    sys.exit(0 if success else 1)
