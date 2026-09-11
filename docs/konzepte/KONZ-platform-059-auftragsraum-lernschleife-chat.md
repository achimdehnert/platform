---
concept_id: KONZ-platform-059
title: Auftragsraum „Aufträge Achim / Lotse" — Auftragseingang mit Lernschleife über dem Chat-Lotsen
pipeline_status: idea
tier: T2
owner: Achim Dehnert
spec_refs: []            # keine SoR-Spec; das Konzept beschreibt eine Konvention über bestehendem Werkzeug (chat_lotse.py), keine Oberfläche
adr_threshold: kein ADR   # Konvention in einem Repo über bestehendem Werkzeug; wird Stufe 2 (Live-Auslösung) gebaut, ist das der Charta-Entscheid aus chat-hub#48 Stufe B, kein neuer ADR
review_by: 2026-10-10
kill_criteria: "Wenn bis 2026-10-08 (28 Tage nach Anlage) weniger als 20 Nachrichten des Owners im Raum stehen ODER auch nur eine Owner-Korrektur länger als 24 h ohne Regel-Artefakt gezählt wurde, wird Stufe 2 nicht gebaut und der Raum bleibt Notiz-Eingang ohne Lotsen-Lauf."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: docs/konzepte/KONZ-platform-025-lotsen-charta.md, commit_or_pr: "Art. 1.0–1.4, Art. 7", opened_in_session: true}
  - {claim_id: C2, source_path: docs/konzepte/KONZ-platform-058-iil-assist-ein-dienst-zwei-zugaenge.md, commit_or_pr: "Ledger A3, D1, D2, D4, D6, R2; Regelkreis; Modellfest", opened_in_session: true}
  - {claim_id: C3, source_path: "iilgmbh/chat-hub#48", commit_or_pr: "iilgmbh/chat-hub#48 (OPEN, Stufe A/B)", opened_in_session: true}
  - {claim_id: C4, source_path: chat-hub/deploy/chat_lotse.py, commit_or_pr: "iilgmbh/chat-hub main, 1443 Zeilen, Unterbefehle init/sync/watch/send/react/find-room/status/room-create", opened_in_session: true}
  - {claim_id: C5, source_path: infra/ports.yaml, commit_or_pr: "Eintrag chat-hub (prod-b, 8008, Repo iilgmbh/chat-hub, Produktname iil-assist-hub)", opened_in_session: true}
  - {claim_id: C6, source_path: docs/betrieb/mailcheck.md, commit_or_pr: "#3054, #3061, #3064, #3070, #3078", opened_in_session: true}
  - {claim_id: C7, source_path: tools/mail_agent/messjournal.py, commit_or_pr: "#3061, #3076, #3077", opened_in_session: true}
  - {claim_id: C8, source_path: tools/mail_agent/verfallsmelder.py, commit_or_pr: "#3064, #3065", opened_in_session: true}
  - {claim_id: C9, source_path: tools/betrieb_backlog_check.py, commit_or_pr: "#3070", opened_in_session: true}
  - {claim_id: C10, source_path: "achimdehnert/platform#3079", commit_or_pr: "#3079 (Auftrag, Freigabe-Zeile 2026-09-10)", opened_in_session: true}
  - {claim_id: C11, source_path: "~/.claude/CLAUDE.md + CLAUDE.md + MEMORY.md + AGENT_HANDOVER.md", commit_or_pr: "Messung 2026-09-10: 74.146 Bytes ≈ 18.500 Tokens Grundlast je Sitzungsstart, ohne Hooks", opened_in_session: true}
  - {claim_id: C12, source_path: tools/deferral_anchor_check.py, commit_or_pr: "#3059 (--issue), Required Check Aufgeschobene-Arbeit-braucht-einen-Anker", opened_in_session: true}
created: 2026-09-10
---

# KONZ-platform-059 — Auftragsraum „Aufträge Achim / Lotse"

