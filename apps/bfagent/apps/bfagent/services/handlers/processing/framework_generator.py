"""
Framework Generator Processing Handler

Generates story outlines using established story frameworks.
"""

from typing import Any, Dict
import structlog

from ..base.processing import BaseProcessingHandler
from ..exceptions import ProcessingHandlerException
from ..decorators import with_logging, with_performance_monitoring
from ..schemas import FrameworkGeneratorConfig

logger = structlog.get_logger()


class FrameworkGeneratorHandler(BaseProcessingHandler):
    """
    Generate story outlines using frameworks.
    
    Uses the story_frameworks module to generate structured
    outlines based on established frameworks like:
    - Hero's Journey
    - Save the Cat
    - Three-Act Structure
    
    Configuration:
        framework (str): Framework name. Required.
            Options: "heros_journey", "save_the_cat", "three_act"
        output_format (str): Output format. Defaults to "markdown".
            Options: "markdown", "plain", "json"
        num_chapters (int, optional): Override chapter count
        include_suggestions (bool): Include writing suggestions. Defaults to False.
    
    Input Data:
        title (str): Project title
        genre (str): Project genre
        num_chapters (int): Number of chapters
        story_premise (str, optional): Story premise for suggestions
    
    Context:
        project (BookProjects): Required for accessing project data
    
    Returns:
        str: Generated outline in specified format
    
    Example:
        >>> handler = FrameworkGeneratorHandler({
        ...     "framework": "save_the_cat",
        ...     "output_format": "markdown"
        ... })
        >>> result = handler.process(input_data, context)
        >>> # "# Story Outline\n## Chapter 1: Opening Image\n..."
    """
    
    handler_name = "framework_generator"
    handler_version = "1.0.0"
    description = "Generates story outlines using established frameworks"
    
    def validate_config(self) -> None:
        """Validate configuration using Pydantic."""
        try:
            FrameworkGeneratorConfig(**self.config)
        except Exception as e:
            raise ProcessingHandlerException(
                message="Invalid configuration for FrameworkGeneratorHandler",
                handler_name=self.handler_name,
                context={"config": self.config, "error": str(e)}
            )
    
    @with_logging
    @with_performance_monitoring
    def process(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """
        Generate framework-based outline.
        
        Args:
            input_data: Data from input handlers
            context: Runtime context with project
            
        Returns:
            Generated outline string
        """
        from ...story_frameworks import get_framework
        
        # Get configuration
        framework_name = self.config["framework"]
        output_format = self.config.get("output_format", "markdown")
        include_suggestions = self.config.get("include_suggestions", False)
        
        # Get data
        project = context.get("project")
        if not project:
            raise ValueError("Context missing 'project'")
        
        title = input_data.get("title", project.title)
        genre = input_data.get("genre", project.genre)
        num_chapters = (
            self.config.get("num_chapters") or 
            input_data.get("num_chapters") or 
            12
        )
        story_premise = input_data.get("story_premise", project.story_premise)
        
        # Load framework
        framework = get_framework(framework_name)
        
        # Generate outline based on format
        if output_format == "json":
            return self._generate_json(framework, title, genre, num_chapters, story_premise, include_suggestions)
        elif output_format == "plain":
            return self._generate_plain(framework, title, genre, num_chapters, story_premise, include_suggestions)
        else:  # markdown (default)
            return self._generate_markdown(framework, title, genre, num_chapters, story_premise, include_suggestions)
    
    def _generate_markdown(
        self, 
        framework: Any, 
        title: str, 
        genre: str, 
        num_chapters: int,
        story_premise: str = None,
        include_suggestions: bool = False
    ) -> str:
        """Generate markdown format outline."""
        lines = []
        
        # Header
        lines.append(f"# {title} - Story Outline")
        lines.append(f"**Framework:** {framework.name}")
        lines.append(f"**Genre:** {genre or 'Not specified'}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Generate chapter outlines
        for i in range(1, num_chapters + 1):
            position = i / num_chapters
            beat = framework.get_beat_for_position(position)
            
            # Determine act (for frameworks with acts)
            act = self._get_act_for_position(framework, position, num_chapters)
            
            # Chapter header
            if act:
                lines.append(f"## Chapter {i}: {beat.name} ({act})")
            else:
                lines.append(f"## Chapter {i}: {beat.name}")
            
            lines.append(f"**Story Position:** {position:.0%}")
            lines.append(f"**Beat Description:** {beat.description}")
            lines.append(f"**Chapter Focus:** {beat.chapter_guidance}")
            lines.append(f"**Emotional Arc:** {beat.emotional_arc}")
            
            # Optional: Add suggestions based on story premise
            if include_suggestions and story_premise and i <= 3:  # First 3 chapters only
                lines.append("")
                lines.append(f"*Suggestion: Connect '{beat.name}' to your premise: {story_premise[:100]}...*")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_plain(
        self, 
        framework: Any, 
        title: str, 
        genre: str, 
        num_chapters: int,
        story_premise: str = None,
        include_suggestions: bool = False
    ) -> str:
        """Generate plain text format outline."""
        lines = []
        
        lines.append(f"{title} - Story Outline")
        lines.append(f"Framework: {framework.name}")
        lines.append(f"Genre: {genre or 'Not specified'}")
        lines.append("")
        lines.append("=" * 60)
        lines.append("")
        
        for i in range(1, num_chapters + 1):
            position = i / num_chapters
            beat = framework.get_beat_for_position(position)
            
            act = self._get_act_for_position(framework, position, num_chapters)
            
            lines.append(f"CHAPTER {i}: {beat.name}")
            if act:
                lines.append(f"Act: {act}")
            lines.append(f"Position: {position:.0%}")
            lines.append(f"{beat.description}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_json(
        self, 
        framework: Any, 
        title: str, 
        genre: str, 
        num_chapters: int,
        story_premise: str = None,
        include_suggestions: bool = False
    ) -> str:
        """Generate JSON format outline."""
        import json
        
        outline_data = {
            "title": title,
            "framework": framework.name,
            "genre": genre,
            "num_chapters": num_chapters,
            "chapters": []
        }
        
        for i in range(1, num_chapters + 1):
            position = i / num_chapters
            beat = framework.get_beat_for_position(position)
            
            act = self._get_act_for_position(framework, position, num_chapters)
            
            chapter_data = {
                "number": i,
                "title": beat.name,
                "position": round(position, 3),
                "beat": beat.name,
                "description": beat.description,
                "guidance": beat.chapter_guidance,
                "emotional_arc": beat.emotional_arc
            }
            
            if act:
                chapter_data["act"] = act
            
            outline_data["chapters"].append(chapter_data)
        
        return json.dumps(outline_data, indent=2)
    
    def _get_act_for_position(self, framework: Any, position: float, num_chapters: int) -> str:
        """Determine act for position (for applicable frameworks)."""
        framework_name = framework.name.lower()
        
        if "save the cat" in framework_name:
            if position <= 0.25:
                return "ACT 1 - Setup"
            elif position <= 0.75:
                return "ACT 2 - Confrontation"
            else:
                return "ACT 3 - Resolution"
        
        elif "three" in framework_name and "act" in framework_name:
            if position <= 0.25:
                return "AKT 1: Setup"
            elif position <= 0.75:
                return "AKT 2: Konfrontation"
            else:
                return "AKT 3: Auflösung"
        
        # No acts for other frameworks
        return ""
