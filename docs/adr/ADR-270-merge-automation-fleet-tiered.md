---
status: proposed
date: 2026-07-09
decision-makers: Achim Dehnert
consulted: –
informed: –
implementation_status: not-started
domains: [architecture, ci-cd, governance]
scope: platform
relates_to: [ADR-046, ADR-234, ADR-264, ADR-242]
tags: [merge-queue, auto-merge, branch-protection, dependabot, fleet, throughput]
---

# ADR-270: Merge-Automatisierung fleet-weit einführen — risiko-getiert (Tier A: strict=false + Auto-Merge · Tier B: Merge-Queue)

## Metadaten

| Attribut | Wert |
|----------|------|
| **Status** | Proposed |
| **Scope** | platform (org-weite Konvention) |
| **Erstellt** | 2026-07-09 |
| **Autor** | Achim Dehnert |
| **Reviewer** | – |
| **Supersedes** | – |
| **Superseded by** | – |
| **Relates to** | ADR-046 (Docs-Governance), ADR-234 (Registry-SSoT/Gates), ADR-242 (Branch-Protection-Wellen), ADR-264 (Deployment-SSoT) |

## Repo-Zugehörigkeit

| Repo | Rolle | Betroffene Pfade / Komponenten |
|------|-------|-------------------------------|
| `platform` | Primär | `docs/adr/`, Branch-Protection/Ruleset (Referenz-Implementierung), `.github/workflows/dependabot-automerge.yml` |
| *Tier-A-Repos* (Libs/Docs/Meta) | Sekundär | Branch-Protection `strict=false`, `allow_auto_merge` |
| *Tier-B-Repos* (Prod-Deploy) | Sekundär | Merge-Queue-Ruleset + `merge_group`-CI-Trigger auf Required Checks |

---

## Decision Drivers

- **Catch-up-Merge-Tax (belegt 2026-07-09):** Bei der platform-PR-Triage stallten 10 approved+grüne PRs seriell, weil `strict=true` (up-to-date-Pflicht) nach jedem Merge alle übrigen PRs auf „behind" setzte → manuelles Whack-a-Mole. `strict=false` auf platform löste es sofort.
- **Review-Durchsatz:** Approved-aber-nicht-gemergte PRs sammeln sich an; der manuelle Merge-Klick + CI-Timing ist reiner Overhead, sobald das menschliche Gate (Review) passiert ist.
- **Dependabot-Rauschen:** 9 von 11 Backlog-PRs waren Dependabot-Bumps mit wiederkehrenden `requirements`-Konflikten.
- **Prod-Sicherheit darf nicht geopfert werden:** Deploy-on-push-Repos deployen bei Merge→main direkt nach Prod (ADR-264, Memory `merge_to_main_triggers_deploy`). Dort ist `strict=true` schützend, nicht lästig — ein einheitliches `strict=false` würde ungetestete Semantik-Konflikte live schicken.

---

## 1. Context and Problem Statement

Der Merge-Durchsatz über die Fleet ist durch zwei Reibungen begrenzt: (a) die **up-to-date-Pflicht** (`strict=true`) erzeugt seriellen Catch-up-Zwang bei mehreren gleichzeitig approved PRs, und (b) jeder Merge braucht einen manuellen Klick zum richtigen Zeitpunkt (nach CI-Grün, vor dem nächsten main-Move). Beides ist auf **platform** am 2026-07-09 konkret aufgetreten.

Der naive Fix — `strict=false` + Auto-Merge **überall** — ist aber nicht uniform sicher: für Prod-Deploy-Repos hebt er eine echte Schutzeigenschaft auf.

### 1.1 Ist-Zustand

| Aspekt | Zustand vor diesem ADR |
|--------|------------------------|
| Branch-Protection | Pro Repo, meist `strict=true` (klassisch + teils Ruleset) |
| Auto-Merge | Repo-Setting `allow_auto_merge` uneinheitlich; auf platform seit 2026-07-09 an |
| Merge-Queue | Nirgends aktiv |
| Dependabot | patch/minor werden manuell reviewt+gemergt |

### 1.2 Warum jetzt

Die platform-Triage 2026-07-09 hat die Catch-up-Tax quantifiziert (10 PRs, mehrere manuelle Rebase-Runden) und den sauberen Fix (`strict=false`) auf platform validiert. Das ist der Moment, die Lehre als org-weite Konvention zu verankern — **bevor** sie ad-hoc + inkonsistent pro Repo nachgebaut wird.

