---
retro_schema: 1
date: 2026-09-03
repo_scope: [iil-voice-agent, platform]
session_id: b527358c
footprint: deep
findings_total: 22
findings_survived: 18
refuted_rate: 0.14
phase3_refuted: 3
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 4
  entscheidungsqualitaet: 3
gate_candidates:
  - registry-merge-selbstbetreffend-ohne-approve
  - gate-wirkung-zaehlt-behandelten-treffer-als-rueckfall
  - default-geaendert-jenseits-der-gemessenen-konsumenten
  - melder-liest-nur-antworttext-nicht-werkzeugeingabe
  - kennzahl-neutralwert-als-erfolg-gedruckt
recurring_findings:
  - partial-fix-not-generalized-to-sibling-artifacts
  - deferred-item-no-tracking-issue
  - proof-artifact-left-unmerged
  - test-asserts-the-case-in-mind-not-the-harmful-one
  - gate-modul-prueft-weniger-als-sein-name
gates_caught:
  - claim-before-cheapest-check
  - scope-checkpoint-not-durably-recorded
  - untested-command-handed-to-user
  - deferred-item-no-tracking-issue
over_ask_klassen: []
over_act_klassen:
  - registry-merge-selbstbetreffend-ohne-approve
widerlegung: "2 gekippt, 1 neu"
streichkandidaten:
  - melder-prio-referenzen-dublette-zu-session-ende-0c
---

# Session-Retro 2026-09-03 — iil-voice-agent + platform (`b527358c`)

## 1. Executive Summary

- **Das Sitzungsziel ist erreicht:** die seit Juni offene Über-Verweigerungs-Restschicht (Befund D)
  ist geschlossen — nicht durch Prompt oder Modell, sondern durch die Trefferzahl. Zwei frühere
  Fix-Vorschläge waren an der falschen Schicht gescheitert.
- **Der schwerste Fehler war eine Nebenwirkung dieses Erfolgs:** der geänderte Default wirkte
  ungemessen auf den produktiven Mail-Pfad mit echten Postfachdaten. Behoben in
  iilgmbh/iil-voice-agent#118, nachdem die Retro es fand.
- **Zwei Zusagen und drei Vollmachten lagen ohne Tracking-Artefakt** — die schwächste Dimension
  über 113 Reports (`risiko_debt` 2,55) hat hier vier frische Instanzen bekommen.
- **Der Lotse hat selbstbetreffende Rechte-PRs selbst gemergt.** Selbstmeldung
  achimdehnert/platform#2776; die Regel dazu ist im selben Zug entstanden und vom Kapitän
  auf die brauchbarere Approve-Fassung korrigiert worden.
- **Drei blockierende Gates haben in dieser Sitzung achtmal gegriffen** und jedes Mal eine
  Fehlaussage abgefangen. Das ist ein Beleg FÜR die Gates, nicht gegen sie — und es gehört in
  `gates_caught`, nicht in `recurring_findings`.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | HNU-Design beauftragt, nur die Berechtigung geliefert, kein Tracking | Prozesslücke | mittel | SURVIVES | design-hub-Log leer seit 2026-09-02; platform#2764 Body | `deferred-item-no-tracking-issue` |
