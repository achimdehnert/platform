"""
Research Integration Service for Writing Hub
=============================================

Provides seamless access to Research Hub services for:
- Scientific papers (literature review, fact-checking)
- Non-fiction books (research, citations)
- Any content requiring factual backing

This integration makes Research Hub a SERVICE for Writing Hub,
not a separate standalone application.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class LiteratureSearchResult:
    """Result from a literature search for scientific writing."""
    success: bool
    query: str
    sources: List[Dict] = field(default_factory=list)
    academic_sources: List[Dict] = field(default_factory=list)
    citation_ready: List[Dict] = field(default_factory=list)
    total_found: int = 0
    errors: List[str] = field(default_factory=list)
    
    def to_citations(self, style: str = 'APA') -> List[str]:
        """Convert sources to formatted citations."""
        citations = []
        for source in self.citation_ready:
            # Basic APA format
            authors = source.get('authors', ['Unknown'])
            year = source.get('year', 'n.d.')
            title = source.get('title', 'Untitled')
            journal = source.get('journal', '')
            
            if style == 'APA':
                author_str = ', '.join(authors[:3])
                if len(authors) > 3:
                    author_str += ' et al.'
                citation = f"{author_str} ({year}). {title}."
                if journal:
                    citation += f" {journal}."
                citations.append(citation)
        return citations


class WritingResearchService:
    """
    Unified research service for Writing Hub.
    
    Wraps Research Hub services with Writing-specific functionality:
    - Literature review for scientific papers
    - Fact-checking for non-fiction
    - Source collection with citation formatting
    
    Usage:
        from apps.writing_hub.services.research_integration import get_writing_research
        
        research = get_writing_research()
        
        # For scientific papers
        sources = research.find_literature(
            topic="Machine Learning in Healthcare",
            paper_type="empirical",
            peer_reviewed_only=True
        )
        
        # For fact-checking
        verified = research.verify_claim(
            claim="AI can detect cancer with 95% accuracy",
            context="medical_imaging"
        )
    """
    
    def __init__(self):
        """Initialize with Research Hub services."""
        self._research_service = None
        self._academic_service = None
        self._summary_service = None
    
    @property
    def research_service(self):
        """Lazy load research service."""
        if self._research_service is None:
            try:
                from apps.research.services import get_research_service
                self._research_service = get_research_service()
            except ImportError:
                logger.warning("Research Hub not available - using mock service")
                self._research_service = MockResearchService()
        return self._research_service
    
    @property
    def academic_service(self):
        """Lazy load academic search service."""
        if self._academic_service is None:
            try:
                from apps.research.services import get_academic_search
                self._academic_service = get_academic_search()
            except ImportError:
                logger.warning("Academic Search not available")
                self._academic_service = None
        return self._academic_service
    
    @property
    def summary_service(self):
        """Lazy load AI summary service."""
        if self._summary_service is None:
            try:
                from apps.research.services import get_ai_summary_service
                self._summary_service = get_ai_summary_service()
            except ImportError:
                logger.warning("AI Summary service not available")
                self._summary_service = None
        return self._summary_service
    
    # =========================================================================
    # Literature Search (for Scientific Writing)
    # =========================================================================
    
    def find_literature(
        self,
        topic: str,
        paper_type: str = 'any',
        peer_reviewed_only: bool = False,
        max_results: int = 20,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        domains: Optional[List[str]] = None
    ) -> LiteratureSearchResult:
        """
        Find academic literature for scientific writing.
        
        Args:
            topic: Research topic or question
            paper_type: 'empirical', 'theoretical', 'review', 'any'
            peer_reviewed_only: Only include peer-reviewed sources
            max_results: Maximum number of results
            year_from: Filter by publication year (from)
            year_to: Filter by publication year (to)
            domains: Academic domains to search (e.g., ['computer_science', 'medicine'])
        
        Returns:
            LiteratureSearchResult with sources ready for citations
        """
        try:
            # Use academic search if available
            if self.academic_service:
                result = self.academic_service.search(
                    query=topic,
                    filters={
                        'peer_reviewed': peer_reviewed_only,
                        'paper_type': paper_type,
                        'year_from': year_from,
                        'year_to': year_to,
                        'domains': domains or []
                    },
                    max_results=max_results
                )
                
                return LiteratureSearchResult(
                    success=result.success if hasattr(result, 'success') else True,
                    query=topic,
                    sources=result.sources if hasattr(result, 'sources') else [],
                    academic_sources=result.academic_sources if hasattr(result, 'academic_sources') else [],
                    citation_ready=self._prepare_citations(result),
                    total_found=len(result.sources) if hasattr(result, 'sources') else 0
                )
            
            # Fallback to general research
            result = self.research_service.research(
                query=topic,
                options={
                    'max_sources': max_results,
                    'academic_only': peer_reviewed_only
                }
            )
            
            return LiteratureSearchResult(
                success=result.success,
                query=topic,
                sources=result.sources,
                total_found=len(result.sources)
            )
            
        except Exception as e:
            logger.error(f"Literature search failed: {e}")
            return LiteratureSearchResult(
                success=False,
                query=topic,
                errors=[str(e)]
            )
    
    def _prepare_citations(self, result) -> List[Dict]:
        """Prepare sources for citation formatting."""
        citations = []
        sources = getattr(result, 'sources', []) or []
        
        for source in sources:
            citation = {
                'title': source.get('title', ''),
                'authors': source.get('authors', []),
                'year': source.get('publication_date', '')[:4] if source.get('publication_date') else '',
                'journal': source.get('journal_name', ''),
                'volume': source.get('volume', ''),
                'issue': source.get('issue', ''),
                'pages': source.get('pages', ''),
                'doi': source.get('doi', ''),
                'url': source.get('url', ''),
                'is_peer_reviewed': source.get('is_peer_reviewed', False)
            }
            citations.append(citation)
        
        return citations
    
    # =========================================================================
    # Fact Checking (for Non-Fiction)
    # =========================================================================
    
    def verify_claim(
        self,
        claim: str,
        context: Optional[str] = None,
        require_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Verify a factual claim with sources.
        
        Args:
            claim: The claim to verify
            context: Additional context (e.g., 'medical', 'historical')
            require_sources: Whether to require supporting sources
        
        Returns:
            Dict with verification result and sources
        """
        try:
            result = self.research_service.research(
                query=f"fact check: {claim}",
                options={
                    'max_sources': 5,
                    'domain': context
                }
            )
            
            return {
                'success': True,
                'claim': claim,
                'verified': len(result.sources) > 0,
                'confidence': self._calculate_confidence(result.sources),
                'sources': result.sources,
                'summary': result.summary
            }
            
        except Exception as e:
            logger.error(f"Fact check failed: {e}")
            return {
                'success': False,
                'claim': claim,
                'error': str(e)
            }
    
    def _calculate_confidence(self, sources: List[Dict]) -> float:
        """Calculate confidence score based on sources."""
        if not sources:
            return 0.0
        
        # Simple confidence based on number and quality of sources
        base_score = min(len(sources) / 5, 1.0) * 0.5
        
        # Bonus for peer-reviewed sources
        peer_reviewed = sum(1 for s in sources if s.get('is_peer_reviewed'))
        peer_bonus = (peer_reviewed / len(sources)) * 0.3 if sources else 0
        
        # Bonus for high relevance scores
        avg_relevance = sum(s.get('relevance_score', 0.5) for s in sources) / len(sources)
        relevance_bonus = avg_relevance * 0.2
        
        return min(base_score + peer_bonus + relevance_bonus, 1.0)
    
    # =========================================================================
    # Research Summary (for any content type)
    # =========================================================================
    
    def summarize_topic(
        self,
        topic: str,
        max_words: int = 500,
        style: str = 'academic'
    ) -> Dict[str, Any]:
        """
        Generate a research summary for a topic.
        
        Args:
            topic: Topic to research and summarize
            max_words: Maximum words in summary
            style: 'academic', 'journalistic', 'simple'
        
        Returns:
            Dict with summary and sources
        """
        try:
            # First, gather sources
            result = self.research_service.research(
                query=topic,
                options={'max_sources': 10}
            )
            
            # Then summarize if service available
            if self.summary_service and result.sources:
                summary = self.summary_service.summarize(
                    sources=result.sources,
                    style=style,
                    max_words=max_words
                )
                return {
                    'success': True,
                    'topic': topic,
                    'summary': summary,
                    'sources': result.sources,
                    'word_count': len(summary.split()) if summary else 0
                }
            
            return {
                'success': True,
                'topic': topic,
                'summary': result.summary,
                'sources': result.sources
            }
            
        except Exception as e:
            logger.error(f"Topic summary failed: {e}")
            return {
                'success': False,
                'topic': topic,
                'error': str(e)
            }


class MockResearchService:
    """Mock service when Research Hub is not available."""
    
    def research(self, query: str, options: Optional[Dict] = None):
        """Return empty result."""
        from dataclasses import dataclass, field
        from typing import List, Dict, Optional
        
        @dataclass
        class MockResult:
            success: bool = True
            query: str = ""
            sources: List[Dict] = field(default_factory=list)
            summary: Optional[str] = None
        
        return MockResult(query=query)


# Singleton instance
_writing_research_service: Optional[WritingResearchService] = None


def get_writing_research() -> WritingResearchService:
    """Get or create the Writing Research Service singleton."""
    global _writing_research_service
    if _writing_research_service is None:
        _writing_research_service = WritingResearchService()
    return _writing_research_service
