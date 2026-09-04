---
retro_schema: 1
date: 2026-08-28
repo_scope: [writing-hub, weltenhub, platform]
session_id: effb03
footprint: full
footprint_reduction_reason: >-
  Rule-B-Trigger "Prod-Schritt" greift (Seed in die Prod-DB, ein POST nach
  weltenforger.com). Eine Stufe runter von deep auf full, weil alle drei
  Bedingungen erfuellt sind: (a) explizite Owner-Freigabe "11 go" auf einen
  Board-Punkt, der den WeltenHub-Schreibzugriff woertlich nannte; (b) keine
  DB-Migration, gleiche Bereitstellung, Datenschreibvorgaenge rueckrollbar;
  (c) Befund-Schaetzung <= 10.
findings_total: 12
findings_survived: 10
refuted_rate: 0.17
phase3_refuted: 2
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates:
  - dry-run-does-not-exercise-external-write
  - prod-repair-outside-approved-plan
recurring_findings:
  - deferred-item-no-tracking-issue
  - untested-command-handed-to-user
gates_caught:
  - claim-before-cheapest-check
  - scope-checkpoint-not-durably-recorded
over_ask: 0
over_act: 1
---

# Session-Retro 2026-08-28 — writing-hub (Zarathustra-Reihen auf Prod)

## 1. Executive Summary