**Tier-Entscheidung: T2.** Das Konzept legt eine neue lokale Konvention in platform fest (was eine Nachricht im Raum auslösen darf, wie eine Korrektur zur Regel wird, welche Kennzahlen der Raum schreibt) über einem Werkzeug, das bereits existiert (`chat_lotse.py`, C4) und einem Zugang, der bereits entschieden ist (KONZ-058 D4/D6, C2). Auto-Eskalation greift wegen eines persistenten Artefakts (Auftragsjournal) — mindestens T2. **Nicht T3**, weil die Sicherheitsgrenze (Live-Bot als Auslöser eines Werkzeugs) nicht hier entschieden wird, sondern in chat-hub#48 Stufe B (C3); dieses Konzept nimmt diese Grenze als gegeben und baut alles Wesentliche **vor** ihr. Bedingte Eskalation: sobald Stufe 2 (Auslösung ohne Kapitäns-Sitzung) gebaut werden soll, ist das der Charta-Entscheid aus #48 — dann T3 mit drei unabhängigen Agenten, nicht vorher.

## Kernthese

Dieses Konzept sagt: **Der Chatraum ist kein zweiter Befehlskanal, sondern ein Auftragseingang mit Gedächtnis — jede Nachricht wird zu einem Artefakt, das die bestehende Kapitäns-Sitzung abarbeitet, jede Korrektur wird zu einer Regel, und der Raum misst beides selbst. „Selbst verbessernd" heißt in Stufe 1: der Raum verbessert die *Regeln*, nach denen gearbeitet wird, nicht sich selbst ohne Menschen — das wäre Stufe 3 hinter chat-hub#48 B. Erst wenn diese Schleife vier Wochen trägt, lohnt die Frage nach einem Lotsen, der ohne Sitzung antwortet.**

## Was schon existiert (Root-Cause-Tiefe, Step 0)

