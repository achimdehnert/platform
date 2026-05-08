---
status: proposed
date: 2026-05-08
deciders: [Achim Dehnert]
implementation_status: none
supersedes: []
related: [ADR-178, ADR-023, ADR-028, ADR-115]
---

# ADR-189: Einführung eines automatisierten LLM Model Screener & Provider Research Systems

## Status

Proposed

## Kontext und Problemstellung

Die IIL-Plattform nutzt über das `aifw`-Package (PyPI: `aifw>=0.5.0`) eine DB-gesteuerte Model-Routing-Architektur. Jeder LLM-Aufruf wird über einen *Action Code* (z.B. `begehung_photo_analysis`) an ein konfiguriertes Model geroutet. Die Zuordnung `AIActionType` → `LLMModel` wird manuell in der Django-Admin-Oberfläche gepflegt.

### Auslöser

Am 2026-05-08 schlug der Action Code `begehung_reformat` fehl, weil Groq das Model `llama-3.1-8b-instant` ohne Vorwarnung deprecated hat (HTTP 404). Es gab keinen Fallback — der gesamte Analyse-Workflow in `risk-hub/begehung_pilot` war blockiert bis zur manuellen Umstellung auf `gpt-4o-mini`.

### Identifizierte Probleme

| # | Problem | Auswirkung | Häufigkeit |
|---|---------|------------|------------|
| P1 | Model-Deprecation ohne Vorwarnung | Service-Ausfall bis manueller Fix | ~2×/Quartal |
| P2 | Keine Fallback-Chain bei Provider-Ausfall | Kompletter Action-Code-Ausfall | ~1×/Monat |
| P3 | Kein systematisches Provider-Scouting | Verpasste Kostenoptimierung, veraltete Models | dauerhaft |
| P4 | Keine Kosten-Transparenz pro Action Code | Budget-Überraschungen | dauerhaft |
| P5 | Keine Quality-Benchmarks | Suboptimale Model-Zuordnung | dauerhaft |

### Abgrenzung zu ADR-178 (LLM Gateway Consolidation)

ADR-178 regelt die **Code-Architektur**: welcher Service (`llm_gateway/`) die LLM-Calls technisch ausführt (HTTP-Routing, Logging, Retry).

ADR-189 regelt die **Model-Selektion**: welches konkretes Model (`gpt-4o-mini`, `llama-3.3-70b`, etc.) für einen gegebenen Action Code verwendet wird, und wie diese Zuordnung automatisch aktuell gehalten wird.

**Beziehung:** ADR-189 baut auf der durch ADR-178 konsolidierten Gateway-Architektur auf. Die Fallback-Chain (Phase 1) wird in `aifw.service.completion()` implementiert — also im Client-Package, nicht im Gateway selbst.

## Entscheidungstreiber

- Produktionsstabilität (kein Ausfall bei Model-Deprecation)
- Kosteneffizienz (günstigstes geeignetes Model pro Task)
- Minimaler manueller Pflegeaufwand
- Compliance-Sicherheit (DSGVO, EU AI Act)
- Inkrementelle Umsetzbarkeit (Phase 1 sofort, Rest bei Bedarf)

## Betrachtete Optionen

### Option A: Fallback-Chain + Monitoring + Provider-Research (gewählt)

4-Phasen-Ansatz mit sofortiger Fallback-Chain, Monitoring als Basis, und langfristiger Research-Automatisierung.

- **Pro:** Inkrementell, Phase 1 löst akutes Problem sofort
- **Pro:** Jede Phase ist unabhängig nutzbar
- **Pro:** Automatisiert langfristig einen manuellen Prozess
- **Con:** 12 Monate Gesamt-Research-Aufwand für Phase 3+4
- **Con:** Benchmark-Suite erfordert laufende Pflege

### Option B: OpenRouter als einziger Gateway

Alle Calls über OpenRouter routen — aggregiert 200+ Models unter einem API-Key.

