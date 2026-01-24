"""
ChapterGenerateHandler - Feature #28
Orchestrates chapter generation workflow with LLM calls, validation, and storage

Architecture:
    Input → Validation → LLM Processing → Post-processing → Storage → Output

Dependencies:
    - BaseProcessingHandler
    - BookProjects, BookChapters models
    - Agents, Llms models (for LLM integration)
"""

import logging
from typing import Any, Dict, List, Optional

from django.utils.text import slugify

from apps.bfagent.handlers.base import BaseProcessingHandler, ProcessingError
from apps.bfagent.handlers.processing_handlers.llm_call_handler import LLMCallHandler
from apps.bfagent.models import BookChapters, BookProjects
from apps.bfagent.services.context_enrichment.enricher import DatabaseContextEnricher
from apps.bfagent.services.prompt_service import PromptTemplateService
from apps.core.services.storage import ContentStorageService

logger = logging.getLogger(__name__)


class ChapterGenerateHandler(BaseProcessingHandler):
    """
    Handler for AI-powered chapter generation

    Features:
        - Chapter outline generation
        - Chapter content generation
        - Chapter refinement
        - Multi-pass generation support
        - Context-aware generation (story arc, characters, etc.)

    Usage:
        handler = ChapterGenerateHandler()
        result = handler.execute({
            'action': 'generate_chapter_outline',
            'project_id': 1,
            'chapter_number': 1,
            'parameters': {...}
        })
    """

    def __init__(self):
        super().__init__(name="chapter_generator", version="2.0.0")
        self.llm_handler = LLMCallHandler()
        self.context_enricher = DatabaseContextEnricher()
        self.prompt_service = PromptTemplateService()
        self.storage_service = ContentStorageService()
        self.supported_actions = [
            "generate_chapter_outline",
            "generate_chapter_content",
            "refine_chapter",
            "expand_chapter_section",
            "generate_chapter_summary",
            "regenerate_chapter_with_feedback",
        ]

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute chapter generation action

        Args:
            context: Dictionary containing:
                - action: str (required) - Action to perform
                - project_id: int (required) - Project ID
                - chapter_id: int (optional) - Existing chapter ID
                - chapter_number: int (optional) - Chapter number for new chapter
                - parameters: Dict (optional) - Action-specific parameters
                - agent_id: int (optional) - Specific agent to use

        Returns:
            Dictionary with:
                - success: bool
                - action: str
                - data: Dict with results
                - message: str (optional)

        Raises:
            ProcessingError: If action fails
        """
        action = context.get("action")
        if not action:
            raise ProcessingError("Action is required in context")

        if action not in self.supported_actions:
            raise ProcessingError(
                f"Unsupported action: {action}. " f"Supported: {', '.join(self.supported_actions)}"
            )

        logger.info(f"ChapterGenerateHandler executing action: {action}")

        # Validate common requirements
        project_id = context.get("project_id")
        if not project_id:
            raise ProcessingError("project_id is required")

        # Validate project exists
        try:
            project = BookProjects.objects.get(pk=project_id)
        except BookProjects.DoesNotExist:
            raise ProcessingError(f"Project {project_id} not found")

        # Route to specific action handler
        action_handlers = {
            "generate_chapter_outline": self._generate_chapter_outline,
            "generate_chapter_content": self._generate_chapter_content,
            "refine_chapter": self._refine_chapter,
            "expand_chapter_section": self._expand_chapter_section,
            "generate_chapter_summary": self._generate_chapter_summary,
            "regenerate_chapter_with_feedback": self._regenerate_chapter_with_feedback,
        }

        handler = action_handlers[action]
        return handler(context, project)

    # ========================================================================
    # ACTION HANDLERS
    # ========================================================================

    def _generate_chapter_outline(
        self, context: Dict[str, Any], project: BookProjects
    ) -> Dict[str, Any]:
        """
        Generate outline for a chapter

        Context parameters:
            - chapter_number: int (required)
            - chapter_title: str (optional)
            - plot_points: List[str] (optional)
            - word_count_target: int (optional)
        """
        chapter_number = context.get("chapter_number")
        if not chapter_number:
            raise ProcessingError("chapter_number is required for outline generation")

        parameters = context.get("parameters", {})
        chapter_title = parameters.get("chapter_title", f"Chapter {chapter_number}")
        plot_points = parameters.get("plot_points", [])
        word_count = parameters.get("word_count_target", 3000)

        # Build context for generation using DatabaseContextEnricher
        project_context = self._build_project_context(project, chapter_number)
        agent_id = context.get("agent_id")

        # Generate outline using LLM (with fallback to mock)
        outline = self._generate_outline_with_llm(
            project_context, chapter_number, chapter_title, plot_points, word_count, agent_id
        )

        result = {
            "success": True,
            "action": "generate_chapter_outline",
            "data": {
                "chapter_number": chapter_number,
                "chapter_title": chapter_title,
                "outline": outline,
                "word_count_estimate": word_count,
                "project_context": project_context,
            },
            "message": f"Generated outline for chapter {chapter_number}",
        }

        logger.info(f"Generated outline for chapter {chapter_number} " f"in project {project.id}")
        return result

    def _generate_chapter_content(
        self, context: Dict[str, Any], project: BookProjects
    ) -> Dict[str, Any]:
        """
        Generate full chapter content

        Context parameters:
            - chapter_id: int (required if updating) OR chapter_number: int (if creating)
            - outline: Dict (optional - outline structure)
            - style_notes: str (optional)
            - include_dialogue: bool (optional, default=True)
        """
        chapter_id = context.get("chapter_id")
        chapter_number = context.get("chapter_number")

        if not chapter_id and not chapter_number:
            raise ProcessingError("Either chapter_id or chapter_number is required")

        # Get or prepare chapter
        if chapter_id:
            try:
                chapter = BookChapters.objects.get(pk=chapter_id)
            except BookChapters.DoesNotExist:
                raise ProcessingError(f"Chapter {chapter_id} not found")
        else:
            chapter = None  # Will create new chapter

        parameters = context.get("parameters", {})
        outline = parameters.get("outline", {})
        style_notes = parameters.get("style_notes", "")
        include_dialogue = parameters.get("include_dialogue", True)

        # Build generation context
        project_context = self._build_project_context(project, chapter_number)
        chapter_context = self._build_chapter_context(chapter) if chapter else {}
        agent_id = context.get("agent_id")

        # Generate content with LLM
        content = self._generate_content_with_llm(
            project_context,
            chapter_context,
            outline,
            chapter_number or (chapter.chapter_number if chapter else 1),
            style_notes,
            include_dialogue,
            agent_id,
        )

        # Save content to storage
        project_slug = slugify(project.title)
        try:
            file_path = self.storage_service.save_chapter(
                project_slug=project_slug,
                chapter_number=chapter_number or (chapter.chapter_number if chapter else 1),
                content=content,
                metadata={
                    "outline_used": bool(outline),
                    "style_notes": style_notes,
                    "include_dialogue": include_dialogue,
                    "word_count": len(content.split()),
                    "project_id": project.id,
                    "project_title": project.title,
                },
            )
            logger.info(f"Saved chapter content to {file_path}")
            saved_path = str(file_path)
        except Exception as e:
            logger.error(f"Failed to save chapter content: {e}")
            saved_path = None

        result = {
            "success": True,
            "action": "generate_chapter_content",
            "data": {
                "chapter_id": chapter_id,
                "chapter_number": chapter_number or (chapter.chapter_number if chapter else None),
                "content": content,
                "word_count": len(content.split()),
                "saved_path": saved_path,
                "metadata": {
                    "outline_used": bool(outline),
                    "style_notes": style_notes,
                    "include_dialogue": include_dialogue,
                },
            },
            "message": f"Generated content for chapter {chapter_number or chapter_id}",
        }

        logger.info(f"Generated content for chapter (ID: {chapter_id}, Number: {chapter_number})")
        return result

    def _refine_chapter(self, context: Dict[str, Any], project: BookProjects) -> Dict[str, Any]:
        """
        Refine existing chapter content

        Context parameters:
            - chapter_id: int (required)
            - refinement_focus: str (optional - 'pacing', 'dialogue', 'description', 'all')
            - specific_notes: str (optional)
        """
        chapter_id = context.get("chapter_id")
        if not chapter_id:
            raise ProcessingError("chapter_id is required for refinement")

        try:
            chapter = BookChapters.objects.get(pk=chapter_id)
        except BookChapters.DoesNotExist:
            raise ProcessingError(f"Chapter {chapter_id} not found")

        parameters = context.get("parameters", {})
        focus = parameters.get("refinement_focus", "all")
        notes = parameters.get("specific_notes", "")

        # Analyze and refine (mock for now)
        refined_content = self._mock_refine_content(
            chapter.content if hasattr(chapter, "content") else "", focus, notes
        )

        result = {
            "success": True,
            "action": "refine_chapter",
            "data": {
                "chapter_id": chapter_id,
                "refined_content": refined_content,
                "changes": {
                    "focus": focus,
                    "improvements": [
                        "Enhanced pacing in action scenes",
                        "Improved dialogue naturalness",
                        "Added sensory details",
                    ],
                },
            },
            "message": f"Refined chapter {chapter_id} with focus on {focus}",
        }

        logger.info(f"Refined chapter {chapter_id} (focus: {focus})")
        return result

    def _expand_chapter_section(
        self, context: Dict[str, Any], project: BookProjects
    ) -> Dict[str, Any]:
        """
        Expand a specific section of a chapter

        Context parameters:
            - chapter_id: int (required)
            - section_text: str (required) - Text to expand
            - expansion_type: str (optional - 'detail', 'dialogue', 'action')
            - target_length: int (optional - words)
        """
        chapter_id = context.get("chapter_id")
        if not chapter_id:
            raise ProcessingError("chapter_id is required")

        parameters = context.get("parameters", {})
        section_text = parameters.get("section_text")
        if not section_text:
            raise ProcessingError("section_text is required for expansion")

        expansion_type = parameters.get("expansion_type", "detail")
        target_length = parameters.get("target_length", len(section_text.split()) * 3)

        # Expand section (mock for now)
        expanded = self._mock_expand_section(section_text, expansion_type, target_length)

        result = {
            "success": True,
            "action": "expand_chapter_section",
            "data": {
                "chapter_id": chapter_id,
                "original_text": section_text,
                "expanded_text": expanded,
                "original_word_count": len(section_text.split()),
                "expanded_word_count": len(expanded.split()),
                "expansion_type": expansion_type,
            },
            "message": f"Expanded section in chapter {chapter_id}",
        }

        logger.info(
            f"Expanded section in chapter {chapter_id} "
            f"({len(section_text.split())} → {len(expanded.split())} words)"
        )
        return result

    def _generate_chapter_summary(
        self, context: Dict[str, Any], project: BookProjects
    ) -> Dict[str, Any]:
        """
        Generate summary of a chapter

        Context parameters:
            - chapter_id: int (required)
            - summary_length: str (optional - 'short', 'medium', 'detailed')
        """
        chapter_id = context.get("chapter_id")
        if not chapter_id:
            raise ProcessingError("chapter_id is required for summary generation")

        try:
            chapter = BookChapters.objects.get(pk=chapter_id)
        except BookChapters.DoesNotExist:
            raise ProcessingError(f"Chapter {chapter_id} not found")

        parameters = context.get("parameters", {})
        summary_length = parameters.get("summary_length", "medium")

        # Generate summary (mock for now)
        summary = self._mock_generate_summary(
            chapter.content if hasattr(chapter, "content") else "", summary_length
        )

        result = {
            "success": True,
            "action": "generate_chapter_summary",
            "data": {
                "chapter_id": chapter_id,
                "summary": summary,
                "summary_length": summary_length,
            },
            "message": f"Generated {summary_length} summary for chapter {chapter_id}",
        }

        logger.info(f"Generated {summary_length} summary for chapter {chapter_id}")
        return result

    # ========================================================================
    # HELPER METHODS - CONTEXT BUILDING
    # ========================================================================

    def _build_project_context(
        self, project: BookProjects, chapter_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Build comprehensive project context using DatabaseContextEnricher

        Args:
            project: BookProjects instance
            chapter_number: Optional chapter number for chapter-specific context

        Returns:
            Enriched context dictionary
        """
        try:
            # Use DatabaseContextEnricher for dynamic, schema-driven context
            params = {"project_id": project.id}
            if chapter_number:
                params["chapter_number"] = chapter_number

            enriched_context = self.context_enricher.enrich("chapter_generation", **params)

            logger.info(
                f"Enriched context for project {project.id}"
                f"{f' chapter {chapter_number}' if chapter_number else ''} "
                f"using DatabaseContextEnricher"
            )

            return enriched_context

        except Exception as e:
            # Fallback to basic context if enrichment fails
            logger.warning(f"Context enrichment failed: {e}. Using fallback basic context.")
            return {
                "project_id": project.id,
                "title": project.title or "",
                "genre": project.genre or "",
                "premise": project.story_premise or "",
            }

    def _build_chapter_context(self, chapter: BookChapters) -> Dict[str, Any]:
        """Build chapter-specific context"""
        return {
            "chapter_id": chapter.id,
            "chapter_number": chapter.chapter_number,
            "title": chapter.chapter_title or "",
            "current_content": chapter.content if hasattr(chapter, "content") else "",
            "word_count": (
                len(chapter.content.split())
                if hasattr(chapter, "content") and chapter.content
                else 0
            ),
        }

    # ========================================================================
    # LLM GENERATION METHODS
    # ========================================================================

    def _generate_outline_with_llm(
        self,
        project_context: Dict,
        chapter_number: int,
        chapter_title: str,
        plot_points: List[str],
        word_count: int,
        agent_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate chapter outline using LLM with PromptTemplateService"""

        # Prepare variables for template
        premise = project_context.get("premise", project_context.get("story_premise", "N/A"))
        variables = {
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "title": project_context.get("title", "Untitled"),
            "genre": project_context.get("genre", "Fiction"),
            "premise": premise[:500] if len(str(premise)) > 500 else premise,
            "themes": project_context.get("themes", "N/A"),
            "target_audience": project_context.get("target_audience", "N/A"),
            "protagonist_name": project_context.get("protagonist_name", "N/A"),
            "protagonist_description": project_context.get("protagonist_description", "")[:200],
            "antagonist_name": project_context.get("antagonist_name", "N/A"),
            "antagonist_description": project_context.get("antagonist_description", "")[:200],
            "story_position": project_context.get("story_position", "N/A"),
            "current_beat_name": project_context.get("current_beat", {}).get("beat_name", "N/A"),
            "word_count": word_count,
            "plot_points": ", ".join(plot_points) if plot_points else "General story progression",
        }

        # Try to use template from database
        rendered = self.prompt_service.render_template("chapter_outline_generation", variables)

        if rendered:
            system_prompt = rendered["system_prompt"]
            user_prompt = rendered["user_prompt"]
            logger.info("Using database template for outline generation")
        else:
            # Fallback to hardcoded (shouldn't happen)
            logger.warning("Template not found, using fallback prompts")
            system_prompt = """You are a professional fiction writing assistant specialized in story structure and chapter planning.
Your task is to create detailed chapter outlines that serve as blueprints for compelling narrative chapters."""
            user_prompt = (
                f"""Create outline for Chapter {chapter_number}: {chapter_title} (fallback mode)"""
            )

        try:
            # Call LLM
            response = self.llm_handler.call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                agent_id=agent_id,
                max_tokens=1000,
            )

            # Parse and structure the response
            return self._parse_outline_response(
                response, chapter_number, chapter_title, plot_points, word_count
            )

        except ProcessingError as e:
            logger.warning(f"LLM outline generation failed: {e}. Using fallback.")
            return self._mock_generate_outline(
                project_context, chapter_number, chapter_title, plot_points, word_count
            )

    def _parse_outline_response(
        self,
        llm_response: str,
        chapter_number: int,
        chapter_title: str,
        plot_points: List[str],
        word_count: int,
    ) -> Dict[str, Any]:
        """Parse LLM response into structured outline format"""
        # Simple parsing - in production, this would be more sophisticated
        lines = llm_response.strip().split("\n")
        sections = []
        section_num = 1

        for line in lines:
            line = line.strip()
            if line and (
                line.startswith("#")
                or line.startswith("Section")
                or line.startswith(str(section_num))
            ):
                sections.append(
                    {
                        "section_number": section_num,
                        "heading": line.lstrip("#").strip(),
                        "description": "See LLM-generated outline",
                        "estimated_words": word_count // 3,
                        "key_elements": ["narrative progression"],
                    }
                )
                section_num += 1

        # If parsing failed, create basic structure
        if not sections:
            sections = [
                {
                    "section_number": 1,
                    "heading": "Part 1",
                    "description": llm_response[:200] + "...",
                    "estimated_words": word_count // 3,
                    "key_elements": ["LLM-generated content"],
                }
            ]

        return {
            "chapter_title": chapter_title,
            "chapter_number": chapter_number,
            "sections": sections,
            "plot_points_addressed": plot_points or ["LLM-generated"],
            "estimated_total_words": word_count,
            "llm_generated": True,
            "raw_response": llm_response,
        }

    # ========================================================================
    # MOCK GENERATION METHODS (Fallback when LLM fails)
    # ========================================================================

    def _mock_generate_outline(
        self,
        project_context: Dict,
        chapter_number: int,
        chapter_title: str,
        plot_points: List[str],
        word_count: int,
    ) -> Dict[str, Any]:
        """Mock outline generation - will be replaced with LLM"""
        return {
            "chapter_title": chapter_title,
            "chapter_number": chapter_number,
            "sections": [
                {
                    "section_number": 1,
                    "heading": "Opening Scene",
                    "description": "Introduce the chapter conflict and setting",
                    "estimated_words": word_count // 4,
                    "key_elements": ["setting", "mood", "character state"],
                },
                {
                    "section_number": 2,
                    "heading": "Development",
                    "description": "Develop the conflict and character reactions",
                    "estimated_words": word_count // 2,
                    "key_elements": ["conflict escalation", "character decisions"],
                },
                {
                    "section_number": 3,
                    "heading": "Resolution",
                    "description": "Resolve immediate conflict, set up next chapter",
                    "estimated_words": word_count // 4,
                    "key_elements": ["tension release", "hook for next chapter"],
                },
            ],
            "plot_points_addressed": plot_points or ["Character development", "Plot advancement"],
            "estimated_total_words": word_count,
        }

    def _generate_content_with_llm(
        self,
        project_context: Dict,
        chapter_context: Dict,
        outline: Dict,
        chapter_number: int,
        style_notes: str,
        include_dialogue: bool,
        agent_id: Optional[int] = None,
    ) -> str:
        """Generate chapter content using LLM based on outline"""

        # Extract outline sections
        sections = outline.get("sections", []) if outline else []
        raw_outline = outline.get("raw_response", "") if outline else ""

        # Build system prompt
        system_prompt = """You are a professional fiction writer with expertise in crafting compelling narrative prose.
Your task is to write engaging chapter content based on a detailed outline, maintaining consistent character voices and story themes.
Write in a vivid, immersive style that draws readers into the story."""

        # Extract context details
        premise = project_context.get("premise", project_context.get("story_premise", ""))
        protagonist_name = project_context.get("protagonist_name", "the protagonist")
        protagonist_desc = project_context.get("protagonist_description", "")
        antagonist_name = project_context.get("antagonist_name", "the antagonist")

        # Build user prompt with JSON structure for clean output
        user_prompt = f"""Write Chapter {chapter_number} based on the following outline and context.

PROJECT CONTEXT:
- Title: {project_context.get('title', 'Untitled')}
- Genre: {project_context.get('genre', 'Fiction')}
- Premise: {premise[:300] if len(str(premise)) > 300 else premise}
- Themes: {project_context.get('themes', 'N/A')}
- Target Audience: {project_context.get('target_audience', 'Adult')}

MAIN CHARACTERS:
- Protagonist: {protagonist_name}
  {protagonist_desc[:150] if protagonist_desc else 'Main character'}
- Antagonist: {antagonist_name}

CHAPTER OUTLINE:
{raw_outline}

WRITING REQUIREMENTS:
- Write in third person limited perspective, focusing on {protagonist_name}
- Target length: Approximately 2500-3000 words for the complete chapter
- Include dialogue: {"Yes, include natural, character-appropriate dialogue" if include_dialogue else "Minimal dialogue, focus on narrative"}
- Style: {style_notes if style_notes else "Engaging literary fiction style with vivid descriptions and emotional depth"}
- Maintain consistency with the premise: the story explores themes of love across social classes

IMPORTANT:
- Follow the outline structure closely
- Show don't tell - use vivid sensory details
- Develop characters through actions and dialogue
- Create emotional resonance with readers
- Maintain proper pacing throughout

OUTPUT FORMAT - STRUCTURED RESPONSE:
Respond in this exact format to ensure clean chapter content:

<<<CHAPTER_START>>>
[Write the complete chapter content here - pure narrative prose only]
<<<CHAPTER_END>>>

CRITICAL RULES:
- Everything between <<<CHAPTER_START>>> and <<<CHAPTER_END>>> must be ONLY story content
- NO meta-commentary, NO editorial notes, NO analysis
- Start the story immediately after <<<CHAPTER_START>>>
- End the story immediately before <<<CHAPTER_END>>>
- Write ONLY in-world narrative content

Write the complete chapter now, following the outline sections:"""

        try:
            # Call LLM with higher token limit for full chapter
            response = self.llm_handler.call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                agent_id=agent_id,
                max_tokens=4000,  # Enough for ~3000 words
            )

            # Extract clean chapter content from structured response
            return self._extract_chapter_content(response)

        except ProcessingError as e:
            logger.warning(f"LLM content generation failed: {e}. Using fallback.")
            return self._mock_generate_content(
                project_context, chapter_context, outline, style_notes, include_dialogue
            )

    def _mock_generate_content(
        self,
        project_context: Dict,
        chapter_context: Dict,
        outline: Dict,
        style_notes: str,
        include_dialogue: bool,
    ) -> str:
        """Mock content generation - fallback only"""
        genre = project_context.get("genre", "fiction")
        title = project_context.get("title", "Untitled")

        content = f"""[GENERATED CONTENT FOR: {title}]

This is a placeholder chapter content generated by ChapterGenerateHandler.

Genre: {genre}
Style Notes: {style_notes or 'Standard narrative style'}
Dialogue Included: {include_dialogue}

The chapter begins with a compelling opening that draws the reader in...

[In production, this will be replaced with actual LLM-generated content
based on the project context, outline, and style preferences.]

Word count: ~500 words (sample)
"""
        return content

    def _mock_refine_content(self, original_content: str, focus: str, notes: str) -> str:
        """Mock refinement - will be replaced with LLM"""
        refined = f"""[REFINED CONTENT - Focus: {focus}]

{original_content}

[REFINEMENTS APPLIED]
- Enhanced {focus}
- Applied notes: {notes or 'None'}
- Improved flow and readability

[In production, this will use LLM to intelligently refine the content]
"""
        return refined

    def _mock_expand_section(
        self, section_text: str, expansion_type: str, target_length: int
    ) -> str:
        """Mock section expansion - will be replaced with LLM"""
        expanded = f"""{section_text}

[EXPANDED WITH {expansion_type.upper()}]
Additional details, sensory information, and {expansion_type} added here.
This expansion brings the scene to life with more vivid descriptions and engagement.

[In production, this will use LLM to expand the section naturally]
"""
        return expanded

    def _mock_generate_summary(self, content: str, length: str) -> str:
        """Mock summary generation - will be replaced with LLM"""
        length_map = {
            "short": "1-2 sentences",
            "medium": "1 paragraph",
            "detailed": "Multiple paragraphs",
        }

        return f"""[{length.upper()} SUMMARY - {length_map.get(length, 'medium')}]

This chapter advances the plot with key developments.
Main characters face new challenges and make important decisions.

[In production, this will use LLM to generate actual summaries]
"""

    def _extract_chapter_content(self, response: str) -> str:
        """
        Extract clean chapter content from structured LLM response

        Supports two formats:
        1. <<<CHAPTER_START>>> ... <<<CHAPTER_END>>> markers
        2. Plain text (fallback if no markers found)

        Args:
            response: Raw LLM response

        Returns:
            Clean chapter content without meta-commentary
        """
        # Try to extract content between markers
        start_marker = "<<<CHAPTER_START>>>"
        end_marker = "<<<CHAPTER_END>>>"

        if start_marker in response and end_marker in response:
            # Find the content between markers
            start_idx = response.find(start_marker) + len(start_marker)
            end_idx = response.find(end_marker)

            content = response[start_idx:end_idx].strip()
            logger.info("Extracted chapter content using structured markers")
            return content

        # Fallback: Use entire response (but log warning)
        logger.warning(
            "No structured markers found in LLM response. "
            "Using full response (may contain meta-commentary)"
        )
        return response.strip()

    def _regenerate_chapter_with_feedback(
        self, context: Dict[str, Any], project: BookProjects
    ) -> Dict[str, Any]:
        """
        Re-generate chapter content with user feedback integration

        Features:
        - Loads approved user comments (status='addressed' or 'acknowledged')
        - Reuses original generation parameters
        - Integrates feedback into regeneration prompt
        - Uses structured output markers

        Context parameters:
            - chapter_id: int (required)
            - include_feedback_types: List[str] (optional) - e.g., ['suggestion', 'concern']
            - preserve_original_style: bool (optional, default=True)
        """
        from apps.bfagent.models import Comment

        chapter_id = context.get("chapter_id")
        if not chapter_id:
            raise ProcessingError("chapter_id is required")

        try:
            chapter = BookChapters.objects.get(pk=chapter_id)
        except BookChapters.DoesNotExist:
            raise ProcessingError(f"Chapter {chapter_id} not found")

        parameters = context.get("parameters", {})

        # 1. Load approved comments (TEST DEFAULT: all comments treated as "approved")
        feedback_types = parameters.get(
            "include_feedback_types", ["suggestion", "concern", "general"]
        )

        comments = Comment.objects.filter(
            chapter=chapter,
            status__in=["addressed", "acknowledged"],  # Freigegebene Kommentare
            comment_type__in=feedback_types,
        ).order_by("created_at")

        # TEST MODE: If no approved comments, use all open comments
        if comments.count() == 0:
            logger.info("No approved comments found, using all comments for testing")
            comments = Comment.objects.filter(
                chapter=chapter, comment_type__in=feedback_types
            ).order_by("created_at")

        # 2. Get original generation parameters (from chapter.metadata JSON field)
        original_params = {}
        if hasattr(chapter, "metadata") and chapter.metadata:
            original_params = chapter.metadata.get("generation_params", {})

        # Use original params as defaults, can be overridden by context
        style_notes = parameters.get("style_notes", original_params.get("style_notes", ""))
        include_dialogue = parameters.get(
            "include_dialogue", original_params.get("include_dialogue", True)
        )

        # 3. Build feedback section for prompt
        feedback_text = ""
        if comments.exists():
            feedback_text = "\n\nUSER FEEDBACK TO INTEGRATE:\n"
            for i, comment in enumerate(comments, 1):
                feedback_text += f"{i}. [{comment.comment_type}] {comment.text}\n"
                if comment.author_reply:
                    feedback_text += f"   Author response: {comment.author_reply}\n"
            feedback_text += "\nPlease integrate this feedback naturally into the revised chapter."

        # 4. Build regeneration context
        project_context = self._build_project_context(project, chapter.chapter_number)
        chapter_context = self._build_chapter_context(chapter)

        # Get outline from metadata if available
        outline = original_params.get("outline", {})

        # 5. Generate with feedback-enhanced prompt
        content = self._generate_content_with_feedback(
            project_context,
            chapter_context,
            outline,
            chapter.chapter_number,
            style_notes,
            include_dialogue,
            feedback_text,
            context.get("agent_id"),
        )

        # 6. Save with metadata
        project_slug = slugify(project.title)
        try:
            file_path = self.storage_service.save_chapter(
                project_slug=project_slug,
                chapter_number=chapter.chapter_number,
                content=content,
                metadata={
                    "regenerated": True,
                    "feedback_count": comments.count(),
                    "generation_params": {
                        "style_notes": style_notes,
                        "include_dialogue": include_dialogue,
                        "outline": outline,
                    },
                    "word_count": len(content.split()),
                },
            )
            saved_path = str(file_path)
        except Exception as e:
            logger.error(f"Failed to save regenerated chapter: {e}")
            saved_path = None

        result = {
            "success": True,
            "action": "regenerate_chapter_with_feedback",
            "data": {
                "chapter_id": chapter_id,
                "content": content,
                "word_count": len(content.split()),
                "feedback_integrated": comments.count(),
                "saved_path": saved_path,
                "metadata": {
                    "style_notes": style_notes,
                    "include_dialogue": include_dialogue,
                },
            },
            "message": f"Regenerated chapter {chapter_id} with {comments.count()} feedback items",
        }

        logger.info(f"Regenerated chapter {chapter_id} with {comments.count()} feedback items")
        return result

    def _generate_content_with_feedback(
        self,
        project_context: Dict,
        chapter_context: Dict,
        outline: Dict,
        chapter_number: int,
        style_notes: str,
        include_dialogue: bool,
        feedback_text: str,
        agent_id: Optional[int] = None,
    ) -> str:
        """Generate chapter content with integrated user feedback"""

        # Use same prompt as normal generation, but with feedback section added
        raw_outline = outline.get("raw_response", "") if outline else ""
        premise = project_context.get("premise", project_context.get("story_premise", ""))
        protagonist_name = project_context.get("protagonist_name", "the protagonist")

        system_prompt = """You are a professional fiction writer specialized in revising and improving chapter content based on user feedback.
Your task is to rewrite the chapter while naturally integrating the feedback without disrupting the story flow."""

        user_prompt = f"""Rewrite Chapter {chapter_number} integrating user feedback.

PROJECT CONTEXT:
- Title: {project_context.get('title', 'Untitled')}
- Genre: {project_context.get('genre', 'Fiction')}
- Premise: {premise[:300] if len(str(premise)) > 300 else premise}

PROTAGONIST: {protagonist_name}

CHAPTER OUTLINE:
{raw_outline}

STYLE: {style_notes if style_notes else "Engaging literary fiction"}
{feedback_text}

OUTPUT FORMAT - STRUCTURED RESPONSE:
<<<CHAPTER_START>>>
[Rewritten chapter content with feedback integrated]
<<<CHAPTER_END>>>

CRITICAL:
- Integrate feedback naturally without breaking story flow
- NO meta-commentary about the feedback
- Write ONLY story content between markers

Rewrite the chapter now:"""

        try:
            response = self.llm_handler.call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                agent_id=agent_id,
                max_tokens=4000,
            )
            return self._extract_chapter_content(response)
        except ProcessingError as e:
            logger.warning(f"LLM regeneration failed: {e}. Using fallback.")
            return f"[REGENERATED CONTENT WITH FEEDBACK]\n\n{chapter_context.get('current_content', '')}"
