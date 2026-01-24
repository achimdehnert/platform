"""
World Building Handlers - AI-Powered World Generation
======================================================

Handlers for generating and expanding worlds using LLMAgent.
Uses intelligent model routing for cost optimization.

Features:
- Multi-language support (de, en, es, fr, it, pt)
- Configurable output language via 'language' parameter
- Automatic system prompt translation

Created: 2026-01-15
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from django.conf import settings

from apps.bfagent.domains.book_writing.services.llm_service import LLMService

logger = logging.getLogger(__name__)

# Language configurations
LANGUAGE_CONFIG = {
    "de": {
        "name": "Deutsch",
        "system_prompt": "Du bist ein meisterhafter Weltenbauer, spezialisiert auf die Erschaffung reicher, detaillierter fiktiver Welten mit innerer Konsistenz. Antworte immer auf Deutsch.",
        "output_instruction": "Antworte auf Deutsch.",
    },
    "en": {
        "name": "English", 
        "system_prompt": "You are a master world-builder specializing in creating rich, detailed fictional worlds with internal consistency. Always respond in English.",
        "output_instruction": "Respond in English.",
    },
    "es": {
        "name": "Español",
        "system_prompt": "Eres un maestro constructor de mundos especializado en crear mundos ficticios ricos y detallados con consistencia interna. Siempre responde en español.",
        "output_instruction": "Responde en español.",
    },
    "fr": {
        "name": "Français",
        "system_prompt": "Tu es un maître bâtisseur de mondes spécialisé dans la création de mondes fictifs riches et détaillés avec une cohérence interne. Réponds toujours en français.",
        "output_instruction": "Réponds en français.",
    },
    "it": {
        "name": "Italiano",
        "system_prompt": "Sei un maestro costruttore di mondi specializzato nella creazione di mondi fittizi ricchi e dettagliati con coerenza interna. Rispondi sempre in italiano.",
        "output_instruction": "Rispondi in italiano.",
    },
    "pt": {
        "name": "Português",
        "system_prompt": "Você é um mestre construtor de mundos especializado em criar mundos fictícios ricos e detalhados com consistência interna. Sempre responda em português.",
        "output_instruction": "Responda em português.",
    },
}

def get_language_config(language: str) -> Dict[str, str]:
    """Get language configuration, defaulting to German."""
    return LANGUAGE_CONFIG.get(language, LANGUAGE_CONFIG["de"])


class WorldGeneratorHandler:
    """
    Generate complete world foundation using LLM.
    
    Input:
    - name: str (world name)
    - world_type: str (fantasy, scifi, historical, etc.)
    - genre: str (optional, story genre for context)
    - seed_idea: str (optional, initial concept)
    - language: str (de, en, es, fr, it, pt - default: de)
    
    Output:
    - description: str
    - setting_era: str
    - geography: str
    - climate: str
    - inhabitants: str
    - culture: str
    - technology_level: str
    - success: bool
    - usage: dict
    """
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate world foundation with LLM"""
        name = data.get("name", "").strip()
        world_type = data.get("world_type", "fantasy")
        genre = data.get("genre", "")
        seed_idea = data.get("seed_idea", "")
        language = data.get("language", "de")
        
        if not name:
            return {"success": False, "error": "World name required"}
        
        # Get language config
        lang_config = get_language_config(language)
        
        # Build context
        context = {
            "name": name,
            "world_type": world_type,
            "genre": genre,
            "seed_idea": seed_idea,
            "language": language,
            "output_instruction": lang_config["output_instruction"],
        }
        
        # Build prompt
        prompt = WorldGeneratorHandler._build_prompt(context)
        
        # Generate with LLM (balanced quality for creative world-building)
        provider = getattr(settings, "LLM_PROVIDER", "openai")
        model = getattr(settings, "LLM_MODEL", None)
        llm = LLMService(provider=provider, model=model)
        
        result = llm.generate_chapter_content(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.8,  # Higher creativity
            quality="balanced",  # Creative task
            system_prompt=lang_config["system_prompt"],
        )
        
        if not result["success"]:
            return result
        
        # Parse world data
        parsed = WorldGeneratorHandler._parse_world(result["content"])
        
        logger.info(f"Generated world foundation for '{name}'")
        
        return {
            "success": True,
            **parsed,
            "raw_content": result["content"],
            "usage": result.get("usage"),
            "model_used": result.get("model_used"),
            "cached": result.get("cached", False),
        }
    
    @staticmethod
    def _build_prompt(context: Dict) -> str:
        """Build LLM prompt for world generation"""
        parts = [
            "# Task: Create World Foundation",
            "",
            "Generate a rich, detailed world foundation for creative writing.",
            "",
            f"## World Name: {context['name']}",
            f"## World Type: {context['world_type']}",
        ]
        
        if context.get("genre"):
            parts.append(f"## Story Genre: {context['genre']}")
        
        if context.get("seed_idea"):
            parts.extend([
                "",
                "## Starting Concept:",
                context["seed_idea"],
            ])
        
        parts.extend([
            "",
            "## Generate the following (be creative and specific):",
            "",
            "1. **DESCRIPTION**: 2-3 paragraphs overview of this world",
            "2. **SETTING_ERA**: Time period or era (e.g., 'Medieval Fantasy', 'Far Future 3000 AD')",
            "3. **GEOGRAPHY**: Major landforms, continents, notable features",
            "4. **CLIMATE**: Weather patterns, seasons, climate zones",
            "5. **INHABITANTS**: Races, species, or peoples who live here",
            "6. **CULTURE**: Dominant cultures, traditions, values",
            "7. **TECHNOLOGY_LEVEL**: Tech level and notable inventions",
            "",
            "## Output Format:",
            "",
            f"**{context.get('output_instruction', 'Respond in German.')}**",
            "",
            "Return as JSON:",
            "```json",
            "{",
            '  "description": "...",',
            '  "setting_era": "...",',
            '  "geography": "...",',
            '  "climate": "...",',
            '  "inhabitants": "...",',
            '  "culture": "...",',
            '  "technology_level": "..."',
            "}",
            "```",
        ])
        
        return "\n".join(parts)
    
    @staticmethod
    def _parse_world(content: str) -> Dict[str, Any]:
        """Parse LLM response into world data"""
        # Try JSON extraction
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try raw JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Fallback: extract sections
        result = {}
        sections = ["description", "setting_era", "geography", "climate", 
                   "inhabitants", "culture", "technology_level"]
        
        for section in sections:
            pattern = rf'{section}["\s:]*["\s]*(.*?)(?=(?:{"|".join(sections)})|$)'
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                result[section] = match.group(1).strip().strip('"').strip()
        
        return result