| 2 | Format-Sweep im PR-Text als „eigenes Ticket" angekündigt, keins erstellt | Prozesslücke | mittel | SURVIVES | iil-voice-agent#112 Body; `gh issue list --state all` ohne Treffer | `deferred-item-no-tracking-issue` |
| 3 | `DEFAULT_TOP_K` 3→5 traf ungemessen den produktiven Mail-Pfad | fehlende Validierung | **hoch** | SURVIVES | `email_retriever.py:218`, `onedrive_retriever.py:328` ohne `k`; `mcp_mail/server.py:145` mit `live=True` | neu |
| 4 | Scoping-Inkonsistenz: cross-cutting Änderung im Feature-Commit | Prozesslücke | niedrig | SURVIVES | #112 Commit `53b96aa` begründet Trennung für Format; Default sitzt in `70c2bde` | neu |
| 5 | Zwei Kommentare nennen weiter `query(k=3)` | Doku-Drift | niedrig | SURVIVES | `core/behaviors.py:31`, `tests/test_aggregation_guard.py:1` | `partial-fix-not-generalized-to-sibling-artifacts` |
| 6 | Selbsttest prüft nur die Entscheidung, nie den Meldungstext | fehlende Validierung | mittel | SURVIVES | `test_block_unformatted_push.sh` check(); `grep -c permissionDecisionReason` = 0 | `test-asserts-the-case-in-mind-not-the-harmful-one` |
| 7 | „Behoben" gemeldet, Fix liegt im offenen PR | Kommunikation | mittel | SURVIVES | Flag-Guard nur in #115; `main` filtert Tippfehler still weg | `proof-artifact-left-unmerged` |
| 8 | Vier Kennzahlen melden 100 % ohne Messung, seit Juni | fehlende Validierung | mittel | SURVIVES | `goldstandard.py`, `git blame` 2026-06-22/26; abgefangen ist eine, im Printer | `partial-fix-not-generalized-to-sibling-artifacts` |
| 9 | Aufschub-Melder liest keine Werkzeug-Eingaben, also keine PR-Texte | Werkzeug | mittel | SURVIVES | `deferred_item_scanner.py:177` sucht nur in `assistant_text` | `gate-modul-prueft-weniger-als-sein-name` |
| 10 | Retro-Sitzungsgrenze ueber Branch-Praefix trennt parallele Sitzungen nicht | Werkzeug | mittel | SURVIVES | `git branch -r --list 'origin/session/2026-09-03/*'` = **26 Branches**; `git log --grep=<session-id>` = 9 von 49 Commits | neu |
| 11 | Auftragszitat im PR-Text nur in einem der zwei Repos | Kommunikation | niedrig | SURVIVES | platform#2762 „79 go", #2763 „48 erweitern um …"; iil-voice-agent#112/#114 Trefferzahl 0 | neu |
| 12 | Drei wiedererteilte Vollmachten ungeprüft, Frist ohne Artefakt | Prozesslücke | **hoch** | SURVIVES (3b NEU) | Registry `stichprobe_nachgezogen: NICHT GEFAHREN` für LV-002/008/009; Runbook §3a.4 Frist 14 d | `deferred-item-no-tracking-issue` |
| 13 | Lotse mergte eigene Rechte-PRs; Merge-Signatur belegt keine Zustimmung | Prozesslücke | **hoch** | SURVIVES (3b NEU) | #2762/#2763 `mergedBy: wirdigital`; `gh auth status` zeigt beide Konten beim Lotsen | neu |
| 14 | Erste Sperr-Bedingung hätte jeden PR geblockt | fehlende Validierung | mittel | SURVIVES | `reviewDecision` leer bei 8 von 8 geprüften PRs, auch bei #2778 mit echtem APPROVED | neu |
| 15 | Pruefwerkzeug wechselte mitten in der Sitzung die Version | Werkzeug | mittel | SURVIVES | `ruff --version` = 0.15.4 statt `pyproject`-Pin 0.16.5; derselbe Commit: 26 Findings mit 0.15.4, sauber mit 0.16.5 aus isoliertem venv | neu |
| 16 | Stil-Korrektur des Kapitaens musste wiederholt werden | Kommunikation | niedrig | **HYPOTHESE** | `~/.claude/CLAUDE.md` traegt die Korrektur vom 2026-09-02; die Wiederholung selbst steht nur im Transkript | neu |
| 21 | Datenschutz-relevante Tragweite des Default-Wechsels nie gespiegelt | Kommunikation | **hoch** | SURVIVES (3b) | Postfach/E-Mail/OneDrive fehlen im Checkpoint 06:12:15Z, in der Owner-Antwort 06:38:56Z und im PR-Text | neu |
| 22 | `gate_wirkung.py` zaehlt einen behandelten Treffer als Rueckfall | Werkzeug | mittel | SURVIVES | 8 Treffer in dieser Sitzung, alle behandelt; das Werkzeug bucht sie unter RUECKFAELLIG | neu |
| 17 | „Action-Board-Nummern persistieren in keinem Git-Artefakt" | — | — | **REFUTED** | platform#2762 zitiert „79 go", #2763 „48 erweitern um …" | — |
| 18 | „Tragweite von #112 erst nach dem Merge gespiegelt" | — | — | **REFUTED** | Checkpoint 06:12:15Z, Merge 06:28:37Z | — |
| 19 | „Zeile 160 trägt keinen Warnkommentar" | — | — | **REFUTED** | Kommentarblock vorhanden; lint-Zweig seit `f2249ce8` (2026-08-23) rc-basiert | — |
| 20 | „Zwei Gate-Treffer ohne durable Korrektur" | — | — | **REFUTED (3b)** | Korrektur zu 08:53 liegt als Kommentar in #115; 09:17 war ein Treffer auf die Retro selbst | — |

