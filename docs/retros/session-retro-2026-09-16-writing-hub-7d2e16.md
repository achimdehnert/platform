---
retro_schema: 1
date: 2026-09-16
repo_scope: [writing-hub, platform]
session_id: 7d2e16
footprint: full
footprint_reduction_reason: "deep→full: (a) jeder Prod-Schritt mit Owner-Wort im Transkript (10:22 „ok go", 16:48 „5 go", Titelbilder vom Owner selbst gefahren), (b) pg_dump vor jedem Lauf, 0 Migrationen, (c) findings_total 18 ≤ Schätzung"
findings_total: 21
findings_survived: 15
refuted_rate: 0.29
phase3_refuted: 4   # 3 Skeptiker (#6, #14, #15) + 1 Widerlegungsbahn (#18)
pre_refuted: 2
scores:
  zielerreichung: 3
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 2
  entscheidungsqualitaet: 3
gate_candidates: [self-review-presented-as-review, prod-as-test-environment, test-asserts-the-case-in-mind-not-the-harmful-one, gate-claim-before-cheapest-check-nachschaerfen-absenz]
recurring_findings: [prod-as-test-environment, same-file-serial-prs, self-review-presented-as-review, test-asserts-the-case-in-mind-not-the-harmful-one, gate-modul-prueft-weniger-als-sein-name, untested-command-handed-to-user, claim-before-cheapest-check, absence-claim-needs-second-search-path, lint-failure-no-local-gate, action-board-link-missing, spend-estimate-without-sample-run, catalog-hit-treated-as-license, two-sources-for-one-physical-value]
gates_caught: [untested-command-handed-to-user, claim-before-cheapest-check]
over_ask_klassen: []
over_act_klassen: [prod-schreiblauf-ueberschreitet-erteilte-freigabe]
widerlegung: "1 gekippt, 3 neu"
streichkandidaten: []
streich_begruendung: "keiner, weil jede Phase dieser Retro das Urteil verändert hat (Skeptiker 3 von 4 gekippt, Widerlegungsbahn 1 gekippt + 3 neu, Kennzahlen-Skript 2 Befunde); der einzige ertragsarme Teil, over_ask (14 von 17 Retros leer), hat mit retro_kpis.py --nominierung einen Leser und ist der einzige Sensor für KONZ-025 Art. 2.1a"
---

# Session-Retro 2026-09-16 · writing-hub · 7d2e16

Sitzung: Kapitäns-Session in `achimdehnert/writing-hub`, Auftrag Issue #1181 (K1–K7): klickbare Leseliste je Termin, Bücher je Termin, Termine 2–5 anhand der Bücher überarbeiten → Modulversion v12 auf Prod. Scope = 22 gemergte PRs #1182–#1207 (Branch-Präfix `session/2026-09-16/achim-dehnert/*`), Issues #1181/#1190/#1191/#1199/#1203, platform#3208/#3209, vier Prod-Schreibläufe per Owner-Skript.

**Footprint `full`** (reduziert von `deep`, Gründe im Frontmatter): ein Code-Repo plus zwei Issues in platform, 22 PRs, Prod-Schreibläufe ohne Migration. Agenten: 3 Finder (sonnet), 3 Skeptiker (sonnet) für 4 Bewertungsbefunde + 1 over_act-Klasse, Widerlegungsbahn (opus), Meta (sonnet) = 8; Phase 1 inline. Transkript-Kennzahlen per `tools/retro_transkript_kennzahlen.py` (Ausgabe neben diesem Report: `session-retro-2026-09-16-writing-hub-7d2e16.kennzahlen.txt`, eine IP geschwärzt): 577 Bash-Aufrufe, 6 Workflows, 1 Ablehnung, 18 Fehlerläufe, 9 Silent-Reminder, Kontext-Kompaktierung 16:01.

**Phase 0.0:** `tools/gate_wirkung.py` → „Kein Gate rueckfaellig"; über alle 126 Retros haben 4 Gates ihren Befund gefangen, 13 Gates sind `zu-frueh`. In dieser Sitzung selbst fingen zwei Gates (`gates_caught`).

## 1. Executive Summary

