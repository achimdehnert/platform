"""
Django forms for BF Agent - Book Factory Agent Management System
Professional forms with validation and HTMX integration
"""

from django import forms
from django.core.exceptions import ValidationError

# Writing Hub Lookups (DB-driven statt hardcoded)
from apps.writing_hub.models import (
    ContentRating,
    WritingStage,
)

from .models import (
    ActionTemplate,
    AgentAction,
    AgentArtifacts,
    AgentExecutions,
    Agents,
    BookChapters,
    BookProjects,
    BookTypePhase,
    BookTypes,
    Characters,
    FieldUsage,
    Genre,
    GraphQLOperation,
    Llms,
    PhaseActionConfig,
    PlotPoint,
    ProjectPhaseHistory,
    PromptTemplate,
    QueryPerformanceLog,
    StoryArc,
    TargetAudience,
    WorkflowPhase,
    WorkflowPhaseStep,
    WorkflowTemplate,
    Worlds,
    WritingStatus,
)


class BookProjectsForm(forms.ModelForm):
    """Form for creating and editing book projects"""
    
    # DB-driven Dropdown Fields (statt hardcoded choices)
    content_rating = forms.ModelChoiceField(
        queryset=ContentRating.objects.filter(is_active=True).order_by('sort_order'),
        required=False,
        empty_label="Select rating...",
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Content rating (e.g., G, PG, PG-13, R, NC-17)"
    )
    
    status = forms.ModelChoiceField(
        queryset=WritingStatus.objects.filter(is_active=True).order_by('sort_order'),
        required=False,
        empty_label="Select status...",
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Current project status"
    )
    
    genre = forms.ModelChoiceField(
        queryset=Genre.objects.filter(is_active=True).order_by('sort_order', 'name'),
        required=False,
        empty_label="Select genre...",
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Primary genre of your book"
    )
    
    target_audience = forms.ModelChoiceField(
        queryset=TargetAudience.objects.filter(is_active=True).order_by('sort_order'),
        required=False,
        empty_label="Select audience...",
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Target audience for your book"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make workflow_template read-only with helpful message
        if "workflow_template" in self.fields:
            self.fields["workflow_template"].disabled = True
            self.fields["workflow_template"].required = False
            self.fields["workflow_template"].help_text = (
                "Automatically set based on Book Type. "
                "Change Book Type to select a different workflow."
            )

    class Meta:
        model = BookProjects
        fields = [
            "title",
            "book_type",
            "genre",
            "content_rating",
            "description",
            "tagline",
            "target_word_count",
            "current_word_count",
            "status",
            "deadline",
            "story_premise",
            "target_audience",
            "story_themes",
            "setting_time",
            "setting_location",
            "atmosphere_tone",
            "main_conflict",
            "stakes",
            "protagonist_concept",
            "antagonist_concept",
            "inspiration_sources",
            "unique_elements",
            "genre_settings",
            "workflow_template",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter book title"}
            ),
            # genre, content_rating, status, target_audience: defined as ModelChoiceFields above
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Brief description of your book",
                }
            ),
            "tagline": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Catchy one-liner for your book"}
            ),
            "target_word_count": forms.NumberInput(attrs={"class": "form-control", "min": 1000}),
            "current_word_count": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            # status: defined as ModelChoiceField above
            "deadline": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "story_premise": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            # target_audience: defined as ModelChoiceField above
            "story_themes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "setting_time": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "setting_location": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "atmosphere_tone": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "main_conflict": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "stakes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "protagonist_concept": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "antagonist_concept": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "inspiration_sources": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "unique_elements": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "genre_settings": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "book_type": forms.Select(
                attrs={
                    "class": "form-select",
                    "id": "id_book_type",
                }
            ),
            "workflow_template": forms.Select(
                attrs={
                    "class": "form-select",
                    "readonly": "readonly",
                    "disabled": "disabled",
                }
            ),
        }

    # Note: No api_key handling here; this belongs to LlmForm.

    def clean_target_word_count(self):
        target = self.cleaned_data.get("target_word_count")
        if target and target < 1000:
            raise ValidationError("Target word count must be at least 1,000 words.")
        return target

    def clean(self):
        cleaned_data = super().clean()
        current = cleaned_data.get("current_word_count", 0)
        target = cleaned_data.get("target_word_count", 0)

        if current and target and current > target:
            raise ValidationError("Current word count cannot exceed target word count.")

        return cleaned_data


