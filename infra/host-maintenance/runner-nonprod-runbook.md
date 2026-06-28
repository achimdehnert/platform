# Non-Prod CI-Runner — Betriebs-Runbook (ADR-257 Folge-Artefakt)

> **Status:** Entwurf (begleitet ADR-257 `proposed`). Erfüllt die in ADR-257
> §Folge-Artefakte (REC-5/REC-7) geforderte Härtungs-Checkliste **+** operatives
> Playbook. Setzt **keinen** Runner in Betrieb — das ist ein bewusster, gegateter
> Schritt nach Annahme von ADR-257.
>
> **Was ADR-257 entscheidet:** CI/Test-Workloads laufen **nicht** mehr auf dem
> Prod-Host; ein dedizierter **Non-Prod-Runner** übernimmt sie, `prod-server` wird
> für CI deprecated. Dieses Runbook ist das *Wie der Runner-Realisierung* —
> konkretisiert als **Alternative E** (Runner auf dem bestehenden Staging-Host).

## 1. Zielhost — verifiziert 2026-06-28 (read-only, `server_probe` + `ssh … df/free/docker ps`)

| Merkmal | Staging `88.99.38.75` (`ubuntu-32gb-fsn1-1`) | Prod `88.198.191.108` (heute kontendierend) |
|---|---|---|
| Specs | 16 CPU, 32 GB RAM | 8 GB RAM |
| Disk | 601 G, 18 % belegt → **475 G frei** | 150 G (war Sa 2026-06-27 voll → Deploy-Fail) |
| Docker | 29.1.3 | ✓ |
| Laufende Container | 29 (risk_hub_staging/local, cad/ttz/welten/writing_hub, ib_gateway …) | alle Prod-Hubs |
| Actions-Runner | **keiner** (frei; `hosts.yaml: hosts_runners: []`) | 18× `actions.runner.<repo>.prod-server` |

→ Die Disk-/RAM-Contention, die den 2026-06-27-Deploy-Fail verursachte, ist auf
diesem Host **strukturell entschärft** (4× Disk, 6× RAM). Nicht angenommen — gemessen.

## 2. Runner-Modell (spiegelt die Prod-Konvention, anderer Pool/Label)

Prod = **ein Runner pro Repo** (`/opt/actions-runner-<repo>`, Service
`actions.runner.achimdehnert-<repo>.prod-server.service`). Auf Staging spiegeln:

| Aspekt | Wert |
|---|---|
| Install-Dir | `/opt/actions-runner-<repo>` (gleiches Schema) |
| Service | `actions.runner.achimdehnert-<repo>.staging-ci.service` |
| Labels | `[self-hosted, Linux, X64, ci-nonprod]` — **kein** `prod`/`prod-server` |
| User | dedizierter `github-ci` (kein root, **kein `user:0:0`** — REC-5) |

## 3. Registrierung (pro Repo)

```bash
REPO=travel-beat   # Pilot
TOKEN=$(gh api -X POST repos/achimdehnert/$REPO/actions/runners/registration-token -q .token)
sudo -u github-ci bash -c "
  cd /opt/actions-runner-$REPO &&
  ./config.sh --url https://github.com/achimdehnert/$REPO \
    --token $TOKEN --labels ci-nonprod --name $REPO-staging-ci \
    --unattended --replace"
# Service als github-ci installieren (NICHT root):
cd /opt/actions-runner-$REPO && sudo ./svc.sh install github-ci && sudo ./svc.sh start
```

## 4. Label-Gate (REC-2/3 — Enforcement)

Der bestehende `runner-label-check.yml` (validiert `runs-on` gegen `hosts.yaml`,
hat den `ALLOWED_EXTRA`-Hook) wird **erweitert** — kein neues Gate:

- `ALLOWED_EXTRA = {"ci-nonprod", "deploy-prod"}` (statt leer)
- Neue Regel: **CI/Test-Jobs mit plain `self-hosted` ODER `prod-server` → rot.**
  Nur Deploy-Jobs (ADR-156) dürfen `deploy-prod`/`prod-server`.
- `hosts.yaml`: neuen Runner als eigenen Eintrag `status: online` führen (SSoT-Pflicht),
  `prod-server`-CI-Deprecation dort vermerken.

## 5. Härtung (REC-5 — Checkliste, vor `svc.sh start`)

