"""
Universal Book Importer Management Command

Imports book projects from various folder structures:
- Manuscripts (Markdown chapters)
- Publisher materials (Exposé, Klappentext)
- Structure files (YAML)
- Character/World data

Usage:
    python manage.py import_book books/zimmer7/
    python manage.py import_book books/zimmer7/ --dry-run
    python manage.py import_book books/zimmer7/ --framework "Three-Act"
"""

import os
import re
import yaml
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from apps.bfagent.models import BookProjects, BookTypes
from apps.writing_hub.models import Chapter


User = get_user_model()


class BookImporter:
    """Universal book project importer"""
    
    def __init__(self, path, user=None, dry_run=False, verbose=False, force_update=False):
        self.path = Path(path)
        self.user = user or User.objects.first()
        self.dry_run = dry_run
        self.verbose = verbose
        self.force_update = force_update
        self.results = {
            'project': None,
            'chapters': [],
            'word_count': 0,
            'errors': [],
            'warnings': [],
        }
    
    def log(self, message, level='info'):
        """Log message based on verbosity"""
        # Always show in dry-run mode or verbose mode, or for warnings/errors
        if self.verbose or self.dry_run or level in ['error', 'warning', 'success']:
            prefix = {'info': '  ', 'warning': '⚠️', 'error': '❌', 'success': '✅'}
            print(f"{prefix.get(level, '  ')} {message}")
    
    def _clean_content(self, content):
        """Clean up markdown content - reduce excessive empty lines"""
        import re
        # Replace 3+ consecutive newlines with 2 newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        # Clean up spaces before newlines
        content = re.sub(r' +\n', '\n', content)
        # Remove trailing whitespace
        content = content.strip()
        return content
    
    def discover_structure(self):
        """Discover project structure and available files"""
        structure = {
            'has_project_yaml': (self.path / 'project.yaml').exists(),
            'has_manuskript': (self.path / 'manuskript').exists(),
            'has_verlagsmaterial': (self.path / 'Verlagsmaterial').exists(),
            'has_chapters_yaml': False,
            'has_structure_yaml': False,
            'manuscript_files': [],
            'yaml_files': [],
        }
        
        # Find manuscript files
        if structure['has_manuskript']:
            structure['manuscript_files'] = sorted(
                (self.path / 'manuskript').glob('*.md')
            )
        
        # Find YAML files
        structure['yaml_files'] = list(self.path.glob('*.yaml'))
        structure['has_chapters_yaml'] = any(
            'chapter' in f.name.lower() for f in structure['yaml_files']
        )
        structure['has_structure_yaml'] = any(
            'structure' in f.name.lower() for f in structure['yaml_files']
        )
        
        return structure
    
    def extract_metadata(self, structure):
        """Extract project metadata from available sources"""
        metadata = {
            # Convert folder name to proper title (zimmer7 -> Zimmer 7)
            'title': re.sub(r'([a-z])(\d)', r'\1 \2', self.path.name).replace('_', ' ').title(),
            'genre': 'Fiction',
            'description': '',
            'target_word_count': 50000,
            'target_audience': '',
            'tagline': '',
        }
        
        # Try project.yaml first
        if structure['has_project_yaml']:
            try:
                with open(self.path / 'project.yaml', 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if 'project' in config:
                        proj = config['project']
                        metadata.update({
                            'title': proj.get('title', metadata['title']),
                            'genre': proj.get('genre', metadata['genre']),
                            'target_word_count': proj.get('target_word_count', 50000),
                        })
                        if 'audience' in proj:
                            metadata['target_audience'] = proj['audience'].get('description', '')
            except Exception as e:
                self.results['warnings'].append(f"Could not parse project.yaml: {e}")
        
        # Try Exposé
        if structure['has_verlagsmaterial']:
            expose_path = self.path / 'Verlagsmaterial' / '02_Expose.md'
            if expose_path.exists():
                metadata.update(self._parse_expose(expose_path))
            
            # Try Klappentext
            blurb_path = self.path / 'Verlagsmaterial' / '01_Klappentext.md'
            if blurb_path.exists():
                metadata['tagline'] = self._extract_tagline(blurb_path)
        
        return metadata
    
    def _parse_expose(self, filepath):
        """Parse exposé for metadata"""
        result = {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract genre
            genre_match = re.search(r'\*\*Genre[:\*]*\s*(.+?)(?:\n|\|)', content)
            if genre_match:
                result['genre'] = genre_match.group(1).strip().strip('*')
            
            # Extract word count target
            word_match = re.search(r'ca\.\s*([\d.]+)\s*Wörter', content)
            if word_match:
                result['target_word_count'] = int(word_match.group(1).replace('.', ''))
            
            # Extract pitch/description
            pitch_match = re.search(
                r'## 2\. KURZINHALT.*?\n\n(.+?)\n\n---', 
                content, re.DOTALL
            )
            if pitch_match:
                result['description'] = pitch_match.group(1).strip()
            
        except Exception as e:
            self.results['warnings'].append(f"Could not parse exposé: {e}")
        
        return result
    
    def _extract_tagline(self, filepath):
        """Extract tagline from Klappentext"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for bold tagline
            match = re.search(r'\*\*(.+?)\*\*', content)
            if match:
                return match.group(1).strip()
        except:
            pass
        return ''
    
    def parse_chapters(self, structure):
        """Parse chapter files"""
        chapters = []
        
        if structure['manuscript_files']:
            # Parse markdown manuscripts
            for filepath in structure['manuscript_files']:
                chapter = self._parse_markdown_chapter(filepath)
                if chapter:
                    chapters.append(chapter)
        
        elif structure['has_chapters_yaml']:
            # Parse YAML chapter definitions
            for yaml_file in structure['yaml_files']:
                if 'chapter' in yaml_file.name.lower():
                    chapters.extend(self._parse_yaml_chapters(yaml_file))
        
        return sorted(chapters, key=lambda c: c['number'])
    
    def _parse_markdown_chapter(self, filepath):
        """Parse a markdown chapter file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract chapter number from filename
            match = re.match(r'Kapitel_(\d+)_(.+)\.md', filepath.name)
            if not match:
                # Try alternative patterns
                match = re.match(r'chapter_?(\d+).*\.md', filepath.name, re.I)
            
            if match:
                number = int(match.group(1))
                slug = match.group(2) if len(match.groups()) > 1 else ''
            else:
                # Fallback: use file order
                number = int(re.search(r'\d+', filepath.name).group())
                slug = filepath.stem
            
            # Extract title from content
            lines = content.split('\n')
            title = slug.replace('_', ' ').title()
            
            for line in lines[:5]:
                if line.startswith('# '):
                    title = line.replace('# ', '').strip()
                    title = re.sub(r'^(KAPITEL|Kapitel|Chapter)\s*\d+:\s*', '', title)
                    break
            
            # Get content without header
            content_lines = []
            skip_header = True
            for line in lines:
                if skip_header and line.startswith('#'):
                    continue
                skip_header = False
                content_lines.append(line)
            
            chapter_content = '\n'.join(content_lines).strip()
            
            # Clean up excessive empty lines (more than 2 consecutive)
            chapter_content = self._clean_content(chapter_content)
            
            return {
                'number': number,
                'title': title,
                'content': chapter_content,
                'word_count': len(chapter_content.split()),
                'source': str(filepath),
            }
            
        except Exception as e:
            self.results['errors'].append(f"Error parsing {filepath}: {e}")
            return None
    
    def _parse_yaml_chapters(self, filepath):
        """Parse chapters from YAML structure file"""
        chapters = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Handle various YAML structures
            chapter_list = data.get('chapters', data.get('book_1', {}).get('chapters', []))
            
            for i, ch in enumerate(chapter_list, 1):
                if isinstance(ch, dict):
                    chapters.append({
                        'number': ch.get('number', i),
                        'title': ch.get('title', f'Chapter {i}'),
                        'content': ch.get('content', ''),
                        'word_count': ch.get('word_count', 0),
                        'source': str(filepath),
                    })
                elif isinstance(ch, str):
                    chapters.append({
                        'number': i,
                        'title': ch,
                        'content': '',
                        'word_count': 0,
                        'source': str(filepath),
                    })
                    
        except Exception as e:
            self.results['errors'].append(f"Error parsing YAML {filepath}: {e}")
        
        return chapters
    
    def create_project(self, metadata):
        """Create or update BookProject"""
        book_type = BookTypes.objects.first()
        existing_project = None
        
        # Check if project exists
        try:
            existing_project = BookProjects.objects.get(title=metadata['title'])
        except BookProjects.DoesNotExist:
            pass
        
        if self.dry_run:
            if existing_project:
                self.log(f"[DRY-RUN] Project EXISTS: {metadata['title']} (ID: {existing_project.id})", 'warning')
                self.log(f"[DRY-RUN] Would UPDATE existing project and chapters")
            else:
                self.log(f"[DRY-RUN] Would CREATE new project: {metadata['title']}")
            return None
        
        if existing_project:
            if not self.force_update:
                self.log(f"Project already exists: {existing_project.title} (ID: {existing_project.id})", 'warning')
                self.log(f"Use --force-update to overwrite existing content", 'warning')
                self.results['warnings'].append(f"Project exists, use --force-update to overwrite")
            project = existing_project
            self.log(f"Updating existing project: {project.title} (ID: {project.id})")
        else:
            project = BookProjects(
                title=metadata['title'],
                user=self.user,
                book_type=book_type,
            )
            self.log(f"Creating new project: {metadata['title']}")
        
        # Update fields
        project.genre = metadata.get('genre', 'Fiction')
        project.description = metadata.get('description', '')[:2000]
        project.target_audience = metadata.get('target_audience', '')
        project.target_word_count = metadata.get('target_word_count', 50000)
        if not existing_project:
            project.status = 'draft'
        
        project.save()
        self.results['project'] = project
        action = "Updated" if existing_project else "Created"
        self.log(f"{action} project: {project.title} (ID: {project.id})", 'success')
        
        return project
    
    def create_chapters(self, project, chapters):
        """Create or update chapters"""
        if self.dry_run:
            total_words = 0
            for ch in chapters:
                self.log(f"[DRY-RUN] Chapter {ch['number']}: {ch['title']} ({ch['word_count']} words)")
                total_words += ch['word_count']
            self.results['word_count'] = total_words
            self.log(f"[DRY-RUN] Total: {len(chapters)} chapters, {total_words:,} words")
            return
        
        total_words = 0
        for ch in chapters:
            chapter, created = Chapter.objects.update_or_create(
                project=project,
                chapter_number=ch['number'],
                defaults={
                    'title': ch['title'],
                    'content': ch['content'],
                    'word_count': ch['word_count'],
                    'status': 'draft',
                }
            )
            total_words += ch['word_count']
            self.results['chapters'].append(chapter)
            
            action = "Created" if created else "Updated"
            self.log(f"{action} Chapter {ch['number']}: {ch['title']} ({ch['word_count']} words)")
        
        # Update project word count
        project.current_word_count = total_words
        project.save()
        self.results['word_count'] = total_words
    
    def import_all(self):
        """Run complete import pipeline"""
        self.log(f"Importing from: {self.path}")
        
        # Phase 1: Discovery
        structure = self.discover_structure()
        self.log(f"Found: {len(structure['manuscript_files'])} manuscripts, "
                f"{len(structure['yaml_files'])} YAML files")
        
        # Phase 2: Metadata
        metadata = self.extract_metadata(structure)
        self.log(f"Title: {metadata['title']}, Genre: {metadata['genre']}")
        
        # Phase 3: Chapters
        chapters = self.parse_chapters(structure)
        self.log(f"Parsed {len(chapters)} chapters")
        
        # Phase 4: Create
        project = self.create_project(metadata)
        if project or self.dry_run:
            self.create_chapters(project, chapters)
        
        return self.results


class Command(BaseCommand):
    help = 'Import a book project from a folder structure'
    
    def add_arguments(self, parser):
        parser.add_argument('path', type=str, help='Path to book project folder')
        parser.add_argument('--user', type=str, help='Username for project owner')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be imported')
        parser.add_argument('--verbose-import', action='store_true', help='Verbose output')
        parser.add_argument('--force-update', action='store_true', help='Force update if project exists')
        parser.add_argument('--framework', type=str, help='Framework to assign')
    
    def handle(self, *args, **options):
        path = options['path']
        
        if not os.path.exists(path):
            raise CommandError(f"Path does not exist: {path}")
        
        # Get user
        user = None
        if options['user']:
            try:
                user = User.objects.get(username=options['user'])
            except User.DoesNotExist:
                raise CommandError(f"User not found: {options['user']}")
        
        # Run importer
        importer = BookImporter(
            path=path,
            user=user,
            dry_run=options['dry_run'],
            verbose=options['verbose_import'],
            force_update=options['force_update'],
        )
        
        self.stdout.write(self.style.NOTICE('=' * 60))
        self.stdout.write(self.style.NOTICE('Universal Book Importer'))
        self.stdout.write(self.style.NOTICE('=' * 60))
        
        results = importer.import_all()
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('=' * 60))
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes made'))
        else:
            self.stdout.write(self.style.SUCCESS('Import completed!'))
            if results['project']:
                self.stdout.write(f"  Project: {results['project'].title} (ID: {results['project'].id})")
                self.stdout.write(f"  Chapters: {len(results['chapters'])}")
                self.stdout.write(f"  Words: {results['word_count']:,}")
                self.stdout.write(f"  URL: http://localhost:8000/writing/projects/{results['project'].id}/")
        
        if results['warnings']:
            self.stdout.write(self.style.WARNING('\nWarnings:'))
            for w in results['warnings']:
                self.stdout.write(f"  ⚠️ {w}")
        
        if results['errors']:
            self.stdout.write(self.style.ERROR('\nErrors:'))
            for e in results['errors']:
                self.stdout.write(f"  ❌ {e}")
        
        self.stdout.write(self.style.NOTICE('=' * 60))
