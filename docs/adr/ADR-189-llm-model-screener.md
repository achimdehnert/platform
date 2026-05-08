---
status: Proposed
date: 2026-05-08
amended: 2026-05-08
decision-makers:
  - Achim Dehnert
reviewed-by: Cascade Senior Architecture Reviewer
depends-on:
  - ADR-178 (LLM Gateway Consolidation)
  - ADR-115 (LLM Usage Logging)
  - ADR-009 (Service Layer Pattern)
  - ADR-022 (BigAutoField Platform Standard)
  - ADR-072 (Multi-Tenancy Schema Isolation)
related:
  - ADR-023 (Shared Scoring & Routing Engine)
  - ADR-028 (Platform Context)
  - ADR-045 (SOPS Secrets Management)
  - ADR-059 (Drift-Detector)
repo: platform
implementation_status: none
staleness_months: 6
drift_check_paths:
  - packages/aifw/aifw/models.py
  - packages/aifw/aifw/service.py
  - packages/aifw/aifw/exceptions.py
supersedes_check: []
---

# ADR-189: Einführung eines automatisierten LLM Model Screener & Provider Research Systems

| Metadaten | |
|-----------|---|
| **Status** | Proposed |
| **Datum** | 2026-05-08 |
| **Amended** | 2026-05-08 (v3 — External Review Fixes) |
| **Autor** | Achim Dehnert |
| **Reviewer** | Cascade Senior Architecture Reviewer |
| **Depends On** | ADR-178, ADR-115, ADR-009, ADR-022, ADR-072 |
| **Consumers** | risk-hub, bfagent, weltenhub, alle Repos die `aifw` nutzen |

### Änderungshistorie

| Version | Datum | Änderung |
|---------|-------|----------|
| 1.0 | 2026-05-08 | Initiale Version |
| 2.0 | 2026-05-08 | Strukturelle Überarbeitung: MADR-Frontmatter, Glossar, Open Questions, M2M statt JSONField, ADR-178-Abgrenzung |
| 2.1 | 2026-05-08 | Minor-Fixes: Key-Management, tenant-Scope, Q3-Auflösung, Expand-Contract im Glossar |
| 3.0 | 2026-05-08 | External Review Fixes: DB-Sync-Strategie, Multi-Tenancy-Schema, Drift-Detector-Felder, Open-Questions mit Pro/Con, RateLimitError-Backoff, LLM-as-Judge, PyPI-Rollout, ADR-115-Cross-DB |

---

## Status

Proposed

## Context and Problem Statement

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

ADR-189 regelt die **Model-Selektion**: welches konkretes Model für einen Action Code verwendet wird, und wie diese Zuordnung automatisch aktuell gehalten wird.

ADR-189 baut auf der durch ADR-178 konsolidierten Gateway-Architektur auf. Die Fallback-Chain (Phase 1) wird in `aifw.service.completion()` implementiert — also im Client-Package, nicht im Gateway selbst.

## Decision Drivers

- Produktionsstabilität (kein Ausfall bei Model-Deprecation)
- Kosteneffizienz (günstigstes geeignetes Model pro Task)
- Minimaler manueller Pflegeaufwand
- Compliance-Sicherheit (DSGVO, EU AI Act)
- Inkrementelle Umsetzbarkeit (Phase 1 sofort, Rest bei Bedarf)
- Konsistenz über 19+ Repos die `aifw` nutzen

## Considered Options

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

## Decision Outcome

**Gewählt: Option A — Fallback-Chain + Monitoring + Provider-Research**

Wir erweitern das bestehende `aifw`-Package um automatische Resilienz (Phase 1), Verfügbarkeits-Monitoring (Phase 2), und langfristig um systematische Provider-Research mit Quality-Benchmarking (Phase 3+4).

**Begründung:** Option A ist die einzige die sowohl das akute Problem (P1, P2) sofort löst als auch eine Roadmap für die strukturellen Probleme (P3-P5) bietet, ohne Vendor Lock-in (B) oder zusätzliche Infrastruktur (D) einzuführen.

### Datenbank-Architektur (Schema-Verortung & Multi-Repo-Sync)

