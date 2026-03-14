---
status: "proposed"
date: 2026-03-14
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: ["ADR-143-knowledge-hub-outline-integration.md"]
related: ["ADR-143-knowledge-hub-outline-integration.md", "ADR-142-unified-identity-authentik-platform-idp.md", "ADR-132-ai-context-defense-in-depth.md", "ADR-114-discord-ide-like-communication-gateway.md", "ADR-116-dynamic-model-router.md"]
implementation_status: not_started
---

# ADR-145: Knowledge Management — Cascade ↔ Outline Anti-Knowledge-Drain

---

## 1. Kontext & Problemstellung

### 1.1 Das Knowledge-Drain-Problem

AI Coding Assistants (Cascade/Windsurf) generieren pro Session **enormes implizites Wissen**:

| Wissenstyp | Beispiel (aus OIDC-Session 2026-03-14) | Halbwertszeit |
|-------------|----------------------------------------|---------------|
| **Architektur-Entscheidungen** | "authentik braucht Signing Key + Scope Mappings auf jedem Provider" | Wochen |
| **Troubleshooting-Wissen** | "self-signed cert hinter Cloudflare Tunnel → NODE_TLS_REJECT_UNAUTHORIZED=0" | Monate |
| **Deployment-Patterns** | "extra_hosts: host-gateway für Container→Host→Nginx Routing" | Permanent |
| **Anti-Patterns** | "OIDC URIs: KEIN Slug im Pfad (/application/o/authorize/)" | Permanent |

Dieses Wissen existiert aktuell in **vier Silos**:

