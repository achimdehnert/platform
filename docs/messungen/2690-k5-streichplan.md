# K5 — Streichplan & Kontext-Diät für die drei Session-Skills

> Auftrag: [platform#2690](https://github.com/achimdehnert/platform/issues/2690), Kriterium **K5**
> (Out-of-the-Box-Streichbahn + Kontext-Diät ≤ 60 KB, kein Pflichtinhalt ersatzlos).
> Read-only-Analyse, Stand 2026-09-02, `main` @ `1a379f55`. Keine Edits, kein Commit.

## 0. Ausgangslage (gemessen)

| Datei | Bytes | Zeilen | `##`/`###` | Ziel (Plan) | Reduktion |
|---|---:|---:|---:|---:|---:|
| `.windsurf/workflows/session-start.md` | 35 196 | 551 | 23 | **14 000** | −60 % |
| `.windsurf/workflows/session-ende.md` | 52 152 | 966 | 27 (+37 Code-`#`-Zeilen als Fehl-Überschriften) | **20 000** | −62 % |
| `.windsurf/workflows/session-retro.md` | 42 156 | 525 | 14 | **22 000** | −48 % |
| **Summe** | **129 504** | 2 042 | | **56 000** | **−57 %** |

Zielmarke des Issues ist ≤ 60 KB → der Plan lässt ~4 KB Puffer (u.a. für die zwei neuen
Retro-Bahnen aus K5 Teil 2, die im Ziel schon eingerechnet sind).

**Messmethode Byte-Größe je Sektion:** Offset der `^#{1,3} `-Überschrift bis zur nächsten,
über die rohe Datei (`python3`, kein Tool-Zwischenschritt). Bei `session-ende.md` zählen
einige `#`-Kommentarzeilen in Bash-Blöcken als Überschrift mit — deren Bytes sind der
darüberliegenden echten Sektion zugerechnet.

**Grober Anteil „Begründungsprosa"** (Zeilen mit `>`-Blockquote ODER einem der Marker
`Lesson|Lehre|Realfall|Anlass|gemessen|Drift|Retro |Belegt|Messung|Beleg:|Warum `):
start ≈ 6,7 KB · ende ≈ 13,0 KB · retro ≈ 7,3 KB = **27 KB (21 % aller Bytes)**.
Changelog-Sektionen zusätzlich: 5,2 + 4,6 + 8,2 = **18,0 KB (14 %)**.
Zusammen sind das **35 % der 130 KB** — ohne eine einzige Anweisung anzufassen.

---

## 1. Inventar `session-start.md` (35 196 B → 14 000 B)

