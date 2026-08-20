---
retro_schema: 1
date: 2026-08-20
repo_scope: [platform, tax-hub, travel-beat, trading-hub, risk-hub]
session_id: beefc148
footprint: deep
findings_total: 11
findings_survived: 5
refuted_rate: 0.55
phase3_refuted: 6
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [gate-claim-before-cheapest-check-wirkungslos, guard-untested-against-its-own-bypass, test-asserts-text-not-behavior]
recurring_findings: [claim-before-cheapest-check, gate-claim-before-cheapest-check-wirkungslos]
---

# Session-Retro 2026-08-20 — platform (beefc148)

## 1. Executive Summary

- Die Sitzung baute ein Maß, das der Loop bisher nicht hatte: **Rückfälle nach dem Gate-Bau**. Ergebnis über 82 Retros — 8 von 20 Gates rückfällig, genau **eines** belegt wirksam. Der Zielzustand ist erreicht, alle vier Akzeptanzkriterien einzeln belegt (skeptiker-bestätigt).
- **Das neue Werkzeug hat zwei reproduzierte Fehler**, beide von einem fremden Prüfer gefunden, beide in gemergtem Code: die Anti-Goodhart-Sperre ist durch die eigene `elif`-Reihenfolge umgehbar, und der Frontmatter-Parser verliert Slugs still bei Inline-Kommentaren. Die zweite Fehlrichtung ist die gefährlichere — sie **verdeckt** Rückfälle.
- Drei rote Prod-Stränge aufgelöst und je am Manifest wirkungsgeprüft. In allen drei Fällen war die Prio-Prämisse überholt; die tatsächliche Ursache war jedes Mal eine andere als die dokumentierte.
- **Sechs von elf Befunden wurden widerlegt** — darunter drei, die als Anklage gegen die Sitzung formuliert waren, und einer, den die Sitzung selbst schon als Treffer akzeptiert hatte. Die Fehlerrichtung war beidseitig: zu streng häufiger als zu milde.
- Der überlebende Kern-Befund ist ein **Gate-Rückfall**, nicht ein neuer Fehler: `claim-before-cheapest-check` traf zu, obwohl sein Gate gebaut, verdrahtet und drill-grün ist — begangen in derselben Sitzung, die den Rückfall vermessen hat.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | **Gate `claim-before-cheapest-check` ist rückfällig.** Aussage auf tax-hub#123 (10:09:26Z), Production werde „nicht erreicht, weil Staging davor steht" — sachlich falsch, 27 Min später vom selben Autor widerrufen. `deploy.yml:57` hätte es vorab gezeigt. | fehlende Validierung | hoch | SURVIVES | tax-hub#123 Kommentare 10:09:26Z / 10:36:28Z; `origin/main:.github/workflows/deploy.yml:57` | Gate seit 2026-08-02, **16 Rückfälle**; Slug ×48 |
| 2 | **Anti-Goodhart-Sperre durch eigene Zweig-Reihenfolge umgehbar.** `RUECKFAELLIG` wird vor `fenster < MIN_FENSTER` geprüft; zugleich zählt `nachher` das Retro des Bau-Tags mit (`d >= gebaut`). Da ein Gate meist aus dem Befund des Bau-Tags entsteht, reicht faktisch **ein** weiterer Rückfall statt zwei. Der Code-Kommentar behauptet das Gegenteil. | Werkzeug | kritisch | SURVIVES | `tools/gate_wirkung.py:162-173`; Probe-Lauf des Prüfers: `RUECKFAELLIG` bei `fenster_retros: 2` | neu |
| 3 | **Frontmatter-Parser verliert Slugs still.** `_LISTEN_EINTRAG` matcht nur `^\s*-\s*slug\s*$`; ein `- slug  # Kommentar` bricht den Block ab, alle folgenden Einträge fallen weg. Fehlrichtung verdeckt echte Rückfälle. | Werkzeug | hoch | SURVIVES | `tools/gate_wirkung.py:86,140-146`; Reproduktion des Prüfers | neu |
| 4 | **Drill für den `deploy.sh`-Fix prüft Text, nicht Verhalten.** `test_deploy_migrate_url.py` grept Substrings, führt die Shell-Zeile nie aus. Der Mechanismus ist korrekt (Prüfer verifizierte mit `sh`/`dash`), aber die Tests wären bei einer textlich ähnlichen, im Container kaputten Zeile blind. | fehlende Validierung | mittel | SURVIVES | `tools/tests/test_deploy_migrate_url.py:41-67` | verwandt `untested-tool-module-green-gate` (Gate seit 2026-08-12) |
| 5 | **Beleg trägt nicht so weit wie die Behauptung.** PR #2151 begründet „bei `schedule` sind Inputs leer" mit Lauf `32359300251` — der war ein `workflow_dispatch`-Lauf und kann die Schedule-Semantik nicht belegen. Die Aussage selbst ist korrekt (Doku-verifiziert), der zitierte Beweis nicht einschlägig. | fehlende Validierung | mittel | SURVIVES | `gh run view 32359300251` → `event: workflow_dispatch`; PR #2151 Body | Familie `claim-before-cheapest-check` |
| 6 | risk-hub-Dispatch sei undokumentiert geblieben | Prozesslücke | mittel | **REFUTED** | #2148 Kommentar 11:31:47Z benennt Run 32363921746, Ursache und Konsequenz | — |
| 7 | „2 von 4 substanziellen Aussagen korrigiert" | Kommunikation | niedrig | **REFUTED** | Zähler 2 belegt, Nenner 4 ohne kanonische Grundlage (2/3 oder 2/5 gleich plausibel) | — |
| 8 | PRs #2149/#2150 adressieren #2143 | — | niedrig | **REFUTED** | Beide existieren, referenzieren #2143 aber weder im Body noch in der Timeline | — |
| 9 | Prio 5 (#2086) mit keinem Wort erwähnt | Kommunikation | mittel | **REFUTED** | `AGENT_HANDOVER.md` Z.83 (Prio 6) + Z.89 — zwei Treffer im Volltext | — |
| 10 | Auftrag nur zur Hälfte eingelöst (Gates nicht repariert) | verfrühte Festlegung | niedrig | **REFUTED** | Zielzustand Z.42 enthält keine Reparatur-Zusage; Abnahme Z.52 belegt alle vier Kriterien; Reparatur explizit Out-of-Scope mit Tracking (#2143) | — |
| 11 | „Zeitplan ist zurück" als vollzogen behauptet | verfrühte Festlegung | hoch | **REFUTED** | Klammerzusatz „(#2151, Auto-Merge scharf)" qualifiziert die Zeile korrekt als in Arbeit | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **4** | Zielzustand erreicht, vier Kriterien einzeln belegt (#10 REFUTED bestätigt das) — Abzug für die zwei Fehler im gelieferten Werkzeug (#2, #3) |
| architektur_design | **3** | Der Entwurf ist tragfähig und an drei Stellen verdrahtet, aber ausgerechnet die Ehrlichkeits-Sperre, die sein Alleinstellungsmerkmal war, ist durch die eigene Zweig-Reihenfolge umgehbar (#2) |
| code_konventionstreue | **4** | Commit-Format und Testnamen aller fünf PRs konform (geprüft); Registry-Eintrag konsistent mit `GATE_HEADER`. Abzug: ruff-Formatierung erst nach Gate-Block nachgereicht |
| risiko_debt | **3** | Drei Prod-Deploys inkl. Migrationen, alle wirkungsgeprüft; Tracking sauber (#2143, #2148). Abzug: zwei Fehler in gemergtem Code (#2, #3) sind offene Schuld |
| prozess_effizienz | **3** | Kein vermeidbares Rework in der Deploy-Kette (#F4 des Prüfers), aber eine falsche Aussage und ein falscher Fix-Vorschlag mussten zurückgenommen werden (#1) |
| entscheidungsqualitaet | **4** | GRANT nicht ausgeführt, `--admin` verweigert, risk-hub bewusst nicht neu ausgelöst, Scope-Checkpoint durabel abgelegt. Abzug für #1 |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Mechanik aus dem Job-Verlauf **geschlossen** („Production wird nicht erreicht"), statt die Workflow-Datei zu lesen (tax-hub#123, 10:09:26Z) | Bei jeder Aussage über **Deploy-Mechanik** zuerst die Workflow-Datei am entscheidenden Ausdruck lesen (`target_environment`, `if:`, `needs:`), dann erst das Log interpretieren. Reihenfolge: Datei → Lauf → Aussage | #1 |
| `RUECKFAELLIG` steht im `elif` **vor** der `MIN_FENSTER`-Sperre, `nachher` schließt das Retro des Bau-Tags ein (`gate_wirkung.py:162-173`) | Bau-Tag ausschließen (`d > gebaut` statt `>=`) **und** die Fenster-Sperre vor die Rückfall-Prüfung ziehen; ein Test, der genau diesen Fall fixiert (2 Retros, einer davon am Bau-Tag) | #2 |
| Parser bricht den YAML-Block beim ersten nicht-passenden Zeichen ab; kein Test für Kommentare oder mehrzeilige Werte (`gate_wirkung.py:86`) | Beim Schreiben eines Parsers **die Formen zuerst als Testfälle sammeln** (inline, Block, Kommentar, Leerzeile, Einrückung), dann implementieren — nicht umgekehrt | #3 |
| Drill prüft die Aufrufzeile per Substring-Grep, führt sie nie aus (`test_deploy_migrate_url.py:41-67`) | Bei Shell-Fragmenten mindestens **einen** Test, der das Fragment mit `sh -c` real ausführt und die Variablen-Auflösung am Ergebnis prüft — Textgleichheit ist kein Verhalten | #4 |
| PR-Body zitiert einen `workflow_dispatch`-Lauf als Beleg für `schedule`-Semantik (#2151) | Vor dem Zitieren eines Laufs als Beleg prüfen, ob sein **Ereignistyp** die Behauptung überhaupt tragen kann; sonst die Quelle ehrlich als Dokumentation benennen statt als Lauf | #5 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (82 Reports): `claim-before-cheapest-check` **×47** vor dieser Retro, mit diesem Report **×48**. Weiterhin GATE-PFLICHT, wie 20 andere Slugs.

## 5a. Rückfall-Prüfung

`python3 tools/gate_wirkung.py`: **8 von 20 Gates rückfällig.** Der überlebende Befund #1 fällt exakt in diese Klasse — das Gate `claim-before-cheapest-check` ist seit dem 2026-08-02 gebaut, als Stop-Hook verdrahtet, Drill grün, und der Befund kam zum **16.** Mal nach dem Bau.

Nach der Regel dieses Skills ist der Befund damit **nicht** „Slug zum 48. Mal", sondern **Gate rückfällig** — Slug `gate-claim-before-cheapest-check-wirkungslos`. Von den drei zulässigen Antworten ist **ausweiten** unzureichend und **umbauen** die wahrscheinlich richtige: der Scanner sucht Marker im Text, der Fehlfall dieser Retro war aber eine Aussage über **Mechanik**, die keinen Marker trägt. Die Entscheidung gehört nach #2143 und wird hier nicht vorweggenommen.

Beide Slugs stehen bewusst im Frontmatter: der alte, damit der Zähler ehrlich bleibt, der neue, damit der Gate-Rückfall als eigene Klasse sichtbar wird.

## 5b. Autonomie-Kalibrierung

`over_ask`: **0.** `over_act`: **0.** Die drei Prod-Deploys waren wörtlich freigegeben (Auswahl-Dialog, zitiert in #2122). Zwei Aktionen wurden von Werkzeug-Sperren gestoppt (Secret-Guard, Klassifizierer) und **nicht** umgangen, sondern übergeben — das ist kein `over_act`, aber auch kein `over_ask`, weil die Sperre nicht vom Agenten kam.

## 6. Verankerung

**memory_candidates** (kopierfertig, vom Menschen zu entscheiden):

- `feedback_own_guard_needs_a_test_for_its_bypass` — „Wer eine Sperre gegen Kennzahl-Manipulation baut, braucht einen Test, der die Sperre **umgeht**. Zwei Fehler in `gate_wirkung.py` (2026-08-20) saßen beide in der Sperre selbst, nicht in der Messung: die `elif`-Reihenfolge übersprang die Fenster-Prüfung, und das Bau-Tags-Retro zählte als Rückfall mit. Beide fand ein fremder Prüfer, keiner der acht eigenen Tests."
- `feedback_read_the_workflow_file_before_claiming_deploy_mechanics` — „Aussagen über Deploy-Mechanik (‚wird nicht erreicht', ‚blockiert', ‚wartet auf') zuerst an der Workflow-Datei prüfen, dann am Lauf. Realfall 2026-08-20: aus dem Job-Verlauf geschlossen, Production werde von Staging blockiert; tatsächlich stand in `deploy.yml:57` ein `target_environment`-Default, der Production überspringt. 27 Minuten später selbst widerrufen."

**adr_candidates:** keine. Beide Befunde sind Werkzeug- und Disziplinfragen nach bestehendem Muster, keine Architektur-Entscheidung (`adr-threshold.md`).

## 7. Maßnahmen

### 🔵 Offen — sofort machbar

| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Bau-Tag ausschließen, Sperre vorziehen | platform | #2143 | 🔵 ready | `d > gebaut` + Test — ich |
| 2 | Parser-Formen als Tests | platform | #2143 | 🔵 ready | Kommentar/Leerzeile — ich |
| 3 | Shell-Fragment real ausführen | platform | #2143 | 🔵 ready | `sh -c`-Test — ich |

### 🟢 Offen — Owner-Entscheidung

| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 4 | Beleg-Zeile im PR korrigieren | platform | #2151 | 🟢 offen | vor Merge — du |
| 5 | Gate umbauen statt ausweiten | platform | #2143 | 🟢 offen | Mechanik-Klasse — du |

## 8. Nicht verifiziert (Restlücken)

| Was | Warum offen | Billigster Check |
|---|---|---|
| Ob das Chat-Board „✅ done" für den Zeitplan-PR eine eigene Überklaim-Instanz ist | Der Prüfer bewertete nur `AGENT_HANDOVER.md`; Chat ist kein Artefakt und lag außerhalb seines Zugriffs. Die Handover-Zeile wurde REFUTED — die Board-Zeile trug denselben Anspruch ohne den qualifizierenden Zusatz | Transkript gegen die Artefakt-Lage lesen |
| Ob `DATABASE_URL_MIGRATE` im Migrations-Container von travel-beat tatsächlich als Env ankommt | Der Prüfer hatte kein Host-Mandat; belegt ist nur, dass der Deploy durchlief | `docker compose config` auf prod-a für den Migrations-Service |
| Ob die übrigen ~20 Parallel-Sitzungen des Tages kollidierten | Nur die eigene Artefakt-Spur war in-scope | `gh pr list --search "created:2026-08-20"` gegen die Branch-Präfixe |
| Ob die 16 Rückfälle von `claim-before-cheapest-check` je einzeln echte, verschiedene Muster sind | Nie erhoben — die Zahl stammt aus Frontmatter-Zählung, nicht aus Inhaltsprüfung | Die 16 Retros gegen die Scanner-Muster lesen |

**Getan:** Rückfall-Maß gebaut, verdrahtet, verteilt; drei Prod-Stände aufgeholt und wirkungsgeprüft; fünf PRs, zwei Tracking-Issues.
**Angenommen:** dass die Frontmatter-Zählung die Realität der Rückfälle abbildet (Befund #3 zeigt, dass sie das nicht zuverlässig tut).
**Nicht verifizierbar:** die Tabelle oben.
**Offen geblieben:** die acht rückfälligen Gates selbst (#2143), risk-hubs Prod-Deploy (#2148), die zwei Werkzeug-Fehler aus dieser Retro.
