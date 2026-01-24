"""
Register BookWriting Domain Handlers in Database

Usage:
    python manage.py register_bookwriting_handlers
"""

from django.core.management.base import BaseCommand
from apps.bfagent.models_handlers import Handler


class Command(BaseCommand):
    help = 'Register BookWriting domain handlers in database'

    def handle(self, *args, **options):
        self.stdout.write("Registering BookWriting Domain Handlers...")
        
        handlers = [
            {
                'handler_id': 'bookwriting.project.enrich',
                'display_name': 'Project Enrichment Handler',
                'description': 'Enriches book projects using AI agents. Supports actions like outline generation, premise development, themes, stakes, and character cast generation.',
                'category': 'processing',
                'module_path': 'apps.core.handlers.domains.bookwriting.enrichment',
                'class_name': 'ProjectEnrichmentHandler',
                'version': '1.0.0',
                'config_schema': {
                    'type': 'object',
                    'properties': {
                        'project': {'type': 'object', 'required': True},
                        'agent': {'type': 'object', 'required': True},
                        'action': {'type': 'string', 'required': True},
                        'chapter': {'type': 'object', 'required': False},
                    }
                },
                'input_schema': {
                    'type': 'object',
                    'required': ['project', 'agent', 'action'],
                },
                'output_schema': {
                    'type': 'object',
                    'properties': {
                        'success': {'type': 'boolean'},
                        'result': {'type': 'string'},
                        'action': {'type': 'string'},
                        'error': {'type': ['string', 'null']},
                        'metadata': {'type': 'object'},
                    }
                },
            },
            {
                'handler_id': 'bookwriting.chapter.enrich',
                'display_name': 'Chapter Enrichment Handler',
                'description': 'Enriches book chapters using AI agents. Supports writing drafts, summarization, and expansion.',
                'category': 'processing',
                'module_path': 'apps.core.handlers.domains.bookwriting.enrichment',
                'class_name': 'ChapterEnrichmentHandler',
                'version': '1.0.0',
                'config_schema': {
                    'type': 'object',
                    'properties': {
                        'chapter': {'type': 'object', 'required': True},
                        'agent': {'type': 'object', 'required': True},
                        'action': {'type': 'string', 'required': True},
                    }
                },
                'input_schema': {
                    'type': 'object',
                    'required': ['chapter', 'agent', 'action'],
                },
                'output_schema': {
                    'type': 'object',
                    'properties': {
                        'success': {'type': 'boolean'},
                        'result': {'type': 'string'},
                        'action': {'type': 'string'},
                        'error': {'type': ['string', 'null']},
                        'metadata': {'type': 'object'},
                    }
                },
            },
            {
                'handler_id': 'bookwriting.character.enrich',
                'display_name': 'Character Enrichment Handler',
                'description': 'Enriches characters using AI agents. Supports backstory generation, dialogue voice development, and character arc creation.',
                'category': 'processing',
                'module_path': 'apps.core.handlers.domains.bookwriting.enrichment',
                'class_name': 'CharacterEnrichmentHandler',
                'version': '1.0.0',
                'config_schema': {
                    'type': 'object',
                    'properties': {
                        'character': {'type': 'object', 'required': True},
                        'agent': {'type': 'object', 'required': True},
                        'action': {'type': 'string', 'required': True},
                    }
                },
                'input_schema': {
                    'type': 'object',
                    'required': ['character', 'agent', 'action'],
                },
                'output_schema': {
                    'type': 'object',
                    'properties': {
                        'success': {'type': 'boolean'},
                        'result': {'type': 'string'},
                        'action': {'type': 'string'},
                        'error': {'type': ['string', 'null']},
                        'metadata': {'type': 'object'},
                    }
                },
            },
            {
                'handler_id': 'bookwriting.chapter.generate',
                'display_name': 'Chapter Generation Handler',
                'description': 'Generates new chapters for book projects based on outline or AI suggestions.',
                'category': 'processing',
                'module_path': 'apps.core.handlers.domains.bookwriting.generation',
                'class_name': 'ChapterGenerateHandler',
                'version': '1.0.0',
                'config_schema': {
                    'type': 'object',
                    'properties': {
                        'project': {'type': 'object', 'required': True},
                        'agent': {'type': 'object', 'required': True},
                        'count': {'type': 'integer', 'default': 5},
                    }
                },
                'input_schema': {
                    'type': 'object',
                    'required': ['project', 'agent'],
                },
                'output_schema': {
                    'type': 'object',
                    'properties': {
                        'success': {'type': 'boolean'},
                        'chapters': {'type': 'array'},
                        'error': {'type': ['string', 'null']},
                        'metadata': {'type': 'object'},
                    }
                },
            },
            {
                'handler_id': 'bookwriting.character.cast',
                'display_name': 'Character Cast Handler',
                'description': 'Generates a complete character cast for book projects (6+ characters) based on story requirements.',
                'category': 'processing',
                'module_path': 'apps.core.handlers.domains.bookwriting.generation',
                'class_name': 'CharacterCastHandler',
                'version': '1.0.0',
                'config_schema': {
                    'type': 'object',
                    'properties': {
                        'project': {'type': 'object', 'required': True},
                        'agent': {'type': 'object', 'required': True},
                        'count': {'type': 'integer', 'default': 6},
                    }
                },
                'input_schema': {
                    'type': 'object',
                    'required': ['project', 'agent'],
                },
                'output_schema': {
                    'type': 'object',
                    'properties': {
                        'success': {'type': 'boolean'},
                        'characters': {'type': 'array'},
                        'error': {'type': ['string', 'null']},
                        'metadata': {'type': 'object'},
                    }
                },
            },
        ]
        
        created = 0
        updated = 0
        
        for handler_data in handlers:
            handler, was_created = Handler.objects.update_or_create(
                handler_id=handler_data['handler_id'],
                defaults=handler_data
            )
            
            if was_created:
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Created: {handler.handler_id}")
                )
            else:
                updated += 1
                self.stdout.write(
                    self.style.WARNING(f"  ↻ Updated: {handler.handler_id}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\nRegistration complete: {created} created, {updated} updated"
            )
        )
