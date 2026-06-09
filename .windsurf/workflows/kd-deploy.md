---
description: Klickdummy/Genesor → iil.pet deployen (Mechanik, Sonnet-tauglich). NICHT für App-Deploys (→ /deploy).
mode: write
---

# /kd-deploy — Klickdummy auf iil.pet deployen

> **Arbeitsteilung (Owner-Wunsch):** *Konzept + schärfen + Spec final + PR-Approval*
> macht der Mensch/Opus **vorher**. `/kd-deploy` ist die **deterministische Mechanik
> danach** — gemacht, um an Sonnet delegiert zu werden. Kein Urteil über KD-Inhalt.
>
> **Wann:** Eine genehmigte KD-Spec (PR approved oder gemergt) soll live auf iil.pet.
> **Wann NICHT:** App-/Service-Deploy (bfagent, cad-hub …) → `/deploy`. Inhaltliche
> Frage am KD (was rein/raus) → zurück an Opus/Mensch, NICHT hier entscheiden.

## Verwendung

```
/kd-deploy <repo> <kd> [renderer-PR#]
# z.B. /kd-deploy risk-hub gefahrstoff-kataster
#      /kd-deploy risk-hub gefahrstoff-kataster 52   (wenn ein iil-klickdummy-Renderer-PR mitmuss)
```

`<repo>` = Consumer-Repo (achimdehnert/<repo>); `<kd>` = Spec-Dir unter `klickdummy/<kd>/`.
Owner/Pfade NIE hardcoden — aus git-Remote bzw. `project-facts.md` ableiten.

## Erdung (einmal, vor Schritt 1)

- `GH=${GITHUB_DIR:-$HOME/github}`; `LINEAGE=$GH/iil-klickdummy/src`;
  `PORTAL=$GH/iil-pet-portal`; Regen-Script `$PORTAL/scripts/regen-genesor-main.sh`.
- Live-Verify: `~/.claude/bin/verify-iilpet.sh <pfad>` (geht DURCH Cloudflare Access via
  Service-Token; iil.pet ist sonst eine Login-Wand — `curl` allein sieht nur Login).
- Der Regen nutzt den **lokalen** `$LINEAGE`-Working-Tree als Renderer **und** scannt
  **origin/main**-Worktrees der Consumer-Repos. Beides muss den gewollten Stand haben.

## Schritte (mit Gates)

**1. Lokale Invarianten grün** (vor allem anderen):
```
SCHEMA=$LINEAGE/iil_klickdummy/schemas/screens-spec.schema.json
SPEC=$GH/<repo>/klickdummy/<kd>/screens-spec.yaml
PYTHONPATH=$LINEAGE python3 -m iil_klickdummy.check_i1 "$SPEC:$SCHEMA"   # I1 → PASS
PYTHONPATH=$LINEAGE python3 -m iil_klickdummy.check_i2 "$SPEC:$SCHEMA"   # I2 → PASS
PYTHONPATH=$LINEAGE python3 -m iil_klickdummy.check_flow $GH/<repo>      # Flow → PASS
# Falls klickdummy/stories/ existiert: check_stories ebenfalls.
```
Eines rot → **STOP**, zurück an Opus/Mensch (Spec-Problem, kein Deploy-Problem).

**2. PR-CI-Gate** (für jeden beteiligten PR — KD-PR + ggf. Renderer-PR):
```
gh pr checks <PR#>          # alle REQUIRED contexts grün?
```
- **Bekannter Flaky:** `Staging Gate (e2e)` rot mit DB-Container-Fehler
  („dependency db failed to start" / „container … exited (1)") → **genau 1×**
  `gh run rerun <run-id> --failed`, dann erneut pollen.
- e2e **zweimal** rot, ODER ein anderer Check rot → **STOP** (nicht Infra, eskalieren).

**3. Mergen** (Renderer-PR zuerst, dann KD-PR — Reihenfolge wichtig, KD hängt am Renderer):
```
gh pr merge <renderer-PR#> --squash --delete-branch    # falls vorhanden
gh pr merge <kd-PR#>       --squash --delete-branch
```

**4. Lokale mains syncen** (Regen liest sie):
```
git -C $GH/iil-klickdummy switch main && git -C $GH/iil-klickdummy pull --ff-only   # falls Renderer-PR
git -C $GH/<repo> fetch origin main && git -C $GH/<repo> switch main && git -C $GH/<repo> reset --hard origin/main
```
`reset --hard origin/main` nur, wenn lokal KEINE eigenen main-Commits (nach Merge der Fall).

