"""
Core Services Integration Tests

End-to-end tests verifying all services work together correctly.

Run with:
    pytest apps/core/tests/test_integration.py -v
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_markdown():
    """Sample markdown content for testing."""
    return """# Test Document

## Introduction

This is a test document for integration testing.

## Features

- Feature 1: Testing
- Feature 2: Integration
- Feature 3: Validation

## Conclusion

End of test document.
"""


@pytest.fixture
def sample_book_data():
    """Sample book data for testing."""
    return {
        "title": "Integration Test Book",
        "author": "Test Author",
        "genre": "Technical",
        "chapters": [
            {"number": 1, "title": "Getting Started", "content": "This is chapter one content."},
            {"number": 2, "title": "Advanced Topics", "content": "This is chapter two content."},
        ],
    }


# =============================================================================
# Service Import Tests
# =============================================================================


class TestServiceImports:
    """Test that all services can be imported."""

    def test_import_llm_service(self):
        """Test LLM service imports."""
        try:
            from apps.core.services.llm import (
                LLMConfig,
                LLMException,
                LLMResponse,
                LLMService,
                ProviderNotFoundError,
            )

            assert LLMService is not None
            assert LLMConfig is not None
        except ImportError as e:
            pytest.skip(f"LLM service not installed: {e}")

    def test_import_cache_service(self):
        """Test Cache service imports."""
        try:
            from apps.core.services.cache import CacheConfig, CacheException, CacheService, cached

            assert CacheService is not None
            assert CacheConfig is not None
        except ImportError as e:
            pytest.skip(f"Cache service not installed: {e}")

    def test_import_storage_service(self):
        """Test Storage service imports."""
        try:
            from apps.core.services.storage import StorageConfig, StorageException, StorageService

            assert StorageService is not None
            assert StorageConfig is not None
        except ImportError as e:
            pytest.skip(f"Storage service not installed: {e}")

    def test_import_export_service(self):
        """Test Export service imports."""
        try:
            from apps.core.services.export import (
                BookContent,
                BookExporter,
                ExportException,
                export_to,
            )

            assert export_to is not None
            assert BookExporter is not None
        except ImportError as e:
            pytest.skip(f"Export service not installed: {e}")

    def test_import_extractors(self):
        """Test Extractor service imports."""
        try:
            from apps.core.services.extractors import (
                DOCXExtractor,
                ExtractorException,
                PDFExtractor,
                extract_file,
            )

            assert extract_file is not None
            assert PDFExtractor is not None
        except ImportError as e:
            pytest.skip(f"Extractor service not installed: {e}")


# =============================================================================
# LLM Service Tests
# =============================================================================


class TestLLMServiceIntegration:
    """Integration tests for LLM Service."""

    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI API response."""
        return {
            "choices": [{"message": {"content": "This is a test response."}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }

    def test_llm_config_creation(self):
        """Test LLM configuration creation."""
        try:
            from apps.core.services.llm import LLMConfig

            config = LLMConfig(
                provider="openai", model="gpt-4", default_temperature=0.7, default_max_tokens=1000
            )

            assert config.provider == "openai"
            assert config.model == "gpt-4"
            assert config.default_temperature == 0.7
        except ImportError:
            pytest.skip("LLM service not installed")

    def test_llm_response_model(self):
        """Test LLM response model."""
        try:
            from apps.core.services.llm import LLMResponse

            response = LLMResponse(success=True, content="Test response", model="gpt-4")

            assert response.content == "Test response"
            assert response.success is True
        except ImportError:
            pytest.skip("LLM service not installed")


# =============================================================================
# Cache Service Tests
# =============================================================================


class TestCacheServiceIntegration:
    """Integration tests for Cache Service."""

    def test_memory_cache_operations(self):
        """Test in-memory cache operations."""
        try:
            from apps.core.services.cache import CacheConfig, CacheService

            config = CacheConfig(backend="memory")
            cache = CacheService(config)

            # Set and get
            cache.set("test_key", {"value": 123})
            result = cache.get("test_key")

            assert result == {"value": 123}

            # Delete
            cache.delete("test_key")
            assert cache.get("test_key") is None

        except ImportError:
            pytest.skip("Cache service not installed")

    def test_cache_with_ttl(self):
        """Test cache TTL functionality."""
        try:
            import time

            from apps.core.services.cache import CacheConfig, CacheService

            config = CacheConfig(backend="memory")
            cache = CacheService(config)

            # Set with short TTL
            cache.set("ttl_key", "value", ttl=1)

            # Should exist immediately
            assert cache.get("ttl_key") == "value"

            # Wait for expiry
            time.sleep(1.5)

            # Should be gone
            assert cache.get("ttl_key") is None

        except ImportError:
            pytest.skip("Cache service not installed")


# =============================================================================
# Storage Service Tests
# =============================================================================


class TestStorageServiceIntegration:
    """Integration tests for Storage Service."""

    def test_local_storage_save_load(self, temp_dir):
        """Test local storage save and load."""
        try:
            from apps.core.services.storage import LocalStorageBackend, StorageConfig

            config = StorageConfig(backend="local", base_path=str(temp_dir))
            storage = LocalStorageBackend(config)

            # Save content
            content = b"Test file content"
            result = storage.write("test/file.txt", content)

            assert result is not None

            # Load content
            loaded = storage.read("test/file.txt")
            assert loaded == content

            # Check exists
            assert storage.exists("test/file.txt") is True
            assert storage.exists("nonexistent.txt") is False

        except ImportError:
            pytest.skip("Storage service not installed")

    def test_storage_list_files(self, temp_dir):
        """Test file listing."""
        try:
            from apps.core.services.storage import LocalStorageBackend, StorageConfig

            config = StorageConfig(backend="local", base_path=str(temp_dir))
            storage = LocalStorageBackend(config)

            # Create some files
            storage.write("dir/file1.txt", b"content1")
            storage.write("dir/file2.txt", b"content2")
            storage.write("dir/subdir/file3.txt", b"content3")

            # List files
            files = storage.list("dir")

            assert len(files) >= 2

        except ImportError:
            pytest.skip("Storage service not installed")


# =============================================================================
# Export Service Tests
# =============================================================================


class TestExportServiceIntegration:
    """Integration tests for Export Service."""

    def test_export_markdown(self, temp_dir, sample_markdown):
        """Test Markdown export."""
        try:
            from apps.core.services.export import export_markdown

            output_path = temp_dir / "output.md"
            result = export_markdown(sample_markdown, str(output_path), add_frontmatter=True)

            assert result.success is True
            assert output_path.exists()

            content = output_path.read_text()
            assert "# Test Document" in content

        except ImportError:
            pytest.skip("Export service not installed")

    def test_export_html(self, temp_dir, sample_markdown):
        """Test HTML export."""
        try:
            from apps.core.services.export import export_to

            output_path = temp_dir / "output.html"
            result = export_to("html", sample_markdown, str(output_path))

            assert result.success is True
            assert output_path.exists()

            content = output_path.read_text()
            assert "<html" in content.lower()

        except ImportError:
            pytest.skip("Export service not installed")

    def test_export_json(self, temp_dir):
        """Test JSON export."""
        try:
            from apps.core.services.export import export_json

            data = {"key": "value", "list": [1, 2, 3]}
            output_path = temp_dir / "output.json"

            result = export_json(data, str(output_path))

            assert result.success is True

            # Verify content
            with open(output_path) as f:
                loaded = json.load(f)

            assert loaded == data

        except ImportError:
            pytest.skip("Export service not installed")

    def test_book_content_model(self, sample_book_data):
        """Test BookContent model."""
        try:
            from apps.core.services.export import BookContent, ChapterContent

            chapters = [
                ChapterContent(number=ch["number"], title=ch["title"], content=ch["content"])
                for ch in sample_book_data["chapters"]
            ]

            book = BookContent(
                title=sample_book_data["title"],
                author=sample_book_data["author"],
                genre=sample_book_data["genre"],
                chapters=chapters,
            )

            assert book.title == "Integration Test Book"
            assert book.chapter_count == 2
            assert book.total_words > 0

        except ImportError:
            pytest.skip("Export service not installed")


# =============================================================================
# Extractor Service Tests
# =============================================================================


class TestExtractorServiceIntegration:
    """Integration tests for Extractor Service."""

    def test_text_extractor(self, temp_dir):
        """Test text file extraction."""
        try:
            from apps.core.services.extractors import extract_file

            # Create test file
            test_file = temp_dir / "test.txt"
            test_file.write_text("Hello World\n\nThis is a test file.")

            result = extract_file(test_file)

            assert result.success is True
            assert "Hello World" in result.text
            assert result.word_count > 0

        except ImportError:
            pytest.skip("Extractor service not installed")

    def test_json_extractor(self, temp_dir):
        """Test JSON file extraction."""
        try:
            from apps.core.services.extractors import extract_file

            # Create test file
            test_file = temp_dir / "test.json"
            data = {"name": "Test", "values": [1, 2, 3]}
            test_file.write_text(json.dumps(data))

            result = extract_file(test_file)

            assert result.success is True
            assert "Test" in result.raw_content

        except ImportError:
            pytest.skip("Extractor service not installed")

    def test_csv_extractor(self, temp_dir):
        """Test CSV file extraction."""
        try:
            from apps.core.services.extractors import extract_file

            # Create test file
            test_file = temp_dir / "test.csv"
            test_file.write_text("name,age\nAlice,30\nBob,25")

            result = extract_file(test_file)

            assert result.success is True
            assert len(result.tables) == 1
            assert result.tables[0].row_count == 2

        except ImportError:
            pytest.skip("Extractor service not installed")

    def test_extractor_config(self):
        """Test extractor configuration."""
        try:
            from apps.core.services.extractors import ExtractorConfig

            config = ExtractorConfig(ocr_enabled=True, ocr_language="deu", preserve_formatting=True)

            assert config.ocr_enabled is True
            assert config.ocr_language == "deu"

        except ImportError:
            pytest.skip("Extractor service not installed")


# =============================================================================
# Cross-Service Integration Tests
# =============================================================================


class TestCrossServiceIntegration:
    """Tests that verify services work together."""

    def test_extract_and_export(self, temp_dir):
        """Test extracting content and re-exporting it."""
        try:
            from apps.core.services.export import export_to
            from apps.core.services.extractors import extract_file

            # Create source file
            source = temp_dir / "source.txt"
            source.write_text("# Original Content\n\nThis is the original text.")

            # Extract
            extract_result = extract_file(source)
            assert extract_result.success

            # Export to different format
            output = temp_dir / "output.html"
            export_result = export_to("html", extract_result.text, str(output))

            assert export_result.success
            assert output.exists()

        except ImportError:
            pytest.skip("Services not installed")

    def test_cache_llm_response(self):
        """Test caching LLM responses."""
        try:
            from apps.core.services.cache import CacheConfig, CacheService
            from apps.core.services.llm import LLMResponse

            cache = CacheService(CacheConfig(backend="memory"))

            # Simulate caching an LLM response
            response = LLMResponse(
                content="Cached response", model="gpt-4", provider="openai", tokens_used=50
            )

            cache.set("llm:test_prompt", response.model_dump())

            # Retrieve
            cached = cache.get("llm:test_prompt")
            assert cached["content"] == "Cached response"

        except ImportError:
            pytest.skip("Services not installed")

    def test_storage_and_export(self, temp_dir):
        """Test exporting to storage."""
        try:
            from apps.core.services.export import export_to
            from apps.core.services.storage import LocalStorageBackend, StorageConfig

            # Setup storage
            storage = LocalStorageBackend(StorageConfig(backend="local", base_path=str(temp_dir)))

            # Export content
            content = "# Report\n\nGenerated content."
            export_path = temp_dir / "exports" / "report.md"
            export_path.parent.mkdir(exist_ok=True)

            result = export_to("md", content, str(export_path))
            assert result.success

            # Verify through storage
            assert storage.exists("exports/report.md")

        except ImportError:
            pytest.skip("Services not installed")


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Test error handling across services."""

    def test_extractor_file_not_found(self, temp_dir):
        """Test extractor handles missing files."""
        try:
            from apps.core.services.extractors import extract_file

            result = extract_file(temp_dir / "nonexistent.pdf")

            assert result.success is False
            assert len(result.errors) > 0

        except ImportError:
            pytest.skip("Extractor service not installed")

    def test_export_invalid_format(self, temp_dir):
        """Test export handles invalid formats."""
        try:
            from apps.core.services.export import UnsupportedFormatError, export_to

            with pytest.raises((UnsupportedFormatError, ValueError)):
                export_to("invalid_format", "content", str(temp_dir / "out"))

        except ImportError:
            pytest.skip("Export service not installed")


# =============================================================================
# Performance Tests
# =============================================================================


class TestPerformance:
    """Basic performance tests."""

    def test_cache_performance(self):
        """Test cache operations are fast."""
        try:
            import time

            from apps.core.services.cache import CacheConfig, CacheService

            cache = CacheService(CacheConfig(backend="memory"))

            start = time.time()

            # Many operations
            for i in range(1000):
                cache.set(f"key_{i}", f"value_{i}")
                cache.get(f"key_{i}")

            elapsed = time.time() - start

            # Should complete in under 1 second
            assert elapsed < 1.0

        except ImportError:
            pytest.skip("Cache service not installed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
