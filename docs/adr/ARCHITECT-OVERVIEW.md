# Plattform-ADR — Architekten-Übersicht

> **Stand:** 2026-05-11
> **Scope:** 144 aktive ADRs (Status `Accepted` / `Proposed` / Draft). Deprecated/Superseded/Archived nicht enthalten — Historie siehe `INDEX.md` und `_archive/`.
> **Quelle:** Filesystem `docs/adr/*.md` (SSOT, siehe ADR-065).
> **Lesehilfe:** Jede ADR mit 1–2 Sätzen — **Konzept** (was es ist) + **Fokus** (warum es da ist / was es liefert).

---

## 0. Wie diese Plattform gedacht ist (Big Picture)

Die Plattform ist ein **Hub-Landschaft auf gemeinsamer Foundation**: ~20 Django/Reflex-Hubs (UI-Produkte) teilen sich eine wiederverwendbare Foundation aus Shared-Packages (`iil-*`, `weltenfw`, `aifw`, `authoringfw`, `promptfw`, …), eine zentrale Deployment-Pipeline auf Hetzner und einen AI/Agent-Layer (Multi-Agent Coding Team + LLM-Gateway + MCP-Tools). Multi-Tenancy (PostgreSQL Schema Isolation + RLS), zentrales Billing und ein einheitliches Identity Provider (authentik) sind plattformweit verpflichtend. **Single-Engineer-Team mit AI-Agents** — daher Optimierung auf Reuse, Konvention statt Konfiguration, automatisierte Gates statt manueller Reviews.

Die ADRs gliedern sich in **13 Architektur-Cluster**:

| # | Cluster | ADRs |
|---|---------|------|
| 1 | Foundation & Platform Governance | 14 |
| 2 | Multi-Tenancy & Identity | 10 |
| 3 | Frontend, UI, HTMX & REFLEX | 8 |
| 4 | Deployment, CI/CD & Infrastructure | 21 |
| 5 | MCP & Tool-Plattform | 8 |
| 6 | AI / LLM Routing & Frameworks | 11 |
| 7 | Agent-Plattform & Autonomous Coding | 19 |
| 8 | Search, RAG & Document-Pipeline | 9 |
| 9 | Shared Packages & Libraries | 13 |
| 10 | Testing & Quality Gates | 7 |
| 11 | Hubs, Domains & Produkte | 18 |
| 12 | Work Management & Operationen | 4 |
| 13 | Dokumentation | 2 |

---

## 1. Foundation & Platform Governance

**Konzept-Strang:** Wie ADRs entstehen, wie sie konsistent bleiben, und welche plattformweiten Konventionen alle Repos einhalten. Optimiert auf **AI-Agent-Lesbarkeit** und **Drift-Vermeidung**.

- **[ADR-015](ADR-015-platform-governance-system.md) — Platform Governance System.** Verbindliches Rahmenwerk für plattformweite Entscheidungen. *Fokus: definiert Rollen, Entscheidungs-Flow und Eskalationspfade.*
- **[ADR-022](ADR-022-platform-consistency-standard.md) — Platform Consistency Standard (v3).** Pflicht-Tech-Stack & Coding-Konventionen für alle Django-Hubs. *Fokus: Voraussetzung für Shared-Packages und Multi-Agent-Coding — Konsistenz vor Innovation pro Repo.*
- **[ADR-028](ADR-028-platform-context.md) — Platform Context.** Konsolidierung der Foundation-Schichten in einer SSOT. *Fokus: ein Ort, wo "wie funktioniert die Plattform" beantwortet wird (für Menschen und Agents).*
- **[ADR-050](ADR-050-platform-decomposition-hub-landscape.md) — Hub Landscape & Developer Portal.** Plattform zerfällt in unabhängige Hubs + Entwicklerportal. *Fokus: Domain-Schnitt + dev-hub als Navigationszentrale.*
- **[ADR-051](ADR-051-concept-to-adr-pipeline.md) — Concept-to-ADR Pipeline.** Idee → Concept-Note → ADR über AI-assistierte Promotion. *Fokus: niedrigere Friction für architektonische Entscheidungen.*
- **[ADR-059](ADR-059-adr-drift-detector.md) — ADR Drift Detection.** Automatische Erkennung von ADRs, die nicht mehr zur Realität passen. *Fokus: ADRs als lebendige Artefakte, nicht historische Notizen.*
- **[ADR-065](ADR-065-adr-numbering-filesystem-first.md) — Filesystem-first ADR Numbering.** Nummer = `max(existing) + 1`, niemals Wiederverwendung. *Fokus: keine Kollisionen bei parallelen Agent-Branches.*
- **[ADR-071](ADR-071-amendment-code-quality-tooling.md) — Code Quality Tooling (Amendment zu 022).** Ruff/Black/etc. verbindlich. *Fokus: einheitliches Lint/Format-Setup als Vorbedingung für AI-Codegen.*
- **[ADR-073](ADR-073-repo-scope.md) — Repo Scope & Migration Status.** Inventory aller in-scope Repos (mittlerweile 30). *Fokus: SSOT was zur Plattform gehört.*
- **[ADR-083](ADR-083-hybrid-adr-governance.md) — Hybrid ADR Governance.** Plattform-ADRs + Repo-lokale ADRs. *Fokus: nicht alles muss in `platform/` landen — lokale Entscheidungen bleiben lokal.*
- **[ADR-138](ADR-138-implementation-tracking-standard.md) — Implementation Tracking Standard.** Frontmatter-Feld `implementation_status` + verifizierbare Evidence. *Fokus: ADR sagt nicht nur "soll", sondern auch "ist umgesetzt".*
- **[ADR-174](ADR-174-workflow-enforcement-ci-gate.md) — Workflow Enforcement: CI Gate.** PR-Checklist + Symlink-Policy + CI-Pflichtchecks. *Fokus: Konventionen werden vom CI durchgesetzt, nicht von Code-Review.*
- **[ADR-175](ADR-175-workflow-modularization-pattern.md) — Workflow Modularization.** `.windsurf/workflows/` selektiv modularisieren. *Fokus: wiederverwendbare Agent-Workflows.*
- **[ADR-190](ADR-190-adopt-iil-adrfw-tooling-framework.md) — iil-adrfw Tooling Framework.** Shared Python-Package für ADR-Tooling (Lint, Drift, Index). *Fokus: ADR-Toolchain ist selbst ein versionierbares Asset.*

