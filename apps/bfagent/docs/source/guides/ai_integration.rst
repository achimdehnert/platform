.. _ai-integration-guide:

======================================
AI/LLM Integration - Benutzerhandbuch
======================================

.. contents:: Inhalt
   :local:
   :depth: 2

Übersicht
=========

BF Agent bietet eine **Multi-Provider LLM Integration** für AI-gestützte Funktionen.
Das System abstrahiert die Unterschiede zwischen Anbietern und ermöglicht 
einheitlichen Zugriff auf:

- **OpenAI** (GPT-4, GPT-4o, o1)
- **Anthropic** (Claude 3.5, Claude 3)
- **Google** (Gemini Pro, Gemini Flash)
- **Lokale Modelle** (Ollama, vLLM)

.. mermaid::

   flowchart LR
       App[Ihre Anwendung] --> LLM[LLM Service]
       LLM --> OpenAI[OpenAI API]
       LLM --> Anthropic[Anthropic API]
       LLM --> Google[Google AI]
       LLM --> Local[Lokale Modelle]

Schnellstart
============

1. API-Keys konfigurieren
-------------------------

Fügen Sie Ihre API-Keys zur ``.env`` Datei hinzu:

.. code-block:: ini

   # OpenAI (empfohlen für GPT-4)
   OPENAI_API_KEY=sk-proj-...
   
   # Anthropic (empfohlen für Claude)
   ANTHROPIC_API_KEY=sk-ant-...
   
   # Optional: Standard-Provider
   LLM_PROVIDER=openai
   LLM_MODEL=gpt-4o

2. Erste Generierung
--------------------

.. code-block:: python

   from apps.core.services.llm import get_client
   
   # Client erstellen (nutzt Einstellungen aus .env)
   client = get_client()
   
   # Text generieren
   response = client.generate("Erkläre mir Django in 3 Sätzen")
   
   if response.success:
       print(response.content)
   else:
       print(f"Fehler: {response.error}")

3. Provider auswählen
---------------------

.. code-block:: python

   # OpenAI explizit
   client = get_client("openai", model="gpt-4o")
   
   # Anthropic
   client = get_client("anthropic", model="claude-3-5-sonnet-20241022")
   
   # Mit eigenem API-Key
   client = get_client("openai", api_key="sk-...", model="gpt-4")

Verwendung
==========

Text-Generierung
----------------

Einfache Text-Generierung mit optionalem System-Prompt:

.. code-block:: python

   response = client.generate(
       prompt="Schreibe einen Produkttext für einen Laptop",
       system_prompt="Du bist ein erfahrener Werbetexter.",
       temperature=0.7,      # Kreativität (0-2)
       max_tokens=500        # Maximale Länge
   )
   
   print(response.content)
   print(f"Tokens: {response.usage.total_tokens}")
   print(f"Latenz: {response.latency_ms}ms")

Strukturierte Ausgabe
---------------------

Erhalten Sie typsichere Antworten mit Pydantic-Schemas:

.. code-block:: python

   from pydantic import BaseModel
   from typing import List
   
   class ProductInfo(BaseModel):
       name: str
       price: float
       features: List[str]
       rating: float
   
   # LLM generiert valides ProductInfo-Objekt
   product = client.generate_structured(
       prompt="Extrahiere Produktinfos: MacBook Pro 16', 2499€, M3 Chip, 18h Akku, 4.8 Sterne",
       response_model=ProductInfo
   )
   
   print(product.name)      # "MacBook Pro 16'"
   print(product.price)     # 2499.0
   print(product.features)  # ["M3 Chip", "18h Akku"]

Streaming
---------

Für lange Texte können Sie Streaming verwenden:

.. code-block:: python

   for chunk in client.generate_stream("Erzähle eine kurze Geschichte"):
       print(chunk, end="", flush=True)

Quick-Funktion
--------------

Für einmalige Aufrufe ohne Client-Instanz:

.. code-block:: python

   from apps.core.services.llm import generate
   
   response = generate(
       prompt="Was ist 2+2?",
       provider="openai",
       model="gpt-4o-mini"
   )
   print(response.content)

Provider-Konfiguration
======================

OpenAI
------

.. code-block:: ini

   # .env
   OPENAI_API_KEY=sk-proj-...
   
   # Optional: Organisation
   OPENAI_ORG_ID=org-...

**Verfügbare Modelle:**

+-------------------+------------+------------------+------------------+
| Modell            | Kontext    | Input $/1k       | Output $/1k      |
+===================+============+==================+==================+
| gpt-4o            | 128k       | $0.005           | $0.015           |
+-------------------+------------+------------------+------------------+
| gpt-4o-mini       | 128k       | $0.00015         | $0.0006          |
+-------------------+------------+------------------+------------------+
| gpt-4-turbo       | 128k       | $0.01            | $0.03            |
+-------------------+------------+------------------+------------------+
| o1-preview        | 128k       | $0.015           | $0.06            |
+-------------------+------------+------------------+------------------+
| o1-mini           | 128k       | $0.003           | $0.012           |
+-------------------+------------+------------------+------------------+

**Empfehlung:** ``gpt-4o-mini`` für Entwicklung, ``gpt-4o`` für Produktion.

Anthropic
---------

