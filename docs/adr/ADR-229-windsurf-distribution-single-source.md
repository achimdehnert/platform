---
status: proposed
decision_date: 2026-05-30
deciders: Achim Dehnert
domains: [tooling, dx, drift-prevention, infra]
supersedes: []
amends: []
tags: [windsurf, skills, workflows, distribution, cross-repo]
---

# ADR-229: Kanonische `.windsurf`-Distribution — Single Global Source, consumed not mirrored

| Attribut | Wert |
|---|---|
| **Status** | Proposed |
| **Scope** | Platform-wide (~30 Repos) |
| **Datum** | 2026-05-30 |
| **Autor** | Achim Dehnert |
| **Relates to** | `~/.claude/policies/claude-skills.md`, ADR-065 (Filesystem-first ADR-Numbering) |

> **Status proposed.** **Right-Sizing-Nachtrag 2026-05-30:** Aktuelle Nutzung = Coding **nur mit CC**
> (bereits gelöst via `~/.claude/commands/`); **Windsurf nur für ADR-Review**, nicht als Coding-IDE.
> Damit ist die globale Windsurf-Workflow-Distribution (**Schritt 2–4**) **YAGNI → zurückgestellt**.
> Nur **Schritt 1 (Untrack/Cleanup)** war nutzungsunabhängig richtig und ist **erledigt**; der
> F1-Zustand ist durch das gesetzte `.gitignore` regressionsgeschützt. Reaktivieren von D/Schritt 2–4
> **nur, falls Windsurf Coding-Tool wird**. Zwei externe Review-Runden eingearbeitet (s. §Anhang).

## 1. Kontext

### 1.1 Ausgangslage
Windsurf-Workflows (Slash-Commands) sind die SSoT in `platform[-workflows]/.windsurf/workflows/`.
CC konsumiert sie über **eine** globale Location `~/.claude/commands/` (Symlinks) — **kein** Per-Repo-Mirror.
Für die Windsurf-IDE trägt **jedes Consumer-Repo** ein eigenes `.windsurf/workflows/` mit ~60 Dateien
(Kopie der Platform-Workflows), befüllt vom `sync-repo`-Workflow.

### 1.2 Problem (Audit 2026-05-30, F1)
- **`.gitignore` enthält `.windsurf/`, die Dateien sind aber getrackt** → Widerspruch (ignored-yet-tracked).
- **Index = reguläre Datei (100644), On-Disk = Symlink** → permanenter `T`-Typechange. Pro Repo ~50–62,
  über ~20 Repos **~1.000 Phantom-Dirty-Files**.
- **Bricht Git-Ops:** `rebase`/`stash`/`checkout --ff-only` scheitern an „uncommitted changes";
  maskiert echte Änderungen; Typechanges drohen in Feature-PRs zu lecken.
- **Mixed-State:** Repos tracken teils Dateien, teils Symlinks (z. B. risk-hub 56 Dateien + 5 Symlinks,
  bfagent 60+8); 2 Repos (dms-hub, iil-relaunch) tracken `.windsurf` **ohne** gitignore-Schutz.
- **Subtree-Versuch empirisch gescheitert** (s. §Anti-Pattern).

### 1.3 Constraints
- Windsurf liest Workflows aus `.windsurf/workflows/` (repo-scoped) **und** hat eine globale Location
  (verifiziert vorhanden: `~/.codeium/windsurf/windsurf/workflows/`, enthält `review.md`; **nicht** mit
  Platform-Workflows befüllt). **Offen:** liest Windsurf global *zusätzlich* zu repo-lokal (Merge),
  nur als Fallback, oder überschreibend? → **hartes Acceptance-Gate** (§Acceptance, REC-1).
- `claude-skills.md`: **Never hardcode** Pfade/Owner/Prefixe. SSoT = `platform-workflows/.windsurf/workflows/`.
- Dev primär Linux/WSL (Symlinks ok); Fresh-Clones/CI evtl. ohne `platform`-Sibling.

