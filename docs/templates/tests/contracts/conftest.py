"""
tests/contracts/conftest.py — Contract-Test Marker Registration.

Kopiere diese Datei nach tests/contracts/conftest.py in deinem Hub-Repo.
Registriert den pytest-Marker 'contract' damit pytest keine Warnings wirft.

ADR: ADR-155
"""
import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "contract: Contract-Tests für API-Signaturen und Adapter (ADR-155)",
    )
