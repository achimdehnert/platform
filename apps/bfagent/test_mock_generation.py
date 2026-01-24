"""Quick test of mock image generation"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.bfagent.handlers.illustration_handler import ImageGenerationHandler
from apps.bfagent.models import BookProjects, GeneratedImage
from django.contrib.auth import get_user_model
import asyncio

User = get_user_model()

async def test_generation():
    print("Testing mock image generation...")
    
    # Get user
    user = User.objects.first()
    if not user:
        print("❌ No users found!")
        return
    print(f"✅ User: {user.username}")
    
    # Get project
    project = BookProjects.objects.filter(user=user).first()
    if not project:
        print("❌ No projects found!")
        return
    print(f"✅ Project: {project.title}")
    
    # Initialize handler in mock mode
    handler = ImageGenerationHandler(mock_mode=True)
    print(f"✅ Handler initialized (mock_mode={handler.mock_mode})")
    
    # Generate image
    print("\n🎨 Generating image...")
    results = await handler.generate_image(
        prompt="A test image for debugging",
        provider="dalle3",
        quality="standard",
        size="1024x1024"
    )
    
    print(f"\n✅ Generation successful!")
    print(f"   URL: {results[0]['image_url']}")
    print(f"   Cost: ${results[0]['cost_usd']}")
    print(f"   Time: {results[0]['generation_time_seconds']}s")
    
    # Check if images exist in database
    image_count = GeneratedImage.objects.filter(user=user).count()
    print(f"\n📊 Total images in database: {image_count}")
    
    if image_count > 0:
        latest = GeneratedImage.objects.filter(user=user).latest('created_at')
        print(f"   Latest image ID: {latest.pk}")
        print(f"   Image URL: {latest.image_url}")
        print(f"   Created: {latest.created_at}")

# Run test
asyncio.run(test_generation())
