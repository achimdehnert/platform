# ADR Template — Deployment & Infrastructure Decisions

> **Verwendung**: Für ADRs die Deployment-Pipelines, Infrastruktur-Architektur,
> CI/CD-Systeme, Server-Operationen oder Tool-Auswahl für Ops-Aufgaben betreffen.
> Basiert auf MADR 4.0 + Platform Governance (ADR-021, ADR-056, ADR-065).

---

```yaml
---
status: "proposed"                          # proposed | accepted | deprecated | superseded
date: YYYY-MM-DD
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []                              # ["ADR-NNN-..."] wenn dieses ADR ein anderes ablöst
amends: []                                  # ["ADR-NNN-..."] wenn dieses ADR ein anderes ergänzt
related: []                                 # verwandte ADRs (keine Hierarchie)
---
```

---

# [Verb] [Objekt] — [kurze Beschreibung der Entscheidung]

> Titelformat: Aktiv-Verb + Objekt, z.B.:
> - "Adopt server-side execution for long-running deploy operations"
> - "Split deployment-mcp into read-only local tools and server-side workflows"
> - "Introduce infra-deploy as centralized deployment API"

---

## Context and Problem Statement

> **Was ist der technische/operative Kontext?**
> - Welches System/Tool ist betroffen?
> - Was funktioniert nicht oder fehlt?
> - Welche konkreten Symptome/Fehler wurden beobachtet?
> - Welche Constraints existieren (Sicherheit, Kosten, Latenz)?

**Problem**: [Ein-Satz-Problemformulierung]

### Betroffene Systeme

| System | Rolle | Aktueller Stand |
|--------|-------|----------------|
| `system-a` | Primär | Beschreibung |
| `system-b` | Sekundär | Beschreibung |

---

## Decision Drivers

> **Was sind die nicht-verhandelbaren Anforderungen?**
> Maximal 6 Treiber, jeder mit klarer Begründung.

- **[Treiber 1]**: Begründung
- **[Treiber 2]**: Begründung
- **[Treiber 3]**: Begründung

---

## Constraints & Non-Goals

> **Was ist explizit NICHT Teil dieser Entscheidung?**

### Constraints (unveränderlich)
- Server: Hetzner VM `88.198.191.108` (kein Wechsel)
- Registry: `ghcr.io/achimdehnert/` (kein Wechsel)
- Orchestration: Docker Compose per App (kein K8s)
- Auth: SSH Key `DEPLOY_SSH_KEY` (kein Token-basiertes System)

### Non-Goals
- [ ] [Was explizit nicht gelöst wird]
- [ ] [Was in einem späteren ADR behandelt wird]

---

## Considered Options

> **Mindestens 3 Optionen. Jede mit:**
> - Kurzbeschreibung (1 Satz)
> - Pro-Liste (konkret, nicht generisch)
> - Contra-Liste (konkret, nicht generisch)
> - Verworfungsgrund (wenn nicht gewählt)

### Option 1 — [Name] (gewählt / verworfen)

[Kurzbeschreibung]

**Pro:**
- [Konkreter Vorteil]
- [Konkreter Vorteil]

**Contra:**
- [Konkreter Nachteil]
- [Konkreter Nachteil]

**Entscheidung**: Gewählt / Verworfen weil: [Begründung]

---

### Option 2 — [Name] (verworfen)

[Kurzbeschreibung]

**Pro:**
- [Konkreter Vorteil]

**Contra:**
- [Konkreter Nachteil]

**Verworfen**: [Begründung]

---

### Option 3 — [Name] (verworfen)

[Kurzbeschreibung]

**Pro:**
- [Konkreter Vorteil]

**Contra:**
- [Konkreter Nachteil]

**Verworfen**: [Begründung]

---

## Decision Outcome

**Gewählt: Option N** — [Ein-Satz-Begründung]

### Positive Consequences

- [Konkreter Nutzen — messbar wenn möglich]
- [Konkreter Nutzen]

### Negative Consequences

- [Konkreter Nachteil — mit Mitigation]
- [Konkreter Nachteil]

---

## Implementation Details

> **Konkrete technische Spezifikation.**
> Für Deployment-ADRs: Architektur-Diagramm, Workflow-Sequenz, Konfiguration.

### Architektur

```
[ASCII-Diagramm der Lösung]
```

### Workflow-Sequenz

```
[Schritt-für-Schritt Ablauf mit Akteuren]
```

### Konfiguration / Schnittstellen

```yaml
# Relevante Konfiguration
```

### Security-Anforderungen

| Anforderung | Implementierung | Status |
|-------------|----------------|--------|
| Secrets nie in Logs | `--mask-value` / `add-mask` | ⬜ |
| Least-Privilege SSH | Dedizierter Deploy-User | ⬜ |
| Concurrent Deploy Protection | `concurrency:` in GitHub Actions | ⬜ |
| Audit Trail | Append-only `deploy.log` | ⬜ |

### Operational Runbook

| Szenario | Aktion | Befehl/Link |
|----------|--------|-------------|
| Manueller Deploy | GitHub Actions UI | `Actions → deploy-service → Run workflow` |
| Rollback | GitHub Actions UI | `Actions → rollback → Run workflow` |
| Deploy-Status prüfen | Server | `cat /opt/deploy/production/.deployed/<service>.tag` |
| Logs prüfen | Server | `tail -f /opt/deploy/production/.deployed/deploy.log` |

---

## Migration Tracking

| Schritt | Abhängigkeit | Status | Datum |
|---------|-------------|--------|-------|
| [Schritt 1] | — | ⬜ pending | — |
| [Schritt 2] | Schritt 1 | ⬜ pending | — |
| [Schritt 3] | Schritt 2 | ⬜ pending | — |

---

## Consequences

### Risks

| Risiko | Schwere | Wahrscheinlichkeit | Mitigation |
|--------|---------|-------------------|-----------|
| [Risiko] | HIGH/MEDIUM/LOW | HIGH/MEDIUM/LOW | [Mitigation] |

### Confirmation (messbare Kriterien)

> **Wie wird verifiziert, dass die Entscheidung korrekt umgesetzt wurde?**

- [ ] [Messbares Kriterium 1]
- [ ] [Messbares Kriterium 2]
- [ ] [Messbares Kriterium 3]

### Deprecation-Pfad (falls zutreffend)

| Was wird deprecated | Bis wann | Ersatz |
|--------------------|----------|--------|
| [Tool/Workflow] | [Datum/Release] | [Ersatz] |

---

## Best Practices Compliance

> **Checkliste gegen etablierte Deployment Best Practices.**

| Best Practice | Status | Notiz |
|--------------|--------|-------|
| Immutable Infrastructure (Tags statt `latest` in Prod) | ✅/⬜/❌ | |
| Health-Check nach jedem Deploy | ✅/⬜/❌ | |
| Automatischer Rollback bei Health-Check-Failure | ✅/⬜/❌ | |
| Concurrent Deploy Protection | ✅/⬜/❌ | |
| Audit Trail (append-only Log) | ✅/⬜/❌ | |
| Secrets nie in Logs/Outputs | ✅/⬜/❌ | |
| Idempotentes Deploy-Script | ✅/⬜/❌ | |
| Least-Privilege Principle | ✅/⬜/❌ | |
| Separate Deploy-User (nicht root) | ✅/⬜/❌ | |
| Pre-Deploy Backup (DB) bei Migrations | ✅/⬜/❌ | |

---

## Drift-Detector Governance Note

```yaml
paths:
  - [betroffene Pfade]
gate: NOTIFY | APPROVE | BLOCK
```
