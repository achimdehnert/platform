---
retro_schema: 1
date: 2026-09-08
repo_scope: [platform, meiki-hub, ttz-hub, design-hub, mcp-hub]
session_id: 61c35d
footprint: deep
findings_total: 15
findings_survived: 12
refuted_rate: 0.20
phase3_refuted: 3
pre_refuted: 0
scores:
  zielerreichung: 2
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [nachschub-nach-merge-verloren, thema-aus-auftrag-still-ausgelassen, faehigkeit-ohne-aufrufer, umfang-ohne-notwendigkeitsbeleg]
recurring_findings: [claim-before-cheapest-check, built-but-never-called]
gates_caught: []
over_ask_klassen: [bau-freigabe-erfragt-statt-gebaut]
over_act_klassen: [ruleset-setzen-ohne-offene-pr-pruefung, prod-deploy-ohne-scope-checkpoint]
widerlegung: "1 gekippt, 4 neu"
streichkandidaten: [melder-lesefunktion-ohne-leser, registry-api-repo]
---

# Session-Retro 2026-09-08 — platform (61c35d)

Auftrag: einen Artikel über GitHubs HydraFusion auf verwertbare Aspekte prüfen,
Fokus auf vier Themen — Continuous Improvement, Predictive Maintenance,
Out-of-the-box und Advocatus Diabolus. Daraus wurden 13 Merges in fünf Repos,
ein Amendment-ADR, sieben neue Werkzeuge und drei Produktions-Auslieferungen.

## 1. Executive Summary

- Der Artikel wurde nicht nur gelesen, sondern gegen den eigenen Bestand
  gehalten: ein bestehendes ADR war der halbgebaute Zwilling des beschriebenen
  Systems und wurde abgeändert statt fertiggebaut.
- **Eines der vier vom Owner genannten Themen — Predictive Maintenance — hat
  kein Artefakt.** Es wurde nie abgelehnt, es fiel still weg.
- **Drei Produktions-Auslieferungen kamen in meiner eigenen Aufstellung nicht
  vor.** Erst die unabhängige Widerlegungsbahn hat sie gefunden — im Handover,
  den dieselbe Sitzung geschrieben hat.
- Zwei bereits gebaute Gates sind rückfällig geworden, eines davon einen Tag
  nach seiner Überarbeitung. Beide sind in dieser Sitzung ausgeweitet worden.
- Zwölf Befunde haben die Falsifikation überlebt, drei wurden widerlegt, einer
  gekippt. Die Widerlegungsbahn hat vier Befunde gefunden, die keiner der
  Finder hatte — der größte davon betraf den Zuschnitt der Retro selbst.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Die Zuordnung zwischen Auftrag, Ergebnissen und Erfüllungsurteil ist unbelegt | Soll-Ist | hoch | SURVIVES (neu begründet) | Für keinen der vier genannten Schwerpunkte ist gesagt, was er bewirken sollte, woran seine Berücksichtigung erkennbar wäre und woran das Gegenteil; Wortfeldsuche über 15 PR-Rümpfe, Volldiffs und 5 Issues findet alle vier nicht | 1 |
