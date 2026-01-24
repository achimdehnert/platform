"""
Smart Content Merger für KI-generierte Inhalte
==============================================

Intelligentes Zusammenführen von bestehendem Content mit KI-generierten Inhalten:
- Diff-basierte Analyse
- Abschnitts-Erkennung
- Selektives Übernehmen
"""

import re
import difflib
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


class MergeAction(Enum):
    """Mögliche Aktionen für einen Abschnitt."""
    KEEP = "keep"       # Bestehenden Inhalt behalten
    ADD = "add"         # Neuen Inhalt hinzufügen
    REPLACE = "replace" # Bestehenden durch neuen ersetzen
    SKIP = "skip"       # Neuen Inhalt überspringen


@dataclass
class ContentSection:
    """Ein Abschnitt des Inhalts."""
    heading: str
    content: str
    level: int = 1  # 1 = ##, 2 = ###, 3 = ####
    line_start: int = 0
    line_end: int = 0


@dataclass
class MergeDiff:
    """Diff zwischen zwei Abschnitten."""
    section_heading: str
    existing_content: str
    new_content: str
    is_new: bool = False        # Abschnitt existiert noch nicht
    is_modified: bool = False   # Abschnitt wurde geändert
    is_empty: bool = False      # Bestehender Abschnitt ist leer
    similarity: float = 0.0     # 0.0 - 1.0
    suggested_action: MergeAction = MergeAction.KEEP
    
    def get_html_diff(self) -> str:
        """Generiert HTML-Diff für Anzeige."""
        if self.is_new:
            return f'<div class="diff-add">{self._escape(self.new_content)}</div>'
        
        if self.is_empty:
            return f'<div class="diff-add">{self._escape(self.new_content)}</div>'
        
        if self.similarity > 0.9:
            return f'<div class="diff-same">{self._escape(self.existing_content)}</div>'
        
        # Zeilenweiser Diff
        existing_lines = self.existing_content.splitlines()
        new_lines = self.new_content.splitlines()
        
        diff = difflib.unified_diff(
            existing_lines, 
            new_lines, 
            lineterm='',
            n=0
        )
        
        html_parts = []
        for line in diff:
            if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
                continue
            elif line.startswith('+'):
                html_parts.append(f'<div class="diff-add">+ {self._escape(line[1:])}</div>')
            elif line.startswith('-'):
                html_parts.append(f'<div class="diff-remove">- {self._escape(line[1:])}</div>')
            else:
                html_parts.append(f'<div class="diff-same">{self._escape(line)}</div>')
        
        return '\n'.join(html_parts) if html_parts else f'<div class="diff-same">{self._escape(self.existing_content)}</div>'
    
    def _escape(self, text: str) -> str:
        """HTML-Escape."""
        return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('\n', '<br>'))


@dataclass 
class MergeResult:
    """Ergebnis einer Merge-Operation."""
    merged_content: str
    diffs: List[MergeDiff] = field(default_factory=list)
    sections_added: int = 0
    sections_modified: int = 0
    sections_kept: int = 0


