---
retro_schema: 1
date: 2026-08-28
repo_scope: [ausschreibungs-hub]
session_id: e70d11
footprint: deep
findings_total: 9
findings_survived: 7
refuted_rate: 0.11
phase3_refuted: 0
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [gate-deferred-item-no-tracking-issue-wirkungslos, built-but-never-called, fabricated-identifier-in-report, truncated-output-read-as-complete]
recurring_findings: [deferred-item-no-tracking-issue, claim-before-cheapest-check, built-but-never-called, test-asserts-the-case-in-mind-not-the-harmful-one]
gates_caught: [claim-before-cheapest-check]
footprint_reduction_reason: "keine Reduktion — Rule-B-Trigger (3 Prod-Deploys) und Bedingung (b) 'keine DB-Migration' verletzt (0008, 0009)"
---

# Session-Retro 2026-08-28 — ausschreibungs-hub (e70d11)

## 1. Executive Summary

- **17 PRs, alle gemergt; 3 Prod-Deploys grün; 2 Migrationen** — der Zielzustand #240 (Kette Anmeldung→Abgabe) ist gebaut, aber **nie abgenommen**: das Issue steht offen, kein Kriterium K1–K5 ist als erfüllt oder verfehlt vermerkt.
- Die zweite Sitzungshälfte lieferte eine **komplett andere Feature-Linie** (Vergabeunterlagen-Abruf, #272 → PRs #271/#273/#274), jede Stufe vom Owner einzeln freigegeben. In Prod verifiziert: 10 Unterlagen, 8,2 MB, Texte extrahiert.
- **Schwerster Befund: drei in Prod gefundene Defekte blieben ohne Tracking-Artefakt** — sie existieren nur im Gesprächsverlauf. Das ist ein **Rückfall des Gates `deferred-item-no-tracking-issue`** (advisory, laut `gate_wirkung.py` rückfällig, letzter Rückfall heute).
- **Eine Run-ID wurde erfunden** und dem Owner als klickbarer Link vorgelegt (`33187696864` → HTTP 404). Selbst korrigiert, aber erst einen Turn später.
- **Eine falsche Aussage über den Klickdummy-Entwurf** entstand aus einem mit `head -8` abgeschnittenen Grep; der Evidenz-Hook erzwang die Nachprüfung, die sie widerlegte. Der Entwurf enthält den vermissten Konzept-Screen sehr wohl.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| B1 | Zielzustand #240 blieb unabgenommen — kein K1–K5 als erfüllt/verfehlt vermerkt, Sitzung endete auf einer anderen Feature-Linie | Prozesslücke | mittel | SURVIVES | `gh issue view 240` → OPEN, 2 Kommentare; PRs #271/#273/#274 referenzieren #270/#272, nicht #240 | neu |
| B2 | ux-review-Sammel-Issue #251 blieb offen, obwohl die daraus abgeleiteten Einzel-Issues (#242–#250) alle geschlossen sind | Prozesslücke | niedrig | SURVIVES | `gh issue list --state all` → #251 OPEN, #242–#250 CLOSED | `issue-open-after-its-fix-merged` |
| B3 | Drei in Prod gemessene Defekte ohne Tracking-Artefakt: 3 Dokument-Dubletten (gleiche `sha256`, `upload://` vs. Portal), 2 PDFs mit 0 Zeichen bei `fetch_status=ok`, falsches Quell-Etikett `evergabe-online:` für evergabe.de-Abrufe | Prozesslücke | hoch | SURVIVES | `gh issue list --search "dublette OR sha256 OR OCR OR duplikat"` → kein passendes Issue | **`deferred-item-no-tracking-issue` — Gate rückfällig** |
| B4 | Erfundene CI-Run-ID `33187696864` als klickbarer Link im Action Board | Überconfidence | mittel | SURVIVES | `gh run view 33187696864` → HTTP 404 | `claim-before-cheapest-check` (Variante ohne Hook-Abdeckung) |
| B5 | Die Attrappen des Seiten-Ernters wurden aus einer geratenen Seitenform gebaut; zwei Defekte überlebten eine vollständig grüne Suite | fehlende Validierung | mittel | HYPOTHESE | echter Lauf: 0 → 42 → 10 Dateien bei durchgehend grüner Suite; „geraten" ist ein Urteil, nicht kommandobelegt | `gemockt-und-deshalb-blind` |
| B6 | Das Test-Doppel der Netzwache hob die Wache auf, die es prüfen sollte (jeder Name → öffentliche IP, auch die wörtliche `169.254.169.254`) | fehlende Validierung | mittel | SURVIVES | Testlauf: `test_should_check_every_redirect_hop_not_just_the_first` schlug fehl, Log zeigt `GET http://169.254.169.254/... 200 OK` | `test-asserts-the-case-in-mind-not-the-harmful-one` (declined-Gate) |
| B7 | Der Evidenz-Stop-Hook feuerte **zweimal** in einer Sitzung; beide Male war eine prüfbare Behauptung ohne Check formuliert worden | Prozesslücke | mittel | SURVIVES | zwei Stop-Hook-Blocks im Transkript; beide Korrekturen durchgeführt (Positivkontrolle `scrapy/pooch`, Widerlegung Konzept-Screen) | **`claim-before-cheapest-check` — Gate hat gefangen** |
| B8 | Falsche Aussage an den Owner („der Entwurf kennt Konzept nur als Metadatum, nicht als Screen") aus einem mit `head -8` abgeschnittenen Grep | fehlende Validierung | hoch | SURVIVES | `klickdummy/it-angebot/screens-spec.yaml:231` `- id: konzept_wertungsmatrix`, `:255` `- id: it_sicherheitskonzept` — beide vom abgeschnittenen Grep nicht gezeigt | neu: `truncated-output-read-as-complete` |
| B9 | Deploy `727c6ff` steht auf `failure` ohne sichtbare Nacharbeit | — | — | PRE-REFUTED | `git branch -r --contains 727c6ff` → in `origin/main`; vier spätere Deploys erfolgreich; Fehlschlag war ein überholter Gate-Run | — |

**Zwei `built-but-never-called`-Instanzen in dieser Sitzung** (in B-Nummern nicht separat geführt, weil beide innerhalb der Sitzung behoben wurden): der Sammel-Abruf war seit 2026-08-25 gebaut und nur per Shell erreichbar (#272), und `dokument_urls` wird vom DÖE-Adapter erzeugt (`doe_opendata.py:118`), ohne dass ein Verbraucher existiert (`git log -S "dokument_urls"` → sechs Commits, alle Erzeuger). Der Slug steht laut `retro_kpis.py` bei ≥2 **ohne registriertes Gate**.

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Jede Owner-Anforderung geliefert und in Prod verifiziert (10 Unterlagen, 8,2 MB); Abzug für B1 (Zielzustand unabgenommen) |
| architektur_design | 4 | Geteilter Kern statt zweiter Umsetzung (`archiv_entpacken`, `unterlagen_abruf`), Wache als eigenes Modul, bewusst keine Portal-Positivliste; Abzug für B5/B6 (Designannahmen geraten) |
| code_konventionstreue | 4 | ruff durchgehend sauber, `test_should_*`, jedes Gate mit einzeln gefahrener Positivkontrolle; Abzug für B6 (Test-Doppel prüfte den harmlosen Fall) |
| risiko_debt | 2 | B3 (drei Prod-Befunde ohne Anker) + #240/#251 offen + drei Dubletten liegen jetzt in Prod-Daten |
| prozess_effizienz | 3 | 3 PRs, 3 Deploys, keine Rework-Schleife; Abzug für B4 und B8, die je einen Korrekturzyklus kosteten |
| entscheidungsqualitaet | 4 | Echter Lauf statt Attrappen-Vertrauen (fing 2 Defekte), SSRF-Wache ungefragt, Endungsfilter nach Gegenbeleg verworfen; Abzug für B4/B8 |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| #240 blieb offen; die Sitzung endete auf #272, ohne K1–K5 zu adressieren | Wechselt die Arbeit auf eine Linie außerhalb des akzeptierten Zielzustands, wird **im selben Zug** ein Abnahme-Kommentar an das Zielzustand-Issue geschrieben: je Kriterium erfüllt/verfehlt/verschoben | B1 |
| #251 blieb offen, obwohl alle Kind-Issues geschlossen sind | Beim Schließen des letzten Kind-Issues eines Sammel-Issues wird das Sammel-Issue im selben Zug geschlossen oder sein Rest benannt | B2 |
| Drei Prod-Befunde nur im Gesprächsverlauf genannt | Ein Befund, der in einem Board erscheint, bekommt **vor dem Absenden dieses Boards** sein Issue — die Board-Zeile trägt dann den Link, nicht die Absicht | B3 |
| Run-ID `33187696864` erfunden und verlinkt | Jede Zahl in einem Link stammt aus einer Werkzeugausgabe **dieses** Turns; ist sie es nicht, wird sie vor dem Absenden geholt (`gh run list --json databaseId`) | B4 |
| Test-Doppel gab jedem Namen eine öffentliche Adresse | Ein Doppel, das eine Schutzfunktion bedient, wird zuerst gegen den **schädlichen** Fall gefahren: schlägt der Test mit dem Doppel nicht fehl, prüft er nichts | B6 |
| Zweimal eine prüfbare Behauptung ohne Check formuliert | Vor jeder Aussage mit Marker (Zahl/Datei/Status) ein Blick, ob dieser Turn ihren Beleg enthält — der Hook ist die Rückfalllinie, nicht der Arbeitsschritt | B7 |
| `grep … \| head -8` als vollständige Antwort gelesen | Ein Grep, aus dem eine **Absenz** geschlossen wird, läuft ohne `head` und mit Positivkontrolle; erst dann ist die Null die Welt und nicht der Filter | B8 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über 101 Reports:

- `deferred-item-no-tracking-issue` — ≥2, Gate vorhanden (advisory)
- `claim-before-cheapest-check` — ≥2, Gate vorhanden (blocking)
- `built-but-never-called` — ≥2, **ohne registriertes Gate** (eine von 14)
- `test-asserts-the-case-in-mind-not-the-harmful-one` — ≥2, bewusst ohne Gate (declined)

`refuted_rate`-Band gesund über die Historie; **dieser Report liegt mit 0,11 unter dem Band** — Ursache ist keine schwache Falsifikation, sondern eine ausgefallene (§8).

Score-Mittel der Historie: `risiko_debt` 2,52 (schwächste Dimension) — dieser Report liegt mit 2 darunter und bestätigt das Muster: der Treiber ist erneut ungetrackte Restarbeit.

## 5a. Rückfall-Prüfung

`python3 tools/gate_wirkung.py` über 101 Reports:

| Gate | Modus | vor | nach | Urteil |
|---|---|---|---|---|
| `deferred-item-no-tracking-issue` | advisory | 24 | 6 | 🚨 **RUECKFAELLIG**, letzter Rückfall 2026-08-28 |
| `claim-before-cheapest-check` | blocking | 63 | 0 | zu-früh — **hat in dieser Sitzung 2× gefangen** |

**Klasse `gate-deferred-item-no-tracking-issue-wirkungslos`.** B3 ist der sechste Rückfall nach dem Bau. Zulässige Antwort: **ausweiten**. Das Gate prüft PR-Texte (`verankerung_pruefer.py --pr`) — B3 entstand aber in einem **Action Board im Chat**, nie in einem PR-Text. Genau dieser Kanal ist blind. Vorschlag: die Prüfung auf Board-Zeilen ausdehnen (jede Zeile mit Severity/Befund-Charakter braucht Link-Marker), oder als Pre-Send-Regel im Action-Board-Kanon verankern.

**`claim-before-cheapest-check` ist kein Rückfall, sondern ein Beleg**: der Stop-Hook feuerte zweimal und erzwang beide Male eine Korrektur, davon einmal die Widerlegung einer bereits an den Owner gesendeten Falschaussage (B8). Er steht in `gates_caught`, nicht in der Rückfall-Klasse.

## 6. Verankerung

### memory_candidates

```markdown
---
name: truncated-grep-read-as-absence
description: Ein Grep mit head/tail belegt keine Absenz — die Null ist dann der Filter, nicht die Welt
metadata:
  type: feedback
drift: true
drift_episode: 2026-08-28-konzept-screen
---

Am 2026-08-28 lautete die Aussage an den Owner: „der Klickdummy-Entwurf kennt
Konzept nur als Metadatum, nicht als Screen." Grundlage war
`grep -rhn "konzept" klickdummy/*/screens-spec.yaml | head -8` — die acht
gezeigten Zeilen waren `konzept_id`/`konzept_ref` aus anderen Spezifikationen.
Der vollständige Grep fand `klickdummy/it-angebot/screens-spec.yaml:231
- id: konzept_wertungsmatrix` und `:255 - id: it_sicherheitskonzept`.

**Why:** Aus einer abgeschnittenen Ausgabe wurde eine Absenz geschlossen und dem
Owner als Fakt gemeldet. Die Folge wäre gewesen, einen Screen neu zu entwerfen,
der spezifiziert vorliegt.

**How to apply:** Ein Grep, aus dem eine Absenz folgt, läuft ohne `head`/`tail`
und mit Positivkontrolle (derselbe Ausdruck muss etwas Bekanntes finden). Siehe
[[evidence-discipline]] und [[kd-gap-claims-need-fulltext-evidence]] — dieselbe
Klasse, dort auf Klickdummy-Gap-Claims, hier auf Screen-Existenz.
```

```markdown
---
name: board-line-needs-its-issue-before-send
description: Ein Befund im Action Board bekommt sein Issue VOR dem Absenden, nicht danach
metadata:
  type: feedback
---

Am 2026-08-28 nannte ein Board drei in Prod gemessene Defekte (Dokument-Dubletten
per sha256, zwei PDFs mit 0 Zeichen bei `fetch_status=ok`, falsches Quell-Etikett).
Alle drei blieben ohne Issue; `gh issue list --search` findet nichts dazu.

**Why:** `deferred-item-no-tracking-issue` ist seit dem 2026-08-23 gegated — aber
das Gate prüft PR-Texte. Ein Befund, der im Chat-Board entsteht und nie in einen
PR-Text wandert, passiert es ungesehen. Sechs Rückfälle nach Gate-Bau.

**How to apply:** Trägt eine Board-Zeile einen Befund (Severity, „Defekt",
„fehlt", „falsch"), bekommt sie vor dem Absenden einen echten Link — Issue
anlegen, dann die Zeile schreiben. Siehe [[autonomy-gates-preference]].
```

### adr_candidates

Keine. Beide Befunde sind Prozess-, keine Architekturentscheidungen; ein ADR wäre laut `policies/adr-threshold.md` überdimensioniert.

## 7. Maßnahmen

### ✅ Erledigt im selben Zug

Die fünf sofort machbaren Maßnahmen wurden **vor dem Commit dieses Reports** ausgeführt — sonst wäre B3 ein zweites Mal ungetrackt geblieben.

1. ✅ Dokument-Dubletten (sha256 statt source_url) — https://github.com/iilgmbh/ausschreibungs-hub/issues/275
2. ✅ Zwei signierte PDFs mit null Zeichen, Status `ok` — https://github.com/iilgmbh/ausschreibungs-hub/issues/276
3. ✅ Falsches Quell-Etikett `evergabe-online:` — https://github.com/iilgmbh/ausschreibungs-hub/issues/277
4. ✅ Zwischenabnahme K1–K5 kommentiert — https://github.com/iilgmbh/ausschreibungs-hub/issues/240
5. ✅ Sammel-Issue abgeglichen — https://github.com/iilgmbh/ausschreibungs-hub/issues/251

**Korrektur zu M5:** Die Annahme, #251 könne geschlossen werden, war falsch — von 18 verlinkten Befunden ist **#236 noch offen** (`[ux-review] Kette Recherche→Abgabe · 2026-08-26`). Das Sammel-Issue bleibt begründet offen statt still liegenzubleiben.

### 🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| M6 | Gate ausweiten: Board-Zeilen statt nur PR-Texte | platform | — | 🟢 offen | entscheiden (du) |
| M7 | Gate bauen für `built-but-never-called` | platform | — | 🟢 offen | entscheiden (du) |
| M8 | Falsifikation von B5 nachholen (~55k Token) | — | — | 🟢 offen | freigeben (du) |
| M9 | Frischer klick-only-Durchlauf nach dem letzten Deploy (K5-Lücke) | a-hub | #240 | 🟢 offen | anstoßen (du) |

## 8. Nicht verifiziert (Restlücken)

- **Regel-1-Bruch (Richter ≠ Angeklagter): Find- und Verify-Phase liefen inline**, nicht über frische Subagenten. Grund: die Systemanweisung dieser Sitzung untersagt das Agent-Tool ohne ausdrückliche Anforderung. Der Skill sieht diesen Fall vor (Phase 0, „Wenn die Umgebung Subagenten untersagt"): inline finden, sortieren, die Bewertungsbefunde zur Freigabe vorlegen. **Billigster Check:** ein Sonnet-Skeptiker auf B5, gemessene Kosten ~55k Token.
- **B5 ist der einzige Bewertungsbefund** und deshalb unfalsifiziert als Hypothese geführt. Die übrigen acht sind kommandobelegt (Issue-Status, HTTP 404, Grep-Ergebnis, Testlauf-Ausgabe) — dort ändert ein fremder Kontext an der Zahl nichts.
- **`refuted_rate` 0,11 liegt unter dem gesunden Band (<0,2).** Ursache ist die ausgefallene Phase 3, nicht laxe Finder: `pre_refuted=1` stammt aus einer eigenen Vorprüfung (B9), `phase3_refuted=0` ist mangels Skeptiker strukturell.
- **Nicht geprüft:** ob der Seiten-Ernter bei `meinauftrag.rib.de` und `evergabe.nrw.de` trägt (steht so in PR #273). Billigster Check: derselbe Lauf gegen je eine Ausschreibung von dort.
- **Nicht geprüft:** ob die drei Dubletten in Prod die Analysequalität messbar verzerren (doppelte Gewichtung derselben Leistungsbeschreibung). Billigster Check: eine Analyse vor/nach Dublettenbereinigung vergleichen.

### getan · angenommen · nicht verifizierbar · offen geblieben

- **getan:** Ground-Truth aus Artefakten gesammelt (17 PRs, 18 Issues, 12 Deploys, `git branch -r --contains` je Merge-Commit); 9 Befunde gebildet, 8 davon kommandobelegt; beide Pflicht-Werkzeuge gelaufen; Rückfall-Klasse für `deferred-item-no-tracking-issue` gebildet.
- **angenommen:** dass die Sitzungsgrenze über die Branch-Präfixe `session/2026-08-2[78]` korrekt gezogen ist (keine fremde Sitzung im selben Fenster gefunden, aber nicht gegen ein Transkript gegengeprüft).
- **nicht verifizierbar:** B5 ohne Skeptiker; der Zusammenhang zwischen Hook-Feuern und tatsächlicher Verhaltensänderung über die Sitzung hinaus.
- **offen geblieben:** M6–M9 (Owner-Entscheidung); M1–M5 wurden im selben Zug erledigt.
- **Phase 5 (Meta-Reviewer) ist ausgefallen** — derselbe Subagenten-Grund wie Phase 2/3. Dieser Report ist damit nicht gegen die Skill-Regeln gegengeprüft worden; billigster Check ist ein Sonnet-Meta-Agent auf den Report-Text (~55k).
