"""
Visualization service - Generate visual representations of story structure.
Supports Mermaid diagrams, HTML exports, and timeline views.
"""

from typing import Optional

from ..models import Character, Novel, PlotThread, Scene


class VisualizationService:
    """Service for generating story visualizations."""

    # =========================================================================
    # Mermaid Diagram Generators
    # =========================================================================

    def generate_structure_diagram(self, novel: Novel) -> str:
        """Generate a Mermaid flowchart of the novel structure."""
        lines = [
            "```mermaid",
            "flowchart TB",
            f'    Novel["{self._escape(novel.title)}"]',
        ]

        for act in novel.acts:
            act_node = f"Act{act.number}"
            lines.append(f'    {act_node}["{self._escape(act.title)}"]')
            lines.append(f"    Novel --> {act_node}")

            for chapter in act.chapters:
                chap_node = f"Ch{act.number}_{chapter.number}"
                lines.append(f'    {chap_node}["{self._escape(chapter.title)}"]')
                lines.append(f"    {act_node} --> {chap_node}")

                for scene in chapter.scenes:
                    scene_node = f"Sc{scene.id[:4]}"
                    scene_label = self._escape(scene.title[:20])
                    lines.append(f'    {scene_node}("{scene_label}")')
                    lines.append(f"    {chap_node} --> {scene_node}")

        lines.append("```")
        return "\n".join(lines)

    def generate_plot_threads_diagram(self, novel: Novel) -> str:
        """Generate a Mermaid diagram showing plot thread flow."""
        scenes = novel.get_all_scenes()
        if not scenes or not novel.plot_threads:
            return "Keine Handlungsstränge oder Szenen vorhanden."

        lines = [
            "```mermaid",
            "flowchart LR",
        ]

        # Define subgraphs for each plot thread
        for thread in novel.plot_threads:
            thread_scenes = [s for s in scenes if thread.id in s.plot_thread_ids]
            if thread_scenes:
                lines.append(f'    subgraph {thread.id[:8]}["{self._escape(thread.name)}"]')

                prev_node = None
                for scene in thread_scenes:
                    node = f"S{scene.id[:6]}"
                    lines.append(f'        {node}["{self._escape(scene.title[:15])}"]')
                    if prev_node:
                        lines.append(f"        {prev_node} --> {node}")
                    prev_node = node

                lines.append("    end")

        lines.append("```")
        return "\n".join(lines)

    def generate_timeline_diagram(self, novel: Novel) -> str:
        """Generate a Mermaid timeline of story events."""
        scenes = novel.get_all_scenes()

        # Sort scenes that have story dates
        dated_scenes = [s for s in scenes if s.story_date_description or s.story_datetime]

        lines = [
            "```mermaid",
            "timeline",
            f"    title {self._escape(novel.title)} - Zeitleiste",
        ]

        current_section = ""
        for scene in dated_scenes:
            date_label = scene.story_date_description or str(scene.story_datetime)[:10]

            if date_label != current_section:
                lines.append(f"    section {self._escape(date_label)}")
                current_section = date_label

            lines.append(f"        {self._escape(scene.title[:30])}")

        if not dated_scenes:
            lines.append("    section Keine Zeitangaben")
            lines.append("        Füge story_date_description zu Szenen hinzu")

        lines.append("```")
        return "\n".join(lines)

    def generate_character_scene_matrix(self, novel: Novel) -> str:
        """Generate a character-scene presence matrix as Markdown table."""
        scenes = novel.get_all_scenes()
        if not scenes or not novel.characters:
            return "Keine Szenen oder Charaktere vorhanden."

        # Header
        char_names = [c.name[:10] for c in novel.characters[:8]]  # Limit for readability
        header = "| Szene | " + " | ".join(char_names) + " | Konflikt |"
        separator = "|-------|" + "|".join(["---"] * len(char_names)) + "|----------|"

        lines = [header, separator]

        for scene in scenes[:20]:  # Limit rows
            row = [scene.title[:15]]

            for char in novel.characters[:8]:
                if char.id == scene.pov_character_id:
                    row.append("**●**")  # POV character
                elif char.id in scene.character_ids:
                    row.append("○")  # Present
                else:
                    row.append(" ")

            row.append(scene.conflict_level.value)
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)

    def generate_scene_connections_diagram(self, novel: Novel) -> str:
        """Generate a diagram of scene connections (foreshadowing, callbacks, etc.)."""
        if not novel.scene_connections:
            return "Keine Szenenverbindungen definiert."

        lines = [
            "```mermaid",
            "flowchart LR",
        ]

        # Define connection styles
        connection_styles = {
            "foreshadows": "-.->",
            "callback": "-->",
            "parallel": "<-->",
            "contrast": "x--x",
            "cause-effect": "==>",
        }

        # Add scene nodes
        scenes_in_connections = set()
        for conn in novel.scene_connections:
            scenes_in_connections.add(conn.from_scene_id)
            scenes_in_connections.add(conn.to_scene_id)

        for scene_id in scenes_in_connections:
            scene = novel.get_scene(scene_id)
            if scene:
                lines.append(f'    {scene_id[:6]}["{self._escape(scene.title[:20])}"]')

        # Add connections
        for conn in novel.scene_connections:
            arrow = connection_styles.get(conn.connection_type, "-->")
            label = conn.connection_type
            lines.append(f"    {conn.from_scene_id[:6]} {arrow}|{label}| {conn.to_scene_id[:6]}")

        lines.append("```")
        return "\n".join(lines)

    # =========================================================================
    # Text Reports
    # =========================================================================

    def generate_outline_text(self, novel: Novel, include_details: bool = True) -> str:
        """Generate a text-based outline of the novel."""
        lines = [
            f"# {novel.title}",
            f"*{novel.author}*" if novel.author else "",
            "",
            f"**Genre:** {novel.genre}" if novel.genre else "",
            f"**Logline:** {novel.logline}" if novel.logline else "",
            f"**Ziel-Wortanzahl:** {novel.target_word_count:,}",
            "",
            "---",
            "",
        ]

        for act in novel.acts:
            lines.append(f"## {act.title}")
            if act.description:
                lines.append(f"*{act.description}*")
            lines.append("")

            for chapter in act.chapters:
                lines.append(f"### Kapitel {chapter.number}: {chapter.title}")
                if chapter.summary and include_details:
                    lines.append(f"> {chapter.summary}")
                lines.append("")

                for scene in chapter.scenes:
                    pov = ""
                    if scene.pov_character_id:
                        char = novel.get_character(scene.pov_character_id)
                        pov = f" [{char.name}]" if char else ""

                    status_emoji = {
                        "idea": "💡",
                        "outlined": "📝",
                        "drafted": "✍️",
                        "revised": "🔄",
                        "final": "✅",
                    }
                    emoji = status_emoji.get(scene.status.value, "")

                    lines.append(f"- {emoji} **{scene.title}**{pov}")

                    if include_details and scene.summary:
                        lines.append(f"  - {scene.summary[:100]}...")
                    if include_details and scene.goal:
                        lines.append(f"  - *Ziel: {scene.goal}*")

                lines.append("")

        return "\n".join(lines)

    def generate_synopsis(self, novel: Novel) -> str:
        """Generate a synopsis from scene summaries."""
        lines = [f"# Synopsis: {novel.title}", ""]

        for act in novel.acts:
            lines.append(f"## {act.title}")
            lines.append("")

            act_summary = []
            for chapter in act.chapters:
                for scene in chapter.scenes:
                    if scene.summary:
                        act_summary.append(scene.summary)

            if act_summary:
                lines.append(" ".join(act_summary))
            else:
                lines.append("*Noch keine Zusammenfassungen vorhanden.*")

            lines.append("")

        return "\n".join(lines)

    # =========================================================================
    # Export Formats
    # =========================================================================

    def export_to_markdown(self, novel: Novel) -> str:
        """Export complete novel outline to Markdown."""
        sections = [
            self.generate_outline_text(novel),
            "",
            "---",
            "",
            "## Charaktere",
            "",
        ]

        for char in novel.characters:
            sections.append(f"### {char.name}")
            sections.append(f"**Rolle:** {char.role}")
            if char.description:
                sections.append(f"\n{char.description}")
            if char.arc:
                sections.append(f"\n**Charakterbogen:** {char.arc}")
            sections.append("")

        sections.extend(
            [
                "---",
                "",
                "## Handlungsstränge",
                "",
            ]
        )

        for thread in novel.plot_threads:
            sections.append(f"### {thread.name} ({thread.thread_type})")
            if thread.description:
                sections.append(f"\n{thread.description}")
            if thread.resolution:
                sections.append(f"\n**Auflösung:** {thread.resolution}")
            sections.append("")

        return "\n".join(sections)

    def export_to_html(self, novel: Novel) -> str:
        """Export novel outline to a simple HTML page."""
        outline_md = self.generate_outline_text(novel)

        html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{novel.title} - Outline</title>
    <style>
        body {{ font-family: 'Segoe UI', system-ui, sans-serif; max-width: 900px; margin: 0 auto; padding: 2rem; line-height: 1.6; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 0.5rem; }}
        h2 {{ color: #34495e; margin-top: 2rem; }}
        h3 {{ color: #7f8c8d; }}
        blockquote {{ border-left: 4px solid #3498db; padding-left: 1rem; color: #666; margin: 1rem 0; }}
        li {{ margin: 0.5rem 0; }}
        .status {{ font-size: 0.9em; color: #888; }}
        .character {{ background: #f8f9fa; padding: 1rem; border-radius: 8px; margin: 1rem 0; }}
        .thread {{ background: #fff3cd; padding: 1rem; border-radius: 8px; margin: 1rem 0; }}
    </style>
</head>
<body>
    <h1>{novel.title}</h1>
    <p><em>{novel.author}</em></p>
    <p><strong>Genre:</strong> {novel.genre} | <strong>Ziel:</strong> {novel.target_word_count:,} Wörter</p>

    <h2>Struktur</h2>
"""

        for act in novel.acts:
            html += f"<h3>{act.title}</h3>\n"
            if act.description:
                html += f"<p><em>{act.description}</em></p>\n"

            for chapter in act.chapters:
                html += f"<h4>Kapitel {chapter.number}: {chapter.title}</h4>\n<ul>\n"

                for scene in chapter.scenes:
                    pov_name = ""
                    if scene.pov_character_id:
                        char = novel.get_character(scene.pov_character_id)
                        pov_name = f" <span class='status'>[{char.name}]</span>" if char else ""

                    html += f"<li><strong>{scene.title}</strong>{pov_name}"
                    if scene.summary:
                        html += f"<br><small>{scene.summary[:150]}...</small>"
                    html += "</li>\n"

                html += "</ul>\n"

        html += """
    <h2>Charaktere</h2>
"""

        for char in novel.characters:
            html += f"""
    <div class="character">
        <strong>{char.name}</strong> ({char.role})<br>
        {char.description if char.description else '<em>Keine Beschreibung</em>'}
    </div>
"""

        html += """
    <h2>Handlungsstränge</h2>
"""

        for thread in novel.plot_threads:
            html += f"""
    <div class="thread">
        <strong>{thread.name}</strong> ({thread.thread_type})<br>
        {thread.description if thread.description else '<em>Keine Beschreibung</em>'}
    </div>
"""

        html += """
</body>
</html>"""

        return html

    # =========================================================================
    # Helpers
    # =========================================================================

    def _escape(self, text: str) -> str:
        """Escape special characters for Mermaid."""
        return text.replace('"', "'").replace("\n", " ").replace("#", "")
