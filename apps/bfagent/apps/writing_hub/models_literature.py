"""
Literature Management Models for Scientific Writing
====================================================
Models for managing citations, references, and bibliography.
"""

from django.db import models
from django.utils import timezone


class LiteratureSource(models.Model):
    """
    A literature source (book, article, website, etc.) for citation.
    Supports common citation styles: APA, MLA, Chicago, IEEE, Harvard.
    """
    
    SOURCE_TYPE_CHOICES = [
        ('article', 'Journal Article'),
        ('book', 'Book'),
        ('chapter', 'Book Chapter'),
        ('conference', 'Conference Paper'),
        ('thesis', 'Thesis/Dissertation'),
        ('website', 'Website'),
        ('report', 'Report'),
        ('other', 'Other'),
    ]
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='literature_sources'
    )
    
    # Basic Information
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES, default='article')
    title = models.TextField()
    authors = models.TextField(help_text="Comma-separated: Last, First; Last, First")
    year = models.IntegerField(null=True, blank=True)
    
    # Publication Details (varies by type)
    journal = models.CharField(max_length=255, blank=True)  # For articles
    volume = models.CharField(max_length=50, blank=True)
    issue = models.CharField(max_length=50, blank=True)
    pages = models.CharField(max_length=50, blank=True)
    
    publisher = models.CharField(max_length=255, blank=True)  # For books
    edition = models.CharField(max_length=50, blank=True)
    
    conference = models.CharField(max_length=255, blank=True)  # For conference papers
    location = models.CharField(max_length=255, blank=True)
    
    # Online Sources
    url = models.URLField(blank=True)
    doi = models.CharField(max_length=100, blank=True, verbose_name="DOI")
    accessed_date = models.DateField(null=True, blank=True)
    
    # Identifiers
    isbn = models.CharField(max_length=20, blank=True, verbose_name="ISBN")
    issn = models.CharField(max_length=20, blank=True, verbose_name="ISSN")
    
    # BibTeX
    bibtex_key = models.CharField(max_length=100, blank=True, db_index=True)
    bibtex_raw = models.TextField(blank=True, help_text="Raw BibTeX entry")
    
    # Organization
    tags = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    abstract = models.TextField(blank=True)
    
    # Usage tracking
    citation_count = models.IntegerField(default=0, help_text="Times cited in this project")
    is_read = models.BooleanField(default=False)
    is_key_source = models.BooleanField(default=False, help_text="Mark as key/important source")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_hub_literature_sources'
        ordering = ['authors', 'year']
        verbose_name = 'Literature Source'
        verbose_name_plural = 'Literature Sources'
    
    def __str__(self):
        author_short = self.authors.split(';')[0].split(',')[0] if self.authors else 'Unknown'
        return f"{author_short} ({self.year or 'n.d.'}) - {self.title[:50]}"
    
    def get_citation_key(self):
        """Generate citation key like 'Smith2024'"""
        if self.bibtex_key:
            return self.bibtex_key
        author_short = self.authors.split(';')[0].split(',')[0].strip() if self.authors else 'Unknown'
        return f"{author_short}{self.year or ''}"
    
    def format_apa(self):
        """Format citation in APA style"""
        authors = self._format_authors_apa()
        year = f"({self.year})" if self.year else "(n.d.)"
        title = self.title
        
        if self.source_type == 'article':
            journal = f"*{self.journal}*" if self.journal else ""
            vol_issue = f", {self.volume}" if self.volume else ""
            if self.issue:
                vol_issue += f"({self.issue})"
            pages = f", {self.pages}" if self.pages else ""
            doi = f" https://doi.org/{self.doi}" if self.doi else ""
            return f"{authors} {year}. {title}. {journal}{vol_issue}{pages}.{doi}"
        
        elif self.source_type == 'book':
            publisher_info = f"{self.location}: {self.publisher}" if self.location and self.publisher else self.publisher
            return f"{authors} {year}. *{title}*. {publisher_info}."
        
        elif self.source_type == 'website':
            url = f"Retrieved from {self.url}" if self.url else ""
            return f"{authors} {year}. {title}. {url}"
        
        return f"{authors} {year}. {title}."
    
    def format_harvard(self):
        """Format citation in Harvard style"""
        authors = self._format_authors_harvard()
        year = f"({self.year})" if self.year else "(n.d.)"
        
        if self.source_type == 'article':
            return f"{authors} {year} '{self.title}', *{self.journal}*, vol. {self.volume}, no. {self.issue}, pp. {self.pages}."
        elif self.source_type == 'book':
            return f"{authors} {year} *{self.title}*, {self.publisher}, {self.location}."
        
        return f"{authors} {year} '{self.title}'."
    
    def _format_authors_apa(self):
        """Format authors list for APA: Last, F. M., & Last, F. M."""
        if not self.authors:
            return "Unknown"
        
        author_list = [a.strip() for a in self.authors.split(';')]
        formatted = []
        
        for author in author_list[:7]:  # APA shows max 7 authors
            parts = author.split(',')
            if len(parts) >= 2:
                last = parts[0].strip()
                first_names = parts[1].strip().split()
                initials = ' '.join(f"{n[0]}." for n in first_names if n)
                formatted.append(f"{last}, {initials}")
            else:
                formatted.append(author)
        
        if len(author_list) > 7:
            return ', '.join(formatted[:6]) + ', ... ' + formatted[-1]
        elif len(formatted) > 1:
            return ', '.join(formatted[:-1]) + ', & ' + formatted[-1]
        return formatted[0] if formatted else "Unknown"
    
    def _format_authors_harvard(self):
        """Format authors list for Harvard: Last, F.M. and Last, F.M."""
        if not self.authors:
            return "Unknown"
        
        author_list = [a.strip() for a in self.authors.split(';')]
        formatted = []
        
        for author in author_list[:3]:  # Harvard typically shows 3 authors
            parts = author.split(',')
            if len(parts) >= 2:
                last = parts[0].strip()
                first_names = parts[1].strip().split()
                initials = ''.join(f"{n[0]}." for n in first_names if n)
                formatted.append(f"{last}, {initials}")
            else:
                formatted.append(author)
        
        if len(author_list) > 3:
            return formatted[0] + ' et al.'
        elif len(formatted) > 1:
            return ', '.join(formatted[:-1]) + ' and ' + formatted[-1]
        return formatted[0] if formatted else "Unknown"


