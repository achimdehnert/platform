"""
Sphinx Documentation Sync Service
==================================

Prüft und synchronisiert Sphinx-Dokumentation mit dem Quellcode.

Features:
- Erkennt Änderungen in Python-Dateien (Docstrings)
- Erkennt Änderungen in RST/MD-Dokumentationsdateien
- Generiert Bericht über veraltete Dokumentation
- Kann autodoc-Stubs aktualisieren
- Git-basierte Change Detection

Author: BF Agent Framework
"""

import hashlib
import json
import re
import ast
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ChangeType(Enum):
    """Art der Änderung."""
    NEW = "new"
    MODIFIED = "modified"
    DELETED = "deleted"
    OUTDATED = "outdated"


@dataclass
class FileChange:
    """Repräsentiert eine Dateiänderung."""
    path: Path
    change_type: ChangeType
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    details: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'path': str(self.path),
            'change_type': self.change_type.value,
            'details': self.details,
        }


@dataclass
class DocstringInfo:
    """Information über einen Docstring."""
    name: str
    type: str  # class, function, method
    docstring: Optional[str]
    line_number: int
    file_path: Path


@dataclass
class SyncReport:
    """Bericht über Dokumentations-Synchronisation."""
    timestamp: datetime = field(default_factory=datetime.now)
    python_changes: List[FileChange] = field(default_factory=list)
    doc_changes: List[FileChange] = field(default_factory=list)
    missing_docs: List[str] = field(default_factory=list)
    outdated_docs: List[str] = field(default_factory=list)
    undocumented_items: List[DocstringInfo] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    @property
    def has_changes(self) -> bool:
        return bool(
            self.python_changes or 
            self.doc_changes or 
            self.missing_docs or 
            self.outdated_docs
        )
    
    @property
    def total_issues(self) -> int:
        return (
            len(self.python_changes) + 
            len(self.doc_changes) + 
            len(self.missing_docs) + 
            len(self.outdated_docs) +
            len(self.undocumented_items)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'has_changes': self.has_changes,
            'total_issues': self.total_issues,
            'python_changes': [c.to_dict() for c in self.python_changes],
            'doc_changes': [c.to_dict() for c in self.doc_changes],
            'missing_docs': self.missing_docs,
            'outdated_docs': self.outdated_docs,
            'undocumented_items': len(self.undocumented_items),
            'suggestions': self.suggestions,
        }
    
    def to_markdown(self) -> str:
        """Generiert Markdown-Bericht."""
        lines = [
            f"# 📊 Sphinx Sync Report",
            f"",
            f"**Generiert:** {self.timestamp:%Y-%m-%d %H:%M}",
            f"**Status:** {'⚠️ Änderungen gefunden' if self.has_changes else '✅ Alles aktuell'}",
            f"**Issues:** {self.total_issues}",
            f"",
        ]
        
        if self.python_changes:
            lines.extend([
                "## 🐍 Python-Änderungen",
                "",
            ])
            for change in self.python_changes:
                icon = {"new": "🆕", "modified": "✏️", "deleted": "🗑️"}.get(
                    change.change_type.value, "❓"
                )
                lines.append(f"- {icon} `{change.path}` - {change.details}")
            lines.append("")
        
        if self.doc_changes:
            lines.extend([
                "## 📄 Dokumentations-Änderungen",
                "",
            ])
            for change in self.doc_changes:
                icon = {"new": "🆕", "modified": "✏️", "deleted": "🗑️"}.get(
                    change.change_type.value, "❓"
                )
                lines.append(f"- {icon} `{change.path}` - {change.details}")
            lines.append("")
        
        if self.missing_docs:
            lines.extend([
                "## ❌ Fehlende Dokumentation",
                "",
            ])
            for doc in self.missing_docs:
                lines.append(f"- `{doc}`")
            lines.append("")
        
        if self.outdated_docs:
            lines.extend([
                "## ⚠️ Veraltete Dokumentation",
                "",
            ])
            for doc in self.outdated_docs:
                lines.append(f"- `{doc}`")
            lines.append("")
        
        if self.undocumented_items:
            lines.extend([
                "## 📝 Undokumentierte Items",
                f"",
                f"**{len(self.undocumented_items)} Items ohne Docstring**",
                "",
            ])
            for item in self.undocumented_items[:20]:
                lines.append(f"- `{item.file_path}:{item.line_number}` - {item.type} `{item.name}`")
            if len(self.undocumented_items) > 20:
                lines.append(f"- ... und {len(self.undocumented_items) - 20} weitere")
            lines.append("")
        
        if self.suggestions:
            lines.extend([
                "## 💡 Vorschläge",
                "",
            ])
            for suggestion in self.suggestions:
                lines.append(f"- {suggestion}")
            lines.append("")
        
        return "\n".join(lines)


