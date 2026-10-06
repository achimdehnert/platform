---
retro_schema: 1
date: 2026-09-15
repo_scope: [writing-hub, decks-hub]
session_id: a397a5
footprint: full
footprint_reduction_reason: "deep→full: (a) jeder Prod-Schritt ausdrücklich freigegeben und im Issue verankert (#1162 09:15, #1171 10:44/11:14/12:07), (b) keine DB-Migration, Datenschritte über idempotentes Kommando mit Sicherung, (c) Befund-Schätzung ≤10 (tatsächlich 16 inkl. 3b)"
findings_total: 16
findings_survived: 10
refuted_rate: 0.31
phase3_refuted: 5   # #2 #3 #9 #13 #14 vom Phase-3-Skeptiker; #11 erst in 3b gekippt, nicht mitgezaehlt (steht in widerlegung)
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [gate-claim-before-cheapest-check-wirkungslos, verify-step-not-gating-write, gate-wirkung-ignoriert-covers]
recurring_findings: [gate-claim-before-cheapest-check-wirkungslos, check-ohne-positivkontrolle, dod-reinterpreted-only-in-pr-body, verify-step-not-gating-write, ausnahme-gegen-eigenes-gate-nicht-geprueft, prod-fehlschlag-in-erfolgsmeldung-verschwiegen, mehrdeutige-owner-anweisung-ohne-rueckfrage, folgeauftrag-unter-geschlossenem-issue, adr-evidence-stale-after-feature-removal, gate-wirkung-ignoriert-covers]
gates_caught: [secret-leak-via-safe-pattern, claim-before-cheapest-check]
over_ask_klassen: []
over_act_klassen: [prod-host-temp-loeschen-unter-lesefreigabe]
widerlegung: "4 gekippt, 2 neu"
streichkandidaten: [retro-phase1-collector-subagent]
---

# Session-Retro 2026-09-15 — writing-hub + decks-hub (a397a5)

