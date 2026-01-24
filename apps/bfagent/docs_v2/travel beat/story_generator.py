"""
Travel Story - Story Agent
==========================
Part 2: Generator Engine

Generiert Kapitel mittels LLM API.
"""

import json
import os
from typing import List, Dict, Optional, Generator
from dataclasses import dataclass, field
from datetime import datetime

from story_models import ChapterOutline, StoryOutline, StoryPreferences
from agent_prompts import (
    PromptBuilder, StoryContext, ChapterState,
    SUMMARY_PROMPT, LOCATION_RESEARCH_PROMPT,
)


# ═══════════════════════════════════════════════════════════════
# GENERATED CHAPTER
# ═══════════════════════════════════════════════════════════════

@dataclass
class GeneratedChapter:
    """A generated chapter with metadata"""
    chapter_number: int
    title: str
    content: str
    word_count: int
    
    # From outline
    story_location: str
    reader_location: str
    reading_date: str
    
    # Generation metadata
    generated_at: str = ""
    model_used: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    
    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat()
        if not self.word_count:
            self.word_count = len(self.content.split())
    
    def to_dict(self) -> Dict:
        return {
            "chapter_number": self.chapter_number,
            "title": self.title,
            "content": self.content,
            "word_count": self.word_count,
            "story_location": self.story_location,
            "reader_location": self.reader_location,
            "reading_date": self.reading_date,
            "generated_at": self.generated_at,
            "model_used": self.model_used,
        }
    
    def to_markdown(self) -> str:
        return f"""# Kapitel {self.chapter_number}: {self.title}

*{self.story_location} | {self.reading_date}*

---

{self.content}

---
*Wörter: {self.word_count}*
"""


@dataclass
class GeneratedStory:
    """Complete generated story"""
    title: str
    chapters: List[GeneratedChapter] = field(default_factory=list)
    
    # Metadata
    genre: str = ""
    total_words: int = 0
    generated_at: str = ""
    
    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat()
    
    def add_chapter(self, chapter: GeneratedChapter):
        self.chapters.append(chapter)
        self.total_words = sum(ch.word_count for ch in self.chapters)
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "genre": self.genre,
            "total_words": self.total_words,
            "total_chapters": len(self.chapters),
            "generated_at": self.generated_at,
            "chapters": [ch.to_dict() for ch in self.chapters],
        }
    
    def to_markdown(self) -> str:
        lines = [
            f"# {self.title}",
            "",
            f"*{self.genre} | {self.total_words:,} Wörter | {len(self.chapters)} Kapitel*",
            "",
            "---",
            "",
        ]
        for ch in self.chapters:
            lines.append(ch.to_markdown())
            lines.append("\n---\n")
        return "\n".join(lines)
    
    def save_markdown(self, filepath: str):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())
    
    def save_json(self, filepath: str):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════
# LLM CLIENT INTERFACE
# ═══════════════════════════════════════════════════════════════

class LLMClient:
    """
    Abstract LLM client interface.
    Implement for different providers (Anthropic, OpenAI, etc.)
    """
    
    def generate(
        self, 
        system_prompt: str, 
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.8,
    ) -> Dict:
        """
        Generate text from the LLM.
        
        Returns:
            {
                "content": str,
                "model": str,
                "prompt_tokens": int,
                "completion_tokens": int,
            }
        """
        raise NotImplementedError


class MockLLMClient(LLMClient):
    """
    Mock client for testing without API calls.
    Generates placeholder text.
    """
    
    def __init__(self, model_name: str = "mock-model"):
        self.model_name = model_name
    
    def generate(
        self, 
        system_prompt: str, 
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.8,
    ) -> Dict:
        # Extract word target from prompt
        word_target = 3000
        if "Wörter**:" in user_prompt:
            try:
                start = user_prompt.find("Wörter**:") + 10
                end = user_prompt.find(" ", start)
                word_target = int(user_prompt[start:end].replace(",", ""))
            except:
                pass
        
        # Generate placeholder
        placeholder_words = word_target // 10  # Generate ~10% as placeholder
        content = self._generate_placeholder(user_prompt, placeholder_words)
        
        return {
            "content": content,
            "model": self.model_name,
            "prompt_tokens": len(system_prompt.split()) + len(user_prompt.split()),
            "completion_tokens": len(content.split()),
        }
    
    def _generate_placeholder(self, prompt: str, word_count: int) -> str:
        """Generate placeholder text based on prompt"""
        # Extract chapter number
        ch_num = "?"
        if "KAPITEL" in prompt:
            try:
                start = prompt.find("KAPITEL") + 8
                end = prompt.find(" ", start)
                ch_num = prompt[start:end]
            except:
                pass
        
        # Extract location
        location = "Unbekannt"
        if "Story spielt in**:" in prompt:
            try:
                start = prompt.find("Story spielt in**:") + 19
                end = prompt.find("\n", start)
                location = prompt[start:end].strip()
            except:
                pass
        
        # Generate placeholder paragraphs
        paragraphs = [
            f"[KAPITEL {ch_num} - PLACEHOLDER]",
            "",
            f"Die Szene spielt in {location}.",
            "",
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 10,
            "",
            "Der Protagonist bewegt sich durch die Straßen. " * 8,
            "",
            "Ein Dialog entwickelt sich zwischen den Charakteren. " * 6,
            "",
            "[KAPITEL-ENDE MIT HOOK]",
        ]
        
        return "\n\n".join(paragraphs)