class BookTypesForm(forms.ModelForm):
    """Form for creating and editing book types"""

    class Meta:
        model = BookTypes
        fields = [
            "name",
            "description",
            "complexity",
            "estimated_duration_hours",
            "target_word_count_min",
            "target_word_count_max",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g., Novel, Short Story, Poetry"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Description of this book type",
                }
            ),
            "complexity": forms.Select(
                attrs={"class": "form-select"},
                choices=[
                    ("beginner", "Beginner"),
                    ("intermediate", "Intermediate"),
                    ("advanced", "Advanced"),
                    ("expert", "Expert"),
                ],
            ),
            "estimated_duration_hours": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),
            "target_word_count_min": forms.NumberInput(attrs={"class": "form-control", "min": 100}),
            "target_word_count_max": forms.NumberInput(attrs={"class": "form-control", "min": 100}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class AgentsForm_Old(forms.ModelForm):
    """Form for creating and editing AI agents - DEPRECATED, use AgentsForm"""

    class Meta:
        model = Agents
        fields = [
            "name",
            "agent_type",
            "description",
            "status",
            "system_prompt",
            "instructions",
            "llm_model_id",
            "creativity_level",
            "consistency_weight",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Agent name"}),
            "agent_type": forms.Select(
                attrs={"class": "form-select"},
                choices=[
                    ("writer", "Writer"),
                    ("editor", "Editor"),
                    ("researcher", "Researcher"),
                    ("character_developer", "Character Developer"),
                    ("plot_analyzer", "Plot Analyzer"),
                    ("style_checker", "Style Checker"),
                ],
            ),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "status": forms.Select(
                attrs={"class": "form-select"},
                choices=[
                    ("active", "Active"),
                    ("inactive", "Inactive"),
                    ("testing", "Testing"),
                    ("maintenance", "Maintenance"),
                ],
            ),
            "system_prompt": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "System prompt for the agent",
                }
            ),
            "instructions": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Additional instructions"}
            ),
            "llm_model_id": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "creativity_level": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0", "max": "1"}
            ),
            "consistency_weight": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0", "max": "1"}
            ),
        }


class BookChaptersForm(forms.ModelForm):
    """Form for creating and editing book chapters"""

    class Meta:
        model = BookChapters
        fields = [
            "project",
            "title",
            "summary",
            "content",
            "chapter_number",
            "status",
            "word_count",
            "target_word_count",
            "notes",
            "outline",
        ]
        widgets = {
            "project": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Chapter title"}
            ),
            "summary": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Brief chapter summary"}
            ),
            "content": forms.Textarea(
                attrs={"class": "form-control", "rows": 10, "placeholder": "Chapter content"}
            ),
            "chapter_number": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "status": forms.Select(
                attrs={"class": "form-select"},
                choices=[
                    ("draft", "Draft"),
                    ("in_progress", "In Progress"),
                    ("review", "Under Review"),
                    ("completed", "Completed"),
                    ("published", "Published"),
                ],
            ),
            "word_count": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "target_word_count": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "outline": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = BookProjects.objects.all()


class CharactersForm(forms.ModelForm):
    """Form for creating and editing characters"""

    class Meta:
        model = Characters
        fields = [
            "project",
            "name",
            "description",
            "role",
            "age",
            "background",
            "personality",
            "appearance",
            "motivation",
            "conflict",
            "arc",
        ]
        widgets = {
            "project": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Character name"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Brief character description",
                }
            ),
            "role": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., Protagonist, Antagonist, Supporting",
                }
            ),
            "age": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "background": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "personality": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "appearance": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "motivation": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "conflict": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "arc": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = BookProjects.objects.all()


