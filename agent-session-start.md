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
MCP: mcp11_get_infra_context()
  → Liefert: Hetzner-Hosts, Cloudflare-Domains, Deploy-Targets (9 Repos),
    MCP-Server-Registry, Quick-Reference-Tool-Calls
  → Einmalig pro Session aufrufen — danach ist der Infra-Kontext bekannt
```

**Bestätigung (Agent spricht laut aus):**
```
Ich habe gelesen:
- AGENT_HANDOVER: Hetzner-Prod=88.198.191.108, 9 Deploy-Targets bekannt
- CORE_CONTEXT: [3 Sätze Zusammenfassung — Tech Stack + kritische Constraints]
- ADRs: [Anzahl + relevanteste für diese Session]
- Infra-Kontext: mcp11_get_infra_context() aufgerufen ✓
```

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

## Step 6: Knowledge-Lookup (ADR-145)

Bevor der Plan erstellt wird — prüfe ob relevantes Wissen in Outline existiert:

```
outline-knowledge: search_knowledge("<Thema der aktuellen Aufgabe>")
```

- **Treffer gefunden?** → `get_document()` und als Kontext nutzen (Runbook, Lesson Learned)
- **Kein Treffer?** → Neues Wissensgebiet — am Session-Ende `/knowledge-capture` ausführen

Beispiele für gute Suchanfragen:
- `"OIDC authentik troubleshooting"` — vor OIDC-Integration
- `"RLS rollout"` — vor Row-Level-Security Deployment
- `"Cloudflare tunnel neue domain"` — vor neuem Service-Setup

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
| Repo-Sync nach Cascade-Session | `/sync-repo` |
