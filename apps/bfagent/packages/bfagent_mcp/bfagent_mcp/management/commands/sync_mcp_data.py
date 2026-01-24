"""
Django Management Command: sync_mcp_data
==========================================

Synchronisiert alle MCP Initial-Daten:
- Naming Conventions
- Component Types
- Risk Levels
- Protection Levels
- Path Categories
- Protected Paths
- Domain Configs

Usage:
    python manage.py sync_mcp_data
    python manage.py sync_mcp_data --dry-run
    python manage.py sync_mcp_data --only naming
    python manage.py sync_mcp_data --only components
"""

import asyncio
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = 'Synchronize MCP initial data (naming conventions, component types, etc.)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without making changes',
        )
        parser.add_argument(
            '--only',
            type=str,
            choices=[
                'naming', 'components', 'risk', 'protection',
                'categories', 'paths', 'domains', 'all'
            ],
            default='all',
            help='Sync only specific data type',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even if data exists',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        only = options['only']
        
        self.stdout.write(self.style.NOTICE(
            f"\n{'='*60}\n"
            f"BF Agent MCP - Data Sync\n"
            f"{'='*60}\n"
        ))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made\n'))
        
        try:
            from bfagent_mcp.data_loader_mcp import (
                sync_naming_conventions,
                sync_mcp_component_types,
                sync_mcp_risk_levels,
                sync_mcp_protection_levels,
                sync_mcp_path_categories,
                sync_mcp_protected_paths,
                sync_mcp_domain_configs,
                sync_all_mcp_data,
            )
        except ImportError as e:
            raise CommandError(f'Could not import data_loader_mcp: {e}')
        
        results = {}
        
        if only == 'all':
            # Sync everything
            self.stdout.write('Syncing ALL MCP data...\n')
            if not dry_run:
                results = asyncio.run(sync_all_mcp_data())
        else:
            # Sync specific type
            sync_map = {
                'naming': ('Naming Conventions', sync_naming_conventions),
                'components': ('Component Types', sync_mcp_component_types),
                'risk': ('Risk Levels', sync_mcp_risk_levels),
                'protection': ('Protection Levels', sync_mcp_protection_levels),
                'categories': ('Path Categories', sync_mcp_path_categories),
                'paths': ('Protected Paths', sync_mcp_protected_paths),
                'domains': ('Domain Configs', sync_mcp_domain_configs),
            }
            
            if only in sync_map:
                name, sync_func = sync_map[only]
                self.stdout.write(f'Syncing {name}...\n')
                if not dry_run:
                    results[only] = asyncio.run(sync_func())
        
        # Print results
        self.stdout.write(self.style.SUCCESS('\n📊 Results:\n'))
        
        if dry_run:
            self.stdout.write('  (dry run - no changes made)\n')
        else:
            for key, value in results.items():
                if isinstance(value, dict):
                    created = value.get('created', 0)
                    updated = value.get('updated', 0)
                    skipped = value.get('skipped', 0)
                    components = value.get('components', 0)
                    
                    status = []
                    if created:
                        status.append(f'+{created} created')
                    if updated:
                        status.append(f'~{updated} updated')
                    if skipped:
                        status.append(f'-{skipped} skipped')
                    if components:
                        status.append(f'+{components} components')
                    
                    self.stdout.write(f'  {key}: {", ".join(status) or "no changes"}\n')
                else:
                    self.stdout.write(f'  {key}: {value}\n')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Sync complete!\n'))
