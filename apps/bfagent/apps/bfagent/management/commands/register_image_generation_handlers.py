"""
Register Image Generation Handlers in Database

Usage:
    python manage.py register_image_generation_handlers
"""

from django.core.management.base import BaseCommand
from apps.bfagent.models_handlers import Handler


class Command(BaseCommand):
    help = 'Register Image Generation handlers in database'

    def handle(self, *args, **options):
        self.stdout.write("Registering Image Generation Handlers...")
        
        handlers = [
            {
                'handler_id': 'image_generation.single',
                'display_name': 'Single Image Generator',
                'description': 'Generate a single image from text prompt using OpenAI or Stability AI',
                'category': 'processing',
                'module_path': 'apps.image_generation.handlers.generic_image_handler',
                'class_name': 'SingleImageHandler',
                'version': '1.0.0',
                'is_experimental': False,
                'requires_llm': False,
                'config_schema': {
                    'type': 'object',
                    'properties': {
                        'provider': {'type': 'string', 'enum': ['openai', 'stability', 'auto']},
                        'size': {'type': 'string'},
                        'quality': {'type': 'string', 'enum': ['standard', 'hd']},
                        'save_to_path': {'type': 'string'},
                    }
                },
                'input_schema': {
                    'type': 'object',
                    'required': ['prompt'],
                    'properties': {
                        'prompt': {'type': 'string', 'minLength': 1},
                        'provider': {'type': 'string'},
                        'size': {'type': 'string'},
                        'quality': {'type': 'string'},
                        'save_to_path': {'type': 'string'},
                    }
                },
                'output_schema': {
                    'type': 'object',
                    'properties': {
                        'status': {'type': 'string'},
                        'image': {'type': 'object'},
                        'total_cost_cents': {'type': 'number'},
                        'total_time_seconds': {'type': 'number'},
                    }
                },
            },
            {
                'handler_id': 'image_generation.batch',
                'display_name': 'Batch Image Generator',
                'description': 'Generate multiple images in parallel with load distribution',
                'category': 'processing',
                'module_path': 'apps.image_generation.handlers.generic_image_handler',
                'class_name': 'BatchImageHandler',
                'version': '1.0.0',
                'is_experimental': False,
                'requires_llm': False,
                'config_schema': {
                    'type': 'object',
                    'properties': {
                        'distribute_load': {'type': 'boolean'},
                        'save_to_directory': {'type': 'string'},
                        'naming_pattern': {'type': 'string'},
                    }
                },
                'input_schema': {
                    'type': 'object',
                    'required': ['prompts'],
                    'properties': {
                        'prompts': {'type': 'array', 'items': {'type': 'string'}},
                        'provider': {'type': 'string'},
                        'distribute_load': {'type': 'boolean'},
                        'save_to_directory': {'type': 'string'},
                    }
                },
                'output_schema': {
                    'type': 'object',
                    'properties': {
                        'status': {'type': 'string'},
                        'images': {'type': 'array'},
                        'success_rate': {'type': 'number'},
                        'total_cost_cents': {'type': 'number'},
                        'total_time_seconds': {'type': 'number'},
                    }
                },
            },
            {
                'handler_id': 'image_generation.illustration',
                'display_name': 'Book Illustration Generator',
                'description': 'Generate consistent illustrations for educational books with character preservation',
                'category': 'processing',
                'module_path': 'apps.image_generation.handlers.illustration_handler',
                'class_name': 'IllustrationGenerationHandler',
                'version': '1.0.0',
                'is_experimental': False,
                'requires_llm': False,
                'config_schema': {
                    'type': 'object',
                    'properties': {
                        'save_images': {'type': 'boolean'},
                        'max_parallel': {'type': 'integer'},
                        'default_provider': {'type': 'string'},
                    }
                },
                'input_schema': {
                    'type': 'object',
                    'required': ['scene_descriptions', 'illustration_style', 'save_to_directory'],
                    'properties': {
                        'book_id': {'type': 'integer'},
                        'chapter_id': {'type': 'integer'},
                        'scene_descriptions': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'minItems': 1
                        },
                        'illustration_style': {'type': 'string'},
                        'character_descriptions': {'type': 'object'},
                        'aspect_ratio': {'type': 'string'},
                        'save_to_directory': {'type': 'string'},
                        'provider': {'type': 'string'},
                        'ensure_consistency': {'type': 'boolean'},
                    }
                },
                'output_schema': {
                    'type': 'object',
                    'properties': {
                        'status': {'type': 'string'},
                        'book_id': {'type': 'integer'},
                        'chapter_id': {'type': 'integer'},
                        'illustrations': {'type': 'array'},
                        'successful_illustrations': {'type': 'integer'},
                        'failed_illustrations': {'type': 'integer'},
                        'illustration_directory': {'type': 'string'},
                        'total_cost_cents': {'type': 'number'},
                        'total_time_seconds': {'type': 'number'},
                    }
                },
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for handler_data in handlers:
            handler, created = Handler.objects.update_or_create(
                handler_id=handler_data['handler_id'],
                defaults=handler_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Created: {handler.display_name}")
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f"⚠️  Updated: {handler.display_name}")
                )
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(
            f"✅ Registered {created_count + updated_count} Image Generation handlers"
        ))
        self.stdout.write(f"   Created: {created_count}")
        self.stdout.write(f"   Updated: {updated_count}")
        self.stdout.write("="*60 + "\n")