# adr-review

Minimales CLI für KI-gestützte ADR-Architektur-Reviews auf Pull Requests.
Konsumiert von `.github/workflows/adr-review.yml` (`pip install ./packages/adr-review`
→ `adr-review --pr <n> --repo <owner/name>`).

## Verhalten

1. Lädt geänderte ADR-Dateien des PR (Trigger-Pfade wie im Workflow).
2. Reviewt sie via **litellm → Flatrate Cerebras/Groq** gegen eine
   MADR-/Advocatus-Diabolus-Checkliste. **Kein Anthropic, kein
   ANTHROPIC_API_KEY** (Plattform-`llm-routing`-Policy: Cerebras/Groq first).
3. Upsertet **einen** PR-Kommentar (Marker `<!-- adr-review -->`, kein Spam).
4. Setzt Score-Label: `adr-review-passed` (≥7) · `-concerns` (5–6) · `-failed` (<5).

**Informativ, nicht blockierend.** Default Exit 0 (auch bei niedrigem Score) —
bewusst kein Enforcement-Gate (ADR-199-Lehre). `--fail-under N` macht CI
optional rot unter Score N.

## Env

| Var | Pflicht | Default |
|---|---|---|
| `GITHUB_TOKEN` | ja | — |
| `CEREBRAS_API_KEY` | eine LLM-Quelle nötig | — |
| `GROQ_API_KEY` | (für Fallback) | — |
| `ADR_REVIEW_MODEL` | nein | `cerebras/qwen-3-235b-a22b-instruct-2507` |
| `ADR_REVIEW_FALLBACK` | nein | `groq/llama-3.3-70b-versatile` |
| `ADR_REVIEW_DEEP_MODEL` | nein | `cerebras/zai-glm-4.7` |
| `ADR_REVIEW_ESCALATE_BELOW` | nein | `6` |
| `ADR_REVIEW_DEEP_LABEL` | nein | `adr-deep-review` |

### Eskalation (zweiter Pass)

Günstiger Erstpass für alle PRs. Ein zweiter Pass mit dem stärkeren
Flatrate-Modell läuft, wenn **eines** zutrifft: PR trägt Label
`adr-deep-review` · >1 ADR-Datei (cross-cutting) · Erstpass-Score < Schwelle.
Der Kommentar nennt das genutzte Modell + Eskalationsgrund.

> **Ehrliche Grenze:** Eskalation verengt die Qualitätslücke, schließt sie
> **nicht**. Für tiefe, kontroverse Architektur-Synthese (versteckte
> Selbstwidersprüche, repo-übergreifende Implikationen) bleibt ein
> Mensch-/In-Session-Frontier-Review nötig — das Paket ist Sicherheitsnetz +
> Checkliste, kein Ersatz. Modellnamen werden künftig auf ADR-208-Resolver-
> Aliase gemappt (noch nicht hart gekoppelt).

Keys werden wie bei `print_agent` aufgelöst: env-Var **oder**
`~/shared/secrets-inbox/<provider>_api_key`. Fehlt `GITHUB_TOKEN`, jeder
LLM-Key oder enthält der PR keine ADR-Datei → sauberer Exit 0 mit Hinweis
(kein false-rot, konsistent mit dem Workflow-Guard).

Default-Modell = Policy-Tier-1a (user-visible Prosa), Flatrate, kein Frontier.
Override jederzeit via Env. ADR-208-Resolver als künftige Auflösung vorgesehen,
bewusst noch nicht hart gekoppelt (Paket bleibt minimal).

## Lokal

```bash
pip install ./packages/adr-review
adr-review --pr 175 --repo achimdehnert/platform --dry-run
pytest packages/adr-review/tests
```
