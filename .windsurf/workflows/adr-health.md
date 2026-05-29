---
description: Full ADR Health Audit — Schema, Staleness, Freshness, Redundancy, Compliance in einem Durchlauf
---

# /adr-health — Full ADR Audit Pipeline

> **Wann:** Wöchentlich, vor Releases, nach größeren Architektur-Änderungen.
> **Zweck:** Vollständiger Gesundheitscheck aller 158+ ADRs in einem Workflow.
> **iil-adrfw:** v0.4.0+ (12 MCP Tools)

## Verwendung

```
/adr-health [REPO]
```

| Argument | Beschreibung | Default |
|----------|-------------|---------|
| `REPO` | Repo für Freshness-Check | Auto-Detect via Git-Root |

---

## Phase 1: Schema + Validation

```
MCP: mcp2_adr_validate()
→ Alle ADRs gegen Schema v3 prüfen
→ Erwartung: 100% passed, 0 failures
→ Bei Failures: sofort fixen (Frontmatter-Fehler)
```

---

## Phase 2: Constitution Health Audit

```
MCP: mcp2_adr_audit(auditors=["supersession_hygiene","dependency_health","staleness","redundancy_detector","conflict","coverage","open_question_aging"])
→ ALLE 7 Auditors in einem Call
→ Health Score melden (Ziel: >= 0.95)
```

| Score | Bewertung | Aktion |
|-------|-----------|--------|
| >= 0.98 | Excellent | Keine Aktion nötig |
| 0.95-0.97 | Good | Info-Findings optional beheben |
| 0.90-0.94 | Warning | Warning-Findings sollten behoben werden |
| < 0.90 | Critical | Sofort beheben — Architektur-Drift! |

**Besonders beachten:**
- `redundancy_detector`: Konsolidierungs-Kandidaten → User fragen ob ADRs gemerged werden sollen
- `open_question_aging`: Offene Fragen die seit >3 Monaten ungeklärt sind → Eskalation
- `conflict`: ADR-Paare die sich widersprechen → sofort lösen

---

## Phase 3: Staleness + Review-Status

```
MCP: mcp2_adr_staleness(months=6)
→ ADRs die seit >6 Monaten nicht reviewed wurden
→ ADRs ohne last_reviewed Datum
→ Broken refs (superseded_by/depends_on zeigt auf nicht-existentes ADR)
```

Für jedes Finding:
- **Missing review**: Datum setzen oder Review einplanen
- **Broken ref**: Referenz korrigieren oder entfernen
- **Stale**: Inhalt prüfen — noch aktuell? Dann `last_reviewed` updaten

---

## Phase 4: Content Freshness (Repo-spezifisch)

```
MCP: mcp2_adr_freshness(repo_path="${GITHUB_DIR}/<REPO>")
→ Prüft Claims (Versionen, Ports, Images) gegen tatsächlichen Repo-Stand
→ Nur ADRs die für dieses Repo relevant sind (consumers/repo Filter)
```

| Finding | Aktion |
|---------|--------|
| Version-Drift (warning) | ADR aktualisieren oder PR für Version-Bump |
| Port-Abweichung (info) | Nur wenn eigener Port betroffen |
| Image-Mismatch (warning) | Docker-Image-Referenz in ADR updaten |

**Multi-Repo Scan** (optional, für Platform-weiten Check):
```bash
for repo in dev-hub risk-hub travel-beat bfagent weltenhub; do
  echo "=== $repo ==="
  # MCP: mcp2_adr_freshness(repo_path="${GITHUB_DIR}/$repo")
done
```

---

## Phase 5: Temporal Diff (Was hat sich geändert?)

```
MCP: mcp2_adr_diff(mode="temporal", left_time="<letzte-session>", right_time="<jetzt>")
→ Zeigt: neue ADRs, Status-Änderungen, Supersession-Ketten seit letztem Check
→ Nützlich für "Was hat sich in der Architektur letzte Woche geändert?"
```

---

## Phase 6: Report generieren

Zusammenfassung als Markdown:

```markdown
# ADR Health Report — <DATUM>

## Metrics
- **ADRs total**: X (Y accepted, Z proposed)
- **Schema**: 100% valid
- **Health Score**: 0.XX
- **Stale ADRs**: N
- **Freshness Warnings**: M (für <REPO>)

## Findings
### Critical
- (none / aufgelistete Findings)

### Warnings
- ADR-022: PostgreSQL 15 → actual 16 (Freshness)
- ADR-109/ADR-110: Consolidation candidate (Redundancy)

### Info
- ADR-172: missing last_reviewed
```

→ Report dem User präsentieren.
→ Optional in Outline speichern: `mcp4_create_concept(title="ADR Health Report <DATUM>", content=report)`
→ Optional als GitHub Issue: `mcp1_create_issue(title="[adr-health] X Findings from <DATUM>")`

---

## Automatisierung

Dieser Workflow kann als **Step 0.4.3** in `/session-start` eingebaut werden (weekly trigger):

```python
from datetime import datetime, timedelta
last_health = memory.get("adr_health_last_run")
if not last_health or (datetime.now() - last_health) > timedelta(days=7):
    # Run /adr-health
    pass
```
