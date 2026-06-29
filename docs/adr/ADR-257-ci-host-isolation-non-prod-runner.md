---
status: accepted
date: 2026-06-26
revision: 3
decision-makers: [Achim Dehnert]
scope: platform
implementation_status: in-progress
related: [ADR-222, ADR-156, KONZ-risk-hub-004]
supersedes: []
---

# ADR-257: CI läuft nicht auf dem Produktions-Host — dedizierter Non-Prod-Runner

> **Kurz:** Der einzige self-hosted-Runner `prod-server` liegt **auf dem Prod-Host**
> (88.198.191.108) und wird von mehreren Hubs geteilt. CI-Jobs teilen damit die
> Docker-Engine, Ports und CPU mit *allen* Prod-Containern. Entscheidung: CI-Workloads
> auf einen **dedizierten Non-Prod-Runner** verlagern; `prod-server` für CI deprecaten.
> Das *Wie* der geteilten Workflows bleibt **ADR-222** (SHA-gepinnte Familien) — dieser
> ADR entscheidet nur das **Wo** (Runner-Placement), die von ADR-222 nicht abgedeckte Achse.

## Status

`accepted` (2026-06-28, Achim Dehnert). Frische Empirie aus der travel-beat-Session
2026-06-27/28 bestätigte die Prämisse: CI-Image-Churn auf der geteilten Prod-Disk
killte einen travel-beat-Deploy (apt `No space left`), und ein gleichzeitiger
risk-hub-CI-Job auf demselben `prod-server`-Runner belegte den Host (E-2/E-3 live
beobachtet). Umsetzung läuft (`implementation_status: in-progress`): Runner-Runbook
materialisiert (`infra/host-maintenance/runner-nonprod-runbook.md`), Pilot = travel-beat.

> **Mechanik-Befund 2026-06-28 (verifiziert):** Die shared-ci-Workflows
> (`_ci-python.yml`, `_deploy-unified.yml`) haben **bereits** einen `runs_on`-Input
> (default `self-hosted`) und `_deploy-unified.yml` ein separates `deploy_runs_on` —
> der Build→non-prod / Deploy→prod-Carve-out ist also pro Repo per Input steuerbar,
> **ohne** shared-ci zu ändern. Das ist der Migrationshebel je Repo.

> **Rev 2 (2026-06-26):** Externe Zweitmeinung (`/adr-handoff-extern`, Cross-Provider)
> eingearbeitet — 12 Befunde, alle `[valid]` nach Rückfluss-Gate. Wesentliche Schärfungen:
> Label-Enforcement via Erweiterung des bestehenden `runner-label-check` (REC-2/3), Staging-Host
> als billigste konkrete Runner-Realisierung (REC-9), expliziter Prod-Carve-out (REC-4),
> Kill-Gate-Aktuator + Folge-Artefakte (REC-7/8/10).

## Kontext

**Auslöser (KONZ-risk-hub-004, alle Belege 2026-06-26 in-session verifiziert):**

- **E-1 (gh api + `platform/infra/hosts.yaml`):** Der einzige self-hosted-Runner ist
  `prod-server`, installiert **auf dem Prod-Host** 88.198.191.108. `runs-on: self-hosted`
  hat kein anderes Ziel. Der Staging-Host (88.99.38.75) hat **keinen** Runner.
- **E-2 (gh api je Repo):** `prod-server` wird von ≥9 Hubs geteilt (billing-, cad-, coach-,
  trading-, travel-beat-, welten-, wedding-, pptx-, dev-hub). Es ist kein Einzel-Repo-Problem.
- **E-3 (`ssh … docker/ss`):** Auf dem Prod-Host hält der **Live-Container `risk_hub_web`**
  Port `127.0.0.1:8090`. Der risk-hub-CI-Job rief `runserver 0.0.0.0:8090` → **kann nie
  binden, solange Prod läuft**. Zusätzlich liefen **2 verwaiste `runserver`-Prozesse** auf
  dem Prod-Host (nie beendeter `&`-Job). CI kontendiert real um **Live-Prod-Ports**.
- **E-4 (`hosts.yaml`):** Der Prod-Host ist ein Multi-Hub-Host (eine Docker-Engine für ALLE
  Prod-Container). Der Outage 2026-06-15 war eine docker-compose-Projekt-Kollision auf genau
  diesem Host — die „CI teilt Engine mit Prod"-Klasse hat **bereits** Downtime verursacht.

