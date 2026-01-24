"""
Citation Service
================

Comprehensive citation management for academic research.

Features:
- Multiple citation styles (APA 7, MLA 9, Chicago, Harvard, IEEE, Vancouver)
- BibTeX, RIS, EndNote export
- DOI resolution
- In-text citation generation
- Reference list formatting
"""

import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from enum import Enum

logger = logging.getLogger(__name__)


class CitationStyle(Enum):
    """Supported citation styles."""
    APA = "apa"           # APA 7th Edition
    MLA = "mla"           # MLA 9th Edition
    CHICAGO = "chicago"   # Chicago 17th Edition
    HARVARD = "harvard"   # Harvard
    IEEE = "ieee"         # IEEE
    VANCOUVER = "vancouver"  # Vancouver (medical)


class SourceType(Enum):
    """Types of sources for citation formatting."""
    JOURNAL = "journal"
    BOOK = "book"
    CHAPTER = "chapter"
    CONFERENCE = "conference"
    THESIS = "thesis"
    WEBSITE = "website"
    PREPRINT = "preprint"
    REPORT = "report"


@dataclass
class Author:
    """Represents an author."""
    family: str  # Last name
    given: str = ""  # First name(s)
    suffix: str = ""  # Jr., III, etc.
    orcid: str = ""
    
    def format_apa(self) -> str:
        """Format as 'Family, G.' for APA."""
        if self.given:
            initials = ". ".join(n[0].upper() for n in self.given.split() if n) + "."
            return f"{self.family}, {initials}"
        return self.family
    
    def format_mla(self) -> str:
        """Format as 'Family, Given' for MLA."""
        if self.given:
            return f"{self.family}, {self.given}"
        return self.family
    
    def format_ieee(self) -> str:
        """Format as 'G. Family' for IEEE."""
        if self.given:
            initials = ". ".join(n[0].upper() for n in self.given.split() if n) + "."
            return f"{initials} {self.family}"
        return self.family


