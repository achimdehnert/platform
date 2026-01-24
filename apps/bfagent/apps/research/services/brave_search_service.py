"""
Brave Search Service
====================

Integration with Brave Search API via MCP server.
Provides web search functionality for Research Hub.
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Single search result from Brave Search."""
    title: str
    url: str
    description: str
    age: Optional[str] = None
    extra_snippets: Optional[List[str]] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


class BraveSearchService:
    """
    Brave Search API integration.
    
    Uses the brave-search MCP server for web search queries.
    Falls back to mock data if MCP is unavailable.
    
    Usage:
        service = BraveSearchService()
        results = service.search("AI developments 2024", count=10)
    """
    
    def __init__(self, use_mcp: bool = True):
        """
        Initialize Brave Search service.
        
        Args:
            use_mcp: Whether to use MCP server (True) or mock data (False)
        """
        self.use_mcp = use_mcp
        self._mcp_available = None
    
    def search(
        self,
        query: str,
        count: int = 10,
        offset: int = 0
    ) -> Dict:
        """
        Perform web search using Brave Search.
        
        Args:
            query: Search query (max 400 chars, 50 words)
            count: Number of results (1-20)
            offset: Pagination offset (max 9)
            
        Returns:
            Dict with results, success status, and metadata
        """
        try:
            if self.use_mcp:
                return self._search_via_mcp(query, count, offset)
            else:
                return self._mock_search(query, count)
        except Exception as e:
            logger.error(f"Brave Search error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'results': [],
                'query': query
            }
    
    def local_search(
        self,
        query: str,
        count: int = 5
    ) -> Dict:
        """
        Perform local business search.
        
        Args:
            query: Local search query (e.g. "pizza near Berlin")
            count: Number of results (1-20)
            
        Returns:
            Dict with local business results
        """
        try:
            if self.use_mcp:
                return self._local_search_via_mcp(query, count)
            else:
                return self._mock_local_search(query, count)
        except Exception as e:
            logger.error(f"Brave Local Search error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'results': [],
                'query': query
            }
    
    def _search_via_mcp(self, query: str, count: int, offset: int) -> Dict:
        """
        Execute search via Brave MCP server or API.
        
        Tries to use the Brave Search API directly if available,
        otherwise falls back to mock data.
        """
        import os
        
        # Try to get API key from Django settings or environment
        api_key = None
        try:
            from django.conf import settings
            api_key = getattr(settings, 'BRAVE_API_KEY', None)
        except Exception:
            pass
        
        if not api_key:
            try:
                from decouple import config
                api_key = config('BRAVE_API_KEY', default='')
            except Exception:
                pass
        
        if not api_key:
            api_key = os.environ.get('BRAVE_API_KEY')
        if api_key:
            try:
                import requests
                headers = {
                    'Accept': 'application/json',
                    'X-Subscription-Token': api_key
                }
                params = {
                    'q': query[:400],
                    'count': min(20, max(1, count)),
                    'offset': min(9, max(0, offset))
                }
                response = requests.get(
                    'https://api.search.brave.com/res/v1/web/search',
                    headers=headers,
                    params=params,
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    return self._process_mcp_results(data)
                else:
                    logger.warning(f"Brave API returned {response.status_code}")
            except Exception as e:
                logger.warning(f"Brave API error: {e}, falling back to mock")
        
        # Fallback to mock data with informative message
        logger.info(f"Using mock search for: {query}")
        return self._mock_search(query, count)
    
    def _local_search_via_mcp(self, query: str, count: int) -> Dict:
        """Execute local search via Brave MCP server."""
        return {
            'mcp_tool': 'mcp3_brave_local_search',
            'params': {
                'query': query,
                'count': min(20, max(1, count))
            },
            'callback': self._process_mcp_local_results
        }
    
    def _process_mcp_results(self, mcp_response: Dict) -> Dict:
        """Process MCP response into standardized format."""
        results = []
        
        if 'web' in mcp_response and 'results' in mcp_response['web']:
            for item in mcp_response['web']['results']:
                results.append(SearchResult(
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    description=item.get('description', ''),
                    age=item.get('age'),
                    extra_snippets=item.get('extra_snippets', [])
                ))
        
        return {
            'success': True,
            'results': [r.to_dict() for r in results],
            'total': len(results)
        }
    
    def _process_mcp_local_results(self, mcp_response: Dict) -> Dict:
        """Process MCP local search response."""
        results = []
        
        if 'locations' in mcp_response:
            for item in mcp_response['locations']:
                results.append({
                    'name': item.get('name', ''),
                    'address': item.get('address', ''),
                    'phone': item.get('phone', ''),
                    'rating': item.get('rating'),
                    'reviews': item.get('review_count'),
                    'hours': item.get('opening_hours', [])
                })
        
        return {
            'success': True,
            'results': results,
            'total': len(results)
        }
    
    def _mock_search(self, query: str, count: int) -> Dict:
        """Fallback search using LLM when Brave API unavailable."""
        # Try LLM fallback
        llm_result = self._llm_fallback_search(query, count)
        if llm_result:
            return llm_result
        
        # No static fallback - return error message
        logger.warning(f"Research unavailable for: {query} (Brave API + LLM both failed)")
        return {
            'success': False,
            'results': [],
            'total': 0,
            'query': query,
            'error': 'research_unavailable',
            'message': 'Recherche ist zum jetzigen Zeitpunkt nicht möglich. '
                      'Bitte versuchen Sie es später erneut oder prüfen Sie die API-Konfiguration.',
        }
    
    def _llm_fallback_search(self, query: str, count: int) -> Optional[Dict]:
        """Use LLM to generate search-like results."""
        try:
            from apps.bfagent.services.llm_agent import LLMAgent, ModelPreference
            llm = LLMAgent()
            
            prompt = f"""Generiere {count} informative Suchergebnisse zum Thema: "{query}"

Für jedes Ergebnis:
- title: Informativer Titel
- url: Plausible URL (wikipedia.org, fachseiten, etc.)
- description: 2-3 Sätze mit konkreten Fakten

Antwort als JSON-Array. Nur faktisch korrekte Informationen."""

            response = llm.generate(prompt, preferences=ModelPreference(quality="fast"))
            
            if response.success and response.content:
                import json
                import re
                json_match = re.search(r'\[[\s\S]*\]', response.content)
                if json_match:
                    results = json.loads(json_match.group())
                    return {
                        'success': True,
                        'results': results[:count],
                        'total': len(results),
                        'query': query,
                        'fallback': 'llm',
                        'model_used': response.model_used,
                    }
        except Exception as e:
            logger.warning(f"LLM fallback failed: {e}")
        
        return None
    
    def _mock_local_search(self, query: str, count: int) -> Dict:
        """Return mock local search results."""
        return {
            'success': True,
            'results': [
                {
                    'name': f"Local Business {i+1}",
                    'address': f"123 Main St #{i+1}",
                    'phone': f"+49 30 1234567{i}",
                    'rating': 4.5 - (i * 0.2),
                    'reviews': 100 - (i * 10)
                }
                for i in range(min(count, 3))
            ],
            'total': min(count, 3),
            'query': query,
            'mock': True
        }


# Singleton instance for easy access
_brave_service = None

def get_brave_search() -> BraveSearchService:
    """Get singleton instance of BraveSearchService."""
    global _brave_service
    if _brave_service is None:
        _brave_service = BraveSearchService()
    return _brave_service
