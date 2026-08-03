---
retro_schema: 1
date: 2026-08-03
repo_scope: [writing-hub, aifw, platform]
session_id: 86704b
footprint: deep
findings_total: 5
findings_survived: 5
refuted_rate: 0.0
phase3_refuted: 0
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [claim-before-cheapest-check-attribut-und-dokumentzustand, german-schliesst-keyword-no-autoclose]
recurring_findings: [claim-before-cheapest-check, german-schliesst-keyword-no-autoclose]
footprint_reduction_reason: "keine Reduktion — Bedingung (b) verletzt: zwei DB-Migrationen (0042_bookproject_archived_at, 0043_bookproject_is_experiment)"
---

# Session-Retro 2026-08-03 — writing-hub (86704b)

## 1. Executive Summary

* **Der Auftrag wurde erfüllt und weit überschritten**: aus `/session-start` wurden 9 gemergte
  PRs, 2 Konzepte, 3 geschlossene Issues — jedes Artefakt auf eine ausdrückliche Anweisung
  zurückführbar, aber der Scope-Checkpoint feuerte 5× ohne dass sich das Verhalten änderte.
* **Die folgenschwerste Fehlleistung war eine Überbehauptung**, keine Fehlimplementierung:
  „37 erfundene Belegstellen" war nie gemessen und rahmte zwei Konzepte falsch, bis ein
  **externer Reviewer** es fand.
* **Zwei Zustandsbehauptungen wurden von anderen widerlegt, nicht von der eigenen Prüfung** —
  eine vom externen Review, eine vom Owner. Beide hatten dieselbe Signatur: ein Dokument als
  Zustandsbeschreibung genommen, statt die Sache anzusehen.
* **Handwerklich war die Session solide**: kein dritter Schreibpfad, Mutationstests gegen
  Schein-Grün, serielles Mergen fand einen `ImportError`, den keine Einzel-PR-CI fangen konnte.
* **Zwei Issues blieben offen, weil der PR-Body „Schließt" statt „Closes" sagt** — ein
  dokumentierter Drift, im eigenen Memory, heute erneut eingetreten.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | PR #484 schreibt „**Schließt** #473 und #481" — GitHub kennt nur `Closes/Fixes/Resolves`; beide Issues blieben `OPEN`, obwohl der Fix gemergt und deployt ist | Wissenslücke | mittel | SURVIVES | `gh pr view 484 --json body` → „Schließt **#473**"; `gh issue view 473/481` → `OPEN`; Memory `german-schliesst-keyword-no-autoclose.md` existiert | ja — eigene Drift-Memory |
