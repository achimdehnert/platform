---
retro_schema: 1
date: 2026-08-17
repo_scope: [illustration-hub, platform]
session_id: 9e4a72
footprint: deep
findings_total: 7
findings_survived: 4
refuted_rate: 0.14
phase3_refuted: 0
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [claim-before-cheapest-check, deferred-item-no-tracking-issue]
recurring_findings: [claim-before-cheapest-check, deferred-item-no-tracking-issue]
---

# Session-Retro 2026-08-17 · illustration-hub · `9e4a72`

## 1. Executive Summary

- Aus „Prio 1" wurde eine Zielzustands-Entscheidung („GUI-optimierte Plattform") und daraus
  sechs weitere Punkte — jede Erweiterung kam als explizites Owner-`go`, nicht als Drift.
- Geliefert: 4 Commits über 4 Zweige (illustration-hub) + 1 Commit (platform). **Kein einziger
  gepusht** — GitHub lag ab 13:40 UTC im `major`-Ausfall.
- Der teuerste Befund ist nicht der Code, sondern die **Buchführung**: vier bewusst
  aufgeschobene Punkte haben kein durables Artefakt — nur Chat.
- Zwei Defekte fing die eigene Testschicht, bevor sie jemand sah (Kommentar-Leck,
  zweite N+1-Quelle). Ein dritter Befund war eine **Behauptung**, die der billigste Check
  widerlegt hätte.
- Die Falsifikation der zwei Bewertungsbefunde steht aus: Subagenten sind in dieser Umgebung
  per Systemanweisung untersagt (§8).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Mehrzeiliges `{# … #}` liefert Kommentartext an den Leser aus — 1 neu eingeführt, 5 im Bestand live | Wissenslücke | mittel | SURVIVES | Testfehler `data-stand-url not in <page>`; Scan über 25 Vorlagen | neu |