class LlmsForm_Old(forms.ModelForm):
    """Form for creating and editing LLM configurations - DEPRECATED, use LlmsForm"""

    class Meta:
        model = Llms
        fields = [
            "name",
            "provider",
            "llm_name",
            "api_key",
            "api_endpoint",
            "max_tokens",
            "temperature",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "cost_per_1k_tokens",
            "description",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Display name"}),
            "provider": forms.Select(
                attrs={"class": "form-select"},
                choices=[
                    ("openai", "OpenAI"),
                    ("anthropic", "Anthropic"),
                    ("google", "Google"),
                    ("cohere", "Cohere"),
                    ("huggingface", "Hugging Face"),
                    ("local", "Local Model"),
                ],
            ),
            "llm_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Model name (e.g., gpt-4)"}
            ),
            "api_key": forms.PasswordInput(
                attrs={"class": "form-control", "placeholder": "API Key"}
            ),
            "api_endpoint": forms.URLInput(
                attrs={"class": "form-control", "placeholder": "API Endpoint URL"}
            ),
            "max_tokens": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "temperature": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.1", "min": "0", "max": "2"}
            ),
            "top_p": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.1", "min": "0", "max": "1"}
            ),
            "frequency_penalty": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.1", "min": "-2", "max": "2"}
            ),
            "presence_penalty": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.1", "min": "-2", "max": "2"}
            ),
            "cost_per_1k_tokens": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.0001", "min": "0"}
            ),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-normalize incoming POST data so built-in FloatField validation accepts it
        if hasattr(self, "data") and self.data:
            try:
                qd = self.data.copy()
                # Replace comma decimals for float fields
                for field in ("temperature", "top_p", "frequency_penalty", "presence_penalty"):
                    val = qd.get(field)
                    if isinstance(val, str) and "," in val and "." not in val:
                        qd[field] = val.replace(",", ".")
                # Trim and normalize api_endpoint scheme
                ep = qd.get("api_endpoint")
                if isinstance(ep, str):
                    ep_norm = ep.strip()
                    if ep_norm and not (
                        ep_norm.startswith("http://") or ep_norm.startswith("https://")
                    ):
                        ep_norm = f"https://{ep_norm}"
                    qd["api_endpoint"] = ep_norm
                self.data = qd
            except Exception:
                # Non-fatal; proceed with original data
                pass
        # Make API key optional to allow env/settings-based keys
        self.fields["api_key"].required = False
        # Do not render existing secret; keep placeholder only
        self.fields["api_key"].widget.attrs.update(
            {
                "placeholder": "API Key (leave blank to use environment variable, e.g. OPENAI_API_KEY)"
            }
        )

    def clean_api_key(self):
        """If left blank on edit, keep stored value; allow blank on create for env fallback."""
        api_key = self.cleaned_data.get("api_key")
        if not api_key and getattr(self, "instance", None) and self.instance.pk:
            return self.instance.api_key
        return api_key

    def clean(self):
        cleaned = super().clean()
        # Normalize API endpoint: strip and ensure scheme
        api_endpoint = cleaned.get("api_endpoint")
        if isinstance(api_endpoint, str):
            norm = api_endpoint.strip()
            if norm and not (norm.startswith("http://") or norm.startswith("https://")):
                norm = f"https://{norm}"
            cleaned["api_endpoint"] = norm

        # Accept comma as decimal separator for numeric float fields
        for field in ("temperature", "top_p", "frequency_penalty", "presence_penalty"):
            val = self.data.get(field)
            if isinstance(val, str) and "," in val and "." not in val:
                try:
                    cleaned[field] = float(val.replace(",", "."))
                except ValueError:
                    pass  # let default validation surface the error
        # Sensible defaults if omitted
        if not cleaned.get("max_tokens"):
            cleaned["max_tokens"] = 512
        if cleaned.get("temperature") in (None, ""):
            cleaned["temperature"] = 0.7
        if cleaned.get("top_p") in (None, ""):
            cleaned["top_p"] = 1.0
        if cleaned.get("frequency_penalty") in (None, ""):
            cleaned["frequency_penalty"] = 0.0
        if cleaned.get("presence_penalty") in (None, ""):
            cleaned["presence_penalty"] = 0.0
        return cleaned


