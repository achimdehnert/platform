---
id: ADR-275
title: "Registry-SSoT-Konsolidierung — canonical.yaml als einzige Quelle, github_repos.yaml stilllegen"
status: proposed
decision_date: 2026-07-14
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [iilgmbh]
scope: platform
supersedes: []
related: [ADR-022, ADR-157, ADR-234]
tags: [registry, ssot, drift-prevention, ci, generated, governance]
drift_check_paths:
  - "registry/canonical.yaml"
  - "registry/github_repos.yaml"
  - "registry/repos.yaml"
---

# ADR-275 — Registry-SSoT-Konsolidierung

## Context and Problem Statement

Die Plattform pflegt **zwei** Repo-Registries, die beide von sich behaupten, die
„Single Source of Truth" zu sein, und **beide von aktiver CI live gelesen werden**:

| Datei | Selbstanspruch (Header) | Realität | Schutz |
|---|---|---|---|
| `registry/canonical.yaml` → `registry/repos.yaml` (View) | „Kanonische Quelle" (ADR-234 P0) | generiert, zuletzt 2026-07-10; 53 aktive Repos, reiches Schema | **CI-Drift-Gate** `registry-consistency.yml`; View-Reader-Guard (ADR-234 §11.1) |
| `registry/github_repos.yaml` | „Single Source of Truth für Cascade, port_audit, onboard-repo, deploy-check" | **manuell** gepflegt, Snapshot **2026-04-03** (86 Repos), zuletzt berührt 2026-06-29; 113 Einträge inkl. 68 Archive | **kein** Gate — nur ein `runner-health`-Kommentar „manually maintained" |

Das ist kein historisches Relikt: `github_repos.yaml` wird nachweislich von **vier
aktiven Konsumenten** gelesen (per `grep` verifiziert, 2026-07-14):

1. `scripts/sync-workflows.sh` — liest die Sektions-Keys `django_apps` +
   `org_django_apps` → `DJANGO_HUBS`, `frameworks` → `PACKAGES` (Repo-Typ-Klassifikation
   für die Workflow-Symlink-Verteilung).
2. `.github/workflows/runner-health.yml` — iteriert `django_apps` + `org_django_apps`
   mit `deployed==true` + `github`-Feld (Runner-Health-Abgleich).
3. `.github/workflows/sync-drift-meter.yml` — erwartet die Datei unter
   `$GITHUB_DIR/platform/registry/github_repos.yaml` (Fleet-Drift-Melder).
4. `infra/scripts/validate_repos.py` — Cross-Check GitHub ↔ `github_repos.yaml` ↔
   `ports.yaml`.

**Kernbefund:** Manche Workflows entscheiden gegen die frische, gegatete Quelle,
andere gegen einen 3,5 Monate alten, ungeschützten Snapshot. Ein April-Snapshot
kennt z. B. `dms-hub` nicht (erst später onboarded) und führt dekommissionierte
Repos (`bfagent`, seit 2026-06-03) evtl. noch als aktiv. **Stille Fehlfunktion durch
Datenalter ist der eigentliche Schaden, nicht die Existenz zweier Dateien.**

