.. _llm-technical-reference:

==========================================
LLM Service - Technische Referenz
==========================================

.. contents:: Inhalt
   :local:
   :depth: 3

Architektur
===========

Das LLM-Subsystem folgt einer **Provider-Abstraktions-Architektur**:

.. mermaid::

   classDiagram
       class BaseLLMClient {
           <<abstract>>
           +provider: str
           +config: LLMConfig
           +generate(prompt) LLMResponse
           +generate_structured(prompt, model) T
           +generate_stream(prompt) Generator
           #_generate(request) LLMResponse
           #_init_client()
       }
       
       class OpenAIClient {
           +provider = "openai"
           -_client: OpenAI
           #_generate(request)
           #_init_client()
       }
       
       class AnthropicClient {
           +provider = "anthropic"
           -_client: Anthropic
           #_generate(request)
           #_init_client()
       }
       
       class LLMConfig {
           +provider: str
           +api_key: str
           +api_endpoint: str
           +model: str
           +default_temperature: float
           +default_max_tokens: int
           +timeout: int
           +retry_count: int
       }
       
       class LLMRequest {
           +prompt: str
           +system_prompt: str
           +temperature: float
           +max_tokens: int
           +response_format: ResponseFormat
           +response_schema: Type
       }
       
       class LLMResponse {
           +success: bool
           +content: str
           +usage: TokenUsage
           +latency_ms: int
           +error: str
       }
       
       BaseLLMClient <|-- OpenAIClient
       BaseLLMClient <|-- AnthropicClient
       BaseLLMClient --> LLMConfig
       BaseLLMClient --> LLMRequest
       BaseLLMClient --> LLMResponse

Modul-Struktur
==============

::

   apps/core/services/llm/
   ├── __init__.py          # Public API, Factory Functions
   ├── base.py              # BaseLLMClient (Abstract)
   ├── openai_client.py     # OpenAI Implementation
   ├── anthropic_client.py  # Anthropic Implementation
   ├── models.py            # Data Models (Request, Response, Config)
   ├── exceptions.py        # Exception Hierarchy
   └── utils.py             # Token Utilities, Cost Tracking

Public API
==========

Factory Functions
-----------------

.. py:function:: get_client(provider=None, api_key=None, model=None, **kwargs)

   Factory für LLM-Client-Instanzen.
   
   :param provider: Provider-Name ("openai", "anthropic", "local")
   :param api_key: API-Key (optional, nutzt Settings wenn nicht angegeben)
   :param model: Model-Name (optional, nutzt Provider-Default)
   :param kwargs: Weitere Config-Parameter
   :return: Konfigurierte ``BaseLLMClient``-Instanz
   
   **Beispiel:**
   
   .. code-block:: python
   
      # Auto-Detection aus Django Settings
      client = get_client()
      
      # Expliziter Provider
      client = get_client("anthropic", model="claude-3-5-sonnet-20241022")
      
      # Mit allen Optionen
      client = get_client(
          provider="openai",
          api_key="sk-...",
          model="gpt-4o",
          timeout=60,
          retry_count=5
      )

.. py:function:: get_openai_client(api_key=None, model="gpt-4", **kwargs)

   Convenience-Funktion für OpenAI-Client.
   
   :return: ``OpenAIClient``-Instanz

.. py:function:: get_anthropic_client(api_key=None, model="claude-3-5-sonnet-20241022", **kwargs)

   Convenience-Funktion für Anthropic-Client.
   
   :return: ``AnthropicClient``-Instanz

.. py:function:: generate(prompt, provider=None, model=None, system_prompt=None, **kwargs)

   Quick-Funktion für einmalige Generierung.
   
   :param prompt: User-Prompt
   :param provider: Optional Provider
   :param model: Optional Model
   :param system_prompt: Optional System-Prompt
   :return: ``LLMResponse``

BaseLLMClient
-------------