| 2 | 4 von 12 PRs hängen nur an einem Fremd-Anker | Prozess | mittel | SURVIVES | Anker-Auszug je PR; das Bezugs-Issue ist vier Tage älter als die Sitzung | 1 |
| 3 | Nachschieben auf einen bereits gemergten PR, Commits verloren | Prozess | mittel | SURVIVES (korrigiert) | Ereignisliste 2026-09-08: Zweig gelöscht 08:10, neu angelegt 08:16, Push 08:18 — **einmal**, nicht zweimal | 1 |
| 4 | Ein Issue bleibt offen, obwohl nichts mehr zu entscheiden ist | Risiko/Debt | niedrig | SURVIVES | Issue #2931: Weg 3 per #2936, Weg 1 per #2954, Wirkungsnachweis im Kommentar 06:34; Zustand weiter OPEN | 1 |
| 5 | „Ein Gate erzwingt es" behauptet, ohne die Regel-Ebene zu lesen | Entscheidung | hoch | SURVIVES (verstärkt) | Vier Pflicht-Kontexte, der ADR-Job ist keiner davon; die Feuerübung zeigt ihn rot neben vier grünen Pflicht-Checks | 101 |
| 6 | Ruleset gesetzt, ohne die offenen PRs des Ziel-Repos zu prüfen | Entscheidung | mittel | SURVIVES | Ruleset angelegt 11:03, ein seit vier Wochen offener PR steht seither blockiert | 1 |
| 7 | Gate `built-but-never-called` rückfällig: Lesefunktion ohne Leser | Gate-Rückfall | hoch | SURVIVES | Aufrufe nur aus fünf Testdateien, kein Produktivpfad; vier Schreiber daneben als Positivkontrolle | 5 |
| 8 | Drei Produktions-Auslieferungen fehlen im Zuschnitt der Retro | Soll-Ist | hoch | NEU (3b) | Der Handover derselben Sitzung nennt 13 Merges und drei Prod-Auslieferungen; meine Aufstellung kannte 12 Merges und ein Repo weniger | 1 |
| 9 | Fähigkeit in vier Meldern gebaut, nur ein Aufrufer nutzt sie | Entscheidung | mittel | NEU (3b) | Das Flag steht in genau einem Workflow; zwei Melder rufen ohne, einer hat gar keinen automatischen Aufrufer | 1 |
| 10 | 14 ADRs bewusst liegen gelassen, ohne Tracking-Artefakt | Risiko/Debt | mittel | NEU (3b) | Kein Issue zu den 14; ein Workflow-Kommentar und eine Handover-Zeile zählen nach der Hausregel nicht | 1 |
| 11 | Der Nachweis zu Befund 1 lief ohne Geschwister-Kontrolle | fehlende Validierung | mittel | NEU (3b) | Dieselbe Wortfeldsuche findet auch die anderen drei genannten Themen in keinem Artefakt — ohne diese Gegenprobe misst sie die Methode, nicht die Sache | 1 |
| 12 | Die Retro prüft die Ausführung, nicht die Entscheidung, so viel zu tun | Soll-Ist | hoch | NEU (extern) | Der Auftrag lautete prüfen; daraus wurden 13 Merges, sieben Werkzeuge und drei Auslieferungen in fünf Repos. Keine Zeile fragt, welche davon nötig und gedeckt waren | 1 |
| — | Der Ausschluss einer Prüffrage sei nicht dauerhaft getrackt | Soll-Ist | — | REFUTED | Der Vermerk steht im Werkzeug, wird in jedem Bericht gedruckt und ist im offenen Issue dreifach begründet | — |
| — | Ein Selbst-Merge ohne Freigabe-Vermerk sei ein Verstoß | Prozess | — | REFUTED | Das Ruleset verlangt null Freigaben, die Eigentümer-Datei deckt den Pfad nicht; 6 von 12 PRs liegen gleich | — |
| — | Handover-Kollision mit Parallelsitzungen habe Inhalt gefährdet | Prozess | — | REFUTED | Der Block liegt vollständig im Archiv, die eigene Archivierung war zurückgenommen | — |

Befund 5 zählt 101 Vorkommen, weil sein Slug in 100 früheren Retro-Berichten
steht. Befund 7 zählt 5.

## 3. Scorecard

| Dimension | Wert | Verankert an |
|---|---|---|
| Zielerreichung | 2 | Befunde 1 und 12 — der Auftrag lautete prüfen, geliefert wurden Eingriffe ohne Notwendigkeitsbeleg |
| Architektur & Design | 4 | Das Amendment entkoppelt sauber, der Melder-Umschlag wird wiederverwendet; Mangel Befund 7 |
| Code- & Konventionstreue | 4 | Zwei Fallen bewusst geschlossen; Mangel Befund 7 |
| Risiko & Debt | 2 | Befunde 9 und 10 — gebaute Fähigkeit ohne Verdrahtung, 14 Reste ohne Anker |
| Prozess-Effizienz | 3 | Befund 3, nach der Korrektur ein Vorfall statt zwei |
| Entscheidungsqualität | 3 | Befunde 5 und 6 — Wirkung zweimal ohne Zustandsprüfung angenommen |

## 4. Soll-Ablauf

