"""
Book Reengineering Parser

Parses mixed manuscript files (text + meta-info + AI artifacts)
and extracts structured book project data.

Usage:
    python manage.py reengineer_book "path/to/manuscript.md" --analyze
    python manage.py reengineer_book "path/to/manuscript.md" --import
    python manage.py reengineer_book "path/to/manuscript.md" --output-dir output/
"""

import os
import re
import json
import yaml
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from django.core.management.base import BaseCommand, CommandError


@dataclass
class ChapterMeta:
    """Metadata for a single chapter"""
    number: int
    title: str
    content: str = ""
    word_count: int = 0
    status: str = "draft"
    pov: str = ""
    location: str = ""
    timeline: str = ""
    tension_level: int = 0
    emotional_tone: str = ""
    beats: List[str] = field(default_factory=list)
    established: List[str] = field(default_factory=list)
    foreshadowing: List[str] = field(default_factory=list)
    characters: List[str] = field(default_factory=list)
    key_objects: List[str] = field(default_factory=list)


@dataclass
class CharacterInfo:
    """Extracted character information"""
    name: str
    role: str = "unknown"
    first_appearance: int = 0
    mentions: int = 0
    traits: List[str] = field(default_factory=list)
    relationships: List[Dict] = field(default_factory=list)
    # Extended fields for character sheets
    age: str = ""
    occupation: str = ""
    background: str = ""
    motivation: str = ""
    arc: str = ""
    psychology: Dict = field(default_factory=dict)


@dataclass
class SubplotInfo:
    """Extracted subplot information"""
    name: str
    character: str = ""
    weight_percent: int = 0
    function: str = ""
    chapters: List[int] = field(default_factory=list)


@dataclass 
class StoryArc:
    """Story structure / arc information"""
    structure_type: str = ""  # e.g., "McFadden", "Three-Act", "Hero's Journey"
    parts: List[Dict] = field(default_factory=list)  # {name, chapters, beats}
    twists: List[Dict] = field(default_factory=list)
    themes: List[str] = field(default_factory=list)


@dataclass
class LocationInfo:
    """Extracted location information"""
    name: str
    description: str = ""
    chapters: List[int] = field(default_factory=list)
    features: List[str] = field(default_factory=list)


@dataclass
class ReengineeringResult:
    """Complete reengineering result"""
    title: str = ""
    genre: str = ""
    word_count: int = 0
    chapter_count: int = 0
    chapters: List[ChapterMeta] = field(default_factory=list)
    characters: List[CharacterInfo] = field(default_factory=list)
    locations: List[LocationInfo] = field(default_factory=list)
    beat_sheet: Dict = field(default_factory=dict)
    clean_manuscript: str = ""
    stats: Dict = field(default_factory=dict)
    # Extended fields for planning documents
    document_type: str = "manuscript"  # "manuscript", "planning", "mixed"
    subplots: List[SubplotInfo] = field(default_factory=list)
    story_arc: StoryArc = field(default_factory=StoryArc)
    sample_prose: Dict[int, str] = field(default_factory=dict)  # chapter -> prose
    working_titles: List[str] = field(default_factory=list)