Dieser Konflikt ist wiederholt als „bekannt" notiert worden (KONZ-platform-015
Befund; AGENT_HANDOVER), aber nie aufgelöst — dasselbe „bekannt, nicht befolgt"-Muster
wie beim Port-Duplikat (Issue #1033, real getroffen 2026-07-14).

## Decision Drivers

1. **Genau eine SSoT** — prüfbar, gegen die neue Consumer validieren, kein zweiter
   Anspruch.
2. **Kein stiller Datenzerfall** — die maßgebliche Quelle muss ein CI-Gate haben
   (wie `canonical.yaml` bereits), nicht auf manuelle Disziplin bauen.
3. **Reversibel & inkrementell** — kein Big-Bang; jeder der 4 Consumer muss einzeln,
   verifizierbar migrierbar sein, sonst bleibt ein Consumer auf einer toten Quelle.
4. **Coverage-Ehrlichkeit** — `github_repos.yaml` trägt Dinge, die `canonical.yaml`
   heute **nicht** hat (s. u.). Diese Lücken müssen VOR der Stilllegung geschlossen
   werden, nicht danach.

## Coverage-Delta (verifiziert 2026-07-14, nicht geschätzt)

`canonical.yaml` (53 Repos) deckt die aktiven Felder ab, die die Consumer brauchen —
je Repo `github` (owner/repo), `deployed`, `type`, plus `deploy`/`staging`-Blöcke.
Typverteilung: django 23, library 22, infra 2, fastapi/static/bot/python/other je 1–2.

**Was `github_repos.yaml` UNIQUE trägt und vor der Stilllegung migriert werden muss:**

| Lücke | Umfang | Betroffener Consumer |
|---|---|---|
| **68 Archive-Repos** | `canonical.yaml` schließt Archiv bewusst aus | `validate_repos.py` (Cross-Check gegen GitHub-Vollinventar) |
| **`django-lms-lite`** | 1 aktives Framework, in canonical **gar nicht** vorhanden | coach-hub-Dep (bereits als CI-Auth-Problem separat bekannt) |
| **Sektions-Gruppierung** (`django_apps`/`frameworks`/…) | canonical nutzt flaches `repos{}`-Dict + `type`-Feld statt Sektionen | `sync-workflows.sh`, `runner-health.yml` extrahieren nach Sektion, nicht nach `type` |

Die Sektions-Gruppierung ist rein mechanisch aus `type` ableitbar
(`type==django → django_apps`, `type∈{library,framework} → frameworks`), aber der
Ableitungscode existiert noch nicht.

## Considered Options

### Option A — canonical.yaml als alleinige SSoT, github_repos.yaml stilllegen (empfohlen)

Die 4 Consumer werden einzeln auf `canonical.yaml` (bzw. die generierte `repos.yaml`-View)
umgestellt; `github_repos.yaml` wird nach vollständiger Consumer-Migration nach
`registry/_archived/` verschoben. Coverage-Lücken (Archive-Liste, `django-lms-lite`)
werden vorher in `canonical.yaml` bzw. eine dedizierte `archived-repos.yaml` überführt.

- **Pro:** Ein Anspruch, ein Gate. Datenalter strukturell unmöglich (generiert).
- **Contra:** 4 Consumer-Migrationen + Lückenschluss; nicht trivial.

### Option B — github_repos.yaml aus canonical.yaml generieren (Zwei-Dateien, ein Ursprung)

`github_repos.yaml` bleibt als generierte View bestehen, wird aber aus `canonical.yaml`
erzeugt (wie `repos.yaml` heute), mit MANAGED-Header + Drift-Gate. Consumer bleiben
unverändert.

- **Pro:** Null Consumer-Änderung; kleinster Diff.
- **Contra:** Zementiert zwei Schema-Formate dauerhaft; der Generator muss die
  Sektions-Gruppierung + Archive-Liste + `django-lms-lite` mitführen — d. h. dieselben
  Lücken müssen ohnehin geschlossen werden, nur landen sie in einem Generator statt in
  einer Migration. Verlängert die „zwei SSoT sehen"-Verwirrung optisch.

### Option C — Status quo + Waiver (verworfen)

Nichts tun, Konflikt dokumentieren. Verworfen: genau das ist seit 2026-04 passiert,
der Snapshot altert weiter, `runner-health`/`sync-workflows` treffen zunehmend falsche
Entscheidungen.

## Decision Outcome

**Gewählt: Option A**, in reversiblen Phasen, jede mit eigenem verifizierbaren Gate.
Begründung gegen B: B löst dieselben Lücken, behält aber dauerhaft zwei Schemata —
das widerspricht Driver 1 (genau eine SSoT). Der einzige B-Vorteil (null Consumer-Diff)
wiegt die dauerhafte Doppel-Schema-Last nicht auf.

### Phasen (jede ein eigener PR, jede einzeln reversibel)

- **P0 — Lücken schließen (VOR jeder Consumer-Migration):**
  (a) Archive-Repos aus `github_repos.yaml.archive` in eine eigene, generierte
  `registry/archived-repos.yaml` überführen (oder als `lifecycle: archived` in
  canonical, falls das Schema es trägt — Entscheid im P0-PR); (b) `django-lms-lite`
  in `canonical.yaml` aufnehmen. **Gate:** `validate_repos.py` läuft grün gegen die
  neue Archiv-Quelle statt gegen `github_repos.yaml`.
- **P1 — `sync-workflows.sh`** auf eine kleine Ableitungsfunktion umstellen
  (`type→Sektion` aus `repos.yaml`). **Gate:** Symlink-Set vor/nach identisch
  (`--dry-run`-Diff == leer).
- **P2 — `runner-health.yml`** auf `repos.yaml` `deployed`+`github` umstellen.
  **Gate:** Runner-Liste vor/nach identisch.
- **P3 — `sync-drift-meter.yml`** auf `repos.yaml` umstellen. **Gate:** Drift-Report
  vor/nach identisch.
- **P4 — `validate_repos.py`** auf die neue Archiv-Quelle + `canonical.yaml` umstellen.
- **P5 — Stilllegung:** `github_repos.yaml` → `registry/_archived/github_repos.yaml.<datum>`;
  `check_registry_view_readers.py` aus dem Reader-Set entfernen; Header-Selbstanspruch
  gelöscht. **Gate:** `grep -rl github_repos.yaml` (ohne `_archived/`) == leer.

**Enforcement (Driver 2):** Nach P5 existiert genau eine Reader-Oberfläche; ein neuer
`grep`-Guard in `check_registry_view_readers.py` failt, sobald irgendein Nicht-archivierter
Pfad `github_repos.yaml` wieder liest — verhindert Rückfall.

## Consequences

**Positiv:** Eine SSoT, ein Gate, kein Datenalter; die 4 Consumer treffen fortan
Entscheidungen gegen aktuelle Daten. Das „zwei SSoT"-Muster ist strukturell (nicht nur
per Dokument) unmöglich gemacht.

**Negativ / Risiko:** 6 PRs statt 1; jeder Consumer-PR braucht einen echten Vorher/Nachher-
Diff-Beleg (nicht nur „CI grün"). Falls ein Consumer eine `github_repos.yaml`-Eigenheit
nutzt, die hier übersehen wurde, bricht dessen Migration — deshalb je Phase ein
Identitäts-Gate statt eines Aggregat-Checks.

**Nicht verifiziert / offene Restlücke:** Ob `sync-drift-meter.yml` und `validate_repos.py`
über die hier belegten Feld-Zugriffe hinaus weitere `github_repos.yaml`-Felder lesen, ist
nur per `grep` geprüft, nicht per Ausführung beider Tools im Vorher/Nachher — der billigste
weitere Check ist ein Dry-Run beider Tools in P3/P4 (dort als Gate verankert).

## Abgrenzung

Dieses ADR betrifft **nur** die Registry-Doppelquelle. Die ADR-021-§2.9-Port-Tabelle ist
eine **dritte**, manuell gepflegte Teilkopie derselben Daten (Ports), schon jetzt
unvollständig (~24 vs. 53 Einträge) — sie ist ein verwandter, aber separater SSoT-Drift
und wird hier bewusst nicht mitbehandelt (eigener, kleinerer Folge-PR: Tabelle durch einen
Generator-Verweis auf `ports.yaml` ersetzen).
