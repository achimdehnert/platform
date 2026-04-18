---
description: Task abschließen — Pflicht-Gate vor "COMPLETE". Alle Aufgaben erledigt, getestet, Fehler behoben, Protokoll erstellt.
---

# /complete — Task Completion Gate

**Wann:** Bevor du "COMPLETE" sagst. Immer. Ohne Ausnahme.

**Regel:** Du darfst "COMPLETE" erst schreiben, wenn ALLE 6 Schritte grün sind.

---

## Step 1: Todo-Liste prüfen

Prüfe die aktuelle Todo-Liste. Jeder Eintrag muss `completed` sein.

```
Falls offene Items → STOPP. Erst fertig machen oder mit User klären.
```

## Step 2: Banned Patterns Scan

Grep über **alle editierten Dateien** nach verbotenen Patterns:

```bash
# In Django-Templates:
grep -rn "onclick=" <editierte_templates>
grep -rn "bg-dark text-light border-secondary" <editierte_templates>

# In Python:
grep -rn "print(" <editierte_python_files>   # → sollte logging sein
grep -rn "except:" <editierte_python_files>   # → braucht Exception-Typ
grep -rn "os.environ" <editierte_python_files> # → sollte decouple sein
```

```
Falls Treffer in DEINEN Änderungen → STOPP. Erst fixen.
Falls Treffer in Code außerhalb deines Scopes → dokumentieren als "known issues".
```

## Step 3: Template/Code Validation

// turbo
```bash
# Django Templates:
DJANGO_SETTINGS_MODULE=config.settings.development python3 -c "
import django; django.setup()
from django.template.loader import get_template
for t in [<LISTE_ALLER_GEÄNDERTEN_TEMPLATES>]:
    try:
        get_template(t); print(f'✅ {t}')
    except Exception as e:
        print(f'❌ {t}: {e}')
"

# Python:
python3 -m py_compile <editierte_python_files>
```

```
Falls ❌ → STOPP. Erst fixen.
```

## Step 4: Playwright Visual + Functional Test

Für **jede betroffene Seite**:

1. **HTTP 200 Test** — Navigiere zu jeder URL, prüfe Status
2. **JS Console Errors** — Prüfe `browser_console_messages(level='error')` → muss 0 sein
3. **Link-Test** — Auf der Hauptseite alle `<a href>` per `fetch()` prüfen
4. **Screenshot** — Vollbild-Screenshot als Beweis

```javascript
// Automatisierter Multi-Page-Test:
const pages = [/* alle betroffenen URLs */];
for (const p of pages) {
  const resp = await page.goto(url);
  // Prüfe resp.status() === 200
}
```

```
Falls HTTP != 200 oder JS-Errors > 0 → STOPP. Erst fixen, dann nochmal testen.
```

## Step 5: Mobile-Test (falls UI-Änderungen)

```javascript
await page.setViewportSize({ width: 375, height: 812 });
// Screenshot + Hamburger-Test + Layout-Check
```

```
Falls Layout broken → STOPP. Erst fixen.
```

## Step 6: Audit-Report erstellen

Erstelle `docs/<TASK>_REPORT.md` mit:

```markdown
# <Task-Name> — Audit Report

**Datum:** YYYY-MM-DD
**Branch:** `<branch>` (HEAD: <sha>)
**Scope:** <Anzahl> Dateien, <Anzahl> Seiten

## Geänderte Dateien
| Datei | Änderungen | Typ |

## Fixes
| # | Fix | Status |

## Test-Ergebnisse
### HTTP-Status (Playwright)
| Seite | URL | Status |

### JS-Console-Errors
| Level | Count |

### Link-Test
| Kategorie | Count | Status |

### Banned Patterns
| Pattern | Treffer |

### Mobile (falls getestet)
| Test | Status |

## Bekannte verbleibende Issues (außerhalb Scope)
| Datei | Issue | Priorität |

## Fazit
COMPLETE ✅ / INCOMPLETE ❌
```

---

## Output-Format

Wenn alle 6 Steps grün sind, schreibe:

```
# COMPLETE ✅

## Beweislage
| Prüfung | Ergebnis |
|---------|----------|
| Seiten HTTP 200 | ✅ X/X |
| JS-Console-Errors | ✅ 0 |
| Links getestet | ✅ X/X OK |
| Templates/Code parsen | ✅ X/X |
| Banned Patterns | ✅ 0 in Scope |
| Mobile (falls UI) | ✅ / n/a |
| Audit-Report | ✅ docs/<name>.md |

Protokoll: docs/<name>_REPORT.md
```

Falls NICHT alle grün:

```
# INCOMPLETE ❌

## Blocker
- [ ] <was fehlt>
```

---

## Varianten nach Task-Typ

| Task-Typ | Steps anwenden |
|----------|---------------|
| **UI/Template** | Alle 6 Steps |
| **Backend/Python** | Steps 1-3 + pytest statt Playwright |
| **Infrastructure** | Steps 1-2 + health_check statt Playwright |
| **Docs only** | Steps 1 + 6 |

Für **Backend-Tasks** ersetze Step 4 mit:
```bash
# pytest statt Playwright:
DJANGO_SETTINGS_MODULE=config.settings.test python3 -m pytest apps/<app>/tests/ -v
```

Für **Infrastructure-Tasks** ersetze Step 4 mit:
```bash
# Health-Check statt Playwright:
mcp0_system_manage(action='health_dashboard')
# oder
mcp0_ssh_manage(action='http_check', url='https://<domain>/healthz/')
```
