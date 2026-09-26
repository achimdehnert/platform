---
retro_schema: 1
date: 2026-09-16
repo_scope: [chat-hub, platform]
session_id: 916eb7
footprint: full
findings_total: 12
findings_survived: 11
refuted_rate: 0.08
phase3_refuted: 1
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [inline-heredoc-quoting-rework, gate-lint-failure-no-local-gate-wirkungslos]
recurring_findings: [inline-heredoc-quoting-rework, lint-failure-no-local-gate, issue-open-after-its-fix-merged, deferred-item-no-tracking-issue]
gates_caught: [scope-checkpoint-not-durably-recorded, claim-before-cheapest-check]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "0 gekippt, 1 neu"
streichkandidaten: [retro-phase1-sammler-subagent]
---

# Session-Retro 2026-09-16 · chat-hub · 916eb7

Sitzung: Kapitäns-Session in platform, Arbeit in `iilgmbh/chat-hub`. Anlass: Im Raum „Achim / Lotse" kamen Nachrichten abgeschnitten an, außerdem wollte der Owner über den Raum Aufträge an Claude Code geben können. Scope sind PRs chat-hub#101, #103, #105, #106, #107, #108, Issues #102, #104 und #109 sowie der Host-Timer `lotse-auftrag-wache.timer`.

**Footprint `full`:** ein Code-Repo, 6 gemergte PRs, ein dauerhafter User-Timer auf dem Host, kein Deploy und keine Migration. Budget ≤7 Agenten, verbraucht 7: Sammler (haiku), 3 Finder (sonnet), 1 Skeptiker (sonnet) für 6 Bewertungsbefunde, Widerlegungsbahn (opus), Meta-Agent (sonnet).

**Phase 0.0:** `tools/gate_wirkung.py` meldet „Kein Gate rueckfaellig". Die Rückfall-Prüfung nach diesem Report ergibt eine neue Rückfall-Klasse (§5a).

## 1. Executive Summary

