"""
iil_testkit/contract/verifier.py

Platform-weiter Contract-Verifier für Funktions- und Methoden-Signaturen.

Unterstützt alle 5 Aufruftypen:
  1. Package-APIs:       ContractVerifier(OutlineGenerator)
  2. Service-Layer:      ContractVerifier(DocumentService)
  3. Celery Tasks:       ContractVerifier.for_task(analyze_document_task)
  4. Freie Funktionen:   ContractVerifier.for_callable(analyze_cv_with_llm)
  5. REST Schema:        ResponseShapeVerifier({"fit_score": float, ...})

Korrekturen gegenüber ADR-v2:
  - B1: assert_return_annotation: Generics-Bug gefixt — kein hasattr(__origin__) Short-Circuit
  - B2: assert_raises: warnings.warn → assert (war kein CI-Gate)
  - B3: assert_return_keys: warnings.warn → assert (war kein CI-Gate)
  - B4: TaskContractVerifier: getattr(task, "run", task) → korrekte Celery-Task-Introspection
  - K1: _assert_params: prüft jetzt auch neue Required-Params im Provider (bidirektional)
  - H3: conftest.py Inhalt dokumentiert
  - H4: __init__.py mit __all__ (siehe __init__.py)
  - M3: BaseContractVerifier Protocol als gemeinsame Basis

ADR: ADR-155
"""
from __future__ import annotations

import inspect
import warnings
from abc import ABC, abstractmethod
from typing import Any, Callable, TypeVar, get_type_hints

_T = TypeVar("_T")


# ══════════════════════════════════════════════════════════════════════════════
# Base Protocol — gemeinsame Basis für alle Verifier (Fix M3)
# ══════════════════════════════════════════════════════════════════════════════


class BaseContractVerifier(ABC):
    """Gemeinsame Basis für alle Contract-Verifier-Typen."""

    @abstractmethod
    def assert_params(self, expected: list[str]) -> None: ...

    @abstractmethod
    def assert_no_param(self, wrong_name: str) -> None: ...


# ══════════════════════════════════════════════════════════════════════════════
# ContractVerifier — für Klassen (Package-APIs, Service-Layer)
# ══════════════════════════════════════════════════════════════════════════════