Diese Entscheidung adressiert direkt die Multi-Tenancy- und Multi-Repo-Frage (ADR-072 Konflikt).

**Schema-Verortung (Single Source of Truth):**

Alle `aifw`-Tabellen (inkl. `LLMProvider`, `LLMModelCandidate`, `LLMModel`, `AIActionType`, `ActionFallbackModel`) leben **ausschließlich im `public` Schema** — auch in Repos mit Tenant-Schema-Isolation (risk-hub, weltenhub, bfagent).

```python
# packages/aifw/aifw/models.py
class LLMProvider(models.Model):
    class Meta:
        db_table = "aifw_llm_provider"  # NICHT in tenant schemas
        # Django folgt automatisch DEFAULT_TABLESPACE = public
```

**Begründung:** LLM-Provider und Model-Kandidaten sind plattformweite Ressourcen. Eine N-fache Replikation pro Tenant wäre absurd (gleiche Provider-Liste in jedem Schema).

**Multi-Repo-Synchronisation (Provider-Katalog konsistent über 19+ Repos):**

Da jedes Repo eine eigene Postgres-DB hat, würde naive Verwendung zu 19 separaten Provider-Listen führen. Lösung:

1. **Single Source of Truth:** `platform/fixtures/aifw/llm_providers.yaml` (im platform-Repo, versioniert)
2. **Sync-Mechanismus:** `aifw`-Management-Command `python manage.py sync_aifw_providers` lädt Fixture aus platform-Repo (via HTTP raw URL oder gepinnter Commit)
3. **Trigger:** Wöchentlicher Celery Beat Task pro Repo, oder manuell nach Provider-Update
4. **Konfliktauflösung:** Fixture-Inhalt überschreibt lokale Daten (`LLMProvider.objects.update_or_create(name=...)`), lokale `LLMModel`-Zuordnungen (Action Code → Model) bleiben repo-spezifisch

```python
# aifw/management/commands/sync_aifw_providers.py
class Command(BaseCommand):
    """Synchronisiert Provider-Katalog aus platform-Repo."""

    PLATFORM_FIXTURE_URL = (
        "https://raw.githubusercontent.com/achimdehnert/platform/"
        "main/fixtures/aifw/llm_providers.yaml"
    )

    def handle(self, *args, **options):
        data = yaml.safe_load(httpx.get(self.PLATFORM_FIXTURE_URL).text)
        for entry in data["providers"]:
            LLMProvider.objects.update_or_create(
                name=entry["name"],
                defaults={k: v for k, v in entry.items() if k != "name"},
            )
```

**Cost-Tracking (Cross-DB-Strategie für ADR-115):**

ADR-115 loggt alle LLM-Calls in `mcp_hub_db.llm_calls` (zentrale DB). Phase 4 Cost-Reports nutzen diese zentrale Tabelle — keine Cross-DB-Queries aus den App-Repos nötig. Reports werden im `mcp-hub` Service generiert (READ-only Zugriff via SQLAlchemy auf bestehende Tabelle).

### PyPI-Rollout-Strategie für `aifw`

Phase 1 erfordert ein neues `aifw`-Release. Rollout über 19+ Repos:

| Schritt | Aktion | Verantwortlich |
|---------|--------|----------------|
| 1 | Phase 1 Code in `aifw` PR mergen | Achim |
| 2 | Version-Bump: `aifw==0.5.x` → `aifw==0.6.0` (Minor, additive) | Maintainer |
| 3 | PyPI Publish via `publish.yml` Workflow | CI |
| 4 | Pilot-Repo (`risk-hub`) auf `aifw>=0.6.0,<1` pinnen + deployen | Achim |
| 5 | Nach 7 Tagen Pilot-Stabilität: Rollout auf alle 19 Repos via Bulk-PR | Bulk-PR-Tool |
| 6 | Migration `python manage.py migrate aifw` läuft automatisch im Container-Start | Deploy-Pipeline |

**Rollback:** Repos können auf `aifw==0.5.x` zurück (kein DB-Schema-Drop nötig — nur ungenutzte additive Tabelle).

