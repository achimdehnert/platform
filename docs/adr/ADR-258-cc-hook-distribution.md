---
status: accepted
date: 2026-06-29
revision: 2
decision-makers: [Achim Dehnert]
scope: platform
implementation_status: in-progress
related: [ADR-230, ADR-233, ADR-234, ADR-257]
supersedes: []
---

# ADR-258: Org-weite Verteilung von Claude-Code-Hooks (Reaper-Gate als Erstfall)

> **Kurz:** `cc-skill-dist` (ADR-230) verteilt nur `commands` + `skills` — es fehlt eine
> Achse, um Claude-Code-**Hooks** org-weit zu installieren. Dieser ADR entscheidet das **Wie**
> der Hook-**Verteilung** (neue `hooks`-Lane) und trennt sie **explizit** von der **Wirksamkeit**:
> Verteilung allein erzwingt nichts — Enforcement entsteht erst durch nachgewiesenes
> `settings.json`-Wiring **plus** grünen `doctor.py`-Check pro Host. Erstfall:
> `worktree-orphan-accumulation`-Reaping am Session-Ende.

## Status

`accepted` (2026-06-29). Auslöser: Session-Retro 2026-06-28 (Befund #4) + Issue #673. Lokale
Enforcement auf **einem** Host ist als **PoC** umgesetzt (E-5) — das ist **kein** Beleg für die
org-weite Stufe (Gate `claim-before-cheapest-check`); #673 schließt erst nach dem 2.-Host-Kriterium.
Stufe A (hooks-Lane + Reaper-Script + Bootstrap + doctor-Wiring-Check) ist in PR #703/#706 umgesetzt.

> **Rev 2 (2026-06-29):** Externe Cross-Provider-Zweitmeinung (`/adr-handoff-extern`, OpenAI o3)
> eingearbeitet — 16 von 20 RECs nach Rückfluss-Gate `[valid]`, 2 `[missversteht-Kontext]`
> (Briefing/Antwort: `~/shared/adr-handoff-ADR-258-2026-06-29*.md`). Wesentliche Schärfungen:
> (1) **Verteilung ≠ Enforcement** explizit zweistufig (REC-1/16/20); (2) harte **Akzeptanz-
> kriterien** der org-weiten Stufe (REC-2/14); (3) `doctor.py`-settings-Check **verpflichtend**
> (REC-3); (4) **stabiler Hook-Pfad** + **Lane-Semantik** + **Security/Failure/Rollback/Namensraum**
> (REC-4/5/6/7/15/19); (5) **Host-Attestierung** gegen dezentrale Aktivierungs-Wahrheit (REC-9/10);
> (6) **Dry-Run-Bootstrap** statt Auto-Schreiben (REC-11); (7) **Auto-Merge braucht eigenen ADR**
> + Gate gilt **für die Lane selbst** (REC-12/13).

## Kontext

**Auslöser:** `worktree-orphan-accumulation` ist laut `tools/retro_kpis.py` **≥2 über Retros ⇒
Gate-PR-Pflicht**. `session-ende` (Phase 3.1c) bittet per Prosa um den Reaper-Lauf — überspringbar,
real übersprungen am 2026-06-28.

**Evidenz (alle 2026-06-28/29 in-session verifiziert):**
- **E-1 (`tools/cc-skill-dist/generate.py`, LANES):** zwei Lanes — `commands` → `~/.claude/commands/`,
  `skills` → `~/.claude/skills/`. Keine Lane für Hooks/`settings.json`.
- **E-2 (`~/.claude/settings.json`):** maschinen-spezifisch + secret-haltig (MCP-Bearer-Token,
  host-spezifische Tool-Pfade) → nicht org-weit überschreibbar; Hook-Eintrag bräuchte idempotenten
  JSON-Merge pro Maschine.
- **E-3 (Topologie):** Orphan-Worktrees liegen lokal unter `~/.repo-session/worktrees/`. GitHub-
  gehostete Runner sehen sie nicht; der einzige self-hosted-Runner liegt auf dem Prod-Host
  (ADR-257). ⇒ CI kann das Problem nicht lösen; Reaping muss am Session-Ende **auf jeder
  Dev-Maschine** laufen.
- **E-4 (`tools/worktree-reaper.py`):** self-protecting — behält offene-PR/Lease/DIRTY, schreibt
  Restore-Manifest. Auto-`--apply` ist datensicher.
- **E-5 (PoC, dev-desktop):** `SessionEnd`-Hook (`reap_worktrees.sh` + settings.json-Eintrag) auf
  **einem** Host verifiziert (Exit 0, reapt nur Gemergtes). **Begrenzt als PoC** — kein org-weiter Beleg.

## Entscheidung

**Zweistufig, bewusst getrennt (REC-1):**

**Stufe A — Verteilung (dieser ADR entscheidet sie):** Eine dritte `cc-skill-dist`-Lane `hooks`,
analog `skills`/`commands`:
- Quelle kanonisch in platform (`tools/hooks/<name>.sh`), Ziel `~/.claude/hooks/managed/<name>.sh`.
- **Dediziertes `managed/`-Unterverzeichnis (Fix nach Erstimpl):** generate macht einen atomaren
  Verzeichnis-**Swap**; `~/.claude/hooks/` enthält auch hand-gepflegte Hooks (PreToolUse/SessionStart/…),
  die ein Swap dort wegwischen würde. Die Lane besitzt darum exklusiv `~/.claude/hooks/managed/`.
- **Lane-Semantik (REC-5):** kopiert die kanonische Datei, setzt `chmod +x`, schreibt MANAGED-BY-
  Header + Manifest (Hash), **meldet** Drift/lokale Edits via `doctor.py` (repariert nicht stillschweigend),
  fasst **nur** den `hooks/managed`-Namensraum an, lässt fremde lokale Dateien unberührt.
- **Stabiler Pfad (REC-4):** der settings-Eintrag verweist dauerhaft auf den **konstanten** Pfad
  `~/.claude/hooks/managed/reap_worktrees.sh`; Versionierung passiert im Datei-**Inhalt**, nie im Pfad.
- **Security-Posture (REC-6, scoped):** Hook-Dateien `0755`, owner = User, **kein** world-write;
  MANAGED-BY + Manifest-Hash als Integritätsanker; `doctor.py` zeigt lokale Manipulation als Drift.
  Volles Signatur-/Manifest-Schema (Ansatz 3) ist **deferred**, nicht Teil dieser Stufe.

**Stufe B — Wirksamkeit (NICHT durch Verteilung allein erfüllt, REC-1/14):** Der Hook feuert erst,
wenn `~/.claude/settings.json` einen `SessionEnd`-Eintrag auf den Pfad hat. Dieses Wiring bleibt ein
**bewusster, reviewbarer Akt pro Maschine** (E-2: kein org-weiter Auto-Schreibzugriff auf Secrets):
- **Aktivierungsprozedur (REC-10):** dokumentiertes kopierbares Snippet + Vorher-/Nachher-Check.
- **Dry-Run-Bootstrap (REC-11):** ein Begleit-Command liest die bestehende `settings.json`, validiert
  JSON, zeigt den **exakten Patch/Diff** und schreibt **nicht** automatisch.
- **`doctor.py`-Check verpflichtend (REC-3):** „Script vorhanden" allein = **nicht** gesund; doctor
  prüft zusätzlich, dass der `SessionEnd`-Eintrag existiert, auf den stabilen Pfad zeigt und die
  Datei ausführbar ist. Fehlt das Wiring → **unhealthy**.
- **Host-Attestierung (REC-9):** gegen die dezentrale Aktivierungs-Wahrheit ein maschinenlokaler
  Health-Report / Host-Inventar, damit org-weit nachweisbar ist, **wo** der Hook aktiv ist.

**Failure-Semantik des SessionEnd-Hooks (REC-7) — teils im PoC bereits entschieden:**
- non-blocking: der Hook beendet **immer** mit 0, darf das Session-Ende nie blockieren (PoC).
- Timeout gesetzt (PoC: 60 s); Reaper schreibt Restore-Manifest (E-4); Hook-Lauf wird geloggt
  (REC-17, minimaler Log-Vertrag: Ziel-Ort + Diagnose eines fehlgeschlagenen Laufs).
- **Namensraum-Garantie (REC-19):** der Reaper bearbeitet **ausschließlich** `~/.repo-session/
  worktrees/` und fasst keine repo-lokalen/fremden Worktrees außerhalb an.

**Akzeptanzkriterien für die org-weite Annahme (REC-2/14) — `claim-before-cheapest-check`:**
1. Frische Installation der `hooks`-Lane auf **≥1 zweitem Dev-Host**.
2. `SessionEnd`-Eintrag vorhanden + auf stabilen Pfad zeigend; Script ausführbar.
3. **Echter** Hook-Lauf am Session-Ende (nicht nur manueller Script-Aufruf) + Reaper-Log.
4. `settings.json`-Secrets **unverändert** (Diff beweist: kein Auto-Schreibzugriff).
5. `doctor.py` meldet den Host als **healthy** (Datei + Wiring + ausführbar).
Erst wenn 1–5 belegt sind, gilt die org-weite Stufe als „fertig" und #673 schließt.

## Verworfene / verschobene Optionen

- **Voll-Auto `settings.json`-Merge:** org-weiter Schreibzugriff auf secret-haltige Dateien — hoher
  Blast-Radius; **braucht einen eigenen ADR + Gate** (REC-12), darf **nicht** als implizite Folge
  dieser Entscheidung durchrutschen. Nur mit robustem JSON-Merge + Backup + Dry-Run-in-CI.
- **Nightly GitHub-Action:** sieht lokale Dev-Worktrees nicht (E-3).
- **CI-Detektions-Gate** (`retro_kpis --gate`): detektiert, verhindert nicht — höchstens ergänzend.
- **systemd-user-Timer (Out-of-the-Box Ansatz 2):** entkoppelt von CC, erwischt auch abgebrochene
  Sessions — **als ergänzendes Sicherheitsnetz** vermerkt, nicht als Ersatz des Session-Ende-Pfads.

## Governance

- **`autonomous-no-human-review` gilt für die Lane selbst (REC-13):** Die `hooks`-Lane verteilt
  org-weit **automatisch ausgeführten** Code — sensibler als `skills`/`commands` (die ein Nutzer
  aktiv aufruft). Ihr Roll-out bekommt darum vor Merge einen erzwungenen Dry-Run-in-CI **oder**
  Vier-Augen-Review, der Lane-Semantik + Security-Posture beweist.

## Konsequenzen

- **Gut:** Erste org-weite Hook-Verteilung; schließt `worktree-orphan-accumulation` strukturell;
  `settings.json`-Secrets bleiben unangetastet; konsistent zu ADR-230.
- **Bekannte Schuld:** Aktivierung bleibt manuell (Dry-Run-Bootstrap mildert) → die org-weite
  Wirksamkeit ist nur so vollständig wie das Host-Inventar (REC-9). Ehrliche Benennung: dieser ADR
  liefert **Verteilung + Aktivierungs-Nachweisbarkeit**, nicht „auf jeder Maschine garantiert aktiv".
- **Rollback (REC-15):** Hook deaktivieren = `SessionEnd`-Eintrag entfernen/auskommentieren; Datei
  via Lane zurückrollen oder entfernen; `doctor.py` muss den deaktivierten Zustand verständlich melden.
- **Folge-Artefakte:** (1) `hooks`-Lane in `generate.py`/`doctor.py` (inkl. settings-Wiring-Check);
  (2) kanonisches `tools/hooks/reap_worktrees.sh`; (3) Dry-Run-Bootstrap-Command; (4) Doku-Snippet
  + Host-Attestierung; (5) #673 schließt erst nach den Akzeptanzkriterien (2. Host).
