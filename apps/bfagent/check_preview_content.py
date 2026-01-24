"""
Check what's actually in PreviewSlide content_data
"""
import os
import sys
import django

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.presentation_studio.models import PreviewSlide

print("=" * 70)
print("CHECKING PREVIEW SLIDE CONTENT_DATA")
print("=" * 70)

# Get last 3 preview slides
previews = PreviewSlide.objects.order_by('-created_at')[:3]

for preview in previews:
    print(f"\n{'=' * 70}")
    print(f"ID: {preview.id}")
    print(f"Title: {preview.title}")
    print(f"Status: {preview.status}")
    print(f"Created: {preview.created_at}")
    print(f"\nCONTENT_DATA:")
    print("-" * 70)
    
    if preview.content_data:
        print(f"Keys: {list(preview.content_data.keys())}")
        
        content_blocks = preview.content_data.get('content_blocks', [])
        print(f"\nContent Blocks Count: {len(content_blocks)}")
        
        if content_blocks:
            print("\nFirst 3 blocks:")
            for idx, block in enumerate(content_blocks[:3], 1):
                print(f"\n  Block {idx}:")
                print(f"    Type: {block.get('type')}")
                content = block.get('content', '')
                preview_text = content[:80] + "..." if len(content) > 80 else content
                print(f"    Content: {preview_text}")
        else:
            print("  ⚠️  NO CONTENT BLOCKS!")
        
        # Other fields
        print(f"\nHeadline: {preview.content_data.get('headline')}")
        print(f"Quote: {preview.content_data.get('quote')}")
        print(f"Navigation: {preview.content_data.get('navigation')}")
    else:
        print("  ❌ content_data is EMPTY!")

print("\n" + "=" * 70)
