# Advocatus Diaboli — Cloud-Routine (KONZ-platform-070 Z2 Stufe 2)

**Zweck.** Ein adversarialer, *beratender* LLM-Review fuer offene PRs der Pilot-Repos
(`registry/review-profile.yaml` → `pilot`, O2). Laeuft nur, wenn der Risiko-Klassifikator
anschlaegt; schreibt genau einen PR-Kommentar je PR-Stand und bucht Befunde ins Review-Ledger
(dev-hub, WP3). Nie Approve, Request-Changes, Label oder Commit (Lotsen-Charta Art. 3).
Mandat: [#3903](https://github.com/achimdehnert/platform/issues/3903); Owner-Entscheid O3
(2026-10-13): „Opus; Fable nur für `needs-deep-review`“.

## Bauteile

| Datei | Rolle |
|---|---|
| `registry/review-risiko.yaml` | Trigger (RK-*), Autoren-Ausschluss, Routine-Parameter, Modell-ID (die eine Stelle) |
| `tools/review_risiko.py` | Klassifikator-CLI (`--repo --pr`, Exit 0 = laeuft), `--repos`, `--render`, `--check` |
| `agents/advocatus/PROMPT.template.md` | Vorlage der Routine-Anweisung (Hand gepflegt) |
| `agents/advocatus/PROMPT.md` | **generiert**, MANAGED-BY-Fusszeile, Drift-Test in `make test` |
| `agents/advocatus/routine.json` | **generiert**, Body fuer die Trigger-API (`environment_id` = Platzhalter) |
| `tools/advocatus_ledger_post.py` | Befunde validieren und als Bulk ins Ledger buchen; `--dry-run` |

Aenderung an Trigger, Modell, Cron oder Vorlage: YAML/Vorlage editieren, dann
`python3 tools/review_risiko.py --render`; `--check` (CI) meldet Drift.

## Owner-Schritte (einmalig)

1. Ledger-Token als Umgebungsvariable `REVIEW_LEDGER_TOKEN` in der Cloud-Umgebung der Routine
   hinterlegen (nur der Name steht im Repo; Wert aus dem Secret-Speicher, nie im Checkout).
2. Routine anlegen: Body aus `agents/advocatus/routine.json`, `environment_id` durch die eigene
   Umgebung ersetzen (`/schedule` → create). Erwartet: Routine `advocatus-diaboli`, Cron
   `0 7-17/2 * * 1-5` (werktags alle 2 h, UTC).
3. GitHub-Zugang der Routine pruefen: `gh pr view` und `gh pr comment` muessen fuer alle Pilot-Repos
   funktionieren, auch `iilgmbh/risk-hub` (anderer Org-Owner).
4. Ersten Lauf von Hand ausloesen (`run`) und das Run-Log lesen: Abschnitt 6 der Anweisung
   (Abschlussmeldung) muss eine Tabelle je PR zeigen.

## Kill-Gate-Kennzahlen (KONZ-070 §8, Entscheid 2026-12-15)

| Kennzahl | Ziel | Ablesen |
|---|---|---|
| K4 Praezision Advocatus | ≥ 60 % der Befunde `bestaetigt` | Ledger-Export, `quelle=advocatus`, Ausgang je Zeile |
| K5 Latenz | Kommentar ≤ 15 min nach Push | Marker `<!-- advocatus:<sha> -->` vs. Push-Zeit; Cron (2 h) erreicht das nicht — Stufe 1 misst nur |
| Kosten | ≤ Budget aus #3903 | `kosten_usd` je Ledger-Zeile, Summe pro Woche |
| Rauschen | 0 Befunde ohne Locator/Beleg | Stichprobe der PR-Kommentare |

Ledger-Export: `GET /api/v1/review-ledger/befunde/?quelle=advocatus` (dev-hub, Token wie oben);
Quittung `bestaetigt`/`widerlegt` setzt der Mensch im Ledger, nicht der Advocatus.

## Grenzen der Stufe 1

- Leere Laeufe (0 Befunde) erzeugen keine Ledger-Zeile — sie haetten keinen quittierbaren Ausgang.
- Cron statt Event-Trigger; derselbe PR-Stand wird nie zweimal bewertet (Dedup-Marker).
- Hoechstens `max_prs_je_lauf` PRs je Lauf; der Rest wartet auf den naechsten Lauf.
