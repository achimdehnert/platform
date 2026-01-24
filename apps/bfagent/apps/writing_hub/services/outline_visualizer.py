"""
Outline Visualization Service
Generates visual representations of story structures
"""

import json
from typing import Any, Dict, List


class OutlineVisualizer:
    """
    Generate visualizations for story outlines
    Supports: Mermaid.js, Timeline, Gantt charts
    """

    @staticmethod
    def generate_mermaid_timeline(outline_data: Dict[str, Any]) -> str:
        """
        Generate Mermaid.js timeline from outline

        Input:
        - outline_data: {'framework': 'Save the Cat', 'beats': [...]}

        Output:
        - Mermaid.js code (string)
        """
        framework = outline_data.get("framework", "Story Outline")
        beats = outline_data.get("beats", [])

        if framework == "Save the Cat":
            return OutlineVisualizer._save_the_cat_timeline(beats)
        elif framework == "Hero's Journey":
            return OutlineVisualizer._heros_journey_timeline(beats)
        elif framework == "Three-Act Structure":
            return OutlineVisualizer._three_act_timeline(beats)
        else:
            return OutlineVisualizer._generic_timeline(beats)

    @staticmethod
    def _save_the_cat_timeline(beats: List[Dict]) -> str:
        """Generate Save the Cat Gantt timeline"""
        lines = [
            "```mermaid",
            "gantt",
            "    title Save the Cat Beat Sheet - Story Timeline",
            "    dateFormat X",
            "    axisFormat %s%%",
            "    ",
            "    section Act 1 (25%)",
        ]

        current_act = 1
        for beat in beats:
            position = int(beat.get("position", 0) * 100)
            name = beat.get("name", "Unknown")

            # Detect act changes
            if position > 25 and current_act == 1:
                lines.append("    ")
                lines.append("    section Act 2 (50%)")
                current_act = 2
            elif position > 75 and current_act == 2:
                lines.append("    ")
                lines.append("    section Act 3 (25%)")
                current_act = 3

            # Add beat (with minimal duration for visibility)
            next_pos = position + 2  # Small duration for visibility
            lines.append(f"    {name:<25} :{position}, {next_pos}")

        lines.append("```")
        return "\n".join(lines)

    @staticmethod
    def _heros_journey_timeline(stages: List[Dict]) -> str:
        """Generate Hero's Journey timeline"""
        lines = [
            "```mermaid",
            "journey",
            "    title The Hero's Journey - 12 Stages",
            "    section Act 1: Departure",
        ]

        current_act = 1
        for stage in stages:
            act = stage.get("act", 1)
            name = stage.get("stage_name", "Unknown")

            # Detect act changes
            if act != current_act:
                if act == 2:
                    lines.append("    section Act 2: Initiation")
                elif act == 3:
                    lines.append("    section Act 3: Return")
                current_act = act

            # Hero's journey uses emotional scores (1-5)
            score = 3  # Neutral by default
            if "ordeal" in name.lower() or "lost" in name.lower():
                score = 1  # Low point
            elif "reward" in name.lower() or "return" in name.lower():
                score = 5  # High point

            lines.append(f"      {name}: {score}")

        lines.append("```")
        return "\n".join(lines)

    @staticmethod
    def _three_act_timeline(acts: List[Dict]) -> str:
        """Generate Three-Act Structure timeline"""
        lines = [
            "```mermaid",
            "gantt",
            "    title Three-Act Structure",
            "    dateFormat X",
            "    axisFormat %s%%",
            "    ",
        ]

        current_act = 1
        act_name = "Act 1: Setup"
        lines.append(f"    section {act_name}")

        for item in acts:
            act = item.get("act", 1)
            chapter = item.get("chapter", 1)
            beat_name = item.get("beat_name", "Scene")

            # Detect act changes
            if act != current_act:
                if act == 2:
                    act_name = "Act 2: Confrontation"
                elif act == 3:
                    act_name = "Act 3: Resolution"
                lines.append("    ")
                lines.append(f"    section {act_name}")
                current_act = act

            # Calculate position based on chapter
            position = int((chapter / len(acts)) * 100)
            next_pos = position + 2

            lines.append(f"    Ch{chapter}: {beat_name:<20} :{position}, {next_pos}")

        lines.append("```")
        return "\n".join(lines)

    @staticmethod
    def _generic_timeline(beats: List[Dict]) -> str:
        """Generate generic timeline"""
        lines = [
            "```mermaid",
            "timeline",
            "    title Story Structure",
        ]

        for beat in beats:
            chapter = beat.get("chapter", 1)
            name = beat.get("beat_name", beat.get("name", "Beat"))

            lines.append(f"    Chapter {chapter} : {name}")

        lines.append("```")
        return "\n".join(lines)

    @staticmethod
    def generate_flowchart(outline_data: Dict[str, Any]) -> str:
        """
        Generate Mermaid.js flowchart showing story flow
        Useful for branching narratives or decision points
        """
        framework = outline_data.get("framework", "Story")
        beats = outline_data.get("beats", [])

        lines = [
            "```mermaid",
            "flowchart TD",
            "    Start[📖 Story Begins]",
        ]

        prev_id = "Start"
        for i, beat in enumerate(beats):
            beat_id = f"B{i+1}"
            name = beat.get("name", beat.get("beat_name", f"Beat {i+1}"))

            # Clean name for node
            clean_name = name.replace("'", "").replace('"', "")

            lines.append(f"    {beat_id}[{clean_name}]")
            lines.append(f"    {prev_id} --> {beat_id}")

            prev_id = beat_id

        lines.append(f"    {prev_id} --> End[🎬 The End]")
        lines.append("```")

        return "\n".join(lines)

    @staticmethod
    def generate_html_visualization(outline_data: Dict[str, Any]) -> str:
        """
        Generate standalone HTML with Mermaid.js rendering
        Can be displayed in Django template or exported
        """
        mermaid_code = OutlineVisualizer.generate_mermaid_timeline(outline_data)

        # Extract mermaid code (without ``` markers)
        mermaid_clean = mermaid_code.replace("```mermaid\n", "").replace("\n```", "")

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{outline_data.get('framework', 'Story')} Visualization</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .mermaid {{
            margin: 30px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{outline_data.get('framework', 'Story Outline')} - Visual Timeline</h1>
        <div class="mermaid">
{mermaid_clean}
        </div>
    </div>
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
    </script>
</body>
</html>
"""
        return html

    @staticmethod
    def generate_json_for_d3(outline_data: Dict[str, Any]) -> str:
        """
        Generate JSON format for D3.js visualization
        For more advanced/custom visualizations
        """
        beats = outline_data.get("beats", [])

        nodes = []
        links = []

        for i, beat in enumerate(beats):
            node = {
                "id": i,
                "name": beat.get("name", beat.get("beat_name", f"Beat {i+1}")),
                "chapter": beat.get("chapter", i + 1),
                "position": beat.get("position", i / len(beats)),
                "description": beat.get("description", ""),
                "act": beat.get("act", 1),
            }
            nodes.append(node)

            # Link to next beat
            if i > 0:
                links.append({"source": i - 1, "target": i, "value": 1})

        return json.dumps(
            {"nodes": nodes, "links": links, "framework": outline_data.get("framework", "Story")},
            indent=2,
        )


# Convenience functions
def visualize_outline(outline_data: Dict[str, Any], format: str = "mermaid") -> str:
    """
    Generate visualization for outline

    Args:
        outline_data: Outline dict from handler
        format: 'mermaid', 'html', 'flowchart', 'd3'

    Returns:
        Visualization code/HTML
    """
    if format == "mermaid":
        return OutlineVisualizer.generate_mermaid_timeline(outline_data)
    elif format == "html":
        return OutlineVisualizer.generate_html_visualization(outline_data)
    elif format == "flowchart":
        return OutlineVisualizer.generate_flowchart(outline_data)
    elif format == "d3":
        return OutlineVisualizer.generate_json_for_d3(outline_data)
    else:
        raise ValueError(f"Unknown format: {format}")
