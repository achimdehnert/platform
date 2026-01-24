"""
Management command to seed illustration style templates
"""
from django.core.management.base import BaseCommand
from apps.writing_hub.models import IllustrationStyleTemplate, IllustrationStyle


class Command(BaseCommand):
    help = 'Creates default illustration style templates'

    def handle(self, *args, **options):
        templates = [
            {
                'name': 'Fantasy Aquarell',
                'description': 'Weicher, magischer Aquarell-Stil für Fantasy-Romane',
                'style_type': 'watercolor',
                'base_prompt': 'watercolor painting, fantasy illustration, soft edges, magical atmosphere, ethereal lighting, dreamy colors',
                'negative_prompt': 'photo, realistic, 3d render, blurry, low quality, harsh lines',
                'color_palette': ['#2E5A4C', '#8B4513', '#4A6FA5', '#D4A574'],
                'provider': 'dalle3',
                'quality': 'hd',
                'image_size': '1024x1024',
                'is_public': True,
            },
            {
                'name': 'Kinderbuch Digital',
                'description': 'Farbenfroher, freundlicher Stil für Kinderbücher',
                'style_type': 'digital_art',
                'base_prompt': 'digital illustration, children book style, colorful, friendly, warm lighting, cute characters, whimsical',
                'negative_prompt': 'scary, dark, realistic, violent, complex, detailed',
                'color_palette': ['#FF6B6B', '#4ECDC4', '#FFE66D', '#95E1D3'],
                'provider': 'dalle3',
                'quality': 'hd',
                'image_size': '1024x1024',
                'is_public': True,
            },
            {
                'name': 'Dark Fantasy',
                'description': 'Düsterer, atmosphärischer Stil für Dark Fantasy',
                'style_type': 'oil_painting',
                'base_prompt': 'oil painting, dark fantasy, dramatic lighting, moody atmosphere, rich shadows, gothic elements',
                'negative_prompt': 'bright, cheerful, colorful, cartoon, cute, simple',
                'color_palette': ['#1C1C1C', '#4A0000', '#2D2D2D', '#483D8B'],
                'provider': 'dalle3',
                'quality': 'hd',
                'image_size': '1024x1024',
                'is_public': True,
            },
            {
                'name': 'Sci-Fi Konzept',
                'description': 'Futuristischer Stil für Science Fiction',
                'style_type': 'digital_art',
                'base_prompt': 'concept art, science fiction, futuristic, sleek design, neon accents, high tech, cinematic lighting',
                'negative_prompt': 'medieval, fantasy, old, rustic, natural, organic',
                'color_palette': ['#00D4FF', '#1A1A2E', '#16213E', '#0F3460'],
                'provider': 'dalle3',
                'quality': 'hd',
                'image_size': '1792x1024',
                'is_public': True,
            },
            {
                'name': 'Romance Soft',
                'description': 'Romantischer, weicher Stil für Liebesromane',
                'style_type': 'watercolor',
                'base_prompt': 'soft illustration, romantic, pastel colors, gentle lighting, dreamy atmosphere, elegant',
                'negative_prompt': 'harsh, dark, violent, scary, cold, industrial',
                'color_palette': ['#FFB6C1', '#E6E6FA', '#F5DEB3', '#DDA0DD'],
                'provider': 'dalle3',
                'quality': 'hd',
                'image_size': '1024x1024',
                'is_public': True,
            },
            {
                'name': 'Thriller Noir',
                'description': 'Film Noir Stil für Thriller und Krimis',
                'style_type': 'sketch',
                'base_prompt': 'film noir style, high contrast, dramatic shadows, black and white with color accents, mystery atmosphere',
                'negative_prompt': 'colorful, bright, cheerful, cartoon, simple',
                'color_palette': ['#000000', '#FFFFFF', '#8B0000', '#2F4F4F'],
                'provider': 'dalle3',
                'quality': 'hd',
                'image_size': '1024x1024',
                'is_public': True,
            },
            {
                'name': 'Sachbuch Minimal',
                'description': 'Klarer, minimalistischer Stil für Sachbücher',
                'style_type': 'vector',
                'base_prompt': 'minimalist illustration, clean lines, simple shapes, professional, informative, vector style',
                'negative_prompt': 'complex, detailed, realistic, fantasy, cluttered',
                'color_palette': ['#2C3E50', '#3498DB', '#ECF0F1', '#E74C3C'],
                'provider': 'dalle3',
                'quality': 'standard',
                'image_size': '1024x1024',
                'is_public': True,
            },
        ]

        created_count = 0
        for template_data in templates:
            template, created = IllustrationStyleTemplate.objects.get_or_create(
                name=template_data['name'],
                defaults=template_data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Created: {template.name}'))
            else:
                self.stdout.write(f'  Exists: {template.name}')

        self.stdout.write(self.style.SUCCESS(f'\nDone! Created {created_count} new templates.'))
