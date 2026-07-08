---
retro_schema: 1
date: 2026-07-08
repo_scope: [frist-hub, platform]
session_id: 7f7fbd
footprint: full
findings_total: 14
findings_survived: 10
refuted_rate: 0.286
phase3_refuted: 4
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [handover-stale-vor-merge, ci-gate-maskiert-failure, klickdummy-local-gate-not-wired-into-ci]
recurring_findings: [handover-stale-vor-merge, ci-gate-maskiert-failure]
---

# Session-Retro · frist-hub / platform · 2026-07-08 (Session 7f7fbd)

## 1. Executive Summary

- BRMS-Rechtskorrekturen (PR #5, 74/74 Tests grün), Governance-Matrix-Split (KONZ-001/002),
  zwei Klickdummies (Fristenmanagement mit Szenario-Switch, AKTE-DMS mit echtem d.velop-Layout)
  und eine Cross-Repo-ADR-109-Ausnahme (platform PR #979) wurden geliefert und real click-getestet
  (Playwright), nicht nur `curl`/`grep`-verifiziert.
- **`AGENT_HANDOVER.md` ist auf `main` stale** — 3 PRs (#18, #20, #22) wurden nach dem letzten
  Edit gemerged, ohne den Handover nachzuziehen; das ist eine **Wiederholung** des bereits
  gate-pflichtigen Musters `handover-stale-vor-merge` (2. Beleg dieser Session, ×N historisch).
  Der session-eigene `handoff-banner-gate.yml` kann das strukturell nicht fangen — er feuert nur
  bei Edits an der Datei selbst, nicht bei fremden PR-Merges.
- **I4-Namespace-Verstoß aktuell live auf `main`**: `KONZ-frist-hub-001/002` haben 12 unqualifizierte
  Cross-Repo-ADR-Referenzen; der Fix liegt in PR #23 — **unmerged**, seit dieser Session offen.
- **`ci-gate-maskiert-failure`** (bereits als Drift-Memory bekannt) trat in dieser Session ein
  zweites Mal strukturell relevant auf: 6 weitere Merges liefen über den bekannt-defekten
  `ci / gate` (maskiert `continue-on-error`-Failures), ohne dass der stalled-fix (platform PR #963)
  angefasst wurde — das macht den Slug zum ersten Mal **≥2 über Retros hinweg** ⇒ Gate-Pflicht.
- Ein ursprünglich als „möglicher Konventionsfehler" eingestufter eigener Entscheid (PR #979,
  kein `amended:`-Frontmatter) wurde durch die Falsifikation **positiv bestätigt**: das reale
  ADR-JSON-Schema verlangt ein strukturiertes Array, die 39 ADRs mit skalarem `amended:` sind
  selbst nicht-konform — kein Konventions-Fehler, sondern die einzig valide Wahl.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | `AGENT_HANDOVER.md` stale auf `main` — 3 PRs (#18, #20, #22) nach letztem Edit gemerged, keine der Änderungen (AKTE-DMS, Szenario-Switch, ADR-109-Ausnahme) im Handover erwähnt. **Korrektur ggü. Erstbehauptung:** #21 fälschlich als 4. PR genannt — #21 mergte 3 Min *vor* dem letzten Handover-Edit, gehört nicht zur Stale-Menge. | Prozesslücke | hoch | SURVIVES (korrigiert) | `git log --follow AGENT_HANDOVER.md` vs. `gh pr list --state merged`, Zeitstempel-Diff durch Skeptiker A neu gezogen | 🌀 `handover-stale-vor-merge` — ≥2 (siehe `retro_kpis.py`) |
| 2 | `handoff-banner-gate.yml` (dieser Session selbst gebaut) kann Handover-Staleness durch **fremde** PR-Merges strukturell nicht erkennen — Trigger nur `paths: AGENT_HANDOVER.md`. | Wissenslücke (Gate-Design) | hoch | SURVIVES | Workflow-YAML gelesen, `on.pull_request.paths` geprüft | neu — direkt an #1 gekoppelt |
| 3 | AKTE-DMS-Klickdummy ist Netto-Neu-Scope ohne Beleg auf einem Vor-Session-Backlog-Artefakt (Jira/NEXT.md/Issue). Kein Urteil über Autorisierung — nur Abwesenheits-Check. | Scope | mittel | SURVIVES | `grep` über `NEXT.md`, MEIKI1-Jira-Backlog-Snapshot, keine Treffer vor User-Prompt | neu |
| 4 | Reviewer „wirdigital" approved platform PR #979 in 91s mit generischer Body-Formel; Skeptiker fand denselben Reviewer/Zeitmuster (1,5–70 Min, nicht uniform ~90s) auf 5+ weiteren platform-PRs — echtes, aber unregelmäßigeres Muster als ursprünglich behauptet. | Prozess/Kollaboration | hoch | SURVIVES (korrigiert) | `gh pr view 979 --json reviews`, Org-weite Suche über 5+ weitere PRs | neu |
| 5 | `KONZ-frist-hub-001/002` haben 12 unqualifizierte Cross-Repo-ADR-Refs (I4-Verstoß, platform:ADR-211) **live auf `main`**, seit PR #18 gemerged wurde ohne vorheriges `make klickdummy`. Fix liegt in PR #23, unmerged. | Prozesslücke / Konventionsverstoß | hoch | SURVIVES | `make klickdummy-i4` gegen `origin/main` (nicht Working-Tree) durch Skeptiker B neu gezogen | neu |
| 6 | Lokale `make klickdummy`-I4-Prüfung wurde nie in CI verdrahtet (kein `.github/workflows`-Treffer) — reiner manueller Gate, kein automatisierter. **Korrektur ggü. Erstbehauptung:** die Formulierung „dritte CI-Gate-Instanz" ist ein Kategoriefehler — es handelt sich nicht um dieselbe Automatisierungsklasse wie die beiden zitierten Präzedenzfälle. Der zugrunde liegende Defekt (Namespace-Drift unentdeckt bis Retro) bleibt real. | Werkzeug/Prozesslücke | mittel (von hoch herabgestuft) | SURVIVES (Framing korrigiert) | `grep -r "klickdummy" .github/workflows/` (frist-hub) → 0 Treffer | neu |
| 7 | Echter Name („Frau Martinkat") in Konzept-Entwurf auf 2 Branches committed, jeweils in einem Folge-Commit korrigiert — Korrektur-Lücke **asymmetrisch** (40 Min auf einem Branch, 80 Min auf dem anderen, nicht „~40 Min auf beiden" wie erstbehauptet). Der Rohtext bleibt in der Git-Historie beider (unmerged/unsquashed) Branches über die GitHub-API abrufbar. | Datenschutz/Prozess | mittel-hoch | SURVIVES (korrigiert) | `git log -p` beider Branches, Commit-Zeitstempel-Diff durch Skeptiker B neu gezogen | neu |
| 8 | PR #23 bündelt zwei fachlich unabhängige Änderungen (d.velop-Screenshot-Layout-Refresh **und** I4-Namespace-Fix) in einem PR — erschwert Review/Revert-Granularität. | Prozess | mittel | SURVIVES | `gh pr diff 23 --name-only` gegen PR-Body-Beschreibung | neu |
| 9 | Branch-Verschränkung: PR #17s Branch wurde direkt in den zu dem Zeitpunkt noch offenen Branch von PR #20 gemerged (nicht über `main`), bevor #20 selbst gemerged war. | Prozess/Kollaboration | mittel | SURVIVES | `git log --graph` über beide Branches, Merge-Base-Analyse | neu |
| 10 | `ci/gate` (frist-hub + platform, `_ci-python.yml:~330`) meldet strukturell SUCCESS trotz `continue-on-error: true` auf `ci / Integration Tests` — bekannter Fleet-weiter Defekt (Draft-Fix platform PR #963, stalled). Diese Session mergte 6 weitere PRs über diesen maskierten Gate, ohne #963 anzufassen. | Risiko/Tech-Debt | kritisch | SURVIVES | `.github/workflows/_ci-python.yml` Zeile ~330 gelesen, `gh pr view 963 --json state,updatedAt` | 🌀 `ci-gate-maskiert-failure` — jetzt ×2 über Retros (Gate-Pflicht-Schwelle erreicht) |

**Nicht in die Tabelle aufgenommen (positiv/informativ, kein Soll-Schritt nötig):**
- PR-Bodies von #5/#17/#18/#22/#979 entsprechen inhaltlich den tatsächlichen Diffs (stichprobenartig 3 PRs unabhängig gegengeprüft, keine Diskrepanz) — SURVIVES als Bestätigung.
- PR #5 (BRMS-Rechtskorrekturen) ist mit 4 neuen, spezifischen Testfällen (Stichtag-Grenzfälle, Aufforderung-Fiktion) sauber abgedeckt, Ruff clean — SURVIVES als Bestätigung.

**Verworfen (REFUTED, nicht im Report, Korrektur-Fakt nur soweit oben eingearbeitet):**
- Ursprüngliche B4-Behauptung „PR #979 hätte `amended: <date>` nutzen sollen" — Skeptiker fand:
  das reale ADR-JSON-Schema verlangt ein strukturiertes Amendment-Array, auch die Skalar-Form
  ist ungültig; die 39 ADRs mit `amended: <date>` sind selbst nicht-schema-konforme Legacy-Artefakte.
  PR #979s Body-Text-Lösung war die korrekte Wahl, kein Fehler.
- Ursprüngliche C4-Behauptung „~ein Dutzend un-gelöschte Branches" — tatsächlich 8, zusätzlich
  methodische Mehrdeutigkeit zwischen git-nativer und PR-Status-basierter Zählung (11 vs. 3).

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| Zielerreichung | 4 | Kernauftrag (PR #5/#17/#18/#22 vor ViKo, KD für AKTE-DMS, User-Handout) vollständig geliefert; Abzug für #17 unmerged + Handover-Lücke (#1). |
| Architektur/Design | 4 | KONZ-Split (Kern vs. Extraktions-Naht) sauber right-sized; ADR-001/002-Kollision proaktiv vermieden; Abzug für initiale Über-Bündelung in PR #23 (#8). |
| Code-Konventionstreue | 3 | I4-Verstoß aktuell live auf `main` (#5) ist ein echter, gegenwärtiger Konventionsbruch, nicht nur historisch. |
| Risiko/Tech-Debt | 2 | Kritischer, bekannter `ci/gate`-Maskierungs-Defekt (#10) wurde trotz wiederholter Kenntnisnahme durch 6 weitere Merges nicht adressiert — echte Akkumulation. |
| Prozess-Effizienz | 3 | Mehrfaches Rework (AKTE-DMS ohne Referenz → Revision; PR #18 ohne `make klickdummy` gemerged → Nachfix nötig). |
| Entscheidungsqualität | 4 | Mehrere belastbare Calls (KONZ-Split, Merge-Verweigerung ohne `rechtsamt-ok`, Body-Text statt invalidem Frontmatter); PR-#18-Merge ohne Namespace-Check war der einzige echte Fehlgriff. |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Handover wurde früh im Session-Verlauf editiert, danach liefen 3 weitere PRs durch, ohne dass ein Trigger das erneut anstieß. | Handover-Update als **letzter** Schritt vor Session-Ende fahren (nicht bei Zwischenstand) — bereits als Memory `handover-stale-vor-merge` festgehalten; hier bestätigt es sich ein weiteres Mal, verschärft die Gate-Pflicht statt eines neuen Memos. | #1 |
| `handoff-banner-gate.yml` prüft nur, ob `AGENT_HANDOVER.md` im selben PR geändert wurde. | Gate erweitern: bei jedem Merge auf `main`, der `apps/`, `docs/klickdummy*/` oder `docs/adr/` berührt, `AGENT_HANDOVER.md`-Alter (`git log -1 --format=%ct`) gegen Merge-Zeitpunkt prüfen; Alter > X Merges seit letztem Edit ⇒ Warn-Kommentar auf den PR. | #2 |
| Scope-Erweiterung (AKTE-DMS-KD) entstand direkt aus User-Chat-Prompt, ohne dass vorher ein Board/Issue-Eintrag geprüft wurde. | Vor Aufnahme von Netto-Neu-Scope (kein Bezug zu offenem Issue/Board-Item) kurz spiegeln: „das ist neuer Scope, nicht auf dem Board — trotzdem aufnehmen?" (1 Satz, kein Vollstopp). | #3 |
| Reviewer-Genehmigungen liefen als Einzelperson-Fast-Approval ohne erkennbares zweites Augenpaar. | Bei Cross-Repo-ADR-Änderungen (wie ADR-109-Ausnahme) vor dem Merge explizit einen zweiten, funktional unabhängigen Reviewer benennen/anfragen — nicht nur den Standard-Approval-Bot laufen lassen. | #4 |
| PR #18 wurde gemerged, ohne vorher `make klickdummy` (I1–I4) im entsprechenden Worktree laufen zu lassen. | `make klickdummy` als Pflicht-Schritt **vor jedem Merge**, der `docs/konzepte/*` oder `docs/klickdummy*/` berührt — nicht erst beim nächsten zufälligen Touch der Datei. | #5 |
| Lokaler `make klickdummy`-Gate existiert nur als manuelles Kommando, nie in GitHub Actions verdrahtet. | `make klickdummy` (I1–I4) als eigenen Job in `.github/workflows/ci.yml` (frist-hub) aufnehmen — macht den Gate erzwingbar statt Vertrauens-basiert. | #6 |
| Realname wurde in einem Konzept-Draft committed, in einem Folge-Commit "korrigiert" — der Rohtext bleibt aber im Git-Verlauf abrufbar (API), solange der Branch nicht gesquasht/gemerged ist. | Bei Realname-Leak in einem Konzept-Draft: vor dem nächsten Push aktiv squashen/rebase-cleanen statt nur vorwärts zu korrigieren — insbesondere wenn der Branch absehbar noch offen bleibt. | #7 |
| PR #23 vermischt Layout-Refresh und I4-Namespace-Fix in einem Commit-Set. | Fachlich unabhängige Fixes (Layout vs. Namespace-Compliance) in getrennte PRs aufteilen, auch wenn beide im selben Arbeitsschritt entdeckt werden. | #8 |
| PR #17s Branch wurde direkt in PR #20s (damals offenen) Branch gemerged, nicht über `main`. | Cross-Branch-Abhängigkeiten immer über `main` auflösen (PR A mergen → PR B rebasen), nie Branch-zu-Branch — sonst wird die Merge-Reihenfolge im Git-Graph unklar. | #9 |
| `ci/gate` maskiert `continue-on-error`-Failures seit bekannt (Fix-Draft #963 stalled); diese Session mergte 6 weitere PRs darüber hinweg, ohne #963 anzustoßen. | Sobald ein bekannt-defekter Required-Check erneut passiert wird (hier: 2. Mal über Retros), automatisch Draft-Fix-PR (#963) reaktivieren/pingen statt nur erneut zu dokumentieren — bei ×2 ist das jetzt Gate-Pflicht, kein drittes Memo. | #10 |

## 5. Längsschnitt (`tools/retro_kpis.py`)

- **9 Slugs bereits ≥2 über alle Retros** (Gate-PR-Pflicht, unverändert von diesem Report):
  `claim-before-cheapest-check`, `critical-alert-no-ticket`, `handover-stale-vor-merge`,
  `lint-failure-no-local-gate`, `parallel-session-pr-collision`, `planned-phase-no-issue`,
  `scope-checkpoint-not-durably-recorded`, `stale-local-clone-as-ground-truth`,
  `worktree-midsession-accumulation`.
- **`handover-stale-vor-merge` (Befund #1)** ist eine direkte Wiederholung eines bereits
  gate-pflichtigen Slugs — bestätigt gegen `MEMORY.md`-Eintrag `handover-stale-vor-merge.md`.
- **`ci-gate-maskiert-failure` (Befund #10)** stand vor diesem Report bei ×1 (`a50bc6`) — mit
  diesem Report erreicht der Slug **×2**, überschreitet die Gate-Pflicht-Schwelle zum ersten Mal.
  Bestätigt gegen `MEMORY.md`-Eintrag `ci-gate-maskiert-failure.md`.
- **refuted_rate-Trend**: `e17299:0.33 · f5e1d:0.20 · 16fd96:0.33 · a2c373:0.40 · 2752dc:0.12 ·
  35c665:0.33 · 44240f:0.38 · 0b46ee:0.50` — Band gesund. Dieser Report: **0.286**, liegt innerhalb
  des gesunden Bands (weder Finder zu lasch >0.8 noch Falsifikation Theater <0.2).
- **Score-Vergleich ggü. historischem Mittel (n=16)**: `risiko_debt` (2 vs. Ø 2.75) liegt spürbar
  unter Durchschnitt — konsistent mit Befund #10 (bekannter kritischer Defekt, wiederholt
  durchgereicht statt behoben). Andere Dimensionen liegen nahe am historischen Mittel.

### 5b. Autonomie-Kalibrierung

- **`over_ask`**: keiner identifiziert — alle Merge-Bestätigungen betrafen tatsächlich irreversible
  Gates (Merge auf geschütztem `main`), korrekt als „dein Zug" behandelt.
- **`over_act`**: keiner identifiziert — die einzige potenziell riskante Aktion (Cloudflare-Access-
  Token-Zugriff) wurde nach dem zweiten Block korrekt gestoppt und eskaliert, nicht autonom
  fortgesetzt.

## 6. Verankerung — kopierfertige Vorschläge

**Memory-Update (bestehende Datei, Occurrence-Zähler erhöhen):**
```yaml
# ~/.claude/projects/-home-devuser-github-frist-hub/memory/handover-stale-vor-merge.md
# Ergänzen: 2. bestätigtes Vorkommen (2026-07-08, session 7f7fbd) — 3 PRs (#18,#20,#22)
# nach letztem Edit gemerged. Handoff-Banner-Gate erkennt fremde-PR-Staleness strukturell nicht.
```

**Memory-Update (bestehende Datei, Occurrence-Zähler erhöhen, jetzt Gate-Pflicht):**
```yaml
# ~/.claude/projects/-home-devuser-github-frist-hub/memory/ci-gate-maskiert-failure.md
# Ergänzen: 2. bestätigtes Vorkommen über Retros (retro_kpis.py: a50bc6 → jetzt 7f7fbd).
# Schwelle ≥2 erreicht → Gate-PR-Pflicht statt drittes Memo. Nächster Schritt: platform PR #963
# reaktivieren (derzeit Draft/stalled) statt erneut nur dokumentieren.
```

**Neue Memory (`klickdummy-local-gate-not-wired-into-ci.md`):**
```yaml
---
name: klickdummy-local-gate-not-wired-into-ci
description: make klickdummy (I1-I4) läuft nur lokal/manuell, nie in GitHub Actions — Namespace-Drift (I4) blieb bis zum Retro unentdeckt
metadata:
  type: feedback
---
`make klickdummy` (I1-I4-Invarianten, platform:ADR-211) ist in frist-hub nur ein manuelles
Makefile-Target, kein CI-Job. PR #18 wurde gemerged, ohne dass I4 (Cross-Repo-Namespace) geprüft
wurde — 12 unqualifizierte ADR-Refs blieben bis zum Session-Retro unentdeckt.

**Why:** ein lokal existierender Gate schützt nur, wenn er auch ausgeführt wird — ohne CI-
Verdrahtung ist er vertrauensbasiert, nicht erzwungen.

**How to apply:** vor jedem Merge, der docs/konzepte/* oder docs/klickdummy*/ berührt,
`make klickdummy` explizit laufen lassen; mittelfristig als CI-Job in .github/workflows/ci.yml
aufnehmen (frist-hub). Nicht mit [[ci-gate-maskiert-failure]] verwechseln — anderer Fehlermodus
(fehlende Verdrahtung vs. maskiertes Ergebnis eines existierenden Jobs).
```

**ADR-Kandidat:** keiner — die Befunde sind Prozess-/Gate-Lücken, keine Architektur-Entscheidung
(unter `adr-threshold.md`).

## 7. Maßnahmen — Action-Board

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | `AGENT_HANDOVER.md` nachziehen (AKTE-DMS, Szenario-Switch, ADR-109-Ausnahme, PR#23-Status) | frist-hub | — | 🟢 offen | du: bestätigen, dann ich sofort |
| 2 | PR #23 (I4-Fix + Layout-Refresh) mergen — löst den aktuell live auf `main` stehenden I4-Verstoß | frist-hub | [#23](https://github.com/meiki-lra/frist-hub/pull/23) | 🟢 offen | du: PR-spezifische Merge-Bestätigung |
| 3 | PR #17 (Szenario-Switch) mergen oder explizit zurückstellen | frist-hub | [#17](https://github.com/meiki-lra/frist-hub/pull/17) | 🟢 offen | du: PR-spezifische Merge-Bestätigung |
| 4 | platform PR #963 (Integration-Coverage-Gate-Fix) reaktivieren — jetzt Gate-Pflicht (×2) | platform | [#963](https://github.com/achimdehnert/platform/pull/963) | 🟢 offen | du: Priorität/Owner bestätigen |
| 5 | `handoff-banner-gate.yml` um Fremd-PR-Staleness-Check erweitern | frist-hub | — | 🔵 ready | ich: Workflow-Patch vorbereiten, PR öffnen |
| 6 | `make klickdummy` als CI-Job in `.github/workflows/ci.yml` verdrahten | frist-hub | — | 🔵 ready | ich: PR öffnen |
| 7 | Realname-Restrisiko in Git-Historie (PR #17-Branch, unsquashed) bewerten | frist-hub | — | 🟡 wip | du: Squash vor nächstem Push entscheiden |

## 8. Nicht verifiziert (Restlücken)

- **Ob die AKTE-DMS-KD-Erstellung explizit vom User oder Team 204 vorab autorisiert war** (nur
  Abwesenheit auf Backlog-Artefakten geprüft, keine Aussage über tatsächliche mündliche
  Freigabe) — billigster Check: User direkt fragen, ob ViKo-Vorbereitung diesen Scope einschloss.
- **Ob PR #17s Branch nach Merge gesquasht wird** (aktuell offen, Realname-Rohtext bleibt bis
  dahin abrufbar) — billigster Check: `gh pr view 17 --json mergeable,mergeStateStatus` vor Merge.
- **Cross-Repo-Impact von platform PR #979 auf andere `ADR-109`-Konsumenten** (nur frist-hub-
  Ausnahme geprüft, keine vollständige Fleet-weite Such-Sweep) — billigster Check:
  `grep -rl "platform:ADR-109" ~/github/*/docs/` nach Merge von #979.
