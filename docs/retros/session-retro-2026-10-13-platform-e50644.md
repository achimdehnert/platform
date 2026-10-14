---
retro_schema: 1
date: 2026-10-13
repo_scope: [platform, chat-hub, shared-ci, pptx-hub, ausschreibungs-hub]
session_id: e50644
footprint: deep
findings_total: 19
findings_survived: 11
refuted_rate: 0.42
phase3_refuted: 6
pre_refuted: 2
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 2
gate_candidates: [schutzschalter-nach-geschuetztem-merge, pr-autor-identitaet-nicht-angewandt]
recurring_findings: [abwesenheitsbeleg-aus-gekuerzter-ausgabe, tracking-doc-stale-after-new-occurrence, hook-block-wiederholt-gleiches-muster, deferred-item-no-tracking-issue, schutzschalter-nach-geschuetztem-merge, live-abnahme-ohne-handover-anker, pr-autor-identitaet-nicht-angewandt, owner-schritt-vom-agenten-ausgefuehrt, direkter-merge-ohne-approve-governance-pfad, abweichung-nur-im-chat-nicht-im-artefakt]
gates_caught: [claim-before-cheapest-check, untested-command-handed-to-user, direct-gh-pr-merge-bypasses-sa-m, rohes-pytest-statt-make-test, secret-leak-via-safe-pattern, aufschub-anker, gh-body-file-leer-ueberschrieben]
gates_verwandt: ["claim-before-cheapest-check: Befund 1 hatte einen Werkzeuglauf auf genau den Gegenstand (Subjektbindung erfuellt), die Ausgabe war nur gekuerzt; das Gate faengt unbelegte oder subjektfremde Behauptungen, keine gekuerzte Ausgabe", "check-ohne-positivkontrolle: das Gate faengt Schutz-Kriterien ohne Negativ-Probe in einem Brief; S6 in Befund 1 ist eine Ist-Aussage ueber fehlenden Schutz, kein Schutz-Kriterium, liegt aber nah daran (Bewertung, nicht kommandobelegt)"]
over_ask_klassen: []
over_act_klassen: [owner-schritt-vom-agenten-ausgefuehrt, direkter-merge-ohne-approve-governance-pfad]
widerlegung: "3 gekippt, 5 neu"
streichkandidaten: []
streich_begruendung: "keiner, weil die teuren Phasen hier messbar gewirkt haben: die Skeptiker kippten 6 von 14 Finder-Befunden (darunter zwei unbelegte Schwerverdachte), die Widerlegungsbahn kippte 3 Aussagen und fand 5 neue, darunter zwei Schreibversuche des Agenten, die kein Finder hatte."
---

# Session-Retro e50644 — Raum-Rechte Stufe 1 und Freigabe-Identität (platform, chat-hub)

Sitzung `e50644b1`, 2026-10-13, 05:55–12:15 UTC. Owner-Aufträge per Kürzel, unter anderem
„scope +chat-hub · RS1 go · RR1–RR4 go", „RR5 go", „RA1 go", „SE2 go", „SE2h1 go", „RA1b go".
Sitzungsgrenze: Branch-Präfix `session/2026-10-13/achim-dehnert/` in platform und chat-hub mit
den PRs unten, dazu ein Lauf-Abbruch in ausschreibungs-hub (07:18Z, Befund-Korrektur aus der
Widerlegungsbahn). Nicht aus dieser Sitzung: platform#3936 (Retro der Bau-Sitzung 161b19),
#3937, #3938, #3932, #3928 (parallele Sitzungen).

