#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Management Command: seed_sample_skills

Erstellt Beispiel-Skills gemäß AgentSkills.io Standard.

Usage:
    python manage.py seed_sample_skills
    python manage.py seed_sample_skills --force  # Überschreibt existierende

Spec: https://agentskills.io/specification
Anthropic Skills: https://github.com/anthropics/skills
"""
from django.core.management.base import BaseCommand
from apps.bfagent.models import PromptTemplate


SAMPLE_SKILLS = [
    {
        "template_key": "research-skill",
        "name": "Research Skill",
        "category": "analysis",
        "description": "Web-Recherche und Fakten-Analyse",
        "skill_description": (
            "Performs web research, fact-checking, and information synthesis. "
            "Use when the user asks to research a topic, verify facts, find sources, "
            "or gather information from the web. Supports quick search, deep research, "
            "and fact verification with source citations."
        ),
        "system_prompt": """You are an expert research assistant with access to web search capabilities.

Your role:
- Find accurate, up-to-date information
- Verify facts with multiple sources
- Provide clear citations
- Synthesize findings into actionable insights

Guidelines:
- Always cite sources with URLs
- Distinguish between facts and opinions
- Note when information may be outdated
- Be transparent about limitations""",
        "user_prompt_template": """# Research Request

## Query
{{ query }}

{% if depth %}
## Research Depth: {{ depth }}
{% endif %}

{% if focus_areas %}
## Focus Areas
{% for area in focus_areas %}
- {{ area }}
{% endfor %}
{% endif %}

## Instructions
1. Search for relevant information
2. Verify key facts with multiple sources
3. Synthesize findings
4. Provide citations

## Output Format
Provide a structured research report with:
- Executive Summary
- Key Findings
- Sources (with URLs)
- Confidence Level""",
        "required_variables": ["query"],
        "optional_variables": ["depth", "focus_areas"],
        "variable_defaults": {"depth": "standard"},
        "output_format": "markdown",
        "license": "Apache-2.0",
        "author": "BF Agent Team",
        "compatibility": "Requires internet access for web search",
        "allowed_tools": ["WebSearch", "Read"],
        "agent_class": "apps.bfagent.agents.ResearchAgent",
        "max_tokens": 2000,
        "temperature": 0.3,
    },
    {
        "template_key": "writing-analysis-skill",
        "name": "Writing Analysis Skill",
        "category": "analysis",
        "description": "Analyse von Texten und Schreibstil",
        "skill_description": (
            "Analyzes text for style, structure, and quality. Use when the user wants "
            "feedback on their writing, needs style analysis, character extraction, "
            "or wants to understand the qualities of a text. Supports fiction, "
            "non-fiction, and technical writing."
        ),
        "system_prompt": """You are an expert literary analyst and writing coach.

Your role:
- Analyze writing style and structure
- Identify strengths and areas for improvement
- Extract key elements (characters, themes, plot points)
- Provide constructive feedback

