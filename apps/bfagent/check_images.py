import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models import GeneratedImage

print("=" * 60)
print("GENERATED IMAGES IN DATABASE:")
print("=" * 60)

total = GeneratedImage.objects.count()
print(f"\nTotal images in DB: {total}\n")

if total > 0:
    images = GeneratedImage.objects.all().order_by('-created_at')[:10]
    for img in images:
        print(f"ID: {img.id}")
        print(f"  Chapter: {img.chapter_id}")
        print(f"  URL: {img.image_url}")
        print(f"  Prompt: {img.prompt_used[:80]}...")
        print(f"  Provider: {img.provider_used}")
        print(f"  Status: {img.status}")
        print(f"  Created: {img.created_at}")
        print()
else:
    print("❌ NO IMAGES FOUND IN DATABASE!")
    print("\nThis means:")
    print("1. Auto-Illustrate was called but images weren't saved")
    print("2. There was an error during image generation")
    print("3. Check the terminal logs for errors")

print("=" * 60)
