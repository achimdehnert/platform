"""
Management command to sync domains from DomainRegistry to Database
"""

from django.core.management.base import BaseCommand
from apps.core.models import Domain
from apps.core.features import get_domain_registry


class Command(BaseCommand):
    help = 'Sync domains from DomainRegistry (code) to Database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without actually syncing'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        domain_registry = get_domain_registry()
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made\n'))
        
        synced = 0
        created = 0
        updated = 0
        
        for domain_id, domain_info in domain_registry.domains.items():
            try:
                # Get or create domain in DB
                domain, is_created = Domain.objects.get_or_create(
                    domain_id=domain_id,
                    defaults={
                        'name': domain_info.name,
                        'description': domain_info.description,
                        'category': domain_info.category.value,
                        'version': domain_info.version,
                        'base_path': domain_info.base_path,
                        'is_active': domain_info.is_active,
                        'dependencies': domain_info.dependencies,
                        'metadata': domain_info.metadata,
                    }
                )
                
                if dry_run:
                    if is_created:
                        self.stdout.write(f"Would CREATE: {domain_id} - {domain_info.name}")
                    else:
                        self.stdout.write(f"Would UPDATE: {domain_id} - {domain_info.name}")
                    continue
                
                if is_created:
                    created += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Created: {domain_id} - {domain_info.name}")
                    )
                else:
                    # Update existing domain
                    updated_fields = []
                    
                    if domain.name != domain_info.name:
                        domain.name = domain_info.name
                        updated_fields.append('name')
                    
                    if domain.description != domain_info.description:
                        domain.description = domain_info.description
                        updated_fields.append('description')
                    
                    if domain.category != domain_info.category.value:
                        domain.category = domain_info.category.value
                        updated_fields.append('category')
                    
                    if domain.version != domain_info.version:
                        domain.version = domain_info.version
                        updated_fields.append('version')
                    
                    if domain.base_path != domain_info.base_path:
                        domain.base_path = domain_info.base_path
                        updated_fields.append('base_path')
                    
                    if domain.is_active != domain_info.is_active:
                        domain.is_active = domain_info.is_active
                        updated_fields.append('is_active')
                    
                    if domain.dependencies != domain_info.dependencies:
                        domain.dependencies = domain_info.dependencies
                        updated_fields.append('dependencies')
                    
                    if domain.metadata != domain_info.metadata:
                        domain.metadata = domain_info.metadata
                        updated_fields.append('metadata')
                    
                    if updated_fields:
                        domain.save()
                        updated += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"↻ Updated: {domain_id} - {', '.join(updated_fields)}"
                            )
                        )
                    else:
                        self.stdout.write(
                            f"= Unchanged: {domain_id}"
                        )
                
                synced += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Error syncing {domain_id}: {str(e)}")
                )
        
        # Summary
        self.stdout.write("\n" + "=" * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN COMPLETED"))
        else:
            self.stdout.write(self.style.SUCCESS("SYNC COMPLETED"))
        self.stdout.write(f"Total domains in registry: {len(domain_registry.domains)}")
        self.stdout.write(f"Synced: {synced}")
        if not dry_run:
            self.stdout.write(f"Created: {created}")
            self.stdout.write(f"Updated: {updated}")
