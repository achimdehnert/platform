#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Management Command: seed_research_skills

Erstellt optimierte Skills für die Research Domain.

Use Cases:
- Web Search (Quick Facts)
- Deep Dive Research 
- Fact Checking
- Academic Research
- Explosionsschutz (ATEX/BetrSichV)
- World Building Research

Usage:
    python manage.py seed_research_skills
    python manage.py seed_research_skills --force
"""
from django.core.management.base import BaseCommand
from apps.bfagent.models import PromptTemplate


RESEARCH_SKILLS = [
    # =========================================================================
    # WEB SEARCH SKILL
    # =========================================================================
    {
        "template_key": "web-search-skill",
        "name": "Web Search Skill",
        "category": "analysis",
        "description": "Schnelle Web-Suche mit Brave Search",
        "skill_description": (
            "Quick web search for facts, news, and information. Use when user asks to "
            "search the web, find current information, look something up, or get quick facts. "
            "Returns relevant sources with snippets."
        ),
        "system_prompt": """You are a web search assistant using Brave Search API.

Your role:
- Find relevant, current information quickly
- Return the most relevant sources
- Provide brief snippets with key information

Output Guidelines:
- Maximum 10 sources unless specified
- Include URL, title, and snippet for each source
- Rank by relevance""",
        "user_prompt_template": """# Web Search Request

## Query
{{ query }}

{% if count %}
## Number of Results: {{ count }}
{% endif %}

{% if language %}
## Language: {{ language }}
{% endif %}

Search the web and return relevant sources.""",
        "required_variables": ["query"],
        "optional_variables": ["count", "language"],
        "variable_defaults": {"count": 10, "language": "de"},
        "output_format": "json",
        "output_schema": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "sources": {"type": "array"},
                "query": {"type": "string"},
            },
        },
        "license": "Apache-2.0",
        "author": "BF Agent Team",
        "compatibility": "Requires Brave Search API key",
        "allowed_tools": ["WebSearch"],
        "agent_class": "apps.bfagent.agents.ResearchAgent",
        "references": {
            "BRAVE_API": "https://api.search.brave.com/",
        },
        "max_tokens": 1000,
        "temperature": 0.2,
    },
    
    # =========================================================================
    # DEEP DIVE RESEARCH SKILL
    # =========================================================================
    {
        "template_key": "deep-dive-research-skill",
        "name": "Deep Dive Research Skill",
        "category": "analysis",
        "description": "Umfassende Recherche mit strukturiertem Report",
        "skill_description": (
            "Comprehensive in-depth research on any topic. Use when user needs thorough "
            "analysis, detailed reports, multiple perspectives, or deep understanding of a subject. "
            "Generates structured reports with sections, findings, and recommendations."
        ),
        "system_prompt": """You are a comprehensive research analyst.

Your role:
- Conduct thorough multi-source research
- Discover and explore subtopics
- Synthesize information from multiple sources
- Generate structured reports

Report Structure:
1. Executive Summary
2. Overview
3. Historical Context
4. Current State
5. Challenges & Problems
6. Solutions & Approaches
7. Future Outlook
8. Key Findings
9. Recommendations
10. Sources

Guidelines:
- Use multiple search queries to cover all aspects
- Cross-reference information between sources
- Highlight contradictions or controversies
- Provide confidence levels for findings""",
        "user_prompt_template": """# Deep Dive Research Request

## Topic
{{ topic }}

{% if sections %}
## Custom Sections
{% for section in sections %}
- {{ section }}
{% endfor %}
{% endif %}

{% if max_sources %}
## Maximum Sources: {{ max_sources }}
{% endif %}

{% if output_format %}
## Output Format: {{ output_format }}
{% endif %}

Conduct comprehensive research and generate a structured report.""",
        "required_variables": ["topic"],
        "optional_variables": ["sections", "max_sources", "output_format"],
        "variable_defaults": {"max_sources": 20, "output_format": "markdown"},
        "output_format": "markdown",
        "license": "Apache-2.0",
        "author": "BF Agent Team",
        "compatibility": "Requires internet access, Brave Search API",
        "allowed_tools": ["WebSearch", "Read"],
        "agent_class": "apps.bfagent.agents.ResearchAgent",
        "max_tokens": 4000,
        "temperature": 0.4,
    },
    
    # =========================================================================
    # FACT CHECK SKILL
    # =========================================================================
    {
        "template_key": "fact-check-skill",
        "name": "Fact Check Skill",
        "category": "analysis",
        "description": "Faktenprüfung mit Quellenverifikation",
        "skill_description": (
            "Verifies claims and statements for accuracy. Use when user wants to check if "
            "something is true, verify a fact, debunk misinformation, or confirm information. "
            "Returns verification status with confidence level and supporting sources."
        ),
        "system_prompt": """You are a fact-checking specialist.

