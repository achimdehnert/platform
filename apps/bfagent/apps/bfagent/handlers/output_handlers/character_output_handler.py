"""
Character Output Handler
Persists Characters data to database
"""

import logging
from typing import Any, Dict, List

from django.db import transaction

from apps.bfagent.handlers.base import BaseOutputHandler, OutputError
from apps.bfagent.models import Characters

logger = logging.getLogger(__name__)


class CharacterOutputHandler(BaseOutputHandler):
    """Handler for Characters persistence"""

    def __init__(self):
        super().__init__(name="character_output", version="1.0.0")

    def save(self, data: Dict[str, Any]) -> Characters:
        """
        Save or update Characters

        Args:
            data: Cleaned character data from InputHandler

        Returns:
            Characters instance
        """
        character_id = data.get('id')

        try:
            if character_id:
                # Update existing character
                character = self._update_character(character_id, data)
            else:
                # Create new character
                character = self._create_character(data)

            logger.info(f"Character saved successfully: {character.id}")
            return character

        except Exception as e:
            logger.error(f"Failed to save character: {e}")
            raise OutputError(f"Failed to save character: {e}")

    def _create_character(self, data: Dict[str, Any]) -> Characters:
        """Create new character"""
        with transaction.atomic():
            # Remove 'id' if present
            data.pop('id', None)

            character = Characters.objects.create(**data)
            logger.info(
                f"Created new character: {character.id} - {character.name}"
            )
            return character

    def _update_character(
        self, character_id: int, data: Dict[str, Any]
    ) -> Characters:
        """Update existing character"""
        try:
            character = Characters.objects.get(pk=character_id)
        except Characters.DoesNotExist:
            raise OutputError(f"Character {character_id} not found")

        with transaction.atomic():
            # Update fields
            for field, value in data.items():
                if field != 'id' and hasattr(character, field):
                    setattr(character, field, value)

            character.save()
            logger.info(
                f"Updated character: {character.id} - {character.name}"
            )
            return character

    def bulk_create(self, characters_data: List[Dict[str, Any]]) -> List[Characters]:
        """
        Create multiple characters at once

        Args:
            characters_data: List of cleaned character dicts

        Returns:
            List of created Characters instances
        """
        if not characters_data:
            logger.warning("No characters to create")
            return []

        try:
            with transaction.atomic():
                characters = []
                for data in characters_data:
                    # Remove 'id' if present
                    data.pop('id', None)
                    character = Characters.objects.create(**data)
                    characters.append(character)

                logger.info(f"Bulk created {len(characters)} characters")
                return characters

        except Exception as e:
            logger.error(f"Failed to bulk create characters: {e}")
            raise OutputError(f"Failed to bulk create characters: {e}")

    def save_ai_generation(
        self, character_id: int, generated_data: Dict[str, str]
    ) -> Characters:
        """
        Save AI-generated character enhancements

        Args:
            character_id: Characters ID
            generated_data: Dict of field_name: generated_value

        Returns:
            Updated Characters instance
        """
        try:
            character = Characters.objects.get(pk=character_id)
        except Characters.DoesNotExist:
            raise OutputError(f"Character {character_id} not found")

        with transaction.atomic():
            for field, value in generated_data.items():
                if hasattr(character, field):
                    setattr(character, field, value)
                else:
                    logger.warning(
                        f"Skipping unknown field for character {character_id}: {field}"
                    )

            character.save()
            logger.info(
                f"Saved AI generation to character {character.id}: "
                f"{list(generated_data.keys())}"
            )
            return character
