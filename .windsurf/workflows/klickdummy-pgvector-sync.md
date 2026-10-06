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

Repo-Liste **aus dem Dateisystem**, nicht aus einer gepflegten Liste (die war dreimal
veraltet: #1263, #1495, #1571). Der Gov-Ausschluss steht als Filter im Befehl:

```bash
REPOS=$(ls -d "$GITHUB_DIR"/*/klickdummy | xargs -n1 dirname | xargs -n1 basename \
  | grep -vxE 'ttz-hub|meiki-hub|frist-hub' | paste -sd,)
echo "$REPOS"   # merken: N_repos — neue Gov-Repos hier in den grep aufnehmen
```

## Step 2 — NDJSON erzeugen

```bash
VENV=$GITHUB_DIR/risk-hub/.venv-klickdummy
OUT=$(mktemp --suffix=.ndjson)
$VENV/bin/klickdummy-sync --cross-repo --base "$GITHUB_DIR" \
  --repos "$REPOS" --output "$OUT"
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
- ❌ `written: true` als Fidelity-Verlust lesen und den Entry „korrigieren". Eine kleine,
  stabile Menge von Entries hat einen klemmenden leeren `content_hash` (Embedding-Fehler,
  `store.py:110-128`) und meldet **immer** `written: true`, auch wenn eine Maschine die
  exakten Quell-Bytes schickt. Jede „Korrektur" schreibt den Entry neu und garantiert den
  Befund für die Folgenacht — so entstand die Fidelity-Reihe 05.–14.09. Einziger gültiger
  Beleg ist der Byte-Vergleich (`klickdummy_pgvector_bytecheck.py`, kein LLM im Pfad).
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
- 2026-08-23 **Falsifiziert — der nächtliche Lauf fiel NICHT aus.** Dieser Eintrag
  entstand im Lauf vom 2026-08-23 03:17 selbst; er hielt sich für einen manuellen
  Ersatzlauf, weil `~/logs/klickdummy-pgvector-sync.log` beim Hineinschauen nur bis zum
  `2026-08-22`-Block reichte. Dagegen: der Cron-Eintrag (`17 3 * * *`) existiert, `cron`
  ist `active`, der Host lief durch (uptime seit 2026-05-07), und Log-Datei wie
  Changelog-Datei tragen dieselbe mtime `03:32:16` — beide wurden von **einem** Prozess
  geschrieben. Der Log-Tail ist der Report dieses Laufs, inklusive der Fehlmeldung selbst.
  **Root Cause der Fehldiagnose:** ein Cron-Job, dessen stdout per `>>` in genau die Datei
  läuft, die er prüfen will, sieht darin nie sich selbst — seine Ausgabe erscheint erst
  beim Prozessende. Diese Selbstprüfung ist strukturell blind, nicht gelegentlich falsch.
  **Konsequenz:** „Log endet auf gestern“ ist von innen **kein** Ausfall-Beleg. Billigster
  echter Check: `stat -c %y` auf die Log-Datei bzw. `systemctl is-active cron`.
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
- 2026-08-31: **Manueller Lauf (Session risk-hub) + Repo-Liste `+cad-hub`.** 171 Entries/
  25 Repos, R3 PASS (171/171 `ok`, 0 failed; **0 written**, alles content_hash-Dedup —
  deckungsgleich mit dem Cron-Lauf 2026-08-30, damit selbstverifizierend). Producer
  `iil-klickdummy 1.35.0`; 171 Zeilen = 171 unique `entry_key` (kein Duplikat). cad-hub
  (Org `achimdehnert`, kein Gov-Marker → syncbar, 2 Entries) stand seit dem 30.08. im
  Cron-Lauf, fehlte aber in dieser Quelldatei — nachgezogen, schließt
  [achimdehnert/platform#2357](https://github.com/achimdehnert/platform/issues/2357).
  frist-hub (meiki-lra) und ttz-hub (ttz-lif) bleiben gov-ausgeschlossen (E3) →
  Discovery 27 − 2 = 25. Schema-WARNs 177, unverändert und alle getrackt: pg-hub 110
  (bahn-sqf/pg-hub#8), design-hub 36 (design-hub#36/#38), nl2iot-hub 31 (nl2iot-hub#5).
  Offen bleiben aus dem 30.08.-Report: Cron-Env/Step-3-Wartelimit
  ([platform#2462](https://github.com/achimdehnert/platform/issues/2462)),
  Gov-Issue-Dubletten (risk-hub#583/#666/#667) und die K1-Entscheidung
  ([risk-hub#717](https://github.com/iilgmbh/risk-hub/issues/717), Frist 2026-08-31).
- 2026-09-05: **Manueller Lauf (Session risk-hub).** 172 Entries/25 Repos, R3 PASS
  (172/172 `ok`, 0 failed). 171→172 durch `klickdummy:achimdehnert:design-hub:sitemap`
  (Spec seit 2026-09-04 10:28, nach dem Cron-Lauf 03:31). Producer `iil-klickdummy
  1.35.0`; 172 Zeilen = 172 unique `entry_key`. Discovery jetzt 28 Repos mit
  `klickdummy/`: **meiki-hub (meiki-lra) neu dabei → gov-ausgeschlossen (E3)**, wie
  frist-hub und ttz-hub → 28 − 3 = 25, Liste unverändert. Schema-WARNs 177, alle
  getrackt (pg-hub#8, design-hub#36/#38, nl2iot-hub#5).
  **`written: true` = 6, davon 4 Falsch-Positive.** Legitim: design-hub:sitemap (neu)
  und 137-hub:sitemap (Commit 7542675 in der Versions-History). Falsch: sqf-hub:ADR-003,
  design-hub:ADR-007, #2, #3 — Quelle unverändert, Store-Tail nach dem Subagenten-Upsert
  `\n` statt `\n\n`. Damit ist das Anti-Pattern vom 2026-08-13 reproduziert und schärfer
  gefasst: 4 der 6 `\n\n`-Entries waren betroffen, die anderen 2 liefen bei zwei anderen
  Subagenten sauber durch — der Verlust hängt am **einzelnen Worker**, nicht am Entry.
  Korrektur inline mit exaktem Content (4× `written: true`), danach lesend verifiziert
  (Tails byte-genau). Beleg als Kommentar an
  [platform#1733](https://github.com/achimdehnert/platform/issues/1733).
  **Konsequenz für Step 3/4:** bei Delegation ist jedes `written: true` ohne
  Quelländerung **vor** dem Report lesend gegenzuprüfen; die Referenz für „Quelle
  unverändert" ist `git log --since=<letzter Report>` über `klickdummy/` + `docs/adr/`
  des Repos, nicht der Changelog.
- 2026-09-06: **Nightly-Lauf (03:18 UTC) + NEUER BEFUND — der Cron-Pfad pullt die Repos
  nicht.** 18 der 25 Repos lagen hinter `origin/main`, 14 davon mit Diff in `klickdummy/`
  oder `docs/adr/` (risk-hub 18 Commits, tax-hub 12, trading-hub 11, billing-hub 10).
  Vor `git merge --ff-only`: 172 Entries; danach **176** — 4 neu (risk-hub
  `betroffenenrechte` + `ADR-066`, pg-hub `sitemap` + `ADR-005#2`), 6 geändert
  (risk-hub `art15-vorgang` + `ADR-064`, pg-hub `pocket-governance-db` + `ADR-005`,
  dms-hub `sitemap`, billing-hub `sitemap`). Die „0 written"-Reports der Vortage belegten
  also nur einen unbewegten lokalen Klon, nicht einen aktuellen Store. dev-hub ließ sich
  nicht fast-forwarden (9 dirty Dateien) → dessen 5 KD/ADR-Diffs bleiben stale. Getrackt:
  [platform#2865](https://github.com/achimdehnert/platform/issues/2865) (Step 0
  „fetch + ff-only, Nicht-ff-bare als stale melden"). R3 PASS: 176/176 `ok`, 0 failed,
  25 Repos, Producer `iil-klickdummy 1.35.0`, 176 unique `entry_key`, Schema-WARNs 177
  unverändert (pg-hub 110, design-hub 36, nl2iot-hub 31, alle getrackt). Discovery 28,
  frist-hub/meiki-hub/ttz-hub gov-ausgeschlossen (E3) → 25.
  **`written: true` = 11, davon 10 legitim** (die 4 neuen + 6 geänderten oben).
  Der elfte, `ausschreibungs-hub:ADR-005`, ist Fidelity-Verlust — **diesmal kein
  Trailing-Whitespace, sondern ein Anführungszeichen:** die Quelle schreibt
  `„…des Bieters"` (U+201E + ASCII `"`), der Sonnet-Worker normalisierte das Schlusszeichen
  zu U+201C. Konsequenz: nicht nur endständiger Whitespace, sondern jede Stelle, an der
  die Quelle „falsch aussieht", ist beim Durchreichen gefährdet — der Worker korrigiert
  still. Korrektur inline (`written: true`), lesend verifiziert (ASCII `"`, Tail `\n`).
  Die 7 `\n\n`-Entries wurden diesmal von vornherein inline geschrieben: 6× dedup,
  pg-hub:ADR-005 legitim `true`. Beleg als Kommentar an
  [platform#1733](https://github.com/achimdehnert/platform/issues/1733).
- 2026-09-07: **Nightly-Lauf (03:17 UTC), Step 0 erstmals gefahren.** fetch + ff-only
  über alle 25 Repos: 24 bereits auf `origin/main`, nur dev-hub weiter Nicht-ff
  (40 Commits hinter, 9 dirty Dateien, 5 KD/ADR-Diffs stale — platform#2865 offen).
  Quelländerung seit dem 06.09.-Report (`git log --since` über `klickdummy/` +
  `docs/adr/`, alle 25 Repos): **keine** ⇒ Erwartung 0 `written: true`. R3 PASS:
  176/176 `ok`, 0 failed, 25 Repos, Producer `iil-klickdummy 1.35.0`, 176 unique
  `entry_key`, Schema-WARNs 177 unverändert (pg-hub 110, design-hub 36, nl2iot-hub 31,
  alle getrackt). Discovery 28, frist-hub/meiki-hub/ttz-hub gov-ausgeschlossen (E3) → 25.
  **`written: true` = 1, davon 0 legitim — dritte Fidelity-Variante: Fett-Marker.**
  `ausschreibungs-hub:ADR-009` kam aus einem Sonnet-Worker mit 2027 statt 2035 Zeichen
  zurück: die vier `**` um die Phrasen `**„Angebot erstellen"**` und `**„Template
  erstellen → Dokument erstellen"**` fehlten; Anführungszeichen und Tail waren diesmal
  korrekt. Der Brief verbot die Quote-Normalisierung ausdrücklich — die Abweichung
  wanderte auf das nächste Merkmal derselben Stelle (05.09. Newline, 06.09. Glyph,
  07.09. Marker). **Lehre:** Prompt-Härtung schließt Varianten, nicht die Klasse;
  byte-genau ist nur Inline-Upsert oder ein Transport ohne LLM (platform#2462).
  Korrektur inline (`written: true`), lesend verifiziert. Die 7 `\n\n`-Entries von
  vornherein inline: 7× dedup. Beleg als Kommentar an
  [platform#1733](https://github.com/achimdehnert/platform/issues/1733).
- 2026-09-08: **Manueller Lauf (Session risk-hub), Step 0 gefahren.** fetch + ff-only
  über alle 25 Repos: 20 bereits auf `origin/main`, 4 fast-forwarded (travel-beat,
  writing-hub, weltenhub, pptx-hub — keiner davon mit Diff in `klickdummy/` oder
  `docs/adr/`), dev-hub weiter Nicht-ff (45 Commits hinter, 9 dirty Dateien,
  platform#2865 offen). Quelländerung seit dem 07.09.-Report (`git log --since`
  über `klickdummy/` + `docs/adr/`, alle 25 Repos): **keine** ⇒ Erwartung
  0 `written: true`. R3 PASS: 176/176 `ok`, 0 failed, 25 Repos, Producer
  `iil-klickdummy 1.35.0`, 176 Zeilen = 176 unique `entry_key`, Schema-WARNs 177
  unverändert (pg-hub 110, design-hub 36, nl2iot-hub 31, alle getrackt). Discovery 28,
  frist-hub/meiki-hub/ttz-hub gov-ausgeschlossen (E3) → 25. Keine Verteilungs-Drift
  (Quelle und verteilte Kopie unterscheiden sich nur im MANAGED-BY-Footer).
  **`written: true` = 0 — erster Lauf seit dem 04.09. ohne Fidelity-Verlust.**
  Geändert gegenüber den drei Vornächten: der Worker-Brief benannte die
  **Fehlerklasse** statt der drei Einzelvarianten („sieht im content etwas falsch
  aus — Typografie, Marker, Whitespace, Rechtschreibung —, ist es Absicht und wird
  unverändert reproduziert"), und die 7 `\n\n`-Entries liefen von vornherein inline.
  **Das ist ein Indiz, kein Beweis:** bei 0 Quelländerungen ist dieser Lauf der
  leichteste denkbare Fall, und ein einzelner sauberer Lauf falsifiziert die
  Fehlerklasse nicht. Die Entscheidung in platform#2462 (Transport ohne LLM) bleibt
  offen — der Upsert-Schema-Check dieses Laufs bestätigt sie: `agent_memory_upsert`
  nimmt nur `content` als String, es gibt keinen Datei- oder Hash-Parameter.
- 2026-09-08 **NEUER BEFUND — der Store lowercased ADR-Tags.** Der Producer emittiert
  `klickdummy:adr:ADR-009`, gespeichert ist `klickdummy:adr:adr-009` (lesend an
  `ausschreibungs-hub:ADR-009` und `risk-hub:ADR-065` verifiziert; drei Worker
  unabhängig gemeldet). Betrifft **nur** `tags` — `content`, `entry_key` und `title`
  kommen unverändert zurück. Konsequenz: ein case-sensitiver Tag-Filter auf
  `klickdummy:adr:ADR-*` findet **nie** einen Treffer und meldet das als leeres
  Ergebnis, nicht als Fehler — dasselbe Muster wie der unzuverlässige `agent`-Filter
  (Eintrag 2026-08-17, iil-klickdummy#221). Getrackt:
  [iilgmbh/iil-klickdummy#243](https://github.com/iilgmbh/iil-klickdummy/issues/243).
- 2026-09-08 **Beantwortet, damit es nicht jeder Lauf neu fragt: die Dedup ist
  content-basiert, nicht key-basiert.** Vier von sechs Workern hielten ihr eigenes
  `written: false` für mehrdeutig („könnte auch heißen, es wurde gar nichts
  geschrieben") und baten um einen Test. Der Beleg liegt bereits vor: am 05., 06.
  und 07.09. kamen genau die **korrumpierten** Entries unter **unverändertem**
  `entry_key` mit `written: true` zurück. Bei key-basierter Dedup wäre das unmöglich
  gewesen. `written: false` ist damit der Fidelity-Beleg, den Step 4 unterstellt —
  ein absichtlich verfälschender Probe-Upsert ist dafür **nicht** nötig und würde
  gegen das Anti-Pattern vom 2026-08-13 verstoßen (der Test überschreibt sein
  eigenes Prüfobjekt).
- 2026-09-11: **Nightly-Lauf (03:17 UTC), Step 0 gefahren.** fetch + ff-only über alle
  25 Repos: 24 bereits auf `origin/main`, writing-hub 4 Commits fast-forwarded (kein
  Diff in `klickdummy/` oder `docs/adr/`), dev-hub weiter Nicht-ff (47 Commits hinter,
  9 dirty Dateien, platform#2865 offen). Quelländerung seit dem 10.09.-Report
  (`git log --since` über `klickdummy/` + `docs/adr/`, alle 25 Repos): **keine** ⇒
  Erwartung 0 `written: true`. R3 PASS: 176/176 `ok`, 0 failed, 25 Repos, Producer
  `iil-klickdummy 1.35.0`, 176 Zeilen = 176 unique `entry_key`, Schema-WARNs 177
  unverändert (pg-hub 110, design-hub 36, nl2iot-hub 31, alle getrackt). Discovery 28,
  frist-hub/meiki-hub/ttz-hub gov-ausgeschlossen (E3) → 25. 6 Sonnet-Worker à 27–29
  Entries (Brief mit Fehlerklasse wie am 08.09.), die 7 `\n\n`-Entries inline: 7× dedup.
  **`written: true` = 1, davon 0 legitim — vierte Fidelity-Variante: Zeilenumbruch-
  Position.** `writing-hub:ADR-190` kam aus einem Worker mit gleicher Zeichenfolge,
  aber drei verschobenen Umbrüchen zurück — alle an der Anführungszeichen-Stelle
  `„Charaktere" und` / `„Welten"`: Quelle bricht nach `und`, nach `Weltenbau der`
  und nach `hinweg — ein`; der Worker brach jeweils ein Wort früher. Anführungs-
  zeichen, Marker und Tail waren korrekt. Damit ist die Reihe geschlossen: 05.09.
  Newline, 06.09. Glyph, 07.09. Marker, 11.09. Umbruch — **dieselbe Stelle** (das
  „falsch aussehende" `„…"`), viertes Merkmal. Korrektur inline (`written: true`),
  lesend verifiziert (Umbrüche und Tail byte-genau). Bestätigt platform#2462:
  der Brief mit Fehlerklasse (08.09., 10.09. sauber) hält nicht unter jedem Worker.
- 2026-09-11 **NEUER BEFUND — die Läufe vom 09.09. und 10.09. fehlen hier, und der
  10.09.-Lauf meldete einen Entwurf, den es nicht gibt.** Der Log-Block vom 10.09.
  trägt zweimal die Überschrift „manueller Lauf, Session risk-hub", Log-Datei-mtime
  03:34 — es war der Nightly-Lauf (Wiederholung der Fehldiagnose vom 23.08.). Sein
  Zug-Item [5] verwies per `file://` auf einen Entwurf im Worktree
  `…/2026-09-10-…-kd-sync-changelog-2026-09-10-033318`; der Worktree ist **leer**
  (0 Commits vor `origin/main`, sauberer Tree, keine 09-09/09-10-Zeile in der
  Datei). Der 09.09.-Nightly hinterließ gar keinen Eintrag. Ursache (Hypothese, mit
  Gegenprobe heute): der Cron-Aufruf erlaubt nur `Bash`/`ToolSearch`/`Read`/
  `upsert` — `Write`/`Edit` werden im `-p`-Modus abgelehnt, der Lauf meldete das
  aber als „Entwurf liegt bereit". Gegenprobe: dieser Eintrag wurde aus dem
  Nightly-Prozess selbst (Prozess-Ahnenkette `cron → sh → claude`) per Bash-Append
  geschrieben, committed und als PR eingereicht — der Weg existiert also. Die
  Report-Blöcke der beiden Läufe liegen in `~/logs/klickdummy-pgvector-sync.log`
  (Zeilen 1756 und 1806/1832): beide R3 PASS, 176/176, 0 written.
  **Konsequenz:** ein Nightly-Report, der ein Artefakt nennt, muss dessen Existenz
  im selben Lauf belegen (`git diff --stat` ≠ leer), sonst ist der Zug-Eintrag
  eine Behauptung ohne Objekt.
- 2026-09-12: **Nightly-Lauf (03:17 UTC), Step 0 gefahren.** fetch + ff-only über alle
  25 Repos: 24 bereits auf `origin/main`, writing-hub 1 Commit fast-forwarded (kein
  Diff in `klickdummy/` oder `docs/adr/`), dev-hub weiter Nicht-ff (48 Commits hinter,
  9 dirty Dateien, platform#2865 offen). Quelländerung seit dem 11.09.-Report
  (`git log --since` über `klickdummy/` + `docs/adr/`, alle 25 Repos): **keine** ⇒
  Erwartung 0 `written: true`. R3 PASS: 176/176 `ok`, 0 failed, 25 Repos, Producer
  `iil-klickdummy 1.35.0`, 176 Zeilen = 176 unique `entry_key`, Schema-WARNs 177
  unverändert (pg-hub 110, design-hub 36, nl2iot-hub 31, alle getrackt). Discovery 28,
  frist-hub/meiki-hub/ttz-hub gov-ausgeschlossen (E3) → 25. 6 Sonnet-Worker à 24–29
  Entries (Brief mit Fehlerklasse **und** explizitem Umbruch-Verbot), die 7
  `\n\n`-Entries inline: 7× dedup.
  **`written: true` = 1, davon 0 legitim — derselbe Entry wie am 11.09.**
  `writing-hub:ADR-190` kippte erneut aus einem Sonnet-Worker, obwohl der Brief
  die Umbruch-Variante diesmal ausdrücklich benannte. Zwei Läufe in Folge, zwei
  verschiedene Worker, dieselbe Stelle (`„Charaktere" und` / `„Welten"`): das ist
  eine **reproduzierbare Kipp-Stelle**, kein Worker-Zufall. Korrektur inline
  (`written: true`), lesend verifiziert (Umbrüche nach `und`/`der`/`ein`, U+201E +
  ASCII `"`, Tail `\n`). Beleg als Kommentar an
  [platform#1733](https://github.com/achimdehnert/platform/issues/1733).
  **Konsequenz für Step 3, bis platform#2462 entschieden ist:** bekannte
  Kipp-Entries (`writing-hub:ADR-190`, `ausschreibungs-hub:ADR-005`,
  `ausschreibungs-hub:ADR-009`) werden wie die `\n\n`-Fälle **fest inline**
  geschrieben, nicht mehr delegiert — die Liste wächst mit jedem neuen Fund.
  Betriebs-Nebenbefund: `git switch -c` im Haupt-Tree wird vom main-tree-guard
  (ADR-233) zurückgesetzt — der Changelog-Weg aus dem Nightly ist ausschließlich
  `repo-session start platform --task <slug>` + Worktree, wie am 11.09.
- 2026-09-13: **Nightly-Lauf (03:17 UTC), Step 0 gefahren.** fetch + ff-only über alle
  25 Repos: 24 bereits auf `origin/main`, writing-hub 1 Commit fast-forwarded
  (Vorlesungsfolien, kein Diff in `klickdummy/` oder `docs/adr/`), dev-hub weiter
  Nicht-ff (48 Commits hinter, 9 dirty Dateien, platform#2865 offen). Quelländerung
  seit dem 12.09.-Report (`git log --since` über `klickdummy/` + `docs/adr/`, alle 25
  Repos): **keine** ⇒ Erwartung 0 `written: true`. R3 PASS: 176/176 `ok`, 0 failed,
  25 Repos, Producer `iil-klickdummy 1.35.0`, 176 Zeilen = 176 unique `entry_key`,
  Schema-WARNs 177 unverändert (pg-hub 110, design-hub 36, nl2iot-hub 31, alle
  getrackt). Discovery 28, frist-hub/meiki-hub/ttz-hub gov-ausgeschlossen (E3) → 25.
  6 Sonnet-Worker à 27–28 Entries, 10 Entries inline (7 `\n\n` + 3 Kipp-Entries
  laut 12.09.).
  **`written: true` = 5, davon 0 legitim — und erstmals einer aus dem Inline-Pfad.**
  (a) `writing-hub:ADR-190` kam aus dem **Inline-Upsert** (Hauptmodell, kein Worker)
  mit `written: true` zurück; die Quelldatei wurde zuletzt 2026-07-06 geändert. Der
  Store-Stand vom 12.09. („Korrektur inline, lesend verifiziert") und der heutige
  Inline-Schrieb sind also verschieden — mindestens einer von beiden war nicht
  byte-genau, und welcher, ist nicht mehr feststellbar, weil der Sync-Schrieb sein
  eigenes Vergleichsobjekt überschreibt. Heutiger Store-Stand lesend gegen das NDJSON
  geprüft (Umbrüche nach `und`/`der`/`ein`, U+201E + ASCII `"`, Tail `\n`): keine
  Abweichung sichtbar. **Konsequenz:** „lesend verifiziert" ist eine Sichtprüfung,
  kein Byte-Vergleich. Die Lehre vom 07.09. („byte-genau ist nur Inline-Upsert") ist
  damit **relativiert** — inline ist besser, nicht sicher. Ein echter Vergleich braucht
  den `content_hash` im Search-Ergebnis oder einen Transport ohne LLM (platform#2462).
  (b) Worker 6 meldete selbst 4 Abweichungen, alle an der bekannten Kipp-Stelle
  `„…"`: `risk-hub:ADR-049` und `pptx-hub:ADR-004` (Schlusszeichen `"` → U+201C,
  Variante vom 06.09.), `writing-hub:ADR-184` (Leerzeichen vor `-Autoren-Loop`
  eingefügt), `writing-hub:ADR-197` (doppeltes Leerzeichen nach `„Research"`).
  Fünfte und sechste Variante: **eingefügtes bzw. verdoppeltes Leerzeichen**.
  Korrektur inline (4× `written: true`), lesend verifiziert. Feste Inline-Liste
  wächst von 3 auf 7: + `risk-hub:ADR-049`, `pptx-hub:ADR-004`, `writing-hub:ADR-184`,
  `writing-hub:ADR-197`. Beleg als Kommentar an
  [platform#1733](https://github.com/achimdehnert/platform/issues/1733).
- 2026-09-14: **Manueller Lauf (Session risk-hub), Step 0 gefahren.** fetch + ff-only über
  alle 25 Repos: 24 bereits auf `origin/main`, writing-hub 2 Commits fast-forwarded (kein
  Diff in `klickdummy/` oder `docs/adr/`), dev-hub weiter Nicht-ff (48 Commits hinter,
  9 dirty Dateien, platform#2865 offen). Quelländerung seit dem 13.09.-Report (`git log
  --since` über `klickdummy/` + `docs/adr/`, alle 25 Repos): **keine** ⇒ Erwartung
  0 `written: true`. R3 PASS: 176/176 `ok`, 0 failed, 25 Repos, Producer `iil-klickdummy
  1.35.0`, 176 Zeilen = 176 unique `entry_key`, Schema-WARNs 177 unverändert (pg-hub 110,
  design-hub 36, nl2iot-hub 31, alle getrackt). Discovery 28, frist-hub/meiki-hub/ttz-hub
  gov-ausgeschlossen (E3) → 25. 6 Sonnet-Worker à 27 Entries, 14 Entries inline
  (7 `\n\n` + 7 Kipp-Entries laut 13.09.).
  **`written: true` = 7, davon 0 legitim.**
  (a) **Die 5 Inline-Kipper sind exakt die 5 Entries, die am 13.09. inline korrigiert
  wurden** (`risk-hub:ADR-049`, `pptx-hub:ADR-004`, `writing-hub:ADR-184`/`190`/`197`);
  die 9 übrigen Inline-Entries (zuletzt vor dem 08.09. oder nie korrigiert) kamen als
  dedup zurück. 5 von 5 gegen 0 von 9 ist keine Zufallsverteilung: der Inline-Schrieb vom
  13.09. und der von heute liefern für dieselbe unveränderte Quelle verschiedene Bytes.
  Für `writing-hub:ADR-190` ist das der dritte Tag in Folge (12.→13.→14.09.). Sichtprüfung
  des heutigen Store-Stands an allen bekannten Kipp-Stellen (U+201E + ASCII `"`, Umbrüche
  nach `und`/`der`/`ein`, Ellipse `…`, Tail `\n`): keine Abweichung sichtbar — wie am
  13.09., wo das ebenfalls nichts bewies. **Konsequenz:** die „feste Inline-Liste"
  (12./13.09.) ist kein Fix, sondern verschiebt den Fehler vom Worker auf das Hauptmodell;
  jede Inline-„Korrektur" ist selbst der Kandidat für das nächste `written: true`, und
  ohne `content_hash` im Search-Ergebnis ist nicht entscheidbar, welcher von zwei Ständen
  der richtige ist. platform#2462 (Transport ohne LLM) ist damit der einzige verbleibende
  Weg, nicht eine Option.
  (b) Worker 2 meldete 2 Abweichungen selbst, per `diff` gegen den JSON-dekodierten Text
  belegt — **siebte und achte Variante:** `risk-hub:ADR-057` (Backticks um `hub` in
  `` `hub`-Screen-Badge `` verloren, dazu Großschreibung), `risk-hub:ADR-058`
  (`"Option A — additive"` → `additiv`, die englische Endung der Quelle „korrigiert").
  Beide an Stellen, die „falsch aussehen". Korrektur inline (2× `written: true`).
  Nebenbefund: Worker 3, 4 und 5 dekodierten das NDJSON per `python3 json.loads` in
  Einzeldateien statt manuell — 0 Abweichungen bei 81 Entries; Worker 2 (manuelles
  Decoding) 2 von 27. Ein Lauf, kein Beweis, aber der billigste nächste Hebel für den
  Worker-Brief.
  **Log-Befund:** `~/logs/klickdummy-pgvector-sync.log` trägt für 12.09. und 13.09.
  **keinen** Report-Block, nur je eine Abschlusszeile („warte auf Merge-Status von
  PR #3114") — der Changelog hat beide Läufe, das Log nicht. Die Referenz-Regel vom
  23.08. („richtige Referenz ist der letzte Report-Block im Log") lief damit an zwei
  Tagen leer; heute wurde gegen den Changelog gemessen. Beleg als Kommentar an
  [platform#1733](https://github.com/achimdehnert/platform/issues/1733).
- 2026-09-15: **Nightly-Lauf (03:17 UTC), Step 0 gefahren.** fetch + ff-only über alle
  25 Repos: 21 bereits auf `origin/main`, 4 fast-forwarded (risk-hub 2, ausschreibungs-hub 2,
  illustration-hub 1, writing-hub 26 Commits — keiner mit Diff in `klickdummy/` oder
  `docs/adr/`), dev-hub weiter Nicht-ff (50 Commits hinter, 9 dirty Dateien, platform#2865
  offen). Quelländerung seit dem 14.09.-Report (`git log --since` über `klickdummy/` +
  `docs/adr/`, alle 25 Repos): **keine** ⇒ Erwartung 0 `written: true`. R3 PASS: 176/176
  `ok`, 0 failed, 25 Repos, Producer `iil-klickdummy 1.35.0`, 176 Zeilen = 176 unique
  `entry_key`, Schema-WARNs 177 unverändert (pg-hub 110, design-hub 36, nl2iot-hub 31, alle
  getrackt). Discovery 28, frist-hub/meiki-hub/ttz-hub gov-ausgeschlossen (E3) → 25.
  14 Entries inline (7 `\n\n` + 7 Kipp-Liste laut 13./14.09.), 162 an 6 Worker à 27.
  **Worker-Befund — 5 von 6 Sonnet-Workern vom Modell-Safeguard abgebrochen** (`[cyber]`,
  jeweils vor dem ersten Upsert; Worker 2 lief durch: 27× dedup). Neustart der fünf mit
  `model: opus`, identischer Brief: 135 Entries, 133× dedup, 2× `written: true` (s. u.).
  Vermutlich lösen die ADR-Inhalte selbst aus (Token, HMAC, Kill-Switch, Prod-Guards) —
  nicht geprüft. Konsequenz: Sonnet ist für diesen Skill als Worker-Tier nicht verlässlich;
  Delegation ab sofort mit `model: opus`.
  **`written: true` = 7 — und erstmals ist entscheidbar, welcher Stand richtig ist: der
  heutige.** Die 7 sind exakt die 7 am 14.09. inline „korrigierten" Entries (Inline-Pfad:
  `risk-hub:ADR-049`, `writing-hub:ADR-184/190/197`, `pptx-hub:ADR-004`; Opus-Worker:
  `risk-hub:ADR-057/058`), 0 von 169 übrigen. **Byte-Vergleich ohne Sprachmodell:** der
  Orchestrator-MCP ist per Streamable-HTTP direkt aus Bash erreichbar (Key aus
  `~/.claude.json`; Cloudflare antwortet mit Error 1010 auf den urllib-User-Agent — UA
  setzen genügt), `agent_memory_search` liefert `content` vollständig, `==` gegen die
  NDJSON-Zeile. Ergebnis: **alle 7 heutigen Schreibstände byte-gleich mit der Quelle**,
  insgesamt 87/176 verifiziert (76 `decision` + 11 `repo_context`). Damit waren die
  Inline-Korrekturen vom 13./14.09. die fehlerhaften Stände, nicht die Worker-Stände, die
  sie ersetzten — die „feste Inline-Liste" (12./13.09.) hat den Fehler täglich neu erzeugt
  und ist **aufgehoben**. Neue Regel für Step 3/4: kein Entry mehr fest inline; Worker mit
  `model: opus`; jedes `written: true` und die 7 `\n\n`-Entries danach per
  `platform/tools/klickdummy_pgvector_bytecheck.py <ndjson> <keys…>` byte-prüfen statt
  lesend zu sichten. Beleg: platform#1733; Vorschlag für den Schreibpfad ohne LLM
  (derselbe HTTP-Weg trägt `agent_memory_upsert`): platform#2462.
  **NEUER BEFUND — 89 der 100 `repo_context`-Entries sind für die Suche unsichtbar.**
  Auffindbar sind nur die 11 seit ~17.08. geschriebenen oder geänderten Specs; `sitemap`
  mit `limit=50` liefert 5 von 24. Code-gestützte Hypothese (mcp-hub
  `orchestrator_mcp/memory/`): `HALF_LIFE_DEFAULTS["repo_context"] = 7` Tage, `gc()`
  setzt `is_active = FALSE` bei Decay < 0,05 (≈ 30 Tage), die Suche filtert
  `is_active = TRUE`, und der Upsert-Dedup-Zweig setzt `is_active` nicht zurück — der
  Sync bestätigt die 89 seit Wochen mit `written: false`, ohne sie zu reaktivieren.
  Store-seitig nicht verifiziert (billigster Check: `SELECT is_active, count(*) …
  WHERE id LIKE 'klickdummy:%'`). `decision` (180 Tage) ist nicht betroffen. Konsequenz
  für K1 (risk-hub#717): `/klickdummy-search` misst gegen 11 % des Bestands. Getrackt:
  [achimdehnert/mcp-hub#273](https://github.com/achimdehnert/mcp-hub/issues/273).
  Nebenbefund: jede Suche antwortet `search_mode: fulltext` (Embedding-Fallback), obwohl
  `session_stats` 1151 OpenAI-Embeddings zählt — Ursache nicht geprüft.
  **Betriebs-Nebenbefund:** dieser Lauf hielt sich bis 03:39 UTC für eine manuelle Session
  („Log endet auf 14.09."), obwohl er selbst der Cron-Prozess war (`cron → sh → claude -p`
  seit 03:17:01) — dritte Wiederholung der Fehldiagnose vom 23.08./11.09. `date -u` gegen
  den Cron-Zeitpunkt gehört an den Anfang von Step 0, nicht ans Ende.
- 2026-09-16: **Nightly-Lauf (03:17 UTC), Step 0 gefahren.** fetch + ff-only über alle
  25 Repos: 24 bereits auf `origin/main`, dev-hub weiter Nicht-ff (50 Commits hinter,
  9 dirty Dateien, 5 KD/ADR-Diffs stale — platform#2865 offen). Quelländerung seit dem
  15.09.-Report (`git log --since` über `klickdummy/` + `docs/adr/`, alle 25 Repos):
  **keine**. R3 PASS: 176/176 `ok`, 0 failed, 25 Repos, Producer `iil-klickdummy 1.35.0`,
  176 Zeilen = 176 unique `entry_key`, Schema-WARNs 177 unverändert (pg-hub 110,
  design-hub 36, nl2iot-hub 31, alle getrackt). Discovery 28,
  frist-hub/meiki-hub/ttz-hub gov-ausgeschlossen (E3) → 25.
- 2026-09-16 **FALSIFIZIERT — `written: true` ist kein Fidelity-Signal. Die Fidelity-Reihe
  vom 05.–14.09. hat fünf Nächte lang ein Phantom gejagt.** Dieser Lauf schrieb alle 176
  Entries **ohne LLM im Pfad** (Python liest die NDJSON-Zeile und schickt sie per
  Streamable-HTTP an dasselbe `agent_memory_upsert` — der Schreibweg, den der Byte-Check
  vom 15.09. schon lesend nutzt). Ergebnis: `written: true` = 7, und es sind **exakt** die
  7 Entries der „festen Inline-Liste" vom 13./14.09. (`risk-hub:ADR-049/057/058`,
  `writing-hub:ADR-184/190/197`, `pptx-hub:ADR-004`). Eine Maschine, die garantiert die
  Quell-Bytes sendet, erzeugt dieselben 7 — die Ursache kann also nicht Transkription sein.
  **Gegenprobe:** `writing-hub:ADR-190` sechsmal hintereinander identisch gesendet →
  6× `written: true`, Store-Content durchgehend `len 4100`, byte-gleich zur Quelle.
  Tag-Schreibweise (`ADR-190` vs. `adr-190`) als Ursache ausgeschlossen (Kreuztest
  gross/klein, beide Richtungen, alle `true`). Stichprobe 6 `decision` + 6 `repo_context`:
  die übrigen 10 deduplizieren sauber (`false`) — betroffen ist eine **kleine, stabile
  Menge**, nicht ein Typ und nicht der Store insgesamt.
  **Mechanismus (Code gelesen, `mcp-hub/orchestrator_mcp/memory/store.py`):** Dedup ist
  rein content-basiert (`new_hash = sha256(content)`, Zeile 181/195). Aber
  `_resolve_content_hash` (Zeile 110–128) persistiert einen **leeren** Hash, wenn der
  Embedding-Call endgültig scheitert — bewusst, als Selbstheilung gegen „dark" Entries.
  Ein Entry in diesem Zustand matcht nie wieder, wird bei jedem Lauf neu geschrieben, der
  Embedding-Versuch scheitert erneut, der Hash bleibt leer: **permanent `written: true`**.
  Passend dazu `session_stats`: `active_null_embeddings: 31`, `embedding_models` führt
  152 Entries unter `∅`; die Zähler bewegten sich durch 176 Upserts + ~20 Wiederholungen
  **nicht** (vorher = nachher), es entsteht also kein neues Embedding.
  **Damit kippt die Kette rückwirkend:** eine „Inline-Korrektur" schrieb den Entry neu,
  liess den Hash wieder leer und garantierte damit sein `written: true` in der nächsten
  Nacht. Genau das meldete der 14.09. als Beweis („5 von 5 Inline-Korrigierte kippen,
  0 von 9 übrigen") und las es als „der Inline-Schrieb liefert verschiedene Bytes".
  Die Korrelation war echt, die Kausalität umgekehrt: **das Korrigieren selbst erzeugte
  den Befund des Folgetags.** Die Schlussfolgerungen vom 12./13.09. (feste Inline-Liste)
  und vom 14.09. („inline ist auch nicht sicher") sind beide gegenstandslos.
  **Nicht falsifiziert ist die Worker-Drift selbst:** die am 06./07./14.09. gemeldeten
  Abweichungen waren mit `diff` und Zeichenzahl belegt (2027 vs. 2035 Zeichen, U+201C
  statt `"`) und vom Worker *vor* dem Upsert gefunden — reale Transkriptionsfehler. Nur
  ihr *Nachweis über `written: true`* war untauglich, und die Behauptung „X von Y
  Fidelity-Verluste" in den Reports vom 05., 11., 12., 13. und 15.09. ist damit
  unbelegt — dort wurde die stabile 7er-Menge gezählt, nicht Drift.
  **Store-Zustand belegt, vorher und nachher:** Byte-Vergleich über alle 176 Entries
  (`klickdummy_pgvector_bytecheck.py`, kein LLM) **vor** dem Upsert: 87 byte-gleich,
  **0 DIFF**, 89 nicht-auffindbar (die `repo_context`-Decay-Lücke, mcp-hub#273).
  **Nach** dem Upsert: identisch, Zeile für Zeile — auch die 7 mit `written: true`.
  Es lag also nie eine Korruption im Store, weder von gestern noch von heute.
  **Konsequenz für Step 3/4:** (a) `written: true` allein löst **keine** Korrektur mehr
  aus — Beleg ist ausschliesslich der Byte-Vergleich; (b) die feste Inline-Liste bleibt
  aufgehoben (15.09.) und darf nicht zurückkommen, sie war der Erzeuger des Musters;
  (c) der Schreibweg ohne LLM hat 176/176 `ok` bei 0 Transkriptionsrisiko geliefert —
  Beleg für platform#2462, das damit entscheidungsreif ist. Neu getrackt: der klemmende
  `content_hash` der 7 Entries (mcp-hub).
  **Abweichung vom Skill, offen deklariert:** Step 3 schreibt Delegation an Subagenten
  vor; dieser Lauf hat stattdessen den LLM-freien HTTP-Weg genommen. Grund: die
  Vorher-Messung zeigte den Store bereits als byte-korrekt, ein Worker-Pfad hätte nur
  Transkriptionsrisiko ohne Nutzen hinzugefügt. Werkzeug-Hinweis: der Byte-Check liegt
  noch **nicht** auf `main` — PR [#3188](https://github.com/achimdehnert/platform/pull/3188)
  ist offen und grün; der im 15.09.-Report genannte Pfad `platform/tools/…` existiert erst
  nach dessen Merge (Wiederholung des Artefakt-Musters vom 11.09., diesmal nur im Pfad).
