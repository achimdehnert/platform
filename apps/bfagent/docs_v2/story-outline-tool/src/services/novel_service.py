"""
Novel service - Business logic for managing stories.
"""

from datetime import datetime
from typing import Optional

from ..models import (
    Act,
    Beat,
    Chapter,
    Character,
    Location,
    Novel,
    PlotThread,
    Scene,
    SceneConnection,
    Status,
    TimelineEvent,
    generate_id,
)
from ..models.templates import StoryTemplate, get_template, list_templates
from ..repositories import BackupManager, NovelRepository


class NovelService:
    """Service for managing novels and their structure."""

    def __init__(self, storage_dir: str = "~/.story-outline"):
        self.repo = NovelRepository(storage_dir)
        self.backup = BackupManager(storage_dir)

    # =========================================================================
    # Novel CRUD
    # =========================================================================

    def create_novel(
        self,
        title: str,
        author: str = "",
        genre: str = "",
        template_id: Optional[str] = None,
        target_word_count: int = 80000,
    ) -> Novel:
        """Create a new novel, optionally from a template."""
        novel = Novel(
            title=title,
            author=author,
            genre=genre,
            target_word_count=target_word_count,
            template_used=template_id,
        )

        if template_id:
            template = get_template(template_id)
            if template:
                novel = self._apply_template(novel, template)

        self.repo.save(novel)
        return novel

    def get_novel(self, novel_id: str) -> Optional[Novel]:
        """Get a novel by ID."""
        return self.repo.load(novel_id)

    def save_novel(self, novel: Novel, create_backup: bool = False) -> None:
        """Save a novel, optionally creating a backup first."""
        if create_backup:
            self.backup.create_backup(novel)
        self.repo.save(novel)

    def delete_novel(self, novel_id: str) -> bool:
        """Delete a novel."""
        return self.repo.delete(novel_id)

    def list_novels(self) -> list[dict]:
        """List all novels."""
        return self.repo.list_all()

    # =========================================================================
    # Template Operations
    # =========================================================================

    def _apply_template(self, novel: Novel, template: StoryTemplate) -> Novel:
        """Apply a template structure to a novel."""
        words_per_act = novel.target_word_count

        for tpl_act in template.acts:
            act = Act(
                title=tpl_act.name,
                number=tpl_act.number,
                description=tpl_act.description,
                target_word_percentage=tpl_act.target_percent,
                order=tpl_act.number,
            )

            # Create a chapter for each beat (simplified)
            for i, beat in enumerate(tpl_act.beats, 1):
                chapter = Chapter(
                    title=beat.name,
                    number=i,
                    summary=beat.description,
                    notes=f"Fragen zu beantworten:\n" + "\n".join(f"- {q}" for q in beat.questions),
                    order=i,
                )

                # Create a placeholder scene
                scene = Scene(
                    title=f"{beat.name} - Szene 1",
                    summary=beat.description,
                    goal=beat.purpose,
                    order=1,
                )
                chapter.scenes.append(scene)
                act.chapters.append(chapter)

            novel.acts.append(act)

        return novel

    def get_available_templates(self) -> list[dict]:
        """Get list of available templates with basic info."""
        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "genres": t.genre_suited,
                "acts_count": len(t.acts),
            }
            for t in list_templates()
        ]

    # =========================================================================
    # Structure Operations
    # =========================================================================

    def add_act(self, novel: Novel, title: str, description: str = "") -> Act:
        """Add a new act to the novel."""
        act = Act(
            title=title,
            number=len(novel.acts) + 1,
            description=description,
            order=len(novel.acts),
        )
        novel.acts.append(act)
        self.repo.save(novel)
        return act

    def add_chapter(self, novel: Novel, act_id: str, title: str) -> Optional[Chapter]:
        """Add a chapter to an act."""
        for act in novel.acts:
            if act.id == act_id:
                chapter = Chapter(
                    title=title,
                    number=len(act.chapters) + 1,
                    order=len(act.chapters),
                )
                act.chapters.append(chapter)
                self.repo.save(novel)
                return chapter
        return None

    def add_scene(
        self,
        novel: Novel,
        chapter_id: str,
        title: str,
        summary: str = "",
        pov_character_id: Optional[str] = None,
    ) -> Optional[Scene]:
        """Add a scene to a chapter."""
        for act in novel.acts:
            for chapter in act.chapters:
                if chapter.id == chapter_id:
                    scene = Scene(
                        title=title,
                        summary=summary,
                        pov_character_id=pov_character_id,
                        order=len(chapter.scenes),
                    )
                    chapter.scenes.append(scene)
                    self.repo.save(novel)
                    return scene
        return None

    def move_scene(
        self, novel: Novel, scene_id: str, target_chapter_id: str, position: int = -1
    ) -> bool:
        """Move a scene to a different chapter or position."""
        scene_to_move = None
        source_chapter = None

        # Find and remove scene from source
        for act in novel.acts:
            for chapter in act.chapters:
                for i, scene in enumerate(chapter.scenes):
                    if scene.id == scene_id:
                        scene_to_move = chapter.scenes.pop(i)
                        source_chapter = chapter
                        break
                if scene_to_move:
                    break
            if scene_to_move:
                break

        if not scene_to_move:
            return False

        # Add to target chapter
        for act in novel.acts:
            for chapter in act.chapters:
                if chapter.id == target_chapter_id:
                    if position < 0 or position >= len(chapter.scenes):
                        chapter.scenes.append(scene_to_move)
                    else:
                        chapter.scenes.insert(position, scene_to_move)

                    # Re-order scenes
                    for i, s in enumerate(chapter.scenes):
                        s.order = i

                    self.repo.save(novel)
                    return True

        # If target not found, put it back
        if source_chapter:
            source_chapter.scenes.append(scene_to_move)

        return False

    # =========================================================================
    # Character Operations
    # =========================================================================

    def add_character(
        self,
        novel: Novel,
        name: str,
        role: str = "supporting",
        description: str = "",
    ) -> Character:
        """Add a character to the novel."""
        colors = ["#3498db", "#e74c3c", "#2ecc71", "#9b59b6", "#f39c12", "#1abc9c"]
        color = colors[len(novel.characters) % len(colors)]

        character = Character(
            name=name,
            role=role,
            description=description,
            color=color,
        )
        novel.characters.append(character)
        self.repo.save(novel)
        return character

    # =========================================================================
    # Plot Thread Operations
    # =========================================================================

    def add_plot_thread(
        self,
        novel: Novel,
        name: str,
        description: str = "",
        thread_type: str = "subplot",
    ) -> PlotThread:
        """Add a plot thread to the novel."""
        colors = ["#e74c3c", "#3498db", "#2ecc71", "#9b59b6", "#f39c12"]
        color = colors[len(novel.plot_threads) % len(colors)]

        thread = PlotThread(
            name=name,
            description=description,
            thread_type=thread_type,
            color=color,
        )
        novel.plot_threads.append(thread)
        self.repo.save(novel)
        return thread

    def connect_scene_to_thread(self, novel: Novel, scene_id: str, thread_id: str) -> bool:
        """Connect a scene to a plot thread."""
        scene = novel.get_scene(scene_id)
        if scene and thread_id not in scene.plot_thread_ids:
            scene.plot_thread_ids.append(thread_id)
            self.repo.save(novel)
            return True
        return False

    # =========================================================================
    # Scene Connections
    # =========================================================================

    def add_scene_connection(
        self,
        novel: Novel,
        from_scene_id: str,
        to_scene_id: str,
        connection_type: str,
        description: str = "",
    ) -> SceneConnection:
        """Add a connection between two scenes."""
        connection = SceneConnection(
            from_scene_id=from_scene_id,
            to_scene_id=to_scene_id,
            connection_type=connection_type,
            description=description,
        )
        novel.scene_connections.append(connection)
        self.repo.save(novel)
        return connection


