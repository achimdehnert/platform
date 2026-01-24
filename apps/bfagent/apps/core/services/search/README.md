# Core Semantic Search Service

**Production-ready semantic search for BF Agent applications**

## 🎯 Features

- **FAISS-based semantic search** - Fast and accurate similarity search
- **Multi-index support** - Isolated namespaces for different data types
- **Document chunking** - Smart text chunking for long documents
- **Advanced filtering** - Complex metadata filtering with boolean logic
- **Async operations** - Non-blocking search and indexing
- **Caching** - Hash-based cache invalidation for fast rebuilds
- **German language support** - Optimized embedding models available
- **Type-safe** - Full Pydantic model support

---

## 📦 Installation

### Required Dependencies

```bash
pip install sentence-transformers faiss-cpu numpy
```

### Optional Dependencies

```bash
# For advanced features
pip install rank-bm25  # Hybrid search (Phase 2)

# For reranking (Phase 3)
pip install sentence-transformers[cross-encoder]

# For GPU acceleration
pip install faiss-gpu  # Instead of faiss-cpu
```

---

## 🚀 Quick Start

### 1. Basic Search

```python
from apps.core.services.search import get_search_engine

# Create search engine
search = get_search_engine(namespace="my_tools")

# Add items
search.add_item(
    id="parser_1",
    text="DWG/DXF Parser: Parse AutoCAD files and extract geometry",
    metadata={"category": "input", "version": "1.0.0"}
)

search.add_item(
    id="calculator_1",
    text="Area Calculator: Calculate room areas according to DIN 277",
    metadata={"category": "processing", "version": "1.0.0"}
)

# Build index
search.build_index()

# Search
results = search.search("parse DXF files", top_k=5)

for result in results:
    print(f"{result.id}: {result.score:.2f}")
```

### 2. Tool Search Index

```python
from apps.core.services.search import ToolSearchIndex, FAISSSearchEngine

# Create specialized tool index
engine = FAISSSearchEngine(namespace="cad_tools")
index = ToolSearchIndex(namespace="cad_tools", search_engine=engine)

# Add tools
index.add_tool(
    code="dwg_parser",
    title="DWG/DXF Parser",
    description="Parse AutoCAD files",
    category="input",
    version="1.0.0",
    requires_external=["ODA File Converter"]
)

# Build and search
index.build()
results = index.search("parse DWG", top_k=5)
```

### 3. Document Search with Chunking

```python
from apps.core.services.search import DocumentSearchIndex, FAISSSearchEngine

# Create document index with chunking
engine = FAISSSearchEngine(namespace="chapters")
index = DocumentSearchIndex(
    namespace="chapters",
    search_engine=engine,
    chunk_size=512,
    chunk_overlap=50,
    chunking_strategy="semantic"
)

# Add long document (will be automatically chunked)
index.add_document(
    id="chapter_1",
    title="Chapter 1: Introduction",
    content="Very long chapter content...",  # 10,000+ words
    metadata={"book_id": 42},
    use_chunking=True
)

# Search finds relevant chunks
results = index.search("character development", top_k=5)
```

### 4. Filtered Search

```python
from apps.core.services.search import FilterBuilder

# Build complex filter
filter_obj = (
    FilterBuilder()
    .equals("category", "processing")
    .greater_than("version", "1.0.0")
    .in_list("status", ["active", "beta"])
    .build()
)

# Search with filters
results = search.search(
    query="calculate areas",
    top_k=10,
    filters={
        "category": "processing",
        "version": {"operator": "gte", "value": "1.0.0"}
    }
)
```

### 5. Async Search

```python
from apps.core.services.search import get_async_search_engine

# Create async engine
search = get_async_search_engine(namespace="async_tools")

# Add items
search.add_item(id="item_1", text="First item", metadata={})

# Build async
await search.build_index_async()

# Single async search
results = await search.search_async("query", top_k=5)

# Batch search (parallel)
queries = ["query1", "query2", "query3"]
all_results = await search.batch_search_async(queries, top_k=5)
```