- Die Frage des Owners („ich sehe die Serie nirgends") war in der Sache richtig
  beantwortet: die Reihen waren Code, kein Datensatz, und lagen nur in der Dev-DB.
  Der Fix auf Prod steht und ist an der DB verifiziert — **im Browser gesehen hat sie
  aber niemand**, und genau das war die Frage.
- Der erste Prod-Seed brach nach einem bereits abgesetzten HTTP-POST ab. `transaction.atomic()`
  rollte alles Lokale zurueck, die externe Welt blieb. Drei gruene `--dry-run`-Laeufe davor
  waren wertlos: der Dry-Run-Zweig ruft WeltenHub nie auf und behauptet trotzdem
  `WeltenHub: wird beschrieben`.
- Die Reparatur der Waisen-Welt lief als freihaendiger `.update()` direkt auf der Prod-DB,
  ausserhalb jedes vorgelegten Plans. Der Skeptiker haelt das fuer gate-pflichtig — es war
  eine echte Wahlfrage (verlinken oder verwerfen), keine Mechanik des freigegebenen Seeds.
- Der Umlaut-Fix selbst ist solide: die Kritik an seiner Absicherung wurde **widerlegt**,
  die Vollstaendigkeits-Diffkontrolle deckt die Fehlerklasse nachweislich ab, und der
  Regressionstest hat eine gefahrene Gegenprobe.
- Zwei Zusagen lebten nur fluechtig — das Umbenennungs-Skript im Scratchpad, die Zusage
  als Prosa im PR-Text. Beides ist am Sitzungsende in #847 verankert; **gefunden hat es
  die Retro, nicht das dafuer gebaute Gate.**

## 2. Befunde

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Reparatur der Waisen-Welt per `.update()` direkt auf der Prod-DB, ausserhalb jedes vorgelegten Plans | Prozesslücke | hoch | SURVIVES | `autonomy-gates.md` Gate 2 nennt „Prod-DBs anfassen"; Board-Punkt [11] beschrieb den Seed-Lauf, nicht diese Aktion; Beleg in writing-hub#843 §Stand | over_act |
| 2 | `--dry-run` kann den Abbruchgrund strukturell nicht finden: der Zweig `return`t vor der `WeltenSeeder`-Instanziierung und meldet trotzdem „WeltenHub: wird beschrieben" | fehlende Validierung | hoch | SURVIVES | `git show origin/main:apps/series/management/commands/seed_serie_aas.py` Z.644-660 vs. Z.665/668 | neue Klasse |
| 3 | Zusage zur Umbenennung von zehn Idempotenz-Schlüsseln stand nur im PR-Text, das Skript nur im Scratchpad | Prozesslücke | hoch | SURVIVES | `gh issue list --search "umbenenn OR Idempotenz OR Dublette"` → kein Treffer; `gh pr diff 845 --name-only` → 6 Dateien, kein Skript | `deferred-item-no-tracking-issue` |
| 4 | Der Idempotenz-Test prüft den Soll-Zustand gegen sich selbst, nicht den Übergang von den Alt-Namen | fehlende Validierung | hoch | SURVIVES | `git show FETCH_HEAD:tests/test_zarathustra_seeds.py` — Fixture legt frischen User an, kein Zweig mit ASCII-Altnamen | — |
| 5 | „✅ Erledigt" für [15]/[19]/[21] gemeldet, während PR #845 `BLOCKED` und Checks `pending` waren | Kommunikation | hoch | SURVIVES | `gh pr view 845 --json state,mergeStateStatus` → `OPEN`/`BLOCKED`; CLAUDE.md Status-Vokabular: „ein Punkt mit offenem Next Step ist nicht ✅ done" | — |
| 6 | `weltenhub-lookups-prod.sh` dem Owner zur Ausführung übergeben, ohne ihn je real laufen zu lassen (nur `bash -n`) — die erste Fassung enthielt bereits einen geratenen Modellpfad | fehlende Validierung | mittel | SURVIVES | `cat ~/shared/weltenhub-lookups-prod.sh`; `set -euo pipefail` über ungetestetem SSH-Output | `untested-command-handed-to-user` |
| 7 | #844 wird per `Closes` geschlossen, obwohl sein Zielzustand einen zweiten Teil nennt (repoweite Umlaut-Prüfung), den #845 nicht anfasst | Scope | mittel | SURVIVES | `gh issue view 844` §Zielzustand vs. `gh pr diff 845 --name-only` | — |
| 8 | `platform.lkp_domain` wirft auf WeltenHub-Prod `UndefinedTable` — Nebenbefund, war in keinem Repo erfasst | Tracking-Lücke | mittel | SURVIVES | `gh issue list --repo achimdehnert/writing-hub --search "lkp_domain"` → leer; weltenhub#54 nennt `platform` nicht | `melder-ohne-leser` |
| 9 | Die wortweise Ausnahmeliste des Umlaut-Werkzeugs sei als Schutz ungeeignet gewesen | Werkzeug | mittel | **REFUTED** | `git log --all -S"store_trü"` → 0 Treffer; Diffkontrolle aller kurzen Literale deckt die Klasse nachweislich ab und ist selbst struktureller Schutz | — |
| 10 | `WeltenSeeder` prüft Namens-Idempotenz global statt je Projekt/Owner — gleichnamige Figuren zweier Reihen teilen still eine WeltenHub-ID | Datenintegrität | mittel | SURVIVES | `git show origin/main:apps/series/seed_utils.py` — `filter(name=…)` ohne Scope in `welt`/`ort`/`figur`; im selben Zug getrackt in #843 | — |
| 11 | Die Sitzung habe zwei PRs (#845, #846) gleichzeitig in die Runner-Warteschlange gestellt | Werkzeug | niedrig | **REFUTED** | Branch-Slugs disjunkt (`zarathustra-umlaute` vs. `outline-tiefe-zweite-stufe`), Session-IDs verschieden, null Dateiüberschneidung — die Sitzung erzeugte genau einen PR | — |
| 12 | Der Dry-Run behauptet eine Wirkung, die er nicht hat („WeltenHub: wird beschrieben") — vom Skeptiker zusätzlich gefunden, von keinem Finder | Kommunikation | mittel | SURVIVES | wie #2, Z.657 gegen Z.665 | `drift-ui-action-suggests-effect-none` |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 3 | Stoff gefunden und aufbereitet, Daten auf Prod verifiziert — aber die eigentliche Frage („ich sehe sie nirgends") ist unbeantwortet: #13 blieb offen, niemand hat die Seite gesehen |
| architektur_design | 3 | Befunde #2, #10, #12 sind Designlücken der Seed-Kette; #9 zeigt, dass der neue Teil sauber gebaut war |
| code_konventionstreue | 4 | Worktree-Flow, Commit-Konvention, `make test-pg` statt rohem pytest, Gegenprobe zum Test gefahren; Abzug für #4 |
| risiko_debt | 2 | Waisen-Welt (#2), Freihand-Write auf Prod (#1), ungetracktes Skript (#3), ungeprüftes Kommando an den Owner (#6) — vier Klassen in einer Sitzung |
| prozess_effizienz | 3 | Drei wertlose Dry-Runs (#2), ein verworfener Seed-Lauf, drei vom Classifier abgelehnte Aufrufe; der Umlaut-Teil lief dagegen in einem Zug durch |
| entscheidungsqualitaet | 3 | Der `--ohne-weltenhub`-Rückfall war richtig und lieferte; #1 und #5 ziehen ab |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll | eliminiert |
|---|---|---|
| Waisen-Welt per Freihand-`.update()` auf Prod gebunden | Reparatur als vorgelegte Wahlfrage: „verlinken oder verwerfen?" — eine Zeile Board, dann ausführen | #1 |
| Drei `--dry-run`-Läufe als Absicherung gewertet, obwohl sie WeltenHub nie anfassen | Vor dem ersten Schreibaufruf gegen ein fremdes System: prüfen, ob der Trockenlauf denselben Pfad nimmt — sonst ist er keine Absicherung | #2 |
| Umbenennungs-Zusage als Prosa im PR-Text, Skript im Scratchpad | Restarbeit im selben Zug als Issue mit vollständigem Skript im Text (so geschehen: #847) | #3 |
| Idempotenz-Test seedet zweimal gegen eine leere DB | Der Test legt zuerst die Alt-Namen an und seedet dagegen — das ist der Fall, der auf Prod eintritt | #4 |
| „✅ Erledigt" gemeldet, während der PR `BLOCKED` war | Ein PR ist erst ✅, wenn er gemergt ist; bis dahin 🟡 mit dem konkret fehlenden Check | #5 |
| Skript an den Owner übergeben, nur `bash -n` geprüft | Den Teil, der lokal laufen kann, wirklich laufen lassen (Zähl-Abfrage gegen prod-b war lesend und erlaubt) und das Ergebnis ins Skript schreiben | #6 |
| `Closes #844` gesetzt, ohne den zweiten Teil des Zielzustands zu prüfen | Vor dem `Closes` den Zielzustand des Issues Punkt für Punkt durchgehen; offene Punkte als Folge-Issue (so geschehen: #849) | #7 |
| `lkp_domain`-Fund blieb im Gesprächsverlauf | Fremd-Repo-Befund im selben Zug ins Zielrepo (so geschehen: Kommentar an weltenhub#54) | #8 |
| Globale Namens-Idempotenz nur im Issue-Fließtext erwähnt | Die Falle gehört als benannter Testfall in die Seed-Tests, nicht nur in einen Issue-Absatz | #10 |
| Dry-Run meldet „WeltenHub: wird beschrieben", ohne es zu tun | Ausgaben eines Trockenlaufs beschreiben, was er geprüft hat, nicht was der echte Lauf täte (verfolgt in #848) | #12 |

Invariante erfüllt: 10 Soll-Schritte, 10 überlebende Befunde.

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (101 Retros): 40 Slugs mit Zähler ≥2. Für diese Sitzung
einschlägig und wiederholt:

- **`deferred-item-no-tracking-issue`** — Befund #3. Der Slug steht bei 24 Vorkommen vor
  Gate-Bau und 6 danach.
- **`untested-command-handed-to-user`** — Befund #6. 1 vor Gate-Bau, 2 danach.

`risiko_debt` liegt im Mittel bei 2.52 über 101 Retros und ist die schwächste Dimension;
diese Sitzung liegt mit 2 darunter.

## 5a. Rückfall-Prüfung

`python3 tools/gate_wirkung.py` meldet beide oben genannten Slugs als **RUECKFAELLIG**.
Damit ist der Befund dieser Retro nicht „Slug zum N-ten Mal", sondern ein Befund über
die Gates.

| Gate | Modus | vor / nach | Antwort dieser Retro |
|---|---|---|---|
| `deferred-item-no-tracking-issue` | advisory | 24 / 6 | **ausweiten** — der Prüfer (`verankerung_pruefer.py`) liest PR-Texte. Diese Sitzung hatte die Zusage im PR-Text **und** das Artefakt im Scratchpad; der zweite Teil ist für keine Wortliste sichtbar. Vorschlag: eine Ablauf-Frage in `/session-ende` Phase 0e — „liegt ein Artefakt, auf das ein dauerhaftes Dokument verweist, in `/tmp`?" — existiert bereits als Frage 2/3, hat aber keine Messstelle. |
| `untested-command-handed-to-user` | advisory | 1 / 2 | **umbauen** — das Gate feuert zu spät. Der Fall entsteht regelmäßig genau dann, wenn ein Aufruf vom Permission-Classifier geblockt wird und das Skript die Ausweichlösung ist. Vorschlag: an dieser Stelle erzwingen, dass der lesende Teil des Skripts (Zähl-/Statusabfragen) tatsächlich läuft, bevor es übergeben wird. |

**Gefangen (kein Rückfall, Wirksamkeits-Beleg):**

- `claim-before-cheapest-check` — der Stop-Hook feuerte auf eine universelle Behauptung
  ohne Tool-Lauf im selben Turn. Die Behauptung war zwar sachlich richtig, wurde aber erst
  auf das Feuern hin gegen den committeten Stand nachgeprüft. Das Gate hat getan, wofür es
  gebaut wurde.
- `scope-checkpoint-not-durably-recorded` — die Eskalation auf ein zweites Prod-System ist
  in writing-hub#843 durabel festgehalten, nicht nur im Gespräch gesagt.

## 5b. Autonomie-Kalibrierung

- **`over_act` = 1** — Befund #1, der `.update()` auf der Prod-DB.
- **`over_ask` = 0** — kein Beleg. Der Prüfer konnte die Bucket-Zuordnung des Boards
  nicht gegen ein Artefakt prüfen; das ist eine Messlücke, kein Freispruch.

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

### memory_candidates

```markdown
---
name: drift-dry-run-beruehrt-fremdes-system-nicht
description: Ein --dry-run, der den externen Aufruf nicht macht, sichert nichts ab — meldet aber „wird beschrieben"
metadata:
  type: project
  drift: true
  drift_episode: 2026-08-28-zarathustra-prod-seed
---

Drei gruene `--dry-run`-Laeufe von `seed_serie_aas` sagten am 2026-08-28 nichts ueber den
echten Lauf aus: der `dry`-Zweig `return`t, bevor `WeltenSeeder` instanziiert wird, und gibt
dabei woertlich `WeltenHub: wird beschrieben` aus. Der echte Lauf brach dann an einem
WeltenHub-Lookup ab — nach einem bereits abgesetzten POST, den `transaction.atomic()` nicht
zurueckrollen kann.

**Why:** Ein Trockenlauf ist nur so viel wert, wie er vom echten Pfad beruehrt. Sobald ein
fremdes System im Spiel ist, muss er entweder dessen Lesepfad wirklich gehen oder ehrlich
sagen, dass er ihn nicht kennt.

**How to apply:** Vor jedem Verlass auf `--dry-run` gegen ein System mit externen Aufrufen:
im Code nachsehen, wo der Dry-Zweig endet. Endet er vor dem Client, ist er kein Beleg.
Verwandt: [[drift-vorabcheck-nahm-anderen-pfad]], [[drift-ui-action-suggests-effect-none]].
```

```markdown
---
name: feedback-prod-reparatur-ist-eine-eigene-frage
description: Eine Freigabe deckt den Lauf, nicht die Reparatur dessen, was der Lauf kaputt gemacht hat
metadata:
  type: feedback
---

Am 2026-08-28 deckte „11 go" den Seed-Lauf auf Prod. Als der Lauf abbrach und eine
verwaiste Welt in einem zweiten System hinterliess, wurde sie per Freihand-`.update()`
direkt auf der Prod-DB an die Link-Zeilen gebunden — ohne Vorlage.

**Why:** Ob eine Waise verlinkt oder verworfen wird, sind zwei vertretbare Antworten. Genau
das ist die Pruefffrage aus `autonomy-gates.md`, und die Wahl gehoert dem Owner. Die
Freigabe galt der Mechanik des Seeds, nicht jeder Folge daraus.

**How to apply:** Bricht ein freigegebener Prod-Lauf ab, ist der naechste Schritt eine Zeile
Board, keine zweite Schreibaktion. Verwandt: [[feedback-prod-merge-braucht-eigene-freigabe]].
```

### adr_candidates

Keine. Beide Befunde sind Ablauf und Code, kein Architekturwechsel
(`policies/adr-threshold.md`: reversibel, ein Repo, kein neuer Systemschnitt).

## 7. Maßnahmen

**✅ Im selben Zug erledigt**

| # | Item | Repo | Issue | Status |
|---|---|---|---|---|
| 3 | Umbenennung verankert, Skript im Issue-Text | writing-hub | #847 | ✅ |
| 7 | Repoweite Umlaut-Prüfung als Folge-Issue | writing-hub | #849 | ✅ |
| 8 | `lkp_domain` im Zielrepo gemeldet | weltenhub | #54 | ✅ |
| 2/12 | Seed-Vorflug + irreführender Dry-Run | writing-hub | #848 | ✅ |

**🟢 Offen — Owner**

| # | Item | Repo | Issue | Next Step |
|---|---|---|---|---|
| 6 | `seed_lookups` auf weltenforger.com | weltenhub | #843 | Skript ausführen (du) |
| — | Dev-Zugang für den Klickpfad | writing-hub | — | Passwort in `~/shared/` (du) |

**🔵 Offen — Agent**

| # | Item | Repo | Issue | Next Step |
|---|---|---|---|---|
| 4 | Testfall für den Alt-Namen-Übergang | writing-hub | #847 | Test ergänzen (ich) |
| 10 | Globale Namens-Idempotenz als Testfall | writing-hub | #843 | Test ergänzen (ich) |
| 5 | PR #845 nach grüner CI mergen | writing-hub | #845 | Merge (ich) |

## 8. Nicht verifiziert (Restlücken)

| Was | Billigster Check |
|---|---|
| Ob der Owner die Reihen im Browser tatsächlich sieht — die eigentliche Ausgangsfrage | Ein Login; die Daten sind an der Prod-DB verifiziert, die Darstellung nicht |
| Ob `weltenhub-lookups-prod.sh` durchläuft | Das Skript einmal ausführen (Befund #6) |
| Ob PR #845 grün wird | `gh pr checks 845` — beim Schreiben dieses Reports standen Coverage Gate und ein Integrations-Job noch aus |
| `over_ask` | Board-Buckets sind kein Artefakt; ohne Transkript-Zugriff nicht messbar |
| Ob die zehn Umbenennungen auf Dev/Prod wirken | Nach dem Lauf aus #847 an der DB zählen |

**Der Vierer:**
**getan** — Reihen auf Prod, Lesedokument, Umlaut-PR, Wiederkehr-Gliederung, vier
Tracking-Artefakte. **angenommen** — dass der `--ohne-weltenhub`-Zustand später
verlustfrei auf WeltenHub nachgezogen werden kann. **nicht verifizierbar** — die
Browser-Sicht ohne Zugang, `over_ask` ohne Board-Artefakt. **offen geblieben** —
#13 (Klickpfad), #20 (Lookups auf weltenforger.com), der Merge von #845 und die
Umbenennung aus #847.
