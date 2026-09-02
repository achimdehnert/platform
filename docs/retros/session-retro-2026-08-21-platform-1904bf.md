---
retro_schema: 1
date: 2026-08-21
repo_scope: [platform]
session_id: 1904bf
footprint: full
findings_total: 14
findings_survived: 7
refuted_rate: 0.5
phase3_refuted: 7
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 4
  code_konventionstreue: 2
  risiko_debt: 2
  prozess_effizienz: 4
  entscheidungsqualitaet: 3
gate_candidates:
  - comment-claims-guard-the-code-does-not-have
  - test-passes-because-join-masks-the-defect
recurring_findings:
  - claim-before-cheapest-check
  - skill-copy-not-redistributed
  - hand-distributed-copy-not-redistributed
  - gate-matches-spelling-not-substance
gates_caught:
  - claim-before-cheapest-check
---

# Session-Retro 2026-08-21 — platform: Vorgangsseite, Mail-Links, Melder-Fix

## 1 · Executive Summary

- **Vier PRs gemergt, alle CI-gruen** (2185, 2186, 2189, 2194), ein Issue angelegt
  (2183), zwei Analyse-Kommentare an Issue 2054. Ein Repo, kein Prod-Schritt,
  keine Migration.
- **Die drei schwersten Befunde sind Selbstbefunde im eigenen Code** und alle drei
  von einem fremden Reviewer per ausgefuehrtem Kommando belegt: ein Kommentar, der
  einen Schutz behauptet, den die Regex nicht hat; ein Test, der genau diesen
  Schutz zu pruefen vorgibt und ihn strukturell nicht pruefen kann; und eine
  Klassifikationsregel, die "Nichts zu tun." als offenen Punkt hervorhebt.
- **Sieben von vierzehn Befunden wurden widerlegt** — darunter **alle vier**
  Prozess-Befunde. Die Fehlerrichtung war Selbst-*Strenge*, nicht Selbstnachsicht:
  eine als eigenes Rework gebuchte Aenderung war nachweislich eine Erweiterung.
- **Ein Finder hat ein Zitat erfunden** und einen Satz aus Issue 2054 dem Issue
  2183 zugeschrieben, um einen Doppelstandard zu belegen. Der Skeptiker hat es
  gefangen. Das ist ein Befund ueber die Retro-Methode, nicht ueber die Sitzung.
- **Das Gate `claim-before-cheapest-check` hat gefeuert und gegriffen**: es fing
  eine falsche Behauptung ueber den Verbleib eines Commits, bevor sie stehen
  blieb. Es ist damit `gates_caught`, kein Rueckfall.