---

## 2. Multi-Tenancy & Identity

**Konzept-Strang:** Die Plattform ist von Anfang an **multi-tenant**. PostgreSQL-Schema pro Tenant, Self-Service-Onboarding, plattformweites SSO via authentik.

- **[ADR-007](ADR-007-FINAL-PRODUCTION.md) — Tenant- & RBAC-Architektur.** Ur-ADR für Tenancy: Schema-Isolation + RBAC. *Fokus: Produktions-Baseline, auf der alles spätere aufsetzt.*
- **[ADR-035](ADR-035-shared-django-tenancy.md) — Shared Django Tenancy Package.** Tenancy als wiederverwendbare Lib. *Fokus: Tenancy einmal richtig bauen, in jedem Hub nutzen.*
- **[ADR-072](ADR-072-multi-tenancy-schema-isolation.md) — PostgreSQL Schema Isolation.** Ein Schema je Tenant statt Discriminator-Column. *Fokus: harte Isolation, geringere Mandanten-Leak-Wahrscheinlichkeit.*
- **[ADR-074](ADR-074-multi-tenancy-testing-strategy.md) — Multi-Tenancy Testing Strategy.** Tenant-Propagation und Isolation als CI-Gate. *Fokus: Tenancy-Bugs sind silent — Tests müssen sie aktiv suchen.*
- **[ADR-092](ADR-092-tenant-aware-seed-commands.md) — Tenant-Aware Seed Commands.** `manage.py seed_*` müssen Tenant explizit machen. *Fokus: kein versehentliches "Seed läuft in public-Schema".*
- **[ADR-109](ADR-109-multi-tenancy-platform-standard.md) — Multi-Tenancy Plattform-Standard.** Multi-Tenancy ist für **alle UI-Hubs** verpflichtend. *Fokus: keine Single-Tenant-Hub-Ausreißer mehr.*
- **[ADR-110](ADR-110-i18n-platform-standard.md) — i18n Plattform-Standard.** DE/EN ab Tag 1 in jedem Hub. *Fokus: i18n nicht nachträglich nachrüsten.*
- **[ADR-137](ADR-137-tenant-lifecycle-module-selfservice-rls.md) — Tenant-Lifecycle + RLS.** Self-Service-Tenant-Anlage, Modul-Buchung, PostgreSQL RLS als zweite Schutzschicht. *Fokus: Plattform-Store macht neue Mandanten produktiv ohne Engineer.*
- **[ADR-142](ADR-142-unified-identity-authentik-platform-idp.md) — authentik als Platform IdP.** Ein SSO über alle Hubs. *Fokus: Identity weg aus jedem Hub — eine zentrale Wahrheit.*
- **[ADR-161](ADR-161-shared-sds-library.md) — Two-Layer-Schema + Hybrid-RLS.** Plattform-weite (tenant-übergreifende) SDS-Daten ohne Tenancy-Bruch. *Fokus: kontrollierter Ausweg für genuinely geteilte Daten.*

---

## 3. Frontend, UI, HTMX & REFLEX

**Konzept-Strang:** Server-rendered Django-Templates + HTMX, Tailwind via Design-Tokens, plus **REFLEX** als evidenzbasierte UI-Test/Quality-Methodologie.

- **[ADR-040](ADR-040-frontend-completeness-gate.md) — Frontend Completeness Gate.** Feature gilt erst als fertig, wenn UI sichtbar funktioniert. *Fokus: kein "API ist da, UI kommt später".*
- **[ADR-041](ADR-041-django-component-pattern.md) — Django Component Pattern.** Wiederverwendbare UI-Blöcke (`{% include %}`-Komponenten). *Fokus: gemeinsames Design-System ohne SPA-Komplexität.*
- **[ADR-048](ADR-048-htmx-playbook.md) — HTMX Playbook.** Kanonische Patterns für Django+HTMX. *Fokus: ein Pattern pro Problem (Form, List, Modal, Polling), nicht "jeder Hub erfindet neu".*
- **[ADR-049](ADR-049-design-token-system.md) — Design Token System.** CSS-Custom-Properties + Tailwind-Bridge. *Fokus: ein Theme über alle Hubs, Brand-Anpassung via Tokens.*
- **[ADR-162](ADR-162-reflex-ui-testing-and-scraping.md) — REFLEX als Standard-Methodologie.** Evidenz-basierte UI-Entwicklung (Scraping + Pixel-Tests). *Fokus: UI-Behauptungen werden empirisch verifiziert, nicht behauptet.*
- **[ADR-163](ADR-163-reflex-tiering-platform-quality-standard.md) — Three-Tier REFLEX Quality Standard.** Hub bekommt Tier 1/2/3 je nach UI-Qualitäts-Anspruch. *Fokus: nicht jeder Hub braucht Pixel-Perfekt — aber jeder Hub kennt sein Tier.*
- **[ADR-165](ADR-165-reflex-review-engine-with-grafana-controlling.md) — Plugin-based REFLEX Review Engine.** Pluggable Reviewers + Grafana-Controlling. *Fokus: UI-Reviews auf Dashboards sichtbar, nicht in Issue-Kommentaren versteckt.*
- **[ADR-192](ADR-192-django-service-layer-htmx-compliance-scanner.md) — Django Service-Layer + HTMX Compliance Scanner.** Statische Prüfung auf Service-Layer-Pattern + HTMX-Konventionen. *Fokus: Konvention statt Code-Review.*

