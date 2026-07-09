---
id: ADR-265
title: "Verteilte Symlink-Ziele fleet-weit aus git untracken (.gitignore) statt die Symlinks zu committen"
status: accepted
decision_date: 2026-07-04
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [iilgmbh]
scope: platform
related: [ADR-230, ADR-233, ADR-242]
tags: [git-hygiene, symlink, distribution, windsurf, cc-first, fleet-pattern, dirty-tree]
implementation_status: implemented
---

# ADR-265 — Verteilte Symlink-Ziele fleet-weit aus git untracken statt committen

> **Rev 4 (2026-07-05): adversariales Review verarbeitet.** Review-Verdikt „Überarbeiten";
> Orchestrator-Triage geerdet am Code (Volltext + Triage-Tabelle:
> [`reviews/review-adr-265-2026-07-05.md`](reviews/review-adr-265-2026-07-05.md)). Kern:
> **REC-5a (Dry-Run fehlt) ist REFUTED** — `--dry-run` existiert vollständig
> (`scripts/sync-workflows.sh:9,124,129,173–211,305`); **AD-2 „hoch"→mittel**, weil das Skript
> `SKIP-REPO`/`SKIP-TRACKED` bei jedem Lauf echot (Z.167,240) — nur die *Längsaggregation* fehlt.
> Umgesetzt: REC-4 (Sunset) unten; REC-5b Guard-Tests + REC-1 SKIP-Aggregation → Code-Issue;
> REC-3 CI-Fallback → Entscheidungs-Issue (Cross-Repo-Write-Gate). REC-2 laut Rollout real
> weitgehend erledigt (21 Repos, Fleet 13→3 dirty).