class WorldExpanderHandler:
    """
    Expand a specific aspect of an existing world.
    
    Input:
    - world_data: dict (existing world info)
    - aspect: str (magic_system, politics, economy, history, religion)
    - existing_content: str (optional, current content to expand)
    - direction: str (optional, specific direction to expand)
    
    Output:
    - content: str (expanded content for the aspect)
    - suggestions: list (related ideas)
    - success: bool
    """
    
    ASPECT_PROMPTS = {
        "magic_system": {
            "title": "Magic System Design",
            "instructions": """Design a complete magic system including:
- Source of magic (where does it come from?)
- Rules and limitations (what can't it do?)
- Cost or price (what does using it require?)
- Learning/access (who can use it and how?)
- Cultural impact (how does society view magic?)
- Types or schools (different magical disciplines)""",
        },
        "politics": {
            "title": "Political Landscape",
            "instructions": """Define the political structure including:
- Government types (monarchy, democracy, theocracy, etc.)
- Major factions and their goals
- Power dynamics and conflicts
- Laws and justice systems
- International/inter-regional relations
- Current political tensions""",
        },
        "economy": {
            "title": "Economic System",
            "instructions": """Detail the economic systems including:
- Currency and trade systems
- Major industries and resources
- Wealth distribution
- Trade routes and partners
- Economic classes
- Market dynamics""",
        },
        "history": {
            "title": "Historical Timeline",
            "instructions": """Create key historical events including:
- Origin/creation myths
- Major wars or conflicts
- Golden ages and dark periods
- Technological breakthroughs
- Cultural shifts
- Recent history (last 100 years)""",
        },
        "religion": {
            "title": "Religious Systems",
            "instructions": """Develop religious/spiritual systems including:
- Major deities or beliefs
- Religious organizations
- Sacred sites and rituals
- Afterlife concepts
- Religious conflicts
- Relationship between religion and society""",
        },
    }
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Expand world aspect with LLM"""
        world_data = data.get("world_data", {})
        aspect = data.get("aspect", "")
        existing_content = data.get("existing_content", "")
        direction = data.get("direction", "")
        language = data.get("language", "de")
        
        if not aspect or aspect not in WorldExpanderHandler.ASPECT_PROMPTS:
            return {
                "success": False,
                "error": f"Invalid aspect. Choose from: {list(WorldExpanderHandler.ASPECT_PROMPTS.keys())}"
            }
        
        # Get language config
        lang_config = get_language_config(language)
        
        # Build context
        context = {
            "world_data": world_data,
            "aspect": aspect,
            "existing_content": existing_content,
            "direction": direction,
            "aspect_config": WorldExpanderHandler.ASPECT_PROMPTS[aspect],
            "output_instruction": lang_config["output_instruction"],
        }
        
        # Build prompt
        prompt = WorldExpanderHandler._build_prompt(context)
        
        # Generate (balanced for creative expansion)
        provider = getattr(settings, "LLM_PROVIDER", "openai")
        model = getattr(settings, "LLM_MODEL", None)
        llm = LLMService(provider=provider, model=model)
        
        result = llm.generate_chapter_content(
            prompt=prompt,
            max_tokens=1800,
            temperature=0.8,
            quality="balanced",
            system_prompt=lang_config["system_prompt"],
        )
        
        if not result["success"]:
            return result
        
        # Parse response
        parsed = WorldExpanderHandler._parse_expansion(result["content"])
        
        logger.info(f"Expanded world aspect: {aspect}")
        
        return {
            "success": True,
            "aspect": aspect,
            **parsed,
            "raw_content": result["content"],
            "usage": result.get("usage"),
        }
    
    @staticmethod
    def _build_prompt(context: Dict) -> str:
        """Build expansion prompt"""
        aspect_config = context["aspect_config"]
        world_data = context["world_data"]
        
        parts = [
            f"# Task: {aspect_config['title']}",
            "",
            "## World Context:",
            f"- **Name:** {world_data.get('name', 'Unknown')}",
            f"- **Type:** {world_data.get('world_type', 'Fantasy')}",
        ]
        
        if world_data.get("description"):
            parts.extend([
                "",
                "## World Description:",
                world_data["description"][:500],
            ])
        
        if world_data.get("culture"):
            parts.extend([
                "",
                "## Existing Culture:",
                world_data["culture"][:300],
            ])
        
        if context.get("existing_content"):
            parts.extend([
                "",
                "## Current Content to Expand:",
                context["existing_content"],
            ])
        
        if context.get("direction"):
            parts.extend([
                "",
                "## Specific Direction:",
                context["direction"],
            ])
        
        parts.extend([
            "",
            "## Instructions:",
            aspect_config["instructions"],
            "",
            "## Output Format:",
            "",
            f"**{context.get('output_instruction', 'Respond in German.')}**",
            "",
            "```json",
            "{",
            '  "content": "Detailed expansion content...",',
            '  "suggestions": ["Related idea 1", "Related idea 2", "Related idea 3"]',
            "}",
            "```",
        ])
        
        return "\n".join(parts)
    
    @staticmethod
    def _parse_expansion(content: str) -> Dict[str, Any]:
        """Parse expansion response"""
        # Try JSON
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Fallback
        return {
            "content": content,
            "suggestions": [],
        }


class LocationGeneratorHandler:
    """
    Generate locations for a world.
    
    Input:
    - world_data: dict (world context)
    - location_type: str (continent, country, city, etc.)
    - count: int (how many to generate, default 3)
    - parent_location: str (optional, parent location name)
    
    Output:
    - locations: list of dicts with name, description, significance
    - success: bool
    """
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate locations with LLM"""
        world_data = data.get("world_data", {})
        location_type = data.get("location_type", "city")
        count = min(data.get("count", 3), 10)  # Max 10
        parent_location = data.get("parent_location", "")
        language = data.get("language", "de")
        
        # Get language config
        lang_config = get_language_config(language)
        
        # Build prompt
        prompt = LocationGeneratorHandler._build_prompt(
            world_data, location_type, count, parent_location, lang_config["output_instruction"]
        )
        
        # Generate (fast model for simple lists)
        provider = getattr(settings, "LLM_PROVIDER", "openai")
        model = getattr(settings, "LLM_MODEL", None)
        llm = LLMService(provider=provider, model=model)
        
        result = llm.generate_chapter_content(
            prompt=prompt,
            max_tokens=1500,
            temperature=0.8,
            quality="fast",  # Location lists are simpler
            system_prompt=lang_config["system_prompt"],
        )
        
        if not result["success"]:
            return result
        
        # Parse locations
        locations = LocationGeneratorHandler._parse_locations(result["content"])
        
        logger.info(f"Generated {len(locations)} {location_type} locations")
        
        return {
            "success": True,
            "locations": locations,
            "location_type": location_type,
            "raw_content": result["content"],
            "usage": result.get("usage"),
        }
    
    @staticmethod
    def _build_prompt(world_data: Dict, location_type: str, count: int, parent: str, output_instruction: str = "Antworte auf Deutsch.") -> str:
        """Build location generation prompt"""
        type_descriptions = {
            "continent": "major landmasses with distinct characteristics",
            "country": "nations or kingdoms with unique cultures",
            "region": "geographical or cultural regions",
            "city": "settlements with history and character",
            "district": "neighborhoods or areas within a city",
            "building": "notable buildings or structures",
            "landmark": "famous landmarks or points of interest",
            "natural": "natural features like mountains, forests, rivers",
        }
        
        parts = [
            f"# Task: Generate {count} {location_type.title()} Locations",
            "",
            "## World Context:",
            f"- **World:** {world_data.get('name', 'Unknown')}",
        ]
        
        if world_data.get("geography"):
            parts.append(f"- **Geography:** {world_data['geography'][:200]}")
        if world_data.get("culture"):
            parts.append(f"- **Culture:** {world_data['culture'][:200]}")
        
        if parent:
            parts.extend([
                "",
                f"## Parent Location: {parent}",
                "Generate locations within or related to this parent.",
            ])
        
        parts.extend([
            "",
            f"## Generate {count} {type_descriptions.get(location_type, 'locations')}",
            "",
            "For each location provide:",
            "- **name**: Unique, fitting name",
            "- **description**: 2-3 sentences about the place",
            "- **significance**: Why this place matters to the story",
            "",
            "## Output Format:",
            "",
            f"**{output_instruction}**",
            "",
            "```json",
            "{",
            '  "locations": [',
            '    {"name": "...", "description": "...", "significance": "..."},',
            "    ...",
            "  ]",
            "}",
            "```",
        ])
        
        return "\n".join(parts)
    
    @staticmethod
    def _parse_locations(content: str) -> List[Dict]:
        """Parse location list from response"""
        # Try JSON
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return data.get("locations", [])
            except json.JSONDecodeError:
                pass
        
        # Try raw JSON
        try:
            data = json.loads(content)
            return data.get("locations", [])
        except json.JSONDecodeError:
            pass
        
        return []


