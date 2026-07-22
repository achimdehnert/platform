# Archiv: `.windsurf/project-facts/` (Windsurf-Ära-Fleet-Übersicht)

Archiviert am 2026-07-21 (platform#1304). Vorher: `platform/.windsurf/project-facts/<repo>.md`,
77 Dateien, zuletzt inhaltlich geändert am 2026-04-28 (`5ee498c`).

## Warum archiviert

Diese Dateien sind der Output von `scripts/generate_project_facts.py`, das im Zuge von
ADR-234 §11.3 nach `scripts/_ARCHIVED/generate_project_facts_api.py` archiviert wird
(platform#1007). Generator und Output gehören zusammen — ein Output ohne lebenden
Generator veraltet still weiter.

**Verifiziert vor dem Move:**

| Prüfung | Befund |
|---|---|
| Konsumenten im Repo (`grep -rn "project-facts/"` über `*.md/*.py/*.sh/*.yml`) | nur Selbstreferenzen in den Dateien selbst — **0 echte Leser** |
| Verteilung in andere Repos (`scripts/sync-repo.sh`) | 0 Treffer — wurde nie verteilt |
| Auto-Load durch Windsurf | nein: kein `trigger: always_on`-Frontmatter (anders als `.windsurf/rules/project-facts.md`) |
| letzte inhaltliche Änderung | 2026-04-28, seither unverändert |

## Nicht zu verwechseln mit dem **lebenden** Artefakt

`<repo>/.windsurf/rules/project-facts.md` — per-Repo, `trigger: always_on`, erzeugt von
`scripts/gen_project_facts.py` (kanonisch laut ADR-234 §11.3, verdrahtet in `bootstrap.sh`
und `tools/session_start_checks.sh`). **Das** ist die Quelle, die Skills wie
`issues-offen` und `kd-scout` meinen, wenn sie „project-facts.md lesen" sagen.

Die beiden Generatoren schreiben unterschiedliche Ziele in unterschiedlichem Format —
ein Umbiegen der alten Header auf `gen_project_facts.py` wäre sachlich falsch gewesen
(siehe Diskussion in platform#1304).

## Rückweg

`git mv _ARCHIVED/project-facts-windsurf .windsurf/project-facts` + Generator aus
`scripts/_ARCHIVED/generate_project_facts_api.py` zurückholen. Der Generator zieht seine
Daten aus GitHub-API + `ports.yaml` + `repos.yaml` und ist damit reproduzierbar.
