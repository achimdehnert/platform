# agent-session-start.md
# Windsurf Workflow: /agent-session-start
# Platform: iil-Platform-Stack
# Updated: 2026-03-14 — Added Step 5: Knowledge-Lookup (ADR-145)
# Path: .windsurf/workflows/agent-session-start.md

## Zweck
Standardisierter Session-Start für alle iil-Platform-Entwicklungssessions.
Lädt Architektur-Kontext, Memory und Knowledge Hub in definierter Reihenfolge.

---

## Schritt 1: Platform-Kontext laden

1. Lies `platform/docs/adr/INDEX.md` (ADR-Übersicht)
2. Identifiziere aktive ADRs für den aktuellen Arbeitsbereich (Hub)
3. Lade die relevantesten 2-3 ADRs vollständig

**Priorität-ADRs (immer laden):**
- ADR-050: Platform Decomposition (Hub-Landscape)
- ADR-045: Settings & Secrets Standard
- ADR-044: MCP-Hub Architecture Standards
- ADR-094/010: Platform Context & Windsurf Workflow Optimization

---

## Schritt 2: Cascade Memory-Check

Lies die aktuellen Cascade Memories:
- Welcher Hub ist aktiv?
- Welche offenen Tasks gibt es?
- Welche Deployment-Facts sind relevant?

Wenn Memories unvollständig oder > 7 Tage alt: Hinweis an Nutzer.

---

## Schritt 3: Aktuellen Arbeitsbereich prüfen

1. Welcher Hub / welches Repo ist das Ziel dieser Session?
2. Lies `project-facts.md` des Hubs (immer aktiv via `.windsurf/rules/`)
3. Prüfe offene GitHub Issues (`/gh-status` wenn nötig)

---

## Schritt 4: Environment-Check

```bash
# Docker-Status des Hubs prüfen
docker ps --filter "name=<hub>" --format "table {{.Names}}\t{{.Status}}"
```

Wenn Container nicht laufen: Hinweis ausgeben, aber Session nicht blockieren.

---

## Schritt 5: Knowledge-Lookup (NEU — ADR-145)

**Zweck:** Verhindert Session-Amnesie durch Abrufen relevanter Runbooks,
Konzepte und Lessons Learned aus dem Outline Knowledge Hub.

### 5.1 Thema der Session identifizieren

Analysiere die Aufgabenbeschreibung und extrahiere:
- **Hauptthema:** z.B. "OIDC authentik Integration", "Docker Networking", "RLS Migration"
- **Betroffene Komponenten:** z.B. "coach-hub", "authentik", "Cloudflare Tunnel"

### 5.2 Knowledge Hub durchsuchen

```
# Suche nach dem Hauptthema
outline-knowledge: search_knowledge("<hauptthema>", limit=5)

# Wenn erstes Ergebnis relevant: vollständigen Inhalt laden
outline-knowledge: get_document("<document_id>")
```

**Suchstrategie:**
- Erst spezifisch: `"OIDC authentik self-signed cert"`
- Dann breiter: `"OIDC authentik"`, dann `"OIDC"`
- Maximal 3 Suchen pro Session-Start

### 5.3 Gefundenes Wissen in Kontext einbeziehen

Wenn Runbook/Lesson gefunden:
- Lade den vollständigen Inhalt
- Beachte insbesondere: Anti-Patterns, bekannte Stolperfallen, Verifizierungsschritte
- Informiere den Nutzer: *"Ich habe ein relevantes Runbook gefunden: [Titel]"*

Wenn kein Treffer:
- Neues Wissensgebiet — am Session-Ende Runbook erstellen (`/knowledge-capture`)
- Merke: *"Kein Wissen zu [Thema] gefunden — nach Session dokumentieren"*

---

## Schritt 6: Session-Ziel bestätigen

Kurze Zusammenfassung an den Nutzer:
1. Aktiver Hub + relevante ADRs
2. Gefundene Knowledge-Dokumente (oder "keine gefunden")
3. Wichtigste Anti-Patterns / Lessons Learned
4. Nächste konkrete Aktion

**Format:**
```
🚀 Session bereit

📂 Hub: <hub-name>
📋 ADRs: ADR-XXX, ADR-YYY
📚 Knowledge: <Runbook-Titel> (gefunden) | ⚠️ Kein Wissen gefunden — /knowledge-capture am Ende
⚡ Nächster Schritt: [Aufgabe]
```

---

*Workflow-Version: 2.0 | ADR-145 Integration | 2026-03-14*

---
---

