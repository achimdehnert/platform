# Deployment & Infra-Security Fleet-Audit — 2026-07-04

> **Scope:** Alle 63 Git-Repos unter `~/github` (Orgs achimdehnert + iilgmbh), Fokus
> **CI/CD-Workflows, Docker/Compose, Deploy-Pfade, Secrets-Handling**.
> **Ziel:** Standards so oft wie möglich, Individual-Lösungen nur wo nötig.
> **Methode:** Fleet-weite greps (Evidenz mit `datei:zeile`), Advocatus-Diaboli-Pass, OOTB-Vorschläge.
> **Nicht verifiziert (kein Server-Zugriff in dieser Session):** Host-Firewall, laufende
> Container, SSL-Ablauf, GitHub-Environment-Protection-Rules. Billigste Checks je Befund benannt.
> **Inbox-Intake:** 7 Dateien gesichtet, nur deployment-relevante FPs übernommen (FP-3 staging
> health-URL, FP-6 continue-on-error, klickdummy FP-6/7 mutable refs / concurrency, platform FP-6
> Owner-Registry). Inbox-Dateien **nicht** umbenannt — sie enthalten weitere, hier nicht
> verarbeitete Nicht-Deployment-Findings (XSS/RCE in iil-klickdummy!) für den nächsten Voll-Audit.

## Executive Summary

- **Repos auditiert:** 63 (davon 27 mit `docker-compose.prod.yml`, 37 mit deploy/cd-Workflow, 15+ PyPI-Publisher)
- **Findings:** 3 Critical · 5 High · 9 Medium
- **Kernbild:** Die Flotte hat einen guten Standard (`_deploy-unified` via Reusable Workflows,
  27/27 Prod-Compose überwiegend localhost-gebunden, 0 getrackte Key-Dateien) — aber er existiert
  **zweimal** (shared-ci vs. platform), in **8 Versionsständen**, und ~10 Repos fahren daran vorbei.
  Das größte Einzelrisiko ist eine **git-getrackte Prod-Env-Datei in bfagent**.

---

## 1. Critical

### C1 · bfagent: Prod-Secrets git-getrackt 🔴 *(Update: Repo archiviert)*
- **Evidenz:** `bfagent/deployment/.env.production.local` ist in git (`git ls-files`), 25 Zeilen,
  `DEBUG=False`, Keys u.a. `SECRET_KEY`, `POSTGRES_PASSWORD`, `CLAUDE_API_KEY`,
  `GITHUB_ACCESS_TOKEN`, `TOGETHER_API_KEY`, `BRAVE_API_KEY` — alle mit Wert belegt
  (8 Werte >20 Zeichen, **0 Platzhalter-Muster**). Zusätzlich getrackt: `config/settings/.env.utf8`
  (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `POSTGRES_PASSWORD`).
- **Update aus Umsetzung (17:58):** `achimdehnert/bfagent` ist auf GitHub **archiviert**
  (seit 2026-06-03, read-only, PRIVATE; kein iilgmbh-Nachfolger) — ein Untrack-PR ist unmöglich.
  Lokaler Branch `chore/rueckbau-bfagent` bestätigt Rückbau-Kontext.
- **Verifiziert:** Datei getrackt, Keys nicht-leer, Repo archiviert+privat. **Nicht verifiziert:**
  ob Werte noch aktiv (billigster Check: einen Key gegen die API testen).
- **Fix (reduziert, aber nicht erledigt):** Die Keys leben in der History eines privaten Archivs
  und in jedem Clone → **alle rotieren** (v.a. `GITHUB_ACCESS_TOKEN`, `CLAUDE_API_KEY`); wenn
  bfagent-Dienste noch laufen, Server-seitige `.env` prüfen. Kein PR möglich; Rotation = User.
- **✅ ERLEDIGT (User-Bestätigung 2026-07-04):** „bfagent creds. sind veraltet und bereits
  rotiert" — C1 geschlossen. Restnotiz: Aktivitäts-Test der alten Werte wurde vom
  Permission-Classifier verweigert (Credential-Probing); Rotation macht ihn obsolet.

