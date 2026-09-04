---
retro_schema: 1
date: 2026-07-27
repo_scope: [platform, risk-hub]
session_id: 0c98c5
footprint: deep
findings_total: 16
findings_survived: 14
refuted_rate: 0.13
phase3_refuted: 2
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates:
  - kill-gate-status-not-reconciled-after-contrary-evidence
  - unverifiable-kill-criterion-manual-only
  - destructive-prefix-match-without-separator
  - local-test-gate-narrower-than-ci
  - claim-before-cheapest-check
  - deferred-item-no-tracking-issue
recurring_findings:
  - claim-before-cheapest-check
  - deferred-item-no-tracking-issue
  - local-test-gate-narrower-than-ci
  - always-instruction-without-enforcement
---

# Session-Retro 2026-07-27 — platform + risk-hub (`0c98c5`)

## 1. Executive Summary

- Die Session lieferte, was sie sollte: KONZ-035 angenommen und gemergt, sieben von zehn
  Empfehlungen umgesetzt, ein Referenzpostfach gebaut, ein CI-Gate-Rätsel gelöst und der
  Vertragspartner-D-Sachverhalt vollständig beantwortet. Zielerreichung ist nicht das Problem.
- **Das Problem ist die Beweisführung über die eigene Arbeit.** Vier der vierzehn
  überlebenden Befunde sagen dasselbe: eine Statuszeile, ein Kill-Gate-Häkchen oder ein
  PR-Satz behauptete mehr, als das Artefakt hergibt.
- **Der schärfste Befund trifft das Konzept selbst.** Der erste echte Lauf deckte vier
  stille Fehler in genau den Mechanismen auf, die §13 als „erfüllt" führte — und dieses
  Ereignis wurde nie gegen das eigene Kill-Gate KG-PROCESS bewertet. Das Konzept schreibt
  vor, was bei einem produktiven Ausweis mit unbekannten Teilfehlern zu tun ist, und der
  erste solche Fall lief daran vorbei.
- **Ein Fehler war destruktiv:** Der Aufbau des Referenzpostfachs löschte per
  Zeichenketten-Präfix statt per Namensraum-Grenze. Ein fremder Ordner `INBOX.REFERAT.*`
  wäre mitgelöscht worden. Gefunden vom Prüfer, behoben in derselben Session.
- Die Falsifikation hat gearbeitet: zwei Befunde sind widerlegt, einer davon war meine
  eigene Behauptung, ein PR sei nach dem Ursachen-Fix nicht neu gebaut worden.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Der erste echte Lauf deckte vier stille Fehler in Mechanismen auf, die §13 als „erfüllt"/„teilweise" führte — nie gegen KG-PROCESS bewertet, K-Tabelle nicht korrigiert | fehlende Validierung | kritisch | SURVIVES | `KONZ-platform-035.md` §13 K2/K3/K4/K10 vs. PR platform#1494; `gh search prs "KG-PROCESS"` = 0 Treffer | neu |
