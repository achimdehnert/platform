---
status: "accepted"
date: 2026-02-22
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related: ["ADR-051-concept-to-adr-pipeline.md"]
implementation_status: implemented
---

# Adopt filesystem-first ADR numbering — max(existing) + 1

---

## Context and Problem Statement

ADR-Nummern wurden wiederholt falsch vergeben: AI-Agenten (Cascade) nutzten Nummern
aus dem Gedächtnis statt das Filesystem zu prüfen. Das führte zu konkreten Problemen:

- **Kollisionen**: Dieselbe Nummer wurde in verschiedenen Sessions vergeben
- **Lücken**: Nummern wurden übersprungen (059, 060, 061, 063 fehlen)
- **Phantom-ADRs**: ADR-062 wurde in einer Session "erstellt" aber nie committed,
  in der nächsten Session erneut vergeben — ohne Kollisionserkennung
- **Veralteter INDEX.md**: ADR-056 bis ADR-064 fehlten komplett

Das ursprüngliche Nummernbereichskonzept (platform: 001–049, bfagent: 050–099 etc.)
wurde nie konsequent eingehalten und ist seit ADR-050 de facto aufgegeben.

**Problem**: Keine zuverlässige, werkzeuggestützte Methode zur Nummernvergabe.
Jede Methode, die auf Gedächtnis oder Konvention basiert, ist fehleranfällig.

---

## Decision Drivers

- **Kollisionsfreiheit**: Jede Nummer darf nur einmal vergeben werden
- **Werkzeugunterstützung**: Methode muss von AI-Agenten zuverlässig und ohne
  Kontextwissen ausführbar sein
- **Einfachheit**: Eine einzige Regel, kein Interpretationsspielraum
- **Rückwärtskompatibilität**: Bestehende Nummern bleiben unverändert
- **Sofortige Anwendbarkeit**: Keine neue Infrastruktur erforderlich

---

## Considered Options

### Option 1 — Filesystem-First: max(existing) + 1 (gewählt)

Vor jeder ADR-Erstellung wird das Verzeichnis `docs/adr/` gescannt. Die höchste
vorhandene Nummer wird ermittelt, inkrementiert und auf Kollision geprüft.

**Pro:**
- Deterministisch: Ergebnis hängt nur vom Filesystem-Zustand ab, nicht vom Gedächtnis
- Werkzeuggestützt: `find_by_name` ist ein verfügbares Tool für AI-Agenten
- Keine neue Infrastruktur nötig
- Sofort anwendbar

**Contra:**
- Erfordert Regex-Parsing der Dateinamen
- Bei gleichzeitiger Erstellung durch zwei Agenten (unwahrscheinlich) möglich Kollision

---

### Option 2 — Bereichskonzept beibehalten (platform: 001–049 etc.)

**Pro:** Nummern sind nach Repo/Scope gruppiert und lesbar

**Contra:**
- Wurde nie konsequent eingehalten — historisch gescheitert
- Erfordert Kontextwissen über Bereichsgrenzen
- Führt zu Lücken wenn ein Bereich voll ist

**Verworfen**: Historisch gescheitert; Konvention ohne Enforcement ist keine Lösung.

---

### Option 3 — Zentrales Lock-File (`NEXT_ADR_NUMBER`)

Eine Datei enthält die nächste freie Nummer, wird atomar inkrementiert.

**Pro:** Atomar, kein Regex-Parsing, explizit

**Contra:**
- Zusätzliche Datei muss bei jedem Commit aktualisiert werden
- Merge-Konflikte wenn zwei Branches gleichzeitig ADRs erstellen
- Erfordert disziplinierte Pflege — ähnliches Risiko wie Gedächtnis-basiert

**Verworfen**: Merge-Konflikt-Risiko überwiegt den Vorteil der Atomarität.

---

### Option 4 — GitHub API: letzte Datei im Verzeichnis abfragen

**Pro:** Immer aktuell, kein lokales Filesystem nötig

**Contra:**
- API-Aufruf erfordert Authentifizierung und Netzwerkzugang
- Latenz und Fehleranfälligkeit bei API-Ausfall
- Komplexer als Filesystem-Scan

**Verworfen**: Unnötige Abhängigkeit; Filesystem-Scan ist ausreichend zuverlässig.

---

## Decision Outcome

**Gewählt: Option 1** — Filesystem-Scan als einzige Wahrheitsquelle.

