"""
Seed Academic Research Skills
=============================

Creates skills for academic research and citation management.
"""

from django.core.management.base import BaseCommand
from apps.bfagent.models import PromptTemplate


class Command(BaseCommand):
    help = 'Create academic research and citation management skills'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing skills',
        )

    def handle(self, *args, **options):
        force = options['force']
        
        skills = self._get_skills()
        
        created = 0
        updated = 0
        skipped = 0
        
        for skill_data in skills:
            template_key = skill_data['template_key']
            
            existing = PromptTemplate.objects.filter(template_key=template_key).first()
            
            if existing:
                if force:
                    for key, value in skill_data.items():
                        setattr(existing, key, value)
                    existing.save()
                    updated += 1
                    self.stdout.write(f"  Updated: {template_key}")
                else:
                    skipped += 1
                    self.stdout.write(f"  Skipped (exists): {template_key}")
            else:
                PromptTemplate.objects.create(**skill_data)
                created += 1
                self.stdout.write(self.style.SUCCESS(f"  Created: {template_key}"))
        
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Academic Skills: {created} created, {updated} updated, {skipped} skipped"
        ))

    def _get_skills(self):
        return [
            # =============================================
            # CITATION MANAGEMENT SKILL
            # =============================================
            {
                "template_key": "citation-management-skill",
                "name": "Citation Management",
                "category": "analysis",
                "description": "Format citations, generate bibliographies, and manage references in academic style",
                "skill_description": (
                    "Manages academic citations and references. Use when user needs to create "
                    "citations, format references, convert DOI to citation, generate bibliography, "
                    "export to BibTeX/RIS, or format in APA, MLA, Chicago, Harvard, IEEE, Vancouver style."
                ),
                "system_prompt": """You are an expert academic citation manager.

Your capabilities:
1. Format citations in multiple styles: APA 7, MLA 9, Chicago 17, Harvard, IEEE, Vancouver
2. Generate BibTeX and RIS exports for reference managers
3. Convert DOI to full citation
4. Create properly formatted bibliographies
5. Generate in-text citations

Citation Style Guidelines:
- APA 7: Author, A. A. (Year). Title. Journal, Volume(Issue), pages. https://doi.org/xxx
- MLA 9: Author. "Title." Journal, vol. X, no. X, Year, pp. X-X.
- Chicago: Author. "Title." Journal Volume, no. Issue (Year): pages.
- IEEE: [1] A. Author, "Title," Journal, vol. X, no. X, pp. X-X, Month Year.
- Vancouver: 1. Author AA. Title. Journal. Year;Volume(Issue):pages.

Always:
- Verify DOI when provided
- Include access date for web sources
- Format author names correctly for each style
- Handle edge cases (no author, no date, etc.)
""",
                "user_prompt_template": """Citation Task: {{task}}

Source Information:
{{source_info}}

Required Format: {{citation_style}}
Output Type: {{output_type}}

Please format the citation(s) according to the specified style.""",
                "required_variables": ["task", "source_info"],
                "optional_variables": ["citation_style", "output_type"],
                "variable_defaults": {
                    "citation_style": "apa",
                    "output_type": "full_citation"
                },
                "output_format": "markdown",
                "max_tokens": 1000,
                "temperature": 0.3,
                "license": "Apache-2.0",
                "author": "BF Agent",
                "compatibility": "Python 3.10+, CrossRef API",
                "allowed_tools": ["Read"],
                "references": {
                    "APA_STYLE": "https://apastyle.apa.org/",
                    "MLA_STYLE": "https://www.mla.org/",
                    "CHICAGO_STYLE": "https://www.chicagomanualofstyle.org/",
                    "CROSSREF": "https://api.crossref.org/",
                },
                "agent_class": "apps.research.services.CitationService",
                "is_active": True,
                "is_default": False,
            },
            
            # =============================================
            # GOOGLE SCHOLAR SEARCH SKILL
            # =============================================
            {
                "template_key": "google-scholar-skill",
                "name": "Google Scholar Search",
                "category": "analysis",
                "description": "Search Google Scholar for academic papers with citation counts",
                "skill_description": (
                    "Search Google Scholar for academic papers and scholarly articles. Use when user "
                    "asks for papers with citation counts, highly cited works, or needs Google Scholar "
                    "specifically. Includes proper source attribution and ethical rate limiting."
                ),
                "system_prompt": """You are an academic research assistant specializing in Google Scholar searches.

Your capabilities:
1. Search Google Scholar for academic papers
2. Find highly cited papers on a topic
3. Track citation counts
4. Identify key authors in a field

Important Guidelines:
- Always include proper source attribution: "Retrieved from Google Scholar"
- Respect rate limits (ethical scraping)
- Provide accurate citation counts when available
- Note that Google Scholar includes grey literature (theses, reports)

Output Format:
For each paper found, provide:
- Title
- Authors (first 3 + "et al." if more)
- Year of publication
- Journal/Source
- Citation count (if available)
- URL to paper
- Brief relevance note

Always remind users that Google Scholar may include non-peer-reviewed sources.""",
                "user_prompt_template": """Search Query: {{query}}

Search Parameters:
- Number of results: {{count}}
- Sort by: {{sort_by}}
- Year range: {{year_from}} - {{year_to}}

Please search Google Scholar and provide relevant academic papers with citation information.""",
                "required_variables": ["query"],
                "optional_variables": ["count", "sort_by", "year_from", "year_to"],
                "variable_defaults": {
                    "count": "10",
                    "sort_by": "relevance",
                    "year_from": "",
                    "year_to": ""
                },
                "output_format": "markdown",
                "max_tokens": 2000,
                "temperature": 0.3,
                "license": "Apache-2.0",
                "author": "BF Agent",
                "compatibility": "Python 3.10+, BeautifulSoup4, Rate-limited (2-4 sec delay)",
                "allowed_tools": ["WebSearch"],
                "references": {
                    "GOOGLE_SCHOLAR": "https://scholar.google.com/",
                    "RATE_LIMIT_NOTE": "Ethical scraping with 2-4 second delay between requests",
                },
                "agent_class": "apps.research.services.AcademicSearchService",
                "is_active": True,
                "is_default": False,
            },
            
            # =============================================
            # PUBMED SEARCH SKILL
            # =============================================
            {
                "template_key": "pubmed-search-skill",
                "name": "PubMed Biomedical Search",
                "category": "analysis",
                "description": "Search PubMed for biomedical and life sciences literature",
                "skill_description": (
                    "Search PubMed/MEDLINE for biomedical and life sciences research. Use when user "
                    "needs medical research, clinical studies, pharmaceutical papers, biology research, "
                    "or any health-related scientific literature. Free API, 35+ million citations."
                ),
                "system_prompt": """You are a biomedical research specialist using PubMed.

Your capabilities:
1. Search PubMed's 35+ million biomedical citations
2. Find clinical trials and medical studies
3. Access MEDLINE indexed journals
4. Retrieve abstracts and publication details

PubMed Strengths:
- Biomedical and life sciences focus
- Peer-reviewed medical journals
- Clinical trial data
- MeSH (Medical Subject Headings) for precise searching

Output Format:
For each paper:
- PMID (PubMed ID)
- Title
- Authors
- Journal
- Year
- Abstract (first 200 words)
- DOI (if available)
- Link to PubMed

Search Tips:
- Use medical terminology when possible
- Include MeSH terms for better results
- Filter by study type (clinical trial, review, etc.)""",
                "user_prompt_template": """Search Query: {{query}}

Search Filters:
- Number of results: {{count}}
- Article types: {{article_types}}
- Date range: {{date_range}}

Please search PubMed and provide relevant biomedical literature.""",
                "required_variables": ["query"],
                "optional_variables": ["count", "article_types", "date_range"],
                "variable_defaults": {
                    "count": "10",
                    "article_types": "all",
                    "date_range": ""
                },
                "output_format": "markdown",
                "max_tokens": 2000,
                "temperature": 0.3,
                "license": "Apache-2.0",
                "author": "BF Agent",
                "compatibility": "Python 3.10+, NCBI E-utilities API (free)",
                "allowed_tools": ["Read"],
                "references": {
                    "PUBMED": "https://pubmed.ncbi.nlm.nih.gov/",
                    "NCBI_API": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
                    "MESH": "https://www.nlm.nih.gov/mesh/",
                },
                "agent_class": "apps.research.services.AcademicSearchService",
                "is_active": True,
                "is_default": False,
            },
            
            # =============================================
            # OPENALEX SEARCH SKILL
            # =============================================
            {
                "template_key": "openalex-search-skill",
                "name": "OpenAlex Academic Search",
                "category": "analysis",
                "description": "Search OpenAlex for 250M+ academic works across all disciplines",
                "skill_description": (
                    "Search OpenAlex, the largest open academic database with 250+ million works. "
                    "Use when user needs comprehensive academic search across all disciplines, "
                    "citation analysis, author profiles, or institution data. Free, replaces Microsoft Academic."
                ),
                "system_prompt": """You are a research specialist using OpenAlex.

OpenAlex is the world's largest open academic database:
- 250+ million academic works
- Replaces Microsoft Academic (discontinued 2021)
- Free, no authentication required
- Covers all academic disciplines

Your capabilities:
1. Search across all academic fields
2. Get citation counts and impact metrics
3. Find open access versions of papers
4. Track author and institution data
5. Analyze research topics and concepts

Output Format:
For each paper:
- Title
- Authors (with affiliations)
- Year
- Journal/Source
- Citation count
- Open Access status (and link if available)
- DOI
- Related concepts/topics

Advantages over other sources:
- Broader coverage than any single database
- Free and open
- Includes citation graph data
- Links to open access versions""",
                "user_prompt_template": """Search Query: {{query}}

Search Parameters:
- Number of results: {{count}}
- Filter by year: {{year_filter}}
- Open access only: {{open_access_only}}
- Sort by: {{sort_by}}

Please search OpenAlex and provide comprehensive academic results.""",
                "required_variables": ["query"],
                "optional_variables": ["count", "year_filter", "open_access_only", "sort_by"],
                "variable_defaults": {
                    "count": "10",
                    "year_filter": "",
                    "open_access_only": "false",
                    "sort_by": "relevance"
                },
                "output_format": "markdown",
                "max_tokens": 2000,
                "temperature": 0.3,
                "license": "Apache-2.0",
                "author": "BF Agent",
                "compatibility": "Python 3.10+, OpenAlex API (free, 100k/day)",
                "allowed_tools": ["Read"],
                "references": {
                    "OPENALEX": "https://openalex.org/",
                    "OPENALEX_API": "https://api.openalex.org/",
                    "DOCS": "https://docs.openalex.org/",
                },
                "agent_class": "apps.research.services.AcademicSearchService",
                "is_active": True,
                "is_default": False,
            },
            
            # =============================================
            # BIBLIOGRAPHY GENERATOR SKILL
            # =============================================
            {
                "template_key": "bibliography-generator-skill",
                "name": "Bibliography Generator",
                "category": "analysis",
                "description": "Generate formatted bibliographies from collected sources",
                "skill_description": (
                    "Generate complete bibliographies from research sources. Use when user has "
                    "collected sources and needs a formatted reference list, works cited page, "
                    "or bibliography in any academic style. Supports export to BibTeX, RIS, EndNote."
                ),
                "system_prompt": """You are a bibliography and reference list specialist.

Your task is to create properly formatted bibliographies from collected sources.

Supported Output Formats:
1. Formatted Reference Lists:
   - APA 7th Edition (alphabetical by author)
   - MLA 9th Edition (Works Cited)
   - Chicago (Bibliography or Notes-Bibliography)
   - Harvard (Reference List)
   - IEEE (Numbered references)
   - Vancouver (Numbered, medical)

2. Export Formats:
   - BibTeX (.bib) for LaTeX
   - RIS (.ris) for EndNote, Zotero, Mendeley
   - Markdown (formatted list)

Bibliography Rules:
- Sort entries according to style requirements
- Handle special cases (no author, multiple authors, etc.)
- Include all required fields for each source type
- Properly format URLs, DOIs, and access dates
- Maintain consistent formatting throughout

Always verify:
- Author name order and format
- Date format for each style
- Title capitalization rules
- Punctuation and spacing""",
                "user_prompt_template": """Sources to Include:
{{sources}}

Output Requirements:
- Citation Style: {{citation_style}}
- Output Format: {{output_format}}
- Sort Order: {{sort_order}}
- Include Annotations: {{include_annotations}}

Please generate a properly formatted bibliography.""",
                "required_variables": ["sources"],
                "optional_variables": ["citation_style", "output_format", "sort_order", "include_annotations"],
                "variable_defaults": {
                    "citation_style": "apa",
                    "output_format": "markdown",
                    "sort_order": "author",
                    "include_annotations": "false"
                },
                "output_format": "markdown",
                "max_tokens": 3000,
                "temperature": 0.2,
                "license": "Apache-2.0",
                "author": "BF Agent",
                "compatibility": "Python 3.10+",
                "allowed_tools": ["Read"],
                "references": {
                    "APA_GUIDE": "https://apastyle.apa.org/style-grammar-guidelines/references",
                    "MLA_GUIDE": "https://style.mla.org/works-cited/",
                },
                "agent_class": "apps.research.services.CitationService",
                "is_active": True,
                "is_default": False,
            },
        ]
