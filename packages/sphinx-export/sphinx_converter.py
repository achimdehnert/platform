"""
Sphinx Feature Converters
Konvertiert spezielle Sphinx-Elemente zu Markdown.

Features:
- Admonitions (note, warning, tip, etc.)
- Code-Blocks
- Cross-References (:ref:, :doc:, :class:, etc.)
- Intersphinx (externe Dokumentations-Links)
- Math (inline und block)
- Images
- Toctree
- Autodoc (Docstring-Extraktion)

Author: BF Agent Framework
License: MIT
"""

import re
import ast
from dataclasses import dataclass, field
from typing import Callable, Optional
from pathlib import Path


@dataclass
class ConversionContext:
    """Kontext für die Konvertierung."""
    source_dir: Path
    intersphinx_mapping: dict[str, str] = field(default_factory=dict)
    current_file: Optional[Path] = None
    all_anchors: set[str] = field(default_factory=set)


class SphinxFeatureConverter:
    """
    Konvertiert Sphinx-spezifische Features zu Markdown.
    
    Unterstützte Features:
    - Admonitions (note, warning, tip, important, danger, caution)
    - Code-Blocks mit Syntax-Highlighting
    - Cross-References (:ref:, :doc:, :class:, :func:, etc.)
    - Intersphinx-Links
    - Math (inline :math: und .. math:: blocks)
    - Images mit Alt-Text
    - Toctree zu Inhaltsverzeichnis
    - Download-Links
    - Glossary-Terms
    """
    
    # Standard Intersphinx-Mappings für bekannte Projekte
    DEFAULT_INTERSPHINX = {
        'python': 'https://docs.python.org/3',
        'django': 'https://docs.djangoproject.com/en/stable',
        'sphinx': 'https://www.sphinx-doc.org/en/master',
        'numpy': 'https://numpy.org/doc/stable',
        'pandas': 'https://pandas.pydata.org/docs',
        'requests': 'https://requests.readthedocs.io/en/latest',
    }
    
    # Emoji-Mapping für Admonitions
    ADMONITION_EMOJI = {
        'note': '📝',
        'warning': '⚠️',
        'tip': '💡',
        'important': '❗',
        'danger': '🚨',
        'caution': '⚡',
        'hint': '💡',
        'attention': '⚠️',
        'error': '❌',
        'seealso': '👉',
        'todo': '📋',
        'deprecated': '🚫',
        'versionadded': '✨',
        'versionchanged': '🔄',
    }
    
    def __init__(self, ctx: ConversionContext):
        self.ctx = ctx
        self._build_converters()
    
    def _build_converters(self):
        """Baut die Liste der Konverter-Regeln."""
        self.converters: list[tuple[re.Pattern, Callable | str]] = [
            # Admonitions (note, warning, etc.)
            (re.compile(
                r'\.\. (note|warning|tip|important|danger|caution|hint|attention|error|seealso|todo|deprecated)::\s*\n((?:\s+.+\n?)+)',
                re.MULTILINE
            ), self._convert_admonition),
            
            # Versionadded/changed mit Argument
            (re.compile(
                r'\.\. (versionadded|versionchanged)::\s*(.+)\n((?:\s+.+\n?)*)',
                re.MULTILINE
            ), self._convert_version_directive),
            
            # Code-Blocks
            (re.compile(
                r'\.\. code-block::\s*(\w+)?\s*\n((?:\s+.+\n?)+)',
                re.MULTILINE
            ), self._convert_code_block),
            
            # Literalinclude
            (re.compile(
                r'\.\. literalinclude::\s*(.+)\n((?:\s+:\w+:.*\n)*)',
                re.MULTILINE
            ), self._convert_literalinclude),
            
            # Cross-References
            (re.compile(r':ref:`([^`]+)`'), self._convert_ref),
            (re.compile(r':doc:`([^`]+)`'), self._convert_doc),
            (re.compile(r':(class|func|meth|attr|mod|exc|obj|data|const):`([^`]+)`'), 
             self._convert_code_ref),
            
            # PEP und RFC Links
            (re.compile(r':pep:`(\d+)`'), r'[PEP \1](https://peps.python.org/pep-\1/)'),
            (re.compile(r':rfc:`(\d+)`'), r'[RFC \1](https://www.rfc-editor.org/rfc/rfc\1)'),
            
            # Inline literals
            (re.compile(r'``([^`]+)``'), r'`\1`'),
            
            # Emphasis (RST style)
            (re.compile(r'\*\*([^*]+)\*\*'), r'**\1**'),
            (re.compile(r'(?<!\*)\*([^*]+)\*(?!\*)'), r'*\1*'),
            
            # Math
            (re.compile(r':math:`([^`]+)`'), r'$\1$'),
            (re.compile(
                r'\.\. math::\s*\n((?:\s+.+\n?)+)',
                re.MULTILINE
            ), self._convert_math_block),
            
            # Images
            (re.compile(
                r'\.\. image::\s*(.+)\n((?:\s+:\w+:.*\n)*)',
                re.MULTILINE
            ), self._convert_image),
            
            # Figures (wie Images, aber mit Caption)
            (re.compile(
                r'\.\. figure::\s*(.+)\n((?:\s+.+\n?)+)',
                re.MULTILINE
            ), self._convert_figure),
            
            # Glossary terms
            (re.compile(r':term:`([^`]+)`'), r'**\1**'),
            
            # Download links
            (re.compile(r':download:`([^`]+)`'), self._convert_download),
            
            # Toctree
            (re.compile(
                r'\.\. toctree::\s*\n((?:\s+.+\n?)+)',
                re.MULTILINE
            ), self._convert_toctree),
            
            # Rubric (Überschrift ohne TOC-Eintrag)
            (re.compile(r'\.\. rubric::\s*(.+)'), r'\n**\1**\n'),
            
            # Centered text
            (re.compile(r'\.\. centered::\s*(.+)'), r'\n<p align="center">\1</p>\n'),
            
            # Raw HTML passthrough
            (re.compile(
                r'\.\. raw::\s*html\s*\n((?:\s+.+\n?)+)',
                re.MULTILINE
            ), self._convert_raw_html),
            
            # Index entries (entfernen)
            (re.compile(r'\.\. index::\s*\n((?:\s+.+\n?)+)', re.MULTILINE), ''),
            
            # Targets
            (re.compile(r'\.\. _[\w-]+:\s*\n?'), ''),
            
            # Comments (RST comments entfernen)
            (re.compile(r'^\.\.\s+[^:\n]+$', re.MULTILINE), ''),
            
            # RST Tables - Simple Table (===== Unterstriche)
            (re.compile(
                r'^(=+\s+)+\n((?:.*\n)+?)(=+\s+)+$',
                re.MULTILINE
            ), self._convert_simple_table),
            
            # RST Tables - Grid Table (+-----+-----+)
            (re.compile(
                r'^\+[-=+]+\+\n((?:\|.*\|\n)+\+[-=+]+\n)+',
                re.MULTILINE
            ), self._convert_grid_table),
            
            # RST list-table directive
            (re.compile(
                r'\.\. list-table::\s*(.*)?\n((?:\s+.+\n?)+)',
                re.MULTILINE
            ), self._convert_list_table),
        ]
    
    def convert(self, content: str) -> str:
        """
        Wendet alle Konverter auf den Inhalt an.
        
        Args:
            content: RST-Inhalt
            
        Returns:
            Markdown-Inhalt
        """
        for pattern, replacement in self.converters:
            if callable(replacement):
                content = pattern.sub(replacement, content)
            else:
                content = pattern.sub(replacement, content)
        
        return self._post_process(content)
    
    def _convert_admonition(self, match: re.Match) -> str:
        """Konvertiert Admonitions zu Markdown Blockquotes mit Emoji."""
        admonition_type = match.group(1).lower()
        content = self._dedent(match.group(2))
        
        emoji = self.ADMONITION_EMOJI.get(admonition_type, '📌')
        title = admonition_type.capitalize()
        
        # Blockquote mit Titel
        lines = content.strip().split('\n')
        quoted = '\n'.join(f'> {line}' for line in lines)
        
        return f'\n> {emoji} **{title}**\n>\n{quoted}\n'
    
    def _convert_version_directive(self, match: re.Match) -> str:
        """Konvertiert versionadded/versionchanged Direktiven."""
        directive_type = match.group(1)
        version = match.group(2).strip()
        description = self._dedent(match.group(3)).strip() if match.group(3) else ''
        
        emoji = self.ADMONITION_EMOJI.get(directive_type, '📌')
        
        if directive_type == 'versionadded':
            title = f"Neu in Version {version}"
        else:
            title = f"Geändert in Version {version}"
        
        if description:
            return f'\n> {emoji} **{title}**: {description}\n'
        else:
            return f'\n> {emoji} **{title}**\n'
    
    def _convert_code_block(self, match: re.Match) -> str:
        """Konvertiert Code-Blocks zu Fenced Code-Blocks."""
        language = match.group(1) or ''
        code = self._dedent(match.group(2))
        
        # Sprach-Aliase normalisieren
        lang_map = {
            'pycon': 'python',
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'sh': 'bash',
            'shell': 'bash',
            'console': 'bash',
        }
        language = lang_map.get(language.lower(), language)
        
        return f'\n```{language}\n{code.strip()}\n```\n'
    
    def _convert_literalinclude(self, match: re.Match) -> str:
        """Konvertiert literalinclude zu Code-Block mit Hinweis."""
        filepath = match.group(1).strip()
        options = match.group(2) if match.group(2) else ''
        
        # Extrahiere Sprache aus Options
        lang_match = re.search(r':language:\s*(\w+)', options)
        language = lang_match.group(1) if lang_match else ''
        
        # Versuche Datei zu lesen
        if self.ctx.source_dir:
            full_path = self.ctx.source_dir / filepath
            if full_path.exists():
                try:
                    code = full_path.read_text(encoding='utf-8')
                    
                    # Lines-Option berücksichtigen
                    lines_match = re.search(r':lines:\s*([\d,-]+)', options)
                    if lines_match:
                        line_spec = lines_match.group(1)
                        code = self._extract_lines(code, line_spec)
                    
                    return f'\n```{language}\n{code.strip()}\n```\n'
                except Exception:
                    pass
        
        return f'\n```{language}\n# Datei: {filepath}\n# (Inhalt nicht verfügbar)\n```\n'
    
    def _extract_lines(self, code: str, line_spec: str) -> str:
        """Extrahiert spezifische Zeilen aus Code."""
        lines = code.split('\n')
        result = []
        
        for part in line_spec.split(','):
            if '-' in part:
                start, end = part.split('-')
                start = int(start) - 1 if start else 0
                end = int(end) if end else len(lines)
                result.extend(lines[start:end])
            else:
                idx = int(part) - 1
                if 0 <= idx < len(lines):
                    result.append(lines[idx])
        
        return '\n'.join(result)
    
    def _convert_ref(self, match: re.Match) -> str:
        """Konvertiert :ref: zu Markdown-Links."""
        ref_content = match.group(1)
        
        # Format: "Title <target>" oder einfach "target"
        if '<' in ref_content and '>' in ref_content:
            title_match = re.match(r'(.+?)\s*<(.+?)>', ref_content)
            if title_match:
                title, target = title_match.groups()
                anchor = self._to_anchor(target)
                return f'[{title}](#{anchor})'
        
        anchor = self._to_anchor(ref_content)
        # Titel aus Anchor generieren
        title = ref_content.replace('_', ' ').replace('-', ' ').title()
        return f'[{title}](#{anchor})'
    
    def _convert_doc(self, match: re.Match) -> str:
        """Konvertiert :doc: zu Markdown-Links."""
        doc_ref = match.group(1)
        
        # Extrahiere Titel und Pfad
        if '<' in doc_ref:
            title_match = re.match(r'(.+?)\s*<(.+?)>', doc_ref)
            if title_match:
                title, path = title_match.groups()
            else:
                title = path = doc_ref
        else:
            title = path = doc_ref
        
        # Konvertiere zu Anchor (für Single-File) oder relativen Link
        anchor = self._to_anchor(path.split('/')[-1])
        
        # Titel bereinigen
        if title == path:
            title = path.split('/')[-1].replace('_', ' ').replace('-', ' ').title()
        
        return f'[{title}](#{anchor})'
    
    def _convert_code_ref(self, match: re.Match) -> str:
        """Konvertiert :class:, :func:, :meth:, etc. zu Code-Links."""
        ref_type = match.group(1)
        target = match.group(2)
        
        # Entferne leading ~ (zeigt nur letzten Teil)
        if target.startswith('~'):
            display = target[1:].split('.')[-1]
        else:
            display = target
        
        # Versuche Intersphinx-Auflösung
        url = self._resolve_intersphinx(ref_type, target.lstrip('~'))
        if url:
            return f'[`{display}`]({url})'
        
        # Fallback: nur Code-Formatierung
        return f'`{display}`'
    
    def _resolve_intersphinx(self, ref_type: str, target: str) -> Optional[str]:
        """
        Löst Intersphinx-Referenz zu URL auf.
        
        Unterstützt:
        - Python stdlib Module
        - Django
        - Benutzerdefinierte Mappings aus ctx.intersphinx_mapping
        """
        parts = target.split('.')
        
        # Benutzer-Mappings prüfen
        for project, base_url in self.ctx.intersphinx_mapping.items():
            if parts[0].lower() == project.lower():
                return f'{base_url}/{"/".join(parts[1:])}'
        
        # Python stdlib
        stdlib_modules = {
            'os', 'sys', 'pathlib', 'typing', 'collections', 'functools',
            'itertools', 'json', 're', 'datetime', 'logging', 'unittest',
            'dataclasses', 'enum', 'abc', 'contextlib', 'asyncio', 'subprocess',
            'threading', 'multiprocessing', 'socket', 'http', 'urllib', 'email',
            'html', 'xml', 'sqlite3', 'io', 'tempfile', 'shutil', 'glob',
        }
        
        if parts[0] in stdlib_modules:
            base = self.DEFAULT_INTERSPHINX.get('python', '')
            if ref_type == 'mod':
                return f'{base}/library/{parts[0]}.html'
            elif ref_type in ('class', 'func', 'meth', 'attr', 'exc', 'data'):
                return f'{base}/library/{parts[0]}.html#{target}'
        
        # Django
        if parts[0] == 'django':
            base = self.DEFAULT_INTERSPHINX.get('django', '')
            return f'{base}/ref/{"/".join(parts[1:])}'
        
        return None
    
    def _convert_math_block(self, match: re.Match) -> str:
        """Konvertiert Math-Blöcke zu Display-Math."""
        math = self._dedent(match.group(1)).strip()
        return f'\n$$\n{math}\n$$\n'
    
    def _convert_image(self, match: re.Match) -> str:
        """Konvertiert Image-Direktiven zu Markdown."""
        image_path = match.group(1).strip()
        options = match.group(2) if match.group(2) else ''
        
        # Extrahiere alt-Text
        alt_match = re.search(r':alt:\s*(.+)', options)
        alt = alt_match.group(1).strip() if alt_match else 'image'
        
        # Extrahiere Breite (optional)
        width_match = re.search(r':width:\s*(\d+)', options)
        
        if width_match:
            width = width_match.group(1)
            return f'\n<img src="{image_path}" alt="{alt}" width="{width}">\n'
        
        return f'\n![{alt}]({image_path})\n'
    
    def _convert_figure(self, match: re.Match) -> str:
        """Konvertiert Figure-Direktiven (mit Caption) zu Markdown."""
        image_path = match.group(1).strip()
        content = self._dedent(match.group(2))
        
        # Extrahiere alt/caption
        alt_match = re.search(r':alt:\s*(.+)', content)
        alt = alt_match.group(1).strip() if alt_match else ''
        
        # Caption ist der Rest ohne Options
        caption_lines = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith(':'):
                caption_lines.append(line)
        
        caption = ' '.join(caption_lines)
        
        if caption:
            return f'\n![{alt or caption}]({image_path})\n\n*{caption}*\n'
        
        return f'\n![{alt or "figure"}]({image_path})\n'
    
    def _convert_download(self, match: re.Match) -> str:
        """Konvertiert Download-Links."""
        download_ref = match.group(1)
        
        if '<' in download_ref:
            title_match = re.match(r'(.+?)\s*<(.+?)>', download_ref)
            if title_match:
                title, path = title_match.groups()
                return f'[📥 {title}]({path})'
        
        return f'[📥 {download_ref}]({download_ref})'
    
    def _convert_toctree(self, match: re.Match) -> str:
        """Konvertiert toctree zu Markdown-Inhaltsverzeichnis."""
        content = match.group(1)
        lines = content.strip().split('\n')
        
        toc_items = []
        max_depth = 2  # Default
        
        for line in lines:
            line = line.strip()
            
            # Options überspringen
            if line.startswith(':'):
                if line.startswith(':maxdepth:'):
                    try:
                        max_depth = int(line.split(':')[-1].strip())
                    except ValueError:
                        pass
                continue
            
            if not line:
                continue
            
            # Prüfe auf "Title <docname>" Format
            if '<' in line and '>' in line:
                title_match = re.match(r'(.+?)\s*<(.+?)>', line)
                if title_match:
                    title, docname = title_match.groups()
                    anchor = self._to_anchor(docname)
                    toc_items.append(f'- [{title}](#{anchor})')
                    continue
            
            # Einfacher Dokumentname
            anchor = self._to_anchor(line)
            title = line.replace('_', ' ').replace('-', ' ').title()
            toc_items.append(f'- [{title}](#{anchor})')
        
        if toc_items:
            return '\n**Inhalt:**\n\n' + '\n'.join(toc_items) + '\n'
        
        return ''
    
    def _convert_raw_html(self, match: re.Match) -> str:
        """Konvertiert raw HTML Blöcke."""
        html = self._dedent(match.group(1)).strip()
        return f'\n{html}\n'
    
    def _convert_simple_table(self, match: re.Match) -> str:
        """
        Konvertiert RST Simple Tables zu Markdown.
        
        RST Format:
            ======  ======  ======
            Col 1   Col 2   Col 3
            ======  ======  ======
            A       B       C
            D       E       F
            ======  ======  ======
        """
        full_match = match.group(0)
        lines = full_match.strip().split('\n')
        
        # Finde Spaltenbreiten aus der ersten Zeile (====)
        separator_line = lines[0]
        columns = []
        current_start = 0
        
        for i, char in enumerate(separator_line):
            if char == ' ' and i > 0 and separator_line[i-1] == '=':
                columns.append((current_start, i))
                current_start = i + 1
            elif i == len(separator_line) - 1:
                columns.append((current_start, i + 1))
        
        if not columns:
            return full_match  # Fallback
        
        # Parse Zeilen
        result_rows = []
        header_found = False
        
        for line in lines:
            if line.startswith('='):
                if result_rows and not header_found:
                    header_found = True
                continue
            
            # Extrahiere Zellen basierend auf Spaltenposition
            cells = []
            for start, end in columns:
                cell = line[start:end].strip() if len(line) > start else ''
                cells.append(cell)
            
            if cells and any(cells):
                result_rows.append(cells)
        
        if not result_rows:
            return full_match
        
        # Erstelle Markdown-Tabelle
        md_lines = []
        
        # Header
        md_lines.append('| ' + ' | '.join(result_rows[0]) + ' |')
        md_lines.append('| ' + ' | '.join(['---'] * len(result_rows[0])) + ' |')
        
        # Body
        for row in result_rows[1:]:
            md_lines.append('| ' + ' | '.join(row) + ' |')
        
        return '\n' + '\n'.join(md_lines) + '\n'
    
    def _convert_grid_table(self, match: re.Match) -> str:
        """
        Konvertiert RST Grid Tables zu Markdown.
        
        RST Format:
            +-------+-------+
            | Col 1 | Col 2 |
            +=======+=======+
            | A     | B     |
            +-------+-------+
        """
        full_match = match.group(0)
        lines = full_match.strip().split('\n')
        
        result_rows = []
        header_separator_idx = -1
        
        for i, line in enumerate(lines):
            if line.startswith('+'):
                # Header-Separator hat '=' statt '-'
                if '=' in line:
                    header_separator_idx = len(result_rows)
                continue
            
            if line.startswith('|'):
                # Extrahiere Zellen
                cells = [c.strip() for c in line.split('|')[1:-1]]
                if cells:
                    result_rows.append(cells)
        
        if not result_rows:
            return full_match
        
        # Erstelle Markdown-Tabelle
        md_lines = []
        
        for i, row in enumerate(result_rows):
            md_lines.append('| ' + ' | '.join(row) + ' |')
            
            # Separator nach Header
            if i == 0 or (header_separator_idx > 0 and i == header_separator_idx - 1):
                md_lines.append('| ' + ' | '.join(['---'] * len(row)) + ' |')
        
        return '\n' + '\n'.join(md_lines) + '\n'
    
    def _convert_list_table(self, match: re.Match) -> str:
        """
        Konvertiert RST list-table Direktive zu Markdown.
        
        RST Format:
            .. list-table:: Title
               :header-rows: 1
               
               * - Col 1
                 - Col 2
               * - A
                 - B
        """
        title = match.group(1).strip() if match.group(1) else ''
        content = self._dedent(match.group(2))
        
        # Parse Optionen
        header_rows = 1
        header_match = re.search(r':header-rows:\s*(\d+)', content)
        if header_match:
            header_rows = int(header_match.group(1))
        
        # Parse Zeilen (beginnen mit * -)
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
                continue  # Option
        
        if current_row:
            rows.append(current_row)
        
        if not rows:
            return ''
        
        # Erstelle Markdown-Tabelle
        md_lines = []
        
        if title:
            md_lines.append(f'\n**{title}**\n')
        
        for i, row in enumerate(rows):
            md_lines.append('| ' + ' | '.join(row) + ' |')
            
            if i == header_rows - 1:
                md_lines.append('| ' + ' | '.join(['---'] * len(row)) + ' |')
        
        return '\n' + '\n'.join(md_lines) + '\n'
    
    def _to_anchor(self, text: str) -> str:
        """Konvertiert Text zu einem gültigen Markdown-Anchor."""
        anchor = text.lower()
        anchor = re.sub(r'[^\w\s-]', '', anchor)
        anchor = re.sub(r'\s+', '-', anchor)
        anchor = re.sub(r'-+', '-', anchor)  # Mehrfache Bindestriche
        return anchor.strip('-')
    
    def _dedent(self, text: str) -> str:
        """Entfernt gemeinsame führende Whitespace."""
        lines = text.split('\n')
        if not lines:
            return text
        
        # Finde minimale Einrückung (ignoriere leere Zeilen)
        min_indent = float('inf')
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                min_indent = min(min_indent, indent)
        
        if min_indent == float('inf'):
            min_indent = 0
        
        return '\n'.join(
            line[min_indent:] if len(line) >= min_indent else line
            for line in lines
        )
    
    def _post_process(self, content: str) -> str:
        """Finale Bereinigung des Markdown."""
        # Doppelte Leerzeilen reduzieren
        content = re.sub(r'\n{4,}', '\n\n\n', content)
        
        # Bereinige RST-Reste (nicht erkannte Direktiven)
        content = re.sub(r'^\.\. [\w-]+::\s*$', '', content, flags=re.MULTILINE)
        
        # Trailing Whitespace entfernen
        content = '\n'.join(line.rstrip() for line in content.split('\n'))
        
        return content


