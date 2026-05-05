---
description: Review an ADR against the platform-specific checklist (MADR 4.0 + infrastructure conventions + Modern Platform Patterns)
---

# ADR Review Workflow

## Trigger

User says: `/adr-review ADR-[NNN]` or "Review ADR-[NNN]" or "Reviewe ADR-[NNN]"

---

## Step 1: Load the ADR

Read the ADR file from `docs/adr/ADR-[NNN]-*.md` in the `platform` repo (or the relevant service repo).

Also load the review checklist:
`platform/docs/templates/adr-review-checklist.md`

---

## Step 2: Run through all 8 checklist categories

Work through each category systematically:

1. **MADR 4.0 Compliance** — frontmatter (incl. `implementation_status` per ADR-138), title, sections, Confirmation
2. **Platform Infrastructure Specifics** — server IP, SSH, registry, ports, Nginx
3. **CI/CD & Docker Conventions** — Dockerfile location, compose, health checks (NOT in Dockerfile!), pipeline
4. **Database & Migration Safety** — Expand-Contract, tenant_id, shared DB risk
5. **Security & Secrets** — no hardcoded secrets, SOPS, org-level secrets
6. **Architectural Consistency** — service layer, no ADR contradictions, Guardian compatibility
7. **Open Questions & Deferred Decisions** — all open questions addressed
8. **Modern Platform Patterns** — infra-deploy, Multi-Tenancy, Content Store, catalog-info.yaml, Drift-Detector, Runner labels, Temporal (nur wenn relevant)
9. **ADR-138 Implementation Tracking** — `implementation_status` in frontmatter (required for Accepted ADRs), `implementation_evidence` if status is partial/implemented/verified, INDEX.md Impl column matches frontmatter
10. **Glossar & Lesbarkeit** — Glossar-Abschnitt vorhanden? Alle Abkürzungen/Fachbegriffe erklärt? Alphabetisch sortiert? Erläuterungen kontextbezogen (nicht nur Übersetzung)? Zielgruppe: Fachpersonal ohne IT-Hintergrund.

For each check: mark ✅ Pass, ⚠️ Minor issue, or ❌ Fail with a brief note.

---

## Step 3: Output the review report

```text
## 🔍 ADR Review: ADR-[NNN] — [Title]

### 1. MADR 4.0 Compliance
✅ 1.1 YAML frontmatter present
✅ 1.2 Title is a decision statement
⚠️ 1.5 Only 2 options considered — recommend adding ≥ 1 more
...

### 2. Platform Infrastructure Specifics
✅ 2.1 Server IP correct
❌ 2.3 StrictHostKeyChecking=no found in deploy-service.yml line 42 — replace with ssh-keyscan
...

[Continue for all 8 categories]

---

### 📊 Scoring

| Category | Score | Notes |
|----------|-------|-------|
| MADR 4.0 compliance | 4/5 | Missing Confirmation subsection |
| Platform Infrastructure Specifics | 5/5 | |
| CI/CD & Docker Conventions | 5/5 | |
| Database & Migration Safety | 5/5 | |
| Security & Secrets | 3/5 | StrictHostKeyChecking=no must be fixed |
| Architectural Consistency | 5/5 | |
| Open Questions | 4/5 | |
| Modern Platform Patterns | 5/5 | n/a for this ADR |
| **Overall** | **4.5/5** | |

---

### ✅ Stärken
- [List positives]

### ⚠️ Verbesserungsvorschläge
- [List minor improvements]

### ❌ Kritische Punkte
- [List blockers — must fix before Accept]

---

### 🎯 Empfehlung
[Accept / Accept with changes / Reject]

Soll ich die Änderungen direkt anwenden? [Ja/Nein]
```

---

## Step 3.5: ADR-138 Compliance Quick-Check

Automatically verify:
1. **Frontmatter field**: Does the ADR have `implementation_status` in its YAML frontmatter?
   - If missing and status is `Accepted`: ❌ BLOCK — add `implementation_status: none` (or appropriate value)
   - If missing and status is `Proposed`: ⚠️ SUGGEST — add `implementation_status: none`
   - If missing and status is `Deprecated`/`Superseded`/`Archived`: skip (not applicable)
2. **Evidence field**: If `implementation_status` is `partial`, `implemented`, or `verified`, does `implementation_evidence` exist with at least one entry?
3. **INDEX.md sync**: Does the Impl column in INDEX.md match the frontmatter value?
   - `none` → ⬜, `partial` → 🔶, `implemented` → ✅, `verified` → ✅✅

---

## Step 4: Apply fixes (if user confirms)

If user says "Ja" or "apply" or "fix it":

1. Apply all ❌ critical fixes directly to the ADR file
2. Apply ⚠️ minor improvements if user confirms
3. Update ADR frontmatter: `amended: [today's date]`
4. If review outcome is **Accept**: update `platform/docs/adr/INDEX.md` — Status `Proposed` → `Accepted`
5. If `implementation_status` was missing: add it to frontmatter and update INDEX.md Impl column
6. Push to GitHub with commit message:
   `fix(ADR-[NNN]): address review findings — [summary of changes]`

---

## Step 5: Update migration tracking (if applicable)

If the ADR has a migration tracking table (§4 or §5 pattern from ADR-021):
- Check if any items can be marked as done based on current repo state
- Suggest updates to the tracking table

---

## Reference

- Checklist: `platform/docs/templates/adr-review-checklist.md` (v2.0)
- ADR Index: `platform/docs/adr/INDEX.md`
- MADR 4.0: https://adr.github.io/madr/
- Modern Platform Patterns: ADR-059, ADR-062, ADR-072, ADR-075, ADR-077
- Implementation Tracking: ADR-138 (lifecycle: none → partial → implemented → verified)
