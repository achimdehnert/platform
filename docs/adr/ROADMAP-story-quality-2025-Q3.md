# Roadmap: Story-Qualitätsoffensive 2025-Q3

| Metadata    | Value                                                              |
|-------------|--------------------------------------------------------------------|
| **Datum**   | 2025-06-12                                                         |
| **Autor**   | Cascade AI / achimdehnert                                          |
| **Scope**   | travel-beat, weltenhub, bfagent, platform                          |
| **ADRs**    | ADR-025-tb, ADR-026-tb, ADR-024-platform                          |

---

## 1. Motivation

Die Story-Generierung in travel-beat produziert Geschichten mit:

- **Fehlenden Orten** (~37% der Stopps nicht in der Story)
- **Generischen Beschreibungen** (keine realen POIs, Restaurants, Straßen)
- **Isolierten Szenen** (kein übergreifender Handlungsbogen)
- **Unverhältnismäßiger Kapitelverteilung** (11 Kapitel für einen Ort, 0 für andere)
- **Fehlenden Transport-Erlebnissen** (Langstreckenflüge nicht narrativ genutzt)

Drei ADRs adressieren diese Probleme auf verschiedenen Ebenen:

| ADR | Repo | Kern | Löst |
|-----|------|------|------|
| **ADR-025** | travel-beat | 3-Phasen-Pipeline (Storyline → Outline → Kapitel) | Fehlende Orte, isolierte Szenen, Kapitelverteilung |
| **ADR-026** | travel-beat | Smart Location Enrichment v2 (POIs, Trip-Typ) | Generische Beschreibungen, fehlende lokale Details |
| **ADR-024** | platform | Recherche-Hub & Weltenhub Integration | Tiefe Orts-Recherche, Caching, Cross-App Wiederverwendung |

---

## 2. Abhängigkeiten

```text
ADR-024 (Recherche-Hub)
    │
    ▼
ADR-026 (Enrichment v2)  ←── liefert POI-Daten, nutzt Weltenhub-Cache
    │
    ▼
ADR-025 (3-Phasen-Pipeline)  ←── konsumiert angereicherte Daten
```

**Kritischer Pfad:** ADR-025 und ADR-026 können parallel gestartet werden. ADR-024 ist eine Erweiterung, die die Qualität weiter steigert, aber nicht blockierend ist.

---

## 3. Phasen

### Phase 1: Foundation (Woche 1-2)

**Ziel:** Kapitelstruktur und Enrichment-Basis verbessern.

| # | Task | ADR | Repo | Aufwand | Abhängigkeit |
|---|------|-----|------|---------|-------------|
| 1.1 | `ChapterConsolidator` — Stop-Konsolidierung | 025 | travel-beat | 2 Tage | — |
| 1.2 | `Storyline` Model + Migration | 025 | travel-beat | 1 Tag | — |
| 1.3 | `OverpassPOIService` — reale POIs | 026 | travel-beat | 2 Tage | — |
| 1.4 | `TRIP_TYPE_POI_PROFILES` | 026 | travel-beat | 0.5 Tag | — |
| 1.5 | Tests für 1.1-1.4 | — | travel-beat | 1.5 Tage | 1.1-1.4 |

**Deliverable:** Kapitel-Konsolidierung funktioniert deterministisch, POIs werden aus OSM geladen.

### Phase 2: Storyline & Enrichment (Woche 3-4)

**Ziel:** LLM-basierte Storyline-Generierung und erweiterte Enrichment-Pipeline.

| # | Task | ADR | Repo | Aufwand | Abhängigkeit |
|---|------|-----|------|---------|-------------|
| 2.1 | `StorylineGenerator` Service + Prompt | 025 | travel-beat | 2 Tage | 1.2 |
| 2.2 | `CultureServiceV2` (LLM-Fallback) | 026 | travel-beat | 1 Tag | — |
| 2.3 | `POINarrativeEnricher` (LLM-Hints) | 026 | travel-beat | 1 Tag | 1.3 |
| 2.4 | Pipeline v2 Integration (POI-Stufe) | 026 | travel-beat | 1 Tag | 1.3, 2.2, 2.3 |
| 2.5 | Sofort-Enrichment bei Stop-Import | 026 | travel-beat | 1 Tag | 2.4 |
| 2.6 | Tests für 2.1-2.5 | — | travel-beat | 1.5 Tage | 2.1-2.5 |

