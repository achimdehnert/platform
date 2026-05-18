---
description: CI-Health Konvergenz-Programm (v2) — Prävention vor Detektion. Portfolio-Triage → shared-CI-Konvergenz → event-driven Remediation mit Gates-als-Code → Selbstabschaltung. Governance ADR-209.
---

# /ci-green-program — CI-Health Konvergenz-Programm (v2)

> **Zweck:** NICHT „48 CIs ewig grün triagieren", sondern Failure-Klassen an
> der *geteilten Quelle* eliminieren und das Programm sich selbst überflüssig
> machen. Empirie: ein Fix in reusable `_ci-python.yml` (#191) entsperrte alle.
> **Baut auf:** `/process-agent-queue`, `/agentic-coding` v6, `/issues-abarbeiten`.
> **Governance:** ADR-209 v2. v1 (Wartungs-Loop) verworfen per Self-Red-Team.

---

## Leitprinzip

Jede manuelle Per-Repo-Reparatur ist ein Eingeständnis, dass die geteilte
Quelle eine Klasse nicht verhindert. Ziel ist, den Loop **abzuschaffen**, nicht
ihn zu perfektionieren.

## Gates G1–G7 (Klassifizierer-Regeln, empirisch Lauf 1)

G1 Status = letzter *push/PR*-Lauf, **nie `gh run list --limit 1`** (grüner
Dependabot maskiert roten Deploy). G2 jede Klassifikation am Repo verifizieren.
G3 Versions-/API-Check vor jedem Dep-Swap (Lauf 1: 8-Repo-Downgrade-Beinahe).
G4 cross-cutting/shared zuerst. G5 Deploy/Infra nie autonom. G6 Judgment
(Test-vs-Code, Gate-Senkung, Star-Import) → `ci-green` ohne `auto`. G7
Contract-First: Issue benennt die wiederhergestellte erzwungene Regel.

---

## Phasen

### Phase 0 — Portfolio-Triage (einmalig, Opus/Human, G6)
Jedes Repo: **live / maintenance / dead**. `dead` → archivieren (CI-Pflege
einstellen, nicht grün-halten). Reduziert Scope *bevor* investiert wird —
größter MTTR-Hebel ist weniger Fläche.

### Phase 1 — Bootstrap-Survey (EINMALIG, nicht wiederkehrend)
Über live-Repos: letzter push/PR-Lauf (G1) → Fehlerklassen-Matrix. Dient nur
als Konvergenz-Backlog. Danach **kein Polling mehr** — siehe Phase 3.

### Phase 2 — Konvergenz (der eigentliche Hebel, Opus-Design + Sonnet-Rollout)
Eine gehärtete reusable Workflow-Familie (`_ci-*.yml`) als Single Source:
- Python-Version aus `requires-python` abgeleitet (nicht hartkodiert)
- org-weite ruff-Config zentral
- `git+...#subdirectory`-Deps = Hard-Fail (Conformance-Check)
- secret-scan/permissions/cache zentral korrekt (vgl. #191)
Pro live-Repo: lokale CI durch `uses:` der shared Workflow ersetzen +
Conformance-Check grün. Das **eliminiert** Lint/Python-Pin/Dead-Dep/
Permission-Klassen permanent statt sie zu detektieren.

### Phase 3 — Event-driven Remediation (Steady State, autonom)
Org-Level: CI-rot-Event → Klassifizierer-Skript (G1–G7 als Code) →
mechanische Klasse → auto-Fix-PR (Sonnet) / sonst → eskalieren (Opus, nur
`UNKNOWN`/novel). Kein Survey, kein Opus-am-Eingang.

### Phase 4 — Anti-Goodhart-Enforcement (Dauer-Invariante)
Kein Fix senkt ein Gate (Coverage/Lint/Skip) ohne Eintrag in
`docs/ci-waivers.md`: `repo · gate · grund · expires:<datum>`. Abgelaufener
oder fehlender Waiver bei gesenktem Gate = CI-Fail. „Grün" bleibt verdient.

### Phase 5 — Lehren-Rückschrieb (Pflicht-Abschluss jeder Aktion)
Neue Erfahrung → Gates/Phasen ergänzen + orchestrator-memory
`queue-run:<date>` + `project_ci_green_program.md`.

---

## Exit-Kriterium (das Programm schaltet sich selbst ab)
Wenn **≥90 % der live-Repos** die shared-CI per `uses:` nutzen **und**
Red-Rate **< 10 % über 30 Tage**: Standing-Programm zurückziehen, nur den
Thin-Event-Handler (Phase 3) + Anti-Goodhart (Phase 4) behalten. Skill wird
dann auf „retired — siehe ADR-209 Exit" gesetzt. Ohne Exit-Prüfung wird das
Programm selbst zur verwaisten Infra.

## Modell-Routing
Sonnet = Default (klassifizierte mechanische Fixes, Phase 3). Opus =
Konvergenz-Design (Phase 2) + Eskalation (`UNKNOWN`) + Portfolio-Triage.
Cerebras verworfen (Tool-Use-Schwäche).
