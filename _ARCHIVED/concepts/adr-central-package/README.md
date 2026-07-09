# 📋 Centralized ADR Management Package

Komplettes Paket für **zentralisiertes ADR-Management** über alle Repositories der BF Agent Platform.

---

## 🎯 Konzept

**Alle ADRs an einem Ort** – im `platform` Repository, strukturiert nach Scope:

```
platform/docs/adr/
├── core/           # Platform-Infrastruktur (001-019)
├── bfagent/        # BF Agent App (020-029)
├── travel-beat/    # Travel-Beat App (030-039)
├── mcp-hub/        # MCP Hub (040-049)
├── risk-hub/       # Risk Hub (050-059)
├── cad-hub/        # CAD Hub (060-069)
├── pptx-hub/       # PPTX Hub (070-079)
├── shared/         # Cross-App (080-099)
├── drafts/         # Work in Progress
└── _archive/       # Superseded/Deprecated
```

---

## 📦 Paket-Inhalt

```
adr-central-package/
├── docs/adr/
│   ├── core/
│   │   └── ADR-011-centralized-adr-management.md  # Das Policy ADR
│   ├── TEMPLATE.md                                 # ADR Template
│   └── TRIAGE.md                                   # Scope-Entscheidungshilfe
├── scripts/
│   ├── generate-adr-index.py                       # Index Generator
│   └── setup-adr-structure.sh                      # Setup Script
├── .github/workflows/
│   └── adr-index.yml                               # CI/CD Integration
└── README.md                                       # Diese Datei
```

---

## 🚀 Installation

### Schritt 1: Paket entpacken & kopieren

```bash
# Entpacken
unzip adr-central-package.zip

# In Platform-Repo kopieren
cp -r adr-central-package/docs/adr/* /path/to/platform/docs/adr/
cp -r adr-central-package/scripts/* /path/to/platform/scripts/
cp -r adr-central-package/.github/workflows/* /path/to/platform/.github/workflows/

# Scripts ausführbar machen
chmod +x /path/to/platform/scripts/*.sh
```

### Schritt 2: Struktur aufsetzen

```bash
cd /path/to/platform

# Ordnerstruktur erstellen
./scripts/setup-adr-structure.sh

# Index generieren
python3 scripts/generate-adr-index.py
```

### Schritt 3: Bestehende ADRs migrieren

```bash
# Bestehende ADRs in platform nach core/ verschieben
mv docs/adr/ADR-*.md docs/adr/core/

# Oder aus anderem Repo:
# 1. ADR kopieren
# 2. Nummer anpassen (siehe Nummernkreise)
# 3. In richtigen Scope verschieben
```

### Schritt 4: Commit

```bash
git add docs/adr scripts/.github/workflows/
git commit -m "feat: Centralized ADR management (ADR-011)"
git push
```

---

## 📊 Nummernkreise

| Scope | Bereich | Beschreibung |
|-------|---------|--------------|
| **core** | 001-019 | Platform-Infrastruktur |
| **bfagent** | 020-029 | BF Agent App |
| **travel-beat** | 030-039 | Travel-Beat App |
| **mcp-hub** | 040-049 | MCP Hub |
| **risk-hub** | 050-059 | Risk Hub |
| **cad-hub** | 060-069 | CAD Hub |
| **pptx-hub** | 070-079 | PPTX Hub |
| **shared** | 080-099 | Cross-App |
| **reserve** | 100-199 | Für Erweiterungen |

---

## 🔄 Workflow: Neues ADR erstellen

```bash
# 1. Draft erstellen
cp docs/adr/TEMPLATE.md docs/adr/drafts/ADR-DRAFT-my-feature.md

# 2. Template ausfüllen
# - Context, Decision, Consequences

# 3. Scope bestimmen (siehe TRIAGE.md)
# Frage: Welche App(s) betroffen?

# 4. Nächste Nummer holen
python3 scripts/generate-adr-index.py --next bfagent
# Output: Next number for 'bfagent': 020

# 5. Verschieben und umbenennen
mv docs/adr/drafts/ADR-DRAFT-my-feature.md \
   docs/adr/bfagent/ADR-020-my-feature.md

# 6. Nummer im Dokument aktualisieren
# ADR-DRAFT → ADR-020

# 7. PR erstellen
git checkout -b adr/020-my-feature
git add docs/adr/
git commit -m "docs(adr): Add ADR-020 my-feature"
git push -u origin adr/020-my-feature
# → PR erstellen
```

---

## 🎯 Triage: Welcher Scope?

```
Neues ADR
    │
    ▼
┌───────────────────────┐
│ Betrifft Infrastruktur│───Ja───→ core/
│ (CI/CD, DB, Deploy)?  │
└───────────┬───────────┘
            │ Nein
            ▼
┌───────────────────────┐
│ Betrifft ≥2 Apps?     │───Ja───→ shared/
└───────────┬───────────┘
            │ Nein
            ▼
      Welche App?
      │
      ├─→ BF Agent     → bfagent/
      ├─→ Travel-Beat  → travel-beat/
      ├─→ MCP-Hub      → mcp-hub/
      └─→ ...
```

---

## 🤖 CI/CD Integration

Die GitHub Action:

1. **Prüft** ob Index aktuell ist
2. **Validiert** Ordnerstruktur
3. **Prüft** Nummern-Eindeutigkeit
4. **Prüft** Scope-Grenzen
5. **Generiert** Index automatisch (auf main)

---

## ✅ Vorteile

| Vorteil | Beschreibung |
|---------|--------------|
| **Single Source of Truth** | Alle ADRs an einem Ort |
| **Eindeutige Nummern** | ADR-042 ist global eindeutig |
| **Einfache Suche** | `grep -r "auth" docs/adr/` |
| **Automatischer Index** | Filterbar, immer aktuell |
| **Cross-Referenzen** | Einfach zwischen Apps verlinken |

---

## 🔧 Nützliche Befehle

```bash
# Index generieren
python3 scripts/generate-adr-index.py

# Index prüfen (CI-Mode)
python3 scripts/generate-adr-index.py --check

# Nächste Nummer für Scope
python3 scripts/generate-adr-index.py --next core
python3 scripts/generate-adr-index.py --next bfagent

# Struktur aufsetzen
./scripts/setup-adr-structure.sh
```

---

## 📚 Referenzen

- [ADR-011: Centralized ADR Management](docs/adr/core/ADR-011-centralized-adr-management.md)
- [ADR Template](docs/adr/TEMPLATE.md)
- [Triage Guide](docs/adr/TRIAGE.md)
- [ADR GitHub Organization](https://adr.github.io/)
