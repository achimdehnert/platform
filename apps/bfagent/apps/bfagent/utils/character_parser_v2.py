#!/usr/bin/env python
"""
Character Cast Parser V2 - Structured Output Edition
Uses Pydantic schemas for reliable parsing
"""

import json
import re
from typing import Any, Dict, List

from ..schemas.character_schemas import CharacterCastSchema, character_schema_to_dict


def parse_character_cast_structured(content: str, project) -> List[Dict[str, Any]]:
    """
    Parse character cast using structured JSON output from OpenAI

    Args:
        content: LLM-generated JSON content (guaranteed valid by structured output)
        project: Django project instance

    Returns:
        List of character dictionaries ready for Django model creation
    """
    characters = []

    # Try to parse as JSON first (structured output should guarantee this works)
    try:
        # Clean content - remove markdown code blocks if present (just in case)
        cleaned = content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned.replace("```json", "").replace("```", "").strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned.replace("```", "").strip()

        # Parse JSON - should be guaranteed valid by OpenAI structured output
        data = json.loads(cleaned)

        print(f"   ✅ JSON parsed successfully")
        print(f"   📋 Found {len(data.get('characters', []))} characters in JSON")

        # Validate with Pydantic (optional but good for safety)
        try:
            cast = CharacterCastSchema(**data)
            print(f"   ✅ Pydantic validation passed")

            # Convert to Django format
            for character in cast.characters:
                char_dict = character_schema_to_dict(character)
                characters.append(char_dict)

            print(f"   ✅ Converted {len(characters)} characters to Django format")
            return characters

        except Exception as pydantic_error:
            print(f"   ⚠️  Pydantic validation failed: {pydantic_error}")
            print(f"   🔄 Using direct JSON mapping...")

            # Direct mapping without Pydantic validation
            for char in data.get("characters", []):
                char_dict = {
                    "name": char.get("name", "Unknown"),
                    "role": char.get("role", "Supporting Character"),
                    "description": char.get("description", ""),
                    "background": char.get("background", ""),
                    "motivation": char.get("motivation", ""),
                    "personality": char.get("personality", ""),
                    "arc": char.get("arc", ""),
                    "age": char.get("age"),
                }
                characters.append(char_dict)

            print(f"   ✅ Mapped {len(characters)} characters directly")
            return characters

    except json.JSONDecodeError as e:
        print(f"   ⚠️  JSON parsing failed: {e}")
        print(f"   📄 Content preview: {content[:200]}...")
        print("   🔄 Falling back to text parsing...")

    except Exception as e:
        print(f"   ⚠️  Structured parsing failed: {e}")
        print("   🔄 Falling back to text parsing...")

    # Fallback: Try to parse as markdown/text (shouldn't happen with structured output)
    print("   ⚠️  WARNING: Structured output failed, using regex fallback!")
    return parse_character_cast_fallback(content, project)


