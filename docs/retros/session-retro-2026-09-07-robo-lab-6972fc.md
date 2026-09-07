---
retro_schema: 1
date: 2026-09-07
repo_scope: [robo-lab]
session_id: 6972fc
footprint: full
findings_total: 10
findings_survived: 9
refuted_rate: 0.10
refuted_rate_echt: 0.10
phase3_refuted: 1
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 4
  entscheidungsqualitaet: 3
gate_candidates: [kennzahl-misst-nicht-das-kriterium, ci-gate-narrower-than-local-test, partial-fix-not-generalized-to-sibling-artifacts, owner-methodenentscheid-nur-im-chat]
recurring_findings: [claim-before-cheapest-check, partial-fix-not-generalized-to-sibling-artifacts, ci-gate-narrower-than-local-test, untested-tool-module-green-gate, same-file-serial-prs]
gates_caught: [claim-before-cheapest-check]
over_ask_klassen: []
over_act_klassen: []   # 0 unter der in Paragraf 8 benannten Annahme, nicht artefaktbelegt
widerlegung: "1 gekippt, 2 neu"
streichkandidaten: [gate-wirkung-verfallsfristen-dauerausgabe]
---

# Session-Retro robo-lab — Exoskelett MVP-1 (2026-09-06 16:30 – 2026-09-07 14:15)

## 1. Executive Summary

