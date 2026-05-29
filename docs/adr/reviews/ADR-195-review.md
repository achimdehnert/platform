# ADR-195 Review: LiteLLM-Proxy as Logging Engine + Anthropic Admin API as Truth Anchor

**Reviewer**: Claude Opus 4.7 (Sparring Review)
**Datum**: 2026-05-11
**ADR**: ADR-195 — LiteLLM-Proxy as Engine + Admin API as Truth (v1.0, proposed)
**Reviewer-Note**: Sparring durch dieselbe LLM-Instanz, die ADR-195 als Reaktion auf das ADR-194-Review entworfen hat. Bewusst adversarial gegen den eigenen Vorschlag. **Bias-Warnung**: Selbstreview hat strukturell schwächere Adversarialität als Cross-Review — finale Acceptance sollte einen unabhängigen menschlichen Reviewer (Achim) einschließen.
**Gesamturteil**: ⚠ **REVISIONS REQUIRED** — 1 Blocker, 3 Kritisch, 4 Hoch. Architektonische Richtung ist deutlich gesünder als ADR-194, aber drei tragende Annahmen sind nicht validiert (LiteLLM-Callback-API, Per-Source-Key-Delivery, Provider-Symmetrie) und das "Sidecar überall" ist Ops-seitig zu optimistisch kalkuliert.

---

## 1. Review-Tabelle