| Sektion (Zeile) | Bytes | Klasse | Beleg / Begründung | Ziel-B |
|---|---:|---|---|---:|
| Frontmatter + `# /session-start` + Bootstrap (1) | 402 | PFLICHT-KERN | Kaltstart-Einstieg (K1) | 400 |
| `## Verwendung` (18) | 513 | PFLICHT-KERN | Argument-Semantik `TARGET_REPO` | 250 |
| `## Platform Sync Loop (Prinzip)` (37) | 480 | **TOT (Dublette)** | Identischer Block in `session-ende.md` Z. 17–27 (beide: gleiches ASCII-Diagramm + „GitHub ist die einzige Source of Truth"). Zwei Kopien derselben Aussage in zwei Skills, die nie zusammen gelesen werden. | 200 (nur in start, ende verlinkt) |
| `## Phase 0` Präambel (50) | 594 | LEHRE/BEGRÜNDUNG | Erklärt, *warum* es den Runner gibt (Retro c494a2) — für die Ausführung irrelevant | 250 |
| `### 0.R Runner ausführen` (59) | **11 590** | gemischt, s.u. | **größter Einzelposten des Skills (33 %)** | **1 800** |
|  ├ Aufruf + `RESULT`-Regel + Journal-Lautstärken | ~1 500 | PFLICHT-KERN | ohne den Aufruf passiert gar nichts | 900 |
|  ├ WARN-Deutung für 0.4/0.7/0.7.6/0.7.7/0.7.11/0.7.12/0.7.16/0.7.17/0.7.18/0.4.1 | ~8 000 | **BEREITS-IM-RUNNER (Deutung gehört an die Phase)** | Alle 10 Phasen existieren als `record "<id> …"` im Runner (verifiziert: `grep -oE 'record "[^"]+"' tools/session_start_checks.sh` → 38 Phasen, darunter alle genannten). Die Klassen-Erklärung („5xx vs. NXDOMAIN", „abgelaufen vs. fallback-zertifikat", „SAMMELPHASE ≠ Entwarnung") ist **Wissen über die Ausgabe des Runners** und gehört als Notiztext neben die `record`-Zeile bzw. in `docs/governance/session-start-warnklassen.md`, nicht in den Skill-Ausführungstext. | 500 (Zeiger + „jede ⚠️ ist ein Befund") |
|  └ `**Troubleshooting**`-Block (181–202) | ~2 100 | **BEREITS-IM-RUNNER / teils TOT** | `ping`-Verbot: Runner Z. 90 `0.1 Server-Erreichbarkeit (TCP-Probe, NIE ping — Hetzner blockt ICMP)`. pgvector-sudo-Fallback: Runner Z. 244 `0.5 pgvector-Tunnel (PFLICHT, einziger Hard-FAIL)`. Stash-Semantik: Runner Z. 113 ff. `0.4 Parallel-Session-Guard` (Guard statt Stash ist im Code). **TOT:** „in Windsurf: `/windsurf-clean`" — `~/.claude/policies/claude-skills.md` Z. 10: „Windsurf wird **nicht mehr zum Coden** genutzt … ausschließlich das Review-Subset (ADR-229)". | 400 |
| `### Architecture Context laden` (204) | 972 | PFLICHT-KERN | Judgment-Phase, bewusst nicht im Runner (Runner-Kopf Z. 3–4) | 600 |
| `### 0.4.3 Worktree` (219) | 1 847 | PFLICHT-KERN + LEHRE | Kern = `repo-session.sh start`-Aufruf + „Haupt-Tree heilig" (ADR-233-Kill-Gate). Der `--ziel`-Rechtfertigungsabsatz (~700 B, „hätte am 2026-08-04 eine Kette in vier Sitzungen zerschnitten") ist Begründung. | 900 |
| `### 0.8 Modell-Tier` (245) | 1 106 | PFLICHT-KERN | Tabelle ist die Anweisung; `policies/session-routing.md` ist SSoT → Preisanekdote ($1577) raus | 900 |
| `## Phase 1: Kontext laden` (263) | 1 368 | PFLICHT-KERN | 7 nummerierte Schritte, kein Runner-Äquivalent | 1 000 |
| `## Phase 2: pgvector Warm-Start` (286) | 952 | PFLICHT-KERN | Runner 0.5 prüft nur den **Tunnel**, nicht die Suche — kein `record`-Eintrag für Memory-Search | 600 |
| `## Phase 2.5: Error-Learning` + Auto-Issue-Template (307–346) | 1 662 | **STREICHKANDIDAT** | **Leser-/Wirkungstest:** Das Template erzeugt Issues mit Titel `[adr-candidate] Recurring: …` und Labels `adr-candidate, auto-detected`. `gh issue list --label auto-detected --state all` → **2 Treffer**, davon exakt **einer** aus diesem Template: #82, erstellt **2026-04-30**, geschlossen 2026-08-20. In 125 Tagen kein zweites Artefakt. Die 30-zeilige Template-Kopie im Skill hat also faktisch nie gefeuert. **Vorschlag:** Auswertungs-Tabelle (3–4×/5–9×/10×+) als 4 Zeilen behalten, Issue-Erzeugung an `tools/befund_journal.py`-Muster oder einen Cron abgeben. | 400 |
| `## Phase 2.6 Handover↔Memory-Reconciliation` (349) | 1 354 | PFLICHT-KERN + LEHRE | Kern = „Prio gegen Memory abgleichen, Diskrepanz IST der Fund" (~250 B). Der iPad/claude.ai-Realfall (630 B Blockquote) ist Begründung. **Teilüberlappung, nicht Ersatz:** Runner Z. 453 `0.7.4 Prio zeigt auf Erledigtes` prüft GitHub-Referenzen der Prio-Zeilen, **nicht** pgvector-Memory → Phase bleibt. | 700 |
| `## Phase 2.7 Zielzustand` (375) | 1 305 | PFLICHT-KERN | SA-4-Anker, Gegenstück zu ende-0d | 800 |
| `## Phase 3: Arbeitsplan` (395) | 200 | PFLICHT-KERN | das eigentliche Ergebnis des Skills | 200 |
| `## Startklar-Checkliste` (401) | 3 202 | PFLICHT-KERN + LEHRE | Die Tabelle (17 Zeilen) ist das Ausführungstreue-Gate. Der Lesson-Blockquote (630 B) + der „Pflicht-Selbstcheck (2-Schritt)"-Absatz (900 B) sind Begründung; die **Regel** daraus ist ein Einzeiler: „Neue Pflicht-Phase ⇒ Checklisten-Zeile im selben PR; Auswahl über `grep -n '^## \|^### '`, nicht über das Wort PFLICHT." Zellen sind zudem 3–4 Zeilen lang (2c–2f) → Lean-Kürzung. | 2 000 |
| `## MCP-Server Quick-Reference` (441–465) | 1 097 | **TOT** | Zwei Tabellen mit `mcp0_`…`mcp5_`-Prefixen. Der Skill sagt selbst zwei Zeilen darunter, dass diese Nummern „Windsurf-Ära und environment-volatil" sind und `project-facts.md` die Quelle ist (existiert: `.windsurf/rules/project-facts.md`). Policy `claude-skills.md` Z. 10 bestätigt: Windsurf codet nicht. Die Tabelle ist eine Kopie einer als nicht-autoritativ deklarierten Quelle. | 150 (1 Zeile Zeiger) |
| `## Anti-Patterns` (469) | 1 131 | PFLICHT-KERN | Policy `claude-skills.md` §Pflicht-Review-Gate Pkt. 3 verlangt sie | 900 |
| `## Changelog` (486) | 5 300 | **CHANGELOG** | 10 Einträge, ältester ≤2026-06-24. Inhalt ist zu 100 % Historie. **Achtung Policy-Konflikt** → §4 Diabolus. | 600 (letzte 3 Einträge + Verweis) |

**Lücke am Rand (kein Streich, sondern Nachtrag):** Checklisten-Zeile 7a und ein
Anti-Pattern verweisen auf **0.4.4 Basis-Abstand**, aber die WARN-Deutungsliste in 0.R
erklärt 0.4.4 **nicht** (Runner hat die Phase: Z. 168). Beim Straffen muss 0.4.4 in die
Warnklassen-Doku, sonst zeigt die Checkliste auf nichts.

---

## 2. Inventar `session-ende.md` (52 152 B → 20 000 B)

**Struktureller Hauptbefund:** Es gibt **keinen** `session_ende_checks.sh`
(`ls tools/ | grep -i -E 'session|ende|retro'` → `session_start_checks.sh`,
`session-leases`, `session-memory`, `repo-session.sh`, `retro_kpis.py`,
`session_collision_meter.py` — **kein Ende-Runner**). Deshalb steht in diesem Skill
mechanischer Bash-Code, den `session-start` längst ausgelagert hat. **Das ist der
größte Einzelhebel für K5 und zugleich der Beitrag zu K1** (ein Runner ist nicht
überspringbar).

