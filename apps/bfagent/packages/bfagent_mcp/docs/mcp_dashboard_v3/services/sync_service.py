"""
MCP Sync Service
================

Service für die Synchronisation von MCP-Konfigurationsdaten.

Synchronisiert:
- Domain Configurations aus dem Dateisystem
- Protected Paths
- Component Registrations
- Naming Conventions

Author: BF Agent Team
"""

from __future__ import annotations

import fnmatch
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SyncResult:
    """Result of a sync operation."""
    synced: int = 0
    created: int = 0
    updated: int = 0
    deleted: int = 0
    skipped: int = 0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'synced': self.synced,
            'created': self.created,
            'updated': self.updated,
            'deleted': self.deleted,
            'skipped': self.skipped,
            'errors': self.errors,
        }


@dataclass
class DomainInfo:
    """Information about a discovered domain."""
    domain_id: str
    display_name: str
    base_path: str
    has_handlers: bool = False
    has_services: bool = False
    has_models: bool = False
    has_tests: bool = False
    handler_count: int = 0
    service_count: int = 0
    model_count: int = 0


# =============================================================================
# SYNC SERVICE
# =============================================================================

class MCPSyncService:
    """
    Service für MCP Daten-Synchronisation.
    
    Scannt das Projekt-Verzeichnis und synchronisiert:
    - Domains und ihre Konfigurationen
    - Protected Paths
    - Component Types
    - Naming Conventions
    
    Usage:
        service = MCPSyncService()
        result = service.sync_all()
    """
    
    # Default paths to scan for domains
    DEFAULT_DOMAIN_PATHS = [
        'apps',
        'packages',
    ]
    
    # Default protected path patterns
    DEFAULT_PROTECTED_PATTERNS = [
        ('packages/bfagent_mcp/**', 'absolute', 'MCP Package', 'mcp'),
        ('config/**', 'absolute', 'Configuration', 'config'),
        ('.env*', 'absolute', 'Environment Files', 'security'),
        ('manage.py', 'absolute', 'Django Entry', 'infrastructure'),
        ('**/migrations/**', 'review', 'Database Migrations', 'infrastructure'),
        ('Dockerfile*', 'warn', 'Docker Config', 'infrastructure'),
        ('docker-compose*.yml', 'warn', 'Docker Compose', 'infrastructure'),
        ('*.lock', 'warn', 'Lock Files', 'infrastructure'),
        ('**/__pycache__/**', 'absolute', 'Python Cache', 'infrastructure'),
        ('.git/**', 'absolute', 'Git Repository', 'infrastructure'),
    ]
    
    # Component types to detect
    COMPONENT_PATTERNS = {
        'handler': {
            'pattern': '*_handler.py',
            'class_suffix': 'Handler',
            'icon': '🔧',
        },
        'service': {
            'pattern': '*_service.py',
            'class_suffix': 'Service',
            'icon': '⚙️',
        },
        'repository': {
            'pattern': '*_repository.py',
            'class_suffix': 'Repository',
            'icon': '🗄️',
        },
        'model': {
            'pattern': 'models.py',
            'class_suffix': None,
            'icon': '📊',
        },
        'view': {
            'pattern': 'views*.py',
            'class_suffix': 'View',
            'icon': '👁️',
        },
        'serializer': {
            'pattern': 'serializers.py',
            'class_suffix': 'Serializer',
            'icon': '📦',
        },
        'test': {
            'pattern': 'test*.py',
            'class_suffix': 'Test',
            'icon': '🧪',
        },
    }
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize the sync service.
        
        Args:
            project_root: Root directory of the project. Defaults to settings.BASE_DIR.
        """
        self.project_root = Path(project_root or settings.BASE_DIR)
        self._django_available = self._check_django()
        
    def _check_django(self) -> bool:
        """Check if Django models are available."""
        try:
            from bfagent_mcp.models_mcp import MCPDomainConfig
            return True
        except ImportError:
            logger.warning("MCP models not available - running in standalone mode")
            return False
    
    # =========================================================================
    # MAIN SYNC METHODS
    # =========================================================================
    
    def sync_all(self) -> Dict[str, SyncResult]:
        """
        Synchronize all MCP data.
        
        Returns:
            Dict with SyncResult for each category.
        """
        logger.info("Starting full MCP sync...")
        
        results = {}
        
        try:
            # 1. Sync domains first (others depend on this)
            results['domains'] = self.sync_domains()
            
            # 2. Sync protected paths
            results['protected_paths'] = self.sync_protected_paths()
            
            # 3. Sync components for each domain
            results['components'] = self.sync_components()
            
            # 4. Sync naming conventions
            results['conventions'] = self.sync_naming_conventions()
            
            logger.info(f"MCP sync completed: {results}")
            
        except Exception as e:
            logger.error(f"MCP sync failed: {e}", exc_info=True)
            results['error'] = str(e)
        
        return results
    
    @transaction.atomic
    def sync_domains(self) -> SyncResult:
        """
        Discover and sync domain configurations.
        
        Scans the project for Django apps and creates/updates
        MCPDomainConfig entries.
        """
        result = SyncResult()
        
        if not self._django_available:
            result.errors.append("Django models not available")
            return result
        
        from bfagent_mcp.models_mcp import MCPDomainConfig, MCPRiskLevel
        from bfagent_mcp.models import Domain
        
        logger.info("Syncing domains...")
        
        # Discover domains from filesystem
        discovered_domains = self._discover_domains()
        
        # Get or create default risk level
        default_risk, _ = MCPRiskLevel.objects.get_or_create(
            name='medium',
            defaults={
                'display_name': 'Medium',
                'severity_score': 50,
                'requires_approval': False,
                'requires_backup': True,
                'color': 'warning',
                'icon': '🟡',
            }
        )
        
        existing_domain_ids = set(
            MCPDomainConfig.objects.values_list('domain__domain_id', flat=True)
        )
        
        for domain_info in discovered_domains:
            try:
                # Get or create the base Domain
                domain, created = Domain.objects.get_or_create(
                    domain_id=domain_info.domain_id,
                    defaults={
                        'name': domain_info.domain_id,
                        'display_name': domain_info.display_name,
                        'is_active': True,
                    }
                )
                
                # Get or create MCP config
                config, config_created = MCPDomainConfig.objects.get_or_create(
                    domain=domain,
                    defaults={
                        'base_path': domain_info.base_path,
                        'risk_level': default_risk,
                        'is_active': True,
                        'allows_refactoring': True,
                    }
                )
                
                if config_created:
                    result.created += 1
                    logger.debug(f"Created domain config: {domain_info.domain_id}")
                else:
                    # Update base_path if changed
                    if config.base_path != domain_info.base_path:
                        config.base_path = domain_info.base_path
                        config.save(update_fields=['base_path'])
                        result.updated += 1
                    else:
                        result.skipped += 1
                
                result.synced += 1
                
            except Exception as e:
                logger.error(f"Failed to sync domain {domain_info.domain_id}: {e}")
                result.errors.append(f"{domain_info.domain_id}: {str(e)}")
        
        logger.info(f"Domains synced: {result.synced} ({result.created} new, {result.updated} updated)")
        
        return result
    
    @transaction.atomic
    def sync_protected_paths(self) -> SyncResult:
        """
        Sync protected path patterns.
        
        Creates default protected paths if they don't exist.
        """
        result = SyncResult()
        
        if not self._django_available:
            result.errors.append("Django models not available")
            return result
        
        from bfagent_mcp.models_mcp import (
            MCPProtectedPath,
            MCPProtectionLevel,
            MCPPathCategory,
        )
        
        logger.info("Syncing protected paths...")
        
        # Ensure protection levels exist
        protection_levels = {}
        for level_name, display, score in [
            ('absolute', 'Absolute Protection', 100),
            ('review', 'Requires Review', 75),
            ('warn', 'Warning Only', 50),
            ('none', 'No Protection', 0),
        ]:
            level, _ = MCPProtectionLevel.objects.get_or_create(
                name=level_name,
                defaults={
                    'display_name': display,
                    'severity_score': score,
                    'color': 'danger' if score >= 75 else 'warning' if score >= 50 else 'secondary',
                }
            )
            protection_levels[level_name] = level
        
        # Ensure categories exist
        categories = {}
        for cat_name, display, icon, order in [
            ('mcp', 'MCP Package', '🔧', 1),
            ('config', 'Configuration', '⚙️', 2),
            ('security', 'Security', '🔐', 3),
            ('infrastructure', 'Infrastructure', '🏗️', 4),
            ('migrations', 'Migrations', '📦', 5),
        ]:
            cat, _ = MCPPathCategory.objects.get_or_create(
                name=cat_name,
                defaults={
                    'display_name': display,
                    'icon': icon,
                    'order': order,
                }
            )
            categories[cat_name] = cat
        
        # Sync default protected patterns
        existing_patterns = set(
            MCPProtectedPath.objects.values_list('path_pattern', flat=True)
        )
        
        for pattern, level_name, reason, cat_name in self.DEFAULT_PROTECTED_PATTERNS:
            if pattern in existing_patterns:
                result.skipped += 1
                continue
            
            try:
                MCPProtectedPath.objects.create(
                    path_pattern=pattern,
                    protection_level=protection_levels.get(level_name, protection_levels['warn']),
                    category=categories.get(cat_name, categories['infrastructure']),
                    reason=reason,
                    is_regex='**' in pattern or '*' in pattern,
                    is_active=True,
                )
                result.created += 1
                result.synced += 1
                
            except Exception as e:
                logger.error(f"Failed to create protected path {pattern}: {e}")
                result.errors.append(f"{pattern}: {str(e)}")
        
        logger.info(f"Protected paths synced: {result.synced} ({result.created} new)")
        
        return result
    
    @transaction.atomic
    def sync_components(self) -> SyncResult:
        """
        Scan domains and sync their components.
        
        Detects handlers, services, models, etc. in each domain.
        """
        result = SyncResult()
        
        if not self._django_available:
            result.errors.append("Django models not available")
            return result
        
        from bfagent_mcp.models_mcp import (
            MCPDomainConfig,
            MCPDomainComponent,
            MCPComponentType,
        )
        
        logger.info("Syncing components...")
        
        # Ensure component types exist
        component_types = {}
        for type_name, info in self.COMPONENT_PATTERNS.items():
            ct, _ = MCPComponentType.objects.get_or_create(
                name=type_name,
                defaults={
                    'display_name': type_name.title(),
                    'file_pattern': info['pattern'],
                    'class_suffix': info.get('class_suffix', ''),
                    'icon': info['icon'],
                    'is_refactorable': type_name not in ['model', 'test'],
                }
            )
            component_types[type_name] = ct
        
        # Scan each domain for components
        domain_configs = MCPDomainConfig.objects.filter(is_active=True)
        
        for config in domain_configs:
            domain_path = self.project_root / config.base_path
            
            if not domain_path.exists():
                logger.warning(f"Domain path not found: {domain_path}")
                continue
            
            # Detect components
            for type_name, info in self.COMPONENT_PATTERNS.items():
                pattern = info['pattern']
                files = list(domain_path.rglob(pattern))
                
                for file_path in files:
                    relative_path = file_path.relative_to(self.project_root)
                    component_name = file_path.stem
                    
                    # Create or update component
                    comp, created = MCPDomainComponent.objects.get_or_create(
                        domain_config=config,
                        component_type=component_types[type_name],
                        name=component_name,
                        defaults={
                            'file_path': str(relative_path),
                            'is_active': True,
                            'is_refactorable': type_name not in ['model', 'test'],
                        }
                    )
                    
                    if created:
                        result.created += 1
                    else:
                        # Update file path if changed
                        if comp.file_path != str(relative_path):
                            comp.file_path = str(relative_path)
                            comp.save(update_fields=['file_path'])
                            result.updated += 1
                    
                    result.synced += 1
        
        logger.info(f"Components synced: {result.synced} ({result.created} new, {result.updated} updated)")
        
        return result
    
    @transaction.atomic
    def sync_naming_conventions(self) -> SyncResult:
        """
        Sync naming convention defaults.
        """
        result = SyncResult()
        
        if not self._django_available:
            result.errors.append("Django models not available")
            return result
        
        from bfagent_mcp.models_naming import TableNamingConvention
        
        logger.info("Syncing naming conventions...")
        
        # Default conventions
        default_conventions = [
            {
                'app_label': '*',
                'component_type': 'handler',
                'file_pattern': '{model}_handler.py',
                'class_pattern': '{Model}Handler',
                'suffix': 'Handler',
                'enforce_convention': True,
                'description': 'Standard handler naming pattern',
                'example': 'chapter_handler.py → ChapterHandler',
            },
            {
                'app_label': '*',
                'component_type': 'service',
                'file_pattern': '{model}_service.py',
                'class_pattern': '{Model}Service',
                'suffix': 'Service',
                'enforce_convention': True,
                'description': 'Standard service naming pattern',
                'example': 'book_service.py → BookService',
            },
            {
                'app_label': '*',
                'component_type': 'repository',
                'file_pattern': '{model}_repository.py',
                'class_pattern': '{Model}Repository',
                'suffix': 'Repository',
                'enforce_convention': False,
                'description': 'Repository pattern naming',
                'example': 'user_repository.py → UserRepository',
            },
            {
                'app_label': '*',
                'component_type': 'view',
                'file_pattern': 'views_{feature}.py',
                'class_pattern': '{Feature}View',
                'suffix': 'View',
                'enforce_convention': False,
                'description': 'View naming pattern',
                'example': 'views_mcp.py → MCPDashboardView',
            },
        ]
        
        for conv_data in default_conventions:
            app_label = conv_data.pop('app_label')
            component_type = conv_data.pop('component_type')
            
            conv, created = TableNamingConvention.objects.get_or_create(
                app_label=app_label,
                component_type=component_type,
                defaults={**conv_data, 'is_active': True}
            )
            
            if created:
                result.created += 1
            else:
                result.skipped += 1
            
            result.synced += 1
        
        logger.info(f"Naming conventions synced: {result.synced} ({result.created} new)")
        
        return result
    
    # =========================================================================
    # DISCOVERY METHODS
    # =========================================================================
    
    def _discover_domains(self) -> List[DomainInfo]:
        """
        Discover Django apps/domains in the project.
        
        Returns:
            List of DomainInfo objects.
        """
        domains = []
        
        for search_path in self.DEFAULT_DOMAIN_PATHS:
            path = self.project_root / search_path
            
            if not path.exists():
                continue
            
            # Look for directories with __init__.py (Python packages)
            for item in path.iterdir():
                if not item.is_dir():
                    continue
                
                init_file = item / '__init__.py'
                if not init_file.exists():
                    continue
                
                # Check if it looks like a Django app
                has_models = (item / 'models.py').exists() or (item / 'models').is_dir()
                has_views = (item / 'views.py').exists() or (item / 'views').is_dir()
                has_handlers = any(item.glob('*_handler.py')) or (item / 'handlers').is_dir()
                
                if has_models or has_views or has_handlers:
                    domain_id = item.name
                    display_name = domain_id.replace('_', ' ').title()
                    base_path = str(item.relative_to(self.project_root))
                    
                    # Count components
                    handler_count = len(list(item.rglob('*_handler.py')))
                    service_count = len(list(item.rglob('*_service.py')))
                    
                    domains.append(DomainInfo(
                        domain_id=domain_id,
                        display_name=display_name,
                        base_path=base_path,
                        has_handlers=has_handlers,
                        has_services=any(item.glob('*_service.py')),
                        has_models=has_models,
                        has_tests=(item / 'tests').is_dir() or any(item.glob('test*.py')),
                        handler_count=handler_count,
                        service_count=service_count,
                    ))
        
        logger.debug(f"Discovered {len(domains)} domains")
        return domains
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def check_path_protection(self, file_path: str) -> Dict[str, Any]:
        """
        Check if a file path is protected.
        
        Args:
            file_path: Relative path to check.
            
        Returns:
            Dict with protection status and details.
        """
        if not self._django_available:
            return {'protected': False, 'reason': 'Models not available'}
        
        from bfagent_mcp.models_mcp import MCPProtectedPath
        
        # Normalize path
        file_path = file_path.replace('\\', '/')
        
        # Check against all active patterns
        protected_paths = MCPProtectedPath.objects.filter(is_active=True)
        
        for pp in protected_paths:
            pattern = pp.path_pattern
            
            if pp.is_regex:
                # Use fnmatch for glob patterns
                if fnmatch.fnmatch(file_path, pattern):
                    return {
                        'protected': True,
                        'pattern': pattern,
                        'level': pp.protection_level.name,
                        'severity': pp.protection_level.severity_score,
                        'reason': pp.reason,
                        'category': pp.category.name if pp.category else None,
                    }
            else:
                # Exact match
                if file_path == pattern:
                    return {
                        'protected': True,
                        'pattern': pattern,
                        'level': pp.protection_level.name,
                        'severity': pp.protection_level.severity_score,
                        'reason': pp.reason,
                        'category': pp.category.name if pp.category else None,
                    }
        
        return {'protected': False}
    
    def get_domain_stats(self) -> Dict[str, Any]:
        """
        Get statistics about synced domains.
        """
        if not self._django_available:
            return {'error': 'Models not available'}
        
        from bfagent_mcp.models_mcp import (
            MCPDomainConfig,
            MCPProtectedPath,
            MCPDomainComponent,
        )
        
        return {
            'total_domains': MCPDomainConfig.objects.filter(is_active=True).count(),
            'refactorable_domains': MCPDomainConfig.objects.filter(
                is_active=True, allows_refactoring=True
            ).count(),
            'protected_paths': MCPProtectedPath.objects.filter(is_active=True).count(),
            'total_components': MCPDomainComponent.objects.filter(is_active=True).count(),
        }
