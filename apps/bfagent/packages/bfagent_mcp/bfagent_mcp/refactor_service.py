"""
BF Agent MCP Server - Refactoring Service
==========================================

Service Layer für MCP Refactoring Tools.

Provides:
- Domain refactoring options
- Path protection checking
- Session management
- Naming conventions
"""

from __future__ import annotations

import fnmatch
from datetime import datetime
from typing import Any, Optional

from asgiref.sync import sync_to_async


class MCPRefactorService:
    """
    Service für Refactoring-Operationen.
    
    Wird von MCP Tools aufgerufen um:
    - Refactoring-Optionen abzufragen
    - Pfad-Schutz zu prüfen
    - Sessions zu verwalten
    - Refactoring execution (für Celery Tasks)
    """
    
    def __init__(self, session=None):
        self._django_available = self._check_django()
        self.session = session
    
    def _check_django(self) -> bool:
        """Check if Django is properly configured."""
        try:
            import django
            django.setup()
            return True
        except Exception:
            return False
    
    # =========================================================================
    # REFACTOR OPTIONS
    # =========================================================================
    
    async def get_refactor_options(
        self,
        domain_id: str,
        response_format: str = "markdown"
    ) -> str:
        """
        Get refactoring options for a domain.
        
        Returns available components, risk level, and constraints.
        """
        if not self._django_available:
            return self._get_mock_refactor_options(domain_id, response_format)
        
        from bfagent_mcp.models_mcp import MCPDomainConfig, MCPProtectedPath
        
        try:
            config = await sync_to_async(
                lambda: MCPDomainConfig.objects.select_related(
                    'domain', 'risk_level'
                ).prefetch_related(
                    'components__component_type',
                    'depends_on'
                ).get(domain__domain_id=domain_id)
            )()
        except MCPDomainConfig.DoesNotExist:
            return f"❌ No refactor config found for domain: `{domain_id}`"
        
        # Get components
        components = await sync_to_async(
            lambda: list(config.components.filter(
                is_active=True, is_refactorable=True
            ).select_related('component_type'))
        )()
        
        # Get dependencies
        deps = await sync_to_async(
            lambda: list(config.depends_on.values_list('domain_id', flat=True))
        )()
        
        # Get protected paths for this domain
        protected = await self._get_protected_paths_for_domain(domain_id)
        
        if response_format == "json":
            import json
            return json.dumps({
                "domain_id": domain_id,
                "base_path": config.base_path,
                "risk_level": config.risk_level.name,
                "risk_display": config.risk_level.display_name,
                "severity_score": config.risk_level.severity_score,
                "requires_approval": config.risk_level.requires_approval,
                "requires_backup": config.risk_level.requires_backup,
                "is_protected": config.is_protected,
                "is_refactor_ready": config.is_refactor_ready,
                "refactor_order": config.refactor_order,
                "depends_on": deps,
                "components": [
                    {
                        "name": c.component_type.name,
                        "display_name": c.component_type.display_name,
                        "path": c.get_effective_path(),
                        "icon": c.component_type.icon,
                    }
                    for c in components
                ],
                "protected_paths": protected,
            }, indent=2)
        
        # Markdown format
        risk_icon = config.risk_level.icon or "⚪"
        status_icon = "🔒" if config.is_protected else ("✓" if config.is_refactor_ready else "○")
        
        output = f"""# Refactor Options: {domain_id}

**Status:** {status_icon} {"PROTECTED" if config.is_protected else ("Ready" if config.is_refactor_ready else "Not Ready")}
**Base Path:** `{config.base_path}`
**Risk:** {risk_icon} {config.risk_level.display_name} (Score: {config.risk_level.severity_score}/100)
**Order:** #{config.refactor_order}

"""
        
        if config.is_protected:
            output += """⚠️ **This domain is PROTECTED and cannot be refactored!**

"""
        
        if config.risk_level.requires_approval:
            output += """⚠️ **Requires manual approval before refactoring.**

"""
        
        if deps:
            output += f"""## Dependencies

Refactor these first: {', '.join(f'`{d}`' for d in deps)}

"""
        
        output += """## Available Components

| Component | Path | Icon |
|-----------|------|------|
"""
        for c in components:
            output += f"| {c.component_type.display_name} | `{c.get_effective_path()}` | {c.component_type.icon} |\n"
        
        if protected:
            output += f"""
## Protected Paths (DO NOT MODIFY)

"""
            for p in protected[:5]:
                output += f"- `{p['pattern']}` - {p['reason'][:50]}...\n"
            if len(protected) > 5:
                output += f"\n_...and {len(protected) - 5} more_\n"
        
        if config.risk_notes:
            output += f"""
## Notes

{config.risk_notes}
"""
        
        return output
    
    async def _get_protected_paths_for_domain(self, domain_id: str) -> list[dict]:
        """Get protected paths relevant for a domain."""
        from bfagent_mcp.models_mcp import MCPProtectedPath
        
        paths = await sync_to_async(
            lambda: list(MCPProtectedPath.objects.filter(
                is_active=True
            ).select_related('protection_level', 'category').values(
                'path_pattern', 'reason', 
                'protection_level__name', 'protection_level__display_name',
                'category__name'
            ))
        )()
        
        return [
            {
                "pattern": p['path_pattern'],
                "reason": p['reason'],
                "level": p['protection_level__name'],
                "category": p['category__name'],
            }
            for p in paths
        ]
    
    def _get_mock_refactor_options(self, domain_id: str, response_format: str) -> str:
        """Mock response when Django not available."""
        if response_format == "json":
            import json
            return json.dumps({
                "domain_id": domain_id,
                "error": "Django not configured - using mock data",
                "components": ["handler", "service", "model"],
            })
        return f"""# Refactor Options: {domain_id}

⚠️ **Django not configured** - Mock data shown.

## Components
- handlers/
- services/
- models.py
"""
    
    # =========================================================================
    # PATH PROTECTION
    # =========================================================================
    
    async def check_path_protection(
        self,
        file_path: str,
        response_format: str = "markdown"
    ) -> str:
        """
        Check if a file path is protected.
        
        Returns protection status and reason.
        """
        if not self._django_available:
            return self._get_mock_protection(file_path, response_format)
        
        from bfagent_mcp.models_mcp import MCPProtectedPath
        
        # Normalize path
        file_path = file_path.replace("\\", "/").strip("/")
        
        # Get all active protected paths
        protected_paths = await sync_to_async(
            lambda: list(MCPProtectedPath.objects.filter(
                is_active=True
            ).select_related('protection_level', 'category'))
        )()
        
        # Check each pattern
        matches = []
        for pp in protected_paths:
            pattern = pp.path_pattern.strip("/")
            
            # Handle glob patterns
            if fnmatch.fnmatch(file_path, pattern):
                matches.append(pp)
            # Handle ** patterns
            elif "**" in pattern:
                base_pattern = pattern.replace("**", "")
                if file_path.startswith(base_pattern.rstrip("/")):
                    matches.append(pp)
        
        if response_format == "json":
            import json
            if matches:
                return json.dumps({
                    "path": file_path,
                    "is_protected": True,
                    "matches": [
                        {
                            "pattern": m.path_pattern,
                            "level": m.protection_level.name,
                            "blocks_refactoring": m.protection_level.blocks_refactoring,
                            "reason": m.reason,
                            "category": m.category.name,
                        }
                        for m in matches
                    ]
                }, indent=2)
            return json.dumps({
                "path": file_path,
                "is_protected": False,
                "matches": []
            })
        
        # Markdown
        if not matches:
            return f"""# Path Check: `{file_path}`

✅ **Not Protected** - Safe to modify.
"""
        
        most_restrictive = max(matches, key=lambda m: m.protection_level.severity_score)
        blocks = most_restrictive.protection_level.blocks_refactoring
        
        output = f"""# Path Check: `{file_path}`

{"🔒 **BLOCKED**" if blocks else "⚠️ **WARNING**"} - This path is protected!

## Matching Rules

"""
        for m in matches:
            icon = "🔒" if m.protection_level.blocks_refactoring else "⚠️"
            output += f"""### {icon} {m.protection_level.display_name}

- **Pattern:** `{m.path_pattern}`
- **Category:** {m.category.display_name}
- **Reason:** {m.reason}

"""
        
        if blocks:
            output += """## ❌ Action Required

**DO NOT MODIFY this file!** It is absolutely protected.
"""
        else:
            output += """## ⚠️ Proceed with Caution

You may modify this file, but please:
1. Create a backup first
2. Review changes carefully
3. Test thoroughly
"""
        
        return output
    
    def _get_mock_protection(self, file_path: str, response_format: str) -> str:
        """Mock protection check."""
        # Simple mock rules
        protected_patterns = [
            "packages/bfagent_mcp/**",
            ".env*",
            "manage.py",
        ]
        
        is_protected = any(
            fnmatch.fnmatch(file_path, p.replace("**", "*")) 
            for p in protected_patterns
        )
        
        if response_format == "json":
            import json
            return json.dumps({
                "path": file_path,
                "is_protected": is_protected,
                "note": "Mock data - Django not configured"
            })
        
        if is_protected:
            return f"🔒 **PROTECTED:** `{file_path}` (mock check)"
        return f"✅ **OK:** `{file_path}` (mock check)"
    
    # =========================================================================
    # NAMING CONVENTIONS
    # =========================================================================
    
    async def get_naming_convention(
        self,
        app_label: str,
        response_format: str = "markdown"
    ) -> str:
        """
        Get naming conventions for an app/domain.
        """
        if not self._django_available:
            return self._get_mock_naming(app_label, response_format)
        
        from bfagent_mcp.models_naming import TableNamingConvention
        
        try:
            convention = await sync_to_async(
                lambda: TableNamingConvention.objects.get(
                    app_label=app_label, is_active=True
                )
            )()
        except TableNamingConvention.DoesNotExist:
            return f"❌ No naming convention found for: `{app_label}`"
        
        if response_format == "json":
            import json
            return json.dumps({
                "app_label": convention.app_label,
                "display_name": convention.display_name,
                "table_prefix": convention.table_prefix,
                "class_prefix": convention.class_prefix,
                "table_pattern": convention.table_pattern,
                "class_pattern": convention.class_pattern,
                "file_pattern": convention.file_pattern,
                "examples": {
                    "tables": convention.example_tables,
                    "classes": convention.example_classes,
                }
            }, indent=2)
        
        output = f"""# Naming Convention: {convention.display_name}

**App Label:** `{convention.app_label}`

## Prefixes

| Type | Prefix | Pattern |
|------|--------|---------|
| Table | `{convention.table_prefix}` | `{convention.table_pattern}` |
| Class | `{convention.class_prefix}` | `{convention.class_pattern}` |
| File | - | `{convention.file_pattern}` |

## Examples

**Tables:**
"""
        for t in convention.example_tables[:5]:
            output += f"- `{t}`\n"
        
        output += "\n**Classes:**\n"
        for c in convention.example_classes[:5]:
            output += f"- `{c}`\n"
        
        if convention.description:
            output += f"\n## Description\n\n{convention.description}\n"
        
        return output
    
    async def list_naming_conventions(
        self,
        response_format: str = "markdown"
    ) -> str:
        """List all naming conventions."""
        if not self._django_available:
            return "Django not configured"
        
        from bfagent_mcp.models_naming import TableNamingConvention
        
        conventions = await sync_to_async(
            lambda: list(TableNamingConvention.objects.filter(
                is_active=True
            ).order_by('app_label'))
        )()
        
        if response_format == "json":
            import json
            return json.dumps([
                {
                    "app_label": c.app_label,
                    "display_name": c.display_name,
                    "table_prefix": c.table_prefix,
                    "class_prefix": c.class_prefix,
                }
                for c in conventions
            ], indent=2)
        
        output = """# Naming Conventions

| App | Display Name | Table Prefix | Class Prefix |
|-----|--------------|--------------|--------------|
"""
        for c in conventions:
            output += f"| `{c.app_label}` | {c.display_name} | `{c.table_prefix}` | `{c.class_prefix}` |\n"
        
        return output
    
    def _get_mock_naming(self, app_label: str, response_format: str) -> str:
        """Mock naming convention."""
        mock_data = {
            "core": ("core_", "Core"),
            "bfagent_mcp": ("mcp_", "MCP"),
            "books": ("books_", "Books"),
        }
        
        if app_label in mock_data:
            prefix, cls = mock_data[app_label]
            if response_format == "json":
                import json
                return json.dumps({
                    "app_label": app_label,
                    "table_prefix": prefix,
                    "class_prefix": cls,
                    "note": "Mock data"
                })
            return f"**{app_label}:** Tables=`{prefix}*`, Classes=`{cls}*`"
        
        return f"❌ Unknown app: `{app_label}`"
    
    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================
    
    async def start_refactor_session(
        self,
        domain_id: str,
        components: list[str],
        triggered_by: str = "windsurf"
    ) -> str:
        """
        Start a new refactoring session.
        
        Returns session ID for tracking.
        """
        if not self._django_available:
            return '{"session_id": "mock-session", "status": "mock"}'
        
        from bfagent_mcp.models_mcp import (
            MCPDomainConfig, MCPRefactorSession, MCPComponentType
        )
        from django.utils import timezone
        
        try:
            config = await sync_to_async(
                lambda: MCPDomainConfig.objects.select_related('domain').get(
                    domain__domain_id=domain_id
                )
            )()
        except MCPDomainConfig.DoesNotExist:
            return f'{{"error": "Domain not found: {domain_id}"}}'
        
        if config.is_protected:
            return f'{{"error": "Domain is protected: {domain_id}"}}'
        
        # Create session
        session = await sync_to_async(MCPRefactorSession.objects.create)(
            domain_config=config,
            started_at=timezone.now(),
            status='in_progress',
            triggered_by=triggered_by,
        )
        
        # Add components
        if components:
            comp_types = await sync_to_async(
                lambda: list(MCPComponentType.objects.filter(name__in=components))
            )()
            await sync_to_async(session.components.set)(comp_types)
        
        import json
        return json.dumps({
            "session_id": session.id,
            "domain": domain_id,
            "components": components,
            "status": "in_progress",
            "started_at": session.started_at.isoformat(),
            "message": f"Refactoring session started for {domain_id}"
        }, indent=2)
    
    async def end_refactor_session(
        self,
        session_id: int,
        status: str = "completed",
        summary: str = "",
        files_changed: int = 0,
        lines_added: int = 0,
        lines_removed: int = 0,
    ) -> str:
        """
        End a refactoring session.
        """
        if not self._django_available:
            return '{"status": "mock-completed"}'
        
        from bfagent_mcp.models_mcp import MCPRefactorSession
        from django.utils import timezone
        
        try:
            session = await sync_to_async(
                MCPRefactorSession.objects.get
            )(id=session_id)
        except MCPRefactorSession.DoesNotExist:
            return f'{{"error": "Session not found: {session_id}"}}'
        
        session.status = status
        session.completed_at = timezone.now()
        session.summary = summary
        session.total_files_changed = files_changed
        session.total_lines_added = lines_added
        session.total_lines_removed = lines_removed
        
        await sync_to_async(session.save)()
        
        # Update domain config
        config = await sync_to_async(lambda: session.domain_config)()
        config.last_refactored_at = timezone.now()
        config.refactor_count += 1
        config.last_refactor_notes = summary
        await sync_to_async(config.save)()
        
        import json
        return json.dumps({
            "session_id": session_id,
            "status": status,
            "duration_seconds": session.duration_seconds,
            "files_changed": files_changed,
            "lines_added": lines_added,
            "lines_removed": lines_removed,
        }, indent=2)
    
    # =========================================================================
    # COMPONENT TYPES
    # =========================================================================
    
    async def list_component_types(
        self,
        response_format: str = "markdown"
    ) -> str:
        """List all available component types."""
        if not self._django_available:
            return "Django not configured"
        
        from bfagent_mcp.models_mcp import MCPComponentType
        
        types = await sync_to_async(
            lambda: list(MCPComponentType.objects.filter(
                is_active=True
            ).order_by('order'))
        )()
        
        if response_format == "json":
            import json
            return json.dumps([
                {
                    "name": t.name,
                    "display_name": t.display_name,
                    "icon": t.icon,
                    "path_pattern": t.default_path_pattern,
                    "supports_refactoring": t.supports_refactoring,
                }
                for t in types
            ], indent=2)
        
        output = """# Component Types

| Icon | Name | Path Pattern | Refactorable |
|------|------|--------------|--------------|
"""
        for t in types:
            refactor = "✓" if t.supports_refactoring else "✗"
            output += f"| {t.icon} | {t.display_name} | `{t.default_path_pattern}` | {refactor} |\n"
        
        return output
    
    # =========================================================================
    # REFACTORING EXECUTION (für Celery Tasks)
    # =========================================================================
    
    def create_backup(self) -> str:
        """
        Create backup of files before refactoring.
        
        Returns:
            Path to backup directory
        """
        import shutil
        from pathlib import Path
        from django.conf import settings
        from django.utils import timezone
        
        if not self.session:
            raise ValueError("Session required for backup")
        
        # Create backup directory
        backup_base = Path(settings.BASE_DIR) / '.backups' / 'mcp'
        backup_dir = backup_base / f"session_{self.session.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy files to backup
        base_path = Path(settings.BASE_DIR) / self.session.domain_config.base_path
        if base_path.exists():
            shutil.copytree(base_path, backup_dir / base_path.name, dirs_exist_ok=True)
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Backup created: {backup_dir}")
        
        return str(backup_dir)
    
    def analyze_files(self) -> list:
        """
        Analyze files in domain for refactoring.
        
        Returns:
            List of file info dicts
        """
        from pathlib import Path
        from django.conf import settings
        
        if not self.session:
            raise ValueError("Session required")
        
        files = []
        base_path = Path(settings.BASE_DIR) / self.session.domain_config.base_path
        
        if not base_path.exists():
            return files
        
        # Get selected component types
        selected_components = self.session.components_selected or ['handler', 'service', 'model']
        
        for component in selected_components:
            # Find files based on component type
            patterns = {
                'handler': 'handlers/**/*.py',
                'service': 'services/**/*.py',
                'model': 'models*.py',
                'view': 'views*.py',
                'admin': 'admin*.py',
            }
            
            pattern = patterns.get(component)
            if not pattern:
                continue
            
            for file_path in base_path.glob(pattern):
                if file_path.name.startswith('__'):
                    continue
                
                files.append({
                    'path': str(file_path.relative_to(settings.BASE_DIR)),
                    'component_type': component,
                    'size': file_path.stat().st_size,
                })
        
        return files
    
    def refactor_file(self, file_info: dict) -> dict:
        """
        Apply refactoring to a single file.
        
        Args:
            file_info: File information dict
        
        Returns:
            Change result dict
        """
        # TODO: Implement actual refactoring logic
        # For now, just placeholder for MVP
        return {
            'changed': False,
            'change_type': 'none',
            'lines_added': 0,
            'lines_removed': 0,
            'diff': '',
        }
    
    def validate_changes(self) -> dict:
        """
        Validate refactored code.
        
        Returns:
            {'valid': bool, 'errors': list}
        """
        # TODO: Run linting, tests, etc.
        # For MVP: Always valid
        return {'valid': True, 'errors': []}
    
    def rollback(self):
        """Rollback changes from backup."""
        import shutil
        from pathlib import Path
        from django.conf import settings
        import logging
        
        logger = logging.getLogger(__name__)
        
        if not self.session or not self.session.backup_path:
            raise ValueError("No backup to rollback")
        
        # Restore from backup
        backup_path = Path(self.session.backup_path)
        if not backup_path.exists():
            raise ValueError(f"Backup path does not exist: {backup_path}")
        
        # Get target path
        base_path = Path(settings.BASE_DIR) / self.session.domain_config.base_path
        
        # Remove current files
        if base_path.exists():
            shutil.rmtree(base_path)
        
        # Restore backup
        shutil.copytree(
            backup_path / base_path.name,
            base_path,
            dirs_exist_ok=True
        )
        
        logger.info(f"Rollback completed for session {self.session.id}")


# Singleton instance
_refactor_service: Optional[MCPRefactorService] = None


def get_refactor_service() -> MCPRefactorService:
    """Get or create refactor service instance."""
    global _refactor_service
    if _refactor_service is None:
        _refactor_service = MCPRefactorService()
    return _refactor_service