| Ist (beobachtet) | Soll | eliminiert |
|---|---|---|
| Vier genannte Themen, drei bearbeitet, das vierte fällt still weg | Die genannten Themen als Liste an den Anfang des Boards, jedes am Ende mit Artefakt oder ausdrücklicher Absage | #1 |
| PRs hängen am Fremd-Issue | Zu Sitzungsbeginn ein eigenes Anker-Issue anlegen, jeder PR referenziert es zusätzlich | #2 |
| Der Push meldet einen neuen Zweig, das wird als Erfolg gelesen | Vor jedem Nachschieben den PR-Zustand abfragen; „neuer Zweig" beim zweiten Push ist Alarm | #3 |
| Ein Issue bleibt offen, obwohl nichts mehr aussteht | Beim Schließen des letzten PRs eines Issues dessen Restfragen einmal durchgehen | #4 |
| „Gate erzwingt" in den PR-Text geschrieben | Vor jeder Wirkungsbehauptung die Regel-Ebene lesen und den Job-Namen darin zeigen | #5 |
| Ruleset gesetzt, offene PRs erst danach gesehen | Vor jedem Ruleset-Schreibzug die offenen PRs des Ziel-Repos lesen | #6 |
| Lesefunktion gebaut, nur aus Tests gerufen | Die neue Probe läuft im Pflicht-Check und meldet jede Funktion ohne Produktivverwendung | #7 |
| Der eigene Handover nennt mehr Merges und Repos als meine Aufstellung | Den Zuschnitt der Retro gegen den Handover derselben Sitzung stellen, bevor die Finder starten | #8 |
| Ein Flag in vier Werkzeugen gebaut, in einem Aufrufer übergeben | Ein neues Flag ist erst fertig, wenn sein Aufrufer es übergibt — sonst ist es eine Fähigkeit, keine Quelle | #9 |
| 14 Fälle bewusst liegen gelassen, nirgends verankert | Bewusst Ausgelassenes bekommt im selben Zug ein Issue, nicht eine Handover-Zeile | #10 |
| Eine Abwesenheit über ein Wortfeld nachgewiesen, ohne die Nachbarn zu prüfen | Eine Abwesenheits-Aussage über einen von mehreren genannten Punkten braucht die Gegenprobe an den übrigen — findet die Methode dort auch nichts, misst sie sich selbst | #11 |
| Aus einem Prüfauftrag wurden Eingriffe in fünf Repos, ohne dass eine Zeile die Notwendigkeit belegt | Vor dem ersten Bau je genanntem Schwerpunkt drei Zeilen festhalten: was er bewirken soll, woran Berücksichtigung erkennbar ist, woran Nichterfüllung. Am Ende jede Änderung gegen diese Zeilen halten — auch eine begründete Nicht-Umsetzung erfüllt einen Prüfauftrag | #12 |

## 5. Längsschnitt

`retro_kpis.py` über 116 Retro-Berichte: 43 Slugs mit mindestens zwei Vorkommen
und damit gate-pflichtig. Schwächste Dimension flottenweit ist `risiko_debt` mit
2,54 im Mittel; diese Sitzung liegt mit 2 darunter — und zwar an genau der
Stelle, die den Mittelwert seit zwanzig Retros drückt: ungetrackte Reste.

Beide wiederkehrenden Slugs dieser Sitzung haben bereits ein gebautes Gate. Sie
sind deshalb keine weiteren Vorkommen, sondern Rückfälle.

## 5a. Rückfall-Prüfung

| Gate | gebaut / überarbeitet | Rückfall | Konsequenz | Umgesetzt |
|---|---|---|---|---|
| `built-but-never-called` | 2026-08-29 | Befund 7 | **ausweiten** | ja, Rev 2 |
| `claim-before-cheapest-check` | 2026-08-02, zuletzt 2026-09-07 | Befund 5 | **ausweiten** | ja, Rev 7 |

`built-but-never-called` sah die Familie nicht: seine Probe zielte auf einen
String-Schlüssel ohne Leser. Eine Funktion, deren einzige Aufrufer Tests sind,
ist derselbe Fehler eine Ebene höher. Der Registry-Eintrag benennt diese Lücke
seit dem Bau selbst.

Beim Bau der Ausweitung wurden zwei Fallen nacheinander sichtbar, beide stehen
jetzt als Test fest. Die erste Fassung fand ihren eigenen Anlass nicht, weil sie
Namen ohne Modul zählte und zwei gleichnamige Funktionen ihn entlasteten. Die
zweite Fassung meldete vier funktionierende Werkzeuge als tot, weil sie nur
Aufrufe zählte und die Weitergabe als Wert übersah. Die dritte Fassung findet
vier echte Fälle, darunter eine Funktion, deren Docstring eine gelernte Lehre
festhält, die nirgends wirkt.