| # | Befund | Severity | Bereich |
|---|--------|----------|---------|
| B-01 | **Tragende Annahme nicht validiert**: ADR-195 baut ganze Pipeline auf LiteLLM `success_callback` — aber kein Probe-Test gegen LiteLLM zeigt, dass `cache_creation.ephemeral_5m_input_tokens`, `cache_creation.ephemeral_1h_input_tokens`, `cache_read_input_tokens` UND streaming-aggregierte Usage tatsächlich im Callback-Payload landen. Wenn nicht: P5 ist Reverse-Engineering, nicht 1 PT | **BLOCKER** | Architektur-Annahme |
| K-01 | **Tool-Wahl ADR-fixiert, aber Spike erst in P4**: ADR sagt "LiteLLM oder Helicone, finale Wahl in P4". Falls Helicone gewählt → komplett anderer Callback-Mechanismus, andere Schema-Annahmen. Architektur-Entscheidung darf nicht *nach* ADR-Acceptance passieren | **KRITISCH** | Prozess |
| K-02 | **Asymmetrische Provider-Coverage**: Truth-Anchor (Admin API) ist Anthropic-only. OpenAI/OpenRouter/Cerebras-Calls landen nur in LiteLLM-Callback ohne Reconcile. Wenn Callback dort einen Bug hat, fällt das nicht auf — kein Drift-Alarm möglich | **KRITISCH** | Coverage |
| K-03 | **Per-Source-Key-Delivery ungelöst**: ADR listet 5 Keys, sagt aber nicht WIE sie an Cascade-BYOK (Windsurf-UI?), Ad-hoc-Scripts (`.envrc`? PyPI-Lib?), Headless-CI-Runner (Secrets-Injection?) verteilt werden. Operativer Kern fehlt | **KRITISCH** | Betrieb |
| H-01 | **P4-Effort 0.5 d für Sidecar auf 3 Host-Typen ist optimistisch**: Workstation (Docker), Dev/Prod-Hetzner (systemd), Headless-CI-Runner (?). Realistisch 1.5–2 d inkl. systemd-Unit, Health-Check, Auto-Restart, Update-Mechanismus | **HOCH** | Effort |
| H-02 | **Stop-Hook-Self-Disable kann Silent-Gap erzeugen**: Wenn `ANTHROPIC_BASE_URL` gesetzt aber Sidecar tot → Hook feuert nicht, Anthropic-Call schlägt fehl, Logging ebenfalls aus. Schlechter als heutiger Stand (Hook würde mindestens Transcript loggen) | **HOCH** | Robustheit |
| H-03 | **Reconcile-Threshold "1 % über 7 Tage" undefiniert**: Über was 1 %? Tokens? USD? Pro Key? Aggregat? Pro Modell? Welcher Query? Gleiche Kritik wie M-06 im ADR-194-Review — nicht gefixt, nur portiert | **HOCH** | Spezifikation |
| H-04 | **Admin-Key-Rotation/Access nicht spezifiziert**: Admin-Key ist Crown-Jewel (kann jeden Workspace-Key listen + Spend lesen). ADR sagt "store with same care as production secrets" — das ist Versprechen, kein Mechanismus. Rotation-Intervall? Audit-Log-Pflicht? Single-Laptop-Verlust-Szenario? | **HOCH** | Security |
| M-01 | **`action_code`-Attribution für Ad-hoc-Scripts unverändert**: Header `x-litellm-metadata` setzt instrumentierter Code. Direkter `import anthropic` ohne Wrapping setzt nichts. ADR claimt verbesserte Attribution — gilt nur für aifw/agent_team, also Status quo | **MEDIUM** | Claim-Realität |
| M-02 | **`source='litellm'` kollidiert mit ADR-115-Taxonomie**: Bestehende Dashboard-Queries filtern auf `source IN ('aifw', 'agent_team', 'claude_code', ...)`. Neuer Wert `litellm` ist erstens generisch (welcher Caller?), zweitens bricht Filter | **MEDIUM** | Schema-Konsistenz |
| M-03 | **Bootstrap-Paradox nur teilweise gelöst**: Sidecar auf Workstation läuft auch bei Prod-Down — aber Claude Code → MCP-Hub (prod) → kaputt. Path "CC nutzt lokalen MCP-Hub" nicht spezifiziert | **MEDIUM** | Architektur |
| M-04 | **ADR-116-Replacement-Claim überzogen**: "Anthropic-side spend limits replace most of ADR-116" — ADR-116 ist Dynamic Model Router mit Budget-aware Routing, nicht nur Spend-Cap. Routing-Logik bleibt komplett erforderlich | **MEDIUM** | Claim-Genauigkeit |
| M-05 | **Headless-CLI (`bridge.py`) Dedup unklar**: Gleiche Lücke wie M-01 in ADR-194-Review. Wenn Headless-Claude-CLI `ANTHROPIC_BASE_URL` honoriert: doppelter Eintrag. Wenn nicht: bridge.py + Admin API = doppelt. Strategie fehlt | **MEDIUM** | Correctness |
| M-06 | **Admin-API-Rate-Limit unverifiziert**: ADR sagt "well under limits" ohne Zahl. Mehrere Workspaces × häufiges Polling × Beta-Header → reale Limits prüfen vor Acceptance | **MEDIUM** | Belege |
| M-07 | **`llm_calls_reconcile`-Schema fehlt**: Neue Tabelle mentioned, kein DDL. Storage-Growth-Schätzung? Retention? Unique-Constraint? | **MEDIUM** | Schema |
| N-01 | **Acceptance-Gate undefiniert**: "implementation begins after acceptance" — wer akzeptiert, welches Quorum, welcher Review-Gate? Selbstreview reicht nicht (siehe Reviewer-Note oben) | **NIT** | Prozess |
| N-02 | **5 Keys vs. Workspaces-Frage offen gelassen**: "Open Questions #2" — aber Phase P3 macht es trotzdem. Reihenfolge: erst entscheiden, dann ausführen | **NIT** | Reihenfolge |

---

## 2. Detailbefunde

### B-01: LiteLLM-Callback-Payload nicht validiert — BLOCKER

**Zitat** (Architektur):
> "success_callback → eurer Callback-Code → INSERT into llm_calls"

Plus P5:
> "Write callback module: reads LiteLLM `success_callback` payload → applies `pricing.py` → INSERT into `llm_calls`. 1 d"

**Problem**: Die *gesamte* Per-Call-Pipeline hängt davon ab, dass LiteLLM im `success_callback` folgende Felder mit korrekten Werten liefert:

| Erforderlich | LiteLLM liefert? |
|---|---|
| `uncached_input_tokens` | wahrscheinlich (`prompt_tokens` Mapping) |
| `output_tokens` | wahrscheinlich (`completion_tokens`) |
| `cache_creation.ephemeral_5m_input_tokens` | **unklar** — LiteLLM normalisiert Anthropic-spezifisch? |
| `cache_creation.ephemeral_1h_input_tokens` | **unklar** — 1h-Tier ist neu (2026) |
| `cache_read_input_tokens` | wahrscheinlich |
| Streaming-aggregierte Usage (final delta) | **unklar** — LiteLLM hat hier historisch Bugs |
| Anthropic `request_id` für Reconcile | **unklar** |

