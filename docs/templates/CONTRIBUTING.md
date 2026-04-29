# Mitwirken / Contributing

## Branch-Konvention

```
main          ← Produktionsstand
feat/<thema>  ← Neue Features
fix/<thema>   ← Bugfixes
docs/<thema>  ← Nur Dokumentation
```

## Commit-Format

```
[TAG] modul: kurze Beschreibung

feat    — Neue Funktionalität
fix     — Bugfix
refactor — Refactoring ohne API-Änderung
docs    — Nur Dokumentation
test    — Tests
chore   — Tooling, CI, Dependencies
```

Beispiel: `feat(substances): SDS-Upload-Pipeline mit OCR-Fallback`

## Pull Request

1. Branch vom aktuellen `main` anlegen
2. Änderungen committen (Konvention oben)
3. PR öffnen — Beschreibung mit: **Was / Warum / Wie testen**
4. Mind. 1 Review erforderlich

## Code-Qualität

```bash
ruff check . && ruff format --check .
python -m pytest tests/ -v
```

Beide müssen grün sein vor Merge.

## Für Dokumentations-Repos

- Markdown-Quellen in `docs/<bereich>/kapitel/`
- Kein HTML direkt in Markdown — `arch`/`flow`/`tree` Code-Fences nutzen
- PDF neu erzeugen vor Commit: `/create-pdf`

## Fragen?

→ [Issue anlegen](../../issues/new/choose)
