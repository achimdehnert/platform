# Runbook — platform Runner-Reprovisionierung & Secret-Re-Population (Org-Transfer)

> **Zweck:** Den teuersten Bruch eines `achimdehnert/platform` → `iilgmbh/platform`-Transfers
> vorab absichern — der self-hosted Runner ist **repo-gebunden** und die 15 Repo-Secrets werden
> beim Transfer **nicht** mitübertragen. Ohne dieses Runbook bedeutet „Transfer geklickt" =
> 10 self-hosted-Workflows tot + alle Prod-Secrets leer, ohne dokumentierten Rückweg.
> **Phase-B-Artefakt** aus [`KONZ-platform-012`](../konzepte/KONZ-platform-012-platform-org-migration.md);
> die vom Maintainer-2028-Adversariat + KONZ-002-S3 identifizierte Lücke (S3 kennt nur
> Secrets/Webhooks/Deploy-Keys, **keinen Runner-Fall**).
> **Status:** aktiv (Vorbereitung) · **Owner:** Achim Dehnert · **Review-by:** 2026-09-15
> **Wird ausgeführt:** erst in KONZ-012 **Phase C** (nach Kill-Gate + Coupling-Indirektion) — dies
> ist der *Plan*, nicht die Durchführung.

## Ist-Zustand (verifiziert 2026-07-05, am Host)

| Fakt | Wert | Beleg |
|---|---|---|
| Runner-Service | `actions.runner.achimdehnert-platform.prod-server.service` | `systemctl list-units` @ hetzner-prod |
| Install-Dir | `/opt/actions-runner-platform` | `ls -d` @ Host |
| Registriert auf | `https://github.com/achimdehnert/platform`, agentName `prod-server` | `.runner`-Config (URL/Name, keine Secrets) |
| Tooling | `config.sh` + `svc.sh` vorhanden | `ls` @ Host |
| Abhängige Workflows | **10 aktive** self-hosted (`_ci-python`, `sync-adrs-to-devhub`, `sync-registry-to-devhub`, `megatest`, `backup-meter`, `branch-protection-meter`, `apply-branch-protection`, `platform-audit`, `sync-policies-to-orchestrator`, `scaffold-tests`) | `grep runs-on:self-hosted .github/workflows/` |
| Repo-Secrets (Anzahl) | **15** | `gh secret list --repo achimdehnert/platform` |
| Secret-Quell-SSoT | [`infra/secrets-inventory.yaml`](../../infra/secrets-inventory.yaml) (378 Z.) + `~/.secrets/` | vorhanden |

## Warum das kritisch ist (Blast-Radius)

- **`_ci-python`** ist der Blocking-Gate JEDER PR der shared-ci-Konsumenten — fällt der Runner aus,
  stehen Cross-Repo-PRs fleet-weit still, nicht nur platform.
- **`backup-meter`** blind = Backup-Monitoring aus (Kategorie des risk-hub-NULL-Backup-Vorfalls).
- **sync-adrs/sync-registry** still → dev-hub-Katalog driftet unbemerkt.
- Leere Secrets → Hetzner-Deploy (kein SSH-Key), SOPS unentschlüsselbar (kein AGE-Key),
  PyPI-Publish (kein Token). Exakt die coach-hub-Signatur (2026-06-14), diesmal am SSoT.

## Vorab-Inventar (VOR dem Transfer erfassen — Pflicht, Schema A)

```bash
# 1. Repo-Secret-Namen sichern (nur Namen — Werte sind NICHT auslesbar):
gh secret list --repo achimdehnert/platform > /tmp/platform-secrets-pre-transfer.txt
# 2. Quell-Zuordnung je Secret aus dem Inventar bestätigen (NICHT raten):
#    infra/secrets-inventory.yaml ist die SSoT — je Secret: source, scope, rotation.
#    Secrets ohne dokumentierte Quelle VOR dem Transfer klären, sonst nach Transfer nicht
#    re-populierbar.
# 3. Runner-Config sichern:
ssh hetzner-prod 'sudo cat /opt/actions-runner-platform/.runner' > /tmp/platform-runner-config-pre.json  # nur zur Referenz (URL/Name/Pool-ID)
```

## R-R1 — Runner de-registrieren (VOR/während Transfer)

```bash
ssh hetzner-prod
cd /opt/actions-runner-platform
sudo ./svc.sh stop
sudo ./svc.sh uninstall
# Alten Repo-Runner aus GitHub entfernen (Token vom ALTEN Repo, solange erreichbar):
./config.sh remove --token <REMOVE_TOKEN_von_achimdehnert/platform>
# REMOVE_TOKEN: gh api -X POST repos/achimdehnert/platform/actions/runners/remove-token --jq .token
```
> Wird der Runner NICHT sauber entfernt, bleibt ein toter „offline"-Eintrag am alten Repo zurück
> und die Host-Registrierung kollidiert bei der Neu-Registrierung.