class BookReengineer:
    """Main parser class for book reengineering"""
    
    # Regex patterns for parsing
    PATTERNS = {
        # Chapter detection
        'chapter_start': re.compile(r'^KAPITEL\s+(\d+):\s+(.+)$', re.MULTILINE),
        'chapter_end': re.compile(r'^Ende Kapitel\s+(\d+)$', re.MULTILINE),
        
        # Status markers
        'chapter_status': re.compile(r'^✅\s*Kapitel\s+(\d+)\s+fertig\s*\(~?([\d.,]+)\s*Wörter\)', re.MULTILINE),
        
        # Meta blocks
        'established_header': re.compile(r'^Etabliert:\s*$', re.MULTILINE),
        'foreshadowing_header': re.compile(r'^Foreshadowing:\s*$', re.MULTILINE),
        'beats_header': re.compile(r'^Beats:\s*$', re.MULTILINE),
        
        # Beat sheet fields
        'pov': re.compile(r'^POV:\s*(.+)$', re.MULTILINE),
        'location': re.compile(r'^Location:\s*(.+)$', re.MULTILINE),
        'timeline': re.compile(r'^(?:Timeline:\s*|Tag\s+(\d+).*)$', re.MULTILINE),
        'tension': re.compile(r'^Spannungslevel:\s*(\d+)', re.MULTILINE),
        'emotion': re.compile(r'^Emotion(?:al(?:er Ton)?)?:\s*(.+)$', re.MULTILINE),
        'characters_line': re.compile(r'^Charaktere:\s*(.+)$', re.MULTILINE),
        'key_objects': re.compile(r'^Schlüsselobjekte:\s*(.+)$', re.MULTILINE),
        
        # AI artifacts to remove
        'ai_prompt': re.compile(r'^Weiter mit Kapitel\s+\d+\?.*$', re.MULTILINE),
        'ai_response': re.compile(r'^Ja\s*(?:komplettes?)?\s*Kapitel.*$', re.MULTILINE),
        'ai_reasoning': re.compile(r'^Der Benutzer möchte.*$', re.MULTILINE),
        'ai_planning': re.compile(r'^Ich werde.*(?:schreiben|erstellen).*$', re.MULTILINE),
        'timestamp': re.compile(r'^\d+\.\s+(?:Jan|Feb|Mär|Apr|Mai|Jun|Jul|Aug|Sep|Okt|Nov|Dez)\.\s*$', re.MULTILINE),
        'orchestrated': re.compile(r'^Orchestrated.*$', re.MULTILINE),
        'word_target': re.compile(r'^~?\d+\s*Wörter,\s*\d+\s*Seiten.*$', re.MULTILINE),
        
        # Planning document patterns (NEW)
        'character_header': re.compile(r'^[🔮🩺🎭]\s*([A-ZÜÖÄ][A-ZÜÖÄ\s]+)\s*\((\w+)\)', re.MULTILINE),
        'subplot_header': re.compile(r'^SUBPLOT\s+([A-Z]):\s*(.+)$', re.MULTILINE),
        'teil_structure': re.compile(r'^TEIL\s+(\d+):\s*(.+?)\s*\((?:Kap(?:itel)?\.?\s*)?(\d+)-(\d+)\)', re.MULTILINE),
        'beat_table': re.compile(r'^Beat\|Inhalt', re.MULTILINE),
        'attribute_table': re.compile(r'^Attribut\|Detail', re.MULTILINE),
        'stilprobe': re.compile(r'^Stilprobe\s+Kapitel\s+(\d+):', re.MULTILINE),
        'subplot_weight': re.compile(r'^(?:├──|└──)?\s*(?:HAUPTPLOT|Subplot\s+[A-Z])\s*\([^)]+\):\s*(\d+)%', re.MULTILINE),
        'mcfadden': re.compile(r'McFadden', re.IGNORECASE),
        'working_titles': re.compile(r'^"([^"]+)"(?:\s*/\s*"([^"]+)")*', re.MULTILINE),
        'kapitel_outline': re.compile(r'^KAPITEL\s+(\d+):\s*"([^"]+)"\s*\((\d+)-(\d+)\s*Seiten\)', re.MULTILINE),
    }
    
    def __init__(self, filepath: str, verbose: bool = False):
        self.filepath = Path(filepath)
        self.verbose = verbose
        self.content = ""
        self.result = ReengineeringResult()
        
    def log(self, msg: str):
        if self.verbose:
            print(f"  {msg}")
    
    def load(self) -> str:
        """Load the manuscript file"""
        with open(self.filepath, 'r', encoding='utf-8') as f:
            self.content = f.read()
        return self.content
    
    def analyze(self) -> ReengineeringResult:
        """Run full analysis on the manuscript"""
        self.load()
        
        # Detect document type first
        self._detect_document_type()
        self.log(f"Document type: {self.result.document_type}")
        
        # Extract title from filename or first chapter
        self.result.title = self._extract_title()
        
        # Extract based on document type
        if self.result.document_type == "planning":
            self._extract_planning_document()
        else:
            # Standard manuscript processing
            self._extract_chapters()
            self._extract_meta_info()
            self._build_clean_manuscript()
        
        # Common extraction for all types
        self._extract_characters()
        self._extract_locations()
        self._extract_subplots()
        self._extract_story_arc()
        
        # Build beat sheet
        self._build_beat_sheet()
        
        # Calculate stats
        self._calculate_stats()
        
        return self.result
    
    def _detect_document_type(self):
        """Detect if this is a manuscript, planning doc, or mixed"""
        # Count indicators for each type
        manuscript_indicators = len(self.PATTERNS['chapter_start'].findall(self.content))
        planning_indicators = 0
        
        # Check for planning patterns
        if self.PATTERNS['mcfadden'].search(self.content):
            planning_indicators += 3
        if self.PATTERNS['teil_structure'].search(self.content):
            planning_indicators += 2
        if self.PATTERNS['character_header'].search(self.content):
            planning_indicators += 2
        if self.PATTERNS['subplot_header'].search(self.content):
            planning_indicators += 2
        if self.PATTERNS['beat_table'].search(self.content):
            planning_indicators += 1
        if self.PATTERNS['stilprobe'].search(self.content):
            planning_indicators += 1
        
        # Determine type
        if planning_indicators >= 5 and manuscript_indicators < 5:
            self.result.document_type = "planning"
        elif manuscript_indicators >= 5 and planning_indicators < 3:
            self.result.document_type = "manuscript"
        else:
            self.result.document_type = "mixed"
    
    def _extract_planning_document(self):
        """Extract data from a planning/development document"""
        # Extract chapter outlines (not full prose)
        self._extract_chapter_outlines()
        
        # Extract sample prose sections
        self._extract_sample_prose()
        
        # Extract working titles
        self._extract_working_titles()
    
    def _extract_chapter_outlines(self):
        """Extract chapter outlines from planning document"""
        # Look for KAPITEL X: "Title" (X-Y Seiten) pattern
        outlines = self.PATTERNS['kapitel_outline'].findall(self.content)
        
        for match in outlines:
            chapter_num = int(match[0])
            title = match[1]
            min_pages = int(match[2])
            max_pages = int(match[3])
            
            # Find beat-sheet for this chapter
            beats = self._extract_chapter_beats(chapter_num)
            
            chapter = ChapterMeta(
                number=chapter_num,
                title=title,
                content="",  # No prose content
                word_count=(min_pages + max_pages) // 2 * 250,  # Estimate
                status="planned",
                beats=beats,
            )
            self.result.chapters.append(chapter)
        
        # Also check for simpler pattern: KAPITEL X: Title
        simple_chapters = self.PATTERNS['chapter_start'].findall(self.content)
        existing_nums = {c.number for c in self.result.chapters}
        
        for match in simple_chapters:
            chapter_num = int(match[0])
            if chapter_num not in existing_nums:
                title = match[1].strip('"').strip()
                beats = self._extract_chapter_beats(chapter_num)
                
                chapter = ChapterMeta(
                    number=chapter_num,
                    title=title,
                    content="",
                    status="planned",
                    beats=beats,
                )
                self.result.chapters.append(chapter)
        
        # Sort chapters
        self.result.chapters.sort(key=lambda c: c.number)
        self.result.chapter_count = len(self.result.chapters)
        self.log(f"Found {self.result.chapter_count} chapter outlines")
    
    def _extract_chapter_beats(self, chapter_num: int) -> List[str]:
        """Extract beats for a specific chapter from beat-sheet tables"""
        beats = []
        
        # Find the chapter section
        pattern = f"KAPITEL\\s+{chapter_num}:"
        match = re.search(pattern, self.content)
        if not match:
            return beats
        
        # Find beat table after this chapter header
        section_start = match.end()
        next_chapter = re.search(r'KAPITEL\s+\d+:', self.content[section_start:])
        section_end = next_chapter.start() + section_start if next_chapter else len(self.content)
        section = self.content[section_start:section_end]
        
        # Parse Beat|Inhalt table
        if 'Beat|Inhalt' in section or 'Beat\tInhalt' in section:
            lines = section.split('\n')
            in_table = False
            for line in lines:
                if 'Beat' in line and 'Inhalt' in line:
                    in_table = True
                    continue
                if in_table and '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 2:
                        beat_name = parts[0].strip()
                        beat_content = parts[1].strip()
                        if beat_name and beat_content and not beat_name.startswith('-'):
                            beats.append(f"{beat_name}: {beat_content}")
                elif in_table and not line.strip():
                    break
        
        return beats
    
    def _extract_sample_prose(self):
        """Extract sample prose sections (Stilprobe)"""
        matches = self.PATTERNS['stilprobe'].finditer(self.content)
        
        for match in matches:
            chapter_num = int(match.group(1))
            start = match.end()
            
            # Find end of prose section (next header or double newline)
            end_patterns = [r'\n\nKAPITEL', r'\n\n📖', r'\n\n📊', r'\n\n🔄']
            end = len(self.content)
            for ep in end_patterns:
                ep_match = re.search(ep, self.content[start:])
                if ep_match:
                    end = min(end, start + ep_match.start())
            
            prose = self.content[start:end].strip()
            if prose:
                self.result.sample_prose[chapter_num] = prose
                self.log(f"Found sample prose for chapter {chapter_num}")
    
    def _extract_working_titles(self):
        """Extract working title suggestions"""
        # Look for quoted titles at beginning of document
        first_500 = self.content[:500]
        matches = re.findall(r'"([^"]+)"', first_500)
        self.result.working_titles = matches[:5]  # Max 5 titles
    
    def _extract_title(self) -> str:
        """Extract book title"""
        # Try from parent directory name
        parent = self.filepath.parent.parent.name
        if parent and parent != 'manuskript':
            return parent.replace('_', ' ').title()
        return "Untitled Book"
    
    def _extract_chapters(self):
        """Extract all chapters from the manuscript"""
        # Find all chapter starts
        starts = list(self.PATTERNS['chapter_start'].finditer(self.content))
        ends = list(self.PATTERNS['chapter_end'].finditer(self.content))
        
        self.log(f"Found {len(starts)} chapter starts, {len(ends)} chapter ends")
        
        for i, match in enumerate(starts):
            chapter_num = int(match.group(1))
            chapter_title = match.group(2).strip()
            
            # Find content between this start and the corresponding end
            start_pos = match.end()
            
            # Find matching end
            end_pos = len(self.content)
            for end_match in ends:
                if int(end_match.group(1)) == chapter_num:
                    end_pos = end_match.start()
                    break
            
            # If no end found, try next chapter start
            if end_pos == len(self.content) and i + 1 < len(starts):
                end_pos = starts[i + 1].start()
            
            content = self.content[start_pos:end_pos].strip()
            
            # Clean content from meta-info
            content = self._clean_chapter_content(content)
            
            chapter = ChapterMeta(
                number=chapter_num,
                title=chapter_title,
                content=content,
                word_count=len(content.split()),
            )
            
            self.result.chapters.append(chapter)
            self.log(f"Extracted Chapter {chapter_num}: {chapter_title} ({chapter.word_count} words)")
        
        self.result.chapter_count = len(self.result.chapters)
    
    def _clean_chapter_content(self, content: str) -> str:
        """Remove meta-info and AI artifacts from chapter content"""
        # Remove AI artifacts
        for key in ['ai_prompt', 'ai_response', 'ai_reasoning', 'ai_planning', 
                    'timestamp', 'orchestrated', 'word_target']:
            content = self.PATTERNS[key].sub('', content)
        
        # Remove meta blocks (everything after status marker)
        status_match = self.PATTERNS['chapter_status'].search(content)
        if status_match:
            content = content[:status_match.start()]
        
        # Remove established/foreshadowing blocks
        for marker in ['established_header', 'foreshadowing_header', 'beats_header']:
            match = self.PATTERNS[marker].search(content)
            if match:
                content = content[:match.start()]
        
        # Clean up excessive whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = content.strip()
        
        return content
    
    def _extract_meta_info(self):
        """Extract meta-information for each chapter"""
        # Find meta blocks between chapters
        for chapter in self.result.chapters:
            chapter_num = chapter.number
            
            # Find the section after this chapter's end
            end_pattern = f"Ende Kapitel {chapter_num}"
            end_pos = self.content.find(end_pattern)
            if end_pos == -1:
                continue
            
            # Find next chapter start or end of file
            next_chapter = f"KAPITEL {chapter_num + 1}:"
            next_pos = self.content.find(next_chapter, end_pos)
            if next_pos == -1:
                next_pos = len(self.content)
            
            meta_section = self.content[end_pos:next_pos]
            
            # Extract status
            status_match = self.PATTERNS['chapter_status'].search(meta_section)
            if status_match:
                chapter.status = "complete"
                word_count = status_match.group(2).replace('.', '').replace(',', '')
                chapter.word_count = int(word_count)
            
            # Extract POV
            pov_match = self.PATTERNS['pov'].search(meta_section)
            if pov_match:
                chapter.pov = pov_match.group(1).strip()
            
            # Extract location
            loc_match = self.PATTERNS['location'].search(meta_section)
            if loc_match:
                chapter.location = loc_match.group(1).strip()
            
            # Extract timeline
            time_match = self.PATTERNS['timeline'].search(meta_section)
            if time_match:
                chapter.timeline = time_match.group(0).strip()
            
            # Extract tension level
            tension_match = self.PATTERNS['tension'].search(meta_section)
            if tension_match:
                chapter.tension_level = int(tension_match.group(1))
            
            # Extract emotional tone
            emotion_match = self.PATTERNS['emotion'].search(meta_section)
            if emotion_match:
                chapter.emotional_tone = emotion_match.group(1).strip()
            
            # Extract established elements
            chapter.established = self._extract_list_block(meta_section, 'Etabliert:')
            
            # Extract foreshadowing
            chapter.foreshadowing = self._extract_list_block(meta_section, 'Foreshadowing:')
            
            # Extract beats
            chapter.beats = self._extract_list_block(meta_section, 'Beats:')
            
            # Extract characters from line
            char_match = self.PATTERNS['characters_line'].search(meta_section)
            if char_match:
                chapter.characters = [c.strip() for c in char_match.group(1).split(',')]
            
            self.log(f"Meta for Ch.{chapter_num}: POV={chapter.pov}, Loc={chapter.location}, "
                    f"{len(chapter.beats)} beats, {len(chapter.established)} established")
    
    def _extract_list_block(self, text: str, header: str) -> List[str]:
        """Extract a list of items after a header"""
        items = []
        start = text.find(header)
        if start == -1:
            return items
        
        # Find the list after the header
        lines = text[start + len(header):].split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Stop at next header or non-list line
            if line.endswith(':') or line.startswith('KAPITEL') or line.startswith('Ende'):
                break
            # Remove list markers
            if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                line = line[1:].strip()
            if line and not line.startswith('Weiter') and not line.startswith('Ja'):
                items.append(line)
        
        return items
    
    def _build_clean_manuscript(self):
        """Build a clean manuscript without meta-info"""
        clean_parts = []
        for chapter in self.result.chapters:
            clean_parts.append(f"# KAPITEL {chapter.number}: {chapter.title}\n\n")
            clean_parts.append(chapter.content)
            clean_parts.append("\n\n---\n\n")
        
        self.result.clean_manuscript = ''.join(clean_parts)
        self.result.word_count = sum(c.word_count for c in self.result.chapters)
    
    def _extract_characters(self):
        """Extract character information from the manuscript with context-based descriptions"""
        # Collect all mentioned characters
        character_mentions = {}
        
        for chapter in self.result.chapters:
            for char_name in chapter.characters:
                if char_name not in character_mentions:
                    character_mentions[char_name] = {
                        'first': chapter.number,
                        'count': 0,
                        'traits': []
                    }
                character_mentions[char_name]['count'] += 1
        
        # Also scan established elements for character traits
        for chapter in self.result.chapters:
            for item in chapter.established:
                for char_name in character_mentions:
                    if char_name.split()[0] in item:
                        # Extract trait
                        trait = item.replace(char_name, '').strip(': ')
                        if trait:
                            character_mentions[char_name]['traits'].append(trait)
        
        # Use context extractor to get descriptions (lazy import to avoid circular deps)
        context_extractor = None
        try:
            # Direct import to avoid __init__.py chain
            import importlib.util
            spec = importlib.util.find_spec('apps.writing_hub.services.context_extractor')
            if spec:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                context_extractor = module.ContextExtractor(self.content, use_ai=False)
        except Exception:
            pass
        
        # Build character objects
        for name, data in character_mentions.items():
            role = "protagonist" if data['first'] == 1 else "supporting"
            if any(t for t in data['traits'] if 'antagon' in t.lower() or 'böse' in t.lower()):
                role = "antagonist"
            
            # Get context-based description
            background = ""
            if context_extractor:
                context = context_extractor.extract_character_context(name)
                background = context.description
                # Add extracted features to traits
                for feature in context.features:
                    if feature not in data['traits']:
                        data['traits'].append(feature)
            
            char = CharacterInfo(
                name=name,
                role=role,
                first_appearance=data['first'],
                mentions=data['count'],
                traits=list(set(data['traits']))[:5],  # Top 5 traits
                background=background
            )
            self.result.characters.append(char)
        
        self.log(f"Extracted {len(self.result.characters)} characters")
    
    def _extract_locations(self):
        """Extract location information with context-based descriptions"""
        location_data = {}
        
        for chapter in self.result.chapters:
            if chapter.location:
                locs = [l.strip() for l in chapter.location.split(',')]
                for loc in locs:
                    if loc not in location_data:
                        location_data[loc] = {'chapters': [], 'features': []}
                    location_data[loc]['chapters'].append(chapter.number)
        
        # Also extract from Ort: lines in planning docs
        ort_matches = re.findall(r'^Ort:\s*(.+)$', self.content, re.MULTILINE)
        for ort in ort_matches:
            locs = [l.strip() for l in ort.split(',')]
            for loc in locs:
                if loc and loc not in location_data:
                    location_data[loc] = {'chapters': [], 'features': []}
        
        # Use context extractor to get descriptions (lazy import to avoid circular deps)
        extractor = None
        try:
            import importlib.util
            spec = importlib.util.find_spec('apps.writing_hub.services.context_extractor')
            if spec:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                extractor = module.ContextExtractor(self.content, use_ai=False)
        except Exception:
            pass
        
        for name, data in location_data.items():
            description = ""
            features = []
            if extractor:
                try:
                    context = extractor.extract_location_context(name)
                    description = context.description
                    features = context.features
                except Exception:
                    pass
            
            loc = LocationInfo(
                name=name,
                description=description,
                chapters=data['chapters'],
                features=features
            )
            self.result.locations.append(loc)
        
        self.log(f"Extracted {len(self.result.locations)} locations")
    
    def _extract_subplots(self):
        """Extract subplot information from planning documents"""
        # Find SUBPLOT headers
        matches = self.PATTERNS['subplot_header'].finditer(self.content)
        
        for match in matches:
            subplot_id = match.group(1)
            subplot_desc = match.group(2).strip()
            
            # Extract character name from description
            char_match = re.search(r'(?:Der|Die|Das)\s+(\w+)', subplot_desc)
            character = char_match.group(1) if char_match else ""
            
            # Try to find weight percentage
            weight = 0
            weight_pattern = f"Subplot\\s+{subplot_id}.*?:\\s*(\\d+)%"
            weight_match = re.search(weight_pattern, self.content)
            if weight_match:
                weight = int(weight_match.group(1))
            
            subplot = SubplotInfo(
                name=f"Subplot {subplot_id}: {subplot_desc}",
                character=character,
                weight_percent=weight,
            )
            self.result.subplots.append(subplot)
        
        # Also look for HAUPTPLOT
        hauptplot_match = re.search(r'HAUPTPLOT.*?:\s*(\d+)%', self.content)
        if hauptplot_match:
            self.result.subplots.insert(0, SubplotInfo(
                name="Hauptplot",
                weight_percent=int(hauptplot_match.group(1))
            ))
        
        self.log(f"Extracted {len(self.result.subplots)} subplots")
    
    def _extract_story_arc(self):
        """Extract story structure/arc information"""
        arc = StoryArc()
        
        # Detect structure type
        if self.PATTERNS['mcfadden'].search(self.content):
            arc.structure_type = "McFadden"
        elif re.search(r'three.?act|drei.?akt', self.content, re.IGNORECASE):
            arc.structure_type = "Three-Act"
        elif re.search(r"hero'?s?.?journey|heldenreise", self.content, re.IGNORECASE):
            arc.structure_type = "Hero's Journey"
        
        # Extract TEIL structure
        teil_matches = self.PATTERNS['teil_structure'].finditer(self.content)
        for match in teil_matches:
            part_num = int(match.group(1))
            part_name = match.group(2).strip()
            start_ch = int(match.group(3))
            end_ch = int(match.group(4))
            
            arc.parts.append({
                'number': part_num,
                'name': part_name,
                'chapters': list(range(start_ch, end_ch + 1)),
            })
        
        # Extract twists
        twist_patterns = [
            r'MID.?BOOK.?TWIST',
            r'TWIST.?SEQUENZ',
            r'Der\s+(?:finale\s+)?(?:McFadden.?)?Twist',
            r'DOPPEL.?TWIST',
        ]
        for pattern in twist_patterns:
            matches = re.finditer(pattern, self.content, re.IGNORECASE)
            for match in matches:
                # Extract context around the twist
                start = max(0, match.start() - 50)
                end = min(len(self.content), match.end() + 200)
                context = self.content[start:end]
                
                arc.twists.append({
                    'name': match.group(0),
                    'context': context[:100] + '...' if len(context) > 100 else context
                })
        
        self.result.story_arc = arc
        self.log(f"Story arc: {arc.structure_type}, {len(arc.parts)} parts, {len(arc.twists)} twists")
    
    def _build_beat_sheet(self):
        """Build a complete beat sheet from extracted data"""
        self.result.beat_sheet = {
            'title': self.result.title,
            'total_chapters': self.result.chapter_count,
            'total_words': self.result.word_count,
            'chapters': []
        }
        
        for chapter in self.result.chapters:
            chapter_data = {
                'number': chapter.number,
                'title': chapter.title,
                'word_count': chapter.word_count,
                'pov': chapter.pov,
                'location': chapter.location,
                'timeline': chapter.timeline,
                'tension': chapter.tension_level,
                'emotion': chapter.emotional_tone,
                'beats': chapter.beats,
                'established': chapter.established,
                'foreshadowing': chapter.foreshadowing,
            }
            self.result.beat_sheet['chapters'].append(chapter_data)
    
    def _calculate_stats(self):
        """Calculate statistics about the manuscript"""
        self.result.stats = {
            'document_type': self.result.document_type,
            'total_chapters': self.result.chapter_count,
            'total_words': self.result.word_count,
            'avg_words_per_chapter': self.result.word_count // max(1, self.result.chapter_count),
            'total_characters': len(self.result.characters),
            'total_locations': len(self.result.locations),
            'total_beats': sum(len(c.beats) for c in self.result.chapters),
            'total_established': sum(len(c.established) for c in self.result.chapters),
            'total_foreshadowing': sum(len(c.foreshadowing) for c in self.result.chapters),
            'chapters_complete': sum(1 for c in self.result.chapters if c.status == 'complete'),
            'chapters_planned': sum(1 for c in self.result.chapters if c.status == 'planned'),
            'total_subplots': len(self.result.subplots),
            'story_arc_type': self.result.story_arc.structure_type,
            'story_arc_parts': len(self.result.story_arc.parts),
            'story_arc_twists': len(self.result.story_arc.twists),
            'sample_prose_chapters': len(self.result.sample_prose),
            'working_titles': len(self.result.working_titles),
        }
    
    def export_yaml(self, output_path: Path):
        """Export beat sheet as YAML"""
        with open(output_path / 'beat_sheet.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(self.result.beat_sheet, f, allow_unicode=True, default_flow_style=False)
    
    def export_json(self, output_path: Path):
        """Export all data as JSON"""
        data = {
            'title': self.result.title,
            'document_type': self.result.document_type,
            'working_titles': self.result.working_titles,
            'stats': self.result.stats,
            'story_arc': asdict(self.result.story_arc),
            'subplots': [asdict(s) for s in self.result.subplots],
            'chapters': [asdict(c) for c in self.result.chapters],
            'characters': [asdict(c) for c in self.result.characters],
            'locations': [asdict(l) for l in self.result.locations],
            'sample_prose': self.result.sample_prose,
        }
        with open(output_path / 'book_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def export_manuscript(self, output_path: Path):
        """Export clean manuscript"""
        with open(output_path / 'manuscript_clean.md', 'w', encoding='utf-8') as f:
            f.write(self.result.clean_manuscript)


class Command(BaseCommand):
    help = 'Reengineer a book from a mixed manuscript file (text + meta-info)'
    
    def add_arguments(self, parser):
        parser.add_argument('filepath', type=str, help='Path to manuscript file')
        parser.add_argument('--analyze', action='store_true', help='Only analyze, do not import')
        parser.add_argument('--import', dest='do_import', action='store_true', help='Import to Django')
        parser.add_argument('--output-dir', type=str, help='Output directory for exports')
        parser.add_argument('--verbose-parse', action='store_true', help='Verbose output')
    
    def handle(self, *args, **options):
        filepath = options['filepath']
        
        if not os.path.exists(filepath):
            raise CommandError(f"File not found: {filepath}")
        
        self.stdout.write(self.style.NOTICE('=' * 60))
        self.stdout.write(self.style.NOTICE('Book Reengineering Parser'))
        self.stdout.write(self.style.NOTICE('=' * 60))
        
        # Run analysis
        reeng = BookReengineer(filepath, verbose=options.get('verbose_parse', False))
        result = reeng.analyze()
        
        # Print summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f"Title: {result.title}"))
        self.stdout.write(self.style.NOTICE(f"  Document Type: {result.document_type.upper()}"))
        if result.working_titles:
            self.stdout.write(f"  Working Titles: {', '.join(result.working_titles[:3])}")
        self.stdout.write(f"  Chapters: {result.chapter_count}")
        self.stdout.write(f"  Words: {result.word_count:,}")
        self.stdout.write(f"  Characters: {len(result.characters)}")
        self.stdout.write(f"  Locations: {len(result.locations)}")
        if result.subplots:
            self.stdout.write(f"  Subplots: {len(result.subplots)}")
        if result.story_arc.structure_type:
            self.stdout.write(f"  Story Arc: {result.story_arc.structure_type} ({len(result.story_arc.parts)} parts, {len(result.story_arc.twists)} twists)")
        
        # Print chapter summary
        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('Chapters:'))
        for ch in result.chapters:
            status = '✅' if ch.status == 'complete' else '📝'
            self.stdout.write(f"  {status} Ch.{ch.number}: {ch.title} ({ch.word_count} words)")
            if ch.pov:
                self.stdout.write(f"      POV: {ch.pov}, Loc: {ch.location}")
        
        # Print characters
        if result.characters:
            self.stdout.write('')
            self.stdout.write(self.style.NOTICE('Characters:'))
            for char in result.characters:
                self.stdout.write(f"  • {char.name} ({char.role}) - first in Ch.{char.first_appearance}")
        
        # Export if output directory specified
        output_dir = options.get('output_dir')
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            reeng.export_yaml(output_path)
            reeng.export_json(output_path)
            reeng.export_manuscript(output_path)
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(f"Exported to: {output_path}"))
            self.stdout.write(f"  - beat_sheet.yaml")
            self.stdout.write(f"  - book_data.json")
            self.stdout.write(f"  - manuscript_clean.md")
        
        # Stats
        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('Statistics:'))
        for key, value in result.stats.items():
            self.stdout.write(f"  {key}: {value}")
        
        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('=' * 60))
