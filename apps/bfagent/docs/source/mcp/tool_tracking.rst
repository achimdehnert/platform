================
MCP Tool Tracking
================

.. note::
   **Zentrales Tracking für alle MCP Tool Calls** | Status: Production

Übersicht
=========

Alle MCP Tool Calls werden automatisch getrackt für:

- **Audit Trail**: Wer hat wann welches Tool aufgerufen
- **Performance Monitoring**: Dauer, Erfolg/Fehler
- **Usage Analytics**: Welche Tools werden wie oft genutzt
- **Debugging**: Fehler-Analyse und Troubleshooting

Architektur
===========

.. code-block:: text

   ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
   │  bfagent_mcp    │     │  bfagent_db_mcp │     │ code_quality_mcp│
   └────────┬────────┘     └────────┬────────┘     └────────┬────────┘
            │                       │                       │
            │                       │                       │
            ▼                       ▼                       ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │                    OrchestrationCall Model                       │
   │                  (bfagent_orchestrationcall)                     │
   └─────────────────────────────────────────────────────────────────┘

Tracking-Modell
===============

OrchestrationCall
-----------------

Das zentrale Model für Tool-Call-Tracking:

.. code-block:: python

   class OrchestrationCall(models.Model):
       CALL_TYPES = [
           ('request', 'Request Received'),
           ('planning', 'Task Planning'),
           ('routing', 'Task Routing'),
           ('execution', 'Task Execution'),
           ('llm_call', 'LLM Call'),
           ('tool_call', 'Tool Call'),  # ← MCP Tools
           ('result', 'Result Returned'),
       ]
       
       call_type = models.CharField(max_length=20, choices=CALL_TYPES)
       name = models.CharField(max_length=200)  # Tool-Name
       description = models.TextField()  # Argumente (JSON)
       status = models.CharField(max_length=20)  # success/failed
       result_summary = models.TextField()  # Ergebnis (truncated)
       error_message = models.TextField()  # Fehler wenn vorhanden
       duration_ms = models.IntegerField()  # Ausführungsdauer
       session_id = models.CharField(max_length=100)  # Session-Gruppierung
       metadata = models.JSONField()  # Zusätzliche Infos

Felder
^^^^^^

- **call_type**: Immer ``'tool_call'`` für MCP Tools
- **name**: Tool-Name (z.B. ``bfagent_list_domains``)
- **description**: JSON-serialisierte Argumente
- **status**: ``success`` oder ``failed``
- **result_summary**: Truncated Result (max 500 chars)
- **error_message**: Fehlertext bei Failures
- **duration_ms**: Ausführungszeit in Millisekunden
- **session_id**: Format ``mcp-YYYYMMDD-HHMMSS``
- **metadata**: Tool-Kategorie, triggered_by, input_args

Integration
===========

bfagent_mcp
-----------

Tracking via ``_log_mcp_usage_async``:

.. code-block:: python

   # In packages/bfagent_mcp/bfagent_mcp/server.py
   
   async def _log_mcp_usage_async(
       tool_name: str,
       arguments: dict,
       result: str,
       status: str,
       error_message: str = None,
       duration_ms: int = 0
   ):
       from apps.bfagent.models_controlling import OrchestrationCall
       
       OrchestrationCall.objects.create(
           call_type='tool_call',  # WICHTIG: 'tool_call' nicht 'tool'!
           name=tool_name,
           description=json.dumps(arguments),
           status='success' if status == "success" else 'failed',
           result_summary=result[:500],
           error_message=error_message,
           duration_ms=duration_ms,
           session_id=f"mcp-{timezone.now():%Y%m%d-%H%M%S}",
           metadata={
               'tool_category': _categorize_tool(tool_name),
               'triggered_by': 'cascade',
           }
       )

bfagent_db_mcp
--------------

Tracking via ``_log_tool_call``:

