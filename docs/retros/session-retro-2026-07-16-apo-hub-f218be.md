---
retro_schema: 1
date: 2026-07-16
repo_scope: [apo-hub, platform]
session_id: f218be
footprint: full
footprint_reduction_reason: >
  Trigger war "Prod-Schritt" (apo-hub main = Auto-Deploy nach Hetzner/Cloudflare-Access-
  Acceptance) => Start bei `deep`. Downscale auf `full`, weil alle drei Bedingungen erfüllt:
  (a) jeder der drei Merges (#55, #56, platform#1203) wurde vom Menschen explizit freigegeben
  (Chat: "Beide PRs mergen" / "ja, mergen" / AskUserQuestion-Wahl "Admin-Override"), (b) voll
  rollback-fähig — keine neue DB-Migration in den Diffs (docs/tests/1-Zeilen-YAML), gleiche
  Deploy-Pipeline wie zuvor, (c) plausible Befund-Dichte <=10 gegeben durchgängiger
  Verifikationspraxis in der Session (Coverage-Zahlen, Health-Check pre-existing-vs-Regression,
  Merge-Bestätigung — alles vor Behauptung geprüft).
findings_total: 8
findings_survived: 6
refuted_rate: 0.125
phase3_refuted: 1
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 5
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [handover-sync-gate]
recurring_findings: [handover-stale-vor-merge]
---

# Session-Retro 2026-07-16 — apo-hub Handover-Cleanup + Coverage + platform-Nebenfixes (f218be)

## 1. Executive Summary

- Kernauftrag ("Handover sauberziehen, dann Coverage/Self-Login-Fix") wurde erreicht:
  `AGENT_HANDOVER.md`-Drift behoben (apo-hub#55), `apps/web/views.py`-Coverage 81%→91%
  angehoben (apo-hub#56, 19 neue Tests), Self-Login-Fix bewusst nur als Tracking-Issue
  (platform#1197) statt als Cross-Repo-Umsetzung — korrekt an die Nutzerentscheidung
  gebunden, kein Scope-Verlust.
- **Wiederholungsfund (#2/#6, Slug `handover-stale-vor-merge`, laut `retro_kpis.py`
  bereits ≥2 gate-pflichtig, real 11 vorangegangene Retro-Reports, s. §5 für Beleg):**
  `AGENT_HANDOVER.md` driftete
  **innerhalb derselben Session ein drittes Mal** — PR#56 hob den in "Offene Punkte" Punkt 1
  beschriebenen Coverage-Stand an, ohne den Eintrag selbst nachzuziehen. Das Dokument trägt
  bereits zwei eigene Warnblöcke zu genau diesem Muster (2026-07-15, 2026-07-16-Header) —
  beide griffen nicht für den PR direkt danach.
- Zwei PR-Body-Zahlenbehauptungen waren falsch, ohne gegen CI-Ground-Truth geprüft worden
  zu sein (Gesamt-Coverage "91%→94%" statt real 95%→97%; Testplan "134 Tests" statt real
  133) — beide fallen unter das org-weite `claim-before-cheapest-check`-Muster.
- Ein Merge-Blocker (platform#1203, Code-Owner-Review-Pflicht) führte zum Angebot einer
  `--admin`-Override-Option, die strukturell (Ruleset `bypass_actors: []`,
  `current_user_can_bypass: never`) nie hätte greifen können — der Versuch schlug wie
  erwartet fehl, aber die Prüfung hätte vor dem Anbieten stattfinden sollen.
- Positiv, mehrfach falsifiziert: kein Rework/Duplikat-PRs, jede Merge-Freigabe real
  eingeholt, die "pre-existing vs. Regression"-Einordnung des Health-Check-Warnings
  (apo-hub#57) hielt der unabhängigen Prüfung stand, Merge-Bestätigungen wurden vor
  Rückmeldung an den User verifiziert statt übernommen.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | apo-hub#56 PR-Body behauptet Gesamt-Coverage "91%→94%"; CI-Ground-Truth (Job `Unit Tests`, Runs `29480073723`→`29480010957`) zeigt 95%→97% (2527→2623 Statements). Einzelzahl views.py (81%→91%) korrekt. | fehlende Validierung | mittel | SURVIVES | CI-Log `TOTAL`-Zeilen beider Runs (Skeptiker-Zitat) | claim-before-cheapest-check |
| 2/6 | `AGENT_HANDOVER.md` "Offene Punkte" Punkt 1 nicht nachgezogen nach apo-hub#56 (weiterhin "81%" statt real 91%) — **drittes Auftreten desselben Musters trotz zwei eigener Warnblöcke im selben Dokument** (2026-07-15, 2026-07-16) | Prozesslücke | mittel-hoch | SURVIVES | `git show origin/main:AGENT_HANDOVER.md` (apo-hub), Commit-Historie der Datei (letzter Touch = PR#55, nicht #56) | **handover-stale-vor-merge (≥2, gate-pflichtig laut retro_kpis.py, 11 Vorkommen org-weit)** |
| 3 | apo-hub#56 Testplan-Checkbox behauptet "134 Tests grün"; CI-Log (Run `29480010957`) zeigt "133 passed" | fehlende Validierung | niedrig | SURVIVES | CI-Log-Zeile (Skeptiker-Zitat) | claim-before-cheapest-check |
| 4 | Bei blockiertem Merge platform#1203 wurde per `AskUserQuestion` u.a. "Admin-Override (--admin)" angeboten, ohne vorher zu prüfen, dass das Ziel-Ruleset (`main-required-checks`) strukturell **niemand** per Admin bypassen kann (`bypass_actors: []`, `current_user_can_bypass: "never"`) | Governance/Evidenzdisziplin | mittel | SURVIVES | `gh api repos/achimdehnert/platform/rulesets/17621471`; CODEOWNERS `*  @achimdehnert @wirdigital` | — |
| 5 | apo-hub#56 lässt bewusst 43 Zeilen `apps/web/views.py` ungetestet (verstreute Rollen-/Guard-Branches); diese Restlücke ist nirgends als Issue/Tracking-Zeile festgehalten | Anti-Pattern/Tech-Debt | mittel | SURVIVES | CI-Log Missing-Zeilen; `gh issue list --search coverage` (kein Treffer); Issue #57 behandelt nachweislich ein anderes Thema | — |
| 7 | Nach den drei Merges: 2 apo-hub-Worktrees (`handover-cleanup`, `coverage-heben`) als Orphans liegen geblieben (keine `.closed`-Lease); platform#1203-Remote-Branch nach Merge nicht gelöscht. **Korrigierte Fassung** einer ursprünglich breiteren, teilweise falschen Behauptung (Widerlegt-Begründung direkt unter dieser Tabelle). | Prozesslücke | niedrig | SURVIVES (korrigiert) | `git worktree list`; Lease-Dateien ohne `.closed`-Suffix; `gh api .../git/refs/heads/session/...ports-yaml...` (Ref existiert noch) | worktree-midsession-accumulation (verwandter, nicht identischer Slug) |
| 8 | Nutzer-Nachricht "2 was muss ich tun?" — mutmaßlich Folge eines Turns ohne die laut CLAUDE.md-Regel (≥3 Items/PR-Bezug ⇒ Board-Pflicht) vorgeschriebene nummerierte Board-Struktur | Kommunikation | — | **Hypothese** (nicht artefaktprüfbar — kein Transkript-Zugriff für den Skeptiker) | Regel-Zitat CLAUDE.md Z.63 verifiziert; konkreter Regelverstoß im Chat nicht per gh/git nachprüfbar | — |

**Widerlegt** (Begründung hier, nicht in §8 — §8 ist für *ungeklärte* Restlücken reserviert, dies ist eine *geklärte* Falsifikation): Ursprüngliche Behauptung "alle drei Worktrees (inkl. platform) blieben ungereinigt" — der platform-Worktree für `ports-yaml-apo-hub-repo-fix` wurde nachweislich sauber per `repo-session.sh end` entfernt (Lease trägt `.closed`-Suffix). Nur der schmalere Befund #7 oben überlebt.

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Beide Hauptziele erreicht (Handover-Fix, Coverage 81%→91%), Self-Login-Fix korrekt als Tracking statt Verlust geführt; Abzug für sofortige Re-Drift des Handovers (#2/#6) |
| architektur_design | 4 | Keine echten Architektur-Entscheidungen im Scope (docs/tests/1-Zeilen-YAML); Test-Design (Guard-Branch-Parametrize, Admin-CRUD-Coverage) sauber, keine strukturellen Mängel gefunden |
| code_konventionstreue | 5 | Ruff/Lint clean, Test-Namenskonvention (`test_should_*`) durchgehend eingehalten, Fixtures wiederverwendet statt dupliziert |
| risiko_debt | 2 | Org-weit konstant schwächste Dimension (Ø 2,70) — hier bestätigt: #5 (43 Zeilen ungetrackte Coverage-Lücke), #2/#6 (Handover-Doku-Drift ein drittes Mal, gate-pflichtiges Org-Muster) |
| prozess_effizienz | 3 | Solide Freigabe-Disziplin, aber #4 (Admin-Override auf totes Gate angeboten), #7 (Worktree/Branch-Cleanup unvollständig), #8 (Board-Lücke) summieren sich zu spürbarer, aber nicht schwerer Reibung |
| entscheidungsqualitaet | 4 | Durchgängig verifiziert vor Behauptung (Health-Check pre-existing-Check, Merge-Bestätigung via `gh pr view` statt Zuruf-Vertrauen); Abzug für #1/#3 (PR-Body-Zahlen nicht gegen CI geprüft) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| PR-Body-Coverage-Zahl "91%→94%" vermutlich aus einem lokalen `pytest --cov=apps`-Lauf mit abweichendem Scope übernommen, nicht gegen den CI-Job-Log geprüft (apo-hub#56) | Vor dem Schreiben von Coverage-/Test-Zahlen in eine PR-Beschreibung den tatsächlichen CI-Job-Log des zugehörigen (oder erwarteten) Runs als Quelle nehmen — lokale Worktree-Läufe nur als Vorab-Indikator, nie als zitierte Endzahl | #1 |
| `AGENT_HANDOVER.md` "Offene Punkte" Punkt 1 blieb nach apo-hub#56 unverändert, obwohl der PR genau diesen Punkt erledigt hat — drittes Auftreten trotz zweier Selbst-Warnungen im Dokument | Jeder PR, der einen in `AGENT_HANDOVER.md`/`NEXT.md` gelisteten "Offenen Punkt" abschließt, aktualisiert im selben PR (nicht erst bei `/session-ende`) den betroffenen Eintrag — als Pflicht-Diff-Zeile, nicht als Erinnerung | #2/#6 |
| Testplan-Checkbox "134 Tests grün" stammt vermutlich aus einem abweichenden lokalen `make test`-Lauf, nicht aus dem CI-Log des Merge-Commits | Testplan-Zahlen aus dem CI-Log des tatsächlichen PR-Runs übernehmen, nicht aus dem letzten lokalen Testlauf | #3 |
| Bei blockiertem Merge (platform#1203) wurde "Admin-Override" als Option angeboten, bevor geprüft wurde, ob das Ziel-Ruleset einen Admin-Bypass überhaupt zulässt | Bei `mergeStateStatus: BLOCKED` zuerst `gh api repos/<repo>/rulesets` prüfen, ob ein Admin-Override technisch greifen würde — nur tatsächlich wirksame Optionen zur Wahl stellen | #4 |
| apo-hub#56 deckte bewusst nur eine Teilmenge der fehlenden Coverage-Zeilen ab; die verbleibenden 43 Zeilen wurden nirgends als Issue/Handover-Zeile festgehalten | Bei bewusst unvollständiger Coverage-Erhöhung die Restlücke im selben Turn als kurze Zeile in `AGENT_HANDOVER.md` "Offene Punkte" oder als Issue festhalten (Hausregel "Bewusst Ausgelassenes bekommt ein Tracking-Artefakt im selben Turn") | #5 |
| Nach den drei Merges wurde keine `repo-session.sh end`-Aufräum-Runde für die beiden apo-hub-Worktrees ausgeführt; der platform#1203-Remote-Branch (extern durch `wirdigital` gemergt) wurde nicht gelöscht | Nach jedem eigenen Merge im selben Turn `repo-session.sh end` für den zugehörigen Worktree aufrufen; bei extern gemergten PRs den Remote-Branch aktiv nachziehen (`git push origin --delete <branch>`) statt anzunehmen, `--delete-branch` habe gegriffen | #7 |

**Invariante erfüllt:** 6 Soll-Schritte = 6 harte SURVIVES-Befunde (#8 als Hypothese bewusst außerhalb der Invariante, s. §8).

## 5. Längsschnitt (`retro_kpis.py`, Lauf 2026-07-16)

Beleg 1 — `python3 platform/tools/retro_kpis.py` (Rohausgabe, Auszug der Gate-Zeile):
```
→ 10 Slug(s) ≥2 ⇒ Gate-PR-Pflicht: always-instruction-without-enforcement,
  ci-gate-maskiert-failure, ci-replace-requires-job-catalog-diff,
  claim-before-cheapest-check, handover-stale-vor-merge, lint-failure-no-local-gate,
  planned-phase-no-issue, platform-pinned-perma-dirty-loop,
  scope-checkpoint-not-durably-recorded, stale-local-clone-as-ground-truth.
```
Beleg 2 — `grep -rl "handover-stale-vor-merge" platform/docs/retros/ | sort` (11 Treffer,
exakte Zählung des Rohtexts, unabhängig von `retro_kpis.py`s interner ≥2-Schwellenlogik):
```
session-retro-2026-07-02-frist-hub-a50bc6.md      session-retro-2026-07-06-iil-klickdummy-2752dc.md
session-retro-2026-07-04-platform-e17299.md       session-retro-2026-07-08-frist-hub-7f7fbd.md
session-retro-2026-07-04-platform-f5e1d.md        session-retro-2026-07-10-meiki-hub-42bfe0.md
session-retro-2026-07-05-iil-adrfw-16fd96.md      session-retro-2026-07-10-platform-d2522c.md
session-retro-2026-07-06-frist-hub-3b123e.md      session-retro-2026-07-11-platform-d2522c-incr.md
                                                   session-retro-2026-07-13-iil-klickdummy-04b5ac.md
```
`handover-stale-vor-merge` ist damit bereits **≥2 gate-pflichtig** (Beleg 1) mit **11
real gezählten Vorkommen** in vorangegangenen Retro-Reports (Beleg 2) — dieser Report ist
das **12. Vorkommen**, und zwar **innerhalb derselben Session, in der die Drift bereits
einmal explizit behoben wurde** (apo-hub#55). Das ist der stärkste Beleg dieser Session
dafür, dass eine Memory-Notiz allein das Muster nicht durchbricht — `AGENT_HANDOVER.md`
selbst enthält bereits zwei Warnblöcke zu genau diesem Thema, beide griffen nicht.

`refuted_rate` dieser Session: **0,125** (1 von 8 Behauptungen widerlegt). Org-weiter Trend zum Vergleich (`retro_kpis.py`): `f4a546:0.00 · d2522c-incr:0.40 · d2b425-incr:0.60 · d2b425:0.33 · 04b5ac:0.43 · 0ba8b4:0.36 · c494a2-incr:0.11 · 590926:0.10`. Der Wert 0,125 liegt am unteren Rand dieses Bands (nahe den beiden niedrigsten Werten 0,10/0,11) — Phase-5-Meta-Reviewer soll das rein numerisch einordnen, nicht die Einzel-Verdikte neu bewerten.

Score-Mittel der letzten 29 Retros zum Vergleich: `risiko_debt 2,69` — diese Session liegt mit `2` leicht darunter, konsistent mit der Einordnung als "konstant schwächste Dimension".

**5b. Autonomie-Kalibrierung:**
- `over_ask: 1` — die Rückfrage, ob für den Cloudflare-Access-Health-Check-Gap ein Issue angelegt werden soll, war laut Hausregel ("Bewusst Ausgelassenes bekommt im SELBEN Turn ein Tracking-Artefakt — sonst gilt es als nicht existent") kein echter Gate-Fall (nicht irreversibel, kein Prod-Schritt, kein drittes Repo, keine Governance-Config, kein Spend) — das Anlegen hätte direkt erfolgen können/sollen, statt es zur Wahl zu stellen.
- `over_act: 0` — alle gate-pflichtigen Aktionen (3× Merge-Freigabe, 1× Admin-Override-Versuch) wurden vorher explizit eingeholt; kein Fall von autonomem Handeln an einem der fünf Gates ohne vorherige Freigabe gefunden.

## 6. Verankerung (Vorschläge — Verankerung entscheidet der Mensch)

**memory_candidates:**

```markdown
---
name: handover-drift-recurs-within-session
description: AGENT_HANDOVER.md kann noch INNERHALB derselben Session erneut driften, direkt nachdem die Drift explizit behoben wurde — ein Folge-PR, der einen "Offene Punkte"-Eintrag erledigt, zieht das Dokument nicht automatisch nach. Slug handover-stale-vor-merge ist bereits 11x org-weit gate-pflichtig; Memo-Wiederholung allein wirkt nachweislich nicht.
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-16-apo-hub-handover-redrift
---

Nach jedem PR, der einen in AGENT_HANDOVER.md/NEXT.md unter "Offene Punkte" gelisteten
Punkt sachlich erledigt, im SELBEN PR den Eintrag streichen/aktualisieren — nicht erst
bei /session-ende. Realfall 2026-07-16 (apo-hub): PR#55 behob die Handover-Drift explizit
(inkl. eigenem Warnblock im Dokument), PR#56 (direkt danach, "Coverage heben") hob den
in Offene-Punkte-Punkt-1 beschriebenen Zustand an, ohne den Eintrag selbst zu berühren —
dritte Instanz desselben Musters trotz zweier Selbst-Warnungen im selben Dokument.

**Why:** Handover-Pflege ist aktuell nur an /session-ende gebunden (task-getaktet wäre
richtig, ist aber session-getaktet) — jeder Mehr-PR-Batch produziert daher zwangsläufig
zwischenzeitlich veraltete Einträge.

**How to apply:** Vor dem Merge eines PRs prüfen, ob dessen Diff einen Punkt aus
AGENT_HANDOVER.md "Offene Punkte" sachlich erledigt — falls ja, den Eintrag im selben PR
nachziehen, nicht als separaten Folge-Task vertagen. Siehe [[handover-stale-vor-merge]]
(org-weiter Gate-Kandidat, retro_kpis.py).
```

```markdown
---
name: claim-numeric-in-pr-body-against-ci-log
description: PR-Body-Zahlen (Coverage-Prozent, Testanzahl) müssen gegen den tatsächlichen CI-Job-Log geprüft werden, nicht aus dem letzten lokalen Testlauf übernommen werden — zwei von zwei geprüften Zahlen in apo-hub#56 waren falsch (Coverage 91%→94% behauptet vs. real 95%→97%; 134 Tests behauptet vs. real 133).
metadata:
  type: feedback
---

Vor dem Schreiben einer Zahlen-Behauptung (Coverage-Prozent, Testanzahl, Zeilen-Diff) in
einen PR-Body: den tatsächlichen CI-Job-Log des Runs zitieren, nicht den letzten lokalen
Worktree-Lauf. Realfall 2026-07-16 (apo-hub#56): beide im PR-Body genannten Summenzahlen
(Gesamt-Coverage, Testanzahl) waren falsch, obwohl die Einzelzahl (views.py-Coverage)
korrekt aus dem lokalen Lauf übernommen wurde — lokaler und CI-Coverage-Scope
unterscheiden sich vermutlich in `--cov`-Konfiguration/Omit-Liste.

**Why:** claim-before-cheapest-check ist bereits org-weit gate-pflichtig; diese Session
liefert zwei weitere, saubere Einzelbelege für dieselbe Fehlerfamilie.

**How to apply:** Bei jeder PR-Body-Zahl mit Coverage-/Test-Bezug: `gh run view --job
<id> --log | grep TOTAL` (bzw. äquivalent) vor dem Schreiben ausführen.
```

**adr_candidates:** keine — kein Fund berührt eine Architektur-Entscheidung (ADR-Schwelle
laut `policies/adr-threshold.md` nicht erreicht: reine Doku-/Test-/Daten-Fixes).

**gate_candidates:**
- `handover-sync-gate` (NEU, abgeleitet aus dem 12. Vorkommen von `handover-stale-vor-merge`):
  Ein CI-Check (oder `repo-session.sh end`-Hook) für Repos mit `AGENT_HANDOVER.md`, der
  warnt/fehlschlägt, wenn ein PR-Body die Formulierung "Bezieht sich auf Handover-Punkt N"
  o. ä. enthält, aber `AGENT_HANDOVER.md` nicht im selben Diff geändert wird. 11+
  Memo-Wiederholungen ohne wirksamen Fix belegen: das Muster braucht einen technischen
  Gate, keine 12. Notiz.

## 7. Maßnahmen (Action-Board)

🔵 **Ich kann sofort**

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | `AGENT_HANDOVER.md` Offene-Punkte-Punkt-1 nachziehen (Coverage jetzt 91%, nicht 81%) | apo-hub | — | 🔵 ready | PR erstellen |
| 2 | 2 apo-hub-Worktrees (`handover-cleanup`, `coverage-heben`) aufräumen | apo-hub | — | 🔵 ready | `repo-session.sh end` je Worktree |
| 3 | platform#1203-Remote-Branch löschen | platform | https://github.com/achimdehnert/platform/pull/1203 | 🔵 ready | `git push origin --delete session/2026-07-16/achim-dehnert/ports-yaml-apo-hub-repo-fix` |
| 4 | Coverage-Restlücke (43 Zeilen `views.py`) als Issue tracken | apo-hub | — | 🔵 ready | Issue anlegen mit Missing-Zeilen-Liste |

🟢 **Offen — dein Zug**

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 5 | `handover-sync-gate` als CI-Check/Hook verankern (12. Vorkommen desselben Musters) | platform | — | 🟢 offen | Priorität/Umsetzung bestätigen |
| 6 | Memory-Kandidaten oben speichern/verwerfen | — | — | 🟢 offen | Ja/Nein je Kandidat |

## 8. Nicht verifiziert (Restlücken)

- **Befund #8** (Board-Nummerierungslücke → "2 was muss ich tun?"): als Hypothese geführt,
  weil kein Transkript-Zugriff für den unabhängigen Skeptiker bestand. Billigster Check:
  den tatsächlichen Chat-Turn vor der User-Nachricht gegen die CLAUDE.md-Board-Regel lesen
  (im Haupt-Kontext dieser Retro-Session zwar vorhanden, aber laut Regel 1 [Richter≠
  Angeklagter] nicht durch den Haupt-Kontext selbst zu verifizieren, sondern durch einen
  künftigen frischen Reviewer mit Transkript-Zugriff).
- **Herkunft der falschen PR-Body-Coverage-Zahl** (Befund #1): plausible Hypothese (anderer
  `--cov`-Scope im lokalen Lauf vs. CI-Job), aber nicht abschließend belegt — der genaue
  CI-Coverage-Aufruf liegt vermutlich in einer shared-ci-Reusable-Action, nicht im
  apo-hub-Repo selbst. Billigster Check: shared-ci-Workflow-Definition lesen.
- **Phase 6 (Extern-Handoff):** nicht durchgeführt — Footprint `full`, nicht `deep`;
  laut Skill nur bei `deep` vorgesehen.
