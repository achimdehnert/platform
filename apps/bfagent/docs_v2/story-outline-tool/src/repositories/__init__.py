"""Repositories package - Data persistence."""

from .novel_repository import BackupManager, NovelRepository

__all__ = ["NovelRepository", "BackupManager"]