---

## 4. Deployment, CI/CD & Infrastructure

**Konzept-Strang:** Ein einheitlicher Deployment-Weg für alle Hubs auf **Hetzner-VMs**, 3-Server-Setup (Dev/Staging/Prod), `.ship.conf` als SSOT, Cloudflare davor.

- **[ADR-021](ADR-021-unified-deployment-pattern.md) — Unified Single-Service Deployment Pipeline.** Eine Pipeline-Definition für alle Hubs. *Fokus: Deploy-Bugs einmal fixen, alle Repos profitieren.*
- **[ADR-031](ADR-031-static-asset-versioning.md) — Static Asset Versioning & Landing Page Registry.** Statische Sites unter Git-Kontrolle. *Fokus: nie wieder "live-Page versehentlich überschrieben".*
- **[ADR-042](ADR-042-dev-environment-deploy-workflow.md) — Dev-Environment & Deploy Workflow.** Wie Engineer/Agent lokal → Staging → Prod gelangt. *Fokus: ein dokumentierter Flow für alle Hubs.*
- **[ADR-045](ADR-045-secrets-management.md) — Secrets & Environment Management.** `.env`-Konvention + Secret-Source pro Umgebung. *Fokus: keine Secrets im Git, kein Drift zwischen Hubs.*
- **[ADR-056](ADR-056-deployment-preflight-and-pipeline-hardening.md) — Deployment Pre-Flight Validation.** Pre-Deploy Checks (Migrations, Health, Konfig). *Fokus: kaputte Deploys werden vor SSH-Push gestoppt.*
- **[ADR-060](ADR-060-developer-workstation-ssh-configuration.md) — SSH Key Configuration Standard.** Einheitliche `~/.ssh/config`-Strategie. *Fokus: jeder Engineer/Agent erreicht jeden Server gleich.*
- **[ADR-075](ADR-075-deployment-execution-strategy.md) — Split Deployment Execution.** Read-only MCP-Tools lokal + GH-Actions schreiben. *Fokus: Agents können nichts kaputtmachen, GH Actions hat Audit-Trail.*
- **[ADR-077](ADR-077-infrastructure-context-system.md) — Infrastructure Context System.** `catalog-info.yaml` → dev-hub API → `context.md`. *Fokus: Plattform-Metadaten zentral abfragbar (Backstage-Pattern, schlank).*
- **[ADR-078](ADR-078-amendment-docker-healthcheck-convention.md) — Docker HEALTHCHECK Convention.** HEALTHCHECK nur in `docker-compose.prod.yml`. *Fokus: keine Healthcheck-Drift zwischen Dockerfile und Compose.*
- **[ADR-090](ADR-090-cicd-pipeline-python-postgres.md) — Hybrid Matrix CI/CD Pipeline.** Standard-Pipeline für Python+Postgres+Docker. *Fokus: Template, das jeder Hub übernimmt.*
- **[ADR-098](ADR-098-production-infrastructure-tuning-standard.md) — 3-Layer Tuning Standard (Hetzner).** Redis maxmemory, Postgres `random_page_cost`, Docker `shm_size`/`logging` plattformweit. *Fokus: gleiche Tuning-Defaults, kein Production-Surprise.*
- **[ADR-102](ADR-102-cloudflare-dns-cdn-migration.md) — Cloudflare DNS/CDN/DDoS.** Cloudflare als Edge für alle Hubs. *Fokus: DDoS-Schutz + zentrales DNS-Management.*
- **[ADR-120](ADR-120-unified-deployment-pipeline.md) — Unified Multi-Repo Deployment Pipeline mit Staging.** Erweiterung von 021 um Staging-Stufe. *Fokus: keine direkten Prod-Deploys mehr.*
- **[ADR-156](ADR-156-reliable-deployment-pipeline.md) — Server-Side Deploy Scripts + Short-Trigger.** Deploy-Logik auf dem Server, GH Actions triggert nur. *Fokus: weniger fragile GH-Actions-YAML, mehr lokaler Server-Code.*
- **[ADR-157](ADR-157-staging-production-split-and-port-governance.md) — 3-Server-Architektur (Dev/Staging/Prod).** Drei Hetzner-Server + automatisierte Port-Governance. *Fokus: harte physische Trennung statt Logik-Trennung.*
- **[ADR-159](ADR-159-shared-secrets-management.md) — Shared Secrets Management.** SSOT für API-Keys über alle Repos. *Fokus: API-Key existiert genau einmal, wird referenziert, nicht kopiert.*
- **[ADR-164](ADR-164-port-strategy-conflict-free-dev-staging-prod.md) — Unified Port Strategy.** Konfliktfreie Port-Zuweisung dev/staging/prod. *Fokus: kein "Hub X läuft auf Port 8000, Hub Y auch".*
- **[ADR-166](ADR-166-deployment-configuration-standard.md) — `.ship.conf` SSOT + `/livez/`.** Eine Datei pro Repo beschreibt Deploy + Healthcheck. *Fokus: SSOT für Deployment-Konfiguration, maschinen-lesbar für Agents.*
- **[ADR-167](ADR-167-three-tier-middleware-architecture.md) — 3-Tier Middleware Standard.** Health Probes + Tenant Resolution in einer definierten Reihenfolge. *Fokus: Middleware-Reihenfolge ist Architektur, nicht Detail.*
- **[ADR-185](ADR-185-deploy-agent-pattern.md) — Gate-controlled Deploy-Agent.** Automatisierte Staging→Prod-Deploys mit Quality-Gates. *Fokus: Deploys ohne Engineer, aber mit Safety-Net.*
- **[ADR-193](ADR-193-deployment-configuration-compliance-audit.md) — Deployment Configuration Compliance Audit.** Automatische Prüfung, dass alle Repos den Deployment-Standard einhalten. *Fokus: Drift-Detection auf Infra-Ebene.*