---

## 2. Considered Options

### Option A: Risiko-getierte Zwei-Klassen-Policy ✅

- **Tier A** (kein Prod-Deploy: Libraries, Docs, Meta): `strict=false` + `allow_auto_merge=true` + `allow_update_branch=true`. Auto-Merge nach Approval ist Default.
- **Tier B** (Prod-Deploy-on-push): **Merge-Queue** (Required Checks laufen im `merge_group`-Kontext gegen latest main → rebase+test+merge in Reihenfolge). `strict` bleibt wirksam, aber die Queue automatisiert das Up-to-date-Halten.
- **Dependabot** patch/minor: Auto-Merge-Workflow (platform#1021 als Referenz).

**Pros:**
- Fleet-weit „schnell + keine ungewollten Stopps".
- Tier B behält Prod-Schutz (kein ungetesteter Semantik-Konflikt → Prod).
- Klassifikation per **Regel** (deploy-on-push?), nicht per eingefrorener Liste.

**Cons:**
- Zwei Konfigurationsprofile statt einem (mehr Rollout-Arbeit).
- Tier B braucht `merge_group`-CI-Verdrahtung als Vorbedingung.

### Option B: `strict=false` + Auto-Merge uniform überall

**Pros:** Einheitlich, minimaler Rollout.

**Cons:** Ein approved-aber-nicht-gegen-latest-main-getesteter PR kann auf einem Prod-Deploy-Repo auto-mergen → **auto-deploy nach Prod**. Semantik-Konflikt = möglicher Prod-Ausfall bei Repos mit echten Kundendaten (risk-hub, coach-hub). → **Abgelehnt weil:** opfert Prod-Sicherheit für Uniformität.

### Option C: Status quo (`strict=true` überall, kein Auto-Merge)

**Pros:** Maximaler Schutz, nichts zu ändern.

**Cons:** Die Catch-up-Tax bleibt fleet-weit; manueller Merge-Overhead skaliert mit dem PR-Volumen. → **Abgelehnt weil:** das belegte Durchsatzproblem bleibt ungelöst.

---

## 3. Decision Outcome

**Gewählte Option: Option A — risiko-getierte Zwei-Klassen-Policy.**

Sie liefert den Durchsatzgewinn dort, wo er risikofrei ist (Tier A), und den *gleichen* Durchsatzgewinn über die Merge-Queue dort, wo Prod-Sicherheit zählt (Tier B) — ohne die schützende Up-to-date-Eigenschaft für Prod-Deploys wegzunehmen. Option B wurde wegen des Prod-Risikos verworfen, Option C weil sie das Problem nicht löst.

---

## 4. Implementation Details

### 4.1 Tier-Klassifikation (Regel, nicht Liste)

Ein Repo ist **Tier B**, wenn ein Merge auf `main` einen **Prod-Deploy** auslöst (`deploy.yml`/`_deploy-*.yml` mit `on: push: branches: [main]` **ohne** reinen paths-Filter, der Deploy ausschließt). Sonst **Tier A**. Die konkrete Liste wird **zum Rollout-Zeitpunkt** aus `origin/main` gescannt (nicht hier eingefroren — Memory `stale_local_clone_never_ground_truth`), Kandidat: `tools/` Scan-Skript über `registry/canonical.yaml` + `.github/workflows/`.

### 4.2 Tier-A-Konfiguration

- Branch-Protection `main`: `required_status_checks.strict = false`.
- Repo-Settings: `allow_auto_merge = true`, `allow_update_branch = true`.
- Konvention: nach externem/Code-Owner-Approval `gh pr merge --auto` (Default-Verhalten).

### 4.3 Tier-B-Konfiguration (Merge-Queue)

**Vorbedingung (hart):** Die Required Checks müssen auf `merge_group` triggern — sonst friert die Queue **alle** Merges ein (belegt: platform `guardian.yml` hört nur auf `pull_request`).

```yaml
# in jedem Required-Check-Workflow ergänzen:
on:
  pull_request:
    types: [opened, synchronize, reopened]
  merge_group:            # <- neu, Voraussetzung für Merge-Queue
```

Erst **danach** Merge-Queue via Ruleset-Regel `merge_queue` aktivieren.

### 4.4 Dependabot-Auto-Merge

patch/minor via `dependabot-automerge.yml` (platform#1021 als Referenz-Implementierung); `major` bleibt manuell. Kein Ruleset-Bypass ohne separate, benannte Freigabe.

### 4.5 `require_last_push_approval`

Bewusst **aus** (Entscheidung Achim 2026-07-09). Konsequenz: ein Commit nach dem Approval kann ungeprüft auto-mergen — akzeptiertes Restrisiko, dokumentiert unter §7.

---

## 5. Migration Tracking

Rollout **gegatet**, Tier für Tier, je Phase eigener PR + Verifikation. Kein Massen-Patch.

| Phase | Umfang | Status | Datum | Notizen |
|-------|--------|--------|-------|---------|
| 0 | platform (Referenz) | ✅ Abgeschlossen | 2026-07-09 | `strict=false`+`allow_update_branch`+Auto-Merge live; Dependabot-WF #1021 |
| 1 | Tier-A-Klassifikation scannen + Liste erzeugen | ⬜ Ausstehend | – | Scan gegen origin/main |
| 2 | Tier A ausrollen (`strict=false`+Auto-Merge) | ⬜ Ausstehend | – | dry-run-Report zuerst, dann je Repo |
| 3 | Tier-B `merge_group`-CI-Verdrahtung | ⬜ Ausstehend | – | Required-Check-Workflows erweitern, VOR Queue |
| 4 | Tier B Merge-Queue aktivieren | ⬜ Ausstehend | – | erst nach Phase 3 verifiziert |

---

## 6. Consequences

### 6.1 Good
- Fleet-weit hoher Merge-Durchsatz ohne manuelles Rebase-Whack-a-Mole.
- Prod-Deploy-Repos behalten den Up-to-date-Schutz (via Queue statt via Stall).
- Dependabot-Rauschen sinkt (patch/minor auto).

### 6.2 Bad
- Zwei Konfigurationsprofile → mehr Rollout- und Pflegeaufwand.
- Tier B hängt an der `merge_group`-Verdrahtung jedes Required Checks.

### 6.3 Nicht in Scope
- Ruleset-Bypass für Dependabot (separate Entscheidung).
- `require_last_push_approval=true` (bewusst nicht gesetzt).
- Konsolidierung klassische Protection ↔ Ruleset (eigener Cleanup).

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| Semantik-Konflikt (zwei je-grüne PRs) landet auf Tier A ungetestet | Niedrig | Niedrig (kein Prod) | Tier A ist deploy-frei; Schaden kosmetisch/reparabel |
| Merge-Queue eingeschaltet ohne `merge_group`-CI → alle Merges eingefroren | Mittel | Hoch | Phase 3 **vor** Phase 4 gaten; Reihenfolge im ADR fixiert |
| Post-Approval-Push auto-merged ungeprüft (`require_last_push_approval=false`) | Niedrig | Mittel | Restrisiko bewusst akzeptiert; bei Missbrauch nachträglich aktivierbar |
| Fehl-Klassifikation eines Deploy-Repos als Tier A | Niedrig | Hoch | Klassifikation per Regel (deploy-on-push-Scan), dry-run-Report vor Apply |

---

## 8. Confirmation

1. **Rollout-Scan-Report**: `tools/`-Skript listet je Repo Tier (A/B) + Ist-Protection; Divergenz zu diesem ADR = Finding.
2. **Tier-B-Guard**: Merge-Queue wird nur aktiviert, wenn der Scan bestätigt, dass alle Required Checks des Repos `merge_group` triggern (sonst Abbruch).
3. **Drift-Detector**: Dieses ADR wird von ADR-059 auf Aktualität geprüft — Staleness-Schwelle: 12 Monate.

---

## 9. More Information

- ADR-264: Deployment-SSoT (Merge→main→Prod-Promotion) — begründet den Tier-B-Schutzbedarf.
- ADR-242: Branch-Protection-Wellen — dieselbe Protection-Fläche.
- platform#1021: Dependabot-Auto-Merge-Referenz-Workflow.
- Auslöser-Session: platform-PR-Triage 2026-07-09 (Catch-up-Tax quantifiziert, `strict=false` auf platform validiert).

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-07-09 | Achim Dehnert | Initial: Status Proposed |
