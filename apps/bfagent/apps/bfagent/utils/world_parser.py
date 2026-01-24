"""
World Parser for BF Agent
Parses LLM-generated world descriptions into structured data
"""

import re
from typing import Any, Dict, List


def parse_world_collection(content: str, project) -> List[Dict[str, Any]]:
    """Parse AI-generated world collection into structured world data"""
    worlds = []

    # Split content into sections by world numbers (#### 1. World Name, #### 2. World Name, etc.)
    world_sections = re.split(r"####\s*\d+\.\s*([A-Za-z\s\-']+)", content)

    # Process each world section
    for i in range(1, len(world_sections), 2):  # Skip first empty section, then take pairs
        if i + 1 < len(world_sections):
            name = world_sections[i].strip()
            world_content = world_sections[i + 1].strip()

            # Extract world details
            world_data = {
                "name": name,
                "description": "",
                "world_type": "primary",
                "setting_details": "",
                "geography": "",
                "culture": "",
                "technology_level": "",
                "magic_system": "",
                "politics": "",
                "history": "",
                "inhabitants": "",
                "connections": "",
            }

            # Parse structured content
            lines = world_content.split("\n")
            current_field = None

            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Check for field markers
                if "**Type**:" in line:
                    world_type = line.split("**Type**:")[1].strip()
                    world_data["world_type"] = world_type.lower()
                elif "**Description**:" in line:
                    description = line.split("**Description**:")[1].strip()
                    world_data["description"] = description
                elif "**Geography**:" in line:
                    geography = line.split("**Geography**:")[1].strip()
                    world_data["geography"] = geography
                elif "**Culture**:" in line:
                    culture = line.split("**Culture**:")[1].strip()
                    world_data["culture"] = culture
                elif "**Technology**:" in line:
                    tech = line.split("**Technology**:")[1].strip()
                    world_data["technology_level"] = tech
                elif "**Magic System**:" in line:
                    magic = line.split("**Magic System**:")[1].strip()
                    world_data["magic_system"] = magic
                elif "**Politics**:" in line:
                    politics = line.split("**Politics**:")[1].strip()
                    world_data["politics"] = politics
                elif "**History**:" in line:
                    history = line.split("**History**:")[1].strip()
                    world_data["history"] = history
                elif "**Inhabitants**:" in line:
                    inhabitants = line.split("**Inhabitants**:")[1].strip()
                    world_data["inhabitants"] = inhabitants
                elif "**Connections**:" in line:
                    connections = line.split("**Connections**:")[1].strip()
                    world_data["connections"] = connections
                elif "**Setting Details**:" in line:
                    setting = line.split("**Setting Details**:")[1].strip()
                    world_data["setting_details"] = setting
                elif line.startswith("- **") and ":" in line:
                    # Generic field parsing
                    field_content = line.split(":", 1)[1].strip()
                    if world_data["description"]:
                        world_data["description"] += f" {field_content}"
                    else:
                        world_data["description"] = field_content

            # Clean up world type
            if world_data["world_type"] in ["main", "primary", "central"]:
                world_data["world_type"] = "primary"
            elif world_data["world_type"] in ["secondary", "side", "alternate"]:
                world_data["world_type"] = "secondary"
            elif "parallel" in world_data["world_type"].lower():
                world_data["world_type"] = "parallel"
            elif "pocket" in world_data["world_type"].lower():
                world_data["world_type"] = "pocket"

            worlds.append(world_data)

    # Fallback: create default worlds if parsing failed
    if not worlds:
        worlds = [
            {
                "name": "Primary World",
                "description": "Main setting for the story",
                "world_type": "primary",
                "setting_details": "Central world where most action takes place",
                "geography": "",
                "culture": "",
                "technology_level": "",
                "magic_system": "",
                "politics": "",
                "history": "",
                "inhabitants": "",
                "connections": "",
            },
            {
                "name": "Secondary Realm",
                "description": "Alternative setting or parallel dimension",
                "world_type": "secondary",
                "setting_details": "Supporting world that complements the main story",
                "geography": "",
                "culture": "",
                "technology_level": "",
                "magic_system": "",
                "politics": "",
                "history": "",
                "inhabitants": "",
                "connections": "",
            },
            {
                "name": "Hidden Domain",
                "description": "Secret or mystical location",
                "world_type": "pocket",
                "setting_details": "Special world accessible under certain conditions",
                "geography": "",
                "culture": "",
                "technology_level": "",
                "magic_system": "",
                "politics": "",
                "history": "",
                "inhabitants": "",
                "connections": "",
            },
        ]

    return worlds[:6]  # Limit to 6 worlds max
