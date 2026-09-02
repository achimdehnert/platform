---
retro_schema: 1
date: 2026-08-20
repo_scope: [platform]
session_id: 8d6869
footprint: full
findings_total: 10
findings_survived: 6
refuted_rate: 0.4
phase3_refuted: 2
pre_refuted: 2
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [same-file-serial-prs, gate-approval-needs-pr-comment, worktree-midsession-accumulation]
over_ask: 1
over_act: 0
recurring_findings: [same-file-serial-prs, gate-approval-needs-pr-comment, worktree-midsession-accumulation]
---

# Session-Retro 2026-08-20 — platform (8d6869)

Vormittagssitzung, ~09:41–10:45 UTC. Inhalt: ein Mailentwurf gekürzt und mit echten Umlauten
neu abgelegt, drei gesendete Vorgänge im Ledger fortgeschrieben, ein Kontrastfehler der
Mailansicht gefunden und behoben (PR #2144, gemergt, Dienst neu gestartet), derselbe Code
danach auf CSS-Variablen gezogen (PR #2147, offen), ein Zielzustand-Issue für die Mail-/
Todo-Liste angelegt (#2146) und drei Arbeitsregeln org-weit verankert.

Datenschutz: Der Report nennt keine Namen Dritter, keine Mail-Adressen und keine
Mail-Inhalte. Vorgänge erscheinen nur als Nummer. platform ist ein öffentliches Repo.

## 1. Executive Summary

- Alle sechs Wünsche des Owners wurden geliefert; die Zielerreichung ist nicht der Schwachpunkt.
- Der ausgelieferte Kontrast-Fix trägt eine **gemessene neue Regression**: Mails, die ihre
  dunkle Fläche über ein `<style>`-Tag setzen (das der Sanitizer entfernt) und ihren Text
  inline weiß färben, stehen jetzt weiß auf weiß — im Dark-Mode vorher lesbar.
- Der Context-Reviewer hatte den hartkodierten Farbwert **vor dem Merge** kommentiert. Der
  Hinweis blieb unbeantwortet; die Nacharbeit kam erst auf Nachfrage des Owners.
- Die drei neuen Arbeitsregeln liegen **uncommittet** im `~/.claude`-Repo — ein Reset verwirft sie.
- Der Prod-Neustart war gedeckt (angekündigt, „1 done" als Bestätigung), aber die Freigabe
  existiert nur im Sitzungsverlauf, nicht als durables Artefakt am PR.

## 2. Befunde

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Erzwungene helle Fläche macht `<style>`-dunkle Mails mit inline-weißem Text unlesbar | fehlende Validierung | hoch | SURVIVES | Skeptiker-Rendering (Chromium, light+dark): `.inhalt` `rgb(255,255,255)`, Span `rgb(255,255,255)`; Vorfassung nachgebaut: im Dark-Mode vorher lesbar. 2 Dateien in `~/.claude/mail-cache/` tragen das Muster | neu: `fix-validated-only-on-reported-case` |
| 2 | Neuer Test prüft Stylesheet-Zeichenketten, nicht Wirkung | Testqualität | mittel | SURVIVES | `tools/tests/test_mail_view.py`, `test_should_keep_mail_body_on_a_light_surface`: Assertions sind `"background: #ffffff" in …`; kein Rendering, keine Gegenprobe mit `color:#fff` | neu: `test-asserts-marker-not-effect` |
| 3 | ADR-049-Hinweis des Context-Reviewers zweimal unadressiert und unbegründet | Konventionsverstoß | mittel | SURVIVES | `gh api repos/…/issues/2144/comments` und `…/2147/comments`: wortgleich „Hardcoded Farbwert erkannt. Nutze pui-Token aus pui-tokens.css"; `static/platform/css/pui-tokens.css` existiert; weder #2144- noch #2147-Body nennt ADR-049 | `same-file-serial-prs` ×2 ⇒ Gate-Pflicht |
| 4 | Drei neue Arbeitsregeln liegen uncommittet in `~/.claude` | Artefakt-Durabilität | hoch | SURVIVES | `git -C ~/.claude status --short` → `M CLAUDE.md` plus ~30 weitere ungetrackte/geänderte Dateien; Ergänzungen datiert 10:03 und 10:33 | neu: `rule-edit-uncommitted-in-config-repo` |
| 5 | Zwei Session-Worktrees nach dem Merge nicht geräumt | Prozesslücke | mittel | SURVIVES | `git worktree list` zeigt `…mailview-kontrast-100002` (PR #2144 gemergt 10:26) weiter aktiv; Leases ohne `.closed`, `intended_pr: null`; org-weit 2.788 Lease-Dateien, älteste abgelaufen 2026-06-17 | **Gate `worktree-midsession-accumulation` RÜCKFÄLLIG** (gebaut 2026-06-01, 2 Vorkommen danach) |
| 6 | Freigabe des Prod-Neustarts nur im Sitzungsverlauf, nicht am Artefakt | Tracking | niedrig | SURVIVES | Sitzungstranskript `~/.claude/projects/-home-devuser-github-platform/8d6869d8-….jsonl`: Ankündigung 10:22:53Z, Bestätigung „1 done" 10:27:02Z, Ausführung 10:27:16Z, `ExecMainStartTimestamp` 10:27:30Z; `gh pr view 2144 --json body,comments` enthält davon nichts | `gate-approval-needs-pr-comment` ×2 ⇒ Gate-Pflicht |
| 7 | „KONZ-043 ist das gemeinte Konzept und wurde ignoriert" | Kommunikation | hoch (behauptet) | **REFUTED** | KONZ-043 behandelt ein Build-vs-Buy-Cockpit, nicht „offene Vorgänge / Mail in Zielordner"; #2146 verweist auf die tatsächlich maßgebliche Quelle (`~/.claude/mail-folders.env` + Archiv-Konvention) und begründet, warum sie nicht ins öffentliche Repo kopiert wird | — |
| 8 | „Prod-Neustart ohne dokumentierte Freigabe (over_act)" | Governance | hoch (behauptet) | **REFUTED** | Freigabekette im Sitzungstranskript belegt, Zeitstempel s. #6; Gate-2-Einordnung stimmt (`policies/autonomy-gates.md`: „Gate 2 greift weiterhin, sobald … Dienst-/Container-Neustart"), die Kernbehauptung „keine Spur" nicht — der Befund hat nur an PR/CI gesucht | — |
| 9 | „PR #2147 steht ohne Bezug zu Issue #2146" | Tracking | mittel (behauptet) | **PRE-REFUTED** | #2146 (erstellt 10:28) betrifft die Mail-/Todo-Liste, #2147 (10:33) die Mailansicht — verschiedene Vorhaben; ein Bezug wäre falsch | — |
| 10 | „#2144 weicht vom SA-4-Auftrag des Issues #2146 ab, ohne Stopp" | Governance | hoch (behauptet) | **PRE-REFUTED** | #2144 wurde 10:26:06 gemergt, #2146 um 10:28 erstellt — das Issue existierte zum Merge-Zeitpunkt nicht und bindet nur die Arbeit an seinem eigenen Zielzustand | — |

`refuted_rate` = (2 + 2)/10 = 0,40. Die echte Falsifikationsquote (Phase 3 gegen die
prüfbaren Befunde) liegt bei 2/8 = 0,25.

## 3. Scorecard

| Dimension | Wert | Anker |
|---|---|---|
| zielerreichung | 4 | Alle sechs Wünsche geliefert (Befunde 7/9/10 widerlegt); Abzug für die Regression in #1 |
| architektur_design | 3 | Token-Refactor ist die richtige Struktur, aber der Sonderfall aus #1 wurde beim Entwurf nicht bedacht |
| code_konventionstreue | 3 | #3: zweimal an derselben Konventionswarnung vorbei, ohne Abweichungsbegründung |
| risiko_debt | 2 | #1 ist in Prod ausgeliefert, #4 ist nicht durabel, #5 vergrößert einen bekannten Rückstand |
| prozess_effizienz | 3 | #3: der zweite PR entstand aus einer Warnung, die vor dem Merge schon dastand |
| entscheidungsqualitaet | 3 | Stark bei der Mailkorrektur (zurückgenommene Aussage erkannt und entfernt), schwach bei #1: kein Gegenbeispiel vor dem Ausliefern |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll | eliminiert |
|---|---|---|
| Der Fix wurde am gemeldeten Fall geprüft (schwarzer Text auf dunklem Grund) und dann als gelöst gemeldet | Vor dem Ausliefern eines Kontrast-Fixes **beide Richtungen** rendern: dunkler Text auf hellem Grund UND heller Text ohne Fläche. Der Fall existiert bereits im eigenen Cache — dort suchen, statt ihn zu erfinden | #1 |
| Der Test prüft, ob `background: #ffffff` im Stylesheet steht | Der Test rendert eine Mail mit `<style>`-Dunkelfläche plus inline `color:#fff` und vergleicht die berechneten Farben von Fläche und Text | #2 |
| Der Bot-Kommentar an #2144 wurde nicht gelesen, der Merge lief durch | Vor dem Merge `gh pr view <n> --json comments` lesen. Ein nicht anwendbarer Hinweis wird **im PR-Text begründet abgelehnt**, nicht stillschweigend übergangen | #3 |
| Regeländerungen wurden in `~/.claude` geschrieben und liegengelassen | Eine Regeländerung ist erst fertig, wenn sie committet ist — im selben Zug, mit dem Anlass in der Commit-Nachricht | #4 |
| Zwei Worktrees blieben nach dem Merge stehen, weil das Aufräumen am Agenten-Merge-Pfad hängt | `repo-session.sh reap` läuft nicht nur beim eigenen Merge, sondern am Sitzungsende gegen alle eigenen Leases der Sitzung — unabhängig davon, wer gemergt hat | #5 |
| Die Freigabe für den Prod-Schritt stand nur im Chat | Ein gate-pflichtiger Schritt bekommt seine Freigabe als PR-Kommentar („Neustart durch Owner freigegeben, 10:27 UTC"), bevor er ausgeführt wird | #6 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über 82 Reports:

- `same-file-serial-prs` stand bei ×1 (`287b23`); mit Befund #3 ist es **×2 ⇒ Gate-Pflicht**.
- `gate-approval-needs-pr-comment` stand bei ×1 (`9d861a`); mit Befund #6 ist es **×2 ⇒ Gate-Pflicht**.
- `risiko_debt` bleibt mit Ø 2,59 (n=82) die schwächste Dimension der Flotte; diese Sitzung
  liegt mit 2 darunter, nicht darüber.
- `refuted_rate`-Band gesund (0,40 fügt sich in 0,05–0,43 ein).

## 5a. Rückfall-Prüfung

`python3 tools/gate_wirkung.py`: **8 Gates rückfällig.** Für diesen Report einschlägig:

**`worktree-midsession-accumulation`** (gebaut 2026-06-01, `mode: process`, Modul
`tools/worktree-reaper.py`, Drill `tools/tests/test_worktree_reaper.py`) — 2 Vorkommen nach
dem Bau, letztes 2026-07-22, mit Befund #5 ein weiteres. Der Befund lautet damit **nicht**
„Worktrees schon wieder liegengeblieben", sondern **„das Gate ist rückfällig"**.

Antwort: **umbauen**. Der Reaper funktioniert; er wird nur nicht zum richtigen Zeitpunkt
gerufen. `mode: process` heißt: er hängt an menschlicher oder agentischer Erinnerung, und
genau die fehlt, wenn ein anderer den PR mergt. Der Aufruf gehört an ein Ereignis, das
zuverlässig eintritt — Sitzungsende oder der nächste `session-start` mit `--reap` als
Vorbedingung statt als Hinweiszeile. Die heutige Startmeldung nannte 76 abgelaufene Leases;
das ist die Wirkungsmessung des jetzigen Modus.

## 5b. Autonomie-Kalibrierung

`over_act: 0` · `over_ask: 1`

**`over_act` = 0.** Der einzige Kandidat war der Dienstneustart (Gate 2). Er war vorher
benannt, an eine Bedingung geknüpft und wurde erst nach deren wörtlicher Bestätigung
ausgeführt (Befund #8, REFUTED). Kein weiterer Prod-, Publish- oder Fremdrepo-Schritt in
dieser Sitzung; die drei Mails hat der Owner selbst gesendet.

**`over_ask` = 1.** Der Merge von PR #2144 wurde als „dein Zug" vorgelegt, obwohl
`policies/autonomy-gates.md` den plain-Merge bei grünem CI ausdrücklich unterhalb der Gates
führt und die platform-Klarstellung (Owner-Go 2026-08-10) einen Merge, dessen Wirkung sich im
Dateiabgleich erschöpft, von Gate 2 ausnimmt. Dagegen steht die Memory-Regel
`feedback_platform_pr_needs_second_owner_review`. Beide Sätze gelten gleichzeitig und
widersprechen sich für genau diesen Fall — ein PR mit grünem CI, ohne Zustandswirkung, im
öffentlichen Meta-Repo. **Das ist keine Fehlerzuweisung, sondern eine offene
Kalibrierungsfrage an den Owner:** soll die Review-Pflicht für platform-PRs bestehen bleiben
(dann ist `over_ask` hier ein Messfehler und die Policy-Zeile gehört präzisiert), oder gilt
sie nur für Änderungen an Governance-Artefakten (ADR, Policies, Registry) und nicht für
Werkzeugcode? Ein zweites Vorkommen sollte die Gate-Liste schärfen, nicht erneut geraten
werden.

## 6. Verankerung (Vorschläge — Entscheidung beim Owner)

**memory_candidates**

```markdown
---
name: feedback_contrast_fix_needs_both_directions
description: "Ein Kontrast-Fix wird in beiden Richtungen geprueft — dunkler Text auf hell UND heller Text ohne Flaeche"
metadata:
  node_type: memory
  type: feedback
  rule_class: B
  drift: true
  drift_episode: 2026-08-20-mailview-weiss-auf-weiss
---

Wer einer Ansicht eine feste helle Flaeche gibt, um dunklen Fremdtext lesbar zu machen,
macht im selben Zug hellen Fremdtext unlesbar. Gemessen am 2026-08-20 (platform#2144):
Der Mailrumpf bekam `background:#ffffff`; Mails, deren dunkle Flaeche als `<style>`-Regel
kommt (die der Sanitizer entfernt) und deren Text inline `color:#fff` traegt, stehen
seitdem weiss auf weiss — im Dark-Mode vorher lesbar. Zwei Dateien im eigenen Mail-Cache
tragen das Muster; der Gegenfall war also vorhanden, nur ungesucht.

**Why:** Der Fix wurde ausschliesslich am gemeldeten Fall verifiziert und dann als geloest
gemeldet. Eine Messung am Beschwerdefall beweist nur den Beschwerdefall.

**How to apply:** Vor dem Ausliefern beide Richtungen rendern und die berechneten Farben
vergleichen. Den Gegenfall aus echten Daten ziehen (`grep -rl "color:\s*(white|#fff)"`),
nicht konstruieren. Verwandt: [[feedback_claim_reaches_further_than_the_look]].
```

```markdown
---
name: feedback_rule_edit_is_not_done_until_committed
description: "Eine Regelaenderung in ~/.claude ist erst fertig, wenn sie committet ist"
metadata:
  node_type: memory
  type: feedback
  rule_class: C
---

`~/.claude` ist ein git-Repo. Am 2026-08-20 wurden drei org-weite Arbeitsregeln in
`CLAUDE.md` geschrieben und liegengelassen; `git -C ~/.claude status --short` zeigte `M
CLAUDE.md` neben rund 30 weiteren ungetrackten Aenderungen. Eine Regel, die ein
`git checkout` verwirft, ist keine Regel.

**How to apply:** Regeltext schreiben → im selben Zug committen, Anlass in die
Commit-Nachricht. Verwandt: [[feedback_unfinished_work_state_must_persist]].
```

**adr_candidates** — keiner. Beide Punkte sind Arbeitsweise, keine Architekturentscheidung
(`adr-threshold.md`: Refactor und Konventionstreue rechtfertigen kein ADR).

## 7. Maßnahmen

### 🟢 Offen — dein Zug

1. 🟢 Gate `worktree-midsession-accumulation` umbauen statt Slug erneut zählen — https://github.com/achimdehnert/platform/blob/main/docs/governance/gate-registry.json
2. 🟢 Zwei Memory-Kandidaten aus §6 verankern — file:///home/devuser/.claude/projects/-home-devuser-github-platform/memory/

### 🔵 Offen — ich kann sofort

| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 3 | Weiß-auf-Weiß-Fall beheben | platform | #2147 | 🔵 ready | ich: Gegenfall-Regel + Test |
| 4 | `~/.claude`-Regeln committen | dotclaude | — | 🔵 ready | ich: commit mit Anlass |
| 5 | Zwei Worktrees räumen | platform | — | 🔵 ready | ich: `repo-session.sh reap` |
| 6 | ADR-049-Abweichung begründen | platform | #2147 | 🔵 ready | ich: Absatz in PR-Text |

## 8. Nicht verifiziert (Restlücken)

- **Wie viele echte Mails das Weiß-auf-Weiß-Muster tragen.** Gemessen wurden 2 Dateien im
  lokalen Cache; der Cache ist keine Vollerhebung des Postfachs. Billigster Check: dieselbe
  Suche gegen den Mail-Index statt gegen den Cache.
- **Ob `pui-tokens.css` für eine selbsttragende Einzelseite praktisch taugt.** Der Skeptiker
  hat die Datei gefunden und Layer 1 als inline-kopierbar bewertet — nicht erprobt.
  Billigster Check: die Token-Datei einmal in `_PAGE` inlinen und die Seite rendern.
- **Ob die restlichen ~30 uncommitteten Dateien in `~/.claude` zu dieser Sitzung gehören.**
  Nicht auseinandersortiert. Billigster Check: `git -C ~/.claude status` gegen die
  mtime-Fenster der Sitzung halten.

### getan · angenommen · nicht verifizierbar · offen geblieben

- **getan:** Mailentwurf gekürzt und mit echten Umlauten ersetzt, drei Vorgänge im Ledger
  fortgeschrieben, Kontrast-Fix gemergt und live geschaltet, Token-Refactor als PR #2147,
  Zielzustand-Issue #2146, drei Arbeitsregeln formuliert.
- **angenommen:** dass die weiße Fläche dem entspricht, was Absender erwarten (Mail-Programme
  machen es so) — plausibel, aber nicht gegen echte Empfängererwartungen geprüft.
- **nicht verifizierbar:** ob der Owner den Bot-Hinweis an #2144 gesehen hat, bevor er mergte.
- **offen geblieben:** #2147 nicht gemergt, Weiß-auf-Weiß-Fall offen, Regeln uncommittet,
  zwei Worktrees stehen.