---

## 5. MCP & Tool-Plattform

**Konzept-Strang:** **MCP (Model Context Protocol)** ist die Schnittstelle, über die Agents/Claude/Cascade Plattform-Tools nutzen. 3-Tier-Architektur: Servers (capability) → Hub (consolidation) → Tools (skill).

- **[ADR-010](ADR-010-mcp-tool-governance.md) — MCP Tool Governance.** Spec-Standard, Service-Discovery, Tool-Composition. *Fokus: Tools haben ein vorhersagbares Schema, Agents können sie blind nutzen.*
- **[ADR-012](ADR-012-mcp-quality-standards.md) — MCP Server Quality Standards.** Mindestanforderungen für MCP-Server (Logging, Auth, Tests). *Fokus: kein "schnell hingerotzter" MCP-Server in Produktion.*
- **[ADR-044](ADR-044-mcp-hub-architecture-consolidation.md) — MCP-Hub Architecture Consolidation.** Konsolidierung der MCP-Server in einem Hub-Repo. *Fokus: ein Ort statt 12 verteilte MCP-Repos.*
- **[ADR-069](ADR-069-web-intelligence-mcp.md) — Web Intelligence MCP.** Plattformweiter Web-Zugriff (Scrape, Fetch, Cache). *Fokus: keiner muss mehr selbst HTTP-Clients bauen.*
- **[ADR-091](ADR-091-platform-operations-hub-consolidation.md) — Platform Operations Hub Consolidation.** Ops-Tooling als ein MCP-Hub. *Fokus: Deploy/Logs/Restart über eine Tool-Surface.*
- **[ADR-101](ADR-101-mcp-plattform-konzept.md) — 3-Tier MCP Architecture.** Tier 1 = Capability, Tier 2 = Hub, Tier 3 = Skill. *Fokus: klare Abstraktions-Ebenen statt Tool-Wildwuchs.*
- **[ADR-172](ADR-172-rag-mcp-server.md) — rag-mcp Server.** Plattform-weite RAG-API als MCP-Tool. *Fokus: jeder Hub spricht denselben RAG-Endpoint an.*
- **[ADR-176](ADR-176-mcp-server-ssot.md) — MCP-Server SSoT: platform = Config, mcp-hub = Code.** Config zentral, Implementierung im mcp-hub. *Fokus: keine Drift zwischen Server-Definition und tatsächlicher Implementierung.*

---

## 6. AI / LLM Routing & Frameworks

**Konzept-Strang:** Plattform routet LLM-Calls über eine **eigene Abstraktionsschicht** (aifw + bfagent-llm/LiteLLM + Model-Registry), nicht direkt zu Anbietern. Routing entscheidet Tier/Budget/Quality dynamisch.

- **[ADR-068](ADR-068-adaptive-model-routing.md) — Adaptive Model Routing.** Quality-Feedback-Loop steuert Modell-Auswahl. *Fokus: Modelle werden auf Basis empirischer Qualität gewählt, nicht Anbieter-Marketing.*
- **[ADR-084](ADR-084-model-registry-dynamic-llm-routing.md) — Model Registry.** DB-gestützte Tier-Verwaltung der verfügbaren LLMs. *Fokus: Modell-Wechsel = DB-Update, kein Code-Deploy.*
- **[ADR-089](ADR-089-bfagent-llm-litellm-db-driven-architecture.md) — bfagent-llm + LiteLLM.** LiteLLM als Provider-Adapter + DB-Routing. *Fokus: ein Endpoint für alle Anbieter (Anthropic/OpenAI/local).*
- **[ADR-093](ADR-093-ai-config-app.md) — AI Config App in dev-hub.** UI zur Konfiguration der AI-Plattform. *Fokus: AI-Konfig ist editierbar ohne Deploy.*
- **[ADR-095](ADR-095-aifw-quality-level-routing.md) — aifw Quality-Level Routing.** Multi-dimensionales Routing mit Prompt-Template-Koordination. *Fokus: "diese Task braucht Quality=high, Budget=low" → System wählt.*
- **[ADR-097](ADR-097-aifw-060-implementation-contract.md) — aifw 0.6.0 Implementation Contract.** Models, Migrations, Service-Layer, Public API für aifw. *Fokus: stabiler API-Vertrag für aifw-Consumer.*
- **[ADR-116](ADR-116-dynamic-model-router.md) — Dynamic Model Router.** Budget-aware regelbasierter Fallback-Router. *Fokus: wenn Premium-Modell aus, ziehe auf günstigeres um, ohne Code-Änderung.*
- **[ADR-132](ADR-132-ai-context-defense-in-depth.md) — AI Context Defense-in-Depth.** Mehrere Schichten gegen Prompt-Injection und Context-Drift. *Fokus: Agents arbeiten mit getrustetem Kontext.*
- **[ADR-133](ADR-133-shared-ai-services-package.md) — Shared AI Services Package.** Wiederverwendbare AI-Services als pip-Paket. *Fokus: Embedding/Summarize/Classify einmal bauen, überall nutzen.*
- **[ADR-146](ADR-146-hub-prompt-management.md) — promptfw als SSoT für DB-Prompts.** Prompts in DB, editierbar via UI. *Fokus: Prompt-Engineering ohne Deploy.*
- **[ADR-178](ADR-178-llm-gateway-consolidation.md) — LLM Gateway Consolidation.** Konsolidierung mehrerer Gateway-Komponenten. *Fokus: weniger Hops zwischen Hub und Anbieter.*

