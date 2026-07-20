---
retro_schema: 1
date: 2026-06-30
repo_scope: [platform, apo-hub, travel-beat, ttz-hub, iil-adrfw, iil-codeguard, iil-ingest, iil-enrichment, nl2cad]
session_id: 0181a7-incr
footprint: full
footprint_reduction_reason: "Rule-B deep (>=6 Repos + Prod-Deploys) → full: (a) alle Prod-Schritte menschlich !-getriggert, (b) rollback-fähig keine Migration, (c) Increment-Minimum bei Prod-Schritt. Transparente, self-korrigierende Session."
findings_total: 11
findings_survived: 10
refuted_rate: 0.09
phase3_refuted: 1
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 2
  entscheidungsqualitaet: 2
gate_candidates: [analytical-claim-cheapest-check, canary-must-target-real-consumer]
recurring_findings: [claim-before-cheapest-check, scope-checkpoint-not-durably-recorded, shipped-executable-no-pre-merge-mode-check]
---

# Session-Retro Increment 2026-06-30 — platform (apo-hub GHCR · Meter · /repo-optimize · ttz-hub)

> Increment auf dem ersten Retro (`0181a7`). Nur neue Arbeit nach dem Publish-Gate-Cluster.

## 1. Executive Summary
- **Schärfster Befund: der zentrale #762-GHCR-Fix hat KEINEN sauber-verifizierten Consumer-Deploy.** Der Canary (travel-beat) nutzt `_deploy-hetzner.yml` gar nicht + lief vor dem Merge; der Fallback „apo-hub beweist es" (mein In-Conversation-Claim) ist nicht sauber belegt (Run pre-merge, Login im Build- nicht Deploy-Job).
- **`claim-before-cheapest-check` rezidiviert massiv** (Längsschnitt ×12): Canary-Ziel ungegreppt, „7 Consumer" ungegreppt, „#762 verifiziert" ungeprüft, #767 Policy-Compliance ungeprüft. Der im 1. Retro gebaute Pre-Push-Gate (#748) deckt CODE, nicht die **analytischen** Claims — die versagten erneut.
- Technisch solide gebaut (Guard/Meter/Skill, apo-hub-Fix mechanisch korrekt), aber 2 verschwendete Prod-Deploys (travel-beat) + ship-then-fix (#767→#768).
- Neue Risiken: Meter-KeyError-Bug (E4), ttz-lif-Gov-Security-Funde irreversibel in platform-Git-History (E8).
- Vorbildlich: ttz-hub-Security NICHT auto-gefixt (Issue), eigene Worktrees/Leases sauber geschlossen, Eigen-Fehler innerhalb der Session mehrfach selbst gefangen.

## 2. Befund-Tabelle
| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| F1 | #762-Canary wertlos: travel-beat nutzt `_deploy-hetzner` nicht + lief 2min vor Merge; „apo-hub beweist es" nicht sauber belegt (Run 13:57<Merge 15:09, Login im Build- nicht Deploy-Job) → **#762 unverifiziert** | fehlende Validierung | kritisch | SURVIVES | C1/C2/C3; travel-beat/deploy.yml(kein _deploy-hetzner); run 28449880751 createdAt 13:57Z | claim-before-cheapest-check, verified-before-end-to-end |
| F2 | „7 @main-Consumer Fleet-Fix" (PR#762-Body) — real ≤3, 1 aktiv (apo-hub) | Scope-Überzug | hoch | SURVIVES | C4; gh search `_deploy-hetzner.yml@main --owner achimdehnert` → 1 App-Consumer; `~/shared/deploy-convergence-audit-2026-06-30.md` | claim-before-cheapest-check |
| F3 | #767 ohne `mode:`/Output-Format/Changelog gemergt → #768 37min später | verfrühter Merge | mittel | SURVIVES | Finder-Beleg (nicht Skeptiker): diff #767↔#768 ergänzt `mode:`+`## Output-Format`+`## Changelog`; #768-Body „#767 hatte Lücken" | shipped-executable-no-pre-merge-mode-check |
| F4 | Meter `os.environ["GH_TOKEN"]` (direkter Dict-Zugriff) im `--local`-Pfad ohne Guard → KeyError | fehlende Validierung | mittel | SURVIVES | C5; publish_gate_meter.py:199 vs Guard nur else-Zweig | — |
| F5 | ttz-lif-Gov-Security-Funde (Klartext-PW-Ref, OpenAI) in platform-Git-History geschrieben (repo-optimize.md Changelog + #768-Body) — irreversibel | Data-Sovereignty / nicht-reversibler Record | mittel | SURVIVES | C6; repo-optimize.md:100-105; PR#768-Body | — |
| F6 | Word-Boundary-Fix #745 `\btest\b` matcht `tests`/`run-tests` (Plural) NICHT → False Negative | untested edge-case | niedrig | SURVIVES | C7; `re.search(...,'tests')`==None | — |
| F7 | #762 (Prod-Deploy, 2. Repo) ohne dokumentierten Scope-Checkpoint im PR-Body | Scope-Checkpoint-Gap | mittel | SURVIVES | S4; PR#762-Body (kein Checkpoint-Satz) | scope-checkpoint-not-durably-recorded |
| F8 | #762 mit `[DRAFT]` im gemergten Titel + 2× BEHIND→update-branch | Aufräum-Disziplin | niedrig | SURVIVES | P4; gh pr view 762 title/commits | — |
| F9 | ttz-hub PR#22 + Security-Issue#23 ohne Labels/Assignees → Issue könnte untergehen | Handoff-Disziplin | niedrig | SURVIVES | P6; gh ... --json labels,assignees → [] | — |
| F10 | `_deploy-hetzner.yml` ohne `permissions:`-Block (stille Caller-Abhängigkeit) + GHCR_TOKEN-`.env.prod`-Write nach #762 redundant | Tech-Debt | niedrig | SURVIVES | E1/E2; `_deploy-hetzner.yml` grep `permissions:` → 0 Treffer; `_deploy-hetzner.yml:273-280` (env.prod-Block) | — |
| — | (Finder-3) „apo-hub-Canary beweist #762" | Validierung | — | REFUTED | C1: Run pre-merge, Login im Build-Job | — |

## 3. Scorecard (1–5, je an Befund verankert)
- **zielerreichung 3** — Retro-Fixes + Skill + apo-hub-Fix geliefert, aber #762 (Kern-Deliverable) **unverifiziert** (F1).
- **architektur_design 3** — Guard/Meter/Skill tragfähig; #762 mechanisch korrekt aber permissions/env.prod-Debt (F10).
- **code_konventionstreue 3** — #767 non-compliant gemergt (F3), Word-Boundary-Plural-Lücke (F6), Meter-KeyError (F4).
- **risiko_debt 2** — unverifizierter Prod-Fix (F1) + irreversible Gov-Funde in platform-History (F5) = reale unmitigierte Risiken.
- **prozess_effizienz 2** — 2 verschwendete Prod-Deploys (F1), #767→#768-Rework (F3), #762 BEHIND×2 (F8).
- **entscheidungsqualitaet 2** — Canary-Wahl schlecht (F1), 7-Consumer-Überzug (F2), Gov-in-History nicht bedacht (F5); Gate-Disziplin (kein Self-Merge) aber gewahrt.

## 4. Soll-Ablauf (Ist → Soll → eliminiert)
| Ist (Beleg) | Soll | eliminiert |
|---|---|---|
| travel-beat als #762-Canary gewählt + vor Merge getriggert, ohne zu prüfen ob es den Reusable nutzt | Canary für einen Reusable-Fix MUSS ein Repo sein, das ihn `uses:` (grep), getriggert NACH dem Merge; vor „validiert" den Consumer-grep + Post-Merge-Timestamp zitieren | #F1 |
| „7 @main-Consumer" in den PR-Body geschrieben ohne grep | Reichweiten-Zahl vor dem Schreiben per `grep -rl '<reusable>@'` belegen; Quell-Repos ausschließen | #F2 |
| #767 gemergt, dann Compliance-Lücken in #768 nachgezogen | Vor Skill-Merge die `claude-skills`-Pflichtstruktur-Checklist (mode/Output-Format/Changelog/Dogfood) gegen die Datei halten | #F3 |
| `os.environ["GH_TOKEN"]` direkt nach if/else, im --local-Pfad ungeguarded | Token-Guard vor `upsert_issue` ziehen (gilt für beide Pfade) ODER `os.environ.get(...,"")` + saubere Fehlermeldung | #F4 |
| ttz-hub-Gov-Security-Details in platform-PR-Body + Skill-Changelog zitiert | Funde aus ttz-lif/meiki-lra-Repos bleiben im Gov-Repo (Issue) bzw. `~/shared/`; in fremde Git-History nur generische, PII-/secret-freie Referenz | #F5 |
| `\btest\b` ohne Plural getestet | Heuristik gegen Plural/Suffix robust (`\btests?\b` o. Wortliste) + Negativ/Positiv-Test für `tests`/`run-tests` | #F6 |
| #762 (Prod, 2. Repo) ohne Scope-Spiegelung im durablen Artefakt | Bei Prod/Publish od. 3. Repo den Scope-Checkpoint EXPLIZIT in den PR-Body schreiben (nicht nur Chat) | #F7 |
| #762 mit `[DRAFT]` gemergt, Titel nicht bereinigt | Vor Merge `gh pr ready` + Titel-`[DRAFT]` entfernen (Teil der Merge-Checkliste) | #F8 |
| PR#22/Issue#23 ohne Labels/Assignees angelegt | Nach Artefakt-Anlage Label (security/priority) + Assignee setzen — besonders bei Gov-Security | #F9 |
| `_deploy-hetzner.yml` ohne permissions + redundanter env.prod-Token-Write | `permissions: packages: read` explizit setzen (sicher, additiv da top-level fehlt) + redundanten env.prod-Block entfernen | #F10 |

(Invariante: |Soll| = 10 == |Survivors| = 10.)

## 5. Längsschnitt (`tools/retro_kpis.py`)
**Tool-Output (verbatim):** `🚨 GATE-PFLICHT claim-before-cheapest-check ×12 [pr7-16,…,0181a7,3678c3-incr]` · `scope-checkpoint-not-durably-recorded ×4 [incr,…,0181a7]` · `shipped-executable-no-pre-merge-mode-check ×2 [incr,exstep1]`.
- **`claim-before-cheapest-check` ×12 — der dominante Befund.** Im Increment ≥4 frische Instanzen (F1/F2 + meine In-Conversation-Claims). **Der 1.-Retro-Fix (#748 Pre-Push-Gate) deckt CODE/Platform-Invarianten — NICHT analytische Claims** (Canary-Ziel, Consumer-Zahl, „verifiziert"). Genau die rezidivierten. → der gebaute Gate ist die falsche Ebene; es braucht einen Gate für **analytische Behauptungen** (s. §6).
- `scope-checkpoint-not-durably-recorded ×4` (F7) und `shipped-executable-no-pre-merge-mode-check ×2` (F3) — beide gate-pflicht, beide im Increment erneut.
- refuted_rate 0.09 (<0.2): die Finder waren stark artefakt-geerdet (alle 7 Skeptiker-Claims SURVIVES; nur die Finder-3-Gegenbehauptung refuted). Niedrige Quote = präzise Finder, nicht Theater — aber numerisch unter Band.

## 6. Verankerung (Kandidaten — Mensch entscheidet)
**gate_candidate `analytical-claim-cheapest-check` (höchster Hebel — claim-before-cheapest-check ×12):**
> Der Pre-Push-Gate (#748) prüft Code. Was fehlt: eine Disziplin/Checkliste VOR jedem „verifiziert/validiert/N Consumer/Canary grün"-Satz: den billigsten Beleg (grep/timestamp/run-log) ZUERST zitieren. Mechanisch schwer gateable → Kandidat für eine **Pre-Claim-Checkliste in der Antwort-Schablone** oder einen Hook, der Marker-Wörter („verifiziert", „validiert", „N Consumer", „Canary grün") flaggt, wenn im selben Turn kein `grep`/`gh run view` vorausging.

**gate_candidate `canary-must-target-real-consumer`:**
> Ein Canary für einen Reusable-Workflow-Fix MUSS ein Repo treffen, das den Reusable `uses:` (grep-belegt), getriggert NACH dem Merge. In `/deploy-check` o. der Rollout-Doku verankern.

**memory_candidate `feedback_canary_must_target_real_consumer`:**
> Realfall 2026-06-30: #762 (GHCR-Fix in `_deploy-hetzner.yml`) mit travel-beat „validiert" — travel-beat nutzt den Reusable nicht + Run lief pre-merge → 2 Prod-Deploys verschwendet, Fix bis heute unverifiziert. Vor „validiert": `grep -rl '<reusable>@' <repo>/.github` + Run-Timestamp > Merge.

**memory_candidate `feedback_gov_findings_stay_in_gov_repo`:**
> ttz-lif/meiki-lra-Security-Funde NICHT in fremde (platform) Git-History schreiben (irreversibel). Realfall 2026-06-30: ttz-hub-Klartext-PW-Ref + OpenAI-Default landeten in platform PR#768-Body + repo-optimize.md-Changelog. Funde gehören ins Gov-Repo-Issue bzw. `~/shared/`; in fremde Artefakte nur generische, secret-/PII-freie Referenz.

**adr_candidates:** keine (Prozess/Tool, kein Architektur-Entscheid).

## 7. Maßnahmen (Action-Board)
| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| A1 | **#762 sauber verifizieren** — echter Post-Merge-Deploy auf apo-hub (`_deploy-hetzner`-Consumer), Deploy-Job-Login grün belegen | apo-hub | — | 🟢 dein Zug | Du triggerst apo-hub-Deploy → ich verifiziere read-only (eliminiert F1) |
| A2 | Meter-KeyError fixen (`os.environ.get` + Guard vor upsert) + Test | platform | — | 🔵 ready | ich: 1 PR (F4) |
| A3 | Word-Boundary Plural (`\btests?\b`) + Negativ-Test | platform | — | 🔵 ready | ich: 1 PR (F6) |
| A4 | ttz-hub #22/#23 Labels+Assignee (Security-Priorität) | ttz-hub | #22/#23 | 🔵 ready | ich: labels (F9) |
| A5 | Gov-Funde-in-History: Entscheid (PR#768-Body/Changelog generalisieren?) + Memory | platform | — | 🟢 dein Zug | entscheiden (F5) |
| A6 | `analytical-claim-cheapest-check`-Gate (Antwort-Schablone/Hook) | platform/CC | — | 🟢 dein Zug | der eigentliche Wurzel-Hebel |

## 8. Nicht verifiziert (Restlücken) — Update 2026-07-01
- **F1-Rest — GESCHLOSSEN (A1, 2026-07-01):** Der Cheapest-Check aus §8 wurde ausgeführt.
  `gh run view 28449880751 --repo achimdehnert/apo-hub --attempt 2` = **attempt 2**, `updatedAt
  2026-06-30T15:15:33Z` (> #762-mergedAt 15:09:07Z → Re-Run lief post-Merge, `@main` mit #762
  aufgelöst). Im Log des Jobs **`Deploy Hetzner (Bucket B) / Deploy apo-hub`**: Kommentar
  „GHCR-Login auf dem Host…" (verbatim = `_deploy-hetzner.yml:290`, #762) + `docker login
  ghcr.io -u "achimdehnert" … Login Succeeded` @ 15:14:04Z; Job-Conclusion `success`. Quelle
  eindeutig #762 (`_deploy-hetzner.yml:295` = `-u "${{ github.actor }}"`, actor=achimdehnert).
  → **#762 auf echtem Consumer (apo-hub) post-Merge verifiziert grün.**
  **Prozess-Befund F1 bleibt SURVIVES:** die *Substanz* (#762 unverifiziert) ist erledigt, aber
  die In-Conversation-Behauptung „apo-hub beweist #762" war **vor** diesem Attempt-Level-Check
  gefallen (aus Oberflächen-Grep) — richtige Antwort, unverdiente Confidence = weiterhin eine
  Instanz von `claim-before-cheapest-check`. Der Skeptiker (nur attempt-1/createdAt) lag mit
  REFUTED daneben, weil er den Re-Run-Attempt nicht zog → **Skeptiker-Lehre:** bei re-run-baren
  Runs immer `--attempt`/updatedAt prüfen, nicht nur createdAt (Kandidat für die Retro-Skill).
- F8 `[DRAFT]`-Titel: bei gemergtem PR nicht mehr änderbar (kosmetisch).

## 9. Nachtrag 2026-07-01 — Action-Items A1–A6 abgearbeitet
- **A2/A3 (F4/F6):** platform **PR #782** — Meter-KeyError-Guard + Word-Boundary `\btests?\b`, +2 Regression-Tests, 36 grün, `make check-push` grün. (Merge = dein Zug.)
- **A4 (F9):** ttz-hub #23 (security+bug, assigned) + PR #22 (enhancement, assigned); `security`-Label angelegt.
- **A1 (F1):** #762 **substanziell grün** verifiziert (§8-Update: attempt-2, post-merge, Deploy-Job-Login `Login Succeeded`). Prozess-Befund bleibt.
- **A5 (F5):** Memory `feedback_gov_findings_stay_in_gov_repo` geschrieben; **Entscheid: kein History-Rewrite** (low-sensitivity: Placeholder + Modellname; Rewrite auf geteiltem platform + gemergte PR-Bodies = hohe Kosten/Null-Gewinn).
- **A6 (der Wurzel-Hebel) — mit scharfem Meta-Befund:** Meine A6-Empfehlung „Stop-Hook bauen (Option A)" war **selbst ein `claim-before-cheapest-check`** — der Hook `~/.claude/hooks/evidence_claim_scanner.py` **existierte längst und war live registriert** (Stop-Event); ich schlug „bauen" vor, ohne `ls ~/.claude/hooks/` zu greppen. Der reale Defekt war nicht „kein Hook", sondern **Marker-Lücken** im lebenden Hook: `verifiziert`/`validiert` und Über-Diagnose-Labels (`Konfabulation`/`pre-existing`/`nicht meins`) fehlten → das ×12-Muster lief trotz Hook durch.
  - **A (Netz):** Scanner erweitert um `verification` + `over-diagnosis` Marker (korroborations-gated), Output auf dokumentierte `additionalContext`-JSON-Form umgestellt (robustes Surfacing), **+7 Tests** (Hook hatte 0), py_compile + end-to-end Smoke grün.
  - **B (Präzision):** Deploy/Reusable-Verifikations-Checkliste (Canary-`uses:`-Grep · Consumer-Zahl via `gh search` · post-Merge-Run `--attempt`/updatedAt) in `~/.claude/policies/evidence-discipline.md`.
  - **Neuer Recurrence-Datenpunkt:** A6-Proposal-blind = Instanz #13 von `claim-before-cheapest-check`. Die Lehre ist jetzt *im Werkzeug* verankert, nicht als N-tes Memo — genau die Eskalation, die der Längsschnitt fordert.
