===========
BFAgent MCP
===========

.. note::
   **Haupt-MCP Server für BF Agent** | 35+ Tools | Status: Production

Übersicht
=========

Der BFAgent MCP Server ist der zentrale Einstiegspunkt für AI-Assistenten.
Er bietet strukturierten Zugriff auf:

- **Domain Management**: Domains auflisten, inspizieren, erstellen
- **Handler Framework**: Handler suchen, generieren, validieren
- **Refactoring**: Sessions tracken, Pfad-Schutz prüfen
- **Requirements**: Tasks/Bugs verwalten, Feedback synchronisieren
- **DevOps**: Sentry, Grafana, Chrome DevTools Integration
- **Code Delegation**: Einfache Tasks an Worker-LLMs delegieren

Installation
============

.. code-block:: bash

   cd packages/bfagent_mcp
   pip install -e .

Start
-----

.. code-block:: bash

   python -m bfagent_mcp.server
   # oder mit HTTP Transport
   python -m bfagent_mcp.server --transport http --port 8765

Tools
=====

Domain Management
-----------------

.. function:: bfagent_list_domains(status_filter?, include_handler_count?, include_phases?, response_format?)

   Liste aller BF Agent Domains mit Status und Handler-Anzahl.
   
   :param status_filter: production, beta, development, planned, deprecated
   :param include_handler_count: Handler-Anzahl anzeigen (default: true)
   :param include_phases: Phasen anzeigen (default: true)
   :param response_format: markdown oder json
   :return: Domain-Liste mit Details

.. function:: bfagent_get_domain(domain_id, include_handlers?, include_phases?, response_format?)

   Detaillierte Domain-Informationen inkl. Handler und Phasen.
   
   :param domain_id: Domain ID (z.B. 'books', 'cad')
   :return: Domain mit allen Details

Handler Framework
-----------------

.. function:: bfagent_search_handlers(query, domain_filter?, handler_type_filter?, limit?, response_format?)

   Suche nach Handlern über alle Domains.
   
   :param query: Suchbegriff (z.B. 'PDF parsing', 'character generation')
   :param handler_type_filter: ai_powered, rule_based, hybrid, utility
   :param limit: Max. Ergebnisse (1-50, default: 10)
   :return: Gefundene Handler mit Beschreibung

.. function:: bfagent_generate_handler(handler_name, domain, description, handler_type?, input_fields?, output_fields?, ai_provider?, include_tests?, use_ai_enhancement?)

   Generiert produktionsreifen Handler-Code mit Tests.
   
   :param handler_name: Name des Handlers
   :param domain: Ziel-Domain
   :param description: Was der Handler tun soll
   :param handler_type: ai_powered, rule_based, hybrid, utility
   :param ai_provider: openai, anthropic, ollama, none
   :return: Handler-Code, Tests, Registrierung

.. function:: bfagent_validate_handler(code, strict_mode?)

   Validiert Handler-Code gegen BF Agent Standards.
   
   :param code: Python-Code des Handlers
   :param strict_mode: Strikte Prüfung (default: false)
   :return: Score 0-100, gefundene Issues

.. function:: bfagent_scaffold_domain(domain_id, display_name, description, phases, initial_handlers?, include_admin?, include_tests?)

   Erstellt komplette Domain-Struktur mit Models, Admin, Handlers.
   
   :param domain_id: Eindeutige Domain-ID
   :param phases: Liste der Workflow-Phasen
   :return: Generierte Dateien und Registrierung

Best Practices
--------------

.. function:: bfagent_get_best_practices(topic, include_examples?, response_format?)

   Holt Best Practices für ein Thema.
   
   :param topic: handlers, pydantic, ai_integration, testing, error_handling, performance
   :return: Best Practices mit Code-Beispielen

Refactoring Tools
-----------------

.. function:: bfagent_get_refactor_options(domain_id, response_format?)

   Zeigt Refactoring-Optionen für eine Domain: Komponenten, Risiko, Dependencies.
   
   **Immer vor Refactoring aufrufen!**
   
   :param domain_id: Domain ID
   :return: Refactoring-Optionen mit Risiko-Level

.. function:: bfagent_check_path_protection(file_path, response_format?)

   Prüft ob ein Pfad geschützt ist.
   
   **Immer vor Datei-Änderungen aufrufen!**
   
   :param file_path: Dateipfad
   :return: Schutz-Status, Level, Grund