| 2 | „Kein einziges Byte JavaScript" verallgemeinert aus `grep <script` — `onsubmit` existierte | fehlende Validierung | mittel | SURVIVES | `git show origin/main:apps/comics/templates/comics/project_detail.html` → `<script` 0, `onsubmit` 1 | claim-before-cheapest-check |
| 3 | Vier aufgeschobene Punkte ohne durables Artefakt (3 ungepushte Zweige, Ruleset-Änderung, `cover`-Entscheidung) | Prozesslücke | hoch | SURVIVES | `gh issue list`: nur #263 neu; kein Ledger unter `~/shared/` oder im Repo | deferred-item-no-tracking-issue |
| 4 | Erster N+1-Fix unvollständig — nur Vorlagen-`.count` gegrept, Property `welt` übersehen | fehlende Validierung | niedrig | SURVIVES | `git show --stat ee8a7eb` → Nachzug in `apps/comics/models.py` (+10) | neu |
| 5 | ~~Zweig-Bündelung: ein PR, zwei Themen, `wip:`-Commit in der Historie~~ | verfrühte Festlegung | mittel | **REFUTED** (2026-08-19) | `merge-base --is-ancestor 8009924 origin/main` → nein (Squash); `pr-schnitt-und-stapel.md` empfiehlt bei Dateiüberlappung **einen** PR | — |
| 6 | Ohne Fehlerzustand hätte die Selbstaktualisierung bei dauerhaftem Fehlschlag 30 Min. leer gefragt — ~~als verfrühte Festlegung gewertet~~ | Mechanismus real, Wertung fällt | niedrig | **PARTIALLY REFUTED** (2026-08-19) | `MAX_VERSUCHE = 360` × 5 s = 30 Min. steht im Quelltext; `9bfc400` war nie auf `main`, 25 Min. später selbst geschlossen | — |
| 7 | *(vorab widerlegt)* „`9bfc400` enthielt eine Endlos-Neuladeschleife" | — | — | PRE-REFUTED | `git show 9bfc400`: `beobachten` und `laeuft` nutzten **dieselbe** Bedingung, konnten nicht auseinanderlaufen | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | 4 von 6 zugesagten Punkten geliefert; 2 durch Fremdausfall blockiert, 1 (24) begründet zurückgewiesen statt blind ausgeführt |
| architektur_design | 4 | Gemeinsame Schicht für CLI+UI (`lora_export.py`), ein Vertragsmodul (`core/stand.py`), Prefetch statt zweiter Wahrheit; kein Status-Feld neben `render_asset` |
| code_konventionstreue | 4 | Repo-Muster durchgehalten (action-POST, `data-testid`, deutsche Docstrings), `ruff` sauber — abzüglich Befund #1 |
| risiko_debt | 2 | Befund #3: 4 aufgeschobene Punkte ohne Artefakt, 4 Commits nur lokal, eine Migration nirgends remote |
| prozess_effizienz | 3 | Zwei Testläufe durch eigene Fehler verloren (Fixture-Kollision, falsche pytest-Fixture); Zweig-Merge war pragmatisch, aber ungeplant |
| entscheidungsqualitaet | 4 | Vor `cover`-Löschung gestoppt (Gate 1), zweites Repo angesagt, eigene JS-Behauptung selbst korrigiert |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Drei mehrzeilige `{# … #}` geschrieben, Leck erst durch fehlschlagende Tests bemerkt (`base.html`, 2 Vorlagen) | Vor dem ersten Commit einer Vorlage: `{% comment %}` für alles, was über eine Zeile geht — der Gate-Test `test_vorlagen_kommentare.py` steht jetzt, er hätte den eigenen Fehler beim ersten Lauf gefangen | #1 |
| „Kein einziges Byte JavaScript" aus einem `grep <script` gefolgert und als Befund #6 der Verbesserungsliste veröffentlicht | Bei einer **Abwesenheits**-Behauptung immer die zweite Schreibweise mitprüfen (`grep -E "on[a-z]+=\|<script"`), sonst als „kein `<script>`-Tag" formulieren statt als „kein JavaScript" | #2 |
| Vier Punkte in den Chat aufgeschoben, weil GitHub schrieb nicht — kein Artefakt angelegt | Ist die Schreibseite von GitHub aus, im selben Zug eine Datei `docs/offen-<datum>.md` im Worktree anlegen und mitcommitten; sie ersetzt das Issue, bis die API wieder da ist | #3 |
| N+1 über die Vorlagen gegrept (`.count`), gefixt, committet — die zweite Quelle (`ComicProject.welt`) fand erst der Abfragezähler-Test | Bei einer Abfrage-Optimierung nicht die Vorlage lesen, sondern **zuerst** den Zähler-Test schreiben und ihn die Fundstellen benennen lassen; das Grep ist die Hypothese, der Zähler der Beleg | #4 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (81 Reports) — zwei Slugs dieser Sitzung stehen bereits auf
Gate-Pflicht:

| Slug | Zähler vor dieser Sitzung | jetzt | Status |
|---|---|---|---|
| `claim-before-cheapest-check` | ≥2 (gate-pflichtig gelistet) | +1 | Gate existiert als CLAUDE.md-Regel, greift nicht mechanisch |
| `deferred-item-no-tracking-issue` | ≥2 (gate-pflichtig gelistet) | +1 | dito |

`risiko_debt` liegt im Bestand bei Ø 2,56 über 79 Reports — die schwächste Dimension. Diese
Sitzung liegt mit **2** darunter und bestätigt das Muster: nicht der Code, die Buchführung
über bewusst Liegengelassenes ist der wiederkehrende Schwachpunkt.

Neuer Slug-Kandidat (×1, kein Gate nötig): `django-multiline-comment-leaks-to-page` — in
dieser Sitzung bereits mechanisch geschlossen (`tests/test_vorlagen_kommentare.py`).

## 5b. Autonomie-Kalibrierung

| KPI | Wert | Beleg |
|---|---|---|
| `over_ask` | 0 | Jede Erweiterung kam als Owner-`go`; nichts deterministisch Reversibles wurde unnötig vorgelegt |
| `over_act` | 0 | Kein Prod-Schritt, kein Merge, kein Push; zweites Repo angesagt; `cover`-Löschung (irreversibel) bewusst zurückgehalten |