### Verbindliche Regel

> **Vor jeder ADR-Erstellung**: `find_by_name` auf `docs/adr/` mit Pattern `ADR-*.md`
> und `MaxDepth 1` ausführen. Nächste Nummer = `max(alle gefundenen Nummern) + 1`.
> Danach Kollisionsprüfung: existiert `ADR-NNN-*.md` bereits? Falls ja → +1 wiederholen.

### Nummernbereichskonzept

Das ursprüngliche Bereichskonzept (platform: 001–049, bfagent: 050–099 etc.) wird
**nicht mehr durchgesetzt**. Neue ADRs erhalten die nächste freie Globalnummer.
Historische Nummern bleiben unverändert. INDEX.md ist die einzige Übersicht.

### Positive Consequences

- Keine Kollisionen möglich, solange die Regel eingehalten wird
- Einfach und werkzeuggestützt — kein Kontextwissen nötig
- Sofort anwendbar ohne Infrastruktur-Änderungen

### Negative Consequences

- Nummern sind nicht mehr nach Repo/Scope gruppiert
- Bestehende Lücken (059–061, 063) bleiben bestehen — werden nicht aufgefüllt
- Erfordert Regex-Parsing der Dateinamen (geringes Fehlerrisiko)

---

## Implementation Details

### Pflicht-Ablauf bei ADR-Erstellung (in `/adr` Workflow)

```python
# Pseudocode — implementiert via find_by_name Tool
files = find_by_name("docs/adr/", pattern="ADR-*.md", max_depth=1)
numbers = [int(re.search(r"ADR-(\d+)-", f).group(1)) for f in files]
next_num = max(numbers) + 1

# Kollisionsprüfung
while exists(f"docs/adr/ADR-{next_num:03d}-*.md"):
    next_num += 1

create(f"docs/adr/ADR-{next_num:03d}-{slug}.md")
update_index("docs/adr/INDEX.md", next_num)  # sofort im selben Commit
```

### INDEX.md als Single Source of Truth

- INDEX.md wird **sofort** nach ADR-Erstellung aktualisiert
- Enthält alle ADRs mit Status, Repo, Dateilink
- "Letzte Aktualisierung"-Datum wird bei jeder Änderung aktualisiert
- INDEX.md und ADR-Datei werden **im selben Commit** eingecheckt

### Bekannte Lücken (werden nicht aufgefüllt)

| Lücke | Grund |
|-------|-------|
| ADR-011 | Nie erstellt (historisch) |
| ADR-025, ADR-026 | Nie erstellt (historisch) |
| ADR-059, ADR-060, ADR-061 | Durch Nummernfehler übersprungen |
| ADR-063 | Durch Nummernfehler übersprungen |

---

## Migration Tracking

| Schritt | Status | Datum |
|---------|--------|-------|
| Workflow `adr.md` aktualisiert (Filesystem-First Regel) | ✅ done | 2026-02-22 |
| INDEX.md auf aktuellen Stand gebracht (ADR-056–065) | ✅ done | 2026-02-22 |
| ADR-065 erstellt und in INDEX.md eingetragen | ✅ done | 2026-02-22 |
| CI-Check für INDEX.md-Aktualität | ⬜ pending | — |

---

## Consequences

### Risks

| Risiko | Schwere | Mitigation |
|--------|---------|-----------|
| Scan-Schritt wird übersprungen | MEDIUM | Workflow-Regel explizit als KRITISCH markiert; CI-Check geplant |
| Parallele ADR-Erstellung (zwei Agenten gleichzeitig) | LOW | Kollisionsprüfung nach Scan; Single-Developer-Setup macht dies unwahrscheinlich |
| Regex-Parsing-Fehler bei unerwarteten Dateinamen | LOW | Pattern `ADR-(\d+)-` ist robust; Dateien ohne Nummer werden ignoriert |

### Confirmation

- Jede neue ADR-Datei hat eine Nummer größer als alle bestehenden
- INDEX.md enthält den Eintrag innerhalb desselben Commits wie die ADR-Datei
- `/adr` Workflow enthält expliziten Filesystem-Scan-Schritt als KRITISCH markiert

---

## Drift-Detector Governance Note

```yaml
paths:
  - docs/adr/INDEX.md
  - .windsurf/workflows/adr.md
gate: NOTIFY
```
