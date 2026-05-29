# ADR-194 Review: Universal LLM Call Logging via Gateway Choke-Point

**Reviewer**: Claude Opus 4.7 (Sparring Review)
**Datum**: 2026-05-11
**ADR**: ADR-194 — Universal LLM Call Logging via Gateway Choke-Point (v1.0, proposed)
**Reviewer-Note**: Sparring durch die LLM-Instanz, die den ADR selbst entworfen hat — bewusst adversarial, sucht Schwächen im eigenen Vorschlag.
**Gesamturteil**: ⚠ **REVISIONS REQUIRED** — 1 Blocker, 2 Kritisch, 4 Hoch. Architektonische Richtung stimmt, aber drei substanzielle Lücken (Auth-Modell, Dedup-Story P2, Fallback bei Gateway-Ausfall) müssen vor Acceptance geschlossen werden.

---

## 1. Review-Tabelle

| # | Befund | Severity | Bereich |
|---|--------|----------|---------|
| B-01 | Auth-Modell beschreibt **zwei widersprüchliche Produkte** in einem Satz: "validates locally if we issue our own keys, or forwards verbatim for BYOK". Das sind unterschiedliche Finanz- und Sicherheitsmodelle — nicht beide gleichzeitig | **BLOCKER** | Architektur/Security |
| K-01 | Dedup-Story für **P2-Übergangsphase ist kaputt**: Stop-Hook schreibt `source='claude_code'`, Gateway schreibt `source='llm_gateway'`. UNIQUE INDEX `(source, request_id)` greift nicht → 4 Wochen lang doppelt erfasste Kosten in Dashboard | **KRITISCH** | Correctness |
| K-02 | Consequence "Audit trail — Sec/legal can inspect prompts + responses centrally" **widerspricht Non-Goal** "Token-level prompt inspection / DLP". Eines davon muss raus | **KRITISCH** | Konsistenz |
| H-01 | Streaming-Passthrough mit Usage-Extraktion in **3 Tagen** ist zu knapp kalkuliert. Anthropic-SSE hat 7 Event-Typen; `input_tokens` kommt in `message_start`, `output_tokens` im `message_delta`; gleichzeitig muss byte-faithful weitergestreamt werden → Realistisch 5–7 Tage | **HOCH** | Effort |
| H-02 | Phase **P3 Fallback unvollständig**: nach Entfernung des `aifw.service` INSERT-Pfads ist bei Gateway-Ausfall weder LLM-Call möglich noch logging-Fallback dokumentiert | **HOCH** | Robustheit |
| H-03 | Latenz-Claim "+30–50 ms p95" **unbelegt**. Vor Acceptance: P0-Messung gegen prod-Anthropic-Endpoint vs prod-Gateway-Endpoint, sonst sind die Negative-Consequences fiktional | **HOCH** | Methodik |
| H-04 | Drift-Check **LLM-002 ist nicht enforce-bar**: Workstation `~/.bashrc` ist nicht im VCS, CI sieht das nicht. Entweder droppen oder durch `claude doctor`-style Local-Check ersetzen | **HOCH** | Compliance |
| M-01 | Headless-CLI-Pfad fuzzy: "logging via gateway preferred when CLI honors ANTHROPIC_BASE_URL; fallback remains bridge.py" → **gleiches Dedup-Problem wie K-01** für `headless.claude` vs `llm_gateway` | **MEDIUM** | Correctness |
| M-02 | Cache-Pricing-Multipliers "1.25x/2x/0.1x" **ohne Quellenangabe**. Per Anthropic-Pricing 2026-05 korrekt, aber ADR muss zitieren oder Test mit gepinntem Snapshot referenzieren | **MEDIUM** | Belege |
| M-03 | Provider-Scope unklar: Decision Drivers nennt "Anthropic, OpenAI, OpenRouter, Cerebras". OpenRouter ist OAI-compatible (✓), Cerebras hat eigene API. Welche Provider in MVP, welche deferred? | **MEDIUM** | Scope |
| M-04 | Inkonsistenz: Frontmatter listet **8 consumers**, Body sagt **"19 platform repos"**. Reconcile | **MEDIUM** | Frontmatter |
| M-05 | HA-Plan "2 Replicas hinter nginx" → **Kosten und Ops-Aufwand nicht quantifiziert**. Falls Gateway nicht HA-betrieben wird, ist das ein zweiter Single-Point-of-Failure | **MEDIUM** | Betrieb |
| M-06 | Phase **P5 Retirement** hat keinen klaren Gate-Kriterium: "after one billing cycle with zero discrepancy" — was misst "discrepancy", welche Toleranz, welcher Query? | **MEDIUM** | Betrieb |
| N-01 | Effort-Schätzungen ohne Confidence-Intervall — 6.5 PT total ist plausibel, aber bei Streaming-Komplexität (H-01) liegt p90 wahrscheinlich näher bei 9–10 PT | **NIT** | Planung |

