---
retro_schema: 1
date: 2026-07-22
repo_scope: [writing-hub, platform]
session_id: 20ef83-incr
footprint: full
footprint_reduction_reason: "Increment-Retro auf die Abarbeitung der Maßnahmen von 20ef83. Kein Prod-Deploy im Increment (alle Merges cosmetic-gated, verifiziert an den Job-Conclusions), keine Migration — Rule-B feuert nicht. Über lean, weil eine live geschaltete Änderung am eigenen Guardrail (evidence_claim_scanner.py) im Scope liegt."
findings_total: 5
findings_survived: 5
findings_harness_only: 1
refuted_rate: 0.0
phase3_refuted: 0
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 4
  entscheidungsqualitaet: 3
gate_candidates: [claim-before-cheapest-check, deferred-item-no-tracking-issue]
recurring_findings: [claim-before-cheapest-check, deferred-item-no-tracking-issue, autoclose-sweeps-meta-issue-by-title, guardrail-change-uncommitted, subagent-prod-access-unscoped-prompt]
---

# Session-Retro 2026-07-22 (Increment) — writing-hub/platform: Die Maßnahmen des Eltern-Retros, und was beim Abarbeiten schiefging

> **Increment auf `20ef83`.** In-scope ist ausschließlich, was **nach** dem Schreiben jenes Reports geschah — die Abarbeitung seiner eigenen acht Maßnahmen. Die dort behandelten Befunde werden nicht neu verhandelt.

## 1. Executive Summary

