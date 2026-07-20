# cc-skill-dist — CC-Skill-Distribution-Tooling (platform:ADR-230)

Werkzeuge zur deterministischen Verteilung aus der **einen kanonischen Quelle** (platform `main`)
— gemäß ADR-230 (CC-first). Drei Lanes über `--kind`:

| `--kind` | Quelle (platform) | Live-Ziel | Form |
|----------|-------------------|-----------|------|
| `commands` (Default) | `.windsurf/workflows/*.md` | `~/.claude/commands/` | flach (Slash-Commands) |
| `skills` | `skills/<name>/SKILL.md` | `~/.claude/skills/<name>/SKILL.md` | verschachtelt (Anthropic Agent Skills) |
| `hooks` (ADR-258) | `tools/hooks/*.sh` | `~/.claude/hooks/managed/` | flach, ausführbar (0755), Shell-#-Footer |

> **Warum `managed/`-Unterverzeichnis:** `generate.py` macht einen atomaren Verzeichnis-**Swap**.
> `~/.claude/hooks/` enthält auch hand-gepflegte Hooks (PreToolUse/SessionStart/…) — ein Swap dort
> würde sie wegwischen. Die Lane besitzt darum exklusiv `~/.claude/hooks/managed/`; settings.json
> verweist auf `~/.claude/hooks/managed/reap_worktrees.sh`.

**Hooks: Verteilung ≠ Enforcement (ADR-258).** Die `hooks`-Lane verteilt nur das Skript;
ein Hook feuert erst, wenn `~/.claude/settings.json` ihn als Event-Eintrag (z. B. `SessionEnd`)
verdrahtet. Das Wiring bleibt ein **bewusster Akt pro Maschine** (settings.json ist secret-haltig,
keine Org-Automatik schreibt rein). Aktivierung vorbereiten:
```bash
python3 tools/cc-skill-dist/bootstrap-hook.py      # zeigt den exakten settings-Patch, schreibt NIE
python3 tools/cc-skill-dist/doctor.py --kind hooks # prüft Datei + verpflichtendes settings-Wiring (REC-3)
```

**Enterprise-weit = user-level Install pro Maschine, NICHT Kopie in N Repos.** CC lädt
`~/.claude/skills` + `~/.claude/commands` in jeder Session/jedem Repo/jeder Org — ein Install
deckt alles ab, die Kanonik bleibt SSoT in platform (Drift-Vermeidung). Beispiele:
```bash
python3 tools/cc-skill-dist/generate.py --kind skills --target /tmp/skills-staging
python3 tools/cc-skill-dist/doctor.py   --kind skills        # Drift Quelle ↔ ~/.claude/skills
```

## `doctor.py` — read-only Drift-Diagnose (ADR-230 REC-9)

Vergleicht die branch-stabile Quelle (`origin/main`) mit dem live `~/.claude/commands/`,
**ohne etwas zu ändern**. Meldet stale Kopien, dangling Symlinks, extra/fehlende Skills,
Hybrid-Status und einen Drift-Score.

```bash
python3 tools/cc-skill-dist/doctor.py            # Default: ~/github/platform, ~/.claude/commands, origin/main
python3 tools/cc-skill-dist/doctor.py --ref origin/main
```

Exit-Code: `0` = sauber, `1` = Drift gefunden (CI-tauglich), `2` = Quelle nicht lesbar.

**Dogfood 2026-05-30:** 69 kanonisch / 68 Ziel; 28 Symlinks ok; 35 Kopien fresh, **3 stale**
(`adr-handoff-extern`, `onboard-repo`, `run-local`); 2 extra, 3 fehlend — **Drift-Score 8**.
Belegt empirisch die ADR-230-R1-Realrisiken (statische, stale-prone Kopien).

## Roadmap (nach ADR-230-Acceptance)

- ✅ `generate.py` (**Prototyp, staging-only**) — erzeugt ein Ziel-Verzeichnis deterministisch aus dem
  **resolved Commit**: generierte Kopien mit MANAGED-Footer (`source_commit`/`content_hash`/`do_not_edit`),
  `MANAGED_BY` + `manifest.json`, atomarer Rename-Swap (+ `.bak`). `--target` Pflicht; schreibt **nie**
  nach `~/.claude/commands` ohne `--allow-live`. Dogfood: 69 Skills, Frontmatter intakt, 2× = bit-identisch.
  ```bash
  python3 tools/cc-skill-dist/generate.py --target /tmp/cc-staging
  ```
- ✅ `windsurf-subset.py` (**Prototyp, staging-only**) — generiert das **ADR-Review-Subset** primär über
  Frontmatter-Tag `tool_targets: [windsurf-review]`; **Fallback** = kuratierte Liste (adr*/review/challenger/
  curator), solange keine Tags existieren. Live-Schutz für `~/.codeium/windsurf/windsurf/workflows/`.
  Dogfood: 9 Workflows (Fallback-Modus). **Folge-PR:** `tool_targets`-Tags in die ~9 Quell-Workflows ziehen → Tag-Modus.
  ```bash
  python3 tools/cc-skill-dist/windsurf-subset.py --target /tmp/cc-windsurf-staging
  ```
- Policy-Kollaps (≥ 4 `claude-skills.md`-Kopien → eine + Pointer-Stubs).

> Schreibende Schritte folgen **nach** ADR-230-Acceptance. `doctor.py` ist read-only und schon jetzt nützlich.
