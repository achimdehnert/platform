---
description: Pflicht-Ritual vor jeder Coding-Agent-Session — Kontext laden, Stand prüfen, sicher starten
---

# Agent Session Start Workflow

**Trigger:** Jede neue Windsurf/Cascade-Session, bevor der erste Code-Change gemacht wird.

> Dieses Ritual verhindert, dass ein Agent ohne Kontext blind drauflos arbeitet.
> Dauer: ~2 Minuten. Spart Stunden an Debugging und Rollbacks.

---

## Step 1: Repo-Kontext laden (immer)

Lese in dieser Reihenfolge — alle drei, kein Überspringen:

```
1. AGENT_HANDOVER.md           — Infra-Kontext: Hetzner, Cloudflare, Deploy-Targets, MCP-Tools
2. docs/CORE_CONTEXT.md        — Tech Stack, Architektur-Regeln, Verbotene Muster
3. docs/adr/README.md          — Welche ADRs gelten? (Index genügt)
```

Falls diese Dateien nicht existieren → `/new-github-project` aufrufen.

Danach MCP-Kontext aktiv abrufen:

```
MCP: mcp14_get_context_for_task(repo="<aktuelles-repo>", file_type="<hauptdatei>")
  → Liefert: Architektur-Regeln, ADR-Referenzen, Banned Patterns, Repo-Facts
  → Einmalig pro Session aufrufen — danach ist der Kontext bekannt
```

**Bestätigung (Agent spricht laut aus):**
```
Ich habe gelesen:
- AGENT_HANDOVER: Hetzner-Prod=88.198.191.108, Deploy-Targets bekannt
- CORE_CONTEXT: [3 Sätze Zusammenfassung — Tech Stack + kritische Constraints]
- ADRs: [Anzahl + relevanteste für diese Session]
- Platform-Context: mcp14_get_context_for_task() aufgerufen ✓
```

---

## Step 1.5: Health Dashboard (bei Infra/Deploy-Sessions)

Wenn die Session Infrastruktur, Deployment oder Stack-Upgrades betrifft:

```
MCP: mcp6_system_manage(action: health_dashboard, host: 88.198.191.108)
→ Zeigt Status aller 14+ Platform-Apps auf einen Blick
→ Identifiziert Probleme BEVOR sie die Session blockieren
```

Bei Problemen: erst fixen oder bewusst ignorieren, dann weiterarbeiten.

---

## Step 2: Aufgabe klären (immer)

Bevor irgendetwas implementiert wird:

- [ ] GitHub Issue vorhanden? (Pflicht bei complexity >= simple — ADR-067)
- [ ] Use Case dokumentiert? (Pflicht bei neuer User-Facing-Funktion)
- [ ] ADR nötig? (→ `/adr` aufrufen wenn Architektur-Entscheidung nötig)
- [ ] Governance-Check nötig? (→ `/governance-check` bei complexity >= moderate)

**Bei unklarem Auftrag:** Erst klären, dann starten. Lieber 2 Fragen stellen als 2h falsch implementieren.

---

## Step 3: Repo syncen (immer — verhindert "overwritten by merge")

// turbo
```bash
bash ~/github/platform/scripts/sync-repo.sh
```

Synct WSL-Checkout mit GitHub (Single Source of Truth).
Cascade schreibt gleichzeitig lokal (filesystem MCP) und remote (GitHub MCP) —
ohne Sync divergieren Repos und jeder `git pull` schlägt fehl.

Varianten:
- Alle Repos: `bash ~/github/platform/scripts/sync-repo.sh --all`
- Inkl. Server: `bash ~/github/platform/scripts/sync-repo.sh --full`

---

## Step 4: Branch-Status prüfen

// turbo
```bash
git status && git log --oneline -5
```

Erwartung:
- Sauberer Stand (kein uncommitted work von anderer Session)
- Auf korrektem Branch (main oder feature/XXX)
- Falls dirty: erst aufräumen (commit, stash, oder bewusst weiterführen)

---

## Step 5: Tests baseline (bei Test-kritischen Repos)

// turbo
```bash
pytest tests/ -q --tb=no 2>&1 | tail -5
```

Zweck: Sicherstellen dass Tests VOR meinen Änderungen grün waren.
Falls Tests rot: **Erst fixen, dann neue Arbeit starten.** Nie auf roter Basis aufbauen.