```
┌─────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE SILOS (Status Quo)              │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Chat-Verläufe│  │ Cascade      │  │ Entwickler-Kopf   │  │
│  │ (Windsurf)   │  │ Memories     │  │ (nicht skalierbar)│  │
│  │              │  │              │  │                    │  │
│  │ • Vergänglich│  │ • Kurze      │  │ • Single Point    │  │
│  │ • Nicht      │  │   Snippets   │  │   of Failure      │  │
│  │   durchsuch- │  │ • Nicht      │  │ • Nicht teilbar   │  │
│  │   bar        │  │   teilbar    │  │                    │  │
│  │ • Kontext    │  │ • Kein       │  │                    │  │
│  │   geht       │  │   Struktur-  │  │                    │  │
│  │   verloren   │  │   wissen     │  │                    │  │
│  └──────────────┘  └──────────────┘  └───────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ ADRs + Code (Git)                                     │    │
│  │ • Nur finales Ergebnis, nicht der Weg dorthin         │    │
│  │ • Kein Troubleshooting-Wissen, keine Lessons Learned  │    │
│  │ • Nicht von Cascade durchsuchbar (kein API-Zugriff)   │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Konkretes Problem: Session-Amnesie

**Szenario A — ohne Knowledge Hub:**
1. Session 1: OIDC-Integration debugging (3h) → Lösung gefunden
2. Session 2 (nächste Woche): doc-hub OIDC-Integration → gleiche Probleme, gleiches Debugging
3. Cascade hat Memories, aber: *"self-signed cert fix"* ist ein 10-Wort-Snippet — nicht das Runbook

**Szenario B — mit Knowledge Hub:**
1. Session 1: OIDC-Integration → Lösung als Runbook in Outline gespeichert
2. Session 2: `search_knowledge("OIDC authentik troubleshooting")` → Runbook gefunden → 10 Min statt 3h

### 1.3 Cascade Memory vs. strukturiertes Wissen

| Aspekt | Cascade Memory | Outline Knowledge Hub |
|--------|---------------|----------------------|
| **Format** | Kurze Text-Snippets (~500 Zeichen) | Vollständige Markdown-Dokumente |
| **Struktur** | Flach, Tag-basiert | Hierarchisch (Collections, Subcollections) |
| **Durchsuchbar** | Semantisch (Vektor) | Volltext + semantisch (AI-Keywords) |
| **Teilbar** | Nein (an Cascade-User gebunden) | Ja (OIDC-Login, Team-Zugang) |
| **Versioniert** | Nein | Ja (Outline hat Versionshistorie) |
| **Editierbar** | Nur via Cascade | Browser + API + Cascade |
| **Trigger** | Automatisch/manuell in Cascade | Bewusste Entscheidung |

**Beide ergänzen sich** — Memories für kurzfristigen Session-Kontext, Outline für langfristiges Strukturwissen.

---

## 2. Entscheidung

**Outline als Knowledge Hub für langfristiges, strukturiertes Wissen** — ergänzend zu Cascade Memories. Integration über drei Kanäle:

1. **Mensch → Outline**: Browser-Editor (knowledge.iil.pet)
2. **Cascade → Outline**: outline_mcp (MCP-Tools: suchen, lesen, schreiben)
3. **Outline → Cascade**: Session-Start-Ritual mit Knowledge-Lookup

### 2.1 Knowledge-Kategorien und Speicherort

| Kategorie | Speicherort | Trigger |
|-----------|-------------|---------|
| **Session-Kontext** (Variablennamen, aktuelle Aufgabe) | Cascade Memory | Automatisch |
| **Deployment-Facts** (Container, Ports, Domains) | Cascade Memory | Automatisch |
| **Runbooks** (Troubleshooting, Step-by-Step) | **Outline** | Manuell am Session-Ende |
| **Architektur-Konzepte** (Designs, Evaluationen) | **Outline** | Manuell beim Konzipieren |
| **Lessons Learned** (Anti-Patterns, Stolperfallen) | **Outline** | Manuell am Session-Ende |
| **ADR-Drafts** (in Arbeit) | **Outline** → Git | Manuell |
| **ADRs (final)** | Git (platform/docs/adr/) | Git-Workflow |
| **Hub-Dokumentation** (Setup, API, Konfiguration) | **Outline** | Bei Deployment/Änderungen |

---

## 3. Architektur: Knowledge-Loop

### 3.1 Der Knowledge-Loop

```
                    ┌──────────────────────────┐
                    │     SESSION START          │
                    │                            │
                    │  1. Cascade Memory laden   │
                    │  2. outline_mcp:           │
                    │     search_knowledge()     │
                    │     → relevante Runbooks   │
                    │     → Konzepte             │
                    └──────────┬─────────────────┘
                               │
                    ┌──────────▼─────────────────┐
                    │     ARBEITEN                │
                    │                            │
                    │  • Code schreiben          │
                    │  • Debugging               │
                    │  • Architektur-Entscheide  │
                    │  • Troubleshooting         │
                    └──────────┬─────────────────┘
                               │
                    ┌──────────▼─────────────────┐
                    │     SESSION ENDE            │
                    │                            │
                    │  3. Cascade Memory update   │
                    │  4. outline_mcp:            │
                    │     create_or_update_doc()  │
                    │     → Runbook               │
                    │     → Lessons Learned        │
                    │     → Konzept-Update         │
                    └──────────┬─────────────────┘
                               │
                    ┌──────────▼─────────────────┐
                    │     ASYNC ENRICHMENT        │
                    │                            │
                    │  5. Webhook → research-hub  │
                    │  6. Celery: AI-Summary      │
                    │  7. Celery: Keyword-Extract  │
                    │  8. Celery: ADR-Linking      │
                    └──────────────────────────────┘