class WorldRuleGeneratorHandler:
    """
    Generate rules/constraints for a world.
    
    Input:
    - world_data: dict (world context)
    - category: str (physics, magic, social, technology, biology, economy)
    - count: int (how many rules, default 5)
    
    Output:
    - rules: list of dicts with rule, explanation, importance
    - success: bool
    """
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate world rules with LLM"""
        world_data = data.get("world_data", {})
        category = data.get("category", "physics")
        count = min(data.get("count", 5), 10)
        language = data.get("language", "de")
        
        # Get language config
        lang_config = get_language_config(language)
        
        # Build prompt
        prompt = WorldRuleGeneratorHandler._build_prompt(world_data, category, count, lang_config["output_instruction"])
        
        # Generate (fast model for rule lists)
        provider = getattr(settings, "LLM_PROVIDER", "openai")
        model = getattr(settings, "LLM_MODEL", None)
        llm = LLMService(provider=provider, model=model)
        
        result = llm.generate_chapter_content(
            prompt=prompt,
            max_tokens=1200,
            temperature=0.7,
            quality="fast",
            system_prompt=lang_config["system_prompt"],
        )
        
        if not result["success"]:
            return result
        
        # Parse rules
        rules = WorldRuleGeneratorHandler._parse_rules(result["content"])
        
        logger.info(f"Generated {len(rules)} {category} rules")
        
        return {
            "success": True,
            "rules": rules,
            "category": category,
            "raw_content": result["content"],
            "usage": result.get("usage"),
        }
    
    @staticmethod
    def _build_prompt(world_data: Dict, category: str, count: int, output_instruction: str = "Antworte auf Deutsch.") -> str:
        """Build rule generation prompt"""
        category_guidance = {
            "physics": "Laws of physics that differ from real world",
            "magic": "Rules governing magical abilities and limitations",
            "social": "Social norms, taboos, and customs",
            "technology": "Technological capabilities and restrictions",
            "biology": "Biological rules for creatures and beings",
            "economy": "Economic laws and trade rules",
        }
        
        parts = [
            f"# Task: Generate {count} World Rules ({category.title()})",
            "",
            "## World Context:",
            f"- **World:** {world_data.get('name', 'Unknown')}",
            f"- **Type:** {world_data.get('world_type', 'Fantasy')}",
        ]
        
        if world_data.get("magic_system"):
            parts.append(f"- **Magic:** {world_data['magic_system'][:200]}")
        if world_data.get("technology_level"):
            parts.append(f"- **Tech:** {world_data['technology_level'][:100]}")
        
        parts.extend([
            "",
            f"## Category: {category_guidance.get(category, category)}",
            "",
            f"Generate {count} rules that help maintain world consistency.",
            "Rules should be clear, enforceable, and story-relevant.",
            "",
            "For each rule:",
            "- **rule**: Clear statement of the rule",
            "- **explanation**: Why this rule exists",
            "- **importance**: 'absolute', 'strong', or 'guideline'",
            "",
            "## Output Format:",
            "",
            f"**{output_instruction}**",
            "",
            "```json",
            "{",
            '  "rules": [',
            '    {"rule": "...", "explanation": "...", "importance": "strong"},',
            "    ...",
            "  ]",
            "}",
            "```",
        ])
        
        return "\n".join(parts)
    
    @staticmethod
    def _parse_rules(content: str) -> List[Dict]:
        """Parse rules from response"""
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return data.get("rules", [])
            except json.JSONDecodeError:
                pass
        
        try:
            data = json.loads(content)
            return data.get("rules", [])
        except json.JSONDecodeError:
            pass
        
        return []


class WorldConsistencyCheckerHandler:
    """
    Check world for internal consistency using LLM.
    
    Input:
    - world_data: dict (complete world data)
    
    Output:
    - issues: list of potential inconsistencies
    - suggestions: list of improvements
    - consistency_score: int (1-10)
    - success: bool
    """
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Check world consistency with LLM"""
        world_data = data.get("world_data", {})
        language = data.get("language", "de")
        
        if not world_data.get("name"):
            return {"success": False, "error": "World data required"}
        
        # Get language config
        lang_config = get_language_config(language)
        
        # Build prompt
        prompt = WorldConsistencyCheckerHandler._build_prompt(world_data, lang_config["output_instruction"])
        
        # Generate (best quality for critical analysis)
        provider = getattr(settings, "LLM_PROVIDER", "openai")
        model = getattr(settings, "LLM_MODEL", None)
        llm = LLMService(provider=provider, model=model)
        
        result = llm.generate_chapter_content(
            prompt=prompt,
            max_tokens=1500,
            temperature=0.5,  # More analytical
            quality="best",  # Critical analysis needs best model
            system_prompt=lang_config["system_prompt"],
        )
        
        if not result["success"]:
            return result
        
        # Parse analysis
        parsed = WorldConsistencyCheckerHandler._parse_analysis(result["content"])
        
        logger.info(f"Consistency check for '{world_data.get('name')}': Score {parsed.get('consistency_score', 'N/A')}/10")
        
        return {
            "success": True,
            **parsed,
            "raw_content": result["content"],
            "usage": result.get("usage"),
        }
    
    @staticmethod
    def _build_prompt(world_data: Dict, output_instruction: str = "Antworte auf Deutsch.") -> str:
        """Build consistency check prompt"""
        parts = [
            "# Task: World Consistency Analysis",
            "",
            "Analyze this world for internal consistency and logic.",
            "",
            f"## World: {world_data.get('name', 'Unknown')}",
            f"## Type: {world_data.get('world_type', 'Unknown')}",
            "",
            "## World Details:",
        ]
        
        fields = [
            ("description", "Description"),
            ("setting_era", "Era"),
            ("geography", "Geography"),
            ("climate", "Climate"),
            ("inhabitants", "Inhabitants"),
            ("culture", "Culture"),
            ("technology_level", "Technology"),
            ("magic_system", "Magic System"),
            ("politics", "Politics"),
            ("economy", "Economy"),
            ("religion", "Religion"),
            ("history", "History"),
        ]
        
        for field, label in fields:
            if world_data.get(field):
                parts.append(f"**{label}:** {world_data[field][:300]}")
        
        parts.extend([
            "",
            "## Analyze for:",
            "1. Logical inconsistencies",
            "2. Contradictions between elements",
            "3. Missing explanations",
            "4. Unrealistic interactions",
            "",
            "## Output Format:",
            "",
            f"**{output_instruction}**",
            "",
            "```json",
            "{",
            '  "consistency_score": 8,',
            '  "issues": [',
            '    {"issue": "...", "severity": "high/medium/low", "affected": "..."}',
            "  ],",
            '  "suggestions": ["Improvement 1", "Improvement 2"],',
            '  "strengths": ["What works well"]',
            "}",
            "```",
        ])
        
        return "\n".join(parts)
    
    @staticmethod
    def _parse_analysis(content: str) -> Dict[str, Any]:
        """Parse consistency analysis"""
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        return {
            "consistency_score": 5,
            "issues": [],
            "suggestions": [],
            "strengths": [],
        }


