"""
GenAgent Migration Manager - Feature 5: Migration System

Provides safe schema evolution and version migration for handlers.

Author: GenAgent Development Team
Created: 2025-01-19
"""

import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


logger = logging.getLogger(__name__)


class MigrationStatus(Enum):
    """Status of a migration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class MigrationError(Exception):
    """Raised when migration fails."""
    pass


@dataclass
class Migration:
    """
    Represents a single migration between versions.
    
    Attributes:
        id: Unique migration identifier
        from_version: Source version
        to_version: Target version
        description: Human-readable description
        migrate_func: Function to perform migration
        rollback_func: Optional function to rollback
        created_at: When migration was created
        status: Current migration status
    """
    
    id: str
    from_version: str
    to_version: str
    description: str
    migrate_func: Callable[[Dict[str, Any]], Dict[str, Any]]
    rollback_func: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    created_at: datetime = field(default_factory=datetime.now)
    status: MigrationStatus = MigrationStatus.PENDING
    
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the migration.
        
        Args:
            data: Data to migrate
            
        Returns:
            Migrated data
            
        Raises:
            MigrationError: If migration fails
        """
        try:
            logger.info(f"Executing migration {self.id}: {self.from_version} -> {self.to_version}")
            self.status = MigrationStatus.IN_PROGRESS
            
            result = self.migrate_func(data)
            
            self.status = MigrationStatus.COMPLETED
            logger.info(f"Migration {self.id} completed successfully")
            
            return result
            
        except Exception as e:
            self.status = MigrationStatus.FAILED
            error_msg = f"Migration {self.id} failed: {str(e)}"
            logger.error(error_msg)
            raise MigrationError(error_msg) from e
    
    def rollback(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rollback the migration.
        
        Args:
            data: Data to rollback
            
        Returns:
            Rolled back data
            
        Raises:
            MigrationError: If rollback not supported or fails
        """
        if self.rollback_func is None:
            raise MigrationError(f"Migration {self.id} does not support rollback")
        
        try:
            logger.info(f"Rolling back migration {self.id}")
            result = self.rollback_func(data)
            
            self.status = MigrationStatus.ROLLED_BACK
            logger.info(f"Migration {self.id} rolled back successfully")
            
            return result
            
        except Exception as e:
            error_msg = f"Rollback of migration {self.id} failed: {str(e)}"
            logger.error(error_msg)
            raise MigrationError(error_msg) from e


class MigrationManager:
    """
    Manages migrations between handler versions.
    
    Features:
    - Migration registration
    - Version path finding
    - Safe migration execution
    - Rollback support
    - Migration history tracking
    """
    
    def __init__(self):
        """Initialize the MigrationManager."""
        self._migrations: Dict[str, Migration] = {}
        self._version_graph: Dict[str, List[str]] = {}
        self._migration_history: List[Migration] = []
    
    def register_migration(self, migration: Migration) -> None:
        """
        Register a migration.
        
        Args:
            migration: Migration to register
            
        Raises:
            ValueError: If migration ID already exists
        """
        if migration.id in self._migrations:
            raise ValueError(f"Migration {migration.id} already registered")
        
        self._migrations[migration.id] = migration
        
        # Update version graph
        if migration.from_version not in self._version_graph:
            self._version_graph[migration.from_version] = []
        
        self._version_graph[migration.from_version].append(migration.to_version)
        
        logger.debug(f"Registered migration: {migration.id}")
    
    def get_migration_path(
        self,
        from_version: str,
        to_version: str
    ) -> List[Migration]:
        """
        Find migration path between versions.
        
        Args:
            from_version: Source version
            to_version: Target version
            
        Returns:
            List of migrations to apply in order
            
        Raises:
            MigrationError: If no path found
        """
        if from_version == to_version:
            return []
        
        # Simple BFS to find path
        visited = set()
        queue = [(from_version, [])]
        
        while queue:
            current_version, path = queue.pop(0)
            
            if current_version in visited:
                continue
            
            visited.add(current_version)
            
            if current_version == to_version:
                return path
            
            # Get next versions
            next_versions = self._version_graph.get(current_version, [])
            
            for next_version in next_versions:
                # Find migration
                migration = self._find_migration(current_version, next_version)
                if migration:
                    queue.append((next_version, path + [migration]))
        
        raise MigrationError(
            f"No migration path found from {from_version} to {to_version}"
        )
    
    def migrate(
        self,
        data: Dict[str, Any],
        from_version: str,
        to_version: str,
        safe_mode: bool = True
    ) -> Dict[str, Any]:
        """
        Migrate data from one version to another.
        
        Args:
            data: Data to migrate
            from_version: Source version
            to_version: Target version
            safe_mode: If True, rollback on failure
            
        Returns:
            Migrated data
            
        Raises:
            MigrationError: If migration fails
        """
        # Get migration path
        migrations = self.get_migration_path(from_version, to_version)
        
        if not migrations:
            logger.info(f"No migrations needed (already at version {to_version})")
            return data
        
        logger.info(
            f"Migrating from {from_version} to {to_version} "
            f"using {len(migrations)} migration(s)"
        )
        
        # Execute migrations
        migrated_data = data
        executed_migrations = []
        
        try:
            for migration in migrations:
                migrated_data = migration.execute(migrated_data)
                executed_migrations.append(migration)
                self._migration_history.append(migration)
            
            logger.info(f"Successfully migrated to version {to_version}")
            return migrated_data
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            
            if safe_mode and executed_migrations:
                logger.info("Safe mode enabled, attempting rollback...")
                
                try:
                    # Rollback in reverse order
                    for migration in reversed(executed_migrations):
                        migrated_data = migration.rollback(migrated_data)
                    
                    logger.info("Rollback successful")
                    
                except Exception as rollback_error:
                    logger.error(f"Rollback failed: {str(rollback_error)}")
                    raise MigrationError(
                        f"Migration and rollback both failed: {str(e)}, {str(rollback_error)}"
                    ) from e
            
            raise MigrationError(f"Migration failed: {str(e)}") from e
    
    def _find_migration(
        self,
        from_version: str,
        to_version: str
    ) -> Optional[Migration]:
        """Find migration between two versions."""
        for migration in self._migrations.values():
            if (migration.from_version == from_version and
                migration.to_version == to_version):
                return migration
        return None
    
    def get_migration_history(self) -> List[Dict[str, Any]]:
        """
        Get migration history.
        
        Returns:
            List of migration records
        """
        return [
            {
                "id": m.id,
                "from_version": m.from_version,
                "to_version": m.to_version,
                "description": m.description,
                "status": m.status.value,
                "created_at": m.created_at.isoformat()
            }
            for m in self._migration_history
        ]
    
    def get_migration_stats(self) -> Dict[str, Any]:
        """
        Get migration statistics.
        
        Returns:
            Dictionary with migration stats
        """
        total = len(self._migration_history)
        completed = sum(
            1 for m in self._migration_history
            if m.status == MigrationStatus.COMPLETED
        )
        failed = sum(
            1 for m in self._migration_history
            if m.status == MigrationStatus.FAILED
        )
        
        return {
            "total_migrations": total,
            "completed": completed,
            "failed": failed,
            "success_rate": (completed / total * 100) if total > 0 else 0.0,
            "registered_migrations": len(self._migrations),
            "available_versions": len(self._version_graph)
        }
    
    def clear_history(self) -> None:
        """Clear migration history."""
        self._migration_history.clear()
        logger.info("Migration history cleared")


# Global migration manager instance
_migration_manager = MigrationManager()


def get_migration_manager() -> MigrationManager:
    """
    Get the global MigrationManager instance.
    
    Returns:
        Global MigrationManager
    """
    return _migration_manager


# Helper functions for common migrations
def add_field_migration(field_name: str, default_value: Any) -> Callable:
    """
    Create migration function to add a field.
    
    Args:
        field_name: Name of field to add
        default_value: Default value for the field
        
    Returns:
        Migration function
    """
    def migrate(data: Dict[str, Any]) -> Dict[str, Any]:
        result = data.copy()
        if field_name not in result:
            result[field_name] = default_value
        return result
    
    return migrate


def remove_field_migration(field_name: str) -> Callable:
    """
    Create migration function to remove a field.
    
    Args:
        field_name: Name of field to remove
        
    Returns:
        Migration function
    """
    def migrate(data: Dict[str, Any]) -> Dict[str, Any]:
        result = data.copy()
        result.pop(field_name, None)
        return result
    
    return migrate


def rename_field_migration(old_name: str, new_name: str) -> Callable:
    """
    Create migration function to rename a field.
    
    Args:
        old_name: Current field name
        new_name: New field name
        
    Returns:
        Migration function
    """
    def migrate(data: Dict[str, Any]) -> Dict[str, Any]:
        result = data.copy()
        if old_name in result:
            result[new_name] = result.pop(old_name)
        return result
    
    return migrate


def transform_field_migration(
    field_name: str,
    transform_func: Callable[[Any], Any]
) -> Callable:
    """
    Create migration function to transform a field value.
    
    Args:
        field_name: Name of field to transform
        transform_func: Function to transform the value
        
    Returns:
        Migration function
    """
    def migrate(data: Dict[str, Any]) -> Dict[str, Any]:
        result = data.copy()
        if field_name in result:
            result[field_name] = transform_func(result[field_name])
        return result
    
    return migrate
