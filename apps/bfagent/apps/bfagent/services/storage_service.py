"""
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
"""

"""
Storage Service
===============

Handles file storage operations for chapters and other content.

Author: BF Agent Framework
Date: 2025-11-03
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class StorageService:
    """
    Service for handling file storage operations

    Manages saving and retrieving chapter content, markdown files, etc.
    """

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize storage service

        Args:
            base_path: Base path for storage (defaults to 'generated_content/')
        """
        self.base_path = base_path or "generated_content"
        logger.info(f"StorageService initialized with base_path: {self.base_path}")

    def save_chapter(
        self, project_slug: str, chapter_number: int, content: str, filename: Optional[str] = None
    ) -> str:
        """
        Save chapter content to file

        Args:
            project_slug: Slugified project title
            chapter_number: Chapter number
            content: Chapter content to save
            filename: Optional custom filename

        Returns:
            Path to saved file
        """
        # Create directory structure
        project_dir = Path(self.base_path) / project_slug / "chapters"
        project_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        if not filename:
            filename = f"chapter_{chapter_number}.md"

        # Save file
        file_path = project_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Saved chapter to: {file_path}")
        return str(file_path)

    def load_chapter(
        self, project_slug: str, chapter_number: int, filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Load chapter content from file

        Args:
            project_slug: Slugified project title
            chapter_number: Chapter number
            filename: Optional custom filename

        Returns:
            Chapter content or None if not found
        """
        # Generate filename
        if not filename:
            filename = f"chapter_{chapter_number}.md"

        # Load file
        file_path = Path(self.base_path) / project_slug / "chapters" / filename

        if not file_path.exists():
            logger.warning(f"Chapter file not found: {file_path}")
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        logger.info(f"Loaded chapter from: {file_path}")
        return content

    def chapter_exists(
        self, project_slug: str, chapter_number: int, filename: Optional[str] = None
    ) -> bool:
        """
        Check if chapter file exists

        Args:
            project_slug: Slugified project title
            chapter_number: Chapter number
            filename: Optional custom filename

        Returns:
            True if file exists
        """
        if not filename:
            filename = f"chapter_{chapter_number}.md"

        file_path = Path(self.base_path) / project_slug / "chapters" / filename
        return file_path.exists()

    def delete_chapter(
        self, project_slug: str, chapter_number: int, filename: Optional[str] = None
    ) -> bool:
        """
        Delete chapter file

        Args:
            project_slug: Slugified project title
            chapter_number: Chapter number
            filename: Optional custom filename

        Returns:
            True if deleted successfully
        """
        if not filename:
            filename = f"chapter_{chapter_number}.md"

        file_path = Path(self.base_path) / project_slug / "chapters" / filename

        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted chapter file: {file_path}")
            return True

        return False