class ContractVerifier(BaseContractVerifier):
    """Prüft API-Signaturen einer Klasse gegen Consumer-Erwartungen.

    Verwendung:
        verifier = ContractVerifier(OutlineGenerator)
        verifier.assert_init_params(["router"])
        verifier.assert_method_params("generate", ["framework_key", "context"])
        verifier.assert_no_param(OutlineGenerator.__init__, "llm_router")
        verifier.assert_enum_values(REGISTRY.keys(), ["essay", "report"])
    """

    def __init__(self, cls: type) -> None:
        if not inspect.isclass(cls):
            raise TypeError(
                f"ContractVerifier erwartet eine Klasse, got {type(cls).__name__}. "
                f"Für Funktionen: ContractVerifier.for_callable(fn). "
                f"Für Celery Tasks: ContractVerifier.for_task(task)."
            )
        self._cls = cls
        self._name = cls.__qualname__

    # ── Factory Methods ───────────────────────────────────────────────────────

    @classmethod
    def for_callable(cls, func: Callable[..., Any]) -> "CallableContractVerifier":
        """Erstellt einen Verifier für eine freistehende Funktion."""
        return CallableContractVerifier(func)

    @classmethod
    def for_task(cls, task: Any) -> "TaskContractVerifier":
        """Erstellt einen Verifier für einen Celery Task (alle Task-Typen)."""
        return TaskContractVerifier(task)

    # ── Signatur-Checks ───────────────────────────────────────────────────────

    def assert_init_params(
        self,
        expected: list[str],
        *,
        exhaustive: bool = False,
    ) -> None:
        """Prüft __init__-Parameternamen.

        Args:
            expected: Parameternamen die der Consumer erwartet.
            exhaustive: Wenn True, prüft auch ob der Provider neue Required-Params
                        hinzugefügt hat (bidirektionaler Contract — Fix K1).
        """
        self._assert_params(
            self._cls.__init__,
            expected,
            f"{self._name}.__init__",
            exhaustive=exhaustive,
        )

    def assert_method_params(
        self,
        method_name: str,
        expected: list[str],
        *,
        exhaustive: bool = False,
    ) -> None:
        """Prüft Parameternamen einer Methode.

        Args:
            method_name: Name der zu prüfenden Methode.
            expected: Parameternamen die der Consumer erwartet.
            exhaustive: Wenn True, prüft auch neue Required-Params im Provider (Fix K1).
        """
        method = self._get_method(method_name)
        self._assert_params(
            method,
            expected,
            f"{self._name}.{method_name}",
            exhaustive=exhaustive,
        )

    def assert_method_exists(self, method_name: str) -> None:
        """Prüft dass eine Methode existiert (nicht umbenannt/entfernt)."""
        assert hasattr(self._cls, method_name), (
            f"{self._name}: Methode '{method_name}' nicht gefunden. "
            f"Verfügbare public Methoden: "
            f"{[m for m in dir(self._cls) if not m.startswith('_')]}"
        )

    def assert_no_param(self, method: Callable[..., Any] | str, wrong_name: str) -> None:
        """Prüft dass ein bekannter Fehler-Parametername NICHT existiert.

        Args:
            method: Methoden-Objekt ODER Methoden-Name (string).
            wrong_name: Der falsche Parametername der nicht existieren darf.
        """
        if isinstance(method, str):
            method = self._get_method(method)
        sig = inspect.signature(method)
        params = set(sig.parameters.keys()) - {"self", "cls"}
        assert wrong_name not in params, (
            f"{method.__qualname__}: Parameter '{wrong_name}' sollte nicht existieren "
            f"(bekannter historischer Fehler-Alias). "
            f"Tatsächliche Parameter: {sorted(params)}"
        )

    # ── Enum / Registry-Checks ────────────────────────────────────────────────

    def assert_enum_values(
        self,
        actual_values: set[str] | list[str],
        expected_subset: list[str],
    ) -> None:
        """Prüft dass erwartete Werte in einem Registry/Enum vorhanden sind."""
        actual = set(actual_values)
        missing = set(expected_subset) - actual
        assert not missing, (
            f"{self._name}: Fehlende Werte in Registry/Enum: {sorted(missing)}. "
            f"Verfügbare Werte: {sorted(actual)}"
        )

    def assert_not_enum_value(
        self,
        actual_values: set[str] | list[str],
        wrong_value: str,
    ) -> None:
        """Prüft dass ein bekannter falscher Wert NICHT in der Registry ist."""
        actual = set(actual_values)
        assert wrong_value not in actual, (
            f"{self._name}: Falscher Wert '{wrong_value}' existiert in Registry — "
            f"versehentliche Umbenennung oder Consumer-Annahme falsch?"
        )

    # ── Exception-Contracts ───────────────────────────────────────────────────

    def assert_raises(
        self,
        method_name: str,
        expected_exceptions: list[type[BaseException]],
    ) -> None:
        """Prüft dass eine Service-Methode ihre Exceptions im Docstring deklariert.

        WICHTIG: Dies prüft die DEKLARATION (Docstring), nicht das Verhalten.
        Für Verhaltenstest: pytest.raises() in Integration-Tests nutzen.

        Docstring-Format (Sphinx/RST):
            :raises DocumentUploadError: Wenn Datei ungültig.

        Fix B2: Nutzt assert statt warnings.warn — Test schlägt fehl wenn
        Exception nicht dokumentiert ist.
        """
        method = self._get_method(method_name)
        docstring = inspect.getdoc(method) or ""

        for exc_type in expected_exceptions:
            exc_name = exc_type.__name__

            # Sanity-Check: ist es überhaupt eine Exception?
            assert inspect.isclass(exc_type) and issubclass(exc_type, BaseException), (
                f"{self._name}.{method_name}: {exc_name} ist keine Exception-Klasse"
            )

            # Fix B2: assert statt warnings.warn
            assert f":raises {exc_name}:" in docstring or f"Raises:" in docstring, (
                f"{self._name}.{method_name}: Exception '{exc_name}' nicht im Docstring "
                f"dokumentiert. Erwartet ':raises {exc_name}: <Beschreibung>' "
                f"oder Google-Style 'Raises:' Block.\n"
                f"Vorhandener Docstring: {docstring!r}"
            )

    # ── Return-Shape-Contracts ────────────────────────────────────────────────

    def assert_return_annotation(
        self,
        method_name: str,
        expected_type: type,
    ) -> None:
        """Prüft den Return-Typ-Annotation einer Methode.

        Fix B1: Kein hasattr(__origin__)-Short-Circuit mehr.
        Generische Typen werden explizit verglichen (dict[str,Any] ≠ list).

        Für generische Return-Types: assert_return_annotation_generic() nutzen.
        """
        method = self._get_method(method_name)

        # Nutze get_type_hints für aufgelöste Annotations (korrekt für from __future__ import annotations)
        try:
            hints = get_type_hints(method)
        except Exception:
            hints = {}

        annotation = hints.get("return", inspect.Parameter.empty)

        if annotation is inspect.Parameter.empty:
            # Fallback: direkte Signatur
            sig = inspect.signature(method)
            annotation = sig.return_annotation

        assert annotation is not inspect.Parameter.empty, (
            f"{self._name}.{method_name}: Keine Return-Annotation vorhanden. "
            f"iil-Packages müssen vollständig annotiert sein (PEP 561 / py.typed Standard)."
        )

        # Fix B1: Direkter Vergleich ohne __origin__-Short-Circuit
        assert annotation == expected_type, (
            f"{self._name}.{method_name}: Return-Typ {annotation!r} ≠ erwartet {expected_type!r}. "
            f"Consumer erwartet {expected_type.__name__ if hasattr(expected_type, '__name__') else expected_type!r}."
        )

    def assert_return_origin(self, method_name: str, expected_origin: type) -> None:
        """Prüft den Generic-Origin eines Return-Typs.

        Für generische Returns wie dict[str, Any], list[str], Optional[X].
        Beispiel: assert_return_origin("generate", dict)  # prüft ob Return dict[...] ist
        """
        method = self._get_method(method_name)
        try:
            hints = get_type_hints(method)
        except Exception:
            hints = {}
        annotation = hints.get("return", inspect.Parameter.empty)

        if annotation is inspect.Parameter.empty:
            sig = inspect.signature(method)
            annotation = sig.return_annotation

        assert annotation is not inspect.Parameter.empty, (
            f"{self._name}.{method_name}: Keine Return-Annotation vorhanden."
        )

        origin = getattr(annotation, "__origin__", annotation)
        assert origin is expected_origin, (
            f"{self._name}.{method_name}: Generic-Origin {origin!r} ≠ erwartet {expected_origin!r}."
        )

    def assert_return_keys(
        self,
        method_name: str,
        expected_keys: list[str],
    ) -> None:
        """Prüft Return-Key-Dokumentation im Docstring.

        Fix B3: assert statt warnings.warn.

        EMPFEHLUNG: TypedDict/Pydantic bevorzugen (§Alternative A im Review).
        Diese Methode ist ein Dokumentations-Gate — prüft ob Keys deklariert sind,
        nicht ob sie zur Laufzeit existieren.
        """
        method = self._get_method(method_name)
        docstring = inspect.getdoc(method) or ""

        missing_docs = [k for k in expected_keys if k not in docstring]

        # Fix B3: assert statt warnings.warn
        assert not missing_docs, (
            f"{self._name}.{method_name}: Return-Keys nicht im Docstring dokumentiert: "
            f"{missing_docs}. "
            f"Consumer erwartet diese Keys im Return-Dict. "
            f"Besser: TypedDict oder Pydantic-Model als Return-Type nutzen."
        )

    # ── Internes ──────────────────────────────────────────────────────────────

    def _get_method(self, method_name: str) -> Callable[..., Any]:
        assert hasattr(self._cls, method_name), (
            f"{self._name}: Methode '{method_name}' nicht gefunden. "
            f"Verfügbare Methoden: {[m for m in dir(self._cls) if not m.startswith('__')]}"
        )
        return getattr(self._cls, method_name)

    def _assert_params(
        self,
        func: Callable[..., Any],
        expected: list[str],
        label: str,
        *,
        exhaustive: bool = False,
    ) -> None:
        """Prüft Parameter-Übereinstimmung.

        Fix K1: exhaustive=True prüft BEIDE Richtungen:
          - Consumer erwartet Parameter die nicht existieren (bestehend)
          - Provider hat neue Required-Parameter die Consumer nicht kennt (NEU)
        """
        sig = inspect.signature(func)
        params = sig.parameters

        # Alle Parameter ohne self/cls
        actual = [
            name for name, p in params.items()
            if name not in ("self", "cls")
        ]

        # Richtung 1: Consumer erwartet Parameter die nicht existieren
        missing = [p for p in expected if p not in actual]
        assert not missing, (
            f"{label}: Consumer erwartet Parameter die nicht existieren: {missing}. "
            f"Tatsächliche Signatur: {actual}. "
            f"→ Parameternamen im Consumer anpassen."
        )

        # Richtung 2 (Fix K1): Provider hat neue Required-Params die Consumer nicht übergibt
        if exhaustive:
            required_in_provider = [
                name for name, p in params.items()
                if name not in ("self", "cls")
                and p.default is inspect.Parameter.empty
                and p.kind not in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                )
            ]
            unknown_required = [p for p in required_in_provider if p not in expected]
            assert not unknown_required, (
                f"{label}: Provider hat neue Required-Parameter die der Consumer nicht kennt: "
                f"{unknown_required}. "
                f"→ Consumer muss diese Parameter übergeben oder Contract aktualisieren."
            )

    # Alias für BaseContractVerifier-Protokoll
    def assert_params(self, expected: list[str]) -> None:
        """Alias für assert_init_params — BaseContractVerifier-Kompatibilität."""
        self.assert_init_params(expected)