.. code-block:: ini

   # .env
   ANTHROPIC_API_KEY=sk-ant-...

**Verfügbare Modelle:**

+---------------------------+------------+------------------+------------------+
| Modell                    | Kontext    | Input $/1k       | Output $/1k      |
+===========================+============+==================+==================+
| claude-3-5-sonnet-20241022| 200k       | $0.003           | $0.015           |
+---------------------------+------------+------------------+------------------+
| claude-3-opus-20240229    | 200k       | $0.015           | $0.075           |
+---------------------------+------------+------------------+------------------+
| claude-3-haiku-20240307   | 200k       | $0.00025         | $0.00125         |
+---------------------------+------------+------------------+------------------+

**Empfehlung:** ``claude-3-5-sonnet`` für beste Qualität/Preis.

Lokale Modelle (Ollama)
-----------------------

Für lokale Inferenz mit Ollama:

.. code-block:: ini

   # .env
   LLM_PROVIDER=local
   LLM_ENDPOINT=http://localhost:11434/v1
   LLM_MODEL=llama3.1

.. code-block:: python

   client = get_client(
       provider="local",
       api_endpoint="http://localhost:11434/v1",
       model="llama3.1"
   )

Best Practices
==============

1. Temperatur richtig wählen
----------------------------

+-----------------+-------------+------------------------+
| Use Case        | Temperature | Beschreibung           |
+=================+=============+========================+
| Fakten-Extrakt  | 0.0 - 0.3   | Deterministisch        |
+-----------------+-------------+------------------------+
| Zusammenfassung | 0.3 - 0.5   | Konsistent             |
+-----------------+-------------+------------------------+
| Kreatives       | 0.7 - 1.0   | Variiert               |
+-----------------+-------------+------------------------+
| Brainstorming   | 1.0 - 1.5   | Sehr kreativ           |
+-----------------+-------------+------------------------+

2. Token-Kosten optimieren
--------------------------

.. code-block:: python

   from apps.core.services.llm import estimate_tokens
   
   # Tokens vor dem Aufruf schätzen
   text = "Ihr langer Text..."
   estimated = estimate_tokens(text)
   print(f"Geschätzte Tokens: {estimated}")
   
   # Kosten nach dem Aufruf
   response = client.generate(prompt)
   cost = client.calculate_cost(response.usage)
   print(f"Kosten: ${cost:.4f}")

3. Fehlerbehandlung
-------------------

.. code-block:: python

   from apps.core.services.llm import (
       LLMRateLimitError,
       LLMAuthenticationError,
       LLMContextLengthError
   )
   
   try:
       response = client.generate(prompt)
   except LLMRateLimitError as e:
       print(f"Rate Limit! Warte {e.retry_after}s")
   except LLMAuthenticationError:
       print("API-Key ungültig!")
   except LLMContextLengthError as e:
       print(f"Text zu lang: {e.actual_tokens} > {e.max_tokens}")

4. System-Prompts nutzen
------------------------

.. code-block:: python

   SYSTEM_PROMPT = """
   Du bist ein Experte für technische Dokumentation.
   - Antworte präzise und strukturiert
   - Verwende Markdown für Formatierung
   - Füge Code-Beispiele hinzu wo sinnvoll
   """
   
   response = client.generate(
       prompt="Erkläre Django Migrations",
       system_prompt=SYSTEM_PROMPT
   )

Integration in BF Agent
=======================

Der LLM Service ist in alle Hubs integriert:

Writing Hub
-----------

.. code-block:: python

   from apps.writing_hub.handlers.chapter_writer import ChapterWriterHandler
   
   handler = ChapterWriterHandler()
   result = handler.handle({
       "project_id": 17,
       "chapter_number": 1,
       "outline": "Einführung des Protagonisten"
   })

CAD Hub
-------

.. code-block:: python

   from apps.cad_hub.services import analyze_building
   
   # AI-gestützte Gebäudeanalyse
   result = analyze_building(ifc_model_id=42)

Troubleshooting
===============

API-Key funktioniert nicht
--------------------------

1. Prüfen Sie, ob der Key korrekt in ``.env`` steht
2. Stellen Sie sicher, dass keine Leerzeichen vorhanden sind
3. Prüfen Sie Ihr API-Guthaben beim Provider

.. code-block:: python

   # Health-Check
   client = get_client()
   if client.health_check():
       print("✅ Verbindung OK")
   else:
       print("❌ Verbindung fehlgeschlagen")

Rate Limits
-----------

Bei häufigen Rate-Limit-Fehlern:

.. code-block:: python

   from apps.core.services.llm import LLMConfig
   
   config = LLMConfig(
       retry_count=5,      # Mehr Versuche
       retry_delay=2.0     # Längere Wartezeit
   )
   client = get_client(config=config)

Kontextlänge überschritten
--------------------------

.. code-block:: python

   from apps.core.services.llm import truncate_to_tokens
   
   # Text auf max. 4000 Tokens kürzen
   safe_text = truncate_to_tokens(long_text, max_tokens=4000)

Weiterführende Dokumentation
============================

- :ref:`llm-technical-reference` - Technische API-Referenz
- :doc:`../reference/handlers` - Handler mit LLM-Integration
- :doc:`../hubs/writing-hub` - Writing Hub mit AI-Features
