"""
Repository layer for persisting novels and story data.
Uses JSON files for simplicity - easily extensible to SQLite.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..models.core import Novel


class NovelRepository:
    """Repository for storing and retrieving novels."""

    def __init__(self, storage_dir: str | Path = "~/.story-outline"):
        """Initialize repository with storage directory."""
        self.storage_dir = Path(storage_dir).expanduser()
        self.novels_dir = self.storage_dir / "novels"
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create storage directories if they don't exist."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.novels_dir.mkdir(parents=True, exist_ok=True)

    def _novel_path(self, novel_id: str) -> Path:
        """Get the file path for a novel."""
        return self.novels_dir / f"{novel_id}.json"

    def save(self, novel: Novel) -> None:
        """Save a novel to disk."""
        novel.updated_at = datetime.now()
        path = self._novel_path(novel.id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(novel.model_dump(mode="json"), f, indent=2, ensure_ascii=False, default=str)

    def load(self, novel_id: str) -> Optional[Novel]:
        """Load a novel by ID."""
        path = self._novel_path(novel_id)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Novel.model_validate(data)

    def delete(self, novel_id: str) -> bool:
        """Delete a novel by ID."""
        path = self._novel_path(novel_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_all(self) -> list[dict]:
        """List all novels (basic info only)."""
        novels = []
        for path in self.novels_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                novels.append(
                    {
                        "id": data.get("id"),
                        "title": data.get("title"),
                        "author": data.get("author", ""),
                        "genre": data.get("genre", ""),
                        "updated_at": data.get("updated_at"),
                        "word_count_target": data.get("target_word_count", 0),
                    }
                )
            except (json.JSONDecodeError, KeyError):
                continue
        return sorted(novels, key=lambda x: x.get("updated_at", ""), reverse=True)

    def exists(self, novel_id: str) -> bool:
        """Check if a novel exists."""
        return self._novel_path(novel_id).exists()

    def export_to_json(self, novel_id: str, output_path: str | Path) -> bool:
        """Export a novel to a specific JSON file."""
        novel = self.load(novel_id)
        if not novel:
            return False
        output = Path(output_path)
        with open(output, "w", encoding="utf-8") as f:
            json.dump(novel.model_dump(mode="json"), f, indent=2, ensure_ascii=False, default=str)
        return True

    def import_from_json(self, input_path: str | Path) -> Optional[Novel]:
        """Import a novel from a JSON file."""
        path = Path(input_path)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        novel = Novel.model_validate(data)
        self.save(novel)
        return novel


class BackupManager:
    """Manages backups and version history."""

    def __init__(self, storage_dir: str | Path = "~/.story-outline"):
        self.storage_dir = Path(storage_dir).expanduser()
        self.backup_dir = self.storage_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, novel: Novel) -> Path:
        """Create a timestamped backup of a novel."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{novel.id}_{timestamp}.json"
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(novel.model_dump(mode="json"), f, indent=2, ensure_ascii=False, default=str)
        return backup_path

    def list_backups(self, novel_id: str) -> list[Path]:
        """List all backups for a novel."""
        return sorted(
            self.backup_dir.glob(f"{novel_id}_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

    def restore_backup(self, backup_path: Path) -> Optional[Novel]:
        """Restore a novel from a backup file."""
        if not backup_path.exists():
            return None
        with open(backup_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Novel.model_validate(data)