## 2 · Befunde

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | `_SATZGRENZE` trennt "20.08. Klimm" in zwei Saetze; der Kommentar darueber behauptet einen Zwei-Ziffern-Lookbehind, den die Regex nicht enthaelt (Unterform: Doku-Code-Diskrepanz) | fehlende Validierung | hoch | SURVIVES | `todo_board.py:706-708` gegen `origin/main`; ausgefuehrt: `_SATZGRENZE.split("Termin am 20.08. Klimm bestaetigt.")` → 2 Teile | neu |
| 2 | Der Test `test_should_keep_a_date_from_splitting_the_sentence` besteht trotz Befund 1, weil `" ".join(inhalt)` beide Fragmente wieder zusammenfuegt — er kann die behauptete Eigenschaft nicht falsifizieren (Unterform: vakuoser Test) | fehlende Validierung | hoch | SURVIVES | `test_todo_board.py:748`; Assertion prueft `t["inhalt"]` statt die Zwischengroesse `saetze` | neu |
| 3 | `_ACTION_MUSTER` zieht "Nichts zu tun." in die Action-Bahn — Bedeutungsumkehr; ebenso "Fall bleibt offen fuer Rueckfragen." (Unterform: fehlerhafte Klassifikation) | verfrühte Festlegung | hoch | SURVIVES | `todo_board.py:720-723`; per `zerlege_eintrag` ausgefuehrt | neu |
| 4 | Die Analyse-Bahn feuert auf **4 von 302** realen Verlaufseintraegen (1,3 %); kein einziger Test erzwingt je einen nichtleeren `analyse`-Wert | fehlende Validierung | mittel | SURVIVES | Skeptiker-Lauf ueber `mail-vorgaenge.json` + Archiv: 302 Eintraege → Analyse 4, Action 33, Deckung 80 | neu |
| 5 | `_repos_aus_kommando("cat ~/github/NOTES.md")` liefert `{'NOTES.md'}` — kein Existenz-Check gegen `~/github/` (Unterform: fehlende Eingabevalidierung) | fehlende Validierung | niedrig | SURVIVES | `scope_checkpoint_scanner.py:150-166`, ausgefuehrt | neu |
| 6 | `_ordner_mit_uid` veraendert die IMAP-Selektion und stellt sie nicht wieder her; heute unschaedlich, weil der einzige Aufrufer neu selektiert (Unterform: Kapselungsluecke) | Werkzeug | niedrig | SURVIVES | `mail_link_server.py:782-816` | neu |
| 7 | `todo_board._slug` dupliziert `mail_view.slugify` handschriftlich; heute zeichengleich bis auf den fehlenden Leer-Fallback (Unterform: Code-Duplikation) | Werkzeug | niedrig | SURVIVES | Zeile-fuer-Zeile-Vergleich beider Funktionen | neu |
| 8 | PR 2189 sei vermeidbares Rework an PR 2185 (36 Min Fehlerfenster in `main`) | Prozesslücke | hoch | **REFUTED** | `git log -S "_ordner_ohne_angabe"`: Funktion entsteht erst in `61f4480d` (PR 2189) — die Server-Faehigkeit war zur Bauzeit von 2185 nicht vorhanden, also nicht pruefbar | — |
| 9 | Branch-Wiederverwendung ueber 2189/2194 schade der Nachvollziehbarkeit | Prozesslücke | mittel | **REFUTED** | `gh pr diff 2194` zeigt sauber 2 Dateien / 222 Zeilen; der Merge-Commit taucht im Review-Diff nicht auf | — |
| 10 | Issue 2183 sei ohne sitzungsinternen Tracking-Vermerk liegengeblieben | Prozesslücke | mittel | **REFUTED** | Hausregel verlangt "Issue **oder** Ledger-/KONZ-Zeile"; das Issue selbst erfuellt sie, ein PR-Rueckverweis ist nicht gefordert | — |
| 11 | PR 2185 buendle zwei fachlich unabhaengige Anliegen | Prozesslücke | mittel | **REFUTED** | Der Doku-Teil beschreibt woertlich die Konvention, die der neue Renderer voraussetzt — ein Anliegen, nicht zwei | — |
| 12 | PR 2186 (Melder-Fix) sei Scope Creep | verfrühte Festlegung | niedrig | **REFUTED** | Kein Beleg fuer "nicht angefordert"; der Melder mass waehrend derselben Sitzung nachweislich falsch, der Fix stand fest — Instandhaltung, nicht Creep | — |
| 13 | Doppelstandard: Melder sofort gefixt, `ablage_erledigt.py` nur getrackt — gestuetzt auf ein Zitat aus Issue 2183 | Kommunikation | mittel | **REFUTED** | Der zitierte Satz steht **nicht** in Issue 2183 (`comments: []`), sondern in Issue 2054 und betrifft ein anderes Werkzeug — der Befund ruht auf einem erfundenen Zitat | — |
| 14 | Alle 14 PRs des Tages gehoerten zu dieser Sitzung (Branch-Praefix als Kriterium) | Werkzeug | mittel | **REFUTED** | Das Praefix `session/<datum>/<owner>/` ist eine Tages-Konvention, keine Sitzungs-ID; 2188/2190/2192 zeigen keine Branch-, Code- oder Verweis-Kontinuitaet zum Faden 2185→2189→2194 | — |

