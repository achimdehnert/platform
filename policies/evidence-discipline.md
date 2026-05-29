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

Recall surface (concrete past incidents only, not doctrine):
CC-memory `claim-confidence-vs-cheapest-check`. This file is the single
authoritative statement.

## Effectiveness test (binding — falsify or cut)

Signal **R** = (marker-claims with a cited check in the same turn
*before* the claim) / (all marker-claims), counted by `grep` over session
transcripts, both directions. Baseline = the ~6 documented pre-policy
incidents of the 2026-05-19 thread (assert-before-check or never).
**If R over the next ~10 real sessions does not beat baseline, this
policy is cut, not patched.** A policy that cannot fail its own test is
the sprawl it warns against.

## Changelog

- 2026-05-19: Initial, promoted passive→active. Trimmed same day to
  operative core (removed speculative "where applies" table + essay —
  by its own standard, unverified content does not belong in an
  authoritative policy). Falsification threshold added and binding.
