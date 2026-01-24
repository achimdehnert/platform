"""
Chapter Planning Handlers - Phase 5: Chapter Breakdown
Handlers for detailed chapter-level planning before writing
"""

import json
import logging
import re
from typing import Any, Dict, List

from django.conf import settings

from apps.bfagent.domains.book_writing.services.llm_service import LLMService
from apps.bfagent.models import BookChapters, BookProjects

logger = logging.getLogger(__name__)


class ChapterStructureHandler:
    """
    Generate detailed chapter structure using LLM from outline

    Input:
    - project_id: int (BookProjects ID)
    - chapter_number: int (which chapter to plan)
    - outline: dict (optional, story outline/beats)
    - previous_chapters: list (optional, summaries of previous chapters)

    Output:
    - structure: dict with:
      - opening: str (how chapter opens)
      - middle: str (what happens in middle)
      - ending: str (how chapter ends)
      - pov_character: str
      - setting: str
      - time_period: str
    - scene_count: int (recommended number of scenes)
    - estimated_word_count: int
    - success: bool
    - usage: dict (LLM usage stats)
    """

    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate chapter structure with LLM"""
        project_id = data.get("project_id")
        chapter_number = data.get("chapter_number")

        if not project_id:
            return {"success": False, "error": "project_id required"}
        if not chapter_number:
            return {"success": False, "error": "chapter_number required"}

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
            "title": project.title,
            "genre": project.genre or "Fiction",
            "premise": getattr(project, "premise", "") or project.description or "",
            "chapter_number": chapter_number,
            "outline": data.get("outline", getattr(project, "outline", {})),
            "previous_chapters": data.get("previous_chapters", []),
        }

        # Get previous chapters from DB if not provided
        if not context["previous_chapters"] and chapter_number > 1:
            try:
                prev_chapters = (
                    BookChapters.objects.filter(
                        project_id=project_id, chapter_number__lt=chapter_number
                    )
                    .order_by("chapter_number")
                    .values("chapter_number", "title", "summary")
                )
                context["previous_chapters"] = list(prev_chapters)
            except:
                pass

        # Build prompt
        prompt = ChapterStructureHandler._build_prompt(context)

        # Generate with LLM
        provider = getattr(settings, "LLM_PROVIDER", "openai")
        model = getattr(settings, "LLM_MODEL", None)
        llm = LLMService(provider=provider, model=model)

        result = llm.generate_chapter_content(
            prompt=prompt, max_tokens=1200, temperature=0.7, quality="balanced"
        )

        if not result["success"]:
            return result

        # Parse structure
        parsed = ChapterStructureHandler._parse_structure(result["content"])

        logger.info(f"Generated structure for chapter {chapter_number} of project {project_id}")

        return {
            "success": True,
            **parsed,
            "chapter_number": chapter_number,
            "raw_content": result["content"],
            "usage": result.get("usage"),
            "cost": llm.calculate_cost(result["usage"]) if result.get("usage") else 0,
        }

    @staticmethod
    def _build_prompt(context: Dict) -> str:
        """Build LLM prompt for chapter structure"""
        parts = [
            "# Task: Plan Chapter Structure",
            "",
            "You are a professional story consultant helping an author plan a chapter in detail.",
            "",
            "## Book Information:",
            f"- **Title:** {context['title']}",
            f"- **Genre:** {context['genre']}",
            f"- **Chapter Number:** {context['chapter_number']}",
            "",
            "## Premise:",
            context["premise"],
        ]

        if context.get("outline"):
            parts.extend(
                [
                    "",
                    "## Story Outline:",
                    str(context["outline"])[:500],  # Limit outline size
                ]
            )

        if context.get("previous_chapters"):
            parts.extend(
                [
                    "",
                    "## Previous Chapters:",
                ]
            )
            for ch in context["previous_chapters"][-3:]:  # Last 3 chapters only
                parts.append(f"- Chapter {ch.get('chapter_number')}: {ch.get('title', 'Untitled')}")
                if ch.get("summary"):
                    parts.append(f"  Summary: {ch['summary'][:200]}")

        parts.extend(
            [
                "",
                "## Your Task:",
                "",
                f"Plan the structure for Chapter {context['chapter_number']}. Provide:",
                "",
                "1. **OPENING** (First few paragraphs)",
                "   - Where/when does the chapter start?",
                "   - What's the opening image or action?",
                "   - What hook grabs the reader?",
                "",
                "2. **MIDDLE** (Bulk of chapter)",
                "   - What happens?",
                "   - What conflicts arise?",
                "   - What character developments occur?",
                "",
                "3. **ENDING** (Last few paragraphs)",
                "   - How does the chapter end?",
                "   - What question or tension is left?",
                "   - What makes readers turn the page?",
                "",
                "4. **POV_CHARACTER**",
                "   - Whose perspective is this chapter from?",
                "",
                "5. **SETTING**",
                "   - Where does this chapter take place?",
                "",
                "6. **TIME_PERIOD**",
                "   - When? (time of day, how long after previous chapter)",
                "",
                "7. **SCENE_COUNT**",
                "   - How many distinct scenes? (typically 2-5)",
                "",
                "8. **ESTIMATED_WORD_COUNT**",
                "   - Target word count (typically 2000-5000)",
                "",
                "## Output Format:",
                "",
                "Return your response as JSON:",
                "",
                "```json",
                "{",
                '  "structure": {',
                '    "opening": "Description of opening...",',
                '    "middle": "Description of middle...",',
                '    "ending": "Description of ending...",',
                '    "pov_character": "Character name",',
                '    "setting": "Where it takes place",',
                '    "time_period": "When/how long after previous"',
                "  },",
                '  "scene_count": 3,',
                '  "estimated_word_count": 3000',
                "}",
                "```",
                "",
                "Make the structure:",
                "- Specific and actionable",
                "- Story-driven (not just plot summary)",
                "- Emotionally engaging",
                "- Builds on previous chapters",
                f"- Appropriate for {context['genre']}",
            ]
        )

        return "\n".join(parts)

    @staticmethod
    def _parse_structure(content: str) -> Dict:
        """Parse structure from LLM response"""
        # Try JSON first
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return data
            except json.JSONDecodeError:
                pass

        # Fallback: Extract sections
        result = {"structure": {}, "scene_count": 3, "estimated_word_count": 3000}

        patterns = {
            "opening": r"(?:OPENING|Opening)[:\s]+(.*?)(?=\n\n|MIDDLE|Middle|$)",
            "middle": r"(?:MIDDLE|Middle)[:\s]+(.*?)(?=\n\n|ENDING|Ending|$)",
            "ending": r"(?:ENDING|Ending)[:\s]+(.*?)(?=\n\n|POV|$)",
            "pov_character": r"(?:POV[_\s]CHARACTER|POV)[:\s]+([^\n]+)",
            "setting": r"(?:SETTING|Setting)[:\s]+([^\n]+)",
            "time_period": r"(?:TIME[_\s]PERIOD|Time)[:\s]+([^\n]+)",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                result["structure"][key] = match.group(1).strip()

        # Extract numbers
        scene_match = re.search(r"scene[_\s]count[:\s]+(\d+)", content, re.IGNORECASE)
        if scene_match:
            result["scene_count"] = int(scene_match.group(1))

        word_match = re.search(r"word[_\s]count[:\s]+(\d+)", content, re.IGNORECASE)
        if word_match:
            result["estimated_word_count"] = int(word_match.group(1))

        return result


class ChapterHookHandler:
    """
    Generate compelling chapter hook using LLM

    Input:
    - project_id: int (BookProjects ID)
    - chapter_number: int
    - chapter_structure: dict (from ChapterStructureHandler)
    - hook_type: str (optional: 'action', 'mystery', 'emotion', 'dialogue')

    Output:
    - hook: str (opening line/paragraph)
    - hook_variations: list of str (3 alternative hooks)
    - hook_analysis: str (why this works)
    - opening_image: str (visual description)
    - success: bool
    - usage: dict (LLM usage stats)
    """

    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate chapter hook with LLM"""
        project_id = data.get("project_id")
        chapter_number = data.get("chapter_number")

        if not project_id:
            return {"success": False, "error": "project_id required"}
        if not chapter_number:
            return {"success": False, "error": "chapter_number required"}

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
            "title": project.title,
            "genre": project.genre or "Fiction",
            "chapter_number": chapter_number,
            "chapter_structure": data.get("chapter_structure", {}),
            "hook_type": data.get("hook_type", "action"),
        }

        # Build prompt
        prompt = ChapterHookHandler._build_prompt(context)

        # Generate with LLM
        provider = getattr(settings, "LLM_PROVIDER", "openai")
        model = getattr(settings, "LLM_MODEL", None)
        llm = LLMService(provider=provider, model=model)

        result = llm.generate_chapter_content(
            prompt=prompt, max_tokens=800, temperature=0.9, quality="fast"  # Short creative task
        )

        if not result["success"]:
            return result

        # Parse hook
        parsed = ChapterHookHandler._parse_hook(result["content"])

        logger.info(f"Generated hook for chapter {chapter_number} of project {project_id}")

        return {
            "success": True,
            **parsed,
            "chapter_number": chapter_number,
            "raw_content": result["content"],
            "usage": result.get("usage"),
            "cost": llm.calculate_cost(result["usage"]) if result.get("usage") else 0,
        }

    @staticmethod
    def _build_prompt(context: Dict) -> str:
        """Build LLM prompt for chapter hook"""
        parts = [
            "# Task: Create Compelling Chapter Hook",
            "",
            "You are a master storyteller crafting the perfect opening for a chapter.",
            "",
            f"## Chapter {context['chapter_number']} Information:",
            f"- **Book:** {context['title']}",
            f"- **Genre:** {context['genre']}",
            f"- **Hook Type:** {context['hook_type']}",
        ]

        if context.get("chapter_structure"):
            parts.extend(
                [
                    "",
                    "## Chapter Plan:",
                    f"- **Opening:** {context['chapter_structure'].get('opening', 'N/A')}",
                    f"- **POV:** {context['chapter_structure'].get('pov_character', 'N/A')}",
                    f"- **Setting:** {context['chapter_structure'].get('setting', 'N/A')}",
                ]
            )

        parts.extend(
            [
                "",
                "## Your Task:",
                "",
                "Create a compelling opening hook (1-2 paragraphs, ~150 words) that:",
                "",
                f"**{context['hook_type'].upper()} Hook Style:**",
            ]
        )

        # Add hook type specific guidance
        if context["hook_type"] == "action":
            parts.append("- Starts with immediate action or movement")
            parts.append("- Drops reader right into the scene")
        elif context["hook_type"] == "mystery":
            parts.append("- Raises a question or creates intrigue")
            parts.append("- Hints at something unknown")
        elif context["hook_type"] == "emotion":
            parts.append("- Connects with character's emotional state")
            parts.append("- Makes reader feel something immediately")
        elif context["hook_type"] == "dialogue":
            parts.append("- Opens with compelling dialogue")
            parts.append("- Character voice shines through")

        parts.extend(
            [
                "",
                "Also provide:",
                "- 3 alternative hook variations",
                "- Analysis of why the main hook is effective",
                "- Description of the opening visual image",
                "",
                "## Output Format:",
                "",
                "Return your response as JSON:",
                "",
                "```json",
                "{",
                '  "hook": "Main hook text (1-2 paragraphs, ~150 words)",',
                '  "hook_variations": [',
                '    "Alternative version 1",',
                '    "Alternative version 2",',
                '    "Alternative version 3"',
                "  ],",
                '  "hook_analysis": "Why this hook is effective",',
                '  "opening_image": "Visual description of opening scene"',
                "}",
                "```",
                "",
                "Make the hook:",
                "- Immediately engaging",
                "- Show, don't tell",
                "- Establish tone and voice",
                "- Make readers want to continue",
                f"- Perfect for {context['genre']}",
            ]
        )

        return "\n".join(parts)

    @staticmethod
    def _parse_hook(content: str) -> Dict:
        """Parse hook from LLM response"""
        # Try JSON first
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return data
            except json.JSONDecodeError:
                pass

        # Fallback: Use first paragraphs as hook
        paragraphs = content.split("\n\n")

        result = {
            "hook": paragraphs[0] if paragraphs else content[:300],
            "hook_variations": paragraphs[1:4] if len(paragraphs) > 1 else [],
            "hook_analysis": "Hook creates immediate engagement",
            "opening_image": "Opening scene draws reader in",
        }

        return result