- Ziel weitgehend erreicht: Leseliste, Bücher, v12 mit 91 Vorschlägen, 50 Praxisbeispielen, Reifegrad-Index, 14 Titelbildern und Kurzbeleg-Layout sind auf Prod. K7 (Moodle) ist nach Owner-Entscheid vertagt (#1178), #1181 bleibt offen.
- Der schwerste Befund ist ein Prod-Vorfall: der Schreiblauf für das E5.4-Bild („122 go") setzte die Owner-Editor-Revisionen an E3 zurück, weil das Skript jede abweichende Einheit schrieb. Freigabe und Schreib-Footprint deckten sich nicht (#1, over_act). Drei Reaktiv-Patches am selben Skript folgten.
- K4 „jede Seitenangabe gegengeprüft" wurde bei 44 von 51 Vorschlägen von den erzeugenden Agenten selbst geprüft (#2); die Aufwandsschätzung dafür lag um Faktor 6 daneben (#3).
- Zwei Werkzeugfehler betrafen Belege: ein Seitenparser verlor Angaben nach Komma (#7), die Kurzbeleg-Regex verarbeitet Doppel-„S." falsch (#9, am Korpus gefunden: Gröndahl, E9).
- Der Seitenzahl-Test für Decks misst Seminarmodule, nicht die v12-Einheiten — deshalb fiel E5.4 erst dem Owner auf (#17, aus der Falsifikation).
- Die Widerlegungsbahn kippte einen Befund (#18, S1 ist in #1203 dokumentiert gelöst) und fand drei neue: „nicht prüfbar" behauptet, ohne die Titelbilder per OCR anzusehen — der Owner musste seinen Befund wiederholen (#19); Board ohne Link (#20); PR #1182 mit rotem Lint-Check zur Freigabe vorgelegt (#21).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Prod-Schreiblauf setzte Owner-Editor-Revisionen E3 Rev 3–5 zurück; Skript `prod-zug-v12.sh` bekam drei Reaktiv-Patches (#1193 Schreibmodus ungetestet, #1196 Gedächtnis, #1202 Gegenprobe-Fehlalarm E1) | fehlende Validierung | kritisch | SURVIVES | #1181-Kommentar 11:36:45Z „Der Lauf für das Bild in E5.4 (Owner-Go „122 go") hat E3 als Revision 6 zurückgesetzt"; Skriptstand `8e97028` schrieb jede abweichende Einheit; PR-Body #1193 „meine Tests prüften das Gerüst nur trocken" | `prod-as-test-environment` ×4→5, `same-file-serial-prs` ×14→15 |
| 2 | K4 „jede Seitenangabe am Chunk gegengeprüft": bei 44 von 51 Vorschlägen prüften nur die erzeugenden Agenten sich selbst, unabhängig 7 | fehlende Validierung | hoch | SURVIVES | PR #1187 Body „Lücke: … 44 von 51 … nur von den Agenten selbst geprüft"; #1181-Kommentar 08:17:36Z. 3b-Einschränkung: PR #1189 (08:52) prüfte danach je Vorschlag (31 hält / 19 teilweise / 1 nicht) — Severity beschreibt den Stand um 08:32, die Unabhängigkeit der #1189-Prüfer ist ungeprüft (§8) | `self-review-presented-as-review` ×1→2 ⇒ GATE-PFLICHT |
| 3 | Aufwandsschätzung K4 um Faktor 6 daneben (0,6 Mio. geschätzt, 3,53 Mio. Tokens real; 12 Sonnet-Leser + 4 Opus-Synthesen) — Spend ist Freigabe-Gate | Wissenslücke | hoch | SURVIVES | #1181-Kommentar 08:40 „Verbrauch: 3,53 Mio. Tokens … geschätzt … 0,6 Mio." | neu: `spend-estimate-without-sample-run` |
| 4 | Grundlage für K1/K2 (`lizenzpruefung-leseliste.md`, „16 belegt verfügbar") war fehlerhaft: Odoi und Peukert nicht lizenziert | Wissenslücke | mittel | SURVIVES | #1181-Kommentar 07:30 „Odoi und Peukert sind nicht lizenziert (Schäffer-Poeschel …)"; platform#3208 | neu: `catalog-hit-treated-as-license` (Memory `lizenz-katalogtreffer-ist-keine-lizenz` ×2 Vorfälle) |
| 5 | K7 „Moodle-fertig" offen, #1181 OPEN — sei nicht in Tracking mit Termin überführt | Prozesslücke | mittel | pre_refuted | Artefaktliste: #1178 offen, Owner-Entscheid „wenn alles aktuell ist"; Tracking existiert | — |
| 6 | #1183/#1185/#1194 seien fremde Nebenaufträge ohne Kennzeichnung | Prozesslücke | mittel | REFUTED | Skeptiker: AGENT_HANDOVER.md Prio Z.5/6 nennt #1176/#1160; Branch-Namen tragen die Issue-Nummer; #1190 ist in #1181 Kommentar 10:33 als K5-Folge verankert | — |
| 7 | Seitenparser verlor Angaben nach Komma („PDF 47, 49"), 3 Skripte betroffen, Urteile über mehrere der 51 Vorschläge verzerrt | fehlende Validierung | hoch | SURVIVES | PR #1189 Body „Eigener Fehler, an den Urteilen gefunden"; `seiten.py` neu, 6 nachgeprüft | `test-asserts-the-case-in-mind-not-the-harmful-one` ×7→8 |
| 8 | `folienmass.py` kodiert Folienmaße von Hand aus dem CSS in `deck_pdf.html` ab — zwei Quellen für eine physische Größe, kein bindender Test | verfrühte Festlegung | mittel | SURVIVES | `apps/lectures/folienmass.py` Z.14–20 vs. `templates/lectures/deck_pdf.html` `.slide`/`.inhalt.bild-rechts` (origin/main); kein Test bindet beide | neu: `two-sources-for-one-physical-value` (Policy SSoT vor Individuallösung) |
| 9 | Kurzbeleg-Regex `_SEITE` nur gegen zwei Handbeispiele getestet; am v12-Korpus 1 Fehlklassifikation: Gröndahl (E9) trägt zwei „S."-Angaben → Kurzbeleg „S. 50, 150", Literaturliste behält „S. XI, 149–150." | fehlende Validierung | mittel | SURVIVES | Skeptiker-Korpuslauf: 129 Quellen, 116 mit Seite, 111 korrekt, 4 korrekt ausgeschlossen, 1 falsch (`v12/einheiten/E9.json` Abschnitt 0); `tests/test_deck_kurzbeleg_und_literatur.py` nur VIAL/HARWARDT | `test-asserts-the-case-in-mind-not-the-harmful-one` |
| 10 | Stop-Hook `untested-command-handed-to-user` griff 10:09:27 — Befehl vor eigener Ausführungsprüfung übergeben | Prozesslücke | niedrig | SURVIVES | `kennzahlen.json` Z.55 | `untested-command-handed-to-user` — **gates_caught** |
| 11 | Stop-Hook `claim-before-cheapest-check` löste 6× aus (08:14, 10:08, 10:09, 12:40, 14:01, 15:47) | Prozesslücke | mittel | SURVIVES | `kennzahlen.json` Nutzer-Nachrichten, 6 Stop-Hook-Zeilen | `claim-before-cheapest-check` — **gates_caught** |
| 12 | Direkter `scp` nach `hetzner-prod` 04:33:57, von der Permission-Schicht abgelehnt — außerhalb des Owner-Skript-Wegs (#994) | Prozesslücke | niedrig | SURVIVES | `kennzahlen.json` Z.4 Ablehnung „Production Reads" | — |
| 13 | Titelbilder-Skript brach beim ersten Schreiblauf 15:33 ab (`docker cp` legt root-Dateien ab) → #1205 | fehlende Validierung | mittel | SURVIVES | PR-Body #1205 „Der erste Schreiblauf (15:33) brach ab … `docker cp` legt Dateien als root ab"; Owner-Lauf-Protokoll „ABBRUCH: Schritt 2 endete mit Code 1" | `prod-as-test-environment`; Memory `drift-docker-cp-in-vorhandenes-verzeichnis` (zweite docker-cp-Lehre) |
| 14 | Deck-Renderer habe vier separate Owner-Korrekturrunden ohne generischen Vorab-Test bekommen | fehlende Validierung | mittel | REFUTED | Skeptiker: 12:59 war der E3-Entscheid, die #1201-Runde ist 14:01:44Z (drei behoben + einer offen, eine Runde); der Seitenzahl-Test existierte vor #1206 (`git log -S "len(dokument.pages)"`) — ersetzt durch #17 | — |
| 15 | #1199 (KI-Hilfe erfindet Beispiele) hätte vor der nächsten Formularnutzung gefixt werden müssen | Wissenslücke | mittel | REFUTED | Skeptiker: #1197 andere Funktion, #1198/#1200 docs-only aus Kapitelkarten; keine weitere Nutzung der KI-Hilfe zwischen Fund und Issue; Checkliste in #1199 | — |
| 16 | #1197-Merge per 40× `sleep 5`-Polling auf `gh pr checks` | Werkzeug | niedrig | pre_refuted | `kennzahlen.json` 12:02:14 — Polling auf CI ist Standardweg, kein Defekt | — |
| 17 | Seitenzahl-Test `test_should_alle_decks_als_pdf_mit_erwarteter_seitenzahl_rendern` misst `_seminar_dossiers()` (statische Module), nicht die v12-Einheiten — E5.4 lief zwei Seiten, bis der Owner es sah | fehlende Validierung | mittel | SURVIVES (aus Phase 3, NEU) | Skeptiker: `tests/test_lectures_quellen_orientierung.py` (origin/main) iteriert `_seminar_dossiers()`; v12 liegt in `docs/lehre/dai-strategy/buchanalyse/v12/einheiten/E*.json`; Owner-Befund 163 (15:53) | `gate-modul-prueft-weniger-als-sein-name` ×2→3 |
| 18 | Offener Punkt „S1-Bild mit Rechtschreibfehlern" im #1181-Thread ohne dokumentierte Auflösung | Prozesslücke | niedrig | REFUTED (3b) | Widerlegungsbahn: #1203 Body „Seite 1: „Schrift ist inkorrekt" — das Titelbild von v12 E3 trägt die Zeilen „Danete Kubikmaiter …"", Schlusskommentar 15:46:54Z „Erledigt", #1181-Kommentar 15:46:56Z „(#1203 geschlossen, PR #1204/#1205)"; der Skeptiker hatte #1203 nicht gelesen | — |
| 19 | „Vermutlich eine der fünf Buchabbildungen … (Rasterbilder, nicht prüfbar)" behauptet, ohne die 14 KI-Titelbilder per OCR anzusehen; der Owner musste seinen Befund um 14:32 wiederholen, erst dann lief tesseract (14:33) und #1203 fand 3 unbrauchbare | fehlende Validierung | mittel | SURVIVES (3b NEU) | PR #1201 Body 13:31:56Z „alle 261 Wörter der 23 gezeichneten Diagramme geprüft … Rasterbilder, nicht prüfbar"; `kennzahlen.json` 12:59 (Befund), 14:32:10 (Wiederholung), 14:33:50 (tesseract); #1203 Body 14:36 „alle 14 Titelbilder per Texterkennung geprüft" | `absence-claim-needs-second-search-path` ×1→2 ⇒ GATE-PFLICHT; `claim-before-cheapest-check` (Rückfall, §5a) |
| 20 | Action Board ohne klickbaren Link, Owner-Korrektur „154 es fehlt der link !" | Kommunikation | niedrig | SURVIVES (3b NEU) | `kennzahlen.json` 14:51:49, 15:00:45 „154 stil passt"; Memory `feedback-action-board-numbered-links` existiert (grep MEMORY.md) | neu in Retros: `action-board-link-missing` (Memory-Wiederholung) |
| 21 | PR #1182 dem Owner mit rotem Check zur Freigabe vorgelegt: Run 35066518527 `failure` 07:02:17Z (ci / Lint & Format: Ruff format check), Owner 07:13 „51 go checks failing", grün erst 07:16 | Prozesslücke | niedrig | SURVIVES (3b NEU) | `gh run list` Zeitfenster 06:40–07:20; `kennzahlen.json` 07:13:45 | `lint-failure-no-local-gate` ×12→13 (Gate `zu-frueh`, revidiert 2026-09-16 — ob vor oder nach 07:02, §8) |

Befunde 1–5, 7–13, 16–18 sind kommandobelegt (ohne Skeptiker); 6, 9, 14, 15 und die over_act-Klasse waren Bewertungsbefunde und liefen durch drei Skeptiker (1 SURVIVES präzisiert, 3 REFUTED, over_act SURVIVES). Befund 1 bündelt vier gleichlautende Finder-Zeilen (F2/E1/P1/P2). Die Widerlegungsbahn (§ Widerlegung) kippte #18 und ergänzte #19–#21; #14 und #17 sind ein Paar (der Skeptiker zu #14 fand #17).

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| zielerreichung | 3 | K1–K6 auf Prod belegt (#1181-Kommentare), K7 vertagt (#5), E3-Rückschlag kostete Owner-Arbeit (#1) |
| architektur_design | 3 | Platzrechnung als zweite Zahlenquelle (#8); Skript-Design ohne Editor-Fall (#1) |
| code_konventionstreue | 4 | `make test-pg`, `test_should_*`, Owner-Skript-Pfad — mit einem scp-Ausreißer (#12) |
| risiko_debt | 2 | Prod-Vorfall mit Owner-Datenverlust-Risiko (#1, over_act), Regex-Fehlklassifikation live (#9), Owner musste Befund wiederholen (#19) |
| prozess_effizienz | 2 | drei Reaktiv-Patches an einem Skript (#1), Titelbilder-Abbruch (#13), 6× Evidenz-Hook (#11) |
| entscheidungsqualitaet | 3 | Spend-Schätzung ×6 (#3), Selbstprüfung als K4-Erfüllung (#2); tragfähig: Owner-Entscheide (E3 b, Titelbilder ohne Text) eingeholt |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Freigabe „122 go" galt E5.4, das Skript schrieb jede abweichende Einheit; Schreibmodus nur trocken getestet | Prod-Schreibskript nimmt die Einheit als Argument und verweigert jede andere; vor dem ersten Live-Lauf beide Zweige (trocken/schreiben) mit Attrappe, dazu der Fall „Editor-Revision seit letztem Lauf" | #1 |
| K4-Belege von denselben Agenten geprüft, die sie erzeugten | Beleg-Prüfung als eigene Workflow-Stufe mit frischem Sonnet-Kontext, der nur Zitat+Seite sieht — Stichprobe ≠ Vollprüfung ausweisen | #2 |
| 0,6 Mio. geschätzt, 3,53 Mio. verbraucht | Vor einem Fan-out ≥8 Agenten einen Einzelagenten messen und hochrechnen; Schätzung ins Freigabe-Board mit Messbasis | #3 |
| Lizenzliste vom 10.09. als Auftragsgrundlage übernommen | Vor Weiterverwendung einer Lizenzliste den Volltext-Check je Titel neu fahren (Skill hnu-recherche §5), nicht die Liste lesen | #4 |
| Parser gegen „PDF 47" gebaut, „PDF 47, 49" fiel weg | Parser-Tests aus einer Korpus-Stichprobe ableiten (alle Formate, die `grep -o "PDF [0-9, –-]*"` liefert), bevor Urteile laufen | #7 |
| Folienmaße im CSS und in Python getrennt gepflegt | Maße einmal in Python definieren und ins Template rendern (CSS-Variablen aus dem Kontext) oder ein Test, der beide Werte gegeneinander liest | #8 |
| Regex mit zwei Handbeispielen getestet, Doppel-„S." im Korpus unerkannt | Test über den ganzen v12-Korpus: jede Quelle mit „S." liefert genau eine Belegseite, Literaturliste ohne „S." | #9 |
| Befehl vor eigener Probe übergeben | Übergabe-Datei erst schreiben, nachdem sie einmal gelaufen ist (Gate hat gefangen — beibehalten) | #10 |
| Sechs Behauptungen vor dem billigsten Check | Vor jeder Erfolgs-Zeile den Check-Befehl in derselben Nachricht zeigen (Gate hat gefangen — beibehalten) | #11 |
| `scp` direkt nach Prod | Prod-Reads über die Skripte in `~/shared/writing/prod-lesen/`, Vorlage kopieren statt Direktzugriff | #12 |
| `docker cp` als root, Folgelauf scheitert | Prod-Skripte, die Dateien in den Container legen, mit frischem Verzeichnis je Lauf entwerfen; Attrappentest mit echtem `docker cp` | #13 |
| Seitenzahl-Test läuft über Seminarmodule, v12 liegt in JSON | Test iteriert zusätzlich `v12/einheiten/E*.json` (oder die Prod-Dossiers per Export), damit der Deck-Test den Inhalt misst, der gerendert wird | #17 |
| „Rasterbilder, nicht prüfbar" geschrieben, ohne OCR zu versuchen; Suchraum waren die SVG-Diagramme, nicht die Titelbilder, die der Owner meinte | Bei einer Bild-Beanstandung zuerst die Bildklasse am genannten Ort bestimmen (Folie 1 = Titelbild), dann OCR laufen lassen; „nicht prüfbar" nur mit dem gescheiterten Versuch daneben | #19 |
| Board-Zeile ohne Link, Owner fragte nach | Pre-Send-Check Regel 4: jede Item-Zeile endet auf eine URL | #20 |
| PR mit rotem Lint-Check dem Owner vorgelegt | Vor jeder Freigabe-Bitte `gh pr checks` lesen; lokal `ruff format --check` vor dem Push (Gate `lint-failure-no-local-gate`) | #21 |

Invariante: 15 Soll-Schritte = 15 überlebende Befunde.

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (Stand origin/main platform, vor dieser Retro):

- `prod-as-test-environment`: ×4 → ×5 (#1, #13). Kein Gate registriert ⇒ **GATE-PFLICHT**, `gate_candidates`. Vorschlag: `prod-zug-*.sh`-Skripte bekommen einen Pflicht-Attrappenlauf beider Modi (`--trocken` und Schreiben gegen eine lokale Prod-Kopie) als CI-Test, bevor sie in `docs/guides/` landen.
- `same-file-serial-prs`: ×14 → ×15 (#1: #1188/#1192/#1193/#1196/#1202). Gate `serielle-prs-auf-derselben-datei` existiert (advisory, `zu-frueh`, 0 vor / 0 nach) — dieses Vorkommen ist das erste nach dem Bau; nicht rückfällig, aber der erste Messpunkt.
- `self-review-presented-as-review`: ×1 → ×2 (#2) ⇒ **GATE-PFLICHT**, `gate_candidates`. Vorschlag: Workflow-Vorlage „Beleg-Prüfung" mit frischem Kontext als Pflichtstufe in `docs/guides/` der Buchanalyse.
- `test-asserts-the-case-in-mind-not-the-harmful-one`: ×7 → ×9 (#7, #9). Kein Gate registriert; GATE-PFLICHT besteht seit ×2. Diese Retro liefert den Korpus-Test als konkreten Drill (Soll #9).
- `gate-modul-prueft-weniger-als-sein-name`: ×2 → ×3 (#17). Gate existiert (advisory, „beobachten", 1 vor / 1 nach) — mit diesem Vorkommen 2 nach dem Bau ⇒ Rückfall, §5a.
- `absence-claim-needs-second-search-path`: ×1 (fdd368) → ×2 (#19) ⇒ **GATE-PFLICHT**. Kein eigenes Gate; die Familie gehört zu `claim-before-cheapest-check` — deshalb dort umbauen (§5a), kein zweites Gate.
- `lint-failure-no-local-gate`: ×12 → ×13 (#21). Gate existiert (blocking, revidiert 2026-09-16~, `zu-frueh`); ob der Run 07:02 vor oder nach der Revision lag, ist offen (§8) — bis dahin kein Rückfall-Eintrag.
- `action-board-link-missing`: neu als Retro-Slug (#20), aber Wiederholung der Memory `feedback-action-board-numbered-links` — CLAUDE.md-Regel 4/9 existiert, ein Gate nicht; Pre-Send-Check bleibt die Maßnahme.
- `untested-command-handed-to-user` und `claim-before-cheapest-check`: Stop-Hooks haben gefeuert, danach wurde korrigiert ⇒ `gates_caught`, kein Rückfall.
- Neu: `spend-estimate-without-sample-run` (#3), `catalog-hit-treated-as-license` (#4), `two-sources-for-one-physical-value` (#8) — je ×1.

Abgleich MEMORY.md (`grep`): `lizenz-katalogtreffer-ist-keine-lizenz.md` und `drift-docker-cp-in-vorhandenes-verzeichnis.md` existieren (Vorläufer zu #4 und #13); `drift-skript-ueberschreibt-editor-aenderung.md` und `drift-weasyprint-schrumpft-bild-nicht-auf-restplatz.md` wurden in dieser Sitzung angelegt (#1, #17-Umfeld).

### 5a. Rückfall-Prüfung

`tools/gate_wirkung.py` vor dieser Retro: kein Gate rückfällig. Mit diesem Report:

| Gate | Rückfälle seit Bau | Ursache (Ausgang/Quelle) | Konsequenz |
|---|---|---|---|
| `claim-before-cheapest-check` | 1 (diese Retro, #19: Hook feuerte 14:01:55, Text blieb, Owner wiederholte 14:32) | **Quelle:** der Scanner erkennt Erfolgs-Behauptungen, nicht die Absenz-Form „nicht prüfbar / nicht möglich" ohne gescheiterten Versuch daneben | **umbauen** (Scanner-Pfad sieht den Fall nicht): Muster „nicht prüfbar / nicht möglich / lässt sich nicht" ohne folgendes Check-Kommando in den Scanner; Drill = PR #1201-Body als Negativfall. Eintrag bekommt `revised` + `revision_note` + `positivkontrolle` (Owner-Zug M9) |
| `gate-modul-prueft-weniger-als-sein-name` | 2 (2026-09-03; diese Retro #17) | **Quelle:** das Gate prüft Tool-Module in platform (`tools/`), nicht Testfunktionen in Anwendungs-Repos, deren Name „alle Decks" verspricht und deren Korpus enger ist | **ausweiten**: Positivkontrolle „Test-Name nennt Menge, Iteration deckt sie" auf `tests/` der Repos; Eintrag bekommt `revised` + `revision_note` — Umsetzung als Owner-Zug im Board (§7), weil der Edit durch `gate_verankerung_check.py --neu` laufen muss |

`serielle-prs-auf-derselben-datei` (erstes Vorkommen nach Bau) und `issue-offen-nach-gemergtem-fix` (Messpunkt ausstehend) bleiben in Beobachtung.

### 5b. Autonomie-Kalibrierung

- `over_ask`: 0 — alle Owner-„go" lagen auf Gates (Prod-Schreiblauf, Merge→Deploy, Spend für den Workflow, Owner-Entscheid E3).
- `over_act`: 1, Klasse **`prod-schreiblauf-ueberschreitet-erteilte-freigabe`** (#1): Freigabe wörtlich auf E5.4 begrenzt, Skript schrieb jede abweichende Einheit; das Verhalten war seit 09:57 bekannt. Selbst offengelegt, Revisionen in der Historie, aber der Schreib-Footprint war größer als das Wort. `retro_kpis.py --nominierung`: Klasse ×1 — keine Nominierung; ein zweites Vorkommen sperrt sie (Art. 2.2).

## 6. Verankerung

**memory_candidates** (kopierfertig, der Owner entscheidet — die Sitzung hat `drift-skript-ueberschreibt-editor-aenderung.md` bereits angelegt; die folgenden sind neu):

```markdown
---
name: feedback-prod-schreiblauf-nur-die-freigegebene-einheit
description: Ein Prod-Schreiblauf schreibt genau die Einheit, für die das „go" galt — ein Ganz-Dossier-Skript ist keine Freigabe für alle Einheiten
metadata:
  type: feedback
drift: true
drift_episode: 2026-09-16-122-go-schrieb-e3
---
„122 go" galt dem E5.4-Bild; `prod-zug-v12.sh` (Stand 8e97028) schrieb jede Einheit, deren Prod-Stand von der Eingabe abwich, und setzte E3 Rev 3–5 des Owners zurück (#1181, 11:36).
**Why:** Das Skript kannte nur „Eingabe ≠ Prod", nicht „Freigabe gilt für X".
**How to apply:** Schreibskripte nehmen die Einheit als Argument; ohne Argument nur `--trocken`. Vor jedem Lauf `v12-zuletzt.json` gegen die Prod-Revisionen lesen (#1196/#1202). Siehe [[drift-skript-ueberschreibt-editor-aenderung]].
```

```markdown
---
name: feedback-belegpruefung-nie-durch-den-erzeuger
description: „Jede Seitenangabe gegengeprüft" heißt frischer Kontext, der nur Zitat und Seite sieht — 44 von 51 Belegen waren Selbstprüfung
metadata:
  type: feedback
---
K4 in #1181 verlangte die Gegenprüfung ausdrücklich (Falle aus #1163); PR #1187 wies selbst aus, dass 44 von 51 nur vom Erzeuger geprüft waren.
**Why:** Derselbe Agent, der die Aussage schrieb, findet seine Seite wieder — das ist keine Prüfung.
**How to apply:** Workflow-Stufe „Beleg-Prüfung" mit eigenem Sonnet-Kontext je Beleg (Eingabe: Zitat, Seite, Chunk-Text; Ausgabe: steht/steht nicht), Stichprobe als Stichprobe benennen. Spend vorher an einem Agenten messen (Faktor 6 daneben am 16.09.).
```

```markdown
---
name: drift-deck-test-misst-seminarmodule-nicht-v12
description: Der Seitenzahl-Test für Decks iteriert `_seminar_dossiers()` (statische Module); der Prod-Inhalt v12 liegt in v12/einheiten/E*.json und wurde nie gemessen — E5.4 lief zwei Seiten
metadata:
  type: project
drift: true
drift_episode: 2026-09-16-e54-zwei-seiten
---
`tests/test_lectures_quellen_orientierung.py::test_should_alle_decks_als_pdf_mit_erwarteter_seitenzahl_rendern` versprach „alle Decks", maß aber nur die Module unter `apps/lectures/inhalte/`.
**Why:** Der Test entstand vor v12; die JSON-Einheiten kamen als zweiter Korpus dazu, ohne den Test nachzuziehen.
**How to apply:** Wer einen zweiten Inhaltskorpus einführt, hängt ihn an jeden Test, dessen Name eine Menge nennt. Regex-/Parser-Tests aus dem Korpus ableiten (Gröndahl E9: zwei „S."-Angaben, [[drift-weasyprint-schrumpft-bild-nicht-auf-restplatz]]).
```

**adr_candidates:** keine — die Befunde sind Prozess- und Testlücken innerhalb bestehender Architekturentscheidungen (#994 Owner-Skript-Pfad, #952 Route A); `adr-threshold.md` greift nicht.

## 7. Maßnahmen

Stand:
- **[M1]** ✅ Skript-Gedächtnis + Gegenprobe · writing-hub · #1 Erstmaßnahmen gemergt — https://github.com/achimdehnert/writing-hub/pull/1196
- **[M2]** ✅ Seitenparser + Nachprüfung · writing-hub · #7 behoben — https://github.com/achimdehnert/writing-hub/pull/1189
- **[M3]** ✅ Lizenzprüfer-Regex gemeldet · platform · #4 getrackt — https://github.com/achimdehnert/platform/issues/3208

Zug:
- **[M4]** 🔵 Kurzbeleg-Regex: Doppel-„S." (Gröndahl E9) + Korpus-Test · writing-hub · ich, Issue anlegen und fixen — https://github.com/achimdehnert/writing-hub/issues/1181
- **[M5]** 🔵 Deck-Seitenzahl-Test auch über v12/einheiten · writing-hub · ich, Issue + PR — https://github.com/achimdehnert/writing-hub/issues/1181
- **[M6]** 🔵 `prod-zug-v12.sh`: Einheit als Pflichtargument · writing-hub · ich, Issue + PR — https://github.com/achimdehnert/writing-hub/issues/1181
- **[M7]** 🔵 Folienmaße: eine Quelle oder bindender Test · writing-hub · ich, Issue — https://github.com/achimdehnert/writing-hub/issues/1181
- **[M8]** ✅ Belegprüfung je Vorschlag nachgeholt (31/19/1) · writing-hub · #2 Remediation — https://github.com/achimdehnert/writing-hub/pull/1189
- **[M9]** 🟢 Gates: `self-review-presented-as-review` + `prod-as-test-environment` registrieren; `gate-modul-prueft-weniger-als-sein-name` und `claim-before-cheapest-check` revidieren · platform · du entscheidest, ich baue — https://github.com/achimdehnert/platform/tree/main/docs/governance/gates
- **[M10]** 🟢 Memory-Kandidaten aus §6 übernehmen · writing-hub · du — https://github.com/achimdehnert/writing-hub/issues/1181
- **[M11]** ✅ Streichbahn: kein Kandidat, Grund im Frontmatter · platform — https://github.com/achimdehnert/platform/tree/main/docs/retros

## 8. Nicht verifiziert (Restlücken)

- **Owner-Worte „122 go" (11:33-Lauf) und „5 go" (16:48-Lauf):** in `kennzahlen.json` nicht sichtbar (Nachrichten auf 200 Zeichen gekürzt; 16:48 liegt nach der Kompaktierung) — Footprint-Grund (a) ist aus den Kennzahlen nur für 10:22 „ok go" belegt, die beiden anderen sind Session-Gedächtnis; billigster Check: `grep -c '122 go' <transkript.jsonl>` und `grep -c '"5 go' <transkript.jsonl>`.
- **Unabhängigkeit der #1189-Prüfer (#2):** ob die 51 Urteile in #1189 in frischem Kontext liefen; billigster Check: Skript-Header in `docs/lehre/dai-strategy/buchanalyse/v11/belege_pruefen.py`.
- **Rückfall-Status `lint-failure-no-local-gate` (#21):** Revisionszeitpunkt des Gates gegen Run 07:02:17Z; billigster Check: `git log -1 --format=%cI -- docs/governance/gates/gates/lint-failure-no-local-gate.json` in platform.
- **K6 Reproduzierbarkeit der v12-Dossiers:** nur die Leseliste ist zweimal identisch gebaut belegt; billigster Check: `zusammenstellen.py` zweimal laufen lassen und `v12-inhalt.json` per sha256 vergleichen.
- **Genehmigungs-Zeitpunkt des 13:47-Schreiblaufs** (Angebotstreppe-Bild) im Transkript nicht dem Wort zugeordnet; billigster Check: `retro_transkript_kennzahlen.py --von 13:30 --bis 13:50`.
- **`make test-pg` durchgängig statt rohes pytest:** Kennzahlen zeigen nur gekürzte Befehle; billigster Check: `grep -c "pytest " <transkript>` gegen `grep -c "make test"`.
- **Skeptiker-Reichweite E4:** Seminardossiers unter `apps/lectures/inhalte/` wurden nicht in den Regex-Korpuslauf einbezogen.

**Abdeckungsauskunft (Regel 5):** getan — 3 Finder je Dimension über PRs #1182–#1207, Issues, Kennzahlen; 3 Skeptiker über alle 4 Bewertungsbefunde + over_act; Widerlegungsbahn über alle 18 Befunde, 40 CI-Läufe, Secrets-grep, Handover-Log; Korpuslauf der Regex über 129 Quellen. angenommen — Kennzahlen-Skript zählt Stop-Hooks vollständig; Artefaktliste ist der ganze Scope; „ok go" 10:22 deckt den ersten v12-Lauf. nicht verifizierbar — Transkript-Zuordnung einzelner „go"-Wörter zu Läufen ohne Volltext-Lauf; Kontexte der #1189-Prüfer. offen geblieben — die sieben Punkte oben.

## Widerlegung

Widerlegungsbahn (Opus, frischer Kontext; Eingabe: Report-Entwurf mit 18 Befunden + Artefaktliste + Kennzahlen):

- #1 — BESTAETIGT — `git show 8e97028:docs/guides/prod-zug-v12.sh` Z.96–101 schreibt jede abweichende Einheit; #1181 11:36:45Z wörtlich; PR #1193 wörtlich. Einwand unentscheidbar: „122 go"/„5 go" nicht in den Kennzahlen (→ §8).
- #2 — BESTAETIGT mit Einschränkung — #1189 (08:52) holte die Prüfung je Vorschlag nach (31/19/1); in Tabelle und M8 ergänzt.
- #3, #4, #7, #8, #9, #10, #11, #12, #13, #17 — BESTAETIGT — je wörtlicher Beleg (Issue-Kommentar, PR-Body, `origin/main`-Zeile), siehe Tabelle.
- #5, #6, #14, #15, #16 — BESTAETIGT (Verwerfung hält) — #1178 mit Bedingung; Handover Z.39/43/71; `git log -S "len(dokument.pages)"` → 13d5907 (#1066) vor #1206; #1199 ohne Folge-Nutzung; 24 Runs auf main grün.
- #18 — GEKIPPT — #1203 Body und Schlusskommentar „Erledigt" 15:46:54Z, #1181 15:46:56Z; der Skeptiker hatte #1203 nicht gelesen. Aus SURVIVES → REFUTED, M8 gestrichen, `issue-open-after-its-fix-merged` zurückgenommen.
- NEU-A → #19 (mittel), NEU-B → #20 (niedrig), NEU-C → #21 (niedrig, schließt die §8-Lücke „51 go checks failing").

widerlegung: "1 gekippt, 3 neu". Abdeckung der Bahn: versucht — alle 18 Befunde gegen `gh`/`origin/main`, 40 CI-Läufe, Zeitfenster 06:40–07:20 alle Branches, Secrets-grep über beide Prod-Skripte (0 Treffer, gitleaks grün), Handover-Log seit 15.09. (leer, `/session-ende` steht aus); nicht versucht — Transkript-Volltext, K6-Doppellauf, Prod-Lesen, Kontexte der #1189-Prüfer.

## Streichbahn

**(b) keiner, weil** jede Phase dieser Retro das Urteil verändert hat: die Skeptiker kippten 3 von 4 Bewertungsbefunden und präzisierten den vierten am Korpus, die Widerlegungsbahn kippte einen kommandobelegten Befund und fand drei neue, das Kennzahlen-Skript lieferte zwei Befunde (#10, #12). Der einzige ertragsarme Teil ist `over_ask` (14 von 17 Retros leer, eine Klasse ×1) — er hat mit `retro_kpis.py --nominierung` einen Leser und ist der einzige Sensor für KONZ-025 Art. 2.1a; Streichen hieße, die Nominierung abzuschaffen. Ratsche: der Kandidat der Vorgänger-Retro (`retro-phase1-sammler-subagent`, 916eb7) ist am 2026-09-16 gestrichen worden (Skill-Changelog) — kein zweites Auftauchen.

## Self-Review

Meta-Agent (Sonnet, sah nur Report + Skill): `retro_report_check.py` → „1 Report(s) regelkonform". Checkliste 1–8 ✅ bis auf 5 🟡: Belege stichprobenartig verifiziert (#1 `8e97028` Z.96–101, #9 `deck.py:73`, #17 `_seminar_dossiers()` Z.305/308, #21 Run 35066518527 `failure` 07:02:17Z; `same-file-serial-prs ×14`, Gate-Datei und drei Memory-Dateien existieren). Invariante 15 = 15 = 21 − 4 − 2; `refuted_rate` 0,29 = (4+2)/21, echte Quote 4/19 = 0,21, `retro_kpis.py` „Band gesund". Zwei Korrekturen eingearbeitet: „4 Gates haben gefangen" war der Längsschnitt-Wert, nicht die Sitzung (jetzt getrennt); Konsequenz-Wort in §5a „nachschärfen" → Kanon-Wort „umbauen".