### C2 · learn-hub: Postgres öffentlich exponiert in Prod-Compose 🔴
- **Evidenz:** `learn-hub/docker-compose.prod.yml` — Service `db`: `ports: - "5499:5432"`
  (ohne `127.0.0.1:`-Präfix → bindet 0.0.0.0). **Einziges** von 27 Prod-Compose mit offenem DB-Port;
  alle anderen Repos binden localhost-only.
- **Nicht verifiziert:** ob Hetzner-Firewall/ufw den Port blockt. Billigster Check:
  `ss -tlnp | grep 5499` auf dem Host bzw. `nmap -p 5499 <host>` von außen.
- **Fix:** `127.0.0.1:5499:5432` — Einzeiler, kein Grund für Individuallösung.

### C3 · odoo-hub: Prod-IP hartkodiert + ungeschützter Inline-CD 🔴
- **Evidenz:** `odoo-hub/.github/workflows/cd-production.yml` — `host: 46.225.127.211` im Klartext,
  kein `permissions:`-Block; `docker compose pull && up -d --force-recreate` per SSH.
  Dazu `docker-compose.prod.yml`: `/var/run/docker.sock:...:ro` an Traefik, obwohl ein
  `docker/socket-proxy/Dockerfile` im Repo existiert und ungenutzt bleibt.
- **Kontext:** Passt zu NL2X-Audit-Gate G2 (odoo-hub = Prod mit bekanntem NL2SQL-RW-Fallback) —
  derselbe Host, dieselbe Blast-Radius.
- **Fix:** IP → `secrets.DEPLOY_HOST`; `permissions: contents: read`; Traefik hinter den
  vorhandenen socket-proxy klemmen (`providers.docker.endpoint=tcp://socket-proxy:2375`).

## 2. High

### H1 · Zwei Reusable-Workflow-Universen (Supply-Chain-Risiko) 🔴/H
- **Evidenz:** `iilgmbh/shared-ci` und `achimdehnert/platform/.github/workflows/` enthalten
  **beide** `_deploy-unified.yml`, `_ci-python.yml`, `_build-docker.yml` … — `diff` beweist Drift:
  shared-ci hat die GHCR-Token-Fixes (shared-ci#10 Facette A+B: kurzlebiger `GITHUB_TOKEN` statt
  Host-Datei `/opt/scripts/.ghcr_token`, opt-in `PROJECT_PAT`), platform **nicht**.
- **Konsumenten des stale Universums, alle ungepinnt `@main`** *(korrigiert nach
  origin/main-Verifikation — die lokale Erst-Zählung enthielt 2 stale Clones, s. M10)*:
  apo-hub, decks-hub, risk-hub, promptfw, outlinefw (+ frist-hub, SHA-gepinnt — sauber;
  + bfagent, aber archiviert). **billing-hub und dms-hub waren auf origin/main bereits migriert**
  (shared-ci v1.0.5 bzw. v1.0.2) — nur die lokalen Checkouts (46 bzw. 230 Commits behind) zeigten
  noch platform@main; sie wandern damit in den H2-Topf (Versions-Spread).
- **Advocatus Diaboli:** `@main` heißt: **jeder Commit auf platform/main kann sofort 8 Prod-Deploys
  verändern**, ohne Review im Konsumenten-Repo — das ist der eigentliche Supply-Chain-Hebel der
  Flotte, gefährlicher als jedes einzelne Compose-File. Und: die Fixes aus shared-ci#10 fehlen dort,
  d.h. diese 8 Repos hängen vermutlich noch am manuell gepflegten Host-GHCR-Token.
- **Fix:** platform-Kopien archivieren (Redirect-Stub mit `fail` + Hinweis), alle 8 Konsumenten auf
  `iilgmbh/shared-ci@v1.0.8` migrieren. Eine PR pro Repo, mechanisch.

### H2 · shared-ci-Versions-Spread v1.0.1–v1.0.8 über 18 Repos
- **Evidenz (Auszug):** pptx-hub ci=v1.0.1/deploy=v1.0.8 (im selben Repo!), learn-hub v1.0.2+v1.0.6,
  recruiting-hub/tax-hub/travel-beat v1.0.2, wedding-hub/cad-hub v1.0.5, research-hub v1.0.8.
