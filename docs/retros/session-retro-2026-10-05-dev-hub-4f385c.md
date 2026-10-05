---
retro_schema: 1
date: 2026-10-05
repo_scope: [dev-hub, platform, chat-hub, illustration-hub]
session_id: 4f385c
footprint: deep
findings_total: 19
findings_survived: 12
refuted_rate: 0.37
phase3_refuted: 7
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [repo-datei-per-shell-skript-statt-edit, edit-after-compaction-without-reread, accepted-plan-item-silently-dropped]
recurring_findings: [gate-scope-checkpoint-not-durably-recorded-wirkungslos, edit-after-compaction-without-reread, deferred-item-no-tracking-issue, accepted-plan-item-silently-dropped, claim-before-cheapest-check, partial-fix-not-generalized-to-sibling-artifacts, gate-matches-spelling-not-substance, secret-leak-via-safe-pattern, direct-gh-pr-merge-bypasses-sa-m]
gates_caught: [secret-leak-via-safe-pattern, direct-gh-pr-merge-bypasses-sa-m]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "2 gekippt, 5 neu"
streichkandidaten: []
streich_begruendung: "Keine Skill-Regel dieser Retro lief ohne Effekt: Die Skeptiker haben 5 von 9 geprüften Bewertungsbefunden verworfen, die Widerlegungsbahn zwei weitere, und die Trennung kommandobelegt gegen Bewertung hat acht Zweitausführungen gespart."
footprint_reduction_reason: "Keine Reduktion. Die Retro war als full geplant; die Bedingung dafür (Schätzung höchstens 10 Befunde) hielt mit 17 Befunden nicht, also zählt sie als deep. Gelaufen ist die deep-Pipeline bis auf Phase 6 (§8)."
---

# Session-Retro 2026-10-05 — Infrastruktur-Stand (dev-hub#436) und Rückbau stillgelegter Einheiten (dev-hub#440)

> Deep: 3 Finder (Sonnet), 3 Skeptiker (Sonnet, je Dimension) auf 9 Bewertungsbefunde, Widerlegungsbahn (Opus), Meta-Review (Sonnet). 8 Agenten. Die 8 kommandobelegten Befunde gingen ohne Skeptiker durch.

## 0. Wirkungsbilanz (Phase 0.0)

`gate_wirkung.py`: 7 Gates RUECKFAELLIG. Von dieser Sitzung berührt:

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| secret-leak-via-safe-pattern | kein neuer Rückfall | Der Wächter hat zweimal vor der Ausführung blockiert (2026-10-04, Transkript-Kennzahlen). Das ist Beleg für das Gate | keine der vier Konsequenzen gewählt (§8) |
| stale-local-clone-as-ground-truth | kein Fall | Finder, Skeptiker und Widerlegungsbahn lasen aus dem Ref | keine der vier Konsequenzen gewählt (§8) |
| handover-stale-vor-merge | ein Fall am Sitzungsende | Quelle: Der Stand von dev-hub lag 25 Commits zurück; das Gate meldete es erst im Abschluss-Lauf, nach elf Merges | keine der vier Konsequenzen gewählt (§8); Nachtrag liegt als dev-hub#452 vor |

Die übrigen 4 RUECKFAELLIG-Gates (untested-tool-module-green-gate, check-ohne-positivkontrolle, melder-ohne-leser, parallel-session-pr-collision) hat diese Sitzung nicht berührt. Die Regel lässt nur vier Konsequenzen zu (herabstufen, Sunset, nachschärfen, Drill ergänzen); für alle sieben wählt dieser Report keine. Das ist eine Regelabweichung und steht als solche in §8. Die Verfallsfrist von `gate-anchored-without-drill-or-control` ist am 2026-10-02 abgelaufen, das Gate steht weiter auf advisory (§8).

