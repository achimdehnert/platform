# Kritischer Review: ADR-046 (Merged Version)

**Reviewer:** Cascade (AI)
**Datum:** 2026-02-18
**Version:** Post-Merge (ADR-046 + docs-agent-concept)
**Zeilen:** 384

---

## Verdict: BEDINGT ANGENOMMEN — 3 kritische, 5 substanzielle, 3 kleinere Issues

Das Merge-Ergebnis ist deutlich besser als die zwei separaten Dokumente.
Die Redundanzen sind bereinigt, die Konflikte aufgelöst. Aber es gibt
drei kritische Issues, die vor Acceptance gelöst werden MÜSSEN.

---

## Kritische Issues (K-01 bis K-03)

### K-01: `explanation/adr/` — Stille Migration mit massiven Konsequenzen

**Zeilen 113-116.** Die Verzeichnisstruktur verschiebt ADRs von `docs/adr/`
nach `docs/explanation/adr/`:

```text
├── explanation/
│   ├── adr/
│   │   └── _archive/
│   └── architecture/
```

**Problem:** Das ist die gravierendste Entscheidung im gesamten ADR, wird aber
als nebensächlicher Punkt in einem Verzeichnisbaum versteckt.

**Konsequenzen (nicht adressiert):**

- **Alle relativen Links brechen:** `./ADR-020-documentation-strategy.md`
  (Zeile 371) funktioniert nicht mehr nach Migration
- **Betrifft alle 10 Repos gleichzeitig** — kann nicht inkrementell migriert werden
- **Externe Referenzen** (README.md, Workflows, `.windsurf/rules/`) brechen
- **Git-History** für alle ADR-Dateien geht verloren (`git log --follow` nötig)
- **Im Implementation Plan nicht erwähnt** — Phase 2 beschreibt nur Cleanup,
  nicht die Struktur-Migration

**Empfehlung:** Entweder:

- **(A) ADRs bei `docs/adr/` belassen** (pragmatisch, kein Migrationsaufwand)
  und die Verzeichnisstruktur anpassen:

  ```text
  <repo>/docs/
  ├── adr/                  # Architecture Decision Records (Explanation-Quadrant)
  ├── tutorials/
  ├── guides/
  ├── reference/
  ├── explanation/          # Architektur, Design (ohne ADRs)
  └── _archive/
  ```

- **(B) Migration explizit planen** — eigene Phase im Plan, Link-Rewrites,
  sed-Script, alle Repos gleichzeitig, Aufwand ~2h pro Repo

### K-02: "Supersedes" vs. "Deferred" — Metadata-Widerspruch

**Zeile 9:** `Supersedes | ADR-020 → Status: **Deferred**`

**Problem:** Per eigenem Lifecycle (Zeile 124-132) sind "Superseded" und "Deferred"
unterschiedliche Status:

- **Superseded**: "Ersetzt durch neuere ADR. Nicht mehr gültig."
- **Deferred**: "Pausiert, kann später reaktiviert werden."

Der ADR-Text (Zeile 85-86) sagt explizit: ADR-020 ist **Deferred** und
`source/` bleibt erhalten für spätere Reaktivierung. Das ist kein Supersede.

**Empfehlung:** Metadata ändern:

```markdown
| **Relation to ADR-020** | ADR-020 → Status: **Deferred** (Sphinx deferred, DB-Docs adoptiert) |
```

Oder präziser: ADR-046 **partially supersedes** ADR-020 (DB-Docs-Konzept
übernommen, Sphinx-Teil deferred). Das sollte im Text erklärt werden.

### K-03: ADR verletzt eigene Regel R-01

**Zeile 138:** "Eine ADR-Nummer = Eine aktive Datei."

Aber ADR-046 trifft **zwei fundamentally separate Entscheidungen:**

1. **Documentation Hygiene** (Section 2) — Regeln, Struktur, Lifecycle
2. **Docs Agent** (Section 3) — Tooling, LLM-Integration, CLI

Das sind zwei verschiedene Concern-Ebenen:
- Hygiene = **Governance** (was DARF in docs/)
- Agent = **Tooling** (was AUTOMATISIERT docs/)

Man kann Hygiene ohne Agent haben. Man kann den Agent ändern ohne Hygiene
zu berühren. Die Kopplung ist künstlich.

**Empfehlung:** Zwei Optionen:

- **(A) Akzeptieren als "Compound ADR"** — explizit im Text erklären,
  dass R-01 sich auf ADR-*Nummern* bezieht, nicht auf die Anzahl Entscheidungen.
  Viele reale ADRs treffen mehrere verwandte Entscheidungen.
- **(B) Section 3 als ADR-047 auslagern** — sauberere Trennung, aber
  widerspricht dem expliziten Wunsch nach Vereinigung.

---

## Substanzielle Issues (S-01 bis S-05)

### S-01: Phase 1 ✅ bei Status "Proposed" — Prozess-Verletzung

**Zeile 272:** `Phase 1: Hygiene-Grundlagen ✅`

Implementation hat begonnen bevor die ADR akzeptiert ist. Das untergräbt
den ADR-Lifecycle. Wenn der ADR rejected wird, sind die .gitignore-Änderungen
bereits in 10 Repos committed.

**Empfehlung:** Status auf **Accepted** setzen (die Hygiene-Regeln sind
de facto bereits verbindlich), ODER das ✅ entfernen und Phase 1 als
"in Arbeit" markieren.

