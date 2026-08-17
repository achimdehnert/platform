---
retro_schema: 1
date: 2026-08-17
repo_scope: [platform, travel-beat, illustration-hub]
session_id: 37e8e0-incr
footprint: full
findings_total: 6
findings_survived: 4
refuted_rate: 0.33
phase3_refuted: 2
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 4
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [gate-matches-spelling-not-substance]
recurring_findings: [gate-matches-spelling-not-substance, claim-before-cheapest-check]
---

# Increment-Retro 2026-08-17 — platform (`37e8e0-incr`)

Anschluss an [`session-retro-2026-08-17-platform-37e8e0.md`](session-retro-2026-08-17-platform-37e8e0.md).
**Zweck:** die drei Befunde nachholen, die der Parent als *nicht falsifiziert* führen musste
(Subagenten waren untersagt), und das danach entstandene Material prüfen. Der Owner hat
Subagenten für `/session-retro` freigegeben — damit lief Phase 3 erstmals echt.

**Fünf Agenten, alle mit fremdem Kontext:** drei Skeptiker je Parent-Befund, ein Finder auf
das neue Material, ein weiterer Skeptiker auf einen strittigen Finder-Befund.

## 1. Executive Summary

- **Vier von vier Agenten haben mein Bild geändert.** Kein einziger bestätigte nur.
- **Ein Parent-Befund ist widerlegt** (#11 Rework), **einer trägt eine falsche Kategorie**
  (#10), **einer überlebt mit unbelegter Kausal-Hälfte** (#9). Der Parent-Report wird in
  diesem PR entsprechend korrigiert.
- **Der Finder produzierte selbst einen falschen `hoch`-Befund** — 404 als Abwesenheit
  gelesen. Es brauchte einen fünften Agenten, um ihn zu entfernen. Fremder Kontext macht
  **unabhängig**, nicht **richtig**.
- **Ursache dafür ist mein Prompt-Design:** die Kalibrier-Pflicht stand in **zwei von vier**
  Agent-Prompts. Genau der Agent ohne sie fiel in die Falle; die beiden mit ihr führten ihre
  Nullbefunde korrekt als *ungeklärt*.
- **`gate-matches-spelling-not-substance` steht mit I1 bei ×2 ⇒ gate-pflichtig.** Das war
  der mechanische Zweck dieses Increments.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| I1 | Mein Trigger-Fix patchte die zwei gemeldeten Schreibweisen, nicht die Wortklasse — `individuell lösen`, `punktuelle Lösung`, `Sonderregel`, `hart codiert` feuerten weiter nicht | fehlende Validierung | mittel | SURVIVES | Simulation von `find_matches()` gegen die Trigger-Zeile aus dem PR-Diff; behoben, Gegenprobe 27/27 | `gate-matches-spelling-not-substance` **×2** |
| I2 | Phase `0g` stand physisch **vor** `0f` im Skill-Dokument | Werkzeug | mittel | SURVIVES | `gh pr diff 2036` Z. 9 vs. Z. 52; `git show origin/main:.windsurf/workflows/session-ende.md` zeigt vorher 0a…0f korrekt | — |
| I3 | Required Check `ci / gate` sei auf travel-beat#82 / illustration-hub#260 nie gelaufen | fehlende Validierung | hoch | **REFUTED** | `gh pr checks 82` → `ci / gate pass 5s` (Run 31993874876/Job 95282073779); `gh pr view 260 --json statusCheckRollup` → `ci / gate=SUCCESS`. Die REST-404 des Finders waren die bekannte sporadische Instabilität | `claim-before-cheapest-check` |
| I4 | Ausbleibender Deploy auf travel-beat sei derselbe Defekt wie I3 | fehlende Validierung | niedrig | **REFUTED** | folgt aus I3; der ausbleibende Deploy ist die **beabsichtigte** Wirkung des `[skip ci]` im Squash-Subject bei einer docs-only-Änderung | — |
| I5 | Die Kalibrier-Pflicht für Nullbefunde stand in **2 von 4** Agent-Prompts; der Agent ohne sie erzeugte I3 | Prozesslücke | mittel | SURVIVES | eigene Prompt-Texte; die zwei Prompts *mit* Pflicht führten ihre 404 korrekt als ungeklärt | `claim-before-cheapest-check` |
| I6 | Ein Skeptiker lieferte trotz wörtlicher Anweisung „binär, kein teilweise" das Verdikt `SURVIVES (teilweise geschwächt)` | Prozesslücke | niedrig | SURVIVES | Agent-Ausgabe zu Parent-#10; Skill führt das dritte Verdikt als Anti-Pattern | — |

## 2b. Nachgeholte Falsifikation der Parent-Befunde

| Parent-# | Behauptung | Verdikt | Entscheidender Beleg |
|---|---|---|---|
| #9 | Scope-Eskalation, Freigaben stützten sich auf einen um Faktor 2,6 unterzählenden Melder | **SURVIVES** | Unabhängige Nachzählung über `gh search prs` org-weit: ~36–37 PRs über ~31 Repos, ohne die Melder-Logik. **Aber:** ob die Freigaben *tatsächlich* am Melder hingen, ist aus Artefakten nicht belegbar — diese Hälfte bleibt Hypothese |
| #10 | bahn-hub#13 mit rotem `lint` gemergt, Kategorie „verfrühte Festlegung" | **SURVIVES, Kategorie falsch** | Diff ist **eine Zeile** in `secret-scan.yml`, keine Python-Datei; bahn-hub hat **kein** Required-Check-Ruleset (kalibriert gegen platform, wo eines existiert). Der PR hat einen vorbestehenden roten Lint **nicht behoben**, nicht erzeugt → Kategorie „bewusste Inkaufnahme", Severity niedrig |
| #11 | Zwölf PRs mussten nach dem Merge-Angebot erneut geöffnet und erweitert werden | **REFUTED** | Alle 12 PRs haben 4 Commits binnen ~30 min; `mergedAt` liegt überall **nach** dem letzten Commit (travel-beat#83: Commit 11:59:26, Merge 12:18:38). Kein Reopen, kein zweiter PR. Die Messung fiel zwischen Commit 1 und 2 **desselben offenen PRs** — Iteration, nicht Rework |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **4** | Zweck erfüllt: drei offene Befunde falsifiziert, Slug auf ×2 gehoben — aber I3 kostete einen zusätzlichen Agenten |
| architektur_design | **4** | Skeptiker je Befund statt Bündelung war bei drei Bewertungsbefunden die richtige Wahl (Skill-Regel) |
| code_konventionstreue | **3** | I1/I2: zwei Konventionsfehler in meinen eigenen frischen Artefakten, beide von fremdem Kontext gefunden |
| risiko_debt | **4** | beide Fixes noch vor dem Merge eingearbeitet; nichts Falsches gelandet |
| prozess_effizienz | **3** | I5: dieselbe Pflicht nur halb vergeben → ein vermeidbarer Fehlbefund und ein Zusatz-Agent |
| entscheidungsqualitaet | **3** | I1 ist der zweite Anlauf derselben Klasse in derselben Datei; die erste Korrektur war Symptom-Patchen |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll | eliminiert |
|---|---|---|
| Trigger-Fix deckte die zwei gemeldeten Varianten ab | Nach einem Trigger-/Muster-Fix die **Wortklasse durchdeklinieren** (Verb/Adjektiv/Substantiv, c/k, Umlaut/ae-oe-ue), nicht die Meldung nachbauen | I1 |
| Neue Phase am bequemsten Anker eingefügt | Phasen-Einfügung immer gegen die **Reihenfolge** prüfen, nicht nur gegen den Anker-Treffer | I2 |
| REST-404 als „kein Check gelaufen" gelesen | Vor jedem Absence-Schluss **einen zweiten Abfrageweg** nutzen (`gh pr checks` neben REST) — nicht nur kalibrieren, sondern den Weg wechseln | I3, I4 |
| Kalibrier-Pflicht in 2 von 4 Prompts | Agent-Prompts aus **einem Textbaustein** bauen, nicht je Agent frei formulieren — dieselbe Pflicht darf nicht von meiner Tagesform abhängen | I5 |
| „binär" als Prosa im Prompt | Verdikt maschinenlesbar erzwingen (erste Zeile `VERDIKT: SURVIVES|REFUTED`, alles andere zurückweisen) | I6 |

## 5. Längsschnitt

- **`gate-matches-spelling-not-substance`: Parent ×1 + dieser Report ×1 = ×2 ⇒ GATE-PFLICHT.**
  Kandidat: ein Lint über Hook-/Gate-Skripte und Policy-Trigger, der Text-Matching auf
  Kommandozeilen bzw. auf Wortlisten als Zählgrundlage markiert.
- **`claim-before-cheapest-check`** (Parent bei ×44): I3 und I5 sind zwei weitere Instanzen —
  diesmal **nicht meine**, sondern die eines Subagenten und die meiner Prompt-Vergabe. Das
  ist die interessantere Variante: die Klasse überlebt den Wechsel des Handelnden.

### 5b. Autonomie-Kalibrierung

`over_ask: 0` · `over_act: 0`. Alle fünf Agenten liefen auf ausdrückliche Owner-Freigabe
(„subagenten und dyn workflows ab sofort für session-retro erlaubt", „3 go"). Die zwei
Fixes (I1, I2) gingen in **bereits offene, unmergte** PRs — kein neuer Artefakt-Zuwachs.

## 6. Verankerung

- Bestehende Memory `feedback_condition_matches_spelling_not_substance` um I1 als **fünfte
  Instanz** ergänzen (sie führt bisher vier).
- Bestehende Memory `feedback_absence_claim_needs_full_family_grep` deckt I3 bereits über
  den heute ergänzten Punkt „zweite Suche in anderer Formulierung" ab — **keine** neue Datei.
- Kein ADR-Kandidat.

## 7. Maßnahmen

### 🟢 Offen — dein Zug

1. 🟢 Gate zu `gate-matches-spelling-not-substance` bauen (×2, gate-pflichtig)
2. 🟢 Textbaustein für Agent-Prompts (Kalibrier-Pflicht + Verdikt-Format) — behebt I5+I6

### ✅ Erledigt

| # | Item | Beleg |
|---|---|---|
| 3 | I1 behoben | Wortklasse, 27/27, in #2038 |
| 4 | I2 behoben | 0g hinter 0f, in #2036 |
| 5 | Parent korrigiert | dieser PR |

## 8. Nicht verifiziert (Restlücken)

| # | Lücke | Billigster Check |
|---|---|---|
| 1 | Kausal-Hälfte von Parent-#9 (hingen die Freigaben am Melder?) — aus Artefakten nicht belegbar, bleibt Hypothese | keiner; nur der Owner kann es beantworten |
| 2 | Ob `bahn-hub` `main` aktuell rot steht — sporadische 404 auf `commits/<branch>`, sauber kalibriert und als ungeklärt geführt | später `gh run list --repo achimdehnert/bahn-hub --branch main -L 3` |
| 3 | **Phase 5 (Meta-Reviewer) erneut nicht gelaufen** — dieser Report ist nicht gegen die Skill-Regeln gegengelesen | ein Sonnet-Subagent mit Report + Skill, ohne Session-Kontext |
| 4 | Der Finder prüfte nicht alle ~15 Policy-Dateien einzeln und verifizierte die Zahlen aus #2037 nicht gegen shared-ci (eigene Angabe, Zeitbudget) | gezielter Nachlauf auf die zwei Punkte |

**Der Vierer:** *getan* — drei Parent-Befunde falsifiziert, zwei eigene Fehler vor dem Merge
behoben, ein Slug auf Gate-Pflicht gehoben. *angenommen* — dass die vier kommandobelegten
Increment-Befunde ohne weitere Prüfung tragen. *nicht verifizierbar* — die vier Lücken oben.
*offen geblieben* — das Gate selbst, der Prompt-Textbaustein, und Phase 5.
