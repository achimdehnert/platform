"""
Character Cast Parser for BF Agent
Parses LLM-generated character descriptions into structured data
"""

import re
from typing import Any, Dict, List


def parse_character_cast(content: str, project) -> List[Dict[str, Any]]:
    """Parse LLM-generated character cast content into structured data"""
    characters = []

    # Split content into sections by character numbers (### or #### with numbers)
    # Matches: ### Protagonist, #### Protagonist, #### 1. Peter, etc.
    character_sections = re.split(r"#{3,4}\s*(?:\d+\.\s*)?([A-Za-z\s]+)", content)

    # Process each character section
    for i in range(1, len(character_sections), 2):  # Skip first empty section, then take pairs
        if i + 1 < len(character_sections):
            name = character_sections[i].strip()
            char_content = character_sections[i + 1].strip()

            # Extract character details
            char_data = {"name": name, "description": "", "character_type": "main", "backstory": ""}

            # Parse role, background, motivation, etc.
            lines = char_content.split("\n")
            current_field = None

            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Check for field markers
                if "**Role**:" in line:
                    role = line.split("**Role**:")[1].strip()
                    char_data["character_type"] = role.lower()
                elif "**Background**:" in line:
                    background = line.split("**Background**:")[1].strip()
                    char_data["backstory"] = background
                elif "**Motivation**:" in line:
                    motivation = line.split("**Motivation**:")[1].strip()
                    if char_data["description"]:
                        char_data["description"] += f" Motivation: {motivation}"
                    else:
                        char_data["description"] = f"Motivation: {motivation}"
                elif "**Character Arc**:" in line:
                    arc = line.split("**Character Arc**:")[1].strip()
                    if char_data["description"]:
                        char_data["description"] += f" Character Arc: {arc}"
                    else:
                        char_data["description"] = f"Character Arc: {arc}"
                elif line.startswith("- **") and ":" in line:
                    # Generic field parsing
                    field_content = line.split(":", 1)[1].strip()
                    if char_data["description"]:
                        char_data["description"] += f" {field_content}"
                    else:
                        char_data["description"] = field_content

            # Clean up character type
            if char_data["character_type"] in ["protagonist", "main character"]:
                char_data["character_type"] = "protagonist"
            elif char_data["character_type"] in ["antagonist", "villain"]:
                char_data["character_type"] = "antagonist"
            elif "love interest" in char_data["character_type"].lower():
                char_data["character_type"] = "love_interest"
            elif "friend" in char_data["character_type"].lower():
                char_data["character_type"] = "supporting"

            characters.append(char_data)

    # Fallback: create default characters if parsing failed
    if not characters:
        characters = [
            {
                "name": "Protagonist",
                "description": "Main character",
                "character_type": "protagonist",
                "backstory": "",
            },
            {
                "name": "Antagonist",
                "description": "Primary opposition",
                "character_type": "antagonist",
                "backstory": "",
            },
            {
                "name": "Supporting Character",
                "description": "Key supporting role",
                "character_type": "supporting",
                "backstory": "",
            },
        ]

    return characters[:8]  # Limit to 8 characters max
