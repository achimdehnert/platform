# Runbook: GHCR `403 Forbidden` beim Deploy-Build-Push

**Scope**: Ein `Deploy`-Workflow scheitert im Job `deploy / 🐳 Build` beim Push des
Container-Images nach `ghcr.io/<owner>/<repo>` mit `403 Forbidden` — **obwohl** die
Workflow-Permissions korrekt sind. Betrifft die Publishing-Konvergenz (ADR-266) und
die Deploy-Health (session-start Phase 0.7). Realfall: billing-hub 2026-07-04.

**Wer kann das ausführen**: Package-Owner (GitHub-User/Org, der `ghcr.io/<owner>/<repo>`
besitzt) — die granulare *Manage Actions access* ist nur über die GHCR-UI setzbar.

## Symptome (wann dieses Runbook?)

Im Build-Log des `Deploy`-Runs:

```
#NN ERROR: failed to push ghcr.io/<owner>/<repo>:main-<sha>:
  unexpected status from HEAD request to
  https://ghcr.io/v2/<owner>/<repo>/blobs/sha256:…: 403 Forbidden
##[error]buildx failed with: ERROR: failed to build: failed to solve: failed to push …: 403 Forbidden
```

- `deploy / 🐳 Build` = **failure**, `deploy / 🚀 Production` = **skipped**
  → **Prod-Image bleibt unberührt** (die alte Revision läuft weiter, kein Outage durch den Fehlschlag).
- Tritt oft auf einem **docs-only-Push** auf (deploy-on-push ohne paths-Filter), fällt daher leicht auf.

## Schritt 0 — Ursache NICHT raten (billigster Gegenbeweis zuerst)

> 🌀 GHCR-Fehlzuordnung ist eine wiederkehrende Falsch-Diagnose-Quelle
> (org-weit ≥2× retraktiert). **Nicht** reflexartig „Token/Workflow kaputt" behaupten.

Vergleiche das `deploy.yml` des roten Repos mit einem **Nachbar-Repo, das gerade grün
pusht**:

```bash
for r in <rotes-repo> <gruenes-nachbar-repo>; do
  echo "== $r =="
  gh api repos/<owner>/$r/contents/.github/workflows/deploy.yml --jq '.content' \
    | base64 -d | grep -nE 'permissions:|packages:|contents:|_deploy-unified|_ci-python'
done
```

**Ist die Config identisch** (`permissions: contents:read, packages:write` +
gleiche `_deploy-unified.yml@vX`) und das eine Repo pusht trotzdem grün → das
Problem sitzt **NICHT im Workflow**, sondern auf **Package-Ebene**. Weiter zu Schritt 1.

(Realfall 2026-07-04: billing-hub und cad-hub byte-identisch — cad-hub grün, billing-hub 403.)

## Schritt 1 — Fix: Repo in *Manage Actions access* des Packages aufnehmen

GHCR-UI:

```
https://github.com/users/<owner>/packages/container/<repo>/settings
  → Abschnitt "Manage Actions access"
  → "Add Repository" → <repo> auswählen → Rolle "Write"
```

Ursache: Das Package war nicht (mehr) mit Write für das Repo verknüpft — passiert,
wenn das Package älter ist als die Repo-Verknüpfung oder von einem anderen Actor
angelegt wurde. **Die Einstellung persistiert** (GitHub resettet sie nicht) → der
Fix ist damit dauerhaft.

## Schritt 2 — Verifizieren (deploy-green ≠ live)

```bash
# 1. Fehlgeschlagenen Deploy-Run neu laufen lassen (nur failed Jobs)
gh run rerun <run-id> -R <owner>/<repo> --failed

# 2. Warten bis completed, dann Build + Production prüfen (NICHT nur run-conclusion)
gh run view <run-id> -R <owner>/<repo> --json jobs \
  --jq '.jobs[]|select(.name|test("Build|Production"))|"[\(.conclusion)] \(.name)"'
#   erwartet: [success] deploy / 🐳 Build   +   [success] deploy / 🚀 Production

# 3. Live-Check am Prod-Endpoint
curl -s -o /dev/null -w "%{http_code}\n" https://<domain>/healthz/    # erwartet 200
```

## Grenzen / warum kein automatisierter Gate

- Die granulare per-Repo *Actions access* ist **nicht über die REST-API lesbar**
  (`/users/<owner>/packages/container/<repo>/…` → 404). Ein Fleet-Meter genau für
  dieses Setting ist daher **nicht baubar**.
- `.repository.full_name` am Package (`gh api /users/<owner>/packages/container/<repo>`)
  ist nur ein **schwacher Proxy** — ein fehlender Link bedeutet nicht zwingend 403
  (Beispiel 2026-07-06: risk-hubs Package hatte keinen `repository`-Link, deployte
  trotzdem grün).
- **Detektion = der Deploy-Health-Scan** (session-start Phase 0.7): regressiert das
  Setting je, 403't der nächste Build und der Scan fängt es. Das ist das stehende
  Sicherheitsnetz, kein zusätzlicher Gate nötig.
- **Kein Umbau auf PAT-Login** als „Fix" — die identische Config pusht bei allen
  anderen Repos grün; ein PAT wäre mehr Secret-Verwaltung bei gleichem Ergebnis.

## Referenzen

- ADR-266 (PyPI-/Publishing-Konvergenz — GHCR-Publishing-Nachbarschaft)
- session-start Phase 0.7 (Deploy-Health-Scan als Detektion)
- CC-Memory `reference_ghcr_403_push_package_actions_access` (Recall-Kurzform)
- Verwandt: `docs/runbooks/KONZ-002-s3-repo-transfer.md` (Org-Transfer entzieht Package-/PAT-Zugriff)
