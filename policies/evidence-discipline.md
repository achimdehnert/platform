# Policy: Evidence Discipline

**Trigger words:** beweis, daten als beweis, behauptung, claim, done, fertig, festgehalten, deployed, gesichert, erfolgreich, COMPLETE, pre-existing, nicht mein code, infra smell, evidence, nachweis, verifiziert

## Rule

A consequential claim must not be **asserted** — nor **accepted / judged** —
at a confidence higher than its *cheapest available check* establishes.
This binds the claimant and the reviewer equally. Neither may carry a
prior into the gap. Run the check **before** writing the sentence and
**before** rendering the verdict.

Bidirectional, same fault: over-claiming ("done ✓", "Festgehalten: memory
X", "deployed", "1m2s") and over-diagnosing ("confabulated", "infra
smell", "not my code", "pre-existing") both skip the cheapest check.

## Fires when the claim carries a cheaply-falsifiable specificity marker

named artifact ("memory X", "PR #N", "file Y") · status/outcome
("failed", "green", "done ✓") · number/date ("1m2s", "since 2026-03-15")
· root-cause label ("infra", "pre-existing", "not my code") · magnitude
word ("ändert alles").

## How to apply

1. Marker present → run the one cheapest disambiguating check (`ls`,
   `gh run view`, one import, one `grep`, read the line) **first**. Emit
   the check, then the claim — in that order.
2. No check exists → it is a **hypothesis**. Phrase it as one.
3. State residual gaps: "verified: X; not verified: Y — cheapest check
   is Z". Never let a prior — yours or the source's — substitute for Z.
4. A proxy/heuristic is not a verified result — label its output a
   candidate, not a conclusion.
5. **Der Verifikations-Query muss vom Implementierungs-Query UNABHÄNGIG sein.**
   Nach einem Sweep/Refactor „vollständig / Rest = N / fertig" NICHT mit demselben
   Muster prüfen, das die Implementierung baute — der Bau-Blindfleck wandert sonst
   ungeprüft in den Claim (zirkuläre Selbst-Verifikation). Breiter/anders greppen als
   der Bau-Query. Realfall 2026-07-02: mcp-Sweep-Regex `mcp[0-9]_` (einstellig),
   Verifikations-Grep ebenfalls `mcp[0-9]_` → zwei `mcp14_`-Token still übersehen
   (platform #842→#843). Über Retros ×4 (`retro_kpis.py`) — gate-pflichtige Variante
   von claim-before-cheapest-check, die der Marker-Scanner-Hook nicht fängt.
6. **Ein PR/Branch-Close mit „superseded/redundant/überholt"-Begründung ist ein
   prüfbarer Claim — der billigste Check läuft VOR dem Close, nicht danach.** Bevor ein
   PR geschlossen (oder ein Branch gelöscht) wird, weil „X deckt das ab": die konkreten
   Dateien/Module des zu schließenden PRs auflisten (`gh pr view <N> --json files`) und
   belegen, dass der Ersatz (main oder Ersatz-PR) genau die abdeckt — bei Tests die
   **per-Modul-Coverage** (`pytest … | grep <modul>` > 0 %), NICHT nur ein aggregiertes
   Gate: ein grünes `--cov-fail-under` maskiert einen Modul-Verlust, wenn Zuwachs anderswo
   kompensiert. Erst bei belegter Abdeckung schließen, sonst gezielt cherry-picken.
   Realfall 2026-07-02: PR iil-adrfw#17 als „superseded by #20/#29" geschlossen ohne
   Coverage-Diff → `freshness/`+`index/` ~13 h bei 0 % auf main (aggregiertes 70 %-Gate
   hielt trotzdem), repariert erst durch #36. Über Retros ×5 (`retro_kpis.py`) — dieselbe
   Familie wie Punkt 5, anderer Trigger (Close/Delete-Aktion), die der Marker-Scanner-Hook
   (`evidence_claim_scanner.py`) ebenfalls nicht fängt (er scannt Verifikations-/Deploy-
   Marker, keine `gh pr close`-Aufrufe).

Recall surface (concrete past incidents only, not doctrine):
CC-memory `claim-confidence-vs-cheapest-check`. This file is the single
authoritative statement.

## Worked checklist: Deploy / Reusable-Workflow-Fix verification

Deploy/CI claims were the hot sub-domain of `claim-before-cheapest-check`
(Retro-Increment 2026-06-30, ×3 in one session). Before writing
"deployed / validiert / canary grün / N consumers" about a CI or reusable-
workflow fix, run these three — cite each **before** the claim:

1. **Canary targets a real consumer.** The repo you deploy to must actually
   `uses:` the changed reusable — prove it: `grep -rl '<reusable>@' <repo>/.github`.
   (Realfall: travel-beat als #762-Canary gewählt, nutzte `_deploy-hetzner.yml`
   gar nicht → zwei Prod-Deploys verschwendet, Fix nie getestet.)
2. **Reach/consumer-count is grepped, not guessed.** Before "N consumers /
   fleet-wide", run `gh search code '<reusable>@main' --owner <org>` and exclude
   the source repo's own files. (Realfall: "7 Consumer" behauptet, real ≤3, 1 aktiv.)
3. **"Deployed/verified" cites a post-merge green run — attempt-aware.** The run
   must have executed AFTER the fix merged: compare `updatedAt` (not only
   `createdAt`) against the merge time, and on re-run runs read the specific
   `--attempt`. Grep the **deploy job** (not the build job) for the changed step.
   (Realfall: apo-hub run createdAt lag *vor* dem Merge; erst `--attempt 2`
   (`updatedAt` post-merge) belegte #762s Login im Deploy-Job grün.)

Active backstop: `~/.claude/hooks/evidence_claim_scanner.py` (Stop hook) flags
verification/deploy/over-diagnosis markers that fire without an in-turn tool check.

## Effectiveness test (binding — falsify or cut)

Signal **R** = (marker-claims with a cited check in the same turn
*before* the claim) / (all marker-claims), counted by `grep` over session
transcripts, both directions. Baseline = the ~6 documented pre-policy
incidents of the 2026-05-19 thread (assert-before-check or never).
**If R over the next ~10 real sessions does not beat baseline, this
policy is cut, not patched.** A policy that cannot fail its own test is
the sprawl it warns against.

## How to measure

```bash
python3 tools/measure-evidence-discipline.py --repo <repo-slug>
# Scans ~/.claude/projects/*<repo-slug>*/*.jsonl
# Emits: R = <fraction> (<checked>/<total> marker-claim turns)
```

Run on or after **2026-06-15** (~10 sessions post-merge). R ≥ 0.70 = policy working.
If R does not beat the ~6-incident baseline, the policy is cut per the effectiveness test above.

## Changelog

- 2026-05-19: Initial, promoted passive→active. Trimmed same day to
  operative core (removed speculative "where applies" table + essay —
  by its own standard, unverified content does not belong in an
  authoritative policy). Falsification threshold added and binding.
- 2026-07-03: How-to-apply Punkt 6 — „PR/Branch-Close mit superseded-Begründung ist ein
  prüfbarer Claim, Coverage-/Files-Diff VOR dem Close". Aus Session-Retro
  `session-retro-2026-07-03-iil-adrfw-0b46ee.md`: `claim-before-cheapest-check` ×5 über
  Retros (retro_kpis.py), Familie von Punkt 5, anderer Trigger (Close/Delete). Der
  Marker-Scanner-Hook fängt diese Variante bisher nicht — begleitender Hook-Patch-Vorschlag
  im PR-Body (Hook lebt in `~/.claude/hooks/`, außerhalb dieses Repos).
- 2026-07-15: Weiterer Realfall, root-cause-label-Variante (weder Punkt 5 noch 6 — ein
  drittes Muster desselben Bidirectional-Fehlers): ein Root-Cause-Satz ("transiente
  Runner-Kontention") wurde mit mehr Bestimmtheit formuliert, als das Log trug — die
  Log-Zeile belegte einen abgebrochenen/gekillten Prozess (real), aber nicht den
  spezifisch benannten Mechanismus ("Kontention"). Ein unabhängiger Skeptiker bestätigte
  den Beleg für den Prozess-Abbruch, aber nicht für die Kontention-Interpretation. Aus
  `docs/retros/session-retro-2026-07-15-platform-c494a2.md` (Befund #3, `claim-before-
  cheapest-check` erneut ×1 über `retro_kpis.py` — Repo-übergreifend: die Diagnose betraf
  einen Deploy in einem anderen Repo, nicht platform selbst; das Muster ist nicht
  platform-lokal, sondern genau der org-weite Geltungsbereich, für den diese Policy
  geschrieben ist).
