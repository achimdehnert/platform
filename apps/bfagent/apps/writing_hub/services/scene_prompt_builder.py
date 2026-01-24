"""
Scene Prompt Builder
====================

Builds optimized image generation prompts from analyzed chapter scenes.
Combines scene data with project style, characters, and mood modifiers.

Now with LLM-based prompt optimization for better image results!

Usage:
    builder = ScenePromptBuilder(project_id=17)
    result = builder.build_from_scene(scene_data, master_style)
    
    # With LLM optimization (recommended):
    result = builder.build_optimized(scene_data, use_llm=True)
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from apps.writing_hub.models import ChapterSceneAnalysis
from apps.writing_hub.models_prompt_system import (
    PromptMasterStyle,
    PromptCharacter,
    PromptLocation,
)

logger = logging.getLogger(__name__)


# Mood to visual modifier mapping
MOOD_MODIFIERS = {
    'mysterious': {
        'lighting': 'dramatic shadows, chiaroscuro lighting',
        'colors': 'deep blues, purples, and dark greens',
        'atmosphere': 'misty, ethereal, enigmatic',
    },
    'romantic': {
        'lighting': 'soft golden hour light, warm glow',
        'colors': 'warm pinks, soft reds, gentle oranges',
        'atmosphere': 'dreamy, intimate, tender',
    },
    'tense': {
        'lighting': 'harsh contrasts, stark lighting',
        'colors': 'desaturated, cold grays and blues',
        'atmosphere': 'suspenseful, uneasy, electric',
    },
    'peaceful': {
        'lighting': 'soft diffused natural light',
        'colors': 'gentle pastels, soft greens and blues',
        'atmosphere': 'serene, calm, tranquil',
    },
    'dramatic': {
        'lighting': 'dynamic lighting, strong highlights',
        'colors': 'bold, high contrast, vivid',
        'atmosphere': 'intense, powerful, epic',
    },
    'melancholic': {
        'lighting': 'overcast, muted, subdued',
        'colors': 'faded blues, grays, muted earth tones',
        'atmosphere': 'wistful, nostalgic, somber',
    },
    'joyful': {
        'lighting': 'bright, sunny, vibrant',
        'colors': 'warm yellows, oranges, bright greens',
        'atmosphere': 'cheerful, lively, uplifting',
    },
    'action': {
        'lighting': 'dynamic, motion blur, sharp highlights',
        'colors': 'high energy colors, reds and oranges',
        'atmosphere': 'kinetic, explosive, thrilling',
    },
    'dark': {
        'lighting': 'low key, minimal light sources',
        'colors': 'blacks, deep reds, shadows',
        'atmosphere': 'ominous, foreboding, sinister',
    },
}

# Time of day lighting presets
TIME_LIGHTING = {
    'morning': 'soft morning light, gentle golden rays, dawn atmosphere',
    'day': 'bright natural daylight, clear visibility',
    'evening': 'warm sunset glow, orange and pink sky, golden hour',
    'night': 'moonlight, stars, artificial lights, nocturnal ambiance',
}


@dataclass
class ScenePromptResult:
    """Result of scene prompt building."""
    success: bool
    prompt: str
    negative_prompt: str
    scene_title: str
    mood: str
    width: int
    height: int
    steps: int
    guidance_scale: float
    components: Dict[str, Any]
    error: Optional[str] = None


class ScenePromptBuilder:
    """
    Builds image generation prompts from analyzed scene data.
    
    Combines:
    - Scene description and visual elements
    - Character appearances (from PromptCharacter DB)
    - Mood-based lighting and color modifiers
    - Master style settings
    """
    
    def __init__(self, project_id: int):
        self.project_id = project_id
        self._master_style: Optional[PromptMasterStyle] = None
        self._characters: Optional[Dict[str, PromptCharacter]] = None
        self._locations: Optional[Dict[str, PromptLocation]] = None
    
    @property
    def master_style(self) -> Optional[PromptMasterStyle]:
        """Lazy-load master style."""
        if self._master_style is None:
            try:
                self._master_style = PromptMasterStyle.objects.get(
                    project_id=self.project_id
                )
            except PromptMasterStyle.DoesNotExist:
                logger.warning(f"No master style for project {self.project_id}")
        return self._master_style
    
    @property
    def characters(self) -> Dict[str, PromptCharacter]:
        """Lazy-load characters indexed by name."""
        if self._characters is None:
            self._characters = {}
            chars = PromptCharacter.objects.filter(
                project_id=self.project_id,
                is_active=True
            )
            for char in chars:
                self._characters[char.name.lower()] = char
        return self._characters
    
    @property
    def locations(self) -> Dict[str, PromptLocation]:
        """Lazy-load locations indexed by name."""
        if self._locations is None:
            self._locations = {}
            locs = PromptLocation.objects.filter(
                project_id=self.project_id,
                is_active=True
            )
            for loc in locs:
                self._locations[loc.name.lower()] = loc
        return self._locations
    
    def build_from_analysis(
        self,
        analysis: ChapterSceneAnalysis,
        scene_index: int = 0
    ) -> ScenePromptResult:
        """
        Build prompt from a ChapterSceneAnalysis.
        
        Args:
            analysis: The chapter scene analysis
            scene_index: Which scene to use (0-based)
            
        Returns:
            ScenePromptResult with complete prompt
        """
        scene = analysis.get_scene(scene_index)
        if not scene:
            return ScenePromptResult(
                success=False,
                prompt='',
                negative_prompt='',
                scene_title='',
                mood='',
                width=1024,
                height=768,
                steps=28,
                guidance_scale=7.5,
                components={},
                error=f'Scene index {scene_index} not found in analysis'
            )
        
        return self.build_from_scene(
            scene_data=scene,
            overall_mood=analysis.chapter_atmosphere,
            color_mood=analysis.overall_color_mood
        )
    
    def build_from_scene(
        self,
        scene_data: Dict[str, Any],
        overall_mood: str = '',
        color_mood: str = ''
    ) -> ScenePromptResult:
        """
        Build prompt from scene data dictionary.
        
        Args:
            scene_data: Scene dict from analysis
            overall_mood: Chapter's overall mood
            color_mood: Chapter's color palette mood
            
        Returns:
            ScenePromptResult with complete prompt
        """
        if not self.master_style:
            return ScenePromptResult(
                success=False,
                prompt='',
                negative_prompt='',
                scene_title='',
                mood='',
                width=1024,
                height=768,
                steps=28,
                guidance_scale=7.5,
                components={},
                error='No master style defined for project'
            )
        
        prompt_parts = []
        components = {
            'scene': scene_data.get('title', ''),
            'characters': [],
            'location': None,
            'mood_modifiers': [],
        }
        
        # 1. Main scene description
        description = scene_data.get('description', '')
        if description:
            prompt_parts.append(description)
        
        # 2. Characters with their visual descriptions
        characters = scene_data.get('characters', [])
        char_actions = scene_data.get('character_actions', {})
        
        for char_name in characters[:2]:  # Max 2 characters
            char_prompt = self._build_character_prompt(char_name, char_actions)
            if char_prompt:
                prompt_parts.append(char_prompt)
                components['characters'].append(char_name)
        
        # 3. Location/Setting
        location_desc = scene_data.get('location', '')
        time_of_day = scene_data.get('time_of_day', 'day')
        
        location_prompt = self._build_location_prompt(location_desc, time_of_day)
        if location_prompt:
            prompt_parts.append(location_prompt)
            components['location'] = location_desc
        
        # 4. Lighting from scene
        lighting = scene_data.get('lighting', '')
        if lighting:
            prompt_parts.append(f"Lighting: {lighting}")
        
        # 5. Mood modifiers
        mood = scene_data.get('mood', 'peaceful')
        mood_prompt = self._build_mood_prompt(mood)
        if mood_prompt:
            prompt_parts.append(mood_prompt)
            components['mood_modifiers'].append(mood)
        
        # 6. Visual elements
        visual_elements = scene_data.get('visual_elements', [])
        if visual_elements:
            elements_str = ', '.join(visual_elements[:5])
            prompt_parts.append(f"Key elements: {elements_str}")
        
        # 7. Composition suggestion
        composition = scene_data.get('composition_suggestion', '')
        if composition:
            prompt_parts.append(f"Composition: {composition}")
        
        # 8. Color mood from chapter analysis
        if color_mood:
            prompt_parts.append(f"Color palette: {color_mood}")
        
        # 9. Master style (always last)
        style_prompt = self.master_style.get_full_style_prompt()
        prompt_parts.append(style_prompt)
        
        # Combine all parts
        final_prompt = '. '.join(filter(None, prompt_parts))
        
        return ScenePromptResult(
            success=True,
            prompt=final_prompt,
            negative_prompt=self.master_style.negative_prompt,
            scene_title=scene_data.get('title', 'Unnamed Scene'),
            mood=mood,
            width=self.master_style.default_width,
            height=self.master_style.default_height,
            steps=self.master_style.inference_steps,
            guidance_scale=self.master_style.guidance_scale,
            components=components,
        )
    
    def _build_character_prompt(
        self, 
        char_name: str, 
        char_actions: Dict[str, str]
    ) -> str:
        """Build prompt part for a character."""
        parts = []
        
        # Check if we have DB definition for this character
        char_key = char_name.lower()
        if char_key in self.characters:
            db_char = self.characters[char_key]
            # Use full character prompt from DB
            char_visual = db_char.get_full_prompt()
            parts.append(f"{char_name}: {char_visual}")
        else:
            # Just use the name
            parts.append(char_name)
        
        # Add action if specified
        action = char_actions.get(char_name, '')
        if action:
            parts.append(action)
        
        return ', '.join(parts) if parts else ''
    
    def _build_location_prompt(
        self, 
        location_desc: str, 
        time_of_day: str
    ) -> str:
        """Build prompt part for location/setting."""
        parts = []
        
        # Check if we have DB definition for this location
        if location_desc:
            loc_key = location_desc.lower()
            for key, loc in self.locations.items():
                if key in loc_key or loc_key in key:
                    # Use DB location prompt
                    parts.append(loc.get_full_prompt(time_of_day))
                    break
            else:
                # Use scene's location description
                parts.append(f"Setting: {location_desc}")
        
        # Add time-based lighting
        time_lighting = TIME_LIGHTING.get(time_of_day, TIME_LIGHTING['day'])
        parts.append(time_lighting)
        
        return '. '.join(parts) if parts else ''
    
    def _build_mood_prompt(self, mood: str) -> str:
        """Build prompt part for mood/atmosphere."""
        mood_lower = mood.lower()
        
        if mood_lower in MOOD_MODIFIERS:
            mod = MOOD_MODIFIERS[mood_lower]
            parts = [
                mod.get('atmosphere', ''),
                mod.get('lighting', ''),
                mod.get('colors', ''),
            ]
            return ', '.join(filter(None, parts))
        
        return f"{mood} atmosphere"
    
    def build_multiple_scenes(
        self,
        analysis: ChapterSceneAnalysis
    ) -> List[ScenePromptResult]:
        """
        Build prompts for all scenes in an analysis.
        
        Args:
            analysis: The chapter scene analysis
            
        Returns:
            List of ScenePromptResult for each scene
        """
        results = []
        
        for i, scene in enumerate(analysis.scenes):
            result = self.build_from_scene(
                scene_data=scene,
                overall_mood=analysis.chapter_atmosphere,
                color_mood=analysis.overall_color_mood
            )
            results.append(result)
        
        return results
    
    def build_optimized(
        self,
        scene_data: Dict[str, Any],
        overall_mood: str = '',
        color_mood: str = '',
        use_llm: bool = True
    ) -> ScenePromptResult:
        """
        Build an LLM-optimized prompt for better image generation.
        
        Uses ImagePromptOptimizer to transform the scene description
        into a more effective image generation prompt.
        
        Args:
            scene_data: Scene dict from analysis
            overall_mood: Chapter's overall mood
            color_mood: Chapter's color palette mood
            use_llm: Whether to use LLM optimization (default True)
            
        Returns:
            ScenePromptResult with optimized prompt
        """
        if not use_llm:
            return self.build_from_scene(scene_data, overall_mood, color_mood)
        
        try:
            from apps.bfagent.handlers.image_prompt_optimizer import (
                ImagePromptOptimizer, ArtStyle, ImageBackend
            )
            
            optimizer = ImagePromptOptimizer()
            
            # Extract scene info
            description = scene_data.get('description', '')
            characters = scene_data.get('characters', [])
            location = scene_data.get('location', '')
            mood = scene_data.get('mood', overall_mood or 'neutral')
            time_of_day = scene_data.get('time_of_day', 'day')
            
            # Determine style from master_style
            style = ArtStyle.FANTASY_DIGITAL
            if self.master_style:
                style_map = {
                    'watercolor': ArtStyle.WATERCOLOR,
                    'oil': ArtStyle.OIL_PAINTING,
                    'anime': ArtStyle.ANIME,
                    'realistic': ArtStyle.REALISTIC,
                    'concept': ArtStyle.CONCEPT_ART,
                    'children': ArtStyle.CHILDRENS_BOOK,
                    'noir': ArtStyle.NOIR,
                    'cinematic': ArtStyle.CINEMATIC,
                }
                for key, art_style in style_map.items():
                    if key in (self.master_style.art_style or '').lower():
                        style = art_style
                        break
            
            # Call optimizer
            opt_result = optimizer.optimize_scene(
                description=description,
                characters=characters,
                location=location,
                mood=mood,
                time_of_day=time_of_day,
                style=style,
                backend=ImageBackend.COMFYUI
            )
            
            if opt_result.success:
                # Combine optimized prompt with master style if available
                final_prompt = opt_result.prompt
                if self.master_style and self.master_style.style_prefix:
                    final_prompt = f"{self.master_style.style_prefix}, {final_prompt}"
                
                # Use settings from master_style or optimizer
                width = self.master_style.default_width if self.master_style else opt_result.suggested_settings.get('width', 1024)
                height = self.master_style.default_height if self.master_style else opt_result.suggested_settings.get('height', 1024)
                steps = self.master_style.inference_steps if self.master_style else opt_result.suggested_settings.get('steps', 28)
                guidance = self.master_style.guidance_scale if self.master_style else opt_result.suggested_settings.get('cfg', 7.5)
                
                negative = opt_result.negative_prompt
                if self.master_style and self.master_style.negative_prompt:
                    negative = f"{self.master_style.negative_prompt}, {negative}"
                
                return ScenePromptResult(
                    success=True,
                    prompt=final_prompt,
                    negative_prompt=negative,
                    scene_title=scene_data.get('title', 'Unnamed Scene'),
                    mood=mood,
                    width=width,
                    height=height,
                    steps=steps,
                    guidance_scale=guidance,
                    components={
                        'optimized_by': 'ImagePromptOptimizer',
                        'llm_used': opt_result.llm_used,
                        'style': style.value,
                    }
                )
            
        except Exception as e:
            logger.warning(f"LLM optimization failed, using fallback: {e}")
        
        # Fallback to standard builder
        return self.build_from_scene(scene_data, overall_mood, color_mood)


# Convenience function
def build_scene_prompt(
    project_id: int,
    scene_data: Dict[str, Any]
) -> ScenePromptResult:
    """
    Convenience function to build a prompt from scene data.
    
    Args:
        project_id: Project ID for style lookup
        scene_data: Scene dictionary from analysis
        
    Returns:
        ScenePromptResult with prompt
    """
    builder = ScenePromptBuilder(project_id)
    return builder.build_from_scene(scene_data)