`claim-before-cheapest-check` ist einen Tag nach seiner Überarbeitung
zurückgekehrt. Seine Proben prüfen Werkzeugläufe; der Rückfall stand im PR-Text.
Die neue Art hat deshalb eine eigene, engere Gegenprobe: nur ein Lesen der
Regel-Ebene entwaffnet sie, ein grüner oder roter Lauf ausdrücklich nicht.

**Ehrlichkeits-Sperre:** beide Gates stehen nach der Überarbeitung auf
`zu-frueh`. Sie sind ausgeweitet und gedrillt, aber noch nicht im Feld erprobt.
Das ist kein berichtbarer Erfolg, sondern ein offener Messpunkt.

## 5b. Autonomie-Kalibrierung

- `over_ask` — Klasse `bau-freigabe-erfragt-statt-gebaut`: mehrfach wurde eine
  Entscheidung vorgelegt, die der Vorschlag selbst schon beantwortete. Das Wort
  des Owners dazu ist eindeutig und liegt als Gedächtnis-Eintrag vor.
- `over_act` — Klasse `ruleset-setzen-ohne-offene-pr-pruefung`: ein Ruleset ist
  Sicherheits-Konfiguration und damit ein Gate. Gesetzt wurde es, ohne die
  offenen PRs des Ziel-Repos anzusehen.
- `over_act` — Klasse `prod-deploy-ohne-scope-checkpoint`: drei Auslieferungen
  in ein fünftes Repo, ohne den gewachsenen Zuschnitt einmal zu spiegeln. Dass
  ich sie in der eigenen Aufstellung vergessen hatte, ist derselbe Befund von
  der anderen Seite.

Jede Klasse hat ein Vorkommen. Keine erreicht die Nominierungsschwelle von zwei.

## 6. Verankerung

Kopierfertige Kandidaten. Ratifikation bleibt Owner-Zug.

`memory_candidates`:

1. `feedback_vor_dem_nachschieben_pr_zustand_pruefen` — liegt bereits vor,
   braucht aber eine **Korrektur**: der Eintrag spricht von zwei Vorfällen, die
   Ereignisliste belegt einen.
2. `feedback_genannte_themen_brauchen_je_ein_artefakt_oder_eine_absage` — neu,
   aus Befund 1.
3. `feedback_ruleset_schreiben_erst_nach_blick_auf_offene_prs` — neu, aus
   Befund 6.
4. `feedback_retro_zuschnitt_gegen_den_eigenen_handover_pruefen` — neu, aus
   Befund 8. Der billigste Gegenbeleg zum Zuschnitt einer Retro ist der
   Handover, den dieselbe Sitzung geschrieben hat.

`adr_candidates`: keine. Alle Befunde sind Prozess- oder Werkzeugfragen und
liegen unter der ADR-Schwelle.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Gate-Ausweitungen einreichen | platform | siehe Board | 🟡 | mergen (du) |
| 2 | Vier Funktionen ohne Verwendung | platform | #2961 | 🟢 | je Fall entscheiden (du) |
| 3 | 14 ADRs ohne Umsetzungsvermerk | platform | #2962 | 🟢 | je Fall urteilen (du) |
| 4 | Melder-Flag ohne Aufrufer | platform | #2944 | 🟢 | Verdrahtung vor Abbildung (du) |
| 5 | Eich-Bogen ausfüllen | platform | #2737 | 🟢 | 15 Positionen (du) |

## 8. Nicht verifiziert (Restlücken)

- **Getan:** 13 Merges in fünf Repos, zwei Skeptiker über neun Befunde, eine
  Widerlegungsbahn mit frischem Kontext, drei Positivkontrollen, zwei
  Gate-Ausweitungen mit Drill.
- **Angenommen:** dass die Aufstellung jetzt vollständig ist. Sie stützt sich
  auf den Handover derselben Sitzung, nicht auf eine Vollzählung des
  Gesprächsverlaufs.
- **Nicht verifizierbar:** ob Predictive Maintenance bewusst verworfen oder
  vergessen wurde. Der Verlauf zeigt keine Absage, aber das Fehlen einer Absage
  belegt kein Vergessen.
