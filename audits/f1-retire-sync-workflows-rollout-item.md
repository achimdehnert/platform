# ADR-230-Rollout-Item: Retire `sync-workflows-to-repos.yml`

> Status: **Vorschlag, überarbeitet nach externem Review** (2026-05-31). Bezug: ADR-230
> (CC-first, „kein per-Repo `.windsurf`", REC-10/15) · ADR-229 (consumed not mirrored) · ADR-175 (Modularisierung).

## Entscheidung (überarbeitet)

`.github/workflows/sync-workflows-to-repos.yml` stilllegen als **ADR-230-§8-Rollout-Schritt** —
aber **gated**, nicht in einem Rutsch. Begründung: per-Repo-Mirroring ist durch ADR-229/230 tot;
der Workflow ist die belegte Ursache von Audit-F1.

**Code-Beleg (F1-Maschine):** Z. 237–245 `deleteFile` des Symlinks („sonst ändert sich der git-Mode
nicht"), Z. 246–250 `createOrUpdateFileContents` schreibt Voll-Inhalt-Blob, Commit
`chore(workflows): sync <wf>.md from platform`. Trigger: jeder push→main auf
`.windsurf/workflows/**` / `registry/*.yaml` / `docs/{onboarding,governance}/**`.

## 🔴 HARTER BLOCKER (verifiziert 2026-05-31) — Lookup-Delivery-Lücke

`tools/cc-skill-dist/generate.py` kopiert **nur** `.windsurf/workflows/*.md` (Z. 43/47); es liefert
`docs/{onboarding,governance}/`-Lookups **nicht**. **5 Workflows referenzieren solche Lookups**
(agentic-coding, session-ende, new-github-project, platform-audit, onboard-repo). → Retire VOR
Schließen dieser Lücke ⇒ dangling Links in der CC-Distribution. **Retire ist blockiert, bis
`cc-skill-dist` die Lookups mitliefert (oder inlined) UND `cc-skill-dist doctor` Link-Vollständigkeit
maschinenprüfbar erzwingt** (erweitert das bestehende `cc-skill-dist-doctor.yml`).

## Gated Sequenz (zwingend)
1. **Stufe 1 — Distributor entschärfen:** `sync-workflows-to-repos.yml` auf `workflow_dispatch`-only
   reduzieren, mit harten Guardrails (protected environment + manuelle Approval + „Legacy emergency only"-Banner,
   keine Default-Ausführung). Stoppt automatische Drift sofort.
2. **Gate — `cc-skill-dist` live-tauglich:** generierte CC-Commands + Manifest + Hash-Footer konsistent,
   **Lookups vollständig ausgeliefert + doctor-Linkcheck grün**, Windsurf-Review-Subset separat abgedeckt.
3. **Flotten-Dry-Run + Sweep:** `tools/f1-windsurf-sweep.sh` (Dry-Run-Default) → maschinenlesbarer
   Vorher/Nachher-Report je Repo → schreibender Sweep (Distributor-off ist Precondition, nicht Empfehlung).
4. **Beobachtung, dann Stufe 2:** Datei entfernen — mit **fester Bedingung** („nach erfolgreichem Sweep
   + 2 grünen globalen Dist-Runs"), nicht offen liegen lassen.

## Akzeptanz-Kriterien (neu)
- Maschinenlesbarer Flotten-Report: Repo · getrackte Workflow-Files · getrackte Lookup-Files · entfernt · Ignore-Diff · Sonderfälle.
- **Anti-Regression-Check** (Erweiterung `cc-skill-dist-doctor.yml` ODER Flotten-Audit): neu getrackte
  `.windsurf/workflows/**`-Regular-Files dürfen nicht wieder auftauchen.
- Sweep-Report ↔ `cc-skill-dist`-Manifest verknüpft (Traceability alt↔neu).
- 2 Repos ohne erreichbares `origin/main` (`bahn-sqf-pg-hub`, `fristenmanagement`): **Deferred-Exception**
  mit Owner + Datum + Nachhol-Sweep; blockiert „Flotte vollständig".
- `scripts/sync-workflows.sh` (lokaler Symlink-Sync): explizit **deprecaten / auf read-only-Diagnose
  umbauen / als reiner Dev-Komfort markieren** — sonst mutiert er nach dem Sweep weiter Arbeitsbäume.
- Doc-/Registry-/Onboarding-Referenzen auf `sync-workflows-to-repos.yml` entfernt (kein Zombie-Wissen).

## ADR-Form
**Kein eigenes ADR.** Als **ADR-230-Amendment / Rollout-Record** mit explizitem Abschnitt
„**Supersedes ADR-175 distribution half**" + CHANGELOG/PR führen — die Richtung „nicht per Repo spiegeln"
folgt bereits aus ADR-229/230. Eigenes ADR nur, falls Lookup-Files künftig neu modelliert/gebündelt/
semantisch versioniert werden (dann echte neue Entscheidung).

---

## Externe-Review-Rückfluss (Step-5-Gate, ID → Verdikt → Aktion)

Externes Briefing: `~/shared/adr-handoff-ADR-230-retire-sync-2026-05-31.md`. Verdikt des Reviewers:
**überarbeiten** (Richtung richtig, Lookup-Lücke schließen). Nur `[valid]` eingearbeitet.

| ID(s) | Verdikt | Aktion |
|---|---|---|
| AD-1, AD-2, REC-1, M28-4, M28-9, REC-21, OOB-1 | **[valid] — verifiziert** | Lookup-Delivery als HARTER BLOCKER + doctor-Linkcheck (oben). |
| AD-3, AD-12, REC-4, REC-23 | [valid] | Gated Sequenz + konkretes cc-skill-dist-Live-Gate (Stufe 1→Gate→Sweep→Stufe 2). |
| AD-4, AD-9, M28-3, REC-5, OOB-2 | [valid] | Guardrails für `workflow_dispatch`-only (protected env, Approval, Banner). |
| M28-12, REC-6, REC-24 | [valid] | Feste Stufe-2-Bedingung + CHANGELOG/ADR-Notiz statt stillem Verschwinden. |
| AD-5, M28-5, REC-7 | [valid] | 2 unerreichbare Repos als Deferred-Exception mit Owner/Datum. |
| AD-11, M28-2, REC-8, OOB-3 | [valid] | Maschinenlesbarer Flotten-Report vor/nach Sweep. |
| M28-8, REC-15, REC-22, OOB-5 | [valid] | Anti-Regression-Check (erweitert `cc-skill-dist-doctor.yml`). |
| AD-7, M28-6, REC-11 | [valid] | Zukunft `scripts/sync-workflows.sh` explizit klären. |
| AD-8, REC-12, M28-7 | [valid] | Doc/Registry-Referenzen entfernen. |
| AD-9, M28-11, REC-13 | [valid] | Rollback-Plan inkl. Re-Entmirroring, nicht nur „dispatchen". |
| AD-10, REC-14 | [valid] | Sweep als Breaking-DX-Migration kommunizieren (Rebase-Hinweise). |
| AD-13, M28-1, REC-2, REC-3 | [valid] | ADR-175-Supersession-Kapitel + als ADR-230-Amendment führen. |
| M28-10, REC-16 | [valid] | Sweep-Report ↔ Manifest verknüpfen (Traceability). |
| AD-14, REC-17 | [valid, low] | Public-Sector: kurzer „keine Mandantendaten"-Vermerk. |
| AD-15, REC-9 | [valid — bereits abgedeckt] | Dry-Run-Default in `tools/f1-windsurf-sweep.sh` (vorhanden). |
| AD-6, REC-10 | [valid — teilw. abgedeckt] | Plan hat Klasse A blanket / Klasse C präzise; Wording verschärft. |
| PRO-4, REC-19 | [valid — abgedeckt] | Distributor-off als nicht-verhandelbare Precondition (Plan §2). |
| PRO-6, REC-20 | [valid — abgedeckt] | `git rm --cached` ≠ Quell-/History-Verlust (Plan §6). |
| PRO-1,2,3,5,7,8 | [valid — Steelman] | Bestätigen die Richtung; keine Aktion nötig. |
| OOB-4, REC-18, AD-16 | **[out-of-scope]** | Globaler Workflow-Index / Offline-Such-Komfort: DX-Nice-to-have, kein Retire-Blocker — separat backloggen. |
| OOB-6 | **[out-of-scope (Phase 2)]** | Content-addressed Bundle + Link-Rewriting: erst falls Lookup-Mitliefern nicht reicht (Reviewer selbst: nicht für ersten Retire). |
