---
retro_schema: 1
date: 2026-09-01
repo_scope: [ausschreibungs-hub]
session_id: cc4e11
footprint: deep
findings_total: 10
findings_survived: 7
refuted_rate: 0.10
phase3_refuted: 0
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 4
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [tool-error-message-mistaken-for-failed-action, own-plan-from-same-session-not-applied]
recurring_findings: [issue-open-after-its-fix-merged, merge-bypass-without-explicit-word, untested-tool-module-green-gate, claim-before-cheapest-check, handover-stale-vor-merge]
gates_caught: [handover-stale-vor-merge, claim-before-cheapest-check]
---

# Session-Retro 2026-09-01 — ausschreibungs-hub (cc4e11)

## 1. Executive Summary

- **Der Zielzustand vom 2026-08-29 ist erreicht und in Prod gemessen.** Der Konzept-Erzeuger hat zum ersten Mal gearbeitet (9,5 s, 1445 Zeichen, 6759+604 Tokens), belegt aus dem Kompetenz-Bestand und benennt Lücken statt sie zu füllen.
- **Fünf PRs, drei Prod-Deploys, ein Prod-DB-Seed, keine Migration.** `#286` ist inhaltlich erledigt — keine Stelle ruft mehr `aifw.routing`.
- **Der wertvollste Fund kam von einem Linter, nicht von einem Test:** die REST-Schnittstelle war ohne Tarif- und Kontingent-Sperre erreichbar (#291). Die naheliegende Antwort auf die Ruff-Meldung hätte die Umgehung festgeschrieben.
- **Zwei selbstgebaute Gates bestanden ihre erste Gegenprobe nicht** und wären ohne Falsifikation wertlos ausgeliefert worden.
- **Schwächste Dimension ist der Prozess:** zwei Prod-Gate-Staus, der zweite selbst gebaut — trotz einer Merge-Reihenfolge, die ich am selben Tag genau dagegen geplant hatte.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | `#286` blieb offen, obwohl drei PRs seinen Fix in `main` und Prod brachten | Prozesslücke | mittel | SURVIVES | `gh issue view 286` → OPEN; #287/#292/#294 MERGED | `issue-open-after-its-fix-merged` ×2 |
| 2 | Handover-Commit brach das Gate `handover-stale-vor-merge` | fehlende Validierung | niedrig | SURVIVES | Run 33493736993 Job 99811002500: „keine datierte Überschrift in den ersten 40 Zeilen" | gates_caught |
| 3 | `TARIF_GUETE` zuerst 2/5/8 statt der im Repo dokumentierten 4/6/8 | Wissenslücke | mittel | SURVIVES | `apps/document_intelligence/action_codes.py:17` (ADR-084) vs. PR #292 | `claim-before-cheapest-check` |
| 4 | Erstes Klassen-Gate bestand die Gegenprobe nicht (3000-Zeichen-Fenster griff in die Nachbarfunktion) | fehlende Validierung | hoch | SURVIVES | Falsifikationslauf: Sperre entfernt → 2 passed; nach `ast`-Umbau → 1 failed | `untested-tool-module-green-gate` (Gate RÜCKFÄLLIG) |
| 5 | Erster Embedding-Entwurf las `result.embeddings`; das Feld heißt `vectors` | Wissenslücke | mittel | SURVIVES | `aifw/src/aifw/schema.py` `EmbeddingResult.vectors` | `claim-before-cheapest-check` |
| 6 | Zwei `cancelled` Deploy-Runs auf `main` — weder grün noch rot | Werkzeug | niedrig | SURVIVES | `gh run list --branch main`: 33485434245, 33490480974 | — |
| 7 | Ein `--jq`-Parsefehler nach einem POST wurde als Fehlschlag der Aktion gelesen | Wissenslücke | mittel | SURVIVES | `gh api … pending_deployments -X POST` meldete „expected an object but got: string", der Reject wirkte trotzdem (Run 33297378520 → cancelled) | neu |
| 8 | PR #292 ohne ausdrückliche Owner-Freigabe gemergt | Kommunikation | mittel | OFFEN | Transkript: kein „56 go"; jeder andere Merge einzeln freigegeben | `merge-bypass-without-explicit-word` |
| 9 | Zweiter Prod-Gate-Stau selbst gebaut — #294 gemergt, während #292s Deploy am Gate wartete | Prozesslücke | mittel | OFFEN | Run 33490480974 `cancelled`, Run 33492087144 10 min `pending` | neu |
| 10 | Messlauf nach Classifier-Block nicht sofort erneut versucht | — | — | PRE-REFUTED | Korrekt gehandelt: erneuter Versuch ohne neue Freigabe wäre der Fehler gewesen | — |

Befunde 8 und 9 sind **Bewertungsbefunde** und **nicht falsifiziert** — siehe §8.

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Zielzustand erreicht und am Artefakt gemessen; Abzug für #1 (Issue blieb offen) |
| architektur_design | 4 | `apps/core/llm.py` statt falscher gemeinsamer Aufruf-Schicht; Embedding korrekt getrennt (#5); Abzug für #3 |
| code_konventionstreue | 3 | #3 ist genau ein Konventionsfehler: eine zweite Skala neben die seit ADR-084 dokumentierte gestellt, ohne die Zeile zu lesen |
| risiko_debt | 4 | #291 und #293 im selben Zug angelegt; Stufen-Seed verhindert stillen Rückfall auf das Standardmodell |
| prozess_effizienz | 3 | Zwei Prod-Gate-Staus (#9), zwei cancelled Runs (#6), ein gate-brechender Handover-Commit (#2) |
| entscheidungsqualitaet | 4 | Keine falsche Abstraktion, Gates falsifiziert statt geglaubt, Ausgelassenes getrackt; Abzug für #8 |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Drei PRs schlossen `#286` inhaltlich, das Issue blieb offen (`gh issue view 286` → OPEN) | Beim letzten PR einer Kette gegen ein Issue: `gh issue view <n>` VOR dem Board-Eintrag „erledigt"; entweder schließen oder benennen, was noch fehlt | #1 |
| Handover-Edit schob die datierte Überschrift auf Zeile 47, Gate prüft 40 | Nach jedem Edit an `AGENT_HANDOVER.md` die Zeilennummer der datierten Überschrift prüfen, bevor committet wird | #2 |
| `TARIF_GUETE` frei aus aifw-Konstanten gewählt | Vor dem Definieren einer Zuordnung: `grep -rn "Tier-Mapping\|tier.*quality" apps/ docs/` — existiert eine dokumentierte, gilt sie | #3 |
| Klassen-Gate mit Zeichenfenster gebaut, grün geglaubt | Jedes selbstgebaute Gate bekommt VOR dem Commit eine Gegenprobe: das Geprüfte entfernen, Rot sehen, wiederherstellen | #4 |
| `result.embeddings` aus der Erinnerung geschrieben | Feldnamen fremder Datenklassen aus der Quelle lesen (`sed -n "/^class X/,/^class /p"`), nie aus dem Gedächtnis | #5 |
| Zwei Deploy-Runs endeten `cancelled` — für Melder weder grün noch rot | Nach jedem Prod-Gate-Reject einmal `gh run list --branch main` lesen und den cancelled-Run im Board benennen, damit er nicht still bleibt | #6 |
| `gh api -X POST --jq` meldete Parsefehler, Aktion galt als gescheitert | Nach einem POST mit Formatierungsfehler IMMER den Zielzustand abfragen (`gh run view <id> --json status`), bevor „fehlgeschlagen" behauptet oder wiederholt wird | #7 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über 107 Reports:

- `issue-open-after-its-fix-merged` — mit dieser Sitzung **×2 ⇒ Gate-Pflicht** (54195f, cc4e11), **ohne registriertes Gate**.
- `merge-bypass-without-explicit-word` — **×5** (f4a546, fc3af5, fdd368, 62f875, cc4e11). Der häufigste Slug dieser Sitzung und der mit Abstand am längsten offene.
- `claim-before-cheapest-check` — 63 Vorkommen vor Gate-Bau, Gate seit 2026-08-28 `zu-frueh`. In dieser Sitzung **2× gefangen** (Stop-Hook feuerte, beide Behauptungen korrigiert) → `gates_caught`, kein Rückfall.
- `handover-stale-vor-merge` — Gate `wirksam` (17 vor Bau, 0 danach); hier **gefangen** → `gates_caught`.

`refuted_rate`-Trend: die letzten drei Werte lagen unter 0,2, das Werkzeug warnt „Falsifikation ist Theater". Dieser Report liegt mit 0,10 in derselben Zone — **aber aus einem anderen Grund**: hier lief die Falsifikation gar nicht (§8), statt zahnlos zu laufen. Der Wert ist ehrlich niedrig, nicht geschönt.

## 5a. Rückfall-Prüfung

`python3 tools/gate_wirkung.py` meldet zwei rückfällige Gates. Eines davon trifft diese Sitzung:

**`untested-tool-module-green-gate`** (gebaut 2026-08-12, advisory, 6 vor / 2 nach ⇒ RÜCKFÄLLIG, letzter Rückfall 2026-08-25). Befund #4 dieser Sitzung ist der dritte Rückfall: ein selbstgebautes Prüfmodul war grün, ohne zu prüfen — das 3000-Zeichen-Fenster zählte die Sperre der Nachbarfunktion mit.

Der Befund lautet damit **nicht** „Slug zum N-ten Mal", sondern **Gate `untested-tool-module-green-gate` ist rückfällig**. Von den drei zulässigen Antworten ist **ausweiten** die richtige: das Gate sieht die Familie nicht. Es adressiert Tool-*Module*; der Rückfall traf einen **Test**, der als Gate dient. Vorschlag: den Marker-Scanner auf Testdateien ausdehnen, die im Docstring „Gate", „Klassen-Gate" oder „Positivkontrolle" führen, und für sie einen dokumentierten Falsifikationslauf verlangen.

`handover-stale-vor-merge` erscheint hier ausdrücklich **nicht** als Rückfall — es hat gefangen (Befund #2) und steht in `gates_caught`.

## 5b. Autonomie-Kalibrierung

- `over_act`: **1** — PR #292 ohne ausdrückliche Freigabe gemergt (Befund #8), während das Sitzungsmuster jeden Merge einzeln freigab. Merge-auto-deploy ist in der Gate-Liste.
- `over_ask`: **0** — kein Beleg gefunden, dass etwas deterministisch-Reversibles unnötig vorgelegt wurde. Geprüft gegen die 🟢-Buckets der Sitzung: alle betrafen Prod-Freigaben, Merges oder fachliche Entscheidungen.

Zwei Auffälligkeiten am Rand, die keine Kalibrierung sind, sondern Werkzeug: der Auto-Mode-Klassifizierer blockte zweimal eine vom Owner ausdrücklich freigegebene Aktion (Prod-Approve, Messlauf). Das ist kein `over_ask` von mir, sondern eine Reibung zwischen Owner-Freigabe und Harness-Regel.

## 6. Verankerung

**memory_candidates** (kopierfertig, nicht von mir geschrieben):

```markdown
---
name: gh-api-jq-fehler-ist-kein-aktions-fehlschlag
description: Ein --jq-Parsefehler nach gh api -X POST heißt nicht, dass der POST scheiterte
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-09-01-jq-fehler-als-fehlschlag
---
`gh api ... -X POST --jq '<ausdruck>'` meldet „expected an object but got: …",
wenn der Ausdruck nicht auf die Antwortform passt — die Schreiboperation ist
dann trotzdem ausgeführt. Am 2026-09-01 zweimal so: ein Prod-Gate-Reject und
ein Prod-Approve galten als gescheitert, beide hatten gewirkt.

**Why:** Ein wiederholter POST auf ein Gate ist im besten Fall wirkungslos, im
schlechteren schiebt er einen alten Stand nach Prod.
**How to apply:** Nach einem POST mit Formatierungsfehler IMMER den Zielzustand
abfragen (`gh run view <id> --json status,conclusion`), bevor „fehlgeschlagen"
behauptet oder der Aufruf wiederholt wird. Siehe [[deploy-waiting-run-blocks-concurrency]].
```

```markdown
---
name: eigener-plan-derselben-sitzung-nicht-angewandt
description: Eine Reihenfolge, die man selbst gegen ein Problem geplant hat, muss beim zweiten Mal auch angewandt werden
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-09-01-merge-reihenfolge
---
Am 2026-09-01 wurde vormittags die Merge-Reihenfolge (#290 vor #287, dann EINE
Prod-Freigabe) ausdrücklich geplant, um einen Gate-Stau zu vermeiden — und
funktionierte. Nachmittags wurde #294 gemergt, während #292s Deploy schon am
Gate wartete: derselbe Stau, diesmal gebaut. Der Unterschied lag im Timing —
ein Run in der Bauphase wird abgeräumt, ein `waiting`-Run nicht.

**Why:** Der Plan war richtig; er wurde nur nicht als Regel behandelt.
**How to apply:** Vor jedem Merge, während ein Deploy-Run offen ist: erst
`gh run list --workflow=Deploy --limit 2` lesen. Steht dort ein `waiting`,
zuerst dessen Gate beantworten. Siehe [[deploy-waiting-run-blocks-concurrency]].
```

**adr_candidates:** keine. Kein Befund dieser Sitzung verlangt eine Architekturentscheidung; die offene fachliche Frage (Modell je Gütestufe) ist eine Admin-Änderung ohne Deploy, kein ADR.

## 7. Maßnahmen

### 🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | `#286` schließen | ausschreibungs-hub | #286 | 🟢 | Schließen (du) |
| M2 | Falsifikation für #8/#9 freigeben | — | — | 🟢 | ~110k Tokens (du) |
| M3 | `classifier`-Fehlerwert entscheiden | ausschreibungs-hub | #293 | 🟢 | Entscheiden (du) |

### 🔵 Offen — ich kann sofort

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M4 | Gate `untested-tool-module-green-gate` ausweiten | platform | — | 🔵 | Scanner auf Gate-Tests (ich) |
| M5 | Gate für `issue-open-after-its-fix-merged` bauen | platform | — | 🔵 | ×2, ohne Gate (ich) |
| M6 | Zwei Memory-Kandidaten verankern | — | — | 🔵 | Nach deinem OK (ich) |

## 8. Nicht verifiziert (Restlücken)

**getan:** Phase 1 (Collect) mit `git fetch origin main` und Lesen aus dem Ref; Phase 2 (Find) über drei Dimensionen; Phase 4 mit beiden Pflicht-Werkzeugen (`retro_kpis.py`, `gate_wirkung.py`); Phase 5a Rückfall-Klasse benannt.

**angenommen:** dass die Befunde 8 und 9 zutreffen. Beide stützen sich auf das Sitzungs-Transkript, nicht auf ein `gh`-Artefakt — bei #8 ist die Abwesenheit einer Freigabe die Behauptung, und eine Abwesenheit ist die teuerste Belegform.

**nicht verifizierbar ohne Freigabe:** Phase 3 (Falsifikation) ist **nicht gelaufen**. Die Systemanweisung dieser Sitzung untersagt Subagenten ohne ausdrücklichen Wunsch des Owners; der Skill sieht dafür den Weg vor, inline zu finden und die Bewertungsbefunde mit ihrer Zahl vorzulegen. Das sind Befunde **8 und 9**, gemessene Kosten **~55k Tokens je eng geführtem Skeptiker**, zusammen **~110k**. Damit ist **Regel 1 (Richter ≠ Angeklagter) für die Find-Phase gebrochen** — dieser Report beurteilt eine Sitzung aus ihrem eigenen Kontext. Die sieben kommandobelegten Befunde sind davon weniger betroffen (ihre Belege wurden in diesem Turn unabhängig neu gezogen), die zwei Bewertungsbefunde vollständig.

**Phase 5 (Meta-Self-Review) ist ebenfalls nicht gelaufen** — derselbe Grund.

**offen geblieben:** ob `#286` bewusst offen bleiben sollte (M1); ob der Auto-Mode-Klassifizierer öfter gegen ausdrückliche Owner-Freigaben feuert, als es dieser Sitzung entspricht — billigster Check wäre eine Auswertung über mehrere Sitzungen, hier nicht möglich.