Wenn auch nur eines der `cache_*`-Felder fehlt: Pricing-Math ist falsch (ADR-115-Schema hat eigene Spalten dafür), und Reconcile-Drift-Alarm feuert ständig.

**Fix**: **Vor Acceptance**: 30-Zeilen-Probe-Test gegen lokalen LiteLLM-Proxy mit echtem Anthropic-Call inkl. Cache-Hit und Streaming. Payload-Schema dokumentieren. Falls Felder fehlen: Strategie (LiteLLM-Plugin? Eigener HTTP-Middleware? Fork?) ins ADR — ändert Effort-Schätzung von P5 signifikant.

---

### K-01: Tool-Wahl nach ADR-Acceptance ist Anti-Pattern — KRITISCH

**Zitat** (Open Questions):
> "LiteLLM-Proxy vs Helicone — final choice deferred to P4 spike (½ day)."

Plus Architektur-Diagramm zeigt explizit "Local LiteLLM-Proxy sidecar".

**Problem**: ADR-195's Diagram, P4-P5-Aufwand, Callback-Modell, Header-Konvention (`x-litellm-metadata`) sind allesamt LiteLLM-shaped. Wenn der P4-Spike Helicone wählt:

- Helicone-Callback-Architektur ist anders (Edge-Functions + Webhooks, kein Python-Callback)
- Header-Convention ist `helicone-property-*`
- Self-Hosting-Footprint ist um Größenordnung größer (ClickHouse + Kafka)
- P5 (Callback-Modul) muss komplett neu geschrieben werden

Das ist nicht "Open Question", das ist **die Kern-Entscheidung des ADRs**.

**Fix**: Entweder
- (a) ADR auf LiteLLM committen, Helicone aus Optionen rauswerfen (Belege: bereits in `mcp-hub`-Python-Deps, leichtester Footprint, OpenAI-Adapter-Übersetzer matched unsere Multi-Provider-Story), oder
- (b) ADR-195 in zwei ADRs splitten: ADR-195a "Engine-Spike" + ADR-195b "Final architecture after spike".

Empfehlung: (a) — entscheide jetzt, dokumentiere LiteLLM-Wahl in ADR-195.

---

### K-02: Provider-Asymmetrie bei Truth-Anchor — KRITISCH

**Zitat** (Architektur, Reconcile-Komponente):
> "Anthropic Admin API → llm_calls_reconcile → diff vs llm_calls"

**Problem**: Admin API ist **Anthropic-only**. Drift-Detection für OpenAI / OpenRouter / Cerebras-Calls existiert in ADR-195 nicht. Das heißt:

- OpenAI-Spend via LiteLLM-Callback → nur LiteLLM-Wahrheit, kein Cross-Check
- Wenn LiteLLM dort einen Streaming-Bug hat → unerkannt
- "ADR-195 löst das Truth-Source-Problem" gilt nur für Anthropic

OpenAI hat seit 2024 eine **Usage-API** (`/v1/organizations/{org_id}/usage`) mit ähnlicher Funktionalität. ADR-195 erwähnt sie nicht.

**Fix**: ADR-195 muss entweder
- (a) Scope auf "Anthropic-only" reduzieren, OpenAI als separates Folge-ADR, oder
- (b) OpenAI Usage API in den Reconcile-Job aufnehmen (zusätzlicher Effort ~0.5 PT).

Empfehlung: (b) — der Reconcile-Job ist eh ein Poller; einen zweiten Provider hinzuzufügen kostet wenig, und Symmetrie ist Eigenwert. Wenn (a): explizit dokumentieren, dass für non-Anthropic-Provider "trust LiteLLM" gilt.

---

### K-03: Per-Source-Key-Delivery ist Operationale Lücke — KRITISCH

**Zitat** (P3):
> "Create per-source Anthropic keys + set Anthropic-side spend limits. Inventory which keys land where."

**Problem**: "Inventory which keys land where" ist Hand-Wave. Konkret:

| Source | Key-Bezug heute | ADR-195 spezifiziert? |
|---|---|---|
| `aifw` Service auf Prod | `~/.secrets/anthropic_api_key` (gemeinsam) | ❌ wie kommt `key_aifw` exklusiv dahin? |
| Claude Code Workstation | Anthropic Console Login (OAuth) | ❌ Workstation hat schon Key über CC-Auth — soll der ersetzt werden? |
| Cascade BYOK in Windsurf-App | Windsurf-UI-Setting (nicht im Repo) | ❌ wer setzt das, wie wird Drift verhindert? |
| Ad-hoc Python Scripts | `import anthropic; client = Anthropic()` liest `ANTHROPIC_API_KEY` env | ❌ wer setzt env zu `key_scripts`? |
| Headless-CI-Runner (GitHub Actions) | Repo-Secret | ❌ pro Repo welcher Key? |
| `agent_team` MCP auf Prod | `~/.secrets/anthropic_api_key` | ❌ separater Key? |

ADR-194-Review-H-04 hat die selbe Klasse Problem ("Workstation `.bashrc` nicht enforce-bar") als BLOCKER kritisiert. ADR-195 portiert genau dieses Problem auf 5 Keys × 3 Host-Typen.

**Fix**: ADR muss konkrete Key-Delivery-Strategie pro Source spezifizieren:
- Workstation: dotfiles-Repo unter Version-Control, `direnv`-basierte Pro-Repo-Overrides
- Server: `~/.secrets/`-Subfolder pro Service + systemd `EnvironmentFile=`
- Windsurf: nicht enforce-bar → akzeptieren, Drift-Detection via Admin-API-`group_by=api_key_id` zeigt falsche Keys
- CI: `gh secret set` pro Repo, Sync-Script

Ohne diese Tabelle ist P3 = wishful thinking.

---

### H-01: P4-Sidecar-Effort optimistisch — HOCH

**Zitat** (P4):
> "Deploy LiteLLM-Proxy as sidecar on workstation + dev + prod (Docker compose). 0.5 d"

**Problem**: 0.5 d für drei Deployment-Targets ist nur realistisch wenn alles glatt läuft. Realität:

- **Workstation**: Docker laufen lassen, Port 4000 frei, Auto-Start beim Boot, Log-Rotation, Update-Mechanismus
- **Dev/Prod Hetzner**: systemd-Unit, EnvironmentFile mit Keys, Health-Check-Endpoint, restart-on-failure, Monitoring-Integration (existierender Grafana-Stack)
- **Headless-CI-Runner**: Sidecar pro Job oder Shared-Container? Wenn shared: Auth pro Job. Wenn pro Job: Cold-Start-Kosten.
- **Konfiguration**: LiteLLM `proxy_config.yaml` ins Repo, mit Substitutionen pro Host
- **Erste-Tag-Bugs**: Streaming-Edge-Cases, TLS-Termination, Connection-Pooling

Realistisch: **1.5–2 d**. Bei 0.5 d wird's halbgar oder Tests werden gekürzt.

**Fix**: P4 auf 1.5 d erhöhen oder explizit "Headless-CI-Runner" auf P-N (later) schieben.

---

### H-02: Stop-Hook-Self-Disable erzeugt Silent-Gap — HOCH

**Zitat** (P4):
> "Stop hook stays active as DEFENSE-IN-DEPTH but self-disables when `ANTHROPIC_BASE_URL` is set"

**Problem**: Scenarien:
- ✅ Normal: ENV gesetzt + Sidecar läuft → LiteLLM loggt, Hook still
- ❌ ENV gesetzt + Sidecar TOT → Anthropic-Call schlägt fehl, Hook trotzdem still (kein Transcript-Logging mehr), User merkt's spät
- ❌ ENV gesetzt + Sidecar antwortet aber Callback bricht silent → kein Log, Hook still

Heutiger Status quo: Hook *immer* aktiv, Transcript wird *immer* geschrieben (auch wenn API-Call fehlschlägt — Transcript zeigt Error). ADR-195 macht das schlechter.

**Fix**: Hook-Self-Disable-Logik präziser: Hook deaktiviert sich nur wenn (a) ENV gesetzt UND (b) Sidecar-Health-Check innerhalb der letzten 60s grün UND (c) Callback-Liveness-Beacon (Counter in `llm_calls_reconcile`) erhöht sich. Sonst: Hook bleibt aktiv, schreibt mit `source='claude_code_fallback'`, Reconcile-Job dedupliziert per `request_id` falls Anthropic-Response erhalten.

Alternative: Hook bleibt **immer** aktiv, schreibt in Shadow-Tabelle `llm_calls_shadow`. Reconcile vergleicht beide. Kein Silent-Gap-Risiko. Kosten: Shadow-Tabelle Storage.

---