def parse_character_cast_fallback(content: str, project) -> List[Dict[str, Any]]:
    """
    Fallback parser for non-structured output
    Handles markdown and plain text formats
    """
    characters = []

    # Pattern 1: ### Protagonist or #### Protagonist (with optional colon)
    pattern1 = r"#{3,4}\s*(?:Protagonist|Antagonist|Supporting\s*Characters?|Minor\s*Characters?|Love\s*Interest):?"
    matches1 = list(re.finditer(pattern1, content, re.IGNORECASE))

    if matches1:
        print(f"   🔍 Found {len(matches1)} character sections (pattern 1)")
        for i, match in enumerate(matches1):
            start = match.end()
            end = matches1[i + 1].start() if i + 1 < len(matches1) else len(content)

            char_section = content[start:end].strip()
            char_type = match.group(0).strip("# :").lower().replace(" ", "_")

            # Extract all characters from this section (may have multiple in bullet list)
            # Pattern supports:
            # - **Name**: (old format with bullet and colon)
            # 1. **Name** (new format with number, no colon)
            # - **Name** (bullet without colon)
            char_pattern = r'(?:^|\n)\s*(?:-|\d+\.)\s*\*\*([A-Z][a-zA-ZäöüÄÖÜß]+(?:\s+(?:"[^"]+")?\s*[A-Z][a-zA-ZäöüÄÖÜß]+)*)\*\*:?'
            char_matches = list(re.finditer(char_pattern, char_section, re.MULTILINE))

            if char_matches:
                # Filter out field names and invalid entries
                field_blacklist = {
                    "Profile",
                    "Description",
                    "Motivation",
                    "Traits",
                    "Background",
                    "Character Arc",
                    "Arc",
                    "Conflict",
                    "Development",
                    "Personality",
                    "Appearance",
                    "Role",
                    "Age",
                    "Backstory",
                    "History",
                    "Character Dynamics",
                    "Backstories",
                    "Character Development",
                    "Narrative Suggestions",
                    "Additional Elements",
                    "Minor Details",
                    "Psychological Complexity",
                    "Motifs",
                    "Setting Considerations",
                    "Plot Points",
                    "Themes",
                    "Symbolism",
                    "Narrative",
                    "Story",
                    "Interpersonal Tensions",
                    "Symbols",
                    "Elements",
                }

                # Additional keywords that disqualify a name
                blacklist_keywords = [
                    "###",
                    "####",
                    "Character",
                    "Considerations",
                    "Complexity",
                    "Suggestions",
                ]

                valid_names = []
                for char_match in char_matches:
                    name = char_match.group(1).strip()

                    # Skip if:
                    # 1. In blacklist
                    # 2. Contains blacklisted keywords
                    # 3. Is single word (real names have at least 2 words usually)
                    # 4. Starts with lowercase (field names like "early 30s")
                    word_count = len(name.split())
                    is_valid = (
                        name not in field_blacklist
                        and not any(bl in name for bl in blacklist_keywords)
                        and word_count >= 2  # At least first + last name
                        and name[0].isupper()
                    )

                    if is_valid:
                        valid_names.append((char_match, name))

                print(f"   📋 Found {len(valid_names)} valid names in {char_type} section")

                for char_match, name in valid_names:
                    # Get content for this specific character
                    char_start = char_match.end()
                    # Find next character or end of section
                    next_char = re.search(r"-?\s*\*\*[A-Z]", char_section[char_start:])
                    char_end = char_start + next_char.start() if next_char else len(char_section)

                    char_content = char_section[char_start:char_end].strip()
                    char_data = extract_character_data(char_content, char_type, name=name)
                    if char_data:
                        characters.append(char_data)
            else:
                # Fallback: try to extract from whole section
                char_data = extract_character_data(char_section, char_type)
                if char_data:
                    characters.append(char_data)

        if characters:
            return characters

    # Pattern 2: **1. Name** or **Name** (Protagonist) format
    # Match: **1. Peter Baumann** (Protagonist) or just **Peter Baumann**
    pattern2 = r"\*\*(?:\d+\.\s*)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\*\*\s*(?:\(([^)]+)\))?"
    matches2 = list(re.finditer(pattern2, content))

    if matches2:
        print(f"   🔍 Found {len(matches2)} character names (pattern 2)")
        # Filter out field names (Profile, Motivation, etc.)
        field_names = {
            "Profile",
            "Motivation",
            "Traits",
            "Background",
            "Character Arc",
            "Arc",
            "Conflict",
            "Development",
            "Personality",
            "Appearance",
        }

        valid_matches = []
        for match in matches2:
            name = match.group(1).strip()
            # Skip if it's a field name
            if name not in field_names and not any(
                fn.lower() in name.lower() for fn in field_names
            ):
                valid_matches.append(match)

        print(f"   ✅ Valid character names: {len(valid_matches)}")

        for match in valid_matches:
            name = match.group(1).strip()
            char_type = match.group(2).strip().lower() if match.group(2) else "main"

            # Find section for this character
            start = match.end()
            # Look ahead to next character or end
            next_match_pattern = r"\*\*(?:\d+\.\s*)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\*\*"
            next_match = re.search(next_match_pattern, content[start:])
            end = start + next_match.start() if next_match else len(content)

            char_section = content[start:end].strip()
            char_data = extract_character_data(char_section, char_type, name=name)
            if char_data:
                characters.append(char_data)

        if characters:
            return characters

    # Pattern 3: Simple numbered list
    pattern3 = r"\d+\.\s*\*?\*?([A-Za-z\s]+)\*?\*?"
    matches3 = list(re.finditer(pattern3, content))

    if matches3 and len(matches3) >= 2:
        print(f"   🔍 Found {len(matches3)} numbered characters (pattern 3)")
        for match in matches3:
            name = match.group(1).strip()
            start = match.end()
            # Find next number or end
            next_num = re.search(r"\n\d+\.", content[start:])
            end = start + next_num.start() if next_num else len(content)

            char_section = content[start:end].strip()
            char_data = extract_character_data(char_section, "main", name=name)
            if char_data:
                characters.append(char_data)

    if not characters:
        print("   ❌ No characters could be parsed from content")
        print("   💡 TIP: Use structured JSON output for reliable parsing!")

    return characters[:8]  # Limit to 8 characters


