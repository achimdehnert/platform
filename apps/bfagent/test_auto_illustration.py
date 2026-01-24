"""
Quick Test for Auto-Illustration Handler
Run: python test_auto_illustration.py
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import asyncio
from apps.bfagent.handlers.chapter_illustration_handler import ChapterIllustrationHandler

async def test_mvp():
    print("🎨 Testing Auto-Illustration MVP...")
    print("="*60)
    
    # Test chapter text
    chapter_text = """
    The old castle stood against the moonlit sky, its towers reaching into the darkness.
    
    Inside, Sarah crept through the dusty corridors, her torch casting dancing shadows on the ancient stone walls.
    
    She paused at the sound of footsteps echoing from the chamber ahead. Someone - or something - was following her.
    
    The door burst open with a crash. A figure emerged from the darkness, cloaked in shadow.
    
    "I've been waiting for you," the stranger whispered, eyes glowing in the dim light.
    
    Sarah stepped back, her hand reaching for the amulet around her neck. This was the moment she had been dreading.
    
    With a surge of energy, she raised the amulet high. Blue light flooded the chamber, revealing the truth at last.
    """
    
    # Initialize handler in MOCK MODE (no API calls, instant, free!)
    handler = ChapterIllustrationHandler(mock_mode=True)
    
    print("\n📍 Phase 1: Analyzing chapter...")
    result = await handler.auto_illustrate_chapter(
        chapter_id=1,
        chapter_text=chapter_text,
        max_illustrations=3,
        style_profile="fantasy, dramatic lighting, detailed illustration",
        provider='dalle3',
        quality='standard'
    )
    
    print(f"\n✅ COMPLETED!")
    print(f"   • Positions found: {result.total_positions_found}")
    print(f"   • Images generated: {result.images_generated}")
    print(f"   • Total cost: ${result.total_cost_usd:.4f}")
    print(f"   • Duration: {result.duration_seconds:.2f}s")
    
    print(f"\n🖼️  Generated Images:")
    for i, img in enumerate(result.generated_images, 1):
        print(f"\n   Image {i}:")
        print(f"   • URL: {img['image_url']}")
        print(f"   • Paragraph: {img['position']['paragraph_index']}")
        print(f"   • Type: {img['position']['illustration_type']}")
        print(f"   • Priority: {img['position']['priority']}")
    
    print("\n" + "="*60)
    print("✅ MVP TEST SUCCESSFUL!")
    print("💡 Next: Integrate with views, add UI, setup Celery for async")

if __name__ == "__main__":
    asyncio.run(test_mvp())
