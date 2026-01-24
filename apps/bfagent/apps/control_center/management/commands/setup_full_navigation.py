"""
Management command to setup complete navigation structure with automatic categorization.
Creates domains, sections, and navigation items based on URL patterns.
"""
from django.core.management.base import BaseCommand
from django.urls import get_resolver, URLPattern, URLResolver
from apps.control_center.models_navigation import NavigationSection, NavigationItem
from apps.bfagent.models_domains import DomainArt


# Domain definitions with sections
DOMAIN_CONFIG = {
    'control_center': {
        'name': 'Control Center',
        'slug': 'control-center',
        'icon': 'bi-gear',
        'color': 'primary',
        'description': 'System tools, monitoring, and development utilities',
        'sections': {
            'dashboard': {'name': 'Dashboard', 'icon': 'bi-speedometer2', 'order': 10},
            'workflow_engine': {'name': 'Workflow Engine', 'icon': 'bi-diagram-3', 'order': 20},
            'ai_engine': {'name': 'AI Engine', 'icon': 'bi-cpu', 'order': 30},
            'data_management': {'name': 'Data Management', 'icon': 'bi-database', 'order': 40},
            'system_admin': {'name': 'System Admin', 'icon': 'bi-sliders', 'order': 50},
            'development': {'name': 'Development Tools', 'icon': 'bi-code-slash', 'order': 60},
            'mcp': {'name': 'MCP Integration', 'icon': 'bi-plug', 'order': 70},
        }
    },
    'writing_hub': {
        'name': 'Writing Hub',
        'slug': 'writing-hub',
        'icon': 'bi-book',
        'color': 'success',
        'description': 'Modern novel series management with AI chapter generation',
        'sections': {
            'dashboard': {'name': 'Dashboard', 'icon': 'bi-speedometer2', 'order': 10},
            'projects': {'name': 'Projekte', 'icon': 'bi-folder', 'order': 20},
            'reader': {'name': 'Book Reader', 'icon': 'bi-book-half', 'order': 30},
        }
    },
    'expert_hub': {
        'name': 'Expert Hub (Deprecated)',
        'slug': 'expert-hub',
        'icon': 'bi-archive',
        'color': 'secondary',
        'description': 'DEPRECATED - Wird eingestellt. Nutze CAD Hub, MedTrans oder Writing Hub.',
        'is_deprecated': True,
        'sections': {
            'dashboard': {'name': 'Übersicht', 'icon': 'bi-exclamation-triangle', 'order': 10},
        }
    },
    'cad_hub': {
        'name': 'CAD Hub',
        'slug': 'cad-hub',
        'icon': 'bi-building',
        'color': 'info',
        'description': 'CAD & Zeichnungsanalyse - IFC Model Processing',
        'sections': {
            'dashboard': {'name': 'Dashboard', 'icon': 'bi-speedometer2', 'order': 10},
            'projects': {'name': 'Projekte', 'icon': 'bi-folder', 'order': 20},
            'models': {'name': 'Modelle', 'icon': 'bi-box', 'order': 30},
            'analysis': {'name': 'Analyse', 'icon': 'bi-bar-chart', 'order': 40},
            'export': {'name': 'Export', 'icon': 'bi-download', 'order': 50},
        }
    },
    'format_hub': {
        'name': 'Format Hub',
        'slug': 'format-hub',
        'icon': 'bi-file-earmark-richtext',
        'color': 'secondary',
        'description': 'Medical Translation and PPTX Studio combined',
        'sections': {
            'medtrans': {'name': 'Medical Translation', 'icon': 'bi-translate', 'order': 10},
            'pptx': {'name': 'Presentation Studio', 'icon': 'bi-file-earmark-ppt', 'order': 20},
        }
    },
    'research_hub': {
        'name': 'Research Hub',
        'slug': 'research-hub',
        'icon': 'bi-search',
        'color': 'purple',
        'description': 'Recherche-Service - Web Search, Fact-Checking, Literatursuche (integriert in Writing Hub)',
        'is_service': True,  # Indicates this is a service layer, not a standalone hub
        'sections': {
            'dashboard': {'name': 'Dashboard', 'icon': 'bi-speedometer2', 'order': 10},
            'research': {'name': 'Recherche', 'icon': 'bi-journal-text', 'order': 20},
        }
    },
    'dsb_hub': {
        'name': 'DSB Hub',
        'slug': 'dsb-hub',
        'icon': 'bi-shield-check',
        'color': 'danger',
        'description': 'DSGVO & Datenschutzbeauftragter Management',
        'sections': {
            'dashboard': {'name': 'Dashboard', 'icon': 'bi-speedometer2', 'order': 10},
            'compliance': {'name': 'Compliance', 'icon': 'bi-clipboard-check', 'order': 20},
        }
    },
    'dlm_hub': {
        'name': 'DLM Hub',
        'slug': 'dlm-hub',
        'icon': 'bi-hdd-stack',
        'color': 'dark',
        'description': 'Data Lifecycle Management',
        'sections': {
            'dashboard': {'name': 'Dashboard', 'icon': 'bi-speedometer2', 'order': 10},
        }
    },
    'unsortiert': {
        'name': 'Unsortiert',
        'slug': 'unsortiert',
        'icon': 'bi-question-circle',
        'color': 'secondary',
        'description': 'Catch-all für unzugeordnete Apps',
        'sections': {
            'keine_section': {'name': 'Keine Section', 'icon': 'bi-inbox', 'order': 999},
        }
    },
}