---

## 7. Agent-Plattform & Autonomous Coding

**Konzept-Strang:** **Multi-Agent Coding Team** mit spezialisierten Rollen (DocBot/TestBot/FeatureBot/…), Progressive Autonomy, Guardrails, QA-Cycle. Discord/Telegram als IDE-ähnliche Gateways.

- **[ADR-036](ADR-036-chat-agent-ecosystem.md) — Chat-Agent Ecosystem.** DomainToolkits + Research-Integration + Shared Chat-Widget. *Fokus: ein Chat-Agent-Pattern, das jeder Hub einbettet.*
- **[ADR-037](ADR-037-chat-conversation-logging.md) — Chat Conversation Logging.** Conversation-Persistence + Quality-Management. *Fokus: Chats sind Trainingsdaten + Audit-Quelle.*
- **[ADR-043](ADR-043-ai-assisted-development.md) — AI-Assisted Development.** Context- und Workflow-Optimization für Engineers mit AI. *Fokus: AI ist Coworker, nicht Tool — Prozesse passen sich an.*
- **[ADR-066](ADR-066-ai-engineering-team.md) — AI Engineering Squad mit Role-based Agents.** Strukturierte AI-Engineering-Crew mit Rollen. *Fokus: Agent-Rollen statt eines Allzweck-Agents.*
- **[ADR-070](ADR-070-progressive-autonomy-developer-agent.md) — Progressive Autonomy Pattern.** Agent bekommt schrittweise mehr Autonomie nach erfolgreichen Stufen. *Fokus: Vertrauen wird verdient, nicht angenommen.*
- **[ADR-080](ADR-080-multi-agent-coding-team-pattern.md) — Multi-Agent Coding Team Pattern.** Strukturiertes Handoff + parallele Branches + Rollback. *Fokus: mehrere Agents arbeiten ohne sich auf die Füße zu treten.*
- **[ADR-081](ADR-081-agent-guardrails-code-safety.md) — Agent Guardrails & Code Safety.** Scope-Lock, Pre/Post-Gates, Rollback-Strategy. *Fokus: Agent kann nichts kaputtmachen, was nicht reversibel ist.*
- **[ADR-082](ADR-082-llm-tool-integration-autonomous-coding.md) — LLM Tool Integration.** Stub-Steps werden durch echte LLM-Tool-Calls ersetzt. *Fokus: Übergang von "Agent simuliert" zu "Agent macht wirklich".*
- **[ADR-085](ADR-085-use-case-pipeline-nl-to-taskgraph.md) — Use Case Pipeline NL→TaskGraph.** Natural Language → strukturierter TaskGraph. *Fokus: User-Ticket wird zu maschinen-ausführbarem Plan.*
- **[ADR-086](ADR-086-agent-team-workflow.md) — Agent Team Workflow.** Cross-Repo Sprint Execution Pattern. *Fokus: ein Sprint kann mehrere Repos berühren, ohne dass Coordination zerbricht.*
- **[ADR-107](ADR-107-extended-agent-team-deployment-agent.md) — Extended Agent Team.** Cascade als Tech Lead + Deployment Agent + Review Agent. *Fokus: explizite Rollen entlasten den Hauptagent.*
- **[ADR-108](ADR-108-agent-qa-cycle.md) — Agent QA Cycle.** Quality Evaluator + Completion Gate + AuditStore. *Fokus: Agent-Output wird systematisch geprüft, nicht blind übernommen.*
- **[ADR-112](ADR-112-agent-skill-registry-persistent-context.md) — Agent Skill Registry + Persistent Context.** Skills + persistente Kontext-Store über Sessions. *Fokus: Agents vergessen nicht zwischen Sessions.*
- **[ADR-114](ADR-114-discord-ide-like-communication-gateway.md) — Discord als verlängertes Cascade IDE.** Discord = mobiler Eingang zum Coding-Agent. *Fokus: Code aus dem Café via Discord-Thread starten.*
- **[ADR-141](ADR-141-discord-agentic-coding-bridge.md) — Discord → Agentic Coding Bridge (Layer 4).** Standardisierte Bridge zwischen Discord und Agent-Backend. *Fokus: Discord-Messages sind erste-Klasse Trigger.*
- **[ADR-154](ADR-154-autonomous-coding-optimization.md) — Autonomous Coding Optimization.** Information-Flow + Error-Prevention + Continuous Improvement. *Fokus: Agents lernen aus Fehlern, nicht nur aus Erfolgen.*
- **[ADR-169](ADR-169-enrichment-agent-pattern.md) — iil-enrichment Pattern.** Generic Pattern für Brücke zwischen Records und externem Wissen. *Fokus: "Anreichere Datensatz X mit Quelle Y" als wiederverwendbares Muster.*
- **[ADR-177](ADR-177-agent-role-specialization.md) — Agent Role Specialization.** Developer-Agent → 5 Spezialisten (DocBot, TestBot, FeatureBot, ReEngineerBot, ArchitectBot). *Fokus: Spezialisten produzieren höhere Qualität als Generalisten.*
- **[ADR-186](ADR-186-headless-agent-coding-pipeline.md) — Headless Agent-Coding Pipeline.** Devin CLI + Orchestrator-Bridge für Polyrepo-Automation. *Fokus: Coding-Pipeline läuft ohne UI, getriggert via CI.*

