# ADR-285 Phase-1-Pilot — Argument-Übergabe in der Skills-Lane

**Datum:** 2026-07-25
**Anlass:** [#1416](https://github.com/achimdehnert/platform/issues/1416) (Falsifikations-Gate für ADR-285 D2/D3)
**Ergebnis:** `$ARGUMENTS` wird in der Skills-Lane **substituiert** — D2 technisch bestätigt, auf **beiden** Aufrufwegen (programmatisch und getippt).
**Status des ADR:** bleibt `proposed`; §9-Kriterien 1–3 sind grün, 4 und 5 stehen aus (siehe unten).

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

### 1.1 Nachtrag: der getippte Slash-Befehl (2026-07-25, 12:13 UTC)

Der oben als offen ausgewiesene CLI-Pfad ist inzwischen gemessen. Der Owner hat in einer
frisch gestarteten Session `/issues-offen platform-TESTMARKER-4711` **getippt** —
derselbe Marker, dieselbe Prüffrage, aber der Weg über den Slash-Parser statt über den
programmatischen Skill-Aufruf.

Ergebnis identisch: der geladene Body enthielt `platform-TESTMARKER-4711` an **beiden**
`$ARGUMENTS`-Fundstellen (Verwendungs-Block und Step 0.1), Footer wieder
`source=skills/issues-offen/SKILL.md`. Damit liefern beide Aufrufwege dieselbe
Substitution.

**Verifikationsstand:** Werkzeugversion `2.1.220` (`claude --version`, abgerufen
2026-07-25 12:17 UTC), Messung ~12:13 UTC desselben Tages. Für die Erstmessung oben
wurde **keine** Version festgehalten — ob beide Aufrufwege auf exakt derselben
Werkzeugversion liefen, ist damit nicht belegt. Für die Aussage „beide Wege
substituieren" ist das unschädlich: jeder Weg ist für sich auf einer benannten
Version gemessen.

**Abgrenzung — was hier ausgeführt wurde:** anders als bei der Erstmessung blieb es nicht
beim Beobachten. Step 0 des Skills (Repo-Auflösung) lief real und **brach ab**: der Marker
ist bewusst kein existierendes Repo, weder lokal noch in einer der drei Orgs
(`achimdehnert`, `ttz-lif`, `meiki-lra`, je „Could not resolve to a Repository"). Der Lauf
endete damit vor Phase 1 — keine Issue-Triage, keine Branches, keine PRs. Der Marker
erfüllt hier zwei Zwecke zugleich: er kann nicht aus dem Dateiinhalt stammen, **und** er
lässt den Skill folgenlos auslaufen.

## 2. Was das belegt — und was nicht

| | Status |
|---|---|
| `$ARGUMENTS` wird im Skill-Body durch das übergebene Argument ersetzt | ✅ verifiziert |
| Die Ausgabe stammt aus der Skills-Lane (Footer) | ✅ verifiziert |
| Argument-Übergabe über den **Skill-Aufruf mit `args`** | ✅ verifiziert |
| Argument-Übergabe über den **getippten Slash-Befehl** `/issues-offen <arg>` | ✅ verifiziert (§1.1, Nachtrag 12:13 UTC) |

Die letzte Zeile war die ehrliche Lücke dieses Dokuments und ist mit dem Nachtrag in §1.1 geschlossen. §9 verlangt „Slash-Aufruf **und** Argument-Übergabe" — beide Aufrufwege liefern dieselbe Substitution, gemessen mit demselben Marker.

**Was weiterhin nicht gezeigt ist:** dass die Substitution für *jede* Argumentform trägt (mehrere Wörter, `$1`/`$2`, benannte Argumente). Gemessen ist ein einzelnes Argument ohne Leerzeichen — genau der Fall, den §9 verlangt, nicht mehr.

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

### 3.3 Kriterium 2 war rot, unabhängig vom Pilot — inzwischen aufgelöst

`doctor.py`-Round-Trip beider Lanes:

| Lane | kanonisch | DRIFT-SCORE |
|---|---|---|
| `skills` | 4 | **0** ✅ |
| `commands` | 51 | **1** ❌ |

Der eine Befund: `[copy-stale] klickdummy-pgvector-sync.md — Kopie ≠ Quelle (veraltet)`. Ursache ist der Merge von [#1408](https://github.com/achimdehnert/platform/pull/1408) **von heute**, der genau diese Workflow-Datei geändert hat; die verteilte Kopie unter `~/.claude/commands/` ist seitdem veraltet.

Das ist kein Pilot-Problem, sondern der normale Nachlauf eines Merges — aufzulösen nur durch eine **gegatete** Live-Regeneration der `commands`-Lane (Maschinen-Installation, Owner-Freigabe).

**Nachtrag (2026-07-25, 12:16 UTC): erledigt.** Die Regeneration ist mit Owner-Freigabe
gelaufen; nachgemessen sind jetzt **beide** Lanes sauber:

| Lane | kanonisch | DRIFT-SCORE | dangling |
|---|---|---|---|
| `skills` | 4 | **0** ✅ | 0 |
| `commands` | 51 | **0** ✅ (`copy-stale=0`, `fehlend=0`, `extra=0`) | 0 |

Damit ist §9-Kriterium 2 grün. Die Messung stammt aus diesem Nachtrag
(`doctor.py --kind skills|commands`), die Freigabe der Live-Regeneration aus der
vorangegangenen Session — der Regenerationslauf selbst ist hier **nicht** nachgeprüft,
nur sein Ergebnis.

## 4. Stand der Acceptance-Kriterien (ADR-285 §9)

| # | Kriterium | Stand |
|---|---|---|
| 1 | Pilot: ≥3 Commands migriert, ≥1 mit `$ARGUMENTS`, 1 mit `model:`; Slash-Aufruf + Übergabe verifiziert | ✅ **grün** — 4 migriert, `$ARGUMENTS` auf beiden Aufrufwegen bestätigt (§1.1), `model:` gegenstandslos (alle 3 `model:`-Workflows sind `distribute: false`, #1416) |
| 2 | `doctor.py`-Round-Trip beider Lanes DRIFT 0 | ✅ **grün** — nachgemessen 2026-07-25 12:16 UTC: `skills` 0, `commands` 0 (siehe §3.3) |
| 3 | `$ARGUMENTS`-Ersatzmechanismus + `model:`-Ersatz dokumentiert | ✅ **dieses Dokument** + #1416 (`model:` gegenstandslos begründet) |
| 4 | Acceptance-Bündel (ADR-229 → `superseded`, ADR-230 amendiert, `claude-skills.md`) | ⬜ erst bei Acceptance |
| 5 | D5-Rückbau-Gate als prüfbare Prozedur | ⬜ offen |

**Kill-Kriterium (§8) greift nicht.** Es fordert, dass *weder* `skills` *noch* `commands` die Artefakte ohne Funktionsverlust tragen kann. `skills` trägt `$ARGUMENTS` nachweislich; `model:` ist bei distribuierten Commands nicht im Spiel. Der ADR ist damit **nicht** zurückzuziehen.

## 5. Was als Nächstes nötig ist

Die beiden ursprünglich hier stehenden Owner-Aktionen sind **beide erledigt**:

1. ~~Slash-Pfad prüfen~~ → getippt am 2026-07-25 12:13 UTC, Kriterium 1 grün (§1.1).
2. ~~`commands`-Lane live regenerieren~~ → mit Freigabe gelaufen, beide Lanes DRIFT 0, Kriterium 2 grün (§3.3-Nachtrag).

**Kriterien 1–3 sind damit grün.** Verbleibende Arbeit für den Accept:

3. **Acceptance-Bündel** (Kriterium 4): ADR-229 → `superseded`, ADR-230 REC-3 amendieren, `claude-skills.md` nachziehen.
4. **D5-Rückbau-Gate** (Kriterium 5): die Rückbau-Prozedur als prüfbare Schrittfolge festschreiben.

Der Bulk-Move weiterer Skills (Phase 2) bleibt davon getrennt und ist laut #1416 erst nach dem Accept dran.

**Bewusst nicht gemacht:** keine weiteren Skills nach `skills/` migriert. Der Bulk-Move ist Phase 2 und laut #1416 „erst nach grünem Pilot" — vorzuziehen wäre genau die „Entscheidung ≠ Rollout"-Verwechslung, vor der ADR-285 selbst warnt.
