"""
Django Management Command: Analyze docs folder and match with features
"""
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.bfagent.models import ComponentRegistry, FeatureDocument


class Command(BaseCommand):
    help = 'Analyze docs/ folder and match documents with features'

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

    def handle(self, *args, **options):
        PROJECT_ROOT = Path(settings.BASE_DIR)
        DOCS_FOLDER = PROJECT_ROOT / 'docs'

        self.stdout.write("=" * 80)
        self.stdout.write("DOCS FOLDER ANALYSIS")
        self.stdout.write("=" * 80)
        self.stdout.write("")

        # Get all MD files
        md_files = list(DOCS_FOLDER.glob("*.md"))
        self.stdout.write(f"📚 Found {len(md_files)} Markdown files")
        self.stdout.write("")

        # Get existing feature documents
        existing_docs = FeatureDocument.objects.all()
        existing_paths = set(doc.file_path for doc in existing_docs)
        self.stdout.write(f"📝 Already linked: {len(existing_paths)} documents")
        self.stdout.write("")

        # Analyze each file
        matched_docs = []
        unmatched_docs = []

        self.stdout.write("🔍 Analyzing documents...")
        self.stdout.write("")

        for md_file in md_files:
            relative_path = md_file.relative_to(PROJECT_ROOT)
            keywords = self.extract_keywords(md_file)
            features = self.find_matching_features(keywords)

            doc_info = {
                'path': str(relative_path),
                'name': md_file.stem,
                'keywords': keywords,
                'features': features,
                'already_linked': str(relative_path) in existing_paths,
            }

            if features:
                matched_docs.append(doc_info)
            else:
                unmatched_docs.append(doc_info)

        # Report: Matched documents
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS(f"✅ MATCHED DOCUMENTS ({len(matched_docs)})"))
        self.stdout.write("=" * 80)
        self.stdout.write("")

        for doc in sorted(matched_docs, key=lambda x: len(x['features']), reverse=True):
            status = "🔗 Linked" if doc['already_linked'] else "⚡ Ready to link"
            self.stdout.write(f"{status} {doc['name']}")
            self.stdout.write(f"  📂 {doc['path']}")
            self.stdout.write(f"  🏷️  Keywords: {', '.join(doc['keywords'])}")
            self.stdout.write(f"  🎯 Features ({len(doc['features'])}):")
            for feature in doc['features'][:3]:  # Show max 3
                self.stdout.write(f"     • {feature.name} ({feature.status})")
            if len(doc['features']) > 3:
                self.stdout.write(f"     ... and {len(doc['features']) - 3} more")
            self.stdout.write("")

        # Report: Unmatched documents
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.WARNING(f"❌ UNMATCHED DOCUMENTS ({len(unmatched_docs)})"))
        self.stdout.write("=" * 80)
        self.stdout.write("")

        if unmatched_docs:
            self.stdout.write("💡 These documents could become new features:")
            self.stdout.write("")

            for doc in sorted(unmatched_docs, key=lambda x: x['name']):
                self.stdout.write(f"📄 {doc['name']}")
                self.stdout.write(f"  Path: {doc['path']}")
                if doc['keywords']:
                    self.stdout.write(f"  Detected Keywords: {', '.join(doc['keywords'])}")
                else:
                    self.stdout.write(f"  No keywords detected - manual review needed")
                self.stdout.write("")
        else:
            self.stdout.write(self.style.SUCCESS("🎉 All documents have matching features!"))
            self.stdout.write("")

        # Summary
        self.stdout.write("=" * 80)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 80)
        self.stdout.write(f"Total documents:     {len(md_files)}")
        self.stdout.write(f"Already linked:      {len(existing_paths)}")
        unlinked_matched = len([d for d in matched_docs if not d['already_linked']])
        self.stdout.write(f"Matched (can link):  {unlinked_matched}")
        self.stdout.write(f"Unmatched:           {len(unmatched_docs)}")
        self.stdout.write("")

        # Feature suggestions
        if unmatched_docs:
            self.stdout.write("=" * 80)
            self.stdout.write(self.style.WARNING("💡 SUGGESTED NEW FEATURES"))
            self.stdout.write("=" * 80)
            self.stdout.write("")

            # Group by keywords
            suggestions = {}
            for doc in unmatched_docs:
                if doc['keywords']:
                    key = ', '.join(sorted(doc['keywords']))
                    if key not in suggestions:
                        suggestions[key] = []
                    suggestions[key].append(doc['name'])

            for idx, (keywords, docs) in enumerate(suggestions.items(), 1):
                self.stdout.write(f"{idx}. Feature based on: {keywords}")
                self.stdout.write(f"   Related docs: {len(docs)}")
                for doc_name in docs[:3]:
                    self.stdout.write(f"   • {doc_name}")
                if len(docs) > 3:
                    self.stdout.write(f"   ... and {len(docs) - 3} more")
                self.stdout.write("")