- **Pro:** Ein API-Key, eine Rechnung, automatischer Fallback
- **Pro:** Kein eigenes Monitoring nötig
- **Con:** Vendor Lock-in (Single Point of Failure)
- **Con:** Keine eigenen Quality-Benchmarks möglich
- **Con:** OpenRouter-Markup (~10-20% Aufschlag)
- **Con:** Keine Provider-Research (was OpenRouter nicht hat, existiert nicht)

### Option C: Status Quo + manuelle Pflege

Weiter manuell Models zuweisen, bei Ausfall manuell umschalten.

- **Pro:** Kein Entwicklungsaufwand
- **Con:** Wiederholte Ausfälle (P1, P2)
- **Con:** Verpasste Optimierungen (P3–P5)
- **Con:** Skaliert nicht bei steigender Action-Code-Anzahl (aktuell 14, Tendenz steigend)

### Option D: LiteLLM Proxy (self-hosted)

Self-hosted LiteLLM Proxy mit Load-Balancing und Caching.

- **Pro:** Caching reduziert Kosten
- **Pro:** Built-in Fallback bei Provider-Ausfall
- **Con:** Zusätzlicher Container/Service zu betreiben
- **Con:** Kein Auto-Discovery neuer Models
- **Con:** Kein Benchmarking
- **Con:** Dupliziert Funktionalität die `aifw` bereits hat

## Entscheidung

**Gewählt: Option A — Fallback-Chain + Monitoring + Provider-Research**

Wir erweitern das bestehende `aifw`-Package um automatische Resilienz (Phase 1), Verfügbarkeits-Monitoring (Phase 2), und langfristig um systematische Provider-Research mit Quality-Benchmarking (Phase 3+4).

### Phase 1: Fallback-Chain (Q2 2026, 1 Woche) — CRITICAL

**Ownership:** `aifw`-Package (PyPI), deployed in allen Django-Containern.

**Datenbank-Änderung:**

```python
# aifw/models.py — neues M2M-Feld
class AIActionType(models.Model):
    # ... bestehende Felder ...
    fallback_models = models.ManyToManyField(
        "LLMModel",
        related_name="fallback_for_actions",
        blank=True,
        through="ActionFallbackModel",
        help_text="Geordnete Liste alternativer Models bei Ausfall des Default-Models",
    )


class ActionFallbackModel(models.Model):
    """Through-Table für geordnete Fallback-Chain."""

    class Meta:
        ordering = ["priority"]
        unique_together = [("action", "model")]

    action = models.ForeignKey(AIActionType, on_delete=models.CASCADE)
    model = models.ForeignKey("LLMModel", on_delete=models.CASCADE)
    priority = models.PositiveSmallIntegerField(
        default=0,
        help_text="Niedrigere Zahl = höhere Priorität (0 = erster Fallback)",
    )
```

**Service-Logik:**

```python
# aifw/service.py — completion() erweitern
async def completion(action_code: str, messages: list, **kwargs):
    action = AIActionType.objects.get(code=action_code)
    fallbacks = list(
        action.fallback_models.order_by("actionfallbackmodel__priority")
    )
    models_to_try = [action.default_model] + fallbacks

    last_error = None
    for model in models_to_try:
        try:
            return await _call_model(model, messages, **kwargs)
        except (NotFoundError, ServiceUnavailableError, RateLimitError) as e:
            logger.warning(
                "Action '%s': Model '%s' failed (%s), trying next fallback",
                action_code, model.name, type(e).__name__,
            )
            last_error = e

    raise AllModelsFailedError(
        action_code=action_code,
        tried_models=[m.name for m in models_to_try],
        last_error=last_error,
    )
```

**Exception-Handling:** `AllModelsFailedError` wird in `aifw.exceptions` definiert (neues Modul) und erbt von `aifw.AIFWError`.

**Migration:** Expand-Contract-Pattern (ADR-009):
1. Migration 1: Neue Tabelle `ActionFallbackModel` erstellen (additive)
2. Migration 2: Bestehende Action Codes erhalten Default-Fallback `gpt-4o-mini` (Data Migration)
3. Keine Breaking Changes an bestehender API

