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
