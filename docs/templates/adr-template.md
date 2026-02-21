---
status: proposed
date: YYYY-MM-DD
decision-makers: Achim Dehnert
consulted: –
informed: –
---

<!--
  ADR-TEMPLATE v2.0 (2026-02-21)
  Basis: MADR 4.0 + Platform-Governance (ADR-021, ADR-046, ADR-054, ADR-059)
  Strategie: techdocs-first, dev-hub-sync, Drift-Detector-kompatibel

  PFLICHTFELDER: status, date, decision-makers, Titel, §1–§5, §9 Confirmation
  OPTIONALE FELDER: consulted, informed, §6 Migration Tracking (nur bei Transitions)

  HINWEIS: Dieses Template wird via techdocs in dev-hub synchronisiert.
  Änderungen an diesem Template → /adr Workflow ausführen.
-->

# ADR-NNN: [Entscheidung als aktiver Satz — "Adopt X for Y" nicht "X Architecture"]

## Metadaten

| Attribut        | Wert                                                                 |
|-----------------|----------------------------------------------------------------------|
| **Status**      | Proposed                                                             |
| **Scope**       | [platform \| service \| shared]                                      |
| **Erstellt**    | YYYY-MM-DD                                                           |
| **Autor**       | Achim Dehnert                                                        |
| **Reviewer**    | –                                                                    |
| **Supersedes**  | – (oder ADR-NNN: Titel)                                              |
| **Superseded by** | –                                                                  |
| **Relates to**  | ADR-NNN (Titel), ADR-NNN (Titel)                                     |

## Repo-Zugehörigkeit

<!--
  Welche Repos sind von dieser Entscheidung direkt betroffen?
  "Primär" = Repo wo die Änderung implementiert wird
  "Sekundär" = Repo das die Änderung konsumiert oder davon abhängt
  "Referenz" = Repo das nur dokumentarisch betroffen ist
  Bekannte Repos: platform, dev-hub, bfagent, cad-hub, travel-beat,
                  risk-hub, trading-hub, mcp-hub, weltenhub, pptx-hub
-->

| Repo           | Rolle      | Betroffene Pfade / Komponenten              |
|----------------|------------|---------------------------------------------|
| `platform`     | Referenz   | `docs/adr/`, `.windsurf/workflows/`         |
| `[repo-name]`  | Primär     | `[pfad/zur/komponente]`                     |
| `[repo-name]`  | Sekundär   | `[pfad/zur/komponente]`                     |

---

## Decision Drivers

<!--
  Warum wird diese Entscheidung jetzt getroffen?
  Konkrete Treiber: technische Schulden, Compliance, Skalierung, Governance.
  Mindestens 3, maximal 7 Bullet Points.
-->

- **[Treiber 1]**: [Begründung]
- **[Treiber 2]**: [Begründung]
- **[Treiber 3]**: [Begründung]

---

## 1. Context and Problem Statement

<!--
  Was ist das Problem? Warum reicht der Status quo nicht aus?
  Referenziere bestehende ADRs wenn relevant.
  Max. 3 Absätze + optionale Tabelle.
-->

[Problembeschreibung]

### 1.1 Ist-Zustand

[Beschreibung des aktuellen Zustands, ggf. mit Tabelle]

### 1.2 Warum jetzt

[Konkreter Auslöser für diese Entscheidung]

---

## 2. Considered Options

<!--
  Mindestens 3 Optionen. Option A ist immer die gewählte.
  Jede Option mit kurzem Pros/Cons-Block.
-->

### Option A: [Gewählte Option] ✅

**Pros:**
- [Pro 1]
- [Pro 2]

**Cons:**
- [Con 1]

### Option B: [Alternative]

**Pros:**
- [Pro 1]

**Cons:**
- [Con 1] → **Abgelehnt weil:** [Grund]

### Option C: [Alternative]

**Pros:**
- [Pro 1]

**Cons:**
- [Con 1] → **Abgelehnt weil:** [Grund]

---

## 3. Decision Outcome

**Gewählte Option: Option A — [Name]**

[Begründung in 2–4 Sätzen: Warum Option A, warum nicht B/C?]

---

## 4. Implementation Details

<!--
  Konkrete technische Details: Code-Snippets, Konfigurationen, Diagramme.
  Unterabschnitte nach Bedarf. Referenziere Repo-Zugehörigkeits-Tabelle (oben).
-->

### 4.1 [Komponente / Schritt]

```python
# Beispiel-Code
```

### 4.2 [Komponente / Schritt]

[Details]

---

## 5. Migration Tracking

<!--
  NUR ausfüllen wenn dieses ADR eine Transition über mehrere Repos/Services beschreibt.
  Status-Symbole: ⬜ Ausstehend | 🔄 In Progress | ✅ Abgeschlossen | ➖ Out of Scope
  Wird bei jedem Phase-Abschluss aktualisiert (Drift-Detector prüft Aktualität).
-->

| Repo / Service | Phase | Status | Datum | Notizen |
|----------------|-------|--------|-------|---------|
| `[repo]`       | 1     | ⬜ Ausstehend | – | – |
| `[repo]`       | 2     | ⬜ Ausstehend | – | – |

---

## 6. Consequences

### 6.1 Good

- [Positiver Effekt 1]
- [Positiver Effekt 2]

### 6.2 Bad

- [Trade-off 1]
- [Trade-off 2]

### 6.3 Nicht in Scope

- [Was bewusst ausgeschlossen wurde]

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| [Risiko 1] | Niedrig/Mittel/Hoch | Niedrig/Mittel/Hoch/Kritisch | [Maßnahme] |

---

## 8. Confirmation

<!--
  PFLICHT: Wie wird geprüft ob dieses ADR eingehalten wird?
  Mindestens 2 Mechanismen. Muss vom Drift-Detector (ADR-059) verifizierbar sein.
-->

1. **[Mechanismus 1]**: [Wie, wo, wann geprüft]
2. **[Mechanismus 2]**: [Wie, wo, wann geprüft]
3. **Drift-Detector**: Dieses ADR wird von ADR-059 auf Aktualität geprüft — Staleness-Schwelle: [6/12] Monate

---

## 9. More Information

<!--
  Links zu externen Ressourcen, verwandten ADRs, Konzeptpapieren.
  Verwandte ADRs sind bereits in der Metadaten-Tabelle oben verlinkt.
-->

- [Externe Ressource](https://...)
- ADR-NNN: [Titel] — [Beziehung]
- Konzeptpapier: [Titel] ([Datum])

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| YYYY-MM-DD | Achim Dehnert | Initial: Status Proposed |

---

<!--
  GOVERNANCE-HINWEISE (werden nicht in dev-hub angezeigt):

  Drift-Detector-Felder (ADR-059):
  - staleness_months: 12          ← Nach wie vielen Monaten ohne Update als "stale" markieren
  - drift_check_paths:            ← Pfade die der Drift-Detector auf Existenz prüft
      - [repo]/[pfad]
  - supersedes_check: true        ← Prüft ob referenzierte ADRs noch accepted/proposed sind

  techdocs-Sync:
  - Dieses ADR wird via sync_docs_from_github in dev-hub als DocPage gespeichert
  - Kategorie wird aus §Scope abgeleitet
  - Tags werden aus Decision Drivers extrahiert (automatisch)

  Review-Checkliste: /docs/templates/adr-review-checklist.md
  Template-Version: 2.0 (2026-02-21)
-->
