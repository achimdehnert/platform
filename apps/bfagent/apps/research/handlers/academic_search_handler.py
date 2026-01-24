"""
Academic Search Handler
=======================

Specialized handler for academic/scientific research.
Focuses on peer-reviewed sources, proper citations, and scholarly databases.
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional
from datetime import datetime

from ..models import ResearchProject, ResearchSource, ResearchFinding, ResearchResult
from ..services import get_brave_search, get_research_service, get_academic_search, get_citation_service

logger = logging.getLogger(__name__)


@dataclass
class AcademicSearchResult:
    """Result of an academic search operation."""
    success: bool
    sources_found: int = 0
    peer_reviewed_count: int = 0
    citations_generated: int = 0
    bibtex_entries: str = ""
    error: Optional[str] = None


class AcademicSearchHandler:
    """
    Handler for academic/scientific research.
    
    Features:
    - Searches scholarly databases (Google Scholar, arXiv, PubMed)
    - Filters for peer-reviewed sources
    - Generates proper citations in multiple styles
    - Exports to BibTeX for LaTeX documents
    """
    
    handler_id = "academic_search"
    version = "1.0.0"
    domains = ["research"]
    
    # Academic source domains
    ACADEMIC_DOMAINS = [
        'scholar.google.com',
        'arxiv.org',
        'pubmed.ncbi.nlm.nih.gov',
        'ncbi.nlm.nih.gov',
        'doi.org',
        'researchgate.net',
        'semanticscholar.org',
        'jstor.org',
        'springer.com',
        'sciencedirect.com',
        'nature.com',
        'science.org',
        'ieee.org',
        'acm.org',
        'wiley.com',
        'tandfonline.com',
        'cambridge.org',
        'oxford.ac.uk',
    ]
    
    def __init__(self):
        self.brave_search = get_brave_search()
        self.academic_search = get_academic_search()
        self.citation_service = get_citation_service()
    
    def execute(
        self,
        project_id: int,
        query: str = "",
        options: dict = None
    ) -> dict:
        """
        Execute academic search for a research project.
        
        Args:
            project_id: ID of the research project
            query: Search query (uses project.query if not provided)
            options: Additional options (count, citation_style, etc.)
        
        Returns:
            Dictionary with search results
        """
        options = options or {}
        start_time = datetime.now()
        
        try:
            project = ResearchProject.objects.get(pk=project_id)
            
            # Use project query if not provided
            if not query:
                query = project.query
            
            if not query:
                return self._error_result("No search query provided")
            
            # Add academic focus to query
            academic_query = self._build_academic_query(query, options)
            
            # Search with Brave
            count = options.get('count', 20)
            search_results = self.brave_search.search(
                academic_query,
                count=count
            )
            
            if not search_results.get('success'):
                return self._error_result(
                    search_results.get('error', 'Search failed')
                )
            
            # Process and filter results
            sources_created = 0
            peer_reviewed_count = 0
            bibtex_entries = []
            
            for result in search_results.get('results', []):
                source = self._create_academic_source(project, result)
                if source:
                    sources_created += 1
                    if source.is_peer_reviewed:
                        peer_reviewed_count += 1
                        bibtex_entries.append(source.to_bibtex())
            
            # Generate citations list
            citation_style = options.get('citation_style', project.citation_style)
            citations = self._generate_citations(project, citation_style)
            
            # Store result
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            result_data = {
                'query': query,
                'academic_query': academic_query,
                'sources_found': sources_created,
                'peer_reviewed_count': peer_reviewed_count,
                'citation_style': citation_style,
                'citations': citations,
                'bibtex': '\n\n'.join(bibtex_entries),
            }
            
            ResearchResult.objects.create(
                project=project,
                handler_name=self.handler_id,
                phase='quellen_sammeln',
                result_data=result_data,
                success=True,
                execution_time_ms=int(execution_time)
            )
            
            # Update project phase
            if project.current_phase == 'thema_definieren':
                project.current_phase = 'quellen_sammeln'
                project.status = ResearchProject.Status.IN_PROGRESS
                project.save()
            
            return {
                'success': True,
                **result_data
            }
            
        except ResearchProject.DoesNotExist:
            return self._error_result(f"Project {project_id} not found")
        except Exception as e:
            logger.error(f"Academic search error: {e}", exc_info=True)
            return self._error_result(str(e))
    
    def _build_academic_query(self, query: str, options: dict) -> str:
        """Build an academic-focused search query."""
        # Add site filters for academic sources
        site_filter = options.get('site_filter', '')
        
        if not site_filter:
            # Default: focus on scholarly sources
            academic_terms = [
                'research',
                'study',
                'peer-reviewed',
                'journal',
                'academic',
            ]
            # Add one academic term if not already present
            query_lower = query.lower()
            if not any(term in query_lower for term in academic_terms):
                query = f"{query} research paper"
        
        return query
    
    def _create_academic_source(
        self,
        project: ResearchProject,
        result: dict
    ) -> Optional[ResearchSource]:
        """Create a ResearchSource from search result with academic metadata."""
        try:
            url = result.get('url', '')
            title = result.get('title', 'Unknown')
            
            # Determine if peer-reviewed based on domain
            is_peer_reviewed = self._is_academic_source(url)
            
            # Only include if project requires peer-reviewed and this is one
            if project.require_peer_reviewed and not is_peer_reviewed:
                return None
            
            # Determine source type
            source_type = self._determine_source_type(url, result)
            
            # Extract author info if available
            authors = self._extract_authors(result)
            
            # Extract DOI if present
            doi = self._extract_doi(url, result)
            
            # Calculate relevance and credibility
            relevance = result.get('relevance_score', 0.5)
            credibility = 0.9 if is_peer_reviewed else 0.5
            
            source = ResearchSource.objects.create(
                project=project,
                title=title,
                url=url,
                source_type=source_type,
                snippet=result.get('description', ''),
                relevance_score=relevance,
                credibility_score=credibility,
                is_peer_reviewed=is_peer_reviewed,
                authors=authors,
                doi=doi,
                metadata={
                    'search_position': result.get('position', 0),
                    'raw_result': result,
                }
            )
            
            return source
            
        except Exception as e:
            logger.warning(f"Failed to create academic source: {e}")
            return None
    
    def _is_academic_source(self, url: str) -> bool:
        """Check if URL is from an academic/peer-reviewed source."""
        url_lower = url.lower()
        return any(domain in url_lower for domain in self.ACADEMIC_DOMAINS)
    
    def _determine_source_type(self, url: str, result: dict) -> str:
        """Determine the academic source type."""
        url_lower = url.lower()
        
        if 'arxiv.org' in url_lower:
            return ResearchSource.SourceType.JOURNAL
        elif 'pubmed' in url_lower or 'ncbi.nlm.nih.gov' in url_lower:
            return ResearchSource.SourceType.JOURNAL
        elif 'doi.org' in url_lower:
            return ResearchSource.SourceType.JOURNAL
        elif any(ext in url_lower for ext in ['.pdf', '/pdf/']):
            return ResearchSource.SourceType.PDF
        elif 'conference' in url_lower or 'proceedings' in url_lower:
            return ResearchSource.SourceType.CONFERENCE
        elif 'thesis' in url_lower or 'dissertation' in url_lower:
            return ResearchSource.SourceType.THESIS
        elif 'book' in url_lower:
            return ResearchSource.SourceType.BOOK
        else:
            return ResearchSource.SourceType.ARTICLE
    
    def _extract_authors(self, result: dict) -> list:
        """Extract author names from search result."""
        authors = []
        
        # Try to extract from title or description
        # This is a simplified version - real implementation would parse more carefully
        description = result.get('description', '')
        
        # Look for common author patterns
        if ' by ' in description.lower():
            parts = description.lower().split(' by ')
            if len(parts) > 1:
                author_part = parts[1].split('.')[0].strip()
                if len(author_part) < 100:  # Sanity check
                    authors = [author_part.title()]
        
        return authors
    
    def _extract_doi(self, url: str, result: dict) -> str:
        """Extract DOI from URL or result metadata."""
        import re
        
        # Check URL for DOI
        doi_pattern = r'10\.\d{4,}/[^\s]+'
        
        match = re.search(doi_pattern, url)
        if match:
            return match.group(0)
        
        # Check description
        description = result.get('description', '')
        match = re.search(doi_pattern, description)
        if match:
            return match.group(0)
        
        return ''
    
    def _generate_citations(
        self,
        project: ResearchProject,
        style: str
    ) -> list:
        """Generate formatted citations for all project sources."""
        citations = []
        
        sources = project.sources.filter(
            is_peer_reviewed=True
        ).order_by('authors', 'publication_date')
        
        for source in sources:
            citation = source.format_citation(style)
            if citation:
                citations.append({
                    'source_id': source.pk,
                    'citation': citation,
                    'bibtex': source.to_bibtex(),
                })
        
        return citations
    
    def _error_result(self, error: str) -> dict:
        """Return error result."""
        return {
            'success': False,
            'error': error,
            'sources_found': 0,
        }
    
    def export_bibliography(
        self,
        project_id: int,
        format: str = 'bibtex'
    ) -> str:
        """
        Export project bibliography in specified format.
        
        Args:
            project_id: ID of the research project
            format: Output format ('bibtex', 'apa', 'mla', etc.)
        
        Returns:
            Formatted bibliography string
        """
        try:
            project = ResearchProject.objects.get(pk=project_id)
            sources = project.sources.filter(
                is_peer_reviewed=True
            ).order_by('authors', 'publication_date')
            
            if format == 'bibtex':
                entries = [source.to_bibtex() for source in sources]
                return '\n\n'.join(entries)
            else:
                citations = [source.format_citation(format) for source in sources]
                return '\n\n'.join(citations)
                
        except ResearchProject.DoesNotExist:
            return ""
