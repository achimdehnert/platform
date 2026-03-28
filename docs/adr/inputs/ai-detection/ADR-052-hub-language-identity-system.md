---
status: proposed
date: 2026-03-27
decision-makers: Achim Dehnert
consulted: –
informed: –
---

<!-- Drift-Detector-Felder
staleness_months: 6
drift_check_paths:
  - tools/voice_dna/
  - hub_voice_dnas/
  - detection_patterns/text/
supersedes_check: –
-->

# ADR-052: Adopt Hub Language Identity System with AI-Resistant Voice DNA and Copy Mutation Engine

## Metadaten

| Attribut          | Wert                                                                              |
|-------------------|-----------------------------------------------------------------------------------|
| **Status**        | Proposed                                                                          |
| **Scope**         | platform                                                                          |
| **Erstellt**      | 2026-03-27                                                                        |
| **Autor**         | Achim Dehnert                                                                     |
| **Supersedes**    | –                                                                                 |
| **Relates to**    | ADR-051 (Hub Visual Identity System), ADR-049 (Design Token System), ADR-048 (HTMX Playbook) |

## Repo-Zugehörigkeit

| Repo             | Rolle    | Betroffene Pfade / Komponenten                               |
|------------------|----------|--------------------------------------------------------------|
| `platform`       | Primär   | `tools/voice_dna/`, `hub_voice_dnas/`, `detection_patterns/text/` |
| alle Hubs        | Sekundär | `locale/{de,en}/LC_MESSAGES/django.po`, `templates/`         |

---

## Decision Drivers

- **KI-Text-Erkennung wächst parallel zu Design-Erkennung**: Tools wie Originality.ai, GPTZero und Googles Helpful Content System erkennen generischen AI-Copy an Phrasen, Satzstruktur, Wortwiederholung und Tonalität — unabhängig vom visuellen Design.
- **12+ Hubs, eine Stimme**: Alle Hubs klingen identisch — gleiche Button-Labels, gleiche Fehlermeldungen, gleiche CTA-Phrasen. Kein Markencharakter, keine Differenzierung.
- **AI-Fingerprint-Phrasen dominieren**: "Erleben Sie", "Nahtlos integriert", "Leistungsstarke Lösung", "Jetzt loslegen" — klassische LLM-Output-Muster in Micro-Copy.
- **Django i18n fehlt Hub-Kontext**: Standardmäßige `.po`-Dateien sind hub-agnostisch. Gleicher `msgid` → gleicher `msgstr` in allen Hubs, obwohl bieterpilot anders klingen soll als DriftTales.
- **Reaktionsfähigkeit**: Neue Text-Erkennungsmuster müssen plattformweit sofort umsetzbar sein — nicht manuell pro Hub.
- **Python-first, Django-nativ**: Das System muss Django `gettext` / `.po` / `.mo` vollständig respektieren.

---

## 1. Context and Problem Statement

Parallel zum visuellen AI-Fingerprint (ADR-051) existiert ein **textueller AI-Fingerprint**. Während ADR-051 CSS-Tokens und Fonts schützt, schützt ADR-052 den tatsächlichen Inhalt: Buttons, Labels, Fehlermeldungen, Onboarding-Texte, Toasts und alle Micro-Copy-Elemente.

### 1.1 Bekannte AI-Text-Fingerprints (Stand 2026)

| Kategorie               | Beispiele                                                          | Gewichtung |
|-------------------------|--------------------------------------------------------------------|-----------|
| **Generische CTAs**     | "Jetzt loslegen", "Mehr erfahren", "Hier klicken", "Entdecken"    | 25%       |
| **AI-Filler-Phrasen**   | "nahtlos", "leistungsstark", "innovativ", "umfassend", "robust"   | 20%       |
| **Passiv-Konstruktionen** | "wird verarbeitet", "wurde erfolgreich abgeschlossen"            | 15%       |
| **Perfekte Parallelität** | Alle Bullet Points identisch strukturiert, gleiche Länge         | 15%       |
| **Generische Fehler**   | "Ein Fehler ist aufgetreten", "Etwas ist schiefgelaufen"          | 15%       |
| **LLM-Signaturphrasen** | "Es ist wichtig zu beachten", "Im Folgenden", "Zusammenfassend"   | 10%       |

### 1.2 Ist-Zustand

Alle Django-Templates verwenden identische Micro-Copy ohne Hub-Kontext. Die `locale/de/LC_MESSAGES/django.po` ist entweder leer oder enthält generische Übersetzungen.

### 1.3 Ziel

Ein **Hub Language Identity System** das:
- Jede Hub-Stimme in einer `hub-voice-dna.yaml` kodiert
- Deterministisch `.po`-Dateien (DE + EN) pro Hub generiert
- Den textuellen AI-Fingerprint-Score misst (0–100)
- Über Claude API neue Copy-Varianten generiert
- In Django `makemessages` / `compilemessages` integriert ist

---

## 2. Considered Options

### Option A — Manuell pro Hub
Redakteure pflegen `.po`-Dateien manuell per Hub. Kein System, keine Messbarkeit.

### Option B — Hub Voice DNA System mit Mutation Engine ✅ (gewählt)
Zentrales Python-Tool-Set analog zu ADR-051: DNA-Schema → Pipeline → `.po` → Audit → Mutation.