**Deliverable:** Storyline wird generiert, Stops werden bei Import sofort mit POIs angereichert.

### Phase 3: Pipeline Integration (Woche 5-6)

**Ziel:** Alles zusammenführen — 3-Phasen-Pipeline end-to-end.

| # | Task | ADR | Repo | Aufwand | Abhängigkeit |
|---|------|-----|------|---------|-------------|
| 3.1 | Outline-Prompt v2 (nutzt Storyline) | 025 | travel-beat | 1 Tag | 2.1 |
| 3.2 | Kapitel-Prompt v2 (erweiterter Kontext) | 025 | travel-beat | 1 Tag | 3.1 |
| 3.3 | Orchestrator v3 (3-Phasen-Koordination) | 025 | travel-beat | 1 Tag | 3.1, 3.2, 2.4 |
| 3.4 | Bidirektionaler Kontext (prev + next) | 025 | travel-beat | 0.5 Tag | 3.3 |
| 3.5 | Integration-Test mit echtem Trip | — | travel-beat | 2 Tage | 3.1-3.4 |
| 3.6 | Deploy + Live-Test | — | travel-beat | 1 Tag | 3.5 |

**Deliverable:** Vollständige 3-Phasen-Pipeline deployed und getestet.

### Phase 4: Recherche-Hub (Woche 7-9)

**Ziel:** Weltenhub als Knowledge Repository, Recherche-Hub als Lieferant.

| # | Task | ADR | Repo | Aufwand | Abhängigkeit |
|---|------|-----|------|---------|-------------|
| 4.1 | Weltenhub: Location `research_data` Erweiterung | 024 | weltenhub | 1 Tag | — |
| 4.2 | Weltenhub: Research API-Endpoints | 024 | weltenhub | 1 Tag | 4.1 |
| 4.3 | bfagent: `apps/recherche/` Modul-Skeleton | 024 | bfagent | 1 Tag | — |
| 4.4 | bfagent: `LocationResearcher` Service | 024 | bfagent | 2 Tage | 4.3 |
| 4.5 | bfagent: REST API + Celery Task | 024 | bfagent | 1 Tag | 4.4 |
| 4.6 | Weltenhub: `ResearchTrigger` Service | 024 | weltenhub | 1 Tag | 4.2, 4.5 |
| 4.7 | travel-beat: Weltenhub-Cache-Layer in Enrichment | 024+026 | travel-beat | 1 Tag | 4.2 |
| 4.8 | Integration-Tests cross-repo | — | alle | 2 Tage | 4.1-4.7 |

**Deliverable:** Recherche-Hub enriched Weltenhub-Locations, travel-beat nutzt Cache.

### Phase 5: Polish & Optimization (Woche 10)

| # | Task | Repo | Aufwand |
|---|------|------|---------|
| 5.1 | Weltenhub UI: "Recherchieren"-Button | weltenhub | 1 Tag |
| 5.2 | travel-beat UI: Enrichment-Status in Trip-Detail | travel-beat | 0.5 Tag |
| 5.3 | Batch-Job: Nightly Research für unrecherchierte Locations | bfagent | 0.5 Tag |
| 5.4 | Metriken-Dashboard: Story-Qualität vorher/nachher | travel-beat | 1 Tag |
| 5.5 | Dokumentation aktualisieren | platform | 0.5 Tag |

---

## 4. Timeline (Gantt-Übersicht)

```text
Woche:  1    2    3    4    5    6    7    8    9    10
        ├────┤────┤────┤────┤────┤────┤────┤────┤────┤
Phase 1 ████████
Phase 2           ████████
Phase 3                     ████████
Phase 4                               ████████████
Phase 5                                              ████
```

**Gesamtdauer: ~10 Wochen** (bei ~2 Tage/Woche effektiver Arbeitszeit = ~20 Arbeitstage)

---

## 5. Aufwandszusammenfassung

