---
retro_schema: 1
date: 2026-07-08
repo_scope: [iil-voice-agent]
session_id: 733182
footprint: lean
footprint_reduction_reason: "1 PR (#62), 1 Repo, kein Prod/Migration/ADR — Standard-Lean-Trigger, keine Downscale von deep/full nötig"
findings_total: 2
findings_survived: 2
refuted_rate: 0.0
phase3_refuted: 0
pre_refuted: 0
scores:
  zielerreichung: 5
  architektur_design: 5
  code_konventionstreue: 5
  risiko_debt: 4
  prozess_effizienz: 3
  entscheidungsqualitaet: 5
gate_candidates: []
recurring_findings: [main-tree-dirty-edit-window-uncaught-by-guard]
---

# Session-Retro — iil-voice-agent (Faithfulness-Judge-Fix, Prio 3) · 2026-07-08

_Lean-Footprint (1 Repo, 1 PR, kein Prod/Migration/ADR). Inline-Review (0 Subagenten, wie für
`lean` vorgesehen) — Befunde gegen `gh`/`git`-Artefakte verifiziert, nicht aus Session-Erzählung
übernommen. 2 Befunde, 2 SURVIVES, 0 REFUTED._

## 1. Executive Summary

- **Kernauftrag erfüllt und empirisch verifiziert, nicht nur behauptet:** die Session sollte die
  Faithfulness-Judge-Analyse (Handover-Prio 3) in konkrete `_EXTRACT_SYSTEM`/`_VERIFY_SYSTEM`-Fixes
  überführen. [PR #62](https://github.com/iilgmbh/iil-voice-agent/pull/62) liefert das: 12
  Claim-Verdicts wurden einzeln durchgesehen, ein reproduzierbarer Bug (isolierte Zeit-Behauptung
  verliert den Kontext-Zusammenhang) gefixt und **live gegen Groq neu verifiziert** — nicht nur
  ruff/pytest-grün behauptet (Gate `claim-before-cheapest-check` korrekt angewendet).
- **Ein Fix-Versuch scheiterte live und wurde ehrlich verworfen statt geshippt:** eine explizite
  Meta-Hedge-Ausschluss-Instruktion trieb das Spar-Modell (`llama-3.1-8b-instant`) in eine
  ~90-Zeilen-Wiederholungsschleife erfundener Negations-Claims (Score-Kollaps eines Items auf 3%).
  Statt die Instruktion nur umzuformulieren, wurde sie zurückgesetzt und durch einen **deterministischen
  Code-Deckel** (max. 8 Claims + Exact-Dedup) ersetzt, der unabhängig von Prompt-Gehorsam greift.
  Das ist genau das in der Evidenz-Policy geforderte Verhalten (Gegenbeispiel prüfen, bevor ein
  Claim/Fix steht) — als Positiv-Befund festgehalten, nicht nur als Kritikpunkt gesucht.
- **Prozess-Lapsus, selbst erkannt und behoben, aber real:** der allererste Edit-Aufruf traf die
  Quelldatei direkt im geteilten Haupt-Tree (`main`), nicht in einem Worktree — ein Verstoß gegen
  ADR-233/CLAUDE.md, erst nachträglich per `git branch --show-current` bemerkt, dann per Stash +
  `repo-session.sh` sauber in einen Worktree überführt. Kein Schaden (kein Commit auf main), aber
  der Umweg war vermeidbar. **Dies deckt eine reale Lücke im bestehenden Guard auf** (s. Befund 1).
- **PR #62 blieb offen, obwohl CI (test+CodeQL) durchgehend grün und `mergeable=MERGEABLE` ist** —
  in Sessions 2–11 dieses Repos war grünes CI + kein Prod-Bezug wiederholt der Auslöser für Self-Merge.
  Kein Fehler (MVP-Scaffold, kein Auto-Deploy-Risiko), aber eine Abweichung vom etablierten Muster,
  die hier ohne Begründung passierte.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Erster Edit-Aufruf der Session traf `src/voice_agent/eval/faithfulness.py` direkt im geteilten Haupt-Tree (Branch `main`), nicht in einem `repo-session`-Worktree — Verstoß gegen ADR-233/CLAUDE.md "Editieren nur via Worktree". Selbst bemerkt (`git branch --show-current` → `main`), per `git stash` + neuem Worktree korrigiert, **bevor** ein Commit erfolgte. Der installierte `main-tree-guard` (pre-commit-Hook + post-checkout-Snapback) hätte einen Commit auf main geblockt — deckt aber **keine** Edit-Time-Lücke: eine dirty, uncommittete Datei kann beliebig lange auf dem geteilten Tree liegen, sichtbar für jede parallele Session, ohne dass Tooling das erkennt. | Prozesslücke / Werkzeug-Lücke | mittel | SURVIVES | `git -C ~/github/iil-voice-agent branch --show-current` → `main` zum Zeitpunkt des Edits (Tool-Aufruf-Protokoll dieser Session); `ls ~/github/iil-voice-agent/.git/hooks/{pre-commit,post-checkout}` bestätigt Guard installiert, deckt aber nur Commit-/Checkout-Zeitpunkt, nicht Edit-Zeitpunkt | main-tree-dirty-edit-window-uncaught-by-guard (verwandt, aber technisch verschieden von `main-tree-guard-recurring-incident` aus `session-retro-2026-07-06-iil-klickdummy-2752dc.md` — dort griff der Guard bei einem `checkout`-Versuch; hier gab es gar keinen Checkout-Versuch, nur einen ungeschützten Edit-Call, den der Guard architektonisch nicht abdeckt) |
| 2 | [PR #62](https://github.com/iilgmbh/iil-voice-agent/pull/62) blieb am Sitzungsende **offen** (state=OPEN, mergeable=MERGEABLE, CI test+CodeQL beide SUCCESS), obwohl dieses Repo in den Sessions 2–11 laut `AGENT_HANDOVER.md` durchgehend grüne, unkritische PRs selbst gemergt hat (keine Required-Reviews/-Checks, bewusst um den Solo-Workflow nicht zu bremsen) und dieser PR keinen Prod-/Deploy-Bezug hat (Repo-Status weiterhin "idea/MVP-Scaffold"). Kein Policy-Verstoß (kein Gate betroffen), aber unbegründete Abweichung vom etablierten Muster dieses Repos. | Prozesskonvention | niedrig | SURVIVES | `gh pr view 62 -R iilgmbh/iil-voice-agent --json state,mergeable,statusCheckRollup` → `state=OPEN`, `mergeable=MERGEABLE`, alle 3 Checks `SUCCESS`; `AGENT_HANDOVER.md` Sessions 3/4/6/7/9 zeigen wiederholt "GEMERGT" für vergleichbare grüne PRs | pr-open-despite-established-self-merge-norm (1. Vorkommen, neuer Slug) |

**REFUTED:** keine — beide Befunde direkt artefakt-verifiziert (gh/git-Ausgabe oben), kein
Widerspruch zwischen Session-Erzählung und Ground Truth gefunden.

## 3. Scorecard (1–5, an Befunden verankert)

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **5** | Handover-Prio-3-Auftrag ("konkrete Fixes für die Prompts") vollständig erfüllt + live verifiziert; PR CI-grün |
| architektur_design | **5** | Minimal-invasiver Fix (Prompt-Text + ein Code-Deckel), kein Scope-Creep in Core/Ports (ADR-249 G-1 unberührt) |
| code_konventionstreue | **5** | 2 neue `test_should_*`-Tests, ruff clean, Commit-Message-Konvention eingehalten |
| risiko_debt | **4** | Kernrisiko (Judge-Instabilität 58–68 % über Wiederholungsläufe) bleibt offen, aber **ehrlich dokumentiert** statt verschleiert — kein neues, unbekanntes Risiko eingeführt |
| prozess_effizienz | **3** | Befund 1 (Main-Tree-Edit-Umweg: Stash+Worktree-Nacharbeit) + Befund 2 (PR offen gelassen ohne Begründung) — beides vermeidbarer Zusatzaufwand, kein Schaden |
| entscheidungsqualitaet | **5** | Backfiring Hedge-Instruktion sauber verworfen statt kosmetisch umformuliert; Code-Deckel statt weiterer Prompt-Iteration als robusterer Fix gewählt |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Erster `Edit`-Tool-Call traf die Quelldatei direkt im geteilten Haupt-Tree (`main`); Korrektur erst nachträglich via `git branch --show-current`, nachdem bereits ein Testlauf + vier Live-Eval-Läufe auf dem dirty main-Tree liefen | Vor dem **allerersten** Edit an einer Quelldatei in einem worktree-pflichtigen Repo: `repo-session.sh start` ausführen und in den Worktree wechseln, **bevor** überhaupt ein Edit-Tool-Call erfolgt — nicht erst wenn bereits Tests/Live-Läufe gegen den dirty Main-Tree liefen. Zusätzlich: `main-tree-guard.sh` um eine **freiwillige Edit-Time-Warnung** ergänzen (z. B. Claude-seitige Selbstprüfung "bin ich in einem Worktree?" vor dem ersten Edit), da der bestehende Guard Edit-Time strukturell nicht abdeckt | #1 |
| PR #62 blieb nach bestätigt grünem CI (test+CodeQL SUCCESS, mergeable) ohne Begründung offen, obwohl dieses Repo in Sessions 2–11 durchgehend vergleichbare PRs selbst gemergt hat | Nach bestätigt grünem CI + erkennbarem Solo-Merge-Präzedenzfall im selben Repo: PR selbst mergen **oder** im Abschlussbericht explizit begründen, warum diesmal nicht (z. B. "überlasse Merge-Entscheidung dem Menschen, weil …") statt sie kommentarlos offen zu lassen | #2 |

## 5. Längsschnitt

`retro_kpis.py`-Lauf gegen alle `platform/docs/retros/session-retro-*.md`:

- `main-tree-dirty-edit-window-uncaught-by-guard`: **1. Vorkommen** dieses spezifischen Slugs
  (verwandter, aber technisch unterschiedlicher Vorgänger: `main-tree-guard-recurring-incident`,
  3× repo-lokal in `iil-klickdummy` — dort griff der Guard bei einem `checkout`-Versuch; hier lag
  kein Checkout-Versuch vor, nur ein ungeschützter Edit-Call). Kein Gate-Zwang bei Vorkommen 1,
  aber die Verwandtschaft zu einem bereits 3× aufgetretenen Muster ist ein Frühwarnsignal — bei
  einem 2. Vorkommen dieses *neuen* Slugs oder einem 4. Vorkommen der *Familie* insgesamt wird
  ein ADR-233-Amendment (Edit-Time-Warnung) Gate-pflichtig.
- `pr-open-despite-established-self-merge-norm`: 1. Vorkommen, neuer Slug — keine Gate-Pflicht.

(Live-`retro_kpis.py`-Ausgabe wird beim Commit dieses Reports als Kommentar mitgeführt, s. u.)

## 6. Verankerung — Vorschläge (Mensch entscheidet)

**memory_candidates** (an `iil-voice-agent`-Auto-Memory, Typ `feedback`):

```yaml
name: worktree-before-first-edit-not-after
description: Vor dem allerersten Edit in einem worktree-pflichtigen Repo IMMER repo-session.sh
  starten — nicht erst nach dem ersten Edit-Call per git-branch-Check nachträglich korrigieren.
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-08-faithfulness-main-tree-edit
```
Body: Der main-tree-guard (pre-commit + post-checkout) deckt Commit-/Checkout-Zeitpunkt ab, NICHT
den Moment des ersten Edit-Tool-Calls. Ein Edit auf `main` bleibt bis zum nächsten `git status`-
Check unbemerkt dirty auf dem geteilten Tree liegen. Fix: `git branch --show-current` **vor** dem
ersten Edit-Tool-Call einer Session prüfen, nicht erst danach. Verwandt: `adr-233-guard-is-live`.

**adr_candidates:** keins — dies ist ein Tooling-Lücke-Hinweis (Edit-Time-Warnung), kein
Architektur-Entscheid; passt eher als Ergänzung zu `main-tree-guard.sh` (platform-Tool) denn als
neues ADR.

## 7. Maßnahmen (Action Board)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | PR #62 mergen (CI grün, mergeable, kein Prod-Bezug) | iil-voice-agent | [PR #62](https://github.com/iilgmbh/iil-voice-agent/pull/62) | 🔵 ready | du/ich: mergen, dann `AGENT_HANDOVER.md` Session-12-Eintrag nachziehen |
| 2 | Redundanter Stash `stash@{0}` im iil-voice-agent-Haupt-Tree aufräumen (Fix bereits committed+gepusht in Worktree/PR #62) | iil-voice-agent | — | 🟢 dein Zug | du: `git stash drop stash@{0}` (Classifier blockte Agent-Drop) |
| 3 | Judge-Instabilität (58–68 % Score-Schwankung bei identischem Input) — braucht entkoppeltes/stärkeres Judge-Modell oder deterministische Vorfilterung statt Prompt-Instruktion | iil-voice-agent | PR #62 (Restbefund dokumentiert) | 🟢 dein Zug | du/Opus: Architektur-Entscheid, welcher Pfad (stärkeres Modell vs. Code-Filter) |
| 4 | `main-tree-guard.sh` um Edit-Time-Hinweis ergänzen (Lücke aus Befund 1) | platform | — | 🟢 dein Zug | du: entscheiden ob Tooling-Erweiterung gewünscht (Aufwand vs. Nutzen bei bisher 1. Vorkommen dieses Slugs) |

## 8. Nicht verifiziert (Restlücken)

- Ob PR #62 inhaltlich korrekt gegen den *echten* Fachseite-Günzburg- oder Produktions-E-Mail-Korpus
  (statt des synthetischen `EMAILTHREAD_CORPUS`) wirkt, wurde nicht erneut geprüft — Scope dieser
  Session war ausdrücklich der bestehende Faithfulness-Testdatensatz.
- Der in `AGENT_HANDOVER.md` referenzierte Report `docs/retros/session-retro-2026-07-06-iil-voice-agent-9206ac.md`
  existiert nicht im lokalen `platform`-Hauptzweig, sondern nur als offener PR
  ([#976](https://github.com/achimdehnert/platform/pull/976)) — nicht in dieser Session geprüft/
  gefixt (Increment-Retro-Regel: nur neue Artefakte dieser Session sind in Scope), nur als Randnotiz
  festgehalten. Billigster Check bei Bedarf: `gh pr view 976 -R achimdehnert/platform`.
