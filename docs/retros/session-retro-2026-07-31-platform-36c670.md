---
retro_schema: 1
date: 2026-07-31
repo_scope: [platform, dotclaude-memory]
session_id: 36c670
footprint: full
findings_total: 13
findings_survived: 5
refuted_rate: 0.31
phase3_refuted: 4
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [deferred-item-no-tracking-issue, claim-before-cheapest-check]
recurring_findings: [deferred-item-no-tracking-issue, claim-before-cheapest-check, test-fixtures-not-from-real-data, shared-constant-duplicated-across-tools, allowlist-key-too-coarse]
---

# Session-Retro 2026-07-31 — platform (Memory-Integrität, Testbasis, Tier-Policy)

**Scope:** PRs #1596, #1601, #1602, #1603, #1605, #1606, #1609 (alle gemergt),
Issue #1597 (geschlossen), drei Commits im lokalen Repo `~/.claude`
(`22c0b53`, `b628f2c`, `639700b`). Fremde Sitzungen desselben Tages sind
ausdrücklich außer Scope.

## 1. Executive Summary

- **317 Verweis-Befunde auf 0 harte gesenkt** über 832 Memory-Dateien in 36
  Verzeichnissen; die 10 Reste sind als vorausschauende Verweise in einer
  Baseline geführt, nicht übermalt.
- **Testbasis von 33 auf 25 ungetestete Module** (6718 → 4792 Zeilen); alle
  Löschpfade sind jetzt abgedeckt.
- **Der schwerste Fremdbefund wurde widerlegt:** die Namensangleichung habe 61
  menschenlesbare Titel zerstört — der Skeptiker zeigt, dass `description:` und
  die MEMORY.md-Zeile den Titel unverändert weitertragen.
- **Das teuerste Eigenversagen ist prozessual, nicht technisch:** der Fehler,
  den #1606 nach zweieinhalb Stunden behob, wäre durch **einen** Lauf des
  Werkzeugs gegen echte Daten vor dem Merge von #1596 gefallen.
- **Zwei bewusst aufgeschobene Reste haben kein Tracking-Artefakt** — genau das
  Muster, das `risiko_debt` seit 60 Messungen zur schwächsten Dimension macht.

