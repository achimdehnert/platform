"""
Sphinx to Single Markdown Export Service
Konvertiert ein komplettes Sphinx-Projekt in eine einzelne Markdown-Datei.

Features:
- Nutzt sphinx-markdown-builder wenn verfügbar
- Fallback auf direkte RST→MD Konvertierung
- Respektiert toctree-Reihenfolge
- Korrigiert interne Links für Single-File Format
- Unterstützt alle wichtigen Sphinx-Extensions

Author: BF Agent Framework
License: MIT
"""

import subprocess
import tempfile
import shutil
import re
from pathlib import Path
from typing import Optional
from datetime import datetime
from dataclasses import dataclass, field

from .sphinx_converter import SphinxFeatureConverter, AutodocConverter, ConversionContext


@dataclass
class ExportMetadata:
    """Metadaten eines Exports."""
    pages_count: int = 0
    word_count: int = 0
    char_count: int = 0
    duration_seconds: float = 0.0
    features_used: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class ExportConfig:
    """Konfiguration für den Export."""
    title: Optional[str] = None
    include_toc: bool = True
    include_metadata: bool = True
    include_autodoc: bool = True
    include_api_reference: bool = True
    intersphinx_mapping: dict[str, str] = field(default_factory=dict)
    python_source_paths: list[str] = field(default_factory=list)
    
    # Output-Optionen
    heading_offset: int = 0  # Erhöhe alle Headings um diesen Wert
    max_heading_level: int = 6
    
    # Formatting
    add_horizontal_rules: bool = True
    preserve_comments: bool = False