### Phase 1: Fallback-Chain (Q2 2026, 2-3 Wochen) — CRITICAL

**Ownership:** `aifw`-Package (PyPI), deployed in allen Django-Containern.

**Aufwandsschätzung:** 2-3 Wochen (nicht 1) — beinhaltet Code, Tests, PyPI-Release, Pilot-Deploy, Bulk-Rollout über 19 Repos.

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
        db_table = "aifw_action_fallback_model"

    action = models.ForeignKey(AIActionType, on_delete=models.CASCADE)
    model = models.ForeignKey("LLMModel", on_delete=models.CASCADE)
    priority = models.PositiveSmallIntegerField(
        default=0,
        help_text="Niedrigere Zahl = höhere Priorität (0 = erster Fallback)",
    )
```

**Service-Logik mit Fehler-Differenzierung:**

```python
# aifw/service.py — completion() erweitern
import asyncio
from .exceptions import AllModelsFailedError

async def completion(action_code: str, messages: list, **kwargs):
    """Ruft LLM mit Fallback-Chain auf.

    Fehler-Strategie:
    - NotFoundError, ServiceUnavailableError → SOFORT zum nächsten Fallback
    - RateLimitError → exponentieller Backoff (kein Fallback! gleiches Model retry)
    - AuthError → SOFORT zum nächsten Fallback (Provider-Key kaputt)
    """
    action = AIActionType.objects.get(code=action_code)
    fallbacks = list(
        action.fallback_models.order_by("actionfallbackmodel__priority")
    )
    models_to_try = [action.default_model] + fallbacks

    last_error = None
    for model in models_to_try:
        # Pro Model bis zu 3 Retries bei Rate-Limit (exp. Backoff)
        for attempt in range(3):
            try:
                return await _call_model(model, messages, **kwargs)
            except RateLimitError as e:
                wait_s = 2 ** attempt  # 1s, 2s, 4s
                logger.info(
                    "Action '%s': Model '%s' rate-limited, waiting %ds",
                    action_code, model.name, wait_s,
                )
                await asyncio.sleep(wait_s)
                last_error = e
                continue
            except (NotFoundError, ServiceUnavailableError, AuthError) as e:
                logger.warning(
                    "Action '%s': Model '%s' failed (%s), trying next fallback",
                    action_code, model.name, type(e).__name__,
                )
                last_error = e
                break  # nächstes Model versuchen
        else:
            continue  # alle 3 Retries durch — nächstes Model

    raise AllModelsFailedError(
        action_code=action_code,
        tried_models=[m.name for m in models_to_try],
        last_error=last_error,
    )
```

**Wichtige Änderung gegenüber v2:** `RateLimitError` löst KEINEN Fallback mehr aus, sondern exponentiellen Backoff am gleichen Model. Rate-Limits sind transient — Fallback zu schlechterem Model wäre kontraproduktiv.

**Exception-Handling:** `AllModelsFailedError` wird in `aifw.exceptions` definiert (neues Modul) und erbt von `aifw.AIFWError`.

**Migration:** Expand-Contract-Pattern (ADR-009):
1. Migration 1: Neue Tabelle `aifw_action_fallback_model` erstellen (additive)
2. Migration 2: Bestehende Action Codes erhalten Default-Fallback `gpt-4o-mini` (Data Migration)
3. Keine Breaking Changes an bestehender API

**Deliverables:**
- M2M `fallback_models` mit Through-Table
- Retry-Logic mit Backoff-Differenzierung
- Admin-UI: Inline-Formular für Fallback-Chain pro Action Code
- Fehler-Eskalation: `AllModelsFailedError` → Discord-Alert (mit 5-Min-Aggregation gegen Spam)

### Phase 2: Availability Monitoring (Q3 2026, 2 Wochen)

**Ownership:** `aifw`-Package, Celery-Worker im jeweiligen App-Container.

**Neue Model-Felder:**

```python
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
            if model.consecutive_failures == 3:  # exakt 3 → einmaliger Alert
                _send_discord_alert(model)
        model.last_checked_at = timezone.now()
        model.save(update_fields=[
            "is_online", "last_checked_at", "last_latency_ms",
            "last_error", "consecutive_failures",
        ])
