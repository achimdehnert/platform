"""
Enhanced Outline Handlers with LLM Integration
Improved storyline/outline generators using Prompt Factory
"""

import json
import logging
import re
from typing import Any, Dict, List

from django.conf import settings

from apps.bfagent.domains.book_writing.services.llm_service import LLMService
from apps.bfagent.models import BookProjects

logger = logging.getLogger(__name__)


class EnhancedSaveTheCatOutlineHandler:
    """
    Enhanced Save the Cat Beat Sheet with LLM customization

    Features:
    - LLM mode: AI-customized beats based on premise
    - Static mode: Original hardcoded beats (fallback)
    - Premise-aware descriptions
    - Cost tracking

    Input:
    - project_id: int (BookProjects ID)
    - title: str (override)
    - genre: str (override)
    - premise: str (override)
    - num_chapters: int (default 15)
    - use_llm: bool (default False)

    Output:
    - outline: str (markdown formatted)
    - beats: list (structured beat data)
    - chapter_count: int
    - framework: str
    - customized: bool (whether LLM was used)
    """

    # Static beats (fallback)
    STATIC_BEATS = [
        {
            "name": "Opening Image",
            "position": 0.0,
            "description": "Snapshot before transformation",
            "guidance": "Show protagonist in current world",
        },
        {
            "name": "Theme Stated",
            "position": 0.05,
            "description": "Question or theme introduced",
            "guidance": "Side character hints at lesson",
        },
        {
            "name": "Set-Up",
            "position": 0.08,
            "description": "World and what is missing",
            "guidance": "Establish characters and world",
        },
        {
            "name": "Catalyst",
            "position": 0.10,
            "description": "Life-changing event",
            "guidance": "Event that changes everything",
        },
        {
            "name": "Debate",
            "position": 0.17,
            "description": "Should hero act? Doubts and fears",
            "guidance": "Hero hesitates, shows fear",
        },
        {
            "name": "Break into Two",
            "position": 0.25,
            "description": "Hero decides to act",
            "guidance": "Decision made, enter Act 2",
        },
        {
            "name": "B Story",
            "position": 0.30,
            "description": "New relationship explores theme",
            "guidance": "Introduce mentor or love interest",
        },
        {
            "name": "Fun and Games",
            "position": 0.40,
            "description": "Promise of premise",
            "guidance": "Hero explores new world",
        },
        {
            "name": "Midpoint",
            "position": 0.50,
            "description": "False victory or defeat",
            "guidance": "Seems great or all is lost",
        },
        {
            "name": "Bad Guys Close In",
            "position": 0.60,
            "description": "Antagonists gain upper hand",
            "guidance": "Problems pile up",
        },
        {
            "name": "All Is Lost",
            "position": 0.75,
            "description": "Lowest point",
            "guidance": "Worst moment, symbolic death",
        },
        {
            "name": "Dark Night of Soul",
            "position": 0.80,
            "description": "Hero at rock bottom",
            "guidance": "Darkness before enlightenment",
        },
        {
            "name": "Break into Three",
            "position": 0.83,
            "description": "Solution found",
            "guidance": "Hero finds answer",
        },
        {
            "name": "Finale",
            "position": 0.92,
            "description": "Hero applies what learned",
            "guidance": "Final confrontation, show growth",
        },
        {
            "name": "Final Image",
            "position": 1.0,
            "description": "Mirror of Opening Image",
            "guidance": "Show transformation",
        },
    ]

    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate Save the Cat outline"""
        project_id = data.get("project_id")
        title = data.get("title", "Untitled")
        genre = data.get("genre", "Fiction")
        premise = data.get("premise", "")
        num_chapters = data.get("num_chapters", 15)
        use_llm = data.get("use_llm", False)

        # Try to load from project if ID provided
        if project_id:
            try:
                project = BookProjects.objects.get(id=project_id)
                title = title or project.title
                genre = genre or project.genre
                premise = premise or project.story_premise or project.description
            except BookProjects.DoesNotExist:
                pass

        # Decide mode
        if use_llm and premise:
            api_key_available = getattr(settings, "OPENAI_API_KEY", None) or getattr(
                settings, "ANTHROPIC_API_KEY", None
            )

            if api_key_available:
                return EnhancedSaveTheCatOutlineHandler._generate_with_llm(
                    title, genre, premise, num_chapters
                )
            else:
                logger.warning("LLM requested but no API key - falling back to static")

        # Static mode
        return EnhancedSaveTheCatOutlineHandler._generate_static(
            title, genre, premise, num_chapters
        )

    @staticmethod
    def _generate_with_llm(
        title: str, genre: str, premise: str, num_chapters: int
    ) -> Dict[str, Any]:
        """Generate customized beats using LLM"""
        # Build prompt
        prompt = EnhancedSaveTheCatOutlineHandler._build_llm_prompt(
            title, genre, premise, num_chapters
        )

        # Generate with LLM
        provider = getattr(settings, "LLM_PROVIDER", "openai")
        model = getattr(settings, "LLM_MODEL", None)
        llm = LLMService(provider=provider, model=model)

        result = llm.generate_chapter_content(
            prompt=prompt, max_tokens=2500, temperature=0.7, quality="balanced"  # Outline structure
        )

        if not result["success"]:
            logger.error(f"LLM generation failed: {result.get('error')}")
            # Fallback to static
            return EnhancedSaveTheCatOutlineHandler._generate_static(
                title, genre, premise, num_chapters
            )

        # Parse beats
        beats = EnhancedSaveTheCatOutlineHandler._parse_llm_beats(result["content"])

        if not beats:
            logger.warning("Failed to parse LLM beats - falling back to static")
            return EnhancedSaveTheCatOutlineHandler._generate_static(
                title, genre, premise, num_chapters
            )

        # Create outline
        outline = EnhancedSaveTheCatOutlineHandler._format_outline(
            title, genre, premise, beats, num_chapters, customized=True
        )

        cost = llm.calculate_cost(result["usage"]) if result.get("usage") else 0

        logger.info(f"Generated LLM-customized Save the Cat outline (cost: ${cost:.4f})")

        return {
            "success": True,
            "outline": outline,
            "beats": beats,
            "chapter_count": num_chapters,
            "framework": "Save the Cat",
            "customized": True,
            "usage": result.get("usage"),
            "cost": cost,
        }

    @staticmethod
    def _generate_static(title: str, genre: str, premise: str, num_chapters: int) -> Dict[str, Any]:
        """Generate using static beats"""
        beats = EnhancedSaveTheCatOutlineHandler.STATIC_BEATS

        outline = EnhancedSaveTheCatOutlineHandler._format_outline(
            title, genre, premise, beats, num_chapters, customized=False
        )

        logger.info(f"Generated static Save the Cat outline with {num_chapters} chapters")

        return {
            "success": True,
            "outline": outline,
            "beats": beats,
            "chapter_count": num_chapters,
            "framework": "Save the Cat",
            "customized": False,
        }

    @staticmethod
    def _build_llm_prompt(title: str, genre: str, premise: str, num_chapters: int) -> str:
        """Build prompt for LLM customization"""
        return f"""# Task: Customize Save the Cat Beats