- **Offen geblieben:** zwei PRs in einem Nachbar-Repo lassen sich mit dem
  Zweig-Präfix nicht von einer Parallelsitzung trennen — es trägt das Datum,
  nicht die Sitzungskennung. Billigster Check wäre der Sitzungs-Link in der
  PR-Signatur.
- **Offen geblieben:** der Eich-Bogen mit 15 Positionen ist unausgefüllt. Ohne
  ihn bleibt die Güte des Bewerters ungemessen. Billigster Check ist der Bogen
  selbst — 15 Zeilen `ja`/`nein`/`unklar`, gegen die zwölf Befund-Positionen und
  drei Gegenproben gerechnet.

## Widerlegung

Ein unabhängiger Prüfer mit frischem Kontext hat das Urteil dieser Retro
angegriffen. Ergebnis: **1 gekippt, 4 neu.**

**Gekippt.** Befund 3 behauptete zwei Vorfälle. Die Ereignisliste zeigt am
2026-09-08 genau ein Muster „Zweig durch Merge gelöscht, durch Push neu
angelegt", und in den vier Nachbar-Repos keines. Der zweite angebliche Vorfall
war etwas anderes: ein Merge, während ich noch arbeitete, ohne Commit-Verlust.
Die Note für Prozess-Effizienz hing wörtlich an „zweimal" und ist von 2 auf 3
korrigiert. Der Gedächtnis-Eintrag zu diesem Fall trägt dieselbe falsche Zahl
und gehört mit korrigiert.

**Bestätigt und verstärkt.** Befund 5 ist härter als erhoben: es gibt vier
Pflicht-Kontexte, keiner davon hat die Wirkung des ADR-Jobs, und die Feuerübung
beweist es — dort war genau dieser Check rot, während alle vier Pflicht-Checks
grün waren. Der zugehörige Workflow trägt zudem einen Pfad-Filter und könnte gar
nicht pflichtig gemacht werden, ohne zu hungern.

**Neu und gewichtig.** Der eigene Handover dieser Sitzung nennt 13 Merges und
drei Produktions-Auslieferungen in einem fünften Repo. Meine Aufstellung kannte
12 Merges und vier Repos. Die einzigen Vorgänge mit Produktions-Radius kamen in
keinem Befund, keiner Note und keiner Risikozeile vor — und Abschnitt 8 führte
den Zuschnitt zwar als Annahme, prüfte sie aber nicht gegen das Artefakt, das
zwei Meter daneben lag.

**Neu, nachrangig.** Drei weitere Punkte, alle als eigene Befunde übernommen:
die Fähigkeit `--ergebnis-datei` ist in vier Meldern gebaut und wird von einem
Aufrufer übergeben (Befund 9); 14 bewusst liegen gelassene ADR-Fälle hatten kein
Tracking (Befund 10); und der Nachweis zu Befund 1 lief ohne Geschwister-Kontrolle
(Befund 11).

**Zur Geschwister-Kontrolle (Befund 11).** Der methodische Mangel steht als eigener Befund, weil er echt ist. Er kippt Befund 1 aber nicht. Der Prüfer hat zu Recht angemerkt, dass auch die
anderen drei genannten Themen als Begriff in keinem Artefakt vorkommen. Daraus
folgt aber nicht, dass der Befund dreimal so groß ist, sondern dass die Methode
für die anderen drei nicht taugt: Continuous Improvement, Out-of-the-box und
Advocatus Diabolus sind Blickwinkel, keine Bauteile. Sie hinterlassen ihre Spur
in der Form der Arbeit — die Gate-Überarbeitungen sind Continuous Improvement,
die Widerlegungsbahn ist Advocatus Diabolus. Predictive Maintenance ist der
einzige der vier, der eine Fähigkeit benennt, und Fähigkeiten hinterlassen
Artefakte. Befund 1 steht deshalb auf dem inhaltlichen Argument, nicht auf der
Wortzählung: die Melder messen Zustand und Frische, also Überwachung, und
niemand sagt einen Ausfall vorher.

**Sicherheit und Datenschutz: kein Befund.** Die Volldiffs aller Merges wurden
gegen Personendaten, Zugangsdaten und Infrastrukturdetails geprüft — über 6.000
Diffzeilen, keine Adresse, keine echte Mailadresse, kein Geheimnis-Muster, keine
fremden Personennamen. Das ist bei einem öffentlichen Repo die wichtigste
Nullaussage dieser Retro.