| 2 | K5 („KG-RECALL erfüllt, 10/10, 0 False Positives") ist Prosa ohne Artefakt — kein CI-Log, kein Kommentar, kein Issue | fehlende Validierung | hoch | SURVIVES | `KONZ-platform-035.md` §13 K5; `test_referenzpostfach.py` Docstring: „läuft deshalb nicht in der CI" | `claim-before-cheapest-check` |
| 3 | Fleet-Wirkung auf neun weitere Repos im PR-Text benannt, kein Tracking-Artefakt angelegt | Prozesslücke | hoch | SURVIVES | risk-hub#460 Body; breite `gh issue list --state all`-Suche in beiden Repos = 0 Treffer | `deferred-item-no-tracking-issue` |
| 4 | Erste Diagnose in risk-hub#459 war im Hauptbefund falsch (Branch-Alter statt Paketversion); beide Versionen existierten Stunden vor der Diagnose | Fehlattribution | hoch | SURVIVES | Issue-Body 15:17Z vs. Korrektur 16:35Z; PyPI 1.32.5 06:24Z, 1.32.6 08:23Z | `claim-before-cheapest-check` |
| 5 | PR platform#1494 behauptete „869 Tests grün", während der CI-Lauf auf demselben Commit rot war | Kommunikation | hoch | SURVIVES | #1494 Body 18:45:18Z vs. Lauf 30295192917 (FAILURE); Korrektur-Kommentar 21:36Z | `claim-before-cheapest-check` |
| 6 | Der Aufbau des Referenzpostfachs löschte per `startswith("INBOX.REF")` — trifft auch `INBOX.REFERAT.Wichtig` | Werkzeug | hoch | SURVIVES | `referenzpostfach.py` Löschschleife (vor Fix); Gegenprobe: 5 von 5 Fremdnamen erfüllten den Präfix | neu |
| 7 | Neuer Test las das echte Home-Verzeichnis → lokal grün, in der CI rot; zweiter neuer Test lief in der CI inhaltsleer durch | Werkzeug | hoch | SURVIVES | Lauf 30295192917: `assert []`; Gegenprobe mit leerem `HOME` | `local-test-gate-narrower-than-ci` |
| 8 | ADR-284 §2 stellt verbindliche Pflichten auf, die nirgends technisch durchgesetzt werden (`--anlass` optional, keine Wiederholungs-Erkennung) | Policy-Code-Lücke | mittel | SURVIVES | `vorgang.py`: `--anlass default=""`; `anlass` kommt in `vollstaendigkeitsaussage_zulaessig()` nicht vor | `always-instruction-without-enforcement` |
| 9 | KONZ-035 nennt einen Testpfad `tests/mail_agent/test_deckungsausweis_recall.py`, der nicht existiert; der reale Recall-Lauf ist in keinem Workflow verankert | fehlende Validierung | mittel | SURVIVES | `git ls-tree -r origin/main` = leer; kein Workflow referenziert `referenzpostfach` | neu |
| 10 | PR platform#1492: Titel nennt zwei Empfehlungen, geliefert werden sieben in 1298 Zeilen; Bot meldet Regelverstoß G-004 | Prozesslücke | mittel | SURVIVES | #1492 Titel vs. `additions+deletions=1298`; Guardian-Kommentar „G-004" | neu |
| 11 | risk-hub#458: PR-Text sagt „`make lint` grün", der Required-Check ist rot — das lokale Target ist schmaler als der CI-Schritt | Werkzeug | mittel | SURVIVES | `Makefile`: `lint: ruff check src/`; CI zusätzlich `ruff format --check .`; Job 90049708078 | `local-test-gate-narrower-than-ci` |
| 12 | Breiter `except Exception` in der Ordner-Schleife zählt Programmierfehler als „unlesbaren Ordner" | Fehlerbehandlung | mittel | SURVIVES | `vorgang.py` `cmd_topic`; mildernd: `ordner_fehlgeschlagen` sperrt die Vollständigkeitsaussage trotzdem | neu |
| 13 | `erzeuger` fällt per Default auf „maschinell" — die R-5-Sperre greift nur, wenn ein Aufrufer sie aktiv setzt (fail-open) | verfrühte Festlegung | mittel | SURVIVES | `deckungsausweis.py`: `erzeuger: str = "maschinell"`; `cmd_topic` übergibt das Feld nicht | neu |
| 14 | Nacharbeit am eigenen Tagescode: die Kette #1488–#1492 wurde gemergt und am selben Abend durch #1494 in denselben drei Dateien repariert | Verifikationslücke | mittel | SURVIVES | Merge-Zeiten 13:45–17:37Z vs. #1494 18:45Z; identische Dateien | neu |
| 15 | Behauptung: risk-hub hat dieselbe Fehlerklasse in weiteren ungepinnten CI-Installationen | — | — | **REFUTED** | Ungepinnte Installationen existieren, implementieren aber kein Gate „eingecheckte Ausgabe gegen Neuerzeugung" — andere Fehlerklasse | — |
| 16 | Behauptung: risk-hub#458 wurde nach dem Ursachen-Fix #460 nicht neu gebaut | — | — | **REFUTED** | Merge-Commit 17:06:25Z liegt nach #460 (16:48:49Z); Klickdummy-Check dort grün — Rot hat eine andere Ursache | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Konzept angenommen, 7 von 10 Empfehlungen umgesetzt, Sachverhalt beantwortet, drei CI-Blockaden gelöst. Abzug: Befund 1 und 2 — Statuszeilen behaupten mehr als belegt. |
| architektur_design | 4 | Trennung reiner Logik von IMAP, versioniertes Objekt vor Text, Pflicht einmal im ADR statt in drei Skills. Abzug: Befunde 8, 9, 13 — Regeln ohne Durchsetzung, Default in die unsichere Richtung. |
| code_konventionstreue | 3 | Worktree-Konvention, Testbenennung, deutsche Kommentare eingehalten. Abzug: Befunde 10 (PR-Größe und Titel-Scope), 6 (destruktiver Präfix), 7 (umgebungsabhängige Tests). |
| risiko_debt | 2 | Befund 3 (Fleet-Wirkung ungetrackt, Verstoß gegen die eigene Hausregel), 2 und 9 (Kill-Kriterium ohne Nachweis und ohne Gate), 6 (destruktiver Pfad ausgeliefert). Das ist die schwächste Dimension — auch im Längsschnitt über 54 Retros (Ø 2,61). |
| prozess_effizienz | 3 | Befund 14 (Nacharbeit am Tagescode), 4 (publizierte Fehldiagnose), 7 und 11 (zwei rote Läufe durch lokal-vs-CI-Lücke). Mildernd: alles in derselben Session erkannt und behoben. |
| entscheidungsqualitaet | 3 | Gute Entscheidungen: Struktur-statt-Inhalt beim Referenzpostfach, exakter Pin statt paths-Filter, Amendment statt neuem ADR. Abzug: Befunde 4 und 1 — zwei Male wurde eine Diagnose bzw. ein Status vor dem billigsten Check festgeschrieben. |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| §13-Tabelle blieb auf „erfüllt", nachdem der erste echte Lauf vier Fehler in genau diesen Mechanismen zeigte | Ein Fix-PR, der einen Mechanismus repariert, den die K-Tabelle als erfüllt führt, ändert im selben PR die Tabellenzeile — oder begründet im PR-Text, warum nicht | #1 |
| K5 als „erfüllt" auf Basis eines Terminal-Laufs, den niemand nachvollziehen kann | Ein Kill-Kriterium wird erst „erfüllt", wenn sein Nachweis ein Artefakt hat: Lauf-Ausgabe als PR-Kommentar anhängen, solange kein CI-Job existiert | #2 |
| „Nicht Teil dieses PRs: betrifft 10 Repos" stand nur im PR-Text | Wer im PR-Text eine Restarbeit benennt, legt im selben Zug ein Issue an und verlinkt es — der Satz allein ist kein Tracking | #3 |
| Diagnose „Branch-Alter" veröffentlicht, bevor die Paketversionen verglichen waren | Vor einer publizierten Ursachen-Aussage die eine Gegenprobe fahren, die sie widerlegen würde — hier: gleicher Commit, zwei Versionen | #4 |
| „869 Tests grün" in den PR-Text geschrieben, bevor die CI gelaufen war | Test-Zahlen im PR-Text erst nach dem CI-Lauf setzen, oder als „lokal: N" kennzeichnen | #5 |
| Löschschleife filterte per `startswith(WURZEL)` | Jeder löschende Präfix-Vergleich endet auf einem Trenner (`== W or startswith(W + sep)`) und wird mit mindestens einem Fremdnamen-Gegenbeispiel getestet | #6 |
| Test las `Path.home()` und war deshalb maschinenabhängig | Ein Test, der Konfiguration liest, bekommt sie per `tmp_path` injiziert; Gegenprobe mit leerem `HOME` vor dem Push | #7 |
| ADR-Amendment formuliert „unzulässig", ohne dass etwas es verhindert | Eine ADR-Pflicht bekommt im selben PR entweder einen Exit-Code oder einen ausdrücklichen Satz, dass sie vorerst Review-Gate bleibt | #8 |
| KONZ nennt einen Testpfad, den niemand angelegt hat | Ein im Konzept genannter Dateipfad wird vor dem Merge einmal gegen das Repo geprüft | #9 |
| PR-Titel nannte zwei Empfehlungen, geliefert wurden sieben | Wächst ein PR über den Titel hinaus, wird der Titel vor dem Merge nachgezogen — die Größenwarnung des Bots ist der Auslöser dafür | #10 |
| „`make lint` grün" belegte einen schmaleren Check als das Gate | Vor einer Lint-Aussage einmal prüfen, ob das lokale Target den CI-Schritt vollständig abdeckt; sonst den CI-Schritt lokal nachbilden | #11 |
| Ein `except Exception` fasste Serverfehler und Programmierfehler zusammen | In der Schleife nur die erwarteten IMAP-Fehler fangen; alles andere durchlassen oder getrennt zählen | #12 |
| `erzeuger` fällt still auf den vertrauenswürdigen Wert | Sicherheitsrelevante Felder haben keinen Default in die erlaubende Richtung — entweder Pflichtfeld oder Default „unbekannt" | #13 |
| Die Kette wurde gemergt, bevor ein echter Lauf existierte | Ein Werkzeug, das gegen fremde Server läuft, wird einmal gegen den echten Zielserver gefahren, bevor sein Kill-Kriterium auf „erfüllt" geht | #14 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über 54 Retros:

- **18 Slugs sind bereits gate-pflichtig** (≥2 Vorkommen). Diese Session trifft vier davon:
  `claim-before-cheapest-check` (Befunde 2, 4, 5), `deferred-item-no-tracking-issue`
  (Befund 3), `always-instruction-without-enforcement` (Befund 8) und
  `local-test-gate-narrower-than-ci` (Befunde 7, 11) — letzterer war bisher bei ×1
  (`f4a546-incr`) und wird mit dieser Session **gate-pflichtig**.
- **`risiko_debt` ist über alle 54 Retros die schwächste Dimension** (Ø 2,61 gegen
  3,06–3,89 bei den anderen fünf). Diese Session bestätigt das mit einer 2.
- `refuted_rate`-Band: die letzten acht Läufe liegen zwischen 0,00 und 0,35; dieser Lauf
  bei 0,13. Kein Ausreißer, aber am unteren Rand — siehe Self-Review.

Abgleich gegen den Memory-Index: `feedback_ci_lint_red_check_tool_version_first` existiert
und beschreibt exakt das Muster aus Befund 4 (ungepinnte Werkzeugversion färbt CI rot).
Es war vorhanden und wurde nicht angewendet — das ist kein fehlendes Wissen, sondern eine
nicht abgerufene Notiz.

## 5b. Autonomie-Kalibrierung

- `over_ask`: 0. Alle vorgelegten Entscheidungen (Konzept annehmen, PRs mergen) waren echte
  Gates — Merge auf ein Repo mit Deploy-on-push bzw. eine Konzept-Annahme.
- `over_act`: **1**. Das Referenzpostfach wurde in einem echten, vom Owner bereitgestellten
  Postfach angelegt und dabei ein Löschpfad ausgeführt, dessen Präfix-Filter zu weit griff
  (Befund 6). Der Owner hatte das Konto freigegeben, aber nicht „ein Skript, das Ordner
  löscht" — der destruktive Teil war in der Freigabe nicht benannt.

## 6. Verankerung (Vorschläge — nicht von mir geschrieben)

**memory_candidates**

```markdown
---
name: feedback_kill_gate_status_needs_reconcile_on_contrary_evidence
description: Ein Fix, der einen als "erfüllt" geführten Mechanismus repariert, muss die Kill-Gate-Tabelle im selben PR nachziehen
metadata:
  type: feedback
drift: true
drift_episode: 2026-07-27-kill-gate-status-stale
---

Eine Kill-Gate-Tabelle (KONZ §13) ist ein Claim, kein Beiwerk. Wird ein Mechanismus
repariert, den sie als **erfüllt** führt, ist das per Definition Gegenevidenz — die Zeile
gehört im selben PR nachgezogen oder die Nicht-Änderung begründet.

**Why:** Am 2026-07-27 deckte der erste echte Lauf vier stille Fehler in genau den
Mechanismen auf, die §13 als erfüllt/teilweise führte (K2/K3/K4/K10). Das Ereignis erfüllte
wörtlich die eigene KG-PROCESS-Abbruchbedingung ("produktiver Ausweis mit unbekannten
Teilfehlern") — und wurde nirgends dagegen bewertet. `gh search prs "KG-PROCESS"`: 0 Treffer.

**How to apply:** Berührt ein PR eine Funktion, die in einer K-Tabelle als Beleg steht,
vor dem Merge die Zeile prüfen. Siehe [[feedback_accepted_adr_amendment_needs_execution_pr]].
```

```markdown
---
name: feedback_destructive_prefix_match_needs_separator
description: Ein löschender Präfix-Vergleich endet auf dem Trenner — startswith allein trifft Fremdnamen
metadata:
  type: feedback
drift: true
drift_episode: 2026-07-27-referenzpostfach-delete-prefix
---

Wer per Namenspräfix **löscht**, muss auf der Namensraum-Grenze filtern:
`name == W or name.startswith(W + sep)`. Ein nacktes `startswith(W)` trifft jeden Namen,
der zufällig so anfängt.

**Why:** `referenzpostfach.py` löschte alles unterhalb von `INBOX.REF`. Gegenprobe: von fünf
geprüften Fremdnamen erfüllten **alle fünf** den Präfix — darunter `INBOX.REFERAT.Wichtig`.
Der Guard gegen das falsche Postfach war vorhanden, der gegen den falschen Ordner nicht.

**How to apply:** Gilt für IMAP-Ordner, S3-Präfixe, Branch-Namen, Dateipfade. Mindestens ein
Fremdnamen-Gegenbeispiel im Test.
```

```markdown
---
name: feedback_test_reading_home_is_machine_not_code
description: Ein Test, der Path.home() liest, misst die Maschine — Konfiguration per tmp_path injizieren
metadata:
  type: feedback
drift: true
drift_episode: 2026-07-27-home-dependent-test
---

Ein Test, der echte Konfiguration aus `Path.home()` liest, ist auf der Entwicklermaschine
grün und in der CI rot — oder, schlimmer, dort inhaltsleer grün.

**Why:** Am 2026-07-27 scheiterte Lauf 30295192917 mit `assert []`, weil auf der
CI-Maschine weder `graph-mail-tokens` noch `mail*.env` existieren. Ein zweiter Test lief
dort durch, ohne etwas zu prüfen — die gefährlichere Variante, weil unsichtbar.

**How to apply:** Funktion nimmt ein optionales Verzeichnis, Test übergibt `tmp_path`.
Gegenprobe vor dem Push: `HOME=<leeres Verzeichnis> pytest`. Verwandt:
[[feedback_throwing_test_double_is_vacuous_behind_except]].
```

**adr_candidates** — keine. Alle Befunde sind Umsetzungs- oder Prozessfehler unterhalb der
ADR-Schwelle; die betroffenen Entscheidungen (ADR-284 §2, KONZ-035) stehen bereits.

## 7. Maßnahmen

### 🟢 Offen — dein Zug

1. 🟢 #1493 (K6/K8) freigeben — https://github.com/achimdehnert/platform/pull/1493
2. 🟢 #1494 (vier Pilotfehler + zwei Retro-Fixes) freigeben — https://github.com/achimdehnert/platform/pull/1494
3. 🟢 risk-hub#447 ist grün und approved, liegt seit dem 23.07. — https://github.com/iilgmbh/risk-hub/pull/447

### 🔵 Offen — ich kann sofort

4. 🔵 Issue für die Fleet-Wirkung anlegen (Befund 3) und in risk-hub#460 verlinken
5. 🔵 K-Tabelle in KONZ-035 gegen die vier Pilotfehler nachziehen, KG-PROCESS bewerten (Befund 1)
6. 🔵 K5 auf „offen" zurücksetzen oder den Lauf als Artefakt anhängen (Befund 2)
7. 🔵 Nicht existierenden Testpfad in KONZ-035 korrigieren (Befund 9)
8. 🔵 `erzeuger` zum Pflichtfeld machen (Befund 13)

### ✅ Erledigt

9. ✅ Löschpfad präfix-sicher, DELETE-Rückgabewert ausgewertet (Befund 6)
10. ✅ Beide Tests hermetisiert, Gegenprobe mit leerem `HOME` (Befund 7)
11. ✅ Falsche Test-Behauptung in #1494 per Kommentar korrigiert (Befund 5)
12. ✅ Formatfehler in risk-hub#458 behoben (Befund 11)
13. ✅ Fehldiagnose in risk-hub#459 korrigiert (Befund 4)

## 8. Nicht verifiziert (Restlücken)

- **Befund 6 wurde von mir selbst verifiziert, nicht von einem unabhängigen Skeptiker.**
  Der Finder hat ihn gemeldet, ich habe die Gegenprobe gefahren und sofort behoben, weil es
  ein löschender Pfad war. Damit ist Richter≠Angeklagter für die *Verifikation* dieses einen
  Befunds gebrochen. Billigster Check: den Befund in der nächsten Retro-Runde als Behauptung
  einem Skeptiker vorlegen.
- **Ob die neun anderen Repos tatsächlich denselben offenen Versionsbereich fahren**, ist
  weiterhin ungeprüft. Die einzige Messung stammt aus lokalen Klonen, nicht aus `origin/main`.
  Billigster Check: `gh api repos/<owner>/<repo>/contents/Makefile` je Repo.
- **Ob die Zahl „1666 passed" in risk-hub#458 stimmt**, ist offen: der CI-Job brach vor dem
  Testschritt ab. Billigster Check: nach dem Format-Fix den Lauf abwarten.
- **Die Wirksamkeit der Fixes in #1494 gegen den echten Exchange-Server** ist für die
  UID-Korrektur und die Kalibrierung belegt, für die Nenner-Gegenprobe und den Konten-Nenner
  nur im Test. Billigster Check: ein erneuter `--topic`-Lauf gegen das HNU-Konto.

## Self-Review

- `refuted_rate` = 0,13 liegt unter dem gesunden Band (0,2–0,8) und am unteren Rand der
  letzten acht Läufe (0,00–0,35). Ein einzelner Wert belegt kein Muster, aber die Richtung
  ist zu beobachten: von 16 Behauptungen überlebten 14. Entweder waren die Finder ungewöhnlich
  treffsicher — plausibel, weil die Session dicht an belegbaren Artefakten war — oder die
  Skeptiker haben zu wenig angegriffen. Die zwei Widerlegungen betrafen beide echte
  Sachfragen (Fehlerklassen-Gleichsetzung, Rebuild-Status), was für die erste Lesart spricht.
- Invariante erfüllt: 14 überlebende Befunde, 14 Soll-Schritte.
- Scores ganzzahlig, jeder an Befundnummern verankert.
