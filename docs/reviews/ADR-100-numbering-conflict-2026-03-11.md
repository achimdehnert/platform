# Review: ADR-100 Nummernkonflikt — 3 Dateien mit gleicher Nummer

| | |
|---|---|
| **Reviewer** | Cascade (IT-Architekt) |
| **Review-Datum** | 2026-03-11 |
| **Ergebnis** | ❌ CHANGES REQUESTED — 1 BLOCK (Nummernkonflikt) |

---

## [BLOCK] B1 — 3 ADRs mit Nummer 100

3 verschiedene ADRs tragen die Nummer ADR-100:

| Datei | Thema | Status | Datum |
|-------|-------|--------|-------|
| `ADR-100-iil-testkit-shared-test-factory-package.md` | iil-testkit PyPI Package | Accepted | 2026-03-05 |
| `ADR-100-iil-outlinefw-story-outline-framework.md` | iil-outlinefw Story Outlines | Accepted | 2026-03-08 |
| `ADR-100-extended-agent-team-deployment-agent.md` | Agent Team (deprecated) | Deprecated → ADR-107 | 2026-03-08 |

### Problem

ADR-Nummern müssen eindeutig sein (MADR-Standard). Die deprecated Variante ist
kein Problem (superseded by ADR-107), aber die beiden `Accepted` ADRs
(iil-testkit und iil-outlinefw) kollidieren.

### Empfohlener Fix

1. **ADR-100** bleibt `iil-testkit` (älteste, 2026-03-05, bereits auf PyPI publiziert)
2. `iil-outlinefw` bekommt eine neue Nummer — z.B. **ADR-121** (nächste freie Nummer)
3. `ADR-100-extended-agent-team-deployment-agent.md` kann gelöscht oder in
   `deprecated/` verschoben werden (bereits durch ADR-107 ersetzt)

---

## Gesamturteil

❌ **CHANGES REQUESTED** — Nummernkonflikt muss aufgelöst werden.
