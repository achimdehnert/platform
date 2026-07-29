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


## 2026-07-28 — Mail-Archivierung: Zuschnitt gelöst, zwei Postfächer sortiert, Retro deep

**Der Zuschnitt kippte zuerst.** Auf Owner-Weisung fiel der Datenschutz als Vorbehalt weg:
Personendaten und Termine sind erwünscht, weil sie Situationen aufklären; die Grenze ist der
**Zweck** (Situation verstehen vs. Menschen bewerten), nicht der Inhalt. Das ADR-286-Amendment
§4.10 ([#1498](https://github.com/achimdehnert/platform/pull/1498)) hebt den MEiKI-Sonderweg,
das Personenbezug-Verbot und die Nur-deterministisch-Regel auf und ersetzt drei starre
Klauseln durch einen Zwecktest. Bemerkenswert: Das ADR hatte die Inhaltsanalyse nie verboten
(§4.8 wörtlich) — die Bremse saß in der Anwendung, nicht im Dokument.

**28.158 Nachrichten umsortiert, in beiden Postfächern, alle Läufe gegengeprüft.** IIL: 22.599
aus einem flachen Archiv in Jahrgänge, 6.877 aus Gesendete Elemente in einen neu angelegten
Sent-Archiv-Baum, 11 Spam gelöscht. HNU: 649 aus dem Posteingang, 4.910 aus einem Sammelordner
in 11 neue Jahrgänge, 13 nachgezogen, Sammelordner nach Leer-Guard gelöscht. Jeder Lauf folgte
demselben Ablauf: Trockenlauf, Pilot auf dem kleinsten Jahrgang, Gegenprobe über einen
**unabhängigen** Codepfad, dann der Rest.

**Drei Werkzeuge entstanden**, alle mit Tests und alle noch ungemergt:
`indexierung.py` (Ausschlusskonfiguration, [#1501](https://github.com/achimdehnert/platform/pull/1501)),
`archiv_einsortieren.py` (Graph + IMAP, [#1502](https://github.com/achimdehnert/platform/pull/1502)),
`ablage_pruefung.py` (Prüfer, [#1504](https://github.com/achimdehnert/platform/pull/1504)).
Dazu ein Fix am Konten-Nenner des Deckungsausweises
([#1500](https://github.com/achimdehnert/platform/pull/1500)): Er zählte eine Routing-Tabelle
als Konto und übersah das IIL-Hauptpostfach mit 44.878 Nachrichten vollständig.

**Vier Fehler, die erst die Wirklichkeit zeigte** — alle mit Regressionstest verankert:
falsches Schlüsselwort im Schreibpfad (Abbruch beim 1. von 145) · zu kurzer Drossel-Backoff
(12.311 Falsch-Fehler) · Sortierung nach Ankunft statt Kopfzeile · elf vermeintliche
Fehlablagen waren Spam mit gefälschtem `Date`, eine davon auf 1988 datiert.

**Session-Retro (deep):** 20 Befunde, 19 überleben die Falsifikation. Pipeline: 1 Kollektor
+ 3 Finder + 3 Skeptiker + 1 Stichentscheid + 1 Meta-Reviewer. Der Stichentscheid war nötig,
weil zwei Skeptiker sich widersprachen — einer las den nie nacheditierten PR-Body, der andere
die Kommentare. Report: `docs/retros/session-retro-2026-07-28-platform-d5eb5e.md`.

**Nächste Schritte:** Merge-Reihenfolge #1494/#1500 entscheiden (echter, unsichtbarer
Konflikt) · fünf PRs reviewen, damit der Stapel abgebaut wird · Freigabe für die
§4.7/§4.9-Aufhebung als PR-Kommentar an #1498 nachtragen · #1506/#1507/#1508 abarbeiten.

**Nachtrag Wissenssicherung (2026-07-28):** Vier Outline-Dokumente angelegt — Runbook
(Postfach nach Jahrgängen sortieren, mit Tabelle der sechs bekannten Fehler), Konzept
(Zwecktest statt Verbotsliste, inkl. der verworfenen Alternativen und der funktionalen
Begründung für die Akteurs-Registry), zwei Lessons (Trockenlauf deckt den Schreibpfad
nicht ab · Ankunftsstempel ist nicht das Nachrichtendatum, mit vollständiger
Fallunterscheidung und dem Zeitzonen-Fallstrick). Querverweis im pgvector unter
`outline:platform:20260728-mail-archivierung`.

**Offen geblieben am Session-Ende:** Vier Repos sind dirty, alle belegbar **fremd** —
`django-lms-lite` und `iil-doc-templates` mit untracked `.windsurf/`-Verzeichnissen aus der
Verteilung, `lastwar-alliance-ops` mit einer geänderten Service-Datei aus einer parallelen
Session, `risk-hub` mit geändertem `NEXT.md` (war laut Session-Start-Runner schon um 04:22
als `GUARD(dirty)` markiert, also vor Sessionbeginn). Nach der Attributions-Regel liegen
gelassen, nicht eingesammelt. Die Checklisten-Zeile „kein Repo dirty" ist damit **nicht**
erfüllt und wird bewusst als offen geführt.

**Abschluss 2026-07-28 (nach den Merges):** Neun PRs auf `main` (#1493, #1494, #1496, #1498,
#1501, #1502, #1504, #1505, #1509), `main` von `e971840b` auf `ca4befc4`, 28 Commits.
#1500 geschlossen — überholt durch #1509, das die Ansätze von #1494 und #1500 zusammenführt;
Abdeckung gegen `origin/main` geprüft (Strukturfilter, `_env_schluessel`, `GRAPH_ACCOUNTS`,
`KEINE_KORRESPONDENZ`, drei neue Tests) statt behauptet. Verhalten gegen die echte
Konfiguration: `['hnu', 'graph:achim.dehnert@iil.gmbh']` — `default` fällt korrekt heraus.

Offen bleibt allein #1503: approved, keine roten Checks, trotzdem `BLOCKED`. Vermutlich ein
Required Check mit `paths`-Filter, der sich für einen reinen `docs/retros/`-PR nie meldet —
nicht verifiziert, weil der `gh api rulesets`-Aufruf vom Berechtigungs-Klassifikator
abgelehnt wurde.

Deploy-Pflichtprüfung: platform hat keinen Deploy auf `push:main`; die neun Merges lösten
keinen Prod-Schritt aus. Belegt über die Trigger der fünf `deploy-*`-Workflows, nicht
angenommen.

Sechs Worktrees aus Vorsessions (16./20./21./23.07.) bleiben stehen — ihre Branches sind
nicht gemergt, der Reaper schützt sie zu Recht. Wiederkehrendes Muster
`worktree-midsession-accumulation`, hier bewusst nicht angefasst.

---

## Session 2026-07-29 — platform (4df8a8): Paperless 3.0.4, Cloudflare Access, sevdesk-Bankpositionen

**Strang:** doc-hub/Paperless · Backup · Cloudflare Access · sevdesk. Vier PRs gemergt
(#1526, #1528, #1534, #1537), Retro als #1541 offen. Am selben Tag liefen mindestens zwei
weitere Sessions im Repo (18 Merges gesamt) — deren PRs gehören nicht hierher.

**Backup saniert (#1526).** Ursache war nicht Platzmangel, sondern ein doppelter Lauf: das
Cron-Skript (Zip, 427 MB) und dieselbe Repo-Fassung als `/etc/cron.daily/doc-hub-backup`
(unkomprimiert, 2,1 GB) schrieben in dasselbe Verzeichnis. Die 1-Tages-Aufbewahrung vom
April war Symptombehandlung. Jetzt 30 Tage; die Notbremse entfernt den ältesten Stand statt
aller; ein übersprungener Lauf endet mit exit 1 statt Erfolg zu melden. Rückspielprobe
gebaut und bestanden — Weg A 820/826 identisch zur Produktion, Weg B exit 0 mit 5278
Objekten. Der Importer braucht zwingend Redis; das kostete drei Anläufe.

**Paperless 2.14.7 → 2.20.15 → 3.0.4 (#1528),** 53 Migrationen, 826 Dokumente und 3857
Audit-Einträge unversehrt. 2.20.15 ist die zwingende Vorstufe. Zwei Consumer-Variablen
existieren in 3.0.4 nicht mehr und standen in keiner Checkliste — gegen den Quelltext des
Tags geprüft, nicht gegen Prosa.

**Cloudflare Access statt authentik für docs.iil.pet (#1528).** Header-Anmeldung nur
deshalb vertretbar, weil nginx die Seite ausschließlich auf `127.0.0.1:8999` für den
cloudflared-Tunnel bedient — vorher geprüft. Falsifikationstest: mit Kopfzeile HTTP 200 und
Sitzungs-Cookie, ohne 302 auf die Anmeldung. Passwort-Weg bewusst offen als Rückfalltür.
Der Anmeldeweg im Zero-Trust-Konto ist **GitHub**, nicht Einmal-PIN; die wirksame Adresse
ist `admin@wir-digital.de`.

**sevdesk-Bankpositionen (#1537):** 84 unverbuchte Umsätze 2026, Kontenzuordnung nach
Owner-Vorgaben — 76 zugeordnet, 8 in Klärung, 0 offen. Arbeitsstand als JSON eingefroren
(Umsatz-ID → Konto), weil das Board bei jedem Lauf neu aus der API entsteht und damit kein
verlässlicher Bezugspunkt für eine Freigabe wäre.

**⛔ GATE: Buchungen warten auf das Go des Owners.** Mara (`md@dehnert.team`) prüft die
Aufstellung und meldet sich bei ihm. Eingefrorener Stand unter
`~/.claude/boards/archiv/sevdesk-stand-2026-07-29.json`.

**Session-Retro (deep):** 9 Befunde, 7 überleben. Schärfster Befund — und er betrifft die
eigene Arbeit: `restore-test.sh` zeigt weiter auf Paperless 2.14, die Instanz läuft seit
demselben Tag auf 3.0.4. Der einzige verifizierte Rollback-Pfad ist damit für alle Backups
ab jetzt latent gebrochen. Die Version steht an vier Stellen im Repo und wird nirgends
abgeleitet. Zweitschärfster: die wörtlich erklärte ADR-142-Abweichung wurde nirgends
nachgezogen, das Frontmatter behauptet weiter erfolgreiches authentik-SSO für doc-hub.
Vier der sieben Überlebenden tragen bereits gate-pflichtige Slugs.

**Nächste Schritte:** #1541 reviewen · Rückspielprobe auf abgeleiteten Image-Tag umstellen ·
ADR-142 nachziehen oder als Issue eröffnen · Tests für `bankpositionen.py` und die
`/d/`-Route · #1527 (4,2 GB Altlast) und #1529 (totes GHCR-Token des Hosts) abarbeiten.

**Offen geblieben:** Drei Repos sind dirty, alle belegbar fremd — `django-lms-lite` und
`iil-doc-templates` mit untracked `.windsurf/`-Resten aus der Verteilung, `risk-hub` mit
geändertem `NEXT.md`, das schon beim Session-Start als `GUARD(dirty)` markiert war. Nach
der Attributions-Regel liegen gelassen. Die Checklisten-Zeile „kein Repo dirty" ist damit
nicht erfüllt und wird bewusst als offen geführt.
## Session 2026-07-28 Nachmittag (platform) — Handover-Prios 2+3 gebaut, zwei blinde Melder gefunden

**Fünf PRs geöffnet, alle CI-grün, alle `BLOCKED` (Ruleset: kein Self-Merge):** #1511
(Handover-Prio 4 gestrichen), #1512 (`--role` + Kanal-Grenze, schließt #1427/#1481), #1513
(Regel-Interpreter ADR-284 §7a), #1515 (Phase 0.7.2 Cron-Melder), #1517 (project-facts über
PR statt Direkt-Push). Drei neue Issues: #1514, #1516 — plus Kommentare an #1508.

**#1503 entblockt.** Die Hypothese des Vor-Handovers (`paths`-Filter) ist falsifiziert:
`guardian.yml` hat keinen, ist auf Head und `main` byte-identisch, und guardian lief am
selben Tag grün auf #1505 (ebenfalls reiner `docs/retros/`-PR). Für den alten Head gab es
**keinen einzigen** `pull_request`-Lauf; `reopened` löste nur `pull_request_target` aus.
Erst ein neuer Head-SHA per `git commit-tree` (fast-forward, kein force) brachte alle sechs
Läufe. PR ist CLEAN + approved; der Merge wurde vom Permission-Klassifikator abgelehnt und
liegt beim Owner. **Warum die Läufe ausblieben, ist ungeklärt.**

**Zwei eigene Fehler, beide vor dem Commit gefangen und in den PR-Texten benannt:** Der
Cron-Melder-Check holte die Läufe zuerst mit einem Sammel-Abruf — sah vollständig aus,
verdrängte aber die täglichen Workflows und fand 1 von 2 bekannten Meldern (dieselbe
Fehlerklasse wie `feedback_invented_wildcard_is_not_full_enumeration`). Und die erste
Verdrahtung in den Runner fiel still in den `*)`-Fallback, weil `$PLATFORM_DIR` auf den
Haupt-Tree zeigt; belegt erst über einen `GITHUB_DIR`-Symlink auf den Worktree.

**Korrektur einer eigenen Zahl:** „`Gen project-facts.md` seit 15.06. ohne Regenerierung"
war falsch. Der letzte über *alle* Repos grüne Lauf war der **08.06.**; danach wurde weiter
verteilt, nur an immer weniger Repos (06-15: 14 ok/5 Fehler · 07-06: 9/11 · 07-27: 0/18).
Ursache der Fehlzahl: der neue Check zählt nur `event=schedule` und übersah einen
erfolgreichen `workflow_dispatch` am 29.06. Im Issue korrigiert.

**Offen und ausdrücklich zur Freigabe gestellt:** der scharfe Einzel-Lauf zu #1517
(`workflow_dispatch` mit `target_repo`), der den Schreibpfad im Zielsystem belegen würde.
Nicht selbst ausgeführt — Schreibzugriff auf ein zweites Repo.

**Dirty geblieben (fremd):** `django-lms-lite`, `iil-doc-templates`, `lastwar-alliance-ops`,
`risk-hub` — unverändert gegenüber dem Vormittag, keine davon in dieser Session angefasst.
Die Checklisten-Zeile „kein Repo dirty" ist damit bewusst nicht erfüllt.

**Nachtrag am Session-Ende (2026-07-28, nach der Wissenssicherung):** Die Ursache für
#1503 ist gefunden und ersetzt das vorherige „ungeklärt". Es ist **`[skip ci]` in der
Commit-Message des Head-Commits** — GitHub überspringt damit alle Workflow-Läufe des
Pushes, auch das `pull_request`-Event; der Required Check meldet sich nie und der PR
bleibt dauerhaft `BLOCKED`, ohne dass etwas rot wird. In beide Richtungen belegt:
`2c45d444` (mit Marker) 0 Läufe → BLOCKED · `fa04b221` (mein leerer Commit, ohne Marker)
6 Läufe, alle grün → CLEAN · `7e177062` (neuer Commit um 19:07, wieder mit Marker) 0
Läufe → wieder BLOCKED. **Konsequenz: #1503 ist NICHT merge-fertig**, anders als weiter
oben zunächst berichtet — es braucht einen Commit ohne den Marker.

Die Lehre ist nicht „`[skip ci]` ist schlecht", sondern dass derselbe Marker
gegenläufig wirkt: auf einem **Merge nach `main`** ist er richtig (verhindert, dass ein
Docs-Commit einen Prod-Deploy auslöst — genau dafür existiert die Hausregel), auf einem
**PR-Head-Commit** hungert er einen Required Check aus. Korrigiert in CC-Memory
`feedback_blocked_without_any_pull_request_run`, in der Outline-Lesson und als Kommentar
an #1503; die erste Fassung aller drei sagte „ungeklärt".

---

## 2026-07-29 — Mail-Recherche-Werkzeug: von der Frage bis zum Index

Ausgangspunkt war eine gewöhnliche Frage („analysier die Mails von Frau Offner"), die ein
Dutzend Postfach-Abfragen über drei Konten kostete, weil ohne Index nicht auffindbar ist,
in welchem Postfach und Ordner eine Person vorkommt. Am Ende beantwortet ein Index dieselbe
Frage in **26 Millisekunden** mit **exakt derselben, verifizierten** Antwort (21 Nachrichten).

**Entscheidungsgrundlage in drei externen Runden.** KONZ-036 (portables Entwurfsdokument)
ging an zwei adversariale Reviews und eine eigenständige Gegen-Konzeption mit 16 bewerteten
Architekturklassen. 43 Befunde, alle einzeln getaggt in ADR-288 §11. Der tiefste kam aus
Runde 2: *ein ausgewiesen lückenhafter Index trägt positive Treffer, aber keine
Negativaussage* — eine fehlende Nachricht kehrt „offen" in „erledigt" um. Da Negativaussagen
das Produkt sind, war das ein Zuschnittsfehler, kein Detail.

**Vier Messungen kippten Annahmen — drei davon eigene.** (1) Der Bestand ist 66.580, nicht
die seit ADR-286 durchgereichten 90.967; Ursache belegt über den Retro `d5eb5e` (28.158
Nachrichten wurden am Vortag umsortiert, die Zählung erfasste einen Zwischenzustand), und
validiert daran, dass das nicht betroffene Referenzkonto die alte Zahl exakt trifft.
(2) Die Ausschlussregel entfernt 78,9 % — damit fällt der Vollaufbau auf 2,2 min und die
schärfste Review-Kritik von 95 % auf 15 % Fensterauslastung. (3) Bulk-Abruf bringt Faktor
8,9 end-to-end. (4) Mikro-Benchmarks überschätzen systematisch (120,7/s gegen 92,0/s real) —
exakt der Mechanismus, den zwei Runden an meinen Hochrechnungen kritisiert hatten.

**Zwei eigene Fehler fand erst der scharfe Lauf.** Die Parteien-Auflösung führte 13 Adressen
zu einer Person zusammen (halber Verteiler), weil der Anzeigename pro Kopfzeile statt pro
Adresse gebildet wurde. Und die erste Bestandsmessung verrechnete Ausnahmen still als `0`.
Beides gegen Testdaten unsichtbar, gegen das echte Postfach sofort.

**Gebaut und live:** Werkzeug (Ordner-Walk mit sichtbarem Nenner, Dossier, Parteien-Auflösung
in zwei Stufen, Abwesenheitsbeweis mit Kalibriersonde) in `platform`; Index (Rohobjekte,
Build-Generationen, mehrdimensionale Deckung, Volltext, Beteiligung als Relation, Ingestion)
in `dev-hub`, vier Prod-Deploys mit Migration.

**Offen und bewusst nicht getan:** die Postfach-Zugangsdaten liegen nicht auf dem
Produktionsserver. Der Zeitplan ist deployt und **inert** — er prüft sich selbst und meldet
den Grund. Der Schritt, der ein Geheimnis anfasst, gehört einem Menschen; das Runbook dafür
ist geschrieben.

---

## 2026-07-29 (Parallel-Session — Mail-Links klickbar gemacht, vier Studierenden-Vorgänge beantwortet)

**Kern in einem Satz:** Aus einem `/mailcheck` wurde eine Werkzeugkette, weil die Board-Links
nicht anklickbar waren — drei Wege mussten dafür erst **gemessen und verworfen** werden.

**Gemergt (4 PRs, alle CI-grün):** [#1531](https://github.com/achimdehnert/platform/pull/1531)
`mail_view.py` (Mail als lokale HTML-Ansicht, Zähl-Pixel neutralisiert) ·
[#1535](https://github.com/achimdehnert/platform/pull/1535) `anker.py` + Route `/a/<nr>`
(Board-Einträge an der Message-ID statt an Ordner+UID) ·
[#1536](https://github.com/achimdehnert/platform/pull/1536) `port_freigeben.py`
(verwaiste eigene Instanz vor dem Unit-Start vom Port lösen) ·
[#1538](https://github.com/achimdehnert/platform/pull/1538) Doku der systemd-Falle.
**Offen:** [#1544](https://github.com/achimdehnert/platform/pull/1544) — `MAIL_LOGIN` trennt
Anmeldename von Absenderadresse, review required.

**Vier Prämissen, die gekippt sind:**

1. **`file://` konnte nie funktionieren.** Die Sitzung läuft per SSH auf dem Hetzner-Server,
   der Browser des Owners sieht diesen Pfad nicht. Gemessen an `SSH_CONNECTION`, nicht vermutet.
2. **HNU-OWA ist kein Weg.** `outlook.hnu.de/owa/` endet nach Redirect auf `/vpn/tmindex.html` —
   Citrix-Gateway. IMAP ist durchgelassen, OWA nicht.
3. **Die iil.pet-Variante ist schlechter als sie aussah.** Alle vhosts nutzen
   Cloudflare-Origin-Zertifikate; Cloudflare sähe HNU-Mailinhalte im Klartext. Kein einziger
   vhost nutzt bisher `auth_basic` — es gäbe nicht einmal ein Muster.
4. **Der Absender im Entwurf war kosmetisch.** „dehnert" statt Adresse; Outlook setzt den Kopf
   beim Senden auf die Postfachadresse — belegt an der gesendeten #358, nicht angenommen.

**Drei eigene Fehler, benannt statt versteckt:**

- **Das Board führte zwei Studierende als erledigt, weil eine Antwort raus war.** Abel hatte
  seine Thesis-Arbeitsversion angehängt, Schönherr die Abgabeversion seines Study Papers —
  die eigentliche Leistung (Feedback, Bewertung) war unberührt. „Antwort gesendet" ist nicht
  „erledigt"; der Status hing am Sent-Eintrag statt an der Sache.
- **Die selbst eingebaute systemd-Härtung brach den eigenen Port-Vorabcheck.** `PrivateTmp`,
  `ProtectKernelTunables` und `ProtectControlGroups` remounten je `/proc`; fremde
  Datei-Deskriptoren werden unlesbar. `ProcSubset=all` und `ProtectProc=default` heilen es
  **nicht** — beide einzeln per `systemd-run` gegengemessen. Der Fehler war **stumm**: Unit
  auf `activating`, während der Waisenprozess mit altem Code weiterbediente.
- **Ein Test bestand lokal aus dem falschen Grund.** `read_mail.CONFIG_FILE` wird beim Import
  aus dem echten Home gebildet, der `Path.home`-Patch erreicht sie nicht; lokal existiert die
  Datei, auf dem Runner nicht. Gegenprobe seither mit leerem `HOME`.

**Entscheidungen:** Kein öffentlicher Endpunkt für Mail-Inhalte — Loopback plus SSH-Tunnel,
Bindung auf 127.0.0.1 wird erzwungen. Arbeitsteilung bestätigt: Verschieben und Löschen
erkennt die Maschine über den Message-ID-Anker; ansagen muss der Owner nur, was im Postfach
keine Spur hinterlässt (Telefonate, mündliche Zusagen). Gelöschte Anker werden **nicht**
stillschweigend entfernt — die Pflege-Regel „Item verschwindet erst bei Beleg" gilt auch für
Maschinenbefunde.

**Mail-Ergebnis:** Gesendet an Michalk (Hosting-Aufteilung LRA Traunstein), Ullah
(Proposal-Feedback nach 17 Tagen Verzug), Abel (Thesis-Rückmeldung), Lluca (Interview-Design),
dazu Leistungsbezüge-Antrag und MeikI-Terminzusage. **Ein Entwurf offen:** Schönherr —
Kurzfassung auf Owner-Wunsch, das ausführliche Feedback kommt nach seiner Präsentation und
liegt vollständig unter `~/.claude/feedback-schoenherr-studypaper.md`.

**Zwei Funde in fremden Artefakten, die nicht in dieser Session entstanden sind:** Die
Rollen-Signatur `~/.claude/mail-sig/hnu.txt` trug `[TODO Owner: Fakultät/Institut ergänzen]`
und wäre so an eine Studentin hinausgegangen (korrigiert mit der real gesendeten Fassung; die
übrigen vier Rollen-Signaturen gegengeprüft, sauber). Und in Abels Arbeitsversion stehen die
**Interviewpartner mit Vornamen im Fließtext**, zusammen mit Gesellschaft und Rolle — das ist
identifizierend und im Feedback als Erstes benannt.

**Offen und bewusst nicht getan:** `~/.claude/mail-hnu.env` ist **nicht** auf `MAIL_LOGIN`
umgestellt — mit der neuen Belegung käme der installierte Stand im Checkout nicht mehr ins
Postfach (beim Test war es kurz unerreichbar). Die zwei Umstellzeilen stehen als Kommentar in
der Datei und werden nach dem Merge von #1544 gesetzt.

---

## 2026-07-29 (Teil 2 derselben Session — Prod entlastet, Outline hinter Cloudflare Access)

**Kern in einem Satz:** Der Versuch, Prio 1 (Mail-Ingestion auf Prod) zu erledigen, lief in
eine Blockade — und die Blockade war das eigentliche Thema.

**Die Blockade und was sie offenlegte.** Ein `import apps.mail_agent` in `devhub_celery`
starb dreimal mit `rc=137`; das Kernel-Log sagte **„Memory cgroup out of memory"**, also das
Container-Limit, nicht der Host. Die Rechnung schien eindeutig (512 MiB Limit, 370,4 MiB
Leerlauf, 225 MiB neuer Prozess) und die naheliegende Antwort wäre gewesen, das Limit
anzuheben. **Das wäre falsch und gefährlich gewesen:** In die cgroup-Bilanz zählt der
Seiten-Cache mit, und unter Host-Druck kann der Kernel ihn nicht zurückgewinnen — die
Container saßen künstlich an ihren Limits. Nach dem Stoppen nicht benötigter Stacks fiel
derselbe Container **ohne jede Änderung an ihm** auf 305,9 MiB, der Import lief durch.

| Größe | vorher | nachher |
|---|---|---|
| Freies RAM | 444 MB | **9.455 MB** |
| Swap belegt | 4.095 / 4.095 | **1.757 / 4.095** |
| Laufende Container | 113 | **45** |

Gestoppt (nicht entfernt, per `docker start` zurückholbar): ausschreibungs-hub, odoo, hub137,
wedding-hub, coach-hub, recruiting-hub, research-hub, travel-beat, billing-hub, cad-hub,
pptx-hub, learn-hub, tax-hub, ttz, bahn-hub, decks-hub, onboarding-hub, trading-hub inkl.
`ib_gateway`. Messwerte als Kommentar an
[#1303](https://github.com/achimdehnert/platform/issues/1303); Folgebefunde als
[#1549](https://github.com/achimdehnert/platform/issues/1549).

**Cloudflare Access für Outline.** `knowledge.iil.pet` war der einzige produktive Dienst ohne
Access-Regel (200 ohne Umleitung). Angelegt mit zwei Richtlinien — Owner-Adressen und
`non_identity` für gültige Dienstzugänge. Beide Wege belegt: Browser 302 auf
`iil-team.cloudflareaccess.com`, Maschine mit `CF-Access-*`-Kopfzeilen bekommt JSON.
Werkzeugseite in [mcp-hub#187](https://github.com/achimdehnert/mcp-hub/pull/187).

**Drei eigene Fehler, benannt:**

- **Die entscheidende Memory-Notiz zu spät gelesen.** `reference_dochub_access_cloudflare`
  sagt: genau **ein** IdP (GitHub), kein Einmal-PIN, Cloudflare liefert immer
  `admin@wir-digital.de`. Damit sind `achim.dehnert@iil.gmbh` und `ad@dehnert.team` in der
  neuen Regel **wirkungslos**. Dass die funktionierende Adresse trotzdem drinsteht, war
  Vorsicht, nicht Wissen — sonst wäre der Owner aus Outline ausgesperrt gewesen.
- **Dieselbe Notiz warnt wörtlich „Fehlschlag ≠ leere Liste"** für den IdP-Endpunkt, der nur
  mit `cloudflare_write_token` lesbar ist. Genau in diese Falle bin ich gelaufen und zunächst
  darüber hinweggegangen.
- **Der Code-Patch am Outline-MCP genügte nicht** — das Startskript exportierte die beiden
  Variablen gar nicht. Ergebnis: genau der Bruch, den der Patch verhindern sollte, nur eine
  Ebene tiefer. Die Fähigkeit war da, die Verdrahtung fehlte. Nachgezogen.

**Zwei Entscheidungen gegen die Freigabe des Owners** — beide mit Beleg statt Vermutung:
`authentik` bleibt an, weil Outline **und** risk-hub (live, schutztat.de) ihr Login dort
auflösen (220 Auth-Ereignisse in 72 h). Und die Mail-Ingestion wurde **nicht** scharf
geschaltet, obwohl der Pfad jetzt frei ist — die zwei vorbereiteten Dateien liegen bereit,
der Schritt gehört in eine eigene Runde mit dem Geheimnis-Teil beim Owner.

**Offen und bewusst nicht getan:** Der laufende Outline-MCP stammt von vor dem Patch und
bekommt 302; bis zu seinem Neustart ist jeder Outline-Zugriff blockiert. Ein fertiger
Lesson-Entwurf zum cgroup-Thema wartet deshalb unter
`~/.claude/outline-pending/2026-07-29-cgroup-speicherdruck.md`. Ebenfalls angekündigt, aber
nicht mehr ausgeführt: `dev-hub.iil.pet` hinter Access.
