"""
Register Test Generation Handler in Handler Registry
"""

from django.core.management.base import BaseCommand
from apps.bfagent.models import Handler


class Command(BaseCommand):
    help = 'Register Test Generation Handler in Handler Registry'

    def handle(self, *args, **options):
        handler, created = Handler.objects.update_or_create(
            handler_id='testing.test.generate',
            defaults={
                'name': 'Test Generation Handler',
                'description': 'Generates executable test code from acceptance criteria. Supports Robot Framework, pytest, and Playwright.',
                'version': '1.0.0',
                'module_path': 'apps.bfagent.handlers.test_generation_handler',
                'class_name': 'TestGenerationHandler',
                'handler_type': 'processing',
                'domain': 'testing',
                'category': 'test_automation',
                'is_active': True,
                'is_system_handler': False,
                'config_schema': {
                    'type': 'object',
                    'properties': {
                        'requirement': {
                            'type': 'object',
                            'description': 'TestRequirement instance'
                        },
                        'criterion': {
                            'type': 'object',
                            'required': ['scenario', 'given', 'when', 'then'],
                            'properties': {
                                'scenario': {'type': 'string'},
                                'given': {'type': 'string'},
                                'when': {'type': 'string'},
                                'then': {'type': 'string'},
                                'test_type': {'type': 'string', 'enum': ['ui', 'api', 'integration']},
                                'priority': {'type': 'string', 'enum': ['critical', 'high', 'medium', 'low']}
                            }
                        },
                        'framework': {
                            'type': 'string',
                            'enum': ['robot', 'pytest', 'playwright'],
                            'default': 'robot'
                        }
                    },
                    'required': ['requirement', 'criterion']
                },
                'output_schema': {
                    'type': 'object',
                    'properties': {
                        'success': {'type': 'boolean'},
                        'test_code': {'type': 'string'},
                        'file_path': {'type': 'string'},
                        'dependencies': {'type': 'array', 'items': {'type': 'string'}},
                        'estimated_duration': {'type': 'integer'}
                    }
                },
                'tags': ['testing', 'test-generation', 'robot-framework', 'automation'],
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Registered handler: {handler.handler_id}'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  Updated existing handler: {handler.handler_id}'
                )
            )
        
        self.stdout.write('\n📋 Handler Details:')
        self.stdout.write(f'  Name: {handler.name}')
        self.stdout.write(f'  Version: {handler.version}')
        self.stdout.write(f'  Domain: {handler.domain}')
        self.stdout.write(f'  Type: {handler.handler_type}')
        self.stdout.write(f'  Active: {handler.is_active}')
