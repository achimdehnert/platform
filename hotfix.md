---
description: Schneller Produktions-Fix — ohne vollen agentic-coding Flow, mit Safety Gates
---

# Hotfix Workflow

**Trigger:** User sagt eines von:
- "Hotfix für [Problem]"
- "Kritischer Bug in Produktion: [Beschreibung]"
- "Notfall-Fix auf main"

> **Unterschied zu `/agentic-coding`**: Hotfix überspringt Planning/Routing-Overhead,
> arbeitet direkt auf `hotfix/XXX`-Branch, deployt nach Review sofort.
> Nur für **Produktionsfehler mit unmittelbarer Auswirkung**.

---

## Gate 0: Ist das wirklich ein Hotfix?

| Kriterium | Hotfix ✅ | Normaler Flow ❌ |
|-----------|-----------|----------------|
| Produktionsausfall / critical bug | ✅ | — |
| Datenverlust oder Security-Lücke | ✅ | — |
| Kernfunktion komplett kaputt | ✅ | — |
| "Nice to have" Fix | — | → feature branch |
| Refactoring | — | → /agentic-coding |
| Neues Feature als Fix verkleidet | — | → feature branch |

**Bei Unsicherheit: normalen Flow nehmen. Hotfix = Ausnahme, nicht Regel.**

---

## Step 1: Kontext laden (2 Minuten — nicht überspringen)

```
1. docs/CORE_CONTEXT.md lesen (Architektur-Constraints)
2. docs/AGENT_HANDOVER.md lesen (was läuft gerade noch?)
```

Prüfe: Gibt es offene PRs oder WIP-Branches die Konflikt verursachen könnten?

---

## Step 2: Root Cause analysieren (BEVOR Code angefasst wird)

```
Bug-Report ausfüllen (mental oder als GitHub Issue):
- Was genau ist kaputt? (Symptom vs. Root Cause trennen!)
- Seit wann? (welcher Commit hat es eingeführt?)
- Betroffene App(s): apps.[X]
- Betroffene Dateien (maximal 1-3 Dateien für echten Hotfix)
```

// turbo
```bash
git log --oneline -10
```

Zeigt die letzten Commits — verdächtigen Commit identifizieren.

---

## Step 3: Hotfix-Branch erstellen

// turbo
```bash
git checkout main && git pull origin main
git checkout -b hotfix/$(date +%Y%m%d)-BESCHREIBUNG
```

Beispiel: `hotfix/20260226-books-500-error`

---

## Step 4: Minimalen Fix implementieren

**Regeln für Hotfix-Code:**
- ❌ Kein Refactoring während des Fixes
- ❌ Keine neuen Features
- ❌ Kein Umbau von Strukturen "weil man grade dabei ist"
- ✅ Kleinste mögliche Änderung die das Problem löst
- ✅ Service Layer beachten (auch im Hotfix: views → services → models)
- ✅ Keine Secrets im Code

---

## Step 5: Regression Test schreiben (Pflicht)

```python
# tests/test_[app].py
def test_should_not_[bug_beschreibung](client):
    """Regression: #XXX — [Bug-Beschreibung]"""
    # Arrange
    ...
    # Act
    response = client.get("/[url]/")
    # Assert
    assert response.status_code == 200  # war: 500
```

// turbo
```bash
pytest tests/ -q -k "test_should_not_"
```

---

## Step 6: Full Test Suite (kein Überspringen)

// turbo
```bash
pytest tests/ -q
```

**Alle Tests müssen grün sein.** Bei rot: Fix den neuen Fehler, dann weiter.

---

## Step 7: Commit + PR

```bash
git add -p  # Nur relevante Änderungen stagen (kein git add .)
git commit -m "fix([scope]): [kurze Beschreibung]

Fixes #[issue-number] — [was war kaputt, was wurde geändert]
Regression test: test_should_not_[beschreibung]"
```

PR erstellen:
- Title: `[HOTFIX] [Beschreibung]`
- Labels: `bug`, `hotfix` (falls vorhanden)
- Body: Root Cause + Fix + Regression Test
- **Squash & Merge** (saubere main-Historie)

---

## Step 8: Deploy

Nach PR-Merge sofort deployen via `/deploy`:

```
service: [app-name]
image_tag: latest
has_migrations: [true/false]
```

Health-Check verifizieren:
```bash
curl -sf https://[domain]/livez/ && echo "OK"
```

---

## Step 9: Post-Mortem (bei critical/high Schweregrad)

Nach dem Fix:
1. GitHub Issue mit `[BUG]`-Template anlegen (falls noch nicht vorhanden)
2. Root Cause + Fix in Issue dokumentieren
3. `docs/AGENT_HANDOVER.md` aktualisieren
4. Überlegen: Braucht es ein ADR um das Pattern zu verhindern?

---

## Hotfix Checkliste

```
[ ] Root Cause identifiziert (nicht nur Symptom behandelt)
[ ] Hotfix-Branch erstellt (hotfix/YYYYMMDD-beschreibung)
[ ] Minimaler Fix — kein Refactoring
[ ] Regression Test vorhanden (test_should_not_*)
[ ] Alle Tests grün
[ ] PR erstellt + reviewed
[ ] Deployed + Health-Check grün
[ ] GitHub Issue dokumentiert
[ ] AGENT_HANDOVER.md aktualisiert
```