**Abgrenzung zu ADR-222:** ADR-222 (v4) entscheidet *zwei SHA-gepinnte CI-Workflow-Familien*
für die 48 Repos — die **Workflow**-Achse. Es trifft **keine** Aussage zum **Runner-Placement**.
Diese Lücke ist die Achse dieses ADR. Der geteilte hermetische `workflow_call` (Job-Form ohne
Host-Port-Bindung) gehört in ADR-222s Familien — dieser ADR fügt dort *keine* zweite Wahrheit hinzu.

## Entscheidung

1. **CI/Test-Workloads laufen nicht mehr auf dem Prod-Host.** Ein **dedizierter Non-Prod-Runner**
   übernimmt sie. „Dediziert" heißt präzise (REC-1 ← AD-2): **nur CI/Test**, und auf dessen
   Docker-Engine läuft **kein produktiver App-Container** — der geteilte-Engine-Blast-Radius ist
   genau das, was dieser ADR schließt; ein Runner neben Prod-Containern reproduziert ihn.
2. **Prod-Host-Carve-out, explizit (REC-4 ← AD-5):** Auf `prod-server` dürfen **ausschließlich
   Deploy-Schritte nach ADR-156** laufen — **keine** Tests, Builds, `runserver`-/Service-Starts.
   `prod-server` wird für CI/Test **deprecated**.
3. **Technische Durchsetzung per Label + Gate (REC-2/REC-3 ← AD-3/M28-2):** Eine Entscheidung ohne
   Enforcement bleibt eine Fehlkonfiguration entfernt. Daher: CI/Test-Jobs tragen ein eigenes Label
   (`ci-nonprod`), Deploy-Jobs `deploy-prod`; **plain `runs-on: self-hosted` für CI/Test ist
   verboten**. Erzwungen durch **Erweiterung des bestehenden `runner-label-check.yml`** (validiert
   `runs-on` bereits gegen `hosts.yaml`, hat den `ALLOWED_EXTRA`-Hook) — **kein neues Gate**, der
   Check wird rot, wenn ein CI/Test-Job `prod-server`/plain-`self-hosted` zielt.
4. **Ehrliche Benennung (REC-11-bestätigt):** Der neue Runner ist zunächst ein **dediziertes „Pet"**,
   kein ephemerer Runner — es existiert **keine** Provisioning-Automation (ARC/Terraform). „Ephemeral"
   wird *nicht* behauptet, bis Automation steht. Evolutionspfad in §Folge-Artefakte (REC-10).
5. **Mindest-Betriebsregeln des Runners (REC-5 ← AD-1):** Patch-Verantwortung, **kein `user:0:0`**,
   begrenzter Docker-Socket-/Secret-Scope, Disk/CPU-Monitoring + Cleanup — ausformuliert in einem
   **Runbook** (§Folge-Artefakte), nicht hier; Präzedenz: Runner-Pollution-Fix (kein root, tmpfs-STATIC_ROOT).
6. **`hosts.yaml` bleibt Runner-SSoT.** Neuer Runner + `prod-server`-CI-Deprecation dort eintragen.
7. **Hermetische Job-Form** (run-eindeutige Ports / keine Host-Port-Bindung / garantierter Teardown,
   = KONZ-004 Ebene A, bereits gemergt) wird als ADR-222-Familien-Baustein **per SHA referenziert**, nicht kopiert.
8. **Mess-Gate statt Behauptung:** Ein scheduled, read-only **Runner-Hygiene-Check** misst je Runner
   Host-Port-Bindungen + verwaiste CI-Prozesse **und** Ressourcendruck (Disk/Volumes, alte Workspaces,
   CPU/RAM, offene Ports, Docker-Socket-Nutzung — REC-6 ← AD-4); rot bei Verstoß (speist das Kill-Gate).

## Konsequenzen

**Positiv:**
- Die „CI teilt Engine/Ports mit Prod"-Klasse (Outage-Präzedenz 2026-06-15, E-4) ist geschlossen —
  ein CI-OOM/Disk-/Port-Event kann keine Prod-Hubs mehr treffen.
- Ein grüner CI-Lauf bedeutet „Code gut", nicht „Runner war zufällig sauber".
- Über die ≥9 Hubs gehebelt (E-2), da via ADR-222-Familie verteilt.

**Negativ / Kosten (ehrlich):**
- **Ein neuer Host** zum Patchen/Monitoren/Bezahlen. Ohne Provisioning-Automation droht
  Pet-Drift (derselbe Verfall, den er heilen soll) — daher das Mess-Gate + Kill-Gate.
