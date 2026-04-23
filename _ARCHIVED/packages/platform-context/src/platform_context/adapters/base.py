"""
platform_context/adapters/base.py

ApiAdapter-Basisklasse für alle Hub ↔ iil-Package Adapter.

Erzwingt explizites Parameter-Mapping — kein blindes **kwargs-Forwarding.

Anti-Pattern (verboten — ADR-155 §4.3):
    def completion(self, messages, **kwargs):
        return self._router.completion(messages=messages, **kwargs)  # ❌

Korrekt:
    def completion(
        self,
        messages: list[dict[str, str]],
        quality: Quality = Quality.STANDARD,
    ) -> str:
        return self._router.completion(
            messages=messages,
            quality_level=quality.value,   # Consumer → Provider Mapping
        )

Adapter-Konvention:
    Jede Methode MUSS einen Mapping-Kommentar haben wenn Consumer-
    und Provider-Parameternamen abweichen:

        router_kwargs["quality_level"] = quality.value  # Consumer "quality" → Provider "quality_level"

ADR: ADR-155
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class ApiAdapter(ABC):
    """Basisklasse für alle Adapter zwischen Hub und iil-Package.

    Subklassen MÜSSEN:
    1. Alle Provider-Parameter explizit in der Methodensignatur benennen
    2. Kein **kwargs an Provider-Calls durchreichen
    3. Parameter-Mapping in der Methode mit Kommentar dokumentieren:
         # Consumer '<name>' → Provider '<name>'
    4. Von dieser Basisklasse erben

    Subklassen DÜRFEN NICHT:
    - **kwargs aus Consumer-Calls blind an Provider weiterreichen
    - Provider-Parameternamen direkt dem Consumer exponieren (Leaky Abstraction)
    - Provider-Imports im Consumer-Code (nur über Adapter)
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name des Provider-Packages (für Logging und Fehler-Messages).

        Beispiel: return "outlinefw"
        """
        ...

    def _log_call(self, method: str, **consumer_params: Any) -> None:
        """Debug-Logging für alle Adapter-Aufrufe.

        Wird in jeder Adapter-Methode am Anfang aufgerufen.
        Nur bei logging.DEBUG aktiv — kein Performance-Impact in Production.
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "ApiAdapter.%s → %s",
                method,
                self.provider_name,
                extra={
                    "adapter": type(self).__name__,
                    "provider": self.provider_name,
                    "method": method,
                    "consumer_params": sorted(consumer_params.keys()),
                },
            )

    def _log_provider_error(
        self,
        method: str,
        error: Exception,
        **consumer_params: Any,
    ) -> None:
        """Error-Logging wenn der Provider einen Fehler wirft."""
        logger.error(
            "ApiAdapter.%s → %s failed: %s: %s",
            method,
            self.provider_name,
            type(error).__name__,
            str(error),
            extra={
                "adapter": type(self).__name__,
                "provider": self.provider_name,
                "method": method,
                "consumer_params": sorted(consumer_params.keys()),
                "error_type": type(error).__name__,
            },
            exc_info=True,
        )