**Deliverables:**
- M2M `fallback_models` mit Through-Table `ActionFallbackModel`
- Retry-Logic in `aifw.service.completion()` mit strukturiertem Logging
- Admin-UI: Inline-Formular für Fallback-Chain pro Action Code
- Fehler-Eskalation: `AllModelsFailedError` → Discord-Alert

### Phase 2: Availability Monitoring (Q3 2026, 2 Wochen)

**Ownership:** `aifw`-Package, Celery-Worker im jeweiligen App-Container (z.B. `risk_hub_local_worker`).

**Neue Model-Felder:**

```python
# aifw/models.py
class LLMModel(models.Model):
    # ... bestehende Felder ...
    is_online = models.BooleanField(default=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_latency_ms = models.PositiveIntegerField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")
    consecutive_failures = models.PositiveSmallIntegerField(default=0)
```

**Celery-Task:**

```python
@shared_task(name="aifw.check_model_availability")
def check_model_availability():
    """Alle konfigurierten Models auf Erreichbarkeit prüfen.

    Frequenz: alle 6h via Celery Beat.
    Kosten: ~5 Tokens pro Ping × Anzahl Models × 4/Tag.
    Bei 10 Models: 200 Pings/Tag ≈ $0.001/Tag (gpt-4o-mini: $0.15/1M input).
    """
    for model in LLMModel.objects.filter(is_active=True):
        try:
            start = time.monotonic()
            litellm.completion(
                model=model.litellm_id,
                messages=[{"role": "user", "content": "1+1="}],
                max_tokens=3,
                timeout=10,
            )
            model.is_online = True
            model.last_latency_ms = int((time.monotonic() - start) * 1000)
            model.consecutive_failures = 0
            model.last_error = ""
        except Exception as e:
            model.is_online = False
            model.consecutive_failures += 1
            model.last_error = f"{type(e).__name__}: {str(e)[:200]}"
            if model.consecutive_failures >= 3:
                _send_discord_alert(model)
        model.last_checked_at = timezone.now()
        model.save(update_fields=[
            "is_online", "last_checked_at", "last_latency_ms",
            "last_error", "consecutive_failures",
        ])
```

**Routing-Integration:**
- `completion()` bevorzugt Models mit `is_online=True`
- Offline-Models werden nur als letzter Fallback versucht
- Admin-Dashboard: Ampel-Ansicht aller Models (grün/gelb/rot)

**Kosten-Kalkulation:**
- 10 Models × 4 Checks/Tag × 5 Tokens = 200 Tokens/Tag
- Bei gpt-4o-mini ($0.15/1M): **$0.00003/Tag** ≈ $0.01/Jahr
- Bei Groq/Cerebras (free tier): $0.00/Tag

### Phase 3: Provider-Katalog & Research (Q3–Q4 2026, fortlaufend)

**Ownership:** Neues Django-Model in `aifw`-Package (Default). Bei Wachstum über 50 Provider/Models: Auslagerung in separates Package evaluieren (siehe Q3 in Offene Fragen).

**Datenerhebung — ausschließlich über offizielle Kanäle:**

| Quelle | Methode | Rechtliche Basis |
|--------|---------|------------------|
| LiteLLM Model Registry | `litellm.model_list` API | Open Source (MIT) |
| Provider-APIs `/models` | Offizieller Endpunkt (OpenAI, Groq, Mistral) | API-Nutzungsbedingungen erlauben |
| Provider Changelogs | RSS/Atom Feeds | Öffentlich |
| HuggingFace Hub API | `huggingface_hub` Python-Package | Offizielles SDK |

**Kein Web-Scraping.** Provider-Pricing wird manuell oder über offizielle Pricing-APIs erfasst.

**Key-Management:** Provider-API-Keys werden analog bestehender Keys via `decouple.config()` in der jeweiligen `.env`-Datei hinterlegt (z.B. `GROQ_API_KEY`, `MISTRAL_API_KEY`). LiteLLM erkennt diese automatisch über Umgebungsvariablen — keine zentrale Vault-Lösung erforderlich.

**Datenbank-Design:**