## 2. Entscheidung

**(D) Single Global Source, consumed not mirrored.** Präzise (REC-2):
- **Kanonische Quelle ist und bleibt ausschließlich `platform`.** Die globale Windsurf-Location ist
  **reines Konsum-/Installationsziel**, **kein zweiter Wahrheitsstand**.
- Das **Per-Repo-`.windsurf/workflows/`-Mirror entfällt** (untracken; `.windsurf/` gitignored).
- Befüllung der globalen Location: **generierte Symlink-Farm** (REC-3, OOTB-5) als Default auf Linux/WSL —
  lokal generierte Symlinks auf `platform`-Dateien, **nie committet**, `platform` zur **Laufzeit per
  Discovery** aufgelöst (REC-5/REC-15). Vorteile: kein zweiter materieller Stand, immer frisch bei
  Platform-Update, kein `../../../`-Hardcode. **Kopie** nur als dokumentierter Fallback (no-sibling),
  dann mit Commit-Pin + Checksums (REC-6, gegen stille Drift).
- Setup ist **maschinen-einmalig** (analog `~/.claude/commands/`), aber **versioniert + prüfbar**
  (Manifest + Doctor, s. u.) — sonst wird „Kopie ohne Update-Policy" der nächste Mirror (M28-16).

**Windsurf-Pfad ist Beispiel, nicht Vertrag** (REC-18/AD-7): Default `~/.codeium/windsurf/windsurf/workflows/`,
override-bar, von **Doctor/Discovery validiert** — kein hartkodierter Architekturvertrag.

**Fallback E** (falls Windsurf global nur als Fallback/nicht merged liest, REC-14): repo-lokales
`make windsurf` materialisiert **untracked** Symlinks und trägt den Schutz in **`.git/info/exclude`**
ein (nicht `.gitignore` + getrackte Dateien mischen, OOTB-6). E ist **vor Acceptance einsatzfähig
auszuarbeiten** (M28-4), nicht erst wenn D scheitert.

## 3. Betrachtete Alternativen

| Option | Kern | Advocatus-Diabolus-Killshot | Verdikt |
|---|---|---|---|
| **A** Untrack + gitignore-only | Repo trackt nichts; lokale Symlinks via Sync | silent-missing; fragile Sibling-Annahme | Teil-Schritt von D |
| **B** Symlinks committen (120000) | konsistent getrackt | tote Symlinks (Fresh-Clone); committeter Pfad-Hardcode (gg. claude-skills.md); Windows-Müll; Security-Scanner flaggen `../../../`-Escape; ~1.800 Symlinks Churn | **Verworfen** |
| **C** Git-Subtree/Submodule | echter Inhalt getrackt | **empirisch gescheitert** (s. §Anti-Pattern); Submodule-Friktion; Mirror bleibt | **Verworfen (erprobt)** |
| **D** Single Global Source | eine Stelle, kein Mirror | maschinen-einmaliges Setup; hängt an Windsurf-Global-Read | **Gewählt** |
| **E** A-gehärtet (Bootstrap, `.git/info/exclude`) | untrack + `make windsurf` on-demand | Per-Repo-Bootstrap bleibt | **Fallback (ausgearbeitet)** |

## 4. Begründung
Das Anti-Pattern ist *jedes Repo spiegelt alle ~60 Workflows* — A/B streiten nur über die Repräsentation.
CC hat es mit *einer* globalen Quelle gelöst; D überträgt die Symmetrie auf Windsurf. Minimaler
getrackter Zustand = minimale Drift — **vorausgesetzt**, das globale Setup ist versioniert + prüfbar
(sonst nur verschobene Drift, AD-3/4/17).

## 5. Implementation Plan

