"""
Core Search Service - Integration Tests

Integration tests that require FAISS and Sentence Transformers.
These tests are skipped if dependencies are not installed.
"""

import pytest

from ..exceptions import SearchIndexNotBuilt
from ..factory import get_async_search_engine, get_search_engine
from ..indexes import DocumentSearchIndex, ToolSearchIndex

# Check if dependencies are available
try:
    import faiss
    from sentence_transformers import SentenceTransformer

    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not FAISS_AVAILABLE, reason="FAISS and SentenceTransformers not installed"
)


class TestFAISSSearchEngine:
    """Test FAISS search engine"""

    def test_create_engine(self):
        """Test creating a FAISS search engine"""
        search = get_search_engine(namespace="test")

        assert search is not None
        assert search.namespace == "test"

    def test_add_and_search(self):
        """Test adding items and searching"""
        search = get_search_engine(namespace="test_add_search")

        # Add items
        search.add_item(
            id="parser_1",
            text="DWG Parser: Parse AutoCAD DWG files and extract geometry",
            metadata={"category": "input", "version": "1.0.0"},
        )
        search.add_item(
            id="parser_2",
            text="IFC Parser: Parse IFC files and extract building elements",
            metadata={"category": "input", "version": "1.0.0"},
        )
        search.add_item(
            id="calculator_1",
            text="Area Calculator: Calculate room areas according to DIN 277",
            metadata={"category": "processing", "version": "1.0.0"},
        )

        # Build index
        assert search.build_index()
        assert search.is_built()

        # Search
        results = search.search("parse DWG files", top_k=5)

        assert len(results) > 0
        assert results[0].id == "parser_1"
        assert results[0].score > 0.5

    def test_filtered_search(self):
        """Test search with metadata filters"""
        search = get_search_engine(namespace="test_filtered")

        # Add items
        search.add_item(
            id="tool_1",
            text="Input tool version 1.0",
            metadata={"category": "input", "version": "1.0.0"},
        )
        search.add_item(
            id="tool_2",
            text="Input tool version 2.0",
            metadata={"category": "input", "version": "2.0.0"},
        )
        search.add_item(
            id="tool_3",
            text="Processing tool",
            metadata={"category": "processing", "version": "1.0.0"},
        )

        search.build_index()

        # Search with category filter
        results = search.search("tool", top_k=10, filters={"category": "input"})

        assert len(results) == 2
        assert all(r.metadata["category"] == "input" for r in results)

    def test_search_without_build(self):
        """Test that search fails if index not built"""
        search = get_search_engine(namespace="test_no_build")
        search.add_item(id="test", text="test", metadata={})

        with pytest.raises(SearchIndexNotBuilt):
            search.search("test")

    def test_index_caching(self):
        """Test that index is cached and reloaded"""
        namespace = "test_caching"

        # First engine - build index
        search1 = get_search_engine(namespace=namespace)
        search1.add_item(id="item1", text="Test item", metadata={})
        search1.build_index()

        # Second engine - should load from cache
        search2 = get_search_engine(namespace=namespace)
        search2.add_item(id="item1", text="Test item", metadata={})
        result = search2.build_index()

        assert result is True


class TestToolSearchIndex:
    """Test ToolSearchIndex"""

    def test_add_tools(self):
        """Test adding tools to index"""
        from ..backends import FAISSSearchEngine

        engine = FAISSSearchEngine(namespace="test_tools")
        index = ToolSearchIndex(namespace="test_tools", search_engine=engine)

        # Add tools
        index.add_tool(
            code="dwg_parser",
            title="DWG Parser",
            description="Parse AutoCAD DWG files",
            category="input",
            version="1.0.0",
            requires_external=["ODA File Converter"],
        )

        index.add_tool(
            code="area_calculator",
            title="Area Calculator",
            description="Calculate room areas",
            category="processing",
            version="1.0.0",
        )

        # Build and search
        index.build()
        results = index.search("parse DWG", top_k=5)

        assert len(results) > 0
        assert results[0].id == "dwg_parser"


class TestDocumentSearchIndex:
    """Test DocumentSearchIndex"""

    def test_add_documents(self):
        """Test adding documents to index"""
        from ..backends import FAISSSearchEngine

        engine = FAISSSearchEngine(namespace="test_docs")
        index = DocumentSearchIndex(
            namespace="test_docs",
            search_engine=engine,
            chunk_size=50,
            chunking_strategy="semantic",
        )

        # Add short document (no chunking)
        index.add_document(
            id="doc1",
            title="Short Document",
            content="This is a short document.",
            metadata={"type": "manual"},
            use_chunking=True,
        )

        # Add long document (with chunking)
        long_content = "\n\n".join([f"Paragraph {i} content goes here." for i in range(10)])

        index.add_document(
            id="doc2",
            title="Long Document",
            content=long_content,
            metadata={"type": "manual"},
            use_chunking=True,
        )

        # Build and search
        index.build()
        results = index.search("paragraph", top_k=5)

        assert len(results) > 0

    def test_chunking_metadata(self):
        """Test that chunk metadata is preserved"""
        from ..backends import FAISSSearchEngine

        engine = FAISSSearchEngine(namespace="test_chunk_meta")
        index = DocumentSearchIndex(
            namespace="test_chunk_meta", search_engine=engine, chunk_size=20
        )

        content = "\n\n".join([f"Section {i} text content." for i in range(5)])

        index.add_document(
            id="doc_chunked",
            title="Chunked Doc",
            content=content,
            metadata={"author": "test_author", "type": "guide"},
            use_chunking=True,
        )

        index.build()
        results = index.search("section", top_k=10)

        # Check chunk metadata
        for result in results:
            assert "author" in result.metadata
            assert result.metadata["author"] == "test_author"
            if "parent_id" in result.metadata:
                assert result.metadata["parent_id"] == "doc_chunked"


@pytest.mark.asyncio
async def test_async_search():
    """Test async search operations"""
    search = get_async_search_engine(namespace="test_async")

    # Add items
    search.add_item(id="async_item_1", text="Async test item one", metadata={"idx": 1})
    search.add_item(id="async_item_2", text="Async test item two", metadata={"idx": 2})

    # Build
    await search.build_index_async()

    # Single search
    results = await search.search_async("async test", top_k=5)
    assert len(results) > 0

    # Batch search
    queries = ["async", "test", "item"]
    all_results = await search.batch_search_async(queries, top_k=5)
    assert len(all_results) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