- **Konsequenz:** Repos auf ≤v1.0.5 fahren ohne die GHCR-Fixes; Fehlerbilder differieren pro Repo →
  genau die Sorte Drift, die Debugging-Sessions kostet (vgl. 🌀 GHCR-Fehlzuordnungs-Retro 2026-06-22).
- **Fix:** Renovate/Dependabot-Regel für `uses:`-Refs (Renovate kann das nativ: `github-actions`
  manager) + ein Fleet-Check in platform (analog `pypi-fleet-health.yml`): „alle shared-ci-Refs auf
  aktueller Minor?" — Abdeckung heute: **11× dependabot, 2× renovate, 51 Repos ohne**.

### H3 · PyPI-Publish per Legacy-Token statt Trusted Publishing (OIDC)
- **Evidenz:** ~15 publish.yml (aifw, promptfw, testkit, learnfw, outlinefw, researchfw, weltenfw,
  iil-*, …) mit `password: ${{ secrets.PYPI_API_TOKEN }}`; **kein** `permissions: id-token: write` →
  kein OIDC. 22 deploy/publish/cd-Workflows ganz ohne `permissions:`-Block.
- **Advocatus Diaboli:** Ist `PYPI_API_TOKEN` ein Org-Secret? Dann publisht **ein** geleaktes Token
  **alle** iil-Pakete — Supply-Chain in die eigene Flotte (alle Hubs installieren diese Pakete).
- **Fix:** PyPI Trusted Publisher pro Paket (5 Min/Repo, kein Secret mehr), Template einmal in
  shared-ci als `_publish-pypi.yml` gießen → Individuallösung ade. Deckt auch Inbox-FP-6
  (klickdummy: mutable refs im OIDC-Publish) ab: im Template Actions SHA-pinnen.

### H4 · ttz-hub (Government): Build-on-Server ohne Artefakt und Rollback
- **Evidenz:** `ttz-hub/.github/workflows/deploy.yml` — `git pull origin main` +
  `docker compose build` **auf dem Prod-Host**, `sleep 30` + curl als Health-Gate, kein
  `permissions:`, kein Image-Artefakt → kein definierter Rollback (`/rollback`-Skill greift ins Leere).
- **Advocatus Diaboli — ist das eine gerechtfertigte Individuallösung?** Teilweise: Wenn
  Data-Sovereignty GHCR (US-Cloud) ausschließt, ist Build-on-Server eine legitime Entscheidung —
  aber dann gehört sie in ein ADR und der Build gehört reproduzierbar gemacht (digest-getaggte
  lokale Images, `docker tag` vor `up` als Rollback-Punkt). Heute ist es kein Standard **und** kein
  dokumentierter Sonderweg, sondern einfach gewachsen. → ttz-hub/CLAUDE.md bzw. Sovereignty-Regeln
  prüfen und Entscheidung als ADR festhalten (Gate analog NL2X-G1).

### H5 · Default-Passwort-Fallbacks in Prod-/Staging-Compose
- **Evidenz:** `mcp-hub/docker-compose.prod.yml:27` `${POSTGRES_PASSWORD:-change-me-in-production}`;
  `research-hub/docker-compose.prod.yml:10` `${DB_PASSWORD:-research_hub}`;
  `mcp-hub/docker-compose.llm-mcp.yml:61-84` Grafana `changeme`-Fallbacks;
  committete Staging-Passwörter: `coach-hub/docker-compose.staging.yml:83`,
  `billing-hub/docker-compose.staging.yml:62`.
- **Warum das brennt:** `:-fallback` heißt: fehlt die Env-Var (typischer Deploy-Fehler), startet der
  Stack **stumm mit dem Default** statt zu failen.
- **Fix (Standard):** überall `${VAR:?VAR fehlt}` statt `${VAR:-default}` in prod/staging-Compose.
  Ein `deploy-config-lint`-Check (existiert schon in shared-ci!) kann das erzwingen: Regel
  „kein `:-` bei `*PASSWORD*|*SECRET*|*KEY*` in `docker-compose.{prod,staging}.yml`".