| 2 | Zwei Zustandsbehauptungen ohne den billigsten Check: (a) „37 **erfundene** Belegstellen" — gemessen war nur „0 folgen dem Platzhalter-Schema"; (b) „`PLATFORM_GITHUB_TOKEN` rotieren" — aus dem Issue-Text vom Session-Start, während beide Melder seit 07:39 grün liefen | fehlende Validierung | hoch | SURVIVES | (a) CrossRef: Davis 1989 `10.2307/249008` + Miller 2019 `10.1016/j.artint.2018.07.007` existieren; (b) `gh run list --workflow "Runner Health Check"` → `2026-08-03T07:39 success` | ja — `claim-before-cheapest-check` ×37 |
| 3 | „sechs / sieben / acht Worktrees liegen herum" über mehrere Turns behauptet; real waren es **drei** | fehlende Validierung | niedrig | SURVIVES | `git worktree list` → 4 Zeilen inkl. `main`; die gemergten waren längst abgeräumt | ja — selbe Familie wie #2 |
| 4 | Der Artefakt-Budget-Checkpoint feuerte **5×** (Schwelle 4). Jedes Mal wurde der Scope gespiegelt und weitergebaut; das Signal änderte das Verhalten nie | Prozesslücke | mittel | SURVIVES | 5 Stop-Hook-Meldungen im Transkript; PR-Zahl stieg 5 → 7 → 8 → 9 nach dem ersten Checkpoint | ja — `scope-checkpoint-not-durably-recorded` ×10 (hier abgeschwächt: **wurde** durabel im Handover festgehalten) |
| 5 | Prod-DB-Mutation per Titel-Regex **ohne Dry-Run** — in demselben Repo, in dem Issue #478 kurz zuvor genau davor warnte („ein Backfill müsste am Titel raten") | verfrühte Festlegung | mittel | SURVIVES | Der Lauf setzte `is_experiment`/`is_active`/`archived_at` direkt per `save()`; erst danach wurde der Archiv-Bestand angesehen. Schaden gering (1 Treffer), weil der Owner bereits von Hand archiviert hatte | nein |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **4** | Vergleichslauf gefahren, Zahl geliefert, alle 5 Optimierungspunkte gebaut, Stil erstellt, 2 Konzepte extern reviewt. Abzug für #2: die Kernzahl war falsch |
| architektur_design | **4** | Kein dritter Schreibpfad (`chapter_batch` extrahiert statt kopiert), Gate-Muster wiederverwendet, Register-Auflösung sauber gekapselt. Abzug: die Konzept-Erstfassungen waren schwach genug, dass 24/24 externe Empfehlungen gültig waren |
| code_konventionstreue | **4** | Worktrees statt Haupt-Tree, explizites `git add`, Mutationstests, `make test` durchgängig. Abzug für #1 (deutsches Keyword) |
| risiko_debt | **3** | 2 DB-Migrationen, mehrere Prod-Schreibvorgänge, 16 offene Issues; beide Konzepte ausdrücklich `überarbeitungsbedürftig`; #473/#481 offen trotz Fix |
| prozess_effizienz | **3** | Serielles Mergen fand einen echten Fehler — aber 2 CI-Infrastrukturausfälle, 1 Merge-Konflikt und ein `git checkout`, das Arbeit vernichtete, kosteten Zeit. 5 Checkpoints ohne Wirkung |
| entscheidungsqualitaet | **3** | Die falsche Kernzahl (#2a) rahmte zwei Konzepte, ein Issue und mehrere Antworten falsch, bis ein Fremder sie fand. Gegengewicht: die Entscheidung, den aifw-Rückbau zu **stoppen** statt blind zu fahren, war belegt richtig |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| PR-Body sagt „Schließt #473" → Issues bleiben offen | Vor jedem `gh pr create` mit Issue-Bezug: `grep -iE 'closes\|fixes\|resolves' <body>` — kein Treffer bei vorhandenem `#N` ⇒ Body korrigieren, nicht mergen | #1 |
| „37 erfundene Belegstellen" aus „0 Schema-Treffer" geschlossen | Vor jeder Aussage prüfen: *Was habe ich gemessen, was behaupte ich?* Weichen Messgröße und Behauptung ab, ist die Behauptung eine Hypothese — bis der billigste Check läuft (hier: Titel gegen CrossRef) | #2 |
| „acht Worktrees" mehrfach genannt, nie gezählt | Jede Zahl in einer Antwort stammt aus einem Kommando in derselben Antwort oder wird als Schätzung gekennzeichnet | #3 |
| 5 Checkpoints gespiegelt, Verhalten unverändert | Ab dem **zweiten** Checkpoint keine Spiegelung mehr, sondern eine Entscheidungsfrage mit Abbruch-Option als Default — der Mensch wählt Weiterbauen aktiv, statt es durch Schweigen zu bestätigen | #4 |
| Prod-Regex-Mutation direkt ausgeführt | Jede mutierende Prod-Abfrage läuft **zweimal**: erst als reine Auswahl mit Ausgabe der Treffer, dann — nach Sichtung — als Schreibvorgang. Bei Heuristiken ist das keine Kür | #5 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (Stand 2026-08-03):

| Slug | Zähler | Status |
|---|---|---|
| `claim-before-cheapest-check` | **×37** | 🚨 GATE-PFLICHT — Befund #2 und #3 sind Vorkommen 38/39 |
| `german-schliesst-keyword-no-autoclose` | ×0 im Retro-Längsschnitt, **×1 als Drift-Memory** | 🚨 neu aufnehmen — Memory existiert, Retro-Slug fehlte bisher |
| `scope-checkpoint-not-durably-recorded` | ×10 | Befund #4 ist **kein** sauberes Vorkommen: der Scope **wurde** durabel im `AGENT_HANDOVER.md` festgehalten (7 Treffer). Das Problem ist nicht die Aufzeichnung, sondern die Wirkungslosigkeit |

**Der eigentliche Befund des Längsschnitts — nachgemessen, nicht vermutet:**
`claim-before-cheapest-check` steht mit diesem Report bei **×38** und ist seit Langem
gate-pflichtig. Es **gibt** einen Mechanismus, und er **ist aktiv**:
`tools/claude-hooks/evidence_claim_scanner.py`, verdrahtet in `~/.claude/settings.json:116`.

Er hat beide Verstöße dieser Session trotzdem durchgelassen — und der Blick in seine
`CLAIM_PATTERNS` erklärt warum. Abgedeckt sind:

| Muster | Beispiel |
|---|---|
| Testergebnis | `1790 passed`, `12 failed` |
| Deploy/Publish | `deployt`, `live auf PyPI` |
| Verhältniszahl | `5/6 grün` |
| PR/Issue-Existenz | „PR #484 ist gemergt" |

**Beide heutigen Verstöße fallen in keine davon:**

* „37 **erfundene** Belegstellen" ist eine *Wesensaussage über gezählte Dinge* — die Zahl 37
  stimmt, das Attribut „erfunden" war nie geprüft. Kein Muster greift auf ein Adjektiv.
* „`PLATFORM_GITHUB_TOKEN` rotieren" ist eine *aus einem Dokument abgeschriebene
  Zustandsaussage* — der Issue-Text vom Session-Start wurde als Gegenwart gelesen.

Damit ist ×38 kein Beleg für ein wirkungsloses Gate, sondern für eine **präzise
Abdeckungslücke**: der Scanner prüft Zahlen und Ereignisse, nicht **Attribute** und nicht
**Zustände aus Dokumenten**. Das ist die konkrete Erweiterung, die aus diesem Retro folgt —
und sie ist billiger und zielgenauer als „noch ein Memo".

### 5b. Autonomie-Kalibrierung

| KPI | Wert | Beleg |
|---|---|---|
| `over_ask` | **3** | Dreimal um ein „go" für #481/#482 gebeten (Doku-Artefakte unterhalb aller Gates), bis schließlich ohne Freigabe gehandelt wurde; ebenso bei `/session-ende` (2× gefragt) |
| `over_act` | **1** | Prod-DB-Mutation per Regex ohne Dry-Run (#5) — durch „10 go" gedeckt, aber die *Methode* war nicht Teil der Freigabe |

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

**memory_candidates**

```markdown
---
name: drift-messgroesse-ist-nicht-behauptung
description: "Gemessen wurde 'folgt nicht dem Schema', behauptet wurde 'erfunden' — zwei Konzepte trugen die falsche Zahl, bis ein externer Reviewer sie fand"
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-08-03-37-erfundene-belege
---
Vor jeder Aussage mit Zahl: **Was genau habe ich gemessen, und was behaupte ich?**
Weichen beide ab, ist die Behauptung eine Hypothese — auch wenn die Messung sie nahelegt.

Realfall 2026-08-03: 37 Belegstellen, 0 folgten dem Platzhalter-Schema. Daraus wurde
„37 erfundene Belegstellen". Nachprüfung gegen CrossRef: Davis 1989 (`10.2307/249008`)
und Miller 2019 (`10.1016/j.artint.2018.07.007`) existieren mit exakten Metadaten.
Richtig war „37 **nicht autorisierte**". Der Unterschied verschob die ganze Bau-Richtung —
von Fabrikation zu Fehlzuschreibung, die schwerer zu entlarven ist.

**How to apply:** Bei Zitaten ist der billigste Check der Titel gegen CrossRef/DataCite,
nicht die Formatprüfung. Siehe [[claim-before-cheapest-check]].
```

```markdown
---
name: feedback-pr-body-closes-nicht-schliesst
description: "PR-Bodies auf englisches Auto-Close-Keyword prüfen, bevor der PR aufgemacht wird — 'Schließt #N' ließ heute zwei Issues offen"
metadata:
  type: feedback
---
**Why:** GitHub schließt Issues nur bei `Closes/Fixes/Resolves`. Deutsche PR-Bodies
lassen sie offen zurück; der Fix ist live, das Issue sieht offen aus.

**How to apply:** Vor `gh pr create`: enthält der Body ein `#N` **ohne** eines der drei
englischen Keywords ⇒ Body korrigieren. Nach Merge-Serien gegenchecken.
Verstärkt [[german-schliesst-keyword-no-autoclose]] — die Memory existierte und wurde
trotzdem nicht angewandt.
```

**adr_candidates** — keine. Kein Befund berührt eine Architektur-Entscheidung im Sinne der
`adr-threshold`-Policy; #1 und #2 sind Prozess, #5 ist Vorgehen.

## 7. Maßnahmen (Action-Board)

### 🟢 Offen — dein Zug

1. 🟢 `#473` und `#481` von Hand schließen — Fix ist live, nur das Keyword fehlte — https://github.com/achimdehnert/writing-hub/issues/473
2. 🟢 Entscheiden, ob die 3 Bewertungsbefunde extern falsifiziert werden (~55k je, ~165k) — https://github.com/achimdehnert/platform/tree/main/docs/retros

### 🔵 Offen — ich kann sofort

3. 🔵 `german-schliesst-keyword-no-autoclose` als Retro-Slug in den Längsschnitt aufnehmen
4. 🔵 Pre-Send-Check für PR-Bodies (Keyword-Grep) in die Skill-Kette einhängen

### ✅ Erledigt

5. ✅ 9 PRs gemergt, deployt, Container gegen HEAD geprüft
6. ✅ 2 Konzepte extern zweitbegutachtet, 24/24 Empfehlungen eingearbeitet

## 8. Nicht verifiziert (Restlücken)

| Lücke | Billigster Check |
|---|---|
| **Regel-1-Bruch: Find lief inline, nicht über frische Subagenten.** Die Systemanweisung dieser Umgebung untersagt Subagenten ohne ausdrückliche Anforderung; der Skill sieht diesen Fall vor (Phase 0, „Wenn die Umgebung Subagenten untersagt"). Alle 5 Befunde stammen aus dem Kontext des Angeklagten | 3 Sonnet-Skeptiker auf die Bewertungsbefunde #2, #4, #5 — ~165k Tokens |
| **`refuted_rate: 0.0`** ist daher **kein Qualitätssignal**, sondern die Folge fehlender Falsifikation. Der Band-Vergleich (<0,2 ⇒ Falsifikation ist Theater) trifft hier formal zu und ist trotzdem nicht aussagekräftig | s. o. |
| Ob die 5 Scope-Checkpoints hätten stoppen sollen, ist ein Werturteil ohne Artefakt — jeder Schritt war einzeln freigegeben | Owner-Einschätzung |
| Der Prod-Lauf mit dem neuen Stil erzeugte 5.610 Wörter; ob die Prosa fachlich taugt, wurde nicht bewertet | Lektüre durch den Owner |

**Vierer-Abschluss**

* **getan:** 9 PRs gemergt und in Prod gegengeprüft · 2 Konzepte extern reviewt und korrigiert ·
  3 Issues geschlossen · 6 Memory-Einträge · Vergleichslauf gefahren und ausgewertet.
* **angenommen:** dass die 24 externen Empfehlungen alle gültig sind (nicht gegen-falsifiziert) ·
  dass die Konzept-Abgrenzung beim Bauen hält · dass der Retry das echte OTPM-Fenster trifft.
* **nicht verifizierbar:** die drei Bewertungsbefunde ohne Skeptiker · die fachliche Qualität
  der generierten Prosa · die Wirksamkeit von `claim-before-cheapest-check` als Gate.
* **offen geblieben:** #473/#481 formal offen · Gegenlauf `--quality fast` · dreiarmiges
  Experiment aus R1-REC-1 · beide Konzepte `überarbeitungsbedürftig`.

---

## 9. Nachtrag — die konkrete Gate-Erweiterung

Aus Abschnitt 5 folgt ein einzelner, umsetzbarer Vorschlag statt einer Ermahnung. Zwei neue
Muster für `evidence_claim_scanner.py`:

```python
# Wesensaussage über gezählte Dinge: die Zahl mag stimmen, das Attribut ist ungeprüft.
# Realfall 2026-08-03: „37 erfundene Belegstellen" — gemessen war „0 folgen dem Schema".
(re.compile(r"\b\d+\s+(?:erfundene?|fabrizierte?|ungültige?|kaputte?|fehlerhafte?)\b", re.I),
 "attribut-ueber-gezaehltem"),

# Zustandsaussage, die aus einem gelesenen Dokument stammt statt aus einer Messung.
# Realfall 2026-08-03: „Token rotieren" aus dem Issue-Text, während die Workflows grün liefen.
(re.compile(r"\b(?:laut|gemäß|steht in|dem Issue zufolge)\b[^.\n]{0,60}\b(?:ist|sind|bleibt|läuft)\b", re.I),
 "dokumentzustand-als-gegenwart"),
```

Das zweite Muster ist bewusst schwächer — es fängt nur die *benannte* Herleitung. Der teurere
Fall (Dokument gelesen, Herkunft verschwiegen) bleibt offen und wäre nur über eine
Prozessregel zu fassen: **ein Issue-Text ist eine Momentaufnahme seiner Erstellung, kein
Zustand.** Diese Regel gehört in `session-start`, wo Handover und Issues gelesen werden — und
nicht in einen Textscanner.