**5. A3-Scope prüfen** (nur spec-getriebene KDs, die den Zentral-Render/Story-Banner brauchen):
In `$PORTAL/scripts/regen-genesor-main.sh` muss `<kd>` in `A3_ONLY[<repo>]` stehen,
SONST bleibt ein evtl. gebackener Stand. Fehlt der Eintrag und der KD ist neu spec-driven
→ ergänzen. **Neuen Repo in `A3_REPOS` aufnehmen ist eine Scope-Entscheidung → STOP, zurück an Opus.**

**6. Regen:**
```
bash $PORTAL/scripts/regen-genesor-main.sh   # endet mit Diff-Gate (kein Push)
```
Erwartung im Log: `✓ A3 <repo>: N Screen(s) …` mit `<kd>` enthalten.

**7. Marker-Check der deployten Datei** (NICHT „Datei existiert" — Lehre
`smoke-test-marker-presence-gap`: `"x" in html` fängt keine Platzierungs-Bugs):
```
F=$PORTAL/kd/<repo>/klickdummy/<kd>/index.html
# Erwartete domänen-echte Werte + Screen-Anzahl zählen (grep -oc), >0 verlangen.
```
Marker fehlen/0 → **STOP** (Regen hat nicht gegriffen, A3/Spec prüfen).

**8. Commit + Push** (= R2/GitHub-Pages-Deploy):
```
git -C $PORTAL add genesor/ kd/ scripts/regen-genesor-main.sh
git -C $PORTAL commit -m "deploy(genesor): <repo> <kd> — …"
git -C $PORTAL push origin main
```

**9. Deploy-Run abwarten:**
```
gh run list -R iilgmbh/iil-pet-portal --limit 1   # „GH Pages Deploy (R2)" → success
```

**10. Live-Verify durch Cloudflare Access** (der eigentliche Beweis):
```
~/.claude/bin/verify-iilpet.sh /kd/<repo>/klickdummy/<kd>/index.html | grep -oc "<erwarteter Marker>"
# >0 UND keine Login-Wand ("Cloudflare Access"/"Sign in" → 0).
```
Marker live 0 → **STOP**, im Bericht als nicht-verifiziert ausweisen.

## Harte STOPs (zurück an Opus/Mensch)

- Lokale Invariante rot (Schritt 1) — Spec-Problem.
- e2e 2× rot oder anderer Check rot (Schritt 2) — kein Flaky.
- Neuer `A3_REPOS`-Eintrag nötig (Schritt 5) — Scope-Entscheidung.
- Marker fehlen pre-push (7) oder live (10) — Deploy nicht bewiesen.
- Jede inhaltliche KD-Frage — `/kd-deploy` urteilt nicht über Inhalt.

## Bericht (Action-Board, am Ende)

| # | Schritt | Status | Beleg |
|---|---|---|---|
| 1 | i1/i2/flow | ✅/⛔ | PASS/FAIL |
| 2 | PR-CI-Gate | ✅/⛔ | (flaky-rerun?) |
| 3–4 | Merge + main-sync | ✅ | commit-shas |
| 6 | Regen | ✅ | „A3 …: N Screens" |
| 7 | Marker pre-push | ✅ | counts |
| 8–9 | Push + R2-Deploy | ✅ | run success |
| 10 | Live-Verify | ✅ | marker-count, keine Login-Wand |

Live-URL: `https://iil.pet/kd/<repo>/klickdummy/<kd>/`.

## Anti-Patterns

- ❌ Inhaltlich am KD entscheiden (was rein/raus) — das ist Opus/Mensch.
- ❌ „Datei da & rendert" als Erfolg werten — Marker zählen (pre-push UND live).
- ❌ e2e-DB-Flaky mehr als 1× blind rerunnen / oder einen *echten* roten Check als Flaky abtun.
- ❌ Neuen Repo in `A3_REPOS`/Owner/Pfade hardcoden statt aus Remote/`project-facts.md`.
- ❌ Pushen, wenn der User „nicht deployen" sagt oder ein Review offen ist.

## Changelog

- 2026-06-03: Initial. Destilliert aus dem manuellen risk-hub:gefahrstoff-kataster-Deploy
  (iil-klickdummy#52 Renderer + risk-hub#153 KD → Regen → R2 → Live-Verify). Gates:
  i1/i2/flow, e2e-Flaky-1×-Rerun, A3-Scope, Marker-Präsenz pre-push+live. Promotion in
  den Platform-Kanon (`platform/.windsurf/workflows/` + cc-skill-dist): mit diesem PR erfolgt.