.. function:: bfagent_get_naming_convention(app_label, response_format?)

   Holt Naming Conventions für eine App.
   
   :param app_label: App-Label (z.B. 'books', 'core')
   :return: Tabellen-Präfixe, Klassen-Präfixe, Patterns

.. function:: bfagent_start_refactor_session(domain_id, components)

   Startet Refactoring-Session für Tracking.
   
   :param domain_id: Domain
   :param components: ['handler', 'service', 'model']
   :return: Session-ID

.. function:: bfagent_end_refactor_session(session_id, status?, summary?, files_changed?, lines_added?, lines_removed?)

   Beendet Refactoring-Session mit Statistiken.
   
   :param session_id: Session-ID von start_refactor_session
   :param status: completed, failed, cancelled
   :return: Zusammenfassung

Requirement Management
----------------------

.. function:: bfagent_get_requirement(requirement_id, include_feedback?)

   Holt Requirement-Details mit Feedback-Historie.
   
   :param requirement_id: UUID des Requirements
   :return: Requirement mit allen Details

.. function:: bfagent_update_requirement_status(requirement_id, status, notes?)

   Aktualisiert Requirement-Status.
   
   :param status: draft, ready, in_progress, done, completed, blocked, obsolete, archived
   :return: Aktualisiertes Requirement

.. function:: bfagent_record_task_result(requirement_id, success, summary, files_changed?, next_steps?)

   Zeichnet Task-Ergebnis auf. Automatisches Feedback + Status-Update.
   
   :param success: Erfolgreich abgeschlossen?
   :param summary: Was wurde gemacht?
   :param files_changed: Geänderte Dateien
   :return: Bestätigung

.. function:: bfagent_add_feedback(requirement_id, feedback_type, content)

   Fügt Feedback zu Requirement hinzu.
   
   :param feedback_type: comment, progress, blocker, question, solution
   :return: Feedback-ID

Initiative Management
---------------------

.. function:: bfagent_create_initiative(title, description, domain?, priority?, analysis?, concept?, tasks?, tags?)

   Erstellt Initiative (Epic/Concept) mit optionalen Tasks.
   
   :param domain: writing_hub, cad_hub, mcp_hub, control_center, etc.
   :param tasks: Liste von Tasks mit name, description, category, priority
   :return: Initiative mit generierten Requirements

.. function:: bfagent_get_initiative(initiative_id, include_requirements?)

   Holt Initiative-Details mit verknüpften Requirements.

.. function:: bfagent_check_workflow_rules(initiative_id?, requirement_id?, target_status?, rule_category?)

   Prüft Workflow-Regeln und Best Practices.
   
   :param rule_category: workflow, documentation, naming, activity, all

.. function:: bfagent_analyze_requirement(requirement_id, analysis_depth?)

   Analysiert Requirement auf Qualität und Machbarkeit.
   
   :param analysis_depth: quick, detailed
   :return: Analyse mit Empfehlungen

DevOps AI Tools
---------------

.. function:: bfagent_chrome_test_page(url)

   Testet Seite mit Chrome DevTools: Screenshot, Console-Errors, Network.
   
   :param url: URL (z.B. '/admin/writing_hub/scene/')
   :return: Test-Ergebnisse

.. function:: bfagent_chrome_measure_performance(url)

   Misst Performance-Metriken: LCP, FID, CLS.

.. function:: bfagent_sentry_capture_error(error_message, context?)

   Erfasst Fehler in Sentry.

.. function:: bfagent_sentry_get_stats()

   Holt Sentry-Statistiken.

.. function:: bfagent_grafana_create_dashboard()

   Erstellt Grafana Monitoring Dashboard.

.. function:: bfagent_grafana_get_alerts()

   Holt Grafana Alert-Konfiguration.

.. function:: bfagent_admin_ultimate_check(app_label?)

   Führt kompletten Admin Health Check durch.

Code Delegation
---------------

.. function:: bfagent_delegate_code(task_type, description, context?, model?)

   Delegiert Code-Generierung an Worker-LLMs.
   
   :param task_type: django_view, django_template, django_url, django_form, django_model, htmx_component, sql_query
   :param model: auto, deepseek-v3, gpt4o-mini, gemini-flash
   :return: Generierter Code

Session Tracking
----------------

