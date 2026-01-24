"""
Writing Hub Import Service
Centralized import logic with update/merge capabilities
"""
import os
import tempfile
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from django.db import models

from apps.bfagent.models import BookProjects, BookChapters, Characters, Worlds


@dataclass
class ImportStats:
    """Statistics from an import operation"""
    chapters_created: int = 0
    chapters_updated: int = 0
    characters_created: int = 0
    characters_updated: int = 0
    locations_created: int = 0
    locations_updated: int = 0
    
    @property
    def total_created(self) -> int:
        return self.chapters_created + self.characters_created + self.locations_created
    
    @property
    def total_updated(self) -> int:
        return self.chapters_updated + self.characters_updated + self.locations_updated
    
    def summary(self) -> str:
        parts = []
        if self.chapters_created:
            parts.append(f"+{self.chapters_created} Kapitel")
        if self.chapters_updated:
            parts.append(f"~{self.chapters_updated} Kapitel aktualisiert")
        if self.characters_created:
            parts.append(f"+{self.characters_created} Charaktere")
        if self.characters_updated:
            parts.append(f"~{self.characters_updated} Charaktere aktualisiert")
        if self.locations_created:
            parts.append(f"+{self.locations_created} Locations")
        if self.locations_updated:
            parts.append(f"~{self.locations_updated} Locations aktualisiert")
        return ' • '.join(parts) if parts else "Keine Änderungen"


