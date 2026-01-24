"""
Character Input Handler
Validates and prepares Characters data
"""

import logging
from typing import Any, Dict

from apps.bfagent.handlers.base import BaseInputHandler, ValidationError
from apps.bfagent.models import BookProjects, Characters

logger = logging.getLogger(__name__)


class CharacterInputHandler(BaseInputHandler):
    """Handler for Characters input validation and preparation"""

    def __init__(self):
        super().__init__(name="character_input", version="1.0.0")

    def validate(self, data: Dict[str, Any]) -> bool:
        """
        Validate character data

        Required fields:
        - name: str (not empty)
        - project_id: int (valid project)
        """
        errors = []

        # Name validation
        name = data.get('name', '').strip()
        if not name:
            errors.append("Character name is required")
        elif len(name) > 200:
            errors.append("Character name must be 200 characters or less")

        # Project validation
        project_id = data.get('project_id')
        if not project_id:
            errors.append("Project ID is required")
        else:
            try:
                project_id = int(project_id)
                if not BookProjects.objects.filter(pk=project_id).exists():
                    errors.append(f"Project {project_id} does not exist")
            except (ValueError, TypeError):
                errors.append("Project ID must be a number")

        if errors:
            error_msg = "; ".join(errors)
            logger.warning(f"Character validation failed: {error_msg}")
            raise ValidationError(error_msg)

        logger.info("Character data validated successfully")
        return True

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and clean character data

        Returns cleaned data ready for model creation/update
        """
        # First validate
        self.validate(data)

        # Clean and normalize data
        cleaned_data = {
            'name': data.get('name', '').strip(),
            'project_id': int(data.get('project_id')),
        }

        # Optional fields
        optional_fields = [
            'role',
            'description',
            'personality',
            'background',
            'motivation',
            'goals',
            'fears',
            'strengths',
            'weaknesses',
            'relationships',
            'arc',
            'archetype',
            'physical_description',
            'dialogue_voice',
        ]

        for field in optional_fields:
            if field in data and data[field]:
                cleaned_data[field] = str(data[field]).strip()

        logger.info(f"Character data processed: {cleaned_data.get('name')}")
        return cleaned_data

    def prepare_bulk_creation(
        self, characters_data: list[Dict[str, Any]], project_id: int
    ) -> list[Dict[str, Any]]:
        """
        Prepare multiple characters for bulk creation

        Args:
            characters_data: List of character dicts
            project_id: BookProjects ID

        Returns:
            List of cleaned character dicts
        """
        # Validate project exists
        try:
            project = BookProjects.objects.get(pk=project_id)
        except BookProjects.DoesNotExist:
            raise ValidationError(f"Project {project_id} not found")

        cleaned_characters = []
        for idx, char_data in enumerate(characters_data):
            # Add project_id to each character
            char_data['project_id'] = project_id

            try:
                # Process each character
                cleaned = self.process(char_data)
                cleaned_characters.append(cleaned)
            except ValidationError as e:
                logger.warning(f"Character {idx} validation failed: {e}")
                # Continue with other characters
                continue

        logger.info(
            f"Prepared {len(cleaned_characters)} characters for project {project_id}"
        )
        return cleaned_characters