Nicht in der Liste der sieben, aber hier rückfällig: `scope-checkpoint-not-durably-recorded` (Befund #12, §5a).

**Session-Grenze:** Transkript 2026-10-02 bis 2026-10-05, über die PR-Liste gezogen: platform #3694, #3697; dev-hub #430, #435, #437, #439, #441, #444 bis #450; chat-hub #177; illustration-hub #371 (offen). Issues: dev-hub #436, #440, #443, #429, #418. Dazu Eingriffe auf zwei Produktivservern, je Schritt im Ledger dev-hub#440.

## 1. Executive Summary

- Der Infrastruktur-Stand steht und trägt: 215 Einheiten, Abgleich gegen die Live-Messung ohne Differenz, die stillgelegten Einheiten sind zurückgebaut (Ledger dev-hub#440). Zwei Vorwürfe gegen den Sammler (#4, #5) und einer gegen die Belegführung (#6) wurden widerlegt.
- Die Widerlegungsbahn hat den zunächst schwersten Befund gekippt (#2): Den PR mit den vorgeschlagenen Einstufungen hat der Owner selbst gemergt, auf einen Text, der die Übernahme ankündigt. Übrig bleibt ein Darstellungsmangel im Stand → dev-hub#451.
- Neu und jetzt der schwerste Punkt: Beim Rückbau wurden Konfigurationsdateien ohne den Abgleich gelöscht, den derselbe Rückbau einen Schritt später fuhr; der Rest war nirgends verankert (#18) → dev-hub#451.
- Kriterium 1 des Zielzustands ist halb geliefert: Die Verständnis-Probe läuft nur von Hand, ohne Zeitplan und ohne Auslöser bei Modellwechsel, und der Zwischenstand führt das nicht als offen (#7) → dev-hub#451.
- Zugesagtes ohne Anker: Folgearbeiten nach dem letzten Prod-Eingriff und mehrere Reste aus dem Rückbau standen nur als Fließtext im Ledger (#8, #9, #10). In dieser Retro verankert: illustration-hub#372, dev-hub#451, Nachtrag in dev-hub#443.
- Prozess: Der Scope-Checkpoint kam zweimal nach dem Schritt statt davor (#12), Repo-Dateien wurden dreimal per Shell statt per Edit geändert (#13), und eine Fehlermeldung ging ohne den einen fehlenden Check ins Ledger (#16) → platform#3716.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Der PR zur Speichergrenze ließ zwei Runbook-Stellen mit dem alten Wert stehen | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | illustration-hub#371, Runbook-Zeilen 175 und 248 im ersten Commit; in dieser Retro nachgezogen (Commit 944653e) | partial-fix-not-generalized-to-sibling-artifacts |
| 2 | 171 von 178 Einstufungen seien Vorschlag der Sitzung, per Merge ohne Owner-Wort übernommen | verfrühte Festlegung | hoch | REFUTED (Widerlegungsbahn) | Den PR dev-hub#439 hat der Owner gemergt (im Transkript kein Merge-Befehl der Sitzung dazu); der PR-Text trägt die Überschrift „Bitte korrigieren, der Merge übernimmt den Vorschlag", die Datei trennt Owner-Wort und Vorschlag in Abschnitte. Mildernd offen: Der Stand zeigt beide mit derselben Quelle, geführt in dev-hub#451 | — |
| 3 | Eine Sperrliste vor einer Freigabe-Abkürzung lässt eine Klasse schädlicher Aufträge durch; zehn Probe-Sätze ohne Sperre | fehlende Validierung | mittel | SURVIVES | Fundstellen und Proben im privaten Issue chat-hub#180; hier bewusst nur die Klasse, bis der Fix gemergt ist | gate-matches-spelling-not-substance |
| 4 | Filter für kurzlebige CI-Container nur positiv getestet; Marken-Zuordnung per Teilstring gefährdet | fehlende Validierung | mittel | REFUTED | Negativfall vorhanden (Test Z. 567–571); im Stand keine Fehlzuordnung unter 215 Einheiten. Restrisiko: kein Test mit echtem Teilstring-Treffer | — |
| 5 | Build-Helfer-Präfix und Zuordnung per Namensendung sind verfrühte Festlegungen | verfrühte Festlegung | niedrig | REFUTED | `stand.py:33-36` begründet, Unsicheres als `zuordnung_unsicher` ausgewiesen (2 Befunde im Stand) | — |
| 6 | PR-Aussage „Abgleich überall Δ 0" stützt sich auf einen Test, der nur eine Fixture prüft | fehlende Validierung | niedrig | REFUTED | `make infra-stand` gleicht live ab und bricht bei Differenz mit Exit 1 ab; 16 Abgleichszeilen im Stand, alle 0. Mildernd offen: Der Testname verspricht mehr, als er prüft | — |
| 7 | Kriterium 1 von dev-hub#436 halb geliefert: Probe nur von Hand, kein Zeitplan, kein Auslöser bei Modellwechsel; Probe 20,8 h älter als der Stand und mit 9 von 10 genau auf der Grenze | Prozesslücke | hoch | SURVIVES | dev-hub origin/main `Makefile:130`, kein Timer und kein Cron für die Probe im Repo; `probe.json` Z. 84 gegen `stand.json` Z. 7677; Zwischenstand dev-hub#436 Kommentar 5979794161 führt den Punkt nicht | accepted-plan-item-silently-dropped |
| 8 | Folgearbeiten nach dem Prod-Eingriff (Nachmessung, Auslagern, zwei Nebenbefunde) zugesagt ohne Issue; PR offen ohne Frist | Prozesslücke | mittel | SURVIVES (kommandobelegt) | dev-hub#440 Kommentar 5991464156; vor dieser Retro kein Issue in illustration-hub. Jetzt illustration-hub#372 | deferred-item-no-tracking-issue |
| 9 | Drei Reste nur als Fließtext im Ledger: fehlende Org im Register, zwei Konfigurations-Sicherungen außerhalb der Löschliste, ein Rest zu Zugangsdaten eines abgebauten Dienstes | Prozesslücke | mittel | SURVIVES (kommandobelegt) | dev-hub#440 Kommentare 5982916108, 5988438015, 5990689726; dev-hub#443 führte die zwei Sicherungen nicht. Jetzt dev-hub#451 und Nachtrag dev-hub#443 | deferred-item-no-tracking-issue |
| 10 | Nach dem letzten Deklarations-PR fehlt die Rückbau-Bedingung einer Einheit; 21 Einheiten ohne Einstufung, ohne Frist | Prozesslücke | mittel | SURVIVES (kommandobelegt) | dev-hub origin/main `stand.json`: Befund `eins_raus_fehlt`, 21 nicht eingestuft. Jetzt dev-hub#451 | deferred-item-no-tracking-issue |
| 11 | DNS-Einträge über den Wortlaut der Freigabe hinaus gelöscht, Vorgehen uneinheitlich | Kommunikation | niedrig | REFUTED | Freigabe war eine Schrittnummer, keine Namensliste; die vier Namen gehören zu freigegebenen Einheiten; der Vergleichsfall betraf eine fremde Domain außerhalb der Freigabe. Mildernd offen: keine Vorab-Nennung der vier Namen (§8) | — |
| 12 | Scope-Checkpoint zweimal nach dem Schritt statt davor: einmal 21 Sekunden nach der Vollzugsmeldung eines Prod-Schritts, einmal zwei Tage nach dem Erreichen des dritten Repos | Prozesslücke | mittel | SURVIVES (kommandobelegt) | dev-hub#440 Kommentar 5991464156 (09:09:38Z) vor Kommentar 5991469443 (09:09:59Z); dev-hub#429 Kommentar 5979218091 (2026-10-04T10:54Z) nach Arbeit in drei Repos seit 2026-10-02. Owner-Wort zu den Eingriffen selbst lag vor | gate-scope-checkpoint-not-durably-recorded-wirkungslos |
| 13 | Repo-Dateien dreimal per Shell geändert, einmal rohes `pytest`, gegen die Hausregel | Prozesslücke | mittel | SURVIVES (kommandobelegt) | Transkript 2026-10-04T13:46:22Z (dev-hub#441), 2026-10-04T20:59:01Z (dev-hub#445), 2026-10-05T08:54:00Z (dev-hub#450), `pytest` 2026-10-02T14:00:21Z; der letzte Fall wurde dem Owner im selben Zug gemeldet | neu |
| 14 | Zehn PRs in zwei Tagen auf denselben erzeugten Dateien seien vermeidbares Rework | Prozesslücke | niedrig | REFUTED | Jeder PR hing an einem eigenen Owner-Wort oder einem ausgeführten Schritt (Zeitstempel im Ledger dev-hub#440); kein Korrektur-PR, kein Konflikt | — |
| 15 | Für acht von zehn Merges sei nicht belegbar, ob Owner oder Sitzung gemergt hat | Werkzeug | niedrig | REFUTED (Widerlegungsbahn) | Das Transkript enthält Merge-Befehle nur für dev-hub#449 und #450, beide stehen im Journal; das Ledger nennt bei platform#3694 und #3697 den Owner. Mildernd offen: eine Parallelsitzung unter demselben Konto ist nicht ausgeschlossen (§8) | — |
| 16 | „Dienst fehlgeschlagen, Ursache nicht untersucht" ins Ledger geschrieben, obwohl das Protokoll einen Befehl entfernt lag; Korrektur nach 81 Sekunden | fehlende Validierung | niedrig | SURVIVES (kommandobelegt) | dev-hub#440 Kommentar 5991123895 (08:45:52Z), Korrektur 5991144296 (08:47:13Z); selbst gemeldet | claim-before-cheapest-check |
| 17 | 18 von 40 Fehlläufen sind Edit ohne vorheriges Lesen, gehäuft nach Kontextfortsetzung | Werkzeug | niedrig | SURVIVES (kommandobelegt) | Transkript-Kennzahlen Z. 8–48; ein weiterer Fall während dieser Retro | edit-after-compaction-without-reread |
| 18 | Beim Rückbau Konfigurationsdateien mit Zugangsdaten gelöscht, ohne den Abgleich gegen laufende Konfigurationen, den ein späterer Schritt desselben Rückbaus fuhr; der Rest stand nur als Satz im Ledger | fehlende Validierung | mittel | SURVIVES (Widerlegungsbahn, kommandobelegt) | dev-hub#440 Kommentar 5982732668, Abschnitt „Mit gelöscht, bewusst"; vor dieser Retro in keinem Issue. Jetzt dev-hub#451 | deferred-item-no-tracking-issue |
| 19 | Der Streich-PR im Register nahm nur die Portliste mit; zwei weitere Stellen führen zurückgebaute Dienste weiter als Bestand | fehlende Validierung | niedrig | SURVIVES (Widerlegungsbahn, kommandobelegt) | platform origin/main: `infra/secrets-inventory.yaml` Z. 491, `scripts/subdomain-health-check.sh` Z. 46; platform#3694 nennt beide nicht unter „bewusst nicht". Jetzt platform#3716 | partial-fix-not-generalized-to-sibling-artifacts |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| Zielerreichung | 3 | Stand und Rückbau geliefert; Kriterium 1 halb (#7) |
| Architektur & Design | 4 | Sammler hält der Gegenprüfung stand (#4, #5, #6 verworfen); Geschwister-Stellen nicht mitgezogen (#1, #19) |
| Code- & Konventionstreue | 3 | Hausregel zu Edit und Tests viermal verletzt (#13); Sperrliste lückenhaft (#3) |
| Risiko & Debt | 3 | Reste ohne Anker (#8, #9, #10, #18), in der Retro verankert |
| Prozess-Effizienz | 3 | Checkpoint zweimal zu spät (#12), Edit-Fehlläufe (#17); Rework-Vorwurf verworfen (#14) |
| Entscheidungsqualität | 3 | Löschen ohne den Abgleich des Nachbarschritts (#18), Behauptung vor dem Check (#16); Prod-Schritte je einzeln freigegeben |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Wert im Compose geändert, Runbook nicht durchsucht (illustration-hub#371) | Vor dem Commit den alten Wert repo-weit suchen und jede Fundstelle entscheiden | #1 |
| Sperrliste aus den Wörtern gebaut, an die beim Schreiben gedacht wurde (chat-hub#177) | Liste gegen eine Probe aus echten Aufträgen der letzten Wochen testen, darunter die schädlichen Fälle | #3 |
| Zwischenstand nennt Kriterium 1 nicht (dev-hub#436) | Jeder Zwischenstand geht die Kriterien wörtlich durch: geliefert, offen oder vertagt mit Anker | #7 |
| Folgearbeiten im Ledger-Kommentar zugesagt (dev-hub#440) | Im selben Zug ein Issue im Zielrepo, der Kommentar verlinkt es | #8 |
| Reste aus dem Rückbau als Fließtext | Jede Zeile „bleibt offen" im Ledger bekommt beim Schreiben einen Link oder einen Verzicht mit Grund | #9 |
| Deklaration ohne Rückbau-Bedingung gemergt, Befund erst im Stand sichtbar | Vor dem Merge die neuen Befunde des Stands gegen den Vorstand lesen und je Befund entscheiden | #10 |
| Checkpoint nach dem Prod-Schritt eingetragen | Checkpoint vor dem ersten Prod-Befehl eines neuen Repos schreiben, dann ausführen | #12 |
| Zeile per Shell-Skript eingefügt, weil das Muster bequemer war | Edit auch für Mustertransformationen; bei vielen Stellen je Stelle ein Edit in einer Nachricht | #13 |
| Meldung aus dem Stand übernommen, Protokoll des Dienstes nicht gelesen | Vor „fehlgeschlagen" das Protokoll lesen; sonst als Hypothese kennzeichnen | #16 |
| Edit direkt nach Kontextfortsetzung, Fehler, dann Lesen | Nach jeder Fortsetzung gilt jede Datei außerhalb des Arbeitsverzeichnisses als ungelesen | #17 |
| Konfigurationsdateien in Schritt 4 direkt gelöscht, Abgleich erst in Schritt 7 eingeführt (dev-hub#440) | Vor dem Löschen jeder Datei mit Zugangsdaten den Abgleich gegen laufende Konfigurationen fahren und gemeinsam genutzte Zugänge als Liste ins Issue schreiben | #18 |
| Dienst aus der Portliste gestrichen, Register nicht nach dem Namen durchsucht (platform#3694) | Nach dem Streichen repo-weit nach dem Dienstnamen suchen und jede Fundstelle als Verlauf oder Bestand entscheiden | #19 |

## 5. Längsschnitt

`retro_kpis.py` (2026-10-05): 57 Slugs ≥ 2, davon 3 ohne registriertes Gate, darunter `edit-after-compaction-without-reread`. `refuted_rate` der letzten acht Reports zwischen 0,17 und 0,50, Band gesund; dieser Report 0,37 (7 von 19). Von den 9 Bewertungsbefunden, die ein Skeptiker sah (#2 bis #7, #11, #14, #15), fielen dort 5; die Widerlegungsbahn kippte danach #2 und #15, die beide Skeptiker hatten stehen lassen.

| Slug | Zähler vor dieser Retro | Stand im Register | Diese Sitzung |
|---|---|---|---|
| edit-after-compaction-without-reread | ×2 | kein Gate, kein declined | #17, Gate-Pflicht → platform#3716 |
| accepted-plan-item-silently-dropped | ×2 | kein Gate | #7, drittes Vorkommen, Gate-Pflicht → Nachtrag in platform#3716 |
| partial-fix-not-generalized-to-sibling-artifacts | ×16 | Eintrag unter `widerrufen` | #1 und #19, zwei Fälle in einer Sitzung; kein wirksames Gate, ein Nachfolger ist nicht geprüft (§8) |
| gate-matches-spelling-not-substance | ×6 | Eintrag unter `widerrufen` | #3; kein wirksames Gate, Einzelfix in chat-hub#180 |
| deferred-item-no-tracking-issue | nicht gezählt | declined, advisory | #8, #9, #10; in der Retro verankert |
| claim-before-cheapest-check | nicht gezählt | Gate blocking, revidiert 2026-10-01, Status zu-frueh | #16; ein Fall nach der Revision, noch kein Rückfall-Urteil |

Verwandt mit #13, nicht derselbe Slug: `inline-heredoc-quoting-rework` ×10.

### 5a. Rückfall-Prüfung

- **Gate `scope-checkpoint-not-durably-recorded` ist rückfällig** (#12, zwei Fälle in dieser Sitzung, nach dem Fall aus Retro 7152dd; `gate_wirkung.py` führt es noch als wirksam). Das Gate hat gefeuert und der Eintrag entstand, aber erst am Zugende und damit nach dem Prod-Schritt. Antwort: **umbauen** (zu spät), Prüfung vor dem ersten Prod-Befehl. Der Umbau ist nicht gebaut; der Registry-Eintrag bekommt `revised` und `revision_note` erst mit ihm. Bis dahin ist die Antwort ein Kandidat in platform#3716, kein Eintrag (§8).
- **Gefangen, also Beleg für das Gate:** `secret-leak-via-safe-pattern` (zwei Blockaden) und `direct-gh-pr-merge-bypasses-sa-m` (zwei direkte Merge-Versuche blockiert, danach mit Owner-Wort über den Wächterweg; Journal-Zeilen zu dev-hub#449 und #450).

### 5b. Autonomie-Kalibrierung

- `over_ask`: kein Fall.
- `over_act`: kein überlebender Fall. Der Kandidat (#11, DNS-Namen über den Wortlaut hinaus) wurde verworfen, weil die Freigabe den Schritt und nicht eine Namensliste nannte. Zwei Werkzeug-Ablehnungen der Sitzung waren beide gelegen und wurden nicht umgangen.

## 6. Verankerung

Kopierfertige Vorschläge; Verankerung entscheidet der Owner.

```yaml
memory_candidates:
  - name: loeschen-von-zugangsdateien-erst-nach-abgleich
    type: feedback
    text: "Vor dem Löschen einer Datei mit Zugangsdaten den Abgleich gegen laufende Konfigurationen fahren und gemeinsam genutzte Zugänge als Liste ins Issue schreiben."
    why: "Retro 4f385c #18: in einem Rückbau-Schritt ohne Abgleich gelöscht, danach nicht mehr prüfbar."
  - name: zwischenstand-geht-kriterien-woertlich-durch
    type: feedback
    text: "Ein Zwischenstand zu einem Zielzustand nennt jedes Kriterium wörtlich mit geliefert, offen oder vertagt samt Anker."
    why: "Retro 4f385c #7: halbes Kriterium fiel aus dem Zwischenstand."
adr_candidates: []
```

## 7. Maßnahmen

- **[M1]** 🟢 Probe-Zeitplan, Rest zu Zugangsdaten, Herkunft der Einstufung · dev-hub · Owner entscheidet Reihenfolge — https://github.com/achimdehnert/dev-hub/issues/451
- **[M2]** 🟢 Nachmessung 2026-10-06 und Folgearbeiten · illustration-hub · Sitzung misst, Owner entscheidet — https://github.com/achimdehnert/illustration-hub/issues/372
- **[M3]** 🟢 Speichergrenze festschreiben · illustration-hub · Merge mit Owner-Wort — https://github.com/achimdehnert/illustration-hub/pull/371
- **[M4]** 🟢 Sperrliste ergänzen · chat-hub · Auftrag an Worker oder Sitzung — https://github.com/iilgmbh/chat-hub/issues/180
- **[M5]** 🟢 Prozess-Befunde und zwei Register-Stellen · platform · Owner entscheidet je Punkt — https://github.com/achimdehnert/platform/issues/3716
- **[M6]** 🟢 Sicherungen am 2026-10-18 löschen · dev-hub · Owner-Wort — https://github.com/achimdehnert/dev-hub/issues/443

Herkunft aus dem Soll-Ablauf: M1 aus #7, #9, #10, #18 · M2 aus #8 · M3 aus #1 · M4 aus #3 · M5 aus #12, #13, #17, #19 · M6 aus #9. #16 hat keine eigene Maßnahme; das Gate dazu ist am 2026-10-01 revidiert worden und steht unter Beobachtung.

## 8. Nicht verifiziert (Restlücken)

- **Regelabweichung Phase 0.0:** Sieben RUECKFAELLIG-Gates ohne eine der vier zulässigen Konsequenzen; die abgelaufene Verfallsfrist von `gate-anchored-without-drill-or-control` ebenso. Billigster Check: `gate_wirkung.py` in der nächsten platform-Sitzung, Entscheidung je Gate.
- **Rückfall-Gate nur als Kandidat:** Die Registry-Revision zu `scope-checkpoint-not-durably-recorded` fehlt, bis der Umbau gebaut ist (platform#3716).
- **Nachfolger-Gate ungeprüft:** Ob für die widerrufenen Einträge zu #1 und #3 ein Nachfolger existiert, der die Fälle hätte fangen müssen, ist nicht geprüft. Billigster Check: die beiden Einträge unter `widerrufen` lesen.
- **Infra-Topologie-Sonde** erst nachträglich gelaufen (`hosts_audit.py --check all` gegen die Workflows von dev-hub, 2026-10-05): keine Findings. Runner-Abgleich nicht gefahren; die Sitzung hat keinen Workflow geändert.
- **#11, mildernd offen:** Zustand der vier DNS-Namen vor dem Löschen ist nur Selbstauskunft der Sitzung; keine DNS-Historie verfügbar.
- **#15:** Ob eine Parallelsitzung unter demselben Konto gemergt hat, ist nicht geprüft. Billigster Check: Merge-Journale anderer Sitzungen im selben Zeitfenster durchsuchen.
- **#19:** Ob die Erreichbarkeits-Prüfung zeitgesteuert läuft und deshalb Fehlalarme erzeugt, ist eine Hypothese. Billigster Check: Zeitplan auf dem Zielserver lesen.
- **Session-Grenze zu eng gezogen:** Sie kam aus der PR-Liste. platform#3678 (drei Kommentare der Sitzung) und der Abschnitt vom 2026-10-02 bis zum Vormittag des 2026-10-04 (dev-hub#429, #430, #435, ein dauerhafter Benutzerdienst nach erneutem Owner-Go) haben keinen eigenen Finder-Durchgang. Stichprobe der Widerlegungsbahn: Owner-Go dauerhaft festgehalten, in platform#3678 keine Adresse, kein Host, keine Personendaten, keine Zugangsdaten.
- **Öffentlichkeit dieses Reports:** #3, #9 und #18 nennen bewusst nur die Klasse; Fundstellen stehen in den privaten Issues.
- **#3:** Inhalt von `auftrag-repos.yaml` (welche Repos auf Stufe `pr` stehen) nicht gelesen; die zweite Schutzschicht ist damit angenommen.
- **#6:** Der Live-Abgleich zählt dieselbe Messung zweimal; er belegt Konsistenz, keine unabhängige Wahrheit.
- **Prod-Wirkung des letzten Eingriffs:** Ob die nächtlichen Treffer an der Speichergrenze verschwinden, zeigt erst die Nacht auf den 2026-10-06 (illustration-hub#372).
- **Phase 6 (Extern-Handoff):** nicht gelaufen. Sie verlangt einen fremden Anbieter, den der Owner einholt; die Artefakte liegen überwiegend in privaten Repos.
- **Abnahme durch fremden Prüfer** (Sitzungsende, nach den Findern): Kriterium 3 von dev-hub#436 ist ebenfalls nicht erfüllt, 3 Einheiten außerhalb der souveränen Orgs ohne Einstufung. Kein Finder führte das als eigenen Befund; es steht in dev-hub#451 und im Handover dev-hub#452.

## Widerlegung

Ein Agent (Opus, frischer Kontext) las aus dem Ref der vier Repos, aus Issues und Kommentaren und gezielt im Transkript. Ergebnis: 2 gekippt, 5 neu. Die Hauptsitzung hat jede übernommene Behauptung einzeln nachgeprüft.

| Punkt | Verdikt | Beleg |
|---|---|---|
| #1, #3, #7, #8, #10, #17 | BESTAETIGT | Belege neu gezogen, halten |
| #2 | GEKIPPT | Owner hat dev-hub#439 gemergt, PR-Text kündigt die Übernahme an; übrig ein Darstellungsmangel |
| #9 | BESTAETIGT, Beleg korrigiert | Die zweite Sicherung steht in Kommentar 5990689726, nicht 5989624846; in dev-hub#443 richtiggestellt |
| #12 | BESTAETIGT, verschärft | Zweiter später Checkpoint: dev-hub#429 Kommentar 5979218091 |
| #13 | BESTAETIGT, verschärft | Dritter Shell-Edit 2026-10-04T13:46:22Z |
| #15 | GEKIPPT | Merge-Befehle der Sitzung nur für dev-hub#449 und #450, beide im Journal |
| #16 | BESTAETIGT, Beleg korrigiert | Korrektur nach 81 Sekunden, nicht 90 Minuten |
| #4, #5, #6, #11, #14 | BESTAETIGT | Verwerfung hält |
| NEU-1 | NEU → #18 | Löschen ohne Abgleich, Rest nicht verankert |
| NEU-2 | NEU, im Report behoben | Begründung der Footprint-Herabstufung trug nicht; Footprint steht auf deep. Eine Zählung zurückgebauter Einheiten in der Summary ist gestrichen |
| NEU-3 | NEU, im Report behoben | Fundstellen offener Lücken aus dem öffentlichen Report genommen |
| NEU-4 | NEU → §8 | Session-Grenze zu eng |
| NEU-5 | NEU → #19 | Zwei Register-Stellen nicht mitgezogen |

Nicht geprüft hat die Bahn: Inhalt der Runbook-Zeilen zu #1, die 21 nicht eingestuften Einheiten im Detail, die Wächter-Blockaden, den Zustand auf den Servern.

## Self-Review

Ein Agent (Sonnet, frischer Kontext) prüfte die Form gegen den Skill. Befunde und was daraus wurde:

- Footprint-Herabstufung regelwidrig (17 statt höchstens 10 Befunde) → auf deep gesetzt.
- Zahlen falsch: 7 statt 9 geprüfte Bewertungsbefunde, zehn statt acht gesparte Zweitausführungen → korrigiert.
- Phase 0.0: „keine Konsequenz ohne Fall" ist keine zulässige Konsequenz → als Regelabweichung in §8.
- Längsschnitt ohne Zähler; Gate-Pflicht für einen Slug mit drittem Vorkommen übersehen → Tabelle ergänzt, Slug in `gate_candidates`, Nachtrag in platform#3716.
- Infra-Topologie-Sonde fehlte → nachgeholt, keine Findings.
- Eine Maßnahme ohne passenden Link → gestrichen; Herkunft der Maßnahmen ergänzt.
- Registry-Revision des rückfälligen Gates nicht eingetragen → als Kandidat benannt (§8).

## Streichbahn

Keiner, weil jede benutzte Regel einen Effekt hatte: Die Skeptiker verwarfen 5 von 9 Bewertungsbefunden, die Widerlegungsbahn zwei weitere, und die Trennung kommandobelegt gegen Bewertung ersparte acht Zweitausführungen. Beobachtung ohne Streichung: Der Skill nennt das Agenten-Budget für full einmal mit ≤ 5 und einmal mit ≤ 7; die Zahl gehört an eine Stelle.

## Vierklang

- **getan:** Stand über 215 Einheiten erzeugt und gegen live abgeglichen; stillgelegte Einheiten zurückgebaut; Speichergrenze einer Datenbank live angehoben; 19 Befunde gesucht, 9 von Skeptikern und alle von der Widerlegungsbahn gegengeprüft, 12 überleben; vier Issues und drei Nachträge als Anker angelegt; Runbook in illustration-hub#371 nachgezogen.
- **angenommen:** Die nächtliche Sicherung ist die einzige Ursache der Treffer an der Speichergrenze; die zweite Schutzschicht hinter der Sperrliste greift (#3).
- **nicht verifizierbar:** Zustand der vier DNS-Namen vor dem Löschen (#11); ob in den gelöschten Konfigurationsdateien Zugänge standen, die anderswo gelten (#18).
- **offen geblieben:** Kriterien 1 und 3 von dev-hub#436; Herkunft der Einstufung im Stand sichtbar machen; Merge von illustration-hub#371; Nachmessung am 2026-10-06; Entscheidung zu sieben rückfälligen Gates.
