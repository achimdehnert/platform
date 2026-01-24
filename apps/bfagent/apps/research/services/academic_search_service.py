"""
Academic Search Service
=======================

Integration with academic search APIs:
- arXiv (free, no API key needed)
- Semantic Scholar (free tier available)
- CrossRef (for DOI resolution)
"""

import logging
import re
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class AcademicPaper:
    """Represents an academic paper from any source."""
    title: str
    authors: List[str]
    abstract: str
    url: str
    source: str  # 'arxiv', 'semantic_scholar', 'crossref'
    
    # Optional fields
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    publication_date: Optional[str] = None
    journal: Optional[str] = None
    citation_count: Optional[int] = None
    pdf_url: Optional[str] = None
    categories: Optional[List[str]] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


class AcademicSearchService:
    """
    Unified academic search across multiple sources.
    
    Usage:
        service = AcademicSearchService()
        papers = service.search("machine learning healthcare", count=10)
    """
    
    ARXIV_API = "http://export.arxiv.org/api/query"
    SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"
    CROSSREF_API = "https://api.crossref.org/works"
    
    def __init__(self):
        self._session = None
    
    @property
    def session(self):
        """Lazy-load requests session."""
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._session.headers.update({
                'User-Agent': 'BFAgent-Research/1.0 (mailto:research@example.com)'
            })
        return self._session
    
    def search(
        self,
        query: str,
        count: int = 10,
        sources: Optional[List[str]] = None
    ) -> Dict:
        """
        Search academic sources for papers.
        
        Args:
            query: Search query
            count: Max results per source
            sources: List of sources to search ['arxiv', 'semantic_scholar']
                    Default: all sources
        
        Returns:
            Dict with results from each source
        """
        sources = sources or ['arxiv', 'semantic_scholar', 'pubmed', 'openalex']
        results = {
            'success': True,
            'query': query,
            'papers': [],
            'sources_searched': sources,
            'errors': []
        }
        
        for source in sources:
            try:
                if source == 'arxiv':
                    papers = self._search_arxiv(query, count)
                elif source == 'semantic_scholar':
                    papers = self._search_semantic_scholar(query, count)
                elif source == 'pubmed':
                    papers = self._search_pubmed(query, count)
                elif source == 'openalex':
                    papers = self._search_openalex(query, count)
                elif source == 'google_scholar':
                    papers = self._search_google_scholar(query, count)
                elif source == 'biorxiv':
                    papers = self._search_biorxiv(query, count)
                else:
                    continue
                
                results['papers'].extend(papers)
                logger.info(f"Found {len(papers)} papers from {source}")
                
            except Exception as e:
                logger.warning(f"Error searching {source}: {e}")
                results['errors'].append(f"{source}: {str(e)}")
        
        results['total'] = len(results['papers'])
        return results
    
    def _search_arxiv(self, query: str, count: int) -> List[AcademicPaper]:
        """Search arXiv API."""
        import xml.etree.ElementTree as ET
        
        params = {
            'search_query': f'all:{query}',
            'start': 0,
            'max_results': min(count, 50),
            'sortBy': 'relevance',
            'sortOrder': 'descending'
        }
        
        response = self.session.get(self.ARXIV_API, params=params, timeout=15)
        response.raise_for_status()
        
        # Parse XML response
        root = ET.fromstring(response.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
        
        papers = []
        for entry in root.findall('atom:entry', ns):
            try:
                # Extract arxiv ID from URL
                arxiv_url = entry.find('atom:id', ns).text
                arxiv_id = arxiv_url.split('/abs/')[-1] if '/abs/' in arxiv_url else None
                
                # Get authors
                authors = [
                    author.find('atom:name', ns).text
                    for author in entry.findall('atom:author', ns)
                ]
                
                # Get categories
                categories = [
                    cat.get('term')
                    for cat in entry.findall('atom:category', ns)
                ]
                
                # Get PDF link
                pdf_url = None
                for link in entry.findall('atom:link', ns):
                    if link.get('title') == 'pdf':
                        pdf_url = link.get('href')
                        break
                
                paper = AcademicPaper(
                    title=entry.find('atom:title', ns).text.strip().replace('\n', ' '),
                    authors=authors,
                    abstract=entry.find('atom:summary', ns).text.strip().replace('\n', ' ')[:500],
                    url=arxiv_url,
                    source='arxiv',
                    arxiv_id=arxiv_id,
                    publication_date=entry.find('atom:published', ns).text[:10],
                    pdf_url=pdf_url,
                    categories=categories
                )
                papers.append(paper)
                
            except Exception as e:
                logger.warning(f"Error parsing arXiv entry: {e}")
                continue
        
        return papers
    
    def _search_semantic_scholar(self, query: str, count: int) -> List[AcademicPaper]:
        """Search Semantic Scholar API."""
        params = {
            'query': query,
            'limit': min(count, 100),
            'fields': 'title,authors,abstract,url,externalIds,year,venue,citationCount,openAccessPdf'
        }
        
        response = self.session.get(self.SEMANTIC_SCHOLAR_API, params=params, timeout=15)
        
        # Handle rate limiting
        if response.status_code == 429:
            logger.warning("Semantic Scholar rate limit reached")
            return []
        
        response.raise_for_status()
        data = response.json()
        
        papers = []
        for item in data.get('data', []):
            try:
                # Get authors
                authors = [
                    a.get('name', '')
                    for a in item.get('authors', [])
                ]
                
                # Get DOI and arXiv ID
                external_ids = item.get('externalIds', {}) or {}
                doi = external_ids.get('DOI')
                arxiv_id = external_ids.get('ArXiv')
                
                # Get PDF URL
                pdf_info = item.get('openAccessPdf', {}) or {}
                pdf_url = pdf_info.get('url')
                
                paper = AcademicPaper(
                    title=item.get('title', 'Unknown'),
                    authors=authors,
                    abstract=(item.get('abstract') or '')[:500],
                    url=item.get('url', ''),
                    source='semantic_scholar',
                    doi=doi,
                    arxiv_id=arxiv_id,
                    publication_date=str(item.get('year', '')),
                    journal=item.get('venue', ''),
                    citation_count=item.get('citationCount'),
                    pdf_url=pdf_url
                )
                papers.append(paper)
                
            except Exception as e:
                logger.warning(f"Error parsing Semantic Scholar entry: {e}")
                continue
        
        return papers
    
    def get_paper_by_doi(self, doi: str) -> Optional[AcademicPaper]:
        """Fetch paper details by DOI using CrossRef."""
        try:
            url = f"{self.CROSSREF_API}/{doi}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json().get('message', {})
            
            # Get authors
            authors = []
            for author in data.get('author', []):
                name = f"{author.get('given', '')} {author.get('family', '')}".strip()
                if name:
                    authors.append(name)
            
            # Get publication date
            date_parts = data.get('published-print', data.get('published-online', {})).get('date-parts', [[]])
            pub_date = '-'.join(str(p) for p in date_parts[0]) if date_parts[0] else None
            
            return AcademicPaper(
                title=data.get('title', ['Unknown'])[0],
                authors=authors,
                abstract=data.get('abstract', '')[:500] if data.get('abstract') else '',
                url=data.get('URL', f'https://doi.org/{doi}'),
                source='crossref',
                doi=doi,
                publication_date=pub_date,
                journal=data.get('container-title', [''])[0]
            )
            
        except Exception as e:
            logger.warning(f"Error fetching DOI {doi}: {e}")
            return None
    
    def get_paper_by_arxiv_id(self, arxiv_id: str) -> Optional[AcademicPaper]:
        """Fetch paper details by arXiv ID."""
        papers = self._search_arxiv(f'id:{arxiv_id}', count=1)
        return papers[0] if papers else None
    
    def _search_pubmed(self, query: str, count: int) -> List[AcademicPaper]:
        """
        Search PubMed/NCBI E-utilities API.
        
        Free API, optional API key for higher rate limits.
        """
        import xml.etree.ElementTree as ET
        
        # Step 1: Search for PMIDs
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": min(count, 100),
            "retmode": "json",
            "sort": "relevance"
        }
        
        response = self.session.get(search_url, params=params, timeout=15)
        response.raise_for_status()
        
        search_result = response.json()
        pmids = search_result.get("esearchresult", {}).get("idlist", [])
        
        if not pmids:
            return []
        
        # Step 2: Fetch details for PMIDs
        fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml"
        }
        
        response = self.session.get(fetch_url, params=params, timeout=15)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.content)
        papers = []
        
        for article in root.findall(".//PubmedArticle"):
            try:
                # Get article info
                medline = article.find(".//MedlineCitation")
                article_elem = medline.find(".//Article")
                
                # Title
                title_elem = article_elem.find(".//ArticleTitle")
                title = title_elem.text if title_elem is not None else "Unknown"
                
                # Authors
                authors = []
                for author in article_elem.findall(".//Author"):
                    last = author.find("LastName")
                    first = author.find("ForeName")
                    if last is not None:
                        name = last.text
                        if first is not None:
                            name = f"{first.text} {last.text}"
                        authors.append(name)
                
                # Abstract
                abstract_elem = article_elem.find(".//Abstract/AbstractText")
                abstract = abstract_elem.text[:500] if abstract_elem is not None and abstract_elem.text else ""
                
                # Journal
                journal_elem = article_elem.find(".//Journal/Title")
                journal = journal_elem.text if journal_elem is not None else ""
                
                # Date
                pub_date = medline.find(".//DateCompleted")
                if pub_date is None:
                    pub_date = medline.find(".//DateRevised")
                year = pub_date.find("Year").text if pub_date is not None and pub_date.find("Year") is not None else ""
                
                # PMID
                pmid_elem = medline.find(".//PMID")
                pmid = pmid_elem.text if pmid_elem is not None else ""
                
                # DOI
                doi = ""
                for article_id in article.findall(".//ArticleId"):
                    if article_id.get("IdType") == "doi":
                        doi = article_id.text
                        break
                
                paper = AcademicPaper(
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    source='pubmed',
                    doi=doi,
                    publication_date=year,
                    journal=journal,
                    categories=["biomedical"]
                )
                papers.append(paper)
                
            except Exception as e:
                logger.warning(f"Error parsing PubMed entry: {e}")
                continue
        
        return papers
    
    def _search_openalex(self, query: str, count: int) -> List[AcademicPaper]:
        """
        Search OpenAlex API.
        
        Free, no auth required. 100k requests/day.
        Replaces Microsoft Academic.
        """
        url = "https://api.openalex.org/works"
        params = {
            "search": query,
            "per_page": min(count, 50),
            "mailto": "research@bfagent.io"  # Polite pool
        }
        
        response = self.session.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        papers = []
        
        for item in data.get("results", []):
            try:
                # Authors
                authors = []
                for authorship in item.get("authorships", []):
                    author_info = authorship.get("author", {})
                    name = author_info.get("display_name", "")
                    if name:
                        authors.append(name)
                
                # DOI
                doi = item.get("doi", "")
                if doi and doi.startswith("https://doi.org/"):
                    doi = doi[16:]
                
                # PDF URL (open access)
                pdf_url = None
                oa = item.get("open_access", {})
                if oa.get("is_oa"):
                    pdf_url = oa.get("oa_url")
                
                paper = AcademicPaper(
                    title=item.get("title", "Unknown") or "Unknown",
                    authors=authors[:10],  # Limit authors
                    abstract="",  # OpenAlex doesn't return abstracts in search
                    url=item.get("id", ""),
                    source='openalex',
                    doi=doi,
                    publication_date=str(item.get("publication_year", "")),
                    journal=item.get("primary_location", {}).get("source", {}).get("display_name", "") if item.get("primary_location") else "",
                    citation_count=item.get("cited_by_count"),
                    pdf_url=pdf_url
                )
                papers.append(paper)
                
            except Exception as e:
                logger.warning(f"Error parsing OpenAlex entry: {e}")
                continue
        
        return papers
    
    def _search_google_scholar(self, query: str, count: int) -> List[AcademicPaper]:
        """
        Search Google Scholar via scraping.
        
        Ethical guidelines:
        - Rate limited (2-4 sec delay)
        - Clear identification
        - Only metadata, proper citation
        """
        import time
        import random
        from bs4 import BeautifulSoup
        
        # Rate limiting
        time.sleep(random.uniform(2, 4))
        
        url = "https://scholar.google.com/scholar"
        params = {
            "q": query,
            "hl": "en",
            "num": min(count, 10)  # GS limits to 10 per page
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        try:
            response = self.session.get(url, params=params, headers=headers, timeout=15)
            
            # Check for CAPTCHA/block
            if response.status_code == 429 or "captcha" in response.text.lower():
                logger.warning("Google Scholar rate limited or CAPTCHA")
                return []
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            papers = []
            
            for result in soup.select('.gs_ri'):
                try:
                    # Title and URL
                    title_elem = result.select_one('.gs_rt a')
                    if title_elem:
                        title = title_elem.get_text()
                        url = title_elem.get('href', '')
                    else:
                        title_elem = result.select_one('.gs_rt')
                        title = title_elem.get_text() if title_elem else "Unknown"
                        url = ""
                    
                    # Authors and publication info
                    info_elem = result.select_one('.gs_a')
                    authors = []
                    journal = ""
                    year = ""
                    
                    if info_elem:
                        info_text = info_elem.get_text()
                        # Format: "Authors - Journal, Year - Publisher"
                        parts = info_text.split(' - ')
                        if parts:
                            author_part = parts[0]
                            authors = [a.strip() for a in author_part.split(',')[:5]]
                        if len(parts) > 1:
                            journal_part = parts[1]
                            # Extract year
                            year_match = re.search(r'\b(19|20)\d{2}\b', journal_part)
                            if year_match:
                                year = year_match.group()
                            journal = journal_part.split(',')[0].strip()
                    
                    # Snippet
                    snippet_elem = result.select_one('.gs_rs')
                    snippet = snippet_elem.get_text()[:300] if snippet_elem else ""
                    
                    # Citation count
                    citation_count = None
                    cite_elem = result.select_one('a[href*="cites="]')
                    if cite_elem:
                        cite_text = cite_elem.get_text()
                        cite_match = re.search(r'\d+', cite_text)
                        if cite_match:
                            citation_count = int(cite_match.group())
                    
                    paper = AcademicPaper(
                        title=title.strip(),
                        authors=authors,
                        abstract=snippet,
                        url=url,
                        source='google_scholar',
                        publication_date=year,
                        journal=journal,
                        citation_count=citation_count
                    )
                    papers.append(paper)
                    
                except Exception as e:
                    logger.warning(f"Error parsing Google Scholar result: {e}")
                    continue
            
            return papers
            
        except Exception as e:
            logger.warning(f"Google Scholar search failed: {e}")
            return []
    
    def _search_biorxiv(self, query: str, count: int) -> List[AcademicPaper]:
        """
        Search bioRxiv/medRxiv preprints via CrossRef.
        """
        url = "https://api.crossref.org/works"
        params = {
            "query": query,
            "filter": "publisher-name:Cold Spring Harbor Laboratory",
            "rows": min(count, 50),
            "sort": "relevance"
        }
        
        response = self.session.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        papers = []
        
        for item in data.get("message", {}).get("items", []):
            try:
                # Authors
                authors = []
                for author in item.get("author", []):
                    name = f"{author.get('given', '')} {author.get('family', '')}".strip()
                    if name:
                        authors.append(name)
                
                # Date
                date_parts = item.get("posted", {}).get("date-parts", [[]])
                year = str(date_parts[0][0]) if date_parts and date_parts[0] else ""
                
                # DOI
                doi = item.get("DOI", "")
                
                # Determine if bioRxiv or medRxiv
                source = "biorxiv"
                if "medrxiv" in item.get("URL", "").lower():
                    source = "medrxiv"
                
                paper = AcademicPaper(
                    title=item.get("title", ["Unknown"])[0] if item.get("title") else "Unknown",
                    authors=authors,
                    abstract=item.get("abstract", "")[:500] if item.get("abstract") else "",
                    url=item.get("URL", f"https://doi.org/{doi}"),
                    source=source,
                    doi=doi,
                    publication_date=year,
                    categories=["preprint"]
                )
                papers.append(paper)
                
            except Exception as e:
                logger.warning(f"Error parsing bioRxiv entry: {e}")
                continue
        
        return papers
    
    def find_open_access(self, doi: str) -> Optional[str]:
        """
        Find open access PDF URL via Unpaywall.
        
        Args:
            doi: Digital Object Identifier
            
        Returns:
            PDF URL if available, None otherwise
        """
        try:
            url = f"https://api.unpaywall.org/v2/{doi}"
            params = {"email": "research@bfagent.io"}
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            if data.get("is_oa"):
                best_oa = data.get("best_oa_location", {})
                return best_oa.get("url_for_pdf") or best_oa.get("url")
            
            return None
            
        except Exception as e:
            logger.warning(f"Unpaywall lookup failed for {doi}: {e}")
            return None


# Singleton instance
_academic_service = None

def get_academic_search() -> AcademicSearchService:
    """Get singleton instance of AcademicSearchService."""
    global _academic_service
    if _academic_service is None:
        _academic_service = AcademicSearchService()
    return _academic_service
