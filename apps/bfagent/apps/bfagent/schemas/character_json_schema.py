#!/usr/bin/env python
"""
JSON Schema for OpenAI Structured Outputs - Character Cast
"""

CHARACTER_CAST_JSON_SCHEMA = {
    "name": "character_cast",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "characters": {
                "type": "array",
                "description": "List of characters for the story",
                "minItems": 9,
                "maxItems": 9,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Character's full name (first and last name)",
                        },
                        "role": {
                            "type": "string",
                            "description": "Character role in story",
                            "enum": [
                                "Protagonist",
                                "Antagonist",
                                "Supporting Character",
                                "Minor Character",
                            ],
                        },
                        "age": {
                            "type": "integer",
                            "description": "Character's age in years",
                            "minimum": 1,
                            "maximum": 120,
                        },
                        "description": {
                            "type": "string",
                            "description": "Brief character description and personality",
                        },
                        "background": {
                            "type": "string",
                            "description": "Character's background and history",
                        },
                        "motivation": {
                            "type": "string",
                            "description": "What drives this character",
                        },
                        "personality": {
                            "type": "string",
                            "description": "Key personality traits (comma-separated)",
                        },
                        "arc": {
                            "type": "string",
                            "description": "Character development arc throughout the story",
                        },
                    },
                    "required": [
                        "name",
                        "role",
                        "age",
                        "description",
                        "background",
                        "motivation",
                        "personality",
                        "arc",
                    ],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["characters"],
        "additionalProperties": False,
    },
}
