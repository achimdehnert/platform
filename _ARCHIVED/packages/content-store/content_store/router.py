"""Database router for content_store (ADR-130).

Routes all content_store models to the dedicated 'content_store'
database connection defined in DATABASES settings.
"""

from __future__ import annotations


class ContentStoreRouter:
    """Routet content_store Models an die dedizierte DB-Verbindung."""

    APP_LABEL = "content_store"

    def db_for_read(self, model, **hints):
        if model._meta.app_label == self.APP_LABEL:
            return "content_store"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == self.APP_LABEL:
            return "content_store"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if (
            obj1._meta.app_label == self.APP_LABEL
            or obj2._meta.app_label == self.APP_LABEL
        ):
            return obj1._meta.app_label == obj2._meta.app_label
        return None

    def allow_migrate(self, db, app_label, **hints):
        if app_label == self.APP_LABEL:
            return db == "content_store"
        if db == "content_store":
            return False
        return None
