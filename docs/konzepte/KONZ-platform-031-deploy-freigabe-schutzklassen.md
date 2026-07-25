---
concept_id: KONZ-platform-031
title: Deploy-Freigabe nach Schutzklassen — Post-Verification statt Pre-Approval + Approvals-Board
pipeline_status: idea
tier: T2
owner: Achim Dehnert
spec_refs: []
adr_threshold: org-weiter ADR (Governance-Änderung am Prod-Gate) — ADR erst nach Pilot-Phase 3
review_by: 2026-08-19
kill_criteria: "Ein einziger fehlgeschlagener Auto-Rollback in einem 'mittel'-Repo ⇒ betroffenes Repo sofort zurück auf Klick-Gate; wenn nach 45 Tagen kein Repo auf 'mittel' pilotiert ODER die Mechanik-Fixes (F1) nicht gemergt sind ⇒ Konzept sunset, Klick-Gate bleibt Org-Standard."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "iilgmbh/ausschreibungs-hub actions/runs/28917612280", commit_or_pr: "Deploy #240 (PR #144, merged 2026-07-05) status=waiting seit 3 Tagen; pending_deployments zeigte Required-Reviewer achimdehnert", opened_in_session: true}
  - {claim_id: C2, source_path: "iilgmbh/ausschreibungs-hub gh run list --workflow Deploy", commit_or_pr: "Runs #241–#253 alle conclusion=cancelled; #254 (28937833219) pending mit 0 Jobs — UI: 'waiting for Deploy #240 to complete'", opened_in_session: true}
  - {claim_id: C3, source_path: "ausschreibungs-hub/.github/workflows/deploy.yml", commit_or_pr: "concurrency cancel-in-progress:true cancelt laufende, aber KEINE waiting-Runs — ein unbeantworteter Klick hält die Group unbegrenzt", opened_in_session: true}
  - {claim_id: C4, source_path: "Session 2026-07-08 ausschreibungs-hub", commit_or_pr: "7 Merges (#147–#149, #151–#155, #157), davon 5 reine Docs-PRs — jeder erzeugte einen eigenen gate-pflichtigen Deploy-Run", opened_in_session: true}
  - {claim_id: C5, source_path: "iilgmbh/shared-ci#21", commit_or_pr: "Incident 2026-06-01: Auto-Rollback starb am selben Port-Bind-Fehler wie der Deploy — Prod blieb down statt zurückzufallen", opened_in_session: true}
  - {claim_id: C6, source_path: "~/.claude/policies/autonomy-gates.md", commit_or_pr: "Gate 2: Merge=Prod-Schritt in Auto-Deploy-Repos, gate-pflichtig — ratifiziert 2026-07-03", opened_in_session: true}
  - {claim_id: C7, source_path: "dev-hub/apps/releases/services.py:26", commit_or_pr: "GITHUB_TOKEN-Pattern (settings + httpx Bearer) existiert bereits — Board ist dieselbe Mechanik, lesend", opened_in_session: true}
  - {claim_id: C8, source_path: "User-Statement 2026-07-08", commit_or_pr: "devhub.iil.pet liegt hinter Cloudflare Access (achim.dehnert@iil.gmbh) — Board-Zugriff ist bereits identitätsgebunden", opened_in_session: false}
created: 2026-07-08
---

# KONZ-platform-031 — Deploy-Freigabe nach Schutzklassen

## 1 Executive Summary

- **Der Approval-Klick pro Merge skaliert nicht mit agentischer Arbeitsgeschwindigkeit.**
  Session 2026-07-08: 7 Merges (5 davon Docs-only), jeder ein eigener gate-pflichtiger
  Deploy-Run (C4). Der Klick prüft bei Docs-PRs nichts, was CI nicht schon geprüft hat —
  er kostet nur Latenz.
- **Ein vergessener Klick ist heute ein stiller 3-Tage-Ausfall der Deploy-Pipeline.**
  Run #240 stand seit 2026-07-05 auf `waiting`, hielt die Concurrency-Group (C1),
  13 Folge-Runs wurden gecancelt bzw. hingen (C2), sichtbar war das nirgends —
  `cancel-in-progress` greift bei `waiting`-Runs nicht (C3).
- **Lösung: Kontrolle wandert von *vor* dem Deploy nach *nach* dem Deploy, gesteuert über
  zwei Achsen** — statische Repo-Schutzklasse × dynamische Change-Klasse. Pre-Approval
  bleibt nur, wo Blast-Radius hoch UND Rollback schwer ist. Für alles andere: Auto-Deploy
  mit verifiziertem Auto-Rollback + Sichtbarkeit im dev-hub-Board (kein Discord).
