---
concept_id: KONZ-platform-001
title: Deployment-Zuverlässigkeit — Konvergenz auf ADR-021 + Fail-Loud-Config-Sync statt Detektion
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: [ADR-021-unified-deployment-pattern, ADR-022-compose-file-detection]
adr_threshold: Amendment an ADR-021 (REC-1/REC-3 ändern das kanonische Pipeline-Verhalten)
review_by: 2026-09-01
kill_criteria: "Wenn nach Umsetzung von REC-1..REC-4 binnen 90 Tagen erneut ein Host↔Repo-Config-Drift-Incident auftritt (stale Service auf Prod, der im Repo entfernt ist) → entweder REC-5 (Continuous Reconcile) ziehen ODER Konzept als gescheitert verwerfen."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "mcp-hub/.github/workflows/cd.yml", commit_or_pr: "lokal main", opened_in_session: true}
  - {claim_id: C2, source_path: "mcp-hub/.github/workflows/deploy.yml", commit_or_pr: "lokal main", opened_in_session: true}
  - {claim_id: C3, source_path: "platform/.github/workflows/_deploy-unified.yml:199,254,261", commit_or_pr: "lokal main", opened_in_session: true}
  - {claim_id: C4, source_path: "platform/scripts/deploy.sh:93,101,105", commit_or_pr: "lokal main", opened_in_session: true}
  - {claim_id: C5, source_path: "platform/docs/adr/ADR-021-unified-deployment-pattern.md", commit_or_pr: "accepted/implemented", opened_in_session: true}
  - {claim_id: C6, source_path: "mcp-hub/docker-compose.prod.yml (FEHLT)", commit_or_pr: "ls negativ", opened_in_session: true}
  - {claim_id: C7, source_path: "prod 88.198.191.108 docker ps — mcp_hub_discord_bot Restarting", commit_or_pr: "Session 2026-06-01", opened_in_session: true}
  - {claim_id: C8, source_path: "Sub-Agent-Grounding: 23 shared / 6 bespoke Repos; infra-deploy/scripts/deploy.sh:114 OHNE --remove-orphans", commit_or_pr: "Explore-Agent, NICHT von mir direkt geöffnet", opened_in_session: false}
created: 2026-06-01
---

# KONZ-platform-001: Deployment-Zuverlässigkeit

> **Tier-Entscheidung (erster Satz):** **T3** — org-weit (alle ~29 Deploy-Repos), berührt die Deploy-SSoT (ADR-021) und verschiebt Pipeline-Verhalten → Auto-Eskalation-Trigger „SSoT-Verschiebung + Cross-Repo" greift unabhängig von Selbsteinstufung.

## 1. Executive Summary

Deployments fallen wiederkehrend auf, zuletzt durch einen Discord-Bot, der nach seiner Stilllegung im Repo **wochenlang als Crash-Loop auf Prod weiterlief**. Die naheliegende Diagnose („wir brauchen besseres Deployment / Drift-Monitoring") ist **falsch**: Der Mechanismus, der genau diese Drift verhindert, **existiert bereits** — `_deploy-unified.yml` scp't die Compose-Datei vor dem Deploy auf den Host (C3), und der Code-Kommentar nennt den Fehlerfall wörtlich („stale compose file… may reference a removed service").

Die **tatsächliche Wurzel** ist eine **stille Degradation**: Der Config-Sync ist an `if hashFiles('docker-compose.prod.yml') != ''` gekoppelt (C3, Z.254/261). mcp-hub hat **keine** `docker-compose.prod.yml` (C6) → der Sync-Schritt wird **lautlos übersprungen** → `deploy.sh` arbeitet gegen die **stale Host-Compose**, die discord-bot noch definiert → `--remove-orphans` (C4, Z.105) greift nicht, weil discord-bot dort ein *deklarierter* Service ist, **kein Orphan**. Ergebnis: Bei jedem Deploy neu angelegt, Crash-Loop, unbemerkt mangels Alerting.