## 3. Medium

| # | Befund | Evidenz | Fix |
|---|---|---|---|
| M1 | SSH-Secret-Namensschisma: 5 Schemata (`DEPLOY_HOST`/`HETZNER_HOST`/`SSH_HOST`/`STAGING_HOST`; `HETZNER_SSH_KEY`/`DEPLOY_SSH_KEY`/`SSH_PRIVATE_KEY`/`DEPLOY_KEY`/`GENERATORS_DEPLOY_KEY`) | grep über alle Workflows (20/19/19/17/11/10/4/2/2/1 Vorkommen) | Ein Standard (`DEPLOY_HOST/USER/SSH_KEY` + `STAGING_*`), Org-Secrets statt Repo-Kopien, Migration beim nächsten Touch |
| M2 | 14 von 37 deploy/cd-Workflows ohne `concurrency:` → parallele Deploys desselben Repos möglich | Zähl-Scan; `_deploy-unified.yml` hat concurrency (2×), Inline-Deploys nicht | `concurrency: deploy-${{ github.ref }}` in alle Inline-Deploys; deckt Inbox-FP-7 |
| M3 | `aquasecurity/trivy-action@master` (mutable third-party ref) | `shared-ci/_build-docker.yml:116`, `platform/_build-docker.yml:116`, `travel-beat/security.yml:17` | SHA-Pin; generell: third-party Actions in shared-ci SHA-pinnen |
| M4 | Secret-Scan nur in 12/63 Repos (gitleaks/trufflehog) | grep-Liste: apo-hub, design-hub, frist-hub, gaeb-toolkit, iil-fieldprefill, illustration-fw, mcp-hub, nl2iot-hub, platform, pptx-hub, shared-ci, travel-beat | `secret-scan` als Job in `_ci-python.yml`/`_ci-pypi.yml` aufnehmen → automatische Fleet-Abdeckung statt 51 Einzel-Rollouts |
| M5 | Offene App-Ports ohne localhost-Bindung: recruiting-hub `8103:8103`, tax-hub `8104:8000` | jeweils `docker-compose.prod.yml` | `127.0.0.1:`-Präfix (nginx-Upstream braucht kein 0.0.0.0); odoo-hub `80/443` ist ok (Traefik als Edge) |
| M6 | iil-relaunch existiert doppelt (`iil-relaunch` + `iilgmbh-iil-relaunch`), beide mit eigenem rsync/git-pull-Deploy ohne `permissions:` | Workflow-Inventar; passt zu Inbox-FP-2 (Org-Repointing-Leichen) | Kanonisches Repo bestimmen, Zwilling archivieren |
| M7 | 4 Prod-Hosts im Umlauf (88.198.191.108, 88.99.38.75 staging, 46.225.127.211 odoo, 178.104.184.168 molkerei), Host-Wissen verstreut in Secrets/Workflows/Memories | IP-grep; `infra-hosts-audit.yml` existiert in platform (Abdeckung nicht verifiziert — billigster Check: dessen letzten Run lesen) | Host-Inventar als SSoT in platform (`infra/hosts.yml`) inkl. Zweck, Firewall-Stand, Owner |
| M8 | Action-Versions-Spread: checkout v4 (233×) vs v6 (163×), setup-python v5/v6, download-artifact v4/v8 | grep-Zählung | folgt aus H2-Fix (Renovate), kein Einzel-Task |
| M9 | `platform-pinned/` — voller lokaler Zweit-Klon von platform im Repo-Root | `ls`, eigener `.git` | Zweck klären; wenn Experiment → löschen (verfälscht Fleet-greps, tauchte in 3 Scans als Phantom auf) |
| M10 | **Lokale Checkouts driften massiv hinter origin** — Audits/greps auf `~/github` können fehlleiten: billing-hub 46, dms-hub 230 Commits behind; 2 von 8 H1-Erstbefunden dadurch falsch-positiv | `git rev-list --count main..origin/main`; Korrektur in H1 dokumentiert | Vor jedem Fleet-Audit `/sync-repo`-Pass (oder Audit-Skript grept `origin/main` statt Worktree); bfagent-artige Archiv-Repos lokal als solche markieren |

