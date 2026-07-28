# Agent Handover — Session-Log (append-only)

**Zweck:** chronologischer Mitschrieb der Session-Stände. Jede Session hängt ihren
Block **unten** an. Bestehende Einträge werden **nie** geändert, umsortiert oder
gelöscht — auch nicht, wenn sie sich im Nachhinein als falsch erweisen; dann kommt
die Korrektur als **neuer** Eintrag darunter.

**Warum so streng:** Diese Datei trägt `merge=union` (siehe `.gitattributes`).
Bei konkurrierenden Änderungen nimmt git beide Seiten auf, statt einen Konflikt zu
melden — deshalb können zwei parallele Sessions gleichzeitig anhängen, ohne sich zu
blockieren. Diese Gutartigkeit hängt vollständig daran, dass nur angehängt wird:
wird eine bestehende Zeile geändert, mischt Union alte und neue Fassung stillschweigend
ineinander. Der CI-Check `handover-append-only` setzt das durch.

**Was hier NICHT hingehört:** die `## Prioritäten`-Tabelle und alles, was laufend
umgeschrieben wird. Das bleibt in [`AGENT_HANDOVER.md`](AGENT_HANDOVER.md), wo
Konflikte laut bleiben — `session-ende` Phase 0c schreibt dort ausdrücklich vor,
erledigte Zeilen zu entfernen und neu zu nummerieren.

**Gemessene Grundlage (2026-07-22):** GitHub wendet `merge=union` serverseitig
**nicht** an — ein zweiter PR bleibt `CONFLICTING`, auch „Update branch" hilft nicht.
Der Nutzen liegt allein in der *lokalen* Auflösung: `git pull` im Worktree führt beide
Stände still zusammen, danach genügt ein Push. Aus „von Hand auflösen" wird „pullen
und pushen" — mehr verspricht dieser Arm nicht (Beleg: Kommentar an PR #1319).

**Kosmetische Nebenwirkung, kein Fehler:** Beim Zusammenführen zweier paralleler
Anhänge kann die Leerzeile zwischen den Blöcken wegfallen (gemessen 2026-07-22) —
die Einträge selbst bleiben vollständig und in Reihenfolge. Nicht nachträglich
„aufräumen": das wäre eine Änderung an bestehenden Zeilen und damit genau der Bruch,
den der Check verhindert.