@dataclass
class Citation:
    """
    Represents a complete citation with all metadata.
    
    Can be formatted in any citation style and exported to various formats.
    """
    # Required fields
    title: str
    source_type: SourceType = SourceType.JOURNAL
    
    # Authors
    authors: List[Author] = field(default_factory=list)
    
    # Publication info
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None
    
    # Journal/Book info
    journal: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    publisher: str = ""
    edition: str = ""
    
    # Identifiers
    doi: str = ""
    url: str = ""
    isbn: str = ""
    issn: str = ""
    pmid: str = ""
    arxiv_id: str = ""
    
    # Access info
    accessed_date: Optional[date] = None
    
    # Additional
    abstract: str = ""
    keywords: List[str] = field(default_factory=list)
    notes: str = ""
    
    # Internal
    id: str = ""
    source_database: str = ""  # e.g., 'pubmed', 'google_scholar'
    
    def format(self, style: CitationStyle = CitationStyle.APA) -> str:
        """Format citation in specified style."""
        if style == CitationStyle.APA:
            return self._format_apa()
        elif style == CitationStyle.MLA:
            return self._format_mla()
        elif style == CitationStyle.CHICAGO:
            return self._format_chicago()
        elif style == CitationStyle.HARVARD:
            return self._format_harvard()
        elif style == CitationStyle.IEEE:
            return self._format_ieee()
        elif style == CitationStyle.VANCOUVER:
            return self._format_vancouver()
        else:
            return self._format_apa()
    
    def format_in_text(self, style: CitationStyle = CitationStyle.APA) -> str:
        """Generate in-text citation."""
        if not self.authors:
            author_part = "Unknown"
        elif len(self.authors) == 1:
            author_part = self.authors[0].family
        elif len(self.authors) == 2:
            author_part = f"{self.authors[0].family} & {self.authors[1].family}"
        else:
            author_part = f"{self.authors[0].family} et al."
        
        year_part = str(self.year) if self.year else "n.d."
        
        if style in [CitationStyle.APA, CitationStyle.HARVARD]:
            return f"({author_part}, {year_part})"
        elif style == CitationStyle.MLA:
            return f"({author_part} {self.pages})" if self.pages else f"({author_part})"
        elif style == CitationStyle.IEEE:
            return f"[{self.id or '?'}]"
        elif style == CitationStyle.VANCOUVER:
            return f"({self.id or '?'})"
        else:
            return f"({author_part}, {year_part})"
    
    def to_bibtex(self) -> str:
        """Export as BibTeX entry."""
        # Generate key
        if self.authors:
            key = self.authors[0].family.lower().replace(" ", "")
        else:
            key = "unknown"
        key += str(self.year) if self.year else ""
        key = re.sub(r'[^a-z0-9]', '', key)
        
        # Determine entry type
        entry_types = {
            SourceType.JOURNAL: "article",
            SourceType.BOOK: "book",
            SourceType.CHAPTER: "incollection",
            SourceType.CONFERENCE: "inproceedings",
            SourceType.THESIS: "phdthesis",
            SourceType.PREPRINT: "misc",
            SourceType.WEBSITE: "misc",
            SourceType.REPORT: "techreport",
        }
        entry_type = entry_types.get(self.source_type, "misc")
        
        # Build entry
        lines = [f"@{entry_type}{{{key},"]
        
        if self.authors:
            author_str = " and ".join(
                f"{a.family}, {a.given}" for a in self.authors
            )
            lines.append(f'  author = {{{author_str}}},')
        
        lines.append(f'  title = {{{self.title}}},')
        
        if self.year:
            lines.append(f'  year = {{{self.year}}},')
        if self.journal:
            lines.append(f'  journal = {{{self.journal}}},')
        if self.volume:
            lines.append(f'  volume = {{{self.volume}}},')
        if self.issue:
            lines.append(f'  number = {{{self.issue}}},')
        if self.pages:
            lines.append(f'  pages = {{{self.pages}}},')
        if self.publisher:
            lines.append(f'  publisher = {{{self.publisher}}},')
        if self.doi:
            lines.append(f'  doi = {{{self.doi}}},')
        if self.url:
            lines.append(f'  url = {{{self.url}}},')
        if self.isbn:
            lines.append(f'  isbn = {{{self.isbn}}},')
        
        lines.append("}")
        return "\n".join(lines)
    
    def to_ris(self) -> str:
        """Export as RIS format (for EndNote, Zotero)."""
        type_map = {
            SourceType.JOURNAL: "JOUR",
            SourceType.BOOK: "BOOK",
            SourceType.CHAPTER: "CHAP",
            SourceType.CONFERENCE: "CONF",
            SourceType.THESIS: "THES",
            SourceType.WEBSITE: "ELEC",
            SourceType.PREPRINT: "UNPB",
            SourceType.REPORT: "RPRT",
        }
        
        lines = [f"TY  - {type_map.get(self.source_type, 'GEN')}"]
        
        for author in self.authors:
            lines.append(f"AU  - {author.family}, {author.given}")
        
        lines.append(f"TI  - {self.title}")
        
        if self.year:
            lines.append(f"PY  - {self.year}")
        if self.journal:
            lines.append(f"JO  - {self.journal}")
        if self.volume:
            lines.append(f"VL  - {self.volume}")
        if self.issue:
            lines.append(f"IS  - {self.issue}")
        if self.pages:
            if "-" in self.pages:
                sp, ep = self.pages.split("-", 1)
                lines.append(f"SP  - {sp.strip()}")
                lines.append(f"EP  - {ep.strip()}")
            else:
                lines.append(f"SP  - {self.pages}")
        if self.doi:
            lines.append(f"DO  - {self.doi}")
        if self.url:
            lines.append(f"UR  - {self.url}")
        if self.abstract:
            lines.append(f"AB  - {self.abstract}")
        
        lines.append("ER  - ")
        return "\n".join(lines)
    
    def _format_apa(self) -> str:
        """APA 7th Edition format."""
        parts = []
        
        # Authors
        if self.authors:
            if len(self.authors) == 1:
                parts.append(self.authors[0].format_apa())
            elif len(self.authors) == 2:
                parts.append(f"{self.authors[0].format_apa()}, & {self.authors[1].format_apa()}")
            elif len(self.authors) <= 20:
                author_parts = [a.format_apa() for a in self.authors[:-1]]
                parts.append(", ".join(author_parts) + f", & {self.authors[-1].format_apa()}")
            else:
                author_parts = [a.format_apa() for a in self.authors[:19]]
                parts.append(", ".join(author_parts) + f", ... {self.authors[-1].format_apa()}")
        
        # Year
        year_str = f"({self.year})" if self.year else "(n.d.)"
        parts.append(year_str + ".")
        
        # Title
        if self.source_type == SourceType.JOURNAL:
            parts.append(f"{self.title}.")
        else:
            parts.append(f"*{self.title}*.")
        
        # Journal info
        if self.journal:
            journal_part = f"*{self.journal}*"
            if self.volume:
                journal_part += f", *{self.volume}*"
                if self.issue:
                    journal_part += f"({self.issue})"
            if self.pages:
                journal_part += f", {self.pages}"
            parts.append(journal_part + ".")
        
        # DOI/URL
        if self.doi:
            parts.append(f"https://doi.org/{self.doi}")
        elif self.url:
            parts.append(self.url)
        
        return " ".join(parts)
    
    def _format_mla(self) -> str:
        """MLA 9th Edition format."""
        parts = []
        
        # Authors
        if self.authors:
            if len(self.authors) == 1:
                parts.append(self.authors[0].format_mla() + ".")
            elif len(self.authors) == 2:
                parts.append(f"{self.authors[0].format_mla()}, and {self.authors[1].given} {self.authors[1].family}.")
            else:
                parts.append(f"{self.authors[0].format_mla()}, et al.")
        
        # Title
        parts.append(f'"{self.title}."')
        
        # Container (journal)
        if self.journal:
            container = f"*{self.journal}*"
            if self.volume:
                container += f", vol. {self.volume}"
                if self.issue:
                    container += f", no. {self.issue}"
            if self.year:
                container += f", {self.year}"
            if self.pages:
                container += f", pp. {self.pages}"
            parts.append(container + ".")
        
        # DOI
        if self.doi:
            parts.append(f"https://doi.org/{self.doi}.")
        
        return " ".join(parts)
    
    def _format_chicago(self) -> str:
        """Chicago 17th Edition (Author-Date) format."""
        parts = []
        
        # Authors
        if self.authors:
            if len(self.authors) == 1:
                parts.append(f"{self.authors[0].family}, {self.authors[0].given}.")
            else:
                first = f"{self.authors[0].family}, {self.authors[0].given}"
                others = ", ".join(f"{a.given} {a.family}" for a in self.authors[1:])
                parts.append(f"{first}, and {others}.")
        
        # Year
        if self.year:
            parts.append(f"{self.year}.")
        
        # Title
        parts.append(f'"{self.title}."')
        
        # Journal
        if self.journal:
            journal_part = f"*{self.journal}*"
            if self.volume:
                journal_part += f" {self.volume}"
                if self.issue:
                    journal_part += f", no. {self.issue}"
            if self.pages:
                journal_part += f": {self.pages}"
            parts.append(journal_part + ".")
        
        # DOI
        if self.doi:
            parts.append(f"https://doi.org/{self.doi}.")
        
        return " ".join(parts)
    
    def _format_harvard(self) -> str:
        """Harvard format."""
        parts = []
        
        # Authors
        if self.authors:
            author_list = [f"{a.family}, {a.given[0]}." if a.given else a.family for a in self.authors]
            if len(author_list) <= 3:
                parts.append(" and ".join(author_list))
            else:
                parts.append(f"{author_list[0]} et al.")
        
        # Year
        year_str = f"({self.year})" if self.year else "(n.d.)"
        parts.append(year_str)
        
        # Title
        parts.append(f"'{self.title}',")
        
        # Journal
        if self.journal:
            journal_part = f"*{self.journal}*"
            if self.volume:
                journal_part += f", {self.volume}"
                if self.issue:
                    journal_part += f"({self.issue})"
            if self.pages:
                journal_part += f", pp. {self.pages}"
            parts.append(journal_part + ".")
        
        return " ".join(parts)
    
    def _format_ieee(self) -> str:
        """IEEE format."""
        parts = []
        
        # Authors
        if self.authors:
            author_list = [a.format_ieee() for a in self.authors]
            if len(author_list) <= 3:
                parts.append(", ".join(author_list[:-1]) + " and " + author_list[-1] if len(author_list) > 1 else author_list[0])
            else:
                parts.append(f"{author_list[0]} *et al.*")
        
        # Title
        parts.append(f'"{self.title},"')
        
        # Journal
        if self.journal:
            journal_part = f"*{self.journal}*"
            if self.volume:
                journal_part += f", vol. {self.volume}"
                if self.issue:
                    journal_part += f", no. {self.issue}"
            if self.pages:
                journal_part += f", pp. {self.pages}"
            if self.year:
                month_names = ["", "Jan.", "Feb.", "Mar.", "Apr.", "May", "Jun.", 
                              "Jul.", "Aug.", "Sep.", "Oct.", "Nov.", "Dec."]
                if self.month:
                    journal_part += f", {month_names[self.month]} {self.year}"
                else:
                    journal_part += f", {self.year}"
            parts.append(journal_part + ".")
        
        # DOI
        if self.doi:
            parts.append(f"doi: {self.doi}.")
        
        return " ".join(parts)
    
    def _format_vancouver(self) -> str:
        """Vancouver format (medical/biomedical)."""
        parts = []
        
        # Authors
        if self.authors:
            author_list = []
            for a in self.authors[:6]:
                initials = "".join(n[0].upper() for n in a.given.split() if n) if a.given else ""
                author_list.append(f"{a.family} {initials}")
            
            if len(self.authors) > 6:
                parts.append(", ".join(author_list) + ", et al.")
            else:
                parts.append(", ".join(author_list) + ".")
        
        # Title
        parts.append(f"{self.title}.")
        
        # Journal
        if self.journal:
            # Abbreviate journal name (simplified)
            journal_part = self.journal
            if self.year:
                journal_part += f" {self.year}"
            if self.month:
                month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                journal_part += f" {month_names[self.month]}"
            if self.volume:
                journal_part += f";{self.volume}"
                if self.issue:
                    journal_part += f"({self.issue})"
            if self.pages:
                journal_part += f":{self.pages}"
            parts.append(journal_part + ".")
        
        # PMID
        if self.pmid:
            parts.append(f"PMID: {self.pmid}.")
        
        # DOI
        if self.doi:
            parts.append(f"doi: {self.doi}.")
        
        return " ".join(parts)


