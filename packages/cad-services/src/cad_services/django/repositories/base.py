"""
Base Repository Pattern
ADR-009: Separation of Concerns - Generic CRUD operations
"""

from typing import Generic, TypeVar

from django.db import models
from django.db.models import QuerySet


T = TypeVar("T", bound=models.Model)


class BaseRepository(Generic[T]):
    """
    Generic repository for CRUD operations.
    Database-driven, tenant-aware queries.
    """

    model_class: type[T]

    def __init__(self, tenant_id: int | None = None):
        self.tenant_id = tenant_id

    def get_queryset(self) -> QuerySet[T]:
        qs = self.model_class.objects.all()
        if self.tenant_id and hasattr(self.model_class, "tenant_id"):
            qs = qs.filter(tenant_id=self.tenant_id)
        return qs

    def get_by_id(self, pk: int) -> T | None:
        try:
            return self.get_queryset().get(pk=pk)
        except self.model_class.DoesNotExist:
            return None

    def get_all(self) -> QuerySet[T]:
        return self.get_queryset()

    def create(self, **kwargs) -> T:
        if self.tenant_id and hasattr(self.model_class, "tenant_id"):
            kwargs["tenant_id"] = self.tenant_id
        return self.model_class.objects.create(**kwargs)

    def update(self, pk: int, **kwargs) -> T | None:
        obj = self.get_by_id(pk)
        if obj:
            for key, value in kwargs.items():
                setattr(obj, key, value)
            obj.save()
        return obj

    def delete(self, pk: int) -> bool:
        obj = self.get_by_id(pk)
        if obj:
            obj.delete()
            return True
        return False

    def count(self) -> int:
        return self.get_queryset().count()

    def exists(self, pk: int) -> bool:
        return self.get_queryset().filter(pk=pk).exists()
