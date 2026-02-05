# 🎯 ADR Triage Guide

## Wie finde ich den richtigen Scope?

### Entscheidungsbaum

```
                         Neues ADR
                             │
                             ▼
           ┌─────────────────────────────────┐
           │ Betrifft es INFRASTRUKTUR?      │
           │                                  │
           │ • CI/CD Pipelines               │
           │ • Deployment/Docker             │
           │ • Datenbank-Schema              │
           │ • Monitoring/Logging            │
           │ • Security/Auth-Infrastruktur   │
           └───────────────┬─────────────────┘
                           │
                  Ja ──────┴────── Nein
                   │                  │
                   ▼                  ▼
              ┌────────┐    ┌────────────────────────┐
              │ core/  │    │ Betrifft es MEHRERE    │
              │001-019 │    │ Apps (≥2)?             │
              └────────┘    └───────────┬────────────┘
                                        │
                               Ja ──────┴────── Nein
                                │                  │
                                ▼                  ▼
                           ┌─────────┐    ┌────────────────┐
                           │ shared/ │    │ WELCHE APP     │
                           │ 080-099 │    │ ist betroffen? │
                           └─────────┘    └───────┬────────┘
                                                  │
                    ┌─────────┬─────────┬─────────┼─────────┬─────────┬─────────┐
                    ▼         ▼         ▼         ▼         ▼         ▼         ▼
               ┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐
               │bfagent ││travel- ││mcp-hub ││risk-   ││cad-hub ││pptx-   ││ ???    │
               │020-029 ││beat    ││040-049 ││hub     ││060-069 ││hub     ││→shared │
               └────────┘│030-039 │└────────┘│050-059 │└────────┘│070-079 │└────────┘
                         └────────┘          └────────┘          └────────┘
```

---

## Scope-Definitionen

### 🏗️ Core (001-019)

**Wann?** Platform-weite Infrastruktur, betrifft ALLE Apps

| ✅ Gehört hierher | ❌ Gehört nicht hierher |
|-------------------|-------------------------|
| GitHub Actions / CI/CD | App-spezifische Business Logic |
| Deployment-Strategie | UI/UX Entscheidungen einer App |
| PostgreSQL Schema-Konventionen | Feature-Flags einer App |
| Docker/Container-Setup | API-Endpunkte einer App |
| Monitoring/Alerting | |
| Security-Policies | |
| Package-Struktur (platform_core) | |

---

### 🤖 BF Agent (020-029)

**Wann?** Nur die BF Agent Anwendung

| ✅ Gehört hierher | ❌ Gehört nicht hierher |
|-------------------|-------------------------|
| Agent Lifecycle | Shared Auth-System |
| Tool Execution Model | Deployment (→ core) |
| Memory Management | API Conventions (→ shared) |
| Conversation Flow | |

---

### ✈️ Travel-Beat (030-039)

**Wann?** Nur die Travel-Beat / Drifttales Anwendung

| ✅ Gehört hierher | ❌ Gehört nicht hierher |
|-------------------|-------------------------|
| Story Generation Engine | Content in anderen Apps |
| Timing Engine | Shared UI Components |
| Content Templates | |
| Trip Planning Logic | |

---

### 🔌 MCP-Hub (040-049)

**Wann?** Nur der MCP Hub

| ✅ Gehört hierher | ❌ Gehört nicht hierher |
|-------------------|-------------------------|
| Server Registry | MCP Protocol selbst |
| MCP Extensions | Wie andere Apps MCP nutzen |
| Server Discovery | |

---

### ⚠️ Risk-Hub (050-059)

**Wann?** Nur der Risk Hub

| ✅ Gehört hierher | ❌ Gehört nicht hierher |
|-------------------|-------------------------|
| Risk Scoring Models | Shared Reporting |
| Assessment Workflows | |
| Risk Categories | |

---

### 📐 CAD-Hub (060-069)

**Wann?** Nur der CAD Hub

| ✅ Gehört hierher | ❌ Gehört nicht hierher |
|-------------------|-------------------------|
| CAD Format Import/Export | File Storage (→ core) |
| Format Conversion | |
| CAD Viewer | |

---

### 📊 PPTX-Hub (070-079)

**Wann?** Nur der PPTX Hub

| ✅ Gehört hierher | ❌ Gehört nicht hierher |
|-------------------|-------------------------|
| Slide Generation | Template Storage |
| Template Engine | |
| Export Formats | |

---

### 🔗 Shared (080-099)

**Wann?** Betrifft ≥2 Apps, aber NICHT Infrastruktur

| ✅ Gehört hierher | ❌ Gehört nicht hierher |
|-------------------|-------------------------|
| API Versioning Convention | CI/CD (→ core) |
| Error Response Format | Deployment (→ core) |
| Logging Format | DB Schema (→ core) |
| Auth Token Format | App-spezifische Features |
| Shared UI Components | |

---

## Nummernkreise

| Scope | Bereich | Kapazität |
|-------|---------|-----------|
| core | 001-019 | 19 |
| bfagent | 020-029 | 10 |
| travel-beat | 030-039 | 10 |
| mcp-hub | 040-049 | 10 |
| risk-hub | 050-059 | 10 |
| cad-hub | 060-069 | 10 |
| pptx-hub | 070-079 | 10 |
| shared | 080-099 | 20 |
| **reserve** | 100-199 | 100 |

---

## Nächste Nummer finden

```bash
# Beispiel: Nächste freie Nummer in core/
ls docs/adr/core/ADR-*.md 2>/dev/null | sort -V | tail -1
# Output: ADR-011-xxx.md → Nächste: 012

# Oder mit Script:
python3 scripts/generate-adr-index.py --next-number core
```

---

## Grenzfälle

| Situation | Entscheidung |
|-----------|--------------|
| Betrifft 1 App + Infrastruktur | → `core/` (Infrastruktur hat Vorrang) |
| Betrifft 2 Apps | → `shared/` |
| Unsicher ob 1 oder 2 Apps | → `shared/` (kann später verschoben werden) |
| Neue App ohne eigenen Scope | → `shared/` oder neuen Scope beantragen |

---

## FAQ

**Q: Kann ich ein ADR später in einen anderen Scope verschieben?**
A: Ja, aber die Nummer bleibt gleich. Dokumentiere den Move im Changelog.

**Q: Was wenn ein Scope voll ist?**
A: Reserve-Bereich (100-199) nutzen oder Kapazität erweitern (in ADR-011).

**Q: Wer entscheidet den Scope bei Unklarheit?**
A: Im PR-Review klären. Im Zweifel: `shared/`.
