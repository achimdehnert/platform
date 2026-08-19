# Verifikation 2026-08-19 — Cold-Start-Baseline der 19 aktiv-Pakete (ADR-266, #2075 K2)

**Methode:** `tools/pypi_coldstart_baseline.sh` — je Paket frischer Shallow-Clone
(GitHub, nicht lokaler Klon), Einstiegskommando-Erkennung (`make setup+test` →
`make test` → `pip install -e .[dev]` + `pytest`), Setup und Tests in isoliertem
venv, Timeout 240 s je Schritt. Ein Lauf je Paket (Reproduzierbarkeits-Doppel-Lauf
= Folgeschritt, gehört in CI, nicht in diese Baseline).

**Ergebnis: 16/19 bestehen den deterministischen Cold-Start.**

| Paket | Einstieg | Setup | Tests | Dauer |
|---|---|---|---|---|
| aifw | make test | ok | ok | 41s |
| authoringfw | make test | ok | ok | 11s |
| django-lms-lite | pip+pytest | ok | ok | 14s |
| gpufw | make test | ok | ok | 18s |
| iil-adrfw | make test | ok | ok | 42s |
| iil-codeguard | pip+pytest | ok | ok | 12s |
| iil-doc-templates | pip+pytest | ok | ok | 13s |
| iil-fieldprefill | pip+pytest | ok | ok | 31s |
| iil-ingest | pip+pytest | ok | ok | 14s |
| iil-testkit | make test | ok | ok | 27s |
| illustration-fw | make test | ok | ok | 14s |
| learnfw | make test | ok | ok | 29s |
| outlinefw | make test | ok | ok | 14s |
| promptfw | make test | ok | ok | 15s |
| researchfw | make test | ok | ok | 19s |
| weltenfw | make test | ok | ok | 11s |
| **iil-klickdummy** | make test | ok | **fail** | 10s |
| **iil-reflex** | make test | ok | **fail** | 24s |
| **nl2cad** | make test | ok | **fail** | 12s |

## Fehlerklassen

1. **`.venv`-Hardcode ohne `setup:`-Target** (iil-klickdummy, iil-reflex):
   `make test` ruft `.venv/bin/python`, aber kein Target erzeugt das venv →
   Fehler 127 im frischen Clone. Fix uniform: `setup:`-Target (venv +
   `pip install -e .[dev]`) — Template-Kandidat.
2. **dev-Dependencies nicht im Test-Pfad** (nl2cad): uv legt `.venv` an und
   installiert das Umbrella-Paket, aber kein pytest → `No module named pytest`.
   Fix: dev-Group in das `test:`-Target (uv sync/extra).

## Kontextdatei-Baseline (Contents-API, 2026-08-19)

**AGENTS.md: 1/19** (nur nl2cad) · CLAUDE.md: 7/19 (aifw, promptfw, authoringfw,
iil-testkit, iil-reflex, iil-adrfw, researchfw) · **11/19 haben keine** von beiden.
Schema-Soll: `docs/templates/pkg-AGENTS.md` (pkg-agents-v1), Prüfung:
`tools/check_agents_md.py` (advisory-first).

## Einordnung gegen #2075 K2

Verifiziert: deterministische Cold-Start-Fähigkeit + Kontextdatei-Bestand.
**Nicht** verifiziert (offene K2-Schritte): LLM-Agent-Lauf (T1a) je Paket,
Zweifach-Reproduzierbarkeit in CI, AGENTS.md-Rollout, Mutation-/Property-
Stichprobe auf Kernpaketen. Fix-Backlog der 3 Durchfaller: je Repo-Issue
(verlinkt im PR).
