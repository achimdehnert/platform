"""
Outline Recommender Service

LLM-powered recommendation of optimal outline templates based on project metadata.

Features:
- Analyzes project metadata (genre, themes, POV, word count)
- Matches against OutlineTemplate library
- Uses LLM to rank and explain recommendations
- Stores recommendations for analytics

Usage:
    from apps.writing_hub.services.outline_recommender_service import OutlineRecommenderService
    
    service = OutlineRecommenderService()
    recommendations = await service.recommend_outline(import_result)

Author: BF Agent Team
Date: 2026-01-22
"""

import json
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OutlineRecommendationResult:
    """Result of outline recommendation"""
    template_code: str
    template_name: str
    match_score: float  # 0.0 - 1.0
    match_reason: str
    rank: int
    
    # Template details
    category: str
    acts_count: int
    beats_count: int
    example_books: str


RECOMMENDATION_PROMPT = """Du bist ein Experte für Buchstrukturen und Storytelling.

Analysiere dieses Buchprojekt und empfehle die TOP 3 passenden Outline-Templates:

PROJEKT-METADATEN:
- Titel: {title}
- Genre: {genre_primary} {genre_secondary}
- Themen: {themes}
- POV: {pov}
- Ziel-Wortanzahl: {target_word_count}
- Format: {format_type}
- Geplante Bände: {planned_books}
- Logline: {logline}
- Zentrale Frage: {central_question}

CHARAKTERE:
{characters_summary}

VERFÜGBARE TEMPLATES:
{templates_list}

Bewerte jedes Template nach:
1. Genre-Passung (30%)
2. Themen-Passung (25%)
3. Struktur-Eignung für POV (20%)
4. Längen-Eignung (15%)
5. Format-Eignung (Serie vs Standalone) (10%)

Antworte NUR als JSON:
{{
  "recommendations": [
    {{
      "template_code": "code",
      "match_score": 0.0-1.0,
      "match_reason": "Ausführliche Begründung (2-3 Sätze)",
      "rank": 1
    }},
    {{
      "template_code": "code",
      "match_score": 0.0-1.0,
      "match_reason": "Ausführliche Begründung",
      "rank": 2
    }},
    {{
      "template_code": "code",
      "match_score": 0.0-1.0,
      "match_reason": "Ausführliche Begründung",
      "rank": 3
    }}
  ],
  "analysis": "Kurze Gesamt-Analyse der Story-Struktur-Anforderungen"
}}"""


