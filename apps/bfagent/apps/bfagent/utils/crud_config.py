"""
CRUDConfig System for BF Agent
Meta-programming approach for Zero-Hardcoding CRUD operations
"""

from typing import Any, Dict, List, Optional

from django.db import models


class CRUDConfigMixin:
    """Mixin to add CRUDConfig support to models"""

    @classmethod
    def get_crud_config(cls) -> "CRUDConfigBase":
        """Get CRUDConfig for this model, with fallback defaults"""
        if hasattr(cls, "CRUDConfig"):
            return cls.CRUDConfig()
        return DefaultCRUDConfig(cls)


class CRUDConfigBase:
    """Base class for CRUD configuration"""

    def __init__(self, model_class=None):
        self.model_class = model_class

    # List View Configuration
    list_display: List[str] = []
    list_filters: List[str] = []
    search_fields: List[str] = []
    ordering: List[str] = ["-created_at"]
    per_page: int = 20

    # Form Configuration
    form_layout: Dict[str, List[str]] = {}
    form_fields: str = "__all__"
    exclude_fields: List[str] = []

    # HTMX Configuration
    htmx_config: Dict[str, Any] = {
        "auto_save": False,
        "inline_edit": [],
        "modal_edit": [],
        "live_search": True,
        "pagination_htmx": True,
        "loading_indicators": True,
    }

    # Action Buttons
    actions: Dict[str, Dict[str, Any]] = {}

    # UI Configuration
    ui_config: Dict[str, Any] = {
        "card_view": True,
        "table_view": True,
        "default_view": "card",
        "show_stats": True,
        "show_filters": True,
    }

    def get_list_display(self) -> List[str]:
        """Get fields to display in list view"""
        if self.list_display:
            return self.list_display
        # Fallback: first 5 non-relation fields
        if self.model_class:
            fields = [
                f.name
                for f in self.model_class._meta.fields
                if not f.name.endswith("_ptr") and not isinstance(f, models.ForeignKey)
            ]
            return fields[:5]
        return []

    def get_search_fields(self) -> List[str]:
        """Get fields for search functionality"""
        if self.search_fields:
            return self.search_fields
        # Fallback: text fields
        if self.model_class:
            text_fields = []
            for field in self.model_class._meta.fields:
                if isinstance(field, (models.CharField, models.TextField)):
                    text_fields.append(field.name)
            return text_fields[:3]
        return []

    def get_form_layout(self) -> Dict[str, List[str]]:
        """Get form layout configuration"""
        if self.form_layout:
            return self.form_layout
        # Fallback: single section with all fields
        if self.model_class:
            all_fields = [
                f.name
                for f in self.model_class._meta.fields
                if f.name not in self.exclude_fields and not f.name.endswith("_ptr")
            ]
            return {"General": all_fields}
        return {}


class DefaultCRUDConfig(CRUDConfigBase):
    """Default CRUD configuration for models without explicit CRUDConfig"""

    def __init__(self, model_class):
        super().__init__(model_class)
        self.list_display = self.get_list_display()
        self.search_fields = self.get_search_fields()
        self.form_layout = self.get_form_layout()


# Theme System
class BFAgentTheme:
    """Central theme configuration for BF Agent"""

    STATUS_COLORS = {
        "draft": "yellow",
        "in_progress": "blue",
        "review": "orange",
        "completed": "green",
        "published": "emerald",
        "archived": "gray",
        "active": "green",
        "inactive": "red",
        "testing": "purple",
    }

    GENRE_COLORS = {
        "fiction": "blue",
        "non-fiction": "green",
        "science-fiction": "purple",
        "fantasy": "pink",
        "mystery": "indigo",
        "romance": "rose",
        "thriller": "red",
        "historical": "amber",
    }

    ICONS = {
        # Status Icons
        "draft": "pencil",
        "in_progress": "clock",
        "review": "eye",
        "completed": "check-circle",
        "published": "globe",
        "archived": "archive",
        # Action Icons
        "edit": "pencil",
        "delete": "trash",
        "view": "eye",
        "duplicate": "copy",
        "export": "download",
        "share": "share",
        # Entity Icons
        "book": "book-open",
        "chapter": "document-text",
        "character": "user",
        "agent": "cpu-chip",
        "world": "globe-alt",
    }

    @classmethod
    def get_status_color(cls, status: str) -> str:
        """Get color for status"""
        return cls.STATUS_COLORS.get(status, "gray")

    @classmethod
    def get_genre_color(cls, genre: str) -> str:
        """Get color for genre"""
        return cls.GENRE_COLORS.get(genre, "blue")

    @classmethod
    def get_icon(cls, icon_type: str) -> str:
        """Get icon for type"""
        return cls.ICONS.get(icon_type, "question-mark-circle")

    @classmethod
    def get_card_classes(cls, obj, base_classes: str = "") -> str:
        """Generate dynamic CSS classes for cards"""
        classes = f"card shadow-sm hover:shadow-md transition-all {base_classes}".strip()

        # Status-based styling
        if hasattr(obj, "status"):
            color = cls.get_status_color(obj.status)
            classes += f" border-l-4 border-{color}-500"

            if obj.status == "archived":
                classes += " opacity-60"
            elif obj.status == "draft":
                classes += " bg-yellow-50"

        # Genre-based styling
        if hasattr(obj, "genre"):
            color = cls.get_genre_color(obj.genre)
            classes += f" hover:border-{color}-300"

        return classes

    @classmethod
    def get_badge_classes(cls, status: str) -> str:
        """Get badge classes for status"""
        color = cls.get_status_color(status)
        return f"badge bg-{color}-100 text-{color}-800 border border-{color}-200"
