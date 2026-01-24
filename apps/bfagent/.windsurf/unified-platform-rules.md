# Unified Platform Development Rules

## Migration Safety Rules

### CRITICAL: BookFactory Protection
- ❌ NIEMALS direkte Änderungen an bestehenden BookFactory Core-Files
- ✅ IMMER Adapter-Pattern für neue Interfaces verwenden
- ✅ Feature-Flags für alle neuen Funktionalitäten implementieren
- ✅ Rollback-Scripts für jede Migration bereithalten
- ✅ Minimum 95% Test-Coverage für alle Migrations-Schritte

### Backward Compatibility Rules
- ✅ Alle bestehenden APIs müssen funktionsfähig bleiben
- ✅ Database Schema nur durch Migrations erweitern, nie ändern
- ✅ UI-Komponenten durch Wrapper erweitern, nicht ersetzen
- ✅ Configuration-Files abwärtskompatibel halten
- ✅ Export-Formate unverändert unterstützen

### Quality Assurance Rules
- ✅ Separate Test-Suites für BookFactory + Unified Core + DHRW
- ✅ Integration Tests zwischen allen Komponenten
- ✅ Performance Regression Tests bei jeder Änderung
- ✅ User Acceptance Tests vor jeder Release
- ✅ Automated Rollback bei Test-Failures

### Development Workflow Rules
- ✅ Unified Platform Features nur in separate Branches entwickeln
- ✅ BookFactory Hotfixes haben höchste Priorität
- ✅ Code Reviews durch BookFactory + Unified Platform Teams
- ✅ Feature-Freeze für BookFactory während kritischer Migrations-Phasen
- ✅ Vollständige Dokumentation für alle Änderungen vor Implementation

## Implementation Guidelines

### Phase 1: Foundation Extraction (Wochen 1-6)
1. **Woche 1-2**: Repository-Struktur + Development Rules
2. **Woche 3-4**: Unified Core Library Grundstruktur
3. **Woche 5-6**: BookFactory Services abstrahieren (kopieren, nicht verschieben)

### Phase 2: Parallel Development (Wochen 7-18)
1. **Woche 7-10**: DHRW Manager auf Unified Core Basis
2. **Woche 11-14**: Cross-Domain Features entwickeln
3. **Woche 15-18**: Integration Tests + Performance Optimierung

### Phase 3: Gradual Integration (Wochen 19-34)
1. **Woche 19-22**: BookFactory Story Idea Agent auf Unified Core
2. **Woche 23-26**: BookFactory AI Agents migrieren
3. **Woche 27-30**: BookFactory Services migrieren
4. **Woche 31-34**: UI-Komponenten vereinheitlichen

### Phase 4: Enhancement (Wochen 35-42)
1. **Woche 35-38**: Cross-Domain Features aktivieren
2. **Woche 39-42**: Performance Optimierung + Documentation

## Success Metrics
- **BookFactory Uptime**: 99.9%+ während gesamter Migration
- **Performance**: Keine Verschlechterung der Response-Zeiten
- **Feature Parity**: 100% bestehende Features funktionsfähig
- **Test Coverage**: Minimum 95% für alle Komponenten
- **User Satisfaction**: Positive Feedback zu neuen Features
