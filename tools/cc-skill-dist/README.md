# cc-skill-dist — CC-Skill-Distribution-Tooling (platform:ADR-230)

Werkzeuge zur deterministischen Verteilung der Skills aus der **einen kanonischen Quelle**
(platform `main` `.windsurf/workflows/`) nach `~/.claude/commands/` — gemäß ADR-230 (CC-first).

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

- `generate.py` — erzeugt `~/.claude/commands/` deterministisch aus dem **resolved Commit**:
  einheitliche generierte Kopien mit Header (`generated/source_commit/content_hash/do_not_edit`),
  atomar + gelockt (Staging → validieren → Swap), `MANAGED_BY`-Datei, Manifest.
- `windsurf-subset.py` — generiert das ADR-Review-Subset über Frontmatter-Tags (`tool_targets`).
- Policy-Kollaps (≥ 4 `claude-skills.md`-Kopien → eine + Pointer-Stubs).

> Schreibende Schritte folgen **nach** ADR-230-Acceptance. `doctor.py` ist read-only und schon jetzt nützlich.