class SphinxSyncService:
    """
    Service zur Synchronisation von Sphinx-Dokumentation.
    
    Usage:
        service = SphinxSyncService('/path/to/project')
        
        # Prüfe auf Änderungen
        report = service.check_changes()
        
        # Generiere fehlende Stubs
        service.generate_missing_stubs()
        
        # Rebuild Sphinx
        service.rebuild_docs()
    """
    
    def __init__(
        self,
        project_root: Path,
        docs_path: Optional[Path] = None,
        python_paths: Optional[List[Path]] = None,
        state_file: Optional[Path] = None,
    ):
        """
        Initialisiert den Sync Service.
        
        Args:
            project_root: Wurzelverzeichnis des Projekts
            docs_path: Pfad zur Sphinx-Dokumentation (default: docs/source)
            python_paths: Python-Verzeichnisse zu überwachen (default: apps/)
            state_file: Datei für Zustandsspeicherung
        """
        self.project_root = Path(project_root)
        self.docs_path = docs_path or self.project_root / 'docs' / 'source'
        self.python_paths = python_paths or [self.project_root / 'apps']
        self.state_file = state_file or self.project_root / '.sphinx_sync_state.json'
        
        self._state: Dict[str, Any] = self._load_state()
    
    def check_changes(
        self,
        since_last_check: bool = True,
        check_docstrings: bool = True,
    ) -> SyncReport:
        """
        Prüft auf Änderungen seit dem letzten Check.
        
        Args:
            since_last_check: Nur Änderungen seit letztem Check
            check_docstrings: Auch Docstrings prüfen
            
        Returns:
            SyncReport mit allen gefundenen Änderungen
        """
        report = SyncReport()
        
        # 1. Git-basierte Änderungen prüfen
        if since_last_check:
            git_changes = self._get_git_changes()
            for path, status in git_changes.items():
                if path.suffix == '.py':
                    report.python_changes.append(FileChange(
                        path=path,
                        change_type=self._git_status_to_change_type(status),
                        details=f"Git: {status}"
                    ))
                elif path.suffix in ['.rst', '.md']:
                    report.doc_changes.append(FileChange(
                        path=path,
                        change_type=self._git_status_to_change_type(status),
                        details=f"Git: {status}"
                    ))
        
        # 2. Fehlende Dokumentation prüfen
        missing = self._find_missing_docs()
        report.missing_docs = missing
        
        # 3. Veraltete Dokumentation prüfen
        outdated = self._find_outdated_docs()
        report.outdated_docs = outdated
        
        # 4. Undokumentierte Items prüfen
        if check_docstrings:
            undocumented = self._find_undocumented_items()
            report.undocumented_items = undocumented
        
        # 5. Vorschläge generieren
        report.suggestions = self._generate_suggestions(report)
        
        # State speichern
        self._save_state()
        
        return report
    
    def generate_missing_stubs(self, dry_run: bool = True) -> List[str]:
        """
        Generiert fehlende autodoc-Stubs.
        
        Args:
            dry_run: Wenn True, nur anzeigen was generiert würde
            
        Returns:
            Liste der generierten/zu generierenden Dateien
        """
        generated = []
        
        for python_path in self.python_paths:
            if not python_path.exists():
                continue
            
            for py_file in python_path.rglob('*.py'):
                if py_file.name.startswith('_') and py_file.name != '__init__.py':
                    continue
                
                # Berechne relativen Modulpfad
                rel_path = py_file.relative_to(self.project_root)
                module_path = str(rel_path.with_suffix('')).replace('/', '.')
                
                # Prüfe ob Dokumentation existiert
                doc_file = self.docs_path / 'api' / f"{module_path}.rst"
                
                if not doc_file.exists():
                    stub_content = self._generate_autodoc_stub(module_path, py_file)
                    
                    if dry_run:
                        generated.append(f"[DRY-RUN] {doc_file}")
                    else:
                        doc_file.parent.mkdir(parents=True, exist_ok=True)
                        doc_file.write_text(stub_content, encoding='utf-8')
                        generated.append(str(doc_file))
        
        return generated
    
    def rebuild_docs(self, clean: bool = False) -> Tuple[bool, str]:
        """
        Baut Sphinx-Dokumentation neu.
        
        Args:
            clean: Vorher clean machen
            
        Returns:
            (success, output)
        """
        docs_dir = self.docs_path.parent
        
        try:
            if clean:
                subprocess.run(
                    ['make', 'clean'],
                    cwd=docs_dir,
                    capture_output=True,
                    timeout=60
                )
            
            result = subprocess.run(
                ['make', 'html'],
                cwd=docs_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            success = result.returncode == 0
            output = result.stdout + result.stderr
            
            return success, output
            
        except subprocess.TimeoutExpired:
            return False, "Build timeout (>5min)"
        except FileNotFoundError:
            return False, "make command not found"
        except Exception as e:
            return False, str(e)
    
    def _get_git_changes(self, since_commit: Optional[str] = None) -> Dict[Path, str]:
        """Holt Git-Änderungen."""
        changes = {}
        
        try:
            # Uncommitted changes
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                status = line[:2].strip()
                filepath = line[3:].strip()
                
                # Nur relevante Dateien
                if filepath.endswith(('.py', '.rst', '.md')):
                    changes[Path(filepath)] = status
            
            # Recent commits (last 7 days or since last check)
            last_check = self._state.get('last_check_commit')
            if last_check:
                result = subprocess.run(
                    ['git', 'diff', '--name-status', last_check, 'HEAD'],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        status, filepath = parts[0], parts[1]
                        if filepath.endswith(('.py', '.rst', '.md')):
                            changes[Path(filepath)] = status
            
        except Exception:
            pass
        
        return changes
    
    def _git_status_to_change_type(self, status: str) -> ChangeType:
        """Konvertiert Git-Status zu ChangeType."""
        if status in ['A', '??']:
            return ChangeType.NEW
        elif status in ['M', 'MM', 'AM']:
            return ChangeType.MODIFIED
        elif status in ['D']:
            return ChangeType.DELETED
        return ChangeType.MODIFIED
    
    def _find_missing_docs(self) -> List[str]:
        """Findet Module ohne Dokumentation."""
        missing = []
        
        # Wichtige Module die dokumentiert sein sollten
        important_modules = [
            'apps/bfagent/handlers',
            'apps/bfagent/services',
            'apps/writing_hub/handlers',
            'apps/writing_hub/services',
            'apps/control_center/views',
            'apps/sphinx_export/services',
        ]
        
        for module in important_modules:
            module_path = self.project_root / module
            if module_path.exists():
                # Prüfe ob Dokumentation existiert
                doc_name = module.replace('/', '_') + '.rst'
                doc_path = self.docs_path / 'reference' / doc_name
                
                if not doc_path.exists():
                    # Auch in api/ prüfen
                    doc_path_api = self.docs_path / 'api' / doc_name
                    if not doc_path_api.exists():
                        missing.append(module)
        
        return missing
    
    def _find_outdated_docs(self) -> List[str]:
        """Findet veraltete Dokumentation."""
        outdated = []
        
        # Prüfe ob RST-Dateien auf nicht-existente Module verweisen
        if self.docs_path.exists():
            for rst_file in self.docs_path.rglob('*.rst'):
                content = rst_file.read_text(encoding='utf-8', errors='ignore')
                
                # Suche nach automodule-Direktiven
                for match in re.finditer(r'\.\. automodule::\s+(\S+)', content):
                    module_name = match.group(1)
                    module_path = module_name.replace('.', '/')
                    
                    # Prüfe ob Modul existiert
                    full_path = self.project_root / f"{module_path}.py"
                    init_path = self.project_root / module_path / '__init__.py'
                    
                    if not full_path.exists() and not init_path.exists():
                        outdated.append(f"{rst_file.name}: {module_name}")
        
        return outdated
    
    def _find_undocumented_items(self) -> List[DocstringInfo]:
        """Findet undokumentierte Klassen und Funktionen."""
        undocumented = []
        
        for python_path in self.python_paths:
            if not python_path.exists():
                continue
            
            for py_file in python_path.rglob('*.py'):
                # Skip tests, migrations, etc.
                if any(skip in str(py_file) for skip in [
                    'migrations', 'tests', '__pycache__', 'conftest'
                ]):
                    continue
                
                try:
                    content = py_file.read_text(encoding='utf-8')
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        # Klassen
                        if isinstance(node, ast.ClassDef):
                            if not ast.get_docstring(node):
                                undocumented.append(DocstringInfo(
                                    name=node.name,
                                    type='class',
                                    docstring=None,
                                    line_number=node.lineno,
                                    file_path=py_file.relative_to(self.project_root)
                                ))
                        
                        # Funktionen (nicht private)
                        elif isinstance(node, ast.FunctionDef):
                            if not node.name.startswith('_'):
                                if not ast.get_docstring(node):
                                    undocumented.append(DocstringInfo(
                                        name=node.name,
                                        type='function',
                                        docstring=None,
                                        line_number=node.lineno,
                                        file_path=py_file.relative_to(self.project_root)
                                    ))
                                    
                except Exception:
                    pass
        
        return undocumented
    
    def _generate_suggestions(self, report: SyncReport) -> List[str]:
        """Generiert Verbesserungsvorschläge."""
        suggestions = []
        
        if report.python_changes:
            suggestions.append(
                f"📝 {len(report.python_changes)} Python-Dateien geändert - "
                "Docstrings prüfen und Dokumentation aktualisieren"
            )
        
        if report.missing_docs:
            suggestions.append(
                f"📄 {len(report.missing_docs)} Module ohne Dokumentation - "
                "`python manage.py sphinx_sync --generate-stubs` ausführen"
            )
        
        if report.outdated_docs:
            suggestions.append(
                f"⚠️ {len(report.outdated_docs)} veraltete Referenzen - "
                "RST-Dateien aktualisieren oder löschen"
            )
        
        if len(report.undocumented_items) > 10:
            suggestions.append(
                f"✍️ {len(report.undocumented_items)} undokumentierte Items - "
                "Docstrings hinzufügen für bessere API-Dokumentation"
            )
        
        if report.has_changes:
            suggestions.append(
                "🔄 Nach Änderungen: `make html` in docs/ ausführen"
            )
        
        return suggestions
    
    def _generate_autodoc_stub(self, module_path: str, py_file: Path) -> str:
        """Generiert autodoc RST-Stub für ein Modul."""
        module_name = module_path.split('.')[-1]
        title = module_name.replace('_', ' ').title()
        underline = '=' * len(title)
        
        return f"""{title}
{underline}

.. automodule:: {module_path}
   :members:
   :undoc-members:
   :show-inheritance:
"""
    
    def _load_state(self) -> Dict[str, Any]:
        """Lädt gespeicherten Zustand."""
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text())
            except Exception:
                pass
        return {}
    
    def _save_state(self):
        """Speichert aktuellen Zustand."""
        try:
            # Aktuellen Commit speichern
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self._state['last_check_commit'] = result.stdout.strip()
            
            self._state['last_check_time'] = datetime.now().isoformat()
            
            self.state_file.write_text(json.dumps(self._state, indent=2))
        except Exception:
            pass


# Singleton
_sync_service: Optional[SphinxSyncService] = None


def get_sphinx_sync_service() -> SphinxSyncService:
    """Gibt Singleton-Instanz zurück."""
    global _sync_service
    if _sync_service is None:
        from django.conf import settings
        _sync_service = SphinxSyncService(settings.BASE_DIR)
    return _sync_service
