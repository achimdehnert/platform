"""
Vector Store Service
====================

Semantic search over research documents using vector embeddings.
Supports ChromaDB (local) and optional Pinecone (cloud).
"""

import logging
import hashlib
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class VectorStoreService:
    """
    Vector database for semantic search over research documents.
    
    Usage:
        service = VectorStoreService()
        service.add_document("doc1", "Machine learning in healthcare...")
        results = service.search("AI medical diagnosis", top_k=5)
    """
    
    def __init__(self, collection_name: str = "research_hub"):
        self.collection_name = collection_name
        self._client = None
        self._collection = None
        self._embedding_fn = None
    
    @property
    def client(self):
        """Lazy-load ChromaDB client."""
        if self._client is None:
            self._client = self._init_chromadb()
        return self._client
    
    @property
    def collection(self):
        """Get or create collection."""
        if self._collection is None and self.client:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Research Hub Knowledge Base"}
            )
        return self._collection
    
    def _init_chromadb(self):
        """Initialize ChromaDB client."""
        try:
            import chromadb
            from chromadb.config import Settings
            
            # Use persistent storage
            persist_dir = Path("data/chromadb")
            persist_dir.mkdir(parents=True, exist_ok=True)
            
            client = chromadb.PersistentClient(
                path=str(persist_dir),
                settings=Settings(anonymized_telemetry=False)
            )
            logger.info(f"ChromaDB initialized at {persist_dir}")
            return client
            
        except ImportError:
            logger.warning("ChromaDB not installed. Install with: pip install chromadb")
            return None
        except Exception as e:
            logger.error(f"ChromaDB initialization failed: {e}")
            return None
    
    def _get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for text.
        
        Uses sentence-transformers if available, otherwise falls back
        to a simple hash-based pseudo-embedding for testing.
        """
        if self._embedding_fn is None:
            try:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer('all-MiniLM-L6-v2')
                self._embedding_fn = lambda t: model.encode(t).tolist()
                logger.info("Using sentence-transformers for embeddings")
            except ImportError:
                logger.warning("sentence-transformers not available, using fallback")
                self._embedding_fn = self._fallback_embedding
        
        return self._embedding_fn(text)
    
    def _fallback_embedding(self, text: str) -> List[float]:
        """Simple hash-based pseudo-embedding for testing."""
        # Create a deterministic 384-dim vector from text hash
        import struct
        
        # Hash the text
        h = hashlib.sha384(text.encode()).digest()
        
        # Convert to floats between -1 and 1
        embedding = []
        for i in range(0, len(h), 4):
            chunk = h[i:i+4]
            if len(chunk) == 4:
                val = struct.unpack('f', chunk)[0]
                # Normalize to [-1, 1]
                normalized = max(-1.0, min(1.0, val / 1e38))
                embedding.append(normalized)
        
        # Pad to 384 dimensions
        while len(embedding) < 384:
            embedding.append(0.0)
        
        return embedding[:384]
    
    def add_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Add a document to the vector store.
        
        Args:
            doc_id: Unique document identifier
            content: Document text content
            metadata: Optional metadata dict
            
        Returns:
            True if successful
        """
        if not self.collection:
            logger.warning("Vector store not available")
            return False
        
        try:
            # Truncate content for embedding (most models have limits)
            truncated = content[:8000] if len(content) > 8000 else content
            
            self.collection.upsert(
                ids=[doc_id],
                documents=[truncated],
                metadatas=[metadata or {}]
            )
            logger.debug(f"Added document {doc_id} to vector store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add document {doc_id}: {e}")
            return False
    
    def add_documents(
        self,
        documents: List[Dict]
    ) -> int:
        """
        Add multiple documents to the vector store.
        
        Args:
            documents: List of dicts with 'id', 'content', and optional 'metadata'
            
        Returns:
            Number of documents successfully added
        """
        if not self.collection:
            return 0
        
        added = 0
        for doc in documents:
            if self.add_document(
                doc_id=doc.get('id', str(hash(doc.get('content', '')))),
                content=doc.get('content', ''),
                metadata=doc.get('metadata')
            ):
                added += 1
        
        return added
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Semantic search over documents.
        
        Args:
            query: Search query
            top_k: Number of results to return
            filter_metadata: Optional metadata filter
            
        Returns:
            List of result dicts with 'id', 'content', 'score', 'metadata'
        """
        if not self.collection:
            logger.warning("Vector store not available for search")
            return []
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=filter_metadata
            )
            
            # Format results
            formatted = []
            if results and results['ids'] and results['ids'][0]:
                for i, doc_id in enumerate(results['ids'][0]):
                    formatted.append({
                        'id': doc_id,
                        'content': results['documents'][0][i] if results['documents'] else '',
                        'score': 1 - results['distances'][0][i] if results['distances'] else 0,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {}
                    })
            
            return formatted
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the vector store."""
        if not self.collection:
            return False
        
        try:
            self.collection.delete(ids=[doc_id])
            return True
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get vector store statistics."""
        if not self.collection:
            return {'available': False, 'count': 0}
        
        try:
            return {
                'available': True,
                'collection': self.collection_name,
                'count': self.collection.count(),
            }
        except Exception as e:
            return {'available': False, 'error': str(e)}
    
    def index_research_project(self, project) -> int:
        """
        Index all content from a research project.
        
        Args:
            project: ResearchProject instance
            
        Returns:
            Number of documents indexed
        """
        documents = []
        
        # Index project description
        if project.description:
            documents.append({
                'id': f"project_{project.pk}_desc",
                'content': f"{project.name}\n\n{project.description}",
                'metadata': {
                    'type': 'project',
                    'project_id': project.pk,
                    'name': project.name
                }
            })
        
        # Index findings
        for finding in project.findings.all():
            documents.append({
                'id': f"finding_{finding.pk}",
                'content': f"{finding.title}\n\n{finding.content}",
                'metadata': {
                    'type': 'finding',
                    'project_id': project.pk,
                    'finding_id': finding.pk,
                    'title': finding.title
                }
            })
        
        # Index sources
        for source in project.sources.all():
            if source.snippet:
                documents.append({
                    'id': f"source_{source.pk}",
                    'content': f"{source.title}\n\n{source.snippet}",
                    'metadata': {
                        'type': 'source',
                        'project_id': project.pk,
                        'source_id': source.pk,
                        'url': source.url
                    }
                })
        
        return self.add_documents(documents)


# Singleton instance
_vector_store = None

def get_vector_store(collection_name: str = "research_hub") -> VectorStoreService:
    """Get singleton instance of VectorStoreService."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreService(collection_name)
    return _vector_store
