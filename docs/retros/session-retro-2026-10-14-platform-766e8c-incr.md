---
retro_schema: 1
date: 2026-10-14
repo_scope: [platform]
session_id: 766e8c-incr
footprint: lean
footprint_reduction_reason: "Inkrement mit 1 Repo und 2 neuen PRs (#3992 geschlossen, #3994 offen). Kein Prod-Schritt, keine Migration, kein ADR. Die Hook-Verteilung nach ~/.claude hat der Owner per eigenem Skript ausgeführt."
findings_total: 6
findings_survived: 6
refuted_rate: 0.0
phase3_refuted: 0
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 2
  entscheidungsqualitaet: 3
gate_candidates: [merge-vermerk-durch-zitat]
recurring_findings: [pr-autor-identitaet-nicht-angewandt, hook-drill-ohne-fehlalarm-gegenprobe, hook-zweck-speichert-befehlstext, formatter-auf-verzeichnis-statt-eigene-dateien, owner-skript-prueft-vorbedingung-nicht, merge-vermerk-durch-zitat]
gates_caught: []
gates_verwandt: [pr-autor-identitaet-nicht-angewandt]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "n/a (lean): 0 gekippt, 0 neu"
streichkandidaten: []
streich_begruendung: "keiner, weil das Inkrement nur die Pflichtteile von lean nutzte und jeder davon wirkte: Die Wirkungsbilanz verwies alle vier rückfälligen Gates auf den Beschluss der Parent-Retro, und die Zuschnitt-Prüfung zu Befund 1 ergab ein Ausweitungs-Issue statt eines zweiten Gates."
---

# Session-Retro 2026-10-14 (platform, Sitzung 766e8c, Inkrement)

Inkrement zur Retro [`session-retro-2026-10-14-platform-766e8c.md`](session-retro-2026-10-14-platform-766e8c.md), Zeitraum ab ca. 14:44 UTC. Inhalt: Ressourcen-Lease in Betrieb genommen, erster Fehlalarm im Zielkontext, Fix.

Artefakte dieses Inkrements:

- PR [#3981](https://github.com/achimdehnert/platform/pull/3981) Ressourcen-Lease: Owner-Approve, Merge per pr_merge_sa (M2), 14:49:45Z. In der Parent-Retro stand er noch als offen.
- PR [#3992](https://github.com/achimdehnert/platform/pull/3992) Fehlalarm-Fix: unter dem Owner-Konto eröffnet und deshalb geschlossen (Befund 1).
- PR [#3994](https://github.com/achimdehnert/platform/pull/3994) Fehlalarm-Fix plus Lease-Zweck ohne Befehlsargumente: eröffnet von App lotse-autor, CI grün, wartet auf den Owner-Approve.
- [#3977 Kommentar 6171516387](https://github.com/achimdehnert/platform/issues/3977#issuecomment-6171516387) (K4-Stand, Fehlalarm) und [Kommentar 6172076851](https://github.com/achimdehnert/platform/issues/3977#issuecomment-6172076851) (K4 erfüllt, Befund 5).
- Issue [#3997](https://github.com/achimdehnert/platform/issues/3997): Gate pr-autor-identitaet ausweiten (Befund 1).

## 0.0 Wirkungsbilanz

`tools/gate_wirkung.py` lief als erster Schritt. Es meldet vier rückfällige Gates: `claim-before-cheapest-check`, `built-but-never-called`, `scope-checkpoint-not-durably-recorded` und `check-ohne-positivkontrolle`. Über alle vier ist bereits entschieden, in der Parent-Retro [§0.0 und §5a](session-retro-2026-10-14-platform-766e8c.md) sowie in den Retros desselben Tages. Diese Retro trifft keinen zweiten Beschluss. Im Inkrement kam keines der vier Muster erneut vor.

`fremde-sitzung-schreibt-externe-ressource` (gebaut in #3981) steht auf `zu-frueh`, blocking, 0/0. Das heißt nur: noch ungeprüft. Ein Wirksamkeitsbeleg ist das nicht.

## 1. Executive Summary

- Die Ressourcen-Lease ist gemergt und verteilt. Der Hook greift sofort auch in laufenden Sitzungen, die Annahme „erst nach /hooks“ ist widerlegt. Das Journal hat 3 echte Einträge, damit ist K4 erfüllt.
- Beim ersten Echtlauf gab es einen Fehlalarm: Ein Lesebefehl mit `2>/dev/null` wurde gesperrt (#2). Außerdem hat der Lease-Zweck Befehlstext gespeichert, was ein Leck-Risiko für Tokens ist (#3). Beides behebt #3994.
- Eigener Fehler, in dieser Sitzung zum zweiten Mal: ein Approve-pflichtiger PR unter dem Owner-Konto (#1). Der vorhandene Hinweis-Hook kennt diese Pfadklasse nicht. Die Ausweitung steht in #3997.
- Gefangen vor dem Commit: `ruff format` auf das ganze Verzeichnis hätte 10 fremde Dateien geändert (#4).
- Der Owner hat das Verteilskript vor dem Merge ausgeführt (#5). Das hat nicht geschadet, das Skript prüft die Vorbedingung aber nicht.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Den Fehlalarm-Fix habe ich als #3992 unter dem Owner-Konto eröffnet, obwohl der gleiche Fehler bei #3980 in derselben Sitzung kurz vorher gemeldet war. Der Owner-Approve scheiterte, der PR wurde geschlossen und als #3994 neu eröffnet. Das kostete einen Owner-Klick. Der Hinweis-Hook ist installiert, blieb aber still: `tools/claude-hooks/` steht weder in CODEOWNERS noch in `governance_pfade`. Die Approve-Pflicht kommt aus der W1/M1-Regel von pr_merge_sa. | Werkzeug | mittel | SURVIVES (kommandobelegt) | #3992 Autor achimdehnert, Approve-Fehler 15:10:38Z „Review Can not approve your own pull request“; #3994 Autor app/lotse-autor; `.github/CODEOWNERS` Zeile 77 (`/tools/` bewusst ungeschützt); `policies/autonomy-gates.md` Zeile 339 (`governance_pfade`); `tools/pr_merge_sa.py:721` (M1 nur per Approve oder Freigabe-Vermerk) | pr-autor-identitaet-nicht-angewandt (Gate, Fall außerhalb des Zuschnitts, §5a) |
| 2 | Der neue Lease-Hook sperrte beim ersten Echtlauf einen reinen Lesebefehl (`ls … 2>&1`, `tail … 2>/dev/null`), weil die Umgehungsprüfung jedes `>` als Schreiben wertete. Der Drill hatte keine Gegenprobe in Realform, also keinen Lesebefehl mit harmloser Umleitung auf dem Lease-Pfad. Der erste Fix in #3994 war selbst noch zu schmal: Während dieser Retro sperrte der Hook einen Lesebefehl mit `>` in einem `python3 -c`-String. Diese Form deckte die `/dev/null`-Ausnahme nicht ab. | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | Fehllauf 14:50:34Z im Transkript (`scratchpad/kennzahlen_incr.txt`); zweiter Fehllauf in der Retro-Sammlung (~15:40Z); Fix #3994 Commits f1e5f887 und 315684be (shlex-Zerlegung), `make test` 7252 passed | hook-drill-ohne-fehlalarm-gegenprobe ×1 |
| 3 | Lease und Journal speicherten als „Zweck“ die ersten 120 Zeichen des Befehls. Ein Token in Argumenten oder in `VAR=wert` wäre dort im Klartext gelandet. Aufgefallen erst an der ersten echten Lease; die Altzeilen enthalten Mandanten- und Beleg-Präfixe, kein Token. | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | #3994 Commit „Lease-Zweck ohne Befehlsargumente“, Test `test_should_keep_command_arguments_out_of_lease_and_journal` | hook-zweck-speichert-befehlstext ×1 |
| 4 | `ruff format tools/claude-hooks/` formatierte 10 fremde Dateien um. Das fiel im Diff vor dem Commit auf und wurde zurückgenommen. | Werkzeug | niedrig | SURVIVES (kommandobelegt) | #3994 Diff enthält nur 2 Dateien; Rücknahme per `git checkout` im Transkript | formatter-auf-verzeichnis-statt-eigene-dateien ×1 |
| 6 | Nachtrag nach dem Merge dieser Retro: Ich habe die Vermerk-Formel aus pr_merge_sa in #3997 als Erklärung wörtlich zitiert. Die Regex `FREIGABE_VERMERK` traf das Zitat, der Retro-PR #3999 lief mit „M1 deckt W1“ durch. Beim Anlegen von #4000 passierte derselbe Fehler noch einmal. Beide Bodies sind korrigiert, Nachprüfung 0 Treffer. Ohne Folgen blieb das nur, weil #3999 auch mit M0 durchgegangen wäre (wie #3983). Ein Verweis von #3994 auf #3997 hätte den Owner-Approve umgangen. | Werkzeug | hoch | SURVIVES (kommandobelegt) | pr_merge_sa-Ausgabe #3999 „W1/M1 — M1 deckt W1“; #3983 „W1/M0 — M0 deckt W1“ (Transkript 14:47:11Z); Regex-Probe auf #3997 und #4000 vorher 1, danach 0 Treffer; `tools/pr_merge_sa.py:241` | merge-vermerk-durch-zitat ×1, Gate-Kandidat [#4000](https://github.com/achimdehnert/platform/issues/4000) |
| 5 | Der Owner führte `sl.sh` vor dem Merge von #3994 aus, also mit der alten Hook-Fassung. Die Reihenfolge stand in der Antwort. Das Skript prüft aber nur „Hook auf main“, nicht „Fix auf main“. | Kommunikation | niedrig | SURVIVES (inline, kein Skeptiker) | #3994 weiterhin OPEN; Owner-Ausgabe „Eintrag schon vorhanden“ im Transkript; #3977 Kommentar 6172076851 | owner-skript-prueft-vorbedingung-nicht ×1 |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 3 | Lease in Betrieb, K4 erfüllt; der Fix #3994 ist ungemergt, K5 offen (#2, #5) |
| architektur_design | 4 | Der Fix hält die Sperre für echte Schreibwege und lässt Lesen durch, der Zweck ist datensparsam (#2, #3) |
| code_konventionstreue | 3 | Formatter auf das Verzeichnis (#4), PR-Autor falsch (#1) |
| risiko_debt | 2 | Leck-Risiko im Zweck behoben (#3); dafür offene Mandats-Lücke in pr_merge_sa, nur per Textkorrektur entschärft (#6) |
| prozess_effizienz | 2 | Wiederholter Konto-Fehler mit Rework und Owner-Klick (#1) |
| entscheidungsqualitaet | 3 | Fehlalarm sofort gemeldet und behoben; der Drill war vorher zu schmal (#2) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| #3992 unter dem Owner-Konto, obwohl pr_merge_sa für platform M1 verlangt | Vor `gh pr create` in platform fragen: Braucht der Merge mindestens M1, und fehlt ein Freigabe-Vermerk im Issue? Dann `lotse-gh`. Mechanisch über die Hook-Ausweitung #3997 | #1 |
| Drill nur mit Sperr-Fällen und künstlichen Durchlässen; Shell-Syntax per Regex geprüft | Jeder Sperr-Hook bekommt vor dem Merge Gegenproben in Realform: der eigene Lesebefehl auf denselben Pfad, mit `2>/dev/null`, Pipe und Inline-Skript. Shell-Operatoren werden per Tokenizer erkannt, nicht per Regex | #2 |
| Zweck als Befehlsausschnitt | Dauerhaft gespeicherte Felder in Hooks enthalten nie freien Befehlstext, nur Programmname, Skriptname oder Pfad. Ein Test mit Token in Argumenten belegt das | #3 |
| `ruff format <verzeichnis>` | `ruff format` nur auf die Dateien aus `git diff --name-only` | #4 |
| Verteilskript ohne Vorbedingung | `sl.sh` nimmt den erwarteten PR als Parameter und bricht ab, solange der nicht auf `origin/main` liegt | #5 |
| Vermerk-Formel trifft auch Zitate im Fließtext | Der Freigabe-Vermerk zählt nur als eigene Zeile, mit Test für die Erklär-Zeile als Gegenprobe. Bis dahin steht die Formel in Issue-Texten nie wörtlich, nur als Verweis auf `FREIGABE_VERMERK` | #6 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` ist gelaufen. Per `git grep` gegen `origin/main:docs/retros/` kommt `pr-autor-identitaet-nicht-angewandt` in 2 früheren Retros vor. Mit diesem Inkrement sind es 3, damit gilt GATE-PFLICHT. Ein Gate existiert, die Antwort steht in §5a. Die vier neuen Slugs kamen bisher nicht vor.

Abgleich mit `MEMORY.md` per grep: Es gibt 1 Eintrag zu `lotse-autor`, die 🌀-Memory zum Code-Owner-Review. Sie nennt Code-Owner-Pfade, nicht die W1/M1-Klasse, und deckt den Fall #1 deshalb nicht ab (Vorschlag in §6).

### 5a. Rückfall-Prüfung

- **Gate pr-autor-identitaet-nicht-angewandt:** Der Fall liegt außerhalb des Zuschnitts und steht deshalb unter `gates_verwandt`. Der Hook ist installiert, die Pfadklasse prüft er aber nicht. Er meldet nur bei CODEOWNERS- und `governance_pfade`-Treffern, `tools/claude-hooks/` ist keins von beiden. Ursache an der Quelle, Antwort **ausweiten**: Der Hook übernimmt die M1-Pflicht aus pr_merge_sa, mit `revised`, `revision_note` und einer neuen `positivkontrolle` in der Form von #3992. Das ist ein Vorschlag mit Preis in [#3997](https://github.com/achimdehnert/platform/issues/3997) und wartet auf das Owner-Wort „PA go“.
- Die vier rückfälligen Gates aus 0.0 traten hier nicht erneut auf.

### 5b. Autonomie-Kalibrierung

- over_ask: keine. Vorgelegt wurden nur Owner-Approve, die Verteilung nach `~/.claude` und die K5-Probe. Alle drei brauchen Owner-Rechte (Charta 3, kein Selbst-Approve).
- over_act: keine. Ich habe keinen Merge ohne Mandat gemacht, nichts in sevdesk geschrieben und das Buchhaltungs-Board nicht angefasst. Die Owner-Nachrichten „RE go“ und „PS dort“ gingen als Daten an die Parallelsitzung, nicht als Befehl.

## 6. Verankerung (Vorschläge, nicht geschrieben)

- **memory_candidate (feedback, Ergänzung der 🌀-Memory zum Code-Owner-Review):** „In platform braucht jeder Merge mit Wirkung ≥ W1 das Mandat M1. Das gibt es nur per Approve oder per Vermerk ‚Freigabe: akzeptiert durch Owner‘ im verlinkten Issue. Ohne Vermerk den PR immer per `lotse-gh` eröffnen, auch außerhalb von CODEOWNERS (etwa `tools/claude-hooks/`). **Why:** #3980 und #3992 am 2026-10-14, beide geschlossen. **How to apply:** vor `gh pr create` in platform den Pfad gegen `docs/retros/` (W0) prüfen; alles andere über die App.“
- **memory_candidate (feedback):** „Sperr-Hooks: vor dem Merge eine Gegenprobe mit dem eigenen Lesebefehl auf den gesperrten Pfad, mit Umleitung und Pipe. **Why:** #3994, Fehlalarm beim ersten Echtlauf.“
- **adr_candidates:** keine.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Owner-Approve Fix | platform | [#3994](https://github.com/achimdehnert/platform/pull/3994) | 🟢 | Owner: `bash ~/zug/ap3994.sh`, dann Merge per pr_merge_sa |
| 2 | Hook neu verteilen | platform | [#3977](https://github.com/achimdehnert/platform/issues/3977) | ⛔ | nach Merge #3994: Owner `bash ~/zug/sl.sh` |
| 3 | K5-Probe Ausweg | platform | [#3977](https://github.com/achimdehnert/platform/issues/3977) | 🟢 | Owner: `!`-Befehl als eigene Eingabe |
| 4 | Autor-Gate ausweiten | platform | [#3997](https://github.com/achimdehnert/platform/issues/3997) | 🟢 | Owner: „PA go“ |
| 5 | sl.sh Vorbedingung | platform | [#3977](https://github.com/achimdehnert/platform/issues/3977#issuecomment-6172076851) | 🟢 | Owner: „SV go“ |
| 6 | Memory-Ergänzungen | — | Abschnitt 6 | 🟢 | Owner verankert oder verwirft |
| 7 | Vermerk nur als Zeile | platform | [#4000](https://github.com/achimdehnert/platform/issues/4000) | 🟢 | Owner: „VZ go“, PR über lotse-gh |

## 8. Nicht verifiziert (Restlücken)

- **Weitere Vermerk-Quellen ungeprüft (#6):** Ich habe nur die Bodies von #3977, #3997, #3999 und #4000 gescannt. Andere Issues mit zitierter Formel, etwa Doku-Issues zu pr_merge_sa, könnten genauso ein falsches M1 liefern. Die Suche nach der Formel in offenen platform-Issues liefert mindestens 30 Treffer, meist echte Mandats-Issues. Echte Zeilen-Vermerke und Zitate habe ich dabei nicht unterschieden. Billigster Check: die Trefferliste gegen die Zeilenform aus #4000 laufen lassen.
- **Kein Skeptiker für #5** (lean). Die Wertung „Skript statt Antworttext“ ist ein Selbsturteil. Ein Steelman: Die Reihenfolge stand klar da, und ein Skript-Parameter macht den Owner-Zug länger. Billigster Check: ein Sonnet-Skeptiker, etwa 55k Tokens.
- **Altzeilen im lokalen Journal** enthalten Zweck-Ausschnitte mit Mandanten- und Beleg-Präfixen. Ein Muster-Scan nach Token-Formen (`ghp_`, `github_pat_`, `sk-`, `Bearer`, `token`, `secret`, `passw`) fand 2 Treffer. Beide sind `sk-` im Board-Namen „sevdesk-…“, also kein Token. Nicht abgedeckt sind Token-Formen außerhalb dieser Muster.
- **K5 ungeprüft:** Ob ein `!`-Befehl am Hook vorbeiläuft, ist weiter Hypothese. Der eingereihte Befehl kam als Text an.
- **Preis der Ausweitung #3997** ist geschätzt (API-Aufrufe je `gh pr create`), nicht gemessen.

getan: Merge #3981, Fehlalarm-Meldung in #3977, Fix #3994 mit Tests und shlex-Nachtrag, K4-Nachweis, Journal-Scan, Issues #3997 und #4000, Entschärfung beider Bodies, diese Retro mit Nachtrag #6 · angenommen: dass Token nur in den gescannten Formen auftreten · nicht verifizierbar: #5 ohne Skeptiker, Wirksamkeit des Lease-Gates (zu-frueh, 0/0) · offen geblieben: Owner-Approve #3994, Neuverteilung, K5-Probe, Entscheide PA und SV.

## Widerlegung

n/a (lean): Ohne Subagenten gibt es keine Widerlegungsbahn, die Restlücke steht in §8. Das höchste Kipp-Risiko hat #5. Ein Gegenargument wäre, dass ein idempotentes Skript den Doppellauf ohnehin verträgt und der Befund nur einen Komfort-Mangel beschreibt.

## Streichbahn

Keiner, weil das Inkrement nur die Pflichtteile von lean nutzte und jeder davon wirkte. Die Wirkungsbilanz verwies alle vier rückfälligen Gates auf den Beschluss der Parent-Retro. Die Zuschnitt-Prüfung zu Befund 1 ergab ein Ausweitungs-Issue statt eines zweiten Gates.