class AnthropicClient(LLMClient):
    """
    Anthropic Claude client.
    Requires ANTHROPIC_API_KEY environment variable.
    """
    
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
    
    def generate(
        self, 
        system_prompt: str, 
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.8,
    ) -> Dict:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        return {
            "content": response.content[0].text,
            "model": self.model,
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
        }


# ═══════════════════════════════════════════════════════════════
# STORY GENERATOR
# ═══════════════════════════════════════════════════════════════

class StoryGenerator:
    """
    Main story generator that orchestrates chapter generation.
    """
    
    def __init__(
        self,
        story_outline: StoryOutline,
        story_context: StoryContext,
        story_preferences: StoryPreferences,
        llm_client: LLMClient = None,
    ):
        self.outline = story_outline
        self.context = story_context
        self.preferences = story_preferences
        
        # Use mock client if none provided
        self.llm = llm_client or MockLLMClient()
        
        # Build prompt builder
        self.prompt_builder = PromptBuilder(
            story_outline=story_outline,
            story_context=story_context,
            story_preferences=story_preferences,
        )
        
        # Initialize generated story
        self.story = GeneratedStory(
            title=story_outline.title,
            genre=story_preferences.genre,
        )
    
    def generate_chapter(self, chapter_outline: ChapterOutline) -> GeneratedChapter:
        """Generate a single chapter"""
        
        # Build prompts
        system_prompt = self.prompt_builder.build_system_prompt()
        chapter_prompt = self.prompt_builder.build_chapter_prompt(chapter_outline)
        
        # Calculate max tokens based on word target
        # Rough estimate: 1 word ≈ 1.3 tokens
        max_tokens = int(chapter_outline.word_target * 1.5)
        
        # Generate
        response = self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=chapter_prompt,
            max_tokens=max_tokens,
            temperature=0.8,
        )
        
        # Create generated chapter
        chapter = GeneratedChapter(
            chapter_number=chapter_outline.chapter_number,
            title=f"Kapitel {chapter_outline.chapter_number}",  # Can be enhanced
            content=response["content"],
            word_count=len(response["content"].split()),
            story_location=chapter_outline.story_location,
            reader_location=chapter_outline.reader_location,
            reading_date=str(chapter_outline.reading_date),
            model_used=response["model"],
            prompt_tokens=response["prompt_tokens"],
            completion_tokens=response["completion_tokens"],
        )
        
        # Update state (simplified - in production, extract summary via LLM)
        self.prompt_builder.update_state(
            chapter_number=chapter_outline.chapter_number,
            summary=f"[Kapitel {chapter_outline.chapter_number} generiert - {chapter.word_count} Wörter]",
        )
        
        return chapter
    
    def generate_all(self, progress_callback=None) -> GeneratedStory:
        """
        Generate all chapters.
        
        Args:
            progress_callback: Optional function(chapter_num, total, chapter) 
                              called after each chapter
        """
        total = len(self.outline.chapters)
        
        for i, chapter_outline in enumerate(self.outline.chapters):
            chapter = self.generate_chapter(chapter_outline)
            self.story.add_chapter(chapter)
            
            if progress_callback:
                progress_callback(i + 1, total, chapter)
        
        return self.story
    
    def generate_streaming(self) -> Generator[GeneratedChapter, None, None]:
        """
        Generate chapters as a generator (for streaming).
        """
        for chapter_outline in self.outline.chapters:
            chapter = self.generate_chapter(chapter_outline)
            self.story.add_chapter(chapter)
            yield chapter


# ═══════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION
# ═══════════════════════════════════════════════════════════════

def generate_story(
    story_outline: StoryOutline,
    story_context: StoryContext,
    story_preferences: StoryPreferences,
    use_mock: bool = True,
    progress_callback=None,
) -> GeneratedStory:
    """
    Convenience function to generate a complete story.
    
    Args:
        story_outline: The mapped story outline
        story_context: Story metadata (protagonist, setting, etc.)
        story_preferences: User preferences (genre, spice, etc.)
        use_mock: If True, use mock client (no API calls)
        progress_callback: Optional progress callback
    
    Returns:
        GeneratedStory with all chapters
    """
    # Choose client
    if use_mock:
        client = MockLLMClient()
    else:
        client = AnthropicClient()
    
    # Create generator
    generator = StoryGenerator(
        story_outline=story_outline,
        story_context=story_context,
        story_preferences=story_preferences,
        llm_client=client,
    )
    
    # Generate
    return generator.generate_all(progress_callback=progress_callback)
