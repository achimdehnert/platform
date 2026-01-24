"""Create a test project for image generation testing"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.bfagent.models import BookProjects
from apps.bfagent.models_generated import BookType

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a test project for illustration system testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            default='achim',
            help='Username to create project for'
        )

    def handle(self, *args, **options):
        username = options['user']

        # Get user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User "{username}" not found!'))
            return

        # Check if user already has projects
        existing = BookProjects.objects.filter(user=user).count()
        self.stdout.write(f'User "{username}" has {existing} existing projects')

        # Get a BookType (use first available or Novel)
        book_type = BookType.objects.filter(name='Novel').first()
        if not book_type:
            book_type = BookType.objects.first()
        
        if not book_type:
            self.stdout.write(self.style.ERROR('No BookType found! Please create one first.'))
            return

        # Create test project
        project = BookProjects.objects.create(
            user=user,
            book_type=book_type,
            title="Illustration System Test Project",
            genre="Fantasy",
            description="Test project for AI-powered illustration system",
            status="in_progress",
            target_word_count=50000
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Created test project!'
            )
        )
        self.stdout.write(f'   ID: {project.id}')
        self.stdout.write(f'   Title: {project.title}')
        self.stdout.write(f'   User: {project.user.username}')
        self.stdout.write(
            f'\n💡 Now you can generate images at:'
        )
        self.stdout.write('   http://localhost:8000/bookwriting/illustrations/generate/')