# knowledge-capture.md
# Windsurf Workflow: /knowledge-capture
# Platform: iil-Platform-Stack
# Erstellt: 2026-03-14 (ADR-145 Phase 5.7)
# Path: .windsurf/workflows/knowledge-capture.md

## Zweck
Strukturiertes Session-Ende-Ritual. Verhindert Knowledge Drain durch
systematisches Erfassen von Troubleshooting-Wissen, Architektur-Entscheidungen
und Lessons Learned im Outline Knowledge Hub.

**Wann aufrufen:** Am Ende jeder produktiven Session, die neues Wissen erzeugt hat.
**Aufwand:** 5-10 Minuten (mit AI-Unterstützung).

---

## Schritt 1: Session-Audit

Beantworte intern (nicht ausgeben):
- Wurde ein Problem debuggt oder gelöst?
- Wurden Architektur-Entscheidungen getroffen oder evaluiert?
- Wurden Anti-Patterns oder Stolperfallen identifiziert?
- Wurde ein Deployment, eine Integration oder ein neues Muster eingeführt?

Wenn alle Antworten Nein: Kein Capture nötig. Session beenden.

---

## Schritt 2: Troubleshooting-Runbook (wenn Problem gelöst)

**Kriterium:** Problem benötigte > 30 Minuten oder hatte eine nicht-offensichtliche Lösung.

Erstelle via `outline-knowledge: create_runbook()`:

```markdown
## Symptom
[Was war das sichtbare Problem? Fehlermeldung, Verhalten]

## Umgebung
[Hub, Docker-Stack, Cloudflare/Hetzner-Kontext, Versionen]

## Root Cause
[Was war die eigentliche Ursache? Warum ist es passiert?]

## Lösung (Step-by-Step)
1. [Schritt 1]
2. [Schritt 2]
...

## Verifikation
[Wie überprüft man, dass das Problem gelöst ist?]

## Anti-Pattern
[Was NICHT tun? Warum war der erste Ansatz falsch?]

## Verwandte Ressourcen
[Links, Outline-Dokumente, ADRs]
```

**Pflichtfelder für `create_runbook()`:**
- `title`: Kurz und präzise, z.B. `"OIDC authentik: self-signed cert hinter Cloudflare"`
- `content`: Vollständiges Runbook wie oben
- `related_adrs`: Liste der relevanten ADR-IDs

---

## Schritt 3: Architektur-Konzept (wenn Design-Entscheidung getroffen)

**Kriterium:** Eine signifikante technische Entscheidung wurde evaluiert oder getroffen.

Erstelle via `outline-knowledge: create_concept()`:

```markdown
## Kontext
[Warum musste eine Entscheidung getroffen werden?]

## Evaluierte Optionen
| Option | Pros | Cons |
|--------|------|------|
| A | ... | ... |
| B | ... | ... |

## Entscheidung
[Welche Option wurde gewählt? Warum?]

## Konsequenzen
[Was ändert sich? Was sind die Implikationen?]
```

---

## Schritt 4: Lesson Learned (wenn Anti-Pattern identifiziert)

**Kriterium:** Eine nicht-offensichtliche Falle, die andere Entwickler kennen sollten.

Erstelle via `outline-knowledge: create_lesson_learned()`:
- `session_date`: Heutiges Datum (YYYY-MM-DD)
- `title`: Knappes Anti-Pattern, z.B. `"OIDC URIs: Kein Slug im /application/o/ Pfad"`
- `content`: Problem, Ursache, Fix, Vermeidung

---

## Schritt 5: Bestehendes Runbook aktualisieren

**Kriterium:** Ein vorhandenes Runbook wurde durch neue Erkenntnisse erweitert.

```
outline-knowledge: update_document(
    document_id="<id>",
    content="## Update [Datum]\n\n[Neue Erkenntnisse]",
    append=True
)
```

---

## Schritt 6: Cascade Memory updaten

Aktualisiere Cascade Memory mit:
- Session-Ergebnis (was wurde implementiert/gelöst)
- Neue Deployment-Facts (URLs, Container-Namen, Ports)
- Nächste konkrete Aufgabe für die Folge-Session

---

## Abschluss-Bestätigung

```
✅ Knowledge Capture abgeschlossen

📝 Runbook erstellt: [Titel oder "—"]
💡 Konzept erstellt: [Titel oder "—"]
⚠️ Lesson Learned: [Titel oder "—"]
🧠 Cascade Memory: Aktualisiert

🔗 Outline Links:
  [URL 1]
  [URL 2]
```

---

*Workflow-Version: 1.0 | ADR-145 | 2026-03-14*
