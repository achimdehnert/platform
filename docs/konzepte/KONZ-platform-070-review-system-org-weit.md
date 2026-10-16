---
concept_id: KONZ-platform-070
title: Review-System org-weit — Regeln als Daten, Advocatus Diaboli je PR, Befund-Ledger als Lernschleife
pipeline_status: idea
tier: T3                   # Cross-Repo (shared-ci + 61 Repos in 4 Orgs), Security-Perimeter (Branch-Schutz, Bot-Token), neue Boundary (Review-Urteil ↔ Merge-Mandat)
owner: Achim Dehnert
spec_refs: []              # Governance-Capability, kein Klickdummy
adr_threshold: ADR         # org-weite Distribution eines Review-Agenten = eigener ADR (adr-threshold.md; so auch KONZ-028 selbst). Dieses KONZ ist der Zielzustand VOR dem ADR; Pilot auf 3 Repos ohne ADR.
review_by: 2026-12-15
kill_criteria: "Pilot (platform, risk-hub, writing-hub) bis 2026-12-15: (a) menschlich bestätigte Präzision der Advocatus-Befunde (bestätigt / (bestätigt+widerlegt)) < 50 % ODER (b) Owner-Zeit je PR steigt gegenüber Baseline (pr-review-prep-Kommentare als Maß) ODER (c) ≥ 1 falsch-autoritativer BLOCK ohne Locator im Pilot ⇒ Stufe 2 (org-weit) entfällt, Stufe 1 fällt auf Bot-Approval + Regel-Engine zurück. Ja/Nein-Auswertung am review_by-Termin."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "GitHub API branches/main/protection + contents/.github für 61 nicht-archivierte Repos aus registry/canonical.yaml", commit_or_pr: "Inventur 2026-10-13, Sitzung platform-a8", opened_in_session: true}
  - {claim_id: C2, source_path: "GitHub Search is:pr is:merged merged:>=2026-09-13 review:none je Org", commit_or_pr: "Abfrage 2026-10-13", opened_in_session: true}
  - {claim_id: C3, source_path: ".github/workflows/bot-review.yml + tools/bot_review_kandidaten.py (TABU) + iilgmbh/shared-ci _bot-review.yml", commit_or_pr: "origin/main 2026-10-13; platform#3268", opened_in_session: true}
  - {claim_id: C4, source_path: "agents/context_reviewer.py (537 Zeilen, nur re/argparse/json — kein LLM; detect_affected_adrs/principles/projects)", commit_or_pr: "origin/main 2026-10-13", opened_in_session: true}
  - {claim_id: C5, source_path: ".windsurf/rules/reviewer.md (10 Prinzipien + BLOCK-Liste als Prosa, trigger manual)", commit_or_pr: "origin/main 2026-10-13", opened_in_session: true}
  - {claim_id: C6, source_path: "Cloud-Routinen deep-review (Cron 15 6-18/3 Mo–Fr, Label needs-deep-review, max 3 PRs, advisory) und pr-review-prep (0 6 Mo–Fr, max 8 PRs) — beide nur achimdehnert/platform", commit_or_pr: "RemoteTrigger list 2026-10-13", opened_in_session: true}
  - {claim_id: C7, source_path: "tools/pr_merge_sa.py (W1–W3 × M0–M3, BOT_REVIEW_REPOS = platform, OWNER_WORT_REPOS Liste L)", commit_or_pr: "origin/main 2026-10-13; platform#3804 K7", opened_in_session: true}
  - {claim_id: C8, source_path: "docs/konzepte/KONZ-platform-028 (Fach-Reviewer, idea, Kill-Gate review_by 2026-10-23) und KONZ-platform-051 (ux-review, idea)", commit_or_pr: "origin/main 2026-10-13", opened_in_session: true}
  - {claim_id: C9, source_path: "meiki-lra/meiki-hub PRs #607, #588, #536: mergedBy Owner, reviews=0; main ohne Schutz", commit_or_pr: "gh pr view 2026-10-13", opened_in_session: true}
  - {claim_id: C10, source_path: "~/.claude/policies/ssot-vor-individualloesung.md, llm-routing.md, adr-threshold.md, autonomy-gates.md", commit_or_pr: "Stand 2026-10-13", opened_in_session: true}
  - {claim_id: C11, source_path: "Lange et al., The Agentic Scientist, arXiv:2610.18933 + pub.sakana.ai/agentic-scientist (Evidence-Map, Audit auf unbelegte Zahlen und Overclaiming; Reward Hacking im ALIFE-Fall erst durch einen Menschen gefunden)", commit_or_pr: "gelesen 2026-10-16, Lotse-Analyse", opened_in_session: true}
  - {claim_id: C12, source_path: "grep evidence_manifest|claim_id in tools/ und .github/: 0 Treffer — kein Werkzeug prüft das Manifest", commit_or_pr: "origin/main cebacd59, 2026-10-16", opened_in_session: true}