.. py:class:: BaseLLMClient

   Abstrakte Basisklasse für alle LLM-Clients.
   
   .. py:attribute:: provider
      :type: str
      
      Provider-Identifier (z.B. "openai", "anthropic")
   
   .. py:attribute:: config
      :type: LLMConfig
      
      Client-Konfiguration
   
   .. py:method:: generate(prompt, system_prompt=None, temperature=None, max_tokens=None, **kwargs)
   
      Hauptmethode für Text-Generierung.
      
      :param prompt: User-Prompt
      :param system_prompt: System/Instruction-Prompt
      :param temperature: Sampling-Temperatur (0-2)
      :param max_tokens: Maximale Output-Tokens
      :return: ``LLMResponse``
      
      **Beispiel:**
      
      .. code-block:: python
      
         response = client.generate(
             prompt="Erkläre Dependency Injection",
             system_prompt="Antworte als Senior Developer",
             temperature=0.3,
             max_tokens=500
         )
   
   .. py:method:: generate_structured(prompt, response_model, system_prompt=None, **kwargs)
   
      Generierung mit Pydantic-Schema-Validierung.
      
      :param prompt: User-Prompt
      :param response_model: Pydantic ``BaseModel`` Klasse
      :param system_prompt: Optional System-Prompt
      :return: Instanz von ``response_model``
      :raises LLMValidationError: Bei Schema-Verletzung
      
      **Beispiel:**
      
      .. code-block:: python
      
         from pydantic import BaseModel
         
         class Entity(BaseModel):
             name: str
             type: str
             confidence: float
         
         entity = client.generate_structured(
             prompt="Extrahiere: 'Apple Inc. ist ein Technologieunternehmen'",
             response_model=Entity
         )
         # entity.name = "Apple Inc."
         # entity.type = "Unternehmen"
         # entity.confidence = 0.95
   
   .. py:method:: generate_stream(prompt, system_prompt=None, **kwargs)
   
      Streaming-Generierung für lange Texte.
      
      :param prompt: User-Prompt
      :yield: Text-Chunks
      
      **Beispiel:**
      
      .. code-block:: python
      
         for chunk in client.generate_stream("Erzähle eine Geschichte"):
             print(chunk, end="", flush=True)
   
   .. py:method:: estimate_tokens(text)
   
      Schätzt Token-Anzahl für Text.
      
      :param text: Zu schätzender Text
      :return: Geschätzte Token-Anzahl (int)
   
   .. py:method:: calculate_cost(usage, model=None)
   
      Berechnet Kosten für Token-Usage.
      
      :param usage: ``TokenUsage``-Objekt
      :param model: Optional Model-Name
      :return: Kosten in USD (float)
   
   .. py:method:: health_check()
   
      Prüft Verbindung zum Provider.
      
      :return: ``True`` wenn erfolgreich

Datenmodelle
============

LLMConfig
---------

.. py:class:: LLMConfig

   Konfiguration für LLM-Client.
   
   .. code-block:: python
   
      @dataclass
      class LLMConfig:
          provider: str = "openai"
          api_key: Optional[str] = None
          api_endpoint: Optional[str] = None
          model: Optional[str] = None
          default_temperature: float = 0.7
          default_max_tokens: int = 4096
          timeout: int = 120
          retry_count: int = 3
          retry_delay: float = 1.0

   **Properties:**
   
   .. py:attribute:: effective_model
   
      Gibt Model mit Provider-Default zurück wenn nicht explizit gesetzt.
      
      +-----------+---------------------------+
      | Provider  | Default Model             |
      +===========+===========================+
      | openai    | gpt-4                     |
      +-----------+---------------------------+
      | anthropic | claude-3-5-sonnet-20241022|
      +-----------+---------------------------+
      | google    | gemini-pro                |
      +-----------+---------------------------+
   
   .. py:attribute:: effective_endpoint
   
      Gibt API-Endpoint mit Provider-Default zurück.

LLMRequest
----------

.. py:class:: LLMRequest

   Request-Objekt für LLM-Aufrufe.
   
   .. code-block:: python
   
      @dataclass
      class LLMRequest:
          prompt: str
          system_prompt: Optional[str] = None
          messages: Optional[List[Dict[str, str]]] = None
          temperature: Optional[float] = None
          max_tokens: Optional[int] = None
          top_p: Optional[float] = None
          frequency_penalty: Optional[float] = None
          presence_penalty: Optional[float] = None
          stop: Optional[List[str]] = None
          response_format: ResponseFormat = ResponseFormat.TEXT
          response_schema: Optional[Type] = None
          stream: bool = False
          metadata: Dict[str, Any] = field(default_factory=dict)

LLMResponse
-----------

.. py:class:: LLMResponse

   Response-Objekt von LLM-Aufrufen.
   
   .. code-block:: python
   
      @dataclass
      class LLMResponse:
          success: bool
          content: Optional[str] = None
          structured_output: Optional[Any] = None
          usage: Optional[TokenUsage] = None
          model: Optional[str] = None
          finish_reason: Optional[str] = None
          latency_ms: Optional[int] = None
          raw_response: Optional[Dict[str, Any]] = None
          error: Optional[str] = None

   **Class Methods:**
   
   .. py:method:: error_response(error, latency_ms=None)
      :classmethod:
      
      Erstellt Fehler-Response.
   
   .. py:method:: success_response(content, usage=None, model=None, ...)
      :classmethod:
      
      Erstellt Erfolgs-Response.

