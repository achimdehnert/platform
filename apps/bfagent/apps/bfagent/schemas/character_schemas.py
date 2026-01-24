#!/usr/bin/env python
"""
Pydantic schemas for structured character generation
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class CharacterSchema(BaseModel):
    """Single character with all details"""

    name: str = Field(..., description="Character's full name")
    character_type: str = Field(
        default="supporting",
        description="Character type: protagonist, antagonist, supporting, love_interest",
    )
    age_range: Optional[str] = Field(
        None, description="Age range (e.g., 'mid-30s', '20-25', 'elderly')"
    )
    profile: str = Field(..., description="Brief character profile/description")
    motivation: str = Field(..., description="Character's primary motivation")
    traits: List[str] = Field(
        default_factory=list, description="List of character traits (3-5 traits)"
    )
    character_arc: Optional[str] = Field(
        None, description="Character arc / development throughout story"
    )
    background: Optional[str] = Field(None, description="Character's background/backstory")
    relationships: Optional[str] = Field(
        None, description="Key relationships with other characters"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Peter Weiss",
                "character_type": "protagonist",
                "age_range": "mid-30s",
                "profile": "A conflicted former detective haunted by his past",
                "motivation": "Seeking redemption and protecting those he loves",
                "traits": ["brooding", "passionate", "resourceful", "conflicted"],
                "character_arc": "From protector to potential monster, struggling with inner demons",
                "background": "Former police detective with a dark secret",
                "relationships": "Complex romantic tension with Hilde, antagonistic toward Bruno",
            }
        }


class CharacterCastSchema(BaseModel):
    """Complete character cast for a story"""

    characters: List[CharacterSchema] = Field(
        ..., min_items=3, max_items=8, description="List of main characters (3-8 characters)"
    )
    cast_overview: Optional[str] = Field(
        None, description="Brief overview of character dynamics and relationships"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "characters": [
                    {
                        "name": "Peter Weiss",
                        "character_type": "protagonist",
                        "profile": "A conflicted man...",
                        "motivation": "Seeking redemption...",
                        "traits": ["brooding", "passionate"],
                    }
                ],
                "cast_overview": "A tense love triangle with dark psychological undertones",
            }
        }


def character_schema_to_dict(character: CharacterSchema) -> dict:
    """Convert CharacterSchema to Django model format"""
    # Map character_type to role
    role_map = {
        "protagonist": "Protagonist",
        "antagonist": "Antagonist",
        "supporting": "Supporting Character",
        "supporting_characters": "Supporting Character",
        "minor": "Minor Character",
        "minor_characters": "Minor Character",
        "love_interest": "Love Interest",
    }

    return {
        "name": character.name,
        "role": role_map.get(character.character_type, "Supporting Character"),
        "description": character.profile,
        "background": character.background or "",
        "motivation": character.motivation,
        "personality": ", ".join(character.traits),
        "arc": character.character_arc or "",
        # Note: Characters model doesn't have 'backstory' or 'character_type'
        # Using correct field names: role, background, motivation, personality, arc
    }
