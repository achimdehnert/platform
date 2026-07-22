---
id: ADR-246
title: "genesor-Ingest Stufe 2: manifest-getriebener, dev-host-freier CI-Auto-Ingest (nightly)"
status: accepted
decision_date: 2026-06-16
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [iilgmbh, meiki-lra, bahn-sqf, ttz-lif]
domains: [klickdummy, genesor, ingest, ci]
supersedes: []
amends: [ADR-225]
depends_on: [ADR-225]
related: [ADR-211, ADR-213, ADR-215, ADR-216]
tags: [klickdummy, genesor, ingest, cross-repo, ci, automation]
scope:
  include_paths:
    - "docs/adr/ADR-246-*"
implementation_status: implemented
implementation_evidence:
  - "iil-pet-portal/.github/workflows/genesor-ingest.yml — nightly cron (17 3 * * *) aktiv seit 2026-06-17, grüner workflow_dispatch verifiziert (run 27667675206: 7 Repos vendored, Safety-Gate GRÜN, Promote erfolgt)"
  - "Manifest genesor-repos.yaml + Safety-Gate iil-pet-portal/scripts/genesor_diff_gate.py (Self-Test in CI, ADR-246 §8) vorhanden"
  - "GitHub-App-Auth (GENESOR_APP_ID/GENESOR_APP_PRIVATE_KEY, least-privilege contents:read) statt PAT — Plan-Punkt 5 äquivalent erfüllt"
  - "8765-Stale-Snapshot abgeschaltet — live TCP-Probe 88.99.38.75:8765 verifiziert 2026-07-09: connection refused (Plan-Punkt 7)"
---

# ADR-246 — genesor-Ingest Stufe 2: manifest-getriebener, dev-host-freier CI-Auto-Ingest (nightly)

