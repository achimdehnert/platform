---
description: Cascade-Aufträge aus Outline abarbeiten — Triage via Comments, Bearbeitung, Zurückstellen, Archivierung
---

# Cascade-Aufträge Workflow

**Trigger:** Session-Start (nach `/agent-session-start`) ODER explizit via `/cascade-auftraege`.

> Aufträge werden über `/_action` oder den ⚡-Button in die Collection
> **Cascade-Aufträge** (`97a74c51-6c4e-4871-a2b0-a85255b8c916`) erstellt.
> Kommunikation erfolgt **bidirektional über Outline Comments**.

---

## Step 1: Offene Aufträge + Comments laden

```
MCP: <outline-mcp>_list_recent(collection="97a74c51-6c4e-4871-a2b0-a85255b8c916", limit=20)
```

Für jeden Auftrag Comments lesen (Outline API):

```bash
curl -s -X POST https://knowledge.iil.pet/api/comments.list \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"documentId":"<doc-id>"}'
```

Übersicht für den User:

```
# Offene Cascade-Aufträge

| # | Titel | Action | Kommentar |
|---|-------|--------|----------|
| 1 | 📋 Offen — Analyse GEFBU... | analyze | 💬 "jetzt starten" |
| 2 | 📋 Offen — ADR erstellen... | adr | (kein Kommentar) |
```

### 1b: Lesebestätigung posten (PFLICHT)

Für **jeden** Auftrag mit unbeantwortetem User-Comment eine Lesebestätigung posten:

```bash
curl -s -X POST .../api/comments.create \
  -d '{"documentId":"<doc-id>","parentCommentId":"<user-comment-id>",
       "data":{"type":"doc","content":[{"type":"paragraph","content":[
         {"type":"text","text":"Gelesen. <Was ich jetzt tue oder welche Anweisung ich brauche>"}]}]}}'
```

Der User muss in Outline jederzeit sehen können, ob Cascade den Comment gelesen hat.

---

## Step 2: Triage via Comments

User-Comments steuern die Bearbeitung:

| User-Kommentar | Cascade-Aktion |
|---------------|----------------|
| `jetzt starten` / `start` / `los` | Sofort bearbeiten → Step 3 |
| `zurückstellen` / `später` | Status: ⏸️ + Antwort-Comment |
| `Priorität hoch` / `dringend` | Zuerst bearbeiten |
| `abbrechen` / `nicht mehr nötig` | Archivieren + Antwort-Comment |
| Frage / Kontext (Freitext) | Als zusätzliche Anweisung nutzen |

Kein Comment vorhanden → User fragen.

---

## Step 3: Auftrag bearbeiten

### 3a: Titel-Prefix auf "In Arbeit" setzen

```bash
curl -s -X POST .../api/documents.update \
  -d '{"id":"<doc-id>","title":"🔄 In Arbeit — <Kurzbezeichnung>"}'
```

### 3b: Status-Comment posten (PFLICHT)

```bash
curl -s -X POST https://knowledge.iil.pet/api/comments.create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"documentId":"<doc-id>","parentCommentId":"<user-comment-id>",
       "data":{"type":"doc","content":[{"type":"paragraph","content":[
         {"type":"text","text":"🔄 Bearbeitung gestartet..."}]}]}}'
```

### 3c: Zwischen-Status bei langer Bearbeitung (PFLICHT)

Bei Aufträgen die mehrere Schritte umfassen, nach **jedem abgeschlossenen Teilschritt**
einen Status-Comment posten:

```
🔄 Phase 1 implementiert (Commit abc1234). Starte Phase 2...
🔄 PR erstellt. Deploy blockiert — CI/CD Fehler. Analysiere...
```

### 3d: Quell-Dokument + Anweisung lesen

```
MCP: <outline-mcp>_get_document(document_id="<auftrag-id>")
MCP: <outline-mcp>_get_document(document_id="<quell-dokument-id>")
```

### 3e: Action ausführen