.. code-block:: python

   # In packages/bfagent_db_mcp/server.py
   
   def _log_tool_call(tool_name, arguments, result, status, error, duration_ms):
       from apps.bfagent.models_testing import MCPUsageLog
       
       MCPUsageLog.objects.create(
           tool_name=f"bfagent_db:{tool_name}",
           tool_category="database",
           arguments=arguments,
           result_summary=result[:500],
           status=status,
           error_message=error,
           duration_ms=duration_ms,
       )

Shared Module
-------------

Zentrales Tracking-Modul für alle MCP Server:

.. code-block:: python

   # packages/mcp_shared/tracking.py
   
   from mcp_shared import log_mcp_call, log_mcp_call_sync
   
   # Async Version
   await log_mcp_call(
       server_name="code_quality",
       tool_name="analyze_python_file",
       arguments={"file_path": "..."},
       result="...",
       status="success",
       duration_ms=150
   )
   
   # Sync Version
   log_mcp_call_sync(...)

Bug-Fix Historie
================

call_type='tool' → 'tool_call'
------------------------------

**Datum:** 2026-01-16

**Problem:** Tool-Calls wurden mit ``call_type='tool'`` geloggt, aber
das ``OrchestrationCall`` Model hat nur ``'tool_call'`` als validen Choice.

**Fix:** 

.. code-block:: python

   # VORHER (falsch):
   call_type='tool'
   
   # NACHHER (korrekt):
   call_type='tool_call'

**Commit:** ``9e1ef9ff`` - "fix: Change call_type from 'tool' to 'tool_call'"

**DB-Migration:** 6 existierende Records wurden korrigiert:

.. code-block:: sql

   UPDATE bfagent_orchestrationcall 
   SET call_type = 'tool_call' 
   WHERE call_type = 'tool';

Abfragen
========

Tracking-Daten abfragen
-----------------------

.. code-block:: python

   from apps.bfagent.models_controlling import OrchestrationCall
   
   # Letzte 10 Tool-Calls
   OrchestrationCall.objects.filter(
       call_type='tool_call'
   ).order_by('-started_at')[:10]
   
   # Calls pro Tool
   from django.db.models import Count
   OrchestrationCall.objects.filter(
       call_type='tool_call'
   ).values('name').annotate(
       cnt=Count('id')
   ).order_by('-cnt')
   
   # Fehlerhafte Calls
   OrchestrationCall.objects.filter(
       call_type='tool_call',
       status='failed'
   )
   
   # Durchschnittliche Dauer pro Tool
   from django.db.models import Avg
   OrchestrationCall.objects.filter(
       call_type='tool_call'
   ).values('name').annotate(
       avg_duration=Avg('duration_ms')
   )

Via bfagent_django_query Tool
-----------------------------

.. code-block:: python

   bfagent_django_query(
       model="apps.bfagent.models_controlling.OrchestrationCall",
       action="filter",
       filter_kwargs={"call_type": "tool_call"},
       limit=10
   )

Best Practices
==============

1. **Immer 'tool_call' verwenden**: Nicht 'tool' oder andere Werte
2. **Arguments truncaten**: Max 1000 chars für description
3. **Results truncaten**: Max 500 chars für result_summary
4. **Fire-and-forget**: Logging sollte Tool nicht blockieren
5. **Error handling**: Logging-Fehler sollten Tool nicht crashen

Troubleshooting
===============

Keine Tracking-Einträge
-----------------------

1. **MCP Server neu starten**: Windsurf neustarten
2. **Django Setup prüfen**: DJANGO_SETTINGS_MODULE gesetzt?
3. **DB-Verbindung prüfen**: PostgreSQL erreichbar?
4. **Logs checken**: ``logger.warning("Failed to log MCP usage: ...)``

Falsche call_type Werte
-----------------------

.. code-block:: sql

   -- Prüfen
   SELECT call_type, COUNT(*) 
   FROM bfagent_orchestrationcall 
   GROUP BY call_type;
   
   -- Korrigieren
   UPDATE bfagent_orchestrationcall 
   SET call_type = 'tool_call' 
   WHERE call_type = 'tool';