# ══════════════════════════════════════════════════════════════════════════════
# CallableContractVerifier — für freistehende Funktionen
# ══════════════════════════════════════════════════════════════════════════════


class CallableContractVerifier(BaseContractVerifier):
    """Verifier für freistehende Funktionen (nicht Klassen-Methoden).

    Erstellt über: ContractVerifier.for_callable(my_function)
    """

    def __init__(self, func: Callable[..., Any]) -> None:
        if not callable(func):
            raise TypeError(
                f"CallableContractVerifier erwartet ein callable, got {type(func).__name__}."
            )
        self._func = func
        self._name = func.__qualname__

    def assert_params(self, expected: list[str]) -> None:
        """Prüft dass die Funktion die erwarteten Parameter hat."""
        sig = inspect.signature(self._func)
        actual = [p for p in sig.parameters.keys() if p not in ("self", "cls")]
        missing = [p for p in expected if p not in actual]
        assert not missing, (
            f"{self._name}(): Fehlende Parameter: {missing}. "
            f"Tatsächliche Signatur: {actual}."
        )

    def assert_no_param(self, wrong_name: str) -> None:
        """Prüft dass ein bekannter Fehler-Parametername NICHT existiert."""
        sig = inspect.signature(self._func)
        params = set(sig.parameters.keys()) - {"self", "cls"}
        assert wrong_name not in params, (
            f"{self._name}(): Parameter '{wrong_name}' sollte nicht existieren. "
            f"Tatsächliche Parameter: {sorted(params)}"
        )

    def assert_return_annotation(self, expected_type: type) -> None:
        """Prüft den Rückgabetyp."""
        try:
            hints = get_type_hints(self._func)
        except Exception:
            hints = {}
        annotation = hints.get("return", inspect.Parameter.empty)

        if annotation is inspect.Parameter.empty:
            sig = inspect.signature(self._func)
            annotation = sig.return_annotation

        assert annotation is not inspect.Parameter.empty, (
            f"{self._name}(): Keine Return-Annotation vorhanden."
        )
        # Kein __origin__-Short-Circuit (Fix B1)
        assert annotation == expected_type, (
            f"{self._name}(): Return-Typ {annotation!r} ≠ erwartet {expected_type!r}."
        )


