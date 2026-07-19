---
description: KD-Sitemap generieren/aktualisieren + optional in genesor-repos.yaml wiring + iil.pet/kd/-Link anzeigen
mode: write
---

# /kd-sitemap — Klickdummy-Sitemap generieren + auf iil.pet publizieren

> **Wann:** Ein oder mehrere KDs sind im Repo gebaut (`/klickdummy`) und du willst die
> **repo-weite Hierarchie/Sitemap** (`klickdummy/sitemap/index.html` + `kd-tree.json`)
> erstmalig erzeugen ODER auf den neuesten Stand bringen, und den Link auf `iil.pet/kd/`
> sehen. **Idempotent** — läuft identisch, egal ob noch nichts existiert oder schon eine
> ältere Sitemap vorliegt (aktualisiert dann einfach).
> **Wann NICHT:** einen neuen KD **bauen** → `/klickdummy`. KD **prüfen/UX-kritisieren**
> → `/kd-review`. Diese Schritte hier laufen **danach**, einmal pro Repo (nicht pro KD).

## Verwendung

```
/kd-sitemap [<repo>] [--no-push] [--no-ingest]
```

| Argument | Pflicht | Default | Bedeutung |
|---|---|---|---|
| `<repo>` | nein | aktuelles Repo | Ziel-Repo (Slug) |
| `--no-push` | nein | (aus) | nur lokal generieren + diffen, nicht committen/pushen |
| `--no-ingest` | nein | (aus) | `genesor-ingest.yml` nicht per `workflow_dispatch` anstoßen — auf nächtlichen Cron warten |

## Step 0: Repo-Kontext aus project-facts.md (PFLICHT — kein Hardcoding)

Aus `.windsurf/rules/project-facts.md` des Ziel-Repos: `REPO_OWNER/REPO_NAME`. Der
iil-pet-portal-Pfad (`~/github/iil-pet-portal`) und dessen Manifest (`genesor-repos.yaml`)
sind fix (SSoT, `platform:ADR-246`) — kein weiterer Hardcoding-Bedarf dort.

## Step 1: Ist-Zustand feststellen (macht den Skill idempotent)

- `klickdummy/sitemap/index.html` vorhanden? → **Update-Pfad**, sonst **Erstanlage-Pfad**
  (beide Pfade laufen technisch identisch, s. Step 4 — der Unterschied ist nur die Meldung).
- `grep -n "klickdummy-sitemap:" Makefile` → Target vorhanden? Wenn nein: Step 2 ausführen.
  Wenn ja: Step 2 überspringen.
- `grep -n "KLICKDUMMY_VENV" Makefile` → welcher Venv-Pfad wird von den bestehenden
  `klickdummy-i1..i4`-Targets genutzt? **Diesen wiederverwenden**, keinen neuen erfinden.

## Step 2: Makefile-Target ergänzen (nur bei Erstanlage)

```makefile
klickdummy-sitemap: ## KD-Sitemap + kd-tree.json neu generieren
	@$(KLICKDUMMY_VENV)/bin/klickdummy-gen-sitemap . <repo>:<lokale-ADR-Ref-oder-Issue> <repo>
```

`<lokale-ADR-Ref-oder-Issue>`: existierendes lokales KD-ADR suchen
(`grep -rl klickdummy docs/adr/` bzw. `ls docs/adr/ | grep -i klickdummy`) und referenzieren;
sonst Fallback `<repo>:klickdummy`.

## Step 3: Generator-Venv aktuell halten (löst Issue iilgmbh/iil-klickdummy#181-Klasse)

```bash
<KLICKDUMMY_VENV>/bin/pip install --upgrade iil-klickdummy
<KLICKDUMMY_VENV>/bin/pip show iil-klickdummy | grep Version
```

Repos mit einer Versions-Obergrenze im Makefile (`iil-klickdummy>=1.27,<2.0` o.ä.) holen
automatisch die neueste erlaubte Version — **kein manuelles Pinnen** nötig, aber die
tatsächliche Version nach dem Upgrade **verifizieren** (nicht nur den Install-Exit-Code).

## Step 4: Generieren (identisch für Erstanlage UND Update)

```bash
make klickdummy-sitemap
```

Danach **Knotenzahl belegen**, nicht nur "Exit 0" als Erfolg werten:

```bash
python3 -c "
import json
d = json.load(open('klickdummy/_shared/kd-tree.json'))
print('nodes:', len(d.get('nodes', {})), 'roots:', len(d.get('roots', [])))
"
```

- `nodes: 0` bei vorhandenen Specs → Generator erkennt das Renderer-Dateiformat nicht
  (bekannte Klasse: `shell.html` vs. `index.html`, Issue #181 — mit `iil-klickdummy>=1.32.2`
  behoben). Als **Befund** melden, nicht stillschweigend als Erfolg verbuchen.
