"""
Research Service
================

Central research service for all domains.
Coordinates web search, knowledge base, and analysis.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from .brave_search_service import BraveSearchService, get_brave_search

logger = logging.getLogger(__name__)


@dataclass
class ResearchContext:
    """Context for a research session."""
    query: str
    domain: Optional[str] = None
    max_sources: int = 10
    include_local: bool = False
    language: str = 'de'
    filters: Dict = field(default_factory=dict)


@dataclass
class ResearchOutput:
    """Output from a research operation."""
    success: bool
    query: str
    sources: List[Dict] = field(default_factory=list)
    findings: List[Dict] = field(default_factory=list)
    summary: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'success': self.success,
            'query': self.query,
            'sources': self.sources,
            'findings': self.findings,
            'summary': self.summary,
            'metadata': self.metadata,
            'errors': self.errors
        }


class ResearchService:
    """
    Central research service providing unified research capabilities.
    
    This service can be used by all domains:
    - Books: Research for non-fiction, historical novels
    - MedTrans: Medical fact checking
    - PPTX Studio: Content generation
    - Science Writer: Literature review
    
    Usage:
        service = ResearchService()
        result = service.research(
            query="AI developments in healthcare 2024",
            options={'max_sources': 10, 'domain': 'medtrans'}
        )
    """
    
    def __init__(self):
        """Initialize research service with dependencies."""
        self.brave_search = get_brave_search()
        self._knowledge_base = None  # TODO: Add vector DB integration
    
    def research(
        self,
        query: str,
        options: Optional[Dict] = None
    ) -> ResearchOutput:
        """
        Perform comprehensive research on a topic.
        
        Args:
            query: Research query/topic
            options: Research options
                - max_sources: Maximum sources to collect (default: 10)
                - domain: Calling domain for context (e.g., 'books', 'medtrans')
                - include_local: Include local search results
                - language: Target language (default: 'de')
                - filters: Additional filters
                
        Returns:
            ResearchOutput with sources, findings, and summary
        """
        options = options or {}
        context = ResearchContext(
            query=query,
            domain=options.get('domain'),
            max_sources=options.get('max_sources', 10),
            include_local=options.get('include_local', False),
            language=options.get('language', 'de'),
            filters=options.get('filters', {})
        )
        
        output = ResearchOutput(
            success=True,
            query=query,
            metadata={
                'started_at': datetime.now().isoformat(),
                'domain': context.domain,
                'language': context.language
            }
        )
        
        try:
            # Step 1: Web Search
            web_results = self._perform_web_search(context)
            output.sources.extend(web_results)
            
            # Step 2: Knowledge Base Search (if available)
            if self._knowledge_base:
                kb_results = self._search_knowledge_base(context)
                output.sources.extend(kb_results)
            
            # Step 3: Extract Key Findings
            output.findings = self._extract_findings(output.sources, context)
            
            # Step 4: Generate Summary
            output.summary = self._generate_summary(output.findings, context)
            
            output.metadata['completed_at'] = datetime.now().isoformat()
            output.metadata['source_count'] = len(output.sources)
            output.metadata['finding_count'] = len(output.findings)
            
        except Exception as e:
            logger.error(f"Research error: {e}", exc_info=True)
            output.success = False
            output.errors.append(str(e))
        
        return output
    
    def quick_search(
        self,
        query: str,
        count: int = 5
    ) -> List[Dict]:
        """
        Quick web search without full research workflow.
        
        Args:
            query: Search query
            count: Number of results
            
        Returns:
            List of search results
        """
        result = self.brave_search.search(query, count=count)
        return result.get('results', [])
    
    def fact_check(
        self,
        claim: str,
        context: Optional[str] = None
    ) -> Dict:
        """
        Verify a claim or statement.
        
        Args:
            claim: The claim to verify
            context: Optional additional context
            
        Returns:
            Dict with verification result, confidence, and sources
        """
        # Search for evidence
        search_query = f'fact check: {claim}'
        if context:
            search_query = f'{context} {search_query}'
        
        results = self.brave_search.search(search_query, count=5)
        
        # Analyze results for verification
        sources = results.get('results', [])
        
        # Simple verification logic (to be enhanced with AI)
        verification = {
            'claim': claim,
            'verified': None,  # True/False/None (unknown)
            'confidence': 0.0,
            'sources': sources,
            'notes': []
        }
        
        if sources:
            # Check if claim terms appear in results
            claim_terms = set(claim.lower().split())
            match_count = 0
            
            for source in sources:
                desc = source.get('description', '').lower()
                title = source.get('title', '').lower()
                matches = sum(1 for term in claim_terms if term in desc or term in title)
                if matches > len(claim_terms) * 0.5:
                    match_count += 1
            
            if match_count >= 3:
                verification['verified'] = True
                verification['confidence'] = 0.7 + (match_count * 0.05)
            elif match_count >= 1:
                verification['verified'] = None
                verification['confidence'] = 0.4 + (match_count * 0.1)
            else:
                verification['verified'] = False
                verification['confidence'] = 0.3
            
            verification['notes'].append(
                f"Found {match_count} supporting sources out of {len(sources)}"
            )
        
        return verification
    
    def _perform_web_search(self, context: ResearchContext) -> List[Dict]:
        """Perform web search and format results."""
        results = []
        
        # Main search
        search_result = self.brave_search.search(
            context.query,
            count=context.max_sources
        )
        
        if search_result.get('success'):
            for item in search_result.get('results', []):
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('url', ''),
                    'snippet': item.get('description', ''),
                    'source_type': 'web',
                    'relevance_score': 0.8,  # Default high relevance
                    'credibility_score': 0.5,  # Default medium credibility
                    'metadata': {
                        'age': item.get('age'),
                        'extra_snippets': item.get('extra_snippets', [])
                    }
                })
        
        # Local search if requested
        if context.include_local:
            local_result = self.brave_search.local_search(
                context.query,
                count=5
            )
            if local_result.get('success'):
                for item in local_result.get('results', []):
                    results.append({
                        'title': item.get('name', ''),
                        'address': item.get('address', ''),
                        'source_type': 'local',
                        'relevance_score': 0.7,
                        'metadata': item
                    })
        
        return results
    
    def _search_knowledge_base(self, context: ResearchContext) -> List[Dict]:
        """Search internal knowledge base (placeholder)."""
        # TODO: Implement vector DB search (ChromaDB/Pinecone)
        return []
    
    def _extract_findings(
        self,
        sources: List[Dict],
        context: ResearchContext
    ) -> List[Dict]:
        """Extract key findings from sources."""
        findings = []
        
        for source in sources[:5]:  # Top 5 sources
            snippet = source.get('snippet', '')
            if snippet:
                # Extract sentences as findings
                sentences = [s.strip() for s in snippet.split('.') if len(s.strip()) > 20]
                for sentence in sentences[:2]:
                    findings.append({
                        'content': sentence + '.',
                        'finding_type': 'fact',
                        'source_title': source.get('title', ''),
                        'source_url': source.get('url', ''),
                        'importance': 5
                    })
        
        return findings
    
    def _generate_summary(
        self,
        findings: List[Dict],
        context: ResearchContext
    ) -> str:
        """Generate summary from findings."""
        if not findings:
            return f"Keine relevanten Ergebnisse für '{context.query}' gefunden."
        
        # Simple summary (to be enhanced with AI)
        summary_parts = [
            f"Recherche zu: {context.query}",
            f"Gefundene Erkenntnisse: {len(findings)}",
            "",
            "Wichtigste Ergebnisse:"
        ]
        
        for i, finding in enumerate(findings[:5], 1):
            summary_parts.append(f"{i}. {finding['content']}")
        
        return "\n".join(summary_parts)


# Singleton instance
_research_service = None

def get_research_service() -> ResearchService:
    """Get singleton instance of ResearchService."""
    global _research_service
    if _research_service is None:
        _research_service = ResearchService()
    return _research_service
