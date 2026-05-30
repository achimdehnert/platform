# agent-handover Generator

Erzeugt/aktualisiert `<repo>/docs/AGENT_HANDOVER.md` mit **verifizierbaren Ankern**
(Branch/SHA/CI/Migrationen/Working-Tree) und **SSoT-Zeigern** (project-facts/ADRs/
Orchestrator), nach der `new-github-project`-Vorlage.

## Prinzip

- **Anker werden gezogen, nicht getippt** (git/gh/Repo-Introspektion) → driftfrei.
- **Auto-Block zwischen Markern** (`AGENT_HANDOVER:AUTO START`…`END`): Re-Runs ersetzen
  nur diesen Block; von Hand gepflegte Abschnitte (Offene Aufgaben, Bekannte Probleme,
  Wichtige Befehle) bleiben erhalten.
- **Uniform über alle Repos** — keine ttz/meiki-Sonderbehandlung (souveränitäts-neutrale
  Doku-/Metadaten-Arbeit; etwaige Sonderlogik ist Zukunfts-Option). `--no-orchestrator`
  für Repos ohne Orchestrator-Bindung (z. B. meiki-hub).

## Usage

```bash
# Dry-Run (Default) — gibt die generierte Datei auf stdout aus
python3 tools/agent-handover/generate.py ~/github/<repo>

# Schreiben
python3 tools/agent-handover/generate.py ~/github/<repo> --write

# Bestandsdatei OHNE Marker überschreiben (Pilot-Migration)
python3 tools/agent-handover/generate.py ~/github/<repo> --write --force

# Repo ohne Orchestrator-Bindung
python3 tools/agent-handover/generate.py ~/github/<repo> --write --no-orchestrator
```

## Verhalten bei bestehender Datei

| Zustand | Verhalten |
|---|---|
| keine Datei | neu erstellt (Auto-Block + Platzhalter-Hand-Abschnitte) |
| Datei **mit** Markern | nur Auto-Block ersetzt, Hand-Abschnitte erhalten |
| Datei **ohne** Marker | WARN + Dry-Run-Vorschau; Überschreiben nur mit `--force` |

## Rollout

Gedacht für den plattformweiten AGENT_HANDOVER-Anker-Rollout (Batch-weise, z. B. erst
aktive Django-Hubs). Pro Repo ein additiver PR mit gezogenen Ankern; Arbeits-Abschnitte
bleiben „vom Bearbeiter zu füllen".