class AutodocConverter:
    """
    Konvertiert autodoc-generierte Dokumentation zu Markdown.
    Extrahiert Docstrings direkt aus Python-Modulen.
    
    Unterstützt:
    - Modul-Docstrings
    - Klassen mit Methoden
    - Funktionen
    - Type Annotations
    - Google/NumPy Style Docstrings (Basic)
    """
    
    def __init__(self, module_paths: list[Path]):
        self.module_paths = module_paths
    
    def extract_all(self) -> str:
        """Extrahiert Docstrings aus allen Modulen."""
        sections = []
        
        for path in self.module_paths:
            if path.is_file() and path.suffix == '.py':
                content = self.extract_docstrings(path)
                if content.strip():
                    sections.append(content)
            elif path.is_dir():
                for py_file in sorted(path.rglob('*.py')):
                    if py_file.name.startswith('_') and py_file.name != '__init__.py':
                        continue
                    content = self.extract_docstrings(py_file)
                    if content.strip():
                        sections.append(content)
        
        return '\n\n---\n\n'.join(sections)
    
    def extract_docstrings(self, module_path: Path) -> str:
        """
        Extrahiert Docstrings aus einem Python-Modul.
        
        Args:
            module_path: Pfad zur Python-Datei
            
        Returns:
            Markdown-formatierte Dokumentation
        """
        try:
            content = module_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
        except Exception as e:
            return f"<!-- Fehler beim Parsen von {module_path}: {e} -->"
        
        # Parent-Referenzen setzen für Kontext
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                child.parent = node
        
        sections = []
        module_name = module_path.stem
        
        # Modul-Docstring
        module_doc = ast.get_docstring(tree)
        if module_doc:
            sections.append(f"## Modul `{module_name}`\n\n{module_doc}\n")
        else:
            sections.append(f"## Modul `{module_name}`\n")
        
        # Top-Level Funktionen und Klassen
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                sections.append(self._format_class(node))
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                if not node.name.startswith('_'):
                    sections.append(self._format_function(node))
        
        return '\n'.join(sections)
    
    def _format_class(self, node: ast.ClassDef) -> str:
        """Formatiert eine Klasse als Markdown."""
        parts = []
        
        # Klassenkopf mit Bases
        bases = [self._get_name(b) for b in node.bases]
        if bases:
            parts.append(f"### class `{node.name}({', '.join(bases)})`\n")
        else:
            parts.append(f"### class `{node.name}`\n")
        
        # Docstring
        docstring = ast.get_docstring(node)
        if docstring:
            parts.append(self._format_docstring(docstring))
            parts.append('')
        
        # Attribute aus __init__
        init_method = None
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                init_method = item
                break
        
        if init_method:
            attrs = self._extract_init_attributes(init_method)
            if attrs:
                parts.append('\n**Attribute:**\n')
                for name, type_hint in attrs:
                    if type_hint:
                        parts.append(f'- `{name}`: {type_hint}')
                    else:
                        parts.append(f'- `{name}`')
                parts.append('')
        
        # Methoden
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not item.name.startswith('_') or item.name in ('__init__', '__call__', '__str__', '__repr__'):
                    methods.append(self._format_method(item, node.name))
        
        if methods:
            parts.append('\n**Methoden:**\n')
            parts.extend(methods)
        
        return '\n'.join(parts)
    
    def _format_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """Formatiert eine Funktion als Markdown."""
        signature = self._get_signature(node)
        async_prefix = 'async ' if isinstance(node, ast.AsyncFunctionDef) else ''
        
        parts = [f"### `{async_prefix}{node.name}{signature}`\n"]
        
        docstring = ast.get_docstring(node)
        if docstring:
            parts.append(self._format_docstring(docstring))
        
        return '\n'.join(parts)
    
    def _format_method(self, node: ast.FunctionDef | ast.AsyncFunctionDef, class_name: str) -> str:
        """Formatiert eine Methode als Markdown."""
        signature = self._get_signature(node)
        async_prefix = 'async ' if isinstance(node, ast.AsyncFunctionDef) else ''
        
        parts = [f"#### `{async_prefix}{node.name}{signature}`\n"]
        
        docstring = ast.get_docstring(node)
        if docstring:
            parts.append(self._format_docstring(docstring))
        
        return '\n'.join(parts)
    
    def _get_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """Extrahiert die Funktionssignatur."""
        args = []
        
        # Positional args
        for i, arg in enumerate(node.args.args):
            if arg.arg == 'self' or arg.arg == 'cls':
                continue
            
            arg_str = arg.arg
            
            # Type annotation
            if arg.annotation:
                try:
                    arg_str += f': {self._get_annotation(arg.annotation)}'
                except Exception:
                    pass
            
            # Default value
            defaults_start = len(node.args.args) - len(node.args.defaults)
            if i >= defaults_start:
                default_idx = i - defaults_start
                try:
                    default = self._get_default(node.args.defaults[default_idx])
                    arg_str += f' = {default}'
                except Exception:
                    pass
            
            args.append(arg_str)
        
        # *args
        if node.args.vararg:
            arg_str = f'*{node.args.vararg.arg}'
            if node.args.vararg.annotation:
                try:
                    arg_str += f': {self._get_annotation(node.args.vararg.annotation)}'
                except Exception:
                    pass
            args.append(arg_str)
        
        # **kwargs
        if node.args.kwarg:
            arg_str = f'**{node.args.kwarg.arg}'
            if node.args.kwarg.annotation:
                try:
                    arg_str += f': {self._get_annotation(node.args.kwarg.annotation)}'
                except Exception:
                    pass
            args.append(arg_str)
        
        # Return type
        return_str = ''
        if node.returns:
            try:
                return_str = f' -> {self._get_annotation(node.returns)}'
            except Exception:
                pass
        
        return f"({', '.join(args)}){return_str}"
    
    def _get_annotation(self, node: ast.expr) -> str:
        """Konvertiert eine Type Annotation zu String."""
        try:
            return ast.unparse(node)
        except Exception:
            return '...'
    
    def _get_default(self, node: ast.expr) -> str:
        """Konvertiert einen Default-Wert zu String."""
        try:
            return ast.unparse(node)
        except Exception:
            return '...'
    
    def _get_name(self, node: ast.expr) -> str:
        """Extrahiert Namen aus verschiedenen AST-Nodes."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f'{self._get_name(node.value)}.{node.attr}'
        elif isinstance(node, ast.Subscript):
            return f'{self._get_name(node.value)}[...]'
        else:
            try:
                return ast.unparse(node)
            except Exception:
                return '...'
    
    def _extract_init_attributes(self, init_method: ast.FunctionDef) -> list[tuple[str, str]]:
        """Extrahiert self.xyz Zuweisungen aus __init__."""
        attrs = []
        
        for node in ast.walk(init_method):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute):
                        if isinstance(target.value, ast.Name) and target.value.id == 'self':
                            attr_name = target.attr
                            type_hint = ''
                            attrs.append((attr_name, type_hint))
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Attribute):
                    if isinstance(node.target.value, ast.Name) and node.target.value.id == 'self':
                        attr_name = node.target.attr
                        type_hint = self._get_annotation(node.annotation) if node.annotation else ''
                        attrs.append((attr_name, type_hint))
        
        return attrs
    
    def _format_docstring(self, docstring: str) -> str:
        """Formatiert einen Docstring für Markdown."""
        # Einfache Konvertierung von Google/NumPy Style
        lines = docstring.split('\n')
        result = []
        in_section = None
        
        for line in lines:
            stripped = line.strip()
            
            # Section headers erkennen
            if stripped in ('Args:', 'Arguments:', 'Parameters:'):
                result.append('\n**Parameter:**\n')
                in_section = 'args'
                continue
            elif stripped in ('Returns:', 'Return:'):
                result.append('\n**Rückgabe:**\n')
                in_section = 'returns'
                continue
            elif stripped in ('Raises:', 'Exceptions:'):
                result.append('\n**Exceptions:**\n')
                in_section = 'raises'
                continue
            elif stripped in ('Example:', 'Examples:'):
                result.append('\n**Beispiel:**\n')
                in_section = 'example'
                continue
            elif stripped in ('Note:', 'Notes:'):
                result.append('\n> **Hinweis:**\n')
                in_section = 'note'
                continue
            elif stripped.endswith(':') and len(stripped) > 1 and stripped[:-1].isalpha():
                # Andere Sections
                result.append(f'\n**{stripped}**\n')
                in_section = 'other'
                continue
            
            # Content verarbeiten
            if in_section in ('args', 'returns', 'raises'):
                # Parameter-Format: name: description oder name (type): description
                param_match = re.match(r'^(\w+)(?:\s*\(([^)]+)\))?:\s*(.+)?$', stripped)
                if param_match:
                    name, type_hint, desc = param_match.groups()
                    if type_hint:
                        result.append(f'- `{name}` ({type_hint}): {desc or ""}')
                    else:
                        result.append(f'- `{name}`: {desc or ""}')
                    continue
            
            result.append(line)
        
        return '\n'.join(result)