| Baustein | Stand | Beleg |
|---|---|---|
| Matrix-Server, Element, verschlüsselte Räume | läuft auf prod-b, `chat-hub`, Produktname des Chat-Zugangs `iil-assist-hub` | C5 |
| Lotsen-Konto und Werkzeug | `chat_lotse.py`: `init`, `sync` (neue Nachrichten seit Token als JSON-Zeilen, „führt nichts aus"), `watch` (Long-Poll auf einen Raum), `send`, `react`, `room-create`; Outbox | C4 |
| Grenze für den Live-Bot | chat-hub#48 Stufe B: nur mit Owner-Grant, nur Lesen, Außenwirkung als Entwurf | C3, C2 R2 |
| Zugang Chat → Gateway → Hub | KONZ-058 D1/D2: eine Auth-Grenze, Management-Command auf dem Hub-Host | C2 |
| Regelkreis mit vier Bahnen (Verbesserung, Wartung, Diabolus, OOTB) | für den Dienst-Katalog, täglich/wöchentlich, Trockenlauf ohne `--apply` | C2 |
| Messjournal, Verfallsmelder, Backlog-Prüfung | für Mailcheck und To-do-Liste gebaut (K2–K4 aus #3015) | C6–C9 |
| Aufschub-Anker-Gate | Prosa-Aufschub ohne Link wird in PR-Text und Issue-Kommentaren gefunden | C12 |

**Was fehlt** (und was dieses Konzept deshalb überhaupt beschreibt): (1) eine Regel, was eine Nachricht im Raum *ist* — Notiz, Kurzbefehl, Auftrag, Korrektur — und welches Artefakt sie erzeugt; (2) die Lernschleife für Korrekturen; (3) Kennzahlen und Verfallsignale für den Raum selbst; (4) ein Stufenplan, der die #48-Grenze respektiert. Nichts davon ist ein Bot.

## Ledger

| id | Aussage | Typ | Evidenz/Falsifikation | Status |
|---|---|---|---|---|
| A1 | Der Owner schreibt heute Zurufe in die Kapitäns-Sitzung („#207 erledigt", „freundlich nachfragen"); diese Zurufe sind der Nachrichtentyp, den der Raum aufnehmen soll | Annahme | Sitzung 2026-09-10 (C10, Sachstand #3015): 9 Zurufe an einem Tag, alle in der Sitzung | belegt |
| A2 | Ein Aufwachen des Modells kostet ≈ 18.500 Tokens Grundlast vor Hooks; ein Raum kostet im Leerlauf nichts | Annahme | C11 (Dateimessung); Hook-Anteil nicht gemessen → offen bis Kill-Gate-Messung | teilbelegt |
| A3 | `chat_lotse.py sync` liefert die Raumnachrichten als JSON-Zeilen, ohne etwas auszuführen — genau die Form, die ein Sortierer braucht | Annahme | C4 (Docstring, `cmd_sync`) | belegt |
| A4 | Das Aufschub-Anker-Gate kann ein Auftragsjournal lesen, wenn die Einträge die Anker-Form tragen | Annahme | C12 (`--issue` liest Body + Kommentare; ein Journal ist eine Datei — Erweiterung nötig, s. MVC) | teilbelegt |
| D1 | **Vier Nachrichtenklassen, je mit Charta-Artikel und Sicherung** (K1): Notiz → Ledger-/Journalzeile ohne Modell (Art. 1.4); Kurzbefehl (`#N erledigt`, `#N Frist …`) → in Stufe 1 ein **Vorschlag** im Journal, den die Kapitäns-Sitzung mit `auftragsraum.py anwenden` in einem Kommando übernimmt (Art. 1.2: keine Schreibung ohne Sichtung); Auftrag → Issue mit Freigabe-Zeile, Lauf nur aus der Kapitäns-Sitzung (Art. 1.0); Korrektur → Regel-Artefakt, vom Werkzeug angelegt (Art. 3, Gedächtnis); **Rückfrage** (Lotse → Owner) → nur aus der Kapitäns-Sitzung per `chat_lotse.py send` mit KI-Kennzeichnung (Art. 7 Provenienz), die Owner-Antwort darauf ist eine Notiz mit Bezug auf die Rückfrage-Nachricht-ID. Keine Klasse ist auf „später" verschoben; was fehlt, ist allein die Automatik hinter Auftrag und Rückfrage (Stufe 2/3) | Entscheidung | C1; Alternative: alle Nachrichten gleich behandeln → Blackbox mit Vollmacht (Befund B1); Widerlegung 2026-09-10 Punkte 1/2 kippten die erste Fassung (Kurzbefehl schrieb direkt, Rückfrage fehlte) | entschieden |
| D2 | **Nur das Owner-Konto löst Artefakte aus.** Der Sortierer vergleicht das `sender`-Feld jeder `sync`-Zeile mit `OWNER_MXID` aus `~/.claude/auftragsraum.env` (vom Owner gesetzt, nicht im Repo); Nachrichten anderer Konten werden als Klasse `fremd` protokolliert, erzeugen aber weder Vorschlag noch Issue; Ilja und weitere Nutzer bleiben Thema von chat-hub#48 | Entscheidung | C3 (#48 unterscheidet Ilja-Räume); Alternative: Konto-Liste → zweite Rechteverwaltung neben der Registry (Art. 2.6) | entschieden |
| D3 | **Stufe 1 ist modellfrei.** Sortierer (`auftragsraum.py sortieren`) liest `chat_lotse.py sync`, erkennt Kurzbefehle per festem Muster und schreibt sie als Vorschlag ins Journal (Ledger unberührt, bis `anwenden` läuft); alles andere wird als „Auftrag/Notiz" abgelegt und wartet auf die nächste Kapitäns-Sitzung, die den Raum als Eingang abarbeitet (wie `/mailcheck` das Postfach) | Entscheidung | Step 2a Frage 1: je Nachricht ein Aufruf, keine Schleife; Alternative: Modell je Nachricht → Kosten A2 je Zuruf | entschieden |
| D4 | **Lernschleife als Mechanik** (K2): eine Nachricht der Klasse „Korrektur" (Muster: beginnt mit `nein`, `falsch`, `kürzer`, `so:`, oder `!regel`) wird im Journal mit `korrektur: true` geführt; `auftragsraum.py regel <nachricht_id>` legt das Regel-Artefakt **selbst** an (Memory-Kandidat mit Zitat, Datum und Link zur Nachricht; wahlweise Issue) und schreibt dessen Pfad/Link in das Feld `artefakt` — die Sitzung ergänzt nur das „Why". Gate: `auftragsraum.py offen --block` (Exit 1 bei `korrektur: true` mit leerem `artefakt` älter als 24 h) als Zeile in `session-ende` — verhindern statt zählen. Kennzahl „Korrekturen ohne Artefakt" = Journalzeilen mit `korrektur: true` und leerem `artefakt` älter als 24 h, Sollwert 0 | Entscheidung | Probe auf dem Papier (C6, #3037): Owner-Satz „keine prompts, sondern Inhalt" → Journalzeile → Regel 0 im Mailcheck-Skill (#3037) → Link; die Schleife hätte heute in der Sitzung geschlossen — ohne Raum entstand sie nur, weil ich sie im Kopf hatte | entschieden |
| D5 | **Selbstmessung** (K3) nach dem Muster von C7/C8: Journal `~/.claude/auftragsraum-journal.jsonl` (eine Zeile je Nachricht: Zeit, Klasse, Konto-Hash, Artefakt-Link, Korrektur-Flag, Bearbeitet-Zeit, Aufwachkosten in Tokens wenn ein Lauf stattfand); `messjournal.py --anwendung auftragsraum` (**zu bauen** — heute sind nur `mailcheck`, `todo`, `alle` zugelassen, C7) liefert wöchentlich vier Kennzahlen der Stufe 1: Nachrichten je Klasse, Korrekturen ohne Artefakt, mittlere Zeit bis Bearbeitung, Anteil angewendeter Kurzbefehle; Tokens je Auftrag kommen ab Stufe 2 als fünfte Kennzahl. `verfallsmelder.py` bekommt drei Signale (**zu bauen**, C8): Nachricht ohne Bearbeitung > 24 h; Korrektur ohne Artefakt > 24 h; Kosten je Woche > Budget (Stufe 2) | Entscheidung | Bauform existiert (C7, C8), die Funktion nicht — Widerlegung 2026-09-10 Punkt 6/7; Alternative: eigene Datei/eigenes Werkzeug → zweite Wahrheit | entschieden |
| D6 | **Stufenplan** (K5): Stufe 1 Raum + Sortierer + Kurzbefehle + Morgen-Zeitung als erste Meldung (`chat_lotse.py send`, C4); Stufe 2 Auftrag → Issue → Lauf in schlanker Chat-Rolle, ausgelöst aus der Kapitäns-Sitzung („Raum abarbeiten"), nicht vom Raum; Stufe 3 Rückfragen des Lotsen im Raum = chat-hub#48 Stufe B, eigener Owner-Grant, eigenes Konzept-Tier | Entscheidung | C3; Kill-Gate unten | entschieden |
| D7 | Kein Personendatum aus dem Ledger im Raum: Kurzbefehle nennen nur Nummern; der Sortierer schreibt Betreffs nie in den Raum zurück (Raum liegt außerhalb der Mail-Lane) | Entscheidung | C6 (Fallen-Abschnitt), #3054 (Betreff in Fixture, geschwärzt) | entschieden |
| D8 | **Zustand hat genau eine Heimat:** Aufträge → GitHub-Issue (offen/zu), Vorgänge → Ledger, Korrekturen → Regel-Artefakt; das Journal führt Ereignisse und Links, nie Zustand. `auftragsraum.py offen` fragt den Issue-Zustand live per `gh` ab, statt ihn zu spiegeln | Entscheidung | Widerlegung 2026-09-10 Punkt 11 (Journal↔Issue ohne Rücksynchronisation); Alternative: Zustand ins Journal spiegeln → zweite Wahrheit (B1) | entschieden |
| R1 | Der Sortierer erkennt einen Auftrag als Kurzbefehl (oder umgekehrt) und schreibt falsch ins Ledger | Risiko | Muster eng (nur `#N erledigt`, `#N Frist YYYY-MM-DD`); alles andere = Auftrag/Notiz ohne Schreibung; Positivkontrolle: Fixture mit 20 Nachrichten, 0 Fehlklassifikation | offen bis MVC |
| R2 | Der Raum wird zum zweiten Befehlskanal durch die Hintertür, weil die Sitzung „den Raum abarbeitet" und dabei Nachrichten wie Anweisungen liest | Risiko | Art. 1.0 (C1): Raumnachrichten sind Daten; die Sitzung legt je Auftrag ein Issue an und arbeitet das Issue, nicht die Nachricht — Gate: Auftrag ohne Issue = Befund (C12-Erweiterung) | mitigiert durch D1/D3 |
| R3 | Niemand liest den Raum: Zurufe bleiben in der Sitzung, der Raum verwaist | Risiko | Kill-Gate misst genau das (< 20 Nachrichten in 28 Tagen) | offen |
| R4 | Doppelte Wahrheit zwischen Journal und Ledger (Kurzbefehl schreibt beide) | Risiko | Journal trägt nur Ereignis + Link auf die Ledger-Nummer, nie den Zustand; Zustand bleibt im Ledger | mitigiert durch D5 |

## MVC — kleinste Fassung, die die Schleife beweist (Stufe 1)

| Was | Wo | Konkret |
|---|---|---|
| Raum | chat.iil.pet | `chat_lotse.py room-create` „Aufträge Achim / Lotse", verschlüsselt, Mitglieder: Owner-Konto, `@lotse:chat.iil.pet` (C4) |
| Sortierer | `tools/chat_agent/auftragsraum.py` (neu, Stdlib) | `sortieren`: liest `chat_lotse.py sync` (JSON-Zeilen) von stdin oder Datei, prüft `sender` gegen `OWNER_MXID`, klassifiziert nach D1, schreibt Journalzeile (Kurzbefehle als Vorschlag); `--eingabe` für Tests |
| Anwenden | `auftragsraum.py anwenden` | übernimmt alle offenen Kurzbefehl-Vorschläge in einem Kommando über `board.py --erledigt N` (#3049, zu bauen) bzw. `board.py --frist N --datum …`, schreibt `bearbeitet_am`; läuft nur in der Kapitäns-Sitzung |
| Regel | `auftragsraum.py regel <nachricht_id>` | legt den Memory-Kandidaten (Zitat, Datum, Link) an, schreibt `artefakt`; `offen --block` als Gate in `session-ende` |
| Journal | `~/.claude/auftragsraum-journal.jsonl` | Felder: `zeit`, `klasse` (notiz/kurzbefehl/auftrag/korrektur/rueckfrage/fremd), `konto_hash`, `nachricht_id`, `vorschlag` (Kurzbefehl-Text, nur Nummer und Aktion), `artefakt` (Link oder leer), `korrektur` (bool), `bearbeitet_am`, `tokens` (erst ab Stufe 2 gefüllt) — keine Nachrichtentexte |
| Abarbeiten | Skill-Zeile in `session-start.md` Phase „Eingänge": „Raum abarbeiten: `auftragsraum.py offen` zeigt Vorschläge, Aufträge, Korrekturen; `anwenden` für die Kurzbefehle, je Auftrag ein Issue mit Freigabe-Zeile, je Korrektur `regel <id>`; `session-ende` führt `offen --block`" | Skill-PR, eigener Merge (Governance) |
| Kennzahlen | `messjournal.py --anwendung auftragsraum` (zu bauen) | Nachrichten je Klasse (7 Tage), Korrekturen ohne Artefakt, mittlere Zeit bis Bearbeitung, Anteil angewendeter Kurzbefehle; Tokens je Auftrag ab Stufe 2 |
| Verfall | `verfallsmelder.py` (Signale zu bauen) | drei Signale aus D5, Schwellen 24 h / 24 h / Budget (Owner setzt) |
| Erste Meldung | Morgen-Zeitung | `digest_taeglich` postet Titel + Link per `chat_lotse.py send` in den Raum (Outbox, C4) — erster Bewohner, kein Auftrag |
| Gate | `betrieb_backlog_check.py` (C9) | dieses Konzept und die Betriebsakte des Raums tragen die Backlog-Tabelle mit Gegenrede (unten) |
| Betriebsakte | `docs/betrieb/auftragsraum.md` | nach dem Muster der drei bestehenden (C6), inkl. Betriebs-Checkliste und Drill |

**Bewusst nicht drin:** ein Prozess, der ohne Kapitäns-Sitzung antwortet (Stufe 3, #48 B); Rechte für weitere Konten; Senden/Deployen/Löschen aus dem Raum; ein Modell im Sortierer.
**Erfolg nachgewiesen, wenn:** 28 Tage nach Anlage ≥ 20 Owner-Nachrichten im Journal, 100 % der Kurzbefehl-Vorschläge nach `anwenden` im Ledger sichtbar (Positivkontrolle: Nachricht `#N erledigt` → `anwenden` → `board.py --pruefe` zeigt N geschlossen), 0 Korrekturen ohne Artefakt > 24 h (`auftragsraum.py offen --block` Exit 0), Morgen-Zeitung an ≥ 20 von 28 Tagen im Raum.
**Rückbau:** Raum verlassen (`chat_lotse.py room-leave`), Skill-Zeile entfernen, Journal bleibt als Datei; kein Zustand außerhalb des Journals.

**Step 2a (Ausführungsform):** Frage 1: mehrere Schritte je Nachricht? Ja (lesen → sortieren → schreiben) → Frage 2: Folge steht fest → **Kette**, fest verdrahtet; Frage 3/4: keine Parallelität, keine Barriere; Frage 5: Verzweigung nach Klasse ist ein Router mit vier festen Ausgängen, kein Graph; Frage 6: keine Schleife — `watch` ist ein Dienst (chat-hub), kein Agenten-Loop; ein Auftrags-Lauf in Stufe 2 hat das Budget aus `policies/autonomy-gates.md`.

## Kill-Gate

`kill_criteria` (Frontmatter): **bis 2026-10-08** ≥ 20 Owner-Nachrichten im Journal **und** 0 Korrekturen ohne Artefakt > 24 h — sonst wird Stufe 2 nicht gebaut, der Raum bleibt Notiz-Eingang. Exception-Budget: eine Verlängerung um 14 Tage (bis 2026-10-22), wenn der Raum in den ersten 7 Tagen technisch nicht nutzbar war (Beleg: Journal ohne Zeilen bei vorhandenen Raumnachrichten). **Messung vor Stufe 2 (K5):** ein echtes Aufwachen aus dem Raum wird in Tokens gemessen, nicht aus C11 geschätzt — Kommando: die Sitzungsstatistik von Claude Code (`/cost` bzw. Usage-Ausgabe der Sitzung) unmittelbar nach dem ersten Auftrags-Lauf; ob der Orchestrator-MCP (`session_stats`) dieselbe Zahl liefert, ist Hypothese (H), nicht Beleg.

| Kriterium | Status | Beleg |
|---|---|---|
| ≥ 20 Owner-Nachrichten in 28 Tagen | offen | Journal |
| 0 Korrekturen ohne Artefakt > 24 h | offen | `auftragsraum.py offen --block` (Exit 0) |
| Kurzbefehl-Vorschläge nach `anwenden` 100 % im Ledger | offen | Positivkontrolle im MVC |
| Morgen-Zeitung ≥ 20/28 Tage im Raum | offen | Outbox-Log / Journal |
| Aufwachen gemessen, nicht geschätzt | offen | Sitzungsstatistik nach dem ersten Auftrags-Lauf, Wert im Journal (`tokens`) |

Threshold: kein ADR (Konvention über bestehendem Werkzeug, ein Repo); Stufe 3 → Charta-Entscheid #48 B.

## Befunde (Steelman → Diabolus → Maintainer-2028)

**Steelman.** Heute laufen Zurufe des Owners nur, während eine Sitzung offen ist; alles dazwischen geht in Mails an sich selbst oder verloren. Ein Raum, den der Owner ohnehin offen hat (Element), sammelt diese Zurufe ohne Kosten, und die Sitzung holt sie als Eingang ab — dieselbe Form wie `/mailcheck` mit dem Postfach (C6). Die Lernschleife macht aus der heutigen Praxis (Korrekturen landen in CLAUDE.md und Memory, wenn ich daran denke) eine gezählte Pflicht. Das Werkzeug existiert (C4), die Messbausteine existieren (C7–C9); neu ist nur die Regel.

| id | Befund | Klasse | Konsequenz |
|---|---|---|---|
| B1 | **Doppelquelle droht** zwischen Raum, Journal, Ledger und Issues, wenn der Sortierer Zustand schreibt | Diabolus | D5/R4: Journal trägt Ereignisse und Links, nie Zustand; Kurzbefehle schreiben über `board.py`, nicht direkt |
| B2 | **„Sichtbar machen" statt „verhindern":** die erste Fassung zählte Korrekturen ohne Artefakt nur | Diabolus | gekippt in der Widerlegung 2026-09-10 → D4: `regel` legt das Artefakt an, `offen --block` in `session-ende` verhindert das Sitzungsende ohne Artefakt |
| B8 | **K4-Werkzeug akzeptiert nacktes „offen" als Anker** — zwei Backlog-Zeilen der ersten Fassung bestanden die Prüfung ohne Artefakt | Diabolus | Werkzeug-Lücke [#3080](https://github.com/achimdehnert/platform/issues/3080); in dieser Fassung trägt jede Backlog-Zeile eine Nummer |
| B9 | **Journal ↔ Issue ohne Rücksynchronisation** (Zustand eines Auftrags könnte im Journal veralten) | Diabolus | D8: Zustand hat eine Heimat, das Journal spiegelt keinen; `offen` liest GitHub live |
| B3 | **Formal erfüllen, praktisch umgehen:** der Owner schreibt weiter in die Sitzung statt in den Raum; Journal bleibt leer, Kill-Gate reißt — das ist gewollt, nicht ein Fehler des Konzepts | Diabolus | Kill-Gate misst R3; keine Nötigung des Owners |
| B4 | **Verschlüsselung:** `sync` braucht das Lotsen-Gerät mit Olm-Schlüssel (C4); fällt das Gerät weg, liest niemand den Raum, und niemand merkt es | Diabolus | Verfallsignal „Nachricht ohne Bearbeitung > 24 h" fängt genau das; plus `chat_lotse.py status` als Kettenglied |
| B5 | **Maintainer 2028:** ein Journal mit Konto-Hashes und Links, ein Sortierer mit vier Mustern — verständlich ohne Erklärung; Gefahr ist die Musterliste für Korrekturen, die still wächst | Maintainer-2028 | Muster als Tabelle in der Betriebsakte, Änderung nur per PR mit Beispielnachricht; `betrieb_backlog_check` hält die Gegenrede-Pflicht |
| B6 | **Aufwachkosten** sind in Stufe 1 null, in Stufe 2 unbekannt (A2 nur Dateien) | Diabolus | Kill-Gate verlangt Messung vor Stufe 2; schlanke Chat-Rolle ohne Handover-Block als erster Versuch |
| B7 | **Stufe 3 ist attraktiv und gefährlich:** sobald der Lotse im Raum antwortet, wird der Raum faktisch Befehlskanal | Diabolus | ausdrücklich nicht Teil dieses Konzepts; Tür ist #48 B mit Owner-Grant (C3) |

**Zwei Alternativen**

| Alternative | Was | Warum nicht (oder: wann doch) |
|---|---|---|
| ALT-1 „Mail an mich" | Zurufe als Mail ans eigene Postfach, `/mailcheck` holt sie ab | Erfüllt Notiz und Auftrag ohne neuen Raum; Kurzbefehle ohne Modell fehlen, die Lernschleife wäre dieselbe. **Wann doch:** wenn das Kill-Gate reißt, ist das der Rückfall — kein Verlust, weil Journal und Regel unabhängig vom Kanal sind |
| ALT-2 „Bot sofort" (Stufe 3 zuerst) | Live-Lotse antwortet im Raum, Aufträge werden im Raum bearbeitet | Schnellstes Erlebnis, aber Blackbox mit Vollmacht: R2/B7, Art. 1.0; Kosten je Nachricht ungemessen (B6). Verworfen als Einstieg; bleibt als Stufe 3 hinter #48 B |

## Verbesserungs-Backlog (K4 — Prüfung: `python3 tools/betrieb_backlog_check.py docs/konzepte/KONZ-platform-059-auftragsraum-lernschleife-chat.md`)

| # | Vorschlag | Advocatus Diaboli | Out of the Box | Anker |
|---|---|---|---|---|
| 1 | Raum als Auftragseingang mit Sortierer ohne Modell (Stufe 1) | Ein Raum, den nur der Owner beschreibt und nur die Sitzung liest, ist eine teurere Notiz-App; ohne Live-Antwort bleibt das Chat-Gefühl aus | Kein Chat, sondern Mail an sich selbst — dieselbe Schleife, kein neuer Raum (ALT-1) | #3079 |
| 2 | Kurzbefehle `#N erledigt`, `#N Frist …` schreiben direkt ins Ledger | Zwei Muster, die still wachsen, werden eine Kommandosprache ohne Grammatik-Gate; ein Tippfehler schließt den falschen Vorgang | Statt Sprache: Reaktion (Emoji) auf die Morgen-Meldung des Vorgangs — `chat_lotse.py react` existiert, ein Haken schließt | #3049, #3079 |
| 3 | Korrektur → Regel-Artefakt im selben Zug, gezählt | Zählen verhindert nichts; die Sitzung kann die Korrektur bearbeiten und das Artefakt vergessen, der Zähler meldet es einen Tag später | Regel-Artefakt vom Werkzeug vorbereiten: `auftragsraum.py regel N` legt den Memory-Kandidaten mit Zitat und Link an, die Sitzung füllt nur das „Why" | in D4 übernommen, #3079 |
| 4 | Journal + vier Kennzahlen + drei Verfallsignale | Kennzahlen ohne Leser; der Owner sieht das Journal nie, nur ich | Kennzahlen als wöchentliche Nachricht des Lotsen in denselben Raum — dann liest sie der Owner dort, wo er schreibt | #3079 (Stufe 1, Bau) |
| 5 | Stufe 2: Auftrag → Issue → Lauf in schlanker Chat-Rolle aus der Sitzung | Der Lauf startet trotzdem erst, wenn eine Sitzung offen ist; für den Owner ändert sich gegenüber Stufe 1 nur die Automatik hinter dem Issue | Aufträge nicht als Issue, sondern als Ledger-Vorgang wie Mails (Frist, Zustand, Verlauf) — der Mailcheck kennt das Muster schon | #3079 (Entscheid nach Kill-Gate 2026-10-08) |
| 6 | K4-Prüfwerkzeug: nacktes „offen" nicht mehr als Anker zulassen | Strenger heißt mehr Fehlalarme in Akten, die ehrlich „offen" sagen; eine Datumsangabe ist Pflege | Anker-Prüfung nicht im Backlog-Werkzeug, sondern im Aufschub-Anker-Gate, das Prosa schon prüft — ein Prüfer statt zwei | #3080 |

## Entscheidung

**Als MVP annehmen (Stufe 1)**, Bau als eigener Auftrag mit Owner-Wort; Stufe 2 erst nach Kill-Gate-Auswertung 2026-10-08; Stufe 3 bleibt chat-hub#48 B. Wichtigste Begründung: das Werkzeug und die Messbausteine existieren, neu ist nur die Regel, und die Regel ist rückbaubar (Raum verlassen, eine Skill-Zeile). Stärke: Lernschleife wird zählbar. Schwäche: Stufe 1 fühlt sich nicht wie Chat an (B3). Sofortmaßnahme: Raum anlegen, Morgen-Zeitung hineinschreiben, Sortierer mit Fixture-Test. Unsicherheit: Aufwachkosten (A2). Finaler Threshold: kein ADR.

**30/60/90:** 30 = Raum, Sortierer, Journal, Morgen-Meldung, Betriebsakte, Skill-Zeile (PRs mit Owner-Approval für Skill/Governance). 60 = Kill-Gate-Zahlen ablesen, Aufwachen einmal gemessen, Entscheidung Stufe 2. 90 = Stufe 2 gebaut oder Raum als Notiz-Eingang eingefroren; Stufe 3 nur, wenn #48 B ratifiziert ist.

## Widerlegung (frischer Kontext, 2026-09-10)

Ein Advocatus Diaboli ohne Sitzungsgedächtnis prüfte die erste Fassung gegen den Auftrag #3079 und die Belege: 13 Punkte, 8 gekippt, 3 halten, 2 teilweise. Gekippt und eingearbeitet: Kurzbefehle schrieben in Stufe 1 direkt ins Ledger (jetzt Vorschlag + `anwenden`); „Rückfrage" war auf Stufe 3 verschoben (jetzt Klasse mit Art. 7); das Owner-Konto war nicht benannt (jetzt `OWNER_MXID`); das Regel-Artefakt hing an der Disziplin der Sitzung (jetzt `regel` + `offen --block`); der Kill-Gate-Wert 2 widersprach K2 (jetzt 0); `messjournal --anwendung auftragsraum` wurde als vorhanden gelesen (jetzt „zu bauen"); „Sitzungs-Ledger" war kein Werkzeug (jetzt Sitzungsstatistik, MCP als Hypothese); das K4-Werkzeug ließ „offen" als Anker durch (#3080, alle Zeilen tragen Nummern); Journal↔Issue ohne Rücksynchronisation (D8). Hält: das Konzept ist keine Umformulierung von #48 Stufe A (Klassen, Lernschleife, Kill-Gate sind neu); der Titel-Anspruch „selbst verbessernd" ist in Stufe 1 auf die Regeln begrenzt und steht jetzt so in der Kernthese.

**Ehrliche Enforcement-Grenze:** `review_by`, `kill_criteria` und der Kill-Gate-Status wirken hier als Review-Gate, nicht als Exit-Code; das Aufschub-Anker-Gate (C12) liest heute PR-Text und Issue-Kommentare, nicht dieses Dokument.
