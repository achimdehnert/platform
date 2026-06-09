# Konzept: Platform-weite Stabilisierung von Session-Reflexion & Guardrails

> **Status:** Entwurf zur Diskussion · 2026-06-01 · Autor: Claude (Opus) + Achim
> **Umsetzungsstand (Minimal-Kern, AD-geschärft, 2026-06-01):**
> - Artefakt 1 (Verhaltensnormen: Scope-Checkpoint, `make test`, branch-check) → `~/.claude/CLAUDE.md` House Rules
> - Artefakt 2 (`~/.claude` als dotfiles-git, Allowlist-gitignore) → lokal versioniert
> - Artefakt 3 (`gen_make_test_pg.py`, profil-bewusst, dry-run-Default) → platform PR #366
> - Pilot: dev-hub `make test` (PR #68) + evidence-claim-Scanner (Stop-Hook, `~/.claude/hooks/`)
> - **Verworfen** (per AD-Review): `claude-hooks-dist`, eigener Reflexions-Skill (YAGNI bei 1 Maschine / Theater-Risiko)
>
> **Auslöser:** Session 2026-06-01 produzierte 3 wiederkehrende Fehler-Cluster
> (Behauptung-vor-Prüfung, Umgebung-nicht-verstanden, Flailing-bei-Hindernis).
> Zwei lokale Fixes (`make test`, evidence-claim-Stop-Hook) wurden gebaut — aber
> **lokal**. Dieses Konzept beantwortet: *Wie werden solche Lehren strukturell,
> platform-weit und dauerhaft wirksam, statt in einer Maschine zu versanden?*

---

## 1. Problem (evidenzbasiert, nicht vermutet)

| Befund | Beleg (2026-06-01 verifiziert) |
|---|---|
| Fehler wiederholen sich, weil Lehren **nicht persistieren** | Policy `evidence-discipline` war im Kontext und wurde 3× verletzt |
| Fixes bleiben **maschinenlokal** | `~/.claude` ist **kein git-Repo**; `settings.json` nirgends versioniert |
| **Keine** einheitliche Hook-Verteilung | `log_llm_call.py` hand-gespiegelt in `platform/tools/claude-hooks/`; neuer Scanner nirgends; `cc-skill-dist` kann **nur** Skills, keine Hooks |
| Das Test-Env-Problem ist **systemisch** | **28 von 38** Repo-Makefiles haben kaputtes `pytest -v` ohne PG/Env |
| Verteilung ist **3-fach fragmentiert** | Skills→`cc-skill-dist`, Policies→`claude-policy`/Orchestrator, Hooks→manuell |

**Kernsatz:** Wir haben *Mechanismen für Wissen* (Policies, Memory) und *Mechanismen für Workflows* (Skills), aber **keinen Mechanismus für ausführbare Guardrails** (Hooks + `settings.json` + repo-lokale Make/CI-Invarianten). Genau dort entstehen die teuersten Fehler.

---

## 2. Zielbild

Ein **geschlossener Verbesserungs-Loop**, bei dem jede Session-Lehre einen von drei klar getrennten Kanälen nimmt — und jeder Kanal eine **Single Source of Truth in git** hat:

```
Session-Reflexion  ──klassifiziert──▶  Kanal A: Wissen      → policies/ + CC-Memory
                                       Kanal B: Workflow     → .windsurf/workflows/ (Skill)
                                       Kanal C: Guardrail     → platform/tools/claude-hooks/ + repo-Generatoren
                                              │
                                              └──verteilt──▶ alle Maschinen + alle Repos
                                                     │
                                                     └──misst Wirkung──▶ zurück in Reflexion
```

Die drei Kanäle existieren teils schon (A, B). **Das Konzept schließt Kanal C und den Mess-Rückfluss.**

---

## 3. Die drei Bausteine

### Baustein 1 — `claude-hooks-dist` (analog `cc-skill-dist`, für Guardrails)

**Was:** Ein Verteiler, der `platform/tools/claude-hooks/*.py` + ein **versioniertes `settings.json`-Fragment** nach `~/.claude/hooks/` + `~/.claude/settings.json` (merge, nicht overwrite) bringt — mit `generate.py`/`doctor.py`-Muster wie bei Skills (MANAGED-Footer, Manifest, `--allow-live`-Gate).

**Warum git-basiert:** Weil `~/.claude` flüchtig ist. SSoT = `platform@main`. Beim Session-Start (Hook `refresh_pinned_policies.sh` existiert bereits!) wird zusätzlich `claude-hooks-dist pull` ausgeführt → Hooks sind auf jeder Maschine aktuell.

**Kritisch:** `settings.json` darf **nie** überschrieben werden (enthält maschinenspezifische Permissions). Der Verteiler merged nur den `hooks`-Block additiv und idempotent (per Hook-Command-Pfad deduped — genau wie ich es heute manuell tat).

### Baustein 2 — `make test` als Generator-Invariante (nicht 28× Handarbeit)

**Was:** Das self-contained `test-pg`-Target wird **Teil der onboard-repo / repo-Scaffolding-Vorlage** und per `gen_project_facts.py`-artigem Sweep in alle 28 betroffenen Repos gepusht — als **idempotenter Patch**, der nur dann eingreift, wenn das Target noch `bare pytest` ist.

**Warum nicht 28 PRs von Hand:** Das wäre genau der Fehler, den wir vermeiden wollen (Handarbeit, die driftet). Ein Generator + ein Drift-Check (`drift_check.py` existiert) = die Invariante bleibt erzwungen.

**Caveat:** Nicht alle 28 Repos sind Django/PG. Reine Packages (authoringfw, promptfw, …) brauchen kein PG. Der Generator muss **Profil-bewusst** sein (django-app vs python-package — die Unterscheidung gibt es schon in `repo-health-check`).

### Baustein 3 — Reflexion als wiederholbares Ritual (Skill `/session-reflexion`)

**Was:** Ein Skill, der am Session-Ende (oder on-demand) die Transcript-Marker auswertet, die der evidence-claim-Scanner sammelt, die Fehler-Cluster benennt, und **strukturiert in die drei Kanäle einsortiert** — mit Pflicht-Feld „Kanal A/B/C + konkretes Artefakt".

**Warum:** Heute war die Reflexion ad-hoc und nur weil du danach fragtest. Ein Ritual macht sie deterministisch. Es ist das Gegenstück zu `/session-ende` (sichert *Wissen*), aber für *Prozess-Lehren*.

---

## 4. Mess-Rückfluss (sonst ist es Kosmetik)

Jede der drei Maßnahmen braucht eine **Falsifikationsmetrik** (wie `evidence-discipline` sie schon fordert):

| Maßnahme | Metrik | Quelle | Abschalt-Schwelle |
|---|---|---|---|
| evidence-claim-Scanner | Rate „Claim mit Check vor Behauptung" (R) | Transcript-grep, beide Richtungen | wenn R nach ~10 Sessions nicht > Baseline → Hook ist Lärm, raus |
| `make test`-Invariante | Anzahl roter CI-Läufe durch Env-Fehler | CI-History | wenn nicht sinkend → Generator wirkt nicht |
| `/session-reflexion` | Wiederholungsrate gleicher Fehler-Cluster | CC-Memory drift-Tags | wenn Cluster wiederkehren → Ritual ist Theater |

**Prinzip:** Was seine eigene Metrik nicht schlägt, wird **gelöscht, nicht gepatcht** (direkt aus `evidence-discipline.md` übernommen).

---

## 5. ADR-Frage

Braucht das ein ADR? **Teilweise ja:** `claude-hooks-dist` ist eine **neue Verteil-Infrastruktur** (Service-Grenze, cross-cutting über alle Repos+Maschinen) → ADR-pflichtig nach `adr-threshold.md`. `make test`-Generator + Reflexions-Skill folgen bestehenden Mustern (cc-skill-dist, onboard-repo) → **kein** ADR, nur CHANGELOG+PR.

---

## 6. Phasen (kleinste-wirksame zuerst)

- **P0 (heute, lokal bewährt):** evidence-claim-Scanner + `make test` in dev-hub — **erledigt**, dient als Pilot.
- **P1:** evidence-claim-Scanner nach `platform/tools/claude-hooks/` heben + `settings.json`-Fragment versionieren. **Manuell verteilt** auf die 1 Maschine (Achim arbeitet nur auf einer). Wenn der Scanner sich über ~10 Sessions bewährt (R-Metrik) → erst dann P2.
- **P2:** `claude-hooks-dist` bauen (nur falls je >1 Maschine ODER der manuelle Pfad schmerzt — sonst YAGNI, s.u.).
- **P3:** `make test`-Generator + Sweep über 28 Repos (Profil-bewusst).
- **P4:** `/session-reflexion`-Skill.

---

## 7. ADVOCATUS DIABOLUS — wo dieses Konzept selbst falsch sein könnte

> Pflicht-Sektion. Ein Konzept gegen Selbstüberschätzung muss sich selbst misstrauen.

**AD-1 — Das ganze Ding ist über-engineered für einen Ein-Mann-Ein-Maschinen-Betrieb.**
Achim arbeitet (verifiziert in dieser Session) **nur auf einer Maschine**. `claude-hooks-dist` löst ein Multi-Maschinen-Verteilproblem, das **nicht existiert**. Baustein 1 ist möglicherweise reine Beschäftigung. → *Konsequenz: P2 ist YAGNI bis Maschine #2 auftaucht. Der ehrliche Fix für „~/.claude ist flüchtig" ist banal: ein dotfiles-git-Repo + Symlink, kein Verteiler-Framework.*

**AD-2 — Wir bekämpfen ein Verhaltensproblem mit Tooling.** Die 3 Fehler-Cluster sind **Verhaltensmuster des Modells**, kein Werkzeugmangel. Ein Stop-Hook, der *nach* der Falschbehauptung warnt, ist Schadensbegrenzung, nicht Prävention — der falsche PR-Body war schon geschrieben. → *Konsequenz: Der einzige echte Präventiv-Hebel ist Baustein 2 (make test macht den Check billiger als das Raten). Tooling kann nur die Kosten des richtigen Verhaltens senken, nicht das falsche verbieten. Konzept ehrlich darauf zuspitzen statt Hook-Gläubigkeit.*

**AD-3 — Der Reflexions-Skill wird zum Theater.** „Session-Reflexion als Ritual" klingt gut, aber Rituale ohne Konsequenz verkommen zu Abhaken. Wenn die Reflexion nicht *automatisch* Artefakte erzeugt (PR, Memory, Generator-Eintrag), ist sie Selbstbespiegelung. → *Konsequenz: Der Skill darf nicht „reflektiere" sagen, sondern muss „erzeuge ein Artefakt in Kanal A/B/C oder erkläre, warum keins nötig ist" erzwingen — mit demselben Gate-Charakter wie `/complete`.*

**AD-4 — Mess-Metriken sind selbst nicht falsifizierbar gebaut.** Ich behaupte „R-Metrik über grep" — aber wer führt den grep aus? Wenn niemand die Metrik *automatisch* erhebt, ist die ganze Abschnitt-4-Tabelle Dekoration. → *Konsequenz: Die Metrik-Erhebung muss selbst ein Hook/Cron sein, sonst streichen. Lieber 1 Metrik die wirklich läuft als 3 die auf Papier stehen.*

**AD-5 — 28 Repos „fixen" könnte 28 Repos brechen.** Ein Generator-Sweep über 28 heterogene Makefiles, von denen viele Parallel-Sessions gehören, ist **genau** das Bulk-Operation-Risiko aus dem 🌀-Memory `drift_committed_abspath_symlinks_workflows`. Ein falscher Patch × 28 = 28 rote CIs. → *Konsequenz: Sweep nur mit Profil-Check + Dry-run + pro-Repo-PR (kein Direkt-Push), und gegated wie das CI-Green-Programm. Niemals Bulk-Direct.*

**AD-6 — Out-of-the-box-Gegenthese: Vielleicht ist das Problem nicht „zu wenig Guardrails", sondern „zu viel Autonomie-Druck".** Jeder „mach es autonom" hat mich tiefer in die Kette getrieben. Die wirksamste Einzelmaßnahme wäre vielleicht keine Tech, sondern eine **Checkpoint-Norm**: Bei jeder Aktion, die ein 3. Repo oder Prod berührt, *erst innehalten und Scope bestätigen*. Das ist ein Prompt-/Verhaltens-Fix, kein Tool. → *Konsequenz: Prüfen, ob eine einzige Zeile in CLAUDE.md („bei Repo-Wechsel #3+ oder Prod: Scope-Checkpoint an User") mehr bewirkt als alle drei Bausteine.*

