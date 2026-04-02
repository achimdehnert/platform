# tests/contracts/conftest.py
"""
Contract-Test Konfiguration.

Fix H3: pytest.mark.contract muss registriert sein, sonst:
  - PytestUnknownMarkWarning bei default settings
  - Fehler bei --strict-markers (empfohlen für CI)

Diese Datei gehört in JEDES Hub-Repo das Contract-Tests hat.
Alternativ: in pyproject.toml unter [tool.pytest.ini_options] markers registrieren
(dann ist diese conftest.py nicht nötig — aber explizit ist besser).
"""
import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Registriert plattformweite pytest-Marker."""
    config.addinivalue_line(
        "markers",
        "contract: Contract-Tests — prüfen Signaturen, Exceptions und Shapes an "
        "Aufrufgrenzen (Package-APIs, Service-Layer, Celery Tasks, REST). "
        "ADR-155. Läuft in test-contract CI-Job.",
    )
