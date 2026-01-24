"""
Management Command to create test images without API calls
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.bfagent.models import BookProjects
from apps.bfagent.models_illustration import (
    ImageStyleProfile,
    GeneratedImage,
    ImageStatus,
    ArtStyle,
    ImageType,
    AIProvider,
)
import uuid
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = 'Create test images with placeholder URLs for quick PoC testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            default='admin',
            help='Username to create images for'
        )
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='Number of test images to create'
        )

    def handle(self, *args, **options):
        username = options['user']
        count = options['count']

        # Get or create user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User "{username}" not found!')
            )
            return

        # Get or create a project
        project = BookProjects.objects.filter(user=user).first()
        if not project:
            project = BookProjects.objects.create(
                user=user,
                title="Test Book Project",
                genre="Fantasy",
                status="in_progress"
            )
            self.stdout.write(
                self.style.SUCCESS(f'Created test project: {project.title}')
            )

        # Get or create a style profile
        style_profile = ImageStyleProfile.objects.filter(user=user).first()
        if not style_profile:
            style_profile = ImageStyleProfile.objects.create(
                user=user,
                style_id=f"test_style_{uuid.uuid4().hex[:8]}",
                display_name="Epic Fantasy Test Style",
                art_style=ArtStyle.DIGITAL_ART,
                color_mood="vibrant, dramatic",
                base_prompt="epic fantasy digital art, dramatic lighting",
                preferred_provider=AIProvider.DALLE3
            )
            self.stdout.write(
                self.style.SUCCESS(f'Created test style: {style_profile.display_name}')
            )

        # Placeholder image URLs (from placeholder services)
        test_images = [
            {
                'url': 'https://picsum.photos/1024/1024?random=1',
                'prompt': 'A brave knight in shining armor facing a dragon',
                'type': ImageType.SCENE_ILLUSTRATION,
            },
            {
                'url': 'https://picsum.photos/1024/1024?random=2',
                'prompt': 'A magical forest with glowing mushrooms',
                'type': ImageType.LOCATION,
            },
            {
                'url': 'https://picsum.photos/1024/1024?random=3',
                'prompt': 'A wizard casting a powerful spell',
                'type': ImageType.CHARACTER_PORTRAIT,
            },
            {
                'url': 'https://picsum.photos/1024/1024?random=4',
                'prompt': 'An ancient castle on a misty mountain',
                'type': ImageType.LOCATION,
            },
            {
                'url': 'https://picsum.photos/1024/1024?random=5',
                'prompt': 'A mysterious hooded figure in the shadows',
                'type': ImageType.CHARACTER_PORTRAIT,
            },
        ]

        created_count = 0
        for i in range(min(count, len(test_images))):
            img_data = test_images[i % len(test_images)]
            
            image_id = f"test_img_{uuid.uuid4().hex[:12]}"
            
            GeneratedImage.objects.create(
                image_id=image_id,
                user=user,
                project=project,
                style_profile=style_profile,
                image_type=img_data['type'],
                status=ImageStatus.GENERATED,
                provider_used=AIProvider.DALLE3,
                prompt_used=img_data['prompt'],
                negative_prompt_used="low quality, blurry",
                image_url=img_data['url'],
                resolution="1024x1024",
                quality="standard",
                generation_time_seconds=3.5,
                cost_usd=Decimal("0.04"),
                content_context={},
            )
            
            created_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Created test image {i+1}/{count}: {img_data["prompt"][:50]}...'
                )
            )

        # Update style profile stats
        style_profile.usage_count += created_count
        style_profile.total_cost_usd += Decimal("0.04") * created_count
        style_profile.save()

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 Successfully created {created_count} test images!'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'View them at: http://localhost:8000/bookwriting/illustrations/gallery/'
            )
        )
