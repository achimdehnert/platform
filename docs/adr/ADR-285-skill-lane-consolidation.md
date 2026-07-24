---
status: proposed
decision_date: 2026-07-24
deciders: Achim Dehnert
domains: [tooling, dx, drift-prevention, governance]
supersedes: [ADR-229]
amends: [ADR-230, claude-skills.md]
related: [ADR-230, ADR-229, ADR-280, ADR-258]
tags: [skills, commands, workflows, distribution, claude-code, windsurf, lane-consolidation, cross-repo]
---

# ADR-285: Skill-Lane-Konsolidierung — eine Lane, eine Quelle, ein Ziel

| Attribut | Wert |
|---|---|
| **Status** | Proposed (Richtung `skills` steht unter Pilot-Falsifikation, §5/§9) |
| **Scope** | Platform-wide (Tooling/DX, Skill-/Command-Distribution) |
| **Datum** | 2026-07-24 |
| **Autor** | Achim Dehnert |
| **Supersedes** | ADR-229 (`.windsurf`-Distribution — Coding-Tool-Prämisse tot; nur Schritt-1-Untrack bleibt gültig) |
| **Amends** | ADR-230 §Verteilung + REC-3-Watchpoint · Policy `claude-skills.md` |
| **Anker-Issue** | [#1287](https://github.com/achimdehnert/platform/issues/1287) (Owner-Weisung 2026-07-21) |

> **Status proposed — „Entscheidung ≠ Rollout" (ADR-211/ADR-230-Muster).**
> Die **Invariante** (D1: genau EINE Lane, keine Parallelexistenz) ist die
> ratifizierte Owner-Weisung und steht fest. Die **Richtung** (D2: konsolidieren
> auf `skills/`) ist ein Vorschlag, dessen Tragfähigkeit der Phase-1-Pilot
> (§5, ein `$ARGUMENTS`-Command) **falsifizieren** kann — fällt er durch, kippt
> D2 auf „eine Lane, aber `commands`". Deshalb `proposed`, bis der Pilot grün ist.
> Der Bulk-Move (Phase 2) und der Rückbau der `commands`-Lane (Phase 3) laufen
> danach über das Rollout-Gate (§10), nicht mit der Ratifizierung dieses ADR.

## 1. Kontext

### 1.1 Ausgangslage — zwei parallele Lanes
Skill-artige Artefakte existieren derzeit in **zwei** parallelen Lanes mit zwei
Quellverzeichnissen und zwei Live-Zielen (gemessen 2026-07-24, `doctor.py`):

| | Lane `commands` | Lane `skills` |
|---|---|---|
| Quelle | `.windsurf/workflows/*.md` | `skills/<name>/SKILL.md` |
| Anzahl Quelle | 55 | 4 |
| Live-Ziel | `~/.claude/commands/` | `~/.claude/skills/` |
| Anzahl live | 51 | 4 |
| DRIFT-SCORE | 0 | 0 |

Beide Lanes sind je für sich sauber (generiert, `MANAGED-BY`-Footer, `manifest.json`,
DRIFT-SCORE 0). Das Problem ist **nicht** Drift *innerhalb* einer Lane, sondern die
**Existenz zweier Lanes** — Owner-Weisung 2026-07-21: „keine Parallelexistenz,
weder `.claude` vs `.windsurf` noch `commands` vs `skills`".

### 1.2 Warum das ein echtes Problem ist (nicht nur Kosmetik)
- **Das Quellverzeichnis heißt nach einem Tool, das dafür nicht mehr benutzt wird.**
  `.windsurf/workflows/` speist zu 100 % `~/.claude/commands/` (Claude Code). Laut
  ADR-230 wird Windsurf nicht mehr zum Coden genutzt (nur ADR-Review). Der Name ist
  ein Tool-Leak — genau der, den ADR-230 §2 REC-3 als „Phase-2-Watchpoint" bereits
  vermerkte, aber zurückstellte.
- **Die Lane-Wahl für einen neuen Skill ist unentscheidbar.** Anlass des Anker-Issues:
  beim Rebase von #1013 war nicht bestimmbar, in welche Lane ein neuer Skill gehört.
- **Am Nutzungsort ist der Split unsichtbar.** Der Harness listet beide Lanes in
  **einer** Skill-Liste (`antwort-modus-schablone` aus `skills` neben `/next`,
  `/adr` aus `commands`) — der Split kostet Pflegeaufwand, ohne beim Aufruf einen
  Nutzen zu stiften.
- **Die ADR-Basis ist halb-beschlossen.** ADR-230 (CC-first) ist `accepted`, aber
  ADR-229 (`.windsurf`-Distribution) steht seit 2026-05-30 auf `proposed` und ist
  durch die „Windsurf ist kein Coding-Tool"-Basis faktisch tot.

### 1.3 Gemessene Migrationsreibung (aus #1287, nicht geschätzt)
- **8** Workflows nutzen `$ARGUMENTS`/`$1` — Textsubstitution ist ein
  Slash-Command-Feature; Agent Skills bekommen `args` über das Skill-Tool. Diese 8
  brauchen echte Überarbeitung, nicht nur `git mv`.
- **3** Workflows setzen `model:` im Frontmatter — Skill-Frontmatter kennt
  `name`/`description`/`metadata`. Ersatzmechanismus offen.
- **5** Workflows tragen `windsurf-review` (Sub-Lane via `tools/cc-skill-dist/windsurf-subset.py`).
  `grep -rn 'windsurf-subset' .github/workflows/` → **0 Treffer**: kein CI-Gate,
  kein Automatismus — die Sub-Lane ist faktisch tot.
- `allowed-tools:` / `argument-hint:`: **0** Treffer — keine Reibung.

## 2. Entscheidung

### D1 — Invariante: genau EINE Lane (fest, Owner-Weisung)
Es gibt genau **eine** Distributions-Lane für Skill-artige Artefakte: **ein**
Quellverzeichnis, **ein** Live-Ziel, **ein** Generator-`--kind`. Keine
Parallelexistenz. Diese Invariante ist unabhängig von der Richtung (D2) und steht
mit diesem ADR fest.

### D2 — Richtung: konsolidieren auf `skills/` (Vorschlag, pilot-gegatet)
Die verbleibende Lane ist **`skills/<name>/SKILL.md`** (tool-neutral). Konkret:
- Das **Quellverzeichnis `.windsurf/workflows/` entfällt als Skill-Quelle** — sein
  Name ist ein Windsurf-Tool-Leak, den ADR-230 REC-3 schon markiert hat. Damit ist
  D2 die **Ausführung** dieses Watchpoints.
- Die **Live-Lane `~/.claude/commands/` wird zurückgebaut** (gegatet, D5).
- Die 51 Commands werden zu `skills/<name>/SKILL.md` migriert.

**Warum `skills` und nicht `commands`:** (a) tool-neutraler Name; (b) `skills` ist
das vom Harness nativ geladene Format (ADR-280 §8.1 hat 4 Piloten dort real
verifiziert); (c) `commands`/Slash-Command ist das Windsurf-/Legacy-Format, dessen
Quellverzeichnis wir ohnehin umbenennen müssten. Die Richtung ist aber **kein
Big-Bang** — sie steht unter D3.

### D3 — Falsifikations-Gate: Phase-1-Pilot (hart)
Der Phase-1-Pilot (§5) migriert **3 repräsentative Commands, davon mindestens einer
mit `$ARGUMENTS`**, nach `skills/` und verifiziert Slash-Aufruf **und
Argument-Übergabe** in einer echten Session. **Besteht der Pilot nicht** (die
`$ARGUMENTS`- oder `model:`-Semantik lässt sich nicht ohne Funktionsverlust auf
Skills abbilden), dann kippt D2 auf „eine Lane, aber `commands`" — die Invariante D1
bleibt, nur das Ziel-Format ändert sich. Bis der Pilot grün ist, bleibt dieser ADR
`proposed`. Der Pilot ist der Falsifikationstest, nicht die Bestätigung einer
schon getroffenen Annahme.

### D4 — Windsurf-Review-Sub-Lane: einstellen
Die 5 `windsurf-review`-Einträge + `windsurf-subset.py` werden **eingestellt**, nicht
aus der neuen Quelle weitergeneriert. Begründung: (a) kein CI-Gate referenziert sie
(§1.3, 0 Treffer) — sie ist bereits tot; (b) ADR-230 nennt „Windsurf = generiertes
ADR-Subset", aber das betrifft das **ADR-Review-Subset**, nicht Skill-Distribution;
ADR-Review über Windsurf bleibt unberührt und braucht keine Skill-Lane.
*Reversibel:* fällt später ein echter Windsurf-Bedarf an, wird das Subset aus der
neuen `skills`-Quelle regeneriert (die Quelle ist tool-neutral, das ginge).

### D5 — Rückbau `~/.claude/commands/` ist gegatet
Ein zu früher Rückbau nimmt Nutzern **mitten in der Session 51 Slash-Commands** weg.
Der Rückbau (Phase 3) erfolgt **erst**, wenn (a) alle 51 als `skills/` migriert +
`doctor.py`-Round-Trip beider Lanes grün, und (b) pro Maschine bestätigt ist, dass
die Skills-Lane die Commands im `/`-Menü vollständig ersetzt (Muster: ADR-280 §8.1
Kriterium 6). Bis dahin laufen beide Live-Ziele parallel — das ist **kein** Verstoß
gegen D1, weil D1 die *Quell-/Lane-Struktur* meint, nicht das gegatete
Übergangsfenster des Live-Rückbaus (analog ADR-230 „Entscheidung ≠ Rollout").

## 3. Verhältnis zu ADR-229 und ADR-230

**ADR-229 → superseded (bei Acceptance dieses ADR).** ADR-229 („Kanonische
`.windsurf`-Distribution — Single Global Source") setzte Windsurf als Coding-IDE über
alle Repos voraus; seine Schritte 2–4 waren bereits 2026-05-30 als YAGNI
zurückgestellt. Mit D2 (Quellverzeichnis `.windsurf/workflows/` entfällt) ist die
Prämisse endgültig tot. **Gültig bleibt** ADR-229 Schritt 1 (Untrack/Cleanup der
per-Repo `.windsurf`-Mirror, ~32 Repos, `.gitignore`-regressionsgeschützt) — das war
nutzungsunabhängig richtig und wird von diesem ADR **nicht** rückgängig gemacht.

**ADR-230 → amended.** ADR-230 (CC-first Skill-Distribution) bleibt die tragende
Entscheidung; dieser ADR **löst dessen offenen REC-3-Phase-2-Watchpoint auf**
(„Windsurf-benannten Pfad in tool-neutralen `skills/`-Pfad umbenennen") und
präzisiert §Verteilung: das kanonische Quellverzeichnis ist `skills/<name>/SKILL.md`,
die `commands`-Lane wird gegatet zurückgebaut. ADR-230 §8 Rollout-Gate bleibt
gültig und wird um die Phasen aus §10 dieses ADR ergänzt.

## 4. Betrachtete Alternativen

| Option | Kern | Killshot | Verdikt |
|---|---|---|---|
| **A** Status quo — zwei Lanes | `commands` + `skills` parallel weiter | verstößt gegen Owner-Weisung 2026-07-21; Lane-Wahl bleibt unentscheidbar (#1013) | **Verworfen** |
| **B** Konsolidieren auf `commands` | eine Lane, aber Slash-Command-Format behalten | Quellverzeichnis heißt weiter `.windsurf/` (Tool-Leak, gg. ADR-230 REC-3); `skills` ist das nativ geladene Format | **Fallback** (nur falls D3-Pilot durchfällt) |
| **C** Konsolidieren auf `skills` | eine Lane, tool-neutral, natives Format | `$ARGUMENTS`/`model:`-Semantik muss abbildbar sein (8+3 Fälle) → **darum pilot-gegatet** | **Gewählt (proposed, D3)** |

## 5. Phasenplan (aus #1287, gestaffelt — Falsifikation vor Bulk)

- **Phase 0** *(dieser ADR)* — Entscheidung ratifizieren: ADR-285 (proposed),
  ADR-229-Supersede + ADR-230-Amendment + Policy-`claude-skills.md`-Anpassung werden
  **bei Acceptance** dieses ADR angewandt (nicht solange proposed — ein proposed ADR
  flippt keinen fremden ADR-Status).
- **Phase 1** *(Falsifikations-Gate, D3)* — Pilot: 3 repräsentative Commands (davon
  **einer mit `$ARGUMENTS`**, einer mit `model:`) nach `skills/` migrieren, Slash-
  Aufruf **und** Argument-/Model-Übergabe in einer echten Session verifizieren.
  Gate: `doctor.py`-Round-Trip beider Lanes grün.
- **Phase 2** *(nach grünem Pilot)* — Bulk-Move der restlichen Commands nach `skills/`,
  Quellverzeichnis raus aus `.windsurf/`. Generator-`--kind commands` entfällt.
- **Phase 3** *(gegatet, D5)* — Lane `commands` + `~/.claude/commands/` zurückbauen;
  `windsurf-subset.py` gemäß D4 entfernen.

**Warum kein Big-Bang:** Phase 1 ist der Falsifikationstest für Phase 2. Fällt der
Pilot durch, ändert das den Zuschnitt (Fallback B), nicht nur das Tempo.

## 6. Konsequenzen
- **Positiv:** eine Lane → Lane-Wahl für neue Skills eindeutig; tool-neutraler
  Quellname (kein Windsurf-Leak); halbe Pflegelast (ein Generator-`--kind`, ein
  `manifest.json`, ein `doctor`-Lauf); ADR-229 endlich aufgelöst; ADR-230 REC-3
  geschlossen.
- **Trade-offs:** einmalige Migration von 51 Commands, davon 8 mit echter
  `$ARGUMENTS`-Überarbeitung + 3 mit `model:`; gegateter Übergang mit zeitweise zwei
  Live-Zielen (D5).
- **Risiko R1:** `$ARGUMENTS`-Semantik nicht ohne Verlust abbildbar → D3-Pilot fängt
  das ab, Fallback B.
- **Risiko R2:** zu früher `commands`-Rückbau nimmt laufenden Sessions Slash-Commands
  → D5-Gate (pro-Maschine-Bestätigung wie ADR-280 §8.1 Krit. 6).
- **Nicht in Scope:** Inhalt/Governance der Skills selbst; ADR-Review über Windsurf
  (bleibt); die 4 bereits in `skills` pilotierten Einträge (ADR-280).

## 7. Offene Fragen aus #1287 — jetzt entschieden

| Offene Frage (#1287) | Entscheidung hier |
|---|---|
| Überleben alle 51 Commands als `skills/`? | **Pilot-gegatet (D3)** — nicht angenommen; 8×`$ARGUMENTS`+3×`model:` sind die Risikomenge, der Pilot deckt beide ab. |
| Schicksal der 5 `windsurf-review` / `windsurf-subset.py`? | **Einstellen (D4)** — tot (0 CI-Referenzen); ADR-Review über Windsurf bleibt unberührt; reversibel aus neuer Quelle. |
| Rückbau `~/.claude/commands/` auf N Maschinen? | **Gegatet (D5)** — erst nach vollständiger Migration + pro-Maschine-Bestätigung; kein Yank mitten in Sessions. |

## 8. Kill-Kriterium
Dieser ADR wird **zurückgezogen** (nicht `accepted`), falls der Phase-1-Pilot zeigt,
dass **weder** `skills` **noch** `commands` alle 51 Artefakte ohne Funktionsverlust
tragen kann (z. B. `$ARGUMENTS` *und* `model:` sind in keinem der beiden Formate
sauber abbildbar) — dann ist die Owner-Invariante D1 technisch nicht erfüllbar und
die Lage geht zurück an den Owner, nicht in einen erzwungenen Kollaps.

## 9. Acceptance Criteria (hart — `proposed` bis alle grün)
- [ ] **Phase-1-Pilot grün:** 3 Commands (≥1 mit `$ARGUMENTS`, 1 mit `model:`) als
  `skills/` migriert; Slash-Aufruf **und** Argument-/Model-Übergabe in einer echten
  Session verifiziert (Beleg: Session-ID + Skill-Footer).
- [ ] `doctor.py`-Round-Trip **beider** Lanes grün (DRIFT-SCORE 0) nach dem Pilot.
- [ ] `$ARGUMENTS`-Ersatzmechanismus (Skill-`args`) **und** `model:`-Ersatz
  dokumentiert — oder D2→B dokumentiert begründet.
- [ ] Bei Acceptance: ADR-229 → `superseded`, ADR-230 §Verteilung amendiert,
  `claude-skills.md` auf die eine Lane angepasst (im Acceptance-PR gebündelt).
- [ ] D5-Rückbau-Gate als prüfbare Prozedur festgehalten (pro-Maschine-Bestätigung).

## 10. Rollout-Gate (Entscheidung ≠ Rollout)
Ratifizierung dieses ADR = **Richtung + Invariante verbindlich**, nicht Rollout
abgeschlossen. Phase 1 (Pilot), Phase 2 (Bulk-Move) und Phase 3 (Rückbau) laufen
gegatet über #1287; Phase 2/3 zusätzlich unter dem Parallel-Session-Guard
(0.4-Runner) — ein Bulk-Move der Skill-Distribution, während fremde Sessions laufen,
wird auf ein Fenster ohne aktive Fremd-Sessions gelegt.

## 11. Referenzen
- Anker-Issue: [#1287](https://github.com/achimdehnert/platform/issues/1287) (Owner-Weisung 2026-07-21).
- ADR-230 (CC-first Skill-Distribution, accepted) — insb. §2 REC-3 Phase-2-Watchpoint.
- ADR-229 (`.windsurf`-Distribution, proposed → superseded durch diesen ADR; Schritt 1 gültig).
- ADR-280 §8.1 (Skills-Lane Live-Betrieb, 4 Piloten real verifiziert).
- ADR-258 (Hook-Distribution `~/.claude/hooks/managed`, gleiche Generator-Familie).
- Tooling: `tools/cc-skill-dist/{generate,doctor,windsurf-subset}.py`.
- Policy `~/.claude/policies/claude-skills.md` (wird bei Acceptance amendiert).

## 12. Changelog
- 2026-07-24: Initial (Proposed). Phase-0-Entscheidung für #1287 — Invariante D1
  (eine Lane) fest, Richtung D2 (`skills`) pilot-gegatet (D3), Sub-Lane einstellen
  (D4), Rückbau gegatet (D5). Supersedes ADR-229, amends ADR-230 (REC-3 aufgelöst).