TokenUsage
----------

.. py:class:: TokenUsage

   Token-Verbrauch eines Aufrufs.
   
   .. code-block:: python
   
      @dataclass
      class TokenUsage:
          prompt_tokens: int = 0
          completion_tokens: int = 0
          total_tokens: int = 0

   **Aliases für Anthropic-Kompatibilität:**
   
   - ``input_tokens`` → ``prompt_tokens``
   - ``output_tokens`` → ``completion_tokens``

ResponseFormat
--------------

.. py:class:: ResponseFormat

   Enum für Response-Format.
   
   .. code-block:: python
   
      class ResponseFormat(str, Enum):
          TEXT = "text"
          JSON = "json"
          STRUCTURED = "structured"

Exceptions
==========

Exception-Hierarchie
--------------------

.. mermaid::

   classDiagram
       class LLMException {
           +message: str
           +provider: str
           +model: str
           +original_error: Exception
           +to_dict() dict
       }
       
       LLMException <|-- LLMConnectionError
       LLMException <|-- LLMAuthenticationError
       LLMException <|-- LLMRateLimitError
       LLMException <|-- LLMQuotaExceededError
       LLMException <|-- LLMValidationError
       LLMException <|-- LLMContentFilterError
       LLMException <|-- LLMContextLengthError
       LLMException <|-- LLMModelNotFoundError
       LLMException <|-- LLMTimeoutError
       LLMException <|-- LLMConfigurationError

Exception-Referenz
------------------

.. py:exception:: LLMException

   Basis-Exception für alle LLM-Fehler.
   
   :param message: Fehlermeldung
   :param provider: Provider der den Fehler auslöste
   :param model: Verwendetes Model
   :param original_error: Original-Exception

.. py:exception:: LLMConnectionError

   Netzwerk- oder Verbindungsfehler.

.. py:exception:: LLMAuthenticationError

   Ungültiger oder fehlender API-Key.

.. py:exception:: LLMRateLimitError

   Rate-Limit überschritten.
   
   :param retry_after: Wartezeit in Sekunden

.. py:exception:: LLMQuotaExceededError

   Billing-Quota erschöpft.

.. py:exception:: LLMValidationError

   Schema-Validierung fehlgeschlagen.
   
   :param content: Roher Content der nicht validiert werden konnte
   :param validation_errors: Liste der Validierungsfehler

.. py:exception:: LLMContentFilterError

   Content wurde von Safety-Filter blockiert.
   
   :param filter_type: Typ des Filters
   :param flagged_categories: Betroffene Kategorien

.. py:exception:: LLMContextLengthError

   Kontext-Fenster überschritten.
   
   :param max_tokens: Maximale erlaubte Tokens
   :param actual_tokens: Tatsächliche Token-Anzahl

.. py:exception:: LLMModelNotFoundError

   Angefordertes Model existiert nicht.

.. py:exception:: LLMTimeoutError

   Request-Timeout überschritten.
   
   :param timeout_seconds: Timeout-Wert

.. py:exception:: LLMConfigurationError

   Ungültige Client-Konfiguration.

Utility Functions
=================

Token-Utilities
---------------

.. py:function:: estimate_tokens(text)

   Schätzt Token-Anzahl (~4 Zeichen/Token für Englisch).
   
   :param text: Zu schätzender Text
   :return: Token-Schätzung (int)

.. py:function:: truncate_to_tokens(text, max_tokens, preserve_end=False)

   Kürzt Text auf maximale Token-Anzahl.
   
   :param text: Zu kürzender Text
   :param max_tokens: Maximum
   :param preserve_end: Ende statt Anfang behalten
   :return: Gekürzter Text

.. py:function:: count_messages_tokens(messages)

   Zählt Tokens in Messages-Array.
   
   :param messages: Liste von Message-Dicts
   :return: Token-Summe (int)

Prompt-Utilities
----------------

.. py:function:: format_system_prompt(template, **kwargs)

   Formatiert System-Prompt mit Variablen.
   
   :param template: Prompt-Template
   :param kwargs: Template-Variablen
   :return: Formatierter Prompt

.. py:function:: build_few_shot_prompt(task, examples, query)

   Baut Few-Shot-Prompt aus Beispielen.
   
   :param task: Aufgabenbeschreibung
   :param examples: Liste von (input, output) Tupeln
   :param query: Aktuelle Anfrage
   :return: Formatierter Few-Shot-Prompt