## Story Information:
- **Title:** {title}
- **Genre:** {genre}
- **Chapters:** {num_chapters}

## Premise:
{premise}

## Your Task:

Customize the 15 Save the Cat beats for this specific story. For each beat:

1. **name** - Keep the standard beat name
2. **description** - Adapt description to this story (2-3 sentences)
3. **guidance** - Specific guidance for this story
4. **example** - 1-2 sentence example of what could happen

Return as JSON array with this structure:

```json
[
  {{
    "name": "Opening Image",
    "description": "Adapted description for {title}...",
    "guidance": "Specific guidance...",
    "example": "Example event..."
  }},
  ... (15 beats total)
]
```

Ensure all 15 beats are included:
1. Opening Image (0%)
2. Theme Stated (5%)
3. Set-Up (8%)
4. Catalyst (10%)
5. Debate (17%)
6. Break into Two (25%)
7. B Story (30%)
8. Fun and Games (40%)
9. Midpoint (50%)
10. Bad Guys Close In (60%)
11. All Is Lost (75%)
12. Dark Night of the Soul (80%)
13. Break into Three (83%)
14. Finale (92%)
15. Final Image (100%)

Make descriptions specific to the premise and genre."""

    @staticmethod
    def _parse_llm_beats(content: str) -> List[Dict]:
        """Parse beats from LLM response"""
        # Try JSON first
        json_match = re.search(r"```json\s*(\[.*?\])\s*```", content, re.DOTALL)
        if json_match:
            try:
                beats = json.loads(json_match.group(1))
                if isinstance(beats, list) and len(beats) == 15:
                    # Add positions
                    positions = [
                        0.0,
                        0.05,
                        0.08,
                        0.10,
                        0.17,
                        0.25,
                        0.30,
                        0.40,
                        0.50,
                        0.60,
                        0.75,
                        0.80,
                        0.83,
                        0.92,
                        1.0,
                    ]
                    for i, beat in enumerate(beats):
                        beat["position"] = positions[i]
                    return beats
            except json.JSONDecodeError:
                pass

        # Try finding JSON array without markers
        json_match = re.search(r'\[[\s\S]*"name"[\s\S]*\]', content)
        if json_match:
            try:
                beats = json.loads(json_match.group(0))
                if isinstance(beats, list) and len(beats) == 15:
                    positions = [
                        0.0,
                        0.05,
                        0.08,
                        0.10,
                        0.17,
                        0.25,
                        0.30,
                        0.40,
                        0.50,
                        0.60,
                        0.75,
                        0.80,
                        0.83,
                        0.92,
                        1.0,
                    ]
                    for i, beat in enumerate(beats):
                        beat["position"] = positions[i]
                    return beats
            except json.JSONDecodeError:
                pass

        return []

    @staticmethod
    def _format_outline(
        title: str, genre: str, premise: str, beats: List[Dict], num_chapters: int, customized: bool
    ) -> str:
        """Format outline as markdown"""
        lines = []
        lines.append(f"# {title} - Story Outline")
        lines.append(
            f"**Framework:** Save the Cat Beat Sheet {'(AI-Customized)' if customized else ''}"
        )
        lines.append(f"**Genre:** {genre}")
        lines.append(f"**Premise:** {premise}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Map chapters to beats
        for i in range(1, num_chapters + 1):
            position = i / num_chapters

            # Find closest beat
            beat = min(beats, key=lambda b: abs(b["position"] - position))

            lines.append(f"## Chapter {i}: {beat['name']}")
            lines.append(f"**Story Position:** {int(position * 100)}%")
            lines.append(f"**Description:** {beat['description']}")
            lines.append(f"**Guidance:** {beat['guidance']}")

            if "example" in beat:
                lines.append(f"**Example:** {beat['example']}")

            lines.append("")

        return "\n".join(lines)


class HerosJourneyOutlineHandler:
    """
    Hero's Journey (12 Stages) outline generator

    Based on Joseph Campbell's monomyth structure.
    Ideal for fantasy, adventure, and transformation stories.

    Input:
    - project_id: int (optional)
    - title: str
    - genre: str
    - premise: str
    - num_chapters: int (default 12)

    Output:
    - outline: str
    - stages: list
    - chapter_count: int
    - framework: str
    """

    JOURNEY_STAGES = [
        {
            "name": "Ordinary World",
            "act": 1,
            "position": 0.0,
            "description": "Hero in normal life before adventure",
        },
        {
            "name": "Call to Adventure",
            "act": 1,
            "position": 0.08,
            "description": "Challenge or quest is presented",
        },
        {
            "name": "Refusal of the Call",
            "act": 1,
            "position": 0.17,
            "description": "Hero hesitates or refuses",
        },
        {
            "name": "Meeting the Mentor",
            "act": 1,
            "position": 0.21,
            "description": "Guidance from experienced figure",
        },
        {
            "name": "Crossing the Threshold",
            "act": 2,
            "position": 0.25,
            "description": "Hero commits to adventure",
        },
        {
            "name": "Tests, Allies, Enemies",
            "act": 2,
            "position": 0.38,
            "description": "Hero faces challenges, forms relationships",
        },
        {
            "name": "Approach to Inmost Cave",
            "act": 2,
            "position": 0.50,
            "description": "Preparation for major challenge",
        },
        {
            "name": "Ordeal",
            "act": 2,
            "position": 0.58,
            "description": "Hero faces death or greatest fear",
        },
        {
            "name": "Reward",
            "act": 2,
            "position": 0.67,
            "description": "Hero survives and gains reward",
        },
        {
            "name": "The Road Back",
            "act": 3,
            "position": 0.75,
            "description": "Hero returns but danger follows",
        },
        {
            "name": "Resurrection",
            "act": 3,
            "position": 0.88,
            "description": "Final test, hero transformed",
        },
        {
            "name": "Return with Elixir",
            "act": 3,
            "position": 1.0,
            "description": "Hero returns changed, brings benefit",
        },
    ]

    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate Hero's Journey outline"""
        project_id = data.get("project_id")
        title = data.get("title", "Untitled")
        genre = data.get("genre", "Adventure")
        premise = data.get("premise", "")
        num_chapters = data.get("num_chapters", 12)

        # Load from project if ID provided
        if project_id:
            try:
                project = BookProjects.objects.get(id=project_id)
                title = title or project.title
                genre = genre or project.genre
                premise = premise or project.story_premise or project.description
            except BookProjects.DoesNotExist:
                pass

        # Generate outline
        lines = []
        lines.append(f"# {title} - The Hero's Journey")
        lines.append(f"**Framework:** Hero's Journey (12 Stages)")
        lines.append(f"**Genre:** {genre}")
        lines.append(f"**Premise:** {premise}")
        lines.append("")
        lines.append("---")
        lines.append("")

        stages_output = []

        # Map chapters to stages
        for i in range(1, num_chapters + 1):
            position = i / num_chapters

            # Find closest stage
            stage = min(
                HerosJourneyOutlineHandler.JOURNEY_STAGES,
                key=lambda s: abs(s["position"] - position),
            )

            lines.append(f"## Chapter {i}: {stage['name']}")
            lines.append(f"**Act:** {stage['act']}")
            lines.append(f"**Position:** {int(position * 100)}%")
            lines.append(f"**Stage:** {stage['description']}")
            lines.append("")

            stages_output.append(
                {
                    "chapter": i,
                    "stage_name": stage["name"],
                    "act": stage["act"],
                    "position": position,
                    "description": stage["description"],
                }
            )

        outline = "\n".join(lines)

        logger.info(f"Generated Hero's Journey outline with {num_chapters} chapters")

        return {
            "success": True,
            "outline": outline,
            "stages": stages_output,
            "chapter_count": num_chapters,
            "framework": "Hero's Journey",
        }