- **Sitzungsziel erreicht, aber die Kernzahl misst das Falsche.** Der Geh-Regler geht nach drei Optimierungsrunden mit und ohne Assistenz je 23 Zyklen über 15 s (`lauf_id 20260907-132242`). Die daraus gemeldete Zahl −1,4 % wurde in Issue, Konzept und Bericht an den Owner als „erster gültiger Kill-Gate-Vergleich" geführt — **das hält nicht** (#9): das Kriterium verlangt ein einseitiges Defizit, das nie modelliert wurde, und meint das betroffene Gelenk, während gemessen wurde über beide Seiten gemittelt (rechts −5,1 %, links +2,0 %).
- **Zehn PRs, alle grün, alle gemergt, ein Repo.** Kein Prod-Schritt, keine Migration, kein Datenverlust. Ein Fehlstart (< 1 min Schaden), zwei Korrektur-Ketten innerhalb der Session.
- **Schwerster überlebender Befund:** Zwei ausdrücklich als owner-pflichtig deklarierte Methodenentscheidungen wurden umgesetzt, ohne dass im Repo ein Beleg für die Freigabe existiert (#1). Die Freigaben fielen im Kapitänskanal — das Repo weiß davon nichts.
- **Grösste Schuld:** Der gesamte vendor-abhängige Exo-Pfad läuft nie in CI; die dreimal in PR-Texten behauptete Bitgleichheit ist nirgends als wiederholbarer Test verankert (#4, #5).
- **Zwei Aussagen im Repo sind von den Daten nicht gedeckt** (#9, #10) und eine dritte widerspricht sich selbst (#8: das Konzeptdokument nennt an einer Stelle zehn Konformitätstests, an anderer zwölf). Alle drei stammen aus dieser Sitzung und sind noch offen.
- **Ein Gate hat gewirkt und zeigt zugleich seine Grenze:** `claim-before-cheapest-check` hat in dieser Sitzung zweimal eine ungeprüfte Behauptung abgefangen, den gleichartigen Fehler in einem **Code-Kommentar** aber nicht gesehen (#3) — Konsequenz: ausweiten, nicht neu bauen.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Eine ausdrücklich als owner-pflichtig deklarierte Methodenentscheidung (Robustheits-Weg, umgesetzt in #73) wurde ohne durablen Freigabe-Beleg im Repo umgesetzt | Prozesslücke | mittel | **SURVIVES** (halbiert) | Issue-#66-Kommentar 04:52 nennt die Wahl wörtlich „Offen (Methodenentscheid, nicht Handgriff)" mit zwei Optionen; #73 erstellt 06:17:06, wählt Option 1, kein Freigabe-Zitat im PR, Issue oder Ledger. Die Repo-Konvention dafür existiert und wird sonst gelebt (`KONZ-003:30`, `KONZ-004:30`, `AGENT_HANDOVER.md:28/62/328`, Ledger E8 „11 go"/„18 go", Issue-#66-Body „51 go"). **Für #76 fällt der Befund weg:** der Issue-Body führt die Wege mit „Weg 1 bevorzugt (E5/E8)" und „Weg 2 verworfen, solange Weg 1 trägt" durabel begründet und folgt der bereits freigegebenen Ledger-Zeile E8 | neu (`owner-methodenentscheid-nur-im-chat`) |
| 2 | Der Vendor-Import-Helfer existiert in drei Kopien; zwei tragen den Worktree-Fallback, `exo/ab_lauf.py` nicht | Prozesslücke | niedrig | **SURVIVES** (Severity gesenkt) | `exo/adapter_myoassist.py:130` und `exo/train_robust.py:50-53` mit `ROBO_LAB_VENDOR`-Fallback, `exo/ab_lauf.py:74-75` mit festem Pfad. **Kein belegter Schaden:** der feste Pfad hat im Worktree funktioniert — neun Journalzeilen mit `.claude/worktrees/…`-Pfaden, darunter der Kill-Gate-Lauf, existierten sonst nicht (ungeschütztes `os.chdir(VENDOR)`) | `partial-fix-not-generalized-to-sibling-artifacts` |
| 3 | In #68 wurde fremdes Vendor-Verhalten als Code-Kommentar behauptet, ohne den Quellcode zu lesen → realer Fehlstart (`IndexError`), Korrektur erst in #70; kein Test verankert, der den Fall künftig abfängt | fehlende Validierung | hoch | **SURVIVES** | `gh pr diff 68` (Kommentar „nimmt die erste .txt, die er findet") vs. `gh pr diff 70` (Korrektur auf `*_BestLast.txt`, `train.py:136`); Fehlstart 2026-09-06 17:16 in Issue #66 dokumentiert | `claim-before-cheapest-check` (Gate existiert, blocking, gebaut 2026-08-02) |
| 4 | Der vendor-abhängige Exo-Pfad (`ab_lauf.py`, `adapter_myoassist.py`, `train_robust.py`, `aufsetzen.py`) läuft nie in CI — geprüft werden nur Syntax und der Twin-Stub | fehlende Validierung | mittel | **SURVIVES** | `origin/main:.github/workflows/ci.yml` — kein Schritt installiert `vendor/myoassist` oder ruft `make exo-konformitaet-myoassist`; unabhängig gegengeprüft inkl. aller Makefile-Ziele und Testdateien | `ci-gate-narrower-than-local-test` — **Erstvorkommen im selben Repo am 2026-08-28**, jetzt ×2 ⇒ GATE-PFLICHT; dazu `untested-tool-module-green-gate` |
| 5 | Die in drei PR-Texten behauptete Bitgleichheit (Seed-Gleichheit #72, `becken_x`-Regression #75/#78) existiert nur als einmalige Zahl im Fließtext, nicht als wiederholbarer Test | fehlende Validierung | mittel | **SURVIVES** | PR #72 ändert ausschließlich `docs/versuche/journal.jsonl`, keinen Testcode; `git ls-tree -r origin/main --name-only \| grep -iE 'test'` findet keinen Regressionstest für `ab_lauf.py` | `untested-tool-module-green-gate` |
| 6 | Doku-Split bei der Testzahl: #74 zog Code und CLI-Ausgabe auf zwölf Konformitätstests; #75 korrigierte als Nebenprodukt **nur die README-Überschrift**, drei weitere Stellen blieben bei zehn und stehen bis heute so auf `main` | Prozesslücke | mittel | **SURVIVES** (Severity angehoben) | Code eindeutig zwölf (`exo/konformitaet.py:12/88`, `k11`/`k12` in `exo/konformitaet_tests.py:289/303`); stale: `exo/README.md:20` („Suite K1–K10") gegen `:84`/`:416` („zwoelf"/„12/12") sowie `docs/konzepte/KONZ-robo-lab-005.md:88` | `partial-fix-not-generalized-to-sibling-artifacts` |
| 7 | Die Gegenprobe mit festem Profil (E8, 0,1/0,2/0,3 Nm/kg) sei mit dem vorhandenen K10-Wissen vermeidbar gewesen | verfrühte Festlegung | mittel | **REFUTED** | K10 betrifft die Vendor-Bezugsgröße (Standphase), der eigene Regler nutzt Gangzyklus-Anteile (PR #74); die Gegenprobe hielt das Timing bewusst konstant und variierte nur die Stärke — das war der Testzweck (Ledger A12) | — |
| 8 | Serielle PRs auf derselben Datei haben eine widersprüchliche Doppelaussage im **zentralen Konzeptdokument** hinterlassen: `KONZ-robo-lab-005.md` sagt in Zeile 72 „K11/K12 in der Suite" und in Zeile 88 „Suite K1–K10 … beide Adapter 10/10" | Prozesslücke | hoch | **SURVIVES** (in der Widerlegungsbahn von „pre-refuted" gekippt) | Zeile 72 stammt aus #74 (`635d4ab`), Zeile 88 aus #77 (`1b93f3f`) — #77 schrieb die Zeile neu und trug die veraltete Testzahl mit. Die ursprüngliche Entlastung („0 Treffer für Konfliktspuren in den PR-Bodies") war die falsche Suche: der Schaden steht in der Datei, nicht im PR-Text | `same-file-serial-prs` |

| 9 | **Die Kernzahl der Sitzung misst nicht das Kriterium, unter dessen Namen sie berichtet wurde.** Das Kill-Kriterium verlangt Entlastung des Spitzenmoments **am betroffenen Gelenk** bei **einseitigem Defizit**; gemessen wurde ohne Defizit, über beide Sprunggelenke gemittelt, und als Mittel der Zyklus-Spitzen statt als Spitzenmoment | fehlende Validierung | hoch | **SURVIVES** (neu aus der Widerlegungsbahn) | `KONZ-robo-lab-005.md` Frontmatter Z.10 (`kill_criteria`) und R4 Z.77 fordern das Defizit; Ledger A5 steht auf „offen — Eigenbau nötig"; `lauf_id 20260907-132242` hat kein Defizit im `aufbau`. Aggregation: `exo/ab_lauf.py:586-589` mittelt beide Seiten — nachgerechnet A 87,59/95,96 → 91,78, B 92,09/94,06 → 93,07, ergibt −1,42 %; **einzeln rechts −5,14 %, links +1,98 %**, der Mittelwert verdeckt den Vorzeichenwechsel | neu (`kennzahl-misst-nicht-das-kriterium`) |
| 10 | Die Ledger-Folgerung A12 („das Timing entscheidet, nicht die Stärke") ist von keinem Lauf gedeckt | fehlende Validierung | hoch | **SURVIVES** (neu aus der Widerlegungsbahn) | In der gesamten `docs/versuche/journal.jsonl` variiert **kein einziger** Eintrag `peak_time`; die drei Gegenproben `20260907-132337/-132340/-132344` ändern ausschließlich `peak_torque` bei identischem `peak_time=0.5`. Der Vergleich, der die Aussage tragen soll, kreuzt zugleich mindestens drei Unterschiede (eigener Regler statt Vendor-Spline, Halbkosinus statt PCHIP, geweiteter Stellbereich). Dazu ein Einheiten-Bruch: `peak_time` meint beim eigenen Regler den Gangzyklus, beim Vendor die Standphase (`exo/spline_regler.py:19`) — 0,5 Zyklus entspricht bei `STANDANTEIL=0.6` genau 66,7 % der Standphase, also derselben Stelle, gegen die A12 den Vendor abgrenzt | neu (`folgerung-ohne-variierten-parameter`) |

**Zusatzfakt aus der Falsifikation (kein eigener Befund):** Die Nullbefund-Behauptung „kein Force-Push-Bedarf" ist widerlegt — `head_ref_force_pushed` auf #69 (17:18:36) und #74 (06:24:45), je ~1–2 min vor dem Merge. Beides Amend/Rebase vor dem Merge ohne Schaden.

## 3. Scorecard

| Dimension | Score | Verankert an |
|---|---|---|
| zielerreichung | 3 | Gemessen am **Sitzungsziel** aus Issue #66 (Geh-Regler mindestens 10 Zyklen ohne Sturz; Vertrag, Sicherheitskette, Konformitätstests) — beides belegt erfüllt. Das Entlastungskriterium ist ein **Programmziel mit Frist 2026-11-30** (Kill-Gate Zeile 1), nicht das Sitzungsziel; die Sitzung hat es erstmals überhaupt messbar gemacht. Zwei Stufen Abzug, weil das Ergebnis unter falschem Namen berichtet wurde: „erster gültiger Kill-Gate-Vergleich" (#9) hält nicht, und der Verdikt-Wert FEHLSCHLAG des Laufs wurde in der Prosa nie genannt. Rubrik 3: Sitzungsziel erreicht, die Abweichung ist benannt und korrigierbar |
| architektur_design | 4 | Wrapper statt Vendor-Patch, Vertrag, Kette und Adapter tragfähig und unabhängig gegengeprüft (Monkeypatch idempotent, Vendor-Baum unangetastet, Schemas sauber); Abzug für die dritte Kopie des Import-Helfers (#2, ohne belegten Schaden) |
| code_konventionstreue | 3 | Deutsch, `additionalProperties: false`, keine mujoco-Importe auf Modulebene, Journal-Pflichtfelder — alle eingehalten (unabhängig gegengeprüft). Abzug für #6 und #8: vier Doku-Stellen tragen bis heute eine falsche Testzahl, eine davon im zentralen Konzeptdokument |
| risiko_debt | 2 | #3, #4, #5 — drei Validierungslücken, keine davon in der Sitzung geschlossen; der teuerste Pfad ist ungetestet |
| prozess_effizienz | 4 | 10 PRs in 22 h, alle Required Checks grün vor Merge, ein Fehlstart mit < 1 min Schaden; Abzug für die zwei Korrektur-Ketten (#3, #6) |
| entscheidungsqualitaet | 3 | #1 wiegt mittel und trifft die **Dokumentation** der Entscheidung, nicht ihre Güte: beide gewählten Wege waren tragfähig und im Ergebnis bestätigt (Runde 3 lieferte den ersten gültigen Vergleich, #78 traf die wirkliche Ursache). Dagegen steht #10: eine Schlussfolgerung wurde ins Ledger geschrieben, ohne dass ein Lauf den entscheidenden Parameter variiert hätte. Rubrik 3: keine 2, weil kein Rework nötig wurde und alle Wege im Ergebnis trugen; keine 4 wegen #1 und #10 |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| #71 erklärt die Methodenwahl zur Owner-Sache; #73 setzt sie 1 h 25 min später um, ohne dass im Repo ein Freigabe-Beleg steht | Wer eine Entscheidung im PR-Text zur Owner-Sache erklärt, trägt die erhaltene Freigabe **im selben Zug** wörtlich ins Issue oder in die Ledger-Zeile ein, bevor der Umsetzungs-PR erstellt wird — Zitat + Datum, wie bei E8 („11 go"/„18 go") bereits vorbildlich gemacht | #1 |
| Der Worktree-Fallback landete nur in der jüngeren der zwei Kopien des Vendor-Import-Helfers | Beim Fix an einer duplizierten Stelle zuerst `grep -rn "<das duplizierte Muster>" exo/` fahren und **alle** Fundstellen im selben PR nachziehen — oder den Helfer in ein Modul heben, wie es `_foot_side` bereits vormacht | #2 |
| Ein Kommentar behauptete Vendor-Verhalten aus Beobachtung; der Quellcode sagte etwas anderes, Fehlstart folgte | Eine Behauptung über fremden Code, die in eine dauerhafte Datei geschrieben wird, braucht denselben billigsten Check wie eine Behauptung im Chat: `grep -n` auf die genannte Stelle, Zeilennummer in den Kommentar | #3 |
| Der vendor-abhängige Pfad wurde dreimal geändert und ausschließlich manuell belegt | Ein CI-Job mit gecachtem Vendor-Klon (oder ein wöchentlicher Lauf), der `make exo-konformitaet-myoassist` einmal fährt — sonst ist jede Änderung an diesem Pfad ab dem Merge unbelegt | #4 |
| Bitgleichheit wurde dreimal gemessen und dreimal nur als Satz im PR-Text festgehalten | Die Regression als Testdatei mit fixierten Referenzwerten ablegen (`exo/` Selbsttest-Muster wie `sim/reach.py --selbsttest`), damit CI sie wiederholt statt eines Menschen | #5 |
| Code und CLI wurden auf zwölf Tests gezogen, die README-Überschrift blieb bei zehn | Beim Ändern einer Zahl, die auch in Prosa steht, `grep -rn "zehn\|K1–K10\|10/10" exo/ docs/` im selben PR — die Doku-Stellen gehören zum Fix, nicht in den nächsten PR | #6 |
| #77 schrieb die MVP-Zeile im Konzept neu und trug die veraltete Testzahl aus der Vorgängerfassung mit | Wer eine bestehende Zeile in einem lebenden Dokument **neu schreibt** statt sie zu ergänzen, liest vorher die anderen Zeilen desselben Dokuments zum selben Gegenstand — sonst überschreibt ein späterer PR die Korrektur eines früheren | #8 |
| Eine Kennzahl wurde unter dem Namen des Kill-Kriteriums berichtet, ohne gegen dessen Wortlaut geprüft zu sein | Bevor eine Zahl unter dem Namen eines Kriteriums berichtet wird, den Wortlaut des Kriteriums danebenlegen und Feld für Feld abhaken: welche Bedingung, welches Gelenk, welche Statistik. Weicht eines ab, heißt die Zahl anders | #9 |
| Aus drei Läufen, die nur die Stärke variierten, wurde eine Aussage über das Timing ins Ledger geschrieben | Eine Aussage der Form „A entscheidet, nicht B" darf nur ins Ledger, wenn mindestens ein Lauf A variiert hat und B festhielt; sonst ist sie eine Hypothese und wird als solche markiert | #10 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über 114 Reports (jetzt 115): 42 Slugs stehen unter GATE-PFLICHT, alle tragen ein registriertes Gate oder eine dokumentierte Verzichts-Entscheidung. Für die Slugs dieser Sitzung:

| Slug | Vorkommen bisher | Gate | Konsequenz hier |
|---|---|---|---|
| `claim-before-cheapest-check` | Gate seit 2026-08-02, blocking | ja | **Rückfall in neuem Medium** → ausweiten, siehe 5a |
| `partial-fix-not-generalized-to-sibling-artifacts` | ×12 (`retro_kpis.py`; u. a. 3b123e, 8f9a23, fdd368, b527358c) | kein Eintrag unter diesem exakten Slug, `retro_kpis.py` meldet dennoch vollständige Registry-Deckung — siehe Paragraf 8 | zwei neue Vorkommen (#2, #6) |
| `ci-gate-narrower-than-local-test` | ×1, und zwar aus **`session-retro-2026-08-28-robo-lab-54195f.md` — demselben Repo, zehn Tage zuvor** | nein | mit #4 jetzt **×2 ⇒ GATE-PFLICHT**; derselbe Befund ist im selben Repo unverändert wiedergekehrt |
| `untested-tool-module-green-gate` | ×9; Registry: `mode: advisory`, `built: 2026-08-12`, `expires: 2026-10-31` | ja | #4/#5 sind Vorkommen derselben Familie; die Frist läuft noch |
| `same-file-serial-prs` | ×30 Textvorkommen über den Korpus | nein | hier **kein** Befund (pre-refuted, #8) — als Nicht-Vorkommen geführt |

Memory-Abgleich (`grep` im Auto-Memory-Index): Für den Slug `owner-methodenentscheid-nur-im-chat` existiert keine Memory-Datei; die nächstliegende, `feedback_freigabe_vermerk_dorthin_wo_das_werkzeug_liest`, betrifft den PR-Kommentar-Pfad eines Merge-Werkzeugs, nicht die Verankerung einer Methodenentscheidung. Der Vorschlag steht in §6.

## 5a. Rückfall-Prüfung

`python3 tools/gate_wirkung.py` meldete zu Sitzungsbeginn **kein** rückfälliges Gate; 21 Gates gelten als „zu-frueh" (weniger als drei Retros seit Bau) — das ist kein Wirksamkeitsbeleg.

**Ein Gate ist mit diesem Report rückfällig: `claim-before-cheapest-check` (blocking, gebaut 2026-08-02).**

- **Beleg dafür, dass es wirkt:** In dieser Sitzung hat es zweimal gefeuert und beide Male einen echten Nachweis erzwungen — einmal auf eine CI-Status-Behauptung (Antwort korrigiert, Merge-Status per `gh pr view` belegt), einmal auf eine Aussage über die Gelände-Bibliothek (Suche mit Positivkontrolle nachgezogen, Aussage korrigiert). Deshalb steht der Slug in `gates_caught`.
- **Beleg für die Lücke:** Derselbe Fehlertyp in einem **Code-Kommentar** (#3) blieb unbemerkt, weil das Gate den Antworttext prüft, nicht Dateien, die in einem Commit dauerhaft eine Behauptung über fremdes Verhalten festschreiben. Ursache **an der Quelle** — das Gate sieht den Fall nicht.
- **Erwogene Konsequenz: ausweiten. Beim Bauen verworfen** — und das ist selbst ein Ergebnis dieser Rückfall-Prüfung: Der Soll-Ablauf zu #3 verlangt, die geprüfte Fundstelle **mit Zeilennummer** in den Kommentar zu schreiben. Ein Scanner auf Kommentare, die eine fremde Datei samt Zeile nennen, träfe damit genau die **richtige** Praxis; die falsche Form, eine Behauptung ohne Fundstelle, ist von normaler Prosa maschinell nicht zu trennen. Ein solches Gate hätte eine hohe Fehlalarmquote am erwünschten Verhalten und würde umgangen statt befolgt.
- **Gewählte Konsequenz: dokumentierter Verzicht** unter dem engen Slug `behauptung-ueber-fremdcode-im-datei-kommentar`, eingetragen in `declined` mit Begründung — derselbe Weg, den `always-instruction-without-enforcement` bereits geht. Vorschlag zur Ratifikation in platform#2934; Ersatz ist die Memory-Regel aus Paragraf 6.
- **Das bestehende Gate bleibt unverändert.** Es hat zweimal gefangen, und es wurde am selben Tag von einer anderen Sitzung auf Rev 5 gebracht (platform#2374). Ein Rev 6 ohne Verhaltensänderung wäre reines Zurücksetzen der Wirkungsmessung — genau die Steigerbarkeit durch Neubauen, gegen die `gate_wirkung.py` seine Ehrlichkeits-Sperren hat.

## 5b. Autonomie-Kalibrierung

- `over_act`: **0.** Kein Prod-Schritt, kein Publish, kein drittes Repo, nichts Irreversibles. Alle zehn Merges liefen in einem Repo ohne Ruleset und ohne Branch-Protection (`gh api .../rulesets` → `[]`, `.../branches/main/protection` → 404), also ohne verletztes Gate. Die zwei Entscheidungen aus Befund #1 hatten eine Freigabe — sie ist nur nicht im Repo gelandet; das ist ein Verankerungs-, kein Autonomiebefund.
- `over_ask`: **0.** Die vorgelegten Punkte (Störquelle Gelände, Reihenfolge der nächsten Optimierung) waren echte Methodenentscheidungen mit mehrstündigen Läufen als Folge.

## 6. Verankerung

**memory_candidates** (kopierfertig, Entscheidung beim Menschen):

```markdown
---
name: feedback_owner_methodenentscheid_gehoert_ins_issue_bevor_der_pr_entsteht
description: "Eine im PR-Text zur Owner-Sache erklärte Methodenentscheidung braucht das Freigabe-Zitat im Issue/Ledger, bevor der Umsetzungs-PR entsteht"
metadata:
  type: feedback
  rule_class: A
  assessed_with: claude-opus-5
  reassess_by: 2026-12-31
---

Wer in einem PR-Text schreibt „das ist eine Methodenentscheidung, kein Handgriff",
hat damit eine Owner-Pflicht erklärt. Die erhaltene Freigabe gehört dann **im selben
Zug** wörtlich ins Issue oder in die Ledger-Zeile — Zitat + Datum — und zwar bevor
der Umsetzungs-PR entsteht.

**Why:** robo-lab 2026-09-07: #71 erklärte die Wahl des Robustheits-Wegs ausdrücklich
zur Owner-Sache, #73 setzte sie 1 h 25 min später um; im Repo steht dafür kein Beleg.
Dasselbe bei der Aufschiebung von #76. Beide Freigaben gab es wirklich — im
Kapitänskanal. Für jeden späteren Leser sieht es aus wie ein Alleingang, und für den
Längsschnitt ist es nicht von einem zu unterscheiden. Vorbild im selben Repo: der
Ledger-Eintrag E8 zitiert „11 go" und „18 go" mit Datum.

**How to apply:** Sobald ein PR-Text oder eine Antwort eine Entscheidung als
owner-pflichtig markiert, ist der nächste Schreibzug das Zitat ins Issue/Ledger —
nicht der Umsetzungs-PR. Siehe [[feedback_freigabe_vermerk_dorthin_wo_das_werkzeug_liest]].
```

```markdown
---
name: feedback_behauptung_ueber_fremdcode_im_kommentar_braucht_dieselbe_pruefung
description: "Eine Behauptung über fremdes Verhalten, die dauerhaft in eine Datei geschrieben wird, braucht denselben billigsten Check wie eine Behauptung im Chat"
metadata:
  type: feedback
  rule_class: A
  drift: true
  drift_episode: 2026-09-07-vendor-kommentar-ungeprueft
  assessed_with: claude-opus-5
  reassess_by: 2026-12-31
---

Der Evidenz-Check greift beim Antworttext. Ein Kommentar in einer Skript- oder
Doku-Datei, der fremdes Verhalten behauptet („der Trainer nimmt die erste Datei,
die er findet"), entzieht sich ihm — und wirkt länger, weil ihn der nächste Leser
für geprüft hält.

**Why:** robo-lab #68 (2026-09-06): genau dieser Kommentar wurde aus Beobachtung
statt aus dem Quellcode geschrieben; der Trainer filtert in Wahrheit auf eine
Dateiendung. Folge: Fehlstart mit `IndexError`, Korrektur erst in #70.

**How to apply:** Vor dem Schreiben eines solchen Kommentars den billigsten Check
fahren (`grep -n` auf die genannte Stelle) und die Zeilennummer mit in den Kommentar
nehmen — dann ist er im nächsten Vendor-Update auch prüfbar.
```

**adr_candidates:** keine. Die Session hat keine Architekturentscheidung getroffen, die über KONZ-robo-lab-005 hinausgeht; die Ledger-Zeilen E8/A10/A11/A12 sind das richtige, leichtere Gefäß (Schwellenregel `adr-threshold.md`: Ergänzung nach bestehendem Muster braucht kein ADR).

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Verzicht statt Gate, begründet | platform | [#2934](https://github.com/achimdehnert/platform/pull/2934) | 🟢 | Ratifizieren, Governance-Pfad (du) |
| M2 | CI-Job für Vendor-Pfad | robo-lab | [#66](https://github.com/achimdehnert/robo-lab/issues/66) | 🟢 | Kosten/Nutzen entscheiden (du) |
| M3 | Bitgleichheit als Testdatei | robo-lab | [#66](https://github.com/achimdehnert/robo-lab/issues/66) | 🔵 | Selbsttest nach `reach.py`-Muster (ich) |
| M4 | Vendor-Import-Helfer zusammenführen | robo-lab | [#66](https://github.com/achimdehnert/robo-lab/issues/66) | 🔵 | Helfer in Modul heben (ich) |
| M5 | Verfallsfristen-Ausgabe kürzen | platform | [gate_wirkung.py](https://github.com/achimdehnert/platform/blob/main/tools/gate_wirkung.py) | 🟢 | Streichung freigeben (du) |
| M6 | Zwei Memory-Dateien anlegen | platform | [#2933](https://github.com/achimdehnert/platform/pull/2933) | 🟢 | Vorschläge annehmen (du) |
| M7 | Drei Falschaussagen im Repo korrigieren | robo-lab | [#66](https://github.com/achimdehnert/robo-lab/issues/66) | 🟡 | Testzahl, A12, Kill-Gate-Zeile (ich) |
| M8 | Einseitiges Defizit modellieren | robo-lab | [#66](https://github.com/achimdehnert/robo-lab/issues/66) | 🟢 | Ohne A5 bleibt jede Entlastungszahl ein Vorlauf (du) |

## 8. Nicht verifiziert (Restlücken)

- **getan:** Gate-Wirkungsbilanz, Sammlung aus `origin/main` nach `fetch`, drei Finder in frischem Kontext, ein Skeptiker auf vier Behauptungen mit unabhängig neu gezogenen Belegen, Längsschnitt über 114 Reports, Registry-Abgleich für sechs Slugs.
- **angenommen:** Dass die Freigaben zu #73 und #76 im Kapitänskanal wirklich fielen — das ist meine Erinnerung, kein Artefakt. Für den Report zählt nur, dass das Repo sie nicht kennt; die Autonomie-Bewertung (`over_act: 0`) stützt sich auf diese Annahme und ist damit die schwächste Zahl im Frontmatter. Billigster Check: der Owner bestätigt oder widerspricht in einem Satz.
- **nicht verifizierbar:** Welcher Registry-Eintrag den Slug `partial-fix-not-generalized-to-sibling-artifacts` deckt — ein direkter Slug-Vergleich findet keinen, `retro_kpis.py` meldet trotzdem vollständige Deckung; die Zuordnung läuft offenbar über eine Familie oder einen Alias, den der einfache Vergleich nicht auflöst. Billigster Check: die Mapping-Ausgabe von `retro_kpis.py` lesen statt die Registry direkt zu greppen.
- **nicht verifizierbar:** Ob die zwei Force-Pushes (#69, #74) Konfliktauflösungen oder reine Amends waren — die GitHub-API zeigt das Event, nicht den Grund; die Vorher-Commits sind nach dem Squash-Merge nicht mehr abrufbar.
- **offen geblieben:** Ob der Wrapper-Ansatz (`train_robust.py`, Monkeypatch der Vendor-Klasse) einen Vendor-Update überlebt — geprüft ist nur, dass er heute funktioniert. Billigster Check: beim nächsten `EXO_COMMIT`-Bump die Konformitätssuite gegen den MyoAssist-Adapter fahren.

## Self-Review

Ein separater Meta-Prüfer hat den Report gegen die Skill-Regeln geprüft, nicht die Sitzung. Vier Beanstandungen, drei übernommen:

- **Echte Falsifikationsquote fehlte.** Nachgetragen: `phase3_refuted/(findings_total − pre_refuted)` = 1/7 ≈ **0,14**, damit **unter** der 0,2-Schwelle, ab der Falsifikation als Theater gilt; der zusammengesetzte Wert 0,25 verdeckt das. Numerische Lesart: bei acht Befunden und nur einem unabhängig verworfenen trägt die Widerlegungsbahn die Absicherung dieses Reports, nicht der Skeptiker-Pass.
- **Längsschnitt-Zeilen ohne harten Beleg.** Nachgetragen: Report-Dateiname des Erstvorkommens, Registry-Felder der Gates, Slug-Zähler aus `retro_kpis.py`.
- **`over_act: 0` stand glatt da, obwohl Paragraf 8 die Annahme dahinter als schwächste Zahl benennt.** Die Unsicherheit steht jetzt am Frontmatter-Feld selbst.
- **Nachtrag zur Rückfall-Konsequenz:** Der Entwurf trug „ausweiten" ein. Beim tatsächlichen Bau des Registry-Eintrags zeigte sich, dass die Ausweitung das erwünschte Verhalten treffen würde; die Konsequenz wurde zu einem begründeten Verzicht geändert (Paragraf 5a). Das ist kein Ausweichen vor der Drei-Antworten-Regel, sondern der in der Registry vorgesehene vierte Weg — mit Begründung statt mit Schweigen.
- **Nachtrag nach der Widerlegungsbahn:** Deren Befund #9 hat die Beanstandung des Meta-Prüfers zu `zielerreichung` **im Kern bestätigt**, wenn auch aus einem anderen Grund als von ihm genannt — nicht weil das Entlastungskriterium Sitzungsziel wäre, sondern weil die berichtete Zahl das Kriterium gar nicht misst. Score jetzt 3, `code_konventionstreue` wegen #8 ebenfalls 3.
- **Falsifikationsquote nach der Widerlegungsbahn: 1/10 = 0,10**, weiter unter der 0,2-Schwelle. Numerische Lesart: der Skeptiker-Pass hat einen von zehn Befunden verworfen, die Widerlegungsbahn dagegen einen verworfenen zurückgeholt und zwei neue erzeugt — die Absicherung dieses Reports liegt fast vollständig in der Widerlegungsbahn. Für den Trend heißt das: der niedrige Wert steht hier nicht für laxe Falsifikation, sondern für einen zu milden Skeptiker-Pass.
- **Nicht übernommen: Absenkung von `zielerreichung` mit der Begründung des Prüfers.** Der Prüfer las das Entlastungskriterium als Sitzungsziel; es ist ein Programmziel mit Frist 2026-11-30, das Sitzungsziel steht in Issue #66 und ist erfüllt. Die Scorecard benennt die Trennung jetzt ausdrücklich, statt sie mit der zu Recht beanstandeten Formel „ein negatives Ergebnis ist auch Zielerreichung" zu verwischen.

## Widerlegung

Ein Prüfer auf höchster Stufe mit frischem Kontext, ohne Kenntnis der Sitzungserzählung und ohne die Finder-Aufträge, hat den Report-Entwurf angegriffen. Ergebnis: **1 gekippt, 2 neu.**

**Frage 1 — steht ein SURVIVES falsch da? `BESTAETIGT`.** Kein Befund gekippt, aber zwei Belege korrigiert: Befund #1 gilt nur für #73, nicht für #76 (dort ist die Wahl im Issue-Body durabel begründet und folgt der freigegebenen Ledger-Zeile E8) — und die im Entwurf behauptete „vollständige Owner-Zitat-Liste" war unvollständig, sie übersah „51 go" im Body von Issue #66 sowie die Konvention in `KONZ-003`, `KONZ-004` und `AGENT_HANDOVER.md`. Befund #2 verliert seine Schadensbegründung: der feste Pfad hat im Worktree funktioniert, und eine dritte Kopie trägt den Fallback sehr wohl.

**Frage 2 — ist ein REFUTED zu früh verworfen? `GEKIPPT`.** Befund #8 (serielle PRs) war als „pre-refuted" gar nicht erst geführt worden, mit der Begründung, es gebe keine Konfliktspuren in den PR-Texten. Das war die falsche Suche. In der Datei selbst steht der Schaden: das zentrale Konzeptdokument nennt an einer Stelle zwölf Konformitätstests und an anderer zehn, weil ein späterer PR eine Zeile neu schrieb und die veraltete Zahl mittrug. Befund #7 hält dagegen als REFUTED — die Gegenprobe war ein sauber isoliertes Experiment.

**Frage 3 — fehlt eine Dimension? `NEU`, zwei Befunde.** Keiner der drei Prüfer hat die **Kennzahl gegen ihre eigene Definition** gehalten: Scope prüfte den Auftrag, Entscheidungen die Wege, Prozess die Pull Requests. Dazwischen fiel, dass die Zahl, die diese Sitzung trägt, drei stille Ersetzungen gegenüber dem Kriterium enthält (#9), und dass die daraus gezogene Ledger-Folgerung von keinem Lauf gedeckt ist (#10).

**Erfolglos versucht** (damit „nichts gefunden" von „nicht hingesehen" unterscheidbar bleibt): Löschungen oder Schönungen im Messjournal über alle vierzehn Commits der Datei — es gibt genau eine Ersetzung, und die stammt vom 2026-08-30, also von vor der Sitzung; in den zehn Sitzungs-Commits null Löschungen. Ebenso geprüft und sauber: die Gelände-Zahlen gegen sechs Journalzeilen, die Zyklen- und Geschwindigkeitsangaben im Issue-Kommentar gegen den Rohlauf, und die Frage, ob der CI-Workflow doch einen Vendor-Schritt enthält.

## Streichbahn

**Kandidat: `gate-wirkung-verfallsfristen-dauerausgabe` — Belegart „kein Leser".**

`tools/gate_wirkung.py` gibt bei jedem Lauf einen Block mit 23 Zeilen „Verfallsfrist … läuft noch" aus. In **116 Retro-Reports** kommt das Wort „Verfallsfrist" **null Mal** vor — keine Retro hat je auf diese Liste reagiert. Verstärkend: 22 der 23 advisory-Gates tragen dasselbe Datum 2026-10-31, und **kein einziges** Gate der Registry trägt eine `frozen_note`, das heißt: bis heute ist kein Gate über diesen Weg von advisory auf blocking gewandert.

**Konsequenz:** Den Block nur noch ausgeben, wenn eine Frist überschritten ist oder in weniger als 30 Tagen fällig wird. Die Information geht nicht verloren, sie hört auf, jeden Lauf zu verdünnen.

**Ratsche:** Erstes Auftreten. Taucht der Kandidat in der nächsten Retro erneut auf, ohne gestrichen zu sein, ist das selbst ein Befund.
