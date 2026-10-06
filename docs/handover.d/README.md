# Handover-Fragmente je Sitzung

Jede Sitzung legt hier **eine eigene Datei** an und fasst keine fremde an.
Der Übergabestand wird beim Lesen aus den aktiven Fragmenten zusammengesetzt
und nie committet (render-on-read, [KONZ-platform-027](../konzepte/KONZ-platform-027-handover-fragmente-je-session.md),
Zielzustand [#1944](https://github.com/achimdehnert/platform/issues/1944) K6).

```bash
python3 tools/agent-handover/fragments.py neu --session-id <id> --titel "<Titel>" [--ziel "<Ziel>"]
python3 tools/agent-handover/fragments.py render        # aktueller Stand
python3 tools/agent-handover/fragments.py pruefen       # Lint + Unveränderlichkeit
```

Regeln (Mini-Spec v1, Volltext im Modulkopf von `fragments.py`):

- Dateiname `<UTC-Zeitstempel>-<session-id>.md`, Abschnitte `## Erledigt`, `## Offen`, `## Log`.
- Jeder Offen-Punkt trägt genau eine Issue- oder PR-URL.
- Ein Fragment auf `main` wird nie mehr geändert; eine Korrektur ist ein neues Fragment.
- Aktiv ist ein Fragment, solange es jünger als 7 Tage ist oder ein offenes Issue nennt.