class WorldSuggestionApplierHandler:
    """
    Apply AI suggestions to improve world consistency.
    
    Takes suggestions from consistency check and uses AI to 
    expand/improve world fields accordingly.
    
    Input:
    - world: World model instance
    - suggestions: list of suggestion strings
    - issues: list of issue dicts
    
    Output:
    - success: bool
    - changes: list of applied changes
    - updated_fields: dict of field -> new value
    """
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Apply suggestions using LLM"""
        world = data.get("world")
        suggestions = data.get("suggestions", [])
        issues = data.get("issues", [])
        language = data.get("language", "de")
        
        if not world:
            return {"success": False, "error": "World instance required"}
        
        if not suggestions:
            return {"success": False, "error": "No suggestions to apply"}
        
        # Get language config
        lang_config = get_language_config(language)
        
        # Build prompt
        prompt = WorldSuggestionApplierHandler._build_prompt(world, suggestions, issues, lang_config["output_instruction"])
        
        # Generate improvements
        provider = getattr(settings, "LLM_PROVIDER", "openai")
        model = getattr(settings, "LLM_MODEL", None)
        llm = LLMService(provider=provider, model=model)
        
        result = llm.generate_chapter_content(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.7,
            quality="best",
            system_prompt=lang_config["system_prompt"],
        )
        
        if not result["success"]:
            return result
        
        # Parse improvements
        parsed = WorldSuggestionApplierHandler._parse_improvements(result["content"])
        
        logger.info(f"Applied {len(parsed.get('changes', []))} improvements to world '{world.name}'")
        
        return {
            "success": True,
            **parsed,
            "usage": result.get("usage"),
        }
    
    @staticmethod
    def _build_prompt(world, suggestions: List[str], issues: List[Dict], output_instruction: str) -> str:
        """Build improvement prompt"""
        parts = [
            "# Task: Improve World Description",
            "",
            f"## World: {world.name}",
            "",
            "## Current World Data:",
        ]
        
        fields = [
            ("description", "Description"),
            ("geography", "Geography"),
            ("climate", "Climate"),
            ("inhabitants", "Inhabitants"),
            ("culture", "Culture"),
            ("technology_level", "Technology"),
            ("magic_system", "Magic System"),
            ("politics", "Politics"),
            ("history", "History"),
        ]
        
        for field, label in fields:
            value = getattr(world, field, None)
            if value:
                parts.append(f"**{label}:** {value[:500]}")
        
        parts.extend([
            "",
            "## Issues to Address:",
        ])
        for issue in issues[:5]:
            if isinstance(issue, dict):
                parts.append(f"- {issue.get('issue', str(issue))}")
            else:
                parts.append(f"- {issue}")
        
        parts.extend([
            "",
            "## Suggestions to Implement:",
        ])
        for s in suggestions[:5]:
            parts.append(f"- {s}")
        
        parts.extend([
            "",
            "## Task:",
            "Expand and improve the world description to address the issues and implement the suggestions.",
            "Keep existing good content, just expand where needed.",
            "",
            f"**{output_instruction}**",
            "",
            "## Output Format:",
            "```json",
            "{",
            '  "changes": ["Description of change 1", "Description of change 2"],',
            '  "updated_fields": {',
            '    "description": "New expanded description...",',
            '    "inhabitants": "New expanded inhabitants...",',
            '    "culture": "New expanded culture..."',
            "  }",
            "}",
            "```",
            "",
            "Only include fields that need changes. Keep improvements concise but meaningful.",
        ])
        
        return "\n".join(parts)
    
    @staticmethod
    def _parse_improvements(content: str) -> Dict[str, Any]:
        """Parse improvement results"""
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        return {
            "changes": [],
            "updated_fields": {},
        }