# ══════════════════════════════════════════════════════════════════════════════
# TaskContractVerifier — für Celery Tasks (Fix B4)
# ══════════════════════════════════════════════════════════════════════════════


class TaskContractVerifier(BaseContractVerifier):
    """Verifier für Celery Task Signaturen.

    Fix B4: Korrekte Introspection für alle Celery Task-Typen:
      - @shared_task-dekorierte Funktionen (häufigster Fall)
      - @app.task-dekorierte Funktionen
      - Klassen-basierte Tasks (celery.Task-Subklassen)

    Erstellt über: ContractVerifier.for_task(my_task)
    """

    def __init__(self, task: Any) -> None:
        self._task = task
        self._name = self._get_task_name(task)
        self._func = self._resolve_task_function(task)  # Fix B4

    @staticmethod
    def _get_task_name(task: Any) -> str:
        return getattr(task, "name", None) or getattr(task, "__name__", str(task))

    @staticmethod
    def _resolve_task_function(task: Any) -> Callable[..., Any]:
        """Löst die eigentliche Funktion eines Celery Tasks auf.

        Fix B4: Behandelt alle Task-Typen korrekt.

        Celery Task-Typen:
          1. @shared_task fn → task.__wrapped__ zeigt auf originale Funktion
             → inspect.unwrap() folgt der __wrapped__-Kette korrekt
          2. @shared_task(bind=True) → hat self als ersten Parameter (ignoriert)
          3. class MyTask(Task): run() → task.run ist die Methode
          4. Direkte Funktion (in Tests ohne Celery-Setup) → callable
        """
        # Fall 1: inspect.unwrap() folgt __wrapped__-Kette (PEP 362, korrekt für Celery)
        # Vorteil über hasattr(__wrapped__): umgeht Python Descriptor-Binding für
        # class-level Funktionen (die sonst als bound method zurückkommen)
        try:
            unwrapped = inspect.unwrap(task)
            if callable(unwrapped) and unwrapped is not task:
                return unwrapped  # type: ignore[return-value]
        except (TypeError, StopIteration):
            pass

        # Fall 2: .run-Methode (Klassen-basierte Tasks, explizit als unbound holen)
        run_method = getattr(type(task), "run", None)  # unbound via Klasse
        if run_method is not None and callable(run_method):
            return run_method

        # Fall 3: Task ist direkt callable (z.B. Funktion in Tests ohne Celery-Setup)
        if callable(task):
            return task  # type: ignore[return-value]

        raise TypeError(
            f"Celery Task '{TaskContractVerifier._get_task_name(task)}': "
            f"Kann Task-Funktion nicht auflösen. "
            f"Weder inspect.unwrap() noch .run noch direkt callable. "
            f"Task-Typ: {type(task).__name__}"
        )

    def assert_params(self, expected: list[str]) -> None:
        """Prüft dass der Task die erwarteten Parameter hat."""
        sig = inspect.signature(self._func)
        # Ignoriere 'self' bei bind=True Tasks
        actual = [p for p in sig.parameters.keys() if p not in ("self", "cls")]
        missing = [p for p in expected if p not in actual]
        assert not missing, (
            f"Celery Task '{self._name}': Fehlende Parameter: {missing}. "
            f"Tatsächliche Signatur: {actual}. "
            f"→ task.delay()-Aufrufe im Consumer prüfen."
        )

    def assert_no_param(self, wrong_name: str) -> None:
        """Prüft dass ein falscher Parametername NICHT existiert."""
        sig = inspect.signature(self._func)
        params = set(sig.parameters.keys()) - {"self", "cls"}
        assert wrong_name not in params, (
            f"Celery Task '{self._name}': Alias-Parameter '{wrong_name}' sollte nicht "
            f"existieren. Tatsächliche Parameter: {sorted(params)}"
        )

    def assert_is_acks_late(self) -> None:
        """Prüft dass der Task acks_late=True gesetzt hat (ADR-Platform-Standard)."""
        acks_late = getattr(self._task, "acks_late", None)
        assert acks_late is True, (
            f"Celery Task '{self._name}': acks_late={acks_late!r}. "
            f"Platform-Standard (ADR): acks_late=True auf allen Tasks."
        )


