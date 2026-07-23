# Agent Handover — Platform Infra Context

**Pflicht-Lektüre beim Session-Start jedes Coding-Agents.**
Enthält MCP-Tool-Mappings, Infra-Zugänge, Deploy-Targets und Scripting-Referenz.

<!-- Konvention: dieser Abschnitt hält NUR den "## ⚡ Aktueller Stand" + max. EINEN
     "## ⚡ Vorheriger Stand" (den jeweils jüngsten). Alles Ältere wandert nach
     AGENT_HANDOVER_ARCHIVE.md (siehe Verweis unten) — nicht hier anhäufen. -->

**Archiv älterer Session-Stände:** [`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md)
(Blöcke älter als der aktuelle + 1 vorherige Stand).

## ⚡ Aktueller Stand (2026-07-22 Abend — ADR-281 §8.1 auf 6/6 komplettiert, ADR-281 `accepted`, §8.2-Negativtest gemessen + beide Kanten gefixt)

**Kern in einem Satz:** Kriterium 5 war die letzte offene Prämisse von ADR-281 — diese
Session *war* die frische Session, die er brauchte; er trägt, der ADR steht auf `accepted`,
und der §8.2-Negativtest ist gemessen statt vorausgesetzt.

**ADR-281 §8.1 Kriterium 5 — bestanden.** Der am Nachmittag vorbereitete Symlink
(`~/.claude/skills/adr281-k5` → `~/shared/adr281-k5`, gesetzt 16:23) lag beim Start dieser
Session bereits da: der Skill stand **vor jeder Dateisystem-Aktion** im Roster, der Body lud
inklusive `MARKER-K5-V1`, das Argument-Echo stimmte. Werkzeugversion **2.1.217** — identisch
zum Erstlauf, der Vergleich ist also nicht von einem Harness-Upgrade verfälscht. Damit ist
der Erstlauf-Verdacht widerlegt, Symlinks würden nur *dynamisch* aufgelöst: **beide Ladewege
funktionieren.** §8.1 steht auf **6/6**.

**ADR-281 auf `accepted`** ([#1366](https://github.com/achimdehnert/platform/pull/1366), offen,
CI grün). Accept-Bedingung des ADR ist §8.1 (binäre Muss-Kriterien, „scheitert eines →
`rejected`"); §8.2/§8.3 sind Phase-2/3-Gates und keine Accept-Vorbedingungen. Nachgeführt
wurde nicht nur der Status: der Verifikationsstand-Block „**NICHT verifiziert: dass ein
symlinkter Skill tatsächlich lädt**" — die tragende offene Prämisse des ADR — ist als überholt
markiert, §8.1 hat eine Ergebnistabelle je Kriterium, Migration-Tracking Phase 0+1 auf ✅, und
das Risiko „Symlink lädt doch nicht" ist als gemessen widerlegt entfernt.

**Der §8.2-Negativtest brauchte zwei Läufe — und das war der Fund.** Mit dem in §8.2
vorgeschlagenen Namen `adr281-dangling`: `dangling=0`, scheinbar derselbe Fehlschlag wie im
Erstlauf. Mit dem kanonischen Namen `next`: `dangling=1`, korrekte Befund-Zeile. Ursache aus
dem Code belegt, nicht vermutet — in `doctor.py` beendete die `name not in canon`-Prüfung die
Klassifikation per `continue`, **bevor** der dangling-Zweig erreicht wurde. Der Fix aus
[#1332](https://github.com/achimdehnert/platform/issues/1332)/[#1335](https://github.com/achimdehnert/platform/pull/1335)
zielte auf die kanonische Form und tut dort, was er soll.

**Beide Kanten sind gefixt, nicht wegdokumentiert** ([#1369](https://github.com/achimdehnert/platform/pull/1369),
offen, CI grün — schließt [#1368](https://github.com/achimdehnert/platform/issues/1368)):
- **Kante 1:** dangling-Prüfung vor die canon-Prüfung gezogen; Zusatz „(zudem nicht in der
  Quelle)" hält die zweite Eigenschaft sichtbar. Drift-Score unverändert — beide Fälle zählen 1.
- **Kante 2:** eigene maschinenlesbare Zeile `=== DANGLING: N ===` plus `--fail-on-dangling`.
  Hintergrund: ersetzt ein kaputter Link einen zuvor `fehlenden` Skill, sinkt `missing` um 1
  während `dangling` um 1 steigt — die **Score-Summe bleibt gleich**. Auf dieser Maschine ist
  der normale Exit-Code wegen Grund-Drift 3 ohnehin dauerhaft `1` und taugt als Gate nicht;
  mit dem Flag ist er 0 im Normalfall und 1 nur bei gebrochenem Link. Die Auflage „das
  Phase-2-Gate triggert auf die Befund-Liste, nicht auf die Score-Summe" steht in ADR-281 §8.2
  selbst, nicht nur im Issue.
- **Drei Regressionstests, alle drei ohne den Fix rot verifiziert.** Beim Kante-1-Test stehen
  die Etikett-Assertions bewusst vor den Zeilen-Assertions — sonst wäre er ohne den Fix schon
  an der fehlenden Ausgabezeile gescheitert und hätte über die Fehlklassifikation nichts
  bewiesen. Zusätzlich live gegengeprüft, nicht nur synthetisch; Testlinks danach entfernt,
  `doctor.py` zurück auf DRIFT-SCORE 3.

**Format-Gate-Kollision, bewusst entschieden statt umgangen:** Der lokale Push-Gate
`block_unformatted_push.sh` verlangt `ruff format` für geänderte `.py`; das Repo ist aber zu
**475 von 749 Dateien** unformatiert, und genau gegen solche Sweeps existiert
`check_noop_changes.py` in `tools-tests.yml`. Formatieren hätte 135 geänderte Zeilen auf 598
aufgebläht. Owner-Entscheid: **zwei Commits** — `e647d05` (Fix, allein reviewbar) und
`9ac001a` (reines `ruff format`). Der SUGGEST-Check wird den zweiten melden; das ist der
erwartete Preis der Trennung. Platform-CI selbst prüft `ruff format` für diese Dateien nicht.

**⚠️ hetzner-prod SSH war ~15 Minuten weg — transient, Ursache unbekannt**
([#1370](https://github.com/achimdehnert/platform/issues/1370)): gegen 21:35 lieferte Port 22
**Connection refused**, gegen 21:50 war er wieder offen, ohne dass am Host etwas getan wurde.
In dem Fenster liefen weder `session-memory` (Phase 2) noch `claude-policy` — beide nutzen
denselben Transport. **Nachgeholt und verifiziert:** `session:platform:20260722:adr281-k5-abend`
und `error:platform:20260722-doctor-dangling-canon-order` sind geschrieben, beide per
`session-memory get` mit `found: true` bestätigt. Es ist also **nichts verloren**.
**Kein Prod-Ausfall, geprüft statt vermutet:** `risk-hub.iil.pet/livez/` und
`trading-hub.iil.pet/livez/` lieferten während des Ausfalls beide **200** — der Host routete
HTTP durchgehend, nur `sshd` nahm nichts an. Ob das mit der Speicherlage aus
[#1303](https://github.com/achimdehnert/platform/issues/1303) zusammenhängt, ist
**Hypothese, nicht geprüft**; billigster Check ist das Host-Journal um 21:35 ohne Namensfilter.

**Werkzeug-Befund am Session-Ende** ([#1372](https://github.com/achimdehnert/platform/issues/1372)):
der Push-Gate `block_unformatted_push.sh` hat **dreimal** falsch blockiert, aus zwei
unabhängigen Gründen. (a) Sind `add`/`commit`/Push in einem Bash-Aufruf verkettet, läuft der
Hook vor dem Commit, findet `origin/main...HEAD` leer und fällt auf `HEAD~1` zurück — er misst
dann die `.py`-Dateien des **vorherigen, fremden** Commits. Traf einmal eine reine
Markdown-Änderung. (b) Die Trigger-Erkennung grept den **gesamten** Kommandotext inklusive
Heredoc — der Versuch, #1372 selbst per Heredoc-Body anzulegen, wurde blockiert, weil der
Fließtext die gesuchte Zeichenfolge enthielt. Workarounds (getrennte Aufrufe, `--body-file`)
sind verifiziert; brisant ist, dass der Hook im Fehlerfall zu `ruff format .` rät — genau der
Repo-weite Sweep, gegen den `check_noop_changes.py` gebaut wurde.

**Nicht verifiziert / bewusst offen:** ADR-280 §8.1 unverändert blockiert (Owner-Entscheid
`--allow-live`) · beide PRs dieser Session warten auf 2.-Owner-Review, nichts davon ist auf
`main`.

## ⚡ Vorheriger Stand (2026-07-22 Nachmittag — ADR-280/281 gemergt, Symlink-Ladetest real durchgeführt: 5/6 bestanden + zwei Werkzeug-Befunde; Worktree-Bestand 30→23)

**Kern in einem Satz:** Die beiden Skill-Lane-ADRs liegen auf `main`, der ADR-281-Ladetest
wurde **real ausgeführt** statt weiter vorausgesetzt — er trägt, deckt aber zwei Lücken auf,
die vor dem Scharfschalten der Gates zu schließen sind. Beide ADRs bleiben bewusst auf
`status: proposed`.

**Gemergt (alle CI-grün, Head-OIDs vor dem Merge gegen `git ls-remote` geprüft):**
- [#1295](https://github.com/achimdehnert/platform/pull/1295) ADR-280 Rev 2 · [#1296](https://github.com/achimdehnert/platform/pull/1296) ADR-281 Symlink-Verteilung
- [#1321](https://github.com/achimdehnert/platform/pull/1321) session-start Phase 0.7 erkennt hängende Deploy-Gates
- [#1294](https://github.com/achimdehnert/platform/pull/1294) lief über auto-merge durch (`$ARGUMENTS`-Regression zurückgenommen)

**ADR-281 §8.1 Symlink-Ladetest — durchgeführt, Artefakt [`docs/verifications/2026-07-22-adr281-symlink-ladetest.md`](docs/verifications/2026-07-22-adr281-symlink-ladetest.md):**
Ein handgesetzter Symlink unter unbenutztem Namen, Werkzeugversion **2.1.217**, Ausgangscommit `ef4d190`.
- **Bestanden 1, 2, 3, 6:** Skill erschien **ohne Session-Neustart** im Menü (Roster-Refresh
  kam als `system-reminder` Sekunden nach dem `ln -s`), Body lud über den Symlink,
  `$ARGUMENTS` wurde ein- und mehrwortig-gequotet korrekt eingesetzt, `rm` des Links
  entfernte den Skill sauber und ließ die Quelldatei unberührt.
- **Kriterium 4 ist als Testfall untauglich** — nicht der Symlink versagt: Nach Änderung der
  Quelle lieferte die Re-Invocation weiter den alten Body, ein **frischer Skill-Name** auf
  denselben Inhalt aber sofort den neuen. Ursache ist der **Session-Cache des Harness** für
  bereits geladene Skills; eine generierte Kopie verhielte sich identisch. Kriterium 4
  unterscheidet Symlink und Kopie also gar nicht. Neufassung im Artefakt vorgeschlagen.
- **Offen:** Kriterium 5 (frisch gestartete Session) — aus einer laufenden Session nicht erzeugbar.

**Zwei Werkzeug-Befunde aus demselben Lauf:**
- **`doctor.py` erkennt einen dangling Symlink NICHT.** `ln -s /nonexistent …` ließ
  `dangling=0` und den DRIFT-SCORE unverändert. Der von ADR-281 §8.2 geforderte Negativtest
  („ein gebrochener Link **muss** rot werden") würde heute **nicht** bestehen. Zu fixen,
  bevor der Gate scharf geht — sonst trägt der Gate-Name eine Garantie, die er nicht einlöst.
- **Die Symlink-Klassifikation existiert bereits** (`Symlinks ok/symlink-stale/dangling`),
  muss also nicht neu gebaut, nur scharf gemacht werden.

**ADR-280 §8.1 Betriebsnachweis konnte NICHT beginnen — Ursache benannt:** Die drei
migrierten Piloten sind live **nicht installiert** (`doctor.py --kind skills` →
`fehlend: escalate, issues-offen, next`). Belegt in dieser Session: `/issues-offen` und
`/next` liefen und trugen den Footer `source=.windsurf/workflows/<name>.md` — ein Pfad, den
`main` seit #1290 nicht mehr enthält. Es lief also die **alte, verwaiste `commands`-Lane**.
Der nötige Schritt ist `generate.py --kind skills --allow-live` (gegateter Live-Rollout,
ADR-230 §8, Gate mit 8 offenen Checkboxen) — **bewusst nicht ausgeführt**.

**Aufräumen:** Worktree-Bestand **30 → 23**. 3 gemergte + 4 stale entfernt; für jeden stale
Worktree vorher belegt, dass sein Inhalt anderswo liegt oder verworfen wurde (u.a.
`ci-union-gate-warnfirst` = geschlossener [#893](https://github.com/achimdehnert/platform/pull/893),
auf `main` durch das strengere [#963](https://github.com/achimdehnert/platform/pull/963) ersetzt;
`oidc-ready-codeguard-ingest` trug noch `password:`, `main` ist reines OIDC). Branches leben
weiter, Restore-Manifest in `.git/worktree-reaper-manifest.jsonl`. **5 dirty Worktrees**
schützte der Guard — unangetastet.

**Session-Start-Reconciliation fand eine falsche Handover-Prio:** „5 PRs, alle
CONFLICTING/DIRTY, brauchen Rebase" stimmte nicht mehr — [#892](https://github.com/achimdehnert/platform/pull/892)/[#893](https://github.com/achimdehnert/platform/pull/893)
sind CLOSED, die übrigen drei MERGEABLE. Sie brauchten Review, nicht Rebase.

**`/issues-offen` lief mit Nullbefund** (0 neue PRs) — der einzige DO-NOW-Kandidat
[#1304](https://github.com/achimdehnert/platform/issues/1304) war bereits durch
[#1306](https://github.com/achimdehnert/platform/pull/1306) gelöst, und zwar **anders als das
Issue vorschlug**: der dort empfohlene mechanische Header-Sweep hätte auf einen Befehl
gezeigt, der die Zieldatei gar nicht erzeugt.

## ⚡ Vorheriger Stand (2026-07-21 — Skill-Lane-Konsolidierung: ADR-280 Rev 2 nach externem Sparring, ADR-281 Symlink-Verteilung, /adr-Skill + adr-threshold-Policy repariert)
**Laufender Session-Log:** [`AGENT_HANDOVER_LOG.md`](AGENT_HANDOVER_LOG.md) — append-only,
neueste Einträge unten. Dort schreiben Sessions seit KONZ-027 Arm A ihren Stand hin, damit
parallele Sessions sich nicht gegenseitig blockieren. **Diese** Datei hier bleibt die
kuratierte Sicht (Prio-Tabelle + aktueller Stand) und wird weiterhin umgeschrieben.

## ⚡ Aktueller Stand (2026-07-21 — Skill-Lane-Konsolidierung: ADR-280 Rev 2 nach externem Sparring, ADR-281 Symlink-Verteilung, /adr-Skill + adr-threshold-Policy repariert)

**Auslöser war ein Nebenbefund**, kein geplanter Strang: beim Rebase von #1013 war nicht entscheidbar, in welche der zwei Skill-Lanes (`.windsurf/workflows/` → `~/.claude/commands/` vs. `skills/` → `~/.claude/skills/`) ein **neuer** Skill gehört. Owner-Weisung 2026-07-21: keine Parallelexistenz.

**Geliefert:**
- **#1290 gemergt** — Phase 1: 3 Piloten (`next`, `escalate`, `issues-offen`) nach `skills/`; `check_workflow_index.py` scannt jetzt **beide** Lanes, `tools-tests.yml` triggert auf `skills/**`, 5 neue Tests. Nebenbefund dabei: `antwort-modus-schablone` stand seit 2026-06-05 in **keinem** Index — die Lane war für den Vollständigkeits-Gate schlicht unsichtbar.
- **#1291 gemergt** — ADR-280 (Rev 1). **#1295 offen** — ADR-280 **Rev 2**, ergebnisoffene Neubewertung.
- **#1296 offen** — ADR-281: Skills als **Symlink** statt generierter Kopie (amendiert ADR-230 §2.2).
- **#1292 gemergt** — `/adr`-Skill: `gen_adr_index.py` als Pflichtschritt, Abschluss-Checkliste, Anti-Patterns, Changelog (alle drei fehlten).
- **#1293 auto-merge gequeued** — `policies/adr-threshold.md`.
- **#1294 offen** — Regression aus #1290 zurückgenommen.
- **#1118 geschlossen** — superseded, OIDC lag längst auf main.

**Der zentrale Befund — meine Prämisse war falsch:** Rev 1 behauptete, `$ARGUMENTS` entfalle unter Agent Skills. Geprüft gegen die laufende Umgebung (`claude --version` = **2.1.216**, Doku 2026-07-21): *„Custom commands **have been merged into skills** … both create `/deploy` and **work the same way**."* Skills unterstützen `$ARGUMENTS`, `$ARGUMENTS[N]`, `$N`, benannte `$name`. Folgen: Migrationskosten von Option A waren zu hoch angesetzt, „Pilot zuerst" war eine Scheinbegründung, und im Pilot wurde funktionierendes `$ARGUMENTS` durch Prosa **ersetzt** (→ #1294). Zwei unabhängige externe Zweitmeinungen fanden das; beide empfahlen „überarbeiten".

**ADR-280 Rev 2 ruht jetzt auf EINEM geprüften Argument** statt auf vieren: nur die Verzeichnisform trägt **Supporting Files** — damit werden die drei `distribute: false`-Persona-Prompts (Typ 3) per Konstruktion zu Nicht-Skills, die lane-spezifische Sonderlogik entfällt. Nicht tragend und offen so benannt: kein Hersteller-Trend (nicht belegbar — die Doku sagt „keep working", `deprecat|legacy|sunset` liefert **keinen** Treffer), kein Kontextvorteil, keine Argument-Migration.

**Zwei Funde, die keine der Reviews hatte:**
- **Symlinks sind offiziell unterstützt** (`~/.claude/skills/<name>` darf ins Repo zeigen) → Drift wird **strukturell unmöglich** statt detektiert. Manifest, Content-Hash, MANAGED-Footer und Round-Trip-Gate würden für diese Lane entfallen. → ADR-281.
- **Cowork-/Cloud-Sessions inkl. Routinen lesen `~/.claude/skills/` NICHT.** Das gesamte Verteilmodell endet an der Maschinengrenze — unabhängig davon, welche Lane gewinnt. Getrackt als [#1298](https://github.com/achimdehnert/platform/issues/1298) + Option F in ADR-280 §10.

**ADR-281-Belege:** ADR-230 verwarf Symlinks wegen „volatilem Checkout" — der Einwand galt der Volatilität. **ADR-233 (`2026-06-01`) ist jünger als ADR-230 (`2026-05-30`)** und der Guard **erzwingt** nachweislich (`.git/iil-guard-events.log`: 2 `unauthorized_head_flip` vom 2026-07-21, beide zurückgesetzt — aus dieser Session, ich bin selbst hineingelaufen). Dazu: **ADR-230s Rollout-Gate hat 8 offene Checkboxen, 0 abgehakt** — inkl. „Rollback getestet". Es stehen sich zwei *unbelegte* Zusagen gegenüber; gewählt wurde die mit weniger beweglichen Teilen. Eigene Idee (gepinnter Worktree als Symlink-Ziel) an der Faktenprüfung gescheitert: `platform-pinned` ist 11 Commits hinter main und hat **kein** Pflege-Tooling.

**Zwei Werkzeug-Reparaturen, beide durch eigene Fehler ausgelöst:**
- `/adr` Step 3.3 sagte „INDEX.md ergänzen", die Datei trägt aber `AUTO-GENERATED … do not edit manually`. Wer der Anleitung folgt, landet im roten Gate — passiert bei ADR-280. Der Skill hatte **keine Abschluss-Checkliste**; genau die Lücke, durch die ein Pflichtschritt still überspringbar ist.
- `policies/adr-threshold.md` empfahl `ls docs/adr/ | sort | tail -1`. Real ausgeführt liefert das **`reviews`** (ein Unterverzeichnis) statt `ADR-281` — kein Fehler, sondern ein plausibel aussehendes falsches Ergebnis.

**Wissen gesichert (Outline).** Achtung: `search_knowledge` findet beide Dokumente **nicht** (leeres Ergebnis trotz erfolgreicher Anlage, per `get_document` mit Volltext verifiziert) — Discovery läuft daher über den Memory-Eintrag `lesson:platform:20260721-tool-semantics`, nicht über die Outline-Suche:
> - Lesson: `/doc/2026-07-21-werkzeug-semantik-behauptet-statt-in-der-doku-des-laufenden-werkzeugs-nachgeschlagen-vKYm65cvo7`
> - Konzept: `/doc/skill-verteilung-platform-lane-konsolidierung-auf-skills-symlink-statt-kopie-9gcVWVwDIv`

**⚠️ Live-Kopien dieser Maschine sind seit dieser Session von `main` abgewichen** (`doctor.py --kind commands`, 2026-07-21): `copy-stale=4` · `extra=3` · `fehlend=1`. Konkret: **`/adr` läuft live noch mit der kaputten Step-3.3-Anleitung** (`grep -c gen_adr_index.py ~/.claude/commands/adr.md` = **0**, Quelle = **11**); `escalate`/`next`/`issues-offen` liegen als Leichen im `commands`-Ziel, obwohl sie in #1290 nach `skills/` gewandert sind; `delete-repo.md` fehlt seit #1013. Behebung ist `generate.py --allow-live` — das ist der **gegatete** Live-Rollout aus ADR-230 §8, dessen Gate 8 offene Checkboxen hat. **Bewusst nicht ausgeführt** (Owner-Entscheid, verändert die Skill-Installation der Maschine). Bis dahin nutzt jede Session auf dieser Maschine die alte `/adr`-Anleitung.

**Nicht verifiziert:** kein Betriebsnachweis der migrierten Skills (ADR-280 §8.1, sechs Muss-Kriterien definiert, nicht durchlaufen) · kein Symlink-Ladetest (ADR-281 §8.1 — bewusst nicht vorweggenommen, er verändert die Live-Skill-Installation dieser Maschine).

### ⚡ Nachmittag-Session 2026-07-21 (Opus, reaktiv) — trading-hub Prod-Ausfall behoben, Host-Speicherlage getrackt

- **trading-hub war ~16 h mit HTTP 502 offline** ([#1282](https://github.com/achimdehnert/platform/issues/1282)) und ist wiederhergestellt: `https://trading-hub.iil.pet/livez/` **200**, Root **200**, alle fünf Container laufen. Behebung per `workflow_dispatch` auf dem gepinnten Image `main-9411bda` ([run 29829380875](https://github.com/achimdehnert/trading-hub/actions/runs/29829380875), `completed/success`) — bewusst über den ADR-021-Pfad (Compose-SHA-Manifest + atomarer Sync) statt per Hand-`docker compose up`, um die bekannte `-f`-Ketten-Falle zu meiden. Postgres-Volume `trading-hub_trading_hub_pgdata` durchgehend intakt, kein Zustandsverlust.
- **Ursache war kein Deploy-Fehler, sondern eine Speicher-Notlage auf hetzner-prod** am 2026-07-20 18:26–18:48 UTC: cgroup-OOM auf `python` und `gunicorn`, earlyoom bei `mem avail 5,82 %` und `swap free 0,02 %`. Der erste Canary-Alarm (18:42) liegt mitten in diesem Fenster. Der letzte reguläre Deploy lag am 07-16 — die Kiste ist also *von selbst* gestorben, nicht durch eine Änderung.
- **Offen und getrackt ([#1303](https://github.com/achimdehnert/platform/issues/1303)):** **warum die Container entfernt statt neu gestartet wurden, ist ungeklärt** — alle fünf tragen `restart: unless-stopped`, `docker compose ps -a` war trotzdem leer. Ausgeschlossen: `server-maintenance.sh` (prunet nur Builder/Images), `healthcheck.sh` (kein Docker), `docker-cleanup.sh` (So 03:00, vor dem Start am 19.07.), Actions (kein Worker-Log seit 19.07. 05:50), `deploy.sh` (kein Log seit 13.07.). Billigster nächster Check: dockerd-Journal des 20.07. **ohne** Namensfilter.
- **Restrisiko unverändert dünn:** nach dem Restart 3,4 GB verfügbar, **Swap 4095/4095 MB — 0 MB frei**. `swapoff -a` ist in dieser Lage keine Option (zöge 4 GB zurück ins RAM). Vorbereitetes Freimachen (Restart von `iil_authentik_worker` 485/512, `hub137_worker` 305/512, `dms_hub_worker` 137/512 — alle **unhealthy**) wurde **nicht** ausgeführt: der Permission-Classifier blockte den Container-Restart, Owner entschied „direkt deployen". Der Deploy gelang ohne, die Marge blieb damit unangetastet.
- **Handover-Kollision aufgelöst:** [#1299](https://github.com/achimdehnert/platform/pull/1299) und [#1300](https://github.com/achimdehnert/platform/pull/1300) entstanden 99 Sekunden auseinander aus zwei Parallel-Sessions, beide auf `AGENT_HANDOVER.md`. #1299 hatte den Vorab-Check korrekt ausgeführt und nichts gefunden — #1300 existierte da noch nicht. #1299 ist Träger (nur dort die Block-Rotation), #1300 geschlossen. Die strukturelle Lösung dazu liegt bereits als [#1301](https://github.com/achimdehnert/platform/pull/1301) (KONZ-027, Handover-Fragmente je Session) vor.

## Nächste Schritte (kompakt)

> **⚠️ Vor allem anderen — hetzner-prod Speicherlage ([#1303](https://github.com/achimdehnert/platform/issues/1303)):** Swap **4095/4095 MB belegt (0 frei)**, 3,4 GB RAM verfügbar. Der OOM vom 20.07. hat trading-hub 16 h offline genommen; der nächste trifft irgendein anderes Hub. Zusätzlich ungeklärt, **warum** die Container entfernt statt neu gestartet wurden (`restart: unless-stopped` griff nicht). Beides ist Prod-Risiko, kein Aufräumthema — die Nummerierung unten bleibt davon unberührt.

1. **ADR-280 §8.1 Kriterium 6 — erster Handgriff der nächsten Session, keine Vorbereitung nötig:** §8.1 steht seit dem Live-Rollout auf **5/6** ([`docs/verifications/2026-07-23-adr280-betriebsnachweis.md`](docs/verifications/2026-07-23-adr280-betriebsnachweis.md)). Offen ist nur „Verhalten in einer **neu gestarteten** Session": die messende Session muss die vier Skills **vor jeder Dateisystem-Aktion** im `/`-Menü vorfinden und den Footer eines Aufrufs gegen `source=skills/<name>/SKILL.md` halten. Anders als bei ADR-281 Kriterium 5 liegt **nichts** vorbereitet bereit — die Installation ist persistent. Bei ✅ ist §8.1 6/6 und ADR-280 geht von `proposed` auf `accepted`; bei ❌ gilt laut §8.1 ohne neue Grundsatzdebatte **Option D**.
2. **Cloud-Reichweiten-Lücke [#1298](https://github.com/achimdehnert/platform/issues/1298):** Richtungsempfehlung liegt seit 2026-07-23 als Kommentar am Issue (Option 1 „repo-lokale `.claude/skills/`" vor Option 2 „Account-Skills"). Der im Issue genannte billigste Check ist **lokal nicht durchführbar** — die vier Cloud-Routinen sind keine Repo-Dateien, sie leben cloud-seitig. Nächster Schritt ist ein Listing der tatsächlichen Routinen (`/schedule` bzw. `CronList`) + Prüfung, ob eine davon einen `/`-Skill referenziert. **Bis dahin nichts bauen** — beide Optionen führen eine neue Verteil-Route ein und sind owner-/ADR-gegatet (ADR-280 §10 Option F).
3. **Print-Agent externer US-LLM ([#1297](https://github.com/achimdehnert/platform/issues/1297)) — PR liegt vor:** [#1377](https://github.com/achimdehnert/platform/pull/1377) stellt das LLM-Enrichment auf lokales Ollama um, extern nur per Opt-in; wartet auf 2.-Owner-Review. Hintergrund unverändert: Defaults `cerebras`/`groq` hart im Code (`print_agent.py:268/269`), realer Abfluss am 2026-07-21 (Kundenanschrift an Groq).
4. **Review-Stau: 1 offener PR** (gemessen 2026-07-23 06:20 via `gh pr list`) — [#1377](https://github.com/achimdehnert/platform/pull/1377). [#1366](https://github.com/achimdehnert/platform/pull/1366) und [#1369](https://github.com/achimdehnert/platform/pull/1369) sind **MERGED** (06:05/06:06 UTC), [#1367](https://github.com/achimdehnert/platform/pull/1367) ebenfalls. Merkposten zur Methode: `mergeable` liefert erst `UNKNOWN`, GitHub rechnet lazy — Re-Poll nötig.
5. trading-hub Branch-Protection [#1117](https://github.com/achimdehnert/platform/issues/1117) — bewusst zurückgestellt (App-Repo-Scope), weiterhin offen
6. Ausführungstreue-Audit [#1167](https://github.com/achimdehnert/platform/issues/1167): Nebenfund Namenskollision KONZ-platform-001 weiterhin offen
7. KONZ-018 W1: testkit-Dedup, Freshness-Pilot promptfw
8. Stub-Issues via Sonnet-Session (`/model sonnet` + `/issues-offen`)

> **Erledigt 2026-07-23 (früh, ADR-280-Betriebsnachweis — diese Session):** **Alt-Prio 1 entfällt** — [#1366](https://github.com/achimdehnert/platform/pull/1366) und [#1369](https://github.com/achimdehnert/platform/pull/1369) sind **MERGED** (06:05/06:06 UTC, gegen die API geprüft, nicht gefolgert). **Alt-Prio 2 ist entsperrt und zu 5/6 gemessen:** eine Parallel-Session hat `generate.py --kind skills --allow-live` mit Owner-Freigabe ausgeführt (06:14:08 UTC, `manifest.json` → `source_commit=9371148`, 4 Skills, `doctor.py --kind skills` = DRIFT-SCORE 0, keine Lane-Dublette); darauf wurden §8.1 Kriterien 1–5 gemessen und bestanden, Artefakt [`docs/verifications/2026-07-23-adr280-betriebsnachweis.md`](docs/verifications/2026-07-23-adr280-betriebsnachweis.md). Kriterium 6 bleibt als **neue Prio 1** stehen. **Alt-Prio 4 hat jetzt einen PR** ([#1377](https://github.com/achimdehnert/platform/pull/1377), Parallel-Session). Liste dadurch 9 → 8 Einträge, lückenlos durchnummeriert (Maschinen-Vertrag: `claude-next-sync` matcht nur ganze Zahlen). **Methoden-Befund derselben Session:** der Start-Hook `handover_prio_mirror.sh` spiegelt `${CWD}/AGENT_HANDOVER.md` **ohne `fetch` und ohne Behind-Zähler** (Zeilen 30/36) — der lokale Haupt-Tree hing 11 Commits zurück, die gespiegelte Prio war dadurch stumm veraltet (u.a. „12 offene PRs", „Kriterium 5 vorbereitet"). Getrackt als [#1378](https://github.com/achimdehnert/platform/issues/1378).
> **Erledigt 2026-07-22 (Abend-Session — ADR-281 abgeschlossen):** **Alt-Prio 2 (ADR-281 §8.1 Kriterium 5) ist ausgeführt und bestanden** — diese Session fand den am Nachmittag vorbereiteten Symlink beim Start vor, Marker + Argument-Echo korrekt, Werkzeugversion unverändert 2.1.217; §8.1 steht auf 6/6, Testartefakte entfernt, DRIFT-SCORE zurück auf 3. **Alt-Prio 3 („beide ADRs bleiben `proposed`") ist damit für ADR-281 überholt** — der ADR steht auf `accepted` ([#1366](https://github.com/achimdehnert/platform/pull/1366)); ADR-280 bleibt `proposed`. **Alt-Prio 9 entfernt:** [#1289](https://github.com/achimdehnert/platform/issues/1289) ist **CLOSED** (gegen die API geprüft, nicht gefolgert) — die Zeile widersprach ohnehin dem Erledigt-Block vom 21.07. **Alt-Prio 6 neu gemessen:** 12 → **3** offene PRs, 0 nicht-MERGEABLE. Zusätzlich neu: der §8.2-Negativtest wurde vorgezogen, gemessen und die dabei gefundenen zwei Kanten gefixt ([#1369](https://github.com/achimdehnert/platform/pull/1369) schließt [#1368](https://github.com/achimdehnert/platform/issues/1368)). Liste dadurch 11 → 9 Einträge, lückenlos durchnummeriert (Maschinen-Vertrag: `claude-next-sync` matcht nur ganze Zahlen).
> **Erledigt 2026-07-22 (Session-Start-Reconciliation, keine neue Arbeit):** Zwei „Nächste Schritte"-Zeilen waren **stale** und sind entfernt — beide gegen die API geprüft, nicht gefolgert. (a) Alt-Prio 1 führte [#1293](https://github.com/achimdehnert/platform/pull/1293) als `REVIEW_REQUIRED`; der PR ist **MERGED** (2026-07-22 14:35 UTC, Commit `cbc7204` auf `main`) → [#1287](https://github.com/achimdehnert/platform/issues/1287) ist PR-seitig abgeschlossen. (b) Alt-Prio 4 („`doctor.py` meldet dangling Symlink nicht, §8.2-Negativtest würde durchfallen") ist behoben durch [#1335](https://github.com/achimdehnert/platform/pull/1335) **MERGED** (09:59 UTC), Issue [#1332](https://github.com/achimdehnert/platform/issues/1332) **CLOSED**. Liste dadurch 13 → 11 Einträge, lückenlos durchnummeriert (Maschinen-Vertrag: `claude-next-sync` matcht nur ganze Zahlen). Restliche Zeilen inhaltlich unverändert bis auf Prio 6 (PR-Zahl neu gemessen) und Prio 2 (Kriterium 5 braucht Vorbereitung).
> **Erledigt 2026-07-21 (Vormittag, Aufräum- + Infra-Session — Parallel-Session, nicht diese):** **Prio „lügender Index" abgeschlossen** ([#1288](https://github.com/achimdehnert/platform/pull/1288) GEMERGT) — ADR-158 `implementation_status` von `implemented` auf `partial` korrigiert (3 tote Evidence-Pfade unter `packages/docs-agent/`, seit 2026-04-23 in `_ARCHIVED/`), ADR-072-Rollout-Tabelle auf belegten Stand zurückgesetzt. **Bewusst nicht nachgemessen** (wäre Scope-Eskalation in 4 App-Repos) → ungemessene Repos tragen jetzt explizit `❔ nicht nachgemessen`. Gate-Lücke getrackt ([#1289](https://github.com/achimdehnert/platform/issues/1289)) · **Branch-Hygiene: 442 lokale Branches gelöscht (512 → 47)**, Restore-Manifest `~/shared/branch-cleanup-platform-2026-07-21.txt`. **Lehre:** der erste Durchlauf stufte 51 gemergte Branches falsch als „lokal voraus" ein — nicht wegen Divergenz, sondern weil der gemergte `headRefOid` lokal fehlte und der Ancestor-Check scheiterte. Nach `git fetch origin <oid>` waren alle 51 sauber entscheidbar; echte Divergenz lag bei 7, nicht 56.
> **Erledigt 2026-07-21 (Infra-Entscheid GPU, kein Code — Parallel-Session):** Recherche + eigene Messung → **kein GPU-Server gemietet**. illustration-hub läuft auf der vorhandenen RTX 4090, meiki-Pilot + Dokumentenlast auf CPU des Dev-Servers. Gemessen auf 88.99.38.75 (16 Kerne, geteilte Last), Print-Agent-Prompt: `qwen2.5:3b` 7,3 tok/s / 18 s · `7b` 3,6 tok/s / 51 s · `14b` 1,1 tok/s / 153 s — alle valides JSON. Gegenrechnung: Hetzner GEX44 hat **20 GB** (weniger als die 4090; Primärquelle, keine Mindestlaufzeit, FSN1), VRAM-gleicher Scaleway L4 kostet 575 €/Mon netto bei ~⅓ Speicherbandbreite. **Nicht belegt geblieben:** GEX44-Monatspreis (Seite rendert clientseitig), Stromkosten, Preisknick Consumer↔Datacenter — 14 von 25 Recherche-Claims adversarial verworfen. **Auflage für meiki:** gegen austauschbaren OpenAI-kompatiblen Endpunkt bauen, sonst wird der spätere Umzug ins LRA-RZ zum Umbau.
>
> **meiki-Datenklassifikation (Owner-Präzisierung 2026-07-21) — trägt den Entscheid oben:** Der meiki-**Pilot** auf IIL-Infrastruktur arbeitet mit **synthetischen** Daten. Echte Daten erst ab dem **Live-Prod-Testlauf**, und dieser Übergang wird **ausdrücklich kommuniziert**. **Entscheidungsregel: solange keine solche Mitteilung vorliegt, sind meiki-Daten synthetisch** — Abwesenheit einer Mitteilung heißt *synthetisch*, nicht *unklar*. Echte Bürgerdaten liegen im Zielzustand im **LRA-Rechenzentrum**, nicht bei uns. Daraus folgt für den Pilotzeitraum: kein AVV, keine Auftragsverarbeitung, freie Anbieterwahl. Ab dem kommunizierten Umschaltpunkt kippt das vollständig (Backup-Pflicht, AVV-Prüfung, Souveränitäts-Auflagen). Korrigiert die frühere Pauschal-Einordnung „meiki-* hält Prod-Daten" (Stand 06-11), die für den Pilotzeitraum zu streng war; `writing-hub`/`risk-hub` sind davon nicht berührt.
> **Erledigt 2026-07-21 (Skill-Lanes, diese Session):** [#1290](https://github.com/achimdehnert/platform/pull/1290) GEMERGT (Phase 1: 3 Piloten nach `skills/`, Gate + CI-Trigger auf beide Lanes, 5 Tests) · [#1291](https://github.com/achimdehnert/platform/pull/1291) GEMERGT (ADR-280 Rev 1) · [#1292](https://github.com/achimdehnert/platform/pull/1292) GEMERGT (`/adr`-Skill: `gen_adr_index.py` als Pflichtschritt + Abschluss-Checkliste + Anti-Patterns) · [#1118](https://github.com/achimdehnert/platform/pull/1118) GESCHLOSSEN (superseded). **Lehre:** meine tragende Prämisse („`$ARGUMENTS` entfällt unter Skills") war **falsch** — geprüft gegen `claude --version` 2.1.216 + Doku 2026-07-21; zwei externe Zweitmeinungen fanden es, beide empfahlen „überarbeiten". Verifikationsstand mit Versionspin ist seitdem Pflichtblock in ADR-280/281.
> **Erledigt 2026-07-21 (Parallel-Session, nicht diese):** [#1284](https://github.com/achimdehnert/platform/pull/1284) GEMERGT (Handover-Stand 07-20/21) · [#1013](https://github.com/achimdehnert/platform/pull/1013) + [#954](https://github.com/achimdehnert/platform/pull/954) GEMERGT.
> **Erledigt 2026-07-21 (Abend, ADR-Evidence-Strang — eigene Session, parallel zur Nachmittags-Session):** **PR-Stau der 5 DIRTY-PRs aufgelöst** — [#986](https://github.com/achimdehnert/platform/pull/986) / [#1005](https://github.com/achimdehnert/platform/pull/1005) / [#1007](https://github.com/achimdehnert/platform/pull/1007) rebased (alle grün), [#892](https://github.com/achimdehnert/platform/pull/892) + [#893](https://github.com/achimdehnert/platform/pull/893) als von `main` überholt geschlossen (Commit `3d71952` hatte beides bereits umgesetzt; #893 hätte eine scharfe Gate-Stufe zurückgedreht). Funde beim Rebase: Archiv-Namenskollision (zwei Generationen `generate_project_facts.py`), `.windsurf/workflows/onboarding-new-repo.md` via ADR-280 gelöscht. · **ADR-234 §11.3 präzisiert** ([#1007](https://github.com/achimdehnert/platform/pull/1007)): der „Dual-Generator"-Befund ist output-seitig widerlegt — die beiden Skripte schreiben verschiedene Artefakte, A3 war nie eine Deduplizierung; Beschluss bleibt, Begründung korrigiert. · **77 project-facts-Dateien archiviert** ([#1306](https://github.com/achimdehnert/platform/pull/1306), [#1304](https://github.com/achimdehnert/platform/issues/1304)) — 0 Leser verifiziert; der ursprünglich geplante Header-Sweep wäre **falsch** gewesen (anderes Ziel, anderes Format). · **#1289 erledigt** → Evidence-Pfad-Check [#1312](https://github.com/achimdehnert/platform/pull/1312) (SUGGEST, 23 Tests) + Bereinigung [#1318](https://github.com/achimdehnert/platform/pull/1318) ([#1311](https://github.com/achimdehnert/platform/issues/1311)): **16 Findings → 0 ohne einen Ignore-Eintrag**, 10 ADRs; 7 FPs verifiziert ausgeschlossen (`orchestrator_mcp` = Teilspiegel, `packages/django-tenancy` liegt in **risk-hub**, ADR-246 in **iil-pet-portal**). · **noop-Check** [#1322](https://github.com/achimdehnert/platform/pull/1322) aus eigenem Fehler: `ruff format tools/` + `git add -A` schleuste 95 Fremddateien in #1312 (repariert, 4 Dateien). **Lehren:** (a) ein Frontmatter-Parser-Bug ließ den Evidence-Check am eigenen Anlassfall ADR-158 vorbeilaufen — nur die Tests fanden es; (b) `git diff --name-only -w` wertet `-w` **nicht** aus (Blob-Hash-Vergleich), ein darauf gebauter Detektor meldet falsch-grün; (c) „alle Packages jetzt in eigenen Repos" (Commit `2cc7289`) stimmt nicht — 6 von 7 leben nur als PyPI-Dist. **Offen:** alle 7 PRs BLOCKED = warten auf 2.-Owner-Review; Gating-Promotion beider Checks erst nach Merge von #1318.
> **Erledigt 2026-07-21 (Nachmittag, Tools-Strang-Fortsetzung + KONZ-027 + Doppel-Retro, diese Session):** [mcp-hub#180](https://github.com/achimdehnert/mcp-hub/pull/180) GEMERGT (admin-Bypass, auditiert — verify-adr156 nicht mehr falsch-grün) · **KONZ-027 Handover-Fragmente** ([#1301](https://github.com/achimdehnert/platform/pull/1301) GEMERGT, `pipeline_status: pilot`) — 2 externe Cross-Provider-Reviews fanden unabhängig 3 fatale Design-Fehler → R1-Revision; **A/B-Pilot [#1302](https://github.com/achimdehnert/platform/issues/1302): merge=union (empirisch getestet, ~5 Z.) vs. Fragment-Maschinerie** (`model:sonnet-5`) · Retro-Follow-ups [#1309](https://github.com/achimdehnert/platform/pull/1309) GEMERGT (B1-Docstring-Overclaim, ADR-156↔#181-Link) · **Haupt-Retro [#1308](https://github.com/achimdehnert/platform/pull/1308) GEMERGT** (full, 8/11 survived) + **Increment-Retro [#1313](https://github.com/achimdehnert/platform/pull/1313)** (lean) + Skill-Schärfung [#1316](https://github.com/achimdehnert/platform/pull/1316) (stale-clone: nach fetch aus dem Ref lesen). **Offen (execution-ready, `model:sonnet-5`):** [#1302](https://github.com/achimdehnert/platform/issues/1302) A/B-Pilot · [#1310](https://github.com/achimdehnert/platform/issues/1310) verify-adr156-CI-Gate. **Gate-pflichtig rezidiv:** parallel-session-pr-collision (×3, KONZ-027-Pilot ist der Fix), stale-local-clone (×8).
> **Erledigt 2026-07-21 (Abend, #1302/#1310 in Umsetzung — an Sonnet delegiert):** [#1302](https://github.com/achimdehnert/platform/issues/1302) **Arm A gebaut** ([#1319](https://github.com/achimdehnert/platform/pull/1319), offen): `merge=union` auf AGENT_HANDOVER.md + append-only-Konvention; Pilot-Check 1 (server-side Squash ehrt merge=union?) offen bis echter Parallel-PR. · [#1310](https://github.com/achimdehnert/platform/issues/1310) **CI-Gate gebaut** ([#1320](https://github.com/achimdehnert/platform/pull/1320), offen): `workflow_tool_ref_check.py` — Golden-Test verifiziert (Verneinung→FAIL, Aufruf-Form→PASS). · [mcp-hub#182](https://github.com/achimdehnert/mcp-hub/pull/182) (offen, **braucht --admin**): 9 `.py`-Checks in verify-adr156 verschärft. **Nicht im Repo (DSGVO, lokal ~/shared/risk-hub/Feha/):** Feha↔MVZ-DLG TOM-DSB-Beratung — ausfüllbares AcroForm-PDF (188 Felder) + Begleitnotizen + Louzri-Antwort-Entwurf; Kern: TOM-Fragebogen ≠ C5 (separate Instrumente).
> **Erledigt 2026-07-20/21 (Tools-Strang + Mail, 2 Parallel-Sessions):** [#1278](https://github.com/achimdehnert/platform/pull/1278) (estimate_job-Fehldiagnose) · [#1279](https://github.com/achimdehnert/platform/pull/1279) (break-glass-meter, KONZ-004) · [#1280](https://github.com/achimdehnert/platform/pull/1280) (A1 Memory-Key + C1 Lease-Sicht) · [mcp-hub#181](https://github.com/achimdehnert/mcp-hub/issues/181) (deploy_check-Defekt getrackt) · Mail-Postfach strukturiert + Ollama-on-dev + Dienst-H falsifiziert ([#1281](https://github.com/achimdehnert/platform/issues/1281) offen).
> **Erledigt 2026-07-20:** [#1275](https://github.com/achimdehnert/platform/pull/1275) GEMERGT (Ausführungstreue-Umsetzung, KONZ-001+004 Kriterium→Status-Tabellen) · [#1115](https://github.com/achimdehnert/platform/issues/1115) GESCHLOSSEN (usage-sweep: Labels behalten, 36 Skills zurückgebaut via #1257, 3 sunset-reife Skills source- **und** dist-seitig entfernt; Kill-Kriterium *nicht* erfüllt → Sweep läuft weiter) · [#1271](https://github.com/achimdehnert/platform/issues/1271) GESCHLOSSEN (cc-skill-dist DRIFT-SCORE 44→0; alle 35 Orphans durch den einen Rückbau-Commit `cfa9c0f` erklärt, Zweitquellen-Hypothese falsifiziert). **Methodik-Auflage nächster Sweep:** „keine kanonische Source" ist **kein** Tot-Signal — trifft auch frisch zurückgebaute Skills; Status steckt im löschenden Commit (`doctor.py --kind commands` + Orphan↔Commit-Diff vor Teardown).
> **Erledigt 2026-07-19:** Owner-Block #1094 komplett + geschlossen (7/7 OIDC-Bindungen, 3 Pakete live, 4 Alt-Dubletten geyankt, 2. Owner) · ADR-278 accepted (#1266) · codeguard/ingest OIDC (#1267) · django-commons#12 + learnfw#9 Auth-Fixes · shared-ci publish-auth-guard v1.0.13 · #1265 zu, #1268 (Portfolio) ausgelagert · Handover-PR #1171 (stale) geschlossen · **Guard Block-Flip scharf** (shared-ci#33) + v1.0.14 fleet-weit gebumpt (promptfw#32/outlinefw#19) → ADR-278-Enforcement komplett.
> **Erledigt 2026-07-19 (Abend-Session):** #1167-Umsetzungsschritt geliefert (#1275: KONZ-001 + KONZ-004 Kriterium→Status-Tabellen; KONZ-016/018 begründet ausgelassen) · **#1276 GEMERGT** — systemischer ADR-Frontmatter-Blocker (6 ADRs, deprecated Keys) fleet-weit gefixt, `validate` 225/225 · ADR-272-Nummernkollision gelöst (#1077 → ADR-279 umnummeriert, #1086 behält 272) · **Review-Stau von 6 auf 0 rote PRs** (#1027/#1026 gemergt; #1112/#1231/#1141/#1086/#1077/#1225 grün gezogen). **Lehre:** „stale-Index" war bei #1231/#1141 die *falsche* Erst-Diagnose — echter Root-Cause war der repo-weite Schema-Verstoß; ein Log-Blob (base64-HTML) verdeckte bei #1225 einen simplen transienten 503.
> **Erledigt 2026-07-19 (Session-Start-Folgesession):** #1268 geschlossen (Portfolio: alle 6 Pakete behalten) · #1158 geschlossen (`secrets:inherit`: coach-hub bereits auf origin/main gefixt, risk-hub **False Positive** — same-org `iilgmbh` + keine private git-Dep) · #1115 Sweep-Entscheid (Labels behalten; Skill-„tot"-Signal via cc-skill-dist-Drift widerlegt → #1271) · #1167 Stichproben-Audit fortgesetzt (~8 Fix-Kandidaten). **Lehre:** #1 (Guard) + coach-hub-Teil von #2 waren bereits erledigt — nur sichtbar durch konsequente origin/main- statt lokale-Klon-Prüfung.
> **Erledigt 2026-07-18 (Session-Start-Reconciliation, keine neue Arbeit):** Orchestrator-MCP wieder funktional — „Invalid Bearer Token" nicht mehr reproduzierbar, live verifiziert per 3 erfolgreichen Tool-Calls (`agent_memory_search` + `check_recurring_errors` + Outline-Search) am 2026-07-18; Ursache des Wieder-Funktionierens unbekannt (nicht untersucht) · Haupt-Retro [#1162](https://github.com/achimdehnert/platform/pull/1162) ist MERGED + APPROVED (war als „offen" geführt, Handover war stale).
> **Erledigt 2026-07-15:** cad-hub#42 (war schon vor Session-Start gemergt, Handover war stale) · trading-hub#150 · coach-hub#40 · ADR-270-Vorbedingung (#1152) · Increment-Retro (#1165) · session-start-Checkliste-Nachbesserung (#1166).
> **Erledigt 2026-07-13 (nachgezogen, war nur in PR #1122 unmerged dokumentiert):** KONZ-017 W1 sync-drift-meter #998 (#1009 gemergt) · usage_sweep.py (#1116 gemergt) · trading-hub Deploy-403 (#1070 zu) · PyPI-OIDC-Readiness codeguard/ingest (#1118 gemergt) · trading-hub PR #130 (README-Fix, inzwischen gemergt).

> **Ältere Stände** (2026-07-10 Mail-Skill, 2026-06-20 F4/Wave-2 usw.) → [`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md).

## 0. Aktuelle Prioritäten (2026-07-02 — verifiziert via API/Fleet-Scan)

| Prio | Task | Tier |
|---|---|---|
| 1 | **ADR-242 Wave 3** — Tracking **[#811](https://github.com/achimdehnert/platform/issues/811)**. **Realer Stand 2026-07-10 (gegen #811+Retro abgeglichen, weiter als der Issue selbst zeigt):** Phase 1 (learn-hub, recruiting-hub, travel-beat) komplett, gemergt UND live Wave-3-geschützt. Zusätzlich 3 Repos außerhalb der ursprünglichen Worklist live geschützt (weltenhub, illustration-hub, research-hub) — **nachträglich offiziell in #811 aufgenommen** (Entscheid Achim 07-10). Phase 2 (~23 Standalone-Libs): 13/23 verifiziert+gemergt; Rest-Kohorte in **[#987](https://github.com/achimdehnert/platform/issues/987)** (Task A: gaeb-toolkit/riskfw/weltenfw nur PR-Head-Verify; Task B: outlinefw/promptfw gated auf shared-ci#20); 5 strukturell exkludiert. Formales Phase-3-Apply-Artefakt (`wave3-repos.json` + `apply-branch-protection.yml wave=3` + Negativ-Test + Meter) **existiert noch nicht** — die 6 Live-Rulesets liefen ad-hoc außerhalb dieses Prozesses. | `[Sonnet, via #811]` |
| 2 | **Deploy-Health** (separates Programm, **nie autonom** — Owner/Infra). **Re-Check 2026-07-02: weitgehend geheilt** — onboarding-hub grün (seit 06-24), 137-hub grün (seit 06-21), weltenhub grün (07-01, cancelled=Concurrency benign); dms-hub weiter `cancelled` (benign, letzte Runs 06-09). **tax-hub „Issue Triage" 3× failure (07-01/02)** — Root-Cause `Input required and not supplied: github-token` (Repo hat 0 Secrets, `PROJECT_PAT` fehlt; risk-/coach-hub identisches Muster + PAT = grün). **Fix-PR iilgmbh/tax-hub#20 offen** (Fallback `PROJECT_PAT \|\| github.token`; Self-Approval-Block → wartet auf Owner-Merge; bei Merge `[skip ci]` beachten — deploy.yml feuert auf push:main ohne paths-Filter). Alternative: PROJECT_PAT als Secret setzen (Owner). | `[du/Owner]` |

> **Fortschritt 2026-07-03 (Session 54a76c):** Prio 1 (Wave 3): Scope +„Registry-Konsistenz required machen" (#811-Kommentar — Check ist heute NICHT required, nur `guardian`; Realfall #883/#884/#885 mergten rot). Prio 2 (Deploy-Health): **ADR-264 accepted** = strategischer Rahmen steht; travel-beat-Deploy wieder grün (#57); mcp-hub `/mcp` live; Rest-Item = shared-ci#17-Rollout.
>
> **Fortschritt 2026-07-06 (ERLEDIGT):** **Prio 1 — Wave-3 Phase 1 KOMPLETT** (alle 3 gemergt, `ci / gate` real grün verifiziert): learn-hub#25 (`name:"CI"`-Override raus) · recruiting-hub#13 + travel-beat#62 (**Option A1 = additiver `ci`-Job neben bestehender bespoke Test-CI**, kein Coverage-Verlust — der ursprüngliche #811-Befund „KEIN PR-getriggertes ci.yml" war für beide veraltet). recruiting#10/travel#55/learn#23 auto-closed. **Nächster Wave-3-Schritt = Phase 2** (~23 Standalone-Libs, Worklist in #811), dann Apply. **Prio 2 — Deploy-Health geheilt + live:** billing-hub 403 = **Package-`Manage Actions access` fehlte dem Repo** (NICHT Workflow — identische deploy.yml wie cad-hub, das grün pushte); Owner-Fix im Package-Setting → Rerun grün, `billing.iil.pet/healthz` 200. cad-hub = transienter GHA-Cache-Timeout → Rerun grün, `nl2cad.de/healthz` 200. **Neu: Runbook `docs/runbooks/ghcr-403-push-actions-access.md` (#967) + CC-Memory `reference_ghcr_403_push_package_actions_access`.**

> **Fortschritt 2026-07-08 (unmerged geblieben, PR #985, jetzt konsolidiert):** Phase 2 zu 13/23 verifiziert+gemergt; shared-ci#20-Blocker gefunden; Rest-Kohorte in #987 aufgeteilt (Task A/B). Details: s. Aktueller Stand.
>
> **Fortschritt 2026-07-09/10 (ABGEGLICHEN gegen #811 + Retro, 2026-07-10):** Wave-3-Ruleset live auf 6 Repos (nicht 9 — Memory-Zahl war falsch, korrigiert gegen Retro-Ground-Truth), davon 3 außerhalb der #811-Worklist (weltenhub/illustration-hub/research-hub, jetzt nachträglich aufgenommen) + Live-Incident selbst behoben; ADR-270 accepted. **Formales Phase-3-Apply-Artefakt fehlt weiterhin.** Details: s. Aktueller Stand + #811-Kommentar.
>
> **Fortschritt 2026-07-10 (NEU, offen):** weltenhub-Redis-Incident gelöst (s. Aktueller Stand). Drei Folge-Items offen, alle Human-Decision/Freigabe, keine autonome Ausführung: (1) `ausschreibungs-hub-staging` authentik-Provider/-Application vorbereitet (client_id/signing_key/scopes/redirect geklärt gegen risk-hub-Referenz-Pattern), Freigabe-Block gestellt, Session endete vor Bestätigung — nächste Session kann direkt ausführen, kein erneutes Research nötig. (2) `staging-demo.schutztat.de` DNS-Record (→178.104.184.168) — Entscheid offen. (3) "platform"-Governance-DB (`PLATFORM_DB_HOST=bfagent_db`, degradiert aifw-AI-Features) — Entscheid offen, braucht erst Konsumenten-Inventar. (4) KONZ-platform-015 liegt lokal in `platform` (untracked, main geschützt) — braucht Worktree+PR zum Mergen, dann User-Accept-Entscheid für die Empfehlungen REC-1..REC-7. (5) **Deploy-Health-Scan (session-start) fand 3 neue `failure`** auf coach-hub/trading-hub/pptx-hub, nicht triagiert — s. Aktueller Stand.

> **PR-Hygiene (erledigt 2026-07-02, Freigabe Achim):** #753 + #746 geschlossen (Duplikate von gemergtem #808) · **#760 gemergt** (Registry iil-adrfw/codeguard — Registry-Lücke zu) · **#759 gemergt** (gen_adr_index.py; Rebase-Konflikt in INDEX.md durch Generator-Lauf gelöst, 206 aktive + 48 archivierte ADRs indiziert).

> **✅ Retired/erledigt (2026-06-24, hart verifiziert — billigster Check gemacht):**
> - **F4 CI-grün** als Code-CI-Programm GESCHLOSSEN (Fleet-Scan: 0 Lint/Test/Coverage-Rot; alle Roten = Deploy-Stage). **Kein Sonnet-Material mehr** — nicht erneut als Sonnet-Queue listen.
> - **coach-hub #28** gemergt 2026-06-15 (+ Dep-Fix #31, PAT/Org-Transfer). Strang zu.
> - **ADR-242 Wave 1+2** live (11 Repos geschützt, `ci / gate`).
> - **F1 `.windsurf`-Nachzügler** gesweept (lastwar-bot, iil-voice-agent) — F1 ist KEIN Einmal-Endzustand, periodisch `tools/f1-windsurf-sweep.sh` (dry-run) gegen die API laufen lassen.

**✅ Erledigt (2026-06-10):** weltenhub#16 gemergt verifiziert → **ref-sweep 12/12 komplett** · **research-hub#6** gemergt (2 teardown-Bugs gefixt: async-ORM-Connection-Leak + flush-CASCADE vs django_tenancy-FK).

**✅ Erledigt (2026-06-09):** wedding-hub#19 · onboarding-hub#2 · weltenhub pytest-Fixes · F4-Fixes: weltenhub 5, wedding-hub 3, onboarding-hub 1 · **shared-ci `v1.0.2` + `v1.0.3`** · **mcp-hub#106** + **trading-hub#14** · 11/12 ref-sweep-PRs.

**✅ Erledigt (2026-06-08):** F4-acute (alle 6 `ai-assignable`-Issues closed) · ADR-212 Phase-1 (dev-hub#81 merged) · F1 .windsurf-Untrack vollständig (0 `.windsurf`-Files auf origin/main).

**KONZ-002 Enterprise-Konsolidierung:** Kill-Gate **(c) Portabilität ✅ erfüllt** (Feuerübung Runde 1, 2026-06-03; §15 D1-konform). Offen nur **extern**: (a) Kostenbestätigung + (b) Government-Sign-off, Frist **2026-08-15** — User-getrieben, keine Coding-Prio. Richtung ALT-D, Umsetzung gegated.

**CC-Skill-Dist** (platform): Drift-Score live prüfen — `python3 tools/cc-skill-dist/doctor.py` (Zahl driftet mit jedem neuen/geänderten Skill, hier nicht einfrieren)

---

## 1. MCP-Server & Tool-Calls

**Claude Code (aktuell, `mcp__<server>__<tool>` Format) — wichtigste Tool-Calls:**
- GitHub: `mcp__github__create_issue`, `mcp__github__get_pull_request`
- Memory: `mcp__orchestrator__agent_memory_context(task_description, top_k=5)`
- Deploy-Status: `mcp__orchestrator__deploy_check(action="health", repo=...)`
- Browser: `mcp__playwright__browser_navigate`, `mcp__playwright__browser_snapshot`

**Server-Übersicht (7):**

| Server | Zweck |
|--------|-------|
| **deployment-mcp** | SSH, Docker, Compose, Git, DB, DNS, SSL, Nginx, CI/CD |
| **github** | Issues, PRs, Repos, Branches, Files, Reviews, Search |
| **orchestrator** | Memory (pgvector), Task-Analyse, Agent-Team, Tests, Lint |
| **outline-knowledge** | Wiki: Runbooks, Konzepte, Lessons, ADR-Suche |
| **paperless-docs** | Dokumente, Rechnungen, Archive |
| **platform-context** | Architektur-Regeln, ADR-Compliance, Banned Patterns |
| **playwright** | Browser-Automation, UI-Tests, Screenshots, Network |

### Windsurf-Legacy (kein Coding mehr, ADR-230)

Windsurf-Agents nutzten die o. g. Server über numerische Prefixe (`mcp0_`–`mcp6_` in
derselben Reihenfolge wie oben). Seit ADR-230 wird Windsurf **nicht mehr zum Coden**
eingesetzt (nur ADR-Review-Subset) — die Prefix-Tabelle ist nur noch für das Lesen
alter Sessions/Logs relevant, kein aktives Interface mehr.

---

## 2. Hetzner Infrastructure

| Rolle | IP | User |
|-------|-----|------|
| **Prod-Server** | `88.198.191.108` | `root` (via SSH-Key) |
| **Dev-Server (WSL)** | `localhost` | `devuser` |

**Kritische Regeln:**
- `devuser` hat **KEIN sudo-Passwort** → System-Pakete: `ssh root@localhost "apt-get install -y <pkg>"`
- PROD: nur read-only via MCP — Deploys über `scripts/ship.sh` oder CI/CD
- **NIEMALS** `ping` für Server-Check — Hetzner blockiert ICMP. TCP-Check stattdessen.

**Secrets:**
- Lokal: `~/.secrets/` (einzige Location seit 2026-05-30 — `~/shared/secrets/` konsolidiert + leer)
- Server: `/opt/shared-secrets/api-keys.env` (chmod 600, root-only)
- Repo-spezifisch: `.env.prod` (nie in Git)

---

## 3. Deploy Targets (Prod — 88.198.191.108)

| Repo | Domain | Health |
|------|--------|--------|
| `risk-hub` | schutztat.de | https://schutztat.de/healthz/ |
| `coach-hub` | kiohnerisiko.de | https://kiohnerisiko.de/healthz/ |
| `billing-hub` | billing.iil.pet | https://billing.iil.pet/healthz/ |
| `travel-beat` | travel-beat.iil.pet | https://travel-beat.iil.pet/healthz/ |
| `weltenhub` | weltenforger.com | https://weltenforger.com/healthz/ |
| `trading-hub` | trading-hub.iil.pet | https://trading-hub.iil.pet/healthz/ |
| `cad-hub` | nl2cad.de | https://nl2cad.de/healthz/ |
| `pptx-hub` | prezimo.com | https://prezimo.com/healthz/ |
| `ausschreibungs-hub` | bieterpilot.de | https://bieterpilot.de/healthz/ |
| `dms-hub` | dms.iil.pet | https://dms.iil.pet/healthz/ |
| `wedding-hub` | wedding-hub.iil.pet | https://wedding-hub.iil.pet/healthz/ |

**Deploy-Befehl:** `bash ~/github/platform/scripts/ship.sh <repo>`
**Health-Check:** `mcp2_deploy_check(action="health", repo="<repo>")`

---

## 4. Master Repo Identifier

**Alle Repos in einer Registry** (Anzahl live: `python3 -c "import yaml; print(len(yaml.safe_load(open('registry/canonical.yaml'))['repos']))"`):

```bash
# project-facts.md für alle Repos generieren (nur fehlende)
python3 ~/github/platform/scripts/gen_project_facts.py

# Alle neu generieren
python3 ~/github/platform/scripts/gen_project_facts.py --force

# Einzelnes Repo
python3 ~/github/platform/scripts/gen_project_facts.py risk-hub
```

- Registry: `platform/scripts/repo-registry.yaml`
- Output: `<repo>/.windsurf/rules/project-facts.md` (trigger: always_on)
- Läuft automatisch bei `/session-start` (Step 0.3b) und `/session-ende` (Phase 3.2)

---

## 5. CC-Skills & Windsurf Rules

**CC-Skills (primär, ADR-230):** Quelle `platform/.windsurf/workflows/` → verteilt nach `~/.claude/commands/` via `cc-skill-dist`:
```bash
python3 ~/github/platform/tools/cc-skill-dist/generate.py --target ~/.claude/commands --allow-live
python3 ~/github/platform/tools/cc-skill-dist/doctor.py   # Drift-Check
```

**Windsurf Rules** (nur ADR/Review-Subset, kein Coding mehr seit ADR-230):
- Quelle: `platform/.windsurf/rules/` + `platform/.windsurf/workflows/` (tool_targets: windsurf-review)
- Verteilen: `python3 tools/cc-skill-dist/windsurf-subset.py`

**project-facts.md** (repo-spezifisch, generiert):
```bash
python3 ~/github/platform/scripts/gen_project_facts.py          # nur fehlende
python3 ~/github/platform/scripts/gen_project_facts.py --force  # alle
```

---

## 6. GitHub

**Account:** `achimdehnert`
**MCP:** `mcp1_*` für alle GitHub-Operationen
**Reusable Workflows:** `achimdehnert/platform/.github/workflows/_ci-python.yml` etc.

**Repo-Kategorien:**
- **Django Hubs** (21): risk-hub, coach-hub, billing-hub, cad-hub, trading-hub, pptx-hub, travel-beat, weltenhub, wedding-hub, recruiting-hub, dms-hub, ausschreibungs-hub, illustration-hub, research-hub, writing-hub, learn-hub, dev-hub, odoo-hub, 137-hub, bfagent, tax-hub
- **Python Libraries** (14): aifw, authoringfw, promptfw, illustration-fw, learnfw, weltenfw, outlinefw, researchfw, testkit, iil-reflex, iil-ingest, iil-enrichment, iil-fieldprefill, nl2cad
- **Infra** (5): platform, mcp-hub, infra-deploy, iil-relaunch, lastwar-bot

(Diese Kategorien sind kein vollständiges Abbild von `registry/canonical.yaml` — Gesamtzahl
live siehe oben unter §4; bei Abweichung ist die Registry maßgeblich, nicht diese Liste.)

---

## 7. pgvector Memory (Orchestrator)

| Parameter | Wert |
|-----------|------|
| **Container** | `mcp_hub_db` (Image: `pgvector/pgvector:pg16`) |
| **Läuft auf** | Prod-Server `88.198.191.108` |
| **Port auf Prod** | `127.0.0.1:15435` (Host-Binding des Containers) |
| **Lokaler Zugriff** | `localhost:15435` via SSH-Tunnel |
| **systemd Service** | `ssh-tunnel-postgres` (dev desktop, User `adehnert`) |

```bash
# Status prüfen
ss -tlnp | grep 15435
systemctl is-active ssh-tunnel-postgres

# Manuell starten (ohne sudo)
ssh -N -L 15435:localhost:15435 -i ~/.ssh/id_ed25519 root@88.198.191.108 &

# Via systemd (empfohlen — Autostart bei Neustart)
sudo systemctl start ssh-tunnel-postgres
```

- **Kein Fallback auf Cascade Memory** — pgvector MUSS laufen
- Tunnel-Ziel: `remote:localhost:15435` (nicht `:5432` — der Container bindet auf 15435)