- **Harte Vorbedingung:** shared-ci#21 (Port-Preflight + robuster Rollback) muss zuerst
  bewiesen sein — der heutige Rollback stirbt im Fehlerfall selbst (C5). Ohne
  funktionierenden Rollback ist Post-Verification unseriös.
- **Unabhängig von der Governance-Frage werden drei Mechanik-Fixes sofort umgesetzt**
  (nur-neuester-zählt, Stale-Gate-Reaper, Session-Start-Check) — sie beheben die
  #240-Klasse von Ausfällen für immer, ohne das Freigabemodell anzufassen.

## 2 Problem & Evidenz

Drei getrennte Probleme, die heute als ein diffuses „zu kompliziert, zu langsam" erscheinen:

| # | Problem | Beleg |
|---|---|---|
| P1 | `waiting`-Runs halten die Concurrency-Group unbegrenzt; unbeantwortete Gates stauen still | C1–C3 |
| P2 | Freigabe-Granularität = pro Merge, nicht pro Risikoklasse; Mensch ist Serialisierungspunkt | C4 |
| P3 | Freigaben/Status verteilt über GitHub-UI × N Repos; kein Single Pane | C1 (3 Tage unbemerkt) |

## 3 Lösungsmodell: zwei Achsen

### 3.1 Achse 1 — Repo-Schutzklasse (statisch, deklarativ)

Neues Feld `deploy_protection: low | medium | high` in `platform/scripts/repo-registry.yaml`
(SSoT, von `_deploy-unified.yml` gelesen).

