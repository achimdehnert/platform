# 📦 ADR Archive

Archivierte Architecture Decision Records – superseded, deprecated, oder rejected.

## Struktur

```
_archive/
├── core/           # Archivierte Core ADRs
├── bfagent/        # Archivierte BF Agent ADRs
├── travel-beat/    # Archivierte Travel-Beat ADRs
├── mcp-hub/        # Archivierte MCP Hub ADRs
├── risk-hub/       # Archivierte Risk Hub ADRs
├── cad-hub/        # Archivierte CAD Hub ADRs
├── pptx-hub/       # Archivierte PPTX Hub ADRs
└── shared/         # Archivierte Shared ADRs
```

## Archivierungs-Policy

Ein ADR wird archiviert wenn:

| Status | Trigger | Aktion |
|--------|---------|--------|
| **Superseded** | Neues ADR ersetzt altes | → `_archive/{scope}/` |
| **Deprecated** | Nicht mehr relevant | → `_archive/{scope}/` |
| **Rejected** | Während Review abgelehnt | → `_archive/{scope}/` |

## Wie wird archiviert?

```bash
# 1. Status im ADR aktualisieren
#    Status: Accepted → Status: Superseded by ADR-XXX

# 2. Verschieben
mv docs/adr/core/ADR-003-old-decision.md docs/adr/_archive/core/

# 3. Index regenerieren
python3 scripts/generate-adr-index.py

# 4. Commit
git add docs/adr/
git commit -m "docs(adr): Archive ADR-003 (superseded by ADR-015)"
```

## Wiederherstellen

Falls ein ADR doch noch relevant ist:

```bash
# 1. Zurück verschieben
mv docs/adr/_archive/core/ADR-003-xxx.md docs/adr/core/

# 2. Status aktualisieren
#    Status: Superseded → Status: Accepted

# 3. Index regenerieren
python3 scripts/generate-adr-index.py
```

---

*Archivierte ADRs werden im Master-Index unter "Archived" gelistet.*