### S-02: Docstring-Coverage "~60% undokumentiert" — unbelegt

**Zeile 31:** Behauptet `~60%` undokumentiert.
**Zeile 359:** Setzt `~40%` als Vorher-Wert.

**Problem:** Keine Quelle, kein Scan-Ergebnis, keine Methodik. Könnte 30%
oder 80% sein. Auf dieser Zahl basiert das Ziel "80% Coverage" in Phase 4.

**Empfehlung:** Entweder:
- Schätzung kennzeichnen: "geschätzt ~40% (zu validieren in Phase 3 Audit)"
- Oder: Erst den AST-Scanner bauen (Phase 3), dann die Baseline messen

### S-03: .gitignore-Block fehlt im ADR

**Zeile 274:** Referenziert `.gitignore`-Block, aber der Block selbst ist
nicht mehr im ADR enthalten (war in der alten Version Section 3.2).

**Empfehlung:** Entweder den Block wieder einfügen (5 Zeilen), oder explizit
auf das Cleanup-Script verweisen: "siehe `adr046-cleanup.sh`".

### S-04: Cleanup-Script in `input/` — verstößt gegen R-05

**Zeile 287:** `platform/docs/adr/input/adr046-cleanup.sh`

Aber R-05 sagt: "Input nach Konsum archivieren." Das Script liegt in `input/`,
wird aber aktiv genutzt. Es ist kein "Input" sondern ein "Tool".

**Empfehlung:** Script nach `scripts/` oder `tools/` verschieben, oder
es als temporär kennzeichnen (löschen nach Cleanup).

### S-05: Drei LLM-Backend-Optionen ohne klare Priorisierung in Architektur

**Zeilen 179-181:** Architektur-Diagramm zeigt Options A/B/C gleichwertig.
**Zeile 249:** Tabelle sagt "llm_mcp primär, get_client() Fallback".

**Problem:** Widerspruch zwischen Diagramm (3 gleichwertige Optionen) und
Text (klare Priorisierung). Das Diagramm sollte die tatsächliche Entscheidung
widerspiegeln.

**Empfehlung:** Diagramm anpassen:

```text
│  │  Primär:   llm_mcp (MCP Tool, DB-backed)       │ │
│  │  Fallback: apps.core.services.llm.get_client()  │ │
```

---

## Kleinere Issues (M-01 bis M-03)

### M-01: "Scheduled" Modus fehlt im Implementation Plan

**Zeile 224:** Beschreibt "Scheduled" Modus (Celery Beat / Management Command).
Ist aber in keiner Phase geplant. Entweder streichen oder in Phase 5 aufnehmen.

### M-02: Kein Rollback-Plan für DIATAXIS-Struktur

Die Risiko-Tabelle (Zeile 342-347) deckt Agent-Risiken ab, aber nicht
das Risiko, dass die DIATAXIS-Struktur sich als unpraktisch erweist.

**Empfehlung:** Risiko hinzufügen: "DIATAXIS-Struktur zu granular für
kleine Repos" → Mitigation: "Flache Struktur erlaubt für Repos ohne docs/"

### M-03: Changelog nur mit Datum 2026-02-18

Vier Einträge am selben Tag wirken wie ein Draft-Log, nicht wie ein
ADR-Changelog. Bei Acceptance: auf einen Eintrag konsolidieren.

---

## Positiv-Bewertung (was gut gelungen ist)

| Aspekt | Bewertung |
| ------ | --------- |
| **Merge-Qualität** | Exzellent — 1354 → 384 Zeilen ohne Informationsverlust |
| **Konflikte aufgelöst** | howto/→guides/, creative-services→actual infra, Zeitaufwand realistisch |
| **DIATAXIS-Section** | Klar, prägnant, mit ASCII-Diagramm gut verständlich |
| **Tooling-Bausteine (1.2)** | Neu und wertvoll — zeigt erstmals die reale Infrastruktur |
| **Regeltabelle (2.3)** | Kompakt, scannbar, jede Regel mit Geltungsbereich |
| **Success Criteria (6)** | Messbar, phasenweise gestaffelt, realistisch |
| **Implementation Plan** | 5 Phasen statt 10, realistisch für Solo-Dev |

---

## Empfohlene Maßnahmen (priorisiert)

| # | Issue | Aufwand | Priorität |
| - | ----- | ------- | --------- |
| 1 | **K-01:** ADRs bei `docs/adr/` belassen (Option A) | 5 min | MUSS |
| 2 | **K-02:** Metadata korrigieren (Deferred ≠ Superseded) | 2 min | MUSS |
| 3 | **S-01:** Status → Accepted | 1 min | SOLL |
| 4 | **S-02:** Coverage-Zahl als Schätzung kennzeichnen | 1 min | SOLL |
| 5 | **S-05:** Architektur-Diagramm: klare LLM-Priorisierung | 3 min | SOLL |
| 6 | **K-03:** Compound-ADR explizit erklären | 2 min | KANN |
| 7 | **S-03:** .gitignore-Block referenzieren | 1 min | KANN |
| 8 | **M-03:** Changelog konsolidieren bei Acceptance | 2 min | KANN |

**Gesamt-Aufwand für alle Fixes: ~17 Minuten.**

Nach Umsetzung der MUSS-Items: **ANGENOMMEN.**
