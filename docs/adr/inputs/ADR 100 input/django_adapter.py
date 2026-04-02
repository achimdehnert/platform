"""
outlinefw/src/outlinefw/django_adapter.py

Fixes BLOCKER B-3: "Host-App überschreibt Stubs" ist kein sicheres API-Muster.

Korrekte Implementierung: Abstrakte Basisklasse (ABC) mit definierten Contracts.
Host-Apps subclassen OutlineServiceBase und implementieren die abstrakten Methoden.

Warum ABC statt Stubs:
  - Stubs werden bei falscher Nutzung zur Laufzeit still übergangen
  - ABC erzwingt Implementierung bei Instanziierung (TypeError sonst)
  - Mypy und IDEs erkennen das Interface korrekt
  - Testbar via Mock-Subklassen ohne Django-Setup

Django-Adapter-Verantwortlichkeiten:
  - Outline persistieren (Host-App definiert das Modell)
  - Tenant-Kontext bereitstellen (Platform Standard: tenant_id)
  - LLMRouter aus iil-aifw instantiieren
  - Caching-Entscheidungen (Host-App entscheidet)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from outlinefw.generator import OutlineGenerator, LLMQuality
from outlinefw.schemas import OutlineResult, ProjectContext


class OutlineServiceBase(ABC):
    """
    Abstract base class for Host-App outline service implementations.

    Subclass this in your Django app's service layer:

        # writing-hub/apps/authoring/services/outline_service.py
        from outlinefw.django_adapter import OutlineServiceBase

        class WritingHubOutlineService(OutlineServiceBase):
            def get_tenant_id(self, request) -> int:
                return request.tenant.id

            def persist_outline(self, result, context, tenant_id) -> Any:
                from apps.outlines.models import Outline
                return Outline.objects.create(
                    tenant_id=tenant_id,
                    framework_key=result.framework_key,
                    title=context.title,
                    nodes_json=[n.model_dump() for n in result.nodes],
                )

            def get_llm_router(self, tenant_id: int):
                from aifw.routing import get_router
                return get_router(tenant_id=tenant_id)
    """

    @abstractmethod
    def get_tenant_id(self, request: Any) -> int:
        """
        Extract tenant_id from the current request context.
        Platform standard: tenant_id is BigIntegerField — must return int.
        """
        ...

    @abstractmethod
    def persist_outline(
        self,
        result: OutlineResult,
        context: ProjectContext,
        tenant_id: int,
    ) -> Any:
        """
        Persist the generated outline to the Host-App's storage.
        Returns the created model instance (or None if not applicable).

        MUST NOT be called if result.success is False.
        Service caller is responsible for checking result.success.
        """
        ...

    @abstractmethod
    def get_llm_router(self, tenant_id: int) -> Any:
        """
        Return a configured LLMRouter for the given tenant.
        Must return an object implementing the LLMRouter Protocol.
        """
        ...

    def generate_and_persist(
        self,
        framework_key: str,
        context: ProjectContext,
        request: Any,
        quality: LLMQuality = LLMQuality.STANDARD,
    ) -> OutlineResult:
        """
        Template method: generate outline + optionally persist.

        This method is provided — subclasses only implement the 3 abstract methods.
        Business logic stays in service layer per Platform Standard.
        """
        tenant_id = self.get_tenant_id(request)
        router = self.get_llm_router(tenant_id)
        generator = OutlineGenerator(router=router)

        result = generator.generate(
            framework_key=framework_key,
            context=context,
            quality=quality,
        )

        if result.success:
            self.persist_outline(result, context, tenant_id)

        return result


class InMemoryOutlineService(OutlineServiceBase):
    """
    Concrete implementation for testing — no Django required.

    Usage in tests:
        service = InMemoryOutlineService(router=MockLLMRouter(), tenant_id=1)
        result = service.generate_and_persist("three_act", context, request=None)
    """

    def __init__(self, router: Any, tenant_id: int = 1) -> None:
        self._router = router
        self._tenant_id = tenant_id
        self.persisted: list[dict[str, Any]] = []

    def get_tenant_id(self, request: Any) -> int:
        return self._tenant_id

    def persist_outline(
        self,
        result: OutlineResult,
        context: ProjectContext,
        tenant_id: int,
    ) -> dict[str, Any]:
        record = {
            "framework_key": result.framework_key,
            "title": context.title,
            "tenant_id": tenant_id,
            "nodes": [n.model_dump() for n in result.nodes],
        }
        self.persisted.append(record)
        return record

    def get_llm_router(self, tenant_id: int) -> Any:
        return self._router