```

### 3.2 outline_mcp — MCP Server Design

Registriert als `outline-knowledge` MCP-Server in Windsurf:

| Tool | Beschreibung | Wann nutzen |
|------|-------------|-------------|
| `search_knowledge(query, collection?, limit)` | Volltext + semantische Suche | Session-Start, vor neuer Aufgabe |
| `get_document(document_id)` | Vollständigen Markdown-Inhalt | Wenn Suchergebnis relevant |
| `create_runbook(title, content, related_adrs?)` | Neues Runbook in "Runbooks" Collection | Session-Ende nach Troubleshooting |
| `update_document(document_id, content)` | Bestehendes Dokument aktualisieren | Wenn Runbook erweitert wird |
| `create_concept(title, content, related_adrs?)` | Neues Konzept in "Konzepte" Collection | Beim Konzipieren |
| `list_recent(collection?, limit)` | Zuletzt geänderte Dokumente | Überblick gewinnen |

**Technische Details:**
- FastMCP Server, registriert in `.windsurf/mcp.json`
- Nutzt `outline-wiki-api` (PyPI) als Client
- Bearer Token aus `.env` (ADR-045: `decouple.config()`)
- Alle API-Calls via `asyncio.to_thread()` (sync Client in async FastMCP)

### 3.3 Collections-Struktur

```
📁 Runbooks
    ├── 📄 OIDC authentik Troubleshooting
    ├── 📄 Cloudflare Tunnel + Self-signed Cert
    ├── 📄 Docker Cross-Stack Networking (extra_hosts)
    ├── 📄 RLS Rollout Checklist
    └── 📄 Deployment: Neuen Hub aufsetzen
📁 Architektur-Konzepte
    ├── 📄 Knowledge-Loop: Cascade ↔ Outline
    ├── 📄 Multi-Tenant RLS Strategy
    └── 📄 Content-Store Architecture
📁 Lessons Learned
    ├── 📄 2026-03-14: OIDC 3 Root Causes
    ├── 📄 2026-03-12: RLS SQL-Split Bug
    └── 📄 2026-03-11: Cloudflare Tunnel TLS
📁 ADR-Drafts
    └── 📄 [In-Progress ADRs vor Git-Commit]
📁 Hub-Dokumentation
    ├── 📁 risk-hub
    ├── 📁 travel-beat
    ├── 📁 coach-hub
    └── 📁 ...
📁 ADRs (Read-Only Mirror)
    └── 📄 [Sync aus Git — Referenz, nicht editieren]
```

### 3.4 Session-Start Workflow (Integration in /agent-session-start)

Erweiterung des bestehenden `/agent-session-start` Workflows:

```markdown
## Schritt 5 (NEU): Knowledge-Lookup

1. Identifiziere das Thema der aktuellen Aufgabe
2. outline_mcp: search_knowledge("<thema>")
3. Wenn Treffer:
   - Relevante Runbooks als Kontext laden
   - Lessons Learned beachten
   - Konzepte als Basis nutzen
4. Wenn kein Treffer:
   - Neues Wissensgebiet — am Ende Runbook erstellen
```

### 3.5 Session-Ende Workflow (NEU: /knowledge-capture)

```markdown
## /knowledge-capture — Am Ende jeder produktiven Session

1. Prüfe: Wurde neues Troubleshooting-Wissen generiert?
   → Ja: create_runbook() mit Step-by-Step-Anleitung
2. Prüfe: Wurden Architektur-Entscheidungen getroffen?
   → Ja: create_concept() oder update_document()
3. Prüfe: Wurden Lessons Learned identifiziert?
   → Ja: create_runbook() in "Lessons Learned" Collection
