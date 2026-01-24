"""
Image Prompt Optimizer
======================

Intelligent prompt optimization for image generation.
Transforms text descriptions into optimized prompts for various backends.

Design Goals:
- Reusable across contexts (scenes, characters, locations, covers)
- Works with cheap/fast LLMs (Groq, Ollama)
- Configurable for different backends (Stable Diffusion, DALL-E, Midjourney)
- Supports style presets and custom modifiers
- Can enhance existing prompts or create new ones

Usage:
    optimizer = ImagePromptOptimizer()
    
    # From scene description
    result = optimizer.optimize_scene(
        description="Emily sits on a park bench, sketching",
        characters=["Emily Wilson"],
        location="Park",
        mood="peaceful",
        time_of_day="morning"
    )
    
    # From any text
    result = optimizer.optimize(
        text="A dragon flying over mountains",
        style="fantasy_digital",
        backend="stable_diffusion"
    )
    
    print(result.prompt)           # Optimized positive prompt
    print(result.negative_prompt)  # Negative prompt
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from apps.bfagent.handlers.base_llm_handler import BaseLLMHandler

logger = logging.getLogger(__name__)


class ImageBackend(Enum):
    """Supported image generation backends"""
    STABLE_DIFFUSION = "stable_diffusion"
    DALLE = "dalle"
    MIDJOURNEY = "midjourney"
    COMFYUI = "comfyui"


class ArtStyle(Enum):
    """Predefined art styles with optimized modifiers"""
    FANTASY_DIGITAL = "fantasy_digital"
    WATERCOLOR = "watercolor"
    OIL_PAINTING = "oil_painting"
    ANIME = "anime"
    REALISTIC = "realistic"
    CONCEPT_ART = "concept_art"
    CHILDRENS_BOOK = "childrens_book"
    NOIR = "noir"
    CINEMATIC = "cinematic"


@dataclass
class PromptResult:
    """Result of prompt optimization"""
    success: bool
    prompt: str = ""
    negative_prompt: str = ""
    style: str = ""
    suggested_settings: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    # Metadata
    original_text: str = ""
    backend: str = "stable_diffusion"
    llm_used: Optional[str] = None


# Style presets with quality modifiers
STYLE_PRESETS = {
    ArtStyle.FANTASY_DIGITAL: {
        "prefix": "digital fantasy art, highly detailed, ",
        "suffix": ", dramatic lighting, vibrant colors, artstation, trending",
        "negative": "blurry, low quality, text, watermark, signature, deformed",
        "settings": {"steps": 30, "cfg": 7.5, "width": 1024, "height": 1024}
    },
    ArtStyle.WATERCOLOR: {
        "prefix": "watercolor painting, soft edges, ",
        "suffix": ", delicate brushstrokes, artistic, traditional media",
        "negative": "digital art, sharp edges, photorealistic, 3d render",
        "settings": {"steps": 25, "cfg": 7.0, "width": 1024, "height": 1024}
    },
    ArtStyle.OIL_PAINTING: {
        "prefix": "oil painting, classical art style, ",
        "suffix": ", rich textures, museum quality, masterpiece",
        "negative": "digital, anime, cartoon, low quality",
        "settings": {"steps": 30, "cfg": 7.5, "width": 1024, "height": 1024}
    },
    ArtStyle.ANIME: {
        "prefix": "anime style, ",
        "suffix": ", detailed, vibrant, studio ghibli inspired",
        "negative": "realistic, photograph, 3d, western cartoon",
        "settings": {"steps": 25, "cfg": 8.0, "width": 832, "height": 1216}
    },
    ArtStyle.REALISTIC: {
        "prefix": "photorealistic, ultra detailed, ",
        "suffix": ", 8k uhd, dslr, professional photography",
        "negative": "cartoon, anime, painting, illustration, drawing",
        "settings": {"steps": 35, "cfg": 6.5, "width": 1024, "height": 1024}
    },
    ArtStyle.CONCEPT_ART: {
        "prefix": "concept art, ",
        "suffix": ", matte painting, cinematic, epic scale, artstation hq",
        "negative": "amateur, sketch, unfinished, blurry",
        "settings": {"steps": 30, "cfg": 7.5, "width": 1216, "height": 832}
    },
    ArtStyle.CHILDRENS_BOOK: {
        "prefix": "children's book illustration, whimsical, ",
        "suffix": ", soft colors, friendly, storybook art",
        "negative": "scary, dark, realistic, violent, adult",
        "settings": {"steps": 25, "cfg": 7.0, "width": 1024, "height": 1024}
    },
    ArtStyle.NOIR: {
        "prefix": "film noir style, high contrast, ",
        "suffix": ", dramatic shadows, moody atmosphere, cinematic",
        "negative": "colorful, bright, cheerful, cartoon",
        "settings": {"steps": 30, "cfg": 7.5, "width": 1024, "height": 1024}
    },
    ArtStyle.CINEMATIC: {
        "prefix": "cinematic still, movie scene, ",
        "suffix": ", professional color grading, depth of field, dramatic lighting",
        "negative": "amateur, snapshot, low quality, cartoon",
        "settings": {"steps": 30, "cfg": 7.0, "width": 1216, "height": 832}
    },
}

# Backend-specific optimizations
BACKEND_OPTIMIZATIONS = {
    ImageBackend.STABLE_DIFFUSION: {
        "max_length": 200,
        "supports_negative": True,
        "quality_boost": ", masterpiece, best quality",
    },
    ImageBackend.DALLE: {
        "max_length": 400,
        "supports_negative": False,
        "quality_boost": "",  # DALL-E doesn't need quality tags
    },
    ImageBackend.MIDJOURNEY: {
        "max_length": 300,
        "supports_negative": False,  # Uses --no instead
        "quality_boost": " --q 2 --v 6",
    },
    ImageBackend.COMFYUI: {
        "max_length": 250,
        "supports_negative": True,
        "quality_boost": ", masterpiece, best quality, highly detailed",
    },
}


class ImagePromptOptimizer(BaseLLMHandler):
    """
    Optimizes text descriptions into effective image generation prompts.
    
    Uses LLM to:
    1. Extract visual elements from text
    2. Add appropriate style modifiers
    3. Structure prompt for optimal generation
    4. Generate matching negative prompts
    """
    
    phase_name = 'image_prompt'  # For WorkflowPhaseLLMConfig
    
    OPTIMIZATION_PROMPT = '''Du bist ein Experte für Bildgenerierungs-Prompts (Stable Diffusion, DALL-E).
Deine Aufgabe: Optimiere die Beschreibung zu einem effektiven Bild-Prompt.

REGELN:
1. Extrahiere NUR visuelle Elemente (was man SIEHT)
2. Beschreibe Komposition, Perspektive, Beleuchtung
3. Füge passende künstlerische Stilbegriffe hinzu
4. Halte den Prompt kompakt aber detailliert (max 150 Wörter)
5. Verwende englische Begriffe für den Prompt

KONTEXT:
- Stil: {style}
- Stimmung: {mood}
- Tageszeit: {time_of_day}
- Charaktere: {characters}
- Ort: {location}

BESCHREIBUNG:
{description}

Antworte NUR mit JSON:
{{
    "prompt": "optimierter englischer Prompt für Bildgenerierung",
    "composition": "Kompositions-Vorschlag (z.B. wide shot, close-up)",
    "lighting": "Beleuchtungs-Vorschlag",
    "key_elements": ["wichtiges Element 1", "Element 2"]
}}'''

    def __init__(self, llm_id: Optional[int] = None):
        super().__init__(llm_id=llm_id)
        self._style_presets = STYLE_PRESETS
        self._backend_opts = BACKEND_OPTIMIZATIONS
    
    def optimize_scene(
        self,
        description: str,
        characters: Optional[List[str]] = None,
        location: str = "",
        mood: str = "neutral",
        time_of_day: str = "day",
        style: ArtStyle = ArtStyle.FANTASY_DIGITAL,
        backend: ImageBackend = ImageBackend.STABLE_DIFFUSION,
    ) -> PromptResult:
        """
        Optimize a scene description for image generation.
        
        This is the main method for scene illustrations.
        """
        # Build context for LLM
        prompt = self.OPTIMIZATION_PROMPT.format(
            style=style.value,
            mood=mood,
            time_of_day=time_of_day,
            characters=", ".join(characters) if characters else "keine",
            location=location or "unbekannt",
            description=description
        )
        
        # Call LLM
        result = self.call_llm(
            system="Du optimierst Texte zu Bildgenerierungs-Prompts. Antworte nur mit JSON.",
            prompt=prompt,
            parse_json=True,
            temperature=0.4
        )
        
        if not result.get('success'):
            # Fallback: Use description directly with style
            return self._fallback_optimize(description, style, backend)
        
        # Build final prompt from LLM result
        llm_data = result.get('data', {})
        return self._build_prompt_result(
            llm_data=llm_data,
            original=description,
            style=style,
            backend=backend,
            llm_name=result.get('llm_name')
        )
    
    def optimize(
        self,
        text: str,
        style: str = "fantasy_digital",
        backend: str = "stable_diffusion",
        mood: str = "neutral",
    ) -> PromptResult:
        """
        Generic optimization for any text.
        
        Args:
            text: Any descriptive text
            style: Style name or ArtStyle enum value
            backend: Backend name or ImageBackend enum value
            mood: Mood description
        """
        # Convert string to enum if needed
        try:
            art_style = ArtStyle(style) if isinstance(style, str) else style
        except ValueError:
            art_style = ArtStyle.FANTASY_DIGITAL
        
        try:
            img_backend = ImageBackend(backend) if isinstance(backend, str) else backend
        except ValueError:
            img_backend = ImageBackend.STABLE_DIFFUSION
        
        return self.optimize_scene(
            description=text,
            mood=mood,
            style=art_style,
            backend=img_backend
        )
    
    def enhance_prompt(
        self,
        existing_prompt: str,
        style: ArtStyle = ArtStyle.FANTASY_DIGITAL,
        backend: ImageBackend = ImageBackend.STABLE_DIFFUSION,
    ) -> PromptResult:
        """
        Enhance an existing prompt with style and quality modifiers.
        
        Use this when you already have a base prompt and just want
        to add style/quality enhancements.
        """
        preset = self._style_presets.get(style, self._style_presets[ArtStyle.FANTASY_DIGITAL])
        backend_opts = self._backend_opts.get(backend, self._backend_opts[ImageBackend.STABLE_DIFFUSION])
        
        # Build enhanced prompt
        enhanced = preset["prefix"] + existing_prompt + preset["suffix"]
        
        if backend_opts.get("quality_boost"):
            enhanced += backend_opts["quality_boost"]
        
        # Truncate if too long
        max_len = backend_opts.get("max_length", 200)
        if len(enhanced) > max_len:
            enhanced = enhanced[:max_len-3] + "..."
        
        return PromptResult(
            success=True,
            prompt=enhanced,
            negative_prompt=preset["negative"] if backend_opts.get("supports_negative") else "",
            style=style.value,
            suggested_settings=preset["settings"],
            original_text=existing_prompt,
            backend=backend.value
        )
    
    def _build_prompt_result(
        self,
        llm_data: Dict[str, Any],
        original: str,
        style: ArtStyle,
        backend: ImageBackend,
        llm_name: Optional[str] = None
    ) -> PromptResult:
        """Build final PromptResult from LLM output"""
        preset = self._style_presets.get(style, self._style_presets[ArtStyle.FANTASY_DIGITAL])
        backend_opts = self._backend_opts.get(backend, self._backend_opts[ImageBackend.STABLE_DIFFUSION])
        
        # Get LLM-generated prompt
        base_prompt = llm_data.get('prompt', original)
        
        # Add composition and lighting if provided
        composition = llm_data.get('composition', '')
        lighting = llm_data.get('lighting', '')
        
        # Build full prompt
        parts = []
        if composition:
            parts.append(composition)
        parts.append(base_prompt)
        if lighting:
            parts.append(lighting)
        
        full_prompt = preset["prefix"] + ", ".join(parts) + preset["suffix"]
        
        if backend_opts.get("quality_boost"):
            full_prompt += backend_opts["quality_boost"]
        
        # Truncate if needed
        max_len = backend_opts.get("max_length", 200)
        if len(full_prompt) > max_len:
            full_prompt = full_prompt[:max_len-3] + "..."
        
        return PromptResult(
            success=True,
            prompt=full_prompt,
            negative_prompt=preset["negative"] if backend_opts.get("supports_negative") else "",
            style=style.value,
            suggested_settings=preset["settings"],
            original_text=original,
            backend=backend.value,
            llm_used=llm_name
        )
    
    def _fallback_optimize(
        self,
        description: str,
        style: ArtStyle,
        backend: ImageBackend
    ) -> PromptResult:
        """Fallback when LLM is not available"""
        logger.warning("Using fallback optimization (no LLM)")
        
        # Simple keyword extraction
        keywords = description[:150]  # First 150 chars
        
        return self.enhance_prompt(
            existing_prompt=keywords,
            style=style,
            backend=backend
        )
    
    @classmethod
    def get_available_styles(cls) -> List[Dict[str, str]]:
        """Get list of available art styles for UI"""
        return [
            {"id": style.value, "name": style.value.replace("_", " ").title()}
            for style in ArtStyle
        ]
    
    @classmethod
    def get_available_backends(cls) -> List[Dict[str, str]]:
        """Get list of available backends for UI"""
        return [
            {"id": backend.value, "name": backend.value.replace("_", " ").title()}
            for backend in ImageBackend
        ]