---

## 🏗️ Architecture

```
apps/core/services/search/
├── __init__.py              # Public API
├── base.py                  # BaseSearchEngine, SearchIndex
├── factory.py               # get_search_engine(), get_async_search_engine()
├── models.py                # Pydantic models
├── exceptions.py            # Custom exceptions
├── filtering.py             # MetadataFilter, FilterBuilder
├── chunking.py              # DocumentChunker
├── backends/
│   ├── faiss_backend.py     # FAISS implementation
│   └── async_faiss_backend.py  # Async wrapper
└── indexes/
    ├── tool_index.py        # ToolSearchIndex
    └── document_index.py    # DocumentSearchIndex
```

---

## 📊 Configuration

### Django Settings

```python
# settings.py

# Optional: Configure search defaults
SEARCH_BACKEND = "faiss"
SEARCH_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# German-optimized model
# SEARCH_EMBEDDING_MODEL = "deutsche-telekom/gbert-large-paraphrase-cosine"
```

### Search Config

```python
from apps.core.services.search import SearchConfig, SearchBackend

config = SearchConfig(
    backend=SearchBackend.FAISS,
    model="all-MiniLM-L6-v2",
    device="cpu",  # or "cuda" for GPU
    min_score=0.35,  # Minimum similarity score
    relative_threshold=0.90,  # Relative to top score
    cache_dir="~/.bfagent/search"
)

search = get_search_engine(namespace="custom", config=config)
```

---

## 🎨 Available Embedding Models

### Fast & Lightweight (384 dim)
- `all-MiniLM-L6-v2` - **Default**, good balance of speed and quality

### Better Quality (768 dim)
- `all-mpnet-base-v2` - Higher quality, slower

### German-Optimized (768 dim)
- `deutsche-telekom/gbert-large-paraphrase-cosine` - **Best for German text**

### Multilingual (768 dim)
- `intfloat/multilingual-e5-large` - 100+ languages

### Domain-Specific
- `microsoft/codebert-base` - Code search
- `pritamdeka/S-PubMedBert-MS-MARCO` - Medical/biomedical

---

## 🔍 Advanced Features

### Metadata Filtering Operators

```python
filter_obj = MetadataFilter()

# Equality
filter_obj.add_filter("category", "eq", "input")
filter_obj.add_filter("status", "ne", "inactive")

# Lists
filter_obj.add_filter("status", "in", ["active", "beta"])

# Comparisons
filter_obj.add_filter("version", "gte", "1.0.0")
filter_obj.add_filter("score", "lt", 0.5)

# String operations
filter_obj.add_filter("tags", "contains", "important")

# Existence
filter_obj.add_filter("optional_field", "exists", None)
```

### Document Chunking Strategies

```python
# Semantic chunking (paragraph boundaries)
chunker = DocumentChunker(
    chunk_size=512,
    chunk_overlap=50,
    strategy="semantic"  # Best for natural text
)

# Sentence chunking
chunker = DocumentChunker(
    chunk_size=256,
    chunk_overlap=25,
    strategy="sentence"  # Best for precise chunks
)

# Fixed chunking
chunker = DocumentChunker(
    chunk_size=512,
    chunk_overlap=50,
    strategy="fixed"  # Simple word-based
)
```

### Multi-Index Isolation

```python
# Separate indexes for different data types
tools_search = get_search_engine(namespace="tools")
chapters_search = get_search_engine(namespace="chapters")
kb_search = get_search_engine(namespace="knowledge_base")

# Each has isolated cache and index
# No conflicts between different data types
```

---

## 🧪 Testing

### Run Tests

```bash
# Basic tests (no dependencies required)
pytest apps/core/services/search/tests/test_search_basic.py -v

# Integration tests (requires FAISS + Sentence Transformers)
pytest apps/core/services/search/tests/test_search_integration.py -v

# All tests
pytest apps/core/services/search/tests/ -v
```

