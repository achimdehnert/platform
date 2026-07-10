# Policy: Claude-Code Skills (Slash-Commands)

**Trigger words:** skill, slash command, /command, workflow, cc-skill

## Was ist eine CC-Skill?

Markdown-Workflow mit YAML-Frontmatter. **Kanonische Quelle:** `platform` `main` `.windsurf/workflows/` (branch-stabil, resolved Commit) — **nicht** der `platform-workflows`-Worktree (Coding-Ära-Altlast).
- **Claude Code (primär):** verteilt nach `~/.claude/commands/` über `cc-skill-dist` (`generate.py`/`doctor.py`, MANAGED-Footer + Manifest) — CC-first, ADR-230.
- **Windsurf (nur ADR/Review):** Windsurf wird **nicht mehr zum Coden** genutzt. Es erhält ausschließlich das **Review-Subset** via `windsurf-subset.py` (`tool_targets: [windsurf-review]`), nicht alle Skills (ADR-229).

Abgrenzung zu anderen Konzepten:
- **Anthropic Agent Skills** (`~/.claude/skills/<name>/SKILL.md`, ZIP-`.skill`) — **eigener Artefakttyp**, nicht zu verwechseln mit Slash-Commands. User-level → in JEDER Session / jedem Repo / jeder Org aktiv, **ohne Repo-Kopie**. Kanonik = `platform main skills/<name>/SKILL.md`; Verteilung über `cc-skill-dist --kind skills` (s. „Verteilung"). Cross-tool (auch ChatGPT/Gemini paste-basiert). Beispiel: `antwort-modus-schablone` (Antwort-Format).
- **Django Platform-Agents** (`dev-hub/apps/<agent>/`, siehe `platform-agents.md`) — Headless, scheduled, lange Laufzeit
- **CC-Sub-Agents** (`~/.claude/agents/`) — Claude-only, isolierter Context, kein Cross-Tool

> **Enterprise-weit ≠ in N Repos kopieren.** Eine Agent-Skill (oder ein Slash-Command) wird **nicht** in jedes der ~60 Repos committet — das erzeugt genau die Kopien-Drift, die SSoT vermeidet. „Verfügbar in allen Repos/Orgs" liefert der **user-level Install pro Maschine** (CC lädt `~/.claude/skills` + `~/.claude/commands` in jeder Session, unabhängig vom Repo). Kanonik bleibt **eine** Quelle in `platform`; `cc-skill-dist` generiert pro Maschine. Repo-lokale Kopie nur, wenn „clone → sofort da ohne Install" wirklich gebraucht wird, und dann in **wenige Hub-Repos**, nie flächig.

## Wann eine neue Skill bauen?

CC-Skill ist die **Default-Antwort** bei:
- Wiederkehrender Workflow >3× pro Woche manuell ausgeführt
- Kombination aus 2+ MCP-Calls + Output-Aggregation
- Wiederverwendbarkeit über CC-Sessions/Maschinen hinweg (CC-first; Windsurf nur für ADR/Review-Skills relevant)
- Read-only-Analyse oder Reporting

**Nicht** als Skill:
- Single-MCP-Wrapper (direkter MCP-Call genügt)
- Einmaliges Skript (Bash-Snippet in PR-Beschreibung)
- Anything-Write ohne klare Gates (Skill darf write, aber muss Gate explizit machen)

## Pflicht-Strukturelemente

```markdown
---
description: <1-line, action-orientiert, ≤120 Zeichen>
mode: read-only | write
---

# /skill-name — <Tagline>

> **Wann:** ...
> **Wann NICHT:** Verweis auf abgrenzende Skills

## Verwendung
\`\`\`
/skill-name <args>
\`\`\`

## Step 0: Repo-Kontext aus project-facts.md
... (NIEMALS hardcoden)

## Step N: <Schritte>

## Output-Format
\`\`\`
<Schema des Outputs>
\`\`\`

## Anti-Patterns
- ❌ ...

## Changelog
- YYYY-MM-DD: ...
```

## MCP-Signaturen — Pflicht-Verifikation

**Vor Commit:** Jeden im Skill genannten MCP-Call mit dem aktuellen Schema verifizieren. Wrong-Signature-Bugs sind häufig und CI-relevant.

Verifikations-Optionen:
1. `ToolSearch` mit `select:<mcp-tool-name>` und Argument-Schema gegen Skill abgleichen
2. Dry-Run mit echtem MCP-Call im Dogfood-Test
3. (Future) CI-Smoke-Test gegen Schema-Snapshot

## Read-Only Default

Skills sind by-default **read-only**. Write-Modus erfordert:
- Explizites `mode: write` im Frontmatter
- Anti-Pattern-Sektion mit konkreten "darf NICHT" Aufzählungen
- Idempotenz-Garantie ODER explizites "non-idempotent — confirm before re-run"

## Hardcoding-Verbot

**NIEMALS** in Skills:
- Repo-Pfade (`~/github/platform/docs/adr/`)
- MCP-Prefixes (`mcp2_`)
- Owner/Org-Namen (`achimdehnert`)
- Server-IPs

Quelle: **project-facts.md** (always_on rule im Ziel-Repo). Skill liest Werte zur Laufzeit aus.

**Ausnahme maschinen-level Skills (2026-07-10):** Skills ohne Repo-Bezug (z. B. Mail-Transport
`/send-mail`) haben kein sinnvolles project-facts-Ziel-Repo — ihre Config liegt in einer
**maschinen-lokalen, nicht-geheimen** Datei `~/.claude/<topic>.env` (Werte), Credentials separat
unter `~/.secrets/` (nie im Skill, nie in stdout). Das Hardcoding-Verbot gilt unverändert für den
Skill-**Text**; nur die Quelle wechselt von project-facts.md auf die Maschinen-Config. Jede neue
maschinen-level Config-Quelle wird HIER im Changelog vermerkt (nicht nur lokal in der Skill-Datei
begründet — Lehre retro f4a546 #5, `policy-exception-not-backported`). Präzedenz: `/send-mail`
(`~/.claude/mail.env`: SMTP_HOST/SMTP_PORT/MAIL_FROM/MAIL_CREDS_FILE).
**Registry-Schwelle (retro f4a546-incr #7):** Solange nur EINE Maschinen-Config existiert, reicht
der Changelog-Vermerk (YAGNI). **Ab der zweiten** `~/.claude/<topic>.env` wird eine strukturierte
Registry `~/.claude/machine-configs.yaml` angelegt (je Eintrag: Datei, Konsument-Skill, Keys,
Credentials-Verweis) und hier verlinkt — damit künftige Sessions einen abfragbaren Index haben
statt Changelog-Prosa zu greppen.

## 🌀-Memory-Zitate

Skills die auf Drift-Lehren verweisen sollen **echte Memory-IDs** zitieren, nicht erfundene Namespaces. Beispiel:
- ✅ `agent_memory_search(query="ADR-141 vs 179 canonical numbers")` (semantic)
- ❌ `agent_memory_search(query="drift:adr-canonical-numbers")` (kein realer Namespace)

Drift-Lehren leben in lokaler CC-Memory bis sie via `agent_memory_upsert` in Orchestrator promoted werden. Skill darf beide Quellen ansprechen, aber muss den **Discovery-Pfad** beschreiben (CC-Memory zuerst, Fallback Orchestrator).

## Pflicht-Review-Gate

PR der eine neue Skill enthält oder eine bestehende ändert:
1. Mindestens **1 Dogfood-Test** im PR-Body dokumentiert (Tool-Output zitiert)
2. MCP-Signaturen verifiziert (siehe oben)
3. Anti-Patterns-Sektion vollständig
4. Output-Format als Code-Block exemplifiziert
5. CHANGELOG-Eintrag in der Skill-Datei
5b. **Lokaler Testlauf vor dem ersten Push (retro f4a546 #6, Familie `lint-failure-no-local-gate`):**
   `make test` bzw. `pytest tools/tests/` lokal grün, BEVOR der Branch gepusht wird — der
   Workflow-Index-Vollständigkeitstest und die Tool-Unit-Tests sind in <30 s lokal prüfbar;
   `py_compile` allein ist KEIN hinreichender Vorab-Check. (Der Pre-Push-Hook schließt Tests
   bewusst aus — dieser Punkt ist die manuelle Pflicht, die diese Lücke deckt.)
6. **Tracking-Anker bei substanzieller Arbeit (session-retro 2026-06-05, F-F):** Mehrstündige oder cross-concern Skill-/Tooling-Arbeit bekommt einen GitHub-Issue als Anker — ODER der PR-Body verlinkt die externen Belege (z. B. `~/shared`-Reviews, Dogfood-Reports) **explizit**. Sonst ist die Arbeit nur über PR-Body + lokale Artefakte rekonstruierbar und für Außenstehende unsichtbar.

## Verteilung (ADR-230 CC-first)

`cc-skill-dist` kennt zwei Lanes über `--kind`:

**Lane `commands` (Default) — Slash-Commands.** Quelle = `platform main .windsurf/workflows/` → `~/.claude/commands/` (flach):
- `generate.py` — deterministische Kopien mit MANAGED-Footer (`source_commit`/`content_hash`/`do_not_edit`) + `manifest.json`; atomarer Swap mit `.bak`; Live nur mit `--allow-live` (gegatet, ADR-230 §8).
- `doctor.py` — read-only Drift-Diagnose Quelle ↔ `~/.claude/commands` (footer-aware; CI-Round-Trip-Gate `cc-skill-dist-doctor.yml`).
- Windsurf-Review-Subset: `windsurf-subset.py` (`tool_targets: [windsurf-review]`).

**Lane `skills` — Anthropic Agent Skills.** Quelle = `platform main skills/<name>/SKILL.md` → `~/.claude/skills/<name>/SKILL.md` (verschachtelt, ein Verzeichnis je Skill):
- `generate.py --kind skills --target ~/.claude/skills` (Live nur mit `--allow-live`) — gleicher MANAGED-Footer/Manifest/Swap; Quelle ist die **nackte** `SKILL.md` (kein Footer), die Kopie trägt ihn.
- `doctor.py --kind skills` — Drift-Diagnose Quelle ↔ `~/.claude/skills` (verzeichnis-basiert; Relativlink-Guard greift hier NICHT, da Skill-Verzeichnisse gebündelte Referenzen tragen dürfen).
- ChatGPT/Gemini: **kein** Verteil-Tooling (kein Datei-Konsum-Mechanismus) — paste-aus-der-Kanonik bzw. einmalig als Custom GPT / Gem. Bewusst aus dem Verteil-Scope.

**Tooling-Konventionen (session-retro 2026-06-05):**
- **Neue Lane/Mode ⇒ Gate wächst mit (F-A):** Erweitert ein PR `cc-skill-dist` um eine Lane (`--kind …`), müssen im **selben PR** ein Round-Trip-Step der Lane, der `paths:`-Trigger (`skills/**`) **und** ein Test mit. Ein grüner Gate-**Name** ohne Lane-Coverage ist eine Schein-Garantie. Verankert in `cc-skill-dist-doctor.yml` (beide Lanes + Unit-Tests).
- **Kein `-prototype` im Live-Output (F-C):** Sobald `generate.py` per `--allow-live` real verteilt, trägt `GENERATOR_VERSION` **kein** `-prototype`-Suffix mehr — es landet sonst wörtlich im Live-`manifest.json`/`MANAGED_BY`. DoD vor Live-Rollout: Suffix entfernen.
- **Tooling getrennt von Content/Policy (F-H):** Änderungen am Verteil-Tooling (CI-testbar) und Skill-/Policy-**Content** (semantisch) gehören in **getrennte PRs** — Tooling zuerst grün, dann der erste Konsument. Verhindert, dass ein Tooling-Revert Content/Policy mitreißt. (Ausnahme dokumentieren, wenn „erster Konsument" die Bündelung erzwingt.)

Der frühere `~/.claude/commands` → `platform-workflows`-Symlink ist die **Coding-Ära-Altlast** und wird durch das gegatete Live-Rollout abgelöst; Cross-Machine-Sync läuft dann ebenfalls über `generate.py` je Maschine.

## Changelog

- 2026-05-15: Initial. Geschrieben nach Dogfood-Findings der ersten 2 CC-Skills (`/adr-curator`, `/adr-challenger`, PR #168). Schließt Policy-Lücke die `platform-agents.md` offen ließ.
- 2026-05-15: Pushed to orchestrator memory (`entry_key: policy:claude-skills`).
- 2026-05-30: Auf ADR-229/230 (CC-first) ausgerichtet — Quelle = `platform main` (nicht `platform-workflows`-Worktree), Windsurf nur ADR/Review-Subset (nicht mehr Coding), Verteilung über `cc-skill-dist`. Stale „beide Tools / platform-workflows / Plugin-Backlog"-Prämisse korrigiert.
- 2026-06-05: **Agent-Skill-Lane ergänzt.** Anthropic Agent Skills (`~/.claude/skills/<name>/SKILL.md`) als eigener Artefakttyp mit Kanonik `platform main skills/` + `cc-skill-dist --kind skills` (generate+doctor verzeichnis-basiert, Generator 0.2.0). „Enterprise-weit = user-level Install pro Maschine, nicht Kopie in N Repos" als Leitsatz verankert. Erster Konsument: `antwort-modus-schablone` v2.3. Folgt dem bestehenden cc-skill-dist-Muster → kein ADR (Policy-Update genügt, `adr-threshold`).
- 2026-06-05: **Konventionen aus session-retro** (`~/shared/session-retro-2026-06-05-platform-fde7ff.md`): Review-Gate §6 Tracking-Anker (F-F); Tooling-Konventionen Lane⇒Gate-wächst-mit (F-A), kein `-prototype` im Live-Output (F-C), Tooling-PR getrennt von Content/Policy (F-H). F-A bereits umgesetzt (PR #480: beide Lanes + Unit-Tests im Gate).
- 2026-07-10 (2): **Registry-Schwelle für Maschinen-Configs** (retro f4a546-incr #7, `machine-config-no-registry`): ab der 2. `~/.claude/<topic>.env` wird `~/.claude/machine-configs.yaml` Pflicht — definierter Kipp-Punkt statt unbegrenzter Changelog-Prosa.
- 2026-07-10: **Maschinen-level-Config-Ausnahme + Review-Gate 5b** (aus `docs/retros/session-retro-2026-07-10-platform-f4a546.md`, Befunde #5/#6): Skills ohne Repo-Bezug dürfen `~/.claude/<topic>.env` als Config-Quelle nutzen (Hardcoding-Verbot für den Skill-Text unverändert; jede neue Quelle wird hier vermerkt). Review-Gate 5b: lokaler `make test`/`pytest tools/tests/`-Lauf vor dem ersten Push. Präzedenz-Konsument: `/send-mail` (PR #1039, Härtung PR #1050).
