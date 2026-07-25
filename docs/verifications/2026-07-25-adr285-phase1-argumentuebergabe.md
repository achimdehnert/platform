# ADR-285 Phase-1-Pilot — Argument-Übergabe in der Skills-Lane

**Datum:** 2026-07-25
**Anlass:** [#1416](https://github.com/achimdehnert/platform/issues/1416) (Falsifikations-Gate für ADR-285 D2/D3)
**Ergebnis:** `$ARGUMENTS` wird in der Skills-Lane **substituiert** — D2 technisch bestätigt.
**Status des ADR:** bleibt `proposed`; zwei Acceptance-Kriterien aus §9 sind noch offen (siehe unten).

---

## 1. Der Test

`skills/issues-offen/SKILL.md` wurde mit dem Argument `platform-TESTMARKER-4711` aufgerufen. Der Marker ist bewusst ein String, der nirgends im Repo vorkommt — ein Treffer kann also nicht aus dem Dateiinhalt stammen.

**Quelle** (`skills/issues-offen/SKILL.md`, Z. 32 + 38):

```
`$ARGUMENTS`:
- **kein `org:`-Präfix** → Single-Repo-Modus …

1. Repo bestimmen: `$ARGUMENTS` → `<repo>`; sonst Basename von `git rev-parse --show-toplevel`.
```

**Was der Skill-Body beim Aufruf tatsächlich enthielt:**

```
`platform-TESTMARKER-4711`:
- **kein `org:`-Präfix** → Single-Repo-Modus …

1. Repo bestimmen: `platform-TESTMARKER-4711` → `<repo>`; sonst Basename von `git rev-parse --show-toplevel`.
```

Substitution an **beiden** Fundstellen. Lane-Beleg aus dem Footer derselben Ausgabe:

```
<!-- MANAGED-BY: platform/tools/cc-skill-dist · generated=true ·
     source=skills/issues-offen/SKILL.md · source_commit=9371148f567d · … -->
```

`source=skills/…/SKILL.md` ⇒ die Ausgabe kam aus der **Skills-Lane**, nicht aus `commands`.

Der Skill-Body wurde nur beobachtet, **nicht ausgeführt** (keine Issue-Triage, keine PRs).

## 2. Was das belegt — und was nicht

| | Status |
|---|---|
| `$ARGUMENTS` wird im Skill-Body durch das übergebene Argument ersetzt | ✅ verifiziert |
| Die Ausgabe stammt aus der Skills-Lane (Footer) | ✅ verifiziert |
| Argument-Übergabe über den **Skill-Aufruf mit `args`** | ✅ verifiziert |
| Argument-Übergabe über den **getippten Slash-Befehl** `/issues-offen <arg>` | ❌ **nicht verifiziert** |

Die letzte Zeile ist die ehrliche Lücke. §9 verlangt „Slash-Aufruf **und** Argument-Übergabe". Verifiziert ist der programmatische Pfad; ob der CLI-Parser beim getippten `/issues-offen xyz` dieselbe Substitution erzeugt, ist damit **nicht** gezeigt — diesen Pfad kann nur der Owner auslösen.

**Billigster verbleibender Check:** einmal `/issues-offen platform-TESTMARKER-4711` tippen und prüfen, ob der Marker im geladenen Body steht.

## 3. Drei Befunde, die die Pilot-Anlage aus #1416 verändern

### 3.1 Der designierte Testfall enthält den Testgegenstand nicht

#1416 benennt `teste-repo` als „den eigentlichen `$ARGUMENTS`-Fall". `.windsurf/workflows/teste-repo.md` enthält aber **kein literales `$ARGUMENTS`** — das Argument wird dort in Prosa beschrieben (`/teste-repo xyz` → explizites Repo, Z. 8–9 / 28–30). Eine 1:1-Migration hätte also gar keinen Substitutions-Test erzeugt.

Der tatsächliche Testgegenstand — `issues-offen` — war zum Zeitpunkt der Issue-Erstellung **bereits migriert und live**. Der Pilot war damit faktisch schon gelaufen, nur nicht gemessen.

### 3.2 `workflow-index` lässt sich nicht ohne Checker-Fix migrieren

Getestet mit einer simulierten Skills-Lane, in der `workflow-index` migriert ist:

```
$ python3 tools/check_workflow_index.py --skills-dir <sim>
FAIL: folgende Skills fehlen im workflow-index.md (als /<name>):
  - workflow-index
exit-code: 1

# Gegenprobe, heutiger Ist-Zustand:
$ python3 tools/check_workflow_index.py
OK: alle 54 verteilten Skills sind im workflow-index.md referenziert.
exit-code: 0
```

Zwei unabhängige Ursachen:

1. **Lane 2 hat keinen Selbst-Skip.** Lane 1 überspringt die Index-Datei selbst (`if name == index_name: continue`, `check_workflow_index.py`). Die Skills-Schleife darunter hat diese Zeile nicht — `workflow-index` würde sich selbst als „fehlt im Index" melden, denn der Index listet sich nicht selbst.
2. **Der Default-Pfad zeigt auf die Quelle.** `--index` ist auf `.windsurf/workflows/workflow-index.md` vorbelegt, und CI ruft `python3 tools/check_workflow_index.py` **ohne Argumente** (`tools-tests.yml`). Wandert die Datei, läuft der Check in einen `FileNotFoundError`.

Beides gehört in **denselben** PR wie die Migration — sonst bricht `tools-tests.yml`.

### 3.3 Kriterium 2 ist heute rot, unabhängig vom Pilot

`doctor.py`-Round-Trip beider Lanes:

| Lane | kanonisch | DRIFT-SCORE |
|---|---|---|
| `skills` | 4 | **0** ✅ |
| `commands` | 51 | **1** ❌ |

Der eine Befund: `[copy-stale] klickdummy-pgvector-sync.md — Kopie ≠ Quelle (veraltet)`. Ursache ist der Merge von [#1408](https://github.com/achimdehnert/platform/pull/1408) **von heute**, der genau diese Workflow-Datei geändert hat; die verteilte Kopie unter `~/.claude/commands/` ist seitdem veraltet.

Das ist kein Pilot-Problem, sondern der normale Nachlauf eines Merges — aufzulösen nur durch eine **gegatete** Live-Regeneration der `commands`-Lane (Maschinen-Installation, Owner-Freigabe).

## 4. Stand der Acceptance-Kriterien (ADR-285 §9)

| # | Kriterium | Stand |
|---|---|---|
| 1 | Pilot: ≥3 Commands migriert, ≥1 mit `$ARGUMENTS`, 1 mit `model:`; Slash-Aufruf + Übergabe verifiziert | 🟡 **teilweise** — 4 migriert, `$ARGUMENTS` bestätigt, `model:` gegenstandslos (alle 3 `model:`-Workflows sind `distribute: false`, #1416); **Slash-Pfad offen** |
| 2 | `doctor.py`-Round-Trip beider Lanes DRIFT 0 | ❌ **rot** — `commands` = 1 (stale Kopie aus #1408), Fix ist gegatet |
| 3 | `$ARGUMENTS`-Ersatzmechanismus + `model:`-Ersatz dokumentiert | ✅ **dieses Dokument** + #1416 (`model:` gegenstandslos begründet) |
| 4 | Acceptance-Bündel (ADR-229 → `superseded`, ADR-230 amendiert, `claude-skills.md`) | ⬜ erst bei Acceptance |
| 5 | D5-Rückbau-Gate als prüfbare Prozedur | ⬜ offen |

**Kill-Kriterium (§8) greift nicht.** Es fordert, dass *weder* `skills` *noch* `commands` die Artefakte ohne Funktionsverlust tragen kann. `skills` trägt `$ARGUMENTS` nachweislich; `model:` ist bei distribuierten Commands nicht im Spiel. Der ADR ist damit **nicht** zurückzuziehen.

## 5. Was als Nächstes nötig ist — beides Owner-Aktionen

1. **Slash-Pfad prüfen:** einmal `/issues-offen platform-TESTMARKER-4711` tippen (schließt Kriterium 1).
2. **`commands`-Lane live regenerieren:** `generate.py --kind commands … --allow-live` (schließt Kriterium 2). Maschinen-Installation ⇒ Freigabe.

Danach sind 1–3 grün und der Acceptance-PR (Kriterium 4) + die D5-Prozedur (Kriterium 5) sind die verbleibende Arbeit.

**Bewusst nicht gemacht:** keine weiteren Skills nach `skills/` migriert. Der Bulk-Move ist Phase 2 und laut #1416 „erst nach grünem Pilot" — vorzuziehen wäre genau die „Entscheidung ≠ Rollout"-Verwechslung, vor der ADR-285 selbst warnt.
