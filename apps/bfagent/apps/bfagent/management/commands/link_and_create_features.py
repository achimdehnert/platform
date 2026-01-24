"""
Django Management Command: Link matched docs + Create features for unmatched docs
"""
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from apps.bfagent.models import ComponentRegistry, FeatureDocument, ComponentStatus, ComponentType


class Command(BaseCommand):
    help = 'Link matched documents and create features for unmatched documents'

    # Keyword mapping
    KEYWORD_MAPPINGS = {
        'llm': ['llm', 'language model', 'gpt', 'openai', 'anthropic', 'ai'],
        'handler': ['handler', 'handler system', 'handler architecture'],
        'character': ['character', 'character generation', 'character enrichment'],
        'world': ['world', 'world building', 'world settings'],
        'outline': ['outline', 'story outline', 'plot structure'],
        'chapter': ['chapter', 'chapter generation'],
        'agent': ['agent', 'ai agent', 'genagent'],
        'migration': ['migration', 'database migration'],
        'context': ['context', 'context builder', 'context provider'],
        'prompt': ['prompt', 'prompt template', 'prompt management'],
        'control': ['control center', 'dashboard'],
        'consistency': ['consistency', 'consistency framework'],
        'deployment': ['deployment', 'deploy'],
        'authentication': ['authentication', 'auth', 'permissions'],
        'api': ['api', 'graphql', 'rest'],
        'template': ['template', 'field template'],
        'book': ['book', 'book writing', 'book project'],
        'testing': ['testing', 'test'],
        'documentation': ['documentation', 'docs'],
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def extract_keywords(self, file_path):
        """Extract keywords from filename"""
        filename = file_path.stem.lower()
        keywords = []

        for keyword, variants in self.KEYWORD_MAPPINGS.items():
            for variant in variants:
                if variant in filename:
                    keywords.append(keyword)
                    break

        return list(set(keywords))

    def find_matching_features(self, keywords):
        """Find features matching keywords"""
        if not keywords:
            return []

        features = ComponentRegistry.objects.all()
        matched = []

        for feature in features:
            feature_text = f"{feature.name} {feature.description}".lower()
            for keyword in keywords:
                if keyword in feature_text:
                    matched.append(feature)
                    break

        return matched

    def extract_description(self, file_path, max_length=200):
        """Extract first paragraph as description"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Skip frontmatter if exists
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        content = parts[2]
                
                # Get first non-empty paragraph
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                for line in lines:
                    if not line.startswith('#') and len(line) > 20:
                        if len(line) > max_length:
                            return line[:max_length] + '...'
                        return line
                
                return "Documentation file - needs review"
        except Exception:
            return "Documentation file - needs review"

    def create_feature_name(self, doc_name):
        """Create a clean feature name from document name"""
        # Remove common prefixes
        name = doc_name
        prefixes = ['SESSION_', 'SESSION-', 'QUICK_START_', 'QUICK-START-']
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):]
        
        # Convert underscores/hyphens to spaces
        name = name.replace('_', ' ').replace('-', ' ')
        
        # Title case
        name = ' '.join(word.capitalize() for word in name.split())
        
        # Limit length
        if len(name) > 100:
            name = name[:97] + '...'
        
        return name

    def determine_component_type(self, keywords, doc_name):
        """Determine component type from keywords"""
        doc_lower = doc_name.lower()
        
        if 'guide' in doc_lower or 'documentation' in keywords:
            return ComponentType.UTILITY
        elif 'api' in keywords:
            return ComponentType.SERVICE
        elif 'template' in keywords or 'prompt' in keywords:
            return ComponentType.TEMPLATE
        elif 'testing' in keywords or 'test' in doc_lower:
            return ComponentType.UTILITY
        else:
            return ComponentType.UTILITY

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        PROJECT_ROOT = Path(settings.BASE_DIR)
        DOCS_FOLDER = PROJECT_ROOT / 'docs'

        self.stdout.write("=" * 80)
        self.stdout.write("LINK MATCHED DOCS + CREATE FEATURES FOR UNMATCHED")
        self.stdout.write("=" * 80)
        self.stdout.write("")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))
            self.stdout.write("")

        # Get all MD files
        md_files = list(DOCS_FOLDER.glob("*.md"))
        self.stdout.write(f"📚 Found {len(md_files)} Markdown files")
        self.stdout.write("")

        # Get existing feature documents (feature + file_path pairs)
        existing_docs = FeatureDocument.objects.all()
        existing_paths = {(doc.feature_id, doc.file_path) for doc in existing_docs}

        # Analyze each file
        matched_to_link = []
        unmatched_to_create = []

        for md_file in md_files:
            relative_path = str(md_file.relative_to(PROJECT_ROOT))
            keywords = self.extract_keywords(md_file)
            features = self.find_matching_features(keywords)

            if features:
                # Filter out features that are already linked to this document
                new_features = [f for f in features if (f.id, relative_path) not in existing_paths]
                
                if new_features:
                    matched_to_link.append({
                        'path': relative_path,
                        'file': md_file,
                        'name': md_file.stem,
                        'keywords': keywords,
                        'features': new_features,
                    })
            else:
                # Check if this document is already linked to ANY feature
                doc_already_exists = any(path == relative_path for _, path in existing_paths)
                if not doc_already_exists:
                    unmatched_to_create.append({
                        'path': relative_path,
                        'file': md_file,
                        'name': md_file.stem,
                        'keywords': keywords,
                    })

        # PHASE 1: Link matched documents
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS(f"PHASE 1: LINKING {len(matched_to_link)} MATCHED DOCUMENTS"))
        self.stdout.write("=" * 80)
        self.stdout.write("")

        linked_count = 0
        for doc_info in matched_to_link:
            if not dry_run:
                # Create FeatureDocument for each matched feature
                try:
                    word_count = len(doc_info['file'].read_text(encoding='utf-8').split())
                except Exception:
                    word_count = 0

                for feature in doc_info['features']:
                    # Create one document per feature (ForeignKey relationship)
                    FeatureDocument.objects.create(
                        feature=feature,
                        file_path=doc_info['path'],
                        title=doc_info['name'],
                        description=self.extract_description(doc_info['file']),
                        document_type='guide',
                        word_count=word_count,
                        is_auto_discovered=True,
                    )
                
                linked_count += 1

                self.stdout.write(
                    f"✅ Linked: {doc_info['name']} → {len(doc_info['features'])} features"
                )
            else:
                self.stdout.write(
                    f"[DRY RUN] Would link: {doc_info['name']} → {len(doc_info['features'])} features"
                )

        self.stdout.write("")
        self.stdout.write(f"Linked {linked_count} documents")
        self.stdout.write("")

        # PHASE 2: Create features for unmatched documents
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.WARNING(f"PHASE 2: CREATING {len(unmatched_to_create)} NEW FEATURES"))
        self.stdout.write("=" * 80)
        self.stdout.write("")

        created_count = 0
        for doc_info in unmatched_to_create:
            feature_name = self.create_feature_name(doc_info['name'])
            description = self.extract_description(doc_info['file'])
            component_type = self.determine_component_type(doc_info['keywords'], doc_info['name'])
            
            # Determine domain
            if 'book' in doc_info['keywords'] or 'character' in doc_info['keywords']:
                domain = 'book'
            elif 'agent' in doc_info['keywords']:
                domain = 'agent'
            else:
                domain = 'system'

            if not dry_run:
                # Create Feature
                feature = ComponentRegistry.objects.create(
                    identifier=f"proposed.utility.{doc_info['name'].lower()[:50]}",
                    name=feature_name,
                    component_type=component_type,
                    domain=domain,
                    description=description,
                    status=ComponentStatus.PROPOSED,
                    priority='backlog',  # Needs review before prioritization
                    proposed_at=timezone.now(),
                )

                # Create FeatureDocument and link
                try:
                    word_count = len(doc_info['file'].read_text(encoding='utf-8').split())
                except Exception:
                    word_count = 0

                FeatureDocument.objects.create(
                    feature=feature,
                    file_path=doc_info['path'],
                    title=doc_info['name'],
                    description=description,
                    document_type='guide',
                    word_count=word_count,
                    is_auto_discovered=True,
                )

                created_count += 1
                keywords_str = ', '.join(doc_info['keywords']) if doc_info['keywords'] else 'none'
                self.stdout.write(
                    f"✨ Created: {feature_name} ({component_type}) [{keywords_str}]"
                )
            else:
                keywords_str = ', '.join(doc_info['keywords']) if doc_info['keywords'] else 'none'
                self.stdout.write(
                    f"[DRY RUN] Would create: {feature_name} ({component_type}) [{keywords_str}]"
                )

        self.stdout.write("")
        self.stdout.write(f"Created {created_count} new features")
        self.stdout.write("")

        # Summary
        unique_linked_docs = len({path for _, path in existing_paths})
        self.stdout.write("=" * 80)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 80)
        self.stdout.write(f"Total documents:         {len(md_files)}")
        self.stdout.write(f"Already linked:          {unique_linked_docs} docs ({len(existing_paths)} links)")
        self.stdout.write(f"Newly linked:            {linked_count}")
        self.stdout.write(f"Features created:        {created_count}")
        self.stdout.write("")

        if not dry_run:
            self.stdout.write(self.style.SUCCESS("✅ ALL DONE!"))
            self.stdout.write("")
            self.stdout.write("Next steps:")
            self.stdout.write("1. Review features at: http://localhost:8000/control-center/feature-planning/")
            self.stdout.write("2. Update status, priority, and descriptions")
            self.stdout.write("3. Assign owners")
        else:
            self.stdout.write(self.style.WARNING("Run without --dry-run to apply changes"))
