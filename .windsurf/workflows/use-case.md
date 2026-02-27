---
description: Use Case definieren, dokumentieren und als GitHub Issue tracken (RUP/UML-Standard)
---

# Use Case Workflow

**Trigger:** User sagt eines von:
- "Erstelle Use Case für: [Beschreibung]"
- "UC für [Feature] definieren"
- "/use-case [Name]"

---

## Step 0: Ist das wirklich ein Use Case?

Ein Use Case **muss** folgende Kriterien erfüllen:

| Kriterium | Frage |
|-----------|-------|
| **Akteur vorhanden** | Gibt es einen menschlichen oder System-Akteur? |
| **Ziel vorhanden** | Was will der Akteur erreichen? |
| **Interaktion vorhanden** | Gibt es eine Sequenz von Schritten? |
| **Wert vorhanden** | Hat der Akteur nach dem UC einen Mehrwert? |

**Kein Use Case** (→ Alternativen):
- Reine technische Aufgabe ohne Akteur → `task.yml` Issue
- Infrastruktur-Change → ADR + `task.yml`
- Bug-Fix → `bug_report.yml` Issue

---

## Step 1: Use Case ID vergeben

Lese `docs/use-cases/README.md` — nächste freie Nummer wählen.

```
Format: UC-{NNN}
Beispiel: UC-007
```

---

## Step 2: Use Case Steckbrief aufnehmen

Agent fragt folgende Mindest-Infos ab (interaktiv):

```
Use Case ID: UC-XXX
Name: [kurzer, aktiver Titel — z.B. "Buch zur Leseliste hinzufügen"]
Level: summary | user-goal | subfunction
Primärer Akteur: [z.B. "Registrierter Leser"]
Trigger: [Was löst den UC aus?]
Scope: [Welche App/Domain]
```

---

## Step 3: Dokumentationsdatei anlegen

Erstelle `docs/use-cases/UC-{NNN}-{kebab-case-name}.md` nach diesem Template:

```markdown
# UC-XXX: [Name]

**ID:** UC-XXX | **Status:** draft | **Version:** 1.0
**Datum:** YYYY-MM-DD | **Autor:** @username

---

## Steckbrief

| Attribut | Wert |
|---|---|
| Level | user-goal |
| Primärer Akteur | [Akteur] |
| Scope | [App / Domain] |
| Trigger | [Was löst UC aus] |
| Häufigkeit | täglich / gelegentlich / einmalig |

---

## Stakeholder & Interessen

| Stakeholder | Interesse |
|---|---|
| [Akteur 1] | [Was will er/sie] |

---

## Vorbedingungen

- [Vorbedingung 1]

---

## Hauptszenario (Happy Path)

| Schritt | Akteur | Aktion |
|---|---|---|
| 1 | Nutzer | … |
| 2 | System | … |

---

## Alternative Szenarien

### A — [Bezeichnung]
> Einstieg bei Schritt X

| Schritt | Akteur | Aktion |
|---|---|---|
| Xa | System | … |

---

## Ausnahme-Szenarien

### E1 — [Fehlerfall]

| Schritt | Akteur | Aktion |
|---|---|---|
| E1a | System | Fehlermeldung anzeigen |

---

## Nachbedingungen (Erfolgsfall)

- [Was hat sich geändert nach erfolgreichem UC]

---

## Business Rules

| ID | Regel |
|---|---|
| BR-01 | |

---

## Implementierungs-Hinweise

```
apps.[X].views.[View] → apps.[X].services.[Service] → apps.[X].models.[Model]
URL: /[prefix]/[action]/
Template: templates/[X]/[model]_[action].html
```

---

## Verknüpfungen

| Typ | Referenz |
|---|---|
| GitHub Issue | #XX |
| ADR | ADR-XXX |
| Übergeordneter UC | UC-XXX |

---

## Änderungshistorie

| Version | Datum | Autor | Änderung |
|---|---|---|---|
| 1.0 | YYYY-MM-DD | @X | Erstellt |
```

---

## Step 4: docs/use-cases/README.md Index aktualisieren

Füge Zeile im Index-Table ein:

```markdown
| [UC-XXX](UC-XXX-name.md) | [Name] | [App] | [Akteur] | draft |
```

---

## Step 5: GitHub Issue anlegen

Erstelle GitHub Issue mit dem `use_case.yml`-Template:
- Title: `[UC] UC-XXX: [Name]`
- Labels: `use-case`, `triage`
- Body: Steckbrief aus Step 2 + Link zur Doku-Datei

```
Verknüpfung in Doku-Datei nachtragen: GitHub Issue #XX
```

---

## Step 6: Status-Übergänge

```
draft     → Erstellt, noch nicht vollständig
review    → Vollständig, wartet auf Abnahme
accepted  → Abgenommen, bereit für Implementierung
deprecated → Überholt (Grund dokumentieren)
```

Use Case wird auf `accepted` gesetzt wenn:
- [ ] Haupt- + Alternativszenario vollständig
- [ ] Business Rules explizit
- [ ] Implementierungs-Hinweise vorhanden
- [ ] GitHub Issue angelegt und verlinkt
- [ ] Stakeholder haben zugestimmt

---

## Step 7: Implementierungs-Verknüpfung

Wenn der UC implementiert wird:
- GitHub Issue mit `[FEATURE]`-Issue verknüpfen
- In `docs/AGENT_HANDOVER.md` referenzieren
- Nach Implementierung: UC-Status auf `accepted` + GitHub Issue schließen

---

## Referenz: UC-Levels

| Level | Wann | Beispiel |
|-------|------|---------|
| `summary` | Übergeordnetes Ziel / Epic | "User verwaltet seine Bibliothek" |
| `user-goal` | Konkretes Nutzerziel (Standard) | "Buch zur Leseliste hinzufügen" |
| `subfunction` | Hilfsfunktion für anderen UC | "Auth-Status prüfen" |