Provider-Katalog und Model-Kandidaten sind **plattformweite Ressourcen** (nicht tenant-spezifisch). Alle Repos/Tenants teilen denselben Provider-Katalog — daher kein `tenant_id` erforderlich.

```python
class LLMProvider(models.Model):
    """Bekannter LLM-Provider mit Capabilities."""

    class Meta:
        ordering = ["name"]

    name = models.CharField(max_length=100, unique=True)
    api_base_url = models.URLField(blank=True)
    auth_docs_url = models.URLField(blank=True)
    supports_vision = models.BooleanField(default=False)
    supports_function_calling = models.BooleanField(default=False)
    supports_json_mode = models.BooleanField(default=False)
    gdpr_compliant = models.BooleanField(
        default=False,
        help_text="Provider hat DPA unterzeichnet oder EU-Server-Option",
    )
    data_retention_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Tage der Datenspeicherung (null=unbekannt, 0=keine)",
    )
    free_tier_available = models.BooleanField(default=False)
    free_tier_rpm = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Requests/Minute im Free Tier",
    )
    notes = models.TextField(blank=True, default="")
    last_researched_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class LLMModelCandidate(models.Model):
    """Entdecktes aber noch nicht integriertes Model."""

    class Status(models.TextChoices):
        DISCOVERED = "discovered", "Entdeckt"
        EVALUATING = "evaluating", "In Evaluation"
        APPROVED = "approved", "Freigegeben"
        REJECTED = "rejected", "Abgelehnt"
        DEPRECATED = "deprecated", "Deprecated"

    class Meta:
        ordering = ["-discovered_at"]
        unique_together = [("provider", "litellm_id")]

    provider = models.ForeignKey(
        LLMProvider, on_delete=models.PROTECT, related_name="candidates"
    )
    name = models.CharField(max_length=200)
    litellm_id = models.CharField(
        max_length=200,
        help_text="LiteLLM-kompatible Model-ID (z.B. 'groq/llama-3.3-70b')",
    )
    context_window = models.PositiveIntegerField(default=4096)
    input_cost_per_1m = models.DecimalField(
        max_digits=10, decimal_places=6, null=True, blank=True,
        help_text="Kosten pro 1M Input-Tokens in USD",
    )
    output_cost_per_1m = models.DecimalField(
        max_digits=10, decimal_places=6, null=True, blank=True,
        help_text="Kosten pro 1M Output-Tokens in USD",
    )
    supports_vision = models.BooleanField(default=False)
    supports_function_calling = models.BooleanField(default=False)
    supports_json_mode = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DISCOVERED
    )
    rejection_reason = models.TextField(blank=True, default="")
    discovered_at = models.DateTimeField(auto_now_add=True)
    evaluated_at = models.DateTimeField(null=True, blank=True)
```

**Kandidaten-Pipeline:**

```
Discovered → Evaluating → Approved → Integration in LLMModel
                        ↘ Rejected (mit Begründung)
```

**Frequenz:** Monatlicher Research-Zyklus (Cascade-Agent-Task oder manuell).

### Phase 4: Quality Benchmarking & Score-basiertes Routing (Q4 2026 – Q1 2027)

**Voraussetzung:** Phase 2 (is_online) und Phase 3 (Provider-Katalog) müssen stabil laufen.

**Benchmark-Kategorien (domänenspezifisch):**

| Kategorie | Referenz-Task | Primär-Metrik | Sekundär |
|-----------|---------------|---------------|----------|
| Vision/OCR | 10 annotierte Ex-Schutz-Fotos | JSON-Field-F1 | Latenz |
| Fachtext DE | 5 Befund-Reformulierungen | Human-Rating (1–5) | Kosten |
| Classification | 20 Gefahrstoff-Kategorisierungen | Accuracy | Latenz |
| Extraction | 10 Typenschild-Felder | Field-Exact-Match | — |

**Scoring-Formel:**

```
Score = (Quality / Quality_max)² × (Cost_min / Cost) × (Latency_min / Latency)^0.5
```

