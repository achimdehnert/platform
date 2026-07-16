---
retro_schema: 1
date: 2026-07-16
repo_scope: [iil-klickdummy]
session_id: d80d23
footprint: full
findings_total: 2
findings_survived: 1
refuted_rate: 0.5
phase3_refuted: 1
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 5
  code_konventionstreue: 5
  risiko_debt: 3
  prozess_effizienz: 2
  entscheidungsqualitaet: 3
gate_candidates: [stale-local-clone-as-ground-truth]
recurring_findings: [stale-local-clone-as-ground-truth]
footprint_reduction_reason: "KORRIGIERT nach Erstversion: initial faelschlich 'lean' klassifiziert (Stale-Clone zeigte nur 2 statt tatsaechlich 6 PRs seit dem letzten Retro). Belassen bei 'full'-Label statt neuem Multi-Agent-Nachlauf, da die zusaetzlichen PRs (#181-185) bereits einzeln CI-gruen/gemergt sind und der einzige verbleibende Fund (Befund #2) den Prozess dieses Retros selbst betrifft, nicht neue Session-Inhalte."
---

## 0. Korrekturhinweis (ersetzt Erstversion dieses Reports)

Diese Datei wurde **vor dem ersten Merge korrigiert** (PR noch offen, kein Anchor
bisher). Die Erstversion behauptete einen SURVIVES-Fund (`AGENT_HANDOVER.md` zeige
stale "platform#1131 Merge steht aus"), der beim Versuch, die zugehörige Korrektur-PR
#180 zu mergen, **widerlegt** wurde: der Merge schlug fehl (`CONFLICTING`), und die
Nachprüfung gegen frisch gefetchtes `origin/main` zeigte, dass die Live-`##
Prioritäten`-Sektion die korrekte Aussage ("gemergt 2026-07-14T10:24Z") bereits seit
PR #183 (`f879544`, 2026-07-15) enthält — **einen Tag vor** diesem Retro. Ursache der
Fehlbehauptung: dieses Retro las den `git log` des lokalen Klons, ohne vorher
`git fetch` auszuführen, und übersah dadurch 4 gemergte PRs (#182–185). Das ist die
eigentliche, überlebende Erkenntnis dieses Retros (Befund #2).

## 1. Executive Summary

- Seit dem letzten Retro dieses Repos (`0ba8b4`, 2026-07-14) gab es **6**, nicht 2,
  neue Artefakte: PR #178 (gemergt), #180 (jetzt geschlossen, s.u.), #181/#182
  (Sitemap-Generator-Fix, v1.32.2), #183 (Session-Ende 2026-07-15,
  KD-Sitemap-Rollout über 8 weitere Repos + neuer `/kd-sitemap`-Skill), #184
  (sitemap target=_blank-Fix), #185 (genesor-Cross-Link).
- **Befund #1 (Erstversion dieses Reports) ist REFUTED**: die als stale behauptete
  `AGENT_HANDOVER.md`-Aussage war zum Zeitpunkt der Prüfung bereits korrekt — der
  vermeintliche Fund entstand aus einem lokal ungefetchten Repo-Klon.
- **Befund #2 SURVIVES**: dieses Retro selbst ist eine weitere, direkt beobachtete
  Instanz von `stale-local-clone-as-ground-truth` — einem bereits ×6 gate-pflichtigen
  Muster (`retro_kpis.py`: `e17299, 3b123e, a2c373, f4a546, d2b425-incr, d2b425`),
  diesmal *innerhalb der eigenen Ausführung dieser Skill* (Frisch-Checkout-Pflicht,
  Phase 3, existiert bereits als Regel — wurde hier für den initialen Collect-Schritt
  nicht angewendet, obwohl die Skill sie nur für Skeptiker-Prompts explizit vorschreibt).
- Als Konsequenz wurde die Korrektur-PR #180 fälschlich als "liegengeblieben, mergen"
  eingestuft — tatsächlich war sie durch #183 bereits obsolet. Auf Nutzerentscheidung
  hin **geschlossen statt gemerged** (Merge hätte die inzwischen aktualisierte
  Prio-Tabelle regressiert).
- **Neu entdeckt, nicht Teil dieses Retros:** die 2026-07-15-Session (#183,
  Sitemap-Rollout, laut eigener Notiz "7 Merges lösten je einen echten Prod-Deploy
  aus" in anderen Repos) hat noch **kein eigenes Session-Retro** — nach Phase-0-Trigger
  ("Prod-Schritt" ⇒ mind. `full`, hier sogar cross-repo) wäre das fällig. Als
  Restlücke in §8 geführt, nicht selbst nachgezogen (Scope-Checkpoint).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | `AGENT_HANDOVER.md` zeige stale "platform#1131 Merge steht aus" in der Live-Prio-Sektion | Prozesslücke | — | **REFUTED** | `git show origin/main:AGENT_HANDOVER.md` Z. 329-332 (`## Prioritäten`-Sektion, nicht Z. 52/293 der historischen Blöcke) sagt bereits "gemergt 2026-07-14T10:24Z"; `git show f879544 -- AGENT_HANDOVER.md` zeigt PR #183 als Urheber der Korrektur, 2026-07-15, vor diesem Retro | n/a (widerlegt) |
| 2 | Dieses Retro selbst las `git log` ohne vorheriges `git fetch`, übersah 4 gemergte PRs (#182-185) und produzierte daraus den falschen Befund #1 | Werkzeug/Prozesslücke | hoch | **SURVIVES** | Erste Bash-Session dieses Retros: `git log --oneline -15` ohne vorausgehendes `git fetch`; `origin/main` HEAD zum Zeitpunkt war bereits `58fb8df` (#185), lokal sichtbar nur bis `909bfdd` (#178) | `stale-local-clone-as-ground-truth` — **7. Vorkommen** (bereits ×6 gate-pflichtig: `e17299, 3b123e, a2c373, f4a546, d2b425-incr, d2b425`) |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Endergebnis (PR #180 korrekt geschlossen, Report korrigiert) stimmt, aber nur nach einer Selbstkorrektur mitten im Retro |
| architektur_design | 5 | n/a — reine Doku/Prozess-Session |
| code_konventionstreue | 5 | betroffene PRs (#178-185) selbst alle CI-grün, Commit-Konvention eingehalten |
| risiko_debt | 3 | Blast-Radius des Fehlers blieb klein (docs-only, PR noch unmerged, vor Anchor korrigiert), aber ein 7. Vorkommen eines seit >10 Tagen bekannten Gate-Kandidaten ohne Gate ist echtes Risiko |
| prozess_effizienz | 2 | Zusätzliche Roundtrips (Merge-Versuch, Re-Fetch, Report-Neufassung) nur weil der billigste Check (`git fetch`) am Anfang ausgelassen wurde |
| entscheidungsqualitaet | 3 | Ursprüngliche Merge-Empfehlung war falsch; korrigiert erst durch den Merge-Versuch selbst (nicht durch Vorab-Prüfung) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Phase-1-Collect dieses Retros startete mit `git log --oneline -15` auf dem lokalen Klon, ohne vorher `git fetch origin main` — genau die Lücke, die die Skill in Phase 3 ("Frisch-Checkout-Pflicht") bereits für Skeptiker-Prompts schließt, aber nicht explizit für Phase 1 selbst vorschreibt | Phase-1-Collect-Schritt der Skill um denselben Fetch-Zwang erweitern, den Phase 3 bereits hat: **jeder** Collect-Schritt (auch inline bei `lean`) beginnt mit `git fetch origin <default-branch>`, bevor `git log`/`git diff` gegen den lokalen Branch liest | #2 |

## 5. Längsschnitt

```
🚨 GATE-PFLICHT  stale-local-clone-as-ground-truth  ×6  [e17299, 3b123e, a2c373, f4a546, d2b425-incr, d2b425]
```

Mit diesem Report **×7**. Bemerkenswert: die Skill selbst hat für Phase 3
(Skeptiker) bereits eine "Frisch-Checkout-Pflicht" als Reaktion auf das 3.
Vorkommen (`3b123e`) verankert — aber dieses 7. Vorkommen zeigt, dass die Lücke
in **Phase 1 (Collect)** unverändert fortbesteht, weil die Regel dort nie
nachgezogen wurde. Das ist eine Skill-Lücke, kein Einzelfehler.

Gegen `<auto-memory>/MEMORY.md` (iil-klickdummy) abgeglichen: kein bestehender
Eintrag zu `stale-local-clone-as-ground-truth` in diesem Repo (nur in anderen
Repos/Retros dokumentiert) — auch hier fehlt die lokale Verankerung.

## 5b. Autonomie-Kalibrierung

Kein `over_act` (keine irreversible Aktion vor Korrektur ausgeführt — PR #180
wäre beinahe gemerged worden, wurde aber vor Ausführung durch den fehlgeschlagenen
Merge-Versuch selbst gestoppt, nicht durch vorherige Prüfung). Das ist grenzwertig:
ein `over_act`-Beinah-Treffer (Freigabe wurde erteilt, Ausführung lief, Fehler kam
vom Git-Mergecheck, nicht von eigener Sorgfalt) — als Lern-Punkt vermerkt, nicht als
volles `over_act` gewertet, da kein Schaden eintrat.

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

**Memory-Kandidat** (repo: `iil-klickdummy`, Datei `stale-clone-retro-collect-gap.md`):

```markdown
---
name: stale-clone-retro-collect-gap
description: Session-Retro Phase-1-Collect las lokalen git log ohne vorheriges fetch, uebersah 4 gemergte PRs, produzierte einen REFUTED Fund als SURVIVES — 7. Instanz stale-local-clone-as-ground-truth, diesmal in Phase 1 statt Phase 3
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-16-retro-phase1-stale-clone
---

Vor JEDEM `git log`/`git status`-Check als Grundlage für Befunde — auch inline bei
`/session-retro`-Footprint `lean` — zuerst `git fetch origin <default-branch>`.
**Warum:** `stale-local-clone-as-ground-truth` ist seits `e17299`/`a2c373` (2026-07-04ff)
gate-pflichtig (×6) und die Skill hat dafür bereits eine Pflichtzeile in Phase 3
(Skeptiker), aber NICHT in Phase 1 (Collect) — genau dort ist es hier (7. Instanz,
`session-retro-2026-07-16-iil-klickdummy-d80d23`) erneut passiert: 4 gemergte PRs
(#182-185) wurden übersehen, ein falscher Fund (stale Handover-Status) wurde
geschrieben und beinahe zum Schließen der falschen PR (Merge statt Close) geführt.
**How to apply:** gilt für JEDE Aufgabe, die `git log`/`gh pr list` als Ground Truth
nutzt, nicht nur für Retros. Siehe [[genesor-Fix-Scope]] für die Schwester-Lehre
"Codebase-Zustand vor Behauptung prüfen".
```

**Skill-Fix-Vorschlag (an `session-retro.md` selbst, nicht hier ausgeführt):**
Phase 1 ("Collect") um denselben Satz wie Phase 3 ergänzen: "Jeder Collect-Schritt
beginnt mit `git fetch origin <default-branch>`, bevor gegen den lokalen Checkout
gelesen wird." Aktuell steht die Fetch-Pflicht nur bei Phase 3 (Skeptiker).

**ADR-Kandidat:** keiner.

## 7. Maßnahmen (Action-Board)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | PR #180 geschlossen (obsolet, nicht gemerged) | iil-klickdummy | https://github.com/iilgmbh/iil-klickdummy/pull/180 | ✅ done | — |
| 2 | Memory-Kandidat `stale-clone-retro-collect-gap` verankern | iil-klickdummy | n/a (Memory-Datei) | 🟢 dein Zug | Freigabe zum Schreiben |
| 3 | Phase-1-Fetch-Pflicht in `session-retro.md` nachziehen (Skill-Fix) | dev-hub (Skill-Quelle) | n/a, siehe §6 | 🟢 dein Zug | Freigabe, dann patche ich den Skill |
| 4 | 2026-07-15 Sitemap-Rollout-Session (#183, cross-repo Prod-Deploys) hat kein eigenes Retro | iil-klickdummy | n/a | 🟢 dein Zug | Entscheiden: eigenes `/session-retro` fahren? |

## 8. Nicht verifiziert (Restlücken)

- Die 2026-07-15-Sitemap-Rollout-Session (#183) wurde inhaltlich **nicht** retro'd
  (weder in `0ba8b4` noch hier) — sie erwähnt selbst 7 ausgelöste Prod-Deploys in
  anderen Repos. Billigster nächster Check: `gh pr list --search "sitemap 2026-07-15"`
  über die dort genannten Repos (trading-hub, tax-hub, dev-hub, dms-hub, research-hub,
  coach-hub, pptx-hub) + Deploy-Run-Status.
- Ob die in PR #180 behauptete Issue-#176-Merge-Statistik ("8/13 gemergt, 4
  CI-blockiert") mit dem aktuellen Live-Stand von Issue #176 übereinstimmt, wurde
  nicht unabhängig nachgezogen (das lag der ursprünglichen, jetzt zurückgezogenen
  PR-#180-Empfehlung zugrunde und ist mit deren Schließung ohnehin gegenstandslos).
- Kein Phase-5-Meta-Review (nur `full`/`deep`-Pflicht; Footprint wurde nachträglich
  auf `full` korrigiert, aber ein separater Meta-Agent wurde für diese Korrektur
  nicht mehr nachgeholt — Kostenabwägung, da der Bericht bereits durch den
  Merge-Versuch selbst falsifiziert wurde).