| Action | Output | Sub-Workflow |
|--------|--------|-------------|
| `summarize` | Outline-Dokument (Konzepte) | — |
| `adr` | ADR erstellt | `/adr` |
| `github-issue` | GitHub Issue | `mcp8_create_issue` |
| `analyze` | Outline-Dokument | — |
| `review` | Architektur-Review | `/adr-review` |
| `implement` | Branch + PR | `/agentic-coding` |
| `fix-bugs` | Branch + PR | `/hotfix` |
| `estimate` | Comment am Auftrag | — |
| `code-skeleton` | Branch + PR | — |
| `write-tests` | Branch + PR | — |
| `find-related` | Comment am Auftrag | — |
| `checklist` | Outline-Dokument | — |

---

## Step 4: Ergebnis via Comment zurückmelden

### Erledigt

```bash
curl -s -X POST https://knowledge.iil.pet/api/comments.create \
  -d '{"documentId":"<doc-id>","data":{"type":"doc","content":[
    {"type":"paragraph","content":[
      {"type":"text","text":"✅ Erledigt — <Zusammenfassung>"}]},
    {"type":"paragraph","content":[
      {"type":"text","text":"→ <Link zu Ergebnis>"}]}]}}'
```

### Rückfrage

```bash
curl -d '{"documentId":"<doc-id>","data":{"type":"doc","content":[
  {"type":"paragraph","content":[
    {"type":"text","text":"❓ <Konkrete Frage an den User>"}]}]}}'
```

User antwortet in Outline → nächste Session liest den Reply.

---

## Step 5: Abschluss

### 5a: Titel-Prefix auf "Erledigt" setzen

```bash
curl -s -X POST .../api/documents.update \
  -d '{"id":"<doc-id>","title":"✅ Erledigt — <Kurzbezeichnung>"}'
```

### 5b: Dokument-Text mit Ergebnis aktualisieren

```
MCP: <outline-mcp>_update_document(document_id, content="<Text + Ergebnis>")
```

### 5c: Auftrag archivieren

```bash
curl -X POST .../api/documents.archive -d '{"id":"<doc-id>"}'
```

### 5d: Comment resolven

```bash
curl -X POST .../api/comments.resolve -d '{"id":"<comment-id>"}'
```

---

## Kommunikationsfluss

```
User:    [erstellt Auftrag via /_action oder ⚡-Button]
User:    💬 "jetzt starten"
Cascade: 💬 "🔄 Bearbeitung gestartet..."
Cascade: 💬 "❓ Soll der ADR für risk-hub oder Platform?"
User:    💬 "risk-hub"
Cascade: 💬 "✅ Erledigt — ADR-XXX erstellt → /doc/..."
Cascade: [archiviert Auftrag]
```

---

## Titel-Prefixe (PFLICHT)

Jeder Auftrag trägt seinen Status im Titel:

| Prefix | Bedeutung | Wann setzen |
|--------|-----------|-------------|
| `📋 Offen` | Noch nicht begonnen | Step 1 (Triage) |
| `🔄 In Arbeit` | Cascade arbeitet daran | Step 3a |
| `⏸️ Zurückgestellt` | Bewusst verschoben | Step 2 (Triage) |
| `✅ Erledigt` | Abgeschlossen | Step 5a |
| `❌ Abgebrochen` | Nicht mehr relevant | Step 2 (Triage) |

---

## Comment-Prefixe

| Prefix | Wer | Bedeutung |
|--------|-----|----------|
| *(keiner)* | User | Anweisung |
| `Gelesen.` | Cascade | Lesebestätigung (Step 1b) |
| `🔄` | Cascade | In Arbeit / Zwischen-Status |
| `✅` | Cascade | Erledigt + Ergebnis |
| `❓` | Cascade | Rückfrage |
| `⏸️` | Cascade | Zurückgestellt |
| `❌` | Cascade | Fehler / Abbruch |

---

## Schnell-Referenz

```
/cascade-auftraege          → Diesen Workflow starten
/_action                    → Neuen Auftrag erstellen (Browser)
/_upload                    → Dateien hochladen (Browser)
Collection: 97a74c51-...    → Cascade-Aufträge in Outline
Token: ol_api_...           → In localStorage oder Script
```