```

**Discord-Alert Aggregation:** Alert nur bei `consecutive_failures == 3` (exakter Vergleich), nicht `>= 3` — verhindert Spam bei fortlaufenden Ausfällen. Recovery-Alert bei Wiederherstellung.

**Routing-Integration:**
- `completion()` bevorzugt Models mit `is_online=True`
- Offline-Models werden nur als letzter Fallback versucht
- Admin-Dashboard: Ampel-Ansicht aller Models (grün/gelb/rot)

### Phase 3: Provider-Katalog & Research (Q3–Q4 2026, fortlaufend)

**Ownership:** Django-Models in `aifw`-Package. Provider-Katalog im `public` Schema (siehe Datenbank-Architektur oben).

**Datenerhebung — ausschließlich über offizielle Kanäle:**

| Quelle | Methode | Rechtliche Basis |
|--------|---------|------------------|
| LiteLLM Model Registry | `litellm.model_list` API | Open Source (MIT) |
| Provider-APIs `/models` | Offizieller Endpunkt | API-Nutzungsbedingungen |
| Provider Changelogs | RSS/Atom Feeds | Öffentlich |
| HuggingFace Hub API | `huggingface_hub` SDK | Offiziell |

**Kein Web-Scraping.**

**Key-Management (Multi-Repo-Skalierung):**

Provider-API-Keys werden als **org-level GitHub Secrets** hinterlegt (nicht per-Repo) — analog `OPENAI_API_KEY` Pattern. Bei Key-Rotation muss nur 1 Secret aktualisiert werden, nicht 19.

```yaml
# In .github/workflows/_deploy-unified.yml — wird in alle Repos vererbt
env:
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
  MISTRAL_API_KEY: ${{ secrets.MISTRAL_API_KEY }}
  # ... weitere Provider
```

LiteLLM erkennt diese automatisch über Umgebungsvariablen. SOPS (ADR-045) ist nicht erforderlich, da GitHub Secrets bereits verschlüsselt sind.

**Datenbank-Design:** (siehe v2 — keine Änderungen)

### Phase 4: Quality Benchmarking & Score-basiertes Routing (Q4 2026 – Q1 2027)

**Voraussetzung:** Phase 2 + 3 stabil + ≥30 Action Codes (Wirtschaftlichkeits-Gate).

**Skalierbarkeit — LLM-as-Judge:**

Ursprünglich war Human-Rating als Primär-Metrik geplant. Bei 30+ Action Codes × 4-6 Benchmarks/Kategorie ist das nicht skalierbar. **Lösung:**

- Tier 1 (90% der Fälle): **LLM-as-Judge** — ein Premium-Model (z.B. `gpt-4o`) bewertet Output-Qualität. Reproduzierbar, billig, schnell.
- Tier 2 (10% Stichprobe): Human-Rating zur Kalibrierung, monatlich.

```python
# aifw/benchmarks/judge.py
def llm_judge_score(reference: str, candidate: str, criteria: list[str]) -> float:
    """Bewertet Candidate-Output gegen Reference auf Skala 0-1."""
    prompt = f"""Bewerte die Qualität auf Skala 0-1 nach Kriterien: {criteria}.
    Referenz: {reference}
    Kandidat: {candidate}
    Antworte NUR mit einer Zahl 0-1."""
    result = sync_completion(action_code="benchmark_judge", messages=[...])
    return float(result.content.strip())