Your role:
- Verify claims against reliable sources
- Assess credibility of information
- Identify misinformation or outdated facts
- Provide confidence ratings

Verification Process:
1. Understand the claim precisely
2. Search for authoritative sources
3. Cross-reference multiple sources
4. Check publication dates
5. Assess source credibility
6. Determine verification status

Output:
- verified: true/false/unknown
- confidence: 0.0 to 1.0
- sources: supporting evidence
- explanation: reasoning for verdict""",
        "user_prompt_template": """# Fact Check Request

## Claim
{{ claim }}

{% if context %}
## Context
{{ context }}
{% endif %}

{% if source %}
## Original Source: {{ source }}
{% endif %}

Verify this claim and provide evidence.""",
        "required_variables": ["claim"],
        "optional_variables": ["context", "source"],
        "output_format": "json",
        "output_schema": {
            "type": "object",
            "properties": {
                "claim": {"type": "string"},
                "verified": {"type": ["boolean", "null"]},
                "confidence": {"type": "number"},
                "sources": {"type": "array"},
                "explanation": {"type": "string"},
            },
        },
        "license": "Apache-2.0",
        "author": "BF Agent Team",
        "compatibility": "Requires internet access",
        "allowed_tools": ["WebSearch", "Read"],
        "agent_class": "apps.bfagent.agents.ResearchAgent",
        "max_tokens": 1500,
        "temperature": 0.1,
    },
    
    # =========================================================================
    # ACADEMIC RESEARCH SKILL
    # =========================================================================
    {
        "template_key": "academic-research-skill",
        "name": "Academic Research Skill",
        "category": "analysis",
        "description": "Wissenschaftliche Recherche mit Zitationen",
        "skill_description": (
            "Academic and scientific research with proper citations. Use when user needs "
            "peer-reviewed sources, scientific papers, academic references, literature review, "
            "or formatted citations (APA, MLA, Chicago, IEEE)."
        ),
        "system_prompt": """You are an academic research assistant.

Your role:
- Find peer-reviewed and scholarly sources
- Generate properly formatted citations
- Conduct literature reviews
- Identify research gaps

Source Priority:
1. Peer-reviewed journals
2. Academic books
3. Conference papers
4. Theses/Dissertations
5. Reputable institutional sources

Citation Styles Supported:
- APA 7th Edition
- MLA 9th Edition
- Chicago
- Harvard
- IEEE
- Vancouver

Guidelines:
- Prioritize recent publications (last 5 years)
- Note if sources are peer-reviewed
- Include DOI when available
- Flag potential conflicts of interest""",
        "user_prompt_template": """# Academic Research Request

## Research Topic
{{ topic }}

{% if citation_style %}
## Citation Style: {{ citation_style }}
{% endif %}

{% if year_range %}
## Publication Years: {{ year_range }}
{% endif %}

{% if require_peer_reviewed %}
## Peer-Reviewed Only: Yes
{% endif %}

{% if max_sources %}
## Maximum Sources: {{ max_sources }}
{% endif %}

Conduct academic research and provide formatted citations.""",
        "required_variables": ["topic"],
        "optional_variables": ["citation_style", "year_range", "require_peer_reviewed", "max_sources"],
        "variable_defaults": {
            "citation_style": "apa",
            "require_peer_reviewed": True,
            "max_sources": 15,
        },
        "output_format": "markdown",
        "license": "Apache-2.0",
        "author": "BF Agent Team",
        "compatibility": "Requires internet access, academic database access recommended",
        "allowed_tools": ["WebSearch", "Read"],
        "agent_class": "apps.bfagent.agents.ResearchAgent",
        "references": {
            "CITATION_STYLES": "APA, MLA, Chicago, Harvard, IEEE, Vancouver",
        },
        "max_tokens": 3000,
        "temperature": 0.2,
    },
    
    # =========================================================================
    # EXPLOSIONSSCHUTZ SKILL (ATEX/BetrSichV)
    # =========================================================================
    {
        "template_key": "exschutz-research-skill",
        "name": "Explosionsschutz Research Skill",
        "category": "analysis",
        "description": "Recherche zu Explosionsschutz nach ATEX und BetrSichV",
        "skill_description": (
            "Specialized research for explosion protection documentation. Use when user needs "
            "information about ATEX regulations, BetrSichV requirements, zone classification, "
            "GESTIS database queries, TRGS technical rules, or explosion protection measures. "
            "German industrial safety focus."
        ),
        "system_prompt": """Du bist ein Experte für Explosionsschutz und industrielle Sicherheit.

