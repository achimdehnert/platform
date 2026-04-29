# PDF-Dokumentation — <Repo-Name>

Alle PDFs werden aus Markdown-Quellen via `/create-pdf` generiert (Design: `<DESIGN_KEY>`).
Quellen in `docs/` — PDFs sind Read-Only-Deliverables, nicht manuell bearbeiten.

→ **Aktueller Status aller Dokumente:** [STATUS.md](STATUS.md)

---

## Aktuelle Dokumente

| Dokument | Zielgruppe | Version | Status |
|---|---|---|---|
| [<name>_v1.0.pdf](<subdir>/<name>_v1.0.pdf) | <Zielgruppe> | v1.0 | ✅ |
| [<name>_v0.1.pdf](<subdir>/<name>_v0.1.pdf) | <Zielgruppe> | v0.1 | 🚧 |

---

## Erzeugen / Aktualisieren

```bash
# In Windsurf:
/create-pdf
```

Nach Erzeugung → `STATUS.md` aktualisieren (Version + Status anpassen).

---

## Namenskonvention

```
[subdir/]<kebab-case-titel>_vX.Y.pdf
```

| Phase | Dateiname | Status |
|---|---|---|
| Erster Entwurf | `<titel>_v0.1.pdf` | 🚧 |
| Review-Ready | `<titel>_v0.9.pdf` | 🔄 |
| Freigegeben | `<titel>_v1.0.pdf` | ✅ |
| Update | `<titel>_v1.1.pdf` | 🔄 |

---

## Verzeichnisstruktur (Tier 1 — Django App)

```
docs/pdf/
├── STATUS.md          ← Freigabe-Status (immer aktuell halten!)
├── README.md          ← Diese Datei
├── user/              ← Endnutzer / Sachbearbeiter
├── technical/         ← IT-Admins / Entwickler
└── management/        ← Entscheider / Product Owner
```
