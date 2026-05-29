# ADR-Archivierbarkeit — Analyse-Report

> **Kein ADR, kein Index-Eintrag.** Reiner Analyse-Report (Dateiname bewusst
> ohne `ADR-NNN`-Präfix, damit ADR-Tooling/INDEX ihn nicht aufnimmt).
> Erstellt: 2026-05-17 · Autor: Achim Dehnert (via Claude Code)
> Auslöser: Frage „200 ADRs — nach dev/staging/prod aufteilbar?"

## Kontext & Kernaussage

Eine Aufteilung nach **dev/staging/prod ist die falsche Achse**: ADRs sind
umgebungs-agnostische Architektur-Entscheidungen. Die „Last" entsteht durch
Bulk-Load (3,4 MB / 80k Zeilen in einem flachen `docs/adr/`), nicht durch
fehlende Umgebungs-Trennung.

**Empfohlene Hebel (Reihenfolge):**

1. **Frontmatter-Norm** — kleiner als gedacht: Status-Werte sind konsistent,
   nur 3 Sonderfälle. (`status: "accepted"` ≡ `status: accepted` für YAML)
2. **Lifecycle-Split** — `archive/` für superseded/deprecated → Hot-Set ~9 % kleiner
3. **Retrieval statt Bulk-Load** — der eigentliche Last-Treiber; pgvector /
   `agent_memory_search` existiert bereits → dort investieren, nicht im Dateibaum

## Korpus (gemessen 2026-05-17)

173 Dateien (ohne `INDEX.md`) · **122 accepted · 26 proposed · 18 archivierbar**

## 1. Sauber archivierbar — Pointer vorhanden (8)

| ADR | Status | abgelöst von |
|---|---|---|
| ADR-009 Platform Architecture Optimized | superseded | ADR-120 |
| ADR-014 AI-Native Development Teams | superseded | ADR-066 |
| ADR-020 Dokumentationsstrategie | superseded | ADR-158 |
| ADR-027 Shared Backend Services | superseded | ADR-180 |
| ADR-053 deployment-mcp Robustness | superseded | ADR-075 |
| ADR-063 Staging Environment Strategy | superseded | ADR-157 |
| ADR-113 Telegram Gateway + pgvector | superseded | ADR-114 |
| ADR-136 Shared Backend Services (Original) | deprecated | ADR-131 |

## 2. ⚠️ Archivierbar, aber `superseded-by` FEHLT (8) — Hauptbefund

Tot, aber ohne Nachfolge-Pointer. Blind verschieben = Trail verloren.
**Vor Archivierung Pointer backfillen** (`superseded-by:` oder
`archived-reason:` wenn ersatzlos):

`ADR-008` Infrastructure · `ADR-013` Team Org & MCP Ownership ·
`ADR-017` DDL · `ADR-023` Shared Scoring/Routing · `ADR-032` DDL ·
`ADR-033` Dual-Framework-Governance · `ADR-047` Sphinx Hub ·
`ADR-054` Deployment Pre-Flight · `ADR-111` Private Package Distribution

## 3. Redundanz-Cluster

- **ADR-017 + ADR-032** — beide „Domain Development Lifecycle (DDL)",
  doppelte Entscheidung, beide tot → konsolidieren statt nur archivieren.
- **ADR-027 → ADR-180**, **ADR-136 → ADR-131** — „Shared Backend Services"
  4× in der Lineage (027/136/131/180), verworrene Kette → Klärungs-Notiz wert.

## 4. Sonderfälle — NICHT archivieren

| ADR | Status | Befund |
|---|---|---|
| ADR-205 SSL/Cert-Strategie | accepted-with-caveats | untracked WIP, aktiv → bleibt |
| ADR-200 iil-ui v1 | superseded-draft | untracked WIP, nicht in git → nur in v2 mergen |
| ADR-141 Discord→Agentic Bridge | draft | echter ADR, unfertig → erst entscheiden |

## Netto-Bilanz

Real: **8 sofort sauber**, **8 brauchen Pointer-Backfill**, **2 untracked WIP**
(raus aus Rechnung). Effektiver Hot-Set-Gewinn: ~16 Dateien (~9 %).
Größerer Hebel bleibt **Retrieval/Index (Schritt 3)**.

## Empfohlener nächster Schritt

8 Dangling-Pointer aus git-Historie / `supersedes`-Rückverweisen recherchieren,
dann **separater PR** nur mit Frontmatter-Backfill + `archive/`-Move — getrennt
von der aktuell im Repo liegenden fremden WIP (`print_agent`, `CHANGELOG`,
untracked ADR-200/205/206 auf Branch `docs/session-docu-cleanup`).