## 3 · Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 3 | Acht der neun Auftraege sauber geliefert; Auftrag 4 nannte ausdruecklich "inhalt, **analyse**, action" — die Analyse-Bahn greift real bei 1,3 % (#4). |
| architektur_design | 4 | Der Schnitt (Aufloesung im Dienst statt Heuristik im Renderer) hielt der Falsifikation stand (#8 REFUTED); Abzug fuer #6 und #7. |
| code_konventionstreue | 2 | #1 ist ein Kommentar, der eine Eigenschaft behauptet, die der Code nicht hat — in einem Repo, dessen Kommentarkultur genau das verbietet. #2 ist ein Test, der seine eigene Zusicherung nicht traegt. |
| risiko_debt | 2 | #1, #2 und #3 stehen unrepariert in `main`; Issue 2183 offen. Drei Defekte, die die Anzeige eines Arbeitswerkzeugs verfaelschen. |
| prozess_effizienz | 4 | Vier PRs, alle gruen, kein Rework (#8 REFUTED), keine Kollision trotz Parallelsitzung (#9/#11 REFUTED). Ein fehlgeleiteter Commit wurde vom eigenen Check gefangen. |
| entscheidungsqualitaet | 3 | Die bewussten Verengungen (Ordner-Route nur mit Konto, Link nur bei bekanntem Ordner) hielten stand; die Lockerung der Action-Marker (#3) erfolgte ohne Gegenbeispiel-Test. |

## 4 · Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Kommentar behauptet "Lookbehind auf zwei Ziffern schuetzt Datumsformen", die Regex hat einen Ein-Zeichen-Lookbehind | Beim Vereinfachen einer Regex den danebenstehenden Kommentar als **Behauptung** behandeln und mit demselben Kommando pruefen, das ihn belegen soll — hier `_SATZGRENZE.split("… 20.08. Klimm …")` | #1 |
| Test prueft `t["inhalt"]` und besteht, obwohl die Zerlegung falsch ist, weil `" ".join()` den Schaden maskiert | Einen Test, der eine **Zwischengroesse** zusichert, auch auf der Zwischengroesse assertieren (`saetze`), nicht auf dem zusammengesetzten Endergebnis | #2 |
| Action-Marker um bis zu zwei Qualifikatoren gelockert, Negation nicht bedacht | Bei jeder **Lockerung** eines Musters im selben Commit ein Gegenbeispiel als Test schreiben, das unter der Lockerung falsch klassifiziert wuerde ("Nichts zu tun.") | #3 |
| Drei Bahnen gebaut, Wirksamkeit nur an konstruierten Beispielen geprueft | Vor dem Merge eines Klassifikators **einmal ueber den echten Bestand laufen** und die Trefferzahl je Klasse in den PR schreiben — 4/302 waere vor dem Merge sichtbar gewesen | #4 |
| `_repos_aus_kommando` nimmt jeden Namen hinter `/github/` | Den gefundenen Namen gegen die tatsaechlich existierenden Verzeichnisse pruefen, bevor er gezaehlt wird | #5 |
| `_ordner_mit_uid` laesst die IMAP-Selektion veraendert zurueck | Eine Methode, die fremden Zustand anfasst, stellt ihn wieder her oder benennt den Seiteneffekt im Docstring als Vertrag | #6 |
| `_slug` handschriftlich neben `mail_view.slugify` gebaut | Eine bestehende Funktion importieren statt sie nachzubauen; wo der Import nicht geht, den Gleichlauf per Test festnageln | #7 |

## 5 · Längsschnitt

`python3 tools/retro_kpis.py` (84 Retros): **34 Slugs mit Zaehler ≥2** sind gate-pflichtig,
davon **16 ohne registriertes Gate**. Drei davon beruehren diese Sitzung:

- `skill-copy-not-redistributed` — die aktive `mailcheck`-Kopie stand nach dem Merge von
  PR 2185 weiter auf dem alten Commit und kannte die neue Konvention nicht. Nachverteilt
  und verifiziert, aber erst auf Nachfrage. **Kein Gate registriert.**
- `hand-distributed-copy-not-redistributed` — dieselbe Klasse am Hook: die aktive Kopie von
  `evidence_claim_scanner.py` war fuenf Tage aelter als die Quelle. Gate existiert.
- `gate-matches-spelling-not-substance` — der Scope-Melder zaehlte drei Schreibweisen
  desselben Repos als drei Repos. **Kein Gate registriert.**

`refuted_rate`-Band: 0,05–0,55 ueber die letzten acht Retros, aktueller Wert **0,50** — im
gesunden Band, am oberen Rand. Score-Mittel `risiko_debt` ueber 84 Retros: **2,58**; dieser
Report liegt mit 2 darunter.

## 5a · Rückfall-Prüfung

`python3 tools/gate_wirkung.py`: **2 Gates rueckfaellig** —
`deferred-item-no-tracking-issue` (9× seit Bau) und `handover-stale-vor-merge` (2×).
**Beide nicht aus dieser Sitzung**; kein Handlungsbedarf aus diesem Report, der Strang
liegt in [#2143](https://github.com/achimdehnert/platform/issues/2143).

**Ein Gate hat in dieser Sitzung nachweislich gegriffen.** `claim-before-cheapest-check`
(blocking, umgebaut am 2026-08-20) fing eine Aussage, die einen gemergten Commit einem
bereits geschlossenen PR zuordnete. Ohne den Stop-Hook waere die Falschaussage stehen
geblieben **und** der Commit waere in keinem PR gelandet. Es ist damit `gates_caught`
und ausdruecklich **kein** Rueckfall.

Nebenbefund zum Gate selbst: seine aktive Hook-Kopie war zu Sitzungsbeginn fuenf Tage
aelter als die Quelle und kannte den Subjekt-Block nicht — es hat also in seiner
**alten** Fassung gegriffen. Die neue ist seit dem Sync aktiv und ungeprueft.

## 5b · Autonomie-Kalibrierung

- `over_ask`: **1** — der Melder-Fix (PR 2186) wurde als Frage vorgelegt ("jetzt oder
  spaeter?"), obwohl die Loesung feststand, zwei Zeilen umfasste und reversibel war.
  Genau der Fall, den die Owner-Weisung vom 2026-08-20 ausschliesst.
- `over_act`: **0** — kein Prod-Schritt, kein Publish, keine irreversible Aktion; die
  Postfach-Schreibvorgaenge waren saemtlich ruecknehmbar und ausdruecklich beauftragt.

## 6 · Verankerung (Vorschläge, nicht ausgeführt)

**memory_candidates**

```markdown
---
name: feedback_comment_claims_a_guard_the_code_does_not_have
description: "Ein Kommentar neben einer Regex ist eine Behauptung — beim Vereinfachen des Musters mit demselben Kommando pruefen, das ihn belegen soll"
metadata:
  node_type: memory
  drift: true
  drift_episode: 2026-08-21-satzgrenze-lookbehind
  type: feedback
  rule_class: B
---
🌀 Beim Umbau von `_SATZGRENZE` (todo_board.py) blieb ein Kommentar stehen, der
einen "Lookbehind auf zwei Ziffern" behauptete. Die vereinfachte Regex hatte nur
einen Ein-Zeichen-Lookbehind; "20.08. Klimm" wurde in zwei Saetze zerlegt — genau
der Fall, den der Kommentar als geschuetzt auswies.

**Why:** Ein erklaerender Kommentar wird beim spaeteren Lesen wie ein Beleg
behandelt, nicht wie eine Vermutung. Er ueberlebt Refactorings stumm.
**How to apply:** Behauptet ein Kommentar eine Eigenschaft ("schuetzt X",
"verhindert Y"), gehoert das Kommando, das sie belegt, in denselben Commit —
als Test oder als Zeile im PR-Text. Beim Vereinfachen des Musters zuerst den
Kommentar pruefen, dann den Code.
Verwandt: [[feedback_claim_reaches_further_than_the_look]]
```

```markdown
---
name: feedback_join_masks_the_defect_assert_the_intermediate
description: "Ein Test, der das zusammengefuegte Endergebnis prueft, kann einen Zerlegungsfehler nicht sehen — auf der Zwischengroesse assertieren"
metadata:
  node_type: memory
  drift: true
  drift_episode: 2026-08-21-vakuoser-satzgrenzen-test
  type: feedback
  rule_class: A
---
🌀 `test_should_keep_a_date_from_splitting_the_sentence` sicherte zu, dass ein
Datum keinen Satz trennt — und bestand, waehrend die Zerlegung falsch war. Grund:
beide Fragmente landeten in derselben Bahn und wurden mit `" ".join()` wieder zu
genau demselben String zusammengefuegt. Der Test konnte die Eigenschaft
strukturell nicht falsifizieren.

**Why:** Die Nicht-Trivialitaets-Messung (Test faellt gegen origin/main) faengt
das NICHT: der Test fiel gegen die alte Fassung aus einem anderen Grund und war
danach gruen — beides ohne die zugesicherte Eigenschaft je zu beruehren.
**How to apply:** Sichert ein Test eine **Zwischengroesse** zu (Zerlegung,
Klassifikation, Parsing), muss die Assertion auf der Zwischengroesse liegen.
Fuehrt der Weg dorthin ueber ein `join`/`merge`/`format`, ist die Endgroesse als
Beweis ungeeignet — auch wenn sie sich richtig liest.
Verwandt: [[feedback_throwing_test_double_is_vacuous_behind_except]]
```

**adr_candidates:** keine. Alle Befunde sind Werkzeug- und Testfehler innerhalb
eines Repos ohne Service-Boundary, ohne Reversal und ohne Cross-Repo-Vertrag —
nach `adr-threshold.md` ausdruecklich **kein** ADR-Fall.

## 7 · Maßnahmen

### 🟢 Offen — dein Zug

1. 🟢 Entscheiden, ob #1/#2/#3 sofort behoben werden (drei Defekte in `main`, Anzeige verfaelscht) — https://github.com/achimdehnert/platform/blob/main/tools/todo_board/todo_board.py
2. 🟢 Gate fuer `skill-copy-not-redistributed` bauen oder bewusst ablehnen — https://github.com/achimdehnert/platform/blob/main/docs/governance/gate-registry.json

### 🔵 Offen — ich kann sofort

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 3 | Regex + Kommentar richten | platform | #1/#2 | 🔵 ready | Test auf `saetze` (ich) |
| 4 | Negations-Gegenbeispiel | platform | #3 | 🔵 ready | Marker verengen (ich) |
| 5 | Bestandslauf im PR ausweisen | platform | #4 | 🔵 ready | Trefferzahl je Bahn (ich) |
| 6 | Kleinbefunde buendeln | platform | #5/#6/#7 | 🔵 ready | ein PR (ich) |

### ✅ Erledigt

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 7 | Vier PRs gemergt | platform | 2185/2186/2189/2194 | ✅ done | — |
| 8 | Hooks + Skill verteilt | platform | — | ✅ done | — |

## 8 · Nicht verifiziert (Restlücken)

| Was offen blieb | Billigster Check |
|---|---|
| Die zwei DOCX-Steckbriefe und der Mail-Entwurf (Auftrag 7) wurden von **keinem** Finder geprueft — sie liegen ausserhalb von git und waren fuer die Subagenten unerreichbar. Inhaltliche Fehler darin sind durch diesen Report **nicht** abgedeckt. | Owner liest die zwei Dateien in `~/shared/` gegen `KONZ-meiki-006` |
| Der Collector datierte einen Issue-Kommentar (07:25Z) als "nach" einem Merge (08:05Z). Der Fehler blieb ohne Wirkung auf einen Befund, wurde aber nicht formal als Befund gefuehrt. | `gh issue view 2054 --json comments` gegen `gh pr view 2186 --json mergedAt` |
| Die **neue** Fassung des `claim-before-cheapest-check`-Hooks ist seit dem Sync aktiv, hat aber in dieser Sitzung nicht mehr gefeuert — ihre Wirksamkeit ist unbelegt. | Naechste Sitzung: `gate_wirkung.py` nach ≥3 Retros |
| Ob `_ordner_mit_uid` in der Praxis je mehrere Treffer liefert (Auswahlseite), wurde nie ausgeloest. | UID suchen, die in INBOX und Entwuerfen existiert |

**Vierer-Abschluss:** *getan* — vier PRs, ein Issue, zwei Analysen, Hook- und
Skill-Verteilung, sieben belegte Befunde. *angenommen* — dass die 2188/2190/2192
fremden Sitzungen gehoeren (durch Diskontinuitaet gestuetzt, mangels Sitzungs-ID
nicht beweisbar). *nicht verifizierbar* — die Qualitaet der zwei DOCX-Dokumente
und des Mail-Entwurfs mit den vorhandenen Mitteln. *offen geblieben* — die drei
Defekte #1/#2/#3 in `main` und Issue 2183.

## Self-Review (Phase 5)

Ein Meta-Reviewer prüfte den Report gegen die Skill-Regeln (nicht gegen die
Sitzung). Ergebnis: **ein leichter Befund** — die Kategorie-Spalte trug freie
Neuprägungen (`Doku-Code-Diskrepanz`, `vakuoser Test`, `Kapselungsluecke`,
`Code-Duplikation`) statt des kanonischen Vokabulars aus Phase 2. Das schwächt
genau die maschinelle Längsschnitt-Vergleichbarkeit, die das feste Skelett
herstellen soll. **Behoben:** Kategorien auf das kanonische Vokabular gezogen,
die präzise Unterform in den Befundtext verschoben.

Alle übrigen neun Prüfpunkte OK: Frontmatter schema-valide und rechnerisch
konsistent (`(7+0)/14 = 0,50`), Scores ganzzahlig und je an eine Befundnummer
verankert, Invariante 7 = 7 erfüllt, jeder Befund mit hartem Artefakt-Beleg und
ohne „vermutlich"/„Session-Log"-Sprache, `gate_wirkung.py` gelaufen und die
`gates_caught`-Einordnung durch das Tool gedeckt (`urteil: zu-frueh`, 0
Vorkommen nach Bau), Report-Pfad kollisionsfrei, `refuted_rate` numerisch am
oberen Rand des gesunden Bands (0,05–0,55 über acht Retros), Sektion 8 mit
billigstem Check je Lücke, Vierer-Abschluss vorhanden.
