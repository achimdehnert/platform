"""
Management command to populate domain_id and slug for existing NavigationSections
Phase 3 of incremental navigation migration
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from apps.bfagent.models import DomainArt
from apps.control_center.models_navigation import NavigationSection


class Command(BaseCommand):
    help = 'Populate domain_id and slug for existing NavigationSections'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without saving'
        )
        parser.add_argument(
            '--domain',
            type=str,
            default=None,
            help='Domain slug to assign (optional, leave empty to skip domain assignment)'
        )
        parser.add_argument(
            '--skip-domain',
            action='store_true',
            help='Skip domain assignment, only populate slugs'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        target_domain_slug = options['domain']
        skip_domain = options['skip_domain']
        
        self.stdout.write(self.style.SUCCESS('\n📋 Navigation Slug Population\n'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be saved\n'))
        
        # Get target domain (optional)
        target_domain = None
        if target_domain_slug and not skip_domain:
            try:
                target_domain = DomainArt.objects.get(slug=target_domain_slug)
                self.stdout.write(self.style.SUCCESS(
                    f'✅ Target Domain: {target_domain.display_name} (ID={target_domain.id}, slug={target_domain.slug})'
                ))
            except DomainArt.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'⚠️  Domain "{target_domain_slug}" not found!'))
                self.stdout.write('\nAvailable domains:')
                domains = DomainArt.objects.filter(is_active=True)
                if domains.exists():
                    for domain in domains:
                        self.stdout.write(f'  - {domain.slug} ({domain.display_name})')
                else:
                    self.stdout.write('  (No domains found in database)')
                self.stdout.write('\n⏭️  Continuing without domain assignment...\n')
        else:
            self.stdout.write(self.style.WARNING('⏭️  Skipping domain assignment, only populating slugs\n'))
        
        # Get sections that need migration
        sections_to_migrate = NavigationSection.objects.filter(slug__isnull=True) | NavigationSection.objects.filter(slug='')
        total_sections = sections_to_migrate.count()
        
        if total_sections == 0:
            self.stdout.write(self.style.SUCCESS('\n✅ All sections already have slugs assigned!'))
            return
        
        self.stdout.write(f'\n📊 Found {total_sections} sections to update:')
        
        updated_count = 0
        errors = []
        
        for section in sections_to_migrate:
            try:
                # Generate slug from code or name
                new_slug = section.code if section.code else slugify(section.name)
                
                # Check for slug conflicts
                existing = NavigationSection.objects.filter(
                    slug=new_slug
                ).exclude(id=section.id).first()
                
                if existing:
                    # Add suffix to make unique
                    counter = 1
                    while NavigationSection.objects.filter(
                        slug=f"{new_slug}-{counter}"
                    ).exclude(id=section.id).exists():
                        counter += 1
                    new_slug = f"{new_slug}-{counter}"
                
                domain_info = f'domain_id={target_domain.id}, ' if target_domain else ''
                self.stdout.write(
                    f'  • {section.name} → {domain_info}slug={new_slug}'
                )
                
                if not dry_run:
                    if target_domain:
                        section.domain_id = target_domain
                    section.slug = new_slug
                    update_fields = ['slug']
                    if target_domain:
                        update_fields.append('domain_id')
                    section.save(update_fields=update_fields)
                    updated_count += 1
                
            except Exception as e:
                error_msg = f'Error updating {section.name}: {e}'
                errors.append(error_msg)
                self.stdout.write(self.style.ERROR(f'  ❌ {error_msg}'))
        
        # Summary
        self.stdout.write('\n' + '='*60)
        if dry_run:
            self.stdout.write(self.style.WARNING(f'\n🔍 DRY RUN COMPLETE:'))
            self.stdout.write(f'  Would update: {total_sections} sections')
        else:
            self.stdout.write(self.style.SUCCESS(f'\n✅ MIGRATION COMPLETE:'))
            self.stdout.write(f'  Updated: {updated_count} sections')
            if errors:
                self.stdout.write(self.style.ERROR(f'  Errors: {len(errors)}'))
                for error in errors:
                    self.stdout.write(f'    - {error}')
        
        # Verification
        if not dry_run:
            self.stdout.write('\n📊 VERIFICATION:')
            remaining = NavigationSection.objects.filter(domain_id__isnull=True).count()
            self.stdout.write(f'  Sections without domain_id: {remaining}')
            
            if remaining == 0:
                self.stdout.write(self.style.SUCCESS('\n🎉 SUCCESS! All sections migrated!'))
                self.stdout.write('\n💡 NEXT STEPS:')
                self.stdout.write('  1. Test the system with old schema (USE_NEW_SCHEMA=False)')
                self.stdout.write('  2. Enable new schema (USE_NEW_SCHEMA=True) in settings.py')
                self.stdout.write('  3. Test again with new schema')
                self.stdout.write('  4. If all works, proceed to Phase 4 (Switch-Over)')
            else:
                self.stdout.write(self.style.WARNING(f'\n⚠️  Still {remaining} sections without domain_id'))
