# next-sync

CLI-Helfer, die `NEXT.md` eines Repos aus seiner `AGENT_HANDOVER.md` (führend)
bzw. aus `git log` (Fallback) regenerieren. Konsumiert vom `/next`-Skill
(`.windsurf/workflows/next.md`).

- `claude-next-sync` — regeneriert `NEXT.md` **eines** Repos (idempotent, no-op wenn frisch).
- `claude-next-init` — Bootstrap über **alle** Repos unter `$GITHUB_DIR`; schreibt
  `~/.claude/state/next-roster.md`. Findet `claude-next-sync` im selben Verzeichnis.

**Canonical source = diese Dateien** (versioniert). `~/.claude/bin/claude-next-sync`
und `~/.claude/bin/claude-next-init` sind untrackte Kopien — sollten hierauf zeigen
(gleiches Muster wie [`../claude-policy`](../claude-policy/README.md)):

```bash
ln -sf "$(git rev-parse --show-toplevel)/tools/next-sync/claude-next-sync" \
       ~/.claude/bin/claude-next-sync
ln -sf "$(git rev-parse --show-toplevel)/tools/next-sync/claude-next-init" \
       ~/.claude/bin/claude-next-init
```

> Beide zusammen symlinken — `claude-next-init` ruft `claude-next-sync` aus
> **seinem eigenen** (aufgelösten) Verzeichnis auf.

## Parser-Heuristik (claude-next-sync)

`AGENT_HANDOVER.md` → Top-3-Items für `NEXT.md`. Die Prioritäten-Sektion wird so gewählt:

1. **Vorrang:** exakt `## Prioritäten` (kanonische CC-Konvention, ADR-230).
2. **Fallback:** erste Überschrift, deren **erste zwei Wörter** ein Trigger sind
   (`Priorit|Offen|Nächst|Next|TODO|Slice|Open|Backlog|Known|Aufgaben`).

Der First-Words-Anker verhindert Fehl-Treffer auf Status-Überschriften, die ein
Trigger-Wort nur beiläufig enthalten (z. B. `## Stand — … keine offene Arbeit`).

## Verwendung

```bash
claude-next-sync                 # cwd
claude-next-sync --repo PATH     # spezifisch
claude-next-sync --force         # auch frische NEXT.md neu schreiben
claude-next-init                 # alle Repos + Roster
```

## Stand

- 2026-06-24: Scripts aus `~/.claude/bin/` nach `platform/tools/next-sync/`
  versioniert (waren untracked → Drift-Risiko, ADR-230 §R3). Parser-Sektionswahl
  gehärtet: exakt `## Prioritäten` bevorzugt, Fallback per First-Words-Anker
  statt Substring-Match (fing fälschlich `## Stand … keine offene Arbeit`).
