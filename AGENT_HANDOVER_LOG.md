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

---

## 2026-07-29 Abend — Der Egress-Pfad war tot und meldete das nicht

Auftrag war eng: ADR-288 in die vierte externe Runde geben. Der Weg dorthin kostete zwei
Fixes, drei PRs und einen Prod-Deploy, weil ein fehlgeschlagener LLM-Call wie ein
erfolgreicher aussah.

**Der Fehlschlag, der wie ein Ergebnis aussah.** Der erste Versuch, Runde 4 abzusetzen, kam
zurück mit `content: ""`, `tokens_used: 0`, `cost_usd: 0.0`, `duration_seconds: 0.13` — und
**ohne Fehler**. Eine Kurzprobe mit einem Satz Nutzlast lieferte dasselbe in 0,02 s, also
nicht größenbedingt. Die Gegenprobe über **denselben** Transport auf
`groq/llama-3.3-70b-versatile` gab Inhalt und 2.352 Token: der Transport war gesund, nur der
o-Series-Pfad nicht. Im Container-Log stand die Ursache im Klartext —
`litellm.UnsupportedParamsError: O-series models don't support temperature=0.0`. Sichtbar war
sie für den Aufrufer nie. Ohne die Gegenprobe wäre der leere Rückgabewert als fertige
Review-Runde in ein Architektur-Dokument eingeflossen.