> **Accepted 2026-07-04 durch Achim Dehnert** (Session e17299, wörtlich „ADR-265 + ADR-266 accepted").

> Auslöser: Diagnose 2026-07-04 (iil-adrfw-Session). Fleet-weite „dirty tree"-Epidemie —
> Ursache ist **nicht** verstreuter Wildwuchs, sondern **ein** struktureller Mechanismus.

## Kontext und Problemstellung

Workflow-/Skill-Inhalte leben als **Single Source** in `platform/.windsurf/workflows/`
(bzw. `platform/tools/cc-skill-dist/` unter ADR-230/CC-first). Verteilt werden sie in die
einzelnen Repos per **Symlink** durch `platform/scripts/sync-workflows.sh` — der lokale
`.windsurf/workflows/<name>.md` in Repo X ist ein Symlink auf
`platform/.windsurf/workflows/<name>.md`.

Problem: In **8 von 64 Repos** sind genau diese Pfade zusätzlich **im git-Index als
reguläre Datei** (`100644`) getrackt. `sync-workflows.sh` ersetzt sie im Working-Tree durch
Symlinks (`120000`). git meldet das als **Typechange (`T`)** gegen den Index — **dauerhaft**,
weil das Verteilsystem bei jedem Lauf gegen den eigenen Index arbeitet. Beleg (2026-07-04):

| Repo | getrackte `.windsurf/workflows/*.md` | `.gitignore` hat `.windsurf/`? |
|---|---|---|
| platform | 81 | nur `mcp_config.json` |
| frist-hub | 62 | — |
| lastwar-bot | 62 | — |
| billing-hub | 54 | **ja (Z. 42)** — aber wirkungslos, Dateien schon getrackt |
| molkerei-landing | 31 | — |
| design-hub | 28 | ja |
| iil-voice-agent | 28 | — |
| gaeb-toolkit | 2 | — |
| **iil-adrfw** | **0** | **ja (Z. 8)** → **sauberer Ziel-Zustand** |

**Wichtige Exemption (Korrektur 2026-07-04):** `platform` selbst ist die **SSoT** — seine
getrackten `.windsurf/workflows/`-Dateien sind die Originale und bleiben getrackt. Untracken
in `platform` wäre Inhaltsverlust. Gleiches gilt für `platform-pinned` (detached Worktree
desselben Repos, Backing-Store von `~/.claude/policies`): dort darf der Sync gar nicht erst
schreiben — sonst ersetzt er SSoT-Dateien durch **selbstreferenzielle Symlinks** (Realbefund
2026-07-04: 37 Typechanges in `platform-pinned`, wodurch zusätzlich der
`refresh_pinned_policies.sh`-Hook still scheiterte und die Policies auf Mai-Stand einfroren).

Der **Smoking Gun**: `billing-hub` hat `.windsurf/` bereits in `.gitignore` (Z. 42) und
trackt trotzdem 54 Dateien — weil `.gitignore` **bereits getrackte** Dateien nicht entfernt.
`iil-adrfw` beweist den korrekten Endzustand: `.gitignore`-Eintrag **plus** die Dateien nie/
nicht mehr getrackt → `git status` sauber.

> **Korrektur (Retro e17299 F2, 2026-07-04):** ¹ Die billing-hub-Zeile war beim
> Schreiben bereits **stale** — sie stammte aus einem lokalen Klon auf einem alten
> Feature-Branch. Auf origin/main war billing-hub seit **2026-06-01** sauber
> (billing-hub#5, `git rm --cached`, −3640 Zeilen); der Rollout hat dort korrekt
> nichts angefasst (NOOP). Das Argument des Absatzes bleibt gültig (der Zustand
> existierte bis 01.06. real), die Tabelle taugt aber nicht als Ist-Inventar.
> Lehre als Regel: **Beweistabellen nur aus origin/main/Remote-API ziehen**
> (Memory `stale-local-clone-never-ground-truth`).

**Zweiter Dirt-Cluster (gleiche Wurzel, andere Ausprägung):** In 6 Repos (bahn-hub,
shared-ci, iil-django-commons, iilgmbh-iil-data, iil-pet-portal, nl2iot-hub) liegen
**untracked** `.windsurf/`-Symlinks (`??`-Noise, teils `rules/` aus Ad-hoc-Läufen), weil die
`.gitignore` dort nur `.windsurfignore` matcht, nicht `.windsurf/`. Ein Verteil-Lauf in ein
Repo ohne `.windsurf/`-Ignore erzeugt also zwangsläufig Dirt — tracked wie untracked.

### Warum das schadet

- **`session-ende`-Ziel „0 dirty Repos" ist strukturell unerreichbar** — 8 Repos sind
  per Konstruktion permanent `T`-dirty.
- **Echte Änderungen werden maskiert:** ein realer Diff ertrinkt zwischen 54 Typechange-Zeilen;
  die Session-Attribution (welche Datei gehört zu meiner Session?) wird verrauscht.
- **Fehl-Commit-Risiko:** ein `git add -A` friert entweder stale reguläre Kopien oder
  host-absolute Symlinks ein (beide falsch als getrackter Repo-Inhalt).

## Entscheidungsfaktoren

- SSoT-Disziplin: kein zweiter Wahrheitsstand des Workflow-Inhalts pro Repo.
- ADR-230 (CC-first) migriert ohnehin **weg** vom Windsurf-Symlink-Pfad → die getrackten
  Kopien sind Alt-Last, kein Zukunfts-Asset.
- Portabilität: ein committeter Symlink ist ein **host-absoluter** Pfad
  (`/home/devuser/github/platform/…`) → bricht auf jeder anderen Maschine und in CI.
- Reversibilität: der Fix darf keinen Inhalt vernichten (Inhalt bleibt in `platform`).

## Betrachtete Optionen

1. **Untracken + `.gitignore` (gewählt).** In den 8 Repos
   `git rm --cached -r .windsurf/workflows` (bzw. `.windsurf/`) + sicherstellen, dass
   `.gitignore` `.windsurf/` enthält. Der Inhalt bleibt in `platform` SSoT; die lokalen
   Symlinks werden ignoriert → Tree sauber. Genau der Zustand, den `iil-adrfw` schon hat.
2. **Die Symlinks committen (`120000`).** Verworfen: zementiert den Windsurf-Ära-Pfad, von
   dem ADR-230 wegmigriert; Symlinks sind host-absolut → CI/Fremd-Maschine bricht; koppelt
   jede Repo-Historie an ein reines Verteil-Artefakt.
3. **Symlinking einstellen, reale Datei-Kopien pro Repo committen.** Verworfen: N driftende
   Kopien gegen die `platform`-SSoT — genau der SSoT-Bruch, den ADR-230 vermeidet.
4. **Nichts tun.** Verworfen: dauerhafte Fleet-Dirtiness, `session-ende`-Lärm, maskierte Diffs.

## Ergebnis

Gewählt: **Option 1 — Untracken + `.gitignore`.** `platform/.windsurf/workflows/` bleibt
Single Source; alle **verteilten** Kopien werden aus dem jeweiligen Repo-Index entfernt und
per `.gitignore` ferngehalten. `sync-workflows.sh` bleibt der Verteil-Mechanismus (bis ADR-230/
`cc-skill-dist` ihn ablöst), erzeugt aber keinen Index-Konflikt mehr.

### Konsequenzen

- **Positiv:** `git status` in den 8 Repos sauber; `session-ende` „0 dirty" erreichbar; reale
  Diffs wieder sichtbar; kein host-absoluter Symlink in irgendeiner Historie.
- **Negativ / Preis:** Der Workflow-**Inhalt** ist nicht mehr in der Historie jedes einzelnen
  Repos (nur noch in `platform`). Ein frischer Klon ohne `sync`-Lauf hat die Workflows lokal
  noch nicht — akzeptabel, da `session-start` den Sync fährt und der Inhalt in `platform`
  versioniert bleibt. Kein Inhaltsverlust.
- **Fleet-Verankerung (Quelle, nicht 8 Einzel-Patches) — clean-by-construction statt
  Auto-Write (Korrektur 2026-07-04):** `sync-workflows.sh` schreibt **nie** selbst in
  fremde `.gitignore` (ein Auto-Write wäre selbst wieder unkommitteter Dirt). Stattdessen
  drei Guards im Sync:
  1. **SSoT-Skip:** Repos, deren `origin` auf das platform-Repo zeigt (platform,
     platform-pinned, weitere Worktrees/Pins), werden nie besynct.
  2. **Tracked-Guard:** ein im Ziel-Index getrackter Pfad wird **nie** durch einen Symlink
     ersetzt (Hinweis `SKIP-TRACKED` → erst `git rm --cached` per Rollout-Commit).
  3. **Ignore-Guard:** ohne wirksamen `.windsurf/`-Ignore im Ziel-Repo wird das Repo
     übersprungen (Hinweis `SKIP-REPO` → `.gitignore`-Zeile committen, dann sync).
  Damit kann der Sync per Konstruktion keinen `git status`-Dirt mehr erzeugen; neu
  onboardete Repos geraten nicht in den getrackten Zustand.

### Sunset-Kriterium für `sync-workflows.sh` (REC-4 → M28-1, Rev 4)

`sync-workflows.sh` ist ein **Übergangs-Verteiler**, kein Dauerzustand — er wird von
`cc-skill-dist` (ADR-230/CC-first) abgelöst. **Ablösekriterium:** Sobald `cc-skill-dist`
in **≥ 90 % der aktiven Fleet-Repos** der maßgebliche Verteilweg ist (messbar über den
`MANAGED-BY: platform/tools/cc-skill-dist`-Footer-Anteil vs. Symlink-Verteilung), wird
`sync-workflows.sh` **retired** (Skript nach `scripts/_ARCHIVED/`, Session-Start-Trigger
entfernt) — um die Doppelwartung zweier Verteilsysteme (Windsurf-Symlink vs. CC-Dist) zu
beenden. Bis dahin koexistieren beide bewusst; dieser ADR ist der Anker, an dem das Retirement
terminiert wird. Kein fixes Datum (hängt am CC-first-Rollout-Fortschritt), aber ein
**messbarer Schwellwert** statt „irgendwann".

### Confirmation

- Nach Rollout je Repo: `git ls-files '.windsurf/workflows/*'` → **0 Zeilen**.
- `git status --porcelain` → **keine** `.windsurf/`-Zeilen mehr.
- `grep -q '^\.windsurf/' .gitignore` → vorhanden.
- Ein `sync-workflows.sh`-Lauf danach lässt den Tree **sauber** (kein neuer `T`).

### Rollout (gegated — nicht autonom)

`platform` main ist geschützt (ADR-242, `guardian`) → Änderung via Session-Branch + PR, nicht
Direkt-Push. Pro Repo ein kleiner Commit (`git rm --cached -r .windsurf/` + `.gitignore`-Zeile
`.windsurf/`); geschützte mains via PR, ungeschützte direkt. **`platform` und
`platform-pinned` sind ausgenommen** (SSoT bzw. Worktree, s.o.) — dort wird nichts
untrackt; platform-pinned wird nach Bereinigung nur auf `origin/main` refresht.
Ziel-Repos (Stand 2026-07-04, getrackte `.windsurf/*`-Pfade): frist-hub (71), lastwar-bot
(62), billing-hub (55), molkerei-landing (40), iil-voice-agent (37), design-hub (36),
bahn-hub (11), gaeb-toolkit (11), meiki-hub (9), tax-hub/onboarding-hub/iil-adrfw/
iil-codeguard/iil-enrichment/iil-ingest/iil-reflex (je 8, überwiegend `rules/` —
vor Untrack prüfen, ob repo-spezifisch angepasst, z. B. `project-facts.md`). Zusätzlich
`.gitignore`-Zeile `.windsurf/` in den 6 `??`-Noise-Repos. Kein Merge/Deploy ohne Freigabe.

> **Rollout AUSGEFÜHRT 2026-07-04** (Freigabe Achim im Chat: „merge beide PRs und
> führe den Rollout aus"): 21 Repos je 1 Commit `chore(git-hygiene)… [skip ci]`
> via detached Temp-Worktrees; Confirmation je Repo `ls-tree origin/main` = 0
> getrackte `.windsurf/*` + exakte `.gitignore`-Zeile. Zahlen der obigen Liste
> waren teils stale (s. Korrektur ¹ oben) — dank Tracked-Guard war der Rollout
> trotzdem verlustfrei (stale Ziele = NOOP). Fleet-Census 13→3 dirty Repos.

## Glossar

- **Fleet:** die Gesamtheit der Repos unter `~/github/` über die drei Orgs.
- **`.gitignore`:** Datei, die git anweist, passende Pfade **nicht zu tracken** — wirkt aber
  nur auf **noch nicht** getrackte Dateien; bereits getrackte müssen mit `git rm --cached`
  aus dem Index gelöst werden.
- **`git rm --cached <pfad>`:** entfernt `<pfad>` aus dem Index (untrackt ihn), **lässt die
  Datei im Working-Tree** unangetastet. Genau das Werkzeug hier — kein Datenverlust.
- **Index / gestaged:** der Zwischenspeicher, aus dem der nächste Commit gebaut wird; „getrackt"
  = im Index vorhanden.
- **Symlink (symbolischer Link):** ein Verzeichniseintrag, der auf einen anderen Pfad zeigt;
  in git als Modus `120000` gespeichert, wobei der Link**inhalt** der Zielpfad ist.
- **Typechange (`T`):** git-Status, wenn eine Datei im Index einen anderen Objekt-Typ hat als
  im Working-Tree (hier: reguläre Datei `100644` im Index vs. Symlink `120000` im Tree).
- **SSoT (Single Source of Truth):** genau ein maßgeblicher Ort für eine Information; hier
  `platform/.windsurf/workflows/` für Workflow-Inhalte.
- **Sync / `sync-workflows.sh`:** das Skript, das die Workflow-Inhalte aus `platform` per
  Symlink in die anderen Repos verteilt.
- **CC-first (ADR-230):** die Migration von der Windsurf-Ära hin zu Claude Code als primärer
  Agent-Oberfläche; der Windsurf-Symlink-Verteilpfad ist dabei Auslaufmodell.
- **Getrackter Zustand:** eine Datei ist im git-Index → Änderungen an ihr erscheinen im
  `git status`. Ziel dieses ADR: die Verteil-Kopien in den **un**getrackten Zustand bringen.