---

## 8. Search, RAG & Document-Pipeline

**Konzept-Strang:** **Ein unified Vector Store** (pgvector) + ein **RAG-Stack** + eine **Document-Ingest-Pipeline** plattformweit. Mehrsprachig (multilingual-e5-large), bitemporal (ADR-171).

- **[ADR-087](ADR-087-hybrid-search-architecture.md) — pgvector + FTS Hybrid Search.** Plattformweite semantische Suche mit Reciprocal Rank Fusion. *Fokus: ein Such-Pattern für alle Hubs.*
- **[ADR-104](ADR-104-research-hub-iil-researchfw.md) — Research-Hub + iil-researchfw.** Zentralisierung der Research-Infrastruktur. *Fokus: Research einmal bauen, in mehreren Hubs nutzen.*
- **[ADR-105](ADR-105-iil-researchfw-extraction-plan.md) — iil-researchfw Extraction Plan.** Code-Extraktion aus bestehenden Hubs in das Framework. *Fokus: Plan, wie aus bestehendem Code ein wiederverwendbares Lib wird.*
- **[ADR-160](ADR-160-llm-powered-research-pipeline.md) — LLM-Powered Query Expansion (researchfw).** Query-Expansion + Relevance-Scoring via LLM. *Fokus: bessere Suche durch LLM-Augmentation.*
- **[ADR-170](ADR-170-iil-ingest-document-ingestion-package.md) — iil-ingest — Document Ingestion Package.** Tier-3 wiederverwendbares Package. *Fokus: Dokumente → Chunks → Embeddings als Standard-Pipeline.*
- **[ADR-171](ADR-171-temporal-rag-infrastructure.md) — Temporal RAG Infrastructure.** Bitemporal Vector Storage auf pgvector. *Fokus: RAG kennt "was war wann gültig" — wichtig für regulierte Domains.*
- **[ADR-173](ADR-173-document-intake-routing-pattern.md) — Document Intake Routing Pattern.** Dokument → richtiger Processor je nach Typ. *Fokus: Routing als first-class Konzept, nicht hardcoded if-else.*
- **[ADR-187](ADR-187-document-intelligence-pipeline.md) — Document Intelligence Pipeline.** iil-ingest + VectorStore + Multi-Tool-Ensemble + RAG. *Fokus: end-to-end Pipeline für Template-Erkennung, RAG, VectorStore-Befüllung.*
- **[ADR-188](ADR-188-unified-vector-store.md) — Unified Vector Store (multilingual-e5-large).** Konsolidierung mehrerer VectorStores in **einen** plattformweiten. *Fokus: keine Drift mehr zwischen "agent-memory vs. search-chunks vs. rag-chunks".*

---

## 9. Shared Packages & Libraries

**Konzept-Strang:** Plattform = Hubs + **shared Python-Packages**, die als `iil-*` veröffentlicht werden. Konsolidiert auf ~20 Pakete.

- **[ADR-088](ADR-088-notification-registry.md) — Shared Notification Registry.** Multi-Channel-Messaging (Email/SMS/Webhook/Discord/Telegram). *Fokus: jeder Hub schickt Notifications gleich.*
- **[ADR-096](ADR-096-authoringfw-scope-and-architecture.md) — authoringfw.** Content Orchestration Framework. *Fokus: strukturierte Content-Generierung (statt freie LLM-Prompts).*
- **[ADR-100](ADR-100-iil-testkit-shared-test-factory-package.md) — iil-testkit.** Shared Test Factory Package. *Fokus: Test-Fixtures + Factory-Pattern einmal lösen.*
- **[ADR-117](ADR-117-shared-world-layer-worldfw.md) — Shared World Layer (weltenfw).** Weltenhub-DB als SSoT, weltenfw als Schreibkanal. *Fokus: Story-Welten-Daten getrennt von Hub-Logik.*
- **[ADR-130](ADR-130-content-store-shared-persistence.md) — Shared Django App `content_store`.** Persistenz für AI-generierte Inhalte. *Fokus: AI-Output landet in einer definierten Tabelle, nicht in Ad-hoc-Models.*
- **[ADR-131](ADR-131-shared-backend-services.md) — Shared Backend Services Library.** Die "Common"-Lib für Django-Hubs. *Fokus: INSTALLED_APPS/MIDDLEWARE/health URLs einmal definiert.*
- **[ADR-134](ADR-134-module-monetization-strategy.md) — Module Monetization Strategy.** Plattform-Module sind buchbar + monetarisiert. *Fokus: jedes Modul kann eigenständig zahlbar werden.*
- **[ADR-139](ADR-139-shared-learning-platform-package.md) — iil-learnfw.** Shared Learning Platform Package. *Fokus: LMS-Bausteine wiederverwendbar.*
- **[ADR-147](ADR-147-concept-templates-package.md) — iil-concept-templates.** Shared Package für strukturierte Konzept-Vorlagen. *Fokus: Konzepte sind Daten, nicht freier Text.*
- **[ADR-180](ADR-180-package-consolidation-strategy.md) — Package Consolidation Strategy (34→20).** Konsolidierungsplan für die Library-Landschaft. *Fokus: weniger ist mehr — keine ungepflegten Mini-Libs.*
- **[ADR-181](ADR-181-implementation-plan.md) — Implementierungsplan (produktionsreif).** Konkreter Plan zur Konsolidierung. *Fokus: Sequenz + Migration-Path.*
- **[ADR-182](ADR-182-review.md) — Principal Architect Assessment.** Review von ADR-147/180. *Fokus: externer Blick auf Konsolidierung.*
- **[ADR-183](ADR-183-v2-concept-templates-package.md) — iil-concept-templates v2.** Revidiertes Konzept-Template-Package. *Fokus: Iteration auf ADR-147 nach Feedback.*