**Ausdrücklich sauber (Positiv-Evidenz):** 0 getrackte `.pem/.key/id_rsa`-Dateien fleet-weit ·
24/27 Prod-Compose vollständig localhost-gebunden · 18 Repos konsolidiert auf `_deploy-unified` ·
ttz-hub/odoo-hub/bahn-hub nutzen `environment: production` (Protection-Rules nicht verifiziert —
billigster Check: `gh api repos/{org}/{repo}/environments/production`).

## 4. Cross-Repo-Patterns → Standard vs. Individual

| Pattern | Repos | Urteil |
|---|---|---|
| `_deploy-unified` via shared-ci | 18 | ✅ **Der Standard.** Einziges Problem: Versions-Spread (H2) |
| `_deploy-unified` via platform@main | 8 | ❌ Stale Fork, ungepinnt → migrieren (H1) |
| Inline SSH-Deploy (appleboy/ssh-action) | ttz-hub, bahn-hub, odoo-hub, nl2cad, decks-hub | ❌ außer ttz-hub (→ ADR) und odoo-hub (eigener Host/Traefik-Stack — Individual ok, aber C3 fixen) |
| git-pull+rsync-Deploy | iil-relaunch ×2, molkerei (scp, per Memory) | 🟡 Für statische Sites vertretbar — aber 1× reicht (M6); molkerei bewusst außerhalb |
| Traefik als Edge | odoo-hub | 🟡 Individual gerechtfertigt (eigener Host, ACME, Odoo-Multi-Service) — als dokumentierte Ausnahme führen |
| PyPI-Publish inline+Token | 15 Repos | ❌ → `_publish-pypi.yml` in shared-ci + OIDC (H3) |

## 5. Advocatus Diaboli — die unbequemen Fragen

1. **„Standardisierung" ist hier nicht das Problem — Governance ist es.** Der Standard existiert
   (shared-ci) und ist gut. Es fehlt der **Zwang**: nichts hindert Repo Nr. 64, wieder einen
   Inline-Deploy zu bauen. Vorschlag: `validate-workflows.yml`/`deploy-config-lint` von „Linter in
   platform" zu **required check org-weit** machen (GitHub Rulesets auf Org-Ebene, nicht pro Repo).
2. **Version-Pinning-Spread ist auch ein Feature.** Big-Bang „alle auf v1.0.8" bündelt das Risiko:
   ein Fehler in v1.0.8 trifft dann 26 Repos gleichzeitig. Besser: Renovate-PRs pro Repo mit CI-Gate
   — gestaffelt, aber automatisch. Nicht von Hand nachziehen.
3. **Ein Host trägt fast alles.** ~20 Apps auf 88.198.191.108 — Disk-full, Kernel-Update oder
   Kompromittierung eines Containers betrifft die gesamte Flotte. Es gibt kein sichtbares
   DR-/Restore-Konzept auf Fleet-Ebene (db-backup.yml existiert in infra-deploy — Konsumenten und
   letzter erfolgreicher Restore-Test nicht verifiziert; billigster Check: Runs von
   `infra-deploy/db-backup.yml` + einmal echtes Restore üben). „Backups ohne Restore-Test sind
   Hoffnung, keine Strategie."
4. **infra-deploy vs. shared-ci = drittes Universum?** infra-deploy hält eigene
   deploy-service/rollback/migrate-Workflows; im `uses:`-Scan hat es **keine** Konsumenten.
   Entweder es ist das Ops-Cockpit (workflow_dispatch) — dann dokumentieren — oder es ist tot →
   archivieren. Nicht verifiziert: dispatch-Nutzung (billigster Check: `gh run list -R
   iilgmbh/infra-deploy -L 10`).
5. **Wer deployt eigentlich?** `@main`-Refs + fehlende permissions-Blöcke bedeuten: Schreibrecht auf
   platform ≈ Deploy-Recht auf 8 Prod-Apps. Das kollidiert direkt mit dem Gate
   `autonomous-no-human-review` aus den House Rules.