- `roots: 0` bei `nodes > 0` ist **kein Bug**: kommt vor, wenn keine Spec `spec_role: root`
  setzt. Getrennt vom Renderer-Problem behandeln — nicht in denselben Befund mischen.

## Step 5: Auto-Deploy-Preflight (PFLICHT vor jedem Push/Commit-Vorschlag)

`.github/workflows/*deploy*.yml` im Ziel-Repo prüfen: löst ein Push auf `main` (bzw. der
Merge dieses PRs) einen echten Produktions-Deploy aus? `paths-ignore` **exakt** lesen — deckt
es `klickdummy/` ab, oder nur `.md`/`docs` (bekannte Lücke, 🌀
`agent_memory_search(query="trading-hub auto deploy on merge klickdummy paths-ignore")`)?
Ergebnis **explizit im Output benennen** (Step Output-Format, Feld `Auto-Deploy`) — nie
stillschweigend commiten/pushen ohne diese Zeile.

## Step 6: Diff prüfen + committen (übersprungen mit `--no-push`)

- Kein Diff (`git diff --exit-code -- klickdummy/sitemap klickdummy/_shared`) → **"bereits
  aktuell"** melden, nichts committen (das ist der Update-Pfad-Erfolgsfall, kein Fehler).
- Diff vorhanden → über den verbindlichen Entry Point isoliert arbeiten (ADR-233, kein Edit
  im geteilten Haupt-Tree):
  ```bash
  wt=$(bash platform/tools/repo-session.sh start <repo-pfad> --task "kd-sitemap")
  cd "$wt"
  # Step 2-4 hier wiederholen falls noch nicht in diesem Worktree gelaufen
  git add klickdummy/sitemap klickdummy/_shared/kd-tree.json klickdummy/_shared/kd-tree.js Makefile
  git commit -m "feat(klickdummy): Sitemap generieren/aktualisieren (klickdummy-gen-sitemap)"
  git push -u origin HEAD
  gh pr create --title "..." --body "..."
  ```
  Merge **nicht selbst ausführen**, wenn Step 5 ein Auto-Deploy ergab — das ist ein eigenes
  Freigabe-Gate (🌀 `prod-deploy-preflight-before-merge-approval`).

## Step 7: genesor-Wiring prüfen/ergänzen (nur wenn Sitemap gemergt ist)

```bash
grep "repo: <repo>," ~/github/iil-pet-portal/genesor-repos.yaml
```

- Eintrag vorhanden + `enabled: true` → nichts zu tun, weiter zu Step 8.
- Kein Eintrag → **eigenen PR** gegen `iil-pet-portal/genesor-repos.yaml` vorschlagen (SSoT,
  `platform:ADR-246` — Zeile hinzufügen, **nicht** Skript editieren). Dieser PR ist getrennt
  vom Sitemap-PR aus Step 6 — anderes Repo, eigene Freigabe.

## Step 8: Publish anstoßen (übersprungen mit `--no-ingest`)

```bash
gh workflow run genesor-ingest.yml -R iilgmbh/iil-pet-portal
```

Ohne `--no-ingest` und ohne explizite Freigabe **nicht ausführen** — das ist ein Publish-Schritt
(GitHub-Pages-Deploy auf `iil.pet`, Gate 4 `Scope-Eskalation/Publish`). Alternative: nächtlicher
Cron (`17 3 * * *`) holt es automatisch ab, kein manueller Trigger nötig, nur langsamer.

## Step 9: Link anzeigen

```
iil.pet/kd/<repo>/<kd_path>/sitemap/
```

`<kd_path>` aus dem Manifest-Eintrag (Step 7), Default `klickdummy`. **Cloudflare Access**
sitzt davor — der Link ist nicht durch diesen Skill/Playwright verifizierbar, nur durch den
User im eigenen authentifizierten Browser (🌀 `cloudflare-not-a-test-tool`,
`genesor-live-verify`).

## Output-Format

```
== /kd-sitemap <repo> ==
  Pfad:  <Erstanlage | Update>
  Venv:  <pfad> · iil-klickdummy <version>

Generierung
  nodes: <n> · roots: <n>   [Befund: <shell.html-Klasse|spec_role-Klasse|keiner>]

Auto-Deploy: <JA — <workflow> triggert auf klickdummy/ | NEIN — <grund>>

Git
  Diff:   <keiner (bereits aktuell) | <n> Dateien>
  PR:     <url | — (--no-push)>
  Merge:  <NICHT ausgeführt — Freigabe-Gate | n/a>

genesor-Wiring
  Manifest: <bereits enabled | PR vorgeschlagen: <url>>
  Ingest:   <workflow_dispatch ausgelöst | nächtlicher Cron (03:17) | — (--no-ingest)>

Link (nicht automatisiert verifizierbar — Cloudflare Access)
  iil.pet/kd/<repo>/<kd_path>/sitemap/
```

