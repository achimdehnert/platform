---
retro_schema: 1
date: 2026-10-05
repo_scope: [platform, shared-ci]
session_id: 728cf0
footprint: full
findings_total: 15
findings_survived: 13
refuted_rate: 0.13
phase3_refuted: 1
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [edit-in-worktree-without-read, repo-datei-per-shell-statt-edit, automatik-ohne-wartezeit]
recurring_findings: [claim-before-cheapest-check, partial-fix-not-generalized-to-sibling-artifacts, handover-stale-vor-merge, edit-in-worktree-without-read]
gates_caught: [direct-gh-pr-merge-bypasses-sa-m]
gates_verwandt: [claim-before-cheapest-check, handover-stale-vor-merge]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "4 gekippt, 1 neu"
streichkandidaten: []
streich_begruendung: "keiner, weil jede gelaufene Phase hier Wirkung hatte: die Kennzahlen trugen #4, die Skeptiker verwarfen #9, die Widerlegungsbahn kippte #11 und fand #15"
---

# Session-Retro 2026-10-05 (Sitzung 728cf098…728cf0)

Scope über die PR- und Issue-Nummern der Sitzung, nicht über das Datum:

- **platform:** Issue #3775 (von der Sitzung geschlossen), PR #3776 (Merge 54cefede).
- **shared-ci:** PR #95 (Merge 8297090), Issue #96, Dependabot-PRs #68, #69 und #70 (gemergt), #91 (Owner-Merge vor dem Kanon-Wechsel), #92 (offen), Tag `v1.1.22` (vom Owner gesetzt).
- **bfagent:** gescheiterter Issue-Versuch, das Repo ist archiviert.

**Footprint `full`:** zwei Repos, kein Prod-Schritt, keine Migration, kein ADR. Ein Tag ist eine Veröffentlichung, die setzte aber der Owner. Agentenbudget: 3 Finder, 2 Skeptiker, 1 Widerlegung und 1 Meta, zusammen 7 (etwa 55k Tokens je Agent).

## 0.0 Wirkungsbilanz

