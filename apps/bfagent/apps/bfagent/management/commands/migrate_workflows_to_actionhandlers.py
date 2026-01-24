"""
Management command to migrate Workflow V2 Templates to ActionHandler system
Converts EnhancedWorkflowTemplate → AgentAction → ActionHandler
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.bfagent.models import AgentAction, Agents
from apps.bfagent.models_handlers import Handler, ActionHandler
from apps.bfagent.services.workflow_templates_v2 import EnhancedWorkflowRegistry


class Command(BaseCommand):
    help = 'Migrate Workflow V2 Templates to ActionHandler System'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually doing it',
        )
        parser.add_argument(
            '--template',
            type=str,
            help='Migrate specific template only',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        template_filter = options.get('template')

        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS('MIGRATING WORKFLOW V2 TO ACTIONHANDLER SYSTEM'))
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write()

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
            self.stdout.write()

        # Get all templates
        templates = EnhancedWorkflowRegistry.get_all()
        
        if template_filter:
            templates = [t for t in templates if t.template_id == template_filter]
            if not templates:
                self.stdout.write(self.style.ERROR(
                    f'❌ Template "{template_filter}" not found'
                ))
                return

        if not templates:
            self.stdout.write(self.style.WARNING('⚠️  No templates found'))
            return

        migrated = 0
        skipped = 0
        errors = 0

        for template in templates:
            try:
                self.migrate_template(template, dry_run)
                migrated += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'❌ {template.template_id}: ERROR - {str(e)}'
                ))
                errors += 1

        # Summary
        self.stdout.write()
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS('✅ MIGRATION COMPLETE!'))
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write()
        self.stdout.write(f'✅ Migrated: {migrated}')
        if skipped > 0:
            self.stdout.write(f'⏭️  Skipped: {skipped}')
        if errors > 0:
            self.stdout.write(self.style.ERROR(f'❌ Errors: {errors}'))

    def migrate_template(self, template, dry_run: bool = False):
        """Migrate a single template to ActionHandler system"""
        
        self.stdout.write(self.style.HTTP_INFO(
            f'\n📦 Migrating Template: {template.name} ({template.template_id})'
        ))
        self.stdout.write('-'*70)

        # Get or create agent (use a generic workflow agent for now)
        agent, _ = Agents.objects.get_or_create(
            name='Workflow V2 Agent',
            defaults={
                'description': 'Auto-generated agent for Workflow V2 templates',
                'status': 'active'
            }
        )

        # Create AgentAction for this template
        action_name = template.template_id
        action_display_name = template.name

        if dry_run:
            self.stdout.write(f'  📝 Would create Action: {action_name}')
        else:
            action, action_created = AgentAction.objects.get_or_create(
                agent=agent,
                name=action_name,
                defaults={
                    'display_name': action_display_name,
                    'description': template.description,
                    'is_active': True
                }
            )
            
            if action_created:
                self.stdout.write(self.style.SUCCESS(
                    f'  ✅ Created Action: {action_name}'
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f'  🔄 Action exists: {action_name}'
                ))
                # Clear existing action handlers
                ActionHandler.objects.filter(action=action).delete()
                self.stdout.write('     Cleared existing ActionHandlers')

        # Migrate handlers
        order = 0

        # Input handlers
        for handler_config in template.input_handlers:
            order = self.migrate_handler(
                template, handler_config, 'input', order, action if not dry_run else None, dry_run
            )

        # Processing handlers
        for handler_config in template.processing_handlers:
            order = self.migrate_handler(
                template, handler_config, 'processing', order, action if not dry_run else None, dry_run
            )

        # Output handlers
        for handler_config in template.output_handlers:
            order = self.migrate_handler(
                template, handler_config, 'output', order, action if not dry_run else None, dry_run
            )

        self.stdout.write(self.style.SUCCESS(
            f'  ✅ Migrated {order} handlers'
        ))

    def migrate_handler(self, template, handler_config, phase, order, action, dry_run):
        """Migrate a single handler configuration"""
        
        handler_id = handler_config.get('handler')
        config = handler_config.get('config', {})

        # Find Handler in DB
        try:
            if not dry_run:
                handler = Handler.objects.get(handler_id=handler_id)
            
            if dry_run:
                self.stdout.write(
                    f'     📝 Would create ActionHandler: {handler_id} (phase: {phase}, order: {order})'
                )
            else:
                # Create ActionHandler
                ActionHandler.objects.create(
                    action=action,
                    handler=handler,
                    phase=phase,
                    order=order,
                    config=config,
                    is_active=True
                )
                self.stdout.write(
                    f'     ✅ Created ActionHandler: {handler_id} (phase: {phase}, order: {order})'
                )

            return order + 10  # Increment by 10 for easy insertion

        except Handler.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                f'     ❌ Handler not found in DB: {handler_id}'
            ))
            return order + 10