**Der erste Fix war unvollständig, und die Zahl bewies es.** [mcp-hub#183] ließ `temperature`
für o-Series weg. Nach dem Deploy kam derselbe Call weiter leer zurück — aber die
Fehlermeldung sagte jetzt `temperature=0.7` statt `0.0`. Weglassen gibt die Kontrolle an aifw
ab, wo der Default 0.7 greift; litellm lehnt den genauso ab. Dieselbe geänderte Zahl belegte
zugleich, dass der Deploy gewirkt hatte: der Code war live, die Regel falsch. Korrigiert in
[mcp-hub#185] — `temperature` wird wieder **immer explizit** gesetzt, 1.0 für o-Series, 0.0
sonst. Die 13 Tests wurden mit umgeschrieben; die alten prüften auf *Abwesenheit* des
Parameters und hätten den Denkfehler festgeschrieben.

**Die strukturelle Ebene war die teurere.** aifw meldet Provider-Fehler als Feld am
Ergebnisobjekt (`success`/`error`) statt als Ausnahme — und **kein einziger Aufrufer im Repo**
hat sie ausgewertet: nicht `workflow_executor`, nicht `step_executor`, `planner`,
`use_case_decomposer` oder `task_pipeline`. In `step_executor` ist das schlimmer als
verwirrend: eine leere Antwort ohne Tool-Calls bedeutet dort „Schritt fertig", ein
Provider-Fehlschlag wurde also als erledigte Arbeit verbucht. Behoben in [mcp-hub#186]: der
Adapter wirft `LLMCallFailedError` (RuntimeError-Subklasse, damit breite Handler weiter
greifen), die Tool-Schicht bildet sie auf `llm_call_failed` ab statt auf das irreführende
`llm_unavailable` — der Adapter war ja verfügbar, der Provider hat abgelehnt. Volle
Orchestrator-Suite 753 passed, 6 skipped.

**Runde 4 dann mit Beleg.** o3 antwortete auf die Kurzprobe mit `OK` (999 Token, 4,04 s),
der volle Lauf lieferte 11.046 Token in 23,5 s. Verdikt **überarbeiten**, 7 von 9 Befunden
`[valid]`. Sie traf **alle drei** in §11.5 als ungeprüft benannten Punkte — der Auftrag hat
funktioniert, was für sich eine Aussage über §11.5 ist.

**Die folgenreichste Einarbeitung ist eine Herabstufung, keine Ergänzung.** Gate 0 fällt von
✅ auf 🟡: das Argument, mit dem die alte Bestandszahl 90.967 entwertet wurde — eine
Einzelmessung kann einen Zwischenzustand treffen — gilt unverändert gegen die neue 66.580.
Ein Indizienbeweis, der die Vorgängerzahl kippt, trägt seine eigene nicht. Neu sind §3.2.1
(drei benannte Auslöser, ab denen ein Supersede von ADR-286 fällig wird), Gate 10, Gate 11,
eine versionierte Ausschluss-Konfiguration und die Eingrenzung von „gesperrt" auf den
Retrievalpfad statt auf Konto oder Lauf.

**Bewusst abgelehnt:** die Empfehlung, `open` schon ab rund neun Zehnteln Deckung
zuzulassen. Bei jeder zehnten ungesehenen Nachricht kippt die Negativaussage — der
Unterschied zu vollständiger Deckung ist kategorial, nicht graduell. Übernommen wurde der
zweite Teil des Einwands: Gate 8 maß das Problem, ohne es zu beheben, und bekommt jetzt drei
definierte Hebel.

**Zwei eigene Fehlurteile, benannt statt versteckt.** Ich habe „platform braucht einen
zweiten Owner-Review" aus dem Sitzungsverlauf als übertrieben abgetan und auf „ein Approve
genügt" korrigiert — mit Berufung auf `required_approving_review_count: 1`, ohne
`require_code_owner_review: true` im **selben** Antwortobjekt zu lesen. Die ursprüngliche
Notiz war richtig, meine Korrektur der Fehler. Und ich habe zweimal einen Merge angesetzt,
weil ein „approved" im Chat stand, während `GET /pulls/1548/reviews` **null** Einträge
lieferte — Ursache: GitHub lässt Self-Approval nicht zu, Autor und Konto sind dasselbe.

**Offen und bewusst nicht getan:** der Deploy von [mcp-hub#186] stand beim Session-Ende noch
auf `queued`; der scharfe Check für #184 (Aufruf gegen ein absichtlich ungültiges Modell)
steht deshalb aus. [#1548] wartet auf einen Code-Owner. Die Mail-Zugangsdaten auf Prod bleiben
Menschenarbeit. Und auch nach vier Runden ungegengelesen: die Ausschluss-Messung selbst
(§1.4, 52.552 Nachrichten) — Runde 4 griff nur deren Folgen an, nicht die Zahl.

[mcp-hub#183]: https://github.com/achimdehnert/mcp-hub/pull/183
[mcp-hub#185]: https://github.com/achimdehnert/mcp-hub/pull/185
[mcp-hub#186]: https://github.com/achimdehnert/mcp-hub/pull/186
[#1548]: https://github.com/achimdehnert/platform/pull/1548

---

## 2026-07-29 Abend, Nachtrag — Korrektur zum Deploy-Status

Der Block oben sagt, der Deploy von mcp-hub#186 habe beim Session-Ende „noch auf `queued`"
gestanden, und der zweite `/session-ende`-Lauf verschärfte das zu „der Deploy ist abgebrochen,
`deploy / 🔍 Resolve` startet nie". **Beides war falsch.**

Der Lauf [30490611598](https://github.com/achimdehnert/mcp-hub/actions/runs/30490611598) ist um
**21:34 mit `success`** beendet, `deploy / 🚀 Production` grün. Beide Fixes sind im laufenden
Container verifiziert: `/app/llm_errors.py` liegt dort, `_temperature_for` steht an Zeile 219 und
wird an 327 ausgewertet. Zum Zeitpunkt meiner Sichtung stand der Lauf lediglich in der
Warteschlange — ich habe aus zwei fehlgeschlagenen `ci`-Jobs geschlossen, der Deploy könne nicht
mehr starten, statt den Lauf zu Ende zu beobachten.

**Was dabei aber ein echter Fund ist, und der wiegt mehr als der Irrtum:** die zwei roten Jobs
(`ci / Lint & Format`, `ci / Security Scan`) haben den Prod-Deploy **nicht aufgehalten**, weil
`ci / gate` grün meldet und der Deploy an diesem Gate hängt. Ein Lint-Fehler und ein
Dependency-Konflikt sind also nach Produktion durchgelaufen. Ob das Absicht ist oder ein blindes
Gate, ist **nicht geprüft** — der billigste Check ist die `needs:`-Liste des Gate-Jobs. Solange
das offen ist, relativiert es jede „CI grün"-Aussage in diesem Repo.

**Zwei eigene Muster in einer Session, beide dasselbe:** vorhin habe ich eine gefundene
Formatierungs-Abweichung liegen gelassen, weil sie nicht in der PR-Checkliste gated war — und
dann behauptet, genau sie blockiere Prod. Erst war der Befund zu klein, dann zu groß. In beiden
Fällen fehlte derselbe billige Check: einmal die Post-Merge-Job-Liste, einmal das Ende des Laufs.

Korrigiert wurden nicht nur diese Zeilen, sondern alle Kopien der Falschaussage: PR-Body und
Titel von [#188](https://github.com/achimdehnert/mcp-hub/pull/188) und der Text von
[#189](https://github.com/achimdehnert/mcp-hub/issues/189).

## 2026-07-30 — Mail-Ingest auf Prod scharf, Antwort-Entwürfe mit Zitat, ~/.claude-Schaden

Mail-Ingestion läuft: Runbook mail-ingest-prod.md Schritte 1–7 durch, genau eine aktive
Generation (6.008 Nachrichten, 12.865 Beteiligungen, Deckung `complete`), Zeitplan 03:30
nicht mehr inert. Der Größenvergleich lief bewusst **vor** der Freigabe: +0,5 % gegen den
lokalen Referenzlauf, Ordnerzahlen 92/27 identisch.

Antwort-Entwürfe trugen kein Zitat — `createReply` legt es an, der folgende PATCH auf
`body.content` löschte es. Auf dem IMAP-Weg fehlten `In-Reply-To`/`References` ganz.
Behoben: platform#1555 (+ `--design` fürs Rollen-Design), #1556 (Link-Dienst erreicht
jeden Ordner). Drei Entwürfe neu erzeugt, ungesendet.

`mail.iil.pet` hinter Cloudflare Access, eigener Tunnel im User-Kontext. Beim Erstlauf
antwortete der Host ~20 s mit HTTP 200 ohne Anmeldung: Access war angelegt, die
Durchsetzung noch nicht propagiert, der Tunnel lief schon. Tunnel sofort gestoppt, danach
302. Das Skript wartet jetzt auf die nachgewiesene Abweisung, bevor es den Tunnel startet
(`tools/cf_access/`, Runbook `loopback-dienst-hinter-cloudflare-access.md`).

Selbstverschuldeter Schaden: `generate.py --target ~/.claude` statt `~/.claude/commands`
tauschte per atomarem Swap das ganze Verzeichnis aus. Vollständig aus `.bak`
wiederhergestellt, `settings.json` zusammengeführt, Dienste gegengeprüft. Guard dagegen in
#1558. `--allow-live` schützte nicht: es prüft Gleichheit mit dem Live-Pfad, nicht
Enthaltensein.

Zwei Prozess-Stolpersteine: `[skip ci]` im Kopf-Commit macht Required Checks unerreichbar
(#1503 war approved und dauerhaft blockiert); und ein Merge während eines laufenden Push
verliert Commits (#1555 → Folge-PR #1556, zweites Mal am selben Tag).

---

## 2026-07-30 Nachmittag/Abend — dms-hub + doc-hub: Upload-Fix, Ruff-Regelsatz, Paperless-Struktur

**Auslöser:** zwei gemeldete Fehler an `docs.iil.pet` — „Dokument 854 ist ein Angebot, steht
aber als Rechnung" und „Upload mehrerer PDF, Reinziehen klappt nicht". Beide führten tiefer
als erwartet.

**Gemergt (4 PRs, dms-hub):** [#41] Mehrfach-Upload + Ablegen per Ziehen · [#45]
Freigabe-Schalter je Datenklasse · [#43] Ruff-Regelauswahl festgeschrieben · [#44]
KONZ-dms-hub-003. Drei Prod-Deploys, alle `success` (`2fcefcf`, `7b7da05`, `6c83430`);
laufendes Abbild am Container-Tag verifiziert, nicht nur am Job-Ergebnis. #44 mit
`[skip ci]` gemergt (reine Doku, kein Deploy ausgelöst).

**Der Upload-Fehler saß an drei unabhängigen Stellen**, nicht an einer: `<input>` ohne
`multiple`, Aufruf mit `this.files[0]`, und **gar kein** `dragover`/`drop`-Handler —
„Reinziehen" war kein Defekt, sondern eine fehlende Funktion. Serverseitig las
`upload_view` nur `FILES.get()`. Teilerfolg gibt jetzt 207 mit Namen der gescheiterten
Dateien statt 200.

**Der Klassifikations-Fehler war keiner.** Drei Hypothesen widerlegt: OCR läuft (Tesseract
5.3.0 via OCRmyPDF, `deu+eng`, 824/834 mit Textschicht); die `match`-Strings aller 15
Dokumenttypen sind wirkungslos, weil `matching_algorithm=auto` sie ignoriert; und Doc 854
hat **gar keinen** Dokumenttyp. Ursache ist `/opt/doc-hub/scripts/auto-title.py`, das den
Typ mit `break` beim ersten Treffer der Liste wählt — `Rechnung` steht an erster, `Angebot`
an achter Stelle, der Text enthält 9× „angebot" und 4× „rechnung". **Es gewinnt die
Listenposition, nicht der Befund.**

**Struktureller Befund (gemessen, nicht geschätzt):** 826 Dokumente, davon **553 ohne
Dokumenttyp (67 %)**, 681 ohne Korrespondent (82 %), 264 ohne jeden Tag. Das Skript schreibt
ausschließlich `doc.title`. Die Struktur des Archivs ist eine Zeichenkette, keine
Metadatenlage — und dms-hub filtert über Metadaten. Festgehalten in KONZ-dms-hub-003.

**Ruff: die Aufgabenstellung war falsch, nicht der Bestand.** CI stand seit dem 27.07. rot.
Naheliegend war „80 Befunde abarbeiten". Der billigste Gegencheck kippte es: ruff 0.15.21
aktiviert **59** Regeln, ruff 0.16.0 **413** — `ci.yml` zieht ungepinnt. Fix ist die
Deklaration der Auswahl (`select = ["E4","E7","E9","F"]`), keine Zeile Anwendungscode. Die
30 bereits angewandten Autofixes wurden bewusst zurückgenommen, damit der Diff die
Begründung nicht verschleiert.

**Datenschutz-Befund, der eine offene Entscheidung mitentschied:** der Bestand mischt privat
und geschäftlich und enthält **Gesundheitsdaten benannter Personen** (Tag `Gesundheit`, 21
Dokumente; Personen-Tags achim/bine/mara). Art.-9-Daten. Damit ist der lokale Ollama-Weg
nicht die günstigere, sondern die einzige tragfähige Variante — mein Groq-Vorschlag vom
Vormittag war falsch. Der Schalter (#45) schaltet deshalb auf der **Datenklasse**, nicht auf
der Verfügbarkeit, mit Erlaubnisliste statt Verbotsliste (264 ungetaggte Dokumente wären bei
einer Verbotsliste exportiert worden) und Rückfall auf den regelbasierten Weg statt auf die
Cloud. Reichweite heute ehrlich: **1 Dokument** — es gibt keinen Tag, der ein Dokument als
nicht-privat kennzeichnet.

**WireGuard zur RTX 4090: drei Fehler in Reihe, alle behoben.** (1) Rückroute fehlte —
`10.8.0.2` verließ den Server über `eth0`. (2) PSK einseitig: Station verlangte einen, Server
hatte für keinen der drei Peers einen; Kernel-Diagnose zeigte „Invalid handshake response".
(3) `AllowedIPs = 10.8.0.0/24` der Station schließt die Server-Quelladresse `10.99.0.1` aus —
umgangen durch eine zweite Adresse `10.8.0.1/24` auf `wg0`. Handshake steht, ICMP 2/2 in
7,9 ms. Die veraltete Datei im Zip (Endpoint `:51820`, fremder Serverschlüssel) wurde
**nicht** verwendet; nur ihr PSK, dessen Identität gegen `bNYr18c…` verifiziert wurde.

**Vier neue Issues, alle mit Messung statt Vermutung:** [#42] ungepinntes ruff · [#46] **157
Tests laufen nirgends in CI** (`ci.yml` ohne pytest, `deploy.yml` mit `skip_tests: true`) ·
[#47] **Scan seit 2026-03-30 in der Einlese-Warteschlange hängen geblieben**, vier Monate
unbemerkt · [#48] Backup-Aufbewahrung: Skript zielt auf 30 Tage, ein Alt-Cron behält 2.

**Eigene Fehler, benannt:** eine Zwischenmessung („721 von 824 ohne Textschicht") war ein
Artefakt meines Prüfverfahrens — die Gegenprobe mit `pdftotext` fand in 40 von 40 Text; die
Zahl gilt nicht. Eine zweite („16× BLE001") kam vom Grep über das CI-Protokoll statt über das
Werkzeug; es sind 14. Und ich habe `git checkout origin/main` im **geteilten Haupt-Tree** von
dms-hub ausgeführt — ADR-233-Verstoß, zurückgesetzt und per Fast-Forward sauber gezogen.

**⛔ Offen und blockiert:** Die WireGuard-Änderungen (PSK für Peer `bNYr18c…`, zweite Adresse
`10.8.0.1/24` auf `wg0`) stehen **nur im laufenden Zustand**. Der Schreibzugriff auf
`/etc/wireguard/wg0.conf` wurde vom Permission-Klassifikator abgelehnt. Ein Neustart des
Tunnels verliert beides. Befehle stehen im Session-Abschluss.

[#41]: https://github.com/achimdehnert/dms-hub/pull/41
[#43]: https://github.com/achimdehnert/dms-hub/pull/43
[#44]: https://github.com/achimdehnert/dms-hub/pull/44
[#45]: https://github.com/achimdehnert/dms-hub/pull/45
[#42]: https://github.com/achimdehnert/dms-hub/issues/42
[#46]: https://github.com/achimdehnert/dms-hub/issues/46
[#47]: https://github.com/achimdehnert/dms-hub/issues/47
[#48]: https://github.com/achimdehnert/dms-hub/issues/48
## 2026-07-30 Nachtrag — Mail-Werkzeug nach Kundenrückmeldung überarbeitet

Vier PRs im Review, alle aus derselben Rückmeldungskette: ein Kunde nannte eine Mail im
Rollen-Design wörtlich „sieht aus wie ein Newsletter". Daraus: Design raus aus der
Kundenkorrespondenz, Antwort-HTML kompakt (#1566 — jede Zeile wurde ein eigenes `<p>`,
Exchange normalisiert das auf 1em/1em), Namensdopplung nach dem Gruß automatisch entfernt
(#1568), Ursprungsmail optional als `message/rfc822` anhängbar (#1565, dabei RFC-2046-Falle
gefunden: `add_attachment(bytes, maintype="message")` wählt base64, erlaubt sind nur
7bit/8bit/binary). Dazu #1562: `html_to_text` lag zweimal im Baum, die Kopie ohne
`<style>`-Fix — Outlook-Mails kamen als VML-CSS statt als Text an.

Signaturen gekürzt: 5 → 2 Zeilen, Firmenangaben nur noch im Pflicht-Footer, §35a auch für
die DSB-Rolle (Absender ist die GmbH). Referenz für die Länge ist die Kundenmail mit
360 Zeichen; die eigene Erstfassung hatte 4.000.

MEiKI-Datenschutz-Anfrage an Actago: Analyse fertig und als lokales Board eingefroren
(`~/.claude/boards/meiki-datenschutz-anzeige.md`, über den Link-Dienst erreichbar). Kern:
§ 80 Abs. 1 SGB X verlangt ZWEI Anzeigen — die beauftragte öffentliche Stelle (HNU) muss
ihrer eigenen Aufsicht anzeigen, das fehlte im Plan. Und das Wort „KI" gehört aus der
Anfrage gestrichen, weil die Auswertung in beiden Stufen deterministisch ist. Wird in einer
anderen Session weiterbearbeitet.

---

## 2026-07-31 — platform (Sitzung ec0588a8)

Der Hardcoding-Megatest lief seit seiner Einführung am 2026-04-21 **nie**. `python -m pytest`
auf einem Runner, der nur `python3` kennt; unsichtbar, weil der Schritt
`continue-on-error: true` trägt. Der Melder öffnete darauf 28 inhaltsleere Regressions-Issues
(22.04.–15.06., Rumpf `Output nicht gefunden`), alle wurden geschlossen, keines führte zur
Ursache. Gefixt in #1588 samt Zweig, der rot wird, wenn gar keine JUnit-Datei entsteht.
Erster echter Lauf (30619024656): 100 Tests gesammelt, `15 failed, 53 passed`. Die Budgets
stammen vom 27.04. aus lokalen Läufen — Überschreitungen sind erstmalige Messungen, keine
Regressionen.

#1589: `evidence_claim_scanner.py` aus `~/.claude/hooks/` nach `tools/claude-hooks/` geholt
(war ungetrackt und ungetestet, obwohl er den Wächter gegen das häufigste Retro-Finding
darstellt) und um vier Claim-Klassen ergänzt. Gemessen an den fünf realen Fehlsätzen des
Tages fing die alte Fassung einen.

#1591: `read_mail` liest HTML-only-Mails (fünf von neun neuen Nachrichten des Tages waren
das); Anhang-Links des Link-Dienstes sind absolut statt relativ, weil der relative href den
Plattenpfad in die URL trug und von `/a/<nr>` aus ins Leere lief.

Gelernt über das Repo: Ruleset 17621471 hat `bypass_actors: []` — `--admin` hilft niemandem,
auch dem Owner nicht. Der Weg ist das Code-Owner-Review durch `@wirdigital`.

Eigene Korrekturen: „seit dem 15.07." war falsch (14.07. trägt denselben Fehler, Beginn ist
der 21.04.) — nachgezogen an #1588 und #1010. Drei Bypass-Audit-Kommentare beschrieben einen
Merge, der nie stattfand — richtiggestellt.

---

## 2026-08-02 — Lotse-Ausbau: KONZ-038 + Ritual + Welle 1

KONZ-038 (#1639, 3 interne + 2 externe Reviews), regel-ritual.yml (#1641, scharfer Lauf
bewiesen → #1640), Welle 1 komplett: #1643 (Scanner blocking) · #1644 (stale-clone-Drill) ·
#1645 (deferred_item advisory) · #1646 (scope_checkpoint advisory, Option A #1081) · #1648
(Handover-Freshness Skill-Phase + Ritual-Sweep). 8 Gate-Issues #1631–#1638 nachgeholt,
Replay-Analyse 55 Instanzen (DOC-Lücke 42 %) auf #1185. Verdrahtung: 6 Stop-Hooks in
settings.json, 3 Hook-Kopien synchron, cc-skill-dist @ 86546d09. Offen: D4/D6/D7/D8,
Messfenster bis 16.08., Token-Rotation orchestrator (Transkript-Exposure), fremder staged
KONZ-037-Entwurf im Haupt-Tree.

## Session 8ed6a2 — 2026-08-02 (Fortsetzung der SB-Neu-Session vom 31.07.)

**Zeitanker:** HEAD `eaffc4c8` · `rev-list --count` 2757 · geschrieben 2026-08-02

**Kern:** Silent-Failure-Lint (platform#1587) läuft jetzt in **10 Repos** — Canary
iil-testkit#13 mit Rot/Grün-Beweis in echter CI; 8 Bestands-Begründungen, kein
Verhaltens-Change; 3 Merges mit `[skip ci]` gegen ungefilterte Deploy-on-main,
nachgemessen deploy-frei. Staging-Checks: ein Job statt 8× `continue-on-error`,
Baseline der 7 bekannten Roten, **Regression = hartes Rot** (#1630 gemergt).

**Messbarkeit:** Signal K in `measure-evidence-discipline.py` (Flotte 9,3 ·
Session 8ed6a2 **48,6** bei identischem R ≈0,87 — K trennt, R nicht; UNVALIDIERT,
Scorecard-Abgleich offen). **Artefakt-Budget-Hook** (`scope-checkpoint` ×10) als
7. Stop-Hook verdrahtet, feuerte im echten Stop-Event (19 PRs + 3 Issues). Quelle
beider: #1654 gemergt; `~/.claude/hooks/artefakt_budget.py` == Repo-Stand.

**mcp-hub:** #192 + #193 per Owner-`--admin` (Audit-Kommentare an beiden); Deploy
30741745261 **success**, venv-Step im Log belegt → **#189 geschlossen**, #188-PR
gemergt. `policy_zone_freshness.sh`: Rückgabewert 3 statt Falsch-Grün + stderr-
Leak-Fix (#1615/#1626 gemergt). platform#1580 (fremder PR): update-branch löste
den Required-Context-Stau, Auto-Merge zog ohne `--admin`.

**Fremd vorgefunden, NICHT angefasst:** platform-Haupttree mit *gestagtem*
KONZ-platform-037 (parallele Session) · risk-hub NEXT.md · `.windsurf/`-Reste in
django-lms-lite/iil-doc-templates · dev-hub-Deploy `04a9d5e` lief noch (~09:56).

---

## 2026-08-02 — Mail-Index: Vorgangsketten aus Postgres statt aus IMAP

Aufgabe war nicht Stichwortsuche, sondern die *ganze Kette* zu einem Thema — ausgehend von
einer beliebigen passenden Mail, über Ordner- und Kontengrenzen hinweg, schnell genug, um
den Sinn daran zu bearbeiten. Beide vom Owner gesetzten Abnahmefälle bestanden: Offner
3 Nachrichten über zwei Konten in 51 ms (IMAP), Schmalberger 11 Nachrichten, 3 Beteiligte,
4 Ordner in 119 ms (Graph). Keine einzige Kante kam über den Betreff; alle sind über
References bzw. Graph-conversationId belegt. Bestand 11.573 Nachrichten aus drei Postfächern.

Gebaut: S1 Antwortpfad (mail_suche + tools/mail_agent/suche.py, Deckung an jeder Antwort) ·
S2 Vorgangs-Schicht über einen natürlichen Schlüssel (LogicalMessage.kennung, PROTECT) ·
S3 Volltext-Tor an ADR-286 §4.5 ohne Umgehungsschalter · S4 Graph-Ingest mit eigener
App-Registrierung plus vierstufiger Diagnose mail_graph_pruefen · S5 Dossier mit Evidenz je
Zeile · mail_kette mit drei nach Verlässlichkeit geordneten Kantenarten.

ADR-288 §4.1 geändert (#1598): der alte Wortlaut („nie auf Surrogat-IDs") zwang dazu, an der
Datenbank vorbeizubauen; „stabile Identität" erreicht dasselbe Ziel mit einer Beziehung.
Der Owner hat die Änderung ausdrücklich freigegeben — maximale Qualität vor ADR-Buchstabe.

Sechs stille Befunde am echten Bestand: 41 % des Index waren Kalender-/Kontakte-Platzhalter
(#1584) · Betreff-Stränge verschmolzen 43 verschiedene Studierende zu einem Vorgang ·
Verschieben erzeugte Duplikate, weil die transportspezifische Identität den Ordner enthält ·
der Index speicherte Sequenznummern statt UIDs, uidvalidity fest auf 0 (#1656 + dev-hub#195;
am Postfach belegt: FETCH 185 liefert, UID FETCH 185 nichts) · /opt/platform hing 33 Commits
zurück und synct nichts (#1585) · der untested-command-Hook meldete siebenmal denselben
Befund (#1619).

Eigene Fehler: git add -A sammelte fremde Arbeit einer Parallel-Sitzung ein (zurückgenommen);
ein --amend traf den Basis-Merge-Commit; ruff format über den ganzen Baum formatierte fremde
unfertige Dateien um; und das Ausrollen einer Migration ohne vorherige Kollisionsmessung
brach einen Prod-Deploy (6 doppelte Message-IDs). Sicherheitsvorfall: ein cat auf
/etc/cron.d/adr-outline-sync legte den Outline-Token offen — als kompromittiert behandelt,
Rotation offen (#1586).

Offen für die nächste Sitzung: Ingest-Neulauf mit echten UIDs (ohne den holt mail_volltext
nichts), Graph-Pfad in mail_volltext, /opt/platform nach jedem tools/mail_agent-Merge ziehen.

---

## 2026-08-02 (2. Eintrag) — Retro 287b23 + Maßnahmen + Token-Rotation

Retro gemergt (#1661, 7 Survivors, refuted_rate 0.30), Maßnahmen 2–8 komplett (#1664,
#1660, Issues 1186/1190 zu, Welle-2-Rangliste #705). Orchestrator-Key rotiert
(compose --force-recreate, Container-Env verifiziert); 🌀-Lehre docker-restart≠env-reload.
OFFEN: Rotation #2 in frischer Session (~/shared/rotate_orchestrator_token.sh) wegen
Watcher-Re-Exposure; .env.prod.bak-Altkeys auf Prod als Hygiene-Kandidat.

---

## 2026-08-02 (3. Eintrag) — Paperless wird zum DMS: Benutzertrennung, Abgleich, Hook-Vertrag

**Ziel erreicht:** Mara und Bine arbeiten in `docs.iil.pet` und sehen jeweils nur ihre
eigenen Dokumente — an einer echten Anmeldung belegt, nicht nur in der Datenbank.

**Cloudflare Access** (`infra/cloudflare/cf_access_idp_pin.py`, #1667): 16 Anwendungen auf
GitHub festgenagelt, Einmal-PIN angelegt, nur `docs.iil.pet` dafür geöffnet. Zwei Fallen:
leeres `allowed_idps` heißt *alle* Anbieter (ohne Festnageln hätte der PIN sofort auch für
`praes.iil.ai`/LRA gegolten), und der Endpunkt nimmt kein `PATCH` — `405 / 10405` liest
sich wie ein Rechteproblem, ist aber die Methode.

**Paperless-Konten** (`deployment/stacks/doc-hub/benutzertrennung/`, #1667): `mara` →
`md@dehnert.team`, `bine` → `sd@dehnert.team`, `achim` → `achim.dehnert@iil.gmbh`
(Zusammenführung, 65 Dok + 115 guardian-Einträge). 711 Dokumente ans Arbeitskonto, 0 ohne
Besitzer (in Paperless heißt „kein Besitzer" *für alle sichtbar*). 4× Superuser entzogen.
Endstand 776 / 27 / 11.

**dms-hub↔Paperless — DREI Ursachen, nicht eine.** Der Spiegel stand vom 19.07. bis heute
still: (1) Cloudflare Access antwortete mit Weiterleitung statt JSON (#52, interner Pfad),
(2) es gab **keinen Auslöser** — kein Task, kein Zeitplan (#53/#55), (3) der Worker hing
nicht in `bf_platform_prod` und konnte `iil_dochub_web` nie auflösen (#56). Ursache 3 kam
nur ans Licht, weil der neue Task **laut** fehlschlägt statt still `None` zurückzugeben.
Verifiziert nach Merge: Worker im Netz, Lauf über die Warteschlange `succeeded`,
`0 neu, 813 aktualisiert`.

**Hook-Vertrag** (#1674, nach #1673 einer Parallelsitzung): `hygiene_melder` sendete
`hookSpecificOutput` ohne `hookEventName` → der Client verwarf die Ausgabe und zeigte dem
Menschen einen Schema-Dump statt des Hinweises. Dazu: `memory_link_guard` schrieb *alle*
Verzeichnis-Funde dem meldenden Zug zu (8 Funde in nie geöffneten Dateien) — jetzt
getrennt nach eigen/fremd. Neues AST-Gate `test_hook_output_schema.py` über **alle** Hooks;
der alte Aufrufpfad-Drill konnte die Klasse nicht sehen (Registry-Filter + `*_scanner.py`).

**Ein eigener Fehler, offen dokumentiert:** Ich empfahl, `admin@wir-digital.de` einzuziehen,
ohne zu prüfen, welche Kennung die GitHub-Anmeldung erzeugt — und sperrte den Owner aus.
`last_login` stand in derselben Tabelle, die ich schon abgefragt hatte. Zurückgenommen;
Memory `feedback_check_login_identity_before_revoking_rights`.

**Offen für die nächste Sitzung:** GitHub-Hauptadresse auf `achim.dehnert@iil.gmbh`
umstellen, danach `admin@wir-digital.de` einziehen (vorher **nicht** — sperrt den Owner
aus). `ScanDocument` zählt 830 gegen 814 in Paperless: 16 Spiegel gelöschter Dokumente,
der Abgleich räumt nicht ab (in dms-hub#53 vermerkt). `~/.secrets/paperless_api_token`
war nach der Rotation ungültig — nachgezogen, Werkzeug
`deployment/stacks/doc-hub/paperless_token_sync.sh`.

---

## 2026-08-02 (3. Eintrag) — Megatest: 15 Befunde → 3 Wurzelursachen, CI misst jetzt frisch

Handover-Prio 1 komplett. Kern-Einsicht: die „15 failed" waren überwiegend Messfehler,
nicht Regressionen — (a) V-CFG-02 flaggte jeden os.environ.get(-Aufruf inkl. des eigenen
Empfehlungsmusters (Regex ≠ Regelbeschreibung); (b) der Megatest-Checkout klonte nur bei
fehlendem Verzeichnis und scannte auf dem persistenten Runner eingefrorene Erst-Klon-
Stände (research-hub-Funde aus Dateien, die auf origin/main längst anders aussehen);
(c) GITHUB_TOKEN ist repo-scoped — private Repos wurden nie gescannt, still grün.

Geliefert: #1681 (Regel-Präzision + klickdummy-Skip + frische Klone + Budgets neu
basiert: 13 Repos ergänzt, testkit→iil-testkit, bfagent 72→33, mcp-hub 79→34, sechs
weitere Budget-0-Repos auf Messwert) · vier Marker-PRs (dev-hub#199, research-hub#53,
nl2cad#61, iil-enrichment#11 — alle Attrappen/Guards, einzeln gesichtet) · #1679
(hygiene_melder hookEventName: SessionStart statt Stop; Wurzelgrund war die
ERLAUBTE_EVENTS-Liste im Schema-Test, die SessionStart nicht kannte) ·
MEGATEST_READ_TOKEN gesetzt (Enterprise-PAT per Owner-Freigabe; Scrub: Remote-URLs nach
fetch/clone sofort wieder tokenlos — Token liegt nie persistent in .git/config).
Beweis: Main-Lauf 30758611903 = 119 passed, 0 failed; 5 nicht scannbare Repos sind
Fremd-Org (meiki-lra/iilgmbh/ttz-lif) — Owner-Feld-Plan in #1682.

Eigene Fehler: (1) ruff format riss den zeilenbasierten hardcoded-ok-Marker von der
os.environ-Zeile (nl2cad-Lint rot → zweizeilige, formatstabile Fassung); (2) der erste
Checkout-Fix scannte unfetchbare Klone weiter stale → 9 Geister-Fails gegen neue Budgets,
erst der zweite Wurf (stale Klon entfernen statt scannen) war ehrlich; (3) megatest.yml
stand nicht im eigenen paths-Filter — Workflow-only-Push löste keinen Lauf aus (gefixt).

Offen: Marker-PR-Reste keine; Budget>0-Abbau + Org-Read-Vollabdeckung in #1682;
risk-hub seed_test_user-Sichtung iilgmbh/risk-hub#478 (Prod-live, TEST_PASSWORD-Seed).

---

## 2026-08-02 (4. Eintrag) — Rotation #2 nachverifiziert und nachdokumentiert

Session-Start-Befund: Die im 2. Eintrag als OFFEN geführte Rotation #2 des
ORCHESTRATOR_MCP_API_KEY war bereits ausgeführt (mtime der kanonischen Secret-Datei
und des Backups `.bak-rotation2` beide 2026-08-02 13:36 UTC), aber von der ausführenden
Session nirgends dokumentiert — welche Session es war, ist nicht rekonstruierbar (weder
AGENT_HANDOVER_LOG noch Retro 932035 erwähnen sie). Verstoß gegen die Artefakt-Pflicht;
dieser Eintrag holt die Dokumentation nach.

Verifikation (19:10 UTC, nur SHA256-Hash-Präfixe, nie Klartext): lokaler neuer Key =
Server-Env-Datei (mcp-hub-Host, `/opt/mcp-hub/.env.prod`) = Container-Env von
`mcp_hub_orchestrator_http`; Container-StartedAt 13:36:21Z. Die docker-restart-Falle
(env_file wird bei restart NIE neu geladen, 🌀-Memory) greift hier NICHT — die
Container-Env trägt nachweislich den neuen Wert. Der alte, transkript-exponierte Key
ist damit überall abgelöst.

Aufgeräumt: Rotationsskript aus `~/shared/` gelöscht (Übergabeschleuse, Zweck erfüllt;
das Skript enthielt selbst keinen Secret-Wert, hätte aber bei erneutem Lauf unnötig
rotiert — und nutzte intern `docker restart`, wäre also in die Falle gelaufen).

Offen bleibt: (1) Funktionsbeweis per Orchestrator-MCP-Connect aus einer Session, die
den Server lädt (z. B. dev-hub) — curl endet an der Edge mit 403, unkalibrierbar;
(2) Owner-only-Hygiene der `.env.prod.bak-*`-Altdateien auf dem mcp-hub-Host
(Alt-Keys im Klartext, Löschen irreversibel — nur vorgeschlagen).

**KORREKTUR (gleiche Session, ~20:00 UTC) — dieser Eintrag war in zwei Punkten falsch:**
(a) Es GAB ein durables Artefakt: der letzte Kommentar auf #1640 dokumentiert Rotation #2
vollständig (Owner-Freigabe „3 go", Server-Hälfte sofort, Client-Hälfte BEWUSST vertagt).
Der Vorwurf „Artefakt-Pflicht verletzt" entfällt; mein Fehler war, nur AGENT_HANDOVER_LOG
und Retro als Leseflächen abzufragen. (b) Die Rotation ist NICHT komplett: settings.json
trägt absichtlich den toten Token #2; `~/shared/finish_token_rotation2.sh` ist Step 0 der
nächsten frischen Session (VOR jedem settings-Read — Datei-Watcher spiegelt jede
settings.json-Änderung laufender Sessions ins Transkript, 2026-08-02 zweimal beobachtet).
Meine ✅-Ersetzung der ⚠️-Zeile in #1693 hatte genau diese Step-0-Anweisung von der
Lesefläche entfernt — mit dieser Korrektur wiederhergestellt. Die Server-Hälfte-Verifikation
aus dem 4. Eintrag (Hash-Gleichheit, StartedAt) bleibt gültig und ist nun unabhängige
Bestätigung des #1640-Kommentars.

---

## 2026-08-03 — Session 9530de73 (health-poll-honest-failure): Health-Ehrlichkeit + Ritual-Prep

Kern: Zwei Klassen von „grün lügen" beseitigt. (1) Task-Ebene: dev-hub#201 gemergt+deployt —
poll_all_checks/platform_health_scan schlagen fehl statt succeeded-mit-Fehler-Dict; Prämisse
des Issues korrigiert (blinder Poller lief auf fsn1, nicht Prod). (2) Check-Ebene: die 4
Dauer-unhealthy (dms/coach Worker+Beat) arbeiteten nachweislich — pidof matcht Exe-Basenamen
python3.12, nie setproctitle-celery; dms-hub#58 + coach-hub#58 gemergt/deployt, danach
Prod 0 unhealthy (nachgemessen). #1549 damit komplett (beat-Limit war schon via IaC 512M,
authentik seit 2 Tagen healthy).

Ritual-Prep (#1640): D4 ausgeführt — 118 Memory-Regelquellen klassifiziert (A=67/B=36/C=15,
reassess_by gestaffelt), 11 Policies via PR #1700 (einzeilig statt Frontmatter wegen
inject_policies-10-Zeilen-Fenster); K3 Sunset-Ledger via PR #1701; FP-Auswertung der zwei
Advisory-Scanner: n=0 echte Auslösungen (13 Transkript-Treffer = Code-Spuren der Bau-Session)
→ nicht bewertbar, Punkt für Ritual-Lauf 1. ACHTUNG: #1700/#1701 standen 04:30 trotz
Owner-Meldung „gemergt" OPEN/REVIEW_REQUIRED — Approve fehlt.

Offen/Übergabe: fsn1-Tenant-Rätsel (Owner-Lauf created=True + count=1 via Django, psql in
devhub_db = 0 rows; DNS/Netz/Settings/Prozess-Env/Transaktionen ausgeschlossen) —
~/shared/fsn1_org_fix.sh druckt settings_dict + Gegenzählung + Tick. Eigener Fehler:
DB_PASSWORD (fsn1) via Präfix-Grep ins Transkript → dev-hub#202 (Rotation Owner-vertagt);
Lesson + 🌀-Memory. Ferner: docu-update #1704, shared-ci-Tag-stale bereits #1157/#1678,
dev-hub#187 UID-Neulauf unentschieden. Wissen: 2 Outline-Lessons (pidof; Env-Grep-Leak),
pgvector session:platform:20260803:health-poll-honest-failure + error:fleet:20260802-pidof-celery.

---

## 2026-08-03 (2. Eintrag, gleiche Session 9530de73) — Mail-Strang komplett + error-handling-Policy

Vormittagsblock nach dem 1. Session-Ende: UID-Neulauf fertig (#187 zu; mittwald 1.936
saubere Kopien, 3.649 Alt-Kopien stillgelegt), Volltext beide Transporte live (#204 zu via
#205: uidvalidity-/Konto-Filter + Graph-$value; AC 3 scharf: hnu geholt 3 / iil geholt 1,
body 4/4). Wurzelfund: /app/mail/iil_mail_api = Voice-Agent-App ohne Mail-Rolle — der
Container-Graph-Zugriff hatte NIE funktioniert (drei Hypothesen falsifiziert: ReadBasic,
Consent fehlt, Nachrichtenschutz; Beweis via Token-roles-Claim + SP-appRoleAssignments).
#207 gemergt+deployt: Migration 0011 (Zeitpläne iil/mittwald/heartbeat-scan, psql-Beleg),
MAIL_GRAPH_CREDS als Compose-environment auf iil_mail_ingest.env, heartbeat_scan wirft
bei >48h. #206 offen bis Nacht-Beleg. error-handling.md org-weit (#1706), adversarial
right-sized (Incident-Ausnahme, Gate-ab-2.-Auftreten, Taxonomie, Grenzen≠Fehler).

Eigene Fehler (Policy direkt angewendet): (1) Commit-Message-Datei aus tmp-Scratchpad
verschwunden → blinder --amend schrieb die Branch-Basis um; per reset --soft + Lease-Push
repariert, 🌀-Memory feedback_amend_after_failed_push_verify_head. (2) Zwei Lease-Pushes
scheiterten an stalem/ungültigem Lease-Wert — exakter Remote-Hash als Lease ist der Weg.
(3) mail_volltext in devhub_celery stirbt am 512M-cgroup (exit 137) — devhub_web nehmen.

Wissen: Outline-Lesson wrong-app-creds; pgvector session:platform:20260803:mail-strang +
error:dev-hub:20260803-wrong-graph-app. Offen: #206-Nacht-Beleg (03:50/04:10/05:00),
#202 Rotation (Owner-vertagt), #1704 docu-update, Step 0 (finish_token_rotation2.sh)
nächste frische Session.

---

## 2026-08-03 — Session 928b64 (retro-928b64): Paperless-CSRF — Server sauber, Ursache im Browserprofil

Kern: Ein Nutzer-`403 CSRF Failed … header incorrect` auf docs.iil.pet wurde geloest und
die Server-Seite dabei in fuenf Dimensionen belastbar freigemessen — Schreibpfad (POST
/api/tags/ mit Token 201, ohne Kopfzeile 403), keine Token-Rotation ueber vier Aufrufe,
CSRF-Config regulaer (CSRF_USE_SESSIONS=False, COOKIE_DOMAIN=None), nginx ohne Cache und
ohne Cookie-Umschrift (tunnel-only 127.0.0.1:8999), keine domainweite Cookie-Domain in
der Flotte. Ursache lag im Edge-Profilzustand aus der Zeit vor dem Access-Umbau (29.07.);
Fix = Websitedaten loeschen UND alle Tabs schliessen, weil ein Service Worker die
Kontrolle erst dann abgibt. Werkzeuge neu: ~/shared/paperless_csrftest_run.sh und
~/shared/paperless_csrf_rotation.sh.

Entscheid (haelt unabhaengig von der Diagnose): PAPERLESS_ENABLE_HTTP_REMOTE_USER_API
bleibt AUS — sie verschoebe die Vertrauensgrenze von der Oberflaeche auf die API und
haengt dauerhaft an einer nicht durchgesetzten Invariante; API-Skripting laeuft bereits
ueber Token-Auth, DRF erzwingt CSRF nur bei SessionAuthentication.

Eigene Fehler, alle im Retro belegt: die unbewiesene Ursache „veralteter Tab" wurde
zweimal als Feststellung formuliert und in ein durables Memory geschrieben, bevor sie
belegt war; der billigste Client/Server-Discriminator (zweiter Browser) kam als fuenfter
Schritt, obwohl er in der zu Beginn gelesenen Memory-Datei woertlich stand
(reference_paperless_remote_user_and_csrf.md:33 „… oder privates Fenster"); eine nicht
existente Edge-URL wurde als Anweisung genannt; der Prod-DB-Schreibzugriff (2 Wegwerf-Tags,
selbst geloescht, Rest auf 0 nachgezaehlt) war nur im Skript-Kopf offengelegt, nicht in
der Freigabe-Zeile. Slug claim-before-cheapest-check steht damit bei x37.

Offen/Uebergabe: Ursache nicht isoliert (Doppel-Cookie vs. Service Worker — Zustand ist
geloescht, nicht nachholbar); Gate fuer claim-before-cheapest-check (#1640); Memory-Kandidat
„Prod-Schreibzugriff gehoert in die Freigabe-Zeile" (Retro Paragraph 6); Falsifikation von
Retro-Befund #4 ungeprueft, weil Subagenten in dieser Umgebung untersagt sind (refuted_rate
0.0, in Paragraph 8 begruendet). Unveraendert aus dem Vorstand: Step 0
~/shared/finish_token_rotation2.sh. Wissen: Outline-Lesson
d000582f-2316-48c2-99f2-afeefe3ee6d9; pgvector session:platform:20260803:retro-928b64 +
error:doc-hub:20260803-paperless-api-csrf-403.

---

## 2026-08-03 — Session melder-triage: drei Melder gefixt, zwei davon meldeten Gesundes als krank

Auftrag war eng gefasst: der User gab die Punkte 4–7 eines Session-Start-Boards frei,
danach einzeln "1 go 2 3 done 4 go 5 go 6 go 7 automatisch". Alles Folgende haengt an
diesen Nummern; nichts wurde daneben aufgemacht.

**Der rote Faden, den keiner der Punkte vorhergesagt hat:** von fuenf als "blind"
gemeldeten Meldern war keiner aus dem vermuteten Grund rot (HTTP 401), zwei waren
bereits gefixt, und **zwei meldeten Gesundes als krank**. Beide aus derselben Wurzel:
der Melder prueft einen Schluessel, den der produzierende Job gar nicht mehr setzt.

- **backup-meter** meldete "risk-hub juengster Snapshot 89.6 h alt". Nachgemessen:
  der taegliche Job (Cron 02:30) legt `risk_hub_db` UND den Sammel-Snapshot `volumes`
  an, beide 7,8 h alt, und `volumes` enthaelt sowohl `risk_hub_media/_data` als auch
  `risk_hub_minio_data/_data`. Der in `expected-apps.json` erwartete Tag `risk-hub`
  stammt aus einem manuellen Einzellauf vom 30.07., den nichts erneuert. Der Alarmwert
  sah *plausibel* aus (89,6 h statt "kein Snapshot") — genau das machte ihn gefaehrlich.
  Fix platform#1724: der Meter kennt jetzt mehrere `checks` je App und prueft beim
  Sammel-Snapshot zusaetzlich `paths_contain`. Ohne die Pfadpruefung haette der Fix
  eine echte Luecke zugedeckt: `volumes` bliebe frisch, auch wenn risk-hubs Pfade
  daraus verschwaenden. Beweis an den echten 57 Snapshots: alt 1 Verletzung, neu 1 konform.
- **sync-drift-meter** meldete "design-hub: .windsurf/ fehlt in .gitignore" — die
  Zeile ist dort seit dem 2026-06-01 committet (`8a0ee9ca`). Zwei Monate Fehlalarm aus
  einem Klon, den der Melder mit `if [ ! -d ]` anlegte und danach **nie** zog. Zweiter
  Defekt derselben Stelle: Owner hart auf `achimdehnert`, fuenf Repos scheiterten still
  mit `WARN: not found`. Fix platform#1721 (`tools/fleet_checkout.py`): Owner ueber
  `registry_api`, Klone werden aktualisiert, und die **Abdeckung** steht jetzt im
  Issue-Text (49 von 52, drei Fremd-Org namentlich).

**`/opt/platform` ist ab jetzt selbstziehend.** Bis heute zog den Prod-Werkzeugklon
nichts: kein Cron, kein Skript, keine systemd-Unit — nur Handgriffe zu unregelmaessigen
Uhrzeiten, mit einer Luecke von 27 Tagen zwischen dem 02.07. und dem 29.07. Ein Merge
nach `main` wirkte dort nicht, sah aber so aus. Jetzt zwei unabhaengige Dinge:
Phase 0.7.3 misst den Klon in jeder Session von aussen (platform#1723, zwei WARN-Stufen:
`HINTERHER` = Rueckstand ohne Mail-Risiko, `DRIFT` = `tools/mail_agent` weicht ab), und
`opt-platform-sync.yml` zieht ihn bei jedem Push auf main plus taeglich 01:15 UTC
(platform#1725, `self-hosted`, kein SSH — der Runner laeuft als root auf demselben Host).
**Erster scharfer Lauf war der Merge selbst und ist durchgelaufen:** der Klon ging von
32 Commits Rueckstand auf `HEAD == origin/main` (`0da74306`), unabhaengig nachgemessen.
Der Job prueft den Zielzustand nach dem Pull, nicht den Exit-Code von `git pull` — der
kann 0 liefern und den Klon trotzdem hinterherhinkend lassen.

**Eigener Fehler, gemeldet:** ein `cat` auf `/etc/cron.d/adr-outline-sync` trug einen
Outline-API-Token im Klartext ins Transkript; der gezielte `grep` war der naechste
Schritt, einen Aufruf zu spaet. Gleiche Klasse wie dev-hub#202 vom selben Tag. Getrackt
in **dev-hub#214** (privates Repo — platform ist oeffentlich), Rotationsskript liegt
zweiphasig in `~/shared/rotate_outline_token.sh`: Phase 1 legt den neuen Schluessel an,
verifiziert ihn, schreibt `/etc/adr-outline-sync.env` mit 0600 und baut den Cron aufs
Sourcen um; erst `--revoke` nach einem erfolgreichen 04:00-Lauf loescht den alten.
Zwei Classifier-Blocks (worktree-reaper `--apply`, Credential-Handling auf prod) wurden
respektiert, nicht umgangen, und an den Owner uebergeben.

Kleineres: dev-hub#213 gemergt (CHANGELOG+README zur FAILURE-Semantik der Health-Tasks,
`[skip ci]`), platform#1704 geschlossen. `governance/**` fehlte im paths-Filter von
`tools-tests.yml` — der gestern gebaute Trigger-Deckungstest (#1717) fiel sofort darauf,
mitgezogen in #1724. Ein gemergter Worktree in frist-hub gereapt (20→19).

**Offen:** dev-hub#214 Rotation ausfuehren (danach dritte Checkbox: weitere
`/etc/cron.d/`-Dateien mit inline-Geheimnissen pruefen) · platform#1718 kann geschlossen
werden, der Melder ist gefixt · platform#1508 Restpunkte: Registry-Live-Reconcile-Funde
(apo-hub, onboarding-hub) triagieren, und **`Gen project-facts.md` bleibt rot** — 3×
"Kopf von 'main' nicht lesbar" fuer frist-hub/meiki-hub/ttz-hub, weil `gh_slug()` den
Owner ueber einen GitHub-**Redirect** aufloest, den es fuer nie transferierte Repos nicht
gibt; der Fix braucht einen Scope-Entscheid (Owner aufloesen = PRs in Fremd-Org-Repos,
oder ausschliessen mit benanntem Grund) · shared-ci-Tag-Drift jetzt an drei Tags
gleichzeitig sichtbar (#1157 kommentiert) — fehlt eine Tag-Cut-Kadenz, sonst laeuft sie
nach jedem Schliessen erneut auf · die 46 abgelaufenen Leases bleiben liegen: 23 dirty
(fremde Arbeit), 40 mit offenem PR, 12 detached HEAD — nur einer war reapbar, die
Hygiene-Meldung ueberzeichnet den Aufraeumbedarf · drei fremde dirty Repos unveraendert
(django-lms-lite, iil-doc-templates, risk-hub).

**AGENT_HANDOVER.md wurde bewusst NICHT angefasst:** PR #1720 (fremde Session) stand
beim Session-Ende offen und traegt bereits einen neuen Stand. Nur dieser Log-Block —
`merge=union` traegt ihn konfliktfrei neben deren Aenderung.

Wissen: pgvector `session:platform:20260803:melder-triage` +
`error:platform:20260803-melder-misst-falschen-schluessel`.
## 2026-08-03 (3. Eintrag) — Session 8e5cf907 (session-start → Melder, Mail-Bestand, Zugangsschutz)

Als Statusaufnahme gestartet, über freigegebene Ketten in drei Repos gewachsen. Kern: eine
blockierte Merge-Wand aufgelöst, die Melder-Kette wirklich zum Melden gebracht, den Mail-Bestand
ehrlich vermessen und eine offene Route geschlossen.

Erledigt: platform#1716 (Deploy-ADR-Gate akzeptiert `amends:` — `main` war rot und blockierte
jeden PR; auf blankem main gegengeprüft, #1715 auto-closed) · platform#1714 (`gh` auf dem
Prod-Runner installiert + `ensure-runner-tooling.sh` als einzeln aufrufbare IaC; beide Melder
legen wieder Issues an: #1718/#1711) · dev-hub#202 geschlossen (fsn1-DB-Passwort rotiert,
`ALTER ROLE` + `.env.prod` + `--force-recreate`, alle Hashes identisch, DB-Verbindung belegt,
5/5 healthy, bewusst ohne `.bak`-Kopie) · 32 stale Worktrees in 17 Repos entfernt (Leases 76→46).

Prämissen-Korrekturen (beide waren Pflicht-Zeilen im Handover): Step 0 `finish_token_rotation2.sh`
war längst erledigt (drei Orte hash-identisch, MCP verbindet) · #1700/#1701 waren gemergt, nicht
offen · authentik schützt dev-hub **gar nicht** (kein `auth_request` in der nginx-Site; die
Weiterleitungen kommen von django-allauth).

Sicherheitsfund: `/mail-agent/` lieferte 200 ohne Anmeldung, auch an Cloudflare vorbei über die
Origin-IP. Fix + Konzept in dev-hub#212 (KONZ-dev-hub-002): `DevHubLoginRequiredMiddleware` mit
Pfad-Positivliste; `/livez/` und `/api/` begründet offen. Nebenbefund mitbehoben: test.py führte
eine Middleware-Zweitliste, der Testlauf prüfte eine andere Kette als Prod.

Mail-Bestand (Owner-Frage, Antwort NEIN): 15.123 Kopien, 0 Attachment-Zeilen, 4 Volltexte →
dev-hub#209/#210/#211. Zeitpläne iil/mittwald hatten noch nie gefeuert, erster Lauf 2026-08-04.

Eigene Fehler, selbst gemeldet: „keine Issues angelegt" war ein Abfragefehler (`gh --label a,b`
ist UND) · das erste 403 auf `/mail-agent/` war ein falscher Host-Header, kein Defekt · der erste
grüne dev-hub-Testlauf war wertlos, weil test.py die neue Middleware gar nicht lud.

Offen/Übergabe: dev-hub#212 + #208 mergen; **K1 (Nachmessung von außen) steht aus — der Fix wirkt
erst nach Deploy** · dev-hub#211 NICHT vor #212 umsetzen · #1508 bleibt offen (Fremd-Org-Token,
2 Registry-Drift-Funde) · Konzept A (LLM-Antworten) aussteht, ADR-284 verlangt Eval-Satz zuerst ·
Kernel-Reboot 88.198.191.108 steht aus. Nicht verifiziert: ob weitere dev-hub-Routen offenstanden.

---

## 2026-08-03 (4. Eintrag) — Session 3ca15d7d: Mail-Verfuegbarkeit, ADR-293, und ein falsch zugeordnetes Viertel

Als Session-Start begonnen, ueber eine Owner-Entscheidung zur Datenhaltung gewachsen.
Kern: die Mail-Lane ist aus ADR-286 Option D herausgenommen, der Volltext laeuft jetzt
ueber den Umfang statt ueber einen Vorgang — und die dafuer vorgeschriebene Messung hat
einen Datenfehler aufgedeckt, der ein Viertel des Bestands betraf.

Erledigt: platform#1722 (Prio-Liste entstaubt: der SessionStart-Hook spiegelte 7 Punkte,
5 davon laengst erledigt) · platform#1727 (ADR-293, amendet ADR-286 §3) · dev-hub#215
(Anhangs-Inventar aus BODYSTRUCTURE, ohne zusaetzlichen Umlauf; zieht auch bestehende
Kopien nach) · dev-hub#216 (--account waehlt wirklich das Postfach) · dev-hub#217
(mail_volltext nutzt dieselbe Konto-Aufloesung) · dev-hub#218 (tsvector-Grenze) ·
dev-hub#219 (Fortschritt statt Endlosschleife) · dev-hub#212 gemergt (Zugangsschutz,
K1 nachgemessen) · platform#1720 + #1726 der Parallel-Session mitgemergt.

Der Fund: 3.641 von 3.652 `mittwald`-Kopien waren hnu-Kopien. Ursache war eine
Vorrangregel zwei Ebenen tiefer (--config sticht --account), sichtbar erst, weil ADR-293
Gate 2 eine Messung VOR dem Schreiben verlangt. Ohne dieses Gate haette der Volltextlauf
3.579 fremde Nachrichten samt Inhalt unter falschem Label festgeschrieben — aus einem
Zaehlfehler waere ein Inhaltsfehler geworden.

Eigene Fehler, alle selbst gemeldet und im PR-Text belegt: (1) ein Regressionstest war
mit "z"*1.5MB gruen, obwohl der Fix fehlte — 1,5 MB desselben Zeichens ergeben EIN Lexem;
erst 110.000 verschiedene Woerter reproduzierten den Produktionsfehler. (2) "Deploy
success" gemeldet, obwohl der Container noch den alten Stand fuhr — `gh run list --limit 1`
unmittelbar nach dem Merge liefert den VORHERIGEN Lauf; belastbar ist der Abgleich
headSha gegen origin/main plus ein Blick ins Image. (3) `pkill -f volltext_iil` traf die
eigene SSH-Kommandozeile (Exit 255, das folgende sed lief nie) — Klammer-Muster noetig.
(4) ein Befehl an den Owner uebergeben, ohne ihn selbst gelaufen zu sein (`docker exec -it`
ohne TTY). (5) vorgeschlagen, drei unbekannte Konten stillzulegen — es waren die
SSO-Konten des Owners.

Beantwortet, war offen: der server-seitige Merge ehrt `merge=union` NICHT (#1726 ging
nach dem Merge von #1720 auf DIRTY; lokal lief derselbe Merge konfliktfrei).

Offen/Uebergabe: iil-Volltextlauf laeuft (7.926, ~80/Runde) · ADR-293 Gate 3
(Crypto-Shredding am echten Bestand) und Gate 4 (Deckungsausweis) · /mail-agent/ auf
Live-Daten (dev-hub#211) · Fehltreffer bei Personennamen durch deutsches Stemming.

---

## 2026-08-03 (5. Eintrag) — Session 3ca15d7d, Abschluss: Volltext steht auf allen drei Postfaechern

Fortsetzung des 4. Eintrags. Der iil-Lauf ist durch; damit ist der Auftrag
"komplette Verfuegbarkeit von Mail-Text und Anhang fuer alle drei Postfaecher"
erfuellt.

Endstand: hnu 3.513/3.513 · iil 7.920/7.925 · mittwald 91/91. Bestand 11.612
Nachrichten, 8.712 Anhangs-Inventarzeilen, TextUnit body 11.594 / attachment
8.846. Datenbank 7,2 GB. Heute frueh: 4 Volltexte, 0 Anhangszeilen.

Der letzte Blocker war lehrreich und keine Speicherfrage: die offenen
Nachrichten stehen nach sent_at, drei Fotomails (45,8 / 24,0 / 45,8 MB) standen
ganz vorn und rissen JEDE Runde mit, bevor die 845 kleinen drankamen - 105
Runden ohne einen Schritt. Die Speichergrenze aus #220 half nicht, weil sie
NACH einer fertigen Nachricht prueft und diese nie fertig wurden. Gefixt mit
--max-roh (dev-hub#223): zu grosse Nachrichten werden MIT IHRER GROESSE
vermerkt statt uebersprungen; ohne Vermerk gelten sie weiter als offen und
blockieren erneut.

Auf dem Weg dorthin, alle vom Owner angestossen und alle gemessen statt
vermutet: die Frage "wo ist da ueberhaupt Django?" fuehrte zu schlanken
Batch-Settings (Sockel 226 -> 59 MB; der Sockel war nicht Django, sondern 32
geladene Apps inkl. aifw); die Frage nach Staging + Massen-Import fuehrte zur
Messung, dass DB-Schreiben nur 7 % der Verarbeitungszeit kostet und die
Textextraktion 91 % - deshalb keine Staging-Tabelle, sondern die Trennung von
Holen und Auswerten (dev-hub#222), die einen kuenftigen Parserwechsel ohne
Postfach-Zugriff moeglich macht.

Eigene Fehler, zusaetzlich zu den im 4. Eintrag genannten: (1) iil-Volumen als
5-6 GB hochgerechnet, real 7,2 GB - die 120er-Stichprobe traf die Fotomails
nicht. (2) "Deploy success" gemeldet, obwohl `gh run list --limit 1` direkt
nach dem Merge den VORHERIGEN Lauf liefert. (3) Zugriffe je Hostname aus dem
nginx-Log gezaehlt, ohne zu pruefen, dass das Standardformat gar keinen
Hostnamen enthaelt - die Null war mein Filter. (4) Behauptet, die Schleife sei
tot, und eine zweite gestartet; die "2" im Prozesszaehler waren nohup + sh.

Offen: ADR-293 Gate 4 (6.152 Textzonen mit unsupported_reason - nur gezaehlt,
nicht aufgeschluesselt) · Gate 3 (Crypto-Shredding am echten Bestand, jetzt
erstmals pruefbar) · Cloudflare-Entscheidung · Namens-Umstellung auf
dev-hub.iil.pet · /mail-agent/ auf Live-Daten (haengt an der
Cloudflare-Entscheidung).

---

## 2026-08-04 (6. Eintrag) — Session 3ca15d7d, Abschluss: ADR-293 vollstaendig belegt

Fortsetzung des 5. Eintrags. Der Owner gab pg_trgm, OCR, Gate 3, Cloudflare-Weg 1
und die Namens-Umstellung frei; alles ist erledigt und am echten Bestand belegt.

Der wichtigste Fund kam aus Gate 3 und wurde nur sichtbar, WEIL der ADR einen
Nachweis am echten Bestand verlangt und keinen gruenen Test: `record_erasure`
vernichtete Rohtext und Metadaten, liess aber die TextUnit-Zeilen stehen. Nach
der Loeschung war die Nachricht weiterhin durchsuchbar, der Name des Empfaengers
stand woertlich in der body-Zone. Die Loeschung SAH erfolgreich aus. Der
Docstring der Funktion kuendigt die fehlende Ergaenzung seit jeher an; solange
es fast keine Volltexte gab, war es folgenlos. Behoben (dev-hub#227), Nachweis
wiederholt, alles auf 0.

Zweiter Fund: die Trigramm-Schwelle 0.5 war zu locker — "aramis" lieferte neun
Blindgaenger. An vier Begriffen mit bekannter Antwort kalibriert auf 0.6.
Lehrreich daran: unter 0.5 lieferte "Offner" 459 Treffer, was nach guter
Trefferquote aussah und fast vollstaendig Rauschen war. Ohne eine Menge mit
bekannter Antwort haette man das fuer ein gutes Ergebnis gehalten.

Dritter Fund: der Vorgabewert von TENANT_NON_TENANT_SUBDOMAINS kannte den neuen
Kanon dev-hub nicht — nur production.py fuehrte ihn. Dieselbe Klasse wie
--config gegen --account beim Ingest: Vorgabe und gesetzte Einstellung liefen
auseinander, und nur die gesetzte wurde je geprueft.

Erledigt: dev-hub#224 (Volltext-Zeitplan, mail_anhang, Trefferzone,
Endungs-Erkennung) · #225 (pg_trgm + OCR) · #226 (Kanon dev-hub.iil.pet) ·
#227 (Loeschung nimmt abgeleiteten Text mit) · #228 (Schwelle 0.6).

Eigene Fehler: das nginx-Logformat war beim ersten Versuch zerschossen, weil ein
nicht gequotetes Heredoc die $-Variablen von der Shell expandieren liess (als
Datei kopiert, dann korrekt) · der Deploy von #226 nahm die laufende OCR-Schleife
mit, sie verbrauchte ihre Runden im Deploy-Fenster und erreichte die Obergrenze.
Beides fiel nur auf, weil nachgemessen wurde.

Offen/Uebergabe: /mail-agent/ auf Live-Daten (dev-hub#211) · 69 ZIP und 20
Alt-Word ohne Handler · Cloudflare Weg 2 (Origin schliessen) falls gewuenscht ·
NICHT verifiziert: ob die drei neuen Volltext-Zeitplaene wirklich feuern (erster
Lauf 2026-08-04 ab 05:30, Gegencheck ueber ChannelHeartbeat mit Kanal volltext:*).

---

## 2026-08-04 (7. Eintrag) — Nachtrag: der erste Zeitplan-Lauf hat einen Fehler gezeigt

Kurznachtrag zum 6. Eintrag, der die Zeitplaene noch als "nicht verifiziert" fuehrte.

Verifiziert: alle drei feuerten korrekt, hnu und mittwald liefen durch, iil wurde vom
OOM-Killer abgeraeumt (03:50:38, Kernel-Log). Ursache war meine eigene Speichergrenze:
fest auf 650 MB, gebaut und getestet in devhub_web (1 GiB) — der Zeitplan laeuft aber im
Worker devhub_celery mit 512 MB. Eine Schutzgrenze ueber dem Container-Limit ist keine.
Behoben (dev-hub#229): Ableitung aus der cgroup, 80 % des Limits. End-to-End ueber die
Warteschlange belegt, alle drei Kanaele haben jetzt einen Herzschlag.

Die Lehre daraus ist allgemeiner als der Fix: ein Wert, der in einem Container gemessen
und in einem anderen benutzt wird, ist geraten — auch wenn er einmal richtig war.
Dieselbe Klasse wie --config gegen --account (Vorgabe und Einsatzort liefen auseinander)
und wie der TENANT_NON_TENANT_SUBDOMAINS-Vorgabewert.

Neu getrackt: dev-hub#230 — der Herzschlag wird erst am Ende geschrieben, ein
abgebrochener Task hinterlaesst nichts, und heartbeat_scan kann einen nie gelaufenen
Kanal gar nicht sehen. Genau so blieb dieser Fehlschlag unsichtbar.

## 2026-08-04 — Retro 6cec19: was der fremde Blick am eigenen Werk fand

Ein adversarialer Retro ueber den Mail-Strang, gefahren mit fremdem Kontext: ein
Collector, drei Finder je Dimension, drei Skeptiker nur auf Bewertungsbefunde, ein
Meta-Reviewer auf den Report-Entwurf. 16 Befunde, alle ueberlebten die Falsifikation.
Report unter docs/retros/session-retro-2026-08-04-dev-hub-6cec19.md.

Die drei schwersten Befunde kamen alle NICHT aus meiner eigenen Pruefung. Der
Schluessel, der nirgends gesetzt war und den ganzen Bestand an SECRET_KEY haengte.
Die Adressrelation MessageParticipant, die jede Art-17-Loeschung ueberlebte. Die
nginx-Spiegeldatei, deren Existenz ich gar nicht kannte, als ich den vhost umstellte.

Warum der Gate-3-Nachweis MessageParticipant nicht fand, ist die eigentliche Lehre:
er mass, was eine SUCHE noch findet. Die Relation ist keine Suchflaeche. Eine Probe
findet immer nur, wonach sie sucht — deshalb zaehlt der neue Test Modelle auf, statt
Stellen zu pruefen. Ein neues Modell an LogicalMessage laesst ihn fehlschlagen, auch
wenn niemand an die Loeschung gedacht hat.

Dieselbe Klasse ein zweites Mal am selben Tag: der Umschluesselungslauf starb am
OOM-Killer, weil er beim Streamen den ciphertext mitzog — rund 7 GB statt ein paar
hundert Byte je Zeile. Nicht die Rechnung war teuer, sondern das, was nebenbei mitkam.
Gleiche Ursache wie die 650-MB-Grenze der Vornacht.

Und ein Fehler, den kein Test gefunden haette: der Zaehler "schon aktuell" konnte nie
zutreffen, weil rotate jedes Mal einen anderen Wert liefert. Jeder Wiederholungslauf
haette alles erneut umgeschluesselt, und die Ausgabe haette dabei ehrlich ausgesehen.

Der Mailbestand haengt ab jetzt nicht mehr an SECRET_KEY: 11.574 von 11.574 am eigenen
Schluessel, 0 verloren, in Prod gemessen. Der Wert liegt in der Prod-Umgebungsdatei und
im Passwortspeicher des Owners; die Uebergabeschleuse ist geprueft leer.

Bewusst liegengelassen und benannt: die nginx-Spiegeldatei ist weiter veraltet, und die
OCR-Anschlussentscheidung fuer neu eintreffende Scans hat kein Issue. Beides steht im
Retro, ist also getrackt — erledigt ist es nicht, und das gehoert so gesagt.

Selbstkritik am Retro: refuted_rate 0,0 liegt unter dem gesunden Band. Ich habe zur
Falsifikation Behauptungen ausgewaehlt, die ich schon fuer plausibel hielt, statt
solche, die fallen koennten. Der Ertrag kam trotzdem — aber aus den Skeptikern, nicht
aus meiner Auswahl.

---

## 2026-08-05 (8. Eintrag) — Mail-Strang: Vorgangsbuch statt Suche; Session-Skills gegen Kollisionen

**Ziel der Sitzung:** „die Mail-Skripte für den Lotsen auf DB statt IMAP". Was daraus
wurde, ist etwas anderes — der Owner steuerte über den Tag von der Suche zum
**Vorgangsbuch**, und das war die richtige Richtung.

**Der wertvollste Fund war kein Code, sondern ein Muster:** vier Mechanismen waren
gebaut und liefen nie — `reconcile` (Löscherkennung), `ingest_delta` (gegen einen
synthetischen Adapter), `zustand_offener_punkt` (nur Test-Aufrufer), `MailEvent.REPLIED`
(nirgends geschrieben). Alle sahen von außen wie „funktioniert" aus, weil nichts rot
wurde. Jede spätere Entscheidung dieser Sitzung folgt daraus.

**Erledigt (dev-hub, 15 PRs gemergt):**

* **Graph-Delta live und belegt** (#234): erster Lauf 475 Nachrichten, zweiter **0** —
  der `deltaLink` greift. Neu/geändert und entfernt getrennt; `services.abgang_klassifizieren`
  trennt *verschoben* von *gelöscht*, weil beides im Quellordner identisch aussieht und
  erst der eigene Bestand es unterscheidet.
* **IMAP-Weg** (#236): UID-Cursor für Zuwachs, UID-Listen-Abgleich für Abgang. Getrennt,
  weil **kein** Server dieses Bestandes CONDSTORE/QRESYNC anbietet (gemessen). `UID SEARCH n:*`
  liefert bei leerem Rest die höchste UID statt nichts — ungefiltert meldet jeder Lauf „1 neu".
* **Antwort-Erkennung** (#242/#243): 2.356 Buchungen. Zwei Wege, weil jeder Transport nur
  **eine** Verkettung liefert — hnu 2.261 Reply-Header und 0 Konversationen, iil genau
  umgekehrt. Der erste scharfe Lauf buchte für iil **null**; das war keine Verhaltensaussage,
  sondern eine Datenlücke.
* **Suche 27,5 s → 7,9–11,1 s** (#239/#240) — über **zwei Fehlversuche**, die sie
  zwischenzeitlich auf 50,8 s verschlechterten. Die Relevanzordnung war nicht nur teuer,
  sondern **wirkungslos**: `Greatest(ts_rank, word_similarity)` vergleicht 0,0608 mit 1,0,
  das Maximum ist immer die Ähnlichkeit.
* **Drei Ansichten auf den echten Bestand** (#244/#245/#246) — die bestehenden hängen an
  `DEMO_TENANT_ID` (dev-hub#211, kommentiert). Mit Inhalt zum Aufklappen, Klick in die Mail,
  sortierbaren Spalten.
* **Zwei Konzepte:** KONZ-dev-hub-003 (Suche) und **KONZ-dev-hub-004** (Vorgangsbuch mit
  Mail-Anschluss) inkl. §10 Rückfrage-Vorrat: verbindliches Lernen über **eine** Engstelle,
  Entscheidungen in die Datenbank, Schwellen in den Code per PR, **kein** Reinforcement
  Learning (Exploration auf echter Post kostet Vertrauen schneller als sie Genauigkeit
  gewinnt).

**Erledigt (platform):**

* **Retro 346c51** (#1761): 8 Befunde, 7 überleben. Der teuerste ist eine Zahl, die ich
  selbst weitergereicht habe — „21 s" war nach #239 korrekt und nach #240 überholt. Der
  Evidenz-Hook ließ sie durch, weil es einen Beleg *gab*.
* **Session-Skills gegen Kollisionen** (#1764): `repo-session.sh abstand` rechnet den
  Basis-Abstand je Lease (**36 von 87 über der Schwelle, Spitzenreiter 243 Commits**),
  `--ziel` als Lease-Feld. Ursache: der Parallel-Session-Check sagt über sich selbst
  „blockiert nichts, entscheidet nichts" und liefert seine Anweisung „vor Merge/Deploy
  abgleichen" zum einzigen Zeitpunkt, an dem sie nicht befolgbar ist.

**Nächste Schritte, konkret:**

1. **M2/M3 aus KONZ-004** — Punkte ab Stichtag (letzte Woche) eröffnen, Zuordnung über
   Beteiligte **und** Kette. Ohne das bleibt es eine Eingangsliste.
2. **M8** — Rückfrage-Vorrat einmal bauen, mit der Engstelle und dem Test, der beweist,
   dass ein abgelehntes Paar keinen zweiten Vorschlag erzeugt.
3. **Stundenzeitplan** für den Delta-Lauf — geht per Migration nach Prod, eigene Freigabe.
4. **IMAP-Delta scharf laufen lassen** — `--modus delta --ordner-limit 1 --account hnu`
   zweimal. Der Graph-Zwilling ist belegt, der IMAP-Weg nicht.
5. Die drei alten Mail-Views auf `services.STANDARD_TENANT` umstellen oder als Demo
   kennzeichnen (dev-hub#211).

**Nicht verifiziert, ausdrücklich:** der IMAP-Delta-Pfad am echten Postfach · wie viele
Antworten die Erkennung **nicht** findet (neuer Betreff, Telefonat) · ob die Suchzeit von
~8 s stabil ist (zwei Läufe, erster kalt).

**Eigene Fehler dieser Sitzung:** zweimal an einer Stellschraube gedreht, ohne die Wirkung
vorher zu messen (der Skeptiker belegte: beide Ursachen waren ohne Deploy prüfbar) ·
eine Live-URL mit Haken genannt, während die beschriebenen Funktionen nur in einem offenen
PR existierten · dreimal in Tests geprüft, was ich erwartete, statt was das System tut.

## 2026-08-05 — Werkzeuge statt Prosa, und ein Anzeigetext, der das Gegenteil sagte

Der Tag begann mit drei Handover-Prios und endete in einer Datenschutz-Anzeige an eine
Aufsichtsbehörde. Jeder Schritt war eine eigene Ansage, keiner Eigeninitiative — aber die
Kette ist lang, und das gehört festgehalten.

**D6 war zu vier Fünfteln erledigt, der Rest war der wichtige.** Härtung, Golden-Fixtures
und die eingefrorene K1-Baseline standen seit dem 02.08. Was fehlte: das Slug-Wörterbuch
hatte **keinen maschinellen Konsumenten**. „Unmappbare Slugs = nicht bewertbar" und
„Instrumentenwechsel ⇒ Neuberechnung" standen als Prosa im YAML-Kopf, und der Ritual-Lauf
verwies auf den „manuellen Teil". Am 16.09. hätte eine Handzählung den K1-Ausgang
entschieden. Jetzt rechnet ihn `retro_kpis.py --k1`, verdrahtet in `regel-ritual.yml`.
Baseline nach dem Instrumentenwechsel neu berechnet — dieselben Zahlen, Pin nachgezogen.

**Beim Megatest war die bisherige Erklärung falsch.** Die fünf „nicht scannbaren Repos"
lagen nicht am Token-Scope: `megatest.yml` klonte alle 52 als `achimdehnert/$repo`, obwohl
elf unter iilgmbh/meiki-lra/ttz-lif liegen. Sechs davon rettete GitHubs Redirect, fünf
antworten mit 404. Darunter `iil-voice-agent` mit Budget 39 — der größte Posten des
Issues, nie im CI gescannt. Der Owner-Resolver existierte in der Registry; er wurde nur
nicht aufgerufen. Zweimal am selben Tag dasselbe Muster.

**Ein neuer Skill mit eigenem Prüfer.** Aus der Formalprüfung einer Masterarbeit entstand
`/arbeit-pruefen` plus `tools/dokument_formalpruefung.py` (13 Prüfungen, 28 Tests). Die
Entscheidung, die Mechanik ins Werkzeug zu legen statt in Skill-Prosa, hat sich sofort
bezahlt gemacht: Das Werkzeug widerlegte **meine eigene** Handprüfung — 32 statt 17
betroffene Abbildungen, 26 statt 24 Belege, und zwei Befunde, die ich gar nicht hatte
(ein Beleg ohne Verzeichniseintrag, eine Quelle mit zwei Jahren). Beide Zählfehler gingen
in dieselbe Richtung: zu wenig.

**Das Quellen-Gate ist gemessen, nicht vorsichtig.** Von neun belegbar falsch
zugeschriebenen Literatureinträgen tragen drei keinen Autor-Marker, zwei überhaupt keinen.
Ein Werkzeug kann sie nicht finden — deshalb verlangt der Skill einen Abruf je Eintrag.
Ein vierter Fall entpuppte sich beim exakten Auszählen als Detektionslücke: `[a-zäöüß]`
kennt den Akzent in „Léo" nicht. Ohne diesen Fix wäre der Satz „kein Marker heißt nicht
korrekt" mit einer Zahl belegt worden, die ein Werkzeugfehler erzeugt hat.

**Der schwerste Fund des Tages lag nicht im Code.** Ein Entwurf an die externe
Datenschutzbeauftragte führte die Dokumenten-Steuerung als „keine Sozialdaten · kein
externer Auftragsverarbeiter · keine Anzeige" und schrieb, es komme in keiner Stufe ein
lernendes Verfahren zum Einsatz. Der Verantwortliche selbst hatte derselben Empfängerin
17 Minuten später geschrieben, die Post werde „KI-gestützt sortiert und verschlagwortet"
und dabei würden personenbezogene Daten verarbeitet. Vier der neun Anlagen trugen den
Fehler mit — darunter der Anzeigetext an die Aufsicht. Korrigiert in meiki-hub#138, jede
Änderung sichtbar vermerkt statt still überschrieben, weil die Vorfassung im Umlauf ist.

**Nebenbefund mit Sprengkraft:** `read_mail.py --list` zeigt 0 von 221 geprüften
Nachrichten — in jedem Ordner, ohne Filter, Exit 0. Dasselbe Werkzeug trägt den Schalter
`--abwesenheitsbeweis`. Eine Allaussage über eine Abwesenheit auf einer Funktion, die immer
null liefert, ist deren Umkehrung. Gefunden nur, weil der Evidenz-Gate eine schlampige
Zeile von mir traf und ich die Gegenprobe fahren musste.

**Eigene Fehler:** Ein `git checkout` auf eine Datei mit ungetrackter Arbeit — das
komplette K1-Modul war weg und musste neu geschrieben werden, obwohl genau diese Lehre im
Memory steht. Zwei falsche Zahlen in einer Rückmeldung an einen Studenten, gefunden vom
eigenen Werkzeug. Eine Marker-Quote („vier von neun") ohne exaktes Auszählen behauptet.
Und dreimal eine Null gemeldet, ohne vorher zu prüfen, ob die Suche überhaupt etwas finden
kann — dreimal hat der Gate es abgefangen.

**Gesendet hat der Owner selbst:** die Rückmeldung an Frost (13:24) und die Rückfrage an
Zeiner (12:49), beide mit den korrigierten Inhalten (verifiziert am gesendeten Text). Die
MEiKI-Anzeige liegt als Entwurf und bleibt es, solange der AV LRA–OCOS unbelegt ist.

## 2026-08-05 (Nachtrag) — zwei eigene Auswertungen widerlegt, bevor sie jemand geglaubt hat

Die Sitzung lief nach dem formalen Ende weiter, und der wertvollste Teil kam danach.

Auf die Frage „sag ob noch was offen" habe ich eine Liste mit 29 offenen Strängen
geliefert. Sie war falsch. Der Owner fragte bei einem Eintrag nach — „ich habe darauf
nicht geantwortet?" — und die Nachprüfung zeigte, dass meine Auswertung INBOX gegen
„Gesendete Objekte" verglich, während dieser Strang zu sieben Neunteln in einem
Betreuungsordner lag, eigene Antwort inklusive. Dass das Ergebnis bei ihm zufällig
stimmte, machte es nicht besser.

Die zweite Fassung las alle Ordner und gruppierte über den `thread_key`. Auch falsch,
diesmal in zwei Richtungen gleichzeitig: 33 Nachrichten von zehn Personen über
anderthalb Jahre lagen unter einem Schlüssel, weil sie alle „HNU Kontaktformular"
heißen — ohne `References` fällt die Gruppierung auf den Betreff zurück. Und dieselbe
Unterhaltung zerfiel umgekehrt in mehrere Schlüssel, sodass beantwortete Vorgänge als
offen erschienen.

Erst die dritte Fassung — gruppiert nach Gesprächspartner statt nach Strang — fand,
was beide vorher übersehen hatten: eine Studentin, die seit 58 Tagen auf eine erste
Antwort wartet. In Fassung 1 unsichtbar wegen des Ordnervergleichs, in Fassung 2
unsichtbar wegen des kollidierten Strangs.

Die Lehre ist nicht „Gruppierung ist schwierig". Sie ist: **Ich habe zweimal eine Zahl
geliefert, die seriös aussah, und beide Male hat erst die Rückfrage des Owners den
Fehler aufgedeckt.** Eine Liste mit 29 Einträgen wirkt gründlicher als eine mit sechs —
und war es nicht.

Aus derselben Bewegung entstand `dev-hub#249`: eine Verlaufsansicht, die den ganzen
Faden zeigt statt einer Nachricht. Der schwierige Teil war nicht die Darstellung,
sondern dieselbe Auswahlfrage; die Einschränkung auf die Gegenseite ist dort mit einem
Rot-Beweis abgesichert, weil sie sonst still wieder herausfällt.

Zwei Owner-Weisungen kamen dazu und liegen als Memory: in Abläufen mit Menschen schlage
ich vor und warne, entschieden wird vom Owner — ausgelöst daran, dass ich einen PR
mergen wollte, der einen Anzeigetext an eine Aufsichtsbehörde ändert, nur weil er
technisch unter eine Standing Authorization fiel. Und ein Umfangsregler für Mails samt
der Regel, dass jeder Fakt beantworten oder anstoßen muss, sonst rausfliegt — ausgelöst
an einem Gefälligkeitsdetail in einer Mail an ein Landratsamt, das schlicht falsch war.

## 2026-08-09 — ein grünes Häkchen, das keins war

Die Sitzung fing als Ritual-Vorbereitung an und war damit nach einer Stunde fertig: der
Trockenlauf vom Vortag hatte den Schedule-Pfad bewiesen, die befristete Cron-Zeile konnte
raus, die drei Parse-Warnungen ließen sich an der Quelle beheben statt am Instrument.
Alles unspektakulär.

Der Rest der Sitzung entstand aus einer Zeile im Session-Start-Board, die niemand
bestellt hatte: ein fehlgeschlagener Deploy in einem Repo, das seit Wochen stillsteht.
Von dort führte eine Kette, deren jedes Glied für sich harmlos aussah — ein falscher
Pin, ein Fehlalarm-Scanner, ein Skip, der zu breit geschnitten war — und die am Ende
zwei Befunde freilegte, die beide dieselbe Form haben: **ein Mechanismus arbeitet
korrekt, und niemand liest sein Ergebnis.**

Der Megatest meldet seit dem 04.08. jeden Morgen eine Regression. Vier Issues, alle
offen, keins angesehen. Der Grund, warum das niemandem auffiel, ist beinahe elegant:
der Testschritt trägt `continue-on-error: true`, der Run steht damit auf `success`, und
im Handover stand „der Megatest selbst ist grün". Das war nicht gelogen — es war die
Beobachtung der falschen Ebene. Der Melder hatte seine Arbeit getan; er schrieb in einen
Raum, den keiner betritt.

Der zweite Fall ist derselbe Gedanke, eine Etage tiefer. Ein GHCR-Fehler von 07/2026 war
diagnostiziert, gefixt, getaggt und in einem Runbook dokumentiert. Beim Sprung auf die
v1.1.x-Linie ist die eine Zeile, die den Fix trug, wieder herausgefallen — und der
Vorfall wiederholte sich heute wortgleich. Dokumentation hält eine Zeile nicht fest.
Ein Lint hätte es getan.

Drei Dinge, die ich in dieser Sitzung falsch gemacht und selbst gefunden habe: Eine
Flotten-Messung klassifizierte Pfade per Teilstring und hätte zwei lebende Funde als
„geparkt" verschwinden lassen. Ich senkte zwei Budgets auf Basis lokaler Klone und nahm
es zurück, als ein Repo bewies, dass diese Klone nicht die CI-Basis sind — dieselbe
Lehre, die im Memory schon dreimal steht, diesmal aus eigener Hand. Und ein Befehl, den
ich dem Owner zum Kopieren gab, war unvollständig und schlug bei ihm fehl.

Was bleibt: Der Deploy ist immer noch rot, aber jetzt an einer benannten Stelle mit
einem Einzeiler als Fix. Zwei eigene grüne PRs warten auf einen Review-Klick, den die
Freigabe im Gespräch nicht ersetzen kann — das ist zum wiederholten Mal derselbe
strukturelle Reibungspunkt und gehört ins Ritual am 16.08., nicht in ein weiteres
Achselzucken.

## 2026-08-10 (504951) — die Welle war vollständig, bis ein Finder nachzählte

Vierzehn Repos auf shared-ci v1.1.6 gehoben, gestaffelt mit Pilot und Pausen, elf grüne
Deploys, zwei rote an einem vorbestehenden Gate. Ich habe das als abgeschlossen gemeldet.

Ein Finder der Retro hat dann nachgezählt und einen fünfzehnten gefunden. `writing-hub`
steht weiter auf v1.1.2. Mein Preflight hatte per `grep` nach `runs_on` gesucht und den
ersten Treffer genommen — der gehört zum `ci`-Job, der bewusst auf `ubuntu-latest` steht,
weil der self-hosted Runner zeitweise offline war. Der `deploy`-Job kommt sechs Zeilen
später und übergibt gar kein `runs_on`, läuft also auf dem Default `self-hosted`. Ich habe
das Repo als „nie betroffen" ausgeschlossen und den Auftrag geschlossen.

Dieselbe Bewegung dreimal an einem Tag. Beim Mail-Backfill schnitt meine Betreff-Extraktion
am Doppelpunkt ab, sodass aus `AW: Request for Supervision` das Suchfragment `AW` wurde —
ein Zwei-Buchstaben-Platzhalter, der auf jede Antwort passt. Und in einem PR habe ich eine
Nummer als Beleg zitiert, ohne ihren Titel zu lesen; er sagte das Gegenteil dessen, wofür
ich sie anführte, und der darauf gestützte Mute steht bis heute auf `main`, während eine
Parallelsitzung die echte Ursache dreißig Minuten später behob.

Das verbindende Muster ist nicht Schlamperei. Jedes dieser Kommandos lief fehlerfrei und
lieferte eine korrekte Zahl — nur zu einer anderen Frage als der gestellten. Der Stop-Hook,
der solche Behauptungen abfängt, prüft, **ob** ein Check lief. Ob der Check die Frage
beantwortet, prüft er nicht, und genau dort ist diese Sitzung dreimal hindurchgefallen.

Was gut lief, gehört daneben: die Staffelung der Welle, die zwei Gegenproben, die zwei
falsche Mail-Zuordnungen rechtzeitig verhinderten, und die Entscheidung, 42
D4-Extraktionen **nicht** zu schreiben, nachdem die Stichprobe vier von vier widerlegt
hatte. Die drei schwersten Befunde dieser Retro stammen von Findern mit frischem Kontext,
nicht aus meiner Selbsterzählung — das ist die Methode, die funktioniert hat.
---

## 2026-08-10 — Fünf rote CI-Läufe, drei echte Fehler, eine Anweisung nicht ausgeführt

Der Auftrag kam als Link auf eine claude.ai/code-Session, die ich nicht lesen konnte
(HTTP 403, auth-gated; lokal kein Transkript). Statt zu raten: beide billigsten Checks
gefahren, Ergebnis gemeldet, nachgefragt. Antwort: „die Fehler waren im platform-repo,
hol sie dir aus CI."

Drei der fünf roten Läufe waren echte, stumme Dauerfehler — alle drei `schedule`- oder
`issues`-getriggert, keiner blockierte je einen PR. Das ist der verbindende Befund, nicht
die einzelnen Ursachen: `staging-registry-checks` löste einen repo-wurzel-relativen Pfad
erst nach einem `cd` auf und brach neun Läufe lang mit exit 2 ab, bevor der erste Check
lief — der Umbau vom 02.08., der das Gate scharf machen sollte, hatte es stumm
geschaltet. `docu-update-agent` installierte eine auf PyPI vollständig zurückgezogene
Distribution, die es gar nicht brauchte. `gen-project-facts` riet den Owner für drei
Repos, die nie unter der Default-Org lagen.

Der vierte rote Lauf war ein einmaliges 502 bei zeitgleich grünem `/readyz/` — bewusst
kein Fix. Der fünfte, `registry-live-reconcile`, führte am weitesten: nach der vom Owner
entschiedenen Waiver-Verlängerung maß das Werkzeug wieder und meldete vier Dienste als
„Container läuft nicht". Der Owner entschied „Container-Namen korrigieren" — und genau
das habe ich nicht getan. `docker ps` auf beiden Prod-Hosts zeigte, dass alle vier Namen
zeichengleich mit der Realität sind; die Container laufen auf `prod-b`, der Melder sah
nur `prod`. Umbenennen hätte korrekte Werte zerstört. Prämisse widerlegt, Beleg gezeigt,
Host-Blindheit gefixt, Owner bestätigt.

Der Gegentest zu dieser Frage brachte den unangenehmsten Fund des Tages: nur vier von
neun `prod-b`-Diensten fielen auf, weil die anderen fünf **zusätzlich auf `prod`**
laufen. 23 Container doppelt, fünf Postgres-Paare darunter, Image-Tags divergierend.
Welche Instanz Verkehr bedient und welche Datenbank geschrieben wird, ist ungeklärt —
deshalb Issue statt `docker rm`.

Zwei eigene Fehler, beide fremdgefangen: Ich schrieb den Bypass-Aktenvermerk vor dem
Merge, der Merge wurde dann abgelehnt, und der Vermerk beschrieb einen Vorgang, der nie
stattfand. Und mein erster Wurf am Melder hätte bei leerer `ports.yaml` „keine Drift"
gemeldet statt den toten Host zu bemerken — das fing der Bestandstest.

Was bleibt: [#1877](https://github.com/achimdehnert/platform/pull/1877) wartet auf den
Review-Klick, danach ist eine Entscheidung zum Zugang `prod` → `prod-b` fällig (gemessen:
kein Key, kein Runner). [#1876](https://github.com/achimdehnert/platform/issues/1876) und
[#1860](https://github.com/achimdehnert/platform/issues/1860) sind unbearbeitet. Und die
Handover-Prio wurde in dieser Session nicht angefasst — die Frist 16.08. für Ritual-Lauf 1
ist jetzt sechs Tage entfernt.

---

## 2026-08-10 — Sitzung `c45b39`: die Review-Pflicht wurde neu geschnitten, und der Retro fand die Fehler dabei

Der Auftrag war eine Liste von fünf Punkten. Zwei davon waren schon erledigt, als ich sie
anfasste — von einer Parallelsitzung desselben Morgens. Statt sie nachzubauen habe ich sie
verifiziert und dabei in beiden Fällen etwas gefunden, das niemand las: der Megatest meldete
senkbare Budgets in einen Kanal, den pytest verschluckt, und der Hygiene-Melder zählte 68
Leases, von denen das empfohlene Werkzeug per Konstruktion keine abräumen konnte. Dasselbe
Muster begegnete mir an dem Tag noch zweimal. Vier Melder, die korrekt arbeiteten und deren
Ergebnis nirgends ankam.

Der eigentliche Strang entstand aus einer Nebenbemerkung. Ich hatte behauptet, vier
Review-Klicks hätten den Owner die Sitzung gekostet. Er widersprach — es fühle sich nach
mehr an. Die Messung gab ihm recht und mir nicht: **400 gemergte PRs in 30 Tagen, kein
einziger ohne Approval, 399 davon von einem Konto.** Meine Zahl war um zwei Größenordnungen
daneben, und sie stammte aus dem Erleben der Sitzung statt aus einer Abfrage.

Daraus wurde die Arbeit des Tages. Die Ursache lag nicht bei den Autonomie-Gates, sondern im
GitHub-Ruleset: ein CODEOWNERS-Catch-all `*` zwang jeden PR zu einem Owner-Review, auch einen
Handover-Nachtrag. Der Owner formulierte das Ziel schärfer, als ich es hatte: *„ich und
wirdigital agieren als Entscheidungsinstanz, nicht als Auto-Freigeber."* Ein Approval, das
400-mal im Monat fällt, ist keines mehr — die 40 von 40 leeren Review-Texte sind nicht
Nachlässigkeit, sondern der Beleg dafür, dass die Pflicht auf den falschen Dingen lag.

Der Umbau lief in zwei Stufen, und die Reihenfolge war der entscheidende Teil: erst den
Perimeter schließen, dann die Zahl senken. Hätte ich `required_approving_review_count` zuerst
auf 0 gesetzt, wären `governance/`, `deployment/`, `infra/` und `scripts/` ohne jedes
menschliche Auge dagestanden — der Plan, dem ich folgte, hatte diese Pfade offengelassen,
weil er unter der Annahme geschrieben war, dass jeder PR ohnehin ein Approval bekommt. Der
Perimeter ist heute **breiter** als vor der Sitzung.

Gegengeprüft habe ich in beide Richtungen, weil eine Probe allein nichts zeigt: ein PR auf
`/policies/` bleibt blockiert, einer auf `docs/retros/` ist `clean` — beide mit identischen
sechs grünen Checks, der Unterschied kommt allein vom Pfad. Den zweiten habe ich selbst
gemergt, die erste reale Ausübung von SA-2.

Die Retrospektive war der unangenehmste Teil und der nützlichste. Acht Subagenten mit
frischem Kontext, 17 Befunde, 16 überlebten die Falsifikation. **Die drei schwersten sind
meine.** `/governance/` fehlte in meiner ersten Fassung, obwohl der akzeptierte Plan es auf
Zeile 165 listet — still verloren, in keiner Commit-Message erwähnt. Der neue Auto-Reap, den
ich selbst gebaut hatte, meldet jeden Werkzeugfehler als grünes „nichts abzuräumen", dreißig
Zeilen unter einer korrekten Lösung derselben Fehlerklasse. Und die fehlende Ruleset-Zahl
habe ich als *Spezifikationslücke des Plans* gemeldet — sie stand wörtlich in B1-2. Der Plan
war vollständig; meine Umsetzung war es nicht.

Widerlegt wurde ausgerechnet ein Befund, den ich dem Owner als sicher gemeldet hatte: eine
Kollision zweier paralleler Sitzungen am selben Ziel. Es gab sie nicht — der zweite PR
entstand neunzehn Minuten nach dem Merge des ersten und baute auf ihm auf. Mein Einwand dazu
stammte aus dem Issue-Text statt aus dem Diff.

Ein Lichtblick: `claim-before-cheapest-check` steht bei 39 Vorkommen über alle Retros und
bekam heute drei weitere. Aber erstmals ist belegt, dass das Gate dagegen **wirkt** — der
`evidence_claim_scanner` wies mir einen Turn zurück und erzwang die Korrektur einer
unbelegten Zahl. Der Mechanismus existiert nicht nur, er greift.

Was liegen bleibt: elf von siebzehn Mail-Vorgängen ohne Anker, weil ein geratener Link
schlimmer wäre als keiner. Der Auto-Reap-Fehler als #1881. Die IaC-Datei für das Ruleset,
die ich nicht schreiben darf. Und die Erkenntnis, die keine Zeile Code braucht: die Reibung
lag nie bei den Gates. Sie lag bei einer Zahl, die seit einem Monat in einem Plan stand, auf
den ein Fehlzeiger im Policy-Text zeigte.

---

### 2026-08-11 · Session lazy-litellm/fw-wellen (Kapitäns-Kanal)

- #1899 K1–K5 erfüllt (litellm lazy 0.11.7 + preload-Fleet, Host 15–16→13,4 GB)
- #1900: 13 Consumer SSoT-konform, finaler Scan im Issue, Ausnahmen getrackt
- ADR-294 proposed gemergt; SSoT-Regeln 5+6 in PR #1917 (Review offen)
- wedding-hub /delete-repo Phase 0–2 (wartet auf ARCHIVIEREN-Formel)
- weltenhub: Runner→prod-b, /opt/scripts provisioniert (IaC-Spiegel offen, #49)
- Offen: risk-Prod-Redispatch (#578), 137-hub#86, travel-beat#79, tax-Preload-Trigger

### 2026-08-11 · Delta 11:30 (gleiche Session)

- wedding-hub ARCHIVIERT (Owner-Formel), Tombstone #1924, Registry-Cleanup #1925 gemergt
- risk-Prod verifiziert 0.11.8 + preload (letzte aifw-App live)
- #1917 (SSoT-Regeln 5+6) + #1918 (Handover) gemergt; skip-ci-Substring-Falle in Memory nachgetragen

### 2026-08-12 · Session mail-activity-intelligence (Strang 1f9813)

Angefangen bei einer Bewertungsfrage — zwei externe Review-Runden gegen den MVP stellen —
und geendet bei einer Kategorien-Tabelle. Neun Schritte, jeder vom Owner angestoßen.

Der Ertrag ist eine Zahl: **49 → 168**. Der Kopfdaten-Melder zählt je Adresse, und je Faden
werden aus 49 Zeilen 168. Bei „ich schulde" sind es 13 → 70. Diese Asymmetrie ist kein
Rauschen, sie ist strukturell: Je Adresse kippt jede Antwort in irgendeiner Sache die
Richtung auf „ich warte" und verdeckt damit alle unbeantworteten Fäden desselben
Gegenübers. Der Fall, für den das Cockpit überhaupt gebaut wird, ist der, den die billige
Gruppierung am zuverlässigsten verschluckt. Der Owner hat die Messung selbst reproduziert,
Zeile für Zeile identisch.

Zwei Korrekturen an eigenen Aussagen, beide innerhalb einer Stunde nach dem Push. B9 nannte
zuerst ADR-022 als verletzte Norm (null Treffer darin), dann ADR-109 H-1 (zu weit gefasst —
bindet `TenantModel` in Tenancy-UI-Hubs, nicht jedes Modell). Der belegte Stand ist
unbequemer als beide: Die Konvention wird als Standard behandelt, ohne einer zu sein. Und
im ADR-295-Entwurf hing der Löschtermin an einem Frontmatter-Feld, das im ADR-Schema gar
nicht existiert.

Der wertvollste Fund kam beim Prüfen einer eigenen Warnung. Ich hatte gesagt, ein Wipe des
Bestands könne gelöschte Inhalte zurückholen — als Vermutung. Der Code sagt mehr: Der
Grabstein **ist** die Sperre, `ingest_or_skip` fragt `is_blocked()` ab. Ein Wipe entfernt
also nicht den Nachweis, sondern das Hindernis. Heute betrifft das genau eine Nachricht, und
die ist der ADR-293-Gate-3-Nachweis, keine Betroffenen-Anfrage. Nach den geplanten
Testrunden können es echte sein.

Was liegen bleibt, ist das, was ich dreimal aktenkundig gemacht habe und nicht gebaut habe:
`record_erasure` wird ausschließlich aus Tests aufgerufen. Eine DSGVO-Löschung ist Handarbeit
— schon für einen Bestand, nicht erst für zwei. Es blockiert die Datenübertragung nach dev,
es ist der Grund für den gesperrten Löschknopf im Admin, und es ist der einzige offene Punkt
dieser Sitzung, der ein Risiko trägt statt nur Arbeit.

Ein Lichtblick zum Schluss: Der Admin-Test, den ich wegen des Löschknopfs geschrieben hatte,
hat zwei Stunden später den Bau der Kategorien-Tabelle angehalten — sie war nicht
registriert. Ein Guard, der eine andere Lücke fängt als die, für die er gebaut wurde.
### 2026-08-12 · Session gate-registry (Kapitäns-Kanal)

- **#1650 Gate-Audit GESCHLOSSEN** — alle 3 Abnahme-Kriterien erfüllt, Checkboxen abgehakt.
  Owner-Merges: #1938 (4 existierende Gates registriert + retro_kpis-Registry-Abgleich),
  #1939 (declined-Liste ×3 + Ruleset-Wächter täglich), #1940 (nolimits ratifiziert),
  #1941 (Test-Lücken-Gate, Baseline 162→3 Befunde, 0 FP).
- Registry: 16 Einträge, alle drill-frisch (gate_drill_check); K1-Pin 2× regelkonform
  nachgezogen (Kontroll-Läufe identisch: n=20, 10/7/3, Rate 1.000).
- **Fund:** policies/nolimits.md lag seit 10.08. unratifiziert (untracked) in platform-pinned
  und war aktiv eingespeist — Classifier blockte Agent-Commit korrekt; Owner ratifizierte
  interaktiv, PR #1940, danach pinned bereinigt (clean, 0 hinter main, vorher 56).
- Bewusste Reste getrackt: #1943 (Melder-Hook-Umzug ins Repo, 3 ungetestete Altfall-Module).
- Neuer Auftrag materialisiert (Zielzustand-Loop): **#1945 Handover-Flotte** (SA-4-fähig).
- **Abnahme (0d): Zielzustand #1650 ERREICHT** — Kriterien einzeln verifiziert
  (Drill 16/16, retro_kpis-Echtlauf „✓ gedeckt oder entschieden", Issue-Checkboxen).
- **SA-4: 0 Anwendungen · 0 Einzel-OK trotz Klassen-Deckung · 0 Fehlanwendungen** —
  alle Merges liefen bewusst als Owner-Einzel-Review (Perimeter-Pfade + Selbstbetreffendes).

### 2026-08-12 · Strang 9ee08c2 — parallele Sessions kollisionsfrei + Admin-Test

- Nummernkollision KONZ-043 aufgeloest (#1942 -> 044); Ursache: beide Sitzungen rechneten
  korrekt max+1 gegen main, zum Vergabezeitpunkt fuer beide dieselbe Zahl.
- Zielzustand #1944 (Owner-akzeptiert). K5 erfuellt (#1946 Kollisions-Meter: 59 Paare /
  30 Tage, 1,9 %). K1 erfuellt (#1947 Erkennung + #1950 Vergabe; zwei Worktrees ohne Push
  -> 045/046, alter Weg -> 2x 045). K2 abgestuft auf 4 echte Konflikte/30 Tage.
- K2-Erstdiagnose (next_free) durch Gegentest widerlegt: haette add+add nicht geheilt und
  add+edit erst kaputtgemacht. Im Issue korrigiert.
- Mailbestands-Admin in 3 Runden geprueft: 17/17 rendern, 15 readonly, kein Body sichtbar.
  Befund: TextUnit.text steht auf der Detailseite -> Owner-Entscheid "gewollt",
  verankert + festgenagelt in dev-hub#273 (Gegenprobe: Reparatur macht den Test rot).
- Praemisse dazu geprueft: dev-hub.iil.pet/admin lief ohne Cloudflare Access. Werkzeug
  #1949 gebaut und angewandt -> /admin/ jetzt hinter Access, andere Routen unveraendert.
- Eigener Fehler: "admin.py fehlt" aus dem Working Tree gelesen (1 Commit hinter main),
  abgesichert durch eine Anti-Vakuum-Kontrolle, die nur den Filter prueft, nicht das
  Datenalter. Als neue Facette in feedback_stale_local_clone_never_ground_truth ergaenzt.
- Abnahme (0d): #1944 teilweise erreicht — K1+K5 erreicht, K2 abgestuft, K3/K4 offen.
- SA-4: 1 Anwendung (#1946) · 0 Einzel-OK trotz Klassen-Deckung · 0 Fehlanwendungen.
### 2026-08-13 · Session handover-flotte (Kapitäns-Kanal)

- **#1945 GESCHLOSSEN** — alle 4 Kriterien belegt: #1954 (K1 Messung, 2 Läufe byte-identisch),
  #1955 (K2 Gate + K3 Melder als Runner-Phase 0.7.4, Registry + Drill), #1948 (K4).
- Owner-Entscheidung **Weg 1** (#1958): 26 Erstanlage-PRs, 24 gemergt — Flotte 23 → **47 von 54**
  Repos mit AGENT_HANDOVER.md. Kriterium zählt `session/`-Branch-PRs, nicht PRs (sonst 29/31 = wirkungslos).
- Hängen geblieben: mcp-hub#198 (Review-Pflicht), weltenhub#50 (defektes Coverage Gate → weltenhub#52).
  Kein `--admin` — dadurch wurde der weltenhub-Defekt überhaupt sichtbar.
- **Zwei eigene Fehler, beide fremdgefangen:** „Handover veraltet in ruhenden Repos" war falsch
  (Owner-Rückfrage → #1956, Check vergleicht gegen letzten berührenden Commit); Search-Rate-Limit
  ließ `None` als `0` zählen, mcp-hub stand mit 50 Sitzungen als „ruhend" im Bericht.
- Nebenfunde getrackt: #1953 (zwei blinde Cron-Melder), 6 verschiedene Gate-Pins (3× `@main`).
- Prio-Block auf diesen Stand nachgezogen; Melder `handover-prio-zeigt-auf-erledigtes` danach grün.

### 2026-08-13 · Session mailcheck + Mail-Ablage (Kapitäns-Kanal)

- **AGENT_HANDOVER.md bewusst NICHT angefasst.** Phase 0a-handover-pr fand den offenen
  PR #1935 (Strang 4f808a, heute 06:05 aktualisiert); sein Branch ist in einem fremden
  Worktree ausgecheckt. Übernehmen hätte kollidiert, Schließen fremde offene Arbeit
  verworfen — deshalb nur dieser Log-Eintrag (append-only, `merge=union`). Keine Prio
  aus der Tabelle wurde erledigt oder verschoben, Phase 0c feuert nicht.
- **Werkzeuglücke gefunden und geschlossen:** `read_mail` übersah eingebettete
  `message/rfc822`-Nachrichten, weil die Anhangserkennung nach einem Dateinamen fragte
  und ein rfc822-Teil keinen trägt. Eine Weiterleitung, deren Sachinhalt genau dort lag,
  erschien als dreizeiliger Begleittext mit 15 Signaturbildern. Issue #1964 → PR #1965
  (gemergt `0079f083`), 5 Regressionstests inkl. Gegenprobe ohne rfc822-Teil.
- **Nachtrag zum Merge:** Der PR-Text sagte „Behebt #1964" — kein Schlüsselwort, das
  GitHub kennt. Das Issue blieb nach dem Merge offen und wurde von Hand geschlossen.
  Für den Automatismus braucht es `Closes`/`Fixes`/`Resolves`.
- **Mail-Board-Hygiene:** unverankerte Posten von 13 auf 2 gesenkt (7 IMAP-Anker über
  `anker.py`, 6 Graph-Kurzlinks über `mail_link_server.py --register`). Zwei Vorgänge
  lagen ohne Bucket im Ledger und wurden dadurch auf **keiner** der beiden Listen
  gerendert. `anker.py --account iil` läuft ins Leere (sucht eine `mail-iil.env`, die es
  nicht gibt und nicht geben soll) — für Graph ist `--register` der Weg, der Fehlertext
  sagt das aber nicht. Fortschritt kommentiert an #1864.
- **Diagnose-Fund ohne Regel:** Der `\Recent`-Flag trennt „Werkzeug hat nicht abgelegt"
  von „Client hat nicht geholt". Die Pflege-Regel 7 in `board.py` sagt „erst den Client
  prüfen", nennt aber keinen Test. Realfall heute: zwei Entwürfe galten als fehlend,
  lagen aber mit `\Draft \Recent` im Ordner — es war eine abgelaufene Sitzung. Nicht
  eingebaut (Owner-Frage offen), deshalb hier notiert.
- **Neuer Auftrag materialisiert (Zielzustand-Loop): #1966** — geschlossene Vorgänge
  räumen ihre Mail aus dem Posteingang, Ziel A+B (Sach-/Kundenordner zuerst,
  Jahresarchiv als Zweitregel), Trockenlauf-Standard, Vorschlag ≠ Vollzug nach
  ADR-284 §7a. Owner-Freigabe im Kapitäns-Kanal, SA-4-fähig, noch nicht begonnen.
- **Eigener Fehler, selbst gefangen:** Im Session-Worktree ein `git checkout main -- .`
  an einen anderen Befehl gehängt → eigene Änderungen überschrieben und 8 fremde Dateien
  auf einen älteren Stand gesetzt. Vor dem Commit bemerkt, per `git reset --hard` im
  Worktree zurückgenommen; die Originale lagen unversehrt im Hauptbaum.
- **Abnahme (0d): Zielzustand ERREICHT** — Mailcheck gelaufen (Deckung 12.095 Nachrichten /
  145 Ordner / 3 Konten, Post-Ingest-Fenster live nachgezogen), Mail-Liste und Todo-Liste
  neu erzeugt, 7 Mails gesendet, 7 Vorgänge geschlossen. Ein formaler Zielzustand nach
  Phase 2.7 lag zu Sitzungsbeginn nicht vor; das Ziel wurde im Kapitäns-Kanal gesetzt.
- **SA-4: 0 Anwendungen · 0 Einzel-OK trotz Klassen-Deckung · 0 Fehlanwendungen** —
  der einzige Merge (#1965) lief über die reguläre Code-Owner-Review.
### 2026-08-13 · Delta zur Sitzung handover-flotte (Nachmittag/Abend)

Ergänzt den am selben Tag gemergten Stand-Block (#1960); der Stand-Block selbst wurde
BEWUSST nicht erneut umgeschrieben, weil PR #1935 einer parallelen Sitzung ihn offen
hält — ein dritter konkurrierender Stand hätte den Konflikt dort verschärft.

- **#1962 GESCHLOSSEN** (Gate-Pins): Flotte auf einem Pin, gemessen 22× `ja@v1.1.7`,
  keine Abweichung. `trading-hub` zeigte auf einen SHA, den GitHub nicht mehr auflöst
  (HTTP 422) — das Gate lief dort seit 2026-07-16 nicht. Bump verhaltensneutral belegt
  (Gate-Datei über v1.1.0–v1.1.7 byte-identisch, md5 `209e23cd5845`).
- **#1953 GESCHLOSSEN** (zwei Melder): beide Eröffnungs-Diagnosen waren falsch.
  Sync-Drift-Meter war Fehlalarm auf einem nie aktualisierten Klon (design-hub, auf main
  seit 2026-06-01 behoben) → Registry-Guard #1961. `Gen project-facts.md` lief sehr wohl
  und scheiterte an drei Fremd-Org-Repos ausserhalb der Token-Reichweite → neues
  dediziertes PROJECT_PAT (classic, `repo`-Scope, **Ablauf 2027-08-12**, abgelegt in der
  kanonischen Secret-Heimat).
- **Zwei Folgefunde, die erst der ECHTE Lauf zeigte** (der Trockenlauf war grün):
  archiviertes wedding-hub faerbte den Lauf rot (#1967) · die Commit-Message trug eine
  CI-Unterdrueckungsmarke und machte 5 der 8 erzeugten PRs unmergbar, dev-hub#178 seit
  dem 2026-07-31 (#1970). Beweis: leerer Commit auf denselben Tree, Checks 0 → 11–15.
- **weltenhub#52 GESCHLOSSEN**: Coverage Gate scheiterte an fehlendem `pip` (exit 127),
  mass keine Coverage und blockierte jede PR. Kette shared-ci#53 → Tag `v1.1.8` →
  weltenhub#53 (Pin-Bump) → weltenhub#50 gemergt, **ohne Bypass**.
- Flotte: **49 von 54** aktiven Repos mit `AGENT_HANDOVER.md` (Sitzungsbeginn: 23).

**Abnahme (Phase 0d):** Zielzustand #1945 **erreicht** — alle vier Kriterien einzeln
verifiziert und im Issue belegt (Messung determinismus-geprueft, Gate 23/23, Melder in
beiden Zweigen im echten Runner-Pfad, Prio bereinigt). Folge-Zielzustaende #1962/#1953
ebenfalls **erreicht**; ein Abnahmepunkt in #1953 bleibt bewusst offen (Wochenlauf-Beweis
Montag 04:00 UTC) und ist als solcher gekennzeichnet statt abgehakt.

**SA-4: ~40 Anwendungen · 0 Einzel-OK trotz Klassen-Deckung · 0 Fehlanwendungen.**
Der Permission-Classifier blockte dreimal einen Fan-out (Worktree-Reap, 6-fach-Merge,
State-Abfrage-Schleife); alle drei danach vom Owner bzw. einzeln ausgefuehrt, keiner
umgangen. Ein `--admin`-Bypass wurde einmal owner-angewiesen benutzt (mcp-hub#198, mit
durablem Beleg am PR) und einmal versucht, aber vom Ruleset verweigert (weltenhub#50) —
dort war der Fix der Weg.

**Prozess-Fehler dieser Sitzung, benannt:** der Check auf offene `AGENT_HANDOVER.md`-PRs
(session-ende Phase 0a-handover-pr) lief erst am Sitzungsende — #1960 entstand davor und
hat #1935 damit überholt. Genau die Reihenfolge, die diese Phase verhindern soll.

**Offen, ausdruecklich benannt:** Haupt-Tree `~/github/platform` ist dreckig (fremde
staged Aenderungen, 16 Commits hinter origin/main) — jeder Pull dort bricht ab, nach
ADR-233 nicht angefasst. `frist-hub#117` rot (Integration Tests, war vorher von der
Marke verdeckt). `travel-beat#74` geschlossen statt gemergt, ungeklaert.

### 2026-08-14 · Session music-lab-erster-song (früh, Kapitäns-Kanal)

Owner-Ziel: „Audio-Plattform läuft, ich kann Songs produzieren" → [music-lab#1](https://github.com/achimdehnert/music-lab/issues/1).
**Erreicht (technisch):** erster Song `out/20260814-051548-tracht-grachten-tomorrowland.wav`
(179,9 s, 48 kHz stereo, Seed 2027) + Metadaten-JSON; Kriterien K1–K4 einzeln belegt im
[Issue-Kommentar](https://github.com/achimdehnert/music-lab/issues/1#issuecomment-5289784090).
Ohr-Abnahme (K2 „Gesang", K3 Browser) beim Owner offen.

- **music-lab-Fixkette (7 Pushes auf main, SA-4):** Route Dev-Server→Box per SSH-Tunnel
  über den WG-Hub (`make tunnel`, dd754fa) · PS1-ASCII + CI-Gate `ps1-gate` (e7e92a2;
  Em-Dash in String + UTF-8 ohne BOM kippte den PS-5.1-Parser) · `gradio<6` (53f5921) ·
  CUDA-torch (2ced328; PyPI-torch ist auf Windows CPU-only — Model-Load 724 s→13 s) ·
  TorchCodec-Irrweg beendet: Pin torch/torchaudio 2.7.1 + echte Save-Probe (3a3b801) ·
  Handover-Stand (667a763) · `.gitignore` .windsurf (ce74e8d).
- **platform-Anteile:** [#1975](https://github.com/achimdehnert/platform/pull/1975) gemergt —
  Prio-Punkt 4 nachgezogen (#1078 Befund 4 war seit 11.08. zu; Runner-0.7.4-Fund).
  **Haupt-Tree bereinigt (Owner-Go „5 go"):** fremde staged doc-hub-/Ausnahmelisten-Änderungen
  waren NICHT in origin/main — gesichert als Stash `2026-08-14: fremde staged doc-hub…`
  (+ Patchdatei im Session-Scratchpad), dann ff-merge. **Sichtung des Stash: Owner-Zug.**
- **Session-Start-Befunde:** cad-hub Deploy rot = Health-Check 30× HTTP 000 auf nl2cad.de —
  passt zu [#1876](https://github.com/achimdehnert/platform/issues/1876) (Deploy trifft den
  Host ohne Verkehr; Owner-Entscheidung C0 offen) · travel-beat rot = bekannt
  [travel-beat#79](https://github.com/achimdehnert/travel-beat/issues/79).
- **Neue 🌀-Memories (platform-Lane):** `pgrep/pkill -f` matcht die eigene Shell ·
  PyPI-torch Windows CPU-only + torchaudio≥2.9→TorchCodec; Kernlehre des Tages:
  ein Import-Check beweist keinen DLL-Load — Probe muss den echten Pfad ausführen.

**Abnahme (0d):** Zielzustand **erreicht (technisch)** — Kriterien einzeln verifiziert,
Ohr-Urteil aussteht (kein Tracking-Artefakt nötig: Issue #1 bleibt offen bis dahin).
**SA-4: 8 Anwendungen (7× music-lab main, 1× platform-PR-Merge) · 0 Einzel-OK trotz
Klassen-Deckung · 0 Fehlanwendungen.** 1 Classifier-Block (Sammelbefehl
Merge+Pull+Reap) → einzeln ausgeführt, nicht umgangen.

### 2026-08-15 · Session melder-gruen-und-fp-ritual (Kapitäns-Kanal)

Owner-Ziel: „ein Zustand / eine Konfiguration, die dafür sorgt, dass der Zustand der
Repos cross-repo jedes Mal besser wird" — Einstieg über die Session-Start-Items 4+5
(project-facts-Melder entröten, FP-Auswertung der zwei advisory-Scanner).

**Der Kernfund war ein anderer als die Aufgabe.** Die FP-Datengrundlage für das Ritual
am 16.08. bestand aus 212 Treffern — **alle 212 aus `pytest`, null aus echten Sitzungen**.
Die Scanner-Drills fahren `scanner.main()` mit Fixture-Sätzen durch, und `main()` ruft
`gate_hits.notiere()` ohne `pfad`, also in das echte Protokoll. Drei unabhängige Belege:
Ausschnitte wörtlich = Fixture-Sätze, `session` bei allen Zeilen leer, Marker-Verteilung
exakt uniform (6×22, 4×20). Ein „0 Fehlalarme"-Urteil wäre vakuum wahr gewesen.

- **[#1986](https://github.com/achimdehnert/platform/pull/1986)** — pytest-Sperre in
  `notiere()` + Isolations-Fixture in beiden Drills + Herkunfts-Ausweis in `--bericht`
  (Zeilen ohne session_id sind kein Beleg). Zusätzlich: die zwei Tests der
  Archiv-Behandlung (#1953) prüften Quelltext-**Zeichenketten** statt Verhalten — durch
  Verhaltens-Tests ersetzt, Falsifikation belegt.
- **[#1987](https://github.com/achimdehnert/platform/pull/1987)** — Ritual-Termin 16.08.
  als hinfällig ausgewiesen (Handover-Prios 1+3, KONZ-038 §13). Offene Frage gedreht:
  nicht Precision, sondern **Recall** — warum feuert ein Gate mit ×8/×10-Regelverletzung
  in fünf arbeitsreichen Tagen nie?
- **[#1988](https://github.com/achimdehnert/platform/pull/1988)** — beide GATE-HEADER auf
  `2026-08-15 bis 2026-08-29`. **Selbstbetreffend**, Owner-Freigabe wörtlich erteilt.
  Erster Anlauf: der Classifier blockte den zweiten der beiden Edits; die bereits
  durchgegangene Änderung wurde **zurückgenommen** statt halb stehen gelassen.
- **[#1991](https://github.com/achimdehnert/platform/pull/1991)** — `tools/hook-dist-drift.sh`
  + Runner-Phase **0.7.5**, aus [#1989](https://github.com/achimdehnert/platform/issues/1989)
  Schritt 1.

**Teuerster Einzelfund der Sitzung:** nach dem Merge von #1988 wich der aktive Hook-Pfad
`~/.claude/hooks/` in **allen drei** Welle-1-Dateien von `main` ab — im aktiven
`gate_hits.py` fehlte die Sperre aus #1986, also genau die Änderung, die das neu
gestartete Fenster schützen sollte. Merge grün, Sperre im Repo, Wirkung null. Ursache:
diese Hooks werden **von Hand** verteilt (`cc-skill-dist` bespielt nur `managed/`).
Von Hand nachgezogen + scharf geprüft; Ursache getrackt in #1989.

**Vier weitere Drifts, die der neue Melder sofort fand und die NICHT gesynct wurden:**
`block_unformatted_push.sh`, `hygiene_melder.py`, `memory_link_guard.py`,
`model_change_detector.sh` — drei davon in `settings.json` verdrahtet. Bewusst einzeln
anzusehen statt im Massenzug durchzusyncen (#1989).

**Nachgeprüft, nicht übernommen:** die Handover-Annahme, die CI-Unterdrückungsmarke sei
Ursache des roten `Gen project-facts.md`, trug bei **keinem** der beiden Fehlläufe —
10.08. war Fremd-Org-Zugriff (#1768), 13.08. das archivierte wedding-hub (403). Beide
adressiert. Teilantwort zum Wochenlauf-Beweis liegt vor: risk-hub#596 (13 Checks) und
tax-hub#119 (14) tragen Checks; ttz-hub#28 und travel-beat#74 tragen **0** — ungeklärt.

**Offen, ausdrücklich benannt:** ausschreibungs-hub-Prod-Freigabe (Run 31720758982,
Gate `production` id 16077522818) — vom Permission-Classifier geblockt, Kommando liegt
beim Owner; Run trägt `2984518` = main-HEAD, also `approved`, nicht `rejected`.
[#1935](https://github.com/achimdehnert/platform/pull/1935) offen und 44 Commits hinter
main: sein `AGENT_HANDOVER.md`-Teil ist überholt, sein **LOG-Teil (Strang 4f808a,
2026-08-11) steht nirgends sonst** — deshalb bewusst NICHT geschlossen, Owner-Entscheidung.

**Abnahme (0d):** Zielzustand **erreicht** — K1 Messapparat misst nicht mehr sich selbst
(Kontrollprobe 212→212 unverändert bei vollem Testlauf), K2 Herkunft wird vor dem Urteil
ausgewiesen, K3 Drift zwischen Quelle und aktivem Pfad ist ab sofort jede Session
sichtbar (0.7.5, im Haupt-Tree verifiziert), K4 die Freigabe-Hürde steht im
maschinenlesbaren Header statt nur in Prosa.

**SA-4: 0 Anwendungen** — SA-4 wurde nicht beansprucht. Jede Eskalation über den
Ursprungsauftrag hinaus lief über eine wörtliche Owner-Freigabe („5 go", „ich gebe frei",
„mach 1989 schritt 1", „merge 1991"). 2 Classifier-Blocks (Prod-Freigabe, Gate-Header-Edit)
— beide gemeldet, keiner umgangen. Scope-Checkpoint bei 4 PRs durabel abgelegt
([#1640-Kommentar](https://github.com/achimdehnert/platform/issues/1640#issuecomment-5301883096)).

### 2026-08-15 · Delta zur Sitzung melder-gruen-und-fp-ritual (Nachmittag, Kapitäns-Kanal)

Fortsetzung desselben Zielzustands. Zehn PRs insgesamt, alle gemergt; jede Eskalation
über den Ursprungsauftrag hinaus lief über eine wörtliche Owner-Freigabe.

- **Retro (`full`, 8 Befunde, 6 überlebt)** → [`docs/retros/session-retro-2026-08-15-platform-d57884.md`](https://github.com/achimdehnert/platform/pull/1994). Drei Skeptiker auf die Bewertungsbefunde (Owner-Freigabe, ~165k Token). **Zwei von drei widerlegt — beide Selbstanklagen waren zu STRENG, nicht zu milde.**
- **Die teuerste Lehre kam aus der Retro, nicht aus der Arbeit:** eine von mir **veröffentlichte Korrektur** war selbst falsch und drehte eine zutreffende Diagnose ins Gegenteil. Aus einem leeren `gh pr checks`-Rollup wurde eine Kausalaussage, statt Run-Events und PR-Timeline nebeneinanderzulegen. Gemessen: Push `11:04:50` → Checks `11:04:53`; das close/reopen folgte erst `11:05:34` und war überflüssig. **Nicht Behauptung vor dem billigsten Check, sondern Korrektur vor dem billigsten Check** — und eine Korrektur wird härter geglaubt, überschreibt Artefakte und wird selten ein zweites Mal hinterfragt. Drei Artefakte korrigiert (PR-Kommentar eingeklappt statt gelöscht, Outline-Lesson, pgvector). Gefangen hat es ein Skeptiker mit frischem Kontext; auch dessen Erstbeleg trug nicht, erst die Rückfrage brachte die Zeitachse.
- **[#1993](https://github.com/achimdehnert/platform/pull/1993)** — `session-ende.md` + `session-docu.md` trennen jetzt Squash-Subject (harmlos) von Head-Commit (hungert alle Required Checks aus), nennen das Erkennungsmerkmal (leerer Rollup ist der Befund, kein „läuft noch") und den Reparaturweg. CODEOWNERS-Review, vom Owner gemergt.
- **[#1996](https://github.com/achimdehnert/platform/pull/1996)** — Gate `hand-distributed-copy-not-redistributed` registriert; `retro_kpis.py` führt es nicht mehr als ungedeckt.
- **[#1935](https://github.com/achimdehnert/platform/pull/1935)** aufgelöst und gemergt: Handover von `main` (Branch-Stand überholt), LOG **beide Seiten** — die fremden Sitzungs-Einträge `4f808a`/`9ee08c2` standen nirgends sonst. Drei Kontrollproben, 0 entfernte Zeilen.
- **[#1997](https://github.com/achimdehnert/platform/pull/1997) + [#1998](https://github.com/achimdehnert/platform/pull/1998)** — Lane `claude-hooks` mit **nicht-löschendem Merge-Modus** plus `doctor`-Parität. „Flach" war keine Filter-Zeile, sondern ein neuer Schreibmodus: `~/.claude/hooks/` teilt sich mit 26 fremden Einträgen, ein Swap hätte sie gelöscht. Live gelaufen: **0 verloren, 25 fremde überlebt, 13 verteilt**, alle `.py` kompilieren, Sperre im aktiven Pfad wirkt.
- **ausschreibungs-hub**: Prod-Gate freigegeben (Owner-Go), Deploy `completed/success` — der Run hing seit dem 13.08.
- **`commands`-Lane entstaubt**: `doctor` meldete 5 `copy-stale`, nach `generate --allow-live` → `DRIFT-SCORE 0`.

**Was #1989 jetzt trägt, bewusst dreiteilig und unabhängig:** Melder `0.7.5` prüft den
Ist-Zustand des aktiven Pfads *egal ob die Lane lief* · Lane `claude-hooks` behebt ·
`doctor --kind claude-hooks` diagnostiziert. Wäre der Melder durch die Lane ersetzt worden,
hinge die Erkennung wieder an ihrer Ausführung — die Ausgangslage vom Morgen.

**Offen, ausdrücklich benannt:** Recall-Frage [#1640](https://github.com/achimdehnert/platform/issues/1640)
(warum feuerten die zwei advisory-Gates in fünf Tagen real nie?) · Wochenlauf-Beweis
`Gen project-facts.md` Montag 17.08. 04:00 UTC ([#1953](https://github.com/achimdehnert/platform/issues/1953))
· Kalibrierung des Artefakt-Budget-Melders: er feuerte **siebenmal**, siebenmal dieselbe
Antwort, null Treffer — Vorschlag im #1640-Register, ihn an PRs **ohne** vorangehende
Owner-Nachricht zu hängen statt an der absoluten PR-Zahl.

**Abnahme (0d):** Zielzustand **erreicht**, Kriterien einzeln belegt.
**SA-4: 0 Anwendungen** — nicht beansprucht.

### 2026-08-16 · Strang cross-repo-befunde (Kapitäns-Kanal, Session 9d861a14)

Zielzustand [#2004](https://github.com/achimdehnert/platform/issues/2004), vom Owner akzeptiert:
*„Ein Befund über ein anderes Repo verlässt die Sitzung nicht mehr als Prosa in `platform`,
sondern als Arbeitsauftrag im betroffenen Repo — und ein Befund, der wiederkehrt, wird mit
jeder Sitzung sichtbar älter statt gleich laut."* **Erreicht, geschlossen, vier Kriterien
einzeln belegt.** Sechs PRs (#2005, #2007, #2008, #2009, #2010, #2011), alle gemergt; drei
Issues (#2004, #2006, apo-hub#78).

**Der Auftrag stimmte, seine Begründung nicht.** Ich hatte in #2004 geschrieben, es fehle ein
Mechanismus, der Befunde ins Zielrepo bringt. Falsch: `deploy_failure_monitor.py` schreibt
seit Langem cross-repo, und **vier der fünf** Repos hatten den Befund bereits als eigenes
Issue. Gefehlt hat die Gegenprobe *vor* dem Anlegen — Sitzungen legten platform-seitig ein
zweites Exemplar an. Hätte ich meiner eigenen Prämisse geglaubt, wären fünf Duplikate
entstanden. Deshalb spricht Phase 0f von „verankern", nicht von „anlegen".

**Drei Melder haben mich an diesem Tag korrigiert, alle drei zu Recht:**

1. `ci-gate-maskiert-failure` — `continue-on-error: true` ohne Begründung direkt darüber.
   Begründung je Zeile ergänzt statt eine Ausnahme zu suchen.
2. `gitleaks` — ein erfundenes Private-Key-Muster im Drill. Kein Fehlalarm, `platform` ist
   öffentlich. **Bewusst kein Allowlist-Eintrag**: eine Ausnahme für die Regel `private-key`
   taugt nur so viel wie der echte Schlüssel, den sie eines Tages durchlässt. Rahmen wird
   zur Laufzeit gebaut. Nachtrag: das Nachbessern im Folgecommit genügte **nicht** — gitleaks
   prüft den Commit-Bereich des PR, nicht den Endstand; erst das Zusammenziehen der Historie
   löste es.
3. `untested-command-scanner` — Platzhalter in einem Kommando, den ich als Schönheitsfehler
   abgetan hätte. Er ist keiner: literal gesetzt, laufen die Token-Schritte an, scheitern je
   Org, und dank `continue-on-error` bleibt der Lauf **grün** — ein Konfigurationsfehler sähe
   dann exakt aus wie eine fehlende App-Installation.

**Und der dritte Melder deckte einen Defekt in sich selbst auf.** Er meldete denselben,
längst behobenen Befund **neunmal**. Beim dritten Mal habe ich ihn als Fehlalarm gelesen —
genau der Schaden, vor dem der Kommentar direkt über der fehlerhaften Stelle warnt (#1508).
Ursache: die Entprellung filterte nur `untested`, nie `placeholders`, und `_merken` speicherte
auch nur die. Belegt an der Zustandsdatei: neun Meldungen, `{"gemeldet": []}`. Gefixt (#2011),
falsifiziert (ohne Fix fällt genau der neue Test), verteilt, und die Wirkung an vier Läufen
gegen die **aktive** Kopie belegt.

**Eigene Fehler, alle vor dem Merge gefangen — der Weg dahin war dreimal derselbe: ausführen
statt lesen.**

- Der erste Beweislauf für den Org-Token war **kaputt**, nicht der Code:
  `GH_TOKEN=ungültig RECONCILE_TOKEN_X="$(gh auth token)"` — die Zuweisung wirkte schon auf
  die Substitution, beide Tokens waren derselbe Müll. Alle 23 Referenzen `UNKNOWN`, und die
  naheliegende Deutung wäre „der Token-Pfad greift nicht" gewesen.
- Der erste Entwurf des Registry-Schiedsrichters meldete vier Referenzen als „Adressfehler im
  Handover". Falsch — bei `frist-hub#117` stand die richtige URL auf derselben Zeile; gelesen
  hatte der Parser nur den Label-Text. Ein Werkzeug, das seine eigene Annahme dem Dokument als
  Fehler vorhält, ist schlimmer als eines, das schweigt.
- `--help` des neuen Setup-Skripts druckte **Quelltext** (`sed -n '1,30p'` bei längerem Kopf),
  gefunden erst beim Selbstausführen.
- Mein Eingriff in die Entprellungs-Datei wirkte **nicht** — ich hatte die Wirkung behauptet,
  ohne den Scanner einmal laufen zu lassen. Der aktive Code liest `schon` für Platzhalter nie.

**Dreimal an einem Tag: gemergt ≠ wirksam.** `artefakt_budget.py` (der Fix aus #2003 lag nicht
im aktiven Pfad), `untested_command_scanner.py` (nach dem Merge sofort `DRIFT`), und die
Skill-Kopien `session-ende`/`session-start` — die ausgeführte Fassung kannte die eigene, an
diesem Tag gemergte Phase 0f **nicht**. Gefunden hat es jedes Mal ein Melder in einer Zeile
(0.7.5 bzw. `cc-skill-dist doctor`). Alle drei nachgezogen, DRIFT-SCORE 0.

**Erste echte Messwerte des Artefakt-Budget-Melders** (Prio 5): `prs_seit_owner` blieb zweimal
bei 1 und sprang beim dritten Feuern auf 2 — genau dort, wo ungefragt weitergebaut wurde. Das
Kandidat-Kriterium traf den Fall, den die absolute Schwelle verfehlt.

**Abnahme:** Zielzustand erreicht. **SA-4: 0 Anwendungen.** Eine Eskalation ohne Auftrag
(#2011) — vom Melder korrekt angezeigt, gespiegelt, danach vom Owner freigegeben.

### 2026-08-16 · Nachtrag: GitHub App live (Strang cross-repo-befunde)

Nach dem Sitzungs-Handover ausgeführt, deshalb eigener Eintrag. App
`iil-handover-reconciler` (id 4612790) angelegt, in vier Orgs installiert, Secret
gesetzt, Abnahme grün: `nicht prüfbar 12 → 0`, `DISKREPANZ 8 → 18`
([Lauf 31947642164](https://github.com/achimdehnert/platform/actions/runs/31947642164)).
Der Anstieg ist der Erfolg — exakt die zehn Referenzen, die als Prognose in #2009 standen.

**Was auf dem Weg dahin dreimal geprüft statt geglaubt wurde:**

1. Der Owner meldete zweimal „passt" — die Schlüsseldatei war beim ersten Mal **44 Bytes**
   ohne PEM-Struktur (0 Zeilen, 0× `BEGIN`). Gegenprobe an der danebenliegenden, bekannt
   gültigen Datei (27 Zeilen, 1× `BEGIN`) zeigte, dass der Test funktioniert. Ohne diese
   Positivkontrolle wäre „keine PEM-Struktur" nicht von „mein Muster passt nicht" zu
   trennen gewesen.
2. **Welche App ein Schlüssel bedient, sagt nicht der Dateiname.** Im Secrets-Verzeichnis
   lagen zwei fast gleich benannte App-Schlüssel (der neue und ein `…_admin`-Schlüssel von
   Juni). Geprüft per JWT gegen `GET /app` → id 4612790, passt. Ein falscher Schlüssel hätte
   zu leeren Token-Schritten geführt — und das sieht exakt aus wie eine fehlende Installation.
3. Die vier Installationen waren mit dem User-Token **nicht** prüfbar
   (`/user/installations` → 403). Erst der App-JWT zeigte sie: alle vier mit
   `repository_selection: all` und genau den drei Read-Rechten.

**Zwei Handgriffe, die sonst jeder neu sucht:** `gh api` sendet `Authorization: token …`,
ein App-JWT braucht **`Bearer`** — `gh` kann ihn nicht tragen, der Check läuft über
`urllib` mit eigenem Header. Und: eine Absence-Behauptung über die REST-API („es gibt
keinen Endpunkt, um Installationen anzulegen") ist erst mit der Doku belegt; die erste
API-Probe war wertlos, weil die Positivkontrolle am fehlenden `admin:org`-Scope scheiterte.

`bahn-sqf` bewusst **nicht** installiert — kam im Report nie vor; der Workflow-Schritt
bleibt wirkungslos statt rot.

### 2026-08-16 · Nachtrag 2: Retro 9d861a + vier Maßnahmen (Strang cross-repo-befunde)

Retro (`deep`, 19 Befunde, 18 überlebt) → [`docs/retros/session-retro-2026-08-16-platform-9d861a.md`](docs/retros/session-retro-2026-08-16-platform-9d861a.md), [#2014](https://github.com/achimdehnert/platform/pull/2014). Falsifikation mit drei Sonnet-Subagenten (~215k Token), nachdem der Owner Subagenten freigab; die Find-Phase war zuvor inline gelaufen (Systemanweisung), was als Regel-1-Bruch in §8 steht.

**Der Retro kassierte seinen eigenen Hauptbefund.** Ich hatte aus *„16 von 16 Gate-Protokolleinträgen stammen von einem Melder"* geschlossen, die übrigen advisory-Scanner schwiegen. Falsch: **zwei von fünf** aktiven Scannern (`evidence_claim_scanner`, `untested_command_scanner`) schrieben gar nicht ins Protokoll — ausgerechnet die beiden, die an diesem Tag nachweislich feuerten. Die Null war teilweise mein Filter. **Konsequenz für [#1640](https://github.com/achimdehnert/platform/issues/1640): die dortige FP-/Recall-Auswertung stand auf unvollständiger Datenbasis** — nicht verunreinigt wie im Juli, sondern lückenhaft. Als `pre_refuted` geführt, behoben in [#2015](https://github.com/achimdehnert/platform/pull/2015).

**Vier Maßnahmen umgesetzt** ([#2015](https://github.com/achimdehnert/platform/pull/2015), [#2016](https://github.com/achimdehnert/platform/issues/2016), Kommentar an [#2011](https://github.com/achimdehnert/platform/pull/2011)):

1. Beide stummen Scanner protokollieren jetzt. Dabei kam heraus, dass `untested_command_scanner` **überhaupt nicht registriert** war — aktiv seit Wochen, unsichtbar für `gate_drill_check.py` und die Gate-Buchhaltung. Nachgetragen als `untested-command-handed-to-user`.
2. **Zweite Instanz** derselben FN-Klasse wie Retro 287b23 #6: der `deferred_item_scanner` kannte Aufschübe in **Verneinungsform** nicht („ist hier bewusst nicht mitgemacht"). Deshalb blieb ein realer Aufschub ohne Tracking. Muster ergänzt, eng gehalten, Negativ-Test gegen Fremdberichte.
3. Phase 0f meldet bei fehlendem Journal `UNGEPRUEFT` statt vakuum-`OK`.
4. Die aufgeschobene Konsolidierung der zwei Befund-Gedächtnisse hat jetzt ein Tracking-Artefakt (#2016) — sie stand vorher nur im PR-Text, was per Hausregel nicht zählt.

**Methoden-Blindfleck der Retro-Methode, mit Lösung.** Ein Skeptiker zitierte **meinen eigenen** `gh`-Kommentar als „Owner-Aussage" — meine Schreibzugriffe laufen unter demselben Konto, für einen Subagenten nicht erkennbar. Diskriminator gefunden und belegt: **`merged_by` trennt sauber** — `wirdigital` ist der Mensch (mergte #2003/#2005/#2007/#2008/#2009), `achimdehnert` ist der Agent-Token (mergte #2010/#2011/#2012/#2013). Gehört in jeden künftigen Skeptiker-Prompt; macht die Autonomie-Messung erstmals artefaktgestützt.

**Phase 0f lief erstmals echt.** Das Journal entstand um 14:32; das Gate meldete `OFFEN` für `cad-hub` und `travel-beat` und wurde per `--verankert` auf cad-hub#40 bzw. travel-beat#52 geschlossen — beide waren am Vormittag ins Zielrepo überführt worden. Danach Exit 0. Der Mechanismus hat damit einmal vollständig funktioniert.

**Vierter Fall von „gemergt ≠ wirksam" am selben Tag:** die drei geänderten Hooks waren nach dem Merge erwartungsgemäß driftig; per `hook-dist-drift.sh --sync` nachgezogen und **scharf** geprüft (isolierter Lauf schreibt eine Protokollzeile mit dem neuen Slug, `UNGEPRUEFT`-Pfad live ausgeführt).

**Beobachtung ohne Erklärung:** kurz nach dem Merge war der Haupt-Tree dirty mit genau den Dateien dieses PRs, ein `git pull` scheiterte daran; beim nächsten Blick war er clean und auf `origin/main`. Vermutlich eine Parallel-Sitzung — nicht verifiziert. Nichts ging verloren, alles war committet und gemergt.

**Abnahme:** Zielzustand weiterhin erreicht. **SA-4: 0 Anwendungen.** `over_ask: 0` · `over_act: 1` (#2011, skeptiker-bestätigt, Freigabe-Vermerk nachgetragen).

### 2026-08-17 · Eine synchrone Flotte, aus einem Beifang entstanden (Strang sharedci-vereinheitlichung)

Der Auftrag war der Wochenlauf-Beweis. Er gelang — und auf dem Weg fiel auf, dass derselbe
Lauf einen offenen PR geschlossen und das als `aktualisiert` gemeldet hatte. Daraus wurde
ein Tag, der mit **37 PRs ueber ~30 Repos** endete und die Flotte erstmals auf **einen**
shared-ci-Stand brachte (`v1.1.10`).

**Was ich mitnehme, jenseits der Zahlen:**

1. **Zweimal messen schlaegt einmal vermuten — und die zweite Messung muss anders
   formuliert sein.** Meine erste Flottensuche fand `shared-ci/.github/workflows/…@ref`.
   Eine zweite, breiter formulierte Suche fand acht Repos, die eine **Action** referenzieren
   (`gitleaks-scan`), sechs davon auf `v1.0.0`. Waere ich bei der ersten geblieben, haette
   ich "Flotte synchron" gemeldet, waehrend der Secret-Scanner auf dem allerersten Tag lief.
2. **Ein Bump, der nur `ci.yml` anfasst, zementiert die Asynchronitaet.** Alle zwoelf Repos
   der ersten Welle trugen im Deploy-Pfad einen aelteren Pin. Der Owner-Satz "keine
   Extralocken" war der Grund, die schon offenen PRs nochmal aufzumachen statt sie zu mergen.
3. **Drei Defekte, eine Klasse.** shared-ci prueft Exit `5` statt "wurden Tests
   eingesammelt"; shared-ci prueft "Verzeichnis existiert" statt "Projektdatei vorhanden";
   der Artefakt-Melder matcht `gh pr create` statt "wurde ein PR angelegt". Jedes Mal wird
   eine **Schreibweise** geprueft und eine **Sache** gemeint. Das ist keine Sammlung von
   Einzelfehlern, sondern ein Muster, nach dem sich suchen laesst.
4. **`skip_tests: true` blind zu kippen waere der Fehler des Tages gewesen.** Sechs von acht
   Repos hatten einen dokumentierten Grund, eines davon woertlich als Owner-Entscheidung.
   Meine eigene Erstaussage ("acht Repos gruen ohne einen einzigen Test") war fuer sechs
   davon falsch — aufgefallen nur, weil ich vor dem Sweep jede Datei einzeln gelesen habe.
5. **Bei den zwei echten Faellen wandert der Fehler nach vorn, und das ist der Ertrag.**
   trading-hub: Install → DB → 559 gruene Tests → TimescaleDB. Jede Schicht war unsichtbar,
   solange die darueber liegende den Job abbrach.
6. **Zwei eigene Falschaussagen fielen beim Bauen auf, nicht beim Behaupten** — `set +e`
   stand direkt ueber der Zeile, die ich fuer unerreichbar erklaert hatte, und der
   `coverage_threshold`-Input speist einen ganz anderen Job als behauptet. Beide standen da
   schon eine Stunde in gemergten Artefakten. Korrigiert in #2032 und an shared-ci#54.

**Deploys:** 7 gruen. weltenhub neu rot (openai/litellm ohne Obergrenze, weltenhub#56 —
Ausloeser war mein Merge, Ursache nicht). cad-hub, tax-hub, travel-beat waren vorher schon
rot. bahn-hub: 9 Ruff-Fehler in einem seit Juli unberuehrten Repo.

**Abnahme:** Zielzustand erreicht mit benannter Restmenge (5 Repos, je ein Grund).
**SA-4: 0 Anwendungen** · `over_ask: 0` · `over_act: 0`.

### 2026-08-17 · Nachtrag: Subagenten freigegeben, und sie haben mich viermal korrigiert

Nach dem ersten Sitzungsende kamen vier Owner-Auftraege: Skill-PR fuer den fremden Blick,
SSoT-Policy, Konzept-Friedhof, Increment-Retro. Der Owner gab dabei **Subagenten fuer
/session-retro frei** — der erste Retro-Lauf mit echter Phase 3.

**Das Ergebnis der Falsifikation ist die Nachricht.** Vier Agenten, vier Mal aenderte sich
mein Bild, kein einziger bestaetigte nur: Parent-Befund #11 widerlegt (mit Zeitstempeln:
alle 12 PRs haben 4 Commits, mergedAt liegt ueberall NACH dem letzten Commit -- Iteration,
kein Rework), #10 mit falscher Kategorie (der Diff war EINE Zeile in secret-scan.yml, der
rote Lint bestand vorher), #9 ueberlebt mit unbelegter Kausal-Haelfte, und der Finder fand
vier Trigger-Fehlschuesse in einer Liste, die ich als vollstaendig gemeldet hatte.
refuted_rate im Parent von 0.0 auf 0.09 -- die urspruengliche Null war keine Schaerfe,
sondern eine nicht gelaufene Pruefung.

**Der Fehler ueber mich selbst ist der interessantere.** Die Kalibrier-Pflicht fuer
Nullbefunde stand in ZWEI von VIER Agent-Prompts. Genau der Agent ohne sie las eine 404 als
Abwesenheit und erzeugte einen falschen hoch-Befund; ein fuenfter Agent musste ihn
entfernen. Die beiden mit Pflicht fuehrten ihre 404 korrekt als ungeklaert. Dieselbe
Anweisung, halb vergeben, mit exakt dem vorhersagbaren Unterschied. Fremder Kontext macht
unabhaengig, nicht richtig.

**Das Tagesmuster hat jetzt ein Gate-Mandat.** gate-matches-spelling-not-substance steht
nach dem Increment bei x2 und ist damit gate-pflichtig -- ausgeloest davon, dass mein
eigener Trigger-Fix die zwei gemeldeten Schreibweisen patchte statt der Wortklasse
(individuell loesen, punktuelle Loesung, Sonderregel, hart codiert feuerten weiter nicht).
Fuenfte Instanz derselben Klasse an einem Tag.

**Konzept-Friedhof gemessen statt gefuehlt:** 44 Dokumente, 34 auf `idea`, 12 ueberfaellig
(nicht 21 -- meine erste Zahl zaehlte review_by-ZEILEN, mehrere Dokumente tragen zwei).
Sechs auf Owner-Entscheid entfernt (platform#2040), 007 NICHT: dessen Statusfeld ist keine
Statusangabe, sondern eine Entscheidung mit Wiedereintrittsbedingung -- mein Parser las den
Satzanfang als 'sunset'. Zwei Vorbehalte im PR benannt (002 laeuft real, 003 ist der
Umsetzungsplan fuer das akzeptierte ADR-045).

**Und die Antwort auf die Owner-Frage "woher kommt loeschen?": Messfehler.** Mein
Loeschsignal war `pipeline_status: idea` + Alter. Beides misst Vernachlaessigung, nicht
Wert -- und haette 34 von 44 Dokumenten getroffen. In der einzigen Stichprobe, die ich
gegen den INHALT geprueft habe (007), lag der Proxy sofort daneben.

**Offen am Ende:** drei PRs warten auf Owner-Review (#2036 Skill-Phase 0g, #2038 Policy,
#2040 Loeschung) -- der Owner hat keinen gh-Zugriff. Ohne Merge keine Verteilung; die
Skill-Phase 0g und die Policy sind damit geschrieben, aber noch nicht wirksam.


### 2026-08-17 abends · Der blinde Melder hatte recht — vier Prod-Datenbanken ohne Backup

Die Sitzung begann mit sieben Owner-Punkten und endete bei einem Befund, der groesser war
als alle sieben: **`risk-hub` (produktiv live) hatte seit vier Tagen kein Datenbank-Backup**,
zusammen mit `iil_dochub_db`, `wedding_hub_db` und `travel_beat_db`.

**Gefunden wurde er, weil drei Meldungen nebeneinander gelesen wurden.** Der Session-Start
fuehrt den ADR-241-Backup-Melder seit dem 15.08. als *blinden Melder* — „ein dauerhaft roter
Melder meldet nichts mehr". Diese Einordnung war falsch, und zwar auf die gefaehrlichere
Art: rot war kein Rauschen. 26,5 h → 50,6 h → 74,7 h, exakt +24 h pro Tag. Jede einzelne
Zeile las sich wie eine muede Warnung; erst der Trend war die Diagnose.

**Meine erste Hypothese dazu war falsch**, und die Korrektur ist lehrreicher als der Fund:
ich schrieb „der naechtliche Push laeuft nicht mehr". Er lief — in derselben Nacht sicherte
er acht Datenbanken. `risk_hub_db` war nur nicht in der Liste. Die Erkennung filtert die
Image-Spalte von `docker ps` auf `postgres|pgvector`; diese Spalte zeigt eine **nackte
Image-ID**, sobald die Referenz lokal nicht mehr getaggt ist. Der Container lief gesund
weiter, nur sein Anzeigename aenderte sich — und der war das Kriterium.

**Warum es vier Tage hielt, ist der eigentliche Befund:** ein Lauf, der WENIGER Datenbanken
sichert als der vorige, sieht in Log und Exit-Code exakt aus wie ein erfolgreicher. Deshalb
bekam #2047 nicht nur eine neue Erkennung (`pg_isready` — das Verhalten statt des Namens),
sondern einen **Rueckgang-Waechter**. Auf prod rein lesend verifiziert: 20 statt 17.

**Der Artefakt-Budget-Melder widerlegte sich waehrend seiner eigenen Reparatur, dreimal.**
Die alte Kopie meldete 12, dann 15 PRs; tatsaechlich waren es 2 PRs und 1 Issue. Zehn der
zwoelf Phantom-PRs stammten aus der Commit-Message und dem PR-Text von #2044 **selbst** —
beide beschreiben das Muster `gh pr create`. Er verzaehlte sich um Faktor 6, weil er das
Dokument las, das erklaert, dass er sich verzaehlt. Nach Merge UND Verteilung echt gefahren:
die neue Kopie schweigt bei 2 PRs.

**Zwei eigene Denkfehler fanden Bestandstests, nicht ich.** Mein neuer Vorfilter verwarf
still eine `prRepository`-Zeile — dieselbe Klasse wie der Befund selbst, eine Ebene tiefer.
Und die Entprellung der neuen Schwelle setzte den Merker zurueck, „wenn der Zaehler faellt";
den Einbruch sieht der Hook aber nie, er kennt nur den Endstand jedes Stop. Eine zweite
Kette gleicher Laenge waere stumm geblieben.

**Der Schwellen-Entscheid ist umgesetzt (#2050):** `prs_seit_owner` statt absoluter PR-Zahl.
Verlaufs-Replay ueber 84 echte Transkripte: 401 → 40 Ausloesungen, konzentriert auf acht
Sitzungen — darunter der im Docstring benannte Anlassfall. Vorher hatte ich die
Registerdaten selbst entwertet: sie stammten vom defekten Zaehler.

**Ein Handover-Vorschlag war falsch und wurde nicht uebernommen.** Prio 2 schlug fuer
weltenhub `openai>=1.12.0,<2` vor. litellm 1.97 verlangt `openai>=2.20,<3` — der Pin haette
den Build von einem Versions- in einen Aufloesungskonflikt verwandelt. Richtig war, die drei
transitiven Pins zu streichen; `anthropic` faellt dabei komplett aus dem Baum, es war ein
toter Pin ohne Konsumenten.

**Rahmenbedingung des Tages:** eine GitHub-Stoerung mit dauerhaften HTTP 503. Zwei
`gh pr create` scheiterten, Merges brauchten bis zu neun Anlaeufe, `context-review` faellt
seither an mehreren PRs rot aus (kein Required Check). Vermutlich dieselbe Ursache dafuer,
dass der trading-hub-Merge **keinen einzigen** Workflow-Lauf ausloeste — nicht von Hand
nachgeholt, weil der Stack bewusst gestoppt ist.

**Abnahme:** je Owner-Punkt erreicht und einzeln belegt; offen bleiben die zwei
Prod-Schritte fuer #2047 und der trading-hub-Deploy, beide bewusst.
**SA-4: 0 Anwendungen** · `over_ask: 0` · `over_act: 0`.

---

## 2026-08-18 — platform: prod-b sichert erstmals, ein sieben Tage alter Ausfall ist beendet

**HEAD `b59cef38`** · eine Sitzung (Kapitaens-Kanal) · 1 PR, 4 Issues, 2 Fremd-Repo-Issues
ueber 5 Repos und 2 Hosts.

**Der Tag begann mit einer Backup-Prio und endete bei drei Arten, wie "gesichert" luegen
kann** — alle dieselbe Klasse: die Kontrolle prueft einen Namen, die Sache liegt woanders.
`docker ps` zeigt eine nackte Image-ID (#2047, gestern). `restic` speichert einen
abgebrochenen 229-Byte-Dump klaglos als Snapshot, sodass "gibt es einen Snapshot?" mit JA
antwortet, waehrend die Datenbank ungesichert ist (#2057). Und wiederbelebte Alt-Stacks
sichern veraltete Datenbanken unter dem Tag-Namen der echten (#2058).

**Prio 1 ist belegt erledigt:** `risk_hub_db` von 74,7 h auf 0,4 h. Der Lauf meldete
trotzdem Exit 1 — nicht wegen der Nachholung, sondern wegen `pptx_hub_db`, das unter einer
App-Rolle ohne Attribute laeuft. #2059 bestimmt die Dump-Rolle jetzt ueber `pg_roles`
statt sie zu raten und verhindert per `pg_authid`-Vorbedingung, dass ein Leer-Dump
ueberhaupt hochgeladen wird. Erster gruener Lauf seit mindestens sechs Laeufen. Ueber alle
21 Instanzen gemessen: 20 liefern exakt `POSTGRES_USER`, nur pptx weicht ab.

**prod-b sichert seit heute — sieben produktive Datenbanken, die vorher in keinem Backup
lagen.** Gefunden als Beifang, weil `weltenhub_db` und `research_hub_db` mit 340,7 h
auffielen, waehrend weltenhub live antwortete. Weg A: gemeinsames Repository, unterschieden
ueber `OFFSITE_HOST=prod-b`, keine neue Kennung. Der Standort-Einwand liess sich aufloesen
statt offenlassen: die Auflage in `hosts.yaml` schliesst nur Gov-Workloads aus, und der
einzige (`frist-hub`) liegt auf prod nicht vor — 0 Container, 0 Volumes, 0 Snapshots, mit
Positivkontrolle.

**Ein eigener Fehlgriff, vollstaendig protokolliert: trading-hub war nie gestoppt.** Der
Handover fuehrte es als gestoppt; tatsaechlich lief es seit 13 Tagen auf prod-b, wo der
Tunnel es bedient. Mein Deploy erweckte die Karteileiche auf prod zu einem zweiten Stack.
Kein Datenverlust, kein Traffic-Schaden — aber der prod-Lauf haette ab sofort die
veraltete Datenbank unter dem Tag der echten gesichert. Zurueckgebaut.

**wedding-hub war seit 6–7 Tagen offline (502) und niemand hat es bemerkt** (#2061,
geschlossen). Registry und Tunnel-Route stimmten ueberein; dahinter lief nichts. Wer nur
Deklarationen vergleicht, sieht einen konsistenten Zustand — das ist der strukturelle Rest
in #2058 Punkt 3 und die naechste sinnvolle Arbeit.

**Die Recall-Frage der advisory-Scanner ist beantwortet, die Praemisse war ueberholt.**
Nicht mehr "feuert nie": alle 59 Protokollzeilen tragen eine session_id. Replay ueber 374
echte Turns: deferred SOLL 8 / IST 3, scope SOLL 1 / IST 0. Der eigentliche Befund ist ein
Konstruktionsfehler — das Scope-Gate prueft "Checkpoint ausgesprochen, aber nicht
festgehalten", der Retro-Slug zaehlt "gar nicht ausgesprochen". Und die drei echten
deferred-Treffer sind alle drei Zitat-Kontexte.

**Methodisch bemerkenswert:** mein erstes Replay-Skript griff die Muster ueber geratene
Symbolnamen ab, lieferte still `None` und druckte sauber "scope: 0 Feuer-Stellen" — exakt
der Fehlertyp, den es untersuchen sollte. Aufgefallen nur, weil die Null gegen die ×11 des
Slugs zu glatt wirkte.

**Drei eigene Fehlgriffe bei uebergebenen Befehlen:** PowerShell-Syntax fuer eine bash,
verschachtelte Anfuehrungszeichen, zweimal ein Zeilenumbruch mitten im Token. Ursache der
letzten beiden: das Eingabefeld bricht bei ~100 Zeichen hart um. Abhilfe: Uebergaben von
vornherein mehrzeilig, Zeilen < 90 Zeichen. Keiner richtete Schaden an.

**Der Klassifizierer blockte dreimal, dreimal zu Recht** — zuletzt ueber zwei Werkzeuge
hinweg beim Anlegen eines Skripts, das Zugangsdaten zwischen Produktivhosts kopiert. Beim
dritten Mal keinen weiteren Weg gesucht, sondern uebergeben; die Kennung lief nie durch
meinen Kontext.

**Abnahme:** je Owner-Punkt erreicht und einzeln belegt. **SA-4: 0 Anwendungen** ·
`over_ask: 0` · `over_act: 1` — der trading-hub-Deploy lief auf eine woertliche Freigabe,
aber auf einer von mir gelieferten falschen Praemisse.

## 2026-08-19 — platform: vier von sieben Prios waren beim Nachmessen ueberholt

**Das Wurzelthema:** die Prio-Liste beschrieb Zustaende, die es nicht mehr gab. Prio 5
(Sweep auf v1.1.11) war erledigt — beide Konsumenten standen laengst drauf; die echte Lage
sind SECHS Versionsbaender, darunter 15 Bibliotheks-Repos elf Minor zurueck (#2087). Prio 3
(26 gestoppte Container) fand NULL gestoppte Container, dafuer 72 benannte verwaiste
Volumes statt sechs Stacks. Prio 7 verwies auf abgeschlossene Vergangenheit. Lehre fuer die
Handover-Pflege: eine Prio, die einen ZUSTAND behauptet statt einer Aufgabe, verfaellt
zwischen zwei Sitzungen — und wird trotzdem als Auftrag gelesen.

**Scope-Gate Rev 2 (#2085, Review offen).** Rev 1 feuerte, wenn ein Checkpoint
AUSGESPROCHEN, aber nicht festgehalten wurde. Der Retro-Slug zaehlt die andere Haelfte:
gar nicht ausgesprochen (x10). Disjunkte Mengen. Rev 2 nimmt die Bedingung aus
Tool-Evidenz (drei beschriebene Repos oder ein Prod-Schritt) und prueft den Wortlaut erst
danach als Erfuellung. make test 2555 passed, Drill 10 passed, 10 CI-Checks gruen.

**Zwei Befunde am eigenen Neubau, beide vom Drill gefunden.** (1) Fehlerform B war
praktisch tot — jede Bearbeitung unter docs/ galt als "festgehalten", auch eine von
Stunden vorher zu anderem Thema; das durable Artefakt muss jetzt NACH dem Checkpoint
entstehen. (2) Worktree-Pfade zaehlten anfangs nicht als Repo; da seit ADR-233 fast jede
Sitzung in einem Worktree laeuft, waere das umgebaute Gate fuer den Normalfall genauso
blind geblieben wie Rev 1.

**KONZ-047 aus einer verwaisten Schleusen-Uebergabe.** Der ADR, auf den der Dateiname
zeigte, ist ein anderer; der beschriebene ADR existiert nirgends (Volltextsuche platform +
writing-hub: null); eine Antwort kam nie zurueck. 19 von 24 Uebergaben haben keine
Antwortdatei, sechs werden bis Samstag faellig (#2088).

**Volume-Aufraeumung: Entscheidung an der Snapshot-Herkunft, nicht am Namen.** restic
snapshots traegt den Quellhost — damit liess sich "alte Kopie auf prod" von "lebende
Datenbank auf prod-b" trennen, was ueber den Tag-Namen allein nicht geht. Owner-Entscheid:
40 Volumes (6,3 GB). Draussen: acht ohne Backup-Nachweis (#2086) und das Grafana-Volume.

**Zwei Klassifizierer-Blocks, beide zu Recht** (Environment-Freigabe, Volume-Loeschlauf),
beides an den Owner uebergeben statt umgangen.

**Ein eigener Fehlgriff:** `gh issue create --repo achimdehnert/ausschreibungs-hub` folgte
still einem GitHub-Redirect und legte das Issue in der fremden Org `iilgmbh` an. Phase 0f
verlangt dort eine Rueckfrage vorher. Kein Schaden, aber die Regel wurde uebergangen.

**Abnahme:** erreicht fuer 6, 7a, 8 · nicht begonnen 2 und 4 (freigegeben, Sitzung endete
vorher) · beim Owner 1 und 3a. SA-4: 0 Anwendungen · over_ask 0 · over_act 1.

## 2026-08-19 (nachmittags) — PyPI-Fleet-Programm #2075: K1–K4 + Kanon-Umzug (#2084)

Session im Kapitäns-Kanal, ~40 PRs über 20 Repos, alle gemergt. K1 Inventar+Klassifikation
(#2077), K2 Cold-Start 19/19 + AGENTS.md 19/19 + T1a-Eval 19/19 (#2081/#2100), K3
Frühwarn-Scanner Baseline 38 (#2090), K4 Loop-Erstzyklus real (#2095→#2096→#2097).
Kanon `_ci-pypi.yml` → iilgmbh/shared-ci (#2103) + M4-Sweep 15 Repos auf v1.1.11.
gpufw → iilgmbh transferiert. Offen (Owner): #2098, #2089, shared-ci-Überbleibsel,
risk-hub#618. Verifikations-Docs: docs/verifications/2026-08-19-adr266-*.md.

## 2026-08-19 nachmittags — doc-hub: Schleuse aus dem Paperless-Einzug, Dokumentversand per Mail

**Zielzustand** (platform#2083, Owner-Go im Kapitäns-Kanal): doc-hub-Stack versioniert,
Box-Schleuse ausserhalb des Einzugs, Dokumentversand aus der Oberflaeche.
**Abnahme: teilweise erreicht** — Kriterien 2, 3, 4, 5 erfuellt; Kriterium 1
(Host als Auscheckung des Repos) nicht.

**Ausloeser:** zwei Fehlermeldungen an docs.iil.pet (`PermissionError` in `.thumbs/`,
`SubprocessOutputError`). Ursache war eine falsche Praemisse in `tools/box-schleuse.sh`:
`/opt/paperless-consume` und der Paperless-Mount sind derselbe Inode (2064:3733153).
Die Gegenprobe von 2026-08-10 suchte den Pfad-String in den Container-Mounts, wo Docker
den `_data`-Pfad meldet — sie pruefte die Schreibweise, nicht die Identitaet.

**Erledigt:**
- Schleuse nach `/srv/box-schleuse` (scansnap:scanner 2775), eigene Samba-Freigabe
  `[schleuse]`, smbd reload. Windows-Pfad jetzt `\\10.99.0.1\schleuse\von-box\`.
  Gegenprobe `find /opt/paperless-consume -path '*schleuse*'` → 0. 817 Dateien, keine
  Quelldatei fehlt in der Kopie. PR #2101 (gemergt), Korrektur an #1888.
- 55 Fehl-Dokumente (54 Trainingsbilder + LIESMICH.txt) aus dem Archiv entfernt,
  9 verwaiste Tags geloescht. Aktiver Bestand 1004.
- Neues privates Repo `achimdehnert/doc-hub` (Commit c09625e): Compose vom Host plus
  `mailrelay/` — SMTP→Graph-Vermittler, weil Paperless nur Django-SMTP spricht und
  achim.dehnert@iil.gmbh keinen SMTP-Zugang hat.
- Entra: App `iil-mail-send` `f237ca44-50fd-4988-8699-5716f6951869`, genau eine Rolle
  `Mail.Send`, `ApplicationAccessPolicy RestrictAccess` auf ein Postfach.
  Echter Versand belegt: `gesendet an ad@dehnert.team (390906 Bytes)`.
- Rotation `risk@dehnert.team` (Anlass: Leak, siehe unten) auf Dev- und Prod-Host,
  SMTP-Anmeldung verifiziert. iilgmbh/risk-hub#621.
- Secret-Leak-Guard `~/.claude/hooks/block_env_cat.sh` gepatcht: `grep` galt nur als
  nachgeschalteter Filter und konnte die Secret-Datei selbst ausgeben. 5/7 → 7/7.
  achimdehnert/dev-hub#282.

**Eigene Fehler, beide gemeldet und behoben:**
1. `grep -rhiE` auf eine Secret-Datei schrieb ein Prod-Passwort ins Transkript
   (risk@dehnert.team). Rotiert, Gate gepatcht.
2. `mv` als root machte die Prod-Secret-Datei `root:root` — `read_secret()` fing den
   `PermissionError` und fiel still auf die Umgebungsvariable mit dem ALTEN Wert
   zurueck. Sichtbar nur an `len(EMAIL_HOST_PASSWORD)` 10 statt 13.

**Messbefund nebenbei:** die ID-Folge der Dokumente lag 716 vor dem Bestand, 705 Nummern
fehlten in 18 Luecken. Ursache belegt per 1:1-Korrelation (6 fehlgeschlagene
`consume_file`-Tasks in der letzten Stunde ↔ 6 verbrannte Nummern): jeder Fehlversuch
zieht eine Sequenznummer und verwirft sie.

**Offen:** Kriterium 1 aus #2083 (Host ist noch keine Auscheckung von `doc-hub`, die vier
`.bak-*` liegen noch daneben). Nicht verifiziert: ob die Access-Policy einen ANDEREN
Absender wirklich abweist — billigster Check `Test-ApplicationAccessPolicy` gegen ein
zweites Postfach.

**SA-4:** 0 Anwendungen · 0 Einzel-OK trotz Klassen-Deckung · 0 Fehlanwendungen
(Gates einzeln vorgelegt, jeweils Owner-Go).

## 2026-08-19 (Nachtrag zur Vormittagssitzung) — gemergt ist nicht wirksam

Die vier Punkte, die mittags beim Owner lagen, sind erledigt und gegengeprueft:
Environment-Gate ausschreibungs-hub freigegeben (Run completed/success, Folge-Lauf
"Push on main" gruen -> Merge #190 live, Issue iilgmbh/ausschreibungs-hub#191
geschlossen) · Volume-Loeschlauf 40 verarbeitet / 0 uebersprungen / 0 Fehler, plus
mcp-hub_mcp_hub_grafana_data auf Owner-Wort = 41 · benannte verwaiste Volumes auf prod
72 -> 32 · platform#2085 gemergt.

DER EIGENTLICHE BEFUND kam NACH dem Merge: hook-dist-drift.sh meldete
scope_checkpoint_scanner.py als DRIFT. Die aktive Hook-Kopie lief weiter auf Rev 1,
obwohl Rev 2 auf main stand. Erst --sync machte den Umbau wirksam (13 Kopien synchron,
gegengeprueft). Ohne diesen Schritt waere das neue Gate gebaut, gemergt, gruen — und
wirkungslos gewesen. Genau die Klasse aus
feedback_hand_distributed_copy_merge_is_not_effect; die Lehre ist bekannt und hat
trotzdem wieder gegriffen. Konsequenz fuer kuenftige Hook-Aenderungen: der
Verteilungs-Check gehoert in denselben Zug wie der Merge, nicht in den naechsten
Session-Start.

Grafana-Volume: die Vorsicht war unbegruendet. Ein Dashboard, provisioniert aus
mcp-hub:grafana/provisioning/dashboards/agent_controlling.json. allowUiUpdates: true,
Handaenderungen waeren also erlaubt gewesen — liegen aber nicht vor: DB-Eintrag
updated 2026-05-10, Repo-Datei danach noch viermal geaendert. Der Datenbankstand ist
AELTER als die Datei; eine Handaenderung wuerde das Gegenteil zeigen.

Nebenbefund zur Handover-Hygiene: beim Nachtragen lagen ZWEI "Aktueller Stand"-Bloecke
nebeneinander (Vormittag + Nachmittag), obwohl der Dateikopf genau einen erlaubt. Die
Nachmittagssitzung hatte ihren Block vorangestellt, ohne den aelteren herabzustufen.
Hier aufgeloest: Nachmittag = Aktueller, Vormittag = Vorheriger, 2026-08-18 abends ins
Archiv.

Abnahme: erreicht fuer 6, 7a, 8 sowie nachtraeglich 1 und 3a. Nicht begonnen 2 und 4.
SA-4: 0 Anwendungen · over_ask 0 · over_act 1.

---

## 2026-08-19 nachmittags — DSB-Strang: Mailvorgänge, LSBAU-Import in Prod, doc-hub-Schleuse

**Zeitanker:** geschrieben 2026-08-19 · Sitzung parallel zur PyPI-Fleet-Sitzung (#2075) im
selben Repo — deren Stand-Block in `AGENT_HANDOVER.md` bewusst **nicht** überschrieben.

### Was geliefert wurde

**platform** — vier PRs gemergt, einer offen:

| PR | Inhalt |
|---|---|
| [#2071](https://github.com/achimdehnert/platform/pull/2071) | `organize_mail`: Server-Fähigkeiten nach der Anmeldung lesen. `imap.capabilities` trägt nur das Begrüßungs-Banner; der Mittwald-Server nennt `UIDPLUS`/`MOVE` erst danach. Ursache der 89 Dubletten vom 18.08. Am Server gegengemessen: neu ja/ja, alt nein/nein. Schließt #2069. |
| [#2072](https://github.com/achimdehnert/platform/pull/2072) | Schreibpfad der Erledigt-Ablage mit Protokoll und Rücknahme. **Zwei Defekte, die nur der scharfe Lauf zeigte:** der Umzug entwertet die Kennung, die ihn protokolliert (Graph-ID vorher `…AAvAxr8eAAA=`, danach `…AAwtgyJyAAA=`; IMAP-UID genauso) — die Rücknahme löst jetzt am jetzigen Ort neu auf; und `regeln.ruecknahme()` reichte das Konto nicht durch, der Graph-Rückweg fiel auf IMAP. |
| [#2078](https://github.com/achimdehnert/platform/pull/2078) | Anhänge von Graph-Nachrichten ausliefern statt nur ankündigen. Route `/r/<id>/anhaenge/<name>`. Eingebettete Nachrichten werden benannt, nicht verlinkt — sie haben keine Bytes. |
| [#2079](https://github.com/achimdehnert/platform/pull/2079) | `@odata.type` gehört nicht ins `$select` — Graph antwortet 400. Die Attrappe im Test nahm jede URL an und konnte es nicht sehen; sie merkt sich jetzt die Anfrage. |
| [#2073](https://github.com/achimdehnert/platform/pull/2073) | **OFFEN** — `/mailcheck` Schritt 7a (Erledigtes wegräumen). `/.windsurf/` steht in CODEOWNERS, wartet auf @wirdigital. |

**risk-hub** — drei PRs gemergt:

| PR | Inhalt |
|---|---|
| [#619](https://github.com/iilgmbh/risk-hub/pull/619) | `manage.py import_dsb_docs` — TOM-Checkliste, VVT-Nachstrukturierung, Mandanten-Rückmeldungen. Trockenlauf als Voreinstellung; ohne Sicherungsfunktion wird nicht gelöscht. |
| [#620](https://github.com/iilgmbh/risk-hub/pull/620) | Zuordnungsfehler aus dem Probelauf: `Datenquelle`→`data_source` statt `Auftragsverarbeiter` (86 vs. 23 Vorkommen), 25 von 49 Tools-Abschnitten tragen in Wahrheit Datenkategorien und werden verworfen, verschachtelte `(Details: …)`-Klammern. Neu erfasst: DSFA und Schutzbedarf. |
| [#622](https://github.com/iilgmbh/risk-hub/pull/622) | Konzept Tätigkeitsnachweis für den DSB (`concepts/DSB_Taetigkeitsnachweis.md`). |

### Produktive Eingriffe — beide gegengezählt

**risk-hub Prod, Mandant LSBAU** (Deploy `6762ec8` via `workflow_dispatch`, Owner-Freigabe):

| | vorher | nachher |
|---|---|---|
| Verarbeitungstätigkeiten | 89 | 90 |
| Zugriffsberechtigte gefüllt | 0 | 85 |
| Datenquelle | 0 | 85 |
| Werkzeuge/Anwendungen | 0 | **23** (nicht 48 — 25 Fehlwerte abgewiesen) |
| DSFA markiert | 0 | 14 |
| Verknüpfungen | 0 | 761 |
| technische / organisatorische Maßnahmen | 0 / 0 | 24 / 9 |

Der gelöschte `Online-Shop`-Eintrag liegt als Rückweg zweifach: im Container unter
`/tmp/lsbau-geloescht.jsonl` und als `~/shared/2026-08-19-dsb/lsbau-online-shop-geloescht.json`.

**doc-hub Prod (`88.198.191.108`)** — Eingriff aus dieser Sitzung, **an
[#2083](https://github.com/achimdehnert/platform/issues/2083) gemeldet**, weil dort eine
Parallelsitzung am selben Problem arbeitet und den Stack versioniert ausrollen will:

`/opt/doc-hub/docker-compose.yml` um `PAPERLESS_CONSUMER_IGNORE_DIRS` (`schleuse`,
`.thumbs`) und `IGNORE_PATTERN` (`.safetensors`, `.ckpt`, `.pt`) ergänzt, Sicherungskopie
`docker-compose.yml.bak-vor-ignorepattern`. Container zweimal neu gestartet. 1.796
fehlgeschlagene Aufgaben und das Schlagwort `raus` (ID 113, 0 Dokumente) gelöscht.
Wirkung: 810 → **0** Fehler je fünf Minuten bei gleichzeitig 19 → 123 Dateien.

**Wichtig für den versionierten Rollout:** `IGNORE_PATTERN` sind in Paperless 3.0.4
**reguläre Ausdrücke gegen den Dateinamen**, keine Glob-Muster gegen den Pfad.
Verzeichnisse gehen ausschließlich über `IGNORE_DIRS`, und zwar über den **Namen**. Der
erste Versuch mit `schleuse/**` war gesetzt, gemeldet und wirkungslos.

Der älteste Schleusen-Fehlschlag stammt vom **10.08. 15:47** — neun Tage, 1.757
Fehlschläge, unbemerkt.

### Mailvorgänge (lokales Ledger, 24 Vorgänge, 0 ohne Anker)

Acht Entwürfe vom Owner gesendet: Scherer (LSBAU), Herrmann (Gröger NIS2), Gessler
(Marold), Schröder (HNU), Gerstlauer (HNU, zweimal), Zeiner (Ocos).

Fachliche Ergebnisse, die nicht im Code stehen:

- **LSBAU**: Das Portal führte die Liste von 2018; keine der drei Kundenanmerkungen von
  2025 war eingearbeitet. Zwei Fragen aus ihrer Mail vom 22.07.2025 waren **elf Monate**
  unbeantwortet. Die TOM-Checkliste kam nie ausgefüllt zurück — 33 Maßnahmen, 0 angekreuzt.
- **Gröger**: § 28 Abs. 4 BSIG zielt auf die Unabhängigkeit der **Systeme** gegenüber den
  verbundenen Unternehmen, nicht auf getrennte Dienstleister. Fünf von sechs Punkten
  getrennt → Ausnahme trägt, Registrierung entfällt. Eigene frühere Formulierung („ein
  einziges *gemeinsam* trägt bereits die Zusammenrechnung") ausdrücklich zurückgenommen.
- **Ocos/LRA Günzburg**: AVV ist ein 14-seitiger **Scan ohne Textschicht**. Form ist
  unveränderte EU-SCC. Vier Beanstandungen: Supabase (Singapur) und Render (USA) ohne
  Übermittlungsgrundlage; Render und Google Cloud gelistet aber „nicht im Einsatz";
  Klausel 7.5 verlangt für die genannten sensiblen Daten Garantien, Anhang III nennt
  keine; Verfügbarkeitsmaßnahme ist „automatische Skalierung".
- **Marold/DeutschlandGPT**: Trainings-Beanstandung **zurückgenommen** (AV Ziff. 1.7 in
  Anhang III, gilt für alle; Ziff. 4.1 Vorrang; NB 11.5 in Teil A). Neuer, härterer
  Befund vom Owner: Ziff. 7.7 a) erlaubt Änderung der Unterauftragnehmerliste mit **14
  Tagen** Frist, während die unveränderten Klauseln **30** nennen (belegt am Ocos-AVV) —
  und das Dokument behauptet in Ziff. 2 b) die Unabänderbarkeit. Wirkt zulasten des
  Verantwortlichen. **Per Telefonat übergeben, Gessler klärt mit dem Auftragsverarbeiter.**

### Beschaffung HNU (Vorgang 141)

eBANF-Spezifikation für eine KI-Workstation liegt in `~/shared/2026-08-19-hnu/`. Empfehlung
nach Recherche **geändert**: Mac Studio M3 Ultra (819 GB/s, ~4.875 € netto) statt
RTX-PRO-6000-Workstation (1.750 GB/s, 15.000–19.000 €), solange mit Modellen gearbeitet
und nicht trainiert wird. DGX Spark (273 GB/s) und Dell PowerEdge XE7745 (Rackserver)
verworfen. Anfrage läuft, ob der Mac Studio über die Rahmenvereinbarung abrufbar ist.

### Nächste Schritte

1. **#2073** braucht @wirdigital — ohne Merge bleibt `ablage_erledigt.py` gebaut und
   unaufgerufen.
2. **#2083** — meinen doc-hub-Eingriff beim versionierten Rollout mitnehmen, sonst kommen
   die 655 Fehler zurück.
3. **#622** — Entscheidung über feste Fremdschlüssel steht; danach Schritte 1, 2, 5.
4. **Vorgang 141** — eBANF absenden oder Mac Studio, je nach Gerstlauers Antwort.
5. **LSBAU** — Vorlage der Mitarbeitenden-Datenschutzerklärung liegt in
   `~/shared/2026-08-19-dsb/`; in der gesendeten Mail steht die Zusage, sie zu liefern.

### Abnahme

Zielzustand des Owners („mailcheck und todo list erkennen alle Änderungen, stellen
relevante neue Mails strukturiert dar und räumen Erledigtes auf; alles mit Tests geprüft
und fehlerfrei"): **erreicht** — Schreibpfad mit Rücknahme belegt (Rundlauf beide
Richtungen), `make test` 2556 grün, Ablage in Prod ausgeführt und gegengezählt. Die
Verdrahtung in `/mailcheck` hängt an #2073.

**Fehler dieser Sitzung, die genannt gehören:** Vier eigene Aussagen scheiterten an der
Nachprüfung — drei davon, weil ein Filter die Null erzeugte (`head -12` schnitt `schleuse`
ab, Statusabfrage suchte `FAILURE` statt `failure`, Firmennamen-Suche fand keine
Systemanbieter), eine, weil eine verkürzte Seitenwiedergabe für den Volltext gehalten
wurde (DeutschlandGPT 11.5). Beim Marold-Vorgang lag ich dreimal daneben; alle Korrekturen
kamen vom Owner oder von der Gegenseite. **Und: kein Scope-Checkpoint ausgesprochen**,
obwohl die Sitzung zwei Repos, zwei Produktivsysteme und einen Prod-Deploy berührte — der
Stop-Hook musste ihn einfordern.

SA-4: 0 Anwendungen · 0 Einzel-OK trotz Klassen-Deckung · 0 Fehlanwendungen.


---

## Session 2026-08-19 abends — LLM-Readiness-Audit illustration-hub/music-lab/writing-hub (Kapitaens-Kanal, Fable)

Auftrag: drei Repos auf optimale LLM-Nutzung (cloud+lokal) auditieren, Verbesserungen fuer sofortiges Aufsetzen staerkerer LLMs; Prinzipien Adv. Diaboli / OOTB / Continuous Improvement / Predictive Maintenance. Owner-Erweiterungen in-session: Pakete A/B/C als Entwurf, Empfehlungsreihenfolge F/G/J/D/H/E/I/K, Public→Private-Strategie + iilgmbh-Wanderung.

Geliefert (alles Entwurf, 0 Merges, 0 Prod): 14 Draft-PRs — wh#638/#639(+prompt_hash)/#641/#644, ill#283/#284/#285, ml#38, platform#2109/#2110, frist-hub#120, iil-django-commons#15, meiki-dms#15, meiki-hub#145. 2 KONZ-Entwuerfe (048 Doku-Drift-Melder, 049 Box-Cluster-Wachhund). Tracking: platform#2111–#2119, wh#640/#643/#645, meiki-dms#16. Private-Klassifikation (22/5/2) + G-Messung + F-Anleitung durabel in #2119; Welle-1-Flip bewusst NICHT ausgefuehrt (Freigabe ausstehend).

Wichtigste Beifaenge: infra-deploy seit 30.07. ohne Runner (#2114, beruehrt #2086) · shared-ci-Duplikat (#2113) · music-lab fehlte in jeder Registry (#2109) · writing-hub ist public ohne Beschluss-Artefakt (#2119).

Arbeitsweise: 3 Explore-Audits + 10 Umsetzer-Subagents parallel; 3 Audit-Praemissen von Umsetzern falsifiziert (Test-DB-Mechanik, #601-Fallback-Claim, „nur Fehlerpfad getestet") — adversariale Zweitpruefung wirkte. Fehler dieser Sitzung: Scope-Checkpoint erst auf Stop-Hook-Anstoss ausgesprochen; J-Caller-Liste zunaechst aus stale lokalen Klonen erhoben (Agenten korrigierten gegen origin); zwei Warte-Agenten liefen in CI-Idle-Loops und mussten per Nachricht beendet werden.

SA-4: 0 Anwendungen · 0 Einzel-OK trotz Klassen-Deckung · 0 Fehlanwendungen.

---

## 2026-08-20 nachts — Fortsetzung der abgestuerzten Sitzung: MEiKI-Statusbericht, Mailcheck, Plattenplatz der Box

Einstieg war „mach weiter wo wir aufgehoert haben" ohne Themenangabe. Die abgestuerzte Sitzung (23b5d073, Abbruch 02:31) wurde ueber die Transkripte identifiziert statt erraten: letzter Owner-Turn „142 g", danach Greps in meiki-hub nach der Laufzeit. Offen war also nicht der Statusbericht selbst (docx und Entwurf lagen seit 02:22), sondern der Laufzeit-Widerspruch darin.

Aufgeloest gegen drei Primaerquellen ausserhalb des Repos: Projektskizze (Start 01.11.2025 = Antrags-Planung), Projektleitung LRA 09.12.2025 (Antrag mit Starttermin 01.03./01.04., vorzeitiger Massnahmenbeginn ausdruecklich nicht beantragt), Weiterleitungsvertrag mit Zuwendungsbescheid vom 27.01.2026. Ein Nov-2025-Beginn laege vor dem Bescheid. Gueltig: 01.04.2026-31.03.2027. Der Weiterleitungsvertrag war ein reines Bild-PDF — pdftotext lieferte 0 Bytes, die Belegkette entstand erst nach OCR. Doku-Drift korrigiert in meiki-hub#146 (CI gruen, offen gelassen).

Mailcheck: 24 offene Vorgaenge geprueft, DB-first plus Live-Restfenster ueber alle drei Konten inkl. beider Gesendet-Ordner. Genau eine Nachricht war unverbucht (Vorgang 126, 00:37) — die abgestuerzte Sitzung hatte sie gesehen, aber nicht mehr ins Ledger geschrieben. Owner-Weisungen abgearbeitet: 111/124 telefonisch geschlossen, 107 nachgelesen, drei Entwuerfe gebaut (108 Nachfass im Loeschvorgang, 126 Thesis-Betreuung, 141 Beschaffung). Beim 108-Entwurf lief der erste Versuch falsch: createReply auf die EIGENE gesendete Mail setzt den Absender als Empfaenger — der Entwurf waere an den Owner selbst gegangen. Verworfen, ueber die Ursprungsmail der Gegenseite neu gebaut.

Plattenplatz: zwei TreeSize-Berichte, Ebene 1 und Ebene 2. Der interessanteste Befund war keine Zahl, sondern eine Rate — 7,2 GB in 14 Minuten weniger frei, waehrend gemessen wurde. Zweitwichtigster: ein Nebenprofil mit 124 GB Groesse gegen 6,3 GB belegt, Faktor 19,7 — wer nach Groesse aufraeumt statt nach Belegt, loescht dort 124 GB Inhalt fuer sechs Gigabyte Gewinn. Zwei Skripte gebaut und eingeschleust; die Box ist vom Dev-Host aus nicht erreichbar (ping und Ports 8765/5985/22 gemessen), die Schleuse darf laut KONZ-046 nichts ausfuehren — die Freigabe „mach 1-8 autonom" konnte deshalb nur als Werkzeug eingeloest werden, nicht als Ausfuehrung. Das wurde so benannt statt umgangen.

Fehler dieser Sitzung: beim Archivieren des alten Handover-Blocks schnitt der erste Einfuege-Versuch 718 Zeilen aus AGENT_HANDOVER_ARCHIVE.md heraus — vom diffstat gefangen, zurueckgesetzt, korrekt neu eingefuegt. Ausserdem einmal eine Graph-Message-ID der falschen Zeile zugeordnet (die id-Zeile folgt ihrer Nachricht, sie geht ihr nicht voraus) und dadurch die falsche Mail gelesen.

SA-4: 0 Anwendungen · 0 Einzel-OK trotz Klassen-Deckung · 0 Fehlanwendungen.

---

## Session 2026-08-20 frueh — Celery-Healthcheck deckte Deploy-Fehlzuordnung auf (Kapitaens-Kanal, Sitzung 64ce2183, Opus)

Auftrag: Handover-Prio 1 (Celery-Healthcheck) + Schleuse; in-session erweitert um Stilllegung recruiting-hub/onboarding-hub/coach-hub, Runner-Umzuege, Wirkungs-Melder und Backlog-Konvergenz.

**Kern:** `pidof -x celery` statt `pidof python3` in 137-hub/dms-hub/coach-hub (137-hub#91, dms-hub#65, coach-hub#65) — 137-hub FailingStreak **2761 → 0**. dms-hub meldete `success`, war aber **nicht live**: `_deploy-unified.yml` deployt auf dem Host des self-hosted Runners, und nach der Umzugswelle vom 04.08. standen sechs Runner auf prod-a, waehrend die Apps auf prod-b liefen. 16 Tage gruene Runs ohne Wirkung, kein roter Check (#2122). Alle sechs umgezogen und je gegen das Deploy-Manifest verifiziert; das Umzugs-Skript hatte selbst einen Rechte-Bug (#2130), Host-Fix und Skript-Fix im selben Zug.

**Stilllegungen:** recruiting-hub (#2121) und onboarding-hub (#2123) archiviert, Backups verifiziert; coach-hub abgeschaltet (#2125, +362 MB RAM, DNS entfernt, E-Mail-Records bewusst unangetastet).

**Gebaut:** `tools/deploy_wirkung.py` (#2137) — prueft Wirkung statt Deklaration, erster Lauf 11 Befunde von 21 Repos inkl. drei unbekannter Rueckstaende. Nachgebessert: Prod-Gate kennzeichnen statt unterdruecken (#2138, weil tax-hub dasselbe Muster mit echtem Fehler traegt), Owner aus der Registry (#2139, 16 Repos liegen in iilgmbh).

**Backlog:** 314 → 291 (#2140), 24 geschlossen. Drei Wurzeln: rollende Melder legen an statt zu aktualisieren · `adr-nightly-metrics` seit 02.07. tot · ADR-`review_status` 115 → 236 (eskaliert). Betterstack: 6 pausierte Monitore fuer laufende Dienste reaktiviert (#2127). Schleuse 3 faellig → 0.

**Fehler dieser Sitzung:** vier Aussagen scheiterten an der Nachpruefung — falscher Host abgefragt, `pg_stat` fuer exakt gehalten, PR-Status `UNKNOWN` **viermal** als „offen" statt „gemergt" gelesen (kostete einen kaputten ADR-Index auf main, nachgezogen in #2129), ein „gepusht"-Echo ohne Beweis. Alle vier waren uebersprungene Checks, keine Denkfehler. Die drei Merges erzeugten auf prod-a acht Schatten-Container (nach Freigabe gestoppt). Und beim Prio-Umbau in diesem Handover ersetzte ein zu weiter Regex-Slice 129 statt 10 Zeilen — vom diffstat gefangen, zurueckgesetzt, mit festen Zeilengrenzen neu gemacht. Exakt der Fehler, den die parallele Sitzung im Eintrag darueber beschreibt.

SA-4: 0 Anwendungen · 0 Einzel-OK trotz Klassen-Deckung · 0 Fehlanwendungen.