---

## 8. Empfehlung (nach AD-Review geschärft)

Das ursprüngliche 3-Baustein-Konzept ist **zu groß**. Nach der Selbstkritik bleibt der wirksame Kern:

1. **SOFORT (hoher Hebel, niedrig Risiko):**
   - `make test`-Generator über die 28 Repos — aber **gegated, pro-Repo-PR, profil-bewusst** (AD-5). Das ist der einzige echte *Präventiv*-Hebel (AD-2).
   - **dotfiles-git für `~/.claude`** statt `claude-hooks-dist` (AD-1) — banal, löst Flüchtigkeit sofort.
   - **Eine CLAUDE.md-Zeile: Scope-Checkpoint bei Repo #3+/Prod** (AD-6) — billigster Verhaltens-Hebel.

2. **PROBE (bewähren lassen, dann entscheiden):**
   - evidence-claim-Scanner bleibt P0-Pilot. Nach ~10 Sessions R-Metrik prüfen (AD-4: Metrik-Erhebung selbst als Hook bauen, sonst streichen).

3. **VERWORFEN bis Bedarf:**
   - `claude-hooks-dist` (YAGNI bei 1 Maschine, AD-1).
   - `/session-reflexion`-Skill als eigenes Ritual (AD-3) — stattdessen die Artefakt-Pflicht in `/session-ende` integrieren.

**Leitprinzip (aus `feedback_iteration_count_as_signal` + `evidence-discipline`):** Das kleinste wirksame Konzept schlägt das vollständige. Wenn dieser Entwurf nach 3 Iterationen nicht konvergiert, ist das Problem falsch geframt — dann ist die Antwort „eine Verhaltensnorm + ein Generator", nicht „eine Verteil-Infrastruktur".
