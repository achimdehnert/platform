---
retro_schema: 1
date: 2026-08-28
repo_scope: [writing-hub, platform]
session_id: 73073b
footprint: full
footprint_reduction_reason: >
  Rule-B-Trigger war `deep` (Prod-Schritte: zwei Diagnose-Sessions auf der Prod-DB,
  Statusaenderung an zwei ChapterWriteJob-Zeilen, neuer Container writing_hub_beat).
  Eine Stufe reduziert, weil alle drei Bedingungen belegt zutrafen: (a) jeder
  Prod-Schritt war einzeln und woertlich freigegeben ("127 freigegeben", "144 go",
  "145 go"); (b) voll rollback-faehig, keine DB-Migration — die Ausgangswerte der
  zwei Jobs wurden vor der Aenderung gesichert und im Transkript festgehalten;
  (c) findings_total-Schaetzung <=10 (real 13, knapp darueber).
findings_total: 13
findings_survived: 10
refuted_rate: 0.23
phase3_refuted: 3
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 2
  entscheidungsqualitaet: 4
gate_candidates:
  - regressionstest-faellt-in-eigene-falle
  - cross-session-nummer-ohne-gegenpruefung
  - session-ende-uebersieht-eigenen-roten-deploy
recurring_findings:
  - claim-before-cheapest-check
  - partial-fix-not-generalized-to-sibling-artifacts
gates_caught:
  - claim-before-cheapest-check
---

# Session-Retro 2026-08-28 — writing-hub

## 1. Executive Summary

