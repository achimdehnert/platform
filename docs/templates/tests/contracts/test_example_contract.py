"""
tests/contracts/test_example_contract.py — Referenz-Contract-Test Template.

Kopiere diese Datei in dein Hub-Repo und passe sie an deine Adapter an.
Zeigt alle 5 Verifier-Typen aus ADR-155.

ADR: ADR-155
"""
from __future__ import annotations

from typing import Any

import pytest

# ── 1. Package-API Contract ──────────────────────────────────────────────────
# Beispiel: Hub nutzt outlinefw.OutlineGenerator

# from outlinefw import OutlineGenerator  # noqa: ERA001
# from iil_testkit.contract import ContractVerifier


@pytest.mark.contract
class TestOutlineGeneratorContract:
    """Contract-Tests für outlinefw.OutlineGenerator API."""

    @pytest.fixture
    def verifier(self):
        # TODO: Ersetze DummyClass durch die echte Provider-Klasse
        from iil_testkit.contract import ContractVerifier

        class DummyOutlineGenerator:
            def __init__(self, router: object) -> None: ...
            def generate(self, framework_key: str, context: dict) -> dict[str, Any]: ...

        return ContractVerifier(DummyOutlineGenerator)

    def test_should_have_init_params(self, verifier) -> None:
        verifier.assert_init_params(["router"])

    def test_should_have_generate_method(self, verifier) -> None:
        verifier.assert_method_exists("generate")

    def test_should_have_correct_generate_params(self, verifier) -> None:
        verifier.assert_method_params("generate", ["framework_key", "context"])

    def test_should_not_use_old_param_name(self, verifier) -> None:
        """Regression: alter Parameter 'template_key' wurde zu 'framework_key' umbenannt."""
        verifier.assert_no_param("generate", "template_key")

    def test_should_return_dict(self, verifier) -> None:
        verifier.assert_return_origin("generate", dict)


# ── 2. Service-Layer Contract ────────────────────────────────────────────────

@pytest.mark.contract
class TestDocumentServiceContract:
    """Contract-Tests für einen internen Service-Layer."""

    @pytest.fixture
    def verifier(self):
        from iil_testkit.contract import ContractVerifier

        class DummyDocumentService:
            def upload(self, file_path: str, *, tenant_id: int) -> dict[str, Any]:
                """Lädt ein Dokument hoch.

                Returns:
                    Dict mit Keys: document_id, status, url

                :raises ValueError: Wenn file_path leer.
                :raises FileNotFoundError: Wenn Datei nicht existiert.
                """
                ...

        return ContractVerifier(DummyDocumentService)

    def test_should_have_upload_params(self, verifier) -> None:
        verifier.assert_method_params("upload", ["file_path", "tenant_id"])

    def test_should_document_exceptions(self, verifier) -> None:
        verifier.assert_raises("upload", [ValueError, FileNotFoundError])

    def test_should_document_return_keys(self, verifier) -> None:
        verifier.assert_return_keys("upload", ["document_id", "status", "url"])


# ── 3. Celery Task Contract ──────────────────────────────────────────────────

@pytest.mark.contract
class TestCeleryTaskContract:
    """Contract-Tests für einen Celery Task."""

    @pytest.fixture
    def verifier(self):
        from iil_testkit.contract import ContractVerifier

        class DummyTask:
            name = "app.tasks.process_document"
            acks_late = True

            def run(self, document_id: int, *, force: bool = False) -> str: ...

        return ContractVerifier.for_task(DummyTask())

    def test_should_have_correct_params(self, verifier) -> None:
        verifier.assert_params(["document_id"])

    def test_should_not_use_old_param_name(self, verifier) -> None:
        verifier.assert_no_param("doc_id")

    def test_should_be_acks_late(self, verifier) -> None:
        verifier.assert_is_acks_late()


# ── 4. Freie Funktion Contract ───────────────────────────────────────────────

@pytest.mark.contract
class TestFreeFunctionContract:
    """Contract-Tests für eine freistehende Funktion."""

    @pytest.fixture
    def verifier(self):
        from iil_testkit.contract import ContractVerifier

        def analyze_cv_with_llm(cv_text: str, *, quality: str = "standard") -> dict[str, Any]: ...

        return ContractVerifier.for_callable(analyze_cv_with_llm)

    def test_should_have_correct_params(self, verifier) -> None:
        verifier.assert_params(["cv_text"])

    def test_should_return_dict(self, verifier) -> None:
        verifier.assert_return_annotation(dict[str, Any])


# ── 5. REST Response Shape Contract ──────────────────────────────────────────

@pytest.mark.contract
class TestRestResponseContract:
    """Contract-Tests für REST API Response-Shapes."""

    @pytest.fixture
    def verifier(self):
        from iil_testkit.contract import ResponseShapeVerifier

        return ResponseShapeVerifier({
            "fit_score": float,
            "skills": list,
            "summary": str,
        })

    def test_should_have_expected_keys(self, verifier) -> None:
        verifier.assert_response({
            "fit_score": 0.85,
            "skills": ["Python", "Django"],
            "summary": "Guter Kandidat",
            "extra_field": True,  # Extra-Keys sind erlaubt
        })

    def test_should_have_correct_types(self, verifier) -> None:
        verifier.assert_response_types({
            "fit_score": 0.85,
            "skills": ["Python"],
            "summary": "Test",
        })
