---
description: Klickdummy-Specs/Iterationen/ADRs cross-repo in den Orchestrator-pgvector upserten — Schreib-Konsument der klickdummy-sync CLI (KONZ-risk-hub-008, letzte Meile)
mode: write
---

# /klickdummy-pgvector-sync — pgvector-Befüllung für die Cross-Repo-KD-Suche

> **Wann:** Nightly-Routine oder manuell vor KD-Arbeit, damit `/klickdummy-search` aktuelle
> Treffer liefert. Schließt die „letzte Meile" aus KONZ-risk-hub-008 (Produzent = CLI,
> Lese-Konsument = Search-Skill, dieser Skill = fehlender Upsert-Schritt).
> **Wann NICHT:** Verwechsle dies NICHT mit `.github/workflows/klickdummy-sync.yml` in den
> Repos — das ist der **Genesor→GitHub-Issue-Sync** (Counter-A), ein anderer Mechanismus
> mit kollidierendem Namen (KONZ-008 Befund A3). Dieser Skill heißt deshalb `pgvector-sync`.

## Voraussetzungen

- Session bindet `mcp__orchestrator__agent_memory_upsert` (Signatur vor Nutzung via
  `ToolSearch select:mcp__orchestrator__agent_memory_upsert` prüfen — claude-skills-Policy).
- Repo-Checkouts unter `$GITHUB_DIR` sind aktuell (session-start Phase 0.4 pullt die Kern-Repos;
  für einen vollständigen Sync ggf. `git -C <repo> pull` je KD-Repo).
- `iil-klickdummy>=1.32.1` in einem venv (z. B. risk-hubs `.venv-klickdummy` via
  `make -C $GITHUB_DIR/risk-hub klickdummy-install`).

## Step 1 — gov-Ausschluss (KONZ-008 E3, PFLICHT)

Gov-Workloads (Orgs `ttz-lif`, `meiki-lra` → Repos wie `ttz-hub`, `meiki-hub`, `frist-hub`) sind vom
Sync **default-ausgeschlossen**, bis deren Datensouveränitäts-Check die Ablage auf dem
Hetzner-pgvector explizit erlaubt (Repo-CLAUDE.md der Gov-Repos lesen). Das `gov-data`-Tag
im Sync-Code ist Such-Filter-Hilfe, **keine Push-Erlaubnis**.

Repo-Liste (Stand 2026-07-24, bei neuen KD-Repos erweitern — Discovery: `ls -d $GITHUB_DIR/*/klickdummy`):

```
risk-hub,ausschreibungs-hub,design-hub,apo-hub,nl2iot-hub,pg-hub,iil-voice-agent,illustration-hub,travel-beat,writing-hub,iil-klickdummy,sqf-hub,tax-hub,trading-hub,coach-hub,dms-hub,onboarding-hub,research-hub
```

## Step 2 — NDJSON erzeugen

```bash
VENV=$GITHUB_DIR/risk-hub/.venv-klickdummy
OUT=$(mktemp --suffix=.ndjson)
$VENV/bin/klickdummy-sync --cross-repo --base "$GITHUB_DIR" \
  --repos <liste-aus-step-1> --output "$OUT"
wc -l "$OUT"   # merken: N_specs
```

Schema-WARNs (invalide Alt-Specs) sind kein Abbruch — als Befund ans jeweilige Repo melden.

## Step 3 — Upsert-Loop

Für jede NDJSON-Zeile `mcp__orchestrator__agent_memory_upsert` aufrufen mit
`entry_key`, `entry_type`, `title`, `content`, `tags` aus der Zeile und `agent="klickdummy-sync"`.
Mehrere Calls pro Nachricht bündeln. Bei >50 Zeilen: an einen Subagenten delegieren
(der Subagent lädt das Tool-Schema selbst via ToolSearch).

## Step 4 — R3-Invariante (PFLICHT, Zahl statt Exit-Code-Theater)

```
upserted >= 0.9 × N_specs  → sonst FAIL, laut melden (KONZ-008 R3 „Silent-Empty")
```

Ein grüner Lauf mit 0 Upserts ist ein **Fehler**, kein Erfolg (Tunnel down, Pfad-Drift, leere Repo-Liste).

## Step 5 — Report (1 Block)

```
== klickdummy-pgvector-sync <datum> ==
  Repos: <n> · Entries: <upserted>/<N_specs> (failed: <f>)
  je Typ: repo_context <a> · lesson_learned <b> · decision <c>
  R3: PASS|FAIL
```

Bei Nightly-Läufen: Report nur bei FAIL oder Abweichung >10 % zum Vortag eskalieren (Issue), sonst still.

## Kill-Gate-Bezug (KONZ-risk-hub-008)

- **K1:** ≤2 real genutzte `/klickdummy-search`-Treffer bis 2026-08-31 → diesen Skill + Trigger sunsetten.
- **K2:** >20 % stale Einträge in 2 Folge-Wochen → Trigger-Design überarbeiten/killen.

## Anti-Patterns

- ❌ Gov-Repos „nur mit Tag" syncen — Tag schützt nicht vor Ablage (E3).
- ❌ 0-Upsert-Lauf als grün werten (R3).
- ❌ Namen verkürzen zu „klickdummy-sync" — kollidiert mit dem Genesor-Issue-Sync (A3).
- ❌ Bekannter Generator-Makel: `Sync-Zeit` steht im Entry-Content → content_hash ändert sich
  jeden Lauf, Orchestrator-Dedup greift nie (iilgmbh/iil-klickdummy#160-Familie). Bis zum
  Paket-Fix nightly akzeptiert; NICHT stündlich takten.

## Changelog

- 2026-07-12: Initial (KONZ-risk-hub-008 MVC Schritt 1; Backfill-Baseline 125 Entries/14 Repos).
- 2026-07-15: Repo-Liste +tax-hub +trading-hub (Discovery-Fund; 139 Entries/16 Repos). ttz-hub hat jetzt auch `klickdummy/` — bleibt gov-ausgeschlossen (E3).
- 2026-07-24: Repo-Liste +coach-hub +dms-hub +onboarding-hub +research-hub (Discovery), −pptx-hub −dev-hub (kein `klickdummy/` mehr); frist-hub (meiki-lra) neu mit KD → gov-ausgeschlossen (E3). 143 Entries/18 Repos; Producer-Duplikat-Bug gemeldet iilgmbh/iil-klickdummy#188.
