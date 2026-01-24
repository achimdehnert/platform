"""
AI-Powered Context Extraction Service

Extracts descriptions for characters and locations from manuscript context
by analyzing text passages where they are mentioned.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExtractedContext:
    """Context extracted for an entity (character or location)"""
    name: str
    description: str = ""
    features: List[str] = None
    mood: str = ""
    context_snippets: List[str] = None
    
    def __post_init__(self):
        self.features = self.features or []
        self.context_snippets = self.context_snippets or []


class ContextExtractor:
    """
    Extracts descriptive context for characters and locations from manuscript text.
    Can work in two modes:
    1. Rule-based: Fast, no AI, extracts surrounding text
    2. AI-powered: Uses LLM to generate descriptions from context
    """
    
    # Context window size (characters before/after mention)
    CONTEXT_WINDOW = 500
    
    # Patterns for description indicators
    DESCRIPTION_INDICATORS = [
        r'(?:war|ist|wirkt|sieht aus|erscheint|zeigt sich)',
        r'(?:befand sich|lag|stand|war gelegen)',
        r'(?:dunkel|hell|groß|klein|alt|neu|kalt|warm)',
        r'(?:fühlte sich|roch|klang)',
    ]
    
    def __init__(self, manuscript_text: str, use_ai: bool = False):
        """
        Initialize the context extractor.
        
        Args:
            manuscript_text: Full manuscript text to analyze
            use_ai: Whether to use AI for description generation
        """
        self.text = manuscript_text
        self.use_ai = use_ai
        self._llm_service = None
    
    def extract_location_context(self, location_name: str) -> ExtractedContext:
        """
        Extract descriptive context for a location.
        
        Args:
            location_name: Name of the location to find context for
            
        Returns:
            ExtractedContext with description and features
        """
        # Find all mentions of this location
        snippets = self._find_context_snippets(location_name)
        
        if not snippets:
            return ExtractedContext(name=location_name)
        
        if self.use_ai:
            return self._ai_extract_location(location_name, snippets)
        else:
            return self._rule_based_extract_location(location_name, snippets)
    
    def extract_character_context(self, character_name: str) -> ExtractedContext:
        """
        Extract descriptive context for a character.
        
        Args:
            character_name: Name of the character to find context for
            
        Returns:
            ExtractedContext with description and features
        """
        # Find all mentions of this character
        snippets = self._find_context_snippets(character_name)
        
        if not snippets:
            return ExtractedContext(name=character_name)
        
        if self.use_ai:
            return self._ai_extract_character(character_name, snippets)
        else:
            return self._rule_based_extract_character(character_name, snippets)
    
    def _find_context_snippets(self, entity_name: str) -> List[str]:
        """Find all text snippets where the entity is mentioned"""
        snippets = []
        
        # Escape special regex characters in entity name
        escaped_name = re.escape(entity_name)
        
        # Find all mentions
        pattern = re.compile(
            rf'(.{{0,{self.CONTEXT_WINDOW}}})({escaped_name})(.{{0,{self.CONTEXT_WINDOW}}})',
            re.IGNORECASE | re.DOTALL
        )
        
        for match in pattern.finditer(self.text):
            before, name, after = match.groups()
            snippet = f"{before}{name}{after}".strip()
            # Clean up the snippet
            snippet = re.sub(r'\s+', ' ', snippet)
            if snippet and len(snippet) > 20:
                snippets.append(snippet)
        
        # Deduplicate similar snippets
        unique_snippets = []
        for s in snippets:
            is_duplicate = False
            for existing in unique_snippets:
                if s in existing or existing in s:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_snippets.append(s)
        
        return unique_snippets[:10]  # Limit to 10 snippets
    
    def _rule_based_extract_location(self, name: str, snippets: List[str]) -> ExtractedContext:
        """Extract location description using rule-based analysis"""
        description_parts = []
        features = []
        mood = ""
        
        for snippet in snippets:
            # Look for descriptive sentences
            sentences = re.split(r'[.!?]', snippet)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence or name.lower() not in sentence.lower():
                    continue
                
                # Check if sentence contains description indicators
                for indicator in self.DESCRIPTION_INDICATORS:
                    if re.search(indicator, sentence, re.IGNORECASE):
                        # Clean and add to description
                        clean_sent = sentence.strip()
                        if clean_sent and clean_sent not in description_parts:
                            description_parts.append(clean_sent)
                        break
                
                # Extract adjectives as features
                adj_pattern = r'(?:der|die|das|eine?|einem?|einen)\s+(\w+e[rsnm]?)\s+' + re.escape(name)
                adj_matches = re.findall(adj_pattern, sentence, re.IGNORECASE)
                for adj in adj_matches:
                    if adj.lower() not in [f.lower() for f in features]:
                        features.append(adj)
        
        # Build description
        if description_parts:
            description = ' '.join(description_parts[:3])  # Take top 3 sentences
        else:
            # Fallback: use first snippet
            description = f"Ort im Manuskript erwähnt in {len(snippets)} Szenen."
        
        return ExtractedContext(
            name=name,
            description=description,
            features=features[:5],
            mood=mood,
            context_snippets=snippets[:3]
        )
    
    def _rule_based_extract_character(self, name: str, snippets: List[str]) -> ExtractedContext:
        """Extract character description using rule-based analysis"""
        description_parts = []
        features = []
        
        # Common character description patterns
        char_patterns = [
            rf'{re.escape(name)}\s+(?:war|ist|wirkte?)\s+(.{{10,100}}?)[.,]',
            rf'(?:der|die)\s+(\w+e?)\s+{re.escape(name)}',
            rf'{re.escape(name)}(?:s)?\s+(\w+(?:e[rsnm]?)?\s+(?:Augen|Haare?|Gesicht|Stimme|Hände?))',
            rf'{re.escape(name)}\s+(?:trug|hatte)\s+(.{{10,80}}?)[.,]',
        ]
        
        for snippet in snippets:
            for pattern in char_patterns:
                matches = re.findall(pattern, snippet, re.IGNORECASE)
                for match in matches:
                    clean = match.strip()
                    if clean and len(clean) > 5:
                        if clean not in description_parts:
                            description_parts.append(clean)
        
        # Look for traits (adjectives before name)
        for snippet in snippets:
            trait_pattern = rf'(?:der|die|eine?)\s+(\w+e[rsnm]?)\s+{re.escape(name)}'
            trait_matches = re.findall(trait_pattern, snippet, re.IGNORECASE)
            for trait in trait_matches:
                if trait.lower() not in [f.lower() for f in features]:
                    features.append(trait)
        
        # Build description
        if description_parts:
            description = '. '.join(description_parts[:4])
        else:
            description = f"Charakter erscheint in {len(snippets)} Textpassagen."
        
        return ExtractedContext(
            name=name,
            description=description,
            features=features[:5],
            context_snippets=snippets[:3]
        )
    
    def _ai_extract_location(self, name: str, snippets: List[str]) -> ExtractedContext:
        """Use AI to extract location description"""
        if not self._init_llm():
            return self._rule_based_extract_location(name, snippets)
        
        prompt = f"""Analysiere die folgenden Textpassagen und erstelle eine Beschreibung für den Ort "{name}".

