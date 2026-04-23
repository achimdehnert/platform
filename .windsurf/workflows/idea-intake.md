---
description: Outline Inbox lesen, rohe Ideen erkennen, Template ausfüllen, Outline aktualisieren
---

# /idea-intake — Ideen aus Outline Inbox verarbeiten

Der User legt Ideen als kurze Sätze in der **Outline Inbox Collection** an (auch mobil).
Dieser Workflow liest die Inbox, erkennt rohe/unvollständige Ideen und füllt sie strukturiert aus.

## Kontext

- **Inbox Collection ID**: `b9c34816-3068-460f-8647-d4b4b58ca608`
- **Template ID**: `7be08775-4ca5-4baf-a9e8-5926012a7f64`
- **Outline URL**: https://knowledge.iil.pet
- **MCP**: outline-knowledge (<outline-mcp>_search_knowledge, <outline-mcp>_get_document, <outline-mcp>_update_document)

## Workflow-Schritte

### 1. Inbox Collection durchsuchen

Suche alle Dokumente in der Inbox Collection:

```
<outline-mcp>_search_knowledge(query="*", collection="b9c34816-3068-460f-8647-d4b4b58ca608")
```

Alternativ `<outline-mcp>_list_recent(collection="b9c34816-3068-460f-8647-d4b4b58ca608")`.

### 2. Rohe Ideen identifizieren

Für jedes Dokument prüfen:
- **Roh** = Titel oder Text ist kurz (< 200 Zeichen), kein Template-Struktur erkennbar
- **Teilweise** = Template vorhanden, aber Felder leer (z.B. "Hub / Projekt" nicht ausgefüllt)
- **Vollständig** = Alle Template-Felder ausgefüllt → überspringen
- **Template selbst** = Titel enthält "Template" → überspringen

Dokument mit `<outline-mcp>_get_document(document_id=...)` vollständig laden.

### 3. Kontext recherchieren

Für jede rohe Idee:

a) **Hub erkennen**: Aus dem Satz Keywords extrahieren (risk, trading, travel, cad, pptx, wedding, billing, coach, illustration, weltenhub)
b) **Bestehenden Code prüfen**: `mcp14_get_project_facts(repo_name=...)` für erkannten Hub
c) **Verwandte ADRs suchen**: `<outline-mcp>_search_knowledge(query="[Idee-Keywords]")` in ADRs/Konzepten
d) **Priorität einschätzen**: Basierend auf Komplexität und Abhängigkeiten

### 4. Template ausfüllen

Für jede rohe Idee ein vollständiges Dokument generieren:

```markdown
# [Verbesserter Titel basierend auf dem Satz]

## Hub / Projekt
[Erkannter Hub]

## Problem / Motivation
[Aus dem Satz abgeleitet — was ist das Problem?]

## Ziel
[Was soll erreicht werden? Konkret formuliert]

## Unterlagen
- [ ] [Vorgeschlagene Unterlagen basierend auf der Idee]

## Priorität
[🔴 Hoch | 🟡 Mittel | 🟢 Niedrig] — mit Begründung

## Notizen
- Verwandte ADRs: [gefundene ADRs]
- Bestehender Code: [relevante Module/Dateien]
- Abhängigkeiten: [andere Features/Hubs]
- Geschätzter Aufwand: [grob]

## Status
🔍 In Analyse

---
*Statuswerte: 📋 Idee → 🔍 In Analyse → 📐 ADR erstellt → 🚀 In Umsetzung → ✅ Done*
*Ursprüngliche Idee: "[Original-Satz des Users]"*
```

### 5. Outline-Dokument aktualisieren

```
<outline-mcp>_update_document(document_id=..., content=..., title=...)
```

- Titel verbessern (aussagekräftig)
- Template-Inhalt einfügen
- Status auf "🔍 In Analyse" setzen
- Original-Satz des Users als Fußnote erhalten

### 6. Zusammenfassung an User

Nach Verarbeitung aller Ideen dem User eine Zusammenfassung geben:

```
## Inbox verarbeitet

| # | Idee | Hub | Priorität | Aktion |
|---|------|-----|-----------|--------|
| 1 | PDF-Export Risiko-Berichte | risk-hub | 🟡 Mittel | Template ausgefüllt |
| 2 | Dashboard-Redesign | risk-hub | 🔴 Hoch | Template ausgefüllt, ADR vorgeschlagen |

Nächste Schritte:
- [ ] Idee 1: ADR erstellen?
- [ ] Idee 2: GitHub Issue anlegen?
```

### 7. Optionale Folgeaktionen (nur auf Wunsch des Users)

- **ADR erstellen**: `/adr` Workflow mit Idee als Input
- **GitHub Issue**: `mcp8_create_issue` mit strukturiertem Body
- **Implementierung starten**: `/agentic-coding` mit Idee als Task

## Regeln

- **Niemals** Ideen löschen — nur ergänzen
- **Original-Satz** immer als Fußnote erhalten
- **Template-Dokument** (ID `7be08775-...`) nicht verändern
- **Status** beim Ausfüllen auf "🔍 In Analyse" setzen (nicht weiter)
- Bei Unklarheiten: **User fragen**, nicht raten
- Priorität ist nur ein Vorschlag — User entscheidet
