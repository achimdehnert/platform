---
description: Session-Ende Knowledge Capture — Wissen in Outline sichern (ADR-145)
---

# Knowledge Capture Workflow

**Trigger:** `/knowledge-capture` — am Ende jeder produktiven Session ODER mid-session.

> **Der User muss NICHTS auflisten.** Der Agent scannt die Session autonom
> und identifiziert, was in Outline gesichert werden muss.

---

## Step 0: Session-Scan (AUTONOM — Agent führt aus)

Der Agent analysiert die aktuelle Session und beantwortet folgende Fragen:

1. **Welche Repos wurden verändert?** (git status/log der Workspaces prüfen)
2. **Welche Features wurden gebaut?** (Commits seit Session-Start)
3. **Welche ADRs wurden erstellt/geändert?** (platform/docs/adr/)
4. **Welche Bugs wurden gefixt?** (Commit-Messages mit "fix:")
5. **Was wurde deployed?** (Welcher Service, welche URL, Health-Status)
6. **Welche Architektur-Entscheidungen wurden getroffen?**
7. **Welche Probleme traten auf und wie wurden sie gelöst?**

// turbo
Führe aus: `git -C <workspace> log --oneline --since="6 hours ago"` für jeden aktiven Workspace.

Dann erstelle eine **Session-Zusammenfassung** mit diesen Feldern:

```
REPOS: [Liste der veränderten Repos]
FEATURES: [Neue Features mit 1-Satz-Beschreibung]
FIXES: [Bugs die gefixt wurden]
ADRS: [Erstellt/geändert mit Nummer + Titel]
DEPLOYMENTS: [Service → URL → Health-Status]
LESSONS: [Probleme + Root Cause, falls vorhanden]
DECISIONS: [Architektur-Entscheidungen]
```

---

## Step 1: Outline durchsuchen — existiert schon ein Dokument?

// turbo
Suche in Outline nach jedem betroffenen Repo/Feature:

```
search_knowledge("<repo-name>")
search_knowledge("<feature-name>")
```

→ **Treffer?** → Step 4b (bestehendes Dokument aktualisieren)
→ **Kein Treffer?** → Weiter zu Step 1b

### Step 1b: Klassifiziere — Was wird in Outline gesichert?

| Situation | Aktion |
|-----------|--------|
| Bug gefixt, Root Cause gefunden | → Step 2 (Runbook) |
| Neues Architektur-Pattern / ADR | → Step 3 (Konzept) |
| Unerwarteter Fehler / Anti-Pattern | → Step 4 (Lesson) |
| Neuer Service deployed | → Step 2 (Deployment-Runbook) |
| Nur Code geschrieben, nichts Neues gelernt | → Skip |
| Feature gebaut + deployed | → Step 4b (bestehendes Hub-Dok updaten) |
| Bestehendes Runbook ergänzen | → Step 4b (Update) |
| **Mid-Session: 500/Error** | → **Erst `search_knowledge()` vor Debugging** |

---

## Step 2: Runbook erstellen (bei Troubleshooting)

Wenn ein Problem debuggt und gelöst wurde:

```
outline-knowledge: create_runbook(
    title="<Problem-Beschreibung>",
    content="## Wann nutzen\n\n<Kontext>\n\n## Schritt-für-Schritt\n\n<Steps>\n\n## Bekannte Fehler\n\n| Symptom | Ursache | Fix |\n",
    related_adrs="<ADR-Nummern>"
)
```

**Runbook-Template:**
```markdown
## Wann nutzen

[Beschreibung wann dieses Runbook relevant ist]

## Voraussetzungen

- [Was muss vorhanden sein]

## Schritt-für-Schritt

1. [Konkreter Schritt mit Command/Code]
2. [Nächster Schritt]

## Bekannte Fehler

| Symptom | Ursache | Fix |
|---------|---------|-----|

## Referenzen

- ADR-XXX, ADR-YYY
```

---

## Step 3: Konzept erstellen (bei Architektur-Entscheidung)

Wenn eine Design-Entscheidung getroffen wurde:

```
outline-knowledge: create_concept(
    title="<Konzept-Name>",
    content="## Problem\n\n<Was gelöst werden musste>\n\n## Entscheidung\n\n<Was gewählt wurde und warum>\n\n## Alternativen\n\n<Was verworfen wurde>",
    related_adrs="<ADR-Nummern>"
)
```

---

## Step 4: Lesson Learned erstellen (bei Anti-Pattern / Stolperfalle)

Wenn etwas Unerwartetes passiert ist:

```
outline-knowledge: create_lesson(
    title="<Datum>: <Kurzbeschreibung>",
    content="## Kontext\n\n<Was passiert ist>\n\n## Root Cause\n\n<Warum>\n\n## Merksatz\n\n> <Ein-Satz-Zusammenfassung>\n\n## Vermeidung\n\n<Was in Zukunft anders machen>",
    related_adrs="<ADR-Nummern>"
)
```

> `create_lesson` schreibt direkt in die Collection "Lessons Learned" — kein manuelles Verschieben nötig.

---

## Step 4b: Bestehendes Dokument aktualisieren (bei Ergänzung)

Wenn das Wissen zu einem existierenden Dokument gehört:

```
outline-knowledge: search_knowledge("<Thema>")
→ Treffer gefunden?
→ get_document(document_id) — aktuellen Inhalt lesen
→ update_document(document_id, content="<ergänzter Inhalt>")
```

**Beispiel:** Stack-Upgrade-Erfahrungen zu bestehendem Runbook hinzufügen.

---

## Step 5: Cross-Repo Tagging (bei Hub-übergreifendem Wissen)

Wenn eine Lesson oder ein Runbook für **mehrere Repos** gilt:

Am Ende des Dokuments einen "Gilt für"-Abschnitt hinzufügen:

```markdown
## Gilt für

Alle Django-Hubs (risk-hub, billing-hub, weltenhub, bfagent, etc.)
```

Beispiele für Cross-Repo-Wissen:
- Template-Fehler → 500 (gilt für alle Django-Hubs)
- Docker HEALTHCHECK-Pattern (gilt für alle Hubs)
- decouple.config() statt os.environ (gilt für alle Python-Projekte)

---

## Step 6: Cascade Memory mit Outline-Verweis updaten

Ergänzend zum Outline-Eintrag: Cascade Memory mit kurzem **Verweis auf das Outline-Dokument** aktualisieren.

```
Memory: "<Thema> — Runbook in Outline: <Titel>"
Memory: "<Thema> — Lesson in Outline: <Datum>: <Titel>"
```

Beispiel:
```
Memory: "risk-hub Deployment → Runbook in Outline: risk-hub Deployment (manuell via SSH)"
```

So kann der Agent in der nächsten Session die Memory lesen und gezielt das Outline-Dokument laden.

---

## Schnell-Referenz

**User-Prompt (immer gleich):** `/knowledge-capture`

Der Agent erledigt alles autonom — kein Auflisten nötig.