class ChapterGoalHandler:
    """
    Define clear chapter goal and plot progression using LLM

    Input:
    - project_id: int (BookProjects ID)
    - chapter_number: int
    - chapter_structure: dict (from ChapterStructureHandler)
    - story_goal: str (optional, overall story objective)

    Output:
    - chapter_goal: str (what must be accomplished)
    - plot_progression: str (how story advances)
    - character_development: str (how characters change)
    - conflicts: list of str (conflicts in this chapter)
    - stakes: str (what's at risk)
    - next_chapter_setup: str (what this sets up)
    - success: bool
    - usage: dict (LLM usage stats)
    """

    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Define chapter goal with LLM"""
        project_id = data.get("project_id")
        chapter_number = data.get("chapter_number")

        if not project_id:
            return {"success": False, "error": "project_id required"}
        if not chapter_number:
            return {"success": False, "error": "chapter_number required"}

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
            "title": project.title,
            "genre": project.genre or "Fiction",
            "premise": getattr(project, "premise", "") or project.description or "",
            "chapter_number": chapter_number,
            "chapter_structure": data.get("chapter_structure", {}),
            "story_goal": data.get("story_goal", ""),
        }

        # Build prompt
        prompt = ChapterGoalHandler._build_prompt(context)

        # Generate with LLM
        provider = getattr(settings, "LLM_PROVIDER", "openai")
        model = getattr(settings, "LLM_MODEL", None)
        llm = LLMService(provider=provider, model=model)

        result = llm.generate_chapter_content(
            prompt=prompt, max_tokens=1000, temperature=0.7, quality="fast"  # Analytical task
        )

        if not result["success"]:
            return result

        # Parse goal
        parsed = ChapterGoalHandler._parse_goal(result["content"])

        logger.info(f"Defined goal for chapter {chapter_number} of project {project_id}")

        return {
            "success": True,
            **parsed,
            "chapter_number": chapter_number,
            "raw_content": result["content"],
            "usage": result.get("usage"),
            "cost": llm.calculate_cost(result["usage"]) if result.get("usage") else 0,
        }

    @staticmethod
    def _build_prompt(context: Dict) -> str:
        """Build LLM prompt for chapter goal"""
        parts = [
            "# Task: Define Chapter Goal & Purpose",
            "",
            "You are a story consultant helping an author understand what this chapter needs to accomplish.",
            "",
            "## Book Information:",
            f"- **Title:** {context['title']}",
            f"- **Genre:** {context['genre']}",
            f"- **Chapter Number:** {context['chapter_number']}",
            "",
            "## Story Premise:",
            context["premise"],
        ]

        if context.get("story_goal"):
            parts.extend(
                [
                    "",
                    "## Overall Story Goal:",
                    context["story_goal"],
                ]
            )

        if context.get("chapter_structure"):
            parts.extend(
                [
                    "",
                    "## This Chapter's Structure:",
                    f"- **Opening:** {context['chapter_structure'].get('opening', 'N/A')[:200]}",
                    f"- **Middle:** {context['chapter_structure'].get('middle', 'N/A')[:200]}",
                    f"- **Ending:** {context['chapter_structure'].get('ending', 'N/A')[:200]}",
                ]
            )

        parts.extend(
            [
                "",
                "## Your Task:",
                "",
                f"Define what Chapter {context['chapter_number']} must accomplish. Provide:",
                "",
                "1. **CHAPTER_GOAL**",
                "   - What is the specific goal or objective of this chapter?",
                "   - What must happen by the end?",
                "",
                "2. **PLOT_PROGRESSION**",
                "   - How does the plot advance in this chapter?",
                "   - What new information is revealed?",
                "   - What questions are answered/raised?",
                "",
                "3. **CHARACTER_DEVELOPMENT**",
                "   - How do characters change or grow?",
                "   - What do they learn?",
                "   - What relationships evolve?",
                "",
                "4. **CONFLICTS**",
                "   - What conflicts arise or continue? (list 2-3)",
                "   - External and/or internal",
                "",
                "5. **STAKES**",
                "   - What's at risk in this chapter?",
                "   - Why should readers care?",
                "",
                "6. **NEXT_CHAPTER_SETUP**",
                "   - What does this chapter set up for the next?",
                "   - What question makes readers turn the page?",
                "",
                "## Output Format:",
                "",
                "Return your response as JSON:",
                "",
                "```json",
                "{",
                '  "chapter_goal": "What this chapter must accomplish",',
                '  "plot_progression": "How story advances",',
                '  "character_development": "How characters change",',
                '  "conflicts": [',
                '    "Conflict 1",',
                '    "Conflict 2"',
                "  ],",
                '  "stakes": "What is at risk",',
                '  "next_chapter_setup": "What this sets up for next chapter"',
                "}",
                "```",
                "",
                "Make the goal:",
                "- Specific and measurable",
                "- Story-driven (not just plot points)",
                "- Connected to overall story arc",
                f"- Appropriate for {context['genre']}",
                "- Clear about cause and effect",
            ]
        )

        return "\n".join(parts)

    @staticmethod
    def _parse_goal(content: str) -> Dict:
        """Parse goal from LLM response"""
        # Try JSON first
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return data
            except json.JSONDecodeError:
                pass

        # Fallback: Extract sections
        result = {
            "chapter_goal": "",
            "plot_progression": "",
            "character_development": "",
            "conflicts": [],
            "stakes": "",
            "next_chapter_setup": "",
        }

        patterns = {
            "chapter_goal": r"(?:CHAPTER[_\s]GOAL|Goal)[:\s]+(.*?)(?=\n\n|PLOT|$)",
            "plot_progression": r"(?:PLOT[_\s]PROGRESSION|Plot)[:\s]+(.*?)(?=\n\n|CHARACTER|$)",
            "character_development": r"(?:CHARACTER[_\s]DEVELOPMENT|Character)[:\s]+(.*?)(?=\n\n|CONFLICTS|$)",
            "stakes": r"(?:STAKES|Stakes)[:\s]+(.*?)(?=\n\n|NEXT|$)",
            "next_chapter_setup": r"(?:NEXT[_\s]CHAPTER|Setup)[:\s]+(.*?)(?=\n\n|$)",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                result[key] = match.group(1).strip()

        # Extract conflicts list
        conflicts_section = re.search(
            r"(?:CONFLICTS|Conflicts)[:\s]+(.*?)(?=\n\n|STAKES|$)",
            content,
            re.DOTALL | re.IGNORECASE,
        )
        if conflicts_section:
            conflicts_text = conflicts_section.group(1)
            # Find list items
            conflicts = re.findall(r"[-•*]\s*([^\n]+)", conflicts_text)
            result["conflicts"] = conflicts if conflicts else [conflicts_text.strip()]

        return result
