"""
Unit tests for the registry module.
"""

import pytest
import tempfile
import json
from pathlib import Path

from creative_services.prompts import (
    PromptTemplateSpec,
    PromptVariable,
    TemplateNotFoundError,
)
from creative_services.prompts.registry import (
    InMemoryRegistry,
    FileRegistry,
    TemplateRegistry,
    TemplateStore,
)


class TestInMemoryRegistry:
    """Tests for InMemoryRegistry."""

    def test_save_and_get(self, simple_template):
        """Test saving and retrieving a template."""
        registry = InMemoryRegistry()
        registry.save(simple_template)
        
        loaded = registry.get(simple_template.template_key)
        assert loaded is not None
        assert loaded.template_key == simple_template.template_key
        assert loaded.name == simple_template.name

    def test_get_nonexistent(self):
        """Test getting a nonexistent template returns None."""
        registry = InMemoryRegistry()
        result = registry.get("nonexistent.template.v1")
        assert result is None

    def test_get_or_raise(self, simple_template):
        """Test get_or_raise raises on missing template."""
        registry = InMemoryRegistry()
        
        with pytest.raises(TemplateNotFoundError) as exc_info:
            registry.get_or_raise("nonexistent.template.v1")
        
        assert "nonexistent.template.v1" in str(exc_info.value)

    def test_exists(self, simple_template):
        """Test exists check."""
        registry = InMemoryRegistry()
        
        assert not registry.exists(simple_template.template_key)
        registry.save(simple_template)
        assert registry.exists(simple_template.template_key)

    def test_delete(self, simple_template):
        """Test deleting a template."""
        registry = InMemoryRegistry()
        registry.save(simple_template)
        
        assert registry.delete(simple_template.template_key)
        assert not registry.exists(simple_template.template_key)
        assert not registry.delete(simple_template.template_key)  # Already deleted

    def test_list_keys(self, simple_template, complex_template):
        """Test listing template keys."""
        registry = InMemoryRegistry()
        registry.save(simple_template)
        registry.save(complex_template)
        
        keys = registry.list_keys()
        assert len(keys) == 2
        assert simple_template.template_key in keys
        assert complex_template.template_key in keys

    def test_list_keys_by_domain(self, simple_template):
        """Test listing keys filtered by domain."""
        registry = InMemoryRegistry()
        registry.save(simple_template)
        
        # Create template with different domain
        other_template = simple_template.model_copy(update={
            "template_key": "other.test.v1",
            "domain_code": "other",
        })
        registry.save(other_template)
        
        keys = registry.list_keys(domain_code="test")
        assert len(keys) == 1
        assert simple_template.template_key in keys

    def test_list_by_domain(self, simple_template):
        """Test listing templates by domain."""
        registry = InMemoryRegistry()
        registry.save(simple_template)
        
        templates = registry.list_by_domain("test")
        assert len(templates) == 1
        assert templates[0].template_key == simple_template.template_key

    def test_search_by_query(self, simple_template):
        """Test searching templates by text query."""
        registry = InMemoryRegistry()
        registry.save(simple_template)
        
        # Search by template name
        results = registry.search(query=simple_template.name.split()[0])
        assert len(results) == 1
        
        results = registry.search(query="nonexistent_xyz_123")
        assert len(results) == 0

    def test_search_by_tags(self, complex_template):
        """Test searching templates by tags."""
        registry = InMemoryRegistry()
        registry.save(complex_template)
        
        results = registry.search(tags=["character"])
        assert len(results) == 1
        
        results = registry.search(tags=["nonexistent"])
        assert len(results) == 0

    def test_search_active_only(self, simple_template):
        """Test searching only active templates."""
        registry = InMemoryRegistry()
        
        inactive = simple_template.model_copy(update={"is_active": False})
        registry.save(inactive)
        
        results = registry.search(active_only=True)
        assert len(results) == 0
        
        results = registry.search(active_only=False)
        assert len(results) == 1

    def test_clear(self, simple_template, complex_template):
        """Test clearing all templates."""
        registry = InMemoryRegistry()
        registry.save(simple_template)
        registry.save(complex_template)
        
        assert registry.count() == 2
        registry.clear()
        assert registry.count() == 0

    def test_from_dict(self):
        """Test creating registry from dictionary."""
        data = {
            "test.template.v1": {
                "domain_code": "test",
                "name": "Test Template",
                "system_prompt": "System",
                "user_prompt": "User",
            }
        }
        
        registry = InMemoryRegistry.from_dict(data)
        assert registry.count() == 1
        assert registry.exists("test.template.v1")

    def test_implements_protocol(self):
        """Test that InMemoryRegistry implements TemplateRegistry protocol."""
        registry = InMemoryRegistry()
        assert isinstance(registry, TemplateRegistry)
        assert isinstance(registry, TemplateStore)


class TestFileRegistry:
    """Tests for FileRegistry."""

    def test_from_json_file(self, simple_template):
        """Test loading templates from JSON file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            data = {
                simple_template.template_key: simple_template.model_dump(mode="json")
            }
            json.dump(data, f)
            f.flush()
            
            registry = FileRegistry.from_file(f.name)
            assert registry.count() == 1
            
            loaded = registry.get(simple_template.template_key)
            assert loaded is not None
            assert loaded.name == simple_template.name
            
            # Cleanup
            Path(f.name).unlink()

    def test_from_directory(self, simple_template):
        """Test loading templates from directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a JSON file
            file_path = Path(tmpdir) / "templates.json"
            data = {
                simple_template.template_key: simple_template.model_dump(mode="json")
            }
            with open(file_path, "w") as f:
                json.dump(data, f)
            
            registry = FileRegistry.from_directory(tmpdir)
            assert registry.count() == 1

    def test_export_to_json(self, simple_template):
        """Test exporting templates to JSON file."""
        registry = FileRegistry()
        registry.save(simple_template)
        
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            registry.export_to_file(f.name, format="json")
            
            # Read back
            with open(f.name, "r") as rf:
                data = json.load(rf)
            
            assert simple_template.template_key in data
            
            # Cleanup
            Path(f.name).unlink()

    def test_reload(self, simple_template):
        """Test reloading templates from source."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            data = {
                simple_template.template_key: simple_template.model_dump(mode="json")
            }
            json.dump(data, f)
            f.flush()
            
            registry = FileRegistry.from_file(f.name)
            assert registry.count() == 1
            
            # Modify file
            data["new.template.v1"] = {
                "template_key": "new.template.v1",
                "domain_code": "test",
                "name": "New Template",
                "system_prompt": "System",
                "user_prompt": "User",
            }
            with open(f.name, "w") as wf:
                json.dump(data, wf)
            
            # Reload
            registry.reload()
            assert registry.count() == 2
            
            # Cleanup
            Path(f.name).unlink()

    def test_file_not_found(self):
        """Test error on missing file."""
        with pytest.raises(FileNotFoundError):
            FileRegistry.from_file("/nonexistent/path/file.json")

    def test_implements_protocol(self):
        """Test that FileRegistry implements TemplateRegistry protocol."""
        registry = FileRegistry()
        assert isinstance(registry, TemplateRegistry)
        assert isinstance(registry, TemplateStore)
