"""Test mock image generation"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.bfagent.models import BookProjects, GeneratedImage
from apps.bfagent.handlers.illustration_handler import ImageGenerationHandler
import asyncio

User = get_user_model()


class Command(BaseCommand):
    help = 'Test mock image generation and check database'

    def handle(self, *args, **options):
        self.stdout.write("Testing mock image generation...")

        # Get user
        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR("❌ No users found!"))
            return
        self.stdout.write(self.style.SUCCESS(f"✅ User: {user.username}"))

        # Get project
        project = BookProjects.objects.filter(user=user).first()
        if not project:
            self.stdout.write(self.style.ERROR("❌ No projects found!"))
            return
        self.stdout.write(self.style.SUCCESS(f"✅ Project: {project.title}"))

        # Check existing images
        before_count = GeneratedImage.objects.filter(user=user).count()
        self.stdout.write(f"\n📊 Images before test: {before_count}")

        # Initialize handler
        handler = ImageGenerationHandler(mock_mode=True)
        self.stdout.write(
            self.style.SUCCESS(f"✅ Handler initialized (mock_mode={handler.mock_mode})")
        )

        # Generate image
        self.stdout.write("\n🎨 Generating image...")

        async def generate():
            return await handler.generate_image(
                prompt="Test image from management command",
                provider="dalle3",
                quality="standard",
                size="1024x1024"
            )

        results = asyncio.run(generate())

        self.stdout.write(self.style.SUCCESS(f"\n✅ Generation successful!"))
        self.stdout.write(f"   URL: {results[0]['image_url']}")
        self.stdout.write(f"   Cost: ${results[0]['cost_usd']}")
        self.stdout.write(f"   Time: {results[0]['generation_time_seconds']}s")

        # Check images after
        after_count = GeneratedImage.objects.filter(user=user).count()
        self.stdout.write(f"\n📊 Images after test: {after_count}")
        self.stdout.write(f"📈 New images: {after_count - before_count}")

        if after_count > before_count:
            latest = GeneratedImage.objects.filter(user=user).latest('created_at')
            self.stdout.write(
                self.style.SUCCESS(f"\n✅ Latest image saved to database!")
            )
            self.stdout.write(f"   ID: {latest.pk}")
            self.stdout.write(f"   Image ID: {latest.image_id}")
            self.stdout.write(f"   URL: {latest.image_url}")
            self.stdout.write(f"   Prompt: {latest.prompt_used}")
        else:
            self.stdout.write(
                self.style.WARNING("⚠️ No new images created in database!")
            )