class Citation(models.Model):
    """
    A citation instance within a chapter/section.
    Links a literature source to a specific location in the text.
    """
    
    CITATION_TYPE_CHOICES = [
        ('narrative', 'Narrative (Author, Year)'),
        ('parenthetical', 'Parenthetical (Author, Year)'),
        ('direct_quote', 'Direct Quote'),
        ('paraphrase', 'Paraphrase'),
    ]
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='citations'
    )
    source = models.ForeignKey(
        LiteratureSource,
        on_delete=models.CASCADE,
        related_name='citations'
    )
    chapter = models.ForeignKey(
        'bfagent.BookChapters',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='citations'
    )
    
    citation_type = models.CharField(max_length=20, choices=CITATION_TYPE_CHOICES, default='parenthetical')
    page_number = models.CharField(max_length=50, blank=True, help_text="Page(s) being cited")
    
    # For direct quotes
    quoted_text = models.TextField(blank=True)
    
    # Position in text (for tracking)
    position_marker = models.CharField(max_length=100, blank=True, help_text="Marker ID in text")
    
    # The formatted citation text
    citation_text = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'writing_hub_citations'
        ordering = ['created_at']
        verbose_name = 'Citation'
        verbose_name_plural = 'Citations'
    
    def __str__(self):
        return f"{self.source.get_citation_key()} in {self.chapter.title if self.chapter else 'Unknown'}"
    
    def format_inline(self, style='apa'):
        """Format the inline citation"""
        author_short = self.source.authors.split(';')[0].split(',')[0].strip() if self.source.authors else 'Unknown'
        year = self.source.year or 'n.d.'
        page = f", p. {self.page_number}" if self.page_number else ""
        
        if self.citation_type == 'narrative':
            return f"{author_short} ({year}{page})"
        else:  # parenthetical
            return f"({author_short}, {year}{page})"


class CitationStyle(models.Model):
    """
    Citation style configuration.
    Pre-configured styles: APA, MLA, Chicago, IEEE, Harvard.
    """
    
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Format templates (using placeholders)
    article_template = models.TextField(blank=True)
    book_template = models.TextField(blank=True)
    chapter_template = models.TextField(blank=True)
    website_template = models.TextField(blank=True)
    
    # Inline citation format
    inline_narrative_template = models.CharField(max_length=100, default="{author} ({year})")
    inline_parenthetical_template = models.CharField(max_length=100, default="({author}, {year})")
    
    # Bibliography formatting
    hanging_indent = models.BooleanField(default=True)
    sort_by = models.CharField(max_length=50, default='author')  # author, year, title
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'writing_hub_citation_styles'
        ordering = ['name']
        verbose_name = 'Citation Style'
        verbose_name_plural = 'Citation Styles'
    
    def __str__(self):
        return self.name


class LiteratureCollection(models.Model):
    """
    A collection/folder for organizing literature sources.
    E.g., "Theoretical Framework", "Methodology", "Related Work"
    """
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='literature_collections'
    )
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=20, default='#6366f1')
    icon = models.CharField(max_length=50, default='bi-folder')
    
    sources = models.ManyToManyField(
        LiteratureSource,
        blank=True,
        related_name='collections'
    )
    
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'writing_hub_literature_collections'
        ordering = ['sort_order', 'name']
        verbose_name = 'Literature Collection'
        verbose_name_plural = 'Literature Collections'
    
    def __str__(self):
        return f"{self.name} ({self.sources.count()} sources)"


class BibTeXImport(models.Model):
    """
    Track BibTeX imports for deduplication and updates.
    """
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='bibtex_imports'
    )
    
    filename = models.CharField(max_length=255)
    raw_content = models.TextField()
    entries_found = models.IntegerField(default=0)
    entries_imported = models.IntegerField(default=0)
    entries_updated = models.IntegerField(default=0)
    entries_skipped = models.IntegerField(default=0)
    
    import_log = models.JSONField(default=list)
    
    imported_at = models.DateTimeField(auto_now_add=True)
    imported_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        db_table = 'writing_hub_bibtex_imports'
        ordering = ['-imported_at']
        verbose_name = 'BibTeX Import'
        verbose_name_plural = 'BibTeX Imports'
    
    def __str__(self):
        return f"{self.filename} ({self.entries_imported} imported)"