---

## 10. Testing & Quality Gates

**Konzept-Strang:** 4-Level-Test-Strategie + 28-Type-Taxonomy + Contract-Testing + automatisierte Compliance-Scanner. Tests sind **Gates**, nicht Vorschlag.

- **[ADR-057](ADR-057-platform-test-strategy.md) — Four-Level Test Strategy mit Contract Testing.** Test-Ebenen: Unit, Integration, Contract, E2E. *Fokus: jede Ebene hat einen klaren Zweck.*
- **[ADR-058](ADR-058-platform-test-taxonomy.md) — 28-Type Test Taxonomy.** Binding-Standard: jeder Test hat exakt einen der 28 Typen. *Fokus: keine "ungeklärten" Tests.*
- **[ADR-061](ADR-061-hardcoding-elimination-strategy.md) — hardcode_scanner.py.** Statischer Scanner gegen hardgecodete Werte. *Fokus: Konfig gehört in `.env` / Settings, nicht in Code.*
- **[ADR-155](ADR-155-api-contract-testing.md) — API Contract Testing.** Contract-Tests zwischen iil-Packages und Consumers. *Fokus: API-Bruch ist CI-Fail, nicht Prod-Surprise.*
- **[ADR-179](ADR-179-postgresql-only-testing.md) — PostgreSQL-Only Testing.** SQLite verboten in Tests, immer Postgres. *Fokus: keine Test/Prod-Divergenz bei DB-Verhalten.*
- **[ADR-184](ADR-184-contract-testing-strategy.md) — Three-Layer Contract Testing Strategy.** Contracts auf allen Function/Method-Call-Layern. *Fokus: jeder API-Aufruf hat einen verifizierbaren Vertrag.*
- **[ADR-191](ADR-191-adopt-iil-codeguard-library-first.md) — iil-codeguard.** Library-First Code Compliance Tooling. *Fokus: Compliance-Checks als versionierte Lib, nicht als Repo-lokales Script.*

---

## 11. Hubs, Domains & Produkte

**Konzept-Strang:** Konkrete Produkt-Hubs mit ADR-dokumentierter Architektur. Jeder Hub setzt auf die Foundation auf.

- **[ADR-030](ADR-030-odoo-management-app.md) — Erste Odoo Management-App.** Dual-Framework-Governance Django+Odoo. *Fokus: Odoo als Backend für Business-Operations, integriert via API.*
- **[ADR-062](ADR-062-central-billing-service.md) — Zentraler Billing-Service.** billing-hub als Plattform-Komponente. *Fokus: ein Billing, alle Hubs.*
- **[ADR-099](ADR-099-devhub-release-management-ui.md) — dev-hub Release Management UI.** PyPI-Publishing + GitHub-Tag-Workflow via devhub.iil.pet. *Fokus: Releases ohne `twine`/CLI-Magie.*
- **[ADR-103](ADR-103-ausschreibungs-hub-architektur-v3.md) — ausschreibungs-hub.** KI-gestützte Ausschreibungs- und Angebotsplattform. *Fokus: Tender-Process automatisieren.*
- **[ADR-115](ADR-115-grafana-agent-controlling-dashboard.md) — Grafana Agent Controlling Dashboard.** Agent-Metrics in Grafana. *Fokus: Agents sind beobachtbar, ihre Kosten/Quality messbar.*
- **[ADR-118](ADR-118-platform-store-billing-hub-user-registration.md) — billing-hub als Platform Store.** User-Registration + Module-Buchung + Stripe. *Fokus: User-Self-Service vom ersten Klick bis zur Rechnung.*
- **[ADR-119](ADR-119-authored-content-pipeline-neutral-lore-to-style.md) — AuthoredContent Pipeline (Lore → Style).** Neutral-Lore wird in Autoren-Stil transformiert. *Fokus: Content-Generierung trennt "Was" (Lore) von "Wie" (Stil).*
- **[ADR-121](ADR-121-iil-outlinefw-story-outline-framework.md) — iil-outlinefw Story-Outline-Framework.** Strukturierte Story-Outlines als Daten. *Fokus: Outlines wiederverwendbar zwischen Hubs (weltenhub, writing-hub).*
- **[ADR-140](ADR-140-learn-hub.md) — Learn-Hub.** Zentrales Learning Management Hub. *Fokus: LMS als eigenständiger Hub auf iil-learnfw.*
- **[ADR-143](ADR-143-knowledge-hub-outline-integration.md) — Knowledge-Hub.** Outline-Wiki + research-hub Integration. *Fokus: Wiki ist die menschliche Lese-Oberfläche der Knowledge-Plattform.*
- **[ADR-144](ADR-144-doc-hub-paperless-ngx.md) — doc-hub (Paperless-ngx).** Paperless-ngx als DMS für Briefpost/PDF. *Fokus: papierne Dokumente digitalisiert + durchsuchbar.*
- **[ADR-145](ADR-145-knowledge-management-cascade-outline.md) — Cascade ↔ Outline Anti-Knowledge-Drain.** Agent-Lernen wird automatisch nach Outline gespiegelt. *Fokus: Wissen, das ein Agent gewinnt, bleibt der Plattform erhalten.*
- **[ADR-148](ADR-148-recruiting-hub-architecture.md) — Recruiting Hub.** Multi-Tenant SaaS-Architektur für Recruiting. *Fokus: Recruiting-Hub konkreter Anwendungsfall der Multi-Tenancy.*
- **[ADR-149](ADR-149-dms-hub-dvelop-platform-service.md) — dms-hub (d.velop Cloud DMS).** d.velop als Plattform-DMS für reglementierte Domains. *Fokus: Compliance-konformes Dokumentenarchiv (vs. Paperless für Brief-Post).*
- **[ADR-151](ADR-151-recruiting-workflow-e2e.md) — End-to-End Recruiting Workflow.** LinkedIn Recruiter × Hunter CRM × Recruiting Hub. *Fokus: drei Systeme zu einem Workflow verbinden.*
- **[ADR-153](ADR-153-tax-hub-saas-architecture.md) — tax-hub SaaS-Architektur.** Modul-basierte SaaS für Steuer-Domain. *Fokus: buchbare Steuer-Module pro Mandant.*
- **[ADR-168](ADR-168-onboarding-platform-architecture.md) — Onboarding-Platform.** Separates Repo auf coach-hub Primitiven + billing-hub Stripe-Pattern. *Fokus: Onboarding-Flow als Produkt, nicht als Setup-Page.*
- **[ADR-189](ADR-189-sysml-gaphor-ttz-hub.md) — SysML/Gaphor für ttz-hub.** SysML-Modellierung mit Gaphor für Engineering-Hub. *Fokus: Engineering-Artefakte als Modell, nicht als Diagramm-PNG.*