### H-03: Reconcile-Threshold undefiniert (M-06 aus ADR-194 nicht gefixt) — HOCH

**Zitat** (Compliance/Drift Checks):
> "`LLM-003` (warning): `llm_calls_reconcile` drift > 1 % over 7 days → alert."

**Problem**: Exakt dieselbe Kritik wie M-06 im ADR-194-Review — und auch hier nicht aufgelöst:
- 1 % wovon? Token-Count? USD?
- Aggregat über alle Sources? Pro Source? Pro Modell?
- Welcher SQL-Query liefert "drift"?
- Was zählt als "Alert" — Slack? Grafana-Panel rot? Pager?

**Fix**: Konkrete Definition ins ADR:
```sql
-- Beispiel-Definition:
WITH daily AS (
  SELECT date_trunc('day', ts) AS d, source, model,
         SUM(cost_usd) AS gw_cost
  FROM llm_calls
  WHERE source != 'admin_api'
  GROUP BY 1,2,3
),
truth AS (
  SELECT date_trunc('day', ts) AS d, model,
         SUM(cost_usd) AS truth_cost
  FROM llm_calls_reconcile
  GROUP BY 1,2
)
SELECT d, model, gw_cost, truth_cost,
       ABS(gw_cost - truth_cost) / NULLIF(truth_cost,0) AS drift
FROM daily JOIN truth USING (d, model)
WHERE drift > 0.01
```
Plus: Toleranz pro Modell (kleine Modelle mit niedrigen Kosten haben höhere Relative-Drift bei kleinen Absolute-Diffs — vielleicht 5 % unter $1/Tag).

---

### H-04: Admin-Key-Security unterspezifiziert — HOCH

**Zitat** (Risks):
> "Admin keys are highest privilege — store with same care as production secrets; rotation procedure documented"

**Problem**: "Documented" ohne Mechanismus = nicht passiert. Konkrete Lücken:

- **Rotation-Intervall**: 90 Tage? 30? Nie?
- **Wer hat Zugriff**: Achim only? Service-Account auf welchem Host?
- **Audit**: Anthropic-Console-Login-Logs reichen? Wir loggen lokale `cat` auf den Key nicht
- **Compromise-Recovery**: Was tun wenn `~/shared/secrets-inbox/anthropic_admin_api_key` leaked? Revoke + neuer Key + alle laufenden Reconcile-Jobs swappen — Prozedur fehlt
- **Single-Laptop-Risk**: Wenn der Key nur auf der Workstation liegt und Laptop verloren geht → einer kann Org-Spend einsehen und (laut Admin-API-Doku) Workspaces verwalten

**Fix**: Konkrete Section "Admin Key Lifecycle":
- Rotation: 90 Tage, Reminder via Cron
- Storage: `~/shared/secrets-inbox/anthropic_admin_api_key` (chmod 600), ZUSÄTZLICH Bitwarden/1Password-Backup
- Access: nur Reconcile-Job-Service-User, kein interaktiver Read
- Revocation-Runbook: ein Markdown-File in `~/github/platform/docs/runbooks/`

---

### M-01..M-07

Zusammengefasst, jeweils ein Satz Fix:

- **M-01** (action_code für ad-hoc): ADR ehrlich umformulieren — `action_code`-Coverage bleibt ~Status quo, nur Cost-Coverage wird 100 %.
- **M-02** (`source='litellm'`): Source-Wert sollte den *ursprünglichen* Caller reflektieren, nicht das Transport-Layer. Vorschlag: LiteLLM-Callback liest `x-source` Header → schreibt `source` entsprechend (`'cascade_byok'`, `'claude_code'`, etc.). `'litellm'` als Wert vermeiden.
- **M-03** (Bootstrap-Paradox): Anmerkung im ADR — Sidecar löst nur den *Anthropic-Hop*, nicht MCP-Hub-Abhängigkeit. Für letzteres: separate Diskussion.
- **M-04** (ADR-116-Claim): Formulierung weicher — "Anthropic-side spend limits ergänzen ADR-116 als Hard-Cap, ersetzen aber nicht die Routing-Logik".
- **M-05** (bridge.py): Explizit gleiche Self-Disable-Logik wie für Stop-Hook (H-02 oben), oder Shadow-Tabelle.
- **M-06** (Admin-API-Rate-Limit): Tatsächliche Zahl recherchieren (Anthropic Docs nennen 50 req/min für Admin-Endpoints — bei 24h-Buckets reicht 1 req/Tag, kein Problem; aber dokumentieren).
- **M-07** (Reconcile-DDL): 10-Zeilen-Schema-Skizze ins ADR.

