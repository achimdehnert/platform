"""
Management command to discover all URLs and create navigation items for unassigned ones.
Creates a catch-all domain "Unsortiert" with section "Keine Section".
"""
from django.core.management.base import BaseCommand
from django.urls import get_resolver, URLPattern, URLResolver
from apps.control_center.models_navigation import NavigationSection, NavigationItem
from apps.bfagent.models_domains import DomainArt


class Command(BaseCommand):
    help = 'Discover all URLs and create nav items for unassigned ones in "Unsortiert" domain'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
        parser.add_argument('--verbose', action='store_true', help='Show all discovered URLs')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        self.stdout.write(self.style.SUCCESS('\n🔍 Discovering Unassigned URLs\n'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE\n'))

        # Step 1: Create or get "Unsortiert" domain
        domain, domain_created = self._get_or_create_domain(dry_run)
        
        # Step 2: Create or get "Keine Section" section
        section, section_created = self._get_or_create_section(domain, dry_run)
        
        # Step 3: Get all existing navigation url_names
        existing_urls = set(NavigationItem.objects.values_list('url_name', flat=True))
        self.stdout.write(f'📊 Existing nav items: {len(existing_urls)}')
        
        # Step 4: Discover all named URL patterns
        all_urls = self._discover_urls()
        self.stdout.write(f'🔗 Total named URLs found: {len(all_urls)}')
        
        # Step 5: Find unassigned URLs
        unassigned = []
        for url_info in all_urls:
            url_name = url_info['name']
            # Skip admin, auth, debug, and already assigned
            if url_name in existing_urls:
                continue
            if any(skip in url_name for skip in ['admin:', 'debug_toolbar:', 'djdt:', 'auth:']):
                continue
            unassigned.append(url_info)
        
        self.stdout.write(f'❓ Unassigned URLs: {len(unassigned)}\n')
        
        if verbose:
            self.stdout.write('\n📋 All discovered URLs:')
            for url in all_urls:
                status = '✅' if url['name'] in existing_urls else '❌'
                self.stdout.write(f"  {status} {url['name']} -> {url['pattern']}")
        
        # Step 6: Create navigation items for unassigned URLs
        if not section and not dry_run:
            self.stdout.write(self.style.ERROR('Cannot create items without section'))
            return
            
        created_count = 0
        for url_info in unassigned:
            if dry_run:
                self.stdout.write(f"  [DRY] Would create: {url_info['name']}")
            else:
                try:
                    # Generate readable name from url_name
                    readable_name = self._url_to_name(url_info['name'])
                    
                    NavigationItem.objects.create(
                        section=section,
                        code=url_info['name'].replace(':', '_'),
                        name=readable_name,
                        description=f"Auto-discovered: {url_info['pattern']}",
                        item_type='link',
                        url_name=url_info['name'],
                        icon='bi-link-45deg',
                        order=100 + created_count,
                        is_active=True,
                    )
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Created: {readable_name}"))
                    created_count += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"  ⚠️ Skip {url_info['name']}: {e}"))
        
        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS(f'\n✅ COMPLETE:'))
        self.stdout.write(f'  Domain created: {domain_created}')
        self.stdout.write(f'  Section created: {section_created}')
        self.stdout.write(f'  Nav items created: {created_count}')
        self.stdout.write(f'\n💡 View at: /control-center/ under "Unsortiert" domain')

    def _get_or_create_domain(self, dry_run):
        """Get or create the Unsortiert domain"""
        try:
            domain = DomainArt.objects.filter(slug='unsortiert').first()
            if domain:
                self.stdout.write(f'📁 Domain exists: {domain.name}')
                return domain, False
            
            if dry_run:
                self.stdout.write('[DRY] Would create domain: Unsortiert')
                return None, True
            
            domain = DomainArt.objects.create(
                name='Unsortiert',
                slug='unsortiert',
                display_name='Unsortiert',
                description='Catch-all für unzugeordnete Apps und Views',
                icon='bi-question-circle',
                color='secondary',
                is_active=True,
                sort_order=999,
            )
            self.stdout.write(self.style.SUCCESS(f'✅ Created domain: {domain.name}'))
            return domain, True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating domain: {e}'))
            return None, False

    def _get_or_create_section(self, domain, dry_run):
        """Get or create the Keine Section section"""
        section = NavigationSection.objects.filter(code='keine_section').first()
        if section:
            self.stdout.write(f'📂 Section exists: {section.name}')
            return section, False
        
        if dry_run:
            self.stdout.write('[DRY] Would create section: Keine Section')
            return None, True
        
        section = NavigationSection.objects.create(
            code='keine_section',
            name='Keine Section',
            description='Unzugeordnete Navigation Items',
            icon='bi-inbox',
            color='secondary',
            order=999,
            slug='keine-section',
            is_active=True,
            is_collapsible=True,
            is_collapsed_default=True,
        )
        # Link to domain if possible
        if domain:
            section.domains.add(domain)
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created section: {section.name}'))
        return section, True

    def _discover_urls(self):
        """Discover all named URL patterns in the project"""
        urls = []
        resolver = get_resolver()
        self._extract_urls(resolver, '', urls)
        return urls

    def _extract_urls(self, resolver, prefix, urls):
        """Recursively extract URL patterns"""
        for pattern in resolver.url_patterns:
            if isinstance(pattern, URLResolver):
                # Namespace resolver
                new_prefix = prefix
                if pattern.namespace:
                    new_prefix = f"{prefix}{pattern.namespace}:" if prefix else f"{pattern.namespace}:"
                self._extract_urls(pattern, new_prefix, urls)
            elif isinstance(pattern, URLPattern):
                if pattern.name:
                    full_name = f"{prefix}{pattern.name}"
                    urls.append({
                        'name': full_name,
                        'pattern': str(pattern.pattern),
                    })

    def _url_to_name(self, url_name):
        """Convert url_name to readable name"""
        # Remove namespace prefix for display
        if ':' in url_name:
            name = url_name.split(':')[-1]
        else:
            name = url_name
        
        # Convert to title case
        name = name.replace('_', ' ').replace('-', ' ')
        return name.title()
