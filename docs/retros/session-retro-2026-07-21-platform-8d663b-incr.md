---
retro_schema: 1
date: 2026-07-21
repo_scope: [platform, mcp-hub]
session_id: 8d663b-incr
footprint: lean
findings_total: 2
findings_survived: 2
refuted_rate: 0.0
phase3_refuted: 0
pre_refuted: 0
scores:
  zielerreichung: 5
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 4
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [stale-local-clone-as-ground-truth, no-backticks-in-gh-body]
recurring_findings: [stale-local-clone-as-ground-truth, no-backticks-in-gh-commit-args]
---

# Session-Retro-Increment 2026-07-21 — platform + mcp-hub (8d663b-incr)

> **Increment-Scope:** NUR die Follow-up-Arbeit NACH dem Haupt-Retro (session-retro-2026-07-21-platform-8d663b). Der Haupt-Retro wird NICHT re-litigiert. Lean (inline, kein Subagent — Footprint winzig, jeder Schritt owner-freigegeben), aber mit Frisch-Checkout-Pflicht + Artefakt-Erdung.

## 1. Executive Summary
- **Alle 6 Follow-ups landeten sauber auf origin/main** (verifiziert): #1309 (B1+B3+Pilot) mit allen 3 Dateien, KONZ-027 `pipeline_status: pilot`, ADR-156 verlinkt mcp-hub#181, B1-Overclaim weg (0 Treffer), #180 gemergt + Bypass-Audit-Kommentar, #181 gelabelt, #1310 erstellt. Keine verlorene Änderung.
- **Zwei Prozess-Rezidive in der Follow-up-Arbeit** — beide dokumentierte Muster, beide selbst gefangen, aber beide kosteten einen Zyklus.
- **I2 schärft ein gate-pflichtiges Muster:** die „git fetch first"-Disziplin gegen `stale-local-clone` ist unvollständig — Fetch aktualisiert `origin/main`, aber NICHT den Working-Tree; wer danach die Working-Tree-Datei grept, liest weiter stale.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| I1 | `gh issue comment 1302 --body "…"` mit Backticks/Klammern brach die Shell (Command-Substitution) — trotz existierender Memory `feedback_no_backticks_in_gh_commit_args`; Recovery via `--body-file` | Werkzeug / Regel-nicht-angewandt | Niedrig | SURVIVES | Memory existiert (grep-verifiziert); Fehlversuch transkript-geerdet (kein git-Artefakt), Recovery-Kommentar #1302 via `--body-file` real gepostet | `no-backticks-in-gh-commit-args` (Memory, Vorkommen-2 in Session) |
| I2 | In B2 `grep scripts/verify-adr156.sh` auf dem lokalen mcp-hub-Working-Tree gelesen (HEAD `c092cb8`), obwohl origin/main `15a1fc7` war — zeigte die ALTEN Check-Zeilen; nur durch Content-Smell (nicht durch Prozess) gefangen, bevor ein Fehlbefund entstand | fehlende Validierung / stale-clone | Mittel | SURVIVES | `git rev-parse HEAD`=c092cb8 vs `origin/main`=15a1fc7 (SHA-Divergenz real); `git show origin/main:scripts/verify-adr156.sh` zeigte die verankerte Fassung | `stale-local-clone-as-ground-truth` (GATE-PFLICHT ×7 → ×8) |

## 3. Scorecard (1–5, an Befunden verankert)

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 5 | alle 6 Follow-ups korrekt auf main gelandet, verifiziert, exakt wie gescopt |
| architektur_design | 4 | keine neue Architektur (reine Ausführung); B1-Overclaim-FIX erhöhte Doku-Ehrlichkeit |
| code_konventionstreue | 4 | saubere Worktrees/PRs/Commits; Ding: I1 verletzte die `-F`/`--body-file`-Konvention |
| risiko_debt | 4 | Increment REDUZIERTE Debt (B1-Overclaim gefixt, B3 getrackt, B2 als Issue); Ding: I2-Near-Miss |
| prozess_effizienz | 3 | zwei dokumentierte-Muster-Rezidive (I1 Retry nötig, I2 Korrektur nötig) — beide selbst gefangen, aber je ein Zyklus Kosten |
| entscheidungsqualitaet | 4 | gute Calls: #1302-Label behalten (Gate durch Pilot erfüllt), B2 als Issue statt kaputtem CI-Workflow, Bypass-Audit-Kommentar |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #) — |Soll| == 2 Survivors

| Ist (beobachtet, Beleg) | Soll (besserer Schritt) | eliminiert |
|---|---|---|
| `gh --body "…\`backticks\`…(Klammern)…"` brach die Shell trotz Memory (I1) | Pre-Send-Reflex: JEDES `gh`/`git` mit `--body`/`-m`, das Backticks, `(`/`)`, `$` oder `!` enthält, DEFAULT über `--body-file`/`-F` absetzen — nicht erst nach dem Fehlschlag. (Meta-Lehre wie beim Board-Pre-Send-Check: Memory *aufschreiben* ≠ *anwenden*.) | #I1 |
| `git fetch origin main` gelaufen, dann `grep <working-tree-datei>` → stale gelesen (I2) | Frisch-Checkout-Pflicht **präzisieren**: gegen stale-clone hilft nicht „fetch first", sondern **aus dem Ref lesen** — `git show origin/main:<pfad>` / `git -C … diff origin/main`, NIE die Working-Tree-Datei nach dem Fetch (Fetch bewegt `origin/main`, nicht den Tree) | #I2 |