---

## 2. Detailbefunde

### B-01: Auth-Modell ist zwei Produkte in einem Satz — BLOCKER

**Zitat** (§ "Gateway extensions required", Punkt 3):
> "gateway accepts the user's `x-api-key` header, validates it locally if we issue our own keys, **or** forwards verbatim for BYOK. Keys are not stored beyond a salted hash for attribution."

**Problem**: Das sind zwei grundverschiedene Designs:

| Variante A: Eigene Keys | Variante B: BYOK-Passthrough |
|---|---|
| Wir kaufen Anthropic-Credits; User kriegen interne Keys mit Quota | User bringt eigenen Anthropic-Key, wir zahlen nichts |
| Attribution per User-Key trivial | Attribution nur per `source` möglich; Hashing wozu? |
| Wir können Rate-Limits/Budgets pro User erzwingen (ADR-116 anwendbar) | Quotas/Limits liegen bei Anthropic des Users |
| Finanz-Risiko: wir haften für jeden Token | Finanz-Risiko: nur Infra |
| Security-Audit: wir lagern Anthropic-Keys | Security: wir leiten User-Keys durch, müssen sie nicht speichern |

Beide gleichzeitig anzubieten verdoppelt die Komplexität des Gateways und macht die ADR-116-Budget-Story unklar (welcher Budget greift bei BYOK-User der mit eigenem Geld zahlt?).

**Fix**: ADR muss **eine** Variante wählen. Empfehlung: Variante A (eigene Keys) — passt zu ADR-115/116 Budget-Konzept, klare Attribution, klare Finanzlage. BYOK kann als zukünftiger ADR separat behandelt werden. Falls B gewählt: ADR-116 Budget-Tracking explizit als "only for org-issued keys" annotieren.

---

### K-01: Dedup während P2-Übergangsphase ist kaputt — KRITISCH

**Zitat** (Migrationsplan P2):
> "Stop hook stays as defense-in-depth for 4 weeks; logs duplicate calls become a comparison check."

Plus Risiko-Mitigation:
> "Use `request_id` for global dedupe; add UNIQUE INDEX `(source, request_id)` to `llm_calls` as part of P1"

**Problem**: Wenn Stop-Hook `source='claude_code'` schreibt und Gateway `source='llm_gateway'` (oder `claude_code` mit anderem Tag), erzeugt UNIQUE-Constraint **keinen Konflikt** — beide Rows landen in der Tabelle. 4 Wochen lang zeigt das Dashboard ~2× Claude-Code-Cost. Das ist nicht "comparison check", das ist Müll-Datum.

**Lösungsvarianten**:
1. **Beide Writer schreiben denselben `source`** (z.B. `claude_code`), UNIQUE Index greift, doppelter Eintrag wird verworfen.
2. **Hook deaktiviert sich**, wenn `ANTHROPIC_BASE_URL` gesetzt ist → Gateway ist single Source, Hook nur als Fallback bei `unset`.
3. **Comparison-View**: Hook schreibt in eine Shadow-Tabelle `llm_calls_shadow`, nicht ins Haupt-Set; Cron-Job diffed nightly.

**Fix**: ADR muss eine Variante wählen und die UNIQUE-Constraint-Definition mit dem Migrationsplan konsistent machen. Empfehlung: Variante 2 (Hook self-disables) — sauberster Cutover, kein Drift-Risiko.

Gleiches Problem in M-01 für Headless-CLI-Pfad.

---

### K-02: "Audit trail" widerspricht Non-Goal — KRITISCH

**Zitat** (Consequences/Positive):
> "Audit trail. Sec/legal can inspect prompts + responses centrally (with retention/redaction policies set in one place)."

