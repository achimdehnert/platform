"""
Image Prompt System Models
==========================

Database-driven prompt system for consistent image generation across book projects.
Implements separation of concerns with reusable components.

Naming Convention: writing_prompt_* tables
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


# =============================================================================
# MASTER STYLE - Project-level visual consistency
# =============================================================================

class PromptMasterStyle(models.Model):
    """
    Master style definition for all images in a project.
    Defines the visual DNA that gets applied to every generated image.
    """
    
    class StylePreset(models.TextChoices):
        FAIRY_TALE = 'fairy_tale', '🧚 Märchen (Ivan Bilibin)'
        CINEMATIC = 'cinematic', '🎬 Cinematisch'
        WATERCOLOR = 'watercolor', '🎨 Aquarell Kinderbuch'
        MANGA = 'manga', '📚 Manga/Anime'
        REALISTIC = 'realistic', '📷 Fotorealistisch'
        OIL_PAINTING = 'oil_painting', '🖼️ Ölgemälde'
        FANTASY = 'fantasy', '🐉 Fantasy/Episch'
        STEAMPUNK = 'steampunk', '⚙️ Steampunk'
        GOTHIC = 'gothic', '🦇 Gothic/Dunkel'
        MINIMALIST = 'minimalist', '◻️ Minimalistisch'
        COMIC = 'comic', '💥 Comic/Graphic Novel'
        VINTAGE = 'vintage', '📜 Vintage/Retro'
        PIXEL_ART = 'pixel_art', '👾 Pixel Art'
        IMPRESSIONIST = 'impressionist', '🌻 Impressionismus'
        ART_NOUVEAU = 'art_nouveau', '🌸 Jugendstil'
        CUSTOM = 'custom', '⚙️ Benutzerdefiniert'
    
    project = models.OneToOneField(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='prompt_master_style'
    )
    
    name = models.CharField(
        max_length=100,
        help_text="Name des Stils, z.B. 'Kasachisches Märchen'"
    )
    preset = models.CharField(
        max_length=20,
        choices=StylePreset.choices,
        default=StylePreset.FAIRY_TALE
    )
    
    # Core style prompts
    style_base_prompt = models.TextField(
        help_text="Basis-Stil der bei JEDEM Bild angehängt wird",
        default="Digital fairy tale illustration, rich jewel tones, cinematic composition, 4K detail"
    )
    style_modifiers = models.TextField(
        blank=True,
        help_text="Zusätzliche Stil-Modifikatoren"
    )
    
    # Final editable master prompt - this is what gets used for generation
    master_prompt = models.TextField(
        blank=True,
        help_text="Der finale Master-Prompt für die Bildgenerierung. Wird automatisch aus den Komponenten generiert, kann aber manuell editiert werden."
    )
    
    negative_prompt = models.TextField(
        blank=True,
        default="blurry, low quality, text, watermark, signature, ugly, deformed",
        help_text="Was vermieden werden soll"
    )
    
    # Cultural/thematic elements
    cultural_context = models.TextField(
        blank=True,
        help_text="Kultureller Kontext für Authentizität, z.B. 'Kazakh folk art patterns'"
    )
    artistic_references = models.TextField(
        blank=True,
        help_text="Künstlerische Referenzen, z.B. 'inspired by Ivan Bilibin'"
    )
    
    # Technical defaults
    default_width = models.IntegerField(default=1024)
    default_height = models.IntegerField(default=768)
    guidance_scale = models.FloatField(
        default=7.5,
        validators=[MinValueValidator(1.0), MaxValueValidator(20.0)]
    )
    inference_steps = models.IntegerField(
        default=28,
        validators=[MinValueValidator(10), MaxValueValidator(100)]
    )
    
    # Consistency settings
    use_fixed_seed = models.BooleanField(
        default=False,
        help_text="Festen Seed für Charakter-Konsistenz verwenden"
    )
    fixed_seed = models.IntegerField(
        null=True,
        blank=True,
        help_text="Fester Seed-Wert wenn aktiviert"
    )
    
    # Preview Image
    preview_image = models.ImageField(
        upload_to='master_style_previews/',
        blank=True,
        null=True,
        help_text="Vorschaubild zur Visualisierung des Stils"
    )
    preview_generated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Zeitpunkt der letzten Vorschau-Generierung"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_prompt_master_styles'
        verbose_name = 'Master-Stil'
        verbose_name_plural = 'Master-Stile'
    
    def __str__(self):
        return f"{self.name} ({self.project.title})"
    
    def get_preset_style_prompt(self) -> str:
        """Gibt den Stil-Prompt basierend auf dem gewählten Preset zurück."""
        preset_prompts = {
            'fairy_tale': 'fairy tale illustration style, magical atmosphere, soft lighting, Ivan Bilibin inspired, ornate borders, folk art elements',
            'cinematic': 'cinematic composition, dramatic lighting, movie still, wide angle, depth of field, professional photography',
            'watercolor': 'watercolor painting, soft edges, gentle colors, children book illustration, hand-painted look, pastel tones',
            'manga': 'manga style, anime art, clean lines, vibrant colors, expressive eyes, Japanese illustration style',
            'realistic': 'photorealistic, highly detailed, natural lighting, 8k resolution, professional photograph',
            'oil_painting': 'oil painting style, rich textures, classical art, museum quality, masterpiece brushwork',
            'fantasy': 'epic fantasy art, dramatic lighting, magical elements, detailed armor and weapons, mythical creatures, heroic composition',
            'steampunk': 'steampunk aesthetic, brass and copper machinery, Victorian era, cogs and gears, industrial fantasy, sepia tones',
            'gothic': 'gothic art style, dark atmosphere, dramatic shadows, medieval architecture, mysterious mood, moody lighting',
            'minimalist': 'minimalist illustration, clean lines, simple shapes, limited color palette, modern design, white space',
            'comic': 'comic book style, bold outlines, dynamic action poses, halftone dots, vibrant colors, graphic novel aesthetic',
            'vintage': 'vintage illustration, retro aesthetic, aged paper texture, classic typography, nostalgic colors, 1950s style',
            'pixel_art': 'pixel art style, 16-bit aesthetic, retro gaming, blocky shapes, limited palette, nostalgic',
            'impressionist': 'impressionist painting style, visible brushstrokes, light and color, outdoor scenes, Monet inspired, atmospheric',
            'art_nouveau': 'art nouveau style, organic flowing lines, floral motifs, elegant curves, Alphonse Mucha inspired, decorative borders',
            'custom': '',  # No preset additions for custom
        }
        return preset_prompts.get(self.preset, '')
    
    def build_combined_prompt(self) -> str:
        """Baut den kombinierten Prompt aus allen Komponenten."""
        parts = []
        
        # Add preset style first (if not custom)
        preset_prompt = self.get_preset_style_prompt()
        if preset_prompt:
            parts.append(preset_prompt)
        
        # Add user-defined base prompt
        if self.style_base_prompt:
            parts.append(self.style_base_prompt)
        
        if self.style_modifiers:
            parts.append(self.style_modifiers)
        if self.cultural_context:
            parts.append(self.cultural_context)
        if self.artistic_references:
            parts.append(self.artistic_references)
        
        return ", ".join(filter(None, parts))
    
    def get_full_style_prompt(self) -> str:
        """Gibt den finalen Master-Prompt zurück. Nutzt master_prompt wenn gesetzt, sonst build_combined_prompt."""
        if self.master_prompt:
            return self.master_prompt
        return self.build_combined_prompt()
    
    def get_preview_prompt(self) -> str:
        """Generiert einen Prompt für die Stil-Vorschau."""
        base_scene = "A beautiful landscape scene with a lone figure standing on a hill, looking at the horizon"
        return f"{base_scene}. {self.get_full_style_prompt()}"


# =============================================================================
# CHARACTER PROMPTS - Reusable character descriptions
# =============================================================================

class PromptCharacter(models.Model):
    """
    Reusable character visual definition for consistent depiction.
    Links to BookCharacters for story integration.
    """
    
    class Role(models.TextChoices):
        PROTAGONIST = 'protagonist', '⭐ Protagonist'
        ANTAGONIST = 'antagonist', '👿 Antagonist'
        MENTOR = 'mentor', '🧙 Mentor'
        SIDEKICK = 'sidekick', '🤝 Sidekick'
        LOVE_INTEREST = 'love_interest', '💕 Love Interest'
        SUPPORTING = 'supporting', '👥 Nebenrolle'
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='prompt_characters'
    )
    
    # Link to story character
    book_character = models.OneToOneField(
        'bfagent.Characters',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prompt_definition'
    )
    
    # Basic info
    name = models.CharField(max_length=100)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.SUPPORTING
    )
    
    # Visual description prompts
    appearance_prompt = models.TextField(
        help_text="Physische Erscheinung: Alter, Gesichtszüge, Körperbau, etc."
    )
    clothing_prompt = models.TextField(
        help_text="Typische Kleidung und Accessoires"
    )
    props_prompt = models.TextField(
        blank=True,
        help_text="Charakteristische Gegenstände: Waffen, Schmuck, etc."
    )
    expression_default = models.CharField(
        max_length=100,
        blank=True,
        help_text="Standard-Ausdruck, z.B. 'determined expression'"
    )
    
    # Age variations (for flashbacks/timeskips)
    age_child_prompt = models.TextField(
        blank=True,
        help_text="Erscheinung als Kind (für Rückblenden)"
    )
    age_elder_prompt = models.TextField(
        blank=True,
        help_text="Erscheinung als ältere Person (für Zeitsprünge)"
    )
    
    # Consistency
    reference_seed = models.IntegerField(
        null=True,
        blank=True,
        help_text="Seed für konsistentes Aussehen"
    )
    
    # Generated portrait image
    portrait_image = models.ImageField(
        upload_to='prompt_system/portraits/',
        null=True,
        blank=True,
        help_text="Generiertes Charakter-Portrait"
    )
    portrait_generated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Zeitpunkt der Portrait-Generierung"
    )
    
    # Metadata
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_prompt_characters'
        verbose_name = 'Charakter-Prompt'
        verbose_name_plural = 'Charakter-Prompts'
        ordering = ['sort_order', 'role', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"
    
    def get_full_prompt(self, age_variant: str = 'default') -> str:
        """Generiert vollständigen Charakter-Prompt."""
        parts = []
        
        # Age-specific appearance
        if age_variant == 'child' and self.age_child_prompt:
            parts.append(self.age_child_prompt)
        elif age_variant == 'elder' and self.age_elder_prompt:
            parts.append(self.age_elder_prompt)
        else:
            parts.append(self.appearance_prompt)
        
        parts.append(self.clothing_prompt)
        
        if self.props_prompt:
            parts.append(self.props_prompt)
        if self.expression_default:
            parts.append(self.expression_default)
        
        return ". ".join(filter(None, parts))


# =============================================================================
# LOCATION PROMPTS - Reusable environment descriptions
# =============================================================================

class PromptLocation(models.Model):
    """
    Reusable location/environment definitions for consistent settings.
    """
    
    class LocationType(models.TextChoices):
        INTERIOR = 'interior', '🏠 Innenraum'
        EXTERIOR = 'exterior', '🌄 Außenbereich'
        LANDSCAPE = 'landscape', '🏞️ Landschaft'
        URBAN = 'urban', '🏙️ Stadt'
        SUPERNATURAL = 'supernatural', '✨ Übernatürlich'
    
    class TimeOfDay(models.TextChoices):
        DAWN = 'dawn', '🌅 Morgendämmerung'
        DAY = 'day', '☀️ Tag'
        DUSK = 'dusk', '🌆 Abenddämmerung'
        NIGHT = 'night', '🌙 Nacht'
        ANY = 'any', '⏰ Beliebig'
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='prompt_locations'
    )
    
    # Basic info
    name = models.CharField(
        max_length=100,
        help_text="Name des Ortes, z.B. 'Die Steppe', 'Schamanenhöhle'"
    )
    location_type = models.CharField(
        max_length=20,
        choices=LocationType.choices,
        default=LocationType.EXTERIOR
    )
    
    # Visual prompts
    environment_prompt = models.TextField(
        help_text="Detaillierte Umgebungsbeschreibung"
    )
    architecture_prompt = models.TextField(
        blank=True,
        help_text="Architektur und Strukturen"
    )
    nature_prompt = models.TextField(
        blank=True,
        help_text="Natürliche Elemente: Pflanzen, Wasser, etc."
    )
    
    # Lighting variations
    lighting_default = models.TextField(
        blank=True,
        help_text="Standard-Beleuchtung"
    )
    lighting_dawn = models.TextField(
        blank=True,
        help_text="Morgendämmerungs-Beleuchtung"
    )
    lighting_night = models.TextField(
        blank=True,
        help_text="Nacht-Beleuchtung"
    )
    
    # Atmosphere
    atmosphere_prompt = models.TextField(
        blank=True,
        help_text="Stimmung und Atmosphäre"
    )
    weather_default = models.CharField(
        max_length=100,
        blank=True,
        help_text="Standard-Wetter"
    )
    
    # Metadata
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Preview image (generated with ComfyUI)
    preview_image = models.ImageField(
        upload_to='prompt_system/location_previews/',
        null=True,
        blank=True,
        help_text="Generierte Ort-Vorschau"
    )
    preview_generated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Zeitpunkt der Vorschau-Generierung"
    )
    
    class Meta:
        db_table = 'writing_prompt_locations'
        verbose_name = 'Ort-Prompt'
        verbose_name_plural = 'Ort-Prompts'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_location_type_display()})"
    
    def get_full_prompt(self, time_of_day: str = 'day') -> str:
        """Generiert vollständigen Ort-Prompt mit Beleuchtung."""
        parts = [self.environment_prompt]
        
        if self.architecture_prompt:
            parts.append(self.architecture_prompt)
        if self.nature_prompt:
            parts.append(self.nature_prompt)
        
        # Time-specific lighting
        if time_of_day == 'dawn' and self.lighting_dawn:
            parts.append(self.lighting_dawn)
        elif time_of_day == 'night' and self.lighting_night:
            parts.append(self.lighting_night)
        elif self.lighting_default:
            parts.append(self.lighting_default)
        
        if self.atmosphere_prompt:
            parts.append(self.atmosphere_prompt)
        
        return ". ".join(filter(None, parts))


# =============================================================================
# CULTURAL ELEMENTS - Glossary for authenticity
# =============================================================================

class PromptCulturalElement(models.Model):
    """
    Cultural glossary for authentic visual representation.
    Maps local terms to visual descriptions.
    """
    
    class Category(models.TextChoices):
        CLOTHING = 'clothing', '👗 Kleidung'
        ARCHITECTURE = 'architecture', '🏛️ Architektur'
        OBJECTS = 'objects', '🏺 Gegenstände'
        ANIMALS = 'animals', '🐎 Tiere'
        NATURE = 'nature', '🌿 Natur'
        SYMBOLS = 'symbols', '🔷 Symbole'
        FOOD = 'food', '🍜 Essen'
        MUSIC = 'music', '🎵 Musik'
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='prompt_cultural_elements'
    )
    
    # Terms
    term_local = models.CharField(
        max_length=100,
        help_text="Lokaler Begriff, z.B. 'Kiiz üy'"
    )
    term_english = models.CharField(
        max_length=100,
        help_text="Englischer Begriff, z.B. 'Yurt'"
    )
    term_german = models.CharField(
        max_length=100,
        blank=True,
        help_text="Deutscher Begriff, z.B. 'Jurte'"
    )
    
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OBJECTS
    )
    
    # Visual description
    description = models.TextField(
        help_text="Allgemeine Beschreibung für Kontext"
    )
    visual_prompt = models.TextField(
        help_text="Wie es im Bild dargestellt werden soll"
    )
    
    # Usage hints
    usage_context = models.TextField(
        blank=True,
        help_text="In welchen Szenen dieses Element typisch vorkommt"
    )
    
    # Metadata
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'writing_prompt_cultural_elements'
        verbose_name = 'Kulturelles Element'
        verbose_name_plural = 'Kulturelle Elemente'
        ordering = ['category', 'sort_order', 'term_english']
        unique_together = ['project', 'term_local']
    
    def __str__(self):
        return f"{self.term_local} ({self.term_english})"


# =============================================================================
# SCENE TEMPLATES - Reusable scene type prompts
# =============================================================================

class PromptSceneTemplate(models.Model):
    """
    Templates for common scene types with placeholders.
    Allows quick prompt generation for typical situations.
    """
    
    class SceneType(models.TextChoices):
        ESTABLISHING = 'establishing', '🏠 Establishing Shot'
        ACTION = 'action', '⚔️ Action/Kampf'
        EMOTIONAL = 'emotional', '💔 Emotional'
        DIALOGUE = 'dialogue', '💬 Dialog'
        DISCOVERY = 'discovery', '🔍 Entdeckung'
        TRANSFORMATION = 'transformation', '✨ Transformation'
        JOURNEY = 'journey', '🚶 Reise'
        CONFRONTATION = 'confrontation', '🆚 Konfrontation'
        CELEBRATION = 'celebration', '🎉 Feier'
        TRAGEDY = 'tragedy', '😢 Tragödie'
    
    class AspectRatio(models.TextChoices):
        LANDSCAPE_16_9 = '16:9', '🖼️ Landscape 16:9'
        LANDSCAPE_2_1 = '2:1', '📖 Book Spread 2:1'
        PORTRAIT_3_4 = '3:4', '📱 Portrait 3:4'
        SQUARE = '1:1', '⬜ Square 1:1'
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='prompt_scene_templates'
    )
    
    # Basic info
    name = models.CharField(
        max_length=100,
        help_text="Name des Templates, z.B. 'Konfrontation mit Bösem'"
    )
    scene_type = models.CharField(
        max_length=20,
        choices=SceneType.choices,
        default=SceneType.ESTABLISHING
    )
    
    # Template prompt with placeholders
    template_prompt = models.TextField(
        help_text="Template mit Platzhaltern: {character}, {location}, {action}, {emotion}"
    )
    
    # Composition hints
    composition_hints = models.TextField(
        blank=True,
        help_text="Kompositions-Hinweise: Kamerawinkel, Fokus, etc."
    )
    recommended_aspect_ratio = models.CharField(
        max_length=10,
        choices=AspectRatio.choices,
        default=AspectRatio.LANDSCAPE_16_9
    )
    
    # Technical overrides (if different from master style)
    override_steps = models.IntegerField(
        null=True,
        blank=True,
        help_text="Überschreibt Master-Style Steps wenn gesetzt"
    )
    override_guidance = models.FloatField(
        null=True,
        blank=True,
        help_text="Überschreibt Master-Style Guidance wenn gesetzt"
    )
    
    # Metadata
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_prompt_scene_templates'
        verbose_name = 'Szenen-Template'
        verbose_name_plural = 'Szenen-Templates'
        ordering = ['scene_type', 'sort_order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_scene_type_display()})"
    
    def render_prompt(
        self,
        character: str = '',
        location: str = '',
        action: str = '',
        emotion: str = ''
    ) -> str:
        """Rendert Template mit übergebenen Werten."""
        prompt = self.template_prompt
        prompt = prompt.replace('{character}', character)
        prompt = prompt.replace('{location}', location)
        prompt = prompt.replace('{action}', action)
        prompt = prompt.replace('{emotion}', emotion)
        
        if self.composition_hints:
            prompt = f"{prompt}. {self.composition_hints}"
        
        return prompt
    
    def get_dimensions(self) -> tuple:
        """Returns (width, height) based on aspect ratio."""
        ratios = {
            '16:9': (1024, 576),
            '2:1': (1200, 600),
            '3:4': (768, 1024),
            '1:1': (768, 768),
        }
        return ratios.get(self.recommended_aspect_ratio, (1024, 768))


# =============================================================================
# GENERATED PROMPT LOG - Audit trail
# =============================================================================

class PromptGenerationLog(models.Model):
    """
    Logs all generated prompts for analysis and improvement.
    Enables learning from successful generations.
    """
    
    class Rating(models.IntegerChoices):
        TERRIBLE = 1, '⭐ Schlecht'
        POOR = 2, '⭐⭐ Mäßig'
        ACCEPTABLE = 3, '⭐⭐⭐ OK'
        GOOD = 4, '⭐⭐⭐⭐ Gut'
        EXCELLENT = 5, '⭐⭐⭐⭐⭐ Exzellent'
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='prompt_generation_logs'
    )
    chapter = models.ForeignKey(
        'bfagent.BookChapters',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    illustration = models.ForeignKey(
        'writing_hub.ChapterIllustration',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Components used
    master_style = models.ForeignKey(
        PromptMasterStyle,
        on_delete=models.SET_NULL,
        null=True
    )
    characters_used = models.ManyToManyField(
        PromptCharacter,
        blank=True
    )
    location_used = models.ForeignKey(
        PromptLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    template_used = models.ForeignKey(
        PromptSceneTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # The actual prompts
    scene_description = models.TextField(
        help_text="Ursprüngliche Szenen-Beschreibung"
    )
    final_prompt = models.TextField(
        help_text="Finaler zusammengesetzter Prompt"
    )
    negative_prompt = models.TextField(
        blank=True
    )
    
    # Technical settings used
    width = models.IntegerField()
    height = models.IntegerField()
    steps = models.IntegerField()
    guidance_scale = models.FloatField()
    seed_used = models.IntegerField(null=True, blank=True)
    
    # Results
    generation_successful = models.BooleanField(default=False)
    generation_time_seconds = models.FloatField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # User feedback
    user_rating = models.IntegerField(
        choices=Rating.choices,
        null=True,
        blank=True
    )
    user_notes = models.TextField(
        blank=True,
        help_text="Notizen zur Verbesserung"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'writing_prompt_generation_logs'
        verbose_name = 'Prompt-Log'
        verbose_name_plural = 'Prompt-Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        status = '✅' if self.generation_successful else '❌'
        return f"{status} {self.created_at.strftime('%Y-%m-%d %H:%M')}"
