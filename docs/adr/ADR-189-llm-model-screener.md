# ADR-189: LLM Model Screener & Provider Research System

## Status

Proposed

## Datum

2026-05-08

## Kontext

Die IIL-Plattform nutzt über `aifw` eine DB-gesteuerte Model-Routing-Architektur (`AIActionType` → `LLMModel`). Aktuell wird die Zuordnung manuell gepflegt. Probleme:

1. **Model-Deprecation ohne Vorwarnung** — Groq hat `llama-3.1-8b-instant` entfernt, unsere Calls liefen ins Leere (404)
2. **Keine Fallback-Chain** — bei Provider-Ausfall schlägt der gesamte Action Code fehl
3. **Kein systematisches Scouting** — neue Provider (Cerebras, Together, Fireworks, DeepInfra, Mistral) und Models werden nur ad-hoc entdeckt
4. **Kosten-Intransparenz** — kein Tracking welcher Action Code wie viel kostet
5. **Keine Quality-Benchmarks** — ob ein neues Model für eine Kategorie besser geeignet wäre, wird nicht systematisch geprüft

## Entscheidung

Wir entwickeln ein **LLM Model Screener & Provider Research System** als langfristiges Research-Projekt (~12 Monate), das in 4 Phasen aufgebaut wird.

### Phase 1: Fallback-Chain & Availability (Q2 2026, 1 Woche)

**Sofort-Maßnahme in `aifw`:**

```python
# aifw/models.py — neues Feld
class AIActionType(models.Model):
    fallback_models = models.JSONField(
        default=list,
        help_text="Ordered list of model IDs to try if default fails"
    )

# aifw/service.py — completion() erweitern
async def completion(...):
    models_to_try = [action.default_model] + action.fallback_models
    for model in models_to_try:
        try:
            return await _call_model(model, messages, **kwargs)
        except (NotFoundError, ServiceUnavailableError) as e:
            logger.warning("Model %s failed, trying next: %s", model, e)
    raise AllModelsFailedError(action_code, models_to_try)
```

**Deliverables:**
- `AIActionType.fallback_models` JSONField
- Retry-Logic in `aifw.service.completion()`
- Admin-UI: Fallback-Chain pro Action Code konfigurierbar

### Phase 2: Availability Monitoring (Q3 2026, 2 Wochen)

**Celery-Task `check_model_availability`:**

```python
@shared_task(name="aifw.check_model_availability")
def check_model_availability():
    """Ping all configured models every 6h."""
    for model in LLMModel.objects.filter(is_active=True):
        try:
            result = litellm.completion(
                model=model.litellm_id,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            model.is_online = True
            model.last_latency_ms = result._response_ms
        except Exception as e:
            model.is_online = False
            model.last_error = str(e)
        model.last_checked_at = timezone.now()
        model.save()
```

**Deliverables:**
- `LLMModel.is_online`, `last_checked_at`, `last_latency_ms` Felder
- Celery Beat: alle 6h
- Admin-Dashboard: Model-Status auf einen Blick
- Alert (Discord) bei Model-Ausfall

### Phase 3: Provider Research & Discovery (Q3–Q4 2026, fortlaufend)

**Systematische Recherche neuer Provider:**

| Dimension | Methode | Frequenz |
|-----------|---------|----------|
| Neue Provider | API-Katalog-Scraping (OpenRouter, LiteLLM Registry) | monatlich |
| Preisänderungen | Provider Pricing Pages monitoren | wöchentlich |
| Neue Models | Provider Release Notes / RSS | wöchentlich |
| Open-Source Models | HuggingFace Trending, Papers with Code | monatlich |
| Regulatorik | EU AI Act Compliance-Check | quartalsweise |

**Provider-Datenbank (neues Django-Model):**

```python
class LLMProvider(models.Model):
    name = models.CharField(max_length=100, unique=True)
    api_base_url = models.URLField()
    pricing_url = models.URLField(blank=True)
    supports_vision = models.BooleanField(default=False)
    supports_function_calling = models.BooleanField(default=False)
    supports_streaming = models.BooleanField(default=False)
    max_context_window = models.IntegerField(default=4096)
    gdpr_compliant = models.BooleanField(default=False)
    data_retention_days = models.IntegerField(null=True)
    free_tier_available = models.BooleanField(default=False)
    free_tier_rpm = models.IntegerField(null=True, help_text="Requests/min on free tier")
    notes = models.TextField(blank=True)
    last_researched_at = models.DateTimeField(null=True)

class LLMModelCandidate(models.Model):
    """Discovered but not yet integrated models."""
    provider = models.ForeignKey(LLMProvider, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    litellm_id = models.CharField(max_length=200)
    input_cost_per_1m = models.DecimalField(max_digits=8, decimal_places=4, null=True)
    output_cost_per_1m = models.DecimalField(max_digits=8, decimal_places=4, null=True)
    context_window = models.IntegerField()
    capabilities = models.JSONField(default=list)  # ["vision", "json_mode", "function_calling"]
    benchmark_score = models.FloatField(null=True)
    status = models.CharField(choices=[
        ("discovered", "Discovered"),
        ("testing", "Testing"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("deprecated", "Deprecated"),
    ], default="discovered")
    discovered_at = models.DateTimeField(auto_now_add=True)
```