**Empfehlung:** Keine Neuarchitektur. **Strukturelle Prävention** statt Detektion: (1) Config-Sync **fail-loud** statt silent-skip, (2) Compose-Naming-Konformität erzwingen, (3) kanonische Pipeline als **einzigen** Deploy-Pfad technisch erzwingen, (4) **ein** minimales Crash-Loop-Safety-Net. Drift-Dashboards werden bewusst **verworfen** (Panel-Votum 2:1). Continuous-Reconcile (die echte Lösung für nie-wieder-deployte Services) wird **benannt und deferred**.

## 2. Scope & Evidenzbasis

Betroffen: alle Repos mit aktivem Deploy (Sub-Agent: 23 nutzen den geteilten Workflow, 6 bespoke; C8 — nicht von mir direkt geöffnet, als Hypothese zu behandeln bis nachverifiziert). Direkt verifiziert (C1–C7): mcp-hub als Fallbeispiel, der kanonische Workflow + deploy.sh, ADR-021, der Prod-Crash-Loop.

## 3. Infrastruktur-Fit

- **ADR-021** (accepted/implemented, C5): unified deployment, geteilte reusable Workflows, `/opt/scripts/deploy.sh` als Entrypoint, ~10 Hubs auf einer Hetzner-VM (Single-Dev).
- **ADR-022**: Compose-File-Detection (`docker-compose.prod.yml`/`.staging.yml`/Fallback `docker-compose.yml`).
- mcp-hub Auto-Deploy (push:main) läuft über den **kanonischen** `_deploy-unified.yml` (C2); die bespoke `cd.yml` ist nur **manuell** (`workflow_dispatch`, C1) — also kein reiner „bespoke vs. shared"-Fall, sondern ein **konformer Pfad mit stillem Sync-Loch** + ein manueller Zweitpfad.

## 4. Steelman (stärkster Fall FÜR Konvergenz)

Der Fix reduziert sich von „Architektur erfinden" auf „Konvergenz erzwingen + bekannte Restlücken schließen" — billig, verifizierbar, ohne neuen Wartungs-Surface. ADR-021 ist bewiesen; man baut auf der SSoT statt eine zweite zu schaffen. Drei der vier Mechanismen nutzen **bestehende** Skills (`compose-audit`, `drift-check`, `discord_notify`). Der Incident entstand durch *Abweichung* von der SSoT, nicht durch deren Fehlen — eine Neuarchitektur würde das eine zerstören, das nachweislich funktioniert (scp-Sync).

## 5. Konzeptdefinition

**Kernthese:** Deployment-Unzuverlässigkeit ist ein **Silent-Degradation- + Adoptions-Problem**, kein Mechanismus-Problem. Der Hebel ist, die *vorhandene* SSoT-Garantie **lückenlos und laut** zu machen und Abweichungspfade **konstruktiv** zu schließen — nicht, Drift nachträglich zu *beobachten*.

## 6. Adversariale Analyse — Konfliktmatrix (Pflicht T3)

Drei unabhängige Agenten (Steelman / Advocatus Diabolus / Maintainer-2028), die sich gegenseitig nicht sahen. Belegte Dissense:

| # | Streitpunkt | Steelman | Advocatus Diabolus | Maintainer-2028 | Auflösung |
|---|---|---|---|---|---|
| K1 | Drift-Detection-Dashboard als primärer Mechanismus | JA (4. Mechanismus) | NEIN — wird selbst zur **zweiten Wahrheitsquelle** (grünes Dashboard vor stale Host = exakt der Discord-Proxy in teuer) | NEIN — **verrottet** (Report den keiner liest) + redundant bei struktureller Prävention | **2:1 → VERWORFEN** als primär; höchstens Fallback, falls Prävention unerreichbar |
| K2 | Alerting = Lösung? | Mechanismus | „Versicherung gegen das eigene Versagen beim Verhindern", schwächer als verhindern | verrottet nach False-Positives (Mute) | **Konvergenz:** nur **minimales** Safety-Net, nicht die Lösung |
| K3 | Bespoke-Pipelines verbieten | per Policy | Gate wird beim ersten Hotfix umgangen (`--no-verify`/force) → Papier | per **required check technisch** erzwingen, nicht per ADR | **Konvergenz:** technisch erzwingen; **+ Multi-Service-Profil zertifizieren** statt pauschal verbieten (Diabolus K3b: mcp-hub ist legitim multi-service) |
| K4 | Eigentliche Fehlerklasse | Deploy-Pfad-Compliance | **RUNTIME/Lifecycle** — kein Deploy-Workflow entfernt einen Service, der **nie wieder deployt** wird; Runtime-Drift (`docker exec`, Volumes, manuelle `run`) ist außerhalb Compose-SSoT | deploy-time `--remove-orphans` reicht für **aktive** Apps | **Teil-Dissens:** Für aktive Apps löst REC-1..3; never-redeployed + Runtime-Drift = **Restlücke** → REC-5 (deferred) |

**Diabolus' teuerster blinder Fleck (angenommen):** Das Konzept adressiert primär den **Deploy-Pfad**; der Incident war ein **Lifecycle**-Versagen. Antwort: REC-1..3 schließen es für *aktive* Apps strukturell (frischer Sync → `--remove-orphans` entfernt den entfernten Service). Die *echte* Volllösung (Continuous Reconcile Host==Soll-Manifest, deploy-unabhängig) ist schwerer → **REC-5, bewusst deferred mit Kill-Gate**, nicht verschwiegen.

## 7. Deep-Dive — die Kausalkette (verifiziert)

1. mcp-hub push:main → kanonischer `_deploy-unified.yml` (C2).
2. Sync-Schritt `if hashFiles('docker-compose.prod.yml') != ''` (C3) → mcp-hub hat die Datei nicht (C6) → **silent skip**.
3. `deploy.sh` nutzt Fallback = stale Host-`docker-compose.yml` (definiert discord-bot).
4. `up -d --force-recreate --remove-orphans` (C4): discord-bot ist *in* dieser Compose → **kein Orphan** → wird re-created.
5. Token beim Stilllegen entfernt → Crash-Loop; kein Alerting → wochenlang unsichtbar (C7).

## 8. Alternativen

- **A — Status quo:** Drift wiederholt sich pro nicht-konformem Repo. ❌
- **B — Neues deklaratives Deploy-System (z.B. Compose→Nomad/k3s, GitOps/ArgoCD):** löst Runtime-Reconcile *richtig*, aber massiver Overhead für Single-Dev + unreife Pipeline; zerstört das funktionierende scp+deploy.sh. ❌ (jetzt)
- **C — Konvergenz + Fail-Loud + minimales Safety-Net (GEWÄHLT):** right-sized, baut auf SSoT, strukturelle Prävention. ✅
- **D — Reine Detektion (Drift-Dashboard + Alerting):** Panel 2:1 dagegen; behandelt Symptom, erzeugt zweite Wahrheitsquelle. ❌

## 9. Out-of-the-Box

- **OOTB-1:** Der `hashFiles()`-Silent-Skip ist ein generisches Anti-Pattern — ein **CI-Lint gegen `if: hashFiles(...)`-guards auf sicherheits-/SSoT-kritischen Schritten** könnte die ganze Klasse fangen (nicht nur Compose-Sync).
- **OOTB-2:** „expected services"-Manifest pro Repo (`deploy/expected-services.txt`), gegen `docker ps` diff't — die billige Vorstufe zu REC-5 ohne vollen Reconcile-Stack.

## 10. Befunde

