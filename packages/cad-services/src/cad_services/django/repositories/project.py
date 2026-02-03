"""
Project Repository
ADR-009: Data access layer for Project operations
"""

from django.db.models import Count, QuerySet, Sum

from cad_services.django.models.cadhub import Model, Project
from cad_services.django.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    """Repository for Project CRUD and queries."""

    model_class = Project

    def __init__(self, tenant_id: int):
        super().__init__(tenant_id)

    def get_active(self) -> QuerySet[Project]:
        return self.get_queryset().filter(status="active")

    def get_with_stats(self) -> QuerySet[Project]:
        return (
            self.get_queryset()
            .annotate(
                model_count=Count("models"),
                total_size=Sum("models__file_size_bytes"),
            )
            .order_by("-created_at")
        )

    def get_by_name(self, name: str) -> Project | None:
        try:
            return self.get_queryset().get(name=name)
        except Project.DoesNotExist:
            return None

    def archive(self, project_id: int) -> Project | None:
        return self.update(project_id, status="archived")

    def restore(self, project_id: int) -> Project | None:
        return self.update(project_id, status="active")


class ModelRepository(BaseRepository[Model]):
    """Repository for Model (IFC/DXF file) operations."""

    model_class = Model

    def __init__(self, project_id: int):
        self.project_id = project_id
        super().__init__()

    def get_queryset(self) -> QuerySet[Model]:
        return Model.objects.filter(project_id=self.project_id)

    def get_by_status(self, status: str) -> QuerySet[Model]:
        return self.get_queryset().filter(parse_status=status)

    def get_pending(self) -> QuerySet[Model]:
        return self.get_by_status("pending")

    def get_completed(self) -> QuerySet[Model]:
        return self.get_by_status("completed")

    def mark_parsing(self, model_id: int) -> Model | None:
        return self.update(model_id, parse_status="parsing")

    def mark_completed(self, model_id: int) -> Model | None:
        from django.utils import timezone

        return self.update(
            model_id,
            parse_status="completed",
            parsed_at=timezone.now(),
        )

    def mark_failed(self, model_id: int, error: str) -> Model | None:
        return self.update(
            model_id,
            parse_status="failed",
            parse_error=error,
        )
