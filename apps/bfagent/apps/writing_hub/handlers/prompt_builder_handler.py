"""
Prompt Builder Handler
======================

Business logic for building image generation prompts from database components.
Implements separation of concerns - this handler only deals with prompt assembly.

Usage:
    handler = PromptBuilderHandler(project_id=3)
    prompt = handler.build_chapter_prompt(chapter, scene_type='action')
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from django.db.models import Q

from apps.writing_hub.models_prompt_system import (
    PromptMasterStyle,
    PromptCharacter,
    PromptLocation,
    PromptCulturalElement,
    PromptSceneTemplate,
    PromptGenerationLog,
)

logger = logging.getLogger(__name__)


@dataclass
class PromptResult:
    """Result of prompt building operation."""
    success: bool
    prompt: str
    negative_prompt: str
    width: int
    height: int
    steps: int
    guidance_scale: float
    seed: Optional[int]
    components_used: Dict[str, Any]
    error: Optional[str] = None


class PromptBuilderHandler:
    """
    Handles building image generation prompts from database components.
    
    Responsibilities:
    - Fetch and combine prompt components
    - Apply master style to all prompts
    - Detect characters and locations from text
    - Log generated prompts for analysis
    """
    
    def __init__(self, project_id: int):
        self.project_id = project_id
        self._master_style: Optional[PromptMasterStyle] = None
        self._characters: Optional[List[PromptCharacter]] = None
        self._locations: Optional[List[PromptLocation]] = None
        self._cultural_elements: Optional[List[PromptCulturalElement]] = None
    
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
    def characters(self) -> List[PromptCharacter]:
        """Lazy-load active characters."""
        if self._characters is None:
            self._characters = list(
                PromptCharacter.objects.filter(
                    project_id=self.project_id,
                    is_active=True
                ).order_by('sort_order')
            )
        return self._characters
    
    @property
    def locations(self) -> List[PromptLocation]:
        """Lazy-load active locations."""
        if self._locations is None:
            self._locations = list(
                PromptLocation.objects.filter(
                    project_id=self.project_id,
                    is_active=True
                ).order_by('sort_order')
            )
        return self._locations
    
    @property
    def cultural_elements(self) -> List[PromptCulturalElement]:
        """Lazy-load cultural elements."""
        if self._cultural_elements is None:
            self._cultural_elements = list(
                PromptCulturalElement.objects.filter(
                    project_id=self.project_id,
                    is_active=True
                )
            )
        return self._cultural_elements
    
    def build_prompt(
        self,
        scene_description: str,
        character_names: Optional[List[str]] = None,
        location_name: Optional[str] = None,
        scene_type: str = 'establishing',
        time_of_day: str = 'day',
        age_variant: str = 'default',
        override_width: Optional[int] = None,
        override_height: Optional[int] = None,
    ) -> PromptResult:
        """
        Build a complete prompt from components.
        
        Args:
            scene_description: Base description of the scene
            character_names: Names of characters to include
            location_name: Name of location to use
            scene_type: Type of scene for template selection
            time_of_day: dawn/day/dusk/night for lighting
            age_variant: default/child/elder for character age
            override_width: Override default width
            override_height: Override default height
        
        Returns:
            PromptResult with complete prompt and settings
        """
        if not self.master_style:
            return PromptResult(
                success=False,
                prompt='',
                negative_prompt='',
                width=1024,
                height=768,
                steps=28,
                guidance_scale=7.5,
                seed=None,
                components_used={},
                error='Kein Master-Stil für dieses Projekt definiert'
            )
        
        prompt_parts = []
        components_used = {
            'master_style': self.master_style.name,
            'characters': [],
            'location': None,
            'cultural_elements': [],
            'template': None,
        }
        
        # 1. Scene description (primary)
        prompt_parts.append(scene_description)
        
        # 2. Characters
        if character_names:
            for name in character_names[:2]:  # Max 2 characters
                char = self._find_character(name)
                if char:
                    prompt_parts.append(char.get_full_prompt(age_variant))
                    components_used['characters'].append(char.name)
        else:
            # Auto-detect characters from scene description
            detected = self._detect_characters(scene_description)
            for char in detected[:2]:
                prompt_parts.append(char.get_full_prompt(age_variant))
                components_used['characters'].append(char.name)
        
        # 3. Location
        location = None
        if location_name:
            location = self._find_location(location_name)
        else:
            location = self._detect_location(scene_description)
        
        if location:
            prompt_parts.append(location.get_full_prompt(time_of_day))
            components_used['location'] = location.name
        
        # 4. Cultural elements (auto-detect and replace)
        enriched_prompt = self._enrich_with_cultural_elements(
            ". ".join(prompt_parts)
        )
        for elem in self._get_used_cultural_elements(scene_description):
            components_used['cultural_elements'].append(elem.term_english)
        
        # 5. Scene template (if available)
        template = self._find_scene_template(scene_type)
        if template:
            components_used['template'] = template.name
        
        # 6. Master style (always appended)
        final_prompt = f"{enriched_prompt}. {self.master_style.get_full_style_prompt()}"
        
        # Settings
        width = override_width or self.master_style.default_width
        height = override_height or self.master_style.default_height
        
        if template:
            dims = template.get_dimensions()
            if not override_width:
                width = dims[0]
            if not override_height:
                height = dims[1]
        
        steps = self.master_style.inference_steps
        if template and template.override_steps:
            steps = template.override_steps
        
        guidance = self.master_style.guidance_scale
        if template and template.override_guidance:
            guidance = template.override_guidance
        
        seed = None
        if self.master_style.use_fixed_seed:
            seed = self.master_style.fixed_seed
        
        return PromptResult(
            success=True,
            prompt=final_prompt,
            negative_prompt=self.master_style.negative_prompt,
            width=width,
            height=height,
            steps=steps,
            guidance_scale=guidance,
            seed=seed,
            components_used=components_used,
        )
    
    def build_chapter_prompt(
        self,
        chapter,
        scene_type: str = 'establishing',
        time_of_day: str = 'day',
    ) -> PromptResult:
        """
        Build prompt for a chapter illustration.
        Auto-detects characters and location from chapter content.
        """
        # Extract scene from chapter
        scene_description = self._extract_scene_from_chapter(chapter)
        
        # Detect characters mentioned in chapter
        character_names = self._detect_character_names_in_text(
            chapter.content or chapter.outline or ''
        )
        
        return self.build_prompt(
            scene_description=scene_description,
            character_names=character_names,
            scene_type=scene_type,
            time_of_day=time_of_day,
        )
    
    def log_generation(
        self,
        result: PromptResult,
        chapter=None,
        illustration=None,
        scene_description: str = '',
        generation_successful: bool = False,
        generation_time: float = 0,
        error_message: str = '',
    ) -> PromptGenerationLog:
        """Log a prompt generation for analysis."""
        log = PromptGenerationLog.objects.create(
            project_id=self.project_id,
            chapter=chapter,
            illustration=illustration,
            master_style=self.master_style,
            scene_description=scene_description,
            final_prompt=result.prompt,
            negative_prompt=result.negative_prompt,
            width=result.width,
            height=result.height,
            steps=result.steps,
            guidance_scale=result.guidance_scale,
            seed_used=result.seed,
            generation_successful=generation_successful,
            generation_time_seconds=generation_time,
            error_message=error_message,
        )
        
        # Link used characters
        for char_name in result.components_used.get('characters', []):
            char = self._find_character(char_name)
            if char:
                log.characters_used.add(char)
        
        # Link location
        loc_name = result.components_used.get('location')
        if loc_name:
            loc = self._find_location(loc_name)
            if loc:
                log.location_used = loc
                log.save()
        
        # Link template
        template_name = result.components_used.get('template')
        if template_name:
            try:
                template = PromptSceneTemplate.objects.get(
                    project_id=self.project_id,
                    name=template_name
                )
                log.template_used = template
                log.save()
            except PromptSceneTemplate.DoesNotExist:
                pass
        
        return log
    
    # =========================================================================
    # PRIVATE HELPER METHODS
    # =========================================================================
    
    def _find_character(self, name: str) -> Optional[PromptCharacter]:
        """Find character by name (case-insensitive)."""
        for char in self.characters:
            if char.name.lower() == name.lower():
                return char
        return None
    
    def _find_location(self, name: str) -> Optional[PromptLocation]:
        """Find location by name (case-insensitive)."""
        for loc in self.locations:
            if loc.name.lower() == name.lower():
                return loc
        return None
    
    def _find_scene_template(self, scene_type: str) -> Optional[PromptSceneTemplate]:
        """Find scene template by type."""
        try:
            return PromptSceneTemplate.objects.filter(
                project_id=self.project_id,
                scene_type=scene_type,
                is_active=True
            ).first()
        except Exception:
            return None
    
    def _detect_characters(self, text: str) -> List[PromptCharacter]:
        """Detect which characters are mentioned in text."""
        detected = []
        text_lower = text.lower()
        
        for char in self.characters:
            if char.name.lower() in text_lower:
                detected.append(char)
        
        return detected
    
    def _detect_character_names_in_text(self, text: str) -> List[str]:
        """Extract character names mentioned in text."""
        names = []
        text_lower = text.lower()
        
        for char in self.characters:
            if char.name.lower() in text_lower:
                names.append(char.name)
        
        return names
    
    def _detect_location(self, text: str) -> Optional[PromptLocation]:
        """Detect which location is mentioned in text."""
        text_lower = text.lower()
        
        for loc in self.locations:
            if loc.name.lower() in text_lower:
                return loc
        
        return None
    
    def _enrich_with_cultural_elements(self, prompt: str) -> str:
        """Replace cultural terms with visual descriptions."""
        enriched = prompt
        
        for elem in self.cultural_elements:
            # Replace local term with visual prompt
            pattern = re.compile(re.escape(elem.term_local), re.IGNORECASE)
            if pattern.search(enriched):
                enriched = pattern.sub(
                    f"{elem.term_local} ({elem.visual_prompt})",
                    enriched,
                    count=1
                )
        
        return enriched
    
    def _get_used_cultural_elements(self, text: str) -> List[PromptCulturalElement]:
        """Get cultural elements mentioned in text."""
        used = []
        text_lower = text.lower()
        
        for elem in self.cultural_elements:
            if elem.term_local.lower() in text_lower:
                used.append(elem)
            elif elem.term_english.lower() in text_lower:
                used.append(elem)
        
        return used
    
    def _extract_scene_from_chapter(self, chapter) -> str:
        """Extract scene description from chapter content."""
        # Priority: outline > first paragraph of content > title
        if chapter.outline:
            return chapter.outline[:500]
        
        if chapter.content:
            # Get first paragraph
            paragraphs = chapter.content.split('\n\n')
            if paragraphs:
                return paragraphs[0][:500]
        
        return f"Scene from chapter: {chapter.title}"


# =============================================================================
# PRESET TEMPLATES
# =============================================================================

class PromptPresetFactory:
    """
    Factory for creating preset prompt configurations.
    Use these to quickly set up a project's prompt system.
    """
    
    @staticmethod
    def create_kazakh_fairytale_preset(project_id: int) -> Dict[str, Any]:
        """
        Create the Kazakh Fairytale preset from the documentation.
        Returns dict of created objects.
        """
        from apps.bfagent.models import BookProjects
        
        project = BookProjects.objects.get(id=project_id)
        created = {'master_style': None, 'characters': [], 'locations': [], 'elements': [], 'templates': []}
        
        # Master Style
        master_style, _ = PromptMasterStyle.objects.update_or_create(
            project=project,
            defaults={
                'name': 'Kasachisches Märchen',
                'preset': 'fairy_tale',
                'style_base_prompt': (
                    'Digital fairy tale illustration, Eastern European storybook aesthetic, '
                    'rich jewel tones with gold accents, dramatic lighting with warm amber '
                    'highlights and deep blue shadows, textured brushwork, ornate decorative '
                    'borders, cinematic composition, 4K detail, atmospheric depth'
                ),
                'cultural_context': 'Kazakh folk art patterns, tribal motifs',
                'artistic_references': 'inspired by Ivan Bilibin',
                'negative_prompt': 'blurry, low quality, text, watermark, ugly, deformed, photo, 3d render',
                'default_width': 1024,
                'default_height': 768,
                'guidance_scale': 4.5,
                'inference_steps': 28,
            }
        )
        created['master_style'] = master_style
        
        # Protagonist
        char, _ = PromptCharacter.objects.update_or_create(
            project=project,
            name='Arman',
            defaults={
                'role': 'protagonist',
                'appearance_prompt': (
                    'Young Kazakh hero, 16-18 years old, athletic build, determined expression, '
                    'traditional Kazakh features with almond-shaped dark eyes, short black hair'
                ),
                'clothing_prompt': (
                    'Wearing traditional chapan (embroidered robe) in deep blue with gold '
                    'geometric patterns, leather boots, felt hat (borik)'
                ),
                'props_prompt': 'Carries an ancestral dagger with turquoise inlay',
                'expression_default': 'expression of courage and wonder',
                'age_child_prompt': (
                    'Young Kazakh boy, 8 years old, curious expression, traditional clothing'
                ),
                'sort_order': 1,
            }
        )
        created['characters'].append(char)
        
        # Mentor
        mentor, _ = PromptCharacter.objects.update_or_create(
            project=project,
            name='Baqsy',
            defaults={
                'role': 'mentor',
                'appearance_prompt': (
                    'Ancient Kazakh shaman (baqsy) with long white beard, wise eyes'
                ),
                'clothing_prompt': (
                    'Wearing ceremonial costume with owl feathers and bone ornaments'
                ),
                'props_prompt': 'Sacred instruments: kobyz and drum',
                'expression_default': 'mystical and knowing expression',
                'sort_order': 2,
            }
        )
        created['characters'].append(mentor)
        
        # Locations
        steppe, _ = PromptLocation.objects.update_or_create(
            project=project,
            name='Die Steppe',
            defaults={
                'location_type': 'landscape',
                'environment_prompt': (
                    'Vast golden Kazakh steppe, wind sweeping through feather grass (stipa), '
                    'endless horizon, Tian Shan mountains in distance'
                ),
                'nature_prompt': 'Wild horses grazing, eagles circling overhead',
                'lighting_default': 'Golden sunlight, dramatic sky',
                'lighting_dawn': 'Crimson sunrise, rays breaking through clouds',
                'lighting_night': 'Star-filled sky, moonlit landscape',
                'atmosphere_prompt': 'Epic and mystical atmosphere',
                'sort_order': 1,
            }
        )
        created['locations'].append(steppe)
        
        yurt, _ = PromptLocation.objects.update_or_create(
            project=project,
            name='Die Jurte',
            defaults={
                'location_type': 'interior',
                'environment_prompt': (
                    'Traditional yurt (ger) interior, felt walls covered in colorful '
                    'shyrdak carpets, central fire pit'
                ),
                'architecture_prompt': 'Circular structure, wooden frame, smoke hole in roof',
                'lighting_default': 'Warm firelight illuminating felt walls',
                'lighting_night': 'Amber interior contrasting with cool blue moonlit exterior through opening',
                'atmosphere_prompt': 'Cozy and sacred atmosphere',
                'sort_order': 2,
            }
        )
        created['locations'].append(yurt)
        
        # Cultural Elements
        elements_data = [
            ('Kiiz üy', 'Yurt', 'Jurte', 'architecture', 
             'Traditional Kazakh felt tent with shyrdak carpets and ornate decorations'),
            ('Berkut', 'Golden Eagle', 'Steinadler', 'animals',
             'Majestic golden eagle, symbol of strength and freedom'),
            ('Chapan', 'Embroidered Robe', 'Bestickte Robe', 'clothing',
             'Ceremonial robe with gold geometric patterns and rich colors'),
            ('Dombra', 'Dombra', 'Dombra', 'music',
             'Traditional two-stringed Kazakh lute, wooden instrument'),
            ('Borik', 'Felt Hat', 'Filzmütze', 'clothing',
             'Traditional Kazakh felt cap with ornamental patterns'),
        ]
        
        for local, english, german, category, visual in elements_data:
            elem, _ = PromptCulturalElement.objects.update_or_create(
                project=project,
                term_local=local,
                defaults={
                    'term_english': english,
                    'term_german': german,
                    'category': category,
                    'description': f'{english} - traditional Kazakh {category}',
                    'visual_prompt': visual,
                }
            )
            created['elements'].append(elem)
        
        # Scene Templates
        templates_data = [
            ('Kindheit', 'establishing', 
             '{character} in childhood scene, {location}, nostalgic atmosphere, {emotion}',
             'Low angle, warm colors, soft focus on background'),
            ('Erwachen', 'discovery',
             '{character} receiving vision or revelation, {location}, mystical light, {emotion}',
             'Dramatic low-angle, rays of light, epic composition'),
            ('Konfrontation', 'confrontation',
             'Epic battle scene, {character} facing enemy, {location}, dramatic chiaroscuro, {emotion}',
             'Dynamic diagonal composition, high contrast, climactic moment'),
            ('Triumph', 'celebration',
             '{character} triumphant return, {location}, joyful celebration, {emotion}',
             'Wide shot, golden hour lighting, sense of completion'),
        ]
        
        for name, scene_type, template, composition in templates_data:
            tmpl, _ = PromptSceneTemplate.objects.update_or_create(
                project=project,
                name=name,
                defaults={
                    'scene_type': scene_type,
                    'template_prompt': template,
                    'composition_hints': composition,
                }
            )
            created['templates'].append(tmpl)
        
        logger.info(f"Created Kazakh Fairytale preset for project {project_id}")
        return created