| ID | Befund | Schwere | Evidenz |
|---|---|---|---|
| B1 | Config-Sync degradiert **still** zu „nutze stale Host-Compose", wenn `docker-compose.prod.yml` fehlt | **hoch** | C3+C6 |
| B2 | mcp-hub verletzt Compose-Naming (ADR-022) → triggert B1 | mittel | C6 |
| B3 | `--remove-orphans` entfernt entfernte Services nur, wenn die *frische* Compose ankommt (sonst kein Orphan) | hoch | C4 (Z.93-Kommentar) |
| B4 | Kein Crash-Loop-/Container-Health-Alerting platform-weit | mittel | C7 + Lücke |
| B5 | Zweiter manueller Deploy-Pfad (mcp-hub cd.yml) gegen stale Host-Compose | mittel | C1 |
| B6 | infra-deploy/deploy.sh nutzt **kein** `--remove-orphans` | mittel | C8 (Hypothese — nachverifizieren) |

## 11. Top-5-Risiken

1. **R1 — Migration stagniert bei 8/10** (Diabolus K8): nicht-konforme Repos bleiben „später". → Mitigation: required check erzwingt, kein Opt-out.
2. **R2 — Dashboard-Grün-Blindheit:** falls doch ein Drift-Report gebaut wird → Whitelisting macht ihn blind. → Mitigation: REC-D (kein Dashboard).
3. **R3 — Gate-Umgehung beim Hotfix** (Diabolus K3): → Mitigation: Fast-Deploy-Override aus ADR-021 §2.15 nutzen statt Gate umgehen.
4. **R4 — Multi-Service-Zwang macht kanonischen Workflow fragil** (Diabolus K7): → Mitigation: zertifiziertes Multi-Service-Profil statt `if`-Wildwuchs.
5. **R5 — Restlücke never-redeployed/Runtime-Drift bleibt offen** (Diabolus K4): → bewusst akzeptiert, REC-5 Kill-Gate.

## 12. Empfehlungen (konkret)

