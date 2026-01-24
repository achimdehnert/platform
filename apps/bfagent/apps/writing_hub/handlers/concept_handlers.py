"""
Concept Handlers - Phase 1: Konzept & Idee
Handlers for initial project conception and planning
"""

import json
import logging
import re
from typing import Any, Dict, List

from django.conf import settings

from apps.bfagent.domains.book_writing.services.llm_service import LLMService
from apps.bfagent.models import BookProjects

logger = logging.getLogger(__name__)


class PremiseGeneratorHandler:
    """
    Generate premise (story concept) using LLM from basic project info

    Input:
    - project_id: int (BookProjects ID)
    - title: str (optional, overrides project title)
    - genre: str (optional, overrides project genre)
    - inspiration: str (optional, user's initial ideas)
    - target_length: str (optional: 'short_story', 'novella', 'novel', 'series')

    Output:
    - premise: str (2-3 paragraph story premise)
    - premise_short: str (1 sentence version)
    - premise_elevator: str (30 second pitch)
    - key_conflict: str
    - protagonist_sketch: str
    - antagonist_sketch: str
    - success: bool
    - usage: dict (LLM usage stats)
    """

    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate premise with LLM"""
        project_id = data.get("project_id")

        if not project_id:
            return {"success": False, "error": "project_id required"}

        try:
            project = BookProjects.objects.get(id=project_id)
        except BookProjects.DoesNotExist:
            return {"success": False, "error": f"Project {project_id} not found"}

        # Check API key
        api_key_available = getattr(settings, "OPENAI_API_KEY", None) or getattr(
            settings, "ANTHROPIC_API_KEY", None
        )

        if not api_key_available:
            return {"success": False, "error": "No LLM API key configured"}

        # Build context
        context = {
            "title": data.get("title") or project.title,
            "genre": data.get("genre") or project.genre or "Fiction",
            "description": project.description or "",
            "inspiration": data.get("inspiration", ""),
            "target_length": data.get("target_length", "novel"),
        }

        # Build prompt
        prompt = PremiseGeneratorHandler._build_prompt(context)

        # Generate with LLM
        provider = getattr(settings, "LLM_PROVIDER", "openai")
        model = getattr(settings, "LLM_MODEL", None)
        llm = LLMService(provider=provider, model=model)

        result = llm.generate_chapter_content(
            prompt=prompt, max_tokens=1500, temperature=0.8, quality="balanced"  # Creative concept
        )

        if not result["success"]:
            return result

        # Parse premise
        parsed = PremiseGeneratorHandler._parse_premise(result["content"])

        # Update project with premise
        if parsed.get("premise"):
            try:
                project.premise = parsed["premise"]
                if hasattr(project, "tagline") and parsed.get("premise_short"):
                    project.tagline = parsed["premise_short"]
                project.save()
            except Exception as e:
                logger.warning(f"Could not save premise to project: {e}")

        logger.info(f"Generated premise for project {project_id}")

        return {
            "success": True,
            **parsed,
            "raw_content": result["content"],
            "usage": result.get("usage"),
            "cost": llm.calculate_cost(result["usage"]) if result.get("usage") else 0,
        }

    @staticmethod
    def _build_prompt(context: Dict) -> str:
        """Build LLM prompt for premise generation"""
        parts = [
            "# Task: Generate Story Premise",
            "",
            "You are a professional story consultant helping an author develop their book concept.",
            "",
            "## Book Information:",
            f"- **Working Title:** {context['title']}",
            f"- **Genre:** {context['genre']}",
            f"- **Target Length:** {context['target_length']}",
        ]

        if context.get("description"):
            parts.extend(
                [
                    f"- **Initial Description:** {context['description']}",
                ]
            )

        if context.get("inspiration"):
            parts.extend(
                [
                    "",
                    "## Author's Inspiration:",
                    context["inspiration"],
                ]
            )

        parts.extend(
            [
                "",
                "## Your Task:",
                "",
                "Generate a compelling story premise that includes:",
                "",
                "1. **PREMISE** (2-3 paragraphs)",
                "   - What is the story about?",
                "   - What is the main conflict?",
                "   - What are the stakes?",
                "   - Why would readers care?",
                "",
                "2. **PREMISE_SHORT** (1 sentence)",
                "   - Distill the premise to its essence",
                "   - This will be the logline later",
                "",
                "3. **ELEVATOR_PITCH** (30 seconds)",
                "   - How would you pitch this story in an elevator?",
                "   - 2-3 sentences maximum",
                "",
                "4. **KEY_CONFLICT**",
                "   - What is the central conflict of the story?",
                "   - External AND internal if applicable",
                "",
                "5. **PROTAGONIST_SKETCH**",
                "   - Brief sketch of who the main character is",
                "   - What do they want?",
                "   - What stands in their way?",
                "",
                "6. **ANTAGONIST_SKETCH**",
                "   - Brief sketch of the opposing force",
                "   - Could be a person, system, nature, or internal struggle",
                "",
                "## Output Format:",
                "",
                "Return your response as JSON:",
                "",
                "```json",
                "{",
                '  "premise": "Full 2-3 paragraph premise...",',
                '  "premise_short": "One sentence version",',
                '  "premise_elevator": "30 second pitch",',
                '  "key_conflict": "Central conflict description",',
                '  "protagonist_sketch": "Main character sketch",',
                '  "antagonist_sketch": "Opposing force sketch"',
                "}",
                "```",
                "",
                "Make the premise:",
                "- Specific and vivid",
                "- Emotionally engaging",
                "- Clear about what makes this story unique",
                f"- Appropriate for the {context['genre']} genre",
                f"- Suitable for a {context['target_length']}",
            ]
        )

        return "\n".join(parts)

    @staticmethod
    def _parse_premise(content: str) -> Dict[str, str]:
        """Parse premise from LLM response"""
        # Try JSON first
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return data
            except json.JSONDecodeError:
                pass

        # Fallback: Parse markdown sections
        result = {}

        patterns = {
            "premise": r"##?\s*PREMISE[:\s]+(.*?)(?=##|\*\*|$)",
            "premise_short": r"##?\s*PREMISE[_\s]SHORT[:\s]+(.*?)(?=##|\*\*|$)",
            "premise_elevator": r"##?\s*ELEVATOR[_\s]PITCH[:\s]+(.*?)(?=##|\*\*|$)",
            "key_conflict": r"##?\s*KEY[_\s]CONFLICT[:\s]+(.*?)(?=##|\*\*|$)",
            "protagonist_sketch": r"##?\s*PROTAGONIST[_\s]SKETCH[:\s]+(.*?)(?=##|\*\*|$)",
            "antagonist_sketch": r"##?\s*ANTAGONIST[_\s]SKETCH[:\s]+(.*?)(?=##|\*\*|$)",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                result[key] = match.group(1).strip()

        # If still no premise, use entire content
        if not result.get("premise"):
            result["premise"] = content.strip()

        return result


class ThemeIdentifierHandler:
    """
    Identify themes in a story using LLM from premise and context

    Input:
    - project_id: int (BookProjects ID)
    - premise: str (optional, if not using project.premise)
    - additional_context: str (optional, any extra info)

    Output:
    - themes: list of theme dicts with:
      - name: str
      - description: str
      - how_explored: str
    - primary_theme: str
    - secondary_themes: list of str
    - success: bool
    - usage: dict (LLM usage stats)
    """

    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Identify themes with LLM"""
        project_id = data.get("project_id")

        if not project_id:
            return {"success": False, "error": "project_id required"}

        try:
            project = BookProjects.objects.get(id=project_id)
        except BookProjects.DoesNotExist:
            return {"success": False, "error": f"Project {project_id} not found"}

        # Check API key
        api_key_available = getattr(settings, "OPENAI_API_KEY", None) or getattr(
            settings, "ANTHROPIC_API_KEY", None
        )

        if not api_key_available:
            return {"success": False, "error": "No LLM API key configured"}

        # Get premise
        premise = data.get("premise") or getattr(project, "premise", None)
        if not premise:
            return {
                "success": False,
                "error": "No premise found. Run PremiseGeneratorHandler first.",
            }

        # Build context
        context = {
            "title": project.title,
            "genre": project.genre or "Fiction",
            "premise": premise,
            "description": project.description or "",
            "additional_context": data.get("additional_context", ""),
        }

        # Build prompt
        prompt = ThemeIdentifierHandler._build_prompt(context)

        # Generate with LLM
        provider = getattr(settings, "LLM_PROVIDER", "openai")
        model = getattr(settings, "LLM_MODEL", None)
        llm = LLMService(provider=provider, model=model)

        result = llm.generate_chapter_content(
            prompt=prompt, max_tokens=1200, temperature=0.7, quality="fast"  # Theme analysis
        )

        if not result["success"]:
            return result

        # Parse themes
        parsed = ThemeIdentifierHandler._parse_themes(result["content"])

        # Update project with themes
        if parsed.get("themes"):
            try:
                # Convert to simple list for JSON storage
                theme_list = [theme["name"] for theme in parsed["themes"]]
                if hasattr(project, "themes"):
                    project.themes = theme_list
                    project.save()
            except Exception as e:
                logger.warning(f"Could not save themes to project: {e}")

        logger.info(f"Identified {len(parsed.get('themes', []))} themes for project {project_id}")

        return {
            "success": True,
            **parsed,
            "raw_content": result["content"],
            "usage": result.get("usage"),
            "cost": llm.calculate_cost(result["usage"]) if result.get("usage") else 0,
        }

    @staticmethod
    def _build_prompt(context: Dict) -> str:
        """Build LLM prompt for theme identification"""
        parts = [
            "# Task: Identify Story Themes",
            "",
            "You are a literary analyst helping an author identify the themes in their story.",
            "",
            "## Book Information:",
            f"- **Title:** {context['title']}",
            f"- **Genre:** {context['genre']}",
            "",
            "## Premise:",
            context["premise"],
        ]

        if context.get("additional_context"):
            parts.extend(
                [
                    "",
                    "## Additional Context:",
                    context["additional_context"],
                ]
            )

        parts.extend(
            [
                "",
                "## Your Task:",
                "",
                "Identify 3-5 themes that this story explores. For each theme:",
                "",
                "1. **NAME** - What is the theme? (e.g., 'Redemption', 'Power and Corruption')",
                "2. **DESCRIPTION** - What does this theme mean in the context of this story?",
                "3. **HOW_EXPLORED** - How will this theme be explored through the plot and characters?",
                "",
                "Focus on:",
                "- Universal themes that resonate with readers",
                "- Themes that naturally emerge from the premise",
                "- Themes appropriate for the genre",
                "- Clear primary theme (most important)",
                "- 2-4 secondary themes (support primary)",
                "",
                "## Output Format:",
                "",
                "Return your response as JSON:",
                "",
                "```json",
                "{",
                '  "primary_theme": "Main theme name",',
                '  "secondary_themes": ["Theme 2", "Theme 3", "Theme 4"],',
                '  "themes": [',
                "    {",
                '      "name": "Theme Name",',
                '      "description": "What this theme means in this story",',
                '      "how_explored": "How it will be shown through plot and characters"',
                "    }",
                "  ]",
                "}",
                "```",
                "",
                "Make themes:",
                "- Specific to THIS story",
                "- Emotionally resonant",
                "- Relevant to the premise",
                f"- Appropriate for {context['genre']}",
            ]
        )

        return "\n".join(parts)

    @staticmethod
    def _parse_themes(content: str) -> Dict:
        """Parse themes from LLM response"""
        # Try JSON first
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return data
            except json.JSONDecodeError:
                pass

        # Fallback: Simple extraction
        result = {"themes": [], "primary_theme": "", "secondary_themes": []}

        # Try to find theme mentions
        theme_pattern = r"(?:Theme|theme).*?:\s*([^\n]+)"
        themes = re.findall(theme_pattern, content)

        if themes:
            result["primary_theme"] = themes[0]
            result["secondary_themes"] = themes[1:5]
            result["themes"] = [
                {
                    "name": theme,
                    "description": f"Theme identified from premise",
                    "how_explored": "Through plot and character development",
                }
                for theme in themes
            ]

        return result


