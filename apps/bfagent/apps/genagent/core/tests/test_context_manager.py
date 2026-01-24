"""
Tests for GenAgent Context Manager - Feature 3: Context Isolation

Author: GenAgent Development Team
Created: 2025-01-19
"""

import pytest
import copy
from apps.genagent.core.context_manager import (
    ContextManager,
    ContextIsolationError,
    get_context_manager
)


class TestContextManager:
    """Test suite for ContextManager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.context_manager = ContextManager()
        
        # Sample context for testing
        self.sample_context = {
            "user_id": 123,
            "project_name": "Test Project",
            "settings": {
                "theme": "dark",
                "language": "en"
            },
            "data": [1, 2, 3]
        }
    
    def test_create_isolated_context(self):
        """Test creating an isolated context."""
        isolated = self.context_manager.create_isolated_context(
            self.sample_context
        )
        
        # Should be equal in content
        assert isolated == self.sample_context
        
        # But not the same object
        assert isolated is not self.sample_context
        
        # Modifications to isolated shouldn't affect original
        isolated["user_id"] = 999
        assert self.sample_context["user_id"] == 123
    
    def test_deep_copy_isolation(self):
        """Test that nested objects are deeply copied."""
        isolated = self.context_manager.create_isolated_context(
            self.sample_context
        )
        
        # Modify nested object
        isolated["settings"]["theme"] = "light"
        
        # Original should be unchanged
        assert self.sample_context["settings"]["theme"] == "dark"
    
    def test_list_isolation(self):
        """Test that lists are properly isolated."""
        isolated = self.context_manager.create_isolated_context(
            self.sample_context
        )
        
        # Modify list
        isolated["data"].append(4)
        
        # Original should be unchanged
        assert self.sample_context["data"] == [1, 2, 3]
        assert isolated["data"] == [1, 2, 3, 4]
    
    def test_context_with_id_tracking(self):
        """Test context creation with ID tracking."""
        context_id = "test_context_1"
        
        isolated = self.context_manager.create_isolated_context(
            self.sample_context,
            context_id=context_id
        )
        
        # Should be tracked
        stats = self.context_manager.get_context_stats()
        assert context_id in stats["context_ids"]
        assert stats["active_contexts"] == 1
    
    def test_read_only_keys_marking(self):
        """Test marking keys as read-only."""
        read_only = {"user_id", "project_name"}
        
        isolated = self.context_manager.create_isolated_context(
            self.sample_context,
            read_only_keys=read_only
        )
        
        # Should have read-only keys marked
        assert "__read_only_keys__" in isolated
        assert isolated["__read_only_keys__"] == read_only
    
    def test_validate_context_integrity(self):
        """Test context integrity validation."""
        read_only = {"user_id"}
        
        isolated = self.context_manager.create_isolated_context(
            self.sample_context,
            read_only_keys=read_only
        )
        
        # Validation should pass
        assert self.context_manager.validate_context_integrity(
            isolated,
            read_only
        ) is True
    
    def test_cleanup_context(self):
        """Test context cleanup."""
        context_id = "cleanup_test"
        
        # Create tracked context
        self.context_manager.create_isolated_context(
            self.sample_context,
            context_id=context_id
        )
        
        # Should be tracked
        assert self.context_manager.get_active_contexts_count() == 1
        
        # Cleanup
        self.context_manager.cleanup_context(context_id)
        
        # Should be removed
        assert self.context_manager.get_active_contexts_count() == 0
    
    def test_isolated_execution_context_manager(self):
        """Test the isolated_execution context manager."""
        context_id = "exec_test"
        modifications_made = False
        
        with self.context_manager.isolated_execution(
            self.sample_context,
            context_id=context_id
        ) as isolated:
            # Modify isolated context
            isolated["user_id"] = 456
            modifications_made = True
            
            # Should be tracked during execution
            assert self.context_manager.get_active_contexts_count() == 1
        
        assert modifications_made
        
        # Should be cleaned up after context exit
        assert self.context_manager.get_active_contexts_count() == 0
        
        # Original should be unchanged
        assert self.sample_context["user_id"] == 123
    
    def test_exception_handling_in_isolated_execution(self):
        """Test that cleanup happens even with exceptions."""
        context_id = "exception_test"
        
        with pytest.raises(ValueError):
            with self.context_manager.isolated_execution(
                self.sample_context,
                context_id=context_id
            ) as isolated:
                # Raise exception
                raise ValueError("Test exception")
        
        # Should still be cleaned up
        assert self.context_manager.get_active_contexts_count() == 0
    
    def test_merge_results_all_keys(self):
        """Test merging all results back."""
        isolated = self.context_manager.create_isolated_context(
            self.sample_context
        )
        
        # Modify isolated context
        isolated["user_id"] = 999
        isolated["new_key"] = "new_value"
        
        # Merge back
        merged = self.context_manager.merge_results(
            self.sample_context,
            isolated
        )
        
        # Should have merged results
        assert merged["user_id"] == 999
        assert merged["new_key"] == "new_value"
        
        # Original should be unchanged
        assert self.sample_context["user_id"] == 123
        assert "new_key" not in self.sample_context
    
    def test_merge_results_specific_keys(self):
        """Test merging only specific keys."""
        isolated = self.context_manager.create_isolated_context(
            self.sample_context
        )
        
        # Modify multiple keys
        isolated["user_id"] = 999
        isolated["project_name"] = "Modified"
        
        # Merge only user_id
        merged = self.context_manager.merge_results(
            self.sample_context,
            isolated,
            merge_keys={"user_id"}
        )
        
        # Only user_id should be merged
        assert merged["user_id"] == 999
        assert merged["project_name"] == "Test Project"  # Unchanged
    
    def test_merge_skips_internal_keys(self):
        """Test that internal keys are not merged."""
        read_only = {"user_id"}
        
        isolated = self.context_manager.create_isolated_context(
            self.sample_context,
            read_only_keys=read_only
        )
        
        # Merge results
        merged = self.context_manager.merge_results(
            self.sample_context,
            isolated
        )
        
        # Should not include internal marker
        assert "__read_only_keys__" not in merged
    
    def test_get_context_stats(self):
        """Test getting context statistics."""
        # Create multiple contexts
        self.context_manager.create_isolated_context(
            self.sample_context,
            context_id="ctx_1"
        )
        self.context_manager.create_isolated_context(
            self.sample_context,
            context_id="ctx_2"
        )
        
        stats = self.context_manager.get_context_stats()
        
        assert stats["active_contexts"] == 2
        assert "ctx_1" in stats["context_ids"]
        assert "ctx_2" in stats["context_ids"]
    
    def test_get_context_manager_singleton(self):
        """Test global context manager accessor."""
        manager1 = get_context_manager()
        manager2 = get_context_manager()
        
        # Should be same instance
        assert manager1 is manager2
    
    def test_complex_nested_structure_isolation(self):
        """Test isolation of complex nested structures."""
        complex_context = {
            "level1": {
                "level2": {
                    "level3": {
                        "data": [1, 2, 3]
                    }
                },
                "list": [{"a": 1}, {"b": 2}]
            }
        }
        
        isolated = self.context_manager.create_isolated_context(
            complex_context
        )
        
        # Modify deeply nested value
        isolated["level1"]["level2"]["level3"]["data"].append(4)
        isolated["level1"]["list"][0]["a"] = 999
        
        # Original should be unchanged
        assert complex_context["level1"]["level2"]["level3"]["data"] == [1, 2, 3]
        assert complex_context["level1"]["list"][0]["a"] == 1
    
    def test_empty_context(self):
        """Test handling of empty context."""
        empty = {}
        isolated = self.context_manager.create_isolated_context(empty)
        
        assert isolated == {}
        assert isolated is not empty
    
    def test_multiple_cleanup_calls(self):
        """Test that multiple cleanup calls don't error."""
        context_id = "multi_cleanup"
        
        self.context_manager.create_isolated_context(
            self.sample_context,
            context_id=context_id
        )
        
        # First cleanup
        self.context_manager.cleanup_context(context_id)
        
        # Second cleanup should not error
        self.context_manager.cleanup_context(context_id)
        
        assert self.context_manager.get_active_contexts_count() == 0
