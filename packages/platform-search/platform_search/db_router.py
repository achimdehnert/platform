"""Database router for platform-search (ADR-062, ADR-087).

Routes platform_search migrations to the content_store database.
Add 'platform_search.db_router.SearchRouter' to DATABASE_ROUTERS.
"""

from __future__ import annotations

from typing import Any


class SearchRouter:
    """Route platform_search app to content_store database."""

    APP_LABEL = "platform_search"
    DB_NAME = "content_store"

    def db_for_read(
        self, model: type, **hints: Any
    ) -> str | None:
        if model._meta.app_label == self.APP_LABEL:
            return self.DB_NAME
        return None

    def db_for_write(
        self, model: type, **hints: Any
    ) -> str | None:
        if model._meta.app_label == self.APP_LABEL:
            return self.DB_NAME
        return None

    def allow_relation(
        self, obj1: Any, obj2: Any, **hints: Any
    ) -> bool | None:
        return None

    def allow_migrate(
        self,
        db: str,
        app_label: str,
        model_name: str | None = None,
        **hints: Any,
    ) -> bool | None:
        if app_label == self.APP_LABEL:
            return db == self.DB_NAME
        return None
