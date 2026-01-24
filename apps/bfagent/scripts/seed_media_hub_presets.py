#!/usr/bin/env python
"""
Seed Media Hub with initial presets.
Run: python scripts/seed_media_hub_presets.py
"""
import os
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()

from django.db import connection
from django.utils.text import slugify


def seed_style_presets():
    """Seed style presets for image generation."""
    presets = [
        {
            'name': 'Cinematic',
            'slug': 'cinematic',
            'description': 'Film-like, dramatic lighting and composition',
            'prompt_style': 'cinematic lighting, dramatic composition, film grain, professional photography',
            'prompt_negative': 'cartoon, anime, drawing, sketch, low quality',
            'defaults': {'cfg_scale': 7.5, 'steps': 30},
            'category': 'illustration',
            'color_palette': ['#1a1a2e', '#16213e', '#0f3460', '#e94560'],
        },
        {
            'name': 'Watercolor',
            'slug': 'watercolor',
            'description': 'Soft watercolor painting style',
            'prompt_style': 'watercolor painting, soft edges, flowing colors, artistic, traditional media',
            'prompt_negative': 'photorealistic, sharp edges, digital art',
            'defaults': {'cfg_scale': 7.0, 'steps': 25},
            'category': 'illustration',
            'color_palette': ['#f6d365', '#fda085', '#a8edea', '#fed6e3'],
        },
        {
            'name': 'Comic Book',
            'slug': 'comic-book',
            'description': 'Bold lines, flat colors, comic style',
            'prompt_style': 'comic book style, bold outlines, cel shading, vibrant colors, dynamic poses',
            'prompt_negative': 'photorealistic, soft shading, blurry',
            'defaults': {'cfg_scale': 8.0, 'steps': 28},
            'category': 'comic',
            'color_palette': ['#ff6b6b', '#4ecdc4', '#ffe66d', '#2c3e50'],
        },
        {
            'name': 'Manga',
            'slug': 'manga',
            'description': 'Japanese manga illustration style',
            'prompt_style': 'manga style, anime, Japanese illustration, clean lines, expressive',
            'prompt_negative': 'western comic, realistic, 3d render',
            'defaults': {'cfg_scale': 7.5, 'steps': 25},
            'category': 'comic',
            'color_palette': ['#ffeaa7', '#dfe6e9', '#74b9ff', '#fd79a8'],
        },
        {
            'name': 'Fantasy Art',
            'slug': 'fantasy-art',
            'description': 'Epic fantasy illustration style',
            'prompt_style': 'fantasy art, epic, magical, detailed, dramatic lighting, oil painting style',
            'prompt_negative': 'modern, urban, mundane, low quality',
            'defaults': {'cfg_scale': 8.0, 'steps': 35},
            'category': 'illustration',
            'color_palette': ['#6c5ce7', '#a29bfe', '#fd79a8', '#00b894'],
        },
        {
            'name': 'Children Book',
            'slug': 'children-book',
            'description': 'Warm, friendly illustration for children',
            'prompt_style': 'children book illustration, warm colors, friendly, whimsical, soft shading',
            'prompt_negative': 'scary, dark, violent, realistic',
            'defaults': {'cfg_scale': 6.5, 'steps': 25},
            'category': 'illustration',
            'color_palette': ['#ff9ff3', '#feca57', '#5f27cd', '#54a0ff'],
        },
    ]
    
    with connection.cursor() as cursor:
        for p in presets:
            cursor.execute("""
                INSERT INTO media_hub_style_preset 
                (name, slug, description, prompt_style, prompt_negative, defaults, category, color_palette, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true, NOW(), NOW())
                ON CONFLICT (slug) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    prompt_style = EXCLUDED.prompt_style,
                    prompt_negative = EXCLUDED.prompt_negative,
                    defaults = EXCLUDED.defaults,
                    category = EXCLUDED.category,
                    color_palette = EXCLUDED.color_palette,
                    updated_at = NOW()
            """, [
                p['name'], p['slug'], p['description'], p['prompt_style'],
                p['prompt_negative'], 
                str(p['defaults']).replace("'", '"'),  # JSON format
                p['category'],
                str(p['color_palette']).replace("'", '"'),
            ])
            print(f"  ✓ Style: {p['name']}")
    
    return len(presets)