class SphinxToMarkdownService:
    """
    Service für die Konvertierung von Sphinx-Projekten zu Markdown.
    
    Unterstützt alle wichtigen Sphinx-Features:
    - autodoc (Python-Docstrings)
    - intersphinx (externe Links)
    - Cross-References
    - Admonitions
    - Code-Blocks
    - Math
    - Tables
    - Images/Figures
    - toctree
    
    Usage:
        service = SphinxToMarkdownService(
            source_path=Path('/path/to/docs'),
            config=ExportConfig(title="My Docs")
        )
        success, output_path, metadata = service.export()
    """
    
    def __init__(
        self,
        source_path: Path,
        config: Optional[ExportConfig] = None
    ):
        """
        Initialisiert den Service.
        
        Args:
            source_path: Pfad zum Sphinx source-Verzeichnis (mit conf.py)
            config: Export-Konfiguration
        """
        self.source_path = Path(source_path)
        self.config = config or ExportConfig()
        self.metadata = ExportMetadata()
        
        # Konversions-Kontext
        self.ctx = ConversionContext(
            source_dir=self.source_path,
            intersphinx_mapping=self.config.intersphinx_mapping
        )
        
        self.converter = SphinxFeatureConverter(self.ctx)
    
    def export(
        self,
        output_path: Optional[Path] = None
    ) -> tuple[bool, Optional[Path], ExportMetadata]:
        """
        Führt den vollständigen Export durch.
        
        Args:
            output_path: Ziel-Pfad für die MD-Datei (optional)
            
        Returns:
            Tuple von (Erfolg, Ausgabepfad, Metadaten)
        """
        import time
        start_time = time.time()
        
        try:
            # 1. Validierung
            if not self._validate_project():
                return False, None, self.metadata
            
            # 2. Temporäres Build-Verzeichnis
            with tempfile.TemporaryDirectory() as tmp_dir:
                build_dir = Path(tmp_dir) / 'markdown'
                
                # 3. Sphinx-Build (falls sphinx-markdown-builder installiert)
                sphinx_success = self._run_sphinx_build(build_dir)
                
                if sphinx_success:
                    # 4a. Kombiniere generierte MD-Dateien
                    combined_content = self._combine_markdown_files(build_dir)
                    self.metadata.features_used.append('sphinx-markdown-builder')
                else:
                    # 4b. Fallback: Direkte RST/MD Konvertierung
                    combined_content = self._direct_conversion()
                    self.metadata.features_used.append('direct-conversion')
                
                # 5. API-Referenz hinzufügen (falls gewünscht)
                if self.config.include_api_reference and self.config.python_source_paths:
                    api_docs = self._generate_api_reference()
                    if api_docs:
                        combined_content += f"\n\n---\n\n# API-Referenz\n\n{api_docs}"
                        self.metadata.features_used.append('autodoc')
                
                # 6. Post-Processing
                combined_content = self._post_process(combined_content)
                
                # 7. Schreibe Ausgabe
                if output_path is None:
                    output_path = Path(tempfile.gettempdir()) / f'{self.source_path.name}_docs.md'
                
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(combined_content, encoding='utf-8')
                
                # 8. Metadaten berechnen
                self.metadata.pages_count = combined_content.count('\n---\n') + 1
                self.metadata.word_count = len(combined_content.split())
                self.metadata.char_count = len(combined_content)
                self.metadata.duration_seconds = time.time() - start_time
                
                return True, output_path, self.metadata
                
        except Exception as e:
            self.metadata.errors.append(str(e))
            self.metadata.duration_seconds = time.time() - start_time
            return False, None, self.metadata
    
    def _validate_project(self) -> bool:
        """Validiert das Sphinx-Projekt."""
        if not self.source_path.exists():
            self.metadata.errors.append(f"Source-Pfad existiert nicht: {self.source_path}")
            return False
        
        if not (self.source_path / 'conf.py').exists():
            self.metadata.errors.append("Keine conf.py gefunden - kein gültiges Sphinx-Projekt")
            return False
        
        # Prüfe auf Index-Datei
        has_index = any(
            (self.source_path / f).exists()
            for f in ['index.rst', 'index.md', 'contents.rst']
        )
        if not has_index:
            self.metadata.warnings.append("Keine index.rst/md gefunden")
        
        return True
    
    def _run_sphinx_build(self, build_dir: Path) -> bool:
        """
        Führt Sphinx-Build mit Markdown-Builder aus.
        
        Returns:
            True wenn erfolgreich, False sonst
        """
        try:
            result = subprocess.run(
                [
                    'sphinx-build',
                    '-b', 'markdown',
                    '-q',  # Quiet
                    '-W', '--keep-going',  # Warnings als Errors, aber weitermachen
                    str(self.source_path),
                    str(build_dir)
                ],
                capture_output=True,
                text=True,
                timeout=300  # 5 Minuten Timeout
            )
            
            if result.stderr:
                # Warnings extrahieren
                for line in result.stderr.split('\n'):
                    if 'WARNING' in line:
                        self.metadata.warnings.append(line.strip())
            
            if result.returncode != 0:
                self.metadata.warnings.append(
                    f"Sphinx-Build mit Returncode {result.returncode} beendet"
                )
                # Prüfe ob trotzdem Output generiert wurde
                if not list(build_dir.glob('*.md')):
                    return False
            
            return True
            
        except FileNotFoundError:
            self.metadata.warnings.append(
                "sphinx-markdown-builder nicht installiert. "
                "Installieren mit: pip install sphinx sphinx-markdown-builder"
            )
            return False
        except subprocess.TimeoutExpired:
            self.metadata.errors.append("Sphinx-Build Timeout (>5min)")
            return False
    
    def _combine_markdown_files(self, md_dir: Path) -> str:
        """
        Kombiniert alle Markdown-Dateien in der richtigen Reihenfolge.
        
        Args:
            md_dir: Verzeichnis mit generierten MD-Dateien
            
        Returns:
            Kombinierter Markdown-Inhalt
        """
        # Toctree-Reihenfolge ermitteln
        toc_order = self._get_toctree_order()
        
        all_files = list(md_dir.rglob('*.md'))
        
        # Sortierung nach toctree
        def sort_key(f: Path) -> tuple:
            stem = f.stem
            rel_path = str(f.relative_to(md_dir).with_suffix(''))
            
            # Index immer zuerst
            if stem == 'index':
                return (0, 0, stem)
            
            # toctree-Reihenfolge
            for i, doc in enumerate(toc_order):
                if doc == stem or doc == rel_path:
                    return (1, i, stem)
            
            # Rest alphabetisch
            return (2, 0, stem)
        
        sorted_files = sorted(all_files, key=sort_key)
        
        # Header
        parts = []
        
        if self.config.include_metadata:
            title = self.config.title or self.source_path.name
            parts.extend([
                f"# {title}\n\n",
                f"> 📚 Generiert am {datetime.now():%Y-%m-%d %H:%M}\n",
                f"> 📁 Quelle: `{self.source_path}`\n\n",
            ])
            
            if self.config.add_horizontal_rules:
                parts.append("---\n\n")
        
        # Inhaltsverzeichnis (dedupliziert)
        if self.config.include_toc:
            parts.append("## 📑 Inhaltsverzeichnis\n\n")
            seen_anchors = set()
            
            for f in sorted_files:
                content = f.read_text(encoding='utf-8')
                h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                if h1_match:
                    title = h1_match.group(1).strip()
                    anchor = self._to_anchor(title)
                    
                    # Duplikate überspringen
                    if anchor in seen_anchors:
                        continue
                    seen_anchors.add(anchor)
                    
                    parts.append(f"- [{title}](#{anchor})\n")
            
            if self.config.add_horizontal_rules:
                parts.append("\n---\n\n")
        
        # Dokumente kombinieren
        for f in sorted_files:
            content = f.read_text(encoding='utf-8')
            
            # Heading-Level anpassen
            if self.config.heading_offset > 0:
                content = self._offset_headings(content, self.config.heading_offset)
            
            # Interne Links korrigieren
            content = self._fix_internal_links(content, md_dir, f)
            
            parts.append(content)
            
            if self.config.add_horizontal_rules:
                parts.append("\n\n---\n\n")
        
        return ''.join(parts)
    
    def _direct_conversion(self) -> str:
        """
        Direkte Konvertierung ohne Sphinx-Build.
        Wird verwendet wenn sphinx-markdown-builder nicht verfügbar.
        
        Returns:
            Markdown-Inhalt
        """
        parts = []
        
        if self.config.include_metadata:
            title = self.config.title or self.source_path.name
            parts.extend([
                f"# {title}\n\n",
                f"> 📚 Generiert am {datetime.now():%Y-%m-%d %H:%M}\n",
                f"> 📁 Quelle: `{self.source_path}`\n",
                f"> ⚠️ Direkte Konvertierung (sphinx-markdown-builder nicht verfügbar)\n\n",
            ])
            
            if self.config.add_horizontal_rules:
                parts.append("---\n\n")
        
        # Toctree-Reihenfolge ermitteln
        toc_order = self._get_toctree_order()
        
        # Sammle alle Quelldateien
        all_files = []
        for ext in ['*.rst', '*.md']:
            all_files.extend(self.source_path.rglob(ext))
        
        # Sortiere nach toctree
        def sort_key(f: Path) -> tuple:
            stem = f.stem
            if stem == 'index':
                return (0, 0, stem)
            for i, doc in enumerate(toc_order):
                if doc == stem:
                    return (1, i, stem)
            return (2, 0, stem)
        
        sorted_files = sorted(all_files, key=sort_key)
        
        # Inhaltsverzeichnis (dedupliziert nach normalisiertem Titel)
        if self.config.include_toc:
            parts.append("## 📑 Inhaltsverzeichnis\n\n")
            seen_titles = set()
            for f in sorted_files:
                if f.name.startswith('_'):
                    continue
                title = f.stem.replace('_', ' ').replace('-', ' ').title()
                anchor = self._to_anchor(f.stem)
                
                # Duplikate nach normalisiertem Titel überspringen
                normalized_title = title.lower().replace(' ', '')
                if normalized_title in seen_titles:
                    continue
                seen_titles.add(normalized_title)
                
                parts.append(f"- [{title}](#{anchor})\n")
            
            if self.config.add_horizontal_rules:
                parts.append("\n---\n\n")
        
        # Konvertiere Dateien
        for f in sorted_files:
            if f.name.startswith('_'):
                continue
            
            content = f.read_text(encoding='utf-8')
            
            # RST zu Markdown konvertieren
            if f.suffix == '.rst':
                # Setze aktuellen Datei-Kontext
                self.ctx.current_file = f
                content = self.converter.convert(content)
                
                # RST-Titel-Unterstriche zu Markdown-Headings
                content = self._convert_rst_titles(content)
            
            parts.append(content)
            
            if self.config.add_horizontal_rules:
                parts.append("\n\n---\n\n")
        
        return ''.join(parts)
    
    def _convert_rst_titles(self, content: str) -> str:
        """
        Konvertiert RST-Titel-Unterstriche zu Markdown-Headings.
        
        RST:
            Mein Titel
            ==========
            
        MD:
            # Mein Titel
        """
        # Patterns für verschiedene Heading-Levels
        patterns = [
            (r'^(.+)\n={3,}\s*$', r'# \1'),      # ===== → H1
            (r'^(.+)\n-{3,}\s*$', r'## \1'),     # ----- → H2
            (r'^(.+)\n~{3,}\s*$', r'### \1'),    # ~~~~~ → H3
            (r'^(.+)\n\^{3,}\s*$', r'#### \1'),  # ^^^^^ → H4
            (r'^(.+)\n"{3,}\s*$', r'##### \1'),  # """"" → H5
        ]
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        return content
    
    def _generate_api_reference(self) -> str:
        """Generiert API-Referenz aus Python-Sourcen."""
        paths = [Path(p) for p in self.config.python_source_paths]
        
        # Validiere Pfade
        valid_paths = []
        for p in paths:
            if not p.is_absolute():
                p = self.source_path.parent / p
            if p.exists():
                valid_paths.append(p)
            else:
                self.metadata.warnings.append(f"Python-Source nicht gefunden: {p}")
        
        if not valid_paths:
            return ""
        
        autodoc = AutodocConverter(valid_paths)
        return autodoc.extract_all()
    
    def _get_toctree_order(self) -> list[str]:
        """
        Extrahiert die Dokumentreihenfolge aus index.rst/md.
        
        Returns:
            Liste von Dokumentnamen in der Reihenfolge des toctree
        """
        for idx_name in ['index.rst', 'index.md', 'contents.rst']:
            idx_file = self.source_path / idx_name
            if idx_file.exists():
                content = idx_file.read_text(encoding='utf-8')
                
                # RST toctree Pattern
                match = re.search(
                    r'\.\. toctree::.*?(?=\n\S|\n\n\S|\Z)',
                    content,
                    re.DOTALL
                )
                if match:
                    order = []
                    for line in match.group().split('\n'):
                        line = line.strip()
                        # Options überspringen
                        if line.startswith(':') or line.startswith('..') or not line:
                            continue
                        # "Title <docname>" Format
                        if '<' in line and '>' in line:
                            doc_match = re.search(r'<(.+)>', line)
                            if doc_match:
                                order.append(doc_match.group(1))
                        else:
                            order.append(line)
                    return order
                
                # MyST toctree (in code-fence)
                myst_match = re.search(
                    r'```{toctree}.*?```',
                    content,
                    re.DOTALL
                )
                if myst_match:
                    order = []
                    for line in myst_match.group().split('\n'):
                        line = line.strip()
                        if line.startswith(':') or line.startswith('```') or not line:
                            continue
                        order.append(line)
                    return order
        
        return []
    
    def _fix_internal_links(
        self,
        content: str,
        md_dir: Path,
        current_file: Path
    ) -> str:
        """
        Korrigiert interne Links für Single-File Format.
        
        [Link](other.md) → [Link](#other)
        [Link](folder/other.md) → [Link](#folder-other)
        """
        def replace_link(match: re.Match) -> str:
            text = match.group(1)
            link = match.group(2)
            
            # Nur lokale .md Links konvertieren
            if link.endswith('.md') and not link.startswith('http'):
                # Entferne .md und konvertiere zu Anchor
                anchor = link.replace('.md', '').replace('/', '-').lower()
                anchor = re.sub(r'[^\w-]', '', anchor)
                return f'[{text}](#{anchor})'
            
            # Relative Pfade ohne Extension
            if not link.startswith(('http', '#', 'mailto:')):
                if '.' not in link.split('/')[-1]:  # Keine Extension
                    anchor = link.replace('/', '-').lower()
                    anchor = re.sub(r'[^\w-]', '', anchor)
                    return f'[{text}](#{anchor})'
            
            return match.group(0)
        
        return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_link, content)
    
    def _offset_headings(self, content: str, offset: int) -> str:
        """Erhöht alle Heading-Levels um den angegebenen Offset."""
        def replace_heading(match: re.Match) -> str:
            hashes = match.group(1)
            text = match.group(2)
            
            new_level = min(len(hashes) + offset, self.config.max_heading_level)
            return f"{'#' * new_level} {text}"
        
        return re.sub(r'^(#{1,6})\s+(.+)$', replace_heading, content, flags=re.MULTILINE)
    
    def _post_process(self, content: str) -> str:
        """Finale Bereinigung des Markdown."""
        # Doppelte Leerzeilen reduzieren
        content = re.sub(r'\n{4,}', '\n\n\n', content)
        
        # Doppelte horizontale Linien
        content = re.sub(r'(---\s*\n)+', '---\n', content)
        
        # Trailing Whitespace entfernen
        content = '\n'.join(line.rstrip() for line in content.split('\n'))
        
        # Finale Newline sicherstellen
        if not content.endswith('\n'):
            content += '\n'
        
        return content
    
    def _to_anchor(self, text: str) -> str:
        """Konvertiert Text zu Markdown-Anchor."""
        anchor = text.lower()
        anchor = re.sub(r'[^\w\s-]', '', anchor)
        anchor = re.sub(r'\s+', '-', anchor)
        anchor = re.sub(r'-+', '-', anchor)
        return anchor.strip('-')


