"""
Tests for GenAgent Migration Manager - Feature 5: Migration System

Author: GenAgent Development Team
Created: 2025-01-19
"""

import pytest
from apps.genagent.core.migration_manager import (
    Migration,
    MigrationManager,
    MigrationStatus,
    MigrationError,
    get_migration_manager,
    add_field_migration,
    remove_field_migration,
    rename_field_migration,
    transform_field_migration
)


class TestMigration:
    """Test suite for Migration dataclass."""
    
    def test_create_migration(self):
        """Test creating a migration."""
        def migrate_func(data):
            return {**data, "new_field": "value"}
        
        migration = Migration(
            id="test_migration_1",
            from_version="1.0.0",
            to_version="1.1.0",
            description="Add new field",
            migrate_func=migrate_func
        )
        
        assert migration.id == "test_migration_1"
        assert migration.from_version == "1.0.0"
        assert migration.to_version == "1.1.0"
        assert migration.status == MigrationStatus.PENDING
    
    def test_execute_migration_success(self):
        """Test successful migration execution."""
        def migrate_func(data):
            return {**data, "migrated": True}
        
        migration = Migration(
            id="test_exec",
            from_version="1.0.0",
            to_version="1.1.0",
            description="Test migration",
            migrate_func=migrate_func
        )
        
        data = {"original": "value"}
        result = migration.execute(data)
        
        assert result["original"] == "value"
        assert result["migrated"] is True
        assert migration.status == MigrationStatus.COMPLETED
    
    def test_execute_migration_failure(self):
        """Test migration execution failure."""
        def failing_migrate(data):
            raise ValueError("Migration error")
        
        migration = Migration(
            id="test_fail",
            from_version="1.0.0",
            to_version="1.1.0",
            description="Failing migration",
            migrate_func=failing_migrate
        )
        
        with pytest.raises(MigrationError):
            migration.execute({"data": "value"})
        
        assert migration.status == MigrationStatus.FAILED
    
    def test_rollback_migration(self):
        """Test migration rollback."""
        def migrate_func(data):
            return {**data, "new_field": "value"}
        
        def rollback_func(data):
            result = data.copy()
            result.pop("new_field", None)
            return result
        
        migration = Migration(
            id="test_rollback",
            from_version="1.0.0",
            to_version="1.1.0",
            description="Test rollback",
            migrate_func=migrate_func,
            rollback_func=rollback_func
        )
        
        # Execute migration
        data = {"original": "value"}
        migrated = migration.execute(data)
        assert "new_field" in migrated
        
        # Rollback
        rolled_back = migration.rollback(migrated)
        assert "new_field" not in rolled_back
        assert rolled_back["original"] == "value"
        assert migration.status == MigrationStatus.ROLLED_BACK
    
    def test_rollback_not_supported(self):
        """Test rollback when not supported."""
        migration = Migration(
            id="test_no_rollback",
            from_version="1.0.0",
            to_version="1.1.0",
            description="No rollback",
            migrate_func=lambda d: d
        )
        
        with pytest.raises(MigrationError, match="does not support rollback"):
            migration.rollback({"data": "value"})