def seed_format_presets():
    """Seed format presets for output dimensions."""
    presets = [
        {'name': 'Square 1:1', 'slug': 'square-1-1', 'width': 1024, 'height': 1024, 'aspect_ratio': '1:1', 'use_case': 'general'},
        {'name': 'Portrait 3:4', 'slug': 'portrait-3-4', 'width': 768, 'height': 1024, 'aspect_ratio': '3:4', 'use_case': 'book_cover'},
        {'name': 'Landscape 16:9', 'slug': 'landscape-16-9', 'width': 1024, 'height': 576, 'aspect_ratio': '16:9', 'use_case': 'general'},
        {'name': 'Comic Panel Wide', 'slug': 'comic-panel-wide', 'width': 1024, 'height': 512, 'aspect_ratio': '2:1', 'use_case': 'comic_panel'},
        {'name': 'Comic Panel Tall', 'slug': 'comic-panel-tall', 'width': 512, 'height': 1024, 'aspect_ratio': '1:2', 'use_case': 'comic_panel'},
        {'name': 'Book Cover Standard', 'slug': 'book-cover-standard', 'width': 1600, 'height': 2560, 'aspect_ratio': '5:8', 'use_case': 'book_cover'},
        {'name': 'Audiobook Cover', 'slug': 'audiobook-cover', 'width': 3000, 'height': 3000, 'aspect_ratio': '1:1', 'use_case': 'audiobook'},
        {'name': 'Social Media Square', 'slug': 'social-square', 'width': 1080, 'height': 1080, 'aspect_ratio': '1:1', 'use_case': 'social'},
    ]
    
    with connection.cursor() as cursor:
        for p in presets:
            cursor.execute("""
                INSERT INTO media_hub_format_preset 
                (name, slug, description, width, height, aspect_ratio, meta, use_case, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, '{}', %s, true, NOW(), NOW())
                ON CONFLICT (slug) DO UPDATE SET
                    name = EXCLUDED.name,
                    width = EXCLUDED.width,
                    height = EXCLUDED.height,
                    aspect_ratio = EXCLUDED.aspect_ratio,
                    use_case = EXCLUDED.use_case,
                    updated_at = NOW()
            """, [p['name'], p['slug'], f"{p['width']}x{p['height']}", p['width'], p['height'], p['aspect_ratio'], p['use_case']])
            print(f"  ✓ Format: {p['name']}")
    
    return len(presets)


def seed_quality_presets():
    """Seed quality presets."""
    presets = [
        {'name': 'Draft', 'slug': 'draft', 'level': 'draft', 'settings': {'steps': 15, 'cfg_scale': 6.0}},
        {'name': 'Standard', 'slug': 'standard', 'level': 'standard', 'settings': {'steps': 25, 'cfg_scale': 7.0}},
        {'name': 'High Quality', 'slug': 'high', 'level': 'high', 'settings': {'steps': 35, 'cfg_scale': 7.5}},
        {'name': 'Final Production', 'slug': 'final', 'level': 'final', 'settings': {'steps': 50, 'cfg_scale': 8.0, 'upscale': 'true'}},
    ]
    
    with connection.cursor() as cursor:
        for p in presets:
            cursor.execute("""
                INSERT INTO media_hub_quality_preset 
                (name, slug, description, level, settings, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, true, NOW(), NOW())
                ON CONFLICT (slug) DO UPDATE SET
                    name = EXCLUDED.name,
                    level = EXCLUDED.level,
                    settings = EXCLUDED.settings,
                    updated_at = NOW()
            """, [p['name'], p['slug'], f"{p['level'].title()} quality preset", p['level'], 
                  str(p['settings']).replace("'", '"')])
            print(f"  ✓ Quality: {p['name']}")
    
    return len(presets)