class CitationService:
    """
    Service for managing citations and references.
    
    Usage:
        service = CitationService()
        
        # Create citation from DOI
        citation = service.from_doi("10.1038/nature12373")
        
        # Format in different styles
        apa = citation.format(CitationStyle.APA)
        bibtex = citation.to_bibtex()
        
        # Generate bibliography
        bibliography = service.format_bibliography(citations, CitationStyle.APA)
    """
    
    def __init__(self):
        self._session = None
    
    @property
    def session(self):
        """Lazy-load requests session."""
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._session.headers.update({
                'User-Agent': 'BFAgent-Citation/1.0 (mailto:research@example.com)'
            })
        return self._session
    
    def from_doi(self, doi: str) -> Optional[Citation]:
        """
        Create citation from DOI using CrossRef.
        
        Args:
            doi: Digital Object Identifier
            
        Returns:
            Citation object or None if not found
        """
        try:
            # Clean DOI
            doi = doi.strip()
            if doi.startswith("https://doi.org/"):
                doi = doi[16:]
            elif doi.startswith("http://doi.org/"):
                doi = doi[15:]
            elif doi.startswith("doi:"):
                doi = doi[4:]
            
            url = f"https://api.crossref.org/works/{doi}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"DOI not found: {doi}")
                return None
            
            data = response.json().get("message", {})
            
            # Parse authors
            authors = []
            for author in data.get("author", []):
                authors.append(Author(
                    family=author.get("family", ""),
                    given=author.get("given", "")
                ))
            
            # Parse date
            date_parts = data.get("published-print", data.get("published-online", {})).get("date-parts", [[]])
            year = date_parts[0][0] if date_parts and date_parts[0] else None
            month = date_parts[0][1] if date_parts and len(date_parts[0]) > 1 else None
            
            # Determine source type
            type_map = {
                "journal-article": SourceType.JOURNAL,
                "book": SourceType.BOOK,
                "book-chapter": SourceType.CHAPTER,
                "proceedings-article": SourceType.CONFERENCE,
                "dissertation": SourceType.THESIS,
                "posted-content": SourceType.PREPRINT,
            }
            source_type = type_map.get(data.get("type", ""), SourceType.JOURNAL)
            
            # Parse pages
            pages = data.get("page", "")
            
            return Citation(
                title=data.get("title", [""])[0],
                authors=authors,
                year=year,
                month=month,
                journal=data.get("container-title", [""])[0] if data.get("container-title") else "",
                volume=data.get("volume", ""),
                issue=data.get("issue", ""),
                pages=pages,
                publisher=data.get("publisher", ""),
                doi=doi,
                url=data.get("URL", f"https://doi.org/{doi}"),
                issn=data.get("ISSN", [""])[0] if data.get("ISSN") else "",
                source_type=source_type,
                source_database="crossref"
            )
            
        except Exception as e:
            logger.error(f"Error resolving DOI {doi}: {e}")
            return None
    
    def from_url(self, url: str, accessed_date: date = None) -> Citation:
        """
        Create citation for a website/URL.
        
        Args:
            url: Website URL
            accessed_date: Date accessed (defaults to today)
            
        Returns:
            Citation object
        """
        import urllib.parse
        
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        
        return Citation(
            title=f"Content from {domain}",
            url=url,
            source_type=SourceType.WEBSITE,
            accessed_date=accessed_date or date.today(),
            source_database="web"
        )
    
    def format_bibliography(
        self,
        citations: List[Citation],
        style: CitationStyle = CitationStyle.APA,
        sort_by: str = "author"  # "author", "year", "title"
    ) -> str:
        """
        Format a list of citations as a bibliography.
        
        Args:
            citations: List of Citation objects
            style: Citation style to use
            sort_by: How to sort entries
            
        Returns:
            Formatted bibliography string
        """
        if not citations:
            return ""
        
        # Sort citations
        if sort_by == "author":
            sorted_citations = sorted(
                citations,
                key=lambda c: c.authors[0].family.lower() if c.authors else "zzz"
            )
        elif sort_by == "year":
            sorted_citations = sorted(
                citations,
                key=lambda c: c.year or 9999,
                reverse=True
            )
        elif sort_by == "title":
            sorted_citations = sorted(
                citations,
                key=lambda c: c.title.lower()
            )
        else:
            sorted_citations = citations
        
        # Format each citation
        formatted = []
        for i, citation in enumerate(sorted_citations, 1):
            if style == CitationStyle.IEEE:
                # IEEE uses numbered references
                citation.id = str(i)
                formatted.append(f"[{i}] {citation.format(style)}")
            elif style == CitationStyle.VANCOUVER:
                citation.id = str(i)
                formatted.append(f"{i}. {citation.format(style)}")
            else:
                formatted.append(citation.format(style))
        
        return "\n\n".join(formatted)
    
    def export_bibtex(self, citations: List[Citation]) -> str:
        """Export all citations as BibTeX."""
        return "\n\n".join(c.to_bibtex() for c in citations)
    
    def export_ris(self, citations: List[Citation]) -> str:
        """Export all citations as RIS (EndNote/Zotero)."""
        return "\n\n".join(c.to_ris() for c in citations)


# Singleton instance
_citation_service = None

def get_citation_service() -> CitationService:
    """Get singleton instance of CitationService."""
    global _citation_service
    if _citation_service is None:
        _citation_service = CitationService()
    return _citation_service
