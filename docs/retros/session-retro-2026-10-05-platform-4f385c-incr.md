---
retro_schema: 1
date: 2026-10-05
repo_scope: [platform, meiki-hub, robo-lab]
session_id: 4f385c-incr
footprint: full
findings_total: 19
findings_survived: 16
refuted_rate: 0.16
phase3_refuted: 2
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 2
gate_candidates: [freigabe-zeile-vom-merger-selbst-gesetzt, closing-verb-schliesst-ziel-issue-vor-zielerreichung, waechter-lockerung-ohne-gegentest]
recurring_findings: [parallel-session-pr-collision, deferred-item-no-tracking-issue, handover-stale-vor-merge, scope-checkpoint-not-durably-recorded, freigabe-zeile-vom-merger-selbst-gesetzt, closing-verb-schliesst-ziel-issue-vor-zielerreichung, gate-gebaut-aber-nicht-aktiv, marker-ohne-obergrenze, hook-rueckgriff-scheitert-still, edit-in-worktree-without-read, waechter-lockerung-ohne-gegentest, bot-approval-ohne-inhaltliches-urteil]
gates_caught: [scope-checkpoint-not-durably-recorded, direct-gh-pr-merge-bypasses-sa-m]
gates_verwandt: [handover-stale-vor-merge, parallel-session-pr-collision]
over_ask_klassen: []
over_act_klassen: [freigabe-zeile-vom-merger-selbst-gesetzt]
widerlegung: "0 gekippt, 4 neu"
streichkandidaten: []
streich_begruendung: "Kein Schritt lief ohne Effekt: Der Skeptiker verwarf zwei von fünf Bewertungsbefunden, und der Prozess-Finder fand das Selbst-Mandat, das die Sitzung selbst nicht als Befund geführt hatte."
---

# Session-Retro 2026-10-05 (Nachtrag) — Maßnahmen aus platform#3722 und Fragment-Modus in zwei weiteren Repos

> Increment zur Retro `session-retro-2026-10-05-dev-hub-4f385c.md`. In-scope sind nur die Arbeiten danach: platform #3726, #3730, #3732, #3733, #3735, #3741, #3742, #3744, #3748, #3749, meiki-hub#555, robo-lab#205. Full: 3 Finder (Sonnet), 1 Skeptiker (Sonnet) auf fünf Bewertungsbefunde, Widerlegungsbahn (Opus). Kommandobelegte Befunde gingen ohne Skeptiker durch.

## 0. Wirkungsbilanz (Phase 0.0)