# URL prefix to domain/section mapping
URL_MAPPING = {
    # Control Center
    'control_center:dashboard': ('control_center', 'dashboard'),
    'control_center:master-data': ('control_center', 'data_management'),
    'control_center:workflow': ('control_center', 'workflow_engine'),
    'control_center:agents': ('control_center', 'ai_engine'),
    'control_center:llms': ('control_center', 'ai_engine'),
    'control_center:templates': ('control_center', 'ai_engine'),
    'control_center:genagent': ('control_center', 'ai_engine'),
    'control_center:api': ('control_center', 'development'),
    'control_center:code-review': ('control_center', 'development'),
    'control_center:model-consistency': ('control_center', 'development'),
    'control_center:migration': ('control_center', 'development'),
    'control_center:feature': ('control_center', 'development'),
    'control_center:mcp': ('control_center', 'mcp'),
    'control_center:system': ('control_center', 'system_admin'),
    'control_center:metrics': ('control_center', 'system_admin'),
    
    # BFAgent (mostly control center)
    'bfagent:workflow': ('control_center', 'workflow_engine'),
    'bfagent:agents': ('control_center', 'ai_engine'),
    'bfagent:llms': ('control_center', 'ai_engine'),
    'bfagent:prompt': ('control_center', 'ai_engine'),
    'bfagent:field': ('control_center', 'data_management'),
    'bfagent:domain': ('control_center', 'data_management'),
    
    # GenAgent
    'genagent:': ('control_center', 'ai_engine'),
    
    # Writing Hub
    'writing_hub:': ('writing_hub', 'dashboard'),
    'book_reader:': ('writing_hub', 'reader'),
    
    # Expert Hub
    'expert_hub:': ('expert_hub', 'dashboard'),
    
    # CAD Hub
    'cad_hub:dashboard': ('cad_hub', 'dashboard'),
    'cad_hub:project': ('cad_hub', 'projects'),
    'cad_hub:model': ('cad_hub', 'models'),
    'cad_hub:room': ('cad_hub', 'analysis'),
    'cad_hub:wall': ('cad_hub', 'analysis'),
    'cad_hub:door': ('cad_hub', 'analysis'),
    'cad_hub:window': ('cad_hub', 'analysis'),
    'cad_hub:slab': ('cad_hub', 'analysis'),
    'cad_hub:area': ('cad_hub', 'analysis'),
    'cad_hub:woflv': ('cad_hub', 'analysis'),
    'cad_hub:export': ('cad_hub', 'export'),
    'cad_hub:ifc': ('cad_hub', 'models'),
    'cad_hub:cad': ('cad_hub', 'models'),
    
    # Format Hub
    'medtrans:': ('format_hub', 'medtrans'),
    'presentation_studio:': ('format_hub', 'pptx'),
    
    # Workflow System
    'workflow_system:': ('control_center', 'workflow_engine'),
    'checklist_system:': ('control_center', 'workflow_engine'),
    
    # Features
    'features:': ('control_center', 'development'),
    
    # Hub (generic)
    'hub:': ('unsortiert', 'keine_section'),
}