class AgentExecutionsForm(forms.ModelForm):
    """Form for creating and editing agent executions"""

    class Meta:
        model = AgentExecutions
        fields = ["project", "agent", "status", "field_name", "content_preview"]
        widgets = {
            "project": forms.Select(attrs={"class": "form-select"}),
            "agent": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(
                attrs={"class": "form-select"},
                choices=[
                    ("pending", "Pending"),
                    ("running", "Running"),
                    ("completed", "Completed"),
                    ("failed", "Failed"),
                    ("cancelled", "Cancelled"),
                ],
            ),
            "field_name": forms.TextInput(attrs={"class": "form-control"}),
            "content_preview": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = BookProjects.objects.all()
        self.fields["agent"].queryset = Agents.objects.filter(status="active")


class WorldsForm(forms.ModelForm):
    """Form for Worlds model"""

    class Meta:
        model = Worlds
        fields = [
            "name",
            "description",
            "world_type",
            "setting_details",
            "geography",
            "culture",
            "technology_level",
            "magic_system",
            "politics",
            "history",
            "inhabitants",
            "connections",
            "project",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "setting_details": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "geography": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "culture": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "magic_system": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "politics": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "history": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "inhabitants": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "connections": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                current_classes = field.widget.attrs.get("class", "")
                if (
                    "form-control" not in current_classes
                    and "form-check-input" not in current_classes
                ):
                    field.widget.attrs["class"] = f"{current_classes} form-control".strip()

    # CUSTOM_CODE_START: validation
    # Add your custom validation methods here
    # CUSTOM_CODE_END:

    # CUSTOM_CODE_START: save_override
    # Override save method if needed
    # CUSTOM_CODE_END:


class AgentsForm(forms.ModelForm):
    """Form for Agents model"""

    class Meta:
        model = Agents
        fields = [
            "name",
            "agent_type",
            "status",
            "description",
            "system_prompt",
            "instructions",
            "llm_model_id",
            "creativity_level",
            "consistency_weight",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "system_prompt": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "instructions": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "creativity_level": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "consistency_weight": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                current_classes = field.widget.attrs.get("class", "")
                if (
                    "form-control" not in current_classes
                    and "form-check-input" not in current_classes
                ):
                    field.widget.attrs["class"] = f"{current_classes} form-control".strip()

    # CUSTOM_CODE_START: validation
    # Add your custom validation methods here
    # CUSTOM_CODE_END:

    # CUSTOM_CODE_START: save_override
    # Override save method if needed
    # CUSTOM_CODE_END:


class LlmsForm(forms.ModelForm):
    """Form for Llms model"""

    class Meta:
        model = Llms
        fields = [
            "name",
            "provider",
            "llm_name",
            "api_key",
            "api_endpoint",
            "max_tokens",
            "temperature",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "cost_per_1k_tokens",
            "description",
            "is_active",
        ]
        widgets = {
            "api_key": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "api_endpoint": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "max_tokens": forms.NumberInput(attrs={"class": "form-control"}),
            "temperature": forms.NumberInput(attrs={"class": "form-control", "step": "any"}),
            "top_p": forms.NumberInput(attrs={"class": "form-control", "step": "any"}),
            "frequency_penalty": forms.NumberInput(attrs={"class": "form-control", "step": "any"}),
            "presence_penalty": forms.NumberInput(attrs={"class": "form-control", "step": "any"}),
            "cost_per_1k_tokens": forms.NumberInput(attrs={"class": "form-control", "step": "any"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                current_classes = field.widget.attrs.get("class", "")
                if (
                    "form-control" not in current_classes
                    and "form-check-input" not in current_classes
                ):
                    field.widget.attrs["class"] = f"{current_classes} form-control".strip()

    # CUSTOM_CODE_START: validation
    # Add your custom validation methods here
    # CUSTOM_CODE_END:

    # CUSTOM_CODE_START: save_override
    # Override save method if needed
    # CUSTOM_CODE_END:


class StoryArcForm(forms.ModelForm):
    """Form for Story Arc model"""

    class Meta:
        model = StoryArc
        fields = [
            "project",
            "name",
            "description",
            "arc_type",
            "start_chapter",
            "end_chapter",
            "central_conflict",
            "importance_level",
            "completion_status",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "central_conflict": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "arc_type": forms.Select(attrs={"class": "form-select"}),
            "importance_level": forms.Select(attrs={"class": "form-select"}),
            "completion_status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                current_classes = field.widget.attrs.get("class", "")
                if "form-control" not in current_classes and "form-select" not in current_classes:
                    field.widget.attrs["class"] = f"{current_classes} form-control".strip()


class PlotPointForm(forms.ModelForm):
    """Form for Plot Point model"""

    class Meta:
        model = PlotPoint
        fields = [
            "story_arc",
            "project",
            "name",
            "description",
            "point_type",
            "chapter_number",
            "sequence_order",
            "emotional_impact",
            "involved_characters",
            "completion_status",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "point_type": forms.Select(attrs={"class": "form-select"}),
            "emotional_impact": forms.Select(attrs={"class": "form-select"}),
            "completion_status": forms.Select(attrs={"class": "form-select"}),
            "sequence_order": forms.NumberInput(attrs={"class": "form-control"}),
            "chapter_number": forms.NumberInput(attrs={"class": "form-control"}),
            "involved_characters": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                current_classes = field.widget.attrs.get("class", "")
                if "form-control" not in current_classes and "form-select" not in current_classes:
                    field.widget.attrs["class"] = f"{current_classes} form-control".strip()


class AgentArtifactsForm(forms.ModelForm):
    """Form for Agent Artifacts model"""

    class Meta:
        model = AgentArtifacts
        fields = ["project", "agent", "action", "content_type", "content", "metadata", "version"]
        widgets = {
            "content_type": forms.Select(attrs={"class": "form-select"}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 10}),
            "metadata": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "action": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                current_classes = field.widget.attrs.get("class", "")
                if "form-control" not in current_classes and "form-select" not in current_classes:
                    field.widget.attrs["class"] = f"{current_classes} form-control".strip()


class GraphQLOperationForm(forms.ModelForm):
    """Form for GraphQL Operation model"""

    class Meta:
        model = GraphQLOperation
        fields = [
            "operation_name",
            "operation_type",
            "query_string",
            "complexity_score",
            "depth",
            "field_count",
            "htmx_request",
            "htmx_target",
        ]
        widgets = {
            "operation_type": forms.Select(attrs={"class": "form-select"}),
            "query_string": forms.Textarea(attrs={"class": "form-control", "rows": 6}),
            "complexity_score": forms.NumberInput(attrs={"class": "form-control"}),
            "depth": forms.NumberInput(attrs={"class": "form-control"}),
            "field_count": forms.NumberInput(attrs={"class": "form-control"}),
            "htmx_request": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "htmx_target": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                current_classes = field.widget.attrs.get("class", "")
                if (
                    "form-control" not in current_classes
                    and "form-check-input" not in current_classes
                    and "form-select" not in current_classes
                ):
                    field.widget.attrs["class"] = f"{current_classes} form-control".strip()


class FieldUsageForm(forms.ModelForm):
    """Form for Field Usage model"""

    class Meta:
        model = FieldUsage
        fields = [
            "type_name",
            "field_name",
            "model_name",
            "usage_count",
            "avg_resolve_time_ms",
            "error_count",
            "is_deprecated",
            "deprecation_reason",
            "suggested_alternative",
        ]
        widgets = {
            "deprecation_reason": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "is_deprecated": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "usage_count": forms.NumberInput(attrs={"class": "form-control"}),
            "avg_resolve_time_ms": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "error_count": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                current_classes = field.widget.attrs.get("class", "")
                if (
                    "form-control" not in current_classes
                    and "form-check-input" not in current_classes
                ):
                    field.widget.attrs["class"] = f"{current_classes} form-control".strip()


class QueryPerformanceLogForm(forms.ModelForm):
    """Form for Query Performance Log model"""

    class Meta:
        model = QueryPerformanceLog
        fields = [
            "operation",
            "duration_ms",
            "db_queries",
            "db_time_ms",
            "ip_address",
            "user_agent",
            "has_errors",
            "error_message",
        ]
        widgets = {
            "operation": forms.Select(attrs={"class": "form-select"}),
            "duration_ms": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "db_queries": forms.NumberInput(attrs={"class": "form-control"}),
            "db_time_ms": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "user_agent": forms.TextInput(attrs={"class": "form-control"}),
            "has_errors": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "error_message": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                current_classes = field.widget.attrs.get("class", "")
                if (
                    "form-control" not in current_classes
                    and "form-check-input" not in current_classes
                    and "form-select" not in current_classes
                ):
                    field.widget.attrs["class"] = f"{current_classes} form-control".strip()


class GenreForm(forms.ModelForm):
    """Form for Genre model"""

    class Meta:
        model = Genre
        fields = ["name", "description", "parent_genre", "is_active", "sort_order", "created_at"]
        widgets = {
            # Add custom widgets here
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                current_classes = field.widget.attrs.get("class", "")
                if (
                    "form-control" not in current_classes
                    and "form-check-input" not in current_classes
                ):
                    field.widget.attrs["class"] = f"{current_classes} form-control".strip()

    # CUSTOM_CODE_START: validation
    # Add your custom validation methods here
    # CUSTOM_CODE_END:

    # CUSTOM_CODE_START: save_override
    # Override save method if needed
    # CUSTOM_CODE_END:


class TargetAudienceForm(forms.ModelForm):
    """Form for TargetAudience model"""

    class Meta:
        model = TargetAudience
        fields = ["name", "age_range", "description", "is_active", "sort_order", "created_at"]
        widgets = {
            # Add custom widgets here
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                current_classes = field.widget.attrs.get("class", "")
                if (
                    "form-control" not in current_classes
                    and "form-check-input" not in current_classes
                ):
                    field.widget.attrs["class"] = f"{current_classes} form-control".strip()

    # CUSTOM_CODE_START: validation
    # Add your custom validation methods here
    # CUSTOM_CODE_END:

    # CUSTOM_CODE_START: save_override
    # Override save method if needed
    # CUSTOM_CODE_END:


class WritingStatusForm(forms.ModelForm):
    """Form for WritingStatus model"""

    class Meta:
        model = WritingStatus
        fields = ["name", "description", "color", "icon", "sort_order", "is_active", "created_at"]
        widgets = {
            # Add custom widgets here
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                current_classes = field.widget.attrs.get("class", "")
                if (
                    "form-control" not in current_classes
                    and "form-check-input" not in current_classes
                ):
                    field.widget.attrs["class"] = f"{current_classes} form-control".strip()

    # CUSTOM_CODE_START: validation
    # Add your custom validation methods here
    # CUSTOM_CODE_END:

    # CUSTOM_CODE_START: save_override
    # Override save method if needed
    # CUSTOM_CODE_END:


class WorkflowPhaseForm(forms.ModelForm):
    """Form for WorkflowPhase model"""

    class Meta:
        model = WorkflowPhase
        fields = ["name", "description", "icon", "color", "is_active", "created_at"]
        widgets = {
            # Add custom widgets here
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                current_classes = field.widget.attrs.get("class", "")
                if (
                    "form-control" not in current_classes
                    and "form-check-input" not in current_classes
                ):
                    field.widget.attrs["class"] = f"{current_classes} form-control".strip()

    # CUSTOM_CODE_START: validation
    # Add your custom validation methods here
    # CUSTOM_CODE_END:

    # CUSTOM_CODE_START: save_override
    # Override save method if needed
    # CUSTOM_CODE_END:


class WorkflowTemplateForm(forms.ModelForm):
    """Form for WorkflowTemplate model"""

    class Meta:
        model = WorkflowTemplate
        fields = ["name", "book_type", "description", "is_default", "is_active", "created_at"]
        widgets = {
            # Add custom widgets here
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                current_classes = field.widget.attrs.get("class", "")
                if (
                    "form-control" not in current_classes
                    and "form-check-input" not in current_classes
                ):
                    field.widget.attrs["class"] = f"{current_classes} form-control".strip()

    # CUSTOM_CODE_START: validation
    # Add your custom validation methods here
    # CUSTOM_CODE_END:

    # CUSTOM_CODE_START: save_override
    # Override save method if needed
    # CUSTOM_CODE_END:


class WorkflowPhaseStepForm(forms.ModelForm):
    """Form for WorkflowPhaseStep model"""

    class Meta:
        model = WorkflowPhaseStep
        fields = [
            "template",
            "phase",
            "order",
            "required_chapters",
            "required_characters",
            "can_skip",
            "can_return",
        ]
        widgets = {
            # Add custom widgets here
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                current_classes = field.widget.attrs.get("class", "")
                if (
                    "form-control" not in current_classes
                    and "form-check-input" not in current_classes
                ):
                    field.widget.attrs["class"] = f"{current_classes} form-control".strip()

    # CUSTOM_CODE_START: validation
    # Add your custom validation methods here
    # CUSTOM_CODE_END:


class AgentActionForm(forms.ModelForm):
    """Form for AgentAction model"""

    class Meta:
        model = AgentAction
        fields = [
            "agent",
            "name",
            "display_name",
            "description",
            "prompt_template",
            "order",
            "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                current_classes = field.widget.attrs.get("class", "")
                if (
                    "form-control" not in current_classes
                    and "form-check-input" not in current_classes
                ):
                    field.widget.attrs["class"] = current_classes + " form-control"


class PhaseActionConfigForm(forms.ModelForm):
    """Form for PhaseActionConfig model"""

    class Meta:
        model = PhaseActionConfig
        fields = ["phase", "action", "is_required", "order", "description"]
        widgets = {
            "is_required": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                current_classes = field.widget.attrs.get("class", "")
                # Skip checkbox fields - they already have form-check-input
                if field_name == "is_required":
                    continue
                if (
                    "form-control" not in current_classes
                    and "form-check-input" not in current_classes
                ):
                    field.widget.attrs["class"] = f"{current_classes} form-control".strip()

    # CUSTOM_CODE_START: validation
    # Add your custom validation methods here
    # CUSTOM_CODE_END:

    # CUSTOM_CODE_START: save_override
    # Override save method if needed
    # CUSTOM_CODE_END:


class ProjectPhaseHistoryForm(forms.ModelForm):
    """Form for ProjectPhaseHistory model"""

    class Meta:
        model = ProjectPhaseHistory
        fields = [
            "project",
            "workflow_step",
            "phase",
            "entered_at",
            "exited_at",
            "entered_by",
            "notes",
            "actions_completed",
            "requirements_met",
        ]
        widgets = {
            # Add custom widgets here
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                current_classes = field.widget.attrs.get("class", "")
                if (
                    "form-control" not in current_classes
                    and "form-check-input" not in current_classes
                ):
                    field.widget.attrs["class"] = f"{current_classes} form-control".strip()

    # CUSTOM_CODE_START: validation
    # Add your custom validation methods here
    # CUSTOM_CODE_END:

    # CUSTOM_CODE_START: save_override
    # Override save method if needed
    # CUSTOM_CODE_END:


class ActionTemplateForm(forms.ModelForm):
    """Form for ActionTemplate model"""

    class Meta:
        model = ActionTemplate
        fields = ["action", "template", "is_default", "order", "description_override"]
        widgets = {
            "action": forms.Select(attrs={"class": "form-select"}),
            "template": forms.Select(attrs={"class": "form-select"}),
            "is_default": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "value": 0}),
            "description_override": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class PromptTemplateForm(forms.ModelForm):
    """Form for Prompt Management System V2.0 PromptTemplate model"""

    class Meta:
        model = PromptTemplate
        fields = [
            "name",
            "template_key",
            "category",
            "parent_template",
            "system_prompt",
            "user_prompt_template",
            "required_variables",
            "optional_variables",
            "variable_defaults",
            "output_format",
            "output_schema",
            "max_tokens",
            "temperature",
            "top_p",
            "version",
            "is_active",
            "is_default",
            "ab_test_group",
            "ab_test_weight",
            "fallback_template",
            "language",
            "description",
            "tags",
        ]
        widgets = {
            "description": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": "form-control",
                    "placeholder": "Template description...",
                }
            ),
            "system_prompt": forms.Textarea(
                attrs={
                    "rows": 6,
                    "class": "form-control font-monospace",
                    "placeholder": "You are an expert...",
                }
            ),
            "user_prompt_template": forms.Textarea(
                attrs={
                    "rows": 12,
                    "class": "form-control font-monospace",
                    "placeholder": "Create {target.name} for {project.genre}...",
                }
            ),
            "output_schema": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": "form-control font-monospace",
                    "placeholder": "JSON Schema (optional)...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                current_classes = field.widget.attrs.get("class", "")
                if (
                    "form-control" not in current_classes
                    and "form-check-input" not in current_classes
                    and "form-select" not in current_classes
                ):
                    field.widget.attrs["class"] = f"{current_classes} form-control".strip()

    # CUSTOM_CODE_START: validation
    # Add your custom validation methods here
    # CUSTOM_CODE_END:

    # CUSTOM_CODE_START: save_override
    # Override save method if needed
    # CUSTOM_CODE_END:


class BookTypePhaseForm(forms.ModelForm):
    """Form for configuring workflow phases for book types"""

    class Meta:
        model = BookTypePhase
        fields = [
            "book_type",
            "phase",
            "order",
            "is_required",
            "estimated_days",
            "description_override",
        ]
        widgets = {
            "book_type": forms.Select(attrs={"class": "form-select"}),
            "phase": forms.Select(attrs={"class": "form-select"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "is_required": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "estimated_days": forms.NumberInput(
                attrs={"class": "form-control", "min": "1", "placeholder": "Estimated days"}
            ),
            "description_override": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Optional: Override phase description for this book type",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate book type choices
        self.fields["book_type"].queryset = BookTypes.objects.filter(is_active=True).order_by(
            "name"
        )

        # Populate phase choices
        self.fields["phase"].queryset = WorkflowPhase.objects.filter(is_active=True).order_by(
            "name"
        )

        # Add help text
        self.fields["order"].help_text = "Order of this phase in the workflow"
        self.fields["is_required"].help_text = "Is this phase mandatory for this book type?"
        self.fields["estimated_days"].help_text = "Estimated days to complete this phase"

    def clean(self):
        cleaned_data = super().clean()
        book_type = cleaned_data.get("book_type")
        phase = cleaned_data.get("phase")

        # Check for duplicate assignment (only for new instances)
        if book_type and phase and not self.instance.pk:
            if BookTypePhase.objects.filter(book_type=book_type, phase=phase).exists():
                raise ValidationError(
                    f"Phase '{phase.name}' is already assigned to book type '{book_type.name}'"
                )

        return cleaned_data