class OutlineRecommenderService:
    """
    Service for recommending optimal outline templates.
    
    Uses LLM to analyze project metadata and match against template library.
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self._ensure_llm_client()
    
    def _ensure_llm_client(self):
        """Ensure LLM client is available"""
        if self.llm_client is None:
            try:
                from apps.bfagent.services.llm_client import get_llm_client
                self.llm_client = get_llm_client()
            except ImportError:
                logger.warning("LLM client not available")
                self.llm_client = None
    
    def _get_available_templates(self) -> List[Dict]:
        """Load available templates from database"""
        try:
            from apps.writing_hub.models_import_framework import OutlineTemplate
            
            templates = OutlineTemplate.objects.filter(is_active=True).select_related('category')
            
            result = []
            for t in templates:
                result.append({
                    'code': t.code,
                    'name': t.name,
                    'name_de': t.name_de,
                    'category': t.category.name if t.category else 'Uncategorized',
                    'description': t.description[:200],
                    'genre_tags': t.genre_tags,
                    'pov_tags': t.pov_tags,
                    'theme_tags': t.theme_tags,
                    'word_count_min': t.word_count_min,
                    'word_count_max': t.word_count_max,
                    'acts_count': t.get_acts_count(),
                    'beats_count': t.get_total_beats(),
                    'example_books': t.example_books,
                })
            
            return result
        except Exception as e:
            logger.warning(f"Could not load templates from DB: {e}")
            return self._get_default_templates()
    
    def _get_default_templates(self) -> List[Dict]:
        """Fallback templates if DB not available"""
        return [
            {
                'code': 'three_act',
                'name': 'Three-Act Structure',
                'name_de': 'Drei-Akt-Struktur',
                'category': 'Classic',
                'description': 'Klassische Hollywood-Struktur mit Setup, Confrontation, Resolution',
                'genre_tags': ['thriller', 'romance', 'fantasy', 'literary'],
                'pov_tags': ['first_person', 'third_limited', 'multiple'],
                'theme_tags': [],
                'word_count_min': 60000,
                'word_count_max': 150000,
                'acts_count': 3,
                'beats_count': 12,
                'example_books': 'Die meisten Hollywood-Filme, viele Thriller',
            },
            {
                'code': 'save_the_cat',
                'name': 'Save the Cat Beat Sheet',
                'name_de': 'Save the Cat Beatsheet',
                'category': 'Author Methods',
                'description': 'Blake Snyders 15-Beat-Struktur für emotionales Storytelling',
                'genre_tags': ['romance', 'thriller', 'comedy'],
                'pov_tags': ['first_person', 'third_limited'],
                'theme_tags': ['redemption', 'love', 'transformation'],
                'word_count_min': 70000,
                'word_count_max': 100000,
                'acts_count': 3,
                'beats_count': 15,
                'example_books': 'Legally Blonde, Miss Congeniality',
            },
            {
                'code': 'heroes_journey',
                'name': "Hero's Journey",
                'name_de': 'Heldenreise',
                'category': 'Classic',
                'description': 'Joseph Campbells mythologische 12-Stufen-Struktur',
                'genre_tags': ['fantasy', 'adventure', 'epic'],
                'pov_tags': ['third_limited', 'first_person'],
                'theme_tags': ['transformation', 'growth', 'destiny'],
                'word_count_min': 80000,
                'word_count_max': 200000,
                'acts_count': 3,
                'beats_count': 12,
                'example_books': 'Star Wars, Harry Potter, Der Herr der Ringe',
            },
            {
                'code': 'romance_arc',
                'name': 'Romance Arc (HEA)',
                'name_de': 'Romance-Bogen (HEA)',
                'category': 'Genre-Specific',
                'description': 'Struktur für Romance mit Meet-Cute, Konflikt, und Happy End',
                'genre_tags': ['romance', 'contemporary_romance', 'dark_romance'],
                'pov_tags': ['dual_pov', 'first_person'],
                'theme_tags': ['love', 'trust', 'healing'],
                'word_count_min': 50000,
                'word_count_max': 100000,
                'acts_count': 4,
                'beats_count': 16,
                'example_books': 'The Hating Game, Beach Read',
            },
            {
                'code': 'seven_point',
                'name': 'Seven-Point Story Structure',
                'name_de': 'Sieben-Punkte-Struktur',
                'category': 'Author Methods',
                'description': 'Dan Wells\' kompakte Struktur: Hook, Plot Turn 1, Pinch 1, Midpoint, Pinch 2, Plot Turn 2, Resolution',
                'genre_tags': ['thriller', 'mystery', 'horror'],
                'pov_tags': ['first_person', 'third_limited'],
                'theme_tags': ['mystery', 'revelation', 'discovery'],
                'word_count_min': 60000,
                'word_count_max': 120000,
                'acts_count': 3,
                'beats_count': 7,
                'example_books': 'Thriller und Mystery-Romane',
            },
        ]
    
    def _format_templates_for_prompt(self, templates: List[Dict]) -> str:
        """Format templates for LLM prompt"""
        lines = []
        for t in templates:
            lines.append(f"""
- **{t['code']}**: {t['name']}
  Kategorie: {t['category']}
  Beschreibung: {t['description']}
  Genre-Tags: {', '.join(t['genre_tags'])}
  POV-Tags: {', '.join(t['pov_tags'])}
  Akte: {t['acts_count']}, Beats: {t['beats_count']}
  Wortanzahl: {t['word_count_min']:,} - {t['word_count_max']:,}
