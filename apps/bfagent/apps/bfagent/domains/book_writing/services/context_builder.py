"""
Context Builder for Chapter Generation
Builds comprehensive context from project data for LLM prompts
"""
import logging
from typing import Dict, List, Optional
from apps.bfagent.models import BookProjects, Characters, Worlds

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Builds context strings from project data
    For use in LLM prompts
    """
    
    @staticmethod
    def build_character_context(project: BookProjects) -> str:
        """
        Build character context string
        
        Args:
            project: BookProjects instance
            
        Returns:
            Formatted string with character information
        """
        characters = Characters.objects.filter(project=project)
        
        if not characters.exists():
            return "No characters defined yet."
        
        context_parts = []
        for char in characters:
            char_info = [
                f"**{char.name}** ({char.role})"
            ]
            
            if char.age:
                char_info.append(f"- Age: {char.age}")
            
            if char.description:
                char_info.append(f"- Description: {char.description}")
            
            if char.personality:
                char_info.append(f"- Personality: {char.personality}")
            
            if char.appearance:
                char_info.append(f"- Appearance: {char.appearance}")
            
            if char.motivation:
                char_info.append(f"- Motivation: {char.motivation}")
            
            if char.conflict:
                char_info.append(f"- Conflict: {char.conflict}")
            
            if char.background:
                char_info.append(f"- Background: {char.background}")
            
            if char.arc:
                char_info.append(f"- Character Arc: {char.arc}")
            
            context_parts.append("\n".join(char_info))
        
        return "\n\n".join(context_parts)
    
    @staticmethod
    def build_world_context(project: BookProjects) -> str:
        """
        Build world context string from Worlds model
        
        Args:
            project: BookProjects instance
            
        Returns:
            Formatted string with world information
        """
        context_parts = []
        
        # Get worlds from the Worlds model (proper connection)
        worlds = Worlds.objects.filter(project=project)
        
        if worlds.exists():
            for world in worlds:
                world_section = [f"### {world.name} ({world.world_type})"]
                
                if world.description:
                    world_section.append(f"**Description:** {world.description}")
                
                if world.setting_details:
                    world_section.append(f"**Setting:** {world.setting_details}")
                
                if world.geography:
                    world_section.append(f"**Geography:** {world.geography}")
                
                if world.culture:
                    world_section.append(f"**Culture:** {world.culture}")
                
                if world.technology_level:
                    world_section.append(f"**Technology:** {world.technology_level}")
                
                if world.magic_system:
                    world_section.append(f"**Magic System:** {world.magic_system}")
                
                if world.politics:
                    world_section.append(f"**Politics:** {world.politics}")
                
                if world.history:
                    world_section.append(f"**History:** {world.history}")
                
                if world.inhabitants:
                    world_section.append(f"**Inhabitants:** {world.inhabitants}")
                
                context_parts.append("\n".join(world_section))
        
        # Fallback to project fields if no Worlds defined
        if not context_parts:
            if project.setting_time:
                context_parts.append(f"**Time Period:** {project.setting_time}")
            
            if project.setting_location:
                context_parts.append(f"**Location:** {project.setting_location}")
            
            if project.atmosphere_tone:
                context_parts.append(f"**Atmosphere:** {project.atmosphere_tone}")
        
        if not context_parts:
            return "No world setting defined yet."
        
        return "\n\n".join(context_parts)
    
    @staticmethod
    def build_previous_chapters_context(previous_chapters: List[Dict]) -> str:
        """
        Build context from previous chapters with intelligent summarization
        
        Args:
            previous_chapters: List of dicts with title, content, outline, summary
            
        Returns:
            Formatted string with previous chapter summaries
        """
        if not previous_chapters:
            return "This is the first chapter."
        
        context_parts = []
        total_chapters = len(previous_chapters)
        
        for i, chapter in enumerate(previous_chapters, 1):
            title = chapter.get('title', f'Chapter {i}')
            content = chapter.get('content', '')
            outline = chapter.get('outline', '')
            summary = chapter.get('summary', '')  # Pre-generated summary if available
            
            # Build chapter context based on recency
            if i == total_chapters:
                # Last chapter - include more detail (last 800 chars)
                detail_level = "detailed"
                content_excerpt = content[-800:] if len(content) > 800 else content
                if content_excerpt and len(content) > 800:
                    content_excerpt = "..." + content_excerpt
            elif i >= total_chapters - 2:
                # Recent chapters - medium detail (500 chars)
                detail_level = "medium"
                content_excerpt = content[:500] + "..." if len(content) > 500 else content
            else:
                # Older chapters - use summary or outline only
                detail_level = "brief"
                content_excerpt = summary if summary else (outline if outline else content[:200] + "...")
            
            chapter_info = [f"**Chapter {i}: {title}**"]
            
            if outline:
                chapter_info.append(f"*Purpose:* {outline[:200]}...")
            
            if content_excerpt:
                chapter_info.append(f"*Content:* {content_excerpt}")
            
            # Add key plot points if available
            key_events = chapter.get('key_events', [])
            if key_events:
                chapter_info.append(f"*Key Events:* {', '.join(key_events[:3])}")
            
            context_parts.append("\n".join(chapter_info))
        
        return "\n\n".join(context_parts)
    
    @staticmethod
    def summarize_chapter(content: str, max_length: int = 300) -> str:
        """
        Create a brief summary of chapter content
        
        Args:
            content: Full chapter content
            max_length: Maximum summary length
            
        Returns:
            Summarized content
        """
        if not content:
            return ""
        
        if len(content) <= max_length:
            return content
        
        # Simple extractive summary: first and last sentences
        sentences = content.replace('\n', ' ').split('. ')
        if len(sentences) <= 2:
            return content[:max_length] + "..."
        
        # Take first sentence, middle indicator, and last sentence
        first = sentences[0]
        last = sentences[-1] if sentences[-1] else sentences[-2]
        
        summary = f"{first}. [...] {last}"
        
        if len(summary) > max_length:
            return content[:max_length] + "..."
        
        return summary
    
    @staticmethod
    def build_outline_context(project: BookProjects) -> Dict[str, any]:
        """
        Build outline context from project's story structure
        
        Args:
            project: BookProjects instance
            
        Returns:
            Dict with outline information
        """
        import json
        from apps.bfagent.models import BookChapters
        
        chapters = BookChapters.objects.filter(project=project).order_by('chapter_number')
        
        if not chapters.exists():
            return {
                'has_outline': False,
                'formatted': 'No outline defined yet.',
                'chapters': [],
                'structure_type': 'custom'
            }
        
        # Detect structure type from outline patterns
        outlines = [c.outline for c in chapters if c.outline]
        structure_type = ContextBuilder._detect_structure_type(outlines)
        
        chapter_list = []
        formatted_parts = []
        
        for chapter in chapters:
            # Extract structured data from notes if available
            beat = ''
            act = None
            emotional_arc = ''
            raw_outline = chapter.outline or ''
            
            if chapter.notes:
                try:
                    notes_data = json.loads(chapter.notes) if isinstance(chapter.notes, str) else chapter.notes
                    beat = notes_data.get('beat', '')
                    act = notes_data.get('act')
                    emotional_arc = notes_data.get('emotional_arc', '')
                    raw_outline = notes_data.get('raw_outline', chapter.outline or '')
                except (json.JSONDecodeError, TypeError, AttributeError):
                    pass
            
            chapter_info = {
                'number': chapter.chapter_number,
                'title': chapter.title,
                'outline': chapter.outline or '',
                'raw_outline': raw_outline,
                'beat': beat,
                'act': act,
                'emotional_arc': emotional_arc,
                'target_words': chapter.target_word_count,
                'status': chapter.status,
            }
            chapter_list.append(chapter_info)
            
            # Format for LLM with rich context
            format_parts = [f"**Chapter {chapter.chapter_number}: {chapter.title}**"]
            if beat:
                format_parts.append(f"- Beat: {beat}")
            if act:
                format_parts.append(f"- Act: {act}")
            if emotional_arc:
                format_parts.append(f"- Emotional Arc: {emotional_arc}")
            format_parts.append(f"- Outline: {raw_outline or chapter.outline or 'Not defined'}")
            format_parts.append(f"- Target: {chapter.target_word_count} words")
            
            formatted_parts.append("\n".join(format_parts))
        
        return {
            'has_outline': True,
            'formatted': "\n\n".join(formatted_parts),
            'chapters': chapter_list,
            'structure_type': structure_type,
            'total_chapters': len(chapter_list)
        }
    
    @staticmethod
    def _detect_structure_type(outlines: List[str]) -> str:
        """Detect story structure type from outline patterns"""
        if not outlines:
            return 'custom'
        
        combined = ' '.join(outlines).lower()
        
        # Save the Cat beats
        if any(term in combined for term in ['opening image', 'catalyst', 'break into two', 'midpoint', 'all is lost']):
            return 'save_the_cat'
        
        # Hero's Journey
        if any(term in combined for term in ['call to adventure', 'crossing the threshold', 'road of trials', 'return']):
            return 'heros_journey'
        
        # Three Act
        if any(term in combined for term in ['act 1', 'act 2', 'act 3', 'setup', 'confrontation', 'resolution']):
            return 'three_act'
        
        return 'custom'
    
    @staticmethod
    def build_full_context(
        project: BookProjects,
        chapter_data: Dict,
        previous_chapters: List[Dict]
    ) -> Dict[str, str]:
        """
        Build complete context for chapter generation
        
        Args:
            project: BookProjects instance
            chapter_data: Dict with chapter info (number, title, outline)
            previous_chapters: List of previous chapter dicts
            
        Returns:
            Dict with all context components
        """
        outline_context = ContextBuilder.build_outline_context(project)
        
        return {
            # Project basics
            'project_title': project.title,
            'project_genre': project.genre or 'Fiction',
            'project_description': project.description or "No description",
            
            # Story elements
            'story_premise': project.story_premise or '',
            'main_conflict': project.main_conflict or '',
            'stakes': project.stakes or '',
            'protagonist': project.protagonist_concept or '',
            'antagonist': project.antagonist_concept or '',
            
            # Context from other phases
            'characters': ContextBuilder.build_character_context(project),
            'world': ContextBuilder.build_world_context(project),
            'outline': outline_context,
            'previous_chapters': ContextBuilder.build_previous_chapters_context(previous_chapters),
            
            # Current chapter
            'chapter_number': chapter_data.get('chapter_number'),
            'chapter_title': chapter_data.get('chapter_title'),
            'chapter_outline': chapter_data.get('chapter_outline', 'No outline provided'),
            'target_word_count': chapter_data.get('target_word_count', 1000)
        }
    
    @staticmethod
    def build_project_context(project: BookProjects) -> Dict[str, any]:
        """
        Build project context for handlers (Phase 1-2)
        
        Args:
            project: BookProjects instance
            
        Returns:
            Dict with project information for downstream handlers
        """
        return {
            'id': project.id,
            'title': project.title,
            'genre': project.genre or 'Fiction',
            'description': project.description or '',
            'story_premise': project.story_premise or '',
            'main_conflict': project.main_conflict or '',
            'stakes': project.stakes or '',
            'protagonist_concept': project.protagonist_concept or '',
            'antagonist_concept': project.antagonist_concept or '',
            'setting_time': project.setting_time or '',
            'setting_location': project.setting_location or '',
            'atmosphere_tone': project.atmosphere_tone or '',
            'target_audience': str(project.target_audience) if project.target_audience else '',
            'content_rating': project.content_rating or '',
            'book_type': project.book_type.name if project.book_type else 'Novel',
        }