Textpassagen:
{chr(10).join(f'- {s[:300]}...' for s in snippets[:5])}

Erstelle eine prägnante Beschreibung (2-3 Sätze) die Folgendes enthält:
- Atmosphäre und Stimmung des Ortes
- Physische Merkmale (falls erwähnt)
- Bedeutung für die Geschichte

Antwort NUR mit der Beschreibung, keine Erklärungen."""

        try:
            response = self._llm_service.generate(prompt, max_tokens=200)
            description = response.strip()
            
            # Also extract features with rule-based
            rule_based = self._rule_based_extract_location(name, snippets)
            
            return ExtractedContext(
                name=name,
                description=description,
                features=rule_based.features,
                context_snippets=snippets[:3]
            )
        except Exception as e:
            logger.warning(f"AI extraction failed for location {name}: {e}")
            return self._rule_based_extract_location(name, snippets)
    
    def _ai_extract_character(self, name: str, snippets: List[str]) -> ExtractedContext:
        """Use AI to extract character description"""
        if not self._init_llm():
            return self._rule_based_extract_character(name, snippets)
        
        prompt = f"""Analysiere die folgenden Textpassagen und erstelle eine Charakterbeschreibung für "{name}".

Textpassagen:
{chr(10).join(f'- {s[:300]}...' for s in snippets[:5])}

Erstelle eine prägnante Beschreibung (2-3 Sätze) die Folgendes enthält:
- Persönlichkeit und Charakterzüge
- Äußere Erscheinung (falls erwähnt)
- Rolle in der Geschichte
- Beziehungen zu anderen Charakteren (falls erwähnt)

Antwort NUR mit der Beschreibung, keine Erklärungen."""

        try:
            response = self._llm_service.generate(prompt, max_tokens=250)
            description = response.strip()
            
            # Also extract features with rule-based
            rule_based = self._rule_based_extract_character(name, snippets)
            
            return ExtractedContext(
                name=name,
                description=description,
                features=rule_based.features,
                context_snippets=snippets[:3]
            )
        except Exception as e:
            logger.warning(f"AI extraction failed for character {name}: {e}")
            return self._rule_based_extract_character(name, snippets)
    
    def _init_llm(self) -> bool:
        """Initialize LLM service if needed"""
        if self._llm_service is not None:
            return True
        
        try:
            from apps.bfagent.services.llm_service import LLMService
            self._llm_service = LLMService()
            return True
        except Exception as e:
            logger.warning(f"Could not initialize LLM service: {e}")
            return False
    
    def extract_all_locations(self, location_names: List[str]) -> Dict[str, ExtractedContext]:
        """Extract context for all locations"""
        results = {}
        for name in location_names:
            results[name] = self.extract_location_context(name)
        return results
    
    def extract_all_characters(self, character_names: List[str]) -> Dict[str, ExtractedContext]:
        """Extract context for all characters"""
        results = {}
        for name in character_names:
            results[name] = self.extract_character_context(name)
        return results