>  **Nachtrag 2026-05-30 (Right-Sizing):** **Schritt 1 = erledigt** (~32 Repos untracked). **Schritt 2–4
> = ZURÜCKGESTELLT (YAGNI)** — sie setzen Windsurf als Coding-IDE über alle Repos voraus; aktuelle
> Nutzung ist CC-only + Windsurf-nur-ADR-Review. **Nicht bauen** (kein Installer/Manifest/Doctor/Sync),
> bis Windsurf Coding-Tool wird. F1-Regressionsschutz übernimmt das bereits gesetzte `.gitignore`
> (re-erzeugte Symlinks sind ignoriert → kein Re-Tracking); der alte Sync-Schreibpfad ist nur zu
> beobachten, nicht aktiv umzubauen.

### Schritt 1 — Mixed-State deterministisch bereinigen (läuft)
**Migrationsprotokoll** (REC-9/REC-11, gegen Restbestände M28-6): pro Repo (a) getrackte `.windsurf`-Blobs
**jeden Modus** (Datei *und* Symlink) untracken; (b) `.gitignore` `.windsurf/` sicherstellen
(dms-hub/iil-relaunch ergänzen); (c) **vor** Untrack prüfen, ob repo-lokale Workflow-Änderungen existieren,
die erst nach `platform` upstreamt oder bewusst verworfen werden müssen; (d) nach Merge `git status`
verifizieren = 0 Typechanges. *Status:* learn-hub #4 ✅; recruiting/research/writing-hub, learnfw,
outlinefw, researchfw als PRs offen.

### Schritt 2 — Globales Setup: Installer + Manifest + Doctor — ⏸️ ZURÜCKGESTELLT (YAGNI)
- **Manifest** in `platform`: maschinenlesbare Liste der kanonischen Workflows + Checksums + Source-Commit.
- **Installer** (`make windsurf-global` / `platform windsurf install`): Discovery von `platform`,
  generiert Symlink-Farm in die globale Location, schreibt **Statusdatei** (Quelle, Commit, Zeitpunkt).
- **`doctor`/`verify`-Befehl**: prüft Platform-Quelle, globale Location, Workflow-Anzahl vs. Manifest,
  Checksums, Lesbarkeit — und (REC-1) das **Windsurf-Merge-Verhalten** über einen Test-Workflow.

### Schritt 3 — Re-Tracking-Schutz (REC-10, M28-7/M28-14)
- `new-github-project`-Vorlage legt **kein** `.windsurf/workflows/`-Mirror mehr an; stattdessen optional
  **Repo-Stub `.windsurf/README.md`** (REC-16/OOTB-3): getrackter Zeiger auf den globalen Installer +
  „`.windsurf/workflows` darf NICHT getrackt werden".
- **CI-/Template-Guard**, der Re-Tracking von `.windsurf/workflows` verhindert.

### Schritt 4 — Alten Sync stilllegen/umlenken (Begriff präzisiert, REC-4/AD-6/M28-11)
„Sync" ist **zwei verschiedene Dinge** — sauber trennen:
- **Repo-CI-Sync** (`sync-repo` GitHub-Action) darf **nicht** mehr `.windsurf/workflows` in Consumer-Repos
  schreiben (kann ohnehin nicht ins Home-Dir) → deaktivieren/umlenken auf das Manifest.
- **Maschinen-lokaler Installer** (Schritt 2) ist der einzige Pfad in die globale Home-Location.

## 6. Repo-spezifische Workflows & Kollisionen (REC-13/REC-17, bedingt)
Abhängig von der Windsurf-Merge-Frage:
- Falls **Merge** unterstützt: repo-spezifische Workflows nur unter **separatem Namespace/Prefix** erlaubt;
  **Kollisionsregel** bei gleichem Command-Namen (global vs. repo) explizit (welche gewinnt?).
- Falls **kein** Merge: repo-spezifische Workflows nur über Fallback E.
- **Scope-Regel (REC-17):** global verteilte Workflows müssen **repo-agnostisch** sein. *Weitgehend bereits
  erfüllt:* Workflows lesen Repo-Kontext zur Laufzeit aus `project-facts.md` (Step-0-Konvention,
  never-hardcode) — repo-spezifische Annahmen gehören in Namespace/lokal, nicht in globale Commands.

