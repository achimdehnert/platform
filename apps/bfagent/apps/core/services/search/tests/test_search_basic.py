"""
Core Search Service - Basic Tests

Tests for search functionality without requiring FAISS/SentenceTransformers.
"""

import pytest

from ..exceptions import SearchBackendNotAvailable, SearchIndexNotBuilt
from ..filtering import FilterBuilder, MetadataFilter
from ..models import EmbeddingModel, IndexItem, SearchBackend, SearchConfig, SearchResult


class TestSearchModels:
    """Test Pydantic models"""

    def test_search_config_defaults(self):
        """Test SearchConfig default values"""
        config = SearchConfig()

        assert config.backend == SearchBackend.FAISS
        assert config.model == EmbeddingModel.MINILM_L6.value
        assert config.device == "cpu"
        assert config.min_score == 0.35
        assert config.relative_threshold == 0.90

    def test_search_config_custom(self):
        """Test SearchConfig with custom values"""
        config = SearchConfig(
            backend=SearchBackend.FAISS,
            model=EmbeddingModel.GERMAN_BERT.value,
            device="cuda",
            min_score=0.5,
        )

        assert config.backend == SearchBackend.FAISS
        assert config.model == EmbeddingModel.GERMAN_BERT.value
        assert config.device == "cuda"
        assert config.min_score == 0.5

    def test_search_result(self):
        """Test SearchResult model"""
        result = SearchResult(
            id="test_1",
            score=0.89,
            title="Test Title",
            description="Test Description",
            metadata={"category": "test"},
        )

        assert result.id == "test_1"
        assert result.score == 0.89
        assert result.title == "Test Title"
        assert result.metadata["category"] == "test"

    def test_index_item(self):
        """Test IndexItem model"""
        item = IndexItem(
            id="item_1",
            text="Sample text content",
            title="Sample Title",
            metadata={"key": "value"},
        )

        assert item.id == "item_1"
        assert item.text == "Sample text content"
        assert item.title == "Sample Title"


class TestMetadataFilter:
    """Test metadata filtering"""

    def test_simple_equality_filter(self):
        """Test simple equality filter"""
        filter_obj = MetadataFilter()
        filter_obj.add_filter("category", "eq", "input")

        assert filter_obj.matches({"category": "input"})
        assert not filter_obj.matches({"category": "output"})

    def test_not_equals_filter(self):
        """Test not equals filter"""
        filter_obj = MetadataFilter()
        filter_obj.add_filter("status", "ne", "inactive")

        assert filter_obj.matches({"status": "active"})
        assert not filter_obj.matches({"status": "inactive"})

    def test_in_list_filter(self):
        """Test in list filter"""
        filter_obj = MetadataFilter()
        filter_obj.add_filter("status", "in", ["active", "beta"])

        assert filter_obj.matches({"status": "active"})
        assert filter_obj.matches({"status": "beta"})
        assert not filter_obj.matches({"status": "inactive"})

    def test_contains_filter(self):
        """Test contains filter"""
        filter_obj = MetadataFilter()
        filter_obj.add_filter("tags", "contains", "important")

        assert filter_obj.matches({"tags": ["important", "urgent"]})
        assert filter_obj.matches({"tags": "important-tag"})
        assert not filter_obj.matches({"tags": ["other"]})

    def test_comparison_filters(self):
        """Test comparison filters (gt, gte, lt, lte)"""
        filter_obj = MetadataFilter()

        # Greater than
        filter_obj.clear()
        filter_obj.add_filter("score", "gt", 0.5)
        assert filter_obj.matches({"score": 0.8})
        assert not filter_obj.matches({"score": 0.3})

        # Greater than or equal
        filter_obj.clear()
        filter_obj.add_filter("score", "gte", 0.5)
        assert filter_obj.matches({"score": 0.5})
        assert filter_obj.matches({"score": 0.8})

        # Less than
        filter_obj.clear()
        filter_obj.add_filter("score", "lt", 0.5)
        assert filter_obj.matches({"score": 0.3})
        assert not filter_obj.matches({"score": 0.8})

    def test_exists_filter(self):
        """Test exists filter"""
        filter_obj = MetadataFilter()
        filter_obj.add_filter("optional_field", "exists", None)

        assert filter_obj.matches({"optional_field": "value"})
        assert not filter_obj.matches({"other_field": "value"})

    def test_multiple_filters_and_logic(self):
        """Test multiple filters with AND logic"""
        filter_obj = MetadataFilter()
        filter_obj.add_filter("category", "eq", "processing")
        filter_obj.add_filter("version", "gte", "1.0.0")
        filter_obj.add_filter("status", "in", ["active", "beta"])

        # All match
        assert filter_obj.matches(
            {
                "category": "processing",
                "version": "1.2.0",
                "status": "active",
            }
        )

        # One doesn't match
        assert not filter_obj.matches(
            {
                "category": "input",
                "version": "1.2.0",
                "status": "active",
            }
        )

    def test_filter_chaining(self):
        """Test filter chaining (builder pattern)"""
        filter_obj = (
            MetadataFilter()
            .add_filter("category", "eq", "processing")
            .add_filter("status", "eq", "active")
        )

        assert len(filter_obj.filters) == 2