---

## Step 6: Knowledge-Lookup (ADR-145) — 3-Layer Search

Bevor der Plan erstellt wird — 3 gezielte Outline-Suchen durchführen:

### 6a: Repo-Steckbrief laden (immer)

```
outline-knowledge: search_knowledge("Repo-Steckbrief: <repo-name>")
→ get_document() → Quick Facts, Ports, Container, bekannte Issues
```

### 6b: Task-spezifisches Wissen (immer)

```
outline-knowledge: search_knowledge("<Thema der Aufgabe>")
→ Runbooks, Konzepte, ADR-Reviews
```

Beispiele:
- `"deployment Django-Hub"` — vor Deploy
- `"RLS row level security"` — vor Datenbank-Arbeit
- `"Cloudflare DNS nginx"` — vor neuem Service
- `"Outline webhook HMAC"` — vor Webhook-Integration

### 6c: Lessons Learned prüfen (bei Debugging/Infra)

```
outline-knowledge: search_knowledge("Lesson <Fehlerbild>")
→ Bekannte Stolperfallen, Root Causes, Vermeidungs-Strategien
```

### Auswertung

- **Treffer gefunden?** → `get_document()` und als Kontext nutzen
- **Kein Treffer?** → Neues Wissensgebiet — am Session-Ende `/knowledge-capture` ausführen

### Outline Collection IDs (Quick-Reference)

| Collection | ID | Inhalt |
|---|---|---|
| Runbooks | `a67c9777-3bc3-401a-9de3-91f0cc6c56d9` | How-To Guides, Repo-Steckbriefe |
| Konzepte | `04064c28-a847-4bec-9bc3-a74d5e1012a2` | Architektur, Cross-Repo |
| Lessons Learned | `db8291c2-f135-4834-878e-224db5673ab6` | Fehler, Root Causes |
| ADR Mirror | `cf12fd43-4b14-4e1f-9603-dd7cb124071f` | Alle ADRs (read-only) |

---

## Step 7: Arbeitsplan aufstellen

Agent erstellt IMMER einen expliziten Plan vor der Ausführung:

```
Mein Plan für diese Session:
1. [Schritt 1 — konkreter Deliverable]
2. [Schritt 2]
3. [Schritt 3]

Geschätzte Komplexität: trivial | simple | moderate | complex
Risk Level: low | medium | high
Gate Level: 0 (autonom) | 1 (notify) | 2 (approve) | 3 (sync)
```

Bei complexity >= moderate → `/agentic-coding` verwenden.

---

## Step 8: Session-Ende Checkliste

Am Ende **jeder** Session, bevor die Verbindung getrennt wird:

- [ ] `AGENT_HANDOVER.md` aktualisiert falls neue Infra-Änderungen
- [ ] Alle Tests grün (`pytest tests/ -q`)
- [ ] Kein uncommitted work (oder bewusster WIP-Commit mit `wip:` Präfix)
- [ ] Offene Issues / PRs verlinkt
- [ ] Neues ADR angelegt falls Architektur-Entscheidung getroffen
- [ ] `/knowledge-capture` ausgeführt falls neues Wissen entstanden (ADR-145)
- [ ] Auch **mid-session** Lessons Learned erfassen wenn Root Cause gefunden wird
- [ ] Repo syncen: `bash ~/github/platform/scripts/sync-repo.sh`

---

## Schnell-Referenz: Welcher Workflow wofür?

| Situation | Workflow |
|-----------|----------|
| Neue Feature-Implementierung | `/agentic-coding` |
| Bug in Produktion | `/hotfix` |
| Neues Repo aufsetzen | `/onboard-repo` |
| GitHub-Infra in Repo verankern | `/new-github-project` |
| ADR anlegen | `/adr` |
| ADR reviewen | `/adr-review` |
| Use Case definieren | `/use-case` |
| Governance prüfen | `/governance-check` |
| Deployen | `/deploy` |
| DB-Backup | `/backup` |
| Windsurf-Verbindung tot | `/windsurf-clean` |
| Wissen sichern nach Session | `/knowledge-capture` |
| Third-Party Stack upgraden | `/stack-upgrade` |
| Repo-Sync nach Cascade-Session | `/sync-repo` |
