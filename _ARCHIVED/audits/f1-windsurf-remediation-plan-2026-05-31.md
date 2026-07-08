# F1 Remediation Plan — `.windsurf` typechange (korrigiert, origin-basiert)

> Folge-Artefakt zu `audits/platform-audit-2026-05-30.md` (Finding F1) und PR platform#359.
> **Korrektur 2026-05-31:** Der ursprüngliche F1-Scan + Pilot (illustration-hub#4) liefen gegen
> **stale lokale Working-Trees** (illustration-hub war 12 Commits hinter `origin/main`). Pilot
> geschlossen. Dieser Plan misst ausschließlich gegen **frisch gefetchtes `origin/main`**.

## 1. Problem (korrekt)

Synced `.windsurf/workflows/*`-Dateien sind auf `origin/main` als **Regular Files (mode 100644)**
getrackt, werden aber lokal von `scripts/sync-workflows.sh` (`ln -s`) zu **Symlinks** → `typechange`
("T") = dauerhaft dirty, sobald ein Entwickler den lokalen Sync laufen lässt.

### Root Cause (nicht kosmetisch)
Zwei widersprüchliche Sync-Mechanismen:
| Mechanismus | Tut | git-Effekt |
|---|---|---|
| lokal `scripts/sync-workflows.sh` | `ln -s` → Symlinks | Disk = Symlink |
| CI `.github/workflows/sync-workflows-to-repos.yml:248` (trigger: jeder push→main) | committet Voll-Inhalt als Regular File via GitHub-API | git = 100644 |

→ **Cleanup-PRs sind Sisyphos**: Der nächste Platform-Workflow-Change re-committet Regular Files.

## 2. Pflicht-Sequenz (Reihenfolge ist nicht optional)

1. **Distributor abschalten** — `sync-workflows-to-repos.yml` retiren (ADR-230-Rollout-Item, siehe
   separates Briefing). ADR-230 (accepted) mandatiert *kein per-Repo `.windsurf`* (REC-10).
   **Ohne diesen Schritt zuerst zerfällt jeder Sweep wieder.**
2. **Einmal-Sweep** (dieser Plan) gegen `origin/main`.
3. **Stale lokale Checkouts syncen** (Audit-F3-Hygiene) → killt verbleibendes Phantom-Local-Dirty.

## 3. Sweep-Design

**Untrack-Kandidat** = getrackter `.windsurf`-Pfad auf `origin/main` mit **mode 100644** UND
existierendem **platform-Pendant** (`platform/.windsurf/<pfad>`). → das ist „synced".
**Behalten:** Pfade ohne platform-Pendant (repo-eigen) — real nur `project-facts.md`.
**Nie anfassen:** mode-120000 (Symlink-getrackt, kein typechange) bleibt bis ADR-230-Rollout;
`platform` selbst (SSoT).

### Klasse A — blanket `.windsurf/` in `.gitignore`, 0 repo-eigen → trivial
`git rm --cached <synced>` genügt, `.gitignore` deckt ab. **29 Repos:**
137-hub, aifw, ausschreibungs-hub, authoringfw, billing-hub, cad-hub, coach-hub, dev-hub,
illustration-fw, illustration-hub, learnfw, learn-hub, nl2cad, odoo-hub, outlinefw, pptx-hub,
promptfw, recruiting-hub, researchfw, research-hub, risk-hub, testkit, trading-hub, travel-beat,
ttz-hub (62 Dateien!), wedding-hub, weltenfw, weltenhub, writing-hub.
(meist 5 Dateien/Repo; ttz-hub 62.)

### Klasse C — kein blanket-`.gitignore` → `git rm --cached` + präzise `.gitignore`-Zeilen
Pro untrackten Pfad eine exakte `.gitignore`-Zeile (Verzeichnis-Level würde künftige repo-eigene
Dateien über-ignorieren). **16 Repos:**
bahn-hub (66), bfagent (5), design-hub (4), dms-hub (5), gaeb-toolkit (32, +project-facts.md behalten),
iil-adrfw (1), iil-adrfw-repo (1), iil-codeguard (63), iil-enrichment (63), iil-ingest (63),
iil-reflex (63), meiki-hub (7, +project-facts.md behalten), onboarding-hub (63), pg-hub (62),
sqf-hub (62), tax-hub (63).

## 4. Ausführung pro Repo (1 Branch + 1 PR/Repo, Review via Windsurf)
```
git fetch origin main
git switch -c chore/untrack-synced-windsurf origin/main   # IMMER von origin, nie stale lokal
# <synced 100644-Pfade> via git rm --cached
# Klasse C: präzise .gitignore-Zeilen anhängen
git commit -m "chore: stop tracking synced .windsurf (platform audit F1)"
```
**Verifikation je Repo (Gate):** `git status --porcelain .windsurf` == leer · 0 typechange ·
0 untracked · `project-facts.md` weiterhin getrackt (wo vorhanden) · Symlinks on-disk unberührt.

## 5. Skript
`tools/f1-windsurf-sweep.sh` — origin-basiert, synced-only, **Dry-Run-Default** (`F1_APPLY=1`
zum Anwenden, `F1_PUSH=1` für push+PR). Läuft nie gegen `platform`.

## 6. Rollback
Reversibel: PR je Repo schließen ODER `git revert`. `rm --cached` fasst Worktree nicht an;
Symlinks/Dateien on-disk bleiben. Kein Datenverlust (Inhalt lebt in platform-SSoT + git-History).
