---
status: proposed
date: 2026-06-29
decision-makers: [Achim Dehnert]
scope: platform
implementation_status: none
related: [ADR-230, ADR-233, ADR-234]
supersedes: []
---

# ADR-258: Org-weite Verteilung von Claude-Code-Hooks (Reaper-Gate als Erstfall)

> **Kurz:** Der wiederkehrende Befund `worktree-orphan-accumulation` (≥2 über Retros,
> gate-pflichtig) braucht eine **org-weit erzwungene** Reaper-Ausführung am Session-Ende.
> Es gibt aber **keinen** Mechanismus, um Claude-Code-**Hooks** org-weit zu verteilen —
> `cc-skill-dist` (ADR-230) deckt nur `commands` + `skills` ab. Dieser ADR entscheidet das
> **Wie** der Hook-Verteilung (eine neue Achse zu ADR-230), nicht den Reaper selbst.

## Status

`proposed` — wartet auf Entscheidung. Auslöser: Session-Retro 2026-06-28
(`~/shared/session-retro-2026-06-28-illustration-hub-6474d8.md`, Befund #4) + platform
Issue #673. Lokale Enforcement (ein Host) ist bereits umgesetzt (siehe E-5); dieser ADR
entscheidet nur die **org-weite** Stufe.

## Kontext

**Auslöser:** `worktree-orphan-accumulation` ist laut `tools/retro_kpis.py` **≥2 über
Retros ⇒ Gate-PR-Pflicht**. Die Skill `session-ende` (Phase 3.1c) bittet per Prosa um den
Reaper-Lauf — überspringbar, real übersprungen am 2026-06-28.

**Evidenz (alle 2026-06-28/29 in-session verifiziert):**

- **E-1 (`tools/cc-skill-dist/generate.py`, LANES):** cc-skill-dist hat genau zwei Lanes —
  `commands` → `~/.claude/commands/`, `skills` → `~/.claude/skills/`. **Keine** Lane für
  Hooks oder `settings.json`. Es existiert also keine Hook-Verteilung.
- **E-2 (`~/.claude/settings.json`):** Die User-settings sind **maschinen-spezifisch +
  secret-haltig** (MCP-Bearer-Token, Host-spezifische MCP-`command`-Pfade). Sie lässt sich
  nicht org-weit überschreiben; ein Hook-Eintrag braucht einen **idempotenten JSON-Merge**
  pro Maschine, der den Rest unangetastet lässt.
- **E-3 (Topologie):** Orphan-Worktrees liegen **lokal** unter `~/.repo-session/worktrees/`
  auf jeder Dev-Maschine (ADR-233). GitHub-gehostete Runner sehen sie nicht; der einzige
  self-hosted-Runner liegt auf dem **Prod-Host** (ADR-257, E-1) — auch der hat die
  Dev-Maschinen-Worktrees nicht. ⇒ **Eine CI-Action kann das Problem nicht lösen**; das
  Reaping muss am Session-Ende **auf jeder Dev-Maschine** laufen.
- **E-4 (`tools/worktree-reaper.py`, Lauf 2026-06-28):** Der Reaper ist **self-protecting** —
  behält offene-PR/Lease/DIRTY-Worktrees, schreibt ein Restore-Manifest. Automatisches
  `--apply` ist datensicher (kein unbeabsichtigter Verlust).
- **E-5 (Proof-of-Concept, dev-desktop 2026-06-29):** Lokaler `SessionEnd`-Hook
  (`~/.claude/hooks/reap_worktrees.sh` + settings.json-Eintrag) gesetzt und verifiziert
  (Hook-Exit 0, reapt nur Gemergtes). Das Muster funktioniert — offen ist nur die Verteilung.

## Entscheidung (Vorschlag)

**Eine dritte cc-skill-dist-Lane `hooks`** (Script-Datei → `~/.claude/hooks/`, analog
`skills`/`commands`, MANAGED-BY-Header + Drift-`doctor.py`), **plus** dokumentiertes
**einmaliges** `settings.json`-Wiring pro Maschine (der `SessionEnd`-Block, der das Script
referenziert).

Begründung der Wahl gegen die Alternativen:
- Hält die **secret-haltige `settings.json` aus jeder Automatik heraus** (E-2) — das Tool
  fasst nur `~/.claude/hooks/` an, nie die User-settings.
- Bleibt **konsistent zu ADR-230** (user-level Install pro Maschine, eine kanonische Quelle
  in platform, Drift-`doctor.py`).
- Das einmalige settings-Wiring ist ein **bewusster, reviewbarer Akt** je Maschine statt
  eines org-weiten Schreibzugriffs auf Secrets-Dateien.

Der Reaper-Script-Inhalt (E-5) wird kanonisch in platform abgelegt (z. B.
`tools/hooks/reap_worktrees.sh`) und über die neue Lane verteilt.

## Verworfene Optionen

- **Voll-Auto settings.json-Merge** (Installer mergt den Hook in jede `~/.claude/settings.json`):
  vollautomatisch, aber org-weiter Schreibzugriff auf secret-haltige, maschinen-spezifische
  Dateien — hoher Blast-Radius, verstößt gegen das Gate `autonomous-no-human-review`
  (org-weite Automatik mit Schreibrecht). Als **spätere optionale Stufe** vermerkt, nur mit
  robustem JSON-Merge + Backup + Dry-Run-in-CI.
- **Nightly GitHub-Action**: kann lokale Dev-Maschinen-Worktrees nicht sehen (E-3) — löst das
  Problem nicht.
- **`retro_kpis.py --gate` im CI** (rot bei ≥2 ungereaptem Orphan): detektiert nur, **verhindert
  nicht**; ergänzend sinnvoll, ersetzt die Enforcement aber nicht.

## Konsequenzen

- **Gut:** Erste org-weite Hook-Verteilung; schließt `worktree-orphan-accumulation` strukturell;
  `settings.json`-Secrets bleiben unangetastet; konsistent zu ADR-230.
- **Kosten/Schuld:** Das einmalige settings-Wiring bleibt manuell (eine Zeile je Maschine) —
  bis die optionale Auto-Merge-Stufe entschieden wird. `doctor.py` sollte zusätzlich melden,
  wenn der Hook-Eintrag in settings.json **fehlt** (sonst liegt das Script da, feuert aber nie).
- **Folge-Artefakte:** (1) `hooks`-Lane in `generate.py`/`doctor.py`; (2) kanonisches
  `tools/hooks/reap_worktrees.sh`; (3) Doku-Snippet für den SessionEnd-Block; (4) Issue #673
  schließt erst, wenn die Lane live + auf ≥1 zweitem Host verifiziert ist (kein Selbst-Beweis,
  vgl. Gate `claim-before-cheapest-check`).