Ein Grenzfall in die andere Richtung: Punkt 24 kam mit `go`, wurde aber **nicht** ausgeführt,
weil die Messung die Prämisse nicht trug (3 von 5 „Fragment"-Apps sind tragend) und der eine
echte Kandidat eine Tabelle hat. Das ist kein `over_ask` — der Befund wurde geliefert, nur die
Handlung nicht.

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

**memory_candidates**

```markdown
---
name: django-mehrzeiliger-kommentar-wird-ausgeliefert
description: Djangos {# #} gilt einzeilig — mehrzeilig landet der Text in der Seite
metadata:
  type: reference
  drift: true
  drift_episode: 2026-08-17-kommentar-leck
---
`{# … #}` entfernt nur, was in **derselben Zeile** schliesst. Ein mehrzeiliger Kommentar
wird ausgeliefert und sieht im Browser wie Fliesstext aus — im Diff sieht die Zeile korrekt
aus, deshalb faengt es kein Review. Gefunden 2026-08-17 in illustration-hub: 1 neu
eingefuehrt, 5 im Bestand live. Mehrzeilig immer `{% comment %}…{% endcomment %}`.
Gate: `tests/test_vorlagen_kommentare.py` scannt alle Vorlagen.
Verwandt: [[claim-before-cheapest-check]]
```

```markdown
---
name: abwesenheits-behauptung-braucht-zweite-schreibweise
description: "kein X im Code" aus einem Grep folgt nur, wenn alle Schreibweisen gegrept wurden
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-08-17-kein-byte-javascript
---
`grep -c "<script"` ergab 0 → daraus wurde „kein einziges Byte JavaScript". Real stand ein
`onsubmit="return confirm(...)"` in derselben Datei.
**Why:** Eine Abwesenheits-Behauptung ist so breit wie ihr Suchmuster; ein zu enges Muster
erzeugt eine Null, die wie ein Beweis aussieht.
**How to apply:** Vor jeder „kein X"-Aussage die zweite Schreibweise mitprüfen — oder die
Aussage auf das Gemessene einengen („kein `<script>`-Tag"). Verwandt:
[[null_ohne_positivkontrolle_werkzeug]]
```

**adr_candidates** — keine. Die Sitzung hat keine Architektur-Weiche gestellt; die eine
offene Weiche (`cover` entfernen) ist eine Owner-Entscheidung, kein ADR.

## 7. Maßnahmen

### 🟢 Offen — dein Zug

1. 🟢 Ruleset: `test` als Pflicht-Check ergänzen — https://github.com/achimdehnert/illustration-hub/issues/150
2. 🟢 `cover`: nur Registrierung entfernen oder samt Tabelle — https://github.com/achimdehnert/illustration-hub/tree/main/apps/cover
3. 🟢 Falsifikation der Befunde #5/#6 freigeben (~110k Token, 2 Skeptiker) — file:///home/devuser/.repo-session/worktrees/platform/2026-08-17-achim-dehnert-retro-2026-08-17-illustration-hub-145932/docs/retros/session-retro-2026-08-17-illustration-hub-9e4a72.md

### 🔵 Offen — ich kann sofort

4. 🔵 Aufgeschobenes als Datei im Worktree festhalten, bis GitHub schreibt — file:///home/devuser/github/illustration-hub/AGENT_HANDOVER.md
5. 🔵 Push + 3 PRs + Merge #262, sobald der Vorfall vorbei ist — https://github.com/achimdehnert/illustration-hub/pull/262

### ⛔ Blockiert

6. ⛔ Alles Schreibende gegen GitHub — `major · Partial System Outage` seit 13:40 UTC — https://www.githubstatus.com/

## 8. Nicht verifiziert (Restlücken)

| Lücke | Warum offen | Billigster Check |
|---|---|---|
| ~~Regel-1-Bruch: Find-Phase lief inline~~ | **geschlossen 2026-08-19**: Owner hat die Skeptiker freigegeben (illustration-hub#265 Entscheidung 3), zwei Sonnet-Agenten gelaufen | — |
| ~~Befunde #5 und #6 unfalsifiziert~~ | **geschlossen 2026-08-19** — s. Abschnitt 9 | — |
| Phase-5 Meta-Review des Reports | derselbe Grund | 1 Sonnet-Agent auf Report + Skill |
| `deep`-Footprint ohne volle Pipeline gefahren | Migration `0009` triggert `deep`; Herunterstufen war nicht zulässig (Regel verlangt „keine DB-Migration") | — |
| Ob `ih_cover_jobs` auf Prod Zeilen hat | Kein benannter Management-Befehl dafür; `manage.py shell` ist auf Prod geblockt | Zählbefehl bauen oder Owner fragt die DB |
| Ob die 4 Commits nach dem Push grün durch CI gehen | GitHub Actions degradiert, nichts gepusht | `gh pr checks` nach dem Push |

**Getan:** 4 Commits illustration-hub, 1 Commit platform, 1 Issue (#263), 32 neue Tests,
4 Vorlagen-Lecks im Bestand geschlossen, 1 Gate gebaut.
**Angenommen:** dass die vier Zweige nach dem Push grün durchlaufen (lokal 877–911 grün).
**Nicht verifizierbar:** alles Serverseitige während des Ausfalls.
**Offen geblieben:** Punkte 19/20 (Ruleset), Punkt 24 (Owner-Entscheid), Push aller Zweige.

## 9. Falsifikation der Bewertungsbefunde (nachgetragen 2026-08-19)

Zwei unabhängige Skeptiker, je einer auf einen Befund, beide mit dem Auftrag zu
**widerlegen** und der Vorgabe „im Zweifel refuted". Der Verfasser dieser Retro war an
beiden Läufen nicht beteiligt (Richter ≠ Angeklagter). Die tragenden Belege sind danach
**unabhängig nachgeprüft** worden, nicht übernommen — bei jeder Abwesenheitsaussage
einschliesslich Positivkontrolle.

### Befund #5 — REFUTED

Beide Hälften fallen, und zwar an geprüften Tatsachen statt an Geschmack:

* **Der `wip:`-Commit steht nicht in der Historie.** `git merge-base --is-ancestor 8009924
  origin/main` verneint; derselbe Befehl bejaht für einen bekannt gemergten Commit
  (Positivkontrolle). Der Squash-Merge hat ihn nie durchgelassen. Die Behauptung war eine
  Tatsachenannahme, die niemand geprüft hatte.
* **Die Regel, gegen die gemessen wurde, gibt es nicht.**
  `docs/conventions/pr-schnitt-und-stapel.md` sagt wörtlich: „Die Trennlinie ist nicht
  ‚ein Issue = ein PR', sondern ob der Diff ohne den anderen überhaupt Sinn ergibt."
  Für „fachlich gekoppelt" steht dort als Empfehlung **ein PR**. Beide Zweige fassten
  dieselben zwei Dateien an, und der PR-Text legte die Bündelung offen.

Damit ist #5 dieselbe Klasse wie #2 dieser Retro — eine Bewertung auf ungeprüfter
Prämisse. Der Unterschied: dort war die Prämisse eine `grep`-Null, hier eine **erfundene
Konvention**. Das ist der schärfere Fall, weil eine erfundene Regel jeden Befund trägt,
den man an sie hält.

### Befund #6 — PARTIALLY REFUTED

* **Der Mechanismus ist real und bleibt stehen.** `laeuft = offen > 0` kennt keinen
  Fehlerbegriff; Celery gibt nach `max_retries` auf, das Panel bleibt DB-seitig „offen".
* **Die Zahl war nicht erfunden.** `MAX_VERSUCHE = 360` bei `ABSTAND_MS = 5000` sind exakt
  30 Minuten, mit Kommentar im Quelltext. Der naheliegendste Refutationsgrund trägt nicht.
* **Die Wertung „verfrühte Festlegung" fällt.** `9bfc400` war nie eigenständig auf `main`,
  wurde nie deployt, und derselbe Autor fand und schloss die Lücke 25 Minuten später in
  derselben Sitzung — vor jedem PR. Eine Trennung, die vor dem Merge aufgelöst wird, ist
  kein Prozessmangel, sondern der normale Verlauf von Arbeit.

### Was das über die Retro selbst sagt

Von zwei Bewertungsbefunden hielt **keiner** in seiner ursprünglichen Form. Beide
beschrieben etwas Reales und werteten es falsch. Das ist kein Argument gegen
Bewertungsbefunde, sondern eines für die Falsifikationsstufe: sie hat hier zwei von zwei
korrigiert, und in beiden Fällen war der billigste Check ein Einzeiler.
