---
status: proposed
date: 2026-06-26
revision: 1
decision-makers: [Achim Dehnert]
scope: platform
implementation_status: none
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

`proposed` — wartet auf Entscheidung. Liefert die empirische Begründung, auf die
ADR-222 (eingefroren „bis neue Empirie") für die Placement-Achse wartet.

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

1. **CI-Workloads laufen nicht mehr auf dem Prod-Host.** Ein **dedizierter Non-Prod-Runner**
   (eigener Host/VM) übernimmt `self-hosted`-CI. `prod-server` wird für CI **deprecated**
   (verbleibt höchstens für Deploy-Schritte, die per Definition auf den Prod-Host gehören).
2. **Ehrliche Benennung:** Der neue Runner ist zunächst ein **dediziertes „Pet"**, kein
   auto-skalierender ephemerer Runner — es existiert (Stand heute) **keine** Provisioning-
   Automation (ARC/Terraform). „Ephemeral" wird *nicht* behauptet, bis solche Automation steht.
3. **`hosts.yaml` ist und bleibt die Runner-SSoT.** Der neue Runner + die `prod-server`-CI-
   Deprecation werden dort eingetragen; keine zweite Topologie-Quelle.
4. **Hermetische Job-Form** (run-eindeutige Ports / keine Host-Port-Bindung / garantierter
   Teardown) wird als ADR-222-Familien-Baustein geteilt — **referenziert per SHA**, nicht kopiert.
5. **Mess-Gate statt Behauptung:** Ein scheduled, read-only **Runner-Hygiene-Check** misst je
   Runner Host-Port-Bindungen + verwaiste CI-Prozesse und wird rot bei Verstoß (speist das Kill-Gate).

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
- **D (gewählt): Ein dedizierter Non-Prod-Runner + ADR-222-Familie + Mess-Gate.** Evidenz-
  proportional, schließt den Blast-Radius über einen Host, Drift via SHA-Referenz + Hygiene-Gate.

## Kill-Gate (messbar, datiert)

Wenn **2026-09-24** (90 Tage) *eine* Bedingung gilt:
(i) der scheduled Runner-Hygiene-Check findet auf einem CI-Runner weiterhin eine Host-Port-
Bindung oder einen verwaisten CI-Prozess, **oder** (ii) kein dedizierter Non-Prod-Runner ist in
`hosts.yaml` registriert und in Betrieb → dieser ADR wird `rejected`/`superseded`, Status-quo-
Doku wiederhergestellt. **Exception-Budget:** max. **eine** datiert begründete 30-Tage-Verlängerung.

## Referenzen

- **KONZ-risk-hub-004** — Konzept + adversariale Analyse (3 Agenten) + Evidenzbasis C1–C8.
- **ADR-222** — geteilte CI-Workflow-Familien (Workflow-Achse; dieser ADR = Placement-Achse).
- **ADR-156** — Deployment-Pipeline (Deploy bleibt legitim auf dem Prod-Host).
- **`platform/infra/hosts.yaml`** — Runner-/Host-SSoT (Eintragungsort des neuen Runners).
