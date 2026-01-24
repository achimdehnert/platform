"""
Project Input Handler
Validates and prepares BookProjects data
"""

import logging
from typing import Any, Dict

from apps.bfagent.handlers.base import BaseInputHandler, ValidationError
from apps.bfagent.models import BookProjects

logger = logging.getLogger(__name__)


class ProjectInputHandler(BaseInputHandler):
    """Handler for BookProjects input validation and preparation"""

    def __init__(self):
        super().__init__(name="project_input", version="1.0.0")

    def validate(self, data: Dict[str, Any]) -> bool:
        """
        Validate project data

        Required fields:
        - title: str (not empty)
        - genre: str (not empty)
        - target_word_count: int (> 0)
        - status: str (valid status)
        """
        errors = []

        # Title validation
        title = data.get('title', '').strip()
        if not title:
            errors.append("Title is required")
        elif len(title) > 200:
            errors.append("Title must be 200 characters or less")

        # Genre validation
        genre = data.get('genre', '').strip()
        if not genre:
            errors.append("Genre is required")
        elif len(genre) > 100:
            errors.append("Genre must be 100 characters or less")

        # Target word count validation
        target_word_count = data.get('target_word_count')
        if target_word_count is None:
            errors.append("Target word count is required")
        else:
            try:
                target_word_count = int(target_word_count)
                if target_word_count <= 0:
                    errors.append("Target word count must be positive")
            except (ValueError, TypeError):
                errors.append("Target word count must be a number")

        # Status validation
        status = data.get('status', '').strip()
        valid_statuses = ['planning', 'drafting', 'editing', 'completed']
        if status and status not in valid_statuses:
            errors.append(f"Status must be one of: {', '.join(valid_statuses)}")

        if errors:
            error_msg = "; ".join(errors)
            logger.warning(f"Project validation failed: {error_msg}")
            raise ValidationError(error_msg)

        logger.info("Project data validated successfully")
        return True

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and clean project data

        Returns cleaned data ready for model creation/update
        """
        # First validate
        self.validate(data)

        # Clean and normalize data
        cleaned_data = {
            'title': data.get('title', '').strip(),
            'genre': data.get('genre', '').strip(),
            'content_rating': data.get('content_rating', '').strip(),
            'target_word_count': int(data.get('target_word_count', 0)),
            'status': data.get('status', 'planning').strip(),
        }

        # Optional fields
        optional_fields = [
            'description',
            'tagline',
            'story_premise',
            'target_audience',
            'story_themes',
            'setting_time',
            'setting_location',
            'atmosphere_tone',
            'main_conflict',
            'stakes',
            'protagonist_concept',
            'antagonist_concept',
            'inspiration_sources',
            'unique_elements',
            'genre_settings',
        ]

        for field in optional_fields:
            if field in data and data[field]:
                cleaned_data[field] = str(data[field]).strip()

        # Deadline handling
        if 'deadline' in data and data['deadline']:
            cleaned_data['deadline'] = data['deadline']

        logger.info(f"Project data processed: {cleaned_data.get('title')}")
        return cleaned_data

    def prepare_enrichment_context(
        self, project_id: int, agent_id: int, action: str, parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Prepare context for enrichment operations

        Args:
            project_id: BookProjects ID
            agent_id: Agent ID
            action: Enrichment action name
            parameters: Optional action-specific parameters

        Returns:
            Context dict ready for ProcessingHandler
        """
        try:
            project = BookProjects.objects.get(pk=project_id)
        except BookProjects.DoesNotExist:
            raise ValidationError(f"Project {project_id} not found")

        context = {
            'project_id': project_id,
            'project': project,
            'agent_id': agent_id,
            'action': action,
            'parameters': parameters or {},
            # Add project context for AI
            'project_context': {
                'title': project.title,
                'genre': project.genre,
                'description': project.description,
                'story_premise': project.story_premise,
                'target_audience': project.target_audience,
                'story_themes': project.story_themes,
                'setting': {
                    'time': project.setting_time,
                    'location': project.setting_location,
                },
                'atmosphere_tone': project.atmosphere_tone,
            },
        }

        logger.info(
            f"Enrichment context prepared: project={project_id}, action={action}"
        )
        return context