## 6. Out-of-the-Box

1. **Pull-basiertes GitOps statt 37 Push-SSH-Workflows:** Ein Agent auf dem Host (z.B. Komodo/
   Watchtower-Klasse) zieht GHCR-Images **by digest** aus einem `deploy-manifest` im platform-Repo.
   Effekt: SSH-Keys verschwinden aus GitHub komplett, Rollback = Manifest-Revert, Audit-Trail = git.
   (Gegenargument: neues Moving Part + eigener Failure-Mode; erst pilotieren, z.B. mit learn-hub.)
2. **Deploy-Fleet-Health-Meter:** platform hat bereits `pypi-fleet-health.yml` + diverse Meter.
   Gleiches Muster für Deploys: wöchentlicher grep-Job, der genau die Metriken dieses Audits trackt
   (Universum-Refs, Versions-Spread, permissions-Blöcke, `:-`-Fallbacks, offene Ports) und bei
   Regression ein Issue aufmacht. Dieses Audit ist dann nie wieder Handarbeit.
3. **SSH ganz abschaffen (mittel-/langfristig):** Tailscale/Headscale-Mesh mit ACLs pro Repo-Runner
   oder GitHub-OIDC→kurzlebige SSH-Zertifikate (z.B. via step-ca). Der 5-Schemata-Secret-Zoo (M1)
   löst sich dann strukturell, nicht kosmetisch.
4. **Sovereignty-Profil als shared-ci-Input statt Fork:** `_deploy-unified.yml` bekommt
   `profile: sovereign` (Build-on-Server oder lokale Registry, keine US-Registry) — dann fährt
   **auch ttz-hub** den Standard, und die Ausnahme ist ein Parameter statt eines eigenen Workflows.

## 7. Roadmap (priorisiert)

**Kurzfristig (diese Woche):**
1. C1 bfagent Secrets rotieren + Datei entgittern (History-Rewrite = User-Gate)
2. C2 learn-hub `127.0.0.1:5499` (+ M5 recruiting/tax) — 3 Einzeiler-PRs
3. C3 odoo-hub IP→Secret + permissions-Block
4. H1 die 8 platform@main-Konsumenten auf shared-ci@v1.0.8 (mechanisch, 8 PRs)

**Mittelfristig (2 Wochen):**
5. H3 `_publish-pypi.yml` (OIDC, SHA-pinned) in shared-ci + 15 Repos umstellen
6. H5+M2 deploy-config-lint-Regeln: kein `:-` bei Secrets, `concurrency` Pflicht, `permissions` Pflicht
7. M4 secret-scan in `_ci-python.yml`/`_ci-pypi.yml` einbauen (1 Change → 51 Repos abgedeckt)
8. H2 Renovate org-weit für `uses:`-Refs
9. H4 ttz-hub-Deploy-ADR (Sovereignty-Profil, OOTB-4)

**Langfristig (Backlog):**
10. Org-Rulesets: deploy-config-lint als required check
11. Host-Inventar-SSoT + Restore-Test-Übung (AD-3)
12. GitOps-Pull-Pilot (OOTB-1) · infra-deploy-Schicksal klären (AD-4)

## 8. Metriken (Baseline für Folge-Audits)

| Metrik | Jetzt | Ziel |
|---|---|---|
| Deploy-Konsumenten shared-ci (gepinnt) | 18 (v1.0.1–v1.0.8) | 26, eine Version |
| Konsumenten platform@main (stale/ungepinnt) | 5 aktiv auf origin/main (apo, decks, risk, promptfw, outlinefw) | 0 |
| deploy/publish/cd-Workflows ohne `permissions:` | 22 | 0 |
| deploy/cd ohne `concurrency:` | 14/37 | 0 |
| PyPI-Publish mit Legacy-Token | ~15 | 0 (OIDC) |
| Prod-Compose mit offenem Nicht-Edge-Port | 3 (learn, recruiting, tax) | 0 |
| Secret-Default-Fallbacks (`:-`) in prod/staging | ≥7 Stellen | 0 |
| Repos mit Secret-Scan | 12/63 | 63/63 (via shared-ci) |
| Repos mit Renovate/Dependabot | 13/63 | 63/63 |
| Git-getrackte Env-Dateien mit Secrets | 1 (bfagent) | 0 |