| Attribut       | Wert                                                      |
|----------------|-----------------------------------------------------------|
| **Status**     | Accepted                                                  |
| **Scope**      | platform (cross-cutting: alle KD-Repos, cross-org)        |
| **Repo**       | platform (Entscheidung) · iil-pet-portal (Implementierung)|
| **Erstellt**   | 2026-06-16                                                |
| **Autor**      | Achim Dehnert                                             |
| **Amends**     | ADR-225 (aktiviert dessen deferred „Stufe 2")            |
| **Relates to** | ADR-211 (KD-Prozess), ADR-215 (Discovery-Registry), ADR-216 (iil.pet-Hosting), ADR-213 (Cross-Repo-Refs) |

## 1. Kontext

### 1.1 Ausgangslage
ADR-225 (Proposed) etablierte den **reproduzierbaren main-basierten Ingest** (Stufe 1):
`iil-pet-portal/scripts/regen-genesor-main.sh` legt ephemere git-worktrees am `origin/main`
jedes KD-Repos an, generiert die genesor-Übersicht (`python -m iil_klickdummy.lineage --genesor`),
vendored nach `kd/<repo>/`, Diff-Gate, dann manueller `commit + push` → GH-Pages-Deploy (R2,
`gh-pages.yml`) → `iil.pet/genesor` (CF-Access). **ADR-225 §5.4 hielt Stufe 2 — den CI-/manifest-
basierten Ingest (nightly, kein Dev-Host) — bewusst deferred.** Dieses ADR aktiviert und gestaltet Stufe 2.

### 1.2 Problem / Lücken (verifiziert 2026-06-16)
1. **Dev-Host-Abhängigkeit:** Der Ingest läuft nur dort, wo *alle* KD-Repos lokal ausgecheckt sind und
   `iil-klickdummy`-Source vorliegt. Ein neues KD (z. B. apo-hub:apocenna-portale) erscheint erst, wenn
   eine Person den Regen manuell fährt. → genesor ist so aktuell wie der letzte manuelle Lauf.
2. **Hardcoded Repo-Liste:** `REPOS=(…)` im Skript ist die einzige Quelle der Wahrheit, welche Repos
   ingestiert werden. Neue Repos = Skript-Edit. Kein deklaratives, reviewbares Manifest.
3. **Kein automatischer Safety-Gate:** Der Human-Diff-Gate fängt KD-Verluste heute manuell ab. Ohne ihn
   (Automatisierung) droht stiller KD-Verlust bei transienten Fehlern (Repo-main kurz kaputt, Clone-Fehler).
4. **Generator nicht paketiert:** `iil_klickdummy.lineage` liegt im `src`-Tree, nicht verlässlich im
   veröffentlichten PyPI-Paket → CI braucht einen definierten Bezugsweg.

### 1.3 Constraints
- **Cross-Org** (iilgmbh, meiki-lra, bahn-sqf, achimdehnert) — eine Repo-GitHub-Action reicht für den
  All-Repo-Checkout nicht (ADR-216); der Ingest muss zentral (iil-pet-portal) laufen und mehrere Orgs lesen.
- **Sperrvermerk** (bahn-sqf/pg-hub): nur mit Genehmigung; kein Bulk-Vendoring ([[pg-hub-db-mandat]]).
- **Seed-vs-live-Gate** (ADR-225 §5 Pkt 5): nur synthetische Daten dürfen auf iil.pet veröffentlicht werden.
- **„KD-auf-main"-Contract** (ADR-225 §2 Pkt 2) bleibt unverändert.
- **Fail-safe, nicht fail-open:** Automatik darf nie still KDs verlieren (ersetzt den Human-Diff-Gate).

## 2. Entscheidung

> Hinweis (REC-15): ADR-246 **hängt an der Annahme von ADR-225** (Stufe 1, derzeit Proposed). Beide werden
> in einen konsistenten Status gebracht (gemeinsam accepten oder ADR-246 explizit auf ADR-225-Accept gaten).

1. **Deklaratives Manifest als Governance-Quelle** `iil-pet-portal/genesor-repos.yaml` ersetzt die hardcoded
   `REPOS=()`. Schema je Eintrag: `org`, `repo`, `kd_path` (Default `klickdummy`), **`kd_id`** (stabile,
   pfad-entkoppelte Identität), `owner` (fachlich, für Alarme), **`data_class`** (`synthetic` Publish-Pflicht,
   Pkt 7), `enabled`, `sperrvermerk`, **`last_seen_max_age`** (Stale-SLA, Pkt 5), optional `previous_kd_id`/
   `path_moved_from` (Umbenennung/Move). Aufnahme/Deaktivierung/Move = **Manifest-PR**. **Manifest-Validierung
   im CI** (ungültiger `kd_path`, Dubletten, falsche Org, versehentlich `enabled`-Sperrvermerk → Fail).

2. **Dev-host-freier Ingest per ephemerem Shallow-Clone in CI** (`git clone --depth 1 --branch main`) in einen
   Temp-Scan-Root → **unveränderter** Generator mit `--repos-root <temp>` (reuse). Gegen die ADR-225-erwogene
   Contents-API: billiger, reuse-t den Mechanismus 1:1, CI ist ephemer. **Betriebsparameter verbindlich:**
   begrenzte Parallelität, Per-Repo-Timeout, Retry mit Backoff, Fehlerklassifikation (transient vs hart),
   strukturiertes Logging.

3. **Candidate → Gate → Promote** (statt Direkt-Commit): der Lauf erzeugt einen vollständigen Candidate-Stand
   + `ingest-report.json`; **nur wenn alle harten Gates grün sind**, wird er nach `main` promoted → der
   bestehende `gh-pages.yml` (R2) deployt unverändert. **Concurrency-Lock** (`group: genesor-ingest`,
   cancel-in-progress:false), Bot-Commit-Konvention, **kein Commit bei 0-Diff**. Kein neuer Deploy-Pfad.

4. **Safety-Gate als Zustandsmaschine je KD** (ersetzt den Human-Diff-Gate — kritischste Entscheidung).
   Status: `fresh` · `unchanged` · `transient_failed_kept` · `spec_missing_blocked` · `realdata_blocked` ·
   `disabled_removed` · `stale_blocked`.
   - **Transienter Fehler ⇒ `transient_failed_kept`**: letzter Stand behalten, aber als **sichtbarer Status**
     (kein stiller Normalzustand) + Warnung.
   - **Echter Spec-Wegfall bei `enabled`-Repo ⇒ `spec_missing_blocked`**: Lauf **failt** (kein Promote).
     Identität über **`kd_id`**, nicht Verzeichnis-Diff → Umbenennung/Move (`previous_kd_id`/`path_moved_from`)
     gilt **nicht** als Verlust.
   - **Bewusste Entfernung NUR per Manifest-PR (`enabled:false`)** → `disabled_removed`. **Kein** pauschaler
     `allow_removal`-Dispatch-Bypass: `workflow_dispatch` dient ausschließlich dem erneuten Lauf, nie der Entfernung.
   - **Global-Failure-Gate:** sind `> 20 %` der Repos **oder** `≥ 3 Orgs` nicht klonbar/generierbar, **blockt der
     gesamte Publish** (statt „Rest publizieren") — verhindert Mischzustand bei Token-/Netz-/Org-Ausfall.

5. **Stale-SLA:** `transient_failed_kept` ist nur begrenzt fail-safe. Überschreitet ein KD `last_seen_max_age`
   (Default z. B. 7 Tage / 7 erfolglose Zyklen), wird er `stale_blocked` bzw. im Output sichtbar als `stale`
   markiert (Pkt 8) — „alt aber sichtbar" nur, solange der Zustand transparent ist.

6. **Cross-Org-Auth: GitHub-App-Installation-Tokens als Zielarchitektur.** Bevorzugt eine GitHub App **pro Org**
   (oder Repo-Gruppe) mit nur `contents:read` auf die freigegebenen Manifest-Repos → kurzlebige Installation-Tokens
   je Lauf (kleiner Blast-Radius, Rotation/Audit pro Org). Fine-grained PAT nur als **Übergangslösung**.
   Sperrvermerk-Repos außerhalb jedes Token-Scopes (Defense-in-Depth). **Kein** Enterprise-/Admin-PAT.

7. **Daten-Souveränität: Hard-Block + Contract-Metadatum.** (a) `data_class: synthetic` wird **Pflichtfeld** des
   KD-Contracts (ADR-211/225); fehlt es oder `≠ synthetic` ⇒ KD-Publish blockiert. (b) Der CI-Realdaten-Scan
   (Mandantennamen-Allowlist) ist **Zusatzverteidigung**; ein Treffer ⇒ **gesamter Lauf blockiert**
   (`realdata_blocked`), bis geprüft ist, ob bereits vendored Artefakte betroffen sind — nicht nur das Repo ausschließen.

8. **Maschinenlesbarer Ingest-Status:** je Lauf `ingest-report.json` (Manifest-Version, Source-Commit je Repo,
   Status je KD, Fehlertyp, letzter erfolgreicher Stand, Generator-Version, Gate-Entscheidung) als Artefakt **und**
   publiziert als `genesor/ingest-status.json`. Da Generator/Skin out-of-scope sind, ist die `fresh/stale/blocked`-
   Sichtbarkeit mindestens maschinenlesbar verfügbar (sichtbares UI-Overlay = spätere Generator-Erweiterung).

9. **Sperrvermerk-Aktivierung mit Zusatz-Approval:** ein Sperrvermerk-Repo `enabled` zu setzen erfordert über den
   Manifest-PR hinaus ein **zweites Gate** (CODEOWNERS/Approver-Gruppe bzw. Feld `approved_for_genesor: true` mit
   dokumentierter Genehmigung) — ein einfacher Manifest-PR darf vertrauliche Artefakte nicht versehentlich sichtbar machen.

10. **Generator-Packaging verbindlich:** bevorzugt `lineage` ins veröffentlichte iil-klickdummy-PyPI-Paket **+
    Lockfile** (reproduzierbar inkl. Deps); Git-Tag-Pin nur als dokumentierte Übergangslösung. Nie `@main`.

11. **Hotfix-Pfad:** Nightly + `workflow_dispatch` ist Default; der Dispatch ist der **dokumentierte Sofortlauf**
    für kritische Fälle (Removal nach Manifest-PR-Merge, Sperrvermerk-Korrektur, Daten-Souveränitäts-Vorfall).
    Event-getriebener `repository_dispatch` bei Merge bleibt späteres Inkrement (Nicht in Scope).

## 3. Betrachtete Alternativen

| Option | Bewertung |
|---|---|
| **Status quo (manueller Dev-Host-Regen)** | ❌ — genau das Problem; nicht skalierbar, nicht stabil-evolvierend. |
| **GitHub Contents-API je Mockup-Tree** (ADR-225-Erwägung) | ⚠️ — teuer für ganze Trees, Rate-Limit-anfällig; verworfen zugunsten Shallow-Clone. |
| **Pro-KD-Repo-Action pusht zu iil-pet-portal** (verteilt) | ❌ — N Repos × Cross-Org-Push-Rechte auf iil-pet-portal; Koordinations-/Auth-Sprawl; widerspricht „zentral" (ADR-216). |
| **Nur ADR-215-Discovery-Push (Orchestrator-Registry)** | ⚠️ — anderer Konsument (`klickdummy-search`, pgvector); ersetzt **nicht** die lineage-HTML-Übersicht auf iil.pet. Komplementär, nicht Ersatz. |
| **Manifest + Shallow-Clone + zentraler nightly-CI + Safety-Gate (gewählt)** | ✅ — dev-host-frei, deklarativ, reuse-t Generator + bestehenden Deploy, fail-safe. |

## 4. Begründung im Detail
Der Generator und der Deploy (`gh-pages.yml`) funktionieren bereits; die einzige manuelle, drift-anfällige
Stelle ist die **Beschaffung der Quell-Specs** (Worktrees am Dev-Host). Stufe 2 ersetzt nur diese eine Stelle
durch Manifest + Shallow-Clone-in-CI und macht den bisher menschlichen Diff-Gate als **fail-safe Automatik**
explizit. Damit wird genesor zur **stabilen, stetig wachsenden Basis** (Ziel des Auftraggebers): jeder KD,
der auf `main` seines Repos liegt und dessen Repo im Manifest steht, erscheint **automatisch** über Nacht —
ohne dass jemand einen Dev-Host bemüht oder ein Skript editiert.

## 5. Implementation Plan
1. **Manifest** `iil-pet-portal/genesor-repos.yaml` aus heutiger `REPOS=()`-Liste ableiten (inkl. `kd_path`
   für meiki-hub-Sonderpfad), Sperrvermerk-Repos `enabled:false`.
2. **`regen-genesor-main.sh` refactoren**: Repo-Quelle = Manifest; Beschaffung über austauschbaren
   „provider" (lokal-worktree | ci-shallow-clone). Verhalten bei Repo-Fehler = „behalten" (Pkt 4).
3. **Safety-Gate-Skript** (`scripts/genesor-diff-gate.py`): vergleicht regenerierten Stand gegen committeten,
   blockt Netto-KD-Verlust, gibt Report aus (für CI-Log + Issue).
4. **CI-Workflow** `genesor-ingest.yml`: nightly + dispatch; Token `GENESOR_INGEST_TOKEN`; install pinned
   iil-klickdummy; run refactored regen (ci-Provider); Safety-Gate; commit+push `main`; Alarm bei Warnungen.
5. **Token bereitstellen**: fine-grained PAT/App (`contents:read` auf Manifest-Repos), Secret setzen.
6. **lineage-Packaging** klären (PyPI-Inklusion vs Git-Pin) und in CI pinnen.
7. **8765-Stale-Snapshot** (ADR-225) endgültig abschalten, sobald nightly stabil läuft.
8. `/klickdummy`-Skill-Hinweis aktualisieren: „neues KD-Repo → ins genesor-repos.yaml-Manifest aufnehmen".

## 6. Risiken
- **Stiller KD-Verlust** bei Automatik → primär adressiert durch fail-safe Safety-Gate (Pkt 4); ohne ihn kein Merge.
- **Cross-Org-Token-Leak**: least-privilege fine-grained PAT/App, kein Admin-PAT; Secret nur in iil-pet-portal;
  Sperrvermerk-Repos außerhalb des Scopes.
- **Generator-Drift** (`@main`-Install): Versions-Pin verpflichtend (Lehre [[feedback_sharedci_tag_stale_vs_platform_main]] sinngemäß: Pin ≠ main).
- **Nightly-Lärm**: Alarm nur bei echten Warnungen/Blocks, nicht bei No-op-Läufen (kein Commit wenn 0 Diff).
- **Seed-vs-live-Heuristik** kann false-negativ sein → bleibt Verantwortung des „KD-auf-main"-Contracts (Autor),
  CI-Scan ist zusätzliche Verteidigung, kein Ersatz.

## 7. Konsequenzen
### 7.1 Positiv
- genesor wird **dev-host-frei, deklarativ und selbst-aktualisierend** (nightly) — stabile, wachsende Basis.
- Neues KD-Repo = ein Manifest-PR statt Skript-Edit + manueller Lauf.
- Auto-Ingest ist **fail-safe** (verliert nie still KDs) — stärker als der heutige manuelle Diff-Gate.
### 7.2 Trade-offs
- Latenz bis zu ~1 Nacht (statt sofort) — per `workflow_dispatch` jederzeit manuell triggerbar.
- Ein zusätzliches Cross-Org-Token + dessen Lifecycle (Rotation).
### 7.3 Nicht in Scope
- Der lineage-Generator selbst / Skin-System (ADR-211/216).
- ADR-215-Discovery-Registry/`klickdummy-search` (komplementär, eigener Konsument).
- `repository_dispatch`-Push aus KD-Repo-CIs bei Merge (mögliche spätere Latenz-Optimierung, eigenes Inkrement).

## 8. Validation Criteria

Über den Happy-Path hinaus werden folgende Szenarien getestet (REC-16):

- **Happy-Path:** neues KD-auf-main (Manifest-`enabled`) erscheint nach nightly **ohne** Dev-Host-Aktion
  (Beweis: apo-hub:apocenna-portale via CI statt manuellem Regen reproduziert).
- **Einzel-Repo unerreichbar:** dessen KDs bleiben (`transient_failed_kept`, sichtbar), Lauf warnt, Rest promoted.
- **Globaler Ausfall** (>20 % Repos / ≥3 Orgs / Token tot): **gesamter Publish blockiert**, kein Mischzustand.
- **Echter Spec-Wegfall** bei `enabled`-Repo: Lauf **failt** (`spec_missing_blocked`), kein Promote.
- **Umbenennung/`kd_path`-Move** (`previous_kd_id`/`path_moved_from`): **kein** Fehl-Verlust, kein Doppel-KD.
- **Stale:** nach `last_seen_max_age` → `stale_blocked`/sichtbar `stale`.
- **Realdata-Treffer / fehlendes `data_class: synthetic`:** KD bzw. Lauf blockiert (`realdata_blocked`).
- **Sperrvermerk versehentlich `enabled` ohne Zusatz-Approval:** Manifest-Validierung **failt**.
- **Token-Scope:** nur `contents:read` auf Manifest-Repos, kein Sperrvermerk-Repo im Scope.
- **Paralleler Lauf:** Concurrency-Lock greift, keine Race-Condition; **0-Diff-Lauf:** kein Commit/Deploy.
- **`ingest-report.json`** je Lauf vollständig + `genesor/ingest-status.json` publiziert.

## 9. Glossar
| Begriff | Bedeutung |
|---|---|
| **Stufe 2** | dev-host-freier, CI-/manifest-getriebener genesor-Ingest (dieses ADR; ADR-225 §5.4) |
| **Manifest** | `genesor-repos.yaml` — deklarative Liste der zu ingestierenden KD-Repos |
| **Safety-Gate** | automatischer Blocker gegen Netto-KD-Verlust (ersetzt den Human-Diff-Gate) |
| **Sperrvermerk** | Repos mit Vertraulichkeitsauflage (bahn-sqf/pg-hub), nur mit Genehmigung ingestierbar |
| **Shallow-Clone** | `git clone --depth 1 --branch main` — flacher, ephemerer Klon in CI |
| **fail-safe** | Fehlerverhalten, das den sicheren Zustand bewahrt (hier: lieber nicht publizieren als KDs verlieren) |

## 10. Referenzen
- platform:ADR-225 (genesor-Ingest Stufe 1, wird hier amended) · platform:ADR-216 (iil.pet-Hosting)
- platform:ADR-211 (KD-Prozess) · platform:ADR-215 (Discovery-Registry) · platform:ADR-213 (Cross-Repo-Refs)
- Implementierung: `iil-pet-portal/scripts/regen-genesor-main.sh`, `.github/workflows/gh-pages.yml`
- Verifizierter Stufe-1-Lauf (apo-hub aufgenommen): 2026-06-16

## 11. Changelog
- 2026-06-16: Initial (Proposed). Aktiviert ADR-225 §5.4 (Stufe 2). Entworfen nach Verifikation der
  Stufe-1-Mechanik (manueller Regen brachte apo-hub:apocenna-portale live auf iil.pet/genesor).
- 2026-06-16: Externe LLM-Zweitmeinung eingearbeitet (16 RECs, alle [valid]). Wesentliche Härtungen:
  Safety-Gate als Zustandsmaschine mit `kd_id`-Identität + Global-Failure-Gate (REC-1/5/6); Candidate→Gate→Promote
  statt Direkt-Commit (REC-1/Ansatz 1); Stale-SLA (REC-2); Manifest als Governance-Quelle (REC-3); `allow_removal`
  -Bypass gestrichen, Entfernung nur per Manifest-PR (REC-4); GitHub-App-Tokens als Zielarchitektur (REC-7);
  Realdata = Hard-Block + `data_class: synthetic`-Pflicht (REC-9); `ingest-status.json` (REC-10);
  Concurrency/Shallow-Clone-Betriebsparameter (REC-11/12); Sperrvermerk-Zusatz-Approval (REC-8); Packaging+Lockfile
  (REC-14); Hotfix-Pfad (REC-13); ADR-225-Abhängigkeit explizit (REC-15); Validation gehärtet (REC-16).
- 2026-06-16: **Accepted** (gemeinsam mit ADR-225, das hiermit ebenfalls accepted wird). Stufe-2-Design entscheidungsreif; Implementierung (Manifest, Safety-Gate-Skript, `genesor-ingest.yml`, GitHub-App-Token) folgt als Build.
