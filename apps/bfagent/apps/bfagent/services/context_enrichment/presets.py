"""
Default Context Enrichment Schemas

Pre-defined schemas that are loaded automatically via management command.
These schemas are marked as is_system=True and cannot be deleted via UI.
"""

# Schema: chapter_generation
CHAPTER_GENERATION_SCHEMA = {
    "name": "chapter_generation",
    "display_name": "Chapter Generation Context",
    "description": "Context for AI-powered chapter outline generation",
    "handler_type": "ChapterGenerateHandler",
    "is_system": True,
    "version": "1.0.0",
    "sources": [
        {
            "name": "Project Base Information",
            "order": 1,
            "source_type": "model",
            "model_name": "BookProjects",
            "filter_config": {"pk": "{project_id}"},
            "fields": ["title", "genre", "story_premise", "story_themes", "target_audience"],
            "field_mappings": {
                "story_premise": "premise",
                "story_themes": "themes",
            },
            "is_required": True,
            "is_active": True,
        },
        {
            "name": "Protagonist Character",
            "order": 2,
            "source_type": "related_query",
            "model_name": "Characters",
            "filter_config": {
                "project_id": "{project_id}",
                "role": "protagonist"
            },
            "fields": ["name", "description", "personality_traits"],
            "field_mappings": {
                "name": "protagonist_name",
                "description": "protagonist_description",
                "personality_traits": "protagonist_traits",
            },
            "aggregate_type": "first",
            "is_required": True,
            "is_active": True,
        },
        {
            "name": "Antagonist Character",
            "order": 3,
            "source_type": "related_query",
            "model_name": "Characters",
            "filter_config": {
                "project_id": "{project_id}",
                "role": "antagonist"
            },
            "fields": ["name", "description"],
            "field_mappings": {
                "name": "antagonist_name",
                "description": "antagonist_description",
            },
            "aggregate_type": "first",
            "is_required": False,
            "fallback_value": {},
            "is_active": True,
        },
        {
            "name": "Previous Chapters",
            "order": 4,
            "source_type": "related_query",
            "model_name": "BookChapters",
            "filter_config": {
                "project_id": "{project_id}",
                "chapter_number__lt": "{chapter_number}"
            },
            "fields": ["chapter_number", "title", "summary"],
            "aggregate_type": "list",
            "order_by": "chapter_number",
            "context_key": "previous_chapters",
            "is_required": False,
            "fallback_value": [],
            "is_active": True,
        },
        {
            "name": "Story Position",
            "order": 5,
            "source_type": "computed",
            "function_name": "calculate_story_position",
            "function_params": {
                "chapter_number": "{chapter_number}",
                "total_chapters": 15
            },
            "context_key": "story_position",
            "is_required": False,
            "is_active": True,
        },
        {
            "name": "Current Beat",
            "order": 6,
            "source_type": "beat_sheet",
            "function_name": "get_beat_info",
            "function_params": {
                "beat_type": "save_the_cat",
                "chapter_number": "{chapter_number}"
            },
            "context_key": "current_beat",
            "is_required": False,
            "fallback_value": {},
            "is_active": True,
        },
    ]
}

# Schema: character_enrichment
CHARACTER_ENRICHMENT_SCHEMA = {
    "name": "character_enrichment",
    "display_name": "Character Enrichment Context",
    "description": "Context for character development and enrichment",
    "handler_type": "CharacterEnrichHandler",
    "is_system": True,
    "version": "1.0.0",
    "sources": [
        {
            "name": "Character Base",
            "order": 1,
            "source_type": "model",
            "model_name": "Characters",
            "filter_config": {"pk": "{character_id}"},
            "fields": [
                "name", "description", "role", "personality_traits",
                "backstory", "goals", "fears"
            ],
            "is_required": True,
            "is_active": True,
        },
        {
            "name": "Project Context",
            "order": 2,
            "source_type": "model",
            "model_name": "BookProjects",
            "filter_config": {"pk": "{project_id}"},
            "fields": ["title", "genre", "story_premise", "setting_time", "setting_location"],
            "field_mappings": {
                "story_premise": "project_premise",
            },
            "is_required": True,
            "is_active": True,
        },
        {
            "name": "Related Characters",
            "order": 3,
            "source_type": "related_query",
            "model_name": "Characters",
            "filter_config": {
                "project_id": "{project_id}",
            },
            "fields": ["name", "role", "description"],
            "aggregate_type": "list",
            "context_key": "other_characters",
            "is_required": False,
            "fallback_value": [],
            "is_active": True,
        },
    ]
}