class TestFilterBuilder:
    """Test fluent filter builder"""

    def test_builder_pattern(self):
        """Test fluent builder interface"""
        builder = FilterBuilder()
        filter_obj = (
            builder.equals("category", "processing")
            .greater_than("version", "1.0.0")
            .in_list("status", ["active", "beta"])
            .build()
        )

        assert len(filter_obj.filters) == 3

        # Test matching
        assert filter_obj.matches(
            {
                "category": "processing",
                "version": "1.5.0",
                "status": "active",
            }
        )

    def test_builder_shortcuts(self):
        """Test builder shortcut methods"""
        builder = FilterBuilder()

        builder.equals("key1", "value1")
        builder.not_equals("key2", "value2")
        builder.contains("key3", "value3")

        filter_obj = builder.build()
        assert len(filter_obj.filters) == 3


class TestDocumentChunker:
    """Test document chunking"""

    def test_chunker_import(self):
        """Test that DocumentChunker can be imported"""
        from ..chunking import DocumentChunker

        chunker = DocumentChunker(chunk_size=100, chunk_overlap=20)
        assert chunker.chunk_size == 100
        assert chunker.chunk_overlap == 20

    def test_chunker_fixed_strategy(self):
        """Test fixed chunking strategy"""
        from ..chunking import DocumentChunker

        chunker = DocumentChunker(chunk_size=10, chunk_overlap=2, strategy="fixed")
        text = " ".join([f"word{i}" for i in range(50)])

        chunks = chunker.chunk_text(text)

        assert len(chunks) > 1
        assert all(chunk.idx == i for i, chunk in enumerate(chunks))

    def test_chunker_semantic_strategy(self):
        """Test semantic chunking (paragraph-based)"""
        from ..chunking import DocumentChunker

        chunker = DocumentChunker(chunk_size=20, strategy="semantic")
        text = "Paragraph 1 content.\n\nParagraph 2 content.\n\nParagraph 3 content."

        chunks = chunker.chunk_text(text, metadata={"doc_id": "123"})

        assert len(chunks) > 0
        assert all(chunk.metadata.get("doc_id") == "123" for chunk in chunks)


def test_imports():
    """Test that all main components can be imported"""
    from ..backends import FAISSSearchEngine
    from ..base import BaseSearchEngine, SearchIndex
    from ..chunking import DocumentChunker
    from ..exceptions import SearchException
    from ..filtering import FilterBuilder, MetadataFilter
    from ..indexes import DocumentSearchIndex, ToolSearchIndex
    from ..models import SearchConfig, SearchResult

    # All imports successful
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
