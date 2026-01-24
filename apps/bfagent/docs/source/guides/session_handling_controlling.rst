================================
Session Handling & Controlling
================================

.. note::
   **Stand:** 16. Januar 2026 | **Status:** Production Ready

Überblick
=========

Das Session Handling & Controlling System bietet vollständige Nachverfolgbarkeit 
aller Interaktionen zwischen User und Cascade (AI Assistant). Es basiert auf dem 
bestehenden ``OrchestrationCall``-Modell und integriert sich nahtlos in das 
BF Agent Controlling Dashboard.

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────┐
   │                    CONTROLLING SYSTEM                        │
   ├─────────────────────────────────────────────────────────────┤
   │                                                             │
   │  User Request                                               │
   │       ↓                                                     │
   │  bfagent_log_user_request()  →  OrchestrationCall           │
   │       ↓                         (call_type='request')       │
   │  Tool Calls (automatisch)    →  OrchestrationCall           │
   │       ↓                         (call_type='tool')          │
   │  LLM Calls (bestehend)       →  LLMUsageLog                 │
   │       ↓                                                     │
   │  bfagent_log_session_end()   →  Session Update              │
   │                                                             │
   └─────────────────────────────────────────────────────────────┘

Komponenten
===========

OrchestrationCall Modell
------------------------

Zentrale Tabelle für alle Tracking-Daten in ``apps/bfagent/models_controlling.py``:

.. code-block:: python

   class OrchestrationCall(models.Model):
       CALL_TYPES = [
           ('request', 'User Request'),   # NEU: User-Anfragen
           ('tool', 'Tool Call'),         # MCP Tool Aufrufe
           ('llm', 'LLM Call'),           # LLM Interaktionen
           ('validation', 'Validation'),
           ('delegation', 'Code Delegation'),
           ('agent', 'Agent Action'),
       ]
       
       call_type = models.CharField(max_length=20, choices=CALL_TYPES)
       name = models.CharField(max_length=200)
       description = models.TextField(blank=True)
       status = models.CharField(...)  # running, success, failed
       session_id = models.CharField(max_length=100)
       metadata = models.JSONField(default=dict)
       duration_ms = models.IntegerField(null=True)

MCP Tools
=========

bfagent_log_user_request
------------------------

Loggt den Start einer User-Session:

.. code-block:: python

   # Aufruf
   bfagent_log_user_request(
       user_request="Erstelle eine REST API für Books",
       mode="auto",           # auto, route, ab, ac, default
       context="apps/api/"    # Optional: Zusätzlicher Kontext
   )

**Response:**

.. code-block:: text

   ## 📝 Session gestartet

   **Session ID:** `session-a1b2c3d4`
   **Modus:** auto
   **Request:** Erstelle eine REST API für Books...

bfagent_log_session_end
-----------------------

Schließt eine Session ab:

.. code-block:: python

   bfagent_log_session_end(
       session_id="session-a1b2c3d4",  # Optional
       summary="REST API implementiert mit 4 Endpoints",
       success=True
   )

Automatisches Tool-Logging
==========================

Jeder MCP Tool-Aufruf wird automatisch geloggt (Fire-and-Forget):

.. code-block:: python

   # packages/bfagent_mcp/bfagent_mcp/server.py

   @mcp_server.call_tool()
   async def call_tool(name: str, arguments: Dict[str, Any]):
       start_time = time.time()
       
       try:
           result = await _dispatch_tool(name, arguments)
           duration_ms = int((time.time() - start_time) * 1000)
           
           # Automatisches Logging (non-blocking)
           _log_mcp_usage(
               tool_name=name,
               arguments=arguments,
               result=result,
               status="success",
               duration_ms=duration_ms
           )
           
           return [TextContent(type="text", text=result)]
       except Exception as e:
           _log_mcp_usage(name, arguments, status="error", error_message=str(e))
           raise

Tool-Kategorisierung
--------------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Tool-Pattern
     - Kategorie
   * - ``*domain*``, ``*handler*``
     - domain
   * - ``*template*``
     - template
   * - ``*shell*``, ``*query*``
     - database
   * - ``*doc*``
     - documentation
   * - ``*requirement*``, ``*initiative*``
     - workflow
   * - ``*refactor*``
     - refactoring
   * - ``*chrome*``, ``*sentry*``, ``*grafana*``
     - devops

Dashboard
=========

URL
---

::

   /control-center/controlling/orchestration/

Ansichten
---------

1. **Übersicht**: Alle OrchestrationCalls mit Filter
2. **Session-Gruppierung**: Calls gruppiert nach ``session_id``
3. **Statistiken**: Calls pro Typ, Erfolgsrate, Durchschnittsdauer

Filter
------

- Nach ``call_type``: request, tool, llm, etc.
- Nach ``status``: running, success, failed
- Nach ``session_id``: Bestimmte Session
- Nach Zeitraum

Best Practices
==============

Session-Start am Anfang
-----------------------

.. code-block:: python

   # Cascade sollte bei jedem User-Request starten mit:
   bfagent_log_user_request(
       user_request="<original message>",
       mode="auto"  # oder route, ab, ac
   )

Session-Ende bei Abschluss
--------------------------

.. code-block:: python

   # Am Ende der Arbeit:
   bfagent_log_session_end(
       summary="Was wurde erreicht",
       success=True
   )

Keine manuellen Tool-Logs
-------------------------

Tool-Aufrufe werden **automatisch** geloggt. Keine zusätzliche Aktion nötig.

Troubleshooting
===============

Logs erscheinen nicht
---------------------

1. **MCP Server neu starten** (nach Code-Änderungen)
2. **Django Server läuft?** (für DB-Zugriff)
3. **Prüfen:** ``OrchestrationCall.objects.filter(call_type='tool').count()``

Session-ID fehlt
----------------

Wenn ``bfagent_log_user_request`` nicht aufgerufen wurde, haben Tool-Calls 
eine generierte Session-ID im Format ``mcp-YYYYMMDD-HHMMSS``.

Verwandte Dokumentation
=======================

.. toctree::
   :maxdepth: 1

   LLM_USAGE_TRACKING
   CONTROLLING_DASHBOARD

Änderungshistorie
=================

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Datum
     - Änderung
   * - 2026-01-16
     - Session Tracking Tools hinzugefügt
   * - 2026-01-16
     - MCP Tool Logging via OrchestrationCall
   * - 2026-01-16
     - Fire-and-Forget Async Logging
