# adr-review

Minimales CLI für KI-gestützte ADR-Architektur-Reviews auf Pull Requests.
Konsumiert von `.github/workflows/adr-review.yml` (`pip install ./packages/adr-review`
→ `adr-review --pr <n> --repo <owner/name>`).

## Verhalten

1. Lädt geänderte ADR-Dateien des PR (Trigger-Pfade wie im Workflow).
2. Reviewt sie via Claude gegen eine MADR-/Advocatus-Diabolus-Checkliste
   (System-Prompt ge-cached).
3. Upsertet **einen** PR-Kommentar (Marker `<!-- adr-review -->`, kein Spam).
4. Setzt Score-Label: `adr-review-passed` (≥7) · `-concerns` (5–6) · `-failed` (<5).

**Informativ, nicht blockierend.** Default Exit 0 (auch bei niedrigem Score) —
bewusst kein Enforcement-Gate (ADR-199-Lehre). `--fail-under N` macht CI
optional rot unter Score N.

## Env

| Var | Pflicht | Default |
|---|---|---|
| `GITHUB_TOKEN` | ja | — |
| `ANTHROPIC_API_KEY` | ja | — |
| `ADR_REVIEW_MODEL` | nein | `claude-sonnet-4-6` |

Fehlt ein Pflicht-Secret oder enthält der PR keine ADR-Datei → sauberer
Exit 0 mit Hinweis (kein false-rot, konsistent mit dem Workflow-Guard).

## Lokal

```bash
pip install ./packages/adr-review
adr-review --pr 175 --repo achimdehnert/platform --dry-run
pytest packages/adr-review/tests
```

Künftig: Modellauflösung über den internen Resolver (ADR-208) statt
hartem Default — bewusst noch nicht hart gekoppelt (Paket bleibt minimal).