class AnalysisService:
    """Service for analyzing novel structure and content."""

    def analyze_character_presence(self, novel: Novel) -> dict:
        """Analyze how often each character appears in scenes."""
        scenes = novel.get_all_scenes()
        total_scenes = len(scenes)

        character_stats = {}
        for char in novel.characters:
            char_scenes = novel.get_scenes_by_character(char.id)
            pov_scenes = [s for s in char_scenes if s.pov_character_id == char.id]

            character_stats[char.id] = {
                "name": char.name,
                "role": char.role,
                "total_scenes": len(char_scenes),
                "pov_scenes": len(pov_scenes),
                "percentage": (len(char_scenes) / total_scenes * 100) if total_scenes > 0 else 0,
            }

        return character_stats

    def analyze_plot_coverage(self, novel: Novel) -> dict:
        """Analyze how well plot threads are covered."""
        scenes = novel.get_all_scenes()
        total_scenes = len(scenes)

        thread_stats = {}
        for thread in novel.plot_threads:
            thread_scenes = novel.get_scenes_by_plot_thread(thread.id)

            # Find gaps (consecutive scenes without this thread)
            gaps = []
            current_gap = 0
            for scene in scenes:
                if thread.id in scene.plot_thread_ids:
                    if current_gap > 2:  # Gap of more than 2 scenes
                        gaps.append(current_gap)
                    current_gap = 0
                else:
                    current_gap += 1

            thread_stats[thread.id] = {
                "name": thread.name,
                "type": thread.thread_type,
                "scene_count": len(thread_scenes),
                "percentage": (len(thread_scenes) / total_scenes * 100) if total_scenes > 0 else 0,
                "has_resolution": bool(thread.resolution),
                "gaps": gaps,
            }

        return thread_stats

    def analyze_pacing(self, novel: Novel) -> dict:
        """Analyze the emotional pacing of the story."""
        scenes = novel.get_all_scenes()

        conflict_distribution = {
            "none": 0,
            "low": 0,
            "medium": 0,
            "high": 0,
            "climax": 0,
        }

        for scene in scenes:
            conflict_distribution[scene.conflict_level.value] += 1

        # Find potential pacing issues
        issues = []
        consecutive_high = 0
        consecutive_low = 0

        for i, scene in enumerate(scenes):
            if scene.conflict_level.value in ["high", "climax"]:
                consecutive_high += 1
                consecutive_low = 0
                if consecutive_high > 3:
                    issues.append(
                        f"Zu viele aufeinanderfolgende High-Conflict-Szenen ab Szene {i-2}"
                    )
            elif scene.conflict_level.value in ["none", "low"]:
                consecutive_low += 1
                consecutive_high = 0
                if consecutive_low > 4:
                    issues.append(
                        f"Möglicher Durchhänger: {consecutive_low} Low-Conflict-Szenen ab Szene {i-consecutive_low+1}"
                    )
            else:
                consecutive_high = 0
                consecutive_low = 0

        return {
            "conflict_distribution": conflict_distribution,
            "total_scenes": len(scenes),
            "pacing_issues": issues,
        }

    def analyze_word_count(self, novel: Novel) -> dict:
        """Analyze word count progress."""
        stats = novel.calculate_word_count()

        act_stats = []
        for act in novel.acts:
            act_actual = sum(s.word_count_actual for c in act.chapters for s in c.scenes)
            act_target = (act.target_word_percentage / 100) * novel.target_word_count

            act_stats.append(
                {
                    "act": act.title,
                    "actual": act_actual,
                    "target": int(act_target),
                    "percentage": (act_actual / act_target * 100) if act_target > 0 else 0,
                }
            )

        return {
            **stats,
            "acts": act_stats,
        }

    def get_status_summary(self, novel: Novel) -> dict:
        """Get summary of scene statuses."""
        scenes = novel.get_all_scenes()

        status_counts = {}
        for status in Status:
            status_counts[status.value] = 0

        for scene in scenes:
            status_counts[scene.status.value] += 1

        return {
            "total_scenes": len(scenes),
            "status_counts": status_counts,
            "completion_percentage": (
                (
                    (status_counts.get("final", 0) + status_counts.get("revised", 0))
                    / len(scenes)
                    * 100
                )
                if scenes
                else 0
            ),
        }
