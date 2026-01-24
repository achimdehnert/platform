"""
Story Chapter Handlers - Book Writing Domain
Universal handlers for story-based books (novels, fiction)
"""
from typing import Dict, Any
import logging

from django.conf import settings
from apps.bfagent.models import BookProjects
from ..services.llm_service import LLMService
from ..services.context_builder import ContextBuilder

logger = logging.getLogger(__name__)


class UniversalStoryChapterHandler:
    """
    Universal handler for any story chapter
    
    Works with any chapter number and book structure.
    Uses chapter outline and context to generate content.
    
    Input:
    - chapter_number: int
    - chapter_title: str
    - chapter_outline: str (beat description)
    - project_title: str
    - project_genre: str
    - project_description: str
    - target_word_count: int
    - previous_chapters: list (optional, content from previous chapters)
    
    Output:
    - content: str
    - word_count: int
    """
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate content for a story chapter using LLM"""
        chapter_number = data.get('chapter_number', 1)
        chapter_title = data.get('chapter_title', 'Chapter')
        chapter_outline = data.get('chapter_outline', '')
        
        project_title = data.get('project_title', 'Story')
        project_genre = data.get('project_genre', 'Fiction')
        project_description = data.get('project_description', '')
        
        target_word_count = data.get('target_word_count', 1000)
        previous_chapters = data.get('previous_chapters', [])
        
        # Get generation mode from config
        use_llm = config.get('use_llm', True) if config else True
        project_id = data.get('project_id')
        
        # Check if LLM should be used and is available
        if use_llm and project_id:
            api_key_available = (
                getattr(settings, 'OPENAI_API_KEY', None) or
                getattr(settings, 'ANTHROPIC_API_KEY', None)
            )
            
            if not api_key_available:
                logger.error("LLM requested but no API key configured!")
                return {
                    'success': False,
                    'error': 'LLM generation requested but no API key found. Please configure OPENAI_API_KEY or ANTHROPIC_API_KEY in settings'
                }
            
            return UniversalStoryChapterHandler._generate_with_llm(
                data, project_id, config
            )
        
        # Explicit placeholder mode
        logger.info(f"Using placeholder mode for chapter {chapter_number}")
        return UniversalStoryChapterHandler._generate_placeholder(
            chapter_number, chapter_title, chapter_outline,
            project_title, project_genre, target_word_count, previous_chapters
        )
    
    @staticmethod
    def _generate_with_llm(
        data: Dict[str, Any],
        project_id: int,
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate content using LLM with full context"""
        try:
            project = BookProjects.objects.get(id=project_id)
        except BookProjects.DoesNotExist:
            logger.error(f"Project {project_id} not found")
            return {'success': False, 'error': 'Project not found'}
        
        # Build full context
        chapter_data = {
            'chapter_number': data.get('chapter_number', 1),
            'chapter_title': data.get('chapter_title', 'Chapter'),
            'chapter_outline': data.get('chapter_outline', ''),
            'target_word_count': data.get('target_word_count', 1000)
        }
        
        context = ContextBuilder.build_full_context(
            project=project,
            chapter_data=chapter_data,
            previous_chapters=data.get('previous_chapters', [])
        )
        
        # Build prompt
        prompt = UniversalStoryChapterHandler._build_prompt(context)
        
        # Initialize LLM service
        provider = getattr(settings, 'LLM_PROVIDER', 'openai')
        model = getattr(settings, 'LLM_MODEL', None)
        llm = LLMService(provider=provider, model=model)
        
        # Generate content
        max_tokens = min(context['target_word_count'] * 2, 4000)
        result = llm.generate_chapter_content(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=0.7
        )
        
        if not result['success']:
            logger.error(f"LLM generation failed: {result.get('error')}")
            return result
        
        content = result['content']
        word_count = len(content.split())
        
        logger.info(
            f"Generated {word_count} words for chapter {context['chapter_number']} "
            f"using {provider} (tokens: {result['usage']['total_tokens']})"
        )
        
        if result.get('usage'):
            cost = llm.calculate_cost(result['usage'])
            logger.info(f"Estimated cost: ${cost:.4f}")
        
        return {
            'success': True,
            'content': content,
            'word_count': word_count,
            'chapter_number': context['chapter_number'],
            'chapter_title': context['chapter_title'],
            'usage': result.get('usage'),
            'cost': cost if result.get('usage') else 0
        }
    
    @staticmethod
    def _build_prompt(context: Dict[str, str]) -> str:
        """Build LLM prompt from context with rich outline information"""
        # Extract beat info from outline context if available
        outline_info = context.get('outline', {})
        current_chapter_info = None
        
        if isinstance(outline_info, dict) and outline_info.get('chapters'):
            for ch in outline_info['chapters']:
                if ch.get('number') == context['chapter_number']:
                    current_chapter_info = ch
                    break
        
        # Build chapter section with beat details
        chapter_section = [
            "## Current Chapter:",
            f"- **Number:** {context['chapter_number']}",
            f"- **Title:** {context['chapter_title']}",
        ]
        
        if current_chapter_info:
            if current_chapter_info.get('beat'):
                chapter_section.append(f"- **Story Beat:** {current_chapter_info['beat']}")
            if current_chapter_info.get('act'):
                chapter_section.append(f"- **Act:** {current_chapter_info['act']}")
            if current_chapter_info.get('emotional_arc'):
                chapter_section.append(f"- **Emotional Arc:** {current_chapter_info['emotional_arc']}")
            chapter_section.append(f"- **Outline:** {current_chapter_info.get('raw_outline') or context['chapter_outline']}")
        else:
            chapter_section.append(f"- **Outline/Beat:** {context['chapter_outline']}")
        
        chapter_section.append(f"- **Target Word Count:** {context['target_word_count']} words")
        
        prompt_parts = [
            "# Task: Write a Chapter for a Novel",
            "",
            "## Book Information:",
            f"- **Title:** {context['project_title']}",
            f"- **Genre:** {context['project_genre']}",
            f"- **Description:** {context['project_description']}",
            "",
            "## Characters:",
            context['characters'],
            "",
            "## World Setting:",
            context['world'],
            "",
            "## Previous Chapters Summary:",
            context['previous_chapters'],
            "",
            "\n".join(chapter_section),
            "",
            "## Instructions:",
            "1. Write the chapter content following the Story Beat and Outline precisely",
            "2. Match the Emotional Arc - start and end the chapter with the specified emotional tone",
            "3. Use the characters and world information to maintain consistency",
            "4. Build naturally on the previous chapters",
            "5. Match the genre and tone throughout",
            f"6. Aim for approximately {context['target_word_count']} words",
            "7. Write in an engaging, professional fiction style",
            "8. Include dialogue, description, and action as appropriate",
            "9. Focus on advancing the plot according to the beat structure",
            "",
            "## Output Format:",
            "Write the chapter content directly. Do not include meta-commentary or explanations.",
            "Start with the chapter content immediately.",
            "",
            "---",
            "",
            "Begin writing now:"
        ]
        
        return "\n".join(prompt_parts)
    
    @staticmethod
    def _generate_placeholder(
        chapter_number: int,
        chapter_title: str,
        chapter_outline: str,
        project_title: str,
        project_genre: str,
        target_word_count: int,
        previous_chapters: list
    ) -> Dict[str, Any]:
        """Generate placeholder content when LLM is not available"""
        logger.info(f"Using placeholder for chapter {chapter_number} (no LLM configured)")
        
        # Build context from previous chapters
        context_summary = ""
        if previous_chapters:
            context_summary = "\n\n".join([
                f"**Previous Chapter {i+1}:**\n{ch['title']}\n{ch['content'][:200]}..."
                for i, ch in enumerate(previous_chapters[-3:])  # Last 3 chapters
            ])
        
        content_parts = []
        
        content_parts.append(f"# Chapter {chapter_number}: {chapter_title}")
        content_parts.append("")
        content_parts.append(f"**Story:** {project_title}")
        content_parts.append(f"**Genre:** {project_genre}")
        content_parts.append("")
        
        if chapter_outline:
            content_parts.append(f"## Beat Description")
            content_parts.append(chapter_outline)
            content_parts.append("")
        
        content_parts.append(f"## Chapter Content")
        content_parts.append("")
        
        # Generate content based on chapter outline
        if chapter_number == 1:
            # Opening
            content_parts.append("The story begins here. The protagonist is introduced in their ordinary world.")
            content_parts.append("")
            content_parts.append(f"In the world of '{project_title}', we meet our main character...")
            content_parts.append("")
            content_parts.append("The setting is established. The reader gets a sense of what life is like before everything changes.")
            
        elif "catalyst" in chapter_outline.lower() or "inciting" in chapter_outline.lower():
            # Inciting incident
            content_parts.append("Something happens that changes everything.")
            content_parts.append("")
            content_parts.append("The protagonist faces a decision that will alter the course of their life.")
            content_parts.append("")
            content_parts.append("There's no going back now. The journey has begun.")
            
        elif "midpoint" in chapter_outline.lower():
            # Midpoint
            content_parts.append("We've reached the middle of the story.")
            content_parts.append("")
            content_parts.append("A major revelation or turning point occurs. Everything the protagonist thought they knew is challenged.")
            content_parts.append("")
            content_parts.append("The stakes are raised. The real battle begins.")
            
        elif "lost" in chapter_outline.lower() or "lowest" in chapter_outline.lower():
            # All is lost
            content_parts.append("This is the darkest moment.")
            content_parts.append("")
            content_parts.append("The protagonist has lost everything. Hope seems distant.")
            content_parts.append("")
            content_parts.append("But in darkness, there is often a spark of light waiting to be discovered.")
            
        elif "finale" in chapter_outline.lower() or "climax" in chapter_outline.lower():
            # Climax
            content_parts.append("The final confrontation.")
            content_parts.append("")
            content_parts.append("Everything has led to this moment. The protagonist must use everything they've learned.")
            content_parts.append("")
            content_parts.append("The battle rages. The outcome hangs in the balance.")
            
        elif chapter_number >= 14:
            # Resolution
            content_parts.append("The story draws to a close.")
            content_parts.append("")
            content_parts.append("We see how the protagonist has changed. The transformation is complete.")
            content_parts.append("")
            content_parts.append("A new equilibrium is established. The journey has come full circle.")
            
        else:
            # Generic chapter content
            content_parts.append(f"Chapter {chapter_number} continues the story.")
            content_parts.append("")
            content_parts.append(f"Building on previous events, the narrative moves forward.")
            content_parts.append("")
            content_parts.append(f"The protagonist faces new challenges and makes important discoveries.")
            content_parts.append("")
            content_parts.append(f"Beat focus: {chapter_outline}")
        
        # Add context if available
        if context_summary:
            content_parts.append("")
            content_parts.append("---")
            content_parts.append("")
            content_parts.append("## Story Context")
            content_parts.append(context_summary)
        
        # Pad to reach target word count
        content = "\n".join(content_parts)
        current_words = len(content.split())
        
        if current_words < target_word_count:
            padding_words = target_word_count - current_words
            padding = []
            padding.append("")
            padding.append("---")
            padding.append("")
            padding.append("## Extended Content")
            padding.append("")
            
            # Generate filler paragraphs
            paragraphs_needed = (padding_words // 50) + 1
            for i in range(min(paragraphs_needed, 5)):
                padding.append(f"This chapter explores the themes and developments outlined in the beat description. ")
                padding.append(f"The protagonist continues their journey, facing obstacles and growing through experience. ")
                padding.append(f"Each scene builds on the last, creating momentum toward the story's climax. ")
                padding.append("")
            
            content += "\n".join(padding)
        
        final_word_count = len(content.split())
        
        logger.info(f"Generated {final_word_count} words for chapter {chapter_number}")
        
        return {
            'success': True,
            'content': content,
            'word_count': final_word_count,
            'chapter_number': chapter_number,
            'chapter_title': chapter_title
        }


class StoryOpeningHandler:
    """Handler specifically for opening chapters"""
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate opening chapter content"""
        # Delegate to universal handler
        return UniversalStoryChapterHandler.handle(data, config)


class StoryMiddleHandler:
    """Handler specifically for middle chapters"""
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate middle chapter content"""
        # Delegate to universal handler
        return UniversalStoryChapterHandler.handle(data, config)


class StoryEndingHandler:
    """Handler specifically for ending chapters"""
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate ending chapter content"""
        # Delegate to universal handler
        return UniversalStoryChapterHandler.handle(data, config)