### Option C — Translation-Management-System (Phrase, Lokalise)
Externer SaaS-Dienst für Übersetzungsverwaltung.
**Cons:** Kosten, externe Abhängigkeit, kein AI-Fingerprint-Schutz, kein Mutation-Engine.

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                 HUB LANGUAGE IDENTITY SYSTEM                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  hub_voice_dnas/bieterpilot.yaml                                    │
│  ┌──────────────────────────────────────────┐                       │
│  │  tone: precise, authoritative, direct    │                       │
│  │  banned_words: [nahtlos, innovativ, ...]  │                       │
│  │  micro_copy:                             │                       │
│  │    de:                                   │                       │
│  │      cta_primary: "Ausschreibung starten"│                       │
│  │      error_generic: "Verbindung fehl."   │                       │
│  │    en:                                   │                       │
│  │      cta_primary: "Start tender"         │                       │
│  └──────────────┬───────────────────────────┘                       │
│                 ↓                                                    │
│  tools/voice_dna/pipeline.py                                        │
│  DNA → locale/de/LC_MESSAGES/django.po                              │
│      → locale/en/LC_MESSAGES/django.po                              │
│                 ↓                                                    │
│  tools/voice_dna/audit.py    (AI Text Fingerprint Score 0–100)      │
│                 ↓  Score >= 35                                       │
│  tools/voice_dna/mutate.py   (Claude API Mutation Engine)           │
│                                                                      │
│  .github/workflows/language-audit.yml  (PR-Gate, täglich)          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Decision Outcome

**Gewählt: Option B**. Begründung: Python-native, Django-kompatibel, selbes Governance-Modell wie ADR-051.

### 4.1 Confirmation

Diese ADR gilt als implementiert wenn:
1. `python -m tools.voice_dna audit --all` in CI läuft
2. Alle 14 Hubs haben Text-Fingerprint-Score `< 35`
3. `locale/{de,en}/LC_MESSAGES/django.po` wird pro Hub generiert
4. `language-audit.yml` läuft auf jedem PR
5. **Externe Validierung**: Mindestens 1 Hub vorher/nachher durch GPTZero oder Originality.ai Text Classifier getestet

> **Hinweis**: Der interne Text-Fingerprint-Score basiert auf einem eigenen Pattern-Katalog. Ohne externe Validierung ist er eine Heuristik. Die externe Validierung stellt sicher, dass der Score mit realer AI-Text-Erkennung korreliert.

### 4.2 `{% trans %}` Migrationsaufwand

Die `.po`-Pipeline generiert Dateien mit `msgid`s wie `"cta.primary"`. Das funktioniert nur, wenn Templates `{% trans "cta.primary" %}` verwenden. **Aktuell nutzt kein Hub `{% trans %}` für Micro-Copy** — Labels sind hartcodiert.

**Geschätzter Aufwand pro Hub:**

| Aufgabe | Aufwand |
|---------|---------|
| `base.html` + Nav: `{% trans %}` Tags einsetzen | ~1h |
| Formulare: Labels, Buttons, Hints umstellen | ~2h |
| Error-Templates + Toasts | ~1h |
| `compilemessages` + Smoketest | ~0.5h |
| **Summe pro Hub** | **~4.5h** |

**Gesamtaufwand für 14 Hubs: ~63h (≈ 8 Personentage)**

**Empfohlene Strategie**: Nicht alle 14 Hubs auf einmal, sondern:
1. **Pilot**: 1 Hub (z.B. risk-hub) vollständig auf `{% trans %}` migrieren
2. **Validieren**: `.po` deployen, Smoketest, externes AI-Detection-Tool testen
3. **Rollout**: Weitere Hubs in 2–3er Batches

### 4.3 Banned-Words Auto-Generierung

Die `banned_words_de/en` in den Hub-Voice-DNAs sollten automatisch aus `detection_patterns/text/ai_text_v1.yaml` abgeleitet werden, statt manuell pro Hub gepflegt. Der Pattern-Katalog hat 30+ Phrasen, die Hub-DNAs listen nur 6–7. Ein `sync_banned_words` Schritt in der Pipeline kann das automatisieren.

---

## 5. Migration Tracking

| Schritt                                        | Status     | Datum      |
|------------------------------------------------|------------|------------|
| ADR-052 erstellen                              | ✅ Done    | 2026-03-27 |
| `tools/voice_dna/schema.py` (Pydantic)         | ✅ Done    | 2026-03-27 |
| `tools/voice_dna/pipeline.py` (DNA → .po)      | ✅ Done    | 2026-03-27 |
| `tools/voice_dna/audit.py` (Text-Scorer)       | ✅ Done    | 2026-03-27 |
| `tools/voice_dna/mutate.py` (aifw)             | ✅ Done    | 2026-03-27 |
| `detection_patterns/text/ai_text_v1.yaml`       | ✅ Done    | 2026-03-27 |
| Alle 14 Hub Voice DNA YAMLs (de + en)          | ✅ Done    | 2026-03-27 |
| `language-audit.yml` GitHub Action             | ✅ Done    | 2026-03-27 |
| `django_voice_backend.py` (i18n Integration)   | ✅ Done    | 2026-03-27 |
| Pilot-Hub `{% trans %}` Migration (risk-hub)   | ⏳ Pending | –          |
| Externe Validierung (GPTZero o.ä.)             | ⏳ Pending | –          |
| Banned-Words Auto-Sync aus Patterns            | ⏳ Pending | –          |
| Integration in alle Hub-Repos (`.po` deployen) | ⏳ Pending | –          |
| CI-Gate Score-Threshold aktivieren             | ⏳ Pending | –          |

---

## 6. More Information

- ADR-051: Hub Visual Identity System — analoges System für CSS/Design
- ADR-049: Design Token System
- `tools/voice_dna/` — Implementierung
- `hub_voice_dnas/` — Source of Truth pro Hub
- Django i18n: https://docs.djangoproject.com/en/5.0/topics/i18n/translation/
