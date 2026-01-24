"""
Research Hub - Domain Models
============================

Zentrale Recherche-Plattform mit Web-Suche (Brave), Knowledge Base, und Faktenprüfung.
Stellt Research-Dienste für alle anderen Domains bereit.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ResearchProject(models.Model):
    """
    Main project model for Research Hub domain.
    Represents a single research workflow instance with all associated data.
    """
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        IN_PROGRESS = 'in_progress', _('In Progress')
        REVIEW = 'review', _('In Review')
        COMPLETED = 'completed', _('Completed')
        ARCHIVED = 'archived', _('Archived')
    
    class ResearchType(models.TextChoices):
        """Different research modes with specific outputs."""
        QUICK_FACTS = 'quick_facts', _('Quick Facts')
        DEEP_DIVE = 'deep_dive', _('Deep Dive')
        ACADEMIC = 'academic', _('Academic Research')
    
    class OutputFormat(models.TextChoices):
        """Output format for research results."""
        MARKDOWN = 'markdown', _('Markdown')
        HTML = 'html', _('HTML')
        LATEX = 'latex', _('LaTeX')
        PDF = 'pdf', _('PDF')
        BIBTEX = 'bibtex', _('BibTeX')
    
    # Core Fields
    name = models.CharField(
        max_length=200,
        verbose_name=_('Project Name')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    query = models.TextField(
        blank=True,
        verbose_name=_('Research Query'),
        help_text=_('Main research question or topic')
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_('Status'),
        db_index=True
    )
    
    # Research Type
    research_type = models.CharField(
        max_length=20,
        choices=ResearchType.choices,
        default=ResearchType.QUICK_FACTS,
        verbose_name=_('Research Type'),
        db_index=True
    )
    output_format = models.CharField(
        max_length=20,
        choices=OutputFormat.choices,
        default=OutputFormat.MARKDOWN,
        verbose_name=_('Output Format')
    )
    
    # Academic-specific settings
    citation_style = models.CharField(
        max_length=20,
        choices=[
            ('apa', 'APA (7th Edition)'),
            ('mla', 'MLA (9th Edition)'),
            ('chicago', 'Chicago'),
            ('harvard', 'Harvard'),
            ('ieee', 'IEEE'),
            ('vancouver', 'Vancouver'),
        ],
        default='apa',
        verbose_name=_('Citation Style')
    )
    require_peer_reviewed = models.BooleanField(
        default=False,
        verbose_name=_('Require Peer-Reviewed Sources'),
        help_text=_('Only include peer-reviewed sources (for academic research)')
    )
    
    # Workflow Tracking
    current_phase = models.CharField(
        max_length=50,
        default='thema_definieren',
        verbose_name=_('Current Phase')
    )
    
    # Ownership
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='research_projects',
        verbose_name=_('Owner'),
        null=True,
        blank=True
    )
    
    # Metadata (flexible JSON storage)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Metadata')
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = _('Research Project')
        verbose_name_plural = _('Research Projects')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['current_phase']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    @classmethod
    def get_phases(cls) -> list:
        """Return list of workflow phases."""
        return [
            ('thema_definieren', 'Thema definieren'),
            ('quellen_sammeln', 'Quellen sammeln'),
            ('analyse', 'Analyse'),
            ('zusammenfassung', 'Zusammenfassung'),
            ('export', 'Export'),
        ]
    
    def advance_phase(self) -> bool:
        """Move to next workflow phase."""
        phases = [p[0] for p in self.get_phases()]
        try:
            current_idx = phases.index(self.current_phase)
            if current_idx < len(phases) - 1:
                self.current_phase = phases[current_idx + 1]
                self.save(update_fields=['current_phase', 'updated_at'])
                return True
        except ValueError:
            pass
        return False


class ResearchSource(models.Model):
    """
    Sources found during research (web pages, documents, etc.)
    """
    
    class SourceType(models.TextChoices):
        WEB = 'web', _('Web Page')
        PDF = 'pdf', _('PDF Document')
        ARTICLE = 'article', _('Article')
        JOURNAL = 'journal', _('Journal Article')
        BOOK = 'book', _('Book')
        CHAPTER = 'chapter', _('Book Chapter')
        CONFERENCE = 'conference', _('Conference Paper')
        THESIS = 'thesis', _('Thesis/Dissertation')
        VIDEO = 'video', _('Video')
        KNOWLEDGE_BASE = 'kb', _('Knowledge Base')
        OTHER = 'other', _('Other')
    
    project = models.ForeignKey(
        ResearchProject,
        on_delete=models.CASCADE,
        related_name='sources',
        verbose_name=_('Project')
    )
    
    # Source Info
    title = models.CharField(max_length=500, verbose_name=_('Title'))
    url = models.URLField(max_length=2000, blank=True, verbose_name=_('URL'))
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.WEB,
        verbose_name=_('Type')
    )
    
    # Content
    snippet = models.TextField(blank=True, verbose_name=_('Snippet'))
    full_content = models.TextField(blank=True, verbose_name=_('Full Content'))
    
    # Scoring
    relevance_score = models.FloatField(
        default=0.0,
        verbose_name=_('Relevance Score'),
        help_text=_('0.0 to 1.0')
    )
    credibility_score = models.FloatField(
        default=0.0,
        verbose_name=_('Credibility Score'),
        help_text=_('0.0 to 1.0')
    )
    
    # Academic Fields (for citations)
    authors = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Authors'),
        help_text=_('List of author names: ["Last, First", "Last, First"]')
    )
    publication_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Publication Date')
    )
    journal_name = models.CharField(
        max_length=300,
        blank=True,
        verbose_name=_('Journal/Publisher')
    )
    volume = models.CharField(max_length=50, blank=True, verbose_name=_('Volume'))
    issue = models.CharField(max_length=50, blank=True, verbose_name=_('Issue'))
    pages = models.CharField(max_length=50, blank=True, verbose_name=_('Pages'))
    doi = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('DOI'),
        help_text=_('Digital Object Identifier')
    )
    isbn = models.CharField(max_length=20, blank=True, verbose_name=_('ISBN'))
    is_peer_reviewed = models.BooleanField(
        default=False,
        verbose_name=_('Peer-Reviewed')
    )
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = _('Research Source')
        verbose_name_plural = _('Research Sources')
        ordering = ['-relevance_score', '-created_at']
    
    def __str__(self):
        return f"{self.title[:50]}... ({self.get_source_type_display()})"
    
    def format_citation(self, style: str = 'apa') -> str:
        """Format this source as a citation in the specified style."""
        authors_str = self._format_authors(style)
        year = self.publication_date.year if self.publication_date else 'n.d.'
        
        if style == 'apa':
            return self._format_apa(authors_str, year)
        elif style == 'mla':
            return self._format_mla(authors_str)
        elif style == 'chicago':
            return self._format_chicago(authors_str, year)
        elif style == 'ieee':
            return self._format_ieee(authors_str, year)
        else:
            return self._format_apa(authors_str, year)
    
    def _format_authors(self, style: str) -> str:
        """Format authors list based on citation style."""
        if not self.authors:
            return ''
        
        if style == 'apa':
            if len(self.authors) == 1:
                return self.authors[0]
            elif len(self.authors) == 2:
                return f"{self.authors[0]} & {self.authors[1]}"
            else:
                return f"{self.authors[0]} et al."
        elif style == 'mla':
            if len(self.authors) == 1:
                return self.authors[0]
            elif len(self.authors) == 2:
                return f"{self.authors[0]} and {self.authors[1]}"
            else:
                return f"{self.authors[0]}, et al."
        else:
            return ', '.join(self.authors[:3]) + (' et al.' if len(self.authors) > 3 else '')
    
    def _format_apa(self, authors: str, year) -> str:
        """APA 7th Edition format."""
        base = f"{authors} ({year}). {self.title}."
        if self.journal_name:
            base += f" *{self.journal_name}*"
            if self.volume:
                base += f", *{self.volume}*"
                if self.issue:
                    base += f"({self.issue})"
            if self.pages:
                base += f", {self.pages}"
            base += "."
        if self.doi:
            base += f" https://doi.org/{self.doi}"
        return base
    
    def _format_mla(self, authors: str) -> str:
        """MLA 9th Edition format."""
        date_str = self.publication_date.strftime('%d %b. %Y') if self.publication_date else ''
        base = f"{authors}. \"{self.title}.\""
        if self.journal_name:
            base += f" *{self.journal_name}*"
            if self.volume:
                base += f", vol. {self.volume}"
            if self.issue:
                base += f", no. {self.issue}"
            if date_str:
                base += f", {date_str}"
            if self.pages:
                base += f", pp. {self.pages}"
            base += "."
        if self.doi:
            base += f" doi:{self.doi}."
        return base
    
    def _format_chicago(self, authors: str, year) -> str:
        """Chicago style format."""
        base = f"{authors}. \"{self.title}.\""
        if self.journal_name:
            base += f" *{self.journal_name}*"
            if self.volume:
                base += f" {self.volume}"
            if self.issue:
                base += f", no. {self.issue}"
            base += f" ({year})"
            if self.pages:
                base += f": {self.pages}"
            base += "."
        if self.doi:
            base += f" https://doi.org/{self.doi}."
        return base
    
    def _format_ieee(self, authors: str, year) -> str:
        """IEEE style format."""
        base = f"{authors}, \"{self.title},\""
        if self.journal_name:
            base += f" *{self.journal_name}*"
            if self.volume:
                base += f", vol. {self.volume}"
            if self.issue:
                base += f", no. {self.issue}"
            if self.pages:
                base += f", pp. {self.pages}"
            base += f", {year}."
        if self.doi:
            base += f" doi: {self.doi}."
        return base
    
    def to_bibtex(self) -> str:
        """Export source as BibTeX entry."""
        import re
        # Generate citation key
        first_author = self.authors[0].split(',')[0] if self.authors else 'Unknown'
        year = self.publication_date.year if self.publication_date else 'nd'
        key = re.sub(r'[^a-zA-Z0-9]', '', f"{first_author}{year}")
        
        entry_type = 'article' if self.source_type == 'journal' else 'misc'
        if self.source_type == 'book':
            entry_type = 'book'
        elif self.source_type == 'conference':
            entry_type = 'inproceedings'
        elif self.source_type == 'thesis':
            entry_type = 'phdthesis'
        
        lines = [f"@{entry_type}{{{key},"]
        lines.append(f"  title = {{{self.title}}},")
        if self.authors:
            lines.append(f"  author = {{{' and '.join(self.authors)}}},")
        if self.publication_date:
            lines.append(f"  year = {{{self.publication_date.year}}},")
        if self.journal_name:
            lines.append(f"  journal = {{{self.journal_name}}},")
        if self.volume:
            lines.append(f"  volume = {{{self.volume}}},")
        if self.issue:
            lines.append(f"  number = {{{self.issue}}},")
        if self.pages:
            lines.append(f"  pages = {{{self.pages}}},")
        if self.doi:
            lines.append(f"  doi = {{{self.doi}}},")
        if self.url:
            lines.append(f"  url = {{{self.url}}},")
        lines.append("}")
        
        return '\n'.join(lines)


class ResearchFinding(models.Model):
    """
    Key findings extracted from sources.
    """
    
    class FindingType(models.TextChoices):
        FACT = 'fact', _('Fact')
        QUOTE = 'quote', _('Quote')
        STATISTIC = 'statistic', _('Statistic')
        CLAIM = 'claim', _('Claim')
        CONCLUSION = 'conclusion', _('Conclusion')
    
    project = models.ForeignKey(
        ResearchProject,
        on_delete=models.CASCADE,
        related_name='findings',
        verbose_name=_('Project')
    )
    source = models.ForeignKey(
        ResearchSource,
        on_delete=models.CASCADE,
        related_name='findings',
        verbose_name=_('Source'),
        null=True,
        blank=True
    )
    
    # Finding Content
    content = models.TextField(verbose_name=_('Content'))
    finding_type = models.CharField(
        max_length=20,
        choices=FindingType.choices,
        default=FindingType.FACT,
        verbose_name=_('Type')
    )
    
    # Verification
    is_verified = models.BooleanField(default=False, verbose_name=_('Verified'))
    verification_notes = models.TextField(blank=True, verbose_name=_('Verification Notes'))
    
    # Importance
    importance = models.PositiveSmallIntegerField(
        default=5,
        verbose_name=_('Importance'),
        help_text=_('1-10 scale')
    )
    
    # Tags
    tags = models.JSONField(default=list, blank=True, verbose_name=_('Tags'))
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = _('Research Finding')
        verbose_name_plural = _('Research Findings')
        ordering = ['-importance', '-created_at']
    
    def __str__(self):
        return f"{self.content[:50]}... ({self.get_finding_type_display()})"


class ResearchResult(models.Model):
    """
    Stores processing results for Research Hub workflows.
    One result per handler execution within a project.
    """
    
    project = models.ForeignKey(
        ResearchProject,
        on_delete=models.CASCADE,
        related_name='results',
        verbose_name=_('Project')
    )
    handler_name = models.CharField(
        max_length=100,
        verbose_name=_('Handler'),
        db_index=True
    )
    phase = models.CharField(
        max_length=50,
        verbose_name=_('Phase')
    )
    
    # Result Data
    result_data = models.JSONField(
        default=dict,
        verbose_name=_('Result Data')
    )
    
    # Status
    success = models.BooleanField(
        default=True,
        verbose_name=_('Success'),
        db_index=True
    )
    error_message = models.TextField(
        blank=True,
        verbose_name=_('Error Message')
    )
    
    # Performance
    execution_time_ms = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Execution Time (ms)')
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = _('Research Result')
        verbose_name_plural = _('Research Results')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'handler_name']),
            models.Index(fields=['success']),
        ]
    
    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.handler_name} ({self.phase})"


class ResearchTemplate(models.Model):
    """
    Reusable research workflow templates.
    
    Templates define:
    - Research type and settings
    - Search queries/patterns
    - Required sections
    - Output format
    """
    
    class Category(models.TextChoices):
        LITERATURE_REVIEW = 'literature_review', _('Literature Review')
        MARKET_RESEARCH = 'market_research', _('Market Research')
        COMPETITIVE_ANALYSIS = 'competitive_analysis', _('Competitive Analysis')
        FACT_CHECKING = 'fact_checking', _('Fact Checking')
        TECHNICAL_RESEARCH = 'technical_research', _('Technical Research')
        GENERAL = 'general', _('General Research')
    
    # Core Fields
    name = models.CharField(
        max_length=200,
        verbose_name=_('Template Name')
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name=_('Slug')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.GENERAL,
        verbose_name=_('Category')
    )
    
    # Research Settings
    research_type = models.CharField(
        max_length=20,
        choices=ResearchProject.ResearchType.choices,
        default=ResearchProject.ResearchType.DEEP_DIVE,
        verbose_name=_('Research Type')
    )
    output_format = models.CharField(
        max_length=20,
        choices=ResearchProject.OutputFormat.choices,
        default=ResearchProject.OutputFormat.MARKDOWN,
        verbose_name=_('Output Format')
    )
    
    # Academic Settings (for academic templates)
    citation_style = models.CharField(
        max_length=20,
        choices=[
            ('apa', 'APA'),
            ('mla', 'MLA'),
            ('chicago', 'Chicago'),
            ('harvard', 'Harvard'),
            ('ieee', 'IEEE'),
        ],
        default='apa',
        verbose_name=_('Citation Style')
    )
    require_peer_reviewed = models.BooleanField(
        default=False,
        verbose_name=_('Require Peer-Reviewed')
    )
    
    # Template Structure
    sections = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Sections'),
        help_text=_('List of sections: [{"id": "intro", "title": "Introduction", "query_template": "{topic} overview"}]')
    )
    
    # Search Settings
    default_query_template = models.TextField(
        blank=True,
        verbose_name=_('Default Query Template'),
        help_text=_('Use {topic} as placeholder, e.g., "{topic} research 2024"')
    )
    source_filters = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Source Filters'),
        help_text=_('Filters: {"domains": ["arxiv.org"], "exclude": ["wikipedia.org"]}')
    )
    min_sources = models.PositiveIntegerField(
        default=5,
        verbose_name=_('Minimum Sources')
    )
    max_sources = models.PositiveIntegerField(
        default=20,
        verbose_name=_('Maximum Sources')
    )
    
    # Ownership & Visibility
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='research_templates',
        verbose_name=_('Owner'),
        null=True,
        blank=True
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name=_('Public Template')
    )
    is_system = models.BooleanField(
        default=False,
        verbose_name=_('System Template'),
        help_text=_('Built-in template, cannot be deleted')
    )
    
    # Usage Stats
    usage_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Usage Count')
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = _('Research Template')
        verbose_name_plural = _('Research Templates')
        ordering = ['-is_system', '-usage_count', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"
    
    def create_project(self, name: str, topic: str, owner=None) -> 'ResearchProject':
        """
        Create a new ResearchProject from this template.
        
        Args:
            name: Project name
            topic: Research topic (replaces {topic} in templates)
            owner: Project owner
            
        Returns:
            New ResearchProject instance
        """
        # Build query from template
        query = self.default_query_template.replace('{topic}', topic) if self.default_query_template else topic
        
        # Create project
        project = ResearchProject.objects.create(
            name=name,
            query=query,
            description=f"Created from template: {self.name}",
            research_type=self.research_type,
            output_format=self.output_format,
            citation_style=self.citation_style,
            require_peer_reviewed=self.require_peer_reviewed,
            owner=owner,
            metadata={
                'template_id': self.pk,
                'template_name': self.name,
                'sections': self.sections,
                'source_filters': self.source_filters,
                'min_sources': self.min_sources,
                'max_sources': self.max_sources,
            }
        )
        
        # Increment usage
        self.usage_count += 1
        self.save(update_fields=['usage_count'])
        
        return project
    
    @classmethod
    def get_system_templates(cls):
        """Return all system templates."""
        return cls.objects.filter(is_system=True, is_active=True)
    
    @classmethod
    def get_public_templates(cls):
        """Return all public templates."""
        return cls.objects.filter(is_public=True, is_active=True)
