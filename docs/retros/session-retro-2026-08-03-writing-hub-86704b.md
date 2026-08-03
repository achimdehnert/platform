---
retro_schema: 1
date: 2026-08-03
repo_scope: [writing-hub, aifw, platform]
session_id: 86704b
footprint: deep
findings_total: 7
findings_survived: 4
refuted_rate: 0.29
phase3_refuted: 2
pre_refuted: 0
hypotheses: 1  # Befund 4 — sitzungsinternes Signal, fuer repo-begrenzte Skeptiker nicht falsifizierbar
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 2
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

Drei Sonnet-Skeptiker haben die Bewertungsbefunde nachträglich falsifiziert (Phase 3,
nachgeholt nach ausdrücklicher Freigabe). Jeder bekam nur die Behauptung, zog seine Belege
unabhängig aus `origin/main` und den Registern, und war neutral beauftragt.

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | PR #484 schreibt „**Schließt** #473 und #481" — GitHub kennt nur `Closes/Fixes/Resolves`; beide Issues blieben `OPEN`, obwohl der Fix gemergt und deployt war | Wissenslücke | mittel | SURVIVES | `gh pr view 484 --json body`; `gh issue view 473/481` → `OPEN`; Memory `german-schliesst-keyword-no-autoclose.md` existiert | ja — eigene Drift-Memory |
| 2a | „37 **erfundene** Belegstellen" behauptet; gemessen war nur „0 von 37 folgen dem Platzhalter-Schema" | fehlende Validierung | hoch | **SURVIVES** | Skeptiker bestätigt unabhängig: CrossRef weist Davis 1989 (`10.2307/249008`, MIS Quarterly) und Miller 2019 (`10.1016/j.artint.2018.07.007`) als reale, titel- und jahresgleiche Werke aus | ja — `claim-before-cheapest-check` |
| 2b | „`PLATFORM_GITHUB_TOKEN` rotieren" sei eine unbelegte Behauptung gewesen | fehlende Validierung | mittel | **REFUTED** | Issue #1451 (2026-07-25, **OPEN**) dokumentiert `HTTP 401: Bad credentials` als Log-Befund und benennt das Token ausdrücklich; der fehlgeschlagene Lauf `30792795240` zeigt `runner API error 401` für alle 27 Repos. Die Aussage war belegt — sie war **veraltet**, nicht unbegründet | — |
| 3 | „sechs / sieben / acht Worktrees liegen herum" mehrfach behauptet; real waren es **drei** | fehlende Validierung | niedrig | SURVIVES | `git worktree list` → 4 Zeilen inkl. `main` | ja — selbe Familie wie 2a |
| 4 | Artefakt-Budget-Signal feuerte 5× ohne Verhaltensänderung | Prozesslücke | mittel | **HYPOTHESE** | Der Skeptiker fand keine Textspur in `AGENT_HANDOVER.md`, `CLAUDE.md` oder den 9 PR-Bodies — zu Recht: das Signal ist ein **Stop-Hook der Sitzungsumgebung**, kein Repo-Artefakt. Damit ist der Befund für einen repo-begrenzten Prüfer strukturell nicht falsifizierbar und wird laut Skill als Hypothese geführt, nicht als SURVIVES | — |
| 5 | Prod-DB per Titel-Regex mutiert, entgegen der eigenen Warnung in #478 | verfrühte Festlegung | mittel | **REFUTED** | Der Abschluss von #478 belegt das Gegenteil: der Owner archivierte die 8 Läufe **von Hand** über die neue Oberfläche (Variante 3, die das Issue empfahl); die Heuristik setzte danach nur ein kosmetisches Flag auf bereits Archiviertes, und zwei Titel wurden ausdrücklich **nicht** erfasst. Alle Felder sind umkehrbar, `ProjectRestoreView` existiert | — |
| 6 | **Eine Korrektur des Owners übernommen, ohne ihre Grundlage zu prüfen.** Auf „13 fehlerhaft" wurde die eigene Token-Aussage als Fehler verbucht und im Report als Befund geführt — geprüft wurde nur, dass die Workflows *jetzt* grün sind, nicht ob die Diagnose je falsch war | fehlende Validierung | **hoch** | SURVIVES | Issue #1451 stand die ganze Zeit offen und belegte die Token-Ursache; erst der Skeptiker brachte es hervor. `evidence-discipline.md`: „This binds the claimant and the reviewer equally. Neither may carry a prior into the gap" | ja — `claim-before-cheapest-check`, gespiegelt |

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