---

### N-01: Acceptance-Gate

**Zitat**: "Implementation begins after acceptance."

**Problem**: Nicht definiert wer akzeptiert. Bei ADR-194 hat dasselbe Vakuum existiert — Acceptance war implizit "Achim sagt ok". Für ein ADR dieser Tragweite (5 Migration-Phasen, 19 Repos indirekt) sollte explizit stehen: "Acceptance Gate = Achim + 1 Maintainer-Approval + B-01 vorab gelöst".

---

## 3. Was am ADR stark ist

Damit der Review nicht nur Tadel ist:

- **Layer-Ownership-Tabelle** ist konkret und testbar — "LiteLLM owns nothing of value" ist eine klare Aussage, gegen die später gemessen werden kann
- **Anti-Lock-In-Regeln** (5 explizite Commitments) sind hands-on, nicht abstrakt
- **Sidecar statt Central-Choke** löst SPoF und Bootstrap-Paradox sauber (wenn auch nicht zu 100 %, siehe M-03)
- **Truth-Anchor-Idee** (Admin API als Cost-Source-of-Truth) ist architektonisch sauber: Anthropic = Ground Truth, alles andere = Approximation
- **Hook-Self-Disable** behebt K-01 aus ADR-194-Review (Dedup-Strategie)
- **Audit-Trail-Claim entfernt** behebt K-02 aus ADR-194-Review
- **Reconcile-Job** ist die ehrliche Validierungsmechanik die in ADR-194 komplett fehlte
- **2.5 PT vs 6.5 PT** mit datenbasierter C-Decision nach 3 Monaten ist Optionalitäts-Strategie, kein Sunk-Cost-Pfad
- **Cascade-BYOK 80%→100%** ohne Agent-Cooperation ist konkrete Verbesserung gegenüber Status quo

---

## 4. Empfohlenes Vorgehen

### Pre-Acceptance (ca. ½ Tag)

1. **B-01 lösen**: 30-Zeilen-Probe-Test gegen lokales LiteLLM, Payload-Schema für Cache-Felder + Streaming verifizieren. Ergebnis ins ADR als § "LiteLLM Callback Validation".
2. **K-01 fixen**: Auf LiteLLM committen, Helicone aus Architekturpfad streichen (kann als verworfene Alternative kurz dokumentiert bleiben).
3. **K-02 fixen**: OpenAI Usage API in Reconcile-Scope aufnehmen oder Scope explizit auf Anthropic begrenzen.
4. **K-03 fixen**: Key-Delivery-Tabelle pro Source.
5. **H-04 fixen**: Admin-Key-Lifecycle-Section.

### Acceptance mit den Korrekturen → v1.1

### Bei v1.1

- H-01..H-03 in selben Pass.
- M-01..M-07 in 1 h.

### Verbleibendes Risiko nach v1.1

- Hauptsächlich operational (Sidecar-Stabilität, Key-Rotation-Disziplin) — fließt in Runbooks, nicht ADR.

---

## 5. Selbst-Reflexions-Notiz

Dieser Review wurde vom selben Modell verfasst, das ADR-195 entworfen hat. Das ist strukturell ein schwächeres Sparring als ein unabhängiger Reviewer. Konkret riskiere ich:

- **Blindspots gegen eigene Annahmen**: Z.B. "LiteLLM Callback liefert alle Felder" wurde im ADR als Selbstverständlichkeit angenommen — der B-01-Befund fühlte sich beim Review-Schreiben wie eine Entdeckung an, hätte aber schon beim ADR-Schreiben da sein müssen.
- **Konsistenz-Pull**: Tendenz, das eigene Pattern zu verteidigen statt fundamentale Alternativen (z.B. "kein Logging, nur Admin API + Anthropic-Spend-Limits") nochmal zu prüfen.

Empfehlung: **vor Acceptance** einmal eine zweite menschliche oder anderer-Modell-Stimme drüberlaufen lassen. Achim ist faktisch der einzige Entscheider — eine 15-min-Lese-Session mit konkreten Push-Backs ("warum nicht nur Admin API ohne LiteLLM?") wäre der wertvollste nächste Schritt.