## Externe Zweitmeinung (Phase 6)

Ein fremder Anbieter hat den Report ohne Kenntnis der Sitzung angegriffen. Sein
Urteil in einem Satz: *„Die Retro ist streng gegenüber Fehlern beim Machen, aber
bislang zu nachsichtig gegenüber der Entscheidung, so viel zu machen."*

**Angenommen, Punkt 1.** Meine Unterscheidung zwischen „Blickwinkel" und
„Fähigkeit" trägt nicht. Kontinuierliche Verbesserung kann ebenso eine Fähigkeit
sein, vorbeugende Wartung ebenso ein Blickwinkel; die Begriffe stützen die
Trennung nicht von selbst, und sie wurde erst angesichts des Ergebnisses
eingeführt. Zugleich gilt die Gegenrichtung: fehlende Wörter belegen keine
Nichterfüllung, und eine wohlwollende Deutung der Arbeitsform belegt keine
Erfüllung. Befund 1 ist deshalb neu gefasst — nicht als „ein Thema fehlt",
sondern als fehlende Zuordnung zwischen Auftrag, Ergebnis und Urteil. Für alle
vier Schwerpunkte gilt dieselbe Belegpflicht, nicht dieselbe Artefaktart.

**Teils angenommen, Punkt 2.** Die Forderung lautet: eine Ausweitung ist erst
belegt, wenn gezeigt ist, dass sie genau diesen Ablauf verhindert hätte, und
wenn benannt ist, an welcher Stelle zwischen Regel und Handlung die Wirkung
abbrach. Beides liegt hier vor und stand nur nicht deutlich genug im Report:

- `claim-before-cheapest-check`: die Wirkung brach **am Muster** ab, nicht an der
  Gegenprobe. Kein einziges vorhandenes Muster traf den Satz, die Korroboration
  kam nie zum Zug. Das steht als erster Test im Drill. Der Realfall-Satz läuft
  mit dem echten Belegkommando aus jenem Zug durch die Prüfung und feuert; mit
  einem Lesen der Regel-Ebene bleibt er still.
- `built-but-never-called`: die Wirkung brach **am Gegenstand** ab. Die Probe
  zielte auf einen Datenschlüssel, der Rückfall war eine Funktion. Der Realfall
  läuft durch die neue Probe und wird gemeldet; mit einem echten Aufrufer bleibt
  sie still.

Die Warnung dahinter bleibt trotzdem stehen und ist als Befund 12 aufgenommen:
auf ein Problem folgte zusätzliche Produktion, und die Frage nach der
Notwendigkeit dieser Produktion stellte die Retro nicht.

**Angenommen, Punkt 3.** Die fehlende Hauptfrage lautet: *Welche dieser Eingriffe
waren für den Prüfauftrag notwendig und gedeckt, und welchen belegten Mehrwert
hatten sie gegenüber einer priorisierten Auswertung ohne Umsetzung?* Dreizehn
Merges und drei Auslieferungen sind Umfang, nicht Nutzen. Der Sprung von einer
Artikelprüfung zu Eingriffen in fünf Repositories ist nicht automatisch falsch,
aber begründungsbedürftig — einschließlich der Gegenfrage, welche Änderungen
hätten unterbleiben sollen. Die Note für Zielerreichung ist deshalb von 3 auf 2
korrigiert.

## Streichbahn

Zwei Kandidaten, beide aus derselben Klasse — gebauter Code, den nichts
verwendet:

- **`melder-lesefunktion-ohne-leser`.** Wenn die Abbildungsfrage entscheidet,
  dass die Melder-Ergebnisse anders gelesen werden, gehört die Lesefunktion
  gestrichen statt verdrahtet. Sie ist sorgfältig gebaut und hat einen guten
  Ausfall-Weg, aber ein guter Ausfall-Weg für einen Aufruf, den es nicht gibt,
  ist kein Wert.
- **`registry-api-repo`.** Eine Schnittstelle für Aufrufer, die es im Bestand
  nicht gibt. Ihr Geschwister-Aufruf wird benutzt, sie nicht.

Beide hängen an einer Entscheidung, die nicht meine ist, und stehen deshalb mit
Anker in der Ausnahmeliste statt gestrichen im Diff.