| Klasse | Freigabe | Beispiele (Vorschlag, Zuordnung = offene Entscheidung §8) |
|---|---|---|
| **low** | Auto-Deploy, kein Gate, kein Klick. Agent darf bei grünem CI autonom mergen. | Klickdummy-Portale (iil-pet-portal), Docs-/TechDocs-Sites |
| **medium** | Kein Pre-Approval. Deploy → Health-Check → bei Fail **verifizierter** Auto-Rollback → Board-Eintrag. Mensch wird informiert, nicht gefragt. Merge-Freigabe bleibt im Chat (Gate 2, C6). | ausschreibungs-hub (Pilot), risk-hub, cad-hub, … |
| **high** | GitHub-Environment-Gate bleibt, Mensch klickt (im Board, §5). | ttz-lif/*, meiki-lra/* (Souveränität), billing-hub (Zahlungspfad) |

### 3.2 Achse 2 — Change-Klasse (dynamisch, pro Diff)

`_deploy-unified.yml` prüft den Diff seit letztem erfolgreichen Deploy und **eskaliert
einzelne Deploys** auf „high"-Verhalten, unabhängig von der Repo-Klasse:

- Migrationen mit destruktiven Operationen (`DROP`, `ALTER … DROP`, `RemoveField`, `DeleteModel`)
- Änderungen an `docker-compose*.yml`, Secrets-Templates, `Dockerfile`-`ENTRYPOINT`/`CMD`
- Änderungen an den Deploy-Workflows selbst

Das ist die „Gefährdungsklasse": Repo-Klasse setzt den Default, Change-Klasse überstimmt
nach oben (nie nach unten).

## 4 Mechanik-Fixes (F1 — sofort, governance-neutral)

1. **Nur-neuester-zählt:** `_deploy-unified.yml` rejected beim Start ältere `waiting`-Runs
   desselben Environments via `POST /actions/runs/{id}/pending_deployments` (state=rejected,
   Kommentar mit Verweis auf den neuen Run). Es existiert nie mehr als ein offenes Gate
   pro Repo — die #240-Stauklasse ist damit strukturell unmöglich.
2. **Stale-Gate-Reaper:** scheduled Workflow (shared-ci, 1×/6h) rejected `waiting`-Deployments
   älter als 6h org-weit mit Kommentar. Fallback-Netz für Fix 1.
3. **Session-Start-Check:** `/session-start` Phase 0.7 erweitert: `waiting`-Runs > 24h
   org-weit melden. Der heutige Fund wäre am Session-Start sichtbar gewesen.

## 5 Sichtbarkeit: dev-hub „Deploys & Approvals"-Board (statt Discord)

devhub.iil.pet, hinter Cloudflare Access (C8) — Zugriff ist bereits identitätsgebunden.
Pattern existiert (C7). Drei Sektionen: wartende Freigaben (mit Alters-Badge, >6h rot),
offene PRs, letzte Deploys — alles mit Deep-Links.

- **Stufe A (links-only):** Read-API + Deep-Links in die GitHub-UI. Kein neues Token-Risiko.
  → Umsetzung läuft (dev-hub PR, Session 2026-07-08).
- **Stufe B (one-click):** Approve/Reject-Buttons im Board (`POST pending_deployments`,
  User-Token → Audit bleibt auf achimdehnert). Braucht PAT mit org-weitem `repo`-Scope in
  dev-hub ⇒ **Gate 3 (Security-Config), separate Entscheidung** — nicht Teil dieses Konzepts.
- `notify_discord` in Deploy-Workflows → `false`, sobald Board live; Deploy-Ergebnisse
  sind Board-Inhalt.

## 6 Rollout & Messung

| Phase | Inhalt | Vorbedingung |
|---|---|---|
| 1 | Mechanik-Fixes F1 (shared-ci PR) + Board Stufe A | — |
| 2 | shared-ci#21: Port-Preflight + Rollback härten, Rollback-Erfolg in CI beweisen | — |
| 3 | `deploy_protection`-Feld + Klassen-Logik in `_deploy-unified.yml`; Pilot: ausschreibungs-hub → `medium` | Phase 2 gemergt + 1 bewiesener Auto-Rollback |
| 4 | Org-Rollout per Klassen-Zuordnung (§8); ADR schreiben (adr_threshold) | 2 Wochen Pilot ohne Kill-Kriterium |

**Metriken:** (M1) Median Merge→Prod-Live pro Klasse — Ziel `medium` < 15 min ohne
Human-Klick (Baseline heute: Stunden bis Tage, C1). (M2) Anzahl `waiting`-Runs > 6h — Ziel 0.
(M3) Rollback-Erfolgsquote bei Health-Fail — Pflicht 100 % (Kill-Kriterium).

## 7 Verworfene Alternativen

- **Nur Repo-Tier (ohne Change-Achse):** hätte den 2026-06-01-Incident nicht verhindert —
  ein „mittel"-Repo mit destruktiver Migration braucht das Gate trotzdem.
- **Nur mehr Agent-Autonomie (Gate 2 aufweichen) ohne Rollback-Härtung:** verschiebt das
  Risiko vom Klick in die Nacht; C5 zeigt, dass der Rollback heute nicht trägt.
- **Discord-Notify:** Push-Kanal ohne Aktionsfähigkeit; User-Entscheid 2026-07-08 explizit
  dagegen — Board ist pull-basiert und klickbar.
- **Approval-Delegation an den Agent (Agent klickt selbst):** zirkulär — der Prüfende wäre
  der Geprüfte; verletzt Gate `autonomous-no-human-review`.

## 8 Offene Entscheidungen

1. **Klassen-Zuordnung pro Repo** (Vorschlagsliste in §3.1) — Owner-Entscheid, dann
   `repo-registry.yaml`.
2. **Stufe B** (One-Click im Board): PAT-Scope-Entscheidung (Gate 3).
3. **`medium`-Autonomie-Endstufe:** Darf der Agent in `medium`-Repos nach 2 Wochen
   beweisbarem Auto-Rollback auch den Merge autonom ausführen (Gate-2-Delegation pro
   Klasse)? Empfehlung: ja für `low` sofort, für `medium` erst nach Phase 4.
4. **PR-Review-Pflicht in platform für Docs-only-Pfade** (vom Owner beim Review dieses
   Konzepts ergänzt, 2026-07-08): Das Ruleset verlangt 1 Approval + Code-Owner — bei einem
   Solo-Owner heißt das ein **Zwei-Konten-Ritual** (wirdigital approved achimdehnert) für
   jeden Docs-PR. Derselbe Reibungstyp wie das Deploy-Klick-Gate (§2 P2), nur am Merge
   statt am Deploy. Kandidat: Klassen-Logik auch auf die *Merge*-Anforderung anwenden —
   Docs-only-Pfade (`docs/**`, `.windsurf/workflows/**`) in platform = Klasse `low`,
   Review-Pflicht dort entfällt (Ruleset-Bypass per Pfad ist in GitHub nicht direkt
   abbildbar → Alternativen: separates Docs-Ruleset, merge-queue mit Path-Check, oder
   `--admin`-Konvention mit Audit-Kommentar). Entscheidung + Umsetzungsweg offen.
5. **Runner-/Host-Kollokation:** CI-Worker und Prod-Docker-Builds teilen sich denselben
   Host — beim #254-Deploy (2026-07-08, 12:30–12:38) starben zweimal alle 20
   pytest-xdist-Worker eines parallel laufenden dev-hub-CI-Runs („node down: Not properly
   terminated"). Hängt mit platform#988 (Disk/Ressourcen-Druck) zusammen. Kandidat für
   Phase 1: Deploy-Builds und CI-Jobs per Runner-Label oder Concurrency-Gruppe entzerren.