.. function:: bfagent_log_user_request(user_request, mode?, context?)

   Loggt User-Request am Session-Start.
   
   :param mode: auto, route, ab, ac, default
   :return: Session-ID

.. function:: bfagent_log_session_end(summary, session_id?, success?)

   Loggt Session-Ende.

Documentation Tools
-------------------

.. function:: bfagent_scan_hub_docs(hub_name, response_format?)

   Scannt Hub auf Dokumentations-Status.
   
   :param hub_name: writing_hub, cad_hub, etc.
   :return: Docstring Coverage, undokumentierte Items

.. function:: bfagent_update_hub_docs(hub_name)

   Aktualisiert Hub-Dokumentation aus Docstrings.

.. function:: bfagent_list_undocumented(hub_name)

   Listet undokumentierte Klassen/Funktionen.

.. function:: bfagent_docs_analyze_legacy(legacy_path?, include_subdirs?)

   Analysiert Legacy-Dokumentation für Migration.

.. function:: bfagent_docs_migrate_file(source, target, delete_source?)

   Migriert einzelne Dokumentations-Datei.

.. function:: bfagent_docs_check_duplicates(legacy_path?, sphinx_path?)

   Prüft auf Duplikate zwischen Legacy und Sphinx Docs.

Template Tools
--------------

.. function:: bfagent_find_duplicate_templates(template_path?)

   Findet doppelte Django Templates.

.. function:: bfagent_cleanup_duplicate_templates(dry_run?, keep_source?)

   Bereinigt doppelte Templates mit Backup.

.. function:: bfagent_restore_template_backup(backup_dir)

   Stellt Templates aus Backup wieder her.

Django Shell
------------

.. function:: bfagent_django_shell(code, timeout?)

   Führt Python-Code in Django Shell aus.
   
   :param code: Python-Code (mehrzeilig möglich)
   :param timeout: Timeout in Sekunden (default: 30)
   :return: Ausgabe

.. function:: bfagent_django_query(model, action?, filter_kwargs?, limit?)

   Führt einfache Django ORM Query aus.
   
   :param model: Model-Pfad (z.B. 'apps.bfagent.models.LLMUsageLog')
   :param action: count, first, last, all, filter
   :return: Query-Ergebnis

Beispiele
=========

Domain-Übersicht
----------------

.. code-block:: python

   # Alle Production Domains
   bfagent_list_domains(status_filter="production")
   
   # Domain-Details mit Handlern
   bfagent_get_domain(domain_id="books", include_handlers=True)

Handler entwickeln
------------------

.. code-block:: python

   # Handler suchen
   bfagent_search_handlers(query="PDF parsing", limit=5)
   
   # Neuen Handler generieren
   bfagent_generate_handler(
       handler_name="DocumentParserHandler",
       domain="books",
       description="Parst Word/PDF Dokumente und extrahiert Text",
       handler_type="utility",
       input_fields=["file_path", "options"],
       output_fields=["text", "metadata", "pages"],
       include_tests=True
   )

Refactoring-Session
-------------------

.. code-block:: python

   # 1. Optionen prüfen
   bfagent_get_refactor_options(domain_id="books")
   
   # 2. Pfad-Schutz prüfen
   bfagent_check_path_protection(file_path="apps/books/handlers/chapter_handler.py")
   
   # 3. Session starten
   session = bfagent_start_refactor_session(
       domain_id="books",
       components=["handler", "service"]
   )
   
   # 4. Änderungen durchführen...
   
   # 5. Session beenden
   bfagent_end_refactor_session(
       session_id=session["session_id"],
       status="completed",
       summary="Handler refactored to use new service layer",
       files_changed=3,
       lines_added=150,
       lines_removed=80
   )

Task-Workflow
-------------

.. code-block:: python

   # 1. Request loggen
   bfagent_log_user_request(
       user_request="Fix bug in chapter handler",
       mode="auto"
   )
   
   # 2. Arbeiten...
   
   # 3. Fortschritt melden
   bfagent_add_feedback(
       requirement_id="uuid-here",
       feedback_type="progress",
       content="Root cause identified: missing null check"
   )
   
   # 4. Ergebnis aufzeichnen
   bfagent_record_task_result(
       requirement_id="uuid-here",
       success=True,
       summary="Fixed null check in chapter handler",
       files_changed=["apps/books/handlers/chapter_handler.py"]
   )
