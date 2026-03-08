---
description: Review Agent — automatisierter PR-Review gegen ADRs, Ruff, Bandit, Platform-Patterns (ADR-100)
---

# Agent Review Workflow

> **Rolle (ADR-100)**: Review Agent übernimmt systematische PR-Qualitätsprüfung.
> Cascade (Tech Lead) wird nur bei ADR-Compliance-Verstößen oder Gate-2-Decisions involviert.

---

## Wann verwenden

- Bei jedem PR gegen `main` (automatisch via GitHub Actions, sobald implementiert)
- Manuell: wenn du einen PR vor dem Merge reviewen willst
- Als Pre-Commit-Check für größere Änderungen

---

## Step 1: Gate-0-Checks (blockierend — kein Merge ohne grün)

```bash
# Ruff
ruff check . --output-format=github

# Bandit
bandit -r . -ll -q
```

Bei Fehlern → **sofort stoppen**, Developer benachrichtigen. Kein Weiter.

---

## Step 2: ADR-Compliance prüfen (Gate 1 — blockierend)

```python
# Via platform-context MCP
mcp12_check_violations(code_snippet=<diff>, file_type=<file_type>)
```

Prüft gegen alle aktiven ADR-Regeln:
- Keine Inline-Styles in Python-Views (ADR-048)
- Kein hardcoded SQL (ADR-022)
- Service-Layer-Pattern (ADR-041)
- Keine `os.environ` direkt in Views (ADR-045)

Bei Verletzung → Kommentar auf PR + Block.

---

## Step 3: Platform-Patterns (Gate 1 — blockierend)

```python
mcp12_get_banned_patterns(context="all")
```

Prüft auf bekannte Anti-Patterns:
- Direkter DB-Zugriff in Templates
- `print()` statt `logging`
- Hardcoded Credentials / URLs
- `except:` ohne Exception-Typ

---

## Step 4: Coverage-Delta (Warnung — kein Block)

```bash
# Coverage vor und nach dem Change vergleichen
coverage run -m pytest
coverage report --fail-under=0  # nur für Delta-Berechnung
```

Wenn Coverage sinkt → Warnung im PR-Kommentar, aber kein Block.

---

## Step 5: Migration-Safety (Warnung)

Prüft neue Migrations auf:
- `RunPython` ohne `reverse_code` → Warnung
- `ALTER TABLE` auf großen Tabellen → Warnung  
- `NOT NULL` ohne Default auf existierende Spalten → **Block**

```bash
grep -r "RunPython" apps/*/migrations/*.py
```

---

## Step 6: PR-Kommentar generieren

Review-Report als strukturierter PR-Kommentar:

```markdown
## Review Agent Report

### Gate-0 (Pflicht)
- Ruff: ✅ / ❌ N Fehler
- Bandit: ✅ / ❌ N Issues

### Gate-1 (Pflicht)
- ADR-Compliance: ✅ / ❌ Verstöße
- Platform-Patterns: ✅ / ❌ Anti-Patterns

### Warnungen
- Coverage-Delta: +X% / -X%
- Migration-Safety: ✅ / ⚠️ Details

### Ergebnis
✅ **APPROVED** — bereit für Tech Lead Review
❌ **CHANGES REQUESTED** — blockierende Issues (siehe oben)
```

---

## Cascade-Involvement (Tech Lead Gate 2)

Cascade wird **nur** involviert bei:
- ADR-Compliance-Verletzung die unklar ist (Grauzone)
- Neues Pattern das noch nicht in ADRs erfasst ist
- `coverage_delta < -5%` (signifikanter Rückgang)
- Migrations mit potenziellem Datenverlust

---

## Referenzen

- ADR-100: Erweitertes Agent-Team
- ADR-066: AI Engineering Squad
- ADR-081: Agent Guardrails & Code Safety
- `agent_team_config.yaml` → `review_agent`
- `/agentic-coding` → Step 6 (Guardian) wird durch Review Agent ergänzt