## 7. Risiken
- **R1 (AD-1):** Windsurf merged global+repo nicht wie nötig → D operativ nicht tragfähig → **E wird
  Primärpfad**. *Mitigation:* hartes Acceptance-Gate (REC-1), E vorab ausgearbeitet (M28-4).
- **R2 (AD-3/4/M28-2):** stille Drift zwischen Maschinen. *Mitigation:* Manifest+Commit-Pin+Doctor.
- **R3 (AD-7/M28-3):** Windsurf ändert globalen Pfad bei Update. *Mitigation:* Discovery + Doctor validiert.
- **R4 (AD-13):** Untrack löscht noch nicht upstreamte lokale Workflow-Edits. *Mitigation:* Schritt-1(c)-Check.
- **R5 (AD-23, teil-OOS):** Remote-Dev/WSL/Devcontainer-Pfadvarianz. *Mitigation:* Discovery deckt WSL ab;
  JetBrains o. ä. out-of-scope (Windsurf = eigene IDE).

## 8. Konsequenzen
- **Positiv:** ~1.000 Phantom-Dirty-Files weg; Git-Ops entblockt; Fresh-Clone-sauber; Single-Source = keine
  Drift; symmetrisch zu CC; kein committeter Pfad-Hardcode; Cross-Repo-Churn (Workflow-Änderung × ~30 Repos) entfällt.
- **Trade-offs:** maschinen-einmaliges, aber **versioniertes/prüfbares** Setup; Abhängigkeit von Windsurf-Global-Read.
- **Nicht in Scope:** Inhalt/Governance der Workflows selbst; CC-`~/.claude/commands/` (gelöst).

## 9. Acceptance Criteria (hart — proposed bis alle grün, REC-20)

> ⏸️ **Nachtrag 2026-05-30:** Diese Kriterien (inkl. Windsurf-Merge-Validierung) greifen **nur bei Reaktivierung** von Schritt 2–4 (Windsurf wird Coding-Tool). Aktuell **nicht blockierend** — Schritt 1 ist eigenständig erledigt.
- [ ] **Windsurf-Merge-Verhalten empirisch dokumentiert** (Merge / Fallback / Overwrite) — entscheidet D vs E (REC-1).
- [ ] **Installer + Manifest + Doctor** existieren und sind grün (REC-7/8).
- [ ] **Symlink vs. Kopie** entschieden + dokumentiert (Freshness/Offline/Fehlerbild/Update) (REC-3).
- [ ] **Discovery-Regel** statt Pfad-Hardcode; verständliches Scheitern ohne `platform`-Sibling (REC-5/15).
- [ ] **Mixed-State vollständig bereinigt** (alle Repos 0 Typechanges) + **Re-Tracking-Guard aktiv** (REC-9/10).
- [ ] **Fallback E** einsatzfähig (untracked + `.git/info/exclude`) (REC-14).
- [ ] Alter Repo-CI-Sync deaktiviert/umgelenkt (REC-4/M28-14).

## 10. Anti-Pattern: gescheiterter Subtree-Versuch (REC-19/AD-14)
Git-History (z. B. learn-hub): `remove tracked workflow files (replace with subtree)` →
`Squashed '.windsurf/workflows' content` → `Merge ... as '.windsurf/workflows'`. Hinterließ den Mixed-State
(Datei+Symlink). **Failure-Signatur dokumentiert, damit kein Maintainer aus Reproduzierbarkeits-Reflex
erneut einen Per-Repo-Mirror/Subtree einführt.**

