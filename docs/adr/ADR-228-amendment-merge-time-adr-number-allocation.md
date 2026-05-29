---
id: ADR-228
title: "Amendment: Merge-time ADR number allocation (amends ADR-065)"
status: proposed
date: 2026-05-29
deciders: [Achim Dehnert]
consulted: []
informed: [all-repos]
domains: [governance, ci, adr]
supersedes: []
amends: [ADR-065]
related: [ADR-059, ADR-107]
implementation_status: none
---

# Amendment: Merge-time ADR number allocation (amends ADR-065)

> **Trigger**: The 2026-05-29 platform PR-backlog sweep had to hand-renumber
> **seven** ADRs (ADR-194/209/210/212/218/226 collisions → 221..227). The root
> cause is structural, not accidental: ADR-065 allocates numbers at
> author-time and the uniqueness check is blind to other open PRs.

> **Amends ADR-065** (filesystem-first ADR numbering). It does **not** reverse
> the on-main invariant (one number = one file, `max+1` ordering); it moves the
> *moment of allocation* from author-time to merge-time. ADR-065 stays the base
> decision; this record is the pattern, like ADR-071/078 amend their bases.

## Context and Problem Statement

ADR-065 allocates the next ADR number at **author time** as `max(numbers on
main) + 1` (implemented in `scripts/adr_next_number.py`). The uniqueness gate
(`adr-guard.yml` → `adr_next_number.py --check`) validates the **merged tree**
(PR vs main) and so catches a PR colliding with a number already on main.

It is **blind to other open PRs**: two PRs opened while the same `max` is
current both pick the same next number for *different* ADRs. Each passes its own
check; the collision only surfaces when the second tries to merge — by which
time it is stale, conflicts on `INDEX.md`, and must be hand-renumbered (file +
frontmatter `id` + body self-refs + INDEX row). On 2026-05-29 this happened
seven times in one backlog sweep and a hand-resolution even leaked git conflict
markers onto `main` once (separately fixed).

Dogfood (2026-05-29): with `#199` (ADR-226) and `#329` (ADR-227) open,
`scripts/adr_next_number.py` still prints `ADR-226` — it would hand a third PR
the already-claimed 226.

An **interim guard** (`scripts/adr_open_pr_guard.py`, PR #332, wired into
`adr-guard.yml`) now compares numbers across all open PRs and fails on a
same-number/different-file clash, so the collision is at least **visible at PR
time**. But it is *detective and advisory* — it still requires a manual
renumber and does not *prevent* the clash. This amendment is the *preventive,
structural* fix.

## Decision Drivers

* Collision probability scales with the number of simultaneously-open ADR PRs;
  the platform routinely carries many (the 2026-05 backlog had ~15).
* Manual renumbering is multi-file and error-prone (it already caused a
  conflict-marker regression on `main`).
* Merges to `main` are **already serialized** by the platform — that is the
  natural, race-free point to allocate a number.
* The fix must not break existing numbered ADRs or the on-main uniqueness
  invariant — only the *timing* of allocation should move.

## Considered Options

