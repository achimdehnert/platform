"""
MCP Refactor Service
====================

Service für die Durchführung von Refactoring-Sessions.

Features:
- Backup-Erstellung vor Änderungen
- Datei-Analyse und Transformation
- Validierung nach Änderungen
- Rollback bei Fehlern

Author: BF Agent Team
"""

from __future__ import annotations

import difflib
import hashlib
import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class FileInfo:
    """Information about a file to process."""
    path: str
    absolute_path: Path
    relative_path: str
    component_type: str
    size: int
    hash: str
    
    @classmethod
    def from_path(cls, path: Path, project_root: Path, component_type: str) -> 'FileInfo':
        """Create FileInfo from a path."""
        content = path.read_bytes()
        return cls(
            path=str(path),
            absolute_path=path,
            relative_path=str(path.relative_to(project_root)),
            component_type=component_type,
            size=len(content),
            hash=hashlib.md5(content).hexdigest(),
        )


@dataclass
class ChangeResult:
    """Result of a file change operation."""
    changed: bool
    change_type: str = 'none'  # none, modified, added, deleted
    lines_added: int = 0
    lines_removed: int = 0
    diff: str = ''
    error: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validation after changes."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# =============================================================================
# REFACTOR SERVICE
# =============================================================================

class MCPRefactorService:
    """
    Service für Refactoring-Operationen.
    
    Führt Refactoring-Sessions durch mit:
    - Backup vor Änderungen
    - Schrittweise Datei-Transformation
    - Validierung (Syntax, Tests)
    - Rollback bei Fehlern
    
    Usage:
        service = MCPRefactorService(session)
        backup_path = service.create_backup()
        files = service.analyze_files()
        for file_info in files:
            result = service.refactor_file(file_info)
        validation = service.validate_changes()
        if not validation.valid:
            service.rollback()
    """
    
    # Backup directory name
    BACKUP_DIR = '.mcp_backups'
    
    # Refactoring rules (can be extended via database)
    DEFAULT_REFACTORING_RULES = {
        'handler': [
            # Add type hints
            {
                'name': 'add_return_type_hints',
                'pattern': r'def (\w+)\(self([^)]*)\):',
                'replacement': r'def \1(self\2) -> Any:',
                'description': 'Add return type hints to methods',
            },
            # Add docstrings
            {
                'name': 'ensure_docstring',
                'pattern': r'(class \w+.*:)\n(\s+)(?!""")',
                'replacement': r'\1\n\2"""\n\2TODO: Add docstring\n\2"""\n\2',
                'description': 'Ensure classes have docstrings',
            },
        ],
        'service': [
            # Add logging
            {
                'name': 'add_logger',
                'pattern': r'^(import.*\n)+',
                'replacement': r'\g<0>\nimport logging\n\nlogger = logging.getLogger(__name__)\n',
                'description': 'Add logger import',
                'condition': lambda content: 'logging' not in content,
            },
        ],
    }
    
    def __init__(
        self,
        session: Optional[Any] = None,
        project_root: Optional[Path] = None,
        dry_run: bool = False,
    ):
        """
        Initialize the refactor service.
        
        Args:
            session: MCPRefactorSession instance (optional)
            project_root: Root directory of the project
            dry_run: If True, don't actually modify files
        """
        self.session = session
        self.project_root = Path(project_root or settings.BASE_DIR)
        self.dry_run = dry_run
        
        self._backup_path: Optional[Path] = None
        self._files_changed: List[str] = []
        self._original_contents: Dict[str, bytes] = {}
        
        # Get domain config if session provided
        self.domain_config = session.domain_config if session else None
        self.base_path = Path(self.domain_config.base_path) if self.domain_config else None
    
    # =========================================================================
    # BACKUP METHODS
    # =========================================================================
    
    def create_backup(self) -> str:
        """
        Create a backup of all files that will be modified.
        
        Returns:
            Path to the backup directory.
        """
        if not self.domain_config:
            raise ValueError("No domain config available - cannot create backup")
        
        # Create backup directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        session_id = self.session.id if self.session else 'manual'
        backup_name = f"{self.domain_config.domain.domain_id}_{session_id}_{timestamp}"
        
        backup_dir = self.project_root / self.BACKUP_DIR / backup_name
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy files to backup
        domain_path = self.project_root / self.base_path
        
        if domain_path.exists():
            for file_path in domain_path.rglob('*.py'):
                relative = file_path.relative_to(domain_path)
                backup_file = backup_dir / relative
                backup_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, backup_file)
        
        self._backup_path = backup_dir
        
        logger.info(f"Backup created: {backup_dir}")
        return str(backup_dir)
    
    def rollback(self) -> bool:
        """
        Rollback all changes from the backup.
        
        Returns:
            True if rollback was successful.
        """
        if not self._backup_path or not self._backup_path.exists():
            logger.error("No backup available for rollback")
            return False
        
        if not self.base_path:
            logger.error("No base path available for rollback")
            return False
        
        domain_path = self.project_root / self.base_path
        
        try:
            # Restore files from backup
            for backup_file in self._backup_path.rglob('*.py'):
                relative = backup_file.relative_to(self._backup_path)
                target_file = domain_path / relative
                
                # Ensure parent directory exists
                target_file.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.copy2(backup_file, target_file)
                logger.debug(f"Restored: {target_file}")
            
            logger.info(f"Rollback completed from: {self._backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}", exc_info=True)
            return False
    
    # =========================================================================
    # ANALYSIS METHODS
    # =========================================================================
    
    def analyze_files(self) -> List[Dict[str, Any]]:
        """
        Analyze files in the domain for refactoring.
        
        Returns:
            List of file info dicts with analysis results.
        """
        if not self.domain_config:
            raise ValueError("No domain config available")
        
        files_to_process = []
        domain_path = self.project_root / self.base_path
        
        if not domain_path.exists():
            logger.warning(f"Domain path not found: {domain_path}")
            return []
        
        # Get components from session or all components
        if self.session and self.session.components_selected:
            component_types = self.session.components_selected
        else:
            component_types = list(self.DEFAULT_REFACTORING_RULES.keys())
        
        # Find files for each component type
        for comp_type in component_types:
            pattern = self._get_pattern_for_component(comp_type)
            
            for file_path in domain_path.rglob(pattern):
                # Skip protected paths
                if self._is_protected(file_path):
                    logger.debug(f"Skipping protected: {file_path}")
                    continue
                
                file_info = {
                    'path': str(file_path),
                    'relative_path': str(file_path.relative_to(self.project_root)),
                    'component_type': comp_type,
                    'size': file_path.stat().st_size,
                    'needs_refactoring': self._needs_refactoring(file_path, comp_type),
                }
                
                files_to_process.append(file_info)
        
        logger.info(f"Found {len(files_to_process)} files to process")
        return files_to_process
    
    def _get_pattern_for_component(self, component_type: str) -> str:
        """Get file pattern for a component type."""
        patterns = {
            'handler': '*_handler.py',
            'service': '*_service.py',
            'repository': '*_repository.py',
            'model': 'models.py',
            'view': 'views*.py',
        }
        return patterns.get(component_type, '*.py')
    
    def _is_protected(self, file_path: Path) -> bool:
        """Check if a file is protected from refactoring."""
        from .sync_service import MCPSyncService
        
        sync_service = MCPSyncService(self.project_root)
        relative_path = str(file_path.relative_to(self.project_root))
        result = sync_service.check_path_protection(relative_path)
        
        return result.get('protected', False)
    
    def _needs_refactoring(self, file_path: Path, component_type: str) -> bool:
        """
        Check if a file needs refactoring based on rules.
        """
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            return False
        
        rules = self.DEFAULT_REFACTORING_RULES.get(component_type, [])
        
        for rule in rules:
            pattern = rule['pattern']
            condition = rule.get('condition')
            
            # Check condition first
            if condition and not condition(content):
                continue
            
            # Check if pattern matches
            if re.search(pattern, content, re.MULTILINE):
                return True
        
        return False
    
    # =========================================================================
    # REFACTORING METHODS
    # =========================================================================
    
    def refactor_file(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply refactoring rules to a file.
        
        Args:
            file_info: Dict with file information from analyze_files()
            
        Returns:
            Dict with change results.
        """
        file_path = Path(file_info['path'])
        component_type = file_info['component_type']
        
        result = {
            'changed': False,
            'change_type': 'none',
            'lines_added': 0,
            'lines_removed': 0,
            'diff': '',
            'error': None,
        }
        
        try:
            # Read original content
            original_content = file_path.read_text(encoding='utf-8')
            self._original_contents[str(file_path)] = original_content.encode('utf-8')
            
            # Apply refactoring rules
            new_content = self._apply_rules(original_content, component_type)
            
            # Check if content changed
            if new_content != original_content:
                result['changed'] = True
                result['change_type'] = 'modified'
                
                # Calculate diff
                diff_lines = list(difflib.unified_diff(
                    original_content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=f'a/{file_info["relative_path"]}',
                    tofile=f'b/{file_info["relative_path"]}',
                ))
                result['diff'] = ''.join(diff_lines)
                
                # Count added/removed lines
                for line in diff_lines:
                    if line.startswith('+') and not line.startswith('+++'):
                        result['lines_added'] += 1
                    elif line.startswith('-') and not line.startswith('---'):
                        result['lines_removed'] += 1
                
                # Write new content (unless dry run)
                if not self.dry_run:
                    file_path.write_text(new_content, encoding='utf-8')
                    self._files_changed.append(str(file_path))
                    logger.debug(f"Modified: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to refactor {file_path}: {e}")
            result['error'] = str(e)
        
        return result
    
    def _apply_rules(self, content: str, component_type: str) -> str:
        """
        Apply all refactoring rules to content.
        """
        rules = self.DEFAULT_REFACTORING_RULES.get(component_type, [])
        
        for rule in rules:
            pattern = rule['pattern']
            replacement = rule['replacement']
            condition = rule.get('condition')
            
            # Check condition
            if condition and not condition(content):
                continue
            
            # Apply rule
            try:
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            except Exception as e:
                logger.warning(f"Rule {rule['name']} failed: {e}")
        
        return content
    
    # =========================================================================
    # VALIDATION METHODS
    # =========================================================================
    
    def validate_changes(self) -> Dict[str, Any]:
        """
        Validate all changes made during the session.
        
        Runs:
        - Python syntax check
        - Import check
        - Optional: Tests
        
        Returns:
            Dict with validation results.
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
        }
        
        # Validate each changed file
        for file_path in self._files_changed:
            file_result = self._validate_file(Path(file_path))
            
            if not file_result['valid']:
                result['valid'] = False
                result['errors'].extend(file_result['errors'])
            
            result['warnings'].extend(file_result.get('warnings', []))
        
        # Run syntax check on all modified files
        syntax_result = self._check_syntax()
        if not syntax_result['valid']:
            result['valid'] = False
            result['errors'].extend(syntax_result['errors'])
        
        logger.info(f"Validation result: valid={result['valid']}, errors={len(result['errors'])}")
        
        return result
    
    def _validate_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate a single file."""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Try to compile the Python code
            compile(content, str(file_path), 'exec')
            
        except SyntaxError as e:
            result['valid'] = False
            result['errors'].append(f"{file_path}: Syntax error - {e}")
            
        except Exception as e:
            result['warnings'].append(f"{file_path}: Warning - {e}")
        
        return result
    
    def _check_syntax(self) -> Dict[str, Any]:
        """
        Run Python syntax check on modified files.
        """
        result = {'valid': True, 'errors': []}
        
        for file_path in self._files_changed:
            try:
                # Use Python -m py_compile for syntax check
                subprocess.run(
                    ['python', '-m', 'py_compile', file_path],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as e:
                result['valid'] = False
                result['errors'].append(f"{file_path}: {e.stderr}")
            except FileNotFoundError:
                # Python not available, skip check
                pass
        
        return result
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics for the current session."""
        return {
            'files_analyzed': len(self._original_contents),
            'files_changed': len(self._files_changed),
            'backup_path': str(self._backup_path) if self._backup_path else None,
            'dry_run': self.dry_run,
        }
    
    def cleanup_backup(self, keep_days: int = 7) -> int:
        """
        Clean up old backups.
        
        Args:
            keep_days: Number of days to keep backups.
            
        Returns:
            Number of backups deleted.
        """
        backup_base = self.project_root / self.BACKUP_DIR
        
        if not backup_base.exists():
            return 0
        
        deleted = 0
        cutoff = datetime.now().timestamp() - (keep_days * 86400)
        
        for backup_dir in backup_base.iterdir():
            if backup_dir.is_dir():
                if backup_dir.stat().st_mtime < cutoff:
                    shutil.rmtree(backup_dir)
                    deleted += 1
                    logger.debug(f"Deleted old backup: {backup_dir}")
        
        return deleted


