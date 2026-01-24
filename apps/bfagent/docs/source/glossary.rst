Glossar
=======

.. glossary::
   :sorted:

   Handler
      Eine spezialisierte Komponente die eine einzelne Aufgabe im 
      Workflow ausführt. Handler folgen dem Drei-Phasen-Muster
      (Input → Processing → Output) und werden über die Handler Registry
      verwaltet.

   Domain
      Ein abgeschlossener Funktionsbereich innerhalb von BF Agent,
      z.B. Books, Comics, CAD Analysis. Jede Domain hat eigene
      Models, Handler und Konfigurationen.

   Zero-Hardcoding
      Architekturprinzip bei dem alle Konfigurationen in der Datenbank
      gespeichert werden. Ermöglicht Runtime-Änderungen ohne Code-Deployment.

   Handler Registry
      Zentrales Verzeichnis aller verfügbaren Handler mit ihrer
      Konfiguration, Status und Abhängigkeiten.

   Plugin
      Erweiterungsmodul das die Funktionalität von BF Agent erweitert.
      Plugins können eigene Handler, Models und APIs mitbringen.

   Context
      Strukturierte Daten die zwischen Handlern übergeben werden.
      Wird mit Pydantic-Schemas validiert.

   Workflow
      Eine Kette von Handlern die nacheinander oder parallel ausgeführt
      werden um eine komplexe Aufgabe zu erledigen.

   Three-Phase Pattern
      Das Standard-Verarbeitungsmuster für Handler bestehend aus:
      
      1. **Input Phase**: Validierung und Context-Building
      2. **Processing Phase**: Business Logic und AI-Integration
      3. **Output Phase**: Formatierung und Persistenz

   AI Provider
      Ein externer Dienst für KI-Funktionen wie Text- oder Bildgenerierung.
      BF Agent unterstützt OpenAI, Anthropic Claude und lokale LLMs via Ollama.

   n8n
      Visual Workflow Automation Tool das für komplexe Orchestrierungen
      und externe Integrationen verwendet wird.

   Citizen Developer
      Nicht-technische Benutzer die Workflows über UI-Interfaces
      (Django Admin, n8n) konfigurieren können ohne Code zu schreiben.

   Pydantic
      Python-Bibliothek für Datenvalidierung. Wird für alle Input/Output
      Schemas der Handler verwendet.

   Celery
      Distributed Task Queue für asynchrone Handler-Ausführung und
      Background Jobs.

   SSOT (Single Source of Truth)
      Prinzip dass Informationen nur an einer Stelle definiert werden.
      In BF Agent: Code-Docstrings als Quelle für API-Dokumentation.

   Transaction Safety
      Mechanismus der sicherstellt dass bei Fehlern alle Änderungen
      automatisch zurückgerollt werden.

   Audit Trail
      Lückenlose Protokollierung aller Aktionen für Compliance
      und Debugging.

   ExSchutz
      Domain für Explosionsschutz-Dokumentation nach deutschen
      Vorschriften (ATEX, BetrSichV).

   CAD
      Computer-Aided Design. Die CAD Domain analysiert technische
      Zeichnungen in verschiedenen Formaten (DXF, DWG, PDF).

   Speech Bubble
      Sprechblasen-System im Comic Creator für Dialoge und
      Erzähltext. Unterstützt verschiedene Stile (Speech, Thought,
      Narration, SFX).

   Panel
      Einzelnes Bild/Frame innerhalb einer Comic-Seite.

   Handler Chain
      Verkettung mehrerer Handler für komplexe Verarbeitungsabläufe.
      Wird automatisch oder manuell konfiguriert.

   Rate Limiting
      Beschränkung der API-Aufrufe pro Zeiteinheit zur Kostenkontrolle
      und Fair-Use.

   Caching
      Zwischenspeicherung von AI-Responses und berechneten Ergebnissen
      zur Performance-Optimierung und Kostensenkung.

   MCP (Model Context Protocol)
      Protokoll für die Integration von KI-Modellen in IDEs und
      Entwicklungstools.