- **Der teuerste Fund der Sitzung kam von einem Klick, nicht von einer Analyse.** Sieben
  Hypothesen wurden durch Code-Lesen geprueft und waren alle falsch; der erste echte
  Browser-Klick zeigte die Ursache in der ersten Sekunde (nachgestelltes Komma in einem
  handgebauten JSON-Block, PR #825). Drei Prod-Projekte waren seit dem 2026-08-03
  unbedienbar, ohne dass ein Melder anschlug.
- **Die Sitzung wurde rot geschlossen und hat es nicht gemerkt.** Der Regressionstest aus
  PR #834 — gebaut, um die `asyncio.run`-Falle abzusichern — lief selbst hinein und machte
  `main` rot (CI-Lauf 33167707267). Das Session-Ende meldete „alles live", ohne den
  entstandenen Deploy-Lauf anzusehen. Erst diese Retro fand es.
- **Eine falsche PR-Nummer wurde in fuenf Artefakten und zwei Repos verankert.** Der
  JSON-Fix hiess durchgaengig `#820` — das ist ein fremder PR aus einer Parallelsitzung.
  Drei Finder fanden es unabhaengig voneinander.
- **Drei Selbstanklagen wurden vom Skeptiker widerlegt.** Die Entscheidungen waren besser
  als die eigene Kritik: `alert()` korrekt ausgenommen, PR #818 eigenstaendig wertvoll,
  die `ProjectPhaseExecution`-Ausnahme notwendig statt ueberfluessig.
- **Zwei echte Maengel im neuen Dialog ueberlebten die Falsifikation** — fehlende
  Fokus-Falle und ein Promise, das bei Mehrfach-Oeffnung fuer immer haengt. Der zweite
  erzeugt genau die Symptomatik, gegen die der Dialog gebaut wurde.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Regressionstest aus #834 ruft selbst `asyncio.run` auf oberster Ebene; `main` rot, Sitzung rot geschlossen | fehlende Validierung | **hoch** | SURVIVES | CI-Run 33167707267, `tests/test_research_llm_via_aifw.py` | `claim-before-cheapest-check` |
| 2 | JSON-Fix durchgaengig als `#820` bezeichnet — das ist ein fremder PR (`chore(ci): shared-ci Pin`); korrekt sind #825 (Fix) und #817 (Befund) | Kommunikation | **hoch** | SURVIVES | `gh pr view 820` vs. `825`; 5 Fundstellen in writing-hub + platform#2398-Body | neu |
| 3 | `templates/outlines/outline_detail.html:421-430` baut weiterhin JSON von Hand mit `escapejs` — dieselbe Bauform, die #825 als Fehlerklasse ersetzt hat | Wissensluecke | **hoch** | SURVIVES | `git grep 'type="application/json"' origin/main -- templates/` | `partial-fix-not-generalized-to-sibling-artifacts` |
| 4 | DOM-Dialog ohne Fokus-Falle: nur `Escape`/`Enter` behandelt, kein `Tab`, kein `inert`, kein `<dialog>` | fehlende Validierung | mittel | SURVIVES | `templates/base.html:285-294`, `static/css/app.css:255-265` | neu |
| 5 | `oeffnen()` prueft nicht auf bereits offenen Dialog; zweiter Aufruf laesst das erste Promise **fuer immer** haengen — real erreichbar per Tab auf einen zweiten, ungesperrten Trigger | fehlende Validierung | mittel | SURVIVES | `templates/base.html:253-274`; `chapter_writer.html:634-636,851-853` | neu |
| 6 | Merge von #832 machte `main` rot (xdist-Verteilung verschob einen reihenfolgeabhaengigen Test) | fehlende Validierung | mittel | SURVIVES | CI-Run 33160602123, Commit `42fab2b` | neu |
| 7 | Handover schreibt „Sieben PRs" und zaehlt acht auf | fehlende Validierung | mittel | SURVIVES | `AGENT_HANDOVER.md` (origin/main, Stand 2026-08-28) | neu |
| 8 | Fristen 6h/24h in `wartezustand.py` ungemessen gewaehlt — der Kommentar fordert selbst eine Messung | verfruehte Festlegung | niedrig | SURVIVES | `apps/core/wartezustand.py:30-39` | neu |
| 9 | Zielzustand: 1 von 4 Board-Punkten geliefert (12/13/15 nicht angefasst) | verfruehte Festlegung | niedrig | SURVIVES | `AGENT_HANDOVER.md` Abnahme-Tabelle; platform#2391/#2389 `OPEN` | neu |
| 10 | Beat-Zeitplan nur in `docker-compose.prod.yml`, nicht in dev/staging — dort altern Wartezustaende weiter unbegrenzt | Prozessluecke | niedrig | SURVIVES | `docker-compose.yml`, `.staging.yml`; `tests/test_alterung_ist_verdrahtet.py:56` | neu |
| 11 | `alert()` an 8 Stellen nicht ersetzt — angeblich unbegruendete Luecke | verfruehte Festlegung | mittel | **REFUTED** | `chapter_writer.html:544-546,549-550,768,770` · `editing.html:136` · `review.html:132` · `publishing.html:349,351` — 6 Guard-Klauseln mit unbedingtem `return`, 2 Meldungen nach abgeschlossenem Fetch. Kein Aufruf prueft einen Rueckgabewert, Unterdrueckung aendert den Kontrollfluss nie. | — |
| 12 | #818 wurde 2h14min nach #825 mit einer widerlegten Kausalbehauptung gemergt | verfruehte Festlegung | mittel | **REFUTED** | #818s Body behauptet **keine** Exklusivitaet; der `confirm()`-Defekt ist real, unabhaengig gemessen und klassenweit ueber 10 Aufrufstellen behoben. Zwei unabhaengige Fehler teilten ein Symptomfenster. | — |
| 13 | `ProjectPhaseExecution`-Ausnahme fuer ein totes Modell geschrieben | Wissensluecke | mittel | **REFUTED** | Die Zaehlung stimmt (kein Aufrufer ausser Admin/Migration), aber sie ist die **Begruendung** der Ausnahme, nicht ihr Widerlegung: ohne sie faellt `test_should_give_every_waiting_state_a_deadline_or_a_reason` bei **jedem** Lauf, weil die Registry-Sonde das Modell findet. | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **3** | Recherche-Teil des Zielzustands erreicht und im Browser belegt; von vier Board-Punkten einer geliefert. Drei ungeplante Prod-Defekte behoben — hoher Wert, aber am Ziel vorbei (#9). |
| architektur_design | **3** | `json_script` statt Handarbeit und die zentrale Wartezustands-Registry sind der richtige Schnitt (Klasse statt Symptom, von zwei Skeptikern bestaetigt: #12, #13). Abzug fuer den unvollstaendigen Sweep (#3) und zwei Dialog-Maengel (#4, #5). |
| code_konventionstreue | **3** | Tests durchgaengig mit Positivkontrolle und Gegenprobe, Gates per AST statt grep, `ruff` gruen. Abzug fuer eine falsche Referenznummer in fuenf Artefakten (#2) und einen Zaehlfehler (#7). |
| risiko_debt | **2** | `main` rot hinterlassen und nicht bemerkt (#1); zwei rote Deploys (#1, #6); zwei bekannte Dialog-Maengel ungefixt (#4, #5); die Fehlerklasse aus #825 steht weiter in einem zweiten Template (#3). |
| prozess_effizienz | **2** | Sieben widerlegte Hypothesen aus Code-Analyse, bevor der erste Klick erfolgte (#1-Wurzel). Neun PRs an zwei Tagen, zwei davon rot auf `main`. |
| entscheidungsqualitaet | **4** | Drei von fuenf Bewertungsbefunden wurden zugunsten der getroffenen Entscheidungen widerlegt (#11, #12, #13) — die Selbstkritik war strenger als die Sachlage. Die Owner-Weisung wurde org-weit verankert statt lokal notiert. |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Regressionstest nutzt `asyncio.run`, um eine `asyncio.run`-Falle abzusichern; lokal gruen, CI rot (Run 33167707267) | Ein Test, der eine Falle absichert, wird **gegen dieselbe Falle** ausgefuehrt: der aeussere Aufruf nutzt dieselbe Schutzfunktion wie der innere. Beweis in beide Richtungen im selben Lauf. | #1 |
| Referenznummer aus dem Gespraechskontext in Code, Tests, Handover und ein zweites Repo geschrieben | Vor der ersten Verwendung einer `#N`-Referenz **einmal** `gh pr view N --json title` — die Ausgabe muss zum Gegenstand passen. Bei Parallelsitzungen im selben Repo ist die naechste freie Nummer nie die eigene. | #2 |
| `chapter_writer.html` auf `json_script` umgestellt, `outline_detail.html` mit derselben Bauform blieb stehen | Beim Beheben einer Fehlerklasse **zuerst** die Geschwisterstellen zaehlen (`git grep` auf das Muster), dann entscheiden: alle mitnehmen oder die Restliste als Issue anlegen. Kein PR, der eine Klasse benennt und eine Instanz behebt. | #3 |
| Dialog mit `role="dialog"` und `aria-modal`, aber ohne Fokus-Behandlung | Ein selbstgebauter modaler Dialog bekommt eine Fokus-Falle (Tab-Zyklus zwischen den Knoepfen) oder das native `<dialog>`-Element mit `showModal()`. `aria-modal` allein ist eine Behauptung, keine Kontrolle. | #4 |
| `oeffnen()` ohne Guard; zweiter Aufruf haengt das erste Promise auf | Eine Funktion, die ein Promise ueber globalen Zustand aufloest, prueft als erstes, ob dieser Zustand belegt ist — und loest das alte Promise ab (mit `false`), bevor sie es ersetzt. | #5 |
| PR-CI gruen, `main`-CI rot; die Verteilung aendert sich mit der Testanzahl | Nach jedem Merge in ein Repo mit Deploy-on-main **den entstandenen main-Lauf** ansehen, nicht nur den PR-Status. Das ist ein Blick, kein Prozess. | #6 |
| „Sieben PRs" geschrieben, acht aufgezaehlt | Zahlwoerter vor Aufzaehlungen im Abschlussdokument gegen die Liste zaehlen — oder weglassen. Eine Zahl, die nicht traegt, entwertet den Rest des Absatzes. | #7 |
| Fristen 6h/24h gewaehlt, waehrend der eigene Kommentar eine Messung fordert | Entweder die realen Laufzeiten einmal messen (`max(updated_at - created_at)` ueber die `done`-Zeilen) und die Frist daraus ableiten, oder den Wert ausdruecklich als vorlaeufig markieren — nicht beides im selben Kommentar behaupten. | #8 |
| Zielzustand von drei Prod-Klick-Befunden verdraengt, ohne Neuverhandlung | Wenn ein ungeplanter Prod-Defekt den Zielzustand verdraengt, den Zielzustand **im selben Zug** neu aushandeln (ein Satz an den Owner), statt ihn am Ende als „teilweise erreicht" zu berichten. | #9 |
| Beat-Dienst nur in der Prod-Compose | Ein wiederkehrender Lauf, der einen Datenzustand korrigiert, gehoert in **jede** Umgebung, die diesen Zustand erzeugt — oder die Auslassung bekommt eine Zeile im Test, die sagt warum. | #10 |

## 5. Laengsschnitt

`python3 tools/retro_kpis.py` (Lauf 2026-08-28): 39 Slugs mit Zaehler >=2 sind
gate-pflichtig, davon **13 ohne registriertes Gate**. Score-Mittel ueber 100 Retros:
`risiko_debt` bleibt mit **2,53** die schwaechste Dimension — diese Sitzung liegt mit
**2** darunter und bestaetigt den Trend statt ihn zu brechen.

Drei Slugs dieser Sitzung sind Wiederholungen:

- **`claim-before-cheapest-check`** — Befund #1. Der Stop-Hook hat in dieser Sitzung
  **zweimal gefeuert** und beide Male einen ungedeckten Claim abgefangen („funktioniert
  wieder" vor dem Deploy; „CI laeuft" ungeprueft). Deshalb steht der Slug in
  `gates_caught`: das Gate hat gearbeitet. Es hat nur nicht gefangen, was **kein**
  formulierter Claim war — den nicht angesehenen main-Lauf.
- **`partial-fix-not-generalized-to-sibling-artifacts`** — Befund #3. Steht laut
  `retro_kpis.py` bei 8 Vorkommen und hat **kein** registriertes Gate.
`deferred-item-no-tracking-issue` wurde **bewusst nicht** als `recurring_finding`
gefuehrt: die einzige aufgeschobene Arbeit dieser Sitzung (#819 Herkunfts-Befund) bekam
im selben Zug Issue #827. Ein Slug im Frontmatter ohne zugehoerige Befund-Zeile wuerde
den Cross-Retro-Zaehler mit einem unbelegten Vorkommen fuettern — genau die Dekoration,
vor der die Skill warnt.

## 5a. Rueckfall-Pruefung

`python3 tools/gate_wirkung.py` (Lauf 2026-08-28) meldet **drei rueckfaellige Gates**:

| Gate | vor Bau | nach Bau | letzter Rueckfall |
|---|---|---|---|
| `deferred-item-no-tracking-issue` | 24 | 5 | 2026-08-28 |
| `untested-command-handed-to-user` | 1 | 2 | 2026-08-28 |
| `untested-tool-module-green-gate` | 6 | 2 | 2026-08-25 |

**Keiner der drei ist dieser Sitzung zuzurechnen** — geprueft: die aufgeschobene Arbeit
trug ihr Issue (#827); der einzige an den Owner gegebene Befehl
(`manage.py altere_wartezustaende --trocken`) wurde vor der Nennung selbst ausgefuehrt
und danach vom Agenten durchgefuehrt, nicht dem Owner ueberlassen.

**Korrektur nach dem Meta-Review:** Der erste Entwurf dieses Abschnitts erfand eine
**vierte** Antwort („Zuordnung zur Parallelsitzung") auf einen Gate-Rueckfall. Die Skill
laesst genau drei zu und sagt ausdruecklich: „Ein vierter Weg… ist ausdrücklich keiner."
Der Fehler lag eine Stufe frueher: `deferred-item-no-tracking-issue` haette gar nicht
erst als `recurring_finding` dieser Sitzung gefuehrt werden duerfen, weil kein Befund
dieser Sitzung ihn belegt. Ohne den Frontmatter-Eintrag entfaellt der Trigger von Regel
5a — und die Frage nach der Antwort stellt sich nicht.

**Was daraus bleibt, ist ein Befund ueber die Zuordnung, nicht ueber das Gate:**
`gate_wirkung.py` datiert Rueckfaelle auf den Tag, nicht auf die Sitzung. An einem Tag
mit zwei parallelen Sitzungen im selben Repo kann es einen Rueckfall der einen der
anderen zurechnen. Das ist ein Werkzeug-Befund und gehoert als solcher gemeldet
(Massnahme #14), nicht als Ausweichantwort auf Regel 5a.

**Ehrlichkeits-Sperre beachtet:** fuenf Gates stehen auf `zu-frueh` und eines auf
`unerprobt` — das sind keine Wirksamkeits-Belege und werden hier nicht als solche
gefuehrt.

## 5b. Autonomie-Kalibrierung

- **`over_ask: 0`** — Kein deterministischer, reversibler Schritt wurde unnoetig
  vorgelegt. Die vier Vorlagen (Diagnose-Session ×2, Altjobs altern, Beat verdrahten)
  waren alle Prod-Zustandsaenderungen und damit Gate 2.
- **`over_act: 0`** — Kein Gate wurde autonom ueberschritten. Der blockierte Versuch,
  eine Prod-Session ohne Freigabe anzulegen, wurde vom Classifier abgefangen **und nicht
  umgangen**; die Freigabe wurde stattdessen eingeholt.

## 6. Verankerung (Vorschlaege — nicht selbst geschrieben)

### memory_candidates

```markdown
---
name: drift-regressionstest-faellt-in-eigene-falle
description: Ein Test, der eine Falle absichert, darf sie nicht selbst enthalten — asyncio.run im Regressionstest gegen asyncio.run
metadata:
  type: feedback
drift: true
drift_episode: 2026-08-28-regressionstest-eigene-falle
---

Der Regressionstest zu einem `asyncio.run`-Fehler rief selbst `asyncio.run` auf oberster
Ebene auf. Lokal gruen, unter `pytest-xdist` rot — mit exakt dem Fehler, den er absichern
sollte. `main` blieb rot, und die Sitzung wurde geschlossen, ohne den entstandenen
Deploy-Lauf anzusehen (CI-Run 33167707267, 2026-08-28).

**Why:** „Gegenprobe gemessen" hiess hier „lokal gemessen". Der Beweis lief in einer
Umgebung, in der die Falle nicht zuschnappen kann — er belegte damit nichts ueber die
Umgebung, in der sie zuschnappt.

**How to apply:** Ein Test, der eine Fehlerklasse absichert, wird **gegen dieselbe Klasse**
ausgefuehrt: der aeussere Rahmen nutzt dieselbe Schutzfunktion wie der innere Fall. Und
nach jedem Merge in ein Deploy-on-main-Repo den **entstandenen main-Lauf** ansehen —
ein PR-gruen ist keine Aussage ueber main. Verwandt: [[gate-claim-before-cheapest-check]].
```

```markdown
---
name: drift-nummer-aus-dem-kontext-statt-aus-github
description: Bei Parallelsitzungen im selben Repo gehoert jede #N-Referenz einmal gegen `gh pr view` geprueft
metadata:
  type: feedback
drift: true
drift_episode: 2026-08-28-fremde-pr-nummer
---

Der JSON-Fix wurde durchgaengig als `#820` bezeichnet — in zwei Code-Kommentaren, zwei
Testmodulen, dem Handover und einem PR-Body in einem **zweiten Repo**. `#820` gehoert
einer Parallelsitzung (`chore(ci): shared-ci Pin`); der Fix ist #825, der Befund #817.
Auf GitHub verlinkte jede Referenz auf die falsche Sache.

**Why:** Die Nummer stammte aus dem Gespraechskontext, nicht aus GitHub. Bei
Parallelsitzungen im selben Repo ist die naechste freie Nummer nie die eigene — zwischen
Issue-Anlage und PR-Erstellung vergibt die andere Sitzung Nummern.

**How to apply:** Vor der **ersten** Verwendung einer `#N`-Referenz in einem dauerhaften
Artefakt einmal `gh pr view N --json title` bzw. `gh issue view N` — der Titel muss zum
Gegenstand passen. Drei unabhaengige Retro-Finder fanden diesen Fehler; keiner der
Schreibvorgaenge hatte ihn bemerkt.
```

### adr_candidates

Keine. Kein Befund erreicht die ADR-Schwelle (`policies/adr-threshold.md`): alle
Aenderungen folgen bestehenden Mustern, sind repo-lokal und reversibel.

## 7. Massnahmen

### 🔵 Offen — ich kann sofort

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Roter `main` behoben | writing-hub | #836 | 🟡 | mergen bei gruenem CI (ich) |
| 3 | `outline_detail.html` sweepen | writing-hub | — | 🔵 | Issue anlegen (ich) |
| 4+5 | Dialog: Fokus-Falle + Doppel-Guard | writing-hub | — | 🔵 | Issue anlegen (ich) |

### 🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 8 | Fristen messen statt schaetzen | writing-hub | — | 🟢 | entscheiden: messen oder vorlaeufig lassen |
| 14 | `gate_wirkung.py` datiert Rueckfaelle auf den Tag, nicht die Sitzung | platform | — | 🟢 | entscheiden: Sitzungs-ID mitfuehren oder bewusst tagesgenau lassen |
| 10 | Beat in dev/staging | writing-hub | — | 🟢 | entscheiden: noetig oder bewusst nur Prod |

### ✅ Erledigt in dieser Retro

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Regressionstest aus der Falle geholt | writing-hub | #836 | ✅ | — |
| 2 | Falsche PR-Nummer in 5 Artefakten korrigiert | writing-hub | #836 | ✅ | — |
| 7 | Zaehlfehler im Handover korrigiert | writing-hub | #836 | ✅ | — |

## 8. Nicht verifiziert (Restluecken)

| Was offen blieb | Billigster Check |
|---|---|
| `verankerung_pruefer.py` (session-ende Phase 0g) lief in Timeouts — kein Modell erreichbar. Die Zusagen wurden **von Hand** gegengeprueft (#819 → Issue #827; #831 → beide Prod-Schritte in derselben Sitzung erledigt), nicht maschinell. | `ollama` starten, dann `python3 platform/tools/verankerung_pruefer.py --pr 819 --repo achimdehnert/writing-hub` |
| Befund #2 nennt platform#2398 als betroffen — die Korrektur dort ist **nicht** erfolgt (nur writing-hub wurde korrigiert). | `gh pr view 2398 --repo achimdehnert/platform --json body \| grep -c '820'` |
| Ob die zwei Gate-Rueckfaelle vom 2026-08-28 wirklich der Parallelsitzung gehoeren, wurde aus der Abwesenheit eigener Verstoesse geschlossen, nicht positiv der anderen Sitzung zugeordnet. Das ist eine Absenz-Behauptung ohne zweiten Suchpfad. | `python3 platform/tools/befund_journal.py --bericht` und die Slugs gegen die Retro der Parallelsitzung halten |
| Befund #6 (xdist-Verteilung) hat keinen Regressionsschutz — es gibt keinen Test, der reihenfolgeabhaengige Tests als Klasse findet. | `pytest -p no:randomly --collect-only` gegen eine erzwungene Umkehrung der Reihenfolge |
| Der Dialog-Doppelaufruf (#5) wurde vom Skeptiker als „real erreichbar" beurteilt, aber **nicht im Browser ausgeloest**. | Playwright: Dialog oeffnen, per Tab auf `btn-research-all`, Enter — haengt der erste `await`? |

**Vierer:** *getan* — 9 PRs gemergt, drei Prod-Defekte behoben, zwei Prod-Schritte
ausgefuehrt und gegengeprueft, Owner-Weisung org-weit verankert. *angenommen* — dass die
zwei Gate-Rueckfaelle der Parallelsitzung gehoeren. *nicht verifizierbar* — die
Verankerungspruefung ohne laufendes Modell. *offen geblieben* — Board-Punkte 12/13/15,
der zweite JSON-Bauplatz, beide Dialog-Maengel, platform#2398.