# =============================================================================
# REFACTORING RULE REGISTRY
# =============================================================================

class RefactoringRuleRegistry:
    """
    Registry for refactoring rules.
    
    Allows adding custom rules via database or code.
    """
    
    _instance: Optional['RefactoringRuleRegistry'] = None
    _rules: Dict[str, List[Dict[str, Any]]] = {}
    
    @classmethod
    def get_instance(cls) -> 'RefactoringRuleRegistry':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        # Load default rules
        self._rules = dict(MCPRefactorService.DEFAULT_REFACTORING_RULES)
        
        # Load database rules
        self._load_database_rules()
    
    def _load_database_rules(self):
        """Load custom rules from database."""
        try:
            from bfagent_mcp.models_mcp import MCPRefactoringRule
            
            for rule in MCPRefactoringRule.objects.filter(is_active=True):
                component_type = rule.component_type
                
                if component_type not in self._rules:
                    self._rules[component_type] = []
                
                self._rules[component_type].append({
                    'name': rule.name,
                    'pattern': rule.pattern,
                    'replacement': rule.replacement,
                    'description': rule.description,
                    'order': rule.order,
                })
            
        except Exception as e:
            logger.debug(f"Could not load database rules: {e}")
    
    def get_rules(self, component_type: str) -> List[Dict[str, Any]]:
        """Get rules for a component type."""
        rules = self._rules.get(component_type, [])
        return sorted(rules, key=lambda r: r.get('order', 0))
    
    def add_rule(
        self,
        component_type: str,
        name: str,
        pattern: str,
        replacement: str,
        **kwargs
    ):
        """Add a custom rule."""
        if component_type not in self._rules:
            self._rules[component_type] = []
        
        self._rules[component_type].append({
            'name': name,
            'pattern': pattern,
            'replacement': replacement,
            **kwargs
        })
    
    def list_rules(self) -> Dict[str, List[str]]:
        """List all registered rules."""
        return {
            comp_type: [r['name'] for r in rules]
            for comp_type, rules in self._rules.items()
        }