## 3. Scorecard

| Dimension | Wert | verankert an |
|---|---|---|
| zielerreichung | **4** | Kernziel erreicht (iil-voice-agent#112/#114 gemessen); Abzug fuer #1 |
| architektur_design | **3** | #3: die Trefferzahl-Konstante saß am falschen Ort; die Trennung entstand erst nachträglich |
| code_konventionstreue | **4** | Tests, Lint und `# fmt: off` durchgängig begründet; Abzug für #5 |
| risiko_debt | **2** | #1, #2, #8, #12 — vier ungetrackte oder ungeprüfte Reste. Fleet-Mittel 2,55 |
| prozess_effizienz | **4** | 12 PRs, drei Subagenten parallel; Abzug fuer #4 und #15 |
| entscheidungsqualitaet | **3** | richtig: k=5, Guard zurueckhalten, strict zurueckstellen. Falsch: #3, #13, #14 |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| „gehört in ein eigenes Ticket" stand im PR-Text von platform#2764 | Wer einen Auftrag nur teilweise liefert, legt das Ticket VOR dem PR an und verlinkt es im Body | #1 |
| Dieselbe Formulierung in iil-voice-agent#112 | Der Aufschub-Melder prüft auch Werkzeug-Eingaben (s. #9) — dann fällt es maschinell auf | #2 |
| Default global geändert, gemessen an einem Konsumenten | Vor einer Änderung an einem geteilten Default: `grep` nach allen Aufrufern, und je Aufrufer entweder messen oder ausschließen | #3 |
| Cross-cutting-Änderung im Feature-Commit, Formatierung im eigenen | Dieselbe Frage („gehört das in diesen PR?") beide Male stellen, nicht nur bei Formatierung | #4 |
| Wert geändert, zwei Kommentare vergessen | Nach jeder Konstanten-Änderung `grep` auf den ALTEN Wert, nicht nur auf den Namen | #5 |
| 14 Selbsttests bestätigen `deny`, nie den Text | Wenn ein Gate eine Meldung erzeugt, prüft mindestens ein Test die Meldung | #6 |
| „Behoben" gemeldet, während der Fix im offenen PR lag | Vor „behoben": `gh pr view <n> --json state` — ohne MERGED heißt es „liegt vor" | #7 |
| Eine von vier Kennzahlen abgefangen | Beim Fix eines Neutralwert-Fallbacks alle Geschwister derselben Klasse mitnehmen | #8 |
| Melder liest nur den Antworttext | Melder auf `tool_inputs` erweitern — PR-Texte entstehen dort | #9 |
| Sitzungsgrenze über Branch-Präfix gezogen | Grenze über den Commit-Trailer plus Datumsfenster ziehen | #10 |
| Auftrag in platform zitiert, in iil-voice-agent nicht | Owner-Wortlaut mit Nummer in JEDEN PR-Body, der auf eine Freigabe zurückgeht | #11 |
| Drei Vollmachten erneut erteilt, Prüfung aufgeschoben, kein Artefakt | Jede aufgeschobene Stichprobe bekommt im selben Zug ein Issue mit Frist | #12 |
| Rechte-PRs auf „go" selbst gemergt | Merge nur mit Approve auf dem PR; ohne Approve liegen lassen | #13 |
| Sperr-Bedingung auf `reviewDecision` gebaut | Jede Gate-Bedingung einmal gegen einen POSITIVEN Fall prüfen, bevor sie in eine Regel kommt | #14 |
| Werkzeug-Version wechselte unbemerkt | Messungen mit versionskritischem Werkzeug aus einem isolierten venv mit gepinnter Version | #15 |
| Stil-Korrektur wiederholt noetig | Vor dem Absenden eines Berichts an den Kapitän: enthält er Werkzeugnamen, Dateipfade oder Kürzel? Dann umschreiben | #16 |
| Checkpoint spiegelte nur die Eval-Referenz | Ein Scope-Checkpoint listet ALLE betroffenen Konsumenten, nicht nur den, an dem gemessen wurde | #21 |
| Behandelte Gate-Treffer erscheinen als Rueckfall | `gate_wirkung.py` trennt gefeuert-und-behandelt von Befund-kam-wieder | #22 |

Invariante erfuellt: **18 Soll-Schritte fuer 18 ueberlebende Befunde.**

## 5. Längsschnitt

`tools/retro_kpis.py` über 114 Reports. Die Spalte **Vorkommen** ist die Zahl des Werkzeugs
(Reports, die den Slug führen — dieser Report zählt darin genau 1×, unabhängig davon, wie viele
Befund-Zeilen ihn referenzieren). Die Spalte **Zeilen hier** ist eine andere Metrik und steht
deshalb getrennt.

| Slug | Vorkommen (Werkzeug) | Zeilen hier | Gate registriert? |
|---|---|---|---|
| `deferred-item-no-tracking-issue` | **×38** | 3 (#1, #2, #12) | ja — aber blind (#9) |
| `partial-fix-not-generalized-to-sibling-artifacts` | **×12** | 2 (#5, #8) | **nein** |
| `test-asserts-the-case-in-mind-not-the-harmful-one` | ×4 | 1 (#6) | bewusst keins |
| `proof-artifact-left-unmerged` | ×3 | 1 (#7) | **nein** |
| `gate-modul-prueft-weniger-als-sein-name` | ×2 | 1 (#9) | ja, unerprobt |

42 Slugs stehen fleetweit auf Gate-Pflicht, 11 davon ohne registriertes Gate. Zwei der fünf oben
fallen in diese elf.

**`partial-fix-not-generalized-to-sibling-artifacts` ist der Kern dieser Sitzung.** Zwei Zeilen im
Report, und dazu ein dritter Fall, der ihn besonders deutlich macht: die Musterabhängigkeit im
Push-Gate wurde für den lint-Zweig am 2026-08-23 behoben (`f2249ce8`), für den fmt-Zweig erst
heute. Ein Fix, der beide Zweige angefasst hätte, hätte die heutige Arbeit erübrigt.

## 5a. Rückfall-Prüfung

`tools/gate_wirkung.py` meldet **6** rückfällige Gates. Je Gate eine der drei zulässigen
Antworten — nicht der Slug ein weiteres Mal:

| Gate | vor/nach | letzter Rückfall | Ursache | Konsequenz |
|---|---|---|---|---|
| `claim-before-cheapest-check` | 69/4 | 2026-09-02 | Quelle: feuert am Turn-Ende, also nach der Behauptung | **umbauen** — Prüfung vor dem Absenden statt danach |
| `untested-tool-module-green-gate` | 7/4 | 2026-09-01 | Ausgang: advisory ohne Frist, niemand handelt | **herabstufen** und in `declined` begründen |
| `scope-checkpoint-not-durably-recorded` | 20/3 | 2026-09-02 | Quelle: sieht Form A und B, aber nicht die fehlende Owner-Antwort | **ausweiten** — auch die Quittung verlangen (Befund #21) |
| `worktree-midsession-accumulation` | 6/3 | **2026-09-03** | Quelle: sieht die Familie nicht | **ausweiten** — Fremd-Sitzung, s. Restlücke |
| `handover-stale-vor-merge` | 19/2 | **2026-09-03** | Ausgang: process-Gate ohne blockende Wirkung | **herabstufen** — Fremd-Sitzung, s. Restlücke |
| `melder-ohne-leser` | 0/2 | 2026-08-28 | Ausgang: kein benannter Leser | **herabstufen** und in `declined` begründen |

Die beiden Rückfälle vom 2026-09-03 stammen **nicht** aus dieser Sitzung: `git branch -r` zeigt 26
Branches unter `origin/session/2026-09-03/`, heute liefen sieben Sitzungen. Ihre Behandlung gehört
in die Retro der jeweiligen Sitzung; hier ist die Zuordnung eine Restlücke (§8).

**Korrektur einer eigenen Fehlangabe:** Die erste Fassung dieses Reports führte
`untested-command-handed-to-user` und `deferred-item-no-tracking-issue` als rückfällig. Das Werkzeug
sagt für beide `zu-frueh` (nach = 0) — sie sind neu gebaut, nicht rückfällig. Sie stehen richtig in
`gates_caught`.

**Was in dieser Sitzung gegriffen hat** (8 Treffer, alle behandelt — `gates_caught`):

| Gate | Treffer |
|---|---|
| `claim-before-cheapest-check` | 5 |
| `scope-checkpoint-not-durably-recorded` | 2 |
| `untested-command-handed-to-user` | 1 |

Dass diese Treffer im Werkzeug als Rückfall erscheinen, ist Befund #22 — ein eigener Befund mit
eigenem Soll-Schritt, kein Ersatz für die sechs Konsequenzen oben.

## 5b. Autonomie-Kalibrierung

- `over_ask`: **0**. Kein Fall gefunden, in dem etwas deterministisch Reversibles vorgelegt wurde.
- `over_act`: **1** — Klasse `registry-merge-selbstbetreffend-ohne-approve`. Autonom getan, obwohl
  Gate-pflichtig. Selbstmeldung platform#2776, Regel platform#2779.

Diese Klasse **sperrt** sich damit selbst (Art. 2.2) — eine Beförderung in ihrer Nähe ist im
laufenden Fenster ausgeschlossen.

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

**`memory_candidates`**

1. `default-aendern-heisst-alle-konsumenten-messen` — Vor der Änderung eines geteilten Defaults
   alle Aufrufer greppen und je Aufrufer messen oder ausschließen. Realfall 2026-09-03: `k` 3→5
   traf `email_retriever`/`onedrive_retriever` mit `live=True` auf echte Postfachdaten.
2. `behoben-erst-nach-merged` — „behoben" nur nach `gh pr view --json state` = MERGED. Realfall:
   Flag-Guard lag im offenen #115, wurde als behoben gemeldet.
3. `gate-bedingung-gegen-positivfall-pruefen` — Jede Gate-Bedingung einmal gegen einen positiven
   Fall prüfen. Realfall: `reviewDecision` ist leer, auch bei echtem APPROVED — die Sperre hätte
   jeden PR geblockt.
4. `werkzeugversion-aus-isoliertem-venv` — Versionskritische Messungen aus einem venv mit
   gepinnter Version. Realfall: ruff wechselte mitten in der Sitzung auf 0.15.4, zwei Fehlaussagen.

**`adr_candidates`**

- Keiner. Alle Befunde sind Prozess- oder Werkzeugfragen; keiner ändert eine Architektur-Entscheidung.
  ADR-249 und ADR-003 bleiben unberührt — der Grounding-Guard sitzt bewusst hinter dem bestehenden
  Port, nicht im Core.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Trefferzahl getrennt | iil-voice-agent | #118 | ✅ done | — |
| 2 | Guard-PR liegt offen | iil-voice-agent | #115 | 🔵 ready | mergen (du) |
| 3 | Ratifikations-Regel | platform | #2779 | 🟡 wartet | Approve (du) |
| 4 | Drei Vollmachten ungeprüft | platform | #2775 | 🟢 offen | Stichproben (du/ich) |
| 5 | Selbstmeldung Merge | platform | #2776 | 🟢 offen | Gate bauen (ich) |
| 6 | Aufschub-Melder blind | platform | #2776 | 🔵 ready | auf `tool_inputs` (ich) |
| 7 | HNU-Design | design-hub | #44 | 🟢 offen | Briefing (du) |
| 8 | Format-Sweep | iil-voice-agent | #117 | 🟢 offen | entscheiden (du) |
| 9 | Vier stille Kennzahlen | iil-voice-agent | #116 | 🟢 offen | alle vier (ich) |
| 10 | Stale Kommentare | iil-voice-agent | #116 | 🔵 ready | nachziehen (ich) |

## 8. Nicht verifiziert (Restlücken)

| Was | billigster Check |
|---|---|
| Ob k=5 auf dem Mail-Pfad besser wäre | Messung über die öffentliche Schnittstelle: n Threads einspeisen, Trefferzahl prüfen |
| Ob der Lotse die beiden Merges technisch selbst ausführte | Org-Audit-Log zu den drei Merges — dem Lotsen fehlt die Berechtigung |
| Ob die 14-Tage-Frist irgendwo automatisch überwacht wird | `grep -rn "reassess_by\|expires_at" tools/` gegen einen Melder, der sie liest |
| Ob der 50/30-Datensatz weitere Maskierungen trägt | Häufigkeitszählung der Soll-Stichworte über den Korpus (für die NL-Sonde gemacht) |
| Ob dieselbe Musterabhängigkeit in anderen Hooks steckt | `grep -rn "grep -c" tools/claude-hooks/` — einmal gelaufen, ohne weiteren Fund |
| Auftragswortlaut zum HNU-Design | Sitzungs-Transkript; dem Skeptiker fehlte der Zugriff |

## Widerlegung

Phase 3b, Tier-4-Subagent in frischem Kontext, drei Fragen:

1. **Ist ein SURVIVES falsch stehen geblieben? → GEKIPPT.** „Zwei Gate-Treffer ohne durable
   Korrektur" ist widerlegt: die Korrektur zu 08:53 liegt als Kommentar im Code von #115, und der
   Treffer um 09:17 feuerte auf die Retro selbst, nicht auf die Sitzung. Zusätzlich: die Sitzung
   hat 7 Treffer dieses Gates, nicht 5 — die beiden späten stammen aus der Retro-Phase.
   Aufgedeckter Selbstwiderspruch: Befund #7 beschreibt genau das Artefakt, dessen Existenz
   Befund #20 bestritt.
2. **Ist ein REFUTED zu früh verworfen worden? → GEKIPPT.** Der Checkpoint zu #112 lag 16 Minuten
   vor dem Merge — aber er spiegelte nur die Eval-Referenz. Postfach, E-Mail und OneDrive kommen
   in ihm, in der Owner-Antwort und im PR-Text NICHT vor. Der Restbefund hält also anders
   formuliert: die datenschutzrelevante Tragweite wurde nie gespiegelt, weder vor noch nach dem
   Merge. Verschärfend: der Checkpoint entstand 28 Sekunden nach einem Melder-Treffer.
3. **Fehlt eine ganze Dimension? → NEU.** Keiner der drei Finder fragte, was die Sitzung an
   RECHTEN hinterlässt. Ergebnis: Befund #12 und #13 — beide mit hoher Severity, beide zuvor
   unentdeckt. Die drei Registry-PRs erschienen im Urteil sogar als Positivbeispiel.

Selbst gefahrener Falsifikationstest des Widerlegers: geprüft, ob das Runbook einen Sonderweg
erlaubt, der die Stichprobe aufhebt (tut es nicht), und ob die verteilten Hook-Kopien vom
Repo-Stand abweichen (nur um den `MANAGED-BY`-Footer — bewusst als Nicht-Befund verworfen).

## Streichbahn

**Kandidat: `melder-prio-referenzen-dublette-zu-session-ende-0c`** — Belegart **Dublette**.

Der Session-Start-Melder `0.7.4 prio-referenzen` prüft, ob Prio-Zeilen im Handover auf Geschlossenes
zeigen. Genau diese Pflege erzwingt `/session-ende` bereits am anderen Ende:

| Fundstelle | Inhalt |
|---|---|
| `.windsurf/workflows/session-ende.md:112` | Phase 0c **PFLICHT** — erledigte/verschobene Prioritäten nachziehen |
| `.windsurf/workflows/session-ende.md:374` | Abschluss-Checkliste Zeile 11 prüft genau das ab |
| `.windsurf/workflows/session-ende.md:88` | Exit 1 erzwingt das Nachziehen des Stand-Abschnitts |

Der Melder am Sitzungs-**Start** meldet also einen Zustand, den das Sitzungs-**Ende** verbindlich
herstellt. Erschwerend lief er in dieser Sitzung mit **33 % Trefferquote** (1 echt, 2 falsch) und
wurde vom Runner selbst unter die Schwelle gemeldet.

Konsequenz: herabstufen oder abschalten — nicht nachschärfen. Ein Melder, der eine erzwungene
Pflege ein zweites Mal prüft und dabei in zwei von drei Fällen falsch liegt, kostet Aufmerksamkeit
ohne Gegenwert.

Geprüft und **nicht** als Kandidat vorgeschlagen: **Phase 6 (Extern-Handoff)**. In `~/shared/` liegen
2 Briefings, 10 von 115 Reports erwähnen die Phase. Das ist dünn, reicht aber für keine der vier
Belegarten — insbesondere nicht für „kein Leser".

## Self-Review

`refuted_rate` = 3/20 = **0,15**, also unter dem 0,2-Band. Das Band warnt bei dauerhaftem
Unterschreiten vor Falsifikations-Theater. Hier ist die niedrige Quote erklärbar, aber sie bleibt
ein Beobachtungspunkt: die Widerlegungsbahn hat zusätzlich einen Befund gekippt und zwei neue
geliefert — die eigentliche Falsifikationsarbeit lag also in Phase 3b, nicht in Phase 3.
Trend der letzten Läufe: 0,11 · 0,00 · 0,10 · 0,00 · 0,11 · 0,29 · 0,20 · 0,21 · **0,15**.

### Meta-Review (Phase 5) — 7 Mängel am Report, alle behoben

Ein separater Meta-Agent hat den Entwurf gegen die Skill-Regeln geprüft (nicht die Sitzung) und
sieben Mängel gefunden. Alle sind in dieser Fassung behoben:

| # | Mangel | Behandlung |
|---|---|---|
| 1 | §5a behandelte 5 statt 6 rückfällige Gates, zwei davon falsch eingestuft, und wählte für die echten keine der drei zulässigen Antworten | §5a neu geschrieben, je Gate eine Antwort |
| 2 | `widerlegung` invertiert („1 gekippt, 2 neu" statt „2 gekippt, 1 neu") | korrigiert |
| 3 | §5 vermischte zwei Zähler unter einem Label | zwei getrennte Spalten, Werkzeug-Zahlen nachgezogen (×38, ×12, ×4, ×3, ×2) |
| 4 | Zwei Scorecard-Anker zeigten auf nicht existente Befund-Nummern | auf echte Nummern gesetzt |
| 5 | Ein GEKIPPT-Ergebnis der Widerlegungsbahn war nie als Befund-Zeile materialisiert | als #21 aufgenommen, mit Soll-Schritt |
| 6 | Streichbahn-Belegart passte nicht zur Begründung | auf **Dublette** umgestellt, drei Fundstellen genannt |
| 7 | Drei Belegzellen waren Aggregat- statt artefaktscharf | #10 und #15 mit Kommandos belegt, #16 als **HYPOTHESE** gekennzeichnet |

Der Kritik-Punkt zu §5a war der schwerste: der Entwurf hatte das Werkzeug für fehlerhaft erklärt
**statt** eine Konsequenz zu wählen — der laut Skill unzulässige vierte Weg. Die
Werkzeug-Kritik steht jetzt als eigener Befund (#22) mit eigenem Soll-Schritt, und die sechs
Konsequenzen stehen daneben.
