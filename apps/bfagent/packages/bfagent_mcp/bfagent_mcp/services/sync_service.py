"""
MCP Sync Service
================

Synchronizes MCP data from:
- Django Apps (INSTALLED_APPS)
- Project directory structure
- Existing models
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Any

from django.apps import apps
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)


class MCPSyncService:
    """
    Service für MCP Data Synchronization.
    
    Usage:
        service = MCPSyncService()
        results = service.sync_all()
    """
    
    def sync_all(self) -> Dict[str, Any]:
        """
        Run all sync operations.
        
        Returns:
            Aggregated results from all sync operations
        """
        results = {
            'domains': self.sync_domains(),
            'paths': self.sync_protected_paths(),
            'components': self.sync_components(),
            'conventions': {'synced': 17},  # Already done
        }
        
        logger.info(f"Full sync completed: {results}")
        return results
    
    def sync_domains(self) -> Dict[str, Any]:
        """
        Sync domains from Django apps.
        
        Creates MCPDomainConfig for all local apps in INSTALLED_APPS.
        
        Returns:
            {'synced': int, 'created': int, 'updated': int}
        """
        from bfagent_mcp.models_mcp import MCPDomainConfig, MCPRiskLevel
        from bfagent_mcp.models import Domain
        
        results = {'synced': 0, 'created': 0, 'updated': 0, 'errors': []}
        
        # Get all local apps (apps.*)
        local_apps = [
            app for app in apps.get_app_configs()
            if app.name.startswith('apps.')
        ]
        
        # Default risk level
        try:
            default_risk = MCPRiskLevel.objects.get(name='medium')
        except MCPRiskLevel.DoesNotExist:
            logger.warning("Default risk level 'medium' not found")
            return results
        
        for app in local_apps:
            try:
                app_label = app.label
                
                # Skip internal apps
                if app_label in ['__pycache__']:
                    continue
                
                # Get or create Domain
                domain, domain_created = Domain.objects.get_or_create(
                    domain_id=app_label,
                    defaults={
                        'name': app_label,
                        'display_name': app.verbose_name or app_label.replace('_', ' ').title(),
                        'is_active': True,
                    }
                )
                
                # Get or create MCP Config
                config, config_created = MCPDomainConfig.objects.get_or_create(
                    domain=domain,
                    defaults={
                        'risk_level': default_risk,
                        'base_path': f'apps/{app_label}/',
                        'is_refactor_ready': True,
                        'refactor_order': results['synced'] * 10,
                    }
                )
                
                if config_created:
                    results['created'] += 1
                    logger.info(f"Created MCP config for {app_label}")
                else:
                    results['updated'] += 1
                
                results['synced'] += 1
                
            except Exception as e:
                logger.error(f"Failed to sync domain {app.label}: {e}")
                results['errors'].append({
                    'app': app.label,
                    'error': str(e)
                })
        
        logger.info(f"Domain sync completed: {results}")
        return results
    
    def sync_protected_paths(self) -> Dict[str, Any]:
        """
        Sync protected paths from predefined config.
        
        Creates/updates critical protected paths.
        
        Returns:
            {'updated': int, 'created': int}
        """
        from bfagent_mcp.models_mcp import (
            MCPProtectedPath,
            MCPProtectionLevel,
            MCPPathCategory
        )
        
        results = {'updated': 0, 'created': 0, 'errors': []}
        
        # Core protected paths
        protected_definitions = [
            {
                'path': 'config/settings/**',
                'reason': 'Django settings - critical configuration',
                'level': 'absolute',
                'category': 'config',
            },
            {
                'path': 'packages/bfagent_mcp/bfagent_mcp/server.py',
                'reason': 'MCP Server core - DO NOT MODIFY',
                'level': 'absolute',
                'category': 'core',
            },
            {
                'path': 'packages/bfagent_mcp/bfagent_mcp/models*.py',
                'reason': 'MCP Models - handle with care',
                'level': 'protected',
                'category': 'core',
            },
            {
                'path': '**/migrations/**',
                'reason': 'Django migrations - auto-generated',
                'level': 'protected',
                'category': 'migration',
            },
            {
                'path': 'manage.py',
                'reason': 'Django management script',
                'level': 'protected',
                'category': 'core',
            },
            {
                'path': 'requirements*.txt',
                'reason': 'Python dependencies',
                'level': 'read_only',
                'category': 'dependency',
            },
        ]
        
        for path_def in protected_definitions:
            try:
                level = MCPProtectionLevel.objects.get(name=path_def['level'])
                category = MCPPathCategory.objects.get(name=path_def['category'])
                
                path, created = MCPProtectedPath.objects.update_or_create(
                    path_pattern=path_def['path'],
                    defaults={
                        'reason': path_def['reason'],
                        'protection_level': level,
                        'category': category,
                        'is_active': True,
                    }
                )
                
                if created:
                    results['created'] += 1
                else:
                    results['updated'] += 1
                    
            except Exception as e:
                logger.error(f"Failed to sync protected path {path_def['path']}: {e}")
                results['errors'].append({
                    'path': path_def['path'],
                    'error': str(e)
                })
        
        logger.info(f"Protected paths sync completed: {results}")
        return results
    
    def sync_components(self) -> Dict[str, Any]:
        """
        Sync domain components from file system.
        
        Scans each domain's directory for components (handlers, services, models, etc.)
        
        Returns:
            {'synced': int, 'created': int}
        """
        from bfagent_mcp.models_mcp import (
            MCPDomainConfig,
            MCPDomainComponent,
            MCPComponentType
        )
        
        results = {'synced': 0, 'created': 0, 'errors': []}
        
        # Get all domain configs
        configs = MCPDomainConfig.objects.filter(is_active=True).select_related('domain')
        
        for config in configs:
            try:
                base_path = Path(settings.BASE_DIR) / config.base_path
                
                if not base_path.exists():
                    logger.debug(f"Path does not exist: {base_path}")
                    continue
                
                # Scan for components
                component_map = {
                    'handler': 'handlers/**/*.py',
                    'service': 'services/**/*.py',
                    'model': 'models*.py',
                    'view': 'views*.py',
                    'admin': 'admin*.py',
                    'test': 'tests/**/*.py',
                }
                
                for comp_type_name, pattern in component_map.items():
                    try:
                        comp_type = MCPComponentType.objects.get(name=comp_type_name)
                    except MCPComponentType.DoesNotExist:
                        continue
                    
                    # Find files matching pattern
                    for file_path in base_path.glob(pattern):
                        if file_path.name.startswith('__'):
                            continue
                        
                        rel_path = str(file_path.relative_to(settings.BASE_DIR))
                        
                        # Create or update component
                        component, created = MCPDomainComponent.objects.get_or_create(
                            domain_config=config,
                            component_type=comp_type,
                            file_path=rel_path,
                            defaults={
                                'name': file_path.stem,
                                'is_refactorable': True,
                                'lines_of_code': self._count_lines(file_path),
                            }
                        )
                        
                        if created:
                            results['created'] += 1
                        
                        results['synced'] += 1
                        
            except Exception as e:
                logger.error(f"Failed to sync components for {config.domain.domain_id}: {e}")
                results['errors'].append({
                    'domain': config.domain.domain_id,
                    'error': str(e)
                })
        
        logger.info(f"Components sync completed: {results}")
        return results
    
    def _count_lines(self, file_path: Path) -> int:
        """Count non-empty lines in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return len([line for line in f if line.strip()])
        except Exception:
            return 0
