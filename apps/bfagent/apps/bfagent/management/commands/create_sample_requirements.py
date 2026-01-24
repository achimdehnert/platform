"""Create 5 Sample Test Requirements for Book Domain"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.bfagent.models import TestRequirement

User = get_user_model()


class Command(BaseCommand):
    help = 'Create 5 sample test requirements'

    def handle(self, *args, **options):
        admin = User.objects.filter(is_superuser=True).first()
        
        # Requirement 1: Chapter Creation
        req1 = TestRequirement.objects.create(
            name='Chapter Creation Workflow',
            description='Users can create new chapters',
            category='feature',
            priority='critical',
            acceptance_criteria=[
                {
                    'id': 'ac_1',
                    'scenario': 'User creates new chapter',
                    'given': 'User is logged in and has book project',
                    'when': 'User fills chapter creation form and submits',
                    'then': 'Chapter is created and displayed',
                    'test_type': 'ui',
                    'priority': 'critical'
                },
                {
                    'id': 'ac_2',
                    'scenario': 'Chapter creation validates fields',
                    'given': 'User is on chapter creation page',
                    'when': 'User submits without title',
                    'then': 'Error message should appear',
                    'test_type': 'ui',
                    'priority': 'high'
                }
            ],
            tags=['chapter', 'creation'],
            created_by=admin,
            status='ready'
        )
        
        # Requirement 2: Chapter Feedback
        req2 = TestRequirement.objects.create(
            name='Chapter Feedback System',
            description='Users can add feedback to chapters',
            category='feature',
            priority='high',
            acceptance_criteria=[
                {
                    'id': 'ac_1',
                    'scenario': 'User adds comment',
                    'given': 'User views chapter detail page',
                    'when': 'User clicks add comment and enters text',
                    'then': 'Comment should be saved',
                    'test_type': 'ui',
                    'priority': 'high'
                },
                {
                    'id': 'ac_2',
                    'scenario': 'Regenerate with feedback',
                    'given': 'User has added feedback',
                    'when': 'User clicks regenerate button',
                    'then': 'Chapter regeneration triggered',
                    'test_type': 'integration',
                    'priority': 'high'
                }
            ],
            tags=['chapter', 'feedback'],
            created_by=admin,
            status='ready'
        )
        
        # Requirement 3: Book Management
        req3 = TestRequirement.objects.create(
            name='Book Project Management',
            description='Users can manage book projects',
            category='feature',
            priority='critical',
            acceptance_criteria=[
                {
                    'id': 'ac_1',
                    'scenario': 'Create book project',
                    'given': 'User is logged in',
                    'when': 'User creates new book',
                    'then': 'Book appears in list',
                    'test_type': 'ui',
                    'priority': 'critical'
                },
                {
                    'id': 'ac_2',
                    'scenario': 'View book details',
                    'given': 'User has book',
                    'when': 'User clicks on book',
                    'then': 'Book details displayed',
                    'test_type': 'ui',
                    'priority': 'high'
                }
            ],
            tags=['book', 'management'],
            created_by=admin,
            status='ready'
        )
        
        # Requirement 4: LLM Integration
        req4 = TestRequirement.objects.create(
            name='LLM Configuration',
            description='Users can configure LLM providers',
            category='feature',
            priority='high',
            acceptance_criteria=[
                {
                    'id': 'ac_1',
                    'scenario': 'Add LLM provider',
                    'given': 'User is on LLM list page',
                    'when': 'User adds new LLM configuration',
                    'then': 'LLM should be saved',
                    'test_type': 'ui',
                    'priority': 'high'
                },
                {
                    'id': 'ac_2',
                    'scenario': 'Test LLM connection',
                    'given': 'User has configured LLM',
                    'when': 'User clicks test button',
                    'then': 'Connection status displayed',
                    'test_type': 'integration',
                    'priority': 'medium'
                }
            ],
            tags=['llm', 'configuration'],
            created_by=admin,
            status='ready'
        )
        
        # Requirement 5: Character Management
        req5 = TestRequirement.objects.create(
            name='Character Management',
            description='Users can manage book characters',
            category='feature',
            priority='medium',
            acceptance_criteria=[
                {
                    'id': 'ac_1',
                    'scenario': 'Create character',
                    'given': 'User has book project',
                    'when': 'User creates new character',
                    'then': 'Character saved to book',
                    'test_type': 'ui',
                    'priority': 'medium'
                },
                {
                    'id': 'ac_2',
                    'scenario': 'Edit character',
                    'given': 'Character exists',
                    'when': 'User updates character details',
                    'then': 'Changes are saved',
                    'test_type': 'ui',
                    'priority': 'medium'
                }
            ],
            tags=['character', 'management'],
            created_by=admin,
            status='ready'
        )
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created 5 test requirements'))
        self.stdout.write(f'  1. {req1.name} ({req1.get_total_criteria()} criteria)')
        self.stdout.write(f'  2. {req2.name} ({req2.get_total_criteria()} criteria)')
        self.stdout.write(f'  3. {req3.name} ({req3.get_total_criteria()} criteria)')
        self.stdout.write(f'  4. {req4.name} ({req4.get_total_criteria()} criteria)')
        self.stdout.write(f'  5. {req5.name} ({req5.get_total_criteria()} criteria)')