class KishotenketsuOutlineHandler:
    """
    Kishōtenketsu Outline Generator (Japanese 4-Act Structure)

    Traditional Japanese narrative structure WITHOUT direct conflict!
    Perfect for character-driven, contemplative, literary fiction.

    Structure:
    - Ki (Introduction): Setup characters and situation
    - Shō (Development): Develop relationships and nuances
    - Ten (Twist): Unexpected turn or shift in perspective
    - Ketsu (Conclusion): Harmonious resolution, new understanding

    Input:
    - project_id: int (optional)
    - title: str
    - genre: str
    - premise: str
    - num_chapters: int (default 10-12)

    Output:
    - outline: str
    - acts: list
    - chapter_count: int
    - framework: str
    """

    ACT_STRUCTURE = [
        {
            "number": 1,
            "name": "Ki (Introduction)",
            "name_en": "Introduction",
            "position": 0.0,
            "percentage": 25,
            "description": "Introduce characters, setting, and situation",
            "guidance": "Establish normal world and relationships",
        },
        {
            "number": 2,
            "name": "Shō (Development)",
            "name_en": "Development",
            "position": 0.25,
            "percentage": 25,
            "description": "Develop character relationships and explore themes",
            "guidance": "Deepen understanding, show nuances, build emotional connections",
        },
        {
            "number": 3,
            "name": "Ten (Twist)",
            "name_en": "Twist",
            "position": 0.50,
            "percentage": 25,
            "description": "Unexpected turn or shift in perspective",
            "guidance": "Introduce new element or viewpoint that changes understanding",
        },
        {
            "number": 4,
            "name": "Ketsu (Conclusion)",
            "name_en": "Conclusion",
            "position": 0.75,
            "percentage": 25,
            "description": "Harmonious resolution and new understanding",
            "guidance": "Synthesize elements, show transformation, find harmony",
        },
    ]

    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate Kishōtenketsu outline"""
        project_id = data.get("project_id")
        title = data.get("title", "Untitled")
        genre = data.get("genre", "Literary Fiction")
        premise = data.get("premise", "")
        num_chapters = data.get("num_chapters", 12)

        # Load from project
        if project_id:
            try:
                project = BookProjects.objects.get(id=project_id)
                title = title or project.title
                genre = genre or project.genre
                premise = premise or project.story_premise or project.description
            except BookProjects.DoesNotExist:
                pass

        lines = []
        lines.append(f"# {title} - Kishōtenketsu Structure")
        lines.append(f"**Framework:** Kishōtenketsu (Japanese 4-Act Structure)")
        lines.append(f"**Genre:** {genre}")
        lines.append(f"**Premise:** {premise}")
        lines.append("")
        lines.append(
            "*Note: This structure avoids direct conflict, focusing on harmony and perspective shifts.*"
        )
        lines.append("")
        lines.append("---")
        lines.append("")

        acts_output = []
        chapters_per_act = num_chapters // 4

        for i in range(1, num_chapters + 1):
            # Determine which act
            act_index = min((i - 1) // chapters_per_act, 3)
            act = KishotenketsuOutlineHandler.ACT_STRUCTURE[act_index]

            # Chapter position within story
            position = i / num_chapters

            lines.append(f"## Chapter {i}: {act['name']}")
            lines.append(f"**Act:** {act['number']} - {act['name_en']}")
            lines.append(f"**Position:** {int(position * 100)}%")
            lines.append(f"**Focus:** {act['description']}")
            lines.append(f"**Guidance:** {act['guidance']}")
            lines.append("")

            acts_output.append(
                {
                    "chapter": i,
                    "act": act["number"],
                    "act_name": act["name"],
                    "position": position,
                    "description": act["description"],
                }
            )

        outline = "\n".join(lines)

        logger.info(f"Generated Kishōtenketsu outline with {num_chapters} chapters")

        return {
            "success": True,
            "outline": outline,
            "acts": acts_output,
            "chapter_count": num_chapters,
            "framework": "Kishōtenketsu",
        }


class SevenPointOutlineHandler:
    """
    7-Point Structure Outline Generator (Dan Wells)

    Highly structured approach perfect for genre fiction.
    Based on mirror structure: Hook reflects Resolution, etc.

    Structure:
    1. Hook - Starting state
    2. Plot Turn 1 - Call to action, enter new world
    3. Pinch Point 1 - Apply pressure, show antagonist force
    4. Midpoint - Shift from reaction to action
    5. Pinch Point 2 - Apply more pressure
    6. Plot Turn 2 - Obtain final piece to resolve
    7. Resolution - Final state (mirror of Hook)

    Input:
    - project_id: int (optional)
    - title: str
    - genre: str
    - premise: str
    - num_chapters: int (default 7-14)

    Output:
    - outline: str
    - points: list
    - chapter_count: int
    - framework: str
    """

    STORY_POINTS = [
        {
            "number": 1,
            "name": "Hook",
            "position": 0.0,
            "description": "Starting state - character before change",
            "guidance": "Show protagonist in their normal world, hint at flaw or need",
            "mirror": 7,  # Mirrors Resolution
        },
        {
            "number": 2,
            "name": "Plot Turn 1",
            "position": 0.17,
            "description": "Call to action - enter new situation",
            "guidance": "Something happens that forces character into new circumstances",
            "mirror": 6,
        },
        {
            "number": 3,
            "name": "Pinch Point 1",
            "position": 0.33,
            "description": "Apply pressure - antagonist force shown",
            "guidance": "Show strength of opposition, raise stakes, character still reactive",
            "mirror": 5,
        },
        {
            "number": 4,
            "name": "Midpoint",
            "position": 0.50,
            "description": "Move from reaction to action",
            "guidance": "Character makes choice to take control, shifts from victim to hero",
            "mirror": 4,  # Mirrors itself
        },
        {
            "number": 5,
            "name": "Pinch Point 2",
            "position": 0.67,
            "description": "Apply more pressure - opposition doubles down",
            "guidance": "Antagonist fights back harder, all seems lost",
            "mirror": 3,
        },
        {
            "number": 6,
            "name": "Plot Turn 2",
            "position": 0.83,
            "description": "Obtain final piece needed to resolve",
            "guidance": "Character gains knowledge, tool, or realization for final confrontation",
            "mirror": 2,
        },
        {
            "number": 7,
            "name": "Resolution",
            "position": 1.0,
            "description": "Final state - character after change",
            "guidance": "Mirror of Hook, show transformation, resolve plot",
            "mirror": 1,
        },
    ]

    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate 7-Point Structure outline"""
        project_id = data.get("project_id")
        title = data.get("title", "Untitled")
        genre = data.get("genre", "Fiction")
        premise = data.get("premise", "")
        num_chapters = data.get("num_chapters", 14)  # 2 chapters per point

        # Load from project
        if project_id:
            try:
                project = BookProjects.objects.get(id=project_id)
                title = title or project.title
                genre = genre or project.genre
                premise = premise or project.story_premise or project.description
            except BookProjects.DoesNotExist:
                pass

        lines = []
        lines.append(f"# {title} - 7-Point Structure")
        lines.append(f"**Framework:** 7-Point Structure (Dan Wells)")
        lines.append(f"**Genre:** {genre}")
        lines.append(f"**Premise:** {premise}")
        lines.append("")
        lines.append("*Note: This structure uses mirror symmetry - each point reflects another.*")
        lines.append("")
        lines.append("---")
        lines.append("")

        points_output = []

        for i in range(1, num_chapters + 1):
            # Map chapter to story point
            position = i / num_chapters

            # Find closest story point
            point = min(
                SevenPointOutlineHandler.STORY_POINTS, key=lambda p: abs(p["position"] - position)
            )

            lines.append(f"## Chapter {i}: {point['name']}")
            lines.append(f"**Point:** {point['number']}/7")
            lines.append(f"**Position:** {int(position * 100)}%")
            lines.append(f"**Description:** {point['description']}")
            lines.append(f"**Guidance:** {point['guidance']}")
            lines.append(f"**Mirrors:** Point {point['mirror']}")
            lines.append("")

            points_output.append(
                {
                    "chapter": i,
                    "point": point["number"],
                    "point_name": point["name"],
                    "position": position,
                    "description": point["description"],
                    "mirrors": point["mirror"],
                }
            )

        outline = "\n".join(lines)

        logger.info(f"Generated 7-Point Structure outline with {num_chapters} chapters")

        return {
            "success": True,
            "outline": outline,
            "points": points_output,
            "chapter_count": num_chapters,
            "framework": "7-Point Structure",
        }