## 1. Executive Summary
- Geliefert und live: Reiter „Modul" bearbeitbar + Sperre (writing-hub#1167), Zusatzeinheit „Wirksam prompten" mit Kommando und Deck (writing-hub#1172, decks-hub#102), Folien 4–7 + zwei Diagramme (writing-hub#1173, decks-hub#103); alle Required-Checks und Deploys grün; Prod = main in beiden Repos **Stand ~12:45 UTC** (danach writing-hub#1174 einer parallelen Sitzung, 12:58).
- Freigabe-Disziplin hielt: jeder Merge/Prod-Datenschritt/Dev-Neustart lief nach einer im Issue verankerten Owner-Freigabe (Prozess-Finder, Abdeckungsauskunft); ein over_act am Rand (Löschen eigener Temp-Dateien auf Prod unter Lese-Freigabe).
- Schwächster Punkt: Prüfungen ohne Wirkung auf den nächsten Schritt — Sicherungsprüfung lief nach dem Prod-Schreiben (#5), ein Messfehler stand 3,5 h als „Rotation nötig" (#6).
- Das blockierende Gate `claim-before-cheapest-check` (Rev 8, 2026-09-14) war bei #1 und #6 blind — Rückfall-Klasse, kein neues Gate (Widerlegung).
- Nebenwirkung der Streichung: ADR-186/187 zitieren gelöschte Tests/UI als Nachweis (#15).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | K6 verlangte „/ux-review"; nie aufgerufen, PR-Body nennt „Klick-Lauf", Abschluss führt CI/Deploy als K6-Beleg; „ohne Befund" war zudem sachlich nicht erfüllt (Kontrastbefund 08:17 nach #1170 verschoben) | Prozesslücke | hoch | SURVIVES (kommandobelegt, 3b bestätigt) | #1162 Body K6; Kennzahlen `Skill: 1`; #1167 Body; #1162-Kommentar 10:03; Memory `feedback-gui-durchlauf-ux-review-nutzen` | dod-reinterpreted-only-in-pr-body ×3 (covers von `issue-offen-nach-gemergtem-fix`); Sonde `kriteriums-claim` von claim-before-cheapest-check blind |
| 2 | Bildstellen-Bedienung ohne spezifische Freigabe entfernt, Konsequenz erst nachträglich bemerkt | verfrühte Festlegung | hoch | REFUTED (3b bestätigt; Zusatz: Konflikt mit Owner-Entscheid 45 A vom Vortag nicht angesprochen) | #1162-Kommentar 08:42 nennt „Titelbild anfordern … kein Bedienweg" zeitgleich; `bca611e:templates/lectures/module_detail.html` Z. 150 | — |
| 3 | K3 „Deck-Prüfung ohne Befund" wegen 8-vs-7 nicht tragfähig, ohne Tracking | fehlende Validierung | mittel | REFUTED | `tests/test_dai_strategy_prompten.py` test_should_fit_every_section_on_one_slide mit Positivkontrolle; #1170-Kommentar 11:46 | — |
| 4 | Folien 4–7 (#1173) ohne eigenes Issue/Zielzustand, „Refs" auf bereits geschlossenes #1171 | Prozesslücke | niedrig | SURVIVES (kommandobelegt) | #1171 closedAt 11:01:38; #1173 mergedAt 12:10:30, Body „Refs #1171" | folgeauftrag-unter-geschlossenem-issue ×1 |
| 5 | Sicherungsprüfung vor Prod-Datenschritt 1 lief ins Leere (`docker exec` ohne `-i`), Schreiben lief weiter; Prüfung erst danach | fehlende Validierung | hoch | SURVIVES (kommandobelegt, selbst gemeldet) | #1171-Kommentar 11:29 „Eigener Fehler" | verify-step-not-gating-write ×1 (zweites `-i`-Vorkommen derselben Sitzung: Media-Löschung) |
| 6 | Behauptung „Groq-Schlüssel ungültig, Rotation nötig" (Messfehler: KV-Zeile als Bearer) mit Handlungsaufforderung an den Owner, ~3,5 h stehen gelassen, Korrektur erst nach Owner-Nachfrage | fehlende Validierung | hoch | SURVIVES (Ort #1162; Slug-Zuordnung durch 3b korrigiert) | #1162-Kommentar 08:23:15; Owner 11:51:53; #1170-Korrektur 11:53:28 | claim-before-cheapest-check (Hook ließ durch) + check-ohne-positivkontrolle ×2 |
| 7 | Routen zunächst als Gate-Ausnahme belassen, 14 min später wegen #781 doch entfernt | verfrühte Festlegung | mittel | SURVIVES (kommandobelegt) | #1162-Kommentare 08:42:24 / 08:56:14 | ausnahme-gegen-eigenes-gate-nicht-geprueft ×1 |
| 8 | Prod-Aufräumen scheiterte zuerst („Operation not permitted"), Erfolgsmeldung „0 Reste" verschweigt Fehlschlag und Methode | Kommunikation | niedrig | SURVIVES | Fehlerlauf 08:29:18; #1162-Kommentar 08:32:18 | prod-fehlschlag-in-erfolgsmeldung-verschwiegen ×1 |
| 9 | Zwei Versuche, Secret-Klartext auszulesen | Prozesslücke | mittel | REFUTED | Befehle geschwärzt; Guard nennt nur Werkzeugtyp; tatsächlicher Weg „kein Wert ausgegeben" (#1170 11:53) | — |
| 10 | Zwei Secret-Leak-Guard-Blockaden beim Nachmessen, erst dann guard-konformer Weg | Werkzeug | niedrig | SURVIVES (kommandobelegt) | Fehlerläufe 11:52:17, 11:52:31 | gefangen von secret-leak-via-safe-pattern |
| 11 | K2/K3 gebaut, bevor geprüft war, ob „Vorlesungen im Modul" sie abdeckt — Rework durch verfrühte Festlegung | verfrühte Festlegung | niedrig | REFUTED in 3b (Phase 3: SURVIVES; 3b: K2/K3 akzeptiert, Owner setzte die Sichtung selbst an und strich danach; −273 in views_modules.py sind Bestandscode aus `bca611e`) | #1162 Body; Owner 08:26, 08:35/08:37; `git diff bca611e..7ec82af -- apps/lectures/views_modules.py` | — |
| 12 | „lass es mich local testen" als „lokale KI einschalten" gelesen; 3 KI-Fehlläufe + Rückbau | Kommunikation | mittel | SURVIVES (kommandobelegt) | Owner 08:19:15; Fehlerläufe 08:20–08:21; #1162-Kommentar 08:23 „zurückgenommen" | mehrdeutige-owner-anweisung-ohne-rueckfrage ×1 |
| 13 | Statusaussage über offenen Pull ohne Prüfung | fehlende Validierung | niedrig | REFUTED in Phase 3 (Befund unbelegt; 3b: Gegenbeleg unentscheidbar — Gegenbeleg „kein offener PR" falsch, Draft #1054 offen; s. §8) | Owner 12:19:47; kein Assistant-Text im Material | — |
| 14 | Edit-Fehlläufe 08:01–08:06 Mitursache des späteren Rückbaus | Werkzeug | niedrig | REFUTED | Rückbau-Auslöser Owner-Entscheid 08:35/08:37 | — |
| 15 | ADR-186/187 stehen auf `implemented` und zitieren als Nachweis `tests/test_lectures_lehrinhalt_views.py` bzw. UI-PRs, die #1167 gelöscht hat | fehlende Validierung | mittel | SURVIVES (NEU aus 3b, kommandobelegt) | `origin/main:docs/adr/ADR-186-lehrinhalt-modell-modulebene.md` Frontmatter; `git cat-file -e origin/main:tests/test_lectures_lehrinhalt_views.py` fehlt | adr-evidence-stale-after-feature-removal ×1 |
| 16 | `gate_wirkung.py` misst Rückfälle nur über den Haupt-Slug, `retro_kpis.py` wertet `covers` als „Gate registriert" — Rückfälle unter mitgedeckten Slugs werden nie RUECKFAELLIG | Werkzeug | mittel | SURVIVES (NEU aus 3b, kommandobelegt) | `platform:tools/gate_wirkung.py` Z. 250–277; `tools/retro_kpis.py` Z. 216/236; `gate-registry.json` Z. 1097–1107 | gate-wirkung-ignoriert-covers ×1 |

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| zielerreichung | 4 | alles live; K6 ohne Benennung ersetzt (#1) |
| architektur_design | 4 | ein idempotentes Kommando für Dev+Prod; verfrühte Gate-Ausnahme (#7) |
| code_konventionstreue | 4 | Tests mit Positivkontrollen; ADR-Nachweise nicht nachgezogen (#15) |
| risiko_debt | 3 | Prod-Schreiben vor belegter Sicherung (#5), verschwiegener Fehlschlag (#8) |
| prozess_effizienz | 3 | Fehlinterpretation mit Rückbau (#12), Folgeauftrag ohne Issue (#4) |
| entscheidungsqualitaet | 3 | Messfehler als Handlungsaufforderung verankert (#6) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| K6 nennt /ux-review, geliefert Playwright-Klicklauf; Abschluss zitiert CI (#1162 10:03) | Nennt ein Kriterium ein Werkzeug, wird es aufgerufen — oder der Abschluss führt „K6 ersetzt durch X, weil Y" als eigene Zeile; offene Teilbefunde heißen „mit Befund", nicht „ohne" | #1 |
| Folgeauftrag „integriere 4–7" als PR unter geschlossenem #1171 | Neuer Owner-Auftrag nach Issue-Schließung → #1171 wieder öffnen oder Kurz-Issue mit 2–3 Kriterien, bevor gebaut wird | #4 |
| `pg_restore -l` ohne `-i` lief ins Leere, Kette schrieb weiter (#1171 11:29) | Sicherung + Prüfung als eigener Aufruf, der nur bei belegter Zahl (Tabellendaten > 0) den Schreibschritt freigibt — so im zweiten Datenschritt umgesetzt (#1171 12:25) | #5 |
| 401 an Groq als „Rotation nötig" an den Owner (#1162 08:23) | Vor einem Negativbefund mit Handlungsaufforderung: Format der Quelle prüfen und am selben Messweg einen bekannt-positiven Fall gegenmessen | #6 |
| Ausnahme im Routen-Gate eingetragen, dann #781 entdeckt (#1162 08:42/08:56) | Vor einer Gate-Ausnahme alle Tests greppen, die dieselben Namen prüfen (`grep -rl <route> tests/`) | #7 |
| „0 Reste" gemeldet ohne den Fehlschlag (#1162 08:32) | Erfolgsmeldung nennt Zwischenfehlschlag und geänderte Methode in einem Halbsatz | #8 |
| Zwei Guard-Blockaden vor dem konformen Weg (11:52) | Messungen an Secret-Dateien beginnen mit einem per Write abgelegten Skript, das nur Status/Länge/Gleichheit ausgibt | #10 |
| „local testen" als lokale KI gelesen (08:19) | Mehrdeutige Kurzanweisung in einem Satz zurückspiegeln, bevor Settings/DB geändert werden | #12 |
| Views/Tests gelöscht, ADR-186/187 unverändert auf `implemented` mit toten Nachweisen | Beim Entfernen einer Funktion `git grep` über `docs/adr/` nach den gelöschten Dateien/Routen und die Nachweiszeilen im selben PR nachziehen | #15 |
| `gate_wirkung.py` zählt nur Haupt-Slugs, `covers`-Slugs gelten als gedeckt | `gate_wirkung.py` bewertet `covers` wie den Haupt-Slug (Rückfall je gedecktem Slug) | #16 |

## 5. Längsschnitt
`python3 tools/retro_kpis.py` (125 Reports) und `gate_wirkung.py`:
- **gate-claim-before-cheapest-check-wirkungslos** ×1 vorher (beefc148) → mit #1/#6 ×2 ⇒ **GATE-PFLICHT als Rückfall-Klasse** (kein neues Gate).
- **check-ohne-positivkontrolle** ×1 vorher (40c069) → ×2 ⇒ Pflicht, eingelöst über die Revision von claim-before-cheapest-check (s. 5a), nicht als eigenes Gate.
- **dod-reinterpreted-only-in-pr-body** ×3 — in `covers` von `issue-offen-nach-gemergtem-fix`; wegen #16 nie als Rückfall messbar.
- Übrige Slugs neu ×1. Drift-Memories zur Positivkontrolle existieren bereits (`drift-pruefung-erkennt-eigenen-leerlauf-nicht`, `drift-positivkontrolle-prueft-werkzeug-nicht-ort`) — kein weiteres Memo.

### 5a. Rückfall-Prüfung
`gate_wirkung.py` meldet kein Gate RUECKFAELLIG (claim-before-cheapest-check `zu-frueh`). Die Widerlegung belegt dennoch zwei konkrete Durchlässe dieses Gates in dieser Sitzung:
- **#1** — Sonde `kriteriums-claim` feuert nur bei „erreicht|erfüllt|nachgewiesen" und strippt Klammern (`evidence_claim_scanner.py` Z. 706/776); „(/ux-review)" und K-Tabellen ohne Triggerwort fallen durch.
- **#6** — ein Werkzeuglauf lag vor, der Hook akzeptierte ihn; die Positivkontrolle fehlte.
**Konsequenz (vorgeschlagen): ausweiten** — derselbe Registry-Eintrag bekommt `revised` + `revision_note` + neue `positivkontrolle` (K-Tabelle ohne Triggerwort; Werkzeugname in Klammern; Negativbefund ohne Positivkontrolle). Umsetzung über `tools/gate_verankerung_check.py --neu`, Entscheidung beim Owner.
`secret-leak-via-safe-pattern` hat #10 **gefangen**; `claim-before-cheapest-check` hat in dieser Sitzung einmal **gefangen** (Stop-Hook 12:41:49, Kennzahlen Z. 75).

### 5b. Autonomie-Kalibrierung
- over_act: `prod-host-temp-loeschen-unter-lesefreigabe` — Löschen eigener Exportdateien auf hetzner-prod (08:29) unter einer Lese-Freigabe (Skeptiker SURVIVES).
- over_ask: keiner belegt (abgelehnte Rückfrage 08:37 ohne Inhaltsbeleg).

## 6. Verankerung (Vorschläge, nicht geschrieben)

**memory_candidates**
- `feedback-docker-exec-stdin-braucht-i` (drift: true, drift_episode: 2026-09-15-sicherungspruefung-leer): „`docker exec … < datei` ohne `-i` liest leeres stdin — die Prüfung läuft still ins Leere. Zweimal am 2026-09-15 (Media-Löschung, Sicherungsprüfung vor Prod-Schreiben). How: `docker exec -i`, und das Prüfergebnis (Zahl) als Bedingung des nächsten Schritts."
- Kein Memo zur Positivkontrolle (Dublette bestehender Drift-Memories).

**adr_candidates**: keine neue ADR; **ADR-186/187 nachziehen** (Nachweiszeilen, ggf. `implementation_status`) — writing-hub.

**gate_candidates**
- Revision `claim-before-cheapest-check` (5a).
- `verify-step-not-gating-write` — Kandidat ×1, noch keine Pflicht.
- `gate_wirkung.py` wertet `covers` (platform-Werkzeug).

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Gate claim-before-cheapest-check ausweiten | platform | [registry](https://github.com/achimdehnert/platform/blob/main/docs/governance/gate-registry.json) | 🟢 | du: Revision freigeben |
| M2 | gate_wirkung.py wertet covers | platform | [gate_wirkung.py](https://github.com/achimdehnert/platform/blob/main/tools/gate_wirkung.py) | 🟢 | du: Issue freigeben |
| M3 | ADR-186/187 Nachweise nachziehen | writing-hub | [ADR-186](https://github.com/achimdehnert/writing-hub/blob/main/docs/adr/ADR-186-lehrinhalt-modell-modulebene.md) | 🔵 | ich: Docs-PR |
| M4 | K6-Substitution an #1162 nachtragen | writing-hub | [#1162](https://github.com/achimdehnert/writing-hub/issues/1162) | 🔵 | ich: Kommentar |
| M5 | Memory docker exec -i | writing-hub | [#1171](https://github.com/achimdehnert/writing-hub/issues/1171) | 🔵 | ich: bei session-ende |
| M6 | Streichkandidat Collector-Subagent | platform | [retro.md](https://github.com/achimdehnert/platform/blob/main/docs/governance/session-skills-lehren/retro.md) | 🟢 | du: entscheiden |

## 8. Nicht verifiziert (Restlücken)
- **#13** unentscheidbar: welcher Assistant-Text die Owner-Nachricht „102 kein pull offen" (12:19:47) auslöste — billigster Check: im JSONL den Assistant-Text zwischen 12:18:43 und 12:19:47 nach „102" durchsuchen.
- Inhalt der abgelehnten Rückfrage (08:37) — billigster Check: AskUserQuestion-Zeile im JSONL.
- Deck-Darstellung am gerenderten decks-hub (Folie 3) nur aus der Folienreihenfolge abgeleitet, nicht im Browser nachgezählt (Cloudflare Access).
- Deploy-Stand nach writing-hub#1174 (12:58, parallele Sitzung) nicht geprüft.
- Regel-1-Grenze: Befunde von frischen Subagenten; Zusammenführung und Slug-Wahl im Haupt-Kontext (3b hat eine Slug-Wahl korrigiert).

## Widerlegung
Phase 3b (Opus, frischer Kontext, gh/git): **4 gekippt, 2 neu.**
- GEKIPPT: §5/M2 „neues Gate dod-reinterpreted" — Slug ist in `covers` von `issue-offen-nach-gemergtem-fix`, #1 gehört zur blinden Sonde `kriteriums-claim` → Revision statt Dublette.
- GEKIPPT: #6 Slug-Zuordnung — „Rotation nötig" ist eine Behauptung mit Handlungsaufforderung ohne billigsten Check → claim-before-cheapest-check zusätzlich; Memo-Kandidat Positivkontrolle ist Dublette.
- GEKIPPT: #11 — legitime neue Owner-Entscheidung nach selbst angesetzter Sichtung; −273 Bestandscode.
- GEKIPPT: §8 Restlücke „Stop-Hook gefeuert?" — belegt (Kennzahlen Z. 75) → gates_caught ergänzt.
- NEU: #15 ADR-186/187 mit toten Nachweisen. NEU: #16 gate_wirkung ignoriert covers.
- Bestätigt: #1 (inkl. „ohne Befund" sachlich falsch), #2 (Zusatz 45 A), #3, #4, #5, #7, #8, #9, #10, #12, #14. #13 unentscheidbar.

## Streichbahn
- **retro-phase1-collector-subagent** — Belegart **Dublette**: Phase 2/3 verlangen, dass Finder und Skeptiker jeden Beleg unabhängig neu per gh/git ziehen (Skill § Phase 3 „Eiserne Verify-Regel"); alle drei Finder und die Widerlegung taten das (Abdeckungsauskünfte), die einzige Collector-Eigenleistung war eine falsche Zeitangabe (#1168 „12:10"), die zwei Finder korrigieren mussten. Die Transkript-Kennzahlen liefert bereits das Skript.

## Self-Review
Meta-Agent (Sonnet, nur Report gegen Skill): Stichproben #5, #6, #15, #16 sowie „Rev 8, 2026-09-14" in §5a wortgetreu bestätigt; Scores ganzzahlig und verankert; Invariante Soll-Schritte/Überlebende 10/10; eingefrorene Spalten lückenlos; §8, Widerlegung und Streichbahn vorhanden; Pfad kollisionsfrei. Einziger Mangel war die Etikettierung: sechs REFUTED in der Tabelle gegen `phase3_refuted: 5` — aufgelöst, #11 wurde erst in 3b gekippt und zählt nicht in die Phase-3-Quote (Frontmatter-Kommentar, Verdikt-Spalte präzisiert). Falsifikationsquote phase3_refuted/(findings_total − pre_refuted) = 5/16 = 0,31 — im unauffälligen Band (0,2–0,8).
