# Runbook — OOTB-A: Shared-CI aus `platform` herauslösen (Tag-gepinnt)

> Optimierung aus dem adversarialen Review (2026-06-04). Löst den `platform`-SPOF
> **und** das OOTB-5-Cutover-Problem **by construction**. Werkzeug: [`tools/ref-sweep.py`](../../tools/ref-sweep.py) (gehärtet).

## Problem (Review-Befund)

Die gesamte CI von ~30 Repos hängt an **einem** Repo `achimdehnert/platform`, referenziert per **`uses: …@main`**. Zwei reale Risiken:
1. **Supply-Chain / SPOF:** ein Push auf `platform/main` deployt sofort, ungereviewt, in alle 30 Consumer-CIs (inkl. Deploy-/Publish-Workflows mit Secrets/OIDC). `@main` = keine stabile Version, kein Review-Gate.
2. **Harter Cutover:** `uses:` folgt dem Transfer-Redirect **nicht** ([ootb5-Runbook](./KONZ-002-ootb5-ref-sweep.md)) → ein `platform`-Move bräche alle 30 Consumer gleichzeitig.

## Lösung

Die geteilten Bausteine in ein **eigenes, langlebiges, NIE migriertes** Repo `iilgmbh/shared-ci` ziehen, Consumer auf **Tag** statt `@main` pinnen, Dependabot hält sie aktuell.

- 6 reusable Workflows: `_ci-python`, `_ci-pypi`, `_deploy-unified`, `_deploy-hetzner`, `_build-docker`, `_ci-odoo`
- 3 composite actions: `gitleaks-scan`, `install-iil-packages`, `resolve-install-extra`

**Warum besser:** Tag-Pinning = stabile Version + Supply-Chain-Schutz (Updates = reviewbare Dependabot-PRs). `shared-ci` wird nie transferiert → `platform` (und jedes andere Repo) kann frei umziehen, **kein** `uses:`-Bruch mehr. Eigene CODEOWNERS/Recovery-Owner → entkoppelt vom Bus-Faktor des Mono-`platform`.

## Schritte

| # | Schritt | Reversibel? | Gate |
|---|---|---|---|
| **B1** | Repo `iilgmbh/shared-ci` anlegen (in Enterprise → erbt Posture) **+ Actions-Access = `organization`** setzen: `gh api -X PUT repos/iilgmbh/shared-ci/actions/permissions/access -f access_level=organization` | additiv | — |
| **B1-Pflicht** ⚠️ | **Canary-Fund 2026-06-04:** ein privates Shared-CI teilt seine Actions per Default NICHT (`access_level: none`) → jeder Consumer scheitert an *Set up job* (`repository not found`). OHNE diesen Schritt bricht der Sweep über alle 30 Repos gleichzeitig. Bereits live gesetzt. | — | vor B4 |
| **B2** | Die 6 Workflows + 3 Actions hineinkopieren; **interne Self-Refs** (`achimdehnert/platform/...` *innerhalb* der Bausteine) auf `iilgmbh/shared-ci/...` setzen | additiv | B1 |
| **B3** | `v1.0.0` taggen | additiv | B2; Smoke: 1 Demo-Repo gegen `@v1.0.0` grün |
| **B4** | **Consumer sweepen:** `ref-sweep.py --old achimdehnert/platform --new iilgmbh/shared-ci --pin v1.0.0` — **erst `--apply --limit 1` (Canary)** → grün → dann voll | PRs reversibel | **scharf** |
| **B5** | Dependabot `github-actions` in Consumern (hält `@v1`-Pins aktuell) | additiv | nach B4 |
| **B6** | reusable Workflows aus `platform` entfernen/archivieren (erst wenn ALLE Consumer auf `shared-ci` + grün) | reversibel (re-add) | B4 vollständig grün |

## Werkzeug-Härtung (ref-sweep.py, Review-Fixes)
- Ersetzt nur echte **`uses:`-Zeilen** (Kommentare/Banner werden übersprungen).
- **Wortgrenze**: `achimdehnert/platform` matcht nicht `…/platform-tools`.
- **`--pin v1.0.0`**: repinnt `@main` → `@v1.0.0` (killt das `@main`-Antipattern).
- **`--limit N`** (Canary) + **Branch-/PR-Idempotenz** (Re-Run dupliziert nicht).

## Gates / Leitplanken
- **B4 ist der einzige scharfe Schritt** → **Canary (`--limit 1`) zuerst**, verifizieren (Consumer-CI grün gegen `@v1.0.0`), dann voll. Kein Auto-Merge ohne Sicht auf ≥1 grüne Canary-PR.
- B1–B3 sind additiv (nichts zeigt auf `shared-ci`, bis B4) → null Bruch-Risiko.
- `platform`-Move ist nach OOTB-A **kein Sonderfall** mehr (siehe ootb5-Runbook: Cutover-Problem entfällt).

## Changelog
- 2026-06-04: **Canary** (iilgmbh/desktop-setup → shared-ci@v1.0.0) **grün** nach Access-Fix; B1 um Pflicht-Access-Policy ergänzt (privates Shared-CI braucht `access_level=organization`).
- 2026-06-04: Initial — OOTB-A-Design (shared-ci-Extraktion + Tag-Pinning); ref-sweep.py gehärtet (uses:-Anker, --pin, --limit, Idempotenz).