class ThreeActOutlineHandler:
    """
    Three-Act Structure outline generator

    Classic dramatic structure: Setup → Confrontation → Resolution
    Simple and flexible for any genre.

    Input:
    - project_id: int (optional)
    - title: str
    - genre: str
    - premise: str
    - num_chapters: int (default 9-12)

    Output:
    - outline: str
    - acts: list
    - chapter_count: int
    - framework: str
    """

    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate Three-Act outline"""
        project_id = data.get("project_id")
        title = data.get("title", "Untitled")
        genre = data.get("genre", "Fiction")
        premise = data.get("premise", "")
        num_chapters = data.get("num_chapters", 10)

        # Load from project
        if project_id:
            try:
                project = BookProjects.objects.get(id=project_id)
                title = title or project.title
                genre = genre or project.genre
                premise = premise or project.story_premise or project.description
            except BookProjects.DoesNotExist:
                pass

        # Calculate act breakpoints
        act1_end = int(num_chapters * 0.25)
        act2_end = int(num_chapters * 0.75)

        lines = []
        lines.append(f"# {title} - Three-Act Structure")
        lines.append(f"**Framework:** Three-Act Structure")
        lines.append(f"**Genre:** {genre}")
        lines.append(f"**Premise:** {premise}")
        lines.append("")
        lines.append("---")
        lines.append("")

        acts_output = []

        for i in range(1, num_chapters + 1):
            # Determine act and beat
            if i <= act1_end:
                act = 1
                beat = ThreeActOutlineHandler._get_act1_beat(i, act1_end)
            elif i <= act2_end:
                act = 2
                beat = ThreeActOutlineHandler._get_act2_beat(i - act1_end, act2_end - act1_end)
            else:
                act = 3
                beat = ThreeActOutlineHandler._get_act3_beat(i - act2_end, num_chapters - act2_end)

            lines.append(f"## Chapter {i}: {beat['name']}")
            lines.append(f"**Act:** {act} - {beat['act_name']}")
            lines.append(f"**Beat:** {beat['description']}")
            lines.append(f"**Focus:** {beat['guidance']}")
            lines.append("")

            acts_output.append(
                {
                    "chapter": i,
                    "act": act,
                    "beat_name": beat["name"],
                    "description": beat["description"],
                }
            )

        outline = "\n".join(lines)

        logger.info(f"Generated Three-Act outline with {num_chapters} chapters")

        return {
            "success": True,
            "outline": outline,
            "acts": acts_output,
            "chapter_count": num_chapters,
            "framework": "Three-Act Structure",
        }

    @staticmethod
    def _get_act1_beat(chapter: int, act1_length: int) -> Dict[str, str]:
        """Get beat for Act 1 chapter"""
        position = chapter / act1_length

        if position < 0.3:
            return {
                "name": "Opening",
                "act_name": "Setup",
                "description": "Introduce protagonist and their world",
                "guidance": "Establish normal life, hint at dissatisfaction",
            }
        elif position < 0.6:
            return {
                "name": "Inciting Incident",
                "act_name": "Setup",
                "description": "Event disrupts status quo",
                "guidance": "Present challenge or opportunity",
            }
        else:
            return {
                "name": "Plot Point 1",
                "act_name": "Setup",
                "description": "Protagonist commits to new direction",
                "guidance": "Lock into Act 2, no going back",
            }

    @staticmethod
    def _get_act2_beat(chapter: int, act2_length: int) -> Dict[str, str]:
        """Get beat for Act 2 chapter"""
        position = chapter / act2_length

        if position < 0.4:
            return {
                "name": "Rising Action",
                "act_name": "Confrontation",
                "description": "Obstacles increase, stakes rise",
                "guidance": "Hero tries and fails, learns lessons",
            }
        elif position < 0.6:
            return {
                "name": "Midpoint",
                "act_name": "Confrontation",
                "description": "Major revelation or reversal",
                "guidance": "Shift from reaction to action",
            }
        else:
            return {
                "name": "Plot Point 2",
                "act_name": "Confrontation",
                "description": "Lowest point, all seems lost",
                "guidance": "Force hero to make final choice",
            }

    @staticmethod
    def _get_act3_beat(chapter: int, act3_length: int) -> Dict[str, str]:
        """Get beat for Act 3 chapter"""
        position = chapter / act3_length

        if position < 0.5:
            return {
                "name": "Climax",
                "act_name": "Resolution",
                "description": "Final confrontation",
                "guidance": "Hero uses what they learned",
            }
        elif position < 0.8:
            return {
                "name": "Falling Action",
                "act_name": "Resolution",
                "description": "Aftermath of climax",
                "guidance": "Show consequences, tie up threads",
            }
        else:
            return {
                "name": "Resolution",
                "act_name": "Resolution",
                "description": "New normal established",
                "guidance": "Show how protagonist has changed",
            }
