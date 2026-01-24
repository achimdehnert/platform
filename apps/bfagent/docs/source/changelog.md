# Changelog

Alle wichtigen Änderungen an BF Agent werden hier dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und das Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

### Geplant
- MCP Server Integration für IDE-Support
- Erweitertes Plugin-System
- Coaching Hub Domain

---

## [2.0.0] - 2025-01-14

### Hinzugefügt
- **Handler Framework v2.0** mit Drei-Phasen-Verarbeitung
- Pydantic-Validierung für alle Handler
- Transaction Safety mit automatischem Rollback
- Comprehensive Audit Trails
- Multi-Provider AI Integration (OpenAI, Claude, Ollama)

### Geändert
- Migration von hardcodierten Konfigurationen zur Datenbank
- Neue Domain-Struktur mit geteilten Core-Komponenten
- Verbesserte Fehlerbehandlung mit strukturiertem Logging

### Entfernt
- Legacy Handler-System
- Deprecated API Endpoints v1

---

## [1.5.0] - 2024-11-01

### Hinzugefügt
- CAD Analysis Domain
- ExSchutz Domain (Beta)
- n8n Workflow Integration
- Comic Speech Bubble System

### Verbessert
- Performance-Optimierungen für Image Generation
- Bessere Error Messages

### Behoben
- Memory Leak in langen Workflow-Chains
- Race Condition bei parallelen Handlern

---

## [1.0.0] - 2024-06-15

### Hinzugefügt
- Initiale Version
- Book Domain mit vollständiger Workflow-Unterstützung
- Comic Domain (Basic)
- Django Admin Integration
- Basic AI Integration (OpenAI)

---

## Versions-Schema

```
MAJOR.MINOR.PATCH

MAJOR: Inkompatible API-Änderungen
MINOR: Neue Features (abwärtskompatibel)
PATCH: Bug Fixes (abwärtskompatibel)
```

## Migration Guides

### Von 1.x auf 2.0

```{warning}
Version 2.0 enthält Breaking Changes!
```

1. **Backup erstellen**
   ```bash
   python manage.py dumpdata > backup.json
   ```

2. **Dependencies aktualisieren**
   ```bash
   pip install -r requirements.txt
   ```

3. **Migrationen ausführen**
   ```bash
   python manage.py migrate
   ```

4. **Handler-Konfiguration migrieren**
   ```bash
   python manage.py migrate_handlers_v2
   ```

Siehe die Installationsanleitung für Details.
