---
status: accepted
date: 2026-05-30
decision-makers: Achim Dehnert
domains: [tooling, dx, drift-prevention, governance]
amends: [claude-skills.md]
relates_to: [ADR-229]
tags: [skills, workflows, distribution, claude-code, windsurf, cross-repo]
---

# ADR-230: CC-first Skill-Distribution — eine kanonische Quelle, deterministische Verteilung, Windsurf = generiertes ADR-Subset

| Attribut | Wert |
|---|---|
| **Status** | Accepted (Entscheidung; Live-Rollout via Rollout-Gate §8) |
| **Scope** | Platform-wide (Tooling/DX) |
| **Datum** | 2026-05-30 |
| **Amends** | Policy `claude-skills.md` (Cross-Tool-Prämisse) |
| **Relates** | ADR-229 (`.windsurf`-Distribution right-sized) |

> **Status accepted (2026-05-30) — „Entscheidung ≠ Rollout“ (ADR-211-Muster).** Die *Entscheidung* (CC-first, eine kanonische Quelle, Windsurf-ADR-Subset) ist **ratifiziert** und extern reviewt. Die *Live-Implementierung* ist NICHT „accepted = fertig“, sondern läuft über das **Rollout-Gate (§8)** separat: read-only/Staging-Tooling existiert (`cc-skill-dist` doctor/generate/windsurf-subset), die Live-Aktivierung (Schreiben gegen `~/.claude/commands` + Hybrid-Auflösung + Policy-Kollaps) erfolgt gated. Akzeptiert = Richtung verbindlich, nicht Rollout abgeschlossen.

## 1. Kontext