class ImportService:
    """
    Centralized service for importing data into Writing Hub projects.
    
    Supports:
    - Creating new records
    - Updating existing records (replacing placeholder text)
    - Merging differences on re-import
    """
    
    # Placeholder patterns to detect and replace
    PLACEHOLDER_PATTERNS = [
        'Aus Import ergänzt',
        'Automatisch aus Import ergänzt',
        'Importiert aus:',
        'Location aus Import',
        'Extrahiert aus Import',
    ]
    
    def __init__(self, project: BookProjects):
        self.project = project
        self.stats = ImportStats()
    
    @staticmethod
    def parse_file(file_path: str):
        """Parse a file and return analysis results"""
        from apps.writing_hub.management.commands.reengineer_book import BookReengineer
        reeng = BookReengineer(file_path, verbose=False)
        return reeng.analyze()
    
    @staticmethod
    def parse_uploaded_file(uploaded_file):
        """Parse an uploaded file and return analysis results"""
        from apps.writing_hub.management.commands.reengineer_book import BookReengineer
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk.decode('utf-8'))
            temp_path = f.name
        
        try:
            reeng = BookReengineer(temp_path, verbose=False)
            return reeng.analyze()
        finally:
            os.unlink(temp_path)
    
    def is_placeholder(self, text: str) -> bool:
        """Check if text is a placeholder that should be replaced"""
        if not text:
            return True
        text_lower = text.lower().strip()
        for pattern in self.PLACEHOLDER_PATTERNS:
            if pattern.lower() in text_lower:
                return True
        return len(text.strip()) < 10  # Very short text is also considered placeholder
    
    def import_chapter(self, chapter_data: dict) -> Tuple[Optional[BookChapters], str]:
        """
        Import or update a chapter.
        Returns (chapter, action) where action is 'created', 'updated', or 'skipped'
        """
        title = chapter_data.get('title', '')
        if not title:
            return None, 'skipped'
        
        # Try to find existing chapter by title
        existing = BookChapters.objects.filter(project=self.project, title=title).first()
        
        if existing:
            # Check if we should update (existing has placeholder/empty data)
            updated = False
            
            # Update notes if current is placeholder
            new_notes = self._build_chapter_notes(chapter_data)
            if self.is_placeholder(existing.notes) and new_notes:
                existing.notes = new_notes
                updated = True
            
            if updated:
                existing.save()
                self.stats.chapters_updated += 1
                return existing, 'updated'
            return existing, 'skipped'
        
        # Create new chapter
        max_num = BookChapters.objects.filter(project=self.project).aggregate(
            max_num=models.Max('chapter_number')
        )['max_num'] or 0
        
        chapter = BookChapters.objects.create(
            project=self.project,
            title=title,
            chapter_number=chapter_data.get('number', max_num + 1),
            content='',
            status='outlined' if chapter_data.get('status') == 'planned' else 'draft',
            notes=self._build_chapter_notes(chapter_data),
        )
        self.stats.chapters_created += 1
        return chapter, 'created'
    
    def _build_chapter_notes(self, chapter_data: dict) -> str:
        """Build notes string from chapter data"""
        parts = []
        if chapter_data.get('pov'):
            parts.append(f"POV: {chapter_data['pov']}")
        if chapter_data.get('location'):
            parts.append(f"Ort: {chapter_data['location']}")
        if chapter_data.get('beats'):
            parts.append(f"Beats: {', '.join(chapter_data['beats'][:5])}")
        return '\n'.join(parts)
    
    def import_character(self, char_data: dict) -> Tuple[Optional[Characters], str]:
        """
        Import or update a character.
        Returns (character, action) where action is 'created', 'updated', or 'skipped'
        """
        name = char_data.get('name', '')
        if not name:
            return None, 'skipped'
        
        # Try to find existing character by name
        existing = Characters.objects.filter(project=self.project, name=name).first()
        
        if existing:
            # ALWAYS update with new data if available (merge new data into existing)
            updated = False
            
            # Update role if new data is better
            if char_data.get('role') and char_data['role'] != 'unknown':
                if self.is_placeholder(existing.role) or existing.role == 'Importiert':
                    existing.role = char_data['role']
                    updated = True
            
            # Update description with new data
            new_desc = self._build_character_description(char_data)
            if new_desc and (self.is_placeholder(existing.description) or len(new_desc) > len(existing.description or '')):
                existing.description = new_desc
                updated = True
            
            # Update age if empty
            if char_data.get('age') and not existing.age:
                existing.age = char_data['age']
                updated = True
            
            # Update background - merge if both exist
            if char_data.get('background'):
                if self.is_placeholder(existing.background):
                    existing.background = char_data['background']
                    updated = True
                elif char_data['background'] not in (existing.background or ''):
                    existing.background = f"{existing.background}\n\n{char_data['background']}"
                    updated = True
            
            # Update motivation
            if char_data.get('motivation'):
                if self.is_placeholder(existing.motivation):
                    existing.motivation = char_data['motivation']
                    updated = True
            
            # Update arc
            if char_data.get('arc'):
                if self.is_placeholder(existing.arc):
                    existing.arc = char_data['arc']
                    updated = True
            
            if updated:
                existing.save()
                self.stats.characters_updated += 1
                return existing, 'updated'
            return existing, 'skipped'
        
        # Create new character
        character = Characters.objects.create(
            project=self.project,
            name=name,
            role=char_data.get('role') or 'Importiert',
            age=char_data.get('age') or '',
            background=char_data.get('background') or '',
            motivation=char_data.get('motivation') or '',
            arc=char_data.get('arc') or '',
            description=self._build_character_description(char_data),
        )
        self.stats.characters_created += 1
        return character, 'created'
    
    def _build_character_description(self, char_data: dict) -> str:
        """Build description string from character data"""
        parts = []
        if char_data.get('background'):
            parts.append(char_data['background'])
        if char_data.get('motivation'):
            parts.append(f"Motivation: {char_data['motivation']}")
        if char_data.get('traits'):
            parts.append(f"Eigenschaften: {', '.join(char_data['traits'][:5])}")
        return '\n'.join(parts) if parts else ''
    
    def import_location(self, loc_data: dict) -> Tuple[Optional[Worlds], str]:
        """
        Import or update a location/world.
        Returns (world, action) where action is 'created', 'updated', or 'skipped'
        """
        name = loc_data.get('name', '')
        if not name:
            return None, 'skipped'
        
        # Try to find existing world by name
        existing = Worlds.objects.filter(project=self.project, name=name).first()
        
        if existing:
            # ALWAYS update with new data if available (merge new data into existing)
            updated = False
            
            new_desc = self._build_location_description(loc_data)
            if new_desc:
                if self.is_placeholder(existing.description):
                    existing.description = new_desc
                    updated = True
                elif len(new_desc) > len(existing.description or '') and new_desc not in (existing.description or ''):
                    # New description is longer and contains new info - merge it
                    existing.description = f"{existing.description}\n\n{new_desc}"
                    updated = True
            
            if updated:
                existing.save()
                self.stats.locations_updated += 1
                return existing, 'updated'
            return existing, 'skipped'
        
        # Create new world
        world = Worlds.objects.create(
            project=self.project,
            name=name,
            description=self._build_location_description(loc_data),
        )
        self.stats.locations_created += 1
        return world, 'created'
    
    def _build_location_description(self, loc_data: dict) -> str:
        """Build description string from location data"""
        desc = loc_data.get('description') or ''
        if loc_data.get('features'):
            if desc:
                desc += '\n\n'
            desc += f"Merkmale: {', '.join(loc_data['features'][:5])}"
        return desc
    
    def import_from_analysis(self, analysis: dict, 
                              selected_chapters: List[int] = None,
                              selected_characters: List[str] = None,
                              selected_locations: List[str] = None) -> ImportStats:
        """
        Import data from a parsed analysis result.
        
        Args:
            analysis: Parsed analysis dict with chapters, characters, locations
            selected_chapters: List of chapter indices to import (None = all)
            selected_characters: List of character names to import (None = all)
            selected_locations: List of location names to import (None = all)
        
        Returns:
            ImportStats with counts of created/updated records
        """
        # Import chapters
        chapters = analysis.get('chapters', [])
        for idx, ch_data in enumerate(chapters):
            if selected_chapters is None or idx in selected_chapters:
                self.import_chapter(ch_data)
        
        # Import characters
        characters = analysis.get('characters', [])
        for char_data in characters:
            char_name = char_data.get('name') if isinstance(char_data, dict) else char_data
            if selected_characters is None or char_name in selected_characters:
                if isinstance(char_data, dict):
                    self.import_character(char_data)
                else:
                    self.import_character({'name': char_data})
        
        # Import locations
        locations = analysis.get('locations', [])
        for loc_data in locations:
            loc_name = loc_data.get('name') if isinstance(loc_data, dict) else loc_data
            if selected_locations is None or loc_name in selected_locations:
                if isinstance(loc_data, dict):
                    self.import_location(loc_data)
                else:
                    self.import_location({'name': loc_data})
        
        return self.stats