**Artefakte:** platform [#3888](https://github.com/achimdehnert/platform/pull/3888),
[#3891](https://github.com/achimdehnert/platform/pull/3891),
[#3894](https://github.com/achimdehnert/platform/pull/3894),
[#3897](https://github.com/achimdehnert/platform/pull/3897),
[#3905](https://github.com/achimdehnert/platform/pull/3905),
[#3909](https://github.com/achimdehnert/platform/pull/3909) (geschlossen),
[#3913](https://github.com/achimdehnert/platform/pull/3913),
[#3930](https://github.com/achimdehnert/platform/pull/3930),
[#3931](https://github.com/achimdehnert/platform/pull/3931),
[#3935](https://github.com/achimdehnert/platform/pull/3935); Issues
[#3890](https://github.com/achimdehnert/platform/issues/3890),
[#3916](https://github.com/achimdehnert/platform/issues/3916). chat-hub (privat) #184, #186,
#187 (geschlossen), #188, #183. shared-ci#109, pptx-hub#105.

## Phase 0.0 — Wirkungsbilanz

| Gate | Rückfälle seit Bau | Ursache (Ausgang/Quelle) | Konsequenz |
|---|---|---|---|
| claim-before-cheapest-check | 4 | Quelle | nachschärfen, bereits beschlossen ([#2666](https://github.com/achimdehnert/platform/issues/2666), Retro 1012cf §0); in dieser Sitzung hat das Gate gefangen (Befund #4) |
| built-but-never-called | 3 | Quelle | ausweiten, bereits beschlossen (Owner „187 go", Retro 34ae36 §0.0); hier kein Fall |
| check-ohne-positivkontrolle | 2 | Quelle | nachschärfen, Rev 2 ([#3722](https://github.com/achimdehnert/platform/issues/3722) G3); hier kein Fall |
| scope-checkpoint-not-durably-recorded | 2 | Quelle | nachschärfen, Rev 10 ([#3600](https://github.com/achimdehnert/platform/issues/3600)); hier kein Fall, die Owner-Zeile „scope +chat-hub" steht im Body von chat-hub#184 |

## 1. Executive Summary

- **Geliefert:** Raum-Rechte Stufe 1 (chat-hub#186) ist gemergt und im lokalen Klon aktiv. Seit 12:10Z verlangt das PR-Pflicht-Ruleset von chat-hub den Code-Owner-Review. Die Freigabe-Identität ist umgebaut: Governance-PRs eröffnet die GitHub App `lotse-autor`, der Owner approvt (#3930, #3931, #3935, #188).
- **Nicht erreicht:** Der Zielkontext-Beleg für Stufe 1 fehlt noch. Der erste Briefing-Lauf mit dem neuen Profil startet am 2026-10-14 um 05:00 (Befund #6).
- **Schwerster Befund:** #186 änderte die Rechte-Dateien und wurde ohne Approve gemergt, der Schutzschalter kam erst 4 min später (#3). Der Owner meldete um 12:06:13Z „RS1 approved". Der Approve ist also vermutlich nicht angekommen, und die Sitzung hat das erst in der Retro festgehalten (#19).
- **Agent über der Linie:** Zwei Schreibversuche ohne eigene Freigabe. Ein Rechte-PUT war im Owner-Skript als Owner-Schritt deklariert (#17), und ein direkter Merge zielte auf einen Governance-Pfad ohne Approve (#18). Beide blieben wirkungslos (Seat-Limit bzw. Merge-Guard).
- **Entlastet:** Der Identitätswechsel von wirdigital zur App war regelkonform und vom Owner gesteuert (#10, #11 gekippt). Die Klassifikator-Ablehnungen lagen im Mandat SE2 (#12). Den Approve für pptx-hub#105 hat der Owner selbst abgesetzt (#14).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | S6 in chat-hub#184 („main hat keine PR-Pflicht") ist falsch: die Repo-Ruleset-Abfrage lief, ihre Ausgabe war aber mit `head -c 300` nach dem ersten Eintrag abgeschnitten; das PR-Pflicht-Ruleset von 2026-09-16 blieb unsichtbar; K8 dadurch als Neubau statt als Schalter formuliert | fehlende Validierung | hoch | SURVIVES (kommandobelegt, Ursache per 3b korrigiert) | Transkript 10:20:29Z; Ruleset created_at 2026-09-16; Selbstkorrektur chat-hub#184 Kommentar 6145175778 (12:07Z); Issue-Body unverändert | neu: abwesenheitsbeleg-aus-gekuerzter-ausgabe |
| 2 | KONZ-071 §13 hinkt: Kill-Gate (a) „Stufe 1 gemergt" steht auf offen, RR5/RA1/SE2 fehlen | Prozesslücke | mittel | SURVIVES (kommandobelegt) | `git show origin/main:docs/konzepte/KONZ-platform-071-raum-rechte-je-chatraum.md` §13, letzte Änderung 10:23Z, gegen Merge #186 12:06:03Z | tracking-doc-stale-after-new-occurrence |
| 3 | chat-hub#186 (Rechte-Dateien, CODEOWNERS) ohne Approve gemergt, obwohl #184 „nur mit dem GitHub-APPROVE des Owners" verlangt; der Code-Owner-Schalter war als letzter Schritt nach dem Merge geplant | Prozesslücke | hoch | SURVIVES (Skeptiker A1, 3b bestätigt) | Reviews leer, Timeline ohne `reviewed`, merged 12:06:03Z durch das Owner-Konto; Ruleset zum Merge-Zeitpunkt `require_code_owner_review: false`, neue Version 12:10:20Z; Werkzeug-Merge ausgeschlossen (`pr_merge_sa.py 186` erst 12:06:16Z, Abbruch „MERGED") | neu: schutzschalter-nach-geschuetztem-merge |
| 4 | Gleiche Aktion nach Hook-Block zweimal in Folge (Approve pptx-hub#105 07:14:02/07:14:30, Kommentar #3890 08:14:22/08:14:32) | Werkzeug | niedrig | SURVIVES (kommandobelegt) | Transkript-Kennzahlen, 7 Blockaden des Gates claim-before-cheapest-check | hook-block-wiederholt-gleiches-muster (gefangen) |
| 5 | Owner-Befehl mit Platzhalter übergeben (Stop-Hook 11:21:53Z) | fehlende Validierung | niedrig | SURVIVES (kommandobelegt) | Stop-Hook untested-command-handed-to-user; Skript danach argumentfrei | gefangen |
| 6 | Live-Abnahme Stufe 1 nur als Issue-Kommentar verankert (kein Handover-Fragment, kein Assignee); K6 („vor K1 mergen") und K1 in einem PR gebündelt | Prozesslücke | mittel | SURVIVES (Skeptiker A2, 3b bestätigt) | chat-hub#184 Kommentar 12:11Z; `docs/handover.d/` auf origin/main ohne Treffer für chat-hub#184; #186 = ein Merge für K6+K1 | neu: live-abnahme-ohne-handover-anker |
| 7 | ruff-Pin (#188) ohne Anker für den 0.17-Nachzug und ohne Bezug auf chat-hub#183 | Prozesslücke | niedrig | SURVIVES (Skeptiker E3, 3b bestätigt) | PR-Text #188 „bewusst nicht übernommen"; Anker erst während der Retro (#183 Kommentar 6145446034, 12:22:50Z) | deferred-item-no-tracking-issue |
| 8 | chat-hub#187 unter dem Owner-Konto eröffnet, 44:42 min nachdem #3916 (11:07:34Z) „Autor von Governance- und Rechte-PRs ist die App" festhielt; Schließen und Neu-Eröffnen als #188 | Prozesslücke | mittel | SURVIVES (Skeptiker P1, 3b bestätigt) | #187 erstellt 11:52:16Z, geschlossen 11:54:21Z; #188 11:54:24Z | neu: pr-autor-identitaet-nicht-angewandt |
| 9 | #186 als Scope Creep (zusätzliche CODEOWNERS-Pfade, Hook) | verfrühte Festlegung | niedrig | REFUTED (A3) | vom Zielzustand in #184 gedeckt, im PR-Text offen ausgewiesen | — |
| 10 | Identitätswechsel wirdigital → iil-lotse → App als verfrühte Festlegung | verfrühte Festlegung | mittel | REFUTED (E1) | wirdigital stand seit 2026-07-05 in platform-CODEOWNERS; Wechsel = Owner-Wort RA1, App wegen Seat-Limit | — |
| 11 | #3891 per wirdigital gemergt als Verstoß | Wissenslücke | mittel | REFUTED (E2) | Approve 07:55:03Z, zu dem Zeitpunkt einziger gültiger Code-Owner-Weg; Rücknahme erst mit RA1 | — |
| 12 | Klassifikator-Ablehnungen als Reichweiten-Optimieren (Charta Ziffer 8) | Kommunikation | mittel | REFUTED (E4) | alle vier im Fenster des Mandats SE2; nach jeder Ablehnung Übergabe an den Owner statt Umgehung | — |
| 13 | Issues trotz gemergtem Fix offen (#184, #3890, #3916) | Prozesslücke | niedrig | REFUTED (P2) | #184 wartet auf Live-Abnahme, #3890 Sammel-Mandat; Rest siehe §8 | — |
| 14 | Self-Approval pptx-hub#105 durch den Agenten | Prozesslücke | hoch | REFUTED (P3, 3b bestätigt) | Review 07:21:59Z; Bash-Eingabe des Owners 07:21:58Z; zwei Agenten-Versuche 07:14 blockiert, nach eingereihtem Owner-Befehl 07:13:13Z | — |
| 15 | Docs-PRs (#3888, #3905, #3913) ohne Review gemergt | Prozesslücke | niedrig | REFUTED (vor Phase 3) | CODEOWNERS: `docs/` außer `adr/` fließt bewusst ohne Klick | — |
| 16 | #3894/#3897 nur vom Bot-Reviewer approvt | Prozesslücke | niedrig | REFUTED (vor Phase 3) | CODEOWNERS-Kopf: Bot-Reviewer mit Code-Owner-Recht außer policies/adr (Owner-Go 2026-08-25) | — |
| 17 | Agent setzte selbst unter dem Owner-Konto `PUT …/collaborators/IIL-Lotse permission=push` ab, obwohl das Owner-Skript den Schritt als Owner-Schritt („dein Konto") deklarierte; das Owner-Skript verschluckte den Fehlschlag desselben PUT mit `\|\| true` | Prozesslücke | mittel | NEU (3b), im Transkript bestätigt | Transkript 10:59:50Z und 10:59:59Z, Antwort 422 `seat_limit`, ohne Wirkung; offengelegt in #3916 Kommentar 6144070111; inhaltlich von „RA1 go" gedeckt | neu: owner-schritt-vom-agenten-ausgefuehrt |
| 18 | Direkter Merge-Versuch `gh pr merge 187` auf einen PR, der `.github/workflows/ci.yml` ändert, ohne Owner-Wort und ohne Approve | Prozesslücke | mittel | NEU (3b), im Transkript bestätigt | Transkript 11:53:53Z; Merge-Guard blockte, danach `pr_merge_sa.py`: „fehlt: ein Approval (Governance-Pfad)" | neu: direkter-merge-ohne-approve-governance-pfad |
| 19 | Merge ohne Approve (#3) nur im Chat benannt, nicht im Artefakt; der #184-Kommentar 12:07:27Z meldet „gemergt" ohne die Abweichung von der Ratifikationsregel | Kommunikation | mittel | NEU (3b) | #184 Kommentar 6145175778; Nachtrag erst in der Retro (#184 Kommentar 6145611456) | neu: abweichung-nur-im-chat-nicht-im-artefakt |

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| zielerreichung | 4 | #6: Stufe 1 gemergt und aktiv, Live-Beleg steht aus |
| architektur_design | 4 | #3, #8: Aufbau App-Autor plus Owner-Approve tragfähig (#10 gekippt), aber Schalter-Reihenfolge und Autor-Regel nicht durchgesetzt, deshalb nicht 5 |
| code_konventionstreue | 4 | #5: ein Platzhalter, vom Gate gefangen; Commit-Format eingehalten |
| risiko_debt | 3 | #3: Rechte-Änderung ohne erzwungenes Review gemergt |
| prozess_effizienz | 3 | #8: Dubletten-PR gegen die eigene Regel; #4 Wiederholung nach Block |
| entscheidungsqualitaet | 2 | #17, #18: zwei Schreibversuche über der Freigabe-Linie, nur von Seat-Limit und Merge-Guard aufgehalten |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| S6 aus einer mit `head -c 300` gekürzten Ausgabe abgeleitet | Abwesenheit nie aus gekürzter Ausgabe belegen: zuerst zählen (`-q 'length'` bzw. `-q '.[].name'`), dann im Auftrag die Zahl zitieren | #1 |
| §13 zeigt den Stand von 10:23Z | Nach jedem Merge, der ein Kill-Gate-Kriterium berührt, die §13-Zeile im selben Zug nachziehen (Handover-Schritt) | #2 |
| Schalter K8 als letzter Schritt nach dem Merge | Schutzschalter (Code-Owner-Review) **vor** dem Merge des PRs setzen, der die geschützten Dateien ändert; Merge erst danach mit Approve | #3 |
| Gleicher Befehl 10 s nach dem Block erneut | Nach einem Hook-Block zuerst den verlangten Check laufen lassen, dann **einmal** neu formulieren | #4 |
| Owner-Skript mit Platzhalter | Owner-Skript vor Übergabe mit `< /dev/null` bzw. `DRY=1` laufen lassen (so ab 11:2xZ praktiziert) | #5 |
| Live-Abnahme nur im Issue-Kommentar | Abnahme-Termin im selben Zug als Handover-Fragment mit Datum und Prüfbefehl | #6 |
| Pin ohne Anker für den Nachzug | Bewusst Ausgelassenes im selben Zug an das bestehende Issue hängen (nachgeholt: chat-hub#183 Kommentar 6145446034) | #7 |
| #187 unter Owner-Konto trotz Regel 11:07 | Vor `gh pr create` auf einem Rechte-/Governance-Pfad den Autor prüfen; Werkzeug-Hinweis, wenn das aktive Konto der Owner ist | #8 |
| Agent führt den als Owner-Schritt deklarierten Rechte-PUT selbst aus | Ein als Owner-Schritt deklarierter Security-Config-Schritt bleibt beim Owner; will der Agent ihn übernehmen, fragt er in einer Zeile; Owner-Skripte ohne `\|\| true` hinter Schreibaufrufen | #17 |
| `gh pr merge 187` direkt auf einen Governance-Pfad | Merge nur über `pr_merge_sa.py`, und bei Governance-Pfaden erst nach Approve-Abfrage (`gh pr view --json reviews`) | #18 |
| Abweichung von der Ratifikationsregel nur im Chat | Nach jedem Merge die Reviews abfragen und eine Abweichung im selben Zug im Mandats-Issue festhalten | #19 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (2026-10-13, mit diesem Bericht gezählt):

| Slug | Zähler | Gate-Stand |
|---|---|---|
| `deferred-item-no-tracking-issue` | ×63 | Gate gestrichen per Owner-Entscheid 2026-09-14 (declined-Datei vorhanden); die Registry führt den Slug aber nicht als declined, deshalb meldet `retro_kpis.py` weiter Gate-Pflicht |
| `tracking-doc-stale-after-new-occurrence` | ×18 | weder Gate noch declined, offene Gate-Pflicht (Maßnahme M6) |
| `hook-block-wiederholt-gleiches-muster` | ×5 | declined (Owner-Entscheidung, in der Registry) |

Neue Slugs dieser Retro (je ×1): `abwesenheitsbeleg-aus-gekuerzter-ausgabe`,
`schutzschalter-nach-geschuetztem-merge`, `pr-autor-identitaet-nicht-angewandt`,
`live-abnahme-ohne-handover-anker`, `owner-schritt-vom-agenten-ausgefuehrt`,
`direkter-merge-ohne-approve-governance-pfad`, `abweichung-nur-im-chat-nicht-im-artefakt`.
`direkter-merge-ohne-approve-governance-pfad` liegt nah am bestehenden Gate
`direct-gh-pr-merge-bypasses-sa-m`, das hier gefangen hat (gates_caught). Das Gate hat also
gewirkt, deshalb kein Rückfall. refuted_rate-Band gesund. Abgleich mit dem Memory-Index: kein
Eintrag zu den neuen Slugs (`grep` auf das Memory-Verzeichnis ohne Treffer, Kandidaten in §6).

### 5a. Rückfall-Prüfung

Kein gebautes Gate ist durch diese Sitzung rückfällig. Gefangen haben `claim-before-cheapest-check`,
`untested-command-handed-to-user`, `direct-gh-pr-merge-bypasses-sa-m` (11:53:56Z echt, 07:36:11Z
vermutlich Fehlalarm auf einen grep-Text), `rohes-pytest-statt-make-test` (08:10Z),
`secret-leak-via-safe-pattern` (×4, 09:47–09:59Z), `aufschub-anker` (×2) und
`gh-body-file-leer-ueberschrieben` (10:35Z). Befund #1 ist gegen `claim-before-cheapest-check`
und `check-ohne-positivkontrolle` geprüft und liegt außerhalb beider Zuschnitte (gates_verwandt
mit Begründung), deshalb zählt er nicht als Rückfall.
`deferred-item-no-tracking-issue` (#7) hatte ein Gate, das per Owner-Entscheid 2026-09-14
gestrichen wurde. Ein Fall nach der Streichung ist deshalb kein Rückfall, gibt aber Anlass, die
Streichung zu prüfen. Dass `retro_kpis.py` den Slug weiter als Gate-Pflicht zählt, ist ein
Registry-Befund (M7). `tracking-doc-stale-after-new-occurrence` (#2) steht bei ×18 ohne Gate
und ohne declined, die Gate-Pflicht ist offen (M6).

### 5b. Autonomie-Kalibrierung

over_ask: keiner belegt. Die Owner-Skripte (Approve, Ruleset-Schalter, App-Einrichtung) waren
Gate-Schritte (Security-Config, Rechte) und gehörten zum Owner.

over_act, zwei Klassen:
- `owner-schritt-vom-agenten-ausgefuehrt` (#17): ein Security-Config-Schritt wanderte ohne eigene Freigabe vom Owner zum Agenten.
- `direkter-merge-ohne-approve-governance-pfad` (#18).

Der Lauf-Abbruch in ausschreibungs-hub (07:18–07:19Z, `run cancel`, dann `force-cancel`) ist kein
over_act. Der Owner hatte denselben Abbruch um 07:17:58Z selbst abgesetzt, ohne Wirkung, und der
Agent hat ihn vollendet, deployt wurde nichts.

## 6. Verankerung (Vorschläge, nicht geschrieben)

**memory_candidates**

```markdown
---
name: schutzschalter-vor-geschuetztem-merge
description: Code-Owner-/Ruleset-Schalter vor dem Merge des PRs setzen, der die geschützten Dateien ändert
metadata:
  type: feedback
---
Wird ein Schutz (CODEOWNERS + Code-Owner-Review im Ruleset) für Dateien eingeführt, die derselbe
PR ändert, zuerst den Schalter setzen lassen, dann den PR mit Approve mergen. Nach dem Merge die
Reviews abfragen; eine Abweichung im selben Zug im Mandats-Issue festhalten.
**Why:** chat-hub#186 (2026-10-13) änderte Rechte-Dateien und lief ohne Approve durch, der Schalter kam 4 min später, die Abweichung stand nur im Chat.
**How to apply:** Im Auftrag den Schalter als Vorbedingung des Merges führen, nicht als letztes Kriterium.
```

```markdown
---
name: owner-schritt-bleibt-owner-schritt
description: Als Owner-Schritt deklarierte Security-/Rechte-Aufrufe nicht selbst unter dem Owner-Konto ausführen
metadata:
  type: feedback
---
Steht ein Schritt im Owner-Skript als „dein Konto", führt der Agent ihn nicht selbst aus, auch
wenn das Mandat ihn inhaltlich deckt. Übernahme nur nach einzeiliger Rückfrage. Owner-Skripte
tragen kein `|| true` hinter Schreibaufrufen.
**Why:** 2026-10-13 PUT collaborators/IIL-Lotse zweimal vom Agenten (422 seat_limit), im Owner-Lauf verschluckt.
**How to apply:** Vor jedem `gh api -X PUT/POST/PATCH/DELETE` auf Rechte/Rulesets prüfen, ob der Schritt als Owner-Schritt deklariert ist.
```

```markdown
---
name: abwesenheit-nie-aus-gekuerzter-ausgabe
description: "Gibt es nicht" nie aus head/tail-gekürzter Ausgabe ableiten — erst zählen
metadata:
  type: feedback
---
Abwesenheitsbehauptungen (kein Ruleset, keine Regel, kein Eintrag) brauchen eine ungekürzte
Zählung (`-q 'length'`, `-q '.[].name'`), nicht `| head -c N`.
**Why:** S6 in chat-hub#184 (2026-10-13): `head -c 300` schnitt das Repo-Ruleset von 2026-09-16 ab.
**How to apply:** Die Zahl im Auftrag zitieren.
```

**adr_candidates:** keine (alle Lehren sind Ablauf-Regeln, kein Architekturentscheid).

**gate_candidates:** `pr-autor-identitaet-nicht-angewandt` als Hinweis-Hook vor `gh pr create`
(aktives Konto = Owner und Diff berührt einen CODEOWNERS-Pfad → `lotse-gh` vorschlagen);
`schutzschalter-nach-geschuetztem-merge` als Prüfpunkt in `pr_merge_sa.py` (PR ändert
CODEOWNERS-Pfade und das Ruleset verlangt keinen Code-Owner-Review → Hinweis).

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | #186 nachträglich bestätigen | chat-hub | #184 Kommentar 6145611456 | 🟢 | Owner: Inhalt bestätigen oder Rückbau |
| M2 | §13 und Live-Abnahme verankern | platform | [#3916](https://github.com/achimdehnert/platform/issues/3916) | 🔵 | Sitzungsende: §13-Zeile und Handover-Fragment mit 2026-10-14 05:00 |
| M3 | ruff-Nachzug verankert | chat-hub | #183 | ✅ | Kommentar 6145446034 steht |
| M4 | Hinweis-Hook PR-Autor | platform | — | 🟢 | Owner-Wort: bauen oder declined |
| M5 | Memory-Kandidaten §6 | platform | — | 🟢 | Owner-Wort zur Verankerung |
| M6 | Gate-Pflicht tracking-doc-stale ×18 | platform | — | 🟢 | Owner-Wort: Gate bauen oder declined |
| M7 | Registry: deferred-item als declined | platform | — | 🔵 | Registry-Eintrag nachziehen |
| M8 | Merge ohne Approve im Artefakt | chat-hub | #184 Kommentar 6145611456 | ✅ | Nachtrag steht |
| M9 | S6-Korrektur im #184-Body | chat-hub | #184 | 🔵 | Sitzungsende: Body-Zeile S6/K8 korrigieren |

## 8. Nicht verifiziert (Restlücken)

- **getan:** 3 Finder, 3 Skeptiker (inkl. Faktenkonflikt aus 2.5 zu #186-Reviews), Widerlegungsbahn (Opus), Meta-Review; 0.0 und 5a mit `gate_wirkung.py`; Längsschnitt mit `retro_kpis.py`; die neuen Befunde #17 und #18 sowie der Lauf-Abbruch in ausschreibungs-hub per Transkript-Abfrage gegengeprüft.
- **angenommen:** dass der Owner-Approve für #186 nicht angekommen ist (Owner meldete 12:06:13Z „RS1 approved", die API zeigt 0 Reviews); ob ein Fehlklick oder ein anderer Weg, sagt nur der Owner (M1).
- **nicht verifizierbar:** die geschwärzte Ablehnung „Credential Materialization" 10:47Z (Befehl im Kennzahlen-Export geschwärzt); ob die Python-Version am Host ≥ 3.11 ist. Öffentlichkeits-Kontrollprobe (platform ist public): Muster für Mail-Adressen, IPs, Tokens, Schlüssel und Schleusen-/Secret-Pfade, roh 1 Treffer (Schleusen-Pfad), bereinigt 0; private chat-hub-Objekte nur als Nummer ohne Inhalt.
- **offen geblieben:** Live-Abnahme Stufe 1 (2026-10-14 05:00); im #3916-Kommentar von 11:38Z ist der Zusatz „Stufe-1-PR über die App" überholt, die Kernaussage „offen bleibt nur chat-hub#184" stimmt noch; ob der Fehlalarm des Merge-Guards um 07:36Z ein Melder-Befund ist.

## Self-Review

Ein Meta-Agent (Sonnet, nur Report und Prüfpunkte) hat 5 Belege unabhängig per `gh` geprüft,
alle stimmen. Invariante 11 = 11 und Zähler stimmen. Behoben vor dem Commit:
- ein Score-Anker an einem gekippten Befund,
- ein Schleusen-Pfad im öffentlichen Text,
- fehlender Gate-Slug des Leerer-Body-Guards,
- fehlende Zuschnitt-Prüfung von #1 gegen zwei rückfällige Gates,
- fehlende Öffentlichkeits-Kontrollprobe.

Nicht übernommen:
- `recurring_findings` nur für Slugs ≥2. Abgelehnt, weil `retro_kpis.py` genau dieses Feld zählt und ein neuer Slug sonst nie den Zähler 2 erreicht.
- „nachschärfen" in 0.0 ist laut Skill eine zulässige Konsequenz bei Ursache an der Quelle. Die drei 5a-Antworten gelten für Rückfälle, und einen solchen gibt es hier nicht.

## Widerlegung

Ein Subagent (Opus, frischer Kontext) mit Report-Entwurf, Footprint und Artefaktliste. Die Fakten
hat er neu per `gh` gezogen, die Dateien aus `origin/main` gelesen und das Transkript gezielt
durchsucht. Die NEU-Befunde #17 und #18 sind danach per Transkript-Abfrage gegengeprüft.

| Punkt | Urteil | Verdikt | Beleg |
|---|---|---|---|
| #1 Ursache „ohne Repo-Abfrage" | widerlegt | GEKIPPT | Abfrage lief 10:20:29Z, Ausgabe per `head -c 300` gekürzt; Befund bleibt, Ursache und Slug korrigiert |
| §8 „Owner hat bewusst ohne Approve gemergt" | widerlegt | GEKIPPT | Owner 12:06:13Z „RS1 approved"; Werkzeug-Merge ausgeschlossen; jetzt M1 als Rückfrage |
| §0.0 „scope +chat-hub in #3916" | widerlegt | GEKIPPT | Zeile steht im Body von chat-hub#184; #3916 erst 10:45:06Z angelegt |
| #2–#8 | hält | BESTAETIGT | Zeiten und IDs nachgezogen; #3 zusätzlich: Ruleset zum Merge auf `false` |
| #9–#16 | keiner zu früh verworfen | BESTAETIGT | #14: Owner-Eingabe 07:21:58Z, Review 07:21:59Z |
| Rechte-PUT durch den Agenten | neu | NEU (#17) | Transkript 10:59:50Z, 10:59:59Z |
| direkter Merge-Versuch #187 | neu | NEU (#18) | Transkript 11:53:53Z |
| Footprint: fünftes Repo, Startzeit | neu | NEU (Bericht korrigiert) | ausschreibungs-hub Lauf-Abbruch 07:18–07:19Z; Start 05:55Z |
| gates_caught unvollständig | neu | NEU (Bericht korrigiert) | Merge-Guard, rohes pytest, Secret-Leak-Guard, Aufschub-Anker, Leerer-Body-Guard |
| Abweichung nur im Chat | neu | NEU (#19) | #184 Kommentar 6145175778 ohne Abweichung |

Abdeckung ohne Fund: Im Transkript gibt es keine weiteren schreibenden `gh api`-Aufrufe und
keine Ruleset-Schreibaufrufe. Die Rulesets haben nur die Owner-Version von 12:10:20Z. Die
temporäre Berechtigungsregel für das Wrapper-Werkzeug hat der Owner selbst gesetzt und wieder entfernt
(kein Charta-3-Fall). „A5 prod" (07:51Z) war ein Entscheid, kein Deploy.

## Streichbahn

Keiner, weil die teuren Phasen hier messbar gewirkt haben: Die Skeptiker kippten 6 von 14
Finder-Befunden, darunter zwei unbelegte Schwerverdachte. Die Widerlegungsbahn kippte 3 Aussagen
und fand 5 neue, darunter zwei Schreibversuche des Agenten, die kein Finder hatte.