Guidelines:
- Be specific with examples from the text
- Balance positive feedback with suggestions
- Consider the intended audience and genre
- Respect the author's voice""",
        "user_prompt_template": """# Writing Analysis Request

## Text to Analyze
{{ text }}

{% if genre %}
## Genre: {{ genre }}
{% endif %}

{% if analysis_type %}
## Analysis Type: {{ analysis_type }}
{% endif %}

## Instructions
Analyze the text for:
1. Style and voice
2. Structure and pacing
3. Character development (if fiction)
4. Clarity and readability
5. Areas for improvement

## Output Format
Provide structured analysis with:
- Overall Assessment
- Style Analysis
- Structural Analysis
- Specific Suggestions
- Strengths to Maintain""",
        "required_variables": ["text"],
        "optional_variables": ["genre", "analysis_type"],
        "variable_defaults": {"analysis_type": "comprehensive"},
        "output_format": "markdown",
        "license": "Apache-2.0",
        "author": "BF Agent Team",
        "compatibility": "No special requirements",
        "allowed_tools": ["Read"],
        "agent_class": "apps.bfagent.agents.WritingAgent",
        "max_tokens": 1500,
        "temperature": 0.5,
    },
    {
        "template_key": "code-quality-skill",
        "name": "Code Quality Skill",
        "category": "analysis",
        "description": "Code-Analyse und Qualitätsbewertung",
        "skill_description": (
            "Analyzes Python/Django code for quality, complexity, and best practices. "
            "Use when reviewing code, checking for issues, measuring complexity, "
            "or ensuring coding standards. Detects code smells, dead code, and "
            "documentation gaps."
        ),
        "system_prompt": """You are an expert code reviewer specializing in Python and Django.

Your role:
- Analyze code quality and structure
- Identify potential bugs and code smells
- Check adherence to best practices
- Suggest improvements

Guidelines:
- Follow PEP 8 and Django conventions
- Consider maintainability and readability
- Identify security concerns
- Balance perfectionism with pragmatism""",
        "user_prompt_template": """# Code Quality Review

## Code
```{{ language|default('python') }}
{{ code }}
```

{% if file_path %}
## File: {{ file_path }}
{% endif %}

{% if focus %}
## Focus Areas: {{ focus }}
{% endif %}

## Instructions
Analyze the code for:
1. Code quality and style
2. Complexity (cyclomatic, cognitive)
3. Potential bugs or issues
4. Documentation coverage
5. Best practice violations

## Output Format
Provide structured review with:
- Quality Score (0-100)
- Issues Found (by severity)
- Suggestions for Improvement
- Positive Aspects""",
        "required_variables": ["code"],
        "optional_variables": ["file_path", "language", "focus"],
        "variable_defaults": {"language": "python"},
        "output_format": "json",
        "output_schema": {
            "type": "object",
            "properties": {
                "quality_score": {"type": "integer", "minimum": 0, "maximum": 100},
                "issues": {"type": "array"},
                "suggestions": {"type": "array"},
                "summary": {"type": "string"},
            },
        },
        "license": "Apache-2.0",
        "author": "BF Agent Team",
        "compatibility": "Python 3.8+",
        "allowed_tools": ["Read", "Bash(python:*)"],
        "agent_class": "apps.bfagent.agents.CodeQualityAgent",
        "max_tokens": 1500,
        "temperature": 0.2,
    },
]


class Command(BaseCommand):
    help = "Create sample skills based on AgentSkills.io specification"
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Overwrite existing skills",
        )
    
    def handle(self, *args, **options):
        force = options.get("force", False)
        
        self.stdout.write("\n🎯 Seeding Sample Skills\n")
        self.stdout.write("-" * 50)
        
        created = 0
        updated = 0
        skipped = 0
        
        for skill_data in SAMPLE_SKILLS:
            template_key = skill_data["template_key"]
            
            existing = PromptTemplate.objects.filter(
                template_key=template_key
            ).first()
            
            if existing and not force:
                self.stdout.write(f"  ⏭️  {template_key} (exists, use --force)")
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
                "license": skill_data.get("license", "Proprietary"),
                "author": skill_data.get("author", ""),
                "compatibility": skill_data.get("compatibility", ""),
                "allowed_tools": skill_data.get("allowed_tools", []),
                "agent_class": skill_data.get("agent_class", ""),
                "max_tokens": skill_data.get("max_tokens", 500),
                "temperature": skill_data.get("temperature", 0.7),
                "is_active": True,
                "version": "1.0",
            }
            
            if existing:
                for key, value in data.items():
                    setattr(existing, key, value)
                existing.save()
                self.stdout.write(self.style.WARNING(f"  🔄 {template_key} (updated)"))
                updated += 1
            else:
                PromptTemplate.objects.create(template_key=template_key, **data)
                self.stdout.write(self.style.SUCCESS(f"  ✅ {template_key} (created)"))
                created += 1
        
        self.stdout.write("\n" + "-" * 50)
        self.stdout.write(f"Created: {created}, Updated: {updated}, Skipped: {skipped}")
        self.stdout.write(self.style.SUCCESS("\n✅ Done!\n"))
        
        # Show next steps
        self.stdout.write("Next steps:")
        self.stdout.write("  python manage.py skill_export --list")
        self.stdout.write("  python manage.py skill_export ./skills/")
        self.stdout.write("  python manage.py skill_export --validate research-skill\n")
