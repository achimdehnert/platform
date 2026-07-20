# Contributing — achimdehnert/platform

Dies ist das **Plattform-Repo** der iil-Org-Familie:

- **ADRs**: alle Architektur-Entscheidungen (Bestand live: `ls docs/adr/ADR-*.md | wc -l`;
  höchste Nr.: `ls docs/adr/ADR-*.md | grep -oE 'ADR-[0-9]+' | sort -V | tail -1`)
- **Policies**: `policies/*.md` für Cross-Repo-Konventionen
- **Workflows**: `.windsurf/workflows/` — Quelle der Claude-Code-Skills (Windsurf selbst
  nur noch ADR-Review-Subset, kein Coding mehr, ADR-230)
- **Scripts/Checks**: `scripts/checks/*.sh`
- **Schemas**: `schemas/*.json`

## Wo Issues hingehören

Bitte bei jedem Issue prüfen, ob es wirklich plattformweit ist oder ein
konkretes Repo betrifft:

| Issue-Thema | Richtiges Repo |
|---|---|
| `iil-klickdummy` Bug/Feature | [`iilgmbh/iil-klickdummy`](https://github.com/iilgmbh/iil-klickdummy/issues) |
| Klickdummy-spezifisch in meiki-hub | [`meiki-lra/meiki-hub`](https://github.com/meiki-lra/meiki-hub/issues) |
| Klickdummy-spezifisch in writing-hub | [`achimdehnert/writing-hub`](https://github.com/achimdehnert/writing-hub/issues) |
| Klickdummy-spezifisch in risk-hub | [`iilgmbh/risk-hub`](https://github.com/iilgmbh/risk-hub/issues) |
| Klickdummy-spezifisch in ttz-hub | [`ttz-lif/ttz-hub`](https://github.com/ttz-lif/ttz-hub/issues) |
| **Cross-Repo-Konvention / ADR** | hier (platform) ✅ |
| **Plattform-Skill / Workflow** | hier (platform) ✅ |
| **Cross-Repo-Tooling** | hier (platform) ✅ |

## Label-Konvention

Issue-Labels folgen einem konsistenten Schema:

- `priority/P1-high` · `priority/P2-medium` · `priority/P3-low`
- `area/<bereich>` — z. B. `area/adr`, `area/klickdummy`, `area/infra`
- `type/<art>` — `type/bug`, `type/feature`, `type/tracking`, `type/docu`
- `adr-<NNN>-followup` für ADR-bezogenes Tracking
- `keep` — Stale-Bot überspringt (90+30d Auto-Close)
- `tracking` · `roadmap` — langfristige Items, kein Auto-Close

## Stale-Politik

- Issues ohne Aktivität >90 Tage → `stale`-Label + Hinweis-Kommentar
- Nach weiteren 30 Tagen ohne Aktivität → Auto-Close
- Re-Open jederzeit möglich
- Befreit: `keep`, `tracking`, `roadmap`, `priority/P1-high`, `security`,
  `adr-211-followup`, `adr-210-followup`

## Diskussionen vs. Issues

Für allgemeine Fragen, Ideensammlung, „könnte man X machen?" bitte
**Discussions** statt Issues:
https://github.com/achimdehnert/platform/discussions

Issues sind für **konkrete, lösbare** Aufgaben.