def extract_character_data(
    section: str, char_type: str = "main", name: str = None
) -> Dict[str, Any]:
    """
    Extract character data from a text section

    Args:
        section: Text section containing character info
        char_type: Character type (protagonist, antagonist, etc.)
        name: Character name (if already extracted)

    Returns:
        Character dictionary matching Characters model fields
    """
    # Map char_type to role
    role_map = {
        "protagonist": "Protagonist",
        "antagonist": "Antagonist",
        "supporting": "Supporting Character",
        "supporting_characters": "Supporting Character",
        "minor": "Minor Character",
        "minor_characters": "Minor Character",
        "love_interest": "Love Interest",
        "main": "Main Character",
    }

    char_data = {
        "name": name or "Unknown Character",
        "role": role_map.get(char_type, "Supporting Character"),
        "description": "",
        "background": "",
        "motivation": "",
        "personality": "",
        "arc": "",
        "age": None,
    }

    # Extract name if not provided
    if not name:
        name_match = re.search(r"\*\*([A-Za-z\s]+)\*\*", section)
        if name_match:
            char_data["name"] = name_match.group(1).strip()

    # Extract fields - map to Characters model fields
    # Note: "Role" is already captured in char_type/role mapping
    fields = {
        "description": ["profile", "description", "role"],  # Role can be description
        "motivation": ["motivation", "goal", "desire"],
        "personality": ["traits", "personality", "character"],
        "arc": ["character arc", "arc", "development", "journey"],
        "background": ["background", "backstory", "history", "past"],
    }

    # Try to extract labeled fields first
    # Pattern now handles both formats:
    # **Field**: value
    # - **Field**: value (with bullet and indent)
    for model_field, keywords in fields.items():
        for keyword in keywords:
            # Try with bullet/indent first (new format)
            pattern = rf"(?:^|\n)\s*-\s*\*\*{keyword}\*\*:?\s*(.+?)(?=\n\s*-\s*\*\*|\n\n|$)"
            match = re.search(pattern, section, re.IGNORECASE | re.DOTALL)

            if not match:
                # Try without bullet (old format)
                pattern = rf"\*\*{keyword}\*\*:?\s*(.+?)(?=\n\s*-|\n\s*\*\*|$)"
                match = re.search(pattern, section, re.IGNORECASE | re.DOTALL)

            if match:
                value = match.group(1).strip()
                # Clean up value: remove extra whitespace and newlines
                value = " ".join(value.split())
                if value:
                    char_data[model_field] = value
                break

    # If no labeled fields found, use entire section as description
    if not char_data["description"] and section:
        # Clean up section: remove bullets, stars, etc.
        clean_section = re.sub(r"^\s*-\s*", "", section, flags=re.MULTILINE)
        clean_section = re.sub(r"\*\*([^*]+)\*\*", r"\1", clean_section)
        clean_section = clean_section.strip()

        # Take first 500 chars for description
        if clean_section:
            char_data["description"] = clean_section[:500]

            # Try to extract age if mentioned
            age_match = re.search(
                r"(?:in\s+(?:his|her|their)\s+)?(?:early|mid|late)?\s*(\d+)(?:s|years?\s+old)",
                section,
                re.IGNORECASE,
            )
            if age_match:
                try:
                    char_data["age"] = int(age_match.group(1))
                except (ValueError, AttributeError):
                    pass

    # Only return if we have at least a name
    if char_data["name"] and char_data["name"] != "Unknown Character":
        return char_data

    return None


# Alias for backward compatibility
parse_character_cast = parse_character_cast_structured