| Phase | Aufwand | Repos |
|-------|---------|-------|
| Phase 1: Foundation | ~7 Tage | travel-beat |
| Phase 2: Storyline & Enrichment | ~7.5 Tage | travel-beat |
| Phase 3: Pipeline Integration | ~6.5 Tage | travel-beat |
| Phase 4: Recherche-Hub | ~10 Tage | weltenhub, bfagent, travel-beat |
| Phase 5: Polish | ~3.5 Tage | alle |
| **Gesamt** | **~34.5 Tage** | |

---

## 6. Erfolgskriterien

| Metrik | Vorher | Ziel (nach Phase 3) | Ziel (nach Phase 4) |
|--------|--------|---------------------|---------------------|
| Stopps in Story / Stopps gesamt | ~63% | **100%** | 100% |
| Kapitel mit realem Ortsbezug | ~10% | **60%** | **90%** |
| Max Kapitel pro Ort / Gesamt | 38% | **≤15%** | ≤15% |
| Kapitel mit Szenen-Übergang (Hook) | 0% | **100%** | 100% |
| Transport-Szenen pro Langstrecke | 0 | **≥1** | ≥1 |
| Unique Eröffnungsstile | ~3/8 | **≥6/8** | ≥6/8 |
| Ø LLM-Kosten pro Story | ~$0.90 | ~$0.78 | ~$2.46 (inkl. Recherche) |
| Recherche-Cache-Hit-Rate | — | — | **>50%** (nach 3 Monaten) |

---

## 7. Risikomanagement

| Risiko | Impact | Wahrscheinlichkeit | Mitigation |
|--------|--------|--------------------|-----------| 
| LLM-Kosten steigen durch 3 Phasen | Mittel | Hoch | Konsolidierung reduziert Kapitel: Netto-Kosten sinken |
| Overpass API wird instabil | Mittel | Niedrig | Fallback: LLM-only POIs |
| Recherche-Hub-Integration zu komplex | Hoch | Mittel | Phase 4 ist optional — Phase 1-3 liefern bereits 80% des Werts |
| Story-Qualität verbessert sich nicht messbar | Hoch | Niedrig | A/B-Test: alte vs. neue Pipeline auf gleichem Trip |
| Cross-Repo-Abhängigkeiten verlangsamen | Mittel | Mittel | Phase 1-3 sind rein travel-beat-intern, kein Cross-Repo |

---

## 8. Quick Wins — ✅ UMGESETZT (2025-06-12)

Alle Quick Wins wurden **vor** Start der Roadmap implementiert:

| # | Quick Win | Datei | Status |
|---|-----------|-------|--------|
| QW1 | `MAX_CHAPTERS_PER_STOP` von 4 auf **2** gesenkt | `chapter_planner.py:118` | ✅ Done |
| QW2 | Outline-Prompt: "5-8 Kapitel" → "1 Kapitel pro Reise-Stopp" + Konsolidierungs-/Transport-Regeln | `prompts/__init__.py:55-58` | ✅ Done |
| QW3 | Merge-Fallback: leere `summary`/`key_events` → auto-generiert aus Stadt + Fokusthemen | `orchestrator.py:482-498` | ✅ Done |
| QW4 | Transport-Lookup (Route, Dauer, Flugnr.) pro Kapitel in LLM-Prompt injiziert | `orchestrator.py:471-506, 281-289` | ✅ Done |

**Erwarteter Impact:**

- Kapitel-Inflation: **~35 → ~18-22 Kapitel** (QW1 + QW2)
- Leere Kapitel-Summaries: **~70% → ~0%** (QW3)
- Transport-Erwähnung: **0 → alle Langstrecken** (QW4)
- Test angepasst: `test_should_create_extra_chapters_for_long_stay` → `assert len(plans) == 2`

---

## 9. Entscheidungspunkte

| Zeitpunkt | Entscheidung | Optionen |
|-----------|-------------|----------|
| Nach Phase 1 | Recherche-Hub: bfagent-Modul oder neues Repo? | Evaluation basierend auf bfagent-Zustand |
| Nach Phase 3 | Phase 4 starten oder erst Story-Qualität messen? | Metriken-basierte Entscheidung |
| Nach Phase 4 | Recherche-Hub als MCP-Tool exponieren? | Wenn andere Apps (pptx-hub) Bedarf haben |
| Laufend | LLM-Modell für Recherche (Claude Haiku vs. Sonnet) | Kosten/Qualitäts-Tradeoff |
