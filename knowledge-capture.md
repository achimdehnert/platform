---
description: Session-Ende Knowledge Capture — Wissen in Outline sichern (ADR-145)
---

# Knowledge Capture Workflow

**Trigger:** Am Ende jeder produktiven Session ODER mid-session bei wichtigen Erkenntnissen.

> Verhindert Knowledge Drain — das implizite Wissen aus der Session wird
> strukturiert in Outline gesichert, bevor es verloren geht.
>
> **Mid-Session-Trigger** (sofort erfassen, nicht bis zum Ende warten):
> - Root Cause eines schwierigen Bugs gefunden
> - Breaking Change oder Inkompatibilität entdeckt
> - Neues Pattern etabliert (z.B. Test-Pattern für FastMCP)
>
> **Mid-Session-Suche** (VOR dem Debuggen):
> - Bei jedem 500/Error: `search_knowledge("<Fehlerbild>")` — erst prüfen ob bekannt
> - Bei Architektur-Frage: `search_knowledge("<Thema>")` — Konzept vorhanden?
> - Spart Stunden wenn das Problem schon gelöst wurde

---

## Step 1: Prüfe — Was wurde in dieser Session gelernt?

Gehe diese Checkliste durch:

- [ ] **Troubleshooting-Wissen?** (Fehler debuggt, Root Cause gefunden)
- [ ] **Architektur-Entscheidung?** (Design gewählt, Alternative verworfen)
- [ ] **Lessons Learned?** (Anti-Pattern entdeckt, Stolperfalle dokumentiert)
- [ ] **Deployment-Wissen?** (Neuer Service, Config-Änderung, Infrastruktur)

Wenn **nichts davon** zutrifft → Session war reine Implementierung → Skip.

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

## Schnell-Entscheidung

| Situation | Aktion |
|-----------|--------|
| Bug gefixt, Root Cause gefunden | → Step 2 (Runbook) |
| Neues Architektur-Pattern gewählt | → Step 3 (Konzept) |
| Unerwarteter Fehler / Anti-Pattern | → Step 4 (Lesson) |
| Nur Code geschrieben, nichts Neues | → Skip |
| Deployment durchgeführt | → Step 2 (Deployment-Runbook) |
| Bestehendes Runbook ergänzen | → Step 4b (Update) |
| Stack-Upgrade durchgeführt | → Step 2 (Upgrade-Runbook) |
| Wissen gilt für mehrere Repos | → Step 5 (Cross-Repo Tag) |
| Outline-Eintrag erstellt | → Step 6 (Memory-Verweis) |
| **Mid-Session: 500/Error auftritt** | → **Erst `search_knowledge()` vor Debugging** |