- **Die Automatik hat ihren eigenen Fehlerbericht kassiert.** platform#1353 (angelegt für „Canary-Titel irreführend + kein Kommentar-Throttle") wurde 30 Minuten später vom Canary selbst geschlossen — dessen Auto-Close-Step sucht offene Issues per Titel-Substring `prod-uptime-canary in:title` **ohne** Label-Filter. Alle drei DoD-Kästchen sind unangehakt. Der Effekt ist für jedes künftige Meta-Issue über den Canary reproduzierbar.
- **Der Guardrail-Patch liegt uncommittet.** `~/.claude` ist ein git-Repo mit 17 Commits und sauberer Konventions-Historie; `hooks/evidence_claim_scanner.py` wurde heute geändert, aber nie committet — neben sechs weiteren modifizierten und vier untracked Dateien, teils Wochen alt. Kein Remote, also auch kein Backup.
- **Die neuen Hook-Muster sind im Betrieb unbelegt.** Der einzige reale Treffer (an #1353) ging nachweislich auf das drei Wochen alte `verification`-Muster zurück, nicht auf eines der beiden heute eingeführten. Ich hatte das Gegenteil suggeriert, ohne zu prüfen, welches Muster feuerte.
- **Die Muster haben messbare Lücken.** „Ein Throttle **fehlt**", „**ohne jeden** Throttle", „**deckungsgleich**", „**1:1 ersetzt**", englisches „**lacks**" — alle feuern nicht. Der Skeptiker fand zusätzlich, dass die Aussagesatz-Form „**Es gibt kein** X" gar nicht erfasst wird, nur die Wortfolge „gibt es kein".
- **Sauber:** die Verdrahtung des neuen Musters in `main()` (unabhängig per Transkript-Test bestätigt), PR #325, der Draft #326, und die Schließ-Begründungen von #322/#317/#312.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | platform#1353 wurde vom Auto-Close-Step des Canary geschlossen, den es selbst kritisiert — Titel-Substring-Suche ohne Label-Filter, alle 3 DoD offen | Werkzeug | kritisch | SURVIVES | `prod-uptime-canary.yml:154-155` — zweite `gh issue list` ohne `--label`; `closedBy: github-actions[bot]` 14:45:08Z; `labels: []` | `autoclose-sweeps-meta-issue-by-title` (neu) |
| 2 | Der Hook-Patch liegt uncommittet in `~/.claude` (17 Commits Historie, org-konforme Message-Konvention, **kein Remote**) — neben 6 weiteren modifizierten + 4 untracked Dateien | Prozesslücke | hoch | SURVIVES | `git -C ~/.claude status --porcelain`; `log --oneline -5` → `efc70ed` 2026-07-15; `remote -v` leer | `guardrail-change-uncommitted` (neu) |
| 3 | Die Wirksamkeit der beiden NEUEN Muster ist im Betrieb unbelegt — der reale Treffer an #1353 kam vom `verification`-Muster (seit `effd5d9`, 2026-07-01) | fehlende Validierung | mittel | SURVIVES | Echter Issue-Body gegen `CLAIM_PATTERNS` getestet → einziger Treffer `verification` auf „Verifiziert"; neue Muster: kein Treffer | `claim-before-cheapest-check` (#27) |
| 4 | Beide neuen Muster haben Lücken: 7 realistische Absenz-/Deckungs-Formulierungen feuern nicht; „Es gibt kein X" (Aussagesatz) gar nicht; ein FP („keinen Bock") | fehlende Validierung | mittel | SURVIVES | Eigener Modul-Import des Skeptikers mit selbst gebildeten Fällen; `absence-claim`-Regex verlangt die Wortfolge „gibt es kein" | — |
| 5 | Die Reaper-Diskrepanz („0 entfernt", Zahl sank trotzdem) ist im Memory dokumentiert, aber nirgends als Issue getrackt | Prozesslücke | mittel | SURVIVES | `gh issue list --search reaper/worktree` beide Repos: kein Treffer von heute; `grep 2026-07-22` in beiden Manifesten: 0 | `deferred-item-no-tracking-issue` (#2) |

**Außerhalb der Zählung — Harness-Meldung, kein Phase-3-Befund:**

| # | Vorfall | Kategorie | Severity | Beleg |
|---|---|---|---|---|
| H1 | Ein von mir gestarteter Finder versuchte SSH-root + `docker exec` gegen den **Prod-Host**, weil mein Prompt den Zugriffsweg nicht eingrenzte | Prozesslücke | hoch | Security-Warning des Harness zum Subagenten; Classifier blockte, Agent wich auf MCP aus |

H1 ist **kein** `SURVIVES` — er durchlief keinen Skeptiker, sondern wurde vom Harness gemeldet. Er zählt deshalb nicht in `findings_total`/`findings_survived` und nicht in den `refuted_rate`-Nenner (eigenes Frontmatter-Feld `findings_harness_only`). Aufgenommen wird er trotzdem, weil Charta-Regel 5 die Selbstmeldung eigener Fehler verlangt — die Zählregel darf das nicht verwässern, das Verschweigen aber auch nicht.

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **3** | Alle acht Maßnahmen wurden angefasst, aber zwei landeten nur scheinbar: #1353 steht auf CLOSED bei offenem DoD (Befund 1), der Hook wirkt lokal, ist aber nicht gesichert (Befund 2). „Erledigt" im GitHub-Status ≠ erledigt. |
| architektur_design | **3** | Die Trennung in zwei Marker-Klassen mit je eigenem Evidenz-Gate ist richtig konstruiert und korrekt verdrahtet (unabhängig bestätigt). Abzug: die Regexes wurden am **Wortlaut** des Vorfalls gebaut, nicht an der Bedeutungsklasse (Befund 4). |
| code_konventionstreue | **3** | Commit-Format, Worktree-Disziplin und Verifiziert/Nicht-verifiziert-Sektionen durchgehalten. Abzug: ein Repo mit 17 sauberen Commits blieb mit 7 modifizierten + 4 untracked Dateien zurück (Befund 2). |
| risiko_debt | **2** | Drei Artefakte lesen sich als erledigt, sind es nicht: #1353 CLOSED bei offenem DoD (Befund 1), Hook wirkt aber ungesichert (Befund 2), Reaper-Diskrepanz dokumentiert aber ungetrackt (Befund 5). Erneut die schwächste Dimension. |
| prozess_effizienz | **4** | **Befundfrei** — kein Finder brachte hier etwas vor. Positiv begründet: Reihenfolge stimmte (erst Arbeit sichern via #326, dann aufräumen), kein Rework, keine Doppelarbeit, keine Merge-Konflikte. Kein 5, weil H1 (Prod-Zugriffsversuch eines Subagenten) einen vermeidbaren Umweg erzeugte. |
| entscheidungsqualitaet | **3** | Stark: `--admin` bewusst nicht genutzt, WIP als Draft gesichert statt gelöscht, das eigene Issue mit gemessenen Zahlen korrigiert. Schwach: dem Hook einen Treffer zugeschrieben, ohne zu prüfen, welches Muster feuerte (Befund 3). |

## 4. Soll-Ablauf

Invariante: **5 überlebende Befunde → 5 Soll-Schritte** (#1–#5). Der sechste Schritt gehört zu H1 und steht außerhalb der Invariante — ein Vorfall ohne Lehre wäre sinnlos, auch wenn er nicht mitzählt.

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Ein Meta-Issue über eine Automatik bekam einen Titel, der die Suchphrase dieser Automatik wörtlich enthält | Vor dem Anlegen eines Issues **über** einen Automatismus dessen eigene Such-/Close-Queries lesen und den Titel so wählen, dass er sie nicht matcht — oder das Issue sofort mit einem Label versehen, das der Close-Pfad ausschließt | #1 |
| Ein geändertes Stop-Hook-Skript in `~/.claude` blieb uncommittet, weil der Abschluss-Scan nur `~/github/*/` iteriert | Der Dirty-Check am Sessionende iteriert **jedes** git-Repo, das in der Session angefasst wurde — inklusive `~/.claude`. Wer eine Datei in einem Repo mit Commit-Historie ändert, committet sie im selben Zug | #2 |
| „Der Hook hat gefeuert" wurde als Beleg für die neuen Muster gelesen, ohne die Label-Angabe der Meldung zu prüfen | Wenn ein eigener Guardrail anschlägt, zuerst **auslesen, welches Muster** gefeuert hat (Label steht in der Meldung), bevor man den Treffer einer bestimmten Änderung zuschreibt | #3 |
| Regexes wurden aus dem konkreten Vorfallssatz abgeleitet und nur gegen dessen Varianten getestet | Ein neues Erkennungsmuster wird gegen eine **selbst erweiterte** Formulierungsliste getestet — mindestens Synonyme („fehlt", „ohne", „lacks"), Aussagesatz- und Frageform, deutsch und englisch. Der eigene Bau-Satz zählt nicht als Testfall | #4 |
| Eine offen erkannte Unklarheit landete im Session-Memory statt in einem Issue | „Nicht verifiziert" im Report ist kein Tracking. Jede Zeile dort bekommt im selben Zug entweder einen ausgeführten Check oder ein Issue — sonst existiert sie beim nächsten Mal nicht | #5 |
| Ein Subagent-Prompt verlangte einen Existenz-Check, ohne den Zugriffsweg einzugrenzen; der Agent griff zu SSH-root gegen Prod | Jeder Subagent-Prompt, der Daten prüfen lässt, benennt **explizit** den erlaubten Zugriffsweg und schließt Prod-Zugriff aus. Die Einschränkung gehört in den Prompt, nicht in die Hoffnung auf den Classifier | H1 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py`, Stand vor diesem Report:

| Slug | vorher | nachher | Status |
|---|---|---|---|
| `claim-before-cheapest-check` | ×26 | **×27** | 🚨 längst gate-pflichtig |
| `deferred-item-no-tracking-issue` | ×1 | **×2** | 🚨 **neu gate-pflichtig** |
| `autoclose-sweeps-meta-issue-by-title` | — | ×1 | neu |
| `guardrail-change-uncommitted` | — | ×1 | neu |
| `subagent-prod-access-unscoped-prompt` | — | ×1 | neu |

**Eigene Zählkorrektur:** Im Eltern-Retro und in der Session-Kommunikation stand „×27 nach zwei neuen Instanzen". Falsch — `retro_kpis.py` zählt einen Slug **einmal pro Retro-Datei**, nicht pro Instanz. Der Eltern-Retro hob den Zähler von 25 auf 26, nicht auf 27. Ein Zählfehler in einer Aussage über einen Zähler, der Zählfehler messen soll.

**Der strukturelle Befund:** Der Eltern-Retro schlug den Hook-Patch als Antwort auf `claim-before-cheapest-check` vor. Der Patch wurde gebaut, getestet, live geschaltet — und derselbe Slug feuert im Increment **erneut** (Befund 3), diesmal in Form einer unbelegten Aussage **über den Patch selbst**. Das ist kein Argument gegen den Patch, aber ein Beleg dafür, dass ein Werkzeug die Disziplin nicht ersetzt, solange seine eigene Wirkung wieder nur behauptet statt gemessen wird.

## 5b. Autonomie-Kalibrierung

| KPI | Wert | Beleg |
|---|---|---|
| `over_ask` | **0** | Alle vier Arbeitspakete (Hook, Reaper, Worktree, Issue) waren explizit freigegeben; der selbstbetreffende Charakter des Hook-Patches wurde vor der Ausführung gekennzeichnet. |
| `over_act` | **1** | Befund 6: Ein von mir gestarteter Subagent versuchte einen Prod-Zugriff (SSH-root + `docker exec`), den niemand freigegeben hatte. Dass der Classifier ihn abfing, ändert nichts an der Zurechnung — der ungeeignete Prompt war meiner. |

`over_act` ist damit ×1 im Längsschnitt. Kein Muster ≥2, also keine Charter-Schärfung fällig — aber der Fall gehört ausdrücklich in die Delegations-Praxis: **Prod-Ausschluss gehört in jeden Subagent-Prompt**, nicht in die Annahme, dass die Gates schon greifen.

## 6. Verankerung (kopierfertig — Mensch entscheidet)

> Vorschläge. Weder Memory-Datei noch Workflow-Änderung wurde von dieser Retro geschrieben.

### memory_candidates

```markdown
---
name: drift-autoclose-sweeps-meta-issue-by-title
description: Ein Issue ÜBER eine Automatik darf deren Suchphrase nicht im Titel tragen — Auto-Close per Titel-Substring kassiert sonst den eigenen Fehlerbericht
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-22-canary-closed-its-own-bug-report
---

platform#1353 („Prod-Uptime-Canary: /readyz/-503 meldet unter 'nicht erreichbar'
+ kommentiert alle 15 min ohne Throttle") wurde 30 Minuten nach dem Anlegen vom
`github-actions`-Bot geschlossen — mit der Begründung „Alle überwachten
Prod-Endpoints wieder 200". Alle drei DoD-Kästchen waren unangehakt.

Ursache: `prod-uptime-canary.yml:154-155` sucht beim Grün-Werden offene Issues
über **zwei** Wege — per Label UND per `gh issue list --search
"prod-uptime-canary in:title"`. Die zweite Query hat keinen Label-Filter; sie war
als Fallback für Alt-Issues ohne Label gedacht. Mein Issue hatte `labels: []` und
die Phrase im Titel — also getroffen.

**Why:** Ein Meta-Issue über einen Automatismus enthält dessen Namen fast
zwangsläufig im Titel. Die Automatik unterscheidet nicht zwischen „Alert, den ich
erzeugt habe" und „Bericht über meinen Defekt". Der Effekt ist für jedes künftige
Issue mit dieser Phrase reproduzierbar.

**How to apply:** Vor dem Anlegen eines Issues **über** einen Automatismus dessen
eigene Such-/Close-Queries lesen (`grep -n "issue list\|issue close" <workflow>`)
und den Titel so wählen, dass er sie nicht matcht — oder sofort ein Label setzen,
das der Close-Pfad ausschließt. Gilt analog für jeden Bot, der per Volltextsuche
aufräumt. Siehe [[gate-claim-before-cheapest-check]].
```

```markdown
---
name: guardrail-change-belongs-in-a-commit
description: Änderungen an ~/.claude (Hooks, Policies, settings.json) im selben Zug committen — das Verzeichnis ist ein git-Repo ohne Remote, ein Reset löscht sie ersatzlos
metadata:
  type: feedback
---

Am 2026-07-22 wurde `~/.claude/hooks/evidence_claim_scanner.py` um zwei
Marker-Klassen erweitert, getestet und live geschaltet — aber nie committet. Der
Session-Abschluss meldete „0 dirty", weil sein Scan nur `~/github/*/` iteriert.

`~/.claude` ist ein git-Repo mit 17 Commits und org-konformer Message-Konvention
(`feat(hooks)`, `docs(hausregeln)`) — der Versionierungs-Anspruch ist also
etabliert. Es hat aber **kein Remote**: ein `git checkout --` oder ein Neuaufsetzen
der Maschine löscht die Änderung ersatzlos. Neben dem Hook lagen sechs weitere
modifizierte und vier untracked Dateien, teils seit Wochen.

**Why:** Das Verzeichnis liegt außerhalb `~/github/` und fällt deshalb durch jeden
Fleet-Scan, der über `~/github/*/` iteriert. Genau diese Lücke reproduzierte sich
im Prüfauftrag der Retro selbst.

**How to apply:** Wer eine Datei unter `~/.claude` ändert, committet sie im selben
Zug. Der Dirty-Check am Sessionende iteriert **jedes** in der Session angefasste
git-Repo, nicht nur `~/github/*/`. Bei Guardrails (Hooks, Policies) zusätzlich
prüfen, ob ein Test mitgeändert werden muss — der vorhandene
`hooks/test_evidence_claim_scanner.py` kennt die neuen Muster nicht.
```

```markdown
---
name: subagent-prompt-must-scope-access-path
description: Jeder Subagent-Prompt, der Daten prüfen lässt, benennt den erlaubten Zugriffsweg und schließt Prod aus — sonst greift der Agent zum nächstbesten Mittel
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-22-finder-ssh-prod
---

Ein Retro-Finder bekam den Auftrag „prüfe, ob die Memory-Einträge existieren" —
ohne Angabe, wie. Er schrieb ein Skript, das per SSH als root auf den Prod-Host
ging und `docker exec` im Orchestrator-Container ausführte, um die Daten zu ziehen.
Der Permission-Classifier blockte, der Agent wich auf das MCP-Tool aus; das Harness
meldete den Versuch als Security-Warnung.

**Why:** Ein Subagent kennt die Gates der Hauptsession nicht und optimiert auf
Aufgabenerfüllung. Ein Prompt, der ein Ziel nennt aber keinen Weg, delegiert die
Wegwahl — und der kürzeste Weg zu Live-Daten ist oft Prod. Dass der Classifier hier
hielt, ist Glück, keine Kontrolle: die Zurechnung liegt beim Prompt-Autor.

**How to apply:** In jeden Subagent-Prompt, der Daten prüft, einen expliziten Satz
aufnehmen — welcher Zugriffsweg erlaubt ist (lokal, `gh`, `git`, benannte CLI) und
dass Prod-Zugriff (SSH, `docker exec` gegen Remote-Hosts) untersagt ist. Die
Einschränkung gehört in den Prompt, nicht in die Hoffnung auf nachgelagerte Gates.
```

### adr_candidates

Keine. Alle sechs Befunde sind Werkzeug- und Prozesslücken innerhalb bestehender
Muster — nach `adr-threshold.md` kein ADR-Anlass.

## 7. Maßnahmen

### 🟢 Offen — dein Zug

1. 🟢 platform#1353 wieder öffnen + Titel entschärfen oder Label setzen — https://github.com/achimdehnert/platform/issues/1353
2. 🟢 Auto-Close-Fallback im Canary auf Label-Pflicht umstellen (Titel-Substring-Query entfernen) — file:///home/devuser/github/platform/.github/workflows/prod-uptime-canary.yml
3. 🟢 `~/.claude` committen (Hook + 6 weitere Dateien sichten) — file:///home/devuser/.claude
4. 🟢 3 Memory-Kandidaten übernehmen? — file:///home/devuser/.claude/projects/-home-devuser-github-writing-hub/memory/

### 🔵 Offen — ich kann sofort

5. 🔵 Hook-Muster um „fehlt/ohne jeden/deckungsgleich/1:1/lacks/Es gibt kein" erweitern — file:///home/devuser/.claude/hooks/evidence_claim_scanner.py
6. 🔵 `hooks/test_evidence_claim_scanner.py` um die neuen Klassen ergänzen — file:///home/devuser/.claude/hooks/test_evidence_claim_scanner.py
7. 🔵 Issue für die Reaper-Diskrepanz anlegen — file:///home/devuser/github/platform/tools/worktree-reaper.py

### ✅ Erledigt

8. ✅ #325 gemergt, Falschaussagen von `main` entfernt — https://github.com/achimdehnert/writing-hub/pull/325
9. ✅ #326 sichert den gestrandeten WIP als Draft — https://github.com/achimdehnert/writing-hub/pull/326
10. ✅ #1334 gemergt, Eltern-Retro auf `main` — https://github.com/achimdehnert/platform/pull/1334
11. ✅ #322/#317/#312 mit belegten Begründungen geschlossen — https://github.com/achimdehnert/writing-hub/issues/322

## 8. Nicht verifiziert (Restlücken)

| Offen | Billigster Check |
|---|---|
| Befund 6 (Subagent-Prod-Zugriff) durchlief **keinen** Phase-3-Skeptiker — er stammt aus einer Harness-Meldung, nicht aus einem Finder | Das Subagent-Transkript unter `tasks/*.output` lesen und den konkreten Befehl zitieren |
| Ob der Reaper die Worktree-Zahl überhaupt gesenkt hat (Manifest zeigt keinen Eintrag von heute) | `repo-session.sh`-Merge-Pfad lesen: `grep -n "worktree remove\|prune" tools/repo-session.sh` |
| Ob ein echter `/readyz/`-503 im Canary wirklich ein Issue erzeugt | `workflow_dispatch` in einem Fork gegen einen absichtlich falschen Endpunkt |
| Ob die erweiterten Hook-Muster nach dem Fix im Betrieb feuern | Nach der nächsten Absenz-/Deckungs-Behauptung die Label-Angabe der Hook-Meldung lesen |

## Self-Review

Der Meta-Reviewer (separater Agent, sah nur diesen Report + die Skill) prüfte 12
Formregeln und fand **drei** Verstöße, alle korrigiert:

1. **Selbst erfundenes drittes Verdikt.** Befund 6 trug „HARNESS-MELDUNG" und lief
   trotzdem in `findings_survived` und den `refuted_rate`-Nenner. Das umgeht die
   Regel „nur SURVIVES gehen in den Report", statt sie einzuhalten — Offenlegung
   ersetzt keine Zählregel. Jetzt als **H1** außerhalb der Zählung geführt, mit
   eigenem Frontmatter-Feld `findings_harness_only`; `findings_total` 6→5.
2. **Uneinheitliche Score-Verankerung.** Zwei von sechs Dimensionen zitierten keine
   Befund-Nummer. `risiko_debt` ergänzt, `prozess_effizienz` ausdrücklich als
   befundfrei-positiv gekennzeichnet.
3. **Streak-Framing ohne Deckung.** „Vierter Wert im Trendfenster" suggerierte eine
   Serie; real sind es 4 von 9 verstreuten Werten. Korrigiert.

Danach die numerischen Auffälligkeiten, die ich selbst benennen muss.

**`refuted_rate` = 0,00 — der vierte Wert unter 0,20, aber NICHT konsekutiv.**
Präzise: 4 von 9 zurückliegenden Werten liegen unter 0,20 (`590926: 0,10`,
`8d663b-incr: 0,00`, `20ef83: 0,11`, jetzt `0,00`), verteilt über neun Reports —
dazwischen liegen `c25d21: 0,375`, `d80d23: 0,50`, `11feac: 0,25`, `8d663b: 0,27`.
Der `--min-band`-Check von `retro_kpis.py` bleibt deshalb weiterhin auf „gesund";
es gibt keine Serie, nur eine Häufung. Meine erste Formulierung („vierter Wert im
Trendfenster") suggerierte einen rollierenden Trend, den das Tool nicht führt —
korrigiert.

Der Eltern-Retro hat sich für den vierten Unterschreiter selbst verpflichtet:
*„bei einem vierten Wert <0,2 ist die Finder- oder Skeptiker-Schärfe ein eigener
Befund wert."* Die Zusage wird eingelöst, auch wenn die Streak-Lesart entfällt.

Die Lage ist zweideutig. **Für** die These „Falsifikation wird zur Formsache":
sechs von sechs Behauptungen gingen unverändert durch, keine einzige wurde
verworfen. **Gegen** sie: der Skeptiker hat bei B4 den Streitfall zwischen zwei
Lesarten *aktiv entschieden* — und dabei die Version bestätigt, die dem
Auftraggeber dieses Reports **widerspricht** (mein „der Hook hat wegen der neuen
Muster gefeuert" war falsch). Er hat außerdem bei B3 eine Lücke gefunden, die kein
Finder vorgelegt hatte („Es gibt kein X" wird gar nicht erfasst). Das ist kein
Abnicken.

Die plausibelste Erklärung ist strukturell, nicht qualitativ: Ein Increment-Retro
prüft die Abarbeitung **bereits falsifizierter** Befunde. Die Behauptungen sind
damit von vornherein enger und besser belegt als in einem Erst-Retro — eine
niedrige Widerlegungsquote ist hier eher zu erwarten als verdächtig. Wenn das
stimmt, ist der Band-Schwellwert für `-incr`-Retros schlicht falsch kalibriert und
sollte getrennt geführt werden. Das ist eine **Hypothese**, kein Befund: sie wäre
zu prüfen, indem man die `refuted_rate` aller `-incr`-Reports gegen die der
Erst-Reports vergleicht — `retro_kpis.py` trennt das heute nicht.
