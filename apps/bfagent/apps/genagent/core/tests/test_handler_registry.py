"""
Unit tests for GenAgent Handler Registry.
Tests handler registration, validation, and versioning.
"""

import pytest
import warnings
from apps.genagent.core.handler_registry import (
    HandlerRegistry,
    HandlerNotFoundError,
    VersionMismatchError,
    HandlerMetadata
)


# Mock Handler Classes for Testing
class MockHandlerV1:
    """Mock handler version 1.0.0"""
    VERSION = "1.0.0"
    dependencies = []
    schema_version = "1.0.0"
    
    def process(self, context):
        return {"result": "v1"}


class MockHandlerV2:
    """Mock handler version 2.0.0"""
    VERSION = "2.0.0"
    dependencies = ["mock_handler_v1"]
    schema_version = "2.0.0"
    
    def process(self, context):
        return {"result": "v2"}


class DeprecatedHandler:
    """Deprecated mock handler"""
    VERSION = "0.9.0"
    dependencies = []
    schema_version = "1.0.0"


class ExperimentalHandler:
    """Experimental mock handler"""
    VERSION = "3.0.0-alpha"
    dependencies = []
    schema_version = "1.0.0"


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear registry before each test."""
    HandlerRegistry.clear()
    yield
    HandlerRegistry.clear()


class TestHandlerRegistration:
    """Test handler registration functionality."""
    
    def test_register_basic_handler(self):
        """Test registering a basic handler."""
        HandlerRegistry.register(
            name="test_handler",
            handler_class=MockHandlerV1,
            version="1.0.0",
            domains=["test_domain"],
            description="Test handler"
        )
        
        assert "test_handler" in HandlerRegistry.get_all_handlers()
        info = HandlerRegistry.get_handler_info("test_handler")
        assert info["version"] == "1.0.0"
        assert "test_domain" in info["domains"]
    
    def test_register_multiple_domains(self):
        """Test handler with multiple domains."""
        HandlerRegistry.register(
            name="multi_domain_handler",
            handler_class=MockHandlerV1,
            version="1.0.0",
            domains=["domain1", "domain2", "domain3"]
        )
        
        info = HandlerRegistry.get_handler_info("multi_domain_handler")
        assert len(info["domains"]) == 3
        assert "domain1" in info["domains"]
    
    def test_register_duplicate_handler_same_version(self):
        """Test that duplicate registration with same version raises error."""
        HandlerRegistry.register(
            name="duplicate",
            handler_class=MockHandlerV1,
            version="1.0.0",
            domains=["test"]
        )
        
        with pytest.raises(ValueError, match="already registered"):
            HandlerRegistry.register(
                name="duplicate",
                handler_class=MockHandlerV1,
                version="1.0.0",
                domains=["test"]
            )
    
    def test_register_duplicate_handler_different_version(self):
        """Test that duplicate registration with different version logs warning."""
        HandlerRegistry.register(
            name="versioned",
            handler_class=MockHandlerV1,
            version="1.0.0",
            domains=["test"]
        )
        
        # Should allow overwriting with different version (with warning)
        with pytest.warns(UserWarning):
            HandlerRegistry.register(
                name="versioned",
                handler_class=MockHandlerV2,
                version="2.0.0",
                domains=["test"]
            )
        
        info = HandlerRegistry.get_handler_info("versioned")
        assert info["version"] == "2.0.0"
    
    def test_register_invalid_version_format(self):
        """Test that invalid version format raises error."""
        with pytest.raises(ValueError, match="Invalid semantic version"):
            HandlerRegistry.register(
                name="bad_version",
                handler_class=MockHandlerV1,
                version="1.0",  # Invalid: needs 3 parts
                domains=["test"]
            )
        
        with pytest.raises(ValueError, match="Invalid semantic version"):
            HandlerRegistry.register(
                name="bad_version2",
                handler_class=MockHandlerV1,
                version="v1.0.0",  # Invalid: no 'v' prefix
                domains=["test"]
            )


class TestHandlerValidation:
    """Test handler availability validation."""
    
    def test_validate_existing_handler(self):
        """Test validation of existing handler."""
        HandlerRegistry.register(
            name="valid_handler",
            handler_class=MockHandlerV1,
            version="1.0.0",
            domains=["test"]
        )
        
        assert HandlerRegistry.validate_availability("valid_handler") is True
    
    def test_validate_nonexistent_handler(self):
        """Test validation of non-existent handler raises error."""
        with pytest.raises(HandlerNotFoundError, match="not registered"):
            HandlerRegistry.validate_availability("nonexistent")
    
    def test_validate_deprecated_handler_warning(self):
        """Test that deprecated handler shows warning."""
        HandlerRegistry.register(
            name="deprecated_handler",
            handler_class=DeprecatedHandler,
            version="0.9.0",
            domains=["test"],
            status="deprecated"
        )
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            HandlerRegistry.validate_availability("deprecated_handler")
            
            assert len(w) == 1
            assert "deprecated" in str(w[0].message).lower()
    
    def test_validate_experimental_handler_warning(self):
        """Test that experimental handler shows warning."""
        HandlerRegistry.register(
            name="experimental_handler",
            handler_class=ExperimentalHandler,
            version="3.0.0",
            domains=["test"],
            status="experimental"
        )
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            HandlerRegistry.validate_availability("experimental_handler")
            
            assert len(w) == 1
            assert "experimental" in str(w[0].message).lower()


class TestHandlerInfo:
    """Test handler information retrieval."""
    
    def test_get_handler_info_complete(self):
        """Test getting complete handler information."""
        HandlerRegistry.register(
            name="info_handler",
            handler_class=MockHandlerV1,
            version="1.0.0",
            domains=["domain1", "domain2"],
            description="Test description"
        )
        
        info = HandlerRegistry.get_handler_info("info_handler")
        
        assert info["name"] == "info_handler"
        assert info["class"] == "MockHandlerV1"
        assert info["version"] == "1.0.0"
        assert len(info["domains"]) == 2
        assert info["status"] == "active"
        assert info["description"] == "Test description"
        assert "module" in info
    
    def test_get_nonexistent_handler_info(self):
        """Test that getting info for nonexistent handler raises error."""
        with pytest.raises(HandlerNotFoundError):
            HandlerRegistry.get_handler_info("nonexistent")


class TestDomainFiltering:
    """Test domain-based handler filtering."""
    
    def test_get_handlers_for_domain_single(self):
        """Test getting handlers for a domain with one handler."""
        HandlerRegistry.register(
            name="handler1",
            handler_class=MockHandlerV1,
            version="1.0.0",
            domains=["book_writing"]
        )
        
        handlers = HandlerRegistry.get_handlers_for_domain("book_writing")
        assert len(handlers) == 1
        assert "handler1" in handlers
    
    def test_get_handlers_for_domain_multiple(self):
        """Test getting multiple handlers for same domain."""
        HandlerRegistry.register(
            name="handler1",
            handler_class=MockHandlerV1,
            version="1.0.0",
            domains=["book_writing"]
        )
        HandlerRegistry.register(
            name="handler2",
            handler_class=MockHandlerV2,
            version="2.0.0",
            domains=["book_writing", "screenplay"]
        )
        
        handlers = HandlerRegistry.get_handlers_for_domain("book_writing")
        assert len(handlers) == 2
        assert "handler1" in handlers
        assert "handler2" in handlers
    
    def test_get_handlers_excludes_deprecated(self):
        """Test that deprecated handlers are excluded from domain results."""
        HandlerRegistry.register(
            name="active_handler",
            handler_class=MockHandlerV1,
            version="1.0.0",
            domains=["test"],
            status="active"
        )
        HandlerRegistry.register(
            name="deprecated_handler",
            handler_class=DeprecatedHandler,
            version="0.9.0",
            domains=["test"],
            status="deprecated"
        )
        
        handlers = HandlerRegistry.get_handlers_for_domain("test")
        assert len(handlers) == 1
        assert "active_handler" in handlers
        assert "deprecated_handler" not in handlers
    
    def test_get_handlers_for_nonexistent_domain(self):
        """Test getting handlers for domain with no handlers."""
        handlers = HandlerRegistry.get_handlers_for_domain("nonexistent")
        assert len(handlers) == 0


class TestVersionCompatibility:
    """Test version compatibility checking."""
    
    def test_version_compatibility_exact_match(self):
        """Test version compatibility with exact match."""
        HandlerRegistry.register(
            name="versioned_handler",
            handler_class=MockHandlerV1,
            version="1.0.0",
            domains=["test"]
        )
        
        assert HandlerRegistry.check_version_compatibility(
            "versioned_handler",
            "1.0.0"
        ) is True
    
    def test_version_compatibility_minor_upgrade(self):
        """Test version compatibility with minor version upgrade."""
        HandlerRegistry.register(
            name="versioned_handler",
            handler_class=MockHandlerV1,
            version="1.5.0",
            domains=["test"]
        )
        
        # Handler v1.5.0 should be compatible with required v1.0.0
        assert HandlerRegistry.check_version_compatibility(
            "versioned_handler",
            "1.0.0"
        ) is True
    
    def test_version_incompatibility_major_version(self):
        """Test version incompatibility with different major version."""
        HandlerRegistry.register(
            name="versioned_handler",
            handler_class=MockHandlerV2,
            version="2.0.0",
            domains=["test"]
        )
        
        with pytest.raises(VersionMismatchError, match="Major version mismatch"):
            HandlerRegistry.check_version_compatibility(
                "versioned_handler",
                "1.0.0"
            )
    
    def test_version_incompatibility_minor_too_old(self):
        """Test version incompatibility when handler is too old."""
        HandlerRegistry.register(
            name="old_handler",
            handler_class=MockHandlerV1,
            version="1.0.0",
            domains=["test"]
        )
        
        with pytest.raises(VersionMismatchError, match="Minor version too old"):
            HandlerRegistry.check_version_compatibility(
                "old_handler",
                "1.5.0"  # Requires newer minor version
            )


class TestRegistryStats:
    """Test registry statistics functionality."""
    
    def test_registry_stats_empty(self):
        """Test stats for empty registry."""
        stats = HandlerRegistry.get_registry_stats()
        
        assert stats["total_handlers"] == 0
        assert len(stats["by_status"]) == 0
        assert len(stats["by_domain"]) == 0
    
    def test_registry_stats_multiple_handlers(self):
        """Test stats with multiple handlers."""
        HandlerRegistry.register(
            name="handler1",
            handler_class=MockHandlerV1,
            version="1.0.0",
            domains=["domain1"],
            status="active"
        )
        HandlerRegistry.register(
            name="handler2",
            handler_class=MockHandlerV2,
            version="2.0.0",
            domains=["domain1", "domain2"],
            status="active"
        )
        HandlerRegistry.register(
            name="handler3",
            handler_class=DeprecatedHandler,
            version="0.9.0",
            domains=["domain2"],
            status="deprecated"
        )
        
        stats = HandlerRegistry.get_registry_stats()
        
        assert stats["total_handlers"] == 3
        assert stats["by_status"]["active"] == 2
        assert stats["by_status"]["deprecated"] == 1
        assert stats["by_domain"]["domain1"] == 2
        assert stats["by_domain"]["domain2"] == 2


class TestHandlerClassRetrieval:
    """Test handler class retrieval for instantiation."""
    
    def test_get_handler_class(self):
        """Test getting handler class for instantiation."""
        HandlerRegistry.register(
            name="test_handler",
            handler_class=MockHandlerV1,
            version="1.0.0",
            domains=["test"]
        )
        
        handler_class = HandlerRegistry.get_handler_class("test_handler")
        assert handler_class == MockHandlerV1
        
        # Test instantiation
        instance = handler_class()
        assert hasattr(instance, "process")
    
    def test_get_nonexistent_handler_class(self):
        """Test that getting nonexistent handler class raises error."""
        with pytest.raises(HandlerNotFoundError):
            HandlerRegistry.get_handler_class("nonexistent")