```

**Benchmark-Versionierung:** Test-Sets in `platform/benchmarks/aifw/v{N}/` versioniert. Score-Vergleiche sind nur innerhalb derselben Version valide. Bei Breaking Change → neue Version, alte Scores werden archiviert.

**Scoring-Formel:**

```
Score = (Quality / Quality_max)² × (Cost_min / Cost) × (Latency_min / Latency)^0.5
```

Begründung der Gewichtung wie v2 (Quality² überproportional, Cost linear, Latency gedämpft).

**Schwellenwert für Auto-Routing:**
- Nur Models mit `Quality ≥ 0.8` kommen für Auto-Routing in Frage
- Bei Score-Gleichstand (Δ < 5%): Default-Model bleibt aktiv (Stabilität)
- Auto-Routing ist opt-in per Action Code (`auto_route = models.BooleanField(default=False)`)
- **Sicherheitskritische Action Codes** (markiert als `is_safety_critical=True`, z.B. `hazard_analysis`) sind von Auto-Routing AUSGESCHLOSSEN — nur manuelle Model-Wahl
- Jede Auto-Route-Änderung generiert Discord-Notification (max. 1×/Stunde aggregiert) + Audit-Log
- Architecture Guardian (ADR-054) wird über Auto-Route-Wechsel via `aifw_route_changed` Signal informiert

### Confirmation

Die erfolgreiche Umsetzung wird wie folgt verifiziert:

| Phase | Erfolgskriterium | Verifikation |
|-------|------------------|--------------|
| 1 | Bei Provider-Ausfall wechselt System automatisch auf Fallback | Provozierter Test: Default-Model temporär auf ungültigen Wert setzen, `pytest tests/test_fallback_chain.py` |
| 1 | RateLimit triggert Backoff statt Fallback | Mock-Test mit `RateLimitError` × 2 → gleicher Call retry'd, kein Fallback |
| 2 | Offline-Models werden innerhalb von 6h erkannt | Model manuell deaktivieren, Alert-Eingang in Discord prüfen |
| 3 | Provider-Katalog identisch über alle Repos | `python manage.py sync_aifw_providers` in 3 Repos, dann SQL-Vergleich |
| 4 | Auto-Routing wählt nachweisbar günstigeres Model bei gleicher Qualität | A/B-Vergleich, Audit-Log auswerten |

## Pros and Cons of the Options

(Pros/Cons je Option in Abschnitt "Considered Options" oben dokumentiert.)

## Consequences

### Good

- Automatische Resilienz bei Provider-Ausfällen (Phase 1 löst P1+P2 sofort)
- Systematische Kostenoptimierung durch Benchmark-Vergleich
- Compliance-Transparenz (DSGVO-Status pro Provider dokumentiert)
- Frühzeitige Entdeckung besserer/günstigerer Alternativen
- Audit-Trail aller Model-Routing-Entscheidungen
- Konsistenter Provider-Katalog über 19+ Repos (Sync-Mechanismus)
- Org-Level-Secrets vereinfachen Key-Rotation (1 Stelle statt 19)

### Bad

- Phase 3+4: ~12 Monate Research-Aufwand (verteilt)
- Benchmark-Suite erfordert domänenspezifische Referenzdaten (einmalig ~2 Tage)
- 3 neue DB-Tabellen in `aifw` (Migration-Aufwand × 19 Repos)
- Risiko: Over-Engineering wenn Action-Code-Anzahl bei <20 bleibt
- LLM-as-Judge führt zirkuläre Abhängigkeit ein (Judge-Model selbst muss vertraut werden)
- Sync-Mechanismus erzeugt Dependency auf platform-Repo Verfügbarkeit

### Neutral

- Kein neuer Service/Container — alles lebt im bestehenden `aifw`-Package
- Celery-Task nutzt bestehende Worker-Infrastruktur
- Admin-UI nutzt bestehende Django-Admin-Oberfläche

## Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Provider-API ändert sich | Mittel | Niedrig | LiteLLM abstrahiert Provider-Unterschiede |
| Benchmarks sind irreführend | Mittel | Mittel | Human-in-the-loop: Auto-Routing nur opt-in, monatliche Human-Rating-Stichprobe |
| Free Tiers werden abgeschafft | Hoch | Niedrig | Fallback-Chain enthält immer ein bezahltes Model |
| Kosten-Explosion durch Ping-Tasks | Niedrig | Niedrig | 200 Tokens/Tag = $0.01/Jahr (berechnet) |
| DSGVO-Verstoß durch Test an unbekanntem Provider | Mittel | Hoch | Nur synthetische Testdaten, nie Produktionsdaten |
| Benchmark-Set-Memorization durch Provider | Niedrig | Mittel | Eigene Domänen-Daten (Ex-Schutz) statt öffentliche Benchmarks |
| Sync-Mechanismus fällt aus → veralteter Katalog | Niedrig | Niedrig | Lokale Daten bleiben funktional, kein harter Sync-Zwang |
| `aifw 0.6.0` Bug crasht 19 Repos | Niedrig | Hoch | Pilot-Deploy in risk-hub für 7 Tage vor Bulk-Rollout |
| LLM-as-Judge selbst hat Bias | Mittel | Mittel | Tier-2-Human-Stichprobe zur Kalibrierung, Judge-Model rotieren |

## Open Questions

Pro Frage werden Optionen mit Pro/Con aufgelistet, damit zukünftige Reviewer die Auswirkung einer Entscheidung einschätzen können.

### Q1: Ab welcher Action-Code-Anzahl lohnt sich Phase 4 wirtschaftlich?

| Option | Pro | Con |
|--------|-----|-----|
| Q1.A: ≥30 Action Codes (gewählt im aktuellen Draft) | Klare Schwelle | Willkürliche Zahl ohne Datenbasis |
| Q1.B: Wenn Phase 2 ≥3 Modell-Wechsel/Quartal zeigt | Datengetrieben | Erst nach 6 Monaten Phase 2 entscheidbar |
| Q1.C: Nie — Phase 4 streichen | Kein Aufwand | P5 (Quality-Gap) bleibt ungelöst |

**Entscheidung bis:** Vor Phase 4 Start. **Verantwortlich:** Achim.

### Q2: Soll Auto-Routing für sicherheitskritische Action Codes erlaubt sein?

| Option | Pro | Con |
|--------|-----|-----|
| Q2.A: Ausschluss via `is_safety_critical=True` (gewählt) | Sicher, einfach | Manuelle Klassifizierung nötig |
| Q2.B: Auto-Routing erlaubt mit Approval-Workflow | Flexibel | Komplex, Verzögerung |
| Q2.C: Nie — nur manuelle Wahl für alle | Maximale Kontrolle | Verliert Phase-4-Wert |

**Entscheidung bis:** Phase 4 Design. **Verantwortlich:** Achim.

### Q3: Provider-Katalog in `aifw` oder separates Package?

| Option | Pro | Con |
|--------|-----|-----|
| Q3.A: In `aifw` (Default, gewählt) | Eine Dependency, ein Release | aifw wird größer |
| Q3.B: Separates `iil-llm-catalog` Package | Klare Trennung | Doppelter Release-Aufwand |
| Q3.C: Cloud-Service mit API | Zentrale Verwaltung | Neuer Service-Aufwand |

**Trigger für Re-Evaluation:** >50 Provider-Einträge. **Entscheidung bis:** Phase 3 Review.

### Q4: Models nur in bestimmten Regionen (z.B. Azure EU)?

| Option | Pro | Con |
|--------|-----|-----|
| Q4.A: Region-Feld in `LLMProvider`, Filter in Routing | Sauber | Komplex |
| Q4.B: Pro Region eigener Provider-Eintrag (`azure-openai-eu`, `azure-openai-us`) | Einfach | Duplikation |
| Q4.C: Nur EU-Provider zulassen (für DSGVO) | Compliance-sicher | Begrenzt Provider-Auswahl |

**Entscheidung bis:** Phase 3. **Verantwortlich:** Achim.

### Q5: Benchmark-Set öffentlich oder intern?

| Option | Pro | Con |
|--------|-----|-----|
| Q5.A: Intern (Wettbewerbsvorteil) | Provider können nicht "memorieren" | Keine externe Validierung |
| Q5.B: Öffentlich auf GitHub | Transparenz, Community-Beiträge | Memorization-Risiko |
| Q5.C: Interne Test-Sets, öffentliche Methodologie | Best of both | Mehr Pflegeaufwand |

**Entscheidung bis:** Phase 4. **Verantwortlich:** Achim.

### Q6 (NEU): Wie werden Benchmark-Referenzdaten versioniert?

| Option | Pro | Con |
|--------|-----|-----|
| Q6.A: `platform/benchmarks/aifw/v{N}/` (gewählt) | Klar versioniert, Diff sichtbar | Manuelle Bump-Disziplin |
| Q6.B: Git-Tags `benchmark-v1`, `benchmark-v2` | Implizit über Git-History | Schwerer auffindbar |
| Q6.C: DVC (Data Version Control) | Standard-Tool | Zusätzliche Infrastruktur |

### Q7 (NEU): Tie-Breaking bei gleichem Score zwischen Providern?

| Option | Pro | Con |
|--------|-----|-----|
| Q7.A: Default-Model gewinnt (Stabilität) | Konservativ, weniger Wechsel | Verpasst Optimierung |
| Q7.B: Random Selection | Statistisch fair | Unvorhersagbar |
| Q7.C: Provider-Diversität (LIFO — letzter Wechsel zuerst) | Anti-Lock-In | Komplex |

### Q8 (NEU): Wann wechselt `LLMModelCandidate` von "Evaluating" → "Approved"?

| Option | Pro | Con |
|--------|-----|-----|
| Q8.A: Manueller Schritt im Admin-UI | Volle Kontrolle | Bottleneck Achim |
| Q8.B: Automatisch wenn Quality ≥ 0.8 in 3 Benchmark-Runs | Skalierbar | Risiko: schlechtes Model wird automatisch promoted |
| Q8.C: Hybrid — Auto bei Quality ≥ 0.9, sonst manuell | Balance | Komplex |

### Q9 (NEU): Was bei Provider-Deprecation (z.B. Groq entfernt Model)?

| Option | Pro | Con |
|--------|-----|-----|
| Q9.A: Soft-Delete via `is_active=False` (gewählt impl.) | Audit-Trail bleibt | DB wächst |
| Q9.B: Hard-Delete | DB schlank | Verlust historischer Daten |
| Q9.C: Move zu `LLMModelArchive` Tabelle | Aufgeräumt | Mehr Code |

## Timeline

| Phase | Zeitraum | Aufwand | Priorität | Gate |
|-------|----------|---------|-----------|------|
| 1: Fallback-Chain | Q2 2026 | 2-3 Wochen | CRITICAL | Sofort umsetzbar |
| 2: Monitoring | Q3 2026 | 2 Wochen | HIGH | Nach Phase 1 stabil (7d Pilot) |
| 3: Provider-Katalog | Q3–Q4 2026 | fortlaufend (~2h/Monat) | MEDIUM | Nach Phase 2 stabil |
| 4: Auto-Routing | Q4 2026 – Q1 2027 | 4-6 Wochen | LOW | Nur wenn ≥30 Action Codes |

**Implementation-Tracking:**

- [ ] Phase 1.1: M2M `fallback_models` + Through-Table
- [ ] Phase 1.2: Service-Logik mit Backoff
- [ ] Phase 1.3: PyPI Release `aifw==0.6.0`
- [ ] Phase 1.4: Pilot-Deploy risk-hub (7d)
- [ ] Phase 1.5: Bulk-Rollout 19 Repos
- [ ] Phase 2.1: Availability-Felder + Celery-Task
- [ ] Phase 3.1: Provider-Katalog Models + Sync-Command
- [ ] Phase 4.1: Benchmark-Runner + LLM-as-Judge

## More Information

- **ADR-178** (LLM Gateway Consolidation) — Gateway-Code-Architektur. ADR-189 baut darauf auf.
- **ADR-115** (LLM Usage Logging) — Logging-Daten in `mcp_hub_db.llm_calls` als Cost-Report-Quelle.
- **ADR-009** (Service Layer Pattern) — `aifw.service.completion()` als Service-Layer.
- **ADR-022** (BigAutoField) — Alle neuen Models nutzen BigAutoField.
- **ADR-072** (Multi-Tenancy Schema Isolation) — `aifw`-Tabellen explizit im `public` Schema (siehe Datenbank-Architektur).
- **ADR-045** (SOPS) — N/A: Provider-Keys über GitHub Secrets, nicht SOPS.
- **ADR-054** (Architecture Guardian) — Phase-4-Auto-Routing benachrichtigt Guardian via Signal.
- **ADR-059** (Drift-Detector) — Felder `staleness_months`, `drift_check_paths` im Frontmatter.

## Glossar

| Begriff | Erklärung |
|---------|-----------|
| **Action Code** | Eindeutiger Bezeichner für einen LLM-Anwendungsfall (z.B. `begehung_photo_analysis`). Wird in DB-Tabelle `AIActionType` konfiguriert. |
| **aifw** | IIL-eigenes Python-Package für LLM-Aufrufe. Abstrahiert Provider-Unterschiede und steuert Model-Routing über die Datenbank. |
| **BLEU** | Bilingual Evaluation Understudy — automatische Metrik für Textgenerierungsqualität (Vergleich mit Referenztext). |
| **Celery Beat** | Scheduler-Komponente von Celery, die periodische Tasks zu festgelegten Zeiten ausführt (ähnlich Cron, aber Python-nativ). |
| **DPA** | Data Processing Agreement — vertragliche DSGVO-Vereinbarung mit Datenverarbeiter. |
| **DSGVO** | Datenschutz-Grundverordnung der EU (engl. GDPR) — Regelwerk zum Schutz personenbezogener Daten. |
| **EU AI Act** | EU-Verordnung 2024/1689 zu Künstlicher Intelligenz. Klassifiziert KI-Systeme nach Risiko und definiert Pflichten für Hochrisiko-Anwendungen. |
| **Expand-Contract** | Migrations-Pattern bei dem zuerst neue Strukturen additiv hinzugefügt werden (Expand), dann alte entfernt werden (Contract). Verhindert Breaking Changes bei laufendem Betrieb. |
| **Exponential Backoff** | Retry-Strategie bei der die Wartezeit zwischen Versuchen verdoppelt wird (1s, 2s, 4s, ...). Standard bei transienten Fehlern wie Rate-Limits. |
| **F1-Score** | Harmonisches Mittel aus Precision und Recall — Standardmetrik für Klassifikations- und Extraktionsaufgaben. |
| **Fallback-Chain** | Geordnete Liste alternativer Models, die bei Ausfall des Primär-Models automatisch durchprobiert werden. |
| **Fixture** | Vordefinierter Datensatz (YAML/JSON) der per Management-Command in eine Datenbank geladen wird. Ermöglicht reproduzierbaren initialen Daten-Stand. |
| **Human-Rating** | Manuelle Bewertung durch Fachexperten auf Skala 1–5. Gold-Standard für Textqualität. |
| **LiteLLM** | Open-Source Python-Library die 100+ LLM-Provider unter einer einheitlichen API zusammenfasst. Bereits Dependency von `aifw`. |
| **LLM-as-Judge** | Verfahren bei dem ein hochwertiges Sprachmodell die Qualität anderer Sprachmodelle bewertet. Skalierbarer Ersatz für Human-Rating. |
| **M2M (Many-to-Many)** | Datenbank-Beziehung bei der mehrere Datensätze beliebig viele andere referenzieren können. In Django via `ManyToManyField`. |
| **p95 Latenz** | 95. Perzentil der Antwortzeit — 95% aller Anfragen sind schneller als dieser Wert. Robuster als Durchschnitt. |
| **Provider** | Anbieter von LLM-APIs (z.B. OpenAI, Groq, Anthropic, Mistral, Cerebras). |
| **PyPI** | Python Package Index — zentraler Distributionskanal für Python-Pakete. `aifw` wird hier veröffentlicht. |
| **Rate-Limit** | Vom Provider auferlegte Begrenzung der Anfragen pro Zeitfenster (z.B. 60 RPM). Transienter Fehler — bei Überschreitung wird HTTP 429 zurückgegeben. |
| **ROUGE-L** | Recall-Oriented Understudy for Gisting Evaluation — Metrik für Zusammenfassungsqualität (längste gemeinsame Subsequenz). |
| **Through-Table** | Explizit definierte Zwischentabelle bei M2M-Beziehungen. Erlaubt zusätzliche Felder (z.B. `priority`) auf der Beziehung selbst. |
| **Token** | Kleinste Texteinheit für LLMs (~4 Zeichen Deutsch). Abrechnungseinheit bei Provider-APIs. |