class SmartContentMerger:
    """Intelligenter Content-Merger für Markdown-Inhalte."""
    
    # Pattern für Markdown-Überschriften
    HEADING_PATTERN = re.compile(r'^(#{1,4})\s+(.+)$', re.MULTILINE)
    
    def __init__(self):
        self.similarity_threshold = 0.7  # Ab 70% als "ähnlich" betrachten
    
    def parse_sections(self, content: str) -> List[ContentSection]:
        """Parst Content in Abschnitte basierend auf Überschriften."""
        if not content or not content.strip():
            return []
        
        sections = []
        lines = content.split('\n')
        current_section = None
        current_lines = []
        
        for i, line in enumerate(lines):
            match = self.HEADING_PATTERN.match(line)
            if match:
                # Vorherigen Abschnitt speichern
                if current_section:
                    current_section.content = '\n'.join(current_lines).strip()
                    current_section.line_end = i - 1
                    sections.append(current_section)
                
                # Neuen Abschnitt starten
                level = len(match.group(1))
                heading = match.group(2).strip()
                current_section = ContentSection(
                    heading=heading,
                    content="",
                    level=level,
                    line_start=i
                )
                current_lines = []
            elif current_section:
                current_lines.append(line)
        
        # Letzten Abschnitt speichern
        if current_section:
            current_section.content = '\n'.join(current_lines).strip()
            current_section.line_end = len(lines) - 1
            sections.append(current_section)
        
        return sections
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Berechnet Ähnlichkeit zwischen zwei Texten (0.0 - 1.0)."""
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0
        
        # Normalisieren
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()
        
        return difflib.SequenceMatcher(None, text1, text2).ratio()
    
    def find_matching_section(
        self, 
        section: ContentSection, 
        candidates: List[ContentSection]
    ) -> Optional[ContentSection]:
        """Findet passenden Abschnitt in Kandidatenliste."""
        # Exakte Überschrift-Matches
        for candidate in candidates:
            if self._normalize_heading(section.heading) == self._normalize_heading(candidate.heading):
                return candidate
        
        # Fuzzy Heading Match
        for candidate in candidates:
            if self.calculate_similarity(section.heading, candidate.heading) > 0.8:
                return candidate
        
        return None
    
    def _normalize_heading(self, heading: str) -> str:
        """Normalisiert Überschrift für Vergleich."""
        # Entferne Nummerierung (z.B. "1.1", "2.3.1")
        normalized = re.sub(r'^\d+(\.\d+)*\s*', '', heading)
        return normalized.lower().strip()
    
    def create_merge_diff(
        self, 
        existing_content: str, 
        new_content: str
    ) -> List[MergeDiff]:
        """
        Erstellt Diff-Liste für Merge-Vorschau.
        
        Args:
            existing_content: Bestehender Content
            new_content: Neuer (KI-generierter) Content
            
        Returns:
            Liste von MergeDiff-Objekten für jeden Abschnitt
        """
        existing_sections = self.parse_sections(existing_content)
        new_sections = self.parse_sections(new_content)
        
        diffs = []
        processed_new = set()
        
        # Bestehende Abschnitte durchgehen
        for existing in existing_sections:
            matching_new = self.find_matching_section(existing, new_sections)
            
            if matching_new:
                processed_new.add(id(matching_new))
                similarity = self.calculate_similarity(
                    existing.content, 
                    matching_new.content
                )
                
                # Bestimme Aktion
                if similarity > 0.95:
                    action = MergeAction.KEEP
                elif not existing.content.strip():
                    action = MergeAction.ADD
                elif similarity < self.similarity_threshold:
                    action = MergeAction.REPLACE
                else:
                    action = MergeAction.KEEP
                
                diffs.append(MergeDiff(
                    section_heading=existing.heading,
                    existing_content=existing.content,
                    new_content=matching_new.content,
                    is_new=False,
                    is_modified=similarity < 0.95,
                    is_empty=not existing.content.strip(),
                    similarity=similarity,
                    suggested_action=action
                ))
            else:
                # Kein neuer Inhalt für diesen Abschnitt
                diffs.append(MergeDiff(
                    section_heading=existing.heading,
                    existing_content=existing.content,
                    new_content="",
                    is_new=False,
                    is_modified=False,
                    similarity=1.0,
                    suggested_action=MergeAction.KEEP
                ))
        
        # Neue Abschnitte (nicht in existing)
        for new_section in new_sections:
            if id(new_section) not in processed_new:
                diffs.append(MergeDiff(
                    section_heading=new_section.heading,
                    existing_content="",
                    new_content=new_section.content,
                    is_new=True,
                    is_modified=False,
                    is_empty=True,
                    similarity=0.0,
                    suggested_action=MergeAction.ADD
                ))
        
        return diffs
    
    def merge_content(
        self, 
        existing_content: str, 
        new_content: str,
        actions: Optional[Dict[str, MergeAction]] = None
    ) -> MergeResult:
        """
        Führt Content zusammen basierend auf Aktionen.
        
        Args:
            existing_content: Bestehender Content
            new_content: Neuer Content
            actions: Dict mit {heading: MergeAction}, None = auto
            
        Returns:
            MergeResult mit zusammengeführtem Content
        """
        diffs = self.create_merge_diff(existing_content, new_content)
        
        result = MergeResult(merged_content="", diffs=diffs)
        merged_parts = []
        
        for diff in diffs:
            # Aktion bestimmen
            if actions and diff.section_heading in actions:
                action = actions[diff.section_heading]
            else:
                action = diff.suggested_action
            
            # Aktion ausführen
            if action == MergeAction.KEEP:
                if diff.existing_content:
                    merged_parts.append(f"## {diff.section_heading}\n\n{diff.existing_content}")
                result.sections_kept += 1
                
            elif action == MergeAction.ADD:
                if diff.new_content:
                    merged_parts.append(f"## {diff.section_heading}\n\n{diff.new_content}")
                result.sections_added += 1
                
            elif action == MergeAction.REPLACE:
                if diff.new_content:
                    merged_parts.append(f"## {diff.section_heading}\n\n{diff.new_content}")
                result.sections_modified += 1
                
            elif action == MergeAction.SKIP:
                if diff.existing_content:
                    merged_parts.append(f"## {diff.section_heading}\n\n{diff.existing_content}")
                result.sections_kept += 1
        
        result.merged_content = "\n\n".join(merged_parts)
        return result
    
    def smart_append(self, existing: str, new: str) -> str:
        """
        Einfaches Smart-Append: Fügt neuen Content an, aber vermeidet Duplikate.
        
        Args:
            existing: Bestehender Content
            new: Neuer Content
            
        Returns:
            Zusammengeführter Content
        """
        if not existing or not existing.strip():
            return new
        
        if not new or not new.strip():
            return existing
        
        # Prüfe ob new bereits in existing enthalten
        if new.strip() in existing:
            return existing
        
        # Prüfe Überschriften-Duplikate
        existing_sections = self.parse_sections(existing)
        new_sections = self.parse_sections(new)
        
        existing_headings = {self._normalize_heading(s.heading) for s in existing_sections}
        
        # Nur Abschnitte hinzufügen, die noch nicht existieren
        new_parts = []
        for section in new_sections:
            if self._normalize_heading(section.heading) not in existing_headings:
                heading_prefix = '#' * section.level
                new_parts.append(f"{heading_prefix} {section.heading}\n\n{section.content}")
        
        if new_parts:
            return existing.rstrip() + "\n\n---\n\n" + "\n\n".join(new_parts)
        
        return existing


def get_merge_preview_html(existing: str, new: str) -> str:
    """
    Generiert HTML für Merge-Vorschau.
    
    Args:
        existing: Bestehender Content
        new: Neuer Content
        
    Returns:
        HTML-String für Diff-Anzeige
    """
    merger = SmartContentMerger()
    diffs = merger.create_merge_diff(existing, new)
    
    html_parts = ["""
    <style>
        .merge-preview { font-family: monospace; font-size: 13px; }
        .merge-section { margin-bottom: 20px; border: 1px solid #ddd; border-radius: 5px; }
        .merge-header { padding: 10px; background: #f5f5f5; border-bottom: 1px solid #ddd; }
        .merge-header.new { background: #d4edda; }
        .merge-header.modified { background: #fff3cd; }
        .merge-content { padding: 10px; white-space: pre-wrap; }
        .diff-add { background: #d4edda; color: #155724; }
        .diff-remove { background: #f8d7da; color: #721c24; text-decoration: line-through; }
        .diff-same { color: #666; }
        .action-badge { float: right; }
    </style>
    <div class="merge-preview">
    """]
    
    for diff in diffs:
        header_class = ""
        if diff.is_new:
            header_class = "new"
        elif diff.is_modified:
            header_class = "modified"
        
        action_badge = {
            MergeAction.KEEP: '<span class="badge bg-secondary">Behalten</span>',
            MergeAction.ADD: '<span class="badge bg-success">Hinzufügen</span>',
            MergeAction.REPLACE: '<span class="badge bg-warning">Ersetzen</span>',
            MergeAction.SKIP: '<span class="badge bg-light text-dark">Überspringen</span>',
        }.get(diff.suggested_action, '')
        
        html_parts.append(f"""
        <div class="merge-section">
            <div class="merge-header {header_class}">
                <strong>{diff.section_heading}</strong>
                <span class="action-badge">{action_badge}</span>
            </div>
            <div class="merge-content">
                {diff.get_html_diff()}
            </div>
        </div>
        """)
    
    html_parts.append("</div>")
    return "\n".join(html_parts)