`gate_wirkung.py` meldet drei Gates als RUECKFAELLIG. Für alle drei haben Retros vom selben Tag schon eine der zulässigen Konsequenzen entschieden. Diese Retro übernimmt sie, statt eine zweite Entscheidung daneben zu stellen.

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| handover-stale-vor-merge | 4 | Quelle: E.3 (`prs_nach_fragment`, `tools/sitzungs_branches.py:120`) zählt nur PRs, die nach dem Fragment angelegt wurden, und liest „Offen" nicht | **nachschärfen** nach Vorlage G2 (`docs/governance/gates/vorschlag-rueckfaellige-gates-2026-10-05.md`), wie in Retro `cdfeff` entschieden. Hier verwandt (#3), ergänzt G2 um „Inhalt von Offen" |
| claim-before-cheapest-check | 3 | Quelle: Hook sieht Zustandsbehauptungen im Antworttext, keine Prognosen und keine PR-Texte | **nachschärfen** (Ausweitung am bestehenden Eintrag, platform#2666), wie in Retro `4f385c-incr2` (M5) und `cdfeff`. Hier verwandt (#1) |
| worktree-midsession-accumulation | 2 | Ausgang: Melder zählt aktive Leases vom selben Tag als Stau | **herabstufen**, wie in Retro `4f385c-incr2` (M6). Hier kein Vorkommen (#14 vorab widerlegt) |

## 1. Executive Summary

- Das Ziel ist erreicht. Die sechs Errors `shared-ci-tag-stale` aus #3775 sind weg: Die Messung nach `v1.1.22` ergab 0 Treffer, die Messung vorher 6. Ob die Lösung dauerhaft hält, zeigt erst der erste scharfe Auto-Release-Lauf am 2026-10-06 (shared-ci#96, #12).
- Die schwerste Lücke fand erst die Widerlegungsbahn (#15, #11). Die neue Automatik merget und taggt fremde Action-Releases ohne Wartezeit, und 0.x-Minor-Sprünge (trivy-action v0.36) wertet sie als harmlos. Ein kompromittiertes Upstream-Release wie trivy-action im März 2026 stünde damit am nächsten Morgen in einem Tag. Der Fix liegt als shared-ci#97 zur Durchsicht durch den Owner.
- #2: Die Vorlage für neue Repos und zwei ADRs verwiesen noch auf die eingefrorene platform-Kopie von `_build-docker.yml`. Die Vorlage ist in diesem PR umgestellt, die ADRs sind offen.
- #8: Die Hauptversions-Sprünge von upload-artifact und setup-python stecken in `v1.1.22`. Die lokalen Runner erfüllen die Node-24-Anforderung, Runner auf anderen Hosts sind ungeprüft.
- Die Prozessfehler sind klein und belegt: eine falsche Tag-Prognose an den Owner (#1), dreimal Edit ohne vorheriges Lesen (#4), eine Repo-Datei per Shell geändert (#5).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Dem Owner wurde angekündigt, der erste Auto-Release-Lauf setze `v1.1.22`; das war falsch, weil #95 selbst Nicht-Versionszeilen in den Abstand Tag…main brachte | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | PR-Text #95 „wuerde taggen: v1.1.22 auf f63be8b1"; `git diff --stat v1.1.21 8297090` enthält `tools/auto_release.py` (+647 Zeilen); Korrektur der Sitzung erst nach den Merges. Die Folgeprognose `v1.1.23` kennzeichnete die Sitzung aus eigenem Antrieb, der Hook feuerte um 16:46:56Z auf eine andere Aussage | claim-before-cheapest-check — gates_verwandt: der Stop-Hook prüft Zustandsbehauptungen gegen Werkzeugläufe, eine Prognose über einen künftigen Lauf liegt außerhalb seines Zuschnitts |
| 2 | Teil (c) des Auftrags (bfagent-Umzug) entfiel ohne Anker, und „letzter Aufrufer ist bfagent" war ungeprüft: `docs/templates/ci.yml:59` verweist weiter auf die eingefrorene platform-Kopie, die Nachbarzeilen 46 und 69 schon auf shared-ci | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | `git show origin/main:docs/templates/ci.yml` Z.59 `achimdehnert/platform/.github/workflows/_build-docker.yml@main`; dazu `ADR-021…md:227` und `ADR-022…md:350` mit `…/_build-docker.yml@v1` (Widerlegungsbahn); bfagent `isArchived=true` | partial-fix-not-generalized-to-sibling-artifacts |
| 3 | Der Abschnitt „Offen" im Handover-Fragment nennt drei Punkte, die mit dem Merge des Fragments selbst erledigt waren; die tatsächlich offenen (#96, #92, Vorlage) fehlen | Prozesslücke | niedrig | SURVIVES (kommandobelegt) | `docs/handover.d/2026-10-05T16-45-00Z-728cf098.md` „## Offen"; #3776 gemergt 16:42:10Z, #95 und #68 bis #70 gemergt bis 16:46Z | handover-stale-vor-merge — gates_verwandt: E.3 (`prs_nach_fragment`, `tools/sitzungs_branches.py:120`) zählt nur PRs, die nach dem Fragment angelegt wurden, und prüft den Inhalt von „Offen" nicht; der Stand steht in einem neuen Fragment (`2026-10-05T17-34-10Z-728cf098.md`), weil ein Fragment auf main unveränderlich ist |
| 4 | Drei Edits schlugen fehl mit „File has not been read yet", weil die Dateien nach dem Wechsel in den Worktree nicht neu gelesen wurden | Werkzeug | niedrig | SURVIVES (kommandobelegt) | Transkript 16:14:57Z, 16:15:00Z, 16:15:57Z (`drift_check.py`, Test, `_build-docker.yml`); `kennzahlen.txt` 7 Fehlerläufe | edit-in-worktree-without-read |
| 5 | `tools/auto_release.py` in shared-ci wurde per Python-Heredoc geändert statt per Edit, ein Verstoß gegen die House Rule; die Sitzung meldete es selbst, aber erst nachträglich | Werkzeug | niedrig | SURVIVES (kommandobelegt) | Transkript: `python3 - <<'EOF'` mit `Path("tools/auto_release.py").read_text()` im shared-ci-Worktree | — (neu: repo-datei-per-shell-statt-edit) |
| 6 | Der Schließ-Kommentar zu #3775 nennt ein Vorher-Repo nur als „ein weiteres Repo", und PR #3776 schreibt „18:06" in Ortszeit in einem sonst UTC-datierten Text | Kommunikation | niedrig | SURVIVES (kommandobelegt) | Kommentar zu #3775; PR #3776 Abschnitt „Restschritt"; Fragment übernimmt „um 18:06" | — |
| 7 | PR #3776 nannte den erneuten Probelauf „wird nachgeholt"; er lag beim Owner-Merge (16:42:10Z) noch nicht vor, nachgeholt wurde er um 16:48Z | fehlende Validierung | niedrig | SURVIVES (kommandobelegt) | PR #3776 Abschnitt „Belege"; Lauf 16:48:38Z im Schließ-Kommentar | — |
| 8 | Die Hauptversions-Bumps #69 (upload-artifact 4.6.2 → 7.0.1) und #70 (setup-python → 7.0.0) wurden ohne Beleg der Runner-Kompatibilität gemergt und getaggt; die PR-Checks prüfen nur Syntax, die Releases ab v6 verlangen Node 24 und Runner ≥ 2.327.1 | fehlende Validierung | mittel | SURVIVES | `gh pr checks` #69/#70: nur Validate Syntax, Docker-Actions, Stille Fehlschläge, compose-Auswahl; `_ci-python.yml:104` Default `self-hosted`. Mildernd: Die lokalen Runner haben Version ≥ 2.336 und bringen Node 24 mit (Widerlegungsbahn, nachgemessen). Ungeprüft sind nur Runner auf anderen Hosts. Inputs geprüft, `pip-install` nirgends genutzt; Owner-Wort „A4 go" | — |
| 9 | Dass die Automatik nur Syntax-Checks als Merge-Gate hat, sei nirgends als Kompromiss dokumentiert | verfrühte Festlegung | mittel | REFUTED | PR #95 „Die Checks am Dependabot-PR sind deshalb die einzige Prüfung vor dem Tag"; `auto-release.yml:17-18`; Docstring `auto_release.py:12-21` | — |
| 10 | `offene_dependabot_prs` ruft `gh pr list` ohne `--limit`; ab 31 offenen Dependabot-PRs fallen die übrigen still heraus | fehlende Validierung | niedrig | SURVIVES | `tools/auto_release.py:175-179`; `gh pr list --help`: „default 30" | — |
| 11 | `hauptversion()` wertet bei 0.x nur die Null; ein Minor-Sprung von trivy-action (v0.36 → v0.37), unter 1.0 nach SemVer ein Bruch, würde automatisch gemergt und getaggt | Wissenslücke | mittel | SURVIVES (Phase 3 REFUTED, von der Widerlegungsbahn gekippt) | `_build-docker.yml:118` `aquasecurity/trivy-action@ed142fd… # v0.36.0`; `auto_release.py:62-65` vergleicht nur `split(".")[0]` | — |
| 12 | #3775 wurde geschlossen, bevor der Mechanismus für „dauerhaft" einmal scharf lief; fällt der Lauf aus, meldet ihn nichts automatisch | Prozesslücke | niedrig | SURVIVES | `gh run list --workflow auto-release.yml`: ein Lauf, Event `pull_request`; `auto-release.yml` ohne Failure-Handler; shared-ci#96 offen, nur manueller Rückverweis. Mildernd: der Drift-Check fände wiederkehrende Errors | — |
| 13 | Das Board nannte den Grund für die Owner-Pflicht beim Merge der neuen Automatik, aber nicht die Gegenseite, das Owner-Wort „Approval-Last verringern" (dev-hub#453); die Spannung steht nur im Issue-Text von #3775 | Kommunikation | niedrig | SURVIVES | `mergedBy`: #95 und #68 achimdehnert, #3776 wirdigital; Tag per `!`-Befehl; #3775 nennt die Spannung zu dev-hub#453 | — |
| 14 | Die Sitzungs-Worktrees liegen nach dem Merge noch | Prozesslücke | niedrig | REFUTED (vorab) | Aufräumen ist Schritt des Sitzungsendes, die Lease läuft 7 Tage; die Sitzung ist nicht beendet | — |
| 15 | Die Automatik merget fremde Action-Releases ohne Wartezeit, und vor dem Tag laufen nur Syntax-Checks. Ein kompromittiertes Upstream-Release wäre binnen eines Tages gemergt und getaggt. trivy-action, das `_build-docker.yml` nutzt, war im März 2026 genau so kompromittiert | fehlende Validierung | hoch | SURVIVES (NEU, Widerlegungsbahn) | `git show origin/main:.github/dependabot.yml`: kein `cooldown`; `auto-release.yml` täglich; [GHSA-69fq-xp46-6x23](https://github.com/advisories/GHSA-69fq-xp46-6x23) (critical, 2026-03-24, `aquasecurity/trivy-action`). Dependabots `cooldown` gilt nicht für `github-actions` (GitHub-Doku), darum Wartezeit im Werkzeug: shared-ci#97 | — (neu: automatik-ohne-wartezeit) |

Der Merge-Wächter fing den direkten `gh pr merge 69` ab (16:43:38Z). Das ist ein Beleg für das Gate, kein Befund.

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Kriterium von #3775 gemessen erfüllt (6 → 0); dauerhaft noch Prognose (#12), Vorlage offen (#2) |
| architektur_design | 3 | Kanon folgt ADR-226, Automatik ist fail-closed und mit Head-SHA-Pin; aber ohne Wartezeit (#15) und mit falscher 0.x-Regel (#11) |
| code_konventionstreue | 3 | Heredoc-Edit (#5), `--limit` fehlt (#10) |
| risiko_debt | 2 | Lieferketten-Lücke in einer Automatik mit Tag-Recht (#15, #11); Fix liegt offen, Rework nötig |
| prozess_effizienz | 3 | 7 Fehlerläufe, davon 3 Edit ohne Lesen (#4) und 1 Wächter-Treffer |
| entscheidungsqualitaet | 3 | falsche Tag-Prognose (#1), „letzter Aufrufer" ohne Suche (#2) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Trockenlauf vor dem Merge von #95 als Prognose für den Lauf danach genommen | Eine Prognose über eine Automatik rechnet den eigenen Merge in den Abstand ein: `git diff --stat <tag> <PR-Head>` vor der Ankündigung | #1 |
| „letzter Aufrufer bfagent" aus dem Gedächtnis, (c) entfällt ohne Anker | Vor „eingefroren" alle Verweise suchen: `git grep '<datei>' origin/main` und `gh search code`; jede Fundstelle umstellen oder als Issue verankern | #2 |
| Fragment im selben PR wie der Fix, „Offen" beschreibt den Stand vor dem Merge | Ein Fragment mit Offen-Punkten, die der eigene Merge erledigt, gehört erst nach dem Merge geschrieben, oder es wird beim Sitzungsende ersetzt | #3 |
| Edit im Worktree auf Dateien, die nur im Haupt-Tree gelesen waren | Nach `repo-session.sh start` jede zu ändernde Datei im Worktree-Pfad lesen, bevor der erste Edit läuft | #4 |
| Mehrzeilige Ersetzung per `python3 - <<'EOF'` | Mehrzeilige Ersetzung per Edit mit größerem Kontext oder per Write der ganzen Datei | #5 |
| „ein weiteres Repo", Ortszeit ohne Zone | Vorher-Liste vollständig aus der gespeicherten Ausgabe zitieren; Zeitangaben mit `Z` | #6 |
| PR an den Owner mit „wird nachgeholt" | Ausstehende Belege vor der Übergabe nachholen oder den PR als Entwurf halten, bis sie vorliegen | #7 |
| Hauptversions-Merge nach grünen Syntax-Checks | Vor einem Major-Merge in shared-ci die Release-Notes auf Runner-/Node-Anforderungen prüfen und einen Konsumenten-Lauf gegen den Branch abwarten | #8 |
| `gh pr list` ohne `--limit` | Jede Listen-Abfrage einer Automatik mit explizitem Limit und einem Test für „mehr als die Seite" | #10 |
| „Hauptversion = erste Ziffer" ohne Blick auf die tatsächlich gepinnten Versionen | Vor einer Versionsregel alle Pins mit `git grep 'uses:.*# v0\.'` auflisten und je Klasse einen Gegentest schreiben | #11 |
| Issue zu bei erfülltem Momentkriterium | Den dauerhaften Teil als eigenes Kriterium in das Issue schreiben oder das Issue bis zum ersten scharfen Lauf offen lassen | #12 |
| Board ohne Zielkonflikt-Zeile | Steht eine selbst auferlegte Owner-Pflicht gegen ein Owner-Wort, steht der Konflikt als eine Zeile im Board | #13 |
| Automatik, die fremden Code merget und veröffentlicht, ohne Wartezeit entworfen | Bei jeder Automatik, die Fremd-Releases übernimmt, steht im Entwurf eine Mindest-Wartezeit samt Gegentest, und die Annahme „Dependabot regelt das" wird gegen die Doku geprüft | #15 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (Lauf 2026-10-05, origin/main): 60 Slugs mit Zähler ≥ 2, 6 davon ohne registriertes Gate. Für diese Sitzung:

- `edit-in-worktree-without-read`: in 7 Retros, ohne Gate und ohne `declined`. Das ist **Gate-Pflicht**. Der Vorschlag „Lesen vor Edit" liegt als Owner-Entscheidung in platform#2234. Kein zweites Item, M6 zeigt dorthin.
- `partial-fix-not-generalized-to-sibling-artifacts`: wiederkehrend, aber nicht unter den 6 ungedeckten. Der Einzelfall wird mit M1 in diesem PR geschlossen.
- `claim-before-cheapest-check` und `handover-stale-vor-merge`: als verwandt geführt, s. 5a.
- `repo-datei-per-shell-statt-edit`: erstes Vorkommen. Die Ursache liegt im Werkzeug: Der Auto-Mode-Hinweis der Umgebung lädt ausdrücklich zu Shell-Edits ein, die House Rule verbietet sie für Repo-Dateien. Kandidat, noch keine Gate-Pflicht.

Abgleich mit MEMORY.md: keine Memory zu Edit ohne Lesen und keine zum Heredoc-Verbot gegenüber dem Auto-Mode-Hinweis (`grep -l` im Memory-Verzeichnis).

### 5a. Rückfall-Prüfung

- `claim-before-cheapest-check` (#1): **gates_verwandt**. Das Gate fängt prüfbare Zustandsbehauptungen ohne belegenden Werkzeuglauf. Die falsche Prognose war eine Folgerung über einen künftigen Lauf und stützte sich auf einen echten Trockenlauf. Die Folgeprognose `v1.1.23` hat die Sitzung selbst als Prognose gekennzeichnet. Der Hook feuerte um 16:46:56Z auf eine andere Aussage, deshalb ist das kein Fang des Gates (Widerlegungsbahn).
- `handover-stale-vor-merge` (#3): **gates_verwandt**. E.3 (`prs_nach_fragment`, `tools/sitzungs_branches.py:120`) zählt nur PRs, die nach dem Fragment angelegt wurden, und prüft den Inhalt von „Offen" nicht. Auch beim Sitzungsende hätte E.3 hier bestanden. Der Fall zählt nicht gegen das Gate, zeigt aber eine Lücke in seinem Zuschnitt. Die gehört zu G2 und ist kein neues Gate.
- `direct-gh-pr-merge-bypasses-sa-m`: **gefangen** (16:43:38Z). Beleg für das Gate.

### 5b. Autonomie-Kalibrierung

- `over_ask`: 0. Die eine Rückfrage (shared-ci eigenständig oder mit platform) betraf die Repo-Grenze einer Automatik mit Schreibrecht.
- `over_act`: 0. Die Merges #69 und #70 liefen auf das Owner-Wort „A4 go" mit `OWNER_WORT`-Marker und Head-Pin. Den Tag setzte der Owner selbst. #95 und #3776 mergte nicht die Sitzung.

## 6. Verankerung (Vorschläge, nicht geschrieben)

**memory_candidate** (platform, `feedback`):

```markdown
---
name: auto-mode-erlaubt-keine-shell-edits-an-repo-dateien
description: Der Auto-Mode-Hinweis erlaubt Shell-Edits; die House Rule "Repo-Dateien nur per Edit/Write" hat Vorrang
metadata:
  type: feedback
---
Repo-Dateien werden auch im Auto-Mode nur per Edit/Write geändert, nie per sed, Heredoc oder Python-Skript.
**Why:** Retro 728cf0 #5 — `tools/auto_release.py` per `python3 - <<'EOF'` geändert, weil der Auto-Mode-Hinweis Shell-Edits ausdrücklich anbietet.
**How to apply:** Mehrzeilige Ersetzung per Edit mit mehr Kontext oder per Write der ganzen Datei; Shell-Edits nur im Scratchpad.
```

**gate_candidate** `edit-in-worktree-without-read`: siehe platform#2234 („Lesen vor Edit"), dort Owner-Wort. Nach der Kontext-Kürzung dieser Retro schlugen erneut sieben Edits mit „not read yet" fehl. Das Werkzeug fing sie ab, die Kosten waren je ein Fehlerlauf. Zudem änderte der erste Stand dieses PRs das schon gemergte Fragment 16-45-00Z. Die lokale Fragment-Prüfung bestand (Ursache ungeprüft, Hypothese: Basis-Ref), die CI lehnte ab (Unveränderlichkeit, KONZ-027 L9). Korrigiert durch ein neues Fragment.

**gate_candidate** `automatik-ohne-wartezeit` (#15): erstes Vorkommen, keine Gate-Pflicht. Der Fix steht in shared-ci#97 als Code mit Gegentest.

## 7. Maßnahmen

- **[M1]** ✅ Vorlage auf shared-ci umgestellt · platform · mit dem Retro-PR — https://github.com/achimdehnert/platform/pull/3780
- **[M2]** ✅ Neues Fragment angelegt · platform · mit dem Retro-PR — https://github.com/achimdehnert/platform/pull/3780
- **[M3]** 🟢 Wartezeit, 0.x, Limit · shared-ci · Owner-Review und Merge — https://github.com/iilgmbh/shared-ci/pull/97
- **[M4]** 🔵 Runner anderer Hosts prüfen · shared-ci · Konsumenten-Lauf gegen v1.1.22 — https://github.com/iilgmbh/shared-ci/issues/98
- **[M5]** 🔵 Ersten scharfen Lauf prüfen · shared-ci · 2026-10-06 nach 06:17 UTC — https://github.com/iilgmbh/shared-ci/issues/96
- **[M6]** 🟢 Gate „Lesen vor Edit" · platform · Owner-Wort — https://github.com/achimdehnert/platform/issues/2234
- **[M7]** 🔵 ADR-021/022 auf shared-ci · platform · Folge-PR — https://github.com/achimdehnert/platform/issues/3779

## 8. Nicht verifiziert (Restlücken)

- **Getan:** 3 Finder, 2 Skeptiker auf 6 Bewertungsbefunde, Widerlegungsbahn, Meta.
- **Angenommen:** Der Owner-Tag `v1.1.22` zeigt auf 369eabf (von Finder und Skeptiker gelesen).
- **Nicht verifizierbar:** Runner auf anderen Hosts als dem lokalen (`gh api …/actions/runners` → 403, kein `admin:org`).
- **Offen geblieben:** der erste scharfe Auto-Release-Lauf (#12, M5); der Merge von shared-ci#97 (M3); ADR-021/022 (M7). Die Belege zu #4 und #5 sind Zeitstempel im Sitzungs-Transkript. Das Transkript liegt nur lokal, deshalb sind sie außerhalb der Sitzung nicht nachprüfbar. Ob private Repos die platform-Kopie von `_build-docker.yml` noch aufrufen: `gh search code` deckt nur den Index ab, ein geprüfter privater Konsument ruft schon shared-ci auf und trägt nur einen veralteten Kommentar.

## Self-Review

Der Meta-Agent (Sonnet, nur Report und Skill) meldete sieben kleine Formbefunde und keinen harten Verstoß. Eingearbeitet sind:

- Maßnahmen-Reihenfolge und Anker: M4 zeigt auf shared-ci#98, M7 auf platform#3779.
- absolutes Datum bei M5
- Konsequenzen in 0.0 nach den vier zulässigen Arten, mit Quelle
- Zeilenangabe zu E.3
- Hinweis, dass die Transkript-Belege nur lokal vorliegen

**Falsifikationsquote:** Phase 3 allein kommt auf phase3_refuted/(total − pre_refuted) = 1/14 = 0,07. Das liegt unter dem Band von 0,2 („Theater“). Rechnet man die vier Kippungen der Widerlegungsbahn hinzu, ergibt sich 5/14 = 0,36. Das liegt im Normalband. Die Falsifikation hat also hier hauptsächlich 3b geleistet, nicht Phase 3. Phase 3 hat zudem #11 zu Unrecht verworfen.

## Widerlegung

Opus, frischer Kontext, mit Report-Entwurf, Footprint und Artefaktliste. Je Punkt mit Beleg aus `origin/main`:

| Punkt | Verdikt | Beleg |
|---|---|---|
| #11 0.x-Regel | GEKIPPT (REFUTED → SURVIVES) | `_build-docker.yml:118` pinnt trivy-action `# v0.36.0`; der Skeptiker hatte nur nach 0.x-Pins gesucht, die es angeblich nicht gab |
| #3 Zuschnitt-Begründung | GEKIPPT (Begründung, Verdikt hält) | `prs_nach_fragment` (`sitzungs_branches.py:120`): E.3 hätte auch beim Sitzungsende bestanden |
| #1 `gates_caught` | GEKIPPT (Eintrag gestrichen) | Hook-Treffer 16:46:56Z galt einer anderen Aussage |
| #8 Restlücke | GEKIPPT (abgeschwächt) | lokale Runner ≥ 2.336 mit Node 24, nachgemessen |
| #2 | BESTAETIGT, erweitert | ADR-021:227, ADR-022:350 |
| #13 | BESTAETIGT, abgeschwächt | Board nannte den Grund, nicht die Gegenseite |
| #9 | BESTAETIGT (verworfen) | PR #95 benennt den Kompromiss |
| #15 Lieferkette | NEU | kein Dependabot-`cooldown`, tägliches Auto-Release, GHSA-69fq-xp46-6x23 |

Die fehlende Dimension war **Lieferkette**. Keiner der drei Finder hatte sie, weil ihre Dimensionen (Soll-Ist, Entscheidungen, Prozess) nach der Sitzung fragen und nicht danach, was die gebaute Automatik künftig tut.

## Streichbahn

Keiner. Jede gelaufene Phase hatte hier einen Effekt, der sich an einer Befundnummer zeigt:

- Die Transkript-Kennzahlen trugen #4.
- Die Skeptiker verwarfen #9.
- Die Widerlegungsbahn kippte ein Fehlurteil der Phase 3 (#11) und fand die einzige Lücke der Stufe „hoch“ (#15).

Gegen eine Streichung spricht vor allem dieser letzte Punkt. Ohne 3b hätte die Retro mit Ergebnis „mittel“ geschlossen, und die Lieferketten-Lücke wäre unentdeckt geblieben.
