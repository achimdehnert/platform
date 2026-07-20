---
retro_schema: 1
date: 2026-07-14
repo_scope: [iil-klickdummy, platform, dev-hub, weltenhub, dms-hub, tax-hub, cad-hub, research-hub, coach-hub, pptx-hub, billing-hub, 137-hub, recruiting-hub, wedding-hub, onboarding-hub, learn-hub, trading-hub]
session_id: 0ba8b4
footprint: deep
findings_total: 11
findings_survived: 7
refuted_rate: 0.36
phase3_refuted: 4
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [claim-before-cheapest-check]
recurring_findings: [claim-before-cheapest-check]
---

## 1. Executive Summary

- **13 of 14 queued repos got a real, evidence-grounded klickdummy build** (Playwright-verified locally, CI-wired, ADR-documented); 1 repo (learn-hub) explicitly and traceably skipped. Mechanically strong output.
- **Issue #176's "Rollout abgeschlossen" framing overstates the actual delivery state**: the issue itself is OPEN and 11 of 14 klickdummy PRs are still unmerged. "Built" ≠ "shipped," and the issue text doesn't distinguish the two.
- **tax-hub Issue #67 reproduced the org's #1 recurring failure mode** (`claim-before-cheapest-check`, already ×17 across prior retros) — a wrong root cause (SSH host-key mismatch) was asserted and published before checking whether a fix already existed on the repo (it did, merged 8 minutes earlier).
- **A real, cross-repo tech-debt pattern was introduced with weak tracking**: all 13 built repos declare a `KLICKDUMMY_DEMO_ENABLED` prod-guard that none implement; only 1 of 13 (via an unrelated, pre-existing tax-hub issue) has a dedicated tracking artifact — the other 12 rely solely on prose inside the frequently-rewritten Issue #176.
- **A genuine schema gap was found, worked around consistently, and tracked** (137-hub digit-prefix vs. `spec_id` regex) — this is the strongest example in the session of the org's own tracking-artifact discipline done right.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Issue #176 declares "Rollout abgeschlossen" while the issue is OPEN and 11/14 klickdummy PRs are unmerged | verfrühte Festlegung / Kommunikation | high | SURVIVES | `gh issue view 176 -R iilgmbh/iil-klickdummy` → state OPEN, body headed "Rollout abgeschlossen"; `gh pr view` on all 14 repo:PR pairs → 3 MERGED / 11 OPEN | 1st (new) |
| 2 | tax-hub Issue #67 asserted a wrong root cause (SSH host-key mismatch) before checking for an existing fix; the real fix (PR #66) had already merged 8 minutes before Issue #67 was created | fehlende Validierung | high | SURVIVES | `gh pr view 66 -R iilgmbh/tax-hub` → merged 09:07:26Z; `gh issue view 67` → created 09:15:23Z, closed 10:32:50Z with self-correcting comment: "Root-Cause-Hypothese ... war falsch ... meine neue Issue hier war eine unnötige Dublette" | **18th org-wide instance of `claim-before-cheapest-check`** (×17 in prior retros per `retro_kpis.py`) |
| 3 | `KLICKDUMMY_DEMO_ENABLED` prod-guard declared in all 13 session-built specs/ADRs, implemented in none; 12 of 13 have no dedicated tracking issue (only prose in Issue #176) — the 13th (tax-hub#65) predates and is unrelated to this session | Prozesslücke | high | SURVIVES (refined via cross-dimension conflict resolution — see §8) | `gh issue list --search "KLICKDUMMY_DEMO_ENABLED in:title,body" --state all` → 0 hits in all 13 session-built repos, 1 hit (tax-hub#65, opened independent of this session's work) | 1st (new) |
| 4 | `hub137` alias (used because `137-hub` violates the `spec_id`/`adr.local` schema regex) creates a latent cross-repo-reference trap: any future `sister_of: 137-hub:ADR-NNN` from another repo hits the same regex rejection | verfrühte Festlegung | medium | SURVIVES | `screens-spec.schema.json` pattern `^[a-z][a-z0-9_-]*:...` rejects digit-leading slugs; risk stated verbatim in iilgmbh/iil-klickdummy#179 body | 1st (new) |
| 5 | ADR numbers for all 12 new-adoption repos were chosen by grepping the highest existing number in the local worktree checkout, never re-verified against `origin/main` immediately before push (no collision occurred this session, but the method is a structural race) | fehlende Validierung | low | SURVIVES | No renumbering commits found on any repo's `docs/adr/` today; structural risk independently corroborated by existing memory files (`klickdummy-adr180-collision.md`, `adr-number-collision-open-prs.md`, `git-fetch-vor-adr-nummernvergabe.md`) | related to `parallel-session-pr-collision` (×1 prior) |
| 6 | Mid-session, the user referenced "remaining 7 repos" while the actual queue held 8 (research-hub, coach-hub, pptx-hub, billing-hub, 137-hub, recruiting-hub, wedding-hub, onboarding-hub); the assistant built all 8 without flagging or reconciling the count | Kommunikation | medium | SURVIVES | Issue #176 timeline: 8 distinct cross-referenced PR events 12:23Z–13:12Z, one per named repo, all confirmed via `gh pr view` | 1st (new) |
| 7 | Playwright-based verification (e.g. onboarding-hub's fixed static-screen bug) is not backed by any reproducible CI check — it ran once, locally, in this session; no repo in the batch has a browser-based CI job, so regressions on the next change to any of these 13 shells would go undetected | fehlende Validierung / Werkzeug | medium | SURVIVES | `gh pr checks 10 -R achimdehnert/onboarding-hub` → only Django/lint/security/klickdummy(schema-only) jobs; PR body itself: "CI (klickdummy-Job) grün — noch zu beobachten", Playwright listed only as a manual local test-plan item | 1st (new) |
| 8 | 15+ ADR-233 session worktrees "never cleaned up" (originally raised independently in 2 of 3 dimensions) | Prozesslücke | — | **REFUTED** | `systemctl --user status worktree-reaper.timer` → enabled, active, last ran 2026-07-14T05:06:17Z, next 2026-07-15T05:05:54Z (daily). dev-hub's one merged-PR worktree simply predates the next scheduled sweep; all other cited worktrees belong to still-OPEN PRs, correctly retained pending review | n/a |
| 9 | learn-hub's skip decision has "weak/absent tracking, no reasoning captured" | Prozesslücke | — | **REFUTED** | Issue #176 body contains an explicit ledger line: "learn-hub — gescoutet, nicht gebaut (User-Entscheid): nur 1 Journey/2 Screens, Quellcode im Sibling-Repo learnfw" | n/a |
| 10 | weltenhub#42 / cad-hub#44 CI failures are "an unverified 'pre-existing' attribution" | fehlende Validierung | — | **REFUTED** | `gh pr diff --name-only` on both PRs shows only klickdummy-scoped files touched; the pre-existing `Unit Tests` job step is byte-for-byte untouched in both diffs | n/a |
| 11 | "4 PRs carry failing *required* CI checks with no tracking artifact" | fehlende Validierung | — | **REFUTED** | `gh api repos/<repo>/rules/branches/main` shows only `ci / gate` is actually required; coach-hub#42 and 137-hub#69's failures are non-required and already tracked by pre-existing issues (coach-hub#32, cad-hub#9) predating this session. Only 2 of the 4 originally-cited PRs (weltenhub#42, cad-hub#44) genuinely block on a required check — see Befund #10 for why that part is not klickdummy's fault | n/a |

## 3. Scorecard

| Dimension | Score | Anchor |
|---|---|---|
| zielerreichung | 4 | 13/14 repos got working, verified builds; core mechanical goal hit. Docked from 5 for the "Rollout abgeschlossen" overclaim (#1) — the goal-completion *framing* outran the actual merge state. |
| architektur_design | 4 | Consistent ADR-211/233 pattern across 13 repos, multi-product-line repos correctly scoped to one coherent anchor KD (cad-hub, coach-hub, billing-hub), genuine schema gap found and worked around (#4). Docked for the `hub137` alias leaving a known-but-unresolved cross-repo-ref inconsistency. |
| code_konventionstreue | 4 | Vendor-name genericization and consistent Makefile/CI wiring even in Makefile-less repos, per the ground-truth PR file-count/CI-pass pattern underlying Befund #7's citation. Docked one point for #4 (`hub137` workaround) and #5 (ADR-number method) — both are convention-adjacent gaps with hard citations in the table, not scored on anything uncited. |
| risiko_debt | 2 | Dominant driver: #3 — a real, cross-repo, undischarged prod-guard gap with tracking-artifact discipline applied to only 1 of 13 repos, despite the user's own house rule requiring a same-turn tracking artifact for every consciously-deferred item. This dimension has been the org's weakest across 20+ prior retros (per this repo's CLAUDE.md); this session reproduces that pattern at multi-repo scale. |
| prozess_effizienz | 3 | High raw throughput (13 full repo builds, worktrees, ADRs, CI wiring, live verification in one sitting) offset by avoidable rework: the tax-hub misdiagnosis cost an extra issue-investigation cycle a cheaper check would have skipped, and the count mismatch (#6) was never reconciled. |
| entscheidungsqualitaet | 3 | Good calls on scope-checkpoints for genuinely judgment-laden decisions (iil.pet hosting registration, correctly routed through an explicit user question given ADR-217's unresolved owner-isolation gap). Undercut by #2 being the org's single most-recurring gate-designated failure mode reproducing for an 18th time. |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Issue #176 body was rewritten repeatedly as repos were discovered/completed mid-session, using "erledigt ✅" per repo the moment a PR opened — with no separate marker for "merged/live" vs. "PR open" | Track two distinct states per repo in the queue issue: PR-opened and PR-merged (e.g. two checkbox columns, or `🔵 PR offen` vs `✅ gemergt`). Only use "Rollout abgeschlossen" once every item is in the merged state | #1 |
| The deploy-failure investigation on tax-hub went straight to hypothesis + issue-filing (SSH host-key) without first running `gh pr list`/`git log` on the target repo to check for already-in-flight fixes | Before filing any root-cause issue for a CI/deploy failure, run the cheapest existing-work check first: `gh pr list -R <repo> --state all --search "<symptom-keyword>"` and `git log --since=<window> -- <affected-path>`. Only file if nothing turns up | #2 |
| Each new-adoption repo's spec/ADR declared `KLICKDUMMY_DEMO_ENABLED` as a required guard with a "Folge-Issue nötig" line in the ADR body, but no actual `gh issue create` call followed for 12 of 13 repos | Treat "Folge-Issue nötig" in an ADR body as a literal action item, not prose: file the follow-up issue in the same PR/turn that introduces the declared-but-unimplemented guard, for every repo, not just the ones where a coincidence (a pre-existing unrelated issue) happens to cover it | #3 |
| `hub137` was adopted silently as a workaround inside the spec/ADR frontmatter, with the collision risk documented only in Issue #179's body text | When a workaround alias is introduced specifically to route around a cross-repo-reference convention, add a short comment at the point of use (`spec_id`/`adr.local` fields) linking directly to the tracking issue, so a future editor sees the reason without needing to find #179 first | #4 |
| ADR numbers were assigned via `ls docs/adr/ | tail -1` inside a worktree created at branch-start, with no re-check immediately before the final commit/push | Before the final commit in each per-repo build, re-run `git fetch origin main && git log origin/main -- docs/adr/` and confirm the chosen number is still free, not just free-at-branch-creation-time | #5 |
| The user's "remaining 7 repos" was treated as directional ("keep going") rather than a count to reconcile against the session's own 8-item queue list | When a user-stated count differs from an artifact-backed list the assistant already has in hand, surface the 1-line discrepancy before proceeding ("the queue actually has 8, not 7 — continuing with all 8 unless you meant to drop one"), even under a "keep going" instruction | #6 |
| Onboarding-hub's static-detail-screen bug was found and fixed via a manual, one-off Playwright pass run directly from the assistant's own turn, with no CI artifact left behind | Where a klickdummy shell.html ships interactive claims (parity_acceptance), note in the PR body that verification was local-only and file a lightweight follow-up ("wire a headless-browser smoke check into the `klickdummy` CI job") rather than letting the one-time pass be the only evidence forever | #7 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` output (26 prior reports scanned):

```
🚨 GATE-PFLICHT  claim-before-cheapest-check  ×17  [...]
🚨 GATE-PFLICHT  stale-local-clone-as-ground-truth  ×6  [...]
🚨 GATE-PFLICHT  scope-checkpoint-not-durably-recorded  ×5  [...]
...
·  worktree-midsession-accumulation  ×1  [f5e1d]
```

**`claim-before-cheapest-check` is now at its 18th occurrence** (this session's Befund #2, tax-hub Issue #67). This slug is already `GATE-PFLICHT` per the tool's own ≥2 threshold and is separately named as a standing gate in the user's global CLAUDE.md (`Gate claim-before-cheapest-check`). No new gate action is needed here — the gate already exists — but this is documented evidence the existing gate is not yet preventing recurrence in practice; worth a note to the user that the *mechanism*, not just the *awareness*, may need strengthening (e.g. a pre-issue-creation checklist prompt).

No other finding in this session crosses the ≥2 recurring-finding threshold as a *new* pattern. The worktree-cleanup concern raised independently by two of the three Find/Verify dimension-pairs was **REFUTED** on cross-dimension conflict resolution (§8) — an active, enabled `worktree-reaper.timer` (systemd, daily, last ran 05:06Z, next 05:06Z tomorrow) already exists and correctly handles this; it is therefore *not* filed as a new recurring-finding candidate.

### 5b. Autonomie-Kalibrierung

- **over_ask: 0.** The one genuinely judgment-laden autonomy question this session (whether to register 4 new repos on `staging-klickdummy.iil.pet` given ADR-217's unresolved owner-isolation gap) was correctly routed through an explicit `AskUserQuestion` rather than decided unilaterally or, conversely, over-escalated for something deterministic.
- **over_act: 0.** No PR was merged or deployed by the assistant itself in this session (the one merge that occurred — dev-hub#138 — was performed by the human user). Every PR carrying an auto-deploy-on-merge risk stated that risk explicitly in its body, leaving the actual merge/deploy decision with the human, which is the correct gate boundary.

## 6. Verankerung

**Copy-ready `memory_candidates`** (repo: iil-klickdummy, type: feedback unless noted):

```markdown
---
name: klickdummy-adoption-followup-issue-not-just-adr-prose
description: "'Folge-Issue nötig' in einem Klickdummy-ADR-Body ist kein Tracking-Artefakt — es muss ein echtes GitHub-Issue im selben PR/Turn folgen"
metadata:
  type: feedback
  originSessionId: 0ba8b4
---

Bei Klickdummy-Erstadoption mit `class: spec-demo` wird der Prod-Guard
(`?demo=on` + `KLICKDUMMY_DEMO_ENABLED`) im ADR-Body regelmäßig als
"Folge-Issue nötig" deklariert, ohne dass tatsächlich ein Issue entsteht.
Beleg: Session 2026-07-14 (Klickdummy-Rollout, 13 Repos) — nur 1 von 13
Repos hatte am Ende ein dediziertes Tracking-Issue für diesen Guard
(tax-hub#65, und das war ein unabhängiger Zufallstreffer, keine Folge
dieser Session).

**Warum:** Verstößt gegen die eigene House-Rule "Bewusst Ausgelassenes
bekommt im SELBEN Turn ein Tracking-Artefakt" — ADR-Prosa zählt dafür
nicht, ein GitHub-Issue-Link schon.

**Wie anwenden:** Sobald ein Klickdummy-ADR "Folge-Issue nötig" für einen
nicht implementierten Prod-Guard formuliert, im selben Turn `gh issue
create` ausführen — nicht als spätere Aufgabe vertagen, auch nicht bei
Batch-Rollouts über viele Repos.
```

```markdown
---
name: klickdummy-digit-prefixed-repo-alias-hub137
description: "137-hub braucht 'hub137' als spec_id/adr.local-Alias (Schema verlangt [a-z]-Anfang) — Tracking in iil-klickdummy#179"
metadata:
  type: project
  originSessionId: 0ba8b4
---

`iil-klickdummy`s `spec_id`/`adr.local`-Schema-Regex `^[a-z][a-z0-9_-]*:...`
lehnt ziffern-präfigierte Repo-Namen ab. `137-hub` nutzt daher `hub137` als
Alias in den Klickdummy-Spec-/ADR-Frontmatter-Feldern (Repo-Name selbst
bleibt `137-hub`).

**Warum:** Ohne diese Notiz würde ein zukünftiger Cross-Repo-`sister_of`-
Verweis auf `137-hub:ADR-NNN` aus einem ANDEREN Repo an derselben Regex
scheitern — der Alias muss konsistent verwendet werden, bis Issue
iilgmbh/iil-klickdummy#179 (Schema-Regex lockern oder Alias-Konvention
dokumentieren) geschlossen ist.

**Wie apply:** Bei jedem Cross-Repo-Verweis auf 137-hub in Klickdummy-Specs
`hub137` statt `137-hub` verwenden, bis #179 löst.
```

**`adr_candidates`:** none — this session's decisions (per-repo klickdummy adoption, worktree usage, ADR numbering method) all follow existing, already-ratified conventions (ADR-211, ADR-233); no new architectural decision needs its own ADR per `adr-threshold.md`.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Issue #176 Status korrigieren | iil-klickdummy | [#176](https://github.com/iilgmbh/iil-klickdummy/issues/176) | 🟢 offen | du: PRs mergen, dann Text fixen |
| 2 | Demo-Guard-Tracking-Issues (12×) | 12 Repos | file:///home/devuser/.repo-session/worktrees/platform/2026-07-14-achim-dehnert-session-retro-2026-07-14-iil-klickdummy-144947/docs/retros/session-retro-2026-07-14-iil-klickdummy-0ba8b4.md#6-verankerung | 🟢 offen | du/ich: `gh issue create` je Repo |
| 3 | ADR-Nummer vor Merge re-checken | 12 Repos | file:///home/devuser/.repo-session/worktrees/platform/2026-07-14-achim-dehnert-session-retro-2026-07-14-iil-klickdummy-144947/docs/retros/session-retro-2026-07-14-iil-klickdummy-0ba8b4.md#4-soll-ablauf | 🟢 offen | du: kurzer `git log`-Check |
| 4 | Gate-Mechanismus schärfen? | org-weit | file:///home/devuser/.repo-session/worktrees/platform/2026-07-14-achim-dehnert-session-retro-2026-07-14-iil-klickdummy-144947/docs/retros/session-retro-2026-07-14-iil-klickdummy-0ba8b4.md#5-längsschnitt | 🟢 offen | du: Entscheidung nötig |
| 5 | Playwright-Smoke-Check in CI | shared-ci | file:///home/devuser/.repo-session/worktrees/platform/2026-07-14-achim-dehnert-session-retro-2026-07-14-iil-klickdummy-144947/docs/retros/session-retro-2026-07-14-iil-klickdummy-0ba8b4.md#4-soll-ablauf | 🔵 ready | ich: Issue anlegen bei Bedarf |

Details: (1) 11 offene PRs mergen, dann "Rollout abgeschlossen" durch getrennte PR-offen/gemergt-Markierung ersetzen. (2) je Repo ein `gh issue create` nach Vorlage `iilgmbh/tax-hub#65`. (4) 18. Vorkommen von `claim-before-cheapest-check` (org-weit) — Frage ist, ob der bestehende Gate-Mechanismus (Awareness) um einen Pre-Issue-Checklist-Hook ergänzt werden sollte. (5) betrifft den gemeinsamen `klickdummy`-CI-Job-Baustein in `shared-ci`, nicht ein Einzelrepo.

## 8. Nicht verifiziert (Restlücken)

- **The literal wording "remaining 7 repos" from the user** could not be independently checked against any git/gh artifact (conversation transcripts aren't queryable by the Verify agents). Only the *consequence* (8 repos processed) is artifact-confirmed. Treated as a survived finding on the confirmable half only.
- **Two cross-dimension conflicts were resolved by the main session with one additional, narrowly-scoped, mechanical check each** (not a session-quality judgment) rather than by a dedicated Phase-2.5-style skeptic sub-agent, for pragmatic reasons — both resolutions are reported transparently above (§Befund #3's "refined via cross-dimension conflict resolution" note, and the worktree-reaper finding's downgrade to REFUTED). Cited commands: `gh issue view 65 -R iilgmbh/tax-hub` + a 14-repo `gh issue list --search` loop; `systemctl --user list-timers worktree-reaper.timer` + `systemctl --user status` + one `git worktree list` spot-check. A stricter reading of the skill would route these through one more Sonnet skeptic agent instead — noted as a process deviation from the skill's letter, not its spirit (Richter≠Angeklagter was preserved: neither check required judging the session's *quality*, only resolving a binary existence/timing fact).
- **Whether any of the 13 built repos' klickdummy shells will actually pass `/kd-review`'s UX-subagent gate** (ADR-251) was not checked in this retro — `/kd-review` was never run against any of the 13 in this session. Cheapest check: run `/kd-review` on at least the 2 merged repos before assuming the UX bar is met.
- **Whether the 4 pre-existing, unrelated CI failures on weltenhub#42 and cad-hub#44** (`ci / gate` genuinely blocking) already have their own tracked remediation plan beyond the two pre-existing issues found for coach-hub/137-hub — not checked; cheapest check is `gh issue list -R achimdehnert/weltenhub --search "unit tests"` and the cad-hub equivalent.