- [ ] Runner läuft als `github-ci`, **nicht** root; `github-ci` ist **nicht** in `docker` group, außer Builds brauchen es.
- [ ] **Kein** breiter `-v /var/run/docker.sock`-Mount in CI-Jobs; Builds via rootless `buildx`-Container.
- [ ] Secret-Scope: Staging-Runner bekommt **nur** CI-Secrets (Test-DB, Registry-**Read**). **Keine** Prod-Deploy-Keys — die bleiben am `prod-server`/`infra-deploy`-Runner (ADR-156-Carve-out).
- [ ] `STATIC_ROOT`/Scratch auf tmpfs oder Job-eindeutigem Pfad (Präzedenz: Runner-Pollution-Fix).
- [ ] Patch-Kadenz für den Host dokumentiert (unattended-upgrades aktiv).
- [ ] Resource-Limits: Runner-Service mit `Nice=10`, optional `CPUQuota=`/`MemoryMax=` via systemd-drop-in, damit CI die Staging-Stacks nicht verdrängt.

## 6. Hygiene-Check (REC-6/8 — Mess-Gate, speist ADR-257 Kill-Gate)

Scheduled, **read-only** Check je Runner-Host (Muster wie `infra-cleanup.timer`):
misst Host-Port-Bindungen durch CI · verwaiste `runserver`/CI-Prozesse · Disk/Volumes-Druck
· CPU/RAM-Sättigung · Docker-Socket-Nutzung. **Rot bei Verstoß** → Signal für das
ADR-257-Kill-Gate (Stichtag 2026-09-24).

## 7. Operatives Playbook — wenn der Hygiene-Check rot wird

| Symptom | Sofort-Aktion | Eskalation |
|---|---|---|
| Host-Port-Bindung durch CI-Job | Job-Workflow auf hermetische Form prüfen (run-eindeutige Ports, kein `0.0.0.0:host`-Bind) | Repo-Workflow-Fix per ADR-222-Familie |
| Verwaister `runserver`/`&`-Prozess | Prozess killen, `_work/_temp` des Runners räumen (idle) | Job-Teardown-Garantie nachziehen |
| Disk/RAM-Sättigung | `infra-cleanup`-Lauf; CI-Concurrency drosseln | Bei Wiederholung: eigener Host (Alt D ohne E) |
| Runner-Kompromittierung vermutet | Runner-Service stoppen, aus GitHub deregistrieren, Secrets rotieren | Quarantäne, Incident |

## 8. ⚠️ Zwei strukturelle Risiken (nicht wegmoderiert)

1. **Port-Kollision wandert mit, wenn CI nicht hermetisch ist.** Staging hat 29
   Container mit Port-Bindings. Ein CI-Job mit `runserver 0.0.0.0:8090` kollidiert
   hier genauso — nur **ohne Prod-Blast-Radius**. Alt E entschärft die *Prod*-Gefahr;
   die hermetische Job-Form (ADR-222/KONZ-004 Ebene A) bleibt **Voraussetzung**.
2. **Ressourcen-Verdrängung.** 16 Kerne, aber 29 Stacks + bis ~18 parallele CI-Läufe.
   ADR-257 Alt E gilt nur „sofern CI die Staging-Stacks nicht verdrängt" → §5
   Resource-Limits + §6 Hygiene-Check als Frühwarnung; bei Sättigung eigener Host.

## 9. Migrations-Reihenfolge (Pilot zuerst)

1. **Pilot: `travel-beat`** (der 2026-06-27-Geschädigte) — Staging-Runner +
   `ci-nonprod`-Label, hermetische Job-Form verifizieren, eine echte CI-Runde grün.
2. Hygiene-Check + Label-Gate scharf schalten.
3. Restliche ≥9 Hubs gestaffelt via ADR-222-Familie.
4. `prod-server` für CI deprecaten (nur Deploy bleibt, ADR-156).

## Referenzen
- **ADR-257** — CI-Host-Isolation (Placement-Achse; dieses Runbook = REC-5/REC-7-Folge-Artefakt).
- **ADR-222** — geteilte CI-Workflow-Familien (Workflow-Achse, hermetische Job-Form).
- **ADR-156** — Deployment-Pipeline (Deploy bleibt legitim auf `prod-server`).
- **`infra/hosts.yaml`** — Runner-/Host-SSoT (Eintragungsort des neuen Runners).
- **`*/.github/workflows/runner-label-check.yml`** — Label-Gate (`ALLOWED_EXTRA`-Hook).
- Ground-Truth-Belege 2026-06-28 in-session verifiziert (server_probe, ssh df/free/docker ps, gh api runners).