**Zitat** (Non-goals):
> "Token-level prompt inspection / DLP. A future ADR may add prompt-content auditing in the gateway; this ADR limits scope to usage/cost."

**Problem**: Wenn der Gateway nur `usage`/`cost` loggt, kann Sec/Legal **keine prompts/responses inspizieren**. Der Audit-Trail-Vorteil ist im aktuellen Scope eine Lüge.

**Fix**: Entweder
- (a) prompt/response-Storage in Scope nehmen (eigener § "Prompt Retention Policy"), oder
- (b) Audit-Trail-Vorteil herunterziehen auf "usage/cost audit", Sec/Legal-Anspruch streichen.

Empfehlung: (b) für v1.0 — Prompt-Storage ist DLP-/DSGVO-Thema und braucht eigenen ADR mit Legal-Review.

---

### H-01: Streaming-Effort unterkalkuliert — HOCH

**Zitat** (P1):
> "Gateway: add `/v1/messages` passthrough + streaming + cache pricing. 3 d"

**Problem**: Anthropic-SSE-Streams emittieren in der Reihenfolge:
1. `message_start` — enthält `usage.input_tokens` + `cache_creation_input_tokens` + `cache_read_input_tokens`
2. `content_block_start`, `content_block_delta`, `content_block_stop` (×N)
3. `message_delta` — enthält finale `usage.output_tokens`
4. `message_stop`

Der Gateway muss:
- Stream-Events parsen WHILE byte-faithful streamt (Client darf keine Latenz spüren)
- Usage aus zwei verschiedenen Events aggregieren
- Bei Abbruch (Client disconnect, upstream-500) trotzdem partielle Usage loggen — sonst gehen Costs verloren
- Tests gegen anthropic-sdk Test-Fixtures (Mock-Stream-Generator)

Realistisch: **5–7 Tage**, nicht 3. Bei 3 Tagen kommt entweder schlechte Implementierung oder die Tests werden gekürzt.

**Fix**: Effort auf 5–7 d hochsetzen oder Streaming explizit auf P1.1 (Folge-Phase) verlagern, P1 nur non-streaming.

---

### H-02: P3 Fallback bei Gateway-Ausfall unvollständig — HOCH

**Zitat** (P3):
> "remove `aifw.service` INSERT path; keep cost-computation utility for compatibility"

Plus Risk-Mitigation:
> "When the gateway is unreachable, the system should degrade to direct provider calls plus best-effort local logging — never block work."

**Problem**: Wenn `aifw.service` den INSERT-Pfad ENTFERNT hat, gibt es bei Gateway-Down kein "best-effort local logging" mehr — der INSERT-Code existiert nicht mehr im Codebase.

**Optionen**:
1. INSERT-Pfad behalten als **disabled-by-default Fallback**, aktiviert wenn Gateway-Health-Check rot
2. Bei Gateway-Down: direkt zu Anthropic, **gar nicht loggen** (akzeptierter Verlust)
3. Bei Gateway-Down: Calls **blockieren** (Verfügbarkeits-Trade-off zu Gunsten Logging-Vollständigkeit)

**Fix**: Eine Variante wählen und in P3 spezifizieren. Empfehlung: (1) — INSERT-Pfad als Notausgang bleibt in Codebase, mit `if not gateway_reachable():` Guard.

---

### H-03: Latenz-Claim unbelegt — HOCH

**Zitat** (Negative Consequences):
> "Latency tax. Adding one HTTP hop. Measure during P1; budget +30–50 ms p95."

**Problem**: Das ist Schätzung, keine Messung. P1 misst — aber wenn die Messung +200 ms zeigt, ist Acceptance auf falscher Basis erfolgt.

**Fix**: **Vor Acceptance**: 100-Call-Microbenchmark gegen `api.anthropic.com` direkt vs via `llm-gateway.iil.pet` (mit echtem TLS + Network-Path). Resultat in ADR aufnehmen, ggf. Decision revisiten.

---

### H-04: LLM-002 Drift-Check unenforce-bar — HOCH

**Zitat** (Compliance/Drift Checks):
> "LLM-002 (warning): Workstation shell profile missing `ANTHROPIC_BASE_URL` once P2 ships."

