---
concept_id: KONZ-platform-051
title: "ux-review-agent — eine Kette klick-only auf Begehbarkeit pruefen, je Befund ein Klassen-Gate"
pipeline_status: idea
tier: T2
owner: "Achim Dehnert"
spec_refs: []
adr_threshold: >
  Kein ADR fuer Stufe 1 (CC-Skill, Ausgabe = Issues; Addition nach dem Muster
  kd-review/ADR-251, rueckbaubar durch Loeschen des Skills). ADR-wuerdig wird
  Stufe 2: ein geplanter Dienst in dev-hub/apps mit issues:write auf fremde
  Repos (Perimeter, policies/platform-agents.md, Gate autonomous-no-human-review).
review_by: 2026-10-15
kill_criteria: >
  Pilot bis 2026-09-30 auf writing-hub und ausschreibungs-hub gegen den Stand
  VOR den Fixes: findet der Agent weniger als 7 der 9 bekannten Defekte wieder
  ODER liegt die Fehlbefund-Quote ueber 30 % (Owner-Urteil je Issue) ODER
  liefert er zu keinem Befund einen Klassen-Gate-Vorschlag, der einen zweiten
  Fall faengt — dann Stufe 1 einfrieren, Stufe 2 nicht bauen, Memory
  project_ux_review_agent_program auf sunset.
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: ~/.claude/projects/-home-devuser-github-platform/memory/project_ux_review_agent_program.md, commit_or_pr: "Owner-Weisung 2026-07-22", opened_in_session: true}
  - {claim_id: C2, source_path: docs/retros/session-retro-2026-08-25-writing-hub-fdd368.md, commit_or_pr: "#2325", opened_in_session: true}
  - {claim_id: C3, source_path: "knowledge.iil.pet/doc/2026-08-25-sechs-befunde-die-nur-ein-browser-sehen-konnte-ausschreibungs-hub-Oo0ZmhrOIA", commit_or_pr: "Outline 2026-08-25", opened_in_session: true}
  - {claim_id: C4, source_path: "ausschreibungs-hub/tests/test_erreichbarkeit_screens.py", commit_or_pr: "main 2026-08-25", opened_in_session: true}
  - {claim_id: C5, source_path: "ausschreibungs-hub/templates/base/base.html:101", commit_or_pr: "main 2026-08-25", opened_in_session: true}
  - {claim_id: C6, source_path: .windsurf/workflows/kd-review.md, commit_or_pr: "main c39462d5", opened_in_session: true}
  - {claim_id: C7, source_path: docs/adr/ADR-251-reengineering-pipeline-ux-gate-am-klickdummy.md, commit_or_pr: "accepted", opened_in_session: true}
  - {claim_id: C8, source_path: "pgvector error:ausschreibungs-hub:20260825-screen-ohne-weg", commit_or_pr: "agent_memory_search 2026-08-25", opened_in_session: true}
  - {claim_id: C9, source_path: "pgvector error:ausschreibungs-hub:f8820cc8a690", commit_or_pr: "agent_memory_search 2026-08-25", opened_in_session: true}
created: 2026-08-25
---

# KONZ-platform-051: ux-review-agent

## Kernthese

Ein Agent, der eine benannte Kette **nur per Klick** durchlaeuft, beweist ihre
Begehbarkeit — und der Ertrag ist nicht der Einzelbefund, sondern der
**Klassen-Test**, den er je Befund vorschlaegt (2 verwaiste Screens -> Test ueber
alle Routen -> 14, C4/C8).

## Fakt

Zwei Repos, zwei Tage, beide Male von Hand am Tresen:

| Repo | Datum | Vorher | Was der Browser fand | Was Tests hatten sehen koennen | Beleg |
|---|---|---|---|---|---|
| writing-hub | 2026-08-25 | e2e mit deterministischem Stub gruen | 3 Produktdefekte (#758 escapejs an 4 Stellen, #759, #762) | 0 von 3 | C2 |
| ausschreibungs-hub | 2026-08-25 | 329 Tests gruen, Kette in Prod nie durchlaufen (89 Ausschreibungen, 0 Angebote) | 6 Befunde, darunter 14 Routen aus keinem Template verlinkt (Station 4 und 5 der Kette) | 0 von 6 | C3, C8 |
| ausschreibungs-hub | 2026-08-24 | Routen-Tests gruen | Bid/No-Bid nur per URL, Abmelden fehlt, HTMX-4xx unsichtbar | 0 von 3 | C9 |

Und derselbe Lauf zeigte, wie ein Agent **falsch** liegt: Issue #760 „Feld fehlt"
aus leerem DOM, das Feld existierte (Rendering-Bedingung); geteilte `.env` fuer
den eigenen Lauf verstellt bei 12 parallelen Sessions; „alle Checks gruen" bei
zwei roten, weil `tail -12` sie abschnitt (C2).

**Owner-Prio seit 2026-07-22** (C1): „autonom UX testen, Prioritaet vor allem".
Naechster Schritt damals: KONZ T2 + Live-Pilot. Bis heute: kein KONZ
(`grep -li 'e2e|ux-review|playwright' docs/konzepte` -> 0 vor diesem Dokument).

**Was existiert und was nicht** (Root-Cause-Tiefe):

| Mechanismus | Prueft | Luecke | Beleg |
|---|---|---|---|
| `/kd-review` | Klickdummy statisch: I1-Coverage, Console, UX-Subagent gegen Design-System | kein Login, keine laufende App, keine Kette | C6 |
| ADR-251 UX-Gate | Gate **am Klickdummy** | endet vor der gebauten App | C7 |
| `/repo-ux-opt` | Struktur-Audit einer App | liest Code, klickt nicht | Skill-Liste |
| writing-hub `make e2e-buch` | Buch-Kette mit Stub | „ausdruecklich nicht abgedeckt: Oberflaeche" | pgvector outline:writing-hub:20260823-kc |
| ausschreibungs-hub `test_erreichbarkeit_screens.py` | jede Route gegen `{% url %}` aller Templates | repo-lokal, eine Klasse, nach dem Befund gebaut | C4 |

Der Agent ist also kein Ersatz fuer einen dieser fuenf, sondern das Stueck
**zwischen** Klickdummy-Gate und Klassen-Test: die laufende App, benutzt wie ein
Mensch.

## Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|---|---|---|---|---|
| A1 | HTTP-/Routen-Tests koennen Begehbarkeit strukturell nicht sehen | Annahme | C3, C9: `reverse()` gruen, kein Template verlinkt; 3 Repos-Tage, 12 Befunde, 0 durch Tests | belegt |
| A2 | Der Wert liegt im Klassen-Gate, nicht im Einzelfund | Annahme | C4/C8: 2 -> 14; Falsifikation: Pilot liefert Gate-Vorschlaege, die keinen zweiten Fall fangen | offen (Kill-Gate) |
| A3 | Fehlbefunde kosten mehr Owner-Zeit als sie sparen, wenn > 30 % | Annahme | C2 #760: Freigabe fuer Fix, den es nicht brauchte | belegt, Schwelle = Setzung |
| A4 | Playwright-MCP (`navigate/click/fill/snapshot/console`) ist im CC-Perimeter nutzbar, `run_code_unsafe` nicht | Annahme | C1 (real genutzt 2026-07-22); C2 (real genutzt 2026-08-25) | belegt |
| E1 | **Klick-only**: eine getippte URL ist selbst ein Befund der Klasse „nicht begehbar" | Entscheidung | Alternative: URL-Liste abfahren (= Routen-Test mit Browser, sieht A1 nicht) | gesetzt |
| E2 | **Absenz braucht zweiten Suchpfad**: „Feature fehlt" nur nach `grep -rn <feld> templates/ apps/` leer | Entscheidung | C2 #760; Alternative: Owner filtert (= A3) | gesetzt |
| E3 | **Ausgabe = Issue im Zielrepo** mit Screenshot, Antwortkoerper, Repro, Severity `fehler`/`optimierung`, Klassen-Gate-Vorschlag; nie PR, nie Deploy | Entscheidung | Autonomie-Grenze aus C1; Tracking-Artefakt-Regel | gesetzt |
| E4 | **Drei Zustaende** im Bericht: Befund / OK / blind — blind ist nie gruen (Exit 2 wie in #2284) | Entscheidung | C3 Regel 5: „SKIP kein PASS"; Alternative: zwei Zustaende (= die Klasse, die 2026-08-25 sechsmal versagte) | gesetzt |
| E5 | **Eigene Umgebung**: eigener Worktree + eigener Compose-Stack oder Staging; nie die geteilte `.env`, Port-Vorpruefung (`ss -tlnp`), `*.localhost` -> `::1` beachten | Entscheidung | C2 Befund 3; C9 Prevention (4) | gesetzt |
| E6 | **Diagnose aus dem Antwortkoerper**, nie aus dem Statuscode; Konsole + Netzwerk werden mitgelesen | Entscheidung | C3 Regel 2 (403 = CSRF und Tenant); C9 HTMX-4xx unsichtbar | gesetzt |
| E7 | **Erfolgsaussehende Ausgaben gegen Quelle pruefen** (Fallback-Text, Extraktions-Rohbytes) | Entscheidung | C3 Regel 1 (3x in einer Sitzung) | gesetzt |
| E8 | **Stufe 1 = CC-Skill** `/ux-review <repo> <kette>`; **Stufe 2** (Dienst in `dev-hub/apps/`, Zeitplan) erst nach Kill-Gate | Entscheidung | policies/platform-agents.md; Gate autonomous-no-human-review | gesetzt |
| E9 | **Positivkontrolle vor der ersten Zahl**: Pilot laeuft gegen den Commit vor den Fixes (9 bekannte Defekte) | Entscheidung | Lehre #2253 (Kill-Gate pre-registrieren); C3 Regel 4 | gesetzt |
| R1 | Agent findet, Mensch fixt einzeln — Klassen-Gate bleibt Prosa im Issue | Risiko | A2; Gegenmittel: Gate-Vorschlag ist Pflichtfeld des Issue-Templates, Retro zaehlt gebaute Gates | offen |
| R2 | Login/CF-Access blockiert autonomen Lauf | Risiko | C1: Test-Creds per `fill`, CF-Access einmal als pytest-playwright verdrahten | offen, Pilot |
| R3 | Vision-Urteil („Optimierung") erzeugt Geschmacks-Issues | Risiko | Severity `optimierung` nur mit Referenz auf Design-System/ADR-048/049 oder Nielsen-Heuristik-Nummer | offen |
| R4 | Testdaten aus Prod im Screenshot (Personendaten, platform ist public) | Risiko | Screenshots nur ins Zielrepo-Issue (privat), nie nach platform; Pilot mit synthetischen Mandanten | offen |

## MVC (Stufe 1)

| Was | Wo | Inhalt |
|---|---|---|
| Skill | `platform/.windsurf/workflows/ux-review.md` (Verteilung via cc-skill-dist) — **gebaut 2026-08-25** | Phasen: (0) Umgebung E5 · (1) Einstieg = Startseite nach Login, ab dann Klick-only E1 · (2) je Station: Snapshot, Konsole, Netzwerk E6 · (3) Urteil: Befund/OK/blind E4 · (4) Absenz-Gegenprobe E2 · (5) Issue je Befund E3 · (6) Bericht |
| Issue-Schema | **im Skill** (Step 6) — *Abweichung 2026-08-25 beim Bau:* ein platform-Issue-Template gaelte nur fuer Issues in platform, die Issues landen aber im Zielrepo (Doppelquelle, D1) | Felder: Kette/Station · Screenshot · Antwortkoerper · Repro · Severity · **Klassen-Gate-Vorschlag** (Pflicht) · Gegenprobe (E2, Pflicht bei Absenz) |
| Bericht | stdout + **Sammel-Issue** `[ux-review] <repo> · <kette> · <datum>` im Zielrepo — *Abweichung 2026-08-25:* eine Datei im Zielrepo braeuchte einen PR, den E3 ausschliesst | drei Zustaende je Station, Zaehler: Befunde / OK / blind / bekannt; Owner labelt Fehlbefunde (`fehlbefund`) → K2 |
| Positivkontrolle | Pilot-Lauf gegen writing-hub `git checkout <sha vor #761>` und ausschreibungs-hub vor dem Erreichbarkeits-Fix | Trefferliste gegen die 9 bekannten Defekte |
| Gate-Katalog (Vorschlaege, die der Agent kennt) | im Skill | Routen-vs-Templates (C4) · mehrzeilige Django-Kommentare ueber alle Templates (C3) · `htmx:responseError` global (C5) · `hx-headers` CSRF am body (C3) · Invariante ueber Datenbestand statt Ursache (C3 Regel 3) · escapejs-Familie (C2) |

**Ausfuehrungsform (Step 2a):** mehrere Schritte ja; Schrittfolge steht fest
(Kette) — innerhalb einer Station entscheidet der Agent den naechsten Klick zur
Laufzeit; Stationen sequenziell (jede haengt vom Zustand der vorigen ab); keine
Barriere; kein Graph. **Schleife nur innerhalb einer Station**, Abbruch
messbar: Station erreicht ODER 25 Klicks ohne neue Seite -> Zustand `blind` mit
Grund. Budget je Lauf: eine Kette, deklariert vor dem Start.

## Steelman

Zwoelf Befunde in drei Repo-Tagen, keiner durch 329 + n gruene Tests sichtbar —
das ist keine Testluecke, die man mit mehr Tests schliesst, sondern eine
**Messrichtung**, die Tests nicht haben: vom Menschen aus. Beide Durchlaeufe
waren teuer (2,5 h writing-hub) und werden deshalb nicht wiederholt, wenn kein
Werkzeug sie traegt. Und beide zeigten dieselbe Uebersetzung: Browser-Befund ->
Klassen-Test -> Faktor 7 (2 -> 14). Ein Agent, der diese Uebersetzung
**erzwingt** (Pflichtfeld), macht aus jedem Tresen-Gang ein dauerhaftes Gate —
das ist die Owner-Weisung vom 22.07. mit einem Monat Evidenz obendrauf.

## Advocatus Diabolus

| # | Einwand | Antwort |
|---|---|---|
| D1 | **Doppelquelle:** `/kd-review` urteilt am Klickdummy, `/ux-review` an der App — zwei UX-Gates, zwei Wahrheiten | Verschiedene Objekte (Spec-Render vs. gebaute App), gleiche Kriterien (ADR-251). Kein zweites Design-System, kein zweites Scoreboard. Wird ein Kriterium neu, gehoert es in ADR-251, nicht in den Skill. |
| D2 | **Sichtbar machen statt verhindern:** Issues sind Prosa; der 15. verwaiste Screen kommt trotzdem | Deshalb E3/R1: der Gate-Vorschlag ist Pflichtfeld, und das Kill-Gate misst, ob daraus Tests wurden. Ohne gebaute Gates ist der Agent ein Melder — und wird per Kill-Gate eingefroren. |
| D3 | **Formal erfuellen, praktisch umgehen:** „Klick-only" — der Agent tippt eine URL und nennt es Befund, um weiterzukommen | Erlaubt und gewollt: die getippte URL **ist** der Befund und steht im Bericht. Umgehung ohne Meldung faellt an der Positivkontrolle auf (14 Routen muessen als Befund erscheinen). |
| D4 | **Agent mit issues:write auf fremde Repos** = Perimeter (Gate autonomous-no-human-review) | Stufe 1 laeuft in der interaktiven Session unter dem Owner-Token — kein neuer Automatismus. Stufe 2 ist genau deshalb ADR-pflichtig und hinter dem Kill-Gate. |
| D5 | **Vision-Urteil ist Geschmack** — Nielsen-Heuristiken per Screenshot erzeugen Rauschen | R3: `optimierung` nur mit Referenz. Ohne Referenz kein Issue, sondern Zeile im Bericht. Der Pilot zaehlt Fehlbefunde getrennt nach Severity. |
| D6 | **Der Fehlbefund #760 war ein Agent** — genau dieser Agent, ohne Werkzeug | Ja. E2 ist die Antwort, und sie ist mechanisch (grep), nicht appellativ. Wird sie im Pilot einmal umgangen, ist das ein Kill-Gate-Fall. |
| D7 | Verschlimmert es F18 (Locator-Fragilitaet)? | Nein: der Agent hat keine Locator-Liste, er liest Snapshots. F18 betrifft Klickdummy-Parity-Tests, nicht diesen Lauf. |

## Maintainer 2028

Sieht ein Skill-File, ein Issue-Template, und in fuenf Zielrepos je einen
`docs/retros/ux-review-*.md`. Fragt: „Wurde je ein Gate daraus?" — die Antwort
steht in der Kill-Gate-Tabelle unten, nicht in Prosa. Findet er dort nur
`offen`, ist das Konzept per `review_by` abgelaufen und der Skill zu loeschen.
Was er **nicht** finden soll: einen zweiten Kriterienkatalog neben ADR-251, oder
Screenshots mit Kundendaten in einem oeffentlichen Repo (R4).

## Alternativen

| # | Alternative | Warum nicht (jetzt) |
|---|---|---|
| ALT-1 | **Nur die Klassen-Tests flottenweit ausrollen** (`test_erreichbarkeit_screens.py`, Kommentar-Test, `htmx:responseError`) ohne Agenten | Richtig und unabhaengig davon zu tun (eigenes Issue). Deckt aber nur die **bekannten** Klassen; die naechste unbekannte findet wieder nur ein Tresen-Gang. Kein Ersatz, sondern Voraussetzung: der Agent darf Bekanntes nicht neu melden. |
| ALT-2 | **Stagehand/BrowserUse als freier Explorer** statt kettengebundenem Skill | LLM-natives `page.act` erkundet breiter, aber ohne Kette gibt es kein „Station erreicht" und damit kein messbares Abbruchkriterium (Step 2a Frage 6). Fuer Stufe 2 als Erweiterung denkbar, wenn Stufe 1 die Kettenform belegt hat. |

## Top-3-Risiken

1. **R1 Prosa-Gate** — der Agent meldet, niemand baut den Test. Messpunkt: Kill-Gate Zeile 3.
2. **R4 Personendaten im Screenshot** — Pilot nur mit synthetischen Mandanten; Issues nur im privaten Zielrepo.
3. **R2 Login-Huerde** — der Pilot scheitert an CF-Access und wird still zu „URL-Liste abfahren" (D3). Gegenmittel: `blind` mit Grund ist ein zulaessiger Ausgang, „begehbar" ohne Klickpfad nicht.

## Kill-Gate + Threshold

Frist **2026-09-30**, Exception-Budget: eine Verlaengerung um 14 Tage, wenn der
Pilot an R2 (Login) haengt und das dokumentiert ist.

| Kriterium | Status | Beleg |
|---|---|---|
| K1 Positivkontrolle: >= 7 der 9 bekannten Defekte (writing-hub 3, ausschreibungs-hub 6) wiedergefunden am Stand vor den Fixes | offen | — |
| K2 Fehlbefund-Quote <= 30 % ueber alle Pilot-Issues (Owner-Urteil je Issue) | offen | — |
| K3 Mindestens ein Klassen-Gate-Vorschlag aus dem Pilot als Test gebaut, der einen **zweiten** Fall faengt | offen | — |
| K4 Jede getippte URL im Pilot erscheint als Befund im Bericht (D3-Probe) | offen | — |
| K5 Kein Screenshot mit Personendaten ausserhalb des Zielrepos (R4-Probe: grep der PR-Diffs in platform) | offen | — |

Alle fuenf erfuellt -> Stufe 2 als ADR (Dienst in dev-hub/apps, Zeitplan, eigener
Bot-Token, Dry-Run in CI). Eines verfehlt -> Stufe 1 bleibt manuell aufrufbar,
Stufe 2 wird nicht gebaut; zwei verfehlt -> `sunset`.

## Bezug

- Memory `project_ux_review_agent_program` (C1) — Owner-Prio 2026-07-22, wird durch dieses Dokument abgeloest
- Retro writing-hub fdd368 (C2, #2325) — drei Defekte, ein Fehlbefund, eine geteilte `.env`
- Outline „Sechs Befunde, die nur ein Browser sehen konnte" (C3) — vier Regeln, fuenf Gates
- `/kd-review` (C6), ADR-251 (C7) — das Gate davor
- `policies/platform-agents.md` — Ort fuer Stufe 2
- #2253 — Kill-Gate vor der ersten Zahl pre-registrieren
- ALT-1 als eigenes Issue: [#2326](https://github.com/achimdehnert/platform/issues/2326) — Klassen-Tests flottenweit (risk-hub, billing-hub, weltenhub, bfagent)