- **REC-1 (Fail-Loud, höchster Hebel, struktureller Fix):** In `_deploy-unified.yml` den Silent-Skip ersetzen: Wenn ein Repo über den kanonischen Workflow deployt und **keine** prod/staging-Compose zum Syncen existiert → **Deploy mit klarem Fehler abbrechen**, statt still auf Host-Stand zurückzufallen. (behebt B1) → **Amendment ADR-021.**
- **REC-2:** mcp-hub `docker-compose.prod.yml` anlegen (= Repo-SSoT der Prod-Topologie, ohne discord-bot). Nächster Deploy synct frisch → `--remove-orphans` entfernt discord-bot **strukturell**. (behebt B2 + Discord-Recreation-Restrisiko)
- **REC-3:** Kanonische Pipeline als **einzigen** Deploy-Pfad **technisch** erzwingen (required status check / Branch-Protection lehnt push-to-deploy ohne `uses: _deploy-unified` ab); mcp-hub `cd.yml` zurückbauen oder als zertifiziertes **Multi-Service-Profil** in den kanonischen Workflow heben. (behebt B5, K3) → **Amendment ADR-021.**
- **REC-4 (minimales Safety-Net, kein Metrik-Stack):** **ein** Cron/Timer: `docker ps` → `Restarting`-State grep → `orchestrator__discord_notify`. Explizit sekundär. (behebt B4, Maintainer #5)
- **REC-5 (DEFER, benannt):** Continuous Reconcile gegen ein „expected-services"-Manifest (Host-State == Soll, sonst kill+alert), deploy-unabhängig — die echte Lösung für never-redeployed + Runtime-Drift. **Nur bauen, wenn Kill-Gate feuert.**
- **REC-D (NICHT TUN):** kein eigenständiges Drift-Detection-Dashboard als primäre Kontrolle (Panel 2:1; zweite Wahrheitsquelle).
- **REC-6:** B6 nachverifizieren (infra-deploy deploy.sh) und ggf. `--remove-orphans` angleichen.

## 13. Entscheidung + Kill-Gate + 30/60/90

**Entscheidung (Vorschlag):** Option C. Reihenfolge nach Hebel: REC-1 → REC-2 → REC-3 → REC-4. REC-5 deferred.

**Kill-Gate (messbar):** siehe Frontmatter `kill_criteria` — erneuter Config-Drift-Incident binnen 90 Tagen nach REC-1..4 ⇒ REC-5 ziehen oder Konzept verwerfen. Exception-Budget: 1 tolerierter Near-Miss bis 2026-09-01.

- **30 Tage:** REC-1 (Fail-Loud) als ADR-021-Amendment + Implementierung; REC-2 (mcp-hub prod-compose).
- **60 Tage:** REC-3 (required check, einziger Pfad) + Multi-Service-Profil-Entscheidung.
- **90 Tage:** REC-4 (Crash-Loop-Cron) live; Kill-Gate-Review.

**Ehrliche Enforcement-Grenze:** Dieses Doc *schreibt* Lifecycle-Felder, *erzwingt* sie nicht — `review_by`/`kill_criteria` wirken erst über ein Lifecycle-Gate. Bis dahin Review-Gate, kein Exit-Code.

---

## 14. Externe Zweitmeinung — Rückfluss-Gate (2026-06-01)

Cross-Provider-Review (Briefing `~/shared/adr-handoff-KONZ-platform-001-2026-06-01.md`). Jede ID getaggt; nur `[valid]` fließt ein, als Änderung mit eigener Begründung (nicht GPT-Prosa). Zwei Review-Behauptungen selbst nachverifiziert: AD-18 (GHA-Concurrency-Groups existieren pro App, `_deploy-unified.yml:185-243` → CI-Pfad gesperrt, Residual host-manuell) und AD-5 (`scripts/deploy.sh:49` setzt `COMPOSE_PROJECT_NAME` nur für staging, prod implizit verzeichnis-basiert → Risiko real).

### Kern-Erkenntnis (angenommen)
Die Review verschiebt die Wurzel von **„fail-loud bei fehlender Compose"** zu **„CI-Sync, `deploy.sh`-Compose-Detection und Host-Ist-Zustand teilen keinen verifizierten Vertrag"**. REC-1 wird entsprechend von einem Skip-Fix zu einem **Deploy-Bundle-Vertrag mit Host-seitigem Verify** aufgewertet. Das trifft F1 (Fail-Loud allein ist Symptom-nah) und schärft F2 (Eigentums-Grenze statt Zeitpunkt-Grenze).

### Verdikt-Tabelle (ID → Verdikt → Aktion)
| IDs | Verdikt | Aktion |
|---|---|---|
| PRO-1..8 | valid | Bestätigen Konzept-Kern; keine Änderung |
| AD-1, M28-1 | valid | REC-1' — EINE geteilte Compose-Resolution (Workflow == `deploy.sh`), ADR-021+022 vereinheitlicht |
| AD-2, AD-12 | valid | REC-1' — Prod verlangt explizite env-Compose; fehlt sie → **fail-loud** statt silent-fallback (Fallback-Politik vorab entscheiden) |
| AD-3, AD-17 | valid | REC-1'/REC-2' — atomarer Sync (temp→hash→rename) + Host-Verify `compose_sha == CI-Bundle`, sonst **fail-closed** |
| AD-4 | valid | REC-1' — Bundle deckt referenzierte Artefakte (`env_file`/Overrides/Profiles/Includes/Build-Kontext) ODER markiert sie explizit host-owned |
| AD-5, M28-8 | valid | REC-NEU-B — `COMPOSE_PROJECT_NAME` auch für **prod** explizit pinnen (Manifest); `deploy.sh` failt bei Mismatch |
| AD-6, AD-13, M28-3, OOTB-C | valid | REC-3' — Host-seitiger Deploy-Intent-Token; manuell nur `--break-glass` (Grund/Ablauf/Audit). Required-check allein stoppt Host-SSH nicht |
| AD-7, M28-7 | valid | REC-3' — „Multi-Service-Profil" operativ definieren: erlaubte Dateien, Project-Name, Ownership, Retire, Health, **Re-Zertifizierung mit Ablaufdatum** |
| AD-8, AD-16, M28-4, OOTB-D | valid | REC-4' — Safety-Net über `docker inspect` (Restarting/Exited/unhealthy/RestartCount-Delta/OOM/fehlende Owner-Labels), nicht `grep Restarting` |
| AD-9, M28-6 | valid | Kill-Gate' — feuert auch, wenn Host-`compose_sha`/Labels/Service-Liste nicht zum letzten Bundle passen (abgeleiteter Host-vs-Bundle-Proof, KEIN Dashboard) |
| AD-14, M28-5 | valid | REC-NEU-A — Ownership-Labels (`repo/service/environment/commit_sha/compose_sha/deploy_run_id/deployed_at`); Audits auditieren Labels, nicht Namen |
| AD-15 | valid | REC-5' — `expected-services` MUSS aus dem letzten akzeptierten Bundle/Repo-Compose abgeleitet sein, nie manuell (sonst zweite Wahrheit) |
| AD-10, M28-2 | valid | REC-2' — Doppelpflege `*.yml` ↔ `*.prod.yml` vermeiden (Generator/Symlink/Check); fachliche Abweichung nur im Profil begründet |
| AD-18 | valid-partiell | CI-Pfad bereits durch GHA-Concurrency gesperrt (verifiziert); Residual = host-manuelle Deploys → durch REC-3' Intent-Token abgedeckt. **Kein** separater Host-Lock nötig |
| AD-11, OOTB-B | deferred | Retire-Tombstones (entfernt vs. retired) — sinnvoll, aber über idea-stage/Single-Dev hinaus; in REC-5-Scope aufnehmen, nicht v1 |
| OOTB-A | valid-adopt | = Spine aus REC-1'/REC-NEU-A/B (Bundle + Manifest + Labels) |

Out-of-scope/abgelehnt: keine — die Review war durchweg on-point.

### Revidierte Empfehlungen (v2 — ersetzt §12-Spine)
- **REC-1' (Deploy-Bundle-Vertrag, höchster Hebel):** EINE geteilte Compose-Resolution für Workflow + `deploy.sh`; Prod verlangt explizite env-Compose (kein stiller Fallback) → fail-loud; atomarer Sync (temp→hash→rename); Host-Verify `compose_sha == CI-Bundle`, sonst fail-closed; Bundle deckt/benennt Nebenartefakte. (AD-1/2/3/4/12/17, M28-1)
- **REC-2' (mcp-hub prod-Compose):** wie REC-2, plus Doppelpflege vermeiden (Generator/Symlink/Check). (AD-10, M28-2)
- **REC-3' (einziger Pfad, host-erzwungen):** required check + Host-Intent-Token; manuell nur `--break-glass`. Multi-Service-Profil operativ + mit Re-Zert-Ablauf definieren. (AD-6/7/13, M28-3/7, OOTB-C)
- **REC-4' (State-Safety-Net via `docker inspect`):** breiter Container-State-Check statt grep. (AD-8/16, M28-4, OOTB-D)
- **REC-NEU-A (Ownership-Labels):** jedes von `deploy.sh` erzeugte Container-Set labeln; Audits/REC-4'/REC-5' nutzen Labels. (AD-14, M28-5)
- **REC-NEU-B (Project-Name-Pin):** `COMPOSE_PROJECT_NAME` für prod explizit; Mismatch = fail. (AD-5, M28-8)
- **REC-5' (Reconcile, deferred):** `expected-services` **abgeleitet**, nie manuell; deckt nie-wieder-deployte + Runtime-Drift; Retire-Tombstones hier verorten. (AD-11/15)
- **Kill-Gate':** zusätzlich Host-vs-Bundle-Mismatch (Label/SHA/Service-Liste), der nur manuell auffällt. (AD-9, M28-6)

**Right-Sizing-Hinweis (Maintainer-Lens gewahrt):** v1 = REC-1' + REC-NEU-A + REC-NEU-B + REC-2' (struktureller Spine); REC-3'-Intent-Token + REC-4' folgen; REC-5'/Tombstones bleiben deferred. Kein Bundle-Over-Engineering vor belegtem Bedarf — der Spine löst den verifizierten Incident, der Rest ist Härtung mit eigenem Kill-Gate.
