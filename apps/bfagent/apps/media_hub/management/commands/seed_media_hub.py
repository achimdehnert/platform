"""
Seed Media Hub Presets
======================

Creates initial presets for the Media Hub:
- StylePresets (illustration, comic, cover, food)
- FormatPresets (various dimensions)
- QualityPresets (draft, standard, final)
- VoicePresets (TTS voices)
- ParameterMappings (field mappings)

Usage:
    python manage.py seed_media_hub
    python manage.py seed_media_hub --force  # Overwrite existing
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.media_hub.models import (
    StylePreset,
    FormatPreset,
    QualityPreset,
    VoicePreset,
    ParameterMapping,
)


class Command(BaseCommand):
    help = 'Seed Media Hub with initial presets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing presets'
        )

    def handle(self, *args, **options):
        force = options['force']
        
        with transaction.atomic():
            self.seed_style_presets(force)
            self.seed_format_presets(force)
            self.seed_quality_presets(force)
            self.seed_voice_presets(force)
            self.seed_parameter_mappings(force)
        
        self.stdout.write(self.style.SUCCESS('✅ Media Hub seeding complete!'))

    def seed_style_presets(self, force: bool):
        """Seed style presets based on MVP documentation."""
        
        presets = [
            # Illustration Styles
            {
                'key': 'illustration_cinematic_v1',
                'name': 'Cinematic Illustration',
                'description': 'Dramatic, high-detail illustrations with cinematic lighting',
                'category': StylePreset.Category.ILLUSTRATION,
                'prompt_style': 'cinematic illustration, high detail, dramatic lighting, coherent anatomy, professional artwork, masterpiece',
                'prompt_negative': 'low quality, blurry, watermark, text, deformed anatomy, bad hands, extra fingers',
                'defaults': {
                    'steps': 30,
                    'cfg': 6.5,
                    'sampler': 'dpmpp_2m',
                    'scheduler': 'karras'
                },
                'color_palette': ['#1a1a2e', '#16213e', '#0f3460', '#e94560'],
                'is_approved': True,
            },
            {
                'key': 'illustration_watercolor_v1',
                'name': 'Watercolor Illustration',
                'description': 'Soft watercolor style with dreamy atmosphere',
                'category': StylePreset.Category.ILLUSTRATION,
                'prompt_style': 'watercolor painting, soft edges, dreamy atmosphere, gentle colors, artistic, flowing brushstrokes, traditional media',
                'prompt_negative': 'digital art, sharp edges, neon colors, photorealistic, 3d render',
                'defaults': {
                    'steps': 28,
                    'cfg': 7.0,
                    'sampler': 'dpmpp_2m',
                    'scheduler': 'karras'
                },
                'color_palette': ['#f0e6d3', '#c9b99a', '#8b7355', '#5d4e37'],
                'is_approved': True,
            },
            # Comic Styles
            {
                'key': 'comic_realistic_v1',
                'name': 'Realistic Comic',
                'description': 'Clean, realistic comic style with consistent characters',
                'category': StylePreset.Category.COMIC,
                'prompt_style': 'realistic comic style, clean ink lines, consistent characters, professional comic art, detailed shading',
                'prompt_negative': 'messy lines, sketchy, distorted face, extra fingers, anime style',
                'defaults': {
                    'steps': 35,
                    'cfg': 6.0,
                    'sampler': 'dpmpp_2m',
                    'scheduler': 'karras'
                },
                'color_palette': ['#2c3e50', '#e74c3c', '#f39c12', '#ecf0f1'],
                'is_approved': True,
            },
            {
                'key': 'comic_manga_v1',
                'name': 'Manga Style',
                'description': 'Japanese manga aesthetic with expressive characters',
                'category': StylePreset.Category.COMIC,
                'prompt_style': 'manga style, anime art, expressive eyes, dynamic poses, clean lineart, japanese comic',
                'prompt_negative': 'western comic, realistic, 3d render, photo',
                'defaults': {
                    'steps': 30,
                    'cfg': 7.0,
                    'sampler': 'dpmpp_2m',
                    'scheduler': 'karras'
                },
                'color_palette': ['#ff6b6b', '#4ecdc4', '#ffe66d', '#2c3e50'],
                'is_approved': True,
            },
            # Cover Art Styles
            {
                'key': 'cover_fantasy_v1',
                'name': 'Fantasy Book Cover',
                'description': 'Epic fantasy book cover style',
                'category': StylePreset.Category.COVER,
                'prompt_style': 'epic fantasy book cover, dramatic composition, magical atmosphere, professional artwork, bestseller cover art',
                'prompt_negative': 'amateur, low resolution, text, watermark, logo',
                'defaults': {
                    'steps': 40,
                    'cfg': 7.5,
                    'sampler': 'dpmpp_2m',
                    'scheduler': 'karras'
                },
                'color_palette': ['#2e1a47', '#6b3fa0', '#f9c846', '#1a1a2e'],
                'is_approved': True,
            },
            {
                'key': 'cover_thriller_v1',
                'name': 'Thriller Book Cover',
                'description': 'Dark, suspenseful thriller cover style',
                'category': StylePreset.Category.COVER,
                'prompt_style': 'thriller book cover, dark atmosphere, suspenseful, noir style, high contrast, professional',
                'prompt_negative': 'bright colors, cheerful, cartoon, low quality',
                'defaults': {
                    'steps': 35,
                    'cfg': 7.0,
                    'sampler': 'dpmpp_2m',
                    'scheduler': 'karras'
                },
                'color_palette': ['#1a1a1a', '#8b0000', '#c0c0c0', '#2c2c2c'],
                'is_approved': True,
            },
            # Food Photography Styles
            {
                'key': 'food_hero_shot_v1',
                'name': 'Food Hero Shot',
                'description': 'Professional food photography with dramatic presentation',
                'category': StylePreset.Category.FOOD,
                'prompt_style': 'professional food photography, hero shot, shallow depth of field, steam rising, dramatic lighting, appetizing, food magazine cover',
                'prompt_negative': 'blurry, amateur, bad lighting, unappetizing, artificial',
                'defaults': {
                    'steps': 30,
                    'cfg': 7.5,
                    'sampler': 'dpmpp_2m',
                    'scheduler': 'karras'
                },
                'color_palette': [],
                'is_approved': True,
            },
            {
                'key': 'food_overhead_v1',
                'name': 'Overhead Food Shot',
                'description': 'Clean overhead food photography style',
                'category': StylePreset.Category.FOOD,
                'prompt_style': 'overhead shot, flat lay, food photography, marble surface, natural lighting, professional, appetizing, clean composition',
                'prompt_negative': 'blurry, dark, underexposed, artificial, plastic looking',
                'defaults': {
                    'steps': 28,
                    'cfg': 7.0,
                    'sampler': 'dpmpp_2m',
                    'scheduler': 'karras'
                },
                'color_palette': [],
                'is_approved': True,
            },
        ]
        
        created = 0
        updated = 0
        
        for data in presets:
            key = data.pop('key')
            obj, was_created = StylePreset.objects.update_or_create(
                key=key,
                defaults=data
            ) if force else (StylePreset.objects.get_or_create(key=key, defaults=data))
            
            if was_created:
                created += 1
            elif force:
                updated += 1
        
        self.stdout.write(f'  StylePresets: {created} created, {updated} updated')

    def seed_format_presets(self, force: bool):
        """Seed format presets."""
        
        presets = [
            # General
            {
                'key': 'square_1024',
                'name': 'Square (1024x1024)',
                'description': 'Standard square format',
                'use_case': FormatPreset.UseCase.GENERAL,
                'width': 1024,
                'height': 1024,
                'meta': {'dpi': 72},
                'is_approved': True,
            },
            {
                'key': 'landscape_16_9',
                'name': 'Landscape 16:9',
                'description': 'Widescreen landscape format',
                'use_case': FormatPreset.UseCase.GENERAL,
                'width': 1344,
                'height': 768,
                'meta': {'dpi': 72},
                'is_approved': True,
            },
            {
                'key': 'portrait_3_4',
                'name': 'Portrait 3:4',
                'description': 'Standard portrait format',
                'use_case': FormatPreset.UseCase.GENERAL,
                'width': 896,
                'height': 1152,
                'meta': {'dpi': 72},
                'is_approved': True,
            },
            # Comic Panels
            {
                'key': 'comic_panel_landscape',
                'name': 'Comic Panel (Landscape)',
                'description': 'Wide comic panel',
                'use_case': FormatPreset.UseCase.COMIC_PANEL,
                'width': 1216,
                'height': 832,
                'meta': {'dpi': 72},
                'is_approved': True,
            },
            {
                'key': 'comic_panel_portrait',
                'name': 'Comic Panel (Portrait)',
                'description': 'Tall comic panel',
                'use_case': FormatPreset.UseCase.COMIC_PANEL,
                'width': 832,
                'height': 1216,
                'meta': {'dpi': 72},
                'is_approved': True,
            },
            {
                'key': 'comic_panel_square',
                'name': 'Comic Panel (Square)',
                'description': 'Square comic panel',
                'use_case': FormatPreset.UseCase.COMIC_PANEL,
                'width': 1024,
                'height': 1024,
                'meta': {'dpi': 72},
                'is_approved': True,
            },
            # Book Covers
            {
                'key': 'book_cover_6x9',
                'name': 'Book Cover (6x9)',
                'description': 'Standard paperback cover',
                'use_case': FormatPreset.UseCase.BOOK_COVER,
                'width': 1024,
                'height': 1536,
                'meta': {'dpi': 300, 'bleed': True},
                'is_approved': True,
            },
            # Audiobook
            {
                'key': 'audiobook_cover_3000',
                'name': 'Audiobook Cover (3000x3000)',
                'description': 'Audible/Spotify audiobook cover',
                'use_case': FormatPreset.UseCase.AUDIOBOOK,
                'width': 1024,
                'height': 1024,
                'meta': {'dpi': 72, 'upscale_to': 3000, 'format': 'jpg'},
                'is_approved': True,
            },
            # Print
            {
                'key': 'print_a4_portrait',
                'name': 'Print A4 Portrait',
                'description': 'A4 format for print',
                'use_case': FormatPreset.UseCase.PRINT,
                'width': 1024,
                'height': 1448,
                'meta': {'dpi': 300, 'upscale_factor': 3},
                'is_approved': True,
            },
        ]
        
        created = 0
        updated = 0
        
        for data in presets:
            key = data.pop('key')
            obj, was_created = FormatPreset.objects.update_or_create(
                key=key,
                defaults=data
            ) if force else (FormatPreset.objects.get_or_create(key=key, defaults=data))
            
            if was_created:
                created += 1
            elif force:
                updated += 1
        
        self.stdout.write(f'  FormatPresets: {created} created, {updated} updated')

    def seed_quality_presets(self, force: bool):
        """Seed quality presets."""
        
        presets = [
            {
                'key': 'draft',
                'name': 'Draft',
                'description': 'Quick preview quality',
                'settings': {
                    'steps': 20,
                    'upscale': False,
                },
                'estimated_time_seconds': 3,
                'estimated_cost': 0,
                'is_approved': True,
            },
            {
                'key': 'standard',
                'name': 'Standard',
                'description': 'Good quality for most uses',
                'settings': {
                    'steps': 30,
                    'upscale': False,
                },
                'estimated_time_seconds': 5,
                'estimated_cost': 0,
                'is_approved': True,
            },
            {
                'key': 'high',
                'name': 'High Quality',
                'description': 'High quality with refinement',
                'settings': {
                    'steps': 40,
                    'upscale': False,
                    'use_refiner': True,
                },
                'estimated_time_seconds': 10,
                'estimated_cost': 0,
                'is_approved': True,
            },
            {
                'key': 'final',
                'name': 'Final (Print Ready)',
                'description': 'Maximum quality with upscaling',
                'settings': {
                    'steps': 40,
                    'upscale': True,
                    'upscale_factor': 2,
                    'use_refiner': True,
                },
                'estimated_time_seconds': 20,
                'estimated_cost': 0,
                'is_approved': True,
            },
        ]
        
        created = 0
        updated = 0
        
        for data in presets:
            key = data.pop('key')
            obj, was_created = QualityPreset.objects.update_or_create(
                key=key,
                defaults=data
            ) if force else (QualityPreset.objects.get_or_create(key=key, defaults=data))
            
            if was_created:
                created += 1
            elif force:
                updated += 1
        
        self.stdout.write(f'  QualityPresets: {created} created, {updated} updated')

    def seed_voice_presets(self, force: bool):
        """Seed voice presets for TTS."""
        
        presets = [
            {
                'key': 'male_deep_de_v1',
                'name': 'Male Deep (German)',
                'description': 'Deep male voice for narration',
                'engine': VoicePreset.Engine.XTTS,
                'voice_id': 'male_deep_01',
                'language': VoicePreset.Language.DE,
                'gender': VoicePreset.Gender.MALE,
                'defaults': {
                    'speed': 1.0,
                    'pitch': -1,
                },
                'is_approved': True,
            },
            {
                'key': 'female_warm_de_v1',
                'name': 'Female Warm (German)',
                'description': 'Warm female voice for narration',
                'engine': VoicePreset.Engine.XTTS,
                'voice_id': 'female_warm_01',
                'language': VoicePreset.Language.DE,
                'gender': VoicePreset.Gender.FEMALE,
                'defaults': {
                    'speed': 1.0,
                    'pitch': 0,
                },
                'is_approved': True,
            },
            {
                'key': 'male_narrator_en_v1',
                'name': 'Male Narrator (English)',
                'description': 'Professional male narrator voice',
                'engine': VoicePreset.Engine.XTTS,
                'voice_id': 'male_narrator_01',
                'language': VoicePreset.Language.EN,
                'gender': VoicePreset.Gender.MALE,
                'defaults': {
                    'speed': 0.95,
                    'pitch': 0,
                },
                'is_approved': True,
            },
        ]
        
        created = 0
        updated = 0
        
        for data in presets:
            key = data.pop('key')
            obj, was_created = VoicePreset.objects.update_or_create(
                key=key,
                defaults=data
            ) if force else (VoicePreset.objects.get_or_create(key=key, defaults=data))
            
            if was_created:
                created += 1
            elif force:
                updated += 1
        
        self.stdout.write(f'  VoicePresets: {created} created, {updated} updated')

    def seed_parameter_mappings(self, force: bool):
        """Seed parameter mappings for different job types."""
        
        from apps.core.models.media_base import AbstractRenderJob
        
        mappings = [
            # ILLUSTRATION mappings
            {
                'job_type': AbstractRenderJob.JobType.ILLUSTRATION,
                'source_field': 'scene.location',
                'target_field': 'prompt.scene_location',
                'transform': ParameterMapping.Transform.TEMPLATE,
                'template': '{{ value }}, detailed environment',
                'order': 1,
            },
            {
                'job_type': AbstractRenderJob.JobType.ILLUSTRATION,
                'source_field': 'scene.mood',
                'target_field': 'prompt.scene_mood',
                'transform': ParameterMapping.Transform.PASSTHROUGH,
                'order': 2,
            },
            {
                'job_type': AbstractRenderJob.JobType.ILLUSTRATION,
                'source_field': 'scene.description',
                'target_field': 'prompt.positive',
                'transform': ParameterMapping.Transform.PASSTHROUGH,
                'is_required': True,
                'order': 0,
            },
            # COMIC_PANEL mappings
            {
                'job_type': AbstractRenderJob.JobType.COMIC_PANEL,
                'source_field': 'panel.description',
                'target_field': 'prompt.panel_description',
                'transform': ParameterMapping.Transform.PASSTHROUGH,
                'is_required': True,
                'order': 0,
            },
            {
                'job_type': AbstractRenderJob.JobType.COMIC_PANEL,
                'source_field': 'panel.dialogue',
                'target_field': 'prompt.dialogue',
                'transform': ParameterMapping.Transform.PASSTHROUGH,
                'order': 1,
            },
            {
                'job_type': AbstractRenderJob.JobType.COMIC_PANEL,
                'source_field': 'panel.camera',
                'target_field': 'prompt.camera',
                'transform': ParameterMapping.Transform.TEMPLATE,
                'template': '{{ value }} camera angle',
                'default_value': 'medium shot',
                'order': 2,
            },
            # AUDIO_CHAPTER mappings
            {
                'job_type': AbstractRenderJob.JobType.AUDIO_CHAPTER,
                'source_field': 'chapter.narration',
                'target_field': 'tts.narration',
                'transform': ParameterMapping.Transform.PASSTHROUGH,
                'is_required': True,
                'order': 0,
            },
            {
                'job_type': AbstractRenderJob.JobType.AUDIO_CHAPTER,
                'source_field': 'chapter.dialogues',
                'target_field': 'tts.dialogues',
                'transform': ParameterMapping.Transform.JSON,
                'order': 1,
            },
        ]
        
        created = 0
        updated = 0
        
        for data in mappings:
            job_type = data['job_type']
            source = data['source_field']
            target = data['target_field']
            
            if force:
                obj, was_created = ParameterMapping.objects.update_or_create(
                    job_type=job_type,
                    source_field=source,
                    target_field=target,
                    defaults={k: v for k, v in data.items() if k not in ['job_type', 'source_field', 'target_field']}
                )
            else:
                obj, was_created = ParameterMapping.objects.get_or_create(
                    job_type=job_type,
                    source_field=source,
                    target_field=target,
                    defaults={k: v for k, v in data.items() if k not in ['job_type', 'source_field', 'target_field']}
                )
            
            if was_created:
                created += 1
            elif force:
                updated += 1
        
        self.stdout.write(f'  ParameterMappings: {created} created, {updated} updated')