## R-R2 — Runner neu registrieren (auf `iilgmbh/platform`, NACH Transfer)

**Option A — Repo-Runner (1:1-Ersatz, minimal):**
```bash
# Registration-Token vom NEUEN Repo (braucht Zugriff auf iilgmbh/platform):
# gh api -X POST repos/iilgmbh/platform/actions/runners/registration-token --jq .token
ssh hetzner-prod
cd /opt/actions-runner-platform
./config.sh --url https://github.com/iilgmbh/platform --token <REG_TOKEN> \
  --name prod-server --labels self-hosted --unattended --replace
sudo ./svc.sh install
sudo ./svc.sh start
```

**Option B — Org-Runner-Pool (empfohlen für Ziel-Zustand, braucht `admin:org`):**
```bash
# gh api -X POST orgs/iilgmbh/actions/runners/registration-token --jq .token
./config.sh --url https://github.com/iilgmbh --token <ORG_REG_TOKEN> \
  --name prod-server --labels self-hosted --runnergroup Default --unattended --replace
```
> Org-Runner erlauben Wiederverwendung über mehrere iilgmbh-Repos (weniger Host-Registrierungen
> bei künftigen Transfers) — der eigentliche strukturelle Gewinn des Org-Modells.

## R-R3 — Secrets re-populieren (NACH Transfer, scoped)

```bash
# Je Secret aus infra/secrets-inventory.yaml → ~/.secrets/<quelle> → neues Repo/Org:
# Repo-scoped (1:1-Ersatz):
gh secret set <NAME> --repo iilgmbh/platform < <wert-aus-quelle>
# ODER Org-scoped (nur wo geteilt sinnvoll — KONZ-002 REC-10: smallest sensible scope,
# NICHT blanket; Prod-Kronjuwelen wie SOPS_AGE_KEY/HETZNER_SSH_KEY repo-scoped lassen):
gh secret set <NAME> --org iilgmbh --visibility selected --repos platform < <wert>
```
**Reihenfolge nach Kritikalität:** zuerst die Deploy-/Sync-blockierenden (`HETZNER_*`,
`SOPS_AGE_KEY`, `DEVHUB_WEBHOOK_SECRET`, `PLATFORM_DEPLOY_TOKEN`), dann Publish (`PYPI_API_TOKEN`),
dann LLM-Keys (`GROQ`/`OPENAI`/`CEREBRAS`).

## R-R4 — Post-Transfer-Verifikation (Pflicht, VOR „fertig")

```bash
# 1. Runner online am neuen Repo/Org:
gh api repos/iilgmbh/platform/actions/runners --jq '.runners[]|"\(.name):\(.status)"'   # → online
# 2. Ein self-hosted-Workflow als Rauchtest grün (attempt-aware, nach Transfer):
gh workflow run megatest.yml --repo iilgmbh/platform   # dann run view → success
# 3. Secret-abhängiger Pfad grün: sync-registry-Dispatch → completed success
# 4. Kein Secret leer: jeder der 15 Namen via `gh secret list --repo iilgmbh/platform` vorhanden
# 5. OIDC/Trusted-Publishing: EIN echter Publish-Dry-Run (REC-6 — Dry-Run beweist nicht Identität,
#    nur ein echter Lauf durch den finalen Pfad zählt).
```
> „11 Workflows laufen wieder" gilt erst als bewiesen, wenn mind. 1 self-hosted + 1 secret-
> abhängiger Workflow **nach** dem Transfer grün lief (nicht bloß Runner=online).

## Rollback-Grenze

Bricht R-R2/R-R3 und Prod (Hetzner-Deploy) ist betroffen: Der Rückweg ist ein **zweiter** Transfer
zurück auf `achimdehnert/platform` — er kostet erneut R-R1+R-R2 (Runner) + R-R3 (15 Secrets). Das
ist die „Einbahn-Exit"-Realität (KONZ-002): Rollback ist möglich, aber selbst ein Incident, keine
kostenlose Rückabwicklung. **Daher:** Transfer nur in einem angekündigten Wartungsfenster, mit
diesem Runbook offen, und erst nach grünem Consumer-CI-Beweis gegen `uses: iilgmbh/platform/...@main`.

## Verwandt

- [`KONZ-platform-012`](../konzepte/KONZ-platform-012-platform-org-migration.md) — Mutter-Konzept (Phase C = Durchführung).
- [`platform-owner-recovery.md`](platform-owner-recovery.md) — Owner-/Leaver-Prozess (Phase A).
- [`KONZ-002-s3-repo-transfer.md`](KONZ-002-s3-repo-transfer.md) — Transfer-Runbook (Secrets/Webhooks/Deploy-Keys; dieses hier ergänzt den fehlenden Runner-Fall).
- [`infra/secrets-inventory.yaml`](../../infra/secrets-inventory.yaml) — Secret-Quell-SSoT.
