"""
Web Search Handler
==================

Handler for web search operations using Brave Search.
"""

import logging
import time
from typing import Dict, Any, Optional

from ..services import BraveSearchService, get_brave_search
from ..models import ResearchProject, ResearchSource, ResearchResult

logger = logging.getLogger(__name__)


class WebSearchHandler:
    """
    Handler for web search operations.
    
    Performs web searches using Brave Search API and stores results.
    
    Usage:
        handler = WebSearchHandler()
        result = handler.execute(project_id=1, query="AI developments")
    """
    
    name = "WebSearchHandler"
    description = "Performs web searches using Brave Search API"
    phase = "quellen_sammeln"
    
    def __init__(self):
        """Initialize handler with search service."""
        self.search_service = get_brave_search()
    
    def execute(
        self,
        project_id: int,
        query: Optional[str] = None,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Execute web search for a research project.
        
        Args:
            project_id: ID of the research project
            query: Search query (uses project query if not provided)
            options: Additional options
                - count: Number of results (default: 10)
                - offset: Pagination offset
                
        Returns:
            Dict with success status, sources found, and metadata
        """
        start_time = time.time()
        options = options or {}
        
        try:
            # Get project
            project = ResearchProject.objects.get(id=project_id)
            
            # Use provided query or project query
            search_query = query or project.query or project.name
            
            if not search_query:
                return {
                    'success': False,
                    'error': 'No search query provided',
                    'handler': self.name
                }
            
            # Perform search
            count = options.get('count', 10)
            offset = options.get('offset', 0)
            
            search_result = self.search_service.search(
                search_query,
                count=count,
                offset=offset
            )
            
            if not search_result.get('success', False):
                return {
                    'success': False,
                    'error': search_result.get('error', 'Search failed'),
                    'handler': self.name
                }
            
            # Store sources
            sources_created = []
            for item in search_result.get('results', []):
                source = ResearchSource.objects.create(
                    project=project,
                    title=item.get('title', '')[:500],
                    url=item.get('url', '')[:2000],
                    source_type=ResearchSource.SourceType.WEB,
                    snippet=item.get('description', ''),
                    relevance_score=0.8,  # Default high for direct search
                    metadata={
                        'age': item.get('age'),
                        'extra_snippets': item.get('extra_snippets', []),
                        'search_query': search_query
                    }
                )
                sources_created.append({
                    'id': source.id,
                    'title': source.title,
                    'url': source.url
                })
            
            execution_time = int((time.time() - start_time) * 1000)
            
            # Store result
            ResearchResult.objects.create(
                project=project,
                handler_name=self.name,
                phase=self.phase,
                success=True,
                result_data={
                    'query': search_query,
                    'sources_found': len(sources_created),
                    'sources': sources_created
                },
                execution_time_ms=execution_time
            )
            
            return {
                'success': True,
                'handler': self.name,
                'query': search_query,
                'sources_found': len(sources_created),
                'sources': sources_created,
                'execution_time_ms': execution_time
            }
            
        except ResearchProject.DoesNotExist:
            return {
                'success': False,
                'error': f'Project {project_id} not found',
                'handler': self.name
            }
        except Exception as e:
            logger.error(f"WebSearchHandler error: {e}", exc_info=True)
            execution_time = int((time.time() - start_time) * 1000)
            
            # Store error result
            try:
                ResearchResult.objects.create(
                    project_id=project_id,
                    handler_name=self.name,
                    phase=self.phase,
                    success=False,
                    error_message=str(e),
                    execution_time_ms=execution_time
                )
            except Exception:
                pass
            
            return {
                'success': False,
                'error': str(e),
                'handler': self.name
            }
