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
- 2026-08-13: Turnus-Lauf — 164 Entries/24 Repos, R3 PASS (164/164 `ok`, 0 failed;
  3 written, Rest content_hash-Dedup). Producer-Duplikat aus dem 2026-08-10-Lauf
  (137-hub:ADR-002 doppelt) ist **weg**: 164 Zeilen = 164 unique `entry_key` unter
  `iil-klickdummy 1.34.0`. Schema-WARNs unverändert und alle getrackt: pg-hub 110
  (bahn-sqf/pg-hub#8), design-hub 36 (design-hub#36/#38), nl2iot-hub 31 (nl2iot-hub#5).
- 2026-08-13 **NEUES ANTI-PATTERN — Trailing-Whitespace überlebt den Upsert-Schritt nicht
  zuverlässig.** Genau die 3 Entries, deren `content` auf eine Leerzeile endet
  (`ausschreibungs-hub:ADR-002`, `design-hub:ADR-007#2`, `sqf-hub:ADR-003`), kamen mit
  `written: true` zurück — der abschließende `\n` ging beim Durchreichen durch den
  Tool-Call verloren und wurde erst im zweiten Anlauf korrekt gespeichert. Ursache ist
  der Mechanismus selbst: Step 3 reicht `content` über LLM-Textreproduktion weiter, und
  endständiger Whitespace ist dabei die fragilste Stelle. **Konsequenz für Step 4:** ein
  `written: true` bei einem Entry, dessen Quelldatei sich nachweislich nicht geändert hat,
  ist ein **Fidelity-Verdacht**, kein Erfolg — Entry gegen die NDJSON-Zeile gegenlesen
  (`mcp__orchestrator__agent_memory_search` gibt `content` vollständig JSON-kodiert zurück,
  Tail direkt als `\n\n` ablesbar) statt blind neu zu schreiben. Der `content_hash` hat den
  Verlust sichtbar gemacht; ohne ihn wäre er still durchgelaufen.
  ❌ **Nicht** per Re-Upsert „verifizieren" — der Test überschreibt sein eigenes Prüfobjekt
  und ein Transkriptionsfehler des Prüfers erzeugt einen Falschbefund gegen den Vorgänger.
  Lesend prüfen ist billiger und nicht-destruktiv.
- 2026-08-13 **Verteilungs-Drift:** die an risk-hub verteilte Skill-Kopie hing auf
  `source_commit=bb17444e2d8f` (Repo-Liste ohne 137-hub, Changelog bis 2026-08-03) —
  zwei Läufe hinter dieser Quelle. Wer nur die verteilte Kopie liest, syncte 23 statt
  24 Repos. Vor „Repo-Liste erweitern" erst diese Quelldatei prüfen, nicht die Kopie.
- 2026-08-17: Turnus-Lauf — 164 Entries/24 Repos, R3 PASS (164/164 `ok`, 0 failed;
  **0 written**, alles content_hash-Dedup). Keine Verteilungs-Drift (Quelle und verteilte
  Kopie beide `39efc9aa`). Discovery fand 26 Repos mit `klickdummy/`; frist-hub (meiki-lra)
  und ttz-hub (ttz-lif) bleiben gov-ausgeschlossen (E3) → Liste unverändert 24.
  Schema-WARNs unverändert und alle getrackt: pg-hub 110 (bahn-sqf/pg-hub#8),
  design-hub 36 (design-hub#36/#38), nl2iot-hub 31 (nl2iot-hub#5). 164 Zeilen =
  164 unique `entry_key` (kein Producer-Duplikat) unter `iil-klickdummy 1.34.0`.
- 2026-08-17 **Präzisierung zum Trailing-Whitespace-Anti-Pattern:** die Notiz vom
  2026-08-13 las sich, als beträfe das Risiko drei Sonderfälle. Gemessen enden
  **alle 164** Entries auf `\n` und **6** auf `\n\n` (ausschreibungs-hub:ADR-002,
  design-hub:ADR-007 + #2 + #3, risk-hub:ADR-046, sqf-hub:ADR-003) — endständiger
  Whitespace ist also bei *jedem* Entry die fragile Stelle, nicht bei einer Handvoll.
  Lesende Gegenprobe über 6 Entries (inkl. eines `\n\n`-Falls): Tails byte-genau.
- 2026-08-17 **NEUES ANTI-PATTERN — `written: false` ist ein vollständiger No-Op, nicht
  „Content unverändert".** Alle 164 Calls dieses Laufs setzten weisungsgemäß
  `agent="klickdummy-sync"`; trotzdem trägt `klickdummy-adr:iilgmbh:risk-hub:ADR-055`
  im Store weiterhin `agent="iil-klickdummy-sync"`. Bei Hash-Gleichheit wird **kein**
  Feld aktualisiert, auch keine Metadaten. Ursache des Mischbestands: das NDJSON führt
  selbst ein Feld `"agent": "iil-klickdummy-sync"`, während Step 3 `klickdummy-sync`
  vorschreibt — je nachdem, welcher Wert beim *ersten* Schreiben eines Entry-Keys galt,
  ist er dort eingefroren. **Konsequenz:** Metadaten-Korrekturen (agent, tags) sind über
  den Upsert-Pfad nicht durchsetzbar, solange der Content gleich bleibt; ein `agent`-Filter
  auf dem Store ist damit unzuverlässig. Getrackt: iilgmbh/iil-klickdummy#221.
- 2026-08-22: Turnus-Lauf — **165** Entries/24 Repos, R3 PASS (165/165 `ok`, 0 failed;
  **0 written**, alles content_hash-Dedup). Keine Verteilungs-Drift (verteilte Kopie
  `5f31af77` byte-identisch zur Quelle). Discovery fand weiter 26 Repos mit `klickdummy/`;
  frist-hub (meiki-lra) und ttz-hub (ttz-lif) bleiben gov-ausgeschlossen (E3) → Liste
  unverändert 24. 165 Zeilen = 165 unique `entry_key` (kein Producer-Duplikat) unter
  `iil-klickdummy 1.34.0`. Schema-WARNs unverändert und alle getrackt: pg-hub
  (bahn-sqf/pg-hub#8), design-hub (design-hub#36/#38), nl2iot-hub (nl2iot-hub#5).
  164→165 kommt von `klickdummy:iilgmbh:risk-hub:grundschutz` (Spec neu seit 2026-08-18).
- 2026-08-22 **Falsifiziert — „neues ADR fehlt im NDJSON" ist kein Producer-Gap.**
  writing-hub bekam seit dem letzten Lauf `ADR-203` und `ADR-204`; beide tauchen im
  NDJSON nicht auf, `ADR-203` nennt „Klickdummy" sogar im Fließtext. Der Producer
  selektiert aber über **`tags: [klickdummy]` im Frontmatter** (Gegenprobe: das
  aufgenommene `ADR-199` trägt den Tag, `ADR-203` nicht). Ein Volltext-`grep` auf
  „klickdummy" ist als Vollständigkeits-Check des Sync also untauglich — er erzeugt
  Falsch-Positive.
- 2026-08-22 **NEUER BEFUND — Gov-Daten liegen im Store, E3 räumt Altbestand nicht ab.**
  Eine einzige lesende Suche fand ≥6 `meiki-lra:frist-hub`-Entries (ADR-003 + fünf
  Iterations-Zeilen), alle mit `agent="klickdummy-sync"`. `frist-hub:ADR-003` ist auf
  2026-07-21 datiert, die Datei existiert also erst seit dem 21.07. — der Erstschreib
  fiel damit **hinter** die E3-Einführung (12.07.). E3 verhindert Neuschreiben, nicht
  Bestand. Zahl nach oben unbekannt; der billigste Check ist store-seitig
  (`tags @> '{"klickdummy:org:meiki-lra"}'`), über `agent_memory_search` nicht zu
  bekommen. Entscheidung Owner (löschen / dokumentieren / als Restlücke führen):
  iilgmbh/risk-hub#666.
- 2026-08-22 **NEUER BEFUND — es gab einen Lauf ohne Changelog-Eintrag.** `grundschutz`
  tauchte heute erstmals im NDJSON auf und kam trotzdem mit `written: false` zurück; im
  Store trägt der Entry `agent="klickdummy-sync"`. Das NDJSON führt selbst
  `"agent": "iil-klickdummy-sync"`, `klickdummy-sync` setzt nur **Step 3 dieses Skills**,
  und `agent` friert beim Erstschreib ein (Eintrag 2026-08-17). Der Spec-Inhalt (v1.5)
  existiert erst seit 2026-08-18 ⇒ zwischen 18.08. und 21.08. lief dieser Skill mindestens
  einmal, ohne hier eine Zeile zu hinterlassen. Konsequenz für die Lauf-Buchführung: der
  Changelog ist **kein** vollständiges Lauf-Register — „N seit letztem Eintrag" ist keine
  belastbare Delta-Basis.
- 2026-08-23: **Manueller Lauf** — 165 Entries/24 Repos, R3 PASS (165/165 `ok`, 0 failed;
  **0 written**, alles content_hash-Dedup). 165 Zeilen = 165 unique `entry_key` unter
  `iil-klickdummy 1.34.0`; Producer deterministisch (zweiter Lauf byte-identisch).
  Keine Verteilungs-Drift (Quelle und verteilte Kopie beide `5f31af776fa5`).
  Discovery fand 26 Repos mit `klickdummy/`; frist-hub (meiki-lra) und ttz-hub (ttz-lif)
  bleiben gov-ausgeschlossen (E3) → Liste unverändert 24. Schema-WARNs unverändert und
  alle getrackt: pg-hub 110 (bahn-sqf/pg-hub#8), design-hub 36 (design-hub#36/#38),
  nl2iot-hub 31 (nl2iot-hub#5).
- 2026-08-23 **Der nächtliche Lauf fiel aus.** `~/logs/klickdummy-pgvector-sync.log`
  endet auf dem Block `2026-08-22`, mtime 2026-08-22 03:32 — der Cron-Eintrag (`17 3 * * *`)
  hat am 23.08. nichts angehängt. Der manuelle Lauf ersetzt ihn; die Ursache des
  Ausfalls ist **nicht** untersucht. Billigster Check beim nächsten Mal: `systemctl
  status cron` bzw. Uptime des Hosts um 03:17 gegenprüfen.
- 2026-08-23 **NEUES ANTI-PATTERN — „0 written bei gewachsener Entry-Zahl" ist keine
  Anomalie, und der Changelog ist die falsche Referenz dafür.** Heute stieg die
  Entry-Zahl von 164 auf 165, während *kein* Entry geschrieben wurde. Das sieht nach
  Widerspruch aus (ein neuer `entry_key` kann nicht dedupliziert werden) und kostete
  vier Checks. Auflösung: der Skill schreibt vor, dass **Nightly-Läufe still bleiben**,
  solange R3 PASS und die Abweichung <10 % ist — die Läufe vom 18.–22.08. haben also
  gearbeitet und den neuen Entry (`klickdummy:iilgmbh:risk-hub:grundschutz`, Erst-Commit
  2026-08-17 20:52, also nach dem 08-17-Lauf um 03:35 UTC) längst geschrieben, ohne hier
  eine Zeile zu hinterlassen. **Konsequenz:** Der Changelog ist ein Log der *manuellen/
  auffälligen* Läufe, nicht der Bestandsstand. Wer „written" gegen den letzten
  Changelog-Eintrag prüft, misst gegen eine bis zu mehrere Läufe alte Basis. Richtige
  Referenz ist der letzte Report-Block in `~/logs/klickdummy-pgvector-sync.log`.
  Nebenbefund derselben Spur: eine Spec-Änderung, die nur Felder betrifft, die der
  Producer nicht in den `content` rendert (hier `off_ramp_status` → `parity-green`,
  risk-hub #610), erzeugt korrekt **kein** `written` — die Versions-History im Entry
  bewegt sich trotzdem, weil sie aus der Git-History kommt.
- 2026-08-23 **E3-Altlast jetzt getrackt: [iilgmbh/risk-hub#667](https://github.com/iilgmbh/risk-hub/issues/667).**
  Der Lauf vom 2026-08-22 hatte notiert, dass `meiki-lra/frist-hub`-Einträge im Store
  liegen, obwohl das Repo gov-ausgeschlossen ist — ohne Tracking-Artefakt. Lesend
  bestätigt: mindestens 7 `klickdummy-iter:meiki-lra:frist-hub:*`-Entries, `agent=
  klickdummy-sync`, Tag `klickdummy:org:meiki-lra`; Inhalt sind KD-Iterationsprotokolle
  und ADR-Texte (LRA-Verfahrenslogik), **keine** personenbezogenen Daten. Die
  Gesamtzahl bleibt unbelegt — die semantische Suche kann keine Vollständigkeit zeigen,
  und einen Lösch- oder Filter-Pfad gibt es über die MCP-Tools nicht (nur `upsert`/
  `search`). **Lehre für den Skill selbst:** ein Befund im stillen Nightly-Report ist
  faktisch unsichtbar — Gov-/Datensouveränitäts-Funde müssen den Still-Modus
  durchbrechen und sofort ein Issue bekommen, sonst liegen sie tagelang nur im Log.