class LoglineGeneratorHandler:
    """
    Generate logline (one-sentence pitch) using LLM from premise

    Input:
    - project_id: int (BookProjects ID)
    - premise: str (optional, if not using project.premise)
    - style: str (optional: 'concise', 'dramatic', 'mysterious', 'action')

    Output:
    - logline: str (one sentence, ~25 words)
    - logline_variations: list of str (3 alternative versions)
    - hook_analysis: str (what makes this compelling)
    - success: bool
    - usage: dict (LLM usage stats)
    """

    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate logline with LLM"""
        project_id = data.get("project_id")

        if not project_id:
            return {"success": False, "error": "project_id required"}

        try:
            project = BookProjects.objects.get(id=project_id)
        except BookProjects.DoesNotExist:
            return {"success": False, "error": f"Project {project_id} not found"}

        # Check API key
        api_key_available = getattr(settings, "OPENAI_API_KEY", None) or getattr(
            settings, "ANTHROPIC_API_KEY", None
        )

        if not api_key_available:
            return {"success": False, "error": "No LLM API key configured"}

        # Get premise
        premise = data.get("premise") or getattr(project, "premise", None)
        if not premise:
            return {
                "success": False,
                "error": "No premise found. Run PremiseGeneratorHandler first.",
            }

        # Build context
        context = {
            "title": project.title,
            "genre": project.genre or "Fiction",
            "premise": premise,
            "style": data.get("style", "concise"),
        }

        # Build prompt
        prompt = LoglineGeneratorHandler._build_prompt(context)

        # Generate with LLM
        provider = getattr(settings, "LLM_PROVIDER", "openai")
        model = getattr(settings, "LLM_MODEL", None)
        llm = LLMService(provider=provider, model=model)

        result = llm.generate_chapter_content(
            prompt=prompt, max_tokens=800, temperature=0.8, quality="fast"  # Short logline
        )

        if not result["success"]:
            return result

        # Parse logline
        parsed = LoglineGeneratorHandler._parse_logline(result["content"])

        # Update project with logline
        if parsed.get("logline"):
            try:
                if hasattr(project, "tagline"):
                    project.tagline = parsed["logline"]
                    project.save()
            except Exception as e:
                logger.warning(f"Could not save logline to project: {e}")

        logger.info(f"Generated logline for project {project_id}")

        return {
            "success": True,
            **parsed,
            "raw_content": result["content"],
            "usage": result.get("usage"),
            "cost": llm.calculate_cost(result["usage"]) if result.get("usage") else 0,
        }

    @staticmethod
    def _build_prompt(context: Dict) -> str:
        """Build LLM prompt for logline generation"""
        parts = [
            "# Task: Generate Logline",
            "",
            "You are a professional pitch consultant helping an author create a compelling logline.",
            "",
            "A logline is a one-sentence summary that captures:",
            "- WHO the protagonist is",
            "- WHAT they want",
            "- WHO/WHAT opposes them",
            "- WHAT's at stake",
            "",
            "## Book Information:",
            f"- **Title:** {context['title']}",
            f"- **Genre:** {context['genre']}",
            "",
            "## Premise:",
            context["premise"],
            "",
            f"## Desired Style: {context['style']}",
            "",
            "## Your Task:",
            "",
            "Create a compelling logline that:",
            "- Is ONE sentence (approximately 25 words)",
            "- Includes protagonist, goal, opposition, and stakes",
            "- Hooks the reader immediately",
            f"- Matches the {context['style']} style",
            "- Avoids clichés",
            "",
            "Also provide:",
            "- 3 alternative versions (different angles)",
            "- Analysis of what makes the main logline effective",
            "",
            "## Output Format:",
            "",
            "Return your response as JSON:",
            "",
            "```json",
            "{",
            '  "logline": "Main logline (one sentence, ~25 words)",',
            '  "logline_variations": [',
            '    "Alternative version 1",',
            '    "Alternative version 2",',
            '    "Alternative version 3"',
            "  ],",
            '  "hook_analysis": "What makes this logline compelling and effective"',
            "}",
            "```",
            "",
            "Examples of great loglines:",
            "- The Hunger Games: 'In a dystopian future, a teenage girl volunteers to take her sister's place in a televised fight to the death.'",
            "- Jurassic Park: 'A wealthy entrepreneur secretly creates a theme park featuring living dinosaurs drawn from prehistoric DNA.'",
            "",
            "Make your logline:",
            "- Clear and specific",
            "- Emotionally engaging",
            "- Highlight the unique hook",
            f"- Perfect for {context['genre']}",
        ]

        return "\n".join(parts)

    @staticmethod
    def _parse_logline(content: str) -> Dict:
        """Parse logline from LLM response"""
        # Try JSON first
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return data
            except json.JSONDecodeError:
                pass

        # Fallback: Extract first clear sentence
        sentences = re.split(r"[.!?]\s+", content)

        result = {
            "logline": sentences[0] if sentences else content[:200],
            "logline_variations": sentences[1:4] if len(sentences) > 1 else [],
            "hook_analysis": "Logline captures the core conflict and stakes",
        }

        return result