Cost Tracking
-------------

.. py:class:: CostTracker

   Tracking von LLM-Kosten.
   
   .. code-block:: python
   
      tracker = CostTracker()
      
      # Nach jedem Aufruf
      tracker.add_usage(response.usage, model="gpt-4o")
      
      # Zusammenfassung
      print(f"Total: ${tracker.total_cost:.4f}")
      print(f"Calls: {tracker.total_calls}")

.. py:class:: UsageRecord

   Einzelner Usage-Eintrag.
   
   .. code-block:: python
   
      @dataclass
      class UsageRecord:
          timestamp: datetime
          model: str
          prompt_tokens: int
          completion_tokens: int
          cost: float

Preise
======

Die aktuellen Preise (Stand 2024) sind in ``LLM_PRICING`` definiert:

.. code-block:: python

   LLM_PRICING = {
       "openai": {
           "gpt-4": {"input": 0.03, "output": 0.06},
           "gpt-4-turbo": {"input": 0.01, "output": 0.03},
           "gpt-4o": {"input": 0.005, "output": 0.015},
           "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
           "o1-preview": {"input": 0.015, "output": 0.06},
           "o1-mini": {"input": 0.003, "output": 0.012},
       },
       "anthropic": {
           "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
           "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
           "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
       },
       "google": {
           "gemini-pro": {"input": 0.00025, "output": 0.0005},
           "gemini-1.5-pro": {"input": 0.0035, "output": 0.0105},
           "gemini-1.5-flash": {"input": 0.00035, "output": 0.00105},
       },
   }

Eigenen Provider implementieren
===============================

Um einen neuen Provider zu implementieren:

.. code-block:: python

   from apps.core.services.llm import BaseLLMClient, LLMRequest, LLMResponse
   
   class MyProviderClient(BaseLLMClient):
       """Client für meinen LLM-Provider."""
       
       provider = "myprovider"
       
       def _init_client(self):
           """Initialisiert den Provider-SDK-Client."""
           self._client = MySDK(api_key=self.config.api_key)
       
       def _generate(self, request: LLMRequest) -> LLMResponse:
           """Implementiert die Generierung."""
           try:
               result = self._client.complete(
                   prompt=request.prompt,
                   system=request.system_prompt,
                   max_tokens=request.max_tokens,
                   temperature=request.temperature,
               )
               
               return LLMResponse.success_response(
                   content=result.text,
                   usage=TokenUsage(
                       prompt_tokens=result.input_tokens,
                       completion_tokens=result.output_tokens,
                       total_tokens=result.total_tokens,
                   ),
                   model=result.model,
               )
           except MyProviderError as e:
               return LLMResponse.error_response(str(e))

Integration mit Django Settings
===============================

Der Service liest automatisch aus Django Settings:

.. code-block:: python

   # config/settings/base.py
   
   # Standard-Provider
   LLM_PROVIDER = env("LLM_PROVIDER", default="openai")
   LLM_MODEL = env("LLM_MODEL", default=None)
   
   # API Keys
   OPENAI_API_KEY = env("OPENAI_API_KEY", default=None)
   ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default=None)
   
   # Optionale Endpoints
   OPENAI_API_ENDPOINT = env("OPENAI_API_ENDPOINT", default=None)
   ANTHROPIC_API_ENDPOINT = env("ANTHROPIC_API_ENDPOINT", default=None)

Testing
=======

Mock-Client für Tests
---------------------

.. code-block:: python

   from unittest.mock import Mock, patch
   from apps.core.services.llm import LLMResponse, TokenUsage
   
   def test_my_handler():
       mock_response = LLMResponse.success_response(
           content="Mocked response",
           usage=TokenUsage(100, 50, 150)
       )
       
       with patch('apps.core.services.llm.get_client') as mock:
           mock.return_value.generate.return_value = mock_response
           
           # Test your code
           result = my_function_using_llm()
           
           assert result == expected

Integration Test
----------------

.. code-block:: python

   import pytest
   from apps.core.services.llm import get_client
   
   @pytest.mark.integration
   def test_openai_connection():
       client = get_client("openai")
       assert client.health_check() is True
   
   @pytest.mark.integration
   def test_generation():
       client = get_client()
       response = client.generate("Say 'test'", max_tokens=10)
       
       assert response.success
       assert "test" in response.content.lower()

Siehe auch
==========

- :ref:`ai-integration-guide` - Benutzerhandbuch
- :doc:`handlers` - Handler mit LLM-Integration
- :doc:`../concepts/agent-architecture` - Agent-Architektur mit LLM