## 9. Umsetzung 2026-07-04 (Kurzfrist-Scope, alle als PR — kein Merge ohne Freigabe)

| PR | Finding | Inhalt |
|---|---|---|
| learn-hub#24 | C2 | Postgres 5499 → 127.0.0.1 |
| recruiting-hub#11 | M5 | Port 8103 → 127.0.0.1 |
| tax-hub#31 | M5 | Port 8104 → 127.0.0.1 |
| odoo-hub#14 | C3 | toten `cd-production.yml` gelöscht (0 Runs, Secrets existieren nicht, IP hardcoded) |
| apo-hub#38 · decks-hub#2 · risk-hub#380 · promptfw#25 | H1 | platform@main → shared-ci@v1.0.8 |
| outlinefw#17 | H1 | SHA-Pin auf platform (Migration blockiert: `mypy_blocking` fehlt in shared-ci) |

**Nicht umgesetzt / User-Gates:** billing/dms-Migration obsolet (schon migriert) ·
verbleibende Mittelfrist-Items: OIDC-PyPI (PyPI-seitige Konfig = User), deploy-config-lint-Regeln
(Design-Issue: Lint-Script lebt in platform, shared-ci checkt es cross-repo aus), Renovate org-weit.

**Neu entdeckt während Umsetzung:** odoo-hub cd-production war toter Code (0 Runs) ·
risk-hub hat 17 offene Dependabot-Alerts (6 high) · bfagent archiviert ohne Nachfolger ·
`mypy_blocking`/`enable_bandit` existieren nur in platform, nicht in shared-ci → platform ist
nicht rein stale, ein Feature-Port nach shared-ci (v1.0.9) ist Voraussetzung für outlinefw/iil-adrfw.

### Nachtrag Umsetzungs-Runde 2 (2026-07-04 abends, nach Freigaben)

- **Merges:** learn#24, recruiting#11, tax#31, apo#38, odoo#14, promptfw#25, outlinefw#17,
  shared-ci#18 ✅; risk-hub#380 wartet auf letzten Check; decks#2 s.u.
- **C1 geschlossen:** bfagent-Keys laut User veraltet + bereits rotiert.
- **shared-ci v1.0.9 getaggt** (mypy_blocking/enable_bandit-Port + generischer iil-Dep-Repair),
  **vorher im Zielkontext validiert**: outlinefw-CI grün inkl. „Type Check (mypy, blocking)".
  M4-Korrektur: gitleaks ist seit v1.0.1 Teil von `_ci-python` — Secret-Scan-Lücke betrifft nur
  Repos ohne shared-ci-CI.
- **Incident odoo (aufgelöst, ~18:30–19:00):** Auto-Deploy nach odoo#14-Merge failte am
  Health-Check; Origin war durchgehend gesund (direkt 200), der Cloudflare→Origin-Pfad war
  temporär tot; danach wieder 200. Backlog: Deploy-Trigger ohne Path-Filter (jeder main-Push
  deployt) + Health-Check läuft nur über CDN-Pfad.
- **Regression durch H1-Migration (behoben):** apo-hub Deploy-Leg failte — `secrets: inherit`
  reicht **required**-Secrets nicht über die Org-Grenze achimdehnert→iilgmbh
  (Run 28715627300; Muster wie risk-hub/ADR-236). Fix: explizites Mapping, apo-hub#39
  (gemerged), decks-hub#2 präventiv gehärtet. **Lehre für alle künftigen Migrationen
  achimdehnert→iilgmbh: Secret-Mapping explizit, nie inherit bei required-Secrets.**
- **decks-hub: Branch-Protection unerfüllbar (Vorbestand):** Required-Context „CI" vs.
  Check-Name „Build deck (static)" → jeder PR BLOCKED. Gate-freier Fix im PR #2
  (Job-Rename), kein `--admin`-Bypass.

---
*Generated by /platform-audit (Fokus Deployment/Infra-Security) — 2026-07-04*
