"""
Enrichment handlers for Book Writing Studio.

These handlers enrich projects, chapters, and characters using LLM agents.
"""

from typing import Any, Dict, Optional

from apps.core.handlers.base import BaseHandler


class ProjectEnrichmentHandler(BaseHandler):
    """
    Enriches book projects with AI-generated content.

    Supports enrichment actions like:
    - outline_from_fundamentals
    - outline_from_world_conflict
    - outline_from_characters
    - concepts_brainstorm
    - premise, themes, stakes
    - character cast generation
    """

    def __init__(self):
        super().__init__()
        self.handler_id = "bookwriting.project.enrich"
        self.name = "Project Enrichment Handler"
        self.description = "Enriches book projects using AI agents"
        self.version = "1.0.0"

    def validate_input(self, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate required context."""
        required = ["project", "agent", "action"]
        missing = [key for key in required if key not in context]

        if missing:
            return False, f"Missing required context: {', '.join(missing)}"

        # Validate project object
        project = context.get("project")
        if not hasattr(project, "pk"):
            return False, "Invalid project object"

        # Validate agent object
        agent = context.get("agent")
        if not hasattr(agent, "system_prompt"):
            return False, "Invalid agent object"

        # Validate action
        action = context.get("action")
        if not isinstance(action, str) or not action:
            return False, "Invalid action string"

        return True, None

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute project enrichment.

        Args:
            context: {
                'project': BookProject instance
                'agent': Agent instance
                'action': str (e.g., 'outline_from_fundamentals')
                'chapter': Optional[BookChapter] for chapter-specific actions
                'user': Optional[User] for tracking
            }

        Returns:
            {
                'success': bool
                'result': str (LLM response)
                'action': str
                'error': Optional[str]
                'metadata': {...}
            }
        """
        # Import here to avoid circular imports
        from apps.bfagent.services.project_enrichment import _build_prompt, _call_llm, _choose_llm

        project = context["project"]
        agent = context["agent"]
        action = context["action"]
        chapter = context.get("chapter")

        try:
            # Choose LLM
            llm = _choose_llm(agent)
            if not llm:
                return {
                    "success": False,
                    "result": "",
                    "action": action,
                    "error": "No active LLM configured",
                    "metadata": {},
                }

            # Build prompt
            prompt_data = _build_prompt(project, agent, action, chapter)

            # Call LLM
            response = _call_llm(
                llm=llm, system=prompt_data["system"], user_message=prompt_data["user"]
            )

            return {
                "success": True,
                "result": response,
                "action": action,
                "error": None,
                "metadata": {
                    "llm_id": llm.pk,
                    "llm_name": llm.name,
                    "agent_id": agent.pk,
                    "agent_name": agent.name,
                    "project_id": project.pk,
                    "project_title": project.title,
                    "chapter_id": chapter.pk if chapter else None,
                },
            }

        except Exception as e:
            return {
                "success": False,
                "result": "",
                "action": action,
                "error": str(e),
                "metadata": {
                    "agent_id": agent.pk,
                    "project_id": project.pk,
                },
            }


class ChapterEnrichmentHandler(BaseHandler):
    """
    Enriches book chapters with AI-generated content.

    Supports actions like:
    - write_chapter_draft
    - summarize_chapter
    - expand_chapter
    """

    def __init__(self):
        super().__init__()
        self.handler_id = "bookwriting.chapter.enrich"
        self.name = "Chapter Enrichment Handler"
        self.description = "Enriches book chapters using AI agents"
        self.version = "1.0.0"

    def validate_input(self, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate required context."""
        required = ["chapter", "agent", "action"]
        missing = [key for key in required if key not in context]

        if missing:
            return False, f"Missing required context: {', '.join(missing)}"

        return True, None

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute chapter enrichment.

        Uses ProjectEnrichmentHandler with chapter context.
        """
        # Import here
        from apps.bfagent.models import BookProjects

        chapter = context["chapter"]

        # Get project from chapter
        try:
            project = BookProjects.objects.get(pk=chapter.project_id)
        except BookProjects.DoesNotExist:
            return {
                "success": False,
                "result": "",
                "action": context.get("action", ""),
                "error": "Project not found for chapter",
                "metadata": {"chapter_id": chapter.pk},
            }

        # Use ProjectEnrichmentHandler with chapter
        enrichment_context = {
            **context,
            "project": project,
            "chapter": chapter,
        }

        handler = ProjectEnrichmentHandler()
        return handler.execute(enrichment_context)


class CharacterEnrichmentHandler(BaseHandler):
    """
    Enriches characters with AI-generated content.

    Supports actions like:
    - generate_backstory
    - develop_dialogue_voice
    - create_character_arc
    """

    def __init__(self):
        super().__init__()
        self.handler_id = "bookwriting.character.enrich"
        self.name = "Character Enrichment Handler"
        self.description = "Enriches characters using AI agents"
        self.version = "1.0.0"

    def validate_input(self, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate required context."""
        required = ["character", "agent", "action"]
        missing = [key for key in required if key not in context]

        if missing:
            return False, f"Missing required context: {', '.join(missing)}"

        return True, None

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute character enrichment."""
        from apps.bfagent.models import BookProjects
        from apps.bfagent.services.project_enrichment import _call_llm, _choose_llm

        character = context["character"]
        agent = context["agent"]
        action = context["action"]

        try:
            # Get project
            project = BookProjects.objects.get(pk=character.project_id)

            # Choose LLM
            llm = _choose_llm(agent)
            if not llm:
                return {
                    "success": False,
                    "result": "",
                    "action": action,
                    "error": "No active LLM configured",
                    "metadata": {},
                }

            # Build character-specific prompt
            system = agent.system_prompt or "You are a character development expert."
            user_message = f"""
Character Name: {character.name}
Role: {character.role}
Description: {character.description or 'Not yet defined'}

Project Context:
- Title: {project.title}
- Genre: {project.genre}
- Setting: {project.setting_time}, {project.setting_location}

Action: {action}

Please provide detailed, creative content that fits the character and story.
"""

            # Call LLM
            response = _call_llm(llm, system, user_message)

            return {
                "success": True,
                "result": response,
                "action": action,
                "error": None,
                "metadata": {
                    "llm_id": llm.pk,
                    "agent_id": agent.pk,
                    "character_id": character.pk,
                    "character_name": character.name,
                    "project_id": project.pk,
                },
            }

        except Exception as e:
            return {
                "success": False,
                "result": "",
                "action": action,
                "error": str(e),
                "metadata": {
                    "character_id": character.pk,
                },
            }