- Migrationsaufwand je Hub (Runner-Registrierung, Label, Secrets).

## Alternativen

- **A: Status quo + nur Symptom-Fixes** (Ports freigeben, Prozesse killen). Verworfen — lässt
  Blast-Radius-Klasse intakt; Outage-Präzedenz bleibt.
- **B: Nur hermetische Jobs auf dem Prod-Host** (= KONZ-004 Ebene A allein). Notwendig, aber
  **nicht hinreichend**: CI-Code teilt weiter die Prod-Engine. Ist der Interim, nicht das Ziel.
- **C: Voll-ephemere ARC-Runner (Kubernetes).** Über-Engineering für die heutige Lage; kein
  Cluster/Provisioning vorhanden. Möglicher *späterer* Pfad, sobald Automation existiert.
- **E: Runner auf dem bestehenden Staging-Host (REC-9 ← AD-6).** Der Staging-Host (88.99.38.75,
  32 GB) **existiert bereits** und hat heute keinen Runner — ihn als CI/Test-Runner-Ziel zu nutzen
  ist die **billigste** Realisierung von D (kein neuer Host zu bezahlen/patchen). Bedingung: Er trägt
  **keine Prod-Container** (Bedingung aus Entscheidung 1 gilt) und seine Staging-Container teilen die
  Engine bewusst mit CI — akzeptabel, weil non-prod. **Bevorzugte konkrete Form von D**, sofern die
  CI-Last die Staging-Stacks nicht verdrängt (sonst eigener Host).
- **D (gewählt, konkretisiert durch E): Dedizierter Non-Prod-Runner — vorzugsweise auf dem
  Staging-Host — + ADR-222-Familie + Label-Gate + Mess-Gate.** Evidenz-proportional, schließt den
  Blast-Radius, Drift via SHA-Referenz + erweitertem `runner-label-check` + Hygiene-Gate.

## Kill-Gate (messbar, datiert)

Wenn **2026-09-24** (90 Tage) *eine* Bedingung gilt:
(i) der scheduled Runner-Hygiene-Check findet auf einem CI-Runner weiterhin eine Host-Port-
Bindung oder einen verwaisten CI-Prozess, **oder** (ii) kein dedizierter Non-Prod-Runner ist in
`hosts.yaml` registriert und in Betrieb → dieser ADR wird `rejected`/`superseded`, Status-quo-
Doku wiederhergestellt. **Exception-Budget:** max. **eine** datiert begründete 30-Tage-Verlängerung.

**Aktuator, präzise (REC-8 ← AD-7):** Datenquellen sind der Hygiene-Check + der erweiterte
`runner-label-check`. Auslösung-Prüfung: am Stichtag manuell durch den Decision-Maker (Achim).
Statusänderung erfolgt per **Folge-PR**, der das Frontmatter auf `rejected`/`superseded` setzt;
„Status-quo-Doku wiederhergestellt" = derselbe PR revertet die `prod-server`-CI-Deprecation in
`hosts.yaml` und den Label-Gate-Zwang. Kein stiller Auto-Status — die Änderung ist immer ein PR.

## Folge-Artefakte (gefordert, nicht hier ausspezifiziert)

- **Runner-Betriebs-Runbook (REC-5/REC-7 ← AD-1/M28-4):** Härtungs-Checkliste (kein `user:0:0`,
  Docker-Socket-/Secret-Scope, Firewall, Disk/CPU) **+** Operational Playbook für Hygiene-Rot:
  wer reagiert, welche Jobs werden gestoppt, wann Runner-Quarantäne, wann Kill-Gate-Auslösung.
- **Evolutionspfad (REC-10 ← M28-3):** Pet-Runner jetzt → **reproduzierbares Bootstrap-Skript**
  als nächster Schritt (gegen Schneeflocken-Drift) → optional später Terraform/ARC/ephemer. Ohne
  diesen Pfad ist der Pet-Runner ein bekannter, datierter Tech-Debt, kein Endzustand.

## Referenzen

- **KONZ-risk-hub-004** — Konzept + adversariale Analyse (3 Agenten) + Evidenzbasis C1–C8.
- **ADR-222** — geteilte CI-Workflow-Familien (Workflow-Achse; dieser ADR = Placement-Achse).
- **ADR-156** — Deployment-Pipeline (Deploy bleibt legitim auf dem Prod-Host).
- **`platform/infra/hosts.yaml`** — Runner-/Host-SSoT (Eintragungsort des neuen Runners).