### 1.1 Alte Prämisse (tot)
Skills lagen als **Windsurf-Workflow-Format** (`.windsurf/workflows/*.md`) als SSoT vor, weil **zwei
Coding-Tools** (CC + Windsurf) sie brauchten: CC via `~/.claude/commands/`-Symlinks, Windsurf via
per-Repo `.windsurf/workflows/`. Policy: `claude-skills.md` („verfügbar in **beiden** Tools").

### 1.2 Neue Basis (2026-05-30)
Coding läuft **nur über CC**; **Windsurf nur für ADR/Review**. Die Cross-Tool-Prämisse entfällt.

### 1.3 Belegte Ist-Probleme (Audit-Analyse 2026-05-30)
- **`claude-skills.md` existiert ≥4-fach mit divergierendem Wortlaut:** platform `main` `policies/`,
  `.claude/policies/`, `docs/policies/`, via `platform-pinned/policies/`, und `~/.claude/policies/`.
- **`~/.claude/commands/` = historischer Hybrid:** **28 Symlinks + 40 statische Kopien**. *(Korrektur nach R1-Forensik 2026-05-30: das zunächst berichtete „live 0/0“ war ein `find`-Messartefakt — **kein rogue Rewriter**.)* Die Kopien sind **statische Snapshots vom Skill-Erstelltag** (aktualisieren sich nicht bei späterer Quell-Änderung → **stale-prone**); die Symlinks zeigen auf einen **branch-volatilen** Arbeits-Checkout → **intermittierendes Dangling**.
- **Branch-volatile Quelle:** CC-Symlinks zeigen in einen **Arbeits-Checkout**, dessen Branch im
  Minutentakt wechselt (parallele Sessions) → CC-Skills **nicht-deterministisch**.
- **Deklaration ≠ Realität:** Policy nennt SSoT `platform-workflows` (Worktree), genutzt wird
  `platform` (primary). Beide volatil.
- **Stabil/kanonisch ist faktisch nur:** platform **`main`** `.windsurf/workflows/` (**69** Workflows).
  (Die zuvor vermutete „Main-Drift" war ein Messartefakt aus Feature-Branch-Checkouts — `main` ist vollständig.)

## 2. Entscheidung (Vorschlag): CC-first
1. **Eine kanonische Quelle, auf konkreten Commit aufgelöst (REC-2):** platform `main` `.windsurf/workflows/` — der Generator liest `main`, **installiert aber den resolved Commit** und hält ihn im Manifest fest (nicht „semantisch main"). *Phase-2-Watchpoint (REC-3): den Windsurf-benannten Pfad in einen **tool-neutralen `skills/`-Pfad** umbenennen (Tool-Leak vermeiden) — nicht Voraussetzung für ADR-230.*
2. **Deterministische CC-Distribution — EINE Form, kein Hybrid (REC-1):** Default = **generierte Kopien** in `~/.claude/commands/`, jede mit Header `generated: true / source_commit / source_path / content_hash / do_not_edit` (REC-14). Erzeugung **atomar + gelockt** (Staging → validieren → Rename/Swap, REC-6), globaler Write **serialisiert** (REC-19); Ziel trägt **`MANAGED_BY`** (erlaubter Writer, Commit, Regen-Kommando, REC-5). Der **historische Hybrid wird aufgelöst** (keine statischen stale-Kopien, keine Symlinks auf volatilen Checkout); **fail-closed** (REC-4): bis Hybrid aufgelöst + Quelle branch-stabil gilt der Installer **nicht** als akzeptiert.
3. **Windsurf = generiertes ADR-Review-Subset über Frontmatter-Tags** (`tool_targets: [windsurf-review]`), **nicht** Dateinamen-Globs (REC-10) → Windsurfs globale Location, kein per-Repo. **Windsurf ist kein Coding-Ziel mehr** (REC-15 — schützt ADR-229 vor Rückabwicklung).
4. **Policy-Kollaps:** `claude-skills.md` auf **eine** kanonische Kopie; übrige Duplikate → **Pointer-Stubs/Weiterleitungen** statt stilles Löschen (REC-11), damit alte Links/gepinnte Worktrees nicht brechen. Deklaration = Realität.

## 2a. Betriebsvertrag (aus externer Review, alle `[valid]`)
- **„Deterministisch" (Def., REC-20):** gleicher `source_commit` + gleiche Generator-Version ⇒ **bit-identische** Zielinhalte **und** identisches Manifest.
- **Manifest (REC-7):** `source_repo`, `source_commit`, `generator_version`, `timestamp`, `skill_count`, `file_list`, `hashes`, `target_type`.
- **Integrität (REC-13):** Ziel-Dateien gegen Manifest-Hash prüfen; Handänderung im generierten Ziel verboten (`do_not_edit`).
- **Drift/Health (REC-9/17):** `doctor`/CI über {Quelle, Manifest, commands, Windsurf-Subset, Policy}; **pre-session-Check** meldet fremdbeschriebenen `~/.claude/commands` sofort.
- **Rollback (REC-18):** vorheriges Manifest reaktivierbar.
- **Runtime-Discovery (REC-12):** Quelle/CC-Ziel/Windsurf-Location zur Laufzeit auflösen (kein Hardcode).
- **Deferred (spätere Iteration):** content-addressed Install + atomarer Pointer (OOB-3); per-Session-Wrapper (OOB-4) — für ADR-230 zu invasiv.

## 3. Betrachtete Alternativen
| Option | Kern | Verdikt |
|---|---|---|
| Status quo (dual-tool, multi-copy) | belassen | **Verworfen** — driftet aktiv, dient totem Use-Case |
| Nur Quellen konsolidieren, `.windsurf`-Format als SSoT behalten | Teil-Fix | unzureichend — Windsurf-Zentrik bleibt trotz CC-only-coding |
| Voll **CC-native** (eigenes Skills-Repo/Format) | sauberste Trennung | mehr Migration; als Endausbau denkbar, nicht zwingend für den Kern |
| **CC-first, platform-main als Quelle** (gewählt) | eine Quelle, deterministisch, Windsurf-Subset | **Gewählt** |

## 4. Begründung
„Erst konsolidieren (A), dann Architektur (B)" ist **logisch unmöglich**, solange keine *eine* Quelle
existiert — jede Einzeländerung erzeugt nur eine weitere driftende Kopie oder wird vom Live-Mutator
überschrieben (empirisch beim Versuch bestätigt). ADR-230 **erschafft das Ziel**, in das konsolidiert wird.

## 5. Implementation (= das frühere „A", nach Acceptance, einmal & deterministisch)
1. **Hybrid auflösen + Quelle branch-stabil pinnen** — *R1-Forensik (2026-05-30): kein rogue Rewriter (Messartefakt); Ist = statische-Kopie-Hybrid + Symlinks auf volatilen Checkout. Kopie-Schreiber = CC-Skill-Registrierung beim Anlegen (statisch), kein Daemon.*
2. Kanonische Quelle **branch-stabil pinnen** (Klon/Pin von platform `main`).
3. `~/.claude/commands/` **deterministisch generieren** (kein Hybrid, kein Fremd-Mutator).
4. **Policy-Kopien auf eine kollabieren** (claude-policy-Sync + pinned-worktree berücksichtigen).
5. **Windsurf-ADR-Subset generieren**.

> **Gate nach Schritt 1 (REC-16):** Generation/Policy-Kollaps erst, **wenn der Hybrid aufgelöst + die Quelle branch-stabil** ist (R1 verstanden, kein Blocker mehr).

## 6. Risiken
- **R1 (verstanden, kein Blocker):** *Kein* rogue Rewriter (war `find`-Messartefakt). Reale Risiken: (a) **stale statische Kopien** (Snapshot-Hybrid); (b) **Symlinks auf branch-volatilen Checkout** (intermittierendes Dangling). Beide behebt der Betriebsvertrag (generierte Kopien+Hash; branch-stabile resolved-Commit-Quelle).
- **R2:** Branch-stabile Quelle braucht einen Checkout/Klon, der **nicht** für Feature-Arbeit benutzt wird.
- **R3:** Policy-Kollaps muss `~/.claude/bin/claude-policy`-Sync + `platform-pinned`-Worktree einbeziehen, sonst Re-Drift.

## 7. Konsequenzen
- **Positiv:** deterministische CC-Skills; Single-Source statt ≥4 Kopien; Windsurf schlank (ADR-Subset); tote Dual-Tool-Wartungslast (Worktree-SSoT, per-Repo-Distribution) entfällt; Deklaration = Realität.
- **Trade-offs:** Migrationsaufwand; der unbekannte Mutator muss gezähmt werden.
- **Nicht in Scope:** Inhalt/Governance einzelner Skills; ADR-229-`.windsurf`-Untrack (bereits erledigt).

## 8. Rollout-Gate (Entscheidung ≠ Rollout — gilt für die Live-Aktivierung, nicht die Entscheidung)
- [ ] **Hybrid aufgelöst:** Ziel einheitlich generiert+gehasht (keine stale Kopien, keine dangling Symlinks); Quelle branch-stabil; pre-session-Drift-Check aktiv (REC-4/17).
- [ ] **Eine Form, kein Hybrid:** generierte Kopien mit Header; **keine dangling Symlinks**; jede Datei aus Manifest ableitbar; erwartete Anzahl erklärbar (REC-1/8).
- [ ] **Resolved-Commit-Pin** im Manifest; „deterministisch" erfüllt (bit-identisch bei gleichem Commit+Generator, REC-2/20).
- [ ] **Manifest + Integritäts-Hash + `MANAGED_BY`** vorhanden (REC-5/7/13).
- [ ] **`doctor`/CI-Drift-Check** grün über Quelle/Manifest/commands/Windsurf-Subset/Policy (REC-9).
- [ ] **`claude-skills.md` auf eine Kopie kollabiert** (übrige = Pointer-Stubs); Deklaration = Realität (REC-11).
- [ ] **Windsurf-Subset** via Frontmatter-Tags generiert; kein per-Repo `.windsurf` (REC-10).
- [ ] **Rollback** (vorheriges Manifest reaktivierbar) getestet (REC-18).

## 9. Glossar
| Begriff | Bedeutung |
|---|---|
| **SSoT** | Single Source of Truth |
| **Hybrid** | `~/.claude/commands` teils Symlinks, teils Kopien (drift-anfällig) |
| **Hybrid** (R1) | `~/.claude/commands` = 28 Symlinks (→ volatiler Checkout) + 40 statische Kopien (stale-prone); kein rogue Rewriter (Messartefakt) |
| **Subset** | kuratierte ~9 ADR/Review-Workflows für Windsurf |

## 10. Referenzen
- Platform-Audit 2026-05-30 (`platform/audits/platform-audit-2026-05-30.md`).
- Policy `claude-skills.md` (wird durch diesen ADR amendiert).
- ADR-229 (`.windsurf`-Distribution right-sized — Schritt 1 = Untrack erledigt).

## Anhang: Externer Review (Rückfluss-Tagging, 2026-05-30)
Cross-Provider-Zweitmeinung via `/adr-handoff-extern`; Briefing `~/shared/adr-handoff-ADR-230-2026-05-30.md`.
Empfehlung **überarbeiten** — Richtung richtig, aber „Entscheidung → Betriebsvertrag" nötig. **~20/20 RECs `[valid]`**
(eingearbeitet in §2/§2a/§5/§8), 2 OOB **deferred** (content-addressed Install OOB-3; per-Session-Wrapper OOB-4).
Kernschärfungen: generierte-Kopien-mit-Header statt „Symlink ODER Kopie"; resolved-Commit-Pin; atomic+lock+`MANAGED_BY`;
Manifest + Integrität + Drift-Doctor; Subset via Frontmatter-Tags; Policy-Kollaps via Pointer-Stubs; R1 fail-closed-Gate.

## 11. Changelog
- 2026-05-30: Initial (Proposed). Aus Audit-Analyse auf neuer Basis (Windsurf nur ADR/Review). Zur externen Zweitmeinung via `/adr-handoff-extern` vorgesehen.
- 2026-05-30: **R1-Korrektur** (Forensik) — „unidentifizierter Live-Rewriter (Blocker)“ war ein `find`-Messartefakt; Ist = statische-Kopie-Hybrid + branch-volatile Symlinks (kein rogue Mutator) → R1 von „Blocker“ auf „verstanden“ herabgestuft.
- 2026-05-30: Externe Review (20 RECs, alle `[valid]`) über Rückfluss-Gate eingearbeitet → **Betriebsvertrag** (§2a): generierte Kopien+Header, resolved-Commit-Pin, atomic/lock/`MANAGED_BY`, Manifest+Integrität+Drift-Doctor, Frontmatter-Tag-Subset, Pointer-Stub-Kollaps, R1 fail-closed; Acceptance verschärft. Bleibt `proposed`.
- 2026-05-30: **Status → accepted** („Entscheidung ≠ Rollout“, ADR-211-Muster): CC-first-Entscheidung ratifiziert; Live-Rollout über das §8-Rollout-Gate separat. tool_targets-Tags gesetzt (#350); Tooling (doctor/generate/windsurf-subset) read-only/staging auf main.