1. **Keep author-time `max+1`, rely on the interim guard (#332) only.**
   Rejected as the end state: detective + advisory, still needs manual
   renumber, does not prevent. Good as a transitional safety net.
2. **Author-time allocation made open-PR-aware** (query open PRs when the
   author picks a number). Partial: still racy for near-simultaneous PR
   creation, and a PR drifts stale as *other* PRs merge and shift `max`.
   Reduces, does not eliminate.
3. **Merge-time allocation (chosen).** The PR carries a draft slug
   (`ADR-DRAFT-<slug>`) with no number; a merge-time allocator assigns the next
   free number atomically on landing. Because merges serialize, two PRs can
   never receive the same number — collision impossible **by construction**.
4. **Central reservation ledger** (claim a number on a registry at PR-open).
   Rejected: needs a serialized write at open-time → re-implements merge-time
   allocation, worse (a second place to drift from the filesystem SSoT).

## Decision Outcome

Chosen: **Option 3 — merge-time allocation.**

* **Author time:** an ADR PR introduces `docs/adr/ADR-DRAFT-<kebab-slug>.md`
  with frontmatter `id: ADR-DRAFT-<slug>` (or a `draft: true` marker). No
  number is chosen; `/adr` and `adr_next_number.py` emit a slug, not a number.
  In-PR cross-references use the slug or the PR number.
* **Merge time:** a GitHub Action (`adr-allocate-on-merge.yml`, on
  `push: main`, paths `docs/adr/ADR-DRAFT-*`) computes the next free number —
  now race-free, since it runs serialized on `main` — and atomically:
  `git mv` the file to `ADR-NNN-<slug>.md`, set frontmatter `id: ADR-NNN`,
  rewrite the H1 + intra-file self-refs, insert the `INDEX.md` row, bump
  "next free", and commit back to `main`.
* **On-main invariant unchanged:** `adr_next_number.py --check` still asserts
  no duplicate numbers on `main`; ADR-065's `max+1` ordering still holds — it
  is just computed by the allocator at merge, not by the author at creation.

### Consequences

* Good: collisions become **structurally impossible**; the renumber churn (and
  its conflict-marker risk) cannot recur.
* Good: authors no longer pick numbers — less cognitive load, no "is this
  number free?" lookup.
* Trade-off: a new automation with **write access to `main`** (rename + INDEX +
  commit). A bot commit lands on every ADR merge. Scope the token minimally
  (`contents: write` + `workflow` only if needed) and trigger only on
  `ADR-DRAFT-*` paths.
* Trade-off: a freshly-merged ADR's *final* number is known only post-merge —
  external references (chat, issues) made pre-merge must use the slug or PR
  number until the allocator runs.
* Trade-off: `amends`/`supersedes`/`related` in *other* ADRs cannot point at the
  new ADR by number until it has merged; use the slug or wait.
* Keep: `adr_open_pr_guard.py` (#332) stays as a belt-and-suspenders during and
  after the transition (it is cheap and advisory).

### Confirmation

1. A merged ADR PR that introduced an `ADR-DRAFT-*` file results in a numbered
   `ADR-NNN-*` file on `main` plus its INDEX row, authored by the allocator.
2. Two ADR PRs opened against the same `max` both merge cleanly with distinct
   numbers and **zero** manual renumber.
3. `adr_next_number.py --check` stays green on `main` (no duplicate numbers).

## Implementation Plan (deferred to a follow-up PR)

* `/adr` skill + `adr_next_number.py`: add a `--draft-slug` mode emitting
  `ADR-DRAFT-<slug>` instead of a number; stop printing a number for new ADRs.
* New `adr-allocate-on-merge.yml` (push→main, paths `docs/adr/ADR-DRAFT-*`):
  rename + frontmatter `id` + H1/self-ref rewrite + INDEX row + commit.
* Migration: existing numbered ADRs are untouched; only new ADRs use the draft
  flow. ADR-065 gets an `amended_by: [ADR-228]` note.
* Transition: keep `adr_open_pr_guard.py` enforcing until the allocator has run
  green on ≥2 real ADR merges.

## Risks

* **Bot write to `main`.** The allocator commits to `main` — a new automation
  with commit rights (supply-chain surface). Mitigate: minimal-scope token,
  path-restricted trigger, no other repo content touched, PR-reviewable
  workflow definition.
* **Allocator failure leaves a draft un-numbered on `main`.** Mitigate:
  idempotent + re-runnable on `workflow_dispatch`; `adr_next_number.py --check`
  would still flag a left-over `ADR-DRAFT-*` (extend the check to treat a
  drafted file on `main` as a failure).

## Not in scope

* Renumbering existing ADRs (the 221..227 results stand).
* The interim detective guard (#332) — already shipped, kept as safety net.

## Glossar

> Zielgruppe: Fachpersonal ohne IT-Hintergrund.

| Begriff | Bedeutung |
|---|---|
| **ADR** | Architecture Decision Record — dokumentierte Architektur-Entscheidung mit fortlaufender Nummer (ADR-NNN). |
| **Allokator** | Hier: das Automatik-Skript, das beim Merge die nächste freie ADR-Nummer vergibt. |
| **CI / GitHub Action** | Automatische Abläufe, die bei Code-Änderungen/Merges laufen. |
| **Frontmatter** | Der strukturierte Kopf einer ADR-Datei (zwischen `---`), u. a. mit `id`/`status`. |
| **idempotent** | Mehrfach ausführbar mit gleichem Ergebnis — ein zweiter Lauf richtet keinen Schaden an. |
| **INDEX.md** | Die Übersichtstabelle aller ADRs. |
| **Merge** | Das Übernehmen eines Pull-Requests in den `main`-Stand. |
| **Race-Condition** | Fehler durch ungünstige Gleichzeitigkeit — hier: zwei offene PRs greifen dieselbe Nummer. |
| **Slug** | Sprechender Kurzname aus dem Titel (z. B. `merge-time-adr-number-allocation`). |

## More Information

* ADR-065 — filesystem-first ADR numbering (the base this amends).
* ADR-059, ADR-107 — abandoned the per-repo range concept (global `max+1`).
* PR #332 — `scripts/adr_open_pr_guard.py`, the interim detective guard.
* 2026-05-29 platform sweep — the renumber churn (ADR-221..227) that motivated this.

## Changelog

* 2026-05-29: Initial (proposed). Amendment to ADR-065 — allocate ADR numbers
  at merge time to eliminate the in-flight open-PR collision race.
