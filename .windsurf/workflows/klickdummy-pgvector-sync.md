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

Repo-Liste (Stand 2026-08-10, bei neuen KD-Repos erweitern — Discovery: `ls -d $GITHUB_DIR/*/klickdummy`):

```
risk-hub,ausschreibungs-hub,design-hub,apo-hub,nl2iot-hub,pg-hub,iil-voice-agent,illustration-hub,travel-beat,writing-hub,iil-klickdummy,sqf-hub,tax-hub,trading-hub,coach-hub,dms-hub,onboarding-hub,research-hub,billing-hub,recruiting-hub,weltenhub,dev-hub,pptx-hub,137-hub
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
- ❌ Einen gekappten Entry als vollständigen Treffer lesen. Bis iil-klickdummy 1.33.x kappte
  der Produzent ADR-Bodies bei 8000 Zeichen; seit
  [#207](https://github.com/iilgmbh/iil-klickdummy/pull/207) wird stattdessen an
  `##`-Grenzen gechunkt (`…:ADR-007#2`, Titel `(Teil 2/4)`). Ein Treffer auf einem
  Folge-Chunk ist **normal**, kein Dublett — alle Chunks tragen dieselben ADR-Tags.
  Offene Restlücke: schrumpft ein ADR wieder, bleiben höhere `#N` stale
  ([iil-klickdummy#205](https://github.com/iilgmbh/iil-klickdummy/issues/205)).

## Changelog

- 2026-07-12: Initial (KONZ-risk-hub-008 MVC Schritt 1; Backfill-Baseline 125 Entries/14 Repos).
- 2026-07-15: Repo-Liste +tax-hub +trading-hub (Discovery-Fund; 139 Entries/16 Repos). ttz-hub hat jetzt auch `klickdummy/` — bleibt gov-ausgeschlossen (E3).
- 2026-07-24: Repo-Liste +coach-hub +dms-hub +onboarding-hub +research-hub (Discovery), −pptx-hub −dev-hub (kein `klickdummy/` mehr); frist-hub (meiki-lra) neu mit KD → gov-ausgeschlossen (E3). 143 Entries/18 Repos; Producer-Duplikat-Bug gemeldet iilgmbh/iil-klickdummy#188.
- 2026-07-30: Anti-Pattern „`Sync-Zeit` im Entry-Content ⇒ Dedup greift nie" **entfernt — die
  Aussage war falsifiziert**, nicht nur veraltet. Belege, zwei unabhängige: (1) der Produzent
  `sync_to_orchestrator.py` enthält kein `Sync-Zeit`/`datetime`/`now()`/`strftime`, (2) im Lauf
  über 20 Repos tragen **0 von 243** Entries einen Zeitstempel. Der Lauf 2026-07-29 zeigte
  passend dazu 57/142 `written: false`, also greifenden `content_hash`-Dedup. Ersetzt durch das
  Chunk-Anti-Pattern (iil-klickdummy#199/#207). Die alte Notiz hätte weiter davon abgeraten,
  den Sync häufiger als nightly zu takten — mit einer Begründung, die nicht mehr zutrifft.
- 2026-08-03: Repo-Liste +billing-hub +recruiting-hub +weltenhub +dev-hub +pptx-hub
  (Discovery; dev-hub und pptx-hub haben wieder `klickdummy/`). frist-hub (meiki-lra) und
  ttz-hub (ttz-lif) weiter gov-ausgeschlossen (E3). 160 Entries/23 Repos, R3 PASS
  (160/160, 28 written, Rest content_hash-Dedup). Schema-WARNs pg-hub bereits getrackt
  (bahn-sqf/pg-hub#8). Betriebs-Hinweis: orchestrator-Key-Rotation 2026-08-02 war in
  `~/.claude.json` nicht nachgezogen (403 beim MCP-Bind) — Client-Nachzug gehört zur
  Rotations-Checkliste (Wiederholung von 2026-07-12, mcp-hub#175).
- 2026-08-10: Repo-Liste +137-hub (Discovery; `achimdehnert`, kein Gov-Marker → syncbar).
  frist-hub (meiki-lra) und ttz-hub (ttz-lif) weiter gov-ausgeschlossen (E3). 164 Entries/
  24 Repos, R3 PASS (164/164, 3 written, Rest content_hash-Dedup). Schema-WARNs:
  design-hub (4 Module, neu — grounding/personas/datafields-Format), nl2iot-hub (2 Module,
  neu), pg-hub (2, bereits getrackt bahn-sqf/pg-hub#8). Producer emittiert 137-hub:ADR-002
  doppelt (byte-identisch, Zeile 163/164) — Duplikat-Bug-Muster wie iilgmbh/iil-klickdummy#188.
- 2026-08-11: Turnus-Lauf ohne Abweichung — 164 Entries/24 Repos, R3 PASS (164/164,
  1 written: tax-hub ADR-001, Rest content_hash-Dedup). nl2iot-hub-Schema-WARNs jetzt
  getrackt ([iilgmbh/nl2iot-hub#5](https://github.com/iilgmbh/nl2iot-hub/issues/5));
  design-hub bereits getrackt (design-hub#36/#38). Hinweis: nl2iot-hub-Remote zeigt
  lokal noch auf `achimdehnert` (Org-Transfer → GitHub-Redirect, stale-owner-Muster).