**Begründung der Gewichtung:**
- **Quality²** — Qualität ist überproportional wichtig. Ein Model mit 90% Qualität ist nicht "10% besser" als 80%, sondern deutlich wertvoller für Produktionseinsatz.
- **1/Cost linear** — Kosten sind relevant aber nicht dominant. Ein 2× teureres Model mit besserer Qualität ist akzeptabel.
- **1/Latency^0.5** — Latenz ist Nice-to-have. 2× langsamer ist akzeptabel wenn Qualität stimmt. Wurzel dämpft den Einfluss.

**Schwellenwert für Auto-Routing:**
- Nur Models mit `Quality ≥ 0.8` kommen für Auto-Routing in Frage
- Bei Score-Gleichstand (Δ < 5%): Default-Model bleibt aktiv (Stabilität)
- Auto-Routing ist opt-in per Action Code (`auto_route = models.BooleanField(default=False)`)
- Jede Auto-Route-Änderung generiert Discord-Notification + Audit-Log

## Confirmation

Die erfolgreiche Umsetzung wird wie folgt verifiziert:

| Phase | Erfolgskriterium | Verifikation |
|-------|------------------|--------------|
| 1 | Bei Provider-Ausfall wechselt System automatisch auf Fallback | Provozierter Test: Default-Model temporär auf ungültigen Wert setzen |
| 2 | Offline-Models werden innerhalb von 6h erkannt | Model manuell deaktivieren, Alert-Eingang in Discord prüfen |
| 3 | Mindestens 5 neue Provider in DB erfasst | Admin-Zähler |
| 4 | Auto-Routing wählt nachweisbar günstigeres Model bei gleicher Qualität | A/B-Vergleich mit festem vs. auto-geroutetem Model |

## Konsequenzen

### Positiv

- Automatische Resilienz bei Provider-Ausfällen (Phase 1 löst P1+P2 sofort)
- Systematische Kostenoptimierung durch Benchmark-Vergleich
- Compliance-Transparenz (DSGVO-Status pro Provider dokumentiert)
- Frühzeitige Entdeckung besserer/günstigerer Alternativen
- Audit-Trail aller Model-Routing-Entscheidungen

### Negativ

- Phase 3+4: ~12 Monate Research-Aufwand (verteilt)
- Benchmark-Suite erfordert domänenspezifische Referenzdaten (einmalig ~2 Tage)
- 3 neue DB-Tabellen in `aifw` (Migration-Aufwand)
- Risiko: Over-Engineering wenn Action-Code-Anzahl bei <20 bleibt

### Neutral

- Kein neuer Service/Container — alles lebt im bestehenden `aifw`-Package
- Celery-Task nutzt bestehende Worker-Infrastruktur
- Admin-UI nutzt bestehende Django-Admin-Oberfläche

## Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Provider-API ändert sich | Mittel | Niedrig | LiteLLM abstrahiert Provider-Unterschiede |
| Benchmarks sind irreführend | Mittel | Mittel | Human-in-the-loop: Auto-Routing nur opt-in, Discord-Alert bei Wechsel |
| Free Tiers werden abgeschafft | Hoch | Niedrig | Fallback-Chain enthält immer ein bezahltes Model |
| Kosten-Explosion durch Ping-Tasks | Niedrig | Niedrig | 200 Tokens/Tag = $0.01/Jahr (berechnet, siehe Phase 2) |
| DSGVO-Verstoß durch Test an unbekanntem Provider | Mittel | Hoch | Nur synthetische Testdaten ("1+1="), nie Produktionsdaten in Benchmarks |

## Offene Fragen

| # | Frage | Entscheidung bis | Verantwortlich |
|---|-------|-----------------|----------------|
| Q1 | Ab welcher Action-Code-Anzahl lohnt sich Phase 4 wirtschaftlich? | Vor Phase 4 Start | Achim |
| Q2 | Soll Auto-Routing auch für sicherheitskritische Action Codes (z.B. `hazard_analysis`) erlaubt sein? | Phase 4 Design | Achim |
| Q3 | Default: Provider-Katalog lebt in `aifw`. Auslagerung in separates Package evaluieren wenn Katalog >50 Einträge. | Phase 3 Review | Achim |
| Q4 | Wie gehen wir mit Models um die nur in bestimmten Regionen verfügbar sind (z.B. Azure EU)? | Phase 3 | Achim |
| Q5 | Soll das Benchmark-Set öffentlich dokumentiert werden (Transparenz) oder intern bleiben (Wettbewerbsvorteil)? | Phase 4 | Achim |

