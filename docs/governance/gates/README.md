# Gate-Registry — ein Eintrag je Datei

Seit 2026-09-16 ([#1944](https://github.com/achimdehnert/platform/issues/1944) K7) ist die
frühere Sammeldatei `docs/governance/gate-registry.json` aufgeteilt. Parallele Sitzungen
kollidieren damit nur noch, wenn sie **denselben** Eintrag ändern; vorher war die Datei mit
20 Kollisionspaaren in 14 Tagen die meistgeteilte des Repos.

| Pfad | Inhalt |
|---|---|
| `_meta.json` | die Doku-Schlüssel (`_doc`, `_faengt_doc`, …) |
| `gates/<slug>.json` | ein gebautes Gate |
| `declined/<slug>.json` | eine bewusste Nicht-Gate-Entscheidung |
| `widerrufen/<slug>.json` | eine zurückgenommene Nicht-Gate-Entscheidung |
| `kandidaten/<slug>.json` | ein Gate-Kandidat |

Gelesen wird die Registry **nur** über `tools/gate_registry.py`, das daraus das frühere
Format zusammensetzt:

```bash
python3 tools/gate_registry.py                    # zusammengesetztes JSON
python3 tools/gate_registry.py --ref origin/main  # Stand auf einem Git-Ref
```

Einen neuen Eintrag legst du als neue Datei an; der Dateiname ist der `slug`.
Einträge werden alphabetisch nach Slug geladen, die Reihenfolge trägt keine Bedeutung.
