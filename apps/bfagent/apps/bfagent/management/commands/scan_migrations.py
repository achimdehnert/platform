"""
Management Command: Scan Django migrations and register in Migration Registry
"""
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connection
from pathlib import Path
import ast
import re
import hashlib
from apps.bfagent.models_registry import MigrationRegistry


class MigrationScanner:
    """Scans Django migration files"""
    
    @staticmethod
    def scan_app_migrations(app_label):
        """Scan all migrations for a specific app"""
        try:
            app_config = apps.get_app_config(app_label)
        except LookupError:
            return {'error': f'App {app_label} not found'}
        
        migrations_path = Path(app_config.path) / 'migrations'
        
        if not migrations_path.exists():
            return {'error': f'No migrations folder for {app_label}'}
        
        results = []
        migration_files = list(migrations_path.glob('0*.py'))
        
        for file_path in sorted(migration_files):
            migration_data = MigrationScanner.analyze_migration_file(
                app_label, file_path
            )
            if migration_data:
                results.append(migration_data)
        
        return {'migrations': results}
    
    @staticmethod
    def analyze_migration_file(app_label, file_path):
        """Analyze a single migration file"""
        migration_name = file_path.stem
        
        # Extract migration number
        match = re.match(r'(\d+)_', migration_name)
        if not match:
            return None
        
        migration_number = int(match.group(1))
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Calculate file hash
        file_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Parse AST
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return None
        
        # Extract description and operations
        description = ""
        operations_count = 0
        migration_type = 'schema'
        
        for node in ast.walk(tree):
            # Find Migration class
            if isinstance(node, ast.ClassDef) and node.name == 'Migration':
                # Get operations
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                if target.id == 'operations':
                                    if isinstance(item.value, ast.List):
                                        operations_count = len(item.value.elts)
                                        
                                        # Check if data migration
                                        for op in item.value.elts:
                                            if isinstance(op, ast.Call):
                                                if hasattr(op.func, 'attr'):
                                                    if op.func.attr == 'RunPython':
                                                        migration_type = 'data'
        
        # Simple complexity score
        complexity_score = operations_count * 5
        
        # Check if applied
        is_applied = MigrationScanner.check_if_applied(app_label, migration_name)
        
        return {
            'app_label': app_label,
            'migration_name': migration_name,
            'migration_number': migration_number,
            'file_path': str(file_path.relative_to(Path.cwd())),
            'file_hash': file_hash,
            'description': description,
            'migration_type': migration_type,
            'complexity_score': min(complexity_score, 100),
            'is_reversible': True,  # Default assumption
            'requires_downtime': False,
            'is_applied': is_applied,
        }
    
    @staticmethod
    def check_if_applied(app_label, migration_name):
        """Check if migration is applied in database"""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM django_migrations WHERE app = %s AND name = %s",
                [app_label, migration_name]
            )
            result = cursor.fetchone()
            return result[0] > 0 if result else False


class Command(BaseCommand):
    help = 'Scan and register Django migrations'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--app',
            type=str,
            help='Scan migrations for specific app'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n📋 Migration Scanner\n'))
        
        scanner = MigrationScanner()
        
        # Get list of apps to scan
        if options['app']:
            app_labels = [options['app']]
        else:
            # Scan all apps with migrations
            app_labels = [app.label for app in apps.get_app_configs() 
                          if (Path(app.path) / 'migrations').exists()]
        
        total_scanned = 0
        total_registered = 0
        
        for app_label in app_labels:
            result = scanner.scan_app_migrations(app_label)
            
            if 'error' in result:
                self.stdout.write(self.style.ERROR(f'  ✗ {app_label}: {result["error"]}'))
                continue
            
            migrations = result['migrations']
            total_scanned += len(migrations)
            
            # Register in database
            registered = 0
            for mig_data in migrations:
                obj, created = MigrationRegistry.objects.update_or_create(
                    app_label=mig_data['app_label'],
                    migration_name=mig_data['migration_name'],
                    defaults=mig_data
                )
                if created:
                    registered += 1
            
            total_registered += registered
            
            self.stdout.write(
                f'  ✅ {app_label:20} | Scanned: {len(migrations):3} | Registered: {registered:3}'
            )
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('📊 TOTAL SUMMARY'))
        self.stdout.write('='*70)
        self.stdout.write(f'Total Scanned:    {total_scanned}')
        self.stdout.write(f'✅ Registered:    {total_registered}')
        self.stdout.write('')
