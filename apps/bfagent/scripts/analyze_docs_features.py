"""
Analyze docs/ folder and match with features
"""
import os
import sys
from pathlib import Path

# UTF-8 ENCODING FIX (REQUIRED FOR WINDOWS)
os.environ.setdefault("PYTHONUTF8", "1")
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.bfagent.models import ComponentRegistry, FeatureDocument
from django.conf import settings

# Configuration
PROJECT_ROOT = Path(settings.BASE_DIR)
DOCS_FOLDER = PROJECT_ROOT / 'docs'

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

def extract_keywords(file_path: Path) -> list[str]:
    """Extract keywords from filename"""
    filename = file_path.stem.lower()
    keywords = []
    
    for keyword, variants in KEYWORD_MAPPINGS.items():
        for variant in variants:
            if variant in filename:
                keywords.append(keyword)
                break
    
    return list(set(keywords))

def find_matching_features(keywords: list[str]) -> list:
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

def main():
    print("=" * 80)
    print("DOCS FOLDER ANALYSIS")
    print("=" * 80)
    print()
    
    # Get all MD files
    md_files = list(DOCS_FOLDER.glob("*.md"))
    print(f"📚 Found {len(md_files)} Markdown files")
    print()
    
    # Get existing feature documents
    existing_docs = FeatureDocument.objects.all()
    existing_paths = set(doc.file_path for doc in existing_docs)
    print(f"📝 Already linked: {len(existing_paths)} documents")
    print()
    
    # Analyze each file
    matched_docs = []
    unmatched_docs = []
    
    print("🔍 Analyzing documents...")
    print()
    
    for md_file in md_files:
        relative_path = md_file.relative_to(PROJECT_ROOT)
        keywords = extract_keywords(md_file)
        features = find_matching_features(keywords)
        
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
    print("=" * 80)
    print(f"✅ MATCHED DOCUMENTS ({len(matched_docs)})")
    print("=" * 80)
    print()
    
    for doc in sorted(matched_docs, key=lambda x: len(x['features']), reverse=True):
        status = "🔗 Linked" if doc['already_linked'] else "⚡ Ready to link"
        print(f"{status} {doc['name']}")
        print(f"  📂 {doc['path']}")
        print(f"  🏷️  Keywords: {', '.join(doc['keywords'])}")
        print(f"  🎯 Features ({len(doc['features'])}):")
        for feature in doc['features'][:3]:  # Show max 3
            print(f"     • {feature.name} ({feature.status})")
        if len(doc['features']) > 3:
            print(f"     ... and {len(doc['features']) - 3} more")
        print()
    
    # Report: Unmatched documents
    print("=" * 80)
    print(f"❌ UNMATCHED DOCUMENTS ({len(unmatched_docs)})")
    print("=" * 80)
    print()
    
    if unmatched_docs:
        print("💡 These documents could become new features:")
        print()
        
        for doc in sorted(unmatched_docs, key=lambda x: x['name']):
            print(f"📄 {doc['name']}")
            print(f"  Path: {doc['path']}")
            if doc['keywords']:
                print(f"  Detected Keywords: {', '.join(doc['keywords'])}")
            else:
                print(f"  No keywords detected - manual review needed")
            print()
    else:
        print("🎉 All documents have matching features!")
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total documents:     {len(md_files)}")
    print(f"Already linked:      {len(existing_paths)}")
    print(f"Matched (can link):  {len([d for d in matched_docs if not d['already_linked']])}")
    print(f"Unmatched:           {len(unmatched_docs)}")
    print()
    
    # Feature suggestions
    if unmatched_docs:
        print("=" * 80)
        print("💡 SUGGESTED NEW FEATURES")
        print("=" * 80)
        print()
        
        # Group by keywords
        suggestions = {}
        for doc in unmatched_docs:
            if doc['keywords']:
                key = ', '.join(sorted(doc['keywords']))
                if key not in suggestions:
                    suggestions[key] = []
                suggestions[key].append(doc['name'])
        
        for idx, (keywords, docs) in enumerate(suggestions.items(), 1):
            print(f"{idx}. Feature based on: {keywords}")
            print(f"   Related docs: {len(docs)}")
            for doc_name in docs[:3]:
                print(f"   • {doc_name}")
            if len(docs) > 3:
                print(f"   ... and {len(docs) - 3} more")
            print()

if __name__ == '__main__':
    main()