## 5. Längsschnitt (retro_kpis.py)
`python3 tools/retro_kpis.py` gelaufen.
- **`stale-local-clone-as-ground-truth` GATE-PFLICHT ×7** (e17299, 3b123e, a2c373, f4a546, d2b425-incr, d2b425, d80d23) → **mit I2 jetzt ×8**. Die Skill-Zeile (Phase 1/3 „git fetch first") existiert bereits, hat den Fall aber NICHT verhindert — weil sie „fetch" sagt, nicht „aus dem Ref lesen". **Das ist der Gate-Hebel: die bestehende Anti-Pattern-Zeile ist unvollständig**, nicht abwesend. Soll-Schritt #I2 formuliert die Schärfung.
- `no-backticks-in-gh-commit-args` ist eine Memory (nicht im retro_kpis-Slug-Satz) — I1 ist ihr 2. Vorkommen in dieser Session-Kette; noch kein retro-Slug, aber Memory-belegt.
- **refuted_rate 0.0:** lean-Footprint hat KEINEN unabhängigen Phase-3-Skeptiker (inline verifiziert) → das Band-KPI (<0.2 = Theater) gilt hier nicht; beide Befunde sind dokumentierte-Muster-Rezidive mit hartem Anker (Memory-Existenz bzw. SHA-Divergenz), nicht widerlegbares Stroh.

## 5b. Autonomie-Kalibrierung
- **over_ask = 0:** Follow-ups liefen nach expliziter Batch-Freigabe („B8-9-10-1-3rest-2 go", „idea→pilot go", „1 per admin", „#1309 approved") autonom durch — korrekt, kein unnötiges Rückfragen.
- **over_act = 0:** der Admin-Bypass von mcp-hub#180 war explizit owner-freigegeben („1 per admin") + Audit-Kommentar; der Pilot-Flip explizit freigegeben. Kein Gate ohne Wort berührt.

## 6. Verankerung (kopierfertig — Mensch entscheidet)

### memory_candidates
```
name: feedback-stale-clone-read-from-ref-not-tree-after-fetch
type: feedback
drift: true
drift_episode: 2026-07-21-stale-clone-post-fetch-worktree-read
body: Gegen `stale-local-clone-as-ground-truth` (gate-pflichtig ×8) reicht „git fetch origin main first" NICHT — Fetch aktualisiert `origin/main`, aber NICHT den Working-Tree. Wer nach dem Fetch die Working-Tree-Datei grept/liest, liest weiter stale. **Regel: nach dem Fetch aus dem REF lesen** — `git show origin/main:<pfad>` bzw. `git diff origin/main -- <pfad>`, nie `grep <lokale-datei>`. Realfall 2026-07-21 (retro 8d663b-incr, I2): B2-grep auf lokalem mcp-hub-Tree (HEAD c092cb8) zeigte die alten verify-adr156-Check-Zeilen, obwohl origin/main (15a1fc7) sie längst verankert hatte — nur durch Content-Smell gefangen. **Why:** die bestehende Skill-Zeile sagt „fetch", nicht „aus dem Ref lesen" — die Lücke ist die Lesequelle, nicht der Fetch. **How to apply:** Verifikations-Reads in seltenen/fremden Repos IMMER über `git show origin/<branch>:` statt Working-Tree. [[feedback_stale_local_clone_never_ground_truth]] [[feedback_stale_clone_as_edit_basis]]
```
Kein zweiter memory_candidate für I1 — `feedback_no_backticks_in_gh_commit_args` existiert bereits und ist korrekt; die Lücke ist Anwendung, nicht Inhalt (deckt sich mit dem Board-Pre-Send-Check-Muster in `~/.claude/CLAUDE.md`).

### adr_candidates
```
(keiner — reine Prozess-/Werkzeug-Ebene.)
```

## 7. Maßnahmen (Action-Board)

🟢 **Offen — dein Zug**
| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Memory `stale-clone-read-from-ref` verankern | — | [file://…/memory/](file:///home/devuser/.claude/projects/-home-devuser-github-platform/memory/) | 🟢 offen | du: memory_candidate freigeben |
| 2 | session-retro-Skill Phase-1/3-Zeile schärfen (fetch → „aus dem Ref lesen") | platform | folgt | 🟢 offen | du: Gate-Schärfung ok? |

✅ **Erledigt (Increment selbst)**
| # | Item | Status |
|---|---|---|
| 3 | 6/6 Haupt-Retro-Follow-ups auf main verifiziert | ✅ |

## 8. Nicht verifiziert (Restlücken)
- **I1-Instanz** (der konkrete Shell-Fehler) ist transkript-geerdet, kein git-Artefakt — als Instanz Hypothese; die Regel-Verletzung selbst ist über die Memory-Existenz + den `--body-file`-Recovery-Kommentar belegt.
- **Keine unabhängige Falsifikation** (lean, kein Phase-3-Skeptiker) — beide Befunde sind Selbst-Report mit dokumentiertem Anker; billigster Härtungs-Check wäre ein frischer Sonnet-Skeptiker, für diesen Footprint bewusst ausgelassen.