created: 2026-10-13
---

# KONZ-platform-070 — Review-System org-weit

> **Auftrag (Owner-Wort 2026-10-13, Kapitäns-Sitzung):** „ich möchte dass du den review signifikant
> verbesserst; alle repos sollen perfekt optimiert werden können. SSoT, database/file driven und kein
> hardcoded sind pflicht (wann immer sinnvoll!!) Fokus: zukünftiges besseres LLM setzt verzugslos auf
> aktuellen stand auf, continous improvement und pred. maintenance, ootb, adv. diabolus"
>
> **Tier T3, keine Umsetzung in diesem Dokument.** Es beschreibt Ist, Zielzustand, Kriterien und den
> Stufenplan. Stufe 1 (Pilot auf drei Repos) braucht kein ADR; Stufe 2 (org-weit) braucht einen.

## 1. Ist — gemessen 2026-10-13

### 1.1 Schutz und Review-Deckung (C1, 61 nicht-archivierte Repos: 55 achimdehnert, 6 iilgmbh)

| Merkmal | Zahl |
|---|---|
| `main` ohne jeden Branch-Schutz | 56 / 61 |
| `main` mit Pflicht-Checks | 5 (platform 1, risk-hub 4, writing-hub 2, decks-hub 1, iil-adrfw 1) |
| `main` mit Approval-Pflicht | 0 / 61 |
| Prod-Repos (`deployed`) ohne Schutz | 11 / 14 |
| CODEOWNERS vorhanden | 61 / 61 — ohne Approval-Pflicht wirkungslos |
| Bot-Review aktiv | 2 (platform, risk-hub) |
| Context-Reviewer aktiv | 1 (platform) |
| meiki-lra, ttz-lif in `registry/canonical.yaml` | Namen vorhanden (meiki-hub, frist-hub, post-hub, schreib-hub, buerger-hub; ttz-hub), aber ohne `rich`-Daten — vor WP0 fehlte `github` bei 6/6 und registry-weit bei 34/69 (38/69 ohne `rich`-Block), nach WP0 (`tools/registry_rich_sync.py`, #3903) bei 0/6 bzw. 1/69; `lifecycle` bleibt bei 6/6 offen, `deployed` ist bei 4/6 belegt (`false`, ports.yaml blockiert) und bei meiki-hub, ttz-hub nicht belegbar |

### 1.2 Merges ohne Review, 30 Tage bis 2026-10-13 (C2)

| Org | gemergt | ohne Review | Anteil | davon Dependabot |
|---|---|---|---|---|
| achimdehnert | 1151 | 857 | 74 % | 19 |
| iilgmbh | 268 | 262 | 98 % | 15 |
| meiki-lra | 277 | 276 | 99,6 % | 4 |
| ttz-lif | 15 | 15 | 100 % | 0 |

Der Anteil ist kein Bot-Effekt. In 30 Tagen wurden rund 1400 PRs ohne Review-Urteil gemergt; die
Sitzungen mergen ihre eigenen PRs (C9 zeigt das Muster an meiki-hub).

### 1.3 Vorhandene Bausteine (C3–C8) — und ihr Defekt

| Baustein | Was er kann | Defekt gegen den Auftrag |
|---|---|---|
| `bot-review.yml` / shared-ci `_bot-review.yml` | approvt Owner-PRs mit grünen Checks | urteilt nicht inhaltlich; TABU-Pfade als Konstante im Code |
| `agents/context_reviewer.py` | Diff → betroffene ADRs/Prinzipien per Muster | Muster hartkodiert, kein LLM, nur platform |
| `.windsurf/rules/reviewer.md` | 10 Prinzipien, BLOCK-Liste | Prosa, `trigger: manual`, nicht maschinenlesbar, nicht gemessen |
| Routine `deep-review` | adversarial, 4 Linsen, Fable-Tier | nur platform, nur Label `needs-deep-review`, Befunde ohne Ledger |
| Routine `pr-review-prep` | TL;DR + Review-Fragen je PR | nur platform; Ausgabe liest niemand automatisch (vgl. #3887) |
| `pr_merge_sa.py` | Wirkung × Mandat (W/M) | kennt Review nur als „Approval ja/nein“, nicht als Befundqualität |
| KONZ-028, KONZ-051 | Fach-/UX-Reviewer | `idea`, je ein Pilot, keine gemeinsame Regel- oder Befundbasis |

**Kern des Defekts:** Sechs Review-Bausteine, keine gemeinsame Quelle für Regeln, keine gemeinsame
Ablage für Befunde, keine Messung, welche Regel trifft. Ein besseres Modell könnte heute nichts
„verzugslos übernehmen“ — der Review-Stand steht in Prosa, Konstanten und Prompts.

## 2. Zielzustand (ein Satz)

**Jedes Repo der vier Orgs bekommt ohne eigene Konfiguration denselben Review: mechanische Regeln aus
einer Datenquelle, einen Advocatus-Diaboli-Kommentar je riskantem PR, und jeder Befund landet in einem
Ledger, aus dem Regeln kalibriert, Wartung vorhergesagt und ein künftiges Modell eingelernt werden.**

## 3. Bauplan — sieben Teile

### Z1 Review-Regeln als Daten (SSoT)

`registry/review-regeln.yaml` ist die einzige Quelle. Je Regel: `id`, `klasse` (BLOCK · WARN · HINT),
`geltung` (Pfad-Globs, Repo-Tags aus der Registry), `detektor` (Regex · AST-Skript · LLM-Frage),
`begruendung` (ADR/Policy-Link), `seit`, `praezision` (gemessen, s. Z3). Daraus **generiert**:
`reviewer.md` (Prosa für Menschen), die TABU-Liste des Bots, die Muster des Context-Reviewers, der
Prompt-Block des Advocatus. Repo-Abweichungen stehen in `canonical.yaml` unter `review_profile`
(z. B. `odoo`, `library`, `static`), nie im Workflow. **Kein Regel-Literal außerhalb dieser Datei.**

### Z2 Ein Review-Workflow, überall (OOTB)

shared-ci `_review.yml`, aufgerufen aus `_ci-python.yml`/`_ci-odoo.yml`/`_ci-pypi.yml` — wer heute CI
nutzt (44 / 61), bekommt Review ohne eigene Zeile. Drei Stufen je PR:

1. **Mechanik** — Regel-Engine (Z1) + bestehende Lints; Ergebnis als Check mit Locator.
2. **Advocatus Diaboli** — LLM-Review mit festem Vertrag: „Was bricht, wen trifft es, wo steht die
   Zahl/Hausdatum/Secret hart im Code, welcher ADR/Policy widerspricht.“ Ausgabe ist strukturiert
   (`regel_id`, `klasse`, `locator`, `konfidenz`, `begruendung`), zusätzlich ein lesbarer Kommentar.
   Advisory, nie Approve/Request-Changes (Charta Art. 3). Läuft nur, wenn der Risiko-Klassifikator
   anschlägt (Pfade mit `deploy*.yml`, Migrationen, `permissions:`, Secrets, > N Zeilen, W3-Wirkung);
   Dependabot-Patches laufen nicht durch das LLM.
3. **Bot-Approval** — nur wenn Stufe 1 grün und kein nicht quittierter BLOCK-Kandidat aus Stufe 2.
   Quittung = Sitzung oder Owner markiert den Befund als `widerlegt` mit Grund (Ledger-Eintrag).

Modell-Routing (llm-routing.md): Stufe 1 ohne LLM; Triage/Zusammenfassung Groq/Cerebras; der
Advocatus Opus-Tier; Fable nur für `needs-deep-review` (bestehende Routine wird zum Konsumenten).

### Z3 Befund-Ledger (Lernschleife)

Jeder Befund ist eine Zeile: `repo, pr, head_sha, regel_id, klasse, locator, konfidenz, modell,
ausgang` mit `ausgang ∈ {bestätigt, widerlegt, offen, gemergt-ohne-Quittung}`. Ablage: Tabelle in
dev-hub (Platform Agents, DB mit CRUD) — Export als JSONL nach platform für die Melder. Daraus:

- **Präzision je Regel** (rollierend 4 Wochen). Regel < 50 % ⇒ automatisch HINT; Regel ≥ 90 % über
  8 Wochen ⇒ Kandidat für Pflicht-Check. Die Herabstufung ist der Melder-Befund, nicht der PR.
- **Regel-Kandidaten**: ein Advocatus-Befund ohne `regel_id`, der 3× bestätigt wird, erzeugt einen
  Issue „Regel aufnehmen“ mit den drei Locators.
- **Vorausschauende Wartung**: je Repo monatlich eine Zeile `Wartungsprognose` aus Ledger +
  Dependabot-Alter + Deploy-Historie + Check-Rotquote (Hotspot-Dateien, Abhängigkeiten > 2 Majors
  zurück, Checks mit steigender Flake-Rate). Ausgabe als Issue-Kommentar, Leser = Session-Start (#3887).

### Z4 Branch-Schutz als Deklaration

`review_profile` in der Registry legt fest, was `main` verlangen muss (Prod-Repo: CI-Gate + Review-Check
+ 1 Approval, Bot zählt; Bibliothek: CI-Gate; statisch: nichts). Ein Melder vergleicht Ist (API) mit
Soll und meldet Drift. **Anwenden** bleibt Owner-Zug (Security-Config-Gate, autonomy-gates): der Melder
liefert den fertigen Befehl je Repo. Ziel: 14 / 14 Prod-Repos deckungsgleich.

### Z5 Übergabefähig für ein stärkeres Modell

Der komplette Review-Stand liegt in drei Dateien/Tabellen: Regeln (Z1), Profile (Registry), Ledger (Z3).
Ein neues Modell liest sie und läuft einen **Rekalibrierungslauf**: alle Regeln gegen die letzten 500
Ledger-Zeilen, Vorschlag je Regel (behalten · schärfen · streichen) als PR. Kein Wissen nur in Prompts
oder Köpfen; jeder Prompt-Baustein wird aus Z1 generiert und trägt `source_commit`.

### Z6 Merge-Mandat kennt Befundqualität

`pr_merge_sa.py` liest das Ledger: ein offener BLOCK-Kandidat hebt die Wirkung um eine Stufe (W1→W2),
ein quittierter senkt sie nicht unter die Pfad-Regel. Damit wird „Approval“ vom Klick zur geprüften
Aussage, ohne die bestehenden Gates (Prod = Owner) anzutasten.

### Z7 Beleg-Audit: keine Zahl ohne Quelle

> **Owner-Wort 2026-10-16, Kapitäns-Sitzung:** „V1 go“ — auf den Vorschlag „Beleg-Audit in
> Review-System“ aus der Lotse-Analyse zu The Agentic Scientist (C11).

Konzepte tragen schon ein `evidence_manifest` mit Marken `C1…Cn`, aber kein Werkzeug prüft es (C12).
Z7 macht „Evidenz vor Behauptung“ zur Regel in Z1, in zwei Stufen von Z2:

1. **Mechanik** (Detektor-Skript, ohne LLM) — in Dateien mit `evidence_manifest`: jede Marke `(Cn)` im
   Text hat einen Manifest-Eintrag, jeder Eintrag wird mindestens einmal zitiert, jeder Eintrag hat
   `source_path` und `commit_or_pr`. Verwaiste Marke ⇒ WARN, unbenutzter Eintrag ⇒ HINT.
2. **Advocatus-Linse** — feste Frage im Vertrag aus Z2: „Welche Zahl oder Aussage in Diff oder PR-Text
   hat keinen Beleg, und welche geht über ihren Beleg hinaus?“ Befunde laufen unter einer eigenen
   `regel_id` ins Ledger (Z3).

Beide starten als HINT; die Aufstufung entscheidet die gemessene Präzision (Z3), nicht dieses Konzept.
Die Positivkontrolle läuft am Realfall: ein Konzept aus `main`, dem eine Marke entzogen wird.

## 4. Prüfbare Kriterien

| # | Kriterium | Messung |
|---|---|---|
| K1 | 0 Review-Regeln außerhalb `review-regeln.yaml`; `reviewer.md`, TABU, Context-Muster generiert | Drift-Test im CI, Hash-Vergleich |
| K2 | OOTB: Sandbox-Repo (iilsandbox) aus Template erhält Review ohne eigene Zeile | Nachweis-PR mit Advocatus-Kommentar |
| K3 | 14 / 14 Prod-Repos: Branch-Schutz = deklariertes Profil | Melder Z4 grün 4 Wochen |
| K4 | Präzision je Regel nach 4 Wochen Pilot gemessen; Regeln < 50 % herabgestuft | Ledger-Auswertung, Kommentar im Mandats-Issue |
| K5 | Advocatus-Kommentar ≤ 15 min nach Push an jedem Risiko-PR der Pilot-Repos | Ledger-Zeitstempel vs. PR-Push |
| K6 | Ledger wird gelesen: Session-Start-Phase (#3887) zeigt neue Befunde; Wartungsprognose 1× monatlich je Pilot-Repo | Runner-Zeile, Issue-Kommentar |
| K7 | Rekalibrierungslauf einmal durchgeführt (Modellwechsel-Drill) mit PR „Regeln behalten/schärfen/streichen“ | PR-Link |
| K8 | Merges ohne jedes Review-Urteil in den Pilot-Repos: 0 (Bot zählt, Dependabot-Patch ausgenommen) | Search-Abfrage wie C2 |
| K9 | Beleg-Audit (Z7) läuft in den Pilot-Repos; Positivkontrolle am Realfall erkannt; Präzision nach 4 Wochen gemessen | Check-Lauf mit Locator, Ledger-Auswertung |

## 5. Stufenplan

| Stufe | Inhalt | Repos | Gate |
|---|---|---|---|
| 0 | KONZ akzeptiert; Mandats-Issue mit K1–K8 | platform | Owner-Wort |
| 1 | Z1 + Z2 (Stufe 1–2) + Z3 (JSONL) + Z4 (Melder) als Pilot | platform, risk-hub, writing-hub (Liste L, #3804) | kein ADR; Kill-Gate s. o. |
| 2 | ADR „Review-System org-weit“; Z2 Default in shared-ci; Z3 als DB; Z6 | alle achimdehnert + iilgmbh | ADR accepted, Kill-Gate bestanden |
| 3 | meiki-lra, ttz-lif | nur mit eigenem Owner-Wort (Autonomie-Ausschluss 2026-10-06) | Owner-Wort je Org |

**Vor Stufe 1 zwei Vorarbeiten:** (a) meiki-lra und ttz-lif in `canonical.yaml` aufnehmen — ohne
Registry-Eintrag gibt es kein `review_profile`; (b) KONZ-028 am 2026-10-23 auswerten — besteht es,
wird der Fach-Reviewer eine Linse des Advocatus, fällt es, entfällt die Persona-Schicht.

## 6. Nicht im Umfang

- Menschliche Entscheidung für Prod/Publish ersetzen — die W/M-Gates bleiben (autonomy-gates).
- Code automatisch reparieren; der Advocatus schlägt vor, die Sitzung setzt um.
- ADR-Review (adr-dual-review.yml bleibt eigener Pfad).
- Rollout auf meiki-lra/ttz-lif ohne Owner-Wort.

## 7. Advocatus Diaboli gegen dieses Konzept

| Einwand | Antwort / offene Stelle |
|---|---|
| „Noch ein Bot-Kommentar, den niemand liest“ (vgl. #1472, #1261) | Z3 macht Lesen messbar: `gemergt-ohne-Quittung` ist ein Ledger-Ausgang und fließt in K8. Bleibt er hoch, ist das Kill-Kriterium (b). |
| LLM-Review kostet je PR | Risiko-Klassifikator vor dem LLM; Dependabot-Patches ohne LLM; Routing nach Tier. Kosten je PR sind eine Ledger-Spalte, Budget-Gate (Spend) greift. |
| Regel-YAML wird zur zweiten Prosa | Jede Regel ohne `detektor` oder ohne Messung nach 4 Wochen ist ein Melder-Befund; Prosa ohne Prüfbarkeit ist nicht zulässig. |
| Branch-Schutz org-weit = 56 Owner-Klicks | Z4 liefert je Repo den fertigen Befehl; die Reihenfolge Prod-Repos zuerst (11) macht den Rest optional. |
| Bot-Token in 4 Orgs = Reichweite | Stufe 2 ist genau deshalb ADR-pflichtig; bis dahin bleibt der Bot in Liste L. |

## 8. Offene Entscheidungen (Owner)

- O1 Ledger-Heimat: dev-hub-DB (CRUD, Platform-Agents-Policy) **oder** JSONL in platform (einfacher, aber platform ist öffentlich — Ledger enthält Locators, keine Secrets, aber Pfade). Empfehlung: dev-hub-DB, Export nach platform nur aggregiert.
- O2 Pilot-Repos wie vorgeschlagen (Liste L) **oder** ein Business-Hub dazu (cad-hub, writing-hub ist bereits drin).
- O3 Advocatus-Modell im Pilot: Opus (Standard) **oder** Fable für alle Pilot-PRs (teurer, bessere Kill-Gate-Messung).