## Anti-Patterns

- ❌ **Tag/Commit auf stale lokalem Main taggen/committen ohne `origin/main` zu verifizieren**
  — Worktree über `repo-session.sh` IMMER von `origin/main` frisch ableiten (ADR-233), nie
  vom evtl. veralteten Haupt-Tree-HEAD.
- ❌ **`nodes > 0` als Beweis werten ohne den JSON tatsächlich zu parsen** — Exit-Code 0 allein
  belegt nicht, dass Specs gefunden wurden (genau der Issue-#181-Fehlermodus).
- ❌ **Merge ausführen, wenn Step 5 Auto-Deploy ergab** — eigenes Freigabe-Gate, nicht implizit
  im "push"-Schritt mit erledigen.
- ❌ **Über iil.pet/Cloudflare "verifizieren"** — Access-Wand, kein Prüfmittel (wie `/kd-review`).
- ❌ **Genesor-Manifest-PR und Sitemap-PR in einem PR mischen** — zwei Repos, zwei Freigaben.
- ❌ **`--no-ingest` ignorieren und trotzdem `workflow_dispatch` auslösen** — das ist der
  tatsächliche Publish-Schritt (Gate 4), nicht optional wegdenken.

## 🌀-Memory-Discovery-Pfad

Lokale CC-Memory zuerst, dann Orchestrator. Reale Einträge (iil-klickdummy):
- `prod-deploy-preflight-before-merge-approval` — Auto-Deploy-Check vor JEDER Merge-Freigabe
- `trading-hub-auto-deploy-on-merge` — `paths-ignore` deckt oft nur `.md`/docs, nicht `klickdummy/`
- `klickdummy-adoption-needs-ci-gate` — CI-Job-Verdrahtung bei Erstadoption (verwandtes Muster)
- `cloudflare-not-a-test-tool` / `genesor-live-verify` — iil.pet sitzt hinter Cloudflare Access
- `klickdummy-gen-version-drift` — stale `.venv-klickdummy` färbt Ergebnisse falsch

## Bezug

- `platform:ADR-211` — Klickdummy-Cookbook (Sitemap-Generator-Herkunft, S14 Rev 24)
- `platform:ADR-246` — genesor-Ingest-Architektur (Manifest-SSoT, nightly Cron)
- `iilgmbh/iil-klickdummy#181` — Renderer-Erkennungs-Fix (`shell.html`), ab v1.32.2
- Pipeline: `/kd-scout` (entscheiden) → `/klickdummy` (bauen) → `/kd-review` (verifizieren)
  → **`/kd-sitemap`** (publizieren, einmal pro Repo statt pro KD)

## Dogfood-Tests (Pflicht-Review-Gate per `claude-skills.md`)

### Test 1 — Erstanlage (apo-hub, noch keine Sitemap)

```
/kd-sitemap apo-hub
```
**Erwartung:** Makefile-Target ergänzt, `nodes > 0` nach Generierung, Auto-Deploy-Status
benannt, PR erstellt (nicht gemergt), genesor-Manifest bereits `enabled: true` (kein
zweiter PR nötig) — Ingest-Trigger nur mit expliziter Freigabe.

### Test 2 — Update-Pfad (repo mit bereits existierender Sitemap)

```
/kd-sitemap risk-hub
```
**Erwartung:** kein Makefile-Edit (Target existiert), Generierung läuft, "bereits aktuell"
falls kein Diff — kein unnötiger Commit/PR.

### Test 3 — `--no-push` (nur lokal prüfen)

```
/kd-sitemap coach-hub --no-push
```
**Erwartung:** `nodes`/`roots`-Befund inkl. der bekannten `spec_role`-Lücke (coach-hub#44)
gemeldet, kein Commit/Push/PR.

## Changelog

- 2026-07-15: Initial. Entstanden aus dem KD-Sitemap-Rollout über 8 Repos (trading-hub#153,
  tax-hub#68, dev-hub#140, dms-hub#15, research-hub#50, coach-hub#45, pptx-hub#42,
  onboarding-hub#13) + dem dabei gefundenen und gefixten Generator-Bug
  (iilgmbh/iil-klickdummy#181, `shell.html`-Renderer-Konvention, ab v1.32.2). Der manuelle
  6-Schritt-Ablauf (Makefile-Target, Venv-Upgrade, generieren, Auto-Deploy-Preflight, PR,
  genesor-Wiring, Ingest-Trigger) wurde als zu fehleranfällig/umständlich für Handarbeit
  eingestuft (User-Feedback: "zu kompliziert") und hier als idempotenter Skill kodifiziert —
  Erstanlage und Aktualisierung laufen identisch (Step 1 unterscheidet nur die Meldung).