# Schema: world_building
WORLD_BUILDING_SCHEMA = {
    "name": "world_building",
    "display_name": "World Building Context",
    "description": "Context for world building and setting enrichment",
    "handler_type": "WorldBuildingHandler",
    "is_system": True,
    "version": "1.0.0",
    "sources": [
        {
            "name": "Project Settings",
            "order": 1,
            "source_type": "model",
            "model_name": "BookProjects",
            "filter_config": {"pk": "{project_id}"},
            "fields": [
                "title", "genre", "setting_time", "setting_location",
                "atmosphere_tone", "unique_elements"
            ],
            "is_required": True,
            "is_active": True,
        },
        {
            "name": "Story Context",
            "order": 2,
            "source_type": "model",
            "model_name": "BookProjects",
            "filter_config": {"pk": "{project_id}"},
            "fields": ["story_premise", "main_conflict", "stakes"],
            "field_mappings": {
                "story_premise": "premise",
                "main_conflict": "conflict",
            },
            "is_required": False,
            "is_active": True,
        },
        {
            "name": "Main Characters",
            "order": 3,
            "source_type": "related_query",
            "model_name": "Characters",
            "filter_config": {
                "project_id": "{project_id}",
                "role__in": ["protagonist", "antagonist"]
            },
            "fields": ["name", "role", "description"],
            "aggregate_type": "list",
            "context_key": "main_characters",
            "is_required": False,
            "fallback_value": [],
            "is_active": True,
        },
    ]
}

# Schema: dialogue_generation
DIALOGUE_GENERATION_SCHEMA = {
    "name": "dialogue_generation",
    "display_name": "Dialogue Generation Context",
    "description": "Context for character dialogue and conversation generation",
    "handler_type": "DialogueGenerationHandler",
    "is_system": True,
    "version": "1.0.0",
    "sources": [
        {
            "name": "Speaking Character",
            "order": 1,
            "source_type": "model",
            "model_name": "Characters",
            "filter_config": {"pk": "{character_id}"},
            "fields": [
                "name", "personality_traits", "backstory",
                "speech_patterns", "education_level", "age"
            ],
            "field_mappings": {
                "name": "speaker_name",
                "personality_traits": "speaker_personality",
            },
            "is_required": True,
            "is_active": True,
        },
        {
            "name": "Conversation Partner",
            "order": 2,
            "source_type": "model",
            "model_name": "Characters",
            "filter_config": {"pk": "{partner_id}"},
            "fields": ["name", "personality_traits", "relationship_to_speaker"],
            "field_mappings": {
                "name": "partner_name",
                "personality_traits": "partner_personality",
            },
            "is_required": False,
            "is_active": True,
        },
        {
            "name": "Scene Context",
            "order": 3,
            "source_type": "model",
            "model_name": "BookChapters",
            "filter_config": {
                "project_id": "{project_id}",
                "chapter_number": "{chapter_number}"
            },
            "fields": ["title", "summary", "mood", "setting"],
            "field_mappings": {
                "summary": "scene_summary",
            },
            "is_required": False,
            "is_active": True,
        },
        {
            "name": "Project Tone",
            "order": 4,
            "source_type": "model",
            "model_name": "BookProjects",
            "filter_config": {"pk": "{project_id}"},
            "fields": ["genre", "atmosphere_tone", "target_audience"],
            "is_required": False,
            "is_active": True,
        },
    ]
}

# All default schemas
DEFAULT_SCHEMAS = [
    CHAPTER_GENERATION_SCHEMA,
    CHARACTER_ENRICHMENT_SCHEMA,
    WORLD_BUILDING_SCHEMA,
    DIALOGUE_GENERATION_SCHEMA,
]
