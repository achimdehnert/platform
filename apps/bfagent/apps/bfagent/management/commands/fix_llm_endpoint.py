"""
Management command to fix LLM API endpoint
"""
from django.core.management.base import BaseCommand
from apps.bfagent.models import Llms


class Command(BaseCommand):
    help = 'Fix LLM API endpoint'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, required=True, help='LLM ID')
        parser.add_argument('--endpoint', type=str, required=True, help='New API endpoint')

    def handle(self, *args, **options):
        llm_id = options['id']
        new_endpoint = options['endpoint']
        
        try:
            llm = Llms.objects.get(id=llm_id)
            old_endpoint = llm.api_endpoint
            llm.api_endpoint = new_endpoint
            llm.save()
            
            self.stdout.write(self.style.SUCCESS(
                f'Updated LLM "{llm.name}" (ID: {llm_id})\n'
                f'  Old endpoint: {old_endpoint}\n'
                f'  New endpoint: {new_endpoint}'
            ))
        except Llms.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'LLM with ID {llm_id} not found'))
