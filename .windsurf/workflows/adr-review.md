---
description: Review an ADR against the platform-specific checklist (MADR 4.0 + infrastructure conventions)
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

## Step 2: Run through all 7 checklist categories

Work through each category systematically:

1. **MADR 4.0 Compliance** — frontmatter, title, sections, Confirmation
2. **Platform Infrastructure Specifics** — server IP, SSH, registry, ports, Nginx
3. **CI/CD & Docker Conventions** — Dockerfile location, compose, health checks, pipeline
4. **Database & Migration Safety** — Expand-Contract, tenant_id, shared DB risk
5. **Security & Secrets** — no hardcoded secrets, SOPS, org-level secrets
6. **Architectural Consistency** — service layer, no ADR contradictions, Guardian compatibility
7. **Open Questions & Deferred Decisions** — all open questions addressed

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

[Continue for all 7 categories]

---

### 📊 Scoring

| Category | Score | Notes |
|----------|-------|-------|
| MADR 4.0 compliance | 4/5 | Missing Confirmation subsection |
| Platform specifics | 5/5 | |
| Security | 3/5 | StrictHostKeyChecking=no must be fixed |
| Architectural consistency | 5/5 | |
| Clarity & completeness | 4/5 | |
| **Overall** | **4.2/5** | |

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

## Step 4: Apply fixes (if user confirms)

If user says "Ja" or "apply" or "fix it":

1. Apply all ❌ critical fixes directly to the ADR file
2. Apply ⚠️ minor improvements if user confirms
3. Push to GitHub with commit message:
   `fix(ADR-[NNN]): address review findings — [summary of changes]`
4. Update ADR frontmatter: `amended: [today's date]`

---

## Step 5: Update migration tracking (if applicable)

If the ADR has a migration tracking table (§4 or §5 pattern from ADR-021):
- Check if any items can be marked as done based on current repo state
- Suggest updates to the tracking table

---

## Reference

- Checklist: `platform/docs/templates/adr-review-checklist.md`
- ADR Index: `platform/docs/adr/INDEX.md`
- MADR 4.0: https://adr.github.io/madr/
