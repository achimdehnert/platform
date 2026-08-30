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
  - {claim_id: C10, source_path: "writing-hub/klickdummy/roman-autoren-spine/spec.yaml", commit_or_pr: "main 2026-08-26", opened_in_session: true}
  - {claim_id: C11, source_path: "writing-hub AGENT_HANDOVER.md — Stand 2026-08-26", commit_or_pr: "#778", opened_in_session: true}
  - {claim_id: C12, source_path: docs/adr/ADR-211-spec-zentrierte-klickdummies.md, commit_or_pr: "accepted", opened_in_session: true}
  - {claim_id: C13, source_path: docs/konzepte/KONZ-platform-007-adr-handoff-extern-automation.md, commit_or_pr: "pipeline_status sunset 2026-07-24 — review_by verstrichen, 0 --auto-Laeufe", opened_in_session: true}
  - {claim_id: C14, source_path: "~/.claude/policies/llm-routing.md", commit_or_pr: "Tierliste, Anbieter-Messung 2026-08-25", opened_in_session: true}
  - {claim_id: C15, source_path: "~/github/chat-hub/README.md", commit_or_pr: "main ad0bf1b", opened_in_session: true}
created: 2026-08-25
updated: 2026-08-30
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
| E10 | **Klickdummy als Soll-Gegencheck** (`-kd <name>`, optional): existiert eine KD-Spec zur Kette, wird sie in **beide** Richtungen abgeglichen — KD-Screen ohne App-Weg und App-Station ohne KD-Screen. Der Befund ist der **Dissens**, nie „die App ist falsch" | Entscheidung | C10: `roman-autoren-spine` spezifiziert 6 Screens, der reale Durchlauf hatte 7 Phasen — „Serien-Zuordnung" nie berührt, „Welt & Figuren"/„Recherche" im KD unbekannt. Alternative: KD als Wahrheit setzen (= Fehlalarm bei jedem gewachsenen Feature, R5) | gesetzt |
| E11 | **Inhaltliche Prüfung = Durchgängigkeit, nicht Qualität.** Ein Eigenname aus Station 1 wird in jeder Folgestation gesucht, plus ein Kontrollmarker, der 0 ergeben MUSS | Entscheidung | C11: Protagonist hiess im Konzept „Milo Heller", in der erzeugten Gliederung „Franz" — HTTP-grün, inhaltlich gerissen. Alternative: Textqualität bewerten (= Geschmacks-Issues, R3) | gesetzt |
| E12 | **Blaupause statt Einzelwerkzeug**: der Skill nennt keine repo-spezifischen Pfade; Kette, KD-Name und Marker kommen als Parameter. Ein neues Repo braucht keine Skill-Änderung | Entscheidung | Owner-Weisung 2026-08-26. Alternative: je Repo eine Kopie (= Drift zwischen Kopien, dieselbe Klasse wie `skill-copy-not-redistributed`) | gesetzt |
| R5 | **KD veraltet → Fehlalarm.** Ein KD, der einer gewachsenen App hinterherhinkt, erzeugt bei jedem Lauf dieselben Dissense | Risiko | Gegenmittel: Dissens hat zwei Severities — `spec-luecke` (KD kennt die Station nicht) ist `optimierung`, `weg-fehlt` (KD-Screen ohne App-Weg) ist `fehler`. Zählt K2 mit; > 30 % `spec-luecke` über drei Läufe = der KD gehört gepflegt, nicht der Agent geschärft | offen, Pilot |
| R6 | **Marker verfälscht das Ergebnis.** Ein Eigenname, den der Autor nie schreiben würde, verzerrt die Erzeugung | Risiko | Gegenmittel: Marker sind plausible Eigennamen im Genre, kein `ZZZ-TEST`. Der Kontrollmarker (der 0 ergeben muss) ist die Gegenprobe gegen einen Filter, der nie etwas findet | offen, Pilot |
| R4 | Testdaten aus Prod im Screenshot (Personendaten, platform ist public) | Risiko | Screenshots nur ins Zielrepo-Issue (privat), nie nach platform; Pilot mit synthetischen Mandanten | offen |
| E13 | **Der Gegenpart falsifiziert, er produziert nicht.** Eingabe ist ein fertiger Befund des Laufs, Ausgabe ein Spruch `bestaetigt` / `widerlegt` / `unklar` mit Begruendung. Er darf keinen eigenen Befund eroeffnen | Entscheidung | Die belegte Schwaeche ist der Fehlbefund (C2 #760), nicht Befundmangel — 12 echte Befunde in drei Repo-Tagen. Alternative: zweiter Produzent (= A3-Quote steigt, K2 kippt) | gesetzt |
| E14 | **Modell: andere Familie, Rung T1a** (`groq/openai/gpt-oss-120b`). Der Ertrag ist die andere Trainingsfamilie, nicht die Rung; T4/T5 erst, wenn T1a an Instruktionstreue scheitert | Entscheidung | C14: Frontier-Rung braucht einen benannten Grund, „anderer Anbieter" allein ist keiner **Gemessen 2026-08-30 (A/B, Owner-Freigabe):** derselbe 11er-Korpus gegen `gpt-5.6-terra` und `gpt-5.5`, je drei Laeufe. Das **neueste** Modell faellt durch K9 — `gpt-5.6-terra` gab dem belegten Produktdefekt W3 (writing-hub#762) mehrheitlich `widerlegt`, also R7. `gpt-5.5` war als einziges vollstaendig einig (11/11), bestand K9, ist aber **dieselbe Trainingsfamilie** wie `gpt-oss-120b` — kein Unabhaengigkeits-Gewinn. Dazu: die Pro-Stufe laeuft nicht auf `v1/chat/completions`, und Frontier laesst `temperature: 0` nicht zu. Beleg: [#2489](https://github.com/achimdehnert/platform/issues/2489#issuecomment-5467876788) | gesetzt, 2026-08-30 gegen Frontier gemessen |
| E15 | **Ausgabe auf die Leseflaeche, nicht in einen Raum:** Kommentar am bestehenden Befund-Issue im Zielrepo, plus Feld `falsifikator:` im Sammel-Issue. Kein eigenes Issue, kein PR, kein Chat | Entscheidung | Tracking-Artefakt-Regel; C13: der externe Kanal war gebaut und blieb ungenutzt | gesetzt |
| E16 | **Rohzahl bleibt massgeblich:** K1 und K2 zaehlen den ungefilterten Lauf; der Spruch ist eine zweite Spalte, nie eine Subtraktion | Entscheidung | Der Start am 01.09. liegt **im** laufenden Kill-Gate (Frist 30.09.). Ohne diese Regel misst das Gate ab dem 01.09. ein anderes Werkzeug als am 25.08. | gesetzt |
| E17 | **Kein Bild, keine Echtdaten an den Gegenpart:** uebergeben werden Befundtext und Evidenz-Auszuege aus Laeufen mit synthetischen Mandanten; Repos mit echten Daten sind ausgeschlossen | Entscheidung | R4; T1a laeuft bei einem US-Anbieter (C14) — der Souveraenitaets-Schnitt liegt an der Eingabe, nicht an einer Zusicherung | gesetzt |
| R7 | **Der Gegenpart wird zum Filter** und drueckt echte Befunde weg | Risiko | Gegenmittel: K9 (Gegenprobe an den 9 bekannten Defekten) und E16. Ein `widerlegt` auf einen bekannten echten Defekt ist ein Fehler des Gegenparts, kein Fehler des Laufs. **Eingetreten 2026-08-30, Lauf 2:** F3 (`submission_workflow` unbegehbar, im Browser mit getippter URL belegt) kam als `widerlegt` zurueck — die Gegenprobe war als Satz formuliert („nur `tests/test_route_coverage.py`"), und der Gegenpart las das als Treffer. Der Befund stand trotzdem (E16). **Nachtrag 2026-08-30 (K9-Gegenprobe):** derselbe Datensatz liefert dieses `widerlegt` nur in **einem von drei** Laeufen — E18 beseitigt nicht einen sicheren Fehler, sondern die Mehrdeutigkeit, die ihn moeglich macht (R9) | belegt, Gegenmittel E18 |
| E18 | **Das Feld `gegenprobe` traegt eine Zahl, keinen Bericht.** Erst der Zaehler (`0 Treffer`), dann optional der Satz dahinter | Entscheidung | R7-Realfall oben: dieselbe Tatsache als Satz fuehrte zum falschen Spruch, als Zahl nicht. Alternative: Prompt haerten (= dieselbe Mehrdeutigkeit, nur eine Ebene tiefer) | gesetzt 2026-08-30 |
| E20 | **Der Nenner bleibt 9** — korrigiert wird die Messung, nicht das Kriterium (Owner 2026-08-30, Weg A) | Entscheidung | Die Alternative waere gewesen, den Nenner auf die tatsaechlich reproduzierbaren Defekte zu senken. Das haette die Latte **nach dem Wurf** verschoben, und zwar zugunsten des Werkzeugs, ueber dessen Weiterbau das Gate entscheidet. Wer sein eigenes Kriterium nachtraeglich senkt, misst nichts mehr. Belegt in [#2474](https://github.com/achimdehnert/platform/issues/2474) | gesetzt 2026-08-30 |
| E19 | **Ein Stichtag ist kein Stand.** Die Positivkontrolle laeuft je Defekt gegen den Commit **vor seinem eigenen Fix**, nicht gegen einen Tagesstand | Entscheidung | Realfall 2026-08-30: `8c8090e` wurde als „vor den Fixes vom 25.08." gewaehlt, enthielt aber zwei davon bereits (`docx`-Extraktor registriert, `docx`-Extra in `pyproject.toml`). Zwei Defekte konnten dort nicht auftreten und wurden als „nicht gefunden" gezaehlt — der Nenner war falsch, nicht der Agent. Alternative: pro Repo ein Tagesstand (= genau dieser Fehler) | gesetzt 2026-08-30 |
| R8 | **Eine Station, die sich nur aus einer externen Quelle fuellt, ist klick-only nicht begehbar** — und die Defekte dahinter sind fuer den Lauf unsichtbar | Risiko | Gemessen ausschreibungs-hub 2026-08-30: drei der sechs bekannten Defekte (CSRF an „Analyse starten", `.docx` als ZIP-Rohbytes, eine Meldung fuer drei Ursachen) liegen hinter dem Portal-Abruf der Vergabeunterlagen; die Upload-Tuer daneben weist `.docx` serverseitig ab (`ALLOWED_MIME_TYPES`, `apps/submission_workflow/views.py:110`). Gegenmittel **gebaut 2026-08-30** ([ausschreibungs-hub#285](https://github.com/iilgmbh/ausschreibungs-hub/pull/285)): `PortalAusAufzeichnung` traegt dieselbe Schnittstelle wie der echte Adapter und liest das Archiv von der Platte, `fetch_vergabeunterlagen --aufzeichnung`. Ersetzt wird nur der erste Schritt; Entpacken, Ingest und Extraktion sind derselbe Code. Ob die zwei Defekte hinter der Tuer damit wieder auftreten, ist **noch nicht gemessen** — das entscheidet der naechste Lauf gegen die Staende aus E19 **Nachweis erbracht 2026-08-30:** mit aufgesetzter Aufzeichnung traten **beide** Defekte hinter der Tuer wieder auf (`.docx` als ZIP-Rohbytes an `2259b8e`, Sammelmeldung an `dbf86ce`). Ohne sie waeren sie unerreichbar geblieben — R8 ist damit belegt **und** entschaerft | belegt, Gegenmittel wirksam |
| E21 | **Die Aufzeichnung wird auf den Stand aufgesetzt, nicht der Stand auf die Aufzeichnung gehoben.** Ersetzt werden nur die beiden Netz-Methoden des Adapters (`_sitzung_und_zip_link`, `_archiv_holen`); Entpacken, Ingest und Extraktion bleiben der Code des Standes | Entscheidung | Gemessen 2026-08-30: ein Cherry-pick von [ausschreibungs-hub#285](https://github.com/iilgmbh/ausschreibungs-hub/pull/285) ist an den E19-Staenden **nicht** moeglich — der dortige Adapter importiert `archiv_entpacken`, eine Funktion, die am 25.08. noch eine Methode (`_entpacken`) war. Der Cherry-pick haette genau den Code getauscht, den die Messung prueft | gesetzt 2026-08-30 |
| R9 | **Der Spruch ist nicht reproduzierbar** — derselbe Befund kann in zwei Laeufen zwei Sprueche bekommen | Risiko | Gemessen 2026-08-30 bei der K9-Gegenprobe: 11 Datensaetze x 3 Laeufe bei `temperature: 0`, **zwei kippten** (W2 zwischen `bestaetigt` und `unklar`, die E18-Kontrolle zwischen `widerlegt` und `bestaetigt`). Solange E16 gilt, trifft das keine Gate-Zahl — eine spaetere Verdrahtung als Gate stuende auf einem Wurf. Optionen A/B/C in [#2489](https://github.com/achimdehnert/platform/issues/2489) | Gegenmittel E20 gebaut 2026-08-30 |
| E20 | **Der Spruch ist eine Mehrheit aus drei Laeufen, kein Wurf.** Das Werkzeug fragt dreimal und gibt `laeufe`, `einig` und die Einzelsprueche aus; drei verschiedene Sprueche ergeben `unklar` | Entscheidung | Option B aus [#2489](https://github.com/achimdehnert/platform/issues/2489) (Owner 2026-08-30). Alternative A (nur Mehrheit) haette dieselben Kosten und verschwiege, dass der Gegenpart schwankt — genau die Information, die man vor einer Gate-Verdrahtung braucht. Alternative C (nichts tun) laesst einen Wurf wie ein Urteil aussehen | gesetzt 2026-08-30 |

## MVC (Stufe 1)

| Was | Wo | Inhalt |
|---|---|---|
| Skill | `platform/.windsurf/workflows/ux-review.md` (Verteilung via cc-skill-dist) — **gebaut 2026-08-25** | Phasen: (0) Umgebung E5 · (1) Einstieg = Startseite nach Login, ab dann Klick-only E1 · (2) je Station: Snapshot, Konsole, Netzwerk E6 · (3) Urteil: Befund/OK/blind E4 · (4) Absenz-Gegenprobe E2 · (5) Issue je Befund E3 · (6) Bericht |
| Issue-Schema | **im Skill** (Step 6) — *Abweichung 2026-08-25 beim Bau:* ein platform-Issue-Template gaelte nur fuer Issues in platform, die Issues landen aber im Zielrepo (Doppelquelle, D1) | Felder: Kette/Station · Screenshot · Antwortkoerper · Repro · Severity · **Klassen-Gate-Vorschlag** (Pflicht) · Gegenprobe (E2, Pflicht bei Absenz) |
| Bericht | stdout + **Sammel-Issue** `[ux-review] <repo> · <kette> · <datum>` im Zielrepo — *Abweichung 2026-08-25:* eine Datei im Zielrepo braeuchte einen PR, den E3 ausschliesst | drei Zustaende je Station, Zaehler: Befunde / OK / blind / bekannt; Owner labelt Fehlbefunde (`fehlbefund`) → K2 |
| Positivkontrolle | Pilot-Lauf gegen writing-hub `git checkout <sha vor #761>` und ausschreibungs-hub vor dem Erreichbarkeits-Fix | Trefferliste gegen die 9 bekannten Defekte |
| Gate-Katalog (Vorschlaege, die der Agent kennt) | im Skill | Routen-vs-Templates (C4) · mehrzeilige Django-Kommentare ueber alle Templates (C3) · `htmx:responseError` global (C5) · `hx-headers` CSRF am body (C3) · Invariante ueber Datenbestand statt Ursache (C3 Regel 3) · escapejs-Familie (C2) |

### MVC-Ergaenzung 2026-08-26

| Was | Wo | Inhalt |
|---|---|---|
| `-kd <name>` | Skill, neuer optionaler Parameter | Laedt `klickdummy/<name>/spec.yaml` des Zielrepos, zieht die Screen-Titel, gleicht sie gegen die besuchten Stationen ab. Zwei Befundklassen: `weg-fehlt` (`fehler`) und `spec-luecke` (`optimierung`) |
| `-marker <name>[,<name>]` | Skill, neuer optionaler Parameter | Eigennamen, die in Station 1 eingegeben und in jeder Folgestation gesucht werden; zusaetzlich ein fest eingebauter Kontrollmarker, der 0 ergeben muss |
| Step 3b Gegenrichtung | Skill, bereits gebaut (PR #2343) | URL-Namen ohne Template-Referenz; je Treffer einhaengen ODER entfernen |
| Klassen `built-but-never-called`, `sichtbar-nur-unter-falscher-bedingung`, `gemockt-und-deshalb-blind` | Skill, Klassentabelle (PR #2343) | je mit Gate-Vorlage und Realfall |
| Hook `gui-geaendert-ohne-klick` | `tools/claude-hooks/`, gebaut + gemergt (PR #2344) | Stop-Hook: GUI-Datei geschrieben, aber kein Browser-Werkzeug und kein `/ux-review` in der Sitzung. Advisory. |

**Ausfuehrungsform (Step 2a):** mehrere Schritte ja; Schrittfolge steht fest
(Kette) — innerhalb einer Station entscheidet der Agent den naechsten Klick zur
Laufzeit; Stationen sequenziell (jede haengt vom Zustand der vorigen ab); keine
Barriere; kein Graph. **Schleife nur innerhalb einer Station**, Abbruch
messbar: Station erreicht ODER 25 Klicks ohne neue Seite -> Zustand `blind` mit
Grund. Budget je Lauf: eine Kette, deklariert vor dem Start.

## Erweiterung 2026-08-26 — Blaupause statt Einzelwerkzeug

**Owner-Weisung:** generisch, „als Blaupause für GUI-Tests", entlang der vier
Prinzipien-Anker. Was jeder davon hier konkret bedeutet — keiner ist Dekoration:

| Prinzip | Was er in diesem Konzept erzwingt | Woran man sieht, dass er wirkt |
|---|---|---|
| **Continuous Improvement** | Der Gate-Katalog wächst aus Befunden, nicht aus Vorausdenken. Jeder bestätigte Befund liefert einen Klassen-Gate-Vorschlag (E3, Pflichtfeld); gebaute Gates zählt die Retro. | Katalog-Länge über Läufe. Wächst er nicht, ist A2 falsifiziert (Kill-Gate). |
| **Predictive Maintenance** | Der KD-Gegencheck (E10) meldet Drift **bevor** ein Nutzer stolpert: ein spezifizierter Screen ohne Weg ist ein Defekt, den noch niemand erlebt hat. | Anteil `weg-fehlt`-Befunde, die **vor** der ersten Nutzermeldung entstehen. |
| **Out-of-the-box** | Drei Blickrichtungen statt einer: Kette von vorn (E1), Code → Oberfläche (Step 3b), Spec → Oberfläche (E10). Jede findet, wofür die anderen strukturell blind sind. | Befunde je Richtung. Findet eine Richtung über drei Läufe nichts, wird sie gestrichen — nicht behalten, weil sie schön klingt. |
| **Advocatus Diabolus** | Unten als eigener Abschnitt, mit der Frage, die das Konzept kippen könnte. | Jede Erweiterung trägt ihren stärksten Einwand im Dokument, nicht im Kopf des Autors. |

### Die SSoT-Frage, ausdrücklich beantwortet

ADR-211 setzt: **Spec = System of Record, der Klickdummy rendert sie, der
Parity-Test ist das Konformitäts-Gate** (C12). Ein KD-Gegencheck schafft damit
**keine** zweite Wahrheit — er liest die vorhandene.

Aber er darf sie nicht als Urteil lesen. Gemessen an writing-hub (C10):
`roman-autoren-spine` kennt sechs Screens, der reale Durchlauf hatte sieben
Phasen. „Welt & Figuren" und „Recherche" fehlen im KD — die App ist deshalb
nicht falsch, der KD ist älter. Umgekehrt kennt der KD „Serien-Zuordnung", und
die war im ganzen Durchlauf nie sichtbar.

Daraus folgt die Trennung in E10: **der Befund ist der Dissens**, und er hat
zwei Severities. `weg-fehlt` (KD-Screen ohne App-Weg) ist ein Fehler — das ist
die Klasse `built-but-never-called`, die 2026-08-26 fünfmal an einem Tag auftrat.
`spec-luecke` (App-Station ohne KD-Screen) ist eine Optimierung und trifft
den KD, nicht die App.

Ein Werkzeug, das automatisch „App falsch" sagt, wäre bei jedem gewachsenen
Feature ein Fehlalarm — und würde nach dem dritten abgeschaltet (R5).

### Warum inhaltlich = Durchgängigkeit und nicht Qualität

Der teuerste Defekt des writing-hub-Durchlaufs war keiner, den HTTP sieht: der
Protagonist hiess im Konzept „Milo Heller", in der daraus erzeugten Gliederung
„Franz" (C11). Jede Station war grün, die Kette inhaltlich gerissen.

Das ist messbar — aber nur als **Durchgängigkeit**: ein Eigenname aus Station 1
wird in jeder Folgestation gesucht. Nicht messbar ist „ist der Text gut". Wer
das versucht, produziert Geschmacks-Issues (R3, bereits belegt).

Der Kontrollmarker ist dabei kein Beiwerk: ein Suchlauf, der nie etwas findet,
ist von einem kaputten Suchlauf nicht zu unterscheiden. Er **muss** 0 ergeben,
und dass er 0 ergibt, ist Teil des Belegs.

## Advocatus Diabolus — Erweiterung 2026-08-26

**Der stärkste Einwand: der KD-Gegencheck misst zwei veraltete Dinge gegeneinander.**
Ein Klickdummy ist ein Anforderungsartefakt aus der Planungsphase. Die App
wächst. Nach sechs Monaten ist der Dissens der Normalzustand, nicht der Befund —
und ein Werkzeug, das den Normalzustand meldet, wird ignoriert. Genau so sind
die fünf `[deploy-health]`-Issues in platform verrottet.

*Antwort:* deshalb `-kd` **optional** und die Severity-Trennung in E10. Ein Lauf
ohne KD verliert nichts von seiner Kernleistung. Und R5 hat eine harte Schwelle:
über 30 % `spec-luecke` in drei Läufen heisst, dass der KD gepflegt gehört —
das ist dann der Befund, nicht die Liste der Dissense.

**Zweiter Einwand: drei Blickrichtungen sind drei Gelegenheiten für Fehlalarme.**
Jede zusätzliche Richtung erhöht die Fehlbefund-Quote, und A3 sagt: über 30 %
kostet der Agent mehr Owner-Zeit als er spart.

*Antwort:* die Quote ist bereits das Kill-Kriterium (K2). Die Erweiterung ändert
die Schwelle nicht, sie muss sie **halten** — mit mehr Richtungen. Hält sie
nicht, fällt die schwächste Richtung raus, nicht die Schwelle.

**Dritter Einwand: „Blaupause" ist ein Wort, kein Mechanismus.** Ein Skill wird
generisch, weil jemand die repo-spezifischen Pfade herausnimmt — und unspezifisch,
sobald der erste Sonderfall hineingeschrieben wird.

*Antwort:* E12 ist als Invariante formuliert und im Kill-Gate messbar (K5): der
Skill darf keinen Repo-Namen tragen. Das ist per `grep` prüfbar, nicht per Meinung.

## Erweiterung 2026-08-30 — Falsifikator-Gegenpart (Stufe 1b)

**Owner-Entscheidung 2026-08-30: Start 2026-09-01**, also im laufenden Kill-Gate.
Anlass war die Frage, ob ein zweites System — Vorbild SB-Neu (Ilja Lerch), eigenes
Modell bei einem anderen Anbieter — als Gegenpart taugt und ueber Element-X
angebunden werden sollte. Uebernommen wird davon die **Unabhaengigkeit des
Urteils**; nicht uebernommen wird der **eigene Kanal**.

Die Richtung folgt aus der Befundlage, nicht aus der Idee: in drei Repo-Tagen
standen 12 echte Befunde **einem** Fehlbefund gegenueber (#760, „Feld fehlt" aus
leerem DOM, C2). Ein zweiter Produzent verbessert eine Zahl, die nicht das
Problem ist, und verschlechtert die, die es ist — K2 liegt bei 30 %. Der
Gegenpart wird deshalb Pruefer, nicht Autor (E13).

| Was | Wo | Inhalt |
|---|---|---|
| Step 5b Falsifikation | Skill `.windsurf/workflows/ux-review.md` | je Befund ein Call: Eingabe = Befundtext + mitgelieferte Evidenz (Antwortkoerper-Auszug, Gegenprobe aus E2, Severity-Referenz); Ausgabe = Spruch + Begruendung |
| Feld `falsifikator:` | Sammel-Issue (Step 6) | zweite Spalte neben dem Rohbefund; K1/K2 zaehlen die Rohspalte (E16) |
| Umsetzung | [#2466](https://github.com/achimdehnert/platform/issues/2466) — gebaut 2026-08-30 | `tools/ux_falsifikator.py`, 15 Tests, Dogfood-Test 5 im Skill |

*Abweichung beim Bau 2026-08-30* (wie schon 2026-08-25 hier nachgetragen): E15 sagt
„Kommentar am Befund-Issue"; gebaut wurde der Spruch als **Feld im Issue-Rumpf** (Step 6).
Dieselbe Leseflaeche, ein Artefakt statt zwei — und der Spruch steht dort, wo der Owner das
Label `fehlbefund` setzt. Der zweite Teil von E15 (Spalte und Zaehler im Sammel-Issue)
bleibt unveraendert.

*Beim Bau gemessen, nicht vermutet (E14):* der erste echte Lauf gegen Groq lieferte
`HTTP 403 error code: 1010`. Das ist Cloudflare vor dem Anbieter, das die urllib-Vorgabe als
Bot abweist — **kein** ungueltiger Schluessel. Derselbe Schluessel mit gesetzter
`User-Agent`-Kennung liefert 200. Im Werkzeug und in einem Test festgehalten, weil die
Meldung wie ein Berechtigungsproblem aussieht und genau dorthin fehlleitet.

### Warum nicht Element-X

| # | Grund | Beleg |
|---|---|---|
| 1 | Ein Raumverlauf ist keine Leseflaeche — der Befund muss dort stehen, wo ohnehin gelesen wird | Tracking-Artefakt-Regel; E15 |
| 2 | Ein Bot im E2EE-Raum braucht eigene Device-Verifikation und Key-Pflege; E2EE lebt im Client | C15 |
| 3 | Zwei redende Agenten bilden strukturell einen zweiten Kommandokanal | Lotsen-Charta Art. 1 |
| 4 | chat-hub ist ein Produkt fuer Menschen (Wire/Threema-Analogon), keine Agenten-Infrastruktur | C15 |

Element-X als **Push an den Owner** (Freigabe vom Telefon) ist davon unberuehrt und
bleibt offen. Es aendert Charta-Artikel 1 und ist damit selbstbetreffend — es
gehoert in ein eigenes Konzept mit Vorlage an den Owner, nicht hierher.

### Warum das nicht endet wie KONZ-007

KONZ-007 hat denselben Gedanken schon einmal gebaut: Briefing, Souveraenitaets-Gate,
**ein** externer Call, Antwort als `.md`. Nach vier Wochen null Aufrufe, Kill-Gate
gezogen, `sunset` (C13). Der Unterschied ist nicht der Anbieter und nicht der
Transport, sondern die Stelle: dort war der Call ein **eigener Pfad, den jemand
aufrufen musste**, hier ist er **Schritt 5b eines Laufs, den man ohnehin startet**.
Wer `/ux-review` aufruft, ruft ihn mit. Faellt die Nutzung trotzdem auf null,
faellt K9 — und mit ihm der Gegenpart, einzeln.

### Advocatus Diabolus — Erweiterung 2026-08-30

**Ein T1a-Modell ist schwaecher als der Produzent; ein schwaecherer Pruefer
widerlegt das Falsche.** *Antwort:* er prueft nicht die Sachfrage, sondern
mechanische Eigenschaften des Befunds — liegt zu einer Absenz-Behauptung die
Gegenprobe aus E2 vor, deckt der zitierte Antwortkoerper die Aussage, traegt eine
`optimierung` ihre Referenz (R3). Das sind Pruefungen gegen **mitgelieferte**
Evidenz, nicht gegen Weltwissen. Genau daran misst K9.

**Der Start im laufenden Gate verfaelscht die Messung.** *Antwort:* ja — deshalb
E16. Gemessen wird der ungefilterte Lauf; der Spruch laeuft als zweite Spalte mit.
Damit liegen am 30.09. beide Zahlen vor, die rohe und die gefilterte, und K1/K2
bleiben mit dem Stand vom 25.08. vergleichbar.

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
| ALT-3 | **Gegenpart ueber Element-X / chat-hub als Agent-zu-Agent-Bus** | Loest den Transport; der Engpass war nie der Transport (C13: Kanal gebaut, 0 Laeufe). Dazu die vier Gruende in der Erweiterung 2026-08-30. Als Push-Kanal an den **Menschen** separat denkbar — dann eigenes Konzept mit Charta-Vorlage, weil Artikel 1 beruehrt wird. |

## Top-3-Risiken

1. **R1 Prosa-Gate** — der Agent meldet, niemand baut den Test. Messpunkt: Kill-Gate Zeile 3.
2. **R4 Personendaten im Screenshot** — Pilot nur mit synthetischen Mandanten; Issues nur im privaten Zielrepo.
3. **R2 Login-Huerde** — der Pilot scheitert an CF-Access und wird still zu „URL-Liste abfahren" (D3). Gegenmittel: `blind` mit Grund ist ein zulaessiger Ausgang, „begehbar" ohne Klickpfad nicht.

## Kill-Gate + Threshold

Frist **2026-09-30**, Exception-Budget: eine Verlaengerung um 14 Tage, wenn der
Pilot an R2 (Login) haengt und das dokumentiert ist.

| Kriterium | Status | Beleg |
|---|---|---|
| K1 Positivkontrolle: >= 7 der 9 bekannten Defekte (writing-hub 3, ausschreibungs-hub 6) wiedergefunden **je am Commit vor dem eigenen Fix** (E19) | **erfuellt 2026-08-30 (8/9)** | writing-hub 3/3 am 2026-08-25, Stand 493dc19 — writing-hub#767. ausschreibungs-hub **5 von 6** am 2026-08-30 gegen die E19-Staende, mit aufgesetzter Portal-Aufzeichnung (Weg 1, Owner): `f1f600c` mehrzeiliger `{# #}` auf zwei Seiten **und** CSRF-403 an „Analyse starten" (Antwortkoerper: `CSRF token missing`); `dbf86ce` 18 Routen ohne Template-Verlinkung (darunter `angebote:review` und `document_intelligence:vergabe-analyse`, beide Kontrollen halten) **und** die Sammelmeldung „Alle Extraktions-Calls sind gescheitert." im Browser, waehrend die Ursache nur im Audit-Trail steht; `2259b8e` `.docx` als ZIP-Rohbytes (`text` beginnt mit `PK\x03\x04`, 973 Zeichen). **Nicht reproduzierbar: das fehlende `docx`-Extra** (`e6ee77c`) — ein Deklarationsdefekt in `pyproject.toml`, den eine Laufzeitumgebung mit installierter Abhaengigkeit per Konstruktion nicht zeigt; das fand CI, und kein Browser-Lauf kann es. Beleg: [#2474](https://github.com/achimdehnert/platform/issues/2474) |
| K2 Fehlbefund-Quote <= 30 % ueber alle Pilot-Issues (Owner-Urteil je Issue) | **erfuellt 2026-08-30 (0 von 1)**, Basis duenn | Genau **ein** neu angelegtes Pilot-Issue: [writing-hub#766](https://github.com/achimdehnert/writing-hub/issues/766). Urteil vom Owner in der Sitzung delegiert und deshalb **nachgeprueft statt uebernommen**: der Anhang `verdrahtet:` liest frisch aus der DB (`llm_router.py:143-147`), aifw haelt die Konfiguration bis 600 s im geteilten Cache (`aifw/service.py:83-85`) — die Meldung liest nachweislich eine andere Quelle als der Aufruf. **Kein** `fehlbefund`-Label. Vorbehalt: eine Quote ueber einen einzigen Nenner ist erfuellt, aber nicht belastbar — die uebrigen Laeufe waren Trockenlaeufe oder meldeten Bekanntes nicht neu | 
| K3 Mindestens ein Klassen-Gate-Vorschlag aus dem Pilot als Test gebaut, der einen **zweiten** Fall faengt | offen | Vorschlag liegt in writing-hub#766 (Meldung liest dieselbe Quelle wie der Aufruf; Reseed invalidiert Cache) |
| K4 Jede getippte URL im Pilot erscheint als Befund im Bericht (D3-Probe) | erfuellt (Lauf 1) | 0 getippte URLs, Kette komplett per Klick — writing-hub#767 |
| K5 Kein Screenshot mit Personendaten ausserhalb des Zielrepos (R4-Probe: grep der PR-Diffs in platform) | erfuellt (Lauf 1) | keine Screenshots erzeugt; synthetischer Nutzer, Stack mit Volumes geloescht |
| **K6** (Erweiterung 26.08.) Blaupause haelt: `grep -icE 'writing-hub\|ausschreibungs-hub\|meiki\|risk-hub' .windsurf/workflows/ux-review.md` findet **nur** Zeilen, die als Realfall-Beleg gekennzeichnet sind — kein Repo-Name in einer Anweisung | offen | per `grep` pruefbar, nicht per Meinung (E12) |
| **K7** (Erweiterung 26.08.) KD-Gegencheck traegt: in mindestens einem Pilot-Lauf mit `-kd` entsteht ein `weg-fehlt`-Befund, den der Klick-Durchlauf allein **nicht** gefunden hat | offen | Gegenprobe zur Frage, ob die dritte Blickrichtung eigenen Ertrag hat (OOTB-Prinzip: findet sie nichts, wird sie gestrichen) |
| **K8** (Erweiterung 26.08.) Marker-Durchgaengigkeit traegt: der Kontrollmarker ergibt in **jedem** Lauf 0, und mindestens ein echter Marker-Riss wird gefunden | offen | ohne den ersten Teil ist der Suchlauf womoeglich der Filter; ohne den zweiten hat E11 keinen belegten Ertrag (C11 ist der bekannte Fall) |
| **K9** (Erweiterung 30.08.) Gegenpart traegt: er markiert mindestens einen Fehlbefund der #760-Klasse `widerlegt` und **keinen** der 9 bekannten echten Defekte | **erfuellt 2026-08-30** | Gegenprobe an 11 Datensaetzen (9 echte Defekte + 1 Fehlbefund der #760-Klasse + 1 E18-Kontrolle), je **drei** Laeufe gegen `openai/gpt-oss-120b`: Fehlbefund **3/3 `widerlegt`**, ueber 27 Sprueche zu den echten Defekten **kein einziges `widerlegt`** (W2 zweimal `bestaetigt`, einmal `unklar`). Grenze der Messung: die Befund-Datensaetze sind aus den Issue-Texten und #2470 **rekonstruiert**, nicht aus einem frischen Browser-Lauf. Belege: [#2466](https://github.com/achimdehnert/platform/issues/2466#issuecomment-5467768881) — neu offen daraus: R9 |

Alle neun erfuellt -> Stufe 2 als ADR (Dienst in dev-hub/apps, Zeitplan, eigener
Bot-Token, Dry-Run in CI). Eines verfehlt -> Stufe 1 bleibt manuell aufrufbar,
Stufe 2 wird nicht gebaut; zwei verfehlt -> `sunset`.

**K6-K9 fallen einzeln, nicht als Block.** Verfehlt nur K7, wird der
KD-Gegencheck gestrichen und der Rest laeuft weiter — eine Blickrichtung ohne
Ertrag ist Ballast, kein Grund, das Werkzeug aufzugeben. Dasselbe fuer K8 und
die Marker-Pruefung, und dasselbe fuer K9 und den Gegenpart. Das ist der Unterschied zwischen einer Erweiterung und
einer Neukonzeption: sie darf scheitern, ohne das Bestehende mitzureissen.

## Bezug

- Memory `project_ux_review_agent_program` (C1) — Owner-Prio 2026-07-22, wird durch dieses Dokument abgeloest
- Retro writing-hub fdd368 (C2, #2325) — drei Defekte, ein Fehlbefund, eine geteilte `.env`
- Outline „Sechs Befunde, die nur ein Browser sehen konnte" (C3) — vier Regeln, fuenf Gates
- `/kd-review` (C6), ADR-251 (C7) — das Gate davor
- `policies/platform-agents.md` — Ort fuer Stufe 2
- #2253 — Kill-Gate vor der ersten Zahl pre-registrieren
- [KONZ-platform-007](KONZ-platform-007-adr-handoff-extern-automation.md) (C13) — derselbe Gedanke 2026-07, `sunset` bei 0 Laeufen
- Step 5b als Umsetzungs-Issue: [#2466](https://github.com/achimdehnert/platform/issues/2466)
- ALT-1 als eigenes Issue: [#2326](https://github.com/achimdehnert/platform/issues/2326) — Klassen-Tests flottenweit (risk-hub, billing-hub, weltenhub, bfagent)