4. Cascade Memory wie bisher updaten
```

---

## 4. Abgrenzung: Was NICHT in Outline gehört

| Was | Warum nicht | Wo stattdessen |
|-----|-------------|----------------|
| **Finalisierte ADRs** | Git ist Source of Truth für finale Entscheidungen | `platform/docs/adr/` |
| **Code-Snippets** | Gehören in den Code, nicht ins Wiki | Git Repos |
| **Secrets/Credentials** | Sicherheitsrisiko | `.env` Dateien (ADR-045) |
| **Temporäre Session-Notizen** | Zu kurzlebig für Wiki | Cascade Memory |
| **Automatisch generierte Logs** | Noise → Signal-Ratio zerstören | Grafana/Prometheus |

---

## 5. Implementierungsplan

| Phase | Inhalt | Aufwand | Abhängigkeit |
|-------|--------|---------|-------------|
| **5.1** | Collections-Struktur in Outline anlegen | 30 min | Outline OIDC ✅ |
| **5.2** | Erste Runbooks manuell erstellen (OIDC, RLS, Tunnel) | 1h | 5.1 |
| **5.3** | Outline API-Token erstellen (für outline_mcp) | 15 min | 5.1 |
| **5.4** | outline_mcp FastMCP Server implementieren | 3h | 5.3 |
| **5.5** | outline_mcp in Windsurf registrieren + testen | 1h | 5.4 |
| **5.6** | `/agent-session-start` um Knowledge-Lookup erweitern | 30 min | 5.5 |
| **5.7** | `/knowledge-capture` Workflow erstellen | 30 min | 5.5 |
| **5.8** | research-hub: KnowledgeDocument Model + Webhook | 3h | ADR-143 Phase 5-6 |
| **5.9** | Celery: AI-Enrichment (Summary, Keywords, ADR-Links) | 2h | 5.8 |
| **5.10** | ADR-Git-Sync: platform/docs/adr/ → Outline (read-only) | 2h | 5.8 |

**Quick Wins (sofort nutzbar nach Phase 5.1-5.2):** Manuell Runbooks in Outline schreiben, im Browser durchsuchen.
**Cascade-Integration (nach Phase 5.5):** outline_mcp in Windsurf → Knowledge-Loop aktiv.
**Vollautomatisch (nach Phase 5.9):** AI-Enrichment, ADR-Linking, semantische Suche.

---

## 6. Metriken: Ist der Knowledge-Loop wirksam?

| Metrik | Messung | Ziel |
|--------|---------|------|
| **Runbooks erstellt** | Outline API: Dokumente in "Runbooks" Collection | ≥ 2 pro Woche |
| **Knowledge-Hits** | outline_mcp search_knowledge() calls mit relevanten Treffern | ≥ 50% Hit-Rate |
| **Wiederholtes Debugging** | Subjektiv: Gleiches Problem erneut gelöst? | 0 nach 4 Wochen |
| **Session-Startup-Zeit** | Zeit bis produktive Arbeit beginnt | < 5 Min (mit Kontext) |
| **Outline Engagement** | Logins pro Woche (authentik Logs) | ≥ 3 pro Woche |

---

## 7. Risiken & Gegenmaßnahmen

| Risiko | Wahrscheinlichkeit | Gegenmaßnahme |
|--------|-------------------|---------------|
| **Runbooks veralten** | Hoch | AI-Enrichment markiert Alter, Review-Reminder nach 90 Tagen |
| **Zu viel Noise** | Mittel | Klare Collections-Struktur, Quality Gate: nur echte Lessons Learned |
| **Outline-Ausfall** | Niedrig | Cascade Memories als Fallback, tägliches Backup |
| **Adoption scheitert** | Mittel | Quick Wins zuerst (Phase 5.1-5.2), Wert beweisen vor Automatisierung |
| **Duplizierung mit Memories** | Mittel | Klare Abgrenzung: Memories = Session-Kontext, Outline = Strukturwissen |

---

## 8. Konsequenzen

### Positiv

- **Knowledge Drain → Knowledge Loop**: Wissen bleibt erhalten und wächst
- **Cascade wird schlauer**: Zugriff auf Runbooks, Konzepte, Lessons Learned
- **Team-ready**: Wissen ist teilbar (OIDC-Login), nicht an eine Person gebunden
- **ADR-132 gelöst**: AI Context Amnesia durch strukturiertes Wissensmanagement adressiert
- **Skaliert**: Pattern funktioniert für 1 Person genauso wie für 10

### Negativ

- **Disziplin nötig**: Session-Ende-Ritual muss konsequent durchgeführt werden
- **Pflege-Aufwand**: Runbooks müssen aktuell gehalten werden
- **Zusätzliches Tool**: Outline neben Git, Discord, Grafana — Toolchain wird größer

---

## 9. Referenzen

- ADR-143: Knowledge-Hub — Outline Wiki (technische Architektur)
- ADR-142: Unified Identity — authentik als Platform IdP
- ADR-132: AI Context Defense-in-Depth
- docs/guides/oidc-authentik-integration.md — OIDC Pattern Guide (erstes Runbook-Kandidat)
