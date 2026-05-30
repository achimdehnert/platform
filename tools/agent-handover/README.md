# agent-handover Generator

Erzeugt/aktualisiert `<repo>/docs/AGENT_HANDOVER.md` mit **verifizierbaren Ankern**
(Branch/SHA/CI/Migrationen/Working-Tree) und **SSoT-Zeigern** (project-facts/ADRs/
Orchestrator), nach der `new-github-project`-Vorlage.

## Prinzip

- **Anker werden gezogen, nicht getippt** (git/gh/Repo-Introspektion) → driftfrei.
- **Auto-Block zwischen Markern** (`AGENT_HANDOVER:AUTO START`…`END`): Re-Runs ersetzen
  nur diesen Block; von Hand gepflegte Abschnitte bleiben erhalten.
- **Uniform über alle Repos** — keine ttz/meiki-Sonderbehandlung (souveränitäts-neutrale
  Doku-/Metadaten-Arbeit; etwaige Sonderlogik ist Zukunfts-Option). `--no-orchestrator`
  für Repos ohne Orchestrator-Bindung (z. B. meiki-hub).

## `--ref` (wichtig für Fremd-Repos)

Ohne `--ref` liest der Generator den **Working-Tree** — steht der auf einem Feature-Branch
oder ist dirty, wären die Anker **stale**. Für Repos, in denen man nicht selbst arbeitet,
daher `--ref origin/main`: liest Anker **read-only aus dem Ref**, ohne den Working-Tree
anzufassen (Branch-Anker = `main`, Working-Tree-Anker = `n/a (Snapshot)`).

```bash
git -C ~/github/<repo> fetch origin main -q
python3 tools/agent-handover/generate.py ~/github/<repo> --ref origin/main
```

## Usage

```bash
# Dry-Run (Default) — generierte Datei auf stdout
python3 tools/agent-handover/generate.py ~/github/<repo> [--ref origin/main]

# Schreiben
python3 tools/agent-handover/generate.py ~/github/<repo> --ref origin/main --write

# Repo ohne Orchestrator-Bindung
python3 tools/agent-handover/generate.py ~/github/<repo> --ref origin/main --write --no-orchestrator
```

## Verhalten bei bestehender Datei

| Zustand | Verhalten |
|---|---|
| keine Datei | neu erstellt (Auto-Block + Platzhalter-Hand-Abschnitte) |
| Datei **mit** Markern | nur Auto-Block ersetzt, Hand-Abschnitte erhalten |
| Datei **ohne** Marker | **Inject:** Auto-Block nach dem H1 eingefügt, restliches Dokument vollständig erhalten |
| `--force` | bestehende Datei mit frischer Vorlage **überschrieben** (Bestand verworfen — bewusst nutzen) |

Der Inject-Modus erhält handkuratierte Legacy-Handover-Docs (Repo-Zweck, Stack, Regeln …)
vollständig und fügt nur den Anker-/SSoT-Block oben hinzu.

## Rollout

Plattformweiter AGENT_HANDOVER-Anker-Rollout, Batch-weise (z. B. erst aktive Django-Hubs).
Pro Repo ein additiver PR; Anker via `--ref origin/main` gezogen; Arbeits-Abschnitte
bleiben „vom Bearbeiter zu füllen".