# =============================================================================
# Convenience Functions
# =============================================================================

def sphinx_to_markdown(
    source_path: str | Path,
    output_path: str | Path | None = None,
    title: str | None = None,
    include_toc: bool = True,
    intersphinx_mapping: dict[str, str] | None = None,
    python_source_paths: list[str] | None = None,
) -> tuple[bool, Path | None, ExportMetadata]:
    """
    Convenience-Funktion für einfachen Export.
    
    Args:
        source_path: Pfad zum Sphinx-Projekt
        output_path: Ziel-Pfad (optional)
        title: Dokumenttitel (optional)
        include_toc: Inhaltsverzeichnis generieren
        intersphinx_mapping: Externe Dokumentations-URLs
        python_source_paths: Pfade für API-Referenz
        
    Returns:
        Tuple von (Erfolg, Ausgabepfad, Metadaten)
        
    Example:
        success, path, meta = sphinx_to_markdown(
            '/path/to/docs',
            title="My Project Documentation"
        )
        if success:
            print(f"Exportiert nach: {path}")
            print(f"Seiten: {meta.pages_count}, Wörter: {meta.word_count}")
    """
    config = ExportConfig(
        title=title,
        include_toc=include_toc,
        intersphinx_mapping=intersphinx_mapping or {},
        python_source_paths=python_source_paths or [],
    )
    
    service = SphinxToMarkdownService(
        source_path=Path(source_path),
        config=config
    )
    
    output = Path(output_path) if output_path else None
    return service.export(output)