## 2. Befunde

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Tests in #1596 enthielten keinen Fixture mit Code-Fence/Backticks, obwohl das Muster im realen Bestand vorkommt; der von #1606 behobene Fehler wäre durch einen Lauf gegen echte Daten vor dem Merge gefallen | fehlende Validierung | mittel | SURVIVES | `gh pr diff 1596` → 0 Treffer für CODE_FENCE/INLINE_CODE/Backtick-Fixture; Docstring `memory_link_check.py:34-38` beziffert 12 von 45 Fehllesungen | test-fixtures-not-from-real-data |
| 2 | Baseline-Schlüssel ist `(Projekt, Ziel)` statt `(Projekt, Datei, Ziel)` — ein echter Tippfehler in Datei B wird als `forward-ref` durchgewunken, wenn Datei A denselben String legitim führt | fehlende Validierung | mittel | SURVIVES | `origin/main:tools/claude-hooks/memory_link_check.py:210` `erlaubt = baseline.get(mem.parent.name, set())`; kein Test mit zwei Dateien + kollidierendem Ziel | allowlist-key-too-coarse |
| 3 | `NICHT_MEMORY` ist in beiden Werkzeugen doppelt hartkodiert, obwohl die Regexe ausdrücklich geteilt werden ("eine Quelle für beide") | Werkzeug | mittel | SURVIVES | `memory_link_check.py:58` vs. `memory_link_fix.py:55` identischer Set-Literal; `memory_link_fix.py:39` importiert nur CODE_FENCE/INLINE_CODE | shared-constant-duplicated-across-tools |
| 4 | `CODE_FENCE` erkennt eingerückte Fences nicht und schließt verschachtelte 4-Backtick-Blöcke am inneren Fence | Werkzeug | niedrig | SURVIVES | Repro des Skeptikers gegen beide Fälle; im Bestand aktuell folgenlos (5 eingerückte Fences, keiner mit `[[..]]`) | — |
| 5 | Zwei bewusst aufgeschobene Reste ohne Tracking-Artefakt: Hook-Verdrahtung aus #1596 und Testrest aus #1605 (25 Module, 4792 Zeilen) | Prozesslücke | niedrig | SURVIVES | PR #1596 Body "entscheidet der Owner separat"; PR #1605 Body "25 Module ohne Test"; sechs Suchformulierungen liefern kein Issue | deferred-item-no-tracking-issue |
| 6 | Namensangleichung habe 61 inhaltstragende Titel zerstört | verfrühte Festlegung | hoch | **REFUTED** | `description:` und MEMORY.md-Zeile tragen den Titel unverändert weiter (5 Stichproben); unabhängige Zählung ergibt 60, nicht ≥61 | — |
| 7 | Konvention "name = Dateiname" sei für die Zukunft zementiert | verfrühte Festlegung | hoch | **REFUTED** | `grep -rn memory_link_check ~/.claude/settings.json .github/workflows/` → 0 Treffer; keine Verdrahtung, also Hypothese über die Zukunft | — |
| 8 | Abnahmekriterien selbst umgeschrieben und danach abgehakt | Prozesslücke | hoch | **REFUTED** | Änderung ausdrücklich als "Vorschlag (nicht still geändert)" vorgelegt; Merge durch zweites Konto `wirdigital`, nicht durch den Kommentar-Autor | — |
| 9 | Drei Test-PRs ohne Dateiüberschneidung hätten ein PR sein können | Prozesslücke | niedrig | **REFUTED** | Lückenlose Staffelung (jeder PR erst nach Merge des vorigen), drei verschiedene Risikoklassen, je einzeln rückrollbar | — |
| 10 | Dreifache Zahlenkorrektur in Issue #1597 (10/16/19 → 12/23/10; 12 → 5; 7/23/11 → 8/23/10) | fehlende Validierung | mittel | nicht Phase-3-geprüft (§8) | Issue #1597, Kommentare wörtlich "Zahlen per Auge gezählt statt gemessen" | claim-before-cheapest-check |
| 11 | Kein Artefakt verbindet den Ausgangspunkt (Video-Analyse) mit dem gelieferten Werk | Kommunikation | niedrig | nicht Phase-3-geprüft (§8) | `grep -iE "youtube\|system.?prompt\|kürzen"` über alle 7 PR-Bodies + 3 Commits → 0 thematische Treffer | — |
| 12 | Issue-Closure-Rückverfolgbarkeit: Gruppe a+b wurde durch `639700b` im remote-losen Repo erledigt, das Issue schloss aber über PR #1609 ohne verlinkenden Kommentar | Kommunikation | mittel | nicht Phase-3-geprüft (§8) | `gh pr view 1609 --json closingIssuesReferences`; kein Kommentar zwischen 13:40 und 14:16 | — |
| 13 | Review 6–13 Sekunden vor Merge bei allen sieben PRs | — | — | **kein Befund** | Owner-Angabe: `wirdigital` ist mit der Thematik betraut; aus Artefakten allein nicht auflösbar, durch Owner-Kontext beantwortet | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | 317 → 0 harte Befunde, Testbasis 33 → 25 Module, alle PRs gemergt; Abzug für die zwei ungetrackten Reste (#5) |
| architektur_design | 3 | Geteilte Regex-Quelle und Baseline mit Verrottungs-Prüfung sind tragfähig; #2 (zu grober Schlüssel) und #3 (doppelte Konstante) sind echte Konstruktionsmängel |
| code_konventionstreue | 4 | `test_should_*`, `make test` grün, CI auf allen PRs echt grün, keine Konventionsverstöße gefunden |
| risiko_debt | 3 | Datenänderung über 220 Dateien in einem Repo ohne Remote und ohne Review; zwei Reste ohne Issue (#5). Mildernd: Versionierung wurde VOR der ersten Änderung eingeführt |
| prozess_effizienz | 3 | #1606 war vermeidbares Rework (#1) — ein Lauf gegen echte Daten hätte gereicht; drei Zahlenkorrekturen (#10) |
| entscheidungsqualitaet | 3 | Der Beinahe-Fehler beim globalen Namens-Replace wurde selbst gefangen und die Bauart daraufhin umgestellt; dagegen stehen #1, #2 und #3 als vermeidbare Entwurfslücken |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll | eliminiert |
|---|---|---|
| Testfälle für `memory_link_check` aus erfundenen Beispielen gebaut; erster Lauf gegen die echten 832 Dateien erst NACH dem Merge von #1596 | Vor dem Merge eines Scanners einmal gegen den echten Bestand laufen und mindestens einen Fixture aus einer realen Datei ableiten — "grün gegen Fixtures" ist kein Beleg über reale Eingaben | #1 |
| Baseline-Schlüssel als `(Projekt, Ziel)` gewählt, weil das die 10 bekannten Fälle abdeckte | Ausnahmelisten auf der feinsten Ebene schlüsseln, die der Befund liefert — hier `(Projekt, Datei, Ziel)`; der Prüfbericht liefert das Tripel bereits | #2 |
| `NICHT_MEMORY` beim Bauen des zweiten Werkzeugs kopiert, während die Regexe importiert wurden | Wenn eine Konstante geteilt wird, ALLE geteilten Konstanten aus einer Quelle importieren und einen Test auf Gleichheit setzen | #3 |
| Fence-Regex aus dem Referenzfall abgeleitet (kein eingerückter, kein verschachtelter Fence darin) | Eine Regex, die Markdown-Struktur erkennt, gegen mindestens ein Gegenbeispiel je Variante prüfen, bevor sie als Filter dient | #4 |
| Zwei Reste im PR-Body benannt ("entscheidet der Owner separat", "25 Module ohne Test"), ohne Issue | Im selben Zug ein Issue anlegen — der PR-Body zählt laut Hausregel ausdrücklich nicht als Tracking | #5 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` gelaufen. **18 Slugs sind bereits ≥2 und damit
gate-pflichtig.** Für diese Sitzung einschlägig:

- **`deferred-item-no-tracking-issue`** — Befund #5, bereits ≥2. Das ist der
  direkte Treiber von `risiko_debt` (Ø 2,55 über 60 Messungen, schwächste
  Dimension überhaupt).
- **`claim-before-cheapest-check`** — Befund #10, bereits ≥2. Dreimal in dieser
  Sitzung; jedes Mal vom evidence-discipline-Hook gefangen, nie von mir selbst.

Neu eingeführte Slugs: `test-fixtures-not-from-real-data`,
`shared-constant-duplicated-across-tools`, `allowlist-key-too-coarse` (je ×1).

**Werkzeug-Defekt in der Retro-Skill selbst (Phase 1):** Das vorgeschriebene
`git log --since=<datum>` liefert bei bloßem Datum ohne Uhrzeit **null Treffer**,
obwohl Commits existieren — gemessen: `--since=2026-07-31` → 0,
`--since='2026-07-31 00:00'` → 3. Der Collector meldete daraufhin "keine
Commits" als Faktum. Der Agent hat korrekt ausgeführt; das Rezept ist defekt.

**Zweiter Skill-Defekt:** Der Collector sammelte nach **Datum** statt nach
**Konversation** und lieferte 30 PRs, von denen 23 fremden Sitzungen gehören.
Ohne Korrektur hätten die Finder fremde Arbeit beurteilt.

## 5b. Autonomie-Kalibrierung

- **`over_ask`: 0** — kein Vorgang wurde vorgelegt, der deterministisch und
  reversibel war.
- **`over_act`: 0** — kein Gate wurde autonom überschritten. Die
  Datenänderung an 220 Memory-Dateien war grenzwertig (Massenänderung ohne
  Review), aber die Versionierung wurde **vor** der ersten Änderung eingeführt,
  womit sie rücknehmbar war; kein Prod-Schritt, kein Publish, kein drittes Repo.
- Bemerkenswert: der Merge von #1609 und damit das Schließen von #1597 erfolgte
  durch `wirdigital`, während eine von mir gestellte Entscheidungsfrage zum
  Abnahmekriterium noch offen im Issue stand. Das ist kein `over_act` meinerseits,
  aber ein Hinweis, dass `Closes #N` im PR-Body eine offene Entscheidungsfrage
  überholen kann.

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

### memory_candidates

```markdown
---
name: feedback_scanner_fixtures_from_real_data
description: "Einen Scanner vor dem Merge einmal gegen den echten Bestand fahren — Fixtures aus erfundenen Beispielen decken die Eingabeform nicht ab"
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-31-memory-link-check-code-fence
---

Ein Scanner, dessen Testfälle aus erfundenen Beispielen stammen, ist gegen
Fixtures grün und gegen die Realität falsch. Der Prüfer aus platform#1596 las
Wiki-Verweise auch aus Code-Bereichen; kein einziger Fixture enthielt einen
Code-Fence oder Inline-Backticks, obwohl beides im realen Memory-Bestand steht.

**Why:** Der Fehler kostete platform#1606 zweieinhalb Stunden später — und war
durch **einen** Lauf gegen die echten 832 Dateien vor dem Merge sichtbar.
12 von 45 verbleibenden Befunden gingen darauf zurück.

**How to apply:** Vor dem Merge eines Scanners/Prüfers: einmal scharf gegen den
echten Bestand laufen lassen und mindestens einen Fixture aus einer realen Datei
ableiten. "Grün gegen Fixtures" belegt nichts über reale Eingaben. Verwandt:
[[feedback_dry_run_does_not_cover_write_path]] (dieselbe Familie: der sichere
Modus prüft den gefährlichen Teil nicht).
```

```markdown
---
name: feedback_allowlist_key_as_fine_as_the_finding
description: "Eine Ausnahmeliste auf der feinsten Ebene schlüsseln, die der Befund liefert — ein zu grober Schlüssel deckt fremde Fehler mit ab"
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-31-forward-ref-baseline-key
---

Die Baseline für vorausschauende Verweise (platform#1609) schlüsselt auf
`(Projekt, Ziel)`. Der Prüfbericht liefert aber `(Projekt, Datei, Ziel)`. Damit
wird ein echter Tippfehler in Datei B stillschweigend als zulässig durchgewunken,
sobald Datei A denselben String legitim führt.

**Why:** Eine Ausnahmeliste ist nur so präzise wie ihr Schlüssel. Wer gröber
schlüsselt als der Befund es erlaubt, kauft Bequemlichkeit mit einer Fehlklasse,
die niemand mehr sieht — und genau dagegen war die Liste gebaut.

**How to apply:** Schlüssel = die feinste Identität, die der meldende Befund
mitliefert. Beim Bau einer Ausnahmeliste zusätzlich einen Test schreiben, der
belegt, dass ein Eintrag NICHT auf ein Nachbarobjekt durchschlägt.
```

### adr_candidates

Keiner. Beide Werkzeuge folgen bestehenden Mustern (Hook in
`tools/claude-hooks/`, Test in `tools/tests/`), keine neue Service-Grenze, keine
Umkehr einer bestehenden Entscheidung — laut `adr-threshold.md` kein ADR-Fall.

## 7. Maßnahmen

### 🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Zwei Memory-Vorschläge verankern | platform | — | 🟢 offen | annehmen/ablehnen du |
| 2 | Hook-Verdrahtung entscheiden | platform | — | 🟢 offen | ja/nein du |

### 🔵 Offen — ich kann sofort

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 3 | Baseline-Schlüssel auf Tripel | platform | — | 🔵 ready | Befund #2 |
| 4 | `NICHT_MEMORY` teilen + Gleichheitstest | platform | — | 🔵 ready | Befund #3 |
| 5 | Issue für Testrest anlegen | platform | — | 🔵 ready | Befund #5 |
| 6 | Fence-Regex härten | platform | — | 🔵 ready | Befund #4 |

## 8. Nicht verifiziert (Restlücken)

- **Befunde #10, #11, #12 liefen NICHT durch Phase 3.** Sie stammen aus je zwei
  bzw. einem Finder mit wörtlichem Artefakt-Zitat, wurden aber nicht unabhängig
  falsifiziert. Billigster Check: ein Skeptiker-Pass über genau diese drei.
- **Die Zählung "60 vs. 61 Titel"** in Befund #6 weicht zwischen Finder und
  Skeptiker ab. Für das Verdikt (REFUTED) ist die Differenz folgenlos, für eine
  spätere Aufarbeitung nicht. Billigster Check:
  `git -C ~/.claude show b628f2c --unified=0 -- '*.md' | grep -c '^-name:'`.
- **Der Effekt der Namensangleichung auf die semantische Suche** (pgvector)
  wurde nicht geprüft — falls `name:` dort als Einbettungs-Feld dient, könnte die
  Angleichung Trefferqualität verändert haben. Billigster Check: Feldliste des
  Einbettungs-Schemas im Orchestrator.
- **Ob die 10 Baseline-Einträge sachlich zutreffen** (also wirklich "noch zu
  schreiben" statt Tippfehler) wurde nicht gegengeprüft, nur ihre Form.
