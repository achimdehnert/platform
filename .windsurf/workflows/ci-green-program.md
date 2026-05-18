---
description: CI-Green-Programm — wiederholbarer Loop um ALLE Repos auf grüne CI zu bringen/halten (Survey→Triage→Gate→Issue→Queue→Merge→Lehren). Lehren aus Lauf 1 (2026-05-18) eingebrannt.
---

# /ci-green-program — Repeatable Cross-Repo CI-Green Loop

> **Zweck:** Nicht „einmal grün", sondern niedrige Mean-Time-to-Green über alle
> ~/github-Repos, als *wiederkehrender* Prozess. Jeder Fix härtet zugleich einen
> erzwungenen Contract (Contract-First).
> **Baut auf:** `/process-agent-queue` (Queue-Ernte), `/agentic-coding` v6
> (Router), `/issues-abarbeiten` (Handoff-Resumer).
> **Governance:** ADR-209.

---

## Eiserne Regeln (empirisch aus Lauf 1, 2026-05-18)

1. **Survey-Korrektheit:** Repo-Status = letzter *push/PR*-getriggerter CI/Deploy-Lauf.
   **Nie `gh run list --limit 1`** — grüner Dependabot/Sync-Lauf maskiert roten Deploy.
2. **Triage verifiziert jede Survey-Claim**, bevor gehandelt wird. (Lauf 1: ttz-hub
   als „ADR-Nightly-Bug" klassifiziert — hatte gar keinen ADR-Workflow.)
3. **Versions-/API-Check vor jedem „mechanischen" Dep-Swap.** (Lauf 1: blinder
   git→PyPI-Swap hätte 8 Repos still von 0.7.0 auf 0.5.1 downgraded.)
4. **Cross-cutting zuerst.** Ein Fix der viele Repos entsperrt (shared dep,
   shared workflow, repo-übergreifendes CI-Gate wie `gitleaks`) geht **vor**
   jeder per-Repo-Arbeit. Opus-Triage, nicht Queue.
5. **Hard-Gate Deploy/Infra:** Server-State (SSH-Key, Bind-Mount, apt, BuildKit,
   cancelled-runner) ist **kein** Code → **nie** in die autonome Queue. Eigener
   Workstream mit Prod-Zugriff.
6. **Judgment-Gate:** „Test falsch oder Code falsch?", Coverage-Gate senken,
   Star-Import-Auflösung → `ci-green` **ohne** `auto` (manuelle Sonnet-Session).
   Rein mechanisch (ruff format, Matrix-Bump, 1-Zeilen-Dep) → `auto`.
7. **Issue-Pflichtschema** (sonst reicht Sonnet nicht): Root-Cause · exakte
   Datei+Zeile · `alt`→`neu` · **Contract** (welche erzwungene Regel das
   wiederherstellt) · Done-Kriterium (inkl. `gh run ... --branch main` grün) ·
   `Closes #N`.
8. **Direct-PR für Trivallast.** `run_workflow`/headless läuft server-seitig
   (`/root/github/X`, nicht lokal) und ist per Default Gate-2-gated ohne PR —
   für 1-Zeilen-/format-Fixes ist der direkte PR-Pfad effizienter.

---

## Der Loop

### Phase 1 — Survey (read-only, delegierbar an Sub-Agent)
Pro Repo unter `~/github`: GitHub-Remote? CI vorhanden? letzter *push/PR*-Lauf
(Regel 1). Bei `failure`: Hauptfehlerklasse in 1 Zeile (nicht tief debuggen).
Output = Matrix `Repo | CI? | letzter Lauf | Fehlerklasse | Aufwand S/M/L`.

### Phase 2 — Triage (Opus, Pflicht-Verify)
- Jede Survey-Claim am Repo gegenprüfen (Regel 2).
- Fehlerklassen clustern; **Cross-cutting** markieren (Regel 4).
- Pro Item gaten: `auto` | `ci-green`(manuell) | Deploy/Infra | Cross-cutting/Opus
  (Regeln 5+6).

### Phase 3 — Cross-cutting zuerst (Opus, Direct-PR)
Shared dep / shared workflow / repo-übergreifendes Gate fixen. Ein PR entsperrt
n Repos. (Lauf 1: `iil-platform-context 0.7.0`→PyPI; meiki ADR-Nightly;
`gitleaks` ist der nächste.)

### Phase 4 — Issue-Factory
Pro Repo 1 Issue nach Pflichtschema (Regel 7). Label `ci-green` + ggf. `auto`.
Cluster batchen (gleiches Rezept = ein gh-Loop).

### Phase 5 — Abarbeitung
- `auto`-Issues → `/process-agent-queue` (Sonnet, headless, Budget-Cap).
- `ci-green`-only → manuelle Sonnet-Session (`/issues-abarbeiten`).
- Deploy/Infra → separater manueller Prod-Workstream.

### Phase 6 — Merge-Disziplin
PR grün **und** CLEAN mergen. Wenn ein **unrelated** repo-übergreifendes Gate
(z.B. `gitleaks`) rot ist obwohl der PR-Diff es nicht verursachen kann:
**nicht** durchdrücken — Cross-cutting-Gate-Issue eröffnen (Regel 4), erst das
fixen. Reihenfolge bei abhängigen PRs im selben Repo dokumentieren.

### Phase 7 — Lehren zurückschreiben (Pflicht-Abschluss)
Neue Erfahrungen → diese „Eiserne Regeln" ergänzen + orchestrator-memory
`queue-run:<date>` + `project_ci_green_program.md`. **Ohne diesen Schritt
wiederholt der nächste Lauf die Fehler.**

---

## Recurring-Setup
Phase 1+2 monatlich (oder via Repo-Health-Agent-Trigger) als Cron/Routine;
Phasen 3–7 on-demand wenn die Matrix rote Cluster zeigt. Siehe ADR-209 für
Kadenz + Gate-Begründung.
