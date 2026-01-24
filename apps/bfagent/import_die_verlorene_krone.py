#!/usr/bin/env python
"""
Import 'Die verlorene Krone' from books/generated folder
Creates BookProject and 3 Chapters with full content
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
BOOK_DIR = Path('books/generated/Die_verlorene_Krone')


def parse_complete_file():
    """Parse the complete markdown file to extract chapters"""
    filepath = BOOK_DIR / 'Die_verlorene_Krone_complete_20251016_122521.md'
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract metadata
    lines = content.split('\n')
    title = lines[0].replace('# ', '').strip()
    
    # Find genre
    genre = 'Fantasy'
    for line in lines[:10]:
        if line.startswith('**Genre:**'):
            genre = line.replace('**Genre:**', '').strip()
            break
    
    # Split by chapter markers
    chapter_pattern = r'# Chapter (\d+): (.+?)(?=\n# Chapter |\Z)'
    chapters_raw = re.split(r'\n# Chapter \d+:', content)
    
    # Better approach: split by "---" and "# Chapter"
    chapters = []
    
    # Find chapter sections
    chapter_starts = []
    for i, line in enumerate(lines):
        if line.startswith('# Chapter '):
            chapter_starts.append(i)
    
    for idx, start_line in enumerate(chapter_starts):
        # Get chapter header
        header = lines[start_line]
        match = re.match(r'# Chapter (\d+): (.+)', header)
        if match:
            chapter_num = int(match.group(1))
            chapter_title = match.group(2).strip()
            
            # Get content until next chapter or end
            if idx + 1 < len(chapter_starts):
                end_line = chapter_starts[idx + 1]
            else:
                end_line = len(lines)
            
            # Get chapter content (skip the header line and any duplicate)
            chapter_content_lines = []
            for i in range(start_line + 1, end_line):
                line = lines[i]
                # Skip duplicate chapter headers and separators
                if line.startswith('# Kapitel ') or line == '---':
                    continue
                chapter_content_lines.append(line)
            
            chapter_content = '\n'.join(chapter_content_lines).strip()
            
            chapters.append({
                'number': chapter_num,
                'title': chapter_title,
                'content': chapter_content,
            })
    
    return {
        'title': title,
        'genre': genre,
        'chapters': chapters,
    }


def create_book_project(book_data):
    """Create BookProject for Die verlorene Krone"""
    print(f"Creating BookProject: {book_data['title']}...")
    
    user = User.objects.first()
    book_type = BookTypes.objects.first()
    
    # Check if exists
    try:
        project = BookProjects.objects.get(title=book_data['title'])
        print(f"  Found existing project: {project.title}")
        return project
    except BookProjects.DoesNotExist:
        pass
    
    # Calculate word count
    total_words = sum(len(ch['content'].split()) for ch in book_data['chapters'])
    
    project = BookProjects(
        title=book_data['title'],
        description=f"Ein Fantasy-Abenteuer über einen jungen Prinzen, der eine magische Krone findet und lernen muss, ihre Macht zu kontrollieren, um sein Königreich vor dunklen Mächten zu retten.",
        genre=book_data['genre'],
        target_audience='Jugendliche und Erwachsene',
        status='draft',
        user=user,
        book_type=book_type,
        target_word_count=total_words + 5000,  # Some buffer
        current_word_count=total_words,
    )
    project.save()
    
    print(f"  Created BookProject: {project.title} ({total_words} words)")
    return project


def create_chapters(project, chapters_data):
    """Create chapters from parsed data"""
    print(f"Creating {len(chapters_data)} chapters...")
    
    for ch in chapters_data:
        word_count = len(ch['content'].split())
        
        chapter, created = Chapter.objects.update_or_create(
            project=project,
            chapter_number=ch['number'],
            defaults={
                'title': ch['title'],
                'content': ch['content'],
                'status': 'draft',
                'word_count': word_count,
            }
        )
        
        action = "Created" if created else "Updated"
        print(f"  {action} Chapter {ch['number']}: {ch['title']} ({word_count} words)")


def main():
    print("=" * 60)
    print("Import: Die verlorene Krone")
    print("=" * 60)
    
    # Parse the book file
    print("\nParsing book file...")
    book_data = parse_complete_file()
    print(f"  Title: {book_data['title']}")
    print(f"  Genre: {book_data['genre']}")
    print(f"  Chapters: {len(book_data['chapters'])}")
    
    # Create project
    print()
    project = create_book_project(book_data)
    
    # Create chapters
    print()
    create_chapters(project, book_data['chapters'])
    
    print("\n" + "=" * 60)
    print("Import completed!")
    print(f"View project at: http://localhost:8000/writing/projects/{project.id}/")
    print("=" * 60)


if __name__ == '__main__':
    main()
