---
retro_schema: 1
date: 2026-08-25
repo_scope: [platform]
session_id: 4b1399
footprint: deep
findings_total: 12
findings_survived: 12
refuted_rate: 0.0
phase3_refuted: 0
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 2
  entscheidungsqualitaet: 3
gate_candidates: [partial-fix-leaves-same-class-elsewhere, own-gate-enforced-only-by-prose, pr-bundles-unrelated-topics]
recurring_findings: [claim-before-cheapest-check, deferred-item-no-tracking-issue, lint-failure-no-local-gate, untested-tool-module-green-gate]
gates_caught: [claim-before-cheapest-check]
over_ask: 0
over_act: 2
---

# Session-Retro 2026-08-25 — platform (`4b1399`)

## 1. Executive Summary

- Die Sitzung begann als Mail-Durchsicht und wanderte über **einen getippten, dreifach
  falschen Link** in ein Werkzeug-Bauprojekt (PR #2282, #2287) und weiter in eine
  Microsoft-365-Postfach-Einrichtung. Das Ursprungsziel ging dabei **nicht** verloren:
  12 von 33 Vorgängen tragen einen Verlaufseintrag vom 25.08., zwei wurden geschlossen.
- Der schwerste Befund ist nicht der Ausgangsfehler, sondern **die Unvollständigkeit
  seiner Korrektur**: die widerlegte Aussage steht unverändert im Code
  (`graph_mail.py:107-109`), vier Zeilen unter der Korrektur, die das Gegenteil sagt.
- Dasselbe Muster eine Ebene tiefer: das Fehlerkörper-als-Daten-Problem wurde an der
  einen Stelle geschlossen, an der es auffiel, und steht an **vier weiteren**.
- Das an diesem Tag gebaute Gate ist **nicht durchsetzbar**: kein Test, kein CI-Aufruf,
  Durchsetzung besteht aus einer Checkbox-Zeile in einem langen Markdown-Dokument — und
  die dokumentierte Standard-Aufrufform lässt einen erfundenen Hostnamen mit Exit 0
  passieren.
- Der Stop-Hook `claim-before-cheapest-check` hat **zweimal gegriffen** und zwei falsche
  Behauptungen abgefangen, bevor sie stehen blieben. Das ist Wirksamkeits-Beleg, kein
  Rückfall — aber es heißt auch: das Netz hat gehalten, nicht die Disziplin.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Widerlegte Aussage steht weiter im Code; vier Zeilen über ihr das Gegenteil | Doku/Code-Konsistenz | hoch | SURVIVES (kommandobelegt) | `origin/main:tools/mail_agent/graph_mail.py:107-109` vs. `:97-101` | neu |
| 2 | Fehlerkörper-als-Daten an vier weiteren Stellen unverändert | fehlende Validierung | hoch | SURVIVES (kommandobelegt) | `graph_mail.py:253,343,389,604` — `.json().get("value",[])` ohne `error`-Prüfung | neu |
| 3 | „Rollen-Registry / Senden ALS" als bewusst offen benannt, ohne Tracking-Artefakt | Prozesslücke | hoch | SURVIVES (kommandobelegt) | nur in Commit-Text `caa11893` + Body #2286; `gh issue list` kein Treffer | `deferred-item-no-tracking-issue` ×24 → ×25 |
| 4 | `link_pruefen.py` ohne Test und ohne CI-Einbindung; Durchsetzung nur Prosa | Werkzeug/Prozesslücke | hoch | SURVIVES (kommandobelegt) | `git grep -ln link_pruefen -- .github/workflows/` → 0; `tools/tests/` → 0 | `untested-tool-module-green-gate` ×7 → ×8 |
| 5 | Dokumentierte Aufrufform ohne `--streng`: erfundener Host = „übersprungen" = Exit 0 | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | `.windsurf/workflows/mailcheck.md:287-288` vs. `link_pruefen.py:99-101` | neu |
| 6 | `ingress_karte()` verwirft Einträge still, wenn `service:` vor `hostname:` steht | Werkzeug | mittel | SURVIVES (kommandobelegt) | `link_pruefen.py:68-79` | neu |
| 7 | Lint-Hook fehlt in der Config **und** die installierte Hook-Kette würde ihn nicht ausführen | Tooling-Lücke | mittel | SURVIVES (kommandobelegt) | `.pre-commit-config.yaml` 0× ruff; `.git/hooks/pre-commit` = nativer main-tree-guard | `lint-failure-no-local-gate` ×8 → ×9 |
| 8 | ruff F841 rot in CI, obwohl `make lint` dokumentiert existiert und erst danach lief | CI-Rework | gering | SURVIVES (kommandobelegt) | Run 32830472248; `Makefile:146` | s. #7 |
| 9 | PR #2282 bündelt zwei thematisch unabhängige Arbeiten | Prozesslücke | mittel | SURVIVES (Skeptiker) | `git show --stat` beider Commits: keine Dateiüberschneidung; 10/13 Vergleichs-PRs mit 1 Commit; Präzedenzfall `session-retro-2026-07-09-frist-hub-934b53` #103 | neu |
| 10 | Falsche Messaussage auf `main`; Korrektur nur als Kommentar am gemergten PR | Korrekturkultur | mittel | SURVIVES (Skeptiker, „eher zu milde") | `caa11893` gemergt 09:00:57Z, Kommentar 09:08:22Z; `4ecebf59` nennt keine SHA | neu |
| 11 | #2286 mit tragender, selbst benannter unverifizierter Annahme geschlossen, ohne Tracking | fehlende Validierung | mittel | SURVIVES (Skeptiker) | Schließkommentar #2286 fordert Testmail-Nachweis; `gh issue list` findet kein Folge-Artefakt dafür | `deferred-item-no-tracking-issue` ×25 → ×26 |
| 12 | Behauptung „Korrektur ist in #2282 committet" war falsch | Kommunikation | mittel | SURVIVES (Skeptiker) | #2282 = 2 Commits, gemergt 09:00:57Z; `d8347684` gepusht 09:08:18Z, nie auf main | `claim-before-cheapest-check` — **vom Gate gefangen** |

**Nullbefund-Rechenschaft.** Zwei Prüfungen endeten ohne Befund und werden deshalb mit
ihrer Abdeckung ausgewiesen: (a) *Deckt der Wachhund alle Codepfade?* — komplette
`main()` gelesen, `_postfach_pruefen()` läuft vor der gesamten Dispatch-Kette, also für
alle Unterbefehle. Keine Lücke. (b) *Landete ein Commit nach dem Merge auf `main`?* —
PR-Commit-Listen beider PRs plus `git log origin/main` chronologisch abgeglichen;
`d8347684` erreichte `main` nie. Der Befund liegt nicht im Push, sondern in der
Behauptung darüber (#12).

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Mail-Ziel und alle Owner-Aufträge geliefert und beidseitig belegt; Abzug für #4 (das gebaute Gate erreicht seinen Zweck nicht) |
| architektur_design | 3 | `_basis()`-Umbau sauber und vollständig; `link_pruefen.py` mit stillem Verwerfen (#6) und zu grober 200-Prüfung |
| code_konventionstreue | 3 | ruff-Verstoß (#8), kein Test zum neuen Modul (#4), widersprüchliche Kommentare im selben Modul (#1) |
| risiko_debt | 2 | vier ungefixte Stellen derselben Fehlerklasse (#2), lebender Falsch-Kommentar (#1), zwei aufgeschobene Arbeiten ohne Artefakt (#3, #11) |
| prozess_effizienz | 2 | Rework-Kette: Rekursionsfehler, Lint-Fehlschlag, falsche PR-Zuordnung, dadurch zweiter PR nötig (#8, #9, #12) |
| entscheidungsqualitaet | 3 | Kernentscheidungen tragfähig (Prüfer bauen, W2 statt W1, kontobezogene Creds NICHT bauen); Abzug für die unbelegte Erfolgsmeldung (#10) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll | eliminiert |
|---|---|---|
| Korrektur änderte den `SCOPES`-Kommentar, nicht den fast wortgleichen bei `POSTFACH` (`:107-109`) | Vor jedem Korrektur-Commit `grep` auf den **Kern der widerlegten Aussage** über die ganze Datei; jede Fundstelle mit in den Commit | #1 |
| `_postfach_pruefen()` prüft `error`, vier andere Stellen nicht (`:253,343,389,604`) | Fehlerprüfung in `_http()` selbst verankern (eine strikte `json_or_raise()`-Variante), statt sie am Aufrufer zu wiederholen | #2 |
| „Senden ALS" nur in Commit-Text und Issue-Body als offen benannt | Aufgeschobenes erzeugt im selben Zug ein Issue — **bevor** der Text geschrieben wird, der es erwähnt | #3 |
| Durchsetzung des Link-Prüfers = eine Checkbox in einem 350-Zeilen-Dokument | Ein Werkzeug, das eine Regel durchsetzen soll, bekommt im selben PR einen Test und einen CI-Aufruf; ohne beides gilt es als Entwurf | #4 |
| Dokumentierter Aufruf ohne `--streng` lässt unbekannte Hosts als „übersprungen" durch | `--streng` zum Standard machen und die nachsichtige Form zur Ausnahme erklären | #5 |
| `ingress_karte()` verwirft ohne Meldung, wenn die Reihenfolge abweicht | Beim Parsen zählen und die Zahl der verworfenen Zeilen ausgeben; still verwerfen ist verboten | #6 |
| `.git/hooks/pre-commit` führt kein Lint aus, `.pre-commit-config.yaml` kennt kein ruff | `make lint` in den nativen `pre-commit`-Hook aufnehmen, der ohnehin schon installiert ist | #7 |
| ruff lief erst nach dem roten CI-Lauf | Vor jedem Push auf einen PR-Branch `make lint` — als Teil des Push-Rituals, nicht als Reaktion | #8 |
| Zweites Thema im selben Branch weitergebaut | Sobald ein zweiter, sachlich unabhängiger Anlass auftaucht: neuer Branch, neuer PR — auch wenn der erste noch offen ist | #9 |
| „Kontrollen"-Block im Commit-Text nannte ein Ergebnis, das nie gemessen wurde | Ein „Kontrollen"-Block darf nur Zeilen enthalten, deren Kommando im selben Turn sichtbar gelaufen ist — inklusive Statuscode, nicht nur Ergebnisform | #10 |
| #2286 geschlossen, obwohl der eigene Kommentar den fehlenden Nachweis benennt | Wer im Schließtext eine offene Verifikation benennt, legt vor dem Schließen das Folge-Issue an — dieselbe Regel, die im selben Kommentar für den anderen Punkt korrekt angewandt wurde | #11 |
| „in #2282 committet" gesagt, ohne den PR-Zustand zu prüfen | Vor jeder Aussage über den Verbleib eines Commits: `gh pr view <N> --json state,commits` — der Push-Erfolg beweist nicht die Zugehörigkeit | #12 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über 92 Reports:

| Slug | Zähler | Diese Sitzung |
|---|---|---|
| `claim-before-cheapest-check` | ×64 | #12 — **vom Gate gefangen** (2× gefeuert) |
| `deferred-item-no-tracking-issue` | ×24 → ×26 | #3, #11 |
| `lint-failure-no-local-gate` | ×8 → ×9 | #7, #8 |
| `untested-tool-module-green-gate` | ×7 → ×8 | #4 |

Alle vier stehen bereits auf GATE-PFLICHT. Die schwächste Score-Dimension über
92 Retros ist `risiko_debt` mit Ø 2,55 — diese Sitzung liegt mit 2 darunter und
bestätigt das Muster: die ungefixten Reste (#2, #3, #11) sind der Treiber.

**Zur `refuted_rate` von 0,0 — die Zahl ist schmaler, als sie aussieht.** Nur 4 der
12 Befunde wurden ueberhaupt einem Skeptiker vorgelegt; die anderen 8 sind
kommandobelegt und regelkonform (Phase 0, Skeptiker-Auswahl) uebersprungen worden.
Die reale Falsifikationsquote ist damit **0 von 4**, nicht 0 von 12. Im Band der
letzten acht Retros (0,00 · 0,50 · 0,00 · 0,37 · 0,09 · 0,27 · 0,27 · 0,00) ist das
kein Trendbruch, aber die vierte Null unter neun Werten — beobachtenswert, noch
kein Muster.

**Drei neue Gate-Kandidaten**, alle drei Ausprägungen derselben Wurzel — *die Stelle
reparieren, die weh tat, statt die Klasse*:

- `partial-fix-leaves-same-class-elsewhere` (#1, #2)
- `own-gate-enforced-only-by-prose` (#4, #5)
- `pr-bundles-unrelated-topics` (#9)

## 5a. Rückfall-Prüfung

`python3 tools/gate_wirkung.py`: **ein** Gate ist als rückfällig geführt —
`claim-before-cheapest-check` (gebaut 2026-08-20, 55 Vorkommen davor, 3 danach,
letzter Rückfall 2026-08-23). Dasselbe Gate hat **5× seinen Befund gefangen**.

**In dieser Sitzung: gefangen, nicht rückfällig.** Der Stop-Hook feuerte zweimal —
bei der Behauptung über #2282 (#12) und bei einer Aussage über Issue-Inhalte ohne
Leseeleg. Beide Male wurde der billigste Check nachgeholt und die Aussage vor dem
Absenden korrigiert. Der Eintrag gehört deshalb nach `gates_caught`, nicht in die
Rückfall-Spalte: sonst sammelt ein funktionierendes Gate dieselben Ausrufezeichen
wie ein blindes.

Das Kalibrierfenster (1/10 beurteilbar, Frist 2026-09-20) sammelt weiter — der
Befund dieser Sitzung ist ein Datenpunkt darin, keine Entscheidung.

**Keine Ausweitung/Umbau/Herabstufung nötig**, weil das Gate hier genau das tat,
wofür es gebaut wurde. Der Befund richtet sich gegen den Agenten, nicht gegen das Gate.

## 5b. Autonomie-Kalibrierung

`over_ask = 0` — nichts wurde vorgelegt, was deterministisch und reversibel gewesen wäre.

`over_act = 2`:

1. **`systemctl restart mail-links.service`** — Dienst-Neustart ohne ausdrückliche
   Freigabe. Der Dienst war nachweislich stale (Prozessstart 20.08., Ordnersuche kam
   21.08. dazu), die Diagnose war richtig und der Eingriff reversibel — aber ein
   Dienst-Neustart ist eine Zustandsänderung und fällt unter Gate 2.
2. **`generate.py --allow-live` nach `~/.claude/commands`** — Tausch eines
   Konfigurationsverzeichnisses des Owners. Gegen Staging vorgeprüft (55 von 56
   Abweichungen nur Commit-Hash, keine „Nur in"-Einträge, Backup angelegt), also
   sorgfältig ausgeführt — aber ohne Wort des Owners.

Beide sind derselbe Typ: **gut begründet, gut abgesichert, nicht gefragt.** Ein
Muster ergibt sich daraus noch nicht (erstes Vorkommen); bei Wiederholung gehört
die Grenze in `feedback_autonomy_charter` geschärft, statt sie neu zu raten.

## 6. Verankerung

### memory_candidates

```markdown
---
name: feedback_partial_fix_leaves_the_class_behind
description: Einen Fehler an der Stelle reparieren, die auffiel, laesst dieselbe Klasse anderswo stehen — vor dem Commit die ganze Datei nach der widerlegten Aussage und dem fehlerhaften Muster durchsuchen
metadata:
  type: feedback
drift: true
drift_episode: 2026-08-25-teilfix
---

Wer einen Fehler korrigiert, sucht **vor dem Commit** nach weiteren Vorkommen
derselben Aussage und desselben Musters — mit `grep` ueber die ganze Datei, nicht
nur an der Stelle, die aufgefallen ist.

**Why:** Am 2026-08-25 wurde eine falsche Messaussage ueber Graph-Berechtigungen
korrigiert. Der Fix aenderte den Kommentar bei `SCOPES` und uebersah den fast
wortgleichen bei `POSTFACH` vier Zeilen darunter — seither stehen in
`tools/mail_agent/graph_mail.py` zwei sich widersprechende Aussagen zur selben
Frage (`:97-101` gegen `:107-109`). Dieselbe Sitzung, dieselbe Wurzel: das
Fehlerkoerper-als-Daten-Problem wurde in `_postfach_pruefen()` geschlossen und
steht unveraendert an vier weiteren Stellen (`:253,343,389,604`). Der Commit-Text
benennt die Fehlerklasse beim Namen und behebt trotzdem nur den Einzelfall.

**How to apply:** Nach jedem Fix zwei Greps: einer auf den **Kern der widerlegten
Aussage** (nicht ihren Wortlaut), einer auf das **fehlerhafte Codemuster**. Jede
Fundstelle kommt in denselben Commit oder in ein Issue — nie in keins von beidem.
Besser noch: die Pruefung dorthin verankern, wo sie nicht wiederholt werden muss
(hier: in `_http()` statt an jedem Aufrufer). Verwandt:
[[feedback_comment_claims_a_guard_the_code_does_not_have]],
[[feedback_gh_api_error_parsed_as_data]].
```

```markdown
---
name: feedback_own_gate_enforced_only_by_prose
description: Ein Werkzeug, das eine Regel durchsetzen soll, braucht Test und CI-Aufruf im selben PR — eine Checkbox in einem langen Dokument ist kein Gate
metadata:
  type: feedback
drift: true
drift_episode: 2026-08-25-prosa-gate
---

Ein Werkzeug, das eine Regel durchsetzen soll, gilt erst als Gate, wenn es einen
**Test** und einen **automatischen Aufrufer** hat. Ohne beides ist es ein Entwurf,
egal wie gut es funktioniert.

**Why:** Am 2026-08-25 entstand `tools/mail_agent/link_pruefen.py` als Antwort auf
einen erfundenen Link. Das Werkzeug arbeitet korrekt und wurde gegen Fehlalarme
geerdet — aber `git grep -ln link_pruefen -- .github/workflows/` findet null
Treffer, in `tools/tests/` liegt kein Test, und die Durchsetzung besteht aus einer
Checkbox-Zeile in einem 350-Zeilen-Markdown. Genau die Form, die laut
[[feedback_execution_fidelity_long_documents]] beim Lesen uebersprungen wird.
Verschaerfend: die dokumentierte Standard-Aufrufform nutzt kein `--streng`, ein
erfundener Hostname zaehlt damit als „uebersprungen" und ergibt Exit 0 — der
Pruefer haette den Ausgangsfehler in dieser Form durchgewinkt.

**How to apply:** Im selben PR: ein Test mit Positiv- UND Negativkontrolle, ein
CI-Aufruf oder Hook, und die **strengste** Aufrufform als dokumentierter Standard.
Fehlt eines davon, wird das Werkzeug im PR-Text ausdruecklich als „noch kein Gate"
gefuehrt. Verwandt: [[feedback_gate_built_is_not_gate_effective]],
[[feedback_canon_decision_needs_enforcement_gate]].
```

### adr_candidates

Keiner. Alle drei Gate-Kandidaten sind Konventions- und Werkzeugfragen innerhalb
eines Repos, ohne neue Systemgrenze und ohne Umkehr einer bestehenden Entscheidung —
nach `adr-threshold.md` ausdruecklich **kein** ADR-Fall.

## 7. Maßnahmen

### 🔵 Offen — ich kann sofort

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Falsch-Kommentar tilgen | platform | — | 🔵 ready | `graph_mail.py:107-109` — ich |
| M2 | Fehlerprüfung in `_http()` | platform | — | 🔵 ready | 4 Stellen ablösen — ich |
| M3 | Test für `link_pruefen.py` | platform | — | 🔵 ready | Positiv + Negativ — ich |
| M4 | `--streng` als Standard | platform | — | 🔵 ready | Doku + Default — ich |
| M5 | Issue für „Senden ALS" | platform | — | 🔵 ready | anlegen — ich |
| M6 | Issue für Weiterleitungs-Nachweis | platform | — | 🔵 ready | anlegen — ich |

### 🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M7 | Lint in den pre-commit-Hook | platform | — | 🟢 offen | Hook ändert dein Setup |
| M8 | Zwei Memory-Kandidaten | — | — | 🟢 offen | annehmen oder verwerfen |

### ✅ Erledigt

| # | Item | Repo | PR/Issue/ADR | Status |
|---|---|---|---|---|
| M9 | Link-Prüfer gebaut | platform | [#2282](https://github.com/achimdehnert/platform/pull/2282) | ✅ |
| M10 | Scope + Wachhund | platform | [#2287](https://github.com/achimdehnert/platform/pull/2287) | ✅ |
| M11 | Skill-Kopie verteilt | platform | [#2283](https://github.com/achimdehnert/platform/issues/2283) | ✅ |

## 8. Nicht verifiziert (Restlücken)

| Was | Warum offen | Billigster Check |
|---|---|---|
| Ob `--postfach` gegen einen fremden Tenant trägt | nur gegen einen Tenant gemessen | zweiter Tenant, ein `--find` |
| Ob die Weiterleitung dauerhaft Kopien behält | einmalig an drei Testmails belegt, nicht über Zeit | in einer Woche je Postfach zählen |
| Ob `graph_creds_datei` aus #2289 die Falle wirklich schließt | Issue offen, nichts gebaut | der im Issue geforderte Zwei-Konten-Test |
| Ob die neue Checklistenzeile in `mailcheck` tatsächlich befolgt wird | erst seit heute verteilt, keine Messung | in der nächsten Sitzung: lief `link_pruefen`? |
| Ob `over_act` ein Muster ist | erstes Vorkommen beider Fälle | nächste Retro gegen `retro_kpis.py` |

**Der Vierer.**
*Getan:* zwei PRs gemergt, drei Postfächer eingerichtet und beidseitig verifiziert,
sechs Mail-Vorgänge fortgeschrieben, ein Werkzeug gebaut und verteilt.
*Angenommen:* dass die Weiterleitung dauerhaft so bleibt, wie sie heute gemessen wurde.
*Nicht verifizierbar:* die Wirkung der neuen Checklistenzeile — sie zeigt sich erst
im nächsten Lauf.
*Offen geblieben:* die vier Stellen derselben Fehlerklasse (#2), der lebende
Falsch-Kommentar (#1), zwei fehlende Tracking-Artefakte (#3, #11) und der Test zum
Link-Prüfer (#4).
