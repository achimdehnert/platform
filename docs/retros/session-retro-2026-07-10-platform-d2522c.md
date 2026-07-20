---
retro_schema: 1
date: 2026-07-10
repo_scope: [platform, iil-adrfw, trading-hub, mcp-hub, "~/.claude", platform-pinned]
session_id: d2522c
footprint: deep
findings_total: 15
findings_survived: 12
refuted_rate: 0.20
phase3_refuted: 3
pre_refuted: 0
over_ask: 0
over_act: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [gen-project-facts-pinned-guard, evidence-scanner-published-body-claims, mcp-hub-required-review-rule]
recurring_findings: [claim-before-cheapest-check, lint-failure-no-local-gate, handover-stale-vor-merge, autonomous-no-human-review, platform-pinned-perma-dirty-loop]
---

# Session-Retro 2026-07-10 — Wargame-Analyse → Recall-Goldset → ADR-Fleet/MADR → Fix-Leiter (d2522c)

## 1. Executive Summary

- Sehr hoher Durchsatz mit durchgängiger Selbstkorrektur-Kultur: ~12 PRs/1 Issue über 5 Repos, alle Nutzer-Gos artefakt-belegt umgesetzt (Skeptiker-verifiziert B-S5-REFUTED); drei Falschbehauptungen wurden noch in der Session selbst gefunden und korrigiert.
- **Strukturfund des Retros (#1/#2):** `gen_project_facts.py` symlinkt die 8 GLOBAL_RULES bei jedem `/session-start` auch nach `platform-pinned` (Guard prüft nur `== "platform"`, ADR-265-Guard fehlt) → pinned ist **dauerhaft dirty** → der Session-Start-Policy-Refresh wird dauerhaft übersprungen → pinned altert (57 Commits) → der gemergte claude-policy-Fix (#1052) erreicht das live verlinkte Binary (`~/.claude/bin/claude-policy` → **pinned**) nie. Selbst-erhaltende Blockade-Schleife.
- **Claim-Familie ×3 in einer Session** (#3 „gemergt"-Issue-Kommentar, #9 PR-Body „lint sauber" vor erstem grünem Run, #12 ADR-271-v1.0-„Vollzug"-Framing): `claim-before-cheapest-check` ist laut `retro_kpis.py` bereits gate-pflichtig — der bestehende Stop-Hook fängt Issue-/PR-Body-Claims nicht zuverlässig.
- Prod-Gate war verbal, nicht technisch: mcp-hub/main hat **keine** Review-Protection (nur Status-Checks); #168 (Auto-Deploy Prod) trägt `reviews: []` — Autor- und Merger-Account identisch, menschlicher Klick aus Artefakten nicht beweisbar (#4).
- Entscheidungsqualität strukturell gut (falsifizierbare Wächter, Optionen-Konserven, Amendments vor Merge), aber zweimal mit zu starker Formulierung über die Beleglage hinaus (#5 „ohne realen Konsumenten" ohne Aufrufer-Inventur) bzw. ungetrackter Rest-Debt (#6 Backfill).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | claude-policy-Fix (#1052) erreicht Live-Binary nie: `~/.claude/bin/claude-policy` → platform-**pinned** (57 Commits hinter main), Union-Code dort nicht vorhanden | Werkzeug | hoch | SURVIVES | readlink → pinned; grep `keys \|=` im Ziel leer; `rev-list --count` = 57 | platform-pinned-perma-dirty-loop (neu) |
| 2 | F-8-„verworfen" wirkungslos: `gen_project_facts.py:34-44,150-162` symlinkt GLOBAL_RULES unconditioned in jedes Repo ≠ `"platform"`; pinned nicht ausgenommen (ADR-265-Guard fehlt, den `sync-workflows.sh:236-243` hat) → 8 Symlinke re-erzeugt (mtime 14:24:27Z), pinned perma-dirty, Policy-Refresh perma-übersprungen | Werkzeug | hoch | SURVIVES | Code-Zeilen; `status --short` 8×T; Session-Start-Hook-Warnung | platform-pinned-perma-dirty-loop (neu) |
| 3 | Issue-Close-Kommentar #167 behauptete „#1052 gemergt" 5 Min vor dem realen Merge (14:17:43Z vs. mergedAt 14:22:44Z); Selbstkorrektur 42 s später | fehlende Validierung | mittel | SURVIVES | Kommentar-Timestamps; `gh pr view 1052` | claim-before-cheapest-check (**≥2, gate-pflichtig**) |
| 4 | mcp-hub/main ohne Review-Protection: Ruleset erzwingt nur `🚦 Quality Gate`; #168 (Prod-Auto-Deploy) `reviews: []`, Autor=Merger-Account — „Merge ist dein Klick" technisch nicht erzwungen | Prozesslücke | mittel | SURVIVES | `gh api …/branches/main/protection` → 404; Ruleset 17621473; #168 JSON | autonomous-no-human-review (bekanntes Gate) |
| 5 | KONZ-016 L10 formuliert „ohne realen Konsumenten" (starke Lesart) ohne Aufrufer-Inventur der flottenweiten Freitext-Tools `agent_memory_search`/`agent_memory_context`; Issue #167 geschlossen (14:17:44Z) bevor Trägerdokument #1056 gemergt war | verfrühte Festlegung | mittel | SURVIVES | L10-Wortlaut (#1056-Diff); memory_tools.py-Signaturen; Zeitstempel | claim-before-cheapest-check-Familie |
| 6 | Decay-Ausnahme 4× wortgleicher SQL-CASE in store.py (Z. 414/420/506/520) statt Extraktion; `half_life_days`-Backfill bewusst ausgelassen und **nirgends getrackt** (kein Issue, kein Ledger) | Anti-Pattern/Tech-Debt | mittel | SURVIVES | origin/main store.py; `gh issue list --search backfill/half_life` leer | — |
| 7 | Doppelarbeit F-4: #1041 (approved 12:30:37Z) eine Minute nach Merge des byte-identischen Hunks in #1049 (12:32:02Z per Bündel-PR erledigt) ungemergt geschlossen — Reviewer-Aufwand verschwendet | Prozesslücke | mittel | SURVIVES | beide PR-Diffs/Timestamps | — |
| 8 | Fleet-Audit-Report auf main führt F-4 als „✅ erledigt [#1041]" — #1041 wurde nie gemergt (Fix kam via #1049); Evidenz-Link nach Supersession nie nachgezogen | Kommunikation | mittel | SURVIVES | Report Z. 141 auf origin/main; PR-States | handover-stale-vor-merge (**≥2, gate-pflichtig**) |
| 9 | iil-adrfw#59: PR-Body behauptete „make lint/types: sauber" bei Erstellung (10:28:42Z) — erster CI-Lauf failure (Lint), grün erst nach Fix-Commit f6fd42d (10:47Z) | fehlende Validierung | niedrig-mittel | SURVIVES | Run 29086450296 failure; PR createdAt; Fix-Commit-Zeit | lint-failure-no-local-gate (**≥2, gate-pflichtig**) + claim-Familie |
| 10 | ADR-271 §3.2: fleet-weite Sprachentscheidung (EN) als Beifang eines Tooling-ADRs, `consulted: []`, nur reaktive Rückfalloption; Steelman bestätigt: kein zweiter menschlicher Committer in meiki/ttz-Repos, aber Behörden-Stakeholder sind keine Committer | verfrühte Festlegung | niedrig-mittel | SURVIVES | ADR-271 §3.2/§6.2/§7 + Frontmatter; git log -50 beider Repos | — |
| 11 | Issue #167 als completed geschlossen, alle 4 Body-Checkboxen ungehakt, obwohl Close-Kommentar deren Erledigung feststellt | Kommunikation | niedrig | SURVIVES | Issue-JSON: 4× `- [ ]`, stateReason completed | — |
| 12 | ADR-271 v1.0 trug falsches Governance-Framing („Vollzug einer getroffenen Entscheidung"); Fleet-Audit-Erstfassung trug „ADR-054 existiert nicht mehr" — beide same-day, vor Merge, durch adversarialen Review korrigiert | fehlende Validierung | niedrig | SURVIVES | ADR-271 §10 Changelog; Report-Korrektur-Passagen | claim-before-cheapest-check-Familie |
| 13 | Report-Korrekturen seien „erst nach Betreiber-Go" eingeflossen | — | — | REFUTED | alle 3 Commits sind Ancestors des #1040-Merges (11:55:53Z), Teil des reviewten Diffs | — |
| 14 | Amendment.required-Relaxierung (`by` optional) sei durch keine gelebte Nutzung gedeckt | — | — | REFUTED | ausschreibungs-hub ADR-002:24-28 trägt amendments-Eintrag **ohne** `by` — breiterer Grep widerlegte den Finder | — |
| 15 | Go-Nummern (20/32/23/24/35) für Dritte nicht nachvollziehbar | — | — | REFUTED | Konvention definiert Turn-, nicht Artefakt-Persistenz; alle 5 Gos über PR-Bodies/Commits rückverfolgbar (168→167, 1054↔61, 930be44→168, manifest-mtime, Transkript) | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Alle Gos artefakt-belegt umgesetzt (B-S5-Widerlegung), Goldset→Fix→Deploy→Messung geschlossen; Mängel: #8/#11 Doku-Reste |
| architektur_design | 4 | Exakt-Key/Decay-Design getestet+deployed, Festlegungen mit falsifizierbaren Wächtern; Mängel: #6 Duplizierung, #5 starke Lesart |
| code_konventionstreue | 3 | #9 verletzt Repo-Regel „make fmt before committing"; #6 SQL-Duplizierung; sonst Konventionen (Commits, Worktrees, Validator) eingehalten |
| risiko_debt | 3 | #6 untracked Backfill; #1/#2 strukturelle Schleife bestand unerkannt bis zum Retro; dagegen: alle Messinstrumente mit Regressionsanker |
| prozess_effizienz | 3 | #7 Doppelarbeit, #9 19-Min-Rework-Loop, 3 Selbstkorrektur-Schleifen; dagegen: 12 Artefakte in einem Tag sauber durch Review |
| entscheidungsqualitaet | 4 | Optionen-Konserven, Kill-Gates, Amendment vor Merge (#12 wurde gefangen); Abzug: #5/#10 Formulierungen über Beleglage hinaus |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #)

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Fix in platform gebaut, Symlink-Ziel nie aufgelöst (readlink zeigt pinned) | Vor jedem Fix an einem via `~/.claude` aufgerufenen Werkzeug: `readlink -f` des Einstiegspunkts, Fix-Wirksamkeit am AUFGERUFENEN Pfad verifizieren | 1 |
| „Symlinks verworfen ✓" ohne Erzeuger-Suche; Wiederkehr erst vom Retro-Finder entdeckt | Vor jedem Verwerfen nicht-selbst-angelegter Artefakte: Erzeuger suchen (`grep -rln <pattern> hooks/ tools/`) — wiederkehrende Artefakte haben fast immer einen Generator | 2 |
| Issue-Close-Kommentar nennt PR-Status aus dem Gedächtnis | Jede Status-Nennung in publizierten Bodies (Issue/PR-Kommentar) erst nach `gh pr view <n> --json state` im selben Turn | 3 |
| Prod-deployender PR mit `reviews: []` merge-bar | Owner-Entscheid: Review-Rule im mcp-hub-Ruleset ergänzen (wie platform), damit „dein Klick" technisch erzwungen ist | 4 |
| „ohne realen Konsumenten" ohne Aufrufer-Scan formuliert | Konsumenten-Aussagen nur nach Inventur (`grep -rln <tool-name>` über Repos + ggf. Call-Log-Stichprobe) — sonst schwächere Lesart „kein designter Konsument" schreiben | 5 |
| Backfill bewusst ausgelassen, nur im PR-Text erwähnt | Jede bewusst ausgelassene Restarbeit bekommt im selben Turn ein Tracking-Artefakt (Issue oder Ledger-Zeile), sonst gilt sie als nicht existent | 6 |
| Einzel-PR #1041 parallel zum Bündel-PR #1049 mit identischem Hunk | Vor jedem Quick-Fix-PR prüfen, ob ein bereits geplanter größerer PR denselben Hunk enthält — dann bündeln statt zweimal reviewen lassen | 7 |
| Report-Backlog-Zeile nach Supersession nicht nachgezogen | Wenn ein PR einen anderen obsolet macht: im selben Turn alle main-Dokumente greppen, die den obsoleten PR referenzieren (`grep -rn "#1041" docs/`) und nachziehen | 8 |
| Push ohne lokalen `make fmt-check`; PR-Body claimt Endzustand | Vor jedem Push, der einen PR-Body mit „lint/types sauber" trägt: den Check im selben Turn laufen lassen (Repo-CLAUDE.md verlangt es bereits) | 9 |
| Sprachentscheid fleet-weit im Tooling-ADR, `consulted: []` | Entscheidungen mit benannter Stakeholder-Regression: mindestens `consulted`/`informed` befüllen oder explizit „bewusst ohne Konsultation, weil <Grund>" ins ADR | 10 |
| Checkboxen im Issue-Body blieben ungehakt beim Close | Beim Issue-Close mit „erledigt"-Kommentar: Body-Checkboxen im selben Edit abhaken (`gh issue edit --body`) | 11 |
| v1.0-Governance-Claims aus Kopfwissen („Vollzug", „existiert nicht mehr") | Governance-Fakten (X entschied Y, Z existiert) vor Niederschrift mit einem gezielten grep/Datei-Open belegen — Analyse-Reports fallen unter dieselbe Evidenz-Pflicht wie Code-Claims | 12 |

## 5. Längsschnitt (retro_kpis.py, Lauf 2026-07-10)

Bereits gate-pflichtig (≥2 über Retros) und in dieser Session ERNEUT aufgetreten: **`claim-before-cheapest-check`** (#3/#5/#9/#12 — vier Vorkommen in einer Session), **`lint-failure-no-local-gate`** (#9), **`handover-stale-vor-merge`** (#8, Doku-Variante). Neu eingeführter Slug: **`platform-pinned-perma-dirty-loop`** (#1/#2 — Erstvorkommen, aber struktureller Dauerzustand, Gate-Kandidat ab sofort statt bei ×2, weil deterministisch fixbar). `autonomous-no-human-review` (#4): im heutigen `retro_kpis.py`-Lauf NICHT in der ≥2-Liste (Erstvorkommen unter diesem Slug im KPI-Schema); der Gate-pflichtig-Status stammt aus der User-CLAUDE.md-Dokumentation (2026-06-23, dort „≥2× über Retros“ vor Einführung des Slug-Schemas) — hier in der technischen Variante (fehlende Review-Rule). Score-Mittel der letzten 20 Retros zum Vergleich: zielerreichung 3,90 · risiko_debt 2,70 — diese Session liegt bei 4/3.

**5b. Autonomie-Kalibrierung:** `over_ask: 0` — alle „dein Zug"-Items waren echte Gates (Branch-Protection-Approves, Owner-Entscheide, Prod-Merge). `over_act: 0` — beide heiklen Aktionen (Merge #1042 nach Einzel-Verifikation von `reviewDecision=APPROVED`; Merge #59 nach wörtlichem „25 erledigt") waren namentlich gedeckt; der Auto-Mode-Classifier blockte zwei Merge-Versuche, denen kein Workaround folgte, sondern Rückgabe an den Menschen. Sequenzfehler #5 (Issue-Close vor Trägerdoc-Merge) ist ein Ordnungs-, kein Gate-Fehler.

## 6. Verankerung (Vorschläge — Verankerung entscheidet der Mensch)

**memory_candidates:**

```markdown
---
name: platform-pinned-perma-dirty-loop
description: gen_project_facts.py symlinkt GLOBAL_RULES auch nach platform-pinned (Guard prüft nur == "platform") → pinned perma-dirty → Policy-Refresh perma-übersprungen → ~/.claude/bin/claude-policy (Symlink auf pinned!) altert unbegrenzt; Verwerfen der Symlinks ist Sisyphus, Fix gehört in gen_project_facts.py
metadata:
  type: project
  drift: true
  drift_episode: 2026-07-10-pinned-dirty-loop
---
Kette (alle Glieder artefakt-belegt, Retro d2522c #1/#2): `platform/scripts/gen_project_facts.py:150-162`
symlinkt die 8 GLOBAL_RULES in JEDES Repo ≠ String "platform" — platform-pinned (Worktree,
[[platform-pinned-is-worktree]]) wird über den Unregistered-Scan (Z. 324-333) miterfasst.
Der ADR-265-SSoT-Guard aus sync-workflows.sh:236-243 (remote-URL-Check) fehlt dort.
Folge: pinned dauerhaft dirty → refresh_pinned_policies.sh übersprungen → pinned 57 Commits
hinter main → `~/.claude/bin/claude-policy` (readlink → pinned!) führt alte Logik aus, gemergte
Fixes (z. B. platform#1052) wirken nie. **How to apply:** Symlinks in pinned NICHT von Hand
verwerfen (kommen beim nächsten /session-start wieder); stattdessen gen_project_facts.py um den
remote-URL-Guard ergänzen, danach pinned einmalig clean ziehen.
```

```markdown
---
name: published-body-claims-need-in-turn-check
description: Status-/Erfolgs-Behauptungen in publizierten Texten (Issue-Kommentar, PR-Body, Report) sind claim-before-cheapest-check-Fälle — Check im SELBEN Turn vor dem Publish, nicht danach; Session d2522c hatte 4 Vorkommen in einem Tag
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-10-published-body-claims
---
Vier Vorkommen in EINER Session (Retro d2522c #3/#5/#9/#12): „#1052 gemergt" im Issue-Close
(war OPEN), „make lint sauber" im PR-Body (erster Run rot), „Vollzug einer getroffenen
Entscheidung" in ADR-v1.0 (ADR-059 entschied nur die State-Machine), „ADR-054 existiert nicht
mehr" im Audit-Report (war superseded). **Why:** Publizierte Texte überleben; Chat-Korrekturen
erreichen Leser der Artefakte nicht. **How to apply:** Vor JEDEM gh-Publish (pr create/comment/
close, issue comment/close) mit Status-/Zahlen-/Existenz-Marker: den billigsten Check im selben
Turn laufen lassen und im Text zitieren. Der Stop-Hook evidence_claim_scanner fängt das nur
teilweise — Erweiterung um gh-Publish-Aufrufe ist Gate-Kandidat.
```

**adr_candidates:** Kein neuer ADR nötig (adr-threshold: beides Additions/Fixes nach Muster). Stattdessen zwei Gate-PRs: (1) `gen_project_facts.py` remote-URL-Guard (deterministisch, Klasse A), (2) `evidence_claim_scanner.py` um PreToolUse-Prüfung für `gh pr create|comment|merge`/`gh issue comment|close`-Bodies mit Status-Markern erweitern. Plus Owner-Entscheid: Review-Rule im mcp-hub-Ruleset.

## 7. Maßnahmen (Action-Board)

### 🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Review-Rule mcp-hub/main | mcp-hub | [Ruleset](https://github.com/achimdehnert/mcp-hub/settings/rules) | 🟢 offen | required_approvals≥1 setzen (du) |
| M2 | Memory-Kandidaten übernehmen | ~/.claude | [Report §6](file:///home/devuser/github/platform/docs/retros/session-retro-2026-07-10-platform-d2522c.md) | 🟢 offen | 2 Memories freigeben (du) |

### 🔵 Offen — ich kann sofort (nach Go)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M3 | gen_project_facts pinned-Guard | platform | [gen_project_facts.py](file:///home/devuser/github/platform/scripts/gen_project_facts.py) | 🔵 ready | Guard-PR + pinned clean (ich) |
| M4 | Backfill-Issue half_life | mcp-hub | [#168](https://github.com/achimdehnert/mcp-hub/pull/168) | 🔵 ready | Issue anlegen (ich) |
| M5 | Report-F-4-Link nachziehen | platform | [Fleet-Audit](file:///home/devuser/github/platform/docs/adr/reviews/ADR-FLEET-AUDIT-2026-07-10.md) | 🔵 ready | #1041→#1049 fixen (ich) |
| M6 | #167-Checkboxen abhaken | mcp-hub | [#167](https://github.com/achimdehnert/mcp-hub/issues/167) | 🔵 ready | Body-Edit (ich) |
| M7 | Scanner: gh-Publish-Claims | ~/.claude | [Hook](file:///home/devuser/.claude/hooks/evidence_claim_scanner.py) | 🔵 ready | Hook-Erweiterung (ich) |
| M8 | SQL-CASE extrahieren | mcp-hub | [store.py](https://github.com/achimdehnert/mcp-hub/blob/main/orchestrator_mcp/memory/store.py) | 🔵 ready | Refactor-PR, klein (ich) |

## 8. Nicht verifiziert (Restlücken)

- **E-Mail-Versand an Ilja.Lerch@deutschebahn.com:** kein git/gh-Artefakt möglich; SMTP-Erfolgsmeldung + IMAP-gelesene Antwort („ok", 10:08Z) liegen nur im Session-Transkript — Hypothese-Status für Dritte; billigster Check: IMAP-Postfach `Sent`/Antwort-Thread.
- **Wer klickte den #168-Merge** (Mensch im Browser vs. CLI): Artefakte können es nicht unterscheiden (gleicher Account); M1 macht die Frage künftig gegenstandslos.
- **`tenancy_mode`-blockierte PRs #963/#1053** (Collector-Red-Flag): NICHT aus dieser Session, nicht untersucht — billigster Check: `gh pr checks 1053` + Gate-Log lesen.
- **Ob der 14:24:27Z-Symlink-Rewrite exakt von einem `/session-start` kam:** Code+Timing+Dateiliste passen 1:1, ein Log des konkreten Laufs wurde nicht gesichert (Hypothese mit starker Indizienlage).

## Self-Review (Phase-5-Meta-Agent, Sonnet)

8/9 Skill-Regeln PASS im Erstdurchlauf; ein FAIL (fehlender Zähler-Bezug für `autonomous-no-human-review` in §5) wurde mit ehrlicher Quellen-Trennung korrigiert (KPI-Erstvorkommen vs. CLAUDE.md-Gate-Dokumentation). `refuted_rate` 0,20 liegt im gesunden Band (Vorgänger 0,00–0,50), exakt an der unteren Theater-Schwelle — Meta-Notiz: Randlage, kein Verstoß; drei der zwölf Survivors stammen aus Skeptiker-VERSCHÄRFUNGEN (57 statt 24 Commits; Erzeuger-Mechanismus gefunden), was gegen laxe Finder spricht.

Prozess-Anmerkung (Transparenz): Die Erstfassung dieses Reports wurde durch einen Quoting-Fehler im Edit-Skript OHNE diese Meta-Korrektur gepusht; der Fehler wurde per Remote-Diff entdeckt und mit diesem Folge-Commit behoben — ein Live-Exemplar von Befund #9-Familie (Publish vor Check) im Retro selbst.
