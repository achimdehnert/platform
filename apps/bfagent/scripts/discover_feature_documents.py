#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Feature Document Auto-Discovery Script

Scans docs/ folder for Markdown files and automatically links them to features
based on filename patterns and content keywords.

Usage:
    python manage.py shell
    >>> exec(open('scripts/discover_feature_documents.py', encoding='utf-8').read())
"""

import os
import sys
import django
from pathlib import Path
import re

# UTF-8 ENCODING FIX (REQUIRED FOR WINDOWS)
os.environ.setdefault("PYTHONUTF8", "1")
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.bfagent.models import ComponentRegistry, FeatureDocument, FeatureDocumentKeyword
from django.conf import settings

# Configuration - Use Django settings for PROJECT_ROOT
PROJECT_ROOT = Path(settings.BASE_DIR)
DOCS_FOLDER = PROJECT_ROOT / 'docs'

# Keyword mapping (lowercase for matching)
KEYWORD_MAPPINGS = {
    'llm': ['llm', 'language model', 'gpt', 'openai', 'anthropic'],
    'handler': ['handler', 'handler system', 'handler architecture'],
    'character': ['character', 'character generation', 'character enrichment'],
    'world': ['world', 'world building', 'world settings'],
    'outline': ['outline', 'story outline', 'plot structure'],
    'chapter': ['chapter', 'chapter generation'],
    'phase': ['phase', 'workflow phase', 'phase model'],
    'migration': ['migration', 'django migration', 'database migration'],
    'feature': ['feature', 'feature planning', 'feature registry'],
    'domain': ['domain', 'domain model', 'domain-driven'],
    'accessibility': ['accessibility', 'aria', 'wcag', 'a11y'],
    'refactoring': ['refactor', 'refactoring', 'code cleanup'],
    'architecture': ['architecture', 'system design', 'design pattern'],
    'handler_pipeline': ['handler pipeline', 'processing pipeline'],
    'genagent': ['genagent', 'gen agent', 'phase-agent'],
    'medtrans': ['medtrans', 'medical translation', 'pptx translation'],
    'crud': ['crud', 'create read update delete'],
    'ui': ['ui', 'user interface', 'template', 'htmx'],
}


def estimate_word_count(content: str) -> int:
    """Estimate word count from content"""
    words = content.split()
    return len(words)


def extract_keywords_from_content(content: str) -> list:
    """Extract potential keywords from document content"""
    content_lower = content.lower()
    found_keywords = set()
    
    for category, keywords in KEYWORD_MAPPINGS.items():
        for keyword in keywords:
            if keyword in content_lower:
                found_keywords.add(category)
                break
    
    return list(found_keywords)


def extract_doc_title(content: str, filename: str) -> str:
    """Extract document title from content or use filename"""
    # Try to find first # heading
    lines = content.split('\n')
    for line in lines[:10]:  # Check first 10 lines
        if line.startswith('# '):
            return line[2:].strip()
    
    # Fall back to filename
    return filename.replace('_', ' ').replace('.md', '').title()


def guess_document_type(filename: str, content: str) -> str:
    """Guess document type from filename and content"""
    filename_lower = filename.lower()
    content_lower = content.lower()
    
    if 'architecture' in filename_lower or 'architecture' in content_lower:
        return 'architecture'
    elif 'guide' in filename_lower or 'tutorial' in content_lower:
        return 'guide'
    elif 'spec' in filename_lower or 'specification' in content_lower:
        return 'spec'
    elif 'proposal' in filename_lower:
        return 'spec'
    elif 'readme' in filename_lower:
        return 'reference'
    elif 'notes' in filename_lower or 'meeting' in filename_lower:
        return 'notes'
    elif 'design' in filename_lower:
        return 'design'
    elif '.png' in filename_lower or '.jpg' in filename_lower or '.svg' in filename_lower:
        return 'diagram'
    else:
        return 'other'


def main():
    print("=" * 80)
    print("FEATURE DOCUMENT AUTO-DISCOVERY")
    print("=" * 80)
    print(f"Scanning: {DOCS_FOLDER}")
    print()
    
    if not DOCS_FOLDER.exists():
        print(f"❌ Docs folder not found: {DOCS_FOLDER}")
        return
    
    # Find all markdown files
    md_files = list(DOCS_FOLDER.rglob('*.md'))
    print(f"📄 Found {len(md_files)} markdown files")
    print()
    
    # Get all features
    features = ComponentRegistry.objects.all()
    print(f"🎯 Found {features.count()} features in registry")
    print()
    
    linked_count = 0
    skipped_count = 0
    
    for md_file in md_files:
        # Skip backup files
        if '.backup' in md_file.name or md_file.name.startswith('_'):
            continue
        
        try:
            # Read file
            content = md_file.read_text(encoding='utf-8')
            
            # Get relative path from project root
            rel_path = str(md_file.relative_to(PROJECT_ROOT))
            
            # Extract metadata
            title = extract_doc_title(content, md_file.name)
            word_count = estimate_word_count(content)
            doc_type = guess_document_type(md_file.name, content)
            keywords = extract_keywords_from_content(content)
            
            if not keywords:
                print(f"⏭️  SKIP: {md_file.name} (no matching keywords)")
                skipped_count += 1
                continue
            
            # Find matching features
            matched_features = []
            for feature in features:
                feature_name_lower = feature.name.lower()
                feature_desc_lower = feature.description.lower() if feature.description else ''
                
                # Check if any keyword matches feature name or description
                for keyword in keywords:
                    if keyword in feature_name_lower or keyword in feature_desc_lower:
                        matched_features.append(feature)
                        break
            
            if not matched_features:
                print(f"⏭️  SKIP: {md_file.name} (no matching features for keywords: {', '.join(keywords)})")
                skipped_count += 1
                continue
            
            # Link to each matching feature
            for feature in matched_features:
                # Check if already linked
                if FeatureDocument.objects.filter(feature=feature, file_path=rel_path).exists():
                    continue
                
                # Create document link
                doc = FeatureDocument.objects.create(
                    feature=feature,
                    title=title,
                    file_path=rel_path,
                    document_type=doc_type,
                    description=f"Auto-discovered from {md_file.name}",
                    is_auto_discovered=True,
                    file_size=md_file.stat().st_size,
                    word_count=word_count,
                    last_modified=None,  # Can add later if needed
                )
                
                print(f"✅ LINKED: {md_file.name} → {feature.name}")
                linked_count += 1
        
        except Exception as e:
            print(f"❌ ERROR processing {md_file.name}: {e}")
            continue
    
    print()
    print("=" * 80)
    print(f"DONE: {linked_count} documents linked, {skipped_count} skipped")
    print("=" * 80)


if __name__ == "__main__":
    main()