### Demo Script

```bash
# Run interactive demo
python examples/search_service_demo.py
```

---

## 📝 API Reference

### Factory Functions

#### `get_search_engine(backend, namespace, model, config, **kwargs)`
Create a search engine instance.

**Parameters:**
- `backend` (str): Backend type ("faiss", "postgres_vector")
- `namespace` (str): Index namespace for isolation
- `model` (str): Embedding model name
- `config` (SearchConfig): Configuration object
- `**kwargs`: Backend-specific options

**Returns:** `BaseSearchEngine`

#### `get_async_search_engine(...)`
Create an async search engine instance.

### BaseSearchEngine Methods

#### `add_item(id, text, metadata=None)`
Add single item to index.

#### `add_items(items)`
Add multiple items (bulk operation).

#### `build_index()`
Build/rebuild the search index.

#### `search(query, top_k=10, filters=None)`
Search for similar items.

**Returns:** `List[SearchResult]`

#### `is_available()`
Check if backend dependencies are available.

#### `is_built()`
Check if index is built.

#### `clear()`
Clear all indexed items.

### SearchResult Model

```python
class SearchResult(BaseModel):
    id: str
    score: float  # Similarity score (0-1)
    title: str
    description: str
    content: str
    metadata: Dict[str, Any]
```

---

## 🎯 Use Cases

### 1. Tool/Handler Discovery
Find relevant tools based on semantic queries.

```python
tool_index = ToolSearchIndex(namespace="handlers")
results = tool_index.search("parse DWG files")
```

### 2. Document Search (Writing Hub)
Search through chapters, characters, world-building docs.

```python
doc_index = DocumentSearchIndex(namespace="writing_chapters")
results = doc_index.search("character development arc")
```

### 3. Knowledge Base Search (Expert Hub)
Search technical documentation and guides.

```python
kb_index = DocumentSearchIndex(namespace="expert_kb")
results = kb_index.search("ATEX compliance requirements")
```

### 4. Code Search
Search code snippets and implementations.

```python
code_search = get_search_engine(
    namespace="code",
    model="microsoft/codebert-base"
)
results = code_search.search("Django view authentication")
```

---

## 🔧 Troubleshooting

### Dependencies Not Available

```python
from apps.core.services.search import is_available

if not is_available():
    print("Install: pip install sentence-transformers faiss-cpu")
```

### Index Not Built Error

```python
from apps.core.services.search.exceptions import SearchIndexNotBuilt

try:
    results = search.search("query")
except SearchIndexNotBuilt:
    search.build_index()
    results = search.search("query")
```

### Cache Issues

```bash
# Clear cache manually
rm -rf ~/.bfagent/search/
```

---

## 🚀 Performance Tips

1. **Use appropriate chunk sizes** - Smaller chunks = more precise, larger = more context
2. **Cache indexes** - Indexes are automatically cached and reused
3. **Use async for batch operations** - Process multiple queries in parallel
4. **Filter early** - Apply metadata filters to reduce search space
5. **GPU acceleration** - Use `faiss-gpu` for large indexes (10k+ items)

---

## 📚 Further Reading

- [FAISS Documentation](https://github.com/facebookresearch/faiss)
- [Sentence Transformers](https://www.sbert.net/)
- [BF Agent Architecture](../../docs/ARCHITECTURE_PROPOSAL_SEMANTIC_SEARCH.md)

---

## 🎉 Phase 1 Complete

**Status:** ✅ Production Ready

**Implemented:**
- ✅ Multi-index support
- ✅ FAISS backend
- ✅ Async operations
- ✅ Document chunking
- ✅ Advanced filtering
- ✅ Specialized indexes
- ✅ Full test coverage
- ✅ Comprehensive documentation

**Next Phases:**
- Phase 2: Hybrid Search (BM25 + FAISS)
- Phase 3: Advanced features (reranking, multi-language)
