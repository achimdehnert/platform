"""
Content Storage Service - DEPRECATED

================================================================================
DEPRECATED - DO NOT USE
================================================================================

This file has been deprecated and replaced by the consolidated Core Services.

Replacement: apps.core.services.storage
Deprecated: 2025-12-07
Migration Phase: 4

This file is kept for reference only. All new code should use the replacement.

To migrate existing code, run:
    python manage.py migrate_to_core --apply

================================================================================
Manages file storage for generated book content
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from django.utils.text import slugify

logger = logging.getLogger(__name__)


class ContentStorageService:
    """
    Service for storing generated book content in organized directory structure

    Structure:
        ~/domains/
            {project-slug}/
                metadata.json
                outline.md
                chapters/
                    chapter_01.md
                    chapter_01_v1.md (versions)
                    chapter_02.md
                characters/
                    protagonist.json
                    antagonist.json
                assets/
                    cover.jpg
                exports/
                    book_v1.docx
                    book_v1.pdf
    """

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize storage service

        Args:
            base_path: Base directory for domains (default: ~/domains)
        """
        if base_path is None:
            self.base_path = Path.home() / "domains"
        else:
            self.base_path = Path(base_path)

        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"ContentStorageService initialized at {self.base_path}")

    def get_project_path(self, project_slug: str) -> Path:
        """Get the base path for a project"""
        project_path = self.base_path / project_slug
        project_path.mkdir(parents=True, exist_ok=True)
        return project_path

    def get_chapter_path(self, project_slug: str) -> Path:
        """Get the chapters directory for a project"""
        chapter_path = self.get_project_path(project_slug) / "chapters"
        chapter_path.mkdir(parents=True, exist_ok=True)
        return chapter_path

    def get_character_path(self, project_slug: str) -> Path:
        """Get the characters directory for a project"""
        character_path = self.get_project_path(project_slug) / "characters"
        character_path.mkdir(parents=True, exist_ok=True)
        return character_path

    def get_export_path(self, project_slug: str) -> Path:
        """Get the exports directory for a project"""
        export_path = self.get_project_path(project_slug) / "exports"
        export_path.mkdir(parents=True, exist_ok=True)
        return export_path

    def save_chapter(
        self,
        project_slug: str,
        chapter_number: int,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        format: str = "md",
        version: Optional[int] = None,
    ) -> Path:
        """
        Save chapter content to file

        Args:
            project_slug: Project identifier
            chapter_number: Chapter number
            content: Chapter content
            metadata: Optional metadata dict
            format: File format (md, txt, docx)
            version: Optional version number

        Returns:
            Path to saved file
        """
        chapter_path = self.get_chapter_path(project_slug)

        # Build filename
        filename_base = f"chapter_{chapter_number:02d}"
        if version:
            filename_base += f"_v{version}"
        filename = f"{filename_base}.{format}"

        file_path = chapter_path / filename

        # Prepare content with metadata header
        full_content = self._format_chapter_content(
            chapter_number=chapter_number, content=content, metadata=metadata, format=format
        )

        # Save file
        file_path.write_text(full_content, encoding="utf-8")
        logger.info(f"Saved chapter {chapter_number} to {file_path}")

        # Save metadata separately
        if metadata:
            metadata_path = chapter_path / f"{filename_base}_metadata.json"
            metadata_path.write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")

        return file_path

    def save_outline(self, project_slug: str, outline: Dict[str, Any], format: str = "md") -> Path:
        """
        Save project outline

        Args:
            project_slug: Project identifier
            outline: Outline data
            format: File format

        Returns:
            Path to saved file
        """
        project_path = self.get_project_path(project_slug)
        file_path = project_path / f"outline.{format}"

        if format == "md":
            content = self._format_outline_markdown(outline)
        else:
            content = json.dumps(outline, indent=2, default=str)

        file_path.write_text(content, encoding="utf-8")
        logger.info(f"Saved outline to {file_path}")

        return file_path

    def save_character(
        self, project_slug: str, character_name: str, character_data: Dict[str, Any]
    ) -> Path:
        """
        Save character data

        Args:
            project_slug: Project identifier
            character_name: Character name
            character_data: Character data dict

        Returns:
            Path to saved file
        """
        character_path = self.get_character_path(project_slug)
        filename = f"{slugify(character_name)}.json"
        file_path = character_path / filename

        character_data["saved_at"] = datetime.now().isoformat()

        file_path.write_text(json.dumps(character_data, indent=2, default=str), encoding="utf-8")
        logger.info(f"Saved character '{character_name}' to {file_path}")

        return file_path

    def save_metadata(self, project_slug: str, metadata: Dict[str, Any]) -> Path:
        """
        Save project metadata

        Args:
            project_slug: Project identifier
            metadata: Metadata dict

        Returns:
            Path to saved file
        """
        project_path = self.get_project_path(project_slug)
        file_path = project_path / "metadata.json"

        metadata["last_updated"] = datetime.now().isoformat()

        file_path.write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
        logger.info(f"Saved metadata to {file_path}")

        return file_path

    def _format_chapter_content(
        self, chapter_number: int, content: str, metadata: Optional[Dict[str, Any]], format: str
    ) -> str:
        """Format chapter content with metadata header"""
        if format == "md":
            header = f"# Chapter {chapter_number}\n\n"
            if metadata:
                header += "## Metadata\n\n"
                for key, value in metadata.items():
                    header += f"- **{key}:** {value}\n"
                header += "\n---\n\n"
            return header + content
        else:
            return content

    def _format_outline_markdown(self, outline: Dict[str, Any]) -> str:
        """Format outline data as markdown"""
        md = f"# {outline.get('title', 'Book Outline')}\n\n"

        if "chapters" in outline:
            md += "## Chapters\n\n"
            for chapter in outline["chapters"]:
                md += f"### Chapter {chapter.get('number', '?')}: {chapter.get('title', 'Untitled')}\n\n"
                if "summary" in chapter:
                    md += f"{chapter['summary']}\n\n"

        return md

    def list_chapters(self, project_slug: str) -> list:
        """List all chapters for a project"""
        chapter_path = self.get_chapter_path(project_slug)
        chapters = sorted(chapter_path.glob("chapter_*.md"))
        return chapters

    def get_project_stats(self, project_slug: str) -> Dict[str, Any]:
        """Get statistics for a project"""
        project_path = self.get_project_path(project_slug)

        if not project_path.exists():
            return {"exists": False}

        chapter_path = self.get_chapter_path(project_slug)
        character_path = self.get_character_path(project_slug)

        chapters = list(chapter_path.glob("chapter_*.md"))
        characters = list(character_path.glob("*.json"))

        total_words = 0
        for chapter in chapters:
            content = chapter.read_text(encoding="utf-8")
            total_words += len(content.split())

        return {
            "exists": True,
            "path": str(project_path),
            "chapter_count": len(chapters),
            "character_count": len(characters),
            "total_words": total_words,
        }