""")
        return "\n".join(lines)
    
    def _format_characters_summary(self, characters: List) -> str:
        """Format characters for prompt"""
        if not characters:
            return "Keine Charaktere extrahiert"
        
        lines = []
        for c in characters[:5]:  # Top 5 characters
            name = c.name if hasattr(c, 'name') else c.get('name', 'Unknown')
            role = c.role if hasattr(c, 'role') else c.get('role', 'unknown')
            arc = c.arc if hasattr(c, 'arc') else c.get('arc', '')
            lines.append(f"- {name} ({role}): {arc[:100] if arc else 'Kein Arc definiert'}")
        
        return "\n".join(lines)
    
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM"""
        if self.llm_client is None:
            raise ValueError("LLM client not available")
        
        response = await self.llm_client.generate(
            prompt=prompt,
            system_prompt="Du bist ein Experte für Buchstrukturen und Storytelling.",
            temperature=0.3,
            max_tokens=2000
        )
        return response
    
    def _parse_json_response(self, response: str) -> dict:
        """Parse JSON from LLM response"""
        import re
        
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response
        
        return json.loads(json_str.strip())
    
    async def recommend_outline(
        self, 
        import_result=None,
        metadata: Dict = None,
        characters: List = None,
        top_n: int = 3
    ) -> List[OutlineRecommendationResult]:
        """
        Recommend outline templates based on project data.
        
        Args:
            import_result: ImportResultV2 from smart import (preferred)
            metadata: Alternative: dict with project metadata
            characters: Alternative: list of characters
            top_n: Number of recommendations to return
        
        Returns:
            List of OutlineRecommendationResult sorted by match_score
        """
        # Extract data from import_result or use provided
        if import_result:
            meta = import_result.metadata
            chars = import_result.characters
            
            metadata_dict = {
                'title': meta.title,
                'genre_primary': meta.genre_primary,
                'genre_secondary': ', '.join(meta.genre_secondary),
                'themes': ', '.join(meta.themes),
                'pov': meta.pov or 'Nicht angegeben',
                'target_word_count': meta.target_word_count,
                'format_type': meta.format_type,
                'planned_books': meta.planned_books,
                'logline': meta.logline or 'Nicht vorhanden',
                'central_question': meta.central_question or 'Nicht definiert',
            }
        else:
            metadata_dict = metadata or {}
            chars = characters or []
        
        # Get templates
        templates = self._get_available_templates()
        
        if not templates:
            logger.error("No outline templates available")
            return []
        
        # Build prompt
        prompt = RECOMMENDATION_PROMPT.format(
            **metadata_dict,
            characters_summary=self._format_characters_summary(chars),
            templates_list=self._format_templates_for_prompt(templates)
        )
        
        # Get LLM recommendation
        try:
            response = await self._call_llm(prompt)
            data = self._parse_json_response(response)
        except Exception as e:
            logger.error(f"LLM recommendation failed: {e}")
            # Fallback to simple matching
            return self._simple_match(metadata_dict, templates, top_n)
        
        # Build results
        results = []
        template_map = {t['code']: t for t in templates}
        
        for rec in data.get('recommendations', [])[:top_n]:
            code = rec.get('template_code')
            if code in template_map:
                t = template_map[code]
                results.append(OutlineRecommendationResult(
                    template_code=code,
                    template_name=t['name'],
                    match_score=float(rec.get('match_score', 0.5)),
                    match_reason=rec.get('match_reason', ''),
                    rank=rec.get('rank', len(results) + 1),
                    category=t['category'],
                    acts_count=t['acts_count'],
                    beats_count=t['beats_count'],
                    example_books=t['example_books'],
                ))
        
        return sorted(results, key=lambda x: x.rank)
    
    def _simple_match(
        self, 
        metadata: Dict, 
        templates: List[Dict], 
        top_n: int
    ) -> List[OutlineRecommendationResult]:
        """Simple rule-based matching as fallback"""
        genre = metadata.get('genre_primary', '').lower()
        word_count = metadata.get('target_word_count', 80000)
        
        scored = []
        for t in templates:
            score = 0.5  # Base score
            
            # Genre match
            if any(genre in tag.lower() for tag in t['genre_tags']):
                score += 0.3
            
            # Word count match
            if t['word_count_min'] <= word_count <= t['word_count_max']:
                score += 0.2
            
            scored.append((t, min(score, 1.0)))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for i, (t, score) in enumerate(scored[:top_n]):
            results.append(OutlineRecommendationResult(
                template_code=t['code'],
                template_name=t['name'],
                match_score=score,
                match_reason=f"Genre- und Längen-basierte Empfehlung",
                rank=i + 1,
                category=t['category'],
                acts_count=t['acts_count'],
                beats_count=t['beats_count'],
                example_books=t['example_books'],
            ))
        
        return results
    
    def recommend_outline_sync(
        self, 
        import_result=None,
        metadata: Dict = None,
        characters: List = None,
        top_n: int = 3
    ) -> List[OutlineRecommendationResult]:
        """Synchronous wrapper"""
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.recommend_outline(import_result, metadata, characters, top_n)
        )


# =============================================================================
# Convenience Functions
# =============================================================================

def recommend_outline_for_project(project) -> List[OutlineRecommendationResult]:
    """
    Recommend outline for existing BookProject.
    
    Usage:
        from apps.writing_hub.services.outline_recommender_service import recommend_outline_for_project
        recommendations = recommend_outline_for_project(project)
    """
    metadata = {
        'title': project.title,
        'genre_primary': project.genre,
        'genre_secondary': '',
        'themes': project.story_themes or '',
        'pov': '',
        'target_word_count': project.target_word_count,
        'format_type': 'series' if project.series else 'standalone',
        'planned_books': 1,
        'logline': project.tagline or '',
        'central_question': project.central_question or '',
    }
    
    service = OutlineRecommenderService()
    return service.recommend_outline_sync(metadata=metadata)
