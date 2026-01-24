# -*- coding: utf-8 -*-
"""
SkillMatcher Service - Auto-Routing für Skills.

Gemäß AgentSkills.io Spezifikation:
- Matching basierend auf skill_description Keywords
- Progressive Disclosure (Metadata → Instructions → Resources)
- Agent-Binding für Ausführung

Usage:
    from apps.bfagent.services.skill_matcher import SkillMatcher
    
    matcher = SkillMatcher()
    skill = matcher.match("recherchiere AI Trends 2024")
    result = matcher.execute(skill, {"query": "AI Trends 2024"})
"""
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from django.db.models import Q

logger = logging.getLogger(__name__)


@dataclass
class SkillMatch:
    """Ergebnis eines Skill-Matchings."""
    skill: Any  # PromptTemplate
    score: float
    matched_keywords: List[str]
    
    def __str__(self):
        return f"{self.skill.name} (Score: {self.score:.2f})"


class SkillMatcher:
    """
    Service für Auto-Routing von User-Input zu passenden Skills.
    
    Features:
    - Keyword-basiertes Matching auf skill_description
    - Scoring nach Anzahl der Matches
    - Agent-Binding für Ausführung
    - Export als AgentSkills.io Format
    """
    
    def __init__(self):
        self._cache = {}
    
    def match(
        self, 
        user_input: str, 
        category: Optional[str] = None,
        min_score: float = 0.3,
    ) -> Optional[SkillMatch]:
        """
        Findet den besten Skill für einen User-Input.
        
        Args:
            user_input: User-Anfrage
            category: Optional Filter auf Kategorie
            min_score: Minimaler Score für Match
            
        Returns:
            SkillMatch oder None
        """
        matches = self.find_matches(user_input, category)
        
        if not matches:
            return None
        
        best = max(matches, key=lambda m: m.score)
        
        if best.score < min_score:
            logger.info(f"Best match {best.skill.name} below threshold: {best.score} < {min_score}")
            return None
        
        return best
    
    def find_matches(
        self, 
        user_input: str, 
        category: Optional[str] = None,
    ) -> List[SkillMatch]:
        """
        Findet alle passenden Skills für einen User-Input.
        
        Args:
            user_input: User-Anfrage
            category: Optional Filter auf Kategorie
            
        Returns:
            Liste von SkillMatch, sortiert nach Score
        """
        from apps.bfagent.models import PromptTemplate
        
        # Get active skills with skill_description
        queryset = PromptTemplate.objects.filter(
            is_active=True,
        ).exclude(
            skill_description=""
        )
        
        if category:
            queryset = queryset.filter(category=category)
        
        matches = []
        user_words = set(self._tokenize(user_input.lower()))
        
        for skill in queryset:
            score, keywords = self._calculate_score(user_words, skill)
            if score > 0:
                matches.append(SkillMatch(
                    skill=skill,
                    score=score,
                    matched_keywords=keywords,
                ))
        
        return sorted(matches, key=lambda m: m.score, reverse=True)
    
    def execute(
        self, 
        skill: Any,  # PromptTemplate
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Führt einen Skill aus.
        
        Args:
            skill: PromptTemplate-Instanz
            context: Variablen für Template-Rendering
            
        Returns:
            Ergebnis der Ausführung
        """
        from apps.bfagent.services.prompt_factory import PromptFactory
        from apps.bfagent.services.llm_agent import LLMAgent
        
        factory = PromptFactory()
        llm = LLMAgent()
        
        # Build prompt
        prompt = factory.build(skill.template_key, context)
        
        # Execute with LLM
        response = llm.generate(
            prompt['full'],
            model_id=skill.preferred_llm_id if skill.preferred_llm_id else None,
            max_tokens=skill.max_tokens,
            temperature=skill.temperature,
        )
        
        # Track execution
        from apps.bfagent.services.prompt_service import PromptTemplateService
        PromptTemplateService().record_execution(
            skill,
            success=response.success,
            tokens_used=response.usage.get('total', 0) if response.usage else 0,
            cost=response.cost_estimate,
        )
        
        return {
            'success': response.success,
            'content': response.content,
            'skill': skill.name,
            'model_used': response.model_used,
        }
    
    def get_agent_for_skill(self, skill: Any) -> Optional[Any]:
        """
        Lädt den Agent für einen Skill.
        
        Args:
            skill: PromptTemplate-Instanz
            
        Returns:
            Agent-Instanz oder None
        """
        if not skill.agent_class:
            return None
        
        try:
            # Dynamic import
            parts = skill.agent_class.rsplit('.', 1)
            if len(parts) != 2:
                return None
            
            module_path, class_name = parts
            import importlib
            module = importlib.import_module(module_path)
            agent_class = getattr(module, class_name)
            
            return agent_class()
        except Exception as e:
            logger.error(f"Failed to load agent {skill.agent_class}: {e}")
            return None
    
    def export_skill(self, skill: Any, output_dir: Optional[str] = None) -> str:
        """
        Exportiert einen Skill als SKILL.md.
        
        Args:
            skill: PromptTemplate-Instanz
            output_dir: Optional Ausgabe-Verzeichnis
            
        Returns:
            Pfad zur SKILL.md oder String-Content
        """
        content = skill.to_agentskills_format()
        
        if output_dir:
            import os
            skill_dir = os.path.join(output_dir, skill.template_key)
            os.makedirs(skill_dir, exist_ok=True)
            
            skill_path = os.path.join(skill_dir, 'SKILL.md')
            with open(skill_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Exported skill to: {skill_path}")
            return skill_path
        
        return content
    
    def export_all_skills(self, output_dir: str) -> List[str]:
        """
        Exportiert alle aktiven Skills.
        
        Args:
            output_dir: Ausgabe-Verzeichnis
            
        Returns:
            Liste der erstellten Pfade
        """
        from apps.bfagent.models import PromptTemplate
        
        skills = PromptTemplate.objects.filter(
            is_active=True,
        ).exclude(skill_description="")
        
        paths = []
        for skill in skills:
            path = self.export_skill(skill, output_dir)
            paths.append(path)
        
        logger.info(f"Exported {len(paths)} skills to {output_dir}")
        return paths
    
    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenisiert Text in Wörter."""
        # Remove punctuation and split
        words = re.findall(r'\b\w+\b', text.lower())
        return [w for w in words if len(w) > 2]
    
    def _calculate_score(
        self, 
        user_words: set, 
        skill: Any,
    ) -> Tuple[float, List[str]]:
        """
        Berechnet Score basierend auf Keyword-Matches.
        
        Args:
            user_words: Tokenisierte User-Eingabe
            skill: PromptTemplate
            
        Returns:
            (score, matched_keywords)
        """
        description = skill.skill_description or skill.description or ""
        skill_words = set(self._tokenize(description.lower()))
        
        # Also consider name and tags
        skill_words.update(self._tokenize(skill.name.lower()))
        if skill.tags:
            for tag in skill.tags:
                skill_words.update(self._tokenize(str(tag).lower()))
        
        # Find matches
        matched = user_words.intersection(skill_words)
        
        if not matched:
            return 0.0, []
        
        # Score = matched / total possible
        score = len(matched) / max(len(user_words), 1)
        
        return score, list(matched)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def match_skill(user_input: str) -> Optional[SkillMatch]:
    """Convenience-Funktion für Skill-Matching."""
    matcher = SkillMatcher()
    return matcher.match(user_input)


def execute_skill(skill_key: str, context: Dict) -> Dict:
    """Convenience-Funktion für Skill-Ausführung."""
    from apps.bfagent.models import PromptTemplate
    
    skill = PromptTemplate.objects.filter(
        template_key=skill_key,
        is_active=True,
    ).first()
    
    if not skill:
        return {'success': False, 'error': f'Skill not found: {skill_key}'}
    
    matcher = SkillMatcher()
    return matcher.execute(skill, context)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "SkillMatcher",
    "SkillMatch",
    "match_skill",
    "execute_skill",
]