---

## 12. Work Management & Operationen

**Konzept-Strang:** Wie Arbeit getrackt wird (GitHub Issues SSOT), wie durable Workflows laufen (Temporal), wie Bugs/Migration-Konflikte gehandhabt werden.

- **[ADR-055](ADR-055-cross-app-bug-management.md) — Cross-App Bug & Feature Management.** Issues, die mehrere Hubs betreffen, an einer Stelle. *Fokus: Bugs verlieren sich nicht zwischen Repos.*
- **[ADR-067](ADR-067-work-management-strategy.md) — GitHub Issues + Projects als SSOT.** Ein Tool für Human + AI Work-Tracking. *Fokus: keine Jira/Linear-Drift parallel zu GitHub.*
- **[ADR-079](ADR-079-temporal-workflow-engine.md) — Temporal Self-Hosted.** Durable-Workflow-Engine für long-running Tasks. *Fokus: Workflows überleben Server-Restarts, Retries werden Engine-managed.*
- **[ADR-094](ADR-094-django-migration-conflict-resolution.md) — Django Migration Conflict Resolution.** Pattern für Migration-Konflikte bei parallelen Branches. *Fokus: Multi-Agent-Branches kollidieren oft auf Migrations — definierter Resolver-Flow.*

---

## 13. Dokumentation

**Konzept-Strang:** **dev-hub als Unified Documentation Portal**, DIATAXIS-Struktur, AI-generierte Reference-Docs.

- **[ADR-046](ADR-046-docs-hygiene.md) — Documentation Governance.** Hygiene + DIATAXIS + Docs-Agent. *Fokus: Doku ist gepflegt, weil ein Agent + ein Gate dafür sorgt.*
- **[ADR-158](ADR-158-unified-documentation-architecture.md) — dev-hub als Unified Documentation Portal.** Audience Navigator + AI-Generated Reference Docs. *Fokus: ein Portal für alle Hub-Dokus, AI hält Reference frisch.*

---

## Wie ein Architekt diese Übersicht nutzt

1. **Top-Down Einstieg:** Cluster 1 (Governance) + Cluster 2 (Tenancy) + Cluster 4 (Deployment) — das ist das Skelett. Wer das versteht, versteht 70 % der Plattform.
2. **Bottom-Up Spezifika:** Wenn der Architekt ein Feature einbringt, prüft er Cluster 7 (Agent-Plattform), 8 (Search/RAG) oder 9 (Shared Packages) auf "gibt es das schon?".
3. **Hub-Bau:** Wer einen neuen Hub anlegt, liest Cluster 11 (Beispiele anderer Hubs) + Cluster 2, 3, 4, 10 (Pflicht-Standards).
4. **Drift-Check:** Cluster 10 (Quality Gates) + ADR-059 (Drift Detector) + ADR-193 (Deployment Compliance Audit) sagen, wie Konsistenz erzwungen wird.

> **Wichtigste Querverweise:**
> - **022 → 071 → 138 → 174 → 190 → 191 → 192 → 193**: Die Compliance-Kette — Standard, Tooling, Tracking, Enforcement, Scanner, Audit.
> - **007 → 035 → 072 → 109 → 137 → 142 → 161**: Die Tenancy-Kette — von der Ur-Entscheidung bis zu RLS und SSO.
> - **021 → 056 → 075 → 120 → 156 → 157 → 164 → 166 → 185**: Die Deployment-Kette — von "ein Hub" bis zum gated Auto-Deploy-Agent.
> - **066 → 070 → 080 → 081 → 082 → 086 → 107 → 108 → 177 → 186**: Die Agent-Plattform-Evolution — vom Squad-Konzept zu spezialisierten headless Pipelines.
> - **087 → 170 → 171 → 172 → 173 → 187 → 188**: Die RAG-Konsolidierungs-Kette — von Hybrid-Suche zum unified Vector Store.
