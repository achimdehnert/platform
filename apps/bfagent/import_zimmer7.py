#!/usr/bin/env python
"""
Import 'Zimmer 7' - Complete Psychothriller with manuscript chapters
and publisher materials (Klappentext, Exposé, Fortsetzungsideen)
"""
import os
import re
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from pathlib import Path
from django.contrib.auth import get_user_model
from apps.bfagent.models import BookProjects, BookTypes
from apps.writing_hub.models import Chapter

User = get_user_model()
BOOK_DIR = Path('books/zimmer7')


def parse_expose():
    """Parse the exposé to extract book metadata"""
    filepath = BOOK_DIR / 'Verlagsmaterial' / '02_Expose.md'
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract metadata from exposé
    metadata = {
        'title': 'Zimmer 7',
        'genre': 'Psychothriller',
        'target_word_count': 47000,
        'target_audience': 'Erwachsene, 25-55 Jahre, Leser von Spannungsliteratur',
        'status': 'draft',
    }
    
    # Extract description from Kurzinhalt
    pitch_match = re.search(r'## 2\. KURZINHALT \(Pitch\)\n\n(.+?)\n\n---', content, re.DOTALL)
    if pitch_match:
        metadata['tagline'] = pitch_match.group(1).strip()
    
    # Extract full description from Inhaltsangabe
    desc_match = re.search(r'### Ausgangssituation\n\n(.+?)### Entwicklung', content, re.DOTALL)
    if desc_match:
        metadata['description'] = desc_match.group(1).strip()
    
    return metadata


def parse_klappentext():
    """Parse the Klappentext for marketing text"""
    filepath = BOOK_DIR / 'Verlagsmaterial' / '01_Klappentext.md'
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return content


def get_manuscript_chapters():
    """Get all manuscript chapters"""
    manuscript_dir = BOOK_DIR / 'manuskript'
    
    chapters = []
    for filepath in sorted(manuscript_dir.glob('Kapitel_*.md')):
        # Extract chapter number from filename
        match = re.match(r'Kapitel_(\d+)_(.+)\.md', filepath.name)
        if match:
            chapter_num = int(match.group(1))
            chapter_slug = match.group(2)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract title from first line
            lines = content.split('\n')
            title_line = lines[0] if lines else ''
            title = title_line.replace('# KAPITEL ', '').replace('# Kapitel ', '').strip()
            title = re.sub(r'^\d+:\s*', '', title)  # Remove "1: " prefix if present
            
            # Get content without the header
            chapter_content = '\n'.join(lines[1:]).strip()
            
            chapters.append({
                'number': chapter_num,
                'title': title,
                'content': chapter_content,
                'word_count': len(chapter_content.split()),
            })
    
    return chapters


def create_book_project(metadata, klappentext):
    """Create BookProject for Zimmer 7"""
    print(f"Creating BookProject: {metadata['title']}...")
    
    user = User.objects.first()
    book_type = BookTypes.objects.first()
    
    # Check if exists
    try:
        project = BookProjects.objects.get(title=metadata['title'])
        print(f"  Found existing project: {project.title}")
        return project
    except BookProjects.DoesNotExist:
        pass
    
    # Full description combining tagline and description
    full_description = f"{metadata.get('tagline', '')}\n\n{metadata.get('description', '')}"
    
    project = BookProjects(
        title=metadata['title'],
        description=full_description[:2000],  # Limit to field size
        genre=metadata['genre'],
        target_audience=metadata['target_audience'],
        status=metadata['status'],
        user=user,
        book_type=book_type,
        target_word_count=metadata['target_word_count'],
    )
    project.save()
    
    print(f"  Created BookProject: {project.title}")
    return project


def create_chapters(project, chapters_data):
    """Create chapters from manuscript"""
    print(f"Creating {len(chapters_data)} chapters...")
    
    total_words = 0
    for ch in chapters_data:
        chapter, created = Chapter.objects.update_or_create(
            project=project,
            chapter_number=ch['number'],
            defaults={
                'title': ch['title'],
                'content': ch['content'],
                'status': 'draft',
                'word_count': ch['word_count'],
            }
        )
        total_words += ch['word_count']
        
        action = "Created" if created else "Updated"
        print(f"  {action} Chapter {ch['number']}: {ch['title']} ({ch['word_count']} words)")
    
    # Update project word count
    project.current_word_count = total_words
    project.save()
    
    return total_words


def main():
    print("=" * 60)
    print("Import: Zimmer 7 (Psychothriller)")
    print("=" * 60)
    
    # Parse metadata
    print("\nParsing Verlagsmaterial...")
    metadata = parse_expose()
    klappentext = parse_klappentext()
    print(f"  Title: {metadata['title']}")
    print(f"  Genre: {metadata['genre']}")
    print(f"  Target: {metadata['target_word_count']} words")
    
    # Get chapters
    print("\nParsing Manuskript...")
    chapters = get_manuscript_chapters()
    print(f"  Found {len(chapters)} chapters")
    
    # Create project
    print()
    project = create_book_project(metadata, klappentext)
    
    # Create chapters
    print()
    total_words = create_chapters(project, chapters)
    
    print("\n" + "=" * 60)
    print("Import completed!")
    print(f"  Total: {len(chapters)} chapters, {total_words:,} words")
    print(f"  View: http://localhost:8000/writing/projects/{project.id}/")
    print("=" * 60)


if __name__ == '__main__':
    main()
