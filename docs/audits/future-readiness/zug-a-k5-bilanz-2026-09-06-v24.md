# Future-Readiness Zug A — K5-Bilanz aus dem v2.4-Stand (2026-09-06)

Auftrag: [platform#2737](https://github.com/achimdehnert/platform/issues/2737) (Handover-Faden 28) und K5 aus [platform#2787](https://github.com/achimdehnert/platform/issues/2787). Detaildaten liegen in dev-hub (privat): Phase C `docs/audits/future-readiness/2026-09-03/` (dev-hub#321), v2.4-Neulauf `2026-09-04/` (dev-hub#326), Messung nach Zug A `2026-09-04-zug-a-k5/` (dev-hub#331). Diese Datei enthält nur Aggregate, Repo-Namen und Readiness-Werte — keine Personendaten, keine Secrets, keine Einstellungswerte einzelner privater Repos.

## Warum eine dritte Rechnung nötig war

Der v2.4-Neulauf vom 04.09. (dev-hub#326) sollte der saubere Vorher-Wert für Zug A sein. Er lief aber nach den ersten Owner-Merges der Zug-A-Welle: 20 der 56 Repos trugen dort bereits eine `SECURITY.md`, 11 schon die Third-Party-Notices. Sein Median 53 mischt daher Rubrik-Änderung und Zug-A-Inhalt. Der saubere Vorher-Wert entsteht, wenn die unveränderte Phase-C-Evidenz vom 03.09. mit dem v2.4-Bewerter neu gerechnet wird (Spalte **A′**). Kontrolle: bei den 37 Repos, deren `SECURITY.md`/Notices-Stand zwischen A′ und dem Neulauf gleich blieb, stimmt die Readiness in 36 Fällen überein. Ausnahme ttz-hub: gleicher Commit, aber D05 im Evidenzpaket vom 04.09. anders belegt (GitHub-seitiger Zustand), im Lauf nach Zug A wieder wie am 03.09.

## Kennzahlen

| Kennzahl | A · Phase C 03.09. (v2.3) | A′ · dieselbe Evidenz, v2.4 | C · nach Zug A 04.09. (v2.4) |
|---|---|---|---|
| Readiness Median | 52.0 | 51.5 | 54.0 |
| D08.4 `SECURITY.md` ok | 1 / 56 | 1 / 56 | 43 / 56 |
| D11.2 Third-Party-Notices ok | 0 / 56 | 0 / 56 | 33 / 56 |
| P1-Findings | 53 | n. v.¹ | 53 |

¹ Die P1-Einstufung hängt an den Eingaben `prod-deploy`/`reach`, die in den Ergebnisdateien nicht abgelegt sind; die Neurechnung konnte sie nicht reproduzieren. Belastbar ist: v2.3 (03.09.), v2.4-Neulauf (04.09.) und nach Zug A jeweils 53 P1 — Zug A verändert keine P1-Findings, es ist Doku.

## Zwei Effekte, getrennt

| Effekt | Summe Readiness-Punkte | Repos + / = / − | Spanne |
|---|---|---|---|
| Rubrik v2.3 → v2.4 (A′ − A) | -9 | 13 / 31 / 12 | -13 … +9 |
| Zug A (C − A′) | +145 | 42 / 14 / 0 | +0 … +13 |

**Korrektur zur Zusammenfassung des Neulaufs (dev-hub#326):** Dort gelten 27 Repos als „durch die Regeländerungen verschoben“ und der Median steigt 52 → 53. Die Regeln allein bewegen 25 Repos und senken den Median auf 51,5 (37a wertet D06 Security/Supply Chain jetzt, oft niedrig; D02.1 wertet ein leeres Manifest als `fail`). Den Anstieg auf 53 lieferten die 20 Repos, in denen Zug A vor dem Lauf schon gemergt war. Die Vorher/Nachher-Tabelle in #326 ist damit als Rubrik-Bilanz nicht verwendbar; diese hier ersetzt sie.

## Je Repo

Δ Rubrik = A′ − A · Δ Zug A = C − A′ · D08.4 / D11.2: Stand A′ → C.

| # | Repo | A | A′ | C | Δ Rubrik | Δ Zug A | D08.4 | D11.2 |
|---|---|---|---|---|---|---|---|---|
| 1 | achimdehnert/137-hub | 58 | 58 | 62 | +0 | +4 | — → ok | — → ok |
| 2 | achimdehnert/aifw | 60 | 60 | 63 | +0 | +3 | — → ok | — → ok |
| 3 | achimdehnert/apo-hub | 46 | 49 | 49 | +3 | +0 | — → — | — → — |
| 4 | achimdehnert/authoringfw | 53 | 53 | 56 | +0 | +3 | — → ok | — → ok |
| 5 | achimdehnert/bahn-hub | 48 | 50 | 50 | +2 | +0 | — → — | — → — |
| 6 | achimdehnert/billing-hub | 56 | 57 | 60 | +1 | +3 | — → ok | — → ok |
| 7 | achimdehnert/cad-hub | 47 | 47 | 50 | +0 | +3 | — → ok | — → ok |
| 8 | achimdehnert/ci-sichtbarkeit-probe | 11 | 18 | 20 | +7 | +2 | — → ok | — → — |
| 9 | achimdehnert/ci-sichtbarkeit-probe-caller | 18 | 18 | 20 | +0 | +2 | — → ok | — → — |
| 10 | achimdehnert/coach-hub | 57 | 54 | 54 | -3 | +0 | — → — | — → — |
| 11 | achimdehnert/decks-hub | 18 | 23 | 25 | +5 | +2 | — → ok | — → — |
| 12 | achimdehnert/design-hub | 51 | 42 | 43 | -9 | +1 | — → ok | — → — |
| 13 | achimdehnert/dev-hub | 70 | 72 | 72 | +2 | +0 | — → — | — → — |
| 14 | achimdehnert/dms-hub | 55 | 56 | 59 | +1 | +3 | — → ok | — → ok |
| 15 | achimdehnert/doc-hub | 32 | 29 | 31 | -3 | +2 | — → ok | — → — |
| 16 | achimdehnert/gaeb-toolkit | 51 | 48 | 53 | -3 | +5 | — → ok | — → ok |
| 17 | achimdehnert/ifc-mcp | 38 | 38 | 43 | +0 | +5 | — → ok | — → ok |
| 18 | achimdehnert/iil-adrfw | 53 | 53 | 57 | +0 | +4 | — → ok | — → ok |
| 19 | achimdehnert/iil-codeguard | 49 | 49 | 53 | +0 | +4 | — → ok | — → ok |
| 20 | achimdehnert/iil-demo-fixture | 43 | 43 | 46 | +0 | +3 | — → ok | — → ok |
| 21 | achimdehnert/iil-django-commons | 51 | 51 | 55 | +0 | +4 | — → ok | — → ok |
| 22 | achimdehnert/iil-enrichment | 43 | 42 | 46 | -1 | +4 | — → ok | — → ok |
| 23 | achimdehnert/iil-ingest | 43 | 43 | 48 | +0 | +5 | — → ok | — → ok |
| 24 | achimdehnert/iil-reflex | 57 | 57 | 60 | +0 | +3 | — → ok | — → ok |
| 25 | achimdehnert/iil-testkit | 53 | 53 | 56 | +0 | +3 | — → ok | — → ok |
| 26 | achimdehnert/illustration-hub | 57 | 62 | 65 | +5 | +3 | — → ok | — → ok |
| 27 | achimdehnert/infra-deploy | 25 | 25 | 25 | +0 | +0 | — → — | — → — |
| 28 | achimdehnert/lastwar-alliance-ops | 56 | 49 | 49 | -7 | +0 | — → — | — → — |
| 29 | achimdehnert/lastwar-bot | 40 | 49 | 49 | +9 | +0 | — → — | — → — |
| 30 | achimdehnert/learn-hub | 51 | 51 | 54 | +0 | +3 | — → ok | — → ok |
| 31 | achimdehnert/learnfw | 56 | 56 | 59 | +0 | +3 | — → ok | — → ok |
| 32 | achimdehnert/manuskripte | 27 | 27 | 40 | +0 | +13 | — → ok | n. a. → n. a. |
| 33 | achimdehnert/mcp-hub | 71 | 68 | 68 | -3 | +0 | — → — | — → — |
| 34 | achimdehnert/molkerei-landing | 11 | 11 | 14 | +0 | +3 | — → ok | — → — |
| 35 | achimdehnert/music-lab | 32 | 30 | 34 | -2 | +4 | — → ok | — → ok |
| 36 | achimdehnert/news-hub | 35 | 41 | 41 | +6 | +0 | — → — | — → — |
| 37 | achimdehnert/nl2cad | 68 | 55 | 59 | -13 | +4 | — → ok | — → ok |
| 38 | achimdehnert/odoo-hub | 54 | 54 | 57 | +0 | +3 | — → ok | — → ok |
| 39 | achimdehnert/outlinefw | 53 | 53 | 56 | +0 | +3 | — → ok | — → ok |
| 40 | achimdehnert/platform | 74 | 74 | 77 | +0 | +3 | — → ok | — → ok |
| 41 | achimdehnert/pptx-hub | 59 | 55 | 58 | -4 | +3 | — → ok | — → ok |
| 42 | achimdehnert/promptfw | 56 | 56 | 59 | +0 | +3 | — → ok | — → ok |
| 43 | achimdehnert/researchfw | 57 | 57 | 60 | +0 | +3 | — → ok | — → ok |
| 44 | achimdehnert/robo-lab | 28 | 26 | 28 | -2 | +2 | — → ok | — → — |
| 45 | achimdehnert/schutztat-reporting | 25 | 25 | 27 | +0 | +2 | — → ok | — → — |
| 46 | achimdehnert/shared-ci | 27 | 27 | 27 | +0 | +0 | — → — | — → — |
| 47 | achimdehnert/trading-hub | 50 | 52 | 56 | +2 | +4 | — → ok | — → ok |
| 48 | achimdehnert/travel-beat | 70 | 64 | 64 | -6 | +0 | — → — | — → — |
| 49 | achimdehnert/weltenfw | 53 | 53 | 56 | +0 | +3 | — → ok | — → ok |
| 50 | achimdehnert/weltenhub | 56 | 57 | 60 | +1 | +3 | — → ok | — → ok |
| 51 | achimdehnert/writing-hub | 64 | 67 | 70 | +3 | +3 | — → ok | — → ok |
| 52 | iilgmbh/risk-hub | 63 | 63 | 63 | +0 | +0 | — → — | — → — |
| 53 | meiki-lra/frist-hub | 56 | 56 | 60 | +0 | +4 | — → ok | — → ok |
| 54 | meiki-lra/meiki-dms | 54 | 54 | 54 | +0 | +0 | — → — | — → — |
| 55 | meiki-lra/meiki-hub | 47 | 47 | 47 | +0 | +0 | ok → ok | — → — |
| 56 | ttz-lif/ttz-hub | 43 | 43 | 48 | +0 | +5 | — → ok | — → ok |

## Owner-Fragen aus den Deltas

1. **v2.4 als Basislinie akzeptieren?** Die Rubrik nimmt 12 Repos Punkte (nl2cad −13, design-hub −9, lastwar-alliance-ops −7, travel-beat −6, pptx-hub −4, coach-hub −3), weil D06 Security/Supply Chain jetzt gewertet wird. Das ist Messehrlichkeit, kein Rückschritt im Repo. Empfehlung: ja, künftige Läufe nur noch gegen A′/C vergleichen.
2. **Leeres Manifest (D02.1 `fail`) — füllen oder hinnehmen?** Betroffen design-hub, iil-enrichment, iil-ingest, nl2cad; bei nl2cad und design-hub kostet es die meisten Punkte. Empfehlung: je Repo entscheiden, ob ein Abhängigkeits-Manifest fachlich sinnvoll ist; wo nicht, Archetyp prüfen.
3. **D11.2 ohne Manifest = `fail`?** Neun Repos ohne Manifest bekommen für fehlende Notices ein `fail`, obwohl K2 sie ausdrücklich ausnimmt (ci-sichtbarkeit-probe, -caller, decks-hub, design-hub, doc-hub, molkerei-landing, robo-lab, schutztat-reporting, meiki-hub); manuskripte ist korrekt n. a. Empfehlung: Regel für v2.5 — ohne Manifest ist D11.2 `not_applicable`.
4. **Rubrik-Kennzeichnung im Bewerter.** Die Messung nach Zug A trägt in den Dateien `rubric_version: 2.3-2026-09-04`, rechnet aber mit v2.4 (D06 gewertet, D02.1 `fail`). Ohne Angabe stempelt der Bewerter ein falsches Etikett. Werkzeug-Fix, kein Owner-Entscheid — [platform#2876](https://github.com/achimdehnert/platform/issues/2876).

## Methode

`tools/future_readiness_score.py` (platform `main` 76b92063, Logik v2.4) über die 56 Evidenzpakete `2026-09-03/evidence/*.evidence.json`; Klassifikation (Archetyp, Kritikalität, Lebenszyklus, Datenklasse, Tiefe T1, Horizont) aus den Phase-C-Ergebnisdateien übernommen, `--run-date 2026-09-03`, `--rubric-version 2.4`; 56/56 ohne Fehler. Spalten A und C unverändert aus dev-hub#321 bzw. dev-hub#331. Zählungen aus den JSON-Dateien, nicht aus den Markdown-Berichten.