# URLs to skip (not user-facing or redundant)
SKIP_PATTERNS = [
    'api-',  # API endpoints (internal)
    '-delete',  # Delete confirmations
    '-execute',  # Execute actions (triggered from UI)
    'sse-',  # Server-sent events
    '-reorder',  # Reorder actions
]

# URLs to always include (override skip)
ALWAYS_INCLUDE = [
    'dashboard',
    '-list',
    '-create',
]


class Command(BaseCommand):
    help = 'Setup complete navigation with automatic categorization'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
        parser.add_argument('--include-all', action='store_true', help='Include all URLs (no filtering)')
        parser.add_argument('--reset', action='store_true', help='Reset all navigation items first')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        include_all = options['include_all']
        reset = options['reset']
        
        self.stdout.write(self.style.SUCCESS('\n🚀 Setting Up Complete Navigation\n'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE\n'))

        # Step 0: Reset if requested
        if reset and not dry_run:
            self.stdout.write('🗑️  Resetting navigation...')
            NavigationItem.objects.all().delete()
            NavigationSection.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('  Done'))

        # Step 1: Create/update domains
        self.stdout.write('\n📁 Setting up domains...')
        domains = self._setup_domains(dry_run)
        
        # Step 2: Create/update sections
        self.stdout.write('\n📂 Setting up sections...')
        sections = self._setup_sections(domains, dry_run)
        
        # Step 3: Get existing nav items
        existing_urls = set(NavigationItem.objects.values_list('url_name', flat=True))
        
        # Step 4: Discover URLs
        self.stdout.write('\n🔍 Discovering URLs...')
        all_urls = self._discover_urls()
        self.stdout.write(f'  Found {len(all_urls)} named URLs')
        
        # Step 5: Create navigation items
        self.stdout.write('\n📌 Creating navigation items...')
        stats = {'created': 0, 'skipped': 0, 'existing': 0}
        
        for url_info in all_urls:
            url_name = url_info['name']
            
            # Skip if exists
            if url_name in existing_urls:
                stats['existing'] += 1
                continue
            
            # Skip admin/debug
            if any(skip in url_name for skip in ['admin:', 'debug_toolbar:', 'djdt:', 'auth:']):
                stats['skipped'] += 1
                continue
            
            # Check if should be included
            if not include_all:
                should_skip = any(skip in url_name for skip in SKIP_PATTERNS)
                force_include = any(inc in url_name for inc in ALWAYS_INCLUDE)
                if should_skip and not force_include:
                    stats['skipped'] += 1
                    continue
            
            # Find domain/section
            domain_key, section_key = self._find_mapping(url_name)
            
            if domain_key not in sections or section_key not in sections[domain_key]:
                domain_key, section_key = 'unsortiert', 'keine_section'
            
            section = sections.get(domain_key, {}).get(section_key)
            if not section and not dry_run:
                stats['skipped'] += 1
                continue
            
            # Create nav item
            readable_name = self._url_to_name(url_name)
            icon = self._get_icon_for_url(url_name)
            
            if dry_run:
                self.stdout.write(f'  [DRY] {url_name} → {domain_key}/{section_key}')
            else:
                try:
                    NavigationItem.objects.create(
                        section=section,
                        code=url_name.replace(':', '_').replace('-', '_'),
                        name=readable_name,
                        description=f'Auto: {url_info["pattern"]}',
                        item_type='link',
                        url_name=url_name,
                        icon=icon,
                        order=100 + stats['created'],
                        is_active=True,
                    )
                    stats['created'] += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  ⚠️ {url_name}: {e}'))
                    stats['skipped'] += 1
        
        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('\n✅ COMPLETE:'))
        self.stdout.write(f'  Domains: {len(domains)}')
        self.stdout.write(f'  Sections: {sum(len(s) for s in sections.values())}')
        self.stdout.write(f'  Nav items created: {stats["created"]}')
        self.stdout.write(f'  Already existed: {stats["existing"]}')
        self.stdout.write(f'  Skipped (filtered): {stats["skipped"]}')
        self.stdout.write(f'\n💡 Test at: http://localhost:8000/')

    def _setup_domains(self, dry_run):
        """Create or get all domains"""
        domains = {}
        for key, config in DOMAIN_CONFIG.items():
            domain = DomainArt.objects.filter(slug=config['slug']).first()
            if domain:
                self.stdout.write(f'  ✓ {config["name"]} (exists)')
            elif not dry_run:
                domain = DomainArt.objects.create(
                    name=config['name'],
                    slug=config['slug'],
                    display_name=config['name'],
                    description=config['description'],
                    icon=config['icon'],
                    color=config['color'],
                    is_active=True,
                )
                self.stdout.write(self.style.SUCCESS(f'  ✅ {config["name"]} (created)'))
            else:
                self.stdout.write(f'  [DRY] Would create: {config["name"]}')
            domains[key] = domain
        return domains

    def _setup_sections(self, domains, dry_run):
        """Create or get all sections"""
        sections = {}
        for domain_key, domain_config in DOMAIN_CONFIG.items():
            sections[domain_key] = {}
            domain = domains.get(domain_key)
            
            for section_key, section_config in domain_config.get('sections', {}).items():
                code = f'{domain_key}_{section_key}'
                section = NavigationSection.objects.filter(code=code).first()
                
                if section:
                    pass  # exists
                elif not dry_run:
                    section = NavigationSection.objects.create(
                        code=code,
                        name=section_config['name'],
                        description=f'{section_config["name"]} in {domain_config["name"]}',
                        icon=section_config['icon'],
                        color=domain_config['color'],
                        order=section_config['order'],
                        slug=code.replace('_', '-'),
                        is_active=True,
                        is_collapsible=True,
                        is_collapsed_default=section_key != 'dashboard',
                        domain_id=domain,  # Use FK to DomainArt (new schema)
                    )
                    self.stdout.write(self.style.SUCCESS(f'    ✅ {section_config["name"]}'))
                
                sections[domain_key][section_key] = section
        
        return sections

    def _find_mapping(self, url_name):
        """Find domain/section for URL"""
        # Check exact matches first
        for pattern, (domain, section) in URL_MAPPING.items():
            if url_name.startswith(pattern):
                return domain, section
        
        # Fallback to unsortiert
        return 'unsortiert', 'keine_section'

    def _discover_urls(self):
        """Discover all named URLs"""
        urls = []
        resolver = get_resolver()
        self._extract_urls(resolver, '', urls)
        return urls

    def _extract_urls(self, resolver, prefix, urls):
        """Recursively extract URL patterns"""
        for pattern in resolver.url_patterns:
            if isinstance(pattern, URLResolver):
                new_prefix = prefix
                if pattern.namespace:
                    new_prefix = f'{prefix}{pattern.namespace}:' if prefix else f'{pattern.namespace}:'
                self._extract_urls(pattern, new_prefix, urls)
            elif isinstance(pattern, URLPattern):
                if pattern.name:
                    urls.append({
                        'name': f'{prefix}{pattern.name}',
                        'pattern': str(pattern.pattern),
                    })

    def _url_to_name(self, url_name):
        """Convert url_name to readable name"""
        if ':' in url_name:
            name = url_name.split(':')[-1]
        else:
            name = url_name
        name = name.replace('_', ' ').replace('-', ' ')
        return name.title()

    def _get_icon_for_url(self, url_name):
        """Get appropriate icon for URL"""
        if 'dashboard' in url_name:
            return 'bi-speedometer2'
        elif 'list' in url_name:
            return 'bi-list'
        elif 'create' in url_name:
            return 'bi-plus-circle'
        elif 'edit' in url_name or 'update' in url_name:
            return 'bi-pencil'
        elif 'detail' in url_name:
            return 'bi-eye'
        elif 'export' in url_name:
            return 'bi-download'
        elif 'upload' in url_name:
            return 'bi-upload'
        elif 'search' in url_name:
            return 'bi-search'
        elif 'config' in url_name or 'settings' in url_name:
            return 'bi-gear'
        return 'bi-link-45deg'