| Sektion (Zeile) | Bytes | Klasse | Beleg / Begründung | Ziel-B |
|---|---:|---|---|---:|
| Header + `## Platform Sync Loop` (6–27) | 912 | TOT (Dublette zu start) | s. §1 | 400 |
| `## Phase −0.1 Version-Banner` (30) | 1 044 | **RUNNER-KANDIDAT** | Reines `echo`-Kästchen + `GITHUB_DIR`-in-`.bashrc`-Eintrag. Identische Logik läuft im Start-Runner als `record "0.0 env+banner"`. | 150 |
| `### 0a Blockierte Arbeit` (57) | 572 | PFLICHT-KERN | 3 Fragen, Judgment | 300 |
| `### 0a-deploy` (73) | 1 203 | **RUNNER-KANDIDAT** | Ein `gh run list --workflow=Deploy`-Aufruf je Repo + 3 Verzweigungen. Genau die Messung, die der Start-Runner als `record "0.7 deploy-scan"` schon flottenweit fährt (Z. 286 ff., inkl. `waiting`-Klasse). Im Skill bleibt die Deutung „`failure` ⇒ nicht als fertig melden". | 300 |
| `### 0a-handover-pr` (92) | 1 395 | **RUNNER-KANDIDAT** | Zwei `gh pr list`-Abfragen + Fallback. Mechanisch, gate-registriert unter `parallel-session-pr-collision`? Nein — gehört zum Gate `handover-stale-vor-merge` (Registry: `module: scripts/checks/agent_handover_freshness_check.py`). Der Suchlauf selbst ist reine Mechanik. | 250 |
| `### 0a-merge` (116) | 1 479 | PFLICHT-KERN + LEHRE | Kern = 2 `gh pr merge`-Zeilen + die **4-Grenzen-Tabelle** (Judgment, Owner-Weisung). Der Begründungs-Blockquote (~600 B) ist Lehre. | 700 |
| `### 0a-freshness` (144) | 1 094 | PFLICHT-KERN (schlank) | Gate `handover-stale-vor-merge` ist registriert **und** läuft seit 2026-08-20 zusätzlich als CI-Advisory bei **jedem** PR (Registry-`revision_note`: „Neue Datei `.github/workflows/handover-freshness-advisory.yml` laeuft bei JEDEM PR"). Skill-Phase bleibt als zweiter Leser, aber als 3-Zeiler. | 400 |
| `### 0b Handover aktualisieren` (165–216) | 2 297 | PFLICHT-KERN + LEHRE | Das Stand-Template (~700 B) ist Pflicht (K6 hängt daran). Der KONZ-027-Arm-A-Blockquote (~1 100 B: „GitHub wendet `merge=union` serverseitig nicht an …") ist eine Messnotiz. Regel daraus: *„`AGENT_HANDOVER_LOG.md` nur anhängen (CI `handover-append-only`); `AGENT_HANDOVER.md` umschreiben."* | 1 000 |
| `### 0c Prios nachziehen` (218) | 1 004 | PFLICHT-KERN | 800 |
| `### 0d Abnahme + SA-4-Zähler` (236) | 1 302 | PFLICHT-KERN | Messstelle für K6 | 800 |
| `### 0e Clear-Härte` (255) | 2 269 | PFLICHT-KERN + LEHRE | Kern = 3-Fragen-Tabelle + „kein automatisches `/clear`" (~700 B). Der illustration-hub-Realfall + die `grep -ic`-Positivkontrolle (~1 400 B) sind Beleg für die *Existenz* der Phase, nicht für ihre Ausführung. | 800 |
| `### 0f Cross-Repo-Befunde` (289) | **4 200** | PFLICHT-KERN + LEHRE | Kern = `befund_journal.py --offen-cross-repo`, die Verankern/Verzicht-Tabelle, `--echt`/`--falsch`, die zwei zulässigen Abschlüsse für rückfällige Gates, Scope-Checkpoint (~1 400 B). Rest (~2 800 B: fünf `[deploy-health]`-Issues, vier Fehlalarme am 2026-08-20, „16 Rückfälle") ist Herleitung. | 1 400 |
| `### 0g Zusagen prüfen` (364) | 2 528 | PFLICHT-KERN + LEHRE | Kern = Schleife über eigene PRs + `verankerung_pruefer.py` + **4 Ausgabeklassen** (✅ / ⚠️ / `◌ NICHT PRUEFBAR` / `◌ UNGEPRUEFT`) + „Modus advisory, Präzision 0,50". Die Fettschrift-/Anker-Anekdote (~800 B) ist Lehre. | 1 000 |
| `## Phase 1 knowledge-capture` (403) | 893 | PFLICHT-KERN | Delegation + Erfolgs-Check | 500 |
| `## Phase 1b Docu-Drift-Check` (421–509) | **3 241** | **STREICHKANDIDAT** | Drei Bash-/MCP-Blöcke + vollständiges Issue-Template im Skill-Text. Belege: (a) **mechanisch, kein Judgment** — die Trigger sind `v_code != v_readme`, `cl_entries == 0`, `new_py >= 1`; (b) der Erzeuger-Heuristik-Fehler ist im Skill selbst dokumentiert („8h-Heuristik sammelt bei parallelen Sessions auch FREMDE Commits ein"); (c) **Liegezeit-Test gegen K3** (`Median ≤ 14 d`): `gh issue list --label docu-update --state all` → von 10 jüngsten sind **6 OPEN**, älteste offene seit **2026-08-02 (31 d)**, weitere seit 04./05./16.08. — Median-Liegezeit der offenen ≈ 28 d, also **doppelt über der K3-Schwelle**; (d) der **Verarbeiter existiert bereits als CI**: `.github/workflows/docu-update-agent.yml` (`on: issues: types:[labeled]`) — nur der **Erzeuger** klebt im Skill. **Vorschlag:** Erzeugung als wöchentlicher Cron analog `gen-project-facts.yml`, im Skill 3 Zeilen Zeiger. | 250 |
| `## Phase 1c Template-Drift-Check` (512) | 1 128 | **RUNNER-KANDIDAT** | Ein `scripts/drift_check.py`-Aufruf (existiert) mit `--severity=error`. Vollständig mechanisch; die Warnungen laufen laut Skill ohnehin „täglich per GitHub Action". | 150 |
| `## Phase 2 pgvector Memory` (542–596) | 3 316 | PFLICHT-KERN + LEHRE | Kern = die zwei `session-memory write`-Aufrufe + `entry_key`-Verifikation + die `--session-id`-**Regel**. Der A1-Blockquote (~1 100 B, Realfall `session:platform:20260719`) ist Beleg. | 1 200 |
| `### 3.1 Committen + Pushen` (601–679) | **4 953** | PFLICHT-KERN + LEHRE | Kern = kein `add -A`, Branch-Re-Check, Protection-aware Push, „nicht pushen wenn User es sagt" (~1 200 B). Der **`[skip ci]`-Komplex** (~2 400 B inkl. „Messung 2026-08-15, platform#1992", Diagnose-Falle, Reparatur) trägt genau **eine** Regel: *„`[skip ci]` nur ins Squash-Subject beim Mergen — nie in einen Commit des offenen PR-Branches, auch nicht zitiert; leerer Check-Rollup ist der Befund; Fix = `commit --amend` + Force-Push."* Das sind 3 Zeilen. | 1 400 |
| `### 3.1b Temporäre Dateien` (681) | 355 | PFLICHT-KERN (schlank) | Reihenfolge-Kopplung an 0e | 200 |
| `### 3.1c Worktree-Reaper` (689) | 1 149 | **STREICHKANDIDAT** | Gate `worktree-midsession-accumulation` (Registry) wurde am **2026-08-20 umgebaut**, Zitat `revision_note`: *„`repo-session.sh reap --alle` raeumt jedes Repo mit Lease, verdrahtet in session_start_checks.sh Phase 0.4.5"* — und der Runner hat die Phase (`record "0.4.5 auto-reap"`, Z. 195, Kommentar Z. 210: „Seit 2026-08-20 ueber ALLE Repos mit Lease, nicht nur `$TARGET_REPO`"). Die 15-zeilige Reaper-Schleife am Sitzungsende ist damit die **zweite** Ausführung derselben Mechanik; der nächste Start räumt ohnehin. | 250 (1 Satz + Verweis auf 0.4.5) |
| `### 3.2 Workflows verteilen` (710–772) | 3 698 | gemischt | Kern = `sync-workflows.sh`-Aufruf + „platform-main ist geschützt ⇒ Worktree+PR" (~700 B). **CHANGELOG-im-Code:** der 8-zeilige Kommentarblock „project-facts.md wird hier NICHT mehr lokal regeneriert … Zwei Erzeuger = SSoT-Verletzung" ist eine Änderungsbegründung. **Der zweite `// turbo`-Block (Version-After-Banner, ~1 200 B)** ist reine Kosmetik → Runner. | 700 |
| `### 3.3 Finale Prüfung` (774) | 462 | **RUNNER-KANDIDAT** | 8-zeilige dirty-Schleife | 200 |
| `### 3.4 Fallback bei Shell-Hang` (789) | 446 | **STREICHKANDIDAT / TOT** | Empfiehlt `mcp__github__push_files(branch: "main")`. Widerspricht der eigenen Datei drei Absätze vorher (3.1/3.2: `main` ist in platform + 10 Repos geschützt, Direkt-Push scheitert mit GH013 — ADR-242), und die Einschränkung „Funktioniert nur für **public Repos**" ist sachlich falsch (Token-Frage, nicht Sichtbarkeits-Frage). Ein Fallback, der auf dem Hauptpfad verboten ist, ist keiner. | 150 (nur: „Shell-Hang ⇒ Session neu starten, Read/Write/Edit + GitHub-MCP auf **Branch**, nie auf main") |
| `### 3.5 Clear-Freigabe` (801) | 1 339 | PFLICHT-KERN | Owner-Weisung 2026-08-30, Ausgabepflicht als letzter Satz. Kern = die zwei Zeilen-Varianten (~400 B). | 500 |
| `## Anti-Patterns` (824) | 1 262 | PFLICHT-KERN | Policy-Pflicht | 900 |
| `## Abschluss-Checkliste` (844) | 2 615 | PFLICHT-KERN | 21 Zeilen = das Ausführungstreue-Gate dieses Skills. Zellen 14/17/18/19/20 sind 2–3 Zeilen lang → Lean-Kürzung, kein Streichen. Der Pflicht-Selbstcheck-Blockquote (~700 B) wird zum Einzeiler. | 1 800 |
| `### MCP-Server Quick-Reference` (882) | 971 | **TOT** | Identische `mcpN_`-Tabellen wie in `session-start.md` (Dublette **und** Windsurf-Ära, s. §1) | 150 |
| `## Changelog` (907) | 4 673 | **CHANGELOG** | 8 Einträge | 600 |

---

## 3. Inventar `session-retro.md` (42 156 B → 22 000 B, inkl. 2 neuer Bahnen)

| Sektion (Zeile) | Bytes | Klasse | Beleg / Begründung | Ziel-B |
|---|---:|---|---|---:|
| Header + Zweck (6) | 810 | PFLICHT-KERN + **TOT** | „Wann / Wann NICHT" bleibt. Der Block „Deterministische Engine (optional): `~/shared/session-retro.workflow.js` via Workflow-Tool starten" ist eine **Phantom-Referenz**: `ls -l ~/shared/session-retro.workflow.js` → *Datei oder Verzeichnis nicht gefunden* (geprüft 2026-09-02). Derselbe Pfad wird im Changelog-Eintrag 2026-06-04 ein zweites Mal genannt. Genau die Klasse, die Phase 3 des Skills als REFUTED verlangt („Belegpflicht auch für Längsschnitt-Behauptungen — Verweis auf nicht-existente Memory"). | 500 |
| `## Eiserne Regeln — die 5 Fixes` (20) | 1 532 | PFLICHT-KERN | Methodenkern, nicht kürzbar unter ~1,2 KB | 1 200 |
| `## Phase 0 Right-Sizing` (40) | **4 935** | PFLICHT-KERN + LEHRE | Kern = Stufen-Tabelle, Klassentabelle kommandobelegt/Bewertungsbefund, die **gemessene** Zahl ~55k je Skeptiker, Trigger-Konflikt-Auflösung (a/b/c), Increment-Retro-Regeln (~2 400 B). Der Realfall `6bd412` (~900 B) und der Absatz „Richtung des Fehlers nicht vorhersagbar" (~600 B) sind Belege; die **Regel** daraus ist ein Halbsatz („Skeptiker-Auftrag neutral formulieren"). | 2 400 |
| `## Modell-Routing je Phase` (105) | 1 132 | PFLICHT-KERN | Tabelle + Anti-Pattern „billiger heißt Sonnet-Subagent, nicht kein Subagent" | 800 |
| `## Phase 1 Collect` (121) | 4 258 | PFLICHT-KERN + LEHRE | Kern = **fetch + aus dem Ref lesen**, Session-Grenze = Konversation, die 3 Sammel-Befehle, red_flags-Liste, Infra-Topologie-Sonde (~1 800 B). Die Instanz-Historie von `stale-local-clone-as-ground-truth` (7./8. Vorkommen, `d80d23`, `8d663b-incr`, ~1 200 B) und die `--since`-Messung (~600 B) sind Lehren; als Regel bleiben zwei Zeilen. | 1 800 |
| `## Phase 2 Find` (177) | 1 340 | PFLICHT-KERN | 3 Dimensionen + Finder-Mandat. Realfall `e17299-incr` (~400 B) → Lehren-Doku. | 900 |
| `## Phase 2.5 Finder-Konflikt` (196) | 972 | PFLICHT-KERN | 600 |
| `## Phase 3 Verify` (207) | 2 393 | PFLICHT-KERN + LEHRE | Kern = binär SURVIVES/REFUTED, Sortierregel, „Beleg unabhängig neu ziehen", Frisch-Checkout. Die 3.-Vorkommen-Historie (~700 B) ist Lehre. | 1 300 |
| `## Phase 3.5 Soll-Ablauf` (240) | 782 | PFLICHT-KERN | Invariante `|Soll| == |Survivors|` | 700 |
| `## Phase 4 Anchor` (253) | **8 258** | PFLICHT-KERN + LEHRE | Kern = das **YAML-Frontmatter-Schema** (maschinenrelevant: `tools/retro_kpis.py` und `tools/gate_wirkung.py` lesen es über 111 Reports in `docs/retros/`) + die 8 Report-Punkte + die 3 zulässigen Antworten auf einen Rückfall + die Klassen-Slug-Pflicht (~4 200 B). Zu verlagern: die Inline-YAML-Erklärung zu `gates_caught` (~700 B), `repo_scope`-Historie (~300 B), die 5a-Begründung „8 von 20 Gates rückfällig, 16× seit 2026-08-02" (~900 B), der 5b-Realfall (~400 B), die Report-Pfad-Herleitung (~600 B). | 4 200 |
| `## Phase 5 Self-Review` (360) | 2 747 | PFLICHT-KERN | Meta-Agent-Checkliste (6 Punkte) + `refuted_rate`-Bänder. Die zwei erklärenden Blockquotes zu `retro_kpis`/`gate_wirkung` (~900 B) sind Begründung. | 1 500 |
| `## Phase 6 Extern-Handoff` (393) | 1 077 | PFLICHT-KERN | nur `deep` | 800 |
| `## Anti-Patterns` (409) | 3 229 | PFLICHT-KERN | 25 Zeilen, aber mehrere tragen einen Erklärsatz + Realfall im selben Bullet (z.B. das Budget-Anti-Pattern mit „geschätzt ≪126k, real 115k") | 1 800 |
| `## Changelog` (435) | **8 380** | **CHANGELOG** | Größte Changelog-Sektion der drei Skills (20 % dieser Datei); 10 Einträge, ältester 2026-06-04. Vier davon (`v2.4`/`v2.5`/`v2.6` + Phase-1-Ausweitung) beschreiben **dieselbe** Regelverschärfung in vier Stufen. | 700 |
| **NEU: `## Phase 3b — Widerlegungsbahn`** | — | PFLICHT-KERN (neu) | K5 Teil 2, s. §5 | 900 |
| **NEU: `## Phase 7 — Streichbahn`** | — | PFLICHT-KERN (neu) | K5 Teil 2, s. §5 | 900 |
| **NEU: `## Abschluss-Checkliste`** | — | PFLICHT-KERN (neu) | **Eigener Befund:** `session-retro.md` hat als einziger der drei Skills **keine** Abschluss-Checkliste (`grep -n -i 'checklist\|Abschluss'` → nur Z. 363 „Checkliste:" innerhalb der Phase-5-Meta-Agent-Liste). Damit ist jede seiner 14 Phasen strukturell überspringbar — genau die Klasse, die 2026-07-15 (Retro c494a2) für `session-start.md` als höchstes Ausführungstreue-Risiko benannt wurde. Ohne diese Tabelle haben die zwei neuen Bahnen keine Checklistenzeile, wie K5 sie verlangt. | 900 |

---

## 4. Was wandert wohin — Zielbild

### 4.1 Ziel-Bytes

| Datei | heute | Plan | Delta |
|---|---:|---:|---:|
| `session-start.md` | 35 196 | **14 000** | −21 196 |
| `session-ende.md` | 52 152 | **20 000** | −32 152 |
| `session-retro.md` | 42 156 | **22 000** | −20 156 |
| **Summe** | **129 504** | **56 000** | **−73 504 (−57 %)** |

### 4.2 Neue Begleitdoku `docs/governance/session-skills-lehren.md`

Aufnahme aller LEHRE/BEGRÜNDUNG- und CHANGELOG-Sektionen, **eine Überschrift je
Ursprungsstelle**, damit der Skill mit einem Anker-Link zeigen kann
(`…/session-skills-lehren.md#0f-cross-repo`). Nichts wird gelöscht, alles bekommt eine
Adresse:

**Aus `session-start.md`:** Runner-Motiv (Phase-0-Präambel) · WARN-Klassenkunde 0.4 / 0.7 /
0.7.6 / 0.7.7 / 0.7.11 / 0.7.12 / 0.7.16 / 0.7.17 / 0.7.18 / **0.4.4** *(neu zu ergänzen,
heute nirgends erklärt)* · Troubleshooting-Lessons (ping/Hetzner, pgvector-sudo,
Stash-Semantik, ADR-156) · `--ziel`-Begründung 0.4.3 · Modell-Routing-Preisanekdote ·
Lesson 2026-06-24 (Phase 2.6) · Lesson 2026-07-15 + Pflicht-Selbstcheck-Herleitung
(Startklar-Checkliste) · Changelog v2 – v3 (10 Einträge).

> **Zweitadressat für die WARN-Klassenkunde:** die Deutung gehört fachlich **an die
> `record`-Zeile im Runner** (`tools/session_start_checks.sh`) bzw. in dessen Ausgabe —
> dann liest sie, wer die Zeile sieht, statt wer die Doku sucht. Die Begleitdoku ist der
> Zwischenschritt, nicht das Ziel.

**Aus `session-ende.md`:** Lesson 2026-06-22 (0a-deploy) · Lesson 2026-07-14
(0a-handover-pr) · Owner-Begründung Handover-PR-Merge (0a-merge) · KONZ-038-Warum
(0a-freshness) · KONZ-027-Arm-A-Messung (`merge=union` serverseitig wirkungslos) ·
illustration-hub-Realfall + `grep -ic`-Positivkontrolle (0e) · fünf `[deploy-health]`-Issues
+ vier Fehlalarme 2026-08-20 + 16-Rückfälle-Mechanik (0f) · Fettschrift-/Anker-Anekdote +
Präzisions-Messung 0,50 (0g) · A1-Realfall `session:platform:20260719` (Phase 2) ·
`[skip ci]`-Messung platform#1992 inkl. Diagnose-Falle (3.1) · Reaper-Historie (3.1c) ·
project-facts-SSoT-Begründung (3.2) · Pflicht-Selbstcheck-Herleitung (Checkliste) ·
Changelog (8 Einträge).

**Aus `session-retro.md`:** Realfall `6bd412` + Fehlerrichtung (Phase 0) ·
`stale-local-clone-as-ground-truth`-Instanzhistorie 3./7./8. Vorkommen + `--since`-Messung
(Phase 1/3) · Realfall `e17299-incr` (Phase 2) · Realfall pptx-hub-Finderkonflikt (2.5) ·
`gates_caught`-Begründung + `repo_scope`-Historie + 5a-Messung „8 von 20 Gates" +
5b-Realfall + Report-Pfad-Kollision 2026-06-04 (Phase 4) · Changelog (10 Einträge,
20 % der Datei).

### 4.3 Was in Runner/Tools wandert (nicht in Doku)

| Von | Nach | Beleg, dass das Ziel existiert / fehlt |
|---|---|---|
| start 0.R WARN-Deutung | `record`-Note im Runner + `docs/governance/session-start-warnklassen.md` | 38 `record`-Phasen vorhanden |
| ende −0.1, 0a-deploy, 0a-handover-pr, 1b-Erzeuger, 1c, 3.1c, 3.2-Banner, 3.3 | **neu: `tools/session_ende_checks.sh`** | existiert **nicht** (`ls tools/`) — ist der Vorschlag |
| ende 1b Issue-Erzeugung | Cron-Workflow analog `gen-project-facts.yml` | Verarbeiter existiert: `.github/workflows/docu-update-agent.yml` |

### 4.4 Streichkandidaten mit Beleg (K5 verlangt ≥ 1 — hier **5**)

| # | Kandidat | Beleg | Restersatz |
|---|---|---|---|
| S1 | `session-start` Phase 2.5 Auto-Issue-Template (1,7 KB) | Label `auto-detected`: 2 Issues gesamt, **1** aus dem Template (#82, 2026-04-30, seither 125 Tage kein zweites) | Auswertungstabelle bleibt (4 Zeilen) |
| S2 | `session-ende` Phase 1b Docu-Drift-Erzeuger (3,2 KB) | 6/10 Issues offen, älteste 31 d ⇒ Median-Liegezeit ≈ 28 d gegen K3-Schwelle 14 d; Verarbeiter läuft schon als CI | Cron + 3-Zeilen-Zeiger |
| S3 | `session-ende` 3.1c Worktree-Reaper-Schleife (1,1 KB) | Gate-Registry `worktree-midsession-accumulation` `revision_note` 2026-08-20 + Runner `record "0.4.5 auto-reap"` (alle Repos mit Lease) | 1 Satz + Verweis auf 0.4.5 |
| S4 | `session-ende` 3.4 Shell-Hang-Fallback (0,45 KB) | Empfiehlt Push auf `main`, das dieselbe Datei zweimal als geschützt beschreibt (ADR-242/GH013); „nur public Repos" sachlich falsch | 1 Zeile, Branch statt main |
| S5 | Beide `MCP-Server Quick-Reference`-Tabellen (2,1 KB) | `mcpN_`-Prefixe; Skill deklariert selbst `project-facts.md` als Quelle; Policy `claude-skills.md` Z. 10: Windsurf codet nicht mehr | 1 Zeile Zeiger je Skill |
| S6 | `session-retro` Header-Block „Deterministische Engine" + Changelog-Nennung (~0,4 KB) | `ls -l ~/shared/session-retro.workflow.js` → **nicht vorhanden** (2026-09-02). Der Skill verweist als Alternativ-Ausführungsweg auf eine Datei, die es nicht gibt — Phantom-Referenz, die der Skill in Phase 3 selbst als REFUTED-Klasse führt | ersatzlos, oder Datei wiederherstellen und Pfad belegen |
| — | (Dublette, kein Streich) `Platform Sync Loop` 2× | `grep -rl 'Platform Sync Loop' .windsurf/workflows/` → genau 2 Treffer: `session-start.md`, `session-ende.md`; wortgleich (start Z. 37 / ende Z. 17) | eine Kopie bleibt |

---

## 5. K5 Teil 2 — Widerlegungsbahn und Streichbahn in `session-retro.md`

### 5.1 Was heute schon abgedeckt ist (damit nichts doppelt entsteht)

| Vorhandene Stelle | deckt ab | deckt **nicht** ab |
|---|---|---|
| **Phase 3 Verify** | Falsifikation **einzelner Befunde**, binär, je Dimension, Skeptiker auf **Bewertungsbefunde**, Frisch-Checkout | die **Methode/Rangfolge/Right-Sizing-Entscheidung der Retro selbst**; ein Skeptiker prüft einen Befund, nicht das Urteil über die Sitzung |
| **Phase 5 Self-Review** | **Output-Qualität** des Reports gegen die Skill-Regeln (Schema, Invariante, `gate_wirkung`-Abfrage, `refuted_rate` **nur numerisch**) | ausdrücklich verboten ist ihm das inhaltliche Urteil über SURVIVES/REFUTED („das wäre Session-Urteil") — also genau die Widerlegung |
| **Phase 6 Extern-Handoff** | Advocatus Diabolus als **Methodenkritik**, aber: `optional, nur deep`, **kein** Repo-Zugriff, Mensch holt sie manuell ein | eine **feste**, in jedem `full`-Lauf laufende Widerlegung mit Artefakt-Zugriff |

⇒ Die Lücke ist real: zwischen „Befund widerlegen" (3) und „Report formal prüfen" (5) fehlt
**„das Urteil dieser Retro widerlegen"**, und dieser Auftrag existiert heute nur als
optionale, manuelle, evidenzlose Phase 6.

### 5.2 Vorschlag `## Phase 3b — Widerlegungsbahn (PFLICHT ab `full`)`

```
Ein Subagent, T4 (Opus), **frischer Kontext**, mit gh/git-Zugriff, EIN Auftrag:
"Widerlege das Urteil dieser Retro." Er sieht: Report-Entwurf + Footprint + die
Artefaktliste aus Phase 1 — NICHT die Session-Erzählung und NICHT die Finder-Prompts.

Drei Fragen, jede mit Artefakt-Beleg zu beantworten:
 1. Ist ein SURVIVES falsch stehen geblieben? (Gegenbeleg aus origin/<default-branch>)
 2. Ist ein REFUTED zu früh verworfen worden?
 3. Fehlt eine ganze Dimension? Nenne EINEN Befund, den keiner der Finder hatte.

Ergebnis geht als eigener Abschnitt "## Widerlegung" in den Report, mit Verdikt je
Punkt (BESTAETIGT / GEKIPPT / NEU) und Frontmatter-Feld `widerlegung: <n> gekippt,
<m> neu`. Ein Lauf ohne Fund schreibt die Abdeckungsauskunft (Eiserne Regel 5).
```

*Beleg für den Tier-Zuschnitt:* [#2374](https://github.com/achimdehnert/platform/issues/2374)
§„Offen: der Tier-Zuschnitt" führt `Advocatus Diabolus | T4, fremder Kontext | Richter ≠
Angeklagter` und optional T5. **Ehrlich einzuschränken:** die Sektion ist dort mit
„(war G3, **unbeantwortet**)" überschrieben — es ist ein Vorschlag im offenen Issue, keine
ratifizierte Entscheidung. Der Auftragstext von #2690 behandelt sie als entschieden; wer
den PR baut, sollte das einmal bestätigen lassen.

*Kostenanker (aus Phase 0, gemessen):* ~55k Token je eng geführtem Skeptiker; die
Widerlegungsbahn ist ein Agent obendrauf, also `full` ≤ 7 statt ≤ 6.

### 5.3 Vorschlag `## Phase 7 — Streichbahn (PFLICHT, jeder Footprint)`

```
Genau eine Frage, am Ende jeder Retro: "Welche Phase / welcher Melder / welche
Skill-Sektion gehört WEG?"

Zulässige Antworten — genau zwei, wie bei jedem Verzicht in diesem Loop:
 (a) >=1 Streichkandidat MIT Beleg. Beleg ist eines von vier Dingen:
     - kein Leser   : der Output landet in keinem Artefakt (gh-Suche zeigt 0 bzw. nur
                      Uralt-Treffer)  -> Muster wie start-Phase-2.5 (#82, 2026-04-30)
     - kein Effekt  : ein Tool/Gate erzwingt dieselbe Wirkung ohnehin (Registry-Eintrag
                      oder record-Zeile im Runner nennen)
     - Dublette     : dieselbe Aussage steht in einem anderen Skill/Doc (Fundstelle)
     - Liegezeit    : erzeugte Artefakte liegen im Median > 14 d ohne Entscheidung
                      (gate_deckung.py / befund_journal.py --bericht)
 (b) "keiner, weil <Satz>" — mit dem Grund, nicht nur dem Wort.

Ergebnis als Frontmatter-Feld `streichkandidaten: [<slug>, ...]` (leer erlaubt, dann
ist `streich_begruendung:` Pflicht) und als Zeile im Action-Board (Phase 4, Punkt 7).
Ein Streichkandidat, der zwei Retros hintereinander auftaucht und nicht gestrichen
wurde, ist selbst ein Befund -- dieselbe Ratsche wie GATE-PFLICHT bei >=2.
```

### 5.4 Neue `## Abschluss-Checkliste` für `session-retro.md`

Der Skill hat heute keine (Beleg §3). Vorschlag, 14 Zeilen, Lean-Zellen; die zwei neuen
Bahnen als Zeile 11/12:

| # | Check | Status |
|---|---|---|
| 1 | Footprint + Agenten-Budget festgelegt (Phase 0) | ☐ |
| 2 | `git fetch` **und** Lesen aus dem Ref (Phase 1) | ☐ |
| 3 | Session-Grenze über Branch/PR gezogen, nicht Datum | ☐ |
| 4 | Finder je Dimension, Finder-Mandat im Prompt | ☐ |
| 5 | Finder-Widersprüche als Skeptiker-Task (2.5) | ☐ |
| 6 | Verify binär, nur Bewertungsbefunde (Phase 3) | ☐ |
| 7 | `|Soll| == |Survivors|` (Phase 3.5) | ☐ |
| 8 | `retro_kpis.py` gelaufen (Phase 4 Pkt. 5) | ☐ |
| 9 | `gate_wirkung.py` gelaufen, Rückfall klassifiziert (5a) | ☐ |
| 10 | `over_ask`/`over_act` mit Klassen-Slugs (5b) | ☐ |
| 11 | **Widerlegungsbahn gelaufen, `widerlegung:` gesetzt (3b)** | ☐ |
| 12 | **Streichbahn: ≥1 Kandidat mit Beleg ODER „keiner, weil" (Phase 7)** | ☐ |
| 13 | Report-Pfad kollisionsfrei, Frontmatter vollständig | ☐ |
| 14 | §8 „Nicht verifiziert" gefüllt | ☐ |

---

## 6. Advocatus Diabolus — die drei stärksten Gründe, warum dieser Plan schiefgeht

**D1 — Die Lehre wirkt nur, wo sie steht: „ein Link ist kein Leser."**
Das ist kein Verdacht, sondern der am besten belegte Fehlermodus dieses Repos: der Slug
`melder-ohne-leser` und die fünf `[deploy-health]`-Issues (session-ende 0f) beschreiben
exakt „Information korrekt erzeugt, an einer Stelle abgelegt, die niemand aufsucht".
Eine Begleitdoku ist genau diese Stelle. Wer den Skill zur Laufzeit liest, klickt keinen
Anker. **Konkret gefährdet — die vier Lehren, die nur als Fließtext im Ausführungspfad
funktionieren, weil sie eine Handlung im selben Moment verbieten:**

| Lehre | wo heute | 1-Zeilen-Regel, die im Skill bleiben MUSS |
|---|---|---|
| `[skip ci]` im PR-Head-Commit blockiert alle Checks lautlos | ende 3.1, 2,4 KB | „`[skip ci]` **nur** ins Squash-Subject beim Mergen — nie in einen Commit eines offenen PR-Branches, auch nicht zitiert. Leerer Check-Rollup = Befund, Fix: `commit --amend` + Force-Push." |
| fetch bewegt den Ref, nicht den Tree | retro 1 + 3, ~1,9 KB | „Nach `git fetch`: **aus dem Ref lesen** (`git show origin/<b>:<pfad>`), nie die Working-Tree-Datei greppen." |
| `NICHT messbar` / `SAMMELPHASE` / `nicht-pruefbar` ist kein Grün | start 0.R, ende 0g | „Jede `◌`/`nicht messbar`/`SAMMELPHASE`-Zeile ist eine **Lücke**, kein Pass — als solche ins Board." |
| Melder-Befund braucht ein Urteil | ende 0f, ~700 B | „Jeder behandelte Befund bekommt `--echt` oder `--falsch` — ohne Urteil ist die Präzision des Melders unbekannt." |
Wandern diese vier ersatzlos in die Doku, spart der Plan ~5 KB und kauft dafür genau die
Rückfälle, gegen die die Sektionen geschrieben wurden. **Gegenmaßnahme:** jede verlagerte
Lehre hinterlässt **eine** imperative Zeile am Ort der Handlung; die Doku trägt nur das
*Warum*. Prüfbar machen: nach dem Umbau ein `grep` über die drei Skills auf die vier
Regel-Sätze — 4 Treffer oder der PR ist unvollständig.

**D2 — Der Changelog-Abbau verletzt eine geltende Policy, nicht nur eine Gewohnheit.**
`~/.claude/policies/claude-skills.md` §Pflicht-Review-Gate, Punkt 5: „**CHANGELOG-Eintrag in
der Skill-Datei**"; Punkt 3 verlangt zusätzlich „Anti-Patterns-Sektion **vollständig**".
Die 18 KB Changelog sind damit formal geschützt, und die Anti-Patterns-Sektionen (1,1 +
1,3 + 3,2 = 5,6 KB) dürfen nicht auf Zurufkürze zusammengestrichen werden. Ein PR, der
beides anfasst, ändert **Policy-gebundenes Verhalten** — nach Lotsen-Charta Art. 3
(selbstbetreffende Regeländerung) ist das ein Vorschlag an den Owner, kein autonomer Zug,
auch unter SA-4. **Gegenmaßnahme:** die Policy-Änderung („Changelog = letzte 3 Einträge +
Verweis auf die Begleitdoku; Historie in git") als **eigenen, ungebündelten** PR vorlegen
und erst danach die drei Skills kürzen. Bündelt man es, hängt die ganze Diät an einer
Freigabe, die man nicht eingeholt hat. Fällt die Freigabe aus, kostet das 18 KB — dann
liegt das Ziel bei 74 KB und **K5 ist ohne Policy-Änderung nicht erreichbar**. Das ist die
härteste Abhängigkeit des Plans.

**D3 — Der Ende-Runner existiert nicht; ohne ihn ist „verlagern" nur „löschen mit
Absichtserklärung".**
Rund 8 KB des ende-Plans setzen auf `tools/session_ende_checks.sh` — eine Datei, die es
nicht gibt (`ls tools/`). `session_start_checks.sh` hat heute 1 052 Zeilen und 38 Phasen;
der Ende-Runner wäre kein Nachmittag. Solange er fehlt, ist jede Zeile, die man aus
`session-ende.md` streicht, faktisch weg — und zwar in genau dem Skill, dessen
Abschluss-Checkliste 21 Zeilen hat und dessen Phasen 0a-freshness/0f/0g **gate-registriert**
sind (`handover-stale-vor-merge`, `gate-rueckfall-unbemerkt`, `zusage-ohne-verankerung`).
Ein Gate, dessen Verdrahtung („verdrahtet in session-ende Phase 0g") ins Leere zeigt, ist
laut `gate_wirkung.py`-Logik nicht „schlanker", sondern **rückfällig**. **Gegenmaßnahme:**
Reihenfolge umdrehen — erst der Runner mit Drill (K1) und einem echten Lauf, dann die
Kürzung im selben oder folgenden PR; und die drei gate-tragenden Phasen kommen **zuletzt**
dran, nachdem die Registry-`module`/`note`-Felder auf den neuen Ort zeigen.

**Ergänzend, schwächer, aber real (D4):** Der Byte-Deckel ist ein Proxy, kein Ziel. K1
verlangt, dass ein *frisches Modell* den Skill aus kaltem Kontext vollständig ausführt —
ein Skill, der zu 40 % aus Zeigern besteht, ist kürzer und für ein Modell ohne
Werkzeug-Zugriff auf die Zieldateien **schlechter**. Die Messung, die zählt, ist der
Kaltstart-Drill aus K1, nicht `wc -c`. Deshalb: **K5 erst nach K1 abnehmen**, mit denselben
3 Läufen je Skill vor und nach der Diät und 0 stillschweigend übersprungenen Pflichtphasen
in beiden Messungen.

---

## 7. Restlücken (nicht verifiziert)

- ~~`~/shared/session-retro.workflow.js`~~ — **geprüft, existiert nicht** → als S6 in die
  Streichliste aufgenommen.
- **Nicht verifiziert:** ob die `[docu-update]`-Issues nach dem CI-Agent-Lauf automatisch
  geschlossen werden (der Workflow kann `--dry-run`); gemessen ist nur der Zustand
  „6 von 10 offen". Billigster Check: `gh run list --workflow docu-update-agent.yml`.
- **Nicht verifiziert:** die exakte Ziel-Bytezahl je Sektion — sie ist eine Schätzung aus
  „welcher Anteil der Sektion ist Anweisung", nicht aus einem geschriebenen Entwurf. Der
  Plan ist gegen 56 KB kalibriert und hat 4 KB Puffer zur 60-KB-Marke.
- **Nicht verifiziert (Auftrags-Prämisse):** #2374 führt „Advocatus Diabolus | T4, fremder
  Kontext" unter einer als **unbeantwortet** markierten Überschrift; der Auftrag #2690
  behandelt es als entschieden.
- **Teilweise geprüft:** Dubletten über Skill-Grenzen. `Platform Sync Loop` steht in genau
  2 Dateien (start/ende). **Nicht geprüft:** ob `/knowledge-capture`, `/briefing`, `/next`
  weitere Textstellen duplizieren — billigster Check: `grep -rl 'MCP-Server
  Quick-Reference\|Abschluss-Checkliste' .windsurf/workflows/`.