**Problem**: Workstation-`~/.bashrc` ist nicht im Repo. CI kann das nicht prüfen. iil-codeguard (per ADR-191) ist library-first auf Repo-Code, nicht auf Workstation-Config.

**Fix**: Entweder
- droppen und durch Runtime-Check ersetzen (`claude doctor`-equivalent das beim Session-Start ANTHROPIC_BASE_URL prüft), oder
- in versionsverwalteten dotfiles-Repo verschieben, dort von codeguard checken.

---

### M-01: Headless-CLI Dedup unklar — MEDIUM

**Zitat** (Required changes):
> "Same — these wrap CLIs we do not control. Logging via gateway is preferred when CLI honors `ANTHROPIC_BASE_URL`; fallback remains `bridge.py`"

**Problem**: Gleiches Dedup-Problem wie K-01. Claude Code CLI honoriert `ANTHROPIC_BASE_URL`. Wenn `bridge.py` weiter post-hoc INSERTet UND Gateway loggt → doppelte Rows mit unterschiedlichem `source` (`headless.claude` vs `llm_gateway`).

**Fix**: Headless-Pfad explizit klären — same self-disable Mechanism wie für Stop-Hook empfohlen.

---

### M-02 / M-03 / M-04 / M-05 / M-06

Klein aber sammeln sich:
- **M-02**: Pricing-Multipliers zitieren (Anthropic Pricing Page URL + Datum) oder Pricing-Test mit Snapshot.
- **M-03**: Provider-Scope-Tabelle in P1 mit "MVP/Deferred"-Spalte.
- **M-04**: Consumer-Liste sync (Frontmatter ≈ Body).
- **M-05**: HA-Cost zumindest Größenordnung ("2× Container, ~€10/Monat, +0.5h Ops/Monat").
- **M-06**: P5 Gate-Kriterium konkretisieren: "discrepancy" definieren (z.B. `|gateway_count − hook_count| / hook_count < 1% über 7 Tage`).

---

## 3. Was am ADR stark ist

Damit der Review nicht nur Tadel ist:

- **Problem ist quantifiziert**: 658 unsichtbare Calls = $125 in 4 Tagen ist ein harter Beleg, nicht Hypothese.
- **Options A/B/C ehrlich**: insbesondere Option C (eBPF/Envoy) wird korrekt als unpragmatisch abgelehnt.
- **Non-Goals explizit**: spart spätere Scope-Kämpfe.
- **Migration in Phasen mit Feature-Flag (AIFW_USE_GATEWAY)**: Rollout-Risiko sauber gemanagt.
- **Drift-Checks LLM-001/003 sind konkret und testbar**.
- **Anknüpfung an ADR-178** ist sauber — kein paralleler Gateway, sondern Ausbau des bestehenden.

---

## 4. Empfohlenes Vorgehen

1. **Pre-Acceptance** (½ Tag Aufwand):
   - B-01: Auth-Modell festlegen (Empfehlung: Variante A — eigene Keys)
   - K-01: Dedup-Strategie wählen (Empfehlung: Hook self-disables bei `ANTHROPIC_BASE_URL` gesetzt)
   - K-02: Audit-Trail-Claim runterziehen oder Prompt-Storage in Scope nehmen
   - H-02: P3-Fallback spezifizieren
   - H-03: Latenz-Messung durchführen, Werte ins ADR

2. **Acceptance** mit den Korrekturen → v1.1.

3. **Bei v1.1**: M-01..M-06 in den gleichen Pass mit aufnehmen, kostet ~1h.

4. **Verbleibendes Risiko nach v1.1**: hauptsächlich H-01 (Streaming-Effort) — fließt in Sprint-Planung, nicht ADR.

---

## 5. Tool-Bug-Notiz (separat)

`mcp__orchestrator__review_adr` schlägt fehl mit:
```
litellm.BadRequestError: LLM Provider NOT provided. 
You passed model=claude-3-5-sonnet-20241022
```
LiteLLM erwartet Provider-Prefix (`anthropic/claude-3-5-sonnet-20241022`). Fix in `mcp-hub/orchestrator_mcp/server.py` oder dem ADR-Review-Handler — Modell-String beim LLM-Call mit `anthropic/`-Prefix versehen. Ticket empfohlen.
