---
status: accepted
date: 2026-06-06
decision-makers: Achim Dehnert
consulted: –
informed: –
implementation_status: implemented
implementation_evidence:
  - ".github/workflows/guardian.yml: PR-getriggerter Job 'Architecture Guardian' (opened/synchronize/reopened), postet Review-Kommentar; Dependabot/Renovate ausgenommen."
  - "agents/guardian.py: `python -m agents.guardian --diff <pr.diff> --format json|markdown` analysiert das PR-Diff gegen Architektur-Regeln."
  - "Als CI-Check 'guardian' auf allen platform-PRs sichtbar (required check)."
domains: [governance, ci-cd, architecture, agents]
scope: platform
relates_to: [ADR-056, ADR-057, ADR-058, ADR-059, ADR-061, ADR-177, ADR-184, ADR-223, ADR-231]
tags: [architecture-guardian, ci-gate, compliance, pr-review, agent, renumbering-fix]
---

# ADR-239: Architecture Guardian — PR-Zeit-Architektur-Compliance-Agent

> **Formalisiert eine bereits gelebte, aber nie verankerte Entscheidung.** Mindestens 9 aktive
> ADRs (056/057/058/059/061/177/184/223/231) referenzieren einen „Architecture Guardian" als
> Enforcement-Mechanismus und zitierten dafür durchgängig **ADR-054** — aber ADR-054 ist eine
> archivierte, durch ADR-056 abgelöste *deployment-preflight*-ADR und war nie der Guardian.
> Der Guardian existiert real (CI), hatte aber keine überlebende ADR. Diese ADR schließt die
> Lücke (Full-Scan 2026-06-06, Root-Cause-B-„Phantom").

## Kontext

Der „Architecture Guardian" wird quer durch den ADR-Korpus als selbstverständlicher
Compliance-Mechanismus zitiert (Contract-Tests ADR-184, Test-Taxonomie ADR-058/059,
Hardcoding ADR-061, Rollen-Spezialisierung ADR-177, Model-Routing-Signale ADR-223,
SSoT-Pointer ADR-231 …). Alle zeigten auf **ADR-054**, das archiviert und thematisch
unzutreffend ist (deployment-preflight, `superseded_by: ADR-056`). Es gab also einen
breit referenzierten **Entscheid ohne Record** — ein Phantom, das den
Renumbering-Drift mit verursacht (Leser folgen der Zitatkette ins Archiv).

## Entscheidung

Wir verankern den **Architecture Guardian** als eigenständige, akzeptierte
Plattform-Entscheidung mit dieser ADR (ADR-238) und machen sie zum kanonischen
Referenzziel für alle „Architecture Guardian"-Zitate.

**Mechanismus (real implementiert):**
- `.github/workflows/guardian.yml` — Job *Architecture Guardian*, getriggert auf
  `pull_request` (opened/synchronize/reopened), `permissions: pull-requests: write`;
  Dependabot/Renovate-PRs ausgenommen.
- `agents/guardian.py` — `python -m agents.guardian --diff <pr.diff> --format json|markdown`
  prüft das PR-Diff gegen Architektur-/Plattform-Regeln und postet das Ergebnis als
  PR-Kommentar. Als CI-Check `guardian` auf platform-PRs sichtbar.

**Verhältnis zu ADR-054:** ADR-238 `supersedes` ADR-054 für die „Architecture Guardian"-
Bedeutung. ADR-054 bleibt archiviert (sein *deployment-preflight*-Inhalt ist davon
unabhängig durch ADR-056 abgelöst). Alle Guardian-Zitate werden von ADR-054 auf ADR-238
repointet (begleitender Cleanup-PR).

## Konsequenzen

- **Gut:** Der breit referenzierte Guardian hat endlich einen Record; Zitatketten landen
  nicht mehr im Archiv. Eine zentrale Quelle des Renumbering-Drifts (Magnet-Nummer 054)
  ist neutralisiert.
- **Gut:** Künftige Guardian-Regel-Erweiterungen (z. B. ADR-059 Drift-Detector-Kopplung,
  ADR-058 Taxonomie-Checks, ADR-184 Contract-Regeln) haben ein definiertes Anker-ADR.
- **Neutral:** Kein Verhaltens-/Code-Change — `guardian.yml` + `agents/guardian.py` laufen
  unverändert; dies ist die Dokumentation des Status quo, kein neuer Mechanismus.

## Verifikation

- `.github/workflows/guardian.yml` vorhanden (Job `Architecture Guardian`).
- `agents/guardian.py` vorhanden (`python -m agents.guardian`).
- CI-Check `guardian` läuft auf platform-PRs (in dieser Session auf #492/#495/#499/#500/#503/#504 grün beobachtet).