## Timeline

| Phase | Zeitraum | Aufwand | Priorität | Gate |
|-------|----------|---------|-----------|------|
| 1: Fallback-Chain | Q2 2026 | 1 Woche | CRITICAL | Sofort umsetzbar |
| 2: Monitoring | Q3 2026 | 2 Wochen | HIGH | Nach Phase 1 deployed |
| 3: Provider-Katalog | Q3–Q4 2026 | fortlaufend (~2h/Monat) | MEDIUM | Nach Phase 2 stabil |
| 4: Auto-Routing | Q4 2026 – Q1 2027 | 4 Wochen | LOW | Nur wenn ≥30 Action Codes |

## Verwandte ADRs

- **ADR-178** (LLM Gateway Consolidation) — Gateway-Code-Architektur. ADR-189 baut darauf auf (Model-Selektion-Layer oberhalb des Gateways).
- **ADR-115** (LLM Usage Logging) — Logging-Daten sind Input für Cost-Reports in Phase 4.
- **ADR-023** (Shared Scoring & Routing Engine) — Allgemeines Scoring-Pattern. Phase 4 implementiert eine Spezialisierung für LLM-Models.
- **ADR-028** (Platform Context) — Deployment-Kontext. Monitoring-Task läuft im bestehenden Celery-Worker.

## Glossar

| Begriff | Erklärung |
|---------|-----------|
| **Action Code** | Eindeutiger Bezeichner für einen LLM-Anwendungsfall (z.B. `begehung_photo_analysis`). Wird in der DB-Tabelle `AIActionType` konfiguriert. |
| **aifw** | IIL-eigenes Python-Package für LLM-Aufrufe. Abstrahiert Provider-Unterschiede und steuert Model-Routing über die Datenbank. |
| **Celery Beat** | Scheduler-Komponente von Celery, die periodische Tasks zu festgelegten Zeiten ausführt (ähnlich Cron, aber Python-nativ). |
| **DPA** | Data Processing Agreement — vertragliche DSGVO-Vereinbarung mit Datenverarbeiter. |
| **Expand-Contract** | Migrations-Pattern bei dem zuerst neue Strukturen additiv hinzugefügt werden (Expand), dann alte entfernt werden (Contract). Verhindert Breaking Changes bei laufendem Betrieb. |
| **Fallback-Chain** | Geordnete Liste alternativer Models, die bei Ausfall des Primär-Models automatisch durchprobiert werden. |
| **F1-Score** | Harmonisches Mittel aus Precision und Recall — Standardmetrik für Klassifikations- und Extraktionsaufgaben. |
| **BLEU** | Bilingual Evaluation Understudy — automatische Metrik für Textgenerierungsqualität (Vergleich mit Referenztext). |
| **Human-Rating** | Manuelle Bewertung durch Fachexperten auf Skala 1–5. Gold-Standard für Textqualität. |
| **LiteLLM** | Open-Source Python-Library die 100+ LLM-Provider unter einer einheitlichen API zusammenfasst. Bereits Dependency von `aifw`. |
| **p95 Latenz** | 95. Perzentil der Antwortzeit — 95% aller Anfragen sind schneller als dieser Wert. Robuster als Durchschnitt. |
| **Provider** | Anbieter von LLM-APIs (z.B. OpenAI, Groq, Anthropic, Mistral, Cerebras). |
| **ROUGE-L** | Recall-Oriented Understudy for Gisting Evaluation — Metrik für Zusammenfassungsqualität (längste gemeinsame Subsequenz). |
| **Token** | Kleinste Texteinheit für LLMs (~4 Zeichen Deutsch). Abrechnungseinheit bei Provider-APIs. |
