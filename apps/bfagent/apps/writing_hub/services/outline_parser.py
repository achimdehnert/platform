"""
Outline Parser Service
Parse text input into structured outline data
Supports multiple formats and natural language
"""

import json
import re
from typing import Any, Dict, List, Optional


class OutlineParser:
    """
    Parse text input into structured outline data

    Supports:
    - Numbered lists
    - Markdown
    - Natural language
    - JSON
    - YAML-style
    """

    @staticmethod
    def parse(text: str, framework: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse outline text into structured data

        Input formats:
        - "1. Opening Image\n2. Catalyst\n3. ..."
        - "# Act 1\n## Beat 1: Opening\n..."
        - "Opening -> Catalyst -> All is Lost -> ..."
        - JSON/YAML

        Output:
        {
            'framework': 'Save the Cat',
            'beats': [
                {'number': 1, 'name': 'Opening Image', 'description': '...', 'position': 0.0},
                ...
            ]
        }
        """
        text = text.strip()

        # Try JSON first
        if text.startswith("{") or text.startswith("["):
            return OutlineParser._parse_json(text, framework)

        # Try YAML-style
        if ":" in text and "\n" in text:
            return OutlineParser._parse_yaml_style(text, framework)

        # Try arrow notation (Opening -> Catalyst -> ...)
        if "->" in text:
            return OutlineParser._parse_arrow_notation(text, framework)

        # Try numbered list
        if re.match(r"^\d+\.", text):
            return OutlineParser._parse_numbered_list(text, framework)

        # Try markdown headers
        if text.startswith("#"):
            return OutlineParser._parse_markdown(text, framework)

        # Fallback: split by newlines
        return OutlineParser._parse_simple_lines(text, framework)

    @staticmethod
    def _parse_json(text: str, framework: Optional[str]) -> Dict[str, Any]:
        """Parse JSON format"""
        try:
            data = json.loads(text)

            if isinstance(data, list):
                # List of beats
                return {"framework": framework or "Custom", "beats": data}
            elif isinstance(data, dict):
                # Full structure
                if "beats" not in data:
                    data["beats"] = []
                if "framework" not in data:
                    data["framework"] = framework or "Custom"
                return data
        except json.JSONDecodeError:
            pass

        return {"framework": "Custom", "beats": []}

    @staticmethod
    def _parse_yaml_style(text: str, framework: Optional[str]) -> Dict[str, Any]:
        """
        Parse YAML-style format:
        Beat 1:
          name: Opening Image
          description: ...
        Beat 2:
          name: Catalyst
          description: ...
        """
        beats = []
        current_beat = None

        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Beat header (no leading spaces)
            if ":" in line and not line.startswith(" "):
                if current_beat:
                    beats.append(current_beat)

                beat_name = line.split(":")[0].strip()
                current_beat = {
                    "number": len(beats) + 1,
                    "name": beat_name,
                    "description": "",
                    "position": len(beats) / 15.0,  # Assume 15 beats
                }

            # Beat properties (indented)
            elif current_beat and ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                if key in ["name", "description", "guidance"]:
                    current_beat[key] = value

        if current_beat:
            beats.append(current_beat)

        return {"framework": framework or "Custom", "beats": beats}

    @staticmethod
    def _parse_arrow_notation(text: str, framework: Optional[str]) -> Dict[str, Any]:
        """
        Parse arrow notation:
        Opening Image -> Catalyst -> All is Lost -> Finale
        """
        parts = [p.strip() for p in text.split("->")]

        beats = []
        for i, name in enumerate(parts):
            beats.append(
                {"number": i + 1, "name": name, "description": "", "position": i / len(parts)}
            )

        return {"framework": framework or "Custom", "beats": beats}

    @staticmethod
    def _parse_numbered_list(text: str, framework: Optional[str]) -> Dict[str, Any]:
        """
        Parse numbered list:
        1. Opening Image
        2. Theme Stated
        3. Catalyst
        ...
        """
        beats = []

        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Match "1. Name" or "1) Name"
            match = re.match(r"^(\d+)[.)]?\s+(.+)$", line)
            if match:
                number = int(match.group(1))
                name = match.group(2).strip()

                # Check if there's a description (after -)
                description = ""
                if " - " in name:
                    parts = name.split(" - ", 1)
                    name = parts[0].strip()
                    description = parts[1].strip()

                beats.append(
                    {
                        "number": number,
                        "name": name,
                        "description": description,
                        "position": (number - 1) / max(15, len(beats)),
                    }
                )

        return {"framework": framework or "Custom", "beats": beats}

    @staticmethod
    def _parse_markdown(text: str, framework: Optional[str]) -> Dict[str, Any]:
        """
        Parse markdown format:
        # Act 1
        ## Beat 1: Opening Image
        Description here...

        ## Beat 2: Catalyst
        Description here...
        """
        beats = []
        current_beat = None
        current_description = []

        for line in text.split("\n"):
            # H2 headers are beats
            if line.startswith("## "):
                if current_beat:
                    current_beat["description"] = "\n".join(current_description).strip()
                    beats.append(current_beat)

                beat_text = line[3:].strip()

                # Extract number and name
                match = re.match(r"^Beat (\d+):?\s*(.+)$", beat_text, re.IGNORECASE)
                if match:
                    number = int(match.group(1))
                    name = match.group(2).strip()
                else:
                    number = len(beats) + 1
                    name = beat_text

                current_beat = {
                    "number": number,
                    "name": name,
                    "description": "",
                    "position": (number - 1) / 15.0,
                }
                current_description = []

            # Regular lines are description
            elif current_beat and line.strip() and not line.startswith("#"):
                current_description.append(line.strip())

        # Add last beat
        if current_beat:
            current_beat["description"] = "\n".join(current_description).strip()
            beats.append(current_beat)

        return {"framework": framework or "Custom", "beats": beats}

    @staticmethod
    def _parse_simple_lines(text: str, framework: Optional[str]) -> Dict[str, Any]:
        """
        Parse simple line-by-line:
        Opening Image
        Catalyst
        All is Lost
        Finale
        """
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        beats = []
        for i, name in enumerate(lines):
            beats.append(
                {"number": i + 1, "name": name, "description": "", "position": i / len(lines)}
            )

        return {"framework": framework or "Custom", "beats": beats}

    @staticmethod
    def serialize(outline_data: Dict[str, Any], format: str = "text") -> str:
        """
        Convert outline data back to text

        Formats:
        - 'text': Numbered list
        - 'markdown': Markdown format
        - 'json': JSON
        - 'yaml': YAML-style
        - 'arrow': Arrow notation
        """
        beats = outline_data.get("beats", [])
        framework = outline_data.get("framework", "Custom")

        if format == "json":
            return json.dumps(outline_data, indent=2)

        elif format == "markdown":
            lines = [f"# {framework} Outline\n"]
            for beat in beats:
                lines.append(f"## Beat {beat['number']}: {beat['name']}")
                if beat.get("description"):
                    lines.append(beat["description"])
                lines.append("")
            return "\n".join(lines)

        elif format == "yaml":
            lines = [f"framework: {framework}\n"]
            for beat in beats:
                lines.append(f"Beat {beat['number']}:")
                lines.append(f"  name: {beat['name']}")
                if beat.get("description"):
                    lines.append(f"  description: {beat['description']}")
                lines.append("")
            return "\n".join(lines)

        elif format == "arrow":
            names = [beat["name"] for beat in beats]
            return " -> ".join(names)

        else:  # text (numbered list)
            lines = []
            for beat in beats:
                line = f"{beat['number']}. {beat['name']}"
                if beat.get("description"):
                    line += f" - {beat['description']}"
                lines.append(line)
            return "\n".join(lines)

    @staticmethod
    def validate(outline_data: Dict[str, Any]) -> List[str]:
        """
        Validate outline structure
        Returns list of warnings/errors
        """
        warnings = []

        if "beats" not in outline_data:
            warnings.append("Missing 'beats' array")
            return warnings

        beats = outline_data["beats"]

        if not beats:
            warnings.append("No beats defined")

        if len(beats) < 3:
            warnings.append(f"Only {len(beats)} beats - consider adding more structure")

        # Check for duplicate numbers
        numbers = [b.get("number", 0) for b in beats]
        if len(numbers) != len(set(numbers)):
            warnings.append("Duplicate beat numbers found")

        # Check for missing names
        for i, beat in enumerate(beats):
            if not beat.get("name"):
                warnings.append(f"Beat {i+1} missing name")

        return warnings


# Convenience function
def parse_outline(text: str, framework: str = None) -> Dict[str, Any]:
    """Parse outline text into structured data"""
    return OutlineParser.parse(text, framework)


def serialize_outline(outline_data: Dict[str, Any], format: str = "text") -> str:
    """Convert outline data to text format"""
    return OutlineParser.serialize(outline_data, format)