class TestMigrationManager:
    """Test suite for MigrationManager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = MigrationManager()
        
        # Create test migrations
        self.migration_1_to_2 = Migration(
            id="v1_to_v2",
            from_version="1.0.0",
            to_version="2.0.0",
            description="Upgrade to v2",
            migrate_func=lambda d: {**d, "version": "2.0.0"}
        )
        
        self.migration_2_to_3 = Migration(
            id="v2_to_v3",
            from_version="2.0.0",
            to_version="3.0.0",
            description="Upgrade to v3",
            migrate_func=lambda d: {**d, "version": "3.0.0"}
        )
    
    def test_register_migration(self):
        """Test registering a migration."""
        self.manager.register_migration(self.migration_1_to_2)
        
        # Should be able to find path
        path = self.manager.get_migration_path("1.0.0", "2.0.0")
        assert len(path) == 1
        assert path[0].id == "v1_to_v2"
    
    def test_register_duplicate_migration(self):
        """Test registering duplicate migration fails."""
        self.manager.register_migration(self.migration_1_to_2)
        
        with pytest.raises(ValueError, match="already registered"):
            self.manager.register_migration(self.migration_1_to_2)
    
    def test_get_migration_path_single_step(self):
        """Test finding single-step migration path."""
        self.manager.register_migration(self.migration_1_to_2)
        
        path = self.manager.get_migration_path("1.0.0", "2.0.0")
        
        assert len(path) == 1
        assert path[0].from_version == "1.0.0"
        assert path[0].to_version == "2.0.0"
    
    def test_get_migration_path_multi_step(self):
        """Test finding multi-step migration path."""
        self.manager.register_migration(self.migration_1_to_2)
        self.manager.register_migration(self.migration_2_to_3)
        
        path = self.manager.get_migration_path("1.0.0", "3.0.0")
        
        assert len(path) == 2
        assert path[0].from_version == "1.0.0"
        assert path[0].to_version == "2.0.0"
        assert path[1].from_version == "2.0.0"
        assert path[1].to_version == "3.0.0"
    
    def test_get_migration_path_same_version(self):
        """Test path when already at target version."""
        path = self.manager.get_migration_path("1.0.0", "1.0.0")
        assert len(path) == 0
    
    def test_get_migration_path_not_found(self):
        """Test error when no path exists."""
        self.manager.register_migration(self.migration_1_to_2)
        
        with pytest.raises(MigrationError, match="No migration path found"):
            self.manager.get_migration_path("1.0.0", "99.0.0")
    
    def test_migrate_single_step(self):
        """Test single-step migration."""
        self.manager.register_migration(self.migration_1_to_2)
        
        data = {"key": "value"}
        result = self.manager.migrate(data, "1.0.0", "2.0.0")
        
        assert result["key"] == "value"
        assert result["version"] == "2.0.0"
    
    def test_migrate_multi_step(self):
        """Test multi-step migration."""
        self.manager.register_migration(self.migration_1_to_2)
        self.manager.register_migration(self.migration_2_to_3)
        
        data = {"key": "value"}
        result = self.manager.migrate(data, "1.0.0", "3.0.0")
        
        assert result["key"] == "value"
        assert result["version"] == "3.0.0"
    
    def test_migrate_no_steps_needed(self):
        """Test migration when already at target version."""
        data = {"key": "value"}
        result = self.manager.migrate(data, "1.0.0", "1.0.0")
        
        assert result == data
    
    def test_migrate_with_rollback(self):
        """Test migration rollback on failure."""
        # Migration that will fail
        failing_migration = Migration(
            id="failing",
            from_version="2.0.0",
            to_version="3.0.0",
            description="Will fail",
            migrate_func=lambda d: (_ for _ in ()).throw(ValueError("Fail"))
        )
        
        # Migration with rollback
        migration_with_rollback = Migration(
            id="with_rollback",
            from_version="1.0.0",
            to_version="2.0.0",
            description="Has rollback",
            migrate_func=lambda d: {**d, "temp": "value"},
            rollback_func=lambda d: {k: v for k, v in d.items() if k != "temp"}
        )
        
        self.manager.register_migration(migration_with_rollback)
        self.manager.register_migration(failing_migration)
        
        data = {"key": "value"}
        
        with pytest.raises(MigrationError):
            self.manager.migrate(data, "1.0.0", "3.0.0", safe_mode=True)
    
    def test_get_migration_history(self):
        """Test getting migration history."""
        self.manager.register_migration(self.migration_1_to_2)
        
        # Execute migration
        self.manager.migrate({"key": "value"}, "1.0.0", "2.0.0")
        
        history = self.manager.get_migration_history()
        
        assert len(history) == 1
        assert history[0]["id"] == "v1_to_v2"
        assert history[0]["status"] == "completed"
    
    def test_get_migration_stats(self):
        """Test getting migration statistics."""
        self.manager.register_migration(self.migration_1_to_2)
        self.manager.register_migration(self.migration_2_to_3)
        
        # Execute migrations
        self.manager.migrate({"key": "value"}, "1.0.0", "3.0.0")
        
        stats = self.manager.get_migration_stats()
        
        assert stats["total_migrations"] == 2
        assert stats["completed"] == 2
        assert stats["failed"] == 0
        assert stats["success_rate"] == 100.0
        assert stats["registered_migrations"] == 2
    
    def test_clear_history(self):
        """Test clearing migration history."""
        self.manager.register_migration(self.migration_1_to_2)
        
        # Execute migration
        self.manager.migrate({"key": "value"}, "1.0.0", "2.0.0")
        
        # Clear history
        self.manager.clear_history()
        
        history = self.manager.get_migration_history()
        assert len(history) == 0


class TestGlobalMigrationManager:
    """Test suite for global migration manager accessor."""
    
    def test_get_migration_manager_singleton(self):
        """Test that get_migration_manager returns same instance."""
        manager1 = get_migration_manager()
        manager2 = get_migration_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, MigrationManager)


class TestMigrationHelpers:
    """Test suite for migration helper functions."""
    
    def test_add_field_migration(self):
        """Test adding a field."""
        migrate = add_field_migration("new_field", "default_value")
        
        data = {"existing": "field"}
        result = migrate(data)
        
        assert result["existing"] == "field"
        assert result["new_field"] == "default_value"
    
    def test_add_field_migration_existing_field(self):
        """Test adding field when it already exists."""
        migrate = add_field_migration("field", "new_value")
        
        data = {"field": "old_value"}
        result = migrate(data)
        
        # Should not overwrite existing field
        assert result["field"] == "old_value"
    
    def test_remove_field_migration(self):
        """Test removing a field."""
        migrate = remove_field_migration("to_remove")
        
        data = {"to_remove": "value", "keep": "this"}
        result = migrate(data)
        
        assert "to_remove" not in result
        assert result["keep"] == "this"
    
    def test_remove_field_migration_nonexistent(self):
        """Test removing nonexistent field."""
        migrate = remove_field_migration("nonexistent")
        
        data = {"field": "value"}
        result = migrate(data)
        
        # Should not raise error
        assert result == data
    
    def test_rename_field_migration(self):
        """Test renaming a field."""
        migrate = rename_field_migration("old_name", "new_name")
        
        data = {"old_name": "value", "other": "field"}
        result = migrate(data)
        
        assert "old_name" not in result
        assert result["new_name"] == "value"
        assert result["other"] == "field"
    
    def test_rename_field_migration_nonexistent(self):
        """Test renaming nonexistent field."""
        migrate = rename_field_migration("nonexistent", "new_name")
        
        data = {"field": "value"}
        result = migrate(data)
        
        # Should not raise error
        assert result == data
        assert "new_name" not in result
    
    def test_transform_field_migration(self):
        """Test transforming a field value."""
        migrate = transform_field_migration("field", lambda x: x.upper())
        
        data = {"field": "value", "other": "data"}
        result = migrate(data)
        
        assert result["field"] == "VALUE"
        assert result["other"] == "data"
    
    def test_transform_field_migration_nonexistent(self):
        """Test transforming nonexistent field."""
        migrate = transform_field_migration("nonexistent", lambda x: x.upper())
        
        data = {"field": "value"}
        result = migrate(data)
        
        # Should not raise error
        assert result == data


class TestComplexMigrationScenarios:
    """Test suite for complex migration scenarios."""
    
    def test_complex_version_graph(self):
        """Test migration through complex version graph."""
        manager = MigrationManager()
        
        # Create branching version graph
        manager.register_migration(Migration(
            id="1_to_2a",
            from_version="1.0.0",
            to_version="2.0.0-alpha",
            description="Alpha branch",
            migrate_func=lambda d: {**d, "branch": "alpha"}
        ))
        
        manager.register_migration(Migration(
            id="2a_to_2",
            from_version="2.0.0-alpha",
            to_version="2.0.0",
            description="Alpha to stable",
            migrate_func=lambda d: {**d, "stable": True}
        ))
        
        data = {"key": "value"}
        result = manager.migrate(data, "1.0.0", "2.0.0")
        
        assert result["branch"] == "alpha"
        assert result["stable"] is True
    
    def test_data_integrity_through_migrations(self):
        """Test that data integrity is maintained."""
        manager = MigrationManager()
        
        # Complex transformations
        manager.register_migration(Migration(
            id="normalize",
            from_version="1.0.0",
            to_version="1.1.0",
            description="Normalize data",
            migrate_func=lambda d: {
                **d,
                "normalized": [str(x).lower() for x in d.get("items", [])]
            }
        ))
        
        data = {"items": ["Hello", "WORLD", "Test"], "id": 123}
        result = manager.migrate(data, "1.0.0", "1.1.0")
        
        assert result["id"] == 123
        assert result["normalized"] == ["hello", "world", "test"]