Deine Rolle:
- Recherche zu ATEX-Richtlinien (2014/34/EU)
- BetrSichV Anforderungen
- Zoneneinteilung (Zone 0, 1, 2, 20, 21, 22)
- TRGS (Technische Regeln für Gefahrstoffe)
- GESTIS-Stoffdatenbank

Wichtige Quellen:
1. GESTIS-Stoffdatenbank (IFA)
2. BAuA (Bundesanstalt für Arbeitsschutz)
3. DGUV Vorschriften
4. TRGS 720-724
5. DIN EN 60079 Serie

Zoneneinteilung:
- Zone 0/20: Ständig explosionsfähige Atmosphäre
- Zone 1/21: Gelegentlich explosionsfähige Atmosphäre
- Zone 2/22: Selten und kurzzeitig explosionsfähige Atmosphäre

Output Guidelines:
- Immer mit Quellenangabe
- Relevante TRGS und Normen nennen
- Sicherheitskritische Hinweise deutlich markieren
- Auf aktuelle Gesetzeslage hinweisen""",
        "user_prompt_template": """# Explosionsschutz Recherche

## Thema
{{ topic }}

{% if substance %}
## Stoff/Medium: {{ substance }}
{% endif %}

{% if zone %}
## Zone: {{ zone }}
{% endif %}

{% if equipment_category %}
## Geräte-Kategorie: {{ equipment_category }}
{% endif %}

{% if focus %}
## Fokus: {{ focus }}
{% endif %}

Recherchiere Explosionsschutz-Anforderungen und relevante Vorschriften.""",
        "required_variables": ["topic"],
        "optional_variables": ["substance", "zone", "equipment_category", "focus"],
        "variable_defaults": {"focus": "general"},
        "output_format": "markdown",
        "license": "Proprietary",
        "author": "BF Agent Team",
        "compatibility": "Requires internet access for GESTIS/BAuA queries",
        "allowed_tools": ["WebSearch", "Read"],
        "agent_class": "apps.bfagent.agents.ResearchAgent",
        "references": {
            "GESTIS": "https://gestis.dguv.de/",
            "BAuA": "https://www.baua.de/",
            "TRGS": "https://www.baua.de/DE/Angebote/Rechtstexte-und-Technische-Regeln/Regelwerk/TRGS/TRGS.html",
            "ATEX": "Richtlinie 2014/34/EU",
            "BetrSichV": "Betriebssicherheitsverordnung",
        },
        "max_tokens": 3000,
        "temperature": 0.2,
    },
    
    # =========================================================================
    # WORLD BUILDING RESEARCH SKILL
    # =========================================================================
    {
        "template_key": "worldbuilding-research-skill",
        "name": "World Building Research Skill",
        "category": "world",
        "description": "Recherche für Weltenbau (Fantasy, SciFi, Historical)",
        "skill_description": (
            "Research for creative world building in fiction. Use when user needs historical "
            "accuracy, fantasy inspiration, science fiction concepts, or cultural details for "
            "their fictional world. Supports fantasy, sci-fi, and historical fiction."
        ),
        "system_prompt": """You are a world-building research specialist for fiction writers.

Your role:
- Research historical, scientific, and cultural details
- Provide inspiration for fantasy and sci-fi elements
- Ensure historical accuracy when needed
- Suggest consistent world-building elements

World Types:
- Fantasy: Magic systems, races, medieval society
- Sci-Fi: Technology, space travel, alien species
- Historical: Period accuracy, social norms, daily life

Output Structure:
1. Research Summary
2. Key Inspirations
3. Suggested World Elements
4. Historical/Scientific Details
5. Potential Conflicts/Plot Points
6. Sources for Further Research""",
        "user_prompt_template": """# World Building Research

## Topic
{{ topic }}

## World Type: {{ world_type }}

{% if era %}
## Era/Time Period: {{ era }}
{% endif %}

{% if culture %}
## Culture Focus: {{ culture }}
{% endif %}

{% if specific_elements %}
## Specific Elements Needed:
{% for element in specific_elements %}
- {{ element }}
{% endfor %}
{% endif %}

Research this topic for world building purposes.""",
        "required_variables": ["topic", "world_type"],
        "optional_variables": ["era", "culture", "specific_elements"],
        "variable_defaults": {"world_type": "fantasy"},
        "output_format": "markdown",
        "license": "Apache-2.0",
        "author": "BF Agent Team",
        "compatibility": "No special requirements",
        "allowed_tools": ["WebSearch", "Read"],
        "agent_class": "apps.bfagent.agents.ResearchAgent",
        "max_tokens": 2500,
        "temperature": 0.6,
    },
    
    # =========================================================================
    # SUMMARY GENERATION SKILL
    # =========================================================================
    {
        "template_key": "research-summary-skill",
        "name": "Research Summary Skill",
        "category": "analysis",
        "description": "Zusammenfassung von Recherche-Ergebnissen",
        "skill_description": (
            "Synthesizes and summarizes research findings. Use when user has multiple sources "
            "and needs a coherent summary, executive brief, or condensed report. Supports "
            "different summary lengths and formats."
        ),
        "system_prompt": """You are a research synthesis specialist.