def seed_voice_presets():
    """Seed voice presets for TTS."""
    presets = [
        {'name': 'German Male (Standard)', 'slug': 'de-male-standard', 'engine': 'xtts', 'voice_id': 'de_male_01', 'language': 'de', 'gender': 'male'},
        {'name': 'German Female (Standard)', 'slug': 'de-female-standard', 'engine': 'xtts', 'voice_id': 'de_female_01', 'language': 'de', 'gender': 'female'},
        {'name': 'English Male (Narrator)', 'slug': 'en-male-narrator', 'engine': 'xtts', 'voice_id': 'en_male_01', 'language': 'en', 'gender': 'male'},
        {'name': 'English Female (Narrator)', 'slug': 'en-female-narrator', 'engine': 'xtts', 'voice_id': 'en_female_01', 'language': 'en', 'gender': 'female'},
    ]
    
    with connection.cursor() as cursor:
        for p in presets:
            cursor.execute("""
                INSERT INTO media_hub_voice_preset 
                (name, slug, description, engine, voice_id, defaults, language, gender, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, '{}', %s, %s, true, NOW(), NOW())
                ON CONFLICT (slug) DO UPDATE SET
                    name = EXCLUDED.name,
                    engine = EXCLUDED.engine,
                    voice_id = EXCLUDED.voice_id,
                    language = EXCLUDED.language,
                    gender = EXCLUDED.gender,
                    updated_at = NOW()
            """, [p['name'], p['slug'], f"{p['language'].upper()} {p['gender']} voice", 
                  p['engine'], p['voice_id'], p['language'], p['gender']])
            print(f"  ✓ Voice: {p['name']}")
    
    return len(presets)


def seed_parameter_mappings():
    """Seed parameter mappings for dynamic prompt generation."""
    mappings = [
        # Illustration mappings
        {'job_type': 'illustration', 'source': 'scene.description', 'target': 'prompt.positive', 'transform': 'template', 
         'template': '{{ scene.description }}, {{ style.prompt_style }}'},
        {'job_type': 'illustration', 'source': 'scene.location', 'target': 'prompt.environment', 'transform': 'passthrough'},
        {'job_type': 'illustration', 'source': 'scene.mood', 'target': 'prompt.atmosphere', 'transform': 'passthrough'},
        
        # Comic panel mappings
        {'job_type': 'comic_panel', 'source': 'panel.description', 'target': 'prompt.positive', 'transform': 'template',
         'template': '{{ panel.description }}, comic panel, {{ style.prompt_style }}'},
        {'job_type': 'comic_panel', 'source': 'panel.characters', 'target': 'prompt.characters', 'transform': 'passthrough'},
        
        # Book cover mappings
        {'job_type': 'book_cover', 'source': 'book.title', 'target': 'prompt.title', 'transform': 'passthrough'},
        {'job_type': 'book_cover', 'source': 'book.genre', 'target': 'prompt.genre', 'transform': 'passthrough'},
    ]
    
    with connection.cursor() as cursor:
        for i, m in enumerate(mappings):
            cursor.execute("""
                INSERT INTO media_hub_parameter_mapping 
                (job_type, source_field, target_field, transform, template, default_value, is_required, "order")
                VALUES (%s, %s, %s, %s, %s, '', false, %s)
                ON CONFLICT (job_type, source_field, target_field) DO UPDATE SET
                    transform = EXCLUDED.transform,
                    template = EXCLUDED.template,
                    "order" = EXCLUDED."order"
            """, [m['job_type'], m['source'], m['target'], m['transform'], 
                  m.get('template', ''), i])
            print(f"  ✓ Mapping: {m['source']} → {m['target']}")
    
    return len(mappings)


def main():
    print("\n🎨 Seeding Media Hub Presets...\n")
    
    print("Style Presets:")
    styles = seed_style_presets()
    
    print("\nFormat Presets:")
    formats = seed_format_presets()
    
    print("\nQuality Presets:")
    quality = seed_quality_presets()
    
    print("\nVoice Presets:")
    voices = seed_voice_presets()
    
    print("\nParameter Mappings:")
    mappings = seed_parameter_mappings()
    
    print(f"\n✅ Seeding complete!")
    print(f"   - {styles} style presets")
    print(f"   - {formats} format presets")
    print(f"   - {quality} quality presets")
    print(f"   - {voices} voice presets")
    print(f"   - {mappings} parameter mappings")


if __name__ == '__main__':
    main()