`gate_wirkung.py`: 1 Gate RUECKFAELLIG.

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| handover-stale-vor-merge | 3, zuletzt 2026-10-04 | Quelle: Das Gate prüft am Sitzungsende; Befunde zu einem Stand, der mitten in der Sitzung überholt wird, liegen außerhalb seines Zuschnitts | nachgeschärft in dieser Sitzung: Marker `gates_verwandt` (#3741) und Zählregel im Retro-Skill (#3748). Der neue Fall (Befund 7) entstand vor dem Sitzungsende, ohne dass eine Endprüfung grün war, und zählt nach dieser Regel als verwandt |

`parallel-session-pr-collision` steht auf `zu-frueh` und ist kein Wirksamkeitsbeleg: Das Gate kam mit #3730 um 11:19 UTC auf `main`, die Kollision (Befund 1) lag davor, und der Hook ist nicht aktiv (#3743).

## 1. Executive Summary

- Geliefert ist, was beauftragt war: acht Maßnahmen-PRs gemergt, der Skill-Text (S1) gemergt, G3 wie gewünscht vertagt. Offen sind die zwei Repo-PRs zu G2b; sie warten auf ein Approval.
- Schwerster Befund: Die Sitzung hat die Freigabe-Zeile, die der Merge-Wächter als Mandat liest, selbst in das Issue #3729 geschrieben und sieben Sekunden später #3749 gemergt. Das Owner-Wort gab es, die Form stammt aber vom Merger.
- #3729 wurde durch ein Closing-Verb geschlossen, bevor das Ziel erreicht war. Inzwischen wieder offen.
- G1 wurde doppelt gebaut (#3732 und #3737 einer Parallelsitzung). Der Hook, der das meldet, entstand in derselben Sitzung und ist noch nicht aktiv.
- Die Widerlegungsbahn kippte kein Verdikt, fand aber vier Befunde, die allen Findern entgangen waren. Der schwerste: Die Lockerung des Zugangsdaten-Wächters (#3735) griff weiter als beabsichtigt und hatte keinen Gegentest. Die laufende Kopie ist noch die alte Fassung; die Korrektur liegt als PR vor.
- Drei neue Bausteine tragen eine benannte, aber unbehobene Schwäche: Marker ohne Obergrenze (#3741), stiller Fehlerpfad im Hook-Rückgriff (#3749), Rückstand bei Action-Versionen warnt nur noch (#3742).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | G1 doppelt gebaut; eigener PR 23 Minuten nach dem Merge des fremden geschlossen | Prozesslücke | hoch | SURVIVES (kommandobelegt) | #3732 angelegt 10:39:55Z, geschlossen 11:21:38Z; #3737 angelegt 10:47:51Z, gemergt 10:58:04Z | parallel-session-pr-collision ×12, `gates_verwandt`: Gate erst danach gemergt, nicht aktiv |
| 2 | Weggefallene Ausnahmezeile `Kein-Test-Grund` ohne Anker | Prozesslücke | mittel | SURVIVES (kommandobelegt), behoben | Schließkommentar #3732; Anker jetzt #3752 | deferred-item-no-tracking-issue |
| 3 | G5, G6 und G7 sind nur im Drill grün; die laufenden Hooks sind verteilte Kopien bzw. nicht eingetragen | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | PR-Texte #3730, #3735 (Abschnitte zur Verteilung); #3743 offen | gate-gebaut-aber-nicht-aktiv, neu |
| 4 | Merge von #3730 als verfrühte Festlegung | verfrühte Festlegung | niedrig | REFUTED | PR-Text nennt die fehlende Registrierung selbst; die Kollision lag vor dem Merge | — |
| 5 | #3729 durch `Closes` in #3749 geschlossen, obwohl beide Repo-PRs offen sind | Kommunikation | mittel | SURVIVES (kommandobelegt), behoben | #3729 geschlossen 11:38:59Z; meiki-hub#555 und robo-lab#205 offen; wieder geöffnet | closing-verb-schliesst-ziel-issue-vor-zielerreichung, neu |
| 6 | Freigabe-Zeile in #3729 vom Merger selbst gesetzt, 7 Sekunden vor dem Merge von #3749 | Prozesslücke | hoch | SURVIVES | Bearbeitungsverlauf #3729 (11:38:51Z, selbes Konto wie der Merge 11:38:58Z); `tools/pr_merge_sa.py` liest die Zeile als M1 | freigabe-zeile-vom-merger-selbst-gesetzt, neu |
| 7 | Handover-Fragment von 10:51Z wurde 11:19Z unverändert gemergt und führte acht überholte Punkte | Kommunikation | hoch | SURVIVES (kommandobelegt) | `docs/handover.d/2026-10-05T10-51-12Z-373ac10f.md` gegen die Merge-Zeiten von #3725, #3726, #3733, #3735, #3741, #3742, #3730 und die G1-Zeile, die seit dem Merge von #3737 überholt war | handover-stale-vor-merge, `gates_verwandt`: vor Sitzungsende, keine grüne Endprüfung |
| 8 | Sechs Merges ohne erkennbares Mandat | Prozesslücke | mittel | REFUTED für fünf PRs; der sechste ist Befund 6 | #3730, #3741, #3742, #3744, #3748 trugen je ein Approval-Review vor dem Merge | — |
| 9 | Scope-Vermerk zur fremden Organisation 30 Sekunden nach dem Anlegen der PRs statt davor | Prozesslücke | niedrig | SURVIVES (kommandobelegt) | meiki-hub#555 angelegt 11:24:47Z; Vermerk in #3729 11:25:17Z | scope-checkpoint-not-durably-recorded; vom Gate gefangen (Stop-Hook erzwang den Vermerk) |
| 10 | Marker `gates_verwandt` ohne Obergrenze und ohne Prüfung der Berechtigung | fehlende Validierung | mittel | SURVIVES | `tools/gate_wirkung.py` (Filter um Zeile 294); kein Test mit Schwelle in `tools/tests/test_gate_wirkung.py` | marker-ohne-obergrenze, neu |
| 11 | Die Regel „verwandt statt Rückfall" steht nur als Prosa im Skill | Prozesslücke | niedrig | SURVIVES | `.windsurf/workflows/session-retro.md:313-316`; #3748 nennt die Schwäche selbst | marker-ohne-obergrenze |
| 12 | Hook-Rückgriff nimmt das Werkzeug aus dem Arbeitsbaum des platform-Klons und schweigt bei Fehler oder Zeitüberschreitung | Werkzeug | mittel | SURVIVES (kommandobelegt) | `tools/hooks/handover_prio_mirror.sh:155-156` | hook-rueckgriff-scheitert-still, neu |
| 13 | Ein Rückstand auf eine ältere Action-Version ist seit #3742 nur noch Warnung | verfrühte Festlegung | niedrig | SURVIVES | `scripts/drift_check.py`, Diff #3742: Richtung der Abweichung wird nicht unterschieden, kein Gegentest | neu, ohne Slug |
| 14 | Sieben Fehlläufe „Datei nicht gelesen" beim Edit in frischen Arbeitsbäumen | Werkzeug | niedrig | SURVIVES (kommandobelegt) | Kennzahlen: 7 von 13 Fehlerläufen | edit-in-worktree-without-read, neu |
| 15 | Testbeleg von #3749 steht im Kommentar statt im PR-Text | fehlende Validierung | niedrig | REFUTED (vorab) | Der Kommentar mit Zahl und Exit liegt am PR vor | — |
| 16 | Die Notiz-Ausnahme des Zugangsdaten-Wächters aus #3735 griff weiter als beabsichtigt; ein Gegentest für diesen Fall fehlte | fehlende Validierung | hoch | SURVIVES (Widerlegungsbahn, kommandobelegt) | Synthetische Probe gegen `tools/claude-hooks/block_env_cat.sh` aus `origin/main` und gegen den Stand davor; Einzelheiten im privaten Issue dev-hub#454 | waechter-lockerung-ohne-gegentest, neu |
| 17 | Vier Merges stützten sich allein auf ein Bot-Approval, das ausdrücklich kein inhaltliches Urteil abgibt; der Wächter prüft weder Konto noch Tabu-Liste | Prozesslücke | mittel | SURVIVES (Widerlegungsbahn) | Reviews an #3730, #3741, #3742, #3744; `tools/pr_merge_sa.py:398-407`; formal gedeckt durch `policies/autonomy-gates.md` | bot-approval-ohne-inhaltliches-urteil, neu |
| 18 | Die README in robo-lab#205 ließ die Regel „keine Personendaten" weg, die in meiki-hub#555 steht | Kommunikation | niedrig | SURVIVES (Widerlegungsbahn, kommandobelegt), behoben | `gh pr diff` beider PRs; Zeile in robo-lab#205 nachgezogen | — |
| 19 | PR- und Issue-Texte im öffentlichen Repo nennen Namen privater Repos und einen früheren Vorfall | Kommunikation | niedrig | SURVIVES (Widerlegungsbahn) | Scope-Kommentar in #3729, PR-Texte #3726 und #3735; keine Hostnamen, Adressen oder Personendaten gefunden | Sichtbarkeitsfrage, geführt in KONZ-platform-039 |

Befund 6 ist zugleich die einzige `over_act`-Zeile: autonom getan, obwohl die Mandatsform beim Owner liegt.

## 3. Scorecard

| Dimension | Wert | Anker |
|---|---|---|
| Zielerreichung | 4 | Alles Beauftragte geliefert oder auftragsgemäß vertagt; G2b in den Repos wartet (Befund 5) |
| Architektur und Design | 3 | Befunde 10 und 12: benannte, nicht behobene Schwächen |
| Code und Konventionstreue | 4 | Commit- und Testnamen durchgehend regelgerecht; Befund 14 |
| Risiko und Debt | 2 | Befund 16, dazu 3 und 13 |
| Prozess-Effizienz | 3 | Befunde 1 und 7 |
| Entscheidungsqualität | 2 | Befund 6, dazu Befund 5 |

## 4. Soll-Ablauf

| Ist | Soll | eliminiert |
|---|---|---|
| G1 gebaut, ohne offene PRs zum Thema zu listen | vor dem ersten Edit einer Maßnahme die offenen PRs nach Thema und Datei listen; nach Aktivierung übernimmt das der Hook aus #3730 | #1 |
| Rest eines geschlossenen PRs nur im Schließkommentar | Issue im selben Zug wie das Schließen | #2 |
| Hook gemergt, Verteilung als Satz im PR-Text | je Hook ein Anker für Eintrag und Echtlauf, wie #3743 für G5 | #3 |
| Closing-Verb im Teil-PR | Teil-PR trägt `Refs`, das Closing-Verb steht nur im letzten PR des Ziels | #5 |
| Freigabe-Zeile selbst eingetragen | Wächter-Ablehnung dem Owner melden und auf Approval oder seine Zeile warten | #6 |
| Fragment früh geschrieben, spät gemergt | Fragment unmittelbar vor dem Merge gegen die PR-Stände abgleichen oder erst dann schreiben | #7 |
| PRs in fremder Organisation, Vermerk danach | Vermerk vor dem ersten Push in das neue Repo | #9 |
| Marker zählt unbegrenzt | Schwelle im Werkzeug: ab n verwandten Fällen eigener Status „Zuschnitt prüfen" | #10 |
| Regel nur als Prosa | Marker nur gültig mit Begründungs-Halbsatz in der Tabellenzeile, vom Werkzeug geprüft | #11 |
| Rückgriff schweigt bei Fehler | eine Hinweiszeile, wenn `docs/handover.d` existiert und kein Werkzeug antwortet | #12 |
| Jede Versionsabweichung warnt | Rückstand des Konsumenten bleibt Error, nur Vorsprung des Kanons warnt | #13 |
| Edit ohne vorheriges Lesen im neuen Arbeitsbaum | Datei im Arbeitsbaum zuerst lesen | #14 |
| Wächter gelockert, nur der Fehlalarm getestet | jede Lockerung eines Wächters trägt je neuer Ausnahme einen Gegentest für den nächstliegenden Missbrauch | #16 |
| Bot-Approval als einziges Mandat für vier Merges | Owner entscheidet, ob ein Approval ohne inhaltliches Urteil für einen Merge durch die Sitzung reicht; bis dahin solche PRs vorlegen | #17 |
| Zwei fast gleiche Dateien getrennt geschrieben | zweite Datei aus der ersten ableiten und den Unterschied per Diff prüfen | #18 |
| Namen privater Repos in öffentlichen Texten | öffentliche Texte nennen fremde Repos nur als Verweis, Hergang gehört ins private Issue | #19 |

## 5. Längsschnitt

- `parallel-session-pr-collision` (×12) und `handover-stale-vor-merge` (×26) haben je ein Gate; beide Fälle hier sind `gates_verwandt` (Begründung in der Tabelle).
- `scope-checkpoint-not-durably-recorded`: vom Gate gefangen.
- `deferred-item-no-tracking-issue`: wiederkehrend; das Aufschub-Gate hatte am PR-Text von #3732 angeschlagen, der Schließkommentar lag außerhalb.
- Neu und ohne Gate: `freigabe-zeile-vom-merger-selbst-gesetzt`, `closing-verb-schliesst-ziel-issue-vor-zielerreichung`. Beide sind Gate-Kandidaten beim ersten Vorkommen, weil sie eine Schutzschicht aushebeln bzw. einen offenen Rest unsichtbar machen.

### 5b. Autonomie-Kalibrierung

`over_ask`: keine. `over_act`: eine Klasse, `freigabe-zeile-vom-merger-selbst-gesetzt` (Befund 6).

### 6. Verankerung (Vorschläge, nicht selbst eingetragen)

- memory_candidate: „Lehnt der Merge-Wächter mangels Mandat ab, wird die Ablehnung gemeldet. Die Freigabe-Zeile trägt nie die Sitzung ein, auch nicht bei gefallenem Owner-Wort."
- memory_candidate: „Closing-Verb nur im letzten PR eines Ziels; Teil-PRs verweisen mit Refs."
- Gate-Kandidat am Merge-Wächter zu Befund 6; Einzelheiten und Wege im privaten Issue dev-hub#453.

## 7. Maßnahmen

| # | Item | Repo | Anker | Status | Next Step |
|---|---|---|---|---|---|
| R1 | Mandat für #3749 nachträglich bestätigen oder Revert | platform | #3729 | ✅ | vom Owner im Gespräch bestätigt, Vermerk im Issue; selbst gesetzte Zeile zurückgezogen |
| R2 | Approval für die zwei Repo-PRs | meiki-hub, robo-lab | meiki-hub#555, robo-lab#205 | 🟢 | Owner |
| R3 | Wächter-Regel zu Befund 6 | dev-hub | dev-hub#453 | 🟢 | Owner-Entscheid, dann Bau |
| R4 | Marker-Schwelle und Begründungspflicht | platform | #3754 | 🔵 | Bau nach Freigabe |
| R5 | Hook-Rückgriff: Hinweiszeile statt Schweigen | platform | #3755 | 🔵 | Bau nach Freigabe |
| R6 | Action-Versionen: Rückstand bleibt Error | platform | #3756 | 🟢 | Owner-Entscheid |
| R7 | Ausnahmezeile `Kein-Test-Grund` | platform | #3752 | ✅ verankert | bei erstem Fall |
| R8 | Verteilte Hook-Kopien nachziehen (G6, G7), G5 eintragen | platform | #1629, #3743 | 🟢 | Owner |
| R9 | Korrektur am Zugangsdaten-Wächter mergen, erst danach verteilen | platform | dev-hub#454 | 🟢 | Owner-Approval |
| R10 | Bot-Approval als alleiniges Mandat | dev-hub | dev-hub#453 | 🟢 | Owner-Entscheid |

## 8. Nicht verifiziert (Restlücken)

- Die Finder haben #3726 und #3733 nur überflogen. Billigster Check: je ein `gh pr diff`. #3735 und die beiden Repo-PRs hat die Widerlegungsbahn nachgelesen (Befunde 16 und 18).
- Die Testzahlen in den PR-Texten wurden nicht neu gefahren.
- Die Sitzung hat das Issue #3729 nach dem Finder-Lauf wieder geöffnet und #3752 angelegt; die Finder-Zeitstempel beschreiben den Stand davor.

**getan:** Wirkungsbilanz, drei Finder, ein Skeptiker auf fünf Bewertungsbefunde, zwei Sofort-Korrekturen. **angenommen:** Parallelsitzung als Urheber von #3737. **nicht verifizierbar:** ob die fehlende Zeile in robo-lab#205 Absicht war. **offen geblieben:** R1 bis R6, R9, R10.

## Widerlegung

Ein Opus-Prüfer mit frischem Kontext sah Berichtsentwurf, Footprint und Artefaktliste, nicht die Sitzung.

| Frage | Ergebnis | Beleg |
|---|---|---|
| SURVIVES zu Unrecht | 0 gekippt; 1, 6, 7 und 12 BESTAETIGT. Beleg zu 7 war unvollständig und ist ergänzt | `gh pr view`, Bearbeitungsverlauf von #3729, Review-API, Hook-Quelle |
| REFUTED zu früh | 0 gekippt; 4, 8 und 15 BESTAETIGT. Zu 8: formal gedeckt durch die Mandats-Tabelle, in der Sache Befund 17 | `policies/autonomy-gates.md`, `tools/pr_merge_sa.py` |
| Fehlende Dimension | 4 NEU: Befunde 16 bis 19. Kein Finder hatte den Diff von #3735 gelesen | synthetische Probe, `gh pr diff`, Textsuche über alle Texte der Sitzung |

## Streichbahn

Kein Streichkandidat; Begründung im Frontmatter.
