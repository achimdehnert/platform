---
retro_schema: 1
date: 2026-09-22
repo_scope: [platform, chat-hub]
session_id: 8946e8
footprint: deep
findings_total: 14
findings_survived: 12
refuted_rate: 0.14
phase3_refuted: 2
pre_refuted: 0
scores:
  zielerreichung: 5
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 1
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [test-asserts-the-case-in-mind-not-the-harmful-one, check-reads-a-field-the-writer-never-fills, gating-labelled-job-not-in-required-checks]
recurring_findings: [test-asserts-the-case-in-mind-not-the-harmful-one, dod-reinterpreted-only-in-pr-body, issue-offen-nach-gemergtem-fix, gate-modul-prueft-weniger-als-sein-name, claim-before-cheapest-check, untested-command-handed-to-user, host-config-file-not-documented]
gates_caught: [claim-before-cheapest-check, untested-command-handed-to-user]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "2 gekippt, 4 neu"
streichkandidaten: [retro-skeptiker-ohne-transkriptzugriff]
---

# Session-Retro 2026-09-22 — Der Lotse bekommt eine Stimme (platform + chat-hub)

## 1. Executive Summary

- **Der Auftrag ist erfüllt und im Betrieb belegt:** Der Owner sprach um 10:47:08 eine
  Sprachnachricht, das Transkript lag 9 Sekunden später vor, die gesprochene Antwort nach 14.
  Vier von fünf Stufen aus KONZ-060 sind mit echten Ereignis-IDs abgenommen, die fünfte
  (Vorlesen) läuft als Zeitgeber.