**Ältere Stände:** [`AGENT_HANDOVER.md`](AGENT_HANDOVER.md) (aktueller + vorheriger
Stand) und [`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md) (alles davor).
Dieser Log beginnt bewusst leer statt mit einer Migration: bestehende Blöcke zu
verschieben wäre selbst genau die Art Umschreibung, die hier verboten ist.

---

<!-- Neue Einträge ab hier anhängen. Format:

## <YYYY-MM-DD HH:MM> — <Session-Kürzel> — <Ein-Zeilen-Thema>

- was erledigt wurde (PR/Issue verlinkt)
- was offen bleibt
- was NICHT verifiziert ist

Nichts oberhalb dieser Zeile anfassen. -->

## 2026-07-24 06:51 — adr285-konz-hygiene — Handover-Prios + ADR-285 Lane-Konsolidierung + KONZ-Hygiene

**Erledigt (alles gemergt/geschlossen):**
- #1378 hooks-lane regeneriert (DRIFT 0), `handover_prio_mirror`-Fix live, closed.
- #1399 gemergt (BITV `--pui-warning-text` + ADR-049-Nachtrag).
- #1117 stale-closed (trading-hub-Ruleset `ci/gate` existierte längst; 404 = Legacy-Endpoint).
- **ADR-285** (proposed) gemergt (#1409) = Phase 0 für #1287: D1 eine Lane (fest), D2 Richtung `skills` pilot-gegatet, D4 windsurf-review-Sub-Lane einstellen, D5 `commands`-Rückbau gegatet. Supersedes ADR-229, amends ADR-230 REC-3.
- #1410 gemergt: 4 KONZ-Kollisionen (001/009/014/019) aufgelöst + KONZ-007 Checkliste + `sunset`.
- #1406/#1407 gemergt (upload-artifact v7, setup-python v7).
- #1413 gemergt: `konz-guard.yml` + `konz_number_check.py` (concept_id-Eindeutigkeit).
- #1167 Audit fertig + closed.

**Offen / getrackt:**
- **#1416 ADR-285 Phase-1-Pilot** (`teste-repo` `$ARGUMENTS` + `workflow-index` → `skills/`) — MUSS in frischer Session laufen (Skills laden bei Session-Start). Entscheidet ADR-285 `accepted` vs. Fallback B. Grounded-Finding: `model:`-Friktion aufgelöst (3× `distribute:false`), einziger Test ist `$ARGUMENTS→args`.
- #1414 `tools-tests.yml`: 402 ruff-Fehler, non-required (silent-red), nur bei `.py`-PRs sichtbar.

**Nicht verifiziert:** Pilot-`$ARGUMENTS`-Verhalten (das IST der Falsifikationstest).

**Prio-Table (AGENT_HANDOVER.md) bewusst nicht angefasst:** offene Parallel-Session-PR #1404 berührt die Datei — kein konkurrierender Rewrite (0a-handover-pr). Erledigt aus der alten Prio-Liste: #1298 (war schon closed), #1378, #1117, #1167-Nebenfund (KONZ-Kollision). Nächste reconcilende Session zieht die Prio-Tabelle nach.

## 2026-07-25 11:45 — session-ende-2026-07-25 — Retire `_ci-python`/`_ci-odoo`, Handover-Prio reconcilt, PR-Stau 9→3

**Erledigt (alles gemergt):**
- [#1436](https://github.com/achimdehnert/platform/pull/1436) Handover-Prio reconcilt — #1117 raus (war seit 24.07. CLOSED und stand trotzdem als Prio 1 im Start-Hook), #1416/#1414 aus dem Log vom 24.07. in die Liste gezogen, Prod-Warnblock (#1303) per `free -m` **nachgemessen** statt fortgeschrieben (Swap unverändert 4095/4095).
- [#1437](https://github.com/achimdehnert/platform/pull/1437) `_ci-python.yml` + `_ci-odoo.yml` retired → [#1423](https://github.com/achimdehnert/platform/issues/1423) CLOSED. `_ci-pypi.yml` (19 Consumer, ADR-226) unangetastet. Templates `docs/templates/ci.yml` + `deployment/workflows/ci.yml` auf `iilgmbh/shared-ci/..._ci-python.yml@v1.0.14` umgehängt, `validate-workflows.yml`-Job `test-ci` entfernt, `drift_check.py`-Meldungstext korrigiert.
- [#1418](https://github.com/achimdehnert/platform/pull/1418) + [#1408](https://github.com/achimdehnert/platform/pull/1408) rote Checks behoben — Ursache lag in keinem der beiden PRs, sie waren nur **vor** dem Ruff-Pin [#1425](https://github.com/achimdehnert/platform/pull/1425) abgezweigt. `gh pr update-branch` genügte.
- [#1404](https://github.com/achimdehnert/platform/pull/1404) + [#1401](https://github.com/achimdehnert/platform/pull/1401) Merge-Konflikte aufgelöst.
- [#1438](https://github.com/achimdehnert/platform/issues/1438) als Tracking für bewusst ausgelassene Restarbeit angelegt.

**Zwei Prämissen gekippt — das ist der eigentliche Ertrag:**
1. **„0 Consumer" (#1423)** wurde vor dem Löschen neu gemessen, weil dieselbe Behauptung dort schon einmal falsch war. Dabei zwei **eigene** Fehlläufe gefunden: `/users/<user>/repos` liefert nur öffentliche Repos (32 statt 48 — 16 private ungescannt, darunter ein echter `_ci-pypi`-Consumer; korrekt ist `/user/repos?affiliation=owner`), und Banner-Kommentare wurden als Consumer gezählt. Belastbarer Scan: 63 Repos, 33 privat, 0 Tree-Fails → `_ci-pypi` 19, `_ci-python`/`_ci-odoo` 0.
2. **„402 Ruff-Fehler Lint-Schuld" (#1414)** existiert nicht. Mit gepinntem `ruff 0.15.4` meldet `ruff check tools/ scripts/` „All checks passed!" — die Fehler kamen vollständig aus einer ungepinnten neueren Version. Übrig bleibt nur der Required-Entscheid.

**Offen / getrackt:**
- [#1416](https://github.com/achimdehnert/platform/issues/1416) ADR-285 Phase-1-Pilot — braucht frische Session (neue Prio 1).
- [#1414](https://github.com/achimdehnert/platform/issues/1414) Owner-Entscheid: Check required schalten? Vorbedingung „erst grün, dann required" ist erfüllt; Ruleset verlangt heute nur `guardian` + `gitleaks secret scan` (API-geprüft).
- [#1438](https://github.com/achimdehnert/platform/issues/1438) stale ADR-Evidenzpfade + veraltete Fremd-Repo-Banner + 2 tote `validate-workflows`-Jobs.

**Nicht verifiziert:** ob die 3 Fremd-Repos (learn-hub, weltenhub, ausschreibungs-hub) ihre veralteten Banner-Kommentare korrigieren — App-Repo-Scope, nicht von platform aus angefasst.

## 2026-07-25 12:10 — session-ende-2026-07-25 (Nachtrag) — ADR-285 Phase-1-Pilot gemessen, commands-Lane live regeneriert

**Erledigt:**
- **Falsifikationstest ADR-285 D2 bestanden.** `skills/issues-offen/SKILL.md` mit dem Marker `platform-TESTMARKER-4711` aufgerufen (String kommt nirgends im Repo vor) → Body kam an **beiden** `$ARGUMENTS`-Stellen substituiert zurück, Footer `source=skills/issues-offen/SKILL.md`. Body nur beobachtet, nicht ausgeführt. Kill-Kriterium ADR-285 §8 greift **nicht**. Artefakt: [#1441](https://github.com/achimdehnert/platform/pull/1441).
- **`commands`-Lane live regeneriert** (Owner-Freigabe, Staging vorher gezeigt): beide Lanes DRIFT 0, Backup `~/.claude/commands.bak`. Nebenwirkung mit echtem Wert: die live installierte `klickdummy-pgvector-sync`-Kopie kannte `frist-hub` (meiki-lra) **nicht** als Gov-Ausschluss — jetzt korrigiert.

**Drei Befunde gegen die Anlage von [#1416](https://github.com/achimdehnert/platform/issues/1416):**
1. `teste-repo` — dort als „eigentlicher `$ARGUMENTS`-Fall" benannt — enthält **kein literales `$ARGUMENTS`** (nur Prosa). Der echte Testgegenstand `issues-offen` war bereits migriert und live: der Pilot war faktisch gelaufen, nur nie gemessen.
2. `workflow-index` lässt sich nicht ohne Fix an `check_workflow_index.py` migrieren. Getestet statt gelesen: simulierte Lane → `exit 1`, Gegenprobe Ist-Zustand → `exit 0`. Zwei Ursachen: Lane 2 fehlt der Selbst-Skip (`if name == index_name`), den Lane 1 hat; und der `--index`-Default zeigt auf `.windsurf/workflows/workflow-index.md`, während CI ohne Argumente aufruft.
3. §9-Kriterium 2 war rot durch eine stale Kopie von `klickdummy-pgvector-sync.md` (Nachlauf des #1408-Merges), nicht durch den Pilot.

**Methoden-Notiz:** `diff -rq` meldete alle 51 commands-Dateien als verschieden, `doctor.py` nur eine. `doctor.py` hatte recht — 50 unterscheiden sich ausschließlich im Footer-Feld `source_commit` bei identischem `content_hash`. Das grobe Werkzeug hätte fast zu einer falschen Aussage über den Änderungsumfang geführt.

**Offen:** Der **CLI-Pfad** der Argument-Übergabe ist nicht gemessen (nur der programmatische). Einmal `/issues-offen platform-TESTMARKER-4711` tippen schließt §9-Kriterium 1; danach Acceptance-PR + D5-Prozedur.

---

## 2026-07-26 — ADR-Sync repariert (4 Defekte), 2 Ausführungs-Gates gebaut, DSB-Partner-Konzept

**Kern:** Die Prio-1-Aufgabe (#1447, ADR-Sync 401) war als „Token abgelaufen" beschrieben und
brauchte vier Fixes. Der Ertrag steckt weniger im Ergebnis als in vier Stellen, an denen eine
plausible Annahme falsch war — jede davon hätte den Tag beendet, wenn sie ungeprüft geblieben wäre.

**1. Der Fallback war doppelt kaputt, nicht einmal.** Er signierte `{}`, sendete aber den vollen
Payload (HMAC über `request.body` → `401 Invalid signature`), und selbst mit gültiger Signatur
hätte er nur einen Celery-Task angestoßen, der denselben abgelehnten Token liest. Belegt auf drei
Ebenen: Code, Log (`Webhook fallback also failed`), Zustand (`max(updated_at)` vier Tage still).

**2. `docker restart` wirkt nicht auf `env_file`.** Nach dem Token-Tausch zeigten alle acht Repos
weiter 401. Die Container-Umgebung steht seit der *Erstellung* fest. Hash-Vergleich Datei
`6a0152e4` gegen Container `d7b49e5d` machte es eindeutig; erst `compose up -d --force-recreate`
mit der aus den Container-Labels (`com.docker.compose.project.config_files`) gelesenen `-f`-Kette
hat beide angeglichen. Die Kette wurde gelesen, nicht geraten — `--remove-orphans` bewusst weg.

**3. Die beiden GitHub-Hosts melden abgelehnte Credentials unterschiedlich.** `api.github.com`
antwortet 401, `raw.githubusercontent.com` antwortet **404**. Der erste Fix fing nur 401 ab,
reparierte damit die Dateiliste und ließ jeden Download auflaufen — aufgefallen erst im Echt-Lauf
auf Prod, nicht im Test. Verifikations-Query und Implementierungs-Query waren identisch, genau der
Zirkel, vor dem die Evidenz-Policy warnt.

**4. httpx folgt Redirects per Voreinstellung nicht.** Ein `301` passiert `raise_for_status()`
klaglos. Aufgefallen an einem 301 im Token-Scan des Owners: `achimdehnert/risk-hub` liegt
inzwischen unter `iilgmbh/risk-hub`. Zwei gültige Token wurden dadurch fälschlich als untauglich
gemeldet — der Fehler lag im Prüfwerkzeug, nicht in den Token.

**Selbst verursachter Schaden, benannt.** Der erste erfolgreiche Voll-Import ließ `platform` von
241 auf 202 Zeilen fallen: `unique_together = (tenant_id, adr_id)` plus ein `update_or_create`
ohne `source_repo` im Lookup — jedes Repo hat seine eigene ADR-001. Der Fehler ist älter (vorher
7 verlorene Nummern), sichtbar wurde er durch den ersten vollständigen Import seit Tagen. Behoben
mit Migration und einem Regressionstest, dessen **Negativprobe** belegt, dass er die Regression
trifft (mit dem alten Lookup: 1 failed).

**Zwei Gates, weil Regeln allein nicht gebunden haben.** Drei Fehlerklassen dieses Tages waren
durch bestehende Memories abgedeckt und passierten trotzdem: stale Klon als Lesebasis, Org-Hardcode
ohne Redirect, ungetestete Handover-Befehle. Statt einer vierten Formulierung nun ein Stop-Hook
(Befehlsblock ohne eigenen Lauf im selben Turn / Platzhalter wie `<TOKEN>`) und ein
SessionStart-Hook (Klon-Rückstand mit Nennung des neuesten Commits). Beide mit Positiv- und
Negativprobe getestet, verteilt und live verdrahtet.

**Methoden-Fehlschlag, dokumentiert:** eine Messung über 311 Repos meldete „0 abrechenbare
Actions-Minuten" bei 0 API-Fehlern. Die Gegenprobe an einem einzelnen Lauf kippte sie sofort — der
Timing-Endpunkt meldet `duration_ms: 0` für Jobs, die nachweislich liefen. Ein sauberer Durchlauf
ohne Fehler fühlt sich wie Evidenz an und ist keine. Lehre als Memory: erst einen Fall mit
bekannter Antwort kalibrieren, dann skalieren.

**Owner-Vorschlag DSB-Partner-Rolle** als T3-Konzept ausgearbeitet ([risk-hub#455](https://github.com/iilgmbh/risk-hub/pull/455)):
gestaffelte Freigabe (auswertend → entwerfend → publizierend), Datenzugriff als technische Regel
statt als Vorsatz, Kill-Gate mit Pilot-Zuschnitt. Root-Cause-Prüfung ergab, dass der Mechanismus
für „Dokumentation komplett" bereits existiert (`MandateDokuSection`, 8 Sektionen) — es fehlt die
Auswertung, nicht das Modell.


## 2026-07-26 Abend — ADR-Sync-Hygiene: Prune real gelaufen, 5 Nummern-Kollisionen, Sync-Lücke von 13 ADRs

**Erledigt (alles gemergt):**
- [dev-hub#159](https://github.com/achimdehnert/dev-hub/pull/159) `--prune` (opt-in) + laute Kollisions-Warnung. **Einmal real gelaufen:** 6 Waisen weg (`ADR-013/-014/-023/-033/-063/-2026`), `0 imported, 232 unchanged, 0 errors`; Backup aller 238 Zeilen inkl. Volltext als `/root/adr_platform_pre_prune_2026-07-26.json`. Gegenprobe über `git ls-tree` (nicht über die API, die der Importer selbst liest): 232 = 232.
- [dev-hub#164](https://github.com/achimdehnert/dev-hub/pull/164) erste maschinenlesbare Sync-Liste (`REPO_FULL_NAMES` / `ARCHIVED_REPO_SLUGS` / `ADR_SYNC_REPOS`), `bfagent` ausgeschlossen. Live im Container verifiziert.
- Kollisionen behoben: [risk-hub#456](https://github.com/iilgmbh/risk-hub/pull/456), [odoo-hub#17](https://github.com/achimdehnert/odoo-hub/pull/17), [pptx-hub#45](https://github.com/achimdehnert/pptx-hub/pull/45) + [#46](https://github.com/achimdehnert/pptx-hub/pull/46).
- [#1438](https://github.com/achimdehnert/platform/issues/1438) CLOSED — Banner-Korrekturen in learn-hub#29, weltenhub#44, ausschreibungs-hub#178, alle mit `[skip ci]` gemergt (drei Repos deployen ohne paths-Filter auf `push:main`).
- Nachimport: `odoo-hub` (12 ADRs), `dev-hub` (1), `mcp-hub` (1) standen **nie** im Sync. Bestand 318 → 331.

**Drei Prämissen gekippt — das ist der eigentliche Ertrag:**
1. **Der `--prune`-Vorschlag aus dem Ticket hätte zu viel gelöscht.** Ein reiner `source_path`-Präfixvergleich trifft auch `docs/adr/reviews/`, weil die Contents-API **nicht rekursiv** listet — diese Zeilen tauchen nie in der gesehenen Dateiliste auf und wären nur deshalb als Waisen gelöscht worden. Der Test dazu war vor dem Fix rot.
2. **Meine eigene Zuordnung „bfagent steht in `constants.py` als Sync-Repo" war falsch.** `PLATFORM_REPOS` treibt Concept-Scoping (`services.py:678`, `views.py:264/281/310`); der Importer liest die Liste nie. Ein Löschen des Eintrags hätte den Sync nicht berührt, dafür die Redundanz-Analyse verarmt. Korrektur steht im Issue, nicht nur im Chat.
3. **Bei pptx-hub hätte „längere Fassung behalten" die Abwägung gelöscht.** `-optimized` war **kein Superset**: `Alternatives Considered` stand nur im Entwurf — und fehlt laut `.reflex/baseline.json` genau dort. Beide Abschnitte wörtlich übernommen, maschinell gegen die Quelle verglichen (52 + 5 Zeilen identisch) statt abgetippt.

**Methoden-Notiz:** Die neue Kollisions-Warnung hat beim **allerersten** Einsatz gefunden, wonach niemand gesucht hatte (odoo-hub ADR-001). Der Abschluss-Abgleich über alle 10 Sync-Repos fand eine fünfte, nie bemerkte Kollision (pptx-hub ADR-002) — ein Abgleich, der erst am Ende lief, hätte sonst ein „fertig" getragen, das nicht stimmte.

**Stand am Ende:** 10/10 Sync-Repos stimmen in Dateien, eindeutigen Nummern und Zeilen exakt überein.

**Offen / nicht verifiziert:**
- Es gibt weiterhin **keinen Automatismus**, der `ADR_SYNC_REPOS` konsumiert — der Voll-Sync bleibt Handarbeit, die Liste ist nur die Grundlage.
- `bfagent` trägt 3 unbehebbare Kollisionen, solange es archiviert ist.
- Deploy-Wirkung: dev-hub deployte nach beiden Merges (grün, Konstanten im Container gegengelesen); die fünf Doku-Repos lösten bewusst keinen Deploy aus.

---

## 2026-07-27 — platform + risk-hub (`0c98c5`): Deckungsausweis gebaut, Klickdummy-Pin, deep-Retro

**Was entstanden ist.** KONZ-platform-035 „Deckungsausweis" angenommen (#1491) und sieben
von zehn Empfehlungen umgesetzt (#1492): versioniertes Objekt `deckungsausweis.v1`, zwei
verschiedenartige Retrievalpfade mit Divergenz-Meldung, Selbst-Kalibrierung, unabhängige
Zweitzählung des Nenners, Amendment an ADR-284 §2 Nr. 1 (Coverage-Contract gilt auch für
Live-Antworten). K6/K8 in #1493, Pilot- und Retro-Fixes in #1494 — beide offen.

**Referenzpostfach `search@dehnert.team`.** Owner-Vorschlag „anonymisierte Echt-Mails"
geprüft und verworfen (Anonymisieren = die systematische Inhaltsauswertung, die die DSFA
ausschließt). Stattdessen Struktur messen, Inhalt erfinden. Erster Lauf rot → echter
Fehler gefunden (`imaplib` kodiert nur ASCII, Umlaut-Suche brach still ab).

**risk-hub entblockt.** Klickdummy-Drift kam nicht vom Branch-Alter, sondern von einem
ungepinnten Generator; erste Diagnose war falsch und ist im Issue korrigiert. #460 und
#449 gemergt — `create_deletion_request` liegt in `main`.

**Deep-Retro:** 16 Befunde, 14 überleben. Vier davon sagen dasselbe — eine Statuszeile
behauptete mehr als das Artefakt hergibt. Ein destruktiver Löschpfad (`startswith` ohne
Trenner) wurde gefunden und behoben. Report unter `docs/retros/`.

**Nächste Schritte:** #1493 und #1494 freigeben · risk-hub#447 mergen (grün, approved,
liegt seit 23.07.) · K-Tabelle in KONZ-035 gegen die vier Pilotfehler nachziehen ·
Fleet-Wirkung des Klickdummy-Pins auf neun Repos tracken.
