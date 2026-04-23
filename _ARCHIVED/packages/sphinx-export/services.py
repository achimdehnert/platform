"""
Sphinx Export Services
======================

Service-Klassen für die Integration in andere Django Apps.

Usage:
    from apps.sphinx_export.services import SphinxExportService, TableConverter
    
    # Quick export
    service = SphinxExportService()
    result = service.export_to_markdown('docs/source', title='My Docs')
    
    # Table conversion standalone
    converter = TableConverter()
    md_table = converter.convert_rst_table(rst_content)

Author: BF Agent Framework
"""

import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .export_service import SphinxToMarkdownService, ExportConfig, ExportMetadata
from .sphinx_converter import SphinxFeatureConverter, AutodocConverter


@dataclass
class ExportResult:
    """Ergebnis eines Sphinx-Exports."""
    success: bool
    output_path: Optional[Path] = None
    content: Optional[str] = None
    metadata: Optional[ExportMetadata] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary für JSON-Serialisierung."""
        return {
            'success': self.success,
            'output_path': str(self.output_path) if self.output_path else None,
            'error': self.error,
            'metadata': {
                'pages_count': self.metadata.pages_count if self.metadata else 0,
                'word_count': self.metadata.word_count if self.metadata else 0,
                'char_count': self.metadata.char_count if self.metadata else 0,
                'duration_seconds': self.metadata.duration_seconds if self.metadata else 0,
                'features_used': self.metadata.features_used if self.metadata else [],
                'warnings': self.metadata.warnings if self.metadata else [],
                'errors': self.metadata.errors if self.metadata else [],
            } if self.metadata else None
        }


class TableConverter:
    """
    Standalone Table Converter für RST → Markdown.
    
    Unterstützt:
    - Simple Tables (===== Unterstriche)
    - Grid Tables (+-----+-----+)
    - List Tables (.. list-table::)
    - CSV Tables (.. csv-table::)
    
    Usage:
        converter = TableConverter()
        
        # Einzelne Tabelle
        md = converter.convert_simple_table(rst_table)
        
        # Alle Tabellen in einem Dokument
        md_content = converter.convert_all_tables(rst_content)
    """
    
    def __init__(self):
        self.patterns = {
            'simple': re.compile(
                r'^(=+\s+)+\n((?:.*\n)+?)(=+\s+)+$',
                re.MULTILINE
            ),
            'grid': re.compile(
                r'^\+[-=+]+\+\n((?:\|.*\|\n)+\+[-=+]+\n)+',
                re.MULTILINE
            ),
            'list_table': re.compile(
                r'\.\. list-table::\s*(.*)?\n((?:\s+.+\n?)+)',
                re.MULTILINE
            ),
            'csv_table': re.compile(
                r'\.\. csv-table::\s*(.*)?\n((?:\s+.+\n?)+)',
                re.MULTILINE
            ),
        }
    
    def convert_all_tables(self, content: str) -> str:
        """Konvertiert alle RST-Tabellen zu Markdown."""
        content = self.patterns['simple'].sub(self._convert_simple, content)
        content = self.patterns['grid'].sub(self._convert_grid, content)
        content = self.patterns['list_table'].sub(self._convert_list_table, content)
        content = self.patterns['csv_table'].sub(self._convert_csv_table, content)
        return content
    
    def convert_simple_table(self, table_text: str) -> str:
        """Konvertiert eine einzelne Simple Table."""
        match = self.patterns['simple'].match(table_text)
        if match:
            return self._convert_simple(match)
        return table_text
    
    def convert_grid_table(self, table_text: str) -> str:
        """Konvertiert eine einzelne Grid Table."""
        match = self.patterns['grid'].match(table_text)
        if match:
            return self._convert_grid(match)
        return table_text
    
    def _convert_simple(self, match: re.Match) -> str:
        """Konvertiert RST Simple Table zu Markdown."""
        full_match = match.group(0)
        lines = full_match.strip().split('\n')
        
        # Finde Spaltenbreiten
        separator_line = lines[0]
        columns = self._parse_column_positions(separator_line)
        
        if not columns:
            return full_match
        
        result_rows = []
        for line in lines:
            if line.startswith('='):
                continue
            
            cells = [line[start:end].strip() if len(line) > start else '' 
                     for start, end in columns]
            
            if cells and any(cells):
                result_rows.append(cells)
        
        return self._rows_to_markdown(result_rows)
    
    def _convert_grid(self, match: re.Match) -> str:
        """Konvertiert RST Grid Table zu Markdown."""
        full_match = match.group(0)
        lines = full_match.strip().split('\n')
        
        result_rows = []
        header_idx = -1
        
        for i, line in enumerate(lines):
            if line.startswith('+'):
                if '=' in line:
                    header_idx = len(result_rows)
                continue
            
            if line.startswith('|'):
                cells = [c.strip() for c in line.split('|')[1:-1]]
                if cells:
                    result_rows.append(cells)
        
        return self._rows_to_markdown(result_rows, header_idx)
    
    def _convert_list_table(self, match: re.Match) -> str:
        """Konvertiert RST list-table zu Markdown."""
        title = match.group(1).strip() if match.group(1) else ''
        content = match.group(2)
        
        # Parse header-rows option
        header_rows = 1
        header_match = re.search(r':header-rows:\s*(\d+)', content)
        if header_match:
            header_rows = int(header_match.group(1))
        
        # Parse rows
        rows = []
        current_row = []
        
        for line in content.split('\n'):
            line = line.strip()
            
            if line.startswith('* -'):
                if current_row:
                    rows.append(current_row)
                current_row = [line[3:].strip()]
            elif line.startswith('- '):
                current_row.append(line[2:].strip())
            elif line.startswith(':'):
                continue
        
        if current_row:
            rows.append(current_row)
        
        result = self._rows_to_markdown(rows, header_rows)
        
        if title:
            result = f'\n**{title}**\n' + result
        
        return result
    
    def _convert_csv_table(self, match: re.Match) -> str:
        """Konvertiert RST csv-table zu Markdown."""
        title = match.group(1).strip() if match.group(1) else ''
        content = match.group(2)
        
        # Parse options
        header_rows = 1
        header_match = re.search(r':header-rows:\s*(\d+)', content)
        if header_match:
            header_rows = int(header_match.group(1))
        
        # Parse CSV data (nach den Optionen)
        rows = []
        in_data = False
        
        for line in content.split('\n'):
            stripped = line.strip()
            
            if stripped.startswith(':'):
                continue
            
            if not stripped:
                in_data = True
                continue
            
            if in_data or ',' in stripped:
                in_data = True
                cells = [c.strip().strip('"\'') for c in stripped.split(',')]
                if cells and any(cells):
                    rows.append(cells)
        
        result = self._rows_to_markdown(rows, header_rows)
        
        if title:
            result = f'\n**{title}**\n' + result
        
        return result
    
    def _parse_column_positions(self, separator: str) -> List[Tuple[int, int]]:
        """Parst Spaltenpositionen aus einer Separator-Zeile."""
        columns = []
        current_start = 0
        
        for i, char in enumerate(separator):
            if char == ' ' and i > 0 and separator[i-1] == '=':
                columns.append((current_start, i))
                current_start = i + 1
            elif i == len(separator) - 1:
                columns.append((current_start, i + 1))
        
        return columns
    
    def _rows_to_markdown(self, rows: List[List[str]], header_idx: int = 1) -> str:
        """Konvertiert Zeilen zu Markdown-Tabelle."""
        if not rows:
            return ''
        
        md_lines = []
        
        for i, row in enumerate(rows):
            md_lines.append('| ' + ' | '.join(row) + ' |')
            
            if i == header_idx - 1:
                md_lines.append('| ' + ' | '.join(['---'] * len(row)) + ' |')
        
        return '\n' + '\n'.join(md_lines) + '\n'


class SphinxExportService:
    """
    High-Level Service für Sphinx → Markdown Export.
    
    Designed für Integration in Django Views, APIs, Celery Tasks.
    
    Usage:
        service = SphinxExportService()
        
        # Einfacher Export
        result = service.export_to_markdown('docs/source')
        
        # Mit Optionen
        result = service.export_to_markdown(
            'docs/source',
            output_path='complete.md',
            title='My Documentation',
            include_toc=True,
            include_api=True,
            python_sources=['apps/myapp']
        )
        
        # Nur Content (ohne Datei)
        result = service.export_to_string('docs/source')
        
        # Validierung
        is_valid, errors = service.validate_project('docs/source')
    """
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialisiert den Service.
        
        Args:
            base_path: Basis-Pfad für relative Pfade (default: Django BASE_DIR)
        """
        if base_path is None:
            from django.conf import settings
            self.base_path = Path(settings.BASE_DIR)
        else:
            self.base_path = Path(base_path)
        
        self.table_converter = TableConverter()
    
    def export_to_markdown(
        self,
        source_path: str,
        output_path: Optional[str] = None,
        title: Optional[str] = None,
        include_toc: bool = True,
        include_api: bool = True,
        python_sources: Optional[List[str]] = None,
        intersphinx: Optional[Dict[str, str]] = None,
    ) -> ExportResult:
        """
        Exportiert Sphinx-Projekt zu Markdown-Datei.
        
        Args:
            source_path: Pfad zum Sphinx source-Verzeichnis
            output_path: Ausgabe-Datei (optional, default: docs_export.md)
            title: Dokumenttitel
            include_toc: Inhaltsverzeichnis generieren
            include_api: API-Referenz aus Python-Sourcen
            python_sources: Python-Pfade für Autodoc
            intersphinx: Intersphinx URL-Mapping
            
        Returns:
            ExportResult mit Erfolg/Fehler und Metadaten
        """
        try:
            # Pfade auflösen
            src = self._resolve_path(source_path)
            out = self._resolve_path(output_path or 'docs_export.md')
            
            # Validierung
            if not src.exists():
                return ExportResult(
                    success=False,
                    error=f"Source-Pfad existiert nicht: {src}"
                )
            
            if not (src / 'conf.py').exists():
                return ExportResult(
                    success=False,
                    error=f"Keine conf.py gefunden in: {src}"
                )
            
            # Konfiguration
            config = ExportConfig(
                title=title,
                include_toc=include_toc,
                include_api_reference=include_api,
                python_source_paths=python_sources or [],
                intersphinx_mapping=intersphinx or {},
            )
            
            # Export
            service = SphinxToMarkdownService(src, config)
            success, result_path, metadata = service.export(out)
            
            if success:
                content = result_path.read_text(encoding='utf-8') if result_path else None
                return ExportResult(
                    success=True,
                    output_path=result_path,
                    content=content,
                    metadata=metadata
                )
            else:
                return ExportResult(
                    success=False,
                    metadata=metadata,
                    error='; '.join(metadata.errors) if metadata else 'Unknown error'
                )
                
        except Exception as e:
            return ExportResult(
                success=False,
                error=str(e)
            )
    
    def export_to_string(
        self,
        source_path: str,
        title: Optional[str] = None,
        include_toc: bool = True,
    ) -> ExportResult:
        """
        Exportiert zu String ohne Datei zu erstellen.
        
        Nützlich für API-Responses oder Previews.
        """
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            temp_path = f.name
        
        try:
            result = self.export_to_markdown(
                source_path,
                output_path=temp_path,
                title=title,
                include_toc=include_toc,
                include_api=False,
            )
            
            if result.success:
                content = Path(temp_path).read_text(encoding='utf-8')
                result.content = content
            
            return result
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def validate_project(self, source_path: str) -> Tuple[bool, List[str]]:
        """
        Validiert ein Sphinx-Projekt.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        src = self._resolve_path(source_path)
        
        if not src.exists():
            errors.append(f"Pfad existiert nicht: {src}")
            return False, errors
        
        if not (src / 'conf.py').exists():
            errors.append("conf.py nicht gefunden")
        
        if not (src / 'index.rst').exists() and not (src / 'index.md').exists():
            errors.append("index.rst oder index.md nicht gefunden")
        
        # Prüfe auf RST/MD Dateien
        rst_files = list(src.rglob('*.rst'))
        md_files = list(src.rglob('*.md'))
        
        if not rst_files and not md_files:
            errors.append("Keine .rst oder .md Dateien gefunden")
        
        return len(errors) == 0, errors
    
    def list_documents(self, source_path: str) -> List[Dict[str, Any]]:
        """
        Listet alle Dokumente in einem Sphinx-Projekt.
        
        Returns:
            Liste von Dokumenten mit Pfad, Titel, Typ
        """
        src = self._resolve_path(source_path)
        documents = []
        
        for ext in ['*.rst', '*.md']:
            for f in src.rglob(ext):
                if f.name.startswith('_'):
                    continue
                
                # Titel extrahieren
                content = f.read_text(encoding='utf-8')
                title = f.stem.replace('_', ' ').replace('-', ' ').title()
                
                # RST Titel
                title_match = re.search(r'^(.+)\n[=\-~]+\s*$', content, re.MULTILINE)
                if title_match:
                    title = title_match.group(1).strip()
                
                # MD Titel
                md_title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                if md_title_match:
                    title = md_title_match.group(1).strip()
                
                documents.append({
                    'path': str(f.relative_to(src)),
                    'title': title,
                    'type': f.suffix[1:],  # 'rst' oder 'md'
                    'size': f.stat().st_size,
                })
        
        return sorted(documents, key=lambda d: d['path'])
    
    def convert_tables(self, content: str) -> str:
        """Konvertiert alle RST-Tabellen in einem String zu Markdown."""
        return self.table_converter.convert_all_tables(content)
    
    def _resolve_path(self, path: str) -> Path:
        """Löst relative Pfade auf."""
        p = Path(path)
        if not p.is_absolute():
            p = self.base_path / p
        return p


# Singleton-Instanz für einfachen Zugriff
_service_instance: Optional[SphinxExportService] = None


def get_sphinx_export_service() -> SphinxExportService:
    """
    Gibt Singleton-Instanz des SphinxExportService zurück.
    
    Usage:
        from apps.sphinx_export.services import get_sphinx_export_service
        
        service = get_sphinx_export_service()
        result = service.export_to_markdown('docs/source')
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = SphinxExportService()
    return _service_instance