## 11. Glossar
| Begriff | Bedeutung |
|---|---|
| **Workflow** | Windsurf-Slash-Command (`.md` + Frontmatter); CC-Äquivalent = Skill |
| **Mirror** | Per-Repo-Kopie/Symlink-Satz aller Platform-Workflows |
| **Symlink-Farm** | lokal generierte, nicht committete Symlinks auf eine Quelle |
| **Typechange (`T`)** | Git: Index-Objekttyp ≠ Working-Tree-Objekttyp (Datei vs. Symlink) |
| **Doctor** | Diagnose-Befehl: Quelle/Location/Anzahl/Checksums/Merge-Verhalten prüfen |

## 12. Referenzen
- Platform-Audit 2026-05-30 (`platform/audits/platform-audit-2026-05-30.md`), Finding F1.
- `~/.claude/policies/claude-skills.md` (SSoT + `~/.claude/commands/`-Muster).
- Session-PRs: learn-hub #4, recruiting-hub #2, research-hub #4, writing-hub #26, learnfw #1, outlinefw #1, researchfw #2.

## 13. Anhang: Externer Review (Rückfluss-Tagging, 2026-05-30)
Cross-Provider-Zweitmeinung (blind ggü. Repo/Memory) via `/adr-handoff-extern`; Briefing:
`~/shared/adr-handoff-ADR-229-2026-05-30.md`. Empfehlung: **überarbeiten** — Richtung richtig, Betriebsvertrag
zu offen. ~18/20 RECs `[valid]` (eingearbeitet), 2 teilweise:

| Cluster | RECs | Wo eingeflossen |
|---|---|---|
| „Single Global Source" präzisiert (platform kanonisch, global = Konsum) | 2 | Entscheidung |
| Symlink vs. Kopie + Symlink-Farm | 3 | Entscheidung |
| „Sync-Workflow" entwirrt (CI ≠ Home-Dir) | 4 | Schritt 4 |
| Pfad-Discovery statt Hardcode | 5, 15, 18 | Entscheidung, Risiken |
| Version/Drift: Manifest + Commit-Pin + Doctor | 6, 7, 8 | Schritt 2, Acceptance |
| Migrationsprotokoll + Pre-Untrack-Check | 9, 11 | Schritt 1 |
| Re-Tracking-Guard | 10 | Schritt 3 |
| Bootstrap-Doku als getestete Sequenz | 12 | Schritt 2 (Installer/Doctor) |
| Namespace/Overlay/Kollision (bedingt) | 13, 17 | §6 |
| Fallback E ausgearbeitet (`.git/info/exclude`) | 14 | Entscheidung |
| Repo-Stub `.windsurf/README.md` | 16 | Schritt 3 |
| Anti-Pattern Subtree | 19 | §10 |
| Windsurf-Validierung = Acceptance-Gate | 1 | Acceptance |
| Acceptance-Formulierung geschärft | 20 | Acceptance |
| Scope „repo-agnostisch" | 17 | §6 (teils bereits durch project-facts-Konvention) |
| Devcontainer/JetBrains-Varianz | (AD-23) | R5 (WSL via Discovery; JetBrains out-of-scope) |

## 14. Changelog
- 2026-05-30: Initial (Proposed). Audit-F1; advocatus-diabolus-Review A/B/C/E; Windsurf-Global-Location verifiziert.
- 2026-05-30: Externe Cross-Provider-Review (20 RECs) über Rückfluss-Gate eingearbeitet — Betriebsvertrag
  präzisiert (Installer/Manifest/Doctor, Symlink-Farm, Discovery), Migrationsprotokoll + Re-Tracking-Guard,
  Fallback E (`.git/info/exclude`), harte Acceptance Criteria, Subtree-Anti-Pattern; bleibt `proposed`.
- 2026-05-30: **Right-Sizing** — Nutzung ist CC-only coding + Windsurf-nur-ADR-Review. **Schritt 2–4 (globale Windsurf-Distribution) zurückgestellt (YAGNI)**; Schritt 1 (Untrack/Cleanup) erledigt + per `.gitignore` regressionsgeschützt; Acceptance-Gate nur bei Reaktivierung relevant. Kein Installer/Doctor gebaut.