**Deliverables:**
- Provider-Datenbank mit aktuellen Capabilities
- Monthly Research Report (automatisch generiert)
- Kandidaten-Pipeline: Discovered → Testing → Approved → Integrated

### Phase 4: Quality Benchmarking & Auto-Routing (Q4 2026 – Q1 2027)

**Benchmark-Suite pro Kategorie:**

| Kategorie | Referenz-Task | Metrik |
|-----------|---------------|--------|
| Vision/OCR | 10 Ex-Schutz-Fotos analysieren | JSON-Accuracy, F1 |
| Text Generation | Befund-Formulierung aus JSON | BLEU, Human-Rating |
| Classification | Gefahrstoff-Kategorisierung | Accuracy |
| Extraction | Typenschild-Daten extrahieren | Field-F1 |
| Summarization | Begehungsprotokoll-Summary | ROUGE-L |
| Translation | DE↔EN Fachbegriffe | Accuracy |

**Scoring-Formel:**

```
Score = Quality^2 × (1 / Cost) × (1 / Latency^0.5)
```

- Quality: 0–1 (aus Benchmark)
- Cost: $/1M tokens
- Latency: p95 in ms

**Auto-Routing-Logic:**

```python
def get_optimal_model(action_code: str) -> LLMModel:
    """Return highest-scoring available model for this action."""
    action = AIActionType.objects.get(code=action_code)
    candidates = ModelBenchmark.objects.filter(
        category=action.category,
        model__is_online=True,
        model__is_active=True,
    ).order_by("-score")
    return candidates.first().model if candidates.exists() else action.default_model
```

**Deliverables:**
- Benchmark-Runner (Celery Task, wöchentlich)
- Score-basiertes Auto-Routing (opt-in per Action Code)
- Admin-Dashboard: Model-Vergleich pro Kategorie
- Cost-Report: monatliche Ausgaben pro Action Code

## Konsequenzen

### Positiv
- Kein manuelles Model-Tracking mehr
- Automatische Resilienz bei Provider-Ausfällen
- Systematische Kostenoptimierung
- Frühzeitige Entdeckung besserer/günstigerer Alternativen
- Compliance-Transparenz (GDPR, EU AI Act)

### Negativ
- 12 Monate Research-Aufwand
- Benchmark-Maintenance (Referenz-Tasks aktuell halten)
- Zusätzliche DB-Tabellen und Celery-Tasks
- Risiko: Over-Engineering wenn Plattform klein bleibt

### Risiken
- Provider-APIs ändern sich → Adapter-Maintenance
- Benchmarks können irreführend sein → Human-in-the-loop bei Routing-Entscheidungen
- Free Tiers werden abgeschafft → Fallback auf bezahlte Models

## Alternativen betrachtet

1. **OpenRouter als einziger Gateway** — Pro: Ein API-Key für alles. Contra: Vendor Lock-in, kein Quality-Benchmark, keine Provider-Research
2. **Manuell weiter pflegen** — Pro: Kein Entwicklungsaufwand. Contra: 404-Fehler, verpasste Optimierungen
3. **LiteLLM Proxy (self-hosted)** — Pro: Caching, Load-Balancing. Contra: Kein Auto-Discovery, kein Benchmarking

## Verwandte ADRs

- ADR-178: LLM Gateway Consolidation
- ADR-023: Shared Scoring & Routing Engine
- ADR-028: Platform Context

## Timeline

| Phase | Zeitraum | Aufwand | Priorität |
|-------|----------|---------|-----------|
| 1: Fallback-Chain | Q2 2026 | 1 Woche | CRITICAL |
| 2: Monitoring | Q3 2026 | 2 Wochen | HIGH |
| 3: Research | Q3–Q4 2026 | fortlaufend | MEDIUM |
| 4: Auto-Routing | Q4 2026 – Q1 2027 | 4 Wochen | LOW |
