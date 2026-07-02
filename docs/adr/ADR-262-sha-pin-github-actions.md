---
status: proposed
date: 2026-07-02
decision-makers: Achim Dehnert
consulted: –
informed: –
implementation_status: not-started
domains: [security, ci-cd, supply-chain, infra]
scope: platform
amends: []
relates_to: [ADR-209, ADR-226, ADR-229]
tags: [supply-chain, github-actions, sha-pinning, dependabot, oidc, secrets, ci-hardening]
---

# ADR-262 — GitHub-Actions per SHA pinnen (Supply-Chain-Härtung, fleet-weit)

> **Nummer provisorisch (262) — Allokation zur Merge-Zeit (ADR-065).**

## Kontext

Die Fleet-Konvergenz-Runde 2026-07-02 (Cluster A) hat per Codebase-grep die **größte einzelne
Cross-Repo-Reichweite** aller Befunde belegt:

```
uses: <owner>/<action>@v<N>  (mutable Tag, excl. actions/checkout|setup-*|cache|*-artifact)
→ 37 Repos mit third-party Actions an beweglichen Tags.
```

Bewegliche Tags (`@v4`, `@main`) sind **umschreibbar**: ein kompromittierter oder übernommener
Action-Publisher kann denselben Tag auf bösartigen Code zeigen lassen. Kritisch, weil viele dieser
Refs in **secret-/OIDC-privilegierten Pfaden** liegen (Publish-`@release/v1`, Deploy-`ssh-action`,
`packages:write`). ADR-226 hat den PyPI-Publish-Gate-Invarianten bereits gehärtet — die Action-Refs
selbst sind der verbleibende, ungepinnte Supply-Chain-Vektor.

**Prämissen-Check (Evidenz vor Behauptung):** In `platform/tools/` und `infra-deploy/.github/workflows/`
existiert **kein** Pin-Tool/-Gate (grep-verifiziert 2026-07-02) → dieser Fix ist net-new. `platform-pinned`
ist **nicht** die Lösung, sondern ein stale Meta-Repo-Duplikat (33 eigene mutable Pins).

Cross-cutting über 37 Repos + Security-Perimeter → ADR-pflichtig (nicht 37 Einzel-Patches).

## Entscheidung

**Alle third-party GitHub-Actions werden per Commit-SHA gepinnt; Aktualität hält Dependabot.**

1. **SHA-Pin-Pflicht.** `uses: owner/action@<full-40-char-sha>  # vX.Y.Z` für alle nicht-`actions/*`-
   Actions. Erststufe darf `actions/*` (GitHub-eigen) an Major-Tags belassen; alles andere SHA.
2. **Dependabot (github-actions-Ökosystem)** in jedem Repo → automatische SHA-Bump-PRs, damit Pinning
   nicht zu Stagnation führt. Verteilt über das onboard-repo-/shared-CI-Template.
3. **Gate.** Ein `check_action_pins`-Skript in `platform/tools/` (Spiegel der lokalen Hard-Gates,
   `make check-push`-integrierbar) + ein Fleet-CI-Meter analog `pypi-gate-meter.yml` (ADR-209-Muster):
   erst **messend** (Report, kein Block), dann nach Konvergenz **blockierend**.
4. **Priorisierung nach Privileg.** Zuerst secret-/OIDC-Pfade (publish/deploy), dann restliche.

## Konsequenzen

- **Positiv:** schließt den größten belegten Supply-Chain-Vektor; Dependabot hält Pins frisch;
  messen-vor-blocken vermeidet Fleet-weiten Rot-Schlag (ADR-209-Lehre).
- **Negativ / Risiko:** initialer Umschreib-Aufwand über 37 Repos; Dependabot-PR-Rauschen (mit
  Grouping mildern). Ein org-weiter Automatismus mit `contents:write` (Dependabot) — Rollout des
  Gates braucht **Dry-Run-in-CI** vor scharf (Gate `autonomous-no-human-review`).
- **Reichweite (grep-belegt):** platform 33, shared-ci 13, nl2cad 11, iil-pet-portal 9, mcp-hub 8,
  dev-hub 6, meiki-hub 6, bfagent 5, bahn-hub 5, infra-deploy 4 … (37 Repos gesamt).

## Verifiziert / nicht verifiziert

- **Verifiziert:** 37 Repos mit mutable third-party Pins; kein bestehendes Pin-Tool.
- **Nicht verifiziert:** welche der 37 Repos secret/OIDC in genau diesen Jobs nutzen — billigster Check
  ist `grep -l 'secrets:\|id-token: write' <repo>/.github/workflows/*` je Repo (Teil der Priorisierung).