Your role:
- Synthesize information from multiple sources
- Create coherent summaries
- Identify key themes and patterns
- Highlight contradictions or gaps

Summary Types:
- Executive: 1-2 paragraphs, key points only
- Standard: 1-2 pages, main findings
- Detailed: Comprehensive with sections

Guidelines:
- Group related findings
- Note consensus vs. disagreement
- Highlight strongest evidence
- Flag areas needing more research""",
        "user_prompt_template": """# Research Summary Request

## Sources/Findings
{{ sources }}

{% if summary_type %}
## Summary Type: {{ summary_type }}
{% endif %}

{% if focus %}
## Focus Areas: {{ focus }}
{% endif %}

{% if max_length %}
## Maximum Length: {{ max_length }} words
{% endif %}

Synthesize these findings into a coherent summary.""",
        "required_variables": ["sources"],
        "optional_variables": ["summary_type", "focus", "max_length"],
        "variable_defaults": {"summary_type": "standard", "max_length": 500},
        "output_format": "markdown",
        "license": "Apache-2.0",
        "author": "BF Agent Team",
        "compatibility": "No special requirements",
        "allowed_tools": [],
        "agent_class": "apps.bfagent.agents.ResearchAgent",
        "max_tokens": 2000,
        "temperature": 0.4,
    },
]


class Command(BaseCommand):
    help = "Create research domain skills"
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Overwrite existing skills",
        )
    
    def handle(self, *args, **options):
        force = options.get("force", False)
        
        self.stdout.write("\n🔬 Seeding Research Domain Skills\n")
        self.stdout.write("-" * 50)
        
        created = 0
        updated = 0
        skipped = 0
        
        for skill_data in RESEARCH_SKILLS:
            template_key = skill_data["template_key"]
            
            existing = PromptTemplate.objects.filter(
                template_key=template_key
            ).first()
            
            if existing and not force:
                self.stdout.write(f"  ⏭️  {template_key}")
                skipped += 1
                continue
            
            # Prepare data
            data = {
                "name": skill_data["name"],
                "category": skill_data["category"],
                "description": skill_data.get("description", ""),
                "skill_description": skill_data["skill_description"],
                "system_prompt": skill_data["system_prompt"],
                "user_prompt_template": skill_data["user_prompt_template"],
                "required_variables": skill_data.get("required_variables", []),
                "optional_variables": skill_data.get("optional_variables", []),
                "variable_defaults": skill_data.get("variable_defaults", {}),
                "output_format": skill_data.get("output_format", "text"),
                "output_schema": skill_data.get("output_schema", {}),
                "license": skill_data.get("license", "Apache-2.0"),
                "author": skill_data.get("author", "BF Agent Team"),
                "compatibility": skill_data.get("compatibility", ""),
                "allowed_tools": skill_data.get("allowed_tools", []),
                "references": skill_data.get("references", {}),
                "agent_class": skill_data.get("agent_class", ""),
                "max_tokens": skill_data.get("max_tokens", 1000),
                "temperature": skill_data.get("temperature", 0.5),
                "is_active": True,
                "version": "1.0",
            }
            
            if existing:
                for key, value in data.items():
                    setattr(existing, key, value)
                existing.save()
                self.stdout.write(self.style.WARNING(f"  🔄 {template_key}"))
                updated += 1
            else:
                PromptTemplate.objects.create(template_key=template_key, **data)
                self.stdout.write(self.style.SUCCESS(f"  ✅ {template_key}"))
                created += 1
        
        self.stdout.write("\n" + "-" * 50)
        self.stdout.write(f"Created: {created}, Updated: {updated}, Skipped: {skipped}")
        self.stdout.write(self.style.SUCCESS("\n✅ Research Skills Ready!\n"))
        
        # Show summary
        self.stdout.write("Skills created:")
        self.stdout.write("  - web-search-skill: Quick web search")
        self.stdout.write("  - deep-dive-research-skill: Comprehensive research")
        self.stdout.write("  - fact-check-skill: Claim verification")
        self.stdout.write("  - academic-research-skill: Scholarly sources")
        self.stdout.write("  - exschutz-research-skill: ATEX/BetrSichV")
        self.stdout.write("  - worldbuilding-research-skill: Fiction world building")
        self.stdout.write("  - research-summary-skill: Synthesize findings\n")
