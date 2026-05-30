---
status: proposed
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
| **Status** | Proposed |
| **Scope** | Platform-wide (Tooling/DX) |
| **Datum** | 2026-05-30 |
| **Amends** | Policy `claude-skills.md` (Cross-Tool-Prämisse) |
| **Relates** | ADR-229 (`.windsurf`-Distribution right-sized) |

> **Status proposed.** Zielbild-Entscheidung. Implementierung (= das frühere „Konsolidierungs-A")
> **erst nach Acceptance** — weil sie eine kanonische Quelle voraussetzt, die heute nicht existiert.

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
- **`~/.claude/commands/` wird live umgeschrieben:** Komposition kippte **mitten in der Messung**
  von 28 Symlinks + 40 Kopien → 0/0 (bei 68 Glob-Treffern). Mechanismus **unidentifiziert**
  (nicht die `~/.claude/bin/`-Skripte); Symlink/Kopie-**Hybrid**, teils **dangling**.
- **Branch-volatile Quelle:** CC-Symlinks zeigen in einen **Arbeits-Checkout**, dessen Branch im
  Minutentakt wechselt (parallele Sessions) → CC-Skills **nicht-deterministisch**.
- **Deklaration ≠ Realität:** Policy nennt SSoT `platform-workflows` (Worktree), genutzt wird
  `platform` (primary). Beide volatil.
- **Stabil/kanonisch ist faktisch nur:** platform **`main`** `.windsurf/workflows/` (**69** Workflows).
  (Die zuvor vermutete „Main-Drift" war ein Messartefakt aus Feature-Branch-Checkouts — `main` ist vollständig.)

## 2. Entscheidung (Vorschlag): CC-first
1. **Eine kanonische Quelle:** platform **`main` `.windsurf/workflows/`** — **branch-stabil** referenziert
   (Commit/Tag-Pin oder dedizierter read-only-Klon auf `main`), **nicht** ein Feature-Branch-Arbeits-Checkout/Worktree.
2. **Deterministische CC-Distribution:** `~/.claude/commands/` wird aus **dieser einen** Quelle erzeugt —
   **einheitlich** (all-Symlink **oder** generierte Kopien mit Commit-Pin), **kein Hybrid**. Der
   unidentifizierte Live-Rewriter wird **identifiziert und ersetzt/abgeschaltet**.
3. **Windsurf = generiertes ADR-Review-Subset** (~9 Workflows: `adr*`, `*review`, `challenger`, `curator`)
   in Windsurfs globaler Location (`~/.codeium/windsurf/windsurf/workflows/`). Kein per-Repo, kein Voll-Satz.
   Zweck: Cascade als **Zweit-Agent-Perspektive** für ADR-Review (analog externer LLM-Review).
4. **Policy-Kollaps:** `claude-skills.md` auf **eine** kanonische Kopie reduzieren (übrige → Symlink/entfernt);
   Deklaration = gelebte Realität; Cross-Tool-Prämisse → CC-first.

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
1. **Rewriter identifizieren** (welcher Hook/Mechanismus schreibt `~/.claude/commands`?) — Voraussetzung für alles.
2. Kanonische Quelle **branch-stabil pinnen** (Klon/Pin von platform `main`).
3. `~/.claude/commands/` **deterministisch generieren** (kein Hybrid, kein Fremd-Mutator).
4. **Policy-Kopien auf eine kollabieren** (claude-policy-Sync + pinned-worktree berücksichtigen).
5. **Windsurf-ADR-Subset generieren**.

## 6. Risiken
- **R1 (Blocker):** Solange der `commands`-Rewriter unidentifiziert ist, gibt es **kein** deterministisches Ziel.
- **R2:** Branch-stabile Quelle braucht einen Checkout/Klon, der **nicht** für Feature-Arbeit benutzt wird.
- **R3:** Policy-Kollaps muss `~/.claude/bin/claude-policy`-Sync + `platform-pinned`-Worktree einbeziehen, sonst Re-Drift.

## 7. Konsequenzen
- **Positiv:** deterministische CC-Skills; Single-Source statt ≥4 Kopien; Windsurf schlank (ADR-Subset); tote Dual-Tool-Wartungslast (Worktree-SSoT, per-Repo-Distribution) entfällt; Deklaration = Realität.
- **Trade-offs:** Migrationsaufwand; der unbekannte Mutator muss gezähmt werden.
- **Nicht in Scope:** Inhalt/Governance einzelner Skills; ADR-229-`.windsurf`-Untrack (bereits erledigt).

## 8. Acceptance Criteria (proposed bis alle grün)
- [ ] **`commands`-Rewriter identifiziert + kontrolliert** (R1-Blocker).
- [ ] **Eine kanonische, branch-stabile Quelle**; `~/.claude/commands/` deterministisch (kein Hybrid, kein dangling).
- [ ] **`claude-skills.md` auf eine Kopie kollabiert**; Deklaration = gelebte Realität.
- [ ] **Windsurf-ADR-Subset** generiert; kein per-Repo `.windsurf`.

## 9. Glossar
| Begriff | Bedeutung |
|---|---|
| **SSoT** | Single Source of Truth |
| **Hybrid** | `~/.claude/commands` teils Symlinks, teils Kopien (drift-anfällig) |
| **Rewriter** | unidentifizierter Prozess, der `~/.claude/commands` live mutiert |
| **Subset** | kuratierte ~9 ADR/Review-Workflows für Windsurf |

## 10. Referenzen
- Platform-Audit 2026-05-30 (`platform/audits/platform-audit-2026-05-30.md`).
- Policy `claude-skills.md` (wird durch diesen ADR amendiert).
- ADR-229 (`.windsurf`-Distribution right-sized — Schritt 1 = Untrack erledigt).

## 11. Changelog
- 2026-05-30: Initial (Proposed). Aus Audit-Analyse auf neuer Basis (Windsurf nur ADR/Review). Zur externen Zweitmeinung via `/adr-handoff-extern` vorgesehen.