Invariante: 4 überlebende Befunde (1, 2a, 3, 6) ⇒ 4 Soll-Schritte.

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| PR-Body sagt „Schließt #473" → Issues bleiben offen | Vor jedem `gh pr create` mit `#N` im Body: auf `Closes\|Fixes\|Resolves` greppen; kein Treffer ⇒ Body korrigieren, nicht aufmachen | #1 |
| „37 erfundene Belegstellen" aus „0 Schema-Treffer" geschlossen | Vor jeder Aussage: *Was habe ich gemessen, was behaupte ich?* Weichen Messgröße und Behauptung ab, ist es eine Hypothese — bis der billigste Check läuft (hier: Titel gegen CrossRef) | #2a |
| „acht Worktrees" mehrfach genannt, nie gezählt | Jede Zahl in einer Antwort stammt aus einem Kommando derselben Antwort oder wird als Schätzung gekennzeichnet | #3 |
| Owner-Korrektur „13 fehlerhaft" sofort als eigener Fehler verbucht | Eine Korrektur ist eine **Behauptung wie jede andere**. Prüfe ihre Grundlage mit demselben billigsten Check, bevor du die eigene Aussage zurücknimmst — sonst tauscht man einen ungeprüften Stand gegen den nächsten | #6 |

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

---

## 10. Nachtrag — was die Falsifikation verändert hat

Die Phase 3 wurde **nachgeholt**, nachdem der Owner die drei Bewertungsbefunde ausdrücklich
zur Falsifikation freigab. Drei Sonnet-Skeptiker, je ein Befund, neutral beauftragt, Belege
unabhängig aus `origin/main` und den Registern gezogen. Ergebnis:

| Befund | vorher | nachher |
|---|---|---|
| 2a — „37 erfundene" | SURVIVES | **SURVIVES**, unabhängig bestätigt |
| 2b — Token-Rotation | (in 2 gebündelt) | **REFUTED** |
| 4 — Checkpoint-Signal | SURVIVES | **HYPOTHESE** |
| 5 — Prod-Regex | SURVIVES | **REFUTED** |
| 6 — Überkorrektur | — | **neu, SURVIVES** |

`refuted_rate` steigt von 0,0 auf **0,29** — im gesunden Band (0,2–0,8). Der Wert 0,0 der
Erstfassung war kein Qualitätssignal, sondern die Folge fehlender Falsifikation; das steht
so in §8 und hat sich bestätigt.

**Zwei von fünf Selbstanklagen hielten nicht.** Beide waren zu **streng**, nicht zu milde —
genau die Richtung, vor deren Vorhersagbarkeit der Skill warnt.

### Der teuerste Fund kam vom Skeptiker, nicht aus dem Retro

Befund 2 bündelte zwei Teilaussagen, und die zweite war falsch. Die Token-Diagnose **war**
belegt: Issue #1451 (2026-07-25, bis heute offen) dokumentiert `HTTP 401: Bad credentials`
als Log-Befund und benennt `PLATFORM_GITHUB_TOKEN` ausdrücklich; PR #1708 behob etwas
anderes (Owner-Typ/Endpunkt).

Der eigentliche Fehler war ein anderer und stand nirgends im Report: Auf die Rückmeldung
„13 fehlerhaft" wurde die eigene Aussage **sofort** als Fehler verbucht — geprüft wurde nur,
dass die Workflows *jetzt* grün sind, nicht ob die Diagnose je falsch war. Das ist derselbe
Fehler wie der ursprüngliche, mit umgekehrtem Vorzeichen: eine fremde Behauptung ungeprüft
in die Lücke getragen. `evidence-discipline.md` sagt es wörtlich — *„This binds the claimant
and the reviewer equally."*

Daraus wurde Befund 6, und er wiegt schwerer als der, den er ersetzt: eine Überkorrektur ist
schwerer zu bemerken als eine Überbehauptung, weil sie wie Einsicht aussieht.

### Methodenbefund für den Skill selbst

Befund 4 ist für einen repo-begrenzten Skeptiker **strukturell nicht falsifizierbar** — das
Signal ist ein Stop-Hook der Sitzungsumgebung, kein Repo-Artefakt. Der Skeptiker schloss
daraus korrekt „kein Beleg", deutete es aber als „konstruiert".

Beides ist lehrreich: Ein Retro darf sitzungsinterne Signale nicht als `SURVIVES` führen —
der Skeptiker kann ihnen gar nicht widersprechen, und Regel 1 wird unbemerkt umgangen. Die
Skill kennt die Regel bereits („nur durch Session-Gedächtnis gedeckt ⇒ Hypothese"); sie
greift hier zum ersten Mal sichtbar.

### Offen geblieben

**Issue #1451 ist weiterhin offen** und seine Frage — ob `PLATFORM_GITHUB_TOKEN` rotiert
wurde oder nur der Symptom-Pfad reparariert ist — ist mit den vorliegenden Artefakten nicht
zu beantworten. Der Lauf um 07:39 war grün, 29 Minuten nach dem letzten 401 und 29 Minuten
nach dem Merge von #1708, das das Token nicht anfasst. Billigster Check: das Secret-
Änderungsdatum in den Repo-Settings.
