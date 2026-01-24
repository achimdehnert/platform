"""
Management Command: Show migration status and health
"""
from django.core.management.base import BaseCommand
from apps.bfagent.models_registry import MigrationRegistry


class Command(BaseCommand):
    help = 'Show migration status and health'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--app',
            type=str,
            help='Show status for specific app'
        )
        parser.add_argument(
            '--risky',
            action='store_true',
            help='Show only risky migrations (complexity >= 51)'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n📊 Migration Status\n'))
        
        # Base query
        migrations = MigrationRegistry.objects.all()
        
        # Filter by app if specified
        if options['app']:
            migrations = migrations.filter(app_label=options['app'])
        
        # Filter risky if specified
        if options['risky']:
            migrations = migrations.filter(complexity_score__gte=51)
        
        # Group by app
        apps = migrations.values_list('app_label', flat=True).distinct()
        
        for app_label in sorted(apps):
            app_migrations = migrations.filter(app_label=app_label)
            
            total = app_migrations.count()
            applied = app_migrations.filter(is_applied=True).count()
            pending = total - applied
            
            self.stdout.write(f'\nApp: {app_label}')
            self.stdout.write(f'Total: {total} | Applied: {applied} | Pending: {pending}')
            self.stdout.write('')
            
            # Show migrations
            for mig in app_migrations.order_by('migration_number')[:20]:
                status = "✅" if mig.is_applied else "⏳"
                risk = self._get_risk_badge(mig.complexity_score)
                
                self.stdout.write(
                    f'  {status} {mig.migration_name:30} | {mig.migration_type:8} | '
                    f'Complexity: {mig.complexity_score:3} {risk}'
                )
        
        # Overall summary
        self.stdout.write('\n' + '='*70)
        total_count = migrations.count()
        applied_count = migrations.filter(is_applied=True).count()
        pending_count = total_count - applied_count
        
        self.stdout.write(f'TOTAL: {total_count} | Applied: {applied_count} | Pending: {pending_count}')
        
        # Risk summary
        if not options['risky']:
            risky_count = migrations.filter(complexity_score__gte=51).count()
            if risky_count > 0:
                self.stdout.write(
                    self.style.WARNING(f'\n⚠️  {risky_count} migrations with complexity >= 51')
                )
                self.stdout.write('Run with --risky to see them')
        
        self.stdout.write('')
    
    def _get_risk_badge(self, score):
        """Get risk badge based on score"""
        if score >= 71:
            return '🚨'
        elif score >= 51:
            return '🔥'
        elif score >= 31:
            return '⚠️'
        return '✅'