- Beide Ziele sind erreicht und echt belegt. Der Fix gegen abgeschnittene Nachrichten ist gemergt (#101). Der Weg Raum → Issue → Worker → PR lief einmal Ende-zu-Ende durch (#104 → #105), dazu kamen Rückfrage und Wächter (#107) sowie das Sicherheitsnetz (#108).
- Die schwersten Befunde betreffen das Sicherheitsnetz. Die Merge-Sperre deckt keine MCP-Werkzeuge ab (#4), `main` in chat-hub erzwingt serverseitig keinen PR (#12, aus der Widerlegungsbahn), und #108 wurde vor der CLI-Probe gemergt (#2). Alle drei sind in chat-hub#109 getrackt.
- Ein Mail-Auftrag in der ersten Owner-Nachricht wurde weder bearbeitet noch als nicht zuständig benannt (#1).
- Der Scope-Checkpoint kam erst nach 4 Merges und dem Timer-Start (#3). Das Gate `scope-checkpoint-not-durably-recorded` hat danach die fehlende Verankerung erzwungen.
- Das Gate `lint-failure-no-local-gate` ist rückfällig. Der Push-Hook greift nur in Repos mit ruff-Konfiguration, chat-hub hat keine, prüft `ruff format` aber in der CI (#10).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Mail-Auftrag aus der ersten Nachricht weder bearbeitet noch als abgegrenzt benannt | Kommunikation | hoch | SURVIVES | Transkript 07:23:37 (Auftrag) vs. erste Antwort 07:23:56 (nur Kürzung); `git grep` nach dem Empfängernamen auf origin/main 0 Treffer; #102 Out-of-Scope nur generisch | neu: `nebenauftrag-in-meldung-nicht-abgegrenzt` |
| 2 | chat-hub#108 gemergt, bevor die CLI-Annahme von `--disallowedTools … --` geprüft war | fehlende Validierung | mittel | SURVIVES | `gh pr view 108`: mergedAt 10:50:09Z; Owner-Probe (Ausgabe „OK") als PR-Kommentar 10:50:59Z; PR-Body „Nicht belegt" | neu: `sicherheitsmechanismus-vor-probe-gemergt` |
| 3 | Scope-Checkpoint erst nach 4 Merges und dem Start des dauerhaften Host-Timers | Prozesslücke | mittel | SURVIVES | Merges #101/#103/#106/#107 07:32–09:51; Timer aktiv seit 09:51:09; Checkpoint-Kommentar #102 10:25:56 | neu: `scope-checkpoint-nach-dienst-start` |
| 4 | Merge-Sperre des Workers deckt MCP-GitHub-Werkzeuge nicht ab | Wissenslücke | hoch | SURVIVES | `merge_sperre()` in `deploy/lotse_auftrag.py` (origin/main) nur Bash-Muster; `~/.claude.json` mcpServers enthält `github`; kein Projekt-Override in chat-hub | neu: `merge-sperre-ohne-mcp-pfad` |
| 5 | go-vs-Entwurf-Vergleich mischt lokale Sendezeit und Server-Zeitstempel | fehlende Validierung | niedrig | SURVIVES | `merke_gesendet` `time.time()` vs. `event.server_timestamp`; kein Test mit divergierenden Quellen | neu: `zeitvergleich-zwei-uhrquellen` |
| 6 | Standard „nicht gelistet = pr" sei eine verfrühte Festlegung | verfrühte Festlegung | mittel | REFUTED | Vorschlag [40] „Standard: nur PR" 10:25:49, Owner „46 bgo" 10:28:22 vor dem Bau | — |
| 7 | Erstes go (#103) war an keinen Entwurf gebunden, Nachbesserung erst in #106 | fehlende Validierung | mittel | SURVIVES | `gh pr diff 106`: `pruefe_go(…)` bekommt `entwurf_event`, neuer Zeitvergleich | neu: `freigabe-ohne-bindung-an-vorlage` |
| 8 | Issue #104 offen trotz gemergtem Worker-PR #105 (`Refs` statt `Closes`) | Prozesslücke | niedrig | SURVIVES | `gh issue view 104`: state OPEN, Labels `auftrag-raum`, `erledigt` | `issue-open-after-its-fix-merged` ×4 |
| 9 | Owner-Entscheid „platform ohne Aufstieg" nur im Kommentar eines geschlossenen Issues und im PR-Text | Prozesslücke | niedrig | SURVIVES | #102 CLOSED, letzter Kommentar „Offen: platform …"; bis zu chat-hub#109 kein eigenes Artefakt | `deferred-item-no-tracking-issue` ×42 |
| 10 | Lokales Lint deckt die CI nicht ab (kein `ruff format`, shellcheck lokal nicht installiert): zwei rote CI-Läufe | Werkzeug | mittel | SURVIVES | Run 35068577100 (#101, ruff format), Run 35069705579 (#103, SC1091); Makefile `lint` ohne `ruff format --check`; `make lint` → „shellcheck: not found"; chat-hub ohne ruff-Konfiguration (0 Treffer, Positivkontrolle platform 26) | `lint-failure-no-local-gate` ×12 → Gate rückfällig |
| 12 | `main` in chat-hub erzwingt serverseitig weder PR noch Pflicht-Checks, die Merge-Sperre hängt allein am Worker | Wissenslücke | hoch | SURVIVES (3b NEU) | `gh api repos/iilgmbh/chat-hub/rules/branches/main` nur `deletion`, `non_fast_forward`; `branches/main/protection` 404 | neu: `merge-sperre-nur-clientseitig` |
| 11 | Datei-Edits per `python3 - <<EOF` mit `assert`-Ankern statt Edit-Werkzeug: 3 Fehlläufe | Werkzeug | niedrig | SURVIVES | Kennzahlen: Traceback 09:46:09; Ablehnungen der Heredoc-Edits 10:32:14 und 10:34:53, danach Edit-Werkzeug | `inline-heredoc-quoting-rework` ×2 → GATE-PFLICHT |

Befunde 8, 9, 10 und 11 sind kommandobelegt und gingen ohne Skeptiker durch, ebenso Befund 7. Die Befunde 1–6 sind Bewertungsbefunde, ein Skeptiker hat sie gebündelt geprüft (5 SURVIVES, 1 REFUTED).

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| zielerreichung | 4 | beide Ziele Ende-zu-Ende belegt; Mail-Teil offen (#1) |
| architektur_design | 3 | Lücken im Sicherheitsdesign #4, #7, #5 |
| code_konventionstreue | 4 | Tests `test_should_*`, Commit-Format eingehalten; Lint-Rework #10 |
| risiko_debt | 3 | #4 und #12 offen, #2 nachträglich belegt; Restpunkte in chat-hub#109 getrackt |
| prozess_effizienz | 3 | zwei rote CI-Läufe #10, Edit-Fehlläufe #11 |
| entscheidungsqualitaet | 3 | Scope-Checkpoint spät #3, Merge vor Probe #2 |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Erste Antwort griff nur die Kürzung auf, der Mail-Teil blieb unerwähnt | Jede Teilaufgabe der Eingangsnachricht im ersten Board führen, auch als „gehört der Raum-Session, nicht mir" | #1 |
| #108 gemergt, CLI-Probe 50 s später durch den Owner | Blockierte Probe zuerst an den Owner geben, mergen erst nach „OK" | #2 |
| Checkpoint nach 4 Merges und Timer-Start | Checkpoint vor dem ersten Schritt, der einen dauerhaften Dienst oder Agentenstart einrichtet | #3 |
| Sperrliste nur aus Bash-Mustern gebaut | Beim Bau einer Werkzeugsperre die Werkzeugliste des Zielprozesses erheben (`claude mcp list`), MCP einbeziehen oder `--strict-mcp-config` | #4 |
| Zeitvergleich über zwei Uhren | Beide Seiten aus derselben Quelle (Server-Zeitstempel des eigenen Events) plus Test mit Versatz | #5 |
| go-Prüfung ohne Bezug zum Entwurf gemergt, Lücke erst in der Probe erkannt | Vor dem Merge eines Freigabe-Mechanismus eine Replay-/Fehlzuordnungs-Liste durchgehen und je Fall einen Test schreiben | #7 |
| Worker setzt `Refs`, #104 bleibt offen | Abnahme schließt das Issue (seit #108 `abnehmen`); Alt-Issue #104 per Abnahme oder von Hand schließen | #8 |
| Offene Owner-Frage nur als Kommentar im geschlossenen Issue | Offene Entscheidung im selben Zug als Checkbox in einem offenen Issue (jetzt chat-hub#109) | #9 |
| Push ohne lokalen Format-/Shellcheck, die CI fand beides | Hook greift auch, wenn der Workflow `ruff format`/shellcheck aufruft; lokal Container-Shellcheck | #10 |
| Heredoc-Ersetzungen scheitern an verschobenen Ankern | Mehrzeilige Änderungen an bestehendem Code per Edit-Werkzeug | #11 |
| Sicherheitsnetz nur im Worker gebaut, Server-Regeln nicht angesehen | Vor einer clientseitigen Sperre die Branch-Regeln des Ziel-Repos abfragen und „PR + Pflicht-Checks" serverseitig setzen (Owner-Gate) | #12 |

Invariante: 11 Soll-Schritte = 11 überlebende Befunde.

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (Stand origin/main d70e622d):

- `inline-heredoc-quoting-rework`: bisher ×1 (40c069), mit dieser Retro ×2 ⇒ **GATE-PFLICHT**. Es gibt noch kein Gate, deshalb steht der Slug unter `gate_candidates` (§7).
- `lint-failure-no-local-gate`: ×11 → ×12. Das Gate existiert bereits ⇒ Rückfall, siehe §5a.
- `issue-open-after-its-fix-merged`: ×3 → ×4, gedeckt vom Gate `issue-offen-nach-gemergtem-fix` (advisory, `tools/session_abgleich.py`). Das Gate misst am Sitzungsende, und das steht noch aus. Kein Rückfall, bis `session-ende` gelaufen ist.
- `deferred-item-no-tracking-issue`: ×41 → ×42, gedeckt von `aufschub-anker` (blocking). Das Vorkommen liegt in chat-hub. Ob der Workflow des Gates dort läuft, ist ungeprüft (§8). Der Anker ist inzwischen gesetzt (chat-hub#109).
- `scope-checkpoint-not-durably-recorded`: Das Gate hat in dieser Sitzung zweimal gefeuert (Fehlerform A und B), und beide Male wurde danach gehandelt: Checkpoint ausgesprochen und als #102-Kommentar verankert ⇒ `gates_caught`, kein Rückfall. Die späte Zeit (#3) ist eine eigene, neue Klasse.
- `claim-before-cheapest-check`: Der Stop-Hook hat einmal gefeuert. Danach lief der Check mit Positivkontrolle (0 vs. 26) ⇒ `gates_caught`.

Abgleich MEMORY.md: `feedback_monitor_event_truncated_500_chars.md` und `project_raum_auftraege_an_claude_code.md` existieren (in dieser Sitzung angelegt). Für die neuen Slugs gibt es keine Drift-Memory.

### 5a. Rückfall-Prüfung

| Gate | Rückfälle seit Bau | Ursache (Ausgang/Quelle) | Konsequenz |
|---|---|---|---|
| `lint-failure-no-local-gate` | 1 (diese Retro, Befund #10) | **Quelle:** `tools/claude-hooks/block_unformatted_push.sh` läuft „nur in Repos mit ruff-Config". chat-hub hat keine, die CI (`.github/workflows/ci.yml:42`) prüft trotzdem `ruff format`. shellcheck deckt der Hook gar nicht ab. | **ausweiten:** Hook zusätzlich auslösen, wenn ein Workflow im Repo `ruff format` bzw. `shellcheck` aufruft, mit neuer `positivkontrolle` (Repo ohne ruff-Config, CI mit ruff format). Registry-Eintrag bekommt `revised` + `revision_note`. Umsetzung als eigener platform-PR, Freigabe siehe §7 [R4]. |

Weitere registrierte Gates mit Vorkommen in dieser Retro: `issue-offen-nach-gemergtem-fix` (Messpunkt steht noch aus, s. o.), `aufschub-anker` (Wirkbereich ungeprüft, §8), `scope-checkpoint-not-durably-recorded` und `claim-before-cheapest-check` (gefangen).

### 5b. Autonomie-Kalibrierung

- `over_ask`: 0. Die vorgelegten Punkte (Merge-Wort, Sicherheitsnetz, platform-Aufstieg) berühren Merge oder Rechte-Erweiterung und sind damit keine deterministisch-reversiblen Schritte.
- `over_act`: 0. Jeder Merge und der Timer hatten ein eigenes Owner-Wort („1 go 2 go 5 go", „merge 103", „go 20 19", „46 bgo"). Der Finder-Vorschlag, #3 als over_act zu werten, ist verworfen: Der Skeptiker bestätigt Einzelfreigaben je Schritt, nur die Gesamtspiegelung kam spät.

## 6. Verankerung

**memory_candidates** (kopierfertig, der Owner entscheidet):

```markdown
---
name: feedback_werkzeugsperre_mcp_mitdenken
description: Eine Werkzeugsperre für einen headless Claude-Worker muss MCP-Werkzeuge einschließen — Bash-Muster allein lassen mcp__github__* offen
metadata:
  type: feedback
drift: true
drift_episode: 2026-09-16-merge-sperre-ohne-mcp
---
Beim Sicherheitsnetz der Raum-Aufträge (chat-hub#108) sperrte `--disallowedTools` nur Bash-Befehle; der Worker lädt aber die user-weiten MCP-Server (u. a. `github`).
**Why:** Die Annahme war, Merge ginge nur über `gh`/`git`.
**How to apply:** Vor dem Bau einer Sperre die Werkzeugliste des Zielprozesses erheben (`claude mcp list`) und MCP sperren oder per `--strict-mcp-config` abschalten. Tracking: chat-hub#109.
```

```markdown
---
name: feedback_teilauftraege_der_eingangsnachricht_benennen
description: Enthält die erste Owner-Nachricht mehrere Aufgaben, jede im ersten Board führen — auch „gehört der Raum-Session"
metadata:
  type: feedback
---
Retro 916eb7 #1: Der Mail-Teil blieb unerwähnt, weil nur die Kürzungs-Panne bearbeitet wurde.
**Why:** Unerwähnt heißt für den Owner „vergessen", nicht „nicht zuständig".
**How to apply:** Erste Antwort zählt jede Teilaufgabe als Zeile, mit Zuständigkeit.
```

**adr_candidates:** keiner. Die Raum-Aufträge sind eine Erweiterung nach bestehendem Muster (SA-4, Freigabe-Zeile), gedeckt von `adr-threshold.md`.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| R1 | MCP in Merge-Sperre | chat-hub | #109 | 🔵 ready | Fix-PR (ich) |
| R2 | Eine Uhrquelle im go-Vergleich | chat-hub | #109 | 🔵 ready | Fix-PR (ich) |
| R3 | `make lint` = CI | chat-hub | #109 | 🔵 ready | Fix-PR (ich) |
| R4 | Hook `lint-failure…` ausweiten | platform | §5a | 🟢 offen | Go geben (du) |
| R5 | Gate für Heredoc-Edits | platform | §5 | 🟢 offen | bauen oder declined (du) |
| R6 | platform ohne Aufstieg | chat-hub | #109 | 🟢 offen | ja/nein (du) |
| R7 | #104 schließen | chat-hub | #104 | 🟢 offen | ansehen (du) |
| R8 | Mail-Auftrag klären | Raum | — | 🟢 offen | Zuständigkeit sagen (du) |
| R11 | `main`: PR + Checks Pflicht | chat-hub | #109 | 🟢 offen | Freigabe (du) |
| R9 | Streichkandidat Sammler | platform | §Streichbahn | 🟢 offen | entscheiden (du) |
| R10 | Memory-Kandidaten | Memory | §6 | 🟢 offen | übernehmen? (du) |

## 8. Nicht verifiziert (Restlücken)

- **Ob der Worker die MCP-Server tatsächlich lädt**, ist plausibel (user-weite Konfiguration, kein Override), aber nicht live gemessen. Billigster Check: im Worker-Log eines Auftrags nach `mcp__` suchen oder `claude -p --debug` im Worktree.
- **Wirkbereich von `aufschub-anker` in chat-hub:** Ob der Workflow dort läuft, ist ungeprüft. Billigster Check: `gh api repos/iilgmbh/chat-hub/contents/.github/workflows --jq '.[].name'`.
- **Mail-Auftrag:** Ob die Raum-Session den Auftrag nach der Kürzungs-Rückfrage erhalten und bearbeitet hat, wurde nicht geprüft. Billigster Check: das Transkript der Raum-Session nach dem Empfängernamen durchsuchen.
- **Push-Varianten in #12:** Dass `git -C <pfad> push origin main` an den Sperrmustern vorbeigeht, ist eine Hypothese der Widerlegungsbahn und nicht live getestet.
- **Kosten:** Jeder Auftrag läuft mit `--model opus` und ohne Budget. Nicht gemessen; billigster Check: Worker-Logs unter `auftraege/` auswerten.
- **Phase 6 (Extern-Handoff):** n/a, der Footprint ist nicht `deep`.

**Vierklang (Eiserne Regel 5):**

- **getan:** Wirkungsbilanz, Sammler, drei Finder, ein Skeptiker, Längsschnitt, Rückfall-Prüfung, Tracking-Issue chat-hub#109, Widerlegungsbahn.
- **angenommen:** Der Owner-Probelauf („OK") belegt die CLI-Annahme für den Worker-Aufruf, obwohl dort zusätzlich `--permission-mode auto` gesetzt ist.
- **nicht verifizierbar:** ob der Mail-Teil der ersten Nachricht an diese Sitzung gerichtet war oder nur den Raum-Verlauf zitierte.
- **offen geblieben:** R1–R11 und die Checks oben.

## Widerlegung

Opus in frischem Kontext, liest nur (origin/main: chat-hub, platform d70e622d). Ergebnis: **0 gekippt, 1 neu.**

- **Frage 1 (SURVIVES zu Unrecht?):** keiner gekippt. #2 bestätigt; die Widerlegungsbahn hält „mittel" eher für zu hoch, weil ein Fehlschlag der CLI-Übergabe ohne Merge endet. Bestätigt sind außerdem #4 (Sperre Z. 286, Worker-Aufruf Z. 651 ohne MCP-Abschaltung), #8, #9 (#102 war schon geschlossen, als #107 und #108 noch darunter gebaut wurden) und #10 (beide Läufe `failure`, `lint` ohne `ruff format`). Für #1, #3, #5, #7 und #11 fand sich kein Gegenbeleg.
- **Frage 2 (REFUTED zu früh?):** nein. #6 bleibt widerlegt: Vorschlag [40] und das Owner-Wort „46 bgo" lagen vor dem Bau.
- **Frage 3 (fehlende Dimension):** **NEU #12**. Die serverseitigen Branch-Regeln von chat-hub erzwingen keinen PR, die Merge-Sperre ist rein clientseitig. Keiner der Finder hatte die Server-Seite im Blick.
- **§5a und §5 gegengeprüft:** Der Hook bricht ohne ruff-Konfiguration ab (Z. 78–84) und prüft keinen shellcheck. Die `retro_kpis.py`-Zähler stimmen (Vorstand je +1).
- **Abdeckung ohne Befund:** Absenderprüfung (Z. 117–122), Rückweg und Timer, Worker-Timeout, Tests (22 `test_should_*`). Kosten sind nicht geprüft (§8).
- **Hinweis Öffentlichkeit:** Der Entwurf nannte einen Nachnamen und eine Privatangelegenheit. Beides ist vor dem Commit entfernt, die Kontrollprobe steht im PR.

## Streichbahn

**Kandidat `retro-phase1-sammler-subagent`**, Belegart **kein Effekt**: Alle drei Finder haben `gh pr view`/`gh issue view`/`git show origin/main` für dieselben PRs und Issues selbst gezogen (ihre Belege nennen eigene Befehle). Der Sammler-Report enthielt dagegen zwei Fehler: einen falschen Titel für #104 und „CLI `--disallowedTools` ungeprüft", obwohl der Beleg als PR-Kommentar auf #108 vorlag. Seit 2026-09-14 liefert `retro_transkript_kennzahlen.py` die Transkript-Zahlen. Für `full` genügt eine Artefaktliste im Finder-Prompt.

## Self-Review

Meta-Agent (sonnet) prüfte den Report gegen die Skill-Regeln, nicht die Sitzung.

- **Belege:** 5 Befunde unabhängig nachgezogen (#2, #4, #8, #10, #12), alle bestätigt.
- **Form:** Scores ganzzahlig und verankert, Invariante 11 = 11, Frontmatter vollständig, §5a mit Klasse „Gate rückfällig". `retro_report_check.py` gibt Exit 0. `grep -niE "@|passw|token|immobil"` findet 0 Treffer.
- **Korrigiert:** Die Belegart des Streichkandidaten lautete „Dublette" und heißt jetzt „kein Effekt".
- **`refuted_rate` 0,08:** Der Wert liegt unter dem Band 0,2 (Theater-Risiko). Die echte Quote ist 1/(12−0) = 0,083. Einordnung: Der Skeptiker bekam nur die 6 Bewertungsbefunde, 5 davon sind kommandobelegt und nach Skill-Regel nicht zu falsifizieren. Bezogen auf die geprüften Befunde liegt die Quote bei 1/6 = 0,17. Das bleibt knapp unter dem Band und ist in der nächsten Retro im Auge zu behalten.
