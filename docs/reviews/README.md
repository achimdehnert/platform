# Reviews — IIL Platform

Strukturierte Code- und ADR-Reviews, versioniert und referenzierbar.

## Konvention

| Feld | Format | Beispiel |
|------|--------|----------|
| **Dateiname** | `<Typ>-<ID>-review-<YYYY-MM-DD>.md` | `ADR-118-review-2026-03-11.md` |
| **Typ** | `ADR`, `PR`, `CODE` | — |
| **ID** | ADR-Nummer, `<repo>-<PR#>`, oder frei | `ADR-118`, `risk-hub-42` |
| **Datum** | ISO-8601 | `2026-03-11` |

## Review-Format

Jeder Review folgt dem Platform-Reviewer-Format (`platform/concepts/REVIEWER_PROMPT.md`):

```
[BLOCK]    — Muss vor Akzeptanz gefixt werden
[SUGGEST]  — Empfehlung, nicht zwingend
[QUESTION] — Klärungsbedarf
[NITS]     — Kleinigkeit

Gesamturteil:
✅ APPROVED | ⚠️ APPROVED WITH COMMENTS | ❌ CHANGES REQUESTED
```

## GitHub-Integration

- Reviews mit **BLOCK-Items** → GitHub Issue mit Label `review` im betroffenen Repo
- Issue verlinkt auf die Review-Datei
- Issue wird geschlossen wenn alle BLOCKs resolved sind

## Ablauf

1. Review durchführen (Cascade, manuell, oder `/pr-review` Workflow)
2. Review als Datei hier speichern
3. Bei BLOCKs: GitHub Issue erstellen
4. Fixes implementieren → Issue schließen
5. Optional: Follow-Up-Review als neue Datei

## Index

| Datei | Gegenstand | Urteil | Issue |
|-------|-----------|--------|-------|
| [ADR-118-review-2026-03-11.md](ADR-118-review-2026-03-11.md) | billing-hub als Platform Store | ❌ CHANGES REQUESTED | [platform#23](https://github.com/achimdehnert/platform/issues/23) |