- **Der schwerste Befund betrifft Code, der am selben Tag gemergt wurde — und er hat zwei
  Stockwerke.** Die Sperrliste, die verhindern soll, dass ein 👍 einen unumkehrbaren Schritt
  freigibt, ließ erst **7 von 10** realen Formulierungen durch (#1) — und bekam, wie sich
  danach zeigte, im Echtbetrieb **überhaupt nie einen Text zu sehen** (#11): 148 von 148
  abgelegten Entwurfszeilen hatten kein `body`-Feld. Der PR-Titel nannte sie „harte
  Sperrliste". Beides behoben (chat-hub#132, jetzt fail-closed).
- **Dreimal dieselbe Wurzel:** ein Test, der die eigene Annahme prüft statt der Wirklichkeit —
  beim Variantenselektor (vom Owner gefunden), bei der Wortliste (von einem Finder) und bei
  der leeren Prüfung (von der Widerlegungsbahn). Der Slug
  `test-asserts-the-case-in-mind-not-the-harmful-one` steht bei **×11** und hat kein Gate.
- **Die Kontrollkette hat einen gemeinsamen blinden Fleck gezeigt:** drei Finder prüften die
  Wortliste, der Skeptiker die Urteile, der Meta-Prüfer die Form — alle nahmen an, dass die
  Prüfung prüft, was ihr Name sagt. Erst der Lauf, der fragte „funktioniert dieser Schutz
  überhaupt?", fand das Loch.
- **Ein Nebenfund war größer als die Suche:** Auf der Jagd nach einem Weg für den Bot in einen
  Videocall kam heraus, dass die Medienports seit dem Aufbau im August von außen gefiltert
  waren — **Videotelefonie hat für Menschen nie funktioniert** und war niemandem aufgefallen.
- **Zwei Befunde wurden widerlegt** (V1 ohne Deckung, Prod-Freigabe schwach belegt), beide zu
  meinen Gunsten und beide, weil den Findern das Transkript fehlte — daraus wird der
  Streichkandidat dieser Retro.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Sperrliste gegen Außenwirkung per Flexion/Kompositum umgehbar — „Deployment", „Secrets rotieren", „Berechtigungen", „Datenlöschung", „Produktivumgebung", „Tokens", „Zugangsdaten" liefen durch | fehlende Validierung | **kritisch** | SURVIVES | `deploy/lotse_auftrag.py` (origin/main vor #132), eigene Messung 2026-09-22: **7 von 10 Proben falsch**; behoben in chat-hub#132, danach 0 von 11 | `test-asserts-…` ×11 |
| 2 | Die Tests der Sperrliste prüften fünf Sätze, die wortwörtlich auf die eigene Regex passten — keine unabhängig formulierte Gegenprobe | fehlende Validierung | mittel | SURVIVES | `tests/test_lotse_auftrag.py::test_should_refuse_reaction_for_outward_effect` (5 Fälle vor #132, 15 danach + 5 Gegenproben) | dieselbe Wurzel wie #1 |
| 3 | Host-Konfigurationsdatei `~/.config/chat-hub/vorlesen.env` (`LOTSE_VORLESEN_ROOM`, `LOTSE_VORLESEN_VON`) ist nur als Inline-Kommentar erklärt, in keinem Runbook | Prozesslücke | mittel | SURVIVES | `git grep -l LOTSE_VORLESEN_ROOM origin/main -- docs README.md` → **0 Treffer** | `host-config-file-not-documented` |
| 4 | Positivkontrolle lief real, wurde aber nie ins Issue zurückgeschrieben — chat-hub#123/#124 blieben OPEN mit 0 Kommentaren | Prozesslücke | mittel | SURVIVES | `gh issue view 123/124` → OPEN, Kommentare=0; `session_abgleich.py` nennt genau diese Fälle (7 Befunde) | `issue-offen-nach-gemergtem-fix` ×9 · **gates_caught** |
| 5 | KONZ-062 führte V1 in §1/REC-1 als bestanden, in der maßgeblichen Kill-Gate-Tabelle als „offen" mit dem alten Ausgangswert — vier von sechs Zeilen veraltet | Werkzeug | mittel | SURVIVES | `git show origin/main:docs/konzepte/KONZ-platform-062-…md` Z.224 gegen Z.88; behoben in #3378 | `dod-reinterpreted-only-in-pr-body` ×6 |
| 6 | Sechs Issues wurden mit Beleg-Kommentar geschlossen, ihre `- [ ]`-Kästchen aber nie abgehakt — DoD nur im Kommentar | Prozesslücke | niedrig | SURVIVES | `session_abgleich.py --issues` → 6× „Issue-Body trägt noch unangehakte Kästchen"; nachgeholt für #116–#119, #123 | `dod-reinterpreted-only-in-pr-body` ×6 · **gates_caught** |
| 7 | Nacharbeits-PR #126 war vermeidbar: #125 wurde gemergt, bevor die Positivkontrolle am echten Signal lief — bei einem sicherheitsrelevanten Freigabe-Gate | fehlende Validierung | mittel | SURVIVES | Merge #125 13:12:15Z → Merge #126 14:20:48Z (68 min); PR-#126-Body nennt die Ursache wörtlich | `test-asserts-…` ×11 |
| 8 | Prod-Eingriff (Hetzner-Firewall) ist dokumentiert, aber ohne ausdrückliche Rückbau-Zeile im PR | Prozesslücke | niedrig | SURVIVES | PR #3374, `infra/hosts.yaml`: Vorher/Nachher vollständig, Rollback nur implizit aus dem Zwei-Zeilen-Diff | — |
| 9 | „V1-Messung überschritt den Auftrag ‚Konzept schreiben, nicht bauen' ohne Owner-Deckung" | verfrühte Festlegung | mittel | **REFUTED** | Transkript 11:17:40Z „66 jetzt" (= V1 sofort starten) und 11:33:00Z „70 ja" (= 20 Turns messen); Messergebnis 11:40:07Z. **Einschränkung der Widerlegungsbahn:** die Bedeutung der Ziffern entsteht aus dem Board-Text, den derselbe Agent geschrieben hat — der Beleg ist stark, aber nicht unabhängig | — |
| 10 | „Die Prod-Freigabe ist die einzige ohne zitierbare Belegstelle" | fehlende Validierung | mittel | **REFUTED** | Freigabe steht im durablen Artefakt (PR #3374 und chat-hub#127: „Owner-Freigabe 2026-09-22, Security-Config-Gate") und im Transkript 14:20:56Z | — |
| 11 | **Die Sperrliste bekam im Echtbetrieb nie einen Text.** `merke_gesendet()` legte eigene Nachrichten ohne `body` ab; `pruefe_go_reaktion` las den leeren String, die Sperre fand nie etwas — **jede** Reaktion galt als Freigabe, auch auf einen Prod-Entwurf | fehlende Validierung | **kritisch** | SURVIVES | Eigene Messung: **148 von 148** `gesendet`-Zeilen auf dem Host ohne `body` (Schlüssel nur `event_id, gesendet, room_id, sender, ts`); End-to-End-Probe vor dem Fix akzeptiert „Soll ich das Deployment auf prod starten?". Behoben in chat-hub#132 (`body` ablegen + fail-closed) | `test-asserts-…` ×11, eine Ebene unter #1 |
| 12 | ADR-249 steht in der Datei auf `accepted`, in `index.json`/`INDEX.md` weiter auf `proposed` — und der Job „Platform-specific ADR checks" war auf #3371 **2× rot**, konnte aber nicht blocken, weil er nicht in den Required Checks steht | Werkzeug | hoch | SURVIVES | `index.json` → `("ADR-249", "proposed")`, `INDEX.md` Z.217 `Proposed`; `gh pr checks 3371` → 2× `fail`. Index nachgezogen in #3378 | — |
| 13 | Die zwei Netze gegen Außenwirkung widersprechen sich: `vorschlaege.py` erlaubt die Klasse `basis-abstand` ausdrücklich für den Daumen, ihr eigener Vorschlagstext enthält „mergen" → die Sperre schlägt an und reißt die ganze Morgen-Meldung mit; zugleich deckt **ein** Daumen bis zu drei Vorgänge ohne Zuordnung | verfrühte Festlegung | mittel | SURVIVES | `ERLAUBT["0.4.4 basis-abstand"]` enthält „mergen"; `lotse_briefing.sh` hängt alle Fragen an **eine** Nachricht | — |
| 14 | chat-hub#127 wurde mit „Damit ist auch UDP 7882 belegt" geschlossen — §8 desselben Reports führt genau das als nicht verifizierbar | Kommunikation | niedrig | SURVIVES | Schlusskommentar 14:39:26Z gegen §8 „trennt nicht zwischen UDP und TCP-Fallback 7881" | `claim-before-cheapest-check` ×86 |

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| Zielerreichung | **5** | Verankert an **#7** als einziger Reibung — kein Befund stellt die Zielerreichung selbst in Frage. Belegt: Owner-Sprachnachricht 10:47:08 → Audio-Antwort 10:47:22, Hörprobe bestätigt; dazu die reparierte Videotelefonie (chat-hub#127), die niemand beauftragt hatte |
| Architektur & Design | **3** | Trennung Produkt-Voice (ADR-249) vs. Assistenten-Stimme sauber gezogen. Abzüge: zwei widersprechende Statusträger in KONZ-062 (#5) und **zwei Netze gegen Außenwirkung, die sich gegenseitig blockieren** (#13) — sie wurden nie gegeneinander laufen gelassen |
| Code- & Konventionstreue | **4** | Lazy-Imports, eigene Fehlerklassen, Tests je Modul, Host-Fix ins IaC gespiegelt. Abzug: Host-Konfigdatei undokumentiert (#3) |
| Risiko & Debt | **1** | Das Kernziel dieser Dimension ist verfehlt: der einzige Schutzwall des neuen Freigabewegs war nicht nur löchrig (#1), er **sah nie einen Text** (#11) — jede Reaktion hätte einen Prod-Entwurf freigegeben. Gefunden erst von der Widerlegungsbahn, nachdem Finder, Skeptiker und ich daran vorbeigelaufen waren |
| Prozess-Effizienz | **3** | 12 PRs, keine Dublette, zwei Nacharbeits-PRs. Korrektur gegenüber dem ersten Entwurf: **nicht** „alle grün" — auf #3371 war „Platform-specific ADR checks" 2× rot und wurde übermergt, weil der Job trotz Etikett „gating" nicht in den Required Checks steht (#12) |
| Entscheidungsqualität | **3** | Drei Owner-Entscheidungen sauber belegt, die S4-Empfehlung „erst messen" hat Wochen gespart. Abzüge: „harte Sperrliste" war eine Behauptung ohne Falsifikationstest (#1/#11), und die ADR-Schwellen-Begründung in KONZ-061 („der Freigabe-Perimeter wird nicht erweitert") stützte sich auf genau diese blinde Sperre |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Die Sperrliste wurde aus den fünf Beispielsätzen der Konzeptzeile D5 gebaut und im PR-Titel „hart" genannt | Bei jedem **Muster** (Regex, Parser, Filter): vor dem Merge drei Formulierungen prüfen, die **nicht** aus der eigenen Liste stammen — bei deutschem Text zwingend ein Kompositum und ein Plural | #1 |
| Die Tests parametrisierten genau die Sätze, aus denen die Regex entstand | Ein Test zu einem Muster enthält **immer** eine Gegenprobe-Gruppe: Fälle, die fangen sollen, und Fälle, die durchgehen sollen | #2 |
| `vorlesen.env` wurde angelegt und nur im Skript kommentiert | Jede neue Datei außerhalb des Repos (`~/.config`, `~/.cache`, systemd) bekommt **im selben PR** eine Zeile im Runbook mit Pfad, Schlüsseln und Wirkung | #3 |
| Nach bestandener Positivkontrolle ging es direkt zur nächsten Stufe | Die Positivkontrolle wird **zuerst ins Issue** geschrieben, dann beginnt die nächste Stufe — der PR-Text ist kein Tracking | #4 |
| KONZ-062 trug den Status an zwei Stellen, eine davon veraltet | Ein Dokument hat **einen** maßgeblichen Statusträger; steht der Status auch in der Prosa, wird die Prosa beim Merge nachgezogen oder entfernt | #5 |
| Issues wurden mit Beleg-Kommentar geschlossen, die Kästchen blieben leer | Schließen heißt: Kästchen abhaken **und** Beleg kommentieren — `session_abgleich.py --issues` vor dem Schließen laufen lassen, nicht erst bei `/session-ende` | #6 |
| #125 wurde gemergt, bevor die echte Reaktion des Owners vorlag | Ein Gate, das eine **Freigabe** prüft, wird erst gemergt, wenn die Positivkontrolle am echten Signal gelaufen ist — bei allem anderen bleibt „merge, dann messen" zulässig | #7 |
| Der Firewall-PR dokumentierte Vorher/Nachher, aber nicht den Rückweg | Jeder Prod-Eingriff bekommt im PR eine Zeile „Rückbau: <konkreter Befehl/Schritt>" | #8 |
| Die Prüfung las ein Feld, das der Schreibpfad nie füllte — und die Fixture erfand es | Wo eine Prüfung ein Feld liest, wird der Test gegen eine Zeile geführt, die der **Schreibpfad selbst erzeugt** hat (hier: `merke_gesendet`), nie gegen eine von Hand gebaute. Und: fehlt das Feld, wird **abgelehnt**, nicht durchgewunken | #11 |
| Ein Statuswechsel im ADR wurde ohne Index-Lauf gemergt, der rote Prüfjob war nicht blockend | Nach jeder Frontmatter-Änderung an einem ADR `scripts/gen_adr_index.py` laufen lassen; einen Job, der „gating" heißt, entweder in die Required Checks aufnehmen oder das Etikett streichen | #12 |
| Zwei Sperren wurden unabhängig voneinander gebaut und nie gegeneinander laufen gelassen | Wenn zwei Netze denselben Fall abdecken sollen, wird **einmal** die Ausgabe des einen durch das andere geschickt — hier: `als_text()` der Vorschläge durch `gesperrt_wegen()` | #13 |
| Ein Issue wurde mit einer Aussage geschlossen, die der eigene Report als unbelegt führt | Vor dem Schließen die Abschluss-Aussage gegen die eigene Restlücken-Liste prüfen — was dort als „nicht verifizierbar" steht, darf im Schlusskommentar nicht als belegt auftauchen | #14 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über **132 Reports**:

| Slug | Zähler | heute | Konsequenz |
|---|---|---|---|
| `claim-before-cheapest-check` | ×86 | Hook feuerte **2×** | **gates_caught** — beide Male nachgebessert, bevor die Antwort rausging |
| `untested-command-handed-to-user` | ×10 | Hook feuerte **1×** | **gates_caught** — der Pull wurde daraufhin selbst ausgeführt |
| `test-asserts-the-case-in-mind-not-the-harmful-one` | **×11** (neu: heute) | Befunde #1, #2, #7 | 🚨 **GATE-PFLICHT, kein Gate vorhanden** — Kandidat, siehe §7 |
| `issue-offen-nach-gemergtem-fix` | ×9 | Befund #4 | **Gate rückfällig → nachgeschärft** (§5a) |
| `gate-modul-prueft-weniger-als-sein-name` | ×6 | Befund #1 | **Gate rückfällig → ausgeweitet** (§5a) |
| `dod-reinterpreted-only-in-pr-body` | ×6 | Befunde #5, #6 | von demselben Modul gefangen; Konsequenz in §5a mitbehandelt |
| `host-config-file-not-documented` | ×1 (neu) | Befund #3 | unter Beobachtung; bei ×2 gate-pflichtig |

Memory-Abgleich (`grep` gegen `<auto-memory>/MEMORY.md`): `feedback_reporting_table_format`,
`feedback_repo_session_start_before_any_edit` und `project_raum_auftraege_an_claude_code`
existieren und wurden eingehalten; kein Widerspruch gefunden.

## 5a. Rückfall-Prüfung

`python3 tools/gate_wirkung.py` meldet zwei Gates als `RUECKFAELLIG` (je 3 Rückfälle nach
Bau, zuletzt 2026-09-17). Beide bekommen eine der drei zulässigen Konsequenzen, eingetragen
als `revised` + `revision_note` im **bestehenden** Eintrag — kein zweites Gate unter neuem
Namen, keine Frist verlängert. `tools/gate_verankerung_check.py --neu` läuft grün über beide.

| Gate | Ursache | Konsequenz | Beleg |
|---|---|---|---|
| `issue-offen-nach-gemergtem-fix` | **Quelle — zu spät.** Das Modul trifft den Fall genau, läuft aber erst in `/session-ende`; da liegen die Issues schon | **nachschärfen**: Aufruf gehört vor das Schließen einer Stufe, nicht ans Sitzungsende (§4, Zeilen zu #4/#6) | `session_abgleich.py --issues --seit 2026-09-22` nennt #124 OPEN trotz gemergtem #128 plus sechs Issues mit unangehakten Kästchen — korrekt, nur zu spät; eingetragen als `positivkontrolle.nachtrag_2026_09_22` |
| `gate-modul-prueft-weniger-als-sein-name` | **Quelle — sieht die Familie nicht.** Prüft nur Registry-Einträge auf Drill-Deckung | **ausweiten** auf code-seitige Prüfungen, deren Name Härte behauptet | Befund #1 ist genau dieser Fall außerhalb der Registry: eine Sperrliste, die im PR-Titel „hart" hieß und 7 von 10 Formulierungen durchließ. Neue `positivkontrolle` mit Datum, `faengt` um den Fall ergänzt |

**Was ich zuerst falsch gemacht habe:** Der erste Entwurf dieses Abschnitts stufte beide Gates
als `gates_caught` ein und ließ sie unverändert — eine **vierte** Konsequenz, die der Skill
nicht vorsieht. Der Meta-Prüfer hat das gefangen; einer der beiden Slugs war dabei ganz aus
dem Frontmatter verschwunden. Die Begründung war nicht falsch (beide Melder feuerten und
benannten die Fälle), aber „der Melder hat recht" entbindet nicht davon, die Ursache zu
behandeln — sie verschiebt sie nur von der Anzeige auf Zeitpunkt und Reichweite.

## 5b. Autonomie-Kalibrierung

- **`over_ask`: 0.** Eine einzige Rückfrage (`AskUserQuestion`) in der ganzen Sitzung, und sie
  betraf zwei Entscheidungen, die der Owner allein treffen konnte: den Zuschnitt von P1
  (Reaktion als Freigabeweg = neuer Befehlskanal) und die Tiefe von S4. Beides ist
  Gate-Material, keine Überfrage.
- **`over_act`: 0.** Der einzige Gate-Schritt der Sitzung — die Änderung an der
  Prod-Firewall — lief **nach** ausdrücklicher Freigabe (14:20:56Z „hetzner hast du alle
  rechte -> freigabe erteilt"). Die zwölf PRs wurden sämtlich vom Owner gemergt; kein
  `--admin`, kein Selbst-Merge.
- Zum Vergleich: der Längsschnitt über 132 Retros liegt bei Ø 0,15 `over_ask` und Ø 0,49
  `over_act` je Retro.

## 6. Verankerung

**memory_candidates** (kopierfertig, Verankerung entscheidet der Owner):

```markdown
---
name: feedback_pattern_needs_adversarial_counter_sample
description: Ein Muster (Regex/Parser/Filter) wird nie gegen die eigene Beispielliste getestet — drei fremde Formulierungen, bei Deutsch zwingend Kompositum und Plural
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-09-22-sperrliste-kompositum
---
Wer ein Muster aus Beispielsätzen baut und es mit denselben Sätzen testet, prüft seine
Annahme, nicht die Wirklichkeit. Realfall 2026-09-22 (chat-hub#125): Die Sperrliste, die
verhindern sollte, dass ein 👍 einen Prod-Schritt freigibt, ließ 7 von 10 alltäglichen
Formulierungen durch — „Deployment", „Secrets rotieren", „Berechtigungen", „Datenlöschung",
„Produktivumgebung" —, weil sie ganze Wörter suchte. Vierzehn Tests waren grün.

**Why:** Deutsch bildet Komposita und flektiert; eine Wortliste aus dem Konzepttext trifft
die Sprache der Nutzer nicht. Derselbe Fehler traf am selben Tag den 👍 selbst (Element
sendet ihn mit Variantenselektor, chat-hub#126).

**How to apply:** Vor dem Merge drei Formulierungen prüfen, die NICHT aus der eigenen Liste
stammen; bei deutschem Text mindestens ein Kompositum und einen Plural. Im Test immer zwei
Gruppen: fangen soll / durchgehen soll. Bei Sperren die Richtung des Irrtums bewusst wählen
und im Code begründen. Siehe [[feedback_positivkontrolle_mit_echten_daten]].
```

```markdown
---
name: feedback_host_config_file_needs_runbook_line
description: Jede Datei außerhalb des Repos (~/.config, ~/.cache, systemd) bekommt im selben PR eine Runbook-Zeile
metadata:
  type: feedback
---
Realfall 2026-09-22 (chat-hub#121): `~/.config/chat-hub/vorlesen.env` mit
`LOTSE_VORLESEN_ROOM`/`LOTSE_VORLESEN_VON` steuert, in welchem Raum der Lotse die Zeitung
vorliest. Erklärt wird sie nur als Kommentar im Bash-Skript; `git grep` über `docs/` und
`README` findet null Treffer.

**Why:** Host-Zustand, den nur der Quelltext erklärt, ist beim nächsten Hostwechsel verloren —
und der nächste Operator rät Schlüsselnamen.

**How to apply:** Neue Datei außerhalb des Repos ⇒ im selben PR eine Runbook-Zeile mit Pfad,
Schlüsseln, Wirkung und Verhalten bei Abwesenheit. Gilt auch für systemd-Units und Modelle
in Caches.
```

**adr_candidates:** keine. Alle Entscheidungen dieser Sitzung lagen unterhalb der
ADR-Schwelle (Additionen nach bestehendem Muster) oder wurden an einem bestehenden ADR
verankert (ADR-249 Rev 2).

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Sperrliste Flexion/Komposita | chat-hub | https://github.com/iilgmbh/chat-hub/pull/132 | 🔵 ready | mergen (du) |
| 2 | Kill-Gate-Tabelle KONZ-062 | platform | https://github.com/achimdehnert/platform/pull/3378 | 🔵 ready | mergen (du) |
| 3 | Gate `test-asserts-…` bauen | platform | https://github.com/achimdehnert/platform/issues/2234 | 🟢 offen | Gate-Vorlage, ×11 |
| 4 | Runbook-Zeile `vorlesen.env` | chat-hub | https://github.com/iilgmbh/chat-hub/issues/119 | 🟢 offen | Zeile im Runbook (ich) |
| 5 | Rückbau-Zeile bei Prod-PRs | platform | https://github.com/achimdehnert/platform/pull/3374 | 🟢 offen | Konvention prüfen (du) |
| 6 | Issues 123/124 nachgetragen | chat-hub | https://github.com/iilgmbh/chat-hub/issues/124 | ✅ done | — |
| 7 | Kästchen abgehakt (5 Issues) | chat-hub | https://github.com/iilgmbh/chat-hub/issues/116 | ✅ done | — |
| 8 | Skeptiker ohne Transkript | platform | https://github.com/achimdehnert/platform/issues/2374 | 🟢 offen | Streichbahn, §Streichbahn |
| 9 | Sperre war blind, jetzt fail-closed | chat-hub | https://github.com/iilgmbh/chat-hub/pull/132 | 🔵 ready | mergen (du) |
| 10 | ADR-Index nachgezogen | platform | https://github.com/achimdehnert/platform/pull/3378 | 🔵 ready | mergen (du) |
| 11 | ADR-Job in Required Checks | platform | https://github.com/achimdehnert/platform/pull/3371 | 🟢 offen | aufnehmen oder Etikett streichen (du) |
| 12 | Zwei Netze blockieren sich | platform | https://github.com/achimdehnert/platform/issues/3369 | 🟢 offen | Vorschlagstext gegen Sperre laufen lassen |
| 13 | Gate `check-reads-a-field-…` | platform | https://github.com/achimdehnert/platform/issues/2234 | 🟢 offen | neuer Gate-Kandidat aus #11 |

## 8. Nicht verifiziert (Restlücken)

**Getan:** `gate_wirkung.py` und `retro_kpis.py` gelaufen; drei Finder und ein Skeptiker in
frischem Kontext; vier kommandobelegte Befunde selbst nachgemessen (Issue-Status,
Kill-Gate-Zeile, `git grep` auf Doku, PR-Textvergleich); die Sperrlisten-Lücke mit einer
eigenen Messreihe belegt (7/10 vorher, 0/11 nachher); `session_abgleich.py` gegen die
heutigen Artefakte ausgeführt.

**Angenommen:** Dass die drei Finder ihre Artefakte tatsächlich aus `origin/main` gezogen
haben — ich habe ihre Prompts so gebaut und vier ihrer Befunde stichprobenartig nachgeprüft,
aber nicht jeden einzelnen ihrer Befehle wiederholt.

**Nicht verifizierbar:** Ob die **UDP**-Strecke 7882 nach der Firewall-Änderung wirklich
offen ist — der LiveKit-Mux antwortet nur auf ICE mit Zugangsdaten. Der Owner-Videoanruf
(Bild und Ton) ist der beste verfügbare Beleg, trennt aber nicht zwischen UDP und dem
TCP-Fallback 7881. Billigster fehlender Check: `livekit-cli` oder ein Browser-Call mit
erzwungenem UDP.

**Offen geblieben:** (a) Ob von den 277 Bash-Aufrufen ein nennenswerter Teil vermeidbar war —
der Prozess-Finder hat das ausdrücklich als Hypothese und nicht als Befund geführt, weil ihm
der Kommandoverlauf fehlte; billigster Check wäre eine Auszählung der Wiederholungen im
Transkript. (b) Ob die Sperrliste nach #132 noch Lücken hat — geprüft sind elf Formulierungen,
nicht die Sprache. (c) Ob der Vorlese-Zeitgeber morgen früh wirklich feuert (erster
Werktagslauf 2026-09-23 08:45).

## Widerlegung

Phase 3b (Tier 4, frischer Kontext, nur Report-Entwurf + Artefaktliste) — Ergebnis:
**2 gekippt, 4 neu.** Das ist der wertvollste Lauf dieser Retro gewesen.

**Gekippt:**
1. Der **Abschluss** von Befund #1. Der Report hatte „behoben in chat-hub#132, danach 0 von 11"
   geschrieben — die Widerlegungsbahn zeigte, dass der Fix eine Regex härtet, die im Betrieb
   nie einen Text zu sehen bekommt (#11). Nachgemessen: 148 von 148 Zeilen ohne `body`.
   Der Fix ist jetzt vollständig (fail-closed), aber der erste Abschluss war falsch.
2. Die Scorecard-Zeile **Prozess-Effizienz**: „alle grün, kein rotes Gate" ist widerlegt —
   auf #3371 war der ADR-Job 2× rot (#12).

**Neu:** #11 (kritisch), #12 (hoch), #13 (mittel), #14 (niedrig). Keiner der drei Finder und
auch nicht der Skeptiker hatte sie.

**Rest bei einem REFUTED:** Bei Befund #9 merkt die Widerlegungsbahn zu Recht an, dass die
Bedeutung der Zurufe „66 jetzt" / „70 ja" aus einem Board-Text stammt, den derselbe Agent
geschrieben hat — der Beleg ist stark, aber nicht unabhängig. Das Verdikt bleibt REFUTED, die
Einschränkung steht in der Beleg-Spalte.

**Was das über diese Retro sagt:** Die drei Finder prüften die Wortliste, der Skeptiker prüfte
die Urteile, der Meta-Prüfer prüfte die Form — und der einzige Lauf, der die Frage stellte
„funktioniert dieser Schutz überhaupt?", fand das Loch. Drei Ebenen Kontrolle hatten einen
gemeinsamen blinden Fleck: alle nahmen an, dass die Prüfung das prüft, was ihr Name sagt.

## Streichbahn

**Kandidat: `retro-skeptiker-ohne-transkriptzugriff`** — Belegart **kein Effekt**.

Beide Bewertungsbefunde dieser Retro (#9, #10) wurden von den Findern erhoben, weil ihnen das
Sitzungstranskript fehlte: Sie sahen nur PR- und Issue-Texte und schlossen daraus auf fehlende
Owner-Deckung. Beide fielen im Skeptiker-Lauf sofort — nicht durch bessere Analyse, sondern
weil der Skeptiker die Transkript-Zeilen mitbekam, die die Finder nicht hatten. Das ist ein
Lauf, der Budget kostet (~84k Token) und dessen Ergebnis mit einer Zeile Kontext im
Finder-Prompt vorweggenommen wäre.

**Vorschlag:** Nicht den Skeptiker streichen, sondern die Lücke: Der Skill soll in Phase 1
verlangen, dass die **wörtlichen Owner-Nachrichten** (aus `retro_transkript_kennzahlen.py`,
das sie ohnehin ausgibt) als Datei an **jeden Finder** gehen — nicht erst an den Skeptiker.
Zwei von zehn Befunden dieser Retro wären dann gar nicht erst entstanden, und die
`refuted_rate` von 0,2 wäre keine Rechtfertigung, sondern eine echte Quote.
