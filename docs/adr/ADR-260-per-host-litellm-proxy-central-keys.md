---
status: accepted
decision_date: 2026-06-30
deciders:
  - Achim Dehnert
reviewed_by: Claude Code (Opus 4.8) — Pilot + Fleet-Audit
depends_on:
  - ADR-178 (LLM Gateway Consolidation)
  - ADR-115 (LLM Usage Logging)
  - ADR-045 (SOPS / Secrets Management)
related:
  - ADR-223 (LLM Model Screener — Option D LiteLLM Proxy dort verworfen; siehe „Abgrenzung")
  - ADR-072 (Multi-Tenancy)
repo: platform
implementation_status: pilot
staleness_months: 6
drift_check_paths:
  - packages/aifw/aifw/service.py
  - packages/aifw/aifw/models.py
supersedes_check: []
---

# ADR-260: Per-Host LiteLLM-Proxy als zentraler Provider-Key-Halter für aifw-Hubs

## Status
**Accepted** (2026-06-30) — Richtungsentscheidung (Topologie). Implementierung phasenweise
(Pilot → Härten → Rollout). Die operativen/Security-Härtungen aus der externen Zweitmeinung
(Abschnitt „Externe Zweitmeinung — eingearbeitet", 2026-06-30) sind **Vor-Rollout-Gates**,
nicht optional. Pilot auf risk-hub-staging ist live und verifiziert (siehe Confirmation).

## Context and Problem Statement

aifw-konsumierende Hubs rufen LLMs **direkt** beim Provider auf: aifw setzt
`litellm.api_base = LLMProvider.base_url`; ist `base_url` leer, geht der Call direkt
zu Groq/Anthropic/OpenAI mit dem **provider-Key aus der App-Env**. Daraus zwei Probleme:

- **P1 — Key-Sprawl:** jeder Hub braucht `GROQ_API_KEY`/`ANTHROPIC_API_KEY` in jeder Env.
  Rotation/Audit über ~15 Hubs × N Envs ist nicht handhabbar; in der Praxis landeten Keys
  per manuellem Compose-Override pro Deploy (risk-hub, Issue #335).
- **P2 — kein zentrales Cost/Usage-Logging** auf Transport-Ebene (ADR-115-Ziel).

### Fleet-Evidenz (Audit 2026-06-30, read-only über `~/github/*`)

aifw ist **fleet-weit** im Einsatz (grobe Heuristik — exakte Laufzeit-Nutzung je Repo ist
ein billiger Folge-Check, das *breite* Signal ist robust):

- **Vision/multimodal:** bfagent, cad-hub, risk-hub, travel-beat, writing-hub
- **Text:** 137-hub, ausschreibungs-hub, authoringfw, iil-fieldprefill, odoo-hub, pptx-hub,
  research-hub, trading-hub, weltenhub, tax-hub, ttz-hub
- **Vestigial (Dep, 0 Imports → entfernen):** fristenmanagement

→ Zweistellige Hub-Zahl, mehrfach Vision. Das hebt die Schwelle für eine zentrale Lösung
klar (ADR-threshold: neuer Service-Boundary + cross-cutting über viele Repos).

### Abgrenzung zu ADR-223

ADR-223 wählte **Option A** (Fallback-Chain + Model-Screener) und verwarf **Option D
(LiteLLM Proxy)** mit den Cons „zusätzlicher Service / dupliziert aifw / kein Benchmarking".
Dieser ADR **kehrt die Option-D-Ablehnung teilweise um** — mit neuer Evidenz, die 223 nicht
gewichtete: (1) **Key-Zentralisierung** über ~15 Hubs (nicht „Caching/Routing", sondern
Secret-Management), (2) **multimodal/Vision** (mehrere Hubs), (3) ein **Machbarkeitsbeweis**
(Pilot). Wichtig: Proxy und Model-Screener sind **komplementär**, nicht alternativ — der Proxy
ist Transport+Key-Halter, der Screener wählt das Modell. aifw bleibt der Router (SSoT fürs Modell).

## Decision Drivers

- Key-Sprawl beenden (ein Key-Ort statt ~15 Hubs).
- Vision/multimodal muss funktionieren (schließt den Discord-`llm_gateway` aus — text-only).
- **Kein** App-Code-Change (aifw bereits `base_url`-fähig).
- **Cross-Host-Komplexität vermeiden**, nicht lösen.
- Blast-Radius bei Proxy-Ausfall begrenzen (15 Hubs dürfen nicht an einem SPOF hängen).

## Considered Options (Topologie)

### Option 1: Ein zentraler Proxy (alle Hubs aller Hosts)
- Pro: Keys an genau einem Ort; ein Cost-Dashboard.
- **Con: SPOF für ~15 Hubs**; **Cross-Host-Erreichbarkeit** (prod 88.198.191.108 ↔ staging
  88.99.38.75 ↔ …) erfordert internes Netz/Tunnel — genau das Problem, das den vestigialen
  V0-Gateway (prod-intern 8001) für Staging unerreichbar machte.

### Option 2: Per-Host-Proxy (GEWÄHLT)
Je Host **ein** LiteLLM-Proxy auf dem internen Docker-Netz; alle Hubs *dieses Hosts* zeigen
`aifw base_url` auf den **host-lokalen** Proxy. Provider-Keys liegen je Host **einmal** (im
Proxy), nicht je Hub.
- **Pro: Cross-Host-Erreichbarkeit entfällt by design** (host-lokal).
- **Pro: Blast-Radius = ein Host** (= ohnehin die Ausfalleinheit), kein 15-Hub-SPOF.
- **Pro:** Keys an wenigen Hosts (2–3) statt ~15 Hubs → 5× weniger Sprawl, einfache Rotation.
- **Pro:** aifw config-only; kein App-Code; reversibel (`base_url=''`).
- Con: Cost-Logging je Host (Aggregation = nachgelagert, nicht blockierend).
- Con: Proxy-Image/Config je Host pflegen (über Compose-Template vererbt → gering).

### Option 3: Zentral + HA (mehrere Replicas + LB)
- Pro: ein Key-Ort + ausfallsicher.
- Con: größte Infra (LB, Health, Cross-Host-Netz) — für den aktuellen Bedarf überdimensioniert.

## Decision Outcome

**Gewählt: Option 2 — Per-Host-Proxy.** Löst Key-Sprawl + Vision + den Cross-Host-Schmerz
durch **Vermeidung** von Cross-Host-Abhängigkeit, mit begrenztem Blast-Radius und ohne App-Code.

**Mechanik (bewiesen im Pilot):**
- Container `litellm-proxy` je Host (`ghcr.io/berriai/litellm:main-stable`), `--network <host-staging/prod-net>`,
  Port 4000, **kein Host-Port** (nur netz-intern). Provider-Keys via Server-Secret (ADR-045,
  z. B. `/opt/<...>/.secrets/` oder Container-env aus SOPS) — **nur im Proxy**, nicht in Hub-Envs.
- `proxy.yaml`: `model_list` aller genutzten Modelle (groq/anthropic/openai), `api_key: os.environ/...`.
- aifw: `LLMProvider.base_url = http://<proxy>:4000` je Provider; Hub-`*_API_KEY` → nicht-geheimer
  Placeholder (Proxy hält den echten Key) → **kein Secret-Override mehr**.
- **D-Auth:** netz-intern key-los (Default, Pilot) ODER `LITELLM_MASTER_KEY` je Host (wenn das
  interne Netz nicht als Vertrauensgrenze reicht).
- **Fallback (R1):** aifw-direct-Fallback bleibt initial verdrahtet (Notfall-Key am Host),
  bis Proxy-Stabilität belegt; danach optional entfernen.

### Confirmation (Pilot-Beleg, risk-hub-staging, 2026-06-30)
Container `litellm_proxy_staging` netz-intern; aifw `base_url`→Proxy (config-only); Text **und
Vision** (`image_url`) verifiziert; `_vision_ocr` lief mit `GROQ_API_KEY=DUMMY` durch ⇒ Proxy
hält den echten Key, App braucht keinen. (risk-hub Issue #335, KONZ-risk-hub-005.)

## Consequences

**Good:** Key-Sprawl beendet (Hosts statt Hubs); Vision-fähig; kein App-Code; reversibel;
zentrales Cost-Logging je Host möglich; Modell-SSoT bleibt bei aifw.
**Bad:** neuer Dauerdienst je Host (Betrieb/Update); Host-lokaler Ausfall trifft alle Hubs des
Hosts (= Host-Ausfalleinheit, akzeptiert); Keys weiterhin auf den Hosts (zentralisiert, nicht eliminiert).
**Neutral:** Cost-Aggregation über Hosts ist nachgelagert; Model-Screener (ADR-223) bleibt orthogonal.

## Risiken

| # | Risiko | Gegenmaßnahme |
|---|--------|---------------|
| R1 | Proxy down → Hubs des Hosts ohne LLM | aifw-direct-Fallback initial behalten; Proxy `restart: unless-stopped` + Healthcheck |
| R2 | Zwei Routing-Wahrheiten (aifw + Proxy) | Proxy als **pass-through** (Modell von aifw), nicht als Router (SSoT-Schutz) |
| R3 | Vision nicht durchgereicht | Pilot-Akzeptanzkriterium (erfüllt); pro Modell vor Key-Abzug prüfen |
| R4 | Key liegt weiterhin am Host | als Server-Secret (ADR-045/SOPS), nicht in Hub-Envs; Rotation je Host |
| R5 | Betrieb > Nutzen bei wenig Last | per-Host (nicht zentral+HA) hält Betrieb minimal; Kill-Gate unten |

## Kill-Gate
Pro Host gilt: scheitert der Proxy-Pfad (p95-Latenz >2× direkt **oder** Vision bricht **oder**
Betriebsaufwand > eingesparter Key-/Override-Aufwand) → Rückfall auf durable Secret-Injection
(per-Hub `.env` aus einem Secret-Store) für diesen Host. Review bis 2027-01-31.

## Open Questions
- Q1: Cost-Aggregation über Hosts — separater Collector oder pro-Host-Dashboards? (nachgelagert)
- Q2: SOPS-verschlüsselte `proxy.yaml` im Repo vs. Server-lokales Secret? (ADR-045-Linie)
- Q3: `LITELLM_MASTER_KEY` ab welcher Vertrauensgrenze nötig (Host mit Fremd-Containern)?
- Q4: Rollout-Reihenfolge — staging risk-hub (live) → weitere Hubs des Staging-Hosts → Prod-Hosts.

## Rollout (phasenweise)
1. **Pilot (done):** risk-hub-staging — Proxy + aifw-base_url + Vision verifiziert.
2. **Härten:** `proxy.yaml`+Service in `docker-compose.staging.yml` (deploy-managed) + Keys via
   Server-Secret + Hub-Key→Placeholder → Override entfällt durable.
3. **Staging-Host-Fleet:** weitere aifw-Hubs des Staging-Hosts auf den host-lokalen Proxy.
4. **Prod:** Prod-Host-Proxy analog, nach Staging-Stabilität.
5. **Cleanup:** vestigialen V0-`LLM_GATEWAY_URL`-Pfad + ungenutzte aifw-Deps (fristenmanagement) entfernen.

## More Information
- Pilot/Konzept: risk-hub `docs/konzepte/KONZ-risk-hub-005.md`, Issue #335.
- Discord-`llm_gateway` (mcp-hub) ist **nicht** geeignet (text-only, nicht OpenAI-kompat) — bewusst getrennt.

---

## Externe Zweitmeinung — eingearbeitet (2026-06-30)

Externe Cross-Provider-Review via `/adr-handoff-extern` (Briefing `~/shared/adr-handoff-ADR-260-2026-06-30.md`).
**Step-5-Tagging (Mensch):** Der Review war durchweg kontext-treu (respektierte „settled",
zweifelte den Pilot nicht an) → **alle Befunde `[valid]`**, keine Fehldeutung/out-of-scope.
PRO-1…6 bestätigend (keine Änderung). Untenstehende RECs sind als **ADR-Entscheidungen**
eingearbeitet (Vor-Rollout-Gates), nicht als bloße GPT-Prosa.

| REC | ⇐ Befund | Verdikt | Entscheidung (eingearbeitet) |
|-----|----------|---------|------------------------------|
| REC-1 | AD-8 | valid | **Option 4** unten: „durable per-Hub Secret-Injection (ohne Proxy)" als vollwertige Considered Option + Vergleich. |
| REC-2 | AD-3,M28-1 | valid | **Fallback-Sunset:** aifw-direct-Fallback max. bis Ende Härte-Phase je Host; Notfall-Key nur als Server-Secret (ADR-045), NICHT in Hub-Env; Cleanup-Test „kein echter Provider-Key in Hub-Env" verpflichtend (CI-Grep). |
| REC-3 | AD-9,M28-5 | valid | **Auth-Default = `LITELLM_MASTER_KEY` je Host.** Netz-intern key-los nur erlaubt, wenn der Host **ausschließlich** vertrauenswürdige eigene Container trägt (dokumentierte Bedingung je Host). |
| REC-4 | AD-4,M28-2 | valid | **`proxy.yaml` darf NICHT fachlich routen:** model_name == aifw-Modellname (keine Alias-Semantik), **keine** providerseitigen Fallbacks/Weighted-Routing; **CI-Diff** `proxy.yaml`-Modelle ↔ aifw-`LLMModel` (Drift = Fail). Schützt SSoT (aifw = Router). |
| REC-5 | AD-6,M28-3 | valid | **Image-Pin auf Digest** (kein `main-stable`); Update nur via PR mit CVE-Check + Staging-Verifikation + dokumentiertem Rollback. |
| REC-6 | AD-5 | valid | **Q2 entschieden:** `proxy.yaml` im Repo **ohne** Secrets; Provider-Keys server-lokal via Server-Secret/SOPS (ADR-045) in die Proxy-Env. Vor breitem Rollout. |
| REC-7 | AD-7,M28-4 | valid | **ADR-115 konkret:** Proxy liefert je Host Request-/Token-/Cost-/Latency-Logs; Sammlung je Host (Dashboard) im Rollout; Entscheid „pro-Host genügt vs. Aggregator" bis 2026-12-31. |
| REC-8 | AD-1 | valid | **Degradation (neues R6):** Healthcheck + `restart: unless-stopped` + Alerting + Timeout-Budget + Fallback-Reihenfolge (Proxy→aifw-direct während Härte-Phase); erwartete Nutzerwirkung je Hub dokumentiert. |
| REC-9 | AD-10,M28-7 | valid | **Runtime-Inventur je Host VOR Key-Abzug:** aktive Hubs, Provider, Modelle, Vision-Pfade, Prod/Staging-Kritikalität, reale LLM-Last — pro Provider/Vision-Modell echter Pfad getestet. |
| REC-10 | AD-11 | valid | **ADR-223-Revision geschärft** (siehe „Abgrenzung", Con-by-Con unten). |
| REC-11 | AD-12,M28-2 | valid | **Zentrales Compose-/Config-Template** mit host-spezifischen Overlays (ein Quell-Template, kein driftendes Einzel-Setup je Host). |
| REC-12 | M28-6 | valid | **Kill-Gate messbar** (siehe unten): p95-Messfenster, Vision-Testfälle, Key-Rotations-Aufwände, Betriebsstunden/Incidents, Owner, Frist 2027-01-31. |

### Option 4 (neu): Durable per-Hub Secret-Injection (ohne Proxy)
Direkt-Calls bleiben; Provider-Keys werden je Hub aus einem zentralen Secret-Store/SOPS automatisch
+ auditierbar in `.env.<env>` injiziert (deploy-core, platform#596).
- **Pro:** beendet manuelle Overrides + Rotation-Schmerz **ohne** neuen Dauerdienst/SPOF; kleinster Eingriff.
- **Con:** löst **P2 (Cost/Usage-Logging) NICHT** auf Transport-Ebene; reduziert Key-Orte schwächer
  (Key bleibt je Hub, nicht je Host); kein zentraler Modell-/Vision-Schaltpunkt.
- **Verglichen mit Option 2 (gewählt):** Bei nur „Override-Schmerz weg" ist Option 4 ausreichend
  und billiger. Option 2 gewinnt, **sobald** zentrales Logging (ADR-115) ODER Key-Konsolidierung
  über viele Hubs/Host das Ziel ist (= aktueller Fleet-Befund). **Empfehlung bleibt Option 2**,
  aber Option 4 ist der explizite Kill-Gate-Rückfall pro Host (nicht nur Fußnote).

### ADR-223 Option-D-Cons — Con-by-Con (REC-10)
| Damaliger Con (ADR-223) | Status heute |
|---|---|
| „Zusätzlicher Container/Service" | **weiter gültig** — akzeptiert, durch per-Host begrenzt (Blast-Radius = Host) + Image-Pin/Health. |
| „Kein Auto-Discovery neuer Modelle" | **irrelevant hier** — Modellwahl bleibt bei aifw/ADR-223-Screener; Proxy ist pass-through. |
| „Kein Benchmarking" | **irrelevant hier** — Benchmarking ist ADR-223-Scope, nicht Proxy-Scope. |
| „Dupliziert aifw-Funktionalität" | **entkräftet** — Proxy dupliziert NICHT das Routing (CI-Diff erzwingt das); er ergänzt Transport + zentrale Key-Haltung + Logging, die aifw NICHT bietet. |

### Kill-Gate (operationalisiert, REC-12)
Pro Host scheitert der Proxy-Pfad, wenn in einem 14-Tage-Fenster eines zutrifft: **p95-Latenz
Proxy > 2× direkt** (gemessen über aifw-Usage-Log), **ODER** ein Vision-Testfall (je genutztem
Vision-Modell) bricht, **ODER** >2 Proxy-bedingte Incidents/Monat, **ODER** Betriebsaufwand
(Updates+Incidents h) > eingesparter Key-/Override-Aufwand. → Rückfall auf **Option 4** für den Host.
**Owner:** Achim Dehnert. **Review:** 2027-01-31.