# ══════════════════════════════════════════════════════════════════════════════
# ResponseShapeVerifier — Fix K3: implementiert for_response_schema
# ══════════════════════════════════════════════════════════════════════════════


class ResponseShapeVerifier:
    """Verifier für REST API Response-Shapes.

    Fix K3: War in Klassen-Docstring referenziert aber nie implementiert.

    Verwendung:
        verifier = ResponseShapeVerifier({"fit_score": float, "skills": list})
        verifier.assert_response(response_dict)
        verifier.assert_status_code(response, 200)
    """

    def __init__(self, expected_shape: dict[str, type]) -> None:
        self._shape = expected_shape

    def assert_response(self, actual: dict[str, Any]) -> None:
        """Prüft dass ein Response-Dict alle erwarteten Keys hat."""
        missing_keys = [k for k in self._shape if k not in actual]
        assert not missing_keys, (
            f"Response-Shape-Mismatch: Fehlende Keys: {missing_keys}. "
            f"Tatsächliche Keys: {sorted(actual.keys())}."
        )

    def assert_response_types(self, actual: dict[str, Any]) -> None:
        """Prüft Keys UND Typen der Werte."""
        self.assert_response(actual)
        type_errors = [
            f"  '{k}': erwartet {t.__name__}, got {type(actual[k]).__name__}"
            for k, t in self._shape.items()
            if k in actual and not isinstance(actual[k], t)
        ]
        assert not type_errors, (
            f"Response-Type-Mismatch:\n" + "\n".join(type_errors)
        )

    def assert_status_code(self, response: Any, expected: int) -> None:
        """Prüft HTTP Status-Code (kompatibel mit Django test client + requests)."""
        actual = getattr(response, "status_code", None)
        assert actual == expected, (
            f"HTTP Status {actual} ≠ erwartet {expected}."
        )
